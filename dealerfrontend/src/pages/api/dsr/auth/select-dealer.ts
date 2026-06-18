/**
 * POST /api/dsr/auth/select-dealer — DSR select-dealer proxy.
 *
 * When a DSR has multiple dealer assignments, they pick one. The backend
 * returns a fresh access + refresh JWT scoped to that dealer. We strip the
 * refresh token from the body and rotate the httpOnly cookie, mirroring
 * the login proxy.
 *
 * Security:
 *   - CSRF: rejectCrossOriginPost validates Origin/Referer (audit H7).
 *   - Requires the caller to be authenticated (their httpOnly cookie is
 *     sent automatically with credentials: 'include'). We also forward
 *     the access token from the request body to the backend via
 *     Authorization header — the backend validates it to confirm the DSR
 *     identity.
 */
import type { APIRoute } from "astro";
import {
  buildRefreshCookie,
  dsrApiBase,
  rejectCrossOriginPost,
} from "./_helpers";

export const prerender = false;

const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

interface SelectDealerBody {
  dealer_username?: string;
  access_token?: string; // optional, forwarded to backend as Bearer
}

export const POST: APIRoute = async (context) => {
  // ── CSRF check ────────────────────────────────────────────────────────
  const csrf = rejectCrossOriginPost(context);
  if (csrf) return csrf;

  let body: SelectDealerBody;
  try {
    body = (await context.request.json()) as SelectDealerBody;
  } catch {
    return new Response(JSON.stringify({ detail: "Invalid JSON body" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  if (!body.dealer_username) {
    return new Response(
      JSON.stringify({ detail: "dealer_username is required" }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  // ── Forward to dealerbackend ──────────────────────────────────────────
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (body.access_token) {
    headers["Authorization"] = `Bearer ${body.access_token}`;
  }

  let backendRes: Response;
  try {
    backendRes = await fetch(`${dsrApiBase()}/dsr/auth/select-dealer`, {
      method: "POST",
      headers,
      body: JSON.stringify({ dealer_username: body.dealer_username }),
    });
  } catch {
    return new Response(
      JSON.stringify({ detail: "Dealer service unreachable" }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }

  const responseBodyText = await backendRes.text();
  const contentType = backendRes.headers.get("content-type") || "";

  if (!backendRes.ok) {
    return new Response(responseBodyText, {
      status: backendRes.status,
      headers: { "Content-Type": contentType || "application/json" },
    });
  }

  let data: {
    access?: string;
    refresh?: string;
    dealer?: unknown;
    permissions?: unknown;
    dealer_access?: unknown;
    effective_access?: unknown;
    message?: string;
  };
  try {
    data = JSON.parse(responseBodyText);
  } catch {
    return new Response(responseBodyText, {
      status: backendRes.status,
      headers: { "Content-Type": contentType || "application/json" },
    });
  }

  const refresh = data.refresh;
  const responseHeaders = new Headers({
    "Content-Type": "application/json",
  });

  if (refresh) {
    responseHeaders.append(
      "set-cookie",
      buildRefreshCookie(refresh, REFRESH_MAX_AGE),
    );
  }

  // Strip refresh from the body before returning to the client.
  const safeBody = { ...data, refresh: "" };

  return new Response(JSON.stringify(safeBody), {
    status: backendRes.status,
    headers: responseHeaders,
  });
};
