<script setup lang="ts">
/**
 * InvestmentForm — Create/edit form for InvestmentAccount entities.
 *
 * Fields:
 *   account_id (dropdown — only INVESTMENT type accounts),
 *   portfolio_value, cost_basis_total
 *
 * Holdings are managed on the detail page.
 *
 * Uses useCrudForm composable for lifecycle management.
 * Emits 'saved' on successful create/update.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useInvestmentStore } from "@/stores/investment";
import { useAccountStore } from "@/stores/account";
import type {
  InvestmentAccountOut,
  InvestmentAccountCreate,
  InvestmentAccountUpdate,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "InvestmentForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Form mode: create or edit. */
    mode: "create" | "edit";
    /** Entity ID for edit mode. */
    itemId?: number;
  }>(),
  {
    itemId: undefined,
  },
);

const emit = defineEmits<{
  saved: [item: InvestmentAccountOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const investmentStore = useInvestmentStore();
const accountStore = useAccountStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await dropdownLoader.loadDropdown("accounts", accountStore);
});

// ─── Investment-Type Accounts Only ───────────────────────────────────────────

const investmentAccounts = computed(() => {
  const all = dropdownLoader.getDropdown<{ id: number; name: string; account_type?: string }>("accounts");
  // Filter to INVESTMENT type accounts only (or show all if account_type not available in dropdown)
  return all.filter((a) => {
    // The dropdown may or may not include account_type
    // If it does, filter; if not, show all
    if ("account_type" in a && a.account_type) {
      return a.account_type === "INVESTMENT";
    }
    return true;
  });
});

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<InvestmentAccountOut, InvestmentAccountCreate, InvestmentAccountUpdate>({
  store: investmentStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      account_id: entity.account_id ?? "",
      portfolio_value: entity.portfolio_value ?? "",
      cost_basis_total: entity.cost_basis_total ?? "",
    };
  },
  buildCreatePayload(formData) {
    return {
      account_id: Number(formData.account_id),
      portfolio_value: formData.portfolio_value ? String(formData.portfolio_value) : undefined,
      cost_basis_total: formData.cost_basis_total ? String(formData.cost_basis_total) : undefined,
    } as InvestmentAccountCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("portfolio_value" in diff) diff.portfolio_value = diff.portfolio_value ? String(diff.portfolio_value) : null;
    if ("cost_basis_total" in diff) diff.cost_basis_total = diff.cost_basis_total ? String(diff.cost_basis_total) : null;
    return diff as InvestmentAccountUpdate;
  },
  onSuccess(item) {
    emit("saved", item);
  },
});

// Load entity data in edit mode
onMounted(() => {
  if (props.mode === "edit" && props.itemId) {
    form.load();
  }
});

// ─── Currency Input Handlers ─────────────────────────────────────────────────

function handlePortfolioValueUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("portfolio_value", data.amount);
}

function handleCostBasisUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("cost_basis_total", data.amount);
}

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

    <!-- Account Selection -->
    <div class="space-y-1.5">
      <label for="inv-account" class="label-text">
        Investment Account <span class="text-debit">*</span>
      </label>
      <select
        id="inv-account"
        v-model="form.data.account_id"
        class="input-field"
        :disabled="mode === 'edit'"
        required
      >
        <option value="">Select an account...</option>
        <option
          v-for="acct in investmentAccounts"
          :key="acct.id"
          :value="acct.id"
        >
          {{ acct.name }}
        </option>
      </select>
      <p v-if="mode === 'edit'" class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Account cannot be changed after creation
      </p>
      <p v-else class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Only INVESTMENT-type accounts are shown. Create one in Accounts first if needed.
      </p>
    </div>

    <!-- Portfolio Value + Cost Basis -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label class="label-text">Portfolio Value</label>
        <CurrencyInput
          :amount="String(form.data.portfolio_value ?? '')"
          :currency="'USD'"
          :show-currency-select="false"
          placeholder="0.00"
          @update="handlePortfolioValueUpdate"
        />
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
          Current total market value of holdings
        </p>
      </div>
      <div class="space-y-1.5">
        <label class="label-text">Cost Basis Total</label>
        <CurrencyInput
          :amount="String(form.data.cost_basis_total ?? '')"
          :show-currency-select="false"
          placeholder="0.00"
          @update="handleCostBasisUpdate"
        />
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
          Total amount invested (purchase price of all holdings)
        </p>
      </div>
    </div>

    <!-- Form Actions -->
    <div class="flex items-center justify-end gap-3 pt-4 border-t border-navy-100 dark:border-navy-800">
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
        {{ mode === "create" ? "Create Investment Account" : "Update Investment Account" }}
      </button>
    </div>
  </form>
</template>
