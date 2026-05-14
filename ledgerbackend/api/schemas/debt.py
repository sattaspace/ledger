"""Schemas for Debt models — DebtFacility and DebtPayment.

DebtFacility consolidates both borrowed and lent money tracking.
DebtPayment records each payment with principal/interest breakdown.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# DebtFacility
# =============================================================================


class DebtFacilityCreate(Schema):
    """Create a new debt facility (loan or lending arrangement).

    debt_nature distinguishes MONEY_BORROWED (you owe) from MONEY_LENT (they owe you).
    remaining_balance starts equal to principal_amount and decreases with payments.
    """

    name: str
    debt_nature: str
    debt_type: str
    entity_name: str
    institution_id: Optional[int] = None
    principal_amount: Decimal
    remaining_balance: Decimal
    currency: str = "USD"
    interest_rate: Decimal = Decimal("0")
    start_date: date
    end_date: Optional[date] = None
    term_months: Optional[int] = None
    monthly_payment: Decimal = Decimal("0")
    payment_day: Optional[int] = None
    account_id: Optional[int] = None
    notes: Optional[str] = None


class DebtFacilityUpdate(Schema):
    """Update an existing debt facility. All fields optional."""

    name: Optional[str] = None
    debt_nature: Optional[str] = None
    debt_type: Optional[str] = None
    entity_name: Optional[str] = None
    institution_id: Optional[int] = None
    principal_amount: Optional[Decimal] = None
    remaining_balance: Optional[Decimal] = None
    currency: Optional[str] = None
    interest_rate: Optional[Decimal] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    term_months: Optional[int] = None
    monthly_payment: Optional[Decimal] = None
    payment_day: Optional[int] = None
    account_id: Optional[int] = None
    notes: Optional[str] = None


class DebtFacilityOut(Schema):
    """Full debt facility output with computed properties."""

    id: int
    user_id: int
    name: str
    debt_nature: str
    debt_type: str
    entity_name: str
    institution_id: Optional[int]
    principal_amount: Decimal
    remaining_balance: Decimal
    currency: str
    interest_rate: Decimal
    start_date: date
    end_date: Optional[date]
    term_months: Optional[int]
    monthly_payment: Decimal
    payment_day: Optional[int]
    account_id: Optional[int]
    notes: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    is_mine: bool
    progress_percent: float


class DebtFacilityListOut(Schema):
    """Lightweight debt facility output for list views."""

    id: int
    name: str
    debt_nature: str
    debt_type: str
    entity_name: str
    principal_amount: Decimal
    remaining_balance: Decimal
    currency: str
    interest_rate: Decimal
    monthly_payment: Decimal
    progress_percent: float


class DebtFacilityFilter(PaginationIn):
    """Filter parameters for debt facility list endpoint."""

    debt_nature: Optional[str] = None
    debt_type: Optional[str] = None
    institution_id: Optional[int] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None


# =============================================================================
# DebtPayment
# =============================================================================


class DebtPaymentCreate(Schema):
    """Record a payment against a debt facility.

    Break down into principal, interest, and extra payment portions.
    The sum of principal_portion + interest_portion + extra_payment
    should equal the total amount.
    """

    debt_id: int
    payment_date: date
    amount: Decimal
    principal_portion: Decimal = Decimal("0")
    interest_portion: Decimal = Decimal("0")
    extra_payment: Decimal = Decimal("0")
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class DebtPaymentUpdate(Schema):
    """Update an existing debt payment. All fields optional."""

    payment_date: Optional[date] = None
    amount: Optional[Decimal] = None
    principal_portion: Optional[Decimal] = None
    interest_portion: Optional[Decimal] = None
    extra_payment: Optional[Decimal] = None
    transaction_id: Optional[int] = None
    notes: Optional[str] = None


class DebtPaymentOut(Schema):
    """Full debt payment output."""

    id: int
    user_id: int
    debt_id: int
    payment_date: date
    amount: Decimal
    principal_portion: Decimal
    interest_portion: Decimal
    extra_payment: Decimal
    transaction_id: Optional[int]
    notes: str
    created_at: datetime
    updated_at: datetime


class DebtPaymentFilter(PaginationIn):
    """Filter parameters for debt payment list endpoint."""

    debt_id: Optional[int] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
