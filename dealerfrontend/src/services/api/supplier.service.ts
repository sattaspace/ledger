/**
 * Supplier Service
 *
 * Endpoints mapped:
 * GET    /suppliers         → getAllSuppliers()
 * GET    /suppliers/:id     → getSupplier(id)
 * POST   /suppliers         → createSupplier(data)
 * PATCH  /suppliers/:id     → updateSupplier(id, data)
 * DELETE /suppliers/:id     → deleteSupplier(id)
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
  /** GET /suppliers — Fetch all suppliers */
  async getAllSuppliers(): Promise<ApiResponse<Supplier[]>> {
    return apiClient.get<Supplier[]>("/suppliers");
  }

  /** GET /suppliers/:id — Fetch a single supplier */
  async getSupplier(id: string): Promise<ApiResponse<Supplier>> {
    return apiClient.get<Supplier>(`/suppliers/${id}`);
  }

  /** POST /suppliers — Create a new supplier */
  async createSupplier(
    data: CreateSupplierPayload,
  ): Promise<ApiResponse<Supplier>> {
    return apiClient.post<Supplier>("/suppliers", data);
  }

  /** PATCH /suppliers/:id — Update a supplier */
  async updateSupplier(
    id: string,
    data: UpdateSupplierPayload,
  ): Promise<ApiResponse<Supplier>> {
    return apiClient.patch<Supplier>(`/suppliers/${id}`, data);
  }

  /** DELETE /suppliers/:id — Delete a supplier */
  async deleteSupplier(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/suppliers/${id}`);
  }
}

export const supplierService = new SupplierService();
export default supplierService;
