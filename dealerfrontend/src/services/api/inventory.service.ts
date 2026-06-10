/**
 * Inventory Service — Products & Restocking
 *
 * Endpoints mapped:
 * GET    /api/inventory              → getAllProducts()
 * GET    /api/inventory/:id          → getProduct(id)
 * GET    /api/inventory/restocks      → getAllRestocks()
 * GET    /api/inventory/restocks/:id  → getRestock(id)
 * POST   /api/inventory/add           → addProduct(data)
 * POST   /api/inventory/restock       → restockProduct(data)
 * POST   /api/inventory/:id/edit      → editProduct(id, data)
 * DELETE /api/inventory/:id           → deleteProduct(id)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { Product, RestockRecord, Brand, Category } from "../../types";

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

export interface DeleteResponse {
  message: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class InventoryService {
  /** GET /api/inventory — Fetch all products */
  async getAllProducts(): Promise<ApiResponse<Product[]>> {
    return apiClient.get<Product[]>("/api/inventory");
  }

  /** GET /api/inventory/:id — Fetch a single product */
  async getProduct(id: string): Promise<ApiResponse<Product>> {
    return apiClient.get<Product>(`/api/inventory/${id}`);
  }

  /** GET /api/inventory/restocks — Fetch all restock records */
  async getAllRestocks(): Promise<ApiResponse<RestockRecord[]>> {
    return apiClient.get<RestockRecord[]>("/api/inventory/restocks");
  }

  /** GET /api/inventory/restocks/:id — Fetch a single restock record */
  async getRestock(id: string): Promise<ApiResponse<RestockRecord>> {
    return apiClient.get<RestockRecord>(`/api/inventory/restocks/${id}`);
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

  /** DELETE /api/inventory/:id — Delete a product */
  async deleteProduct(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/api/inventory/${id}`);
  }

  // ─── Brands ──────────────────────────────────────────────────────────────

  /** GET /api/inventory/brands — Fetch all brands */
  async getBrands(): Promise<ApiResponse<Brand[]>> {
    return apiClient.get<Brand[]>("/api/inventory/brands");
  }

  /** POST /api/inventory/brands — Create a brand */
  async createBrand(data: { name: string }): Promise<ApiResponse<Brand>> {
    return apiClient.post<Brand>("/api/inventory/brands", data);
  }

  /** DELETE /api/inventory/brands/:id — Delete a brand */
  async deleteBrand(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/api/inventory/brands/${id}`);
  }

  // ─── Categories ─────────────────────────────────────────────────────────

  /** GET /api/inventory/categories — Fetch all categories */
  async getCategories(): Promise<ApiResponse<Category[]>> {
    return apiClient.get<Category[]>("/api/inventory/categories");
  }

  /** POST /api/inventory/categories — Create a category */
  async createCategory(data: { name: string }): Promise<ApiResponse<Category>> {
    return apiClient.post<Category>("/api/inventory/categories", data);
  }

  /** DELETE /api/inventory/categories/:id — Delete a category */
  async deleteCategory(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/api/inventory/categories/${id}`);
  }
}

export const inventoryService = new InventoryService();
export default inventoryService;
