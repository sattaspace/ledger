<script setup lang="ts">
/**
 * DSR Login Page
 * ---------------
 * Login page for DSRs (Daily Sales Representatives).
 * Separate from dealer login which uses SattaBase.
 */
import { ref, computed } from 'vue';
import { Store, TrendingUp, Shield, Zap, Users } from 'lucide-vue-next';
import dsrAuthService, { type DealerChoice } from '../services/api/dsrAuth.service';

const emit = defineEmits<{
  (e: 'login'): void;
  (e: 'showDealerLogin'): void;
  (e: 'showDsrRegister'): void;
}>();

// Form state
const email = ref('');
const password = ref('');
const showPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref('');

// Dealer selection state
const showDealerSelection = ref(false);
const dealers = ref<DealerChoice[]>([]);
const selectedDealerUsername = ref('');
const isSelectingDealer = ref(false);

// Computed
const canSubmit = computed(() => email.value && password.value && !isLoading.value);

// Handle login
async function handleLogin() {
  if (!canSubmit.value) return;
  
  isLoading.value = true;
  errorMessage.value = '';
  
  try {
    const response = await dsrAuthService.login(email.value, password.value);
    
    if (response.require_dealer_selection) {
      // Show dealer selection
      dealers.value = response.dealers;
      showDealerSelection.value = true;
    } else {
      // Auto-selected, emit login success
      emit('login');
    }
  } catch (error: any) {
    console.error('DSR login failed:', error);
    errorMessage.value = error?.response?.data?.detail || 'Login failed. Please check your credentials.';
  } finally {
    isLoading.value = false;
  }
}

// Handle dealer selection
async function handleSelectDealer() {
  if (!selectedDealerUsername.value || isSelectingDealer.value) return;
  
  isSelectingDealer.value = true;
  errorMessage.value = '';
  
  try {
    await dsrAuthService.selectDealer(selectedDealerUsername.value);
    emit('login');
  } catch (error: any) {
    console.error('Dealer selection failed:', error);
    errorMessage.value = error?.response?.data?.detail || 'Failed to select dealer. Please try again.';
  } finally {
    isSelectingDealer.value = false;
  }
}

// Go back to login form
function goBackToLogin() {
  showDealerSelection.value = false;
  dealers.value = [];
  selectedDealerUsername.value = '';
  errorMessage.value = '';
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
            DSR Portal
          </h1>
          
          <p class="text-lg text-emerald-100 mb-8">
            Access your dealership tools, manage sales, track inventory, and collaborate with your team.
          </p>
          
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <Users class="h-5 w-5" />
              </div>
              <span>Multi-dealer support</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <TrendingUp class="h-5 w-5" />
              </div>
              <span>Real-time sales tracking</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <Shield class="h-5 w-5" />
              </div>
              <span>Secure access control</span>
            </div>
          </div>
        </div>
        
        <div class="text-sm text-emerald-200">
          © 2026 DealerCore. All rights reserved.
        </div>
      </div>
      
      <!-- Right Side - Login Form -->
      <div class="w-full lg:w-1/2 p-8 md:p-12">
        <div class="h-full flex flex-col justify-center">
          
          <!-- Dealer Selection View -->
          <template v-if="showDealerSelection">
            <div class="mb-8">
              <button
                @click="goBackToLogin"
                class="text-sm text-slate-500 hover:text-slate-700 mb-4 flex items-center gap-1"
              >
                ← Back to login
              </button>
              
              <h2 class="text-2xl font-bold text-slate-800 mb-2">
                Select Dealer
              </h2>
              <p class="text-slate-500">
                You're assigned to multiple dealers. Select one to continue.
              </p>
            </div>
            
            <!-- Error message -->
            <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {{ errorMessage }}
            </div>
            
            <!-- Dealer list -->
            <div class="space-y-3 mb-6">
              <button
                v-for="dealer in dealers"
                :key="dealer.username"
                @click="selectedDealerUsername = dealer.username"
                :class="[
                  'w-full p-4 rounded-xl border-2 text-left transition-all',
                  selectedDealerUsername === dealer.username
                    ? 'border-emerald-500 bg-emerald-50'
                    : 'border-slate-200 hover:border-slate-300'
                ]"
              >
                <div class="font-semibold text-slate-800">{{ dealer.full_name }}</div>
                <div v-if="dealer.business_name" class="text-sm text-slate-500">
                  {{ dealer.business_name }}
                </div>
              </button>
            </div>
            
            <button
              @click="handleSelectDealer"
              :disabled="!selectedDealerUsername || isSelectingDealer"
              class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              <svg v-if="isSelectingDealer" class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              {{ isSelectingDealer ? 'Selecting...' : 'Continue' }}
            </button>
          </template>
          
          <!-- Login Form View -->
          <template v-else>
            <div class="mb-8">
              <h2 class="text-2xl font-bold text-slate-800 mb-2">
                Welcome back
              </h2>
              <p class="text-slate-500">
                Sign in to access your DSR dashboard
              </p>
            </div>
            
            <!-- Error message -->
            <div v-if="errorMessage" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {{ errorMessage }}
            </div>
            
            <form @submit.prevent="handleLogin" class="space-y-5">
              <div>
                <label for="emailOrPhone" class="block text-sm font-medium text-slate-700 mb-1">
                  Email or Phone
                </label>
                <input
                  id="emailOrPhone"
                  v-model="email"
                  type="text"
                  placeholder="Enter your email or phone number"
                  class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                  required
                />
              </div>
              
              <div>
                <label for="password" class="block text-sm font-medium text-slate-700 mb-1">
                  Password
                </label>
                <div class="relative">
                  <input
                    id="password"
                    v-model="password"
                    :type="showPassword ? 'text' : 'password'"
                    placeholder="Enter your password"
                    class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all pr-12"
                    required
                  />
                  <button
                    type="button"
                    @click="showPassword = !showPassword"
                    class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <svg v-if="showPassword" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                    </svg>
                    <svg v-else class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  </button>
                </div>
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
                {{ isLoading ? 'Signing in...' : 'Sign in' }}
              </button>
            </form>
            
            <div class="mt-6 text-center space-y-2">
              <p class="text-sm text-slate-500">
                Don't have an account?
                <button 
                  @click="$emit('showDsrRegister')"
                  class="text-emerald-600 hover:text-emerald-700 font-semibold"
                >
                  Register as DSR
                </button>
              </p>
              <p class="text-sm text-slate-500">
                Are you a dealer?
                <a href="/" @click.prevent="$emit('showDealerLogin')" class="text-blue-600 hover:text-blue-800 font-semibold">
                  Login here
                </a>
              </p>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
