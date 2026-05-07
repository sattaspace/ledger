"""Tests for AuthModule — all auth methods."""

from __future__ import annotations

import httpx
import pytest
import respx

from sattabase_sdk.models import MessageResponse, TokenPair

from .conftest import TEST_API_KEY, TEST_BASE_URL, TEST_SERVICE_DOMAIN


class TestAuthLogin:
    """Tests for auth.login()."""

    @pytest.mark.asyncio
    async def test_login_returns_token_pair(self, client):
        """Successful login returns TokenPair with access and refresh."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/login").mock(
                return_value=httpx.Response(
                    200,
                    json={"access": "new_access", "refresh": "new_refresh"},
                )
            )
            tokens = await client.auth.login("user@example.com", "password123")
            assert isinstance(tokens, TokenPair)
            assert tokens.access == "new_access"
            assert tokens.refresh == "new_refresh"

    @pytest.mark.asyncio
    async def test_login_sends_correct_body(self, client):
        """Login sends email and password in JSON body."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.post(f"{TEST_BASE_URL}/auth/login").mock(
                return_value=httpx.Response(
                    200,
                    json={"access": "a", "refresh": "r"},
                )
            )
            await client.auth.login("test@example.com", "MyPass123!")
            body = route.calls[0].request.content
            import json
            data = json.loads(body)
            assert data["email"] == "test@example.com"
            assert data["password"] == "MyPass123!"

    @pytest.mark.asyncio
    async def test_login_401_raises_authentication_error(self, client):
        """Invalid credentials raise AuthenticationError."""
        from sattabase_sdk.exceptions import AuthenticationError

        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/login").mock(
                return_value=httpx.Response(
                    401,
                    json={"detail": "Invalid credentials"},
                )
            )
            with pytest.raises(AuthenticationError):
                await client.auth.login("bad@example.com", "wrong")


class TestAuthRegister:
    """Tests for auth.register()."""

    @pytest.mark.asyncio
    async def test_register_returns_message_response(self, client):
        """Successful registration returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/register").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Registration successful", "success": True},
                )
            )
            result = await client.auth.register(
                email="new@example.com",
                password="Pass123!",
                first_name="Test",
                last_name="User",
            )
            assert isinstance(result, MessageResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_register_sends_optional_fields(self, client):
        """Registration includes timezone/currency/language when provided."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.post(f"{TEST_BASE_URL}/auth/register").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "OK", "success": True},
                )
            )
            await client.auth.register(
                email="new@example.com",
                password="Pass123!",
                first_name="Test",
                last_name="User",
                timezone="Asia/Dhaka",
                currency="BDT",
                language="en",
            )
            import json
            body = json.loads(route.calls[0].request.content)
            assert body["timezone"] == "Asia/Dhaka"
            assert body["currency"] == "BDT"
            assert body["language"] == "en"

    @pytest.mark.asyncio
    async def test_register_omits_optional_fields_when_none(self, client):
        """Registration excludes optional fields when not provided."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.post(f"{TEST_BASE_URL}/auth/register").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "OK", "success": True},
                )
            )
            await client.auth.register(
                email="new@example.com",
                password="Pass123!",
                first_name="Test",
                last_name="User",
            )
            import json
            body = json.loads(route.calls[0].request.content)
            assert "timezone" not in body
            assert "currency" not in body
            assert "language" not in body


class TestAuthRefresh:
    """Tests for auth.refresh()."""

    @pytest.mark.asyncio
    async def test_refresh_returns_new_token_pair(self, client):
        """Successful refresh returns new TokenPair."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/refresh").mock(
                return_value=httpx.Response(
                    200,
                    json={"access": "new_access", "refresh": "new_refresh"},
                )
            )
            tokens = await client.auth.refresh("old_refresh_token")
            assert isinstance(tokens, TokenPair)
            assert tokens.access == "new_access"
            assert tokens.refresh == "new_refresh"

    @pytest.mark.asyncio
    async def test_refresh_sends_refresh_token(self, client):
        """Refresh sends refresh token in JSON body."""
        with respx.mock(assert_all_called=True) as respx_mock:
            route = respx_mock.post(f"{TEST_BASE_URL}/auth/token/refresh").mock(
                return_value=httpx.Response(
                    200,
                    json={"access": "a", "refresh": "r"},
                )
            )
            await client.auth.refresh("my_refresh_token")
            import json
            body = json.loads(route.calls[0].request.content)
            assert body["refresh"] == "my_refresh_token"


