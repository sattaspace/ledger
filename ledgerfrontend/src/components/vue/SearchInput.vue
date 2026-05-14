<script setup lang="ts">
/**
 * SearchInput — Debounced search field with clear button.
 *
 * Emits the updated value after a configurable debounce delay.
 * Shows a search icon on the left and a clear (X) button when
 * the field has content.
 *
 * Usage:
 *   <SearchInput v-model="search" placeholder="Search transactions..." @search="handleSearch" />
 */

const props = withDefaults(
  defineProps<{
    /** Current search value (v-model). */
    modelValue?: string;
    /** Placeholder text. */
    placeholder?: string;
    /** Debounce delay in milliseconds. */
    debounceMs?: number;
    /** Input size: 'sm' | 'md'. */
    size?: "sm" | "md";
    /** Disable the input. */
    disabled?: boolean;
  }>(),
  {
    modelValue: "",
    placeholder: "Search...",
    debounceMs: 300,
    size: "md",
    disabled: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [value: string];
  search: [value: string];
  clear: [];
}>();

// ─── State ────────────────────────────────────────────────────────────────────

const localValue = ref(props.modelValue);
let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// ─── Watch external model changes ─────────────────────────────────────────────

watch(
  () => props.modelValue,
  (newVal) => {
    if (newVal !== localValue.value) {
      localValue.value = newVal;
    }
  },
);

// ─── Handlers ─────────────────────────────────────────────────────────────────

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement;
  localValue.value = target.value;
  emit("update:modelValue", target.value);

  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    emit("search", localValue.value);
  }, props.debounceMs);
}

function handleClear() {
  localValue.value = "";
  emit("update:modelValue", "");
  emit("search", "");
  emit("clear");
  if (debounceTimer) clearTimeout(debounceTimer);
}

// ─── Size Classes ─────────────────────────────────────────────────────────────

const sizeClass = computed(() =>
  props.size === "sm" ? "h-8 text-sm pl-8 pr-8" : "h-10 text-sm pl-10 pr-10",
);

const iconSize = computed(() =>
  props.size === "sm" ? "h-4 w-4 left-2.5" : "h-5 w-5 left-3",
);

const clearIconSize = computed(() =>
  props.size === "sm" ? "h-3.5 w-3.5 right-2.5" : "h-4 w-4 right-3",
);

// ─── Cleanup ──────────────────────────────────────────────────────────────────

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer);
});
</script>

<template>
  <div class="relative w-full">
    <!-- Search Icon -->
    <svg
      :class="['absolute top-1/2 -translate-y-1/2 text-slate-custom-400 pointer-events-none', iconSize]"
      viewBox="0 0 20 20"
      fill="currentColor"
    >
      <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
    </svg>

    <!-- Input -->
    <input
      type="text"
      :value="localValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :class="[
        'input-field w-full',
        sizeClass,
        disabled ? 'opacity-50 cursor-not-allowed' : '',
      ]"
      @input="handleInput"
    />

    <!-- Clear Button -->
    <button
      v-if="localValue.length > 0 && !disabled"
      :class="[
        'absolute top-1/2 -translate-y-1/2 text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 transition-colors',
        clearIconSize,
      ]"
      type="button"
      aria-label="Clear search"
      @click="handleClear"
    >
      <svg viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
      </svg>
    </button>
  </div>
</template>
