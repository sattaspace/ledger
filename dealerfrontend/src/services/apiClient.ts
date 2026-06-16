/**
 * DEALERCORE v3.0 — Centralized API Client for Dealer Backend
 *
 * This is the single point of HTTP communication for dealer business data.
 * All data fetching (GET, POST, PUT, DELETE) must flow through this client.
 *
 * IMPORTANT: This client is for dealer backend business endpoints ONLY.
 * For SattaBase auth/billing API calls, use `apiClient` from `lib/api.ts`.
 *
 * Features:
 * - Configurable base URL (points to Django Ninja dealer backend)
 * - Automatic JWT token injection from SattaBase auth
 * - Request/Response interceptors
 * - Automatic JSON parsing
 * - Typed error handling with ApiError class
 * - Timeout support
 * - Automatic snake_case → camelCase key conversion for all API responses
 */

import { getAccessToken, getSelectedDealerUsername } from "../lib/api";

// ─── snake_case → camelCase Transformer ─────────────────────────────────────

/**
 * Convert a snake_case string to camelCase.
 * e.g. "full_name" → "fullName", "min_stock_alert" → "minStockAlert"
 */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase());
}

/**
 * Recursively transform all snake_case keys in an object (or array of objects)
 * to camelCase. This ensures backend Python/Django snake_case JSON responses
 * are automatically normalized to the camelCase format the frontend expects.
 *
 * Handles: plain objects, arrays, nested structures, and primitive passthrough.
 */
function transformKeysToCamelCase<T = any>(data: T): T {
  if (data === null || data === undefined) {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map((item) => transformKeysToCamelCase(item)) as T;
  }

  if (typeof data === "object" && data.constructor === Object) {
    const result: Record<string, any> = {};
    for (const key of Object.keys(data as Record<string, any>)) {
      const camelKey = snakeToCamel(key);
      result[camelKey] = transformKeysToCamelCase(
        (data as Record<string, any>)[key],
      );
    }
    return result as T;
  }

  // Primitives (string, number, boolean) and Date objects pass through unchanged
  return data;
}

/**
 * Convert a camelCase string to snake_case.
 * e.g. "fullName" → "full_name", "minStockAlert" → "min_stock_alert"
 */
function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
}

/**
 * Recursively transform all camelCase keys in an object (or array of objects)
 * to snake_case. This ensures frontend JavaScript/TypeScript camelCase payloads
 * are automatically converted to the snake_case format the Django backend expects.
 */
function transformKeysToSnakeCase<T = any>(data: T): T {
  if (data === null || data === undefined) {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map((item) => transformKeysToSnakeCase(item)) as T;
  }

  if (typeof data === "object" && data.constructor === Object) {
    const result: Record<string, any> = {};
    for (const key of Object.keys(data as Record<string, any>)) {
      const snakeKey = camelToSnake(key);
      result[snakeKey] = transformKeysToSnakeCase(
        (data as Record<string, any>)[key],
      );
    }
    return result as T;
  }

  return data;
}

