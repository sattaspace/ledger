/**
 * Supplier Service
 *
 * Endpoints mapped:
 * GET    /api/suppliers         → getAllSuppliers()
 * GET    /api/suppliers/:id     → getSupplier(id)
 * POST   /api/suppliers         → createSupplier(data)
 * PATCH  /api/suppliers/:id     → updateSupplier(id, data)
 * DELETE /api/suppliers/:id     → deleteSupplier(id)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { Supplier } from "../../types";

// ─── Request Types ───────────────────────────────────────────────────────────

export interface CreateSupplierPayload {
  name: string;
  phone?: string;
  category?: string;
}

export interface UpdateSupplierPayload {
  name?: string;
  phone?: string;
  category?: string;
}

export interface DeleteResponse {
  message: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class SupplierService {
  /** GET /api/suppliers — Fetch all suppliers */
  async getAllSuppliers(): Promise<ApiResponse<Supplier[]>> {
    return apiClient.get<Supplier[]>("/api/suppliers");
  }

  /** GET /api/suppliers/:id — Fetch a single supplier */
  async getSupplier(id: string): Promise<ApiResponse<Supplier>> {
    return apiClient.get<Supplier>(`/api/suppliers/${id}`);
  }

  /** POST /api/suppliers — Create a new supplier */
  async createSupplier(
    data: CreateSupplierPayload,
  ): Promise<ApiResponse<Supplier>> {
    return apiClient.post<Supplier>("/api/suppliers", data);
  }

  /** PATCH /api/suppliers/:id — Update a supplier */
  async updateSupplier(
    id: string,
    data: UpdateSupplierPayload,
  ): Promise<ApiResponse<Supplier>> {
    return apiClient.patch<Supplier>(`/api/suppliers/${id}`, data);
  }

  /** DELETE /api/suppliers/:id — Delete a supplier */
  async deleteSupplier(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/api/suppliers/${id}`);
  }
}

export const supplierService = new SupplierService();
export default supplierService;
