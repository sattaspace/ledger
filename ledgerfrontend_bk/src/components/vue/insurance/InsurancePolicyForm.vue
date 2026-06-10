<script setup lang="ts">
/**
 * InsurancePolicyForm — Create/edit form for InsurancePolicy entities.
 *
 * Fields:
 *   policy_name (text, required), insurance_type (select), provider (text, required),
 *   institution_id (dropdown, optional), policy_number (text, optional),
 *   premium_amount (CurrencyInput, required), currency, premium_frequency (select),
 *   renewal_date (date, required), coverage_amount (CurrencyInput, optional),
 *   coverage_details (textarea, optional), deductible (CurrencyInput, optional),
 *   remind_renewal (checkbox), days_before_renewal_reminder (number, optional)
 *
 * Uses useCrudForm composable for lifecycle management.
 * Loads institution dropdown via useDropdownLoader.
 * Emits 'saved' on successful create/update.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useInsuranceStore } from "@/stores/insurance";
import { useInstitutionStore } from "@/stores/institution";
import type {
  InsurancePolicyOut,
  InsurancePolicyCreate,
  InsurancePolicyUpdate,
  InsuranceType,
  PremiumFrequency,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "LdgrInsurancePolicyForm" });

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
  saved: [item: InsurancePolicyOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const insuranceStore = useInsuranceStore();
const institutionStore = useInstitutionStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

onMounted(async () => {
  await dropdownLoader.loadDropdown("institutions", institutionStore);
});

// ─── Dropdown Data ───────────────────────────────────────────────────────────

const institutionDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("institutions"),
);

// ─── Insurance Type Options ──────────────────────────────────────────────────

const insuranceTypeOptions: { label: string; value: InsuranceType }[] = [
  { label: "Health", value: "HEALTH" },
  { label: "Auto", value: "AUTO" },
  { label: "Home", value: "HOME" },
  { label: "Life", value: "LIFE" },
  { label: "Travel", value: "TRAVEL" },
  { label: "Business", value: "BUSINESS" },
  { label: "Other", value: "OTHER" },
];

// ─── Premium Frequency Options ───────────────────────────────────────────────

const premiumFrequencyOptions: { label: string; value: PremiumFrequency }[] = [
  { label: "Monthly", value: "MONTHLY" },
  { label: "Quarterly", value: "QUARTERLY" },
  { label: "Yearly", value: "YEARLY" },
];

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<InsurancePolicyOut, InsurancePolicyCreate, InsurancePolicyUpdate>({
  store: insuranceStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      policy_name: entity.policy_name ?? "",
      insurance_type: entity.insurance_type ?? "OTHER",
      provider: entity.provider ?? "",
      institution_id: entity.institution_id ?? "",
      policy_number: entity.policy_number ?? "",
      premium_amount: entity.premium_amount ?? "",
      currency: entity.currency ?? "USD",
      premium_frequency: entity.premium_frequency ?? "MONTHLY",
      renewal_date: entity.renewal_date ?? "",
      coverage_amount: entity.coverage_amount ?? "",
      coverage_details: entity.coverage_details ?? "",
      deductible: entity.deductible ?? "",
      remind_renewal: entity.remind_renewal ?? false,
      days_before_renewal_reminder: entity.days_before_renewal_reminder ?? 30,
    };
  },
  buildCreatePayload(formData) {
    return {
      policy_name: String(formData.policy_name),
      insurance_type: formData.insurance_type as InsuranceType,
      provider: String(formData.provider),
      institution_id: formData.institution_id ? Number(formData.institution_id) : null,
      policy_number: formData.policy_number ? String(formData.policy_number) : null,
      premium_amount: String(formData.premium_amount),
      currency: formData.currency ? String(formData.currency) : undefined,
      premium_frequency: formData.premium_frequency as PremiumFrequency,
      renewal_date: String(formData.renewal_date),
      coverage_amount: formData.coverage_amount ? String(formData.coverage_amount) : null,
      coverage_details: formData.coverage_details ? String(formData.coverage_details) : null,
      deductible: formData.deductible ? String(formData.deductible) : null,
      remind_renewal: Boolean(formData.remind_renewal),
      days_before_renewal_reminder: formData.days_before_renewal_reminder
        ? Number(formData.days_before_renewal_reminder)
        : 30,
    } as InsurancePolicyCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("insurance_type" in diff) diff.insurance_type = diff.insurance_type as InsuranceType;
    if ("provider" in diff) diff.provider = diff.provider ? String(diff.provider) : null;
    if ("institution_id" in diff) diff.institution_id = diff.institution_id ? Number(diff.institution_id) : null;
    if ("policy_number" in diff) diff.policy_number = diff.policy_number ? String(diff.policy_number) : null;
    if ("premium_amount" in diff) diff.premium_amount = diff.premium_amount ? String(diff.premium_amount) : null;
    if ("currency" in diff) diff.currency = diff.currency ? String(diff.currency) : null;
    if ("premium_frequency" in diff) diff.premium_frequency = diff.premium_frequency as PremiumFrequency;
    if ("renewal_date" in diff) diff.renewal_date = diff.renewal_date ? String(diff.renewal_date) : null;
    if ("coverage_amount" in diff) diff.coverage_amount = diff.coverage_amount ? String(diff.coverage_amount) : null;
    if ("coverage_details" in diff) diff.coverage_details = diff.coverage_details ? String(diff.coverage_details) : null;
    if ("deductible" in diff) diff.deductible = diff.deductible ? String(diff.deductible) : null;
    if ("remind_renewal" in diff) diff.remind_renewal = Boolean(diff.remind_renewal);
    if ("days_before_renewal_reminder" in diff) diff.days_before_renewal_reminder = diff.days_before_renewal_reminder ? Number(diff.days_before_renewal_reminder) : null;
    return diff as InsurancePolicyUpdate;
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
    // Set defaults for create mode
    form.setFieldValue("insurance_type", "OTHER");
    form.setFieldValue("premium_frequency", "MONTHLY");
    form.setFieldValue("currency", "USD");
    form.setFieldValue("remind_renewal", true);
    form.setFieldValue("days_before_renewal_reminder", 30);
  }
});

// ─── Currency Input Handlers ─────────────────────────────────────────────────

function handlePremiumUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("premium_amount", data.amount);
  form.setFieldValue("currency", data.currency);
}

function handleCoverageUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("coverage_amount", data.amount);
}

function handleDeductibleUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("deductible", data.amount);
}

// ─── Select Change Handlers ──────────────────────────────────────────────────

function handleInsuranceTypeChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as InsuranceType;
  form.setFieldValue("insurance_type", value);
}

function handlePremiumFrequencyChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as PremiumFrequency;
  form.setFieldValue("premium_frequency", value);
}

function handleInstitutionChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value;
  form.setFieldValue("institution_id", value || "");
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
</script>

<template>
  <Modal
    :open="open"
    :title="mode === 'create' ? 'Add Policy' : 'Edit Policy'"
    size="lg"
    @close="handleCancel"
  >
    <template #body>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Form Errors -->
        <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

        <!-- Policy Name + Provider -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="policy-name" class="label-text">
              Policy Name <span class="text-debit">*</span>
            </label>
            <input
              id="policy-name"
              v-model="form.data.policy_name"
              type="text"
              class="input-field"
              placeholder="e.g. Health Shield Plus"
              required
            />
          </div>
          <div class="space-y-1.5">
            <label for="policy-provider" class="label-text">
              Provider <span class="text-debit">*</span>
            </label>
            <input
              id="policy-provider"
              v-model="form.data.provider"
              type="text"
              class="input-field"
              placeholder="e.g. Blue Cross, State Farm"
              required
            />
          </div>
        </div>

        <!-- Insurance Type + Institution -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="insurance-type" class="label-text">Insurance Type</label>
            <select
              id="insurance-type"
              :value="form.data.insurance_type"
              class="input-field"
              @change="handleInsuranceTypeChange"
            >
              <option
                v-for="opt in insuranceTypeOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
          </div>
          <div class="space-y-1.5">
            <label for="policy-institution" class="label-text">Institution</label>
            <select
              id="policy-institution"
              :value="form.data.institution_id"
              class="input-field"
              @change="handleInstitutionChange"
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

        <!-- Policy Number -->
        <div class="space-y-1.5">
          <label for="policy-number" class="label-text">Policy Number</label>
          <input
            id="policy-number"
            v-model="form.data.policy_number"
            type="text"
            class="input-field"
            placeholder="e.g. POL-2024-001 (optional)"
          />
        </div>

        <!-- Premium Amount + Frequency -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="label-text">
              Premium Amount <span class="text-debit">*</span>
            </label>
            <CurrencyInput
              :amount="String(form.data.premium_amount ?? '')"
              :currency="String(form.data.currency ?? 'USD')"
              :show-currency-select="true"
              placeholder="0.00"
              @update="handlePremiumUpdate"
            />
          </div>
          <div class="space-y-1.5">
            <label for="premium-frequency" class="label-text">Premium Frequency</label>
            <select
              id="premium-frequency"
              :value="form.data.premium_frequency"
              class="input-field"
              @change="handlePremiumFrequencyChange"
            >
              <option
                v-for="opt in premiumFrequencyOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>

        <!-- Renewal Date -->
        <div class="space-y-1.5">
          <label for="renewal-date" class="label-text">
            Renewal Date <span class="text-debit">*</span>
          </label>
          <input
            id="renewal-date"
            v-model="form.data.renewal_date"
            type="date"
            class="input-field"
            required
          />
        </div>

        <!-- Coverage Amount + Deductible -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="label-text">Coverage Amount</label>
            <CurrencyInput
              :amount="String(form.data.coverage_amount ?? '')"
              :show-currency-select="false"
              placeholder="0.00 (optional)"
              @update="handleCoverageUpdate"
            />
          </div>
          <div class="space-y-1.5">
            <label class="label-text">Deductible</label>
            <CurrencyInput
              :amount="String(form.data.deductible ?? '')"
              :show-currency-select="false"
              placeholder="0.00 (optional)"
              @update="handleDeductibleUpdate"
            />
          </div>
        </div>

        <!-- Coverage Details -->
        <div class="space-y-1.5">
          <label for="coverage-details" class="label-text">Coverage Details</label>
          <textarea
            id="coverage-details"
            v-model="form.data.coverage_details"
            class="input-field min-h-[80px] resize-y"
            placeholder="Optional details about coverage..."
            rows="3"
          />
        </div>

        <!-- Renewal Reminder -->
        <div class="space-y-3 p-4 rounded-lg bg-navy-50 dark:bg-navy-900/30 border border-navy-200 dark:border-navy-700">
          <div class="flex items-center gap-3">
            <input
              id="remind-renewal"
              v-model="form.data.remind_renewal"
              type="checkbox"
              class="h-4 w-4 rounded border-navy-300 text-cyan-600 focus:ring-cyan-500"
            />
            <label for="remind-renewal" class="text-sm font-medium text-navy-900 dark:text-navy-100">
              Remind me before renewal
            </label>
          </div>
          <div v-if="form.data.remind_renewal" class="space-y-1.5 pl-7">
            <label for="days-reminder" class="label-text">Days before renewal to remind</label>
            <input
              id="days-reminder"
              v-model.number="form.data.days_before_renewal_reminder"
              type="number"
              class="input-field"
              min="1"
              max="365"
              placeholder="30"
            />
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
        {{ mode === "create" ? "Create Policy" : "Update Policy" }}
      </button>
    </template>
  </Modal>
</template>
