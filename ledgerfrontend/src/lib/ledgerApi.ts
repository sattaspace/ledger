/**
 * Ledger API Service — typed wrapper for all Ledger backend endpoints.
 *
 * Uses the same JWT auth + token refresh machinery as the core Sattabase
 * apiClient, but targets the separate Ledger backend at localhost:8087.
 *
 * All 95 endpoints across 13 domain controllers are mapped here as
 * fully-typed methods. Pinia stores and composables should use this
 * service exclusively for Ledger data — never call apiClient directly
 * for ledgerbackend URLs.
 *
 * Usage:
 *   import { ledgerApi } from "@/lib/ledgerApi";
 *   const institutions = await ledgerApi.institutions.list({ search: "Chase" });
 *   const account = await ledgerApi.accounts.get(42);
 */

import config from "../../sattabase.config";
import { getAccessToken, refreshAccessToken, clearTokens } from "./api";
import type { ApiError } from "./types";
import { useToast } from "@/composables/useToast";

// ─── Auth Event Helper ───────────────────────────────────────────────────────

/**
 * Dispatch global auth events when the session expires so UI components
 * (sidebar, navbar, etc.) can react immediately instead of staying stale.
 */
function dispatchAuthExpired(): void {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(
      new CustomEvent("auth-expired", { detail: { reason: "session_expired" } }),
    );
    window.dispatchEvent(
      new CustomEvent("auth-state-changed", { detail: { authenticated: false } }),
    );
  } catch {
    // Event dispatch is best-effort
  }
}

// ─── Ledger-specific type imports ────────────────────────────────────────────

import type {
  // Common
  PaginationIn,
  PaginatedResponse,
  MessageOut,
  // Core
  InstitutionOut,
  InstitutionListOut,
  InstitutionCreate,
  InstitutionUpdate,
  InstitutionFilter,
  AccountOut,
  AccountListOut,
  AccountCreate,
  AccountUpdate,
  AccountFilter,
  BalanceRecalculateOut,
  TransactionOut,
  TransactionListOut,
  TransactionCreate,
  TransactionUpdate,
  TransactionFilter,
  TransferCreate,
  TransferOut,
  TransactionSplitOut,
  TransactionSplitCreate,
  TransactionSplitUpdate,
  // Categories
  CategoryOut,
  CategoryListOut,
  CategoryTreeOut,
  CategoryCreate,
  CategoryUpdate,
  CategoryFilter,
  TagOut,
  TagListOut,
  TagCreate,
  TagUpdate,
  TagFilter,
  TransactionTagOut,
  TransactionTagCreate,
  TransactionTagBulkCreate,
  TransactionTagBulkOut,
  // Cards
  CardOut,
  CardListOut,
  CardCreate,
  CardUpdate,
  CardFilter,
  // Bills
  BillOut,
  BillListOut,
  BillCreate,
  BillUpdate,
  BillFilter,
  BillGenerateTransactionOut,
  BillPaymentOut,
  BillPaymentCreate,
  BillPaymentUpdate,
  // Debt
  DebtFacilityOut,
  DebtFacilityCreate,
  DebtFacilityUpdate,
  DebtFacilityFilter,
  DebtSummary,
  DebtPaymentOut,
  DebtPaymentCreate,
  DebtPaymentUpdate,
  // Budgets
  BudgetOut,
  BudgetListOut,
  BudgetCreate,
  BudgetUpdate,
  BudgetFilter,
  // Investments
  InvestmentAccountOut,
  InvestmentAccountCreate,
  InvestmentAccountUpdate,
  InvestmentSummary,
  HoldingOut,
  HoldingCreate,
  HoldingUpdate,
  // Goals
  SavingsGoalOut,
  SavingsGoalListOut,
  SavingsGoalCreate,
  SavingsGoalUpdate,
  SavingsGoalFilter,
  SavingsContribution,
  SavingsContributionOut,
  // Insurance
  InsurancePolicyOut,
  InsurancePolicyListOut,
  InsurancePolicyCreate,
  InsurancePolicyUpdate,
  InsurancePolicyFilter,
  // Invoices
  InvoiceOut,
  InvoiceListOut,
  InvoiceCreate,
  InvoiceUpdate,
  InvoiceFilter,
  InvoiceMarkPaid,
  InvoiceLineItemOut,
  InvoiceLineItemCreate,
  InvoiceLineItemUpdate,
  // Vault
  DocumentVaultOut,
  DocumentVaultListOut,
  DocumentVaultCreate,
  DocumentVaultUpdate,
  DocumentVaultFilter,
} from "./ledgerTypes";

// ─── Ledger API Base URL ─────────────────────────────────────────────────────

const LEDGER_BASE_URL = config.ledgerApiUrl;

