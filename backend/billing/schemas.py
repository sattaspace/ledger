"""Pydantic schemas for the billing app.

These schemas define the request/response contracts for all billing-related
API endpoints. They enforce validation and provide automatic OpenAPI documentation.
"""

from typing import Optional, Any
from datetime import datetime
from ninja import Schema, ModelSchema
from pydantic import Field

from users.schemas import UserOutputSchema
from .models import ServiceDomain, Product, Plan, AccessEntry, Subscription


# =============================================================================
# ServiceDomain Schemas
# =============================================================================


class ServiceDomainOutputSchema(Schema):
    """Service domain data for public listing and product details.

    Defined as a plain ``Schema`` (not ``ModelSchema``) because
    ``product_id`` is a database column name, not a Django model field.
    ``ModelSchema`` only recognizes the FK field name ``product``, but
    we want to return the integer ID (not the full nested Product object).
    """

    id: int
    domain: str
    product_id: int
    is_primary: bool
    is_active: bool


# =============================================================================
# Access Entry Schemas
# =============================================================================


class AccessEntryOutputSchema(Schema):
    """Single access entry in API responses."""

    key: str = Field(..., description="Feature identifier, e.g. 'reports'")
    value: Any = Field(..., description="Access value (bool, int, or str)")
    description: Optional[str] = Field(None, description="Human-readable description")


# =============================================================================
# Plan Schemas
# =============================================================================


class PlanOutputSchema(ModelSchema):
    """Plan data for public listing and subscription responses."""

    display_price: str
    is_free: bool

    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price_cents",
            "currency",
            "billing_cycle",
            "trial_days",
            "features",
            "sort_order",
            "is_active",
            "is_featured",
        ]


class PlanDetailSchema(PlanOutputSchema):
    """Plan detail with access entries included."""

    access_entries: list[AccessEntryOutputSchema] = Field(
        default_factory=list,
        description="List of access entries defining what this plan grants",
    )


# =============================================================================
# Product Schemas
# =============================================================================


class ProductOutputSchema(ModelSchema):
    """Product data for public listing."""

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "home_url",
            "is_active",
            "created_at",
        ]


class ProductDetailSchema(ProductOutputSchema):
    """Product detail with plans and service domains included."""

    plans: list[PlanOutputSchema] = Field(
        default_factory=list,
        description="Available plans for this product",
    )
    service_domains: list[ServiceDomainOutputSchema] = Field(
        default_factory=list,
        description="Domains linked to this product",
    )


# =============================================================================
# Subscription Schemas
# =============================================================================


class SubscriptionInfoSchema(Schema):
    """Subscription summary returned in auth/me response."""

    plan_name: str = Field(..., description="Name of the current plan")
    plan_slug: str = Field(..., description="Slug of the current plan")
    status: str = Field(..., description="Subscription status")
    current_period_end: Optional[datetime] = Field(
        None, description="End of the current billing period"
    )
    trial_end: Optional[datetime] = Field(None, description="End of the trial period")
    is_active: bool = Field(..., description="Whether subscription grants access")


class SubscriptionOutputSchema(Schema):
    """Full subscription data for management endpoints.

    Defined as a plain ``Schema`` because we need computed fields
    (``plan_name``, ``plan_slug``, ``product_name``, ``product_slug``)
    that don't exist on the model, plus ``user_id`` which is a database
    column name rather than a Django model field.
    """

    id: int
    user_id: int
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    plan_name: str
    plan_slug: str
    product_name: str
    product_slug: str


class SubscriptionDetailSchema(SubscriptionOutputSchema):
    """Subscription detail with plan and access entries."""

    plan: PlanDetailSchema
    access: dict[str, Any] = Field(
        default_factory=dict,
        description="Flat key-value access map from the plan's access entries",
    )


# =============================================================================
# Auth Me Schema (enhanced)
# =============================================================================


class AuthMeSchema(Schema):
    """Enhanced auth/me response with subscription and access data.

    Returned when X-Service-Domain header is present.
    When no domain header is sent, subscription and access are null/empty.
    """

    user: UserOutputSchema = Field(..., description="User profile data")
    subscription: Optional[SubscriptionInfoSchema] = Field(
        None, description="Subscription info for the requesting domain"
    )
    access: dict[str, Any] = Field(
        default_factory=dict,
        description="Flat key-value access map from the plan's access entries",
    )


# =============================================================================
# Checkout & Portal Schemas
# =============================================================================


class CheckoutInputSchema(Schema):
    """Schema for creating a Stripe checkout session."""

    plan_slug: str = Field(
        ...,
        description="Slug of the plan to subscribe to",
        examples=["standard"],
    )
    billing_cycle: Optional[str] = Field(
        None,
        description="Billing cycle override (if plan supports multiple cycles)",
        examples=["monthly", "yearly"],
    )


class CheckoutOutputSchema(Schema):
    """Schema for Stripe checkout session response."""

    checkout_url: str = Field(
        ..., description="Stripe Checkout URL to redirect user to"
    )


class CheckoutConfirmInputSchema(Schema):
    """Schema for confirming a Stripe checkout session."""

    session_id: str = Field(
        ...,
        description="Stripe Checkout Session ID from the success redirect URL",
        examples=["cs_test_xxxxxxxxxxxx"],
    )


class CheckoutConfirmOutputSchema(Schema):
    """Schema for checkout confirmation response."""

    plan_name: str = Field(..., description="Name of the activated plan")
    plan_slug: str = Field(..., description="Slug of the activated plan")
    status: str = Field(..., description="Subscription status (active/trialing)")
    trial_end: Optional[datetime] = Field(
        None, description="Trial end date if applicable"
    )
    current_period_end: Optional[datetime] = Field(
        None, description="End of the current billing period"
    )


class PortalOutputSchema(Schema):
    """Schema for Stripe Customer Portal session response."""

    portal_url: str = Field(..., description="Stripe Customer Portal URL")


class ChangePlanInputSchema(Schema):
    """Schema for changing subscription plan."""

    plan_slug: str = Field(
        ...,
        description="Slug of the new plan to switch to",
        examples=["pro"],
    )
