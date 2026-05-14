/**
 * useLedgerFilters — filter state management + URL query parameter sync.
 *
 * Provides reactive filter state that stays in sync with the browser URL.
 * On mount, initial filter values are read from URL query parameters.
 * On filter change, the URL is updated via `history.replaceState` so
 * users can bookmark or share filtered views.
 *
 * Designed to work with PaginationIn-based filter objects from Pinia CRUD
 * stores and the FilterBar / SearchInput components.
 *
 * Usage:
 *   const { filters, setFilter, setFilters, resetFilters, applyFilters }
 *     = useLedgerFilters<InstitutionFilter>({
 *       store: useInstitutionStore(),
 *       defaultFilters: { limit: 25, offset: 0 },
 *     });
 *
 *   // In template:
 *   <FilterBar :filters="filterConfigs" v-model="filters" @change="applyFilters" />
 */

import {
  ref,
  reactive,
  computed,
  watch,
  onMounted,
  onUnmounted,
  toRaw,
  type Ref,
  type ComputedRef,
  type UnwrapNestedRefs,
} from "vue";
import type { PaginationIn } from "@/lib/ledgerTypes";

// =============================================================================
// Types
// =============================================================================

/** Filter value types that can be serialized to URL query params. */
type FilterValue = string | number | boolean | null | undefined;

/**
 * Configuration for useLedgerFilters.
 *
 * @template TFilter - The filter type (must extend PaginationIn)
 */
export interface UseLedgerFiltersConfig<TFilter extends PaginationIn> {
  /** The Pinia CRUD store instance to sync filters with. */
  store: {
    filters: TFilter;
    setFilters: (partial: Partial<TFilter>) => void;
    resetFilters: () => void;
    fetchList: (filters?: Partial<TFilter>) => Promise<unknown>;
    total: number;
  };

  /** Default filter values (applied on reset and initial state). */
  defaultFilters: Partial<TFilter>;

  /**
   * Keys to sync with the URL query parameters.
   * If not provided, all non-pagination filter keys are synced.
   * Pagination keys (limit, offset) are always synced.
   */
  syncKeys?: (keyof TFilter)[];

  /**
   * URL param name prefix. Useful when multiple filter sets exist on one page.
   * E.g. prefix="bill" → ?bill_status=ACTIVE&bill_search=rent
   */
  paramPrefix?: string;

  /**
   * Whether to auto-apply filters on mount after reading URL params.
   * Default: true.
   */
  autoApplyOnMount?: boolean;

  /**
   * Debounce delay (ms) for auto-applying filters on reactive changes.
   * Set to 0 to disable debounced auto-apply.
   * Default: 0 (disabled — must call applyFilters() manually).
   */
  debounceMs?: number;
}

/** Return type of useLedgerFilters. */
export interface LedgerFilters<TFilter extends PaginationIn> {
  /** Reactive filter state. Mutate directly or use setFilter/setFilters. */
  filters: UnwrapNestedRefs<TFilter>;

  /**
   * Set a single filter value.
   * Does NOT trigger a fetch.
   *
   * @param key - Filter field name
   * @param value - New value
   */
  setFilter: (key: keyof TFilter, value: FilterValue) => void;

  /**
   * Merge partial filter values into the current filters.
   * Does NOT trigger a fetch.
   *
   * @param partial - Partial filter object to merge
   */
  setFilters: (partial: Partial<TFilter>) => void;

  /**
   * Reset all filters to their default values and apply (fetch).
   * Also clears URL params.
   */
  resetFilters: () => Promise<void>;

  /**
   * Apply the current filters by syncing to the store and fetching.
   * Also updates the URL query parameters.
   */
  applyFilters: () => Promise<void>;

  /**
   * Apply filters with a specific page number.
   * Convenience for: setFilter('offset', ...) + applyFilters().
   *
   * @param page - 1-based page number
   */
  applyPage: (page: number) => Promise<void>;

  /** Whether a fetch is in progress. */
  loading: Ref<boolean>;

