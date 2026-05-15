<script setup lang="ts">
/**
 * InstitutionsPage — Main list page for Institution entities (4.2.1).
 *
 * Provides a full-featured CRUD list view with search, filtering,
 * sorting, pagination, and inline actions (edit, delete/restore,
 * activate/deactivate). Uses the shared reusable component library
 * and Pinia store composables.
 *
 * Registered as `ldgr-institutions-page` custom element for
 * Astro's `client:only="vue"` island pattern.
 */

import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  DataTable,
  Modal,
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import type { DataTableColumn, FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useInstitutionStore } from "@/stores/institution";
import type {
  InstitutionOut,
  InstitutionFilter,
} from "@/lib/ledgerTypes";
import InstitutionForm from "./InstitutionForm.vue";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "InstitutionsPage" });

// ─── Store ─────────────────────────────────────────────────────────────────────

const store = useInstitutionStore();

// ─── Table Columns ─────────────────────────────────────────────────────────────

const columns: DataTableColumn[] = [
  { key: "name", label: "Name", sortable: true },
  { key: "institution_type", label: "Type", sortable: true },
  { key: "website", label: "Website" },
  { key: "is_active", label: "Status", sortable: true },
  { key: "actions", label: "Actions", align: "right" as const },
];

// ─── Filter Configuration ──────────────────────────────────────────────────────

const institutionTypeFilterOptions: FilterConfig[] = [
  {
    key: "institution_type",
    label: "Type",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "Bank", value: "BANK" },
      { label: "Credit Union", value: "CREDIT_UNION" },
      { label: "Brokerage", value: "BROKERAGE" },
      { label: "Crypto", value: "CRYPTO" },
      { label: "Wallet", value: "WALLET" },
      { label: "Other", value: "OTHER" },
    ],
  },
  {
    key: "is_active",
    label: "Active Only",
    type: "toggle",
  },
];

// ─── Filters ───────────────────────────────────────────────────────────────────

const defaultFilters: Partial<InstitutionFilter> = {
  limit: 25,
  offset: 0,
};

const {
  filters,
  setFilter,
  setFilters,
  resetFilters,
  applyFilters,
  applyPage,
  loading: filtersLoading,
  hasActiveFilters,
} = useLedgerFilters<InstitutionFilter>({
  store,
  defaultFilters,
  syncKeys: ["institution_type", "search"],
});

// ─── Search ────────────────────────────────────────────────────────────────────

const searchQuery = ref("");

