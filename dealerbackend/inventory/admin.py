"""
DEALERCORE v3.0 — Inventory Admin
------------------------------------
Rich admin configuration for Brand, Category, Product, and RestockRecord.
Includes inline restock history, stock alerts, and bulk actions.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum

from .models import Brand, Category, Product, RestockRecord


# ── Inline ──────────────────────────────────────────────────────────────────

class RestockRecordInline(admin.TabularInline):
    """Inline restock history displayed on the Product detail page."""
    model = RestockRecord
    extra = 0
    readonly_fields = ("id", "product_name", "quantity", "supplier_name",
                       "cost_price", "total_cost", "date", "received_by",
                       "created_at")
    fields = ("id", "product_name", "quantity", "supplier_name",
              "cost_price", "total_cost", "date", "received_by", "created_at")
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# ── Brand Admin ─────────────────────────────────────────────────────────────

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ("name", "product_count", "created_at")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")
    ordering = ("name",)

    def product_count(self, obj):
        """Number of products using this brand (by name match)."""
        return Product.objects.filter(brand=obj.name).count()
    product_count.short_description = "Products"


# ── Category Admin ──────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "product_count", "created_at")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at")
    ordering = ("name",)

    def product_count(self, obj):
        """Number of products using this category (by name match)."""
        return Product.objects.filter(category=obj.name).count()
    product_count.short_description = "Products"


# ── Product Admin ───────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "brand", "category", "stock",
                    "stock_status", "unit_price", "selling_price", "margin",
                    "location", "updated_at")
    list_filter = ("brand", "category", "location")
    search_fields = ("name", "sku", "brand", "category")
    readonly_fields = ("id", "created_at", "updated_at", "margin",
                       "total_restocked", "total_restock_cost")
    ordering = ("-updated_at",)
    inlines = [RestockRecordInline]

    fieldsets = (
        ("Identity", {
            "fields": ("id", "name", "sku"),
        }),
        ("Classification", {
            "fields": ("brand", "category", "location"),
        }),
        ("Stock", {
            "fields": ("stock", "min_stock_alert"),
        }),
        ("Pricing", {
            "fields": ("unit_price", "selling_price", "margin"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
        ("Aggregates", {
            "fields": ("total_restocked", "total_restock_cost"),
            "classes": ("collapse",),
        }),
    )

    # ── Computed columns ────────────────────────────────────────────────

    def stock_status(self, obj):
        """Colour-coded stock indicator."""
        if obj.stock == 0:
            colour = "#dc3545"   # red — out of stock
            label = "Out of Stock"
        elif obj.stock <= obj.min_stock_alert:
            colour = "#fd7e14"   # orange — low stock
            label = f"Low ({obj.stock})"
        else:
            colour = "#198754"   # green — OK
            label = f"OK ({obj.stock})"
        return format_html(
            '<span style="color:{};font-weight:600;">{}</span>',
            colour, label
        )
    stock_status.short_description = "Stock"

    def margin(self, obj):
        """Profit margin percentage."""
        if obj.unit_price and obj.selling_price and obj.unit_price > 0:
            pct = ((obj.selling_price - obj.unit_price) / obj.unit_price) * 100
            return f"{pct:.1f}%"
        return "—"
    margin.short_description = "Margin"

    def total_restocked(self, obj):
        """Total units ever restocked for this product."""
        agg = obj.restocks.aggregate(total=Sum("quantity"))
        return agg["total"] or 0
    total_restocked.short_description = "Total Restocked"

    def total_restock_cost(self, obj):
        """Total cost across all restocks."""
        agg = obj.restocks.aggregate(total=Sum("total_cost"))
        return agg["total"] or 0
    total_restock_cost.short_description = "Total Restock Cost"


# ── RestockRecord Admin ─────────────────────────────────────────────────────

@admin.register(RestockRecord)
class RestockRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "product_name", "quantity", "supplier_name",
                    "cost_price", "total_cost", "date", "received_by")
    list_filter = ("supplier_name", "date", "received_by")
    search_fields = ("product_name", "supplier_name", "id")
    readonly_fields = ("id", "created_at", "total_cost")
    date_hierarchy = "date"
    ordering = ("-date",)

    fieldsets = (
        ("Restock Detail", {
            "fields": ("id", "product", "product_name", "quantity",
                       "cost_price", "total_cost"),
        }),
        ("Source", {
            "fields": ("supplier_name", "received_by"),
        }),
        ("Date", {
            "fields": ("date", "created_at"),
        }),
    )
