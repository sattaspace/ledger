<script setup lang="ts">
/**
 * LoginForm — Vue interactive island for the Ledger sister domain login page.
 */

import { ref, reactive } from "vue";
import { useAuth } from "@/composables/useAuth";
import { redirectToBase } from "@/lib/auth";
import { getErrorMessage } from "@/lib/auth";
import type { ApiError } from "@/lib/types";

const { login } = useAuth();

const form = reactive({
  email: "",
  password: "",
  remember: false,
});

const loading = ref(false);
const generalError = ref("");
const fieldErrors = reactive({
  email: "",
  password: "",
});

function clearErrors(): void {
  generalError.value = "";
  fieldErrors.email = "";
  fieldErrors.password = "";
}

function validateForm(): boolean {
  clearErrors();

  if (!form.email.trim()) {
    fieldErrors.email = "Email address is required.";
    return false;
  }

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(form.email)) {
    fieldErrors.email = "Please enter a valid email address.";
    return false;
  }

  if (!form.password) {
    fieldErrors.password = "Password is required.";
    return false;
  }

  return true;
}

async function handleSubmit(): Promise<void> {
  if (!validateForm()) return;

  loading.value = true;
  clearErrors();

  try {
    await login(form.email.trim(), form.password, form.remember);
    // Redirect to return_url if provided, otherwise default to dashboard
    const params = new URLSearchParams(window.location.search);
    const returnUrl = params.get("return_url");
    if (returnUrl && returnUrl.startsWith("/")) {
      window.location.href = returnUrl;
    } else {
      window.location.href = "/dashboard";
    }
  } catch (err: unknown) {
    const apiErr = err as ApiError;

    if (apiErr.errors) {
      for (const [key, messages] of Object.entries(apiErr.errors)) {
        if (key in fieldErrors && messages.length > 0) {
          (fieldErrors as Record<string, string>)[key] = messages[0];
        }
      }
    }

    const message = getErrorMessage(err);
    generalError.value = message;
  } finally {
    loading.value = false;
  }
}

function goToRegister(): void {
  redirectToBase("/auth/register");
}

function goToForgotPassword(): void {
  redirectToBase("/auth/forgot-password");
}
</script>

<template>
  <div>
    <!-- Header with icon -->
    <div class="mb-6 text-center">
      <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-cyan-100 dark:bg-cyan-950">
        <svg class="h-8 w-8 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
        </svg>
      </div>
      <h2 class="text-2xl font-bold tracking-tight text-navy-900 dark:text-navy-100">Welcome back</h2>
      <p class="mt-2 text-sm text-slate-custom-700 dark:text-slate-custom-400">
        Sign in to your Satta Ledger account
      </p>
    </div>

    <!-- General Error Alert -->
    <div
      v-if="generalError"
      role="alert"
      class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
    >
      {{ generalError }}
    </div>

    <!-- Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Email -->
      <div class="space-y-2">
        <label for="login-email" class="text-sm font-medium text-navy-900 dark:text-navy-100">Email address</label>
        <div class="relative">
          <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <svg class="h-4 w-4 text-slate-custom-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <input
            id="login-email"
            v-model="form.email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
            class="input-field pl-10"
            :class="{ 'border-red-500 ring-red-500': fieldErrors.email }"
            :aria-invalid="!!fieldErrors.email"
            :aria-describedby="fieldErrors.email ? 'login-email-error' : undefined"
            :disabled="loading"
          />
        </div>
        <p
          v-if="fieldErrors.email"
          id="login-email-error"
          class="text-xs text-red-500"
          role="alert"
        >
          {{ fieldErrors.email }}
        </p>
      </div>

      <!-- Password -->
      <div class="space-y-2">
        <div class="flex items-center justify-between">
          <label for="login-password" class="text-sm font-medium text-navy-900 dark:text-navy-100">Password</label>
          <button
            type="button"
            class="text-sm font-medium text-cyan-600 hover:text-cyan-500 dark:text-cyan-400"
            @click="goToForgotPassword"
          >
            Forgot password?
          </button>
        </div>
        <div class="relative">
          <div class="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
            <svg class="h-4 w-4 text-slate-custom-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <input
            id="login-password"
            v-model="form.password"
            type="password"
            required
            autocomplete="current-password"
            placeholder="Enter your password"
            class="input-field pl-10"
            :class="{ 'border-red-500 ring-red-500': fieldErrors.password }"
            :aria-invalid="!!fieldErrors.password"
            :aria-describedby="fieldErrors.password ? 'login-password-error' : undefined"
            :disabled="loading"
            @keyup.enter="handleSubmit"
          />
        </div>
        <p
          v-if="fieldErrors.password"
          id="login-password-error"
          class="text-xs text-red-500"
          role="alert"
        >
          {{ fieldErrors.password }}
        </p>
      </div>

      <!-- Remember Me -->
      <div class="flex items-center gap-2">
        <input
          id="login-remember"
          v-model="form.remember"
          type="checkbox"
          class="mt-0.5 h-4 w-4 rounded border-slate-custom-500"
          :disabled="loading"
        />
        <label for="login-remember" class="text-sm text-slate-custom-700 dark:text-slate-custom-400">
          Remember me
        </label>
      </div>

      <!-- Submit -->
      <button
        type="submit"
        :disabled="loading"
        class="btn-primary w-full"
        aria-label="Sign in to your account"
      >
        <svg
          v-if="loading"
          class="h-4 w-4 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ loading ? "Signing in..." : "Sign in" }}
      </button>
    </form>

    <!-- Footer with base domain redirects -->
    <p class="mt-6 text-center text-sm text-slate-custom-700 dark:text-slate-custom-400">
      Don't have an account?
      <button
        type="button"
        class="font-medium text-cyan-600 hover:text-cyan-500 dark:text-cyan-400"
        @click="goToRegister"
      >
        Create one
      </button>
    </p>
  </div>
</template>
