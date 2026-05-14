<script setup lang="ts">
/**
 * CategoriesPage — Dual-view (Tree + Flat list) categories management.
 *
 * Features:
 *   - Tree View (default): Hierarchical category tree with expand/collapse,
 *     color dots, income/expense badges, and inline action buttons.
 *   - Flat List View: DataTable with sortable columns and full CRUD actions.
 *   - Toggle between views with styled buttons.
 *   - Search by name and is_income filter.
 *   - Modal form for create/edit using CategoryForm.
 *   - ConfirmDialog for delete/restore and activate/deactivate.
 *
 * Registered as: ldgr-categories-page
 */

import { ref, computed, onMounted, reactive } from "vue";
import {
  DataTable,
  Modal,
  ConfirmDialog,
  StatusBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
} from "@/components/vue";
import type { DataTableColumn, FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useCategoryStore } from "@/stores/category";
import type {
  CategoryOut,
  CategoryFilter,
  CategoryTreeOut,
} from "@/lib/ledgerTypes";
import CategoryForm from "./CategoryForm.vue";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "CategoriesPage" });

// ─── Store ──────────────────────────────────────────────────────────────────

const store = useCategoryStore();

// ─── View Mode ──────────────────────────────────────────────────────────────

type ViewMode = "tree" | "list";
const activeView = ref<ViewMode>("tree");

// ─── Filters ────────────────────────────────────────────────────────────────

const searchQuery = ref("");
const filterIncome = ref<boolean | null>(null);

const filterConfigs: FilterConfig[] = [
  {
    key: "is_income",
    label: "Income",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "Income", value: "true" },
      { label: "Expense", value: "false" },
    ],
  },
];

const filterValues = ref<Record<string, unknown>>({});

function handleFilterChange(key: string, value: unknown) {
  if (key === "is_income") {
    if (value === "true") {
      filterIncome.value = true;
    } else if (value === "false") {
      filterIncome.value = false;
    } else {
      filterIncome.value = null;
    }
  }
  applyFilters();
}

function handleFilterReset() {
  filterIncome.value = null;
  searchQuery.value = "";
  filterValues.value = {};
  applyFilters();
}

function handleSearch(query: string) {
  searchQuery.value = query;
  applyFilters();
}

// ─── Apply Filters ──────────────────────────────────────────────────────────

async function applyFilters() {
  const filters: Partial<CategoryFilter> = {
    limit: 25,
    offset: 0,
  };

  if (searchQuery.value) {
    filters.search = searchQuery.value;
  }
  if (filterIncome.value !== null) {
    filters.is_income = filterIncome.value;
  }

  store.setFilters(filters);
  await store.fetchList();
}

// ─── Pagination (flat list view) ────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as CategoryFilter,
  (partial) => store.setFilters(partial as Partial<CategoryFilter>),
);

async function handlePageChange(page: number) {
  pagination.goToPage(page);
  await store.fetchList();
}

// ─── Soft Delete / Restore ──────────────────────────────────────────────────

const deleter = useSoftDelete<CategoryOut>({
  store,
  entityName: "Category",
  refreshListAfter: true,
  onDeleted() {
    store.fetchTree(true);
  },
  onRestored() {
    store.fetchTree(true);
    store.fetchList();
  },
});

// ─── Activate / Deactivate ──────────────────────────────────────────────────

const activator = useActivator<CategoryOut>({
  store,
  entityName: "Category",
  refreshListAfter: true,
  onActivated() {
    store.fetchTree(true);
  },
  onDeactivated() {
    store.fetchTree(true);
  },
});

// ─── Modal State ────────────────────────────────────────────────────────────

const showModal = ref(false);
const formMode = ref<"create" | "edit">("create");
const formItemId = ref<number | undefined>(undefined);

function openCreateModal() {
  formMode.value = "create";
  formItemId.value = undefined;
  showModal.value = true;
}

function openEditModal(item: CategoryOut) {
  formMode.value = "edit";
  formItemId.value = item.id;
  showModal.value = true;
}

