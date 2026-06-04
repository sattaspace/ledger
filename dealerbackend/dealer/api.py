"""
DEALERCORE v3.0 — Dealer API Router
--------------------------------------
Django Ninja async endpoints for dealer configuration.

Endpoints:
  GET  /api/dealers   → list all dealer configs
  POST /api/dealers/update → update dealer settings
"""

from ninja import Router

from dealer.models import DealerConfig
from dealer.schemas import DealerConfigOut, UpdateDealerIn

router = Router(tags=["Dealer"])


@router.get("", response=list[DealerConfigOut], summary="List dealer configs")
async def list_dealers(request):
    """Return all dealer configurations."""
    return list(DealerConfig.objects.all())


@router.post("update", response=DealerConfigOut, summary="Update dealer settings")
async def update_dealer_settings(request, payload: UpdateDealerIn):
    """Update a dealer's currency and locale settings.
    `username` is the lookup key."""
    dealer = await DealerConfig.objects.aget(username=payload.username)
    dealer.default_currency = payload.default_currency
    dealer.default_locale = payload.default_locale
    await dealer.asave()
    return dealer
