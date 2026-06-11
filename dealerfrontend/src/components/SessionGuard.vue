<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue';
import { useAuth } from '../composables/useAuth';

const props = defineProps<{
  requireAuth?: boolean;
}>();

const emit = defineEmits<{
  (e: 'auth-required'): void;
  (e: 'session-restored'): void;
}>();

const { isAuthenticated, refreshUser } = useAuth();
const isChecking = ref(true);
const hasChecked = ref(false);

// Check auth status on mount
onMounted(async () => {
  if (props.requireAuth && !isAuthenticated.value) {
    // Try to restore session
    try {
      await refreshUser();
      emit('session-restored');
    } catch {
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
