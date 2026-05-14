<script setup lang="ts">
/**
 * TransferForm — Create an internal transfer between two accounts.
 *
 * Always in create mode. Creates two linked transactions (outflow + inflow)
 * via the transaction store's createTransfer() method.
 *
 * Features:
 *   - From/To account selectors with validation (must be different)
 *   - Amount with currency selector
 *   - Date, description, status fields
 *   - Auto-currency from "from" account
 *   - FormErrors display
 */

import {
  FormErrors,
  CurrencyInput,
} from "@/components/vue";
import type { CurrencyInputValue } from "@/components/vue";

import { useDropdownLoader } from "@/composables";

import { useTransactionStore } from "@/stores/transaction";
import { useAccountStore } from "@/stores/account";

import type {
  TransactionStatus,
  TransferCreate,
} from "@/lib/ledgerTypes";

// ─── Emits ───────────────────────────────────────────────────────────────────

const emit = defineEmits<{
  saved: [];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const transactionStore = useTransactionStore();
const accountStore = useAccountStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── Form State ──────────────────────────────────────────────────────────────

const fromAccountId = ref<number | string>("");
const toAccountId = ref<number | string>("");
const amount = ref("");
const currency = ref("USD");
const date = ref(today());
const description = ref("");
const status = ref<TransactionStatus>("PENDING");

// ─── Error State ─────────────────────────────────────────────────────────────

const submitting = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── Status Options ──────────────────────────────────────────────────────────

const statusOptions: { value: TransactionStatus; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "CLEARED", label: "Cleared" },
];

// ─── Auto-currency from "from" account ───────────────────────────────────────

watch(fromAccountId, (newId) => {
  if (newId) {
    const account = accountStore.dropdown.find((a) => a.id === Number(newId));
    if (account) {
      currency.value = account.currency || "USD";
    }
  }
});

// ─── Same account validation ─────────────────────────────────────────────────

const sameAccountError = computed(() => {
  if (fromAccountId.value && toAccountId.value && fromAccountId.value === toAccountId.value) {
    return "From and To accounts must be different";
  }
  return "";
});

// ─── Helper ──────────────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().split("T")[0];
}

// ─── Submit ──────────────────────────────────────────────────────────────────

