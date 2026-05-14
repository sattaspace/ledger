<script setup lang="ts">
/**
 * DataTable — Sortable, paginated data table.
 *
 * Renders a responsive table with sortable column headers,
 * row selection, pagination controls, and loading/empty states.
 * Designed to work with Pinia CRUD stores' items/total/filters state.
 *
 * Usage:
 *   <DataTable
 *     :columns="columns"
 *     :rows="store.items"
 *     :loading="store.loading"
 *     :total="store.total"
 *     :limit="store.filters.limit"
 *     :offset="store.filters.offset"
 *     @page-change="store.setPage($event); store.fetchList()"
 *     @sort-change="handleSort"
 *   />
 */

import LoadingSkeleton from "./LoadingSkeleton.vue";

// ─── Types ────────────────────────────────────────────────────────────────────

export interface DataTableColumn {
  /** Unique key matching a property on the row object, or a custom slot name. */
  key: string;
  /** Header label. */
  label: string;
  /** Whether this column is sortable. */
  sortable?: boolean;
  /** CSS class(es) applied to each cell in this column. */
  class?: string;
  /** Text alignment: 'left' | 'center' | 'right'. */
  align?: "left" | "center" | "right";
  /** Minimum column width (CSS value). */
  minWidth?: string;
}

export type SortDirection = "asc" | "desc";

export interface SortChangePayload {
  key: string;
  direction: SortDirection;
}

// ─── Props & Emits ────────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Column definitions. */
    columns: DataTableColumn[];
    /** Row data array. */
    rows: Record<string, unknown>[];
    /** Show loading state. */
    loading?: boolean;
    /** Total record count (from API pagination). */
    total?: number;
    /** Current page size. */
    limit?: number;
    /** Current offset. */
    offset?: number;
    /** Show row selection checkboxes. */
    selectable?: boolean;
    /** Currently selected row IDs. */
    selectedIds?: number[];
    /** Row key field for selection (default: 'id'). */
    rowKey?: string;
    /** Number of skeleton rows to show while loading. */
    skeletonRows?: number;
    /** Text to show when rows is empty and not loading. */
    emptyText?: string;
    /** Enable sticky header. */
    stickyHeader?: boolean;
    /** Compact row padding. */
    compact?: boolean;
    /** Show card layout on mobile instead of scrollable table. */
    mobileCardMode?: boolean;
  }>(),
  {
    loading: false,
    total: 0,
    limit: 25,
    offset: 0,
    selectable: false,
    selectedIds: () => [],
    rowKey: "id",
    skeletonRows: 5,
    emptyText: "No records found",
    stickyHeader: false,
    compact: false,
    mobileCardMode: true,
  },
);

const emit = defineEmits<{
  "page-change": [page: number];
  "sort-change": [payload: SortChangePayload];
  "row-click": [row: Record<string, unknown>];
  "selection-change": [ids: number[]];
}>();

// ─── Computed ─────────────────────────────────────────────────────────────────

const currentPage = computed(() =>
  Math.floor(props.offset / props.limit) + 1,
);

const totalPages = computed(() =>
  Math.max(1, Math.ceil(props.total / props.limit)),
);

const showPagination = computed(() => props.total > props.limit);

const alignClass = (align?: "left" | "center" | "right") => {
  switch (align) {
    case "center":
      return "text-center";
    case "right":
      return "text-right";
    default:
      return "text-left";
  }
};

// ─── Sort State ───────────────────────────────────────────────────────────────

const sortKey = ref("");
const sortDirection = ref<SortDirection>("asc");

function handleSortClick(column: DataTableColumn) {
  if (!column.sortable) return;
  if (sortKey.value === column.key) {
    sortDirection.value = sortDirection.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = column.key;
    sortDirection.value = "asc";
  }
  emit("sort-change", { key: sortKey.value, direction: sortDirection.value });
}

function sortIcon(column: DataTableColumn): "asc" | "desc" | "none" {
  if (!column.sortable) return "none";
  if (sortKey.value !== column.key) return "none";
  return sortDirection.value;
}

// ─── Selection ────────────────────────────────────────────────────────────────

