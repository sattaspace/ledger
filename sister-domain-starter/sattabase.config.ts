/**
 * Sattabase Sister Domain Configuration
 *
 * Central configuration file for any AstroJS sister domain frontend.
 * All values are pulled from environment variables with sensible defaults
 * for local development.
 *
 * This file is imported by src/lib/api.ts, src/lib/auth.ts, src/lib/billing.ts,
 * and the Astro middleware — it is the single source of truth for all
 * Sattabase-related configuration.
 */

export default {
  // API base URL of the Sattabase backend (Django Ninja)
  apiBaseUrl:
    import.meta.env.PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1",

  // Sattabase base domain frontend URL (for redirects to register, billing, etc.)
  baseDomainUrl:
    import.meta.env.PUBLIC_BASE_DOMAIN_URL || "http://localhost:4321",

  // This sister domain's URL (for return redirects after billing)
  thisDomainUrl:
    import.meta.env.PUBLIC_THIS_DOMAIN_URL || "http://localhost:4322",

  // Service domain identifier (must match ServiceDomain in Sattabase)
  serviceDomain:
    import.meta.env.PUBLIC_SERVICE_DOMAIN || "finance.sattaspace.com",

  // Session cookie name (must match SB_SESSION_COOKIE_NAME on backend)
  sessionCookieName:
    import.meta.env.PUBLIC_SESSION_COOKIE_NAME || "sattabase_session_cookie",

  // Token storage key prefix (domain-specific to avoid collisions)
  tokenKeyPrefix: import.meta.env.PUBLIC_TOKEN_KEY_PREFIX || "sattabase:",

  // JWT access token lifetime in minutes (for proactive refresh)
  accessTokenLifetimeMinutes: 60,
};
