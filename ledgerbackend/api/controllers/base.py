"""Base controller for all Ledger domain controllers.

Provides:
    - Auth helper: require_user_id() — extracts Sattabase user_id, 401 or 503
    - Auth helper: AuthServiceUnavailableError — 503 when auth service is down
    - Feature gate: require_feature() — checks access map for feature boolean
    - Subscription: require_subscription_active() — checks subscription status
    - Plan limit: check_plan_limit() — enforces numeric record limits
    - Retention: get_retention_cutoff() — returns date cutoff for data_retention_days
    - API access: require_api_access() — gates external API access
    - FK ownership: validate_fk_ownership() — ensures FK targets belong to the user
    - Object lookup: get_or_404() — scoped by user_id, excludes soft-deleted
    - Object lookup: get_with_deleted_or_404() — includes soft-deleted (for restore)
    - Pagination: paginate() — consistent paginated list responses
    - Filter application: apply_filters() — common filter logic
    - Update helper: update_object() — with protected field guard
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
        """Extract user_id or return a 401/503 response.

        Use this at the top of every endpoint that requires authentication.

        Returns 503 (AuthServiceUnavailableError) when the auth service is
        unreachable — the user provided a token but we can't verify it.
        Returns 401 (AuthRequiredError) when the user is not authenticated
        (no token, invalid token, or expired token).

        As a side effect, caches the user's base currency (from
        request.sattabase_user.currency) so that model methods like
        Transaction._convert_to_base_currency() can look it up without
        needing the request object.
        """
        user_id = self.get_user_id(request)
        if user_id is None:
            # Check if the auth service is unavailable (set by
            # AuthServiceUnavailableMiddleware after the SDK middleware)
            if getattr(request, "sattabase_auth_unavailable", False):
                raise AuthServiceUnavailableError()
            raise AuthRequiredError()

        # Cache user's base currency for model-level currency conversion
        user = getattr(request, "sattabase_user", None)
        if user and hasattr(user, "currency") and user.currency:
            from api.currency import cache_user_base_currency
            cache_user_base_currency(user_id, user.currency)

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

    # ── FK ownership validation ────────────────────────────────────────────

    # Fields that must NEVER be overwritten via update_object().
    # Prevents a misconfigured schema from allowing a client to change
    # user_id, id, or audit timestamps on an existing record.
    PROTECTED_FIELDS = frozenset({
        "user_id", "id", "created_at", "updated_at",
        "deleted_at", "is_deleted", "activated_at",
    })

    def validate_fk_ownership(self, request, model_class: Type, fk_id: int | None):
        """Validate that a FK target belongs to the current user, or raise 404.

        Returns the resolved object if it exists and belongs to the user.
        Returns None if fk_id is None (optional FK).
        Raises Http404 if the object doesn't exist or belongs to another user.

        Usage in create/update endpoints:
            account = self.validate_fk_ownership(request, Account, payload.account_id)
            category = self.validate_fk_ownership(request, Category, payload.category_id)
        """
        if fk_id is None:
            return None
        user_id = self.require_user_id(request)
        return self.get_or_404(model_class, user_id, fk_id)

    # ── Update helper ─────────────────────────────────────────────────────

    def update_object(self, obj, payload, *, fk_map: dict | None = None) -> None:
        """Apply update schema fields to an object (only provided fields).

        Handles FK field naming: institution_id in schema → institution_id on model.

        Protected fields (user_id, id, created_at, etc.) are silently stripped
        from the update data to prevent accidental or malicious overwrites.

        Args:
            obj: The model instance to update.
            payload: The Pydantic schema with update fields.
            fk_map: Optional dict mapping FK field names to (model_class, request)
                    tuples for ownership validation.  Example:
                        {
                            "institution_id": (Institution, request),
                            "account_id": (Account, request),
                        }
                    When provided, each non-None FK value is validated with
                    validate_fk_ownership() before being applied.
        """
        update_data = payload.model_dump(exclude_unset=True)

        # Strip protected fields — never allow client to overwrite these
        for field in self.PROTECTED_FIELDS:
            update_data.pop(field, None)

        # Validate FK ownership if a mapping was provided
        if fk_map:
            for fk_field, (model_class, req) in fk_map.items():
                fk_value = update_data.get(fk_field)
                if fk_value is not None:
                    # Will raise Http404 if the FK target doesn't belong to user
                    self.validate_fk_ownership(req, model_class, fk_value)

        for field, value in update_data.items():
            setattr(obj, field, value)
        obj.save()


class FkOwnershipError(Exception):
    """Raised when a FK reference does not belong to the current user."""

    def __init__(self, model_name: str, fk_id: int):
        self.status_code = 400
        self.detail = f"{model_name} with id={fk_id} not found or does not belong to you."
        super().__init__(self.detail)


class AuthRequiredError(Exception):
    """Raised when Sattabase auth is required but not present (401)."""

    def __init__(self):
        self.status_code = 401
        self.detail = "Authentication required via Sattabase."
        super().__init__(self.detail)


class AuthServiceUnavailableError(Exception):
    """Raised when the Sattabase auth service is unreachable (503).

    This is distinct from AuthRequiredError (401). When the user provides
    a valid-looking JWT but the base backend is down, we return 503 instead
    of 401 so the client can distinguish between "not authenticated" and
    "auth service temporarily unavailable".
    """

    def __init__(self):
        self.status_code = 503
        self.detail = (
            "Authentication service is temporarily unavailable. "
            "Please try again in a few moments."
        )
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
