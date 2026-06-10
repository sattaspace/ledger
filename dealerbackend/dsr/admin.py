"""
DEALERCORE v3.0 — DSR Admin
------------------------------
Admin configuration for DSR (Daily Sales Representative) model.
Includes hierarchy display and sales statistics.
"""

from django.contrib import admin
from django.db.models import Sum, Count, Q
from .models import DSR


@admin.register(DSR)
class DSRAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "role_col", "parent_dsr_name",
                    "subordinate_count", "total_sales", "total_due",
                    "updated_at")
    list_filter = ("role",)
    search_fields = ("name", "phone", "parent_dsr_name")
    readonly_fields = ("id", "subordinate_count", "total_sales",
                       "total_due", "created_at", "updated_at")
    ordering = ("name",)

    fieldsets = (
        ("DSR Info", {
            "fields": ("id", "name", "phone", "role"),
        }),
        ("Hierarchy", {
            "fields": ("parent_dsr", "parent_dsr_name", "subordinate_count"),
        }),
        ("Statistics", {
            "fields": ("total_sales", "total_due"),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    # ── Computed columns ────────────────────────────────────────────────

    def role_col(self, obj):
        """Colour-coded role badge."""
        from django.utils.html import format_html
        if obj.role == "DSR":
            colour = "#0d6efd"
        else:
            colour = "#6f42c1"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:0.85em;">{}</span>',
            colour, obj.role
        )
    role_col.short_description = "Role"

    def subordinate_count(self, obj):
        """Number of Order Collectors under this DSR."""
        return obj.subordinates.count()
    subordinate_count.short_description = "Subordinates"

    def total_sales(self, obj):
        """Total sales amount attributed to this DSR/OC."""
        from decimal import Decimal
        agg = obj.sales.aggregate(total=Sum("total_amount"))
        return agg["total"] or Decimal("0")
    total_sales.short_description = "Total Sales"

    def total_due(self, obj):
        """Total outstanding balance across this DSR's credit sales."""
        from decimal import Decimal
        from django.db.models import F, ExpressionWrapper, DecimalField

        # Only non-voided, non-written-off credit sales with outstanding balance
        due_agg = obj.sales.filter(
            payment_type="Credit",
            is_voided=False,
            is_closed_with_due=False,
        ).annotate(
            balance=ExpressionWrapper(
                F("total_amount") - F("amount_paid"),
                output_field=DecimalField(),
            )
        ).aggregate(total_due=Sum("balance"))
        return due_agg["total_due"] or Decimal("0")
    total_due.short_description = "Total Due"
