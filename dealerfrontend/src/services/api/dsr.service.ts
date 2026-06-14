/**
 * DSR (Dealer Sales Representative) Service
 *
 * Endpoints mapped:
 * GET    /dsrs        → getAllDsrs()
 * GET    /dsrs/:id    → getDsr(id)
 * PATCH  /dsrs/:id    → updateDsr(id, data)
 * DELETE /dsrs/:id    → deleteDsr(id)
 *
 * NOTE: POST /dsrs (createDsr) has been REMOVED.
 * DSRs must now be invited via /dealer/dsr/invite endpoint.
 * See AddRepModal.vue for the invitation flow implementation.
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { DSR } from "../../types";

// ─── Request Types ───────────────────────────────────────────────────────────

export interface UpdateDsrPayload {
  name?: string;
  phone?: string;
  role?: "DSR" | "Order Collector";
  parentDsrId?: string | null;
}

export interface DeleteResponse {
  message: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class DsrService {
  /** GET /dsrs — Fetch all DSRs */
  async getAllDsrs(): Promise<ApiResponse<DSR[]>> {
    return apiClient.get<DSR[]>("/dsrs");
  }

  /** GET /dsrs/:id — Fetch a single DSR */
  async getDsr(id: string): Promise<ApiResponse<DSR>> {
    return apiClient.get<DSR>(`/dsrs/${id}`);
  }

  /** PATCH /dsrs/:id — Update a DSR */
  async updateDsr(
    id: string,
    data: UpdateDsrPayload,
  ): Promise<ApiResponse<DSR>> {
    return apiClient.patch<DSR>(`/dsrs/${id}`, data);
  }

  /** DELETE /dsrs/:id — Delete a DSR */
  async deleteDsr(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/dsrs/${id}`);
  }
}

export const dsrService = new DsrService();
export default dsrService;
