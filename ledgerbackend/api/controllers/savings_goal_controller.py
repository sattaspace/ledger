"""Savings Goal controller — CRUD + contributions for savings targets."""

import logging

from decimal import Decimal

from ninja import Query
from ninja_extra import api_controller, route

from api.models import SavingsGoal, Transaction
from api.schemas.goals import (
    SavingsContribution,
    SavingsContributionOut,
    SavingsGoalCreate,
    SavingsGoalFilter,
    SavingsGoalListOut,
    SavingsGoalOut,
    SavingsGoalUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/savings-goals", tags=["Savings Goals"])
class SavingsGoalController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[SavingsGoalOut])
    def list_goals(self, request, filters: SavingsGoalFilter = Query(...)):
        """List all savings goals for the authenticated user."""
        user_id = self.require_user_id(request)
        qs = SavingsGoal.objects.filter(user_id=user_id).select_related("account")
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/dashboard", response=list[SavingsGoalListOut])
    def dashboard_goals(self, request):
        """Get savings goals for dashboard (active + uncompleted)."""
        user_id = self.require_user_id(request)
        return list(
            SavingsGoal.objects.filter(
                user_id=user_id, is_active=True, is_deleted=False,
            ).select_related("account")
        )

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:goal_id}", response=SavingsGoalOut)
    def get_goal(self, request, goal_id: int):
        """Get a single savings goal by ID with progress tracking."""
        user_id = self.require_user_id(request)
        return self.get_or_404(SavingsGoal, user_id, goal_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=SavingsGoalOut)
    def create_goal(self, request, payload: SavingsGoalCreate):
        """Create a new savings goal."""
        user_id = self.require_user_id(request)
        data = payload.model_dump()
        data["account_id"] = data.pop("account_id", None)
        obj = SavingsGoal.objects.create(user_id=user_id, **data)
        logger.info("SavingsGoal created: id=%s user_id=%s name=%s", obj.id, user_id, obj.name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:goal_id}", response=SavingsGoalOut)
    def update_goal(self, request, goal_id: int, payload: SavingsGoalUpdate):
        """Update an existing savings goal."""
        user_id = self.require_user_id(request)
        obj = self.get_or_404(SavingsGoal, user_id, goal_id)
        self.update_object(obj, payload)
        return obj

    # ── Contribute ────────────────────────────────────────────────────────

    @route.post("/{int:goal_id}/contribute", response=SavingsContributionOut)
    def contribute(self, request, goal_id: int, payload: SavingsContribution):
        """Add a contribution to a savings goal.

        Optionally creates an INCOME transaction on the linked account
        and updates the goal's current_amount.
        """
        user_id = self.require_user_id(request)
        goal = self.get_or_404(SavingsGoal, user_id, goal_id)

        old_amount = goal.current_amount
        new_amount = old_amount + payload.amount

        # Create transaction if account is specified
        txn_id = None
        if payload.account_id:
            from django.utils import timezone

            txn = Transaction.objects.create(
                user_id=user_id,
                date=payload.date or timezone.now().date(),
                account_id=payload.account_id,
                transaction_type="INCOME",
                amount_original=payload.amount,
                currency_original=goal.currency,
                amount_base=payload.amount,
                exchange_rate=Decimal("1.0"),
                status="CLEARED",
                payee=f"Savings: {goal.name}",
                description=payload.notes or f"Contribution to savings goal: {goal.name}",
            )
            txn_id = txn.id

        # Update goal amount
        goal.current_amount = new_amount
        goal.save(update_fields=["current_amount", "updated_at"])

        logger.info(
            "Savings contribution: goal=%s amount=%s old=%s new=%s",
            goal_id, payload.amount, old_amount, new_amount,
        )
        return {
            "goal_id": goal.id,
            "old_amount": old_amount,
            "new_amount": new_amount,
            "transaction_id": txn_id,
            "detail": f"Contributed {payload.amount} {goal.currency} to '{goal.name}'.",
        }

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:goal_id}", response=MessageOut)
    def soft_delete_goal(self, request, goal_id: int):
        """Soft-delete a savings goal."""
        user_id = self.require_user_id(request)
        obj = self.get_or_404(SavingsGoal, user_id, goal_id)
        obj.soft_delete()
        return {"detail": "Savings goal deleted."}

    @route.post("/{int:goal_id}/restore", response=MessageOut)
    def restore_goal(self, request, goal_id: int):
        """Restore a soft-deleted savings goal."""
        user_id = self.require_user_id(request)
        obj = self.get_with_deleted_or_404(SavingsGoal, user_id, goal_id)
        obj.restore()
        return {"detail": "Savings goal restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:goal_id}/activate", response=MessageOut)
    def activate_goal(self, request, goal_id: int):
        """Activate a savings goal."""
        user_id = self.require_user_id(request)
        obj = self.get_or_404(SavingsGoal, user_id, goal_id)
        obj.activate()
        return {"detail": "Savings goal activated."}

    @route.post("/{int:goal_id}/deactivate", response=MessageOut)
    def deactivate_goal(self, request, goal_id: int):
        """Deactivate a savings goal."""
        user_id = self.require_user_id(request)
        obj = self.get_or_404(SavingsGoal, user_id, goal_id)
        obj.deactivate()
        return {"detail": "Savings goal deactivated."}
