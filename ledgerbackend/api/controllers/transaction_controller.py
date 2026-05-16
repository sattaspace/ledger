"""Transaction controller — CRUD + transfers + splits for financial transactions.

The most complex controller in Ledger. Handles:
  - Standard CRUD for transactions
  - Internal transfers (creates two linked transactions)
  - Transaction splits (split a single transaction across categories)
  - Filtering by date range, amount, type, status, account, etc.
"""

import logging

from decimal import Decimal

from django.db import transaction as db_transaction
from ninja import Query
from ninja_extra import api_controller, route

from api.models import Account, Card, Category, Bill, Transaction, TransactionSplit
from api.schemas.core import (
    TransactionCreate,
    TransactionFilter,
    TransactionListOut,
    TransactionOut,
    TransactionSplitCreate,
    TransactionSplitOut,
    TransactionSplitUpdate,
    TransactionUpdate,
    TransferCreate,
    TransferOut,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase, FkOwnershipError

logger = logging.getLogger(__name__)


@api_controller("/transactions", tags=["Transactions"])
class TransactionController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[TransactionOut])
    def list_transactions(self, request, filters: TransactionFilter = Query(...)):
        """List all transactions for the authenticated user, with filters and pagination.

        Supports filtering by: account, category, type, status, card, currency,
        date range, amount range, search, and recurring flag.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        qs = Transaction.objects.filter(user_id=user_id).select_related("account", "category")

        # Apply filters manually for date/amount range
        filter_dict = filters.model_dump(exclude_unset=True)
        limit = filter_dict.pop("limit", 50)
        offset = filter_dict.pop("offset", 0)
        search = filter_dict.pop("search", None)

        # Special range filters
        date_from = filter_dict.pop("date_from", None)
        date_to = filter_dict.pop("date_to", None)
        amount_min = filter_dict.pop("amount_min", None)
        amount_max = filter_dict.pop("amount_max", None)

        # Standard exact-match filters
        for field, value in filter_dict.items():
            if value is not None:
                qs = qs.filter(**{field: value})

        # Date range
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # Amount range (on amount_original)
        if amount_min is not None:
            qs = qs.filter(amount_original__gte=amount_min)
        if amount_max is not None:
            qs = qs.filter(amount_original__lte=amount_max)

        # Data retention enforcement
        cutoff = self.get_retention_cutoff(request)
        if cutoff:
            qs = qs.filter(date__gte=cutoff)

        # Search on payee and description
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(payee__icontains=search) | Q(description__icontains=search))

        return self.paginate(qs, limit, offset)

    @route.get("/recent", response=list[TransactionListOut])
    def list_recent(self, request, limit: int = 10):
        """Get the most recent transactions (for dashboard)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        qs = Transaction.objects.filter(user_id=user_id).select_related("account", "category")
        # Data retention enforcement
        cutoff = self.get_retention_cutoff(request)
        if cutoff:
            qs = qs.filter(date__gte=cutoff)
        return list(qs[:limit])

    # ── Reports ───────────────────────────────────────────────────────────

    @route.get("/reports/summary", response=dict)
    def get_report_summary(self, request):
        """Get transaction summary report. Requires 'reports' feature."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "reports")
        from django.db.models import Sum, Count, Q
        qs = Transaction.objects.filter(user_id=user_id)
        # Data retention enforcement
        cutoff = self.get_retention_cutoff(request)
        if cutoff:
            qs = qs.filter(date__gte=cutoff)
        summary = qs.aggregate(
            total_transactions=Count("id"),
            total_income=Sum("amount_base", filter=Q(transaction_type="INCOME")),
            total_expense=Sum("amount_base", filter=Q(transaction_type="EXPENSE")),
        )
        return summary

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:transaction_id}", response=TransactionOut)
    def get_transaction(self, request, transaction_id: int):
        """Get a single transaction by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        return self.get_or_404(Transaction, user_id, transaction_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=TransactionOut)
    def create_transaction(self, request, payload: TransactionCreate):
        """Create a new transaction.

        If amount_base is not provided, it is auto-calculated using current
        exchange rates from the base backend.
        """
        user_id = self.require_user_id(request)
        self.require_subscription_active(request)
        self.require_feature(request, "transactions")
        self.check_plan_limit(request, "max_transactions",
                            Transaction.objects.filter(user_id=user_id).count())
        # Validate all FK ownership — every referenced object must belong to this user
        account = self.validate_fk_ownership(request, Account, payload.account_id)
        if account is None:
            raise FkOwnershipError("Account", payload.account_id)
        self.validate_fk_ownership(request, Card, payload.card_id)
        self.validate_fk_ownership(request, Category, payload.category_id)
        self.validate_fk_ownership(request, Bill, payload.bill_id)
        data = payload.model_dump()
        data["account_id"] = data.pop("account_id")
        data["card_id"] = data.pop("card_id", None)
        data["category_id"] = data.pop("category_id", None)
        data["bill_id"] = data.pop("bill_id", None)
        obj = Transaction.objects.create(user_id=user_id, **data)
        logger.info(
            "Transaction created: id=%s user_id=%s type=%s amount=%s",
            obj.id, user_id, obj.transaction_type, obj.amount_original,
        )
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:transaction_id}", response=TransactionOut)
    def update_transaction(self, request, transaction_id: int, payload: TransactionUpdate):
        """Update an existing transaction. Only provided fields are changed."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        obj = self.get_or_404(Transaction, user_id, transaction_id)
        self.update_object(obj, payload, fk_map={
            "account_id": (Account, request),
            "card_id": (Card, request),
            "category_id": (Category, request),
            "bill_id": (Bill, request),
        })
        return obj

    # ── Transfer ──────────────────────────────────────────────────────────

    @route.post("/transfer", response=TransferOut)
    def create_transfer(self, request, payload: TransferCreate):
        """Create an internal transfer between two accounts.

        Creates two linked Transaction records:
          1. Outflow (EXPENSE) from the source account
          2. Inflow (INCOME) to the destination account

        Both are linked via transfer_pair (OneToOneField).
        """
        user_id = self.require_user_id(request)
        self.require_subscription_active(request)
        self.require_feature(request, "transactions")
        self.check_plan_limit(request, "max_transactions",
                            Transaction.objects.filter(user_id=user_id).count())

        # Validate both accounts exist and belong to the user
        from_acct = self.get_or_404(Account, user_id, payload.from_account_id)
        to_acct = self.get_or_404(Account, user_id, payload.to_account_id)

        with db_transaction.atomic():
            # Create outflow transaction
            outflow = Transaction.objects.create(
                user_id=user_id,
                date=payload.date,
                account=from_acct,
                transaction_type="TRANSFER",
                amount_original=payload.amount,
                currency_original=payload.currency,
                amount_base=payload.amount,  # Will be converted in save()
                exchange_rate=Decimal("1.0"),
                status=payload.status,
                description=payload.description or f"Transfer to {to_acct.name}",
            )

            # Create inflow transaction
            inflow = Transaction.objects.create(
                user_id=user_id,
                date=payload.date,
                account=to_acct,
                transaction_type="TRANSFER",
                amount_original=payload.amount,
                currency_original=payload.currency,
                amount_base=payload.amount,  # Will be converted in save()
                exchange_rate=Decimal("1.0"),
                status=payload.status,
                description=payload.description or f"Transfer from {from_acct.name}",
            )

            # Link the pair
            outflow.transfer_pair = inflow
            outflow.save(update_fields=["transfer_pair"])
            inflow.transfer_pair = outflow
            inflow.save(update_fields=["transfer_pair"])

        logger.info(
            "Transfer created: outflow=%s inflow=%s user=%s %s %s -> %s",
            outflow.id, inflow.id, user_id, payload.amount, payload.currency,
            f"{from_acct.name} -> {to_acct.name}",
        )
        return {
            "outflow_transaction_id": outflow.id,
            "inflow_transaction_id": inflow.id,
            "detail": f"Transfer of {payload.amount} {payload.currency} created.",
        }

    # ── Soft Delete ───────────────────────────────────────────────────────

    @route.delete("/{int:transaction_id}", response=MessageOut)
    def soft_delete_transaction(self, request, transaction_id: int):
        """Soft-delete a transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        obj = self.get_or_404(Transaction, user_id, transaction_id)
        obj.soft_delete()
        logger.info("Transaction soft-deleted: id=%s user_id=%s", obj.id, user_id)
        return {"detail": "Transaction deleted."}

    # ── Restore ───────────────────────────────────────────────────────────

    @route.post("/{int:transaction_id}/restore", response=MessageOut)
    def restore_transaction(self, request, transaction_id: int):
        """Restore a soft-deleted transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_transactions",
                            Transaction.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Transaction, user_id, transaction_id)
        obj.restore()
        return {"detail": "Transaction restored."}

    # ── Splits ────────────────────────────────────────────────────────────

    @route.get("/{int:transaction_id}/splits", response=list[TransactionSplitOut])
    def list_splits(self, request, transaction_id: int):
        """List all splits for a transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        # Verify transaction ownership
        self.get_or_404(Transaction, user_id, transaction_id)
        return list(
            TransactionSplit.objects.filter(
                user_id=user_id,
                transaction_id=transaction_id,
            )
        )

    @route.post("/{int:transaction_id}/splits", response=TransactionSplitOut)
    def create_split(self, request, transaction_id: int, payload: TransactionSplitCreate):
        """Add a split to a transaction.

        The sum of all splits must not exceed the transaction's amount_original.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_transactions",
                            TransactionSplit.objects.filter(user_id=user_id).count())
        txn = self.get_or_404(Transaction, user_id, transaction_id)
        # Validate FK ownership
        self.validate_fk_ownership(request, Category, payload.category_id)
        data = payload.model_dump()
        data.pop("transaction_id", None)  # Use the URL param instead
        obj = TransactionSplit.objects.create(
            user_id=user_id,
            transaction=txn,
            **{k: v for k, v in data.items() if v is not None},
        )
        logger.info("Split created: id=%s transaction=%s", obj.id, transaction_id)
        return obj

    @route.patch("/{int:transaction_id}/splits/{int:split_id}", response=TransactionSplitOut)
    def update_split(self, request, transaction_id: int, split_id: int, payload: TransactionSplitUpdate):
        """Update an existing split."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        self.get_or_404(Transaction, user_id, transaction_id)
        try:
            split = TransactionSplit.objects.get(
                id=split_id, user_id=user_id, transaction_id=transaction_id
            )
        except TransactionSplit.DoesNotExist:
            from django.http import Http404
            raise Http404
        self.update_object(split, payload)
        return split

    @route.delete("/{int:transaction_id}/splits/{int:split_id}", response=MessageOut)
    def delete_split(self, request, transaction_id: int, split_id: int):
        """Delete a split from a transaction."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "transactions")
        self.get_or_404(Transaction, user_id, transaction_id)
        try:
            split = TransactionSplit.objects.get(
                id=split_id, user_id=user_id, transaction_id=transaction_id
            )
            split.soft_delete()
        except TransactionSplit.DoesNotExist:
            from django.http import Http404
            raise Http404
        return {"detail": "Split deleted."}
