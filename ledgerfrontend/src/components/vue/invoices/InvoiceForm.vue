<script setup lang="ts">
/**
 * InvoiceForm — Create/edit form for Invoice entities with line items.
 *
 * Features:
 *   - Header fields: invoice_number, client_name, client_email, issue_date,
 *     due_date, currency, status, notes, terms
 *   - Line items section (editable table):
 *     - Each row: description, quantity, unit_price, total (auto-calculated)
 *     - Add row, remove row buttons
 *     - Subtotal (sum of line item totals), tax_amount, total_amount (auto-calculated)
 *   - Uses useCrudForm composable
 *   - On edit: load existing line items from store.fetchLineItems()
 *   - On create: start with one empty line item row
 *
 * Emits 'saved' on successful create/update.
 */

import {
  FormErrors,
} from "@/components/vue";
import { useCrudForm } from "@/composables";
import { useInvoiceStore } from "@/stores/invoice";
import type {
  InvoiceOut,
  InvoiceCreate,
  InvoiceUpdate,
  InvoiceStatus,
  InvoiceLineItemOut,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "InvoiceForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Form mode: create or edit. */
    mode: "create" | "edit";
    /** Entity ID for edit mode. */
    itemId?: number;
    /** Whether the modal is open (parent controls visibility). */
    open?: boolean;
  }>(),
  {
    itemId: undefined,
    open: false,
  },
);

const emit = defineEmits<{
  saved: [item: InvoiceOut];
  cancel: [];
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const invoiceStore = useInvoiceStore();

// ─── Line Items State ────────────────────────────────────────────────────────

interface LineItemRow {
  id?: number;
  description: string;
  quantity: string;
  unit_price: string;
  total: string;
}

const lineItems = ref<LineItemRow[]>([]);

function createEmptyLineItem(): LineItemRow {
  return {
    description: "",
    quantity: "1",
    unit_price: "0",
    total: "0",
  };
}

// ─── Currency Options ────────────────────────────────────────────────────────

const currencyOptions = [
  { label: "USD — US Dollar", value: "USD" },
  { label: "EUR — Euro", value: "EUR" },
  { label: "GBP — British Pound", value: "GBP" },
  { label: "CAD — Canadian Dollar", value: "CAD" },
  { label: "AUD — Australian Dollar", value: "AUD" },
  { label: "JPY — Japanese Yen", value: "JPY" },
];

const statusOptions: { label: string; value: InvoiceStatus }[] = [
  { label: "Draft", value: "DRAFT" },
  { label: "Sent", value: "SENT" },
];

// ─── Auto-calculate line item total ─────────────────────────────────────────

function updateLineItemTotal(index: number) {
  const item = lineItems.value[index];
  if (!item) return;
  const qty = parseFloat(item.quantity) || 0;
  const price = parseFloat(item.unit_price) || 0;
  item.total = (qty * price).toFixed(2);
}

// ─── Computed totals ─────────────────────────────────────────────────────────

const subtotal = computed(() => {
  return lineItems.value.reduce((sum, item) => {
    return sum + (parseFloat(item.total) || 0);
  }, 0);
});

const computedTotalAmount = computed(() => {
  const tax = parseFloat(String(form.data.tax_amount)) || 0;
  return subtotal.value + tax;
});

// ─── Line item actions ──────────────────────────────────────────────────────

function addLineItem() {
  lineItems.value.push(createEmptyLineItem());
}

function removeLineItem(index: number) {
  lineItems.value.splice(index, 1);
  // Recalculate after removal
  if (lineItems.value.length === 0) {
    addLineItem(); // Keep at least one row
  }
}

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<InvoiceOut, InvoiceCreate, InvoiceUpdate>({
  store: invoiceStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      invoice_number: entity.invoice_number ?? "",
      client_name: entity.client_name ?? "",
      client_email: entity.client_email ?? "",
      issue_date: entity.issue_date ?? new Date().toISOString().split("T")[0],
      due_date: entity.due_date ?? "",
      currency: entity.currency ?? "USD",
      status: entity.status ?? "DRAFT",
      notes: entity.notes ?? "",
      terms: entity.terms ?? "",
      subtotal: entity.subtotal ?? "0",
      tax_amount: entity.tax_amount ?? "0",
      total_amount: entity.total_amount ?? "0",
    };
  },
  buildCreatePayload(formData) {
    return {
      invoice_number: String(formData.invoice_number),
      client_name: String(formData.client_name),
      client_email: formData.client_email ? String(formData.client_email) : null,
      issue_date: String(formData.issue_date),
      due_date: String(formData.due_date),
      currency: formData.currency ? String(formData.currency) : undefined,
      status: (formData.status as InvoiceStatus) || "DRAFT",
      subtotal: subtotal.value.toFixed(2),
      tax_amount: formData.tax_amount ? String(formData.tax_amount) : "0",
      total_amount: computedTotalAmount.value.toFixed(2),
      notes: formData.notes ? String(formData.notes) : null,
      terms: formData.terms ? String(formData.terms) : null,
    } as InvoiceCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Always include calculated fields
    diff.subtotal = subtotal.value.toFixed(2);
    diff.tax_amount = formData.tax_amount ? String(formData.tax_amount) : "0";
    diff.total_amount = computedTotalAmount.value.toFixed(2);

    // Coerce types for the API
    if ("client_email" in diff) diff.client_email = diff.client_email ? String(diff.client_email) : null;
    if ("currency" in diff) diff.currency = diff.currency ? String(diff.currency) : null;
    if ("status" in diff) diff.status = diff.status as InvoiceStatus;
    if ("notes" in diff) diff.notes = diff.notes ? String(diff.notes) : null;
    if ("terms" in diff) diff.terms = diff.terms ? String(diff.terms) : null;
    return diff as InvoiceUpdate;
  },
  onSuccess(item) {
    // After create/update, sync line items
    syncLineItems(item.id);
    emit("saved", item);
  },
});

