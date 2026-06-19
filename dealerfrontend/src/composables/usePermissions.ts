/**
 * usePermissions — unified permission checking for both dealers and DSRs.
 *
 * This composable wraps `useAccess` (plan-level / effective_access) and
 * `useDsrPermissions` (DSR per-module per-action) into a single API so
 * page components can gate operation buttons with one function call.
 *
 * The access-control model is:
 *
 *   DEALER session:
 *     - All operations allowed (dealers have full access to their own data)
 *     - The only check is plan-level: does the dealer's subscription
 *       include this feature? (e.g., "bad_debt", "export_pdf")
 *
 *   DSR session (portal mode):
 *     - The `effective_access` map (from select-dealer / refresh-access)
 *       is ALREADY the intersection of plan-level × DSR-assignment.
 *     - So `useAccess().hasAccess("inventory")` returns true only if
 *       BOTH the dealer's plan includes inventory AND the dealer granted
 *       the DSR inventory.view.
 *     - For granular action checks (view vs edit vs delete), we also
 *       consult `useDsrPermissions().hasPermission(module, action)`.
 *       This reads the raw DSR assignment permissions (not the
 *       effective_access intersection), but since the DSR is in portal
 *       mode, the plan-level side was already enforced when
 *       effective_access was computed.
 *
 * Usage:
 *   ```ts
 *   const { can, canView, canEdit, canDelete, canAction } = usePermissions();
 *
 *   // Check if user can view the inventory module
 *   if (canView('inventory').value) { ... }
 *
 *   // Check if user can edit sales
 *   if (canEdit('sales').value) { ... }
 *
 *   // Check a custom action
 *   if (canAction('reports', 'export').value) { ... }
 *
 *   // Check a plan-level feature (not module-specific)
 *   if (can('bad_debt').value) { ... }
 *   ```
 *
 * Audit fix GAP C-1: previously, page components did NO operation-level
 * enforcement. Buttons were always visible and relied entirely on the
 * backend returning 403. This composable provides a one-line check that
 * page components can use to hide buttons the user can't use.
 */

import { computed, type ComputedRef } from "vue";
import { useAccess } from "./useAccess";
import { useDsrPermissions } from "./useDsrPermissions";

export function usePermissions() {
  const { hasAccess, isDealer } = useAccess();
  const {
    hasPermission,
    canView: dsrCanView,
    canEdit: dsrCanEdit,
    canDelete: dsrCanDelete,
    canAction: dsrCanAction,
  } = useDsrPermissions();

  /**
   * Check a plan-level feature key (e.g., "bad_debt", "export_pdf").
   * For dealers, this checks the SattaBase plan access map.
   * For DSRs, this checks the effective_access map (already the
   * intersection of plan × DSR assignment).
   */
  function can(feature: string): ComputedRef<boolean> {
    return hasAccess(feature);
  }

  /**
   * Check if the user can VIEW a module.
   * Combines plan-level access (effective_access[module]) with
   * DSR per-module permission (module.view).
   * For dealers, always true if the plan includes the module.
   */
  function canView(module: string): ComputedRef<boolean> {
    return computed(() => {
      // Dealers bypass DSR-level checks — only plan-level matters.
      if (isDealer.value) return hasAccess(module).value;
      // DSRs: check both the effective_access (intersection) AND
      // the granular DSR assignment permission.
      return hasAccess(module).value && dsrCanView(module).value;
    });
  }

  /**
   * Check if the user can EDIT (create/update) in a module.
   */
  function canEdit(module: string): ComputedRef<boolean> {
    return computed(() => {
      if (isDealer.value) return hasAccess(module).value;
      return hasAccess(module).value && dsrCanEdit(module).value;
    });
  }

  /**
   * Check if the user can DELETE in a module.
   */
  function canDelete(module: string): ComputedRef<boolean> {
    return computed(() => {
      if (isDealer.value) return hasAccess(module).value;
      return hasAccess(module).value && dsrCanDelete(module).value;
    });
  }

  /**
   * Check if the user can perform a specific action in a module.
   * E.g., canAction('reports', 'export').
   */
  function canAction(module: string, action: string): ComputedRef<boolean> {
    return computed(() => {
      if (isDealer.value) return hasAccess(module).value;
      return hasAccess(module).value && dsrCanAction(module, action).value;
    });
  }

  return {
    can,
    canView,
    canEdit,
    canDelete,
    canAction,
    // Re-export the underlying composables for advanced use cases
    isDealer,
  };
}
