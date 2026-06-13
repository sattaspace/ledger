/**
 * API Client — centralized fetch wrapper for the Sattabase backend.
 *
 * All API calls go through here so auth headers, error handling,
 * and token refresh are handled in one place. Designed for use in
 * Vue components (client-side only) within an AstroJS sister domain.
 *
 * Usage:
 *   import { apiClient } from "@/lib/api";
 *   const data = await apiClient.get("/billing/auth/me");
 *   const result = await apiClient.post("/auth/login", { email, password });
 */

import config from "../../sattabase.config";
import type { ApiError } from "./types";

// ─── Constants ───────────────────────────────────────────────────────────────

export const API_BASE_URL = config.apiBaseUrl;
export const DEALER_API_URL = config.dealerApiBaseUrl;

const TOKEN_KEY_ACCESS = `${config.tokenKeyPrefix}access_token`;
const TOKEN_KEY_REFRESH = `${config.tokenKeyPrefix}refresh_token`;
const REMEMBER_KEY = `${config.tokenKeyPrefix}remember_me`;
const DEALER_CONTEXT_KEY = "dealercore:selected_dealer";

// ─── In-memory token cache ───────────────────────────────────────────────────

let _accessToken: string | null = null;
let _refreshToken: string | null = null;

// ─── Token Persistence ───────────────────────────────────────────────────────

/**
 * Token persistence strategy:
 *   - Default: sessionStorage — survives full page reloads within the tab,
 *     cleared when tab/window closes. Good balance of convenience + security.
 *   - "Remember me": localStorage — persists across tabs and browser restarts.
 *   - Tokens are kept in-memory for fast access, with storage as the
 *     persistence layer that survives page reloads.
 */

/** Pick the correct storage backend based on "remember me" preference. */
function tokenStorage(): Storage {
  if (typeof window === "undefined") return sessionStorage;
  try {
    return localStorage.getItem(REMEMBER_KEY) === "true"
      ? localStorage
      : sessionStorage;
  } catch {
    return sessionStorage;
  }
}

/** Recover tokens from storage into memory (called on module init). */
function initTokens(): void {
  if (typeof window === "undefined") return;
  try {
    const access =
      sessionStorage.getItem(TOKEN_KEY_ACCESS) ||
      localStorage.getItem(TOKEN_KEY_ACCESS);
    const refresh =
      sessionStorage.getItem(TOKEN_KEY_REFRESH) ||
      localStorage.getItem(TOKEN_KEY_REFRESH);
    if (access) _accessToken = access;
    if (refresh) _refreshToken = refresh;
  } catch {
    /* storage unavailable */
  }
}

// Recover tokens immediately so they're available before middleware runs
initTokens();

// ─── Token Accessors ─────────────────────────────────────────────────────────

/** Get the current access token from memory. */
export function getAccessToken(): string | null {
  return _accessToken;
}

/** Get the current refresh token from memory. */
function getRefreshToken(): string | null {
  return _refreshToken;
}

/**
 * Store tokens in memory AND the active storage backend.
 * @param remember - true → localStorage (30-day persistence), false → sessionStorage
 */
export function setTokens(
  access: string,
  refresh: string,
  remember = false,
): void {
  _accessToken = access;
  _refreshToken = refresh;

  if (typeof window === "undefined") return;
  try {
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem(TOKEN_KEY_ACCESS, access);
    storage.setItem(TOKEN_KEY_REFRESH, refresh);
    localStorage.setItem(REMEMBER_KEY, String(remember));
  } catch {
    /* storage unavailable */
  }
}

/** Clear tokens from memory AND both storage backends. */
export function clearTokens(): void {
  _accessToken = null;
  _refreshToken = null;

  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(TOKEN_KEY_ACCESS);
    sessionStorage.removeItem(TOKEN_KEY_REFRESH);
    localStorage.removeItem(TOKEN_KEY_ACCESS);
    localStorage.removeItem(TOKEN_KEY_REFRESH);
    localStorage.removeItem(REMEMBER_KEY);
  } catch {
    /* storage unavailable */
  }
}

/** Check if the user is authenticated (has a non-expired access token). */
export function isAuthenticated(): boolean {
  return !!_accessToken;
}

// ─── Request Headers ─────────────────────────────────────────────────────────

/**
 * Get the selected dealer username from localStorage.
 * Used for multi-tenant API requests.
 */
export function getSelectedDealerUsername(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const username = localStorage.getItem(DEALER_CONTEXT_KEY);
    console.log("%c[API] getSelectedDealerUsername", "color: #8b5cf6;", {
      key: DEALER_CONTEXT_KEY,
      username,
    });
    return username;
  } catch {
    return null;
  }
}

/**
 * Set the selected dealer username in localStorage.
 */
export function setSelectedDealerUsername(username: string): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(DEALER_CONTEXT_KEY, username);
  } catch {
    // Storage unavailable
  }
}

/**
 * Clear the selected dealer username from localStorage.
 */
export function clearSelectedDealerUsername(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(DEALER_CONTEXT_KEY);
  } catch {
    // Storage unavailable
  }
}

function buildHeaders(
  custom?: Record<string, string>,
  useDealerBackend = false,
): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...custom,
  };

  // If Content-Type was explicitly overridden to empty string,
  // remove it so the browser auto-sets multipart boundary for FormData uploads.
  if (headers["Content-Type"] === "") {
    delete headers["Content-Type"];
  }

  // Inject the service domain header so the backend returns
  // domain-scoped subscription and access data
  // (only for SattaBase API calls, not dealer backend)
  if (!useDealerBackend && config.serviceDomain) {
    headers["X-Service-Domain"] = config.serviceDomain;
  }

  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Inject X-Dealer-Username for dealer backend API calls (multi-tenancy)
  // This header tells the backend which dealer's data to access
  if (useDealerBackend) {
    const dealerUsername = getSelectedDealerUsername();
    if (dealerUsername) {
      headers["X-Dealer-Username"] = dealerUsername;
    }
  }

  return headers;
}

