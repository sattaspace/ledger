"""Core models — Institution, Account, Transaction, TransactionSplit.

The heart of the ledger: institutions hold accounts, accounts hold transactions.
"""

from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericRelation

from common.models import UserOwnedModel


# ===========================================================================
# Institution
# ===========================================================================


class Institution(UserOwnedModel):
    """Financial institution where accounts are held.

    Examples: Chase Bank, HSBC, Binance, Fidelity, "Cash (Wallet)".
    """

    INSTITUTION_TYPES = [
        ("BANK", "Bank"),
        ("CREDIT_UNION", "Credit Union"),
        ("BROKERAGE", "Brokerage"),
        ("CRYPTO", "Crypto Exchange"),
        ("WALLET", "Digital Wallet"),
        ("OTHER", "Other"),
    ]

    name = models.CharField(max_length=100)
    institution_type = models.CharField(
        max_length=20,
        choices=INSTITUTION_TYPES,
        default="BANK",
    )
    website = models.URLField(blank=True)
    customer_service_phone = models.CharField(max_length=20, blank=True)
    icon = models.CharField(
        max_length=50, blank=True, help_text="Icon name from icon library"
    )
    color = models.CharField(
        max_length=7, blank=True, help_text="Hex color for UI, e.g. #1A73E8"
    )
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "core_institution"
        ordering = ["name"]
        unique_together = [("user_id", "name")]

    def __str__(self) -> str:
        return self.name


# ===========================================================================
# Account
# ===========================================================================


class Account(UserOwnedModel):
    """The Ledger: Where money is tracked.

    Every transaction belongs to an account. Accounts can be assets (checking,
    savings), liabilities (credit cards, loans), or investment (brokerage, crypto).

    Currency is stored as ISO 4217 code (CharField) — NOT a FK to a Currency
    model. Currency metadata (symbol, name, decimal_digits) comes from the
    base backend's /billing/currencies endpoint, cached in Redis by
    api/currency.py.
    """

    ACCOUNT_TYPES = [
        ("ASSET", "Asset (Cash, Savings, Checking)"),
        ("LIABILITY", "Liability (Credit Card, Personal Loan)"),
        ("INVESTMENT", "Investment (Brokerage, Crypto)"),
    ]

    name = models.CharField(max_length=100)
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="accounts",
    )
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES)
    currency = models.CharField(
        max_length=3,
        default="USD",
        help_text="ISO 4217 code. Metadata from base backend /billing/currencies.",
    )

    # ── Balance tracking ──────────────────────────────────────────────
    # current_balance is denormalized for dashboard performance.
    # The authoritative source is always the sum of transactions.
    current_balance = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Denormalized. Recalculated from transactions. In account currency.",
    )

    # ── Credit / Loan fields ──────────────────────────────────────────
    credit_limit = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Only for LIABILITY accounts (credit cards, lines of credit).",
    )
    interest_rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default=Decimal("0"),
        help_text="APR as percentage (e.g. 24.99 = 24.99%). Only for LIABILITY accounts.",
    )

    # ── Credit Card billing cycle ─────────────────────────────────────
    statement_closing_day = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of month when statement closes (e.g. 15). Only for credit cards.",
    )
    due_day = models.IntegerField(
        null=True,
        blank=True,
        help_text="Day of month when payment is due (e.g. 1). Only for credit cards.",
    )

    # ── Display ───────────────────────────────────────────────────────
    icon = models.CharField(max_length=50, blank=True)
    color = models.CharField(max_length=7, blank=True, help_text="Hex color for UI")
    notes = models.TextField(blank=True)
    sort_order = models.IntegerField(default=0, help_text="Manual sort order in UI")

    # ── Generic relation for DocumentVault ────────────────────────────
    documents = GenericRelation(
        "api.DocumentVault",
        related_query_name="account",
    )

    class Meta:
        db_table = "core_account"
        ordering = ["sort_order", "name"]
        unique_together = [("user_id", "institution", "name")]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_account_type_display()})"

    # ── Computed properties ───────────────────────────────────────────

    @property
    def available_credit(self):
        """Available credit = credit_limit - current_balance (for liability accounts).

        Returns None when not applicable (asset / investment accounts),
        distinguishing from zero available credit.
        """
        if self.account_type == "LIABILITY" and self.credit_limit is not None:
            return self.credit_limit - self.current_balance
        return None

    @property
    def currency_symbol(self):
        """Get symbol from cached base backend metadata."""
        from api.currency import get_currency_symbol

        return get_currency_symbol(self.currency)

    # ── Balance recalculation ─────────────────────────────────────────

    def recalculate_balance(self):
        """Recalculate current_balance from transactions.

        Should be called after bulk operations or as a periodic integrity check.
        Normal single-transaction saves update the balance incrementally.
        """
        from django.db.models import Sum, Case, When, Value, DecimalField

        # Income & Refund → positive; Expense → negative; Transfer → depends on direction
        # For simplicity, we sum signed amounts based on transaction_type
        signed_amounts = Case(
            When(
                transaction_type__in=["INCOME", "REFUND"],
                then="amount_original",
            ),
            When(
                transaction_type="EXPENSE",
                then=-models.F("amount_original"),  # noqa: DJ012
            ),
            When(
                transaction_type="TRANSFER",
                then=models.Value(Decimal("0")),  # Handled via transfer pairs
                output_field=DecimalField(),
            ),
            default=Value(Decimal("0")),
            output_field=DecimalField(),
        )

        result = self.transactions.filter(
            is_deleted=False,
            status__in=["CLEARED", "PENDING"],
        ).aggregate(total=Sum(signed_amounts))

        self.current_balance = result["total"] or Decimal("0")
        self.save(update_fields=["current_balance", "updated_at"])


