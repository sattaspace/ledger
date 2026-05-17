"""Schemas for core models — Institution, Account, Transaction, TransactionSplit.

These are the foundational models of the Ledger. Every other domain
(categories, bills, debt, etc.) links back to these.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn, PaginatedResponse


# =============================================================================
# Institution
# =============================================================================


class InstitutionCreate(Schema):
    """Create a new financial institution.

    name must be unique per user.
    """

    name: str
    institution_type: str = "BANK"
    website: Optional[str] = None
    customer_service_phone: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


class InstitutionUpdate(Schema):
    """Update an existing institution. All fields optional — only provided fields are updated."""

    name: Optional[str] = None
    institution_type: Optional[str] = None
    website: Optional[str] = None
    customer_service_phone: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None


class InstitutionOut(Schema):
    """Full institution output including computed fields."""

    id: int
    user_id: int
    name: str
    institution_type: str
    website: str
    customer_service_phone: str
    icon: str
    color: str
    notes: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class InstitutionListOut(Schema):
    """Lightweight institution output for list/dropdown views."""

    id: int
    name: str
    institution_type: str
    icon: str
    color: str


class InstitutionFilter(PaginationIn):
    """Filter parameters for institution list endpoint."""

    institution_type: Optional[str] = None
    search: Optional[str] = None


# =============================================================================
# Account
# =============================================================================


class AccountCreate(Schema):
    """Create a new account.

    institution_id links to an existing Institution.
    currency is ISO 4217 code (3 letters), defaults to USD.
    """

    name: str
    institution_id: int
    account_type: str = "ASSET"
    currency: str = "USD"
    current_balance: Decimal = Decimal("0")
    credit_limit: Optional[Decimal] = None
    interest_rate: Decimal = Decimal("0")
    statement_closing_day: Optional[int] = None
    due_day: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    sort_order: int = 0


class AccountUpdate(Schema):
    """Update an existing account. All fields optional."""

    name: Optional[str] = None
    institution_id: Optional[int] = None
    account_type: Optional[str] = None
    currency: Optional[str] = None
    current_balance: Optional[Decimal] = None
    credit_limit: Optional[Decimal] = None
    interest_rate: Optional[Decimal] = None
    statement_closing_day: Optional[int] = None
    due_day: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    notes: Optional[str] = None
    sort_order: Optional[int] = None


class AccountOut(Schema):
    """Full account output with computed properties."""

    id: int
    user_id: int
    name: str
    institution_id: int
    account_type: str
    currency: str
    current_balance: Decimal
    credit_limit: Optional[Decimal]
    interest_rate: Decimal
    statement_closing_day: Optional[int]
    due_day: Optional[int]
    icon: str
    color: str
    notes: str
    sort_order: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    # ── Computed properties ──
    available_credit: Optional[Decimal] = None
    currency_symbol: str = ""


class AccountListOut(Schema):
    """Lightweight account output for list/dropdown views."""

    id: int
    name: str
    institution_id: int
    account_type: str
    currency: str
    current_balance: Decimal
    icon: str
    color: str
    is_active: bool


class AccountFilter(PaginationIn):
    """Filter parameters for account list endpoint."""

    account_type: Optional[str] = None
    institution_id: Optional[int] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None
    search: Optional[str] = None


class BalanceRecalculateOut(Schema):
    """Response from balance recalculation endpoint."""

    account_id: int
    old_balance: Decimal
    new_balance: Decimal
    detail: str


# =============================================================================
# Transaction
# =============================================================================


class TransactionCreate(Schema):
    """Create a new transaction.

    amount_original must be positive — direction is indicated by transaction_type.
    If amount_base is not provided, it is auto-calculated using exchange rates.
    """

    date: date
    account_id: int
    card_id: Optional[int] = None
    transaction_type: str = "EXPENSE"
    amount_original: Decimal
    currency_original: str = "USD"
    amount_base: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    category_id: Optional[int] = None
    status: str = "CLEARED"
    payee: Optional[str] = None
    description: Optional[str] = None
    reference_number: Optional[str] = None
    is_recurring: bool = False
    bill_id: Optional[int] = None


class TransactionUpdate(Schema):
    """Update an existing transaction. All fields optional."""

    date: Optional[date] = None
    account_id: Optional[int] = None
    card_id: Optional[int] = None
    transaction_type: Optional[str] = None
    amount_original: Optional[Decimal] = None
    currency_original: Optional[str] = None
    amount_base: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    category_id: Optional[int] = None
    status: Optional[str] = None
    payee: Optional[str] = None
    description: Optional[str] = None
    reference_number: Optional[str] = None
    is_recurring: Optional[bool] = None
    bill_id: Optional[int] = None


class TransactionOut(Schema):
    """Full transaction output."""

    id: int
    user_id: int
    date: date
    account_id: int
    card_id: Optional[int]
    transaction_type: str
    amount_original: Decimal
    currency_original: str
    amount_base: Decimal
    exchange_rate: Decimal
    category_id: Optional[int]
    status: str
    payee: str
    description: str
    reference_number: str
    transfer_pair_id: Optional[int]
    is_recurring: bool
    bill_id: Optional[int]
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class TransactionListOut(Schema):
    """Lightweight transaction output for list views."""

    id: int
    date: date
    account_id: int
    transaction_type: str
    amount_original: Decimal
    currency_original: str
    amount_base: Decimal
    status: str
    payee: str
    category_id: Optional[int]
    is_recurring: bool


class TransactionFilter(PaginationIn):
    """Filter parameters for transaction list endpoint.

    tag_id filters transactions that have the specified tag attached
    via the TransactionTag through table.
    """

    account_id: Optional[int] = None
    category_id: Optional[int] = None
    transaction_type: Optional[str] = None
    status: Optional[str] = None
    card_id: Optional[int] = None
    currency_original: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    search: Optional[str] = None
    is_recurring: Optional[bool] = None
    tag_id: Optional[int] = None


class TransferCreate(Schema):
    """Create a transfer between two accounts.

    Creates two linked Transaction records (outflow + inflow) with
    a transfer_pair OneToOneField linking them.
    """

    date: date
    from_account_id: int
    to_account_id: int
    amount: Decimal
    currency: str = "USD"
    description: Optional[str] = None
    status: str = "CLEARED"


class TransferOut(Schema):
    """Response from transfer creation — both transaction IDs."""

    outflow_transaction_id: int
    inflow_transaction_id: int
    detail: str


# =============================================================================
# TransactionSplit
# =============================================================================


class TransactionSplitCreate(Schema):
    """Create a split for a transaction.

    Amount must not exceed the remaining unsplit amount of the transaction.
    """

    transaction_id: int
    category_id: Optional[int] = None
    amount: Decimal
    notes: Optional[str] = None


class TransactionSplitUpdate(Schema):
    """Update an existing split. All fields optional."""

    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None


class TransactionSplitOut(Schema):
    """Full transaction split output."""

    id: int
    user_id: int
    transaction_id: int
    category_id: Optional[int]
    amount: Decimal
    notes: str
    created_at: datetime
    updated_at: datetime
