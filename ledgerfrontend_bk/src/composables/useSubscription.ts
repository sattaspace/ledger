/**
 * useSubscription — shared subscription state across Vue components.
 *
 * Auto-invalidates when billing updates are detected (e.g. user returns
 * from SattaBase billing portal with ?billing_updated=1).
 */

import { ref } from "vue";
import { apiClient } from "@/lib/api";
import type { SubscriptionOutput } from "@/lib/types";

// ─── Module-level shared state (singleton across all components) ────────────

const sharedSubscriptions = ref<SubscriptionOutput[]>([]);
const sharedLoading = ref(false);
const sharedInitialized = ref(false);
let fetchPromise: Promise<SubscriptionOutput[]> | null = null;

// ─── Auto-invalidation on billing updates ──────────────────────────────────

const BILLING_EVENT = "sattabase:billing-updated";

if (typeof window !== "undefined") {
  window.addEventListener(BILLING_EVENT, () => {
    sharedInitialized.value = false;
    sharedSubscriptions.value = [];
    fetchPromise = null;
  });
}

export function useSubscription() {
  const subscriptions = sharedSubscriptions;
  const isLoading = sharedLoading;

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
        const data = result?.items || (result as unknown as SubscriptionOutput[]);
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

  async function refetchSubscriptions(): Promise<SubscriptionOutput[]> {
    sharedInitialized.value = false;
    sharedSubscriptions.value = [];
    fetchPromise = null;
    return fetchSubscriptions();
  }

  function hasActiveSubscription(productSlug: string): boolean {
    return sharedSubscriptions.value.some(
      (sub) =>
        sub.product_slug === productSlug && (sub.status === "active" || sub.status === "trialing"),
    );
  }

  function getSubscription(productSlug: string): SubscriptionOutput | undefined {
    return sharedSubscriptions.value.find((sub) => sub.product_slug === productSlug);
  }

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
