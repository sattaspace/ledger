<script setup lang="ts">
/**
 * Manage Billing Button
 *
 * Handles SSO redirect to SattaBase for billing management.
 * Uses the authorization code flow for seamless cross-domain authentication.
 *
 * Flow:
 * 1. User clicks "Manage Billing"
 * 2. Frontend calls POST /auth/authorize to get one-time auth code
 * 3. Frontend redirects to SattaBase callback with the code
 * 4. SattaBase exchanges code for tokens, logs user in
 * 5. User manages billing on SattaBase
 */
import { ref } from 'vue';
import { CreditCard, ExternalLink, Loader2 } from 'lucide-vue-next';
import { apiClient } from '../lib/api';
import config from '../../sattabase.config';

const props = defineProps<{
  variant?: 'button' | 'link' | 'menu-item';
  openInNewTab?: boolean;
}>();

const isLoading = ref(false);
const error = ref<string | null>(null);
const showError = ref(false);

/**
 * Generate auth code and redirect to SattaBase billing
 */
async function handleBillingRedirect(targetPath: string = '/dashboard/billing'): Promise<void> {
  isLoading.value = true;
  error.value = null;

  try {
    // Get authorization code from SattaBase
    const { code } = await apiClient.post<{ code: string; expires_in: number }>('/auth/authorize');

    // Build callback URL
    const callbackUrl = `${config.baseDomainUrl}/auth/callback`;
    const params = new URLSearchParams({
      code,
      return_to: targetPath,
    });

    const redirectUrl = `${callbackUrl}?${params.toString()}`;

    // Redirect or open in new tab
    if (props.openInNewTab) {
      window.open(redirectUrl, '_blank');
    } else {
      window.location.href = redirectUrl;
    }
  } catch (err: any) {
    error.value = err.message || 'Failed to connect to billing';
    showError.value = true;
    setTimeout(() => showError.value = false, 5000);
  } finally {
    isLoading.value = false;
  }
}

async function handleClick() {
  showError.value = false;
  await handleBillingRedirect('/dashboard/billing');
}
</script>

<template>
  <div class="relative">
    <!-- Error Toast -->
    <div
      v-if="showError && error"
      class="absolute bottom-full left-0 right-0 mb-2 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded-lg text-xs"
    >
      {{ error }}
    </div>

    <!-- Button Variant -->
    <button
      v-if="variant === 'button' || !variant"
      @click="handleClick"
      :disabled="isLoading"
      class="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-500 to-blue-600 text-white text-sm font-semibold rounded-xl shadow-md hover:shadow-lg hover:from-blue-600 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
    >
      <Loader2 v-if="isLoading" class="h-4 w-4 animate-spin" />
      <CreditCard v-else class="h-4 w-4" />
      <span>{{ isLoading ? 'Connecting...' : 'Manage Billing' }}</span>
      <ExternalLink class="h-3.5 w-3.5 opacity-70" />
    </button>

    <!-- Link Variant -->
    <button
      v-else-if="variant === 'link'"
      @click="handleClick"
      :disabled="isLoading"
      class="flex items-center gap-1.5 text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
    >
      <Loader2 v-if="isLoading" class="h-3.5 w-3.5 animate-spin" />
      <CreditCard v-else class="h-3.5 w-3.5" />
      <span>{{ isLoading ? 'Connecting...' : 'Manage Billing' }}</span>
      <ExternalLink class="h-3 w-3 opacity-70" />
    </button>

    <!-- Menu Item Variant -->
    <button
      v-else-if="variant === 'menu-item'"
      @click="handleClick"
      :disabled="isLoading"
      class="w-full flex items-center gap-3 px-4 py-2.5 text-left text-slate-700 hover:bg-slate-50 rounded-lg transition-colors"
    >
      <Loader2 v-if="isLoading" class="h-4 w-4 animate-spin text-slate-400" />
      <CreditCard v-else class="h-4 w-4 text-slate-400" />
      <span class="flex-1 text-sm">{{ isLoading ? 'Connecting...' : 'Manage Billing' }}</span>
      <ExternalLink class="h-3.5 w-3.5 text-slate-400" />
    </button>
  </div>
</template>
