/**
 * Sattabase SDK client — main entry point.
 *
 * Async client for the Sattabase API with auto-refresh, typed errors,
 * and token store integration.
 *
 * @example
 * ```ts
 * import { SattabaseClient, SattabaseConfig } from "@sattabase/sdk";
 *
 * const config = new SattabaseConfig({
 *   baseUrl: "https://sattabase.tld/api/v1",
 *   serviceDomain: "finance.sattabase.tld",
 *   apiKey: "sb_live_...",
 * });
 *
 * const client = new SattabaseClient(config);
 *
 * // Login
 * const tokens = await client.auth.login("user@example.com", "password");
 *
 * // Get domain-scoped user info + access map
 * const authMe = await client.auth.me(tokens.access);
 * if (authMe.hasAccess("reports")) {
 *   console.log("User has reports access");
 * }
 *
 * // Billing redirect (zero API calls)
 * const url = client.billing.manageSubscription("finance", "/settings");
 * ```
 */

import { SattabaseConfig } from "./config.js";
import { buildError, ApiServerError } from "./exceptions.js";
import { AuthModule } from "./auth.js";
import { AccessModule } from "./access.js";
import { BillingRedirect } from "./redirect.js";
import type { TokenStore, TokenStoreWithLookup } from "./token-store.js";
import type { TokenPair } from "./models.js";

/** Options for `SattabaseClient.request()`. */
export interface RequestOptions {
  /** JWT access token for user-authenticated requests. */
  token?: string | null;
  /** JSON body to send (will be serialized). */
  json?: Record<string, unknown>;
}

/**
 * Sattabase API client.
 *
 * Provides namespaced modules:
 * - `client.auth` — Authentication methods
 * - `client.access` — Feature gating helpers (cached)
 * - `client.billing` — Billing redirect URL constructors
 */
export class SattabaseClient {
  readonly config: SattabaseConfig;
  readonly tokenStore: TokenStore | null;

  /** Authentication methods */
  readonly auth: AuthModule;
  /** Feature access checking with caching */
  readonly access: AccessModule;
  /** Billing redirect URL constructors (no API calls) */
  readonly billing: BillingRedirect;

  /** Refresh lock — prevents concurrent refresh calls. */
  private refreshing = false;
  private refreshPromise: Promise<string | null> | null = null;

  constructor(config: SattabaseConfig, tokenStore?: TokenStore) {
    this.config = config;
    this.tokenStore = tokenStore ?? null;

    // Namespaces
    this.auth = new AuthModule(this);
    this.access = new AccessModule(this);
    this.billing = new BillingRedirect(config.appBaseUrl);
  }

  /**
   * Send an API request to Sattabase.
   *
   * Automatically injects `X-API-Key` and `X-Service-Domain` headers.
   * Optionally injects `Authorization: Bearer {token}`.
   * Handles auto-refresh on 401 when `autoRefresh=true`.
   *
   * @internal — public for testing; prefer `client.auth.*` methods.
   */
  async request<T>(
    method: string,
    path: string,
    opts?: RequestOptions,
    _retryCount = 0,
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "X-API-Key": this.config.apiKey,
      "X-Service-Domain": this.config.serviceDomain,
    };

    if (opts?.token) {
      headers["Authorization"] = `Bearer ${opts.token}`;
    }

    let response: Response;
    try {
      response = await fetch(`${this.config.baseUrl}${path}`, {
        method,
        headers,
        body: opts?.json ? JSON.stringify(opts.json) : undefined,
        signal: AbortSignal.timeout(this.config.timeout),
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (msg.includes("timeout") || msg.includes("Timeout")) {
        throw new ApiServerError(
          `Request to ${path} timed out after ${this.config.timeout}ms`,
          { path, timeout: this.config.timeout },
        );
      }
      throw new ApiServerError(
        `Cannot connect to Sattabase at ${this.config.baseUrl}`,
        { baseUrl: this.config.baseUrl, error: msg },
      );
    }

    // Parse response body
    let body: Record<string, unknown> | null = null;
    const ct = response.headers.get("content-type") ?? "";
    if (ct.includes("application/json")) {
      try {
        body = await response.json();
      } catch {
        // body stays null
      }
    }

    // Success
    if (response.ok) {
      return body as T;
    }

    // 401 — attempt auto-refresh
    if (
      response.status === 401 &&
      opts?.token &&
      this.config.autoRefresh &&
      _retryCount <= this.config.maxRetries
    ) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        return this.request<T>(
          method,
          path,
          { ...opts, token: newToken },
          _retryCount + 1,
        );
      }
    }

    // 429 — retry after delay
    if (
      response.status === 429 &&
      body &&
      typeof body["retry_after"] === "number" &&
      _retryCount < 1
    ) {
      const retryAfter = (body["retry_after"] as number) * 1000;
      await new Promise((r) => setTimeout(r, retryAfter));
      return this.request<T>(method, path, opts, _retryCount + 1);
    }

    // Error — map to typed exception
    const code = body ? (body["code"] as string | undefined) : undefined;
    throw buildError(response.status, body, code);
  }

  /**
   * Attempt to refresh the access token.
   *
   * Returns the new access token on success, null on failure.
   * Uses a promise-based lock to prevent concurrent refresh calls.
   */
  private async tryRefresh(): Promise<string | null> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this.doRefresh().finally(() => {
      this.refreshPromise = null;
    });

    return this.refreshPromise;
  }

  private async doRefresh(): Promise<string | null> {
    if (this.refreshing) {
      // Another call is already refreshing — wait a bit and return null
      await new Promise((r) => setTimeout(r, 500));
      return null;
    }

    this.refreshing = true;
    try {
      const refreshToken = this.findRefreshToken();
      if (!refreshToken) return null;

      try {
        const response = await fetch(
          `${this.config.baseUrl}/auth/token/refresh`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-API-Key": this.config.apiKey,
              "X-Service-Domain": this.config.serviceDomain,
            },
            body: JSON.stringify({ refresh: refreshToken }),
            signal: AbortSignal.timeout(this.config.timeout),
          },
        );

        if (!response.ok) return null;

        const data = (await response.json()) as TokenPair;
        // Store new tokens
        const userId = this.findUserIdByRefresh(refreshToken);
        if (userId && this.tokenStore) {
          this.tokenStore.setTokens(userId, data);
        }
        return data.access;
      } catch {
        return null;
      }
    } finally {
      this.refreshing = false;
    }
  }

  /**
   * Find a refresh token from the token store.
   *
   * @internal — used by auto-refresh and auth module.
   */
  findRefreshToken(): string | null {
    const store = this.tokenStore as TokenStoreWithLookup | null;
    if (!store || typeof store.getFirstTokenPair !== "function") return null;
    return store.getFirstTokenPair()?.refresh ?? null;
  }

  /**
   * Find user_id by matching refresh token in the store.
   *
   * @internal — used by auth.logout() and auto-refresh.
   */
  findUserIdByRefresh(refreshToken: string): string | null {
    const store = this.tokenStore as TokenStoreWithLookup | null;
    if (!store || typeof store.getUserIdByRefresh !== "function") return null;
    return store.getUserIdByRefresh(refreshToken);
  }
}