// ─── Internal Request Handler ────────────────────────────────────────────────
//
// Mirrors the core apiClient's request logic but targets the Ledger backend.
// Shares the same token pool (JWT access/refresh) so the user's Sattabase
// SSO session is reused for both backends.

interface LedgerRequestOptions extends RequestInit {
  /** Query parameters appended to the URL. */
  params?: Record<string, string | number | boolean | undefined | null>;
}

/** Build a full URL with optional query string. */
function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
): string {
  let url = `${LEDGER_BASE_URL}${path}`;
  if (params && Object.keys(params).length > 0) {
    const qs = new URLSearchParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== undefined && val !== null && val !== "") {
        qs.append(key, String(val));
      }
    }
    const qsStr = qs.toString();
    if (qsStr) url += (url.includes("?") ? "&" : "?") + qsStr;
  }
  return url;
}

/** Build request headers with JWT + service-domain. */
function buildHeaders(custom?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...custom,
  };

  // Remove Content-Type if explicitly set to empty string
  // (for FormData uploads where browser must set the boundary)
  if (headers["Content-Type"] === "") {
    delete headers["Content-Type"];
  }

  // Service domain header — same as Sattabase core, required by Ledger auth middleware
  if (config.serviceDomain) {
    headers["X-Service-Domain"] = config.serviceDomain;
  }

  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/** Create a typed ApiError from a Response object. */
async function createApiErrorFromResponse(response: Response): Promise<ApiError> {
  let message = `Ledger API request failed with status ${response.status}`;

  try {
    const body = await response.json();
    if (typeof body === "object" && body !== null) {
      // Django Ninja error formats
      if (body.detail) message = body.detail;
      else if (body.message) message = body.message;
      else if (body.non_field_errors?.[0]) message = body.non_field_errors[0];

      // Validation error (ninja-style)
      if (
        body.code === "validation_error" &&
        Array.isArray(body.errors) &&
        body.errors.length > 0
      ) {
        const firstError = body.errors[0];
        if (firstError.message) {
          const fieldLabel = (firstError.field || "")
            .replace(/payload\.\s*/g, "")
            .replace(/body\.\s*/g, "")
            .replace(/_/g, " ")
            .replace(/\b\w/g, (c: string) => c.toUpperCase());
          message = fieldLabel ? `${fieldLabel}: ${firstError.message}` : firstError.message;
        }
      }

      // Field-level errors (dict format)
      const fieldErrors: Record<string, string[]> = {};
      for (const [key, value] of Object.entries(body)) {
        if (
          key !== "detail" &&
          key !== "message" &&
          key !== "non_field_errors" &&
          key !== "code" &&
          key !== "errors"
        ) {
          if (Array.isArray(value)) {
            fieldErrors[key] = value.map(String);
          } else if (typeof value === "string") {
            fieldErrors[key] = [value];
          }
        }
      }
      if (Object.keys(fieldErrors).length > 0) {
        return { status: response.status, message, errors: fieldErrors };
      }
    }
  } catch {
    // Body wasn't JSON
  }

  return { status: response.status, message };
}

/**
 * Core request function for the Ledger backend.
 *
 * - Injects JWT Bearer token from the shared Sattabase auth pool
 * - Auto-refreshes on 401 (same deduped refresh as apiClient)
 * - Parses Django Ninja error format
 */
