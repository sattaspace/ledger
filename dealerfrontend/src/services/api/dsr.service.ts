/**
 * DSR (Dealer Sales Representative) Service
 *
 * Endpoints mapped:
 * GET  /api/dsrs  → getAllDsrs()
 * POST /api/dsrs  → createDsr(data)
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

// ─── Service ──────────────────────────────────────────────────────────────────

export class DsrService {
  /** GET /api/dsrs — Fetch all DSRs */
  async getAllDsrs(): Promise<ApiResponse<DSR[]>> {
    return apiClient.get<DSR[]>("/api/dsrs");
  }

  /** POST /api/dsrs — Create a new DSR */
  async createDsr(data: CreateDsrPayload): Promise<ApiResponse<DSR>> {
    return apiClient.post<DSR>("/api/dsrs", data);
  }
}

export const dsrService = new DsrService();
export default dsrService;
