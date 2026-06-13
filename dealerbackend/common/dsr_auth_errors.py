"""
DEALERCORE v3.0 — DSR Authentication Error Handling
----------------------------------------------------
Centralized error handling for DSR authentication.

Provides consistent error responses with:
- Clear user-facing messages
- Machine-readable error codes
- Appropriate HTTP status codes

Usage:
    from common.dsr_auth_errors import DsrAuthError, dsr_error_response

    # Raise error with automatic response
    raise DsrAuthError("User not found", "user_not_found", 404)

    # Or return error response directly
    return dsr_error_response("Invalid password", "invalid_password", 401)
"""

from django.http import JsonResponse
from typing import Tuple, Dict, Any


class DsrAuthError(Exception):
    """
    DSR Authentication Error with structured response.

    Attributes:
        message: User-facing error message
        code: Machine-readable error code for frontend handling
        status_code: HTTP status code

    Common Error Codes:
        - invalid_credentials: Wrong phone/email or password
        - user_not_found: No user with this phone/email
        - account_deactivated: User account is disabled
        - profile_not_found: DSR profile missing
        - no_dealer_assignment: DSR not assigned to any dealer
        - phone_exists: Phone number already registered
        - email_exists: Email already registered
        - invalid_token: JWT token invalid or expired
        - auth_required: Authentication header missing
        - validation_error: Request data validation failed
        - invitation_expired: Invitation token expired
        - invitation_invalid: Invalid invitation token
        - password_mismatch: Current password incorrect
    """

    # Standard error codes
    INVALID_CREDENTIALS = "invalid_credentials"
    USER_NOT_FOUND = "user_not_found"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    PROFILE_NOT_FOUND = "profile_not_found"
    NO_DEALER_ASSIGNMENT = "no_dealer_assignment"
    PHONE_EXISTS = "phone_exists"
    EMAIL_EXISTS = "email_exists"
    INVALID_TOKEN = "invalid_token"
    AUTH_REQUIRED = "auth_required"
    VALIDATION_ERROR = "validation_error"
    INVITATION_EXPIRED = "invitation_expired"
    INVITATION_INVALID = "invitation_invalid"
    PASSWORD_MISMATCH = "password_mismatch"
    TOKEN_EXPIRED = "token_expired"
    REFRESH_REQUIRED = "refresh_required"

    def __init__(self, message: str, code: str = "auth_error", status_code: int = 401):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

    def to_response(self) -> JsonResponse:
        """Convert error to JsonResponse."""
        return JsonResponse(
            {"detail": self.message, "code": self.code},
            status=self.status_code
        )


def dsr_error_response(message: str, code: str = "auth_error", status_code: int = 401) -> Tuple[int, Dict[str, str]]:
    """
    Create a standard error response tuple for Django Ninja.

    Usage in ninja-extra controller:
        @http_post("/login")
        async def login(self, data: LoginInput):
            if not user:
                return dsr_error_response(
                    "Invalid phone or password",
                    DsrAuthError.INVALID_CREDENTIALS,
                    401
                )
            # ... success case

    Returns:
        Tuple of (status_code, {"detail": message, "code": code})
    """
    return status_code, {"detail": message, "code": code}


def dsr_success_response(message: str, **extra_data: Any) -> Dict[str, Any]:
    """
    Create a standard success response.

    Usage:
        return dsr_success_response("Login successful", user=user_data, token=token)
    """
    result = {"message": message}
    result.update(extra_data)
    return result


# ─── Predefined Error Responses ────────────────────────────────────────────────
# These are commonly used error responses that can be imported and used directly

def error_invalid_credentials() -> Tuple[int, Dict[str, str]]:
    """Invalid phone/email or password."""
    return dsr_error_response(
        "Invalid phone/email or password",
        DsrAuthError.INVALID_CREDENTIALS,
        401
    )


def error_user_not_found() -> Tuple[int, Dict[str, str]]:
    """User not found with this phone/email."""
    return dsr_error_response(
        "No account found with this phone/email",
        DsrAuthError.USER_NOT_FOUND,
        404
    )


def error_account_deactivated() -> Tuple[int, Dict[str, str]]:
    """Account is deactivated."""
    return dsr_error_response(
        "Your account has been deactivated. Please contact support.",
        DsrAuthError.ACCOUNT_DEACTIVATED,
        403
    )


def error_profile_not_found() -> Tuple[int, Dict[str, str]]:
    """DSR profile not found."""
    return dsr_error_response(
        "DSR profile not found. Please complete your registration.",
        DsrAuthError.PROFILE_NOT_FOUND,
        404
    )


def error_no_dealer_assignment() -> Tuple[int, Dict[str, str]]:
    """DSR not assigned to any dealer."""
    return dsr_error_response(
        "You are not assigned to any dealer. Please wait for a dealer invitation.",
        DsrAuthError.NO_DEALER_ASSIGNMENT,
        403
    )


def error_phone_exists() -> Tuple[int, Dict[str, str]]:
    """Phone number already registered."""
    return dsr_error_response(
        "An account with this phone number already exists. Please login instead.",
        DsrAuthError.PHONE_EXISTS,
        409
    )


def error_email_exists() -> Tuple[int, Dict[str, str]]:
    """Email already registered."""
    return dsr_error_response(
        "An account with this email already exists. Please login instead.",
        DsrAuthError.EMAIL_EXISTS,
        409
    )


def error_auth_required() -> Tuple[int, Dict[str, str]]:
    """Authentication required."""
    return dsr_error_response(
        "Authentication required. Please login to continue.",
        DsrAuthError.AUTH_REQUIRED,
        401
    )


def error_invalid_token() -> Tuple[int, Dict[str, str]]:
    """Invalid or expired token."""
    return dsr_error_response(
        "Your session has expired. Please login again.",
        DsrAuthError.INVALID_TOKEN,
        401
    )


def error_invitation_expired() -> Tuple[int, Dict[str, str]]:
    """Invitation token expired."""
    return dsr_error_response(
        "This invitation has expired. Please request a new invitation from your dealer.",
        DsrAuthError.INVITATION_EXPIRED,
        410
    )


def error_invitation_invalid() -> Tuple[int, Dict[str, str]]:
    """Invalid invitation token."""
    return dsr_error_response(
        "Invalid invitation link. Please check with your dealer.",
        DsrAuthError.INVITATION_INVALID,
        400
    )


def error_password_mismatch() -> Tuple[int, Dict[str, str]]:
    """Current password is incorrect."""
    return dsr_error_response(
        "Current password is incorrect. Please try again.",
        DsrAuthError.PASSWORD_MISMATCH,
        400
    )
