<script setup lang="ts">
/**
 * Session Guard Component
 *
 * Wraps protected routes and ensures user is authenticated.
 * Also handles billing return detection for automatic profile refresh.
 *
 * Usage:
 * ```vue
 * <SessionGuard require-auth @auth-required="handleLogout" @session-restored="handleRestore">
 *   <ProtectedContent />
 * </SessionGuard>
 * ```
 */
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useAuth } from '../composables/useAuth';
import { useBillingRedirect } from '../composables/useBillingRedirect';

const props = defineProps<{
  requireAuth?: boolean;
}>();

const emit = defineEmits<{
  (e: 'auth-required'): void;
  (e: 'session-restored'): void;
  // FIX L-17: surface billing return result so the parent can show a
  // success/failure toast. Previously billingSuccess was silently
  // discarded after useAuth refetched the profile.
  (e: 'billing-returned', success: boolean | null): void;
}>();

const { isAuthenticated, refreshUser } = useAuth();
const { checkBillingRedirect, isBillingReturn, billingSuccess } = useBillingRedirect();
const isChecking = ref(true);
const hasChecked = ref(false);

// Check auth status on mount
onMounted(async () => {
  // Check for billing return first
  checkBillingRedirect();

  if (props.requireAuth && !isAuthenticated.value) {
    // Try to restore session.
    // FIX B-8: previously wrapped refreshUser() in try/catch, but
    // refreshUser() swallows its own errors and returns null on failure,
    // so the catch block was dead code — `session-restored` was emitted
    // even on auth failure. Now check the return value explicitly.
    const user = await refreshUser();
    if (user) {
      emit('session-restored');
    } else {
      emit('auth-required');
    }
  }

  isChecking.value = false;
  hasChecked.value = true;

  // Listen for session expiry events
  window.addEventListener('auth:session-expired', handleSessionExpired);
});

onUnmounted(() => {
  window.removeEventListener('auth:session-expired', handleSessionExpired);
});

function handleSessionExpired() {
  emit('auth-required');
}

// Watch for auth state changes
watch(isAuthenticated, (newVal, oldVal) => {
  if (hasChecked.value && oldVal && !newVal) {
    // User just logged out or session expired
    emit('auth-required');
  }
});

// FIX L-17: when useBillingRedirect detects a return from the SattaBase
// billing flow, surface it as an event the parent can render as a toast.
// Without this watcher, the user is silently redirected back into the
// app with no acknowledgement of what just happened.
watch(billingSuccess, (success) => {
  if (success !== null) emit('billing-returned', success);
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
        <div class="w-12 h-12 border-4 border-amber-200 border-t-amber-500 rounded-full animate-spin"></div>
        <p class="text-slate-500 text-sm">Checking authentication...</p>
      </div>
    </div>
    
    <!-- Content -->
    <slot v-else />
  </div>
</template>
