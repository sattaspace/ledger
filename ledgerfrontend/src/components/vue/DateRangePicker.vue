<script setup lang="ts">
/**
 * DateRangePicker — From/To date inputs with preset quick ranges.
 *
 * Provides a pair of date inputs with preset buttons for common
 * date ranges like "This Month", "Last 30 Days", etc.
 *
 * Usage:
 *   <DateRangePicker
 *     :from="filters.date_from"
 *     :to="filters.date_to"
 *     @change="handleDateRange"
 *   />
 */

export interface DateRange {
  from: string;
  to: string;
}

export interface DatePreset {
  label: string;
  from: () => string;
  to: () => string;
}

const props = withDefaults(
  defineProps<{
    /** Start date (ISO YYYY-MM-DD). */
    from?: string;
    /** End date (ISO YYYY-MM-DD). */
    to?: string;
    /** Preset configurations. */
    presets?: DatePreset[];
    /** Disable the inputs. */
    disabled?: boolean;
    /** Show preset buttons. */
    showPresets?: boolean;
  }>(),
  {
    from: "",
    to: "",
    disabled: false,
    showPresets: true,
  },
);

const emit = defineEmits<{
  change: [range: DateRange];
}>();

// ─── State ────────────────────────────────────────────────────────────────────

const localFrom = ref(props.from);
const localTo = ref(props.to);

watch(() => props.from, (v) => { localFrom.value = v; });
watch(() => props.to, (v) => { localTo.value = v; });

// ─── Default Presets ──────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().split("T")[0];
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split("T")[0];
}

function startOfMonth(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), 1).toISOString().split("T")[0];
}

function endOfMonth(): string {
  const d = new Date();
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).toISOString().split("T")[0];
}

function startOfYear(): string {
  return `${new Date().getFullYear()}-01-01`;
}

const defaultPresets: DatePreset[] = [
  { label: "Today", from: () => today(), to: () => today() },
  { label: "Last 7 Days", from: () => daysAgo(7), to: () => today() },
  { label: "Last 30 Days", from: () => daysAgo(30), to: () => today() },
  { label: "Last 90 Days", from: () => daysAgo(90), to: () => today() },
  { label: "This Month", from: startOfMonth, to: endOfMonth },
  { label: "This Year", from: startOfYear, to: () => today() },
];

const activePresets = computed(() => props.presets ?? defaultPresets);

// ─── Active Preset Label ──────────────────────────────────────────────────────

const activePresetLabel = computed(() => {
  for (const preset of activePresets.value) {
    if (preset.from() === localFrom.value && preset.to() === localTo.value) {
      return preset.label;
    }
  }
  return "";
});

// ─── Handlers ─────────────────────────────────────────────────────────────────

function handleFromChange(event: Event) {
  localFrom.value = (event.target as HTMLInputElement).value;
  emit("change", { from: localFrom.value, to: localTo.value });
}

function handleToChange(event: Event) {
  localTo.value = (event.target as HTMLInputElement).value;
  emit("change", { from: localFrom.value, to: localTo.value });
}

function applyPreset(preset: DatePreset) {
  localFrom.value = preset.from();
  localTo.value = preset.to();
  emit("change", { from: localFrom.value, to: localTo.value });
}

function clearRange() {
  localFrom.value = "";
  localTo.value = "";
  emit("change", { from: "", to: "" });
}
</script>

<template>
  <div class="space-y-2">
    <!-- Preset Buttons -->
    <div v-if="showPresets" class="flex flex-wrap gap-1.5">
      <button
        v-for="preset in activePresets"
        :key="preset.label"
        :class="[
          'rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
          activePresetLabel === preset.label
            ? 'bg-cyan-600 text-white'
            : 'bg-navy-100 dark:bg-navy-800 text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-700',
        ]"
        :disabled="disabled"
        @click="applyPreset(preset)"
      >
        {{ preset.label }}
      </button>
    </div>

    <!-- Date Inputs -->
    <div class="flex items-center gap-2">
      <div class="flex-1">
        <label class="label-text sr-only">From</label>
        <input
          type="date"
          :value="localFrom"
          :disabled="disabled"
          class="input-field h-10 w-full"
          @change="handleFromChange"
        />
      </div>
      <span class="text-slate-custom-500 text-sm">to</span>
      <div class="flex-1">
        <label class="label-text sr-only">To</label>
        <input
          type="date"
          :value="localTo"
          :disabled="disabled"
          class="input-field h-10 w-full"
          @change="handleToChange"
        />
      </div>
      <!-- Clear -->
      <button
        v-if="localFrom || localTo"
        class="btn-ghost rounded-lg p-2 text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100"
        title="Clear date range"
        @click="clearRange"
      >
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
  </div>
</template>
