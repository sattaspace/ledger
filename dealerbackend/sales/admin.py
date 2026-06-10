"""
DEALERCORE v3.0 — Sales Admin
--------------------------------
Rich admin configuration for SaleRecord, CreditPayment, and SaleReturn.
Includes inline payments/returns, status badges, due tracking, and bulk actions.
"""

from decimal import Decimal
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Q

from .models import SaleRecord, CreditPayment, SaleReturn


# ── Inline ──────────────────────────────────────────────────────────────────

class CreditPaymentInline(admin.TabularInline):
    """Inline payment history on the SaleRecord detail page."""
    model = CreditPayment
    extra = 0
    readonly_fields = ("id", "amount", "date", "received_by", "created_at")
    fields = ("id", "amount", "date", "received_by", "created_at")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class SaleReturnInline(admin.TabularInline):
    """Inline return history on the SaleRecord detail page."""
    model = SaleReturn
    extra = 0
    readonly_fields = ("id", "product_name", "quantity", "return_amount",
                       "reason", "processed_by", "date", "created_at")
    fields = ("id", "product_name", "quantity", "return_amount",
              "reason", "processed_by", "date", "created_at")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# ── SaleRecord Admin ────────────────────────────────────────────────────────

@admin.register(SaleRecord)
class SaleRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "product_name", "quantity", "customer_info",
                    "payment_type_col", "total_amount", "return_total_amount",
                    "net_amount_col", "amount_paid", "balance_due",
                    "status_col", "date")
    list_filter = ("payment_type", "collection_status", "is_vehicle",
                   "is_voided", "is_closed_with_due", "date")
    search_fields = ("id", "product_name", "customer_name",
                     "customer_phone", "vehicle_number", "dsr_name",
                     "original_dsr_name")
    readonly_fields = ("id", "created_at", "updated_at", "balance_due",
                       "net_amount_col", "total_paid")
    date_hierarchy = "date"
    ordering = ("-date",)
    inlines = [CreditPaymentInline, SaleReturnInline]

    fieldsets = (
        ("Sale Identity", {
            "fields": ("id", "date"),
        }),
        ("Product", {
            "fields": ("product", "product_name", "quantity",
                       "selling_price"),
        }),
        ("Customer", {
            "fields": ("customer_name", "customer_phone",
                       "is_vehicle", "vehicle_number"),
        }),
        ("DSR / Collector", {
            "fields": ("dsr", "dsr_name", "original_dsr", "original_dsr_name"),
        }),
        ("Payment", {
            "fields": ("payment_type", "total_amount", "return_total_amount",
                       "net_amount_col", "amount_paid", "total_paid",
                       "balance_due"),
        }),
        ("Status", {
            "fields": ("collection_status", "due_date",
                       "is_closed_with_due", "is_voided"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    actions = ["mark_as_written_off", "mark_as_voided", "mark_as_fully_paid"]

    # ── Computed columns ────────────────────────────────────────────────

    def customer_info(self, obj):
        """Customer name with vehicle number if applicable."""
        if obj.is_vehicle and obj.vehicle_number:
            return format_html(
                "{} <span style='color:#6c757d;'>({})</span>",
                obj.customer_name, obj.vehicle_number
            )
        return obj.customer_name
    customer_info.short_description = "Customer"

    def payment_type_col(self, obj):
        """Colour-coded payment type badge."""
        if obj.payment_type == "Cash":
            colour = "#198754"
        else:
            colour = "#0d6efd"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:0.85em;">{}</span>',
            colour, obj.payment_type
        )
    payment_type_col.short_description = "Type"

    def status_col(self, obj):
        """Colour-coded collection status badge."""
        palette = {
            "Fully Paid": "#198754",
            "Pending":    "#dc3545",
            "Partial":    "#fd7e14",
            "Written Off":"#6c757d",
            "Voided":     "#343a40",
        }
        colour = palette.get(obj.collection_status, "#6c757d")
        label = obj.collection_status
        if obj.is_voided:
            colour = "#343a40"
            label = "Voided"
        elif obj.is_closed_with_due:
            colour = "#6c757d"
            label = "Closed w/ Due"
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:0.85em;">{}</span>',
            colour, label
        )
    status_col.short_description = "Status"

    def net_amount_col(self, obj):
        """Net amount after returns = total_amount - return_total_amount."""
        return obj.net_amount
    net_amount_col.short_description = "Net Amount"

    def balance_due(self, obj):
        """Outstanding balance = net_amount − amount_paid."""
        due = obj.balance_due
        if due > 0:
            return format_html(
                '<span style="color:#dc3545;font-weight:600;">{}</span>', due
            )
        return format_html(
            '<span style="color:#198754;">0</span>'
        )
    balance_due.short_description = "Balance Due"

    def total_paid(self, obj):
        """Sum of all credit payments for this sale."""
        agg = obj.payments.aggregate(total=Sum("amount"))
        return agg["total"] or Decimal("0")
    total_paid.short_description = "Total Payments"

    # ── Bulk actions ────────────────────────────────────────────────────

    @admin.action(description="Mark selected sales as Written Off")
    def mark_as_written_off(self, request, queryset):
        # Only mark non-voided, non-already-written-off sales
        eligible = queryset.filter(is_voided=False, is_closed_with_due=False)
        count = eligible.count()
        eligible.update(
            collection_status=SaleRecord.STATUS_WRITTEN_OFF,
            is_closed_with_due=True,
        )
        self.message_user(request, f"{count} sale(s) marked as Written Off.")

    @admin.action(description="Void selected sales (WARNING: does NOT reverse stock via admin — use API)")
    def mark_as_voided(self, request, queryset):
        # Note: Admin bulk void does NOT reverse stock.
        # Use the API endpoint /api/sales/{id}/void for proper stock reversal.
        eligible = queryset.filter(is_voided=False)
        count = eligible.count()
        eligible.update(
            is_voided=True,
            collection_status=SaleRecord.STATUS_VOIDED,
        )
        self.message_user(
            request,
            f"{count} sale(s) voided. WARNING: Stock was NOT reversed. "
            f"Use the API void endpoint for proper stock reversal."
        )

    @admin.action(description="Mark selected sales as Fully Paid")
    def mark_as_fully_paid(self, request, queryset):
        # Only mark non-voided, non-written-off sales
        eligible = queryset.filter(is_voided=False, is_closed_with_due=False)
        count = eligible.count()
        eligible.update(
            collection_status=SaleRecord.STATUS_FULLY_PAID,
        )
        self.message_user(request, f"{count} sale(s) marked as Fully Paid.")


# ── CreditPayment Admin ─────────────────────────────────────────────────────

@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "sale_id", "amount", "date", "received_by")
    list_filter = ("date", "received_by")
    search_fields = ("id", "sale__id", "sale__customer_name", "received_by")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "date"
    ordering = ("-date",)
    raw_id_fields = ("sale",)

    fieldsets = (
        ("Payment", {
            "fields": ("id", "sale", "amount", "date", "received_by"),
        }),
        ("Timestamp", {
            "fields": ("created_at",),
        }),
    )


# ── SaleReturn Admin ────────────────────────────────────────────────────────

@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ("id", "sale_id", "product_name", "quantity",
                    "return_amount", "reason", "processed_by", "date")
    list_filter = ("reason", "date", "processed_by")
    search_fields = ("id", "sale__id", "product_name", "processed_by")
    readonly_fields = ("id", "created_at")
    date_hierarchy = "date"
    ordering = ("-date",)
    raw_id_fields = ("sale",)

    fieldsets = (
        ("Return", {
            "fields": ("id", "sale", "product_name", "quantity",
                       "return_amount", "reason"),
        }),
        ("Processing", {
            "fields": ("processed_by", "date", "created_at"),
        }),
    )
