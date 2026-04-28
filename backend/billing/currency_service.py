"""Currency conversion service for the billing app.

Handles conversion between plan base currency and user's preferred
currency using exchange rates stored in the ExchangeRate model.

Flow:
  1. Plans are priced in BASE_CURRENCY (default USD).
  2. Exchange rates are fetched daily from a free API by Celery.
  3. When the frontend requests plans with ?currency=BDT, this service
     converts price_cents from the plan's currency to BDT.
  4. The frontend displays the converted price alongside the base price.
"""

import logging
import urllib.request
import json
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any

from django.conf import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Conversion Helpers
# =============================================================================


def get_exchange_rate(
    from_currency: str,
    to_currency: str,
) -> Optional[Decimal]:
    """Look up the exchange rate for a currency pair.

    Handles three cases:
      1. Same currency → returns 1.0 immediately.
      2. Direct pair (e.g. USD→BDT) → looks up in ExchangeRate table.
      3. Cross pair via base (e.g. EUR→BDT via USD) → composes two rates.

    Returns None if no rate is available (e.g. on fresh install before
    the first Celery fetch completes).
    """
    from .models import ExchangeRate

    from_code = from_currency.upper()
    to_code = to_currency.upper()

    # Same currency — no conversion needed
    if from_code == to_code:
        return Decimal("1.0")

    base = getattr(settings, "BASE_CURRENCY", "USD").upper()

    # Direct pair stored in DB (base → target)
    try:
        direct = ExchangeRate.objects.get(
            base_currency=from_code,
            target_currency=to_code,
        )
        return direct.rate
    except ExchangeRate.DoesNotExist:
        pass

    # Reverse pair stored in DB (target → base) — invert the rate
    try:
        reverse = ExchangeRate.objects.get(
            base_currency=to_code,
            target_currency=from_code,
        )
        return Decimal("1") / reverse.rate if reverse.rate > 0 else None
    except ExchangeRate.DoesNotExist:
        pass

    # Cross pair: from → base → to
    if from_code != base and to_code != base:
        rate_from = get_exchange_rate(from_code, base)
        rate_to = get_exchange_rate(base, to_code)
        if rate_from is not None and rate_to is not None:
            return rate_from * rate_to

    return None


def convert_price(
    amount_cents: int,
    from_currency: str,
    to_currency: str,
) -> tuple[Optional[int], Optional[Decimal]]:
    """Convert a price in cents from one currency to another.

    Returns:
        (converted_amount_cents, exchange_rate_used)

    If no rate is available, returns (None, None) so the caller knows
    conversion failed and can fall back to the original price/currency.
    """
    rate = get_exchange_rate(from_currency, to_currency)
    if rate is None:
        return None, None

    # Convert cents → decimal → apply rate → round to cents
    original = Decimal(amount_cents) / Decimal(100)
    converted = (original * rate).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    converted_cents = int(converted * 100)
    return converted_cents, rate


def convert_plan_prices(
    plans: list,
    target_currency: str,
) -> list[dict]:
    """Batch-convert prices for a list of plan objects.

    Takes a list of Plan model instances (or dicts with plan fields)
    and adds converted price fields for the target currency.

    Returns a list of dicts with the following extra keys:
      - converted_price_cents: int or None
      - user_currency: str (the requested target currency)
      - exchange_rate: str or None (the rate used, e.g. "109.850000")

    If no rate is available for a plan's currency → target, the converted
    fields are None and the frontend should fall back to the base price.
    """
    base = getattr(settings, "BASE_CURRENCY", "USD").upper()
    target = target_currency.upper() if target_currency else base

    if target == base:
        # Same as base — no conversion needed
        return [
            {
                **_plan_to_dict(plan),
                "converted_price_cents": _get_price_cents(plan),
                "user_currency": target,
                "exchange_rate": "1.0",
            }
            for plan in plans
        ]

    result = []
    for plan in plans:
        plan_dict = _plan_to_dict(plan)
        price_cents = _get_price_cents(plan)
        plan_currency = _get_plan_currency(plan).upper()

        converted_cents, rate = convert_price(price_cents, plan_currency, target)

        plan_dict["converted_price_cents"] = converted_cents  # None when no rate
        # Only set user_currency when conversion actually succeeded —
        # frontend uses `user_currency ?? plan.currency` to pick the right
        # symbol.  If we blindly set user_currency=target even when the
        # conversion failed, the frontend formats the ORIGINAL price_cents
        # (which are in plan.currency) with the TARGET symbol, e.g. ৳9.00
        # for a $9 plan.
        plan_dict["user_currency"] = target if converted_cents is not None else None
        plan_dict["exchange_rate"] = str(rate) if rate is not None else None

        result.append(plan_dict)

    return result


