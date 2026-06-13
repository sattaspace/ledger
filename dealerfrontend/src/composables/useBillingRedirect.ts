/**
 * useBillingRedirect — detect billing return from Sattabase.
 *
 * Sister domains place this composable in their root layout or
 * on the dashboard page to detect when a user returns from a
 * billing operation on the Sattabase base domain.
 *
 * Detection flow:
 *   1. Sattabase redirects to sister domain with ?billing_updated=1 (or 0)
 *   2. useBillingRedirect detects the param on mount
 *   3. Cleans the URL via history.replaceState (no flicker)
 *   4. Dispatches a "sattabase:billing-updated" CustomEvent
 *   5. useAuth() picks up the event and auto-refetches user/subscription/access
 *
 * Usage (in a root layout or dashboard page):
 *   const { isBillingReturn, billingSuccess, checkBillingRedirect } = useBillingRedirect();
 *
 *   if (isBillingReturn.value && billingSuccess.value) {
 *     // Show success toast
 *   }
 */

import { ref, onMounted } from "vue";

const BILLING_EVENT = "sattabase:billing-updated";
const PARAM_NAME = "billing_updated";

export function useBillingRedirect() {
  /** true when a billing_updated param was detected in the current URL */
  const isBillingReturn = ref(false);

  /**
   * The result of the billing operation:
   *   true  — billing_updated=1 (success: plan changed, payment succeeded)
   *   false — billing_updated=0 (failure or cancellation)
   *   null  — no billing return detected (initial state)
   */
  const billingSuccess = ref<boolean | null>(null);

  /**
   * Check for the billing_updated query parameter in the current URL.
   *
   * Call this in onMounted() of your dashboard layout or page.
   * If a billing return is detected:
   *   - The URL is cleaned (param removed via history.replaceState)
   *   - A "sattabase:billing-updated" CustomEvent is dispatched
   *   - useAuth automatically refetches the profile
   */
  function checkBillingRedirect(): void {
    if (typeof window === "undefined") return;

    const params = new URLSearchParams(window.location.search);
    const updated = params.get(PARAM_NAME);

    if (updated === null) return; // No billing return — nothing to do

    isBillingReturn.value = true;
    billingSuccess.value =
      updated === "1" ? true : updated === "0" ? false : null;

    // Remove billing_updated from URL so a manual refresh doesn't re-trigger
    params.delete(PARAM_NAME);
    const newSearch = params.toString();
    const cleanUrl =
      window.location.pathname +
      (newSearch ? `?${newSearch}` : "") +
      window.location.hash;
    window.history.replaceState({}, "", cleanUrl);

    // Notify useAuth to invalidate and refetch
    window.dispatchEvent(
      new CustomEvent(BILLING_EVENT, {
        detail: { success: billingSuccess.value },
      }),
    );
  }

  /**
   * Auto-detect on mount. Also fetches the profile to ensure
   * subscription and access data is fresh after a billing change.
   */
  onMounted(() => {
    checkBillingRedirect();
  });

  return {
    isBillingReturn,
    billingSuccess,
    checkBillingRedirect,
  };
}
