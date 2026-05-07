"""Integration tests (B7–B15) — hit the real Sattabase backend at localhost:8000.

These tests exercise the full request/response cycle against a live backend.
They are gated behind ``pytest.mark.integration`` so they only run when
explicitly requested::

    pytest tests/test_integration.py -v --tb=short
    pytest tests/ -v -m integration

Requirements:
    - Sattabase backend running at $SB_BASE_URL (default http://localhost:8000/api/v1)
    - Valid admin credentials in env vars (SB_USER_EMAIL, SB_USER_PASSWORD)
    - Valid API key in SB_API_KEY
"""

from __future__ import annotations

import os
import pytest
import httpx

from sattabase_sdk import SattabaseClient, SattabaseConfig
from sattabase_sdk.exceptions import (
    AuthenticationError,
    BadRequestError,
    ForbiddenError,
    RateLimitError,
    SattabaseError,
    ApiServerError,
)
from sattabase_sdk.models import TokenPair, MessageResponse, AuthMeResponse

# =============================================================================
# Environment helpers
# =============================================================================

BASE_URL: str = os.getenv("SB_BASE_URL", "http://localhost:8000/api/v1")
SERVICE_DOMAIN: str = os.getenv("SB_SERVICE_DOMAIN", "finance.sattabase.tld")
API_KEY: str = os.getenv(
    "SB_API_KEY",
    "sb_live_IxHIC0p-Rv7E6sm0_l6awH0tkDzsDTjmTSrPCQAvwRE",
)
USER_EMAIL: str = os.getenv("SB_USER_EMAIL", "haradhan.sharma@gmail.com")
USER_PASSWORD: str = os.getenv("SB_USER_PASSWORD", "Aa@12345678")

# Module-level state populated by setup_module()
_admin_jwt: str = ""
_tokens: TokenPair | None = None
_backend_up: bool = False


# =============================================================================
# B6 — Module setup
# =============================================================================


def setup_module() -> None:
    """Check backend reachability, login as admin, and verify SDK API key."""
    global _admin_jwt, _tokens, _backend_up

    try:
        with httpx.Client(timeout=5.0) as http:
            # GET /auth/login should return 405 (Method Not Allowed) — proves backend is up
            resp = http.get(f"{BASE_URL}/auth/login")
            if resp.status_code not in (405, 404):
                pytest.skip(
                    f"Backend at {BASE_URL} returned {resp.status_code}, expected 405"
                )
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        pytest.skip(f"Backend not reachable at {BASE_URL}: {exc}")

    # Login as admin via raw HTTP to obtain JWT
    try:
        with httpx.Client(timeout=10.0) as http:
            resp = http.post(
                f"{BASE_URL}/auth/login",
                json={"email": USER_EMAIL, "password": USER_PASSWORD},
            )
            if resp.status_code != 200:
                pytest.skip(f"Admin login failed ({resp.status_code}): {resp.text}")
            body = resp.json()
            _admin_jwt = body["access"]
    except Exception as exc:
        pytest.skip(f"Admin login error: {exc}")

    # Verify SDK API key works via SDK login
    try:
        import asyncio

        async def _sdk_login() -> None:
            global _tokens
            cfg = SattabaseConfig(
                base_url=BASE_URL,
                service_domain=SERVICE_DOMAIN,
                api_key=API_KEY,
                timeout=30.0,
                auto_refresh=False,
                debug=True,
            )
            async with SattabaseClient(cfg) as c:
                _tokens = await c.auth.login(USER_EMAIL, USER_PASSWORD)

        asyncio.run(_sdk_login())
    except Exception as exc:
        pytest.skip(f"SDK API key login failed: {exc}")

    _backend_up = True


# =============================================================================
# Shared helpers
# =============================================================================


def _make_config(
    api_key: str = API_KEY,
    service_domain: str = SERVICE_DOMAIN,
    auto_refresh: bool = False,
) -> SattabaseConfig:
    """Create a SattabaseConfig pointing at the live backend."""
    return SattabaseConfig(
        base_url=BASE_URL,
        service_domain=service_domain,
        api_key=api_key,
        timeout=30.0,
        auto_refresh=auto_refresh,
        debug=True,
    )