function closeModal() {
  showModal.value = false;
  formItemId.value = undefined;
}

function handleFormSaved() {
  closeModal();
  applyFilters();
}

// ─── Tree View State ────────────────────────────────────────────────────────

const expandedIds = ref<Set<number>>(new Set());
const selectedId = ref<number | null>(null);

function toggleExpand(id: number) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id);
  } else {
    expandedIds.value.add(id);
  }
}

function isExpanded(id: number): boolean {
  return expandedIds.value.has(id);
}

function hasChildren(node: CategoryTreeOut): boolean {
  return !!(node.subcategories && node.subcategories.length > 0);
}

function selectNode(node: CategoryTreeOut) {
  selectedId.value = node.id;
}

// ─── Flat List: Find parent name ────────────────────────────────────────────

function getParentName(parentId: number | null): string {
  if (parentId === null) return "—";
  const found = store.items.find((c) => c.id === parentId);
  return found ? found.name : `#${parentId}`;
}

// ─── DataTable Columns ──────────────────────────────────────────────────────

const columns = computed<DataTableColumn[]>(() => [
  { key: "name", label: "Name", sortable: true, minWidth: "160px" },
  { key: "parent_id", label: "Parent", sortable: false, minWidth: "120px" },
  { key: "is_income", label: "Type", sortable: true, minWidth: "100px" },
  { key: "color", label: "Color", sortable: false, minWidth: "70px", align: "center" },
  { key: "is_active", label: "Status", sortable: true, minWidth: "100px" },
  { key: "actions", label: "Actions", minWidth: "140px", align: "right" },
]);

// ─── Load Data ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([
    store.fetchTree(),
    store.fetchList({ limit: 25, offset: 0 } as Partial<CategoryFilter>),
  ]);
});

// ─── Loading State ──────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading);
</script>

