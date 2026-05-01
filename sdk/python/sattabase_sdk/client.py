"""Sattabase SDK client — main entry point."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import httpx

from .auth import AuthModule
from .config import SattabaseConfig
from .exceptions import (
    ApiServerError,
    AuthenticationError,
    SattabaseError,
    build_error,
)
from .models import TokenPair
from .redirect import BillingRedirectModule
from .access import AccessModule
from .token_store import TokenStore

logger = logging.getLogger("sattabase_sdk")


class SattabaseClient:
    """Async client for the Sattabase API.

    Usage::

        config = SattabaseConfig(
            base_url="https://sattabase.tld/api/v1",
            service_domain="finance.sattabase.tld",
            api_key="sb_live_...",
        )

        async with SattabaseClient(config) as client:
            tokens = await client.auth.login("user@example.com", "password")
            auth_me = await client.auth.me(tokens.access)
            if auth_me.has_access("reports"):
                ...
    """

    def __init__(
        self,
        config: SattabaseConfig,
        token_store: TokenStore | None = None,
    ) -> None:
        self.config = config
        self._token_store = token_store
        self._http_client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=httpx.Timeout(config.timeout),
            headers={
                "X-API-Key": config.api_key,
                "X-Service-Domain": config.service_domain,
                "Content-Type": "application/json",
            },
        )
        # Refresh lock to prevent concurrent refresh calls
        self._refresh_lock = asyncio.Lock()
        self._refreshing = False

        # Namespaces
        self.auth = AuthModule(self)
        self.access = AccessModule(self)
        self.billing = BillingRedirectModule(self)

    # --- Context manager ---

    async def __aenter__(self) -> SattabaseClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._http_client.aclose()

    # --- Internal request method ---

    async def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json: dict[str, Any] | None = None,
        _retry_count: int = 0,
        **kwargs: Any,
    ) -> dict[str, Any] | list[Any]:
        """Send an API request to Sattabase.

        Automatically injects ``X-API-Key`` and ``X-Service-Domain`` headers.
        Optionally injects ``Authorization: Bearer {token}``.

        Handles auto-refresh on 401 when ``auto_refresh=True``.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            path: API path (e.g. ``/auth/login``).
            token: Optional JWT access token for user-authenticated requests.
            json: Request body (will be serialized as JSON).
            _retry_count: Internal counter for auto-refresh retries.
            **kwargs: Additional arguments passed to ``httpx.request``.

        Returns:
            Parsed JSON response body.

        Raises:
            SattabaseError: On API errors (mapped by status code).
        """
        headers = dict(kwargs.pop("headers", {}))
        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.debug(
            "Sattabase %s %s (token=%s)",
            method,
            path,
            "yes" if token else "no",
        )

        try:
            response = await self._http_client.request(
                method=method,
                url=path,
                json=json,
                headers=headers,
                **kwargs,
            )
        except httpx.TimeoutException as exc:
            raise ApiServerError(
                message=f"Request to {path} timed out after {self.config.timeout}s",
                detail={"path": path, "timeout": self.config.timeout},
            ) from exc
        except httpx.ConnectError as exc:
            raise ApiServerError(
                message=f"Cannot connect to Sattabase at {self.config.base_url}",
                detail={"base_url": self.config.base_url},
            ) from exc

        # Parse response body
        try:
            body = response.json()
        except Exception:
            body = None

        # Success
        if response.is_success:
            return body

        # 401 — attempt auto-refresh
        if (
            response.status_code == 401
            and token
            and self.config.auto_refresh
            and _retry_count <= self.config.max_retries
        ):
            new_token = await self._try_refresh(token)
            if new_token:
                return await self._request(
                    method,
                    path,
                    token=new_token,
                    json=json,
                    _retry_count=_retry_count + 1,
                    **kwargs,
                )

        # Error — map to typed exception
        code = None
        if isinstance(body, dict):
            code = body.get("code")
        raise build_error(response.status_code, body, code)

    async def _try_refresh(self, failed_token: str) -> str | None:
        """Attempt to refresh the access token.

        Returns the new access token on success, None on failure.
        Uses a lock to prevent concurrent refresh calls.
        """
        if self._refreshing:
            # Another coroutine is already refreshing — wait for it
            await asyncio.sleep(0.5)
            return None

        async with self._refresh_lock:
            self._refreshing = True
            try:
                if not self._token_store:
                    return None

                # Find the user_id by iterating stores (in-memory)
                # In production, the caller should pass user_id context
                refresh_token = await self._find_refresh_token()
                if not refresh_token:
                    return None

                try:
                    result = await self._http_client.post(
                        "/auth/token/refresh",
                        json={"refresh": refresh_token},
                    )
                    if result.is_success:
                        data = result.json()
                        new_tokens = TokenPair(**data)
                        # Store new tokens — find user_id from store
                        user_id = await self._find_user_id_by_refresh(refresh_token)
                        if user_id and self._token_store:
                            await self._token_store.set_tokens(user_id, new_tokens)
                        logger.debug("Token refreshed successfully")
                        return new_tokens.access
                except Exception as exc:
                    logger.warning("Token refresh failed: %s", exc)
                return None
            finally:
                self._refreshing = False

    async def _find_refresh_token(self) -> str | None:
        """Find a refresh token from the token store.

        This is a simple approach for the initial SDK version.
        Production implementations should pass user_id context.
        """
        if not self._token_store or not hasattr(self._token_store, "_store"):
            return None
        store = getattr(self._token_store, "_store", {})
        for tokens in store.values():
            if isinstance(tokens, TokenPair):
                return tokens.refresh
        return None

    async def _find_user_id_by_refresh(self, refresh_token: str) -> str | None:
        """Find user_id by matching refresh token in the store."""
        if not self._token_store or not hasattr(self._token_store, "_store"):
            return None
        store = getattr(self._token_store, "_store", {})
        for user_id, tokens in store.items():
            if isinstance(tokens, TokenPair) and tokens.refresh == refresh_token:
                return user_id
        return None
