<script setup lang="ts">
/**
 * DebtPaymentForm — Create/edit form for DebtPayment entities.
 *
 * Fields:
 *   payment_date, amount, principal_portion, interest_portion,
 *   extra_payment, transaction (optional link), notes
 *
 * Used within DebtDetail's "Record Payment" modal.
 */

import {
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useDebtStore } from "@/stores/debt";
import { useTransactionStore } from "@/stores/transaction";
import type {
  DebtPaymentOut,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "DebtPaymentForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = defineProps<{
  /** The debt ID to record payment against. */
  debtId: number;
  /** Existing payment for edit mode. */
  payment?: DebtPaymentOut;
  /** Default amount (e.g. from debt monthly_payment). */
  defaultAmount?: string;
}>();

const emit = defineEmits<{
  saved: [item: DebtPaymentOut];
  cancel: [];
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const debtStore = useDebtStore();
const transactionStore = useTransactionStore();

// ─── Transaction Search ─────────────────────────────────────────────────────

const transactionSearch = ref("");
const transactionResults = ref<Array<{ id: number; date: string; payee: string; amount_original: string; currency_original: string }>>([]);
const isSearching = ref(false);
const selectedTransactionId = ref<number | null>(null);
const selectedTransactionLabel = ref("");

async function searchTransactions() {
  if (!transactionSearch.value || transactionSearch.value.length < 2) {
    transactionResults.value = [];
    return;
  }
  isSearching.value = true;
  try {
    await transactionStore.fetchList({ search: transactionSearch.value, limit: 10 });
    transactionResults.value = transactionStore.items.map(t => ({
      id: t.id,
      date: t.date,
      payee: t.payee || `Transaction #${t.id}`,
      amount_original: t.amount_original,
      currency_original: t.currency_original,
    }));
  } catch {
    // Silently fail
  } finally {
    isSearching.value = false;
  }
}

function selectTransaction(tx: { id: number; date: string; payee: string; amount_original: string; currency_original: string }) {
  selectedTransactionId.value = tx.id;
  selectedTransactionLabel.value = `${tx.date} — ${tx.payee} (${parseFloat(tx.amount_original).toFixed(2)} ${tx.currency_original})`;
  transactionResults.value = [];
  transactionSearch.value = "";
}

function clearTransactionLink() {
  selectedTransactionId.value = null;
  selectedTransactionLabel.value = "";
}

// ─── Form State ──────────────────────────────────────────────────────────────

const isEdit = computed(() => !!props.payment);

const form = ref({
  payment_date: props.payment?.payment_date ?? new Date().toISOString().split("T")[0],
  amount: props.payment?.amount ?? props.defaultAmount ?? "",
  principal_portion: props.payment?.principal_portion ?? "",
  interest_portion: props.payment?.interest_portion ?? "",
  extra_payment: props.payment?.extra_payment ?? "0",
  notes: props.payment?.notes ?? "",
});

// Initialize transaction link from existing payment
if (props.payment?.transaction_id) {
  selectedTransactionId.value = props.payment.transaction_id;
  selectedTransactionLabel.value = `Transaction #${props.payment.transaction_id}`;
}

const loading = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleAmountUpdate(data: { amount: string }) {
  form.value.amount = data.amount;
}

function handlePrincipalUpdate(data: { amount: string }) {
  form.value.principal_portion = data.amount;
}

function handleInterestUpdate(data: { amount: string }) {
  form.value.interest_portion = data.amount;
}

function handleExtraUpdate(data: { amount: string }) {
  form.value.extra_payment = data.amount;
}

async function handleSubmit() {
  loading.value = true;
  error.value = null;
  fieldErrors.value = {};

  try {
    const payload = {
      payment_date: form.value.payment_date,
      amount: String(form.value.amount),
      principal_portion: form.value.principal_portion ? String(form.value.principal_portion) : "0",
      interest_portion: form.value.interest_portion ? String(form.value.interest_portion) : "0",
      extra_payment: form.value.extra_payment ? String(form.value.extra_payment) : "0",
      transaction_id: selectedTransactionId.value,
      notes: form.value.notes || null,
    };

    let result: DebtPaymentOut | null;
    if (isEdit.value && props.payment) {
      result = await debtStore.updatePayment(props.debtId, props.payment.id, payload);
    } else {
      result = await debtStore.createPayment(props.debtId, payload);
    }

    if (result) {
      emit("saved", result);
    }
  } catch (err: unknown) {
    if (typeof err === "object" && err !== null) {
      const obj = err as Record<string, unknown>;
      if (typeof obj.message === "string") error.value = obj.message;
      else if (typeof obj.detail === "string") error.value = obj.detail;
      else error.value = "Failed to save payment";
    } else {
      error.value = "Failed to save payment";
    }
  } finally {
    loading.value = false;
  }
}

function handleCancel() {
  emit("cancel");
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="error" :field-errors="fieldErrors" />

    <!-- Payment Date -->
    <div class="space-y-1.5">
      <label for="payment-date" class="label-text">
        Payment Date <span class="text-debit">*</span>
      </label>
      <input
        id="payment-date"
        v-model="form.payment_date"
        type="date"
        class="input-field"
        required
      />
    </div>

    <!-- Total Amount -->
    <div class="space-y-1.5">
      <label class="label-text">
        Total Amount <span class="text-debit">*</span>
      </label>
      <CurrencyInput
        :amount="String(form.amount)"
        :show-currency-select="false"
        placeholder="0.00"
        @update="handleAmountUpdate"
      />
    </div>

    <!-- Principal Portion + Interest Portion -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label class="label-text">Principal Portion</label>
        <CurrencyInput
          :amount="String(form.principal_portion)"
          :show-currency-select="false"
          placeholder="0.00"
          @update="handlePrincipalUpdate"
        />
      </div>
      <div class="space-y-1.5">
        <label class="label-text">Interest Portion</label>
        <CurrencyInput
          :amount="String(form.interest_portion)"
          :show-currency-select="false"
          placeholder="0.00"
          @update="handleInterestUpdate"
        />
      </div>
    </div>

    <!-- Extra Payment -->
    <div class="space-y-1.5">
      <label class="label-text">Extra Payment</label>
      <CurrencyInput
        :amount="String(form.extra_payment)"
        :show-currency-select="false"
        placeholder="0.00"
        @update="handleExtraUpdate"
      />
      <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Additional payment beyond the regular amount
      </p>
    </div>

    <!-- Linked Transaction -->
    <div class="space-y-1.5">
      <label class="label-text">Linked Transaction</label>
      <div v-if="selectedTransactionId" class="flex items-center gap-2 rounded-lg bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-800 px-3 py-2">
        <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <span class="text-sm text-navy-900 dark:text-navy-100 flex-1 truncate">
          {{ selectedTransactionLabel }}
        </span>
        <button
          type="button"
          class="text-slate-custom-400 hover:text-debit transition-colors"
          @click="clearTransactionLink"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
      <div v-else class="relative">
        <input
          v-model="transactionSearch"
          type="text"
          class="input-field w-full pr-8"
          placeholder="Search transactions by payee..."
          @input="searchTransactions"
        />
        <svg v-if="isSearching" class="h-4 w-4 animate-spin text-cyan-600 absolute right-2 top-2.5" viewBox="0 0 24 24" fill="none">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <!-- Search Results Dropdown -->
        <div
          v-if="transactionResults.length > 0"
          class="absolute z-10 mt-1 w-full bg-white dark:bg-navy-800 border border-navy-200 dark:border-navy-700 rounded-lg shadow-lg max-h-48 overflow-y-auto"
        >
          <button
            v-for="tx in transactionResults"
            :key="tx.id"
            type="button"
            class="w-full text-left px-3 py-2 text-sm hover:bg-cyan-50 dark:hover:bg-navy-700 transition-colors border-b border-navy-100 dark:border-navy-700 last:border-0"
            @click="selectTransaction(tx)"
          >
            <span class="font-medium text-navy-900 dark:text-navy-100">{{ tx.payee }}</span>
            <span class="text-slate-custom-500 ml-2">{{ tx.date }}</span>
            <span class="text-cyan-600 dark:text-cyan-400 ml-2">{{ parseFloat(tx.amount_original).toFixed(2) }} {{ tx.currency_original }}</span>
          </button>
        </div>
      </div>
      <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Optionally link this payment to an existing transaction
      </p>
    </div>

    <!-- Notes -->
    <div class="space-y-1.5">
      <label for="payment-notes" class="label-text">Notes</label>
      <textarea
        id="payment-notes"
        v-model="form.notes"
        class="input-field min-h-[60px] resize-y"
        placeholder="Optional notes about this payment..."
        rows="2"
      />
    </div>

    <!-- Footer Buttons -->
    <div class="flex items-center justify-end gap-3 pt-3 border-t border-navy-100 dark:border-navy-800">
      <button
        type="button"
        class="btn-secondary"
        :disabled="loading"
        @click="handleCancel"
      >
        Cancel
      </button>
      <button
        type="button"
        class="btn-primary"
        :disabled="loading"
        @click="handleSubmit"
      >
        <svg
          v-if="loading"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ isEdit ? "Update Payment" : "Record Payment" }}
      </button>
    </div>
  </form>
</template>
