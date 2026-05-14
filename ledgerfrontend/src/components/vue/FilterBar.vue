<script setup lang="ts">
/**
 * FilterBar — Horizontal filter strip with reset.
 *
 * Renders a row of filter controls (search, selects, date pickers)
 * with a reset button. Designed to work with Pinia store filters.
 *
 * Usage:
 *   <FilterBar :filters="filterConfig" @filter-change="handleFilter" @reset="resetFilters" />
 */

export interface FilterOption {
  label: string;
  value: string | number | boolean;
}

export interface FilterConfig {
  /** Unique key matching the store filter property. */
  key: string;
  /** Display label. */
  label: string;
  /** Filter type: 'search' | 'select' | 'date' | 'date-range' | 'toggle'. */
  type: "search" | "select" | "date" | "date-range" | "toggle";
  /** Options for 'select' type. */
  options?: FilterOption[];
  /** Placeholder text. */
  placeholder?: string;
}

const props = withDefaults(
  defineProps<{
    /** Filter configuration array. */
    filters: FilterConfig[];
    /** Current filter values (key → value). */
    modelValue?: Record<string, unknown>;
    /** Show reset button. */
    showReset?: boolean;
    /** Show search debounce indicator. */
    loading?: boolean;
  }>(),
  {
    modelValue: () => ({}),
    showReset: true,
    loading: false,
  },
);

const emit = defineEmits<{
  "update:modelValue": [values: Record<string, unknown>];
  "filter-change": [key: string, value: unknown];
  reset: [];
  search: [query: string];
}>();

// ─── Local State ──────────────────────────────────────────────────────────────

const localValues = ref<Record<string, unknown>>({ ...props.modelValue });
let searchTimer: ReturnType<typeof setTimeout> | null = null;

watch(
  () => props.modelValue,
  (newVal) => {
    localValues.value = { ...newVal };
  },
  { deep: true },
);

// ─── Handlers ─────────────────────────────────────────────────────────────────

function updateFilter(key: string, value: unknown) {
  localValues.value[key] = value;
  emit("update:modelValue", { ...localValues.value });
  emit("filter-change", key, value);
}

function handleSearchInput(key: string, event: Event) {
  const value = (event.target as HTMLInputElement).value;
  localValues.value[key] = value;
  emit("update:modelValue", { ...localValues.value });

  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    emit("search", value);
    emit("filter-change", key, value);
  }, 300);
}

function handleReset() {
  localValues.value = {};
  emit("update:modelValue", {});
  emit("reset");
}

function hasActiveFilters(): boolean {
  return Object.values(localValues.value).some(
    (v) => v !== undefined && v !== null && v !== "" && v !== false,
  );
}

onUnmounted(() => {
  if (searchTimer) clearTimeout(searchTimer);
});
</script>

<template>
  <div class="flex flex-wrap items-center gap-3">
    <!-- Filter Controls -->
    <template v-for="filter in filters" :key="filter.key">
      <!-- Search -->
      <div v-if="filter.type === 'search'" class="relative min-w-[200px]">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-custom-400 pointer-events-none" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
        </svg>
        <input
          type="text"
          :value="localValues[filter.key] ?? ''"
          :placeholder="filter.placeholder ?? 'Search...'"
          class="input-field h-10 pl-10 pr-4 w-full"
          @input="handleSearchInput(filter.key, $event)"
        />
      </div>

      <!-- Select -->
      <select
        v-else-if="filter.type === 'select'"
        :value="localValues[filter.key] ?? ''"
        class="input-field h-10 min-w-[140px]"
        @change="updateFilter(filter.key, ($event.target as HTMLSelectElement).value)"
      >
        <option value="">{{ filter.placeholder ?? `All ${filter.label}` }}</option>
        <option
          v-for="opt in filter.options"
          :key="String(opt.value)"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>

      <!-- Date -->
      <input
        v-else-if="filter.type === 'date'"
        type="date"
        :value="localValues[filter.key] ?? ''"
        class="input-field h-10 min-w-[140px]"
        @change="updateFilter(filter.key, ($event.target as HTMLInputElement).value)"
      />

      <!-- Toggle -->
      <label
        v-else-if="filter.type === 'toggle'"
        class="inline-flex items-center gap-2 cursor-pointer text-sm text-navy-900 dark:text-navy-100"
      >
        <input
          type="checkbox"
          :checked="!!localValues[filter.key]"
          class="h-4 w-4 rounded border-navy-300 text-cyan-600 focus:ring-cyan-500"
          @change="updateFilter(filter.key, ($event.target as HTMLInputElement).checked)"
        />
        {{ filter.label }}
      </label>
    </template>

    <!-- Loading Indicator -->
    <svg
      v-if="loading"
      class="h-4 w-4 animate-spin text-cyan-600"
      viewBox="0 0 24 24"
      fill="none"
    >
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>

    <!-- Reset Button -->
    <button
      v-if="showReset && hasActiveFilters()"
      class="btn-ghost text-sm text-slate-custom-500 hover:text-navy-900 dark:hover:text-navy-100"
      @click="handleReset"
    >
      <svg class="h-4 w-4 mr-1 inline" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
      Reset
    </button>
  </div>
</template>
