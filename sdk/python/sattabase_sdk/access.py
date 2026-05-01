"""Access module — feature gating helpers with optional caching."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from .models import AuthMeResponse

if TYPE_CHECKING:
    from .client import SattabaseClient


class AccessModule:
    """Feature access checking with optional client-side caching.

    Wraps :meth:`AuthModule.me` with caching to avoid repeated API calls
    within a configurable TTL window.
    """

    def __init__(self, client: SattabaseClient, cache_ttl: float = 60.0) -> None:
        self._client = client
        self._cache_ttl = cache_ttl
        self._cached: AuthMeResponse | None = None
        self._cached_at: float = 0.0

    def _is_cache_valid(self) -> bool:
        """Check if cached data is still within TTL."""
        if self._cached is None:
            return False
        return (time.monotonic() - self._cached_at) < self._cache_ttl

    def invalidate_cache(self) -> None:
        """Clear cached AuthMeResponse, forcing next call to re-fetch."""
        self._cached = None
        self._cached_at = 0.0

    async def _get_auth_me(self, token: str | None = None) -> AuthMeResponse:
        """Get AuthMeResponse, using cache if valid."""
        if self._is_cache_valid() and self._cached is not None:
            return self._cached

        auth_me = await self._client.auth.me(token)
        self._cached = auth_me
        self._cached_at = time.monotonic()
        return auth_me

    async def has_access(self, key: str, token: str | None = None) -> bool:
        """Check if the user has access to a feature.

        Args:
            key: The access key (e.g. ``"reports"``, ``"max_bank_accounts"``).
            token: Optional JWT token. Falls back to token_store if None.

        Returns:
            True if the user has access to the feature.
        """
        auth_me = await self._get_auth_me(token)
        return auth_me.has_access(key)

    async def get_access(
        self,
        key: str,
        default: Any = None,
        token: str | None = None,
    ) -> Any:
        """Get the raw value for an access key.

        Args:
            key: The access key.
            default: Default value if key not found.
            token: Optional JWT token.

        Returns:
            The raw value from the access map, or default.
        """
        auth_me = await self._get_auth_me(token)
        return auth_me.get_access(key, default)

    async def keys(self, token: str | None = None) -> list[str]:
        """Get all available access keys for the user.

        Args:
            token: Optional JWT token.

        Returns:
            List of access key strings.
        """
        auth_me = await self._get_auth_me(token)
        return auth_me.access_keys
