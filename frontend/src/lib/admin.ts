/**
 * Admin API client — types and functions for all admin endpoints.
 *
 * Covers the admin API endpoints grouped by domain:
 *   - API Keys: create, list, revoke, rotate
 *   - Products: CRUD, toggle, list with counts
 *   - Service Domains: add, update, remove
 *   - Plans: CRUD, toggle, feature, duplicate
 *   - Access Entries: add, update, remove, bulk, matrix
 *   - Subscriptions: list, detail, override, cancel, expire, extend
 *   - Users: list, detail, status, role, audit
 *   - Refunds: list, approve, reject
 *   - Metrics: overview, revenue, subscriptions, products
 *   - Webhooks: list, retry
 *   - Audit Log: list
 *
 * All endpoints require admin role (JWT + IsAdmin permission).
 *
 * Usage in Vue components:
 *   import { adminApi } from "@/lib/admin";
 *   const keys = await adminApi.listApiKeys({ page: 1 });
 *   const products = await adminApi.listProducts();
 */

import { apiClient } from "@/lib/api";

// ─── Shared Types ───────────────────────────────────────────────────────────

export interface PaginationMeta {
  total_items: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface PaginatedResponse<T> {
  meta: PaginationMeta;
  results: T[];
}

// ─── API Key Types ──────────────────────────────────────────────────────────

export interface ApiKeyItem {
  id: number;
  name: string;
  api_key_prefix: string;
  service_domain_id: number;
  service_domain: string;
  permissions: Record<string, unknown>;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string | null;
  created_by: string | null;
}

export interface ApiKeyCreatePayload {
  name: string;
  service_domain_id: number;
}

export interface ApiKeyCreateResponse {
  id: number;
  name: string;
  api_key_prefix: string;
  raw_api_key: string;
  service_domain_id: number;
  service_domain: string;
  is_active: boolean;
  created_at: string | null;
  warning: string;
}

export interface ApiKeyRotateResponse {
  id: number;
  name: string;
  old_prefix: string;
  new_api_key: string;
  new_prefix: string;
  service_domain_id: number;
  service_domain: string;
  is_active: boolean;
  warning: string;
}

export interface ApiKeyListResponse extends PaginatedResponse<ApiKeyItem> {}

export interface ServiceDomainOption {
  id: number;
  domain: string;
  product_name: string;
  is_active: boolean;
}

// ─── Product Types ──────────────────────────────────────────────────────────

export interface ProductItem {
  id: number;
  name: string;
  slug: string;
  description: string;
  home_url: string;
  icon?: string | null;
  is_active: boolean;
  plan_count: number;
  active_plan_count?: number;
  subscriber_count: number;
  domain_count?: number;
  stripe_product_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductDetail extends ProductItem {
  plans: PlanItem[];
  service_domains: ServiceDomainDetail[];
}

export interface ProductCreatePayload {
  name: string;
  slug?: string;
  description?: string;
  home_url?: string;
}

export interface ProductUpdatePayload {
  name?: string;
  slug?: string;
  description?: string;
  home_url?: string;
  is_active?: boolean;
}

export interface ProductListResponse extends PaginatedResponse<ProductItem> {}

// ─── Service Domain Types ───────────────────────────────────────────────────

export interface ServiceDomainDetail {
  id: number;
  domain: string;
  is_primary: boolean;
  is_active: boolean;
  product_id: number;
  product_name: string;
  created_at: string;
}

export interface ServiceDomainCreatePayload {
  domain: string;
  is_primary?: boolean;
}

export interface ServiceDomainUpdatePayload {
  domain?: string;
  is_primary?: boolean;
  is_active?: boolean;
}

// ─── Plan Types ─────────────────────────────────────────────────────────────

export interface PlanItem {
  id: number;
  name: string;
  slug: string;
  price_cents: number;
  currency: string;
  billing_cycle: "monthly" | "yearly";
  trial_days: number;
  is_featured: boolean;
  is_active: boolean;
  sort_order: number;
  subscriber_count: number;
  access_entry_count: number;
  product_id: number;
  product_name: string;
  display_price?: string;
  is_free?: boolean;
}

export interface PlanDetail extends PlanItem {
  access_entries: AccessEntryItem[];
  stripe_price_id: string | null;
  description?: string;
}

export interface PlanCreatePayload {
  name: string;
  slug?: string;
  price_cents: number;
  currency?: string;
  billing_cycle: "monthly" | "yearly";
  trial_days?: number;
  is_featured?: boolean;
  sort_order?: number;
}

export interface PlanUpdatePayload {
  name?: string;
  slug?: string;
  price_cents?: number;
  currency?: string;
  billing_cycle?: "monthly" | "yearly";
  trial_days?: number;
  is_featured?: boolean;
  is_active?: boolean;
  sort_order?: number;
}

export interface PlanListResponse extends PaginatedResponse<PlanItem> {}

// ─── Access Entry Types ─────────────────────────────────────────────────────

export interface AccessEntryItem {
  id: number;
  key: string;
  value: string;
  value_type: "boolean" | "integer" | "string";
  description: string;
  plan_id: number;
  plan_name: string;
}

export interface AccessEntryCreatePayload {
  key: string;
  value: string;
  value_type: "boolean" | "integer" | "string";
  description?: string;
}

export interface AccessEntryUpdatePayload {
  key?: string;
  value?: string;
  value_type?: "boolean" | "integer" | "string";
  description?: string;
}

export interface AccessEntryBulkPayload {
  entries: AccessEntryCreatePayload[];
}

export interface AccessMatrixRow {
  key: string;
  description: string | null;
  values: Record<string, string | null>; // plan_slug → value
  entry_ids: Record<string, number | null>; // plan_slug → entry ID (for edit/delete)
}

export interface AccessMatrixResponse {
  product_id: number;
  product_name: string;
  plans: { slug: string; name: string; is_active: boolean }[];
  rows: AccessMatrixRow[];
}

// ─── Subscription Types ─────────────────────────────────────────────────────

export interface SubscriptionItem {
  id: number;
  user_email: string;
  user_name: string;
  product_name: string;
  plan_name: string;
  status:
    | "active"
    | "trialing"
    | "past_due"
    | "canceled"
    | "expired"
    | "paused";
  current_period_start: string;
  current_period_end: string;
  created_at: string;
}

export interface SubscriptionDetail extends SubscriptionItem {
  user_id: number;
  plan_id: number;
  product_id: number;
  stripe_subscription_id: string | null;
  cancel_at_period_end: boolean;
  trial_start: string | null;
  trial_end: string | null;
  plan_changes: PlanChangeItem[];
  invoices: InvoiceItem[];
  refunds: RefundItem[];
}

export interface SubscriptionOverridePayload {
  plan_id?: number;
  status?: string;
  current_period_end?: string;
}

export interface SubscriptionExtendPayload {
  extend_days: number;
}

export interface SubscriptionListResponse extends PaginatedResponse<SubscriptionItem> {}

export interface PlanChangeItem {
  id: number;
  from_plan_name: string;
  to_plan_name: string;
  proration_amount: number;
  created_at: string;
  initiated_by: string;
}

export interface InvoiceItem {
  id: number;
  invoice_number: string;
  amount: number;
  currency: string;
  status: string;
  hosted_url: string | null;
  created_at: string;
}

// ─── User Types ─────────────────────────────────────────────────────────────

export interface UserItem {
  id: number;
  display_name: string;
  email: string;
  role: string;
  is_staff: boolean;
  email_verified: boolean;
  is_active: boolean;
  subscription_count: number;
  last_login: string | null;
  created_at: string;
}

export interface UserDetail extends UserItem {
  avatar: string | null;
  currency: string;
  subscriptions: SubscriptionItem[];
}

export interface UserStatusPayload {
  is_active: boolean;
}

export interface UserRolePayload {
  role: string;
}

export interface UserAuditEntry {
  id: number;
  action: string;
  details: string;
  ip_address: string;
  created_at: string;
}

export interface UserListResponse extends PaginatedResponse<UserItem> {}

// ─── Refund Types ───────────────────────────────────────────────────────────

export interface RefundItem {
  id: number;
  subscription_id: number;
  user_email: string;
  product_name: string;
  amount: number;
  currency: string;
  status: "pending" | "approved" | "rejected" | "processed" | "failed";
  reason_category: string;
  reason_detail: string;
  initiated_by: string;
  approved_by: string | null;
  created_at: string;
}

export interface RefundApprovalPayload {
  approved: boolean;
  notes?: string;
}

export interface RefundListResponse extends PaginatedResponse<RefundItem> {}

// ─── Metrics Types ──────────────────────────────────────────────────────────
// Aligned with backend billing/admin_schemas.py (Phase 9)

export interface MetricsOverview {
  mrr_cents: number;
  mrr_display: string;
  active_subscriptions: number;
  trial_subscriptions: number;
  past_due_subscriptions: number;
  canceled_subscriptions: number;
  total_users: number;
  churn_rate: number;
  trial_conversion_rate: number;
  currency: string;
}

export interface MetricsRevenueByProduct {
  product_id: number;
  product_name: string;
  product_slug: string;
  mrr_cents: number;
  active_subscriptions: number;
  trial_subscriptions: number;
}

export interface MetricsRevenueByPlan {
  plan_id: number;
  plan_name: string;
  plan_slug: string;
  product_name: string;
  price_cents: number;
  subscriber_count: number;
  mrr_contribution_cents: number;
}

export interface MetricsRevenueByMonth {
  month: string;
  revenue_cents: number;
  new_subscriptions: number;
  churned_subscriptions: number;
  net_mrr_change_cents: number;
}

export interface MetricsRevenue {
  by_product: MetricsRevenueByProduct[];
  by_plan: MetricsRevenueByPlan[];
  by_month: MetricsRevenueByMonth[];
}

export interface MetricsSubscriptions {
  period_days: number;
  new_registrations: number;
  trial_starts: number;
  trial_conversions: number;
  trial_conversion_rate: number;
  active_to_canceled: number;
  active_to_past_due: number;
  past_due_to_active: number;
  by_product: {
    product_id: number;
    product_name: string;
    product_slug: string;
    trial_starts: number;
    trial_conversions: number;
    active_subscribers: number;
    canceled: number;
    past_due: number;
  }[];
}

export interface MetricsProductItem {
  id: number;
  name: string;
  slug: string;
  total_subscribers: number;
  active_subscribers: number;
  mrr_cents: number;
  plan_distribution: { plan_name: string; plan_slug: string; count: number }[];
}

export interface MetricsProducts {
  products: MetricsProductItem[];
}

// ─── Webhook Types ──────────────────────────────────────────────────────────

export interface WebhookEvent {
  id: number;
  event_id: string;
  event_type: string;
  status: "processed" | "pending" | "failed";
  error_message: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface WebhookListResponse extends PaginatedResponse<WebhookEvent> {}

// ─── Audit Log Types ────────────────────────────────────────────────────────

export interface AuditLogEntry {
  id: number;
  admin_user_id: number;
  admin_email: string;
  action: string;
  method: string;
  path: string;
  ip_address: string | null;
  status_code: number | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListResponse extends PaginatedResponse<AuditLogEntry> {}

// ─── API Functions ──────────────────────────────────────────────────────────

export const adminApi = {
  // ═══════════════════════════════════════════════════════════
  //  API Keys
  // ═══════════════════════════════════════════════════════════

  async listApiKeys(params?: {
    page?: number;
    page_size?: number;
    service_domain_id?: number;
    is_active?: boolean;
  }): Promise<ApiKeyListResponse> {
    const queryParams: Record<string, string | number | boolean> = {};
    if (params?.page) queryParams.page = params.page;
    if (params?.page_size) queryParams.page_size = params.page_size;
    if (params?.service_domain_id !== undefined)
      queryParams.service_domain_id = params.service_domain_id;
    if (params?.is_active !== undefined)
      queryParams.is_active = params.is_active;

    return apiClient.get<ApiKeyListResponse>("/admin/api-keys/", {
      params: queryParams,
    });
  },

  async createApiKey(
    payload: ApiKeyCreatePayload,
  ): Promise<ApiKeyCreateResponse> {
    return apiClient.post<ApiKeyCreateResponse>("/admin/api-keys/", payload);
  },

  async revokeApiKey(keyId: number): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/api-keys/${keyId}/revoke`,
    );
  },

  async rotateApiKey(keyId: number): Promise<ApiKeyRotateResponse> {
    return apiClient.post<ApiKeyRotateResponse>(
      `/admin/api-keys/${keyId}/rotate`,
    );
  },

  async fetchServiceDomains(): Promise<ServiceDomainOption[]> {
    const domains = await apiClient.get<ServiceDomainOption[]>(
      "/admin/api-keys/service-domains",
    );
    return domains || [];
  },

  // ═══════════════════════════════════════════════════════════
  //  Products
  // ═══════════════════════════════════════════════════════════

  async listProducts(params?: {
    page?: number;
    page_size?: number;
    is_active?: boolean;
  }): Promise<ProductListResponse> {
    return apiClient.get<ProductListResponse>("/admin/products", { params });
  },

  async getProduct(productId: number): Promise<ProductDetail> {
    return apiClient.get<ProductDetail>(`/admin/products/${productId}`);
  },

  async createProduct(payload: ProductCreatePayload): Promise<ProductDetail> {
    return apiClient.post<ProductDetail>("/admin/products", payload);
  },

  async updateProduct(
    productId: number,
    payload: ProductUpdatePayload,
  ): Promise<ProductDetail> {
    return apiClient.put<ProductDetail>(
      `/admin/products/${productId}`,
      payload,
    );
  },

  async toggleProduct(productId: number): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/products/${productId}/toggle`,
    );
  },

