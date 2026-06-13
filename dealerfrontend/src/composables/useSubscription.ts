/**
 * useSubscription — shared subscription state across Vue components.
 *
 * Provides reactive subscription data fetched once and shared across all
 * dashboard components. Eliminates duplicate getSubscriptions() calls.
 *
 * Usage:
 *   const { subscriptions, isLoading, fetchSubscriptions, hasActiveSubscription } = useSubscription();
 */

import { ref } from "vue";
import { apiClient } from "../lib/api";
import type { SubscriptionOutput } from "../lib/types";

// ─── Module-level shared state (singleton across all components) ────────────

const sharedSubscriptions = ref<SubscriptionOutput[]>([]);
const sharedLoading = ref(false);
const sharedInitialized = ref(false);
let fetchPromise: Promise<SubscriptionOutput[]> | null = null;

export function useSubscription() {
  const subscriptions = sharedSubscriptions;
  const isLoading = sharedLoading;

  /**
   * Fetch subscriptions. Deduplicates concurrent calls — if multiple components
   * call fetchSubscriptions() simultaneously, only one API request is made
   * and all get the same result.
   *
   * Returns cached subscriptions if already loaded. Use refetchSubscriptions()
   * to force a fresh fetch (e.g. after plan change or checkout).
   */
  async function fetchSubscriptions(): Promise<SubscriptionOutput[]> {
    if (sharedInitialized.value && sharedSubscriptions.value.length > 0) {
      return sharedSubscriptions.value;
    }

    if (fetchPromise) return fetchPromise;

    fetchPromise = (async () => {
      sharedLoading.value = true;
      try {
        const result = await apiClient.get<{ items: SubscriptionOutput[] }>(
          "/billing/subscriptions",
        );
        const data =
          result?.items || (result as unknown as SubscriptionOutput[]);
        sharedSubscriptions.value = Array.isArray(data) ? data : [];
        sharedInitialized.value = true;
        return sharedSubscriptions.value;
      } catch {
        return [];
      } finally {
        sharedLoading.value = false;
        fetchPromise = null;
      }
    })();

    return fetchPromise;
  }

  /**
   * Force a fresh fetch from the API — clears cache first.
   * Use after plan changes, checkouts, cancels, reactivations, etc.
   */
  async function refetchSubscriptions(): Promise<SubscriptionOutput[]> {
    sharedInitialized.value = false;
    sharedSubscriptions.value = [];
    fetchPromise = null;
    return fetchSubscriptions();
  }

  /**
   * Check if the user has an active subscription for a given product.
   *
   * @param productSlug - The product slug (e.g. "dealercore")
   * @returns true if an active or trialing subscription exists for the product
   */
  function hasActiveSubscription(productSlug: string): boolean {
    return sharedSubscriptions.value.some(
      (sub) =>
        sub.product_slug === productSlug &&
        (sub.status === "active" || sub.status === "trialing"),
    );
  }

  /**
   * Get the subscription for a specific product.
   *
   * @param productSlug - The product slug
   * @returns The subscription or undefined if not found
   */
  function getSubscription(
    productSlug: string,
  ): SubscriptionOutput | undefined {
    return sharedSubscriptions.value.find(
      (sub) => sub.product_slug === productSlug,
    );
  }

  /**
   * Invalidate cached subscriptions — forces fresh fetch on next call.
   */
  function invalidateSubscriptions(): void {
    sharedInitialized.value = false;
    sharedSubscriptions.value = [];
  }

  return {
    subscriptions,
    isLoading,
    initialized: sharedInitialized,
    fetchSubscriptions,
    refetchSubscriptions,
    hasActiveSubscription,
    getSubscription,
    invalidateSubscriptions,
  };
}
