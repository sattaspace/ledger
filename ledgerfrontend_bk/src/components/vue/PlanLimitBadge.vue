<script setup lang="ts">
/**
 * PlanLimitBadge — Shows current count / max limit for a feature.
 *
 * Displays "3/3" when at limit (with upgrade link) or "2/3" when under limit.
 * When max is 0 (unlimited), shows nothing.
 */
import { computed } from "vue";
import { useAccess } from "@/composables/useAccess";

const props = defineProps<{
  /** The max_* key from the access map (e.g., "max_accounts") */
  maxKey: string;
  /** The boolean feature key (e.g., "accounts") */
  featureKey?: string;
  /** Current count of items */
  current: number;
}>();

const { getLimit, hasAccess } = useAccess();

const maxLimit = getLimit(props.maxKey);
const featureEnabled = props.featureKey ? hasAccess(props.featureKey) : computed(() => true);

const isUnlimited = computed(() => maxLimit.value === 0);
const isAtLimit = computed(() => !isUnlimited.value && props.current >= maxLimit.value);
const showBadge = computed(() => featureEnabled.value && !isUnlimited.value);
</script>

<template>
  <span v-if="showBadge" class="inline-flex items-center gap-1 text-xs">
    <span
      :class="[
        'font-medium',
        isAtLimit
          ? 'text-amber-600 dark:text-amber-400'
          : 'text-slate-custom-500 dark:text-slate-custom-400'
      ]"
    >
      {{ current }}/{{ maxLimit }}
    </span>
    <a
      v-if="isAtLimit"
      href="/dashboard/upgrade"
      class="text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300 font-medium underline"
    >
      Upgrade
    </a>
  </span>
</template>
