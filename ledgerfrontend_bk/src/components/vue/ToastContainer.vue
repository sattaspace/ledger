<script setup lang="ts">
/**
 * ToastContainer — Renders active toast notifications.
 *
 * Must be mounted once in the app shell (e.g. DashboardLayout.astro).
 * Reads from the shared Pinia toast store.
 *
 * Features:
 *   - Stacked toasts in bottom-right corner
 *   - Auto-dismiss with progress bar
 *   - Manual dismiss via close button
 *   - 4 variants: success (green), error (red), warning (amber), info (cyan)
 *   - Slide-in / slide-out animations
 *   - Max 5 visible toasts (oldest dismissed automatically)
 *   - Accessible: role="alert", aria-live="polite"
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useToast } from "@/composables/useToast";
import type { Toast, ToastVariant } from "@/composables/useToast";

const toast = useToast();

// ─── SSR guard — Teleport can only run client-side ────────────────────────
// <Teleport to="body"> is a no-op during SSR (renders inline), but on the
// client it moves the DOM to <body>. This causes a hydration mismatch.
// Solution: only render the Teleport after mount (client-only).
const isMounted = ref(false);

// ─── Max visible toasts ────────────────────────────────────────────────────

const MAX_VISIBLE = 5;

const visibleToasts = computed(() => toast.toasts.slice(-MAX_VISIBLE));

// Auto-dismiss oldest if over limit
watch(
  () => toast.toasts.length,
  (len) => {
    if (len > MAX_VISIBLE) {
      const oldest = toast.toasts[0];
      if (oldest) toast.dismiss(oldest.id);
    }
  },
);

// ─── Variant config ─────────────────────────────────────────────────────────

const variantConfig: Record<ToastVariant, { bg: string; border: string; icon: string; iconColor: string; progressColor: string }> = {
  success: {
    bg: "bg-green-50 dark:bg-green-950/80",
    border: "border-green-200 dark:border-green-800",
    iconColor: "text-green-600 dark:text-green-400",
    progressColor: "bg-green-500",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  error: {
    bg: "bg-red-50 dark:bg-red-950/80",
    border: "border-red-200 dark:border-red-800",
    iconColor: "text-red-600 dark:text-red-400",
    progressColor: "bg-red-500",
    icon: "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  warning: {
    bg: "bg-amber-50 dark:bg-amber-950/80",
    border: "border-amber-200 dark:border-amber-800",
    iconColor: "text-amber-600 dark:text-amber-400",
    progressColor: "bg-amber-500",
    icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
  },
  info: {
    bg: "bg-cyan-50 dark:bg-cyan-950/80",
    border: "border-cyan-200 dark:border-cyan-800",
    iconColor: "text-cyan-600 dark:text-cyan-400",
    progressColor: "bg-cyan-500",
    icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
};

function getConfig(t: Toast) {
  return variantConfig[t.variant];
}

// ─── Progress tracking ──────────────────────────────────────────────────────

/** Compute progress percentage for auto-dismiss indicator. */
function getProgress(t: Toast): number {
  if (t.duration <= 0) return 100;
  const elapsed = Date.now() - t.createdAt;
  return Math.max(0, 100 - (elapsed / t.duration) * 100);
}

// Re-render progress bars every 100ms
const now = ref(Date.now());
let rafId: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  isMounted.value = true;
  rafId = setInterval(() => {
    now.value = Date.now();
  }, 100);
});

onUnmounted(() => {
  if (rafId) clearInterval(rafId);
});

// Use now.value in a computed to make progress reactive
const progressMap = computed(() => {
  void now.value; // trigger reactivity
  const map = new Map<number, number>();
  for (const t of toast.toasts) {
    map.set(t.id, getProgress(t));
  }
  return map;
});
</script>

<template>
  <Teleport v-if="isMounted" to="body">
    <!-- Toast container — bottom-right, stacked -->
    <div
      class="fixed bottom-4 right-4 z-[100] flex flex-col-reverse gap-2 pointer-events-none"
      aria-live="polite"
      aria-atomic="true"
    >
      <TransitionGroup
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="opacity-0 translate-x-8"
        enter-to-class="opacity-100 translate-x-0"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="opacity-100 translate-x-0"
        leave-to-class="opacity-0 translate-x-8"
        move-class="transition duration-300 ease-in-out"
      >
        <div
          v-for="t in visibleToasts"
          :key="t.id"
          :class="[
            'pointer-events-auto w-80 max-w-[calc(100vw-2rem)] rounded-lg border shadow-lg overflow-hidden',
            getConfig(t).bg,
            getConfig(t).border,
          ]"
          role="alert"
        >
          <div class="flex items-start gap-3 p-3">
            <!-- Icon -->
            <svg
              :class="['h-5 w-5 flex-shrink-0 mt-0.5', getConfig(t).iconColor]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" :d="getConfig(t).icon" />
            </svg>

            <!-- Content -->
            <div class="flex-1 min-w-0">
              <p v-if="t.title" class="text-sm font-semibold text-navy-900 dark:text-navy-100">
                {{ t.title }}
              </p>
              <p class="text-sm text-navy-800 dark:text-navy-200 break-words">
                {{ t.message }}
              </p>
            </div>

            <!-- Action button (e.g. Retry) -->
            <button
              v-if="t.action"
              class="flex-shrink-0 rounded-md px-2 py-1 text-xs font-medium transition-colors"
              :class="[
                t.variant === 'error' ? 'bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/40 dark:text-red-300 dark:hover:bg-red-900/60' :
                t.variant === 'warning' ? 'bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/40 dark:text-amber-300 dark:hover:bg-amber-900/60' :
                t.variant === 'info' ? 'bg-cyan-100 text-cyan-700 hover:bg-cyan-200 dark:bg-cyan-900/40 dark:text-cyan-300 dark:hover:bg-cyan-900/60' :
                'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/40 dark:text-green-300 dark:hover:bg-green-900/60'
              ]"
              @click="t.action?.onClick(); toast.dismiss(t.id)"
            >
              {{ t.action.label }}
            </button>

            <!-- Close button -->
            <button
              class="flex-shrink-0 rounded p-0.5 text-slate-custom-500 hover:text-navy-900 dark:hover:text-navy-100 hover:bg-navy-100 dark:hover:bg-navy-800 transition-colors"
              aria-label="Dismiss notification"
              @click="toast.dismiss(t.id)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>

          <!-- Progress bar (auto-dismiss indicator) -->
          <div v-if="t.duration > 0" class="h-0.5 bg-navy-100 dark:bg-navy-800">
            <div
              :class="['h-full transition-all duration-100 ease-linear', getConfig(t).progressColor]"
              :style="{ width: `${progressMap.get(t.id) ?? 100}%` }"
            />
          </div>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
