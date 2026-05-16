"""Insurance model — Policy tracking for all insurance types."""

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from common.models import UserOwnedModel


class InsurancePolicy(UserOwnedModel):
    """Insurance policy tracker.

    Track premiums, renewal dates, and coverage details for all types
    of insurance (health, auto, home, life, travel, etc.).
    """

    INSURANCE_TYPES = [
        ("HEALTH", "Health"),
        ("AUTO", "Auto"),
        ("HOME", "Home/Renters"),
        ("LIFE", "Life"),
        ("TRAVEL", "Travel"),
        ("BUSINESS", "Business"),
        ("OTHER", "Other"),
    ]

    PREMIUM_FREQUENCIES = [
        ("MONTHLY", "Monthly"),
        ("QUARTERLY", "Quarterly"),
        ("YEARLY", "Yearly"),
    ]

    policy_name = models.CharField(
        max_length=100,
        help_text="E.g., 'Blue Cross Health', 'Geico Auto'",
    )
    insurance_type = models.CharField(
        max_length=10, choices=INSURANCE_TYPES, default="OTHER"
    )
    provider = models.CharField(max_length=100)
    institution = models.ForeignKey(
        "api.Institution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to institution if provider is in your institutions list.",
    )
    policy_number = models.CharField(max_length=100, blank=True)

    # ── Premium ───────────────────────────────────────────────────────
    premium_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    premium_frequency = models.CharField(
        max_length=10,
        choices=PREMIUM_FREQUENCIES,
        default="MONTHLY",
    )
    renewal_date = models.DateField()

    # ── Coverage ──────────────────────────────────────────────────────
    coverage_amount = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total coverage amount.",
    )
    coverage_details = models.TextField(blank=True)
    deductible = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # ── Reminders ─────────────────────────────────────────────────────
    remind_renewal = models.BooleanField(default=True)
    days_before_renewal_reminder = models.IntegerField(default=30)

    # ── Generic relation for DocumentVault ────────────────────────────
    documents = GenericRelation(
        "api.DocumentVault",
        related_query_name="insurance_policy",
    )

    class Meta:
        db_table = "insurance_insurance_policy"
        ordering = ["renewal_date"]

    def __str__(self) -> str:
        return f"{self.policy_name} ({self.get_insurance_type_display()})"
