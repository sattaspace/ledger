"""
DEALERCORE v3.0 — Inventory App Models
-----------------------------------------
Brands, Categories, Products and Restock records.

Relationships:
  Brand (standalone registry)
  Category (standalone registry)
  Product ←── RestockRecord (FK: product)
  Product ←── SaleRecord   (FK: product, defined in sales app)

Multi-Tenancy:
  All models have a `dealer` FK to DealerConfig for tenant isolation.
  Each dealer's data is completely isolated from other dealers.
"""

from django.db import models


class Brand(models.Model):
    """Registry of product brands. Used for autocomplete suggestions
    in the product form. Product.brand remains a CharField (denormalized)
    for backward compatibility, but this table tracks known brands.
    
    Dealer-scoped: Each dealer has their own set of brands."""
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='brands',
        db_column='dealer_username',
        # null=True,  # Temporary: will be removed after data migration
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"
        # Brand names are unique per dealer, not globally
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'dealer'],
                name='unique_brand_per_dealer'
            ),
        ]
        indexes = [
            models.Index(fields=['dealer', 'name']),
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Registry of product categories. Used for dropdown selection
    in the product form. Product.category remains a CharField (denormalized)
    for backward compatibility, but this table tracks known categories.
    
    Dealer-scoped: Each dealer has their own set of categories."""
    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='categories',
        db_column='dealer_username',
        null=True,  # Temporary: will be removed after data migration
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        # Category names are unique per dealer, not globally
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'dealer'],
                name='unique_category_per_dealer'
            ),
        ]
        indexes = [
            models.Index(fields=['dealer', 'name']),
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    """Core inventory item. `stock` starts at 0 and increases via restocks.
    
    Dealer-scoped: Each product belongs to exactly one dealer.
    SKU uniqueness is per dealer, not globally."""

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    brand = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    stock = models.PositiveIntegerField(default=0)
    min_stock_alert = models.PositiveIntegerField(default=5)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)  # COGS per unit
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    location = models.CharField(max_length=255, default="Warehouse")
    
    # Dealer association for multi-tenancy
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='products',
        db_column='dealer_username',
        null=True,  # Temporary: will be removed after data migration
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"
        # SKU uniqueness is per dealer, not globally
        constraints = [
            models.UniqueConstraint(
                fields=['sku', 'dealer'],
                name='unique_sku_per_dealer'
            ),
        ]
        indexes = [
            # For low stock queries
            models.Index(fields=["stock", "min_stock_alert"]),
            # For filtering by brand/category
            models.Index(fields=["brand", "category"]),
            # For SKU lookups
            models.Index(fields=["sku"]),
            # For dealer-scoped queries (most common)
            models.Index(fields=["dealer", "name"]),
            models.Index(fields=["dealer", "category"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class RestockRecord(models.Model):
    """Every restocking event for a product. `product_name` is denormalized
    so the frontend can display it without an extra join.
    
    Dealer-scoped: Inherits dealer from the associated product."""

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
    
    # Dealer association for multi-tenancy (denormalized for quick access)
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='restocks',
        db_column='dealer_username',
        # null=True,  # Temporary: will be removed after data migration
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Restock Record"
        verbose_name_plural = "Restock Records"
        indexes = [
            # For product restock history
            models.Index(fields=["product", "-date"]),
            # For supplier performance
            models.Index(fields=["supplier_name", "-date"]),
            # For dealer-scoped queries
            models.Index(fields=["dealer", "-date"]),
        ]

    def __str__(self):
        return f"Restock {self.product_name} × {self.quantity}"
