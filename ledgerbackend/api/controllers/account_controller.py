"""Account controller — CRUD for accounts + balance recalculation."""

import logging

from decimal import Decimal

from ninja import Query
from ninja_extra import api_controller, route

from api.audit import log_audit
from api.rate_limit import check_rate_limit_or_raise
from api.models import Account, Institution
from api.schemas.core import (
    AccountCreate,
    AccountFilter,
    AccountListOut,
    AccountOut,
    AccountUpdate,
    BalanceRecalculateOut,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase, FkOwnershipError

logger = logging.getLogger(__name__)


@api_controller("/accounts", tags=["Accounts"])
class AccountController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[AccountOut])
    def list_accounts(self, request, filters: AccountFilter = Query(...)):
        """List all accounts for the authenticated user, with pagination and filters."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_accounts")
        self.require_feature(request, "accounts")
        qs = Account.objects.filter(user_id=user_id).select_related("institution")
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/dropdown", response=list[AccountListOut])
    def list_dropdown(self, request):
        """Lightweight list for dropdown/select components."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_accounts")
        self.require_feature(request, "accounts")
        return list(Account.objects.filter(user_id=user_id).select_related("institution"))

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:account_id}", response=AccountOut)
    def get_account(self, request, account_id: int):
        """Get a single account by ID."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_accounts")
        self.require_feature(request, "accounts")
        return self.get_or_404(Account, user_id, account_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=AccountOut)
    @log_audit(action="account.create")
    def create_account(self, request, payload: AccountCreate):
        """Create a new account linked to an institution."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_account")
        self.require_subscription_active(request)
        self.require_feature(request, "accounts")
        self.check_plan_limit(request, "max_accounts",
                            Account.objects.filter(user_id=user_id).count())
        # Validate FK ownership — institution must belong to this user
        institution = self.validate_fk_ownership(request, Institution, payload.institution_id)
        if institution is None:
            raise FkOwnershipError("Institution", payload.institution_id)
        data = payload.model_dump()
        data["institution_id"] = data.pop("institution_id")
        obj = Account.objects.create(user_id=user_id, **data)
        logger.info("Account created: id=%s user_id=%s name=%s", obj.id, user_id, obj.name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:account_id}", response=AccountOut)
    @log_audit(action="account.update", capture_state=True)
    def update_account(self, request, account_id: int, payload: AccountUpdate):
        """Update an existing account. Only provided fields are changed."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_account")
        self.require_feature(request, "accounts")
        obj = self.get_or_404(Account, user_id, account_id)
        self.update_object(obj, payload, fk_map={
            "institution_id": (Institution, request),
        })
        return obj

    # ── Balance Recalculation ─────────────────────────────────────────────

    @route.post("/{int:account_id}/recalculate-balance", response=BalanceRecalculateOut)
    @log_audit(action="account.recalculate_balance", capture_state=True)
    def recalculate_balance(self, request, account_id: int):
        """Recalculate account balance from transactions.

        Should be called after bulk operations or as a periodic integrity check.
        Normal single-transaction saves update the balance incrementally.
        """
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_account")
        self.require_feature(request, "accounts")
        obj = self.get_or_404(Account, user_id, account_id)
        old_balance = obj.current_balance
        obj.recalculate_balance()
        obj.refresh_from_db()
        logger.info(
            "Balance recalculated: account=%s old=%s new=%s",
            obj.id, old_balance, obj.current_balance,
        )
        return {
            "account_id": obj.id,
            "old_balance": old_balance,
            "new_balance": obj.current_balance,
            "detail": "Balance recalculated successfully.",
        }

    # ── Soft Delete ───────────────────────────────────────────────────────

    @route.delete("/{int:account_id}", response=MessageOut)
    @log_audit(action="account.delete", capture_state=True)
    def soft_delete_account(self, request, account_id: int):
        """Soft-delete an account (sets is_deleted=True)."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "delete_account")
        self.require_feature(request, "accounts")
        obj = self.get_or_404(Account, user_id, account_id)
        obj.soft_delete()
        logger.info("Account soft-deleted: id=%s user_id=%s", obj.id, user_id)
        return {"detail": "Account deleted."}

    # ── Restore ───────────────────────────────────────────────────────────

    @route.post("/{int:account_id}/restore", response=MessageOut)
    @log_audit(action="account.restore", capture_state=True)
    def restore_account(self, request, account_id: int):
        """Restore a soft-deleted account."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_account")
        self.require_feature(request, "accounts")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_accounts",
                            Account.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Account, user_id, account_id)
        obj.restore()
        logger.info("Account restored: id=%s user_id=%s", obj.id, user_id)
        return {"detail": "Account restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:account_id}/activate", response=MessageOut)
    def activate_account(self, request, account_id: int):
        """Activate an account."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_account")
        self.require_feature(request, "accounts")
        obj = self.get_or_404(Account, user_id, account_id)
        obj.activate()
        return {"detail": "Account activated."}

    @route.post("/{int:account_id}/deactivate", response=MessageOut)
    def deactivate_account(self, request, account_id: int):
        """Deactivate an account."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_account")
        self.require_feature(request, "accounts")
        obj = self.get_or_404(Account, user_id, account_id)
        obj.deactivate()
        return {"detail": "Account deactivated."}
