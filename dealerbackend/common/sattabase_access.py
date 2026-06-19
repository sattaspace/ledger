"""
DEALERCORE v3.0 — SattaBase Access Client
-------------------------------------------
Server-to-service client that queries SattaBase's subscriber-access endpoint
to discover what a dealer's subscription plan allows.

This module bridges the two permission systems:
  - SattaBase Access Matrix (plan-level, dealer-wide)
  - DealerBackend DSR Permissions (per-DSR, per-dealer)

The core principle: **DSR permissions can never exceed what the dealer's
subscription allows.** If the dealer's plan says `suppliers: false`, no
DSR under that dealer can be granted suppliers access.

IMPORTANT: Access keys are DYNAMIC — they come from SattaBase's AccessEntry
table (seeded via billing_seed_data.py). This module does NOT hardcode
access key names for enforcement. Instead, it uses the access map returned
by SattaBase directly. Any new key added to the billing system is
automatically enforced without code changes.

The ACCESS_TO_DSR_MODULE_MAP below is only used for:
  1. constrain_dsr_permissions() — determines HOW to strip DSR permissions
     (strip vs zero_nested) when a dealer's access is False
  2. get_dealer_limit() — identifies which keys are integer limits
  3. _restrictive_fallback() — builds a "deny all" fallback in strict mode

For enforcement (should this module be allowed?), the access map from
SattaBase is consulted directly via the module name as the access key.

Usage
-----
    from common.sattabase_access import SattaBaseAccessClient

    client = SattaBaseAccessClient()

    # Fetch dealer's access matrix (cached for 5 min)
    access = await client.aget_dealer_access(dealer_username)

    # Constrain proposed DSR permissions
    constrained = client.constrain_dsr_permissions(
        proposed_permissions={"suppliers": {"view": True}, "sales": {"view": True}},
        dealer_access=access,
    )
    # → {"suppliers": {}, "sales": {"view": True}}

    # Check if dealer subscription is active
    if not access.get("is_active"):
        raise HttpError(403, "Dealer subscription is not active")

Architecture
------------
    ┌───────────────────┐        ┌───────────────────────┐
    │  DealerBackend    │  HTTP  │  SattaBase            │
    │  sattabase_access │ ────→  │  /billing/service/    │
    │  .py              │        │   subscriber/access   │
    └───────────────────┘        └───────────────────────┘
           │
           ▼
    ┌───────────────────┐
    │  In-memory cache  │  TTL: 300s (configurable)
    │  _access_cache    │
    └───────────────────┘
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx
from django.conf import settings
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# IN-MEMORY CACHE
# ═══════════════════════════════════════════════════════════════════════════
# Keyed by subscriber_id (dealer_username). Each entry stores the response
# dict plus a `__fetched_at` timestamp. Entries older than TTL are
# considered stale and refetched.

_access_cache: Dict[str, Dict[str, Any]] = {}


def _cache_key(subscriber_id: str) -> str:
    """Normalise subscriber_id for cache lookup."""
    return str(subscriber_id)


def _is_cache_entry_fresh(entry: Dict[str, Any], ttl: int) -> bool:
    """Return True if the cache entry is still within TTL."""
    fetched_at = entry.get("__fetched_at", 0)
    return (time.monotonic() - fetched_at) < ttl


def invalidate_cache(subscriber_id: Optional[str] = None) -> None:
    """Remove cached access data.

    Args:
        subscriber_id: If given, invalidate only that entry.
                       Otherwise, clear the entire cache.
    """
    if subscriber_id:
        _access_cache.pop(_cache_key(subscriber_id), None)
    else:
        _access_cache.clear()


# ═══════════════════════════════════════════════════════════════════════════
# DSR PERMISSION CONSTRAINT HINTS
# ═══════════════════════════════════════════════════════════════════════════
# This map is ONLY used by constrain_dsr_permissions() to determine HOW
# to strip DSR permissions when a dealer's access is False. It is NOT
# used for enforcement — that's done by checking the access map directly.
#
# Access keys are dynamic (from SattaBase's AccessEntry table). This map
# only provides "rule hints" for known keys. Unknown keys default to
# "zero_nested" (safest default for nested permission dicts).
#
# Structure: {
#   <access_key>: {
#     "dsr_module": <module_name in DsrDealerAssignment.permissions>,
#                   Usually same as access_key. Only differs when the
#                   SattaBase access key and DSR module name diverge.
#     "rule": "strip" | "zero_nested" | "limit",
#     "description": ...
#   }
# }
#
# Rules:
#   - "strip": If access value is falsy, remove the entire module key
#     from DSR permissions (for simple boolean modules like `print`).
#   - "zero_nested": If access value is falsy, replace the module value
#     with an empty dict `{}` (for nested modules like `suppliers: {view: True}`).
#   - "limit": The access value is an integer cap. Applied to plan_limits,
#     not DSR permissions directly.

ACCESS_TO_DSR_MODULE_MAP: Dict[str, Dict[str, Any]] = {
    # Rule hints for known access keys — these determine HOW to constrain
    # DSR permissions, not WHETHER to enforce them. Enforcement is driven
    # by the access map from SattaBase.
    "dashboard": {
        "dsr_module": "dashboard",
        "rule": "zero_nested",
    },
    "inventory": {
        "dsr_module": "inventory",
        "rule": "zero_nested",
    },
    "sales": {
        "dsr_module": "sales",
        "rule": "zero_nested",
    },
    "collections": {
        "dsr_module": "collections",
        "rule": "zero_nested",
    },
    "bad_debt": {
        "dsr_module": "bad_debt",
        "rule": "zero_nested",
    },
    "suppliers": {
        "dsr_module": "suppliers",
        "rule": "zero_nested",
    },
    "reports": {
        "dsr_module": "reports",
        "rule": "zero_nested",
    },
    "print": {
        "dsr_module": "print",
        "rule": "strip",
    },
    "manage_dsrs": {
        "dsr_module": "manage_dsrs",
        "rule": "strip",
    },
    "export_pdf": {
        "dsr_module": "export_pdf",
        "rule": "strip",
    },
    # Additional keys from billing_seed_data.py — these are auto-enforced
    # by the access map lookup. The rule hints here only affect how
    # constrain_dsr_permissions() strips DSR permissions.
    "api_access": {
        "dsr_module": "api_access",
        "rule": "strip",
    },
    "ai_insights": {
        "dsr_module": "ai_insights",
        "rule": "strip",
    },
    # Limit keys (integer caps, not DSR module permissions)
    "max_dsrs": {
        "dsr_module": None,
        "rule": "limit",
    },
    "max_products": {
        "dsr_module": None,
        "rule": "limit",
    },
    "max_suppliers": {
        "dsr_module": None,
        "rule": "limit",
    },
    "data_retention_days": {
        "dsr_module": None,
        "rule": "limit",
    },
}


def _get_rule_for_key(access_key: str) -> str:
    """Get the constraint rule for an access key.

    Returns the rule from ACCESS_TO_DSR_MODULE_MAP if the key is known,
    otherwise defaults to "zero_nested" (safest default for unknown keys).
    """
    mapping = ACCESS_TO_DSR_MODULE_MAP.get(access_key)
    if mapping:
        return mapping.get("rule", "zero_nested")
    return "zero_nested"


def _get_dsr_module_for_key(access_key: str) -> str:
    """Get the DSR module name for an access key.

    Returns the dsr_module from ACCESS_TO_DSR_MODULE_MAP if defined,
    otherwise returns the access_key itself (convention: they're the same).
    """
    mapping = ACCESS_TO_DSR_MODULE_MAP.get(access_key)
    if mapping and mapping.get("dsr_module"):
        return mapping["dsr_module"]
    return access_key


# ═══════════════════════════════════════════════════════════════════════════
# CLIENT CLASS
# ═══════════════════════════════════════════════════════════════════════════


class SattaBaseAccessClient:
    """Async client for querying SattaBase's subscriber-access endpoint.

    Features:
      - In-memory caching with configurable TTL
      - Automatic constraint of DSR permissions against dealer access
      - Graceful fallback when SattaBase is unreachable
      - Structured logging for debugging

    Example::

        client = SattaBaseAccessClient()
        access = await client.aget_dealer_access("dealer123")
        if not access.get("is_active"):
            raise HttpError(403, "Subscription inactive")
        constrained = client.constrain_dsr_permissions(proposed, access)
    """

    def __init__(self) -> None:
        self._base_url = getattr(settings, "SATTABASE_API_BASE_URL", "http://localhost:8086/api/v1")
        self._api_key = getattr(settings, "SATTABASE_API_KEY", "")
        # SATTABASE_API_KEY is set in settings.py from the env var
        # SATTABASE_API_KEY_FOR_DEALER (named per-sister-domain so future
        # sister domains can have their own keys in the same .env file).
        self._service_domain = getattr(settings, "SATTABASE_SERVICE_DOMAIN", "localhost:4323")
        self._cache_ttl = getattr(settings, "SATTABASE_ACCESS_CACHE_TTL", 300)
        self._strict_mode = getattr(settings, "SATTABASE_ACCESS_STRICT_MODE", False)

    # ── Fetch ─────────────────────────────────────────────────────────────

    async def aget_dealer_access(self, subscriber_id: str) -> Dict[str, Any]:
        """Fetch a dealer's access matrix from SattaBase (with caching).

        Returns a dict matching ``SubscriberAccessResponseSchema``:
        ::
            {
                "subscriber_id": "1",
                "service_domain": "localhost:4323",
                "subscription_status": "active",
                "is_active": True,
                "plan_slug": "standard",
                "plan_name": "Standard",
                "access": {"dashboard": True, "suppliers": False, ...}
            }

        The ``access`` dict is dynamic — its keys come from SattaBase's
        AccessEntry table (seeded via billing_seed_data.py). Any new
        access key added to the billing system is automatically enforced.

        On SattaBase failure, returns a **permissive fallback** so that
        DealerBackend keeps working (same philosophy as plan_limits.py).
        The fallback marks ``is_active=True`` and returns an empty access
        map, which means no constraints are applied. A loud warning is
        logged so ops can fix the connectivity issue.

        Failures are NOT cached — only successful SattaBase responses
        are cached. This ensures the next request immediately retries
        once connectivity is restored (e.g., after fixing a missing
        X-Service-Domain header).
        """
        cache_key = _cache_key(subscriber_id)

        # 1. Check cache
        cached = _access_cache.get(cache_key)
        if cached and _is_cache_entry_fresh(cached, self._cache_ttl):
            logger.debug("[SattaBaseAccess] Cache hit for subscriber %s", subscriber_id)
            return cached

        # 2. Fetch from SattaBase
        logger.info("[SattaBaseAccess] Fetching access for subscriber %s", subscriber_id)
        result, was_success = await self._fetch_from_sattabase(subscriber_id)

        # 3. Only cache SUCCESSFUL responses. Caching failures would
        # mean a transient SattaBase outage / misconfigured header keeps
        # returning the fallback for `cache_ttl` seconds even after the
        # underlying issue is fixed. Skip caching on failure so the next
        # request retries immediately.
        if was_success:
            result["__fetched_at"] = time.monotonic()
            _access_cache[cache_key] = result

        return result

    async def _fetch_from_sattabase(self, subscriber_id: str) -> tuple[Dict[str, Any], bool]:
        """Make the HTTP call to SattaBase.

        Returns
        -------
        (result, was_success)
            ``result`` is the parsed JSON response on success, or a
            permissive/restrictive fallback dict on any failure.
            ``was_success`` is True only when SattaBase returned HTTP 200
            with a valid access payload. Failures (404, 5xx, timeout,
            missing API key, network error) return ``was_success=False``
            so the caller can skip caching them.
        """
        if not self._api_key:
            if self._strict_mode:
                logger.warning(
                    "[SattaBaseAccess] SATTABASE_API_KEY not configured AND "
                    "SATTABASE_ACCESS_STRICT_MODE=True — using restrictive "
                    "fallback. ALL gated modules will be DENIED."
                )
                return self._restrictive_fallback(subscriber_id), False
            else:
                logger.warning(
                    "[SattaBaseAccess] SATTABASE_API_KEY not configured — "
                    "using permissive fallback. DSR permissions will NOT be "
                    "constrained by dealer subscription. Set SATTABASE_API_KEY "
                    "in environment to enable enforcement."
                )
                return self._permissive_fallback(subscriber_id), False

        # SattaBase's middleware REQUIRES both X-API-Key and X-Service-Domain
        # headers (the X-Service-Domain must match the domain bound to the
        # API key's ServiceCredential record). Passing service_domain as a
        # URL query param is NOT enough — the middleware rejects with 400
        # "X-Service-Domain header is required when X-API-Key is provided".
        # We send it in BOTH the header (required) and the query string
        # (kept for backward compat with older SattaBase deployments).
        url = (
            f"{self._base_url}/billing/service/subscriber/access"
            f"?subscriber_id={subscriber_id}"
            f"&service_domain={self._service_domain}"
        )
        headers = {
            "X-API-Key": self._api_key,
            "X-Service-Domain": self._service_domain,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                logger.info(
                    "[SattaBaseAccess] Successfully fetched access for %s "
                    "(plan=%s, status=%s)",
                    subscriber_id,
                    data.get("plan_slug"),
                    data.get("subscription_status"),
                )
                return data, True

            if response.status_code == 404:
                # In strict mode, treat 404 as subscription inactive
                # In development without strict mode, be permissive (is_active=True)
                # In production without strict mode, treat as inactive (is_active=False)
                #
                # NOTE: A 404 can mean either (a) the subscriber genuinely
                # doesn't exist, OR (b) the API key / X-Service-Domain
                # headers are wrong and SattaBase's middleware returned a
                # 404-shaped rejection. We treat both as failure (was_success=False)
                # so we don't cache a possibly-wrong fallback.
                if self._strict_mode:
                    logger.warning(
                        "[SattaBaseAccess] Subscriber %s not found in "
                        "SattaBase — STRICT MODE: treating as inactive",
                        subscriber_id,
                    )
                    return self._restrictive_fallback(subscriber_id, is_active=False), False

                if getattr(settings, "DEBUG", False):
                    # Development: permissive — subscriber may not be in
                    # SattaBase yet (e.g., dealer created locally but not
                    # synced to SattaBase). Don't block DSRs from working.
                    logger.warning(
                        "[SattaBaseAccess] Subscriber %s not found in "
                        "SattaBase — using permissive fallback (DEBUG=True, "
                        "is_active=True). The dealer may not be registered "
                        "in SattaBase yet. NOTE: also check X-API-Key and "
                        "X-Service-Domain headers.",
                        subscriber_id,
                    )
                    return self._permissive_fallback(subscriber_id, is_active=True), False
                else:
                    # Production: subscriber not found = no subscription = inactive
                    logger.warning(
                        "[SattaBaseAccess] Subscriber %s not found in "
                        "SattaBase — subscription inactive (production mode)",
                        subscriber_id,
                    )
                    return self._permissive_fallback(subscriber_id, is_active=False), False

            # 400 (missing X-Service-Domain header) or 5xx — log loudly
            # because these are configuration issues, not normal operation.
            logger.error(
                "[SattaBaseAccess] Unexpected status %d from SattaBase: %s "
                "— verify X-API-Key, X-Service-Domain, and SATTABASE_API_BASE_URL.",
                response.status_code,
                response.text[:200],
            )
            return self._permissive_fallback(subscriber_id), False

        except httpx.TimeoutException:
            logger.error(
                "[SattaBaseAccess] Timeout fetching access for %s",
                subscriber_id,
            )
            if self._strict_mode:
                return self._restrictive_fallback(subscriber_id), False
            return self._permissive_fallback(subscriber_id), False

        except httpx.ConnectError:
            logger.error(
                "[SattaBaseAccess] Connection error to SattaBase at %s",
                self._base_url,
            )
            if self._strict_mode:
                return self._restrictive_fallback(subscriber_id), False
            return self._permissive_fallback(subscriber_id), False

        except Exception as exc:
            logger.error(
                "[SattaBaseAccess] Unexpected error fetching access for %s: %s",
                subscriber_id,
                exc,
            )
            if self._strict_mode:
                return self._restrictive_fallback(subscriber_id), False
            return self._permissive_fallback(subscriber_id), False

    def _permissive_fallback(
        self, subscriber_id: str, is_active: bool = True
    ) -> Dict[str, Any]:
        """Return a permissive fallback when SattaBase is unreachable.

        When ``is_active=True`` (default), the fallback allows everything
        so existing functionality keeps working. When ``is_active=False``
        (subscriber not found), the fallback denies access.

        IMPORTANT: The permissive fallback with ``is_active=True`` and empty
        ``access`` dict means NO module constraints are applied — every module
        is treated as allowed. Use ``SATTABASE_ACCESS_STRICT_MODE=True`` to
        switch to restrictive fallback instead.
        """
        return {
            "subscriber_id": subscriber_id,
            "service_domain": self._service_domain,
            "subscription_status": "unknown" if is_active else "none",
            "is_active": is_active,
            "plan_slug": None,
            "plan_name": None,
            "access": {},
        }

    def _restrictive_fallback(
        self, subscriber_id: str, is_active: bool = False
    ) -> Dict[str, Any]:
        """Return a restrictive fallback when SattaBase is unreachable.

        When ``SATTABASE_ACCESS_STRICT_MODE=True`` and SattaBase cannot be
        reached (no API key, timeout, connection error, 404), this fallback
        sets ``is_active=False`` so that subscription checks block access,
        and includes an empty access map (all modules denied by default
        because _is_dealer_module_allowed treats missing keys as allowed
        only when access data IS available).

        The key insight: with ``is_active=False``, the subscription check
        alone blocks all access. We don't need to enumerate every possible
        access key — the subscription check is the gate.
        """
        return {
            "subscriber_id": subscriber_id,
            "service_domain": self._service_domain,
            "subscription_status": "inactive" if not is_active else "unknown_strict",
            "is_active": is_active,
            "plan_slug": None,
            "plan_name": None,
            "access": {},
        }

    # ── Constrain ─────────────────────────────────────────────────────────

    def constrain_dsr_permissions(
        self,
        proposed_permissions: Dict[str, Any],
        dealer_access: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Constrain DSR permissions to not exceed dealer's access.

        Iterates over the access map from SattaBase. For each key where
        the dealer's access is ``False``, the corresponding DSR permission
        is stripped or zeroed. The constraint rule (strip vs zero_nested)
        comes from ACCESS_TO_DSR_MODULE_MAP for known keys, or defaults
        to "zero_nested" for unknown keys.

        This is database-driven — if a new access key is added to SattaBase
        (e.g., "ai_insights"), it will automatically be constrained here
        without any code changes.

        Args:
            proposed_permissions: The permissions dict the dealer wants to
                assign (e.g. ``{"suppliers": {"view": True}, "sales": {"view": True}}``).
            dealer_access: The access dict from ``aget_dealer_access()``
                (the full response including the ``access`` key).

        Returns:
            A new permissions dict with disallowed modules removed/zeroed.

        Example::

            >>> client.constrain_dsr_permissions(
            ...     {"suppliers": {"view": True}, "sales": {"view": True}},
            ...     {"access": {"suppliers": False, "sales": True}, ...},
            ... )
            {"suppliers": {}, "sales": {"view": True}}
        """
        # Defensive copy — never mutate the input
        constrained = dict(proposed_permissions)
        access_map = dealer_access.get("access", {})

        # Iterate over the ACCESS MAP (database-driven), not the
        # ACCESS_TO_DSR_MODULE_MAP (hardcoded). This way, any new
        # access key added to SattaBase is automatically constrained.
        for access_key, dealer_value in access_map.items():
            # Skip limits — they don't affect DSR permissions directly
            rule = _get_rule_for_key(access_key)
            if rule == "limit":
                continue

            # Get the DSR module name (usually same as access_key)
            dsr_module = _get_dsr_module_for_key(access_key)

            # Only constrain if the module exists in proposed permissions
            if dsr_module not in constrained:
                continue

            # If dealer has True or a positive value, no constraint needed
            if dealer_value is True or (isinstance(dealer_value, (int, float)) and dealer_value > 0):
                continue

            # If dealer has False, apply constraint
            if dealer_value is False:
                if rule == "strip":
                    del constrained[dsr_module]
                    logger.info(
                        "[SattaBaseAccess] Stripped DSR module '%s' "
                        "(dealer access '%s' is False)",
                        dsr_module, access_key,
                    )
                else:
                    # zero_nested (default for unknown keys)
                    constrained[dsr_module] = {}
                    logger.info(
                        "[SattaBaseAccess] Constrained DSR module '%s' → {} "
                        "(dealer access '%s' is False)",
                        dsr_module, access_key,
                    )

        return constrained

    def get_dealer_limit(self, dealer_access: Dict[str, Any], limit_key: str) -> Optional[int]:
        """Get a numeric plan limit from dealer's access map.

        Args:
            dealer_access: The access dict from ``aget_dealer_access()``.
            limit_key: One of "max_dsrs", "max_products", "max_suppliers",
                or any other integer limit key in the access map.

        Returns:
            The integer limit, or None if not configured (unlimited).
            Convention: 0 means "unlimited".
        """
        access_map = dealer_access.get("access", {})
        value = access_map.get(limit_key)
        if isinstance(value, (int, float)):
            return int(value)
        return None

    def is_dealer_subscription_active(self, dealer_access: Dict[str, Any]) -> bool:
        """Check if dealer's subscription is active (active or trialing).

        Args:
            dealer_access: The access dict from ``aget_dealer_access()``.

        Returns:
            True if the subscription is active or trialing.
        """
        return bool(dealer_access.get("is_active", False))

    def get_violations(
        self,
        proposed_permissions: Dict[str, Any],
        dealer_access: Dict[str, Any],
    ) -> list[str]:
        """Return human-readable list of permission violations.

        Useful for returning to the dealer in API error responses so they
        know *why* certain permissions were stripped.

        Database-driven — iterates over the access map from SattaBase,
        not a hardcoded list.

        Args:
            proposed_permissions: The permissions the dealer tried to assign.
            dealer_access: The dealer's access data from SattaBase.

        Returns:
            List of violation descriptions, empty if no violations.
        """
        violations: list[str] = []
        access_map = dealer_access.get("access", {})

        for access_key, dealer_value in access_map.items():
            rule = _get_rule_for_key(access_key)
            if rule == "limit":
                continue

            dsr_module = _get_dsr_module_for_key(access_key)

            if dsr_module not in proposed_permissions:
                continue

            if dealer_value is False:
                violations.append(
                    f"Module '{dsr_module}' is not available in your current "
                    f"plan (access key: '{access_key}' is disabled). "
                    f"Please upgrade to enable this feature."
                )

        return violations


# ═══════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

# Module-level singleton — re-used across requests to share the cache.
_client: Optional[SattaBaseAccessClient] = None


def get_access_client() -> SattaBaseAccessClient:
    """Return the module-level SattaBaseAccessClient singleton."""
    global _client
    if _client is None:
        _client = SattaBaseAccessClient()
    return _client


async def aget_dealer_access(subscriber_id: str) -> Dict[str, Any]:
    """Convenience: fetch dealer access using the module singleton.

    Passes ``subscriber_id`` straight through to SattaBase's
    ``/billing/service/subscriber/access`` endpoint, which already does
    pk → username → email lookup.

    IMPORTANT NAMING CONTEXT
    ------------------------
    In DealerBackend, ``DealerConfig.username`` is a vestigial name — its
    actual value is ``str(SattaBase.User.pk)`` (e.g. ``"1"``, ``"42"``).
    The original design used real usernames; that design was dropped and
    the field was repurposed to hold the SattaBase user PK, but the
    column was never renamed. As a result every call site that passes
    ``dealer.username`` is actually passing a SattaBase user PK.

    That's fine for SattaBase's subscriber-access API — the pk-lookup
    branch will find the user. So this function just passes the value
    through. No email resolution, no DealerConfig lookup, no special
    cases. Previous versions of this wrapper tried to "resolve" the
    dealer's email and pass that instead, which was unnecessary AND
    fragile (DealerConfig.email may not match the SattaBase login email
    in all cases). That complexity has been removed.
    """
    return await get_access_client().aget_dealer_access(str(subscriber_id))


def compute_effective_access(
    dealer_access_response: Dict[str, Any],
    dsr_permissions: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute the SINGLE effective access map for a DSR session.

    This is the AUTHORITATIVE intersection of two permission sources:

    1. **Dealer's plan-level access** (from SattaBase, dynamic keys from
       the AccessEntry table). If the plan says ``bad_debt: false``, NO
       user under this dealer can access bad_debt.
    2. **DSR's per-dealer permissions** (from DsrDealerAssignment). The
       DSR's role may further restrict what they can do, but can never
       exceed what the dealer's plan allows.

    The output is a FLAT map of primitives (bool / int / str) suitable
    for direct use by the frontend's ``setAccessMap()`` — which drops
    non-primitive values. Every module key in the returned map has a
    boolean-ish value: ``True`` for accessible, ``False`` for denied.
    Numeric plan limits (max_products, max_dsrs, ...) pass through as
    integers.

    For DSRs with ``manage_dsrs`` permission, the map includes
    ``manage_dsrs: True`` (since this is a DSR-only key not present in
    SattaBase). Otherwise it's set to ``False`` explicitly so the
    frontend's Team menu hides correctly.

    Returns
    -------
    dict
        Flat access map. Keys are module names (matching SattaBase
        access keys). Values are one of:
        - ``True`` / ``False`` — module visibility
        - ``int`` — plan limit (e.g. ``max_products: 100``)
        Always includes ``__subscription_active`` boolean metadata key.
    """
    dealer_access_map = dealer_access_response.get("access", {}) or {}
    is_active = bool(dealer_access_response.get("is_active", False))

    effective: Dict[str, Any] = {}

    if not is_active:
        # Subscription inactive — deny everything except dashboard (so
        # the user isn't stuck on a blank screen and can see a message).
        effective["dashboard"] = True
        effective["manage_dsrs"] = False
        effective["__subscription_active"] = False
        return effective

    effective["__subscription_active"] = True

    # Step 1: Copy dealer's plan-level access as the baseline.
    # This includes boolean flags (dashboard, suppliers, ...) AND
    # numeric limits (max_products, max_dsrs, ...). Pass everything
    # through — frontend uses hasAccess() for booleans and getLimit()
    # for numerics. Skip nested dicts (shouldn't appear in SattaBase
    # access map, but defensive).
    for key, value in dealer_access_map.items():
        # Skip the subscriber_id / metadata that SattaBase sometimes
        # nests inside the access map.
        if key in ("subscriber_id", "service_domain", "is_active",
                    "subscription_status", "plan_slug", "plan_name"):
            continue
        if isinstance(value, bool):
            effective[key] = value
        elif isinstance(value, (int, float)):
            # Numeric limits (max_products, max_dsrs, ...) — keep as int.
            # Boolean True/False are subclasses of int in Python, so we
            # check bool first above.
            effective[key] = int(value)
        elif isinstance(value, str):
            effective[key] = value

    # Step 2: Intersect with DSR's per-dealer permissions.
    # Rule: DSR permissions can only further RESTRICT, never expand.
    # - If dealer's plan denies a module (False or absent), it stays
    #   denied regardless of what the DSR's permissions say.
    # - If dealer's plan allows a module, the DSR's permissions decide
    #   the final visibility.
    # The frontend's setAccessMap() DROPS non-primitive values, so we
    # flatten nested dicts like {"view": true, "edit": false} into a
    # single boolean: True iff view=True (or the dict is truthy).
    for module, actions in (dsr_permissions or {}).items():
        if module == "manage_dsrs":
            # DSR-only key, not present in SattaBase. Honour the DSR's
            # assignment directly.
            if isinstance(actions, bool):
                effective["manage_dsrs"] = actions
            elif isinstance(actions, dict):
                effective["manage_dsrs"] = bool(actions.get("view", False))
            elif isinstance(actions, (int, float)):
                effective["manage_dsrs"] = bool(actions)
            else:
                effective["manage_dsrs"] = False
            continue

        # Flatten DSR permission value to a boolean
        if isinstance(actions, bool):
            dsr_allowed = actions
        elif isinstance(actions, dict):
            dsr_allowed = bool(actions.get("view", False))
        elif isinstance(actions, (int, float)):
            dsr_allowed = bool(actions)
        else:
            dsr_allowed = False

        if not dsr_allowed:
            # DSR explicitly denied — override to False
            effective[module] = False
        else:
            # DSR allows — but only if dealer's plan doesn't deny it.
            # If the key is absent from dealer's plan, treat as allowed
            # (key not yet in SattaBase AccessEntry table).
            if effective.get(module) is False:
                pass  # dealer denies — stays False
            else:
                effective[module] = True

    # Always set manage_dsrs explicitly so the frontend Team menu
    # gating works deterministically (frontend's hasAccess returns
    # false for absent keys, but being explicit avoids ambiguity).
    if "manage_dsrs" not in effective:
        effective["manage_dsrs"] = False

    return effective


def constrain_dsr_permissions(
    proposed_permissions: Dict[str, Any],
    dealer_access: Dict[str, Any],
) -> Dict[str, Any]:
    """Convenience: constrain DSR permissions using the module singleton."""
    return get_access_client().constrain_dsr_permissions(
        proposed_permissions, dealer_access
    )


def get_dealer_limit(dealer_access: Dict[str, Any], limit_key: str) -> Optional[int]:
    """Convenience: get plan limit using the module singleton."""
    return get_access_client().get_dealer_limit(dealer_access, limit_key)