  async deleteProduct(productId: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(
      `/admin/products/${productId}`,
    );
  },

  // ═══════════════════════════════════════════════════════════
  //  Service Domains
  // ═══════════════════════════════════════════════════════════

  async addServiceDomain(
    productId: number,
    payload: ServiceDomainCreatePayload,
  ): Promise<ServiceDomainDetail> {
    return apiClient.post<ServiceDomainDetail>(
      `/admin/products/${productId}/domains`,
      payload,
    );
  },

  async updateServiceDomain(
    domainId: number,
    payload: ServiceDomainUpdatePayload,
  ): Promise<ServiceDomainDetail> {
    return apiClient.put<ServiceDomainDetail>(
      `/admin/domains/${domainId}`,
      payload,
    );
  },

  async deleteServiceDomain(domainId: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/admin/domains/${domainId}`);
  },

  // ═══════════════════════════════════════════════════════════
  //  Plans
  // ═══════════════════════════════════════════════════════════

  async listPlans(
    productId: number,
    params?: {
      page?: number;
      page_size?: number;
      is_active?: boolean;
    },
  ): Promise<PlanListResponse> {
    return apiClient.get<PlanListResponse>(
      `/admin/products/${productId}/plans`,
      { params },
    );
  },

  async getPlan(planId: number): Promise<PlanDetail> {
    return apiClient.get<PlanDetail>(`/admin/plans/${planId}`);
  },

  async createPlan(
    productId: number,
    payload: PlanCreatePayload,
  ): Promise<PlanDetail> {
    return apiClient.post<PlanDetail>(
      `/admin/products/${productId}/plans`,
      payload,
    );
  },

  async updatePlan(
    planId: number,
    payload: PlanUpdatePayload,
  ): Promise<PlanDetail> {
    return apiClient.put<PlanDetail>(`/admin/plans/${planId}`, payload);
  },

  async togglePlan(planId: number): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/plans/${planId}/toggle`,
    );
  },

