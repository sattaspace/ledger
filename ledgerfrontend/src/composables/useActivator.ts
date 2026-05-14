/**
 * useActivator — activate/deactivate toggle with confirmation.
 *
 * Manages the activate/deactivate confirmation flow for entities
 * that use the ActivatorModel pattern. Shows a ConfirmDialog before
 * toggling the active state, with variant-colored messaging.
 *
 * Designed to work with Pinia CRUD stores built on the base.ts factory
 * and the ConfirmDialog component.
 *
 * Usage:
 *   const activator = useActivator({
 *     store: useInstitutionStore(),
 *     entityName: 'Institution',
 *   });
 *
 *   // In template:
 *   <button @click="activator.confirmToggle(item)">
 *     {{ item.is_active ? 'Deactivate' : 'Activate' }}
 *   </button>
 *
 *   <ConfirmDialog
 *     :open="activator.showConfirm.value"
 *     :title="activator.dialogTitle.value"
 *     :message="activator.dialogMessage.value"
 *     :variant="activator.dialogVariant.value"
 *     :confirm-text="activator.confirmText.value"
 *     :loading="activator.loading.value"
 *     @confirm="activator.execute()"
 *     @cancel="activator.cancel()"
 *   />
 */

import { ref, computed, type Ref, type ComputedRef } from "vue";
import { extractErrorMessage } from "@/stores/base";
import type { MessageOut } from "@/lib/ledgerTypes";

// =============================================================================
// Types
// =============================================================================

/** Entity type constraint for activate/deactivate operations. */
interface ActivatableEntity {
  id: number;
  is_active?: boolean;
  [key: string]: unknown;
}

/** The type of action being confirmed. */
export type ActivatorAction = "activate" | "deactivate";

/**
 * Configuration for useActivator.
 *
 * @template T - Entity type
 */
export interface UseActivatorConfig<T extends ActivatableEntity> {
  /** The Pinia CRUD store instance with activate/deactivate actions. */
  store: {
    activate: (id: number) => Promise<MessageOut>;
    deactivate: (id: number) => Promise<MessageOut>;
    loadingAction: string;
    error: string | null;
    fetchList?: (filters?: unknown) => Promise<unknown>;
    invalidate?: () => void;
  };

  /**
   * Human-readable entity name for dialog messages.
   * E.g. "Institution", "Account", "Budget"
   */
  entityName: string;

  /**
   * Function to get the display name of an entity for dialog messages.
   * Defaults to using the `name` field.
   *
   * @param item - The entity
   * @returns Display name string
   */
  getEntityLabel?: (item: T) => string;

  /**
   * Callback after successful activation.
   *
   * @param item - The activated entity
   */
  onActivated?: (item: T) => void;

  /**
   * Callback after successful deactivation.
   *
   * @param item - The deactivated entity
   */
  onDeactivated?: (item: T) => void;

  /**
   * Callback after a failed activate/deactivate operation.
   *
   * @param err - The error
   * @param action - Which action failed
   */
  onError?: (err: unknown, action: ActivatorAction) => void;

  /**
   * Whether to refresh the list after a successful operation.
   * Default: false (the store does optimistic updates for activate/deactivate).
   */
  refreshListAfter?: boolean;

  /**
   * Whether to show confirmation before activating.
   * Deactivation always requires confirmation.
   * Default: false (activate is often a low-risk operation).
   */
  confirmActivate?: boolean;

  /**
   * Custom confirmation message for deactivation.
   * Supports {name} and {entity} placeholders.
   */
  deactivateMessage?: string;

  /**
   * Custom confirmation message for activation.
   * Supports {name} and {entity} placeholders.
   */
  activateMessage?: string;
}

/** Return type of useActivator. */
export interface ActivatorHandler<T extends ActivatableEntity> {
  /** Whether the confirmation dialog is visible. */
  showConfirm: Ref<boolean>;

  /** The entity being acted upon. */
  targetItem: Ref<T | null>;

