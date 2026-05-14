<script setup lang="ts">
/**
 * HoldingForm — Create/edit form for Holding entities within an InvestmentAccount.
 *
 * Fields:
 *   symbol, asset_name, asset_type (Stock/ETF/Crypto/Bond/Mutual Fund/Other),
 *   quantity, cost_basis, current_price, current_value, currency, purchase_date
 *
 * On create: investment_account_id is set from the parent investment.
 * On edit: pre-populated from the existing holding.
 *
 * Emits 'saved' on successful create/update.
 */

import {
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useInvestmentStore } from "@/stores/investment";
import type {
  HoldingOut,
  AssetType,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "HoldingForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = defineProps<{
  /** The investment account this holding belongs to. */
  investmentId: number;
  /** Existing holding for edit mode (undefined = create mode). */
  holding?: HoldingOut;
}>();

const emit = defineEmits<{
  saved: [];
  cancel: [];
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const investmentStore = useInvestmentStore();

// ─── Form State ──────────────────────────────────────────────────────────────

const isEdit = computed(() => !!props.holding);

const formData = reactive({
  symbol: props.holding?.symbol ?? "",
  asset_name: props.holding?.asset_name ?? "",
  asset_type: (props.holding?.asset_type ?? "STOCK") as AssetType,
  quantity: props.holding?.quantity ?? "",
  cost_basis: props.holding?.cost_basis ?? "",
  current_price: props.holding?.current_price ?? "",
  current_value: props.holding?.current_value ?? "",
  currency: props.holding?.currency ?? "USD",
  purchase_date: props.holding?.purchase_date ?? "",
});

const saving = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── Asset Type Options ──────────────────────────────────────────────────────

const assetTypeOptions: { label: string; value: AssetType }[] = [
  { label: "Stock", value: "STOCK" },
  { label: "ETF", value: "ETF" },
  { label: "Crypto", value: "CRYPTO" },
  { label: "Bond", value: "BOND" },
  { label: "Mutual Fund", value: "MUTUAL_FUND" },
  { label: "Other", value: "OTHER" },
];

// ─── Currency Options ────────────────────────────────────────────────────────

const currencyOptions = [
  "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "BDT",
];

// ─── Auto-calculate current_value from quantity × current_price ──────────────

watch(
  () => [formData.quantity, formData.current_price],
  ([qty, price]) => {
    const q = parseFloat(qty || "0");
    const p = parseFloat(price || "0");
    if (q > 0 && p > 0) {
      formData.current_value = (q * p).toFixed(2);
    }
  },
);

// ─── Handlers ────────────────────────────────────────────────────────────────

function handleCostBasisUpdate(data: { amount: string; currency: string }) {
  formData.cost_basis = data.amount;
}

function handleCurrentPriceUpdate(data: { amount: string; currency: string }) {
  formData.current_price = data.amount;
}

function handleCurrentValueUpdate(data: { amount: string; currency: string }) {
  formData.current_value = data.amount;
}

function handleAssetTypeChange(event: Event) {
  formData.asset_type = (event.target as HTMLSelectElement).value as AssetType;
}

function handleCurrencyChange(event: Event) {
  formData.currency = (event.target as HTMLSelectElement).value;
}

// ─── Submit ──────────────────────────────────────────────────────────────────

async function handleSubmit() {
  saving.value = true;
  error.value = null;
  fieldErrors.value = {};

  try {
    if (isEdit.value && props.holding) {
      // Build update payload with only changed fields
      const updateData: Record<string, unknown> = {};
      const original = props.holding;

      if (formData.symbol !== original.symbol) updateData.symbol = formData.symbol;
      if (formData.asset_name !== original.asset_name) updateData.asset_name = formData.asset_name;
      if (formData.asset_type !== original.asset_type) updateData.asset_type = formData.asset_type;
      if (formData.quantity !== original.quantity) updateData.quantity = formData.quantity || null;
      if (formData.cost_basis !== original.cost_basis) updateData.cost_basis = formData.cost_basis || null;
      if (formData.current_price !== original.current_price) updateData.current_price = formData.current_price || null;
      if (formData.current_value !== original.current_value) updateData.current_value = formData.current_value || null;
      if (formData.currency !== original.currency) updateData.currency = formData.currency;
      if (formData.purchase_date !== original.purchase_date) updateData.purchase_date = formData.purchase_date || null;

      await investmentStore.updateHolding(
        props.investmentId,
        props.holding.id,
        updateData as any,
      );
    } else {
      // Create new holding
      await investmentStore.createHolding(props.investmentId, {
        symbol: formData.symbol,
        asset_name: formData.asset_name,
        asset_type: formData.asset_type,
        quantity: formData.quantity || "0",
        cost_basis: formData.cost_basis || "0",
        current_price: formData.current_price || null,
        current_value: formData.current_value || null,
        currency: formData.currency || "USD",
        purchase_date: formData.purchase_date || null,
      });
    }

    emit("saved");
  } catch (err: unknown) {
    if (err && typeof err === "object" && "errors" in err) {
      fieldErrors.value = (err as any).errors ?? {};
    }
    error.value = err instanceof Error ? err.message : "Failed to save holding";
  } finally {
    saving.value = false;
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

    <!-- Symbol + Asset Name -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="holding-symbol" class="label-text">
          Symbol <span class="text-debit">*</span>
        </label>
        <input
          id="holding-symbol"
          v-model="formData.symbol"
          type="text"
          class="input-field"
          placeholder="e.g. AAPL, BTC, VOO"
          required
        />
      </div>
      <div class="space-y-1.5">
        <label for="holding-name" class="label-text">
          Asset Name <span class="text-debit">*</span>
        </label>
        <input
          id="holding-name"
          v-model="formData.asset_name"
          type="text"
          class="input-field"
          placeholder="e.g. Apple Inc., Bitcoin, Vanguard S&P 500"
          required
        />
      </div>
    </div>

    <!-- Asset Type + Currency -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="holding-type" class="label-text">
          Asset Type <span class="text-debit">*</span>
        </label>
        <select
          id="holding-type"
          :value="formData.asset_type"
          class="input-field"
          required
          @change="handleAssetTypeChange"
        >
          <option
            v-for="opt in assetTypeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
      <div class="space-y-1.5">
        <label for="holding-currency" class="label-text">Currency</label>
        <select
          id="holding-currency"
          :value="formData.currency"
          class="input-field"
          @change="handleCurrencyChange"
        >
          <option
            v-for="c in currencyOptions"
            :key="c"
            :value="c"
          >
            {{ c }}
          </option>
        </select>
      </div>
    </div>

    <!-- Quantity + Purchase Date -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="holding-qty" class="label-text">
          Quantity <span class="text-debit">*</span>
        </label>
        <input
          id="holding-qty"
          v-model="formData.quantity"
          type="number"
          step="0.0001"
          min="0"
          class="input-field"
          placeholder="e.g. 10.5"
          required
        />
      </div>
      <div class="space-y-1.5">
        <label for="holding-date" class="label-text">Purchase Date</label>
        <input
          id="holding-date"
          v-model="formData.purchase_date"
          type="date"
          class="input-field"
        />
      </div>
    </div>

    <!-- Cost Basis + Current Price -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label class="label-text">
          Cost Basis <span class="text-debit">*</span>
        </label>
        <CurrencyInput
          :amount="String(formData.cost_basis ?? '')"
          :currency="formData.currency"
          :show-currency-select="false"
          placeholder="0.00"
          @update="handleCostBasisUpdate"
        />
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
          Total amount invested in this holding
        </p>
      </div>
      <div class="space-y-1.5">
        <label class="label-text">Current Price</label>
        <CurrencyInput
          :amount="String(formData.current_price ?? '')"
          :show-currency-select="false"
          placeholder="0.00"
          @update="handleCurrentPriceUpdate"
        />
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
          Price per unit; auto-calculates current value
        </p>
      </div>
    </div>

    <!-- Current Value (auto-calculated, but editable) -->
    <div class="space-y-1.5">
      <label class="label-text">Current Value</label>
      <CurrencyInput
        :amount="String(formData.current_value ?? '')"
        :show-currency-select="false"
        placeholder="Auto-calculated from qty × price"
        @update="handleCurrentValueUpdate"
      />
      <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Auto-calculated from quantity × current price, but you can override it
      </p>
    </div>

    <!-- Form Actions -->
    <div class="flex items-center justify-end gap-3 pt-4 border-t border-navy-100 dark:border-navy-800">
      <button
        type="button"
        class="btn-secondary"
        :disabled="saving"
        @click="handleCancel"
      >
        Cancel
      </button>
      <button
        type="button"
        class="btn-primary"
        :disabled="saving"
        @click="handleSubmit"
      >
        <svg
          v-if="saving"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ isEdit ? "Update Holding" : "Add Holding" }}
      </button>
    </div>
  </form>
</template>
