/**
 * Currency utilities for Satta Ledger frontend.
 *
 * Provides:
 *   - formatCurrency() — format amounts with proper currency symbol
 *   - convertAmount() — convert between currencies using cached rates
 *   - Currency symbol + metadata lookup (from base backend)
 *   - Rate caching from auth/me exchange_rates
 *
 * Single Source of Truth:
 *   - Currency metadata (symbol, name, decimal_digits) comes from the
 *     Sattabase base backend via the `currencies` field on auth/me.
 *   - This module does NOT hardcode any currency symbols.
 *   - If no metadata is cached, it falls back to Intl.NumberFormat for
 *     symbol resolution and defaults to 2 decimal digits.
 *
 * Architecture:
 *   - Exchange rates come piggybacked on the /billing/auth/me response
 *     (the exchange_rates field, populated when X-Service-Domain is present)
 *   - Currency metadata comes piggybacked on the /billing/auth/me response
 *     (the currencies field, populated when X-Service-Domain is present)
 *   - Rates are cached in sessionStorage for the session lifetime
 *   - Currency metadata is cached in localStorage (persists across sessions,
 *     changes very rarely)
 *   - For specific pair lookups, the /billing/exchange-rates API can be called
 *   - For currency metadata, the /billing/currencies API can be called
 */

import type { AuthMeResponse } from "./types";

// ─── Storage Keys ───────────────────────────────────────────────────────────

const RATES_CACHE_KEY = "sattabase-ledger:exchange_rates";
const BASE_CURRENCY_KEY = "sattabase-ledger:base_currency";
const CURRENCIES_META_KEY = "sattabase-ledger:currencies_meta";

// ─── Types ──────────────────────────────────────────────────────────────────

interface CurrencyMetaEntry {
  symbol: string;
  name: string;
  decimal_digits: number;
}

type CurrenciesMeta = Record<string, CurrencyMetaEntry>;

// ─── Currency Metadata (from base backend) ──────────────────────────────────

/**
 * Cache currency metadata received from auth/me piggyback.
 * Called automatically by useAuth after fetching auth/me.
 *
 * Stores in localStorage since currency metadata changes very rarely
 * (unlike exchange rates which change daily).
 */
export function cacheCurrenciesMeta(currencies: Record<string, unknown> | null | undefined): void {
  if (typeof window === "undefined" || !currencies) return;

  try {
    localStorage.setItem(CURRENCIES_META_KEY, JSON.stringify(currencies));
  } catch {
    // localStorage full or unavailable
  }
}

/**
 * Get cached currency metadata.
 * Falls back to null if not cached.
 */
function getCurrenciesMeta(): CurrenciesMeta | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = localStorage.getItem(CURRENCIES_META_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as CurrenciesMeta;
  } catch {
    return null;
  }
}

/**
 * Get metadata for a specific currency.
 * Returns null if no metadata is cached for that currency.
 */
function getCurrencyMeta(currencyCode: string): CurrencyMetaEntry | null {
  const meta = getCurrenciesMeta();
  if (!meta) return null;
  return meta[currencyCode.toUpperCase()] ?? null;
}

// ─── Public API: Symbol & Formatting ────────────────────────────────────────

/**
 * Get the display symbol for a currency code.
 *
 * Uses cached metadata from the base backend (single source of truth).
 * Falls back to Intl.NumberFormat symbol resolution, then the currency
 * code itself.
 */
export function getCurrencySymbol(currencyCode: string): string {
  // 1. Try cached metadata from base backend
  const meta = getCurrencyMeta(currencyCode);
  if (meta?.symbol) return meta.symbol;

  // 2. Try Intl.NumberFormat for browser-native symbol resolution
  try {
    const parts = new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currencyCode,
      currencyDisplay: "narrowSymbol",
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).formatToParts(0);
    const symbolPart = parts.find((p) => p.type === "currency");
    if (symbolPart?.value && symbolPart.value !== currencyCode) {
      return symbolPart.value;
    }
  } catch {
    // Intl doesn't know this currency
  }

  // 3. Fallback to currency code
  return currencyCode.toUpperCase();
}

/**
 * Get the number of decimal digits for a currency.
 *
 * Uses cached metadata from the base backend.
 * Falls back to 2 for unknown currencies.
 */
export function getCurrencyDecimalDigits(currencyCode: string): number {
  const meta = getCurrencyMeta(currencyCode);
  if (meta && typeof meta.decimal_digits === "number") {
    return meta.decimal_digits;
  }
  return 2;
}

/**
 * Get the human-readable name for a currency.
 *
 * Uses cached metadata from the base backend.
 * Falls back to the currency code.
 */
export function getCurrencyName(currencyCode: string): string {
  const meta = getCurrencyMeta(currencyCode);
  if (meta?.name) return meta.name;
  return currencyCode.toUpperCase();
}

