/**
 * DEALERCORE v3.0 — Application Constants
 *
 * This file re-exports values from sattabase.config.ts for convenience
 * and provides dealer-specific constants.
 */

import config from "../../sattabase.config";

// ─── Re-export Configuration ────────────────────────────────────────────────

/**
 * SattaBase Frontend URL (for redirects)
 * Used for redirects to signup, login, password reset, billing
 */
export const SATTABASE_URL = config.baseDomainUrl;

/**
 * SattaBase API URL
 * Used for auth and billing API calls
 */
export const SATTABASE_API_URL = config.apiBaseUrl;

/**
 * Dealer Backend API URL
 * Used for business data endpoints only (inventory, sales, etc.)
 */
export const DEALER_API_URL = config.dealerApiBaseUrl;

// ─── Navigation URLs ────────────────────────────────────────────────────────

/**
 * URL builder for SattaBase pages
 */
export const sattabaseUrls = {
  // Auth pages (on SattaBase)
  signup: `${SATTABASE_URL}/auth/register`,
  login: `${SATTABASE_URL}/auth/login`,
  forgotPassword: `${SATTABASE_URL}/auth/forgot-password`,
  resetPassword: `${SATTABASE_URL}/auth/reset-password`,
  verifyEmail: `${SATTABASE_URL}/auth/verify-email`,

  // Account management (on SattaBase)
  profile: `${SATTABASE_URL}/dashboard/profile`,
  accountSettings: `${SATTABASE_URL}/dashboard/settings`,

  // Billing & Subscription (on SattaBase)
  billing: `${SATTABASE_URL}/dashboard/billing`,
  plans: `${SATTABASE_URL}/dashboard/billing/plans`,

  // SSO Callback (on SattaBase)
  callback: `${SATTABASE_URL}/auth/callback`,
};

// ─── Product Configuration ─────────────────────────────────────────────────

/**
 * Product slug as defined in SattaBase billing system
 * Must match the product created in SattaBase admin
 */
export const DEALERCORE_PRODUCT_SLUG = config.productSlug;

/**
 * Service domain identifier
 * Sent as X-Service-Domain header for domain-scoped access
 */
export const SERVICE_DOMAIN = config.serviceDomain;

// ─── Token Keys ─────────────────────────────────────────────────────────────

/**
 * Token storage keys (using prefix from config)
 */
export const TOKEN_KEYS = {
  access: `${config.tokenKeyPrefix}access_token`,
  refresh: `${config.tokenKeyPrefix}refresh_token`,
  remember: `${config.tokenKeyPrefix}remember_me`,
};

// ─── Feature Flags ─────────────────────────────────────────────────────────

/**
 * Feature flags based on build configuration
 */
export const FEATURES = {
  // Enable/disable SattaBase integration features
  enableSSO: true,
  enableAccessMatrix: true,
  enableSubscriptionCheck: true,
};

// ─── Default Values ────────────────────────────────────────────────────────

export const DEFAULTS = {
  currency: "USD",
  timezone: "America/New_York",
  language: "en",
};

// ─── Export Config for Direct Access ───────────────────────────────────────

export { config };
