/**
 * useSubscription — shared subscription state across Vue components.
 *
 * Provides reactive subscription data fetched once and shared across all
 * dashboard components. Eliminates duplicate getSubscriptions() calls from
 * DashboardHome, BillingOverview, PlanComparison, and ProfileCard.
 *
 * API-6 FIX: Added staleness-based refetch. Previously, refetchSubscriptions()
 * unconditionally cleared the cache and re-fetched, even if data was fresh.
 * Now, fetchSubscriptions() checks staleness and only fetches if data is
 * older than STALE_THRESHOLD_MS. refetchSubscriptions() still forces a
 * fresh fetch for explicit invalidation (after cancel, reactivate, etc.).
 *
 * CRITICAL FIX: Vue ref() objects created at module level are destroyed
 * when the module is re-evaluated by Astro View Transitions (VM#### contexts).
 * We now store the reactive state on the window object so it persists across
 * module re-evaluations. On re-evaluation, we recover the existing refs from
 * window instead of creating new ones.
 *
 * Usage:
 *   const { subscriptions, loading, fetchSubscriptions, refetchSubscriptions } = useSubscription();
 */

import { ref } from "vue";
import { billingApi } from "@/lib/billing";
import type { SubscriptionOutputSchema } from "@/lib/billing";

// ─── Window-level shared state (survives module re-evaluation) ────────────

const SB_SUB_COMPOSABLE_KEY = "__sb_sub_composable";

// API-6 FIX: Staleness threshold — data older than this is considered stale.
// fetchSubscriptions() will return cached data if fresh; refetchSubscriptions()
// always forces a fresh fetch (for after cancel/reactivate/checkout).
const STALE_THRESHOLD_MS = 60_000; // 1 minute

interface SharedSubState {
  // Vue reactive refs — stored on window so they survive module re-evaluation
  subscriptionsRef: any; // ref<SubscriptionOutputSchema[]>
  loadingRef: any; // ref<boolean>
  initializedRef: any; // ref<boolean>

  // Plain data for deduplication (not reactive)
  fetchPromise: Promise<SubscriptionOutputSchema[]> | null;
  lastFetchTime: number; // API-6: Timestamp of last successful fetch
}

function getSharedSubState(): SharedSubState {
  if (typeof window === "undefined") {
    // SSR fallback
    return {
      subscriptionsRef: ref<SubscriptionOutputSchema[]>([]),
      loadingRef: ref(false),
      initializedRef: ref(false),
      fetchPromise: null,
      lastFetchTime: 0,
    };
  }
  const win = window as any;
  if (!win[SB_SUB_COMPOSABLE_KEY]) {
    win[SB_SUB_COMPOSABLE_KEY] = {
      // Create Vue refs ONCE and store on window
      subscriptionsRef: ref<SubscriptionOutputSchema[]>([]),
      loadingRef: ref(false),
      initializedRef: ref(false),
      // Plain data
      fetchPromise: null,
      lastFetchTime: 0,
    };
  }
  return win[SB_SUB_COMPOSABLE_KEY];
}

// Recover shared refs from window (or create new ones for SSR)
const sharedState = getSharedSubState();
const sharedSubscriptions = sharedState.subscriptionsRef as import("vue").Ref<
  SubscriptionOutputSchema[]
>;
const sharedLoading = sharedState.loadingRef as import("vue").Ref<boolean>;
const sharedInitialized =
  sharedState.initializedRef as import("vue").Ref<boolean>;

export function useSubscription() {
  const subscriptions = sharedSubscriptions;
  const loading = sharedLoading;

  /**
   * Fetch subscriptions. Deduplicates concurrent calls — if multiple components
   * call fetchSubscriptions() simultaneously, only one API request is made
   * and all get the same result.
   *
   * API-6 FIX: Returns cached subscriptions if already loaded AND still fresh
   * (within STALE_THRESHOLD_MS). Use refetchSubscriptions() to force a fresh
   * fetch (e.g. after plan change or checkout).
   */
  async function fetchSubscriptions(): Promise<SubscriptionOutputSchema[]> {
    // API-6 FIX: Return cached data if initialized and not stale
    const ws = getSharedSubState();
    const isDataStale = Date.now() - ws.lastFetchTime > STALE_THRESHOLD_MS;

    if (
      sharedInitialized.value &&
      sharedSubscriptions.value.length > 0 &&
      !isDataStale
    ) {
      return sharedSubscriptions.value;
    }

    if (ws.fetchPromise) return ws.fetchPromise;

    ws.fetchPromise = (async () => {
      sharedLoading.value = true;
      try {
        const data = await billingApi.getSubscriptions();
        sharedSubscriptions.value = data;
        sharedInitialized.value = true;
        ws.lastFetchTime = Date.now(); // API-6: Track fetch time for staleness
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
   * Force a fresh fetch from the API — clears cache first.
   * Use after plan changes, checkouts, cancels, reactivations, etc.
   */
  async function refetchSubscriptions(): Promise<SubscriptionOutputSchema[]> {
    sharedInitialized.value = false;
    sharedSubscriptions.value = [];
    const ws = getSharedSubState();
    ws.fetchPromise = null;
    ws.lastFetchTime = 0; // API-6: Reset staleness tracking
    return fetchSubscriptions();
  }

  /**
   * Invalidate cached subscriptions — forces fresh fetch on next call.
   */
  function invalidateSubscriptions(): void {
    sharedInitialized.value = false;
  }

  return {
    subscriptions,
    loading,
    initialized: sharedInitialized,
    fetchSubscriptions,
    refetchSubscriptions,
    invalidateSubscriptions,
  };
}
