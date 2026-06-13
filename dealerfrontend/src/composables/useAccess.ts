/**
 * useAccess — reactive feature-access checking composable.
 *
 * Provides convenient methods to check the current user's access
 * permissions based on the access map returned by billing.auth.me().
 *
 * This replaces the old usePermissions pattern. Instead of hardcoded roles
 * and permissions, access is determined by the subscription plan's access entries
 * configured in SattaBase billing system.
 *
 * Usage:
 *   const { hasAccess, getAccess, getLimit, accessKeys } = useAccess();
 *
 *   // Template guard
 *   if (hasAccess("reports").value) { showReports(); }
 *
 *   // Typed value retrieval
 *   const maxProducts = getAccess<number>("max_products", 50);
 *
 *   // Numeric limit helper
 *   const maxDsrs = getLimit("max_dsrs", 1);
 *
 *   // List all available keys
 *   console.log(accessKeys.value);  // ["dashboard", "reports", "max_products", ...]
 */

import { computed, type ComputedRef, ref } from "vue";
import { getAccessToken } from "../lib/api";

// ─── Access Map State ────────────────────────────────────────────────────────

/**
 * Global reactive access map state.
 * This is populated when the user logs in and fetches their profile.
 */
const accessMap = ref<Record<string, boolean | number | string>>({});
const isLoadingAccess = ref(false);

/**
 * Update the access map (called by useAuth after fetching /billing/auth/me)
 */
export function setAccessMap(
  access: Record<string, boolean | number | string>,
): void {
  console.log(
    "%c[ACCESS] setAccessMap called",
    "color: #8b5cf6; font-weight: bold",
    {
      keys: Object.keys(access),
      access,
    },
  );
  accessMap.value = access;
}

/**
 * Clear the access map (called on logout)
 */
export function clearAccessMap(): void {
  accessMap.value = {};
}

// ─── useAccess Composable ────────────────────────────────────────────────────

/**
 * Reactive access checking composable.
 *
 * @example
 * ```vue
 * <script setup>
 * import { useAccess } from '../composables/useAccess';
 *
 * const { hasAccess, getAccess, getLimit } = useAccess();
 *
 * // Check if user has access to a feature
 * const canViewReports = hasAccess('reports');
 * const canManageSuppliers = hasAccess('suppliers');
 *
 * // Get numeric limits
 * const maxProducts = getLimit('max_products', 50);
 * const maxDsrs = getLimit('max_dsrs', 1);
 * </script>
 *
 * <template>
 *   <div v-if="canViewReports.value">
 *     <ReportsPanel />
 *   </div>
 * </template>
 * ```
 */
export function useAccess() {
  /**
   * Reactive boolean — true when the given access key exists
   * and its value is truthy. Automatically recomputes when the
   * access map changes (e.g. after a plan change or billing return).
   *
   * Supports boolean, number, and string values:
   *   - boolean true  → true
   *   - number  > 0   → true
   *   - string truthy → true (everything except "", "false", "0")
   */
  function hasAccess(key: string): ComputedRef<boolean> {
    return computed(() => {
      const value = accessMap.value[key];
      const result = (() => {
        if (value === undefined || value === null) return false;
        if (typeof value === "boolean") return value;
        if (typeof value === "number") return value > 0;
        if (typeof value === "string") {
          return value !== "" && value !== "false" && value !== "0";
        }
        return Boolean(value);
      })();

      console.log(`%c[ACCESS] hasAccess("${key}")`, "color: #f59e0b;", {
        key,
        value,
        result,
        accessMapKeys: Object.keys(accessMap.value),
      });

      return result;
    });
  }

  /**
   * Get a typed access value for a given key.
   *
   * @param key        - The access key to look up (e.g. "max_products")
   * @param defaultValue - Returned when the key is missing (defaults to undefined)
   *
   * @example
   *   const maxProducts = getAccess<number>("max_products", 50);
   *   const retention  = getAccess<number>("data_retention_days", 30);
   *   const label      = getAccess<string>("plan_label", "Free");
   */
  function getAccess<T extends boolean | number | string>(
    key: string,
    defaultValue?: T,
  ): ComputedRef<T | undefined> {
    return computed(() => {
      const value = accessMap.value[key];
      if (value === undefined || value === null) return defaultValue;
      return value as T;
    });
  }

  /**
   * Get a numeric limit from the access map.
   *
   * Convenience wrapper around getAccess that always returns a number.
   * Useful for plan limits like max_products, max_dsrs, max_suppliers, etc.
   *
   * @param key          - The access key (e.g. "max_products")
   * @param defaultValue - Default value when key is missing (defaults to 0)
   */
  function getLimit(key: string, defaultValue = 0): ComputedRef<number> {
    return computed(() => {
      const value = accessMap.value[key];
      if (value === undefined || value === null) return defaultValue;
      const num = Number(value);
      return isNaN(num) ? defaultValue : num;
    });
  }

  /** Reactive list of all available access keys. */
  const accessKeys: ComputedRef<string[]> = computed(() =>
    Object.keys(accessMap.value),
  );

  /**
   * Check if user is authenticated (has token)
   */
  const isAuthenticated = computed(() => !!getAccessToken());

  /**
   * Check if user has dealer-level access
   * (This is a convenience for dealer-specific UI)
   */
  const isDealer = computed(() => {
    // Check if access map indicates dealer status
    return hasAccess("dashboard").value && isAuthenticated.value;
  });

  return {
    // State
    access: accessMap,
    accessKeys,
    isLoading: isLoadingAccess,
    isAuthenticated,
    isDealer,

    // Access checking methods
    hasAccess,
    getAccess,
    getLimit,

    // State management (for useAuth)
    setAccessMap,
    clearAccessMap,
  };
}

// ─── Convenience Guards ──────────────────────────────────────────────────────

/**
 * Permission guard for components (backward compatibility)
 *
 * @example
 * ```vue
 * <template>
 *   <AccessGuard feature="reports">
 *     <ReportsPanel />
 *   </AccessGuard>
 * </template>
 * ```
 */
export function canAccessFeature(feature: string): boolean {
  const { hasAccess } = useAccess();
  return hasAccess(feature).value;
}
