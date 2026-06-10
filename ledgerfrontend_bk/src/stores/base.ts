/**
 * Pinia Store Base — src/stores/base.ts
 *
 * Shared store patterns for all 15+ Ledger domain CRUD stores.
 * Provides composable state, getters, and action factories that
 * domain stores spread into their own `defineStore()` call.
 *
 * Architecture:
 *   ┌───────────────────────────────────────────────────────┐
 *   │  crudState<T, F, D>()      → initial state properties │
 *   │  crudActions<T, C, U, F>() → standard CRUD methods    │
 *   │  defineCrudStore<...>()     → convenience factory      │
 *   └───────────────────────────────────────────────────────┘
 *
 *   Domain stores compose the base with their own extras:
 *
 *   export const useInstitutionStore = defineStore('institution', {
 *     state: () => ({
 *       ...crudState<InstitutionOut, InstitutionFilter, InstitutionListOut>(),
 *       // ← domain-specific extra state goes here
 *     }),
 *     getters: {
 *       ...crudGetters<InstitutionOut>(),
 *       // ← domain-specific extra getters go here
 *     },
 *     actions: {
 *       ...crudActions<InstitutionOut, InstitutionCreate, InstitutionUpdate, InstitutionFilter>({
 *         api: { list, get, create, update, remove, restore, ... },
 *       }),
 *       // ← domain-specific extra actions go here
 *     },
 *   });
 *
 * For simple stores with no domain-specific additions, use the
 * convenience factory:
 *
 *   export const useInstitutionStore = defineCrudStore({
 *     storeId: 'institution',
 *     api: { list, get, create, update, remove, restore, ... },
 *   });
 */

import { defineStore } from "pinia";
import type { PaginationIn, PaginatedResponse, MessageOut } from "@/lib/ledgerTypes";
import type { ApiError } from "@/lib/types";
import { useToast } from "@/composables/useToast";

// =============================================================================
// Constants
// =============================================================================

/** Default staleness threshold — data older than this is considered stale. */
const DEFAULT_STALE_THRESHOLD_MS = 5 * 60 * 1000; // 5 minutes

/** Default page size when no filter is provided. */
const DEFAULT_PAGE_SIZE = 25;

// =============================================================================
// Type Definitions
// =============================================================================

/**
 * Standard state shape for all Ledger CRUD stores.
 *
 * @template T       - Full entity type (e.g. InstitutionOut)
 * @template TFilter - Filter/query params type (e.g. InstitutionFilter)
 * @template TDropdown - Dropdown item type (e.g. InstitutionListOut)
 */
export interface CrudStoreState<
  T extends { id: number },
  TFilter extends PaginationIn = PaginationIn,
  TDropdown = { id: number; [key: string]: unknown },
> {
  /** Paginated list of items from the last `fetchList` call. */
  items: T[];
  /** Currently selected/viewed item (from `fetchOne`). */
  current: T | null;
  /** True when any async operation is in progress. */
  loading: boolean;
  /** Which action is currently loading (e.g. 'fetchList', 'create', 'update'). */
  loadingAction: string;
  /** General error message from the last failed operation. */
  error: string | null;
  /** Field-level validation errors from the API (Django Ninja format). */
  fieldErrors: Record<string, string[]>;
  /** Total item count from the last paginated list response. */
  total: number;
  /** Current filter state for list queries. */
  filters: TFilter;
  /** Cached dropdown data (lightweight items for selects/autocompletes). */
  dropdown: TDropdown[];
  /** Whether dropdown data has been loaded at least once. */
  dropdownLoaded: boolean;
  /** Whether the main list has been loaded at least once. */
  listLoaded: boolean;
  /** Timestamp (ms) of the last successful `fetchList` call. */
  lastFetched: number | null;
}

/**
 * API adapter that the store factory uses to call the backend.
 *
 * Each domain store provides a typed adapter mapping to the
 * corresponding `ledgerApi.xxx` methods. Optional methods (restore,
 * dropdown, activate, deactivate) are only provided when the
 * backend supports them for that entity.
 *
 * @template T       - Full entity type
 * @template TCreate - Request body for POST
 * @template TUpdate - Request body for PATCH
 * @template TFilter - Query params for list
 */
