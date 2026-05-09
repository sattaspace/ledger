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
    title="Sattabase API",
    version="1.0.0",
    description=(),
    urls_namespace="sattaledger",
    openapi_extra={
        "info": {
            "contact": {
                "name": "Sattaledger Support",
                "email": "ledger@sattaspace.com",
            },
            "license": {"name": "Private"},
        },
        "servers": [
            {"url": "http://localhost:8087", "description": "Local Development"}
        ],
    },
)

api.auto_discover_controllers()