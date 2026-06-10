"""
DEALERCORE v3.0 — Sales Schemas (Pydantic)
--------------------------------------------
Uses ninja.ModelSchema where possible.
All schemas use camelCase alias for frontend compatibility.
SaleRecord uses custom schema due to embedded payments + computed fields.
"""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional, List

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema, ModelSchema

from sales.models import SaleRecord, CreditPayment, SaleReturn

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


# ─── Model-based Output Schemas ─────────────────────────────

class CreditPaymentOut(ModelSchema):
    """Embedded payment record — auto-generated from CreditPayment model."""

    model_config = _CAMEL_CONFIG

    class Meta:
        model = CreditPayment
        fields = ["id", "amount", "date", "received_by"]


class SaleReturnOut(Schema):
    model_config = _CAMEL_CONFIG
    id: str
    sale_id: str
    product_name: str
    quantity: int
    return_amount: Decimal
    reason: str
    processed_by: str
    date: datetime


# ─── SaleRecord — custom schema (embedded payments + returns) ────────

class SaleRecordOut(Schema):
    """Full sale record with embedded payments and returns list.
    Uses snake_case fields internally; serialized as camelCase via alias."""

    model_config = _CAMEL_CONFIG

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
    original_dsr_id: Optional[str] = None
    original_dsr_name: str = ""
    selling_price: Decimal
    total_amount: Decimal
    return_total_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    balance_due: Decimal = Decimal("0")
    payment_type: Literal["Cash", "Credit"]
    amount_paid: Decimal
    collection_status: Literal["Fully Paid", "Pending", "Partial", "Written Off", "Voided"]
    due_date: Optional[date] = None
    date: datetime
    payments: List[CreditPaymentOut] = []
    is_closed_with_due: bool = False
    is_voided: bool = False
    returns: List[SaleReturnOut] = []


# ─── Custom Input Schemas ───────────────────────────────────

class CreateSaleIn(Schema):
    """Create a single sale."""

    model_config = _CAMEL_CONFIG

    product_id: str
    quantity: int
    customer_name: str
    customer_phone: str = ""
    is_vehicle: Optional[bool] = None
    vehicle_number: Optional[str] = None
    dsr_id: Optional[str] = None
    payment_type: Literal["Cash", "Credit"]
    amount_paid: Optional[Decimal] = None
    due_date: Optional[date] = None


class BulkSaleRowIn(Schema):
    """One row inside a bulk sale request."""

    model_config = _CAMEL_CONFIG

    product_id: str
    quantity: int
    customer_name: str
    customer_phone: str = ""
    payment_type: Literal["Cash", "Credit"]
    amount_paid: Decimal = Decimal("0")
    due_date: Optional[date] = None


class BulkSaleIn(Schema):
    """Bulk sale request — vehicle_number and dsr_id apply to all rows."""

    model_config = _CAMEL_CONFIG

    vehicle_number: str = ""
    dsr_id: Optional[str] = None
    rows: List[BulkSaleRowIn]


class CollectPaymentIn(Schema):
    """Collect a payment against a credit sale."""

    model_config = _CAMEL_CONFIG

    amount: Decimal
    received_by: str


class CreateReturnIn(Schema):
    """Process a product return from a sale."""

    model_config = _CAMEL_CONFIG

    quantity: int
    reason: str = "Customer Return"
    processed_by: str


class EditSaleIn(Schema):
    """Edit sale — non-financial fields + DSR reassignment for collection.
    Financial fields (product, quantity, selling_price, total_amount, amount_paid)
    cannot be changed after creation. To correct financial data, void the sale
    and create a new one.

    DSR reassignment: changing dsr_id reassigns the CURRENT collector.
    The original_dsr (who made the sale) is preserved and never changes.
    This ensures proper attribution: who sold vs who is collecting."""

    model_config = _CAMEL_CONFIG

    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    due_date: Optional[date] = None
    vehicle_number: Optional[str] = None
    dsr_id: Optional[str] = None  # Reassigns current collector (NOT original seller)
