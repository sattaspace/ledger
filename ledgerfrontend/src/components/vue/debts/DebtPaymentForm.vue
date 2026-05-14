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
