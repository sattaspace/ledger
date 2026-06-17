/**
 * POST /api/auth/login — Dealer auth login proxy.
 *
 * Astro server endpoint that forwards credentials to Sattabase
 * (POST /auth/login) and propagates the Set-Cookie headers
 * (sb_refresh_token, sb_remember_me) onto the dealerfrontend origin
 * (port 4323). Returns the backend's JSON body (access token) to the
 * client.
 *
 * Why a server proxy?
 *   Sattabase (8086) and dealerfrontend (4323) are cross-origin. If the
 *   browser calls Sattabase directly, the httpOnly cookie lands on 8086
 *   and the dealerfrontend middleware (which runs on 4323) never sees it.
 *   By proxying through Astro at 4323, the Set-Cookie response from
 *   Sattabase reaches the browser as if it came from 4323 — so the cookie
 *   is bound to the dealerfrontend origin and the middleware can read it.
 *
 * Flow:
 *   1. Read { email, password, remember? } from request body
 *   2. POST to ${SATTABASE_API_BASE_URL}/auth/login
 *   3. On success: forward Set-Cookie headers verbatim, return JSON body
 *      (access token) as-is
 *   4. On backend error: forward status code + JSON error body, do NOT
 *      forward any Set-Cookie headers
 */
import type { APIRoute } from "astro";
import config from "../../../../sattabase.config";

export const prerender = false;

interface LoginBody {
  email?: string;
  password?: string;
  remember?: boolean;
}

/**
 * Parse the backend's Set-Cookie header and return each Set-Cookie value
 * as a separate string. The fetch API collapses multi-value headers
 * (e.g. multiple Set-Cookie entries) into a single comma-separated
 * string — we must re-split on the actual cookie boundary to preserve
 * them when forwarding.
 */
function splitSetCookies(combined: string | null): string[] {
  if (!combined) return [];
  // Each Set-Cookie starts with name=value and ends before the next
  // "name=value" pair (which begins with a non-whitespace char).
  // Strategy: split on commas that are followed by a non-whitespace
  // letter/digit and an "=" (typical cookie name pattern).
  return combined
    .split(/,(?=\s*[A-Za-z0-9_-]+=)/g)
    .map((c) => c.trim())
    .filter(Boolean);
}

export const POST: APIRoute = async ({ request }) => {
  // ── 1. Parse request body ─────────────────────────────────────────────
  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return new Response(
      JSON.stringify({ detail: "Invalid JSON body" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  const { email, password, remember } = body;
  if (!email || !password) {
    return new Response(
      JSON.stringify({ detail: "Email and password are required" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  // ── 2. Forward to Sattabase ───────────────────────────────────────────
  let backendRes: Response;
  try {
    backendRes = await fetch(`${config.apiBaseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, remember: !!remember }),
      // Don't forward the browser's cookies to the backend automatically —
      // the login endpoint must not require a prior cookie, and the
      // backend will set the new cookie in its response.
    });
  } catch (err) {
    // Network failure reaching Sattabase
    return new Response(
      JSON.stringify({ detail: "Authentication service unreachable" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  // ── 3. Build response, forwarding Set-Cookie headers ──────────────────
  const responseHeaders = new Headers();

  // Forward content-type from backend (or default)
  const backendContentType = backendRes.headers.get("content-type");
  responseHeaders.set(
    "Content-Type",
    backendContentType || "application/json",
  );

  // Forward Set-Cookie headers verbatim. Multiple Set-Cookie entries are
  // collapsed by fetch() into a single comma-separated string — split
  // them back out so the browser sees each cookie individually.
  const setCookieCombined = backendRes.headers.get("set-cookie");
  const setCookies = splitSetCookies(setCookieCombined);
  for (const cookie of setCookies) {
    responseHeaders.append("set-cookie", cookie);
  }

  // Read body once (so we can attach it to either success or error path)
  const responseBody = await backendRes.text();

  return new Response(responseBody, {
    status: backendRes.status,
    headers: responseHeaders,
  });
};
