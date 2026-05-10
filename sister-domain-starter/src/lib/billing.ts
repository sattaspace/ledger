/**
 * Billing redirect helpers for the Sattabase sister domain.
 *
 * Sister domains never handle billing directly. Instead, they construct
 * redirect URLs that send users to the Sattabase base domain's billing pages.
 * No API calls are made — these are pure URL string constructors.
 *
 * After a billing action, Sattabase redirects the user back to the sister
 * domain with ?billing_updated=1 (success) or ?billing_updated=0 (failure).
 * Use `detectBillingUpdate()` to check for this parameter.
 *
 * Usage:
 *   import { billingRedirect } from "@/lib/billing";
 *   // Redirect to upgrade page
 *   window.location.href = billingRedirect.upgrade("finance");
 *   // Detect billing return
 *   const status = billingRedirect.detectBillingUpdate();
 */

import config from "../../sattabase.config";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface BillingUpdateStatus {
  /** true when a billing_updated param was detected in the URL */
  updated: boolean;
  /** 1 = success, 0 = failure/cancel, null = no param detected */
  success: 1 | 0 | null;
}

// ─── URL Builder ─────────────────────────────────────────────────────────────

/**
 * Build a redirect URL with optional return_url parameter.
 */
function buildUrl(path: string, returnUrl?: string | null): string {
  let url = `${config.baseDomainUrl}${path}`;
  const effectiveReturnUrl =
    returnUrl ||
    (typeof window !== "undefined"
      ? window.location.href
      : config.thisDomainUrl);
  if (effectiveReturnUrl) {
    const sep = url.includes("?") ? "&" : "?";
    url = `${url}${sep}return_url=${encodeURIComponent(effectiveReturnUrl)}`;
  }
  return url;
}

// ─── Billing Redirect API ────────────────────────────────────────────────────

export const billingRedirect = {
  /**
   * Build URL for the upgrade/plan selection page.
   *
   * @param productSlug - The product slug (e.g. "finance")
   * @param returnUrl - URL to redirect back to after checkout
   */
  upgrade(productSlug: string, returnUrl?: string | null): string {
    return buildUrl(`/dashboard/billing/plans/${productSlug}`, returnUrl);
  },

  /**
   * Build URL to manage a subscription (view plans, upgrade, cancel).
   *
   * @param productSlug - The product slug
   * @param returnUrl - URL to redirect back to after billing action
   */
  manageSubscription(productSlug: string, returnUrl?: string | null): string {
    return buildUrl(`/dashboard/billing/plans/${productSlug}`, returnUrl);
  },

  /**
   * Build URL for the Stripe Customer Portal.
   *
   * @param returnUrl - URL to redirect back to after portal session
   */
  portal(returnUrl?: string | null): string {
    return buildUrl("/dashboard/billing", returnUrl);
  },

  /**
   * Detect a `billing_updated` query parameter in the current URL.
   *
   * Call this on page load to detect return from a billing redirect.
   * Automatically cleans the URL parameter via history.replaceState.
   *
   * @returns BillingUpdateStatus indicating whether a billing update was detected
   */
  detectBillingUpdate(): BillingUpdateStatus {
    if (typeof window === "undefined") {
      return { updated: false, success: null };
    }

    const params = new URLSearchParams(window.location.search);
    const value = params.get("billing_updated");

    if (value === null) {
      return { updated: false, success: null };
    }

    // Clean the URL so refresh doesn't re-trigger
    params.delete("billing_updated");
    const newSearch = params.toString();
    const cleanUrl =
      window.location.pathname +
      (newSearch ? `?${newSearch}` : "") +
      window.location.hash;
    window.history.replaceState({}, "", cleanUrl);

    if (value === "1") return { updated: true, success: 1 };
    if (value === "0") return { updated: true, success: 0 };
    return { updated: true, success: null };
  },
};