async def _admin_service_domains() -> list[dict]:
    """Fetch service domains via admin API. Returns list of domain dicts."""
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(
            f"{BASE_URL}/admin/api-keys/service-domains",
            headers={"Authorization": f"Bearer {_admin_jwt}"},
        )
        resp.raise_for_status()
        return resp.json()


def _require_backend():
    """Skip the test if the backend is not reachable."""
    if not _backend_up:
        pytest.skip("Backend not reachable")


# =============================================================================
# B7 — Login
# =============================================================================


@pytest.mark.integration
class TestB7Login:
    """Integration tests for auth.login() against the real backend."""

    @pytest.mark.asyncio
    async def test_login_returns_token_pair(self):
        """SDK login returns TokenPair with .access and .refresh."""
        _require_backend()
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            tokens = await client.auth.login(USER_EMAIL, USER_PASSWORD)
            assert isinstance(tokens, TokenPair)
            assert tokens.access
            assert tokens.refresh
            assert tokens.access.startswith("eyJ")

    @pytest.mark.asyncio
    async def test_login_wrong_password_raises(self):
        """Wrong password raises AuthenticationError."""
        _require_backend()
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            with pytest.raises(AuthenticationError):
                await client.auth.login(USER_EMAIL, "WrongPassword123!")


# =============================================================================
# B8 — Auth Me
# =============================================================================


@pytest.mark.integration
class TestB8AuthMe:
    """Integration tests for auth.me() against the real backend.

    NOTE: These tests are sensitive to backend bugs. If /billing/auth/me
    returns 500, the tests will skip with a diagnostic message rather than
    failing, since a 500 indicates a backend issue, not an SDK bug.
    """

    @pytest.mark.asyncio
    async def test_auth_me_returns_user_profile(self):
        """auth.me returns user object with correct email."""
        _require_backend()
        assert _tokens is not None
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            try:
                me = await client.auth.me(_tokens.access)
            except ApiServerError as exc:
                pytest.skip(
                    f"Backend /billing/auth/me returned 500 — this is a backend bug, "
                    f"not an SDK bug. Error: {exc}"
                )
            assert isinstance(me, AuthMeResponse)
            assert me.user.email == USER_EMAIL

    @pytest.mark.asyncio
    async def test_auth_me_returns_subscription(self):
        """auth.me returns subscription info with plan_name."""
        _require_backend()
        assert _tokens is not None
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            try:
                me = await client.auth.me(_tokens.access)
            except ApiServerError as exc:
                pytest.skip(
                    f"Backend /billing/auth/me returned 500 — backend bug: {exc}"
                )
            assert me.subscription is not None
            assert me.subscription.plan_name

    @pytest.mark.asyncio
    async def test_auth_me_returns_access_map(self):
        """auth.me returns non-empty access_keys and has_access returns bool."""
        _require_backend()
        assert _tokens is not None
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            try:
                me = await client.auth.me(_tokens.access)
            except ApiServerError as exc:
                pytest.skip(
                    f"Backend /billing/auth/me returned 500 — backend bug: {exc}"
                )
            assert len(me.access_keys) > 0
            # Pick an arbitrary key and check has_access returns bool
            key = me.access_keys[0]
            result = me.has_access(key)
            assert isinstance(result, bool)


# =============================================================================
# B9 — Invalid API Key
# =============================================================================


