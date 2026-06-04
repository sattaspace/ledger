"""
DEALERCORE v3.0 — Sales App Models
------------------------------------
SaleRecord and its embedded CreditPayment records.

Relationships:
  SaleRecord   → Product  (FK: product)
  SaleRecord   → DSR      (FK: dsr, nullable — DSR/OC sales)
  CreditPayment → SaleRecord (FK: sale, on_delete=CASCADE)
"""

from django.db import models


class SaleRecord(models.Model):
    """A single sales transaction. Contains both cash and credit sales.
    `payments` are accessed via reverse relation from CreditPayment."""

    PAYMENT_CASH = "Cash"
    PAYMENT_CREDIT = "Credit"
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, "Cash"),
        (PAYMENT_CREDIT, "Credit"),
    ]

    STATUS_FULLY_PAID = "Fully Paid"
    STATUS_PENDING = "Pending"
    STATUS_PARTIAL = "Partial"
    STATUS_CHOICES = [
        (STATUS_FULLY_PAID, "Fully Paid"),
        (STATUS_PENDING, "Pending"),
        (STATUS_PARTIAL, "Partial"),
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

    # DSR / Order Collector link
    dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        db_column="dsr_id",
    )
    dsr_name = models.CharField(max_length=255, blank=True, default="")

    # Financials
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES)
    amount_paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    collection_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_FULLY_PAID
    )
    due_date = models.DateField(null=True, blank=True)
    date = models.DateTimeField()

    # Write-off flag
    is_closed_with_due = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Sale Record"
        verbose_name_plural = "Sale Records"

    def __str__(self):
        return f"Sale {self.id} — {self.product_name} × {self.quantity}"


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
