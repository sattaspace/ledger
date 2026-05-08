/**
 * Astro middleware — protects /dev_docs/* routes for staff users only.
 *
 * This middleware intercepts every incoming request before it reaches the
 * Starlight page renderer. For routes under `/dev_docs/`, it:
 *
 *   1. Reads the JWT from the `sattadocs_staff_session` cookie
 *   2. Validates the token against the Sattabase backend (GET /users/me)
 *   3. Checks that `is_staff === true`
 *
 * - If valid staff -> passes through to the page (calls next())
 * - If missing/invalid -> redirects to /dev-docs-login with a redirect
 *   query parameter so the user lands back on their original page after login
 *
 * Non-dev_docs routes are unaffected and pass through immediately.
 */

import type { MiddlewareHandler } from "astro";
import { STAFF_SESSION_COOKIE, validateStaffToken } from "./lib/auth";

export const onRequest: MiddlewareHandler = async (context, next) => {
  const url = new URL(context.request.url);
  const pathname = url.pathname;

  // Only guard /dev_docs/* routes
  if (!pathname.startsWith("/dev_docs")) {
    return next();
  }

  // Skip Astro internals (pagefind, etc.)
  if (pathname.startsWith("/dev_docs/__")) {
    return next();
  }

  // Read JWT from cookie
  const cookieHeader = context.request.headers.get("Cookie") || "";
  const cookies = parseCookies(cookieHeader);
  const token = cookies[STAFF_SESSION_COOKIE];

  if (!token) {
    return redirect(context, url);
  }

  // Validate token against Sattabase backend
  const staffUser = await validateStaffToken(token);

  if (!staffUser) {
    return redirect(context, url);
  }

  // Valid staff — attach user info and continue
  context.locals.staffUser = staffUser;
  return next();
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/**
 * Redirect to the dev-docs login page, preserving the original URL
 * so the user can be sent back after authenticating.
 */
function redirect(
  context: Parameters<MiddlewareHandler>[0],
  url: URL,
): Response {
  const loginUrl = new URL("/dev-docs-login", url.origin);
  loginUrl.searchParams.set("redirect", url.pathname + url.search);
  return context.redirect(loginUrl.toString());
}

/**
 * Parse a raw Cookie header into a key-value map.
 */
function parseCookies(header: string): Record<string, string> {
  const cookies: Record<string, string> = {};
  for (const pair of header.split(";")) {
    const trimmed = pair.trim();
    const eqIndex = trimmed.indexOf("=");
    if (eqIndex > 0) {
      const key = trimmed.slice(0, eqIndex).trim();
      const value = trimmed.slice(eqIndex + 1).trim();
      cookies[key] = value;
    }
  }
  return cookies;
}

// ─── Augment Astro.locals ────────────────────────────────────────────────────

declare global {
  namespace App {
    interface Locals {
      staffUser?: {
        id: number;
        email: string;
        full_name: string;
        display_name: string;
        is_staff: boolean;
        is_email_verified: boolean;
      } | null;
    }
  }
}