async function ledgerRequest<T>(path: string, options: LedgerRequestOptions = {}): Promise<T> {
  const { params, ...restOptions } = options;
  const url = buildUrl(path, params);
  const headers = buildHeaders(restOptions.headers as Record<string, string> | undefined);

  const fetchOptions: RequestInit = {
    ...restOptions,
    headers,
    cache: "no-store",
  };

  let response: Response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (fetchError) {
    // Network error (offline, DNS failure, CORS, etc.)
    try {
      useToast().error("Network error. Please check your connection.");
    } catch {}
    throw {
      status: 0,
      message: fetchError instanceof Error ? fetchError.message : "Network error",
    } as ApiError;
  }

  // ── 401 → try token refresh ──
  if (response.status === 401) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = buildHeaders(options.headers as Record<string, string> | undefined);
      retryHeaders["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...fetchOptions, headers: retryHeaders });
    } else {
      // Refresh failed — clear tokens, notify UI, and redirect to login
      clearTokens();
      dispatchAuthExpired();
      if (typeof window !== "undefined") {
        const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/auth/login?return_url=${returnUrl}`;
      }
      throw {
        status: 401,
        message: "Session expired. Please sign in again.",
      } as ApiError;
    }
  }

  // ── 403 Forbidden ──
  if (response.status === 403) {
    const apiError = await createApiErrorFromResponse(response);
    // If the 403 is due to authentication (not authorization), redirect to login
    const isAuthError =
      apiError.message?.toLowerCase().includes("authentication") ||
      apiError.message?.toLowerCase().includes("token") ||
      apiError.message?.toLowerCase().includes("credentials") ||
      apiError.message?.toLowerCase().includes("not authenticated");

    if (isAuthError) {
      clearTokens();
      dispatchAuthExpired();
      if (typeof window !== "undefined") {
        const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
        window.location.href = `/auth/login?return_url=${returnUrl}`;
      }
    } else {
      // Authorization error — show toast but don't redirect
      try {
        useToast().error("You don't have access to this resource");
      } catch {}
    }
    throw apiError;
  }

  // ── 429 Rate Limited ──
  if (response.status === 429) {
    try {
      useToast().warning("Too many requests. Please wait a moment.");
    } catch {}
    throw await createApiErrorFromResponse(response);
  }

  // ── 5xx Server Error ──
  if (response.status >= 500) {
    try {
      useToast().error("Something went wrong. Please try again.");
    } catch {}
    throw await createApiErrorFromResponse(response);
  }

  // ── Non-OK → throw ──
  if (!response.ok) {
    throw await createApiErrorFromResponse(response);
  }

  // ── 204 No Content ──
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ─── Thin HTTP method wrappers ───────────────────────────────────────────────

async function ledgerGet<T = unknown>(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>,
): Promise<T> {
  const opts: LedgerRequestOptions = { method: "GET" };
  if (params) opts.params = params;
  return ledgerRequest<T>(path, opts);
}

async function ledgerPost<T = unknown>(
  path: string,
  body?: unknown,
  options?: LedgerRequestOptions,
): Promise<T> {
  const opts: LedgerRequestOptions = {
    method: "POST",
    ...options,
  };
  if (body) opts.body = JSON.stringify(body);
  return ledgerRequest<T>(path, opts);
}

async function ledgerPatch<T = unknown>(
  path: string,
  body?: unknown,
  options?: LedgerRequestOptions,
): Promise<T> {
  const opts: LedgerRequestOptions = {
    method: "PATCH",
    ...options,
  };
  if (body) opts.body = JSON.stringify(body);
  return ledgerRequest<T>(path, opts);
}

async function ledgerDel<T = unknown>(path: string): Promise<T> {
  return ledgerRequest<T>(path, { method: "DELETE" });
}

// ─── Helper: convert filter object to query params ───────────────────────────
//
// Strips null/undefined values and converts to a flat Record suitable
// for the URL builder. Pagination fields (limit, offset) are included.

function filterToParams<F extends PaginationIn>(
  filter?: F,
): Record<string, string | number | boolean | undefined | null> {
  if (!filter) return {};
  const params: Record<string, string | number | boolean | undefined | null> = {};
  for (const [key, val] of Object.entries(filter)) {
    if (val !== undefined && val !== null && val !== "") {
      params[key] = val;
    }
  }
  return params;
}

// ─── API Endpoint Groups ─────────────────────────────────────────────────────

/** Institutions — `/institutions` */
export const institutions = {
  /** List institutions with pagination and filters. */
  list(filters?: InstitutionFilter): Promise<PaginatedResponse<InstitutionOut>> {
    return ledgerGet("/institutions", filterToParams(filters));
  },

  /** Lightweight list for dropdown/select components. */
  dropdown(): Promise<InstitutionListOut[]> {
    return ledgerGet("/institutions/dropdown");
  },

  /** Get a single institution by ID. */
  get(id: number): Promise<InstitutionOut> {
    return ledgerGet(`/institutions/${id}`);
  },

  /** Create a new institution. */
  create(data: InstitutionCreate): Promise<InstitutionOut> {
    return ledgerPost("/institutions", data);
  },

  /** Update an existing institution (partial). */
  update(id: number, data: InstitutionUpdate): Promise<InstitutionOut> {
    return ledgerPatch(`/institutions/${id}`, data);
  },

  /** Soft-delete an institution. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/institutions/${id}`);
  },

  /** Restore a soft-deleted institution. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/institutions/${id}/restore`);
  },

  /** Activate an institution. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/institutions/${id}/activate`);
  },

  /** Deactivate an institution. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/institutions/${id}/deactivate`);
  },
};

/** Accounts — `/accounts` */
export const accounts = {
  /** List accounts with pagination and filters. */
  list(filters?: AccountFilter): Promise<PaginatedResponse<AccountOut>> {
    return ledgerGet("/accounts", filterToParams(filters));
  },

  /** Lightweight list for dropdown/select components. */
  dropdown(): Promise<AccountListOut[]> {
    return ledgerGet("/accounts/dropdown");
  },

  /** Get a single account by ID. */
  get(id: number): Promise<AccountOut> {
    return ledgerGet(`/accounts/${id}`);
  },

  /** Create a new account linked to an institution. */
  create(data: AccountCreate): Promise<AccountOut> {
    return ledgerPost("/accounts", data);
  },

  /** Update an existing account (partial). */
  update(id: number, data: AccountUpdate): Promise<AccountOut> {
    return ledgerPatch(`/accounts/${id}`, data);
  },

  /** Recalculate account balance from transactions. */
  recalculateBalance(id: number): Promise<BalanceRecalculateOut> {
    return ledgerPost(`/accounts/${id}/recalculate-balance`);
  },

  /** Soft-delete an account. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/accounts/${id}`);
  },

  /** Restore a soft-deleted account. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/accounts/${id}/restore`);
  },

  /** Activate an account. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/accounts/${id}/activate`);
  },

  /** Deactivate an account. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/accounts/${id}/deactivate`);
  },
};

/** Transactions — `/transactions` */
export const transactions = {
  /** List transactions with advanced filters and pagination. */
  list(filters?: TransactionFilter): Promise<PaginatedResponse<TransactionOut>> {
    return ledgerGet("/transactions", filterToParams(filters));
  },

  /** Get the most recent transactions (for dashboard). */
  recent(limit?: number): Promise<TransactionListOut[]> {
    return ledgerGet("/transactions/recent", { limit: limit ?? 10 });
  },

  /** Get a single transaction by ID. */
  get(id: number): Promise<TransactionOut> {
    return ledgerGet(`/transactions/${id}`);
  },

  /** Create a new transaction. */
  create(data: TransactionCreate): Promise<TransactionOut> {
    return ledgerPost("/transactions", data);
  },

  /** Update an existing transaction (partial). */
  update(id: number, data: TransactionUpdate): Promise<TransactionOut> {
    return ledgerPatch(`/transactions/${id}`, data);
  },

  /** Create an internal transfer between two accounts. */
  createTransfer(data: TransferCreate): Promise<TransferOut> {
    return ledgerPost("/transactions/transfer", data);
  },

  /** Soft-delete a transaction. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/transactions/${id}`);
  },

  /** Restore a soft-deleted transaction. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/transactions/${id}/restore`);
  },
};

/** Transaction Splits — `/transactions/{id}/splits` */
export const splits = {
  /** List all splits for a transaction. */
  list(transactionId: number): Promise<TransactionSplitOut[]> {
    return ledgerGet(`/transactions/${transactionId}/splits`);
  },

  /** Add a split to a transaction. */
  create(
    transactionId: number,
    data: Omit<TransactionSplitCreate, "transaction_id">,
  ): Promise<TransactionSplitOut> {
    return ledgerPost(`/transactions/${transactionId}/splits`, data);
  },

  /** Update an existing split. */
  update(
    transactionId: number,
    splitId: number,
    data: TransactionSplitUpdate,
  ): Promise<TransactionSplitOut> {
    return ledgerPatch(`/transactions/${transactionId}/splits/${splitId}`, data);
  },

  /** Delete a split from a transaction. */
  remove(transactionId: number, splitId: number): Promise<MessageOut> {
    return ledgerDel(`/transactions/${transactionId}/splits/${splitId}`);
  },
};

/** Transaction Tags — `/transactions/{id}/tags` */
export const transactionTags = {
  /** List all tags attached to a transaction. */
  list(transactionId: number): Promise<TransactionTagOut[]> {
    return ledgerGet(`/transactions/${transactionId}/tags`);
  },

  /** Attach a single tag to a transaction. */
  attach(
    transactionId: number,
    data: Omit<TransactionTagCreate, "transaction_id">,
  ): Promise<TransactionTagOut> {
    return ledgerPost(`/transactions/${transactionId}/tags`, data);
  },

  /** Replace all tags on a transaction with the provided tag IDs. */
  bulkSet(
    transactionId: number,
    data: Omit<TransactionTagBulkCreate, "transaction_id">,
  ): Promise<TransactionTagBulkOut> {
    return ledgerPost(`/transactions/${transactionId}/tags/bulk`, data);
  },

  /** Detach a tag from a transaction. */
  detach(transactionId: number, tagId: number): Promise<MessageOut> {
    return ledgerDel(`/transactions/${transactionId}/tags/${tagId}`);
  },
};

/** Categories — `/categories` */
export const categories = {
  /** List categories with pagination and filters. */
  list(filters?: CategoryFilter): Promise<PaginatedResponse<CategoryOut>> {
    return ledgerGet("/categories", filterToParams(filters));
  },

  /** Lightweight list for dropdown/select components. */
  dropdown(): Promise<CategoryListOut[]> {
    return ledgerGet("/categories/dropdown");
  },

  /** Get categories as a tree structure for hierarchical display. */
  tree(): Promise<CategoryTreeOut[]> {
    return ledgerGet("/categories/tree");
  },

  /** Get a single category by ID. */
  get(id: number): Promise<CategoryOut> {
    return ledgerGet(`/categories/${id}`);
  },

  /** Create a new category. Use parent_id for subcategories. */
  create(data: CategoryCreate): Promise<CategoryOut> {
    return ledgerPost("/categories", data);
  },

  /** Update an existing category (partial). */
  update(id: number, data: CategoryUpdate): Promise<CategoryOut> {
    return ledgerPatch(`/categories/${id}`, data);
  },

  /** Soft-delete a category. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/categories/${id}`);
  },

  /** Restore a soft-deleted category. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/categories/${id}/restore`);
  },

  /** Activate a category. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/categories/${id}/activate`);
  },

  /** Deactivate a category. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/categories/${id}/deactivate`);
  },
};

/** Tags — `/tags` */
export const tags = {
  /** List all tags with pagination and filters. */
  list(filters?: TagFilter): Promise<PaginatedResponse<TagOut>> {
    return ledgerGet("/tags", filterToParams(filters));
  },

  /** Lightweight list for tag chips/autocomplete. */
  dropdown(): Promise<TagListOut[]> {
    return ledgerGet("/tags/dropdown");
  },

  /** Get a single tag by ID. */
  get(id: number): Promise<TagOut> {
    return ledgerGet(`/tags/${id}`);
  },

  /** Create a new tag. Name must be unique per user. */
  create(data: TagCreate): Promise<TagOut> {
    return ledgerPost("/tags", data);
  },

  /** Update an existing tag. */
  update(id: number, data: TagUpdate): Promise<TagOut> {
    return ledgerPatch(`/tags/${id}`, data);
  },

  /** Soft-delete a tag. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/tags/${id}`);
  },

  /** Restore a soft-deleted tag. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/tags/${id}/restore`);
  },
};

/** Cards — `/cards` */
export const cards = {
  /** List all cards with pagination and filters. */
  list(filters?: CardFilter): Promise<PaginatedResponse<CardOut>> {
    return ledgerGet("/cards", filterToParams(filters));
  },

  /** Lightweight list for card selection components. */
  dropdown(): Promise<CardListOut[]> {
    return ledgerGet("/cards/dropdown");
  },

  /** Get a single card by ID. */
  get(id: number): Promise<CardOut> {
    return ledgerGet(`/cards/${id}`);
  },

  /** Create a new card linked to an account. */
  create(data: CardCreate): Promise<CardOut> {
    return ledgerPost("/cards", data);
  },

  /** Update an existing card. */
  update(id: number, data: CardUpdate): Promise<CardOut> {
    return ledgerPatch(`/cards/${id}`, data);
  },

  /** Soft-delete a card. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/cards/${id}`);
  },

  /** Restore a soft-deleted card. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/cards/${id}/restore`);
  },

  /** Activate a card. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/cards/${id}/activate`);
  },

  /** Deactivate a card. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/cards/${id}/deactivate`);
  },
};

/** Bills — `/bills` */
export const bills = {
  /** List bills with pagination and filters. */
  list(filters?: BillFilter): Promise<PaginatedResponse<BillOut>> {
    return ledgerGet("/bills", filterToParams(filters));
  },

  /** Get bills due within the next N days (for dashboard). */
  upcoming(days?: number): Promise<BillListOut[]> {
    return ledgerGet("/bills/upcoming", { days: days ?? 30 });
  },

  /** Get a single bill by ID. */
  get(id: number): Promise<BillOut> {
    return ledgerGet(`/bills/${id}`);
  },

  /** Create a new bill/subscription. */
  create(data: BillCreate): Promise<BillOut> {
    return ledgerPost("/bills", data);
  },

  /** Update an existing bill. */
  update(id: number, data: BillUpdate): Promise<BillOut> {
    return ledgerPatch(`/bills/${id}`, data);
  },

  /** Generate a transaction from a bill. */
  generateTransaction(id: number): Promise<BillGenerateTransactionOut> {
    return ledgerPost(`/bills/${id}/generate`);
  },

  /** Soft-delete a bill. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/bills/${id}`);
  },

  /** Restore a soft-deleted bill. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/bills/${id}/restore`);
  },

  /** Pause a bill (stops auto-generation). */
  pause(id: number): Promise<MessageOut> {
    return ledgerPost(`/bills/${id}/pause`);
  },

  /** Cancel a bill permanently. */
  cancel(id: number): Promise<MessageOut> {
    return ledgerPost(`/bills/${id}/cancel`);
  },

  /** Reactivate a paused or cancelled bill. */
  reactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/bills/${id}/reactivate`);
  },
};

/** Bill Payments — `/bills/{id}/payments` */
export const billPayments = {
  /** List all payments for a bill. */
  list(billId: number): Promise<BillPaymentOut[]> {
    return ledgerGet(`/bills/${billId}/payments`);
  },

  /** Record a payment for a bill. */
  create(billId: number, data: Omit<BillPaymentCreate, "bill_id">): Promise<BillPaymentOut> {
    return ledgerPost(`/bills/${billId}/payments`, data);
  },

  /** Update a bill payment. */
  update(billId: number, paymentId: number, data: BillPaymentUpdate): Promise<BillPaymentOut> {
    return ledgerPatch(`/bills/${billId}/payments/${paymentId}`, data);
  },
};

/** Debts — `/debts` */
export const debts = {
  /** List debt facilities with pagination and filters. */
  list(filters?: DebtFacilityFilter): Promise<PaginatedResponse<DebtFacilityOut>> {
    return ledgerGet("/debts", filterToParams(filters));
  },

  /** Get summary of total borrowed vs lent amounts. */
  summary(): Promise<DebtSummary> {
    return ledgerGet("/debts/summary");
  },

  /** Get a single debt facility by ID. */
  get(id: number): Promise<DebtFacilityOut> {
    return ledgerGet(`/debts/${id}`);
  },

  /** Create a new debt facility. */
  create(data: DebtFacilityCreate): Promise<DebtFacilityOut> {
    return ledgerPost("/debts", data);
  },

  /** Update an existing debt facility. */
  update(id: number, data: DebtFacilityUpdate): Promise<DebtFacilityOut> {
    return ledgerPatch(`/debts/${id}`, data);
  },

  /** Soft-delete a debt facility. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/debts/${id}`);
  },

  /** Restore a soft-deleted debt facility. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/debts/${id}/restore`);
  },

  /** Activate a debt facility. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/debts/${id}/activate`);
  },

  /** Deactivate a debt facility. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/debts/${id}/deactivate`);
  },
};

/** Debt Payments — `/debts/{id}/payments` */
export const debtPayments = {
  /** List all payments for a debt facility. */
  list(debtId: number): Promise<DebtPaymentOut[]> {
    return ledgerGet(`/debts/${debtId}/payments`);
  },

  /** Record a payment against a debt facility. */
  create(debtId: number, data: Omit<DebtPaymentCreate, "debt_id">): Promise<DebtPaymentOut> {
    return ledgerPost(`/debts/${debtId}/payments`, data);
  },

  /** Update a debt payment. */
  update(debtId: number, paymentId: number, data: DebtPaymentUpdate): Promise<DebtPaymentOut> {
    return ledgerPatch(`/debts/${debtId}/payments/${paymentId}`, data);
  },
};

/** Budgets — `/budgets` */
export const budgets = {
  /** List budgets with pagination and filters. */
  list(filters?: BudgetFilter): Promise<PaginatedResponse<BudgetOut>> {
    return ledgerGet("/budgets", filterToParams(filters));
  },

  /** Get all budgets with spending status (for dashboard). */
  overview(): Promise<BudgetListOut[]> {
    return ledgerGet("/budgets/overview");
  },

  /** Get a single budget by ID with computed spending. */
  get(id: number): Promise<BudgetOut> {
    return ledgerGet(`/budgets/${id}`);
  },

  /** Create a new budget for a category. */
  create(data: BudgetCreate): Promise<BudgetOut> {
    return ledgerPost("/budgets", data);
  },

  /** Update an existing budget. */
  update(id: number, data: BudgetUpdate): Promise<BudgetOut> {
    return ledgerPatch(`/budgets/${id}`, data);
  },

  /** Soft-delete a budget. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/budgets/${id}`);
  },

  /** Restore a soft-deleted budget. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/budgets/${id}/restore`);
  },

  /** Activate a budget. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/budgets/${id}/activate`);
  },

  /** Deactivate a budget. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/budgets/${id}/deactivate`);
  },
};

/** Investments — `/investments` */
export const investments = {
  /** List all investment accounts. */
  list(): Promise<PaginatedResponse<InvestmentAccountOut>> {
    return ledgerGet("/investments");
  },

  /** Get portfolio-wide summary. */
  summary(): Promise<InvestmentSummary> {
    return ledgerGet("/investments/summary");
  },

  /** Get a single investment account by ID. */
  get(id: number): Promise<InvestmentAccountOut> {
    return ledgerGet(`/investments/${id}`);
  },

  /** Create an investment profile for an existing account. */
  create(data: InvestmentAccountCreate): Promise<InvestmentAccountOut> {
    return ledgerPost("/investments", data);
  },

  /** Update an investment account. */
  update(id: number, data: InvestmentAccountUpdate): Promise<InvestmentAccountOut> {
    return ledgerPatch(`/investments/${id}`, data);
  },

  /** Soft-delete an investment account and its holdings. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/investments/${id}`);
  },

  /** Restore a soft-deleted investment account. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/investments/${id}/restore`);
  },
};

/** Holdings — `/investments/{id}/holdings` */
export const holdings = {
  /** List all holdings for an investment account. */
  list(investmentId: number): Promise<HoldingOut[]> {
    return ledgerGet(`/investments/${investmentId}/holdings`);
  },

  /** Add a holding to an investment account. */
  create(
    investmentId: number,
    data: Omit<HoldingCreate, "investment_account_id">,
  ): Promise<HoldingOut> {
    return ledgerPost(`/investments/${investmentId}/holdings`, data);
  },

  /** Update a holding. */
  update(investmentId: number, holdingId: number, data: HoldingUpdate): Promise<HoldingOut> {
    return ledgerPatch(`/investments/${investmentId}/holdings/${holdingId}`, data);
  },

  /** Soft-delete a holding. */
  remove(investmentId: number, holdingId: number): Promise<MessageOut> {
    return ledgerDel(`/investments/${investmentId}/holdings/${holdingId}`);
  },
};

/** Savings Goals — `/savings-goals` */
export const savingsGoals = {
  /** List savings goals with pagination and filters. */
  list(filters?: SavingsGoalFilter): Promise<PaginatedResponse<SavingsGoalOut>> {
    return ledgerGet("/savings-goals", filterToParams(filters));
  },

  /** Get savings goals for dashboard (active + uncompleted). */
  dashboard(): Promise<SavingsGoalListOut[]> {
    return ledgerGet("/savings-goals/dashboard");
  },

  /** Get a single savings goal by ID with progress tracking. */
  get(id: number): Promise<SavingsGoalOut> {
    return ledgerGet(`/savings-goals/${id}`);
  },

  /** Create a new savings goal. */
  create(data: SavingsGoalCreate): Promise<SavingsGoalOut> {
    return ledgerPost("/savings-goals", data);
  },

  /** Update an existing savings goal. */
  update(id: number, data: SavingsGoalUpdate): Promise<SavingsGoalOut> {
    return ledgerPatch(`/savings-goals/${id}`, data);
  },

  /** Add a contribution to a savings goal. */
  contribute(id: number, data: SavingsContribution): Promise<SavingsContributionOut> {
    return ledgerPost(`/savings-goals/${id}/contribute`, data);
  },

  /** Soft-delete a savings goal. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/savings-goals/${id}`);
  },

  /** Restore a soft-deleted savings goal. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/savings-goals/${id}/restore`);
  },

  /** Activate a savings goal. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/savings-goals/${id}/activate`);
  },

  /** Deactivate a savings goal. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/savings-goals/${id}/deactivate`);
  },
};

/** Insurance — `/insurance` */
export const insurance = {
  /** List insurance policies with pagination and filters. */
  list(filters?: InsurancePolicyFilter): Promise<PaginatedResponse<InsurancePolicyOut>> {
    return ledgerGet("/insurance", filterToParams(filters));
  },

  /** Get policies with upcoming renewals (for dashboard). */
  renewals(days?: number): Promise<InsurancePolicyListOut[]> {
    return ledgerGet("/insurance/renewals", { days: days ?? 60 });
  },

  /** Get a single insurance policy by ID. */
  get(id: number): Promise<InsurancePolicyOut> {
    return ledgerGet(`/insurance/${id}`);
  },

  /** Create a new insurance policy. */
  create(data: InsurancePolicyCreate): Promise<InsurancePolicyOut> {
    return ledgerPost("/insurance", data);
  },

  /** Update an existing insurance policy. */
  update(id: number, data: InsurancePolicyUpdate): Promise<InsurancePolicyOut> {
    return ledgerPatch(`/insurance/${id}`, data);
  },

  /** Soft-delete an insurance policy. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/insurance/${id}`);
  },

  /** Restore a soft-deleted insurance policy. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/insurance/${id}/restore`);
  },

  /** Activate an insurance policy. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/insurance/${id}/activate`);
  },

  /** Deactivate an insurance policy. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/insurance/${id}/deactivate`);
  },
};

/** Invoices — `/invoices` */
export const invoices = {
  /** List invoices with pagination and filters. */
  list(filters?: InvoiceFilter): Promise<PaginatedResponse<InvoiceOut>> {
    return ledgerGet("/invoices", filterToParams(filters));
  },

  /** Get all overdue invoices (for dashboard/alerts). */
  overdue(): Promise<InvoiceListOut[]> {
    return ledgerGet("/invoices/overdue");
  },

  /** Get a single invoice by ID. */
  get(id: number): Promise<InvoiceOut> {
    return ledgerGet(`/invoices/${id}`);
  },

  /** Create a new invoice. */
  create(data: InvoiceCreate): Promise<InvoiceOut> {
    return ledgerPost("/invoices", data);
  },

  /** Update an existing invoice. */
  update(id: number, data: InvoiceUpdate): Promise<InvoiceOut> {
    return ledgerPatch(`/invoices/${id}`, data);
  },

  /** Mark an invoice as paid. */
  markPaid(id: number, data: InvoiceMarkPaid): Promise<InvoiceOut> {
    return ledgerPost(`/invoices/${id}/mark-paid`, data);
  },

  /** Soft-delete an invoice. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/invoices/${id}`);
  },

  /** Restore a soft-deleted invoice. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/invoices/${id}/restore`);
  },
};

/** Invoice Line Items — `/invoices/{id}/line-items` */
export const invoiceLineItems = {
  /** List all line items for an invoice. */
  list(invoiceId: number): Promise<InvoiceLineItemOut[]> {
    return ledgerGet(`/invoices/${invoiceId}/line-items`);
  },

  /** Add a line item to an invoice. */
  create(
    invoiceId: number,
    data: Omit<InvoiceLineItemCreate, "invoice_id">,
  ): Promise<InvoiceLineItemOut> {
    return ledgerPost(`/invoices/${invoiceId}/line-items`, data);
  },

  /** Update a line item. */
  update(
    invoiceId: number,
    itemId: number,
    data: InvoiceLineItemUpdate,
  ): Promise<InvoiceLineItemOut> {
    return ledgerPatch(`/invoices/${invoiceId}/line-items/${itemId}`, data);
  },

  /** Delete a line item from an invoice. */
  remove(invoiceId: number, itemId: number): Promise<MessageOut> {
    return ledgerDel(`/invoices/${invoiceId}/line-items/${itemId}`);
  },
};

/** Document Vault — `/vault` */
export const vault = {
  /** List documents with pagination and filters. */
  list(filters?: DocumentVaultFilter): Promise<PaginatedResponse<DocumentVaultOut>> {
    return ledgerGet("/vault", filterToParams(filters));
  },

  /** Get documents expiring within N days (for dashboard/alerts). */
  expiring(days?: number): Promise<DocumentVaultListOut[]> {
    return ledgerGet("/vault/expiring", { days: days ?? 30 });
  },

  /** Get a single document by ID. */
  get(id: number): Promise<DocumentVaultOut> {
    return ledgerGet(`/vault/${id}`);
  },

  /**
   * Create a new document record in the vault.
   * For file uploads, use uploadFile() instead.
   */
  create(data: DocumentVaultCreate): Promise<DocumentVaultOut> {
    return ledgerPost("/vault", data);
  },

  /**
   * Upload a file to the vault with multipart form data.
   * This is the primary way to create documents — combines
   * file + metadata in a single request.
   */
  uploadFile(formData: FormData): Promise<DocumentVaultOut> {
    return ledgerRequest<DocumentVaultOut>("/vault", {
      method: "POST",
      body: formData,
      // Let browser set Content-Type with boundary for FormData
      headers: { "Content-Type": "" } as Record<string, string>,
    });
  },

  /** Update document metadata. File itself cannot be updated. */
  update(id: number, data: DocumentVaultUpdate): Promise<DocumentVaultOut> {
    return ledgerPatch(`/vault/${id}`, data);
  },

  /** Soft-delete a document. */
  remove(id: number): Promise<MessageOut> {
    return ledgerDel(`/vault/${id}`);
  },

  /** Restore a soft-deleted document. */
  restore(id: number): Promise<MessageOut> {
    return ledgerPost(`/vault/${id}/restore`);
  },

  /** Activate a document. */
  activate(id: number): Promise<MessageOut> {
    return ledgerPost(`/vault/${id}/activate`);
  },

  /** Deactivate a document. */
  deactivate(id: number): Promise<MessageOut> {
    return ledgerPost(`/vault/${id}/deactivate`);
  },
};

// ─── Unified Ledger API Object ───────────────────────────────────────────────
//
// Single import point for all Ledger API interactions.
// Pinia stores use:  import { ledgerApi } from "@/lib/ledgerApi";

export const ledgerApi = {
  institutions,
  accounts,
  transactions,
  splits,
  transactionTags,
  categories,
  tags,
  cards,
  bills,
  billPayments,
  debts,
  debtPayments,
  budgets,
  investments,
  holdings,
  savingsGoals,
  insurance,
  invoices,
  invoiceLineItems,
  vault,
} as const;

export default ledgerApi;
