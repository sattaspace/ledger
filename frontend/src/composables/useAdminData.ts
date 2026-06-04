/**
 * useAdminData — shared admin data state across Vue components.
 *
 * API-9 FIX: Provides a singleton composable for commonly-fetched admin data
 * that multiple admin pages need (product list for filter dropdowns, service
 * domains for API key configuration, etc.). Previously, each admin page
 * re-fetched the same data on every visit, wasting 1-3 API calls per page.
 *
 * Features:
 * - Window-level singleton (survives Astro View Transition module re-evaluations)
 * - Staleness-based refetch (5-minute threshold for admin data)
 * - Deduplicated fetching (multiple concurrent callers share one promise)
 *
 * Usage:
 *   const { adminProducts, adminServiceDomains, fetchAdminProducts, fetchServiceDomains } = useAdminData();
 */

import { ref } from "vue";
import { adminApi } from "@/lib/admin";
import type { AdminProductSchema, ServiceDomainSchema } from "@/lib/admin";

// ─── Window-level shared state (survives module re-evaluation) ────────────

const SB_ADMIN_DATA_KEY = "__sb_admin_data_composable";

// Staleness threshold for admin data (5 minutes — admin data changes rarely)
const STALE_THRESHOLD_MS = 300_000;

interface SharedAdminDataState {
  // Vue reactive refs
  adminProductsRef: any; // ref<AdminProductSchema[]>
  serviceDomainsRef: any; // ref<ServiceDomainSchema[]>
  productsLoadingRef: any; // ref<boolean>
  domainsLoadingRef: any; // ref<boolean>

  // Plain data for deduplication
  productsFetchPromise: Promise<AdminProductSchema[]> | null;
  domainsFetchPromise: Promise<ServiceDomainSchema[]> | null;
  productsLastFetchTime: number;
  domainsLastFetchTime: number;
}

function getSharedAdminDataState(): SharedAdminDataState {
  if (typeof window === "undefined") {
    // SSR fallback
    return {
      adminProductsRef: ref<AdminProductSchema[]>([]),
      serviceDomainsRef: ref<ServiceDomainSchema[]>([]),
      productsLoadingRef: ref(false),
      domainsLoadingRef: ref(false),
      productsFetchPromise: null,
      domainsFetchPromise: null,
      productsLastFetchTime: 0,
      domainsLastFetchTime: 0,
    };
  }
  const win = window as any;
  if (!win[SB_ADMIN_DATA_KEY]) {
    win[SB_ADMIN_DATA_KEY] = {
      adminProductsRef: ref<AdminProductSchema[]>([]),
      serviceDomainsRef: ref<ServiceDomainSchema[]>([]),
      productsLoadingRef: ref(false),
      domainsLoadingRef: ref(false),
      productsFetchPromise: null,
      domainsFetchPromise: null,
      productsLastFetchTime: 0,
      domainsLastFetchTime: 0,
    };
  }
  return win[SB_ADMIN_DATA_KEY];
}

// Recover shared refs from window
const sharedState = getSharedAdminDataState();
const sharedAdminProducts = sharedState.adminProductsRef as import("vue").Ref<
  AdminProductSchema[]
>;
const sharedServiceDomains = sharedState.serviceDomainsRef as import("vue").Ref<
  ServiceDomainSchema[]
>;
const sharedProductsLoading =
  sharedState.productsLoadingRef as import("vue").Ref<boolean>;
const sharedDomainsLoading =
  sharedState.domainsLoadingRef as import("vue").Ref<boolean>;

export function useAdminData() {
  const adminProducts = sharedAdminProducts;
  const serviceDomains = sharedServiceDomains;
  const productsLoading = sharedProductsLoading;
  const domainsLoading = sharedDomainsLoading;

  /**
   * Fetch the admin product list (with plan counts, etc.).
   * Used by SubscriptionsAdmin for filter dropdowns and ProductsAdmin for the main list.
   * Cached for 5 minutes — products rarely change.
   */
  async function fetchAdminProducts(): Promise<AdminProductSchema[]> {
    const ws = getSharedAdminDataState();
    const isStale = Date.now() - ws.productsLastFetchTime > STALE_THRESHOLD_MS;

    // Return cached data if fresh
    if (adminProducts.value.length > 0 && !isStale) {
      return adminProducts.value;
    }

    // Deduplicate concurrent fetches
    if (ws.productsFetchPromise) return ws.productsFetchPromise;

    ws.productsFetchPromise = (async () => {
      sharedProductsLoading.value = true;
      try {
        const data = await adminApi.listProducts({ page: 1, page_size: 100 });
        const items = data.results || data;
        adminProducts.value = items;
        ws.productsLastFetchTime = Date.now();
        return items;
      } catch {
        return adminProducts.value;
      } finally {
        sharedProductsLoading.value = false;
        ws.productsFetchPromise = null;
      }
    })();

    return ws.productsFetchPromise;
  }

  /**
   * Fetch service domains (for API key configuration, product dropdowns).
   * Cached for 5 minutes — domains rarely change.
   */
  async function fetchServiceDomains(): Promise<ServiceDomainSchema[]> {
    const ws = getSharedAdminDataState();
    const isStale = Date.now() - ws.domainsLastFetchTime > STALE_THRESHOLD_MS;

    // Return cached data if fresh
    if (serviceDomains.value.length > 0 && !isStale) {
      return serviceDomains.value;
    }

    // Deduplicate concurrent fetches
    if (ws.domainsFetchPromise) return ws.domainsFetchPromise;

    ws.domainsFetchPromise = (async () => {
      sharedDomainsLoading.value = true;
      try {
        const data = await adminApi.fetchServiceDomains();
        serviceDomains.value = data;
        ws.domainsLastFetchTime = Date.now();
        return data;
      } catch {
        return serviceDomains.value;
      } finally {
        sharedDomainsLoading.value = false;
        ws.domainsFetchPromise = null;
      }
    })();

    return ws.domainsFetchPromise;
  }

  /**
   * Force a fresh fetch of admin products — clears cache first.
   * Use after creating/updating/deleting a product.
   */
  async function refetchAdminProducts(): Promise<AdminProductSchema[]> {
    const ws = getSharedAdminDataState();
    adminProducts.value = [];
    ws.productsFetchPromise = null;
    ws.productsLastFetchTime = 0;
    return fetchAdminProducts();
  }

  /**
   * Force a fresh fetch of service domains — clears cache first.
   */
  async function refetchServiceDomains(): Promise<ServiceDomainSchema[]> {
    const ws = getSharedAdminDataState();
    serviceDomains.value = [];
    ws.domainsFetchPromise = null;
    ws.domainsLastFetchTime = 0;
    return fetchServiceDomains();
  }

  /**
   * Invalidate all admin data caches — forces fresh fetch on next call.
   */
  function invalidateAll(): void {
    const ws = getSharedAdminDataState();
    adminProducts.value = [];
    serviceDomains.value = [];
    ws.productsFetchPromise = null;
    ws.domainsFetchPromise = null;
    ws.productsLastFetchTime = 0;
    ws.domainsLastFetchTime = 0;
  }

  return {
    adminProducts,
    serviceDomains,
    productsLoading,
    domainsLoading,
    fetchAdminProducts,
    fetchServiceDomains,
    refetchAdminProducts,
    refetchServiceDomains,
    invalidateAll,
  };
}
