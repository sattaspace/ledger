"""Tests for access module."""

from __future__ import annotations

import pytest
import respx

from .conftest import TEST_BASE_URL, token_response


class TestAccessModule:
    """Tests for feature access checking with caching."""

    @pytest.mark.asyncio
    async def test_has_access_true(self, client, auth_me_response):
        """has_access returns True for granted features."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            assert await client.access.has_access("reports", token="test-token")
            assert await client.access.has_access("dashboard", token="test-token")
            assert await client.access.has_access("api_access", token="test-token")

    @pytest.mark.asyncio
    async def test_has_access_false(self, client, auth_me_response):
        """has_access returns False for denied features."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            assert not await client.access.has_access("priority_support", token="test-token")
            assert not await client.access.has_access("nonexistent_key", token="test-token")

    @pytest.mark.asyncio
    async def test_get_access_integer(self, client, auth_me_response):
        """get_access returns integer values."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            assert await client.access.get_access("max_bank_accounts", token="test-token") == 5
            assert await client.access.get_access("max_team_members", token="test-token") == 3
            assert await client.access.get_access("data_retention_days", token="test-token") == 365

    @pytest.mark.asyncio
    async def test_get_access_default(self, client, auth_me_response):
        """get_access returns default for missing keys."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            assert await client.access.get_access("missing_key", default="fallback", token="test-token") == "fallback"

    @pytest.mark.asyncio
    async def test_keys(self, client, auth_me_response):
        """keys returns all access key names."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            keys = await client.access.keys(token="test-token")
            assert "dashboard" in keys
            assert "reports" in keys
            assert "max_bank_accounts" in keys
            assert len(keys) == 8

    @pytest.mark.asyncio
    async def test_cache_avoids_extra_calls(self, client, auth_me_response):
        """Cached responses don't trigger additional API calls."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            # First call fetches
            await client.access.has_access("reports", token="test-token")
            # Second call uses cache
            await client.access.has_access("dashboard", token="test-token")

            # Only one API call was made
            assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, client, auth_me_response):
        """invalidate_cache forces re-fetch."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.get(f"{TEST_BASE_URL}/billing/auth/me").mock(
                return_value=respx.Response(200, json=auth_me_response)
            )

            # First call
            await client.access.has_access("reports", token="test-token")
            assert route.call_count == 1

            # Invalidate and call again
            client.access.invalidate_cache()
            await client.access.has_access("dashboard", token="test-token")
            assert route.call_count == 2
