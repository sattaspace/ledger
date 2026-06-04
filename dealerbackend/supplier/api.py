"""
DEALERCORE v3.0 — Supplier API Router
----------------------------------------
Django Ninja async endpoints for supplier management.

Endpoints:
  GET  /api/suppliers  → list all suppliers
"""

from ninja import Router

from supplier.models import Supplier
from supplier.schemas import SupplierOut

router = Router(tags=["Supplier"])


@router.get("", response=list[SupplierOut], summary="List all suppliers")
async def list_suppliers(request):
    """Return all suppliers ordered by name."""
    return list(Supplier.objects.all())