  async togglePlanFeature(planId: number): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/plans/${planId}/feature`,
    );
  },

  async duplicatePlan(planId: number): Promise<PlanDetail> {
    return apiClient.post<PlanDetail>(`/admin/plans/${planId}/duplicate`);
  },

  async deletePlan(planId: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(`/admin/plans/${planId}`);
  },

  // ═══════════════════════════════════════════════════════════
  //  Access Entries
  // ═══════════════════════════════════════════════════════════

  async addAccessEntry(
    planId: number,
    payload: AccessEntryCreatePayload,
  ): Promise<AccessEntryItem> {
    return apiClient.post<AccessEntryItem>(
      `/admin/plans/${planId}/access-entries`,
      payload,
    );
  },

  async updateAccessEntry(
    entryId: number,
    payload: AccessEntryUpdatePayload,
  ): Promise<AccessEntryItem> {
    return apiClient.put<AccessEntryItem>(
      `/admin/access-entries/${entryId}`,
      payload,
    );
  },

  async deleteAccessEntry(entryId: number): Promise<{ message: string }> {
    return apiClient.delete<{ message: string }>(
      `/admin/access-entries/${entryId}`,
    );
  },

  async bulkSetAccessEntries(
    planId: number,
    payload: AccessEntryBulkPayload,
  ): Promise<AccessEntryItem[]> {
    return apiClient.post<AccessEntryItem[]>(
      `/admin/plans/${planId}/access-entries/bulk`,
      payload,
    );
  },

  async getAccessMatrix(productId: number): Promise<AccessMatrixResponse> {
    return apiClient.get<AccessMatrixResponse>(
      `/admin/products/${productId}/access-matrix`,
    );
  },

  // ═══════════════════════════════════════════════════════════
  //  Subscriptions
  // ═══════════════════════════════════════════════════════════

  async listSubscriptions(params?: {
    page?: number;
    page_size?: number;
    product_id?: number;
    plan_id?: number;
    status?: string;
    search?: string;
  }): Promise<SubscriptionListResponse> {
    return apiClient.get<SubscriptionListResponse>("/admin/subscriptions", {
      params,
    });
  },

  async getSubscription(subscriptionId: number): Promise<SubscriptionDetail> {
    return apiClient.get<SubscriptionDetail>(
      `/admin/subscriptions/${subscriptionId}`,
    );
  },

  async overrideSubscription(
    subscriptionId: number,
    payload: SubscriptionOverridePayload,
  ): Promise<SubscriptionDetail> {
    return apiClient.patch<SubscriptionDetail>(
      `/admin/subscriptions/${subscriptionId}/override`,
      payload,
    );
  },

  async cancelSubscription(
    subscriptionId: number,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/subscriptions/${subscriptionId}/cancel`,
    );
  },

  async expireSubscription(
    subscriptionId: number,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/subscriptions/${subscriptionId}/expire`,
    );
  },

  async extendSubscription(
    subscriptionId: number,
    payload: SubscriptionExtendPayload,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/subscriptions/${subscriptionId}/extend`,
      payload,
    );
  },

  async getSubscriptionPlanChanges(
    subscriptionId: number,
  ): Promise<PlanChangeItem[]> {
    return apiClient.get<PlanChangeItem[]>(
      `/admin/subscriptions/${subscriptionId}/plan-changes`,
    );
  },

  async getSubscriptionInvoices(
    subscriptionId: number,
  ): Promise<InvoiceItem[]> {
    return apiClient.get<InvoiceItem[]>(
      `/admin/subscriptions/${subscriptionId}/invoices`,
    );
  },

  async getSubscriptionRefunds(subscriptionId: number): Promise<RefundItem[]> {
    return apiClient.get<RefundItem[]>(
      `/admin/subscriptions/${subscriptionId}/refunds`,
    );
  },

  // ═══════════════════════════════════════════════════════════
  //  Users
  // ═══════════════════════════════════════════════════════════

  async listUsers(params?: {
    page?: number;
    page_size?: number;
    role?: string;
    is_active?: boolean;
    email_verified?: boolean;
    search?: string;
  }): Promise<UserListResponse> {
    return apiClient.get<UserListResponse>("/admin/users", { params });
  },

  async getUser(userId: number): Promise<UserDetail> {
    return apiClient.get<UserDetail>(`/admin/users/${userId}`);
  },

  async updateUserStatus(
    userId: number,
    payload: UserStatusPayload,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/users/${userId}/status`,
      payload,
    );
  },

  async updateUserRole(
    userId: number,
    payload: UserRolePayload,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/users/${userId}/role`,
      payload,
    );
  },

  async getUserAudit(
    userId: number,
    params?: {
      page?: number;
      page_size?: number;
    },
  ): Promise<PaginatedResponse<UserAuditEntry>> {
    return apiClient.get<PaginatedResponse<UserAuditEntry>>(
      `/admin/users/${userId}/audit`,
      { params },
    );
  },

  // ═══════════════════════════════════════════════════════════
  //  Refunds
  // ═══════════════════════════════════════════════════════════

  async listRefunds(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    reason_category?: string;
  }): Promise<RefundListResponse> {
    return apiClient.get<RefundListResponse>("/admin/refunds", { params });
  },

  async approveRefund(
    refundId: number,
    payload: RefundApprovalPayload,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/refunds/${refundId}/approve`,
      payload,
    );
  },

  async rejectRefund(
    refundId: number,
    payload: RefundApprovalPayload,
  ): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/refunds/${refundId}/reject`,
      payload,
    );
  },

  // ═══════════════════════════════════════════════════════════
  //  Metrics
  // ═══════════════════════════════════════════════════════════

  async getMetricsOverview(): Promise<MetricsOverview> {
    return apiClient.get<MetricsOverview>("/admin/metrics/overview");
  },

  async getMetricsRevenue(params?: {
    period?: string;
    product_id?: number;
  }): Promise<MetricsRevenue> {
    return apiClient.get<MetricsRevenue>("/admin/metrics/revenue", { params });
  },

  async getMetricsSubscriptions(params?: {
    period?: string;
  }): Promise<MetricsSubscriptions> {
    return apiClient.get<MetricsSubscriptions>("/admin/metrics/subscriptions", {
      params,
    });
  },

  async getMetricsProducts(): Promise<MetricsProducts> {
    return apiClient.get<MetricsProducts>("/admin/metrics/products");
  },

  // ═══════════════════════════════════════════════════════════
  //  Webhooks
  // ═══════════════════════════════════════════════════════════

  async listWebhooks(params?: {
    page?: number;
    page_size?: number;
    event_type?: string;
    status?: string;
  }): Promise<WebhookListResponse> {
    return apiClient.get<WebhookListResponse>("/admin/webhooks", { params });
  },

  async retryWebhook(webhookId: number): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      `/admin/webhooks/${webhookId}/retry`,
    );
  },

  // ═══════════════════════════════════════════════════════════
  //  Audit Log
  // ═══════════════════════════════════════════════════════════

  async listAuditLog(params?: {
    page?: number;
    page_size?: number;
    admin_user?: string;
    action?: string;
  }): Promise<AuditLogListResponse> {
    return apiClient.get<AuditLogListResponse>("/admin/audit-log", { params });
  },
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Format an API key prefix for display (truncate + ellipsis).
 */
