"""Card model — Debit and credit cards linked to accounts."""

from django.db import models

from common.models import UserOwnedModel


class Card(UserOwnedModel):
    """Debit or credit card linked to an account.

    Cards exist because one account can have multiple cards (e.g., joint
    credit card with authorized users, debit card + ATM card on same
    checking account). Transactions can optionally specify which card was used.
    """

    CARD_TYPES = [
        ("DEBIT", "Debit"),
        ("CREDIT", "Credit"),
    ]

    account = models.ForeignKey(
        "api.Account",
        on_delete=models.CASCADE,
        related_name="cards",
    )
    card_type = models.CharField(max_length=10, choices=CARD_TYPES)
    card_name = models.CharField(
        max_length=50,
        help_text="E.g., 'Amazon Prime Visa', 'Chase Sapphire Reserve'",
    )
    last_four = models.CharField(max_length=4)
    expiry_date = models.DateField(null=True, blank=True)

    # ── Fee tracking ──────────────────────────────────────────────────
    annual_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Annual fee for this card.",
    )
    annual_fee_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the annual fee is charged.",
    )

    # ── Display ───────────────────────────────────────────────────────
    color = models.CharField(max_length=7, blank=True, help_text="Card color for UI")
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "cards_card"
        ordering = ["sort_order", "card_name"]
        unique_together = [("user_id", "account", "last_four")]

    def __str__(self) -> str:
        return f"{self.card_name} (****{self.last_four})"
