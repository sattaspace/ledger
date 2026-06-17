<script setup lang="ts">
/**
 * Permission Guard Component
 *
 * Conditionally renders content based on user's access permissions.
 * Uses TWO layers of permission checking:
 *
 *   1. Plan-level access (useAccess): Does the DEALER's subscription
 *      include this feature? (e.g., "suppliers", "reports")
 *
 *   2. DSR module permissions (useDsrPermissions): Does the DSR have
 *      the specific module:action permission? (e.g., "sales.view",
 *      "inventory.edit")
 *
 * For dealers, all checks pass through (dealers have full access).
 * For DSRs/Collectors, both layers must pass for the content to render.
 *
 * Usage:
 * ```vue
 * <!-- Plan-level check only (dealer subscription feature) -->
 * <PermissionGuard feature="reports">
 *   <ReportsPanel />
 * </PermissionGuard>
 *
 * <!-- DSR module + action check (granular DSR permission) -->
 * <PermissionGuard module="sales" action="edit">
 *   <CreateSaleButton />
 * </PermissionGuard>
 *
 * <!-- DSR module view check (any access to module) -->
 * <PermissionGuard module="inventory">
 *   <InventoryPanel />
 * </PermissionGuard>
 *
 * <!-- Any of multiple features -->
 * <PermissionGuard :any="['sales', 'inventory']">
 *   <DashboardWidget />
 * </PermissionGuard>
 * ```
 */
import { computed, watch } from 'vue';
import { useAccess } from '../composables/useAccess';
import { useDsrPermissions } from '../composables/useDsrPermissions';

const props = defineProps<{
  /** Single plan-level feature key to check (e.g., 'reports', 'suppliers') */
  feature?: string;
  /** DSR module to check (e.g., 'sales', 'inventory') */
  module?: string;
  /** DSR action within module (e.g., 'view', 'edit', 'delete'). Default: 'view' */
  action?: string;
  /** Any of these plan-level features grants access */
  any?: string[];
  /** All of these plan-level features required for access */
  all?: string[];
  /** Fallback text to show when access denied */
  fallback?: string;
}>();

const { hasAccess, access } = useAccess();
const { canView, canEdit, canDelete, hasPermission, isDealer: isDsrDealer } = useDsrPermissions();

const canAccess = computed(() => {
  // Determine which check to apply
  const hasCondition = !!(
    props.feature ||
    props.module ||
    (props.any && props.any.length > 0) ||
    (props.all && props.all.length > 0)
  );

  if (!hasCondition) {
    const msg = '[PermissionGuard] No condition prop provided (feature/module/any/all). Denying by default.';
    if (import.meta.env.DEV) {
      console.error(msg);
      throw new Error(msg);
    }
    console.warn(msg);
    return false;
  }

  // ─── DSR Module Permission Check ──────────────────────────────────
  // If `module` is specified, check DSR-level permissions.
  // For dealers, this always returns true.
  if (props.module) {
    const action = props.action || 'view';
    const moduleResult = hasPermission(props.module, action).value;

    if (import.meta.env.DEV) {
      console.log(`%c[PERMISSION GUARD] Checking module="${props.module}" action="${action}"`, 'color: #8b5cf6;', {
        module: props.module,
        action,
        result: moduleResult,
        isDealer: isDsrDealer.value,
      });
    }

    // If a plan-level feature is ALSO specified, both must pass
    if (props.feature) {
      const featureResult = hasAccess(props.feature).value;
      return moduleResult && featureResult;
    }

    return moduleResult;
  }

  // ─── Plan-Level Feature Check ─────────────────────────────────────
  // These check the dealer's subscription access (from billing/auth/me).

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

// Debug: Log when canAccess changes (dev only)
watch(canAccess, (newVal) => {
  if (import.meta.env.DEV) {
    console.log(`%c[PERMISSION GUARD] canAccess changed`, 'color: #10b981;', {
      feature: props.feature,
      module: props.module,
      action: props.action,
      result: newVal,
    });
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
