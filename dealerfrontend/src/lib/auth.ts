/**
 * Auth utilities — authentication functions for the SattaBase sister domain.
 *
 * Sister domains only have LOGIN and LOGOUT screens. Everything else
 * (register, forgot password, reset, verify, profile, billing) redirects
 * to the SattaBase base domain.
 *
 * The Token Pass-Through (authorization code) flow enables seamless SSO:
 *   1. User clicks "Manage Subscription" on sister domain
 *   2. Sister domain calls POST /auth/authorize → gets one-time code
 *   3. Sister domain redirects to base domain's callback with ?code=XXX
 *   4. Base domain exchanges code for tokens, stores them, redirects to target page
 *
 * AUTH COOKIE FLOW (post-migration):
 *   login()  → POST /api/auth/login   (Astro proxy → sets httpOnly cookie)
 *   logout() → POST /api/auth/logout  (Astro proxy → clears httpOnly cookie)
 *   The refresh token NEVER enters JavaScript — it lives only in the
 *   `sb_refresh_token` httpOnly Secure cookie managed by the browser.
 *   See src/middleware.ts and src/pages/api/auth/* for the server side.
 */

import { apiClient, authHelpers, clearTokens } from "./api";
import { clearDsrPortalState } from "../composables/useDsrPortal";
import type {
  ApiError,
  AuthMeResponse,
  TokenPair,
  AuthorizeResponse,
} from "./types";
import config from "../../sattabase.config";

/**
 * POST to a same-origin Astro endpoint (the /api/auth/* proxy).
 *
 * We use raw fetch here instead of apiClient because apiClient prepends
 * `API_BASE_URL` (the Sattabase URL) to every path. The login/logout
 * proxies live on this origin (dealerfrontend), not Sattabase — they
 * exist specifically to land the httpOnly cookie on this origin.
 *
 * credentials: 'include' is REQUIRED so the browser auto-sends the
 * sb_refresh_token cookie when present (e.g. logout needs it so
 * Sattabase can blacklist the token).
 */
async function postSameOrigin<T = unknown>(
  path: string,
  body?: unknown,
): Promise<T> {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    credentials: "include",
  });
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;
    try {
      const errBody = await response.json();
      if (errBody?.detail) message = errBody.detail;
    } catch {
      /* not JSON */
    }
    const err: ApiError = { status: response.status, message };
    throw err;
  }
  // Some endpoints (logout) return 204 with no body — handle gracefully.
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// ─── Login ───────────────────────────────────────────────────────────────────

/**
 * Login — POST /api/auth/login (Astro proxy) → store access token.
 *
 * The proxy forwards credentials to Sattabase /auth/login, which:
 *   - Sets the refresh token in an `sb_refresh_token` httpOnly cookie
 *     (propagated onto the dealerfrontend origin by the proxy).
 *   - Returns the short-lived access token in the JSON response body.
 *
 * This function POSTs to the relative /api/auth/login path so the
 * browser hits the Astro server (not Sattabase directly). That way
 * the Set-Cookie response from Sattabase lands on the dealerfrontend
 * origin (where the Astro middleware can read it) instead of on the
 * Sattabase origin.
 *
 * @param email - User email address
 * @param password - User password
 * @param remember - If true, Sattabase issues a persistent refresh
 *                   cookie (30 days). If false, it's a session cookie.
 */
export async function login(
  email: string,
  password: string,
  remember = false,
): Promise<{ access: string }> {
  const data = await postSameOrigin<{ access: string }>("/api/auth/login", {
    email,
    password,
    remember,
  });
  // Persist access token in memory only (refresh lives in httpOnly cookie).
  authHelpers.setTokens(data.access);
  // Defensive: a dealer login must never inherit a stale DSR portal flag
  // (e.g. user was a DSR in portal mode, closed the tab, now logging in
  // as dealer on the same browser). Clearing the flag prevents the
  // "DSR Portal Mode" banner from showing on the dealer UI.
  clearDsrPortalState();
  return data;
}

// ─── Logout ──────────────────────────────────────────────────────────────────

