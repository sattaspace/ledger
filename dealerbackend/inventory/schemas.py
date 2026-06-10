"""
DEALERCORE v3.0 — Inventory Schemas (Pydantic)
------------------------------------------------
Uses ninja.ModelSchema for auto-generated output schemas.
All schemas use camelCase alias for frontend compatibility
(via pydantic alias_generator). Field names stay snake_case
to match Django model attributes.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema, ModelSchema

from inventory.models import Product, RestockRecord, Brand, Category

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


# ─── Brand Schemas ──────────────────────────────────────────

class BrandOut(Schema):
    model_config = _CAMEL_CONFIG
    id: str
    name: str


class CreateBrandIn(Schema):
    model_config = _CAMEL_CONFIG
    name: str


# ─── Category Schemas ───────────────────────────────────────

class CategoryOut(Schema):
    model_config = _CAMEL_CONFIG
    id: str
    name: str


class CreateCategoryIn(Schema):
    model_config = _CAMEL_CONFIG
    name: str


# ─── Model-based Output Schema ─────────────────────────────

class ProductOut(ModelSchema):
    """Response schema — auto-generated from Product model.
    Excludes: created_at, updated_at (not needed by frontend)."""

    model_config = _CAMEL_CONFIG

    class Meta:
        model = Product
        fields = [
            "id", "name", "sku", "brand", "category",
            "stock", "min_stock_alert", "unit_price",
            "selling_price", "location",
        ]


class RestockRecordOut(Schema):
    """Restock record response — manual Schema because model FK field
    is named `product` but API contract expects `product_id`."""

    model_config = _CAMEL_CONFIG

    id: str
    product_id: str
    product_name: str
    quantity: int
    supplier_name: str
    cost_price: Decimal
    total_cost: Decimal
    date: datetime
    received_by: str


# ─── Custom Input Schemas (frontend field naming) ──────────

class AddProductIn(Schema):
    """Create product payload. Backend sets id and stock=0."""

    model_config = _CAMEL_CONFIG

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

    model_config = _CAMEL_CONFIG

    name: Optional[str] = None
    sku: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    min_stock_alert: Optional[int] = None
    unit_price: Optional[Decimal] = None
    selling_price: Optional[Decimal] = None
    location: Optional[str] = None


class RestockIn(Schema):
    """Restock a product — increases stock and creates a RestockRecord."""

    model_config = _CAMEL_CONFIG

    product_id: str
    quantity: int
    supplier_name: str
    cost_price: Decimal
    received_by: str


class RestockOut(Schema):
    """Restock response — message + updated product."""

    model_config = _CAMEL_CONFIG

    message: str
    product: ProductOut
