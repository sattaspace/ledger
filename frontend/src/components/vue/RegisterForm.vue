<script setup lang="ts">
// Register form — Vue interactive island
// Handles POST /auth/register via auth.ts

import { ref, reactive, computed, onMounted } from "vue";
import {
  register,
  getErrorMessage,
  TIMEZONE_OPTIONS,
  CURRENCY_OPTIONS,
  LANGUAGE_OPTIONS,
  detectUserTimezone,
  detectUserLanguage,
} from "@/lib/auth";
import { showToast } from "@/lib/toast";
import type { ApiError } from "@/lib/api";

const form = reactive({
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  confirm_password: "",
  timezone: "UTC",
  currency: "USD",
  language: "en",
  agree_terms: false,
});

const loading = ref(false);
const generalError = ref("");
const fieldErrors = reactive<Record<string, string>>({
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  confirm_password: "",
  agree_terms: "",
});

// Auto-detect preferences on mount
onMounted(() => {
  form.timezone = detectUserTimezone();
  form.language = detectUserLanguage();
});

// Collapsible preferences section
const showPreferences = ref(false);

// Password strength computation
const passwordChecks = computed(() => {
  const pw = form.password;
  return {
    length: pw.length >= 8,
    uppercase: /[A-Z]/.test(pw),
    lowercase: /[a-z]/.test(pw),
    number: /[0-9]/.test(pw),
    special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`;\']/.test(pw),
  };
});

const passwordStrength = computed(() => {
  const checks = Object.values(passwordChecks.value);
  const passed = checks.filter(Boolean).length;
  if (form.password.length === 0) return { level: 0, label: "", color: "" };
  if (passed <= 2) return { level: 1, label: "Weak", color: "bg-red-500" };
  if (passed <= 3) return { level: 2, label: "Fair", color: "bg-yellow-500" };
  if (passed <= 4) return { level: 3, label: "Good", color: "bg-brand-400" };
  return { level: 4, label: "Strong", color: "bg-brand-600" };
});

const strengthSegments = [0, 1, 2, 3];

function clearErrors() {
  generalError.value = "";
  Object.keys(fieldErrors).forEach((key) => {
    fieldErrors[key] = "";
  });
}

function validateForm(): boolean {
  clearErrors();
  let valid = true;

  if (!form.first_name.trim()) {
    fieldErrors.first_name = "First name is required.";
    valid = false;
  }

  if (!form.email.trim()) {
    fieldErrors.email = "Email address is required.";
    valid = false;
  } else {
    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(form.email)) {
      fieldErrors.email = "Please enter a valid email address.";
      valid = false;
    }
  }

  const checks = Object.values(passwordChecks.value);
  if (checks.some((c) => !c)) {
    fieldErrors.password = "Password does not meet all requirements.";
    valid = false;
  }

  if (form.password !== form.confirm_password) {
    fieldErrors.confirm_password = "Passwords do not match.";
    valid = false;
  }

  if (!form.agree_terms) {
    fieldErrors.agree_terms = "You must agree to the terms and conditions.";
    valid = false;
  }

  return valid;
}

async function handleSubmit() {
  if (!validateForm()) return;

  loading.value = true;
  clearErrors();

  try {
    await register({
      email: form.email.trim(),
      password: form.password,
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      timezone: form.timezone,
      currency: form.currency,
      language: form.language,
    });

    showToast("Account created successfully! Please verify your email.", "success");
    // Redirect to email verification page with the registered email
    setTimeout(() => {
      window.location.href = `/auth/verify-email?email=${encodeURIComponent(form.email.trim())}`;
    }, 1500);
  } catch (err: unknown) {
    const apiErr = err as ApiError;

    // Map field-level errors from API
    if (apiErr.errors) {
      for (const [field, messages] of Object.entries(apiErr.errors)) {
        if (field in fieldErrors) {
          fieldErrors[field] = messages.join(" ");
        }
      }
    }

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
      <h2 class="text-2xl font-bold tracking-tight">Create an account</h2>
      <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
        Start managing your finances with Satta Ledger
      </p>
    </div>

    <!-- General Error -->
    <div
      v-if="generalError"
      role="alert"
      class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
    >
      {{ generalError }}
    </div>

    <!-- Form -->
    <form @submit.prevent="handleSubmit" class="space-y-4">
      <!-- Name Row -->
      <div class="grid grid-cols-2 gap-3">
        <div class="space-y-2">
          <label for="reg-first" class="label-text">First name</label>
          <input
            id="reg-first"
            v-model="form.first_name"
            type="text"
            required
            autocomplete="given-name"
            placeholder="John"
            class="input-field"
            :class="{ 'border-red-500 ring-red-500': fieldErrors.first_name }"
            :aria-invalid="!!fieldErrors.first_name"
            :aria-describedby="fieldErrors.first_name ? 'reg-first-error' : undefined"
            :disabled="loading"
          />
          <p
            v-if="fieldErrors.first_name"
            id="reg-first-error"
            class="text-xs text-red-500"
            role="alert"
          >
            {{ fieldErrors.first_name }}
          </p>
        </div>
        <div class="space-y-2">
          <label for="reg-last" class="label-text">Last name</label>
          <input
            id="reg-last"
            v-model="form.last_name"
            type="text"
            autocomplete="family-name"
            placeholder="Doe"
            class="input-field"
            :disabled="loading"
          />
        </div>
      </div>

      <!-- Email -->
      <div class="space-y-2">
        <label for="reg-email" class="label-text">Email address</label>
        <input
          id="reg-email"
          v-model="form.email"
          type="email"
          required
          autocomplete="email"
          placeholder="you@example.com"
          class="input-field"
          :class="{ 'border-red-500 ring-red-500': fieldErrors.email }"
          :aria-invalid="!!fieldErrors.email"
          :aria-describedby="fieldErrors.email ? 'reg-email-error' : undefined"
          :disabled="loading"
        />
        <p
          v-if="fieldErrors.email"
          id="reg-email-error"
          class="text-xs text-red-500"
          role="alert"
        >
          {{ fieldErrors.email }}
        </p>
      </div>

      <!-- Password -->
      <div class="space-y-2">
        <label for="reg-password" class="label-text">Password</label>
        <input
          id="reg-password"
          v-model="form.password"
          type="password"
          required
          autocomplete="new-password"
          placeholder="Create a strong password"
          class="input-field"
          :class="{ 'border-red-500 ring-red-500': fieldErrors.password }"
          :aria-invalid="!!fieldErrors.password"
          :aria-describedby="fieldErrors.password ? 'reg-password-error' : 'reg-password-strength'"
          :disabled="loading"
        />
        <p
          v-if="fieldErrors.password"
          id="reg-password-error"
          class="text-xs text-red-500"
          role="alert"
        >
          {{ fieldErrors.password }}
        </p>

        <!-- Password Strength Bar -->
        <div v-if="form.password.length > 0" id="reg-password-strength" class="space-y-2">
          <div class="flex items-center gap-2">
            <div class="flex flex-1 gap-1">
              <div
                v-for="i in strengthSegments"
                :key="i"
                class="h-1.5 flex-1 rounded-full transition-colors duration-300"
                :class="passwordStrength.level > i ? passwordStrength.color : 'bg-[var(--color-border)]'"
              ></div>
            </div>
            <span
              class="text-xs font-medium transition-colors duration-300"
              :class="{
                'text-red-500': passwordStrength.level === 1,
                'text-yellow-500': passwordStrength.level === 2,
                'text-brand-400': passwordStrength.level === 3,
                'text-brand-600': passwordStrength.level === 4,
              }"
            >
              {{ passwordStrength.label }}
            </span>
          </div>

          <!-- Password strength hints -->
          <ul class="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs transition-all duration-300">
            <li
              :class="passwordChecks.length ? 'text-brand-600 dark:text-brand-400' : 'text-[var(--color-muted-foreground)]'"
              class="transition-colors duration-200"
            >
              {{ passwordChecks.length ? '✓' : '○' }} 8+ characters
            </li>
            <li
              :class="passwordChecks.uppercase ? 'text-brand-600 dark:text-brand-400' : 'text-[var(--color-muted-foreground)]'"
              class="transition-colors duration-200"
            >
              {{ passwordChecks.uppercase ? '✓' : '○' }} Uppercase letter
            </li>
            <li
              :class="passwordChecks.lowercase ? 'text-brand-600 dark:text-brand-400' : 'text-[var(--color-muted-foreground)]'"
              class="transition-colors duration-200"
            >
              {{ passwordChecks.lowercase ? '✓' : '○' }} Lowercase letter
            </li>
            <li
              :class="passwordChecks.number ? 'text-brand-600 dark:text-brand-400' : 'text-[var(--color-muted-foreground)]'"
              class="transition-colors duration-200"
            >
              {{ passwordChecks.number ? '✓' : '○' }} Number
            </li>
            <li
              :class="passwordChecks.special ? 'text-brand-600 dark:text-brand-400' : 'text-[var(--color-muted-foreground)]'"
              class="transition-colors duration-200"
            >
              {{ passwordChecks.special ? '✓' : '○' }} Special character
            </li>
          </ul>
        </div>
      </div>

      <!-- Confirm Password -->
      <div class="space-y-2">
        <label for="reg-confirm" class="label-text">Confirm password</label>
        <input
          id="reg-confirm"
          v-model="form.confirm_password"
          type="password"
          required
          autocomplete="new-password"
          placeholder="Re-enter your password"
          class="input-field"
          :class="{
            'border-red-500 ring-red-500': fieldErrors.confirm_password || (form.confirm_password && form.password !== form.confirm_password)
          }"
          :aria-invalid="!!(fieldErrors.confirm_password || (form.confirm_password && form.password !== form.confirm_password))"
          :aria-describedby="
            fieldErrors.confirm_password ? 'reg-confirm-error' :
            (form.confirm_password && form.password !== form.confirm_password) ? 'reg-confirm-mismatch' : undefined
          "
          :disabled="loading"
        />
        <p
          v-if="fieldErrors.confirm_password"
          id="reg-confirm-error"
          class="text-xs text-red-500"
          role="alert"
        >
          {{ fieldErrors.confirm_password }}
        </p>
        <p
          v-else-if="form.confirm_password && form.password !== form.confirm_password"
          id="reg-confirm-mismatch"
          class="text-xs text-red-500"
        >
          Passwords do not match
        </p>
      </div>

      <!-- Preferences (Collapsible) -->
      <div class="rounded-lg border border-[var(--color-border)]">
        <button
          type="button"
          @click="showPreferences = !showPreferences"
          class="flex w-full items-center justify-between px-4 py-3 text-sm font-medium transition-colors hover:bg-[var(--color-accent)]"
          :disabled="loading"
        >
          <span class="flex items-center gap-2">
            <svg class="h-4 w-4 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Preferences
          </span>
          <svg
            class="h-4 w-4 text-[var(--color-muted-foreground)] transition-transform duration-200"
            :class="{ 'rotate-180': showPreferences }"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        <div v-show="showPreferences" class="border-t border-[var(--color-border)] px-4 py-3 space-y-3">
          <!-- Timezone -->
          <div class="space-y-1">
            <label for="reg-timezone" class="label-text text-xs">Timezone</label>
            <select
              id="reg-timezone"
              v-model="form.timezone"
              class="input-field"
              :disabled="loading"
            >
              <optgroup label="Americas">
                <option value="UTC">UTC</option>
                <option v-for="tz in TIMEZONE_OPTIONS" :key="tz.value" :value="tz.value">
                  {{ tz.label }}
                </option>
              </optgroup>
            </select>
          </div>

          <!-- Currency & Language Row -->
          <div class="grid grid-cols-2 gap-3">
            <div class="space-y-1">
              <label for="reg-currency" class="label-text text-xs">Currency</label>
              <select
                id="reg-currency"
                v-model="form.currency"
                class="input-field"
                :disabled="loading"
              >
                <option v-for="c in CURRENCY_OPTIONS" :key="c.value" :value="c.value">
                  {{ c.label }}
                </option>
              </select>
            </div>
            <div class="space-y-1">
              <label for="reg-language" class="label-text text-xs">Language</label>
              <select
                id="reg-language"
                v-model="form.language"
                class="input-field"
                :disabled="loading"
              >
                <option v-for="l in LANGUAGE_OPTIONS" :key="l.value" :value="l.value">
                  {{ l.label }}
                </option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Terms -->
      <div class="flex items-start gap-2">
        <input
          id="reg-terms"
          v-model="form.agree_terms"
          type="checkbox"
          required
          class="mt-1 h-4 w-4 rounded border-[var(--color-input)]"
          :aria-invalid="!!fieldErrors.agree_terms"
          :aria-describedby="fieldErrors.agree_terms ? 'reg-terms-error' : undefined"
          :disabled="loading"
        />
        <label for="reg-terms" class="text-sm text-[var(--color-muted-foreground)]">
          I agree to the
          <a href="#" class="text-brand-600 hover:text-brand-500 dark:text-brand-400">Terms of Service</a>
          and
          <a href="#" class="text-brand-600 hover:text-brand-500 dark:text-brand-400">Privacy Policy</a>
        </label>
      </div>
      <p
        v-if="fieldErrors.agree_terms"
        id="reg-terms-error"
        class="text-xs text-red-500"
        role="alert"
      >
        {{ fieldErrors.agree_terms }}
      </p>

      <!-- Submit -->
      <button
        type="submit"
        :disabled="loading"
        class="btn-primary w-full"
        aria-label="Create your account"
      >
        <svg v-if="loading" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        {{ loading ? "Creating account..." : "Create account" }}
      </button>
    </form>

    <!-- Footer -->
    <p class="mt-6 text-center text-sm text-[var(--color-muted-foreground)]">
      Already have an account?
      <a
        href="/auth/login"
        class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400"
      >
        Sign in
      </a>
    </p>
  </div>
</template>
