<script setup lang="ts">
/**
 * Permission Guard Component
 *
 * Conditionally renders content based on user's access permissions.
 * Uses the access map from /billing/auth/me instead of hardcoded roles.
 *
 * Usage:
 * ```vue
 * <PermissionGuard feature="reports">
 *   <ReportsPanel />
 * </PermissionGuard>
 *
 * <PermissionGuard :any="['sales', 'inventory']">
 *   <DashboardWidget />
 * </PermissionGuard>
 *
 * <PermissionGuard :all="['reports', 'export_pdf']">
 *   <ExportButton />
 * </PermissionGuard>
 * ```
 */
import { computed, watch } from 'vue';
import { useAccess } from '../composables/useAccess';

const props = defineProps<{
  /** Single feature key to check (e.g., 'reports', 'suppliers') */
  feature?: string;
  /** Any of these features grants access */
  any?: string[];
  /** All of these features required for access */
  all?: string[];
  /** Fallback text to show when access denied */
  fallback?: string;
}>();

const { hasAccess, access } = useAccess();

const canAccess = computed(() => {
  // Single feature check
  if (props.feature) {
    const result = hasAccess(props.feature).value;
    console.log(`%c[PERMISSION GUARD] Checking feature="${props.feature}"`, 'color: #f59e0b;', {
      feature: props.feature,
      result,
      accessMap: access.value
    });
    return result;
  }

  // Any of the features
  if (props.any && props.any.length > 0) {
    const result = props.any.some(feature => hasAccess(feature).value);
    console.log(`%c[PERMISSION GUARD] Checking any="${props.any.join(', ')}"`, 'color: #f59e0b;', {
      any: props.any,
      result
    });
    return result;
  }

  // All of the features
  if (props.all && props.all.length > 0) {
    const result = props.all.every(feature => hasAccess(feature).value);
    console.log(`%c[PERMISSION GUARD] Checking all="${props.all.join(', ')}"`, 'color: #f59e0b;', {
      all: props.all,
      result
    });
    return result;
  }

  // No condition specified - deny by default
  console.warn('%c[PERMISSION GUARD] No condition specified - denying access by default', 'color: #ef4444;');
  return false;
});

// Debug: Log when canAccess changes
watch(canAccess, (newVal) => {
  console.log(`%c[PERMISSION GUARD] canAccess changed for feature="${props.feature}"`, 'color: #10b981;', newVal);
}, { immediate: true });
</script>

<template>
  <div v-if="canAccess">
    <slot />
  </div>
  <div v-else-if="fallback" class="text-slate-400 text-sm">
    {{ fallback }}
  </div>
</template>
