/**
 * POST /api/dsr/auth/logout — DSR auth logout proxy.
 *
 * Mirrors the dealer-side /api/auth/logout pattern (audit fix C2).
 *
 * Flow:
 *   1. Read the dsr_refresh_token httpOnly cookie from the incoming request.
 *   2. POST to ${DSR_API_BASE}/dsr/auth/logout on the dealerbackend, with
 *      the refresh token forwarded as a cookie header. The backend's
 *      existing logout handler reads this cookie and blacklists the token
 *      (previously this never worked because the frontend stored the token
 *      in localStorage — see audit C2).
 *   3. Always return a 204 + a Set-Cookie that clears the dsr_refresh_token
 *      cookie from the browser.
 *
 * Security:
 *   - CSRF: rejectCrossOriginPost validates Origin/Referer.
 *   - If the backend is unreachable, we still clear the cookie locally so
 *     the browser forgets the session, but the token remains valid
 *     server-side until natural expiry (acceptable graceful degradation).
 */
import type { APIRoute } from "astro";
import {
  DSR_REFRESH_COOKIE_NAME,
  buildRefreshCookie,
  dsrApiBase,
  rejectCrossOriginPost,
} from "./_helpers";

export const prerender = false;

export const POST: APIRoute = async (context) => {
  // ── CSRF check ────────────────────────────────────────────────────────
  const csrf = rejectCrossOriginPost(context);
  if (csrf) return csrf;

  const refreshCookie = context.cookies.get(DSR_REFRESH_COOKIE_NAME)?.value;

  // No cookie → nothing to log out server-side; still clear the cookie
  // locally and return 204 so the client treats it as a success.
  if (refreshCookie) {
    try {
      // Forward to dealerbackend so it can blacklist the refresh token.
      // We forward the cookie manually because Node fetch doesn't
      // auto-forward browser cookies.
      await fetch(`${dsrApiBase()}/dsr/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: `${DSR_REFRESH_COOKIE_NAME}=${refreshCookie}`,
        },
      });
    } catch {
      // Backend unreachable — fall through to clearing the cookie locally.
      // The token will still expire naturally (7 days default).
    }
  }

  // Always clear the cookie on the browser, regardless of backend outcome.
  const responseHeaders = new Headers();
  responseHeaders.append("set-cookie", buildRefreshCookie("", 0));

  return new Response(null, {
    status: 204,
    headers: responseHeaders,
  });
};
