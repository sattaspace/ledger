/**
 * useDsrPermissions — reactive DSR module permission checking composable.
 *
 * DSRs have per-dealer, per-module permissions stored in DsrDealerAssignment.
 * These are MORE granular than the plan-level access checked by useAccess:
 *
 *   useAccess:     Does the DEALER's plan include "suppliers"?  (plan-level)
 *   useDsrPermissions: Does the DSR have "suppliers.view"?     (module-level)
 *
 * For dealers, all module permission checks return true — dealers have full
 * access to their own data. For DSRs/Collectors, permissions come from the
 * DsrDealerAssignment.permissions JSON field, which is structured as:
 *
 *   {
 *     "dashboard": {"view": true},
 *     "inventory": {"view": true, "edit": false, "delete": false},
 *     "sales":     {"view": true, "edit": true, "delete": false},
 *     "collections": {"view": true, "edit": false},
 *     "suppliers": {"view": false},
 *     "reports":   {"view": true, "export": false},
 *     "print": true,
 *     "manage_dsrs": true
 *   }
 *
 * This composable fetches the DSR's permissions from the backend API and
 * provides reactive helpers for template and script-side checks.
 *
 * Usage:
 *   const { canView, canEdit, canDelete, canAction, isDealer } = useDsrPermissions();
 *
 *   // In template
 *   <div v-if="canView('sales')">...</div>
 *   <button v-if="canEdit('inventory')" @click="edit">Edit</button>
 *
 *   // In script
 *   if (canAction('reports', 'export').value) { ... }
 */

import { computed, ref, type ComputedRef } from "vue";
import { useAccess } from "./useAccess";
import { apiClient } from "../lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

/** Structure of DsrDealerAssignment.permissions JSON field */
export interface DsrModulePermissions {
  [module: string]: boolean | Record<string, boolean>;
}

/** API response for GET /dsr/permissions */
export interface DsrPermissionsResponse {
  is_dealer: boolean;
  dsr_user_id: string | null;
  dealer_username: string | null;
  role: string | null;
  permissions: DsrModulePermissions;
}

// ─── Module-level shared state (singleton) ───────────────────────────────────

const dsrPermissions = ref<DsrModulePermissions>({});
const isDsrDealer = ref(false);
const dsrRole = ref<string | null>(null);
const dsrUserId = ref<string | null>(null);
const dsrDealerUsername = ref<string | null>(null);
const isLoaded = ref(false);
const isLoading = ref(false);

// ─── Fetch DSR Permissions ───────────────────────────────────────────────────

/**
 * Fetch the current DSR's permissions from the backend.
 *
 * This should be called once after login (when we know the user is a DSR)
 * and the dealer context has been established. The backend returns the
 * DsrDealerAssignment.permissions for the currently selected dealer.
 *
 * For dealers, the backend returns is_dealer=true with empty permissions
 * (dealers bypass all module checks).
 */
export async function fetchDsrPermissions(): Promise<void> {
  if (isLoading.value) return;
  isLoading.value = true;

  try {
    const response =
      await apiClient.get<DsrPermissionsResponse>("/dsr/permissions");
    const data = response.data;

    isDsrDealer.value = data.is_dealer;
    dsrRole.value = data.role;
    dsrUserId.value = data.dsr_user_id;
    dsrDealerUsername.value = data.dealer_username;
    dsrPermissions.value = data.permissions || {};
    isLoaded.value = true;

    if (import.meta.env.DEV) {
      console.log(
        "%c[DSR_PERM] Fetched DSR permissions",
        "color: #10b981; font-weight: bold",
        {
          is_dealer: data.is_dealer,
          role: data.role,
          modules: Object.keys(data.permissions || {}),
        },
      );
    }
  } catch (error: any) {
    // If the endpoint returns 404 or 403, the user likely doesn't have
    // a DSR assignment. Set empty permissions (most restrictive).
    if (error?.response?.status === 404 || error?.response?.status === 403) {
      dsrPermissions.value = {};
      isLoaded.value = true;
      if (import.meta.env.DEV) {
        console.log(
          "[DSR_PERM] No DSR assignment found — permissions set to empty",
        );
      }
    } else {
      // Network error or other — don't block, but log
      console.error("[DSR_PERM] Failed to fetch DSR permissions:", error);
    }
  } finally {
    isLoading.value = false;
  }
}

/**
 * Clear DSR permissions (called on logout or dealer switch).
 */
