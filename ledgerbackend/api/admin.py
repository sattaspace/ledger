"""Django admin configuration for Ledger domain models.

Registers all models with search, filter, and list display capabilities.
Uses the ``all_objects`` manager (includes soft-deleted records) for
admin access, and provides a custom ``SoftDeleteAdmin`` base class with
restore functionality.

The admin interface provides:
    - Search by name, payee, entity_name, etc.
    - Filter by user_id, account_type, status, is_deleted, is_active
    - Bulk restore action for soft-deleted records
    - Read-only audit fields (created_at, updated_at, user_id)
"""

from django.contrib import admin
from django.utils import timezone

from api.models import (
    Institution,
    Account,
    Transaction,
    TransactionSplit,
    Category,
    Tag,
    TransactionTag,
    Card,
    Bill,
    BillPayment,
    DebtFacility,
    DebtPayment,
    Budget,
    InvestmentAccount,
    Holding,
    SavingsGoal,
    InsurancePolicy,
    Invoice,
    InvoiceLineItem,
    DocumentVault,
)
from api.audit import AuditLog


# ── Custom Admin Base ───────────────────────────────────────────────────


class SoftDeleteAdmin(admin.ModelAdmin):
    """Base admin class for UserOwnedModel instances.

    Provides:
        - ``all_objects`` manager (includes soft-deleted)
        - Bulk restore action
        - Standard read-only fields for audit data
        - Filter by is_deleted and is_active
    """

    readonly_fields = ("created_at", "updated_at", "deleted_at", "activated_at")
    list_filter = ("is_deleted", "is_active")
    actions = ["restore_selected"]

    @admin.action(description="Restore selected soft-deleted records")
    def restore_selected(self, request, queryset):
        count = 0
        for obj in queryset.filter(is_deleted=True):
            obj.restore()
            count += 1
        self.message_user(request, f"Successfully restored {count} records.")

    def get_queryset(self, request):
        """Use all_objects manager to show soft-deleted records in admin."""
        qs = self.model.all_objects.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs


# ── Institution ──────────────────────────────────────────────────────────


@admin.register(Institution)
class InstitutionAdmin(SoftDeleteAdmin):
    list_display = ("name", "user_id", "institution_type", "is_active", "is_deleted")
    search_fields = ("name", "user_id")
    list_filter = ("institution_type", "is_active", "is_deleted")


# ── Account ──────────────────────────────────────────────────────────────


@admin.register(Account)
class AccountAdmin(SoftDeleteAdmin):
    list_display = ("name", "user_id", "account_type", "currency", "current_balance", "is_active")
    search_fields = ("name", "user_id")
    list_filter = ("account_type", "currency", "is_active", "is_deleted")


# ── Transaction ──────────────────────────────────────────────────────────


@admin.register(Transaction)
class TransactionAdmin(SoftDeleteAdmin):
    list_display = ("date", "user_id", "account", "transaction_type", "amount_original", "currency_original", "status")
    search_fields = ("payee", "description", "user_id")
    list_filter = ("transaction_type", "status", "currency_original", "is_deleted")
    date_hierarchy = "date"
    raw_id_fields = ("account", "card", "category", "bill", "transfer_pair")


# ── TransactionSplit ─────────────────────────────────────────────────────


@admin.register(TransactionSplit)
class TransactionSplitAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "transaction", "category", "amount", "notes")
    search_fields = ("notes", "user_id")
    raw_id_fields = ("transaction", "category")


# ── Category ──────────────────────────────────────────────────────────────


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ("name", "user_id", "is_income", "parent", "sort_order", "is_active")
    search_fields = ("name", "user_id")
    list_filter = ("is_income", "is_active", "is_deleted")


# ── Tag ───────────────────────────────────────────────────────────────────


@admin.register(Tag)
class TagAdmin(SoftDeleteAdmin):
    list_display = ("name", "user_id", "color", "is_active")
    search_fields = ("name", "user_id")
    list_filter = ("is_active", "is_deleted")


# ── TransactionTag ────────────────────────────────────────────────────────


@admin.register(TransactionTag)
class TransactionTagAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "transaction", "tag")
    raw_id_fields = ("transaction", "tag")


# ── Card ──────────────────────────────────────────────────────────────────


@admin.register(Card)
class CardAdmin(SoftDeleteAdmin):
    list_display = ("card_name", "user_id", "card_type", "last_four", "is_active")
    search_fields = ("card_name", "user_id")
    list_filter = ("card_type", "is_active", "is_deleted")
    raw_id_fields = ("account",)


# ── Bill ──────────────────────────────────────────────────────────────────


@admin.register(Bill)
class BillAdmin(SoftDeleteAdmin):
    list_display = ("payee", "user_id", "amount", "currency", "recurrence", "next_due_date", "status")
    search_fields = ("payee", "user_id")
    list_filter = ("recurrence", "status", "currency", "is_deleted")
    raw_id_fields = ("account", "category")


