<script setup lang="ts">
/**
 * BudgetDetail — Full detail view for a single Budget.
 *
 * Features:
 *   - Header card with category name, budget amount, spent, remaining,
 *     percent used with ProgressBar, period badge, rollover indicator,
 *     status badge
 *   - Action buttons: Edit, Delete/Restore, Activate/Deactivate
 *   - Detail fields grid: Category, Amount, Currency, Period,
 *     Start Date, Rollover, Status, Created, Updated
 *   - Spending breakdown section (placeholder for Phase 6)
 *   - Edit modal with BudgetForm
 *   - ConfirmDialogs for delete/restore and activate/deactivate
 *   - Back button to /dashboard/budgets
 *
 * Registers as `ldgr-budget-detail` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  LoadingSkeleton,
  FormErrors,
  ProgressBar,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import type { TypeStyleMap } from "@/components/vue";
import {
  useSoftDelete,
  useActivator,
  useDropdownLoader,
} from "@/composables";
import { useBudgetStore } from "@/stores/budget";
import { useCategoryStore } from "@/stores/category";
import { formatCurrency } from "@/lib/currency";
import type { BudgetOut } from "@/lib/ledgerTypes";
import BudgetForm from "./BudgetForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrBudgetDetail",
});

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  /** Budget ID from Astro route param. */
  id: string;
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const budgetStore = useBudgetStore();
const categoryStore = useCategoryStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── State ───────────────────────────────────────────────────────────────────

const budgetId = computed(() => parseInt(props.id, 10));
const activeTab = ref<"overview" | "transactions">("overview");
const showEditModal = ref(false);

// ─── Budget Period Type Map for TypeBadge ─────────────────────────────────────

const budgetPeriodTypeMap: TypeStyleMap = {
  weekly: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  monthly: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  yearly: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
};

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

// ─── Spent Color Helpers ─────────────────────────────────────────────────────

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

// ─── Load Data ───────────────────────────────────────────────────────────────

const isLoading = ref(true);
const loadError = ref<string | null>(null);

