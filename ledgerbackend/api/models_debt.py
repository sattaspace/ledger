"""Debt models — DebtFacility and DebtPayment.

Consolidated from the original Debt + DebtFacility into a single model with
a `debt_nature` field that distinguishes "money I borrowed" from "money I lent".
"""

from decimal import Decimal

from django.db import models

from common.models import UserOwnedModel


class DebtFacility(UserOwnedModel):
    """A loan, mortgage, or lending arrangement.

    Covers both sides:
        - MONEY_BORROWED: You owe someone (liability) — bank loan, credit card debt, mortgage
        - MONEY_LENT: Someone owes you (asset) — personal loan you gave, mortgage you hold

    Payments against this debt are tracked in DebtPayment records.
    The linked Account tracks the running balance.
    """

    DEBT_NATURES = [
        ("MONEY_BORROWED", "Money Borrowed (I owe)"),
        ("MONEY_LENT", "Money Lent (They owe me)"),
    ]

    DEBT_TYPES = [
        ("MORTGAGE", "Mortgage"),
        ("PERSONAL", "Personal Loan"),
        ("STUDENT", "Student Loan"),
        ("AUTO", "Auto Loan"),
        ("BUSINESS", "Business Loan"),
        ("INFORMAL", "Informal Loan (Friends/Family)"),
    ]

    name = models.CharField(
        max_length=100,
        help_text="E.g., 'Chase Mortgage', 'Loan to John'",
    )
    debt_nature = models.CharField(
        max_length=15,
        choices=DEBT_NATURES,
        help_text="Who owes whom? MONEY_BORROWED = you owe; MONEY_LENT = they owe you",
    )
    debt_type = models.CharField(max_length=15, choices=DEBT_TYPES)

    # ── Counterparty ──────────────────────────────────────────────────
    entity_name = models.CharField(
        max_length=100,
        help_text="Lender name (if borrowed) or borrower name (if lent)",
    )
    institution = models.ForeignKey(
        "api.Institution",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Link to institution if it's a bank loan (optional).",
    )

    # ── Terms ─────────────────────────────────────────────────────────
    principal_amount = models.DecimalField(max_digits=18, decimal_places=2)
    remaining_balance = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    interest_rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="APR as percentage (e.g. 6.5 = 6.5%)",
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    term_months = models.IntegerField(
        null=True,
        blank=True,
        help_text="E.g., 360 for 30-year mortgage",
    )

    # ── Payment schedule ──────────────────────────────────────────────
    monthly_payment = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Minimum or agreed monthly payment amount.",
    )
    payment_day = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of month when payment is due.",
    )

    # ── Linked account ────────────────────────────────────────────────
    account = models.ForeignKey(
        "api.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_debts",
        help_text="Account used for payments on this debt.",
    )

    notes = models.TextField(blank=True)

    class Meta:
        db_table = "debt_debt_facility"
        ordering = ["-remaining_balance"]

    def __str__(self) -> str:
        direction = "owe" if self.debt_nature == "MONEY_BORROWED" else "lent"
        return f"{self.name} ({direction} {self.entity_name})"

    @property
    def is_mine(self):
        """True if this is money I borrowed (I owe someone)."""
        return self.debt_nature == "MONEY_BORROWED"

    @property
    def progress_percent(self):
        """How much of the principal has been paid off."""
        if self.principal_amount == 0:
            return 100
        paid = self.principal_amount - self.remaining_balance
        return round((paid / self.principal_amount) * 100, 1)


class DebtPayment(UserOwnedModel):
    """A single payment made against a DebtFacility.

    Each payment breaks down into:
        - Principal portion (reduces remaining_balance)
        - Interest portion (cost of borrowing)
        - Extra payment (additional principal reduction)

    This enables amortization schedules and interest tracking.
    """

    debt = models.ForeignKey(
        DebtFacility,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    payment_date = models.DateField()
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, help_text="Total payment amount"
    )
    principal_portion = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    interest_portion = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))
    extra_payment = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal("0"))

    # ── Auto-generated transaction link ───────────────────────────────
    transaction = models.ForeignKey(
        "api.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="If this payment was recorded as a transaction.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "debt_debt_payment"
        ordering = ["-payment_date"]

    def __str__(self) -> str:
        return f"{self.debt.name} — {self.amount} on {self.payment_date}"