// ─── Types ───────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  statusText: string;
  data: any;

  constructor(status: number, statusText: string, data?: any) {
    const message =
      data?.error ||
      data?.message ||
      data?.detail ||
      statusText ||
      "API Request Failed";
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

export interface ApiResponse<T = any> {
  ok: boolean;
  status: number;
  data: T;
}

export interface RequestConfig extends RequestInit {
  /** Request timeout in milliseconds (default: 15000) */
  timeout?: number;
  /** Skip global error handling for this request */
  skipErrorHandler?: boolean;
  /** Custom headers to merge with defaults */
  headers?: Record<string, string>;
}

// ─── Interceptor Types ───────────────────────────────────────────────────────

type RequestInterceptor = (
  url: string,
  config: RequestConfig,
) => { url: string; config: RequestConfig };
type ResponseInterceptor = (response: Response, url: string) => Response;
type ErrorInterceptor = (error: ApiError, url: string) => void;

// ─── Configuration ───────────────────────────────────────────────────────────

export interface ApiClientConfig {
  /** Base URL for all API requests. Defaults to '' (same-origin). */
  baseURL: string;
  /** Default timeout in ms */
  timeout: number;
  /** Default headers merged into every request */
  defaultHeaders: Record<string, string>;
}

// ─── Client ──────────────────────────────────────────────────────────────────

class ApiClient {
  private config: ApiClientConfig;
  private requestInterceptors: RequestInterceptor[] = [];
  private responseInterceptors: ResponseInterceptor[] = [];
  private errorInterceptors: ErrorInterceptor[] = [];

  constructor(config: Partial<ApiClientConfig> = {}) {
    this.config = {
      baseURL: config.baseURL || "",
      timeout: config.timeout || 15000,
      defaultHeaders: config.defaultHeaders || {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    };
  }

  // ── Interceptor Management ────────────────────────────────────────────

  addRequestInterceptor(fn: RequestInterceptor) {
    this.requestInterceptors.push(fn);
    return () => {
      this.requestInterceptors = this.requestInterceptors.filter(
        (i) => i !== fn,
      );
    };
  }

  addResponseInterceptor(fn: ResponseInterceptor) {
    this.responseInterceptors.push(fn);
    return () => {
      this.responseInterceptors = this.responseInterceptors.filter(
        (i) => i !== fn,
      );
    };
  }

  addErrorInterceptor(fn: ErrorInterceptor) {
    this.errorInterceptors.push(fn);
    return () => {
      this.errorInterceptors = this.errorInterceptors.filter((i) => i !== fn);
    };
  }

  // ── Config Update ──────────────────────────────────────────────────────

  setBaseURL(url: string) {
    this.config.baseURL = url;
  }

  getConfig(): ApiClientConfig {
    return { ...this.config };
  }

  // ── Core Request ───────────────────────────────────────────────────────

  private async request<T = any>(
    method: string,
    endpoint: string,
    body?: any,
    customConfig?: RequestConfig,
  ): Promise<ApiResponse<T>> {
    let url = `${this.config.baseURL}${endpoint}`;
    let config: RequestConfig = {
      method,
      headers: {
        ...this.config.defaultHeaders,
        ...(customConfig?.headers || {}),
      },
      ...customConfig,
    };

    // FIX B-12 + FIX DSR-013: Token injection now handles three scenarios:
    //
    // 1. Dealer session (SattaBase JWT): Inject dealer JWT for business
    //    endpoints. Skip for /dsr/ paths (those use the DSR client).
    // 2. DSR Portal mode (DSR-scoped JWT): When a DSR has entered the
    //    dealer portal, we inject the DSR JWT for ALL endpoints (not just
    //    /dsr/ paths). The backend's PermissionMiddleware handles DSR JWTs
    //    for business endpoints too. We detect portal mode by checking if
    //    there's a DSR access token but NO dealer (SattaBase) access token.
    // 3. No auth (public endpoints): Neither token is injected.
    const isDsrPath = endpoint.startsWith("/dsr/");
    const dealerToken = getAccessToken();
    const dsrToken = localStorage.getItem("dsr_access_token");

    let authToken: string | null = null;
    if (!config.headers?.Authorization) {
      if (isDsrPath) {
        // DSR paths: use DSR token if available
        authToken = dsrToken;
      } else if (dealerToken) {
        // Business paths with dealer session: use dealer token
        authToken = dealerToken;
      } else if (dsrToken) {
        // FIX DSR-013: Business paths with DSR portal mode (no dealer
        // token but DSR token exists): use DSR token. This allows DSRs
        // to access the full dealer app UI with their scoped JWT.
        authToken = dsrToken;
      }
    }

    if (authToken) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${authToken}`,
      };
    }

    // X-Dealer-Username header for multi-tenancy.
    // When a DSR is in portal mode, we get the dealer username from the
    // DSR's selected dealer (localStorage). Otherwise, from the dealer
    // session. Skip for /dsr/ paths (the DSR's assignment handles context).
    if (!isDsrPath) {
      let dealerUsername = getSelectedDealerUsername();
      // FIX DSR-013: If no dealer username from SattaBase session, try
      // the DSR's selected dealer (for DSR portal mode).
      if (!dealerUsername && dsrToken) {
        const dsrDealer = localStorage.getItem("dsr_selected_dealer");
        if (dsrDealer) {
          try {
            const parsed = JSON.parse(dsrDealer);
            dealerUsername = parsed.username;
          } catch {
            /* ignore parse errors */
          }
        }
      }
      if (dealerUsername) {
        config.headers = {
          ...config.headers,
          "X-Dealer-Username": dealerUsername,
        };
      }
    }

    // Add body for POST/PUT/PATCH
    // Transform camelCase keys to snake_case so Django backend can parse them
    if (body !== undefined && method !== "GET") {
      const snakeBody =
        typeof body === "string" ? body : transformKeysToSnakeCase(body);
      config.body =
        typeof snakeBody === "string" ? snakeBody : JSON.stringify(snakeBody);
    }

    // Run request interceptors
    for (const interceptor of this.requestInterceptors) {
      const result = interceptor(url, config);
      url = result.url;
      config = result.config;
    }

    // Timeout wrapper
    const timeout = config.timeout ?? this.config.timeout;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    config.signal = controller.signal;

    try {
      // DEBUG: Log all API requests
      console.log(
        `%c[API] ${method} ${endpoint}`,
        "color: #6366f1; font-weight: bold",
        {
          url,
          dealerUsername: config.headers?.["X-Dealer-Username"] || "none",
          hasToken: !!authToken,
          body: body ? "(has body)" : "none",
        },
      );

      const response = await fetch(url, config as RequestInit);

      // Run response interceptors
      for (const interceptor of this.responseInterceptors) {
        interceptor(response, url);
      }

      // Parse JSON body
      let data: any = null;
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        data = await response.json();
      } else {
        const text = await response.text();
        try {
          data = JSON.parse(text);
        } catch {
          data = text;
        }
      }

      if (!response.ok) {
        // DEBUG: Log error responses
        console.error(
          `%c[API ERROR] ${method} ${endpoint}`,
          "color: #ef4444; font-weight: bold",
          {
            status: response.status,
            statusText: response.statusText,
            data,
          },
        );

        const apiError = new ApiError(
          response.status,
          response.statusText,
          data,
        );

        // Run error interceptors
        if (!customConfig?.skipErrorHandler) {
          for (const interceptor of this.errorInterceptors) {
            interceptor(apiError, url);
          }
        }

        throw apiError;
      }

      // Transform all snake_case keys to camelCase so the frontend
      // can consume data using JavaScript/TypeScript naming conventions
      const transformedData = transformKeysToCamelCase<T>(data);

      // DEBUG: Log successful responses
      console.log(
        `%c[API SUCCESS] ${method} ${endpoint}`,
        "color: #10b981; font-weight: bold",
        {
          status: response.status,
          dataType: Array.isArray(transformedData)
            ? `Array(${transformedData.length})`
            : typeof transformedData,
          preview: Array.isArray(transformedData)
            ? transformedData.slice(0, 2)
            : transformedData,
        },
      );

      return {
        ok: true,
        status: response.status,
        data: transformedData,
      };
    } catch (err: any) {
      if (err.name === "AbortError") {
        const apiError = new ApiError(408, "Request Timeout", {
          error: `Request timed out after ${timeout}ms`,
        });

        if (!customConfig?.skipErrorHandler) {
          for (const interceptor of this.errorInterceptors) {
            interceptor(apiError, url);
          }
        }

        throw apiError;
      }

      // Re-throw ApiError instances (already processed above)
      if (err instanceof ApiError) {
        throw err;
      }

      // Network / unknown errors
      const apiError = new ApiError(0, "Network Error", {
        error: err.message || "Failed to connect to server",
      });

      if (!customConfig?.skipErrorHandler) {
        for (const interceptor of this.errorInterceptors) {
          interceptor(apiError, url);
        }
      }

      throw apiError;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // ── HTTP Method Shortcuts ──────────────────────────────────────────────

  async get<T = any>(
    endpoint: string,
    config?: RequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.request<T>("GET", endpoint, undefined, config);
  }

  async post<T = any>(
    endpoint: string,
    body?: any,
    config?: RequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.request<T>("POST", endpoint, body, config);
  }

  async put<T = any>(
    endpoint: string,
    body?: any,
    config?: RequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.request<T>("PUT", endpoint, body, config);
  }

  async patch<T = any>(
    endpoint: string,
    body?: any,
    config?: RequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.request<T>("PATCH", endpoint, body, config);
  }

  async delete<T = any>(
    endpoint: string,
    config?: RequestConfig,
  ): Promise<ApiResponse<T>> {
    return this.request<T>("DELETE", endpoint, undefined, config);
  }
}

// ─── Singleton Export ─────────────────────────────────────────────────────────

/**
 * Determine the API configuration from environment variables.
 *
 * PUBLIC_DEALER_API_URL — Your Django Ninja dealer backend URL.
 *                          e.g. http://localhost:8088/api
 */
function resolveConfig(): ApiClientConfig {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const env =
    typeof import.meta !== "undefined" && (import.meta as any).env
      ? (import.meta as any).env
      : {};

  const baseURL =
    env.PUBLIC_DEALER_API_URL ||
    env.VITE_API_BASE_URL ||
    "http://localhost:8088/api";

  return {
    baseURL,
    timeout: 15000,
    defaultHeaders: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
  };
}

export const apiClient = new ApiClient(resolveConfig());

export default apiClient;
