/**
 * POST /api/auth/logout — Dealer auth logout proxy.
 *
 * Astro server endpoint that forwards the dealer's refresh cookie to
 * Sattabase (POST /auth/logout) so the backend can blacklist the
 * refresh token (AUTH-2: logout is CSRF-protected — backend requires
 * a valid refresh cookie), then propagates the backend's clearing
 * Set-Cookie headers (max_age=0) onto the dealerfrontend origin so
 * the browser drops the cookie.
 *
 * Flow:
 *   1. Read sb_refresh_token cookie from incoming request
 *   2. POST to ${SATTABASE_API_BASE_URL}/auth/logout with the cookie
 *   3. Forward the backend's Set-Cookie headers (clearing) onto the
 *      Astro response
 *   4. Return 204 on success, 401 if no cookie (caller is unauthenticated)
 *
 * If Sattabase is unreachable, we still attempt to clear the cookie
 * locally by setting sb_refresh_token to empty + max_age=0.
 */
import type { APIRoute } from "astro";
import config from "../../../../sattabase.config";

export const prerender = false;

// Must match the backend cookie name (backend/users/controllers.py:98).
const REFRESH_TOKEN_COOKIE_NAME = "sb_refresh_token";
const REMEMBER_ME_COOKIE_NAME = "sb_remember_me";

/**
 * Audit fix H7: CSRF guard. Rejects any POST whose Origin or Referer
 * header is not the dealerfrontend origin. Prevents logout-CSRF attacks
 * (where an attacker logs the victim out by cross-site POSTing).
 */
function rejectCrossOriginPost(request: Request): Response | null {
  const origin = request.headers.get("origin");
  const referer = request.headers.get("referer");
  const allowed = new Set<string>([config.thisDomainUrl]);
  if (import.meta.env.DEV) {
    try {
      const u = new URL(config.thisDomainUrl);
      allowed.add(`http://${u.host}`);
      allowed.add(`https://${u.host}`);
      allowed.add("http://localhost:4323");
      allowed.add("http://127.0.0.1:4323");
    } catch {
      /* ignore */
    }
  }
  if (origin) {
    return allowed.has(origin)
      ? null
      : new Response(
          JSON.stringify({ detail: "Cross-origin requests are not allowed" }),
          { status: 403, headers: { "Content-Type": "application/json" } },
        );
  }
  if (referer) {
    try {
      const r = new URL(referer);
      return allowed.has(`${r.protocol}//${r.host}`)
        ? null
        : new Response(
            JSON.stringify({ detail: "Cross-origin requests are not allowed" }),
            { status: 403, headers: { "Content-Type": "application/json" } },
          );
    } catch {
      return new Response(
        JSON.stringify({ detail: "Malformed Referer header" }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      );
    }
  }
  return new Response(
    JSON.stringify({ detail: "Missing Origin/Referer header" }),
    { status: 403, headers: { "Content-Type": "application/json" } },
  );
}

/** Split a collapsed fetch() Set-Cookie header back into individual cookies. */
function splitSetCookies(combined: string | null): string[] {
  if (!combined) return [];
  return combined
    .split(/,(?=\s*[A-Za-z0-9_-]+=)/g)
    .map((c) => c.trim())
    .filter(Boolean);
}

export const POST: APIRoute = async ({ request, cookies }) => {
  // ── Audit fix H7: CSRF check ────────────────────────────────────────────
  const csrf = rejectCrossOriginPost(request);
  if (csrf) return csrf;

  const refreshCookie = cookies.get(REFRESH_TOKEN_COOKIE_NAME)?.value;

  // No cookie → nothing to log out; return 401 so caller can redirect.
  if (!refreshCookie) {
    return new Response(JSON.stringify({ detail: "No active session" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── Forward to Sattabase so it can blacklist the refresh token ────────
  // The backend validates the cookie before blacklisting (AUTH-2 fix);
  // we must forward it verbatim.
  let backendRes: Response;
  try {
    backendRes = await fetch(`${config.apiBaseUrl}/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Forward the refresh cookie to the backend so it can identify
        // the session and add the token to the blacklist.
        Cookie: `${REFRESH_TOKEN_COOKIE_NAME}=${refreshCookie}`,
      },
    });
  } catch {
    // Sattabase unreachable — fall through to clearing the cookie locally
    // so the browser at least forgets the session, even if the server-side
    // blacklist is missed. The token will still expire naturally.
    backendRes = new Response(null, { status: 204 });
  }

  // ── Build response ────────────────────────────────────────────────────
  const responseHeaders = new Headers();

  // Forward backend's clearing Set-Cookie headers (max_age=0 entries).
  // These bind to the dealerfrontend origin (4323) because the response
  // is being served by Astro at 4323 — the browser will replace the
  // existing cookie with an expired one.
  const setCookieCombined = backendRes.headers.get("set-cookie");
  for (const cookie of splitSetCookies(setCookieCombined)) {
    responseHeaders.append("set-cookie", cookie);
  }

  // Defensive: if the backend didn't send clearing headers (e.g. it was
  // unreachable), still clear the cookie locally so the user is logged
  // out at the browser level.
  if (!setCookieCombined) {
    responseHeaders.append(
      "set-cookie",
      `${REFRESH_TOKEN_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly`,
    );
    responseHeaders.append(
      "set-cookie",
      `${REMEMBER_ME_COOKIE_NAME}=; Path=/; Max-Age=0`,
    );
  }

  return new Response(null, {
    status: 204,
    headers: responseHeaders,
  });
};
