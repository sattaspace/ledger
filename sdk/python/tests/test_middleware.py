"""Tests for SattabaseAuthMiddleware — token extraction and graceful degradation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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
