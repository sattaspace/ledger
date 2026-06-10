/**
 * Dealer Configuration Service
 *
 * Endpoints mapped:
 * GET  /api/dealers              → getAllDealers()
 * GET  /api/dealers/:username    → getDealer(username)
 * POST /api/dealers/update       → updateDealerSettings(data)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { DealerConfig } from "../../types";

// ─── Request Types ───────────────────────────────────────────────────────────

export interface UpdateDealerPayload {
  username: string;
  defaultCurrency?: string;
  defaultLocale?: string;
  fullName?: string;
  role?: string;
  businessName?: string;
  address?: string;
  phoneNumber?: string;
  email?: string;
  gstNumber?: string;
  googleMapUrl?: string;
  communicationNumber?: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class DealerService {
  /** GET /api/dealers — Fetch all dealer configurations */
  async getAllDealers(): Promise<ApiResponse<DealerConfig[]>> {
    return apiClient.get<DealerConfig[]>("/api/dealers");
  }

  /** GET /api/dealers/:username — Fetch a single dealer configuration */
  async getDealer(username: string): Promise<ApiResponse<DealerConfig>> {
    return apiClient.get<DealerConfig>(`/api/dealers/${username}`);
  }

  /** POST /api/dealers/update — Update dealer currency/locale settings */
  async updateDealerSettings(
    data: UpdateDealerPayload,
  ): Promise<ApiResponse<DealerConfig>> {
    return apiClient.post<DealerConfig>("/api/dealers/update", data);
  }

  /** POST /api/dealers — Create a new dealer */
  async createDealer(data: {
    username: string;
    fullName: string;
    role: string;
    businessName: string;
    address: string;
    phoneNumber: string;
    email: string;
    gstNumber: string;
    googleMapUrl: string;
    communicationNumber: string;
    defaultCurrency: string;
    defaultLocale: string;
  }): Promise<ApiResponse<DealerConfig>> {
    return apiClient.post<DealerConfig>("/api/dealers", data);
  }
}

export const dealerService = new DealerService();
export default dealerService;
