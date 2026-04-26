/**
 * API Client — centralized fetch wrapper for Django Ninja backend.
 *
 * All API calls go through here so auth headers, error handling,
 * and token refresh are handled in one place.
 *
 * Usage in Vue components (client-side only):
 *   import { apiClient } from "@/lib/api";
 *   const data = await apiClient.get("/auth/me");
 *   const result = await apiClient.post("/auth/login", { email, password });
 */

const API_BASE_URL =
  typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_BASE_URL
    ? (import.meta as any).env.VITE_API_BASE_URL
    : "http://localhost:8000/api/v1";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  message?: string;
  errors?: Record<string, string[]>;
}

export interface ApiError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getAccessToken(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function setTokens(access: string, refresh: string): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens(): void {
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

function buildHeaders(custom?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...custom,
  };

  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

// ─── Token refresh ──────────────────────────────────────────────────────────

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
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
        localStorage.setItem("access_token", data.access);
        if (data.refresh) {
          localStorage.setItem("refresh_token", data.refresh);
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

// ─── Main client ────────────────────────────────────────────────────────────

export const apiClient = {
  /**
   * GET request
   */
  async get<T = unknown>(path: string, options?: RequestInit): Promise<T> {
    return request<T>(path, { method: "GET", ...options });
  },

  /**
   * POST request
   */
  async post<T = unknown>(path: string, body?: unknown, options?: RequestInit): Promise<T> {
    return request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });
  },

  /**
   * PUT request
   */
  async put<T = unknown>(path: string, body?: unknown, options?: RequestInit): Promise<T> {
    return request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });
  },

  /**
   * PATCH request
   */
  async patch<T = unknown>(path: string, body?: unknown, options?: RequestInit): Promise<T> {
    return request<T>(path, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    });
  },

  /**
   * DELETE request
   */
  async delete<T = unknown>(path: string, options?: RequestInit): Promise<T> {
    return request<T>(path, { method: "DELETE", ...options });
  },
};

// ─── Core request handler ───────────────────────────────────────────────────

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers = buildHeaders(
    options.headers as Record<string, string> | undefined,
  );

  let response = await fetch(url, { ...options, headers });

  // ── 401 → try token refresh ──
  if (response.status === 401 && getRefreshToken()) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      const retryHeaders = buildHeaders(
        options.headers as Record<string, string> | undefined,
      );
      // The refreshAccessToken already stored the new token,
      // but getAccessToken() will read it
      retryHeaders["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...options, headers: retryHeaders });
    } else {
      // Refresh failed — redirect to login
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

// ─── Error factory ──────────────────────────────────────────────────────────

async function createApiErrorFromResponse(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`;

  try {
    const body = await response.json();
    if (typeof body === "object" && body !== null) {
      // Django Ninja typically returns { detail: "..." } or { message: "..." } or { non_field_errors: [...] }
      if (body.detail) message = body.detail;
      else if (body.message) message = body.message;
      else if (body.non_field_errors?.[0]) message = body.non_field_errors[0];

      // Handle validation error format: { detail: "...", errors: [{ field, message }], code: "validation_error" }
      if (body.code === "validation_error" && Array.isArray(body.errors) && body.errors.length > 0) {
        const firstError = body.errors[0];
        if (firstError.message) {
          // Build user-friendly message from field name
          const fieldLabel = (firstError.field || "")
            .replace(/payload\.\s*/g, "")  // Remove "payload." prefix
            .replace(/body\.\s*/g, "")    // Remove "body." prefix
            .replace(/_/g, " ")            // snake_case → space
            .replace(/\b\w/g, (c: string) => c.toUpperCase()); // Capitalize
          message = fieldLabel
            ? `${fieldLabel}: ${firstError.message}`
            : firstError.message;
        }
      }

      // Field-level errors (dict format)
      const fieldErrors: Record<string, string[]> = {};
      for (const [key, value] of Object.entries(body)) {
        if (key !== "detail" && key !== "message" && key !== "non_field_errors" && key !== "code" && key !== "errors") {
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

// ─── Auth helpers ───────────────────────────────────────────────────────────

export const authHelpers = {
  setTokens,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  isAuthenticated: (): boolean => !!getAccessToken(),
};
