<script setup lang="ts">
/**
 * BillPaymentForm — Simple inline form for recording/editing a bill payment.
 *
 * Props:
 *   billId — the parent bill ID
 *   payment — existing BillPaymentOut for edit mode (undefined = create)
 *   defaultAmount — default amount string (typically the bill's amount)
 *
 * Emits:
 *   saved — with the created/updated BillPaymentOut
 *   cancel — to close the form/modal
 *
 * On submit, calls store.createPayment or store.updatePayment.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { FormErrors } from "@/components/vue";
import { useBillStore } from "@/stores/bill";
import type { BillPaymentOut } from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "BillPaymentForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = defineProps<{
  /** Parent bill ID. */
  billId: number;
  /** Existing payment for edit mode; undefined = create. */
  payment?: BillPaymentOut;
  /** Default amount (typically from the bill). */
  defaultAmount?: string;
}>();

const emit = defineEmits<{
  saved: [payment: BillPaymentOut];
  cancel: [];
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useBillStore();

// ─── Form State ──────────────────────────────────────────────────────────────

const isEdit = computed(() => !!props.payment);

const today = new Date().toISOString().split("T")[0];

const form = reactive({
  payment_date: props.payment?.payment_date ?? today,
  amount: props.payment?.amount ?? props.defaultAmount ?? "",
  notes: props.payment?.notes ?? "",
});

const loading = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── Methods ─────────────────────────────────────────────────────────────────

async function handleSubmit() {
  loading.value = true;
  error.value = null;
  fieldErrors.value = {};

  // Basic validation
  if (!form.payment_date) {
    fieldErrors.value = { payment_date: ["Payment date is required"] };
    loading.value = false;
    return;
  }
  if (!form.amount || parseFloat(form.amount) <= 0) {
    fieldErrors.value = { amount: ["A valid amount is required"] };
    loading.value = false;
    return;
  }

  try {
    const payload = {
      payment_date: form.payment_date,
      amount: form.amount,
      transaction_id: null,
      notes: form.notes || null,
    };

    let result: BillPaymentOut | null;

    if (isEdit.value && props.payment) {
      result = await store.updatePayment(props.billId, props.payment.id, payload);
    } else {
      result = await store.createPayment(props.billId, payload);
    }

    if (result) {
      emit("saved", result);
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to save payment";
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

    <!-- Amount -->
    <div class="space-y-1.5">
      <label for="payment-amount" class="label-text">
        Amount <span class="text-debit">*</span>
      </label>
      <input
        id="payment-amount"
        v-model="form.amount"
        type="text"
        inputmode="decimal"
        class="input-field"
        placeholder="0.00"
        required
      />
    </div>

    <!-- Notes -->
    <div class="space-y-1.5">
      <label for="payment-notes" class="label-text">Notes</label>
      <textarea
        id="payment-notes"
        v-model="form.notes"
        class="input-field min-h-[80px] resize-y"
        placeholder="Optional notes about this payment..."
        rows="3"
      />
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3 pt-2">
      <button
        type="button"
        class="btn-secondary"
        :disabled="loading"
        @click="handleCancel"
      >
        Cancel
      </button>
      <button
        type="submit"
        class="btn-primary"
        :disabled="loading"
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
