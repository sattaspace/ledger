/**
 * Sattabase Sister Domain Configuration — Satta Ledger
 *
 * Central configuration file for the Ledger sister domain frontend.
 * All values are pulled from environment variables with sensible defaults
 * for local development.
 */
const isDev = import.meta.env.DEV;

export default {
  // API base URL of the Sattabase backend (Django Ninja)
  apiBaseUrl: isDev
    ? "http://localhost:8086/api/v1"
    : import.meta.env.SL_SATTABASE_BASE_URL || "https://baseapi.sattaspace.com/api/v1",

  // Sattabase base domain frontend URL (for redirects to register, billing, etc.)
  baseDomainUrl: isDev
    ? "http://localhost:4321"
    : import.meta.env.PUBLIC_SITE_URL_SB || "https://base.sattaspace.com",

  // This sister domain's URL (for return redirects after billing)
  thisDomainUrl: isDev
    ? "http://localhost:4322"
    : import.meta.env.SL_FRONTEND_URL || "https://ledger.sattaspace.com",

  // Service domain identifier (must match ServiceDomain in Sattabase)
  serviceDomain: import.meta.env.SL_SATTABASE_SERVICE_DOMAIN || "ledger.sattaspace.com",

  // Session cookie name (must match SB_SESSION_COOKIE_NAME on backend)
  sessionCookieName: import.meta.env.SL_SESSION_COOKIE_NAME || "sattabase_session_cookie",

  // Token storage key prefix (domain-specific to avoid collisions)
  tokenKeyPrefix: import.meta.env.PUBLIC_TOKEN_KEY_PREFIX_SL || "sattabase-ledger:",

  // Ledger backend API base URL (Django Ninja — separate from Sattabase Core)
  ledgerApiUrl: isDev
    ? "http://localhost:8087/api/v1"
    : import.meta.env.SL_LEDGER_API_URL || "https://ledgerapi.sattaspace.com/api/v1",

  // JWT access token lifetime in minutes (for proactive refresh)
  accessTokenLifetimeMinutes: 60,
};
