/**
 * useBootstrap — central bootstrap orchestration.
 *
 * Called by every protected page's onMounted() to ensure:
 *   1. Auth state is resolved (refresh token → access token → /billing/auth/me)
 *   2. Access map is populated (for X-Plan-Limits header + PermissionGuard)
 *   3. Dealer context is initialized (auto-select dealer)
 *   4. App data is loaded (products, sales, etc.) — only on dashboard pages
 *
 * All operations are idempotent — safe to call from every page without
 * triggering duplicate API calls.
 */

import { useAuth } from "./useAuth";
import { useDealerContext } from "./useDealerContext";
import { useAppData } from "./useAppData";
import { useDsrPortal } from "./useDsrPortal";
import { authHelpers } from "../lib/api";

let bootstrapPromise: Promise<void> | null = null;

/**
 * Bootstrap auth + access state. Safe to call from any page.
 *
 * If the user is not authenticated (no refresh token, or refresh fails),
 * redirects to /login (or /dsr/login for DSR portal mode).
 *
 * Returns true if authenticated, false otherwise.
 */
export async function ensureAuthenticated(): Promise<boolean> {
  const { isAuthenticated, refreshUser, initialized } = useAuth();
  const { dsrInPortalMode } = useDsrPortal();

  // Fast path — already authenticated
  if (isAuthenticated.value) return true;

  // DSR in portal mode — they have a DSR JWT, not a dealer JWT, but they
  // can still access /dashboard, /inventory, etc. Don't redirect them.
  if (dsrInPortalMode.value) return true;

  // Try to restore session via refresh token
  if (authHelpers.getRefreshToken()) {
    try {
      const user = await refreshUser();
      if (user) return true;
    } catch {
      // refreshUser swallows errors; fall through to redirect
    }
  }

  // Not authenticated — redirect to login
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
  return false;
}

/**
 * Full bootstrap: auth + dealer context + app data.
 * Used by the AppShell on mount, and by pages that need app data.
 */
export async function bootstrapAppData(): Promise<void> {
  if (bootstrapPromise) return bootstrapPromise;

  bootstrapPromise = (async () => {
    const ok = await ensureAuthenticated();
    if (!ok) return;
    const { ensureLoaded } = useAppData();
    await ensureLoaded();
  })();

  return bootstrapPromise;
}

/**
 * Reset bootstrap state — used on logout.
 */
export function resetBootstrap(): void {
  bootstrapPromise = null;
  const { clearAll } = useAppData();
  clearAll();
  const { clearDealerContext } = useDealerContext();
  clearDealerContext();
}