# =============================================================================
# Rate Fetching (called by Celery)
# =============================================================================


def fetch_exchange_rates() -> Dict[str, Any]:
    """Fetch latest exchange rates from the configured API.

    Uses the free open.er-api.com endpoint (no API key required).
    Returns the full JSON response dict on success, or raises an
    exception on failure.

    The API returns rates relative to the base currency specified in
    the URL path, e.g. /v6/latest/USD returns all rates relative to USD.
    """
    base = getattr(settings, "BASE_CURRENCY", "USD").upper()
    api_url = getattr(
        settings, "EXCHANGE_RATE_API_URL", "https://open.er-api.com/v6/latest"
    )

    url = f"{api_url}/{base}"

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Sattabase/1.0")

    logger.info(f"Fetching exchange rates from {url}")

    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if data.get("result") != "success":
        raise ValueError(
            f"Exchange rate API returned error: {data.get('error-type', 'unknown')}"
        )

    return data


def update_exchange_rates() -> dict:
    """Fetch exchange rates from API and upsert into ExchangeRate table.

    Called by the ``update_exchange_rates`` Celery task (daily).

    Returns:
        {"updated": int, "skipped": int, "base": str}
    """
    from .models import ExchangeRate

    base = getattr(settings, "BASE_CURRENCY", "USD").upper()
    data = fetch_exchange_rates()
    rates = data.get("rates", {})

    if not rates:
        logger.warning("Exchange rate API returned no rates")
        return {"updated": 0, "skipped": 0, "base": base}

    updated = 0
    skipped = 0

    for target_currency, rate_value in rates.items():
        target = target_currency.upper()

        if target == base:
            skipped += 1
            continue

        try:
            rate = Decimal(str(rate_value))
        except (ValueError, TypeError):
            logger.warning(f"Invalid rate for {target}: {rate_value}")
            skipped += 1
            continue

        ExchangeRate.objects.update_or_create(
            base_currency=base,
            target_currency=target,
            defaults={"rate": rate},
        )
        updated += 1

    logger.info(
        f"Exchange rates updated: {updated} updated, {skipped} skipped, base={base}"
    )

    return {"updated": updated, "skipped": skipped, "base": base}


# =============================================================================
# Internal Helpers
# =============================================================================


def _plan_to_dict(plan) -> dict:
    """Convert a Plan model instance to a dict.

    Includes DB columns from ``__dict__`` and computed ``@property``
    fields (``display_price``, ``is_free``) that Pydantic expects
    in ``PlanOutputSchema``.
    """
    if hasattr(plan, "__dict__"):
        d = {k: v for k, v in plan.__dict__.items() if not k.startswith("_")}
        # Include model properties that Pydantic schema requires
        for prop in ("display_price", "is_free"):
            if hasattr(plan, prop):
                d[prop] = getattr(plan, prop)
        return d
    return plan


def _get_price_cents(plan) -> int:
    """Extract price_cents from a Plan model or dict."""
    if isinstance(plan, dict):
        return plan.get("price_cents", 0)
    return getattr(plan, "price_cents", 0)


def _get_plan_currency(plan) -> str:
    """Extract currency from a Plan model or dict."""
    if isinstance(plan, dict):
        return plan.get("currency", getattr(settings, "BASE_CURRENCY", "USD"))
    return getattr(plan, "currency", getattr(settings, "BASE_CURRENCY", "USD"))