export interface CrudApiAdapter<T, TCreate, TUpdate, TFilter extends PaginationIn = PaginationIn> {
  /** List items with pagination and filters. */
  list: (filters?: TFilter) => Promise<PaginatedResponse<T>>;
  /** Get a single item by ID. */
  get: (id: number) => Promise<T>;
  /** Create a new item. */
  create: (data: TCreate) => Promise<T>;
  /** Update an existing item (partial). */
  update: (id: number, data: TUpdate) => Promise<T>;
  /** Soft-delete an item. */
  remove: (id: number) => Promise<MessageOut>;
  /** Restore a soft-deleted item. Optional — not all entities support restore. */
  restore?: (id: number) => Promise<MessageOut>;
  /** Fetch lightweight dropdown data. Optional — not all entities have /dropdown. */
  dropdown?: () => Promise<unknown[]>;
  /** Activate an item. Optional — only ActivatableModel entities. */
  activate?: (id: number) => Promise<MessageOut>;
  /** Deactivate an item. Optional — only ActivatableModel entities. */
  deactivate?: (id: number) => Promise<MessageOut>;
}

/**
 * Configuration for the CRUD store factory.
 *
 * @template T       - Full entity type
 * @template TCreate - Create request type
 * @template TUpdate - Update request type
 * @template TFilter - Filter/query params type
 */
export interface CrudStoreConfig<
  T extends { id: number },
  TCreate,
  TUpdate,
  TFilter extends PaginationIn = PaginationIn,
> {
  /** Unique Pinia store ID (e.g. 'institution', 'account'). */
  storeId: string;
  /** API adapter with typed endpoint methods. */
  api: CrudApiAdapter<T, TCreate, TUpdate, TFilter>;
  /** Default filter values applied on reset and initial state. */
  defaultFilters?: Partial<TFilter>;
  /** Staleness threshold in ms. Data older than this is considered stale. */
  staleThresholdMs?: number;
  /** Toast messages for CRUD mutations. Set to false to disable toasts for a given action. */
  toastMessages?: Partial<{
    created: string | false;
    updated: string | false;
    removed: string | false;
    restored: string | false;
    activated: string | false;
    deactivated: string | false;
  }>;
}

// ─── Utility Types ────────────────────────────────────────────────────────────

/** Extract the entity type from a CrudStoreState. */
export type StoreEntity<S> = S extends CrudStoreState<infer T, any, any> ? T : never;

/** Extract the filter type from a CrudStoreState. */
export type StoreFilter<S> = S extends CrudStoreState<any, infer F, any> ? F : never;

/** Extract the dropdown item type from a CrudStoreState. */
export type StoreDropdown<S> = S extends CrudStoreState<any, any, infer D> ? D : never;

// =============================================================================
// State Factory
// =============================================================================

/**
 * Create the initial state object for a CRUD store.
 *
 * Spread the result into your `defineStore` state function:
 *
 *   state: () => ({
 *     ...crudState<InstitutionOut, InstitutionFilter, InstitutionListOut>(),
 *     myExtraField: null,
 *   }),
 *
 * @template T        - Full entity type (e.g. InstitutionOut)
 * @template TFilter  - Filter/query params type (e.g. InstitutionFilter)
 * @template TDropdown - Dropdown item type (e.g. InstitutionListOut)
 * @param defaultFilters - Optional default filter values
 */
export function crudState<
  T extends { id: number },
  TFilter extends PaginationIn = PaginationIn,
  TDropdown = { id: number; [key: string]: unknown },
>(defaultFilters?: Partial<TFilter>): CrudStoreState<T, TFilter, TDropdown> {
  return {
    items: [],
    current: null,
    loading: false,
    loadingAction: "",
    error: null,
    fieldErrors: {},
    total: 0,
    filters: (defaultFilters ?? {}) as TFilter,
    dropdown: [],
    dropdownLoaded: false,
    listLoaded: false,
    lastFetched: null,
  };
}

// =============================================================================
// Getters Factory
// =============================================================================

/**
 * Create standard getter definitions for a CRUD store.
 *
 * Spread the result into your `defineStore` getters:
 *
 *   getters: {
 *     ...crudGetters<InstitutionOut>(),
 *     myCustomGetter: (state) => ...,
 *   },
 *
 * Provided getters:
 *   - activeItems   → items where is_active is not false
 *   - hasItems      → items array is not empty
 *   - hasError      → error is set
 *   - hasFieldErrors → field-level validation errors exist
 *   - isStale       → data is older than the staleness threshold
 *   - totalPages    → computed page count based on total and limit
 *   - currentPage   → current page number (1-based)
 *
 * @template T - Full entity type
 * @param staleThreshold - Staleness threshold in ms (default 5 min)
 */
