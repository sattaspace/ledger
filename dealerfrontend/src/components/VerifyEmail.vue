<script setup lang="ts">
/**
 * VerifyEmail — DSR email verification page.
 *
 * Replaces the inline card that was in App.vue. Reads the token from
 * the URL (?token=xxx), calls dsrApi.verifyEmail, and shows status.
 *
 * On success/error, provides a button to navigate to the DSR login page.
 */
import { onMounted, ref } from "vue";
import { dsrApi } from "../services/dsrClient";

const token = ref<string | null>(null);
const status = ref<"loading" | "success" | "error">("loading");
const errorMsg = ref("");

onMounted(async () => {
  if (typeof window === "undefined") return;

  const params = new URLSearchParams(window.location.search);
  const t = params.get("token");
  if (!t) {
    status.value = "error";
    errorMsg.value = "No verification token found. Please request a new one from your DSR Portal.";
    return;
  }
  token.value = t;

  // Strip token from URL for safety (referrer / history leakage)
  params.delete("token");
  const newSearch = params.toString();
  const cleanUrl = window.location.pathname + (newSearch ? `?${newSearch}` : "") + window.location.hash;
  window.history.replaceState({}, "", cleanUrl);

  try {
    await dsrApi.verifyEmail(t);
    status.value = "success";
  } catch (err: any) {
    status.value = "error";
    errorMsg.value =
      err?.data?.detail || err?.message || "Verification failed. The link may have expired.";
  }
});

function goToLogin() {
  window.location.href = "/dsr/login";
}
</script>

<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4"
  >
    <div class="w-full max-w-md bg-white rounded-2xl shadow-xl p-8 text-center">
      <div
        class="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
        :class="status === 'success' ? 'bg-emerald-100' : status === 'error' ? 'bg-red-100' : 'bg-amber-100'"
      >
        <svg v-if="status === 'loading'" class="animate-spin h-8 w-8 text-amber-600" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
          <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <svg
          v-else-if="status === 'success'"
          class="h-8 w-8 text-emerald-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
        </svg>
        <svg v-else class="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
      <h2 class="text-xl font-bold text-slate-800 mb-2">
        {{
          status === "loading"
            ? "Verifying..."
            : status === "success"
              ? "Email Verified!"
              : "Verification Failed"
        }}
      </h2>
      <p class="text-sm text-slate-600 mb-6">
        {{
          status === "loading"
            ? "Please wait while we verify your email address."
            : status === "success"
              ? "Your email has been verified successfully! You can now accept dealer invitations."
              : errorMsg || "The verification link is invalid or has expired. Please request a new one from your DSR Portal."
        }}
      </p>
      <button
        v-if="status !== 'loading'"
        @click="goToLogin"
        class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium rounded-lg transition"
      >
        {{ status === "success" ? "Go to DSR Portal" : "Back to Login" }}
      </button>
    </div>
  </div>
</template>