// ─── Sync Line Items ────────────────────────────────────────────────────────

async function syncLineItems(invoiceId: number) {
  // For each line item, create/update as needed
  // Existing items (with id) might need update, new items need creation
  for (const item of lineItems.value) {
    const payload = {
      description: item.description,
      quantity: item.quantity || "1",
      unit_price: item.unit_price || "0",
      total: item.total || "0",
    };

    try {
      if (item.id) {
        // Update existing
        await invoiceStore.updateLineItem(invoiceId, item.id, payload);
      } else {
        // Create new
        await invoiceStore.createLineItem(invoiceId, payload);
      }
    } catch {
      // Silently continue — line item errors are non-blocking
    }
  }
}

// ─── Load entity data in edit mode ──────────────────────────────────────────

async function loadEditData() {
  if (props.mode === "edit" && props.itemId) {
    await form.load();
    // Load existing line items
    const items = await invoiceStore.fetchLineItems(props.itemId);
    if (items && items.length > 0) {
      lineItems.value = items.map((li: InvoiceLineItemOut) => ({
        id: li.id,
        description: li.description,
        quantity: li.quantity,
        unit_price: li.unit_price,
        total: li.total,
      }));
    } else {
      lineItems.value = [createEmptyLineItem()];
    }
  } else if (props.mode === "create") {
    // Set defaults for create mode
    form.setFieldValue("issue_date", new Date().toISOString().split("T")[0]);
    form.setFieldValue("currency", "USD");
    form.setFieldValue("status", "DRAFT");
    form.setFieldValue("tax_amount", "0");
    lineItems.value = [createEmptyLineItem()];
  }
}

onMounted(() => {
  loadEditData();
});

// ─── Auto-suggest invoice number for create mode ────────────────────────────

