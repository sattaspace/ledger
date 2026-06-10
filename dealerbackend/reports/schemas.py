"""
DEALERCORE v3.0 — Reports Schemas (Pydantic)
----------------------------------------------
Response schemas for computed report data.
All data here is aggregated — no database models to derive from.
Kept as plain Ninja Schema (no ModelSchema applicable).
All schemas use camelCase alias for frontend compatibility.
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


# ─── Dealer Info ────────────────────────────────────────────

class DealerInfo(Schema):
    """Active dealer details for report headers."""

    model_config = _CAMEL_CONFIG

    business_name: str = ""
    address: str = ""
    phone_number: str = ""
    email: str = ""
    gst_number: str = ""
    google_map_url: str = ""
    communication_number: str = ""
    default_currency: str = "INR"
    default_locale: str = "en-IN"


# ─── Low Stock ──────────────────────────────────────────────

class LowStockItem(Schema):
    """Product below its minimum stock alert threshold."""

    model_config = _CAMEL_CONFIG

    id: str
    name: str
    stock: int
    min_stock_alert: int
    category: str


# ─── DSR Performance ────────────────────────────────────────

class DsrPerformanceRow(Schema):
    """Aggregated performance metrics for a DSR."""

    model_config = _CAMEL_CONFIG

    id: str
    name: str
    role: str
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: Optional[str] = None
    total_sales: Decimal
    collected: Decimal
    pending: Decimal
    count: int


# ─── Product Performance ─────────────────────────────────────

class ProductPerformanceRow(Schema):
    """Aggregated sales performance for a product."""

    model_config = _CAMEL_CONFIG

    name: str
    quantity: int
    total: Decimal


# ─── Summary Response ──────────────────────────────────────

class SummaryOut(Schema):
    """Complete dashboard summary data.

    Revenue excludes written-off sales (bad debt) and voided sales
    to accurately reflect collectible income. Written-off amounts
    are reported separately in `written_off_amount` for financial
    transparency.
    """

    model_config = _CAMEL_CONFIG

    revenue: Decimal  # Total revenue from active sales only (excl. written-off & voided)
    cogs: Decimal
    gross_profit: Decimal  # revenue - cogs
    credit_pending: Decimal
    credit_pending_count: int = 0  # Number of active credit invoices with outstanding balance
    credit_collected: Decimal
    written_off_amount: Decimal = Decimal("0")  # Outstanding balance lost to bad debt
    written_off_outstanding: Decimal = Decimal("0")  # Uncollected portion of written-off
    low_stock_count: int
    low_stock_items: List[LowStockItem]
    dsr_performance: List[DsrPerformanceRow]
    product_performance: List[ProductPerformanceRow]
    total_sales_count: int
    total_products_count: int
    dealer: Optional[DealerInfo] = None


# ─── Customer-wise Due ─────────────────────────────────────

class CustomerDueSale(Schema):
    """Individual sale detail within a customer due report."""

    model_config = _CAMEL_CONFIG

    sale_id: str
    product_name: str
    quantity: int
    total_amount: Decimal
    return_total_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    amount_paid: Decimal
    balance_due: Decimal
    collection_status: str
    due_date: Optional[str] = None
    date: str
    dsr_name: str = ""
    original_dsr_name: str = ""


class CustomerDueRow(Schema):
    """Aggregated due for a single customer."""

    model_config = _CAMEL_CONFIG

    customer_name: str
    customer_phone: str = ""
    total_sales: Decimal
    total_paid: Decimal
    total_returns: Decimal = Decimal("0")
    total_due: Decimal
    sale_count: int
    sales: List[CustomerDueSale]


# ─── Vehicle-wise Due ──────────────────────────────────────

class VehicleDueSale(Schema):
    """Individual sale detail within a vehicle due report."""

    model_config = _CAMEL_CONFIG

    sale_id: str
    customer_name: str
    product_name: str
    quantity: int
    total_amount: Decimal
    return_total_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    amount_paid: Decimal
    balance_due: Decimal
    collection_status: str
    due_date: Optional[str] = None
    date: str
    dsr_name: str = ""
    original_dsr_name: str = ""


class VehicleDueRow(Schema):
    """Aggregated due for a single vehicle."""

    model_config = _CAMEL_CONFIG

    vehicle_number: str
    total_sales: Decimal
    total_paid: Decimal
    total_returns: Decimal = Decimal("0")
    total_due: Decimal
    sale_count: int
    sales: List[VehicleDueSale]


# ─── DSR-wise Due (Collection-wise) ────────────────────────

class DsrDueSale(Schema):
    """Individual sale detail within a DSR due report."""

    model_config = _CAMEL_CONFIG

    sale_id: str
    customer_name: str
    product_name: str
    quantity: int
    total_amount: Decimal
    return_total_amount: Decimal = Decimal("0")
    net_amount: Decimal = Decimal("0")
    amount_paid: Decimal
    balance_due: Decimal
    collection_status: str
    due_date: Optional[str] = None
    date: str
    original_dsr_name: str = ""


class DsrDueRow(Schema):
    """Aggregated due for a single DSR/collector."""

    model_config = _CAMEL_CONFIG

    dsr_id: Optional[str] = None
    dsr_name: str
    role: str = ""
    total_sales: Decimal
    total_paid: Decimal
    total_returns: Decimal = Decimal("0")
    total_due: Decimal
    sale_count: int
    sales: List[DsrDueSale]


# ─── Due Report Response (for print) ───────────────────────

class DueReportOut(Schema):
    """Complete due report with dealer info and breakdowns.
    Used for print-friendly report generation."""

    model_config = _CAMEL_CONFIG

    dealer: Optional[DealerInfo] = None
    generated_at: str = ""
    report_type: str  # "customer", "vehicle", "dsr"
    total_outstanding: Decimal = Decimal("0")
    rows: List  # CustomerDueRow | VehicleDueRow | DsrDueRow


# ─── AI Reconciliation Response ─────────────────────────────

class AiReconciliationOut(Schema):
    """AI-generated reconciliation text (Markdown string)."""

    model_config = _CAMEL_CONFIG

    text: str
