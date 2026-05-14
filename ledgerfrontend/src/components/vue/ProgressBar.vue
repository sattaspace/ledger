<script setup lang="ts">
/**
 * ProgressBar — Horizontal progress bar for budgets, goals, and debt.
 *
 * Usage:
 *   <ProgressBar :value="65" :max="100" color="cyan" show-label />
 *   <ProgressBar :value="spentAmount" :max="budgetAmount" color="amber" />
 */

const props = withDefaults(
  defineProps<{
    /** Current value. */
    value: number;
    /** Maximum value (denominator). */
    max: number;
    /** Bar color: named color or CSS value. */
    color?: "cyan" | "green" | "amber" | "red" | "navy";
    /** Show percentage label. */
    showLabel?: boolean;
    /** Show value/max text. */
    showValues?: boolean;
    /** Bar height: 'sm' | 'md' | 'lg'. */
    size?: "sm" | "md" | "lg";
    /** Animate the bar on value change. */
    animate?: boolean;
  }>(),
  {
    color: "cyan",
    showLabel: false,
    showValues: false,
    size: "md",
    animate: true,
  },
);

// ─── Computed ─────────────────────────────────────────────────────────────────

const percentage = computed(() => {
  if (props.max === 0) return 0;
  return Math.min(Math.round((props.value / props.max) * 100), 100);
});

const colorClass = computed(() => {
  switch (props.color) {
    case "cyan":
      return "bg-cyan-600 dark:bg-cyan-500";
    case "green":
      return "bg-credit";
    case "amber":
      return "bg-amber-500 dark:bg-amber-400";
    case "red":
      return "bg-debit";
    case "navy":
      return "bg-navy-700 dark:bg-navy-500";
    default:
      return "bg-cyan-600 dark:bg-cyan-500";
  }
});

const trackClass = computed(() => {
  switch (props.size) {
    case "sm":
      return "h-1.5";
    case "md":
      return "h-2.5";
    case "lg":
      return "h-4";
    default:
      return "h-2.5";
  }
});

/** Automatically switch to red when over 100% */
const effectiveColorClass = computed(() => {
  if (percentage.value >= 100) return "bg-debit";
  return colorClass.value;
});
</script>

<template>
  <div class="w-full">
    <!-- Label Row -->
    <div
      v-if="showLabel || showValues"
      class="flex items-center justify-between text-sm mb-1"
    >
      <span v-if="showValues" class="text-slate-custom-600 dark:text-slate-custom-400">
        {{ value.toLocaleString() }} / {{ max.toLocaleString() }}
      </span>
      <span
        v-if="showLabel"
        :class="[
          'font-medium',
          percentage >= 100
            ? 'text-debit'
            : 'text-navy-900 dark:text-navy-100',
        ]"
      >
        {{ percentage }}%
      </span>
    </div>

    <!-- Track -->
    <div
      :class="[
        'w-full rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden',
        trackClass,
      ]"
    >
      <!-- Fill -->
      <div
        :class="[
          'h-full rounded-full transition-all duration-500 ease-out',
          effectiveColorClass,
          animate ? '' : 'transition-none',
        ]"
        :style="{ width: `${Math.min(percentage, 100)}%` }"
        role="progressbar"
        :aria-valuenow="value"
        :aria-valuemin="0"
        :aria-valuemax="max"
      />
    </div>
  </div>
</template>
