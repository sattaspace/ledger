"""Schemas for Card model — Debit and credit cards linked to accounts."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# Card
# =============================================================================


class CardCreate(Schema):
    """Create a new card linked to an account.

    last_four must be unique per user+account combination.
    """

    account_id: int
    card_type: str
    card_name: str
    last_four: str
    expiry_date: Optional[date] = None
    annual_fee: Decimal = Decimal("0")
    annual_fee_date: Optional[date] = None
    color: Optional[str] = None
    sort_order: int = 0


class CardUpdate(Schema):
    """Update an existing card. All fields optional."""

    account_id: Optional[int] = None
    card_type: Optional[str] = None
    card_name: Optional[str] = None
    last_four: Optional[str] = None
    expiry_date: Optional[date] = None
    annual_fee: Optional[Decimal] = None
    annual_fee_date: Optional[date] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class CardOut(Schema):
    """Full card output."""

    id: int
    user_id: int
    account_id: int
    card_type: str
    card_name: str
    last_four: str
    expiry_date: Optional[date]
    annual_fee: Decimal
    annual_fee_date: Optional[date]
    color: str
    sort_order: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class CardListOut(Schema):
    """Lightweight card output for list views."""

    id: int
    account_id: int
    card_type: str
    card_name: str
    last_four: str
    color: str


class CardFilter(PaginationIn):
    """Filter parameters for card list endpoint."""

    account_id: Optional[int] = None
    card_type: Optional[str] = None
    search: Optional[str] = None
