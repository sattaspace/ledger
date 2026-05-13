"""Pydantic v2 models that mirror the Sattabase backend schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Auth Tokens
# =============================================================================


class TokenPair(BaseModel):
    """JWT token pair returned by login and refresh endpoints.

    Mirrors backend ``TokenOutputSchema``.
    """

    access: str = Field(..., description="Access token (short-lived)")
    refresh: str = Field(..., description="Refresh token (long-lived)")


# =============================================================================
# User
# =============================================================================


class User(BaseModel):
    """User profile data.

    Mirrors backend ``UserOutputSchema``.
    """

    id: int
    slug: str
    email: str
    first_name: str = ""
    last_name: str = ""
    phone: Optional[str] = None
    avatar: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    language: Optional[str] = None
    is_email_verified: bool = False
    is_active: bool = True
    role: str = "member"
    created_at: Optional[datetime] = None
    full_name: str = ""
    display_name: str = ""

    @property
    def display(self) -> str:
        """Return the best display name available."""
        return self.display_name or self.full_name or self.email.split("@")[0]


# =============================================================================
# Subscription
# =============================================================================


class SubscriptionInfo(BaseModel):
    """Subscription summary returned in auth/me response.

    Mirrors backend ``SubscriptionInfoSchema``.
    """

    plan_name: str
    plan_slug: str
    status: str
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    is_active: bool = True


# =============================================================================
# Auth Me Response
# =============================================================================


class AuthMeResponse(BaseModel):
    """Enhanced auth/me response with subscription and access data.

    Mirrors backend ``AuthMeSchema``.
    """

    user: User
    account_status: str = "active"
    subscription: Optional[SubscriptionInfo] = None
    access: dict[str, Any] = Field(default_factory=dict)
    exchange_rates: Optional[dict[str, str]] = Field(
        None,
        description=(
            "Exchange rates from the user's base currency to all available "
            "currencies. Only populated when X-Service-Domain header is present. "
            "Format: {'USD': '1.000000', 'EUR': '0.920000', 'BDT': '109.850000'}"
        ),
    )
    currencies: Optional[dict[str, dict[str, Any]]] = Field(
        None,
        description=(
            "Currency metadata (symbol, name, decimal_digits) for all supported "
            "currencies. Only populated when X-Service-Domain header is present. "
            "Sister domains MUST use this instead of hardcoding symbol maps. "
            "Format: {'USD': {'symbol': '$', 'name': 'US Dollar', 'decimal_digits': 2}}"
        ),
    )

    # ----- Helper methods for feature gating -----

    def has_access(self, key: str) -> bool:
        """Check if the user has access to a feature.

        Coerces string values: ``"true"`` → ``True``, ``"false"`` → ``False``.
        Also treats non-zero integers as truthy.
        """
        value = self.access.get(key)
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        if isinstance(value, (int, float)):
            return bool(value)
        return bool(value)

    def get_access(self, key: str, default: Any = None) -> Any:
        """Get the raw value for an access key."""
        return self.access.get(key, default)

    @property
    def access_keys(self) -> list[str]:
        """Return all access keys the user has."""
        return list(self.access.keys())


# =============================================================================
# Generic Responses
# =============================================================================


class MessageResponse(BaseModel):
    """Generic message response from the API.

    Mirrors backend ``MessageResponse``.
    """

    message: str
    success: bool = True
