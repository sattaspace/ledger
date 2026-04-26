/**
 * Auth utilities — provides helper functions for authentication state
 * management across Vue components (client-side only).
 *
 * Uses localStorage for JWT tokens.
 */

import { authHelpers, apiClient } from "./api";
import type { ApiError } from "./api";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface UserProfile {
  id: number;
  slug: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  timezone: string;
  currency: string;
  language: string;
  is_email_verified: boolean;
  role: string;
  avatar: string | null;
  created_at: string;
  full_name: string;
  display_name: string;
}

// ─── Auth functions ─────────────────────────────────────────────────────────

/**
 * Login — POST /auth/login → store tokens
 */
export async function login(payload: LoginPayload): Promise<AuthTokens> {
  const data = await apiClient.post<AuthTokens>("/auth/login", payload);
  authHelpers.setTokens(data.access, data.refresh);
  return data;
}

/**
 * Register — POST /auth/register
 */
export async function register(payload: RegisterPayload): Promise<void> {
  await apiClient.post("/auth/register", payload);
}

/**
 * Logout — clear tokens and redirect
 */
export async function logout(): Promise<void> {
  try {
    await apiClient.post("/auth/logout");
  } catch {
    // Even if the API call fails, clear local tokens
  }
  authHelpers.clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/auth/login";
  }
}

/**
 * Request password reset email — POST /auth/password-reset/request
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post("/auth/password-reset/request", { email });
}

/**
 * Confirm password reset — POST /auth/password-reset/confirm
 */
export async function confirmPasswordReset(
  token: string,
  new_password: string,
): Promise<void> {
  await apiClient.post("/auth/password-reset/confirm", {
    token,
    new_password,
  });
}

/**
 * Change password (requires current password) — POST /users/me/change-password
 */
export async function changePassword(
  current_password: string,
  new_password: string,
  confirm_password: string,
): Promise<void> {
  await apiClient.post("/users/me/change-password", {
    current_password,
    new_password,
    confirm_password,
  });
}

/**
 * Request email change — POST /users/me/change-email
 * Sends a 6-digit OTP to the current email.
 */
export async function requestEmailChange(
  current_password: string,
  new_email: string,
): Promise<void> {
  await apiClient.post("/users/me/change-email", {
    current_password,
    new_email,
  });
}

/**
 * Confirm email change with OTP — POST /users/me/change-email/confirm
 */
export async function confirmEmailChangeOTP(otp: string): Promise<string> {
  const res = await apiClient.post<{ message: string; success: boolean }>(
    "/users/me/change-email/confirm",
    { otp },
  );
  return res.message;
}

/**
 * Request email verification — POST /auth/verify-email/request
 */
export async function requestEmailVerification(email: string): Promise<void> {
  await apiClient.post("/auth/verify-email/request", { email });
}

/**
 * Verify email with OTP — POST /auth/verify-email/confirm
 */
export async function verifyEmail(email: string, otp: string): Promise<void> {
  await apiClient.post("/auth/verify-email/confirm", { email, otp });
}

/**
 * Delete account — POST /users/me/delete-account
 */
export async function deleteAccount(current_password: string): Promise<void> {
  await apiClient.post("/users/me/delete-account", { current_password });
}

/**
 * Get current user profile — GET /users/me
 */
export async function getCurrentUser(): Promise<UserProfile> {
  return apiClient.get<UserProfile>("/users/me");
}

/**
 * Update user profile — PUT /users/me
 */
export async function updateProfile(
  data: Partial<Pick<UserProfile, "first_name" | "last_name" | "phone" | "timezone" | "currency" | "language">>,
): Promise<UserProfile> {
  return apiClient.put<UserProfile>("/users/me", data);
}

// ─── Convenience ────────────────────────────────────────────────────────────

/**
 * Check if user is authenticated (has a non-expired access token).
 * Note: This only checks localStorage — it doesn't validate the token with the server.
 */
export function isAuthenticated(): boolean {
  return authHelpers.isAuthenticated();
}

/**
 * Redirect to login if not authenticated.
 */
export function requireAuth(): boolean {
  if (!isAuthenticated()) {
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
