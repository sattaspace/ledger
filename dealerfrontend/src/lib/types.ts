/**
 * Type definitions for SattaBase API interactions.
 *
 * These types are used by lib/api.ts, lib/auth.ts, and composables
 * for type-safe API communication with the SattaBase backend.
 */

// ─── API Error Types ─────────────────────────────────────────────────────────

/**
 * Standard API error response from Django Ninja
 */
export interface ApiError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
  code?: string;
}

// ─── Token Types ─────────────────────────────────────────────────────────────

/**
 * JWT token pair returned from login/refresh endpoints
 */
export interface TokenPair {
  access: string;
  refresh: string;
}

/**
 * Authorization code response for SSO
 */
export interface AuthorizeResponse {
  code: string;
  expires_in: number;
}

// ─── User Types ──────────────────────────────────────────────────────────────

/**
 * User profile from SattaBase
 */
export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_staff?: boolean;
  avatar_url?: string;
  created_at?: string;
}

// ─── Subscription Types ──────────────────────────────────────────────────────

/**
 * Subscription status values
 */
export type SubscriptionStatus =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "incomplete"
  | "incomplete_expired"
  | "unpaid"
  | "paused";

/**
 * Billing cycle values
 */
export type BillingCycle = "monthly" | "yearly" | "lifetime";

/**
 * Subscription info returned from /billing/auth/me
 */
export interface Subscription {
  id: number;
  status: SubscriptionStatus;
  plan_name: string;
  plan_slug: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end?: boolean;
  trial_end?: string;
}

/**
 * Full subscription output from /billing/subscriptions endpoint
 * Used by useSubscription composable
 */
export interface SubscriptionOutput {
  id: number;
  user_id: number;
  status: string;
  cancel_at_period_end: boolean;
  currency?: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_start: string | null;
  trial_end: string | null;
  canceled_at: string | null;
  expires_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  plan_name: string;
  plan_slug: string;
  product_name: string;
  product_slug: string;
}

// ─── Access Map Types ────────────────────────────────────────────────────────

/**
 * Access map returned from /billing/auth/me
 *
 * This is a record of feature keys to their values (boolean, number, or string).
 * The values are determined by the subscription plan's access entries.
 *
 * Example:
 * {
 *   "dashboard": true,
 *   "reports": true,
 *   "max_products": 500,
 *   "max_dsrs": 5,
 *   "export_pdf": true
 * }
 */
export type AccessMap = Record<string, boolean | number | string>;

// ─── Auth Me Response ────────────────────────────────────────────────────────

/**
 * Full response from /billing/auth/me endpoint
 *
 * This is the primary endpoint for getting user info, subscription,
 * and access permissions for the current service domain.
 */
export interface AuthMeResponse {
  user: User;
  subscription: Subscription | null;
  access: AccessMap;
  is_dealer?: boolean;
  role?: string;
}

// ─── Login Types ─────────────────────────────────────────────────────────────

/**
 * Login request credentials
 */
export interface LoginCredentials {
  email: string;
  password: string;
  remember?: boolean;
}

/**
 * Login response from SattaBase
 */
export interface LoginResponse extends TokenPair {
  user: User;
}

// ─── Dealer-Specific Types ───────────────────────────────────────────────────

/**
 * Dealer user with additional dealer-specific fields
 */
export interface DealerUser extends User {
  is_dealer?: boolean;
  role?: "dealer" | "dsr" | "collector" | "admin";
  dealer_id?: number;
  dealer_name?: string;
}

/**
 * Dealer configuration
 */
export interface DealerConfig {
  username: string;
  fullName: string;
  role: string;
  businessName: string;
  address: string;
  phoneNumber: string;
  email: string;
  gstNumber: string;
  googleMapUrl: string;
  communicationNumber: string;
  defaultCurrency: string;
  defaultLocale: string;
}
