/**
 * useDropdownLoader — lazy-load dropdown data with caching.
 *
 * Provides a unified interface for loading dropdown data from multiple
 * Pinia CRUD stores. Results are cached so that repeated calls for the
 * same store return instantly. Useful in form components that need
 * dropdowns from several stores (e.g. institutions, accounts, categories, tags).
 *
 * Designed to work with Pinia CRUD stores built on the base.ts factory
 * and the CategoryTreeSelect, CurrencyInput, and other select components.
 *
 * Usage (single store):
 *   const { loadDropdown, getDropdown, isLoading }
 *     = useDropdownLoader();
 *
 *   await loadDropdown('institutions', useInstitutionStore());
 *   const institutions = getDropdown<InstitutionListOut>('institutions');
 *
 * Usage (multi-store, typical for forms):
 *   const loader = useDropdownLoader();
 *
 *   // Load all dropdowns needed for a transaction form
 *   await Promise.all([
 *     loader.loadDropdown('accounts', useAccountStore()),
 *     loader.loadDropdown('categories', useCategoryStore()),
 *     loader.loadDropdown('tags', useTagStore()),
 *   ]);
 *
 *   // Access loaded data
 *   const accounts = loader.getDropdown<AccountListOut>('accounts');
 *
 *   // In template:
 *   <select v-model="form.account_id">
 *     <option v-for="a in loader.getDropdown('accounts')" :value="a.id">
 *       {{ a.name }}
 *     </option>
 *   </select>
 */

import { reactive, ref, computed, type Ref } from "vue";

// =============================================================================
// Types
// =============================================================================

/** Dropdown data cache — maps store key to loaded data. */
type DropdownCache = Record<string, unknown[]>;

/**
 * Store interface that supports dropdown loading.
 * Matches the shape of Pinia CRUD stores built on base.ts.
 */
interface DropdownStore<TDropdown = unknown> {
  /** Fetch dropdown data from the API. */
  fetchDropdown: (forceRefresh?: boolean) => Promise<TDropdown[]>;
  /** Whether dropdown data has been loaded at least once. */
  dropdownLoaded: boolean;
  /** Cached dropdown data. */
  dropdown: TDropdown[];
}

/** Loading state for each dropdown key. */
type DropdownLoadingState = Record<string, boolean>;

/** Error state for each dropdown key. */
type DropdownErrorState = Record<string, string | null>;

/**
 * Configuration for useDropdownLoader.
 */
export interface UseDropdownLoaderConfig {
  /**
   * Whether to force-refresh all dropdowns on loadDropdown calls,
   * even if they've been loaded before.
   * Default: false (use cache).
   */
  forceRefresh?: boolean;
}

/** Return type of useDropdownLoader. */
export interface DropdownLoader {
  /**
   * Load dropdown data from a store.
   *
   * If the store has already loaded its dropdown data (dropdownLoaded=true)
   * and forceRefresh is false, returns the cached data immediately.
   * Otherwise, calls store.fetchDropdown() and caches the result.
   *
   * @template TDropdown - Dropdown item type
   * @param key - Unique key to identify this dropdown (e.g. 'institutions', 'accounts')
   * @param store - The Pinia CRUD store instance
   * @param forceRefresh - Override config-level forceRefresh for this call
   * @returns The dropdown data array
   */
  loadDropdown: <TDropdown = unknown>(
    key: string,
    store: DropdownStore<TDropdown>,
    forceRefresh?: boolean,
  ) => Promise<TDropdown[]>;

  /**
   * Get cached dropdown data by key.
   * Returns an empty array if not yet loaded.
   *
   * @template TDropdown - Dropdown item type
   * @param key - The dropdown key
   * @returns The dropdown data array
   */
  getDropdown: <TDropdown = unknown>(key: string) => TDropdown[];

  /**
   * Load multiple dropdowns in parallel.
   * Useful for form components that need several dropdowns.
   *
   * @param entries - Array of [key, store] pairs
   * @param forceRefresh - Override config-level forceRefresh for all calls
   * @returns Object mapping keys to their dropdown data
   */
  loadMultiple: <TDropdown = unknown>(
    entries: Array<[string, DropdownStore<TDropdown>]>,
    forceRefresh?: boolean,
  ) => Promise<Record<string, TDropdown[]>>;

  /**
   * Check if a specific dropdown has been loaded.
   *
   * @param key - The dropdown key
   * @returns True if the dropdown data is available
   */
  isLoaded: (key: string) => boolean;

