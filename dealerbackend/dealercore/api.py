"""
DEALERCORE v3.0 — Main API Configuration
-------------------------------------------
Central NinjaExtraAPI instance that registers all class-based controllers.

Uses django-ninja-extra for:
  - Class-based API controllers (@api_controller)
  - ModelSchema auto-generation from Django models

Mount this in dealercore/urls.py via Django's standard URL routing.
"""

from ninja_extra import NinjaExtraAPI

api = NinjaExtraAPI(
    title="DEALERCORE v3.0 API",
    version="3.0.0",
    description=(
        "Async Django Ninja Extra backend for DEALERCORE — "
        "a dealer management system with inventory, sales, DSR, "
        "supplier, dealer configuration, and reports modules. "
        "Uses class-based controllers and ModelSchema."
    ),
)

# ─── Register Class-Based Controllers ───────────────
# ninja-extra auto-discovers controllers decorated with @api_controller.
# Alternatively, import and register explicitly:

from inventory.api import InventoryController
from sales.api import SalesController
from dsr.api import DSRController
from dsr.invitation_api import DsrInvitationController
from supplier.api import SupplierController
from dealer.api import DealerController
from reports.api import ReportsController
from common.auth_controller import AuthController
from common.sso_controller import SSOController
from common.access_controller import AccessController

api.register_controllers(
    InventoryController,
    SalesController,
    DSRController,
    SupplierController,
    DealerController,
    ReportsController,
    AuthController,  # Authentication endpoints
    DsrInvitationController,  # DSR invitation endpoints
    SSOController,  # SSO endpoints
    AccessController,  # Access control endpoints
)
