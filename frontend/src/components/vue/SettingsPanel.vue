<script setup lang="ts">
// Settings page — Vue interactive island
// Contains: Change Password, Change Email, Logout, Delete Account

import { ref, reactive } from "vue";
import {
  changePassword,
  requestEmailChange,
  confirmEmailChangeOTP,
  deleteAccount,
  logout,
  requireAuth,
  getErrorMessage,
} from "@/lib/auth";
import { showToast } from "@/lib/toast";

// ==================== Change Password ====================
const pwForm = reactive({
  current_password: "",
  new_password: "",
  confirm_password: "",
});
const pwLoading = ref(false);
const pwError = ref("");
const pwSuccess = ref("");

async function handlePasswordChange() {
  pwError.value = "";
  pwSuccess.value = "";

  if (!pwForm.current_password) {
    pwError.value = "Current password is required.";
    return;
  }
  if (pwForm.new_password.length < 8) {
    pwError.value = "New password must be at least 8 characters.";
    return;
  }
  if (pwForm.new_password !== pwForm.confirm_password) {
    pwError.value = "Passwords do not match.";
    return;
  }

  pwLoading.value = true;
  try {
    await changePassword(pwForm.current_password, pwForm.new_password, pwForm.confirm_password);
    showToast("Password changed successfully.", "success");
    pwForm.current_password = "";
    pwForm.new_password = "";
    pwForm.confirm_password = "";
  } catch (err) {
    const msg = getErrorMessage(err);
    pwError.value = msg;
    showToast(msg, "error");
  } finally {
    pwLoading.value = false;
  }
}

// ==================== Change Email (OTP 2-step) ====================
type EmailStep = "request" | "otp" | "done";
const emailStep = ref<EmailStep>("request");
const emailForm = reactive({
  current_password: "",
  new_email: "",
});
const emailOtp = ref(["", "", "", "", "", ""]);
const emailLoading = ref(false);
const emailError = ref("");
const emailCountdown = ref(0);
let emailCountdownTimer: ReturnType<typeof setInterval> | null = null;

function startEmailCountdown() {
  emailCountdown.value = 60;
  if (emailCountdownTimer) clearInterval(emailCountdownTimer);
  emailCountdownTimer = setInterval(() => {
    emailCountdown.value--;
    if (emailCountdown.value <= 0) {
      clearInterval(emailCountdownTimer!);
      emailCountdownTimer = null;
    }
  }, 1000);
}

function resetEmailFlow() {
  emailStep.value = "request";
  emailForm.current_password = "";
  emailForm.new_email = "";
  emailOtp.value = ["", "", "", "", "", ""];
  emailError.value = "";
  emailCountdown.value = 0;
  if (emailCountdownTimer) {
    clearInterval(emailCountdownTimer);
    emailCountdownTimer = null;
  }
}

function handleOtpInput(e: Event, index: number) {
  const input = e.target as HTMLInputElement;
  const val = input.value.replace(/\D/g, "");
  if (val.length > 1) {
    // Paste support
    const digits = val.slice(0, 6).split("");
    for (let i = 0; i < 6; i++) {
      emailOtp.value[i] = digits[i] || "";
    }
    const lastIdx = Math.min(val.length, 5);
    const nextInput = input.parentElement?.querySelectorAll("input")[lastIdx] as HTMLInputElement;
    nextInput?.focus();
    return;
  }
  emailOtp.value[index] = val;
  if (val && index < 5) {
    const nextInput = input.parentElement?.querySelectorAll("input")[index + 1] as HTMLInputElement;
    nextInput?.focus();
  }
}

function handleOtpKeydown(e: KeyboardEvent, index: number) {
  if (e.key === "Backspace" && !emailOtp.value[index] && index > 0) {
    const inputs = (e.target as HTMLInputElement).parentElement?.querySelectorAll("input");
    (inputs?.[index - 1] as HTMLInputElement)?.focus();
  }
}

