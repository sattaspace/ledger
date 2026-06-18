/// <reference types="astro/client" />

/**
 * Extend Astro's Locals type with auth state populated by src/middleware.ts.
 *
 * The middleware validates the sb_refresh_token cookie on every protected
 * page request and, on success, populates:
 *   - locals.isAuthenticated: true
 *   - locals.accessToken: the fresh JWT access token from /auth/token/refresh-cookie
 *   - locals.authType: "dealer" | "dsr_portal" (audit fix H1 — distinguishes
 *     a normal dealer session from a DSR-in-portal-mode session so pages
 *     can render the portal banner / adjust UI accordingly)
 *
 * Pages and layouts can read these (e.g., BaseLayout embeds the access
 * token as a global JS variable for Vue islands).
 */
declare namespace App {
  interface Locals {
    /**
     * True when the request carries a valid sb_refresh_token cookie
     * (verified server-side via Sattabase /auth/token/refresh-cookie)
     * OR a valid dsr_refresh_token cookie (DSR portal mode, verified
     * via the /api/dsr/auth/refresh-cookie proxy).
     */
    isAuthenticated?: boolean;
    /**
     * Fresh JWT access token minted by /auth/token/refresh-cookie
     * (dealer) or /api/dsr/auth/refresh-cookie (DSR portal mode).
     * Short-lived (5-15 min); clients must refresh via cookie when it expires.
     */
    accessToken?: string;
    /**
     * Audit fix H1: which kind of session this request belongs to.
     * - "dealer"     — normal dealer authenticated via SattaBase cookie
     * - "dsr_portal" — DSR in portal mode, authenticated via the DSR
     *                  refresh-cookie proxy
     * Pages can check this to render the portal banner, hide the
     * "Manage Subscription" button, etc.
     */
    authType?: "dealer" | "dsr_portal";
  }
}
