/**
 * Server-side authentication utilities for sattadocs.
 *
 * Validates JWT tokens against the Sattabase Django Ninja backend
 * and checks whether the authenticated user has staff privileges.
 *
 * All functions are server-side only (Node.js runtime).
 */

// ─── Configuration ──────────────────────────────────────────────────────────

/** Read the backend URL from environment (set via astro.config.mjs). */
function getBackendUrl(): string {
  // import.meta.env.DEV is true during 'npm run dev'
  if (import.meta.env.DEV) {
    return "http://localhost:8000/api/v1";
  }

  // Otherwise, return the environment variable (or the fallback)
  return (
    import.meta.env.PUBLIC_API_BASE_URL_SB || "http://localhost:8000/api/v1"
  );
}

/** Cookie name used to persist the staff session JWT. */
export const STAFF_SESSION_COOKIE = "sattadocs_staff_session";

/** Cookie max-age: 7 days in seconds. */
const COOKIE_MAX_AGE = 7 * 24 * 60 * 60;

// ─── Types ──────────────────────────────────────────────────────────────────

export interface StaffUser {
  id: number;
  email: string;
  full_name: string;
  display_name: string;
  is_staff: boolean;
  is_email_verified: boolean;
}

interface LoginResponse {
  access: string;
  refresh: string;
}

interface UserMeResponse {
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
  is_staff: boolean;
  role: string;
  created_at: string | null;
  full_name: string;
  display_name: string;
}

// ─── Core functions ─────────────────────────────────────────────────────────

/**
 * Validate a JWT access token against the Sattabase backend.
 *
 * Calls `GET /api/v1/users/me` with the Bearer token.
 * Returns the user object if the token is valid and the user is staff.
 * Returns `null` if the token is invalid, expired, or the user is not staff.
 */
export async function validateStaffToken(
  token: string,
): Promise<StaffUser | null> {
  const baseUrl = getBackendUrl();

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10_000);

    let response: Response;
    try {
      response = await fetch(`${baseUrl}/users/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    if (!response.ok) {
      // Token invalid, expired, or user inactive/deleted
      return null;
    }

    const user: UserMeResponse = await response.json();

    // Only staff users are allowed to access dev_docs
    if (!user.is_staff) {
      return null;
    }

    return {
      id: user.id,
      email: user.email,
      full_name: user.full_name,
      display_name: user.display_name,
      is_staff: user.is_staff,
      is_email_verified: user.is_email_verified,
    };
  } catch {
    // Network error or timeout — fail closed
    return null;
  }
}

/**
 * Authenticate with email and password against the Sattabase backend.
 *
 * Calls `POST /api/v1/auth/login` with credentials.
 * Then calls `GET /api/v1/users/me` to verify the user is staff.
 * Returns `{ user, accessToken }` on success.
 * Returns `{ error: string }` on failure.
 */
export async function loginWithCredentials(
  email: string,
  password: string,
): Promise<{ user: StaffUser; accessToken: string } | { error: string }> {
  const baseUrl = getBackendUrl();

  try {
    // Step 1: Login to get tokens
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10_000);

    let loginResponse: Response;
    try {
      loginResponse = await fetch(`${baseUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    if (!loginResponse.ok) {
      const body = await loginResponse.json().catch(() => ({}));
      const message =
        body?.detail ||
        body?.message ||
        "Invalid email or password. Please try again.";
      return { error: message };
    }

    const tokens: LoginResponse = await loginResponse.json();

    // Step 2: Verify the user is staff
    const staffUser = await validateStaffToken(tokens.access);
    if (!staffUser) {
      return {
        error:
          "Access denied. Dev docs are only available to staff members. Please contact your administrator if you believe this is an error.",
      };
    }

    return { user: staffUser, accessToken: tokens.access };
  } catch {
    return {
      error:
        "Unable to connect to the authentication server. Please try again later.",
    };
  }
}

/**
 * Build the Set-Cookie header value for the staff session.
 *
 * The cookie stores only the access token (short-lived JWT).
 * In production, `secure` and `sameSite` should be enforced.
 */
export function buildSessionCookie(
  accessToken: string,
  options?: { isProduction?: boolean },
): string {
  const prod = options?.isProduction ?? isProduction();

  const parts = [
    `${STAFF_SESSION_COOKIE}=${accessToken}`,
    `Max-Age=${COOKIE_MAX_AGE}`,
    "Path=/",
    "HttpOnly",
  ];

  if (prod) {
    parts.push("Secure");
    parts.push("SameSite=Lax");
  }

  return parts.join("; ");
}

/**
 * Build the Set-Cookie header value to clear the staff session.
 */
export function buildClearCookie(): string {
  return `${STAFF_SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly${
    isProduction() ? "; Secure; SameSite=Lax" : ""
  }`;
}

/**
 * Check if we're running in production.
 */
function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}
