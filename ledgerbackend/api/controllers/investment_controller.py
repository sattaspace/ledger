"""Investment controller — CRUD for investment accounts + holdings."""

import logging

from decimal import Decimal

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Account, InvestmentAccount, Holding
from api.schemas.investments import (
    HoldingCreate,
    HoldingFilter,
    HoldingListOut,
    HoldingOut,
    HoldingUpdate,
    InvestmentAccountCreate,
    InvestmentAccountListOut,
    InvestmentAccountOut,
    InvestmentAccountUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/investments", tags=["Investments"])
class InvestmentController(LedgerControllerBase):

    # ── Investment Account List ───────────────────────────────────────────

    @route.get("", response=PaginatedResponse[InvestmentAccountOut])
    def list_investments(self, request):
        """List all investment accounts for the authenticated user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        qs = InvestmentAccount.objects.filter(user_id=user_id).select_related("account")
        return self.paginate(qs)

    @route.get("/summary", response=dict)
    def portfolio_summary(self, request):
        """Get portfolio-wide summary (total value, total cost, total gain/loss)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        from django.db.models import Sum

        qs = InvestmentAccount.objects.filter(user_id=user_id)
        total_value = qs.aggregate(t=Sum("portfolio_value"))["t"] or Decimal("0")
        total_cost = qs.aggregate(t=Sum("cost_basis_total"))["t"] or Decimal("0")
        return {
            "total_portfolio_value": total_value,
            "total_cost_basis": total_cost,
            "total_unrealized_gain_loss": total_value - total_cost,
            "total_gain_loss_percent": round(
                float((total_value - total_cost) / total_cost * 100), 2
            ) if total_cost else 0,
            "account_count": qs.count(),
        }

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:investment_id}", response=InvestmentAccountOut)
    def get_investment(self, request, investment_id: int):
        """Get a single investment account by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        return self.get_or_404(InvestmentAccount, user_id, investment_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=InvestmentAccountOut)
    def create_investment(self, request, payload: InvestmentAccountCreate):
        """Create an investment profile for an existing account."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_investments", InvestmentAccount.objects.filter(user_id=user_id).count())
        # Validate FK ownership — account must belong to this user
        account = self.validate_fk_ownership(request, Account, payload.account_id)
        if account is None:
            from .base import FkOwnershipError
            raise FkOwnershipError("Account", payload.account_id)
        data = payload.model_dump()
        data["account_id"] = data.pop("account_id")
        obj = InvestmentAccount.objects.create(user_id=user_id, **data)
        logger.info("InvestmentAccount created: id=%s user_id=%s", obj.id, user_id)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:investment_id}", response=InvestmentAccountOut)
    def update_investment(self, request, investment_id: int, payload: InvestmentAccountUpdate):
        """Update an investment account."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        obj = self.get_or_404(InvestmentAccount, user_id, investment_id)
        self.update_object(obj, payload, fk_map={
            "account_id": (Account, request),
        })
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:investment_id}", response=MessageOut)
    def soft_delete_investment(self, request, investment_id: int):
        """Soft-delete an investment account and its holdings."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        obj = self.get_or_404(InvestmentAccount, user_id, investment_id)
        obj.soft_delete()
        return {"detail": "Investment account deleted."}

    @route.post("/{int:investment_id}/restore", response=MessageOut)
    def restore_investment(self, request, investment_id: int):
        """Restore a soft-deleted investment account."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_investments",
                            InvestmentAccount.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(InvestmentAccount, user_id, investment_id)
        obj.restore()
        return {"detail": "Investment account restored."}

    # ── Holdings ──────────────────────────────────────────────────────────

    @route.get("/{int:investment_id}/holdings", response=list[HoldingOut])
    def list_holdings(self, request, investment_id: int):
        """List all holdings for an investment account."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        self.get_or_404(InvestmentAccount, user_id, investment_id)
        return list(
            Holding.objects.filter(user_id=user_id, investment_account_id=investment_id)
        )

    @route.post("/{int:investment_id}/holdings", response=HoldingOut)
    def create_holding(self, request, investment_id: int, payload: HoldingCreate):
        """Add a holding to an investment account."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        self.require_subscription_active(request)
        # Holdings share the investment account quota; count both types
        combined_count = (
            InvestmentAccount.objects.filter(user_id=user_id).count()
            + Holding.objects.filter(user_id=user_id).count()
        )
        self.check_plan_limit(request, "max_investments", combined_count)
        inv = self.get_or_404(InvestmentAccount, user_id, investment_id)
        data = payload.model_dump()
        data.pop("investment_account_id", None)
        obj = Holding.objects.create(user_id=user_id, investment_account=inv, **data)

        # Recalculate investment account totals
        self._recalculate_investment_totals(inv)

        logger.info("Holding created: id=%s symbol=%s investment=%s", obj.id, obj.symbol, investment_id)
        return obj

    @route.patch("/{int:investment_id}/holdings/{int:holding_id}", response=HoldingOut)
    def update_holding(self, request, investment_id: int, holding_id: int, payload: HoldingUpdate):
        """Update a holding."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        self.get_or_404(InvestmentAccount, user_id, investment_id)
        try:
            holding = Holding.objects.get(
                id=holding_id, user_id=user_id, investment_account_id=investment_id
            )
        except Holding.DoesNotExist:
            from django.http import Http404
            raise Http404
        self.update_object(holding, payload)
        # Recalculate totals
        inv = self.get_or_404(InvestmentAccount, user_id, investment_id)
        self._recalculate_investment_totals(inv)
        return holding

    @route.delete("/{int:investment_id}/holdings/{int:holding_id}", response=MessageOut)
    def soft_delete_holding(self, request, investment_id: int, holding_id: int):
        """Soft-delete a holding."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "investments")
        self.get_or_404(InvestmentAccount, user_id, investment_id)
        try:
            holding = Holding.objects.get(
                id=holding_id, user_id=user_id, investment_account_id=investment_id
            )
            holding.soft_delete()
        except Holding.DoesNotExist:
            from django.http import Http404
            raise Http404
        # Recalculate totals
        inv = self.get_or_404(InvestmentAccount, user_id, investment_id)
        self._recalculate_investment_totals(inv)
        return {"detail": "Holding deleted."}

    # ── Helpers ───────────────────────────────────────────────────────────

    def _recalculate_investment_totals(self, inv: InvestmentAccount):
        """Recalculate portfolio_value and cost_basis_total from holdings."""
        from django.db.models import Sum

        active_holdings = Holding.objects.filter(
            investment_account=inv, is_deleted=False
        )
        totals = active_holdings.aggregate(
            total_value=Sum("current_value"),
            total_cost=Sum("cost_basis"),
        )
        inv.portfolio_value = totals["total_value"] or Decimal("0")
        inv.cost_basis_total = totals["total_cost"] or Decimal("0")
        inv.save(update_fields=["portfolio_value", "cost_basis_total", "updated_at"])
