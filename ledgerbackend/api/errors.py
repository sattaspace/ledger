"""Custom API error classes for the Ledger domain.

These errors are registered as exception handlers in api/views.py.
"""

from ninja.errors import HttpError


class TooManyRequestsError(HttpError):
    """Raised when a rate limit is exceeded (HTTP 429)."""

    def __init__(self, detail: str = "Rate limit exceeded. Please try again later."):
        super().__init__(status_code=429, message=detail)
