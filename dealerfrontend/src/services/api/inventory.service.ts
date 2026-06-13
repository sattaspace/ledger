/**
 * Inventory Service — Products & Restocking
 *
 * Endpoints mapped:
 * GET    /inventory              → getAllProducts()
 * GET    /inventory/:id          → getProduct(id)
 * GET    /inventory/restocks      → getAllRestocks()
 * GET    /inventory/restocks/:id  → getRestock(id)
 * POST   /inventory/add           → addProduct(data)
 * POST   /inventory/restock       → restockProduct(data)
 * POST   /inventory/:id/edit      → editProduct(id, data)
 * DELETE /inventory/:id           → deleteProduct(id)
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
  /** GET /inventory — Fetch all products */
  async getAllProducts(): Promise<ApiResponse<Product[]>> {
    return apiClient.get<Product[]>("/inventory");
  }

  /** GET /inventory/:id — Fetch a single product */
  async getProduct(id: string): Promise<ApiResponse<Product>> {
    return apiClient.get<Product>(`/inventory/${id}`);
  }

  /** GET /inventory/restocks — Fetch all restock records */
  async getAllRestocks(): Promise<ApiResponse<RestockRecord[]>> {
    return apiClient.get<RestockRecord[]>("/inventory/restocks");
  }

  /** GET /inventory/restocks/:id — Fetch a single restock record */
  async getRestock(id: string): Promise<ApiResponse<RestockRecord>> {
    return apiClient.get<RestockRecord>(`/inventory/restocks/${id}`);
  }

  /** POST /inventory/add — Create a new product */
  async addProduct(data: AddProductPayload): Promise<ApiResponse<Product>> {
    return apiClient.post<Product>("/inventory/add", data);
  }

  /** POST /inventory/restock — Restock existing product */
  async restockProduct(
    data: RestockPayload,
  ): Promise<ApiResponse<{ message: string; product: Product }>> {
    return apiClient.post("/inventory/restock", data);
  }

  /** POST /inventory/:id/edit — Edit product fields */
  async editProduct(
    id: string,
    data: EditProductPayload,
  ): Promise<ApiResponse<Product>> {
    return apiClient.post<Product>(`/inventory/${id}/edit`, data);
  }

  /** DELETE /inventory/:id — Delete a product */
  async deleteProduct(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/inventory/${id}`);
  }

  // ─── Brands ──────────────────────────────────────────────────────────────

  /** GET /inventory/brands — Fetch all brands */
  async getBrands(): Promise<ApiResponse<Brand[]>> {
    return apiClient.get<Brand[]>("/inventory/brands");
  }

  /** POST /inventory/brands — Create a brand */
  async createBrand(data: { name: string }): Promise<ApiResponse<Brand>> {
    return apiClient.post<Brand>("/inventory/brands", data);
  }

  /** DELETE /inventory/brands/:id — Delete a brand */
  async deleteBrand(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/inventory/brands/${id}`);
  }

  // ─── Categories ─────────────────────────────────────────────────────────

  /** GET /inventory/categories — Fetch all categories */
  async getCategories(): Promise<ApiResponse<Category[]>> {
    return apiClient.get<Category[]>("/inventory/categories");
  }

  /** POST /inventory/categories — Create a category */
  async createCategory(data: { name: string }): Promise<ApiResponse<Category>> {
    return apiClient.post<Category>("/inventory/categories", data);
  }

  /** DELETE /inventory/categories/:id — Delete a category */
  async deleteCategory(id: string): Promise<ApiResponse<DeleteResponse>> {
    return apiClient.delete<DeleteResponse>(`/inventory/categories/${id}`);
  }
}

export const inventoryService = new InventoryService();
export default inventoryService;
