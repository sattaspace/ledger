from typing import TypeVar, Generic, Optional, List, Any
from datetime import datetime
from ninja import Schema, ModelSchema
from pydantic import Field, ConfigDict


T = TypeVar("T")


# --- Pagination ---


class PaginationInput(Schema):
    """Schema for pagination input parameters."""

    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (max 100)")


class PaginationMeta(Schema):
    """Metadata for paginated responses."""

    total_items: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    current_page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Items per page")
    has_next: bool = Field(..., description="Whether next page exists")
    has_previous: bool = Field(..., description="Whether previous page exists")


class PaginatedResponse(Schema, Generic[T]):
    """Generic paginated response wrapper."""

    meta: PaginationMeta
    results: List[T]


# --- Message Responses ---


class MessageResponse(Schema):
    """Standard success message response."""

    message: str
    success: bool = True


class ErrorResponse(Schema):
    """Standard error response."""

    detail: str
    code: Optional[str] = None
