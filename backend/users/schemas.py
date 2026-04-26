"""Pydantic schemas for the users app.

These schemas define the request/response contracts for all user-related API
endpoints. They enforce validation and provide automatic OpenAPI documentation.
"""

from typing import Optional
from datetime import datetime
import uuid as _uuid
from ninja import Schema, ModelSchema
from pydantic import Field, field_validator, model_validator
from enum import Enum

from .models import User


# =============================================================================
# Auth Schemas
# =============================================================================


class RegisterInputSchema(Schema):
    """Schema for user registration request."""

    email: str = Field(
        ...,
        max_length=255,
        description="User's email address (used as login)",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars, 1 uppercase, 1 digit)",
        examples=["SecurePass123"],
    )
    first_name: str = Field(
        ...,
        min_length=1,
        max_length=150,
        description="User's first name",
    )
    last_name: Optional[str] = Field(
        default="",
        max_length=150,
        description="User's last name",
    )

    @field_validator("email")
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


class LoginInputSchema(Schema):
    """Schema for email/password login request."""

    email: str = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        description="User's password",
    )


class TokenOutputSchema(Schema):
    """Schema for JWT token pair response."""

    access: str = Field(..., description="Access token (short-lived)")
    refresh: str = Field(..., description="Refresh token (long-lived)")


class TokenRefreshInputSchema(Schema):
    """Schema for token refresh request."""

    refresh: str = Field(..., description="Refresh token")


# =============================================================================
# OTP Schemas
# =============================================================================


class OTPOurpose(str, Enum):
    """Valid OTP purposes."""

    REGISTRATION = "registration"
    LOGIN = "login"
    PASSWORD_RESET = "password_reset"
    EMAIL_VERIFICATION = "email_verification"


class OTPRequestInputSchema(Schema):
    """Schema for requesting an OTP code."""

    email: str = Field(
        ...,
        description="Email address to send OTP to",
        examples=["user@example.com"],
    )
    purpose: OTPOurpose = Field(
        ...,
        description="Purpose of the OTP",
    )


class OTPVerifyInputSchema(Schema):
    """Schema for verifying an OTP code."""

    email: str = Field(
        ...,
        description="Email address the OTP was sent to",
        examples=["user@example.com"],
    )
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP code",
        examples=["123456"],
    )
    purpose: OTPOurpose = Field(
        ...,
        description="Purpose of the OTP (must match request purpose)",
    )


class OTPLoginInputSchema(Schema):
    """Schema for OTP-based passwordless login."""

    email: str = Field(
        ...,
        description="Email address",
        examples=["user@example.com"],
    )
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP code",
        examples=["123456"],
    )


# =============================================================================
# User Profile Schemas
# =============================================================================


class UserOutputSchema(ModelSchema):
    """Schema for user data in API responses.

    Uses Ninja's ModelSchema to auto-generate fields from the User model.
    Extra computed properties (full_name, display_name) are declared explicitly
    since they are model @property methods, not database columns.
    """

    # These are model @property methods — declared explicitly
    full_name: str
    display_name: str
    # Note: slug is auto-mapped from the UUIDField by ModelSchema.
    # We redeclare it as UUID to keep the schema correct for OpenAPI.

    class Meta:
        model = User
        fields = [
            "id",
            "slug",
            "email",
            "first_name",
            "last_name",
            "phone",
            "avatar",
            "timezone",
            "currency",
            "language",
            "is_email_verified",
            "is_active",
            "role",
            "oauth_provider",
            "created_at",
        ]


class UserProfileUpdateInputSchema(Schema):
    """Schema for updating user profile fields."""

    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=30)
    timezone: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=3)
    language: Optional[str] = Field(None, max_length=10)


class ChangePasswordInputSchema(Schema):
    """Schema for changing password (authenticated user)."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (min 8 chars, 1 uppercase, 1 digit)",
    )
    confirm_password: str = Field(..., description="Confirm new password")

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match.")
        return self


class ResetPasswordInputSchema(Schema):
    """Schema for resetting password with OTP verification."""

    email: str = Field(..., description="Email address")
    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP code",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password",
    )

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        return v


# =============================================================================
# OAuth Schemas
# =============================================================================


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""

    GOOGLE = "google"
    GITHUB = "github"


class OAuthLoginInputSchema(Schema):
    """Schema for OAuth-based login/signup.

    The flow:
    1. Frontend authenticates with OAuth provider (Google/GitHub)
    2. Frontend sends provider's access_token to this endpoint
    3. Backend validates token with provider, finds/creates user
    4. Backend returns our JWT tokens
    """

    provider: OAuthProvider = Field(
        ...,
        description="OAuth provider name",
    )
    access_token: str = Field(
        ...,
        description="Access token from the OAuth provider",
    )


class OAuthLinkInputSchema(Schema):
    """Schema for linking an OAuth provider to an existing account."""

    provider: OAuthProvider = Field(...)
    access_token: str = Field(...)


# =============================================================================
# Message Schemas
# =============================================================================


class MessageSchema(Schema):
    """Standard message response."""

    message: str
    success: bool = True
