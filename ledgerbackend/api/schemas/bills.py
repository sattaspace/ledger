"""Schemas for Bill models — Bill and BillPayment.

Recurring or one-time bills/subscriptions with auto-transaction generation.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# Bill
# =============================================================================


class BillCreate(Schema):
    """Create a new bill/subscription.

    next_due_date is auto-updated after each payment.
    For variable-amount bills (electricity), set is_amount_fixed=False and amount=0.
    """

    payee: str
    amount: Decimal
    currency: str = "USD"
    is_amount_fixed: bool = True
    recurrence: str = "MONTHLY"
    start_date: date
    end_date: Optional[date] = None
    next_due_date: date
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    status: str = "ACTIVE"
    remind_me: bool = True
    days_before_reminder: int = 5
    notes: Optional[str] = None


class BillUpdate(Schema):
    """Update an existing bill. All fields optional."""

    payee: Optional[str] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    is_amount_fixed: Optional[bool] = None
    recurrence: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    next_due_date: Optional[date] = None
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    status: Optional[str] = None
    remind_me: Optional[bool] = None
    days_before_reminder: Optional[int] = None
    notes: Optional[str] = None


class BillOut(Schema):
    """Full bill output."""

    id: int
    user_id: int
    payee: str
    amount: Decimal
    currency: str
    is_amount_fixed: bool
    recurrence: str
    start_date: date
    end_date: Optional[date]
    next_due_date: date
    account_id: Optional[int]
    category_id: Optional[int]
    status: str
    remind_me: bool
    days_before_reminder: int
    notes: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class BillListOut(Schema):
    """Lightweight bill output for list views — shows upcoming bills."""

    id: int
    payee: str
    amount: Decimal
    currency: str
    recurrence: str
    next_due_date: date
    status: str
    is_amount_fixed: bool


class BillFilter(PaginationIn):
    """Filter parameters for bill list endpoint."""

    status: Optional[str] = None
    recurrence: Optional[str] = None
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    due_within_days: Optional[int] = None
    search: Optional[str] = None


class BillGenerateTransactionOut(Schema):
    """Response from manual bill transaction generation."""

    transaction_id: int
    bill_id: int
    next_due_date: date
    detail: str


# =============================================================================
# BillPayment
# =============================================================================


class BillPaymentCreate(Schema):
    """Record a payment made for a bill.

    For fixed-amount bills, amount usually matches the bill amount.
    For variable-amount bills, record the actual amount paid.
    """

    bill_id: int
    payment_date: date
    amount: Decimal
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class BillPaymentUpdate(Schema):
    """Update an existing bill payment. All fields optional."""

    payment_date: Optional[date] = None
    amount: Optional[Decimal] = None
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class BillPaymentOut(Schema):
    """Full bill payment output."""

    id: int
    user_id: int
    bill_id: int
    payment_date: date
    amount: Decimal
    transaction_id: Optional[int]
    notes: str
    created_at: datetime
    updated_at: datetime


class BillPaymentFilter(PaginationIn):
    """Filter parameters for bill payment list endpoint."""

    bill_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
