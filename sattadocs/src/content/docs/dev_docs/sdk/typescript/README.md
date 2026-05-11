---
title: TypeScript SDK
description:  the central authentication, subscription, and access control platform.
---

# @sattabase/sdk

TypeScript SDK for **Sattabase** — the central authentication, subscription, and access control platform.

> **Scope:** Auth + Permissions only. Billing, payments, and subscription management are handled entirely by the Sattabase frontend via Stripe. Sister domains never touch payment flows directly — the SDK provides redirect URLs for billing instead.

## Installation

```bash
npm install @sattabase/sdk
```

**Requirements:** Node.js 18+. Zero runtime dependencies — uses the native `fetch` API.

## Quick Start

### Server Mode (Node.js backend)

```ts
import { SattabaseClient, SattabaseConfig } from "@sattabase/sdk";

const config = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "finance.sattabase.tld",
  apiKey: "sb_live_...",  // Required for server-to-server auth
});

const client = new SattabaseClient(config);

// Login
const tokens = await client.auth.login("user@example.com", "password");

// Get domain-scoped user info + access map
const authMe = await client.auth.me(tokens.access);
console.log(`User: ${authMe.user.display_name}`);
console.log(`Plan: ${authMe.subscription?.plan_name ?? "Free"}`);

// Feature gating
if (authMe.hasAccess("reports")) {
  console.log("User has reports access");
}

// Get numeric limits
const maxAccounts = authMe.getAccess("max_bank_accounts", 1);
console.log(`Max bank accounts: ${maxAccounts}`);
```

### Browser Mode (frontend SPA)

```ts
import {
  SattabaseClient,
  SattabaseConfig,
  LocalStorageTokenStore,
} from "@sattabase/sdk";

const config = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "finance.sattabase.tld",
  // apiKey is OMITTED — no secret in browser code!
  debug: true, // for localhost development
});

const store = new LocalStorageTokenStore("finance:");
const client = new SattabaseClient(config, store);

// Login
const tokens = await client.auth.login("user@example.com", "password");

// Get domain-scoped user info + access map (JWT-only, no API key)
const authMe = await client.auth.me(tokens.access);
console.log(`User: ${authMe.user.display_name}`);

// Billing redirect (zero API calls)
const url = client.billing.manageSubscription(
  "finance",
  "https://finance.sattabase.tld/settings",
);
```

> **Security warning:** Never put an `sb_live_...` API key in frontend/browser code. Anyone can read it from DevTools. In browser mode, the SDK sends only `Authorization: Bearer {jwt}` and `X-Service-Domain` headers. The Sattabase backend accepts JWT-only requests on endpoints with the `IsAuthenticatedOrService` permission.

## Configuration

`SattabaseConfig` validates configuration at construction time. All properties are readonly after creation.

| Field | Type | Default | Description |
|---|---|---|---|
| `baseUrl` | `string` | *required* | Sattabase API base URL (e.g. `https://sattabase.tld/api/v1`) |
| `serviceDomain` | `string` | *required* | Identifies this service domain (e.g. `finance.sattabase.tld`) |
| `apiKey` | `string` | *optional* | Service credential raw key (format: `sb_live_{token_urlsafe(32)}`). Omit for browser mode. |
| `timeout` | `number` | `10_000` | HTTP request timeout in milliseconds |
| `autoRefresh` | `boolean` | `true` | Automatically refresh tokens on 401 responses |
| `maxRetries` | `number` | `1` | Max retries after token refresh (total attempts = 1 + maxRetries) |
| `debug` | `boolean` | `false` | Allow `http://` base URLs and relax validation |

**Validation rules:**
- If provided, API key **must** start with `sb_live_`
- Base URL **must** use HTTPS unless `debug=true`
- When `apiKey` is omitted, the SDK operates in **browser mode** — no `X-API-Key` header is sent

```ts
// Server mode — include API key for service-to-service auth
const config = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "finance.sattabase.tld",
  apiKey: "sb_live_abcd1234efgh5678ijkl9012mnop3456",
  timeout: 15_000,
  debug: false,
});

// Browser mode — omit API key for JWT-only auth
const browserConfig = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "finance.sattabase.tld",
  // apiKey is OMITTED — no secret in browser code
  timeout: 15_000,
  debug: true, // for localhost development
});

console.log(config.appBaseUrl); // "https://sattabase.tld"
console.log(config.browserMode); // false
console.log(browserConfig.browserMode); // true
```

