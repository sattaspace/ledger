"""Shared schemas — pagination, filtering, and common response types.

Used across all domain schema modules and controllers.
"""

from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar, Optional

from ninja import Schema


# =============================================================================
# Pagination
# =============================================================================


class PaginationIn(Schema):
    """Pagination parameters for list endpoints."""

    limit: int = 50
    offset: int = 0


class PaginationOut(Schema):
    """Pagination metadata returned with list responses."""

    total: int
    limit: int
    offset: int
    has_more: bool


# =============================================================================
# Generic Paginated Response
# =============================================================================


T = TypeVar("T")


class PaginatedResponse(Schema, Generic[T]):
    """Generic paginated list response.

    Usage in controllers:
        @route.get("", response=PaginatedResponse[InstitutionOut])
        def list_institutions(self, request, ...):
            ...
            return {"items": [...], "pagination": {...}}
    """

    items: list[T]
    pagination: PaginationOut


# =============================================================================
# Common Responses
# =============================================================================


class MessageOut(Schema):
    """Simple message response for delete/restore/activate/deactivate."""

    detail: str


class ErrorResponse(Schema):
    """Standard error response."""

    detail: str


class ValidationErrorOut(Schema):
    """Validation error with field-level details."""

    detail: str
    errors: Optional[dict[str, list[str]]] = None


# =============================================================================
# Bulk Operation Responses
# =============================================================================


class BulkDeleteOut(Schema):
    """Response for bulk soft-delete operations."""

    deleted_count: int
    detail: str


class BulkRestoreOut(Schema):
    """Response for bulk restore operations."""

    restored_count: int
    detail: str


# =============================================================================
# Shared Field Mixins (as schemas for reuse in filter endpoints)
# =============================================================================


class DateRangeFilter(Schema):
    """Common date range filter mixin for list endpoints."""

    date_from: Optional[str] = None
    date_to: Optional[str] = None


class AmountRangeFilter(Schema):
    """Common amount range filter for list endpoints."""

    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None


class CurrencyFilter(Schema):
    """Filter by currency code."""

    currency: Optional[str] = None


# =============================================================================
# Soft-Delete / Activation Action Schemas
# =============================================================================


class SoftDeleteAction(Schema):
    """Schema for soft-delete and restore endpoints — no body needed,
    but this schema exists for OpenAPI documentation clarity."""

    pass


# =============================================================================
# TestNote schemas (migrated from old schemas.py)
# =============================================================================


class TestNoteCreate(Schema):
    title: str
    content: str = ""


class TestNoteUpdate(Schema):
    title: Optional[str] = None
    content: Optional[str] = None


class TestNoteOut(Schema):
    id: int
    user_id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