export function crudGetters<T extends { id: number; is_active?: boolean; is_deleted?: boolean }>(
  staleThreshold = DEFAULT_STALE_THRESHOLD_MS,
) {
  return {
    /** Items filtered to only those with is_active !== false. */
    activeItems: (state: CrudStoreState<T>) => state.items.filter((i) => i.is_active !== false),

    /** Whether the items list has at least one item. */
    hasItems: (state: CrudStoreState<T>) => state.items.length > 0,

    /** Whether an error message is set. */
    hasError: (state: CrudStoreState<T>) => state.error !== null,

    /** Whether field-level validation errors exist. */
    hasFieldErrors: (state: CrudStoreState<T>) => Object.keys(state.fieldErrors).length > 0,

    /** Whether the loaded data is stale (older than threshold). */
    isStale: (state: CrudStoreState<T>) => {
      if (!state.lastFetched) return true;
      return Date.now() - state.lastFetched > staleThreshold;
    },

    /** Total number of pages based on current total and filter limit. */
    totalPages: (state: CrudStoreState<T>) => {
      const limit = (state.filters as PaginationIn).limit ?? DEFAULT_PAGE_SIZE;
      return Math.ceil(state.total / limit);
    },

    /** Current page number (1-based) derived from offset and limit. */
    currentPage: (state: CrudStoreState<T>) => {
      const limit = (state.filters as PaginationIn).limit ?? DEFAULT_PAGE_SIZE;
      const offset = (state.filters as PaginationIn).offset ?? 0;
      return Math.floor(offset / limit) + 1;
    },
  };
}

// =============================================================================
// Actions Factory
// =============================================================================

/**
 * Create standard CRUD action methods for a store.
 *
 * Spread the result into your `defineStore` actions:
 *
 *   actions: {
 *     ...crudActions<InstitutionOut, InstitutionCreate, InstitutionUpdate, InstitutionFilter>({
 *       api: { list, get, create, update, remove, restore, ... },
 *     }),
 *     myCustomAction() { ... },
 *   },
 *
 * Provided actions:
 *   Data Fetching:
 *     - fetchList(filters?)       → paginated list with filter merge
 *     - fetchOne(id)              → single item → sets current
 *     - fetchDropdown(force?)     → cached dropdown data
 *     - refreshIfStale()          → refetch only if data is stale
 *
 *   CRUD Mutations:
 *     - create(data)              → POST + prepend to items
 *     - update(id, data)          → PATCH + update in items & current
 *     - remove(id)                → DELETE + remove from items
 *     - restore(id)               → POST /restore (if supported)
 *
 *   Status Toggles:
 *     - activate(id)              → POST /activate + optimistic update
 *     - deactivate(id)            → POST /deactivate + optimistic update
 *
 *   State Helpers:
 *     - clearError()              → reset error + fieldErrors
 *     - clearCurrent()            → set current to null
 *     - clearFieldErrors()        → reset fieldErrors only
 *     - setFilters(partial)       → merge filters
 *     - resetFilters()            → reset to defaults
 *     - setPage(page)             → set offset from 1-based page number
 *     - invalidate()              → mark list & dropdown as not loaded
 *     - $resetCrud()              → full state reset
 *
 * @template T        - Full entity type
 * @template TCreate  - Create request type
 * @template TUpdate  - Update request type
 * @template TFilter  - Filter/query params type
 * @template TDropdown - Dropdown item type
 * @param config - Store configuration with API adapter and defaults
 */
export function crudActions<
  T extends { id: number; is_active?: boolean; is_deleted?: boolean },
  TCreate,
  TUpdate,
  TFilter extends PaginationIn = PaginationIn,
  TDropdown = { id: number; [key: string]: unknown },
