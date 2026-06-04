"""
DEALERCORE v3.0 — Inventory Schemas (Pydantic)
------------------------------------------------
Request/Response schemas for Inventory and Restock endpoints.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


# ─── Product Schemas ────────────────────────────────────

class ProductOut(Schema):
    """Response schema — full product representation."""

    id: str
    name: str
    sku: str
    brand: str
    category: str
    stock: int
    min_stock_alert: int
    unit_price: Decimal
    selling_price: Decimal
    location: str

    # Allow config for ORM mode
    class Config:
        from_attributes = True


class AddProductIn(Schema):
    """Create product payload. Backend sets id and stock=0."""

    name: str
    sku: str
    brand: str
    category: str
    min_stock_alert: int = 5
    unit_price: Decimal
    selling_price: Decimal
    location: str = "Warehouse"


class EditProductIn(Schema):
    """Partial update payload — all fields optional (PATCH semantics)."""

    name: Optional[str] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    min_stock_alert: Optional[int] = None
    unit_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    location: Optional[str] = None


# ─── Restock Schemas ───────────────────────────────────

class RestockIn(Schema):
    """Restock a product — increases stock and creates a RestockRecord."""

    product_id: str
    quantity: int
    supplier_name: str
    cost_price: Decimal
    received_by: str


class RestockOut(Schema):
    """Restock response — message + updated product."""

    message: str
    product: ProductOut


class RestockRecordOut(Schema):
    """Individual restock record for reference."""

    id: str
    product_id: str
    product_name: str
    quantity: int
    supplier_name: str
    cost_price: Decimal
    total_cost: Decimal
    date: datetime
    received_by: str

    class Config:
        from_attributes = True
