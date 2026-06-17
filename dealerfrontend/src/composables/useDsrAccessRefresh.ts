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
 */

import { onUnmounted } from "vue";
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
    const newAccess =
      result.effective_access || { dashboard: true, __subscription_active: false };
    setAccessMap(newAccess);

    if (import.meta.env.DEV) {
      console.log("%c[DSR ACCESS] Refreshed", "color: #10b981; font-weight: bold", {
        cache_invalidated: result.cache_invalidated,
        effective_access_keys: Object.keys(newAccess),
      });
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
      triggerErrorToast("Could not refresh permissions. Please re-login to see the latest access.");
    }
    return false;
  }
}

function startDsrAccessRefreshTimer(): void {
  stopDsrAccessRefreshTimer();
  timer = setInterval(() => {
    const { dsrInPortalMode } = useDsrPortal();
    if (dsrInPortalMode.value) {
      refreshDsrAccess(true).catch(() => {});
    } else {
      stopDsrAccessRefreshTimer();
    }
  }, 5 * 60 * 1000);
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

// Auto-stop on page unload (safety net)
if (typeof window !== "undefined") {
  window.addEventListener("beforeunload", stopDsrAccessRefreshTimer);
}
