/**
 * useSoftDelete — delete + restore confirmation flow.
 *
 * Manages the complete soft-delete/restore interaction pattern:
 * 1. User clicks "Delete" or "Restore" button
 * 2. Confirmation dialog appears with appropriate messaging
 * 3. On confirm, the store action is called
 * 4. Success/error feedback through callbacks
 *
 * Designed to work with Pinia CRUD stores built on the base.ts factory
 * and the ConfirmDialog component.
 *
 * Usage:
 *   const deleter = useSoftDelete({
 *     store: useInstitutionStore(),
 *     entityName: 'Institution',
 *     onDeleted: () => router.push('/institutions'),
 *   });
 *
 *   // In template:
 *   <button @click="deleter.confirmDelete(item)">Delete</button>
 *   <button @click="deleter.confirmRestore(item)">Restore</button>
 *
 *   <ConfirmDialog
 *     :open="deleter.showConfirm.value"
 *     :title="deleter.dialogTitle.value"
 *     :message="deleter.dialogMessage.value"
 *     :variant="deleter.dialogVariant.value"
 *     :confirm-text="deleter.confirmText.value"
 *     :loading="deleter.loading.value"
 *     @confirm="deleter.execute()"
 *     @cancel="deleter.cancel()"
 *   />
 */

import { ref, computed, type Ref, type ComputedRef } from "vue";
import { extractErrorMessage } from "@/stores/base";
import type { MessageOut } from "@/lib/ledgerTypes";

// =============================================================================
// Types
// =============================================================================

/** Entity type constraint for soft-delete operations. */
interface SoftDeletableEntity {
  id: number;
  is_deleted?: boolean;
  is_active?: boolean;
  [key: string]: unknown;
}

/** The type of action being confirmed. */
export type SoftDeleteAction = "delete" | "restore";

/**
 * Configuration for useSoftDelete.
 *
 * @template T - Entity type
 */
export interface UseSoftDeleteConfig<T extends SoftDeletableEntity> {
  /** The Pinia CRUD store instance with remove/restore actions. */
  store: {
    remove: (id: number) => Promise<MessageOut>;
    restore: (id: number) => Promise<MessageOut>;
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
   * Callback after successful deletion.
   *
   * @param item - The deleted entity
   */
  onDeleted?: (item: T) => void;

  /**
   * Callback after successful restoration.
   *
   * @param item - The restored entity
   */
  onRestored?: (item: T) => void;

  /**
   * Callback after a failed delete/restore operation.
   *
   * @param err - The error
   * @param action - Which action failed
   */
  onError?: (err: unknown, action: SoftDeleteAction) => void;

  /**
   * Whether to refresh the list after a successful operation.
   * Default: true.
   */
  refreshListAfter?: boolean;

  /**
   * Custom confirmation message for delete.
   * Supports {name} and {entity} placeholders.
   */
  deleteMessage?: string;

  /**
   * Custom confirmation message for restore.
   * Supports {name} and {entity} placeholders.
   */
  restoreMessage?: string;
}

/** Return type of useSoftDelete. */
export interface SoftDeleteHandler<T extends SoftDeletableEntity> {
  /** Whether the confirmation dialog is visible. */
  showConfirm: Ref<boolean>;

  /** The entity being acted upon. */
  targetItem: Ref<T | null>;

  /** The current action being confirmed: 'delete' or 'restore'. */
  action: Ref<SoftDeleteAction>;

  /** Whether an operation is in progress. */
  loading: Ref<boolean>;

  /** Error message from the last failed operation. */
  error: Ref<string | null>;

  /** Computed dialog title based on action type. */
  dialogTitle: ComputedRef<string>;

  /** Computed dialog message based on action type and entity. */
  dialogMessage: ComputedRef<string>;

  /** Computed dialog variant for ConfirmDialog. */
  dialogVariant: ComputedRef<"destructive" | "success">;

  /** Computed confirm button text based on action type. */
  confirmText: ComputedRef<string>;

