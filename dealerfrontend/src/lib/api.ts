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

// Type augmentation for the server-injected token set by BaseLayout.
declare global {
  interface Window {
    /** Short-lived JWT access token minted by the Astro middleware. */
    __INITIAL_AUTH_TOKEN__?: string;
  }
}

// Cookie name for the refresh token. Must match the backend cookie name
// (backend/users/controllers.py:98 REFRESH_TOKEN_COOKIE_NAME).
const REFRESH_COOKIE_NAME = "sb_refresh_token";
const DEALER_CONTEXT_KEY = "dealercore:selected_dealer";

// ─── In-memory token cache ───────────────────────────────────────────────────

/**
 * Access token is kept IN MEMORY ONLY (`_accessToken`). Never written to
 * sessionStorage or localStorage. On page reload the in-memory copy is
 * gone; the page either renders with a fresh access token injected by
 * the Astro middleware (see BaseLayout), or the client calls
 * /auth/token/refresh-cookie to mint a new one from the httpOnly
 * refresh cookie. An XSS payload that exfiltrates storage therefore
 * cannot steal a working access token (L-6 / HIGH-03 hardening).
 *
 * Refresh token is NOT stored on the client at all. It lives in an
 * httpOnly Secure cookie (`sb_refresh_token`) set by the
 * /api/auth/login Astro proxy and forwarded by the browser
 * automatically (credentials: 'include') to Sattabase endpoints.
 *
 * Handoff from server middleware: src/middleware.ts validates the
 * refresh cookie on every page request and stores the freshly minted
 * access token on `Astro.locals.accessToken`. BaseLayout injects that
 * value into the page as `window.__INITIAL_AUTH_TOKEN__`. We hydrate
 * `_accessToken` from it synchronously on module load so the FIRST
 * /billing/auth/me call after page mount has a valid Bearer token —
 * no 401 → refresh-cookie → retry dance.
 */
let _accessToken: string | null = null;

// Hydrate from server-injected token (set by BaseLayout before this
// module evaluates). Synchronous, runs once per page load.
if (typeof window !== "undefined") {
  const initial = window.__INITIAL_AUTH_TOKEN__;
  if (initial) {
    _accessToken = initial;
  }
}

// ─── Token Accessors ─────────────────────────────────────────────────────────

/** Get the current access token from memory. */
export function getAccessToken(): string | null {
  return _accessToken;
}

/**
 * Check whether the browser currently holds the refresh cookie.
 *
 * This is a best-effort client-side check — httpOnly cookies are not
 * readable from JavaScript. We use `document.cookie` to look for any
 * non-httpOnly cookie (`sb_remember_me`) as a proxy signal: if the
 * remember-me flag is set, the refresh cookie is also set. If neither
 * is set, the user almost certainly has no active session.
 *
 * The authoritative check is server-side (Astro middleware calls
 * /auth/token/refresh-cookie). This function exists so the
 * SessionGuard and bootstrap logic can short-circuit when no
 * session is plausible.
 */
export function hasRefreshCookie(): boolean {
  if (typeof document === "undefined") return false;
  try {
    // httpOnly cookies are invisible to JS. We can only detect cookies
    // whose httpOnly flag is false (e.g. sb_remember_me). For
    // httpOnly sb_refresh_token itself we have to fall back to the
    // remember-me marker.
    const cookies = document.cookie || "";
    // Note: this returns true if EITHER sb_refresh_token (impossible
    // for httpOnly) OR sb_remember_me is set. In practice the latter
    // is what we can observe; the former is invisible.
    return /sb_refresh_token=|sb_remember_me=/.test(cookies);
  } catch {
    return false;
  }
}

/**
 * Store the access token in memory.
 *
 * The refresh token is no longer accepted as a parameter — it is set
 * by the server as an httpOnly cookie via /api/auth/login and is not
 * readable by JavaScript.
 */
export function setTokens(access: string): void {
  _accessToken = access;
}

/**
 * Clear the access token from memory. The refresh cookie is cleared
 * by POSTing to /api/auth/logout (which the caller must do); this
 * function only handles the in-memory access token.
 */
export function clearTokens(): void {
  _accessToken = null;
}

/** Check if the user has a non-expired access token in memory. */
export function isAuthenticated(): boolean {
  return !!_accessToken;
}

// ─── Request Headers ─────────────────────────────────────────────────────────

