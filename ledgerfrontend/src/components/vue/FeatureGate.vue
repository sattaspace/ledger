<script setup lang="ts">
/**
 * FeatureGate — Conditionally renders content based on feature access.
 *
 * Uses the useAccess composable to check if the current user has access
 * to a specific feature. Supports both boolean access checks and numeric
 * limit checks (e.g. "you can create up to 5 budgets on the free plan").
 *
 * Usage:
 *   <FeatureGate feature="investments">
 *     <InvestmentsPage />
 *   </FeatureGate>
 *
 *   <FeatureGate feature="budgets" :limit="5" :current="budgetStore.items.length">
 *     <BudgetForm />
 *     <template #limit-reached>
 *       <UpgradePrompt feature="budgets" :current="5" :maximum="5" />
 *     </template>
 *   </FeatureGate>
 *
 *   <FeatureGate feature="vault" show-fallback>
 *     <VaultPage />
 *   </FeatureGate>
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useAccess } from '@/composables/useAccess'

const props = withDefaults(defineProps<{
  /** Feature key to check (e.g. 'investments', 'budgets'). */
  feature: string
  /** Max allowed items (for limit checks). Overrides the server-defined limit if provided. */
  limit?: number
  /** Current item count (for limit checks). */
  current?: number
  /** Show a fallback message when access is denied. */
  showFallback?: boolean
}>(), {
  limit: undefined,
  current: undefined,
  showFallback: false,
})

const { hasAccess, getLimit } = useAccess()

const canAccess = computed(() => hasAccess(props.feature).value)

const limitReached = computed(() => {
  if (props.limit === undefined || props.current === undefined) return false
  const maxAllowed = getLimit(props.feature, props.limit).value
  return props.current >= maxAllowed
})
</script>

<template>
  <slot v-if="canAccess && !limitReached" />
  <slot v-else-if="canAccess && limitReached" name="limit-reached" />
  <slot v-else name="no-access">
    <div v-if="showFallback" class="flex flex-col items-center justify-center p-8 text-center">
      <svg class="h-12 w-12 text-slate-custom-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
      <h3 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-1">Premium Feature</h3>
      <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">Upgrade your plan to access this feature.</p>
    </div>
  </slot>
</template>
