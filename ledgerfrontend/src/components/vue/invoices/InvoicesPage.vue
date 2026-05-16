<script setup lang="ts">
/**
 * InvoicesPage — DataTable-based list page for Invoice entities.
 *
 * Features:
 *   - Page header: "Invoices" title + "Create Invoice" button
 *   - Summary bar: Total Due, Total Paid, Overdue Count (3 cards)
 *   - DataTable with columns: Invoice #, Client, Issue Date, Due Date, Total, Paid, Due, Status
 *   - Status badge colors: Draft=slate, Sent=cyan, Viewed=blue, Partial=yellow, Paid=green, Overdue=red, Cancelled=gray
 *   - Search + FilterBar (status select, is_overdue toggle)
 *   - Create/Edit via InvoiceForm in Modal
 *   - "Mark as Paid" action via modal with InvoiceMarkPaid fields
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Click row navigates to detail page: /dashboard/invoices/${id}
 *   - Pagination via DataTable, EmptyState, LoadingSkeleton
 *
 * Registers as `LdgrInvoicesPage` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  DataTable,
  Modal,
  ConfirmDialog,
  StatusBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  FormErrors,
  FeatureGate,
  UpgradePrompt,
  PlanLimitBadge,
} from "@/components/vue";
import type { DataTableColumn, SortChangePayload, FilterConfig, StatusColorMap } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
} from "@/composables";
import { useInvoiceStore } from "@/stores/invoice";
import { useTransactionStore } from "@/stores/transaction";
import { useAccountStore } from "@/stores/account";
import type {
  InvoiceOut,
  InvoiceFilter,
  InvoiceMarkPaid,
} from "@/lib/ledgerTypes";
import InvoiceForm from "./InvoiceForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrInvoicesPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useInvoiceStore();
const transactionStore = useTransactionStore();
const accountStore = useAccountStore();

// ─── Mark Paid - Transaction Search ──────────────────────────────────────────

const markPaidTxSearch = ref("");
const markPaidTxResults = ref<Array<{ id: number; date: string; payee: string; amount_original: string; currency_original: string }>>([]);
const markPaidTxSearching = ref(false);
const markPaidTxSelected = ref<{ id: number; label: string } | null>(null);
const markPaidAutoCreateTx = ref(false);

async function searchMarkPaidTransactions() {
  if (!markPaidTxSearch.value || markPaidTxSearch.value.length < 2) {
    markPaidTxResults.value = [];
    return;
  }
  markPaidTxSearching.value = true;
  try {
    await transactionStore.fetchList({ search: markPaidTxSearch.value, limit: 10 });
    markPaidTxResults.value = transactionStore.items.map(t => ({
      id: t.id,
      date: t.date,
      payee: t.payee || `Transaction #${t.id}`,
      amount_original: t.amount_original,
      currency_original: t.currency_original,
    }));
  } catch {
    // Silently fail
  } finally {
    markPaidTxSearching.value = false;
  }
}

function selectMarkPaidTransaction(tx: { id: number; date: string; payee: string; amount_original: string; currency_original: string }) {
  markPaidForm.transaction_id = tx.id;
  markPaidTxSelected.value = {
    id: tx.id,
    label: `${tx.date} — ${tx.payee} (${parseFloat(tx.amount_original).toFixed(2)} ${tx.currency_original})`,
  };
  markPaidTxResults.value = [];
  markPaidTxSearch.value = "";
  markPaidAutoCreateTx.value = false;
}

function clearMarkPaidTransaction() {
  markPaidForm.transaction_id = null;
  markPaidTxSelected.value = null;
}

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

// ─── Invoice Status Color Map ────────────────────────────────────────────────

const invoiceStatusColorMap: StatusColorMap = {
  draft: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300", dot: "bg-slate-400" },
  sent: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300", dot: "bg-cyan-500" },
  viewed: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300", dot: "bg-blue-500" },
  partial: { bg: "bg-yellow-100 dark:bg-yellow-950/50", text: "text-yellow-800 dark:text-yellow-300", dot: "bg-yellow-500" },
  paid: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  overdue: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
  cancelled: { bg: "bg-gray-100 dark:bg-gray-800/50", text: "text-gray-700 dark:text-gray-300", dot: "bg-gray-400" },
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
} = useLedgerFilters<InvoiceFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["status", "client_name", "is_overdue", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "status",
    label: "Status",
    type: "select",
    placeholder: "All Statuses",
    options: [
      { label: "Draft", value: "DRAFT" },
      { label: "Sent", value: "SENT" },
      { label: "Viewed", value: "VIEWED" },
      { label: "Partial", value: "PARTIAL" },
      { label: "Paid", value: "PAID" },
      { label: "Overdue", value: "OVERDUE" },
      { label: "Cancelled", value: "CANCELLED" },
    ],
  },
  {
    key: "is_overdue",
    label: "Overdue Only",
    type: "select",
    placeholder: "All",
    options: [
      { label: "Yes", value: "true" },
      { label: "No", value: "false" },
    ],
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as InvoiceFilter,
  (partial) => store.setFilters(partial as Partial<InvoiceFilter>),
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
  if (key === "is_overdue") {
    // Convert string "true"/"false" to boolean
    const boolVal = value === "true" ? true : value === "false" ? false : null;
    setFilter("is_overdue" as keyof InvoiceFilter, boolVal as string | null);
  } else {
    setFilter(key as keyof InvoiceFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<InvoiceFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function handlePageChange(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

function handleSortChange(_payload: SortChangePayload): void {
  // Sort handled server-side
}

// ─── Summary ─────────────────────────────────────────────────────────────────

onMounted(() => {
  store.fetchOverdue();
});

const totalDue = computed(() => store.totalDue);
const totalPaid = computed(() => store.totalPaid);
const overdueCount = computed(() => store.overdueCount);

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<InvoiceOut>({
  store,
  entityName: "Invoice",
  getEntityLabel: (item) => item.invoice_number,
  onDeleted: () => {
    applyFilters();
    store.fetchOverdue(true);
  },
  onRestored: () => {
    applyFilters();
    store.fetchOverdue(true);
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

function openEditForm(item: InvoiceOut, event?: Event) {
  if (event) event.stopPropagation();
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved() {
  closeFormModal();
  applyFilters();
  store.fetchOverdue(true);
}

// ─── Mark as Paid Modal ──────────────────────────────────────────────────────

const showMarkPaidModal = ref(false);
const markPaidItemId = ref<number | undefined>(undefined);
const markPaidForm = reactive<InvoiceMarkPaid>({
  paid_date: "",
  amount_paid: "",
  transaction_id: null,
});
const markPaidLoading = ref(false);
const markPaidError = ref<string | null>(null);

function openMarkPaidModal(item: InvoiceOut, event?: Event) {
  if (event) event.stopPropagation();
  markPaidItemId.value = item.id;
  markPaidForm.paid_date = new Date().toISOString().split("T")[0];
  markPaidForm.amount_paid = item.amount_due || "";
  markPaidForm.transaction_id = null;
  markPaidError.value = null;
  markPaidTxSelected.value = null;
  markPaidTxSearch.value = "";
  markPaidTxResults.value = [];
  markPaidAutoCreateTx.value = false;
  showMarkPaidModal.value = true;
}

function closeMarkPaidModal() {
  showMarkPaidModal.value = false;
  markPaidItemId.value = undefined;
}

async function handleMarkPaid() {
  if (!markPaidItemId.value) return;
  markPaidLoading.value = true;
  markPaidError.value = null;
  try {
    // Auto-create transaction if requested and no existing link
    if (markPaidAutoCreateTx.value && !markPaidForm.transaction_id) {
      const invoice = store.items.find(i => i.id === markPaidItemId.value);
      if (invoice) {
        await accountStore.fetchDropdown();
        const assetAccount = accountStore.dropdown.find(a =>
          (a as Record<string, unknown>).account_type === 'ASSET'
        );
        if (assetAccount) {
          const newTx = await transactionStore.create({
            date: markPaidForm.paid_date,
            account_id: assetAccount.id,
            transaction_type: "INCOME",
            amount_original: markPaidForm.amount_paid || invoice.amount_due,
            currency_original: invoice.currency,
            payee: invoice.client_name,
            description: `Payment for Invoice #${invoice.invoice_number}`,
            status: "CLEARED",
          });
          markPaidForm.transaction_id = newTx.id;
        }
      }
    }

    const payload: InvoiceMarkPaid = {
      paid_date: markPaidForm.paid_date,
      amount_paid: markPaidForm.amount_paid || null,
      transaction_id: markPaidForm.transaction_id || null,
    };
    await store.markPaid(markPaidItemId.value, payload);
    closeMarkPaidModal();
    applyFilters();
    store.fetchOverdue(true);
  } catch (err) {
    markPaidError.value = err instanceof Error ? err.message : "Failed to mark as paid";
  } finally {
    markPaidLoading.value = false;
  }
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function handleRowClick(row: Record<string, unknown>) {
  const inv = row as unknown as InvoiceOut;
  if (typeof window !== "undefined") {
    window.location.href = `/dashboard/invoices/${inv.id}`;
  }
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onDeleteClick(event: Event, item: InvoiceOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: InvoiceOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

// ─── Table Columns ───────────────────────────────────────────────────────────

const columns = computed<DataTableColumn[]>(() => [
  { key: "invoice_number", label: "Invoice #", sortable: true, minWidth: "120px" },
  { key: "client_name", label: "Client", sortable: true, minWidth: "140px" },
  { key: "issue_date", label: "Issue Date", sortable: true, minWidth: "110px" },
  { key: "due_date", label: "Due Date", sortable: true, minWidth: "110px" },
  { key: "total_amount", label: "Total", sortable: true, align: "right", minWidth: "110px" },
  { key: "amount_paid", label: "Paid", align: "right", minWidth: "110px" },
  { key: "amount_due", label: "Due", align: "right", minWidth: "110px" },
  { key: "status", label: "Status", minWidth: "110px" },
  { key: "actions", label: "", align: "right", minWidth: "140px" },
]);

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);
</script>

<template>
  <FeatureGate feature="invoices" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Invoices</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Create and manage invoices for your clients
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-primary" @click="openCreateForm">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Create Invoice
        </button>
        <PlanLimitBadge max-key="max_invoices" feature-key="invoices" :current="store.items.length" />
      </div>
    </div>

    <!-- ── Summary Bar ────────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Due</p>
        <p class="text-xl font-bold text-debit">
          {{ formatCurrency(totalDue) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Paid</p>
        <p class="text-xl font-bold text-credit">
          {{ formatCurrency(totalPaid) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Overdue</p>
        <p class="text-xl font-bold text-debit">
          {{ overdueCount }}
        </p>
      </div>
    </div>

    <!-- ── Search + Filters ───────────────────────────────────────────────── -->
    <div class="space-y-3">
      <SearchInput
        v-model="searchQuery"
        placeholder="Search invoices by number or client..."
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
      title="No invoices found"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : 'Create your first invoice to start billing clients.'"
      :action-label="hasActiveFilters ? '' : 'Create Invoice'"
      @action="openCreateForm"
    />

    <!-- ── Data Table ─────────────────────────────────────────────────────── -->
    <DataTable
      v-else
      :columns="columns"
      :rows="(store.items as unknown as Record<string, unknown>[])"
      :loading="isLoading"
      :total="store.total"
      :limit="pagination.limit.value"
      :offset="pagination.offset.value"
      empty-text="No invoices found."
      @page-change="handlePageChange"
      @sort-change="handleSortChange"
      @row-click="handleRowClick"
    >
      <!-- Invoice # Column -->
      <template #cell-invoice_number="{ row }">
        <span class="text-sm font-medium text-cyan-700 dark:text-cyan-400">
          {{ (row as unknown as InvoiceOut).invoice_number }}
        </span>
      </template>

      <!-- Client Column -->
      <template #cell-client_name="{ row }">
        <div>
          <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
            {{ (row as unknown as InvoiceOut).client_name }}
          </span>
          <p
            v-if="(row as unknown as InvoiceOut).client_email"
            class="text-xs text-slate-custom-500 dark:text-slate-custom-400 truncate max-w-[180px]"
          >
            {{ (row as unknown as InvoiceOut).client_email }}
          </p>
        </div>
      </template>

      <!-- Issue Date Column -->
      <template #cell-issue_date="{ row }">
        <span class="text-sm text-navy-900 dark:text-navy-100 whitespace-nowrap">
          {{ formatDate((row as unknown as InvoiceOut).issue_date) }}
        </span>
      </template>

      <!-- Due Date Column -->
      <template #cell-due_date="{ row }">
        <span
          :class="[
            'text-sm whitespace-nowrap',
            (row as unknown as InvoiceOut).is_overdue
              ? 'text-debit font-medium'
              : 'text-navy-900 dark:text-navy-100',
          ]"
        >
          {{ formatDate((row as unknown as InvoiceOut).due_date) }}
        </span>
      </template>

      <!-- Total Column -->
      <template #cell-total_amount="{ row }">
        <span class="text-sm font-semibold text-navy-900 dark:text-navy-100">
          {{ formatCurrency((row as unknown as InvoiceOut).total_amount, (row as unknown as InvoiceOut).currency || "USD") }}
        </span>
      </template>

      <!-- Paid Column -->
      <template #cell-amount_paid="{ row }">
        <span class="text-sm text-credit">
          {{ formatCurrency((row as unknown as InvoiceOut).amount_paid, (row as unknown as InvoiceOut).currency || "USD") }}
        </span>
      </template>

      <!-- Due Column -->
      <template #cell-amount_due="{ row }">
        <span
          :class="[
            'text-sm font-medium',
            parseFloat((row as unknown as InvoiceOut).amount_due || '0') > 0
              ? 'text-debit'
              : 'text-credit',
          ]"
        >
          {{ formatCurrency((row as unknown as InvoiceOut).amount_due, (row as unknown as InvoiceOut).currency || "USD") }}
        </span>
      </template>

      <!-- Status Column -->
      <template #cell-status="{ row }">
        <StatusBadge
          :status="(row as unknown as InvoiceOut).status"
          :color-map="invoiceStatusColorMap"
          size="sm"
        />
      </template>

      <!-- Actions Column -->
      <template #cell-actions="{ row }">
        <div class="flex items-center justify-end gap-1" @click.stop>
          <!-- Edit -->
          <button
            class="btn-ghost rounded-lg p-1.5 text-slate-custom-500 hover:text-cyan-600 dark:hover:text-cyan-400"
            title="Edit invoice"
            :aria-label="`Edit ${(row as unknown as InvoiceOut).invoice_number}`"
            @click="openEditForm(row as unknown as InvoiceOut, $event)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Mark as Paid -->
          <button
            v-if="(row as unknown as InvoiceOut).status !== 'PAID' && (row as unknown as InvoiceOut).status !== 'CANCELLED' && !(row as unknown as InvoiceOut).is_deleted"
            class="btn-ghost rounded-lg p-1.5 text-slate-custom-500 hover:text-green-600 dark:hover:text-green-400"
            title="Mark as paid"
            :aria-label="`Mark ${(row as unknown as InvoiceOut).invoice_number} as paid`"
            @click="openMarkPaidModal(row as unknown as InvoiceOut, $event)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!(row as unknown as InvoiceOut).is_deleted"
            class="btn-ghost rounded-lg p-1.5 text-slate-custom-500 hover:text-debit"
            title="Delete invoice"
            :aria-label="`Delete ${(row as unknown as InvoiceOut).invoice_number}`"
            @click="onDeleteClick($event, row as unknown as InvoiceOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost rounded-lg p-1.5 text-slate-custom-500 hover:text-credit"
            title="Restore invoice"
            :aria-label="`Restore ${(row as unknown as InvoiceOut).invoice_number}`"
            @click="onRestoreClick($event, row as unknown as InvoiceOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </template>
    </DataTable>

    <!-- ── Create / Edit Modal ────────────────────────────────────────────── -->
    <Modal
      :open="showFormModal"
      :title="formMode === 'create' ? 'Create Invoice' : 'Edit Invoice'"
      size="xl"
      @close="closeFormModal"
    >
      <template #body>
        <InvoiceForm
          :mode="formMode"
          :item-id="editingItemId"
          @saved="handleFormSaved"
          @cancel="closeFormModal"
        />
      </template>
    </Modal>

    <!-- ── Mark as Paid Modal ─────────────────────────────────────────────── -->
    <Modal
      :open="showMarkPaidModal"
      title="Mark as Paid"
      size="md"
      @close="closeMarkPaidModal"
    >
      <template #body>
        <form @submit.prevent="handleMarkPaid" class="space-y-4">
          <FormErrors :errors="markPaidError" />

          <div class="space-y-1.5">
            <label for="mark-paid-date" class="label-text">
              Paid Date <span class="text-debit">*</span>
            </label>
            <input
              id="mark-paid-date"
              v-model="markPaidForm.paid_date"
              type="date"
              class="input-field"
              required
            />
          </div>

          <div class="space-y-1.5">
            <label for="mark-paid-amount" class="label-text">Amount Paid</label>
            <input
              id="mark-paid-amount"
              v-model="markPaidForm.amount_paid"
              type="number"
              step="0.01"
              min="0"
              class="input-field"
              placeholder="Defaults to amount due"
            />
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
              Leave empty to mark the full amount due as paid.
            </p>
          </div>

          <!-- Link to existing transaction or auto-create -->
          <div class="space-y-3">
            <div class="flex items-center gap-3">
              <label class="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  v-model="markPaidAutoCreateTx"
                  class="sr-only peer"
                  :disabled="!!markPaidForm.transaction_id"
                />
                <div class="w-9 h-5 bg-navy-200 dark:bg-navy-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-navy-300 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-600"></div>
              </label>
              <span class="text-sm text-navy-900 dark:text-navy-100">Auto-create income transaction</span>
            </div>

            <div v-if="!markPaidAutoCreateTx">
              <label class="label-text mb-1.5 block">Link to Transaction</label>
              <div v-if="markPaidTxSelected" class="flex items-center gap-2 rounded-lg bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-800 px-3 py-2">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
                </svg>
                <span class="text-sm text-navy-900 dark:text-navy-100 flex-1 truncate">
                  {{ markPaidTxSelected.label }}
                </span>
                <button type="button" class="text-slate-custom-400 hover:text-debit transition-colors" @click="clearMarkPaidTransaction">
                  <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                  </svg>
                </button>
              </div>
              <div v-else class="relative">
                <input
                  v-model="markPaidTxSearch"
                  type="text"
                  class="input-field w-full pr-8"
                  placeholder="Search transactions by payee..."
                  @input="searchMarkPaidTransactions"
                />
                <svg v-if="markPaidTxSearching" class="h-4 w-4 animate-spin text-cyan-600 absolute right-2 top-2.5" viewBox="0 0 24 24" fill="none">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                <div
                  v-if="markPaidTxResults.length > 0"
                  class="absolute z-10 mt-1 w-full bg-white dark:bg-navy-800 border border-navy-200 dark:border-navy-700 rounded-lg shadow-lg max-h-48 overflow-y-auto"
                >
                  <button
                    v-for="tx in markPaidTxResults"
                    :key="tx.id"
                    type="button"
                    class="w-full text-left px-3 py-2 text-sm hover:bg-cyan-50 dark:hover:bg-navy-700 transition-colors border-b border-navy-100 dark:border-navy-700 last:border-0"
                    @click="selectMarkPaidTransaction(tx)"
                  >
                    <span class="font-medium text-navy-900 dark:text-navy-100">{{ tx.payee }}</span>
                    <span class="text-slate-custom-500 ml-2">{{ tx.date }}</span>
                    <span class="text-cyan-600 dark:text-cyan-400 ml-2">{{ parseFloat(tx.amount_original).toFixed(2) }} {{ tx.currency_original }}</span>
                  </button>
                </div>
              </div>
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mt-1">
                Optionally link to an existing income transaction
              </p>
            </div>

            <p v-if="markPaidAutoCreateTx" class="text-xs text-amber-600 dark:text-amber-400">
              A new INCOME transaction will be created automatically when marking as paid.
            </p>
          </div>
        </form>
      </template>

      <template #footer>
        <button
          type="button"
          class="btn-secondary"
          :disabled="markPaidLoading"
          @click="closeMarkPaidModal"
        >
          Cancel
        </button>
        <button
          type="button"
          class="btn-primary"
          :disabled="markPaidLoading"
          @click="handleMarkPaid"
        >
          <svg
            v-if="markPaidLoading"
            class="h-4 w-4 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Mark as Paid
        </button>
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
  </div>
  <template #no-access>
    <UpgradePrompt feature="invoices" />
  </template>
  </FeatureGate>
</template>
