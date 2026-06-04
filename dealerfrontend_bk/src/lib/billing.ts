/**
 * Billing redirect helpers for the Sattabase sister domain.
 *
 * Sister domains never handle billing directly. Instead, they construct
 * redirect URLs that send users to the Sattabase base domain's billing pages.
 * No API calls are made — these are pure URL string constructors.
 */

import config from "../../sattabase.config";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface BillingUpdateStatus {
  updated: boolean;
  success: 1 | 0 | null;
}

// ─── URL Builder ─────────────────────────────────────────────────────────────

function buildUrl(path: string, returnUrl?: string | null): string {
  let url = `${config.baseDomainUrl}${path}`;
  const effectiveReturnUrl =
    returnUrl || (typeof window !== "undefined" ? window.location.href : config.thisDomainUrl);
  if (effectiveReturnUrl) {
    const sep = url.includes("?") ? "&" : "?";
    url = `${url}${sep}return_url=${encodeURIComponent(effectiveReturnUrl)}`;
  }
  return url;
}

// ─── Billing Redirect API ────────────────────────────────────────────────────

export const billingRedirect = {
  upgrade(productSlug: string, returnUrl?: string | null): string {
    return buildUrl(`/dashboard/billing/plans/${productSlug}`, returnUrl);
  },

  manageSubscription(productSlug: string, returnUrl?: string | null): string {
    return buildUrl(`/dashboard/billing/plans/${productSlug}`, returnUrl);
  },

  portal(returnUrl?: string | null): string {
    return buildUrl("/dashboard/billing", returnUrl);
  },

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
      window.location.pathname + (newSearch ? `?${newSearch}` : "") + window.location.hash;
    window.history.replaceState({}, "", cleanUrl);

    if (value === "1") return { updated: true, success: 1 };
    if (value === "0") return { updated: true, success: 0 };
    return { updated: true, success: null };
  },
};
