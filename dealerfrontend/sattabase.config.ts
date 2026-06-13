/**
 * Sattabase Sister Domain Configuration
 *
 * Central configuration file for the DealerCore sister domain frontend.
 * All values are pulled from environment variables with sensible defaults
 * for local development.
 *
 * This file is imported by:
 *   - src/lib/api.ts
 *   - src/lib/auth.ts
 *   - src/lib/billing.ts
 *   - Astro middleware
 *
 * It is the single source of truth for all Sattabase-related configuration.
 */

export default {
  // -------------------------------------------------------------------------
  // API Configuration
  // -------------------------------------------------------------------------

  /**
   * API base URL of the Sattabase backend (Django Ninja)
   * This is where auth requests go: /auth/login, /auth/token/refresh, /billing/auth/me
   *
   * IMPORTANT: This points to SattaBase backend, NOT the dealer backend.
   * The dealer backend (localhost:8088) only handles business data.
   */
  apiBaseUrl:
    import.meta.env.PUBLIC_API_BASE_URL_SB || "http://localhost:8086/api/v1",

  // -------------------------------------------------------------------------
  // Domain URLs
  // -------------------------------------------------------------------------

  /**
   * Sattabase base domain frontend URL
   * Used for redirects to register, billing, profile, etc.
   * Example: http://localhost:4321 (dev) or https://sattaspace.com (prod)
   */
  baseDomainUrl:
    import.meta.env.PUBLIC_BASE_DOMAIN_URL || "http://localhost:4321",

  /**
   * This sister domain's URL
   * Used for return redirects after billing actions
   * Example: http://localhost:4323 (dev) or https://dealer.sattaspace.com (prod)
   */
  thisDomainUrl:
    import.meta.env.PUBLIC_THIS_DOMAIN_URL || "http://localhost:4323",

  // -------------------------------------------------------------------------
  // Service Domain Configuration
  // -------------------------------------------------------------------------

  /**
   * Service domain identifier
   * Must match the ServiceDomain record in SattaBase billing system.
   *
   * This is sent as the X-Service-Domain header with every API request,
   * allowing SattaBase to return domain-scoped subscription and access data.
   *
   * Examples:
   *   - "dealer.sattaspace.com" (production)
   *   - "localhost:4323" (development)
   */
  serviceDomain: import.meta.env.PUBLIC_SERVICE_DOMAIN || "localhost:4323",

  // -------------------------------------------------------------------------
  // Token Configuration
  // -------------------------------------------------------------------------

  /**
   * Session cookie name
   * Must match SB_SESSION_COOKIE_NAME on the SattaBase backend
   */
  sessionCookieName:
    import.meta.env.PUBLIC_SESSION_COOKIE_NAME || "sattabase_session_cookie",

  /**
   * Token storage key prefix
   * Domain-specific to avoid collisions with other sister domains
   *
   * Example: "dealercore:" results in keys like "dealercore:access_token"
   */
  tokenKeyPrefix: import.meta.env.PUBLIC_TOKEN_KEY_PREFIX || "dealercore:",

  /**
   * JWT access token lifetime in minutes
   * Used for proactive refresh (refresh before expiry)
   */
  accessTokenLifetimeMinutes: 60,

  // -------------------------------------------------------------------------
  // Product Configuration
  // -------------------------------------------------------------------------

  /**
   * Product slug as defined in SattaBase billing system
   * Must match the Product record in SattaBase
   */
  productSlug: "dealercore",

  // -------------------------------------------------------------------------
  // Dealer Backend Configuration
  // -------------------------------------------------------------------------

  /**
   * Dealer backend API URL
   * This is for business data endpoints only (inventory, sales, etc.)
   * NOT for authentication - auth goes to SattaBase directly
   */
  dealerApiBaseUrl:
    import.meta.env.PUBLIC_DEALER_API_URL || "http://localhost:8088/api",
};
