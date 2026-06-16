"""
DEALERCORE v3.0 — DSR Admin
------------------------------
Admin configuration for DsrUser (Daily Sales Representative) model.

After DSR→DsrUser merge, this admin replaces the old DSR admin.
DsrUser is the unified model — every DsrUser IS a DSR.

FIX: Removed references to the global `role` field (removed in DSR-004).
Role is now per-dealer via DsrDealerAssignment. The admin now shows
the primary assignment's role with a link to the assignment list.
"""

from django.contrib import admin
from django.db.models import Sum, Count, Q
from django.utils.html import format_html
from users.models import DsrUser


@admin.register(DsrUser)
class DsrUserAdmin(admin.ModelAdmin):
    list_display = ("full_name", "phone", "email", "user_type", "primary_role_col",
                    "subordinate_count", "total_sales", "total_due",
                    "updated_at")
    list_filter = ("user_type",)
    search_fields = ("full_name", "phone", "email")
    readonly_fields = ("id", "primary_role_display", "subordinate_count",
                       "total_sales", "total_due", "created_at", "updated_at")
    ordering = ("full_name",)

    fieldsets = (
        ("DSR User Info", {
            "fields": ("id", "email", "full_name", "phone", "user_type", "is_active"),
        }),
        ("Hierarchy", {
            "fields": ("subordinate_count",),
            "description": "Subordinates are linked via DsrDealerAssignment.parent_dsr.",
        }),
        ("Primary Role", {
            "fields": ("primary_role_display",),
            "description": (
                "Role is per-dealer via DsrDealerAssignment. "
                "This shows the role from the DSR's first active assignment."
            ),
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

    def primary_role_col(self, obj):
        """
        Show role from the first active DsrDealerAssignment.

        FIX DSR-004: The global `role` field was removed.
        Role is now per-dealer via DsrDealerAssignment. This column looks up
        the role from the DSR's active assignments.
        """
        assignment = (
            obj.dealer_assignments
            .filter(status="active")
            .select_related("dealer")
            .order_by("activated_at")
            .first()
        )
        if assignment:
            role = assignment.role
            colour = self._role_colour(role)
            dealer_tag = ""
            if assignment.dealer:
                dealer_tag = format_html(
                    ' <span style="color:#64748b;font-size:0.75em;">@{}</span>',
                    assignment.dealer.username,
                )
            return format_html(
                '<span style="background:{};color:#fff;padding:2px 8px;'
                'border-radius:4px;font-size:0.85em;">{}</span>{}',
                colour, role, dealer_tag,
            )
        return format_html(
            '<span style="color:#94a3b8;font-size:0.85em;">No assignment</span>'
        )
    primary_role_col.short_description = "Primary Role"

    def primary_role_display(self, obj):
        """Detailed role display for the detail view."""
        assignments = (
            obj.dealer_assignments
            .filter(status="active")
            .select_related("dealer")
            .order_by("activated_at")
        )
        if not assignments:
            return "No active assignments"

        lines = []
        for a in assignments:
            dealer_label = a.dealer.username if a.dealer else "unknown"
            colour = self._role_colour(a.role)
            lines.append(
                f'{a.role} @ {dealer_label}'
            )
        return " | ".join(lines)
    primary_role_display.short_description = "Active Roles"

    @staticmethod
    def _role_colour(role: str) -> str:
        """Return a colour hex for the given role."""
        return {
            "DSR": "#0d6efd",
            "Senior_DSR": "#6f42c1",
            "Manager": "#d63384",
            "Collector": "#fd7e14",
        }.get(role, "#64748b")

    def subordinate_count(self, obj):
        """Number of Order Collectors under this DSR (via DsrDealerAssignment.parent_dsr)."""
        return obj.subordinate_assignments.filter(status="active").count()
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
