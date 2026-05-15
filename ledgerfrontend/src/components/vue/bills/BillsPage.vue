<script setup lang="ts">
/**
 * BillsPage — Card grid list page for Bill entities.
 *
 * Features:
 *   - Responsive card grid (3/2/1 columns)
 *   - SearchInput for payee search
 *   - FilterBar with status, recurrence, due_within_days
 *   - Card grid with payee, amount, currency, recurrence badge,
 *     next due date coloring, status badge, fixed/variable indicator
 *   - Create/Edit via BillForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Status actions: Pause/Cancel/Reactivate with ConfirmDialog
 *   - Pagination via useLedgerPagination
 *   - EmptyState, LoadingSkeleton
 *
 * Registers as `ldgr-bills-page` custom element.
 */

import { computed, ref } from "vue";

import {
  Modal,
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
} from "@/components/vue";
import type { FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
} from "@/composables";
import { useBillStore } from "@/stores/bill";
import type {
  BillOut,
  BillFilter,
} from "@/lib/ledgerTypes";
import BillForm from "./BillForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrBillsPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useBillStore();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string | number, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(num);
}

function getDueDateClass(date: string): string {
  const today = new Date();
  const due = new Date(date);
  const diffDays = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return "text-red-600 dark:text-red-400";
  if (diffDays <= 7) return "text-orange-600 dark:text-orange-400";
  if (diffDays <= 30) return "text-yellow-600 dark:text-yellow-400";
  return "text-green-600 dark:text-green-400";
}

function getDueDateLabel(date: string): string {
  const today = new Date();
  const due = new Date(date);
  const diffDays = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return `${Math.abs(diffDays)} days overdue`;
  if (diffDays === 0) return "Due today";
  if (diffDays === 1) return "Due tomorrow";
  if (diffDays <= 7) return `Due in ${diffDays} days`;
  return `Due ${due.toLocaleDateString()}`;
}

// ─── Recurrence Type Map ─────────────────────────────────────────────────────

