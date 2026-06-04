/**
 * Astro Middleware — Server-side route protection for protected pages.
 *
 * AUTH-5 FIX: Previously a no-op — all protected HTML was sent to the browser
 * even when the user had no session. This meant:
 * 1. Unauthenticated users could see the full page structure (layout, nav, etc.)
 *    before the client-side redirect kicked in
 * 2. Search engines could index protected pages
 * 3. The page flash between "logged in" and "redirect to login" was visible
 *
 * Now, the middleware checks for the refresh token cookie on protected routes.
 * If no cookie is present, there's no possible session — redirect immediately
 * on the server side. This provides:
 * - Zero-flash redirect (server returns 302, browser navigates directly)
 * - No wasted server resources rendering pages for unauthenticated users
 * - Protection against search engine indexing of protected pages
 *
 * IMPORTANT: This is a BEST-EFFORT check, not a complete solution:
 * - A cookie existing doesn't guarantee the token inside is valid
 * - Token validation still happens client-side + backend API enforcement
 * - The middleware only catches the "no cookie at all" case
 *
 * For admin pages, we additionally make a server-side API call to /users/me
 * to verify staff status. This prevents non-staff users from ever seeing
 * admin page HTML.
 */
import { defineMiddleware } from "astro:middleware";

// ─── Route definitions ─────────────────────────────────────────────────────

// Paths that require authentication (any logged-in user).
// Prefix matching means "/dashboard" covers ALL sub-routes:
//   /dashboard, /dashboard/profile, /dashboard/settings,
//   /dashboard/billing/*, /dashboard/credits/*, etc.
// "/admin" covers all admin sub-routes EXCEPT /admin/django (see exclusion below).
const PROTECTED_PREFIXES = ["/dashboard", "/admin", "/settings", "/profile"];

// Paths that require admin (staff) access — these get an additional
// server-side staff verification check via /users/me
const ADMIN_PATH_PREFIX = "/admin";
// Exclude the Django admin from our guard (it has its own auth)
const DJANGO_ADMIN_PATH = "/admin/django";

// Cookie names — must match backend's cookie names
const REFRESH_TOKEN_COOKIE = "sb_refresh_token";
const REMEMBER_ME_COOKIE = "sb_remember_me";

// Backend API URL for server-side token validation
// AUTH-11 FIX: Use the same dev/prod logic as api.ts so the middleware
// validates against the correct backend. Previously, the middleware fell
// through to the production URL when SERVER_API_BASE_URL_SB was not set,
// which caused admin route validation to always fail in development
// (the refresh token cookie was issued by localhost:8086, not the
// production API).
const isDev = import.meta.env.DEV;
const API_BASE_URL = isDev
  ? "http://localhost:8086/api/v1"
  : process.env.SERVER_API_BASE_URL_SB ||
    process.env.PUBLIC_API_BASE_URL_SB ||
    "https://baseapi.sattaspace.com/api/v1";

// ─── Helper ────────────────────────────────────────────────────────────────

function isProtectedPath(pathname: string): boolean {
  // Exclude Django admin from our guard — it has its own auth system
  if (pathname.startsWith(DJANGO_ADMIN_PATH)) return false;
  // Any path starting with a protected prefix requires authentication
  return PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
}

function isAdminPath(pathname: string): boolean {
  return (
    pathname.startsWith(ADMIN_PATH_PREFIX) &&
    !pathname.startsWith(DJANGO_ADMIN_PATH)
  );
}

/**
 * Attempt to validate a refresh token cookie against the backend API.
 * Returns { valid: true, isStaff: boolean } or { valid: false }.
 *
 * Uses the cookie-based refresh endpoint to check if the token is valid.
 * This is a lightweight check — we only need to know if the token works,
 * not actually use the new access token.
 */