/**
 * Format a numeric amount with the appropriate currency symbol.
 *
 * Uses currency metadata from the base backend for symbol and
 * decimal digits. Falls back to Intl.NumberFormat if no metadata
 * is cached.
 *
 * @param amount - The numeric amount (major units, e.g. 10985.00)
 * @param currencyCode - ISO 4217 currency code (e.g. "BDT")
 * @param options - Formatting options
 * @returns Formatted string, e.g. "৳10,985.00"
 */
export function formatCurrency(
  amount: number | string,
  currencyCode: string,
  options: {
    /** Include the ISO code after the symbol (e.g. "৳10,985.00 BDT") */
    includeCode?: boolean;
    /** Show "N/A" when amount is null/undefined */
    showNA?: boolean;
  } = {},
): string {
  const { includeCode = false, showNA = false } = options;

  if (amount === null || amount === undefined || amount === "") {
    return showNA ? "N/A" : `${getCurrencySymbol(currencyCode)}0.00`;
  }

  const num = typeof amount === "string" ? parseFloat(amount) : amount;

  if (isNaN(num)) {
    return showNA ? "N/A" : `${getCurrencySymbol(currencyCode)}0.00`;
  }

  const symbol = getCurrencySymbol(currencyCode);
  const code = currencyCode.toUpperCase();
  const decimalDigits = getCurrencyDecimalDigits(code);

  let formatted: string;

  if (decimalDigits === 0) {
    formatted = Math.round(num).toLocaleString("en-US");
  } else {
    formatted = num.toLocaleString("en-US", {
      minimumFractionDigits: decimalDigits,
      maximumFractionDigits: decimalDigits,
    });
  }

  let result = `${symbol}${formatted}`;

  if (includeCode) {
    result = `${result} ${code}`;
  }

  return result;
}

// ─── Currency Conversion ────────────────────────────────────────────────────

/**
 * Convert an amount from one currency to another using cached rates.
 *
 * @param amount - Amount in the source currency
 * @param fromCurrency - Source ISO 4217 code
 * @param toCurrency - Target ISO 4217 code
 * @returns Converted amount, or null if rate is unavailable
 */
export function convertAmount(
  amount: number,
  fromCurrency: string,
  toCurrency: string,
): number | null {
  const from = fromCurrency.toUpperCase();
  const to = toCurrency.toUpperCase();

  if (from === to) return amount;

  const rates = getCachedRates(from);

  if (rates && rates[to]) {
    const rate = parseFloat(rates[to]);
    if (!isNaN(rate)) {
      return amount * rate;
    }
  }

  // Try reverse
  const reverseRates = getCachedRates(to);
  if (reverseRates && reverseRates[from]) {
    const reverseRate = parseFloat(reverseRates[from]);
    if (!isNaN(reverseRate) && reverseRate > 0) {
      return amount / reverseRate;
    }
  }

  return null;
}

// ─── Rate Caching ───────────────────────────────────────────────────────────

/**
 * Store exchange rates from auth/me response into cache.
 * Called automatically by useAuth after fetching auth/me.
 */
export function cacheExchangeRates(authMeResponse: AuthMeResponse): void {
  if (typeof window === "undefined") return;

  const { exchange_rates, user } = authMeResponse;

  if (exchange_rates && user?.currency) {
    try {
      sessionStorage.setItem(
        RATES_CACHE_KEY,
        JSON.stringify({
          base: user.currency,
          rates: exchange_rates,
          cachedAt: Date.now(),
        }),
      );
      sessionStorage.setItem(BASE_CURRENCY_KEY, user.currency);
    } catch {
      // sessionStorage full or unavailable
    }
  }
}

/**
 * Get cached exchange rates for a base currency.
 */
export function getCachedRates(baseCurrency?: string): Record<string, string> | null {
  if (typeof window === "undefined") return null;

  try {
    const stored = sessionStorage.getItem(RATES_CACHE_KEY);
    if (!stored) return null;

    const parsed = JSON.parse(stored) as {
      base: string;
      rates: Record<string, string>;
      cachedAt: number;
    };

    // If a specific base is requested, check it matches
    if (baseCurrency && parsed.base !== baseCurrency.toUpperCase()) {
      return null;
    }

    return parsed.rates;
  } catch {
    return null;
  }
}

/**
 * Get the user's base currency from cache.
 */
export function getBaseCurrency(): string {
  if (typeof window === "undefined") return "USD";
  return sessionStorage.getItem(BASE_CURRENCY_KEY) || "USD";
}

/**
 * Clear all cached currency data (on logout).
 */
export function clearExchangeRates(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(RATES_CACHE_KEY);
    sessionStorage.removeItem(BASE_CURRENCY_KEY);
    // NOTE: We intentionally do NOT clear localStorage currencies_meta
    // on logout. Currency metadata is stable across sessions and rarely
    // changes. Clearing it would cause an unnecessary re-fetch.
  } catch {
    // ignore
  }
}

/**
 * Clear currency metadata cache.
 * Use only if the data is stale or corrupted.
 */
export function clearCurrenciesMeta(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(CURRENCIES_META_KEY);
  } catch {
    // ignore
  }
}
