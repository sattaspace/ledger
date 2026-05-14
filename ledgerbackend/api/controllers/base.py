"""Base controller for all Ledger domain controllers.

Provides:
    - Auth helper: require_user_id() — extracts Sattabase user_id or 401
    - Object lookup: get_or_404() — scoped by user_id, excludes soft-deleted
    - Object lookup: get_with_deleted_or_404() — includes soft-deleted (for restore)
    - Pagination: paginate() — consistent paginated list responses
    - Filter application: apply_filters() — common filter logic
"""

import logging
from typing import Type

from django.http import Http404
from ninja_extra import ControllerBase

from api.schemas.common import PaginatedResponse

logger = logging.getLogger(__name__)


class LedgerControllerBase(ControllerBase):
    """Base controller for all Ledger domain controllers.

    Every controller inherits from this class, which provides:
      - Sattabase user_id extraction from request.sattabase_user
      - Scoped object lookups (user_id + pk)
      - Soft-delete-aware queries
      - Consistent pagination

    Usage:
        @api_controller("/institutions", tags=["Institutions"])
        class InstitutionController(LedgerControllerBase):
            @route.get("", response=PaginatedResponse[InstitutionOut])
            def list_institutions(self, request, ...):
                user_id = self.require_user_id(request)
                ...
    """

    # ── Auth helpers ──────────────────────────────────────────────────────

    def get_user_id(self, request) -> int | None:
        """Extract user_id from the Sattabase middleware attributes.

        Returns None if the user is not authenticated via Sattabase.
        """
        user = getattr(request, "sattabase_user", None)
        if user is not None and hasattr(user, "id"):
            return user.id
        return None

    def require_user_id(self, request) -> int:
        """Extract user_id or return a 401 response.

        Use this at the top of every endpoint that requires authentication.
        """
        user_id = self.get_user_id(request)
        if user_id is None:
            raise AuthRequiredError()
        return user_id

    # ── Object lookup helpers ─────────────────────────────────────────────

    def get_or_404(self, model_class: Type, user_id: int, pk: int):
        """Get an active (non-deleted) object scoped by user_id, or raise 404.

        Uses the ActiveManager (objects) which excludes soft-deleted records.
        """
        try:
            return model_class.objects.get(id=pk, user_id=user_id)
        except model_class.DoesNotExist:
            raise Http404

    def get_with_deleted_or_404(self, model_class: Type, user_id: int, pk: int):
        """Get an object (including soft-deleted) scoped by user_id, or raise 404.

        Uses the raw Manager (all_objects) which includes everything.
        Used for restore endpoints.
        """
        try:
            return model_class.all_objects.get(id=pk, user_id=user_id)
        except model_class.DoesNotExist:
            raise Http404

    # ── Pagination helper ─────────────────────────────────────────────────

    def paginate(self, queryset, limit: int = 50, offset: int = 0) -> dict:
        """Paginate a queryset and return a dict matching PaginatedResponse.

        Returns:
            {
                "items": [...],
                "pagination": {
                    "total": N,
                    "limit": L,
                    "offset": O,
                    "has_more": True/False
                }
            }
        """
        total = queryset.count()
        has_more = total > offset + limit
        items = list(queryset[offset : offset + limit])
        return {
            "items": items,
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
            },
        }

    # ── Filter helper ─────────────────────────────────────────────────────

    def apply_filters(self, queryset, filters) -> tuple:
        """Apply filter schema fields to a queryset.

        Handles the common pattern:
          - Skip None values (optional filters)
          - Skip 'limit', 'offset', 'search' (handled separately)
          - Handle 'search' with icontains on name/payee
          - Pass remaining fields as exact lookups

        Returns:
            (filtered_queryset, limit, offset)
        """
        exclude = {"limit", "offset"}
        filter_dict = filters.model_dump(exclude_unset=True)

        limit = filter_dict.pop("limit", 50)
        offset = filter_dict.pop("offset", 0)
        search = filter_dict.pop("search", None)

        # Apply exact-match filters
        for field, value in filter_dict.items():
            if value is not None:
                queryset = queryset.filter(**{field: value})

        # Apply search (icontains on common fields)
        if search:
            # Try name first, then payee (for bills/transactions)
            from django.db.models import Q

            search_q = Q(name__icontains=search)
            # Add payee search if the model has that field
            model = queryset.model
            if hasattr(model, "payee"):
                search_q |= Q(payee__icontains=search)
            if hasattr(model, "entity_name"):
                search_q |= Q(entity_name__icontains=search)
            if hasattr(model, "policy_name"):
                search_q |= Q(policy_name__icontains=search)
            if hasattr(model, "client_name"):
                search_q |= Q(client_name__icontains=search)
            if hasattr(model, "card_name"):
                search_q |= Q(card_name__icontains=search)
            queryset = queryset.filter(search_q)

        return queryset, limit, offset

    # ── Update helper ─────────────────────────────────────────────────────

    def update_object(self, obj, payload) -> None:
        """Apply update schema fields to an object (only provided fields).

        Handles FK field naming: institution_id in schema → institution_id on model.
        """
        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.save()


class AuthRequiredError(Exception):
    """Raised when Sattabase auth is required but not present."""

    def __init__(self):
        self.status_code = 401
        self.detail = "Authentication required via Sattabase."
        super().__init__(self.detail)
