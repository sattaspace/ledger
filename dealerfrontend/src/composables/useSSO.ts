/**
 * DEALERCORE v3.0 — SSO Composable
 *
 * Handles cross-domain Single Sign-On to SattaBase.
 */

import { ref } from 'vue';
import { getAccessToken } from '../lib/auth';

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8088/api';

/**
 * SSO composable for navigating to SattaBase
 * 
 * @example
 * ```vue
 * <script setup>
 * const { redirectToSattaBase, isLoading, error } = useSSO();
 * 
 * async function handleManageBilling() {
 *   await redirectToSattaBase();
 * }
 * </script>
 * ```
 */
export function useSSO() {
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  /**
   * Redirect user to SattaBase via SSO
   * 
   * 1. Gets authorization code from dealerbackend
   * 2. Redirects to SattaBase with the code
   * 3. SattaBase validates and logs user in
   */
  async function redirectToSattaBase(): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      const token = getAccessToken();
      
      if (!token) {
        throw new Error('Not authenticated');
      }

      // Get SSO redirect URL from backend
      const response = await fetch(`${API_BASE_URL}/sso/sattabase`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to generate SSO link');
      }

      const { redirectUrl } = await response.json();
      
      // Redirect to SattaBase
      window.location.href = redirectUrl;
      
    } catch (err: any) {
      error.value = err.message || 'SSO failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Open SattaBase in new tab via SSO
   */
  async function openSattaBaseInNewTab(): Promise<void> {
    isLoading.value = true;
    error.value = null;

    try {
      const token = getAccessToken();
      
      if (!token) {
        throw new Error('Not authenticated');
      }

      const response = await fetch(`${API_BASE_URL}/sso/sattabase`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to generate SSO link');
      }

      const { redirectUrl } = await response.json();
      
      // Open in new tab
      window.open(redirectUrl, '_blank');
      
    } catch (err: any) {
      error.value = err.message || 'SSO failed';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * Clear error
   */
  function clearError(): void {
    error.value = null;
  }

  return {
    isLoading,
    error,
    redirectToSattaBase,
    openSattaBaseInNewTab,
    clearError,
  };
}
