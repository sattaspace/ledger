"""
DEALERCORE v3.0 — Dealer API Controller
-----------------------------------------
Class-based controller using django-ninja-extra.

IMPORTANT: Literal paths (e.g. "update") MUST be registered BEFORE
parameterized paths (e.g. "{username}") to avoid route conflicts.
Django Ninja matches URL patterns first, then checks HTTP method.

Endpoints:
  GET  /api/dealers              → list all dealer configs
  POST /api/dealers              → create a new dealer config
  POST /api/dealers/update       → update dealer settings
  GET  /api/dealers/{username}   → get a single dealer config

GAP E-3 fix: All endpoints now require dealer-only access. DSRs cannot
read or modify dealer configurations. The create_dealer endpoint is
additionally restricted to internal/service-to-service calls (SattaBase
onboarding) via X-API-Key authentication.
"""

from ninja_extra import api_controller, route
from ninja.errors import HttpError

from dealer.models import DealerConfig
from dealer.schemas import DealerConfigOut, UpdateDealerIn, CreateDealerIn


async def _require_dealer_only(request):
    """GAP E-3 fix: reject DSR JWTs on dealer-config endpoints.

    Dealer configuration is dealer-only data — DSRs should not be able
    to read other dealers' configs or modify any dealer's settings.

    The PermissionMiddleware already extracts is_dealer / is_dsr flags
    from the JWT and attaches them to the request object. We use those
    instead of re-decoding the JWT.

    Internal API-key calls (SattaBase onboarding) have no JWT, so
    is_dealer/is_dsr are both False. We allow those if X-API-Key is
    present.
    """
    # Check if this is an internal service-to-service call (SattaBase onboarding)
    api_key = (
        getattr(request, "META", {}).get("HTTP_X_API_KEY")
        or request.headers.get("X-API-Key")
    )
    is_dealer = getattr(request, "is_dealer", False)
    is_dsr = getattr(request, "is_dsr", False)

    if is_dsr and not is_dealer:
        # DSR JWT — reject
        raise HttpError(403, "Dealer access required. DSRs cannot access dealer configurations.")

    if not is_dealer and not api_key:
        # No JWT and no API key — reject
        raise HttpError(403, "Dealer access required. Please login as a dealer.")

    # is_dealer=True OR api_key present → allow


@api_controller("/dealers", tags=["Dealer"])
class DealerController:
    # Maximum records per page to prevent memory exhaustion
    MAX_PAGE_LIMIT = 100

    def _validate_pagination(self, limit: int, offset: int) -> None:
        """Common pagination validation to prevent memory exhaustion."""
        if limit > self.MAX_PAGE_LIMIT:
            raise HttpError(400, f"Limit cannot exceed {self.MAX_PAGE_LIMIT}. Use pagination with offset.")
        if limit < 1:
            raise HttpError(400, "Limit must be at least 1.")
        if offset < 0:
            raise HttpError(400, "Offset cannot be negative.")

    @route.get("", response=list[DealerConfigOut], summary="List dealer configs")
    async def list_dealers(self, request, limit: int = 100, offset: int = 0):
        """Return all dealer configurations.

        GAP E-3 fix: dealer-only access. DSRs are rejected.

        Query Parameters:
            limit: Max records to return (default: 100, max: 100)
            offset: Number of records to skip (for pagination)
        """
        await _require_dealer_only(request)
        self._validate_pagination(limit, offset)
        return [d async for d in DealerConfig.objects.all().order_by("username")[offset:offset+limit]]

    @route.post("", response=DealerConfigOut, summary="Create a new dealer")
    async def create_dealer(self, request, payload: CreateDealerIn):
        """Create a new dealer configuration.

        GAP E-3 fix: restricted to internal/service-to-service calls
        (SattaBase onboarding) or dealer admin. DSRs are rejected.
        """
        await _require_dealer_only(request)
        try:
            dealer = await DealerConfig.objects.aget(username=payload.username)
            raise HttpError(409, f"Dealer with username '{payload.username}' already exists")
        except DealerConfig.DoesNotExist:
            pass
        dealer = await DealerConfig.objects.acreate(
            username=payload.username,
            full_name=payload.full_name,
            role=payload.role,
            business_name=payload.business_name,
            address=payload.address,
            phone_number=payload.phone_number,
            email=payload.email,
            gst_number=payload.gst_number,
            google_map_url=payload.google_map_url,
            communication_number=payload.communication_number,
            default_currency=payload.default_currency,
            default_locale=payload.default_locale,
        )
        return dealer

    @route.post("update", response=DealerConfigOut, summary="Update dealer settings")
    async def update_dealer_settings(self, request, payload: UpdateDealerIn):
        """Update a dealer's settings.

        GAP E-3 fix: dealer-only access. DSRs are rejected.
        `username` is the lookup key. Only provided fields are updated."""
        await _require_dealer_only(request)
        try:
            dealer = await DealerConfig.objects.aget(username=payload.username)
        except DealerConfig.DoesNotExist:
            raise HttpError(404, f"Dealer with username '{payload.username}' not found")

        update_data = payload.model_dump(exclude_unset=True, exclude={"username"})
        for field, value in update_data.items():
            setattr(dealer, field, value)
        await dealer.asave()
        return dealer

    @route.get("{username}", response=DealerConfigOut, summary="Get a dealer config")
    async def get_dealer(self, request, username: str):
        """Return a single dealer configuration by username.

        GAP E-3 fix: dealer-only access. DSRs are rejected.
        """
        await _require_dealer_only(request)
        try:
            return await DealerConfig.objects.aget(username=username)
        except DealerConfig.DoesNotExist:
            raise HttpError(404, f"Dealer with username '{username}' not found")
