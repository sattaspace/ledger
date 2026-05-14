<script setup lang="ts">
/**
 * TypeBadge — Account/transaction type indicator with icon and color.
 *
 * Displays a small badge with an icon and label for entity types
 * like account types (ASSET, LIABILITY, INVESTMENT), transaction
 * types (INCOME, EXPENSE, TRANSFER, REFUND), card types, etc.
 *
 * Usage:
 *   <TypeBadge type="INCOME" />
 *   <TypeBadge type="ASSET" :type-map="accountTypeMap" />
 */

export interface TypeStyleMap {
  [type: string]: {
    bg: string;
    text: string;
    icon?: string;
  };
}

const props = withDefaults(
  defineProps<{
    /** Type string to display. */
    type: string;
    /** Custom type-to-style mapping. */
    typeMap?: TypeStyleMap;
    /** Show type icon. */
    showIcon?: boolean;
    /** Badge size: 'sm' | 'md'. */
    size?: "sm" | "md";
  }>(),
  {
    showIcon: true,
    size: "sm",
  },
);

// ─── Transaction Type Styles ──────────────────────────────────────────────────

const transactionTypeMap: TypeStyleMap = {
  income: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", icon: "income" },
  expense: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", icon: "expense" },
  transfer: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300", icon: "transfer" },
  refund: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300", icon: "refund" },
};

// ─── Account Type Styles ──────────────────────────────────────────────────────

const accountTypeMap: TypeStyleMap = {
  asset: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", icon: "asset" },
  liability: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300", icon: "liability" },
  investment: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300", icon: "investment" },
};

// ─── Card Type Styles ─────────────────────────────────────────────────────────

const cardTypeMap: TypeStyleMap = {
  debit: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", icon: "debit" },
  credit: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300", icon: "credit" },
};

// ─── All Default Styles ───────────────────────────────────────────────────────

const allDefaultMaps: TypeStyleMap = {
  ...transactionTypeMap,
  ...accountTypeMap,
  ...cardTypeMap,
  // Debt types
  money_borrowed: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300" },
  money_lent: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  // Bill recurrence
  weekly: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  biweekly: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  monthly: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  quarterly: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  yearly: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  one_time: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

// ─── Computed ─────────────────────────────────────────────────────────────────

const resolvedStyle = computed(() => {
  const map = props.typeMap ?? allDefaultMaps;
  const key = props.type.toLowerCase();
  return (
    map[key] ?? {
      bg: "bg-slate-100 dark:bg-slate-800/50",
      text: "text-slate-700 dark:text-slate-300",
    }
  );
});

const sizeClass = computed(() =>
  props.size === "sm"
    ? "px-2 py-0.5 text-xs"
    : "px-2.5 py-1 text-sm",
);

/** Format type for display: "MONEY_BORROWED" → "Money Borrowed" */
const displayType = computed(() => {
  return props.type
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
});

// ─── Icon SVGs ────────────────────────────────────────────────────────────────

const iconType = computed(() => resolvedStyle.value.icon);
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 rounded-full font-medium whitespace-nowrap',
      resolvedStyle.bg,
      resolvedStyle.text,
      sizeClass,
    ]"
  >
    <!-- Income: arrow down-left -->
    <svg v-if="showIcon && iconType === 'income'" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M3 10a1 1 0 011-1h9.586L9.293 4.707a1 1 0 011.414-1.414l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L13.586 11H4a1 1 0 01-1-1z" clip-rule="evenodd" />
    </svg>
    <!-- Expense: arrow up-right -->
    <svg v-else-if="showIcon && iconType === 'expense'" class="h-3.5 w-3.5 rotate-180" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M3 10a1 1 0 011-1h9.586L9.293 4.707a1 1 0 011.414-1.414l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L13.586 11H4a1 1 0 01-1-1z" clip-rule="evenodd" />
    </svg>
    <!-- Transfer: swap horizontal -->
    <svg v-else-if="showIcon && iconType === 'transfer'" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path d="M8 5a1 1 0 100 2h5.586l-1.293 1.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L13.586 5H8zM12 15a1 1 0 100-2H6.414l1.293-1.293a1 1 0 10-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L6.414 15H12z" />
    </svg>
    <!-- Asset: building -->
    <svg v-else-if="showIcon && iconType === 'asset'" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2h-3a1 1 0 01-1-1v-2a1 1 0 10-2 0v2a1 1 0 01-1 1H5a1 1 0 110-2V4zm3 1a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clip-rule="evenodd" />
    </svg>
    <!-- Liability: credit card -->
    <svg v-else-if="showIcon && iconType === 'liability'" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4zM2 10v4a2 2 0 002 2h12a2 2 0 002-2v-4H2zm4 2h2a1 1 0 100-2H6a1 1 0 100 2z" />
    </svg>
    <!-- Investment: trending up -->
    <svg v-else-if="showIcon && iconType === 'investment'" class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
      <path fill-rule="evenodd" d="M12 7a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0V8.414l-4.293 4.293a1 1 0 01-1.414 0L8 10.414l-4.293 4.293a1 1 0 01-1.414-1.414l5-5a1 1 0 011.414 0L11 10.586 14.586 7H12z" clip-rule="evenodd" />
    </svg>
    {{ displayType }}
  </span>
</template>