/**
 * Logout — POST /api/auth/logout (Astro proxy) → clear cookie + memory.
 *
 * The proxy forwards the request to Sattabase /auth/logout with the
 * refresh cookie in a Cookie header so Sattabase can blacklist the
 * token (AUTH-2 CSRF protection), then propagates the clearing
 * Set-Cookie headers back to the browser.
 *
 * If the request fails (network error, etc.) we still clear local
 * state and redirect to /login — the user is effectively logged out
 * at the browser level even if the server blacklist was missed.
 */
export async function logout(): Promise<void> {
  try {
    await postSameOrigin<void>("/api/auth/logout");
  } catch {
    // Even if the proxy fails, clear local state — the user wants out.
  }
  clearTokens();
  // Clear any stale DSR portal state so the next dealer login doesn't
  // inherit the banner (and so the next DSR login starts cleanly).
  clearDsrPortalState();
  if (typeof window !== "undefined") {
    // Redirect to the dedicated /login page (MPA refactor).
    window.location.href = "/login";
  }
}

// ─── Get Auth Me ─────────────────────────────────────────────────────────────

/**
 * Get current user profile with domain-scoped subscription and access map.
 *
 * Calls GET /billing/auth/me with the X-Service-Domain header
 * (injected by api.ts). Returns user + subscription + access data
 * scoped to this sister domain's product.
 */
export async function getAuthMe(): Promise<AuthMeResponse> {
  return apiClient.get<AuthMeResponse>("/billing/auth/me");
}

// ─── Authorization Code (SSO) ────────────────────────────────────────────────

/**
 * Generate a one-time authorization code for SSO redirect to base domain.
 *
 * The sister domain calls this after the user is authenticated, then redirects
 * the user to the base domain's callback URL with the code. The base domain
 * exchanges the code for tokens, establishing a seamless cross-domain session.
 *
 * POST /auth/authorize → returns { code, expires_in }
 */
export async function generateAuthCode(): Promise<AuthorizeResponse> {
  return apiClient.post<AuthorizeResponse>("/auth/authorize");
}

/**
 * Exchange an authorization code for JWT tokens.
 *
 * Used by the BASE domain's callback page (not the sister domain directly).
 * Included here for completeness and for potential future use if a sister
 * domain receives a code from another domain.
 *
 * POST /auth/token/exchange → returns { access, refresh }
 */
export async function exchangeAuthCode(code: string): Promise<TokenPair> {
  const data = await apiClient.post<TokenPair>("/auth/token/exchange", {
    code,
  });
  // Audit fix L1: previously called setTokens(data.access, data.refresh)
  // with two args — but setTokens only accepts one (the refresh token
  // lives in an httpOnly cookie set by the backend, not in JS memory).
  // The second arg was silently ignored. We now call with just the
  // access token. Note: exchangeAuthCode is currently unused (it's a
  // stub for a future SSO flow where the BASE domain might forward a
  // code back to the sister domain). If that flow is implemented, the
  // backend should set the refresh cookie via a proxy endpoint, not
  // return the refresh token in the JSON body.
  authHelpers.setTokens(data.access);
  return data;
}

// ─── Redirect to Base Domain ─────────────────────────────────────────────────

/**
 * Construct a base domain URL and redirect the browser.
 *
 * Used for all flows that the sister domain doesn't handle:
 *   - Register: redirectToBase('/auth/register')
 *   - Forgot password: redirectToBase('/auth/forgot-password')
 *   - Reset password: redirectToBase('/auth/reset-password')
 *   - Verify email: redirectToBase('/auth/verify-email')
 *   - Profile: redirectToBase('/dashboard/profile')
 *   - Billing: redirectToBase('/dashboard/billing')
 *
 * @param path - The path on the base domain (e.g. '/auth/register')
 * @param returnUrl - Optional return URL. If provided, appends ?return_url=
 *                    so the base domain can redirect back after the action.
 */
