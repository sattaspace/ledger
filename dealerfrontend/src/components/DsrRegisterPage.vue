<script setup lang="ts">
/**
 * DSR Registration Page
 * ---------------------
 * Registration form for DSRs accepting invitations.
 */
import { ref, computed, onMounted } from 'vue';
import { Store, CheckCircle, AlertCircle } from 'lucide-vue-next';
import dsrAuthService from '../services/api/dsrAuth.service';

const props = defineProps<{
  token: string;
}>();

const emit = defineEmits<{
  (e: 'registered'): void;
  (e: 'showLogin'): void;
}>();

// Form state
const name = ref('');
const phone = ref('');
const password = ref('');
const confirmPassword = ref('');
const showPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');

// Invitation state
const isValidating = ref(true);
const invitationValid = ref(false);
const invitationData = ref<{
  email: string;
  role: string;
  dealer_name: string;
} | null>(null);

// Computed
const canSubmit = computed(() => {
  return name.value && 
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

// Validate invitation token on mount
onMounted(async () => {
  try {
    const response = await fetch(`/api/invitations/${props.token}`);
    const data = await response.json();
    
    if (response.ok) {
      invitationValid.value = true;
      invitationData.value = {
        email: data.email,
        role: data.role,
        dealer_name: data.dealer?.full_name || 'Unknown Dealer',
      };
    } else {
      errorMessage.value = data.detail || 'Invalid or expired invitation';
    }
  } catch (error) {
    errorMessage.value = 'Failed to validate invitation';
  } finally {
    isValidating.value = false;
  }
});

// Handle registration
async function handleRegister() {
  if (!canSubmit.value) return;
  
  isLoading.value = true;
  errorMessage.value = '';
  
  try {
    await dsrAuthService.register(
      props.token,
      name.value,
      phone.value,
      password.value
    );
    
    // Emit success event - parent will handle navigation
    emit('registered');
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
            Join the Team
          </h1>
          
          <p class="text-lg text-emerald-100 mb-8">
            You've been invited to join a dealership team. Create your account to get started.
          </p>
          
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Access sales and inventory tools</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Track your performance</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <CheckCircle class="h-5 w-5" />
              </div>
              <span>Collaborate with your team</span>
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
          
          <!-- Loading state -->
          <template v-if="isValidating">
            <div class="text-center">
              <div class="animate-spin h-12 w-12 border-4 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4"></div>
              <p class="text-slate-500">Validating invitation...</p>
            </div>
          </template>
          
          <!-- Invalid invitation -->
          <template v-else-if="!invitationValid">
            <div class="text-center">
              <div class="bg-red-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                <AlertCircle class="h-8 w-8 text-red-600" />
              </div>
              <h2 class="text-2xl font-bold text-slate-800 mb-2">Invalid Invitation</h2>
              <p class="text-slate-500 mb-6">{{ errorMessage }}</p>
              <button 
                @click="emit('showLogin')" 
                class="text-emerald-600 hover:text-emerald-700 font-semibold"
              >
                Go to login
              </button>
            </div>
          </template>
          
          <!-- Registration form -->
          <template v-else>
            <div class="mb-8">
              <h2 class="text-2xl font-bold text-slate-800 mb-2">
                Create Your Account
              </h2>
              <p class="text-slate-500">
                You've been invited by <span class="font-medium">{{ invitationData?.dealer_name }}</span> as a {{ invitationData?.role }}
              </p>
            </div>
            
            <!-- Email display -->
            <div class="mb-6 p-3 bg-slate-50 rounded-lg border border-slate-200">
              <span class="text-sm text-slate-500">Account email:</span>
              <span class="ml-2 font-medium text-slate-700">{{ invitationData?.email }}</span>
            </div>
            
            <!-- Error message -->
            <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {{ errorMessage }}
            </div>
            
            <form @submit.prevent="handleRegister" class="space-y-5">
              <div>
                <label for="name" class="block text-sm font-medium text-slate-700 mb-1">
                  Full Name
                </label>
                <input
                  id="name"
                  v-model="name"
                  type="text"
                  placeholder="Enter your full name"
                  class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  required
                />
              </div>
              
              <div>
                <label for="phone" class="block text-sm font-medium text-slate-700 mb-1">
                  Phone (optional)
                </label>
                <input
                  id="phone"
                  v-model="phone"
                  type="tel"
                  placeholder="Enter your phone number"
                  class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                />
              </div>
              
              <div>
                <label for="password" class="block text-sm font-medium text-slate-700 mb-1">
                  Password
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
                  Confirm Password
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
                {{ isLoading ? 'Creating account...' : 'Create Account' }}
              </button>
            </form>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
