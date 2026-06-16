"""
DEALERCORE — Plan Limits Enforcement
--------------------------------------
Server-side enforcement of subscription limits and feature flags.

FIX DSR-020: Removed the X-Plan-Limits header fallback. Client-provided
headers can be manipulated to bypass limits. Now the resolution order is:
  1. JWT `plan_limits` claim (preferred — SattaBase should embed this)
  2. Permissive defaults (backward-compat until #1 ships)

When SattaBase starts embedding the `plan_limits` claim in the JWT, the
fallback defaults can be removed entirely.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.http import HttpRequest
from ninja.errors import HttpError


logger = logging.getLogger(__name__)

# Permissive fallback used when the JWT doesn't include plan_limits.
# Returning a very high number (effectively "unlimited") preserves backward
# compatibility for existing customers until SattaBase is updated to embed
# the `plan_limits` claim in the JWT.
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


def get_plan_limits(request: HttpRequest) -> dict:
    """
    Return the plan limits for the current request.

    FIX DSR-020: Resolution order is now:
      1. JWT `plan_limits` claim (preferred — SattaBase should embed this)
      2. Permissive defaults (backward-compat until #1 ships)

    The X-Plan-Limits header is NO LONGER trusted. Client-provided header
    values can be manipulated to bypass limits, so they must not be used
    for enforcement decisions.
    """
    # 1. JWT claim
    limits = _read_jwt_plan_limits(request)
    source = "jwt"
    if not limits:
        # 2. Permissive fallback
        limits = _FALLBACK_LIMITS
        source = "fallback"
        # Only warn once per process to avoid log spam.
        if not getattr(logger, "_fallback_warned", False):
            logger.warning(
                "plan_limits not in JWT — "
                "using permissive fallback. Configure SattaBase to embed "
                "`plan_limits` in the JWT for production enforcement."
            )
            logger._fallback_warned = True  # type: ignore[attr-defined]
    if source != "fallback":
        logger.debug("plan_limits resolved from %s: %s", source, limits)
    return limits


def is_feature_enabled(request: HttpRequest, feature: str) -> bool:
    """
    Return True if the named boolean feature is enabled for this plan.

    Resolution order matches `get_plan_limits`:
      1. JWT `plan_limits.<feature>` (must be a boolean)
      2. Permissive fallback = False (deny-by-default for features)
    """
    limits = get_plan_limits(request)
    value = limits.get(feature)
    if isinstance(value, bool):
        return value
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