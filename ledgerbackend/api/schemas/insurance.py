"""Schemas for InsurancePolicy model — Policy tracking for all insurance types."""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema

from api.schemas.common import PaginationIn


# =============================================================================
# InsurancePolicy
# =============================================================================


class InsurancePolicyCreate(Schema):
    """Create a new insurance policy.

    Tracks premiums, renewal dates, and coverage details for all types
    of insurance (health, auto, home, life, travel, business, etc.).
    """

    policy_name: str
    insurance_type: str = "OTHER"
    provider: str
    institution_id: Optional[int] = None
    policy_number: Optional[str] = None
    premium_amount: Decimal
    currency: str = "USD"
    premium_frequency: str = "MONTHLY"
    renewal_date: date
    coverage_amount: Optional[Decimal] = None
    coverage_details: Optional[str] = None
    deductible: Optional[Decimal] = None
    remind_renewal: bool = True
    days_before_renewal_reminder: int = 30


class InsurancePolicyUpdate(Schema):
    """Update an existing insurance policy. All fields optional."""

    policy_name: Optional[str] = None
    insurance_type: Optional[str] = None
    provider: Optional[str] = None
    institution_id: Optional[int] = None
    policy_number: Optional[str] = None
    premium_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    premium_frequency: Optional[str] = None
    renewal_date: Optional[date] = None
    coverage_amount: Optional[Decimal] = None
    coverage_details: Optional[str] = None
    deductible: Optional[Decimal] = None
    remind_renewal: Optional[bool] = None
    days_before_renewal_reminder: Optional[int] = None


class InsurancePolicyOut(Schema):
    """Full insurance policy output."""

    id: int
    user_id: int
    policy_name: str
    insurance_type: str
    provider: str
    institution_id: Optional[int]
    policy_number: str
    premium_amount: Decimal
    currency: str
    premium_frequency: str
    renewal_date: date
    coverage_amount: Optional[Decimal]
    coverage_details: str
    deductible: Optional[Decimal]
    remind_renewal: bool
    days_before_renewal_reminder: int
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


class InsurancePolicyListOut(Schema):
    """Lightweight insurance policy output for list views."""

    id: int
    policy_name: str
    insurance_type: str
    provider: str
    premium_amount: Decimal
    currency: str
    premium_frequency: str
    renewal_date: date


class InsurancePolicyFilter(PaginationIn):
    """Filter parameters for insurance policy list endpoint."""

    insurance_type: Optional[str] = None
    provider: Optional[str] = None
    premium_frequency: Optional[str] = None
    renewal_within_days: Optional[int] = None
    search: Optional[str] = None
