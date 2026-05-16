"""Ledger-specific middleware for auth failure distinction and health checks.

This module provides:
1. ``AuthServiceUnavailableMiddleware`` — runs AFTER the Sattabase SDK middleware
   and distinguishes between "auth service down" (503) and "not authenticated" (401).

2. ``health_check`` — a standalone function for checking Sattabase connectivity.

Why this middleware?
    The SDK's ``SattabaseAuthMiddleware`` sets ``request.sattabase_user = None``
    on *any* failure — whether the base backend returned 401 (bad token) or the
    network request failed entirely (service down). This middleware inspects the
    failure reason and sets ``request.sattabase_auth_unavailable = True`` when
    the auth service couldn't be reached, so that ``LedgerControllerBase`` can
    return 503 instead of 401.

Usage in settings::

    MIDDLEWARE = [
        ...
        "sattabase_sdk.middleware.SattabaseAuthMiddleware",
        "api.middleware.AuthServiceUnavailableMiddleware",   # <-- after SDK
        ...
    ]
"""

import logging

from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class AuthServiceUnavailableMiddleware:
    """Distinguish between "auth service unavailable" and "not authenticated".

    When the Sattabase SDK middleware encounters an authentication failure,
    it sets ``request.sattabase_user = None`` and logs a warning. However,
    it doesn't distinguish between:

    - **401 responses**: The token is invalid/expired — the user is simply
      not authenticated. Return 401.
    - **Network errors / 5xx**: The auth service is down. The user *might*
      be authenticated but we can't verify it. Return 503.

    This middleware probes the Sattabase ``/auth/me`` endpoint on a failure
    to determine if the service is reachable. If not, it sets
    ``request.sattabase_auth_unavailable = True`` so that
    ``LedgerControllerBase.require_user_id()`` can return 503.

    The probe is cached for ``SATTABASE_AUTH_CACHE_TTL`` seconds to avoid
    hammering the auth service on every request when it's down.
    """

    # Cache the last health check result (status + timestamp)
    _last_health_check: dict | None = None

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If the SDK middleware already set a user, auth succeeded — nothing to do.
        user = getattr(request, "sattabase_user", None)
        if user is not None:
            request.sattabase_auth_unavailable = False
            return self.get_response(request)

        # No user attached — either not authenticated or service unavailable.
        # Check if there was a token present. If no token at all, it's just 401.
        token_present = bool(
            request.META.get("HTTP_AUTHORIZATION", "").startswith("Bearer ")
            or request.COOKIES.get("access_token")
            or request.session.get("access_token")
        )

        if not token_present:
            # No token provided — plain 401, no service check needed
            request.sattabase_auth_unavailable = False
            return self.get_response(request)

        # Token was provided but auth failed — check if the service is reachable
        request.sattabase_auth_unavailable = self._is_auth_service_unavailable()
        return self.get_response(request)

    @classmethod
    def _is_auth_service_unavailable(cls) -> bool:
        """Check if the Sattabase auth service is reachable.

        Uses Django's cache to avoid checking on every request.
        Result is cached for 30 seconds (shorter than auth cache TTL).
        """
        from django.core.cache import cache

        cache_key = "ledger:auth_service_health"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Probe the auth service health endpoint
        try:
            import httpx
            base_url = getattr(settings, "SATTABASE_BASE_URL", "")
            # Strip /api/v1 if present to get the base URL
            if base_url.endswith("/api/v1"):
                base_url = base_url[:-7]

            timeout = getattr(settings, "SATTABASE_AUTH_TIMEOUT", 5)
            # Shorter timeout for health check (don't want to block the request)
            health_timeout = min(timeout, 3)

            with httpx.Client(timeout=health_timeout) as client:
                response = client.get(f"{base_url}/api/v1/health/")
                is_down = response.status_code >= 500
        except Exception:
            # Any error means the service is unavailable
            is_down = True

        # Cache for 30 seconds
        cache.set(cache_key, is_down, timeout=30)
        return is_down


def check_sattabase_health() -> dict:
    """Check Sattabase connectivity for the /health endpoint.

    Returns a dict with:
        - ``sattabase_reachable`` (bool): Whether the base backend is reachable
        - ``sattabase_url`` (str): The configured base URL (redacted)
        - ``response_status`` (int|None): HTTP status from /health, or None
        - ``error`` (str|None): Error message if unreachable
    """
    import httpx

    base_url = getattr(settings, "SATTABASE_BASE_URL", "")
    timeout = min(getattr(settings, "SATTABASE_AUTH_TIMEOUT", 5), 5)

    # Strip /api/v1 for health check
    health_base = base_url
    if health_base.endswith("/api/v1"):
        health_base = health_base[:-7]

    result = {
        "sattabase_reachable": False,
        "sattabase_url": base_url.replace("://", "://***@") if "://" in base_url else base_url,
        "response_status": None,
        "error": None,
    }

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{health_base}/api/v1/health/")
            result["response_status"] = response.status_code
            result["sattabase_reachable"] = response.status_code < 500
    except httpx.ConnectError as exc:
        result["error"] = f"Connection refused: {exc}"
    except httpx.TimeoutException:
        result["error"] = f"Timeout after {timeout}s"
    except Exception as exc:
        result["error"] = str(exc)

    return result
