"""API configuration for the Satta Ledger project.

This module initializes the Django Ninja Extra API instance and configures:
- API metadata (title, version, description)
- Custom exception handlers for consistent error responses
- Controller auto-discovery from installed apps
- JWT default controller registration (standard token obtain/refresh/verify)
"""

import logging
from typing import Any

from ninja_extra import NinjaExtraAPI
from ninja.errors import ValidationError as NinjaValidationError
from ninja_jwt.controller import NinjaJWTDefaultController
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

# =============================================================================
# API Instance
# =============================================================================

api = NinjaExtraAPI(
    title="Satta Ledger API",
    version="1.0.0",
    description=(
        "Satta Ledger API — Personal Accounting & Notifications SaaS.\n\n"
        "## Authentication\n\n"
        "All protected endpoints require a JWT Bearer token in the `Authorization` header:\n"
        "```\nAuthorization: Bearer <access_token>\n```\n\n"
        "## Auth Flows\n\n"
        "1. **Email + Password**: Register → Verify OTP → Login → Get JWT\n"
        "2. **OTP (Passwordless)**: Request OTP → Login with OTP → Get JWT\n"
        "3. **OAuth (Google/GitHub)**: Frontend auth → Send provider token → Get JWT\n\n"
        "## Standard JWT Endpoints (NinjaJWTDefaultController)\n\n"
        "- `POST /api/v1/token/pair` — Obtain access + refresh tokens\n"
        "- `POST /api/v1/token/refresh` — Refresh access token\n"
        "- `POST /api/v1/token/verify` — Verify access token\n"
        "- `POST /api/v1/token/blacklist` — Blacklist a token\n\n"
        "## Rate Limits\n\n"
        "- OTP requests: 5 per hour per email\n"
        "- OTP attempts: 3 per code\n"
    ),
    urls_namespace="sattaledger",
    openapi_extra={
        "info": {
            "contact": {
                "name": "Satta Ledger Support",
                "email": "support@sattaledger.com",
            },
            "license": {
                "name": "Private",
            },
        },
        "servers": [
            {"url": "http://localhost:8000", "description": "Local Development"},
        ],
    },
)


# =============================================================================
# Custom Exception Handlers
# =============================================================================


@api.exception_handler(NinjaValidationError)
def validation_exception_handler(request, exc: NinjaValidationError):
    """Handle Pydantic/Ninja validation errors with consistent formatting."""
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
    """Catch-all handler for unexpected errors. Logs the error and returns a generic message."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return api.create_response(
        request,
        {
            "detail": "An unexpected error occurred. Please try again.",
            "code": "server_error",
        },
        status=500,
    )


# =============================================================================
# Controller Registration
# =============================================================================

# Register the standard JWT controller for token obtain/refresh/verify/blacklist.
# This provides the canonical /token/ endpoints. Our custom AuthController
# at /auth/ provides additional flows (registration, OTP, OAuth) that layer
# on top of these standard endpoints.
api.register_controllers(NinjaJWTDefaultController)

# Auto-discover controllers from all installed apps.
# Controllers must be in a file named `controllers.py` within an app.
api.auto_discover_controllers()