class TestAuthVerify:
    """Tests for auth.verify()."""

    @pytest.mark.asyncio
    async def test_verify_returns_message_response(self, client):
        """Token verification returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/verify").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Token is valid", "success": True},
                )
            )
            result = await client.auth.verify("my_access_token")
            assert isinstance(result, MessageResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_verify_invalid_token_raises_error(self, client):
        """Invalid token raises AuthenticationError."""
        from sattabase_sdk.exceptions import AuthenticationError

        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/verify").mock(
                return_value=httpx.Response(
                    401,
                    json={"detail": "Token is invalid or expired"},
                )
            )
            with pytest.raises(AuthenticationError):
                await client.auth.verify("expired_token")


class TestAuthBlacklist:
    """Tests for auth.blacklist()."""

    @pytest.mark.asyncio
    async def test_blacklist_returns_message_response(self, client):
        """Blacklisting returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/blacklist").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Token blacklisted", "success": True},
                )
            )
            result = await client.auth.blacklist("refresh_to_invalidate")
            assert isinstance(result, MessageResponse)


class TestAuthLogout:
    """Tests for auth.logout()."""

    @pytest.mark.asyncio
    async def test_logout_blacklists_and_clears_store(self, client):
        """Logout calls blacklist and clears token store."""
        with respx.mock(assert_all_called=True) as respx_mock:
            # Mock blacklist endpoint
            respx_mock.post(f"{TEST_BASE_URL}/auth/token/blacklist").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Token blacklisted", "success": True},
                )
            )
            # Pre-populate token store
            from sattabase_sdk.models import TokenPair
            tokens = TokenPair(access="a", refresh="my_refresh")
            await client._token_store.set_tokens("user_42", tokens)

            await client.auth.logout("access_token", "my_refresh")

            # Verify token was deleted from store
            result = await client._token_store.get_tokens("user_42")
            assert result is None


class TestPasswordReset:
    """Tests for password reset flow."""

    @pytest.mark.asyncio
    async def test_request_password_reset(self, client):
        """Request password reset returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/password-reset/request").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "OTP sent", "success": True},
                )
            )
            result = await client.auth.request_password_reset("user@example.com")
            assert isinstance(result, MessageResponse)

    @pytest.mark.asyncio
    async def test_confirm_password_reset(self, client):
        """Confirm password reset returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/password-reset/confirm").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Password reset successful", "success": True},
                )
            )
            result = await client.auth.confirm_password_reset(
                email="user@example.com",
                otp="123456",
                new_password="NewPass123!",
                confirm_password="NewPass123!",
            )
            assert isinstance(result, MessageResponse)


class TestEmailVerification:
    """Tests for email verification flow."""

    @pytest.mark.asyncio
    async def test_request_email_verification(self, client):
        """Request email verification returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/verify-email/request").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Verification OTP sent", "success": True},
                )
            )
            result = await client.auth.request_email_verification("user@example.com")
            assert isinstance(result, MessageResponse)

    @pytest.mark.asyncio
    async def test_confirm_email_verification(self, client):
        """Confirm email verification returns MessageResponse."""
        with respx.mock(assert_all_called=True) as respx_mock:
            respx_mock.post(f"{TEST_BASE_URL}/auth/verify-email/confirm").mock(
                return_value=httpx.Response(
                    200,
                    json={"message": "Email verified", "success": True},
                )
            )
            result = await client.auth.confirm_email_verification(
                email="user@example.com",
                otp="654321",
            )
            assert isinstance(result, MessageResponse)
