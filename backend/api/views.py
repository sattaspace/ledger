"""API configuration for the Sattabase project.

This module creates the NinjaExtraAPI instance, registers exception
handlers for all custom exceptions from ``common.exceptions``, and
auto-discovers all ``@api_controller`` decorated classes.
"""

import logging

from ninja_extra import NinjaExtraAPI
from ninja.errors import ValidationError as NinjaValidationError

from common.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    BadRequestException,
    ConflictException,
    TooManyRequestsException,
    AccountNotActiveException,
)

logger = logging.getLogger(__name__)

api = NinjaExtraAPI(
    title="Sattabase API",
    version="1.0.0",
    description=(
        "Sattabase API — Central Multi-Tenant Subscription Platform.\n\n"
        "## Authentication\n\n"
        "All protected endpoints require a JWT Bearer token in the "
        "``Authorization: Bearer <token>`` header.\n\n"
        "## Auth Endpoints (`/api/v1/auth/`)\n\n"
        "- `POST /auth/register`\n"
        "- `POST /auth/login`\n"
        "- `POST /auth/token/refresh`\n"
        "- `POST /auth/token/verify`\n"
        "- `POST /auth/token/blacklist`\n"
        "- `POST /auth/password-reset/request`\n"
        "- `POST /auth/password-reset/confirm`\n\n"
        "## Billing Endpoints (`/api/v1/billing/`)\n\n"
        "### Public\n"
        "- `GET /billing/products` — List all active products\n"
        "- `GET /billing/products/{slug}` — Product detail with plans & domains\n"
        "- `GET /billing/products/{slug}/plans` — Plans for a product\n\n"
        "### Protected (requires JWT)\n"
        "- `GET /billing/auth/me` — User info + subscription + access map\n"
        "- `GET /billing/subscriptions` — All user subscriptions\n"
        "- `GET /billing/subscriptions/{product_slug}` — Subscription detail\n"
        "- `POST /billing/subscriptions/{product_slug}/cancel`\n"
        "- `POST /billing/subscriptions/{product_slug}/reactivate`\n"
        "- `POST /billing/subscriptions/{product_slug}/change-plan`\n"
        "- `POST /billing/subscriptions/{product_slug}/checkout`\n"
        "- `POST /billing/portal`\n\n"
        "### Webhooks (signature-verified, no JWT)\n"
        "- `POST /billing/webhooks/stripe`"
    ),
    urls_namespace="sattaledger",
    openapi_extra={
        "info": {
            "contact": {
                "name": "Sattabase Support",
                "email": "support@sattabase.com",
            },
            "license": {"name": "Private"},
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local Development"}
        ],
    },
)


# =============================================================================
# Validation Error Handler
# =============================================================================


@api.exception_handler(NinjaValidationError)
def validation_exception_handler(request, exc: NinjaValidationError):
    """Handle Pydantic/Ninja validation errors with field-level details."""
    errors = []
    if hasattr(exc, "errors"):
        for err in exc.errors:
            field = " -> ".join(str(loc) for loc in err.get("loc", []))
            errors.append({"field": field, "message": err.get("msg", "Invalid value")})
    else:
        errors.append({"field": "non_field", "message": str(exc)})
    return api.create_response(
        request,
        {"detail": "Validation error", "errors": errors, "code": "validation_error"},
        status=400,
    )


# =============================================================================
# Custom Exception Handlers
# =============================================================================


def _error_response(request, exc):
    """Build a consistent error response for all custom exceptions.

    All custom exceptions from ``common.exceptions`` extend
    ``ninja_extra.exceptions.APIException`` which provides ``status_code``,
    ``detail`` (an ``ErrorDetail`` string subclass with a ``.code`` attribute),
    and ``default_code``.

    The ``code`` in the response envelope is read from ``exc.detail.code``,
    which comes from each exception's ``default_code`` class attribute.
    """
    return api.create_response(
        request,
        {"detail": str(exc.detail), "code": getattr(exc.detail, "code", "error")},
        status=exc.status_code,
    )


@api.exception_handler(UnauthorizedException)
def unauthorized_handler(request, exc):
    return _error_response(request, exc)


@api.exception_handler(ForbiddenException)
def forbidden_handler(request, exc):
    return _error_response(request, exc)


@api.exception_handler(NotFoundException)
def not_found_handler(request, exc):
    return _error_response(request, exc)


@api.exception_handler(BadRequestException)
def bad_request_handler(request, exc):
    return _error_response(request, exc)


@api.exception_handler(ConflictException)
def conflict_handler(request, exc):
    return _error_response(request, exc)


@api.exception_handler(TooManyRequestsException)
def too_many_requests_handler(request, exc):
    return _error_response(request, exc)


@api.exception_handler(AccountNotActiveException)
def account_not_active_handler(request, exc):
    return _error_response(request, exc)


# =============================================================================
# Catch-All Handler
# =============================================================================


@api.exception_handler(Exception)
def unhandled_exception_handler(request, exc: Exception):
    """Catch-all for truly unexpected errors. Logs full traceback."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return api.create_response(
        request,
        {
            "detail": "An unexpected error occurred. Please try again.",
            "code": "server_error",
        },
        status=500,
    )


api.auto_discover_controllers()