  /** The current action being confirmed: 'activate' or 'deactivate'. */
  action: Ref<ActivatorAction>;

  /** Whether an operation is in progress. */
  loading: Ref<boolean>;

  /** Error message from the last failed operation. */
  error: Ref<string | null>;

  /** Computed dialog title based on action type. */
  dialogTitle: ComputedRef<string>;

  /** Computed dialog message based on action type and entity. */
  dialogMessage: ComputedRef<string>;

  /** Computed dialog variant for ConfirmDialog. */
  dialogVariant: ComputedRef<"warning" | "success">;

  /** Computed confirm button text based on action type. */
  confirmText: ComputedRef<string>;

  /**
   * Initiate an activate/deactivate toggle.
   * Detects the current is_active state and initiates the opposite action.
   * If confirmation is not needed (e.g. activating with confirmActivate=false),
   * the action is executed immediately.
   *
   * @param item - The entity to toggle
   */
  confirmToggle: (item: T) => void;

  /**
   * Specifically initiate an activation confirmation.
   *
   * @param item - The entity to activate
   */
  confirmActivate: (item: T) => void;

  /**
   * Specifically initiate a deactivation confirmation.
   *
   * @param item - The entity to deactivate
   */
  confirmDeactivate: (item: T) => void;

  /**
   * Execute the confirmed action (activate or deactivate).
   * Called by the ConfirmDialog's @confirm handler.
   *
   * @returns The API response, or null on error
   */
  execute: () => Promise<MessageOut | null>;

  /**
   * Cancel the confirmation dialog.
   * Called by the ConfirmDialog's @cancel handler.
   */
  cancel: () => void;

  /**
   * Directly activate an entity without confirmation.
   * Useful for programmatic activation or bulk operations.
   *
   * @param id - The entity ID to activate
   * @returns The API response, or null on error
   */
  activateDirect: (id: number) => Promise<MessageOut | null>;

