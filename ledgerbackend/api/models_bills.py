"""Bill models — Bill and BillPayment.

Recurring or one-time bills/subscriptions with auto-transaction generation.
"""

from datetime import timedelta
from decimal import Decimal

from django.db import models

from common.models import UserOwnedModel

try:
    from dateutil.relativedelta import relativedelta

    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


class Bill(UserOwnedModel):
    """Recurring or one-time bill/subscription.

    Examples: Netflix ($15.99/mo), Rent ($1,500/mo), Annual insurance premium,
    Electricity (variable amount), Spotify, Domain renewal.

    Supports:
        - Fixed amount bills (Netflix) and variable amount bills (Electricity)
        - Multiple recurrence periods (weekly, monthly, yearly)
        - Automatic transaction generation on due date
        - Notification reminders before due date
    """

    RECURRENCE_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("BIWEEKLY", "Every 2 Weeks"),
        ("MONTHLY", "Monthly"),
        ("QUARTERLY", "Quarterly"),
        ("YEARLY", "Yearly"),
        ("ONE_TIME", "One Time"),
    ]

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("PAUSED", "Paused"),
        ("CANCELLED", "Cancelled"),
    ]

    payee = models.CharField(
        max_length=100,
        help_text="Who gets paid (e.g., 'Netflix', 'Landlord')",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Expected amount. 0 for variable bills like electricity.",
    )
    currency = models.CharField(max_length=3, default="USD")
    is_amount_fixed = models.BooleanField(
        default=True,
        help_text="If True, amount is always the same. If False, amount varies each period.",
    )

    # ── Recurrence ────────────────────────────────────────────────────
    recurrence = models.CharField(
        max_length=10, choices=RECURRENCE_CHOICES, default="MONTHLY"
    )
    start_date = models.DateField(help_text="When this bill first started")
    end_date = models.DateField(
        null=True, blank=True, help_text="When this bill ends (blank = ongoing)"
    )
    next_due_date = models.DateField(
        help_text="Next payment due date (auto-updated after each payment)"
    )

    # ── Account & Category ────────────────────────────────────────────
    account = models.ForeignKey(
        "api.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Account used to pay this bill.",
    )
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Default category for auto-generated transactions.",
    )

    # ── Status ────────────────────────────────────────────────────────
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ACTIVE")

    # ── Reminders ─────────────────────────────────────────────────────
    remind_me = models.BooleanField(default=True)
    days_before_reminder = models.IntegerField(
        default=5, help_text="Days before due date to send reminder"
    )

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "bills_bill"
        ordering = ["next_due_date"]

    def __str__(self) -> str:
        return f"{self.payee} — {self.amount} {self.currency} ({self.get_recurrence_display()})"

    def generate_transaction(self):
        """Create a Transaction from this bill (called by Celery on due date).

        Uses lazy import to avoid circular references at module level.
        Returns the created Transaction, or None if the bill is not active.

        Ownership guard: verifies that linked account and category belong to
        the same user as this bill, preventing cross-user data corruption
        in Celery tasks or admin actions.
        """
        if self.status != "ACTIVE":
            return None

        # Ownership guards — prevent cross-user FK corruption
        if self.account and self.account.user_id != self.user_id:
            raise ValueError(
                f"Bill.account (user_id={self.account.user_id}) does not "
                f"belong to Bill.user_id={self.user_id}"
            )
        if self.category and self.category.user_id != self.user_id:
            raise ValueError(
                f"Bill.category (user_id={self.category.user_id}) does not "
                f"belong to Bill.user_id={self.user_id}"
            )

        from api.models_core import Transaction  # noqa: F811

        txn = Transaction.objects.create(
            user_id=self.user_id,
            date=self.next_due_date,
            account=self.account,
            transaction_type="EXPENSE",
            amount_original=self.amount,
            currency_original=self.currency,
            amount_base=self.amount,  # Will be converted in Transaction.save()
            exchange_rate=Decimal("1.0"),
            category=self.category,
            payee=self.payee,
            description=f"Auto-generated from bill: {self.payee}",
            is_recurring=True,
            bill=self,
        )
        self._advance_next_due_date()
        return txn

    def _advance_next_due_date(self):
        """Move next_due_date forward by one period."""
        delta_map = {
            "WEEKLY": relativedelta(weeks=1) if HAS_DATEUTIL else timedelta(weeks=1),
            "BIWEEKLY": relativedelta(weeks=2) if HAS_DATEUTIL else timedelta(weeks=2),
            "MONTHLY": relativedelta(months=1) if HAS_DATEUTIL else timedelta(days=30),
            "QUARTERLY": relativedelta(months=3) if HAS_DATEUTIL else timedelta(days=90),
            "YEARLY": relativedelta(years=1) if HAS_DATEUTIL else timedelta(days=365),
        }
        delta = delta_map.get(self.recurrence)
        if delta:
            self.next_due_date += delta
        # ONE_TIME: don't advance
        self.save(update_fields=["next_due_date", "updated_at"])


class BillPayment(UserOwnedModel):
    """Record of a payment made for a Bill.

    For fixed-amount bills, the amount usually matches the bill amount.
    For variable-amount bills (electricity), the actual amount is recorded here.
    """

    bill = models.ForeignKey(
        Bill, on_delete=models.CASCADE, related_name="payments"
    )
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction = models.ForeignKey(
        "api.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The transaction created by this payment.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "bills_bill_payment"
        ordering = ["-payment_date"]

    def __str__(self) -> str:
        return f"{self.bill.payee} — {self.amount} on {self.payment_date}"
