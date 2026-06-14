/**
 * DEALERCORE v3.0 — Centralized API Services Barrel Export
 *
 * Import everything from this single file:
 *
 *   import { inventoryService, salesService, ... } from '../services/api';
 *
 * This is the ONLY place components should import API services from.
 * Never import fetch() directly in components.
 *
 * NOTE: This file exports the dealer backend API client.
 * For SattaBase auth/billing API, use `apiClient` from `lib/api.ts`.
 */

// Re-export from dealer apiClient (for dealer backend business data)
export { apiClient, ApiError } from "../apiClient";
export type { ApiResponse, RequestConfig } from "../apiClient";

// Re-export SattaBase API client (for auth/billing)
export {
  apiClient as sattabaseClient,
  dealerApi,
  authHelpers,
} from "../../lib/api";
export type { ApiError as SattabaseApiError } from "../../lib/types";

// Services
export { inventoryService, InventoryService } from "./inventory.service";
export type {
  AddProductPayload,
  RestockPayload,
  EditProductPayload,
} from "./inventory.service";

export { salesService, SalesService } from "./sales.service";
export type {
  CreateSalePayload,
  BulkSalePayload,
  BulkSaleRow,
  CollectPaymentPayload,
} from "./sales.service";

export { dsrService, DsrService } from "./dsr.service";
export type { UpdateDsrPayload } from "./dsr.service";

export { supplierService, SupplierService } from "./supplier.service";
export type {
  CreateSupplierPayload,
  UpdateSupplierPayload,
} from "./supplier.service";

export { dealerService, DealerService } from "./dealer.service";
export type { UpdateDealerPayload } from "./dealer.service";

export { reportsService, ReportsService } from "./reports.service";
export type { SummaryData, AiReconciliationResponse } from "./reports.service";
