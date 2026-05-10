/**
 * useAuth — shared auth + billing state across Vue components.
 *
 * Provides reactive refs for user profile, subscription, and access map.
 * Calls billing.auth.me() once and shares the result across all components
 * via module-level singleton state.
 *
 * On sister domains, the X-Service-Domain header is automatically sent
 * by api.ts, so user + subscription + access are all populated with
 * domain-specific data.
 *
 * Auto-invalidates when a billing update is detected (dispatched by
 * useBillingRedirect via the "sattabase:billing-updated" custom event).
 *
 * Usage:
 *   const { user, subscription, access, isLoading, isAuthenticated, login, logout } = useAuth();
 */

import { ref, computed } from "vue";
import { apiClient } from "@/lib/api";
import {
  login as authLogin,
  logout as authLogout,
  getAuthMe,
  redirectToBase,
  redirectToBaseWithAuthCode,
  requireAuth,
  getErrorMessage,
} from "@/lib/auth";
import type { User, SubscriptionInfo, AuthMeResponse } from "@/lib/types";

// ─── Module-level shared state (singleton across all components) ────────────

const sharedUser = ref<User | null>(null);
const sharedSubscription = ref<SubscriptionInfo | null>(null);
const sharedAccess = ref<Record<string, string | boolean | number>>({});
const sharedLoading = ref(false);
const sharedError = ref<Error | null>(null);
const sharedInitialized = ref(false);
let fetchPromise: Promise<User | null> | null = null;

// ─── Auto-invalidation on billing updates ──────────────────────────────────
//
// When a billing_updated param is detected (via useBillingRedirect),
// it dispatches this custom event. useAuth picks it up and silently refetches
// so that subscription and access are fresh.

const BILLING_EVENT = "sattabase:billing-updated";

if (typeof window !== "undefined") {
  window.addEventListener(BILLING_EVENT, () => {
    if (sharedInitialized.value) {
      // Clear everything so the next fetch hits the API
      sharedUser.value = null;
      sharedSubscription.value = null;
      sharedAccess.value = {};
      sharedInitialized.value = false;
      fetchPromise = null;
      // Silent background refetch — errors handled internally
      fetchAuthMe().catch(() => {});
    }
  });
}

// ─── Internal fetch ─────────────────────────────────────────────────────────

async function fetchAuthMe(): Promise<User | null> {
  sharedLoading.value = true;
  sharedError.value = null;

  try {
    const data = await apiClient.get<AuthMeResponse>("/billing/auth/me");

    // The backend returns user + subscription + access scoped to this domain
    sharedUser.value = data.user as unknown as User;
    sharedSubscription.value = data.subscription as unknown as SubscriptionInfo;
    sharedAccess.value = data.access as Record<
      string,
      string | boolean | number
    >;
    sharedInitialized.value = true;

    return sharedUser.value;
  } catch (err) {
    const message = getErrorMessage(err);
    sharedError.value = err instanceof Error ? err : new Error(message);
    return null;
  } finally {
    sharedLoading.value = false;
    fetchPromise = null;
  }
}

// ─── Public composable ──────────────────────────────────────────────────────

export function useAuth() {
  const user = sharedUser;
  const subscription = sharedSubscription;
  const access = sharedAccess;
  const isLoading = sharedLoading;
  const error = sharedError;

  const isAuthenticated = computed(() => !!sharedUser.value);

  /**
   * Fetch auth.me() — returns user + subscription + access.
   *
   * Deduplicates concurrent calls so that multiple components calling
   * fetchProfile() simultaneously trigger only one API request.
   *
   * Returns cached data if already loaded. Use refetch() to force
   * a fresh API call.
   */
  async function fetchProfile(): Promise<User | null> {
    // Return cached user if already loaded
    if (sharedInitialized.value && sharedUser.value) return sharedUser.value;

    // Deduplicate concurrent fetches
    if (fetchPromise) return fetchPromise;

    fetchPromise = fetchAuthMe();
    return fetchPromise;
  }

  /**
   * Check auth and fetch user in one call. Returns false and redirects
   * to login if not authenticated. Use this in onMounted() of protected pages.
   */
  async function initAuth(): Promise<boolean> {
    if (!requireAuth()) return false;
    await fetchProfile();
    return !!sharedUser.value;
  }

  /**
   * Login — calls auth.login and then fetches the profile.
   */
  async function login(
    email: string,
    password: string,
    remember = false,
  ): Promise<User | null> {
    await authLogin(email, password, remember);
    return fetchProfile();
  }

  /**
   * Logout — blacklists refresh token, clears local state, redirects to login.
   */
  async function logout(): Promise<void> {
    // Clear local state first for immediate UI feedback
    sharedUser.value = null;
    sharedSubscription.value = null;
    sharedAccess.value = {};
    sharedInitialized.value = false;
    fetchPromise = null;
    // Then call auth logout (which clears tokens and redirects)
    await authLogout();
  }

  /**
   * Redirect to base domain for a specific path.
   * For register, forgot-password, etc.
   */
  function redirectToBaseDomain(path: string): void {
    redirectToBase(path);
  }

  /**
   * Generate auth code and redirect to base domain with it.
   * For SSO flows where the user needs to access billing/profile
   * on the base domain while maintaining their session.
   */
  async function redirectWithAuthCode(basePath: string): Promise<void> {
    await redirectToBaseWithAuthCode(basePath);
  }

  /**
   * Invalidate the cached user — forces a fresh fetch on next fetchProfile() call.
   * Useful after profile updates, email changes, or billing operations.
   */
  function invalidateProfile(): void {
    sharedUser.value = null;
    sharedSubscription.value = null;
    sharedAccess.value = {};
    sharedInitialized.value = false;
    fetchPromise = null;
  }

  /**
   * Force a fresh fetch from the API — clears all cached state first.
   * Use after plan changes, checkouts, cancels, reactivations, etc.
   */
  async function refetch(): Promise<User | null> {
    invalidateProfile();
    return fetchProfile();
  }

  return {
    user,
    subscription,
    access,
    isLoading,
    error,
    isAuthenticated,
    initialized: sharedInitialized,
    login,
    logout,
    fetchProfile,
    initAuth,
    refetch,
    invalidateProfile,
    redirectToBaseDomain,
    redirectWithAuthCode,
  };
}
