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
  // FIX A-5 (Phase A — CRIT-5): guard against missing conditions.
  // A PermissionGuard with no `feature`/`any`/`all` previously emitted a
  // console.warn and denied access silently — easy to ship a broken gate
  // that looks like an intentional deny. We now throw in dev so the bug
  // is caught immediately at render time, and in production we still
  // deny (safer default) but log the violation.
  const hasAny = !!(props.feature || (props.any && props.any.length > 0) || (props.all && props.all.length > 0));
  if (!hasAny) {
    const msg = '[PermissionGuard] No condition prop provided (feature/any/all). Denying by default.';
    if (import.meta.env.DEV) {
      console.error(msg);
      // Throw so the dev sees the broken template at render time, not
      // 5 minutes later when they wonder why a section is empty.
      throw new Error(msg);
    }
    console.warn(msg);
    return false;
  }

  // Also warn if multiple condition props are set — only one is evaluated.
  const definedCount = [props.feature, props.any?.length, props.all?.length]
    .filter((v) => v !== undefined && v !== null && v !== 0).length;
  if (definedCount > 1) {
    const msg = `[PermissionGuard] Multiple condition props provided (feature=${props.feature}, any=${props.any?.join(',')}, all=${props.all?.join(',')}). Only feature is checked.`;
    if (import.meta.env.DEV) console.error(msg);
    else console.warn(msg);
  }

  // Single feature check (takes priority over any/all if multiple set).
  if (props.feature) {
    const result = hasAccess(props.feature).value;
    if (import.meta.env.DEV) {
      console.log(`%c[PERMISSION GUARD] Checking feature="${props.feature}"`, 'color: #f59e0b;', {
        feature: props.feature,
        result,
        accessMap: access.value
      });
    }
    return result;
  }

  // Any of the features
  if (props.any && props.any.length > 0) {
    const result = props.any.some(feature => hasAccess(feature).value);
    if (import.meta.env.DEV) {
      console.log(`%c[PERMISSION GUARD] Checking any="${props.any.join(', ')}"`, 'color: #f59e0b;', {
        any: props.any,
        result
      });
    }
    return result;
  }

  // All of the features (props.all is guaranteed non-empty here by the guard above).
  const result = props.all!.every(feature => hasAccess(feature).value);
  if (import.meta.env.DEV) {
    console.log(`%c[PERMISSION GUARD] Checking all="${props.all!.join(', ')}"`, 'color: #f59e0b;', {
      all: props.all,
      result
    });
  }
  return result;
});

// Debug: Log when canAccess changes (dev only — was leaking access map in prod)
watch(canAccess, (newVal) => {
  if (import.meta.env.DEV) {
    console.log(`%c[PERMISSION GUARD] canAccess changed for feature="${props.feature}"`, 'color: #10b981;', newVal);
  }
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
