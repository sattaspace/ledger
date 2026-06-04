/**
 * Dealer Configuration Service
 *
 * Endpoints mapped:
 * GET  /api/dealers      → getAllDealers()
 * POST /api/dealers/update → updateDealerSettings(data)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { DealerConfig } from "../../types";

// ─── Request Types ───────────────────────────────────────────────────────────

export interface UpdateDealerPayload {
  username: string;
  defaultCurrency: string;
  defaultLocale: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class DealerService {
  /** GET /api/dealers — Fetch all dealer configurations */
  async getAllDealers(): Promise<ApiResponse<DealerConfig[]>> {
    return apiClient.get<DealerConfig[]>("/api/dealers");
  }

  /** POST /api/dealers/update — Update dealer currency/locale settings */
  async updateDealerSettings(
    data: UpdateDealerPayload,
  ): Promise<ApiResponse<DealerConfig>> {
    return apiClient.post<DealerConfig>("/api/dealers/update", data);
  }
}

export const dealerService = new DealerService();
export default dealerService;
