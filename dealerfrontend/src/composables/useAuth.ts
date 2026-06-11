/**
 * DEALERCORE v3.0 — Authentication Composable
 *
 * Vue 3 composable for reactive authentication state.
 * Uses the auth library for operations.
 */

import { ref, computed, onMounted, onUnmounted } from 'vue';
import type { User, LoginCredentials } from '../lib/auth';
import * as auth from '../lib/auth';

/**
 * Authentication composable
 * 
 * @example
 * ```vue
 * <script setup>
 * const { user, isAuthenticated, login, logout, isLoading, error } = useAuth();
 * </script>
 * ```
 */
export function useAuth() {
  // Local reactive state
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  
  // Track authenticated state locally for immediate reactivity
  const _isAuthenticated = ref(auth.isAuthenticated());
  
  // Computed from auth library
  const user = computed(() => auth.authState.user.value);
  const isAuthenticated = computed({
    get: () => _isAuthenticated.value || auth.authState.isAuthenticated.value,
    set: (val) => { _isAuthenticated.value = val; }
  });
  
  /**
   * Login with email/password
   */
  async function login(credentials: LoginCredentials): Promise<void> {
    isLoading.value = true;
    error.value = null;
    
    try {
      await auth.login(credentials);
      _isAuthenticated.value = true;  // Set immediately for reactivity
      auth.startAutoRefresh();
    } catch (err: any) {
      error.value = err.message || 'Login failed';
      _isAuthenticated.value = false;
      throw err;
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * Logout user
   */
  async function logout(): Promise<void> {
    isLoading.value = true;
    
    try {
      auth.stopAutoRefresh();
      await auth.logout();
      _isAuthenticated.value = false;  // Clear immediately
    } finally {
      isLoading.value = false;
    }
  }
  
  /**
   * Refresh user data from server
   */
  async function refreshUser(): Promise<void> {
    try {
      await auth.getMe();
      _isAuthenticated.value = auth.isAuthenticated();  // Sync state
    } catch (err: any) {
      error.value = err.message;
      _isAuthenticated.value = false;
      throw err;
    }
  }
  
  /**
   * Clear error message
   */
  function clearError(): void {
    error.value = null;
  }
  
  // Auto-refresh on mount if authenticated
  onMounted(() => {
    if (isAuthenticated.value) {
      auth.startAutoRefresh();
    }
  });
  
  // Stop refresh on unmount
  onUnmounted(() => {
    auth.stopAutoRefresh();
  });
  
  return {
    // State
    user,
    isAuthenticated,
    isLoading: readonly(isLoading),
    error: readonly(error),
    
    // Actions
    login,
    logout,
    refreshUser,
    clearError,
  };
}

// Make readonly helper
function readonly<T>(ref: { value: T }) {
  return computed(() => ref.value);
}
