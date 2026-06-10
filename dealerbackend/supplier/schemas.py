"""
DEALERCORE v3.0 — Supplier Schemas (Pydantic)
----------------------------------------------
Uses ninja.ModelSchema — fully auto-generated.
All fields are single words, so camelCase alias is a no-op,
but added for consistency across the project.
"""

from typing import Optional

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema, ModelSchema

from supplier.models import Supplier

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


class SupplierOut(ModelSchema):
    """Supplier response — fully auto-generated from Supplier model."""

    model_config = _CAMEL_CONFIG

    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "category"]


class CreateSupplierIn(Schema):
    """Create a new supplier."""

    model_config = _CAMEL_CONFIG

    name: str
    phone: str = ""
    category: str = "General"


class UpdateSupplierIn(Schema):
    """Partial update on a supplier — all fields optional (PATCH semantics)."""

    model_config = _CAMEL_CONFIG

    name: Optional[str] = None
    phone: Optional[str] = None
    category: Optional[str] = None
