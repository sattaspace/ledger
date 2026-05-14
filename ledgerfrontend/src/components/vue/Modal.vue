<script setup lang="ts">
/**
 * Modal — Overlay dialog with backdrop, focus trap, and keyboard dismiss.
 *
 * Features:
 *   - Focus trap: Tab key cycles within the dialog (WAI-ARIA pattern)
 *   - Auto-focus: First focusable element receives focus on open
 *   - Focus restoration: Focus returns to trigger element on close
 *   - Escape key dismiss
 *   - Body scroll lock
 *   - Backdrop click dismiss
 *   - aria-labelledby referencing the title
 *   - Teleport to body
 *   - Animated transitions
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

// ─── Responsive Size ────────────────────────────────────────────────────────

const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024);

onMounted(() => {
  const updateWidth = () => { windowWidth.value = window.innerWidth; };
  window.addEventListener('resize', updateWidth);
  onUnmounted(() => window.removeEventListener('resize', updateWidth));
});

const effectiveSizeClass = computed(() => {
  // On mobile (< 640px), override to near-full-screen
  if (typeof window !== 'undefined' && windowWidth.value < 640) {
    return 'w-[calc(100vw-1rem)] max-h-[calc(100vh-1rem)]';
  }
  return sizeMap[props.size];
});

// ─── Refs ─────────────────────────────────────────────────────────────────────

const panelRef = ref<HTMLElement | null>(null);
const titleId = computed(() => (props.title ? `modal-title-${Math.random().toString(36).slice(2, 9)}` : undefined));

// Track the element that triggered the modal so we can restore focus
let triggerElement: HTMLElement | null = null;

// ─── Focus Trap ───────────────────────────────────────────────────────────────

/** Get all focusable elements within the panel. */
function getFocusableElements(): HTMLElement[] {
  if (!panelRef.value) return [];
  const selectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ');
  return Array.from(panelRef.value.querySelectorAll(selectors));
}

/** Handle Tab key to trap focus within the modal. */
function handleTabTrap(e: KeyboardEvent) {
  if (e.key !== "Tab") return;

  const focusable = getFocusableElements();
  if (focusable.length === 0) return;

  const first = focusable[0];
  const last = focusable[focusable.length - 1];

  if (e.shiftKey) {
    // Shift+Tab: if focus is on first element, wrap to last
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    // Tab: if focus is on last element, wrap to first
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

// ─── Keyboard Dismiss ─────────────────────────────────────────────────────────

function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.closeable) {
    emit("close");
    return;
  }
  // Focus trap
  handleTabTrap(e);
}

// ─── Auto-focus & Focus Restoration ───────────────────────────────────────────

watch(
  () => props.open,
  (isOpen) => {
    if (import.meta.client) {
      if (isOpen) {
        // Save the currently focused element
        triggerElement = document.activeElement as HTMLElement;

        document.body.style.overflow = "hidden";
        document.addEventListener("keydown", handleKeydown);

        // Auto-focus the first focusable element after transition
        nextTick(() => {
          const focusable = getFocusableElements();
          if (focusable.length > 0) {
            // Skip the close button — focus the first input or interactive element
            const firstInput = focusable.find(
              (el) => el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA",
            );
            (firstInput ?? focusable[0]).focus();
          } else if (panelRef.value) {
            panelRef.value.focus();
          }
        });
      } else {
        document.body.style.overflow = "";
        document.removeEventListener("keydown", handleKeydown);

        // Restore focus to the trigger element
        nextTick(() => {
          if (triggerElement && typeof triggerElement.focus === "function") {
            triggerElement.focus();
            triggerElement = null;
          }
        });
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
            ref="panelRef"
            :class="[
              'relative w-full rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900 shadow-xl animate-scale-in',
              effectiveSizeClass,
            ]"
            role="dialog"
            aria-modal="true"
            :aria-labelledby="titleId"
            tabindex="-1"
          >
            <!-- Header -->
            <div
              v-if="title || closeable || $slots.header"
              class="flex items-center justify-between border-b border-navy-200 dark:border-navy-700 px-6 py-4"
            >
              <slot name="header">
                <h2
                  :id="titleId"
                  class="text-lg font-semibold text-navy-900 dark:text-navy-100"
                >
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
            <div class="px-6 py-4 max-h-[calc(100vh-4rem)] sm:max-h-[calc(100vh-12rem)] overflow-y-auto">
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
