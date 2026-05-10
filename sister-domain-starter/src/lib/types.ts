/**
 * TypeScript interfaces for the Sattabase Sister Domain Starter Kit.
 *
 * These types mirror the backend schemas returned by the Sattabase API.
 * Keep them in sync with the Django Ninja schemas in the Sattabase backend.
 */

// ─── User ────────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  slug: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  full_name: string;
  avatar: string | null;
  timezone: string;
  currency: string;
  language: string;
  is_email_verified: boolean;
  is_active: boolean;
  role: string;
}

// ─── Subscription ────────────────────────────────────────────────────────────

export interface SubscriptionInfo {
  plan_name: string;
  plan_slug: string;
  status: string;
  cancel_at_period_end: boolean;
  current_period_end: string | null;
  trial_end: string | null;
  is_active: boolean;
}

// ─── Auth Me Response ────────────────────────────────────────────────────────

export interface AuthMeResponse {
  user: User;
  account_status: string;
  subscription: SubscriptionInfo | null;
  access: Record<string, string | boolean | number>;

  /** Check if the user has access to a feature (truthy check). */
  hasAccess(key: string): boolean;

  /** Get a typed access value with optional default. */
  getAccess(key: string, defaultValue?: unknown): unknown;
}

// ─── Token Pair ──────────────────────────────────────────────────────────────

export interface TokenPair {
  access: string;
  refresh: string;
}

// ─── Authorization Code ──────────────────────────────────────────────────────

export interface AuthorizeResponse {
  code: string;
  expires_in: number;
}

// ─── Products & Plans ────────────────────────────────────────────────────────

export interface Product {
  id: number;
  name: string;
  slug: string;
  description: string;
}

export interface Plan {
  id: number;
  name: string;
  slug: string;
  price_cents: number;
  currency: string;
  billing_cycle: string;
}

// ─── Subscription Output ─────────────────────────────────────────────────────

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

// ─── API Response Types ──────────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface ApiError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
}
