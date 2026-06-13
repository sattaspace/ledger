<script setup lang="ts">
/**
 * DSR Self-Registration Page
 * ---------------------------
 * Allows DSRs to register independently (without an invitation).
 * After registration, they can receive invitations from dealers.
 */
import { ref, computed } from 'vue';
import { Store, CheckCircle, UserPlus, AlertCircle } from 'lucide-vue-next';
import dsrAuthService from '../services/api/dsrAuth.service';

const emit = defineEmits<{
  (e: 'registered'): void;
  (e: 'showDsrLogin'): void;
}>();

// Form state
const fullName = ref('');
const phone = ref('');
const email = ref('');
const password = ref('');
const confirmPassword = ref('');
const isLoading = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

// Computed
const canSubmit = computed(() => {
  return fullName.value && 
         phone.value && 
         password.value && 
         confirmPassword.value && 
         password.value === confirmPassword.value &&
         password.value.length >= 8 &&
         !isLoading.value;
});

const passwordMismatch = computed(() => {
  return confirmPassword.value && password.value !== confirmPassword.value;
});

const passwordTooShort = computed(() => {
  return password.value && password.value.length < 8;
});

// Handle registration
async function handleRegister() {
  if (!canSubmit.value) return;
  
  isLoading.value = true;
  errorMessage.value = '';
  successMessage.value = '';
  
  try {
    const response = await dsrAuthService.selfRegister(
      phone.value,
      fullName.value,
      password.value,
      email.value || undefined
    );
    
    successMessage.value = 'Registration successful! You can now receive invitations from dealers.';
    
    // Emit registered event after a short delay
    setTimeout(() => {
      emit('registered');
    }, 1500);
  } catch (error: any) {
    console.error('Registration failed:', error);
    errorMessage.value = error?.response?.data?.detail || 'Registration failed. Please try again.';
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
    <div class="w-full max-w-5xl bg-white rounded-3xl shadow-2xl overflow-hidden flex">
      <!-- Left Side - Branding -->
      <div class="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-emerald-500 to-emerald-600 p-12 flex-col justify-between text-white">
        <div>
          <div class="flex items-center gap-3 mb-8">
            <div class="bg-white/20 p-3 rounded-2xl">
              <Store class="h-8 w-8" />
            </div>
            <span class="text-2xl font-bold">DEALERCORE</span>
          </div>
          
          <h1 class="text-4xl font-bold mb-6">
            Join as a DSR
          </h1>
          
          <p class="text-lg text-emerald-100 mb-8">
            Create your independent DSR profile. Receive invitations from multiple dealers and choose who to work with.
          </p>
          
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Independent profile - you own your data</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Work with multiple dealers</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Accept or reject invitations</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Track your sales and performance</span>
            </div>
          </div>
        </div>
        
        <div class="text-sm text-emerald-200">
          © 2026 DealerCore. All rights reserved.
        </div>
      </div>
      
      <!-- Right Side - Registration Form -->
      <div class="w-full lg:w-1/2 p-8 md:p-12">
        <div class="h-full flex flex-col justify-center">
          <div class="mb-8">
            <h2 class="text-2xl font-bold text-slate-800 mb-2">
              Create Your DSR Profile
            </h2>
            <p class="text-slate-500">
              Register to receive dealer invitations and manage your sales career.
            </p>
          </div>
          
          <!-- Success message -->
          <div v-if="successMessage" class="mb-4 p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-3">
            <CheckCircle class="h-5 w-5 text-emerald-600 shrink-0" />
            <p class="text-emerald-700">{{ successMessage }}</p>
          </div>
          
          <!-- Error message -->
          <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-center gap-2">
            <AlertCircle class="h-4 w-4 shrink-0" />
            {{ errorMessage }}
          </div>
          
          <form @submit.prevent="handleRegister" class="space-y-5">
            <div>
              <label for="fullName" class="block text-sm font-medium text-slate-700 mb-1">
                Full Name <span class="text-red-500">*</span>
              </label>
              <input
                id="fullName"
                v-model="fullName"
                type="text"
                placeholder="Enter your full name"
                class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                required
              />
            </div>
            
            <div>
              <label for="phone" class="block text-sm font-medium text-slate-700 mb-1">
                Phone Number <span class="text-red-500">*</span>
              </label>
              <input
                id="phone"
                v-model="phone"
                type="tel"
                placeholder="Enter your phone number"
                class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                required
              />
              <p class="mt-1 text-xs text-slate-500">This will be your primary identifier</p>
            </div>
            
            <div>
              <label for="email" class="block text-sm font-medium text-slate-700 mb-1">
                Email (optional)
              </label>
              <input
                id="email"
                v-model="email"
                type="email"
                placeholder="Enter your email"
                class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
              />
            </div>
            
            <div>
              <label for="password" class="block text-sm font-medium text-slate-700 mb-1">
                Password <span class="text-red-500">*</span>
              </label>
              <input
                id="password"
                v-model="password"
                type="password"
                placeholder="Create a password (min 8 characters)"
                class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                :class="{ 'border-red-500': passwordTooShort }"
                required
              />
              <p v-if="passwordTooShort" class="mt-1 text-sm text-red-600">
                Password must be at least 8 characters
              </p>
            </div>
            
            <div>
              <label for="confirmPassword" class="block text-sm font-medium text-slate-700 mb-1">
                Confirm Password <span class="text-red-500">*</span>
              </label>
              <input
                id="confirmPassword"
                v-model="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                :class="{ 'border-red-500': passwordMismatch }"
                required
              />
              <p v-if="passwordMismatch" class="mt-1 text-sm text-red-600">
                Passwords do not match
              </p>
            </div>
            
            <button
              type="submit"
              :disabled="!canSubmit"
              class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <svg v-if="isLoading" class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              <UserPlus v-else class="h-5 w-5" />
              {{ isLoading ? 'Creating account...' : 'Create DSR Account' }}
            </button>
          </form>
          
          <div class="mt-6 text-center space-y-2">
            <p class="text-sm text-slate-500">
              Already have an account?
              <button 
                @click="$emit('showDsrLogin')"
                class="text-emerald-600 hover:text-emerald-700 font-semibold"
              >
                Sign in
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