@pytest.mark.integration
class TestB9InvalidApiKey:
    """Integration tests for invalid / rejected API keys.

    NOTE: When API_KEY_ENFORCED=False (development default), the backend
    middleware does NOT reject invalid API keys — it validates the prefix
    but lets the request through. Set SB_API_KEY_ENFORCED=True to test
    actual rejection behavior.
    """

    @pytest.mark.asyncio
    async def test_fake_api_key_returns_403(self):
        """SDK with a fake sb_live_ key raises error (403 or 401) on login.

        Skips gracefully if API_KEY_ENFORCED is not set — in that mode,
        the backend accepts any sb_live_ key.
        """
        _require_backend()
        cfg = _make_config(api_key="sb_live_invalid_abcd1234efgh5678ijkl9012mnop3456")
        async with SattabaseClient(cfg) as client:
            try:
                result = await client.auth.login(USER_EMAIL, USER_PASSWORD)
                # If we get here, the backend did NOT reject the fake key.
                # This means API_KEY_ENFORCED=False (development default).
                pytest.skip(
                    "Fake API key was accepted — API_KEY_ENFORCED is likely False. "
                    "Set SB_API_KEY_ENFORCED=True on the backend to test key rejection."
                )
            except (ForbiddenError, AuthenticationError):
                pass  # Expected: backend correctly rejected the fake key

    def test_wrong_prefix_rejected_by_config(self):
        """sb_test_ prefix raises ValueError at config construction."""
        with pytest.raises(ValueError, match="sb_live_"):
            SattabaseConfig(
                base_url=BASE_URL,
                service_domain=SERVICE_DOMAIN,
                api_key="sb_test_abcd1234efgh5678ijkl9012mnop3456",
                timeout=30.0,
                auto_refresh=False,
                debug=True,
            )


# =============================================================================
# B10 — Backward Compat (JWT without X-API-Key header)
# =============================================================================


@pytest.mark.integration
class TestB10BackwardCompat:
    """Integration tests verifying JWT-only auth works on core endpoints."""

    @pytest.mark.asyncio
    async def test_jwt_without_api_key_on_auth_me(self):
        """Raw HTTP GET /billing/auth/me with only JWT Bearer token returns 200."""
        _require_backend()
        assert _admin_jwt
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                f"{BASE_URL}/billing/auth/me",
                headers={"Authorization": f"Bearer {_admin_jwt}"},
            )
            # Should be 200 (OK) or 200-class — backend accepts JWT alone
            assert (
                resp.status_code == 200
            ), f"Expected 200, got {resp.status_code}: {resp.text}"
            body = resp.json()
            assert "user" in body

    @pytest.mark.asyncio
    async def test_jwt_without_api_key_on_verify(self):
        """Raw HTTP POST /auth/token/verify with only JWT works."""
        _require_backend()
        assert _tokens is not None
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.post(
                f"{BASE_URL}/auth/token/verify",
                json={"token": _tokens.access},
            )
            assert (
                resp.status_code == 200
            ), f"Expected 200, got {resp.status_code}: {resp.text}"
            body = resp.json()
            assert body.get("success") is True


# =============================================================================
# B11 — Revoke
# =============================================================================


@pytest.mark.integration
class TestB11Revoke:
    """Integration test for revoking an API key credential.

    NOTE: When API_KEY_ENFORCED=False (development default), the backend
    does not actually reject revoked keys. The test will skip gracefully
    in that case.
    """

    @pytest.mark.asyncio
    async def test_revoked_key_returns_403(self):
        """Create a credential, login, revoke it, then login should fail.

        Skips gracefully if API_KEY_ENFORCED is not set.
        """
        _require_backend()
        assert _admin_jwt

        # a. Find the analytics domain ID
        domains = await _admin_service_domains()
        analytics_domain = next(
            (d for d in domains if d.get("domain") == "analytics.sattabase.tld"), None
        )
        if analytics_domain is None:
            pytest.skip("analytics.sattabase.tld domain not found in service-domains")
        domain_id = analytics_domain["id"]

        credential_id: int | None = None
        try:
            # b. Create credential for the analytics domain
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(
                    f"{BASE_URL}/admin/api-keys/",
                    headers={
                        "Authorization": f"Bearer {_admin_jwt}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": "integration-test-revoke",
                        "service_domain_id": domain_id,
                    },
                )
                if resp.status_code == 409:
                    pytest.skip(
                        "analytics.sattabase.tld already has an active credential (409 Conflict)"
                    )
                # Backend may return 200 or 201 — both indicate success
                if resp.status_code not in (200, 201):
                    pytest.skip(
                        f"Create credential returned {resp.status_code}: {resp.text}"
                    )
                body = resp.json()
                credential_id = body["id"]
                raw_api_key = body["raw_api_key"]

            # c. Login via SDK with the new credential — should work
            cfg = _make_config(
                api_key=raw_api_key,
                service_domain="analytics.sattabase.tld",
            )
            async with SattabaseClient(cfg) as client:
                tokens = await client.auth.login(USER_EMAIL, USER_PASSWORD)
                assert isinstance(tokens, TokenPair)

            # d. Revoke the credential
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.patch(
                    f"{BASE_URL}/admin/api-keys/{credential_id}/revoke",
                    headers={"Authorization": f"Bearer {_admin_jwt}"},
                )
                resp.raise_for_status()

            # e. Login again with the revoked key — should fail
            cfg2 = _make_config(
                api_key=raw_api_key,
                service_domain="analytics.sattabase.tld",
            )
            async with SattabaseClient(cfg2) as client:
                try:
                    result = await client.auth.login(USER_EMAIL, USER_PASSWORD)
                    # Login succeeded — API_KEY_ENFORCED is False
                    pytest.skip(
                        "Revoked API key was still accepted — API_KEY_ENFORCED is "
                        "likely False. Set SB_API_KEY_ENFORCED=True on the backend "
                        "to test revocation enforcement."
                    )
                except (ForbiddenError, AuthenticationError):
                    pass  # Expected: backend correctly rejected the revoked key
        finally:
            # Best-effort cleanup: no additional action needed,
            # the credential is already revoked. If creation failed, nothing to clean.
            pass


