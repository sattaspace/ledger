<script setup lang="ts">
/**
 * GoalsPage — Tabbed card layout for SavingsGoal entities.
 *
 * Features:
 *   - Two tabs: "In Progress" and "Completed" (filter by is_completed)
 *   - Summary bar: Total Saved, Total Target, Overall Progress
 *   - Goal cards in grid (2 cols on md): Name, progress bar (current/target),
 *     percentage, remaining amount, deadline, days remaining badge,
 *     linked account, icon+color
 *   - Color: incomplete card border = navy, completed = cyan (celebration styling)
 *   - Days remaining badge: <7 days = red, <30 days = amber, else = green
 *   - Search + FilterBar (filter by is_active)
 *   - Create/Edit via SavingsGoalForm in Modal
 *   - Contribute via GoalContribute in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Activate/Deactivate via ConfirmDialog + useActivator
 *   - Pagination, EmptyState, LoadingSkeleton
 *   - Click card opens contribute modal
 *
 * Registers as `ldgr-goals-page` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  ConfirmDialog,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  FeatureGate,
  UpgradePrompt,
  PlanLimitBadge,
} from "@/components/vue";
import type { FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useSavingsGoalStore } from "@/stores/savingsGoal";
import { useAccountStore } from "@/stores/account";
import type {
  SavingsGoalOut,
  SavingsGoalFilter,
  SavingsGoalContributionOut,
} from "@/lib/ledgerTypes";
import { ledgerApi } from "@/lib/ledgerApi";
import SavingsGoalForm from "./SavingsGoalForm.vue";
import GoalContribute from "./GoalContribute.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrGoalsPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useSavingsGoalStore();
const accountStore = useAccountStore();

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

function getDaysRemainingBadgeClass(days: number | null): string {
  if (days === null) return "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300";
  if (days < 0) return "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300";
  if (days < 7) return "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300";
  if (days < 30) return "bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300";
  return "bg-green-100 dark:bg-green-950/50 text-green-700 dark:text-green-300";
}

function getDaysRemainingLabel(days: number | null): string {
  if (days === null) return "No deadline";
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

function getProgressColor(percent: number): string {
  if (percent >= 100) return "bg-cyan-500";
  if (percent >= 75) return "bg-green-500";
  if (percent >= 50) return "bg-cyan-500";
  if (percent >= 25) return "bg-amber-500";
  return "bg-red-500";
}

function getAccountName(accountId: number | null): string {
  if (!accountId) return "";
  const acct = accountStore.dropdown.find((a: { id: number; name: string }) => a.id === accountId);
  return acct ? acct.name : "";
}

// ─── Active Tab ──────────────────────────────────────────────────────────────

const activeTab = ref<"inProgress" | "completed">("inProgress");

function switchTab(tab: "inProgress" | "completed") {
  activeTab.value = tab;
  const isCompleted = tab === "completed";
  setFilter("is_completed", isCompleted);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Summary ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  await store.fetchDashboard();
  setFilter("is_completed", false);
  applyFilters();
});

const totalSaved = computed(() => store.totalSaved);
const totalTarget = computed(() => store.totalTarget);
const overallProgress = computed(() => store.overallProgress);

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
} = useLedgerFilters<SavingsGoalFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["is_completed", "is_active", "currency", "account_id", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "is_active",
    label: "Active Only",
    type: "toggle",
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as SavingsGoalFilter,
  (partial) => store.setFilters(partial as Partial<SavingsGoalFilter>),
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
  if (key === "is_active") {
    setFilter(key as keyof SavingsGoalFilter, value ? true : null);
  } else {
    setFilter(key as keyof SavingsGoalFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
  setFilter("is_completed", activeTab.value === "completed");
  applyFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<SavingsGoalFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<SavingsGoalOut>({
  store,
  entityName: "Savings Goal",
  getEntityLabel: (item) => item.name,
  onDeleted: () => {
    applyFilters();
    store.fetchDashboard(true);
  },
  onRestored: () => {
    applyFilters();
    store.fetchDashboard(true);
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<SavingsGoalOut>({
  store,
  entityName: "Savings Goal",
  getEntityLabel: (item) => item.name,
  onActivated: () => {
    applyFilters();
    store.fetchDashboard(true);
  },
  onDeactivated: () => {
    applyFilters();
    store.fetchDashboard(true);
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

function openEditForm(item: SavingsGoalOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: SavingsGoalOut) {
  closeFormModal();
  applyFilters();
  store.fetchDashboard(true);
}

// ─── Contribute Modal ────────────────────────────────────────────────────────

const showContributeModal = ref(false);
const contributingGoalId = ref<number | undefined>(undefined);

function openContributeModal(item: SavingsGoalOut) {
  contributingGoalId.value = item.id;
  showContributeModal.value = true;
}

function closeContributeModal() {
  showContributeModal.value = false;
  contributingGoalId.value = undefined;
}

function handleContributed() {
  closeContributeModal();
  applyFilters();
  store.fetchDashboard(true);
}

// ─── Card Click ──────────────────────────────────────────────────────────────

function handleCardClick(item: SavingsGoalOut) {
  openContributeModal(item);
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onEditClick(event: Event, item: SavingsGoalOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onContributeClick(event: Event, item: SavingsGoalOut) {
  event.stopPropagation();
  openContributeModal(item);
}

function onDeleteClick(event: Event, item: SavingsGoalOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: SavingsGoalOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onActivateClick(event: Event, item: SavingsGoalOut) {
  event.stopPropagation();
  activator.confirmActivate(item);
}

function onDeactivateClick(event: Event, item: SavingsGoalOut) {
  event.stopPropagation();
  activator.confirmDeactivate(item);
}

// ─── Contribution History ────────────────────────────────────────────────────

const showHistory = ref<number | null>(null);
const contributions = ref<SavingsGoalContributionOut[]>([]);
const contributionsLoading = ref(false);
const contributionsError = ref<string | null>(null);

async function toggleHistory(goalId: number) {
  if (showHistory.value === goalId) {
    showHistory.value = null;
    contributions.value = [];
    return;
  }
  showHistory.value = goalId;
  contributions.value = [];
  contributionsError.value = null;
  contributionsLoading.value = true;
  try {
    const result = await ledgerApi.savingsGoals.contributions(goalId, { limit: 10 });
    contributions.value = result.items;
  } catch {
    contributionsError.value = "Failed to load contribution history";
  } finally {
    contributionsLoading.value = false;
  }
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);
</script>

<template>
  <FeatureGate feature="goals" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Savings Goals</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Track your progress toward financial milestones
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-primary" @click="openCreateForm">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Add Goal
        </button>
        <PlanLimitBadge max-key="max_goals" feature-key="goals" :current="store.items.length" />
      </div>
    </div>

    <!-- ── Summary Bar ────────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Saved</p>
        <p class="text-xl font-bold text-credit">
          {{ formatCurrency(totalSaved) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Target</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ formatCurrency(totalTarget) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Overall Progress</p>
        <div class="flex items-center gap-3">
          <p class="text-xl font-bold text-cyan-600 dark:text-cyan-400">
            {{ overallProgress }}%
          </p>
          <div class="flex-1 h-2 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
            <div
              class="h-full rounded-full bg-cyan-500 transition-all duration-500"
              :style="{ width: `${Math.min(overallProgress, 100)}%` }"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- ── Tabs: In Progress / Completed ────────────────────────────────────── -->
    <div class="border-b border-navy-200 dark:border-navy-700">
      <nav class="flex gap-6 -mb-px" aria-label="Savings goal tabs">
        <button
          :class="[
            'pb-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === 'inProgress'
              ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
              : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
          ]"
          @click="switchTab('inProgress')"
        >
          In Progress
        </button>
        <button
          :class="[
            'pb-3 text-sm font-medium border-b-2 transition-colors',
            activeTab === 'completed'
              ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
              : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
          ]"
          @click="switchTab('completed')"
        >
          Completed
        </button>
      </nav>
    </div>

    <!-- ── Search + Filters ───────────────────────────────────────────────── -->
    <div class="space-y-3">
      <SearchInput
        v-model="searchQuery"
        placeholder="Search goals by name..."
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
      :title="activeTab === 'inProgress' ? 'No goals in progress' : 'No completed goals'"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : activeTab === 'inProgress'
          ? 'Create a savings goal to start tracking your progress.'
          : 'Complete a goal to see it here.'"
      :action-label="hasActiveFilters ? '' : 'Add Goal'"
      @action="openCreateForm"
    />

    <!-- ── Goal Cards ─────────────────────────────────────────────────────── -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 gap-4"
    >
      <div
        v-for="goal in store.items"
        :key="goal.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 group"
        :class="[
          (goal as SavingsGoalOut).is_completed
            ? 'border-cyan-300 dark:border-cyan-700 hover:border-cyan-400 dark:hover:border-cyan-600'
            : 'border-navy-200 dark:border-navy-700 hover:border-cyan-300 dark:hover:border-cyan-700',
          {
            'opacity-60': !(goal as SavingsGoalOut).is_active || (goal as SavingsGoalOut).is_deleted,
          },
        ]"
        role="button"
        :aria-label="`Contribute to ${(goal as SavingsGoalOut).name}`"
        tabindex="0"
        @click="handleCardClick(goal as SavingsGoalOut)"
        @keydown.enter="handleCardClick(goal as SavingsGoalOut)"
      >
        <!-- Celebration Header for Completed Goals -->
        <div
          v-if="(goal as SavingsGoalOut).is_completed"
          class="flex items-center gap-2 mb-3 px-3 py-1.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800"
        >
          <span class="text-lg" aria-hidden="true">&#127881;</span>
          <span class="text-sm font-semibold text-cyan-700 dark:text-cyan-300">Goal Achieved!</span>
          <span class="text-lg" aria-hidden="true">&#10024;</span>
        </div>

        <!-- Header: Icon + Name + Days Remaining Badge -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex items-center gap-2 flex-1 min-w-0">
            <span
              v-if="(goal as SavingsGoalOut).icon"
              class="text-xl flex-shrink-0"
              :aria-hidden="true"
            >{{ (goal as SavingsGoalOut).icon }}</span>
            <div class="flex-1 min-w-0">
              <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate">
                {{ (goal as SavingsGoalOut).name }}
              </h3>
              <p
                v-if="(goal as SavingsGoalOut).is_deleted"
                class="text-xs text-debit mt-0.5"
              >
                Deleted
              </p>
              <p
                v-if="getAccountName((goal as SavingsGoalOut).account_id)"
                class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mt-0.5"
              >
                {{ getAccountName((goal as SavingsGoalOut).account_id) }}
              </p>
            </div>
          </div>
          <span
            :class="[
              'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium flex-shrink-0',
              getDaysRemainingBadgeClass((goal as SavingsGoalOut).days_remaining),
            ]"
          >
            {{ getDaysRemainingLabel((goal as SavingsGoalOut).days_remaining) }}
          </span>
        </div>

        <!-- Progress Bar -->
        <div class="mb-3">
          <div class="flex items-center justify-between mb-1">
            <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">Progress</span>
            <span class="text-xs font-medium text-navy-900 dark:text-navy-100">
              {{ (goal as SavingsGoalOut).progress_percent }}%
            </span>
          </div>
          <div class="h-2.5 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
            <div
              :class="['h-full rounded-full transition-all duration-500', getProgressColor((goal as SavingsGoalOut).progress_percent)]"
              :style="{ width: `${Math.min((goal as SavingsGoalOut).progress_percent, 100)}%` }"
            />
          </div>
        </div>

        <!-- Amounts: Current / Target -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Saved</p>
            <p class="text-sm font-semibold text-credit">
              {{ formatCurrency((goal as SavingsGoalOut).current_amount, (goal as SavingsGoalOut).currency || "USD") }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Target</p>
            <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ formatCurrency((goal as SavingsGoalOut).target_amount, (goal as SavingsGoalOut).currency || "USD") }}
            </p>
          </div>
        </div>

        <!-- Remaining + Deadline -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Remaining</p>
            <p class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatCurrency((goal as SavingsGoalOut).remaining, (goal as SavingsGoalOut).currency || "USD") }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Deadline</p>
            <p class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatDate((goal as SavingsGoalOut).deadline) }}
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Contribute -->
          <button
            v-if="!(goal as SavingsGoalOut).is_completed && !(goal as SavingsGoalOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Contribute to goal"
            :aria-label="`Contribute to ${(goal as SavingsGoalOut).name}`"
            @click="onContributeClick($event, goal as SavingsGoalOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- History -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            :class="{ 'bg-cyan-50 dark:bg-navy-800 text-cyan-700 dark:text-cyan-400': showHistory === (goal as SavingsGoalOut).id }"
            title="View contribution history"
            :aria-label="`View history for ${(goal as SavingsGoalOut).name}`"
            :aria-expanded="showHistory === (goal as SavingsGoalOut).id"
            @click.stop="toggleHistory((goal as SavingsGoalOut).id)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Edit goal"
            :aria-label="`Edit ${(goal as SavingsGoalOut).name}`"
            @click="onEditClick($event, goal as SavingsGoalOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Activate/Deactivate -->
          <button
            v-if="(goal as SavingsGoalOut).is_active && !(goal as SavingsGoalOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            title="Deactivate goal"
            :aria-label="`Deactivate ${(goal as SavingsGoalOut).name}`"
            @click="onDeactivateClick($event, goal as SavingsGoalOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else-if="!(goal as SavingsGoalOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
            title="Activate goal"
            :aria-label="`Activate ${(goal as SavingsGoalOut).name}`"
            @click="onActivateClick($event, goal as SavingsGoalOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!(goal as SavingsGoalOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete goal"
            :aria-label="`Delete ${(goal as SavingsGoalOut).name}`"
            @click="onDeleteClick($event, goal as SavingsGoalOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore goal"
            :aria-label="`Restore ${(goal as SavingsGoalOut).name}`"
            @click="onRestoreClick($event, goal as SavingsGoalOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>

        <!-- Contribution History -->
        <div
          v-if="showHistory === (goal as SavingsGoalOut).id"
          class="mt-3 pt-3 border-t border-navy-100 dark:border-navy-800"
        >
          <p class="text-xs font-semibold text-navy-900 dark:text-navy-100 mb-2">Contribution History</p>
          <!-- Loading -->
          <div v-if="contributionsLoading" class="space-y-2">
            <div class="h-4 bg-navy-100 dark:bg-navy-800 rounded animate-pulse w-3/4" />
            <div class="h-4 bg-navy-100 dark:bg-navy-800 rounded animate-pulse w-1/2" />
          </div>
          <!-- Error -->
          <p v-else-if="contributionsError" class="text-xs text-debit">{{ contributionsError }}</p>
          <!-- Empty -->
          <p v-else-if="contributions.length === 0" class="text-xs text-slate-custom-500 dark:text-slate-custom-400">No contributions yet</p>
          <!-- List -->
          <ul v-else class="space-y-2">
            <li
              v-for="c in contributions"
              :key="c.id"
              class="flex items-center justify-between text-xs"
            >
              <div class="flex items-center gap-2 min-w-0">
                <span class="text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0">{{ formatDate(c.contributed_at) }}</span>
                <span v-if="c.notes" class="text-slate-custom-600 dark:text-slate-custom-300 truncate" :title="c.notes">{{ c.notes }}</span>
              </div>
              <span class="font-medium text-credit flex-shrink-0 ml-2">
                {{ formatCurrency(c.amount, c.currency || 'USD') }}
              </span>
            </li>
          </ul>
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
    <Modal
      :open="showFormModal"
      :title="formMode === 'create' ? 'Add Savings Goal' : 'Edit Savings Goal'"
      size="lg"
      @close="closeFormModal"
    >
      <template #body>
        <SavingsGoalForm
          :mode="formMode"
          :item-id="editingItemId"
          :open="showFormModal"
          @saved="handleFormSaved"
          @cancel="closeFormModal"
        />
      </template>
    </Modal>

    <!-- ── Contribute Modal ───────────────────────────────────────────────── -->
    <Modal
      v-if="contributingGoalId"
      :open="showContributeModal"
      title="Contribute to Goal"
      size="md"
      @close="closeContributeModal"
    >
      <template #body>
        <GoalContribute
          :goal-id="contributingGoalId"
          :open="showContributeModal"
          @contributed="handleContributed"
          @cancel="closeContributeModal"
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
    <UpgradePrompt feature="goals" />
  </template>
  </FeatureGate>
</template>
