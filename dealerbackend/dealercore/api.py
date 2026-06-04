"""
DEALERCORE v3.0 — Main API Configuration
-------------------------------------------
Central NinjaAPI instance that registers all app routers.

Mount this in dealercore/urls.py via Django's standard URL routing.
"""

from ninja import NinjaAPI

api = NinjaAPI(
    title="DEALERCORE v3.0 API",
    version="3.0.0",
    description=(
        "Async Django Ninja backend for DEALERCORE — "
        "a dealer management system with inventory, sales, DSR, "
        "supplier, dealer configuration, and reports modules."
    ),
)

# ─── Register App Routers ─────────────────────────────

from inventory.api import router as inventory_router
from sales.api import router as sales_router
from dsr.api import router as dsr_router
from supplier.api import router as supplier_router
from dealer.api import router as dealer_router
from reports.api import router as reports_router

api.add_router("/inventory", inventory_router)
api.add_router("/sales", sales_router)
api.add_router("/dsrs", dsr_router)
api.add_router("/suppliers", supplier_router)
api.add_router("/dealers", dealer_router)
api.add_router("/reports", reports_router)
