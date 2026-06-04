"""
DEALERCORE v3.0 — DSR Schemas (Pydantic)
------------------------------------------
Request/Response schemas for DSR (Daily Sales Representative) endpoints.
"""

from __future__ import annotations

from typing import Literal, Optional

from ninja import Schema


class DSROut(Schema):
    """Full DSR response."""

    id: str
    name: str
    phone: str
    active_sales_count: int = 0
    role: Literal["DSR", "Order Collector"] = "DSR"
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: str = ""

    class Config:
        from_attributes = True


class CreateDSRIn(Schema):
    """Create a new DSR or Order Collector."""

    name: str
    phone: str
    role: Optional[Literal["DSR", "Order Collector"]] = "DSR"
    parent_dsr_id: Optional[str] = None
