"""Debt controller — CRUD for debt facilities + payments with amortization."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.audit import log_audit
from api.models import Account, Institution, DebtFacility, DebtPayment, Transaction
from api.rate_limit import check_rate_limit_or_raise
from api.schemas.debt import (
    DebtFacilityCreate,
    DebtFacilityFilter,
    DebtFacilityListOut,
    DebtFacilityOut,
    DebtFacilityUpdate,
    DebtPaymentCreate,
    DebtPaymentFilter,
    DebtPaymentOut,
    DebtPaymentUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/debts", tags=["Debts"])
class DebtController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[DebtFacilityOut])
    def list_debts(self, request, filters: DebtFacilityFilter = Query(...)):
        """List all debt facilities for the authenticated user."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_debts")
        self.require_feature(request, "debts")
        qs = DebtFacility.objects.filter(user_id=user_id).select_related("institution", "account")
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/summary", response=dict)
    def debt_summary(self, request):
        """Get a summary of total borrowed vs lent amounts."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "report_debts")
        self.require_feature(request, "debts")
        from django.db.models import Sum

        borrowed = DebtFacility.objects.filter(
            user_id=user_id, debt_nature="MONEY_BORROWED",
        ).aggregate(total=Sum("remaining_balance"))["total"] or 0

        lent = DebtFacility.objects.filter(
            user_id=user_id, debt_nature="MONEY_LENT",
        ).aggregate(total=Sum("remaining_balance"))["total"] or 0

        return {
            "total_borrowed": borrowed,
            "total_lent": lent,
            "net_position": lent - borrowed,
        }

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:debt_id}", response=DebtFacilityOut)
    def get_debt(self, request, debt_id: int):
        """Get a single debt facility by ID."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_debts")
        self.require_feature(request, "debts")
        return self.get_or_404(DebtFacility, user_id, debt_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=DebtFacilityOut)
    @log_audit(action="debt.create")
    def create_debt(self, request, payload: DebtFacilityCreate):
        """Create a new debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_debts", DebtFacility.objects.filter(user_id=user_id).count())
        # Validate FK ownership — institution and account must belong to this user
        self.validate_fk_ownership(request, Institution, payload.institution_id)
        self.validate_fk_ownership(request, Account, payload.account_id)
        data = payload.model_dump()
        data["institution_id"] = data.pop("institution_id", None)
        data["account_id"] = data.pop("account_id", None)
        obj = DebtFacility.objects.create(user_id=user_id, **data)
        logger.info("DebtFacility created: id=%s user_id=%s name=%s", obj.id, user_id, obj.name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:debt_id}", response=DebtFacilityOut)
    @log_audit(action="debt.update", capture_state=True)
    def update_debt(self, request, debt_id: int, payload: DebtFacilityUpdate):
        """Update an existing debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        obj = self.get_or_404(DebtFacility, user_id, debt_id)
        self.update_object(obj, payload, fk_map={
            "institution_id": (Institution, request),
            "account_id": (Account, request),
        })
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:debt_id}", response=MessageOut)
    @log_audit(action="debt.delete", capture_state=True)
    def soft_delete_debt(self, request, debt_id: int):
        """Soft-delete a debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "delete_debt")
        self.require_feature(request, "debts")
        obj = self.get_or_404(DebtFacility, user_id, debt_id)
        obj.soft_delete()
        return {"detail": "Debt deleted."}

    @route.post("/{int:debt_id}/restore", response=MessageOut)
    @log_audit(action="debt.restore", capture_state=True)
    def restore_debt(self, request, debt_id: int):
        """Restore a soft-deleted debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_debts",
                            DebtFacility.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(DebtFacility, user_id, debt_id)
        obj.restore()
        return {"detail": "Debt restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:debt_id}/activate", response=MessageOut)
    def activate_debt(self, request, debt_id: int):
        """Activate a debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        obj = self.get_or_404(DebtFacility, user_id, debt_id)
        obj.activate()
        return {"detail": "Debt activated."}

    @route.post("/{int:debt_id}/deactivate", response=MessageOut)
    def deactivate_debt(self, request, debt_id: int):
        """Deactivate a debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        obj = self.get_or_404(DebtFacility, user_id, debt_id)
        obj.deactivate()
        return {"detail": "Debt deactivated."}

    # ── Payments ──────────────────────────────────────────────────────────

    @route.get("/{int:debt_id}/payments", response=list[DebtPaymentOut])
    def list_payments(self, request, debt_id: int):
        """List all payments for a debt facility."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_debts")
        self.require_feature(request, "debts")
        self.get_or_404(DebtFacility, user_id, debt_id)
        return list(
            DebtPayment.objects.filter(user_id=user_id, debt_id=debt_id)
        )

    @route.post("/{int:debt_id}/payments", response=DebtPaymentOut)
    @log_audit(action="debt_payment.create")
    def create_payment(self, request, debt_id: int, payload: DebtPaymentCreate):
        """Record a payment against a debt facility.

        Automatically reduces remaining_balance on the debt by the
        principal_portion + extra_payment.
        """
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_debts",
                            DebtPayment.objects.filter(user_id=user_id).count())
        debt = self.get_or_404(DebtFacility, user_id, debt_id)
        # Validate FK ownership — transaction must belong to this user
        self.validate_fk_ownership(request, Transaction, payload.transaction_id)
        data = payload.model_dump()
        data.pop("debt_id", None)
        data["transaction_id"] = data.pop("transaction_id", None)
        obj = DebtPayment.objects.create(user_id=user_id, debt=debt, **data)

        # Update remaining balance
        reduction = obj.principal_portion + obj.extra_payment
        if reduction > 0:
            debt.remaining_balance -= reduction
            if debt.remaining_balance < 0:
                debt.remaining_balance = 0
            debt.save(update_fields=["remaining_balance", "updated_at"])

        logger.info(
            "DebtPayment created: id=%s debt=%s amount=%s principal=%s interest=%s",
            obj.id, debt_id, obj.amount, obj.principal_portion, obj.interest_portion,
        )
        return obj

    @route.patch("/{int:debt_id}/payments/{int:payment_id}", response=DebtPaymentOut)
    @log_audit(action="debt_payment.update", capture_state=True)
    def update_payment(self, request, debt_id: int, payment_id: int, payload: DebtPaymentUpdate):
        """Update a debt payment."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_debt")
        self.require_feature(request, "debts")
        self.get_or_404(DebtFacility, user_id, debt_id)
        try:
            payment = DebtPayment.objects.get(id=payment_id, user_id=user_id, debt_id=debt_id)
        except DebtPayment.DoesNotExist:
            from django.http import Http404
            raise Http404
        self.update_object(payment, payload)
        return payment
