<script setup lang="ts">
/**
 * Session Guard Component
 *
 * Wraps protected app pages and ensures the user is authenticated before
 * rendering content. On auth failure, redirects to /login (or /dsr/login
 * if the user appears to be a DSR in portal mode).
 *
 * NOTE: billing-redirect detection (?billing_updated=) is now handled
 * globally by AppFooter.vue so we don't re-trigger it on every page.
 */
import { onMounted, onUnmounted, ref, watch } from "vue";
import { useAuth } from "../composables/useAuth";
import { useDsrPortal } from "../composables/useDsrPortal";
// Audit fix TS-12: removed `authHelpers` import — no longer used after
// removing the `authHelpers.getRefreshToken()` check (the refresh token
// is now in an httpOnly cookie that JS cannot read).

const props = defineProps<{
  requireAuth?: boolean;
}>();

const { isAuthenticated, refreshUser, initialized } = useAuth();
const { dsrInPortalMode } = useDsrPortal();
const isChecking = ref(true);
const hasChecked = ref(false);

function redirectToLogin() {
  if (typeof window === "undefined") return;
  // If in DSR portal mode, send them back to DSR dashboard.
  // Audit fix C1: DSR access token is no longer in localStorage (it's in
  // memory only). Use the dsr_user key as a hint that the user was logged
  // in as a DSR on this tab.
  // Audit fix M2: previously this also checked localStorage.getItem("dsr_access_token")
  // and redirected to /dsr/dashboard if present — but that key may be stale
  // (we no longer write it). The /dsr/dashboard page itself does a server-
  // side refresh-cookie check via bootstrapDsrSession(), so sending the user
  // there is safe even if their DSR cookie has expired. We keep the
  // `dsr_user` localStorage check as a hint of previous DSR login.
  if (dsrInPortalMode.value || localStorage.getItem("dsr_user")) {
    window.location.href = "/dsr/dashboard";
  } else {
    window.location.href = "/login";
  }
}

onMounted(async () => {
  if (!props.requireAuth) {
    isChecking.value = false;
    hasChecked.value = true;
    return;
  }

  // Already authenticated — fast path
  if (isAuthenticated.value || dsrInPortalMode.value) {
    isChecking.value = false;
    hasChecked.value = true;
    return;
  }

  // Audit fix TS-12: previously this checked `authHelpers.getRefreshToken()`
  // before attempting refreshUser(). That check is now always false because
  // the refresh token lives in an httpOnly cookie that JavaScript cannot
  // read (authHelpers.getRefreshToken() always returns null post-migration).
  // We now ALWAYS attempt refreshUser() — the underlying apiClient has a
  // 401-refresh interceptor that uses credentials: 'include' to send the
  // httpOnly cookie to /auth/token/refresh-cookie.
  try {
    const user = await refreshUser();
    if (!user && !dsrInPortalMode.value) {
      redirectToLogin();
      return;
    }
  } catch {
    redirectToLogin();
    return;
  }

  isChecking.value = false;
  hasChecked.value = true;

  // Listen for session expiry events
  window.addEventListener("auth:session-expired", handleSessionExpired);
});

onUnmounted(() => {
  window.removeEventListener("auth:session-expired", handleSessionExpired);
});

function handleSessionExpired() {
  redirectToLogin();
}

// Watch for auth state changes — if user logs out, redirect
watch(isAuthenticated, (newVal, oldVal) => {
  if (hasChecked.value && oldVal && !newVal && !dsrInPortalMode.value) {
    redirectToLogin();
  }
});
</script>

<template>
  <div>
    <!-- Loading State -->
    <div
      v-if="isChecking && requireAuth"
      class="min-h-screen flex items-center justify-center bg-slate-50"
    >
      <div class="flex flex-col items-center gap-4">
        <div
          class="w-12 h-12 border-4 border-amber-200 border-t-amber-500 rounded-full animate-spin"
        ></div>
        <p class="text-slate-500 text-sm">Checking authentication…</p>
      </div>
    </div>

    <!-- Content -->
    <slot v-else />
  </div>
</template>
