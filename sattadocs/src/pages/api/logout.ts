/**
 * POST /api/logout
 *
 * Clears the staff session cookie.
 */

import type { APIRoute } from "astro";
import { STAFF_SESSION_COOKIE, buildClearCookie } from "../../lib/auth";

export const POST: APIRoute = async ({ request }) => {
  const cookieHeader = request.headers.get("Cookie") || "";
  const cookies = parseCookies(cookieHeader);
  const token = cookies[STAFF_SESSION_COOKIE];

  // Optionally blacklist the token on the backend
  if (token) {
    try {
      const isDev = import.meta.env.DEV;
      // Use runtime environment variable for production
      const envUrl =
        process.env.SERVER_API_BASE_URL || process.env.PUBLIC_API_BASE_URL_SB;
      const backendUrl = isDev
        ? "http://localhost:8086/api/v1"
        : envUrl || "http://sb-backend:8086/api/v1";

      // We don't have the refresh token, so we can't fully blacklist,
      // but clearing the cookie is sufficient since the access token
      // has a short TTL (60 minutes).
      // If needed, we could store the refresh token in a separate cookie
      // and blacklist it here.
    } catch {
      // Continue with cookie cleanup even if backend call fails
    }
  }

  // Clear the session cookie
  return new Response(
    JSON.stringify({ success: true, message: "Logged out successfully." }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": buildClearCookie(),
      },
    },
  );
};

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
