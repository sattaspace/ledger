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
from dsr.invitation_api import DsrInvitationController as LegacyDsrInvitationController
from dsr.auth_api import DsrAuthController, DsrInvitationController, DsrAssignmentController
from dsr.dealer_dsr_api import DealerDsrController
from supplier.api import SupplierController
from dealer.api import DealerController
from reports.api import ReportsController
from common.auth_controller import AuthController
from common.sso_controller import SSOController
from common.access_controller import AccessController

api.register_controllers(
    # Core Modules
    InventoryController,
    SalesController,
    DSRController,
    SupplierController,
    DealerController,
    ReportsController,
    
    # Authentication
    AuthController,  # Dealer authentication (via SattaBase)
    DsrAuthController,  # DSR authentication (direct login)
    
    # DSR Invitation & Assignment System
    DsrInvitationController,  # DSR-side invitation management (accept/reject)
    DsrAssignmentController,  # DSR-side assignment management (leave dealer)
    DealerDsrController,  # Dealer-side DSR management (invite/remove)
    
    # Legacy (for backward compatibility)
    LegacyDsrInvitationController,  # Old invitation endpoints
    
    # SSO & Access
    SSOController,  # SSO endpoints
    AccessController,  # Access control endpoints
)
