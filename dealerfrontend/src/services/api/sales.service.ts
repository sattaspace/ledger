/**
 * Sales Service — Sales, Collections, Bulk Dispatch
 *
 * Endpoints mapped:
 * GET    /api/sales                       → getAllSales()
 * GET    /api/sales/:id                    → getSale(id)
 * POST   /api/sales                        → createSale(data)
 * POST   /api/sales/bulk                   → createBulkSales(data)
 * POST   /api/sales/:id/collect            → collectPayment(id, data)
 * POST   /api/sales/:id/close-with-due     → closeSaleWithDue(id)
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { SaleRecord } from "../../types";

// ─── Request / Response Types ──────────────────────────────────────────────────

export interface CreateSalePayload {
  productId: string;
  quantity: number;
  customerName: string;
  customerPhone?: string;
  isVehicle?: boolean;
  vehicleNumber?: string;
  dsrId?: string;
  paymentType: "Cash" | "Credit";
  amountPaid?: number;
  dueDate?: string;
}

export interface BulkSaleRow {
  productId: string;
  quantity: number;
  customerName: string;
  customerPhone: string;
  paymentType: "Cash" | "Credit";
  amountPaid: number;
  dueDate?: string;
}

export interface BulkSalePayload {
  vehicleNumber: string;
  dsrId?: string;
  rows: BulkSaleRow[];
}

export interface CollectPaymentPayload {
  amount: number;
  receivedBy: string;
}

export interface ReturnSaleItemPayload {
  quantity: number;
  reason: string;
  processedBy: string;
}

export interface EditSalePayload {
  customerName?: string;
  customerPhone?: string;
  dueDate?: string;
  vehicleNumber?: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class SalesService {
  /** GET /api/sales — Fetch all sales */
  async getAllSales(): Promise<ApiResponse<SaleRecord[]>> {
    return apiClient.get<SaleRecord[]>("/api/sales");
  }

  /** GET /api/sales/:id — Fetch a single sale */
  async getSale(id: string): Promise<ApiResponse<SaleRecord>> {
    return apiClient.get<SaleRecord>(`/api/sales/${id}`);
  }

  /** POST /api/sales — Create a single sale */
  async createSale(data: CreateSalePayload): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>("/api/sales", data);
  }

  /** POST /api/sales/bulk — Create multiple sales (vehicle dispatch) */
  async createBulkSales(
    data: BulkSalePayload,
  ): Promise<ApiResponse<SaleRecord[]>> {
    return apiClient.post<SaleRecord[]>("/api/sales/bulk", data);
  }

  /** POST /api/sales/:id/collect — Collect partial payment on a sale */
  async collectPayment(
    saleId: string,
    data: CollectPaymentPayload,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/api/sales/${saleId}/collect`, data);
  }

  /** POST /api/sales/:id/close-with-due — Write off outstanding balance */
  async closeSaleWithDue(saleId: string): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/api/sales/${saleId}/close-with-due`);
  }

  /** POST /api/sales/:id/return — Return items from a sale */
  async returnSaleItem(
    saleId: string,
    data: ReturnSaleItemPayload,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/api/sales/${saleId}/return`, data);
  }

  /** POST /api/sales/:id/void — Void a sale (restore stock)
   *  @param force - Override void protection for sales with transactions */
  async voidSale(
    saleId: string,
    force: boolean = false,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(
      `/api/sales/${saleId}/void${force ? "?force=true" : ""}`,
    );
  }

  /** POST /api/sales/:id/edit — Edit sale details */
  async editSale(
    saleId: string,
    data: EditSalePayload,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/api/sales/${saleId}/edit`, data);
  }
}

export const salesService = new SalesService();
export default salesService;
