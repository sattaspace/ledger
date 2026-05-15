"""Base controller for all Ledger domain controllers.

Provides:
    - Auth helper: require_user_id() — extracts Sattabase user_id or 401
    - Feature gate: require_feature() — checks access map for feature boolean
    - Subscription: require_subscription_active() — checks subscription status
    - Plan limit: check_plan_limit() — enforces numeric record limits
    - Retention: get_retention_cutoff() — returns date cutoff for data_retention_days
    - API access: require_api_access() — gates external API access
    - Object lookup: get_or_404() — scoped by user_id, excludes soft-deleted
    - Object lookup: get_with_deleted_or_404() — includes soft-deleted (for restore)
    - Pagination: paginate() — consistent paginated list responses
    - Filter application: apply_filters() — common filter logic
"""

import logging
from datetime import datetime, timedelta
from typing import Type

from django.http import Http404
from django.utils import timezone
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

    # ── Feature / subscription helpers ─────────────────────────────────────

    def get_access(self, request) -> dict:
        """Extract the access map from the Sattabase middleware attributes.

        Returns empty dict if access data is not available.
        """
        return getattr(request, "sattabase_access", {}) or {}

    def require_feature(self, request, feature: str) -> None:
        """Verify the user's subscription includes the specified feature.

        Raises FeatureRequiredError (403) if the feature is not enabled.
        Must be called after require_user_id() to ensure authentication first.

        Truthy heuristic matches sidebar: value === true, number > 0,
        non-empty/non-false/non-zero string.
        """
        access = self.get_access(request)
        value = access.get(feature)
        has_access = (
            value is True
            or (isinstance(value, (int, float)) and value > 0)
            or (isinstance(value, str) and value not in ("", "false", "0"))
        )
        if not has_access:
            raise FeatureRequiredError(feature)

    def require_subscription_active(self, request) -> None:
        """Verify the user has an active subscription (not expired/cancelled).

        Raises SubscriptionInactiveError (403) if subscription is not active.
        Must be called after require_user_id() to ensure authentication first.
        """
        subscription = getattr(request, "sattabase_subscription", None)
        if subscription is None or not getattr(subscription, "is_active", False):
            raise SubscriptionInactiveError()

    def check_plan_limit(self, request, limit_key: str, current_count: int) -> int:
        """Check a numeric plan limit from the access map.

        Args:
            limit_key: Access map key (e.g. "max_accounts", "max_transactions").
            current_count: Current number of items the user has.

        Returns:
            The maximum allowed count from the access map.

        Raises PlanLimitReachedError (403) if current_count >= limit.
        """
        access = self.get_access(request)
        max_allowed = access.get(limit_key)
        if max_allowed is not None:
            try:
                max_allowed = int(max_allowed)
            except (ValueError, TypeError):
                max_allowed = None
        if max_allowed is not None and current_count >= max_allowed:
            raise PlanLimitReachedError(limit_key, max_allowed)
        return max_allowed or 0

    # ── Data retention helper ─────────────────────────────────────────────

    def get_retention_cutoff(self, request) -> datetime | None:
        """Return the date cutoff for data retention enforcement.

        Reads `data_retention_days` from the access map. Returns a datetime
        such that records older than it should be excluded from queries.
        Returns None if retention is unlimited (0 or missing).

        Plan values: Free=90 days, Standard=365 days, Pro=0 (forever)

        Usage in list endpoints:
            cutoff = self.get_retention_cutoff(request)
            if cutoff:
                qs = qs.filter(date__gte=cutoff)
        """
        access = self.get_access(request)
        days = access.get("data_retention_days")
        if days is not None:
            try:
                days = int(days)
                if days > 0:  # 0 means unlimited
                    return timezone.now() - timedelta(days=days)
            except (ValueError, TypeError):
                pass
        return None  # No retention limit

    # ── API access helper ──────────────────────────────────────────────────

    def require_api_access(self, request) -> None:
        """Verify the user's subscription includes API access.

        Raises FeatureRequiredError (403) if api_access is not enabled.
        Use this on endpoints that should only be accessible via
        programmatic API (not browser-based requests).

        Plan values: Free=false, Standard=true, Pro=true
        """
        self.require_feature(request, "api_access")

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


class FeatureRequiredError(Exception):
    """Raised when the user's subscription doesn't include a required feature."""

    def __init__(self, feature: str):
        self.status_code = 403
        self.feature = feature
        self.detail = f"Your subscription does not include the '{feature}' feature. Please upgrade your plan."
        super().__init__(self.detail)


class SubscriptionInactiveError(Exception):
    """Raised when the user's subscription is not active."""

    def __init__(self):
        self.status_code = 403
        self.detail = "Your subscription is not active. Please reactivate your plan."
        super().__init__(self.detail)


class PlanLimitReachedError(Exception):
    """Raised when the user has reached a numeric plan limit."""

    def __init__(self, limit_key: str, max_allowed: int):
        self.status_code = 403
        self.limit_key = limit_key
        self.max_allowed = max_allowed
        self.detail = (
            f"Plan limit reached for '{limit_key}' ({max_allowed}). "
            "Please upgrade your plan for more."
        )
        super().__init__(self.detail)