>(config: CrudStoreConfig<T, TCreate, TUpdate, TFilter>) {
  const { api, defaultFilters, staleThresholdMs, toastMessages, storeId } = config;
  const staleThreshold = staleThresholdMs ?? DEFAULT_STALE_THRESHOLD_MS;

  // ── Toast helper ──────────────────────────────────────────────────────────

  /** Show a success toast if the message is enabled (not false). */
  function showToast(
    type: keyof NonNullable<CrudStoreConfig<T, TCreate, TUpdate, TFilter>["toastMessages"]>,
    fallback: string,
  ) {
    const msg = toastMessages?.[type];
    if (msg === false) return; // explicitly disabled
    try {
      const toast = useToast();
      toast.success(msg ?? fallback);
    } catch {
      // Toast store not initialized yet (e.g. during SSR) — silently skip
    }
  }

  return {
    // ─── Data Fetching ──────────────────────────────────────────────

    /**
     * Fetch a paginated list of items.
     *
     * Merges provided filters with the current store filters.
     * Updates items, total, and listLoaded state.
     * Sets lastFetched timestamp for staleness tracking.
     *
     * @param filters - Optional filters to merge/override current filters
     * @returns The full paginated response
     */
    async fetchList(filters?: Partial<TFilter>) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loading = true;
      self.loadingAction = "fetchList";
      self.error = null;
      self.fieldErrors = {};

      try {
        const appliedFilters = {
          ...self.filters,
          ...filters,
        } as TFilter;
        const response = await api.list(appliedFilters);

        self.items = response.items;
        self.total = response.pagination.total;
        self.filters = appliedFilters;
        self.listLoaded = true;
        self.lastFetched = Date.now();

        return response;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        self.fieldErrors = extractFieldErrors(err);
        throw err;
      } finally {
        self.loading = false;
        self.loadingAction = "";
      }
    },

    /**
     * Fetch a single item by ID and set it as `current`.
     *
     * Also updates the item in the `items` list if it exists there,
     * ensuring list views stay in sync with detail views.
     *
     * @param id - The item's primary key
     * @returns The fetched entity
     */
    async fetchOne(id: number) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loading = true;
      self.loadingAction = "fetchOne";
      self.error = null;
      self.fieldErrors = {};

      try {
        const item = await api.get(id);
        self.current = item;

        // Also update in the items list if present
        const idx = self.items.findIndex((i) => i.id === id);
        if (idx !== -1) {
          self.items[idx] = item;
        }

        return item;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        self.fieldErrors = extractFieldErrors(err);
        throw err;
      } finally {
        self.loading = false;
        self.loadingAction = "";
      }
    },

    /**
     * Fetch dropdown data for selects and autocompletes.
     *
     * Results are cached — subsequent calls return the cached data
     * unless `forceRefresh` is true. This avoids redundant API calls
     * when multiple components on the same page need dropdown data.
     *
     * @param forceRefresh - Bypass the cache and re-fetch from API
     * @returns The dropdown items array
     */
    async fetchDropdown(forceRefresh = false) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      if (!api.dropdown) return [];

      if (self.dropdownLoaded && !forceRefresh) {
        return self.dropdown;
      }

      self.loadingAction = "fetchDropdown";

      try {
        const data = await api.dropdown();
        self.dropdown = data as TDropdown[];
        self.dropdownLoaded = true;
        return data;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        throw err;
      } finally {
        self.loadingAction = "";
      }
    },

    /**
     * Conditionally refetch the list if data is stale.
     *
     * Useful when navigating to a list page that was previously loaded —
     * avoids a loading flash if the data is fresh, but ensures the user
     * sees up-to-date data after background changes.
     *
     * @returns The fetchList response if refetched, or null if data is fresh
     */
    async refreshIfStale() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      if (!self.listLoaded || !self.lastFetched) {
        return this.fetchList();
      }
      if (Date.now() - self.lastFetched > staleThreshold) {
        window?.dispatchEvent(new CustomEvent("ledger:refresh-start"));
        try {
          return await this.fetchList();
        } finally {
          window?.dispatchEvent(new CustomEvent("ledger:refresh-end"));
        }
      }
      return null;
    },

    // ─── CRUD Mutations ─────────────────────────────────────────────

    /**
     * Create a new item.
     *
     * On success, the new item is prepended to the items list
     * and the total count is incremented. This gives immediate
     * feedback in list views without requiring a full refetch.
     *
     * @param data - The create request body
     * @returns The newly created entity
     */
    async create(data: TCreate) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loading = true;
      self.loadingAction = "create";
      self.error = null;
      self.fieldErrors = {};

      try {
        const item = await api.create(data);
        self.items.unshift(item);
        self.total += 1;
        showToast(
          "created",
          `${storeId.charAt(0).toUpperCase() + storeId.slice(1)} created successfully`,
        );
        return item;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        self.fieldErrors = extractFieldErrors(err);
        throw err;
      } finally {
        self.loading = false;
        self.loadingAction = "";
      }
    },

    /**
     * Update an existing item (partial update).
     *
     * On success, the item is updated both in the `items` list
     * and in `current` (if it matches the updated ID). This
     * ensures both list and detail views reflect the change.
     *
     * @param id   - The item's primary key
     * @param data - The partial update body
     * @returns The updated entity
     */
    async update(id: number, data: TUpdate) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loading = true;
      self.loadingAction = "update";
      self.error = null;
      self.fieldErrors = {};

      try {
        const item = await api.update(id, data);

        // Update in list
        const idx = self.items.findIndex((i) => i.id === id);
        if (idx !== -1) {
          self.items[idx] = item;
        }

        // Update current if viewing this item
        if (self.current?.id === id) {
          self.current = item;
        }

        showToast(
          "updated",
          `${storeId.charAt(0).toUpperCase() + storeId.slice(1)} updated successfully`,
        );
        return item;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        self.fieldErrors = extractFieldErrors(err);
        throw err;
      } finally {
        self.loading = false;
        self.loadingAction = "";
      }
    },

    /**
     * Soft-delete an item.
     *
     * On success, the item is removed from the `items` list
     * and the total count is decremented. If the deleted item
     * is the current one, `current` is cleared.
     *
     * The backend keeps the record (is_deleted=true) so it can
     * be restored with `restore()`.
     *
     * @param id - The item's primary key
     * @returns The MessageOut response from the API
     */
    async remove(id: number) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loadingAction = "remove";
      self.error = null;

      try {
        const result = await api.remove(id);

        // Remove from items list
        self.items = self.items.filter((i) => i.id !== id);
        self.total = Math.max(0, self.total - 1);

        // Clear current if it was the deleted item
        if (self.current?.id === id) {
          self.current = null;
        }

        showToast("removed", `${storeId.charAt(0).toUpperCase() + storeId.slice(1)} deleted`);
        return result;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        throw err;
      } finally {
        self.loadingAction = "";
      }
    },

    /**
     * Restore a soft-deleted item.
     *
     * The item is restored on the backend (is_deleted=false).
     * After restore, call `fetchList()` or `fetchOne()` to
     * refresh the view with the restored item.
     *
     * Only available for entities with SoftDeleteModel.
     *
     * @param id - The item's primary key
     * @returns The MessageOut response from the API
     */
    async restore(id: number) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loadingAction = "restore";
      self.error = null;

      try {
        const result = api.restore
          ? await api.restore(id)
          : ({ detail: "Restore not supported" } as MessageOut);
        showToast("restored", `${storeId.charAt(0).toUpperCase() + storeId.slice(1)} restored`);
        return result;
      } catch (err: unknown) {
        self.error = extractErrorMessage(err);
        throw err;
      } finally {
        self.loadingAction = "";
      }
    },

    // ─── Status Toggles ─────────────────────────────────────────────

    /**
     * Activate an item.
     *
     * On success, `is_active` is optimistically set to true
     * in both the `items` list and `current`. If the API call
     * fails, the state is reverted by refetching the item.
     *
     * Only available for entities with ActivatorModel.
     *
     * @param id - The item's primary key
     * @returns The MessageOut response from the API
     */
    async activate(id: number) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loadingAction = "activate";
      self.error = null;

      // Optimistic update
      const item = self.items.find((i) => i.id === id);
      if (item) (item as Record<string, unknown>).is_active = true;
      const wasCurrent = self.current?.id === id;
      if (wasCurrent) (self.current as Record<string, unknown>).is_active = true;

      try {
        const result = api.activate
          ? await api.activate(id)
          : ({ detail: "Activate not supported" } as MessageOut);
        showToast("activated", `${storeId.charAt(0).toUpperCase() + storeId.slice(1)} activated`);
        return result;
      } catch (err: unknown) {
        // Revert optimistic update
        if (item) (item as Record<string, unknown>).is_active = false;
        if (wasCurrent) (self.current as Record<string, unknown>).is_active = false;
        self.error = extractErrorMessage(err);
        throw err;
      } finally {
        self.loadingAction = "";
      }
    },

    /**
     * Deactivate an item.
     *
     * On success, `is_active` is optimistically set to false
     * in both the `items` list and `current`. If the API call
     * fails, the state is reverted.
     *
     * Only available for entities with ActivatorModel.
     *
     * @param id - The item's primary key
     * @returns The MessageOut response from the API
     */
    async deactivate(id: number) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.loadingAction = "deactivate";
      self.error = null;

      // Optimistic update
      const item = self.items.find((i) => i.id === id);
      if (item) (item as Record<string, unknown>).is_active = false;
      const wasCurrent = self.current?.id === id;
      if (wasCurrent) (self.current as Record<string, unknown>).is_active = false;

      try {
        const result = api.deactivate
          ? await api.deactivate(id)
          : ({ detail: "Deactivate not supported" } as MessageOut);
        showToast(
          "deactivated",
          `${storeId.charAt(0).toUpperCase() + storeId.slice(1)} deactivated`,
        );
        return result;
      } catch (err: unknown) {
        // Revert optimistic update
        if (item) (item as Record<string, unknown>).is_active = true;
        if (wasCurrent) (self.current as Record<string, unknown>).is_active = true;
        self.error = extractErrorMessage(err);
        throw err;
      } finally {
        self.loadingAction = "";
      }
    },

    // ─── State Management Helpers ───────────────────────────────────

    /** Clear the current error message and field-level errors. */
    clearError() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.error = null;
      self.fieldErrors = {};
    },

    /** Clear the currently selected item (set current to null). */
    clearCurrent() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.current = null;
    },

    /** Clear only the field-level validation errors. */
    clearFieldErrors() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.fieldErrors = {};
    },

    /**
     * Partially update the current filters.
     *
     * Does NOT trigger a fetch — call `fetchList()` after setting
     * filters to apply them.
     *
     * @param filters - Partial filter object to merge into current filters
     */
    setFilters(filters: Partial<TFilter>) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.filters = { ...self.filters, ...filters } as TFilter;
    },

    /**
     * Reset filters to the store's default values.
     *
     * Does NOT trigger a fetch — call `fetchList()` to apply.
     */
    resetFilters() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.filters = (defaultFilters ?? {}) as TFilter;
    },

    /**
     * Set the current page by page number (1-based).
     *
     * Calculates the offset from the page number and the current
     * limit (from filters). Does NOT trigger a fetch.
     *
     * @param page - 1-based page number
     */
    setPage(page: number) {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      const limit = (self.filters as PaginationIn).limit ?? DEFAULT_PAGE_SIZE;
      const offset = Math.max(0, (page - 1) * limit);
      self.filters = { ...self.filters, limit, offset } as TFilter;
    },

    /**
     * Invalidate cached data so the next access triggers a fresh fetch.
     *
     * Marks both the list and dropdown as not loaded, and clears
     * the lastFetched timestamp. Useful after mutations that change
     * server-side state (e.g. bulk operations).
     */
    invalidate() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.listLoaded = false;
      self.dropdownLoaded = false;
      self.lastFetched = null;
    },

    /**
     * Full state reset — clears all items, current, errors, and filters.
     *
     * Returns the store to its initial empty state. Use this when
     * navigating away from a detail page or when the user signs out.
     * Pinia's built-in `$reset()` also works, but this method is
     * more explicit about what it resets for CRUD stores.
     */
    $resetCrud() {
      const self = this as unknown as CrudStoreState<T, TFilter, TDropdown>;
      self.items = [];
      self.current = null;
      self.loading = false;
      self.loadingAction = "";
      self.error = null;
      self.fieldErrors = {};
      self.total = 0;
      self.filters = (defaultFilters ?? {}) as TFilter;
      self.dropdown = [];
      self.dropdownLoaded = false;
      self.listLoaded = false;
      self.lastFetched = null;
    },
  };
}

