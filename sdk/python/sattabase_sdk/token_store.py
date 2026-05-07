"""Token store protocol for persisting user tokens across requests."""

from __future__ import annotations

import json
import logging
from typing import Protocol, runtime_checkable

from .models import TokenPair

logger = logging.getLogger("sattabase_sdk.token_store")


# =============================================================================
# Protocols
# =============================================================================


@runtime_checkable
class TokenStore(Protocol):
    """Protocol for token storage backends.

    Implement this to persist tokens across requests. The SDK uses this
    for auto-refresh and middleware integration.

    Example implementations: :class:`RedisTokenStore`, :class:`InMemoryTokenStore`.
    """

    async def get_tokens(self, user_id: str) -> TokenPair | None:
        """Retrieve stored tokens for a user.

        Args:
            user_id: The Sattabase user ID (string).

        Returns:
            TokenPair if found, None otherwise.
        """
        ...

    async def set_tokens(self, user_id: str, tokens: TokenPair) -> None:
        """Store tokens for a user.

        Args:
            user_id: The Sattabase user ID (string).
            tokens: The token pair to store.
        """
        ...

    async def delete_tokens(self, user_id: str) -> None:
        """Delete stored tokens for a user.

        Args:
            user_id: The Sattabase user ID (string).
        """
        ...


@runtime_checkable
class TokenStoreWithLookup(TokenStore, Protocol):
    """Extended token store protocol with lookup capabilities.

    Adds methods for finding tokens without knowing the user_id upfront.
    This is used by the SDK's auto-refresh and token resolution logic.

    Example implementations: :class:`RedisTokenStore`, :class:`InMemoryTokenStore`.
    """

    async def get_first_token_pair(self) -> TokenPair | None:
        """Retrieve the first available token pair from the store.

        Used when the user_id is not known (e.g. resolving token from store
        for ``auth.me()`` calls).

        Returns:
            The first TokenPair found, or None if the store is empty.
        """
        ...

    async def get_user_id_by_refresh(self, refresh_token: str) -> str | None:
        """Find a user_id by matching a refresh token.

        Used during token refresh to update the correct entry in the store.

        Args:
            refresh_token: The refresh token to look up.

        Returns:
            The user_id associated with the refresh token, or None.
        """
        ...


# =============================================================================
# In-memory implementation
# =============================================================================


class InMemoryTokenStore:
    """In-memory token store for development and testing.

    Not suitable for production — tokens are lost on process restart
    and not shared across workers.

    Implements :class:`TokenStoreWithLookup`.
    """

    def __init__(self) -> None:
        self._store: dict[str, TokenPair] = {}

    async def get_tokens(self, user_id: str) -> TokenPair | None:
        return self._store.get(user_id)

    async def set_tokens(self, user_id: str, tokens: TokenPair) -> None:
        self._store[user_id] = tokens

    async def delete_tokens(self, user_id: str) -> None:
        self._store.pop(user_id, None)

    async def get_first_token_pair(self) -> TokenPair | None:
        """Return the first token pair in the store, or None."""
        for tokens in self._store.values():
            if isinstance(tokens, TokenPair):
                return tokens
        return None

    async def get_user_id_by_refresh(self, refresh_token: str) -> str | None:
        """Find user_id by matching refresh token."""
        for user_id, tokens in self._store.items():
            if isinstance(tokens, TokenPair) and tokens.refresh == refresh_token:
                return user_id
        return None


# =============================================================================
# Redis implementation
# =============================================================================


