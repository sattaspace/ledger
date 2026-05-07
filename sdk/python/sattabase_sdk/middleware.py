"""Django middleware for Sattabase authentication.

Pattern A: Backend proxy — the sister domain's backend proxies user requests
to Sattabase and attaches user identity + access to every request.

Usage in Django settings::

    MIDDLEWARE = [
        ...
        "sattabase_sdk.middleware.SattabaseAuthMiddleware",
    ]

After this middleware, every request has:

- ``request.sattabase_user`` — :class:`User` model or None
- ``request.sattabase_access`` — ``dict[str, Any]`` access map
- ``request.sattabase_subscription`` — :class:`SubscriptionInfo` or None
"""

from __future__ import annotations

import atexit
import logging
from typing import Any

from asgiref.sync import sync_to_async

from .client import SattabaseClient
from .config import SattabaseConfig
from .exceptions import SattabaseError

logger = logging.getLogger("sattabase_sdk.middleware")


class SattabaseAuthMiddleware:
    """Django middleware that attaches Sattabase user data to requests.

    Works with both sync and async Django views via the ``@sync_and_async_middleware``
    pattern. On failure, sets all attributes to None (graceful degradation).

    Configuration via Django settings:

    - ``SATTABASE_BASE_URL`` — Sattabase API base URL
    - ``SATTABASE_SERVICE_DOMAIN`` — Service domain identifier
    - ``SATTABASE_API_KEY`` — Service credential raw key
    - ``SATTABASE_AUTH_TIMEOUT`` — Request timeout (default: 5)
    - ``SATTABASE_AUTH_CACHE_TTL`` — Cache TTL for auth/me (default: 60)
    """

    sync_capable = True
    async_capable = True

    # Shared client instance (lazy-initialized)
    _client: SattabaseClient | None = None

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        # Lazy init is handled per-request to avoid import-time side effects

    @classmethod
    def _get_client(cls) -> SattabaseClient:
        """Get or create the shared SattabaseClient."""
        if cls._client is None:
            from django.conf import settings

            from .access import AccessModule

            cache_ttl = float(getattr(settings, "SATTABASE_AUTH_CACHE_TTL", 60))

            config = SattabaseConfig(
                base_url=getattr(settings, "SATTABASE_BASE_URL", ""),
                service_domain=getattr(settings, "SATTABASE_SERVICE_DOMAIN", ""),
                api_key=getattr(settings, "SATTABASE_API_KEY", ""),
                timeout=getattr(settings, "SATTABASE_AUTH_TIMEOUT", 5),
            )
            cls._client = SattabaseClient(config)

            # Reassign access module with the configured cache TTL
            cls._client.access = AccessModule(cls._client, cache_ttl=cache_ttl)

            # Register cleanup on process shutdown
            atexit.register(cls.close)
        return cls._client

    @classmethod
    def close(cls) -> None:
        """Close the shared SattabaseClient and release resources.

        Called automatically via ``atexit`` on process shutdown, but can also
        be called manually (e.g. in tests or when reconfiguring).
        """
        if cls._client is not None:
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                # If there's a running loop, create a task to close
                loop.create_task(cls._client.close())
            except RuntimeError:
                # No running loop — run close synchronously
                asyncio.run(cls._client.close())
            cls._client = None

    def _extract_token(self, request: Any) -> str | None:
        """Extract JWT access token from the request.

        Checks:
        1. ``Authorization: Bearer {token}`` header
        2. ``access_token`` cookie
        3. Session ``access_token`` key
        """
        # Header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # Cookie
        token = request.COOKIES.get("access_token")
        if token:
            return token

        # Session
        token = request.session.get("access_token")
        if token:
            return token

        return None

    def __call__(self, request: Any) -> Any:
        """Sync middleware entry point."""
        token = self._extract_token(request)
        if not token:
            request.sattabase_user = None
            request.sattabase_access = {}
            request.sattabase_subscription = None
            return self.get_response(request)

        # Run async fetch in sync context
        client = self._get_client()
        auth_me = sync_to_async(client.auth.me)(token=token)

        # We can't await in sync context, so use a thread
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Django dev server already has a running loop
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        client.auth.me(token=token),
                    )
                    auth_me = future.result(timeout=client.config.timeout)
            else:
                auth_me = asyncio.run(client.auth.me(token=token))
        except (SattabaseError, Exception) as exc:
            logger.warning(
                "Sattabase auth/me failed: %s — degrading gracefully",
                exc,
            )
            request.sattabase_user = None
            request.sattabase_access = {}
            request.sattabase_subscription = None
            return self.get_response(request)

        request.sattabase_user = auth_me.user
        request.sattabase_access = auth_me.access
        request.sattabase_subscription = auth_me.subscription

        return self.get_response(request)

    async def __acall__(self, request: Any) -> Any:  # type: ignore[override]
        """Async middleware entry point."""
        token = self._extract_token(request)
        if not token:
            request.sattabase_user = None
            request.sattabase_access = {}
            request.sattabase_subscription = None
            return await self.get_response(request)

        client = self._get_client()
        try:
            auth_me = await client.auth.me(token=token)
        except SattabaseError as exc:
            logger.warning(
                "Sattabase auth/me failed: %s — degrading gracefully",
                exc,
            )
            request.sattabase_user = None
            request.sattabase_access = {}
            request.sattabase_subscription = None
            return await self.get_response(request)

        request.sattabase_user = auth_me.user
        request.sattabase_access = auth_me.access
        request.sattabase_subscription = auth_me.subscription

        return await self.get_response(request)
