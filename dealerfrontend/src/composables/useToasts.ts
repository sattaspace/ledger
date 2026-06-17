/**
 * useToasts — global toast notification state.
 *
 * Extracted from App.vue so the toast container (mounted in AppFooter.vue)
 * can share state with any page or component that needs to trigger a toast.
 *
 * Module-level singleton — survives Astro View Transitions because the
 * AppFooter island is `transition:persist`.
 */

import { ref } from "vue";

const successToast = ref("");
const errorToast = ref("");

let successTimer: ReturnType<typeof setTimeout> | null = null;
let errorTimer: ReturnType<typeof setTimeout> | null = null;

function triggerToast(msg: string): void {
  successToast.value = msg;
  errorToast.value = "";
  if (successTimer) clearTimeout(successTimer);
  successTimer = setTimeout(() => {
    if (successToast.value === msg) successToast.value = "";
  }, 4000);
}

function triggerErrorToast(msg: string): void {
  errorToast.value = msg;
  successToast.value = "";
  if (errorTimer) clearTimeout(errorTimer);
  errorTimer = setTimeout(() => {
    if (errorToast.value === msg) errorToast.value = "";
  }, 6000);
}

function clearSuccessToast(): void {
  successToast.value = "";
}

function clearErrorToast(): void {
  errorToast.value = "";
}

export function useToasts() {
  return {
    successToast,
    errorToast,
    triggerToast,
    triggerErrorToast,
    clearSuccessToast,
    clearErrorToast,
  };
}
