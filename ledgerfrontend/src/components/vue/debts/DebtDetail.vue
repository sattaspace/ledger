<script setup lang="ts">
/**
 * DebtDetail — Full detail view for a single Debt Facility.
 *
 * Features:
 *   - Header card: Name, entity, type badge, nature indicator
 *   - Summary: Principal, Remaining, Progress %, Interest Rate, Monthly Payment
 *   - Tab layout: Overview, Payment History
 *   - Overview: all debt fields in detail grid
 *   - Payment History: DataTable with Record Payment, Edit Payment
 *   - Record Payment modal with DebtPaymentForm
 *   - ConfirmDialogs for delete/restore and activate/deactivate
 *   - Simple amortization visualization (progress bar)
 *
 * Registers as `ldgr-debt-detail` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  ConfirmDialog,
  TypeBadge,
  StatusBadge,
  LoadingSkeleton,
  FormErrors,
  DataTable,
  Modal,
} from "@/components/vue";
import type { DataTableColumn } from "@/components/vue";
import {
  useSoftDelete,
  useActivator,
  useDropdownLoader,
} from "@/composables";
import { useDebtStore } from "@/stores/debt";
import { useAccountStore } from "@/stores/account";
import { useInstitutionStore } from "@/stores/institution";
import type {
  DebtFacilityOut,
  DebtPaymentOut,
} from "@/lib/ledgerTypes";
import DebtForm from "./DebtForm.vue";
import DebtPaymentForm from "./DebtPaymentForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrDebtDetail",
});

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  /** Debt ID from Astro route param. */
  id: string;
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const debtStore = useDebtStore();
const accountStore = useAccountStore();
const institutionStore = useInstitutionStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── State ───────────────────────────────────────────────────────────────────

const debtId = computed(() => parseInt(props.id, 10));
const activeTab = ref<"overview" | "payments">("overview");
const showEditModal = ref(false);
const showPaymentModal = ref(false);
const editingPayment = ref<DebtPaymentOut | undefined>(undefined);

// ─── Lookup Maps ─────────────────────────────────────────────────────────────

const accountMap = computed(() => {
  const map = new Map<number, string>();
  for (const acct of dropdownLoader.getDropdown<{ id: number; name: string }>("accounts")) {
    map.set(acct.id, acct.name);
  }
  return map;
});

function getAccountName(accountId: number | null): string {
  if (!accountId) return "—";
  return accountMap.value.get(accountId) ?? "Unknown Account";
}

const institutionMap = computed(() => {
  const map = new Map<number, string>();
  for (const inst of dropdownLoader.getDropdown<{ id: number; name: string }>("institutions")) {
    map.set(inst.id, inst.name);
  }
  return map;
});

function getInstitutionName(institutionId: number | null): string {
  if (!institutionId) return "—";
  return institutionMap.value.get(institutionId) ?? "Unknown Institution";
}

// ─── Load Data ───────────────────────────────────────────────────────────────

const isLoading = ref(true);
const loadError = ref<string | null>(null);

