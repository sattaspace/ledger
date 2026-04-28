"""Rate limiting utilities for the common app."""

import time
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> bool:
    """Check if a request is within the rate limit using a sliding window.

    Stores a list of timestamps in the cache under ``rl:{key}``. Stale
    timestamps outside the window are pruned on each check.

    Args:
        key: Unique identifier for the rate limit bucket
             (e.g. ``"login:192.168.1.1"``).
        max_attempts: Maximum number of requests allowed in the window.
        window_seconds: Length of the sliding window in seconds.

    Returns:
        True if the request is within the limit, False if exceeded.
    """
    now = time.time()
    window_start = now - window_seconds
    cache_key = f"rl:{key}"
    attempts = cache.get(cache_key, [])
    attempts = [ts for ts in attempts if ts > window_start]

    if len(attempts) >= max_attempts:
        logger.warning(f"Rate limit exceeded for key: {key}")
        return False

    attempts.append(now)
    cache.set(cache_key, attempts, timeout=window_seconds)
    return True


def check_rate_limit_or_raise(
    request,
    key_prefix: str,
    max_attempts: int = None,
    window_seconds: int = None,
) -> None:
    """Check rate limit and raise ``TooManyRequestsException`` if exceeded.

    Builds the rate limit key from the request's user ID (if authenticated)
    and client IP. This is a convenience wrapper that combines
    ``get_client_ip``, ``check_rate_limit``, and exception raising into
    a single call.

    Args:
        request: Django HttpRequest. If ``request.user`` is authenticated,
            the user ID is included in the key for per-user rate limiting.
        key_prefix: Action-specific prefix (e.g. ``"cancel_sub"``,
            ``"checkout"``, ``"change_plan"``).
        max_attempts: Max requests in the window. Falls back to
            ``settings.RATE_LIMIT_BILLING_ATTEMPTS`` (default: 5).
        window_seconds: Window length in seconds. Falls back to
            ``settings.RATE_LIMIT_BILLING_WINDOW`` (default: 3600).

    Raises:
        TooManyRequestsException: If the rate limit is exceeded.

    Example::

        @http_post("/subscriptions/{slug}/cancel")
        async def cancel(self, request, slug):
            check_rate_limit_or_raise(request, "cancel_sub")
            # ... business logic
    """
    from common.exceptions import TooManyRequestsException

    user_id = (
        getattr(request, "user", None)
        and hasattr(request.user, "id")
        and str(request.user.id)
        or "anon"
    )
    client_ip = get_client_ip(request)
    rl_key = f"{key_prefix}:{user_id}:{client_ip}"

    _max = max_attempts or getattr(settings, "RATE_LIMIT_BILLING_ATTEMPTS", 5)
    _window = window_seconds or getattr(settings, "RATE_LIMIT_BILLING_WINDOW", 3600)

    if not check_rate_limit(rl_key, _max, _window):
        raise TooManyRequestsException()


def get_client_ip(request) -> str:
    """Extract the client's IP address from the request.

    Checks ``X-Forwarded-For`` first (for reverse proxy setups),
    then falls back to ``REMOTE_ADDR``.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    return ip