## Modules

The `SattabaseClient` exposes three namespaced modules:

```ts
client.auth      // Authentication methods
client.access    // Feature gating helpers (cached)
client.billing   // Billing redirect URL constructors (no API calls)
```

### Auth (`client.auth`)

In **server mode** (apiKey provided), auth methods send `X-API-Key` + `X-Service-Domain` + `Authorization: Bearer` headers. In **browser mode** (apiKey omitted), only `X-Service-Domain` + `Authorization: Bearer` headers are sent — the backend accepts JWT-only requests via the `IsAuthenticatedOrService` permission. All methods map 1:1 to the backend `AuthController` endpoints.

#### `login(email, password)`

Authenticate a user and obtain JWT tokens.

```ts
const tokens = await client.auth.login("user@example.com", "password");
console.log(tokens.access);   // Short-lived access token
console.log(tokens.refresh);  // Long-lived refresh token
```

#### `register(email, password, firstName, lastName, options?)`

Register a new user account.

```ts
const result = await client.auth.register(
  "newuser@example.com",
  "SecurePass1!",
  "Rahim",
  "Uddin",
  { timezone: "Asia/Dhaka", currency: "BDT", language: "en" },
);
console.log(result.success); // true
```

#### `me(token?)`

Get domain-scoped user info, subscription, and access map. This is the **core method** for service domain integration.

```ts
const authMe = await client.auth.me(tokens.access);

// User profile
console.log(authMe.user.email);           // "user@example.com"
console.log(authMe.user.display_name);    // "Rahim"

// Account status
console.log(authMe.account_status);       // "active" | "inactive" | "deleted"

// Subscription info
if (authMe.subscription) {
  console.log(authMe.subscription.plan_name);       // "Standard"
  console.log(authMe.subscription.status);          // "active"
  console.log(authMe.subscription.is_active);       // true
}

// Feature access
console.log(authMe.hasAccess("reports"));            // true
console.log(authMe.getAccess("max_bank_accounts"));  // 5
console.log(authMe.accessKeys);                      // ["dashboard", "reports", ...]
```

#### `refresh(refreshToken)`

Refresh an expired access token.

```ts
const newTokens = await client.auth.refresh(tokens.refresh);
```

#### `verify(token)`

Verify an access token is still valid.

```ts
const result = await client.auth.verify(tokens.access);
console.log(result.success); // true
```

#### `blacklist(refreshToken)`

Invalidate a refresh token (used for logout).

```ts
await client.auth.blacklist(tokens.refresh);
```

#### `logout(token, refreshToken)`

Convenience method — blacklists the refresh token and clears the token store.

```ts
await client.auth.logout(tokens.access, tokens.refresh);
```

#### Password Reset

```ts
await client.auth.requestPasswordReset("user@example.com");

await client.auth.confirmPasswordReset(
  "user@example.com",
  "123456",
  "NewSecurePass1!",
  "NewSecurePass1!",
);
```

#### Email Verification

```ts
await client.auth.requestEmailVerification("user@example.com");

await client.auth.confirmEmailVerification("user@example.com", "123456");
```

### Access (`client.access`)

Feature access checking with client-side caching. Wraps `auth.me()` with a configurable TTL to avoid repeated API calls.

```ts
// Check if user has access to a feature
const canExport = await client.access.hasAccess("export_pdf", tokens.access);

// Get raw value (numeric limits, etc.)
const maxAccounts = await client.access.getAccess("max_bank_accounts", 1, tokens.access);

// Get all available access keys
const keys = await client.access.keys(tokens.access);

// Force re-fetch (e.g., after returning from billing redirect)
client.access.invalidateCache();
```

**Cache behavior:**
- Default TTL: 60 seconds (configurable via constructor)
- All `access.*` methods share the same cache
- Call `invalidateCache()` when you know access has changed

### Billing Redirects (`client.billing`)

Zero API calls — these methods only construct URL strings for redirecting users to Sattabase's billing pages.

```ts
// Redirect to subscription management
const url = client.billing.manageSubscription(
  "finance",
  "https://finance.sattabase.tld/settings",
);
// → "https://sattabase.tld/dashboard/billing/plans/finance?return_url=..."

// Redirect to upgrade page
const url = client.billing.upgrade("finance", "https://finance.sattabase.tld/billing");

// Redirect to Stripe Customer Portal
const url = client.billing.portal("https://finance.sattabase.tld/dashboard");
```

#### Detecting Billing Updates

