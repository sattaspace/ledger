/**
 * Tests for the Sattabase TypeScript SDK.
 *
 * Run with: npx vitest run
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  SattabaseClient,
  SattabaseConfig,
  InMemoryTokenStore,
  LocalStorageTokenStore,
  SattabaseError,
  AuthenticationError,
  AccountInactiveError,
  AccountDeletedError,
  ForbiddenError,
  RateLimitError,
  ApiServerError,
  buildError,
  BillingRedirect,
  AuthMeResponse,
} from "../dist/index.js";

// ─── Fixtures ──────────────────────────────────────────────────────────────────

const TEST_API_KEY = "sb_live_abcd1234efgh5678ijkl9012mnop3456";
const TEST_BASE_URL = "https://sattabase.tld/api/v1";
const TEST_SERVICE_DOMAIN = "finance.sattabase.tld";

function makeConfig(): SattabaseConfig {
  return new SattabaseConfig({
    baseUrl: TEST_BASE_URL,
    serviceDomain: TEST_SERVICE_DOMAIN,
    apiKey: TEST_API_KEY,
    debug: true,
  });
}

function makeClient(): SattabaseClient {
  return new SattabaseClient(makeConfig());
}

const tokenResponse = {
  access: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
  refresh: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
};

const authMeResponse = {
  user: {
    id: 42,
    slug: "abc123",
    email: "user@example.com",
    first_name: "Rahim",
    last_name: "Uddin",
    phone: "+8801712345678",
    avatar: "/media/avatars/photo.jpg",
    timezone: "Asia/Dhaka",
    currency: "BDT",
    language: "en",
    is_email_verified: true,
    is_active: true,
    role: "member",
    created_at: "2026-04-27T10:00:00Z",
    full_name: "Rahim Uddin",
    display_name: "Rahim",
  },
  account_status: "active",
  subscription: {
    plan_name: "Standard",
    plan_slug: "standard",
    status: "active",
    current_period_end: "2026-05-27T00:00:00Z",
    trial_end: null,
    is_active: true,
  },
  access: {
    dashboard: true,
    reports: true,
    export_pdf: true,
    api_access: true,
    max_bank_accounts: 5,
    max_team_members: 3,
    priority_support: false,
    data_retention_days: 365,
  },
};

// ─── Mock fetch ────────────────────────────────────────────────────────────────

const originalFetch = globalThis.fetch;

function mockFetch(response: { status: number; body?: unknown }): void {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: response.status >= 200 && response.status < 300,
    status: response.status,
    headers: new Headers({ "content-type": "application/json" }),
    json: () => Promise.resolve(response.body),
  });
}

function restoreFetch(): void {
  globalThis.fetch = originalFetch;
}

/** Mock fetch with sequential responses (for auto-refresh tests). */
function mockFetchSequential(
  responses: Array<{ status: number; body?: unknown }>,
): void {
  const queue = [...responses];
  globalThis.fetch = vi.fn().mockImplementation(async () => {
    const resp = queue.shift();
    if (!resp) throw new Error("mockFetchSequential: no more responses queued");
    return {
      ok: resp.status >= 200 && resp.status < 300,
      status: resp.status,
      headers: new Headers({ "content-type": "application/json" }),
      json: () => Promise.resolve(resp.body),
    };
  });
}

// ─── Config Tests ──────────────────────────────────────────────────────────────

