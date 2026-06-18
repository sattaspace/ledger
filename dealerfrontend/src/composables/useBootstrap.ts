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
// Audit fix TS-12: removed `authHelpers` import — no longer used after
// removing the `authHelpers.getRefreshToken()` check (the refresh token
// is now in an httpOnly cookie that JS cannot read).
// Audit fix H3: wire fetchDsrPermissions into the bootstrap flow so the
// PermissionGuard / useDsrPermissions infrastructure is actually populated.
import { fetchDsrPermissions, clearDsrPermissions } from "./useDsrPermissions";

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
  // Audit fix TS-10: removed unused `initialized` from the useAuth()
  // destructure. isAuthenticated + refreshUser are the only fields used.
  const { isAuthenticated, refreshUser } = useAuth();
  const { dsrInPortalMode } = useDsrPortal();

  // Fast path — already authenticated
  if (isAuthenticated.value) return true;

  // DSR in portal mode — they have a DSR JWT, not a dealer JWT, but they
  // can still access /dashboard, /inventory, etc. Don't redirect them.
  if (dsrInPortalMode.value) return true;

  // Audit fix TS-12: previously this checked `authHelpers.getRefreshToken()`
  // before attempting refreshUser(). That check is now always false because
  // the refresh token lives in an httpOnly cookie that JavaScript cannot
  // read (authHelpers.getRefreshToken() always returns null post-migration).
  // The check was therefore dead code — unauthenticated users were
  // immediately redirected without ever attempting the refresh.
  //
  // We now ALWAYS attempt refreshUser(). The underlying apiClient in
  // lib/api.ts has a 401-refresh interceptor that calls
  // /auth/token/refresh-cookie (using credentials: 'include' to send the
  // httpOnly cookie) when /billing/auth/me returns 401. If the cookie is
  // absent or expired, refreshUser() returns null and we fall through to
  // the redirect below.
  try {
    const user = await refreshUser();
    if (user) return true;
  } catch {
    // refreshUser swallows errors; fall through to redirect
  }

  // Not authenticated — redirect to login
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
  return false;
}

/**
 * Full bootstrap: auth + dealer context + app data + DSR permissions.
 * Used by the AppShell on mount, and by pages that need app data.
 *
 * Audit fix H3: also calls fetchDsrPermissions() after auth resolves.
 * Previously fetchDsrPermissions was exported but never called, so
 * the entire PermissionGuard / useDsrPermissions infrastructure was
 * dead code (dsrPermissions stayed {}, isDsrDealer stayed false).
 */
export async function bootstrapAppData(): Promise<void> {
  if (bootstrapPromise) return bootstrapPromise;

  bootstrapPromise = (async () => {
    const ok = await ensureAuthenticated();
    if (!ok) return;
    const { ensureLoaded } = useAppData();
    await ensureLoaded();

    // Audit fix H3: fetch DSR permissions in the background (don't block
    // the bootstrap chain on it). This populates dsrPermissions and
    // isDsrDealer in useDsrPermissions, so PermissionGuard and
    // useDsrPermissions().hasPermission() work correctly.
    //
    // The /dsr/permissions endpoint returns is_dealer=true for dealers
    // (with empty permissions — dealers bypass all module checks) and
    // the actual per-dealer permissions for DSRs. For unauthenticated
    // callers it returns 401 (handled silently by useDsrPermissions).
    fetchDsrPermissions().catch((err) => {
      // Don't fail the bootstrap — permissions are a fallback safety
      // check; the backend enforces them authoritatively.
      if (import.meta.env.DEV) {
        console.warn("[BOOTSTRAP] fetchDsrPermissions failed:", err);
      }
    });
  })();

  return bootstrapPromise;
}

/**
 * Reset bootstrap state — used on logout.
 *
 * Audit fix H3: also clear DSR permissions so a new login doesn't see
 * the previous user's permission state.
 */
export function resetBootstrap(): void {
  bootstrapPromise = null;
  const { clearAll } = useAppData();
  clearAll();
  const { clearDealerContext } = useDealerContext();
  clearDealerContext();
  // Audit fix H3: clear DSR permissions on logout.
  clearDsrPermissions();
}
