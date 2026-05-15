<script setup lang="ts">
/**
 * DebtsPage — Tabbed card layout for Debt entities.
 *
 * Features:
 *   - Two tabs: "Money I Owe" (MONEY_BORROWED) and "Money Owed to Me" (MONEY_LENT)
 *   - Summary bar at top: Total Borrowed, Total Lent, Net Position
 *   - Each debt card shows: Name, entity_name, debt_type badge, principal,
 *     remaining balance, progress bar, interest rate, monthly payment,
 *     next payment date
 *   - Filter by debt_nature, debt_type, is_active
 *   - Create/Edit via DebtForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Activate/Deactivate via ConfirmDialog + useActivator
 *   - Pagination via useLedgerPagination
 *   - EmptyState, LoadingSkeleton
 *
 * Registers as `ldgr-debts-page` custom element.
 */

import { ref, computed, onMounted } from "vue";
import {
  Modal,
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  ProgressBar,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import type { FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useDebtStore } from "@/stores/debt";
import type {
  DebtFacilityOut,
  DebtFacilityFilter,
} from "@/lib/ledgerTypes";
import DebtForm from "./DebtForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrDebtsPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useDebtStore();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string | number, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(num);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString();
}

// ─── Type Maps ───────────────────────────────────────────────────────────────

const debtTypeMap = {
  mortgage: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  personal: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  student: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  auto: { bg: "bg-emerald-100 dark:bg-emerald-950/50", text: "text-emerald-800 dark:text-emerald-300" },
  business: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  informal: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

const debtStatusColorMap = {
  active: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  inactive: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-600 dark:text-slate-400", dot: "bg-slate-400" },
};

// ─── Active Tab ──────────────────────────────────────────────────────────────

const activeTab = ref<"borrowed" | "lent">("borrowed");

function switchTab(tab: "borrowed" | "lent") {
  activeTab.value = tab;
  // Apply the filter based on tab
  const nature = tab === "borrowed" ? "MONEY_BORROWED" : "MONEY_LENT";
  setFilter("debt_nature", nature);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Summary ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  await store.fetchSummary();
  // Set initial filter based on default tab
  setFilter("debt_nature", "MONEY_BORROWED");
  applyFilters();
});

const summary = computed(() => store.summary);

// ─── Filters ─────────────────────────────────────────────────────────────────

const {
  filters,
  setFilter,
  setFilters,
  resetFilters,
  applyFilters,
  applyPage,
  loading: filtersLoading,
  hasActiveFilters,
} = useLedgerFilters<DebtFacilityFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0, debt_nature: "MONEY_BORROWED" },
  syncKeys: ["debt_nature", "debt_type", "is_active", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "debt_type",
    label: "Debt Type",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "Mortgage", value: "MORTGAGE" },
      { label: "Personal", value: "PERSONAL" },
      { label: "Student", value: "STUDENT" },
      { label: "Auto", value: "AUTO" },
      { label: "Business", value: "BUSINESS" },
      { label: "Informal", value: "INFORMAL" },
    ],
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as DebtFacilityFilter,
  (partial) => store.setFilters(partial as Partial<DebtFacilityFilter>),
);

// ─── Search ──────────────────────────────────────────────────────────────────

const searchQuery = ref("");

