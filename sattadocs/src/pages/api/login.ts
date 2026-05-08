/**
 * POST /api/login
 *
 * Authenticates a staff user against the Sattabase backend.
 * On success, sets the `sattadocs_staff_session` cookie and returns user info.
 * On failure, returns a 401 error with a descriptive message.
 */

import type { APIRoute } from "astro";
import { loginWithCredentials, buildSessionCookie } from "../../lib/auth";

export const POST: APIRoute = async ({ request }) => {
  let body: { email?: string; password?: string };

  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid request body." }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const { email, password } = body;

  if (!email || !password) {
    return new Response(
      JSON.stringify({ error: "Email and password are required." }),
      { status: 400, headers: { "Content-Type": "application/json" } },
    );
  }

  const result = await loginWithCredentials(email.trim(), password);

  if ("error" in result) {
    return new Response(JSON.stringify({ error: result.error }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Set the session cookie (HttpOnly, secure in production)
  const cookieValue = buildSessionCookie(result.accessToken);

  return new Response(
    JSON.stringify({
      success: true,
      user: {
        email: result.user.email,
        name: result.user.display_name,
      },
    }),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Set-Cookie": cookieValue,
      },
    },
  );
};