export function formatKeyPrefix(prefix: string): string {
  if (!prefix) return "—";
  if (prefix.length <= 14) return prefix;
  return prefix.slice(0, 14) + "...";
}

/**
 * Format a datetime string for display.
 */
export function formatDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "Never";
  const locale =
    typeof navigator !== "undefined" ? navigator.language : "en-US";
  return new Date(dateStr).toLocaleDateString(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a relative time string (e.g., "2 hours ago", "3 days ago").
 */
export function formatRelativeTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "Never";
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return "just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 30) return `${diffDays}d ago`;
  return formatDateTime(dateStr);
}

/**
 * Get a status badge color class for subscription status.
 */
export function getSubscriptionStatusColor(status: string): {
  bg: string;
  text: string;
} {
  switch (status) {
    case "active":
      return {
        bg: "bg-green-100 dark:bg-green-950",
        text: "text-green-700 dark:text-green-400",
      };
    case "trialing":
      return {
        bg: "bg-blue-100 dark:bg-blue-950",
        text: "text-blue-700 dark:text-blue-400",
      };
    case "past_due":
      return {
        bg: "bg-amber-100 dark:bg-amber-950",
        text: "text-amber-700 dark:text-amber-400",
      };
    case "canceled":
      return {
        bg: "bg-gray-100 dark:bg-gray-900",
        text: "text-gray-600 dark:text-gray-400",
      };
    case "expired":
      return {
        bg: "bg-red-100 dark:bg-red-950",
        text: "text-red-700 dark:text-red-400",
      };
    case "paused":
      return {
        bg: "bg-orange-100 dark:bg-orange-950",
        text: "text-orange-700 dark:text-orange-400",
      };
    default:
      return {
        bg: "bg-gray-100 dark:bg-gray-900",
        text: "text-gray-600 dark:text-gray-400",
      };
  }
}