  /**
   * Initiate a delete confirmation flow.
   * Opens the confirmation dialog for the given entity.
   *
   * @param item - The entity to delete
   */
  confirmDelete: (item: T) => void;

  /**
   * Initiate a restore confirmation flow.
   * Opens the confirmation dialog for the given entity.
   *
   * @param item - The entity to restore
   */
  confirmRestore: (item: T) => void;

  /**
   * Execute the confirmed action (delete or restore).
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
   * Directly delete an entity without confirmation.
   * Useful for bulk operations with a single outer confirmation.
   *
   * @param id - The entity ID to delete
   * @returns The API response, or null on error
   */
  deleteDirect: (id: number) => Promise<MessageOut | null>;

  /**
   * Directly restore an entity without confirmation.
   * Useful for bulk operations with a single outer confirmation.
   *
   * @param id - The entity ID to restore
   * @returns The API response, or null on error
   */
  restoreDirect: (id: number) => Promise<MessageOut | null>;
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Create a soft-delete/restore handler with confirmation flow.
 *
 * @template T - Entity type
 * @param config - Configuration object
 */
export function useSoftDelete<T extends SoftDeletableEntity>(
  config: UseSoftDeleteConfig<T>,
): SoftDeleteHandler<T> {
  const {
    store,
    entityName,
    getEntityLabel,
    onDeleted,
    onRestored,
    onError,
    refreshListAfter = true,
    deleteMessage,
    restoreMessage,
  } = config;

  // ─── State ──────────────────────────────────────────────────────────────

  const showConfirm = ref(false);
  const targetItem = ref<SoftDeletableEntity | null>(null) as Ref<T | null>;
  const action = ref<SoftDeleteAction>("delete");
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
    if (action.value === "delete") {
      return `Delete ${entityName}`;
    }
    return `Restore ${entityName}`;
  });

  const dialogMessage = computed(() => {
    const name = targetItem.value ? getLabel(targetItem.value) : "this item";

    if (action.value === "delete") {
      return deleteMessage
        ? deleteMessage.replace("{name}", name).replace("{entity}", entityName)
        : `Are you sure you want to delete "${name}"? This is a soft delete — the ${entityName.toLowerCase()} can be restored later.`;
    }

    return restoreMessage
      ? restoreMessage.replace("{name}", name).replace("{entity}", entityName)
      : `Are you sure you want to restore "${name}"? The ${entityName.toLowerCase()} will be active again.`;
  });

  const dialogVariant = computed(() => {
    return action.value === "delete" ? "destructive" : "success";
  });

  const confirmText = computed(() => {
    return action.value === "delete" ? "Delete" : "Restore";
  });

  // ─── Confirmation flow ──────────────────────────────────────────────────

  function confirmDelete(item: T): void {
    targetItem.value = item;
    action.value = "delete";
    error.value = null;
    showConfirm.value = true;
  }

  function confirmRestore(item: T): void {
    targetItem.value = item;
    action.value = "restore";
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

      if (action.value === "delete") {
        result = await store.remove(item.id);
        onDeleted?.(item);
      } else {
        result = await store.restore(item.id);
        onRestored?.(item);
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

  // ─── Direct operations (skip confirmation) ──────────────────────────────

  async function deleteDirect(id: number): Promise<MessageOut | null> {
    loading.value = true;
    error.value = null;

    try {
      const result = await store.remove(id);

      if (refreshListAfter) {
        store.invalidate?.();
        store.fetchList?.();
      }

      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      error.value = message;
      onError?.(err, "delete");
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function restoreDirect(id: number): Promise<MessageOut | null> {
    loading.value = true;
    error.value = null;

    try {
      const result = await store.restore(id);

      if (refreshListAfter) {
        store.invalidate?.();
        store.fetchList?.();
      }

      return result;
    } catch (err) {
      const message = extractErrorMessage(err);
      error.value = message;
      onError?.(err, "restore");
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

    confirmDelete,
    confirmRestore,
    execute,
    cancel,
    deleteDirect,
    restoreDirect,
  };
}
