/**
 * useTransactions — shared transaction history state across Vue components.
 *
 * API-4 FIX: Provides a singleton composable for transaction history data,
 * eliminating duplicate getTransactionHistory() calls from multiple components.
 * Previously, BillingOverview, TransactionHistory, and BillingPage each fetched
 * transactions independently, wasting 1-2 API calls per billing page navigation.
 *
 * Now, all components share the same reactive state via window-level refs that
 * survive Astro View Transition module re-evaluations — the same pattern as
 * useAuth() and useSubscription().
 *
 * Features:
 * - Deduplicated fetching (multiple concurrent callers share one promise)
 * - Window-level singleton (survives module re-evaluation)
 * - Pagination support (has_more, starting_after cursor)
 * - Staleness-based refetch (STALE_THRESHOLD_MS, not unconditional clear)
 * - appendTransactions() for infinite-scroll / "load more"
 *
 * Usage:
 *   const { transactions, loading, hasMore, fetchTransactions, loadMore } = useTransactions();
 */

import { ref } from "vue";
import { billingApi } from "@/lib/billing";
import type { TransactionItemSchema } from "@/lib/billing";

// ─── Window-level shared state (survives module re-evaluation) ────────────

const SB_TXN_COMPOSABLE_KEY = "__sb_txn_composable";

// Staleness threshold: data older than this is considered stale and will be refetched.
// This prevents the "clear cache on every visit" problem (API-6 fix pattern).
const STALE_THRESHOLD_MS = 60_000; // 1 minute

interface SharedTxnState {
  // Vue reactive refs — stored on window so they survive module re-evaluation
  transactionsRef: any; // ref<TransactionItemSchema[]>
  loadingRef: any; // ref<boolean>
  initializedRef: any; // ref<boolean>
  hasMoreRef: any; // ref<boolean>
  currencyRef: any; // ref<string>

  // Plain data for deduplication (not reactive)
  fetchPromise: Promise<TransactionItemSchema[]> | null;
  lastFetchTime: number; // Timestamp of last successful fetch (for staleness check)
}

function getSharedTxnState(): SharedTxnState {
  if (typeof window === "undefined") {
    // SSR fallback
    return {
      transactionsRef: ref<TransactionItemSchema[]>([]),
      loadingRef: ref(false),
      initializedRef: ref(false),
      hasMoreRef: ref(false),
      currencyRef: ref("USD"),
      fetchPromise: null,
      lastFetchTime: 0,
    };
  }
  const win = window as any;
  if (!win[SB_TXN_COMPOSABLE_KEY]) {
    win[SB_TXN_COMPOSABLE_KEY] = {
      // Create Vue refs ONCE and store on window
      transactionsRef: ref<TransactionItemSchema[]>([]),
      loadingRef: ref(false),
      initializedRef: ref(false),
      hasMoreRef: ref(false),
      currencyRef: ref("USD"),
      // Plain data
      fetchPromise: null,
      lastFetchTime: 0,
    };
  }
  return win[SB_TXN_COMPOSABLE_KEY];
}

// Recover shared refs from window (or create new ones for SSR)
const sharedState = getSharedTxnState();
const sharedTransactions = sharedState.transactionsRef as import("vue").Ref<
  TransactionItemSchema[]
>;
const sharedLoading = sharedState.loadingRef as import("vue").Ref<boolean>;
const sharedInitialized =
  sharedState.initializedRef as import("vue").Ref<boolean>;
const sharedHasMore = sharedState.hasMoreRef as import("vue").Ref<boolean>;
const sharedCurrency = sharedState.currencyRef as import("vue").Ref<string>;

export function useTransactions() {
  const transactions = sharedTransactions;
  const loading = sharedLoading;
  const hasMore = sharedHasMore;
  const currency = sharedCurrency;

  /**
   * Check if the cached data is stale (older than STALE_THRESHOLD_MS).
   * Returns true if data should be refetched, false if still fresh.
   */
  function isStale(): boolean {
    const ws = getSharedTxnState();
    return Date.now() - ws.lastFetchTime > STALE_THRESHOLD_MS;
  }

  /**
   * Fetch transactions from the API. Deduplicates concurrent calls.
   *
   * Returns cached data if still fresh. Use refetchTransactions() to
   * force a fresh API call regardless of staleness.
   */
  async function fetchTransactions(): Promise<TransactionItemSchema[]> {
    // Return cached data if fresh (not stale)
    if (
      sharedInitialized.value &&
      sharedTransactions.value.length > 0 &&
      !isStale()
    ) {
      return sharedTransactions.value;
    }

    const ws = getSharedTxnState();
    if (ws.fetchPromise) return ws.fetchPromise;

    ws.fetchPromise = (async () => {
      sharedLoading.value = true;
      try {
        const data = await billingApi.getTransactionHistory(25);
        sharedTransactions.value = data.transactions;
        sharedHasMore.value = data.has_more;
        sharedCurrency.value = data.currency;
        sharedInitialized.value = true;
        ws.lastFetchTime = Date.now();
        return data.transactions;
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
   * Load more transactions (pagination). Appends to the existing list.
   * Uses the last transaction ID as a cursor (starting_after).
   */
  async function loadMore(): Promise<TransactionItemSchema[]> {
    if (!sharedHasMore.value) return [];

    const lastId =
      sharedTransactions.value[sharedTransactions.value.length - 1]?.id;
    if (!lastId) return [];

    sharedLoading.value = true;
    try {
      const data = await billingApi.getTransactionHistory(25, lastId);
      sharedTransactions.value = [
        ...sharedTransactions.value,
        ...data.transactions,
      ];
      sharedHasMore.value = data.has_more;
      sharedCurrency.value = data.currency;
      return data.transactions;
    } catch {
      return [];
    } finally {
      sharedLoading.value = false;
    }
  }

  /**
   * Force a fresh fetch from the API — clears cache first.
   * Use after checkout, payment, or other billing operations.
   */
  async function refetchTransactions(): Promise<TransactionItemSchema[]> {
    sharedInitialized.value = false;
    sharedTransactions.value = [];
    sharedHasMore.value = false;
    const ws = getSharedTxnState();
    ws.fetchPromise = null;
    ws.lastFetchTime = 0;
    return fetchTransactions();
  }

  /**
   * Invalidate cached transactions — forces fresh fetch on next call.
   * Lighter than refetchTransactions() — doesn't trigger an immediate fetch.
   */
  function invalidateTransactions(): void {
    const ws = getSharedTxnState();
    sharedInitialized.value = false;
    ws.lastFetchTime = 0;
  }

  return {
    transactions,
    loading,
    hasMore,
    currency,
    initialized: sharedInitialized,
    fetchTransactions,
    loadMore,
    refetchTransactions,
    invalidateTransactions,
  };
}
