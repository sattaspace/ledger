<script setup lang="ts">
// Login form — Vue interactive island
// Handles POST /auth/login → stores JWT tokens via auth.ts

import { ref, reactive } from "vue";
import { login } from "@/lib/auth";
import { getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import type { ApiError } from "@/lib/api";

const form = reactive({
  email: "",
  password: "",
  remember: false,
});

const loading = ref(false);
const generalError = ref("");
const fieldErrors = reactive<Record<string, string>>({
  email: "",
  password: "",
});

function clearErrors() {
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

async function handleSubmit() {
  if (!validateForm()) return;

  loading.value = true;
  clearErrors();

  try {
    await login({ email: form.email.trim(), password: form.password });
    showToast("Welcome back! Redirecting to dashboard...", "success");
    setTimeout(() => {
      window.location.href = "/dashboard";
    }, 800);
  } catch (err: unknown) {
    const apiErr = err as ApiError;

    // Map field-level errors from API
    if (apiErr.errors) {
      for (const [field, messages] of Object.entries(apiErr.errors)) {
        if (field === "email") {
          fieldErrors.email = messages.join(" ");
        } else if (field === "password" || field === "non_field_errors") {
          fieldErrors.password = messages.join(" ");
        }
      }
    }

    // Show general error as toast and inline
    const message = getErrorMessage(err);
    generalError.value = message;
    showToast(message, "error");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6 text-center">
      <h2 class="text-2xl font-bold tracking-tight">Welcome back</h2>
      <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
        Sign in to your account to continue
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
        <label for="login-email" class="label-text">Email address</label>
        <input
          id="login-email"
          v-model="form.email"
          type="email"
          required
          autocomplete="email"
          placeholder="you@example.com"
          class="input-field"
          :class="{ 'border-red-500 ring-red-500': fieldErrors.email }"
          :aria-invalid="!!fieldErrors.email"
          :aria-describedby="fieldErrors.email ? 'login-email-error' : undefined"
          :disabled="loading"
        />
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
          <label for="login-password" class="label-text">Password</label>
          <a
            href="/auth/forgot-password"
            class="text-sm font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
          >
            Forgot password?
          </a>
        </div>
        <input
          id="login-password"
          v-model="form.password"
          type="password"
          required
          autocomplete="current-password"
          placeholder="Enter your password"
          class="input-field"
          :class="{ 'border-red-500 ring-red-500': fieldErrors.password }"
          :aria-invalid="!!fieldErrors.password"
          :aria-describedby="fieldErrors.password ? 'login-password-error' : undefined"
          :disabled="loading"
          @keyup.enter="handleSubmit"
        />
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
          class="mt-0.5 h-4 w-4 rounded border-[var(--color-input)]"
          :disabled="loading"
        />
        <label for="login-remember" class="text-sm text-[var(--color-muted-foreground)]">
          Remember me for 30 days
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

    <!-- Footer -->
    <p class="mt-6 text-center text-sm text-[var(--color-muted-foreground)]">
      Don't have an account?
      <a
        href="/auth/register"
        class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
      >
        Create one
      </a>
    </p>
  </div>
</template>
