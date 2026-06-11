/**
 * DEALERCORE v3.0 — Permissions Composable
 *
 * Role-based permission checking for the frontend.
 */

import { computed, readonly } from 'vue';
import { useAuth } from './useAuth';

export enum Role {
  DEALER = 'dealer',
  DSR = 'dsr',
  COLLECTOR = 'collector',
  ADMIN = 'admin',
}

export enum Permission {
  DEALER_FULL_ACCESS = 'dealer.full_access',
  DEALER_SETTINGS = 'dealer.settings',
  DEALER_BILLING = 'dealer.billing',
  DEALER_REPORTS = 'dealer.reports',
  DEALER_INVITE_DSR = 'dealer.invite_dsr',
  DSR_SALES_CREATE = 'dsr.sales_create',
  DSR_SALES_VIEW = 'dsr.sales_view',
  DSR_INVENTORY_VIEW = 'dsr.inventory_view',
  DSR_CUSTOMERS_VIEW = 'dsr.customers_view',
  DSR_COLLECTIONS_VIEW = 'dsr.collections_view',
  COLLECTOR_ORDER_ENTRY = 'collector.order_entry',
  COLLECTOR_SALES_CREATE = 'collector.sales_create',
  COLLECTOR_CUSTOMERS_VIEW = 'collector.customers_view',
  VIEW_DASHBOARD = 'view.dashboard',
  VIEW_INVENTORY = 'view.inventory',
  VIEW_SALES = 'view.sales',
  VIEW_REPORTS = 'view.reports',
  VIEW_COLLECTIONS = 'view.collections',
}

// Role to permissions mapping
const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  [Role.DEALER]: [
    Permission.DEALER_FULL_ACCESS,
    Permission.DEALER_SETTINGS,
    Permission.DEALER_BILLING,
    Permission.DEALER_REPORTS,
    Permission.DEALER_INVITE_DSR,
    Permission.DSR_SALES_CREATE,
    Permission.DSR_SALES_VIEW,
    Permission.DSR_INVENTORY_VIEW,
    Permission.DSR_CUSTOMERS_VIEW,
    Permission.DSR_COLLECTIONS_VIEW,
    Permission.COLLECTOR_ORDER_ENTRY,
    Permission.COLLECTOR_SALES_CREATE,
    Permission.COLLECTOR_CUSTOMERS_VIEW,
    Permission.VIEW_DASHBOARD,
    Permission.VIEW_INVENTORY,
    Permission.VIEW_SALES,
    Permission.VIEW_REPORTS,
    Permission.VIEW_COLLECTIONS,
  ],
  [Role.DSR]: [
    Permission.DSR_SALES_CREATE,
    Permission.DSR_SALES_VIEW,
    Permission.DSR_INVENTORY_VIEW,
    Permission.DSR_CUSTOMERS_VIEW,
    Permission.DSR_COLLECTIONS_VIEW,
    Permission.VIEW_DASHBOARD,
    Permission.VIEW_INVENTORY,
    Permission.VIEW_SALES,
    Permission.VIEW_COLLECTIONS,
  ],
  [Role.COLLECTOR]: [
    Permission.COLLECTOR_ORDER_ENTRY,
    Permission.COLLECTOR_SALES_CREATE,
    Permission.COLLECTOR_CUSTOMERS_VIEW,
    Permission.VIEW_DASHBOARD,
    Permission.VIEW_SALES,
  ],
  [Role.ADMIN]: [
    Permission.DEALER_FULL_ACCESS,
  ],
};

/**
 * Permissions composable
 * 
 * @example
 * ```vue
 * <script setup>
 * const { can, isDealer, isDSR, isCollector, visibleTabs } = usePermissions();
 * 
 * // Check single permission
 * if (can(Permission.DEALER_SETTINGS)) {
 *   // Show settings
 * }
 * 
 * // Check any permission
 * if (canAny([Permission.DSR_SALES_CREATE, Permission.COLLECTOR_SALES_CREATE])) {
 *   // Show sales button
 * }
 * </script>
 * ```
 */
