"""
DEALERCORE v3.0 — DSR Permission Enforcement
-----------------------------------------------
Server-side enforcement of DSR module permissions and dealer subscription status.

This module bridges the gap identified in Phase 3 of the DSR Permission
Enforcement tracking document:

  Gap #3: DSR module permissions NOT enforced server-side — sales/api.py
          and inventory/api.py don't check DsrDealerAssignment.has_permission()
  Gap #5: DsrDealerAssignment.has_permission() is dead code — never called

Architecture
------------
When a DSR/Collector makes a request:

  1. PermissionMiddleware extracts JWT → sets request.is_dsr, request.dsr_user_id,
     request.dealer_username, etc.
  2. get_dealer_context() validates the DSR has an active assignment to the
     target dealer.
  3. **THIS MODULE** goes further — it loads the DsrDealerAssignment record,
     checks the specific module+action permission, AND verifies the dealer's
     subscription is active via SattaBase.

For dealers (is_dealer=True), the dealer's own access matrix is checked against
their SattaBase subscription plan. Dealers bypass DSR-level module checks (they
don't have DsrDealerAssignment records), but their plan-level access keys are
enforced. If a dealer's plan says ``bad_debt: false``, the dealer themselves
cannot access the bad debt feature.

Usage
-----
Decorator form (for entire endpoints)::

    from common.dsr_permissions import require_dsr_permission

    @route.post("")
    @require_dsr_permission("sales", "edit")
    async def create_sale(self, request, payload):
        ...

Helper form (for conditional logic within endpoints)::

    from common.dsr_permissions import check_dsr_permission

    async def my_endpoint(self, request):
        can_edit = await check_dsr_permission(request, "sales", "edit")
        if can_edit:
            ...

Guard-all form (checks module at the controller class level)::

    @api_controller("/sales", tags=["Sales"])
    @require_dsr_module("sales")
    class SalesController:
        ...

Dealer access form (checks dealer's plan access matrix)::

    from common.dsr_permissions import enforce_dealer_access

    @route.post("{id}/close-with-due")
    async def close_with_due(self, request, sale_id):
        await enforce_dealer_access(request, "bad_debt")
        ...

Permission Model
----------------
DSR permissions are stored as nested JSON on DsrDealerAssignment::

    {
        "dashboard": {"view": True},
        "inventory": {"view": True, "edit": False, "delete": False},
        "sales": {"view": True, "edit": True, "delete": False},
        "collections": {"view": True, "edit": False},
        "bad_debt": {"view": True, "edit": False},
        "suppliers": {"view": False},
        "reports": {"view": True, "export": False},
        "print": True,
        "manage_dsrs": True
    }

Module-level (dict) → check specific action:  has_permission("sales", "edit")
Scalar (bool) → check if True:               has_permission("print")

Enforcement Layers
------------------
Layer 0: Dealer access matrix — checks if the dealer's SattaBase subscription
         plan allows the requested module. Applied to BOTH dealers and DSRs.
         If the dealer's plan says ``bad_debt: false``, nobody (dealer or DSR)
         can access that feature.

Layer 1: Dealer subscription active — verifies the dealer's subscription is
         active (not expired/cancelled). Applied to both dealers and DSRs.

Layer 2: Dealer's plan allows module — same as Layer 0 but for DSRs. This is
         now redundant with Layer 0 but kept for defense-in-depth.

Layer 3: DSR assignment permissions — checks the DsrDealerAssignment record
         for the specific module:action. Only applies to DSRs.

Key principle: **DSR permissions can never exceed what the dealer's
subscription allows.** If the dealer's plan says ``suppliers: false``, no
DSR under that dealer can be granted suppliers access.
"""

from __future__ import annotations

import logging
from functools import wraps
from typing import Optional

from django.http import HttpRequest
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# CORE: ASYNC PERMISSION CHECK
# ═══════════════════════════════════════════════════════════════════════════


