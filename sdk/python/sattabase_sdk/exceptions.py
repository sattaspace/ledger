"""Typed exception hierarchy for Sattabase SDK."""

from __future__ import annotations

from typing import Any


class SattabaseError(Exception):
    """Base exception for all Sattabase SDK errors.

    Attributes:
        status: HTTP status code from the Sattabase API (0 for network errors).
        message: Human-readable error message.
        detail: Optional structured error detail from the API response.
    """

    def __init__(
        self,
        message: str = "",
        status: int = 0,
        detail: Any = None,
    ) -> None:
        self.status = status
        self.message = message
        self.detail = detail
        super().__init__(message)


class AuthenticationError(SattabaseError):
    """401 — Invalid, expired, or missing token / API key."""

    def __init__(self, message: str = "Authentication failed", detail: Any = None) -> None:
        super().__init__(message=message, status=401, detail=detail)


class AccountInactiveError(AuthenticationError):
    """401 — User account is deactivated by admin (code: ``account_inactive``).

    The SDK consumer should force-logout the user.
    """

    def __init__(self, message: str = "Account is inactive", detail: Any = None) -> None:
        super().__init__(message=message, detail=detail)


class AccountDeletedError(AuthenticationError):
    """401 — User account has been soft-deleted (code: ``account_deleted``).

    The SDK consumer should force-logout the user and clear local data.
    """

    def __init__(self, message: str = "Account has been deleted", detail: Any = None) -> None:
        super().__init__(message=message, detail=detail)


class ForbiddenError(SattabaseError):
    """403 — Insufficient permissions."""

    def __init__(self, message: str = "Forbidden", detail: Any = None) -> None:
        super().__init__(message=message, status=403, detail=detail)


class AccountNotActiveError(ForbiddenError):
    """403 — Email not verified (code: ``account_not_active``)."""

    def __init__(self, message: str = "Account not active — verify email", detail: Any = None) -> None:
        super().__init__(message=message, detail=detail)


class NotFoundError(SattabaseError):
    """404 — Resource not found."""

    def __init__(self, message: str = "Not found", detail: Any = None) -> None:
        super().__init__(message=message, status=404, detail=detail)


class ConflictError(SattabaseError):
    """409 — State conflict (e.g. duplicate resource)."""

    def __init__(self, message: str = "Conflict", detail: Any = None) -> None:
        super().__init__(message=message, status=409, detail=detail)


class RateLimitError(SattabaseError):
    """429 — Too many requests.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header).
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
        detail: Any = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(message=message, status=429, detail=detail)


class ValidationError(SattabaseError):
    """422 — Invalid request body / parameters."""

    def __init__(self, message: str = "Validation error", detail: Any = None) -> None:
        super().__init__(message=message, status=422, detail=detail)


class BadRequestError(SattabaseError):
    """400 — Malformed or invalid request."""

    def __init__(self, message: str = "Bad request", detail: Any = None) -> None:
        super().__init__(message=message, status=400, detail=detail)


class ApiServerError(SattabaseError):
    """5xx — Sattabase server error or network failure."""

    def __init__(self, message: str = "Sattabase server error", detail: Any = None) -> None:
        super().__init__(message=message, status=500, detail=detail)


# Map HTTP status codes + error codes to SDK exceptions
_ERROR_CODE_MAP: dict[str, type[SattabaseError]] = {
    "account_inactive": AccountInactiveError,
    "account_deleted": AccountDeletedError,
    "account_not_active": AccountNotActiveError,
    "unauthorized": AuthenticationError,
    "forbidden": ForbiddenError,
    "not_found": NotFoundError,
    "conflict": ConflictError,
    "too_many_requests": RateLimitError,
    "bad_request": BadRequestError,
}

_STATUS_MAP: dict[int, type[SattabaseError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: ValidationError,
    429: RateLimitError,
}


def build_error(status: int, body: dict | None, code: str | None = None) -> SattabaseError:
    """Build the appropriate SDK exception from an HTTP response.

    Priority:
    1. Match by ``code`` field (e.g. ``account_deleted``)
    2. Match by HTTP status code
    3. Fallback to ``ApiServerError``
    """
    detail = body or None
    message = "Unknown error"

    if isinstance(body, dict):
        message = body.get("detail") or body.get("message") or str(body)

    # Check error code first (more specific)
    if code:
        exc_cls = _ERROR_CODE_MAP.get(code)
        if exc_cls:
            kwargs: dict = {"message": message, "detail": detail}
            if exc_cls is RateLimitError:
                # Pass retry_after if available in body
                retry_after = body.get("retry_after") if isinstance(body, dict) else None
                kwargs["retry_after"] = retry_after
            return exc_cls(**kwargs)

    # Fall back to status code
    exc_cls = _STATUS_MAP.get(status, ApiServerError)
    kwargs = {"message": message, "detail": detail}
    if exc_cls is RateLimitError:
        retry_after = body.get("retry_after") if isinstance(body, dict) else None
        kwargs["retry_after"] = retry_after
    return exc_cls(**kwargs)
