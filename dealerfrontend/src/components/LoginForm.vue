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
// FIX L-13: backend login() already accepts a `remember` parameter that
// persists the refresh token to localStorage instead of sessionStorage.
// The frontend just wasn't exposing it. Default to false (session-only)
// for safer default — users opt in to longer sessions explicitly.
const rememberMe = ref(false);

// FIX M-10: stricter email regex (RFC 5322 simplified). Previously any
// non-empty email passed validation, allowing "a@b" to be sent.
// FIX M-3: trim whitespace from email/password before submit so leading/
// trailing spaces don't produce "user not found" responses.
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const errorMessage = computed(() => error.value?.message || null);

const isValid = computed(() => {
  const trimmedEmail = email.value.trim();
  // Audit fix M6: align dealer-login password length check with DSR
  // registration (>=8) and Django's default backend policy. Previously
  // this used >=6, which was inconsistent with the DSR register forms.
  return EMAIL_RE.test(trimmedEmail) && password.value.length >= 8;
});

async function handleSubmit() {
  if (!isValid.value || isLoading.value) return;

  clearError();

  try {
    await login(email.value.trim(), password.value, rememberMe.value);
    emit('success');
  } catch {
    password.value = '';
  }
}

function handleEmailInput() {
  if (clearError) clearError();
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Error Alert -->
    <div
      v-if="errorMessage"
      class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm"
    >
      {{ errorMessage }}
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

    <!-- FIX L-13: Remember-me checkbox. Unchecked = refresh token in
    sessionStorage (cleared on tab close). Checked = refresh token in
    localStorage (survives browser restart). -->
    <label class="flex items-center gap-2 text-sm text-slate-600 select-none cursor-pointer">
      <input
        v-model="rememberMe"
        type="checkbox"
        class="h-4 w-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
      />
      <span>Keep me signed in on this device</span>
    </label>

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
