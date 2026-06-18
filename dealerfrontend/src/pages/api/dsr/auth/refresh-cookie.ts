/**
 * POST /api/dsr/auth/refresh-cookie — DSR refresh-token-via-cookie endpoint.
 *
 * Mirrors the dealer-side /auth/token/refresh-cookie pattern. This is the
 * server-side endpoint that the Astro middleware (and the dsrClient
 * refresh interceptor) call to mint a fresh access token using the
 * httpOnly refresh cookie, without ever exposing the refresh token to
 * JavaScript.
 *
 * Flow:
 *   1. Read the dsr_refresh_token httpOnly cookie.
 *   2. If absent → 401 (no session).
 *   3. POST to ${DSR_API_BASE}/dsr/auth/refresh on the dealerbackend with
 *      { refresh: <token> } in the JSON body.
 *   4. On success: rotate the httpOnly cookie if the backend returned a new
 *      refresh token, and return { access } in the JSON body.
 *   5. On 401 from backend → 401 (cookie expired/revoked); clear the cookie.
 *
 * Security:
 *   - CSRF: rejectCrossOriginPost validates Origin/Referer (audit H7).
 *   - The refresh token never appears in the response body; it's in the
 *     httpOnly cookie only.
 */
import type { APIRoute } from "astro";
import {
  DSR_REFRESH_COOKIE_NAME,
  buildRefreshCookie,
  dsrApiBase,
  rejectCrossOriginPost,
} from "./_helpers";

export const prerender = false;

const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

export const POST: APIRoute = async (context) => {
  // ── CSRF check ────────────────────────────────────────────────────────
  const csrf = rejectCrossOriginPost(context);
  if (csrf) return csrf;

  const refreshCookie = context.cookies.get(DSR_REFRESH_COOKIE_NAME)?.value;

  // Diagnostic: log what we got from the cookie
  console.log("[DSR REFRESH PROXY] Cookie check", {
    hasCookie: !!refreshCookie,
    cookieLength: refreshCookie?.length || 0,
    cookieParts: refreshCookie ? refreshCookie.split(".").length : 0, // should be 3 for JWT
    cookiePreview: refreshCookie
      ? refreshCookie.substring(0, 20) + "..."
      : "(none)",
  });

  if (!refreshCookie) {
    return new Response(JSON.stringify({ detail: "No active DSR session" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── Forward to dealerbackend /dsr/auth/refresh ────────────────────────
  const requestBody = JSON.stringify({ refresh: refreshCookie });
  console.log("[DSR REFRESH PROXY] Forwarding to backend", {
    bodyLength: requestBody.length,
    bodyPreview: requestBody.substring(0, 40) + "...",
  });

  let backendRes: Response;
  try {
    backendRes = await fetch(`${dsrApiBase()}/dsr/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: requestBody,
    });
  } catch (err) {
    console.error("[DSR REFRESH PROXY] Backend unreachable:", err);
    return new Response(
      JSON.stringify({ detail: "Authentication service unreachable" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  // Diagnostic: log the backend response
  const backendBody = await backendRes.text();
  console.log("[DSR REFRESH PROXY] Backend response", {
    status: backendRes.status,
    statusText: backendRes.statusText,
    bodyPreview: backendBody.substring(0, 200),
  });

  // Backend rejected the refresh token (expired/blacklisted) → clear cookie,
  // return 401.
  if (!backendRes.ok) {
    const responseHeaders = new Headers({
      "Content-Type": "application/json",
    });
    responseHeaders.append("set-cookie", buildRefreshCookie("", 0));
    return new Response(backendBody, {
      status: backendRes.status,
      headers: responseHeaders,
    });
  }

  // ── Parse response: { access, refresh? } ──────────────────────────────
  let data: { access?: string; refresh?: string };
  try {
    data = JSON.parse(backendBody);
  } catch {
    return new Response(
      JSON.stringify({ detail: "Malformed refresh response" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  if (!data.access) {
    return new Response(
      JSON.stringify({ detail: "No access token in refresh response" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  const responseHeaders = new Headers({
    "Content-Type": "application/json",
  });

  // If the backend rotated the refresh token, update the cookie.
  // ninja_jwt's default is to keep the same refresh token (no rotation),
  // but if rotation is enabled we honour the new value.
  if (data.refresh) {
    responseHeaders.append(
      "set-cookie",
      buildRefreshCookie(data.refresh, REFRESH_MAX_AGE),
    );
  }

  // Return ONLY the access token in the body. The refresh token stays in
  // the httpOnly cookie.
  return new Response(JSON.stringify({ access: data.access }), {
    status: 200,
    headers: responseHeaders,
  });
};
