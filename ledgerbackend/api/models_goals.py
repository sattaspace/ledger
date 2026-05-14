"""Savings Goal model — Target-based savings tracker."""

from django.db import models

from common.models import UserOwnedModel


class SavingsGoal(UserOwnedModel):
    """Target-based savings tracker.

    Users can create goals like 'Emergency Fund ($10,000)' or 'Vacation ($3,000)'
    and track progress over time. Contributions are linked to transactions.
    """

    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=15, decimal_places=2)
    current_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")
    deadline = models.DateField(null=True, blank=True)

    # ── Linked account ────────────────────────────────────────────────
    account = models.ForeignKey(
        "api.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Account where this savings is held.",
    )
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True)

    class Meta:
        db_table = "goals_savings_goal"
        ordering = ["deadline"]

    def __str__(self) -> str:
        return f"{self.name} — {self.current_amount}/{self.target_amount} {self.currency}"

    @property
    def progress_percent(self):
        if self.target_amount == 0:
            return 100
        return min(round((self.current_amount / self.target_amount) * 100, 1), 100)

    @property
    def remaining(self):
        from decimal import Decimal

        return max(self.target_amount - self.current_amount, Decimal("0"))

    @property
    def is_completed(self):
        return self.current_amount >= self.target_amount

    @property
    def days_remaining(self):
        if not self.deadline:
            return None
        from django.utils import timezone

        delta = self.deadline - timezone.now().date()
        return max(delta.days, 0)
