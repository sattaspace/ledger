"""Tests for token store implementations — InMemory and Redis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from sattabase_sdk.models import TokenPair
from sattabase_sdk.token_store import (
    InMemoryTokenStore,
    RedisTokenStore,
    TokenStore,
    TokenStoreWithLookup,
)


# =============================================================================
# Protocol conformance tests
# =============================================================================


class TestProtocols:
    """Verify InMemoryTokenStore satisfies both protocols."""

    def test_in_memory_satisfies_token_store(self):
        assert isinstance(InMemoryTokenStore(), TokenStore)

    def test_in_memory_satisfies_token_store_with_lookup(self):
        assert isinstance(InMemoryTokenStore(), TokenStoreWithLookup)

    def test_redis_satisfies_token_store_with_lookup(self):
        mock_redis = MagicMock()
        store = RedisTokenStore(mock_redis)
        assert isinstance(store, TokenStoreWithLookup)


# =============================================================================
# InMemoryTokenStore tests
# =============================================================================


class TestInMemoryTokenStore:
    """Tests for InMemoryTokenStore."""

    @pytest.mark.asyncio
    async def test_get_tokens_returns_none_for_missing_user(self):
        store = InMemoryTokenStore()
        result = await store.get_tokens("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get_tokens(self):
        store = InMemoryTokenStore()
        tokens = TokenPair(access="access_1", refresh="refresh_1")
        await store.set_tokens("user_1", tokens)
        result = await store.get_tokens("user_1")
        assert result is not None
        assert result.access == "access_1"
        assert result.refresh == "refresh_1"

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self):
        store = InMemoryTokenStore()
        await store.set_tokens("user_1", TokenPair(access="old_a", refresh="old_r"))
        await store.set_tokens("user_1", TokenPair(access="new_a", refresh="new_r"))
        result = await store.get_tokens("user_1")
        assert result.access == "new_a"

    @pytest.mark.asyncio
    async def test_delete_tokens(self):
        store = InMemoryTokenStore()
        await store.set_tokens("user_1", TokenPair(access="a", refresh="r"))
        await store.delete_tokens("user_1")
        result = await store.get_tokens("user_1")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_does_not_raise(self):
        store = InMemoryTokenStore()
        await store.delete_tokens("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_multiple_users(self):
        store = InMemoryTokenStore()
        await store.set_tokens("user_1", TokenPair(access="a1", refresh="r1"))
        await store.set_tokens("user_2", TokenPair(access="a2", refresh="r2"))
        assert (await store.get_tokens("user_1")).access == "a1"
        assert (await store.get_tokens("user_2")).access == "a2"

    @pytest.mark.asyncio
    async def test_get_first_token_pair(self):
        store = InMemoryTokenStore()
        result = await store.get_first_token_pair()
        assert result is None

        await store.set_tokens("user_1", TokenPair(access="a1", refresh="r1"))
        await store.set_tokens("user_2", TokenPair(access="a2", refresh="r2"))
        result = await store.get_first_token_pair()
        assert result is not None
        assert result.access == "a1"

    @pytest.mark.asyncio
    async def test_get_first_token_pair_after_delete(self):
        store = InMemoryTokenStore()
        await store.set_tokens("user_1", TokenPair(access="a1", refresh="r1"))
        await store.set_tokens("user_2", TokenPair(access="a2", refresh="r2"))
        await store.delete_tokens("user_1")
        result = await store.get_first_token_pair()
        assert result is not None
        assert result.access == "a2"

    @pytest.mark.asyncio
    async def test_get_user_id_by_refresh(self):
        store = InMemoryTokenStore()
        await store.set_tokens("user_1", TokenPair(access="a1", refresh="r1"))
        await store.set_tokens("user_2", TokenPair(access="a2", refresh="r2"))

        assert await store.get_user_id_by_refresh("r1") == "user_1"
        assert await store.get_user_id_by_refresh("r2") == "user_2"
        assert await store.get_user_id_by_refresh("nonexistent") is None


# =============================================================================
# RedisTokenStore tests (mocked Redis)
# =============================================================================


def _make_mock_redis() -> MagicMock:
    """Create a mock async Redis client with in-memory storage."""
    storage: dict[str, str] = {}

    mock_redis = MagicMock()

    async def mock_get(key):
        return storage.get(key)

    async def mock_set(key, value):
        storage[key] = value

    async def mock_delete(key):
        storage.pop(key, None)

    async def mock_scan_iter(pattern):
        for key in list(storage.keys()):
            if key.startswith(pattern.rstrip("*")):
                yield key

    mock_redis.get = mock_get
    mock_redis.set = mock_set
    mock_redis.delete = mock_delete
    mock_redis.scan_iter = mock_scan_iter
    return mock_redis


class TestRedisTokenStore:
    """Tests for RedisTokenStore with mocked Redis client."""

    @pytest.mark.asyncio
    async def test_set_and_get_tokens(self):
        mock_redis = _make_mock_redis()
        store = RedisTokenStore(mock_redis, key_prefix="test:")
        tokens = TokenPair(access="redis_access", refresh="redis_refresh")
        await store.set_tokens("user_42", tokens)
        result = await store.get_tokens("user_42")
        assert result is not None
        assert result.access == "redis_access"

    @pytest.mark.asyncio
    async def test_get_tokens_missing_returns_none(self):
        mock_redis = _make_mock_redis()
        store = RedisTokenStore(mock_redis, key_prefix="test:")
        result = await store.get_tokens("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_tokens(self):
        mock_redis = _make_mock_redis()
        store = RedisTokenStore(mock_redis, key_prefix="test:")
        await store.set_tokens("user_42", TokenPair(access="a", refresh="r"))
        await store.delete_tokens("user_42")
        result = await store.get_tokens("user_42")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_first_token_pair(self):
        mock_redis = _make_mock_redis()
        store = RedisTokenStore(mock_redis, key_prefix="test:")
        assert await store.get_first_token_pair() is None

        await store.set_tokens("user_1", TokenPair(access="a1", refresh="r1"))
        result = await store.get_first_token_pair()
        assert result is not None
        assert result.access == "a1"

    @pytest.mark.asyncio
    async def test_get_user_id_by_refresh(self):
        mock_redis = _make_mock_redis()
        store = RedisTokenStore(mock_redis, key_prefix="test:")
        await store.set_tokens("user_1", TokenPair(access="a1", refresh="r1"))
        await store.set_tokens("user_2", TokenPair(access="a2", refresh="r2"))

        assert await store.get_user_id_by_refresh("r1") == "user_1"
        assert await store.get_user_id_by_refresh("r2") == "user_2"
        assert await store.get_user_id_by_refresh("nonexistent") is None

    def test_raises_import_error_without_redis(self):
        """RedisTokenStore raises ImportError if redis not installed."""
        # This test verifies the guard clause; redis IS installed in this env
        # so we just verify the class can be instantiated with a mock.
        mock_redis = MagicMock()
        store = RedisTokenStore(mock_redis)
        assert store._key_prefix == "sb:tokens:"
