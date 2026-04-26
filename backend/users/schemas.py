"""Pydantic schemas for the users app."""

import re
from typing import Optional
from ninja import Schema, ModelSchema
from pydantic import Field, field_validator, model_validator

from .models import User


# =============================================================================
# Shared Validators
# =============================================================================


def _validate_password_strength(v: str) -> str:
    """Validate password meets minimum strength requirements."""
    if not any(c.isupper() for c in v):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not any(c.islower() for c in v):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not any(c.isdigit() for c in v):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`;\']', v):
        raise ValueError("Password must contain at least one special character.")
    return v


# =============================================================================
# Auth Schemas
# =============================================================================


class RegisterInputSchema(Schema):
    """Schema for user registration request."""

    email: str = Field(..., max_length=255, examples=["user@example.com"])
    password: str = Field(
        ..., min_length=8, max_length=128, examples=["SecurePass123!"]
    )
    first_name: str = Field(..., min_length=1, max_length=150)
    last_name: Optional[str] = Field(default="", max_length=150)

    @field_validator("email")
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)


class LoginInputSchema(Schema):
    """Schema for email/password login request."""

    email: str = Field(..., examples=["user@example.com"])
    password: str = Field(...)


class TokenOutputSchema(Schema):
    """Schema for JWT token pair response."""

    access: str = Field(..., description="Access token (short-lived)")
    refresh: str = Field(..., description="Refresh token (long-lived)")


class TokenRefreshInputSchema(Schema):
    """Schema for token refresh request."""

    refresh: str = Field(...)


class TokenVerifyInputSchema(Schema):
    """Schema for token verify request."""

    token: str = Field(...)


class TokenBlacklistInputSchema(Schema):
    """Schema for token blacklist request."""

    refresh: str = Field(...)


# =============================================================================
# Password Reset Schemas
# =============================================================================


class PasswordResetRequestSchema(Schema):
    """Schema for requesting a password reset."""

    email: str = Field(..., max_length=255, examples=["user@example.com"])

    @field_validator("email")
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class PasswordResetConfirmSchema(Schema):
    """Schema for confirming a password reset with token."""

    token: str = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(...)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @field_validator("token")
    @classmethod
    def token_must_be_uuid(cls, v: str) -> str:
        import uuid

        try:
            uuid.UUID(v, version=4)
        except (ValueError, AttributeError):
            raise ValueError("Invalid token format. Expected UUID4.")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match.")
        return self


# =============================================================================
# Sensitive Action — Re-Authentication Schemas
# =============================================================================


class PasswordConfirmSchema(Schema):
    """Schema for confirming user identity via current password."""

    current_password: str = Field(...)


class ChangeEmailRequestSchema(Schema):
    """Schema for requesting an email change (requires current password)."""

    current_password: str = Field(...)
    new_email: str = Field(..., max_length=255, examples=["newemail@example.com"])

    @field_validator("new_email")
    @classmethod
    def email_must_be_lowercase(cls, v: str) -> str:
        return v.lower().strip()


class ChangeEmailConfirmSchema(Schema):
    """Schema for confirming an email change with token."""

    token: str = Field(..., examples=["a1b2c3d4-e5f6-7890-abcd-ef1234567890"])

    @field_validator("token")
    @classmethod
    def token_must_be_uuid(cls, v: str) -> str:
        import uuid

        try:
            uuid.UUID(v, version=4)
        except (ValueError, AttributeError):
            raise ValueError("Invalid token format. Expected UUID4.")
        return v


class DeleteAccountRequestSchema(Schema):
    """Schema for requesting account deletion (requires current password)."""

    current_password: str = Field(...)


# =============================================================================
# User Profile Schemas
# =============================================================================


class UserOutputSchema(ModelSchema):
    """Schema for user data in API responses."""

    full_name: str
    display_name: str

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

    current_password: str = Field(...)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(...)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match.")
        return self


# =============================================================================
# Message Schemas
# =============================================================================


class MessageSchema(Schema):
    """Standard message response."""

    message: str
    success: bool = True
