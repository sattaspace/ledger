<script setup lang="ts">
/**
 * InstitutionForm — Create/edit form for Institution entities.
 *
 * Used inside a Modal component for both creating and editing
 * institutions. Integrates with useCrudForm for lifecycle
 * management and the institution Pinia store for API calls.
 *
 * Usage:
 *   <InstitutionForm mode="create" @saved="onSaved" @cancel="onCancel" />
 *   <InstitutionForm mode="edit" :item-id="institution.id" @saved="onSaved" @cancel="onCancel" />
 */

import { onMounted } from "vue";
import { useCrudForm } from "@/composables";
import { useInstitutionStore } from "@/stores/institution";
import { FormErrors } from "@/components/vue";
import type { InstitutionOut, InstitutionCreate, InstitutionUpdate, InstitutionType } from "@/lib/ledgerTypes";

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
  saved: [item: InstitutionOut];
  cancel: [];
}>();

// ─── Store & Form ─────────────────────────────────────────────────────────────

const store = useInstitutionStore();

const form = useCrudForm<InstitutionOut, InstitutionCreate, InstitutionUpdate>({
  store,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm: (entity) => ({
    name: entity.name ?? "",
    institution_type: entity.institution_type ?? "BANK",
    website: entity.website ?? "",
    customer_service_phone: entity.customer_service_phone ?? "",
    icon: entity.icon ?? "",
    color: entity.color ?? "",
    notes: entity.notes ?? "",
  }),
  buildCreatePayload: (formData) => ({
    name: formData.name as string,
    institution_type: formData.institution_type as InstitutionType,
    website: (formData.website as string) || null,
    customer_service_phone: (formData.customer_service_phone as string) || null,
    icon: (formData.icon as string) || null,
    color: (formData.color as string) || null,
    notes: (formData.notes as string) || null,
  }),
  onSuccess: (item) => {
    emit("saved", item);
  },
});

// ─── Institution Type Options ─────────────────────────────────────────────────

const institutionTypeOptions: { label: string; value: InstitutionType }[] = [
  { label: "Bank", value: "BANK" },
  { label: "Credit Union", value: "CREDIT_UNION" },
  { label: "Brokerage", value: "BROKERAGE" },
  { label: "Crypto", value: "CRYPTO" },
  { label: "Wallet", value: "WALLET" },
  { label: "Other", value: "OTHER" },
];

// ─── Submit Label ─────────────────────────────────────────────────────────────

const submitLabel = form.isEdit ? "Update Institution" : "Create Institution";

// ─── Load entity for edit mode ────────────────────────────────────────────────

onMounted(async () => {
  if (form.isEdit && props.itemId) {
    await form.load();
  } else {
    // Initialize default values for create mode
    form.setFieldValue("name", "");
    form.setFieldValue("institution_type", "BANK");
    form.setFieldValue("website", "");
    form.setFieldValue("customer_service_phone", "");
    form.setFieldValue("icon", "");
    form.setFieldValue("color", "");
    form.setFieldValue("notes", "");
  }
});

// ─── Handlers ─────────────────────────────────────────────────────────────────

async function handleSubmit(): Promise<void> {
  await form.submit();
  // onSuccess callback will emit 'saved' if successful
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
      <label for="institution-name" class="label-text">
        Name <span class="text-debit">*</span>
      </label>
      <input
        id="institution-name"
        v-model="form.data.name"
        type="text"
        required
        placeholder="e.g. Chase Bank"
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

    <!-- Institution Type -->
    <div class="space-y-1.5">
      <label for="institution-type" class="label-text">
        Institution Type
      </label>
      <select
        id="institution-type"
        v-model="form.data.institution_type"
        class="input-field"
        :disabled="form.loading.value"
      >
        <option
          v-for="opt in institutionTypeOptions"
          :key="opt.value"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>
      <p
        v-if="form.fieldErrors.value?.institution_type"
        class="text-xs text-debit"
        role="alert"
      >
        {{ form.fieldErrors.value.institution_type.join(", ") }}
      </p>
    </div>

    <!-- Website -->
    <div class="space-y-1.5">
      <label for="institution-website" class="label-text">
        Website
      </label>
      <input
        id="institution-website"
        v-model="form.data.website"
        type="url"
        placeholder="https://www.example.com"
        class="input-field"
        :aria-invalid="!!form.fieldErrors.value?.website"
        :disabled="form.loading.value"
        autocomplete="url"
      />
      <p
        v-if="form.fieldErrors.value?.website"
        class="text-xs text-debit"
        role="alert"
      >
        {{ form.fieldErrors.value.website.join(", ") }}
      </p>
    </div>

    <!-- Customer Service Phone -->
    <div class="space-y-1.5">
      <label for="institution-phone" class="label-text">
        Customer Service Phone
      </label>
      <input
        id="institution-phone"
        v-model="form.data.customer_service_phone"
        type="tel"
        placeholder="1-800-555-0199"
        class="input-field"
        :aria-invalid="!!form.fieldErrors.value?.customer_service_phone"
        :disabled="form.loading.value"
        autocomplete="tel"
      />
      <p
        v-if="form.fieldErrors.value?.customer_service_phone"
        class="text-xs text-debit"
        role="alert"
      >
        {{ form.fieldErrors.value.customer_service_phone.join(", ") }}
      </p>
    </div>

    <!-- Icon & Color Row -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <!-- Icon -->
      <div class="space-y-1.5">
        <label for="institution-icon" class="label-text">
          Icon
        </label>
        <input
          id="institution-icon"
          v-model="form.data.icon"
          type="text"
          placeholder="e.g. landmark"
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
        <label for="institution-color" class="label-text">
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
            id="institution-color"
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

    <!-- Notes -->
    <div class="space-y-1.5">
      <label for="institution-notes" class="label-text">
        Notes
      </label>
      <textarea
        id="institution-notes"
        v-model="form.data.notes"
        rows="3"
        placeholder="Optional notes about this institution..."
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
