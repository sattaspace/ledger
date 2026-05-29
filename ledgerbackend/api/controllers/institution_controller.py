"""Institution controller — CRUD for financial institutions."""

import logging

from ninja import Query
from ninja_extra import api_controller, route

from api.audit import log_audit
from api.rate_limit import check_rate_limit_or_raise
from api.models import Institution
from api.schemas.core import (
    InstitutionCreate,
    InstitutionFilter,
    InstitutionListOut,
    InstitutionOut,
    InstitutionUpdate,
)
from api.schemas.common import MessageOut, PaginatedResponse

from .base import AuthRequiredError, LedgerControllerBase

logger = logging.getLogger(__name__)


@api_controller("/institutions", tags=["Institutions"])
class InstitutionController(LedgerControllerBase):

    # ── List ──────────────────────────────────────────────────────────────

    @route.get("", response=PaginatedResponse[InstitutionOut])
    def list_institutions(self, request, filters: InstitutionFilter = Query(...)):
        """List all institutions for the authenticated user, with pagination and filters."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_institutions")
        self.require_feature(request, "institutions")
        qs = Institution.objects.filter(user_id=user_id)
        qs, limit, offset = self.apply_filters(qs, filters)
        return self.paginate(qs, limit, offset)

    @route.get("/dropdown", response=list[InstitutionListOut])
    def list_dropdown(self, request):
        """Lightweight list for dropdown/select components."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_institutions")
        self.require_feature(request, "institutions")
        return list(Institution.objects.filter(user_id=user_id))

    # ── Get ───────────────────────────────────────────────────────────────

    @route.get("/{int:institution_id}", response=InstitutionOut)
    def get_institution(self, request, institution_id: int):
        """Get a single institution by ID."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "list_institutions")
        self.require_feature(request, "institutions")
        return self.get_or_404(Institution, user_id, institution_id)

    # ── Create ────────────────────────────────────────────────────────────

    @route.post("", response=InstitutionOut)
    @log_audit(action="institution.create")
    def create_institution(self, request, payload: InstitutionCreate):
        """Create a new financial institution."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_institution")
        self.require_subscription_active(request)
        self.require_feature(request, "institutions")
        self.check_plan_limit(request, "max_institutions",
                            Institution.objects.filter(user_id=user_id).count())
        obj = Institution.objects.create(user_id=user_id, **payload.model_dump())
        logger.info("Institution created: id=%s user_id=%s name=%s", obj.id, user_id, obj.name)
        return obj

    # ── Update ────────────────────────────────────────────────────────────

    @route.patch("/{int:institution_id}", response=InstitutionOut)
    @log_audit(action="institution.update", capture_state=True)
    def update_institution(self, request, institution_id: int, payload: InstitutionUpdate):
        """Update an existing institution. Only provided fields are changed."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_institution")
        self.require_feature(request, "institutions")
        obj = self.get_or_404(Institution, user_id, institution_id)
        self.update_object(obj, payload)
        return obj

    # ── Soft Delete ───────────────────────────────────────────────────────

    @route.delete("/{int:institution_id}", response=MessageOut)
    @log_audit(action="institution.delete", capture_state=True)
    def soft_delete_institution(self, request, institution_id: int):
        """Soft-delete an institution (sets is_deleted=True)."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "delete_institution")
        self.require_feature(request, "institutions")
        obj = self.get_or_404(Institution, user_id, institution_id)
        obj.soft_delete()
        logger.info("Institution soft-deleted: id=%s user_id=%s", obj.id, user_id)
        return {"detail": "Institution deleted."}

    # ── Restore ───────────────────────────────────────────────────────────

    @route.post("/{int:institution_id}/restore", response=MessageOut)
    @log_audit(action="institution.restore", capture_state=True)
    def restore_institution(self, request, institution_id: int):
        """Restore a soft-deleted institution."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_institution")
        self.require_feature(request, "institutions")
        self.require_subscription_active(request)
        self.check_plan_limit(request, "max_institutions",
                            Institution.objects.filter(user_id=user_id).count())
        obj = self.get_with_deleted_or_404(Institution, user_id, institution_id)
        obj.restore()
        logger.info("Institution restored: id=%s user_id=%s", obj.id, user_id)
        return {"detail": "Institution restored."}

    # ── Activate / Deactivate ─────────────────────────────────────────────

    @route.post("/{int:institution_id}/activate", response=MessageOut)
    def activate_institution(self, request, institution_id: int):
        """Activate an institution."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_institution")
        self.require_feature(request, "institutions")
        obj = self.get_or_404(Institution, user_id, institution_id)
        obj.activate()
        return {"detail": "Institution activated."}

    @route.post("/{int:institution_id}/deactivate", response=MessageOut)
    def deactivate_institution(self, request, institution_id: int):
        """Deactivate an institution (keeps data, excludes from default views)."""
        user_id = self.require_user_id(request)
        check_rate_limit_or_raise(request, "create_institution")
        self.require_feature(request, "institutions")
        obj = self.get_or_404(Institution, user_id, institution_id)
        obj.deactivate()
        return {"detail": "Institution deactivated."}
