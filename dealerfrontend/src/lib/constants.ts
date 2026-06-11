/**
 * DEALERCORE v3.0 — Application Constants
 *
 * Centralized configuration for external services.
 */

// ─── SattaBase (Base System) Configuration ─────────────────────────────────

/**
 * SattaBase Frontend URL (port 4321)
 * Used for redirects to signup, login, password reset, billing
 */
export const SATTABASE_URL = import.meta.env.VITE_SATTABASE_URL || 'http://localhost:4321';

/**
 * SattaBase API URL (port 8086)
 * Used for direct API calls (primarily from backend)
 */
export const SATTABASE_API_URL = import.meta.env.VITE_SATTABASE_API_URL || 'http://localhost:8086/api/v1';

// ─── Navigation URLs ───────────────────────────────────────────────────────

/**
 * URL builder for SattaBase pages
 */
export const sattabaseUrls = {
  // Auth pages
  signup: `${SATTABASE_URL}/signup`,
  login: `${SATTABASE_URL}/login`,
  forgotPassword: `${SATTABASE_URL}/forgot-password`,
  resetPassword: `${SATTABASE_URL}/reset-password`,
  
  // Account management
  account: `${SATTABASE_URL}/account`,
  accountProfile: `${SATTABASE_URL}/account/profile`,
  accountPassword: `${SATTABASE_URL}/account/password`,
  closeAccount: `${SATTABASE_URL}/account/close`,
  
  // Billing & Subscription
  billing: `${SATTABASE_URL}/billing`,
  plans: `${SATTABASE_URL}/plans`,
  checkout: (planId: string) => `${SATTABASE_URL}/checkout?plan=${planId}`,
  
  // Admin (for staff users)
  admin: `${SATTABASE_URL}/admin`,
  adminApiKeys: `${SATTABASE_URL}/admin/api-keys`,
};

// ─── Product Configuration ─────────────────────────────────────────────────

/**
 * Product slug as defined in SattaBase
 * Must match the product created in SattaBase admin
 */
export const DEALERCORE_PRODUCT_SLUG = 'dealercore';

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
  currency: 'USD',
  timezone: 'America/New_York',
  language: 'en',
};