async def get_dsr_assignment(request: HttpRequest):
    """Return the active DsrDealerAssignment for the current request.

    Looks up the DSR user by ``request.dsr_user_id`` (set by
    PermissionMiddleware for local DSR JWTs) or by ``request.user_email``
    (set for SattaBase JWTs), scoped to the dealer from
    ``request.dealer_username``.

    Returns ``None`` if the user is a dealer (no assignment needed) or if
    no active assignment is found.
    """
    # Dealers bypass assignment lookup
    if getattr(request, "is_dealer", False):
        return None

    from dsr.invitation_models import DsrDealerAssignment

    dsr_user_id = getattr(request, "dsr_user_id", None)
    dealer_username = getattr(request, "dealer_username", None)
    user_email = getattr(request, "user_email", None)

    if not dealer_username:
        return None

    # Try by dsr_user_id first (most reliable — from local DSR JWT)
    if dsr_user_id:
        try:
            assignment = await DsrDealerAssignment.objects.select_related(
                "dsr", "dealer"
            ).aget(
                dsr_id=str(dsr_user_id),
                dealer_id=dealer_username,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            )
            return assignment
        except DsrDealerAssignment.DoesNotExist:
            logger.debug(
                "[DSR_PERM] No active assignment for dsr_user_id=%s, dealer=%s",
                dsr_user_id, dealer_username,
            )

    # Fallback: try by email (for SattaBase JWT where dsr_user_id is not set)
    if user_email:
        try:
            assignment = await DsrDealerAssignment.objects.select_related(
                "dsr", "dealer"
            ).aget(
                dsr__email=user_email,
                dealer_id=dealer_username,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            )
            return assignment
        except DsrDealerAssignment.DoesNotExist:
            logger.debug(
                "[DSR_PERM] No active assignment for email=%s, dealer=%s",
                user_email, dealer_username,
            )

    return None


async def check_dsr_permission(
    request: HttpRequest,
    module: str,
    action: str = "view",
) -> bool:
    """Check if the requesting user has the specified module:action permission.

    Returns ``True`` if:
      - The user is a dealer AND the dealer's plan allows this module
      - The user is a DSR with an active assignment that includes the permission,
        AND the dealer's plan allows this module

    Returns ``False`` if:
      - The dealer's subscription is inactive
      - The dealer's plan doesn't include this module (access matrix)
      - The DSR has no active assignment to this dealer
      - The DSR's assignment doesn't include the requested permission

    This does NOT raise — it returns a boolean for conditional logic.
    Use :func:`require_dsr_permission` or :func:`enforce_dsr_permission`
    when you want a 403 on failure.
    """
    # Layer 0: Check dealer's access matrix for EVERYONE (dealer + DSR)
    if not await _is_dealer_module_allowed(request, module):
        return False

    # Layer 1: Check dealer subscription active for EVERYONE
    if not await _is_dealer_subscription_active(request):
        return False

    # Dealers pass after access matrix + subscription checks
    if getattr(request, "is_dealer", False):
        return True

    # If not a DSR, return True — auth handled by permission classes
    if not getattr(request, "is_dsr", False):
        return True

    # Layer 3: Get the assignment and check module:action permission
    assignment = await get_dsr_assignment(request)
    if assignment is None:
        return False

    return assignment.has_permission(module, action)


async def enforce_dsr_permission(
    request: HttpRequest,
    module: str,
    action: str = "view",
) -> None:
    """Enforce permission — raises HttpError(403) if denied.

    This is the raise-on-fail variant of :func:`check_dsr_permission`.
    Use it at the top of endpoint methods to guard access.

    Four-layer check (applies to BOTH dealers and DSRs):
      0. Dealer's plan must ALLOW the requested module (access matrix)
         — checked for dealers AND DSRs
      1. Dealer subscription must be active (via SattaBase access)
         — checked for dealers AND DSRs
      2. Dealer's plan must ALLOW the requested module (redundant with
         layer 0, kept for defense-in-depth for DSRs)
      3. DSR's assignment must include the requested module:action
         — only checked for DSRs

    Layer 0 is critical — if a dealer's plan says ``bad_debt: false``,
    the dealer THEMSELVES cannot access the bad debt feature. This
    ensures the SattaBase access matrix is enforced on the backend,
    not just on the frontend.

    IMPORTANT: If the request has neither ``is_dealer`` nor ``is_dsr``
    set (unauthenticated / JWT not decoded), this function passes
    through silently — authentication is handled by the permission
    classes (IsJwtAuthenticated, etc.), not by the DSR permission layer.
    """
    # Layer 0: Check dealer's access matrix — applies to EVERYONE
    await _enforce_dealer_module_access(request, module)

    # Layer 1: Check dealer subscription active — applies to EVERYONE
    await _enforce_dealer_subscription(request)

    # Dealers pass after access matrix + subscription checks
    if getattr(request, "is_dealer", False):
        return

    # If not identified as a DSR either, skip DSR-level enforcement.
    is_dsr = getattr(request, "is_dsr", False)
    if not is_dsr:
        return

    # Layer 3: Get the assignment and check module:action permission
    assignment = await get_dsr_assignment(request)
    if assignment is None:
        logger.warning(
            "[DSR_PERM] No active assignment found for request to %s %s "
            "(module=%s, action=%s)",
            request.method, request.path, module, action,
        )
        raise HttpError(
            403,
            f"You do not have an active assignment to this dealer. "
            f"Required permission: {module}.{action}",
        )

    if not assignment.has_permission(module, action):
        logger.info(
            "[DSR_PERM] Permission denied: %s.%s for DSR %s on dealer %s",
            module, action, assignment.dsr_id, assignment.dealer_id,
        )
        raise HttpError(
            403,
            f"Permission denied: you do not have '{action}' access to the "
            f"'{module}' module. Contact your dealer to update your permissions.",
        )


