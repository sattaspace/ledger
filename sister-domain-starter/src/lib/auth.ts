/**
 * Auth utilities — authentication functions for the Sattabase sister domain.
 *
 * Sister domains only have LOGIN and LOGOUT screens. Everything else
 * (register, forgot password, reset, verify, profile, billing) redirects
 * to the Sattabase base domain.
 *
 * The Token Pass-Through (authorization code) flow enables seamless SSO:
 *   1. User clicks "Manage Subscription" on sister domain
 *   2. Sister domain calls POST /auth/authorize → gets one-time code
 *   3. Sister domain redirects to base domain's callback with ?code=XXX
 *   4. Base domain exchanges code for tokens, stores them, redirects to target page
 */

import { apiClient, authHelpers, clearTokens } from "./api";
import type {
  ApiError,
  AuthMeResponse,
  TokenPair,
  AuthorizeResponse,
} from "./types";
import config from "../../sattabase.config";

// ─── Login ───────────────────────────────────────────────────────────────────

/**
 * Login — POST /auth/login → store tokens
 *
 * @param email - User email address
 * @param password - User password
 * @param remember - If true, tokens persist in localStorage (30 days).
 *                   If false/omitted, tokens use sessionStorage (tab-only).
 */
export async function login(
  email: string,
  password: string,
  remember = false,
): Promise<TokenPair> {
  const data = await apiClient.post<TokenPair>("/auth/login", {
    email,
    password,
    remember,
  });
  authHelpers.setTokens(data.access, data.refresh, remember);
  return data;
}

// ─── Logout ──────────────────────────────────────────────────────────────────

/**
 * Logout — blacklist refresh token + clear local tokens
 *
 * Blacklists the refresh token server-side before clearing local state.
 * If blacklisting fails (network error, etc.) we still clear locally.
 */
export async function logout(): Promise<void> {
  try {
    const refreshToken = authHelpers.getRefreshToken();
    if (refreshToken) {
      await apiClient.post("/auth/token/blacklist", { refresh: refreshToken });
    }
  } catch {
    // Continue with local cleanup even if blacklist fails
  }
  try {
    await apiClient.post("/users/me/logout");
  } catch {
    // Even if the API call fails, clear local tokens
  }
  authHelpers.clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/auth/login";
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
  authHelpers.setTokens(data.access, data.refresh);
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
  const effectiveReturnUrl =
    returnUrl || (typeof window !== "undefined" ? window.location.href : "");
  if (effectiveReturnUrl) {
    const sep = url.includes("?") ? "&" : "?";
    url = `${url}${sep}return_url=${encodeURIComponent(effectiveReturnUrl)}`;
  }
  if (typeof window !== "undefined") {
    window.location.href = url;
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
      window.location.href = "/auth/login";
    }
    return false;
  }
  return true;
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
