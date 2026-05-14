<script setup lang="ts">
/**
 * BillForm — Create/edit form for Bill entities.
 *
 * Fields:
 *   payee, amount (CurrencyInput), is_amount_fixed, recurrence,
 *   start_date, end_date, next_due_date, account_id, category_id,
 *   status (edit only), remind_me, days_before_reminder, notes
 *
 * Uses useCrudForm composable for lifecycle management.
 * Emits 'saved' on successful create/update.
 */

import {
  Modal,
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import CategoryTreeSelect from "@/components/vue/CategoryTreeSelect.vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useBillStore } from "@/stores/bill";
import { useAccountStore } from "@/stores/account";
import { useCategoryStore } from "@/stores/category";
import type {
  BillOut,
  BillCreate,
  BillUpdate,
  BillRecurrence,
  BillStatus,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "BillForm" });

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
  saved: [item: BillOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const billStore = useBillStore();
const accountStore = useAccountStore();
const categoryStore = useCategoryStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await Promise.all([
    dropdownLoader.loadDropdown("accounts", accountStore),
    dropdownLoader.loadDropdown("categories", categoryStore),
  ]);
});

// ─── Dropdown Data ───────────────────────────────────────────────────────────

const accountDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("accounts"),
);

const categoryTree = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string; is_income?: boolean; color?: string; icon?: string; sort_order?: number; subcategories?: unknown[] }>("categories"),
);

// ─── Recurrence Options ──────────────────────────────────────────────────────

const recurrenceOptions: { label: string; value: BillRecurrence }[] = [
  { label: "Weekly", value: "WEEKLY" },
  { label: "Biweekly", value: "BIWEEKLY" },
  { label: "Monthly", value: "MONTHLY" },
  { label: "Quarterly", value: "QUARTERLY" },
  { label: "Yearly", value: "YEARLY" },
  { label: "One Time", value: "ONE_TIME" },
];

// ─── Status Options (edit mode only) ─────────────────────────────────────────

const statusOptions: { label: string; value: BillStatus }[] = [
  { label: "Active", value: "ACTIVE" },
  { label: "Paused", value: "PAUSED" },
  { label: "Cancelled", value: "CANCELLED" },
];

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<BillOut, BillCreate, BillUpdate>({
  store: billStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      payee: entity.payee ?? "",
      amount: entity.amount ?? "",
      currency: entity.currency ?? "USD",
      is_amount_fixed: entity.is_amount_fixed ?? true,
      recurrence: entity.recurrence ?? "MONTHLY",
      start_date: entity.start_date ?? "",
      end_date: entity.end_date ?? "",
      next_due_date: entity.next_due_date ?? "",
      account_id: entity.account_id ?? "",
      category_id: entity.category_id ?? "",
      status: entity.status ?? "ACTIVE",
      remind_me: entity.remind_me ?? true,
      days_before_reminder: entity.days_before_reminder ?? 3,
      notes: entity.notes ?? "",
    };
  },
  buildCreatePayload(formData) {
    return {
      payee: String(formData.payee),
      amount: String(formData.amount),
      currency: formData.currency ? String(formData.currency) : undefined,
      is_amount_fixed: formData.is_amount_fixed === true,
      recurrence: formData.recurrence as BillRecurrence,
      start_date: String(formData.start_date),
      end_date: formData.end_date ? String(formData.end_date) : null,
      next_due_date: String(formData.next_due_date || formData.start_date),
      account_id: formData.account_id ? Number(formData.account_id) : null,
      category_id: formData.category_id ? Number(formData.category_id) : null,
      status: formData.status as BillStatus | undefined,
      remind_me: formData.remind_me === true,
      days_before_reminder: formData.days_before_reminder ? Number(formData.days_before_reminder) : 3,
      notes: formData.notes ? String(formData.notes) : null,
    } as BillCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("amount" in diff) diff.amount = String(diff.amount);
    if ("is_amount_fixed" in diff) diff.is_amount_fixed = diff.is_amount_fixed === true;
    if ("recurrence" in diff) diff.recurrence = diff.recurrence as BillRecurrence;
    if ("start_date" in diff) diff.start_date = String(diff.start_date);
    if ("end_date" in diff) diff.end_date = diff.end_date ? String(diff.end_date) : null;
    if ("next_due_date" in diff) diff.next_due_date = String(diff.next_due_date);
    if ("account_id" in diff) diff.account_id = diff.account_id ? Number(diff.account_id) : null;
    if ("category_id" in diff) diff.category_id = diff.category_id ? Number(diff.category_id) : null;
    if ("status" in diff) diff.status = diff.status as BillStatus;
    if ("remind_me" in diff) diff.remind_me = diff.remind_me === true;
    if ("days_before_reminder" in diff) diff.days_before_reminder = diff.days_before_reminder ? Number(diff.days_before_reminder) : null;
    if ("notes" in diff) diff.notes = diff.notes ? String(diff.notes) : null;
    return diff as BillUpdate;
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

// ─── Computed ────────────────────────────────────────────────────────────────

const isEdit = computed(() => props.mode === "edit");
const showReminderFields = computed(() => form.data.remind_me === true);

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}

function handleRecurrenceChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as BillRecurrence;
  form.setFieldValue("recurrence", value);
}

function handleStatusChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as BillStatus;
  form.setFieldValue("status", value);
}

function handleCurrencyUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("amount", data.amount);
  form.setFieldValue("currency", data.currency);
}

function handleCategorySelect(id: number | null) {
  form.setFieldValue("category_id", id ?? "");
}

function handleStartDateChange(event: Event) {
  const value = (event.target as HTMLInputElement).value;
  form.setFieldValue("start_date", value);
  // Default next_due_date to start_date if not set
  if (!form.data.next_due_date && value) {
    form.setFieldValue("next_due_date", value);
  }
}

function toggleAmountFixed() {
  form.setFieldValue("is_amount_fixed", !form.data.is_amount_fixed);
}

function toggleRemindMe() {
  form.setFieldValue("remind_me", !form.data.remind_me);
}
</script>

<template>
  <Modal
    :open="open"
    :title="mode === 'create' ? 'Add Bill' : 'Edit Bill'"
    size="lg"
    @close="handleCancel"
  >
    <template #body>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Form Errors -->
        <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

        <!-- Payee -->
        <div class="space-y-1.5">
          <label for="bill-payee" class="label-text">
            Payee <span class="text-debit">*</span>
          </label>
          <input
            id="bill-payee"
            v-model="form.data.payee"
            type="text"
            class="input-field"
            placeholder="e.g. Netflix, Landlord, Electric Company"
            required
          />
        </div>

        <!-- Amount + Fixed/Variable -->
        <div class="space-y-1.5">
          <label class="label-text">
            Amount <span class="text-debit">*</span>
          </label>
          <CurrencyInput
            :amount="String(form.data.amount ?? '')"
            :currency="String(form.data.currency ?? 'USD')"
            :show-currency-select="true"
            placeholder="0.00"
            @update="handleCurrencyUpdate"
          />
          <!-- Fixed/Variable Toggle -->
          <div class="flex items-center gap-3 mt-2">
            <button
              type="button"
              :class="[
                'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring',
                form.data.is_amount_fixed ? 'bg-cyan-600' : 'bg-navy-200 dark:bg-navy-700',
              ]"
              role="switch"
              :aria-checked="form.data.is_amount_fixed"
              @click="toggleAmountFixed"
            >
              <span
                :class="[
                  'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                  form.data.is_amount_fixed ? 'translate-x-5' : 'translate-x-0',
                ]"
              />
            </button>
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ form.data.is_amount_fixed ? 'Fixed amount' : 'Variable amount' }}
            </span>
          </div>
          <p
            v-if="!form.data.is_amount_fixed"
            class="text-xs text-amber-600 dark:text-amber-400 mt-1"
          >
            Variable amount: actual payment may differ
          </p>
        </div>

        <!-- Recurrence -->
        <div class="space-y-1.5">
          <label for="bill-recurrence" class="label-text">Recurrence</label>
          <select
            id="bill-recurrence"
            :value="form.data.recurrence"
            class="input-field"
            @change="handleRecurrenceChange"
          >
            <option
              v-for="opt in recurrenceOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- Start Date + End Date -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="bill-start-date" class="label-text">
              Start Date <span class="text-debit">*</span>
            </label>
            <input
              id="bill-start-date"
              :value="form.data.start_date"
              type="date"
              class="input-field"
              required
              @change="handleStartDateChange"
            />
          </div>
          <div class="space-y-1.5">
            <label for="bill-end-date" class="label-text">End Date</label>
            <input
              id="bill-end-date"
              v-model="form.data.end_date"
              type="date"
              class="input-field"
            />
          </div>
        </div>

        <!-- Next Due Date -->
        <div class="space-y-1.5">
          <label for="bill-next-due-date" class="label-text">
            Next Due Date <span class="text-debit">*</span>
          </label>
          <input
            id="bill-next-due-date"
            v-model="form.data.next_due_date"
            type="date"
            class="input-field"
            required
          />
        </div>

        <!-- Account + Category -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="bill-account" class="label-text">Account</label>
            <select
              id="bill-account"
              v-model="form.data.account_id"
              class="input-field"
            >
              <option value="" disabled>Select an account</option>
              <option
                v-for="acct in accountDropdown"
                :key="acct.id"
                :value="acct.id"
              >
                {{ acct.name }}
              </option>
            </select>
          </div>
          <div class="space-y-1.5">
            <label class="label-text">Category</label>
            <CategoryTreeSelect
              :categories="categoryTree"
              :model-value="form.data.category_id ? Number(form.data.category_id) : null"
              placeholder="Select category..."
              @update:model-value="handleCategorySelect"
            />
          </div>
        </div>

        <!-- Status (edit mode only) -->
        <div v-if="isEdit" class="space-y-1.5">
          <label for="bill-status" class="label-text">Status</label>
          <select
            id="bill-status"
            :value="form.data.status"
            class="input-field"
            @change="handleStatusChange"
          >
            <option
              v-for="opt in statusOptions"
              :key="opt.value"
              :value="opt.value"
            >
              {{ opt.label }}
            </option>
          </select>
        </div>

        <!-- Reminder Toggle + Days Before -->
        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <button
              type="button"
              :class="[
                'relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-ring',
                form.data.remind_me ? 'bg-cyan-600' : 'bg-navy-200 dark:bg-navy-700',
              ]"
              role="switch"
              :aria-checked="form.data.remind_me"
              @click="toggleRemindMe"
            >
              <span
                :class="[
                  'pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out',
                  form.data.remind_me ? 'translate-x-5' : 'translate-x-0',
                ]"
              />
            </button>
            <span class="text-sm text-navy-900 dark:text-navy-100">
              Remind me before due date
            </span>
          </div>
          <div v-if="showReminderFields" class="ml-14">
            <label for="bill-days-reminder" class="label-text">Days before reminder</label>
            <input
              id="bill-days-reminder"
              v-model.number="form.data.days_before_reminder"
              type="number"
              class="input-field w-24"
              min="1"
              max="30"
              placeholder="3"
            />
          </div>
        </div>

        <!-- Notes -->
        <div class="space-y-1.5">
          <label for="bill-notes" class="label-text">Notes</label>
          <textarea
            id="bill-notes"
            v-model="form.data.notes"
            class="input-field min-h-[80px] resize-y"
            placeholder="Optional notes about this bill..."
            rows="3"
          />
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
        {{ mode === "create" ? "Create Bill" : "Update Bill" }}
      </button>
    </template>
  </Modal>
</template>
