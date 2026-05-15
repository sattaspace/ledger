"""Bill controller — CRUD for recurring bills + payments + auto-generation."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Bill, BillPayment, Transaction
from api.schemas.bills import (
    BillCreate,
    BillFilter,
    BillGenerateTransactionOut,
    BillListOut,
    BillOut,
    BillPaymentCreate,
    BillPaymentFilter,
    BillPaymentOut,
    BillPaymentUpdate,
    BillUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/bills", tags=["Bills"])
class BillController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[BillOut])
    def list_bills(self, request, filters: BillFilter = Query(...)):
        """List all bills for the authenticated user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        qs = Bill.objects.filter(user_id=user_id).select_related("account", "category")

        # Handle due_within_days special filter
        filter_dict = filters.model_dump(exclude_unset=True)
        limit = filter_dict.pop("limit", 50)
        offset = filter_dict.pop("offset", 0)
        due_within = filter_dict.pop("due_within_days", None)
        search = filter_dict.pop("search", None)

        from django.utils import timezone
        from datetime import timedelta

        for field, value in filter_dict.items():
            if value is not None:
                qs = qs.filter(**{field: value})

        if due_within:
            today = timezone.now().date()
            future = today + timedelta(days=due_within)
            qs = qs.filter(next_due_date__lte=future)

        if search:
            from django.db.models import Q
            qs = qs.filter(Q(payee__icontains=search) | Q(notes__icontains=search))

        return self.paginate(qs, limit, offset)

    @route.get("/upcoming", response=list[BillListOut])
    def list_upcoming(self, request, days: int = 30):
        """Get bills due within the next N days (for dashboard)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        future = today + timedelta(days=days)
        return list(
            Bill.objects.filter(
                user_id=user_id,
                status="ACTIVE",
                next_due_date__lte=future,
            )
        )

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:bill_id}", response=BillOut)
    def get_bill(self, request, bill_id: int):
        """Get a single bill by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        return self.get_or_404(Bill, user_id, bill_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=BillOut)
    def create_bill(self, request, payload: BillCreate):
        """Create a new bill/subscription."""
        user_id = self.require_user_id(request)
        self.require_subscription_active(request)
        self.require_feature(request, "bills")
        self.check_plan_limit(request, "max_bills",
                            Bill.objects.filter(user_id=user_id).count())
        data = payload.model_dump()
        data["account_id"] = data.pop("account_id", None)
        data["category_id"] = data.pop("category_id", None)
        obj = Bill.objects.create(user_id=user_id, **data)
        logger.info("Bill created: id=%s user_id=%s payee=%s", obj.id, user_id, obj.payee)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:bill_id}", response=BillOut)
    def update_bill(self, request, bill_id: int, payload: BillUpdate):
        """Update an existing bill."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        obj = self.get_or_404(Bill, user_id, bill_id)
        self.update_object(obj, payload)
        return obj

    # ── Generate Transaction ──────────────────────────────────────────────

    @route.post("/{int:bill_id}/generate", response=BillGenerateTransactionOut)
    def generate_transaction(self, request, bill_id: int):
        """Manually generate a transaction from a bill.

        Also auto-called by Celery on the due date.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_transactions",
                            Transaction.objects.filter(user_id=user_id).count())
        obj = self.get_or_404(Bill, user_id, bill_id)
        txn = obj.generate_transaction()
        if txn is None:
            return self.create_response(
                {"detail": "Bill is not active. Cannot generate transaction."},
                status_code=400,
            )
        return {
            "transaction_id": txn.id,
            "bill_id": obj.id,
            "next_due_date": obj.next_due_date,
            "detail": f"Transaction {txn.id} generated for bill '{obj.payee}'.",
        }

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:bill_id}", response=MessageOut)
    def soft_delete_bill(self, request, bill_id: int):
        """Soft-delete a bill."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        obj = self.get_or_404(Bill, user_id, bill_id)
        obj.soft_delete()
        return {"detail": "Bill deleted."}

    @route.post("/{int:bill_id}/restore", response=MessageOut)
    def restore_bill(self, request, bill_id: int):
        """Restore a soft-deleted bill."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_bills",
                            Bill.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Bill, user_id, bill_id)
        obj.restore()
        return {"detail": "Bill restored."}

    # ── Activate / Deactivate (uses Bill status, not ActivatorModel) ──────

    @route.post("/{int:bill_id}/pause", response=MessageOut)
    def pause_bill(self, request, bill_id: int):
        """Pause a bill (stops auto-generation)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        obj = self.get_or_404(Bill, user_id, bill_id)
        obj.status = "PAUSED"
        obj.save(update_fields=["status", "updated_at"])
        return {"detail": "Bill paused."}

    @route.post("/{int:bill_id}/cancel", response=MessageOut)
    def cancel_bill(self, request, bill_id: int):
        """Cancel a bill permanently."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        obj = self.get_or_404(Bill, user_id, bill_id)
        obj.status = "CANCELLED"
        obj.save(update_fields=["status", "updated_at"])
        return {"detail": "Bill cancelled."}

    @route.post("/{int:bill_id}/reactivate", response=MessageOut)
    def reactivate_bill(self, request, bill_id: int):
        """Reactivate a paused or cancelled bill."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        obj = self.get_or_404(Bill, user_id, bill_id)
        obj.status = "ACTIVE"
        obj.save(update_fields=["status", "updated_at"])
        return {"detail": "Bill reactivated."}

    # ── Payments ──────────────────────────────────────────────────────────

    @route.get("/{int:bill_id}/payments", response=list[BillPaymentOut])
    def list_payments(self, request, bill_id: int):
        """List all payments for a bill."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        self.get_or_404(Bill, user_id, bill_id)
        return list(
            BillPayment.objects.filter(user_id=user_id, bill_id=bill_id)
        )

    @route.post("/{int:bill_id}/payments", response=BillPaymentOut)
    def create_payment(self, request, bill_id: int, payload: BillPaymentCreate):
        """Record a payment for a bill."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_bills",
                            BillPayment.objects.filter(user_id=user_id).count())
        bill = self.get_or_404(Bill, user_id, bill_id)
        data = payload.model_dump()
        data.pop("bill_id", None)  # Use URL param
        data["transaction_id"] = data.pop("transaction_id", None)
        obj = BillPayment.objects.create(user_id=user_id, bill=bill, **data)
        logger.info("BillPayment created: id=%s bill=%s amount=%s", obj.id, bill_id, obj.amount)
        return obj

    @route.patch("/{int:bill_id}/payments/{int:payment_id}", response=BillPaymentOut)
    def update_payment(self, request, bill_id: int, payment_id: int, payload: BillPaymentUpdate):
        """Update a bill payment."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "bills")
        self.get_or_404(Bill, user_id, bill_id)
        try:
            payment = BillPayment.objects.get(id=payment_id, user_id=user_id, bill_id=bill_id)
        except BillPayment.DoesNotExist:
            from django.http import Http404
            raise Http404
        self.update_object(payment, payload)
        return payment