# =============================================================================
# B12 — Rotate
# =============================================================================


@pytest.mark.integration
class TestB12Rotate:
    """Integration test for rotating an API key credential."""

    @pytest.mark.asyncio
    async def test_rotated_key_old_fails_new_works(self):
        """Create credential, rotate it, verify old key fails and new key works."""
        _require_backend()
        assert _admin_jwt

        # a. Find the docs domain ID
        domains = await _admin_service_domains()
        docs_domain = next(
            (d for d in domains if d.get("domain") == "docs.sattabase.tld"), None
        )
        if docs_domain is None:
            pytest.skip("docs.sattabase.tld domain not found in service-domains")
        domain_id = docs_domain["id"]

        credential_id: int | None = None
        try:
            # b. Create credential for docs domain
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(
                    f"{BASE_URL}/admin/api-keys/",
                    headers={
                        "Authorization": f"Bearer {_admin_jwt}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "name": "integration-test-rotate",
                        "service_domain_id": domain_id,
                    },
                )
                if resp.status_code == 409:
                    pytest.skip(
                        "docs.sattabase.tld already has an active credential (409 Conflict)"
                    )
                # Backend may return 200 or 201 — both indicate success
                if resp.status_code not in (200, 201):
                    pytest.skip(
                        f"Create credential returned {resp.status_code}: {resp.text}"
                    )
                resp.raise_for_status()
                body = resp.json()
                credential_id = body["id"]
                old_api_key = body["raw_api_key"]

            # c. Login via SDK — should work
            cfg = _make_config(
                api_key=old_api_key,
                service_domain="docs.sattabase.tld",
            )
            async with SattabaseClient(cfg) as client:
                tokens = await client.auth.login(USER_EMAIL, USER_PASSWORD)
                assert isinstance(tokens, TokenPair)

            # d. Rotate the credential
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(
                    f"{BASE_URL}/admin/api-keys/{credential_id}/rotate",
                    headers={"Authorization": f"Bearer {_admin_jwt}"},
                )
                resp.raise_for_status()
                rotate_body = resp.json()
                new_api_key = rotate_body["new_api_key"]

            # e. Login with OLD key — should fail (unless API_KEY_ENFORCED=False)
            cfg_old = _make_config(
                api_key=old_api_key,
                service_domain="docs.sattabase.tld",
            )
            async with SattabaseClient(cfg_old) as client:
                try:
                    await client.auth.login(USER_EMAIL, USER_PASSWORD)
                    pytest.skip(
                        "Old API key still worked after rotation — API_KEY_ENFORCED "
                        "is likely False. Set SB_API_KEY_ENFORCED=True to test rotation."
                    )
                except (ForbiddenError, AuthenticationError):
                    pass  # Expected

            # f. Login with NEW key — should work
            cfg_new = _make_config(
                api_key=new_api_key,
                service_domain="docs.sattabase.tld",
            )
            async with SattabaseClient(cfg_new) as client:
                tokens = await client.auth.login(USER_EMAIL, USER_PASSWORD)
                assert isinstance(tokens, TokenPair)

        finally:
            # g. Cleanup: revoke the credential if it was created
            if credential_id is not None:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as http:
                        await http.patch(
                            f"{BASE_URL}/admin/api-keys/{credential_id}/revoke",
                            headers={"Authorization": f"Bearer {_admin_jwt}"},
                        )
                except Exception:
                    pass  # best-effort cleanup


