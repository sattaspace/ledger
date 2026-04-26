"""Django admin configuration for the users app."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, PasswordResetToken, EmailChangeToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Profile",
            {"fields": ("phone", "avatar", "timezone", "currency", "language")},
        ),
        ("Authentication Status", {"fields": ("is_email_verified", "last_login_ip")}),
        ("SaaS", {"fields": ("role",)}),
    )

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
        "created_at",
    )
    list_filter = ("is_email_verified", "is_active", "is_staff", "role", "created_at")
    search_fields = ("email", "first_name", "last_name", "slug")
    ordering = ("-created_at",)
    readonly_fields = (
        "slug",
        "created_at",
        "updated_at",
        "last_login",
        "last_login_ip",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ("email",)
        return self.readonly_fields


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "user", "created_at", "used_at", "is_valid")
    list_filter = ("used_at", "created_at")
    search_fields = ("token", "user__email")
    readonly_fields = ("token", "created_at", "used_at", "is_valid")

    def is_valid(self, obj):
        return obj.is_valid

    is_valid.boolean = True
    is_valid.short_description = "Valid"


@admin.register(EmailChangeToken)
class EmailChangeTokenAdmin(admin.ModelAdmin):
    list_display = ("token", "user", "new_email", "created_at", "used_at", "is_valid")
    list_filter = ("used_at", "created_at")
    search_fields = ("token", "user__email", "new_email")
    readonly_fields = ("token", "created_at", "used_at", "is_valid")

    def is_valid(self, obj):
        return obj.is_valid

    is_valid.boolean = True
    is_valid.short_description = "Valid"
