"""Currency utilities for the Ledger sister domain.

Provides:
  - Exchange rate caching from the Sattabase base backend
  - Currency metadata caching (symbol, name, decimal_digits) from base backend
  - Currency conversion with stored rates (for transaction-time capture)
  - format_currency() helper for consistent display

Architecture:
  - Exchange rates are fetched from Sattabase's /billing/exchange-rates endpoint
  - Currency metadata is fetched from Sattabase's /billing/currencies endpoint
  - Both are cached in Django's cache backend (Redis) with configurable TTL
  - Transaction creation should call convert_amount() to get the rate at that moment
  - The rate is stored alongside the transaction for historical accuracy
  - Dashboard can also show "current value" using the latest cached rates

Single Source of Truth:
  - All currency metadata (symbol, name, decimal_digits) comes from the
    Sattabase base backend. This module does NOT hardcode any currency
    symbols. The /billing/currencies endpoint and the `currencies` field
    on auth/me are the canonical sources.
  - If the cache is empty and the API is unreachable, a minimal fallback
    is used (currency code as symbol, 2 decimal digits).

Rate source priority:
  1. Redis cache (fast, TTL-based)
  2. Sattabase /billing/exchange-rates API (on cache miss)
"""

import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Configuration
# =============================================================================

RATES_CACHE_KEY_PREFIX = "ledger:exchange_rates"
CURRENCIES_CACHE_KEY = "ledger:currencies_meta"
RATES_CACHE_TTL_SECONDS = getattr(settings, "EXCHANGE_RATE_CACHE_TTL", 6 * 60 * 60)  # 6 hours
CURRENCIES_CACHE_TTL_SECONDS = getattr(settings, "CURRENCY_META_CACHE_TTL", 24 * 60 * 60)  # 24 hours


# =============================================================================
# Currency Metadata — Fetched from Base Backend (NOT hardcoded)
# =============================================================================


