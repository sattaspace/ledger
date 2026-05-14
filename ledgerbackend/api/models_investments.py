"""Investment models — InvestmentAccount and Holding.

InvestmentAccount extends Account for investment-specific tracking.
Holding tracks individual positions (stocks, crypto, bonds, etc.).
"""

from django.db import models

from common.models import UserOwnedModel


class InvestmentAccount(UserOwnedModel):
    """Extension of Account for investment/brokerage accounts.

    An Account with account_type=INVESTMENT can optionally have this
    extension model for investment-specific tracking (overall portfolio
    value, unrealized gains/losses).
    """

    account = models.OneToOneField(
        "api.Account",
        on_delete=models.CASCADE,
        related_name="investment_profile",
    )
    portfolio_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Total current value of all holdings.",
    )
    cost_basis_total = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        help_text="Total amount invested across all holdings.",
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When holdings were last updated from market data.",
    )

    class Meta:
        db_table = "investments_investment_account"

    def __str__(self) -> str:
        return f"Investment: {self.account.name}"

    @property
    def unrealized_gain_loss(self):
        return self.portfolio_value - self.cost_basis_total

    @property
    def unrealized_gain_loss_percent(self):
        if self.cost_basis_total == 0:
            return 0
        return round((self.unrealized_gain_loss / self.cost_basis_total) * 100, 2)


class Holding(UserOwnedModel):
    """A single investment position within an InvestmentAccount.

    Examples: 10 shares of AAPL, 0.5 BTC, $5,000 in Vanguard Total Market Index.
    """

    ASSET_TYPES = [
        ("STOCK", "Stock"),
        ("ETF", "ETF"),
        ("CRYPTO", "Cryptocurrency"),
        ("BOND", "Bond"),
        ("MUTUAL_FUND", "Mutual Fund"),
        ("OTHER", "Other"),
    ]

    investment_account = models.ForeignKey(
        InvestmentAccount,
        on_delete=models.CASCADE,
        related_name="holdings",
    )
    symbol = models.CharField(
        max_length=20, help_text="Ticker symbol: AAPL, BTC, VTI"
    )
    asset_name = models.CharField(
        max_length=100,
        help_text="Full name: Apple Inc., Bitcoin, Vanguard Total Stock Market",
    )
    asset_type = models.CharField(max_length=15, choices=ASSET_TYPES)

    # ── Position ──────────────────────────────────────────────────────
    quantity = models.DecimalField(
        max_digits=18, decimal_places=8, help_text="Shares/units held"
    )
    cost_basis = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        help_text="Total amount paid for this position (not per-share).",
    )
    current_price = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Latest market price per unit (updated via API).",
    )
    current_value = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="quantity * current_price (updated via API).",
    )
    currency = models.CharField(max_length=3, default="USD")

    # ── Metadata ──────────────────────────────────────────────────────
    purchase_date = models.DateField(null=True, blank=True)
    last_price_update = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "investments_holding"
        ordering = ["-current_value"]
        unique_together = [("user_id", "investment_account", "symbol")]

    def __str__(self) -> str:
        return f"{self.symbol} — {self.quantity} ({self.get_asset_type_display()})"

    @property
    def unrealized_gain_loss(self):
        if self.current_value is not None and self.cost_basis:
            return self.current_value - self.cost_basis
        return None

    @property
    def average_purchase_price(self):
        if self.quantity and self.quantity > 0:
            return self.cost_basis / self.quantity
        return None
