<script setup lang="ts">
import { ref, computed } from 'vue';
import { Mail, Lock, Loader2 } from 'lucide-vue-next';
import { useAuth } from '../composables/useAuth';

const emit = defineEmits<{
  (e: 'success'): void;
}>();

const { login, isLoading, error, clearError } = useAuth();

const email = ref('');
const password = ref('');
const showPassword = ref(false);

const isValid = computed(() => {
  return email.value.length > 0 && password.value.length >= 6;
});

async function handleSubmit() {
  if (!isValid.value || isLoading.value) return;
  
  clearError();
  
  try {
    await login({
      email: email.value,
      password: password.value,
    });
    
    emit('success');
  } catch {
    // Error is handled by useAuth
  }
}

function handleEmailInput() {
  clearError();
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Error Alert -->
    <div
      v-if="error"
      class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm"
    >
      {{ error }}
    </div>
    
    <!-- Email Field -->
    <div class="space-y-1.5">
      <label class="block text-sm font-semibold text-slate-700">
        Email Address
      </label>
      <div class="relative">
        <Mail class="absolute left-3.5 top-3.5 h-5 w-5 text-slate-400" />
        <input
          v-model="email"
          type="email"
          required
          autocomplete="email"
          placeholder="dealer@example.com"
          class="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition"
          @input="handleEmailInput"
        />
      </div>
    </div>
    
    <!-- Password Field -->
    <div class="space-y-1.5">
      <label class="block text-sm font-semibold text-slate-700">
        Password
      </label>
      <div class="relative">
        <Lock class="absolute left-3.5 top-3.5 h-5 w-5 text-slate-400" />
        <input
          v-model="password"
          :type="showPassword ? 'text' : 'password'"
          required
          autocomplete="current-password"
          placeholder="Enter your password"
          class="w-full pl-11 pr-12 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition"
          @input="handleEmailInput"
        />
        <button
          type="button"
          @click="showPassword = !showPassword"
          class="absolute right-3.5 top-3.5 text-xs text-slate-500 hover:text-slate-700 font-medium"
        >
          {{ showPassword ? 'Hide' : 'Show' }}
        </button>
      </div>
    </div>
    
    <!-- Forgot Password -->
    <div class="flex justify-end">
      <a
        href="#"
        class="text-sm text-blue-600 hover:text-blue-800 font-medium"
        @click.prevent="$emit('forgot-password')"
      >
        Forgot password?
      </a>
    </div>
    
    <!-- Submit Button -->
    <button
      type="submit"
      :disabled="!isValid || isLoading"
      class="w-full py-3.5 px-4 bg-gradient-to-r from-amber-500 to-amber-600 text-white font-semibold rounded-xl shadow-md hover:shadow-lg hover:from-amber-600 hover:to-amber-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
    >
      <Loader2 v-if="isLoading" class="h-5 w-5 animate-spin" />
      <span>{{ isLoading ? 'Signing in...' : 'Sign In' }}</span>
    </button>
  </form>
</template>