def _fetch_and_cache_currencies() -> dict[str, dict]:
    """Fetch currency metadata from Sattabase's /billing/currencies endpoint.

    Returns:
        dict mapping ISO code → {"symbol": ..., "name": ..., "decimal_digits": ...}

    Raises:
        Exception if the Sattabase API call fails.
    """
    import httpx

    base_url = getattr(settings, "SATTABASE_BASE_URL", "http://localhost:8000/api/v1")
    api_key = getattr(settings, "SATTABASE_API_KEY", "")
    service_domain = getattr(settings, "SATTABASE_SERVICE_DOMAIN", "")

    url = f"{base_url}/billing/currencies"
    headers = {
        "Accept": "application/json",
        "User-Agent": "SattaLedger/1.0",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    if service_domain:
        headers["X-Service-Domain"] = service_domain

    timeout = getattr(settings, "SATTABASE_AUTH_TIMEOUT", 5)

    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    currencies = data.get("currencies", {})

    # Cache the result
    cache.set(CURRENCIES_CACHE_KEY, currencies, CURRENCIES_CACHE_TTL_SECONDS)

    logger.info("Fetched and cached %d currency metadata entries", len(currencies))

    return currencies


def get_currencies_meta() -> dict[str, dict]:
    """Get currency metadata from cache, fetching from API on cache miss.

    Returns:
        dict mapping ISO code → {"symbol": ..., "name": ..., "decimal_digits": ...}
        Empty dict if metadata is unavailable.
    """
    # Try cache first
    meta = cache.get(CURRENCIES_CACHE_KEY)
    if meta is not None:
        return meta

    # Cache miss — fetch from API
    try:
        return _fetch_and_cache_currencies()
    except Exception as e:
        logger.error("Failed to fetch currency metadata: %s", e)
        return {}


def cache_currencies_from_auth_me(currencies: dict) -> None:
    """Cache currency metadata received from auth/me piggyback.

    Called by middleware or the /me endpoint when currencies are included
    in the auth/me response. This avoids a separate /billing/currencies
    API call.
    """
    if currencies and isinstance(currencies, dict):
        cache.set(CURRENCIES_CACHE_KEY, currencies, CURRENCIES_CACHE_TTL_SECONDS)
        logger.debug("Cached currency metadata from auth/me (%d currencies)", len(currencies))


def get_currency_symbol(currency_code: str) -> str:
    """Get the display symbol for a currency code.

    Uses cached metadata from the base backend.
    Falls back to the currency code itself if no meta is available.
    """
    meta = get_currencies_meta()
    entry = meta.get(currency_code.upper())
    if entry and isinstance(entry, dict):
        return entry.get("symbol", currency_code.upper())
    return currency_code.upper()


def get_currency_name(currency_code: str) -> str:
    """Get the human-readable name for a currency code.

    Falls back to the currency code if no meta is available.
    """
    meta = get_currencies_meta()
    entry = meta.get(currency_code.upper())
    if entry and isinstance(entry, dict):
        return entry.get("name", currency_code.upper())
    return currency_code.upper()


def get_currency_decimal_digits(currency_code: str) -> int:
    """Get the number of decimal places for a currency.

    Returns 2 as a safe default for unknown currencies.
    """
    meta = get_currencies_meta()
    entry = meta.get(currency_code.upper())
    if entry and isinstance(entry, dict):
        return int(entry.get("decimal_digits", 2))
    return 2


# =============================================================================
# Rate Fetching & Caching
# =============================================================================


def _rates_cache_key(base_currency: str) -> str:
    """Build the cache key for a given base currency."""
    return f"{RATES_CACHE_KEY_PREFIX}:{base_currency.upper()}"


def fetch_and_cache_rates(base_currency: str = "USD") -> dict[str, str]:
    """Fetch exchange rates from Sattabase and cache them in Redis.

    Returns:
        dict mapping target_currency → rate string,
        e.g. {"USD": "1.000000", "EUR": "0.920000", "BDT": "109.850000"}

    Raises:
        Exception if the Sattabase API call fails.
    """
    import httpx

    base = base_currency.upper()
    base_url = getattr(settings, "SATTABASE_BASE_URL", "http://localhost:8000/api/v1")
    api_key = getattr(settings, "SATTABASE_API_KEY", "")
    service_domain = getattr(settings, "SATTABASE_SERVICE_DOMAIN", "")

    url = f"{base_url}/billing/exchange-rates?base={base}"
    headers = {
        "Accept": "application/json",
        "User-Agent": "SattaLedger/1.0",
    }
    if api_key:
        headers["X-API-Key"] = api_key
    if service_domain:
        headers["X-Service-Domain"] = service_domain

    timeout = getattr(settings, "SATTABASE_AUTH_TIMEOUT", 5)

    with httpx.Client(timeout=timeout) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

    rates = data.get("rates", {})

    # Cache the result
    cache.set(_rates_cache_key(base), rates, RATES_CACHE_TTL_SECONDS)

    logger.info(
        "Fetched and cached %d exchange rates for base=%s",
        len(rates), base,
    )

    return rates


def get_cached_rates(base_currency: str = "USD") -> dict[str, str]:
    """Get exchange rates from cache, fetching from API on cache miss.

    Returns:
        dict mapping target_currency → rate string.
        Empty dict if rates are unavailable.
    """
    base = base_currency.upper()

    # Try cache first
    rates = cache.get(_rates_cache_key(base))
    if rates is not None:
        return rates

    # Cache miss — fetch from API
    try:
        return fetch_and_cache_rates(base)
    except Exception as e:
        logger.error("Failed to fetch exchange rates for %s: %s", base, e)
        return {}


def get_rate(from_currency: str, to_currency: str) -> Optional[Decimal]:
    """Get the exchange rate between two currencies.

    Uses cached rates, falling back to API fetch on cache miss.
    Handles same-currency and cross-rate computation.

    Returns:
        Decimal rate (1 from_currency = ? to_currency), or None if unavailable.
    """
    from_code = from_currency.upper()
    to_code = to_currency.upper()

    # Same currency
    if from_code == to_code:
        return Decimal("1.0")

    # Direct lookup: from → all targets
    rates = get_cached_rates(from_code)
    if to_code in rates:
        try:
            return Decimal(rates[to_code])
        except (InvalidOperation, ValueError):
            pass

    # Reverse lookup: to → all targets (invert)
    rates_reverse = get_cached_rates(to_code)
    if from_code in rates_reverse:
        try:
            reverse_rate = Decimal(rates_reverse[from_code])
            if reverse_rate > 0:
                return Decimal("1") / reverse_rate
        except (InvalidOperation, ValueError, ZeroDivisionError):
            pass

    # Cross rate: from → USD → to
    system_base = "USD"
    if from_code != system_base and to_code != system_base:
        rate_from = get_rate(from_code, system_base)
        rate_to = get_rate(system_base, to_code)
        if rate_from is not None and rate_to is not None:
            return rate_from * rate_to

    return None


# =============================================================================
# Currency Conversion
# =============================================================================


def convert_amount(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Convert an amount from one currency to another.

    This is the core function for the "store rate at transaction time" pattern.
    Call this when creating a transaction to get both the rate and the
    converted amount, then store both alongside the transaction.

    Args:
        amount: The original amount in from_currency (major units, e.g. 100.00)
        from_currency: ISO 4217 source currency code
        to_currency: ISO 4217 target currency code (typically user's base currency)

    Returns:
        (converted_amount, exchange_rate) — both as Decimal, or (None, None)
        if no rate is available.

    Example:
        >>> converted, rate = convert_amount(Decimal("100.00"), "USD", "BDT")
        >>> # converted = Decimal("10985.00"), rate = Decimal("109.850000")
        >>> # Store both in the transaction row
    """
    rate = get_rate(from_currency, to_currency)
    if rate is None:
        return None, None

    decimal_digits = get_currency_decimal_digits(to_currency)
    quantize_str = "1" if decimal_digits == 0 else f"0.{'0' * decimal_digits}"

    converted = (amount * rate).quantize(
        Decimal(quantize_str),
        rounding=ROUND_HALF_UP,
    )
    return converted, rate


def get_current_value(
    original_amount: Decimal,
    original_currency: str,
    base_currency: str,
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Get the current value of an amount in the user's base currency.

    Used for the "current value" display alongside historical amounts.
    This uses the latest cached rate (which may differ from the rate stored
    with the transaction).

    Args:
        original_amount: Amount in the original currency
        original_currency: Original transaction currency
        base_currency: User's base currency

    Returns:
        (current_value, current_rate) — both as Decimal, or (None, None)
    """
    return convert_amount(original_amount, original_currency, base_currency)


# =============================================================================
# Display Helpers
# =============================================================================


def format_currency(
    amount: Decimal | float | int,
    currency_code: str,
    include_code: bool = False,
) -> str:
    """Format an amount with the appropriate currency symbol.

    Uses currency metadata from the base backend (cached locally).

    Args:
        amount: The numeric amount (major units, e.g. 10985.00)
        currency_code: ISO 4217 currency code (e.g. "BDT")
        include_code: If True, append the ISO code (e.g. "৳10,985.00 BDT")

    Returns:
        Formatted string, e.g. "৳10,985.00" or "$100.00 USD"
    """
    symbol = get_currency_symbol(currency_code)
    decimal_digits = get_currency_decimal_digits(currency_code)

    # Format with thousands separator and proper decimal places
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))

    formatted = f"{amount:,.{decimal_digits}f}"

    result = f"{symbol}{formatted}"

    if include_code:
        result = f"{result} {currency_code.upper()}"

    return result
