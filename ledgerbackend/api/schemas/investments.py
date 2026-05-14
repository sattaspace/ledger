"""Schemas for Investment models — InvestmentAccount and Holding.

InvestmentAccount extends Account for investment-specific tracking.
Holding tracks individual positions (stocks, crypto, bonds, etc.).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# InvestmentAccount
# =============================================================================


class InvestmentAccountCreate(Schema):
    """Create an investment profile for an existing Account.

    The Account must have account_type=INVESTMENT.
    portfolio_value and cost_basis_total are auto-calculated from holdings.
    """

    account_id: int
    portfolio_value: Decimal = Decimal("0")
    cost_basis_total: Decimal = Decimal("0")
    last_synced_at: Optional[datetime] = None


class InvestmentAccountUpdate(Schema):
    """Update an investment account. All fields optional."""

    portfolio_value: Optional[Decimal] = None
    cost_basis_total: Optional[Decimal] = None
    last_synced_at: Optional[datetime] = None


class InvestmentAccountOut(Schema):
    """Full investment account output with computed gain/loss."""

    id: int
    user_id: int
    account_id: int
    portfolio_value: Decimal
    cost_basis_total: Decimal
    last_synced_at: Optional[datetime]
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    unrealized_gain_loss: Decimal
    unrealized_gain_loss_percent: float


class InvestmentAccountListOut(Schema):
    """Lightweight investment account output for list views."""

    id: int
    account_id: int
    portfolio_value: Decimal
    cost_basis_total: Decimal
    unrealized_gain_loss: Decimal
    unrealized_gain_loss_percent: float


# =============================================================================
# Holding
# =============================================================================


class HoldingCreate(Schema):
    """Create a new investment position.

    symbol is the ticker (AAPL, BTC, VTI).
    cost_basis is the TOTAL amount paid for the position (not per-share).
    """

    investment_account_id: int
    symbol: str
    asset_name: str
    asset_type: str
    quantity: Decimal
    cost_basis: Decimal
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    currency: str = "USD"
    purchase_date: Optional[date] = None
    last_price_update: Optional[datetime] = None


class HoldingUpdate(Schema):
    """Update an existing holding. All fields optional."""

    symbol: Optional[str] = None
    asset_name: Optional[str] = None
    asset_type: Optional[str] = None
    quantity: Optional[Decimal] = None
    cost_basis: Optional[Decimal] = None
    current_price: Optional[Decimal] = None
    current_value: Optional[Decimal] = None
    currency: Optional[str] = None
    purchase_date: Optional[date] = None
    last_price_update: Optional[datetime] = None


class HoldingOut(Schema):
    """Full holding output with computed properties."""

    id: int
    user_id: int
    investment_account_id: int
    symbol: str
    asset_name: str
    asset_type: str
    quantity: Decimal
    cost_basis: Decimal
    current_price: Optional[Decimal]
    current_value: Optional[Decimal]
    currency: str
    purchase_date: Optional[date]
    last_price_update: Optional[datetime]
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    unrealized_gain_loss: Optional[Decimal]
    average_purchase_price: Optional[Decimal]


class HoldingListOut(Schema):
    """Lightweight holding output for list/portfolio views."""

    id: int
    investment_account_id: int
    symbol: str
    asset_name: str
    asset_type: str
    quantity: Decimal
    cost_basis: Decimal
    current_value: Optional[Decimal]
    currency: str
    unrealized_gain_loss: Optional[Decimal]


class HoldingFilter(PaginationIn):
    """Filter parameters for holding list endpoint."""

    investment_account_id: Optional[int] = None
    asset_type: Optional[str] = None
    currency: Optional[str] = None
    search: Optional[str] = None
