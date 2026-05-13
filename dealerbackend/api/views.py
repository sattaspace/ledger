"""API configuration for the Sattabase project.

This module creates the NinjaExtraAPI instance, registers exception
handlers for all custom exceptions from ``common.exceptions``, and
auto-discovers all ``@api_controller`` decorated classes.
"""

import logging

from ninja_extra import NinjaExtraAPI
from ninja.errors import ValidationError as NinjaValidationError

logger = logging.getLogger(__name__)

api = NinjaExtraAPI(
    title="Satta Ledger API",
    version="1.0.0",
    description="Satta Ledger backend — powered by Sattabase SDK for auth & billing.",
    urls_namespace="sattaledger",
    openapi_extra={
        "info": {
            "contact": {
                "name": "Satta Ledger Support",
                "email": "ledger@sattaspace.com",
            },
            "license": {"name": "Private"},
        },
        "servers": [
            {"url": "http://localhost:8087", "description": "Local Development"}
        ],
    },
)

# Import controllers so auto_discover picks them up
from api.controllers.test_note_controller import TestNoteController  # noqa: E402

api.auto_discover_controllers()