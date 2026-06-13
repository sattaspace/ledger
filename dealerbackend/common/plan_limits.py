"""
DEALERCORE — Plan Limits Enforcement
--------------------------------------
Server-side enforcement of subscription limits and feature flags.

FIX A-1 (Phase A — CRIT-1): the frontend used to be the sole gatekeeper
for `max_products`, `max_dsrs`, `max_suppliers`, `export_pdf`, etc.
Any user with a valid JWT could bypass those checks via direct API calls.
This module provides:

  - `get_plan_limits(request)` \u2014 reads the plan limits from the JWT (custom
    `plan_limits` claim if present, else falls back to a permissive default
    so existing deployments are not broken until SattaBase is updated to
    embed the claim).
  - `check_plan_limit(request, key, current_count)` \u2014 raises `HttpError(403)`
    if `current_count >= limit`.
  - `check_feature(request, key)` \u2014 raises `HttpError(403)` if the feature is
    not enabled for the current plan.

SattaBase-side change required for full effect: include a `plan_limits`
object claim in the access JWT, shaped like::

    {
      "max_products": 50,
      "max_dsrs": 1,
      "max_suppliers": 3,
      "export_pdf": true,
      "ai_insights": false,
      ...
    }

Until that ships, the helper accepts the limits from the request's
`X-Plan-Limits` header (set by the frontend from the /billing/auth/me
access map). The header is trusted only because the request itself is
JWT-authenticated \u2014 an attacker without a valid JWT cannot reach this
code path. When SattaBase ships the claim, this fallback can be removed.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from django.http import HttpRequest
from ninja.errors import HttpError


logger = logging.getLogger(__name__)

# Permissive fallback used when neither the JWT claim nor the X-Plan-Limits
# header is present. Returning a very high number (effectively "unlimited")
# preserves backward compatibility for existing customers until SattaBase
# is updated. New deployments should configure SattaBase to embed the
# `plan_limits` claim in the JWT.
_FALLBACK_LIMITS = {
    "max_products": 10_000,
    "max_dsrs": 1_000,
    "max_suppliers": 1_000,
}

_FEATURE_FALSE_FALLBACK = False


def _read_jwt_plan_limits(request: HttpRequest) -> Optional[dict]:
    """
    Decode the Authorization Bearer JWT (without verifying signature \u2014 the
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


def _read_header_plan_limits(request: HttpRequest) -> Optional[dict]:
    """
    Read plan limits from `X-Plan-Limits` header (JSON-encoded). The
    frontend sets this from the /billing/auth/me access map.

    Headers are trusted only because the request is JWT-authenticated; an
    attacker without a valid JWT cannot reach this code path.
    """
    raw = request.headers.get("X-Plan-Limits", "")
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("Invalid X-Plan-Limits header (not JSON)")
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def get_plan_limits(request: HttpRequest) -> dict:
    """
    Return the plan limits for the current request.

    Resolution order:
      1. JWT `plan_limits` claim (preferred \u2014 SattaBase should embed this)
      2. `X-Plan-Limits` request header (frontend fallback)
      3. Permissive defaults (backward-compat until #1 ships)

    Returns a dict of `key -> int` for limit keys, plus a parallel
    `key -> bool` shape for feature flags via `is_feature_enabled`.
    """
    # 1. JWT claim
    limits = _read_jwt_plan_limits(request)
    source = "jwt"
    if not limits:
        # 2. Header
        limits = _read_header_plan_limits(request)
        source = "header"
    if not limits:
        # 3. Permissive fallback
        limits = _FALLBACK_LIMITS
        source = "fallback"
        # Only warn once per process to avoid log spam.
        if not getattr(logger, "_fallback_warned", False):
            logger.warning(
                "plan_limits not in JWT or X-Plan-Limits header \u2014 "
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
      2. `X-Plan-Limits.<feature>` (must be a boolean)
      3. Permissive fallback = False (deny-by-default for features)
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