<template>
  <div class="space-y-6">
    <!-- ─── Page Header ──────────────────────────────────────────────── -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
          Categories
        </h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Organize your income and expense categories
        </p>
      </div>
      <button class="btn-primary" @click="openCreateModal">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Add Category
      </button>
    </div>

    <!-- ─── View Toggle + Filters ────────────────────────────────────── -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <!-- View Toggle -->
      <div class="inline-flex rounded-lg border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900 p-1">
        <button
          :class="[
            'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            activeView === 'tree'
              ? 'bg-cyan-600 text-white shadow-sm'
              : 'text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-800',
          ]"
          @click="activeView = 'tree'"
        >
          <svg class="h-4 w-4 inline mr-1.5 -mt-0.5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
          </svg>
          Tree View
        </button>
        <button
          :class="[
            'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            activeView === 'list'
              ? 'bg-cyan-600 text-white shadow-sm'
              : 'text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-800',
          ]"
          @click="activeView = 'list'"
        >
          <svg class="h-4 w-4 inline mr-1.5 -mt-0.5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
          </svg>
          List View
        </button>
      </div>

      <!-- Filters -->
      <div class="flex items-center gap-3 flex-1 sm:justify-end">
        <SearchInput
          :model-value="searchQuery"
          placeholder="Search categories..."
          size="sm"
          class="w-full sm:w-56"
          @search="handleSearch"
          @clear="handleSearch('')"
        />
        <select
          :value="filterIncome === null ? '' : filterIncome ? 'true' : 'false'"
          class="input-field h-8 text-sm min-w-[120px]"
          @change="handleFilterChange('is_income', ($event.target as HTMLSelectElement).value)"
        >
          <option value="">All Types</option>
          <option value="true">Income</option>
          <option value="false">Expense</option>
        </select>
      </div>
    </div>

    <!-- ─── Loading Skeleton ─────────────────────────────────────────── -->
    <LoadingSkeleton v-if="isLoading && !store.listLoaded" type="table" :rows="6" />

    <!-- ─── Tree View ────────────────────────────────────────────────── -->
    <div v-else-if="activeView === 'tree'" class="card">
      <div v-if="store.tree.length === 0" class="p-6">
        <EmptyState
          title="No categories yet"
          description="Create your first category to start organizing your transactions."
          icon="folder"
          action-label="Add Category"
          @action="openCreateModal"
        />
      </div>

      <div v-else class="divide-y divide-navy-100 dark:divide-navy-800">
        <template v-for="node in store.tree" :key="node.id">
          <!-- CategoryNode — recursive tree item -->
          <div
            class="group flex items-center gap-2 px-4 py-3 transition-colors hover:bg-cyan-50/50 dark:hover:bg-navy-800/50 cursor-pointer"
            :class="[
              selectedId === node.id
                ? 'bg-cyan-50 dark:bg-cyan-950/20'
                : '',
            ]"
            @click="selectNode(node)"
          >
            <!-- Expand/Collapse Chevron -->
            <button
              v-if="hasChildren(node)"
              class="p-0.5 rounded hover:bg-navy-100 dark:hover:bg-navy-700 transition-colors flex-shrink-0"
              @click.stop="toggleExpand(node.id)"
            >
              <svg
                :class="[
                  'h-4 w-4 text-slate-custom-400 transition-transform duration-200',
                  isExpanded(node.id) ? 'rotate-90' : '',
                ]"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
              </svg>
            </button>
            <span v-else class="w-5 flex-shrink-0" />

            <!-- Color Dot -->
            <span
              class="h-3 w-3 rounded-full flex-shrink-0 border border-navy-200 dark:border-navy-600"
              :style="{ backgroundColor: node.color || '#6C7A89' }"
            />

            <!-- Category Name -->
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100 truncate">
              {{ node.name }}
            </span>

            <!-- Income/Expense Badge -->
            <span
              :class="[
                'text-[10px] font-bold rounded px-1.5 py-0.5 flex-shrink-0',
                node.is_income
                  ? 'text-credit bg-green-50 dark:bg-green-950/30'
                  : 'text-debit bg-red-50 dark:bg-red-950/30',
              ]"
            >
              {{ node.is_income ? 'Income' : 'Expense' }}
            </span>

            <!-- Spacer -->
            <span class="flex-1" />

            <!-- Action Buttons (visible on hover) -->
            <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                class="btn-ghost px-2 py-1 text-xs"
                title="Edit"
                @click.stop="openEditModal({ id: node.id } as CategoryOut)"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
              <button
                class="btn-ghost px-2 py-1 text-xs text-debit hover:text-red-700"
                title="Delete"
                @click.stop="deleter.confirmDelete({ id: node.id, name: node.name } as CategoryOut)"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Children (recursive-like via nested template) -->
          <template v-if="hasChildren(node) && isExpanded(node.id)">
            <div
              v-for="child in node.subcategories"
              :key="child.id"
              class="group flex items-center gap-2 pl-10 pr-4 py-2.5 transition-colors hover:bg-cyan-50/50 dark:hover:bg-navy-800/50 cursor-pointer border-t border-navy-50 dark:border-navy-800/50"
              :class="[
                selectedId === child.id
                  ? 'bg-cyan-50 dark:bg-cyan-950/20'
                  : '',
              ]"
              @click="selectNode(child)"
            >
              <!-- Expand/Collapse for child (if grandchildren exist) -->
              <button
                v-if="hasChildren(child)"
                class="p-0.5 rounded hover:bg-navy-100 dark:hover:bg-navy-700 transition-colors flex-shrink-0"
                @click.stop="toggleExpand(child.id)"
              >
                <svg
                  :class="[
                    'h-3.5 w-3.5 text-slate-custom-400 transition-transform duration-200',
                    isExpanded(child.id) ? 'rotate-90' : '',
                  ]"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                </svg>
              </button>
              <span v-else class="w-4.5 flex-shrink-0" />

              <!-- Color Dot -->
              <span
                class="h-2.5 w-2.5 rounded-full flex-shrink-0"
                :style="{ backgroundColor: child.color || '#6C7A89' }"
              />

              <!-- Name -->
              <span class="text-sm text-navy-900 dark:text-navy-100 truncate">
                {{ child.name }}
              </span>

              <!-- Badge -->
              <span
                :class="[
                  'text-[10px] font-bold rounded px-1.5 py-0.5 flex-shrink-0',
                  child.is_income
                    ? 'text-credit bg-green-50 dark:bg-green-950/30'
                    : 'text-debit bg-red-50 dark:bg-red-950/30',
                ]"
              >
                {{ child.is_income ? 'Income' : 'Expense' }}
              </span>

              <!-- Spacer -->
              <span class="flex-1" />

              <!-- Actions -->
              <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  class="btn-ghost px-2 py-1 text-xs"
                  title="Edit"
                  @click.stop="openEditModal({ id: child.id } as CategoryOut)"
                >
                  <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                  </svg>
                </button>
                <button
                  class="btn-ghost px-2 py-1 text-xs text-debit hover:text-red-700"
                  title="Delete"
                  @click.stop="deleter.confirmDelete({ id: child.id, name: child.name } as CategoryOut)"
                >
                  <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Grandchildren (3rd level) -->
            <template v-if="hasChildren(child) && isExpanded(child.id)">
              <div
                v-for="grandchild in child.subcategories"
                :key="grandchild.id"
                class="group flex items-center gap-2 pl-16 pr-4 py-2 transition-colors hover:bg-cyan-50/50 dark:hover:bg-navy-800/50 cursor-pointer border-t border-navy-50 dark:border-navy-800/50"
                :class="[
                  selectedId === grandchild.id
                    ? 'bg-cyan-50 dark:bg-cyan-950/20'
                    : '',
                ]"
                @click="selectNode(grandchild)"
              >
                <span
                  class="h-2 w-2 rounded-full flex-shrink-0"
                  :style="{ backgroundColor: grandchild.color || '#6C7A89' }"
                />
                <span class="text-sm text-navy-900 dark:text-navy-100 truncate">
                  {{ grandchild.name }}
                </span>
                <span
                  :class="[
                    'text-[10px] font-bold rounded px-1.5 py-0.5 flex-shrink-0',
                    grandchild.is_income
                      ? 'text-credit bg-green-50 dark:bg-green-950/30'
                      : 'text-debit bg-red-50 dark:bg-red-950/30',
                  ]"
                >
                  {{ grandchild.is_income ? 'Income' : 'Expense' }}
                </span>
                <span class="flex-1" />
                <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    class="btn-ghost px-2 py-1 text-xs"
                    title="Edit"
                    @click.stop="openEditModal({ id: grandchild.id } as CategoryOut)"
                  >
                    <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                    </svg>
                  </button>
                  <button
                    class="btn-ghost px-2 py-1 text-xs text-debit hover:text-red-700"
                    title="Delete"
                    @click.stop="deleter.confirmDelete({ id: grandchild.id, name: grandchild.name } as CategoryOut)"
                  >
                    <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </template>
          </template>
        </template>
      </div>
    </div>

    <!-- ─── Flat List View ───────────────────────────────────────────── -->
    <div v-else class="card overflow-hidden">
      <EmptyState
        v-if="!isLoading && store.items.length === 0"
        title="No categories found"
        description="Try adjusting your filters or create a new category."
        icon="folder"
        action-label="Add Category"
        @action="openCreateModal"
      />

      <DataTable
        v-else
        :columns="columns"
        :rows="store.items"
        :loading="isLoading"
        :total="store.total"
        :limit="store.filters.limit ?? 25"
        :offset="store.filters.offset ?? 0"
        empty-text="No categories found"
        @page-change="handlePageChange"
      >
        <!-- Name column -->
        <template #cell-name="{ row }">
          <div class="flex items-center gap-2">
            <span
              class="h-2.5 w-2.5 rounded-full flex-shrink-0"
              :style="{ backgroundColor: (row as CategoryOut).color || '#6C7A89' }"
            />
            <span class="font-medium text-navy-900 dark:text-navy-100">
              {{ (row as CategoryOut).name }}
            </span>
          </div>
        </template>

        <!-- Parent column -->
        <template #cell-parent_id="{ row }">
          <span class="text-slate-custom-600 dark:text-slate-custom-400">
            {{ getParentName((row as CategoryOut).parent_id) }}
          </span>
        </template>

        <!-- Type column -->
        <template #cell-is_income="{ row }">
          <span
            :class="[
              'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold',
              (row as CategoryOut).is_income
                ? 'text-credit bg-green-50 dark:bg-green-950/30'
                : 'text-debit bg-red-50 dark:bg-red-950/30',
            ]"
          >
            {{ (row as CategoryOut).is_income ? 'Income' : 'Expense' }}
          </span>
        </template>

        <!-- Color column -->
        <template #cell-color="{ row }">
          <div class="flex items-center justify-center">
            <span
              class="h-5 w-5 rounded-full border border-navy-200 dark:border-navy-600"
              :style="{ backgroundColor: (row as CategoryOut).color || '#6C7A89' }"
            />
          </div>
        </template>

        <!-- Status column -->
        <template #cell-is_active="{ row }">
          <StatusBadge
            :status="(row as CategoryOut).is_active ? 'Active' : 'Inactive'"
          />
        </template>

        <!-- Actions column -->
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <!-- Edit -->
            <button
              class="btn-ghost px-2 py-1 text-xs"
              title="Edit"
              @click.stop="openEditModal(row as CategoryOut)"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!(row as CategoryOut).is_deleted"
              class="btn-ghost px-2 py-1 text-xs text-debit hover:text-red-700"
              title="Delete"
              @click.stop="deleter.confirmDelete(row as CategoryOut)"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              v-else
              class="btn-ghost px-2 py-1 text-xs text-credit hover:text-green-700"
              title="Restore"
              @click.stop="deleter.confirmRestore(row as CategoryOut)"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
            </button>

            <!-- Activate / Deactivate -->
            <button
              v-if="(row as CategoryOut).is_active"
              class="btn-ghost px-2 py-1 text-xs text-amber-600 hover:text-amber-700"
              title="Deactivate"
              @click.stop="activator.confirmDeactivate(row as CategoryOut)"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              v-else
              class="btn-ghost px-2 py-1 text-xs text-credit hover:text-green-700"
              title="Activate"
              @click.stop="activator.confirmActivate(row as CategoryOut)"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- ─── Create / Edit Modal ──────────────────────────────────────── -->
    <Modal
      :open="showModal"
      :title="formMode === 'create' ? 'Add Category' : 'Edit Category'"
      size="md"
      @close="closeModal"
    >
      <template #body>
        <CategoryForm
          :mode="formMode"
          :item-id="formItemId"
          @saved="handleFormSaved"
          @cancel="closeModal"
        />
      </template>
    </Modal>

    <!-- ─── Delete / Restore Confirm ─────────────────────────────────── -->
    <ConfirmDialog
      :open="deleter.showConfirm.value"
      :title="deleter.dialogTitle.value"
      :message="deleter.dialogMessage.value"
      :variant="deleter.dialogVariant.value"
      :confirm-text="deleter.confirmText.value"
      :loading="deleter.loading.value"
      @confirm="deleter.execute()"
      @cancel="deleter.cancel()"
    />

    <!-- ─── Activate / Deactivate Confirm ────────────────────────────── -->
    <ConfirmDialog
      :open="activator.showConfirm.value"
      :title="activator.dialogTitle.value"
      :message="activator.dialogMessage.value"
      :variant="activator.dialogVariant.value"
      :confirm-text="activator.confirmText.value"
      :loading="activator.loading.value"
      @confirm="activator.execute()"
      @cancel="activator.cancel()"
    />
  </div>
</template>