function isRowSelected(row: Record<string, unknown>): boolean {
  const id = row[props.rowKey] as number;
  return props.selectedIds.includes(id);
}

function toggleRowSelection(row: Record<string, unknown>) {
  const id = row[props.rowKey] as number;
  const current = [...props.selectedIds];
  const idx = current.indexOf(id);
  if (idx === -1) {
    current.push(id);
  } else {
    current.splice(idx, 1);
  }
  emit("selection-change", current);
}

function isAllSelected(): boolean {
  if (props.rows.length === 0) return false;
  return props.rows.every((row) => isRowSelected(row));
}

function toggleAll() {
  if (isAllSelected()) {
    emit("selection-change", []);
  } else {
    const allIds = props.rows.map((row) => row[props.rowKey] as number);
    emit("selection-change", allIds);
  }
}

// ─── Pagination ───────────────────────────────────────────────────────────────

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return;
  emit("page-change", page);
}

// ─── Mobile Card View ──────────────────────────────────────────────────────────

const isMobile = ref(false);

onMounted(() => {
  const checkMobile = () => { isMobile.value = window.innerWidth < 640; };
  checkMobile();
  window.addEventListener('resize', checkMobile);
  onUnmounted(() => window.removeEventListener('resize', checkMobile));
});

const showCardView = computed(() => isMobile.value && props.mobileCardMode && !props.loading && props.rows.length > 0);

function pageNumbers(): (number | string)[] {
  const total = totalPages.value;
  const current = currentPage.value;
  const pages: (number | string)[] = [];

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i);
    return pages;
  }

  pages.push(1);
  if (current > 3) pages.push("...");

  const start = Math.max(2, current - 1);
  const end = Math.min(total - 1, current + 1);
  for (let i = start; i <= end; i++) pages.push(i);

  if (current < total - 2) pages.push("...");
  pages.push(total);

  return pages;
}
</script>

