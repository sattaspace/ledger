"""Billing models for Sattabase — central subscription management.

Models chain:
    ServiceDomain (represents a connected service, e.g. finance.sattabase.tld)
        └── Product (group of plans and access control)
              └── Plan (multiple tiers per product)
                    └── AccessEntry (key-value feature gates per plan)
                          └── Subscription (one per user per product)
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from common.models import TimeStampedModel


# =============================================================================
# Choice Constants
# =============================================================================


class BillingCycle(models.TextChoices):
    """Billing cycle frequency for plans."""

    MONTHLY = "monthly", _("Monthly")
    YEARLY = "yearly", _("Yearly")
    LIFETIME = "lifetime", _("Lifetime")


class SubscriptionStatus(models.TextChoices):
    """Subscription lifecycle states."""

    ACTIVE = "active", _("Active")
    PAST_DUE = "past_due", _("Past Due")
    CANCELED = "canceled", _("Canceled")
    TRIALING = "trialing", _("Trialing")
    PAUSED = "paused", _("Paused")
    EXPIRED = "expired", _("Expired")


class AccessValueType(models.TextChoices):
    """Type casting for access entry values."""

    STRING = "string", _("String")
    BOOLEAN = "boolean", _("Boolean")
    INTEGER = "integer", _("Integer")


# =============================================================================
# ServiceDomain
# =============================================================================


class ServiceDomain(TimeStampedModel):
    """Represents a connected service domain (e.g., finance.sattabase.tld).

    Each service domain is a separate application that authenticates against
    Sattabase and receives domain-specific subscription access. One service
    domain maps to one product. A product can also have additional domains
    (e.g., a custom domain like app.myfinance.com alongside the subdomain).

    When a service calls auth/me with the X-Service-Domain header, Sattabase
    looks up the ServiceDomain by this field, then finds the associated product,
    then returns the user's subscription and access map.
    """

    id = models.BigAutoField(primary_key=True)
    domain = models.CharField(
        _("Domain"),
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_(
            "Service domain, e.g. 'finance.sattabase.tld'. "
            "This is matched against the X-Service-Domain header."
        ),
    )
    product = models.ForeignKey(
        "billing.Product",
        on_delete=models.CASCADE,
        related_name="service_domains",
        db_index=True,
        verbose_name=_("Product"),
        help_text=_("The product this domain serves subscriptions for"),
    )
    is_primary = models.BooleanField(
        _("Primary Domain"),
        default=False,
        db_index=True,
        help_text=_(
            "The primary domain for the product. Used in product detail "
            "responses and admin displays."
        ),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        db_index=True,
        help_text=_("Whether this domain is accepting requests"),
    )

    class Meta:
        db_table = "billing_service_domain"
        verbose_name = _("Service Domain")
        verbose_name_plural = _("Service Domains")
        ordering = ["-is_primary", "domain"]

    def __str__(self) -> str:
        return self.domain


class Product(TimeStampedModel):
    """Represents a product managed by Sattabase.

    A product is a logical grouping of subscription plans and their access
    entries. Service domains (e.g., finance.sattabase.tld) are linked to
    a product via the ServiceDomain model. This allows one product to have
    multiple domains (e.g., subdomain + custom domain).

    All subscription plans and access control for a product's domains are
    managed under this product.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(
        _("Product Name"),
        max_length=100,
        unique=True,
        help_text=_("Display name, e.g. 'Satta Finance'"),
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("URL-safe identifier, e.g. 'finance'"),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
        help_text=_("Product description shown to users"),
    )
    icon = models.ImageField(
        _("Icon"),
        upload_to="products/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("Product icon or logo"),
    )
    home_url = models.URLField(
        _("Home URL"),
        blank=True,
        default="",
        help_text=_("Landing page URL for this service"),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        db_index=True,
        help_text=_("Whether this product is accepting new signups"),
    )
    stripe_product_id = models.CharField(
        _("Stripe Product ID"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Auto-created when the first paid plan checkout is initiated"),
    )

    class Meta:
        db_table = "billing_product"
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def get_primary_domain(self):
        """Return the primary domain for this product."""
        return self.service_domains.filter(is_primary=True, is_active=True).first()

    def get_free_plan(self):
        """Return the free plan (price_cents=0) for this product."""
        return self.plans.filter(price_cents=0, is_active=True).first()

    def get_plans(self):
        """Return active plans ordered by price ascending."""
        return self.plans.filter(is_active=True).order_by("price_cents", "sort_order")


# =============================================================================
# Plan
# =============================================================================


class Plan(TimeStampedModel):
    """Represents a subscription tier within a product.

    Each product has multiple plans (Free, Standard, Pro, etc.).
    Access entries define what each plan grants.
    """

    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="plans",
        db_index=True,
        verbose_name=_("Product"),
    )
    name = models.CharField(
        _("Plan Name"),
        max_length=50,
        help_text=_("Plan name, e.g. 'Free', 'Standard'"),
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=50,
        help_text=_("URL-safe identifier, e.g. 'standard'"),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
        help_text=_("Plan description shown to users"),
    )
    price_cents = models.PositiveIntegerField(
        _("Price (cents)"),
        default=0,
        help_text=_("Price in cents (0 = free plan). 900 = $9.00"),
    )
    currency = models.CharField(
        _("Currency"),
        max_length=3,
        default="USD",
        help_text=_("ISO 4217 currency code"),
    )
    billing_cycle = models.CharField(
        _("Billing Cycle"),
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
        db_index=True,
        help_text=_("How often the user is billed"),
    )
    trial_days = models.PositiveIntegerField(
        _("Trial Days"),
        default=0,
        help_text=_("Free trial duration in days (0 = no trial)"),
    )
    features = models.JSONField(
        _("Public Features"),
        default=dict,
        blank=True,
        help_text=_(
            "Public feature list for display "
            '(e.g. {"reports": "Advanced", "storage": "10GB"})'
        ),
    )
    stripe_price_id = models.CharField(
        _("Stripe Price ID"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Stripe Price ID (null for free plans)"),
    )
    sort_order = models.PositiveIntegerField(
        _("Sort Order"),
        default=0,
        help_text=_("Display order (lower = first)"),
    )
    is_active = models.BooleanField(
        _("Active"),
        default=True,
        db_index=True,
        help_text=_("Whether this plan is available for new subscriptions"),
    )
    is_featured = models.BooleanField(
        _("Featured"),
        default=False,
        help_text=_("Highlight this plan in comparison UI"),
    )

    class Meta:
        db_table = "billing_plan"
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")
        ordering = ["product", "sort_order", "price_cents"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "slug"],
                name="unique_plan_slug_per_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.product.name} — {self.name}"

    @property
    def display_price(self) -> str:
        """Human-readable price string, e.g. '$9.00/mo'."""
        amount = self.price_cents / 100
        if self.price_cents == 0:
            return str(_("Free"))

        cycle_labels = {
            BillingCycle.MONTHLY: "/mo",
            BillingCycle.YEARLY: "/yr",
            BillingCycle.LIFETIME: "",
        }
        cycle = cycle_labels.get(self.billing_cycle, "")
        return f"${amount:.2f}{cycle}"

    @property
    def is_free(self) -> bool:
        """Whether this is a free plan."""
        return self.price_cents == 0


# =============================================================================
# AccessEntry
# =============================================================================


class AccessEntry(models.Model):
    """Key-value pair defining what a plan grants.

    This is the core mechanism for feature gating. Each plan has many
    access entries. The `key` is the feature identifier (e.g. "reports"),
    and the `value` is the access level ("true", "5", "1000").

    Example entries for a Standard finance plan:
        key: "dashboard",        value: "true"
        key: "reports",          value: "true"
        key: "max_bank_accounts", value: "5"
        key: "priority_support",  value: "false"
    """

    id = models.BigAutoField(primary_key=True)
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name="access_entries",
        db_index=True,
        verbose_name=_("Plan"),
    )
    key = models.CharField(
        _("Access Key"),
        max_length=100,
        help_text=_("Feature identifier, e.g. 'reports', 'max_accounts'"),
    )
    value = models.CharField(
        _("Access Value"),
        max_length=255,
        help_text=_("Access value, e.g. 'true', '5', '1000'"),
    )
    value_type = models.CharField(
        _("Value Type"),
        max_length=10,
        choices=AccessValueType.choices,
        default=AccessValueType.STRING,
        help_text=_("Determines how the value is cast (string, boolean, integer)"),
    )
    description = models.TextField(
        _("Description"),
        blank=True,
        default="",
        help_text=_("Human-readable description of this access entry"),
    )

    class Meta:
        db_table = "billing_access_entry"
        verbose_name = _("Access Entry")
        verbose_name_plural = _("Access Entries")
        ordering = ["plan", "key"]
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "key"],
                name="unique_access_key_per_plan",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.plan} → {self.key}: {self.value}"

    @property
    def typed_value(self):
        """Return the value cast to its declared type."""
        if self.value_type == AccessValueType.BOOLEAN:
            return self.value.lower() in ("true", "1", "yes")
        if self.value_type == AccessValueType.INTEGER:
            try:
                return int(self.value)
            except (ValueError, TypeError):
                return self.value
        return self.value

    def as_dict(self) -> dict:
        """Return as a dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.typed_value,
            "description": self.description,
        }


# =============================================================================
# Subscription
# =============================================================================


class Subscription(TimeStampedModel):
    """Join between a user and a plan for a specific product.

    One subscription per user per product. When a user subscribes to a
    product's plan, this record tracks the current plan, status, and
    billing period.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        db_index=True,
        verbose_name=_("User"),
    )
    plan = models.ForeignKey(
        Plan,
        on_delete=models.PROTECT,
        db_index=True,
        verbose_name=_("Plan"),
        help_text=_("PROTECT prevents deleting plans with active subscribers"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        db_index=True,
        verbose_name=_("Product"),
        help_text=_("Denormalized from plan.product for query speed"),
    )
    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE,
        db_index=True,
    )
    stripe_subscription_id = models.CharField(
        _("Stripe Subscription ID"),
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text=_("Stripe Subscription ID for webhook correlation"),
    )
    stripe_customer_id = models.CharField(
        _("Stripe Customer ID"),
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Stripe Customer ID for portal access"),
    )
    current_period_start = models.DateTimeField(
        _("Period Start"),
        null=True,
        blank=True,
        help_text=_("Start of the current billing period"),
    )
    current_period_end = models.DateTimeField(
        _("Period End"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("End of the current billing period"),
    )
    trial_start = models.DateTimeField(
        _("Trial Start"),
        null=True,
        blank=True,
        help_text=_("Start of the trial period"),
    )
    trial_end = models.DateTimeField(
        _("Trial End"),
        null=True,
        blank=True,
        help_text=_("End of the trial period"),
    )
    canceled_at = models.DateTimeField(
        _("Canceled At"),
        null=True,
        blank=True,
        help_text=_("When the user requested cancellation"),
    )
    expires_at = models.DateTimeField(
        _("Expires At"),
        null=True,
        blank=True,
        help_text=_("Hard expiration for lifetime plans"),
    )
    has_used_trial = models.BooleanField(
        _("Has Used Trial"),
        default=False,
        help_text=_(
            "Set to True once the user has consumed a trial for this "
            "product. Prevents trial abuse via repeated plan cycling."
        ),
    )

    class Meta:
        db_table = "billing_subscription"
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="unique_subscription_per_user_product",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} → {self.plan} ({self.status})"

    def is_effectively_active(self) -> bool:
        """Check if subscription grants access.

        Returns True if status is active/trialing and period hasn't ended.
        Past_due and canceled subscriptions remain active until period_end.
        """
        if self.status in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.CANCELED,
        ):
            if self.current_period_end and self.current_period_end:
                from django.utils import timezone

                return self.current_period_end > timezone.now()
            return True
        return False

    def get_access_map(self) -> dict:
        """Return {key: typed_value} dict from plan's access entries.

        Eagerly loads access entries to avoid N+1 queries.
        """
        entries = self.plan.access_entries.all()
        return {entry.key: entry.typed_value for entry in entries}

    def cancel_at_period_end(self):
        """Mark subscription as canceled but keep active until period end."""
        from django.utils import timezone

        self.status = SubscriptionStatus.CANCELED
        self.canceled_at = timezone.now()
        self.save(update_fields=["status", "canceled_at", "updated_at"])

    def reactivate(self):
        """Reactivate a previously canceled subscription."""
        self.status = SubscriptionStatus.ACTIVE
        self.canceled_at = None
        self.save(update_fields=["status", "canceled_at", "updated_at"])

    def change_plan(self, new_plan):
        """Switch to a different plan within the same product."""
        self.plan = new_plan
        # If the new plan has a trial and current status is trialing, keep it
        if self.status != SubscriptionStatus.TRIALING:
            self.status = SubscriptionStatus.ACTIVE
        self.save(update_fields=["plan", "status", "updated_at"])


