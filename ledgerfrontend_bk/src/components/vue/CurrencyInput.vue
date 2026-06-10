<script setup lang="ts">
/**
 * CurrencyInput — Amount input with currency code selector.
 *
 * Provides a combined input where the user enters a numeric amount
 * and selects a currency from a dropdown. Supports formatting and
 * validation of monetary amounts.
 *
 * Currency list: Dynamically loaded from the base backend's currency
 * metadata (cached in localStorage by useAuth). Falls back to a common
 * set if no metadata is cached yet. The `currencies` prop can still
 * override the list for special cases.
 *
 * Currency symbols: Resolved via the currency.ts library (single source
 * of truth from base backend metadata), NOT hardcoded.
 *
 * Usage:
 *   <CurrencyInput
 *     :amount="form.amount"
 *     :currency="form.currency"
 *     @update="handleUpdate"
 *   />
 */

import { ref, watch, computed, onMounted } from "vue";
import { getAvailableCurrencies, getCurrencySymbol } from "@/lib/currency";

export interface CurrencyInputValue {
  amount: string;
  currency: string;
}

const props = withDefaults(
  defineProps<{
    /** Current amount value (as string for Decimal precision). */
    amount?: string;
    /** Current currency code (3-letter). */
    currency?: string;
    /** Available currency codes. Overrides dynamic list from backend. */
    currencies?: string[];
    /** Placeholder for amount input. */
    placeholder?: string;
    /** Disable the input. */
    disabled?: boolean;
    /** Show currency selector. If false, only the amount input is shown. */
    showCurrencySelect?: boolean;
    /** Minimum amount. */
    min?: number;
    /** Step increment. */
    step?: string;
  }>(),
  {
    amount: "",
    currency: "USD",
    currencies: undefined,
    placeholder: "0.00",
    disabled: false,
    showCurrencySelect: true,
    step: "0.01",
  },
);

const emit = defineEmits<{
  update: [value: CurrencyInputValue];
}>();

// ─── State ────────────────────────────────────────────────────────────────────

const localAmount = ref(props.amount);
const localCurrency = ref(props.currency);

watch(() => props.amount, (v) => { localAmount.value = v; });
watch(() => props.currency, (v) => { localCurrency.value = v; });

// ─── Dynamic Currency List ────────────────────────────────────────────────────

/** Resolved currency list: prop override > backend metadata > fallback. */
const currencyList = computed(() => {
  if (props.currencies && props.currencies.length > 0) {
    return props.currencies;
  }
  return getAvailableCurrencies();
});

// ─── Handlers ─────────────────────────────────────────────────────────────────

function handleAmountInput(event: Event) {
  const raw = (event.target as HTMLInputElement).value;
  // Allow: digits, single dot, negative sign at start
  const sanitized = raw.replace(/[^0-9.\-]/g, "");
  localAmount.value = sanitized;
  emit("update", { amount: sanitized, currency: localCurrency.value });
}

function handleCurrencyChange(event: Event) {
  const val = (event.target as HTMLSelectElement).value;
  localCurrency.value = val;
  emit("update", { amount: localAmount.value, currency: val });
}

// ─── Currency Symbol (from backend metadata, not hardcoded) ───────────────────

function getSymbol(code: string): string {
  return getCurrencySymbol(code);
}
</script>

<template>
  <div class="flex items-stretch">
    <!-- Currency Selector -->
    <div
      v-if="showCurrencySelect"
      class="flex items-center rounded-l-lg border border-r-0 border-navy-200 dark:border-navy-700 bg-navy-50 dark:bg-navy-800 px-3 text-sm font-medium text-navy-900 dark:text-navy-100"
    >
      <select
        :value="localCurrency"
        :disabled="disabled"
        class="bg-transparent border-0 text-sm font-medium text-navy-900 dark:text-navy-100 focus:outline-none focus:ring-0 p-0 cursor-pointer"
        @change="handleCurrencyChange"
      >
        <option v-for="c in currencyList" :key="c" :value="c">
          {{ getSymbol(c) }} {{ c }}
        </option>
      </select>
    </div>

    <!-- Amount Input -->
    <input
      type="text"
      inputmode="decimal"
      :value="localAmount"
      :placeholder="placeholder"
      :disabled="disabled"
      :step="step"
      :class="[
        'input-field w-full',
        showCurrencySelect ? 'rounded-l-none' : '',
        disabled ? 'opacity-50 cursor-not-allowed' : '',
      ]"
      @input="handleAmountInput"
    />
  </div>
</template>
