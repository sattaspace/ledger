<script setup lang="ts">
/**
 * DebtForm — Create/edit form for DebtFacility entities.
 *
 * Fields:
 *   name, debt_nature (toggle: I Owe / They Owe Me), debt_type,
 *   entity_name, institution_id (optional dropdown), principal_amount,
 *   remaining_balance, currency, interest_rate, start_date, end_date,
 *   term_months, monthly_payment, payment_day, account_id (dropdown), notes
 *
 * Auto-calculate: when principal_amount changes, set remaining_balance = principal_amount (on create)
 *
 * Uses useCrudForm composable for lifecycle management.
 * Emits 'saved' on successful create/update.
 */

import {
  Modal,
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useDebtStore } from "@/stores/debt";
import { useAccountStore } from "@/stores/account";
import { useInstitutionStore } from "@/stores/institution";
import type {
  DebtFacilityOut,
  DebtFacilityCreate,
  DebtFacilityUpdate,
  DebtNature,
  DebtType,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "DebtForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Form mode: create or edit. */
    mode: "create" | "edit";
    /** Entity ID for edit mode. */
    itemId?: number;
    /** Whether the modal is open (parent controls visibility). */
    open?: boolean;
    /** Default debt_nature based on active tab. */
    defaultNature?: DebtNature;
  }>(),
  {
    itemId: undefined,
    open: false,
    defaultNature: "MONEY_BORROWED",
  },
);

const emit = defineEmits<{
  saved: [item: DebtFacilityOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const debtStore = useDebtStore();
const accountStore = useAccountStore();
const institutionStore = useInstitutionStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await Promise.all([
    dropdownLoader.loadDropdown("accounts", accountStore),
    dropdownLoader.loadDropdown("institutions", institutionStore),
  ]);
});

// ─── Dropdown Data ───────────────────────────────────────────────────────────

const accountDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("accounts"),
);

const institutionDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("institutions"),
);

// ─── Debt Type Options ───────────────────────────────────────────────────────

const debtTypeOptions: { label: string; value: DebtType }[] = [
  { label: "Mortgage", value: "MORTGAGE" },
  { label: "Personal", value: "PERSONAL" },
  { label: "Student", value: "STUDENT" },
  { label: "Auto", value: "AUTO" },
  { label: "Business", value: "BUSINESS" },
  { label: "Informal", value: "INFORMAL" },
];

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<DebtFacilityOut, DebtFacilityCreate, DebtFacilityUpdate>({
  store: debtStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      name: entity.name ?? "",
      debt_nature: entity.debt_nature ?? props.defaultNature,
      debt_type: entity.debt_type ?? "PERSONAL",
      entity_name: entity.entity_name ?? "",
      institution_id: entity.institution_id ?? "",
      principal_amount: entity.principal_amount ?? "",
      remaining_balance: entity.remaining_balance ?? "",
      currency: entity.currency ?? "USD",
      interest_rate: entity.interest_rate ?? "0",
      start_date: entity.start_date ?? "",
      end_date: entity.end_date ?? "",
      term_months: entity.term_months ?? "",
      monthly_payment: entity.monthly_payment ?? "",
      payment_day: entity.payment_day ?? "",
      account_id: entity.account_id ?? "",
      notes: entity.notes ?? "",
    };
  },
  buildCreatePayload(formData) {
    return {
      name: String(formData.name),
      debt_nature: formData.debt_nature as DebtNature,
      debt_type: formData.debt_type as DebtType,
      entity_name: String(formData.entity_name),
      institution_id: formData.institution_id ? Number(formData.institution_id) : null,
      principal_amount: String(formData.principal_amount),
      remaining_balance: formData.remaining_balance
        ? String(formData.remaining_balance)
        : String(formData.principal_amount),
      currency: formData.currency ? String(formData.currency) : undefined,
      interest_rate: formData.interest_rate ? String(formData.interest_rate) : "0",
      start_date: String(formData.start_date),
      end_date: formData.end_date ? String(formData.end_date) : null,
      term_months: formData.term_months ? Number(formData.term_months) : null,
      monthly_payment: formData.monthly_payment ? String(formData.monthly_payment) : "0",
      payment_day: formData.payment_day ? Number(formData.payment_day) : null,
      account_id: formData.account_id ? Number(formData.account_id) : null,
      notes: formData.notes ? String(formData.notes) : null,
    } as DebtFacilityCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("debt_nature" in diff) diff.debt_nature = diff.debt_nature as DebtNature;
    if ("debt_type" in diff) diff.debt_type = diff.debt_type as DebtType;
    if ("institution_id" in diff) diff.institution_id = diff.institution_id ? Number(diff.institution_id) : null;
    if ("principal_amount" in diff) diff.principal_amount = diff.principal_amount ? String(diff.principal_amount) : null;
    if ("remaining_balance" in diff) diff.remaining_balance = diff.remaining_balance ? String(diff.remaining_balance) : null;
    if ("interest_rate" in diff) diff.interest_rate = diff.interest_rate ? String(diff.interest_rate) : null;
    if ("start_date" in diff) diff.start_date = diff.start_date ? String(diff.start_date) : null;
    if ("end_date" in diff) diff.end_date = diff.end_date ? String(diff.end_date) : null;
    if ("term_months" in diff) diff.term_months = diff.term_months ? Number(diff.term_months) : null;
    if ("monthly_payment" in diff) diff.monthly_payment = diff.monthly_payment ? String(diff.monthly_payment) : null;
    if ("payment_day" in diff) diff.payment_day = diff.payment_day ? Number(diff.payment_day) : null;
    if ("account_id" in diff) diff.account_id = diff.account_id ? Number(diff.account_id) : null;
    if ("notes" in diff) diff.notes = diff.notes ? String(diff.notes) : null;
    return diff as DebtFacilityUpdate;
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
    // Set default nature from tab
    form.setFieldValue("debt_nature", props.defaultNature);
  }
});

