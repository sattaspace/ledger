/**
 * Dealer Configuration Service
 *
 * Endpoints mapped:
 * GET  /dealers              → getAllDealers()
 * GET  /dealers/:username    → getDealer(username)
 * POST /dealers/update       → updateDealerSettings(data)
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
  /** GET /dealers — Fetch all dealer configurations */
  async getAllDealers(): Promise<ApiResponse<DealerConfig[]>> {
    return apiClient.get<DealerConfig[]>("/dealers");
  }

  /** GET /dealers/:username — Fetch a single dealer configuration */
  async getDealer(username: string): Promise<ApiResponse<DealerConfig>> {
    return apiClient.get<DealerConfig>(`/dealers/${username}`);
  }

  /** POST /dealers/update — Update dealer currency/locale settings */
  async updateDealerSettings(
    data: UpdateDealerPayload,
  ): Promise<ApiResponse<DealerConfig>> {
    return apiClient.post<DealerConfig>("/dealers/update", data);
  }

  /** POST /dealers — Create a new dealer */
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
    return apiClient.post<DealerConfig>("/dealers", data);
  }
}

export const dealerService = new DealerService();
export default dealerService;
