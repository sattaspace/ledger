<script setup lang="ts">
/**
 * FormErrors — Django Ninja error display component.
 *
 * Renders both general error messages and field-level validation
 * errors from the Django Ninja API error format.
 *
 * Usage:
 *   <FormErrors :errors="store.error" :field-errors="store.fieldErrors" />
 */

const props = withDefaults(
  defineProps<{
    /** General error message string. */
    errors?: string | null;
    /** Field-level validation errors from Django Ninja. */
    fieldErrors?: Record<string, string[]>;
  }>(),
  {
    errors: null,
    fieldErrors: () => ({}),
  },
);

// ─── Computed ─────────────────────────────────────────────────────────────────

const hasGeneralError = computed(() => !!props.errors);
const hasFieldErrors = computed(
  () => Object.keys(props.fieldErrors).length > 0,
);
const hasAnyErrors = computed(() => hasGeneralError.value || hasFieldErrors.value);

/** Format field name for display: "account_id" → "Account" */
function formatFieldName(field: string): string {
  return field
    .replace(/_/g, " ")
    .replace(/id$/i, "")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}
</script>

<template>
  <div v-if="hasAnyErrors" class="space-y-2" role="alert">
    <!-- General Error -->
    <div
      v-if="hasGeneralError"
      class="rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 p-3"
    >
      <div class="flex gap-2">
        <svg class="h-5 w-5 text-debit flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
        </svg>
        <p class="text-sm text-red-800 dark:text-red-300">
          {{ errors }}
        </p>
      </div>
    </div>

    <!-- Field Errors -->
    <div
      v-if="hasFieldErrors"
      class="rounded-lg bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 p-3"
    >
      <div class="flex gap-2">
        <svg class="h-5 w-5 text-debit flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <div class="flex-1">
          <p class="text-sm font-medium text-red-800 dark:text-red-300 mb-1">
            Please fix the following errors:
          </p>
          <ul class="text-sm text-red-700 dark:text-red-400 list-disc list-inside space-y-0.5">
            <li v-for="(messages, field) in fieldErrors" :key="field">
              <strong>{{ formatFieldName(String(field)) }}:</strong>
              {{ messages.join(", ") }}
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
