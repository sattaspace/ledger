/**
 * useLedgerPagination — offset/limit pagination state + helpers.
 *
 * Provides reactive pagination state derived from the store's
 * PaginationIn-based filter object. Works in tandem with DataTable's
 * `@page-change` event and the store's `setPage()` / `fetchList()` methods.
 *
 * Usage:
 *   const pagination = useLedgerPagination(() => store.total, () => store.filters);
 *
 *   // In template:
 *   <DataTable
 *     :total="store.total"
 *     :limit="pagination.limit.value"
 *     :offset="pagination.offset.value"
 *     @page-change="pagination.goToPage($event); store.fetchList()"
 *   />
 *
 *   // Manual:
 *   pagination.nextPage();
 *   await store.fetchList();
 */

import { computed, type ComputedRef } from "vue";
import type { PaginationIn } from "@/lib/ledgerTypes";

// =============================================================================
// Constants
// =============================================================================

/** Default page size when no limit is set in filters. */
const DEFAULT_PAGE_SIZE = 25;

/** Available page size options for the page-size selector. */
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

// =============================================================================
// Types
// =============================================================================

/** Return type of useLedgerPagination. */
export interface LedgerPagination {
  /** Current page size (items per page). */
  limit: ComputedRef<number>;
  /** Current offset (items to skip). */
  offset: ComputedRef<number>;
  /** Current page number (1-based). */
  currentPage: ComputedRef<number>;
  /** Total number of pages. */
  totalPages: ComputedRef<number>;
  /** Total number of items. */
  total: ComputedRef<number>;
  /** Whether there is a next page. */
  hasNext: ComputedRef<boolean>;
  /** Whether there is a previous page. */
  hasPrev: ComputedRef<boolean>;
  /** Human-readable range string: "1–25 of 100". */
  showingRange: ComputedRef<string>;
  /** Whether pagination controls should be shown. */
  showPagination: ComputedRef<boolean>;

  /**
   * Navigate to a specific page (1-based).
   * Updates the store's filters.limit and filters.offset.
   * Does NOT call fetchList — call it yourself after.
   *
   * @param page - 1-based page number
   */
  goToPage: (page: number) => void;

  /**
   * Go to the next page.
   * Does NOT call fetchList.
   */
  nextPage: () => void;

  /**
   * Go to the previous page.
   * Does NOT call fetchList.
   */
  prevPage: () => void;

  /**
   * Change the page size and reset to page 1.
   * Does NOT call fetchList.
   *
   * @param newLimit - New page size
   */
  changePageSize: (newLimit: number) => void;

  /**
   * Directly set pagination state.
   * Does NOT call fetchList.
   *
   * @param newLimit - New page size
   * @param newOffset - New offset
   */
  setPagination: (newLimit: number, newOffset: number) => void;

  /**
   * Reset pagination to page 1 with the current or specified page size.
   * Does NOT call fetchList.
   *
   * @param newLimit - Optional new page size
   */
  resetToFirstPage: (newLimit?: number) => void;
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Create reactive pagination state from the store's total count and filters.
 *
 * @param getTotal - Function returning the current total item count
 * @param getFilters - Function returning the current filter object (or a ref)
 * @param setFilters - Function to update the store's filters
 * @param defaultPageSize - Default page size (default: 25)
 */
export function useLedgerPagination(
  getTotal: () => number,
  getFilters: () => PaginationIn,
  setFilters: (partial: Partial<PaginationIn>) => void,
  defaultPageSize: number = DEFAULT_PAGE_SIZE,
): LedgerPagination {
  // ─── Computed state from filters ──────────────────────────────────────────

  const limit = computed(() => getFilters().limit ?? defaultPageSize);

  const offset = computed(() => getFilters().offset ?? 0);

  const total = computed(() => getTotal());

  const currentPage = computed(() => {
    const lim = limit.value;
    const off = offset.value;
    return Math.floor(off / lim) + 1;
  });

  const totalPages = computed(() => {
    const lim = limit.value;
    return Math.max(1, Math.ceil(total.value / lim));
  });

  const hasNext = computed(() => currentPage.value < totalPages.value);

  const hasPrev = computed(() => currentPage.value > 1);

  const showPagination = computed(() => total.value > limit.value);

  const showingRange = computed(() => {
    const start = offset.value + 1;
    const end = Math.min(offset.value + limit.value, total.value);
    if (total.value === 0) return "0 items";
    return `${start}\u2013${end} of ${total.value}`;
  });

  // ─── Navigation methods ──────────────────────────────────────────────────

  function goToPage(page: number): void {
    const clampedPage = Math.max(1, Math.min(page, totalPages.value));
    const newOffset = (clampedPage - 1) * limit.value;
    setFilters({ limit: limit.value, offset: newOffset });
  }

  function nextPage(): void {
    if (hasNext.value) {
      goToPage(currentPage.value + 1);
    }
  }

  function prevPage(): void {
    if (hasPrev.value) {
      goToPage(currentPage.value - 1);
    }
  }

  function changePageSize(newLimit: number): void {
    const clampedSize = Math.max(1, newLimit);
    // When changing page size, try to keep the current first item visible
    const currentFirstItem = offset.value;
    const newPage = Math.floor(currentFirstItem / clampedSize) + 1;
    const newOffset = (newPage - 1) * clampedSize;
    setFilters({ limit: clampedSize, offset: newOffset });
  }

  function setPagination(newLimit: number, newOffset: number): void {
    setFilters({ limit: Math.max(1, newLimit), offset: Math.max(0, newOffset) });
  }

  function resetToFirstPage(newLimit?: number): void {
    setFilters({
      limit: newLimit ?? limit.value,
      offset: 0,
    });
  }

  return {
    limit,
    offset,
    currentPage,
    totalPages,
    total,
    hasNext,
    hasPrev,
    showingRange,
    showPagination,

    goToPage,
    nextPage,
    prevPage,
    changePageSize,
    setPagination,
    resetToFirstPage,
  };
}