function handleSearch(query: string) {
  searchQuery.value = query;
  setFilter("search", query || null);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Filter Change Handler ───────────────────────────────────────────────────

function handleFilterChange(key: string, value: unknown) {
  setFilter(key as keyof DebtFacilityFilter, value as string | null);
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
  setFilter("debt_nature", activeTab.value === "borrowed" ? "MONEY_BORROWED" : "MONEY_LENT");
  applyFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<DebtFacilityFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<DebtFacilityOut>({
  store,
  entityName: "Debt",
  getEntityLabel: (item) => item.name,
  onDeleted: () => {
    applyFilters();
    store.fetchSummary(true);
  },
  onRestored: () => {
    applyFilters();
    store.fetchSummary(true);
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<DebtFacilityOut>({
  store,
  entityName: "Debt",
  getEntityLabel: (item) => item.name,
  onActivated: () => {
    applyFilters();
    store.fetchSummary(true);
  },
  onDeactivated: () => {
    applyFilters();
    store.fetchSummary(true);
  },
});

// ─── Create / Edit Modal ─────────────────────────────────────────────────────

const showFormModal = ref(false);
const formMode = ref<"create" | "edit">("create");
const editingItemId = ref<number | undefined>(undefined);

function openCreateForm() {
  formMode.value = "create";
  editingItemId.value = undefined;
  showFormModal.value = true;
}

function openEditForm(item: DebtFacilityOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: DebtFacilityOut) {
  closeFormModal();
  applyFilters();
  store.fetchSummary(true);
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateToDetail(item: DebtFacilityOut) {
  window.location.href = `/dashboard/debts/${item.id}`;
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onEditClick(event: Event, item: DebtFacilityOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onDeleteClick(event: Event, item: DebtFacilityOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: DebtFacilityOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onActivateClick(event: Event, item: DebtFacilityOut) {
  event.stopPropagation();
  activator.confirmActivate(item);
}

function onDeactivateClick(event: Event, item: DebtFacilityOut) {
  event.stopPropagation();
  activator.confirmDeactivate(item);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);

const progressColor = (percent: number): string => {
  if (percent >= 80) return "bg-green-500";
  if (percent >= 50) return "bg-cyan-500";
  if (percent >= 25) return "bg-amber-500";
  return "bg-red-500";
};
</script>

<template>
  <FeatureGate feature="debts" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Debts</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Track money you owe and money owed to you
        </p>
      </div>
      <button class="btn-primary" @click="openCreateForm">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Add Debt
      </button>
    </div>

    <!-- ── Summary Bar ────────────────────────────────────────────────────── -->
    <div
      v-if="summary"
      class="grid grid-cols-1 sm:grid-cols-3 gap-4"
    >
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Borrowed</p>
        <p class="text-xl font-bold text-red-600 dark:text-red-400">
          {{ formatCurrency(summary.total_borrowed) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Lent</p>
        <p class="text-xl font-bold text-green-600 dark:text-green-400">
          {{ formatCurrency(summary.total_lent) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Net Position</p>
        <p
          :class="[
            'text-xl font-bold',
            parseFloat(summary.net_position) >= 0
              ? 'text-green-600 dark:text-green-400'
              : 'text-red-600 dark:text-red-400',
          ]"
        >
          {{ formatCurrency(summary.net_position) }}
        </p>
      </div>
    </div>

    <!-- ── Tabs: Money I Owe / Money Owed to Me ────────────────────────────── -->
    <div class="border-b border-navy-200 dark:border-navy-700">
      <nav class="flex gap-6 -mb-px" aria-label="Debt tabs">
        <button
          :class="[
            'pb-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === 'borrowed'
              ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
              : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
          ]"
          @click="switchTab('borrowed')"
        >
          Money I Owe
        </button>
        <button
          :class="[
            'pb-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === 'lent'
              ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
              : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
          ]"
          @click="switchTab('lent')"
        >
          Money Owed to Me
        </button>
      </nav>
    </div>

    <!-- ── Search + Filters ───────────────────────────────────────────────── -->
    <div class="space-y-3">
      <SearchInput
        v-model="searchQuery"
        placeholder="Search debts by name or entity..."
        @search="handleSearch"
      />
      <FilterBar
        :filters="filterConfigs"
        :model-value="{}"
        :loading="isLoading"
        @filter-change="handleFilterChange"
        @reset="handleFilterReset"
        @update:model-value="handleFilterModelUpdate"
      />
    </div>

    <!-- ── Loading State ──────────────────────────────────────────────────── -->
    <LoadingSkeleton v-if="isLoading && !hasItems" type="card" :rows="4" />

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!isLoading && !hasItems"
      icon="credit-card"
      :title="activeTab === 'borrowed' ? 'No debts owed' : 'No money lent'"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : activeTab === 'borrowed'
          ? 'Add a debt you owe to start tracking payments.'
          : 'Add money someone owes you to start tracking.'"
      :action-label="hasActiveFilters ? '' : 'Add Debt'"
      @action="openCreateForm"
    />

    <!-- ── Debt Cards ─────────────────────────────────────────────────────── -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 gap-4"
    >
      <div
        v-for="debt in store.items"
        :key="debt.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-700 hover:-translate-y-0.5 group"
        :class="{
          'opacity-60': !debt.is_active || debt.is_deleted,
        }"
        role="button"
        :aria-label="`View ${debt.name} details`"
        tabindex="0"
        @click="navigateToDetail(debt as DebtFacilityOut)"
        @keydown.enter="navigateToDetail(debt as DebtFacilityOut)"
      >
        <!-- Header: Name + Entity + Type Badge -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate">
              {{ (debt as DebtFacilityOut).name }}
            </h3>
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400 truncate">
              {{ (debt as DebtFacilityOut).entity_name }}
            </p>
            <p
              v-if="(debt as DebtFacilityOut).is_deleted"
              class="text-xs text-debit mt-0.5"
            >
              Deleted
            </p>
          </div>
          <TypeBadge
            :type="(debt as DebtFacilityOut).debt_type"
            :type-map="debtTypeMap"
            :show-icon="false"
            size="sm"
          />
        </div>

        <!-- Principal + Remaining -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Principal</p>
            <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ formatCurrency((debt as DebtFacilityOut).principal_amount, (debt as DebtFacilityOut).currency || "USD") }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Remaining</p>
            <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ formatCurrency((debt as DebtFacilityOut).remaining_balance, (debt as DebtFacilityOut).currency || "USD") }}
            </p>
          </div>
        </div>

        <!-- Progress Bar -->
        <div class="mb-3">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">Paid off</span>
            <span class="text-xs font-medium text-navy-900 dark:text-navy-100">
              {{ (debt as DebtFacilityOut).progress_percent }}%
            </span>
          </div>
          <div class="h-2 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
            <div
              :class="['h-full rounded-full transition-all duration-500', progressColor((debt as DebtFacilityOut).progress_percent)]"
              :style="{ width: `${Math.min((debt as DebtFacilityOut).progress_percent, 100)}%` }"
            />
          </div>
        </div>

        <!-- Interest Rate + Monthly Payment -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Interest Rate</p>
            <p class="text-sm text-navy-900 dark:text-navy-100">
              {{ parseFloat((debt as DebtFacilityOut).interest_rate || "0").toFixed(2) }}%
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Monthly Payment</p>
            <p class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatCurrency((debt as DebtFacilityOut).monthly_payment, (debt as DebtFacilityOut).currency || "USD") }}
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Edit debt"
            :aria-label="`Edit ${(debt as DebtFacilityOut).name}`"
            @click="onEditClick($event, debt as DebtFacilityOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Activate/Deactivate -->
          <button
            v-if="(debt as DebtFacilityOut).is_active && !(debt as DebtFacilityOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            title="Deactivate debt"
            :aria-label="`Deactivate ${(debt as DebtFacilityOut).name}`"
            @click="onDeactivateClick($event, debt as DebtFacilityOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else-if="!(debt as DebtFacilityOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
            title="Activate debt"
            :aria-label="`Activate ${(debt as DebtFacilityOut).name}`"
            @click="onActivateClick($event, debt as DebtFacilityOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!(debt as DebtFacilityOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete debt"
            :aria-label="`Delete ${(debt as DebtFacilityOut).name}`"
            @click="onDeleteClick($event, debt as DebtFacilityOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore debt"
            :aria-label="`Restore ${(debt as DebtFacilityOut).name}`"
            @click="onRestoreClick($event, debt as DebtFacilityOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ── Pagination ─────────────────────────────────────────────────────── -->
    <div
      v-if="pagination.showPagination.value && hasItems"
      class="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-navy-200 dark:border-navy-700"
    >
      <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
        {{ pagination.showingRange.value }}
      </p>
      <div class="flex items-center gap-1">
        <button
          class="btn-ghost px-3 py-1.5 text-sm"
          :disabled="!pagination.hasPrev.value"
          @click="goToPage(pagination.currentPage.value - 1)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
        <template v-for="page in pagination.totalPages.value" :key="page">
          <button
            v-if="page <= 7 || Math.abs(page - pagination.currentPage.value) <= 1 || page === pagination.totalPages.value"
            :class="[
              'px-3 py-1.5 text-sm rounded-lg transition-colors',
              page === pagination.currentPage.value
                ? 'bg-cyan-600 text-white'
                : 'btn-ghost',
            ]"
            @click="goToPage(page)"
          >
            {{ page }}
          </button>
          <span
            v-else-if="page === 2 || page === pagination.totalPages.value - 1"
            class="px-1 text-slate-custom-400"
          >
            &hellip;
          </span>
        </template>
        <button
          class="btn-ghost px-3 py-1.5 text-sm"
          :disabled="!pagination.hasNext.value"
          @click="goToPage(pagination.currentPage.value + 1)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- ── Create / Edit Modal ────────────────────────────────────────────── -->
    <DebtForm
      :mode="formMode"
      :item-id="editingItemId"
      :open="showFormModal"
      :default-nature="activeTab === 'borrowed' ? 'MONEY_BORROWED' : 'MONEY_LENT'"
      @saved="handleFormSaved"
      @cancel="closeFormModal"
    />

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
    <UpgradePrompt feature="debts" />
  </template>
  </FeatureGate>
</template>