class RedisTokenStore:
    """Redis-backed token store for production deployments.

    Tokens are stored as JSON-serialized :class:`TokenPair` objects with
    a configurable key prefix. Uses SCAN for safe iteration over large
    datasets.

    Implements :class:`TokenStoreWithLookup`.

    Args:
        redis_client: Any redis-like client with ``get``, ``set``, ``delete``,
            and ``scan_iter`` (or ``keys``) methods.
            Typically ``redis.Redis`` or ``redis.asyncio.Redis``.
        key_prefix: Redis key prefix (default: ``"sb:tokens:"``).

    Example::

        import redis.asyncio as redis

        redis_client = redis.Redis.from_url("redis://localhost:6379")
        store = RedisTokenStore(redis_client)

        # Keys in Redis: sb:tokens:<user_id> → JSON(TokenPair)
        await store.set_tokens("42", TokenPair(access="...", refresh="..."))
        tokens = await store.get_tokens("42")
    """

    def __init__(
        self,
        redis_client: object,
        key_prefix: str = "sb:tokens:",
    ) -> None:
        try:
            import redis  # noqa: F401 — verify redis is installed
        except ImportError as exc:
            raise ImportError(
                "redis package is required for RedisTokenStore. "
                "Install it with: pip install redis"
            ) from exc

        self._redis = redis_client
        self._key_prefix = key_prefix

    def _key(self, user_id: str) -> str:
        """Build the full Redis key for a user."""
        return f"{self._key_prefix}{user_id}"

    async def get_tokens(self, user_id: str) -> TokenPair | None:
        """Retrieve tokens for a user from Redis."""
        data = await self._redis.get(self._key(user_id))
        if data is None:
            return None
        try:
            parsed = json.loads(data)
            return TokenPair(**parsed)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Failed to deserialize token for user %s: %s", user_id, exc)
            return None

    async def set_tokens(self, user_id: str, tokens: TokenPair) -> None:
        """Store tokens for a user in Redis as JSON."""
        data = tokens.model_dump_json()
        await self._redis.set(self._key(user_id), data)

    async def delete_tokens(self, user_id: str) -> None:
        """Delete tokens for a user from Redis."""
        await self._redis.delete(self._key(user_id))

    async def get_first_token_pair(self) -> TokenPair | None:
        """Scan Redis for the first available token pair.

        Uses SCAN to iterate over keys safely (handles large datasets
        without blocking the Redis server).
        """
        try:
            # Prefer scan_iter if available (redis-py 4.x+)
            if hasattr(self._redis, "scan_iter"):
                async for key in self._redis.scan_iter(f"{self._key_prefix}*"):
                    data = await self._redis.get(key)
                    if data:
                        try:
                            parsed = json.loads(data)
                            return TokenPair(**parsed)
                        except (json.JSONDecodeError, TypeError, ValueError):
                            continue
            else:
                # Fallback to keys() for older redis clients
                keys = await self._redis.keys(f"{self._key_prefix}*")
                for key in keys:
                    data = await self._redis.get(key)
                    if data:
                        try:
                            parsed = json.loads(data)
                            return TokenPair(**parsed)
                        except (json.JSONDecodeError, TypeError, ValueError):
                            continue
        except Exception as exc:
            logger.warning("Redis scan failed in get_first_token_pair: %s", exc)
        return None

    async def get_user_id_by_refresh(self, refresh_token: str) -> str | None:
        """Find user_id by matching refresh token via SCAN.

        Iterates over all token keys to find the one containing the
        matching refresh token.
        """
        prefix_len = len(self._key_prefix)
        try:
            if hasattr(self._redis, "scan_iter"):
                async for key in self._redis.scan_iter(f"{self._key_prefix}*"):
                    data = await self._redis.get(key)
                    if data:
                        try:
                            parsed = json.loads(data)
                            if parsed.get("refresh") == refresh_token:
                                # Extract user_id from key
                                key_str = key.decode() if isinstance(key, bytes) else key
                                return key_str[prefix_len:]
                        except (json.JSONDecodeError, TypeError, ValueError):
                            continue
            else:
                keys = await self._redis.keys(f"{self._key_prefix}*")
                for key in keys:
                    data = await self._redis.get(key)
                    if data:
                        try:
                            parsed = json.loads(data)
                            if parsed.get("refresh") == refresh_token:
                                key_str = key.decode() if isinstance(key, bytes) else key
                                return key_str[prefix_len:]
                        except (json.JSONDecodeError, TypeError, ValueError):
                            continue
        except Exception as exc:
            logger.warning("Redis scan failed in get_user_id_by_refresh: %s", exc)
        return None
