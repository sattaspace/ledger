/**
 * Configuration for the Sattabase SDK.
 *
 * Validates configuration at construction time.
 * Config is immutable after creation (readonly properties).
 */

/** Sattabase SDK configuration options. */
export interface SattabaseConfigOptions {
  /** Sattabase API base URL (e.g. "https://sattabase.tld/api/v1"). */
  baseUrl: string;
  /** Identifies this service domain (e.g. "finance.sattabase.tld"). */
  serviceDomain: string;
  /**
   * Service credential raw key (format: `sb_live_{token_urlsafe(32)}`).
   * Stored in memory only — never persisted to disk.
   */
  apiKey: string;
  /** HTTP request timeout in milliseconds. @default 10_000 */
  timeout?: number;
  /** Enable automatic token refresh on 401. @default true */
  autoRefresh?: boolean;
  /** Max retries after token refresh (total attempts = 1 + maxRetries). @default 1 */
  maxRetries?: number;
  /**
   * When true, allows http:// baseUrl and relaxes validation.
   * @default false
   */
  debug?: boolean;
}

/**
 * Sattabase SDK configuration.
 *
 * Validates configuration at construction time.
 * All properties are readonly after creation.
 *
 * @example
 * ```ts
 * const config = new SattabaseConfig({
 *   baseUrl: "https://sattabase.tld/api/v1",
 *   serviceDomain: "finance.sattabase.tld",
 *   apiKey: "sb_live_abcd1234efgh5678ijkl9012mnop3456",
 *   timeout: 15_000,
 * });
 * ```
 */
export class SattabaseConfig {
  readonly baseUrl: string;
  readonly serviceDomain: string;
  readonly apiKey: string;
  readonly timeout: number;
  readonly autoRefresh: boolean;
  readonly maxRetries: number;
  readonly debug: boolean;

  constructor(opts: SattabaseConfigOptions) {
    if (!opts.apiKey.startsWith("sb_live_")) {
      throw new Error(
        `Invalid API key format: must start with 'sb_live_', got '${opts.apiKey.slice(0, 12)}...'`,
      );
    }

    if (!opts.debug && !opts.baseUrl.startsWith("https://")) {
      throw new Error(
        `baseUrl must use HTTPS in production (set debug=true to override). Got: ${opts.baseUrl}`,
      );
    }

    this.baseUrl = opts.baseUrl;
    this.serviceDomain = opts.serviceDomain;
    this.apiKey = opts.apiKey;
    this.timeout = opts.timeout ?? 10_000;
    this.autoRefresh = opts.autoRefresh ?? true;
    this.maxRetries = opts.maxRetries ?? 1;
    this.debug = opts.debug ?? false;
  }

  /**
   * Derive the Sattabase app base URL from the API base URL.
   *
   * Strips `/api/v1` (and trailing slash) to get the frontend root.
   *
   * @example
   * ```ts
   * config.appBaseUrl; // "https://sattabase.tld" (used by billing redirects)
   * ```
   */
  get appBaseUrl(): string {
    let url = this.baseUrl.replace(/\/+$/, "");
    if (url.endsWith("/api/v1")) {
      url = url.slice(0, -"/api/v1".length);
    }
    return url;
  }
}
