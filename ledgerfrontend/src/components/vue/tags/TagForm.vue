<script setup lang="ts">
/**
 * TagForm — Create/Edit form for Tag entities.
 *
 * Compact two-field form (name + color) designed for small modals.
 * Uses useCrudForm for lifecycle management and FormErrors for
 * validation display.
 *
 * Props:
 *   mode   — 'create' | 'edit'
 *   itemId — Tag ID for edit mode (required when mode='edit')
 *
 * Events:
 *   saved  — Emitted after successful create/update with the entity
 *   cancel — Emitted when user cancels the form
 */

import { FormErrors } from "@/components/vue";
import { useCrudForm } from "@/composables";
import { useTagStore } from "@/stores/tag";
import type { TagOut, TagCreate, TagUpdate } from "@/lib/ledgerTypes";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrTagForm",
});

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Form mode: creating a new tag or editing an existing one. */
    mode: "create" | "edit";
    /** Tag ID for edit mode. Required when mode='edit'. */
    itemId?: number;
  }>(),
  {
    itemId: undefined,
  },
);

const emit = defineEmits<{
  saved: [tag: TagOut];
  cancel: [];
}>();

// ─── Store ────────────────────────────────────────────────────────────────────

const store = useTagStore();

// ─── Form ─────────────────────────────────────────────────────────────────────

const form = useCrudForm<TagOut, TagCreate, TagUpdate>({
  store,
  mode: props.mode,
  itemId: props.itemId,
  mapEntityToForm: (entity: TagOut) => ({
    name: entity.name,
    color: entity.color || "#6B7280",
  }),
  buildCreatePayload: (formData) => ({
    name: String(formData.name ?? "").trim(),
    color: formData.color ? String(formData.color) : null,
  }),
  buildUpdatePayload: (formData, original) => {
    const payload: TagUpdate = {};
    const newName = String(formData.name ?? "").trim();
    const origName = String(original.name ?? "");
    if (newName !== origName) payload.name = newName;

    const newColor = formData.color ? String(formData.color) : null;
    const origColor = original.color ? String(original.color) : null;
    if (newColor !== origColor) payload.color = newColor;

    return payload;
  },
  onSuccess: (tag) => {
    emit("saved", tag);
  },
});

// Initialize form defaults for create mode
if (props.mode === "create") {
  form.data.name = "";
  form.data.color = "#6B7280";
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  if (props.mode === "edit" && props.itemId) {
    await form.load();
  }
});

// ─── Color preview ───────────────────────────────────────────────────────────

const colorValue = computed({
  get: () => String(form.data.color ?? "#6B7280"),
  set: (val: string) => {
    form.data.color = val;
  },
});

// ─── Submit handler ──────────────────────────────────────────────────────────

async function handleSubmit() {
  const name = String(form.data.name ?? "").trim();
  if (!name) {
    form.setFieldError("name", "Tag name is required");
    return;
  }
  await form.submit();
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-4">
    <!-- Name Field -->
    <div class="space-y-1.5">
      <label for="tag-name" class="label-text">
        Name <span class="text-debit">*</span>
      </label>
      <input
        id="tag-name"
        v-model="form.data.name"
        type="text"
        class="input-field"
        placeholder="e.g. Urgent, Review, Tax-deductible"
        required
        autocomplete="off"
      />
    </div>

    <!-- Color Field -->
    <div class="space-y-1.5">
      <label for="tag-color" class="label-text">Color</label>
      <div class="flex items-center gap-3">
        <div class="relative">
          <input
            id="tag-color"
            v-model="colorValue"
            type="color"
            class="h-10 w-12 cursor-pointer rounded-lg border border-navy-200 dark:border-navy-700 bg-transparent p-1"
          />
        </div>
        <!-- Color preview swatch -->
        <div class="flex items-center gap-2 flex-1">
          <span
            class="h-6 w-6 rounded-full shrink-0 border border-navy-200 dark:border-navy-700"
            :style="{ backgroundColor: colorValue }"
          />
          <span class="text-sm text-slate-custom-600 dark:text-slate-custom-400 font-mono">
            {{ colorValue }}
          </span>
        </div>
      </div>
    </div>

    <!-- Errors -->
    <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3 pt-2">
      <button
        type="button"
        class="btn-secondary"
        :disabled="form.loading.value"
        @click="emit('cancel')"
      >
        Cancel
      </button>
      <button
        type="submit"
        class="btn-primary"
        :disabled="form.loading.value"
      >
        <!-- Loading spinner -->
        <svg
          v-if="form.loading.value"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
          />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
        {{ form.isEdit ? "Update" : "Create" }}
      </button>
    </div>
  </form>
</template>
