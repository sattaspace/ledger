"""
DEALERCORE — Plan Limits Enforcement
--------------------------------------
Server-side enforcement of subscription limits and feature flags.

Phase 2 Update: The resolution order now includes SattaBase access data:
  1. SattaBase access map (via sattabase_access client, cached 5 min)
  2. JWT `plan_limits` claim (SattaBase embeds this in the token)
  3. Permissive defaults (backward-compat until #1 and #2 ship)

The SattaBase access map is preferred because it's always fresh (up to
cache TTL) and authoritative — it's the same data source that the
/billing/auth/me endpoint returns to the frontend.

FIX DSR-020: Removed the X-Plan-Limits header fallback. Client-provided
headers can be manipulated to bypass limits.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.http import HttpRequest
from ninja.errors import HttpError


logger = logging.getLogger(__name__)

# Permissive fallback used when neither SattaBase access nor JWT
# plan_limits are available. Returning a very high number (effectively
# "unlimited") preserves backward compatibility for existing customers.
_FALLBACK_LIMITS = {
    "max_products": 10_000,
    "max_dsrs": 1_000,
    "max_suppliers": 1_000,
}

_FEATURE_FALSE_FALLBACK = False


def _read_jwt_plan_limits(request: HttpRequest) -> Optional[dict]:
    """
    Decode the Authorization Bearer JWT (without verifying signature — the
    PermissionMiddleware already verified it upstream) and return the
    `plan_limits` claim if present.

    This function intentionally does NOT re-verify the signature to avoid
    a duplicate crypto op on every request; the middleware is the single
    source of truth for token validity.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        import jwt as pyjwt
        payload = pyjwt.decode(token, options={"verify_signature": False})
    except Exception:
        return None
    return payload.get("plan_limits")


def _extract_sattabase_limits(request: HttpRequest) -> Optional[dict]:
    """
    Extract plan limits from SattaBase access data cached on the request.

    During Phase 2, controllers that call `aget_dealer_access()` store the
    result on `request._sattabase_access` so downstream plan_limits checks
    can use it without an extra HTTP call. If not cached on the request,
    this returns None (the SattaBase call must be done by the controller
    explicitly, since it's async and get_plan_limits is sync).
    """
    access_data = getattr(request, "_sattabase_access", None)
    if not access_data:
        return None

    access_map = access_data.get("access", {})
    limits = {}
    for key in ("max_dsrs", "max_products", "max_suppliers"):
        value = access_map.get(key)
        if isinstance(value, (int, float)):
            limits[key] = value

    return limits if limits else None


def get_plan_limits(request: HttpRequest) -> dict:
    """
    Return the plan limits for the current request.

    Resolution order (Phase 2):
      1. SattaBase access map (cached on request by controller)
      2. JWT `plan_limits` claim
      3. Permissive defaults

    The X-Plan-Limits header is NO LONGER trusted. Client-provided header
    values can be manipulated to bypass limits, so they must not be used
    for enforcement decisions.
    """
    # 1. SattaBase access map (preferred — always fresh from cache)
    limits = _extract_sattabase_limits(request)
    source = "sattabase_access"
    if limits:
        logger.debug("plan_limits resolved from %s: %s", source, limits)
        return limits

    # 2. JWT claim
    limits = _read_jwt_plan_limits(request)
    source = "jwt"
    if limits:
        logger.debug("plan_limits resolved from %s: %s", source, limits)
        return limits

    # 3. Permissive fallback
    limits = _FALLBACK_LIMITS
    source = "fallback"
    # Only warn once per process to avoid log spam.
    if not getattr(logger, "_fallback_warned", False):
        logger.warning(
            "plan_limits not available from SattaBase access or JWT — "
            "using permissive fallback. Configure SATTABASE_API_KEY to "
            "enable SattaBase access enforcement."
        )
        logger._fallback_warned = True  # type: ignore[attr-defined]
    if source != "fallback":
        logger.debug("plan_limits resolved from %s: %s", source, limits)
    return limits


def is_feature_enabled(request: HttpRequest, feature: str) -> bool:
    """
    Return True if the named boolean feature is enabled for this plan.

    Resolution order:
      1. SattaBase access map (if cached on request)
      2. JWT `plan_limits.<feature>` (must be a boolean)
      3. Permissive fallback = False (deny-by-default for features)
    """
    # 1. Check SattaBase access map first
    access_data = getattr(request, "_sattabase_access", None)
    if access_data:
        access_map = access_data.get("access", {})
        value = access_map.get(feature)
        if isinstance(value, bool):
            return value

    # 2. Check JWT plan_limits
    limits = _read_jwt_plan_limits(request)
    if limits:
        value = limits.get(feature)
        if isinstance(value, bool):
            return value

    # 3. Deny-by-default fallback
    return _FEATURE_FALSE_FALLBACK


def check_plan_limit(request: HttpRequest, key: str, current_count: int) -> None:
    """
    Raise HttpError(403) if `current_count` has reached or exceeded the plan
    limit for `key`. `current_count` is the number of records the user
    ALREADY has; pass `count + 1` when checking before insert.

    Returns silently when the limit is not reached.
    """
    limits = get_plan_limits(request)
    limit_value = limits.get(key)
    if not isinstance(limit_value, (int, float)):
        # No limit configured for this key, or wrong type. Permissive path.
        return
    # Convention: limit == 0 means "unlimited" (matches the billing_seed_data
    # convention in the integration tracking doc).
    if limit_value == 0:
        return
    if current_count >= limit_value:
        raise HttpError(
            403,
            f"Plan limit reached for '{key}': you have {current_count} of "
            f"{int(limit_value)} allowed. Please upgrade your plan.",
        )


def check_feature(request: HttpRequest, feature: str) -> None:
    """
    Raise HttpError(403) if the named boolean feature is not enabled for
    the current plan. Returns silently when enabled.
    """
    if not is_feature_enabled(request, feature):
        raise HttpError(
            403,
            f"Your plan does not include the '{feature}' feature. "
            f"Please upgrade to enable it.",
        )


def attach_sattabase_access(request: HttpRequest, access_data: dict) -> None:
    """Store SattaBase access data on the request for downstream use.

    Controllers that fetch dealer access via `aget_dealer_access()` should
    call this to make the data available to `get_plan_limits()` and
    `is_feature_enabled()` without an extra HTTP round-trip.

    Example::

        dealer_access = await aget_dealer_access(dealer_username)
        attach_sattabase_access(request, dealer_access)
        # Now get_plan_limits(request) uses the SattaBase data
    """
    request._sattabase_access = access_data  # type: ignore[attr-defined]
