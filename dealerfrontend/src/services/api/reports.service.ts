/**
 * Reports Service — Summary Stats, Due Reports & AI Reconciliation
 *
 * Endpoints mapped:
 * GET  /api/reports/summary              → getSummary()
 * GET  /api/reports/customer-due         → getCustomerDue()
 * GET  /api/reports/vehicle-due          → getVehicleDue()
 * GET  /api/reports/dsr-due              → getDsrDue()
 * POST /api/reports/ai-reconciliation    → getAiReconciliation()
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
  /** GET /api/reports/summary — Fetch computed summary statistics */
  async getSummary(dealerUsername?: string): Promise<ApiResponse<SummaryData>> {
    const endpoint = dealerUsername
      ? `/api/reports/summary?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/api/reports/summary";
    return apiClient.get<SummaryData>(endpoint);
  }

  /** GET /api/reports/customer-due — Customer-wise due report (for print) */
  async getCustomerDue(
    dealerUsername?: string,
  ): Promise<ApiResponse<DueReport>> {
    const endpoint = dealerUsername
      ? `/api/reports/customer-due?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/api/reports/customer-due";
    return apiClient.get<DueReport>(endpoint);
  }

  /** GET /api/reports/vehicle-due — Vehicle-wise due report (for print) */
  async getVehicleDue(
    dealerUsername?: string,
  ): Promise<ApiResponse<DueReport>> {
    const endpoint = dealerUsername
      ? `/api/reports/vehicle-due?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/api/reports/vehicle-due";
    return apiClient.get<DueReport>(endpoint);
  }

  /** GET /api/reports/dsr-due — DSR/Collector-wise due report (for print) */
  async getDsrDue(dealerUsername?: string): Promise<ApiResponse<DueReport>> {
    const endpoint = dealerUsername
      ? `/api/reports/dsr-due?dealer_username=${encodeURIComponent(dealerUsername)}`
      : "/api/reports/dsr-due";
    return apiClient.get<DueReport>(endpoint);
  }

  /** POST /api/reports/ai-reconciliation — Trigger AI reconciliation analysis */
  async getAiReconciliation(): Promise<ApiResponse<AiReconciliationResponse>> {
    return apiClient.post<AiReconciliationResponse>(
      "/api/reports/ai-reconciliation",
    );
  }
}

export const reportsService = new ReportsService();
export default reportsService;