// ─── Auto-calculate remaining_balance on principal change (create mode) ──────

function handlePrincipalUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("principal_amount", data.amount);
  form.setFieldValue("currency", data.currency);
  // Auto-set remaining_balance on create
  if (props.mode === "create" && !form.data.remaining_balance) {
    form.setFieldValue("remaining_balance", data.amount);
  }
}

function handleRemainingBalanceUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("remaining_balance", data.amount);
}

function handleMonthlyPaymentUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("monthly_payment", data.amount);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isEdit = computed(() => props.mode === "edit");
const isBorrowed = computed(() => form.data.debt_nature === "MONEY_BORROWED");

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}

function toggleDebtNature() {
  const newNature: DebtNature = form.data.debt_nature === "MONEY_BORROWED" ? "MONEY_LENT" : "MONEY_BORROWED";
  form.setFieldValue("debt_nature", newNature);
}

function handleDebtTypeChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as DebtType;
  form.setFieldValue("debt_type", value);
}
</script>

<template>
  <Modal
    :open="open"
    :title="mode === 'create' ? 'Add Debt' : 'Edit Debt'"
    size="lg"
    @close="handleCancel"
  >
    <template #body>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Form Errors -->
        <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

        <!-- Debt Nature Toggle -->
        <div class="space-y-1.5">
          <label class="label-text">Who owes whom?</label>
          <div class="flex rounded-lg border border-navy-200 dark:border-navy-700 overflow-hidden">
            <button
              type="button"
              :class="[
                'flex-1 px-4 py-2.5 text-sm font-medium transition-colors',
                isBorrowed
                  ? 'bg-red-50 dark:bg-red-950/30 text-red-700 dark:text-red-400 border-b-2 border-red-500'
                  : 'text-slate-custom-600 dark:text-slate-custom-400 hover:bg-navy-50 dark:hover:bg-navy-800',
              ]"
              @click="form.setFieldValue('debt_nature', 'MONEY_BORROWED')"
            >
              I Owe Someone
            </button>
            <button
              type="button"
              :class="[
                'flex-1 px-4 py-2.5 text-sm font-medium transition-colors',
                !isBorrowed
                  ? 'bg-green-50 dark:bg-green-950/30 text-green-700 dark:text-green-400 border-b-2 border-green-500'
                  : 'text-slate-custom-600 dark:text-slate-custom-400 hover:bg-navy-50 dark:hover:bg-navy-800',
              ]"
              @click="form.setFieldValue('debt_nature', 'MONEY_LENT')"
            >
              Someone Owes Me
            </button>
          </div>
        </div>

        <!-- Name + Entity Name -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="debt-name" class="label-text">
              Debt Name <span class="text-debit">*</span>
            </label>
            <input
              id="debt-name"
              v-model="form.data.name"
              type="text"
              class="input-field"
              placeholder="e.g. Home Mortgage, Student Loan"
              required
            />
          </div>
          <div class="space-y-1.5">
            <label for="debt-entity" class="label-text">
              {{ isBorrowed ? 'Lender' : 'Borrower' }} <span class="text-debit">*</span>
            </label>
            <input
              id="debt-entity"
              v-model="form.data.entity_name"
              type="text"
              class="input-field"
              :placeholder="isBorrowed ? 'e.g. Chase Bank, Mom' : 'e.g. John, Sarah'"
              required
            />
          </div>
        </div>

        <!-- Debt Type + Institution -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="debt-type" class="label-text">
              Debt Type <span class="text-debit">*</span>
            </label>
            <select
              id="debt-type"
              :value="form.data.debt_type"
              class="input-field"
              required
              @change="handleDebtTypeChange"
            >
              <option
                v-for="opt in debtTypeOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="space-y-1.5">
            <label for="debt-institution" class="label-text">Institution</label>
            <select
              id="debt-institution"
              v-model="form.data.institution_id"
              class="input-field"
            >
              <option value="">None</option>
              <option
                v-for="inst in institutionDropdown"
                :key="inst.id"
                :value="inst.id"
              >
                {{ inst.name }}
              </option>
            </select>
          </div>
        </div>

        <!-- Principal Amount + Remaining Balance -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="label-text">
              Principal Amount <span class="text-debit">*</span>
            </label>
            <CurrencyInput
              :amount="String(form.data.principal_amount ?? '')"
              :currency="String(form.data.currency ?? 'USD')"
              :show-currency-select="true"
              placeholder="0.00"
              @update="handlePrincipalUpdate"
            />
          </div>
          <div class="space-y-1.5">
            <label class="label-text">Remaining Balance</label>
            <CurrencyInput
              :amount="String(form.data.remaining_balance ?? '')"
              :show-currency-select="false"
              placeholder="Auto-filled from principal"
              @update="handleRemainingBalanceUpdate"
            />
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
              Defaults to principal amount for new debts
            </p>
          </div>
        </div>

        <!-- Interest Rate + Monthly Payment -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="debt-interest" class="label-text">Interest Rate (%)</label>
            <input
              id="debt-interest"
              v-model="form.data.interest_rate"
              type="number"
              step="0.01"
              min="0"
              class="input-field"
              placeholder="0.00"
            />
          </div>
          <div class="space-y-1.5">
            <label class="label-text">Monthly Payment</label>
            <CurrencyInput
              :amount="String(form.data.monthly_payment ?? '')"
              :show-currency-select="false"
              placeholder="0.00"
              @update="handleMonthlyPaymentUpdate"
            />
          </div>
        </div>

        <!-- Start Date + End Date -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="debt-start-date" class="label-text">
              Start Date <span class="text-debit">*</span>
            </label>
            <input
              id="debt-start-date"
              v-model="form.data.start_date"
              type="date"
              class="input-field"
              required
            />
          </div>
          <div class="space-y-1.5">
            <label for="debt-end-date" class="label-text">End Date</label>
            <input
              id="debt-end-date"
              v-model="form.data.end_date"
              type="date"
              class="input-field"
            />
          </div>
        </div>

        <!-- Term Months + Payment Day -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="debt-term" class="label-text">Term (months)</label>
            <input
              id="debt-term"
              v-model.number="form.data.term_months"
              type="number"
              class="input-field"
              min="1"
              placeholder="e.g. 360"
            />
          </div>
          <div class="space-y-1.5">
            <label for="debt-payment-day" class="label-text">Payment Day</label>
            <input
              id="debt-payment-day"
              v-model.number="form.data.payment_day"
              type="number"
              class="input-field"
              min="1"
              max="31"
              placeholder="e.g. 15"
            />
          </div>
        </div>

        <!-- Account -->
        <div class="space-y-1.5">
          <label for="debt-account" class="label-text">Linked Account</label>
          <select
            id="debt-account"
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
        </div>

        <!-- Notes -->
        <div class="space-y-1.5">
          <label for="debt-notes" class="label-text">Notes</label>
          <textarea
            id="debt-notes"
            v-model="form.data.notes"
            class="input-field min-h-[80px] resize-y"
            placeholder="Optional notes about this debt..."
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
        {{ mode === "create" ? "Create Debt" : "Update Debt" }}
      </button>
    </template>
  </Modal>
</template>