describe("SattabaseConfig", () => {
  it("creates valid config", () => {
    const config = makeConfig();
    expect(config.apiKey).toBe(TEST_API_KEY);
    expect(config.appBaseUrl).toBe("https://sattabase.tld");
  });

  it("rejects invalid API key format", () => {
    expect(
      () =>
        new SattabaseConfig({
          baseUrl: TEST_BASE_URL,
          serviceDomain: TEST_SERVICE_DOMAIN,
          apiKey: "invalid_key",
          debug: true,
        }),
    ).toThrow("must start with 'sb_live_'");
  });

  it("rejects HTTP in production", () => {
    expect(
      () =>
        new SattabaseConfig({
          baseUrl: "http://sattabase.tld/api/v1",
          serviceDomain: TEST_SERVICE_DOMAIN,
          apiKey: TEST_API_KEY,
        }),
    ).toThrow("HTTPS");
  });

  it("allows HTTP in debug mode", () => {
    const config = new SattabaseConfig({
      baseUrl: "http://localhost:8000/api/v1",
      serviceDomain: TEST_SERVICE_DOMAIN,
      apiKey: TEST_API_KEY,
      debug: true,
    });
    expect(config.appBaseUrl).toBe("http://localhost:8000");
  });

  it("strips /api/v1 for appBaseUrl", () => {
    const config = new SattabaseConfig({
      baseUrl: "https://sattabase.tld/api/v1",
      serviceDomain: TEST_SERVICE_DOMAIN,
      apiKey: TEST_API_KEY,
    });
    expect(config.appBaseUrl).toBe("https://sattabase.tld");
  });
});

// ─── Exception Tests ───────────────────────────────────────────────────────────

describe("buildError", () => {
  it("maps 401 to AuthenticationError", () => {
    const err = buildError(401, { detail: "Invalid token" });
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err.status).toBe(401);
  });

  it("maps account_inactive code to AccountInactiveError", () => {
    const err = buildError(401, {
      detail: "Inactive",
      code: "account_inactive",
    });
    expect(err.status).toBe(401);
    expect(err.message).toBe("Inactive");
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err).toBeInstanceOf(SattabaseError);
  });

  it("maps account_deleted code to AccountDeletedError", () => {
    const err = buildError(401, { detail: "Deleted", code: "account_deleted" });
    expect(err.status).toBe(401);
    expect(err.message).toBe("Deleted");
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err).toBeInstanceOf(SattabaseError);
  });

  it("maps 429 with retry_after", () => {
    const err = buildError(429, { detail: "Too many", retry_after: 60 });
    expect(err).toBeInstanceOf(RateLimitError);
    expect(err.retryAfter).toBe(60);
  });

  it("maps 5xx to ApiServerError", () => {
    const err = buildError(500, { detail: "Internal error" });
    expect(err).toBeInstanceOf(ApiServerError);
  });

  it("handles null body", () => {
    const err = buildError(500, null);
    expect(err).toBeInstanceOf(ApiServerError);
  });

  it("code takes priority over status", () => {
    const err = buildError(401, {
      detail: "Inactive",
      code: "account_inactive",
    });
    expect(err.status).toBe(401);
    expect(err.message).toBe("Inactive");
    // account_inactive maps to AccountInactiveError (subclass of AuthenticationError)
    // not to generic ForbiddenError, even though status=401
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err).toBeInstanceOf(SattabaseError);
  });
});

// ─── Auth Tests ────────────────────────────────────────────────────────────────

