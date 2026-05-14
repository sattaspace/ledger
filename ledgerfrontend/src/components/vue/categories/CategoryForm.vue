<script setup lang="ts">
/**
 * CategoryForm — Create / Edit form for Category entities.
 *
 * Used inside a Modal on the CategoriesPage. Handles both create and edit
 * modes via useCrudForm. Renders a CategoryTreeSelect for parent_id,
 * a toggle for is_income, and standard text/number inputs for the rest.
 *
 * Props:
 *   mode   — 'create' | 'edit'
 *   itemId — Required for edit mode; the category ID to load.
 *
 * Emits:
 *   saved  — Fired after successful create/update.
 *   cancel — Fired when the user cancels the form.
 */

import { onMounted, computed, watch } from "vue";
import { useCrudForm } from "@/composables";
import { useCategoryStore } from "@/stores/category";
import { CategoryTreeSelect } from "@/components/vue";
import { FormErrors } from "@/components/vue";
import type { TreeNode } from "@/components/vue/CategoryTreeSelect.vue";
import type {
  CategoryOut,
  CategoryCreate,
  CategoryUpdate,
  CategoryTreeOut,
} from "@/lib/ledgerTypes";

// ─── Props & Emits ──────────────────────────────────────────────────────────

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
  saved: [item: CategoryOut];
  cancel: [];
}>();

// ─── Store ──────────────────────────────────────────────────────────────────

const store = useCategoryStore();

// ─── Convert CategoryTreeOut[] → TreeNode[] ─────────────────────────────────

function convertToTreeNode(tree: CategoryTreeOut[]): TreeNode[] {
  return tree.map((node) => ({
    id: node.id,
    name: node.name,
    icon: node.icon || undefined,
    color: node.color || undefined,
    is_income: node.is_income,
    sort_order: node.sort_order,
    subcategories: node.subcategories?.length
      ? convertToTreeNode(node.subcategories)
      : undefined,
  }));
}

/** Reactive tree data for the CategoryTreeSelect. */
const treeNodes = computed<TreeNode[]>(() => convertToTreeNode(store.tree));

// ─── Form via useCrudForm ───────────────────────────────────────────────────

const form = useCrudForm<CategoryOut, CategoryCreate, CategoryUpdate>({
  store,
  mode: props.mode,
  itemId: props.itemId,

  mapEntityToForm(entity) {
    return {
      name: entity.name ?? "",
      parent_id: entity.parent_id ?? null,
      is_income: entity.is_income ?? false,
      icon: entity.icon ?? "",
      color: entity.color ?? "",
      sort_order: entity.sort_order ?? 0,
    };
  },

  buildCreatePayload(formData) {
    return {
      name: formData.name as string,
      parent_id: (formData.parent_id as number | null) || null,
      is_income: formData.is_income as boolean,
      icon: (formData.icon as string) || null,
      color: (formData.color as string) || null,
      sort_order: formData.sort_order as number,
    } as CategoryCreate;
  },

  buildUpdatePayload(formData, original) {
    const payload: Record<string, unknown> = {};
    const fields = [
      "name",
      "parent_id",
      "is_income",
      "icon",
      "color",
      "sort_order",
    ] as const;

    for (const field of fields) {
      if (JSON.stringify(formData[field]) !== JSON.stringify(original[field])) {
        payload[field] = formData[field];
      }
    }

    // Ensure parent_id null is sent, not omitted
    if ("parent_id" in payload) {
      payload.parent_id = (payload.parent_id as number | null) || null;
    }

    return payload as CategoryUpdate;
  },

  onSuccess(item) {
    // Refresh tree after create/update
    store.fetchTree(true);
    emit("saved", item);
  },
});

// ─── Load tree data for the parent selector ─────────────────────────────────

onMounted(async () => {
  await store.fetchTree();

  if (props.mode === "edit" && props.itemId) {
    await form.load();
  }
});

// ─── is_income toggle helper ────────────────────────────────────────────────

const isIncome = computed({
  get: () => form.data.is_income as boolean,
  set: (val: boolean) => {
    form.data.is_income = val;
  },
});

// ─── Submit handler ─────────────────────────────────────────────────────────

async function handleSubmit() {
  await form.submit();
}

// ─── Cancel handler ─────────────────────────────────────────────────────────

function handleCancel() {
  emit("cancel");
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="form.error.value" :field-errors="form.fieldErrors.value" />

    <!-- Name -->
    <div class="space-y-1.5">
      <label for="cat-name" class="label-text">
        Name <span class="text-debit">*</span>
      </label>
      <input
        id="cat-name"
        v-model="form.data.name"
        type="text"
        required
        placeholder="e.g. Groceries, Salary"
        class="input-field"
      />
    </div>

    <!-- Parent Category -->
    <div class="space-y-1.5">
      <label class="label-text">Parent Category</label>
      <CategoryTreeSelect
        :categories="treeNodes"
        :model-value="(form.data.parent_id as number | null)"
        placeholder="None (top-level category)"
        @update:model-value="form.data.parent_id = $event"
      />
      <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
        Leave empty for a top-level category.
      </p>
    </div>

    <!-- is_income toggle -->
    <div class="space-y-1.5">
      <label class="label-text">Type</label>
      <div class="flex items-center gap-3">
        <!-- Toggle Switch -->
        <button
          type="button"
          role="switch"
          :aria-checked="isIncome"
          :class="[
            'relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2',
            isIncome
              ? 'bg-credit'
              : 'bg-debit',
          ]"
          @click="isIncome = !isIncome"
        >
          <span
            :class="[
              'pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow-sm ring-0 transition-transform duration-200 ease-in-out',
              isIncome ? 'translate-x-5' : 'translate-x-0',
            ]"
          />
        </button>
        <span
          :class="[
            'text-sm font-medium',
            isIncome
              ? 'text-credit dark:text-green-400'
              : 'text-debit dark:text-red-400',
          ]"
        >
          {{ isIncome ? 'Income' : 'Expense' }}
        </span>
      </div>
    </div>

    <!-- Icon -->
    <div class="space-y-1.5">
      <label for="cat-icon" class="label-text">Icon</label>
      <input
        id="cat-icon"
        v-model="form.data.icon"
        type="text"
        placeholder="e.g. 🛒, 💰"
        class="input-field"
      />
    </div>

    <!-- Color -->
    <div class="space-y-1.5">
      <label for="cat-color" class="label-text">Color</label>
      <div class="flex items-center gap-3">
        <input
          id="cat-color"
          v-model="form.data.color"
          type="text"
          placeholder="#00B4E6"
          class="input-field flex-1"
        />
        <input
          type="color"
          :value="(form.data.color as string) || '#00B4E6'"
          class="h-10 w-10 cursor-pointer rounded-lg border border-navy-200 dark:border-navy-700 bg-transparent p-0.5"
          @input="form.data.color = ($event.target as HTMLInputElement).value"
        />
      </div>
    </div>

    <!-- Sort Order -->
    <div class="space-y-1.5">
      <label for="cat-sort" class="label-text">Sort Order</label>
      <input
        id="cat-sort"
        v-model.number="form.data.sort_order"
        type="number"
        min="0"
        placeholder="0"
        class="input-field w-28"
      />
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
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ form.isEdit ? 'Update Category' : 'Create Category' }}
      </button>
    </div>
  </form>
</template>
