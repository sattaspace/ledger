"""Insurance controller — CRUD for insurance policy tracking."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.models import InsurancePolicy
from api.schemas.insurance import (
    InsurancePolicyCreate,
    InsurancePolicyFilter,
    InsurancePolicyListOut,
    InsurancePolicyOut,
    InsurancePolicyUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/insurance", tags=["Insurance"])
class InsuranceController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[InsurancePolicyOut])
    def list_policies(self, request, filters: InsurancePolicyFilter = Query(...)):
        """List all insurance policies for the authenticated user."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        qs = InsurancePolicy.objects.filter(user_id=user_id).select_related("institution")

        # Handle renewal_within_days special filter
        filter_dict = filters.model_dump(exclude_unset=True)
        limit = filter_dict.pop("limit", 50)
        offset = filter_dict.pop("offset", 0)
        renewal_within = filter_dict.pop("renewal_within_days", None)
        search = filter_dict.pop("search", None)

        for field, value in filter_dict.items():
            if value is not None:
                qs = qs.filter(**{field: value})

        if renewal_within:
            from django.utils import timezone
            from datetime import timedelta
            today = timezone.now().date()
            future = today + timedelta(days=renewal_within)
            qs = qs.filter(renewal_date__lte=future)

        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(policy_name__icontains=search)
                | Q(provider__icontains=search)
                | Q(policy_number__icontains=search)
            )

        return self.paginate(qs, limit, offset)

    @route.get("/renewals", response=list[InsurancePolicyListOut])
    def upcoming_renewals(self, request, days: int = 60):
        """Get policies with upcoming renewals (for dashboard)."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        from django.utils import timezone
        from datetime import timedelta

        today = timezone.now().date()
        future = today + timedelta(days=days)
        return list(
            InsurancePolicy.objects.filter(
                user_id=user_id,
                renewal_date__lte=future,
                remind_renewal=True,
            )
        )

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:policy_id}", response=InsurancePolicyOut)
    def get_policy(self, request, policy_id: int):
        """Get a single insurance policy by ID."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        return self.get_or_404(InsurancePolicy, user_id, policy_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=InsurancePolicyOut)
    def create_policy(self, request, payload: InsurancePolicyCreate):
        """Create a new insurance policy."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        data = payload.model_dump()
        data["institution_id"] = data.pop("institution_id", None)
        obj = InsurancePolicy.objects.create(user_id=user_id, **data)
        logger.info("InsurancePolicy created: id=%s user_id=%s name=%s", obj.id, user_id, obj.policy_name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:policy_id}", response=InsurancePolicyOut)
    def update_policy(self, request, policy_id: int, payload: InsurancePolicyUpdate):
        """Update an existing insurance policy."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        obj = self.get_or_404(InsurancePolicy, user_id, policy_id)
        self.update_object(obj, payload)
        return obj

    # ── Soft Delete / Restore ─────────────────────────────────────────────

    @route.delete("/{int:policy_id}", response=MessageOut)
    def soft_delete_policy(self, request, policy_id: int):
        """Soft-delete an insurance policy."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        obj = self.get_or_404(InsurancePolicy, user_id, policy_id)
        obj.soft_delete()
        return {"detail": "Insurance policy deleted."}

    @route.post("/{int:policy_id}/restore", response=MessageOut)
    def restore_policy(self, request, policy_id: int):
        """Restore a soft-deleted insurance policy."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        obj = self.get_with_deleted_or_404(InsurancePolicy, user_id, policy_id)
        obj.restore()
        return {"detail": "Insurance policy restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:policy_id}/activate", response=MessageOut)
    def activate_policy(self, request, policy_id: int):
        """Activate an insurance policy."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        obj = self.get_or_404(InsurancePolicy, user_id, policy_id)
        obj.activate()
        return {"detail": "Insurance policy activated."}

    @route.post("/{int:policy_id}/deactivate", response=MessageOut)
    def deactivate_policy(self, request, policy_id: int):
        """Deactivate an insurance policy."""
        user_id = self.require_user_id(request)
        self.require_feature(request, "insurance")
        obj = self.get_or_404(InsurancePolicy, user_id, policy_id)
        obj.deactivate()
        return {"detail": "Insurance policy deactivated."}
