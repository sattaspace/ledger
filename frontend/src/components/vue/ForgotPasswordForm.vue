<script setup lang="ts">
// Forgot password — Vue interactive island
// Handles POST /auth/password-reset/request via auth.ts

import { ref, reactive } from "vue";
import { requestPasswordReset } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import { getErrorMessage } from "@/lib/auth";

const form = reactive({
  email: "",
});

const loading = ref(false);
const error = ref("");
const sent = ref(false);

function validateForm(): boolean {
  error.value = "";

  if (!form.email.trim()) {
    error.value = "Email address is required.";
    return false;
  }

  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailPattern.test(form.email)) {
    error.value = "Please enter a valid email address.";
    return false;
  }

  return true;
}

async function handleSubmit() {
  if (!validateForm()) return;

  error.value = "";
  loading.value = true;

  try {
    await requestPasswordReset(form.email.trim());
    sent.value = true;
    showToast("Password reset email sent successfully.", "success");
  } catch (err: unknown) {
    // For security, still show the "sent" state even on error
    // so we don't leak whether an email exists
    sent.value = true;
    showToast("If an account with that email exists, a reset link has been sent.", "info");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div>
    <!-- Sent state -->
    <div v-if="sent" class="text-center">
      <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-950">
        <svg class="h-8 w-8 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <h2 class="text-2xl font-bold tracking-tight">Check your email</h2>
      <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
        If an account with <strong>{{ form.email }}</strong> exists, we've sent a password reset link.
      </p>

      <!-- Checklist -->
      <div class="mt-4 mx-auto max-w-xs text-left space-y-2">
        <div class="flex items-start gap-2 text-sm text-[var(--color-muted-foreground)]">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4" />
          </svg>
          <span>Click the reset link in the email to set a new password</span>
        </div>
        <div class="flex items-start gap-2 text-sm text-[var(--color-muted-foreground)]">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4" />
          </svg>
          <span>The link expires in 24 hours</span>
        </div>
        <div class="flex items-start gap-2 text-sm text-[var(--color-muted-foreground)]">
          <svg class="mt-0.5 h-4 w-4 shrink-0 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4" />
          </svg>
          <span>Check your spam or junk folder if you don't see it</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="mt-6 flex flex-col items-center gap-3">
        <a href="/auth/login" class="btn-primary inline-flex" aria-label="Return to sign in page">
          Back to sign in
        </a>
        <p class="text-xs text-[var(--color-muted-foreground)]">
          Didn't receive it?
          <button
            type="button"
            class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
            @click="sent = false"
          >
            Try again
          </button>
        </p>
      </div>

      <!-- Manual token entry -->
      <div class="mt-4 pt-4 border-t border-[var(--color-border)]">
        <p class="text-xs text-[var(--color-muted-foreground)]">
          Have a reset token?
          <a
            href="/auth/reset-password"
            class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
          >
            Enter it manually
          </a>
        </p>
      </div>
    </div>

    <!-- Form state -->
    <div v-else>
      <div class="mb-6 text-center">
        <h2 class="text-2xl font-bold tracking-tight">Forgot password?</h2>
        <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
          Enter your email and we'll send you a reset link
        </p>
      </div>

      <div
        v-if="error"
        role="alert"
        class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
      >
        {{ error }}
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div class="space-y-2">
          <label for="forgot-email" class="label-text">Email address</label>
          <input
            id="forgot-email"
            v-model="form.email"
            type="email"
            required
            autocomplete="email"
            placeholder="you@example.com"
            class="input-field"
            :aria-invalid="!!error"
            :aria-describedby="error ? 'forgot-email-error' : undefined"
            :disabled="loading"
          />
          <p
            v-if="error"
            id="forgot-email-error"
            class="text-xs text-red-500"
            role="alert"
          >
            {{ error }}
          </p>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="btn-primary w-full"
          aria-label="Send password reset link"
        >
          <svg v-if="loading" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ loading ? "Sending..." : "Send reset link" }}
        </button>
      </form>

      <!-- Manual token entry link -->
      <div class="mt-4 pt-4 border-t border-[var(--color-border)]">
        <p class="text-center text-xs text-[var(--color-muted-foreground)]">
          Already have a reset token?
          <a
            href="/auth/reset-password"
            class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
          >
            Enter it here
          </a>
        </p>
      </div>

      <p class="mt-6 text-center text-sm text-[var(--color-muted-foreground)]">
        Remember your password?
        <a href="/auth/login" class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400">Sign in</a>
      </p>
    </div>
  </div>
</template>