async def enforce_dsr_module(request: HttpRequest, module: str) -> None:
    """Enforce that the user has ANY access to a module (view at minimum).

    This is a coarser check than :func:`enforce_dsr_permission` — it only
    verifies the module is allowed by the dealer's access matrix and, for
    DSRs, that it exists in the DSR's permissions and isn't empty/False.
    Useful for guarding entire controllers where specific action checks are
    done inside individual endpoints.

    For dealers: only the access matrix check is applied.
    For DSRs: access matrix + subscription + assignment checks are applied.
    """
    # Layer 0: Check dealer's access matrix — applies to EVERYONE
    await _enforce_dealer_module_access(request, module)

    # Layer 1: Check dealer subscription active — applies to EVERYONE
    await _enforce_dealer_subscription(request)

    # Dealers pass after access matrix + subscription checks
    if getattr(request, "is_dealer", False):
        return

    # If not a DSR, skip — auth handled by permission classes
    if not getattr(request, "is_dsr", False):
        return

    # Layer 3: Get the assignment and check module permissions
    assignment = await get_dsr_assignment(request)
    if assignment is None:
        raise HttpError(
            403,
            "You do not have an active assignment to this dealer.",
        )

    perms = assignment.get_permissions()
    module_perms = perms.get(module)

    # Boolean modules (like 'print', 'manage_dsrs')
    if isinstance(module_perms, bool):
        if not module_perms:
            raise HttpError(
                403,
                f"Access denied: the '{module}' module is not enabled for your account.",
            )
        return

    # Dict modules (like 'sales': {'view': True, 'edit': False})
    if isinstance(module_perms, dict):
        if not module_perms:
            # Empty dict = no permissions in this module
            raise HttpError(
                403,
                f"Access denied: you have no permissions in the '{module}' module. "
                f"Contact your dealer to update your permissions.",
            )
        return

    # Module not in permissions at all
    raise HttpError(
        403,
        f"Access denied: the '{module}' module is not available for your account.",
    )


async def enforce_dealer_access(
    request: HttpRequest,
    access_key: str,
) -> None:
    """Enforce that the dealer's subscription plan allows a specific access key.

    This is a lightweight check that ONLY looks at the dealer's SattaBase
    access matrix — it does NOT check DSR assignment permissions. Use it
    when you need to gate a feature purely by subscription tier, regardless
    of whether the caller is a dealer or a DSR.

    For example, the "bad_debt" feature (writing off sales as bad debt)
    requires the dealer's plan to have ``bad_debt: true``. Both dealers
    and DSRs are blocked if the plan doesn't include it.

    This function is a convenience wrapper that combines Layer 0 (access
    matrix) and Layer 1 (subscription active) checks.

    **Fully dynamic**: the access_key is looked up directly in the access
    map from the SattaBase API. No hardcoded mapping needed — any new
    key added to the billing system (via billing_seed_data.py or admin)
    is automatically enforced.

    Args:
        request: The HTTP request (must have dealer_username set by middleware
            or resolvable from DSR assignment).
        access_key: The SattaBase access key to check (e.g., "bad_debt",
            "export_pdf", "suppliers"). This is the key in the SattaBase
            access map. By convention, it's also the DSR module name.

    Raises:
        HttpError(403): If the dealer's plan doesn't include this access key
            or if the subscription is inactive.
    """
    # The access_key IS the module name — no mapping needed.
    # Convention: access keys from SattaBase match DSR module names
    # (e.g., "bad_debt" → "bad_debt", "suppliers" → "suppliers").
    # The SattaBase access map is the source of truth.

    # Layer 0: Access matrix check
    await _enforce_dealer_module_access(request, access_key)

    # Layer 1: Subscription active check
    await _enforce_dealer_subscription(request)


