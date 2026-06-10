/**
 * DSR (Dealer Sales Representative) Service
 *
 * Endpoints mapped:
 * GET    /api/dsrs        → getAllDsrs()
 * GET    /api/dsrs/:id    → getDsr(id)
 * POST   /api/dsrs        → createDsr(data)
 * PATCH  /api/dsrs/:id    → updateDsr(id, data)
 * DELETE /api/dsrs/:id    → deleteDsr(id)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { DSR } from "../../types";

// ─── Request Types ───────────────────────────────────────────────────────────

export interface CreateDsrPayload {
  name: string;
  phone: string;
  role?: "DSR" | "Order Collector";
  parentDsrId?: string;
}

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
  /** GET /api/dsrs — Fetch all DSRs */
  async getAllDsrs(): Promise<ApiResponse<DSR[]>> {
    return apiClient.get<DSR[]>("/api/dsrs");
  }

  /** GET /api/dsrs/:id — Fetch a single DSR */
  async getDsr(id: string): Promise<ApiResponse<DSR>> {
    return apiClient.get<DSR>(`/api/dsrs/${id}`);
  }

  /** POST /api/dsrs — Create a new DSR */
  async createDsr(data: CreateDsrPayload): Promise<ApiResponse<DSR>> {
    return apiClient.post<DSR>("/api/dsrs", data);
  }

  /** PATCH /api/dsrs/:id — Update a DSR */
  async updateDsr(
    id: string,
    data: UpdateDsrPayload,
  ): Promise<ApiResponse<DSR>> {
    return apiClient.patch<DSR>(`/api/dsrs/${id}`, data);
  }

  /** DELETE /api/dsrs/:id — Delete a DSR */
  async deleteDsr(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/api/dsrs/${id}`);
  }
}

export const dsrService = new DsrService();
export default dsrService;
