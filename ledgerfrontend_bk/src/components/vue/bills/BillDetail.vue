<script setup lang="ts">
/**
 * BillDetail — Full detail view for a single Bill.
 *
 * Features:
 *   - Header card: Payee, amount, recurrence badge, next due date, status badge
 *   - Action buttons: Edit, Delete/Restore, Pause/Cancel/Reactivate, Generate Transaction
 *   - Tab layout: Overview, Payment History
 *   - Overview: all bill fields in detail grid
 *   - Payment History: DataTable with Record Payment, Edit Payment
 *   - Record Payment modal with BillPaymentForm
 *   - ConfirmDialogs for delete/restore and status changes
 *
 * Registers as `ldgr-bill-detail` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  LoadingSkeleton,
  FormErrors,
  DataTable,
  Modal,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import type { DataTableColumn } from "@/components/vue";
import {
  useSoftDelete,
  useDropdownLoader,
} from "@/composables";
import { useBillStore } from "@/stores/bill";
import { useAccountStore } from "@/stores/account";
import { useCategoryStore } from "@/stores/category";
import type {
  BillOut,
  BillPaymentOut,
  BillGenerateTransactionOut,
} from "@/lib/ledgerTypes";
import BillForm from "./BillForm.vue";
import BillPaymentForm from "./BillPaymentForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrBillDetail",
});

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  /** Bill ID from Astro route param. */
  id: string;
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const billStore = useBillStore();
const accountStore = useAccountStore();
const categoryStore = useCategoryStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── State ───────────────────────────────────────────────────────────────────

const billId = computed(() => parseInt(props.id, 10));
const activeTab = ref<"overview" | "payments">("overview");
const showEditModal = ref(false);
const showPaymentModal = ref(false);
const editingPayment = ref<BillPaymentOut | undefined>(undefined);
const isGeneratingTransaction = ref(false);
const generateResult = ref<BillGenerateTransactionOut | null>(null);

// ─── Account & Category Lookup ───────────────────────────────────────────────

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

const categoryMap = computed(() => {
  const map = new Map<number, string>();
  for (const cat of dropdownLoader.getDropdown<{ id: number; name: string }>("categories")) {
    map.set(cat.id, cat.name);
  }
  return map;
});

function getCategoryName(categoryId: number | null): string {
  if (!categoryId) return "—";
  return categoryMap.value.get(categoryId) ?? "Unknown Category";
}

// ─── Load Data ───────────────────────────────────────────────────────────────

const isLoading = ref(true);
const loadError = ref<string | null>(null);

