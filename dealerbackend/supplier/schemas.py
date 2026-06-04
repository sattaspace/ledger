"""
DEALERCORE v3.0 — Supplier Schemas (Pydantic)
----------------------------------------------
Request/Response schemas for Supplier endpoints.
"""

from __future__ import annotations

from ninja import Schema


class SupplierOut(Schema):
    """Supplier response."""

    id: str
    name: str
    phone: str = ""
    category: str = ""

    class Config:
        from_attributes = True
