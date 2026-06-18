/**
 * POST /api/dsr/auth/login — DSR auth login proxy.
 *
 * Mirrors the dealer-side /api/auth/login pattern (audit fix C1+C2).
 *
 * Flow:
 *   1. Read { email, password } from request body
 *   2. POST to ${DSR_API_BASE}/dsr/auth/login on the dealerbackend
 *   3. On success: strip `refresh` from the JSON body and re-issue it as an
 *      httpOnly, Secure, SameSite=Lax cookie on the dealerfrontend origin.
 *      Return the rest of the JSON body (access token, user, dealers) to
 *      the client.
 *   4. On backend error: forward status + JSON error body, do NOT set any
 *      cookie.
 *
 * Why a server proxy?
 *   The dealerbackend (8088) and dealerfrontend (4323) are cross-origin.
 *   If the browser called 8088 directly, the httpOnly cookie would land on
 *   8088 and our subsequent /api/dsr/auth/refresh-cookie call (which lives
 *   on 4323) would never see it. By proxying through Astro, the cookie is
 *   bound to 4323 and our refresh-cookie endpoint can read it.
 *
 * Security:
 *   - CSRF: rejectCrossOriginPost validates Origin/Referer (audit H7).
 *   - XSS: the refresh token never enters JavaScript; it's in an httpOnly
 *     cookie that the browser sends automatically on subsequent /api/dsr/*
 *     requests (credentials: 'include').
 *   - The short-lived access token (~5 min default) IS returned in the JSON
 *     body — it lives in JavaScript memory only, mirroring the dealer-side
 *     pattern (lib/api.ts:_accessToken).
 */
import type { APIRoute } from "astro";
import {
  buildRefreshCookie,
  dsrApiBase,
  rejectCrossOriginPost,
} from "./_helpers";

export const prerender = false;

interface LoginBody {
  email?: string;
  password?: string;
}

interface DsrLoginResponse {
  access: string;
  refresh: string;
  user: unknown;
  dealers: unknown[];
  require_dealer_selection?: boolean;
  awaiting_invitation?: boolean;
  message?: string;
}

// Default refresh-token cookie Max-Age in seconds. Matches ninja_jwt's
// default ROTATE_REFRESH_TOKEN lifetime of 7 days.
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

export const POST: APIRoute = async (context) => {
  // ── CSRF check ────────────────────────────────────────────────────────
  const csrf = rejectCrossOriginPost(context);
  if (csrf) return csrf;

  // ── 1. Parse request body ─────────────────────────────────────────────
  let body: LoginBody;
  try {
    body = (await context.request.json()) as LoginBody;
  } catch {
    return new Response(JSON.stringify({ detail: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { email, password } = body;
  if (!email || !password) {
    return new Response(
      JSON.stringify({ detail: "Email and password are required" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  // ── 2. Forward to dealerbackend ───────────────────────────────────────
  let backendRes: Response;
  try {
    backendRes = await fetch(`${dsrApiBase()}/dsr/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
  } catch {
    return new Response(
      JSON.stringify({ detail: "Authentication service unreachable" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  const contentType = backendRes.headers.get("content-type") || "";
  const responseBodyText = await backendRes.text();

  // ── 3. On failure, forward the error body verbatim ────────────────────
  if (!backendRes.ok) {
    return new Response(responseBodyText, {
      status: backendRes.status,
      headers: { "Content-Type": contentType || "application/json" },
    });
  }

  // ── 4. On success: strip refresh from body, set httpOnly cookie ───────
  let data: DsrLoginResponse;
  try {
    data = JSON.parse(responseBodyText) as DsrLoginResponse;
  } catch {
    // Malformed success response — pass through as-is, no cookie
    return new Response(responseBodyText, {
      status: backendRes.status,
      headers: { "Content-Type": contentType || "application/json" },
    });
  }

  const refresh = data.refresh;
  if (!refresh) {
    // No refresh token in response — return as-is.
    // Diagnostic: log what the backend actually returned so we can see
    // why the refresh field is missing.
    console.warn("[DSR LOGIN PROXY] Backend response has no 'refresh' field", {
      hasAccess: !!data.access,
      hasUser: !!data.user,
      responseKeys: Object.keys(data),
      responseBodyPreview: responseBodyText.substring(0, 200),
    });
    return new Response(JSON.stringify(data), {
      status: backendRes.status,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Diagnostic: log the refresh token length (NOT the token itself) so
  // we can verify it's a valid JWT (typically 150-400 chars, 3 dot-separated parts).
  console.log("[DSR LOGIN PROXY] Setting refresh cookie", {
    refreshLength: refresh.length,
    refreshParts: refresh.split(".").length, // should be 3 for a JWT
    refreshPreview: refresh.substring(0, 20) + "...",
  });

  // Strip the refresh token from the body before returning to the client.
  const safeBody: DsrLoginResponse = { ...data, refresh: "" };

  const responseHeaders = new Headers({
    "Content-Type": "application/json",
  });
  const cookieStr = buildRefreshCookie(refresh, REFRESH_MAX_AGE);
  console.log("[DSR LOGIN PROXY] Set-Cookie header", {
    cookieLength: cookieStr.length,
    cookiePreview: cookieStr.substring(0, 50) + "...",
  });
  responseHeaders.append("set-cookie", cookieStr);

  return new Response(JSON.stringify(safeBody), {
    status: backendRes.status,
    headers: responseHeaders,
  });
};
