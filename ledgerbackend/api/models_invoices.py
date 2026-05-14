"""Invoice models — Invoice and InvoiceLineItem for freelancers/solopreneurs."""

from django.db import models

from common.models import UserOwnedModel


class Invoice(UserOwnedModel):
    """Invoice for freelancers/solopreneurs.

    Track invoices sent to clients, from creation to payment.
    Linked to a Transaction when payment is received.
    """

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("VIEWED", "Viewed"),
        ("PARTIAL", "Partially Paid"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("CANCELLED", "Cancelled"),
    ]

    invoice_number = models.CharField(max_length=50)
    client_name = models.CharField(max_length=100)
    client_email = models.EmailField(blank=True)

    # ── Dates ─────────────────────────────────────────────────────────
    issue_date = models.DateField()
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)

    # ── Amounts ───────────────────────────────────────────────────────
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="USD")

    # ── Status ────────────────────────────────────────────────────────
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="DRAFT")

    # ── Link to transaction when paid ─────────────────────────────────
    transaction = models.ForeignKey(
        "api.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The income transaction created when this invoice is paid.",
    )

    notes = models.TextField(blank=True)
    terms = models.TextField(
        blank=True, help_text="Payment terms (e.g., 'Net 30')"
    )

    class Meta:
        db_table = "invoices_invoice"
        ordering = ["-issue_date"]
        unique_together = [("user_id", "invoice_number")]

    def __str__(self) -> str:
        return f"INV-{self.invoice_number} — {self.client_name} ({self.get_status_display()})"

    @property
    def amount_due(self):
        return self.total_amount - self.amount_paid

    @property
    def is_overdue(self):
        from django.utils import timezone

        return (
            self.status not in ("PAID", "CANCELLED")
            and self.due_date < timezone.now().date()
        )


class InvoiceLineItem(UserOwnedModel):
    """A line item on an invoice."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name="line_items"
    )
    description = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    total = models.DecimalField(
        max_digits=15, decimal_places=2, help_text="quantity * unit_price"
    )

    class Meta:
        db_table = "invoices_invoice_line_item"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.description} — {self.quantity} x {self.unit_price} = {self.total}"