  /**
   * Check if a specific dropdown is currently loading.
   *
   * @param key - The dropdown key
   * @returns True if the dropdown is being fetched
   */
  isLoading: (key: string) => boolean;

  /**
   * Get the error for a specific dropdown, if any.
   *
   * @param key - The dropdown key
   * @returns The error message or null
   */
  getError: (key: string) => string | null;

  /**
   * Invalidate a specific dropdown's cache.
   * The next loadDropdown call will fetch fresh data.
   *
   * @param key - The dropdown key
   */
  invalidate: (key: string) => void;

  /**
   * Invalidate all dropdown caches.
   */
  invalidateAll: () => void;

  /**
   * Whether any dropdown is currently loading.
   */
  anyLoading: Ref<boolean>;

  /**
   * List of all loaded dropdown keys.
   */
  loadedKeys: Ref<string[]>;
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Create a dropdown data loader with caching.
 *
 * @param config - Optional configuration
 */
export function useDropdownLoader(config: UseDropdownLoaderConfig = {}): DropdownLoader {
  const { forceRefresh: defaultForceRefresh = false } = config;

  // ─── State ──────────────────────────────────────────────────────────────

  /** Cache of loaded dropdown data, keyed by store name. */
  const cache = reactive<DropdownCache>({});

  /** Loading state per dropdown key. */
  const loadingState = reactive<DropdownLoadingState>({});

  /** Error state per dropdown key. */
  const errorState = reactive<DropdownErrorState>({});

  /** Set of keys that have been loaded at least once. */
  const loadedSet = reactive(new Set<string>());

  /** Ref version of loaded keys for reactivity in templates. */
  const loadedKeys = ref<string[]>([]);

  // ─── Loading ────────────────────────────────────────────────────────────

  async function loadDropdown<TDropdown = unknown>(
    key: string,
    store: DropdownStore<TDropdown>,
    forceRefresh?: boolean,
  ): Promise<TDropdown[]> {
    const shouldForce = forceRefresh ?? defaultForceRefresh;

    // Return cache if already loaded and not forcing refresh
    if (cache[key] && !shouldForce && store.dropdownLoaded) {
      return cache[key] as TDropdown[];
    }

    loadingState[key] = true;
    errorState[key] = null;

    try {
      const data = await store.fetchDropdown(shouldForce);
      cache[key] = data;
      loadedSet.add(key);
      loadedKeys.value = [...loadedSet];
      return data;
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : typeof err === "object" && err !== null && "message" in err
            ? String((err as Record<string, unknown>).message)
            : "Failed to load dropdown data";
      errorState[key] = message;
      return [];
    } finally {
      loadingState[key] = false;
    }
  }

  async function loadMultiple<TDropdown = unknown>(
    entries: Array<[string, DropdownStore<TDropdown>]>,
    forceRefresh?: boolean,
  ): Promise<Record<string, TDropdown[]>> {
    const results = await Promise.all(
      entries.map(([key, store]) =>
        loadDropdown<TDropdown>(key, store, forceRefresh).then((data) => [key, data] as const),
      ),
    );

    const resultObj: Record<string, TDropdown[]> = {};
    for (const [key, data] of results) {
      resultObj[key] = data;
    }
    return resultObj;
  }

  // ─── Accessors ──────────────────────────────────────────────────────────

  function getDropdown<TDropdown = unknown>(key: string): TDropdown[] {
    return (cache[key] ?? []) as TDropdown[];
  }

  function isLoaded(key: string): boolean {
    return loadedSet.has(key);
  }

  function isLoading(key: string): boolean {
    return loadingState[key] ?? false;
  }

  function getError(key: string): string | null {
    return errorState[key] ?? null;
  }

  // ─── Invalidation ──────────────────────────────────────────────────────

  function invalidate(key: string): void {
    delete cache[key];
    loadedSet.delete(key);
    loadedKeys.value = [...loadedSet];
    errorState[key] = null;
  }

  function invalidateAll(): void {
    for (const key of Object.keys(cache)) {
      delete cache[key];
    }
    loadedSet.clear();
    loadedKeys.value = [];

    for (const key of Object.keys(errorState)) {
      errorState[key] = null;
    }
  }

  // ─── Computed ──────────────────────────────────────────────────────────

  const anyLoading = computed(() => {
    return Object.values(loadingState).some((v) => v === true);
  });

  return {
    loadDropdown,
    getDropdown,
    loadMultiple,
    isLoaded,
    isLoading,
    getError,
    invalidate,
    invalidateAll,
    anyLoading,
    loadedKeys,
  };
}
