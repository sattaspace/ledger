"""Shared test constants and fixtures for sattabase_sdk tests."""

from __future__ import annotations

import pytest

from sattabase_sdk.config import SattabaseConfig
from sattabase_sdk.token_store import InMemoryTokenStore

# =============================================================================
# Test constants
# =============================================================================

TEST_API_KEY = "sb_live_abcd1234efgh5678ijkl9012mnop3456"
TEST_BASE_URL = "https://sattabase.tld/api/v1"
TEST_SERVICE_DOMAIN = "finance.sattabase.tld"

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def config():
    """Create a SattabaseConfig for testing."""
    return SattabaseConfig(
        base_url=TEST_BASE_URL,
        service_domain=TEST_SERVICE_DOMAIN,
        api_key=TEST_API_KEY,
        timeout=10.0,
        auto_refresh=True,
        debug=True,
    )


@pytest.fixture
def client(config):
    """Create a SattabaseClient with InMemoryTokenStore for testing.

    The client is async-compatible — tests must use ``@pytest.mark.asyncio``
    and ``async def test_*``.
    """
    from sattabase_sdk import SattabaseClient

    token_store = InMemoryTokenStore()
    c = SattabaseClient(config, token_store=token_store)
    yield c
    # Teardown: close the HTTP client after each test
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(c.close())
    except RuntimeError:
        asyncio.run(c.close())


@pytest.fixture
def token_response():
    """Dict with access and refresh tokens (mirrors TokenPair schema)."""
    return {
        "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_access_payload.signature",
        "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_refresh_payload.signature",
    }


@pytest.fixture
def auth_me_response():
    """Dict matching AuthMeResponse schema with user, subscription, and access."""
    return {
        "user": {
            "id": 1,
            "slug": "test-user",
            "email": "user@example.com",
            "first_name": "Test",
            "last_name": "User",
            "phone": None,
            "avatar": None,
            "timezone": "UTC",
            "currency": "USD",
            "language": "en",
            "is_email_verified": True,
            "is_active": True,
            "role": "member",
            "created_at": "2025-01-01T00:00:00Z",
            "full_name": "Test User",
            "display_name": "Test User",
        },
        "account_status": "active",
        "subscription": {
            "plan_name": "Pro",
            "plan_slug": "pro",
            "status": "active",
            "current_period_end": "2026-01-01T00:00:00Z",
            "trial_end": None,
            "is_active": True,
        },
        "access": {
            "dashboard": True,
            "reports": True,
            "expense_tracking": True,
            "priority_support": False,
            "export": False,
            "api_access": True,
            "max_bank_accounts": 5,
            "max_team_members": 3,
            "data_retention_days": 365,
        },
    }