async function loadDebt() {
  if (isNaN(debtId.value)) {
    loadError.value = "Invalid debt ID";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = null;
  try {
    await debtStore.fetchOne(debtId.value);
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load debt";
  } finally {
    isLoading.value = false;
  }
}

async function loadPayments() {
  if (!isNaN(debtId.value)) {
    await debtStore.fetchPayments(debtId.value);
  }
}

onMounted(async () => {
  await Promise.all([
    dropdownLoader.loadDropdown("accounts", accountStore),
    dropdownLoader.loadDropdown("institutions", institutionStore),
  ]);
  await loadDebt();
  await loadPayments();
});

watch(() => props.id, () => {
  loadDebt();
  loadPayments();
});

// ─── Computed ────────────────────────────────────────────────────────────────

const debt = computed<DebtFacilityOut | null>(() => debtStore.current);

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

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
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

const progressColor = (percent: number): string => {
  if (percent >= 80) return "bg-green-500";
  if (percent >= 50) return "bg-cyan-500";
  if (percent >= 25) return "bg-amber-500";
  return "bg-red-500";
};

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<DebtFacilityOut>({
  store: debtStore,
  entityName: "Debt",
  getEntityLabel: (item) => item.name,
  onDeleted: () => {
    window.location.href = "/dashboard/debts";
  },
  onRestored: () => {
    loadDebt();
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<DebtFacilityOut>({
  store: debtStore,
  entityName: "Debt",
  getEntityLabel: (item) => item.name,
  onActivated: () => {
    loadDebt();
  },
  onDeactivated: () => {
    loadDebt();
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
  loadDebt();
  debtStore.fetchSummary(true);
}

// ─── Payment Modal ───────────────────────────────────────────────────────────

function openRecordPayment() {
  editingPayment.value = undefined;
  showPaymentModal.value = true;
}

function openEditPayment(payment: DebtPaymentOut) {
  editingPayment.value = payment;
  showPaymentModal.value = true;
}

function closePaymentModal() {
  showPaymentModal.value = false;
  editingPayment.value = undefined;
}

function handlePaymentSaved() {
  closePaymentModal();
  loadPayments();
  loadDebt(); // Refresh remaining_balance & progress_percent
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function goBack() {
  window.location.href = "/dashboard/debts";
}

// ─── Detail Fields ───────────────────────────────────────────────────────────

interface DetailField {
  label: string;
  value: string | number | null | undefined;
  type?: "text" | "currency" | "badge" | "date";
  currency?: string;
}

const overviewFields = computed<DetailField[]>(() => {
  if (!debt.value) return [];
  const d = debt.value;
  return [
    { label: "Name", value: d.name },
    { label: d.debt_nature === "MONEY_BORROWED" ? "Lender" : "Borrower", value: d.entity_name },
    { label: "Debt Type", value: d.debt_type, type: "badge" },
    { label: "Nature", value: d.debt_nature === "MONEY_BORROWED" ? "I Owe" : "Owed to Me" },
    { label: "Institution", value: getInstitutionName(d.institution_id) },
    { label: "Principal", value: d.principal_amount, type: "currency", currency: d.currency },
    { label: "Remaining Balance", value: d.remaining_balance, type: "currency", currency: d.currency },
    { label: "Interest Rate", value: `${parseFloat(d.interest_rate || "0").toFixed(2)}%` },
    { label: "Monthly Payment", value: d.monthly_payment, type: "currency", currency: d.currency },
    { label: "Start Date", value: formatDate(d.start_date), type: "date" },
    { label: "End Date", value: formatDate(d.end_date), type: "date" },
    { label: "Term", value: d.term_months ? `${d.term_months} months` : "—" },
    { label: "Payment Day", value: d.payment_day ? `Day ${d.payment_day}` : "—" },
    { label: "Account", value: getAccountName(d.account_id) },
    { label: "Notes", value: d.notes || "—" },
    { label: "Created", value: formatDate(d.created_at) },
    { label: "Last Updated", value: formatDate(d.updated_at) },
  ];
});

// ─── Payment History Table ───────────────────────────────────────────────────

const paymentColumns: DataTableColumn[] = [
  { key: "payment_date", label: "Date", sortable: true },
  { key: "amount", label: "Total" },
  { key: "principal_portion", label: "Principal" },
  { key: "interest_portion", label: "Interest" },
  { key: "extra_payment", label: "Extra" },
  { key: "notes", label: "Notes" },
  { key: "actions", label: "Actions", align: "right" as const },
];

function handleSortChange(payload: { key: string; direction: "asc" | "desc" }): void {
  void payload;
}

// ─── Amortization Computed (simple bar chart data) ───────────────────────────

const amortizationData = computed(() => {
  if (!debtStore.payments.length) return [];
  // Build cumulative principal paid over time
  let cumulative = 0;
  const principal = parseFloat(debt.value?.principal_amount || "0");
  return debtStore.payments
    .slice()
    .sort((a, b) => new Date(a.payment_date).getTime() - new Date(b.payment_date).getTime())
    .map((p) => {
      cumulative += parseFloat(p.principal_portion || "0") + parseFloat(p.extra_payment || "0");
      return {
        date: p.payment_date,
        principalPaid: cumulative,
        percentPaid: principal > 0 ? Math.min((cumulative / principal) * 100, 100) : 0,
      };
    });
});

// ─── Tab Switch ──────────────────────────────────────────────────────────────

function switchTab(tab: "overview" | "payments") {
  activeTab.value = tab;
  if (tab === "payments") {
    loadPayments();
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <LoadingSkeleton v-if="isLoading" type="detail" />

    <!-- Error State -->
    <div v-else-if="loadError" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-debit" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-debit font-medium">Failed to load debt</p>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ loadError }}</p>
        <button class="btn-secondary" @click="loadDebt">Try Again</button>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else-if="!debt" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <p class="text-navy-900 dark:text-navy-100 font-medium">Debt not found</p>
        <button class="btn-secondary" @click="goBack">Back to Debts</button>
      </div>
    </div>

    <!-- Debt Detail Content -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="goBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        Back to Debts
      </button>

      <!-- Header Card -->
      <div class="card p-6">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <!-- Left: Debt Info -->
          <div class="flex-1 space-y-3">
            <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
              {{ debt.name }}
            </h1>
            <div class="flex flex-wrap items-center gap-2">
              <TypeBadge
                :type="debt.debt_type"
                :type-map="debtTypeMap"
                :show-icon="false"
                size="md"
              />
              <span
                :class="[
                  'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
                  debt.debt_nature === 'MONEY_BORROWED'
                    ? 'bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-300'
                    : 'bg-green-100 dark:bg-green-950/50 text-green-800 dark:text-green-300',
                ]"
              >
                {{ debt.debt_nature === "MONEY_BORROWED" ? "I Owe" : "Owed to Me" }}
              </span>
              <span class="inline-flex items-center rounded-full bg-navy-100 dark:bg-navy-800 px-2.5 py-1 text-xs font-medium text-navy-700 dark:text-navy-300">
                {{ debt.currency }}
              </span>
            </div>
            <!-- Entity -->
            <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
              {{ debt.debt_nature === "MONEY_BORROWED" ? "Lender" : "Borrower" }}:
              <span class="font-medium text-navy-900 dark:text-navy-100">{{ debt.entity_name }}</span>
            </p>
          </div>

          <!-- Right: Actions -->
          <div class="flex flex-col gap-2 md:items-end">
            <button class="btn-primary" @click="openEditModal">
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
              Edit Debt
            </button>

            <!-- Activate / Deactivate -->
            <button
              v-if="debt.is_active && !debt.is_deleted"
              class="btn-ghost text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30"
              @click="activator.confirmDeactivate(debt)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
              </svg>
              Deactivate
            </button>
            <button
              v-else-if="!debt.is_deleted"
              class="btn-ghost text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="activator.confirmActivate(debt)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
              Activate
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!debt.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="deleter.confirmDelete(debt)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Delete
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="deleter.confirmRestore(debt)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              Restore
            </button>
          </div>
        </div>

        <!-- Summary Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-4 mt-6 pt-6 border-t border-navy-100 dark:border-navy-800">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Principal</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(debt.principal_amount, debt.currency) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Remaining</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(debt.remaining_balance, debt.currency) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Paid Off</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatPercent(debt.progress_percent) }}
            </p>
            <!-- Mini progress bar -->
            <div class="h-2 mt-1 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
              <div
                :class="['h-full rounded-full', progressColor(debt.progress_percent)]"
                :style="{ width: `${Math.min(debt.progress_percent, 100)}%` }"
              />
            </div>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Interest Rate</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ parseFloat(debt.interest_rate || "0").toFixed(2) }}%
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Monthly Payment</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(debt.monthly_payment, debt.currency) }}
            </p>
          </div>
        </div>

        <!-- Store Error -->
        <FormErrors
          v-if="debtStore.error"
          :errors="debtStore.error"
          class="mt-4"
        />
      </div>

      <!-- Tabs -->
      <div class="border-b border-navy-200 dark:border-navy-700">
        <nav class="flex gap-6 -mb-px" aria-label="Debt detail tabs">
          <button
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'overview'
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="switchTab('overview')"
          >
            Overview
          </button>
          <button
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'payments'
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="switchTab('payments')"
          >
            Payment History
          </button>
        </nav>
      </div>

      <!-- Tab: Overview -->
      <div v-if="activeTab === 'overview'" class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Debt Details</h2>
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
              <!-- Currency -->
              <template v-if="field.type === 'currency' && field.currency">
                {{ formatCurrency(String(field.value ?? '0'), field.currency) }}
              </template>
              <!-- Badge -->
              <template v-else-if="field.type === 'badge' && field.value">
                <TypeBadge
                  :type="String(field.value)"
                  :type-map="debtTypeMap"
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

      <!-- Tab: Payment History -->
      <div v-if="activeTab === 'payments'" class="card overflow-hidden">
        <div class="p-4 flex items-center justify-between border-b border-navy-100 dark:border-navy-800">
          <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">Payment History</h2>
          <button class="btn-primary text-sm" @click="openRecordPayment">
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
            Record Payment
          </button>
        </div>

        <DataTable
          :columns="paymentColumns"
          :rows="(debtStore.payments as Record<string, unknown>[])"
          :loading="debtStore.loadingAction === 'fetchPayments'"
          :total="debtStore.payments.length"
          :limit="debtStore.payments.length || 25"
          :offset="0"
          @sort-change="handleSortChange"
        >
          <!-- Date Column -->
          <template #cell-payment_date="{ row }">
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatDate((row as DebtPaymentOut).payment_date) }}
            </span>
          </template>

          <!-- Amount Column -->
          <template #cell-amount="{ row }">
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatCurrency((row as DebtPaymentOut).amount, debt?.currency ?? "USD") }}
            </span>
          </template>

          <!-- Principal Portion Column -->
          <template #cell-principal_portion="{ row }">
            <span class="text-sm text-cyan-700 dark:text-cyan-400">
              {{ formatCurrency((row as DebtPaymentOut).principal_portion, debt?.currency ?? "USD") }}
            </span>
          </template>

          <!-- Interest Portion Column -->
          <template #cell-interest_portion="{ row }">
            <span class="text-sm text-amber-700 dark:text-amber-400">
              {{ formatCurrency((row as DebtPaymentOut).interest_portion, debt?.currency ?? "USD") }}
            </span>
          </template>

          <!-- Extra Payment Column -->
          <template #cell-extra_payment="{ row }">
            <span class="text-sm text-green-700 dark:text-green-400">
              {{ formatCurrency((row as DebtPaymentOut).extra_payment, debt?.currency ?? "USD") }}
            </span>
          </template>

          <!-- Notes Column -->
          <template #cell-notes="{ row }">
            <span class="text-sm text-slate-custom-600 dark:text-slate-custom-400 truncate max-w-[150px] inline-block">
              {{ (row as DebtPaymentOut).notes || '—' }}
            </span>
          </template>

          <!-- Actions Column -->
          <template #cell-actions="{ row }">
            <button
              class="btn-ghost px-2 py-1 text-sm"
              title="Edit payment"
              aria-label="Edit payment"
              @click.stop="openEditPayment(row as DebtPaymentOut)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>
          </template>
        </DataTable>

        <!-- Empty payments -->
        <div
          v-if="debtStore.payments.length === 0 && debtStore.loadingAction !== 'fetchPayments'"
          class="p-8 text-center"
        >
          <svg class="h-10 w-10 text-slate-custom-400 mx-auto mb-3" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
            No payments recorded yet. Click "Record Payment" to add one.
          </p>
        </div>

        <!-- Amortization Visualization (simple bars) -->
        <div
          v-if="amortizationData.length > 0"
          class="p-4 border-t border-navy-100 dark:border-navy-800"
        >
          <h3 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-3">
            Amortization Progress
          </h3>
          <div class="space-y-2">
            <div
              v-for="(point, idx) in amortizationData"
              :key="idx"
              class="flex items-center gap-3"
            >
              <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 w-20 flex-shrink-0">
                {{ formatDate(point.date) }}
              </span>
              <div class="flex-1 h-4 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
                <div
                  class="h-full rounded-full bg-cyan-500 transition-all duration-300"
                  :style="{ width: `${point.percentPaid}%` }"
                />
              </div>
              <span class="text-xs font-medium text-navy-900 dark:text-navy-100 w-14 text-right">
                {{ point.percentPaid.toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Edit Modal -->
      <DebtForm
        mode="edit"
        :item-id="debtId"
        :open="showEditModal"
        @saved="handleFormSaved"
        @cancel="closeEditModal"
      />

      <!-- Payment Modal -->
      <Modal
        :open="showPaymentModal"
        :title="editingPayment ? 'Edit Payment' : 'Record Payment'"
        size="md"
        @close="closePaymentModal"
      >
        <template #body>
          <DebtPaymentForm
            :debt-id="debt.id"
            :payment="editingPayment"
            :default-amount="debt.monthly_payment"
            @saved="handlePaymentSaved"
            @cancel="closePaymentModal"
          />
        </template>
      </Modal>

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
</template>
