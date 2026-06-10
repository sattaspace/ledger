<script setup lang="ts">
/**
 * AccountForm — Create/edit form for Account entities.
 *
 * Used inside a Modal component for both creating and editing
 * accounts. Integrates with useCrudForm for lifecycle
 * management and the account Pinia store for API calls.
 *
 * Usage:
 *   <AccountForm mode="create" @saved="onSaved" @cancel="onCancel" />
 *   <AccountForm mode="edit" :item-id="account.id" @saved="onSaved" @cancel="onCancel" />
 */

import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useAccountStore } from "@/stores/account";
import { useInstitutionStore } from "@/stores/institution";
import { FormErrors } from "@/components/vue";
import type {
  AccountOut,
  AccountCreate,
  AccountUpdate,
  AccountType,
} from "@/lib/ledgerTypes";

// ─── Props & Emits ────────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Form mode: creating a new entity or editing an existing one. */
    mode: "create" | "edit";
    /** Entity ID to load for edit mode. */
    itemId?: number;
  }>(),
  {
    itemId: undefined,
  },
);

const emit = defineEmits<{
  saved: [item: AccountOut];
  cancel: [];
}>();

// ─── Store & Form ─────────────────────────────────────────────────────────────

const store = useAccountStore();
const institutionStore = useInstitutionStore();
const dropdownLoader = useDropdownLoader();

const form = useCrudForm<AccountOut, AccountCreate, AccountUpdate>({
  store,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm: (entity) => ({
    name: entity.name ?? "",
    institution_id: entity.institution_id ?? 0,
    account_type: entity.account_type ?? "ASSET",
    currency: entity.currency ?? "USD",
    current_balance: entity.current_balance ?? "0",
    credit_limit: entity.credit_limit ?? "",
    interest_rate: entity.interest_rate ?? "",
    statement_closing_day: entity.statement_closing_day?.toString() ?? "",
    due_day: entity.due_day?.toString() ?? "",
    icon: entity.icon ?? "",
    color: entity.color ?? "",
    notes: entity.notes ?? "",
    sort_order: entity.sort_order?.toString() ?? "0",
  }),
  buildCreatePayload: (formData) => ({
    name: formData.name as string,
    institution_id: formData.institution_id as number,
    account_type: (formData.account_type as AccountType) || "ASSET",
    currency: (formData.currency as string) || undefined,
    current_balance: (formData.current_balance as string) || "0",
    credit_limit: (formData.credit_limit as string) || null,
    interest_rate: (formData.interest_rate as string) || undefined,
    statement_closing_day: formData.statement_closing_day ? parseInt(formData.statement_closing_day as string, 10) || null : null,
    due_day: formData.due_day ? parseInt(formData.due_day as string, 10) || null : null,
    icon: (formData.icon as string) || null,
    color: (formData.color as string) || null,
    notes: (formData.notes as string) || null,
    sort_order: formData.sort_order ? parseInt(formData.sort_order as string, 10) || 0 : 0,
  }),
  buildUpdatePayload: (formData) => ({
    name: (formData.name as string) || null,
    institution_id: (formData.institution_id as number) || null,
    account_type: (formData.account_type as AccountType) || null,
    currency: (formData.currency as string) || null,
    current_balance: (formData.current_balance as string) || null,
    credit_limit: (formData.credit_limit as string) || null,
    interest_rate: (formData.interest_rate as string) || null,
    statement_closing_day: formData.statement_closing_day ? parseInt(formData.statement_closing_day as string, 10) || null : null,
    due_day: formData.due_day ? parseInt(formData.due_day as string, 10) || null : null,
    icon: (formData.icon as string) || null,
    color: (formData.color as string) || null,
    notes: (formData.notes as string) || null,
    sort_order: formData.sort_order ? parseInt(formData.sort_order as string, 10) || null : null,
  }),
  onSuccess: (item) => {
    emit("saved", item);
  },
});

// ─── Account Type Options ─────────────────────────────────────────────────────

const accountTypeOptions: { label: string; value: AccountType }[] = [
  { label: "Asset", value: "ASSET" },
  { label: "Liability", value: "LIABILITY" },
  { label: "Investment", value: "INVESTMENT" },
];

// ─── Submit Label ─────────────────────────────────────────────────────────────

