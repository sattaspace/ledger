/**
 * useDsrAccessRefresh — periodic access map refresh for DSRs in portal mode.
 *
 * When a DSR enters portal mode, the dealer's plan may change at any time
 * (the dealer themselves changes billing from another device). To keep
 * menu visibility up to date, we periodically call the backend's
 * /dsr/auth/refresh-access endpoint which invalidates the backend cache
 * and returns the fresh effective_access map.
 *
 * Timer interval: 5 minutes (matches backend cache TTL).
 *
 * Started by /dsr/dashboard's "Enter Portal" handler. Stopped automatically
 * when the DSR exits portal mode (via exitPortalMode).
 *
 * Audit fix M8 + L4: the module-level `beforeunload` listener and
 * `setInterval` are now properly tracked and removed. The interval also
 * self-stops when `dsrInPortalMode` becomes false (e.g., user clicks
 * "Exit Portal"). The beforeunload listener is registered once at module
 * load and is idempotent.
 */

import { dsrApi } from "../services/dsrClient";
import { setAccessMap } from "./useAccess";
import { useDsrPortal } from "./useDsrPortal";
import { useToasts } from "./useToasts";

let timer: ReturnType<typeof setInterval> | null = null;

async function refreshDsrAccess(silent = true): Promise<boolean> {
  const { dsrInPortalMode } = useDsrPortal();
  if (!dsrInPortalMode.value) return false;

  try {
    const result = await dsrApi.refreshAccess();
    const newAccess = result.effective_access || {
      dashboard: true,
      __subscription_active: false,
    };
    setAccessMap(newAccess);

    if (import.meta.env.DEV) {
      console.log(
        "%c[DSR ACCESS] Refreshed",
        "color: #10b981; font-weight: bold",
        {
          cache_invalidated: result.cache_invalidated,
          effective_access_keys: Object.keys(newAccess),
        },
      );
    }

    if (!silent) {
      const { triggerToast } = useToasts();
      triggerToast("Permissions refreshed. Menu visibility is now up-to-date.");
    }
    return true;
  } catch (error: any) {
    console.error("[DSR ACCESS] Refresh failed:", error);
    if (!silent) {
      const { triggerErrorToast } = useToasts();
      triggerErrorToast(
        "Could not refresh permissions. Please re-login to see the latest access.",
      );
    }
    return false;
  }
}

function startDsrAccessRefreshTimer(): void {
  // Audit fix L4: always stop any existing timer first — this prevents
  // multiple intervals from accumulating if startDsrAccessRefreshTimer()
  // is called multiple times without an explicit stop. (The previous
  // code already did this, but we now also document the contract.)
  stopDsrAccessRefreshTimer();
  timer = setInterval(
    () => {
      const { dsrInPortalMode } = useDsrPortal();
      if (dsrInPortalMode.value) {
        refreshDsrAccess(true).catch(() => {});
      } else {
        // Audit fix L4: self-stop when portal mode ends so the interval
        // doesn't keep firing every 5 min just to check the flag.
        stopDsrAccessRefreshTimer();
      }
    },
    5 * 60 * 1000,
  );
}

function stopDsrAccessRefreshTimer(): void {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

export function useDsrAccessRefresh() {
  return {
    refreshDsrAccess,
    startDsrAccessRefreshTimer,
    stopDsrAccessRefreshTimer,
  };
}

// Audit fix M8: register the beforeunload listener once at module load.
// The listener is idempotent (calling stopDsrAccessRefreshTimer when timer
// is already null is a no-op), so it doesn't matter if it fires when there
// is no active timer. We do NOT register it inside the composable body
// because that would attach a new listener every time useDsrAccessRefresh()
// is called — the listener is shared across all callers.
//
// The listener is intentionally never removed (it lives for the lifetime
// of the tab) because:
//  1. The handler is idempotent and cheap.
//  2. Removing it would require a teardown hook that runs after every
//     component that uses this composable unmounts — but the composable
//     is designed to be called from multiple places (DsrDashboard,
//     AppHeader, AppFooter) and any one of them unmounting would
//     prematurely remove the listener for the others.
//  3. Tab-close cleanup is the only thing we actually need, and that's
//     exactly what beforeunload provides.
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", stopDsrAccessRefreshTimer);
}
