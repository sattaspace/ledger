<script setup lang="ts">
/**
 * ConfirmDialog — Destructive action confirmation with variant styling.
 *
 * Wraps Modal with a pre-built confirmation UI for common patterns:
 * delete, restore, activate, deactivate, and generic confirmations.
 *
 * Usage:
 *   <ConfirmDialog
 *     :open="showDelete"
 *     title="Delete Institution"
 *     message="This will soft-delete the institution. You can restore it later."
 *     confirmText="Delete"
 *     variant="destructive"
 *     @confirm="handleDelete"
 *     @cancel="showDelete = false"
 *   />
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import Modal from "./Modal.vue";

const props = withDefaults(
  defineProps<{
    /** Whether the dialog is visible. */
    open: boolean;
    /** Dialog title. */
    title: string;
    /** Descriptive message explaining the action. */
    message: string;
    /** Label on the confirm button. */
    confirmText?: string;
    /** Label on the cancel button. */
    cancelText?: string;
    /** Visual variant affecting button color and icon. */
    variant?: "destructive" | "warning" | "primary" | "success";
    /** Show loading spinner on confirm button. */
    loading?: boolean;
  }>(),
  {
    confirmText: "Confirm",
    cancelText: "Cancel",
    variant: "primary",
    loading: false,
  },
);

const emit = defineEmits<{
  confirm: [];
  cancel: [];
}>();

// ─── Variant Styling ──────────────────────────────────────────────────────────

const variantButtonClass = computed(() => {
  switch (props.variant) {
    case "destructive":
      return "btn-destructive";
    case "warning":
      return "bg-amber-600 text-white hover:bg-amber-700 focus:ring-amber-500 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2";
    case "success":
      return "bg-credit text-white hover:bg-green-700 focus:ring-green-500 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2";
    default:
      return "btn-primary";
  }
});

const variantIconClass = computed(() => {
  switch (props.variant) {
    case "destructive":
      return "bg-red-100 dark:bg-red-950/50 text-debit";
    case "warning":
      return "bg-amber-100 dark:bg-amber-950/50 text-amber-600 dark:text-amber-400";
    case "success":
      return "bg-green-100 dark:bg-green-950/50 text-credit";
    default:
      return "bg-cyan-100 dark:bg-cyan-950/50 text-cyan-600 dark:text-cyan-400";
  }
});
</script>

<template>
  <Modal :open="open" :title="title" size="sm" @close="emit('cancel')">
    <template #body>
      <div class="flex gap-4">
        <!-- Icon -->
        <div :class="['flex-shrink-0 rounded-full p-3', variantIconClass]">
          <!-- Destructive: trash icon -->
          <svg v-if="variant === 'destructive'" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <!-- Warning: exclamation -->
          <svg v-else-if="variant === 'warning'" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <!-- Success: check -->
          <svg v-else-if="variant === 'success'" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
          <!-- Default: info -->
          <svg v-else class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
        </div>

        <!-- Message -->
        <div class="text-sm text-slate-custom-700 dark:text-slate-custom-300">
          {{ message }}
        </div>
      </div>
    </template>

    <template #footer>
      <button
        class="btn-secondary"
        :disabled="loading"
        @click="emit('cancel')"
      >
        {{ cancelText }}
      </button>
      <button
        :class="[variantButtonClass, 'inline-flex items-center gap-2']"
        :disabled="loading"
        @click="emit('confirm')"
      >
        <!-- Loading Spinner -->
        <svg
          v-if="loading"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ confirmText }}
      </button>
    </template>
  </Modal>
</template>