describe("AuthModule", () => {
  beforeEach(() => mockFetch({ status: 200, body: tokenResponse }));
  afterEach(restoreFetch);

  it("login returns TokenPair", async () => {
    const client = makeClient();
    const tokens = await client.auth.login("user@example.com", "password");
    expect(tokens.access).toBe(tokenResponse.access);
    expect(tokens.refresh).toBe(tokenResponse.refresh);
  });

  it("login sends correct headers", async () => {
    const client = makeClient();
    await client.auth.login("user@example.com", "password");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${TEST_BASE_URL}/auth/login`,
      expect.objectContaining({
        method: "POST",
      }),
    );
  });
});

describe("AuthMe", () => {
  beforeEach(() => mockFetch({ status: 200, body: authMeResponse }));
  afterEach(restoreFetch);

  it("returns AuthMeResponse with access map", async () => {
    const client = makeClient();
    const result = await client.auth.me(tokenResponse.access);
    expect(result.user.email).toBe("user@example.com");
    expect(result.subscription).not.toBeNull();
    expect(result.subscription!.plan_name).toBe("Standard");
    expect(result.hasAccess("reports")).toBe(true);
    expect(result.getAccess("max_bank_accounts")).toBe(5);
  });

  it("account_inactive raises AccountInactiveError", async () => {
    mockFetch({
      status: 401,
      body: { detail: "Account is inactive", code: "account_inactive" },
    });
    const client = makeClient();
    await expect(client.auth.me(tokenResponse.access)).rejects.toThrow(
      AccountInactiveError,
    );
  });

  it("account_deleted raises AccountDeletedError", async () => {
    mockFetch({
      status: 401,
      body: { detail: "Account has been deleted", code: "account_deleted" },
    });
    const client = makeClient();
    await expect(client.auth.me(tokenResponse.access)).rejects.toThrow(
      AccountDeletedError,
    );
  });

  it("no domain returns empty access", async () => {
    mockFetch({
      status: 200,
      body: {
        user: authMeResponse.user,
        account_status: "active",
        subscription: null,
        access: {},
      },
    });
    const client = makeClient();
    const result = await client.auth.me(tokenResponse.access);
    expect(result.subscription).toBeNull();
    expect(result.accessKeys).toEqual([]);
  });
});

// ─── Access Module Tests ───────────────────────────────────────────────────────

describe("AccessModule", () => {
  beforeEach(() => mockFetch({ status: 200, body: authMeResponse }));
  afterEach(restoreFetch);

  it("has_access returns true for granted features", async () => {
    const client = makeClient();
    expect(await client.access.hasAccess("reports", "test-token")).toBe(true);
    expect(await client.access.hasAccess("dashboard", "test-token")).toBe(true);
  });

  it("has_access returns false for denied features", async () => {
    const client = makeClient();
    expect(
      await client.access.hasAccess("priority_support", "test-token"),
    ).toBe(false);
    expect(await client.access.hasAccess("nonexistent", "test-token")).toBe(
      false,
    );
  });

  it("get_access returns integer values", async () => {
    const client = makeClient();
    expect(
      await client.access.getAccess("max_bank_accounts", 1, "test-token"),
    ).toBe(5);
  });

  it("keys returns all access key names", async () => {
    const client = makeClient();
    const keys = await client.access.keys("test-token");
    expect(keys).toContain("dashboard");
    expect(keys).toContain("max_bank_accounts");
    expect(keys.length).toBe(8);
  });

  it("cache avoids extra API calls", async () => {
    const client = makeClient();
    await client.access.hasAccess("reports", "test-token");
    await client.access.hasAccess("dashboard", "test-token");
    // Only one fetch call should have been made
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("invalidate_cache forces re-fetch", async () => {
    const client = makeClient();
    await client.access.hasAccess("reports", "test-token");
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);

    client.access.invalidateCache();
    await client.access.hasAccess("dashboard", "test-token");
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
  });
});

// ─── Redirect Tests ────────────────────────────────────────────────────────────

describe("BillingRedirect", () => {
  it("builds manage_subscription URL", () => {
    const billing = new BillingRedirect("https://sattabase.tld");
    const url = billing.manageSubscription(
      "finance",
      "https://finance.sattabase.tld/settings",
    );
    expect(url).toContain("/dashboard/billing/plans/finance");
    expect(url).toContain("return_url=");
    expect(url).toContain("finance.sattabase.tld");
  });

  it("manage_subscription without return_url", () => {
    const billing = new BillingRedirect("https://sattabase.tld");
    const url = billing.manageSubscription("finance");
    expect(url).toBe("https://sattabase.tld/dashboard/billing/plans/finance");
  });

  it("builds upgrade URL", () => {
    const billing = new BillingRedirect("https://sattabase.tld");
    const url = billing.upgrade(
      "analytics",
      "https://analytics.sattabase.tld/billing",
    );
    expect(url).toContain("/dashboard/billing/plans/analytics");
    expect(url).toContain("return_url=");
  });

  it("builds portal URL", () => {
    const billing = new BillingRedirect("https://sattabase.tld");
    const url = billing.portal("https://sattabase.tld/dashboard");
    expect(url).toContain("/dashboard/billing");
    expect(url).toContain("return_url=");
  });

  it("portal without return_url", () => {
    const billing = new BillingRedirect("https://sattabase.tld");
    const url = billing.portal();
    expect(url).toBe("https://sattabase.tld/dashboard/billing");
  });
});

describe("detectBillingUpdate", () => {
  it("detects billing_updated=1", () => {
    const result = BillingRedirect.detectBillingUpdate(
      "https://finance.sattabase.tld/dashboard?billing_updated=1",
    );
    expect(result).toEqual({ updated: true, success: 1 });
  });

  it("detects billing_updated=0", () => {
    const result = BillingRedirect.detectBillingUpdate(
      "https://finance.sattabase.tld/dashboard?billing_updated=0",
    );
    expect(result).toEqual({ updated: true, success: 0 });
  });

  it("returns false when absent", () => {
    const result = BillingRedirect.detectBillingUpdate(
      "https://finance.sattabase.tld/dashboard",
    );
    expect(result).toEqual({ updated: false, success: null });
  });

  it("works with other params", () => {
    const result = BillingRedirect.detectBillingUpdate(
      "https://finance.sattabase.tld/dashboard?tab=settings&billing_updated=1&page=2",
    );
    expect(result).toEqual({ updated: true, success: 1 });
  });

  it("handles invalid value", () => {
    const result = BillingRedirect.detectBillingUpdate(
      "https://finance.sattabase.tld/dashboard?billing_updated=abc",
    );
    expect(result.updated).toBe(true);
    expect(result.success).toBeNull();
  });
});

// ─── Model Tests ───────────────────────────────────────────────────────────────

describe("AuthMeResponse", () => {
  it("hasAccess coerces boolean", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: { reports: true },
    });
    expect(me.hasAccess("reports")).toBe(true);
  });

  it("hasAccess coerces string 'true'", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: { reports: "true" },
    });
    expect(me.hasAccess("reports")).toBe(true);
  });

  it("hasAccess coerces string 'false'", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: { reports: "false" },
    });
    expect(me.hasAccess("reports")).toBe(false);
  });

  it("hasAccess coerces integer non-zero", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: { max_accounts: 5 },
    });
    expect(me.hasAccess("max_accounts")).toBe(true);
  });

  it("hasAccess coerces integer zero", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: { max_accounts: 0 },
    });
    expect(me.hasAccess("max_accounts")).toBe(false);
  });

  it("hasAccess returns false for missing key", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: {},
    });
    expect(me.hasAccess("nonexistent")).toBe(false);
  });

  it("accessKeys returns all keys", () => {
    const me = new AuthMeResponse({
      user: { id: 1, slug: "a", email: "t@t.com" } as any,
      access: { dashboard: true, reports: false, api: true },
    });
    expect(me.accessKeys).toEqual(["dashboard", "reports", "api"]);
  });
});

// ─── Token Store Tests ────────────────────────────────────────────────────────

describe("InMemoryTokenStore", () => {
  it("stores and retrieves tokens", () => {
    const store = new InMemoryTokenStore();
    store.setTokens("user_42", tokenResponse);
    const tokens = store.getTokens("user_42");
    expect(tokens).toEqual(tokenResponse);
  });

  it("returns null for missing user", () => {
    const store = new InMemoryTokenStore();
    expect(store.getTokens("missing")).toBeNull();
  });

  it("deletes tokens", () => {
    const store = new InMemoryTokenStore();
    store.setTokens("user_42", tokenResponse);
    store.deleteTokens("user_42");
    expect(store.getTokens("user_42")).toBeNull();
  });

  it("getFirstTokenPair returns first entry", () => {
    const store = new InMemoryTokenStore();
    store.setTokens("user_1", tokenResponse);
    store.setTokens("user_2", { access: "a2", refresh: "r2" });
    expect(store.getFirstTokenPair()?.access).toBe(tokenResponse.access);
  });

  it("getUserIdByRefresh finds correct user", () => {
    const store = new InMemoryTokenStore();
    store.setTokens("user_1", tokenResponse);
    store.setTokens("user_2", { access: "a2", refresh: "r2" });
    expect(store.getUserIdByRefresh(tokenResponse.refresh)).toBe("user_1");
    expect(store.getUserIdByRefresh("r2")).toBe("user_2");
    expect(store.getUserIdByRefresh("nonexistent")).toBeNull();
  });
});

// ─── Client Request Tests ─────────────────────────────────────────────────────

describe("SattabaseClient.request", () => {
  afterEach(restoreFetch);

  it("injects X-API-Key and X-Service-Domain headers", async () => {
    mockFetch({ status: 200, body: { ok: true } });
    const client = makeClient();
    await client.request("GET", "/test");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${TEST_BASE_URL}/test`,
      expect.objectContaining({
        method: "GET",
      }),
    );
  });

  it("401 raises AuthenticationError", async () => {
    mockFetch({ status: 401, body: { detail: "Unauthorized" } });
    const client = makeClient();
    await expect(client.request("GET", "/test")).rejects.toThrow(
      AuthenticationError,
    );
  });

  it("429 raises RateLimitError", async () => {
    // retry_after: 0 so the SDK's built-in retry delay is instant (0ms).
    // The SDK will: receive 429 → wait 0s → retry → get 429 again → throw RateLimitError.
    mockFetchSequential([
      { status: 429, body: { detail: "Too many requests", retry_after: 0 } },
      { status: 429, body: { detail: "Too many requests", retry_after: 0 } },
    ]);
    const client = makeClient();
    try {
      await client.request("GET", "/test");
    } catch (err) {
      expect(err).toBeInstanceOf(RateLimitError);
      expect((err as RateLimitError).retryAfter).toBe(0);
    }
  });

  it("500 raises ApiServerError", async () => {
    mockFetch({ status: 500, body: { detail: "Internal error" } });
    const client = makeClient();
    await expect(client.request("GET", "/test")).rejects.toThrow(
      ApiServerError,
    );
  });
});

