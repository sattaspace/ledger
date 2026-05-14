<script setup lang="ts">
/**
 * InvoiceDetail — Full detail view for a single Invoice.
 *
 * Features:
 *   - Loads invoice by ID from route (props: id as string)
 *   - Fetches line items via store.fetchLineItems()
 *   - Invoice preview card (formatted like a real invoice):
 *     - Header: Invoice #, Status badge, Dates (issue/due/paid)
 *     - Client info: name, email
 *     - Line items table: description, quantity, unit_price, total
 *     - Totals: subtotal, tax, total, paid, due
 *     - Notes, Terms
 *   - Status timeline: Draft → Sent → Viewed → Partial/Paid (visual step indicator)
 *   - Action buttons: Edit (opens InvoiceForm), Mark Paid (opens mark-paid modal), Delete/Restore
 *   - Mark Paid modal: paid_date, amount_paid
 *   - Back button to /dashboard/invoices
 *
 * Registers as `LdgrInvoiceDetail` custom element.
 */

import {
  ConfirmDialog,
  StatusBadge,
  LoadingSkeleton,
  FormErrors,
  Modal,
} from "@/components/vue";
import type { StatusColorMap } from "@/components/vue";
import {
  useSoftDelete,
} from "@/composables";
import { useInvoiceStore } from "@/stores/invoice";
import type {
  InvoiceOut,
  InvoiceMarkPaid,
} from "@/lib/ledgerTypes";
import InvoiceForm from "./InvoiceForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrInvoiceDetail",
});

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  /** Invoice ID from Astro route param. */
  id: string;
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const invoiceStore = useInvoiceStore();

// ─── State ───────────────────────────────────────────────────────────────────

const invoiceId = computed(() => parseInt(props.id, 10));
const showEditModal = ref(false);

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

// ─── Status Timeline ─────────────────────────────────────────────────────────

const timelineSteps = [
  { key: "DRAFT", label: "Draft" },
  { key: "SENT", label: "Sent" },
  { key: "VIEWED", label: "Viewed" },
  { key: "PARTIAL", label: "Partial" },
  { key: "PAID", label: "Paid" },
];

function getTimelineStepStatus(stepKey: string, invoice: InvoiceOut): "completed" | "current" | "pending" | "skipped" {
  const status = invoice.status;
  const stepOrder: Record<string, number> = {
    DRAFT: 0,
    SENT: 1,
    VIEWED: 2,
    PARTIAL: 3,
    PAID: 4,
  };
  const currentIdx = stepOrder[status] ?? 0;
  const stepIdx = stepOrder[stepKey] ?? 0;

  if (status === "CANCELLED" || status === "OVERDUE") {
    if (stepKey === "DRAFT" && status !== "CANCELLED") return "completed";
    return "skipped";
  }

  if (stepIdx < currentIdx) return "completed";
  if (stepIdx === currentIdx) return "current";
  return "pending";
}

// ─── Load Data ───────────────────────────────────────────────────────────────

const isLoading = ref(true);
const loadError = ref<string | null>(null);

