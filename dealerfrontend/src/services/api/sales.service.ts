/**
 * Sales Service — Sales, Collections, Bulk Dispatch
 *
 * Endpoints mapped:
 * GET    /api/sales               → getAllSales()
 * POST   /api/sales               → createSale(data)
 * POST   /api/sales/bulk          → createBulkSales(data)
 * POST   /api/sales/:id/collect   → collectPayment(id, data)
 * POST   /api/sales/:id/close-with-due → closeSaleWithDue(id)
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

// ─── Service ──────────────────────────────────────────────────────────────────

export class SalesService {
  /** GET /api/sales — Fetch all sales */
  async getAllSales(): Promise<ApiResponse<SaleRecord[]>> {
    return apiClient.get<SaleRecord[]>("/api/sales");
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
}

export const salesService = new SalesService();
export default salesService;
