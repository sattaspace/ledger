<script setup lang="ts">
/**
 * StatusBadge — Colored status pill for entity states.
 *
 * Displays a small colored badge with optional dot indicator.
 * Supports custom color maps for any status enum.
 *
 * Usage:
 *   <StatusBadge status="ACTIVE" />
 *   <StatusBadge status="PAID" :color-map="invoiceStatusColors" />
 */

export interface StatusColorMap {
  [status: string]: {
    bg: string;
    text: string;
    dot?: string;
  };
}

const props = withDefaults(
  defineProps<{
    /** Status string to display and color. */
    status: string;
    /** Custom color mapping. Keys are status strings (case-insensitive). */
    colorMap?: StatusColorMap;
    /** Show the leading dot indicator. */
    showDot?: boolean;
    /** Badge size: 'sm' | 'md'. */
    size?: "sm" | "md";
  }>(),
  {
    showDot: true,
    size: "sm",
  },
);

// ─── Default Color Map ────────────────────────────────────────────────────────

const defaultColorMap: StatusColorMap = {
  // Active / positive
  active: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  paid: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  cleared: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  viewed: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300", dot: "bg-cyan-500" },
  sent: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300", dot: "bg-blue-500" },

  // Pending / neutral
  pending: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300", dot: "bg-amber-500" },
  draft: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300", dot: "bg-slate-400" },
  partial: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300", dot: "bg-amber-500" },

  // Paused / inactive
  paused: { bg: "bg-yellow-100 dark:bg-yellow-950/50", text: "text-yellow-800 dark:text-yellow-300", dot: "bg-yellow-500" },
  inactive: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300", dot: "bg-slate-400" },

  // Negative / danger
  cancelled: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
  overdue: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
  void: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
  deleted: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", dot: "bg-red-500" },
};

// ─── Computed ─────────────────────────────────────────────────────────────────

const resolvedColors = computed(() => {
  const map = props.colorMap ?? defaultColorMap;
  const key = props.status.toLowerCase();
  return (
    map[key] ?? {
      bg: "bg-slate-100 dark:bg-slate-800/50",
      text: "text-slate-700 dark:text-slate-300",
      dot: "bg-slate-400",
    }
  );
});

const sizeClass = computed(() =>
  props.size === "sm"
    ? "px-2 py-0.5 text-xs"
    : "px-2.5 py-1 text-sm",
);

/** Format status for display: "ACTIVE" → "Active" */
const displayStatus = computed(() => {
  return props.status
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
});
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 rounded-full font-medium whitespace-nowrap',
      resolvedColors.bg,
      resolvedColors.text,
      sizeClass,
    ]"
  >
    <span
      v-if="showDot"
      :class="['h-1.5 w-1.5 rounded-full flex-shrink-0', resolvedColors.dot]"
    />
    {{ displayStatus }}
  </span>
</template>
