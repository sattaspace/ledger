"""
DEALERCORE v3.0 — Sales Schemas (Pydantic)
--------------------------------------------
Request/Response schemas for Sale and CreditPayment endpoints.
"""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional, List

from ninja import Schema


# ─── CreditPayment Schemas ─────────────────────────────

class CreditPaymentOut(Schema):
    """Embedded payment record inside SaleRecord."""

    id: str
    amount: Decimal
    date: datetime
    received_by: str

    class Config:
        from_attributes = True


# ─── SaleRecord Schemas ────────────────────────────────

class SaleRecordOut(Schema):
    """Full sale record with embedded payments list."""

    id: str
    product_id: str
    product_name: str
    quantity: int
    customer_name: str
    customer_phone: str = ""
    is_vehicle: bool = False
    vehicle_number: str = ""
    dsr_id: Optional[str] = None
    dsr_name: str = ""
    selling_price: Decimal
    total_amount: Decimal
    payment_type: Literal["Cash", "Credit"]
    amount_paid: Decimal
    collection_status: Literal["Fully Paid", "Pending", "Partial"]
    due_date: Optional[date] = None
    date: datetime
    payments: List[CreditPaymentOut] = []
    is_closed_with_due: bool = False

    class Config:
        from_attributes = True


class CreateSaleIn(Schema):
    """Create a single sale."""

    product_id: str
    quantity: int
    customer_name: str
    customer_phone: Optional[str] = None
    is_vehicle: Optional[bool] = None
    vehicle_number: Optional[str] = None
    dsr_id: Optional[str] = None
    payment_type: Literal["Cash", "Credit"]
    amount_paid: Optional[Decimal] = None
    due_date: Optional[str] = None  # YYYY-MM-DD string


class BulkSaleRowIn(Schema):
    """One row inside a bulk sale request."""

    product_id: str
    quantity: int
    customer_name: str
    customer_phone: str = ""
    payment_type: Literal["Cash", "Credit"]
    amount_paid: Decimal = Decimal("0")
    due_date: Optional[str] = None


class BulkSaleIn(Schema):
    """Bulk sale request — vehicle_number and dsr_id apply to all rows."""

    vehicle_number: str = ""
    dsr_id: Optional[str] = None
    rows: List[BulkSaleRowIn]


class CollectPaymentIn(Schema):
    """Collect a payment against a credit sale."""

    amount: Decimal
    received_by: str