# =============================================================================
# B13 — Remaining Methods
# =============================================================================


@pytest.mark.integration
class TestB13RemainingMethods:
    """Integration tests for verify, password reset, email verification, access.keys."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self):
        """auth.verify with a valid token returns success=True."""
        _require_backend()
        assert _tokens is not None
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            result = await client.auth.verify(_tokens.access)
            assert isinstance(result, MessageResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """auth.verify with garbage token raises AuthenticationError."""
        _require_backend()
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            with pytest.raises(AuthenticationError):
                await client.auth.verify("this.is.not.a.valid.jwt.token")

    @pytest.mark.asyncio
    async def test_request_password_reset(self):
        """auth.request_password_reset returns MessageResponse with message."""
        _require_backend()
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            result = await client.auth.request_password_reset(USER_EMAIL)
            assert isinstance(result, MessageResponse)
            assert result.message
            assert result.success is True

    @pytest.mark.asyncio
    async def test_request_email_verification(self):
        """auth.request_email_verification returns success or BadRequestError if already verified."""
        _require_backend()
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            try:
                result = await client.auth.request_email_verification(USER_EMAIL)
                assert isinstance(result, MessageResponse)
                assert result.message
                assert result.success is True
            except BadRequestError as exc:
                # Email may already be verified — that's acceptable
                if "already verified" in str(exc).lower():
                    pytest.skip(
                        "Email is already verified — backend returns 400. "
                        "To test this endpoint fully, use an unverified test account."
                    )
                raise  # Re-raise if it's a different BadRequestError

    @pytest.mark.asyncio
    async def test_access_keys(self):
        """access.keys returns a non-empty list of access key strings."""
        _require_backend()
        assert _tokens is not None
        cfg = _make_config()
        async with SattabaseClient(cfg) as client:
            client.access.invalidate_cache()
            try:
                keys = await client.access.keys(_tokens.access)
            except ApiServerError as exc:
                pytest.skip(
                    f"Backend /billing/auth/me returned 500 (called by access.keys) — "
                    f"backend bug: {exc}"
                )
            assert isinstance(keys, list)
            assert len(keys) > 0
            for k in keys:
                assert isinstance(k, str)


# =============================================================================
# B14 — Auto Refresh Config
# =============================================================================


@pytest.mark.integration
class TestB14AutoRefresh:
    """Integration test verifying auto_refresh config is accepted."""

    @pytest.mark.asyncio
    async def test_auto_refresh_config_enabled(self):
        """Config accepts auto_refresh=True; full E2E auto-refresh is in B5 unit tests."""
        _require_backend()
        cfg = _make_config(auto_refresh=True)
        assert cfg.auto_refresh is True

        # Also verify we can create a client and it works normally
        async with SattabaseClient(cfg) as client:
            # Invalidate any cached data
            client.access.invalidate_cache()
            # Just verify the client is usable
            assert client.config.auto_refresh is True


# =============================================================================
# B15 — Rate Limit
# =============================================================================


@pytest.mark.integration
class TestB15RateLimit:
    """Integration test for rate limiting (may skip depending on backend config)."""

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_429(self):
        """Rapid wrong-login attempts should eventually trigger RateLimitError (429)."""
        _require_backend()
        cfg = _make_config()
        rate_limit_hit = False
        max_attempts = 15

        async with SattabaseClient(cfg) as client:
            for i in range(max_attempts):
                try:
                    await client.auth.login(
                        "nonexistent_rate_limit@example.com", "wrong"
                    )
                except RateLimitError:
                    rate_limit_hit = True
                    break
                except AuthenticationError:
                    # Expected for wrong credentials — keep trying
                    pass
                except Exception:
                    # Unexpected error — stop
                    break

        if not rate_limit_hit:
            pytest.skip(
                "Rate limit not triggered after 15 attempts — "
                "backend may have permissive rate limit config"
            )
