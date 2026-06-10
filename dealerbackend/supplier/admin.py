"""
DEALERCORE v3.0 — Supplier Admin
-----------------------------------
Admin configuration for Supplier model.
Includes restock statistics and category filtering.
"""

from django.contrib import admin
from django.db.models import Sum, Count
from django.utils.html import format_html
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "category", "restock_count",
                    "total_supplied_value", "updated_at")
    list_filter = ("category",)
    search_fields = ("name", "phone", "category")
    readonly_fields = ("id", "restock_count", "total_supplied_value",
                       "created_at", "updated_at")
    ordering = ("name",)

    fieldsets = (
        ("Supplier Info", {
            "fields": ("id", "name", "phone", "category"),
        }),
        ("Statistics", {
            "fields": ("restock_count", "total_supplied_value"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    # ── Computed columns ────────────────────────────────────────────────

    def restock_count(self, obj):
        """Number of restock records linked to this supplier (by name)."""
        from inventory.models import RestockRecord
        return RestockRecord.objects.filter(
            supplier_name=obj.name
        ).count()
    restock_count.short_description = "Restocks"

    def total_supplied_value(self, obj):
        """Total cost of all restocks from this supplier."""
        from decimal import Decimal
        from inventory.models import RestockRecord
        agg = RestockRecord.objects.filter(
            supplier_name=obj.name
        ).aggregate(total=Sum("total_cost"))
        return agg["total"] or Decimal("0")
    total_supplied_value.short_description = "Total Supplied"
