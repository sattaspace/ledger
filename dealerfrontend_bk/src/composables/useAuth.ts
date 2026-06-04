/**
 * useAuth — shared auth + billing state across Vue components.
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
import { cacheExchangeRates, clearExchangeRates, cacheCurrenciesMeta } from "@/lib/currency";
import { cacheUserTimezone, clearUserTimezone } from "@/lib/timezone";
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

const BILLING_EVENT = "sattabase:billing-updated";

if (typeof window !== "undefined") {
  window.addEventListener(BILLING_EVENT, () => {
    if (sharedInitialized.value) {
      sharedUser.value = null;
      sharedSubscription.value = null;
      sharedAccess.value = {};
      sharedInitialized.value = false;
      fetchPromise = null;
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

    sharedUser.value = data.user as unknown as User;
    sharedSubscription.value = data.subscription as unknown as SubscriptionInfo;
    sharedAccess.value = data.access as Record<string, string | boolean | number>;
    sharedInitialized.value = true;

    // ── Cache currency & timezone for this session ──────────────────────
    cacheExchangeRates(data);
    cacheCurrenciesMeta(data.currencies as Record<string, unknown> | null);
    cacheUserTimezone(data.user?.timezone);

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

  async function fetchProfile(): Promise<User | null> {
    if (sharedInitialized.value && sharedUser.value) return sharedUser.value;
    if (fetchPromise) return fetchPromise;
    fetchPromise = fetchAuthMe();
    return fetchPromise;
  }

  async function initAuth(): Promise<boolean> {
    if (!requireAuth()) return false;
    await fetchProfile();
    return !!sharedUser.value;
  }

  async function login(email: string, password: string, remember = false): Promise<User | null> {
    await authLogin(email, password, remember);
    return fetchProfile();
  }

  async function logout(): Promise<void> {
    sharedUser.value = null;
    sharedSubscription.value = null;
    sharedAccess.value = {};
    sharedInitialized.value = false;
    fetchPromise = null;
    clearExchangeRates();
    clearUserTimezone();
    await authLogout();
  }

  function redirectToBaseDomain(path: string): void {
    redirectToBase(path);
  }

  async function redirectWithAuthCode(basePath: string): Promise<void> {
    await redirectToBaseWithAuthCode(basePath);
  }

  function invalidateProfile(): void {
    sharedUser.value = null;
    sharedSubscription.value = null;
    sharedAccess.value = {};
    sharedInitialized.value = false;
    fetchPromise = null;
  }

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
