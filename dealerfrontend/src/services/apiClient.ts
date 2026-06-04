/**
 * DEALERCORE v3.0 — Centralized API Client
 *
 * This is the single point of HTTP communication for the entire frontend.
 * All data fetching (GET, POST, PUT, DELETE) must flow through this client.
 *
 * Features:
 * - Configurable base URL (points to Django Ninja backend)
 * - Request/Response interceptors (auth headers, logging, error normalization)
 * - Automatic JSON parsing
 * - Typed error handling with ApiError class
 * - Timeout support
 */

// ─── Types ───────────────────────────────────────────────────────────────────

export class ApiError extends Error {
  status: number;
  statusText: string;
  data: any;

  constructor(status: number, statusText: string, data?: any) {
    const message =
      data?.error || data?.message || statusText || "API Request Failed";
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

    // Add body for POST/PUT/PATCH
    if (body !== undefined && method !== "GET") {
      config.body = typeof body === "string" ? body : JSON.stringify(body);
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

      return {
        ok: true,
        status: response.status,
        data: data as T,
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
 * VITE_API_BASE_URL  — Your Django Ninja backend URL.
 *                       e.g. http://localhost:8000/api
 */
function resolveConfig(): ApiClientConfig {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const env =
    typeof import.meta !== "undefined" && (import.meta as any).env
      ? (import.meta as any).env
      : {};

  const baseURL = env.VITE_API_BASE_URL || "http://localhost:8000/api";

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