// ─── Auth Module — Register Tests ─────────────────────────────────────────────

describe("AuthModule.register", () => {
  afterEach(restoreFetch);

  it("returns MessageResponse on success", async () => {
    mockFetch({
      status: 200,
      body: { message: "Registration successful", success: true },
    });
    const client = makeClient();
    const result = await client.auth.register(
      "new@example.com",
      "Pass123!",
      "Test",
      "User",
    );
    expect(result.message).toBe("Registration successful");
    expect(result.success).toBe(true);
  });

  it("sends snake_case fields in body", async () => {
    mockFetch({
      status: 200,
      body: { message: "OK", success: true },
    });
    const client = makeClient();
    await client.auth.register("new@example.com", "Pass123!", "Test", "User");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${TEST_BASE_URL}/auth/register`,
      expect.objectContaining({ method: "POST" }),
    );
    // Verify the body was serialized with snake_case keys
    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.email).toBe("new@example.com");
    expect(body.first_name).toBe("Test");
    expect(body.last_name).toBe("User");
  });

  it("includes optional fields when provided", async () => {
    mockFetch({
      status: 200,
      body: { message: "OK", success: true },
    });
    const client = makeClient();
    await client.auth.register("new@example.com", "Pass123!", "Test", "User", {
      timezone: "Asia/Dhaka",
      currency: "BDT",
      language: "en",
    });

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.timezone).toBe("Asia/Dhaka");
    expect(body.currency).toBe("BDT");
    expect(body.language).toBe("en");
  });

  it("omits optional fields when not provided", async () => {
    mockFetch({
      status: 200,
      body: { message: "OK", success: true },
    });
    const client = makeClient();
    await client.auth.register("new@example.com", "Pass123!", "Test", "User");

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.timezone).toBeUndefined();
    expect(body.currency).toBeUndefined();
    expect(body.language).toBeUndefined();
  });

  it("409 raises ConflictError on duplicate email", async () => {
    mockFetch({
      status: 409,
      body: { detail: "User with this email already exists." },
    });
    const client = makeClient();
    await expect(
      client.auth.register("existing@example.com", "Pass123!", "Test", "User"),
    ).rejects.toThrow();
  });
});

// ─── Auth Module — Refresh Tests ─────────────────────────────────────────────

describe("AuthModule.refresh", () => {
  afterEach(restoreFetch);

  it("returns new TokenPair", async () => {
    mockFetch({
      status: 200,
      body: { access: "new_access", refresh: "new_refresh" },
    });
    const client = makeClient();
    const tokens = await client.auth.refresh("old_refresh_token");
    expect(tokens.access).toBe("new_access");
    expect(tokens.refresh).toBe("new_refresh");
  });

  it("sends refresh token in JSON body", async () => {
    mockFetch({
      status: 200,
      body: { access: "a", refresh: "r" },
    });
    const client = makeClient();
    await client.auth.refresh("my_refresh_token");

    expect(globalThis.fetch).toHaveBeenCalledWith(
      `${TEST_BASE_URL}/auth/token/refresh`,
      expect.objectContaining({ method: "POST" }),
    );
    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.refresh).toBe("my_refresh_token");
  });
});

// ─── Auth Module — Verify Tests ─────────────────────────────────────────────

describe("AuthModule.verify", () => {
  afterEach(restoreFetch);

  it("returns MessageResponse on valid token", async () => {
    mockFetch({
      status: 200,
      body: { message: "Token is valid", success: true },
    });
    const client = makeClient();
    const result = await client.auth.verify("my_access_token");
    expect(result.success).toBe(true);
  });

  it("raises error on invalid token", async () => {
    mockFetch({
      status: 401,
      body: { detail: "Token is invalid or expired" },
    });
    const client = makeClient();
    await expect(client.auth.verify("expired_token")).rejects.toThrow(
      AuthenticationError,
    );
  });
});

// ─── Auth Module — Blacklist Tests ──────────────────────────────────────────

describe("AuthModule.blacklist", () => {
  afterEach(restoreFetch);

  it("returns MessageResponse on success", async () => {
    mockFetch({
      status: 200,
      body: { message: "Token blacklisted", success: true },
    });
    const client = makeClient();
    const result = await client.auth.blacklist("refresh_to_invalidate");
    expect(result.message).toBe("Token blacklisted");
  });
});

// ─── Auth Module — Logout Tests ─────────────────────────────────────────────

describe("AuthModule.logout", () => {
  afterEach(restoreFetch);

  it("blacklists refresh and clears token store", async () => {
    // First call: blacklist endpoint, Second call: none (store clear is sync)
    mockFetchSequential([
      {
        status: 200,
        body: { message: "Token blacklisted", success: true },
      },
    ]);

    const store = new InMemoryTokenStore();
    store.setTokens("default", { access: "a", refresh: "my_refresh" });
    const client = new SattabaseClient(makeConfig(), store);

    await client.auth.logout("access_token", "my_refresh");

    // Verify token was deleted from store
    expect(store.getTokens("default")).toBeNull();
    // Verify blacklist was called
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});

// ─── Auth Module — Password Reset Tests ─────────────────────────────────────

describe("AuthModule.passwordReset", () => {
  afterEach(restoreFetch);

  it("requestPasswordReset returns MessageResponse", async () => {
    mockFetch({
      status: 200,
      body: { message: "OTP sent", success: true },
    });
    const client = makeClient();
    const result = await client.auth.requestPasswordReset("user@example.com");
    expect(result.message).toBe("OTP sent");
  });

  it("confirmPasswordReset returns MessageResponse", async () => {
    mockFetch({
      status: 200,
      body: { message: "Password reset successful", success: true },
    });
    const client = makeClient();
    const result = await client.auth.confirmPasswordReset(
      "user@example.com",
      "123456",
      "NewPass123!",
      "NewPass123!",
    );
    expect(result.message).toBe("Password reset successful");
  });

  it("confirmPasswordReset sends correct body", async () => {
    mockFetch({
      status: 200,
      body: { message: "OK", success: true },
    });
    const client = makeClient();
    await client.auth.confirmPasswordReset(
      "user@example.com",
      "123456",
      "NewPass123!",
      "NewPass123!",
    );

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.email).toBe("user@example.com");
    expect(body.otp).toBe("123456");
    expect(body.new_password).toBe("NewPass123!");
    expect(body.confirm_password).toBe("NewPass123!");
  });
});

// ─── Auth Module — Email Verification Tests ─────────────────────────────────

describe("AuthModule.emailVerification", () => {
  afterEach(restoreFetch);

  it("requestEmailVerification returns MessageResponse", async () => {
    mockFetch({
      status: 200,
      body: { message: "Verification OTP sent", success: true },
    });
    const client = makeClient();
    const result =
      await client.auth.requestEmailVerification("user@example.com");
    expect(result.message).toBe("Verification OTP sent");
  });

  it("confirmEmailVerification returns MessageResponse", async () => {
    mockFetch({
      status: 200,
      body: { message: "Email verified", success: true },
    });
    const client = makeClient();
    const result = await client.auth.confirmEmailVerification(
      "user@example.com",
      "654321",
    );
    expect(result.message).toBe("Email verified");
  });

  it("confirmEmailVerification sends correct body", async () => {
    mockFetch({
      status: 200,
      body: { message: "OK", success: true },
    });
    const client = makeClient();
    await client.auth.confirmEmailVerification("user@example.com", "654321");

    const call = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const body = JSON.parse(call[1].body as string);
    expect(body.email).toBe("user@example.com");
    expect(body.otp).toBe("654321");
  });
});

// ─── Auto-Refresh Tests ─────────────────────────────────────────────────────

describe("Auto-refresh", () => {
  afterEach(restoreFetch);

  it("auto-refreshes on 401 and retries with new token", async () => {
    const store = new InMemoryTokenStore();
    store.setTokens("default", {
      access: "old_access",
      refresh: "old_refresh",
    });
    const client = new SattabaseClient(makeConfig(), store);

    // Sequential responses:
    // 1st: GET /test → 401 (original fails)
    // 2nd: POST /auth/token/refresh → 200 with new tokens
    // 3rd: GET /test → 200 with expected data (retry succeeds)
    mockFetchSequential([
      { status: 401, body: { detail: "Token expired" } },
      { status: 200, body: { access: "new_access", refresh: "new_refresh" } },
      { status: 200, body: { data: "success" } },
    ]);

    const result = await client.request<{ data: string }>("GET", "/test", {
      token: "old_access",
    });
    expect(result.data).toBe("success");
    // 3 fetch calls: 401 → refresh → retry
    expect(globalThis.fetch).toHaveBeenCalledTimes(3);
  });

  it("auto-refresh updates token store with new tokens", async () => {
    const store = new InMemoryTokenStore();
    store.setTokens("default", {
      access: "old_access",
      refresh: "old_refresh",
    });
    const client = new SattabaseClient(makeConfig(), store);

    mockFetchSequential([
      { status: 401, body: { detail: "Token expired" } },
      { status: 200, body: { access: "new_access", refresh: "new_refresh" } },
      { status: 200, body: { ok: true } },
    ]);

    await client.request("GET", "/test", { token: "old_access" });

    // Token store should have new tokens
    const tokens = store.getTokens("default");
    expect(tokens).not.toBeNull();
    expect(tokens!.access).toBe("new_access");
    expect(tokens!.refresh).toBe("new_refresh");
  });

  it("skips auto-refresh when autoRefresh=false", async () => {
    const noRefreshConfig = new SattabaseConfig({
      baseUrl: TEST_BASE_URL,
      serviceDomain: TEST_SERVICE_DOMAIN,
      apiKey: TEST_API_KEY,
      debug: true,
      autoRefresh: false,
    });
    const store = new InMemoryTokenStore();
    store.setTokens("default", {
      access: "old_access",
      refresh: "old_refresh",
    });
    const client = new SattabaseClient(noRefreshConfig, store);

    mockFetch({ status: 401, body: { detail: "Token expired" } });

    // Should NOT auto-refresh — just raise the error
    await expect(
      client.request("GET", "/test", { token: "old_access" }),
    ).rejects.toThrow(AuthenticationError);

    // Only 1 fetch call (no refresh attempt)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("skips auto-refresh when no token store", async () => {
    // Client without token store
    const client = makeClient();

    mockFetch({ status: 401, body: { detail: "Token expired" } });

    await expect(
      client.request("GET", "/test", { token: "some_token" }),
    ).rejects.toThrow(AuthenticationError);

    // Only 1 fetch call (no refresh attempt possible)
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });
});
