"""
DEALERCORE v3.0 — DSR Schemas (Pydantic)
------------------------------------------
All schemas use camelCase alias for frontend compatibility.
Custom schema needed for DSROut because of computed active_sales_count.
"""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


# ─── Extended schema with computed field ─────────────────────

class DSROut(Schema):
    """DSR response with computed active_sales_count annotation."""

    model_config = _CAMEL_CONFIG

    id: str
    name: str
    phone: str
    active_sales_count: int = 0
    role: str = "DSR"
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: str = ""


# ─── Custom Input Schema ────────────────────────────────────

class CreateDSRIn(Schema):
    """Create a new DSR or Order Collector."""

    model_config = _CAMEL_CONFIG

    name: str
    phone: str
    role: Optional[str] = "DSR"
    parent_dsr_id: Optional[str] = None


class UpdateDSRIn(Schema):
    """Partial update on a DSR — all fields optional (PATCH semantics)."""

    model_config = _CAMEL_CONFIG

    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    parent_dsr_id: Optional[str] = None