After a user returns from a billing redirect, check for the `billing_updated` query parameter:

```ts
import { BillingRedirect } from "@sattabase/sdk";

const status = BillingRedirect.detectBillingUpdate(window.location.href);
if (status.updated && status.success === 1) {
  // Billing was updated — refresh access
  client.access.invalidateCache();
  const authMe = await client.auth.me(tokens.access);
} else if (status.updated && status.success === 0) {
  // User cancelled or payment failed
}
```

## Token Store

The SDK uses a `TokenStore` interface for persisting tokens across requests (required for auto-refresh).

### Interface

```ts
import type { TokenStore } from "@sattabase/sdk";
import type { TokenPair } from "@sattabase/sdk";

const store: TokenStore = {
  getTokens(userId: string): TokenPair | null | Promise<TokenPair | null> { ... },
  setTokens(userId: string, tokens: TokenPair): void | Promise<void> { ... },
  deleteTokens(userId: string): void | Promise<void> { ... },
};
```

### InMemoryTokenStore (development)

```ts
import { InMemoryTokenStore } from "@sattabase/sdk";

const store = new InMemoryTokenStore();
const client = new SattabaseClient(config, store);
```

Not suitable for production — tokens are lost on page refresh. Implements `TokenStoreWithLookup` for full auto-refresh support.

### LocalStorageTokenStore (browser SPAs)

```ts
import { LocalStorageTokenStore } from "@sattabase/sdk";

const store = new LocalStorageTokenStore("sb:");
const client = new SattabaseClient(config, store);
```

Persists tokens across page refreshes. Suitable for browser-based SPAs. Implements `TokenStoreWithLookup` for full auto-refresh support.

## Models

All types use the exact same field names as the actual backend API response (snake_case).

### `TokenPair`

```ts
interface TokenPair {
  access: string;   // Short-lived JWT access token
  refresh: string;  // Long-lived JWT refresh token
}
```

### `User`

```ts
interface User {
  id: number;
  slug: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  avatar: string | null;
  timezone: string | null;
  currency: string | null;
  language: string | null;
  is_email_verified: boolean;
  is_active: boolean;
  role: string;
  created_at: string | null;
  full_name: string;
  display_name: string;
}
```

### `SubscriptionInfo`

```ts
interface SubscriptionInfo {
  plan_name: string;
  plan_slug: string;
  status: string;
  current_period_end: string | null;
  trial_end: string | null;
  is_active: boolean;
}
```

### `AuthMeResponse`

The core response from `auth/me`. Provides helper methods for feature gating.

```ts
class AuthMeResponse {
  user: User;
  account_status: string;                    // "active" | "inactive" | "deleted"
  subscription: SubscriptionInfo | null;
  access: Record<string, boolean | number | string>;

  hasAccess(key: string): boolean;           // Coerces strings/ints to bool
  getAccess(key: string, default?): unknown; // Raw value lookup
  readonly accessKeys: string[];              // All available keys
}
```

### `MessageResponse`

```ts
interface MessageResponse {
  message: string;
  success: boolean;
}
```

### `BillingUpdateStatus`

Result of detecting a `billing_updated` query parameter after a billing redirect.

```ts
interface BillingUpdateStatus {
  updated: boolean;           // Whether the parameter was present
  success: 1 | 0 | null;     // 1 = billing action succeeded, 0 = cancelled/failed
}
```

## Exceptions

All SDK errors inherit from `SattabaseError`.

```
SattabaseError                     // Base (all errors)
  AuthenticationError               // 401 — Invalid/expired token or API key
    AccountInactiveError            // 401 — User account deactivated
    AccountDeletedError             // 401 — User account soft-deleted
  ForbiddenError                    // 403 — Insufficient permissions
    AccountNotActiveError           // 403 — Email not verified
  NotFoundError                     // 404 — Resource not found
  ConflictError                     // 409 — State conflict
  ValidationError                   // 422 — Invalid request body
  BadRequestError                   // 400 — Malformed request
  RateLimitError                    // 429 — Too many requests
    .retryAfter                     // Seconds to wait
  ApiServerError                    // 5xx — Server error or network failure
```