# =============================================================================
# WebhookEventLog
# =============================================================================


class WebhookEventLog(models.Model):
    """Audit log for incoming Stripe webhook events.

    Every webhook received from Stripe is recorded here before processing.
    This enables idempotent handling (skip duplicate events), debugging
    of failed webhooks, and reconciliation tasks. The ``event_id`` field
    is unique — duplicate deliveries of the same event are rejected.

    Cleaned up periodically by the ``cleanup_stale_webhook_events``
    Celery task (Phase 5).
    """

    id = models.BigAutoField(primary_key=True)
    event_id = models.CharField(
        _("Stripe Event ID"),
        max_length=255,
        unique=True,
        db_index=True,
        help_text=_("Stripe event ID, e.g. evt_1Pxxx..."),
    )
    event_type = models.CharField(
        _("Event Type"),
        max_length=100,
        db_index=True,
        help_text=_("Stripe event type, e.g. checkout.session.completed"),
    )
    processed = models.BooleanField(
        _("Processed"),
        default=False,
        db_index=True,
        help_text=_("Whether this event has been successfully processed"),
    )
    error_message = models.TextField(
        _("Error Message"),
        blank=True,
        default="",
        help_text=_("Error message if processing failed"),
    )
    payload = models.JSONField(
        _("Payload"),
        default=dict,
        help_text=_("Full Stripe event JSON payload"),
    )

    created_at = models.DateTimeField(
        _("Created At"),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        db_table = "billing_webhook_event_log"
        verbose_name = _("Webhook Event Log")
        verbose_name_plural = _("Webhook Event Logs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_type} ({self.event_id})"
