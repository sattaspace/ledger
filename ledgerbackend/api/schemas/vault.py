"""Schemas for DocumentVault model — Secure document storage linked to financial items.

Uses Django's ContentType framework for generic relations — a document
can be attached to any model (Account, InsurancePolicy, Transaction, etc.).
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# DocumentVault
# =============================================================================


class DocumentVaultCreate(Schema):
    """Upload a new document to the vault.

    content_type_id + object_id form the generic relation.
    Example: content_type_id=15 (Account), object_id=42 (specific account).

    The file field is handled separately via multipart upload —
    this schema covers the metadata fields.
    """

    title: str
    file_type: Optional[str] = None
    file_size: int = 0
    expiry_date: Optional[date] = None
    remind_before_expiry: bool = False
    days_before_expiry_reminder: int = 30
    content_type_id: int
    object_id: int


class DocumentVaultUpdate(Schema):
    """Update document metadata. All fields optional.

    The file itself cannot be updated — delete and re-upload instead.
    """

    title: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    expiry_date: Optional[date] = None
    remind_before_expiry: Optional[bool] = None
    days_before_expiry_reminder: Optional[int] = None
    content_type_id: Optional[int] = None
    object_id: Optional[int] = None


class DocumentVaultOut(Schema):
    """Full document vault output."""

    id: int
    user_id: int
    title: str
    file: str
    file_type: str
    file_size: int
    expiry_date: Optional[date]
    remind_before_expiry: bool
    days_before_expiry_reminder: int
    content_type_id: int
    object_id: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class DocumentVaultListOut(Schema):
    """Lightweight document output for list views."""

    id: int
    title: str
    file_type: str
    file_size: int
    expiry_date: Optional[date]
    content_type_id: int
    object_id: int


class DocumentVaultFilter(PaginationIn):
    """Filter parameters for document vault list endpoint."""

    content_type_id: Optional[int] = None
    object_id: Optional[int] = None
    file_type: Optional[str] = None
    expiring_within_days: Optional[int] = None
    search: Optional[str] = None
