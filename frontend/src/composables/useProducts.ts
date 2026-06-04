/**
 * useProducts — shared product catalog state across Vue components.
 *
 * API-5 FIX: Provides a singleton composable for product data,
 * eliminating duplicate getProducts() and getProductBySlug() calls
 * from multiple components. Previously, BillingOverview, PlansLanding,
 * and PlanComparison each fetched products independently, wasting
 * 1 API call per billing page navigation.
 *
 * Features:
 * - Window-level singleton (survives Astro View Transition module re-evaluations)
 * - Deduplicated fetching (multiple concurrent callers share one promise)
 * - Staleness-based refetch (STALE_THRESHOLD_MS, not unconditional clear)
 * - Product detail caching (getProductBySlug results are cached by slug)
 * - Access matrix caching (getProductAccessMatrix results are cached by slug)
 *
 * Usage:
 *   const { products, productDetails, accessMatrices, fetchProducts, fetchProductDetail } = useProducts();
 */

import { ref } from "vue";
import { billingApi } from "@/lib/billing";
import type { ProductSchema, ProductDetailSchema } from "@/lib/billing";
import type { AccessMatrixSchema } from "@/lib/billing";

// ─── Window-level shared state (survives module re-evaluation) ────────────

const SB_PRODUCTS_COMPOSABLE_KEY = "__sb_products_composable";

// Staleness threshold: data older than this is considered stale and will be refetched.
const STALE_THRESHOLD_MS = 120_000; // 2 minutes (products change rarely)

interface SharedProductsState {
  // Vue reactive refs — stored on window so they survive module re-evaluation
  productsRef: any; // ref<ProductSchema[]>
  productDetailsRef: any; // ref<Map<string, ProductDetailSchema>>
  accessMatricesRef: any; // ref<Map<string, AccessMatrixSchema>>
  loadingRef: any; // ref<boolean>
  initializedRef: any; // ref<boolean>

  // Plain data for deduplication (not reactive)
  fetchPromise: Promise<ProductSchema[]> | null;
  detailFetchPromises: Map<string, Promise<ProductDetailSchema | null>>;
  matrixFetchPromises: Map<string, Promise<AccessMatrixSchema | null>>;
  lastFetchTime: number; // Timestamp of last successful fetch (for staleness check)
}

function getSharedProductsState(): SharedProductsState {
  if (typeof window === "undefined") {
    // SSR fallback
    return {
      productsRef: ref<ProductSchema[]>([]),
      productDetailsRef: ref(new Map<string, ProductDetailSchema>()),
      accessMatricesRef: ref(new Map<string, AccessMatrixSchema>()),
      loadingRef: ref(false),
      initializedRef: ref(false),
      fetchPromise: null,
      detailFetchPromises: new Map(),
      matrixFetchPromises: new Map(),
      lastFetchTime: 0,
    };
  }
  const win = window as any;
  if (!win[SB_PRODUCTS_COMPOSABLE_KEY]) {
    win[SB_PRODUCTS_COMPOSABLE_KEY] = {
      // Create Vue refs ONCE and store on window
      productsRef: ref<ProductSchema[]>([]),
      productDetailsRef: ref(new Map<string, ProductDetailSchema>()),
      accessMatricesRef: ref(new Map<string, AccessMatrixSchema>()),
      loadingRef: ref(false),
      initializedRef: ref(false),
      // Plain data
      fetchPromise: null,
      detailFetchPromises: new Map(),
      matrixFetchPromises: new Map(),
      lastFetchTime: 0,
    };
  }
  return win[SB_PRODUCTS_COMPOSABLE_KEY];
}

// Recover shared refs from window (or create new ones for SSR)
const sharedState = getSharedProductsState();
const sharedProducts = sharedState.productsRef as import("vue").Ref<
  ProductSchema[]
>;
const sharedProductDetails = sharedState.productDetailsRef as import("vue").Ref<
  Map<string, ProductDetailSchema>
>;
const sharedAccessMatrices = sharedState.accessMatricesRef as import("vue").Ref<
  Map<string, AccessMatrixSchema>
>;
const sharedLoading = sharedState.loadingRef as import("vue").Ref<boolean>;
const sharedInitialized =
  sharedState.initializedRef as import("vue").Ref<boolean>;