// =============================================================================
// Convenience Factory — defineCrudStore
// =============================================================================

/**
 * Create a complete Pinia CRUD store with standard state, getters, and actions.
 *
 * Use this for simple stores that don't need domain-specific extensions.
 * For stores that need extra state/getters/actions, use the composable
 * `crudState()`, `crudGetters()`, and `crudActions()` functions directly
 * with `defineStore()`.
 *
 * @example
 *   // Simple store — no domain extras
 *   export const useTagStore = defineCrudStore<
 *     TagOut, TagCreate, TagUpdate, TagFilter, TagListOut
 *   >({
 *     storeId: 'tag',
 *     api: {
 *       list: ledgerApi.tags.list,
 *       get: ledgerApi.tags.get,
 *       create: ledgerApi.tags.create,
 *       update: ledgerApi.tags.update,
 *       remove: ledgerApi.tags.remove,
 *       restore: ledgerApi.tags.restore,
 *       dropdown: ledgerApi.tags.dropdown,
 *     },
 *   });
 *
 * @template T        - Full entity type
 * @template TCreate  - Create request type
 * @template TUpdate  - Update request type
 * @template TFilter  - Filter/query params type
 * @template TDropdown - Dropdown item type
 * @param config - Store configuration
 */
export function defineCrudStore<
  T extends { id: number; is_active?: boolean; is_deleted?: boolean },
  TCreate,
  TUpdate,
  TFilter extends PaginationIn = PaginationIn,
  TDropdown = { id: number; [key: string]: unknown },
