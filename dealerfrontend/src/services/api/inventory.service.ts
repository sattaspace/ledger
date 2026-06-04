/**
 * Inventory Service — Products & Restocking
 *
 * Endpoints mapped:
 * GET    /api/inventory           → getAllProducts()
 * POST   /api/inventory/add       → addProduct(data)
 * POST   /api/inventory/restock   → restockProduct(data)
 * POST   /api/inventory/:id/edit  → editProduct(id, data)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { Product } from "../../types";

// ─── Request / Response Types ──────────────────────────────────────────────────

export interface AddProductPayload {
  name: string;
  sku: string;
  brand: string;
  category: string;
  minStockAlert: number;
  unitPrice: number;
  sellingPrice: number;
  location: string;
}

export interface RestockPayload {
  productId: string;
  quantity: number;
  supplierName: string;
  costPrice: number;
  receivedBy: string;
}

export interface EditProductPayload {
  name?: string;
  sku?: string;
  brand?: string;
  category?: string;
  minStockAlert?: number;
  unitPrice?: number;
  sellingPrice?: number;
  location?: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class InventoryService {
  /** GET /api/inventory — Fetch all products */
  async getAllProducts(): Promise<ApiResponse<Product[]>> {
    return apiClient.get<Product[]>("/api/inventory");
  }

  /** POST /api/inventory/add — Create a new product */
  async addProduct(data: AddProductPayload): Promise<ApiResponse<Product>> {
    return apiClient.post<Product>("/api/inventory/add", data);
  }

  /** POST /api/inventory/restock — Restock existing product */
  async restockProduct(
    data: RestockPayload,
  ): Promise<ApiResponse<{ message: string; product: Product }>> {
    return apiClient.post("/api/inventory/restock", data);
  }

  /** POST /api/inventory/:id/edit — Edit product fields */
  async editProduct(
    id: string,
    data: EditProductPayload,
  ): Promise<ApiResponse<Product>> {
    return apiClient.post<Product>(`/api/inventory/${id}/edit`, data);
  }
}

export const inventoryService = new InventoryService();
export default inventoryService;
