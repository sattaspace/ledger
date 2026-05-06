/**
 * Admin API client — types and functions for admin API key management.
 *
 * Covers the admin API key endpoints:
 *   - GET  /admin/api-keys/              (list, paginated, filterable)
 *   - POST /admin/api-keys/              (create, returns raw key once)
 *   - PATCH /admin/api-keys/{id}/revoke  (revoke key)
 *   - POST /admin/api-keys/{id}/rotate   (rotate key)
 *
 * All endpoints require admin role (JWT + IsAdmin permission).
 *
 * Usage in Vue components:
 *   import { adminApi } from "@/lib/admin";
 *   const keys = await adminApi.listApiKeys({ page: 1 });
 */

import { apiClient } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

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

export interface PaginationMeta {
  total_items: number;
  total_pages: number;
  current_page: number;
  page_size: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ApiKeyListResponse {
  meta: PaginationMeta;
  results: ApiKeyItem[];
}

export interface ServiceDomainOption {
  id: number;
  domain: string;
  product_name: string;
  is_active: boolean;
}

// ─── API Functions ───────────────────────────────────────────────────────────

export const adminApi = {
  /**
   * List all API keys with pagination and optional filters.
   */
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

  /**
   * Create a new API key. The raw key is returned ONLY in this response.
   */
  async createApiKey(
    payload: ApiKeyCreatePayload,
  ): Promise<ApiKeyCreateResponse> {
    return apiClient.post<ApiKeyCreateResponse>("/admin/api-keys/", payload);
  },

  /**
   * Revoke an API key. The key becomes immediately invalid.
   */
  async revokeApiKey(keyId: number): Promise<{ message: string }> {
    return apiClient.patch<{ message: string }>(
      `/admin/api-keys/${keyId}/revoke`,
    );
  },

  /**
   * Rotate an API key: revoke old + create new. New raw key returned once.
   */
  async rotateApiKey(keyId: number): Promise<ApiKeyRotateResponse> {
    return apiClient.post<ApiKeyRotateResponse>(
      `/admin/api-keys/${keyId}/rotate`,
    );
  },

  /**
   * Fetch available service domains for the create key dropdown.
   * Uses the public products endpoint to get domains.
   */
  async fetchServiceDomains(): Promise<ServiceDomainOption[]> {
    const products = await apiClient.get<
      Array<{
        id: number;
        name: string;
        slug: string;
        service_domains: Array<{
          id: number;
          domain: string;
          is_primary: boolean;
          is_active: boolean;
        }>;
      }>
    >("/billing/products");

    const domains: ServiceDomainOption[] = [];
    for (const product of products || []) {
      for (const domain of product.service_domains || []) {
        domains.push({
          id: domain.id,
          domain: domain.domain,
          product_name: product.name,
          is_active: domain.is_active,
        });
      }
    }
    return domains;
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