async function handleEmailRequest() {
  emailError.value = "";
  if (!emailForm.current_password) {
    emailError.value = "Current password is required.";
    return;
  }
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(emailForm.new_email)) {
    emailError.value = "Please enter a valid email address.";
    return;
  }
  emailLoading.value = true;
  try {
    await requestEmailChange(emailForm.current_password, emailForm.new_email);
    showToast("A verification code has been sent to your current email.", "info");
    emailStep.value = "otp";
    emailOtp.value = ["", "", "", "", "", ""];
    startEmailCountdown();
  } catch (err) {
    const msg = getErrorMessage(err);
    emailError.value = msg;
    showToast(msg, "error");
  } finally {
    emailLoading.value = false;
  }
}

async function handleEmailOtpConfirm() {
  emailError.value = "";
  const otpStr = emailOtp.value.join("");
  if (otpStr.length !== 6) {
    emailError.value = "Please enter the complete 6-digit code.";
    return;
  }
  emailLoading.value = true;
  try {
    await confirmEmailChangeOTP(otpStr);
    emailStep.value = "done";
    showToast("Email changed successfully. Logging out...", "success");
    // Auto-logout after 2 seconds
    setTimeout(async () => {
      try {
        await logout();
      } catch {
        // Fallback: clear tokens and redirect
        sessionStorage.removeItem("auth_access_token");
        sessionStorage.removeItem("auth_refresh_token");
        localStorage.removeItem("auth_access_token");
        localStorage.removeItem("auth_refresh_token");
        localStorage.removeItem("auth_remember_me");
        window.location.href = "/auth/login";
      }
    }, 2000);
  } catch (err) {
    const msg = getErrorMessage(err);
    emailError.value = msg;
    showToast(msg, "error");
  } finally {
    emailLoading.value = false;
  }
}

async function handleResendEmailOtp() {
  if (emailCountdown.value > 0 || emailLoading.value) return;
  emailError.value = "";
  emailLoading.value = true;
  try {
    await requestEmailChange(emailForm.current_password, emailForm.new_email);
    showToast("A new verification code has been sent.", "info");
    emailOtp.value = ["", "", "", "", "", ""];
    startEmailCountdown();
  } catch (err) {
    const msg = getErrorMessage(err);
    emailError.value = msg;
    showToast(msg, "error");
  } finally {
    emailLoading.value = false;
  }
}

// ==================== Logout ====================
const showLogoutDialog = ref(false);
const logoutLoading = ref(false);

async function handleLogout() {
  showLogoutDialog.value = false;
  logoutLoading.value = true;
  try {
    await logout();
  } catch {
    showToast("Could not reach the server. Signing you out locally.", "warning");
  } finally {
    logoutLoading.value = false;
  }
}

// ==================== Delete Account ====================
const deleteForm = reactive({
  current_password: "",
  confirmText: "",
});
const showDeleteDialog = ref(false);
const deleteLoading = ref(false);
const deleteError = ref("");

const DELETE_CONFIRM_PHRASE = "DELETE MY ACCOUNT";

async function handleDeleteAccount() {
  deleteError.value = "";

  if (!deleteForm.current_password) {
    deleteError.value = "Current password is required.";
    return;
  }

  if (deleteForm.confirmText !== DELETE_CONFIRM_PHRASE) {
    deleteError.value = `Type "${DELETE_CONFIRM_PHRASE}" exactly to confirm.`;
    return;
  }

  deleteLoading.value = true;
  try {
    await deleteAccount(deleteForm.current_password);
    showToast("Account deleted. Redirecting...", "success");
    setTimeout(() => {
      window.location.href = "/auth/login";
    }, 1000);
  } catch (err) {
    const msg = getErrorMessage(err);
    deleteError.value = msg;
    showToast(msg, "error");
  } finally {
    deleteLoading.value = false;
  }
}

function openDeleteDialog() {
  deleteForm.current_password = "";
  deleteForm.confirmText = "";
  deleteError.value = "";
  showDeleteDialog.value = true;
}

