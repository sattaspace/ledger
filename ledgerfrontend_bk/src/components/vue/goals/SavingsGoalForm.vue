<script setup lang="ts">
/**
 * SavingsGoalForm — Create/edit form for SavingsGoal entities.
 *
 * Fields:
 *   name (text, required), target_amount (CurrencyInput, required),
 *   current_amount (CurrencyInput, optional), currency (from CurrencyInput),
 *   deadline (date, optional), account_id (dropdown from accountStore),
 *   icon (text, optional), color (text/color picker, optional)
 *
 * On create: current_amount defaults to "0"
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
import { useSavingsGoalStore } from "@/stores/savingsGoal";
import { useAccountStore } from "@/stores/account";
import type {
  SavingsGoalOut,
  SavingsGoalCreate,
  SavingsGoalUpdate,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "SavingsGoalForm" });

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
  saved: [item: SavingsGoalOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const goalStore = useSavingsGoalStore();
const accountStore = useAccountStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await dropdownLoader.loadDropdown("accounts", accountStore);
});

// ─── Dropdown Data ───────────────────────────────────────────────────────────

const accountDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("accounts"),
);

// ─── Icon Options ────────────────────────────────────────────────────────────

const iconOptions = [
  { label: "None", value: "" },
  { label: "🏠 House", value: "🏠" },
  { label: "🚗 Car", value: "🚗" },
  { label: "✈️ Travel", value: "✈️" },
  { label: "🎓 Education", value: "🎓" },
  { label: "💍 Wedding", value: "💍" },
  { label: "👶 Baby", value: "👶" },
  { label: "🏥 Medical", value: "🏥" },
  { label: "💰 Emergency", value: "💰" },
  { label: "📱 Gadget", value: "📱" },
  { label: "🎮 Gaming", value: "🎮" },
  { label: "🎯 Goal", value: "🎯" },
  { label: "🏖️ Vacation", value: "🏖️" },
  { label: "🎁 Gift", value: "🎁" },
  { label: "📊 Investment", value: "📊" },
  { label: "🔨 Renovation", value: "🔨" },
];

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<SavingsGoalOut, SavingsGoalCreate, SavingsGoalUpdate>({
  store: goalStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      name: entity.name ?? "",
      target_amount: entity.target_amount ?? "",
      current_amount: entity.current_amount ?? "0",
      currency: entity.currency ?? "USD",
      deadline: entity.deadline ?? "",
      account_id: entity.account_id ?? "",
      icon: entity.icon ?? "",
      color: entity.color ?? "",
    };
  },
  buildCreatePayload(formData) {
    return {
      name: String(formData.name),
      target_amount: String(formData.target_amount),
      current_amount: formData.current_amount ? String(formData.current_amount) : "0",
      currency: formData.currency ? String(formData.currency) : undefined,
      deadline: formData.deadline ? String(formData.deadline) : null,
      account_id: formData.account_id ? Number(formData.account_id) : null,
      icon: formData.icon ? String(formData.icon) : null,
      color: formData.color ? String(formData.color) : null,
    } as SavingsGoalCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("name" in diff) diff.name = diff.name ? String(diff.name) : null;
    if ("target_amount" in diff) diff.target_amount = diff.target_amount ? String(diff.target_amount) : null;
    if ("current_amount" in diff) diff.current_amount = diff.current_amount ? String(diff.current_amount) : null;
    if ("currency" in diff) diff.currency = diff.currency ? String(diff.currency) : null;
    if ("deadline" in diff) diff.deadline = diff.deadline ? String(diff.deadline) : null;
    if ("account_id" in diff) diff.account_id = diff.account_id ? Number(diff.account_id) : null;
    if ("icon" in diff) diff.icon = diff.icon ? String(diff.icon) : null;
    if ("color" in diff) diff.color = diff.color ? String(diff.color) : null;
    return diff as SavingsGoalUpdate;
  },
  onSuccess(item) {
    emit("saved", item);
  },
});

// Load entity data in edit mode
onMounted(() => {
  if (props.mode === "edit" && props.itemId) {
    form.load();
  } else if (props.mode === "create") {
    // Set default current_amount to "0"
    form.setFieldValue("current_amount", "0");
  }
});

// ─── CurrencyInput Handlers ─────────────────────────────────────────────────

function handleTargetAmountUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("target_amount", data.amount);
  form.setFieldValue("currency", data.currency);
}

function handleCurrentAmountUpdate(data: { amount: string }) {
  form.setFieldValue("current_amount", data.amount);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isEdit = computed(() => props.mode === "edit");

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}

function handleIconChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  form.setFieldValue("icon", value);
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

    <!-- Name -->
    <div class="space-y-1.5">
      <label for="goal-name" class="label-text">
        Goal Name <span class="text-debit">*</span>
      </label>
      <input
        id="goal-name"
        v-model="form.data.name"
        type="text"
        class="input-field"
        placeholder="e.g. Emergency Fund, Vacation Fund"
        required
      />
    </div>

    <!-- Target Amount -->
    <div class="space-y-1.5">
      <label class="label-text">
        Target Amount <span class="text-debit">*</span>
      </label>
      <CurrencyInput
        :amount="String(form.data.target_amount ?? '')"
        :currency="String(form.data.currency ?? 'USD')"
        :show-currency-select="true"
        placeholder="0.00"
        @update="handleTargetAmountUpdate"
      />
    </div>

    <!-- Current Amount -->
    <div class="space-y-1.5">
      <label class="label-text">Current Amount</label>
      <CurrencyInput
        :amount="String(form.data.current_amount ?? '0')"
        :show-currency-select="false"
        placeholder="0.00"
        @update="handleCurrentAmountUpdate"
      />
      <p v-if="!isEdit" class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Defaults to $0 for new goals
      </p>
    </div>

    <!-- Deadline -->
    <div class="space-y-1.5">
      <label for="goal-deadline" class="label-text">Deadline</label>
      <input
        id="goal-deadline"
        v-model="form.data.deadline"
        type="date"
        class="input-field"
      />
      <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Optional — set a target date to track progress
      </p>
    </div>

    <!-- Account -->
    <div class="space-y-1.5">
      <label for="goal-account" class="label-text">Linked Account</label>
      <select
        id="goal-account"
        v-model="form.data.account_id"
        class="input-field"
      >
        <option value="">None</option>
        <option
          v-for="acct in accountDropdown"
          :key="acct.id"
          :value="acct.id"
        >
          {{ acct.name }}
        </option>
      </select>
      <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Link to an account to track contributions
      </p>
    </div>

    <!-- Icon + Color -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="space-y-1.5">
        <label for="goal-icon" class="label-text">Icon</label>
        <select
          id="goal-icon"
          :value="form.data.icon ?? ''"
          class="input-field"
          @change="handleIconChange"
        >
          <option
            v-for="opt in iconOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </option>
        </select>
      </div>
      <div class="space-y-1.5">
        <label for="goal-color" class="label-text">Color</label>
        <div class="flex items-center gap-2">
          <input
            type="color"
            :value="form.data.color ?? '#0e7490'"
            class="h-10 w-10 rounded-lg border border-navy-200 dark:border-navy-700 cursor-pointer"
            @input="form.setFieldValue('color', ($event.target as HTMLInputElement).value)"
          />
          <input
            id="goal-color"
            :value="form.data.color ?? ''"
            type="text"
            class="input-field flex-1"
            placeholder="#0e7490"
            @input="form.setFieldValue('color', ($event.target as HTMLInputElement).value)"
          />
        </div>
      </div>
    </div>

    <!-- Footer Buttons -->
    <div class="flex items-center justify-end gap-3 pt-3 border-t border-navy-100 dark:border-navy-800">
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
        {{ mode === "create" ? "Create Goal" : "Update Goal" }}
      </button>
    </div>
  </form>
</template>