export function clearDsrPermissions(): void {
  dsrPermissions.value = {};
  isDsrDealer.value = false;
  dsrRole.value = null;
  dsrUserId.value = null;
  dsrDealerUsername.value = null;
  isLoaded.value = false;
}

// ─── Composable ──────────────────────────────────────────────────────────────

export function useDsrPermissions() {
  const { isDealer: planIsDealer } = useAccess();

  /**
   * Check if the DSR has a specific permission in a module.
   *
   * For dealers: always returns true.
   * For DSRs: checks the DsrDealerAssignment.permissions JSON.
   *
   * Module permissions can be:
   *   - Boolean:  hasPermission("print") → true/false
   *   - Dict:     hasPermission("sales", "edit") → true/false
   *
   * @param module  - Module name (e.g. "sales", "inventory", "print")
   * @param action  - Action within module (e.g. "view", "edit", "delete")
   *                   Ignored for boolean modules.
   */
  function hasPermission(
    module: string,
    action: string = "view",
  ): ComputedRef<boolean> {
    return computed(() => {
      // Dealers bypass all module checks
      if (isDsrDealer.value || planIsDealer.value) return true;

      const modulePerms = dsrPermissions.value[module];

      // Module not in permissions at all → denied
      if (modulePerms === undefined || modulePerms === null) return false;

      // Boolean module (like "print" or "manage_dsrs")
      if (typeof modulePerms === "boolean") return modulePerms;

      // Dict module (like "sales": {"view": true, "edit": false})
      if (typeof modulePerms === "object") {
        return Boolean((modulePerms as Record<string, boolean>)[action]);
      }

      return false;
    });
  }

  /**
   * Quick check: can the DSR VIEW this module?
   * Equivalent to hasPermission(module, "view").
   */
  function canView(module: string): ComputedRef<boolean> {
    return hasPermission(module, "view");
  }

  /**
   * Quick check: can the DSR EDIT this module?
   * Equivalent to hasPermission(module, "edit").
   */
  function canEdit(module: string): ComputedRef<boolean> {
    return hasPermission(module, "edit");
  }

  /**
   * Quick check: can the DSR DELETE in this module?
   * Equivalent to hasPermission(module, "delete").
   */
  function canDelete(module: string): ComputedRef<boolean> {
    return hasPermission(module, "delete");
  }

  /**
   * Check if the DSR has ANY permission in a module.
   * True if the module exists and isn't empty/false.
   */
  function hasModuleAccess(module: string): ComputedRef<boolean> {
    return computed(() => {
      // Dealers bypass
      if (isDsrDealer.value || planIsDealer.value) return true;

      const modulePerms = dsrPermissions.value[module];

      // Not in permissions
      if (modulePerms === undefined || modulePerms === null) return false;

      // Boolean module
      if (typeof modulePerms === "boolean") return modulePerms;

      // Dict module — has at least one true value
      if (typeof modulePerms === "object") {
        return Object.values(modulePerms as Record<string, boolean>).some(
          Boolean,
        );
      }

      return false;
    });
  }

  /**
   * Check if the DSR can perform a specific action.
   * Alias for hasPermission with clearer naming for script-side use.
   */
  function canAction(module: string, action: string): ComputedRef<boolean> {
    return hasPermission(module, action);
  }

  /**
   * Is the current user a dealer (bypasses all DSR module checks)?
   */
  const isDealer = computed(() => isDsrDealer.value || planIsDealer.value);

  /**
   * Get all modules the DSR has any access to.
   */
  const accessibleModules = computed(() => {
    if (isDsrDealer.value || planIsDealer.value) {
      // Dealers have access to all modules
      return [
        "dashboard",
        "inventory",
        "sales",
        "collections",
        "suppliers",
        "reports",
        "print",
        "manage_dsrs",
      ];
    }

    return Object.entries(dsrPermissions.value)
      .filter(([, perms]) => {
        if (typeof perms === "boolean") return perms;
        if (typeof perms === "object") {
          return Object.values(perms as Record<string, boolean>).some(Boolean);
        }
        return false;
      })
      .map(([module]) => module);
  });

  return {
    // State
    permissions: dsrPermissions,
    role: dsrRole,
    dsrUserId,
    dealerUsername: dsrDealerUsername,
    isLoaded,
    isLoading,
    isDealer,

    // Module access
    hasModuleAccess,
    accessibleModules,

    // Permission checks
    hasPermission,
    canView,
    canEdit,
    canDelete,
    canAction,

    // Actions
    fetchDsrPermissions,
    clearDsrPermissions,
  };
}
