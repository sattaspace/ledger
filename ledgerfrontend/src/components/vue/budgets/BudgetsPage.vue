<script setup lang="ts">
/**
 * BudgetsPage — Card grid layout for Budget listing.
 *
 * Features:
 *   - Summary stats row (Total Budget, Total Spent, Total Remaining, Average Usage)
 *   - FilterBar with period, category, and currency filters
 *   - Card grid (3/2/1 columns) with budget cards
 *   - Each card: category, amount, spent, remaining, progress, period badge,
 *     rollover indicator, status badge, action buttons
 *   - Create/Edit via BudgetForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Activate/Deactivate via ConfirmDialog + useActivator
 *   - Click card → navigate to /dashboard/budgets/{id}
 *   - EmptyState when no budgets
 *
 * Registers as `ldgr-budgets-page` custom element.
 */

import {
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  ProgressBar,
} from "@/components/vue";
import type { FilterConfig, TypeStyleMap } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
  useDropdownLoader,
} from "@/composables";
import { useBudgetStore } from "@/stores/budget";
import { useCategoryStore } from "@/stores/category";
import { formatCurrency } from "@/lib/currency";
import type { BudgetOut, BudgetFilter, BudgetPeriod } from "@/lib/ledgerTypes";
import BudgetForm from "./BudgetForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrBudgetsPage",
});

// ─── Stores ──────────────────────────────────────────────────────────────────

const budgetStore = useBudgetStore();
const categoryStore = useCategoryStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await dropdownLoader.loadDropdown("categories", categoryStore);
});

// ─── Category Lookup ─────────────────────────────────────────────────────────

const categoryMap = computed(() => {
  const map = new Map<number, string>();
  for (const cat of dropdownLoader.getDropdown<{ id: number; name: string }>("categories")) {
    map.set(cat.id, cat.name);
  }
  return map;
});

function getCategoryName(categoryId: number): string {
  return categoryMap.value.get(categoryId) ?? "Unknown Category";
}

// ─── Budget Period Type Map for TypeBadge ─────────────────────────────────────

const budgetPeriodTypeMap: TypeStyleMap = {
  weekly: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  monthly: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  yearly: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
};

// ─── Filters ─────────────────────────────────────────────────────────────────