function handleSearch(query: string): void {
  searchQuery.value = query;
  setFilter("search", query || null);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Filter Bar Handlers ───────────────────────────────────────────────────────

function handleFilterChange(key: string, value: unknown): void {
  if (key === "is_active") {
    setFilter("is_active" as keyof InstitutionFilter, value ? true : null);
  } else {
    setFilter(key as keyof InstitutionFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset(): void {
  searchQuery.value = "";
  resetFilters();
}

// ─── Pagination ────────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters,
  (partial) => store.setFilters(partial as Partial<InstitutionFilter>),
);

function handlePageChange(page: number): void {
  pagination.goToPage(page);
  applyPage(page);
}

function handleSortChange(payload: { key: string; direction: "asc" | "desc" }): void {
  // Client-side sorting is handled by DataTable;
  // For server-side sorting, you would update filters here.
  void payload;
}

// ─── Soft Delete / Restore ────────────────────────────────────────────────────

const deleter = useSoftDelete<InstitutionOut>({
  store,
  entityName: "Institution",
  refreshListAfter: true,
});

// ─── Activate / Deactivate ────────────────────────────────────────────────────

const activator = useActivator<InstitutionOut>({
  store,
  entityName: "Institution",
  refreshListAfter: true,
  confirmActivate: true,
});

// ─── Form Modal ────────────────────────────────────────────────────────────────

const showFormModal = ref(false);
const formMode = ref<"create" | "edit">("create");
const editItemId = ref<number | undefined>(undefined);

function openCreateModal(): void {
  formMode.value = "create";
  editItemId.value = undefined;
  showFormModal.value = true;
}

function openEditModal(item: InstitutionOut): void {
  formMode.value = "edit";
  editItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal(): void {
  showFormModal.value = false;
  formMode.value = "create";
  editItemId.value = undefined;
}

function handleFormSaved(_item: InstitutionOut): void {
  closeFormModal();
  // Refresh the list to show the new/updated item
  store.invalidate();
  store.fetchList();
}

function handleFormCancel(): void {
  closeFormModal();
}

// ─── Action Handlers ──────────────────────────────────────────────────────────

function handleDelete(item: InstitutionOut): void {
  deleter.confirmDelete(item);
}

function handleRestore(item: InstitutionOut): void {
  deleter.confirmRestore(item);
}

function handleToggleActive(item: InstitutionOut): void {
  activator.confirmToggle(item);
}

// ─── Type Badge Styling ────────────────────────────────────────────────────────

const institutionTypeMap = {
  bank: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  credit_union: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300" },
  brokerage: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  crypto: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  wallet: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  other: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

// ─── Computed ──────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);

// ─── Initial Load ──────────────────────────────────────────────────────────────

onMounted(() => {
  if (!store.listLoaded) {
    store.fetchList();
  }
});
</script>

<template>
  <FeatureGate feature="institutions" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
          Institutions
        </h1>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Manage your banks, credit unions, brokerages, and other financial institutions.
        </p>
      </div>
      <button class="btn-primary" @click="openCreateModal">
        <!-- Plus Icon -->
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Add Institution
      </button>
    </div>

    <!-- ── Search & Filters ───────────────────────────────────────────────── -->
    <div class="card p-4 space-y-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
        <!-- Search -->
        <div class="flex-1 max-w-md">
          <SearchInput
            v-model="searchQuery"
            placeholder="Search institutions by name..."
            @search="handleSearch"
          />
        </div>
        <!-- Filter Bar -->
        <FilterBar
          :filters="institutionTypeFilterOptions"
          :model-value="{
            institution_type: (filters as Record<string, unknown>).institution_type ?? '',
            is_active: (filters as Record<string, unknown>).is_active ?? false,
          }"
          :loading="isLoading"
          @filter-change="handleFilterChange"
          @reset="handleFilterReset"
        />
      </div>
    </div>

    <!-- ── Loading State ──────────────────────────────────────────────────── -->
    <div v-if="isLoading && !hasItems" class="card overflow-hidden">
      <LoadingSkeleton type="table" :rows="6" />
    </div>

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!hasItems && !isLoading"
      title="No institutions found"
      :description="hasActiveFilters
        ? 'No institutions match your current filters. Try adjusting or resetting them.'
        : 'Get started by adding your first financial institution.'"
      icon="credit-card"
      :action-label="hasActiveFilters ? '' : 'Add Institution'"
      @action="openCreateModal"
    />

    <!-- ── Data Table ─────────────────────────────────────────────────────── -->
    <div v-else class="card overflow-hidden">
      <DataTable
        :columns="columns"
        :rows="(store.items as Record<string, unknown>[])"
        :loading="isLoading"
        :total="store.total"
        :limit="pagination.limit.value"
        :offset="pagination.offset.value"
        @page-change="handlePageChange"
        @sort-change="handleSortChange"
      >
        <!-- Name Column -->
        <template #cell-name="{ row }">
          <div class="flex items-center gap-3">
            <!-- Color Indicator -->
            <span
              v-if="(row as InstitutionOut).color"
              class="h-3 w-3 rounded-full flex-shrink-0 border border-navy-200 dark:border-navy-700"
              :style="{ backgroundColor: (row as InstitutionOut).color || undefined }"
              :aria-hidden="true"
            />
            <div>
              <p class="font-medium text-navy-900 dark:text-navy-100">
                {{ (row as InstitutionOut).name }}
              </p>
              <p
                v-if="(row as InstitutionOut).is_deleted"
                class="text-xs text-debit"
              >
                Deleted
              </p>
            </div>
          </div>
        </template>

        <!-- Type Column -->
        <template #cell-institution_type="{ row }">
          <TypeBadge
            :type="(row as InstitutionOut).institution_type"
            :type-map="institutionTypeMap"
            :show-icon="false"
          />
        </template>

        <!-- Website Column -->
        <template #cell-website="{ row }">
          <a
            v-if="(row as InstitutionOut).website"
            :href="(row as InstitutionOut).website"
            target="_blank"
            rel="noopener noreferrer"
            class="text-cyan-600 hover:text-cyan-700 dark:text-cyan-400 dark:hover:text-cyan-300 text-sm truncate max-w-[200px] inline-block transition-colors"
          >
            {{ (row as InstitutionOut).website.replace(/^https?:\/\//, "") }}
            <!-- External link icon -->
            <svg class="inline h-3 w-3 ml-0.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
              <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
            </svg>
          </a>
          <span v-else class="text-slate-custom-400 dark:text-slate-custom-500 text-sm">
            &mdash;
          </span>
        </template>

        <!-- Status Column -->
        <template #cell-is_active="{ row }">
          <StatusBadge
            :status="(row as InstitutionOut).is_active ? 'Active' : 'Inactive'"
          />
        </template>

        <!-- Actions Column -->
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <!-- Edit -->
            <button
              class="btn-ghost px-2 py-1 text-sm"
              title="Edit institution"
              aria-label="Edit institution"
              @click.stop="openEditModal(row as InstitutionOut)"
            >
              <!-- Pencil Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="(row as InstitutionOut).is_deleted"
              class="btn-ghost px-2 py-1 text-sm text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
              title="Restore institution"
              aria-label="Restore institution"
              @click.stop="handleRestore(row as InstitutionOut)"
            >
              <!-- Restore Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              v-else
              class="btn-ghost px-2 py-1 text-sm text-debit hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              title="Delete institution"
              aria-label="Delete institution"
              @click.stop="handleDelete(row as InstitutionOut)"
            >
              <!-- Trash Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>

            <!-- Activate / Deactivate -->
            <button
              v-if="(row as InstitutionOut).is_active"
              class="btn-ghost px-2 py-1 text-sm text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
              title="Deactivate institution"
              aria-label="Deactivate institution"
              @click.stop="handleToggleActive(row as InstitutionOut)"
            >
              <!-- Pause/Deactivate Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              v-else
              class="btn-ghost px-2 py-1 text-sm text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
              title="Activate institution"
              aria-label="Activate institution"
              @click.stop="handleToggleActive(row as InstitutionOut)"
            >
              <!-- Play/Activate Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </template>
      </DataTable>
    </div>

    <!-- ── Create / Edit Modal ────────────────────────────────────────────── -->
    <Modal
      :open="showFormModal"
      :title="formMode === 'create' ? 'Add Institution' : 'Edit Institution'"
      size="lg"
      @close="closeFormModal"
    >
      <template #body>
        <InstitutionForm
          :mode="formMode"
          :item-id="editItemId"
          @saved="handleFormSaved"
          @cancel="handleFormCancel"
        />
      </template>
    </Modal>

    <!-- ── Soft Delete / Restore Confirm ──────────────────────────────────── -->
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

    <!-- ── Activate / Deactivate Confirm ──────────────────────────────────── -->
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
  <template #no-access>
    <UpgradePrompt feature="institutions" />
  </template>
  </FeatureGate>
</template>