  /**
   * Directly deactivate an entity without confirmation.
   *
   * @param id - The entity ID to deactivate
   * @returns The API response, or null on error
   */
  deactivateDirect: (id: number) => Promise<MessageOut | null>;
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Create an activate/deactivate handler with confirmation flow.
 *
 * @template T - Entity type
 * @param config - Configuration object
 */
export function useActivator<T extends ActivatableEntity>(
  config: UseActivatorConfig<T>,
): ActivatorHandler<T> {
  const {
    store,
    entityName,
    getEntityLabel,
    onActivated,
    onDeactivated,
    onError,
    refreshListAfter = false,
    confirmActivate: shouldConfirmActivate = false,
    deactivateMessage,
    activateMessage,
  } = config;

  // ─── State ──────────────────────────────────────────────────────────────

  const showConfirm = ref(false);
  const targetItem = ref<ActivatableEntity | null>(null) as Ref<T | null>;
  const action = ref<ActivatorAction>("deactivate");
  const loading = ref(false);
  const error = ref<string | null>(null);

  // ─── Helpers ────────────────────────────────────────────────────────────

  function getLabel(item: T): string {
    if (getEntityLabel) return getEntityLabel(item);
    if ("name" in item && typeof item.name === "string") return item.name;
    return `#${item.id}`;
  }

  // ─── Computed dialog properties ─────────────────────────────────────────

  const dialogTitle = computed(() => {
    if (action.value === "activate") {
      return `Activate ${entityName}`;
    }
    return `Deactivate ${entityName}`;
  });

  const dialogMessage = computed(() => {
    const name = targetItem.value ? getLabel(targetItem.value) : "this item";

    if (action.value === "activate") {
      return activateMessage
        ? activateMessage.replace("{name}", name).replace("{entity}", entityName)
        : `Are you sure you want to activate "${name}"? The ${entityName.toLowerCase()} will be active and visible in reports.`;
    }

    return deactivateMessage
      ? deactivateMessage.replace("{name}", name).replace("{entity}", entityName)
      : `Are you sure you want to deactivate "${name}"? The ${entityName.toLowerCase()} will be hidden from most views but can be reactivated later.`;
  });

  const dialogVariant = computed(() => {
    return action.value === "activate" ? "success" : "warning";
  });

  const confirmText = computed(() => {
    return action.value === "activate" ? "Activate" : "Deactivate";
  });

  // ─── Confirmation flow ──────────────────────────────────────────────────

  function confirmToggle(item: T): void {
    // Auto-detect the action based on current is_active state
    if (item.is_active === false) {
      initiateActivate(item);
    } else {
      initiateDeactivate(item);
    }
  }

  function confirmActivateAction(item: T): void {
    initiateActivate(item);
  }

  function confirmDeactivate(item: T): void {
    initiateDeactivate(item);
  }

  function initiateActivate(item: T): void {
    if (shouldConfirmActivate) {
      targetItem.value = item;
      action.value = "activate";
      error.value = null;
      showConfirm.value = true;
    } else {
      // Execute immediately without confirmation
      targetItem.value = item;
      action.value = "activate";
      executeImmediate(item.id, "activate");
    }
  }

  function initiateDeactivate(item: T): void {
    targetItem.value = item;
    action.value = "deactivate";
    error.value = null;
    showConfirm.value = true;
  }

  async function execute(): Promise<MessageOut | null> {
    const item = targetItem.value;
    if (!item) return null;

    loading.value = true;
    error.value = null;

    try {
      let result: MessageOut;

      if (action.value === "activate") {
        result = await store.activate(item.id);
        onActivated?.(item);
      } else {
        result = await store.deactivate(item.id);
        onDeactivated?.(item);
      }

      // Refresh the list if configured
      if (refreshListAfter) {
        store.invalidate?.();
        store.fetchList?.();
      }

      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      error.value = message;
      onError?.(err, action.value);
      return null;
    } finally {
      loading.value = false;
      showConfirm.value = false;
      targetItem.value = null;
    }
  }

  function cancel(): void {
    showConfirm.value = false;
    targetItem.value = null;
    error.value = null;
  }

  // ─── Immediate execution (no confirmation) ──────────────────────────────

  async function executeImmediate(
    id: number,
    targetAction: ActivatorAction,
  ): Promise<MessageOut | null> {
    loading.value = true;
    error.value = null;

    try {
      let result: MessageOut;

      if (targetAction === "activate") {
        result = await store.activate(id);
        onActivated?.(targetItem.value as T);
      } else {
        result = await store.deactivate(id);
        onDeactivated?.(targetItem.value as T);
      }

      if (refreshListAfter) {
        store.invalidate?.();
        store.fetchList?.();
      }

      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      error.value = message;
      onError?.(err, targetAction);
      return null;
    } finally {
      loading.value = false;
      targetItem.value = null;
    }
  }

  // ─── Direct operations (skip confirmation) ──────────────────────────────

  async function activateDirect(id: number): Promise<MessageOut | null> {
    loading.value = true;
    error.value = null;

    try {
      const result = await store.activate(id);

      if (refreshListAfter) {
        store.invalidate?.();
        store.fetchList?.();
      }

      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      error.value = message;
      onError?.(err, "activate");
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function deactivateDirect(id: number): Promise<MessageOut | null> {
    loading.value = true;
    error.value = null;

    try {
      const result = await store.deactivate(id);

      if (refreshListAfter) {
        store.invalidate?.();
        store.fetchList?.();
      }

      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      error.value = message;
      onError?.(err, "deactivate");
      return null;
    } finally {
      loading.value = false;
    }
  }

  return {
    showConfirm,
    targetItem,
    action,
    loading,
    error,
    dialogTitle,
    dialogMessage,
    dialogVariant,
    confirmText,

    confirmToggle,
    confirmActivate: confirmActivateAction,
    confirmDeactivate,
    execute,
    cancel,
    activateDirect,
    deactivateDirect,
  };
}