/**
 * Get the selected dealer username from localStorage.
 * Used for multi-tenant API requests.
 *
 * FIX L-7: was logging the dealer username to console on every API call.
 * That leaks tenant context in production. The debug log is now gated
 * behind `import.meta.env.DEV` so it only runs in dev builds.
 */
export function getSelectedDealerUsername(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const username = localStorage.getItem(DEALER_CONTEXT_KEY);
    if (import.meta.env.DEV) {
      console.log("%c[API] getSelectedDealerUsername", "color: #8b5cf6;", {
        key: DEALER_CONTEXT_KEY,
        username,
      });
    }
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

    // FIX A-1 (Phase A — CRIT-1): forward the access map to the backend
    // so server-side plan limits (max_products, max_dsrs, max_suppliers,
    // export_pdf, ai_insights, ...) can be enforced. The access map is
    // populated from /billing/auth/me via useAuth + useAccess.
    //
    // Lazy import to avoid a circular dependency: useAccess imports
    // getAccessToken from this file.
    try {
      // Dynamic require keeps the module load order safe.
      const accessModule = require("../composables/useAccess");
      const accessMap = accessModule?.access?.value;
      if (accessMap && typeof accessMap === "object" && Object.keys(accessMap).length > 0) {
        try {
          headers["X-Plan-Limits"] = JSON.stringify(accessMap);
        } catch {
          // If the map contains non-serializable values (shouldn't
          // happen — backend sends primitives only) skip silently.
        }
      }
    } catch {
      // useAccess not available — skip header.
    }
  }

  return headers;
}

// ─── Token Refresh ───────────────────────────────────────────────────────────

let refreshPromise: Promise<string | null> | null = null;

/**
 * Refresh the access token using the httpOnly refresh cookie.
 *
 * Calls Sattabase POST /auth/token/refresh-cookie with
 * credentials: 'include' so the browser automatically sends the
 * `sb_refresh_token` cookie. The backend reads the cookie, rotates it,
 * and returns a fresh access token (in the response body) + the
 * rotated refresh cookie (in Set-Cookie).
 *
 * Returns the new access token on success, null on failure.
 * Deduplicates concurrent calls so only one refresh request flies.
 */
export async function refreshAccessToken(): Promise<string | null> {
  // Deduplicate concurrent refresh calls.
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/token/refresh-cookie`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include", // browser sends sb_refresh_token cookie
          // Sattabase's refresh-cookie endpoint declares an empty
          // CookieRefreshInputSchema, so Django Ninja rejects requests
          // with no body. Send "{}" to satisfy the schema validator;
          // the refresh token itself is read from the cookie header.
          body: "{}",
        },
      );

      if (!response.ok) {
        clearTokens();
        return null;
      }

      const data = await response.json();
      if (data.access) {
        _accessToken = data.access;
        // The rotated refresh cookie arrives in Set-Cookie; the browser
        // stores it automatically because of credentials: 'include' on
        // this fetch. We don't need to read it from JS — we just trust
        // the cookie is set on the dealerfrontend origin (because the
        // middleware/proxy ensures the proxy response carries
        // Set-Cookie, and refresh-cookie is called directly from the
        // client to sattabase, which also sets the cookie on its own
        // origin for cross-tab SSO).
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
  // Always attempt refresh on 401 — if the refresh cookie exists,
  // /auth/token/refresh-cookie will succeed; if not, it returns 401
  // and we redirect to /login. The refresh-cookie endpoint is the
  // authoritative check for cookie presence server-side.
  if (response.status === 401 && !useDealerBackend) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = buildHeaders(
        options.headers as Record<string, string> | undefined,
        useDealerBackend,
      );
      retryHeaders["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, {
        ...fetchOptions,
        headers: retryHeaders,
        credentials: "include",
      });
    } else {
      // Refresh failed — clear in-memory token and redirect to login.
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
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
  /** Store the access token in memory. Refresh token lives in httpOnly cookie. */
  setTokens,
  /** Clear the in-memory access token. Refresh cookie is cleared via /api/auth/logout. */
  clearTokens,
  /** Get the current access token from memory. */
  getAccessToken,
  /**
   * Legacy API — returns null after the cookie migration. The refresh
   * token is no longer readable from JavaScript.
   * @deprecated Use hasRefreshCookie() or rely on server-side middleware.
   */
  getRefreshToken: (): string | null => null,
  /** Check if the user has an in-memory access token. */
  isAuthenticated,
  /** Check if the browser plausibly holds a refresh cookie. */
  hasRefreshCookie,
};