/**
 * Get a status badge color class for refund status.
 */
export function getRefundStatusColor(status: string): {
  bg: string;
  text: string;
} {
  switch (status) {
    case "pending":
      return {
        bg: "bg-amber-100 dark:bg-amber-950",
        text: "text-amber-700 dark:text-amber-400",
      };
    case "approved":
      return {
        bg: "bg-blue-100 dark:bg-blue-950",
        text: "text-blue-700 dark:text-blue-400",
      };
    case "processed":
      return {
        bg: "bg-green-100 dark:bg-green-950",
        text: "text-green-700 dark:text-green-400",
      };
    case "rejected":
      return {
        bg: "bg-red-100 dark:bg-red-950",
        text: "text-red-700 dark:text-red-400",
      };
    case "failed":
      return {
        bg: "bg-red-100 dark:bg-red-950",
        text: "text-red-700 dark:text-red-400",
      };
    default:
      return {
        bg: "bg-gray-100 dark:bg-gray-900",
        text: "text-gray-600 dark:text-gray-400",
      };
  }
}

/**
 * Get a status badge color class for webhook status.
 */
export function getWebhookStatusColor(status: string): {
  bg: string;
  text: string;
} {
  switch (status) {
    case "processed":
      return {
        bg: "bg-green-100 dark:bg-green-950",
        text: "text-green-700 dark:text-green-400",
      };
    case "pending":
      return {
        bg: "bg-amber-100 dark:bg-amber-950",
        text: "text-amber-700 dark:text-amber-400",
      };
    case "failed":
      return {
        bg: "bg-red-100 dark:bg-red-950",
        text: "text-red-700 dark:text-red-400",
      };
    default:
      return {
        bg: "bg-gray-100 dark:bg-gray-900",
        text: "text-gray-600 dark:text-gray-400",
      };
  }
}
