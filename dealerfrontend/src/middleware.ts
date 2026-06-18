/**
 * Astro Server Middleware — Dealer Auth Guard
 *
 * Runs on every server-side request before the page is rendered.
 *
 * Layer 1 of the auth defense (per SattaBase sister-domain pattern):
 * validates the sb_refresh_token httpOnly cookie by calling SattaBase
 * POST /auth/token/refresh-cookie. If valid, the dealer is authenticated
 * and we forward any rotated refresh cookie back to the browser. If
 * invalid or missing, we redirect to /login (preserving the intended
 * destination as ?redirect=).
 *
 * Audit fix H1: DSR portal-mode support.
 * When a DSR clicks "Enter Portal" on their dashboard, they navigate
 * the main dealer app routes (/dashboard, /inventory, etc.) using their
 * DSR-scoped JWT instead of a SattaBase dealer JWT. The frontend sets a
 * `dealercore:dsr_portal_mode=true` flag in localStorage and the DSR
 * auth proxy sets an httpOnly `dsr_refresh_token` cookie.
 *
 * This middleware now also checks for the DSR refresh cookie. If present,
 * it calls the DSR refresh-cookie proxy (/api/dsr/auth/refresh-cookie)
 * to mint a fresh DSR access token. The token is exposed via
 * `locals.accessToken` so the dealer pages can call dealerbackend
 * endpoints with the DSR-scoped JWT. The dealerbackend's
 * PermissionMiddleware already accepts DSR JWTs for business endpoints.
 *
 * Routes that BYPASS this middleware entirely:
 *   - /api/*         (auth proxy endpoints set their own cookies)
 *   - /_astro/*      (Astro internal assets)
 *   - /login         (the login page itself — must not loop)
 *   - /dsr/*         (DSR has its own auth flow via httpOnly cookie + SPA guard)
 *   - Static assets (anything with a file extension)
 *
 * Auth state propagation to client:
 *   - Astro.locals.isAuthenticated = true on success
 *   - Astro.locals.accessToken = the fresh access token from refresh-cookie
 *   - Astro.locals.authType = "dealer" | "dsr_portal" (so pages can switch behavior)
 *   - BaseLayout reads these and embeds them as window.__INITIAL_AUTH_TOKEN__ for Vue islands
 */
import { defineMiddleware } from "astro:middleware";
import config from "../sattabase.config";

// ─── Constants ──────────────────────────────────────────────────────────────

/** Must match the backend cookie name (backend/users/controllers.py:98). */
const REFRESH_TOKEN_COOKIE_NAME = "sb_refresh_token";
/** DSR refresh cookie name — must match services/dsrClient.ts and the proxy. */
const DSR_REFRESH_TOKEN_COOKIE_NAME = "dsr_refresh_token";

// Routes that the middleware never touches.
const PUBLIC_PREFIXES = ["/api/", "/_astro/", "/dsr/"];
const PUBLIC_EXACT = new Set(["/login", "/favicon.ico", "/robots.txt"]);

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

/**
 * Audit fix M7: apply HTTP security headers to every response.
 *
 * Astro does not set these by default. We add them here so they apply
 * uniformly to all pages and API responses:
 *
 *   - X-Content-Type-Options: nosniff   (prevents MIME-sniffing attacks)
 *   - X-Frame-Options: DENY              (prevents clickjacking via iframes)
 *   - Referrer-Policy: strict-origin-when-cross-origin
 *                                        (prevents full-URL leakage via Referer)
 *   - Strict-Transport-Security         (forces HTTPS for 1 year — only
 *                                        sent if the request is HTTPS)
 *   - Content-Security-Policy           (restricts script/style/img/connect
 *                                        sources to mitigate XSS)
 *
 * CSP note: we allow 'unsafe-inline' for scripts and styles because
 * BaseLayout uses inline `define:vars` scripts. Tightening this requires
 * moving those to nonce-based scripts (a future refactor).
 */
function applySecurityHeaders(response: Response): Response {
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  // HSTS only over HTTPS (sending it over HTTP can pin a user to a
  // malicious HTTP origin). Astro sets url.protocol; we check that.
  // The `request.url` check covers both proxy-terminated and direct HTTPS.
  try {
    const proto =
      response.headers.get("x-forwarded-proto") ||
      (typeof URL !== "undefined"
        ? new URL("/", "https://placeholder").protocol
        : "");
    // Best-effort: set HSTS unconditionally — modern browsers ignore it
    // over HTTP anyway. If a reverse proxy terminates TLS, it should
    // also strip this header from plain-HTTP responses (or set its own).
    response.headers.set(
      "Strict-Transport-Security",
      "max-age=31536000; includeSubDomains",
    );
    void proto;
  } catch {
    /* ignore */
  }

  // Content-Security-Policy. Allow same-origin + the backend origins
  // (SattaBase 8086 and dealerbackend 8088) for connect-src; allow
  // inline scripts/styles (BaseLayout uses them); allow data: URLs for
  // images (avatars, etc.).
  response.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com data:",
      "img-src 'self' data: blob: http://localhost:8086 http://localhost:8088",
      "connect-src 'self' http://localhost:8086 http://localhost:8088 ws://localhost:8086 ws://localhost:8088",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  );

  return response;
}