function closeDeleteDialog() {
  showDeleteDialog.value = false;
  deleteError.value = "";
}
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold tracking-tight">Settings</h1>
      <p class="mt-1 text-sm text-[var(--color-muted-foreground)]">
        Manage your account security and preferences
      </p>
    </div>

    <div class="space-y-6 max-w-2xl">
      <!-- ==================== Change Password ==================== -->
      <div class="card p-6">
        <div class="mb-4">
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <svg class="h-5 w-5 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Change Password
          </h2>
          <p class="mt-1 text-sm text-[var(--color-muted-foreground)]">
            Update your password. Requires current password.
          </p>
        </div>

        <div v-if="pwError" class="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {{ pwError }}
        </div>
        <div v-if="pwSuccess" class="mb-3 rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-sm text-brand-700 dark:border-brand-800 dark:bg-brand-950 dark:text-brand-300">
          {{ pwSuccess }}
        </div>

        <form @submit.prevent="handlePasswordChange" class="space-y-3">
          <div class="space-y-1">
            <label for="pw-current" class="label-text">Current password</label>
            <input id="pw-current" v-model="pwForm.current_password" type="password" required autocomplete="current-password" class="input-field" />
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="space-y-1">
              <label for="pw-new" class="label-text">New password</label>
              <input id="pw-new" v-model="pwForm.new_password" type="password" required minlength="8" autocomplete="new-password" class="input-field" />
            </div>
            <div class="space-y-1">
              <label for="pw-confirm" class="label-text">Confirm new password</label>
              <input id="pw-confirm" v-model="pwForm.confirm_password" type="password" required minlength="8" autocomplete="new-password" class="input-field" />
            </div>
          </div>
          <button type="submit" :disabled="pwLoading" class="btn-primary">
            {{ pwLoading ? "Changing..." : "Change password" }}
          </button>
        </form>
      </div>

      <!-- ==================== Change Email ==================== -->
      <div class="card p-6">
        <div class="mb-4">
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <svg class="h-5 w-5 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            Change Email
          </h2>
          <p class="mt-1 text-sm text-[var(--color-muted-foreground)]">
            Requires current password. A 6-digit code will be sent to your current email.
          </p>
        </div>

        <div v-if="emailError" class="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {{ emailError }}
        </div>

        <!-- Step 1: Request -->
        <form v-if="emailStep === 'request'" @submit.prevent="handleEmailRequest" class="space-y-3">
          <div class="space-y-1">
            <label for="email-current" class="label-text">Current password</label>
            <input id="email-current" v-model="emailForm.current_password" type="password" required autocomplete="current-password" class="input-field" />
          </div>
          <div class="space-y-1">
            <label for="email-new" class="label-text">New email address</label>
            <input id="email-new" v-model="emailForm.new_email" type="email" required autocomplete="email" placeholder="new@example.com" class="input-field" />
          </div>
          <button type="submit" :disabled="emailLoading" class="btn-primary">
            {{ emailLoading ? "Sending code..." : "Send verification code" }}
          </button>
        </form>

        <!-- Step 2: Enter OTP -->
        <div v-else-if="emailStep === 'otp'" class="space-y-4">
          <div class="rounded-lg border border-brand-200 bg-brand-50 px-4 py-3 dark:border-brand-800 dark:bg-brand-950">
            <p class="text-sm text-brand-700 dark:text-brand-300">
              <svg class="inline h-4 w-4 mr-1 -mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" /></svg>
              A code was sent to <strong>your current email</strong>. Changing to <strong>{{ emailForm.new_email }}</strong>.
            </p>
          </div>

          <div class="space-y-2">
            <label class="label-text">Enter 6-digit code</label>
            <div class="flex gap-2 justify-center">
              <input
                v-for="(_, i) in 6"
                :key="i"
                :ref="(el) => { if (el) (el as HTMLInputElement).value = emailOtp[i] }"
                type="text"
                inputmode="numeric"
                maxlength="1"
                class="input-field w-11 h-12 text-center text-lg font-mono"
                :disabled="emailLoading"
                @input="handleOtpInput($event, i)"
                @keydown="handleOtpKeydown($event, i)"
              />
            </div>
          </div>

          <div class="flex gap-2">
            <button @click="handleEmailOtpConfirm" :disabled="emailLoading || emailOtp.join('').length !== 6" class="btn-primary flex-1">
              {{ emailLoading ? "Verifying..." : "Confirm email change" }}
            </button>
            <button type="button" @click="resetEmailFlow" class="btn-ghost" :disabled="emailLoading">Cancel</button>
          </div>

          <button
            type="button"
            @click="handleResendEmailOtp"
            :disabled="emailCountdown > 0 || emailLoading"
            class="w-full text-center text-sm text-brand-600 hover:text-brand-500 dark:text-brand-400 disabled:text-muted-foreground disabled:cursor-not-allowed transition-colors"
          >
            {{ emailCountdown > 0 ? `Resend code in ${emailCountdown}s` : "Resend code" }}
          </button>
        </div>

        <!-- Step 3: Done -->
        <div v-else-if="emailStep === 'done'" class="text-center py-4">
          <div class="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 dark:bg-brand-950">
            <svg class="h-6 w-6 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <p class="text-sm font-medium">Email changed! Logging you out...</p>
        </div>
      </div>

      <!-- ==================== Logout ==================== -->
      <div class="card p-6">
        <div class="mb-4">
          <h2 class="text-lg font-semibold flex items-center gap-2">
            <svg class="h-5 w-5 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out
          </h2>
          <p class="mt-1 text-sm text-[var(--color-muted-foreground)]">
            Sign out of your account on this device.
          </p>
        </div>

        <!-- Logout Confirmation Dialog -->
        <div v-if="showLogoutDialog" class="mb-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-accent)] p-4">
          <p class="text-sm font-medium mb-3">Are you sure you want to sign out?</p>
          <div class="flex gap-2">
            <button
              @click="handleLogout"
              :disabled="logoutLoading"
              class="btn-secondary"
            >
              {{ logoutLoading ? "Signing out..." : "Yes, sign out" }}
            </button>
            <button
              @click="showLogoutDialog = false"
              class="btn-ghost"
              :disabled="logoutLoading"
            >
              Cancel
            </button>
          </div>
        </div>

        <button
          v-else
          @click="showLogoutDialog = true"
          class="btn-secondary"
        >
          Sign out
        </button>
      </div>

      <!-- ==================== Danger Zone ==================== -->
      <div class="card p-6 border-red-200 dark:border-red-900">
        <div class="mb-4">
          <h2 class="text-lg font-semibold text-red-600 dark:text-red-400 flex items-center gap-2">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            Danger Zone
          </h2>
          <p class="mt-1 text-sm text-[var(--color-muted-foreground)]">
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>
        </div>

        <!-- Delete Confirmation Modal -->
        <div v-if="showDeleteDialog">
          <div class="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-800 dark:bg-red-950">
            <div v-if="deleteError" class="mb-3 rounded border border-red-300 bg-red-100 px-3 py-2 text-sm text-red-800 dark:border-red-700 dark:bg-red-900 dark:text-red-200">
              {{ deleteError }}
            </div>

            <p class="mb-3 text-sm font-medium text-red-700 dark:text-red-300">
              This will permanently delete your account and all your data.
            </p>
            <form @submit.prevent="handleDeleteAccount" class="space-y-3">
              <div class="space-y-1">
                <label for="delete-pw" class="label-text">Current password</label>
                <input id="delete-pw" v-model="deleteForm.current_password" type="password" required autocomplete="current-password" class="input-field" />
              </div>
              <div class="space-y-1">
                <label for="delete-confirm" class="label-text">
                  Type <strong>{{ DELETE_CONFIRM_PHRASE }}</strong> to confirm
                </label>
                <input
                  id="delete-confirm"
                  v-model="deleteForm.confirmText"
                  type="text"
                  required
                  class="input-field"
                  :placeholder="DELETE_CONFIRM_PHRASE"
                />
              </div>
              <div class="flex gap-2">
                <button type="submit" :disabled="deleteLoading" class="btn-destructive">
                  {{ deleteLoading ? "Deleting..." : "Permanently delete my account" }}
                </button>
                <button type="button" @click="closeDeleteDialog" class="btn-secondary">
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>

        <button
          v-else
          @click="openDeleteDialog"
          class="btn-destructive"
        >
          Delete account
        </button>
      </div>
    </div>
  </div>
</template>
