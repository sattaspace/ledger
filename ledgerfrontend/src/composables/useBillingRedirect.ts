/**
 * useBillingRedirect — detect billing return from Sattabase.
 */

import { ref, onMounted } from "vue";
import { useAuth } from "./useAuth";

const BILLING_EVENT = "sattabase:billing-updated";
const PARAM_NAME = "billing_updated";

export function useBillingRedirect() {
  const isBillingReturn = ref(false);
  const billingSuccess = ref<boolean | null>(null);

  function checkBillingRedirect(): void {
    if (typeof window === "undefined") return;

    const params = new URLSearchParams(window.location.search);
    const updated = params.get(PARAM_NAME);

    if (updated === null) return;

    isBillingReturn.value = true;
    billingSuccess.value = updated === "1" ? true : updated === "0" ? false : null;

    params.delete(PARAM_NAME);
    const newSearch = params.toString();
    const cleanUrl =
      window.location.pathname + (newSearch ? `?${newSearch}` : "") + window.location.hash;
    window.history.replaceState({}, "", cleanUrl);

    window.dispatchEvent(
      new CustomEvent(BILLING_EVENT, {
        detail: { success: billingSuccess.value },
      }),
    );
  }

  onMounted(() => {
    checkBillingRedirect();
  });

  return {
    isBillingReturn,
    billingSuccess,
    checkBillingRedirect,
  };
}