async function handleSubmit() {
  // Clear previous errors
  error.value = null;
  fieldErrors.value = {};

  // Client-side validation
  if (!fromAccountId.value) {
    fieldErrors.value = { from_account_id: ["From account is required"] };
    return;
  }
  if (!toAccountId.value) {
    fieldErrors.value = { to_account_id: ["To account is required"] };
    return;
  }
  if (sameAccountError.value) {
    fieldErrors.value = { to_account_id: [sameAccountError.value] };
    return;
  }
  if (!amount.value || parseFloat(amount.value) <= 0) {
    fieldErrors.value = { amount: ["Amount must be greater than 0"] };
    return;
  }
  if (!date.value) {
    fieldErrors.value = { date: ["Date is required"] };
    return;
  }

  submitting.value = true;

  try {
    const payload: TransferCreate = {
      date: date.value,
      from_account_id: Number(fromAccountId.value),
      to_account_id: Number(toAccountId.value),
      amount: amount.value,
      currency: currency.value,
      description: description.value || null,
      status: status.value,
    };

    await transactionStore.createTransfer(payload);
    emit("saved");
  } catch (err) {
    if (err && typeof err === "object" && "errors" in err) {
      fieldErrors.value = (err as { errors: Record<string, string[]> }).errors;
    } else {
      error.value = err instanceof Error ? err.message : "Failed to create transfer";
    }
  } finally {
    submitting.value = false;
  }
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(async () => {
  await dropdownLoader.loadDropdown("accounts", accountStore);
});
</script>

<template>
  <div class="space-y-5">
    <form @submit.prevent="handleSubmit" class="space-y-5">
      <!-- Form Errors -->
      <FormErrors :errors="error" :field-errors="fieldErrors" />

      <!-- Transfer Visual Indicator -->
      <div class="flex items-center gap-3 py-2">
        <!-- From Account -->
        <div class="flex-1 text-center">
          <div
            :class="[
              'rounded-lg border-2 border-dashed p-3 transition-colors',
              fromAccountId
                ? 'border-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/20'
                : 'border-navy-200 dark:border-navy-700',
            ]"
          >
            <svg class="h-6 w-6 mx-auto mb-1 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4zM2 10v4a2 2 0 002 2h12a2 2 0 002-2v-4H2zm4 2h2a1 1 0 100-2H6a1 1 0 100 2z" />
            </svg>
            <span class="text-xs text-slate-custom-500">From</span>
          </div>
        </div>

        <!-- Arrow -->
        <div class="flex-shrink-0">
          <svg class="h-6 w-6 text-cyan-600" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 10a1 1 0 011-1h9.586L9.293 4.707a1 1 0 011.414-1.414l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L13.586 11H4a1 1 0 01-1-1z" clip-rule="evenodd" />
          </svg>
        </div>

        <!-- To Account -->
        <div class="flex-1 text-center">
          <div
            :class="[
              'rounded-lg border-2 border-dashed p-3 transition-colors',
              toAccountId && !sameAccountError
                ? 'border-credit bg-green-50/50 dark:bg-green-950/20'
                : sameAccountError
                  ? 'border-debit bg-red-50/50 dark:bg-red-950/20'
                  : 'border-navy-200 dark:border-navy-700',
            ]"
          >
            <svg class="h-6 w-6 mx-auto mb-1 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
              <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4zM2 10v4a2 2 0 002 2h12a2 2 0 002-2v-4H2zm4 2h2a1 1 0 100-2H6a1 1 0 100 2z" />
            </svg>
            <span class="text-xs text-slate-custom-500">To</span>
          </div>
        </div>
      </div>

      <!-- From Account -->
      <div>
        <label class="label-text mb-1.5 block">From Account <span class="text-debit">*</span></label>
        <select
          v-model="fromAccountId"
          class="input-field w-full"
          required
        >
          <option value="" disabled>Select source account...</option>
          <option
            v-for="acct in dropdownLoader.getDropdown<{ id: number; name: string; currency: string }>('accounts')"
            :key="acct.id"
            :value="String(acct.id)"
          >
            {{ acct.name }} ({{ acct.currency }})
          </option>
        </select>
        <p v-if="fieldErrors.from_account_id" class="mt-1 text-xs text-debit">{{ fieldErrors.from_account_id[0] }}</p>
      </div>

      <!-- To Account -->
      <div>
        <label class="label-text mb-1.5 block">To Account <span class="text-debit">*</span></label>
        <select
          v-model="toAccountId"
          class="input-field w-full"
          required
        >
          <option value="" disabled>Select destination account...</option>
          <option
            v-for="acct in dropdownLoader.getDropdown<{ id: number; name: string; currency: string }>('accounts')"
            :key="acct.id"
            :value="String(acct.id)"
          >
            {{ acct.name }} ({{ acct.currency }})
          </option>
        </select>
        <p v-if="sameAccountError" class="mt-1 text-xs text-debit">{{ sameAccountError }}</p>
        <p v-else-if="fieldErrors.to_account_id" class="mt-1 text-xs text-debit">{{ fieldErrors.to_account_id[0] }}</p>
      </div>

      <!-- Amount + Currency -->
      <div>
        <label class="label-text mb-1.5 block">Amount <span class="text-debit">*</span></label>
        <CurrencyInput
          :amount="amount"
          :currency="currency"
          @update="(val: CurrencyInputValue) => { amount = val.amount; currency = val.currency; }"
        />
        <p v-if="fieldErrors.amount" class="mt-1 text-xs text-debit">{{ fieldErrors.amount[0] }}</p>
      </div>

      <!-- Date -->
      <div>
        <label class="label-text mb-1.5 block">Date <span class="text-debit">*</span></label>
        <input
          v-model="date"
          type="date"
          class="input-field w-full"
          required
        />
        <p v-if="fieldErrors.date" class="mt-1 text-xs text-debit">{{ fieldErrors.date[0] }}</p>
      </div>

      <!-- Description -->
      <div>
        <label class="label-text mb-1.5 block">Description</label>
        <textarea
          v-model="description"
          class="input-field w-full min-h-[80px] resize-y"
          placeholder="Optional description for this transfer..."
          rows="3"
        />
      </div>

      <!-- Status -->
      <div>
        <label class="label-text mb-1.5 block">Status</label>
        <select v-model="status" class="input-field w-full">
          <option v-for="st in statusOptions" :key="st.value" :value="st.value">
            {{ st.label }}
          </option>
        </select>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-navy-200 dark:border-navy-700">
        <button
          type="button"
          class="btn-secondary"
          :disabled="submitting"
          @click="emit('cancel')"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="btn-primary"
          :disabled="submitting || !!sameAccountError"
        >
          <svg
            v-if="submitting"
            class="h-4 w-4 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Create Transfer
        </button>
      </div>
    </form>
  </div>
</template>
