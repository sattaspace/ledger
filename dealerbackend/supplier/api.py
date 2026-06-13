"""
DEALERCORE v3.0 — Supplier API Controller
--------------------------------------------
Class-based controller using django-ninja-extra.

MULTI-TENANCY:
  All endpoints are scoped to the dealer context extracted from JWT.
  - Dealers see only their own suppliers
  - DSRs/Collectors see suppliers from their assigned dealer (via X-Dealer-Context header)

Endpoints:
  GET    /api/suppliers         → list all suppliers (dealer-scoped)
  GET    /api/suppliers/{id}    → get a single supplier
  POST   /api/suppliers         → create a new supplier
  PATCH  /api/suppliers/{id}    → update a supplier
  DELETE /api/suppliers/{id}    → delete a supplier
"""

from django.db.models import Max

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from dealercore.async_db import async_aggregate, async_exists
from common.dealer_context import get_dealer_context
from dealer.models import DealerConfig
from supplier.models import Supplier
from supplier.schemas import SupplierOut, CreateSupplierIn, UpdateSupplierIn


@api_controller("/suppliers", tags=["Supplier"])
class SupplierController:
    # Maximum records per page to prevent memory exhaustion
    MAX_PAGE_LIMIT = 1000

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Common pagination validation to prevent memory exhaustion."""
        if limit > self.MAX_PAGE_LIMIT:
            raise HttpError(400, f"Limit cannot exceed {self.MAX_PAGE_LIMIT}. Use pagination with offset.")
        if limit < 1:
            raise HttpError(400, "Limit must be at least 1.")
        if offset < 0:
            raise HttpError(400, "Offset cannot be negative.")

    @route.get("", response=list[SupplierOut], summary="List all suppliers")
    async def list_suppliers(self, request, limit: int = 100, offset: int = 0):
        """Return all suppliers for the current dealer context ordered by name.
        
        Query Parameters:
            limit: Max records to return (default: 100, max: 1000)
            offset: Number of records to skip (for pagination)
        
        Dealer Context:
            - Dealers: See only their own suppliers
            - DSRs/Collectors: See suppliers from X-Dealer-Context header
        """
        self._validate_pagination(limit, offset)
        dealer_username = await get_dealer_context(request)
        return [s async for s in Supplier.objects.filter(dealer_id=dealer_username).order_by("name")[offset:offset+limit]]

    @route.get("{supplier_id}", response=SupplierOut, summary="Get a supplier")
    async def get_supplier(self, request, supplier_id: str):
        """Return a single supplier by ID (dealer-scoped)."""
        dealer_username = await get_dealer_context(request)
        try:
            return await Supplier.objects.aget(id=supplier_id, dealer_id=dealer_username)
        except Supplier.DoesNotExist:
            raise HttpError(404, f"Supplier with id '{supplier_id}' not found")

    @route.post("", response=SupplierOut, summary="Create a supplier")
    async def create_supplier(self, request, payload: CreateSupplierIn):
        """Create a new supplier. Auto-generates ID.
        
        The supplier is automatically associated with the current dealer context.
        """
        dealer_username = await get_dealer_context(request)
        dealer = await DealerConfig.objects.aget(username=dealer_username)
        supplier = await Supplier.objects.acreate(
            id=await self._generate_id(dealer_username),
            name=payload.name,
            phone=payload.phone,
            category=payload.category,
            dealer=dealer,
        )
        return supplier

    @route.patch("{supplier_id}", response=SupplierOut, summary="Update a supplier")
    async def update_supplier(self, request, supplier_id: str, payload: UpdateSupplierIn):
        """Partial update on a supplier. Only provided fields are updated (dealer-scoped)."""
        dealer_username = await get_dealer_context(request)
        try:
            supplier = await Supplier.objects.aget(id=supplier_id, dealer_id=dealer_username)
        except Supplier.DoesNotExist:
            raise HttpError(404, f"Supplier with id '{supplier_id}' not found")
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(supplier, field, value)
        await supplier.asave(update_fields=list(update_data.keys()) + ["updated_at"])
        return supplier

    @route.delete("{supplier_id}", summary="Delete a supplier")
    async def delete_supplier(self, request, supplier_id: str):
        """Delete a supplier by ID (dealer-scoped)."""
        dealer_username = await get_dealer_context(request)
        try:
            supplier = await Supplier.objects.aget(id=supplier_id, dealer_id=dealer_username)
        except Supplier.DoesNotExist:
            raise HttpError(404, f"Supplier with id '{supplier_id}' not found")
        await supplier.adelete()
        return {"message": f"Supplier '{supplier.name}' deleted successfully"}

    # ─── Helpers ────────────────────────────────────────

    async def _generate_id(self, dealer_username: str) -> str:
        """Generate a unique Supplier ID (format: sup-{n}).
        
        Uses dealer-scoped queries to ensure ID uniqueness per dealer.
        Uses a retry loop with existence check to handle race conditions
        under concurrent requests.
        """
        prefix = "sup"
        max_retries = 5
        for attempt in range(max_retries):
            result = await async_aggregate(
                Supplier.objects.filter(id__startswith=prefix, dealer_id=dealer_username),
                _max=Max("id"),
            )
            last = result.get("_max")

            num = 1
            if last:
                try:
                    num = int(last.split("-")[-1]) + 1
                except (ValueError, IndexError):
                    num = 1

            # Add attempt offset to reduce collision probability
            num += attempt
            candidate_id = f"{prefix}-{num}"

            # Check if candidate already exists (dealer-scoped)
            exists = await async_exists(
                Supplier.objects.filter(id=candidate_id, dealer_id=dealer_username),
            )
            if not exists:
                return candidate_id

        # Fallback: use a timestamp-based suffix if all retries exhausted
        import time
        return f"{prefix}-{int(time.time() * 1000)}"
