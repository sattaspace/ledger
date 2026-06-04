"""
DEALERCORE v3.0 — Supplier App Models
---------------------------------------
Simple supplier reference table.
Supplier name is denormalized into RestockRecord.supplier_name.
No formal FK — supplier is referenced by name string in restocks.
"""

from django.db import models


class Supplier(models.Model):
    """Supplier entity. Simple lookup table used during restocking."""

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    category = models.CharField(max_length=255, blank=True, default="General")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.name
