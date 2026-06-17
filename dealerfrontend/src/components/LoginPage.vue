<script setup lang="ts">
import { ref } from 'vue';
import { Store, TrendingUp, Shield, Zap } from 'lucide-vue-next';
import LoginForm from './LoginForm.vue';
import { redirectToBase } from '../lib/auth';

const showForgotPassword = ref(false);

// Redirect to SattaBase for account creation
function handleCreateAccount() {
  redirectToBase('/auth/register');
}

// Redirect to SattaBase for password reset
function handleForgotPassword() {
  redirectToBase('/auth/forgot-password');
}

// After successful login, navigate to /dashboard
function handleLoginSuccess() {
  window.location.href = '/dashboard';
}

// DSR login lives at /dsr/login
function showDsrLogin() {
  window.location.href = '/dsr/login';
}
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
    <div class="w-full max-w-5xl bg-white rounded-3xl shadow-2xl overflow-hidden flex">
      <!-- Left Side - Branding -->
      <div class="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-amber-500 to-amber-600 p-12 flex-col justify-between text-white">
        <div>
          <div class="flex items-center gap-3 mb-8">
            <div class="bg-white/20 p-3 rounded-2xl">
              <Store class="h-8 w-8" />
            </div>
            <span class="text-2xl font-bold">DEALERCORE</span>
          </div>
          
          <h1 class="text-4xl font-bold mb-6">
            Manage Your Dealership
          </h1>
          
          <p class="text-lg text-amber-100 mb-8">
            Complete inventory management, sales tracking, and financial reporting for modern auto dealers.
          </p>
          
          <div class="space-y-4">
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <TrendingUp class="h-5 w-5" />
              </div>
              <span>Real-time sales analytics</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <Shield class="h-5 w-5" />
              </div>
              <span>Secure cloud storage</span>
            </div>
            <div class="flex items-center gap-3">
              <div class="bg-white/20 p-2 rounded-lg">
                <Zap class="h-5 w-5" />
              </div>
              <span>Lightning fast performance</span>
            </div>
          </div>
        </div>
        
        <div class="text-sm text-amber-200">
          © 2026 DealerCore. All rights reserved.
        </div>
      </div>
      
      <!-- Right Side - Login Form -->
      <div class="w-full lg:w-1/2 p-8 md:p-12">
        <div v-if="!showForgotPassword" class="h-full flex flex-col justify-center">
          <div class="mb-8">
            <h2 class="text-2xl font-bold text-slate-800 mb-2">
              Welcome back
            </h2>
            <p class="text-slate-500">
              Sign in to access your dealership dashboard
            </p>
          </div>
          
          <LoginForm @success="handleLoginSuccess" />
          
          <div class="mt-6 text-center space-y-2">
            <p class="text-sm text-slate-500">
              Don't have an account?
              <button 
                @click="handleCreateAccount"
                class="text-blue-600 hover:text-blue-800 font-semibold"
              >
                Create account
              </button>
            </p>
            <p class="text-sm">
              <button 
                @click="handleForgotPassword"
                class="text-slate-400 hover:text-slate-600"
              >
                Forgot password?
              </button>
            </p>
            <p class="text-sm text-slate-500 pt-2 border-t border-slate-100 mt-3">
              Are you a DSR (Sales Representative)?
              <button 
                @click="showDsrLogin"
                class="text-emerald-600 hover:text-emerald-700 font-semibold"
              >
                Login here
              </button>
            </p>
          </div>
        </div>
        
        <!-- Forgot Password View -->
        <!-- Forgot Password - Redirects to SattaBase -->
        <div v-else class="h-full flex flex-col justify-center">
          <button
            @click="showForgotPassword = false"
            class="text-sm text-slate-500 hover:text-slate-700 mb-4 flex items-center gap-1"
          >
            ← Back to login
          </button>
          
          <h2 class="text-2xl font-bold text-slate-800 mb-2">
            Reset Password
          </h2>
          <p class="text-slate-500 mb-6">
            Password resets are handled securely through SattaBase.
          </p>
          
          <button
            @click="handleForgotPassword"
            class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl text-center transition-colors"
          >
            Go to Password Reset
          </button>
          
          <p class="mt-4 text-sm text-slate-400 text-center">
            You will be redirected to the SattaBase secure password reset page.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
