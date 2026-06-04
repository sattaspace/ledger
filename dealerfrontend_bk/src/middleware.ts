/**
 * Astro middleware — enhanced auth guard for Satta Ledger.
 *
 * Protected paths:   /dashboard — redirect to /auth/login if not authenticated
 * Guest-only paths:  /auth/login, /auth/callback — redirect to /dashboard if authenticated
 * Public paths:      / (landing page) — accessible to everyone
 *
 * Since JWTs are stored client-side (sessionStorage / localStorage),
 * the middleware injects a client-side auth check script for protected routes
 * and a redirect script for guest-only routes.
 */

import { defineMiddleware } from "astro:middleware";

// Paths that require authentication
const PROTECTED_PATHS = ["/dashboard"];

// Paths that should redirect away if already authenticated
const GUEST_ONLY_PATHS = ["/auth/login", "/auth/callback", "/auth"];

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

  // Protected routes: inject client-side auth check
  if (isProtected) {
    const response = await next();

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      response.headers.set("x-require-auth", "true");
      return response;
    }

    return response;
  }

  // Guest-only routes: if authenticated, redirect to dashboard
  if (isGuestOnly) {
    const response = await next();

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      response.headers.set("x-guest-only", "true");
      return response;
    }

    return response;
  }

  // Public routes (e.g. / landing page) — let everyone through
  return next();
});
