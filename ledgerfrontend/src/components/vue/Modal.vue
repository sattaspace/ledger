<script setup lang="ts">
/**
 * Modal — Overlay dialog with backdrop, focus trap, and keyboard dismiss.
 *
 * Usage:
 *   <Modal :open="showModal" title="Edit Institution" @close="showModal = false">
 *     <template #body>...</template>
 *     <template #footer>...</template>
 *   </Modal>
 */

const props = withDefaults(
  defineProps<{
    /** Whether the modal is visible. */
    open: boolean;
    /** Modal title displayed in the header. */
    title?: string;
    /** Size variant: 'sm' | 'md' | 'lg' | 'xl' | 'full'. */
    size?: "sm" | "md" | "lg" | "xl" | "full";
    /** Show the close button in the header. */
    closeable?: boolean;
  }>(),
  {
    title: "",
    size: "md",
    closeable: true,
  },
);

const emit = defineEmits<{
  close: [];
}>();

// ─── Size Map ─────────────────────────────────────────────────────────────────

const sizeMap: Record<string, string> = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
  full: "max-w-[calc(100vw-2rem)]",
};

// ─── Keyboard Dismiss ─────────────────────────────────────────────────────────

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.closeable) {
    emit("close");
  }
}

// ─── Body Scroll Lock ─────────────────────────────────────────────────────────

watch(
  () => props.open,
  (isOpen) => {
    if (import.meta.client) {
      if (isOpen) {
        document.body.style.overflow = "hidden";
        document.addEventListener("keydown", handleKeydown);
      } else {
        document.body.style.overflow = "";
        document.removeEventListener("keydown", handleKeydown);
      }
    }
  },
);

onUnmounted(() => {
  if (import.meta.client) {
    document.body.style.overflow = "";
    document.removeEventListener("keydown", handleKeydown);
  }
});
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <!-- Backdrop -->
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-center justify-center bg-navy-950/60 backdrop-blur-sm"
        @click.self="closeable && emit('close')"
      >
        <!-- Panel -->
        <Transition
          enter-active-class="transition duration-200 ease-out"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition duration-150 ease-in"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div
            v-if="open"
            :class="[
              'relative w-full rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900 shadow-xl animate-scale-in',
              sizeMap[size],
            ]"
            role="dialog"
            aria-modal="true"
            :aria-label="title"
          >
            <!-- Header -->
            <div
              v-if="title || closeable || $slots.header"
              class="flex items-center justify-between border-b border-navy-200 dark:border-navy-700 px-6 py-4"
            >
              <slot name="header">
                <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">
                  {{ title }}
                </h2>
              </slot>
              <button
                v-if="closeable"
                class="ml-4 rounded-lg p-1 text-slate-custom-500 hover:text-navy-900 dark:hover:text-navy-100 hover:bg-navy-100 dark:hover:bg-navy-800 transition-colors"
                aria-label="Close"
                @click="emit('close')"
              >
                <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>

            <!-- Body -->
            <div class="px-6 py-4 max-h-[calc(100vh-12rem)] overflow-y-auto">
              <slot name="body" />
              <slot />
            </div>

            <!-- Footer -->
            <div
              v-if="$slots.footer"
              class="flex items-center justify-end gap-3 border-t border-navy-200 dark:border-navy-700 px-6 py-4"
            >
              <slot name="footer" />
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