// ─── Token Refresh ───────────────────────────────────────────────────────────

let refreshPromise: Promise<string | null> | null = null;

/**
 * Refresh the access token using the stored refresh token.
 * Deduplicates concurrent refresh calls so only one request is made.
 */
export async function refreshAccessToken(): Promise<string | null> {
  // Deduplicate concurrent refresh calls
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const refresh = getRefreshToken();
      if (!refresh) return null;

      const response = await fetch(`${API_BASE_URL}/auth/token/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });

      if (!response.ok) {
        clearTokens();
        return null;
      }

      const data = await response.json();
      if (data.access) {
        _accessToken = data.access;
        if (data.refresh) {
          _refreshToken = data.refresh;
        }
        // Persist refreshed tokens to storage
        if (typeof window !== "undefined") {
          try {
            const storage = tokenStorage();
            storage.setItem(TOKEN_KEY_ACCESS, _accessToken!);
            if (data.refresh)
              storage.setItem(TOKEN_KEY_REFRESH, _refreshToken!);
          } catch {
            /* storage unavailable */
          }
        }
        return data.access;
      }

      return null;
    } catch {
      clearTokens();
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

// ─── URL Builder ─────────────────────────────────────────────────────────────

function buildUrl(
  path: string,
  baseUrl: string,
  params?: Record<string, string | number | boolean>,
): string {
  let url = `${baseUrl}${path}`;
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

// ─── Request Options ─────────────────────────────────────────────────────────

interface RequestOptions extends RequestInit {
  /** Query parameters to append to the URL. */
  params?: Record<string, string | number | boolean>;
  /** Use dealer backend instead of SattaBase backend. */
  useDealerBackend?: boolean;
}

// ─── Core Request Handler ────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { params, useDealerBackend = false, ...restOptions } = options;
  const baseUrl = useDealerBackend ? DEALER_API_URL : API_BASE_URL;
  const url = buildUrl(path, baseUrl, params);
  const headers = buildHeaders(
    restOptions.headers as Record<string, string> | undefined,
    useDealerBackend,
  );

  const fetchOptions: RequestInit = {
    ...restOptions,
    headers,
    cache: "no-store",
  };

  let response = await fetch(url, fetchOptions);

  // ── 401 → try token refresh (only for SattaBase API) ──
  if (response.status === 401 && !useDealerBackend && getRefreshToken()) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = buildHeaders(
        options.headers as Record<string, string> | undefined,
        useDealerBackend,
      );
      retryHeaders["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...fetchOptions, headers: retryHeaders });
    } else {
      // Refresh failed — clear tokens and redirect to login
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/auth/login";
      }
      throw createApiError(response, "Session expired. Please sign in again.");
    }
  }

  // ── Non-OK response → throw ──
  if (!response.ok) {
    throw await createApiErrorFromResponse(response);
  }

  // ── 204 No Content ──
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

// ─── Error Factory ───────────────────────────────────────────────────────────

async function createApiErrorFromResponse(
  response: Response,
): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`;

  try {
    const body = await response.json();
    if (typeof body === "object" && body !== null) {
      // Django Ninja typically returns { detail: "..." } or { message: "..." }
      if (body.detail) message = body.detail;
      else if (body.message) message = body.message;
      else if (body.non_field_errors?.[0]) message = body.non_field_errors[0];

      // Handle validation error format
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
          message = fieldLabel
            ? `${fieldLabel}: ${firstError.message}`
            : firstError.message;
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
    // Body wasn't JSON — use default message
  }

  return createApiError(response, message);
}

function createApiError(response: Response, message: string): ApiError {
  return { status: response.status, message };
}

// ─── API Client ──────────────────────────────────────────────────────────────

export const apiClient = {
  /**
   * GET request. Supports `params` for query string parameters.
   */
  async get<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, { method: "GET", ...options });
  },

  /**
   * POST request
   */
  async post<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });
  },

  /**
   * PUT request
   */
  async put<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    return request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });
  },

  /**
   * PATCH request
   */
  async patch<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    return request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });
  },

  /**
   * DELETE request
   */
  async del<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, { method: "DELETE", ...options });
  },
};

// ─── Dealer API Client ───────────────────────────────────────────────────────

/**
 * Dealer API client for business data endpoints.
 * Use this for inventory, sales, DSR, supplier, and dealer endpoints.
 */
export const dealerApi = {
  async get<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, {
      method: "GET",
      useDealerBackend: true,
      ...options,
    });
  },

  async post<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      useDealerBackend: true,
      ...options,
    });
  },

  async patch<T = unknown>(
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<T> {
    return request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
      useDealerBackend: true,
      ...options,
    });
  },

  async del<T = unknown>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>(path, {
      method: "DELETE",
      useDealerBackend: true,
      ...options,
    });
  },
};

// ─── Media URL Helper ────────────────────────────────────────────────────────

/**
 * Convert a relative media path to a full URL pointing at the backend server.
 * Returns null if path is falsy.
 */
export function getMediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  const origin = DEALER_API_URL.replace(/\/api\/?$/, "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${origin}${normalized}`;
}

// ─── Auth Helpers ────────────────────────────────────────────────────────────

export const authHelpers = {
  setTokens,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isAuthenticated,
};
