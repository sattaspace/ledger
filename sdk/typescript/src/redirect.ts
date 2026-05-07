/**
 * Billing redirect URL constructors.
 *
 * Zero API calls. These methods only construct URL strings.
 * Actual `return_url` validation happens server-side in the Sattabase backend (Phase 6.5).
 */

/**
 * Result of detecting a `billing_updated` query parameter.
 *
 * - `{ updated: true, success: 1 }` — billing action succeeded
 * - `{ updated: true, success: 0 }` — billing action cancelled or failed
 * - `{ updated: false, success: null }` — no `billing_updated` parameter present
 */
export interface BillingUpdateStatus {
  updated: boolean;
  success: 1 | 0 | null;
}

/**
 * Billing redirect URL constructors.
 *
 * Build URLs for redirecting users to Sattabase's billing pages.
 * No API calls are made — these are pure URL string constructors.
 *
 * @example
 * ```ts
 * const billing = new BillingRedirect("https://sattabase.tld");
 *
 * // Redirect to manage subscription
 * const url = billing.manageSubscription("finance", "https://finance.sattabase.tld/settings");
 * // → "https://sattabase.tld/dashboard/billing/plans/finance?return_url=..."
 *
 * // Detect billing update after redirect back
 * const status = BillingRedirect.detectBillingUpdate(window.location.href);
 * if (status.updated && status.success === 1) {
 *   await refreshUserAccess();
 * }
 * ```
 */
export class BillingRedirect {
  private readonly appBaseUrl: string;

  constructor(appBaseUrl: string) {
    this.appBaseUrl = appBaseUrl;
  }

  /**
   * Build a redirect URL with optional return_url parameter.
   */
  private buildUrl(path: string, returnUrl?: string | null): string {
    let url = `${this.appBaseUrl}${path}`;
    if (returnUrl) {
      const sep = url.includes("?") ? "&" : "?";
      url = `${url}${sep}return_url=${encodeURIComponent(returnUrl)}`;
    }
    return url;
  }

  /**
   * Build URL to manage a subscription (view plans, upgrade, cancel).
   *
   * @param productSlug - The product slug (e.g. "finance")
   * @param returnUrl - URL to redirect back to after billing action
   */
  manageSubscription(productSlug: string, returnUrl?: string | null): string {
    return this.buildUrl(`/dashboard/billing/plans/${productSlug}`, returnUrl);
  }

  /**
   * Build URL for the upgrade/plan selection page.
   *
   * @param productSlug - The product slug
   * @param returnUrl - URL to redirect back to after checkout
   */
  upgrade(productSlug: string, returnUrl?: string | null): string {
    return this.buildUrl(`/dashboard/billing/plans/${productSlug}`, returnUrl);
  }

  /**
   * Build URL for the Stripe Customer Portal.
   *
   * @param returnUrl - URL to redirect back to after portal session
   */
  portal(returnUrl?: string | null): string {
    return this.buildUrl("/dashboard/billing", returnUrl);
  }

  /**
   * Parse a URL for the `billing_updated` query parameter.
   *
   * Call this on page load to detect return from a billing redirect.
   *
   * @param url - The URL to parse (can include query params)
   *
   * @example
   * ```ts
   * const status = BillingRedirect.detectBillingUpdate(window.location.href);
   * if (status.updated && status.success === 1) {
   *   console.log("Billing was updated successfully");
   * }
   * ```
   */
  static detectBillingUpdate(url: string): BillingUpdateStatus {
    if (!url.includes("billing_updated=")) {
      return { updated: false, success: null };
    }

    try {
      const params = new URL(url.startsWith("http") ? url : `https://x${url}`)
        .searchParams;
      const value = params.get("billing_updated");
      if (value === null) {
        return { updated: false, success: null };
      }
      if (value === "1") return { updated: true, success: 1 };
      if (value === "0") return { updated: true, success: 0 };
      return { updated: true, success: null };
    } catch {
      return { updated: false, success: null };
    }
  }
}
