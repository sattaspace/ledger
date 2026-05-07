"""Auth module — user authentication against Sattabase."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import AuthMeResponse, MessageResponse, TokenPair
from .token_store import TokenStoreWithLookup

if TYPE_CHECKING:
    from .client import SattabaseClient


class AuthModule:
    """Authentication methods.

    Maps 1:1 to the backend ``AuthController`` endpoints.
    All requests automatically include ``X-API-Key`` and ``X-Service-Domain`` headers.
    """

    def __init__(self, client: SattabaseClient) -> None:
        self._client = client

    async def login(self, email: str, password: str) -> TokenPair:
        """Authenticate a user and obtain JWT tokens.

        Args:
            email: User email address.
            password: User password.

        Returns:
            TokenPair with access and refresh tokens.

        Raises:
            AuthenticationError: Invalid credentials.
        """
        data = await self._client._request(
            "POST",
            "/auth/login",
            json={"email": email, "password": password},
        )
        return TokenPair(**data)

    async def register(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        timezone: str | None = None,
        currency: str | None = None,
        language: str | None = None,
    ) -> MessageResponse:
        """Register a new user account.

        Args:
            email: User email address.
            password: Password (min 8 chars, must include upper, lower, digit, special).
            first_name: User first name.
            last_name: User last name.
            timezone: IANA timezone (e.g. ``Asia/Dhaka``).
            currency: ISO 4217 currency code (e.g. ``BDT``).
            language: ISO 639-1 language code (e.g. ``en``).

        Returns:
            MessageResponse with success status.
        """
        body: dict[str, Any] = {
            "email": email,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        }
        if timezone:
            body["timezone"] = timezone
        if currency:
            body["currency"] = currency
        if language:
            body["language"] = language

        data = await self._client._request(
            "POST",
            "/auth/register",
            json=body,
        )
        return MessageResponse(**data)

    async def me(self, token: str | None = None) -> AuthMeResponse:
        """Get domain-scoped user info, subscription, and access map.

        This is the core method for service domain integration.
        The backend resolves the domain via ``X-API-Key`` → ``ServiceDomain``
        (priority) or ``X-Service-Domain`` header (fallback), and returns
        user data scoped to that domain's product.

        Args:
            token: JWT access token. If None, uses token_store if configured.

        Returns:
            AuthMeResponse with user, subscription, and access data.

        Raises:
            AccountInactiveError: User account deactivated (code: ``account_inactive``).
            AccountDeletedError: User account deleted (code: ``account_deleted``).
            AuthenticationError: Invalid or expired token.
        """
        # Resolve token from store if not provided
        if token is None and self._client._token_store:
            token = await self._resolve_token_from_store()

        data = await self._client._request(
            "GET",
            "/billing/auth/me",
            token=token,
        )
        return AuthMeResponse(**data)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Refresh an expired access token.

        Args:
            refresh_token: The long-lived refresh token.

        Returns:
            New TokenPair.

        Raises:
            AuthenticationError: Invalid or expired refresh token.
        """
        data = await self._client._request(
            "POST",
            "/auth/token/refresh",
            json={"refresh": refresh_token},
        )
        return TokenPair(**data)

    async def verify(self, token: str) -> MessageResponse:
        """Verify an access token is still valid.

        Args:
            token: The access token to verify.

        Returns:
            MessageResponse if token is valid.

        Raises:
            AuthenticationError: Token is invalid or expired.
        """
        data = await self._client._request(
            "POST",
            "/auth/token/verify",
            json={"token": token},
        )
        return MessageResponse(**data)

    async def blacklist(self, refresh_token: str) -> MessageResponse:
        """Blacklist a refresh token (invalidate it).

        Used for explicit logout — the access token will still work until
        it expires (short TTL), but the user cannot get new tokens.

        Args:
            refresh_token: The refresh token to invalidate.

        Returns:
            MessageResponse confirming the action.
        """
        data = await self._client._request(
            "POST",
            "/auth/token/blacklist",
            json={"refresh": refresh_token},
        )
        return MessageResponse(**data)

    async def logout(self, token: str, refresh_token: str) -> None:
        """Logout a user — blacklist refresh token and clear token store.

        Args:
            token: The access token (currently unused, kept for API completeness).
            refresh_token: The refresh token to invalidate.
        """
        await self.blacklist(refresh_token)

        # Clear token store if configured
        store = self._client._token_store
        if store is not None and isinstance(store, TokenStoreWithLookup):
            user_id = await store.get_user_id_by_refresh(refresh_token)
            if user_id:
                await store.delete_tokens(user_id)

    async def request_password_reset(self, email: str) -> MessageResponse:
        """Request a password reset OTP via email.

        Args:
            email: The account email address.

        Returns:
            MessageResponse confirming the OTP was sent.
        """
        data = await self._client._request(
            "POST",
            "/auth/password-reset/request",
            json={"email": email},
        )
        return MessageResponse(**data)

    async def confirm_password_reset(
        self,
        email: str,
        otp: str,
        new_password: str,
        confirm_password: str,
    ) -> MessageResponse:
        """Confirm a password reset with the OTP received via email.

        Args:
            email: The account email address.
            otp: 6-digit OTP code.
            new_password: The new password.
            confirm_password: Must match new_password.

        Returns:
            MessageResponse confirming the password was changed.
        """
        data = await self._client._request(
            "POST",
            "/auth/password-reset/confirm",
            json={
                "email": email,
                "otp": otp,
                "new_password": new_password,
                "confirm_password": confirm_password,
            },
        )
        return MessageResponse(**data)

    async def request_email_verification(self, email: str) -> MessageResponse:
        """Request an email verification OTP.

        Args:
            email: The account email address.

        Returns:
            MessageResponse confirming the OTP was sent.
        """
        data = await self._client._request(
            "POST",
            "/auth/verify-email/request",
            json={"email": email},
        )
        return MessageResponse(**data)

    async def confirm_email_verification(
        self,
        email: str,
        otp: str,
    ) -> MessageResponse:
        """Confirm email verification with OTP.

        Args:
            email: The account email address.
            otp: 6-digit OTP code.

        Returns:
            MessageResponse confirming verification.
        """
        data = await self._client._request(
            "POST",
            "/auth/verify-email/confirm",
            json={"email": email, "otp": otp},
        )
        return MessageResponse(**data)

    # --- Internal helpers ---

    async def _resolve_token_from_store(self) -> str | None:
        """Try to resolve a token from the configured token store.

        Uses the TokenStoreWithLookup protocol instead of accessing
        private ``_store`` attribute directly.
        """
        store = self._client._token_store
        if store is None:
            return None

        if isinstance(store, TokenStoreWithLookup):
            tokens = await store.get_first_token_pair()
            if tokens is not None:
                return tokens.access

        return None
