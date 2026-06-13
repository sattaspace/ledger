"""
DEALERCORE — Simple Rate Limiting
---------------------------------
Decorator for limiting request rates on async views using Django's built-in
cache framework. No external dependency required.

FIX H-6: prevents brute-force on login and other auth endpoints.

Usage:
    from common.rate_limit import rate_limit

    @http_post("/login", ...)
    @rate_limit("dsr_login", limit=5, period=60, scope="ip")
    async def login(self, request, data):
        ...

The cache backend is whatever Django uses by default (LocMemCache in dev;
Redis in production). Each cache key is namespaced by the `scope`:
  - "ip": bucket per client IP
  - "user": bucket per authenticated user id (call after auth resolves)
  - "email": bucket per submitted email/identifier (good for password reset)

A 429 response is returned when the limit is exceeded.

Production note: Django's default cache is LocMemCache, which is per-process.
In a multi-worker ASGI deployment, each worker keeps its own bucket, so an
attacker could distribute brute-force across workers. Configure CACHES to
a shared backend (Redis is recommended — the project already includes
`django-redis==6.0.0` and `redis==7.4.0` in the base requirements) before
relying on this for production security.
"""

from __future__ import annotations

import hashlib
from functools import wraps
from typing import Optional

from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from asgiref.sync import sync_to_async


def _get_client_ip(request: HttpRequest) -> str:
    """Get the client's IP, honoring X-Forwarded-For when present."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        # First IP in the comma-separated list is the original client
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or "unknown"


def _bucket_key(scope: str, identifier: str) -> str:
    """Build a stable cache key. Hash to keep keys short and avoid weird chars."""
    raw = f"ratelimit:{scope}:{identifier}"
    return "rl:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


async def _increment(bucket: str, period: int) -> int:
    """
    Atomically increment the counter for `bucket`, creating it on first hit.

    Uses cache.add() to set the initial value with TTL atomically — this is
    the closest Django-cache approximation of a Redis SET NX EX. Subsequent
    hits use cache.incr() which is itself atomic at the cache backend level.
    """
    added = await sync_to_async(cache.add)(bucket, 1, period)
    if added:
        return 1
    # Race window: another request already added; incr returns the new value.
    return await sync_to_async(cache.incr)(bucket)


def rate_limit(
    name: str,
    limit: int,
    period: int,
    scope: str = "ip",
    identifier_fn: Optional[callable] = None,
):
    """
    Decorator that limits requests to `limit` per `period` seconds.

    Args:
        name: short identifier for this limit (e.g. "dsr_login"). Used in
              the cache key so different endpoints have separate buckets.
        limit: max number of requests in `period` seconds.
        period: window size in seconds.
        scope: "ip" (default), "user", or "email". Determines the bucket key.
        identifier_fn: optional callable(request) -> str to override the
                       identifier. Useful for "email" scope where you want
                       the bucket per submitted email.

    Behavior:
        - Returns 429 if the limit is exceeded.
        - The bucket TTL is `period` seconds (sliding-fixed: resets when the
          first hit ages out). This is a small simplification vs true
          sliding-window but is sufficient for brute-force protection.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # ninja-extra controllers: first positional arg is `self`, second
            # is `request`. Bare functions: first positional arg is `request`.
            request: Optional[HttpRequest] = None
            for a in args:
                if isinstance(a, HttpRequest):
                    request = a
                    break
            if request is None:
                request = kwargs.get("request")

            if request is None:
                # No request context — cannot rate-limit. Fail open.
                return await func(*args, **kwargs)

            # Resolve identifier
            if identifier_fn is not None:
                identifier = identifier_fn(request)
                if not identifier:
                    identifier = _get_client_ip(request)
            elif scope == "ip":
                identifier = _get_client_ip(request)
            elif scope == "user":
                # Try JWT-extracted username/email (set by PermissionMiddleware)
                identifier = (
                    getattr(request, "dealer_username", None)
                    or getattr(request, "user_email", None)
                    or _get_client_ip(request)
                )
            else:
                identifier = _get_client_ip(request)

            bucket = _bucket_key(f"{name}:{scope}", identifier)
            count = await _increment(bucket, period)
            if count > limit:
                return JsonResponse(
                    {
                        "detail": (
                            f"Too many requests. Please try again in "
                            f"{period} seconds."
                        ),
                        "code": "rate_limited",
                        "retry_after": period,
                    },
                    status=429,
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
