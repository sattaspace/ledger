/**
 * Astro Server Middleware — Dealer Auth Guard
 *
 * Runs on every server-side request before the page is rendered.
 *
 * Layer 1 of the auth defense (per SattaBase sister-domain pattern):
 * validates the sb_refresh_token httpOnly cookie by calling Sattabase
 * POST /auth/token/refresh-cookie. If valid, the dealer is authenticated
 * and we forward any rotated refresh cookie back to the browser. If
 * invalid or missing, we redirect to /login (preserving the intended
 * destination as ?redirect=).
 *
 * Routes that BYPASS this middleware entirely:
 *   - /api/*         (auth proxy endpoints set their own cookies)
 *   - /_astro/*      (Astro internal assets)
 *   - /login         (the login page itself — must not loop)
 *   - /dsr/*         (DSR has its own auth flow via localStorage + SPA guard)
 *   - Static assets (anything with a file extension)
 *
 * Auth state propagation to client:
 *   - Astro.locals.isAuthenticated = true on success
 *   - Astro.locals.accessToken = the fresh access token from refresh-cookie
 *   - BaseLayout reads these and embeds them as window.__auth for Vue islands
 */
import { defineMiddleware } from "astro:middleware";
import config from "../sattabase.config";

// ─── Constants ──────────────────────────────────────────────────────────────

/** Must match the backend cookie name (backend/users/controllers.py:98). */
const REFRESH_TOKEN_COOKIE_NAME = "sb_refresh_token";

// Routes that the middleware never touches.
const PUBLIC_PREFIXES = ["/api/", "/_astro/", "/dsr/"];
const PUBLIC_EXACT = new Set([
  "/login",
  "/favicon.ico",
  "/robots.txt",
]);

function isPublic(pathname: string): boolean {
  if (PUBLIC_EXACT.has(pathname)) return true;
  if (PUBLIC_PREFIXES.some((p) => pathname.startsWith(p))) return true;
  // Static assets (anything with an extension in the last path segment)
  const last = pathname.split("/").pop() || "";
  if (last.includes(".")) return true;
  return false;
}

/** Split a collapsed fetch() Set-Cookie header back into individual cookies. */
function splitSetCookies(combined: string | null): string[] {
  if (!combined) return [];
  return combined
    .split(/,(?=\s*[A-Za-z0-9_-]+=)/g)
    .map((c) => c.trim())
    .filter(Boolean);
}

/** Append all Set-Cookie values from a fetch Response onto another Response. */
function forwardSetCookies(from: Response, to: Response): void {
  const combined = from.headers.get("set-cookie");
  for (const cookie of splitSetCookies(combined)) {
    to.headers.append("set-cookie", cookie);
  }
}

// ─── Middleware ─────────────────────────────────────────────────────────────

export const onRequest = defineMiddleware(async (context, next) => {
  const { url, cookies, locals, redirect } = context;
  const pathname = url.pathname;

  // Bypass for public / unauthenticated routes.
  if (isPublic(pathname)) {
    return next();
  }

  // Read the httpOnly refresh cookie (set by /api/auth/login).
  const refreshToken = cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value;

  if (!refreshToken) {
    // No cookie → not authenticated. Redirect to /login with redirect param.
    return redirect(
      `/login?redirect=${encodeURIComponent(pathname + url.search)}`,
      302,
    );
  }

  // Validate the cookie by calling Sattabase's cookie-based refresh
  // endpoint. This rotates the refresh token on success (per
  // backend _set_auth_cookie + refresh-cookie controller).
  let backendRes: Response;
  try {
    backendRes = await fetch(`${config.apiBaseUrl}/auth/token/refresh-cookie`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Forward the refresh cookie to the backend (cookies aren't
        // auto-forwarded by Node fetch; we set it manually).
        Cookie: `${REFRESH_TOKEN_COOKIE_NAME}=${refreshToken}`,
      },
      // Sattabase's refresh-cookie endpoint declares an empty
      // CookieRefreshInputSchema, so Django Ninja rejects requests
      // with no body. Send an empty JSON object to satisfy the
      // schema validator. The actual refresh token is read from the
      // cookie header above, not from the body.
      body: "{}",
    });
  } catch {
    // Sattabase unreachable — treat as unauthenticated.
    return redirect(
      `/login?redirect=${encodeURIComponent(pathname + url.search)}`,
      302,
    );
  }

  if (!backendRes.ok) {
    // Cookie expired / blacklisted / invalid → unauthenticated.
    return redirect(
      `/login?redirect=${encodeURIComponent(pathname + url.search)}`,
      302,
    );
  }

  // Parse the access token from the refresh-cookie response body.
  let accessToken: string | undefined;
  try {
    const body = await backendRes.clone().json();
    accessToken = body?.access;
  } catch {
    /* malformed response */
  }

  if (!accessToken) {
    return redirect(
      `/login?redirect=${encodeURIComponent(pathname + url.search)}`,
      302,
    );
  }

  // Make auth state available to pages (BaseLayout embeds it for Vue).
  locals.isAuthenticated = true;
  locals.accessToken = accessToken;

  // Render the page, then forward any rotated refresh cookie onto the
  // browser response. Cookie rotation happens on every successful refresh
  // (per backend controllers.py:539-571).
  const response = await next();
  forwardSetCookies(backendRes, response);
  return response;
});