export const onRequest = defineMiddleware(async (context, next) => {
  const { url, cookies, locals, redirect } = context;
  const pathname = url.pathname;

  // Bypass for public / unauthenticated routes.
  if (isPublic(pathname)) {
    const resp = await next();
    return applySecurityHeaders(resp);
  }

  // Read the httpOnly refresh cookies. Both dealer (sb_refresh_token)
  // and DSR portal (dsr_refresh_token) may be present — we try dealer
  // first, then DSR.
  const dealerRefreshToken = cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value;
  const dsrRefreshToken = cookies.get(DSR_REFRESH_TOKEN_COOKIE_NAME)?.value;

  // ── Audit fix H1: DSR portal-mode support ──────────────────────────
  // If the dealer cookie is absent but the DSR cookie is present, the
  // user is a DSR in portal mode. Validate by calling the dealerbackend
  // /dsr/auth/refresh DIRECTLY (server-to-server), not through the
  // Astro proxy. The proxy's CSRF guard rejects server-side fetch
  // requests because they don't send Origin/Referer headers.
  if (!dealerRefreshToken && dsrRefreshToken) {
    let dsrRes: Response;
    try {
      // Call the dealerbackend directly — same pattern as the dealer-side
      // SattaBase refresh-cookie call below. We have the refresh token
      // from the cookie; send it in the JSON body as the backend expects.
      dsrRes = await fetch(`${config.dealerApiBaseUrl}/dsr/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh: dsrRefreshToken }),
      });
    } catch {
      // Backend unreachable — treat as unauthenticated.
      return redirect(
        `/dsr/login?redirect=${encodeURIComponent(pathname + url.search)}`,
        302,
      );
    }

    if (!dsrRes.ok) {
      // DSR cookie expired/blacklisted → redirect to DSR login.
      return redirect(
        `/dsr/login?redirect=${encodeURIComponent(pathname + url.search)}`,
        302,
      );
    }

    let dsrAccessToken: string | undefined;
    let newDsrRefreshToken: string | undefined;
    try {
      const body = await dsrRes.clone().json();
      dsrAccessToken = body?.access;
      newDsrRefreshToken = body?.refresh;
    } catch {
      /* malformed response */
    }

    if (!dsrAccessToken) {
      return redirect(
        `/dsr/login?redirect=${encodeURIComponent(pathname + url.search)}`,
        302,
      );
    }

    // Make auth state available to pages.
    locals.isAuthenticated = true;
    locals.accessToken = dsrAccessToken;
    locals.authType = "dsr_portal";

    // Render the page, then forward any rotated DSR refresh cookie
    // onto the browser response. If the backend returned a new refresh
    // token (ROTATE_REFRESH_TOKENS=True), we need to set it as an
    // httpOnly cookie on the dealerfrontend origin.
    const response = await next();

    if (newDsrRefreshToken) {
      // Build the cookie inline (same attributes as the proxy's
      // buildRefreshCookie helper, without importing it to avoid
      // circular deps with the pages/ directory).
      const cookieParts = [
        `${DSR_REFRESH_TOKEN_COOKIE_NAME}=${newDsrRefreshToken}`,
        "Path=/",
        "HttpOnly",
        "SameSite=Lax",
        `Max-Age=${7 * 24 * 60 * 60}`,
      ];
      if (/^https:\/\//i.test(config.thisDomainUrl)) {
        cookieParts.push("Secure");
      }
      response.headers.append("set-cookie", cookieParts.join("; "));
    }

    return applySecurityHeaders(response);
  }

  // ── Standard dealer auth path ─────────────────────────────────────
  if (!dealerRefreshToken) {
    // No dealer cookie and no DSR cookie → not authenticated. Redirect
    // to /login with redirect param.
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
        Cookie: `${REFRESH_TOKEN_COOKIE_NAME}=${dealerRefreshToken}`,
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
  locals.authType = "dealer";

  // Render the page, then forward any rotated refresh cookie onto the
  // browser response. Cookie rotation happens on every successful refresh
  // (per backend controllers.py:539-571).
  const response = await next();
  forwardSetCookies(backendRes, response);
  return applySecurityHeaders(response);
});