const submitLabel = form.isEdit ? "Update Account" : "Create Account";

// ─── Load entity for edit mode ────────────────────────────────────────────────

onMounted(async () => {
  // Load institution dropdown for the institution selector
  await dropdownLoader.loadDropdown("institutions", institutionStore);

  if (form.isEdit && props.itemId) {
    await form.load();
  } else {
    // Initialize default values for create mode
    form.setFieldValue("name", "");
    form.setFieldValue("institution_id", "");
    form.setFieldValue("account_type", "ASSET");
    form.setFieldValue("currency", "USD");
    form.setFieldValue("current_balance", "0");
    form.setFieldValue("credit_limit", "");
    form.setFieldValue("interest_rate", "");
    form.setFieldValue("statement_closing_day", "");
    form.setFieldValue("due_day", "");
    form.setFieldValue("icon", "");
    form.setFieldValue("color", "");
    form.setFieldValue("notes", "");
    form.setFieldValue("sort_order", "0");
  }
});

// ─── Handlers ─────────────────────────────────────────────────────────────────

async function handleSubmit(): Promise<void> {
  await form.submit();
}

function handleCancel(): void {
  emit("cancel");
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

    <!-- Name -->
    <div class="space-y-1.5">
      <label for="account-name" class="label-text">
        Account Name <span class="text-debit">*</span>
      </label>
      <input
        id="account-name"
        v-model="form.data.name"
        type="text"
        required
        placeholder="e.g. Chase Checking"
        class="input-field"
        :aria-invalid="!!form.fieldErrors.value?.name"
        :disabled="form.loading.value"
        autocomplete="off"
      />
      <p
        v-if="form.fieldErrors.value?.name"
        class="text-xs text-debit"
        role="alert"
      >
        {{ form.fieldErrors.value.name.join(", ") }}
      </p>
    </div>

    <!-- Institution & Account Type Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- Institution -->
      <div class="space-y-1.5">
        <label for="account-institution" class="label-text">
          Institution <span class="text-debit">*</span>
        </label>
        <select
          id="account-institution"
          v-model="form.data.institution_id"
          required
          class="input-field"
          :disabled="form.loading.value"
        >
          <option value="" disabled>Select an institution</option>
          <option
            v-for="inst in institutionStore.dropdown"
            :key="inst.id"
            :value="inst.id"
          >
            {{ inst.name }}
          </option>
        </select>
        <p
          v-if="form.fieldErrors.value?.institution_id"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.institution_id.join(", ") }}
        </p>
      </div>

      <!-- Account Type -->
      <div class="space-y-1.5">
        <label for="account-type" class="label-text">
          Account Type
        </label>
        <select
          id="account-type"
          v-model="form.data.account_type"
          class="input-field"
          :disabled="form.loading.value"
        >
          <option
            v-for="opt in accountTypeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
        <p
          v-if="form.fieldErrors.value?.account_type"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.account_type.join(", ") }}
        </p>
      </div>
    </div>

    <!-- Currency & Balance Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- Currency -->
      <div class="space-y-1.5">
        <label for="account-currency" class="label-text">
          Currency
        </label>
        <input
          id="account-currency"
          v-model="form.data.currency"
          type="text"
          placeholder="USD"
          class="input-field"
          maxlength="3"
          :aria-invalid="!!form.fieldErrors.value?.currency"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.currency"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.currency.join(", ") }}
        </p>
      </div>

      <!-- Current Balance -->
      <div class="space-y-1.5">
        <label for="account-balance" class="label-text">
          Current Balance
        </label>
        <input
          id="account-balance"
          v-model="form.data.current_balance"
          type="text"
          inputmode="decimal"
          placeholder="0.00"
          class="input-field"
          :aria-invalid="!!form.fieldErrors.value?.current_balance"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.current_balance"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.current_balance.join(", ") }}
        </p>
      </div>
    </div>

    <!-- Credit Limit & Interest Rate Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- Credit Limit (for LIABILITY accounts) -->
      <div class="space-y-1.5">
        <label for="account-credit-limit" class="label-text">
          Credit Limit
        </label>
        <input
          id="account-credit-limit"
          v-model="form.data.credit_limit"
          type="text"
          inputmode="decimal"
          placeholder="e.g. 5000.00"
          class="input-field"
          :aria-invalid="!!form.fieldErrors.value?.credit_limit"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.credit_limit"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.credit_limit.join(", ") }}
        </p>
      </div>

      <!-- Interest Rate -->
      <div class="space-y-1.5">
        <label for="account-interest-rate" class="label-text">
          Interest Rate
        </label>
        <input
          id="account-interest-rate"
          v-model="form.data.interest_rate"
          type="text"
          inputmode="decimal"
          placeholder="e.g. 4.5"
          class="input-field"
          :aria-invalid="!!form.fieldErrors.value?.interest_rate"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.interest_rate"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.interest_rate.join(", ") }}
        </p>
      </div>
    </div>

    <!-- Statement Day & Due Day Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- Statement Closing Day -->
      <div class="space-y-1.5">
        <label for="account-statement-day" class="label-text">
          Statement Closing Day
        </label>
        <input
          id="account-statement-day"
          v-model="form.data.statement_closing_day"
          type="number"
          min="1"
          max="31"
          placeholder="e.g. 15"
          class="input-field"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.statement_closing_day"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.statement_closing_day.join(", ") }}
        </p>
      </div>

      <!-- Due Day -->
      <div class="space-y-1.5">
        <label for="account-due-day" class="label-text">
          Payment Due Day
        </label>
        <input
          id="account-due-day"
          v-model="form.data.due_day"
          type="number"
          min="1"
          max="31"
          placeholder="e.g. 28"
          class="input-field"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.due_day"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.due_day.join(", ") }}
        </p>
      </div>
    </div>

    <!-- Icon & Color Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- Icon -->
      <div class="space-y-1.5">
        <label for="account-icon" class="label-text">
          Icon
        </label>
        <input
          id="account-icon"
          v-model="form.data.icon"
          type="text"
          placeholder="e.g. wallet"
          class="input-field"
          :disabled="form.loading.value"
          autocomplete="off"
        />
        <p
          v-if="form.fieldErrors.value?.icon"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.icon.join(", ") }}
        </p>
      </div>

      <!-- Color -->
      <div class="space-y-1.5">
        <label for="account-color" class="label-text">
          Color
        </label>
        <div class="flex items-center gap-2">
          <input
            v-model="form.data.color"
            type="color"
            class="h-10 w-10 cursor-pointer rounded-lg border border-navy-200 dark:border-navy-700 p-0.5"
            :disabled="form.loading.value"
          />
          <input
            id="account-color"
            v-model="form.data.color"
            type="text"
            placeholder="#00B4E6"
            class="input-field flex-1"
            :disabled="form.loading.value"
            autocomplete="off"
          />
        </div>
        <p
          v-if="form.fieldErrors.value?.color"
          class="text-xs text-debit"
          role="alert"
        >
          {{ form.fieldErrors.value.color.join(", ") }}
        </p>
      </div>
    </div>

    <!-- Sort Order -->
    <div class="space-y-1.5">
      <label for="account-sort-order" class="label-text">
        Sort Order
      </label>
      <input
        id="account-sort-order"
        v-model="form.data.sort_order"
        type="number"
        min="0"
        placeholder="0"
        class="input-field max-w-[120px]"
        :disabled="form.loading.value"
        autocomplete="off"
      />
    </div>

    <!-- Notes -->
    <div class="space-y-1.5">
      <label for="account-notes" class="label-text">
        Notes
      </label>
      <textarea
        id="account-notes"
        v-model="form.data.notes"
        rows="3"
        placeholder="Optional notes about this account..."
        class="input-field resize-y"
        :disabled="form.loading.value"
      />
      <p
        v-if="form.fieldErrors.value?.notes"
        class="text-xs text-debit"
        role="alert"
      >
        {{ form.fieldErrors.value.notes.join(", ") }}
      </p>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3 pt-2">
      <button
        type="button"
        class="btn-secondary"
        :disabled="form.loading.value"
        @click="handleCancel"
      >
        Cancel
      </button>
      <button
        type="submit"
        class="btn-primary"
        :disabled="form.loading.value"
      >
        <!-- Loading Spinner -->
        <svg
          v-if="form.loading.value"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ form.loading.value ? "Saving..." : submitLabel }}
      </button>
    </div>
  </form>
</template>