async function loadInvoice() {
  if (isNaN(invoiceId.value)) {
    loadError.value = "Invalid invoice ID";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = null;
  try {
    await invoiceStore.fetchOne(invoiceId.value);
    await invoiceStore.fetchLineItems(invoiceId.value);
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load invoice";
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  loadInvoice();
});

watch(() => props.id, () => {
  loadInvoice();
});

// ─── Computed ────────────────────────────────────────────────────────────────

const invoice = computed<InvoiceOut | null>(() => invoiceStore.current);
const lineItems = computed(() => invoiceStore.lineItems);

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<InvoiceOut>({
  store: invoiceStore,
  entityName: "Invoice",
  getEntityLabel: (item) => item.invoice_number,
  onDeleted: () => {
    window.location.href = "/dashboard/invoices";
  },
  onRestored: () => {
    loadInvoice();
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
  loadInvoice();
}

// ─── Mark as Paid Modal ──────────────────────────────────────────────────────

const showMarkPaidModal = ref(false);
const markPaidForm = reactive<InvoiceMarkPaid>({
  paid_date: "",
  amount_paid: "",
  transaction_id: null,
});
const markPaidLoading = ref(false);
const markPaidError = ref<string | null>(null);

function openMarkPaidModal() {
  markPaidForm.paid_date = new Date().toISOString().split("T")[0];
  markPaidForm.amount_paid = invoice.value?.amount_due || "";
  markPaidForm.transaction_id = null;
  markPaidError.value = null;
  showMarkPaidModal.value = true;
}

function closeMarkPaidModal() {
  showMarkPaidModal.value = false;
}

async function handleMarkPaid() {
  if (!invoice.value) return;
  markPaidLoading.value = true;
  markPaidError.value = null;
  try {
    const payload: InvoiceMarkPaid = {
      paid_date: markPaidForm.paid_date,
      amount_paid: markPaidForm.amount_paid || null,
      transaction_id: markPaidForm.transaction_id || null,
    };
    await invoiceStore.markPaid(invoice.value.id, payload);
    closeMarkPaidModal();
    loadInvoice();
  } catch (err) {
    markPaidError.value = err instanceof Error ? err.message : "Failed to mark as paid";
  } finally {
    markPaidLoading.value = false;
  }
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function goBack() {
  window.location.href = "/dashboard/invoices";
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
        <p class="text-debit font-medium">Failed to load invoice</p>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ loadError }}</p>
        <button class="btn-secondary" @click="loadInvoice">Try Again</button>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else-if="!invoice" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <p class="text-navy-900 dark:text-navy-100 font-medium">Invoice not found</p>
        <button class="btn-secondary" @click="goBack">Back to Invoices</button>
      </div>
    </div>

    <!-- Invoice Detail Content -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="goBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        Back to Invoices
      </button>

      <!-- ── Invoice Preview Card ───────────────────────────────────────────── -->
      <div class="card p-6 space-y-6">
        <!-- Header -->
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <!-- Left: Invoice Info -->
          <div class="flex-1 space-y-3">
            <div class="flex items-center gap-3">
              <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
                {{ invoice.invoice_number }}
              </h1>
              <StatusBadge
                :status="invoice.status"
                :color-map="invoiceStatusColorMap"
                size="md"
              />
              <span
                v-if="invoice.is_overdue"
                class="inline-flex items-center rounded-full bg-red-100 dark:bg-red-950/50 px-2.5 py-1 text-xs font-medium text-red-800 dark:text-red-300"
              >
                Overdue
              </span>
            </div>

            <!-- Dates -->
            <div class="flex flex-wrap gap-4 text-sm">
              <div>
                <span class="text-slate-custom-500 dark:text-slate-custom-400">Issued:</span>
                <span class="ml-1 font-medium text-navy-900 dark:text-navy-100">{{ formatDate(invoice.issue_date) }}</span>
              </div>
              <div>
                <span class="text-slate-custom-500 dark:text-slate-custom-400">Due:</span>
                <span
                  :class="[
                    'ml-1 font-medium',
                    invoice.is_overdue ? 'text-debit' : 'text-navy-900 dark:text-navy-100',
                  ]"
                >
                  {{ formatDate(invoice.due_date) }}
                </span>
              </div>
              <div v-if="invoice.paid_date">
                <span class="text-slate-custom-500 dark:text-slate-custom-400">Paid:</span>
                <span class="ml-1 font-medium text-credit">{{ formatDate(invoice.paid_date) }}</span>
              </div>
            </div>
          </div>

          <!-- Right: Actions -->
          <div class="flex flex-col gap-2 md:items-end">
            <button class="btn-primary" @click="openEditModal">
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
              Edit Invoice
            </button>

            <button
              v-if="invoice.status !== 'PAID' && invoice.status !== 'CANCELLED' && !invoice.is_deleted"
              class="btn-ghost text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="openMarkPaidModal"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
              </svg>
              Mark as Paid
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!invoice.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="deleter.confirmDelete(invoice)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Delete
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="deleter.confirmRestore(invoice)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              Restore
            </button>
          </div>
        </div>

        <!-- ── Status Timeline ────────────────────────────────────────────── -->
        <div class="py-4 border-t border-b border-navy-100 dark:border-navy-800">
          <div class="flex items-center justify-between">
            <div
              v-for="(step, idx) in timelineSteps"
              :key="step.key"
              class="flex-1 flex items-center"
            >
              <div class="flex flex-col items-center flex-1">
                <div
                  :class="[
                    'h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors border-2',
                    getTimelineStepStatus(step.key, invoice) === 'completed'
                      ? 'bg-green-500 border-green-500 text-white'
                      : getTimelineStepStatus(step.key, invoice) === 'current'
                        ? 'bg-cyan-600 border-cyan-600 text-white'
                        : getTimelineStepStatus(step.key, invoice) === 'skipped'
                          ? 'bg-slate-200 dark:bg-navy-800 border-slate-300 dark:border-navy-600 text-slate-custom-400'
                          : 'bg-white dark:bg-navy-900 border-navy-200 dark:border-navy-700 text-slate-custom-400',
                  ]"
                >
                  <svg
                    v-if="getTimelineStepStatus(step.key, invoice) === 'completed'"
                    class="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                  </svg>
                  <span v-else>{{ idx + 1 }}</span>
                </div>
                <span
                  :class="[
                    'text-xs mt-1.5 whitespace-nowrap',
                    getTimelineStepStatus(step.key, invoice) === 'completed'
                      ? 'text-green-700 dark:text-green-400 font-medium'
                      : getTimelineStepStatus(step.key, invoice) === 'current'
                        ? 'text-cyan-700 dark:text-cyan-400 font-medium'
                        : 'text-slate-custom-500 dark:text-slate-custom-400',
                  ]"
                >
                  {{ step.label }}
                </span>
              </div>
              <!-- Connector line -->
              <div
                v-if="idx < timelineSteps.length - 1"
                :class="[
                  'h-0.5 flex-1 mt-[-16px]',
                  getTimelineStepStatus(timelineSteps[idx + 1]?.key, invoice) !== 'pending'
                    ? 'bg-green-400 dark:bg-green-600'
                    : 'bg-navy-200 dark:bg-navy-700',
                ]"
              />
            </div>
          </div>
        </div>

        <!-- ── Client Info ────────────────────────────────────────────────── -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div>
            <h3 class="text-xs font-semibold text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2">From</h3>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">Your Business</p>
          </div>
          <div>
            <h3 class="text-xs font-semibold text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2">Bill To</h3>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">{{ invoice.client_name }}</p>
            <p v-if="invoice.client_email" class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ invoice.client_email }}</p>
          </div>
        </div>

        <!-- ── Line Items Table ───────────────────────────────────────────── -->
        <div class="overflow-x-auto rounded-lg border border-navy-200 dark:border-navy-700">
          <table class="w-full text-sm">
            <thead class="bg-navy-50 dark:bg-navy-900">
              <tr>
                <th class="px-4 py-3 text-left font-semibold text-navy-900 dark:text-navy-100">Description</th>
                <th class="px-4 py-3 text-right font-semibold text-navy-900 dark:text-navy-100 w-20">Qty</th>
                <th class="px-4 py-3 text-right font-semibold text-navy-900 dark:text-navy-100 w-28">Unit Price</th>
                <th class="px-4 py-3 text-right font-semibold text-navy-900 dark:text-navy-100 w-28">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-navy-100 dark:divide-navy-800">
              <tr
                v-for="item in lineItems"
                :key="item.id"
              >
                <td class="px-4 py-3 text-navy-900 dark:text-navy-100">{{ item.description }}</td>
                <td class="px-4 py-3 text-right text-navy-900 dark:text-navy-100">{{ item.quantity }}</td>
                <td class="px-4 py-3 text-right text-navy-900 dark:text-navy-100">
                  {{ formatCurrency(item.unit_price, invoice.currency || "USD") }}
                </td>
                <td class="px-4 py-3 text-right font-medium text-navy-900 dark:text-navy-100">
                  {{ formatCurrency(item.total, invoice.currency || "USD") }}
                </td>
              </tr>
              <tr v-if="lineItems.length === 0">
                <td colspan="4" class="px-4 py-8 text-center text-slate-custom-500 dark:text-slate-custom-400">
                  No line items
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- ── Totals ──────────────────────────────────────────────────────── -->
        <div class="flex flex-col items-end">
          <div class="w-full max-w-xs space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-slate-custom-600 dark:text-slate-custom-400">Subtotal</span>
              <span class="font-medium text-navy-900 dark:text-navy-100">
                {{ formatCurrency(invoice.subtotal, invoice.currency || "USD") }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-slate-custom-600 dark:text-slate-custom-400">Tax</span>
              <span class="font-medium text-navy-900 dark:text-navy-100">
                {{ formatCurrency(invoice.tax_amount, invoice.currency || "USD") }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm pt-2 border-t border-navy-200 dark:border-navy-700">
              <span class="font-semibold text-navy-900 dark:text-navy-100">Total</span>
              <span class="text-lg font-bold text-navy-900 dark:text-navy-100">
                {{ formatCurrency(invoice.total_amount, invoice.currency || "USD") }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-credit">Paid</span>
              <span class="font-medium text-credit">
                -{{ formatCurrency(invoice.amount_paid, invoice.currency || "USD") }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm pt-2 border-t border-navy-200 dark:border-navy-700">
              <span class="font-semibold text-navy-900 dark:text-navy-100">Amount Due</span>
              <span
                :class="[
                  'text-lg font-bold',
                  parseFloat(invoice.amount_due || '0') > 0 ? 'text-debit' : 'text-credit',
                ]"
              >
                {{ formatCurrency(invoice.amount_due, invoice.currency || "USD") }}
              </span>
            </div>
          </div>
        </div>

        <!-- ── Notes & Terms ──────────────────────────────────────────────── -->
        <div
          v-if="invoice.notes || invoice.terms"
          class="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-4 border-t border-navy-100 dark:border-navy-800"
        >
          <div v-if="invoice.notes">
            <h3 class="text-xs font-semibold text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2">Notes</h3>
            <p class="text-sm text-navy-900 dark:text-navy-100 whitespace-pre-wrap">{{ invoice.notes }}</p>
          </div>
          <div v-if="invoice.terms">
            <h3 class="text-xs font-semibold text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2">Terms & Conditions</h3>
            <p class="text-sm text-navy-900 dark:text-navy-100 whitespace-pre-wrap">{{ invoice.terms }}</p>
          </div>
        </div>

        <!-- Store Error -->
        <FormErrors
          v-if="invoiceStore.error"
          :errors="invoiceStore.error"
          class="mt-4"
        />
      </div>

      <!-- Edit Modal -->
      <Modal
        :open="showEditModal"
        title="Edit Invoice"
        size="xl"
        @close="closeEditModal"
      >
        <template #body>
          <InvoiceForm
            mode="edit"
            :item-id="invoiceId"
            :open="showEditModal"
            @saved="handleFormSaved"
            @cancel="closeEditModal"
          />
        </template>
      </Modal>

      <!-- Mark as Paid Modal -->
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
              <label for="detail-paid-date" class="label-text">
                Paid Date <span class="text-debit">*</span>
              </label>
              <input
                id="detail-paid-date"
                v-model="markPaidForm.paid_date"
                type="date"
                class="input-field"
                required
              />
            </div>

            <div class="space-y-1.5">
              <label for="detail-paid-amount" class="label-text">Amount Paid</label>
              <input
                id="detail-paid-amount"
                v-model="markPaidForm.amount_paid"
                type="number"
                step="0.01"
                min="0"
                class="input-field"
                placeholder="Defaults to amount due"
              />
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
                Leave empty to mark the full amount due ({{ formatCurrency(invoice.amount_due, invoice.currency || "USD") }}) as paid.
              </p>
            </div>

            <div class="space-y-1.5">
              <label for="detail-paid-transaction" class="label-text">Transaction ID</label>
              <input
                id="detail-paid-transaction"
                v-model.number="markPaidForm.transaction_id"
                type="number"
                class="input-field"
                placeholder="Optional — link to existing transaction"
              />
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
    </template>
  </div>
</template>