const invoiceNumberSuggestion = computed(() => {
  // Simple auto-suggest: INV-001 pattern
  const existing = invoiceStore.items;
  let maxNum = 0;
  for (const inv of existing) {
    const match = inv.invoice_number?.match(/INV-(\d+)/);
    if (match) {
      const num = parseInt(match[1], 10);
      if (num > maxNum) maxNum = num;
    }
  }
  return `INV-${String(maxNum + 1).padStart(3, "0")}`;
});

// ─── Computed ────────────────────────────────────────────────────────────────

const isEdit = computed(() => props.mode === "edit");

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}

function handleStatusChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as InvoiceStatus;
  form.setFieldValue("status", value);
}

function handleCurrencyChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  form.setFieldValue("currency", value);
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

    <!-- Invoice Number + Client Name -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="invoice-number" class="label-text">
          Invoice Number <span class="text-debit">*</span>
        </label>
        <input
          id="invoice-number"
          v-model="form.data.invoice_number"
          type="text"
          class="input-field"
          :placeholder="invoiceNumberSuggestion"
          required
        />
      </div>
      <div class="space-y-1.5">
        <label for="invoice-client" class="label-text">
          Client Name <span class="text-debit">*</span>
        </label>
        <input
          id="invoice-client"
          v-model="form.data.client_name"
          type="text"
          class="input-field"
          placeholder="e.g. Acme Corp"
          required
        />
      </div>
    </div>

    <!-- Client Email + Currency -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="invoice-email" class="label-text">Client Email</label>
        <input
          id="invoice-email"
          v-model="form.data.client_email"
          type="email"
          class="input-field"
          placeholder="client@example.com"
        />
      </div>
      <div class="space-y-1.5">
        <label for="invoice-currency" class="label-text">Currency</label>
        <select
          id="invoice-currency"
          :value="form.data.currency"
          class="input-field"
          @change="handleCurrencyChange"
        >
          <option
            v-for="opt in currencyOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- Issue Date + Due Date -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="invoice-issue-date" class="label-text">
          Issue Date <span class="text-debit">*</span>
        </label>
        <input
          id="invoice-issue-date"
          v-model="form.data.issue_date"
          type="date"
          class="input-field"
          required
        />
      </div>
      <div class="space-y-1.5">
        <label for="invoice-due-date" class="label-text">
          Due Date <span class="text-debit">*</span>
        </label>
        <input
          id="invoice-due-date"
          v-model="form.data.due_date"
          type="date"
          class="input-field"
          required
        />
      </div>
    </div>

    <!-- Status -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="invoice-status" class="label-text">Status</label>
        <select
          id="invoice-status"
          :value="form.data.status"
          class="input-field"
          @change="handleStatusChange"
        >
          <option
            v-for="opt in statusOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- ── Line Items Section ──────────────────────────────────────────────── -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Line Items</h3>
        <button
          type="button"
          class="btn-ghost text-sm text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300"
          @click="addLineItem"
        >
          <svg class="h-4 w-4 mr-1 inline" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Add Item
        </button>
      </div>

      <!-- Line Items Table -->
      <div class="overflow-x-auto rounded-lg border border-navy-200 dark:border-navy-700">
        <table class="w-full text-sm">
          <thead class="bg-navy-50 dark:bg-navy-900">
            <tr>
              <th class="px-3 py-2 text-left font-semibold text-navy-900 dark:text-navy-100 min-w-[200px]">Description</th>
              <th class="px-3 py-2 text-right font-semibold text-navy-900 dark:text-navy-100 w-24">Qty</th>
              <th class="px-3 py-2 text-right font-semibold text-navy-900 dark:text-navy-100 w-32">Unit Price</th>
              <th class="px-3 py-2 text-right font-semibold text-navy-900 dark:text-navy-100 w-32">Total</th>
              <th class="px-3 py-2 w-10"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-navy-100 dark:divide-navy-800">
            <tr
              v-for="(item, index) in lineItems"
              :key="index"
            >
              <td class="px-3 py-2">
                <input
                  v-model="item.description"
                  type="text"
                  class="input-field text-sm"
                  placeholder="Item description"
                />
              </td>
              <td class="px-3 py-2">
                <input
                  v-model="item.quantity"
                  type="number"
                  step="1"
                  min="0"
                  class="input-field text-sm text-right"
                  @input="updateLineItemTotal(index)"
                />
              </td>
              <td class="px-3 py-2">
                <input
                  v-model="item.unit_price"
                  type="number"
                  step="0.01"
                  min="0"
                  class="input-field text-sm text-right"
                  placeholder="0.00"
                  @input="updateLineItemTotal(index)"
                />
              </td>
              <td class="px-3 py-2">
                <input
                  :value="item.total"
                  type="text"
                  class="input-field text-sm text-right bg-navy-50 dark:bg-navy-800 cursor-not-allowed"
                  readonly
                  tabindex="-1"
                />
              </td>
              <td class="px-3 py-2">
                <button
                  type="button"
                  class="btn-ghost rounded-lg p-1 text-slate-custom-400 hover:text-debit transition-colors"
                  title="Remove item"
                  :aria-label="`Remove line item ${index + 1}`"
                  @click="removeLineItem(index)"
                >
                  <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Totals -->
      <div class="flex flex-col items-end gap-2 pt-3">
        <div class="flex items-center gap-4 text-sm w-full max-w-xs">
          <span class="text-slate-custom-600 dark:text-slate-custom-400 flex-1">Subtotal</span>
          <span class="font-medium text-navy-900 dark:text-navy-100 text-right">
            {{ new Intl.NumberFormat("en-US", { style: "currency", currency: String(form.data.currency || "USD") }).format(subtotal) }}
          </span>
        </div>
        <div class="flex items-center gap-4 text-sm w-full max-w-xs">
          <label for="invoice-tax" class="text-slate-custom-600 dark:text-slate-custom-400 flex-1">Tax</label>
          <input
            id="invoice-tax"
            v-model="form.data.tax_amount"
            type="number"
            step="0.01"
            min="0"
            class="input-field text-sm text-right w-28"
            placeholder="0.00"
          />
        </div>
        <div class="flex items-center gap-4 text-sm w-full max-w-xs pt-2 border-t border-navy-200 dark:border-navy-700">
          <span class="font-semibold text-navy-900 dark:text-navy-100 flex-1">Total</span>
          <span class="text-lg font-bold text-navy-900 dark:text-navy-100 text-right">
            {{ new Intl.NumberFormat("en-US", { style: "currency", currency: String(form.data.currency || "USD") }).format(computedTotalAmount) }}
          </span>
        </div>
      </div>
    </div>

    <!-- Notes -->
    <div class="space-y-1.5">
      <label for="invoice-notes" class="label-text">Notes</label>
      <textarea
        id="invoice-notes"
        v-model="form.data.notes"
        class="input-field min-h-[60px] resize-y"
        placeholder="Additional notes for the client..."
        rows="2"
      />
    </div>

    <!-- Terms -->
    <div class="space-y-1.5">
      <label for="invoice-terms" class="label-text">Terms & Conditions</label>
      <textarea
        id="invoice-terms"
        v-model="form.data.terms"
        class="input-field min-h-[60px] resize-y"
        placeholder="Payment terms and conditions..."
        rows="2"
      />
    </div>

    <!-- Footer Actions -->
    <div class="flex items-center justify-end gap-3 pt-4 border-t border-navy-200 dark:border-navy-700">
      <button
        type="button"
        class="btn-secondary"
        :disabled="form.loading.value"
        @click="handleCancel"
      >
        Cancel
      </button>
      <button
        type="button"
        class="btn-primary"
        :disabled="form.loading.value"
        @click="handleSubmit"
      >
        <svg
          v-if="form.loading.value"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ mode === "create" ? "Create Invoice" : "Update Invoice" }}
      </button>
    </div>
  </form>
</template>
