"""
DEALERCORE v3.0 — User Admin
-----------------------------
Admin configuration for DsrUser model.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import DsrUser


@admin.register(DsrUser)
class DsrUserAdmin(BaseUserAdmin):
    """
    Admin interface for DsrUser model.
    """
    
    list_display = [
        "email",
        "user_type",
        "full_name",
        "is_active",
        "is_staff",
        "email_verified",
        "created_at",
    ]
    list_filter = [
        "user_type",
        "is_active",
        "is_staff",
        "email_verified",
    ]
    search_fields = ["email", "first_name", "last_name", "phone"]
    ordering = ["-created_at"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "last_login",
        "email_verified_at",
    ]
    
    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        (_("Personal Info"), {
            "fields": (
                "first_name",
                "last_name",
                "phone",
                "user_type",
            ),
        }),
        (_("Permissions"), {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        (_("Email Verification"), {
            "fields": (
                "email_verified",
                "email_verified_at",
            ),
        }),
        (_("Dealer Context"), {
            "fields": ("selected_dealer",),
        }),
        (_("Important Dates"), {
            "fields": (
                "last_login",
                "created_at",
                "updated_at",
            ),
        }),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "user_type",
                "first_name",
                "last_name",
                "phone",
                "password1",
                "password2",
                "is_active",
                "is_staff",
            ),
        }),
    )
