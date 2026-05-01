"""Tests for configuration and exceptions."""

from __future__ import annotations

import pytest
import respx

from sattabase_sdk.config import SattabaseConfig
from sattabase_sdk.exceptions import (
    AccountDeletedError,
    AccountInactiveError,
    ApiServerError,
    AuthenticationError,
    BadRequestError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    SattabaseError,
    build_error,
)
from .conftest import TEST_API_KEY, TEST_BASE_URL, TEST_SERVICE_DOMAIN


class TestSattabaseConfig:
    """Tests for SattabaseConfig validation."""

    def test_valid_config(self):
        config = SattabaseConfig(
            base_url=TEST_BASE_URL,
            service_domain=TEST_SERVICE_DOMAIN,
            api_key=TEST_API_KEY,
        )
        assert config.api_key == TEST_API_KEY
        assert config.app_base_url == "https://sattabase.tld"

    def test_invalid_api_key_format(self):
        with pytest.raises(ValueError, match="must start with 'sb_live_'"):
            SattabaseConfig(
                base_url=TEST_BASE_URL,
                service_domain=TEST_SERVICE_DOMAIN,
                api_key="invalid_key_format",
            )

    def test_http_not_allowed_in_production(self):
        with pytest.raises(ValueError, match="HTTPS"):
            SattabaseConfig(
                base_url="http://sattabase.tld/api/v1",
                service_domain=TEST_SERVICE_DOMAIN,
                api_key=TEST_API_KEY,
            )

    def test_http_allowed_in_debug(self):
        config = SattabaseConfig(
            base_url="http://localhost:8000/api/v1",
            service_domain=TEST_SERVICE_DOMAIN,
            api_key=TEST_API_KEY,
            debug=True,
        )
        assert config.app_base_url == "http://localhost:8000"

    def test_app_base_url_strips_api_v1(self):
        config = SattabaseConfig(
            base_url="https://sattabase.tld/api/v1",
            service_domain=TEST_SERVICE_DOMAIN,
            api_key=TEST_API_KEY,
        )
        assert config.app_base_url == "https://sattabase.tld"

    def test_app_base_url_no_api_suffix(self):
        config = SattabaseConfig(
            base_url="https://api.sattabase.tld",
            service_domain=TEST_SERVICE_DOMAIN,
            api_key=TEST_API_KEY,
        )
        assert config.app_base_url == "https://api.sattabase.tld"


class TestBuildError:
    """Tests for error construction from HTTP responses."""

    def test_authentication_error_by_status(self):
        err = build_error(401, {"detail": "Invalid token"})
        assert isinstance(err, AuthenticationError)
        assert err.status == 401
        assert "Invalid token" in err.message

    def test_forbidden_error_by_status(self):
        err = build_error(403, {"detail": "No permission"})
        assert isinstance(err, ForbiddenError)

    def test_not_found_error_by_status(self):
        err = build_error(404, {"detail": "Not found"})
        assert isinstance(err, NotFoundError)

    def test_bad_request_error_by_status(self):
        err = build_error(400, {"detail": "Bad request"})
        assert isinstance(err, BadRequestError)

    def test_server_error_by_status(self):
        err = build_error(500, {"detail": "Internal error"})
        assert isinstance(err, ApiServerError)

    def test_account_inactive_by_code(self):
        err = build_error(401, {"detail": "Inactive", "code": "account_inactive"})
        assert isinstance(err, AccountInactiveError)
        assert err.status == 401

    def test_account_deleted_by_code(self):
        err = build_error(401, {"detail": "Deleted", "code": "account_deleted"})
        assert isinstance(err, AccountDeletedError)

    def test_rate_limit_with_retry_after(self):
        err = build_error(429, {"detail": "Too many", "retry_after": 60})
        assert isinstance(err, RateLimitError)
        assert err.retry_after == 60

    def test_none_body(self):
        err = build_error(500, None)
        assert isinstance(err, ApiServerError)

    def test_code_takes_priority_over_status(self):
        # Code 'account_inactive' maps to AccountInactiveError (403)
        # even though status is 401
        err = build_error(401, {"detail": "Inactive", "code": "account_inactive"})
        assert isinstance(err, AccountInactiveError)