async function loadBudget() {
  if (isNaN(budgetId.value)) {
    loadError.value = "Invalid budget ID";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = null;
  try {
    await budgetStore.fetchOne(budgetId.value);
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load budget";
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
  await dropdownLoader.loadDropdown("categories", categoryStore);
  await loadBudget();
});

// Watch for ID changes
watch(() => props.id, () => {
  loadBudget();
});

// ─── Computed ────────────────────────────────────────────────────────────────

const budget = computed<BudgetOut | null>(() => budgetStore.current);

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<BudgetOut>({
  store: budgetStore,
  entityName: "Budget",
  getEntityLabel: (item) => getCategoryName(item.category_id),
  onDeleted: () => {
    window.location.href = "/dashboard/budgets";
  },
  onRestored: () => {
    loadBudget();
  },
});

// ─── Activator ──────────────────────────────────────────────────────────────

const activator = useActivator<BudgetOut>({
  store: budgetStore,
  entityName: "Budget",
  refreshListAfter: false,
  onActivated: () => {
    loadBudget();
  },
  onDeactivated: () => {
    loadBudget();
  },
});

// ─── Edit Modal ──────────────────────────────────────────────────────────────

function openEditModal() {
  showEditModal.value = true;
}

function closeEditModal() {
  showEditModal.value = false;
}

function handleFormSaved() {
  closeEditModal();
  loadBudget();
}

// ─── Navigation ─────────────────────────────────────────────────────────────

function goBack() {
  window.location.href = "/dashboard/budgets";
}

// ─── Detail Field Component (local) ─────────────────────────────────────────

interface DetailField {
  label: string;
  value: string | number | null | undefined;
  type?: "text" | "currency" | "boolean";
  currency?: string;
}

function formatPeriodLabel(period: string): string {
  return period.charAt(0) + period.slice(1).toLowerCase();
}

const overviewFields = computed<DetailField[]>(() => {
  if (!budget.value) return [];
  const b = budget.value;
  return [
    { label: "Category", value: getCategoryName(b.category_id) },
    { label: "Budget Amount", value: b.amount, type: "currency", currency: b.currency },
    { label: "Currency", value: b.currency },
    { label: "Period", value: formatPeriodLabel(b.period) },
    { label: "Start Date", value: new Date(b.start_date).toLocaleDateString() },
    { label: "Rollover", value: b.allow_rollover ? "Yes" : "No", type: "boolean" },
    { label: "Spent", value: b.spent_amount, type: "currency", currency: b.currency },
    { label: "Remaining", value: b.remaining, type: "currency", currency: b.currency },
    { label: "Percent Used", value: `${Math.round(b.percent_used)}%` },
    { label: "Status", value: b.is_active ? "Active" : "Inactive", type: "boolean" },
    { label: "Created", value: new Date(b.created_at).toLocaleDateString() },
    { label: "Last Updated", value: new Date(b.updated_at).toLocaleDateString() },
  ];
});
</script>

<template>
  <FeatureGate feature="budgets" show-fallback>
  <div class="space-y-6">
    <!-- Loading State -->
    <LoadingSkeleton v-if="isLoading" type="detail" />

    <!-- Error State -->
    <div v-else-if="loadError" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-debit" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-debit font-medium">Failed to load budget</p>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ loadError }}</p>
        <button class="btn-secondary" @click="loadBudget">Try Again</button>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else-if="!budget" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <p class="text-navy-900 dark:text-navy-100 font-medium">Budget not found</p>
        <button class="btn-secondary" @click="goBack">Back to Budgets</button>
      </div>
    </div>

    <!-- Budget Detail Content -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="goBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        Back to Budgets
      </button>

      <!-- Header Card -->
      <div class="card p-6">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <!-- Left: Budget Info -->
          <div class="flex-1 space-y-3">
            <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
              {{ getCategoryName(budget.category_id) }}
            </h1>

            <!-- Period Badge + Rollover + Status -->
            <div class="flex flex-wrap items-center gap-2">
              <TypeBadge
                :type="budget.period"
                :type-map="budgetPeriodTypeMap"
                :show-icon="false"
                size="md"
              />
              <span
                v-if="budget.allow_rollover"
                class="inline-flex items-center gap-1 rounded-full bg-amber-100 dark:bg-amber-950/50 px-2.5 py-1 text-sm font-medium text-amber-800 dark:text-amber-300"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
                </svg>
                Rollover
              </span>
              <StatusBadge :status="budget.is_active ? 'active' : 'inactive'" size="md" />
            </div>

            <!-- Budget Amount -->
            <div class="pt-2">
              <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-1">Budget Limit</p>
              <p class="text-3xl font-bold text-navy-900 dark:text-navy-100 tracking-tight">
                {{ formatCurrency(budget.amount, budget.currency) }}
              </p>
            </div>

            <!-- Spent / Remaining Row -->
            <div class="flex items-center gap-6">
              <div>
                <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Spent</p>
                <p :class="['text-lg font-semibold', getSpentColorClass(budget.percent_used)]">
                  {{ formatCurrency(budget.spent_amount, budget.currency) }}
                </p>
              </div>
              <div>
                <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Remaining</p>
                <p class="text-lg font-semibold text-navy-900 dark:text-navy-100">
                  {{ formatCurrency(budget.remaining, budget.currency) }}
                </p>
              </div>
            </div>

            <!-- Progress Bar -->
            <div class="max-w-md">
              <ProgressBar
                :value="budget.percent_used"
                :max="100"
                :color="getProgressColor(budget.percent_used)"
                size="md"
                show-label
              />
              <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
                {{ Math.round(budget.percent_used) }}% used
              </p>
            </div>
          </div>

          <!-- Right: Actions -->
          <div class="flex flex-col gap-2 md:items-end">
            <button
              class="btn-primary"
              @click="openEditModal"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
              Edit Budget
            </button>

            <!-- Activate / Deactivate -->
            <button
              v-if="budget.is_active"
              class="btn-ghost text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30"
              @click="activator.confirmToggle(budget)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
              </svg>
              Deactivate
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="activator.confirmToggle(budget)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              Activate
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!budget.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="deleter.confirmDelete(budget)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Delete
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="deleter.confirmRestore(budget)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              Restore
            </button>
          </div>
        </div>

        <!-- Store Error -->
        <FormErrors
          v-if="budgetStore.error"
          :errors="budgetStore.error"
          class="mt-4"
        />
      </div>

      <!-- Tabs -->
      <div class="border-b border-navy-200 dark:border-navy-700">
        <nav class="flex gap-6 -mb-px" aria-label="Budget detail tabs">
          <button
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'overview'
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="activeTab = 'overview'"
          >
            Overview
          </button>
          <button
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'transactions'
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="activeTab = 'transactions'"
          >
            Transactions
          </button>
        </nav>
      </div>

      <!-- Tab: Overview -->
      <div v-if="activeTab === 'overview'" class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Budget Details</h2>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
          <div
            v-for="field in overviewFields"
            :key="field.label"
            class="flex flex-col"
          >
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">
              {{ field.label }}
            </dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100 break-words">
              <!-- Boolean -->
              <template v-if="field.type === 'boolean'">
                <StatusBadge
                  :status="field.value === 'Yes' || field.value === 'Active' ? 'active' : 'inactive'"
                  size="sm"
                  :show-dot="false"
                />
              </template>
              <!-- Currency -->
              <template v-else-if="field.type === 'currency' && field.currency">
                <span :class="field.label === 'Spent' && budget ? getSpentColorClass(budget.percent_used) : ''">
                  {{ formatCurrency(String(field.value ?? '0'), field.currency) }}
                </span>
              </template>
              <!-- Period with badge -->
              <template v-else-if="field.label === 'Period' && budget">
                <TypeBadge
                  :type="budget.period"
                  :type-map="budgetPeriodTypeMap"
                  :show-icon="false"
                  size="sm"
                />
              </template>
              <!-- Default text -->
              <template v-else>
                {{ field.value ?? '—' }}
              </template>
            </dd>
          </div>
        </dl>
      </div>

      <!-- Tab: Transactions (placeholder) -->
      <div v-if="activeTab === 'transactions'" class="card p-6">
        <div class="flex flex-col items-center justify-center py-12 text-center">
          <div class="mb-4 rounded-full bg-navy-100 dark:bg-navy-800 p-4">
            <svg class="h-8 w-8 text-slate-custom-500 dark:text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
            </svg>
          </div>
          <h3 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-1">Transactions for this Budget</h3>
          <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 max-w-sm">
            Transactions for this budget will appear here. Actual transaction filtering will be available in a future update.
          </p>
        </div>
      </div>

      <!-- Edit Modal -->
      <BudgetForm
        mode="edit"
        :item-id="budgetId"
        :open="showEditModal"
        @saved="handleFormSaved"
        @cancel="closeEditModal"
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
    </template>
  </div>
  <template #no-access>
    <UpgradePrompt feature="budgets" />
  </template>
  </FeatureGate>
</template>
