<script setup lang="ts">
// Forgot password — Vue interactive island
// OTP-based flow: Step 1 → enter email & request OTP, Step 2 → enter OTP + new password

import { ref, reactive, computed } from "vue";
import { requestPasswordReset, confirmPasswordReset, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";

// ─── State ──────────────────────────────────────────────────────────────────

const step = ref<1 | 2>(1); // 1 = email form, 2 = OTP + new password form
const loading = ref(false);
const error = ref("");
const done = ref(false);
const resendCooldown = ref(0);

const form = reactive({
  email: "",
  otp: "",
  new_password: "",
  confirm_password: "",
});

const fieldErrors = reactive<Record<string, string>>({
  email: "",
  otp: "",
  new_password: "",
  confirm_password: "",
});

// ─── Password strength ─────────────────────────────────────────────────────

const passwordChecks = computed(() => {
  const pw = form.new_password;
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
  if (form.new_password.length === 0) return { level: 0, label: "", color: "" };
  if (passed <= 2) return { level: 1, label: "Weak", color: "bg-red-500" };
  if (passed <= 3) return { level: 2, label: "Fair", color: "bg-yellow-500" };
  if (passed <= 4) return { level: 3, label: "Good", color: "bg-brand-400" };
  return { level: 4, label: "Strong", color: "bg-brand-600" };
});

const strengthSegments = [0, 1, 2, 3];

// ─── Helpers ────────────────────────────────────────────────────────────────

function clearErrors() {
  error.value = "";
  Object.keys(fieldErrors).forEach((key) => {
    fieldErrors[key] = "";
  });
}

// ─── Step 1: Request OTP ────────────────────────────────────────────────────

function validateEmailForm(): boolean {
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
  return true;
}

async function handleRequestOtp() {
  if (!validateEmailForm()) return;

  loading.value = true;
  clearErrors();

  try {
    await requestPasswordReset(form.email.trim());
    step.value = 2;
    showToast("A verification code has been sent to your email.", "success");
    startResendCooldown();
  } catch (err: unknown) {
    // For security, still proceed to OTP step even on error
    // so we don't leak whether an email exists
    step.value = 2;
    showToast("If an account with that email exists, a reset code has been sent.", "info");
    startResendCooldown();
  } finally {
    loading.value = false;
  }
}

// ─── Resend OTP ─────────────────────────────────────────────────────────────

let cooldownTimer: ReturnType<typeof setInterval> | null = null;

function startResendCooldown() {
  resendCooldown.value = 60;
  if (cooldownTimer) clearInterval(cooldownTimer);
  cooldownTimer = setInterval(() => {
    resendCooldown.value--;
    if (resendCooldown.value <= 0) {
      clearInterval(cooldownTimer!);
      cooldownTimer = null;
    }
  }, 1000);
}

async function handleResendOtp() {
  if (resendCooldown.value > 0 || loading.value) return;
  loading.value = true;
  clearErrors();

  try {
    await requestPasswordReset(form.email.trim());
    showToast("A new verification code has been sent.", "success");
    startResendCooldown();
  } catch {
    showToast("Could not resend code. Please try again.", "error");
  } finally {
    loading.value = false;
  }
}

// ─── Step 2: Confirm OTP + Set New Password ────────────────────────────────

function validateResetForm(): boolean {
  clearErrors();
  let valid = true;

  if (!form.otp.trim()) {
    fieldErrors.otp = "Verification code is required.";
    valid = false;
  } else if (form.otp.trim().length !== 6 || !/^\d{6}$/.test(form.otp.trim())) {
    fieldErrors.otp = "Enter the 6-digit code from your email.";
    valid = false;
  }

  const checks = Object.values(passwordChecks.value);
  if (!form.new_password) {
    fieldErrors.new_password = "New password is required.";
    valid = false;
  } else if (checks.some((c) => !c)) {
    fieldErrors.new_password = "Password does not meet all requirements.";
    valid = false;
  }

  if (!form.confirm_password) {
    fieldErrors.confirm_password = "Please confirm your new password.";
    valid = false;
  } else if (form.new_password !== form.confirm_password) {
    fieldErrors.confirm_password = "Passwords do not match.";
    valid = false;
  }

  return valid;
}

async function handleResetPassword() {
  if (!validateResetForm()) return;

  loading.value = true;
  clearErrors();

  try {
    await confirmPasswordReset(
      form.email.trim(),
      form.otp.trim(),
      form.new_password,
      form.confirm_password,
    );
    done.value = true;
    showToast("Password reset successfully! Redirecting to sign in...", "success");
    if (cooldownTimer) clearInterval(cooldownTimer);
    setTimeout(() => {
      window.location.href = "/auth/login";
    }, 3000);
  } catch (err: unknown) {
    const message = getErrorMessage(err);
    error.value = message;
    showToast(message, "error");
  } finally {
    loading.value = false;
  }
}

// ─── Back to step 1 ────────────────────────────────────────────────────────

function backToEmail() {
  step.value = 1;
  form.otp = "";
  form.new_password = "";
  form.confirm_password = "";
  clearErrors();
}
</script>

<template>
  <div>
    <!-- ─── Done state ─── -->
    <div v-if="done" class="text-center">
      <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-950">
        <svg class="h-8 w-8 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
      </div>
      <h2 class="text-2xl font-bold tracking-tight">Password reset!</h2>
      <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
        Your password has been reset successfully. You can now sign in.
      </p>
      <a href="/auth/login" class="btn-primary mt-6 inline-flex" aria-label="Go to sign in page">
        Sign in
      </a>
    </div>

    <!-- ─── Step 1: Enter email ─── -->
    <div v-else-if="step === 1">
      <div class="mb-6 text-center">
        <h2 class="text-2xl font-bold tracking-tight">Forgot password?</h2>
        <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
          Enter your email and we'll send a verification code
        </p>
      </div>

      <div
        v-if="error"
        role="alert"
        class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
      >
        {{ error }}
      </div>

      <form @submit.prevent="handleRequestOtp" class="space-y-4">
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
            :class="{ 'border-red-500 ring-red-500': fieldErrors.email }"
            :aria-invalid="!!fieldErrors.email"
            :aria-describedby="fieldErrors.email ? 'forgot-email-error' : undefined"
            :disabled="loading"
          />
          <p
            v-if="fieldErrors.email"
            id="forgot-email-error"
            class="text-xs text-red-500"
            role="alert"
          >
            {{ fieldErrors.email }}
          </p>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="btn-primary w-full"
          aria-label="Send verification code"
        >
          <svg v-if="loading" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ loading ? "Sending..." : "Send verification code" }}
        </button>
      </form>

      <p class="mt-6 text-center text-sm text-[var(--color-muted-foreground)]">
        Remember your password?
        <a href="/auth/login" class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400">Sign in</a>
      </p>
    </div>

    <!-- ─── Step 2: OTP + New Password ─── -->
    <div v-else>
      <div class="mb-6 text-center">
        <h2 class="text-2xl font-bold tracking-tight">Enter verification code</h2>
        <p class="mt-2 text-sm text-[var(--color-muted-foreground)]">
          We sent a 6-digit code to <strong>{{ form.email }}</strong>
        </p>
      </div>

      <!-- General Error -->
      <div
        v-if="error"
        role="alert"
        class="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300"
      >
        {{ error }}
      </div>

      <form @submit.prevent="handleResetPassword" class="space-y-4">

        <!-- OTP Input -->
        <div class="space-y-2">
          <label for="forgot-otp" class="label-text">Verification code</label>
          <input
            id="forgot-otp"
            v-model="form.otp"
            type="text"
            inputmode="numeric"
            maxlength="6"
            required
            autocomplete="one-time-code"
            placeholder="000000"
            class="input-field text-center text-lg tracking-[0.5em] font-mono"
            :class="{ 'border-red-500 ring-red-500': fieldErrors.otp }"
            :aria-invalid="!!fieldErrors.otp"
            :aria-describedby="fieldErrors.otp ? 'forgot-otp-error' : undefined"
            :disabled="loading"
          />
          <p
            v-if="fieldErrors.otp"
            id="forgot-otp-error"
            class="text-xs text-red-500"
            role="alert"
          >
            {{ fieldErrors.otp }}
          </p>
          <p class="text-xs text-[var(--color-muted-foreground)]">
            Didn't receive it?
            <button
              type="button"
              class="font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400 disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="resendCooldown > 0 || loading"
              @click="handleResendOtp"
            >
              {{ resendCooldown > 0 ? `Resend in ${resendCooldown}s` : "Resend code" }}
            </button>
          </p>
        </div>

        <!-- New Password -->
        <div class="space-y-2">
          <label for="forgot-new-password" class="label-text">New password</label>
          <input
            id="forgot-new-password"
            v-model="form.new_password"
            type="password"
            required
            autocomplete="new-password"
            placeholder="Create a strong password"
            class="input-field"
            :class="{ 'border-red-500 ring-red-500': fieldErrors.new_password }"
            :aria-invalid="!!fieldErrors.new_password"
            :aria-describedby="fieldErrors.new_password ? 'forgot-pw-error' : (form.new_password ? 'forgot-pw-strength' : undefined)"
            :disabled="loading"
          />
          <p
            v-if="fieldErrors.new_password"
            id="forgot-pw-error"
            class="text-xs text-red-500"
            role="alert"
          >
            {{ fieldErrors.new_password }}
          </p>

          <!-- Password Strength Bar -->
          <div v-if="form.new_password.length > 0" id="forgot-pw-strength" class="space-y-2">
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

            <ul class="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
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
          <label for="forgot-confirm" class="label-text">Confirm new password</label>
          <input
            id="forgot-confirm"
            v-model="form.confirm_password"
            type="password"
            required
            autocomplete="new-password"
            placeholder="Re-enter your new password"
            class="input-field"
            :class="{
              'border-red-500 ring-red-500': fieldErrors.confirm_password || (form.confirm_password && form.new_password !== form.confirm_password)
            }"
            :aria-invalid="!!(fieldErrors.confirm_password || (form.confirm_password && form.new_password !== form.confirm_password))"
            :disabled="loading"
          />
          <p
            v-if="fieldErrors.confirm_password"
            class="text-xs text-red-500"
            role="alert"
          >
            {{ fieldErrors.confirm_password }}
          </p>
          <p
            v-else-if="form.confirm_password && form.new_password !== form.confirm_password"
            class="text-xs text-red-500"
          >
            Passwords do not match
          </p>
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="btn-primary w-full"
          aria-label="Reset your password"
        >
          <svg v-if="loading" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden="true">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ loading ? "Resetting..." : "Reset password" }}
        </button>
      </form>

      <!-- Back link -->
      <div class="mt-4 flex items-center justify-between">
        <button
          type="button"
          class="text-sm text-[var(--color-muted-foreground)] hover:text-foreground transition-colors"
          @click="backToEmail"
        >
          ← Use a different email
        </button>
        <a href="/auth/login" class="text-sm font-medium text-brand-600 hover:text-brand-500 dark:text-brand-400">
          Sign in
        </a>
      </div>
    </div>
  </div>
</template>