export function useProducts() {
  const products = sharedProducts;
  const productDetails = sharedProductDetails;
  const accessMatrices = sharedAccessMatrices;
  const loading = sharedLoading;

  /**
   * Check if the cached data is stale (older than STALE_THRESHOLD_MS).
   */
  function isStale(): boolean {
    const ws = getSharedProductsState();
    return Date.now() - ws.lastFetchTime > STALE_THRESHOLD_MS;
  }

  /**
   * Fetch the product list from the API. Deduplicates concurrent calls.
   *
   * Returns cached data if still fresh. Use refetchProducts() to
   * force a fresh API call regardless of staleness.
   */
  async function fetchProducts(): Promise<ProductSchema[]> {
    // Return cached data if fresh (not stale)
    if (
      sharedInitialized.value &&
      sharedProducts.value.length > 0 &&
      !isStale()
    ) {
      return sharedProducts.value;
    }

    const ws = getSharedProductsState();
    if (ws.fetchPromise) return ws.fetchPromise;

    ws.fetchPromise = (async () => {
      sharedLoading.value = true;
      try {
        const data = await billingApi.getProducts();
        sharedProducts.value = data;
        sharedInitialized.value = true;
        ws.lastFetchTime = Date.now();
        return data;
      } catch {
        return [];
      } finally {
        sharedLoading.value = false;
        ws.fetchPromise = null;
      }
    })();

    return ws.fetchPromise;
  }

  /**
   * Fetch detailed product data (with plans) by slug.
   * Results are cached so repeated calls for the same slug return cached data.
   * Uses the user's currency for price conversion.
   */
  async function fetchProductDetail(
    slug: string,
    currency?: string,
  ): Promise<ProductDetailSchema | null> {
    // Return cached detail if available
    if (sharedProductDetails.value.has(slug)) {
      return sharedProductDetails.value.get(slug)!;
    }

    const ws = getSharedProductsState();
    // Deduplicate concurrent fetches for the same slug
    if (ws.detailFetchPromises.has(slug)) {
      return ws.detailFetchPromises.get(slug)!;
    }

    const promise = (async (): Promise<ProductDetailSchema | null> => {
      try {
        const data = await billingApi.getProductBySlug(slug, currency);
        sharedProductDetails.value.set(slug, data);
        return data;
      } catch {
        return null;
      } finally {
        ws.detailFetchPromises.delete(slug);
      }
    })();

    ws.detailFetchPromises.set(slug, promise);
    return promise;
  }

  /**
   * Fetch access matrix for a product by slug.
   * Results are cached so repeated calls for the same slug return cached data.
   */
  async function fetchAccessMatrix(
    slug: string,
  ): Promise<AccessMatrixSchema | null> {
    // Return cached matrix if available
    if (sharedAccessMatrices.value.has(slug)) {
      return sharedAccessMatrices.value.get(slug)!;
    }

    const ws = getSharedProductsState();
    // Deduplicate concurrent fetches for the same slug
    if (ws.matrixFetchPromises.has(slug)) {
      return ws.matrixFetchPromises.get(slug)!;
    }

    const promise = (async (): Promise<AccessMatrixSchema | null> => {
      try {
        const data = await billingApi.getProductAccessMatrix(slug);
        sharedAccessMatrices.value.set(slug, data);
        return data;
      } catch {
        return null;
      } finally {
        ws.matrixFetchPromises.delete(slug);
      }
    })();

    ws.matrixFetchPromises.set(slug, promise);
    return promise;
  }

  /**
   * Fetch product details + access matrices for ALL products in parallel.
   * This is more efficient than fetching them one by one in a loop.
   * Used by PlansLanding to avoid the N+1 problem.
   */
  async function fetchAllProductDetails(currency?: string): Promise<void> {
    // First ensure we have the product list
    const productList = await fetchProducts();

    // Fetch details and matrices for all products in parallel
    const detailPromises = productList.map((p) =>
      fetchProductDetail(p.slug, currency),
    );
    const matrixPromises = productList.map((p) => fetchAccessMatrix(p.slug));

    await Promise.all([...detailPromises, ...matrixPromises]);
  }

  /**
   * Force a fresh fetch from the API — clears cache first.
   * Use after product/plan changes in admin.
   */
  async function refetchProducts(): Promise<ProductSchema[]> {
    const ws = getSharedProductsState();
    sharedInitialized.value = false;
    sharedProducts.value = [];
    sharedProductDetails.value.clear();
    sharedAccessMatrices.value.clear();
    ws.fetchPromise = null;
    ws.lastFetchTime = 0;
    return fetchProducts();
  }

  /**
   * Invalidate cached products — forces fresh fetch on next call.
   * Lighter than refetchProducts() — doesn't trigger an immediate fetch.
   */
  function invalidateProducts(): void {
    const ws = getSharedProductsState();
    sharedInitialized.value = false;
    ws.lastFetchTime = 0;
  }

  /**
   * Invalidate a specific product's cached detail.
   * Use after plan changes for a specific product.
   */
  function invalidateProductDetail(slug: string): void {
    sharedProductDetails.value.delete(slug);
    sharedAccessMatrices.value.delete(slug);
  }

  return {
    products,
    productDetails,
    accessMatrices,
    loading,
    initialized: sharedInitialized,
    fetchProducts,
    fetchProductDetail,
    fetchAccessMatrix,
    fetchAllProductDetails,
    refetchProducts,
    invalidateProducts,
    invalidateProductDetail,
  };
}
