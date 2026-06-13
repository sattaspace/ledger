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
 * Update the access map (called by useAuth after fetching /billing/auth/me).
 *
 * FIX M-15: validate the payload before storing. Without this, an
 * accidental nested object/array from a backend contract change would
 * fall through `Boolean(value)` in `hasAccess()` and silently grant
 * access. We strip down to primitive types only.
 *
 * @internal Use only via useAuth. Not part of the useAccess() composable API.
 */
export function setAccessMap(
  access: Record<string, boolean | number | string>,
): void {
  const sanitized: Record<string, boolean | number | string> = {};
  let dropped = 0;
  for (const [key, value] of Object.entries(access || {})) {
    if (
      typeof value === "boolean" ||
      typeof value === "number" ||
      typeof value === "string"
    ) {
      sanitized[key] = value;
    } else {
      dropped++;
    }
  }
  if (dropped > 0 && import.meta.env.DEV) {
    console.warn(
      `[ACCESS] setAccessMap dropped ${dropped} non-primitive value(s)`,
    );
  }
  if (import.meta.env.DEV) {
    console.log(
      "%c[ACCESS] setAccessMap called",
      "color: #8b5cf6; font-weight: bold",
      {
        keys: Object.keys(sanitized),
        access: sanitized,
      },
    );
  }
  accessMap.value = sanitized;
}

/**
 * Clear the access map (called on logout).
 *
 * @internal Use only via useAuth. Not part of the useAccess() composable API.
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
        if (typeof value === "number") {
          // FIX L-11: numeric 0 means "unlimited" for limit keys (e.g.
          // max_products=0 in the billing seed data means "unlimited").
          // Treat 0 as truthy for limit keys, falsy for feature keys.
          // Since we don't have an explicit flag-vs-limit distinction
          // here, default to truthy when key starts with "max_" (a
          // future refactor could introduce a separate enum for keys).
          if (value === 0) return key.startsWith("max_");
          return value > 0;
        }
        if (typeof value === "string") {
          // FIX L-10: case-insensitive truthy check. Previously "False",
          // "NO", "disabled" were all truthy. Now any case of false-ish
          // strings is treated as falsy.
          const lower = value.trim().toLowerCase();
          return lower !== "" && lower !== "false" && lower !== "0" && lower !== "no";
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
      if (isNaN(num)) return defaultValue;
      // FIX L-12: clamp to non-negative finite integers. A negative limit
      // (e.g. -5 from a backend bug) is dangerous — callers like
      // `if (current >= limit)` would treat any negative as "unlimited"
      // and the UI would show -5. Floor to defaultValue in that case.
      if (!isFinite(num) || num < 0) return defaultValue;
      return Math.floor(num);
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
   * Check if user has dealer-level access.
   *
   * FIX B-11: previously used `hasAccess("dashboard") && isAuthenticated` as
   * a heuristic, which silently granted `isDealer=true` to any DSR whose
   * plan happened to include `dashboard`. We now read the user's actual
   * role from the auth profile (set via /billing/auth/me).
   *
   * Lazy-imported to avoid a circular import: useAuth.ts already imports
   * getAccessToken from this file.
   */
  const isDealer = computed(() => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const authModule = require("./useAuth");
      const user = authModule?.user?.value;
      return user?.role === "dealer" || user?.is_dealer === true;
    } catch {
      return false;
    }
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

    // FIX B-6: setAccessMap and clearAccessMap removed from the public
    // composable API. They are still exported at module scope so useAuth
    // can call them, but downstream code can no longer accidentally
    // rewrite the global permission state.
  };
}

// ─── Convenience Guards ──────────────────────────────────────────────────────

// FIX L-9: removed `canAccessFeature()` — it was exported but never
// imported anywhere in the project (grep -r canAccessFeature returns
// only this definition). The proper access pattern is:
//   const { hasAccess } = useAccess();
//   const canView = hasAccess('reports');
// or use the <PermissionGuard> component for template-side gating.
