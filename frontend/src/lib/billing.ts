/**
 * Billing API client — types and functions for the billing backend.
 *
 * Covers all billing endpoints:
 *   - Public:  GET /billing/products, GET /billing/products/{slug}, GET /billing/products/{slug}/plans
 *   - Protected: GET /billing/auth/me, GET /billing/subscriptions, subscription management
 *
 * Usage in Vue components:
 *   import { billingApi } from "@/lib/billing";
 *   const subs = await billingApi.getSubscriptions();
 */

import { apiClient } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface AccessEntrySchema {
  key: string;
  value: boolean | number | string;
  description?: string | null;
}

export interface PlanSchema {
  id: number;
  name: string;
  slug: string;
  description: string;
  price_cents: number;
  currency: string;
  billing_cycle: "monthly" | "yearly" | "lifetime";
  trial_days: number;
  features: Record<string, string>;
  sort_order: number;
  is_active: boolean;
  is_featured: boolean;
  display_price: string;
  is_free: boolean;
}

export interface PlanDetailSchema extends PlanSchema {
  access_entries: AccessEntrySchema[];
}

export interface ServiceDomainSchema {
  id: number;
  domain: string;
  product_id: number;
  is_primary: boolean;
  is_active: boolean;
}

export interface ProductSchema {
  id: number;
  name: string;
  slug: string;
  description: string;
  home_url: string;
  is_active: boolean;
  created_at: string;
}

export interface ProductDetailSchema extends ProductSchema {
  plans: PlanSchema[];
  service_domains: ServiceDomainSchema[];
}

export interface SubscriptionInfoSchema {
  plan_name: string;
  plan_slug: string;
  status: string;
  current_period_end: string | null;
  trial_end: string | null;
  is_active: boolean;
}

export interface SubscriptionOutputSchema {
  id: number;
  user_id: number;
  status: string;
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

export interface SubscriptionDetailSchema extends SubscriptionOutputSchema {
  plan: PlanDetailSchema;
  access: Record<string, boolean | number | string>;
}

export interface AuthMeSchema {
  user: Record<string, unknown>;
  subscription: SubscriptionInfoSchema | null;
  access: Record<string, boolean | number | string>;
}

export interface CheckoutInputSchema {
  plan_slug: string;
  billing_cycle?: string;
}

export interface ChangePlanInputSchema {
  plan_slug: string;
}

// ─── API Functions ───────────────────────────────────────────────────────────

export const billingApi = {
  // ── Public endpoints ──

  async getProducts(): Promise<ProductSchema[]> {
    return apiClient.get<ProductSchema[]>("/billing/products");
  },

  async getProductBySlug(slug: string): Promise<ProductDetailSchema> {
    return apiClient.get<ProductDetailSchema>(`/billing/products/${slug}`);
  },

  async getPlansForProduct(slug: string): Promise<PlanSchema[]> {
    return apiClient.get<PlanSchema[]>(`/billing/products/${slug}/plans`);
  },

  // ── Protected endpoints ──

  async getAuthMe(domain?: string): Promise<AuthMeSchema> {
    const headers: Record<string, string> = {};
    if (domain) {
      headers["X-Service-Domain"] = domain;
    }
    return apiClient.get<AuthMeSchema>("/billing/auth/me", { headers });
  },

  async getSubscriptions(): Promise<SubscriptionOutputSchema[]> {
    return apiClient.get<SubscriptionOutputSchema[]>("/billing/subscriptions");
  },

  async getSubscriptionDetail(productSlug: string): Promise<SubscriptionDetailSchema> {
    return apiClient.get<SubscriptionDetailSchema>(`/billing/subscriptions/${productSlug}`);
  },

  async cancelSubscription(productSlug: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/billing/subscriptions/${productSlug}/cancel`);
  },

  async reactivateSubscription(productSlug: string): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(`/billing/subscriptions/${productSlug}/reactivate`);
  },

  async changePlan(productSlug: string, planSlug: string): Promise<{ message: string }> {
    const body: ChangePlanInputSchema = { plan_slug: planSlug };
    return apiClient.post<{ message: string }>(
      `/billing/subscriptions/${productSlug}/change-plan`,
      body,
    );
  },

  async createCheckout(productSlug: string, planSlug: string, billingCycle?: string): Promise<{ checkout_url: string }> {
    const body: CheckoutInputSchema = { plan_slug: planSlug, billing_cycle: billingCycle };
    return apiClient.post<{ checkout_url: string }>(
      `/billing/subscriptions/${productSlug}/checkout`,
      body,
    );
  },

  async confirmCheckout(sessionId: string): Promise<{
    plan_name: string;
    plan_slug: string;
    status: string;
    trial_end: string | null;
    current_period_end: string | null;
  }> {
    return apiClient.post(`/billing/checkout/confirm`, { session_id: sessionId });
  },

  async createPortalSession(): Promise<{ portal_url: string }> {
    return apiClient.post<{ portal_url: string }>("/billing/portal");
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Format price from cents to human-readable string.
 * Example: 900 → "$9.00"
 */
export function formatPrice(cents: number, currency: string = "USD"): string {
  if (cents === 0) return "Free";
  const amount = cents / 100;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
    minimumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format billing cycle for display.
 */
export function formatCycle(cycle: string): string {
  const map: Record<string, string> = {
    monthly: "/mo",
    yearly: "/yr",
    lifetime: "one-time",
  };
  return map[cycle] || cycle;
}

/**
 * Get status color classes for subscription status badge.
 */
export function getStatusStyle(status: string): { bg: string; text: string; dot: string } {
  const styles: Record<string, { bg: string; text: string; dot: string }> = {
    active: { bg: "bg-brand-50 dark:bg-brand-950/50", text: "text-brand-700 dark:text-brand-300", dot: "bg-brand-500" },
    trialing: { bg: "bg-blue-50 dark:bg-blue-950/50", text: "text-blue-700 dark:text-blue-300", dot: "bg-blue-500" },
    past_due: { bg: "bg-yellow-50 dark:bg-yellow-950/50", text: "text-yellow-700 dark:text-yellow-300", dot: "bg-yellow-500" },
    canceled: { bg: "bg-orange-50 dark:bg-orange-950/50", text: "text-orange-700 dark:text-orange-300", dot: "bg-orange-500" },
    paused: { bg: "bg-gray-50 dark:bg-gray-950/50", text: "text-gray-700 dark:text-gray-300", dot: "bg-gray-500" },
    expired: { bg: "bg-red-50 dark:bg-red-950/50", text: "text-red-700 dark:text-red-300", dot: "bg-red-500" },
  };
  return styles[status] || styles.expired;
}

/**
 * Format a date string for display.
 */
export function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
