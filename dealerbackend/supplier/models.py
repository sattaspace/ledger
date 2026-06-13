"""
DEALERCORE v3.0 — Supplier App Models
---------------------------------------
Simple supplier reference table.
Supplier name is denormalized into RestockRecord.supplier_name.
No formal FK — supplier is referenced by name string in restocks.

Multi-Tenancy:
  - Each supplier belongs to a specific dealer for tenant isolation.
  - Supplier names are unique per dealer, not globally.
"""

from django.db import models


class Supplier(models.Model):
    """Supplier entity. Simple lookup table used during restocking.
    
    Dealer-scoped: Each supplier belongs to exactly one dealer.
    Supplier names are unique per dealer, not globally."""

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, default="")
    category = models.CharField(max_length=255, blank=True, default="General")
    
    # Dealer association for multi-tenancy
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='suppliers',
        db_column='dealer_username',
        # null=True,  # Temporary: will be removed after data migration
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        # Supplier names are unique per dealer, not globally
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'dealer'],
                name='unique_supplier_per_dealer'
            ),
        ]
        indexes = [
            # For category-based filtering
            models.Index(fields=["category"]),
            # For dealer-scoped queries
            models.Index(fields=["dealer", "name"]),
            models.Index(fields=["dealer", "category"]),
        ]

    def __str__(self):
        return self.name
