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
 *
 * ─── HYDRATION WARNING (audit fix HYDRATION M-1) ───────────────────────
 *
 * This composable reads localStorage AT MODULE LOAD TIME (lines 23-33).
 * That means:
 *
 *   - On SSR, `dsrInPortalMode.value = false` and `dsrPortalDealer.value = null`
 *   - On the client, refs are populated from localStorage BEFORE any Vue
 *     component setup runs.
 *
 * This pattern is ONLY safe if no `client:load` Vue island renders
 * `dsrInPortalMode` or `dsrPortalDealer` directly in its template. Today
 * (2026-06) only `AppSidebar.vue`, `AppHeader.vue`, and `AppFooter.vue`
 * bind to these refs in their templates — and all three are mounted with
 * `client:only="vue"` in `AppLayout.astro`, which skips SSR entirely.
 *
 * If you ever change one of those three islands to `client:load`, or add
 * a NEW `client:load` component that binds to `dsrInPortalMode` in its
 * template, you WILL trigger a Vue hydration warning (server renders
 * without the banner, client renders with it). To avoid this:
 *
 *   Option A (preferred): keep the consuming component as `client:only="vue"`.
 *   Option B: move the localStorage read into `onMounted` and expose a
 *     `ready` ref that the template gates on with `v-if="ready"`.
 *   Option C: read the portal-mode flag from a cookie (sent on every SSR
 *     request) instead of localStorage.
 *
 * The `BaseLayout.astro:72-85` inline script ALSO reads the same localStorage
 * key and applies a `dsr-portal-mode` class to `<html>` and `<body>` BEFORE
 * Vue mounts. This is intentional and does NOT cause a hydration conflict
 * because the class is on `<body>` (managed by Astro, not Vue).
 */

import { ref, computed } from "vue";

const PORTAL_FLAG_KEY = "dealercore:dsr_portal_mode";
const PORTAL_DEALER_KEY = "dsr_selected_dealer"; // shares key with dsrClient

const dsrInPortalMode = ref(false);
const dsrPortalDealer = ref<{
  username: string;
  full_name: string;
  business_name: string;
} | null>(null);

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

function enterPortalMode(dealer: {
  username: string;
  full_name: string;
  business_name: string;
}): void {
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
