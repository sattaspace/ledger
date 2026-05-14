"""Schemas for SavingsGoal model — Target-based savings tracker."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# SavingsGoal
# =============================================================================


class SavingsGoalCreate(Schema):
    """Create a new savings goal.

    Example: 'Emergency Fund' with target $10,000, deadline in 12 months.
    current_amount tracks how much has been saved so far.
    """

    name: str
    target_amount: Decimal
    current_amount: Decimal = Decimal("0")
    currency: str = "USD"
    deadline: Optional[date] = None
    account_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class SavingsGoalUpdate(Schema):
    """Update an existing savings goal. All fields optional."""

    name: Optional[str] = None
    target_amount: Optional[Decimal] = None
    current_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    deadline: Optional[date] = None
    account_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class SavingsGoalOut(Schema):
    """Full savings goal output with computed progress properties."""

    id: int
    user_id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: Optional[date]
    account_id: Optional[int]
    icon: str
    color: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    progress_percent: float
    remaining: Decimal
    is_completed: bool
    days_remaining: Optional[int]


class SavingsGoalListOut(Schema):
    """Lightweight savings goal output for list/dashboard views."""

    id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    currency: str
    deadline: Optional[date]
    progress_percent: float
    is_completed: bool
    days_remaining: Optional[int]
    icon: str
    color: str


class SavingsGoalFilter(PaginationIn):
    """Filter parameters for savings goal list endpoint."""

    is_completed: Optional[bool] = None
    currency: Optional[str] = None
    account_id: Optional[int] = None


class SavingsContribution(Schema):
    """Add a contribution to a savings goal.

    Creates a transaction and updates the goal's current_amount.
    """

    amount: Decimal
    account_id: int
    date: Optional[date] = None
    notes: Optional[str] = None


class SavingsContributionOut(Schema):
    """Response from savings contribution."""

    goal_id: int
    old_amount: Decimal
    new_amount: Decimal
    transaction_id: Optional[int]
    detail: str