<template>
  <div class="data-table-wrapper w-full">
    <!-- Table Container -->
    <div :class="['overflow-x-auto rounded-xl border border-navy-200 dark:border-navy-700', { 'hidden sm:block': showCardView }]">
      <table class="w-full text-sm">
        <!-- Header -->
        <thead :class="[stickyHeader ? 'sticky top-0 z-10' : '', 'bg-navy-50 dark:bg-navy-900']">
          <tr>
            <!-- Selection Checkbox -->
            <th
              v-if="selectable"
              class="w-10 px-3 py-3"
            >
              <input
                type="checkbox"
                :checked="isAllSelected()"
                :indeterminate="!isAllSelected() && selectedIds.length > 0"
                class="h-4 w-4 rounded border-navy-300 text-cyan-600 focus:ring-cyan-500"
                @change="toggleAll"
              />
            </th>
            <!-- Column Headers -->
            <th
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-4 py-3 font-semibold text-navy-900 dark:text-navy-100 whitespace-nowrap',
                alignClass(col.align),
                col.sortable ? 'cursor-pointer select-none hover:text-cyan-600 dark:hover:text-cyan-400' : '',
                col.class,
              ]"
              :style="col.minWidth ? { minWidth: col.minWidth } : undefined"
              @click="handleSortClick(col)"
            >
              <div class="flex items-center gap-1" :class="col.align === 'right' ? 'justify-end' : col.align === 'center' ? 'justify-center' : 'justify-start'">
                <span>{{ col.label }}</span>
                <!-- Sort Indicator -->
                <span v-if="col.sortable" class="inline-flex flex-col ml-0.5">
                  <svg
                    :class="['h-3 w-3', sortIcon(col) === 'asc' ? 'text-cyan-600 dark:text-cyan-400' : 'text-navy-300 dark:text-navy-600']"
                    viewBox="0 0 10 6" fill="currentColor"
                  >
                    <path d="M5 0L10 4H0z" />
                  </svg>
                  <svg
                    :class="['h-3 w-3 -mt-0.5', sortIcon(col) === 'desc' ? 'text-cyan-600 dark:text-cyan-400' : 'text-navy-300 dark:text-navy-600']"
                    viewBox="0 0 10 6" fill="currentColor"
                  >
                    <path d="M5 6L0 2h10z" />
                  </svg>
                </span>
              </div>
            </th>
          </tr>
        </thead>

        <!-- Body -->
        <tbody class="divide-y divide-navy-100 dark:divide-navy-800">
          <!-- Loading State -->
          <tr v-if="loading">
            <td :colspan="selectable ? columns.length + 1 : columns.length" class="p-0">
              <LoadingSkeleton type="table" :rows="skeletonRows" />
            </td>
          </tr>

          <!-- Empty State -->
          <tr v-else-if="rows.length === 0">
            <td
              :colspan="selectable ? columns.length + 1 : columns.length"
              class="px-4 py-12 text-center text-slate-custom-600 dark:text-slate-custom-400"
            >
              {{ emptyText }}
            </td>
          </tr>

          <!-- Data Rows -->
          <tr
            v-else
            v-for="row in rows"
            :key="(row[rowKey] as number)"
            :class="[
              'transition-colors hover:bg-cyan-50/50 dark:hover:bg-navy-800/50',
              isRowSelected(row) ? 'bg-cyan-50 dark:bg-cyan-950/20' : '',
              $attrs['onRow-click'] ? 'cursor-pointer' : '',
              compact ? 'py-2' : '',
            ]"
            @click="emit('row-click', row)"
          >
            <!-- Selection Checkbox -->
            <td v-if="selectable" class="w-10 px-3 py-3" @click.stop>
              <input
                type="checkbox"
                :checked="isRowSelected(row)"
                class="h-4 w-4 rounded border-navy-300 text-cyan-600 focus:ring-cyan-500"
                @change="toggleRowSelection(row)"
              />
            </td>
            <!-- Cells -->
            <td
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-4 text-navy-900 dark:text-navy-100',
                compact ? 'py-2' : 'py-3',
                alignClass(col.align),
                col.class,
              ]"
            >
              <!-- Named Slot for Custom Cell Rendering -->
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                {{ row[col.key] }}
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Mobile Card View -->
    <div v-if="showCardView" class="space-y-3 sm:hidden">
      <div
        v-for="row in rows"
        :key="(row[rowKey] as number)"
        class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900 p-4 space-y-2"
        @click="emit('row-click', row)"
        :class="$attrs['onRow-click'] ? 'cursor-pointer' : ''"
      >
        <div
          v-for="col in columns"
          :key="col.key"
          class="flex justify-between items-start gap-2"
        >
          <span class="text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400">{{ col.label }}</span>
          <span class="text-sm text-navy-900 dark:text-navy-100 text-right">
            <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
              {{ row[col.key] }}
            </slot>
          </span>
        </div>
      </div>
    </div>

    <!-- Pagination Footer -->
    <div
      v-if="showPagination && !loading"
      class="flex items-center justify-between px-2 py-3 text-sm"
    >
      <div class="text-slate-custom-600 dark:text-slate-custom-400">
        Showing {{ offset + 1 }}–{{ Math.min(offset + limit, total) }} of {{ total }}
      </div>
      <div class="flex items-center gap-1">
        <!-- Previous -->
        <button
          :disabled="currentPage <= 1"
          class="btn-ghost rounded-lg px-2 py-1 disabled:opacity-40 disabled:cursor-not-allowed"
          @click="goToPage(currentPage - 1)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
        <!-- Page Numbers -->
        <template v-for="page in pageNumbers()" :key="page">
          <span v-if="page === '...'" class="px-2 text-slate-custom-500">...</span>
          <button
            v-else
            :class="[
              'rounded-lg px-3 py-1 text-sm font-medium transition-colors',
              page === currentPage
                ? 'bg-cyan-600 text-white'
                : 'text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-800',
            ]"
            @click="goToPage(page as number)"
          >
            {{ page }}
          </button>
        </template>
        <!-- Next -->
        <button
          :disabled="currentPage >= totalPages"
          class="btn-ghost rounded-lg px-2 py-1 disabled:opacity-40 disabled:cursor-not-allowed"
          @click="goToPage(currentPage + 1)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>