async function loadBill() {
  if (isNaN(billId.value)) {
    loadError.value = "Invalid bill ID";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = null;
  try {
    await billStore.fetchOne(billId.value);
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load bill";
  } finally {
    isLoading.value = false;
  }
}

async function loadPayments() {
  if (!isNaN(billId.value)) {
    await billStore.fetchPayments(billId.value);
  }
}

onMounted(async () => {
  await Promise.all([
    dropdownLoader.loadDropdown("accounts", accountStore),
    dropdownLoader.loadDropdown("categories", categoryStore),
  ]);
  await loadBill();
  await loadPayments();
});

watch(() => props.id, () => {
  loadBill();
  loadPayments();
});

// ─── Computed ────────────────────────────────────────────────────────────────

const bill = computed<BillOut | null>(() => billStore.current);

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

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString();
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

const billStatusColorMap = {
  active: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  paused: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300", dot: "bg-amber-500" },
  cancelled: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
};

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<BillOut>({
  store: billStore,
  entityName: "Bill",
  getEntityLabel: (item) => item.payee,
  onDeleted: () => {
    window.location.href = "/dashboard/bills";
  },
  onRestored: () => {
    loadBill();
  },
});

// ─── Status Action Confirmations ─────────────────────────────────────────────

const statusConfirmOpen = ref(false);
const statusAction = ref<"pause" | "cancel" | "reactivate">("pause");
const statusLoading = ref(false);

const statusDialogTitle = computed(() => {
  if (statusAction.value === "pause") return "Pause Bill";
  if (statusAction.value === "cancel") return "Cancel Bill";
  return "Reactivate Bill";
});

const statusDialogMessage = computed(() => {
  const name = bill.value?.payee ?? "this bill";
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

function confirmStatusAction(action: "pause" | "cancel" | "reactivate") {
  statusAction.value = action;
  statusConfirmOpen.value = true;
}

async function executeStatusAction() {
  if (!bill.value) return;
  statusLoading.value = true;
  try {
    if (statusAction.value === "pause") {
      await billStore.pause(bill.value.id);
    } else if (statusAction.value === "cancel") {
      await billStore.cancel(bill.value.id);
    } else {
      await billStore.reactivate(bill.value.id);
    }
    loadBill();
  } catch {
    // Error is handled by the store
  } finally {
    statusLoading.value = false;
    statusConfirmOpen.value = false;
  }
}

function cancelStatusAction() {
  statusConfirmOpen.value = false;
}

// ─── Generate Transaction ────────────────────────────────────────────────────

const generateConfirmOpen = ref(false);

function confirmGenerateTransaction() {
  generateConfirmOpen.value = true;
}

async function executeGenerateTransaction() {
  if (!bill.value) return;
  isGeneratingTransaction.value = true;
  generateResult.value = null;
  try {
    const result = await billStore.generateTransaction(bill.value.id);
    if (result) {
      generateResult.value = result;
    }
  } catch {
    // Error is handled by the store
  } finally {
    isGeneratingTransaction.value = false;
    generateConfirmOpen.value = false;
  }
}

// ─── Edit Modal ──────────────────────────────────────────────────────────────

function openEditModal() {
  showEditModal.value = true;
}

function closeEditModal() {
  showEditModal.value = false;
}

function handleFormSaved() {
  closeEditModal();
  loadBill();
}

// ─── Payment Modal ───────────────────────────────────────────────────────────

function openRecordPayment() {
  editingPayment.value = undefined;
  showPaymentModal.value = true;
}

function openEditPayment(payment: BillPaymentOut) {
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
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function goBack() {
  window.location.href = "/dashboard/bills";
}

// ─── Detail Field Component (local) ─────────────────────────────────────────

interface DetailField {
  label: string;
  value: string | number | null | undefined;
  type?: "text" | "currency" | "boolean" | "badge" | "date";
  currency?: string;
}

const overviewFields = computed<DetailField[]>(() => {
  if (!bill.value) return [];
  const b = bill.value;
  return [
    { label: "Payee", value: b.payee },
    { label: "Amount", value: b.amount, type: "currency", currency: b.currency },
    { label: "Currency", value: b.currency },
    { label: "Amount Type", value: b.is_amount_fixed ? "Fixed" : "Variable", type: "text" },
    { label: "Recurrence", value: b.recurrence, type: "badge" },
    { label: "Start Date", value: formatDate(b.start_date), type: "date" },
    { label: "End Date", value: formatDate(b.end_date), type: "date" },
    { label: "Next Due Date", value: formatDate(b.next_due_date), type: "date" },
    { label: "Account", value: getAccountName(b.account_id) },
    { label: "Category", value: getCategoryName(b.category_id) },
    { label: "Reminder", value: b.remind_me ? `Yes, ${b.days_before_reminder} days before` : "Off", type: "text" },
    { label: "Notes", value: b.notes || "—", type: "text" },
    { label: "Created", value: formatDate(b.created_at) },
    { label: "Last Updated", value: formatDate(b.updated_at) },
  ];
});

// ─── Payment History Table ───────────────────────────────────────────────────

const paymentColumns: DataTableColumn[] = [
  { key: "payment_date", label: "Date", sortable: true },
  { key: "amount", label: "Amount" },
  { key: "transaction_id", label: "Transaction" },
  { key: "notes", label: "Notes" },
  { key: "actions", label: "Actions", align: "right" as const },
];

function handleSortChange(payload: { key: string; direction: "asc" | "desc" }): void {
  void payload;
}

// ─── Tab Switch ──────────────────────────────────────────────────────────────

function switchTab(tab: "overview" | "payments") {
  activeTab.value = tab;
  if (tab === "payments") {
    loadPayments();
  }
}
</script>

<template>
  <FeatureGate feature="bills" show-fallback>
  <div class="space-y-6">
    <!-- Loading State -->
    <LoadingSkeleton v-if="isLoading" type="detail" />

    <!-- Error State -->
    <div v-else-if="loadError" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-debit" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-debit font-medium">Failed to load bill</p>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ loadError }}</p>
        <button class="btn-secondary" @click="loadBill">Try Again</button>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else-if="!bill" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <p class="text-navy-900 dark:text-navy-100 font-medium">Bill not found</p>
        <button class="btn-secondary" @click="goBack">Back to Bills</button>
      </div>
    </div>

    <!-- Bill Detail Content -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="goBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        Back to Bills
      </button>

      <!-- Header Card -->
      <div class="card p-6">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <!-- Left: Bill Info -->
          <div class="flex-1 space-y-3">
            <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
              {{ bill.payee }}
            </h1>
            <div class="flex flex-wrap items-center gap-2">
              <TypeBadge
                :type="bill.recurrence"
                :type-map="recurrenceTypeMap"
                :show-icon="false"
                size="md"
              />
              <StatusBadge
                :status="bill.status"
                :color-map="billStatusColorMap"
                size="md"
              />
              <span class="inline-flex items-center rounded-full bg-navy-100 dark:bg-navy-800 px-2.5 py-1 text-xs font-medium text-navy-700 dark:text-navy-300">
                {{ bill.currency }}
              </span>
              <!-- Fixed/Variable indicator -->
              <span
                v-if="bill.is_amount_fixed"
                class="inline-flex items-center gap-1 text-xs text-slate-custom-500 dark:text-slate-custom-400"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clip-rule="evenodd" />
                </svg>
                Fixed
              </span>
              <span
                v-else
                class="inline-flex items-center gap-1 text-xs text-slate-custom-500 dark:text-slate-custom-400"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 2a5 5 0 00-5 5v2a2 2 0 00-2 2v5a2 2 0 002 2h10a2 2 0 002-2v-5a2 2 0 00-2-2H7V7a3 3 0 015.905-.75 1 1 0 001.937-.5A5.002 5.002 0 0010 2z" />
                </svg>
                Variable
              </span>
            </div>
            <!-- Amount -->
            <div class="pt-2">
              <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-1">Amount</p>
              <p class="text-3xl font-bold tracking-tight text-navy-900 dark:text-navy-100">
                {{ formatCurrency(bill.amount, bill.currency) }}
              </p>
            </div>
            <!-- Next Due Date -->
            <p class="text-sm">
              <span class="text-slate-custom-500 dark:text-slate-custom-400">Next Due: </span>
              <span :class="['font-medium', getDueDateClass(bill.next_due_date)]">
                {{ getDueDateLabel(bill.next_due_date) }}
              </span>
            </p>
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
              Edit Bill
            </button>
            <button
              class="btn-secondary"
              :disabled="isGeneratingTransaction"
              @click="confirmGenerateTransaction"
            >
              <svg
                v-if="isGeneratingTransaction"
                class="h-4 w-4 animate-spin"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <svg v-else class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm7 1a1 1 0 10-2 0v3.586L7.707 7.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 8.586V5z" clip-rule="evenodd" />
              </svg>
              {{ isGeneratingTransaction ? 'Generating...' : 'Generate Transaction' }}
            </button>

            <!-- Status Actions -->
            <button
              v-if="bill.status === 'ACTIVE' && !bill.is_deleted"
              class="btn-ghost text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30"
              @click="confirmStatusAction('pause')"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Pause
            </button>
            <button
              v-if="bill.status === 'ACTIVE' && !bill.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="confirmStatusAction('cancel')"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
              </svg>
              Cancel Bill
            </button>
            <button
              v-if="bill.status !== 'ACTIVE' && !bill.is_deleted"
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="confirmStatusAction('reactivate')"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
              Reactivate
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!bill.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="deleter.confirmDelete(bill)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Delete
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="deleter.confirmRestore(bill)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              Restore
            </button>
          </div>
        </div>

        <!-- Generate Transaction Result Banner -->
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 -translate-y-2"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 -translate-y-2"
        >
          <div
            v-if="generateResult"
            class="mt-4 rounded-lg bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-200 dark:border-cyan-800 p-3"
          >
            <div class="flex items-center gap-2">
              <svg class="h-4 w-4 text-cyan-600 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              <p class="text-sm text-cyan-800 dark:text-cyan-300">
                Transaction created! ID:
                <a
                  :href="`/dashboard/transactions/${generateResult.transaction_id}`"
                  class="text-cyan-700 dark:text-cyan-200 underline hover:text-cyan-800 dark:hover:text-cyan-100"
                >
                  #{{ generateResult.transaction_id }}
                </a>
                — Next due date updated to {{ formatDate(generateResult.next_due_date) }}
              </p>
              <button
                class="ml-auto text-cyan-600 hover:text-cyan-800 dark:hover:text-cyan-200"
                @click="generateResult = null"
              >
                <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        </Transition>

        <!-- Store Error -->
        <FormErrors
          v-if="billStore.error"
          :errors="billStore.error"
          class="mt-4"
        />
      </div>

      <!-- Tabs -->
      <div class="border-b border-navy-200 dark:border-navy-700">
        <nav class="flex gap-6 -mb-px" aria-label="Bill detail tabs">
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
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Bill Details</h2>
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
              <!-- Recurrence Badge -->
              <template v-else-if="field.type === 'badge' && field.value">
                <TypeBadge
                  :type="String(field.value)"
                  :type-map="recurrenceTypeMap"
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
          :rows="(billStore.payments as Record<string, unknown>[])"
          :loading="billStore.loadingAction === 'fetchPayments'"
          :total="billStore.payments.length"
          :limit="billStore.payments.length || 25"
          :offset="0"
          @sort-change="handleSortChange"
        >
          <!-- Date Column -->
          <template #cell-payment_date="{ row }">
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatDate((row as BillPaymentOut).payment_date) }}
            </span>
          </template>

          <!-- Amount Column -->
          <template #cell-amount="{ row }">
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatCurrency((row as BillPaymentOut).amount, bill?.currency ?? "USD") }}
            </span>
          </template>

          <!-- Transaction Column -->
          <template #cell-transaction_id="{ row }">
            <a
              v-if="(row as BillPaymentOut).transaction_id"
              :href="`/dashboard/transactions/${(row as BillPaymentOut).transaction_id}`"
              class="text-sm text-cyan-600 hover:text-cyan-700 dark:text-cyan-400 dark:hover:text-cyan-300 underline transition-colors"
            >
              #{{ (row as BillPaymentOut).transaction_id }}
            </a>
            <span v-else class="text-sm text-slate-custom-400">—</span>
          </template>

          <!-- Notes Column -->
          <template #cell-notes="{ row }">
            <span class="text-sm text-slate-custom-600 dark:text-slate-custom-400 truncate max-w-[200px] inline-block">
              {{ (row as BillPaymentOut).notes || '—' }}
            </span>
          </template>

          <!-- Actions Column -->
          <template #cell-actions="{ row }">
            <button
              class="btn-ghost px-2 py-1 text-sm"
              title="Edit payment"
              aria-label="Edit payment"
              @click.stop="openEditPayment(row as BillPaymentOut)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
            </button>
          </template>
        </DataTable>

        <!-- Empty payments -->
        <div
          v-if="billStore.payments.length === 0 && billStore.loadingAction !== 'fetchPayments'"
          class="p-8 text-center"
        >
          <svg class="h-10 w-10 text-slate-custom-400 mx-auto mb-3" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
            No payments recorded yet. Click "Record Payment" to add one.
          </p>
        </div>
      </div>

      <!-- Edit Modal -->
      <BillForm
        mode="edit"
        :item-id="billId"
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
          <BillPaymentForm
            :bill-id="bill.id"
            :payment="editingPayment"
            :default-amount="bill.amount"
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

      <!-- Status Action ConfirmDialog -->
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

      <!-- Generate Transaction ConfirmDialog -->
      <ConfirmDialog
        :open="generateConfirmOpen"
        title="Generate Transaction"
        :message="`This will create a new transaction from this bill and advance the next due date. Continue?`"
        variant="warning"
        confirm-text="Generate"
        :loading="isGeneratingTransaction"
        @confirm="executeGenerateTransaction"
        @cancel="generateConfirmOpen = false"
      />
    </template>
  </div>
  <template #no-access>
    <UpgradePrompt feature="bills" />
  </template>
  </FeatureGate>
</template>
