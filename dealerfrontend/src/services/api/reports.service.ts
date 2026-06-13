/**
 * Reports Service — Summary Stats, Due Reports & AI Reconciliation
 *
 * Endpoints mapped:
 * GET  /reports/summary              → getSummary()
 * GET  /reports/customer-due         → getCustomerDue()
 * GET  /reports/vehicle-due          → getVehicleDue()
 * GET  /reports/dsr-due              → getDsrDue()
 * POST /reports/ai-reconciliation    → getAiReconciliation()
 */

import apiClient, { ApiResponse } from "../apiClient";
import type { DueReport } from "../../types";

// ─── Response Types ────────────────────────────────────────────────────────────

export interface SummaryData {
  revenue: number;
  cogs: number;
  grossProfit: number;
  creditPending: number;
  creditPendingCount: number;
  creditCollected: number;
  writtenOffAmount: number; // Revenue lost to bad debt (written-off sales)
  writtenOffOutstanding: number; // Uncollected portion of written-off
  lowStockCount: number;
  lowStockItems: Array<{
    id: string;
    name: string;
    stock: number;
    minStockAlert: number;
    category: string;
  }>;
  dsrPerformance: Array<{
    id: string;
    name: string;
    role: string;
    parentDsrId?: string;
    parentDsrName?: string;
    totalSales: number;
    collected: number;
    pending: number;
    count: number;
  }>;
  productPerformance: Array<{
    name: string;
    quantity: number;
    total: number;
  }>;
  totalSalesCount: number;
  totalProductsCount: number;
  dealer?: {
    businessName: string;
    address: string;
    phoneNumber: string;
    email: string;
    gstNumber: string;
    googleMapUrl: string;
    communicationNumber: string;
    defaultCurrency: string;
    defaultLocale: string;
  } | null;
}

export interface AiReconciliationResponse {
  text: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class ReportsService {
  /** GET /reports/summary — Fetch computed summary statistics */
  async getSummary(dealerUsername?: string): Promise<ApiResponse<SummaryData>> {
    const endpoint = dealerUsername
      ? `/reports/summary?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/reports/summary";
    return apiClient.get<SummaryData>(endpoint);
  }

  /** GET /reports/customer-due — Customer-wise due report (for print) */
  async getCustomerDue(
    dealerUsername?: string,
  ): Promise<ApiResponse<DueReport>> {
    const endpoint = dealerUsername
      ? `/reports/customer-due?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/reports/customer-due";
    return apiClient.get<DueReport>(endpoint);
  }

  /** GET /reports/vehicle-due — Vehicle-wise due report (for print) */
  async getVehicleDue(
    dealerUsername?: string,
  ): Promise<ApiResponse<DueReport>> {
    const endpoint = dealerUsername
      ? `/reports/vehicle-due?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/reports/vehicle-due";
    return apiClient.get<DueReport>(endpoint);
  }

  /** GET /reports/dsr-due — DSR/Collector-wise due report (for print) */
  async getDsrDue(dealerUsername?: string): Promise<ApiResponse<DueReport>> {
    const endpoint = dealerUsername
      ? `/reports/dsr-due?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/reports/dsr-due";
    return apiClient.get<DueReport>(endpoint);
  }

  /** POST /reports/ai-reconciliation — Trigger AI reconciliation analysis */
  async getAiReconciliation(): Promise<ApiResponse<AiReconciliationResponse>> {
    return apiClient.post<AiReconciliationResponse>(
      "/reports/ai-reconciliation",
    );
  }
}

export const reportsService = new ReportsService();
export default reportsService;
