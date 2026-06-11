/**
 * DEALERCORE v3.0 — Shared Formatting Utilities
 *
 * Centralized formatting functions used across components.
 * Provides consistent currency, number, and date formatting.
 */

import { computed, type ComputedRef } from 'vue';

export interface UseFormattersOptions {
  /** Optional custom currency formatter passed from parent */
  formatCurrency?: (amount: number) => string;
  /** Locale for formatting (default: 'en-IN') */
  locale?: string;
  /** Currency code (default: 'INR') */
  currency?: string;
}

/**
 * Composable for shared formatting utilities
 * 
 * @example
 * ```ts
 * // In component with props
 * const { formatCurrency } = useFormatters({ formatCurrency: props.formatCurrency });
 * 
 * // In component without props
 * const { formatCurrency, formatNumber, formatDate } = useFormatters();
 * ```
 */
export function useFormatters(options: UseFormattersOptions = {}) {
  const locale = options.locale || 'en-IN';
  const currency = options.currency || 'INR';

  /**
   * Format a number as currency (INR by default)
   * Uses parent's formatter if provided, otherwise creates default
   */
  const formatCurrency: ComputedRef<(amount: number) => string> = computed(() => {
    if (options.formatCurrency) {
      return options.formatCurrency;
    }
    
    return (amount: number): string => {
      return new Intl.NumberFormat(locale, {
        style: 'currency',
        currency: currency,
        maximumFractionDigits: 0
      }).format(amount);
    };
  });

  /**
   * Format a number with locale-specific separators
   */
  const formatNumber: ComputedRef<(num: number, decimals?: number) => string> = computed(() => {
    return (num: number, decimals = 0): string => {
      return new Intl.NumberFormat(locale, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }).format(num);
    };
  });

  /**
   * Format a date to locale string
   */
  const formatDate: ComputedRef<(date: string | Date, options?: Intl.DateTimeFormatOptions) => string> = computed(() => {
    return (date: string | Date, opts?: Intl.DateTimeFormatOptions): string => {
      const d = typeof date === 'string' ? new Date(date) : date;
      return d.toLocaleDateString(locale, opts || {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    };
  });

  /**
   * Format a percentage value
   */
  const formatPercent: ComputedRef<(value: number, decimals?: number) => string> = computed(() => {
    return (value: number, decimals = 1): string => {
      return new Intl.NumberFormat(locale, {
        style: 'percent',
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
      }).format(value / 100);
    };
  });

  return {
    formatCurrency,
    formatNumber,
    formatDate,
    formatPercent
  };
}

/**
 * Standalone currency formatter (for non-component use)
 */
export function formatCurrencyStandalone(
  amount: number,
  locale = 'en-IN',
  currency = 'INR'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: currency,
    maximumFractionDigits: 0
  }).format(amount);
}

/**
 * Standalone number formatter (for non-component use)
 */
export function formatNumberStandalone(
  num: number,
  decimals = 0,
  locale = 'en-IN'
): string {
  return new Intl.NumberFormat(locale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num);
}

/**
 * Standalone date formatter (for non-component use)
 */
export function formatDateStandalone(
  date: string | Date,
  locale = 'en-IN',
  options?: Intl.DateTimeFormatOptions
): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString(locale, options || {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}