```ts
import {
  SattabaseError,
  AuthenticationError,
  AccountInactiveError,
  AccountDeletedError,
  RateLimitError,
} from "@sattabase/sdk";

try {
  const authMe = await client.auth.me(token);
} catch (err) {
  if (err instanceof AccountDeletedError) {
    // User deleted their account — force logout
  } else if (err instanceof AccountInactiveError) {
    // Account deactivated — force logout
  } else if (err instanceof RateLimitError) {
    // Wait and retry
    await new Promise(r => setTimeout(r, err.retryAfter ?? 60_000));
  } else if (err instanceof SattabaseError) {
    console.error(`Sattabase error: ${err.message} (status=${err.status})`);
  }
}
```

## Running Tests

```bash
cd sdk/typescript

# Install dependencies
npm install

# Build the SDK
npm run build

# Run all tests (unit + integration if backend available)
npm test

# Run tests in watch mode
npm run test:watch

# Type check
npm run lint
```

Tests use `vitest` with mocked `fetch` (globalThis.fetch). Unit tests (50 tests in `index.test.ts`) cover config, exceptions, auth, access, redirect, models, token store, and client request handling. Integration tests in `integration.test.ts` require a running Sattabase backend.

## Development

### Project Structure

```
sdk/typescript/
  package.json              # Build config (tsup), scripts, dependencies
  tsconfig.json             # TypeScript config (strict, ES2020, ESM)
  tsup.config.ts            # Build config (tsup → ESM + CJS + DTS)
  vitest.config.ts          # Test config (vitest)
  src/
    index.ts               # Public API exports + VERSION
    config.ts              # SattabaseConfig class with validation
    client.ts              # SattabaseClient — HTTP client + auto-refresh
    auth.ts                # AuthModule — login, register, me, refresh, verify, etc.
    access.ts              # AccessModule — cached feature gating helpers
    redirect.ts            # BillingRedirect — URL constructors + detectBillingUpdate
    token-store.ts         # TokenStore interface + InMemory + LocalStorage stores
    models.ts              # TypeScript interfaces + AuthMeResponse class
    exceptions.ts          # Typed exception hierarchy + buildError mapper
  tests/
    index.test.ts          # 50 unit tests covering all modules
    integration.test.ts    # Integration tests (requires running backend)
  dist/                     # Built output (ESM + CJS + DTS)
    index.js               # ESM entry
    index.cjs              # CJS entry
    index.d.ts             # TypeScript declarations (ESM)
    index.d.cts            # TypeScript declarations (CJS)
```

### Toolchain

| Tool | Purpose |
|---|---|
| [tsup](https://tsup.egoist.dev/) | Build (ESM + CJS + DTS) |
| [TypeScript](https://www.typescriptlang.org/) | Strict type checking |
| [vitest](https://vitest.dev/) | Unit testing with mocked fetch |
| Native `fetch` | HTTP client (zero dependencies) |

### Building

```bash
npm run build
# → dist/index.js       (ESM)
# → dist/index.cjs      (CJS)
# → dist/index.d.ts     (TypeScript declarations)
# → dist/index.d.cts    (TypeScript declarations for CJS)
```

## Architecture Overview

```
+-------------------+         SDK Scope          +-------------------+
|                   |  (Auth + Permissions)      |                   |
|  Sister Domain    | <========================> |    Sattabase      |
|  (finance app)    |                            |   (this platform) |
|                   |                            |                   |
|  - Django/FastAPI |   X-API-Key (server only) |  - Django Ninja   |
|  - Vue/React/Next |   X-Service-Domain        |  - Stripe         |
|  - Own database   |   Authorization: Bearer    |  - User records   |
|    Uses user.id   |                            |  - Subscriptions  |
|    as foreign key |                            |                   |
+-------------------+                            +-------------------+
        |                                                |
        |  billing_updated=1                              |  Stripe
        |  (redirect back)                                |  (payments)
        +<-----------------------------------------------+
```

**Key principles:**

- **Dual mode** — server mode (API key for service-to-service auth) and browser mode (JWT-only, no secret in frontend code). When `apiKey` is omitted, the SDK sends only `Authorization` and `X-Service-Domain` headers.
- **Zero dependencies** — uses native `fetch`, works in browser and Node.js 18+
- **Type-safe** — full TypeScript strict mode with exported declaration files
- **SDK surface is small and stable** — auth schemas rarely change, while billing schemas change often
- **Each sister domain has its own database** — the SDK provides only the identity layer and permission layer
- **Billing is never proxied** — for subscription management, the SDK generates redirect URLs to Sattabase
- **Auto-refresh is built-in** — automatically handles token refresh on 401 responses using a promise-based lock
- **Dual format** — ships both ESM and CJS for maximum compatibility

## License

MIT