  /** Whether any filter differs from its default value. */
  hasActiveFilters: ComputedRef<boolean>;

  /**
   * Get a URL query string representing the current filters.
   * Useful for "Share this view" or "Export filtered data" links.
   */
  toQueryString: () => string;
}

// =============================================================================
// Internal helpers
// =============================================================================

/** Pagination keys that are always synced. */
const PAGINATION_KEYS = new Set(["limit", "offset"]);

/**
 * Serialize a filter value to a string suitable for URL query params.
 * Returns undefined for null/undefined/empty string (these are omitted from the URL).
 */
function serializeFilterValue(value: FilterValue): string | undefined {
  if (value === null || value === undefined || value === "") return undefined;
  return String(value);
}

/**
 * Deserialize a URL query param string to a filter value.
 * Attempts to restore the original type (number, boolean, string).
 */
function deserializeFilterValue(value: string, defaultValue: FilterValue): FilterValue {
  // Try to match the type of the default value
  if (typeof defaultValue === "number") {
    const num = Number(value);
    return isNaN(num) ? value : num;
  }
  if (typeof defaultValue === "boolean") {
    return value === "true";
  }
  return value;
}

/** Build a param key with optional prefix. */
function paramKey(key: string, prefix?: string): string {
  return prefix ? `${prefix}_${key}` : key;
}

