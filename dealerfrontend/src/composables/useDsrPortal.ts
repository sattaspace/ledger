/**
 * useDsrPortal — DSR "Enter Portal" mode state.
 *
 * When a DSR clicks "Enter Portal" on their dashboard, they navigate the
 * main dealer app routes (/dashboard, /inventory, etc.) using their
 * DSR-scoped JWT instead of SattaBase dealer auth. This composable tracks
 * that state so the AppShell can render the purple banner + adjust the
 * logout button to "Back to Dashboard" instead of full logout.
 *
 * State is persisted to localStorage so portal mode survives page
 * navigations in the MPA. On logout/exit, the flag is cleared.
 */

import { ref, computed } from "vue";

const PORTAL_FLAG_KEY = "dealercore:dsr_portal_mode";
const PORTAL_DEALER_KEY = "dsr_selected_dealer"; // shares key with dsrClient

const dsrInPortalMode = ref(false);
const dsrPortalDealer = ref<{ username: string; full_name: string; business_name: string } | null>(null);

// Hydrate from localStorage on module load (runs once per tab)
if (typeof window !== "undefined") {
  dsrInPortalMode.value = localStorage.getItem(PORTAL_FLAG_KEY) === "true";
  const stored = localStorage.getItem(PORTAL_DEALER_KEY);
  if (stored) {
    try {
      dsrPortalDealer.value = JSON.parse(stored);
    } catch {
      dsrPortalDealer.value = null;
    }
  }
}

function enterPortalMode(dealer: { username: string; full_name: string; business_name: string }): void {
  dsrInPortalMode.value = true;
  dsrPortalDealer.value = dealer;
  if (typeof window !== "undefined") {
    localStorage.setItem(PORTAL_FLAG_KEY, "true");
  }
}

function exitPortalMode(): void {
  dsrInPortalMode.value = false;
  dsrPortalDealer.value = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem(PORTAL_FLAG_KEY);
  }
}

/**
 * Defensive scrub of all DSR-portal-related localStorage state.
 *
 * Call this whenever a DEALER session is starting or ending so that a
 * stale `dealercore:dsr_portal_mode` from a previous DSR session
 * (e.g. user clicked Enter Portal as DSR, closed the tab, then logged
 * in as dealer on the same browser) cannot leak across sessions and
 * incorrectly render the "DSR Portal Mode" banner on the dealer UI.
 */
export function clearDsrPortalState(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(PORTAL_FLAG_KEY);
    localStorage.removeItem(PORTAL_DEALER_KEY);
  } catch {
    /* localStorage unavailable */
  }
  dsrInPortalMode.value = false;
  dsrPortalDealer.value = null;
}

export function useDsrPortal() {
  return {
    dsrInPortalMode: computed(() => dsrInPortalMode.value),
    dsrPortalDealer: computed(() => dsrPortalDealer.value),
    enterPortalMode,
    exitPortalMode,
  };
}
