/**
 * Auth utilities — authentication functions for the Sattabase sister domain.
 *
 * Sister domains only have LOGIN and LOGOUT screens. Everything else
 * (register, forgot password, reset, verify, profile, billing) redirects
 * to the Sattabase base domain.
 */

import { apiClient, authHelpers, clearTokens } from "./api";
import type { ApiError, AuthMeResponse, TokenPair, AuthorizeResponse } from "./types";
import config from "../../sattabase.config";

// ─── Login ───────────────────────────────────────────────────────────────────

export async function login(email: string, password: string, remember = false): Promise<TokenPair> {
  const data = await apiClient.post<TokenPair>("/auth/login", {
    email,
    password,
    remember,
  });
  authHelpers.setTokens(data.access, data.refresh, remember);
  return data;
}

// ─── Logout ──────────────────────────────────────────────────────────────────

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

export async function getAuthMe(): Promise<AuthMeResponse> {
  return apiClient.get<AuthMeResponse>("/billing/auth/me");
}

// ─── Authorization Code (SSO) ────────────────────────────────────────────────

export async function generateAuthCode(): Promise<AuthorizeResponse> {
  return apiClient.post<AuthorizeResponse>("/auth/authorize");
}

export async function exchangeAuthCode(code: string): Promise<TokenPair> {
  const data = await apiClient.post<TokenPair>("/auth/token/exchange", {
    code,
  });
  authHelpers.setTokens(data.access, data.refresh);
  return data;
}

// ─── Redirect to Base Domain ─────────────────────────────────────────────────

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

export async function redirectToBaseWithAuthCode(targetPath: string): Promise<void> {
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
    console.error("Failed to generate auth code:", err);
    redirectToBase(targetPath);
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

export function checkAuth(): boolean {
  return authHelpers.isAuthenticated();
}

export function requireAuth(): boolean {
  if (!checkAuth()) {
    if (typeof window !== "undefined") {
      window.location.href = "/auth/login";
    }
    return false;
  }
  return true;
}

export function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    return (error as ApiError).message || "An unexpected error occurred.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred. Please try again.";
}
