"""
DEALERCORE v3.0 — Dealer Admin
---------------------------------
Admin configuration for DealerConfig.
Single-record model with currency and locale settings.
"""

from django.contrib import admin
from .models import DealerConfig


@admin.register(DealerConfig)
class DealerConfigAdmin(admin.ModelAdmin):
    list_display = ("username", "full_name", "role", "business_name",
                    "phone_number", "default_currency", "default_locale",
                    "updated_at")
    search_fields = ("username", "full_name", "business_name",
                     "phone_number", "email", "gst_number")
    readonly_fields = ("username", "created_at", "updated_at")
    ordering = ("username",)

    fieldsets = (
        ("Account", {
            "fields": ("username", "full_name", "role"),
        }),
        ("Business", {
            "fields": ("business_name", "address", "phone_number",
                       "email", "gst_number", "communication_number"),
        }),
        ("Locale", {
            "fields": ("default_currency", "default_locale",
                       "google_map_url"),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def has_add_permission(self, request):
        """Prevent creating multiple configs via admin — use the API instead."""
        return DealerConfig.objects.count() == 0

    def has_delete_permission(self, request, obj=None):
        """Prevent accidental deletion of the sole dealer config."""
        return False