async function validateRefreshCookie(
  refreshToken: string,
  rememberMe: boolean,
): Promise<{ valid: boolean; isStaff?: boolean; userId?: number }> {
  try {
    // First, try to get an access token via cookie refresh.
    // IMPORTANT: This is a server-side fetch (Astro middleware runs on the
    // server), so `credentials: "include"` won't forward the browser's cookies.
    // We must explicitly set the Cookie header with the refresh token (and
    // remember_me flag) so the backend can read them from request.COOKIES.
    const cookieParts = [`${REFRESH_TOKEN_COOKIE}=${refreshToken}`];
    if (rememberMe) {
      cookieParts.push(`${REMEMBER_ME_COOKIE}=true`);
    }
    const refreshResponse = await fetch(
      `${API_BASE_URL}/auth/token/refresh-cookie`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: cookieParts.join("; "),
        },
        body: JSON.stringify({}),
      },
    );

    if (!refreshResponse.ok) {
      return { valid: false };
    }

    const refreshData = await refreshResponse.json();
    if (!refreshData.access) {
      return { valid: false };
    }

    // SIDE EFFECT NOTE: The backend's refresh-cookie endpoint rotates the
    // refresh token and sets a new cookie in the response. Since this is a
    // server-side fetch, that Set-Cookie header goes to our fetch response,
    // NOT to the browser. The browser still has the old refresh token cookie.
    // This is safe because the backend intentionally does NOT blacklist the
    // old token (to support concurrent tabs). However, each middleware
    // validation call does create an orphaned refresh token in the DB that
    // will expire after 7 days. A future optimization would be to add a
    // dedicated /auth/token/validate endpoint that doesn't rotate.

    // For admin routes, validate staff status via /users/me
    // This uses the freshly obtained access token
    const meResponse = await fetch(`${API_BASE_URL}/users/me`, {
      headers: { Authorization: `Bearer ${refreshData.access}` },
    });

    if (!meResponse.ok) {
      return { valid: true }; // Token works, just can't verify staff
    }

    const userData = await meResponse.json();
    return {
      valid: true,
      isStaff: userData.is_staff || userData.is_superuser || false,
      userId: userData.id,
    };
  } catch {
    // Network error — can't validate. Let the request through and
    // rely on client-side checks. Don't block on server-side failures.
    return { valid: true }; // Assume valid, let client handle it
  }
}

// ─── Middleware ─────────────────────────────────────────────────────────────

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Only guard protected paths
  if (!isProtectedPath(pathname)) {
    return next();
  }

  // Check if the refresh token cookie exists
  const cookies = context.cookies;
  const refreshToken = cookies.get(REFRESH_TOKEN_COOKIE)?.value;
  const rememberMe = cookies.get(REMEMBER_ME_COOKIE)?.value === "true";

  // ── No refresh cookie at all → no possible session → redirect immediately ──
  //
  // This is the most important check. Without a refresh cookie, there is
  // absolutely no way the user can have a valid session on this page.
  // Redirecting server-side avoids:
  // 1. Rendering the full page just to redirect client-side
  // 2. The "flash of protected content" before client-side redirect
  // 3. Wasting server resources on rendering for unauthenticated users
  if (!refreshToken) {
    // For API/AJAX requests, return 401 instead of redirecting
    const acceptHeader = context.request.headers.get("accept") || "";
    if (acceptHeader.includes("application/json")) {
      return new Response(
        JSON.stringify({ detail: "Authentication required." }),
        {
          status: 401,
          headers: { "Content-Type": "application/json" },
        },
      );
    }

    // For page requests, redirect to login
    const loginUrl = new URL("/auth/login", context.url);
    loginUrl.searchParams.set("redirect", pathname);
    return context.redirect(loginUrl.toString(), 302);
  }

  // ── Admin routes: additional staff check ─────────────────────────────────
  //
  // For admin pages, we also verify the user has staff privileges.
  // This prevents non-staff users from ever seeing admin page HTML.
  // The check is done server-side by calling the backend API with the
  // refresh cookie. If the API call fails or the user is not staff,
  // redirect to the dashboard.
  if (isAdminPath(pathname)) {
    const result = await validateRefreshCookie(refreshToken, rememberMe);

    if (!result.valid) {
      // Cookie exists but token is invalid — redirect to login
      const loginUrl = new URL("/auth/login", context.url);
      loginUrl.searchParams.set("redirect", pathname);
      return context.redirect(loginUrl.toString(), 302);
    }

    if (result.valid && result.isStaff === false) {
      // User is authenticated but not staff — redirect to dashboard
      return context.redirect("/dashboard", 302);
    }

    // If we couldn't verify staff status (network error), let the request
    // through and rely on client-side checks. This avoids blocking admin
    // access due to temporary backend issues.
  }

  // ── Protected routes with valid cookie → proceed ─────────────────────────
  //
  // The cookie exists (and for admin, staff status is verified or
  // verification failed gracefully). Let the request through.
  // Client-side checks will handle edge cases (expired tokens, etc.).
  return next();
});
