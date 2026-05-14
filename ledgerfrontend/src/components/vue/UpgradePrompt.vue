<script setup lang="ts">
/**
 * UpgradePrompt — Shows an upgrade prompt when plan limits are reached.
 *
 * Displays a visually distinct card prompting the user to upgrade their
 * plan when they've hit the maximum allowed items for a feature.
 *
 * Usage:
 *   <UpgradePrompt feature="budgets" :current="5" :maximum="5" />
 *   <UpgradePrompt feature="investments" :current="3" :maximum="3" />
 */
withDefaults(defineProps<{
  /** Feature name to display (e.g. "budgets", "investments"). */
  feature?: string
  /** Current count of items. */
  current?: number
  /** Maximum allowed on the current plan. */
  maximum?: number
}>(), {
  feature: 'this feature',
  current: 0,
  maximum: 0,
})
</script>

<template>
  <div class="flex flex-col items-center justify-center p-6 text-center rounded-xl border border-dashed border-cyan-300 dark:border-cyan-700 bg-cyan-50/50 dark:bg-cyan-950/20">
    <svg class="h-10 w-10 text-cyan-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
    <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 mb-1">Limit Reached</h3>
    <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mb-3">
      You've used {{ current }} of {{ maximum }} {{ feature }}. Upgrade for more.
    </p>
    <a href="/billing" class="btn-primary text-sm">Upgrade Plan</a>
  </div>
</template>
