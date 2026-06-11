<script setup lang="ts">
import { ref } from 'vue';
import { CreditCard, ExternalLink, Loader2 } from 'lucide-vue-next';
import { useSSO } from '../composables/useSSO';

const { redirectToSattaBase, openSattaBaseInNewTab, isLoading, error } = useSSO();

const props = defineProps<{
  variant?: 'button' | 'link' | 'menu-item';
  openInNewTab?: boolean;
}>();

const showError = ref(false);

async function handleClick() {
  showError.value = false;
  
  try {
    if (props.openInNewTab) {
      await openSattaBaseInNewTab();
    } else {
      await redirectToSattaBase();
    }
  } catch {
    showError.value = true;
    setTimeout(() => showError.value = false, 5000);
  }
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