export function usePermissions() {
  const { user } = useAuth();

  const role = computed(() => {
    return (user.value?.role as Role) || null;
  });

  const isDealer = computed(() => {
    return role.value === Role.DEALER || user.value?.is_dealer === true;
  });

  const isDSR = computed(() => role.value === Role.DSR);
  const isCollector = computed(() => role.value === Role.COLLECTOR);
  const isAdmin = computed(() => role.value === Role.ADMIN);

  const permissions = computed(() => {
    if (isDealer.value) {
      return ROLE_PERMISSIONS[Role.DEALER];
    }
    if (role.value) {
      return ROLE_PERMISSIONS[role.value] || [];
    }
    return [];
  });

  /**
   * Check if user has a specific permission
   */
  function can(permission: Permission): boolean {
    if (isDealer.value) return true;
    return permissions.value.includes(permission);
  }

  /**
   * Check if user has any of the permissions
   */
  function canAny(perms: Permission[]): boolean {
    if (isDealer.value) return true;
    return perms.some(p => permissions.value.includes(p));
  }

  /**
   * Check if user has all of the permissions
   */
  function canAll(perms: Permission[]): boolean {
    if (isDealer.value) return true;
    return perms.every(p => permissions.value.includes(p));
  }

  /**
   * Visible navigation tabs based on role
   */
  const visibleTabs = computed(() => {
    const tabs = [];

    // Dashboard - all roles
    if (can(Permission.VIEW_DASHBOARD)) {
      tabs.push({ id: 'overview', name: 'Dashboard', icon: '📦' });
    }

    // Inventory - dealer and DSR
    if (can(Permission.VIEW_INVENTORY)) {
      tabs.push({ id: 'inventory', name: 'Inventory/Restock', icon: '🏢' });
    }

    // Suppliers - dealer only
    if (isDealer.value) {
      tabs.push({ id: 'suppliers', name: 'Suppliers', icon: '🏪' });
    }

    // Sales - all roles
    if (canAny([Permission.DSR_SALES_CREATE, Permission.COLLECTOR_SALES_CREATE])) {
      tabs.push({ id: 'sales', name: 'Sales Entry', icon: '🧾' });
    }

    // Collections - dealer and DSR
    if (can(Permission.DSR_COLLECTIONS_VIEW)) {
      tabs.push({ id: 'collections', name: 'Pending Collections', icon: '⏳' });
    }

    // Bad Debt - dealer only
    if (isDealer.value) {
      tabs.push({ id: 'bad-debt', name: 'Bad Debt', icon: '⚠️' });
    }

    // Reports - dealer only
    if (can(Permission.DEALER_REPORTS)) {
      tabs.push({ id: 'reports', name: 'Financial Reports', icon: '📊' });
    }

    return tabs;
  });

  /**
   * Quick actions visible based on role
   */
  const visibleQuickActions = computed(() => {
    const actions = [];

    if (canAny([Permission.DSR_SALES_CREATE, Permission.COLLECTOR_SALES_CREATE])) {
      actions.push('sale');
    }

    if (can(Permission.DSR_COLLECTIONS_VIEW)) {
      actions.push('collect');
    }

    if (isDealer.value) {
      actions.push('restock', 'supplier');
    }

    return actions;
  });

  return {
    role: readonly(role),
    isDealer,
    isDSR,
    isCollector,
    isAdmin,
    permissions: readonly(permissions),
    can,
    canAny,
    canAll,
    visibleTabs,
    visibleQuickActions,
  };
}

/**
 * Permission guard for components
 * 
 * @example
 * ```vue
 * <template>
 *   <PermissionGuard :permission="Permission.DEALER_SETTINGS">
 *     <SettingsPanel />
 *   </PermissionGuard>
 * </template>
 * ```
 */
export function canView(permission: Permission): boolean {
  const { can } = usePermissions();
  return can(permission);
}
