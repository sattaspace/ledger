"""Invoice controller — CRUD + line items + mark-paid for freelancer invoicing."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Invoice, InvoiceLineItem, Transaction
from api.schemas.invoices import (
    InvoiceCreate,
    InvoiceFilter,
    InvoiceLineItemCreate,
    InvoiceLineItemOut,
    InvoiceLineItemUpdate,
    InvoiceListOut,
    InvoiceMarkPaid,
    InvoiceOut,
    InvoiceUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/invoices", tags=["Invoices"])
class InvoiceController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[InvoiceOut])
    def list_invoices(self, request, filters: InvoiceFilter = Query(...)):
        """List all invoices for the authenticated user."""
        user_id = self.require_user_id(request)
        qs = Invoice.objects.filter(user_id=user_id)

        # Handle special filters
        filter_dict = filters.model_dump(exclude_unset=True)
        limit = filter_dict.pop("limit", 50)
        offset = filter_dict.pop("offset", 0)
        date_from = filter_dict.pop("date_from", None)
        date_to = filter_dict.pop("date_to", None)
        is_overdue = filter_dict.pop("is_overdue", None)
        search = filter_dict.pop("search", None)

        for field, value in filter_dict.items():
            if value is not None:
                qs = qs.filter(**{field: value})

        if date_from:
            qs = qs.filter(issue_date__gte=date_from)
        if date_to:
            qs = qs.filter(issue_date__lte=date_to)

        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(client_name__icontains=search)
                | Q(invoice_number__icontains=search)
            )

        # is_overdue is a computed property — filter in Python for accuracy
        # (can be optimized later with a DB-level annotation)
        if is_overdue is not None:
            import django.utils.timezone
            today = django.utils.timezone.now().date()
            if is_overdue:
                qs = qs.filter(
                    due_date__lt=today,
                    status__in=["DRAFT", "SENT", "VIEWED", "PARTIAL"],
                )
            else:
                qs = qs.filter(
                    due_date__gte=today,
                ) | qs.filter(status__in=["PAID", "CANCELLED"])

        return self.paginate(qs, limit, offset)

    @route.get("/overdue", response=list[InvoiceListOut])
    def list_overdue(self, request):
        """Get all overdue invoices (for dashboard/alerts)."""
        user_id = self.require_user_id(request)
        from django.utils import timezone
        today = timezone.now().date()
        return list(
            Invoice.objects.filter(
                user_id=user_id,
                due_date__lt=today,
                status__in=["DRAFT", "SENT", "VIEWED", "PARTIAL"],
            )
        )

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:invoice_id}", response=InvoiceOut)
    def get_invoice(self, request, invoice_id: int):
        """Get a single invoice by ID."""
        user_id = self.require_user_id(request)
        return self.get_or_404(Invoice, user_id, invoice_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=InvoiceOut)
    def create_invoice(self, request, payload: InvoiceCreate):
        """Create a new invoice."""
        user_id = self.require_user_id(request)
        data = payload.model_dump()
        data["transaction_id"] = data.pop("transaction_id", None)
        obj = Invoice.objects.create(user_id=user_id, **data)
        logger.info("Invoice created: id=%s user_id=%s number=%s", obj.id, user_id, obj.invoice_number)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:invoice_id}", response=InvoiceOut)
    def update_invoice(self, request, invoice_id: int, payload: InvoiceUpdate):
        """Update an existing invoice."""
        user_id = self.require_user_id(request)
        obj = self.get_or_404(Invoice, user_id, invoice_id)
        self.update_object(obj, payload)
        return obj

    # ── Mark Paid ─────────────────────────────────────────────────────────

    @route.post("/{int:invoice_id}/mark-paid", response=InvoiceOut)
    def mark_paid(self, request, invoice_id: int, payload: InvoiceMarkPaid):
        """Mark an invoice as paid.

        Optionally creates an INCOME transaction and links it.
        """
        user_id = self.require_user_id(request)
        obj = self.get_or_404(Invoice, user_id, invoice_id)

        paid_amount = payload.amount_paid or obj.amount_due
        txn_id = payload.transaction_id

        # Auto-create transaction if not provided
        if not txn_id and paid_amount > 0:
            txn = Transaction.objects.create(
                user_id=user_id,
                date=payload.paid_date,
                transaction_type="INCOME",
                amount_original=paid_amount,
                currency_original=obj.currency,
                amount_base=paid_amount,
                exchange_rate=1,
                status="CLEARED",
                payee=obj.client_name,
                description=f"Payment for invoice {obj.invoice_number}",
            )
            txn_id = txn.id

        obj.status = "PAID"
        obj.paid_date = payload.paid_date
        obj.amount_paid = obj.amount_paid + paid_amount
        if txn_id:
            obj.transaction_id = txn_id
        obj.save(update_fields=["status", "paid_date", "amount_paid", "transaction_id", "updated_at"])

        logger.info("Invoice marked paid: id=%s amount=%s", obj.id, paid_amount)
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:invoice_id}", response=MessageOut)
    def soft_delete_invoice(self, request, invoice_id: int):
        """Soft-delete an invoice."""
        user_id = self.require_user_id(request)
        obj = self.get_or_404(Invoice, user_id, invoice_id)
        obj.soft_delete()
        return {"detail": "Invoice deleted."}

    @route.post("/{int:invoice_id}/restore", response=MessageOut)
    def restore_invoice(self, request, invoice_id: int):
        """Restore a soft-deleted invoice."""
        user_id = self.require_user_id(request)
        obj = self.get_with_deleted_or_404(Invoice, user_id, invoice_id)
        obj.restore()
        return {"detail": "Invoice restored."}

    # ── Line Items ────────────────────────────────────────────────────────

    @route.get("/{int:invoice_id}/line-items", response=list[InvoiceLineItemOut])
    def list_line_items(self, request, invoice_id: int):
        """List all line items for an invoice."""
        user_id = self.require_user_id(request)
        self.get_or_404(Invoice, user_id, invoice_id)
        return list(
            InvoiceLineItem.objects.filter(user_id=user_id, invoice_id=invoice_id)
        )

    @route.post("/{int:invoice_id}/line-items", response=InvoiceLineItemOut)
    def create_line_item(self, request, invoice_id: int, payload: InvoiceLineItemCreate):
        """Add a line item to an invoice."""
        user_id = self.require_user_id(request)
        invoice = self.get_or_404(Invoice, user_id, invoice_id)
        data = payload.model_dump()
        data.pop("invoice_id", None)
        obj = InvoiceLineItem.objects.create(user_id=user_id, invoice=invoice, **data)

        # Update invoice totals
        self._recalculate_invoice_totals(invoice)

        logger.info("LineItem created: id=%s invoice=%s", obj.id, invoice_id)
        return obj

    @route.patch("/{int:invoice_id}/line-items/{int:item_id}", response=InvoiceLineItemOut)
    def update_line_item(self, request, invoice_id: int, item_id: int, payload: InvoiceLineItemUpdate):
        """Update a line item."""
        user_id = self.require_user_id(request)
        self.get_or_404(Invoice, user_id, invoice_id)
        try:
            item = InvoiceLineItem.objects.get(id=item_id, user_id=user_id, invoice_id=invoice_id)
        except InvoiceLineItem.DoesNotExist:
            from django.http import Http404
            raise Http404
        self.update_object(item, payload)
        # Recalculate totals
        invoice = self.get_or_404(Invoice, user_id, invoice_id)
        self._recalculate_invoice_totals(invoice)
        return item

    @route.delete("/{int:invoice_id}/line-items/{int:item_id}", response=MessageOut)
    def delete_line_item(self, request, invoice_id: int, item_id: int):
        """Delete a line item from an invoice."""
        user_id = self.require_user_id(request)
        self.get_or_404(Invoice, user_id, invoice_id)
        try:
            item = InvoiceLineItem.objects.get(id=item_id, user_id=user_id, invoice_id=invoice_id)
            item.soft_delete()
        except InvoiceLineItem.DoesNotExist:
            from django.http import Http404
            raise Http404
        # Recalculate totals
        invoice = self.get_or_404(Invoice, user_id, invoice_id)
        self._recalculate_invoice_totals(invoice)
        return {"detail": "Line item deleted."}

    # ── Helper ────────────────────────────────────────────────────────────

    def _recalculate_invoice_totals(self, invoice: Invoice):
        """Recalculate invoice subtotal and total from line items."""
        from django.db.models import Sum

        active_items = InvoiceLineItem.objects.filter(
            invoice=invoice, is_deleted=False
        )
        subtotal = active_items.aggregate(t=Sum("total"))["t"] or 0
        invoice.subtotal = subtotal
        invoice.total_amount = subtotal + invoice.tax_amount
        invoice.save(update_fields=["subtotal", "total_amount", "updated_at"])