const {
  filters,
  setFilter,
  setFilters,
  resetFilters,
  applyFilters,
  loading: filtersLoading,
  hasActiveFilters,
} = useLedgerFilters<BudgetFilter>({
  store: budgetStore,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["period", "currency", "category_id"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "period",
    label: "Period",
    type: "select",
    placeholder: "All Periods",
    options: [
      { label: "Weekly", value: "WEEKLY" },
      { label: "Monthly", value: "MONTHLY" },
      { label: "Yearly", value: "YEARLY" },
    ],
  },
  {
    key: "category_id",
    label: "Category",
    type: "select",
    placeholder: "All Categories",
    options: dropdownLoader
      .getDropdown<{ id: number; name: string }>("categories")
      .map((cat) => ({ label: cat.name, value: cat.id })),
  },
  {
    key: "currency",
    label: "Currency",
    type: "select",
    placeholder: "All Currencies",
    options: [
      { label: "USD", value: "USD" },
      { label: "EUR", value: "EUR" },
      { label: "BDT", value: "BDT" },
      { label: "GBP", value: "GBP" },
      { label: "CAD", value: "CAD" },
      { label: "AUD", value: "AUD" },
    ],
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => budgetStore.total,
  () => budgetStore.filters as BudgetFilter,
  (partial) => budgetStore.setFilters(partial as Partial<BudgetFilter>),
);

// ─── Filter Change Handler ───────────────────────────────────────────────────

function handleFilterChange(key: string, value: unknown) {
  setFilter(key as keyof BudgetFilter, value as string | number | boolean | null);
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  resetFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<BudgetFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Create / Edit Modal ─────────────────────────────────────────────────────

const showFormModal = ref(false);
const formMode = ref<"create" | "edit">("create");
const editingItemId = ref<number | undefined>(undefined);

function openCreateForm() {
  formMode.value = "create";
  editingItemId.value = undefined;
  showFormModal.value = true;
}

function openEditForm(item: BudgetOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: BudgetOut) {
  closeFormModal();
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<BudgetOut>({
  store: budgetStore,
  entityName: "Budget",
  getEntityLabel: (item) => getCategoryName(item.category_id),
  onDeleted: () => {
    applyFilters();
  },
  onRestored: () => {
    applyFilters();
  },
});

// ─── Activator ──────────────────────────────────────────────────────────────

const activator = useActivator<BudgetOut>({
  store: budgetStore,
  entityName: "Budget",
  refreshListAfter: true,
  onActivated: () => {
    applyFilters();
  },
  onDeactivated: () => {
    applyFilters();
  },
});

// ─── Navigation ─────────────────────────────────────────────────────────────

function navigateToDetail(item: BudgetOut) {
  window.location.href = `/dashboard/budgets/${item.id}`;
}

// ─── Spent Amount Color ─────────────────────────────────────────────────────

function getSpentColorClass(percentUsed: number): string {
  if (percentUsed >= 90) return "text-debit";
  if (percentUsed >= 70) return "text-amber-600 dark:text-amber-400";
  return "text-credit";
}

function getProgressColor(percentUsed: number): "green" | "amber" | "red" | "cyan" {
  if (percentUsed >= 90) return "red";
  if (percentUsed >= 70) return "amber";
  return "green";
}

// ─── Summary Stats Formatting ───────────────────────────────────────────────

const totalBudgetFormatted = computed(() =>
  formatCurrency(String(budgetStore.totalBudgetAmount), "USD"),
);

const totalSpentFormatted = computed(() =>
  formatCurrency(String(budgetStore.totalSpent), "USD"),
);

const totalRemainingFormatted = computed(() =>
  formatCurrency(String(budgetStore.totalRemaining), "USD"),
);

const averageUsageFormatted = computed(() =>
  `${Math.round(budgetStore.averagePercentUsed)}%`,
);

// ─── Action Button Stop Propagation ─────────────────────────────────────────

function onEditClick(event: Event, item: BudgetOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onDeleteClick(event: Event, item: BudgetOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: BudgetOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onToggleActiveClick(event: Event, item: BudgetOut) {
  event.stopPropagation();
  activator.confirmToggle(item);
}
</script>

<template>
  <div class="space-y-6">
    <!-- Page Header -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Budgets</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Track spending against your budget limits
        </p>
      </div>
      <button class="btn-primary" @click="openCreateForm">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Add Budget
      </button>
    </div>

    <!-- Summary Stats Row -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <!-- Total Budget -->
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Budget</p>
        <p class="text-lg font-bold text-navy-900 dark:text-navy-100 truncate">{{ totalBudgetFormatted }}</p>
      </div>
      <!-- Total Spent -->
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Spent</p>
        <p class="text-lg font-bold text-navy-900 dark:text-navy-100 truncate">{{ totalSpentFormatted }}</p>
      </div>
      <!-- Total Remaining -->
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Remaining</p>
        <p class="text-lg font-bold text-credit truncate">{{ totalRemainingFormatted }}</p>
      </div>
      <!-- Average Usage -->
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Average Usage</p>
        <p class="text-lg font-bold text-navy-900 dark:text-navy-100">{{ averageUsageFormatted }}</p>
      </div>
    </div>

    <!-- Filters -->
    <FilterBar
      :filters="filterConfigs"
      :model-value="{}"
      :loading="filtersLoading"
      @filter-change="handleFilterChange"
      @reset="handleFilterReset"
      @update:model-value="handleFilterModelUpdate"
    />

    <!-- Loading State -->
    <LoadingSkeleton v-if="budgetStore.loading && !budgetStore.listLoaded" type="card" :rows="6" />

    <!-- Empty State -->
    <EmptyState
      v-else-if="!budgetStore.loading && budgetStore.items.length === 0"
      icon="calculator"
      title="No budgets found"
      :description="hasActiveFilters
        ? 'Try adjusting your filters.'
        : 'Create your first budget to start tracking spending.'"
      :action-label="hasActiveFilters ? '' : 'Add Budget'"
      @action="openCreateForm"
    />

    <!-- Card Grid -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <div
        v-for="budget in budgetStore.items"
        :key="budget.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-700 hover:-translate-y-0.5 group"
        :class="{ 'opacity-60': !budget.is_active }"
        role="button"
        :aria-label="`View ${getCategoryName(budget.category_id)} budget details`"
        tabindex="0"
        @click="navigateToDetail(budget)"
        @keydown.enter="navigateToDetail(budget)"
      >
        <!-- Category Name + Status -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate flex-1">
            {{ getCategoryName(budget.category_id) }}
          </h3>
          <StatusBadge
            :status="budget.is_active ? 'active' : 'inactive'"
            size="sm"
          />
        </div>

        <!-- Period Badge + Rollover -->
        <div class="flex items-center gap-2 mb-3 flex-wrap">
          <TypeBadge
            :type="budget.period"
            :type-map="budgetPeriodTypeMap"
            :show-icon="false"
            size="sm"
          />
          <span
            v-if="budget.allow_rollover"
            class="inline-flex items-center gap-1 rounded-full bg-amber-100 dark:bg-amber-950/50 px-2 py-0.5 text-xs font-medium text-amber-800 dark:text-amber-300"
          >
            <svg class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
            Rollover
          </span>
        </div>

        <!-- Budget Amount -->
        <div class="mb-2">
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Budget Limit</p>
          <p class="text-xl font-bold text-navy-900 dark:text-navy-100 tracking-tight">
            {{ formatCurrency(budget.amount, budget.currency) }}
          </p>
        </div>

        <!-- Spent Amount -->
        <div class="mb-1">
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Spent</p>
          <p :class="['text-sm font-semibold', getSpentColorClass(budget.percent_used)]">
            {{ formatCurrency(budget.spent_amount, budget.currency) }}
          </p>
        </div>

        <!-- Remaining Amount -->
        <div class="mb-3">
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Remaining</p>
          <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
            {{ formatCurrency(budget.remaining, budget.currency) }}
          </p>
        </div>

        <!-- Progress Bar -->
        <div class="mb-1">
          <ProgressBar
            :value="budget.percent_used"
            :max="100"
            :color="getProgressColor(budget.percent_used)"
            size="sm"
          />
        </div>
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-3">
          {{ Math.round(budget.percent_used) }}% used
        </p>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Edit budget"
            :aria-label="`Edit ${getCategoryName(budget.category_id)} budget`"
            @click="onEditClick($event, budget)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!budget.is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete budget"
            :aria-label="`Delete ${getCategoryName(budget.category_id)} budget`"
            @click="onDeleteClick($event, budget)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore budget"
            :aria-label="`Restore ${getCategoryName(budget.category_id)} budget`"
            @click="onRestoreClick($event, budget)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Activate / Deactivate -->
          <button
            v-if="budget.is_active"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            title="Deactivate budget"
            :aria-label="`Deactivate ${getCategoryName(budget.category_id)} budget`"
            @click="onToggleActiveClick($event, budget)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Activate budget"
            :aria-label="`Activate ${getCategoryName(budget.category_id)} budget`"
            @click="onToggleActiveClick($event, budget)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div
      v-if="pagination.showPagination.value && budgetStore.items.length > 0"
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

    <!-- Create / Edit Modal -->
    <BudgetForm
      :mode="formMode"
      :item-id="editingItemId"
      :open="showFormModal"
      @saved="handleFormSaved"
      @cancel="closeFormModal"
    />

    <!-- Delete / Restore ConfirmDialog -->
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

    <!-- Activate / Deactivate ConfirmDialog -->
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
