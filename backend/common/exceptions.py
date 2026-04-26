from ninja_extra.exceptions import APIException


class UnauthorizedException(APIException):
    """Raised when authentication is required but not provided."""

    status_code = 401
    default_message = "Authentication credentials were not provided."


class ForbiddenException(APIException):
    """Raised when the user does not have permission to perform the action."""

    status_code = 403
    default_message = "You do not have permission to perform this action."


class NotFoundException(APIException):
    """Raised when a requested resource is not found."""

    status_code = 404
    default_message = "The requested resource was not found."


class BadRequestException(APIException):
    """Raised when the request data is invalid or malformed."""

    status_code = 400
    default_message = "The request could not be understood."


class ConflictException(APIException):
    """Raised when the request conflicts with the current state."""

    status_code = 409
    default_message = "The request conflicts with the current state of the resource."


class TooManyRequestsException(APIException):
    """Raised when rate limit is exceeded."""

    status_code = 429
    default_message = "Too many requests. Please try again later."


class AccountNotActiveException(APIException):
    """Raised when user account is not active."""

    status_code = 403
    default_message = "Your account is not active. Please contact support."
