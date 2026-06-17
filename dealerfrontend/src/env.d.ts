/// <reference types="astro/client" />

/**
 * Extend Astro's Locals type with auth state populated by src/middleware.ts.
 *
 * The middleware validates the sb_refresh_token cookie on every protected
 * page request and, on success, populates:
 *   - locals.isAuthenticated: true
 *   - locals.accessToken: the fresh JWT access token from /auth/token/refresh-cookie
 *
 * Pages and layouts can read these (e.g., BaseLayout embeds the access
 * token as a global JS variable for Vue islands).
 */
declare namespace App {
  interface Locals {
    /**
     * True when the request carries a valid sb_refresh_token cookie
     * (verified server-side via Sattabase /auth/token/refresh-cookie).
     */
    isAuthenticated?: boolean;
    /**
     * Fresh JWT access token minted by /auth/token/refresh-cookie.
     * Short-lived (5-15 min); clients must refresh via cookie when it expires.
     */
    accessToken?: string;
  }
}