# ===========================================================================
# Transaction
# ===========================================================================


class Transaction(UserOwnedModel):
    """A single financial transaction.

    Multi-currency architecture:
        - amount_original + currency_original: What was actually spent/received
        - amount_base: Converted to user's base currency at transaction time (for reports)
        - exchange_rate: Rate captured at transaction creation (immutable historical record)

    For same-currency transactions:
        amount_original == amount_base, exchange_rate == 1.0

    Internal transfers (e.g. paying credit card from checking):
        Two Transaction rows linked via transfer_pair (OneToOneField).
        One is the "outflow" from Account A, the other is the "inflow" to Account B.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("CLEARED", "Cleared"),
        ("VOID", "Void"),
    ]

    TRANSACTION_TYPES = [
        ("INCOME", "Income"),
        ("EXPENSE", "Expense"),
        ("TRANSFER", "Transfer"),
        ("REFUND", "Refund"),
    ]

    # ── Core ──────────────────────────────────────────────────────────
    date = models.DateField(db_index=True)
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    card = models.ForeignKey(
        "api.Card",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TRANSACTION_TYPES,
        default="EXPENSE",
    )

    # ── Amounts ───────────────────────────────────────────────────────
    amount_original = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="Amount in the original (transaction) currency. Always positive.",
    )
    currency_original = models.CharField(
        max_length=3,
        default="USD",
        help_text="ISO 4217 code of the transaction currency.",
    )
    amount_base = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Amount converted to user's base currency at transaction time.",
    )
    exchange_rate = models.DecimalField(
        max_digits=18,
        decimal_places=8,
        default=Decimal("1"),
        help_text="Rate used: amount_base = amount_original * exchange_rate",
    )

    # ── Classification ────────────────────────────────────────────────
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="CLEARED"
    )

    # ── Description ───────────────────────────────────────────────────
    payee = models.CharField(
        max_length=200,
        blank=True,
        help_text="Who was paid or who paid you. E.g. 'Amazon', 'Salary from Acme Corp'",
    )
    description = models.TextField(blank=True)
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Check number, transaction ID, or reference from bank statement",
    )

    # ── Internal Transfers ────────────────────────────────────────────
    transfer_pair = models.OneToOneField(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_transfer",
        help_text="For TRANSFER type: links the outflow and inflow transactions.",
    )

    # ── Recurring / Bill link ─────────────────────────────────────────
    is_recurring = models.BooleanField(
        default=False,
        help_text="Auto-set if created from a Bill",
    )
    bill = models.ForeignKey(
        "api.Bill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_transactions",
        help_text="If this transaction was auto-generated from a recurring bill.",
    )

    # ── Generic relation for DocumentVault ────────────────────────────
    documents = GenericRelation(
        "api.DocumentVault",
        related_query_name="transaction",
    )

    class Meta:
        db_table = "core_transaction"
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user_id", "date"], name="idx_txn_user_date"),
            models.Index(
                fields=["user_id", "account_id", "date"],
                name="idx_txn_acct_date",
            ),
            models.Index(
                fields=["user_id", "category_id"],
                name="idx_txn_user_cat",
            ),
            models.Index(
                fields=["user_id", "transaction_type"],
                name="idx_txn_user_type",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.date} | {self.payee or 'N/A'} | "
            f"{self.amount_original} {self.currency_original}"
        )

    def save(self, *args, **kwargs):
        """Auto-convert currency on creation if amount_base not set,
        and trigger account balance recalculation after save."""
        if not self.pk and self.amount_base == Decimal("0"):
            self._convert_to_base_currency()
        super().save(*args, **kwargs)
        # Recalculate the linked account's balance after every save.
        # For bulk operations, consider using the explicit
        # /accounts/{id}/recalculate-balance endpoint or a Celery task.
        if self.account_id:
            try:
                account = Account.objects.get(id=self.account_id)
                account.recalculate_balance()
            except Account.DoesNotExist:
                pass

    def soft_delete(self):
        """Soft-delete and recalculate account balance."""
        super().soft_delete()
        if self.account_id:
            try:
                account = Account.objects.get(id=self.account_id)
                account.recalculate_balance()
            except Account.DoesNotExist:
                pass

    def restore(self):
        """Restore and recalculate account balance."""
        super().restore()
        if self.account_id:
            try:
                account = Account.objects.get(id=self.account_id)
                account.recalculate_balance()
            except Account.DoesNotExist:
                pass

    def _convert_to_base_currency(self):
        """Convert amount_original to user's base currency using current rates.

        The user's base currency is determined from the linked Account's
        currency field. If the transaction currency differs from the account
        currency, conversion is performed using the base backend's exchange
        rate service (cached in Redis via api/currency.py).

        If conversion fails (e.g., rate not available), falls back to 1:1
        (same-currency assumption) and logs a warning.
        """
        from api.currency import convert_amount

        # Determine base currency from the linked account
        base_currency = self.currency_original  # Default: same currency
        if self.account_id:
            try:
                base_currency = Account.objects.get(id=self.account_id).currency
            except Account.DoesNotExist:
                pass

        if self.currency_original != base_currency:
            converted, rate = convert_amount(
                self.amount_original, self.currency_original, base_currency
            )
            if converted is not None:
                self.amount_base = converted
                self.exchange_rate = rate
                return

        # Same currency or conversion failed — use 1:1
        self.amount_base = self.amount_original
        self.exchange_rate = Decimal("1.0")

    def clean(self):
        """Validate transaction data."""
        super().clean()
        if self.amount_original < 0:
            raise ValidationError(
                {"amount_original": "Amount must be positive. Use transaction_type to indicate direction."}
            )


# ===========================================================================
# TransactionSplit
# ===========================================================================


class TransactionSplit(UserOwnedModel):
    """A portion of a transaction assigned to a specific category.

    Example: A $100 Walmart purchase split into:
      - $60 Groceries (category: Food)
      - $30 Electronics (category: Shopping)
      - $10 Household (category: Home)

    The sum of all splits for a transaction must equal amount_original.
    """

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="splits",
    )
    category = models.ForeignKey(
        "api.Category",
        on_delete=models.SET_NULL,
        null=True,
    )
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "core_transaction_split"

    def __str__(self) -> str:
        return f"Split {self.amount} → {self.category or 'Uncategorized'}"

    def clean(self):
        """Validate that splits don't exceed transaction amount."""
        super().clean()
        from django.db.models import Sum

        total = (
            TransactionSplit.objects.filter(transaction=self.transaction)
            .exclude(pk=self.pk)
            .aggregate(total=Sum("amount"))["total"]
            or Decimal("0")
        )
        if total + self.amount > self.transaction.amount_original:
            raise ValidationError(
                f"Split amounts ({total + self.amount}) exceed transaction "
                f"total ({self.transaction.amount_original})."
            )