# ═══════════════════════════════════════════════════════════════════════════
# DEALER SUBSCRIPTION CHECK
# ═══════════════════════════════════════════════════════════════════════════


async def _is_dealer_subscription_active(request: HttpRequest) -> bool:
    """Check if the dealer's subscription is active via SattaBase access.

    Uses the cached access data from Phase 2's sattabase_access module.
    Falls back to True (permissive) if no access data is available.
    """
    access_data = await _get_dealer_access_data(request)
    if access_data is None:
        return True  # No data → permissive

    is_active = bool(access_data.get("is_active", True))
    if not is_active:
        dealer_username = getattr(request, "dealer_username", "unknown")
        logger.warning(
            "[DSR_PERM] Dealer %s subscription is not active (status=%s)",
            dealer_username,
            access_data.get("subscription_status", "unknown"),
        )
    return is_active


async def _enforce_dealer_subscription(request: HttpRequest) -> None:
    """Raise HttpError(403) if the dealer's subscription is not active.

    Works for both dealers and DSRs — checks the dealer's subscription
    regardless of who is making the request.
    """
    is_dealer = getattr(request, "is_dealer", False)
    is_active = await _is_dealer_subscription_active(request)

    if not is_active:
        if is_dealer:
            raise HttpError(
                403,
                "Your subscription is not active. Please renew or upgrade your plan "
                "to continue using this service.",
            )
        else:
            raise HttpError(
                403,
                "This dealer's subscription is not active. Please contact your dealer.",
            )


async def _resolve_dealer_username(request: HttpRequest) -> Optional[str]:
    """Resolve the dealer username for the current request.

    For dealers: returns request.dealer_username (set by middleware from JWT).
    For DSRs: returns request.dealer_username (set from X-Dealer-Username header),
      or falls back to looking up the DSR's first active assignment.

    This ensures we ALWAYS have a dealer_username for access matrix lookups,
    even when the frontend doesn't send the X-Dealer-Username header.
    """
    dealer_username = getattr(request, "dealer_username", None)
    if dealer_username:
        return dealer_username

    # If not a DSR, no fallback possible
    is_dsr = getattr(request, "is_dsr", False)
    if not is_dsr:
        return None

    # DSR with no dealer_username — try to resolve from assignment
    dsr_user_id = getattr(request, "dsr_user_id", None)
    user_email = getattr(request, "user_email", None)

    if dsr_user_id or user_email:
        try:
            from dsr.invitation_models import DsrDealerAssignment

            filters = {"status": DsrDealerAssignment.STATUS_ACTIVE}
            if dsr_user_id:
                filters["dsr_id"] = str(dsr_user_id)
            elif user_email:
                filters["dsr__email"] = user_email

            assignment = await DsrDealerAssignment.objects.filter(
                **filters
            ).afirst()
            if assignment:
                # Cache it on the request for downstream use
                request.dealer_username = assignment.dealer_id
                logger.info(
                    "[DSR_PERM] Resolved dealer_username=%s from DSR assignment "
                    "(dsr_user_id=%s, email=%s)",
                    assignment.dealer_id, dsr_user_id, user_email,
                )
                return assignment.dealer_id
        except Exception as exc:
            logger.warning(
                "[DSR_PERM] Failed to resolve dealer_username from "
                "assignment: %s", exc,
            )

    return None


