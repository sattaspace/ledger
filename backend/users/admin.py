"""Django admin configuration for the users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import User, OTP


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for the User model.

    Extends Django's built-in UserAdmin with email-based auth support,
    additional profile fields, and OAuth information.
    """

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "phone",
                    "avatar",
                    "timezone",
                    "currency",
                    "language",
                )
            },
        ),
        (
            "Authentication Status",
            {
                "fields": (
                    "is_email_verified",
                    "last_login_ip",
                )
            },
        ),
        (
            "OAuth",
            {
                "fields": (
                    "oauth_provider",
                    "oauth_uid",
                )
            },
        ),
        (
            "SaaS",
            {"fields": ("role",)},
        ),
    )

    # Remove 'username' from add_fieldsets (we use email instead)
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    list_display = (
        "email",
        "slug",
        "first_name",
        "last_name",
        "is_email_verified",
        "is_active",
        "is_staff",
        "role",
        "oauth_provider",
        "created_at",
    )
    list_filter = (
        "is_email_verified",
        "is_active",
        "is_staff",
        "role",
        "oauth_provider",
        "created_at",
    )
    search_fields = ("email", "first_name", "last_name", "oauth_uid", "slug")
    ordering = ("-created_at",)

    readonly_fields = (
        "slug",
        "created_at",
        "updated_at",
        "last_login",
        "last_login_ip",
        "oauth_provider",
        "oauth_uid",
    )

    def get_readonly_fields(self, request, obj=None):
        """Make some fields read-only when editing (but not creating)."""
        if obj:
            return self.readonly_fields + ("email",)
        return self.readonly_fields


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    """Admin for the OTP model."""

    list_display = (
        "user",
        "code",
        "purpose",
        "is_used",
        "attempts",
        "expires_at",
        "created_at",
        "ip_address",
    )
    list_filter = ("purpose", "is_used", "created_at")
    search_fields = ("user__email", "code", "ip_address")
    ordering = ("-created_at",)
    readonly_fields = ("code", "created_at", "updated_at")

    actions = ["invalidate_otps"]

    @admin.action(description="Invalidate selected OTPs")
    def invalidate_otps(self, request, queryset):
        """Mark selected OTPs as used (invalidated)."""
        count = queryset.update(is_used=True)
        self.message_user(request, f"{count} OTP(s) invalidated.")
