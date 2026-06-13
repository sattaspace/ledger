/**
 * DSR Invitation Service
 *
 * Endpoints mapped:
 * POST   /invitations/create           → createInvitation(data)
 * GET    /invitations/list             → listInvitations(params)
 * GET    /invitations/:token           → getInvitation(token)
 * POST   /invitations/:token/accept    → acceptInvitation(token)
 * PATCH  /invitations/:id/revoke       → revokeInvitation(id)
 * DELETE /invitations/:id              → deleteInvitation(id)
 * GET    /invitations/assignments/list → listAssignments(params)
 * PATCH  /invitations/assignments/:id/deactivate → deactivateAssignment(id)
 * PATCH  /invitations/assignments/:id/activate   → activateAssignment(id)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type {
  DsrInvitation,
  CreateInvitationPayload,
  DsrAssignment,
} from "../../types";

// ─── Request/Response Types ─────────────────────────────────────────────────────

export interface ListInvitationsParams {
  status?: "pending" | "accepted" | "expired" | "revoked";
  limit?: number;
}

export interface ListAssignmentsParams {
  isActive?: boolean;
  role?: "DSR" | "Collector";
}

export interface AcceptInvitationResponse {
  message: string;
  assignment: {
    id: string;
    dsrId: string;
    dsrName: string;
    dealerUsername: string;
    role: string;
  };
}

// ─── Service ────────────────────────────────────────────────────────────────────

export class InvitationService {
  /** POST /invitations/create — Create a new invitation */
  async createInvitation(
    data: CreateInvitationPayload,
  ): Promise<ApiResponse<DsrInvitation>> {
    return apiClient.post<DsrInvitation>("/invitations/create", data);
  }

  /** GET /invitations/list — List all invitations for the dealer */
  async listInvitations(
    params?: ListInvitationsParams,
  ): Promise<ApiResponse<DsrInvitation[]>> {
    return apiClient.get<DsrInvitation[]>("/invitations/list", params);
  }

  /** GET /invitations/:token — Get invitation details by token (public) */
  async getInvitation(token: string): Promise<ApiResponse<DsrInvitation>> {
    return apiClient.get<DsrInvitation>(`/invitations/${token}`);
  }

  /** POST /invitations/:token/accept — Accept an invitation */
  async acceptInvitation(
    token: string,
  ): Promise<ApiResponse<AcceptInvitationResponse>> {
    return apiClient.post<AcceptInvitationResponse>(
      `/invitations/${token}/accept`,
      {},
    );
  }

  /** PATCH /invitations/:id/revoke — Revoke a pending invitation */
  async revokeInvitation(
    id: string,
  ): Promise<ApiResponse<{ message: string }>> {
    return apiClient.patch<{ message: string }>(
      `/invitations/${id}/revoke`,
      {},
    );
  }

  /** DELETE /invitations/:id — Delete an invitation */
  async deleteInvitation(
    id: string,
  ): Promise<ApiResponse<{ message: string }>> {
    return apiClient.delete<{ message: string }>(`/invitations/${id}`);
  }

  /** GET /invitations/assignments/list — List DSR assignments */
  async listAssignments(
    params?: ListAssignmentsParams,
  ): Promise<ApiResponse<DsrAssignment[]>> {
    return apiClient.get<DsrAssignment[]>(
      "/invitations/assignments/list",
      params,
    );
  }

  /** PATCH /invitations/assignments/:id/deactivate — Deactivate an assignment */
  async deactivateAssignment(
    id: string,
  ): Promise<ApiResponse<{ message: string }>> {
    return apiClient.patch<{ message: string }>(
      `/invitations/assignments/${id}/deactivate`,
      {},
    );
  }

  /** PATCH /invitations/assignments/:id/activate — Activate an assignment */
  async activateAssignment(
    id: string,
  ): Promise<ApiResponse<{ message: string }>> {
    return apiClient.patch<{ message: string }>(
      `/invitations/assignments/${id}/activate`,
      {},
    );
  }
}

export const invitationService = new InvitationService();
export default invitationService;
