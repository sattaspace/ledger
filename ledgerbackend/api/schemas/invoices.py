"""Schemas for Invoice models — Invoice and InvoiceLineItem.

Freelancer/solopreneur invoicing: create, send, track, and get paid.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# Invoice
# =============================================================================


class InvoiceCreate(Schema):
    """Create a new invoice.

    invoice_number must be unique per user.
    subtotal, tax_amount, and total_amount should be consistent.
    amount_paid tracks partial payments.
    """

    invoice_number: str
    client_name: str
    client_email: Optional[str] = None
    issue_date: date
    due_date: date
    subtotal: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    total_amount: Decimal
    amount_paid: Decimal = Decimal("0")
    currency: str = "USD"
    status: str = "DRAFT"
    transaction_id: Optional[int] = None
    notes: Optional[str] = None
    terms: Optional[str] = None


class InvoiceUpdate(Schema):
    """Update an existing invoice. All fields optional."""

    invoice_number: Optional[str] = None
    client_name: Optional[str] = None
    client_email: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    amount_paid: Optional[Decimal] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    transaction_id: Optional[int] = None
    notes: Optional[str] = None
    terms: Optional[str] = None


class InvoiceOut(Schema):
    """Full invoice output with computed properties."""

    id: int
    user_id: int
    invoice_number: str
    client_name: str
    client_email: str
    issue_date: date
    due_date: date
    paid_date: Optional[date]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    currency: str
    status: str
    transaction_id: Optional[int]
    notes: str
    terms: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    amount_due: Decimal
    is_overdue: bool


class InvoiceListOut(Schema):
    """Lightweight invoice output for list views."""

    id: int
    invoice_number: str
    client_name: str
    issue_date: date
    due_date: date
    total_amount: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    currency: str
    status: str
    is_overdue: bool


class InvoiceFilter(PaginationIn):
    """Filter parameters for invoice list endpoint."""

    status: Optional[str] = None
    client_name: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    is_overdue: Optional[bool] = None
    currency: Optional[str] = None
    search: Optional[str] = None


class InvoiceMarkPaid(Schema):
    """Mark an invoice as paid.

    Optionally link to an existing income transaction.
    If no transaction_id is provided, one can be auto-created.
    """

    paid_date: date
    amount_paid: Optional[Decimal] = None
    transaction_id: Optional[int] = None


# =============================================================================
# InvoiceLineItem
# =============================================================================


class InvoiceLineItemCreate(Schema):
    """Create a line item on an invoice.

    total should equal quantity * unit_price.
    """

    invoice_id: int
    description: str
    quantity: Decimal = Decimal("1")
    unit_price: Decimal
    total: Decimal


class InvoiceLineItemUpdate(Schema):
    """Update an existing line item. All fields optional."""

    description: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    total: Optional[Decimal] = None


class InvoiceLineItemOut(Schema):
    """Full line item output."""

    id: int
    user_id: int
    invoice_id: int
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    created_at: datetime
    updated_at: datetime
