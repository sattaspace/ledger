"""Rate limiting utilities for the common app."""

import time
import logging
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)


def check_rate_limit(key: str, max_attempts: int, window_seconds: int) -> bool:
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


def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    return ip
