"""
DEALERCORE v3.0 — Sales App Models
------------------------------------
SaleRecord and its embedded CreditPayment records.

Relationships:
  SaleRecord   → Product  (FK: product)
  SaleRecord   → DSR      (FK: dsr, nullable — current collector)
  SaleRecord   → DSR      (FK: original_dsr, nullable — who made the sale)
  CreditPayment → SaleRecord (FK: sale, on_delete=CASCADE)
  SaleReturn   → SaleRecord (FK: sale, on_delete=CASCADE)

AUDIT TRAIL DESIGN:
  - `dsr` / `dsr_name` → the CURRENT collector (can be reassigned for collection)
  - `original_dsr` / `original_dsr_name` → who MADE the sale (immutable after creation)
  This separation ensures accurate sales attribution vs collection responsibility.

RETURN FINANCIAL MODEL:
  - `return_total_amount` tracks cumulative return amounts
  - `net_amount = total_amount - return_total_amount` (property)
  - `balance_due = net_amount - amount_paid` (property)
  - Collection status is recalculated against `net_amount` after each return
  - This ensures returns properly reduce the outstanding obligation

Multi-Tenancy:
  - All sales records belong to a specific dealer for tenant isolation.
  - The dealer field enables proper revenue attribution and data isolation.
"""

from django.db import models


class SaleRecord(models.Model):
    """A single sales transaction. Contains both cash and credit sales.
    `payments` are accessed via reverse relation from CreditPayment.
    
    Dealer-scoped: Each sale belongs to exactly one dealer for proper
    revenue attribution and tenant isolation."""

    PAYMENT_CASH = "Cash"
    PAYMENT_CREDIT = "Credit"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_CREDIT, "Credit"),
    ]

    STATUS_FULLY_PAID = "Fully Paid"
    STATUS_PENDING = "Pending"
    STATUS_PARTIAL = "Partial"
    STATUS_WRITTEN_OFF = "Written Off"
    STATUS_VOIDED = "Voided"
    STATUS_CHOICES = [
        (STATUS_FULLY_PAID, "Fully Paid"),
        (STATUS_PENDING, "Pending"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_WRITTEN_OFF, "Written Off"),
        (STATUS_VOIDED, "Voided"),
    ]

    id = models.CharField(max_length=100, primary_key=True)
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.PROTECT,
        related_name="sales",
        db_column="product_id",
    )
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, blank=True, default="")
    is_vehicle = models.BooleanField(default=False)
    vehicle_number = models.CharField(max_length=50, blank=True, default="")

    # DSR / Order Collector link — CURRENT collector (can be reassigned)
    dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        db_column="dsr_id",
    )
    dsr_name = models.CharField(max_length=255, blank=True, default="")
    dsr_status = models.CharField(
        max_length=20, 
        blank=True, 
        default="active",
        help_text="Status of DSR at time of sale/removal: 'active', 'removed', 'left'"
    )

    # Original DSR — who MADE the sale (immutable after creation)
    # This preserves the sales attribution even when collection is reassigned
    original_dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="original_sales",
        db_column="original_dsr_id",
    )
    original_dsr_name = models.CharField(max_length=255, blank=True, default="")
    original_dsr_status = models.CharField(
        max_length=20, 
        blank=True, 
        default="active",
        help_text="Status of original DSR: 'active', 'removed', 'left'"
    )

    # Dealer association for multi-tenancy
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='sales',
        db_column='dealer_username',
    )

    # Financials
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    return_total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=0,
        help_text="Cumulative total of all return amounts for this sale. "
                  "Net obligation = total_amount - return_total_amount.",
    )
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    collection_status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STATUS_FULLY_PAID
    )
    due_date = models.DateField(null=True, blank=True)
    date = models.DateTimeField()

    # Write-off flag
    is_closed_with_due = models.BooleanField(default=False)

    # Void flag — marks a sale as cancelled/voided
    is_voided = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Sale Record"
        verbose_name_plural = "Sale Records"
        indexes = [
            # For customer due reports
            models.Index(fields=["customer_name", "collection_status", "is_voided", "is_closed_with_due"]),
            # For DSR workload reports
            models.Index(fields=["dsr", "collection_status", "is_voided", "is_closed_with_due"]),
            # For vehicle tracking reports
            models.Index(fields=["vehicle_number", "is_vehicle", "collection_status"]),
            # For filtering active vs voided/written-off sales (used in most reports)
            models.Index(fields=["is_voided", "is_closed_with_due", "payment_type"]),
            # For date-range queries in reports
            models.Index(fields=["date"]),
            # For product performance reports
            models.Index(fields=["product", "is_voided", "is_closed_with_due"]),
            # For dealer-scoped queries (most common)
            models.Index(fields=["dealer", "-date"]),
            models.Index(fields=["dealer", "collection_status"]),
        ]

    def __str__(self):
        return f"Sale {self.id} — {self.product_name} × {self.quantity}"

    @property
    def net_amount(self):
        """Effective sale amount after returns.
        net_amount = total_amount - return_total_amount
        This is the actual obligation the customer owes."""
        return self.total_amount - self.return_total_amount

    @property
    def balance_due(self):
        """Outstanding balance after returns and payments.
        balance_due = net_amount - amount_paid"""
        return self.net_amount - self.amount_paid


class CreditPayment(models.Model):
    """Individual payment against a credit sale. Embedded in SaleRecord
    via the reverse `payments` relation."""

    id = models.CharField(max_length=100, primary_key=True)
    sale = models.ForeignKey(
        SaleRecord,
        on_delete=models.CASCADE,
        related_name="payments",
        db_column="sale_id",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateTimeField()
    received_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "Credit Payment"
        verbose_name_plural = "Credit Payments"

    def __str__(self):
        return f"Payment {self.amount} on Sale {self.sale_id}"


class SaleReturn(models.Model):
    """Records a product return from a sale (e.g., vehicle dispatch return).
    Stock is incremented back when a return is processed.
    The sale's `return_total_amount` is updated to reflect the cumulative returns,
    and `collection_status` is recalculated against the reduced `net_amount`."""
    REASON_CHOICES = [
        ("Defective", "Defective"),
        ("Wrong Item", "Wrong Item"),
        ("Customer Return", "Customer Return"),
        ("Damaged", "Damaged"),
        ("Other", "Other"),
    ]

    id = models.CharField(max_length=100, primary_key=True)
    sale = models.ForeignKey(
        SaleRecord,
        on_delete=models.CASCADE,
        related_name="returns",
        db_column="sale_id",
    )
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    return_amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default="Customer Return")
    processed_by = models.CharField(max_length=255)
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Sale Return"
        verbose_name_plural = "Sale Returns"

    def __str__(self):
        return f"Return {self.quantity}x {self.product_name} from Sale {self.sale_id}"
