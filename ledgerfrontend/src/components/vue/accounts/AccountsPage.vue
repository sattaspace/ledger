<script setup lang="ts">
/**
 * AccountsPage — Main list page for Account entities.
 *
 * Provides a full-featured CRUD list view with search, filtering,
 * sorting, pagination, and inline actions (edit, delete/restore,
 * activate/deactivate). Uses the shared reusable component library
 * and Pinia store composables.
 *
 * Registered as `ldgr-accounts-page` custom element for
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
  useDropdownLoader,
} from "@/composables";
import { useAccountStore } from "@/stores/account";
import { useInstitutionStore } from "@/stores/institution";
import type {
  AccountOut,
  AccountFilter,
} from "@/lib/ledgerTypes";
import { formatCurrency } from "@/lib/currency";
import AccountForm from "./AccountForm.vue";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "AccountsPage" });

// ─── Stores ──────────────────────────────────────────────────────────────────

const store = useAccountStore();
const institutionStore = useInstitutionStore();
const dropdownLoader = useDropdownLoader();

// ─── Table Columns ────────────────────────────────────────────────────────────

const columns: DataTableColumn[] = [
  { key: "name", label: "Account", sortable: true },
  { key: "institution_id", label: "Institution", sortable: true },
  { key: "account_type", label: "Type", sortable: true },
  { key: "current_balance", label: "Balance", sortable: true, align: "right" as const },
  { key: "currency", label: "Currency" },
  { key: "is_active", label: "Status", sortable: true },
  { key: "actions", label: "Actions", align: "right" as const },
];

// ─── Filter Configuration ─────────────────────────────────────────────────────

const accountFilterOptions: FilterConfig[] = [
  {
    key: "account_type",
    label: "Type",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "Asset", value: "ASSET" },
      { label: "Liability", value: "LIABILITY" },
      { label: "Investment", value: "INVESTMENT" },
    ],
  },
  {
    key: "is_active",
    label: "Active Only",
    type: "toggle",
  },
];

// ─── Filters ──────────────────────────────────────────────────────────────────

const defaultFilters: Partial<AccountFilter> = {
  limit: 25,
  offset: 0,
};

const {
  filters,
  setFilter,
  resetFilters,
  applyFilters,
  applyPage,
  loading: filtersLoading,
  hasActiveFilters,
} = useLedgerFilters<AccountFilter>({
  store,
  defaultFilters,
  syncKeys: ["account_type", "search"],
});

// ─── Search ───────────────────────────────────────────────────────────────────

const searchQuery = ref("");

function handleSearch(query: string): void {
  searchQuery.value = query;
  setFilter("search", query || null);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Filter Bar Handlers ──────────────────────────────────────────────────────

function handleFilterChange(key: string, value: unknown): void {
  if (key === "is_active") {
    setFilter("is_active" as keyof AccountFilter, value ? true : null);
  } else {
    setFilter(key as keyof AccountFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset(): void {
  searchQuery.value = "";
  resetFilters();
}

// ─── Pagination ───────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters,
  (partial) => store.setFilters(partial as Partial<AccountFilter>),
);

function handlePageChange(page: number): void {
  pagination.goToPage(page);
  applyPage(page);
}

function handleSortChange(payload: { key: string; direction: "asc" | "desc" }): void {
  // Client-side sorting handled by DataTable;
  // For server-side sorting, update filters here.
  void payload;
}

// ─── Soft Delete / Restore ────────────────────────────────────────────────────

const deleter = useSoftDelete<AccountOut>({
  store,
  entityName: "Account",
  refreshListAfter: true,
});

// ─── Activate / Deactivate ────────────────────────────────────────────────────

const activator = useActivator<AccountOut>({
  store,
  entityName: "Account",
  refreshListAfter: true,
  confirmActivate: true,
});

// ─── Form Modal ───────────────────────────────────────────────────────────────

const showFormModal = ref(false);
const formMode = ref<"create" | "edit">("create");
const editItemId = ref<number | undefined>(undefined);

function openCreateModal(): void {
  formMode.value = "create";
  editItemId.value = undefined;
  showFormModal.value = true;
}

function openEditModal(item: AccountOut): void {
  formMode.value = "edit";
  editItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal(): void {
  showFormModal.value = false;
  formMode.value = "create";
  editItemId.value = undefined;
}

function handleFormSaved(_item: AccountOut): void {
  closeFormModal();
  store.invalidate();
  store.fetchList();
}

function handleFormCancel(): void {
  closeFormModal();
}

// ─── Action Handlers ──────────────────────────────────────────────────────────

function handleDelete(item: AccountOut): void {
  deleter.confirmDelete(item);
}

function handleRestore(item: AccountOut): void {
  deleter.confirmRestore(item);
}

function handleToggleActive(item: AccountOut): void {
  activator.confirmToggle(item);
}

// ─── Navigate to Detail ───────────────────────────────────────────────────────

function navigateToDetail(item: AccountOut): void {
  if (typeof window !== "undefined") {
    window.location.href = `/dashboard/accounts/${item.id}`;
  }
}

// ─── Type Badge Styling ───────────────────────────────────────────────────────

const accountTypeMap = {
  asset: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300" },
  liability: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300" },
  investment: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
};

// ─── Institution Name Lookup ──────────────────────────────────────────────────

function getInstitutionName(institutionId: number): string {
  const inst = institutionStore.dropdown.find((i) => i.id === institutionId);
  return inst?.name ?? `Institution #${institutionId}`;
}

// ─── Balance Formatting ───────────────────────────────────────────────────────

function formatBalance(item: AccountOut): string {
  return formatCurrency(item.current_balance, item.currency, { displayMode: "symbol" });
}

function balanceColor(item: AccountOut): string {
  if (item.account_type === "LIABILITY") return "text-debit";
  return parseFloat(item.current_balance) >= 0 ? "text-credit" : "text-debit";
}

// ─── Computed ─────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);

// ─── Initial Load ─────────────────────────────────────────────────────────────

onMounted(async () => {
  // Load institution dropdown for lookups
  await dropdownLoader.loadDropdown("institutions", institutionStore);

  if (!store.listLoaded) {
    store.fetchList();
  }
});
</script>

<template>
  <FeatureGate feature="accounts" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
          Accounts
        </h1>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Manage your bank accounts, credit cards, investment accounts, and wallets.
        </p>
      </div>
      <button class="btn-primary" @click="openCreateModal">
        <!-- Plus Icon -->
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Add Account
      </button>
    </div>

    <!-- ── Search & Filters ───────────────────────────────────────────────── -->
    <div class="card p-4 space-y-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
        <!-- Search -->
        <div class="flex-1 max-w-md">
          <SearchInput
            v-model="searchQuery"
            placeholder="Search accounts by name..."
            @search="handleSearch"
          />
        </div>
        <!-- Filter Bar -->
        <FilterBar
          :filters="accountFilterOptions"
          :model-value="{
            account_type: (filters as Record<string, unknown>).account_type ?? '',
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
      title="No accounts found"
      :description="hasActiveFilters
        ? 'No accounts match your current filters. Try adjusting or resetting them.'
        : 'Get started by adding your first account.'"
      icon="credit-card"
      :action-label="hasActiveFilters ? '' : 'Add Account'"
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
        <!-- Account Name Column -->
        <template #cell-name="{ row }">
          <div class="flex items-center gap-3 cursor-pointer" @click="navigateToDetail(row as AccountOut)">
            <!-- Color Indicator -->
            <span
              v-if="(row as AccountOut).color"
              class="h-3 w-3 rounded-full flex-shrink-0 border border-navy-200 dark:border-navy-700"
              :style="{ backgroundColor: (row as AccountOut).color || undefined }"
              :aria-hidden="true"
            />
            <div>
              <p class="font-medium text-navy-900 dark:text-navy-100 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors">
                {{ (row as AccountOut).name }}
              </p>
              <p
                v-if="(row as AccountOut).is_deleted"
                class="text-xs text-debit"
              >
                Deleted
              </p>
            </div>
          </div>
        </template>

        <!-- Institution Column -->
        <template #cell-institution_id="{ row }">
          <span class="text-sm text-navy-900 dark:text-navy-100">
            {{ getInstitutionName((row as AccountOut).institution_id) }}
          </span>
        </template>

        <!-- Type Column -->
        <template #cell-account_type="{ row }">
          <TypeBadge
            :type="(row as AccountOut).account_type"
            :type-map="accountTypeMap"
            :show-icon="false"
          />
        </template>

        <!-- Balance Column -->
        <template #cell-current_balance="{ row }">
          <span :class="['text-sm font-semibold', balanceColor(row as AccountOut)]">
            {{ formatBalance(row as AccountOut) }}
          </span>
          <p
            v-if="(row as AccountOut).available_credit"
            class="text-xs text-slate-custom-500 mt-0.5"
          >
            Available: {{ formatCurrency((row as AccountOut).available_credit!, (row as AccountOut).currency, { displayMode: "symbol" }) }}
          </p>
        </template>

        <!-- Currency Column -->
        <template #cell-currency="{ row }">
          <span class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
            {{ (row as AccountOut).currency }}
          </span>
        </template>

        <!-- Status Column -->
        <template #cell-is_active="{ row }">
          <StatusBadge
            :status="(row as AccountOut).is_active ? 'Active' : 'Inactive'"
          />
        </template>

        <!-- Actions Column -->
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <!-- Edit -->
            <button
              class="btn-ghost px-2 py-1 text-sm"
              title="Edit account"
              aria-label="Edit account"
              @click.stop="openEditModal(row as AccountOut)"
            >
              <!-- Pencil Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="(row as AccountOut).is_deleted"
              class="btn-ghost px-2 py-1 text-sm text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
              title="Restore account"
              aria-label="Restore account"
              @click.stop="handleRestore(row as AccountOut)"
            >
              <!-- Restore Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              v-else
              class="btn-ghost px-2 py-1 text-sm text-debit hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              title="Delete account"
              aria-label="Delete account"
              @click.stop="handleDelete(row as AccountOut)"
            >
              <!-- Trash Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>

            <!-- Activate / Deactivate -->
            <button
              v-if="(row as AccountOut).is_active"
              class="btn-ghost px-2 py-1 text-sm text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
              title="Deactivate account"
              aria-label="Deactivate account"
              @click.stop="handleToggleActive(row as AccountOut)"
            >
              <!-- Pause/Deactivate Icon -->
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
            </button>
            <button
              v-else
              class="btn-ghost px-2 py-1 text-sm text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
              title="Activate account"
              aria-label="Activate account"
              @click.stop="handleToggleActive(row as AccountOut)"
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
      :title="formMode === 'create' ? 'Add Account' : 'Edit Account'"
      size="lg"
      @close="closeFormModal"
    >
      <template #body>
        <AccountForm
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
    <UpgradePrompt feature="accounts" />
  </template>
  </FeatureGate>
</template>
