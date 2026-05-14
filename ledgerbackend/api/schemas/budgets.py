"""Schemas for Budget model — Spending limits by category and period."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# Budget
# =============================================================================


class BudgetCreate(Schema):
    """Create a new budget for a category.

    The spent amount is computed dynamically from transactions.
    allow_rollover lets unspent amounts carry over to the next period.
    """

    category_id: int
    amount: Decimal
    currency: str = "USD"
    period: str = "MONTHLY"
    start_date: date
    allow_rollover: bool = False


class BudgetUpdate(Schema):
    """Update an existing budget. All fields optional."""

    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    period: Optional[str] = None
    start_date: Optional[date] = None
    allow_rollover: Optional[bool] = None


class BudgetOut(Schema):
    """Full budget output with computed spending properties."""

    id: int
    user_id: int
    category_id: int
    amount: Decimal
    currency: str
    period: str
    start_date: date
    allow_rollover: bool
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    spent_amount: Decimal
    remaining: Decimal
    percent_used: float


class BudgetListOut(Schema):
    """Lightweight budget output for list/dashboard views."""

    id: int
    category_id: int
    amount: Decimal
    currency: str
    period: str
    spent_amount: Decimal
    remaining: Decimal
    percent_used: float


class BudgetFilter(PaginationIn):
    """Filter parameters for budget list endpoint."""

    category_id: Optional[int] = None
    period: Optional[str] = None
    currency: Optional[str] = None
