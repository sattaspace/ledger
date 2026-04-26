"""API configuration for the Satta Ledger project."""

import logging

from ninja_extra import NinjaExtraAPI
from ninja.errors import ValidationError as NinjaValidationError
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

api = NinjaExtraAPI(
    title="Satta Ledger API",
    version="1.0.0",
    description=(
        "Satta Ledger API — Personal Accounting & Notifications SaaS.\n\n"
        "## Authentication\n\n"
        "All protected endpoints require a JWT Bearer token.\n\n"
        "## Auth Endpoints (`/api/v1/auth/`)\n\n"
        "- `POST /auth/register`\n"
        "- `POST /auth/login`\n"
        "- `POST /auth/token/refresh`\n"
        "- `POST /auth/token/verify`\n"
        "- `POST /auth/token/blacklist`\n"
        "- `POST /auth/password-reset/request`\n"
        "- `POST /auth/password-reset/confirm`\n"
        "- `POST /auth/email-change/confirm`\n\n"
        "## Sensitive Actions (require current password)\n\n"
        "- `POST /users/me/confirm-identity`\n"
        "- `POST /users/me/change-email`\n"
        "- `POST /users/me/change-password`\n"
        "- `POST /users/me/delete-account`"
    ),
    urls_namespace="sattaledger",
    openapi_extra={
        "info": {
            "contact": {
                "name": "Satta Ledger Support",
                "email": "support@sattaledger.com",
            },
            "license": {"name": "Private"},
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local Development"}
        ],
    },
)


@api.exception_handler(NinjaValidationError)
def validation_exception_handler(request, exc: NinjaValidationError):
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


@api.exception_handler(Exception)
def unhandled_exception_handler(request, exc: Exception):
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
