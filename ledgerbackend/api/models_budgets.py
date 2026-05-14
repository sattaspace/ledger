"""Budget model — Spending limits by category and period."""

from datetime import timedelta
from decimal import Decimal

from django.db import models

from common.models import UserOwnedModel

try:
    from dateutil.relativedelta import relativedelta

    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class Budget(UserOwnedModel):
    """Spending limit for a category over a time period.

    Supports monthly and weekly budgets. The `spent_amount` is computed
    dynamically from transactions for accuracy.
    """

    PERIOD_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
    ]

    category = models.ForeignKey(
        "api.Category",
        on_delete=models.CASCADE,
        related_name="budgets",
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2, help_text="Budget limit")
    currency = models.CharField(max_length=3, default="USD")
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES, default="MONTHLY")
    start_date = models.DateField(help_text="When this budget period starts")

    # ── Rollover ──────────────────────────────────────────────────────
    allow_rollover = models.BooleanField(
        default=False,
        help_text="If True, unspent amount rolls over to next period.",
    )

    class Meta:
        db_table = "budgets_budget"
        ordering = ["-start_date"]
        unique_together = [("user_id", "category", "period", "start_date")]

    def __str__(self) -> str:
        return f"{self.category} — {self.amount} {self.currency} ({self.get_period_display()})"

    # ── Computed properties ───────────────────────────────────────────

    @property
    def spent_amount(self):
        """Calculate total spent in this budget period from transactions."""
        from django.db.models import Sum

        from api.models_core import Transaction

        end_date = self._get_end_date()
        return (
            Transaction.objects.filter(
                user_id=self.user_id,
                category=self.category,
                transaction_type="EXPENSE",
                date__gte=self.start_date,
                date__lte=end_date,
                status="CLEARED",
                is_deleted=False,
            ).aggregate(total=Sum("amount_base"))["total"]
            or Decimal("0")
        )

    @property
    def remaining(self):
        return self.amount - self.spent_amount

    @property
    def percent_used(self):
        if self.amount == 0:
            return 0
        return min(round((self.spent_amount / self.amount) * 100, 1), 100)

    def _get_end_date(self):
        """Calculate the end date of this budget period."""
        if HAS_DATEUTIL:
            delta_map = {
                "WEEKLY": relativedelta(weeks=1),
                "MONTHLY": relativedelta(months=1),
                "YEARLY": relativedelta(years=1),
            }
        else:
            delta_map = {
                "WEEKLY": timedelta(weeks=1),
                "MONTHLY": timedelta(days=30),
                "YEARLY": timedelta(days=365),
            }
        delta = delta_map.get(self.period)
        if delta:
            return self.start_date + delta
        return self.start_date