const recurrenceTypeMap = {
  weekly: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  biweekly: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  monthly: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  quarterly: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  yearly: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  one_time: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

// ─── Status Color Map ────────────────────────────────────────────────────────

const billStatusColorMap = {
  active: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  paused: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300", dot: "bg-amber-500" },
  cancelled: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
};

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
} = useLedgerFilters<BillFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["status", "recurrence", "due_within_days", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "status",
    label: "Status",
    type: "select",
    placeholder: "All Statuses",
    options: [
      { label: "Active", value: "ACTIVE" },
      { label: "Paused", value: "PAUSED" },
      { label: "Cancelled", value: "CANCELLED" },
    ],
  },
  {
    key: "recurrence",
    label: "Recurrence",
    type: "select",
    placeholder: "All Recurrence",
    options: [
      { label: "Weekly", value: "WEEKLY" },
      { label: "Biweekly", value: "BIWEEKLY" },
      { label: "Monthly", value: "MONTHLY" },
      { label: "Quarterly", value: "QUARTERLY" },
      { label: "Yearly", value: "YEARLY" },
      { label: "One Time", value: "ONE_TIME" },
    ],
  },
  {
    key: "due_within_days",
    label: "Due Within",
    type: "select",
    placeholder: "Any Time",
    options: [
      { label: "7 days", value: "7" },
      { label: "14 days", value: "14" },
      { label: "30 days", value: "30" },
      { label: "60 days", value: "60" },
      { label: "90 days", value: "90" },
    ],
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as BillFilter,
  (partial) => store.setFilters(partial as Partial<BillFilter>),
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
  if (key === "due_within_days") {
    setFilter(key as keyof BillFilter, value ? Number(value) : null);
  } else {
    setFilter(key as keyof BillFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<BillFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<BillOut>({
  store,
  entityName: "Bill",
  getEntityLabel: (item) => item.payee,
  onDeleted: () => {
    applyFilters();
  },
  onRestored: () => {
    applyFilters();
  },
});

// ─── Status Action Confirmations ─────────────────────────────────────────────

const statusConfirmOpen = ref(false);
const statusAction = ref<"pause" | "cancel" | "reactivate">("pause");
const statusTarget = ref<BillOut | null>(null);
const statusLoading = ref(false);

function confirmStatusAction(action: "pause" | "cancel" | "reactivate", item: BillOut) {
  statusAction.value = action;
  statusTarget.value = item;
  statusConfirmOpen.value = true;
}

const statusDialogTitle = computed(() => {
  const name = statusTarget.value?.payee ?? "this bill";
  if (statusAction.value === "pause") return `Pause Bill`;
  if (statusAction.value === "cancel") return `Cancel Bill`;
  return `Reactivate Bill`;
});

const statusDialogMessage = computed(() => {
  const name = statusTarget.value?.payee ?? "this bill";
  if (statusAction.value === "pause") return `Are you sure you want to pause "${name}"? You will no longer receive reminders until it is reactivated.`;
  if (statusAction.value === "cancel") return `Are you sure you want to cancel "${name}"? This bill will be marked as cancelled and will no longer generate reminders.`;
  return `Are you sure you want to reactivate "${name}"? Reminders will resume for this bill.`;
});

const statusDialogVariant = computed(() => {
  if (statusAction.value === "reactivate") return "success" as const;
  if (statusAction.value === "cancel") return "destructive" as const;
  return "warning" as const;
});

const statusConfirmText = computed(() => {
  if (statusAction.value === "pause") return "Pause";
  if (statusAction.value === "cancel") return "Cancel Bill";
  return "Reactivate";
});

async function executeStatusAction() {
  const item = statusTarget.value;
  if (!item) return;

  statusLoading.value = true;
  try {
    if (statusAction.value === "pause") {
      await store.pause(item.id);
    } else if (statusAction.value === "cancel") {
      await store.cancel(item.id);
    } else {
      await store.reactivate(item.id);
    }
    applyFilters();
  } catch {
    // Error is handled by the store
  } finally {
    statusLoading.value = false;
    statusConfirmOpen.value = false;
    statusTarget.value = null;
  }
}

function cancelStatusAction() {
  statusConfirmOpen.value = false;
  statusTarget.value = null;
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

function openEditForm(item: BillOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: BillOut) {
  closeFormModal();
  applyFilters();
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateToDetail(item: BillOut) {
  window.location.href = `/dashboard/bills/${item.id}`;
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onEditClick(event: Event, item: BillOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onDeleteClick(event: Event, item: BillOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: BillOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onPauseClick(event: Event, item: BillOut) {
  event.stopPropagation();
  confirmStatusAction("pause", item);
}

function onCancelClick(event: Event, item: BillOut) {
  event.stopPropagation();
  confirmStatusAction("cancel", item);
}

function onReactivateClick(event: Event, item: BillOut) {
  event.stopPropagation();
  confirmStatusAction("reactivate", item);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);

// ─── View Mode ────────────────────────────────────────────────────────────────

const viewMode = ref<"grid" | "calendar">("grid");

// ─── Calendar Computed ────────────────────────────────────────────────────────

const calendarMonth = ref(new Date().getMonth());
const calendarYear = ref(new Date().getFullYear());

const calendarDays = computed(() => {
  const daysInMonth = new Date(calendarYear.value, calendarMonth.value + 1, 0).getDate();
  const firstDayOfWeek = new Date(calendarYear.value, calendarMonth.value, 1).getDay();
  const days: Array<{ day: number; bills: BillOut[] }> = [];
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${calendarYear.value}-${String(calendarMonth.value + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const billsForDay = store.items.filter((b) => {
      if (!b.next_due_date) return false;
      return b.next_due_date === dateStr;
    });
    days.push({ day: d, bills: billsForDay });
  }
  return { firstDayOfWeek, days };
});

const monthName = computed(() => {
  return new Date(calendarYear.value, calendarMonth.value).toLocaleDateString("en-US", { month: "long", year: "numeric" });
});

function prevMonth() {
  if (calendarMonth.value === 0) {
    calendarMonth.value = 11;
    calendarYear.value--;
  } else {
    calendarMonth.value--;
  }
}

function nextMonth() {
  if (calendarMonth.value === 11) {
    calendarMonth.value = 0;
    calendarYear.value++;
  } else {
    calendarMonth.value++;
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Bills</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Track recurring bills, subscriptions, and upcoming payments
        </p>
      </div>
      <div class="flex items-center gap-3">
        <!-- View Mode Toggle -->
        <div class="flex items-center rounded-lg border border-navy-200 dark:border-navy-700 overflow-hidden">
          <button
            :class="[
              'px-3 py-1.5 text-sm font-medium transition-colors',
              viewMode === 'grid'
                ? 'bg-cyan-600 text-white'
                : 'bg-white dark:bg-navy-800 text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-700',
            ]"
            @click="viewMode = 'grid'"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </button>
          <button
            :class="[
              'px-3 py-1.5 text-sm font-medium transition-colors',
              viewMode === 'calendar'
                ? 'bg-cyan-600 text-white'
                : 'bg-white dark:bg-navy-800 text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-700',
            ]"
            @click="viewMode = 'calendar'"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
        <button class="btn-primary" @click="openCreateForm">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Add Bill
        </button>
      </div>
    </div>

    <!-- ── Search + Filters ───────────────────────────────────────────────── -->
    <div class="space-y-3">
      <SearchInput
        v-model="searchQuery"
        placeholder="Search bills by payee..."
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
    <LoadingSkeleton v-if="isLoading && !hasItems" type="card" :rows="6" />

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!isLoading && !hasItems"
      icon="credit-card"
      title="No bills found"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : 'Add your first bill to start tracking recurring payments.'"
      :action-label="hasActiveFilters ? '' : 'Add Bill'"
      @action="openCreateForm"
    />

    <!-- ── Calendar View ────────────────────────────────────────────────────── -->
    <div v-if="viewMode === 'calendar' && hasItems" class="card overflow-hidden">
      <!-- Month Navigation -->
      <div class="flex items-center justify-between p-4 border-b border-navy-100 dark:border-navy-800">
        <button class="btn-ghost text-sm" @click="prevMonth">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">{{ monthName }}</h2>
        <button class="btn-ghost text-sm" @click="nextMonth">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>

      <!-- Calendar Grid -->
      <div class="grid grid-cols-7">
        <!-- Day Headers -->
        <div v-for="day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']" :key="day"
          class="border-b border-r border-navy-100 dark:border-navy-800 p-2 text-center text-xs font-medium text-slate-custom-500"
        >
          {{ day }}
        </div>

        <!-- Empty cells before first day -->
        <div
          v-for="n in calendarDays.firstDayOfWeek"
          :key="'empty-' + n"
          class="border-b border-r border-navy-100 dark:border-navy-800 p-2 min-h-[80px] bg-navy-50/50 dark:bg-navy-900/30"
        />

        <!-- Day cells -->
        <div
          v-for="dayInfo in calendarDays.days"
          :key="dayInfo.day"
          class="border-b border-r border-navy-100 dark:border-navy-800 p-1.5 min-h-[80px]"
          :class="{
            'bg-cyan-50/50 dark:bg-cyan-950/10': dayInfo.day === new Date().getDate() && calendarMonth === new Date().getMonth() && calendarYear === new Date().getFullYear(),
          }"
        >
          <div class="text-xs font-medium mb-1"
            :class="dayInfo.day === new Date().getDate() && calendarMonth === new Date().getMonth() && calendarYear === new Date().getFullYear()
              ? 'text-cyan-600 dark:text-cyan-400' : 'text-slate-custom-500'"
          >
            {{ dayInfo.day }}
          </div>
          <div class="space-y-0.5">
            <div
              v-for="bill in dayInfo.bills"
              :key="bill.id"
              class="text-[10px] leading-tight rounded px-1 py-0.5 cursor-pointer hover:opacity-80 transition-opacity truncate"
              :class="bill.status === 'ACTIVE'
                ? 'bg-cyan-100 dark:bg-cyan-950/30 text-cyan-800 dark:text-cyan-300'
                : bill.status === 'PAUSED'
                  ? 'bg-amber-100 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300'
                  : 'bg-slate-100 dark:bg-slate-800/30 text-slate-600 dark:text-slate-400'"
              @click="navigateToDetail(bill)"
            >
              {{ bill.payee }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Card Grid ──────────────────────────────────────────────────────── -->
    <div
      v-if="viewMode === 'grid' && hasItems"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <div
        v-for="bill in store.items"
        :key="bill.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-700 hover:-translate-y-0.5 group"
        :class="{
          'opacity-60': bill.status === 'CANCELLED' || (bill as BillOut).is_deleted,
        }"
        role="button"
        :aria-label="`View ${bill.payee} details`"
        tabindex="0"
        @click="navigateToDetail(bill as BillOut)"
        @keydown.enter="navigateToDetail(bill as BillOut)"
      >
        <!-- Payee + Amount Row -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate">
              {{ (bill as BillOut).payee }}
            </h3>
            <p
              v-if="(bill as BillOut).is_deleted"
              class="text-xs text-debit mt-0.5"
            >
              Deleted
            </p>
          </div>
          <div class="text-right flex-shrink-0">
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency((bill as BillOut).amount, (bill as BillOut).currency || "USD") }}
            </p>
            <span class="inline-flex items-center rounded-full bg-navy-100 dark:bg-navy-800 px-2 py-0.5 text-xs font-medium text-navy-700 dark:text-navy-300">
              {{ (bill as BillOut).currency || "USD" }}
            </span>
          </div>
        </div>

        <!-- Recurrence Badge + Status Badge -->
        <div class="flex items-center gap-2 mb-3 flex-wrap">
          <TypeBadge
            :type="(bill as BillOut).recurrence"
            :type-map="recurrenceTypeMap"
            :show-icon="false"
            size="sm"
          />
          <StatusBadge
            :status="(bill as BillOut).status"
            :color-map="billStatusColorMap"
            size="sm"
          />
          <!-- Fixed / Variable indicator -->
          <span
            v-if="(bill as BillOut).is_amount_fixed"
            class="inline-flex items-center gap-1 text-xs text-slate-custom-500 dark:text-slate-custom-400"
            title="Fixed amount"
          >
            <!-- Lock icon -->
            <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
            </svg>
            Fixed
          </span>
          <span
            v-else
            class="inline-flex items-center gap-1 text-xs text-slate-custom-500 dark:text-slate-custom-400"
            title="Variable amount"
          >
            <!-- Unlock icon -->
            <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2H7V7a3 3 0 015.905-.75 1 1 0 001.937-.5A5.002 5.002 0 0010 2z" />
            </svg>
            Variable
          </span>
        </div>

        <!-- Next Due Date -->
        <div class="mb-3">
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Next Due</p>
          <p :class="['text-sm font-medium', getDueDateClass((bill as BillOut).next_due_date)]">
            {{ getDueDateLabel((bill as BillOut).next_due_date) }}
          </p>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Edit bill"
            :aria-label="`Edit ${(bill as BillOut).payee}`"
            @click="onEditClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!(bill as BillOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete bill"
            :aria-label="`Delete ${(bill as BillOut).payee}`"
            @click="onDeleteClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore bill"
            :aria-label="`Restore ${(bill as BillOut).payee}`"
            @click="onRestoreClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Status Actions based on current status -->
          <!-- ACTIVE → Pause or Cancel -->
          <button
            v-if="(bill as BillOut).status === 'ACTIVE' && !(bill as BillOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            title="Pause bill"
            :aria-label="`Pause ${(bill as BillOut).payee}`"
            @click="onPauseClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-if="(bill as BillOut).status === 'ACTIVE' && !(bill as BillOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Cancel bill"
            :aria-label="`Cancel ${(bill as BillOut).payee}`"
            @click="onCancelClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- PAUSED → Reactivate or Cancel -->
          <button
            v-if="(bill as BillOut).status === 'PAUSED' && !(bill as BillOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Reactivate bill"
            :aria-label="`Reactivate ${(bill as BillOut).payee}`"
            @click="onReactivateClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- CANCELLED → Reactivate -->
          <button
            v-if="(bill as BillOut).status === 'CANCELLED' && !(bill as BillOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Reactivate bill"
            :aria-label="`Reactivate ${(bill as BillOut).payee}`"
            @click="onReactivateClick($event, bill as BillOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
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
    <BillForm
      :mode="formMode"
      :item-id="editingItemId"
      :open="showFormModal"
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

    <!-- ── Status Action Confirm ──────────────────────────────────────────── -->
    <ConfirmDialog
      :open="statusConfirmOpen"
      :title="statusDialogTitle"
      :message="statusDialogMessage"
      :variant="statusDialogVariant"
      :confirm-text="statusConfirmText"
      :loading="statusLoading"
      @confirm="executeStatusAction"
      @cancel="cancelStatusAction"
    />
  </div>
</template>
