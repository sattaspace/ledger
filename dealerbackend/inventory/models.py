"""
DEALERCORE v3.0 — Inventory App Models
-----------------------------------------
Products and Restock records.

Relationships:
  Product ←── RestockRecord (FK: product)
  Product ←── SaleRecord   (FK: product, defined in sales app)
"""

from django.db import models


class Product(models.Model):
    """Core inventory item. `stock` starts at 0 and increases via restocks."""

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    brand = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    stock = models.PositiveIntegerField(default=0)
    min_stock_alert = models.PositiveIntegerField(default=5)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)  # COGS per unit
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=255, default="Warehouse")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return f"{self.name} ({self.sku})"


class RestockRecord(models.Model):
    """Every restocking event for a product. `product_name` is denormalized
    so the frontend can display it without an extra join."""

    id = models.CharField(max_length=100, primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="restocks",
        db_column="product_id",
    )
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    supplier_name = models.CharField(max_length=255)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2)
    date = models.DateTimeField()
    received_by = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Restock Record"
        verbose_name_plural = "Restock Records"

    def __str__(self):
        return f"Restock {self.product_name} × {self.quantity}"
