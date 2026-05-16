"""Budget controller — CRUD for spending limits by category and period."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import Category, Budget
from api.schemas.budgets import (
    BudgetCreate,
    BudgetFilter,
    BudgetListOut,
    BudgetOut,
    BudgetUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/budgets", tags=["Budgets"])
class BudgetController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[BudgetOut])
    def list_budgets(self, request, filters: BudgetFilter = Query(...)):
        """List all budgets for the authenticated user.

        The spent_amount, remaining, and percent_used are computed
        dynamically from transactions for accuracy.
        """
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        qs = Budget.objects.filter(user_id=user_id).select_related("category")
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/overview", response=list[BudgetListOut])
    def budget_overview(self, request):
        """Get all budgets with spending status (for dashboard)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        return list(
            Budget.objects.filter(user_id=user_id).select_related("category")
        )

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:budget_id}", response=BudgetOut)
    def get_budget(self, request, budget_id: int):
        """Get a single budget by ID with computed spending."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        return self.get_or_404(Budget, user_id, budget_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=BudgetOut)
    def create_budget(self, request, payload: BudgetCreate):
        """Create a new budget for a category."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_budgets", Budget.objects.filter(user_id=user_id).count())
        # Validate FK ownership — category must belong to this user
        category = self.validate_fk_ownership(request, Category, payload.category_id)
        if category is None:
            from .base import FkOwnershipError
            raise FkOwnershipError("Category", payload.category_id)
        data = payload.model_dump()
        data["category_id"] = data.pop("category_id")
        obj = Budget.objects.create(user_id=user_id, **data)
        logger.info("Budget created: id=%s user_id=%s category=%s", obj.id, user_id, obj.category_id)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:budget_id}", response=BudgetOut)
    def update_budget(self, request, budget_id: int, payload: BudgetUpdate):
        """Update an existing budget."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        obj = self.get_or_404(Budget, user_id, budget_id)
        self.update_object(obj, payload, fk_map={
            "category_id": (Category, request),
        })
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:budget_id}", response=MessageOut)
    def soft_delete_budget(self, request, budget_id: int):
        """Soft-delete a budget."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        obj = self.get_or_404(Budget, user_id, budget_id)
        obj.soft_delete()
        return {"detail": "Budget deleted."}

    @route.post("/{int:budget_id}/restore", response=MessageOut)
    def restore_budget(self, request, budget_id: int):
        """Restore a soft-deleted budget."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_budgets",
                            Budget.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Budget, user_id, budget_id)
        obj.restore()
        return {"detail": "Budget restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:budget_id}/activate", response=MessageOut)
    def activate_budget(self, request, budget_id: int):
        """Activate a budget."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        obj = self.get_or_404(Budget, user_id, budget_id)
        obj.activate()
        return {"detail": "Budget activated."}

    @route.post("/{int:budget_id}/deactivate", response=MessageOut)
    def deactivate_budget(self, request, budget_id: int):
        """Deactivate a budget."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "budgets")
        obj = self.get_or_404(Budget, user_id, budget_id)
        obj.deactivate()
        return {"detail": "Budget deactivated."}