# ── BillPayment ───────────────────────────────────────────────────────────


@admin.register(BillPayment)
class BillPaymentAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "bill", "payment_date", "amount")
    list_filter = ("is_deleted",)
    raw_id_fields = ("bill",)


# ── DebtFacility ──────────────────────────────────────────────────────────


@admin.register(DebtFacility)
class DebtFacilityAdmin(SoftDeleteAdmin):
    list_display = ("name", "user_id", "debt_nature", "debt_type", "remaining_balance", "currency")
    search_fields = ("name", "entity_name", "user_id")
    list_filter = ("debt_nature", "debt_type", "currency", "is_deleted")
    raw_id_fields = ("institution", "account")


# ── DebtPayment ───────────────────────────────────────────────────────────


@admin.register(DebtPayment)
class DebtPaymentAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "debt", "payment_date", "amount", "principal_portion", "interest_portion")
    list_filter = ("is_deleted",)
    raw_id_fields = ("debt", "transaction")


# ── Budget ────────────────────────────────────────────────────────────────


@admin.register(Budget)
class BudgetAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "category", "amount", "currency", "period", "start_date", "allow_rollover", "include_pending")
    search_fields = ("user_id",)
    list_filter = ("period", "currency", "allow_rollover", "include_pending", "is_deleted")
    raw_id_fields = ("category",)


# ── InvestmentAccount ─────────────────────────────────────────────────────


@admin.register(InvestmentAccount)
class InvestmentAccountAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "account", "portfolio_value", "cost_basis_total")
    raw_id_fields = ("account",)


# ── Holding ───────────────────────────────────────────────────────────────


@admin.register(Holding)
class HoldingAdmin(SoftDeleteAdmin):
    list_display = ("symbol", "user_id", "investment_account", "asset_type", "quantity", "current_value", "currency")
    search_fields = ("symbol", "asset_name", "user_id")
    list_filter = ("asset_type", "currency", "is_deleted")
    raw_id_fields = ("investment_account",)


# ── SavingsGoal ───────────────────────────────────────────────────────────


@admin.register(SavingsGoal)
class SavingsGoalAdmin(SoftDeleteAdmin):
    list_display = ("name", "user_id", "target_amount", "current_amount", "currency", "deadline")
    search_fields = ("name", "user_id")
    list_filter = ("currency", "is_deleted")
    raw_id_fields = ("account",)


# ── InsurancePolicy ───────────────────────────────────────────────────────


@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(SoftDeleteAdmin):
    list_display = ("policy_name", "user_id", "insurance_type", "provider", "premium_amount", "currency", "renewal_date")
    search_fields = ("policy_name", "provider", "policy_number", "user_id")
    list_filter = ("insurance_type", "premium_frequency", "currency", "is_deleted")
    raw_id_fields = ("institution",)


# ── Invoice ───────────────────────────────────────────────────────────────


@admin.register(Invoice)
class InvoiceAdmin(SoftDeleteAdmin):
    list_display = ("invoice_number", "user_id", "client_name", "currency", "status", "due_date")
    search_fields = ("invoice_number", "client_name", "user_id")
    list_filter = ("status", "currency", "is_deleted")
    raw_id_fields = ("transaction",)


# ── InvoiceLineItem ───────────────────────────────────────────────────────


@admin.register(InvoiceLineItem)
class InvoiceLineItemAdmin(SoftDeleteAdmin):
    list_display = ("user_id", "invoice", "description", "quantity", "unit_price", "total")
    search_fields = ("description", "user_id")
    raw_id_fields = ("invoice",)


# ── DocumentVault ─────────────────────────────────────────────────────────


@admin.register(DocumentVault)
class DocumentVaultAdmin(SoftDeleteAdmin):
    list_display = ("title", "user_id", "file_type", "file_size", "content_type", "object_id", "expiry_date")
    search_fields = ("title", "user_id")
    list_filter = ("file_type", "remind_before_expiry", "is_deleted")


# ── AuditLog ──────────────────────────────────────────────────────────────


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for audit logs — read-only, no soft-delete pattern."""

    list_display = ("created_at", "user_id", "action", "model", "object_id", "ip_address")
    search_fields = ("action", "user_id", "model", "ip_address")
    list_filter = ("action", "model")
    date_hierarchy = "created_at"
    readonly_fields = (
        "created_at", "updated_at", "user_id", "action", "model",
        "object_id", "method", "path", "ip_address", "user_agent",
        "before_state", "after_state", "details",
    )

    def has_add_permission(self, request):
        return False  # Audit logs should never be created manually

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs should never be edited

    def has_delete_permission(self, request, obj=None):
        return False  # Audit logs should never be deleted
