<script setup lang="ts">
/**
 * BudgetForm — Create/edit form for Budget entities.
 *
 * Fields:
 *   category_id, amount, currency, period, start_date, allow_rollover, is_active
 *
 * Uses useCrudForm composable for lifecycle management.
 * Uses CategoryTreeSelect for hierarchical category picking.
 * Uses CurrencyInput for amount + currency entry.
 *
 * Emits 'saved' on successful create/update.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  FormErrors,
  CurrencyInput,
  CategoryTreeSelect,
} from "@/components/vue";
import type { TreeNode } from "@/components/vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useBudgetStore } from "@/stores/budget";
import { useCategoryStore } from "@/stores/category";
import type { BudgetOut, BudgetCreate, BudgetUpdate, BudgetPeriod } from "@/lib/ledgerTypes";

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
  saved: [item: BudgetOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const budgetStore = useBudgetStore();
const categoryStore = useCategoryStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await dropdownLoader.loadDropdown("categories", categoryStore);
  await categoryStore.fetchTree();
});

// ─── Period Options ──────────────────────────────────────────────────────────

const periodOptions: { label: string; value: BudgetPeriod }[] = [
  { label: "Weekly", value: "WEEKLY" },
  { label: "Monthly", value: "MONTHLY" },
  { label: "Yearly", value: "YEARLY" },
];

// ─── Default Start Date ─────────────────────────────────────────────────────

function getDefaultStartDate(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

// ─── Category Tree ───────────────────────────────────────────────────────────

const categoryTree = computed<TreeNode[]>(() => {
  return categoryStore.tree as unknown as TreeNode[];
});

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<BudgetOut, BudgetCreate, BudgetUpdate>({
  store: budgetStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      category_id: entity.category_id ?? "",
      amount: entity.amount ?? "0",
      currency: entity.currency ?? "USD",
      period: entity.period ?? "MONTHLY",
      start_date: entity.start_date ?? getDefaultStartDate(),
      allow_rollover: entity.allow_rollover ?? false,
      is_active: entity.is_active ?? true,
    };
  },
  buildCreatePayload(formData) {
    return {
      category_id: Number(formData.category_id),
      amount: String(formData.amount || "0"),
      currency: String(formData.currency || "USD"),
      period: formData.period as BudgetPeriod,
      start_date: String(formData.start_date),
      allow_rollover: formData.allow_rollover === true,
    } as BudgetCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("category_id" in diff) diff.category_id = Number(diff.category_id);
    if ("amount" in diff) diff.amount = String(diff.amount);
    if ("period" in diff) diff.period = diff.period as BudgetPeriod;
    if ("start_date" in diff) diff.start_date = String(diff.start_date);
    if ("allow_rollover" in diff) diff.allow_rollover = diff.allow_rollover === true;
    if ("is_active" in diff) diff.is_active = diff.is_active === true;
    return diff as BudgetUpdate;
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

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}

function handleCategorySelect(node: TreeNode) {
  form.setFieldValue("category_id", node.id);
}

function handleCurrencyUpdate(value: { amount: string; currency: string }) {
  form.setFieldValue("amount", value.amount);
  form.setFieldValue("currency", value.currency);
}

function handlePeriodChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as BudgetPeriod;
  form.setFieldValue("period", value);
}

function handleRolloverToggle() {
  form.setFieldValue("allow_rollover", !form.data.allow_rollover);
}

function handleActiveToggle() {
  form.setFieldValue("is_active", !form.data.is_active);
}
</script>

<template>
  <Modal
    :open="open"
    :title="mode === 'create' ? 'Add Budget' : 'Edit Budget'"
    size="lg"
    @close="handleCancel"
  >
    <template #body>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Form Errors -->
        <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

        <!-- Category -->
        <div class="space-y-1.5">
          <label for="budget-category" class="label-text">
            Category <span class="text-debit">*</span>
          </label>
          <CategoryTreeSelect
            :categories="categoryTree"
            :model-value="(form.data.category_id as number | null) ?? null"
            placeholder="Select a category..."
            @update:model-value="(id: number | null) => form.setFieldValue('category_id', id ?? '')"
            @select="handleCategorySelect"
          />
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
            One budget per category per period
          </p>
        </div>

        <!-- Amount (CurrencyInput) -->
        <div class="space-y-1.5">
          <label for="budget-amount" class="label-text">
            Budget Amount <span class="text-debit">*</span>
          </label>
          <CurrencyInput
            :amount="String(form.data.amount ?? '')"
            :currency="String(form.data.currency ?? 'USD')"
            :show-currency-select="true"
            placeholder="0.00"
            @update="handleCurrencyUpdate"
          />
        </div>

        <!-- Period -->
        <div class="space-y-1.5">
          <label for="budget-period" class="label-text">Period</label>
          <select
            id="budget-period"
            :value="form.data.period ?? 'MONTHLY'"
            class="input-field"
            @change="handlePeriodChange"
          >
            <option
              v-for="opt in periodOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- Start Date -->
        <div class="space-y-1.5">
          <label for="budget-start-date" class="label-text">
            Start Date <span class="text-debit">*</span>
          </label>
          <input
            id="budget-start-date"
            type="date"
            :value="form.data.start_date ?? getDefaultStartDate()"
            class="input-field"
            required
            @input="form.setFieldValue('start_date', ($event.target as HTMLInputElement).value)"
          />
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
            Budget tracking begins from this date
          </p>
        </div>

        <!-- Allow Rollover Toggle -->
        <div class="flex items-start gap-3 py-2">
          <button
            type="button"
            role="switch"
            :aria-checked="!!form.data.allow_rollover"
            :class="[
              'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring',
              form.data.allow_rollover
                ? 'bg-cyan-600 dark:bg-cyan-500'
                : 'bg-navy-200 dark:bg-navy-700',
            ]"
            @click="handleRolloverToggle"
          >
            <span
              :class="[
                'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                form.data.allow_rollover ? 'translate-x-5' : 'translate-x-0',
              ]"
            />
          </button>
          <div class="flex flex-col">
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
              Allow Rollover
            </span>
            <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
              Allow unused budget to roll over to next period
            </span>
          </div>
        </div>

        <!-- Active Status Toggle (edit mode only) -->
        <div v-if="mode === 'edit'" class="flex items-start gap-3 py-2">
          <button
            type="button"
            role="switch"
            :aria-checked="!!form.data.is_active"
            :class="[
              'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring',
              form.data.is_active
                ? 'bg-cyan-600 dark:bg-cyan-500'
                : 'bg-navy-200 dark:bg-navy-700',
            ]"
            @click="handleActiveToggle"
          >
            <span
              :class="[
                'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                form.data.is_active ? 'translate-x-5' : 'translate-x-0',
              ]"
            />
          </button>
          <div class="flex flex-col">
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
              Active
            </span>
            <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
              Deactivate this budget to pause tracking
            </span>
          </div>
        </div>
      </form>
    </template>

    <template #footer>
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
        {{ mode === "create" ? "Create Budget" : "Update Budget" }}
      </button>
    </template>
  </Modal>
</template>
