/**
 * @sattabase/sdk — TypeScript SDK for Sattabase.
 *
 * Central auth, subscription, and access control for multi-tenant service domains.
 * Supports both server mode (with API key) and browser mode (JWT-only).
 *
 * @example Server mode (Node.js backend)
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
 * const authMe = await client.auth.me(tokens.access);
 * ```
 *
 * @example Browser mode (frontend SPA)
 * ```ts
 * import { SattabaseClient, SattabaseConfig, LocalStorageTokenStore } from "@sattabase/sdk";
 *
 * const config = new SattabaseConfig({
 *   baseUrl: "https://sattabase.tld/api/v1",
 *   serviceDomain: "finance.sattabase.tld",
 *   // apiKey omitted — no secret in browser code!
 *   debug: true,
 * });
 *
 * const store = new LocalStorageTokenStore();
 * const client = new SattabaseClient(config, store);
 * const tokens = await client.auth.login("user@example.com", "password");
 * ```
 */

export { SattabaseClient } from "./client.js";
export { SattabaseConfig } from "./config.js";
export {
  InMemoryTokenStore,
  LocalStorageTokenStore,
  type TokenStore,
  type TokenStoreWithLookup,
} from "./token-store.js";

export {
  AuthMeResponse,
  type TokenPair,
  type User,
  type SubscriptionInfo,
  type MessageResponse,
} from "./models.js";

export {
  SattabaseError,
  AuthenticationError,
  AccountInactiveError,
  AccountDeletedError,
  ForbiddenError,
  AccountNotActiveError,
  NotFoundError,
  ConflictError,
  ValidationError,
  BadRequestError,
  RateLimitError,
  ApiServerError,
  buildError,
} from "./exceptions.js";

export { BillingRedirect, type BillingUpdateStatus } from "./redirect.js";

export const VERSION = "0.1.0";