export function redirectToBase(path: string, returnUrl?: string): void {
  let url = `${config.baseDomainUrl}${path}`;
  // FIX L-8: validate returnUrl before using it. Without this check, an
  // attacker-controlled link can hand us `returnUrl=https://evil.com/phish`
  // and we'll happily pass it to the base domain, which will redirect the
  // user there after the action. Only allow same-origin (this sister domain).
  let effectiveReturnUrl = returnUrl || "";
  if (effectiveReturnUrl && !isAllowedReturnUrl(effectiveReturnUrl)) {
    // Silently drop suspicious returnUrl rather than redirecting to it.
    effectiveReturnUrl = "";
  }
  if (!effectiveReturnUrl && typeof window !== "undefined") {
    effectiveReturnUrl = window.location.href;
  }
  if (effectiveReturnUrl && isAllowedReturnUrl(effectiveReturnUrl)) {
    const sep = url.includes("?") ? "&" : "?";
    url = `${url}${sep}return_url=${encodeURIComponent(effectiveReturnUrl)}`;
  }
  if (typeof window !== "undefined") {
    window.location.href = url;
  }
}

/**
 * FIX L-8 helper: returnUrl is safe to use only if it points at this sister
 * domain (config.thisDomainUrl) or is a relative path. Anything else is
 * treated as an open-redirect attempt and dropped.
 */
function isAllowedReturnUrl(target: string): boolean {
  if (typeof window === "undefined") return false;
  if (!target) return false;
  // Relative paths starting with "/" (but not "//" which is protocol-relative)
  if (target.startsWith("/") && !target.startsWith("//")) return true;
  try {
    const parsed = new URL(target);
    const allowed = new URL(config.thisDomainUrl);
    return parsed.origin === allowed.origin;
  } catch {
    // Unparseable URL — reject.
    return false;
  }
}

/**
 * Generate an auth code and redirect to the base domain with it.
 *
 * This is the SSO flow: the sister domain generates a one-time code
 * from its JWT, then redirects to the base domain's callback page.
 * The base domain exchanges the code for its own tokens.
 *
 * @param targetPath - Where on the base domain to redirect after code exchange
 *                     (e.g. '/dashboard/billing')
 */
export async function redirectToBaseWithAuthCode(
  targetPath: string,
): Promise<void> {
  try {
    const { code } = await generateAuthCode();
    const callbackUrl = `${config.baseDomainUrl}/auth/callback`;
    const params = new URLSearchParams({
      code,
      return_to: targetPath,
    });
    if (typeof window !== "undefined") {
      window.location.href = `${callbackUrl}?${params.toString()}`;
    }
  } catch (err) {
    // If auth code generation fails, fall back to simple redirect
    console.error("Failed to generate auth code:", err);
    redirectToBase(targetPath);
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Check if user is authenticated (has a token).
 */
export function checkAuth(): boolean {
  return authHelpers.isAuthenticated();
}

/**
 * Redirect to login if not authenticated.
 */
export function requireAuth(): boolean {
  if (!checkAuth()) {
    if (typeof window !== "undefined") {
      // Redirect to the dedicated /login page (MPA refactor).
      window.location.href = "/login";
    }
    return false;
  }
  return true;
}

/**
 * Check for existing session on base domain and establish one here.
 *
 * This enables cross-domain session sharing: if the user is logged in
 * on the base domain (SattaBase), they can get a session on this sister
 * domain without re-entering credentials.
 *
 * Call this on the login page if the user has no local session.
 * It redirects to base domain's /auth/authorize-sister endpoint which
 * will redirect back with an auth code if authenticated.
 */
export function checkBaseDomainSession(): void {
  if (typeof window === "undefined") return;

  // Don't redirect if we already have a token
  if (checkAuth()) return;

  // Redirect to base domain's sister auth check
  // Base domain will redirect back with auth code if session exists
  const callbackUrl = `${config.thisDomainUrl}/auth/callback`;
  const targetUrl = `${config.baseDomainUrl}/auth/sso-check`;

  window.location.href = `${targetUrl}?redirect_uri=${encodeURIComponent(callbackUrl)}`;
}

/**
 * Format API error message for display.
 */
export function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    return (error as ApiError).message || "An unexpected error occurred.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred. Please try again.";
}
