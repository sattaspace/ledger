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
import { authHelpers } from "../lib/api";

const props = defineProps<{
  requireAuth?: boolean;
}>();

const { isAuthenticated, refreshUser, initialized } = useAuth();
const { dsrInPortalMode } = useDsrPortal();
const isChecking = ref(true);
const hasChecked = ref(false);

function redirectToLogin() {
  if (typeof window === "undefined") return;
  // If in DSR portal mode, send them back to DSR dashboard
  if (dsrInPortalMode.value || localStorage.getItem("dsr_access_token")) {
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

  // Try to restore session via refresh token
  if (authHelpers.getRefreshToken()) {
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
  } else if (!dsrInPortalMode.value) {
    // No refresh token and not in portal mode → redirect
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