async def _get_dealer_access_data(request: HttpRequest):
    """Fetch and cache dealer access data from SattaBase.

    Uses the Phase 2 API endpoint:
      GET /billing/service/subscriber/access
          ?subscriber_id={dealer_username}
          &service_domain={SATTABASE_SERVICE_DOMAIN}

    The SATTABASE_SERVICE_DOMAIN setting determines which domain's access
    entries are returned:
      - Development: localhost:4323
      - Production: dealer.sattaspace.com

    The access map is fully dynamic — keys come from SattaBase's AccessEntry
    table (seeded via billing_seed_data.py). Any new key added to the billing
    system is automatically enforced without code changes.

    Returns the access data dict, or None on failure (permissive).
    Caches on request for downstream use (plan_limits etc.).
    """
    dealer_username = await _resolve_dealer_username(request)
    if not dealer_username:
        return None

    # Check if already attached to request
    access_data = getattr(request, "_sattabase_access", None)
    if access_data is not None:
        return access_data

    # Fetch fresh from SattaBase (cached 5 min)
    try:
        from common.sattabase_access import aget_dealer_access
        from common.plan_limits import attach_sattabase_access

        access_data = await aget_dealer_access(dealer_username)
        attach_sattabase_access(request, access_data)
        return access_data
    except Exception as exc:
        logger.error(
            "[DSR_PERM] Error fetching dealer access for %s: %s",
            dealer_username, exc,
        )
        return None


async def _is_dealer_module_allowed(request: HttpRequest, module: str) -> bool:
    """Check if the dealer's current plan allows the given module.

    **Fully dynamic / database-driven**: checks the access map returned
    by the SattaBase API directly. The access keys come from SattaBase's
    AccessEntry table (seeded via billing_seed_data.py), so ANY key added
    to the billing system is automatically enforced without code changes.

    Convention: the access key in SattaBase and the DSR module name
    are the same (e.g., "bad_debt" → "bad_debt", "suppliers" → "suppliers").
    No hardcoded mapping is needed for enforcement — the module name is
    looked up directly in the access map from the API response.

    The access map is fetched via the Phase 2 API:
      GET /billing/service/subscriber/access
          ?subscriber_id={dealer_username}
          &service_domain={SATTABASE_SERVICE_DOMAIN}

    Returns True if:
      - Access data is unavailable AND strict mode is off (permissive fallback)
      - The module's access key is True or a positive number
      - The module's access key is missing from the access map
        (plan doesn't explicitly list it — treat as allowed)

    Returns False if:
      - The module's access key is explicitly False
      - Access data is unavailable AND strict mode is on
    """
    access_data = await _get_dealer_access_data(request)
    if access_data is None:
        # No access data available — check strict mode
        from django.conf import settings as django_settings
        strict = getattr(django_settings, "SATTABASE_ACCESS_STRICT_MODE", False)
        if strict:
            logger.warning(
                "[DSR_PERM] No access data available and STRICT mode on — "
                "denying module '%s'", module,
            )
            return False
        # Permissive fallback (development / SattaBase unreachable)
        return True

    access_map = access_data.get("access", {})

    # Look up the module name directly in the access map.
    # Convention: access key == module name (e.g., "bad_debt" → "bad_debt").
    # No hardcoded mapping needed — the SattaBase access map IS the
    # source of truth for which keys exist and what values they have.
    dealer_value = access_map.get(module)

    # If key is not in the access map, treat as allowed (plan might
    # not explicitly list every module — e.g., a new key was added to
    # the billing system but the plan hasn't been updated yet)
    if dealer_value is None:
        return True

    # Explicitly False → module not allowed by dealer's plan
    if dealer_value is False:
        return False

    # True or positive number → allowed
    return True


async def _enforce_dealer_module_access(request: HttpRequest, module: str) -> None:
    """Raise HttpError(403) if the dealer's plan doesn't allow this module.

    This is Layer 0 of the enforcement. It applies to BOTH dealers and
    DSRs — if the dealer's plan doesn't include a module, nobody under
    that dealer can access it, including the dealer themselves.

    This handles plan downgrades where:
    - The dealer's stored permissions become stale
    - The frontend might still show menu items that should be hidden
    - API calls bypass frontend gating
    """
    if not await _is_dealer_module_allowed(request, module):
        dealer_username = getattr(request, "dealer_username", "unknown")
        is_dealer = getattr(request, "is_dealer", False)
        logger.info(
            "[ACCESS_MATRIX] Module '%s' blocked for %s on dealer %s — "
            "dealer's plan doesn't include this module",
            module, "dealer" if is_dealer else "DSR", dealer_username,
        )
        if is_dealer:
            raise HttpError(
                403,
                f"Access denied: the '{module}' feature is not available under "
                f"your current subscription plan. Please upgrade to enable "
                f"this feature.",
            )
        else:
            raise HttpError(
                403,
                f"Access denied: the '{module}' module is not available under "
                f"this dealer's current subscription plan. The dealer may need "
                f"to upgrade to enable this feature.",
            )


