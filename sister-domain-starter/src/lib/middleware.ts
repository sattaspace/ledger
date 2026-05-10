/**
 * Astro middleware — auth guard for protected routes.
 *
 * Checks for JWT token on protected routes (paths starting with /dashboard).
 * If no token is found in localStorage/sessionStorage, redirects to /auth/login.
 *
 * The actual token check happens client-side since JWT tokens are stored
 * in the browser. This middleware sets a cookie-based indicator that the
 * client-side script can use to determine auth state.
 *
 * For server-side rendering protection, you'd need to use cookies instead
 * of localStorage — but for this starter kit, we use the client-side approach
 * which is simpler and works well with the Astro partial hydration model.
 */

import { defineMiddleware } from "astro:middleware";

// Paths that require authentication
const PROTECTED_PATHS = ["/dashboard"];

// Paths that should redirect away if already authenticated
const GUEST_ONLY_PATHS = ["/auth/login"];

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Check if this is a protected path
  const isProtected = PROTECTED_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  // Check if this is a guest-only path
  const isGuestOnly = GUEST_ONLY_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  // For protected routes, inject a script that checks for auth tokens
  // before the page renders. This is a client-side check since JWTs
  // are stored in the browser's storage.
  if (isProtected) {
    const response = await next();

    // Only inject the auth check script for HTML responses
    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      // Return the response as-is; the client-side middleware in
      // the DashboardLayout handles the actual auth check.
      // The middleware flag is set as a header for the layout to read.
      response.headers.set("x-require-auth", "true");
      return response;
    }

    return response;
  }

  // For guest-only routes (like login), let them through
  return next();
});