>(config: CrudStoreConfig<T, TCreate, TUpdate, TFilter>) {
  const { storeId, defaultFilters, staleThresholdMs } = config;

  return defineStore(storeId, {
    state: () => crudState<T, TFilter, TDropdown>(defaultFilters),

    getters: crudGetters<T>(staleThresholdMs),

    actions: crudActions<T, TCreate, TUpdate, TFilter, TDropdown>(config),
  });
}

// =============================================================================
// Error Handling Utilities
// =============================================================================

/**
 * Extract a human-readable error message from an API error.
 *
 * Handles multiple error formats:
 *   - ApiError objects (from ledgerApi / apiClient)
 *   - Django Ninja validation errors
 *   - Standard Error instances
 *   - String errors
 *   - Unknown error types
 *
 * @param err - The thrown error
 * @returns A user-friendly error message string
 */
export function extractErrorMessage(err: unknown): string {
  if (err === null || err === undefined) {
    return "An unknown error occurred";
  }
  if (typeof err === "string") {
    return err;
  }
  if (err instanceof Error) {
    return err.message;
  }
  if (typeof err === "object") {
    const obj = err as Record<string, unknown>;

    // ApiError format from our API clients
    if (typeof obj.message === "string" && obj.message.length > 0) {
      return obj.message;
    }

    // Django Ninja detail format
    if (typeof obj.detail === "string" && obj.detail.length > 0) {
      return obj.detail;
    }

    // Django Ninja validation error with errors array
    if (
      Array.isArray(obj.errors) &&
      obj.errors.length > 0 &&
      typeof obj.errors[0] === "object" &&
      obj.errors[0] !== null &&
      "message" in obj.errors[0]
    ) {
      const firstError = obj.errors[0] as Record<string, unknown>;
      return String(firstError.message);
    }

    // Non-field errors
    if (Array.isArray(obj.non_field_errors) && obj.non_field_errors.length > 0) {
      return String(obj.non_field_errors[0]);
    }
  }

  return "An unexpected error occurred";
}

