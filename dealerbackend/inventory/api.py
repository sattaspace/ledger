"""
DEALERCORE v3.0 — Inventory API Router
----------------------------------------
Django Ninja async endpoints for inventory management.

Endpoints:
  GET  /api/inventory          → list all products
  POST /api/inventory/add     → add a new product
  POST /api/inventory/restock → restock a product
  POST /api/inventory/{id}/edit → partial update a product
"""

from django.db import transaction
from django.db.models import F
from ninja import Router

from inventory.models import Product, RestockRecord
from inventory.schemas import (
    AddProductIn,
    EditProductIn,
    ProductOut,
    RestockIn,
    RestockOut,
)

router = Router(tags=["Inventory"])


@router.get("", response=list[ProductOut], summary="List all products")
async def list_products(request):
    """Return all products ordered by name."""
    return list(Product.objects.all())


@router.post("add", response=ProductOut, summary="Add a new product")
@transaction.atomic
async def add_product(request, payload: AddProductIn):
    """Create a new product with stock=0. Auto-generates ID."""
    product = await Product.objects.acreate(
        id=await _generate_id("prod"),
        name=payload.name,
        sku=payload.sku,
        brand=payload.brand,
        category=payload.category,
        min_stock_alert=payload.min_stock_alert,
        unit_price=payload.unit_price,
        selling_price=payload.selling_price,
        location=payload.location,
        stock=0,
    )
    return product


@router.post("restock", response=RestockOut, summary="Restock a product")
@transaction.atomic
async def restock_product(request, payload: RestockIn):
    """Restock a product: increase stock, create a RestockRecord."""
    product = await Product.objects.aget(id=payload.product_id)
    product.stock = F("stock") + payload.quantity
    await product.asave()

    total_cost = payload.quantity * payload.cost_price
    restock = await RestockRecord.objects.acreate(
        id=await _generate_id("rstk"),
        product=product,
        product_name=product.name,
        quantity=payload.quantity,
        supplier_name=payload.supplier_name,
        cost_price=payload.cost_price,
        total_cost=total_cost,
        received_by=payload.received_by,
    )

    # Re-fetch to get updated stock value (F() expression resolved)
    await product.arefresh_from_db()

    return RestockOut(
        message=f"Restocked {product.name} with {payload.quantity} units",
        product=product,
    )


@router.post("{product_id}/edit", response=ProductOut, summary="Edit a product")
async def edit_product(request, product_id: str, payload: EditProductIn):
    """Partial update on a product. Only provided fields are updated."""
    product = await Product.objects.aget(id=product_id)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)
    await product.asave()
    return product


# ─── Helpers ────────────────────────────────────────────

async def _generate_id(prefix: str) -> str:
    """Generate a unique string ID with given prefix.
    Format: {prefix}-{incrementing_number}
    e.g., prod-1, prod-2, rstk-1
    """
    # Simple approach: count existing records + 1
    # For production, use a proper sequence or UUID
    from django.db.models import Max

    if prefix == "prod":
        last = await Product.objects.all().aaggregate(
            _max=Max("id")
        )["_max"]
    elif prefix == "rstk":
        last = await RestockRecord.objects.all().aaggregate(
            _max=Max("id")
        )["_max"]
    else:
        last = None

    if last:
        # Extract numeric suffix
        try:
            num = int(last.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1

    return f"{prefix}-{num}"