/** Remove prefix from a param key. */
function unprefixKey(prefixedKey: string, prefix?: string): string {
  if (!prefix) return prefixedKey;
  const prefixStr = `${prefix}_`;
  return prefixedKey.startsWith(prefixStr) ? prefixedKey.slice(prefixStr.length) : prefixedKey;
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Create reactive filter state with URL sync and store integration.
 *
 * @template TFilter - Filter type extending PaginationIn
 * @param config - Configuration object
 */
export function useLedgerFilters<TFilter extends PaginationIn>(
  config: UseLedgerFiltersConfig<TFilter>,
): LedgerFilters<TFilter> {
  const {
    store,
    defaultFilters,
    syncKeys,
    paramPrefix,
    autoApplyOnMount = true,
    debounceMs = 0,
  } = config;

  // ─── Reactive filter state ───────────────────────────────────────────────

  const filters = reactive({
    ...defaultFilters,
  }) as unknown as UnwrapNestedRefs<TFilter>;

  const loading = ref(false);

  // ─── Determine which keys to sync ────────────────────────────────────────

  const keysToSync = syncKeys ? new Set<keyof TFilter>([...syncKeys, "limit", "offset"]) : null; // null means sync all keys

  function shouldSyncKey(key: string): boolean {
    if (PAGINATION_KEYS.has(key)) return true;
    if (keysToSync) return keysToSync.has(key as keyof TFilter);
    return true;
  }

  // ─── URL read/write ─────────────────────────────────────────────────────

  /** Read filter values from the current URL query params. */
  function readFromUrl(): Partial<TFilter> {
    if (typeof window === "undefined") return {};

    const params = new URLSearchParams(window.location.search);
    const result: Record<string, FilterValue> = {};
    const defaults = defaultFilters as Record<string, FilterValue>;

    for (const [prefixedKey, value] of params.entries()) {
      const key = unprefixKey(prefixedKey, paramPrefix);
      if (!shouldSyncKey(key)) continue;
      result[key] = deserializeFilterValue(value, defaults[key] ?? "");
    }

    return result as Partial<TFilter>;
  }

  /** Write current filter values to the URL query params. */
  function writeToUrl(): void {
    if (typeof window === "undefined") return;

    const params = new URLSearchParams(window.location.search);
    const rawFilters = toRaw(filters) as Record<string, FilterValue>;

    // Get all current prefixed param keys so we can remove stale ones
    const keysToRemove = new Set<string>();
    for (const key of params.keys()) {
      const unprefixed = unprefixKey(key, paramPrefix);
      if (shouldSyncKey(unprefixed)) {
        keysToRemove.add(key);
      }
    }
    keysToRemove.forEach((k) => params.delete(k));

    // Add current filter values
    for (const [key, value] of Object.entries(rawFilters)) {
      if (!shouldSyncKey(key)) continue;
      const serialized = serializeFilterValue(value);
      if (serialized !== undefined) {
        params.set(paramKey(key, paramPrefix), serialized);
      }
    }

    const qs = params.toString();
    const newUrl = qs
      ? `${window.location.pathname}?${qs}${window.location.hash}`
      : `${window.location.pathname}${window.location.hash}`;

    // Use replaceState to avoid polluting browser history with every filter change
    window.history.replaceState(window.history.state, "", newUrl);
  }

  // ─── Filter mutation methods ─────────────────────────────────────────────

  function setFilter(key: keyof TFilter, value: FilterValue): void {
    (filters as Record<string, FilterValue>)[key as string] = value;
  }

  function setFilters(partial: Partial<TFilter>): void {
    for (const [key, value] of Object.entries(partial)) {
      (filters as Record<string, FilterValue>)[key] = value as FilterValue;
    }
  }

  // ─── Apply / fetch ──────────────────────────────────────────────────────

  async function applyFilters(): Promise<void> {
    // Sync to store
    store.setFilters(toRaw(filters) as Partial<TFilter>);

    // Update URL
    writeToUrl();

    // Fetch
    loading.value = true;
    try {
      await store.fetchList();
    } finally {
      loading.value = false;
    }
  }

  async function resetFilters(): Promise<void> {
    // Reset local reactive state
    for (const key of Object.keys(filters)) {
      delete (filters as Record<string, FilterValue>)[key];
    }
    Object.assign(filters, defaultFilters);

    // Reset store
    store.resetFilters();

    // Update URL
    writeToUrl();

    // Fetch
    loading.value = true;
    try {
      await store.fetchList();
    } finally {
      loading.value = false;
    }
  }

  async function applyPage(page: number): Promise<void> {
    const limit = ((filters as Record<string, FilterValue>).limit as number) ?? 25;
    const offset = Math.max(0, (page - 1) * limit);
    setFilter("offset" as keyof TFilter, offset);
    await applyFilters();
  }

  // ─── Computed helpers ───────────────────────────────────────────────────

  const hasActiveFilters = computed(() => {
    const raw = toRaw(filters) as Record<string, FilterValue>;
    const defaults = defaultFilters as Record<string, FilterValue>;

    for (const key of Object.keys(raw)) {
      if (PAGINATION_KEYS.has(key)) continue;
      const current = raw[key];
      const def = defaults[key];
      if (current !== def && current !== null && current !== undefined && current !== "") {
        return true;
      }
    }
    return false;
  });

  function toQueryString(): string {
    const raw = toRaw(filters) as Record<string, FilterValue>;
    const params = new URLSearchParams();

    for (const [key, value] of Object.entries(raw)) {
      const serialized = serializeFilterValue(value);
      if (serialized !== undefined) {
        params.set(paramKey(key, paramPrefix), serialized);
      }
    }

    return params.toString();
  }

  // ─── Debounced auto-apply (optional) ────────────────────────────────────

  let debounceTimer: ReturnType<typeof setTimeout> | null = null;

  if (debounceMs > 0) {
    watch(
      filters,
      () => {
        if (debounceTimer) clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          applyFilters();
        }, debounceMs);
      },
      { deep: true },
    );
  }

  // ─── Lifecycle: read URL on mount ───────────────────────────────────────

  onMounted(() => {
    const urlFilters = readFromUrl();
    if (Object.keys(urlFilters).length > 0) {
      Object.assign(filters, urlFilters);
    }

    if (autoApplyOnMount) {
      applyFilters();
    }
  });

  onUnmounted(() => {
    if (debounceTimer) {
      clearTimeout(debounceTimer);
      debounceTimer = null;
    }
  });

  return {
    filters,
    setFilter,
    setFilters,
    resetFilters,
    applyFilters,
    applyPage,
    loading,
    hasActiveFilters,
    toQueryString,
  };
}
