/**
 * Reports Service — Summary Stats & AI Reconciliation
 *
 * Endpoints mapped:
 * GET  /api/reports/summary              → getSummary()
 * POST /api/reports/ai-reconciliation   → getAiReconciliation()
 */

import apiClient, { ApiResponse } from "../apiClient";

// ─── Response Types ────────────────────────────────────────────────────────────

export interface SummaryData {
  revenue: number;
  cogs: number;
  grossProfit: number;
  creditPending: number;
  creditCollected: number;
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
}

export interface AiReconciliationResponse {
  text: string;
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class ReportsService {
  /** GET /api/reports/summary — Fetch computed summary statistics */
  async getSummary(): Promise<ApiResponse<SummaryData>> {
    return apiClient.get<SummaryData>("/api/reports/summary");
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
