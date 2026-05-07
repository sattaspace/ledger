/**
 * @sattabase/sdk — TypeScript SDK for Sattabase.
 *
 * Central auth, subscription, and access control for multi-tenant service domains.
 *
 * Usage:
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
 * const tokens = await client.auth.login("user@example.com", "password");
 * const authMe = await client.auth.me(tokens.access);
 * if (authMe.hasAccess("reports")) {
 *   console.log("User has reports access");
 * }
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
