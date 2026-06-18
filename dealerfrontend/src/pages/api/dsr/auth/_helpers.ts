/**
 * DSR auth proxy helpers — shared utilities for /api/dsr/auth/* endpoints.
 *
 * The dealerfrontend talks to the dealerbackend (port 8088) directly for
 * business data, but for DSR authentication we proxy through Astro at 4323
 * so we can:
 *
 *   1. Strip the long-lived refresh token from the JSON response body and
 *      re-issue it as an httpOnly, Secure, SameSite=Lax cookie bound to the
 *      dealerfrontend origin. This prevents XSS from reading it.
 *   2. Forward the cookie on logout/refresh so the dealerbackend's existing
 *      cookie-reading blacklist logic works (it previously read a cookie
 *      that the frontend never set — see audit C2).
 *   3. Validate the `Origin` header on every POST to defeat CSRF (audit H7).
 */

import type { APIContext } from "astro";
import config from "../../../../../sattabase.config";

/** Cookie name — must match the name the dealerbackend reads. */
export const DSR_REFRESH_COOKIE_NAME = "dsr_refresh_token";

/** HttpOnly cookie attributes we apply to every Set-Cookie. */
const COOKIE_ATTRS = [
  "Path=/",
  "HttpOnly",
  "SameSite=Lax",
  // Secure is added only when config.thisDomainUrl is https.
];

function isHttps(url: string): boolean {
  return /^https:\/\//i.test(url);
}

/**
 * Build a Set-Cookie value for the DSR refresh token.
 *
 * @param token  - the refresh JWT (or empty string to clear)
 * @param maxAge - Max-Age in seconds; 0 deletes the cookie
 */
export function buildRefreshCookie(token: string, maxAge: number): string {
  const parts = [
    `${DSR_REFRESH_COOKIE_NAME}=${token}`,
    ...COOKIE_ATTRS,
    `Max-Age=${maxAge}`,
  ];
  if (isHttps(config.thisDomainUrl)) parts.push("Secure");
  return parts.join("; ");
}

/**
 * Resolve the dealerbackend API base URL. Mirrors the logic in
 * services/dsrClient.ts so server and client agree on the same target.
 */
export function dsrApiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const env =
    typeof import.meta !== "undefined" && (import.meta as any).env
      ? (import.meta as any).env
      : {};
  return (
    env.PUBLIC_DEALER_API_URL ||
    env.VITE_API_BASE_URL ||
    config.dealerApiBaseUrl ||
    "http://localhost:8088/api"
  );
}

/**
 * CSRF guard: reject any cross-origin POST.
 *
 * On the dealerfrontend origin, fetch() from the same origin automatically
 * sends the `Origin` header; a CSRF attack from evil.com will send a
 * different `Origin`. We compare against the configured thisDomainUrl
 * (which is the canonical origin of this deployment).
 *
 * Returns `null` if OK, or a 403 `Response` if the origin is rejected.
 *
 * Audit fix (diagnostic): in dev mode, be lenient — accept any origin
 * that uses the same port as config.thisDomainUrl. This handles the
 * common dev scenario of accessing via 127.0.0.1, localhost, or a LAN
 * IP instead of the exact configured thisDomainUrl. In production,
 * only the exact thisDomainUrl (and its https variant) are accepted.
 */
export function rejectCrossOriginPost(context: APIContext): Response | null {
  const request = context.request;
  const origin = request.headers.get("origin");
  const referer = request.headers.get("referer");

  const allowedOrigins = new Set<string>([config.thisDomainUrl]);

  // Parse the configured thisDomainUrl to extract the port.
  let configuredPort: string | null = null;
  let configuredHost: string | null = null;
  try {
    const u = new URL(config.thisDomainUrl);
    configuredPort = u.port || (u.protocol === "https:" ? "443" : "80");
    configuredHost = u.hostname;
  } catch {
    /* ignore */
  }

  if (import.meta.env.DEV) {
    // In dev, accept any origin on the same port (localhost, 127.0.0.1, LAN IP, etc.)
    if (configuredPort) {
      allowedOrigins.add(`http://localhost:${configuredPort}`);
      allowedOrigins.add(`http://127.0.0.1:${configuredPort}`);
      allowedOrigins.add(`https://localhost:${configuredPort}`);
      allowedOrigins.add(`https://127.0.0.1:${configuredPort}`);
    }
    // Also accept the bare host variants
    if (configuredHost) {
      allowedOrigins.add(`http://${configuredHost}`);
      allowedOrigins.add(`https://${configuredHost}`);
    }
  }

  // Helper: check if an origin matches any allowed origin, OR (in dev)
  // if it uses the same port.
  function isAllowedOrigin(testOrigin: string): boolean {
    if (allowedOrigins.has(testOrigin)) return true;
    // In dev, also accept any origin with the same port
    if (import.meta.env.DEV && configuredPort) {
      try {
        const u = new URL(testOrigin);
        const testPort = u.port || (u.protocol === "https:" ? "443" : "80");
        if (testPort === configuredPort) return true;
      } catch {
        /* malformed origin */
      }
    }
    return false;
  }

  if (origin) {
    if (isAllowedOrigin(origin)) return null;
    return new Response(
      JSON.stringify({
        detail: "Cross-origin requests are not allowed",
        origin,
        allowed: Array.from(allowedOrigins),
      }),
      { status: 403, headers: { "Content-Type": "application/json" } },
    );
  }

  // Fallback: check Referer if Origin is missing.
  if (referer) {
    try {
      const r = new URL(referer);
      const refererOrigin = `${r.protocol}//${r.host}`;
      if (isAllowedOrigin(refererOrigin)) return null;
      return new Response(
        JSON.stringify({
          detail: "Cross-origin requests are not allowed",
          refererOrigin,
          allowed: Array.from(allowedOrigins),
        }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      );
    } catch {
      return new Response(
        JSON.stringify({ detail: "Malformed Referer header" }),
        { status: 403, headers: { "Content-Type": "application/json" } },
      );
    }
  }

  // Neither header present — be conservative and reject.
  return new Response(
    JSON.stringify({
      detail: "Missing Origin/Referer header — cannot verify same-origin",
    }),
    { status: 403, headers: { "Content-Type": "application/json" } },
  );
}

/**
 * Split a collapsed fetch() Set-Cookie header back into individual cookies.
 * Same logic as the dealer-side proxy in pages/api/auth/login.ts.
 */
export function splitSetCookies(combined: string | null): string[] {
  if (!combined) return [];
  return combined
    .split(/,(?=\s*[A-Za-z0-9_-]+=)/g)
    .map((c) => c.trim())
    .filter(Boolean);
}
