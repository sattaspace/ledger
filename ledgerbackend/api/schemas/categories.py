"""Schemas for category and tag models — Category, Tag, TransactionTag.

Categories: hierarchical, mutually exclusive (one per transaction).
Tags: flat, additive (many per transaction).
"""

from datetime import datetime
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# Category
# =============================================================================


class CategoryCreate(Schema):
    """Create a new category.

    parent_id creates a subcategory. is_income determines whether the
    category represents income (True) or expense (False).
    """

    name: str
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[int] = None
    is_income: bool = False
    sort_order: int = 0


class CategoryUpdate(Schema):
    """Update an existing category. All fields optional."""

    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_id: Optional[int] = None
    is_income: Optional[bool] = None
    sort_order: Optional[int] = None


class CategoryOut(Schema):
    """Full category output."""

    id: int
    user_id: int
    name: str
    icon: str
    color: str
    parent_id: Optional[int]
    is_income: bool
    sort_order: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class CategoryListOut(Schema):
    """Lightweight category output for list/dropdown views."""

    id: int
    name: str
    parent_id: Optional[int]
    is_income: bool
    icon: str
    color: str


class CategoryTreeOut(Schema):
    """Category in tree structure for hierarchical display.

    subcategories is populated for parent categories only.
    """

    id: int
    name: str
    icon: str
    color: str
    is_income: bool
    sort_order: int
    subcategories: list["CategoryTreeOut"] = []


class CategoryFilter(PaginationIn):
    """Filter parameters for category list endpoint."""

    is_income: Optional[bool] = None
    parent_id: Optional[int] = None
    search: Optional[str] = None


# =============================================================================
# Tag
# =============================================================================


class TagCreate(Schema):
    """Create a new tag. Name must be unique per user."""

    name: str
    color: Optional[str] = None


class TagUpdate(Schema):
    """Update an existing tag. All fields optional."""

    name: Optional[str] = None
    color: Optional[str] = None


class TagOut(Schema):
    """Full tag output."""

    id: int
    user_id: int
    name: str
    color: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class TagListOut(Schema):
    """Lightweight tag output for list/chip views."""

    id: int
    name: str
    color: str


class TagFilter(PaginationIn):
    """Filter parameters for tag list endpoint."""

    search: Optional[str] = None


# =============================================================================
# TransactionTag
# =============================================================================


class TransactionTagCreate(Schema):
    """Link a tag to a transaction."""

    transaction_id: int
    tag_id: int


class TransactionTagOut(Schema):
    """Transaction-Tag link output."""

    id: int
    user_id: int
    transaction_id: int
    tag_id: int
    created_at: datetime
    updated_at: datetime


class TransactionTagBulkCreate(Schema):
    """Bulk-attach tags to a single transaction.

    Replaces all existing tags on the transaction with the provided tag IDs.
    """

    transaction_id: int
    tag_ids: list[int]


class TransactionTagBulkOut(Schema):
    """Response from bulk tag attachment."""

    transaction_id: int
    tag_ids: list[int]
    detail: str
