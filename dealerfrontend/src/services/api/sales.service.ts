/**
 * Sales Service — Sales, Collections, Bulk Dispatch
 *
 * Endpoints mapped:
 * GET    /sales                       → getAllSales()
 * GET    /sales/:id                    → getSale(id)
 * POST   /sales                        → createSale(data)
 * POST   /sales/bulk                   → createBulkSales(data)
 * POST   /sales/:id/collect            → collectPayment(id, data)
 * POST   /sales/:id/close-with-due     → closeSaleWithDue(id)
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
  /** GET /sales — Fetch all sales */
  async getAllSales(): Promise<ApiResponse<SaleRecord[]>> {
    return apiClient.get<SaleRecord[]>("/sales");
  }

  /** GET /sales/:id — Fetch a single sale */
  async getSale(id: string): Promise<ApiResponse<SaleRecord>> {
    return apiClient.get<SaleRecord>(`/sales/${id}`);
  }

  /** POST /sales — Create a single sale */
  async createSale(data: CreateSalePayload): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>("/sales", data);
  }

  /** POST /sales/bulk — Create multiple sales (vehicle dispatch) */
  async createBulkSales(
    data: BulkSalePayload,
  ): Promise<ApiResponse<SaleRecord[]>> {
    return apiClient.post<SaleRecord[]>("/sales/bulk", data);
  }

  /** POST /sales/:id/collect — Collect partial payment on a sale */
  async collectPayment(
    saleId: string,
    data: CollectPaymentPayload,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/sales/${saleId}/collect`, data);
  }

  /** POST /sales/:id/close-with-due — Write off outstanding balance */
  async closeSaleWithDue(saleId: string): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/sales/${saleId}/close-with-due`);
  }

  /** POST /sales/:id/return — Return items from a sale */
  async returnSaleItem(
    saleId: string,
    data: ReturnSaleItemPayload,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/sales/${saleId}/return`, data);
  }

  /** POST /sales/:id/void — Void a sale (restore stock)
   *  @param force - Override void protection for sales with transactions */
  async voidSale(
    saleId: string,
    force: boolean = false,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(
      `/sales/${saleId}/void${force ? "?force=true" : ""}`,
    );
  }

  /** POST /sales/:id/edit — Edit sale details */
  async editSale(
    saleId: string,
    data: EditSalePayload,
  ): Promise<ApiResponse<SaleRecord>> {
    return apiClient.post<SaleRecord>(`/sales/${saleId}/edit`, data);
  }
}

export const salesService = new SalesService();
export default salesService;
