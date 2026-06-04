/**
 * Supplier Service
 *
 * Endpoints mapped:
 * GET /api/suppliers → getAllSuppliers()
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { Supplier } from "../../types";

// ─── Service ──────────────────────────────────────────────────────────────────

export class SupplierService {
  /** GET /api/suppliers — Fetch all suppliers */
  async getAllSuppliers(): Promise<ApiResponse<Supplier[]>> {
    return apiClient.get<Supplier[]>("/api/suppliers");
  }
}

export const supplierService = new SupplierService();
export default supplierService;
