/**
 * Access module — feature gating helpers with optional caching.
 *
 * Wraps `AuthModule.me` with caching to avoid repeated API calls
 * within a configurable TTL window.
 */

import type { SattabaseClient } from "./client.js";
import { AuthMeResponse } from "./models.js";

/**
 * Feature access checking with optional client-side caching.
 *
 * @example
 * ```ts
 * // Check if user has access to a feature
 * const canExport = await client.access.hasAccess("export_pdf", tokens.access);
 *
 * // Get numeric limit
 * const maxAccounts = await client.access.getAccess("max_bank_accounts", 1, tokens.access);
 *
 * // Force re-fetch after billing update
 * client.access.invalidateCache();
 * ```
 */
export class AccessModule {
  private client: SattabaseClient;
  private cacheTtl: number;
  private cached: AuthMeResponse | null = null;
  private cachedAt = 0;

  constructor(client: SattabaseClient, cacheTtl = 60_000) {
    this.client = client;
    this.cacheTtl = cacheTtl;
  }

  /** Check if cached data is still within TTL. */
  private isCacheValid(): boolean {
    if (!this.cached) return false;
    return Date.now() - this.cachedAt < this.cacheTtl;
  }

  /** Clear cached AuthMeResponse, forcing next call to re-fetch. */
  invalidateCache(): void {
    this.cached = null;
    this.cachedAt = 0;
  }

  /** Get AuthMeResponse, using cache if valid. */
  private async getAuthMe(token?: string | null): Promise<AuthMeResponse> {
    if (this.isCacheValid() && this.cached) {
      return this.cached;
    }

    const authMe = await this.client.auth.me(token);
    this.cached = authMe;
    this.cachedAt = Date.now();
    return authMe;
  }

  /**
   * Check if the user has access to a feature.
   *
   * @param key - The access key (e.g. "reports", "max_bank_accounts")
   * @param token - Optional JWT token. Falls back to token store if not provided.
   */
  async hasAccess(key: string, token?: string | null): Promise<boolean> {
    const authMe = await this.getAuthMe(token);
    return authMe.hasAccess(key);
  }

  /**
   * Get the raw value for an access key.
   *
   * @param key - The access key
   * @param defaultValue - Default value if key not found
   * @param token - Optional JWT token
   */
  async getAccess(key: string, defaultValue?: unknown, token?: string | null): Promise<unknown> {
    const authMe = await this.getAuthMe(token);
    return authMe.getAccess(key, defaultValue);
  }

  /**
   * Get all available access keys for the user.
   *
   * @param token - Optional JWT token
   */
  async keys(token?: string | null): Promise<string[]> {
    const authMe = await this.getAuthMe(token);
    return authMe.accessKeys;
  }
}
