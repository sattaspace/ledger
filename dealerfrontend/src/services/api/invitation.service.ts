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
 *
 * Audit fix TS-3: the `apiClient.get(endpoint, config)` signature takes
 * a `RequestConfig` object as the 2nd argument, NOT a params object.
 * `services/apiClient.ts` does NOT translate a `params` config field
 * into query string parameters (unlike `lib/api.ts`). To pass query
 * string params, we build the URL inline using `URLSearchParams` in
 * each method that accepts params (see `listInvitations` and
 * `listAssignments` below).
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
    // Audit fix TS-3: services/apiClient.ts's get(endpoint, config) doesn't
    // build query strings from a `params` field. We construct the URL
    // inline using URLSearchParams so the status/limit filters actually
    // reach the backend.
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    const query = qs.toString();
    const url = query ? `/invitations/list?${query}` : "/invitations/list";
    return apiClient.get<DsrInvitation[]>(url);
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
    // Audit fix TS-3: build query string inline (services/apiClient.ts
    // doesn't translate a `params` config field into query params).
    const qs = new URLSearchParams();
    if (params?.isActive !== undefined)
      qs.set("is_active", String(params.isActive));
    if (params?.role) qs.set("role", params.role);
    const query = qs.toString();
    const url = query
      ? `/invitations/assignments/list?${query}`
      : "/invitations/assignments/list";
    return apiClient.get<DsrAssignment[]>(url);
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
