/**
 * TypeScript interfaces that mirror the Sattabase backend schemas.
 *
 * These types use the EXACT same field names as the actual backend API response
 * (snake_case), matching the Python SDK's Pydantic models and backend Django schemas.
 */

/** JWT token pair returned by login and refresh endpoints. */
export interface TokenPair {
  /** Short-lived access token */
  access: string;
  /** Long-lived refresh token */
  refresh: string;
}

/** User profile data. Mirrors backend `UserOutputSchema`. */
export interface User {
  id: number;
  slug: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  avatar: string | null;
  timezone: string | null;
  currency: string | null;
  language: string | null;
  is_email_verified: boolean;
  is_active: boolean;
  role: string;
  created_at: string | null;
  full_name: string;
  display_name: string;
}

/**
 * Subscription summary returned in auth/me response.
 * Mirrors backend `SubscriptionInfoSchema`.
 */
export interface SubscriptionInfo {
  plan_name: string;
  plan_slug: string;
  status: string;
  current_period_end: string | null;
  trial_end: string | null;
  is_active: boolean;
}

/**
 * Enhanced auth/me response with subscription and access data.
 * Mirrors backend `AuthMeSchema`.
 *
 * Provides helper methods for feature gating.
 */
export class AuthMeResponse {
  user: User;
  account_status: string;
  subscription: SubscriptionInfo | null;
  access: Record<string, boolean | number | string>;
  exchange_rates: Record<string, string> | null;
  currencies: Record<
    string,
    { symbol: string; name: string; decimal_digits: number }
  > | null;

  constructor(data: {
    user: User;
    account_status?: string;
    subscription?: SubscriptionInfo | null;
    access?: Record<string, boolean | number | string>;
    exchange_rates?: Record<string, string> | null;
    currencies?: Record<
      string,
      { symbol: string; name: string; decimal_digits: number }
    > | null;
  }) {
    this.user = data.user;
    this.account_status = data.account_status ?? "active";
    this.subscription = data.subscription ?? null;
    this.access = data.access ?? {};
    this.exchange_rates = data.exchange_rates ?? null;
    this.currencies = data.currencies ?? null;
  }

  /**
   * Check if the user has access to a feature.
   *
   * Coerces string values: "true" → true, "false" → false.
   * Also treats non-zero integers as truthy.
   */
  hasAccess(key: string): boolean {
    const value = this.access[key];
    if (value === undefined || value === null) return false;
    if (typeof value === "boolean") return value;
    if (typeof value === "string")
      return ["true", "1", "yes"].includes(value.toLowerCase());
    if (typeof value === "number") return value !== 0;
    return Boolean(value);
  }

  /** Get the raw value for an access key. */
  getAccess(key: string, defaultValue?: unknown): unknown {
    return key in this.access ? this.access[key] : defaultValue;
  }

  /** Return all access keys the user has. */
  get accessKeys(): string[] {
    return Object.keys(this.access);
  }
}

/** Generic message response from the API. Mirrors backend `MessageResponse`. */
export interface MessageResponse {
  message: string;
  success: boolean;
}
