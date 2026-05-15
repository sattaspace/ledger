"""Tests for SattabaseAuthMiddleware — token extraction, async dispatch, and graceful degradation."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from asgiref.sync import iscoroutinefunction

from sattabase_sdk.middleware import SattabaseAuthMiddleware


def _make_request(META: dict | None = None, COOKIES: dict | None = None, session: dict | None = None):
    """Create a mock Django request object."""
    req = MagicMock()
    req.META = META or {}
    req.COOKIES = COOKIES or {}
    req.session = session or {}
    return req


class TestTokenExtraction:
    """Tests for middleware._extract_token()."""

    def setup_method(self):
        self.middleware = SattabaseAuthMiddleware(get_response=lambda r: r)

    def test_extracts_from_authorization_header(self):
        request = _make_request(META={"HTTP_AUTHORIZATION": "Bearer my_token_123"})
        assert self.middleware._extract_token(request) == "my_token_123"

    def test_extracts_from_authorization_header_with_extra_spaces(self):
        request = _make_request(META={"HTTP_AUTHORIZATION": "Bearer   spaced_token  "})
        assert self.middleware._extract_token(request) == "spaced_token"

    def test_extracts_from_cookie(self):
        request = _make_request(COOKIES={"access_token": "cookie_token"})
        assert self.middleware._extract_token(request) == "cookie_token"

    def test_extracts_from_session(self):
        request = _make_request(session={"access_token": "session_token"})
        assert self.middleware._extract_token(request) == "session_token"

    def test_header_takes_priority_over_cookie_and_session(self):
        request = _make_request(
            META={"HTTP_AUTHORIZATION": "Bearer header_token"},
            COOKIES={"access_token": "cookie_token"},
            session={"access_token": "session_token"},
        )
        assert self.middleware._extract_token(request) == "header_token"

    def test_cookie_takes_priority_over_session(self):
        request = _make_request(
            COOKIES={"access_token": "cookie_token"},
            session={"access_token": "session_token"},
        )
        assert self.middleware._extract_token(request) == "cookie_token"

    def test_returns_none_when_no_token(self):
        request = _make_request()
        assert self.middleware._extract_token(request) is None

    def test_returns_none_for_bearer_without_space(self):
        request = _make_request(META={"HTTP_AUTHORIZATION": "BearerToken"})
        assert self.middleware._extract_token(request) is None

    def test_returns_none_for_wrong_scheme(self):
        request = _make_request(META={"HTTP_AUTHORIZATION": "Basic abc123"})
        assert self.middleware._extract_token(request) is None


class TestGracefulDegradation:
    """Tests for middleware graceful degradation on failure."""

    def test_no_token_sets_attributes_to_none(self):
        """When no token present, sets user=None, access={}, subscription=None."""
        request = _make_request()
        middleware = SattabaseAuthMiddleware(get_response=lambda r: r)
        response = middleware(request)
        assert request.sattabase_user is None
        assert request.sattabase_access == {}
        assert request.sattabase_subscription is None

    @pytest.mark.asyncio
    async def test_async_no_token_sets_attributes_to_none(self):
        """Async path also degrades when no token."""
        request = _make_request()
        async def async_get_response(r):
            return r
        middleware = SattabaseAuthMiddleware(get_response=async_get_response)
        response = await middleware.__acall__(request)
        assert request.sattabase_user is None
        assert request.sattabase_access == {}
        assert request.sattabase_subscription is None


class TestMiddlewareAttributes:
    """Tests for middleware class attributes."""

    def test_sync_capable(self):
        assert SattabaseAuthMiddleware.sync_capable is True

    def test_async_capable(self):
        assert SattabaseAuthMiddleware.async_capable is True


class TestASGIDispatch:
    """Tests for Django 5.2 ASGI middleware dispatch pattern.

    Verifies that the middleware properly dispatches between sync and async
    paths based on whether ``get_response`` is a coroutine function, and that
    ``markcoroutinefunction`` is called so Django's middleware chain can
    correctly await the response.
    """

    def test_sync_mode_no_markcoroutinefunction(self):
        """When get_response is sync, _async_mode is False and markcoroutinefunction is NOT called."""
        middleware = SattabaseAuthMiddleware(get_response=lambda r: r)
        assert middleware._async_mode is False
        assert not iscoroutinefunction(middleware)

    def test_async_mode_calls_markcoroutinefunction(self):
        """When get_response is async, _async_mode is True and markcoroutinefunction is called."""
        async def async_get_response(r):
            return r

        middleware = SattabaseAuthMiddleware(get_response=async_get_response)
        assert middleware._async_mode is True
        assert iscoroutinefunction(middleware)

    def test_sync_call_returns_response_directly(self):
        """Sync __call__ returns the response directly (not a coroutine)."""
        def sync_get_response(r):
            r.status_code = 200
            return r

        middleware = SattabaseAuthMiddleware(get_response=sync_get_response)
        request = _make_request()
        response = middleware(request)
        # Should be the request itself (since sync_get_response returns it)
        assert response is request
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_call_returns_coroutine(self):
        """Async __call__ returns a coroutine that Django can await."""
        async def async_get_response(r):
            r.status_code = 200
            return r

        middleware = SattabaseAuthMiddleware(get_response=async_get_response)
        request = _make_request()

        # __call__ should return a coroutine when _async_mode is True
        result = middleware(request)
        assert asyncio.iscoroutine(result)

        # Awaiting it should give the response
        response = await result
        assert response is request
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_dispatch_no_token(self):
        """Async dispatch with no token sets attributes to None."""
        async def async_get_response(r):
            return r

        middleware = SattabaseAuthMiddleware(get_response=async_get_response)
        request = _make_request()
        response = await middleware(request)
        assert request.sattabase_user is None
        assert request.sattabase_access == {}
        assert request.sattabase_subscription is None
        assert request.sattabase_exchange_rates is None
        assert request.sattabase_currencies is None

    @pytest.mark.asyncio
    async def test_async_dispatch_uses_acall(self):
        """Verify __call__ dispatches to __acall__ in async mode."""
        call_count = 0

        async def async_get_response(r):
            nonlocal call_count
            call_count += 1
            return r

        middleware = SattabaseAuthMiddleware(get_response=async_get_response)
        request = _make_request()

        # Calling middleware(request) should go through __acall__
        await middleware(request)
        assert call_count == 1

    def test_sync_dispatch_with_no_token(self):
        """Sync dispatch with no token sets attributes to None."""
        def sync_get_response(r):
            return r

        middleware = SattabaseAuthMiddleware(get_response=sync_get_response)
        request = _make_request()
        response = middleware(request)
        assert request.sattabase_user is None
        assert request.sattabase_access == {}
        assert request.sattabase_subscription is None