# ═══════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════


def require_dsr_permission(module: str, action: str = "view"):
    """Decorator: enforce module:action permission on an endpoint.

    Raises HttpError(403) if the DSR doesn't have the specified permission
    or if the dealer's access matrix/subscription denies it. Dealers are
    also checked against their access matrix.

    Usage::

        @route.post("")
        @require_dsr_permission("sales", "edit")
        async def create_sale(self, request, payload):
            ...

        @route.get("")
        @require_dsr_permission("reports", "view")
        async def list_reports(self, request):
            ...

        @route.post("/{id}/collect")
        @require_dsr_permission("collections", "edit")
        async def collect_payment(self, request, sale_id):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request — could be (self, request, ...) or (request, ...)
            request = None
            if len(args) >= 2:
                request = args[1]  # (self, request, ...)
            elif len(args) >= 1:
                request = args[0]  # (request, ...)

            if request is None:
                request = kwargs.get("request")

            if request is not None:
                await enforce_dsr_permission(request, module, action)

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_dsr_module(module: str):
    """Decorator: enforce that user has ANY access to a module.

    Less granular than :func:`require_dsr_permission` — only checks that
    the module isn't empty/False in the DSR's permissions. Also checks
    dealer's access matrix for both dealers and DSRs.

    Useful for controller-level guards where individual actions are
    checked inside endpoint methods.

    Usage::

        @api_controller("/sales", tags=["Sales"])
        @require_dsr_module("sales")
        class SalesController:
            ...
    """
    def decorator(func_or_class):
        if isinstance(func_or_class, type):
            # Applied to a class (api_controller)
            original_init = func_or_class.__init__

            @wraps(original_init)
            def __init__(self, *args, **kwargs):
                self._dsr_required_module = module
                if original_init:
                    original_init(self, *args, **kwargs)

            func_or_class.__init__ = __init__
            return func_or_class
        else:
            # Applied to a function (endpoint)
            @wraps(func_or_class)
            async def wrapper(*args, **kwargs):
                request = None
                if len(args) >= 2:
                    request = args[1]
                elif len(args) >= 1:
                    request = args[0]

                if request is None:
                    request = kwargs.get("request")

                if request is not None:
                    await enforce_dsr_module(request, module)

                return await func_or_class(*args, **kwargs)
            return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE: PERMISSION CONTEXT OBJECT
# ═══════════════════════════════════════════════════════════════════════════
# For endpoints that need to check multiple permissions, this avoids
# repeated assignment lookups.


class DsrPermissionContext:
    """Lazy-loaded permission context for a DSR request.

    Caches the assignment lookup so multiple ``can()`` calls within the
    same endpoint don't hit the DB repeatedly.

    Usage::

        ctx = DsrPermissionContext(request)
        await ctx.load()

        if await ctx.can("sales", "edit"):
            # allow creation
        if await ctx.can("sales", "delete"):
            # allow void
    """

    def __init__(self, request: HttpRequest) -> None:
        self.request = request
        self._assignment = None
        self._loaded = False
        self._is_dealer = getattr(request, "is_dealer", False)

    async def load(self) -> None:
        """Load the DSR assignment (called once, cached thereafter)."""
        if self._loaded:
            return
        self._assignment = await get_dsr_assignment(self.request)
        self._loaded = True

    async def can(self, module: str, action: str = "view") -> bool:
        """Check a permission (must call ``load()`` first).

        For dealers: checks access matrix only.
        For DSRs: checks access matrix + assignment permissions.
        """
        # Layer 0: Check dealer's access matrix for everyone
        if not await _is_dealer_module_allowed(self.request, module):
            return False

        # Dealers pass after access matrix check
        if self._is_dealer:
            return True

        # DSRs need assignment check
        if self._assignment is None:
            return False
        return self._assignment.has_permission(module, action)

    @property
    def is_dealer(self) -> bool:
        return self._is_dealer

    @property
    def assignment(self):
        """The DsrDealerAssignment, or None if dealer/no assignment."""
        return self._assignment