/**
 * Extract field-level validation errors from an API error.
 *
 * Returns the `errors` field from ApiError if present, which
 * contains a mapping of field names to arrays of error messages.
 * This is the Django Ninja validation error format.
 *
 * @param err - The thrown error
 * @returns A Record mapping field names to error message arrays
 */
export function extractFieldErrors(err: unknown): Record<string, string[]> {
  if (typeof err !== "object" || err === null) {
    return {};
  }

  const obj = err as Record<string, unknown>;

  // ApiError.errors format: { field_name: ["error1", "error2"] }
  if (obj.errors && typeof obj.errors === "object" && !Array.isArray(obj.errors)) {
    return obj.errors as Record<string, string[]>;
  }

  // Django Ninja format: individual field keys with array values
  // (anything that's not a standard key like detail/message/status)
  const standardKeys = new Set([
    "detail",
    "message",
    "status",
    "non_field_errors",
    "code",
    "errors",
  ]);

  const fieldErrors: Record<string, string[]> = {};
  for (const [key, value] of Object.entries(obj)) {
    if (standardKeys.has(key)) continue;
    if (Array.isArray(value)) {
      fieldErrors[key] = value.map(String);
    } else if (typeof value === "string") {
      fieldErrors[key] = [value];
    }
  }

  return fieldErrors;
}

/**
 * Type guard to check if an error is an ApiError from our API clients.
 *
 * @param err - The value to check
 * @returns True if the error has the ApiError shape
 */
export function isApiError(err: unknown): err is ApiError {
  return (
    typeof err === "object" &&
    err !== null &&
    "status" in err &&
    typeof (err as ApiError).status === "number" &&
    "message" in err
  );
}
