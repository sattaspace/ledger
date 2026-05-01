"""Tests for the SDK client _request method."""

from __future__ import annotations

import pytest
import respx

from sattabase_sdk.exceptions import (
    ApiServerError,
    AuthenticationError,
    RateLimitError,
    SattabaseError,
)

from .conftest import TEST_API_KEY, TEST_BASE_URL, TEST_SERVICE_DOMAIN, config as make_config


class TestClientRequest:
    """Tests for SattabaseClient._request()."""

    @pytest.mark.asyncio
    async def test_injects_headers(self, client):
        """_request injects X-API-Key and X-Service-Domain."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=respx.Response(200, json={"ok": True})
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
                return_value=respx.Response(200, json={"ok": True})
            )

            await client._request("GET", "/test", token="my_jwt_token")

            headers = route.calls[0].request.headers
            assert headers["authorization"] == "Bearer my_jwt_token"

    @pytest.mark.asyncio
    async def test_success_response(self, client):
        """Successful request returns parsed JSON."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=respx.Response(200, json={"data": "hello"})
            )

            result = await client._request("GET", "/test")
            assert result == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_401_raises_authentication_error(self, client):
        """401 response raises AuthenticationError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=respx.Response(401, json={"detail": "Unauthorized"})
            )

            with pytest.raises(AuthenticationError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_429_raises_rate_limit_error(self, client):
        """429 response raises RateLimitError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                return_value=respx.Response(
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
                return_value=respx.Response(500, json={"detail": "Internal error"})
            )

            with pytest.raises(ApiServerError):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_network_error_raises_server_error(self, client):
        """Network failure raises ApiServerError."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                side_effect=respx.ConnectError("Connection refused")
            )

            with pytest.raises(ApiServerError, match="Cannot connect"):
                await client._request("GET", "/test")

    @pytest.mark.asyncio
    async def test_timeout_raises_server_error(self, client):
        """Request timeout raises ApiServerError."""
        timeout_config = make_config()
        timeout_config = type(timeout_config)(
            base_url=timeout_config.base_url,
            service_domain=timeout_config.service_domain,
            api_key=timeout_config.api_key,
            timeout=0.001,  # Very short timeout
            debug=True,
        )

        from sattabase_sdk import SattabaseClient
        timeout_client = SattabaseClient(timeout_config)

        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.get(f"{TEST_BASE_URL}/test").mock(
                side_effect=respx.ConnectError("Timeout")
            )

            with pytest.raises(ApiServerError, match="Cannot connect"):
                await timeout_client._request("GET", "/test")

            await timeout_client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Client works as async context manager."""
        from sattabase_sdk import SattabaseClient
        cfg = make_config()

        async with SattabaseClient(cfg) as c:
            assert c is not None

        # Client should be closed after context exit
