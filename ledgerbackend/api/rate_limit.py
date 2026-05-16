"""Rate limiting utilities for the Ledger sister domain.

Adapted from the base backend's common/rate_limit.py but tailored for
the sister-domain architecture:

- Per-user rate limiting using ``request.sattabase_user.id``
- Per-IP fallback when no user is authenticated
- Configurable per-endpoint limits via settings
- Uses Django's cache framework (Redis in production)

Usage in controllers::

    from api.rate_limit import check_rate_limit_or_raise

    @route.post("")
    def create_account(self, request, payload):
        check_rate_limit_or_raise(request, "create_account")
        ...

Settings (in ledger/settings.py)::

    RATE_LIMIT_CREATE_ATTEMPTS = 30     # per minute
    RATE_LIMIT_LIST_ATTEMPTS = 100      # per minute
    RATE_LIMIT_REPORT_ATTEMPTS = 10     # per minute
    RATE_LIMIT_WINDOW = 60              # seconds
"""

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
        key: Unique identifier for the rate limit bucket.
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
        logger.warning("Rate limit exceeded for key: %s", key)
        return False

    attempts.append(now)
    cache.set(cache_key, attempts, timeout=window_seconds)
    return True


def _get_client_ip(request) -> str:
    """Extract the client's IP address from the request.

    Only trusts X-Forwarded-For when REMOTE_ADDR is a trusted proxy.
    Falls back to REMOTE_ADDR otherwise.
    """
    from ipaddress import ip_address, ip_network

    remote_addr = request.META.get("REMOTE_ADDR", "0.0.0.0")

    trusted_proxies = getattr(settings, "TRUSTED_PROXIES", ["127.0.0.1", "::1"])

    is_trusted = False
    try:
        remote_ip = ip_address(remote_addr)
        for proxy in trusted_proxies:
            try:
                if "/" in proxy:
                    if remote_ip in ip_network(proxy, strict=False):
                        is_trusted = True
                        break
                elif remote_ip == ip_address(proxy):
                    is_trusted = True
                    break
            except ValueError:
                continue
    except ValueError:
        pass

    if is_trusted:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
            return ip

    return remote_addr


def _get_rate_limit_params(action: str) -> tuple[int, int]:
    """Get (max_attempts, window_seconds) for a given action category.

    Routes to the appropriate settings based on the action prefix:
    - "create_*" → RATE_LIMIT_CREATE_ATTEMPTS
    - "list_*" → RATE_LIMIT_LIST_ATTEMPTS
    - "report_*" → RATE_LIMIT_REPORT_ATTEMPTS
    - default → RATE_LIMIT_DEFAULT_ATTEMPTS
    """
    window = getattr(settings, "RATE_LIMIT_WINDOW", 60)

    if action.startswith("create_") or action.startswith("upload_"):
        max_attempts = getattr(settings, "RATE_LIMIT_CREATE_ATTEMPTS", 30)
    elif action.startswith("list_"):
        max_attempts = getattr(settings, "RATE_LIMIT_LIST_ATTEMPTS", 100)
    elif action.startswith("report_") or action.startswith("summary_"):
        max_attempts = getattr(settings, "RATE_LIMIT_REPORT_ATTEMPTS", 10)
    elif action.startswith("delete_") or action.startswith("soft_delete_"):
        max_attempts = getattr(settings, "RATE_LIMIT_DELETE_ATTEMPTS", 30)
    else:
        max_attempts = getattr(settings, "RATE_LIMIT_DEFAULT_ATTEMPTS", 60)

    return max_attempts, window


def check_rate_limit_or_raise(request, action: str, max_attempts: int = None, window_seconds: int = None) -> None:
    """Check rate limit and raise TooManyRequestsError if exceeded.

    Builds the rate limit key from the Sattabase user_id (if authenticated)
    or the client IP (if not authenticated).

    Args:
        request: Django HttpRequest.
        action: Action-specific identifier (e.g. "create_account", "list_transactions").
        max_attempts: Override max requests. Falls back to per-category defaults.
        window_seconds: Override window length. Falls back to RATE_LIMIT_WINDOW.

    Raises:
        TooManyRequestsError: If the rate limit is exceeded.
    """
    from api.errors import TooManyRequestsError

    # Get user_id from Sattabase middleware
    user = getattr(request, "sattabase_user", None)
    user_id = getattr(user, "id", None) if user else None

    # Build the rate limit key
    if user_id:
        identifier = f"u:{user_id}"
    else:
        identifier = f"ip:{_get_client_ip(request)}"

    rl_key = f"{action}:{identifier}"

    # Get rate limit parameters
    if max_attempts is None or window_seconds is None:
        default_max, default_window = _get_rate_limit_params(action)
        max_attempts = max_attempts or default_max
        window_seconds = window_seconds or default_window

    if not check_rate_limit(rl_key, max_attempts, window_seconds):
        raise TooManyRequestsError()
