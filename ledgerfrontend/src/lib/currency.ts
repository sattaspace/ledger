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
 * Display modes (`displayMode` option):
 *   - `'auto'` (default): If the currency matches the base currency, show
 *     symbol only (e.g. "$1,250.00"). If different from base, show symbol +
 *     code (e.g. "€89.50 EUR"). Unknown currencies (where symbol === code)
 *     always show the code with a space (e.g. "XYZ 100.00").
 *   - `'symbol'`: Always show symbol only — preserves the previous default
 *     behavior for backward compatibility (e.g. "€89.50").
 *   - `'code'`: Always show the currency code after the amount
 *     (e.g. "€89.50 EUR").
 *
 * The legacy `includeCode` option is still supported: when true, it forces
 * the code to appear after the amount regardless of `displayMode`.
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
    /**
     * Display mode for currency symbol/code:
     *   - `'auto'` (default): symbol only for base currency, symbol + code for non-base
     *   - `'symbol'`: always symbol only (backward compat)
     *   - `'code'`: always include currency code after amount
     */
    displayMode?: "auto" | "symbol" | "code";
  } = {},
): string {
  const { includeCode = false, showNA = false, displayMode = "auto" } = options;

  const symbol = getCurrencySymbol(currencyCode);
  const code = currencyCode.toUpperCase();
  const decimalDigits = getCurrencyDecimalDigits(code);

  // Determine whether the symbol is unknown (falls back to the code itself)
  const isUnknownCurrency = symbol === code;

  if (amount === null || amount === undefined || amount === "") {
    if (showNA) return "N/A";
    const zeroFormatted = decimalDigits === 0 ? "0" : `0.${"0".repeat(decimalDigits)}`;
    return buildResult(symbol, code, zeroFormatted, isUnknownCurrency, displayMode, includeCode);
  }

  const num = typeof amount === "string" ? parseFloat(amount) : amount;

  if (isNaN(num)) {
    if (showNA) return "N/A";
    const zeroFormatted = decimalDigits === 0 ? "0" : `0.${"0".repeat(decimalDigits)}`;
    return buildResult(symbol, code, zeroFormatted, isUnknownCurrency, displayMode, includeCode);
  }

  let formatted: string;

  if (decimalDigits === 0) {
    formatted = Math.round(num).toLocaleString("en-US");
  } else {
    formatted = num.toLocaleString("en-US", {
      minimumFractionDigits: decimalDigits,
      maximumFractionDigits: decimalDigits,
    });
  }

  return buildResult(symbol, code, formatted, isUnknownCurrency, displayMode, includeCode);
}

/**
 * Internal helper that assembles the final formatted string based on
 * displayMode, unknown-currency detection, and the legacy includeCode flag.
 */
function buildResult(
  symbol: string,
  code: string,
  formattedAmount: string,
  isUnknownCurrency: boolean,
  displayMode: "auto" | "symbol" | "code",
  includeCode: boolean,
): string {
  const baseCurrency = getBaseCurrency().toUpperCase();
  const isBase = code === baseCurrency;

  // For unknown currencies (symbol === code), add a space separator
  // e.g. "XYZ 100.00" instead of "XYZ100.00"
  const separator = isUnknownCurrency ? " " : "";
  let result = `${symbol}${separator}${formattedAmount}`;

  // Determine whether to append the currency code based on displayMode
  let shouldAppendCode = false;

  if (displayMode === "code") {
    // 'code' mode always shows the code
    shouldAppendCode = true;
  } else if (displayMode === "auto") {
    // 'auto' mode: show code for non-base currencies or unknown currencies
    if (!isBase || isUnknownCurrency) {
      shouldAppendCode = true;
    }
  }
  // 'symbol' mode never appends the code (unless includeCode is set)

  // Legacy includeCode overrides the displayMode decision
  if (includeCode) {
    shouldAppendCode = true;
  }

  if (shouldAppendCode) {
    result = `${result} ${code}`;
  }

  return result;
}

// ─── Transaction Amount Display ─────────────────────────────────────────────

/**
 * Format a transaction amount showing original currency, base equivalent,
 * and exchange rate.
 *
 * For foreign currency transactions where currency_original !== base currency.
 *
 * Example output: "€89.50 EUR (~$97.23 @ 1.0864)"
 * If same as base currency, just returns the formatted amount: "$97.23"
 *
 * @param amountOriginal - Original transaction amount
 * @param currencyOriginal - Original currency code
 * @param amountBase - Amount converted to base currency
 * @param exchangeRate - Exchange rate used for conversion
 * @returns Formatted string with original, base equivalent, and rate
 */
export function formatTransactionAmount(
  amountOriginal: number | string,
  currencyOriginal: string,
  amountBase?: number | string | null,
  exchangeRate?: number | string | null,
): string {
  const baseCurrency = getBaseCurrency();
  const originalCode = currencyOriginal.toUpperCase();

  // If same as base currency, just return the formatted amount
  if (originalCode === baseCurrency.toUpperCase()) {
    return formatCurrency(amountOriginal, currencyOriginal);
  }

  // Format the original amount (non-base currency)
  const originalFormatted = formatCurrency(amountOriginal, currencyOriginal);

  // If base amount or rate is missing, just return the original formatted amount
  if (amountBase == null || exchangeRate == null) {
    return originalFormatted;
  }

  const rateNum = typeof exchangeRate === "string" ? parseFloat(exchangeRate) : exchangeRate;
  if (isNaN(rateNum)) {
    return originalFormatted;
  }

  // Format the base equivalent with symbol-only display (it's the user's base)
  const baseFormatted = formatCurrency(amountBase, baseCurrency, { displayMode: "symbol" });

  // Show rate to 4 decimal places
  const rateFormatted = rateNum.toFixed(4);

  return `${originalFormatted} (~${baseFormatted} @ ${rateFormatted})`;
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
