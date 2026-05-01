"""Token store protocol for persisting user tokens across requests."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .models import TokenPair


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


class InMemoryTokenStore:
    """In-memory token store for development and testing.

    Not suitable for production — tokens are lost on process restart
    and not shared across workers.
    """

    def __init__(self) -> None:
        self._store: dict[str, TokenPair] = {}

    async def get_tokens(self, user_id: str) -> TokenPair | None:
        return self._store.get(user_id)

    async def set_tokens(self, user_id: str, tokens: TokenPair) -> None:
        self._store[user_id] = tokens

    async def delete_tokens(self, user_id: str) -> None:
        self._store.pop(user_id, None)
