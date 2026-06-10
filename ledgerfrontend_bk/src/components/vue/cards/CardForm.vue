<script setup lang="ts">
/**
 * CardForm — Create/edit form for Card entities.
 *
 * Fields:
 *   account_id (dropdown), card_type (Debit/Credit), card_name,
 *   last_four, expiry_date, annual_fee, annual_fee_date, color,
 *   sort_order
 *
 * Uses useCrudForm composable for lifecycle management.
 * Emits 'saved' on successful create/update.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  FormErrors,
} from "@/components/vue";
import CurrencyInput from "@/components/vue/CurrencyInput.vue";
import { useCrudForm, useDropdownLoader } from "@/composables";
import { useCardStore } from "@/stores/card";
import { useAccountStore } from "@/stores/account";
import type {
  CardOut,
  CardCreate,
  CardUpdate,
  CardType,
} from "@/lib/ledgerTypes";

// ─── Component Name ──────────────────────────────────────────────────────────

defineOptions({ name: "CardForm" });

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
  saved: [item: CardOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const cardStore = useCardStore();
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

// ─── Card Type Options ───────────────────────────────────────────────────────

const cardTypeOptions: { label: string; value: CardType }[] = [
  { label: "Credit", value: "CREDIT" },
  { label: "Debit", value: "DEBIT" },
];

// ─── Color Options ───────────────────────────────────────────────────────────

const colorOptions = [
  { label: "Cyan", value: "#0891b2" },
  { label: "Indigo", value: "#4f46e5" },
  { label: "Emerald", value: "#059669" },
  { label: "Amber", value: "#d97706" },
  { label: "Rose", value: "#e11d48" },
  { label: "Violet", value: "#7c3aed" },
  { label: "Slate", value: "#475569" },
  { label: "Navy", value: "#1e3a5f" },
];

// ─── CRUD Form ───────────────────────────────────────────────────────────────

const form = useCrudForm<CardOut, CardCreate, CardUpdate>({
  store: cardStore,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm(entity) {
    return {
      account_id: entity.account_id ?? "",
      card_type: entity.card_type ?? "CREDIT",
      card_name: entity.card_name ?? "",
      last_four: entity.last_four ?? "",
      expiry_date: entity.expiry_date ?? "",
      annual_fee: entity.annual_fee ?? "0",
      annual_fee_date: entity.annual_fee_date ?? "",
      color: entity.color ?? "#0891b2",
      sort_order: entity.sort_order ?? 0,
    };
  },
  buildCreatePayload(formData) {
    return {
      account_id: Number(formData.account_id),
      card_type: formData.card_type as CardType,
      card_name: String(formData.card_name),
      last_four: String(formData.last_four),
      expiry_date: formData.expiry_date ? String(formData.expiry_date) : null,
      annual_fee: formData.annual_fee ? String(formData.annual_fee) : "0",
      annual_fee_date: formData.annual_fee_date ? String(formData.annual_fee_date) : null,
      color: formData.color ? String(formData.color) : null,
      sort_order: formData.sort_order ? Number(formData.sort_order) : 0,
    } as CardCreate;
  },
  buildUpdatePayload(formData, original) {
    const diff: Record<string, unknown> = {};
    for (const key of Object.keys(formData)) {
      if (JSON.stringify(formData[key]) !== JSON.stringify(original[key])) {
        diff[key] = formData[key];
      }
    }
    // Coerce types for the API
    if ("account_id" in diff) diff.account_id = diff.account_id ? Number(diff.account_id) : null;
    if ("card_type" in diff) diff.card_type = diff.card_type as CardType;
    if ("last_four" in diff) diff.last_four = String(diff.last_four);
    if ("expiry_date" in diff) diff.expiry_date = diff.expiry_date ? String(diff.expiry_date) : null;
    if ("annual_fee" in diff) diff.annual_fee = diff.annual_fee ? String(diff.annual_fee) : null;
    if ("annual_fee_date" in diff) diff.annual_fee_date = diff.annual_fee_date ? String(diff.annual_fee_date) : null;
    if ("color" in diff) diff.color = diff.color ? String(diff.color) : null;
    if ("sort_order" in diff) diff.sort_order = diff.sort_order ? Number(diff.sort_order) : null;
    return diff as CardUpdate;
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

// ─── Methods ─────────────────────────────────────────────────────────────────

function handleSubmit() {
  form.submit();
}

function handleCancel() {
  emit("cancel");
}

function handleCardTypeChange(event: Event) {
  const value = (event.target as HTMLSelectElement).value as CardType;
  form.setFieldValue("card_type", value);
}

function handleAnnualFeeUpdate(data: { amount: string; currency: string }) {
  form.setFieldValue("annual_fee", data.amount);
}

function handleColorSelect(color: string) {
  form.setFieldValue("color", color);
}
</script>

<template>
  <Modal
    :open="open"
    :title="mode === 'create' ? 'Add Card' : 'Edit Card'"
    size="lg"
    @close="handleCancel"
  >
    <template #body>
      <form @submit.prevent="handleSubmit" class="space-y-5">
        <!-- Form Errors -->
        <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

        <!-- Card Name -->
        <div class="space-y-1.5">
          <label for="card-name" class="label-text">
            Card Name <span class="text-debit">*</span>
          </label>
          <input
            id="card-name"
            v-model="form.data.card_name"
            type="text"
            class="input-field"
            placeholder="e.g. Chase Sapphire, BofA Debit"
            required
          />
        </div>

        <!-- Account + Card Type -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="card-account" class="label-text">
              Account <span class="text-debit">*</span>
            </label>
            <select
              id="card-account"
              v-model="form.data.account_id"
              class="input-field"
              required
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
            <label for="card-type" class="label-text">
              Card Type <span class="text-debit">*</span>
            </label>
            <select
              id="card-type"
              :value="form.data.card_type"
              class="input-field"
              required
              @change="handleCardTypeChange"
            >
              <option
                v-for="opt in cardTypeOptions"
                :key="opt.value"
                :value="opt.value"
              >
                {{ opt.label }}
              </option>
            </select>
          </div>
        </div>

        <!-- Last Four + Expiry Date -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label for="card-last-four" class="label-text">
              Last Four Digits <span class="text-debit">*</span>
            </label>
            <input
              id="card-last-four"
              v-model="form.data.last_four"
              type="text"
              class="input-field"
              placeholder="4242"
              maxlength="4"
              pattern="[0-9]{4}"
              inputmode="numeric"
              required
            />
          </div>
          <div class="space-y-1.5">
            <label for="card-expiry" class="label-text">Expiry Date</label>
            <input
              id="card-expiry"
              v-model="form.data.expiry_date"
              type="date"
              class="input-field"
            />
          </div>
        </div>

        <!-- Annual Fee + Annual Fee Date -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="space-y-1.5">
            <label class="label-text">Annual Fee</label>
            <CurrencyInput
              :amount="String(form.data.annual_fee ?? '0')"
              :show-currency-select="false"
              placeholder="0.00"
              @update="handleAnnualFeeUpdate"
            />
          </div>
          <div class="space-y-1.5">
            <label for="card-annual-fee-date" class="label-text">Annual Fee Date</label>
            <input
              id="card-annual-fee-date"
              v-model="form.data.annual_fee_date"
              type="date"
              class="input-field"
            />
          </div>
        </div>

        <!-- Color Picker -->
        <div class="space-y-1.5">
          <label class="label-text">Card Color</label>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="opt in colorOptions"
              :key="opt.value"
              type="button"
              :class="[
                'h-9 w-9 rounded-lg border-2 transition-all duration-150 hover:scale-110',
                form.data.color === opt.value
                  ? 'border-white ring-2 ring-cyan-500 shadow-md'
                  : 'border-transparent hover:border-white/30',
              ]"
              :style="{ backgroundColor: opt.value }"
              :title="opt.label"
              :aria-label="`Select ${opt.label} color`"
              @click="handleColorSelect(opt.value)"
            />
          </div>
          <!-- Custom color input -->
          <div class="flex items-center gap-2 mt-2">
            <input
              type="color"
              :value="form.data.color ?? '#0891b2'"
              class="h-8 w-8 rounded border border-navy-200 dark:border-navy-700 cursor-pointer"
              @input="(e: Event) => handleColorSelect((e.target as HTMLInputElement).value)"
            />
            <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">Custom color</span>
          </div>
        </div>

        <!-- Sort Order -->
        <div class="space-y-1.5">
          <label for="card-sort-order" class="label-text">Sort Order</label>
          <input
            id="card-sort-order"
            v-model.number="form.data.sort_order"
            type="number"
            class="input-field w-24"
            min="0"
            placeholder="0"
          />
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
            Lower numbers appear first
          </p>
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
        {{ mode === "create" ? "Create Card" : "Update Card" }}
      </button>
    </template>
  </Modal>
</template>
