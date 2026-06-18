/**
 * useInvitations — composable for managing DSR invitations.
 *
 * Provides reactive state and methods for:
 * - Creating invitations
 * - Listing invitations
 * - Revoking/deleting invitations
 * - Managing DSR assignments
 *
 * Usage:
 *   const { invitations, createInvitation, isLoading, error } = useInvitations();
 *
 *   // Create invitation
 *   await createInvitation({ email: "rep@example.com", role: "DSR" });
 *
 *   // List invitations
 *   await fetchInvitations();
 *
 * Audit fix TS-2: the previous version checked `response.error` on every
 * call, but `services/apiClient.ts`'s `ApiResponse<T>` type is
 * `{ ok: boolean; status: number; data: T }` — there is NO `error` field.
 * The apiClient THROWS an `ApiError` instance on non-2xx responses, so
 * the catch block already handles all error cases. The `if (response.error)`
 * checks were dead code that also produced TypeScript errors. Removed.
 */

import { ref, computed, type Ref } from "vue";
import { invitationService } from "../services/api/invitation.service";
import type {
  DsrInvitation,
  CreateInvitationPayload,
  DsrAssignment,
} from "../types";

// ─── Types ─────────────────────────────────────────────────────────────────────

interface UseInvitationsReturn {
  // State
  invitations: Ref<DsrInvitation[]>;
  assignments: Ref<DsrAssignment[]>;
  isLoading: Ref<boolean>;
  error: Ref<string | null>;

  // Computed
  pendingInvitations: Ref<DsrInvitation[]>;
  acceptedInvitations: Ref<DsrInvitation[]>;
  hasPendingInvitations: Ref<boolean>;

  // Actions
  fetchInvitations: (status?: string) => Promise<void>;
  createInvitation: (
    data: CreateInvitationPayload,
  ) => Promise<DsrInvitation | null>;
  revokeInvitation: (id: string) => Promise<boolean>;
  deleteInvitation: (id: string) => Promise<boolean>;
  fetchAssignments: (isActive?: boolean) => Promise<void>;
  deactivateAssignment: (id: string) => Promise<boolean>;
  activateAssignment: (id: string) => Promise<boolean>;
  clearError: () => void;
}

// ─── Composable ────────────────────────────────────────────────────────────────

export function useInvitations(): UseInvitationsReturn {
  // ─── State ──────────────────────────────────────────────────────────────────
  const invitations = ref<DsrInvitation[]>([]);
  const assignments = ref<DsrAssignment[]>([]);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  // ─── Computed ────────────────────────────────────────────────────────────────
  const pendingInvitations = computed(() =>
    invitations.value.filter((inv) => inv.status === "pending"),
  );

  const acceptedInvitations = computed(() =>
    invitations.value.filter((inv) => inv.status === "accepted"),
  );

  const hasPendingInvitations = computed(
    () => pendingInvitations.value.length > 0,
  );

  // ─── Actions ──────────────────────────────────────────────────────────────────

  /**
   * Fetch invitations from the API
   */
  async function fetchInvitations(status?: string): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      // Audit fix TS-2: apiClient throws on non-2xx, so the catch block
      // handles all error cases. No `response.error` check needed.
      const response = await invitationService.listInvitations(
        status ? { status: status as any } : undefined,
      );
      invitations.value = response.data || [];
    } catch (err: any) {
      error.value = err.message || "Failed to fetch invitations";
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Create a new invitation
   */
  async function createInvitation(
    data: CreateInvitationPayload,
  ): Promise<DsrInvitation | null> {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await invitationService.createInvitation(data);
      // Add to local list
      if (response.data) {
        invitations.value.unshift(response.data);
        return response.data;
      }
      return null;
    } catch (err: any) {
      error.value = err.message || "Failed to create invitation";
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Revoke a pending invitation
   */
  async function revokeInvitation(id: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      await invitationService.revokeInvitation(id);
      // Update local state
      const index = invitations.value.findIndex((inv) => inv.id === id);
      if (index !== -1) {
        invitations.value[index].status = "revoked";
      }
      return true;
    } catch (err: any) {
      error.value = err.message || "Failed to revoke invitation";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Delete an invitation
   */
  async function deleteInvitation(id: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      await invitationService.deleteInvitation(id);
      // Remove from local list
      invitations.value = invitations.value.filter((inv) => inv.id !== id);
      return true;
    } catch (err: any) {
      error.value = err.message || "Failed to delete invitation";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Fetch DSR assignments
   */
  async function fetchAssignments(isActive?: boolean): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      const response = await invitationService.listAssignments(
        isActive !== undefined ? { isActive } : undefined,
      );
      assignments.value = response.data || [];
    } catch (err: any) {
      error.value = err.message || "Failed to fetch assignments";
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Deactivate a DSR assignment
   */
  async function deactivateAssignment(id: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      await invitationService.deactivateAssignment(id);
      // Update local state
      const index = assignments.value.findIndex((a) => a.id === id);
      if (index !== -1) {
        assignments.value[index].isActive = false;
      }
      return true;
    } catch (err: any) {
      error.value = err.message || "Failed to deactivate assignment";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Activate a DSR assignment
   */
  async function activateAssignment(id: string): Promise<boolean> {
    isLoading.value = true;
    error.value = null;

    try {
      await invitationService.activateAssignment(id);
      // Update local state
      const index = assignments.value.findIndex((a) => a.id === id);
      if (index !== -1) {
        assignments.value[index].isActive = true;
      }
      return true;
    } catch (err: any) {
      error.value = err.message || "Failed to activate assignment";
      return false;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Clear any error
   */
  function clearError(): void {
    error.value = null;
  }

  // ─── Return ──────────────────────────────────────────────────────────────────
  return {
    // State
    invitations,
    assignments,
    isLoading,
    error,

    // Computed
    pendingInvitations,
    acceptedInvitations,
    hasPendingInvitations,

    // Actions
    fetchInvitations,
    createInvitation,
    revokeInvitation,
    deleteInvitation,
    fetchAssignments,
    deactivateAssignment,
    activateAssignment,
    clearError,
  };
}
