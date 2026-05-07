"""Tests for the SDK client _request method."""

from __future__ import annotations

import httpx
import pytest
import respx

from sattabase_sdk.config import SattabaseConfig
from sattabase_sdk.exceptions import (
    ApiServerError,
    AuthenticationError,
    RateLimitError,
    SattabaseError,
)

from .conftest import TEST_API_KEY, TEST_BASE_URL, TEST_SERVICE_DOMAIN


def _make_config(**overrides):
    """Create a SattabaseConfig for tests (not a pytest fixture)."""
    defaults = dict(
        base_url=TEST_BASE_URL,
        service_domain=TEST_SERVICE_DOMAIN,
        api_key=TEST_API_KEY,
        timeout=10.0,
        auto_refresh=True,
        debug=True,
    )
    defaults.update(overrides)
    return SattabaseConfig(**defaults)


class TestClientRequest:
    """Tests for SattabaseClient._request()."""

    @pytest.mark.asyncio
    async def test_injects_headers(self, client):
        """_request injects X-API-Key and X-Service-Domain."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )

            await client._request("GET", "/test")

            headers = route.calls[0].request.headers
            assert headers["x-api-key"] == TEST_API_KEY
            assert headers["x-service-domain"] == TEST_SERVICE_DOMAIN

    @pytest.mark.asyncio
    async def test_injects_auth_header(self, client):
        """_request injects Authorization header when token is provided."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(200, json={"ok": True})
            )

            await client._request("GET", "/test", token="my_jwt_token")

            headers = route.calls[0].request.headers
            assert headers["authorization"] == "Bearer my_jwt_token"

    @pytest.mark.asyncio
    async def test_success_response(self, client):
        """Successful request returns parsed JSON."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(200, json={"data": "hello"})
            )

            result = await client._request("GET", "/test")
            assert result == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, client):
        """401 response raises AuthenticationError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(401, json={"detail": "Unauthorized"})
            )

            with pytest.raises(AuthenticationError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self, client):
        """429 response raises RateLimitError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(
                    429,
                    json={"detail": "Too many requests", "retry_after": 30},
                )
            )

            with pytest.raises(RateLimitError) as exc_info:
                await client._request("GET", "/test")

            assert exc_info.value.retry_after == 30

    @pytest.mark.asyncio
    async def test_500_raises_server_error(self, client):
        """5xx response raises ApiServerError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(500, json={"detail": "Internal error"})
            )

            with pytest.raises(ApiServerError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_network_error_raises_server_error(self, client):
        """Network failure raises ApiServerError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            with pytest.raises(ApiServerError, match="Cannot connect"):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_timeout_raises_server_error(self, client):
        """Request timeout raises ApiServerError."""
        timeout_config = _make_config(timeout=0.001)

        from sattabase_sdk import SattabaseClient

        timeout_client = SattabaseClient(timeout_config)

        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                side_effect=httpx.ConnectError("Timeout")
            )

            with pytest.raises(ApiServerError, match="Cannot connect"):
                await timeout_client._request("GET", "/test")

            await timeout_client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        from sattabase_sdk import SattabaseClient

        cfg = _make_config()

        async with SattabaseClient(cfg) as c:
            assert c is not None

        # Client should be closed after context exit


class TestAutoRefresh:
    """Tests for auto-refresh on 401 responses."""

    @pytest.mark.asyncio
    async def test_auto_refresh_retries_on_401(self, client):
        """On 401, SDK auto-refreshes token and retries the original request."""
        from sattabase_sdk.models import TokenPair

        # Pre-populate token store
        tokens = TokenPair(access="old_access", refresh="old_refresh")
        await client._token_store.set_tokens("user_42", tokens)

        call_count = {"count": 0}

        def get_side_effect(request):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return httpx.Response(401, json={"detail": "Token expired"})
            return httpx.Response(200, json={"data": "success"})

        with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(side_effect=get_side_effect)
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/refresh").mock(
                return_value=httpx.Response(
                    200,
                    json={"access": "new_access", "refresh": "new_refresh"},
                )
            )

            result = await client._request("GET", "/test", token="old_access")
            assert result == {"data": "success"}
            # GET /test called twice (401 + retry), POST refresh once
            assert call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_auto_refresh_updates_token_store(self, client):
        """After auto-refresh, token store is updated with new tokens."""
        from sattabase_sdk.models import TokenPair

        await client._token_store.set_tokens(
            "user_42", TokenPair(access="old_access", refresh="old_refresh")
        )

        call_count = {"count": 0}

        def get_side_effect(request):
            call_count["count"] += 1
            if call_count["count"] == 1:
                return httpx.Response(401, json={"detail": "Token expired"})
            return httpx.Response(200, json={"ok": True})

        with respx.mock(assert_all_called=False) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(side_effect=get_side_effect)
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/refresh").mock(
                return_value=httpx.Response(
                    200,
                    json={"access": "refreshed_access", "refresh": "refreshed_refresh"},
                )
            )

            await client._request("GET", "/test", token="old_access")

            # Token store should have new tokens
            updated = await client._token_store.get_tokens("user_42")
            assert updated is not None
            assert updated.access == "refreshed_access"
            assert updated.refresh == "refreshed_refresh"

    @pytest.mark.asyncio
    async def test_no_auto_refresh_when_disabled(self):
        """When auto_refresh=False, 401 raises immediately without refresh."""
        from sattabase_sdk import SattabaseClient
        from sattabase_sdk.config import SattabaseConfig

        config = SattabaseConfig(
            base_url=TEST_BASE_URL,
            service_domain=TEST_SERVICE_DOMAIN,
            api_key=TEST_API_KEY,
            timeout=10.0,
            auto_refresh=False,
            debug=True,
        )
        no_refresh_client = SattabaseClient(config)

        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(401, json={"detail": "Token expired"})
            )

            with pytest.raises(AuthenticationError):
                await no_refresh_client._request("GET", "/test", token="some_token")

            await no_refresh_client.close()

    @pytest.mark.asyncio
    async def test_no_auto_refresh_without_token_store(self):
        """Without token store, 401 raises immediately (no refresh possible)."""
        from sattabase_sdk import SattabaseClient

        no_store_config = _make_config()
        no_store_client = SattabaseClient(no_store_config)

        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(401, json={"detail": "Token expired"})
            )

            with pytest.raises(AuthenticationError):
                await no_store_client._request("GET", "/test", token="some_token")

            await no_store_client.close()

    @pytest.mark.asyncio
    async def test_no_auto_refresh_without_refresh_token(self, client):
        """With empty token store, 401 raises immediately."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=httpx.Response(401, json={"detail": "Token expired"})
            )

            with pytest.raises(AuthenticationError):
                await client._request("GET", "/test", token="some_token")
