<script setup lang="ts">
/**
 * SettingsPage — user preferences for Satta Ledger.
 *
 * Sections:
 *   1. Profile — View base currency & timezone from Sattabase base backend (8086).
 *      These are read-only here; to change them, redirect to base domain profile.
 *   2. Date & Time — Date format preference (local storage).
 *   3. Appearance — Theme preference (dark/light/system, local storage).
 *   4. Notifications — Reminder preferences (days before, enabled types).
 */

import { ref, computed, onMounted, watch } from "vue";
import { useAuth } from "@/composables/useAuth";
import { useToast } from "@/composables/useToast";
import { getBaseCurrency, getCurrencySymbol, getCurrencyName } from "@/lib/currency";
import { getUserTimezone, getTimezoneOffsetDisplay } from "@/lib/timezone";
import { redirectToBaseWithAuthCode } from "@/lib/auth";

// ─── Local Storage Keys ──────────────────────────────────────────────────────

const DATE_FORMAT_KEY = "sattabase-ledger:date_format";
const THEME_KEY = "sattabase-ledger:theme";
const REMINDER_BILL_DAYS_KEY = "sattabase-ledger:reminder_bill_days";
const REMINDER_INSURANCE_DAYS_KEY = "sattabase-ledger:reminder_insurance_days";
const REMINDER_DOC_DAYS_KEY = "sattabase-ledger:reminder_doc_days";
const REMINDER_GOAL_DAYS_KEY = "sattabase-ledger:reminder_goal_days";
const REMINDER_BILL_ENABLED_KEY = "sattabase-ledger:reminder_bill_enabled";
const REMINDER_INSURANCE_ENABLED_KEY = "sattabase-ledger:reminder_insurance_enabled";
const REMINDER_DOC_ENABLED_KEY = "sattabase-ledger:reminder_doc_enabled";
const REMINDER_GOAL_ENABLED_KEY = "sattabase-ledger:reminder_goal_enabled";

// ─── State ──────────────────────────────────────────────────────────────────

const { user, fetchProfile } = useAuth();
const toast = useToast();
const loading = ref(true);

// Profile info (read-only, comes from 8086)
const baseCurrency = ref("USD");
const baseCurrencySymbol = ref("$");
const baseCurrencyName = ref("US Dollar");
const userTimezone = ref("UTC");
const timezoneOffset = ref("");

// Date format preference
const dateFormat = ref("MMM DD, YYYY");

// Theme preference
const theme = ref<"light" | "dark" | "system">("system");

// Notification reminder preferences
const reminders = ref({
  billEnabled: true,
  billDays: 5,
  insuranceEnabled: true,
  insuranceDays: 30,
  docEnabled: true,
  docDays: 30,
  goalEnabled: true,
  goalDays: 7,
});

// ─── Date format options ────────────────────────────────────────────────────

const dateFormatOptions = [
  { value: "MM/DD/YYYY", label: "MM/DD/YYYY", example: "01/15/2025" },
  { value: "DD/MM/YYYY", label: "DD/MM/YYYY", example: "15/01/2025" },
  { value: "YYYY-MM-DD", label: "YYYY-MM-DD", example: "2025-01-15" },
  { value: "MMM DD, YYYY", label: "MMM DD, YYYY", example: "Jan 15, 2025" },
  { value: "DD MMM YYYY", label: "DD MMM YYYY", example: "15 Jan 2025" },
  { value: "DD.MM.YYYY", label: "DD.MM.YYYY", example: "15.01.2025" },
];

// ─── Computed ───────────────────────────────────────────────────────────────

const effectiveTheme = computed(() => {
  if (theme.value !== "system") return theme.value;
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
});

// ─── Local Storage Helpers ──────────────────────────────────────────────────

function loadFromStorage(): void {
  if (typeof window === "undefined") return;

  try {
    const storedDateFormat = localStorage.getItem(DATE_FORMAT_KEY);
    if (storedDateFormat) dateFormat.value = storedDateFormat;

    const storedTheme = localStorage.getItem(THEME_KEY);
    if (storedTheme === "light" || storedTheme === "dark" || storedTheme === "system") {
      theme.value = storedTheme;
    }

    const billDays = localStorage.getItem(REMINDER_BILL_DAYS_KEY);
    if (billDays) reminders.value.billDays = parseInt(billDays, 10);
    const insuranceDays = localStorage.getItem(REMINDER_INSURANCE_DAYS_KEY);
    if (insuranceDays) reminders.value.insuranceDays = parseInt(insuranceDays, 10);
    const docDays = localStorage.getItem(REMINDER_DOC_DAYS_KEY);
    if (docDays) reminders.value.docDays = parseInt(docDays, 10);
    const goalDays = localStorage.getItem(REMINDER_GOAL_DAYS_KEY);
    if (goalDays) reminders.value.goalDays = parseInt(goalDays, 10);

    const billEnabled = localStorage.getItem(REMINDER_BILL_ENABLED_KEY);
    if (billEnabled !== null) reminders.value.billEnabled = billEnabled === "true";
    const insuranceEnabled = localStorage.getItem(REMINDER_INSURANCE_ENABLED_KEY);
    if (insuranceEnabled !== null) reminders.value.insuranceEnabled = insuranceEnabled === "true";
    const docEnabled = localStorage.getItem(REMINDER_DOC_ENABLED_KEY);
    if (docEnabled !== null) reminders.value.docEnabled = docEnabled === "true";
    const goalEnabled = localStorage.getItem(REMINDER_GOAL_ENABLED_KEY);
    if (goalEnabled !== null) reminders.value.goalEnabled = goalEnabled === "true";
  } catch {
    // localStorage unavailable
  }
}

function saveDateFormat(value: string): void {
  try {
    localStorage.setItem(DATE_FORMAT_KEY, value);
    toast.success("Date format updated");
  } catch {
    toast.error("Failed to save date format");
  }
}

function saveTheme(value: "light" | "dark" | "system"): void {
  try {
    localStorage.setItem(THEME_KEY, value);
    // Apply theme immediately
    applyTheme(value);
    toast.success("Theme updated");
  } catch {
    toast.error("Failed to save theme");
  }
}

function applyTheme(value: "light" | "dark" | "system"): void {
  if (typeof document === "undefined") return;

  const root = document.documentElement;
  let isDark = false;

  if (value === "dark") {
    isDark = true;
  } else if (value === "system") {
    isDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  if (isDark) {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

function saveReminder(key: string, value: boolean | number): void {
  try {
    localStorage.setItem(key, String(value));
  } catch {
    toast.error("Failed to save reminder settings");
  }
}

// ─── Watchers ───────────────────────────────────────────────────────────────

watch(() => dateFormat.value, (val) => saveDateFormat(val));
watch(() => theme.value, (val) => saveTheme(val));
watch(() => reminders.value.billDays, (val) => saveReminder(REMINDER_BILL_DAYS_KEY, val));
watch(() => reminders.value.insuranceDays, (val) => saveReminder(REMINDER_INSURANCE_DAYS_KEY, val));
watch(() => reminders.value.docDays, (val) => saveReminder(REMINDER_DOC_DAYS_KEY, val));
watch(() => reminders.value.goalDays, (val) => saveReminder(REMINDER_GOAL_DAYS_KEY, val));
watch(() => reminders.value.billEnabled, (val) => saveReminder(REMINDER_BILL_ENABLED_KEY, val));
watch(() => reminders.value.insuranceEnabled, (val) => saveReminder(REMINDER_INSURANCE_ENABLED_KEY, val));
watch(() => reminders.value.docEnabled, (val) => saveReminder(REMINDER_DOC_ENABLED_KEY, val));
watch(() => reminders.value.goalEnabled, (val) => saveReminder(REMINDER_GOAL_ENABLED_KEY, val));

// ─── Actions ────────────────────────────────────────────────────────────────

async function goToBaseProfile(): Promise<void> {
  try {
    await redirectToBaseWithAuthCode("/dashboard/profile");
  } catch {
    window.open("/dashboard/profile", "_blank");
  }
}

// ─── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  loadFromStorage();

  // Load profile data from auth/me (includes currency & timezone from 8086)
  try {
    await fetchProfile();
  } catch {
    // Profile fetch failed — use defaults
  }

  baseCurrency.value = getBaseCurrency();
  baseCurrencySymbol.value = getCurrencySymbol(baseCurrency.value);
  baseCurrencyName.value = getCurrencyName(baseCurrency.value);
  userTimezone.value = getUserTimezone();
  timezoneOffset.value = getTimezoneOffsetDisplay();

  loading.value = false;
});
</script>

<template>
  <div>
    <!-- Header -->
    <div class="mb-6">
      <h1 class="text-2xl font-bold tracking-tight text-navy-900 dark:text-navy-100">Settings & Preferences</h1>
      <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
        Manage your currency, timezone, display, and notification preferences
      </p>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <svg class="h-8 w-8 animate-spin text-cyan-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <div v-else class="space-y-8">
      <!-- ─── Profile & Currency (from 8086) ─── -->
      <section class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900/80 p-6">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">Profile & Currency</h2>
            <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
              These settings come from your SattaBase profile. Changes redirect to the main platform.
            </p>
          </div>
          <button
            class="inline-flex items-center gap-2 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-1.5 text-sm font-medium text-cyan-700 hover:bg-cyan-100 dark:border-cyan-800 dark:bg-cyan-950 dark:text-cyan-300 dark:hover:bg-cyan-900 transition-colors"
            @click="goToBaseProfile"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Edit on SattaBase
          </button>
        </div>

        <div class="mt-4 grid gap-4 sm:grid-cols-2">
          <!-- Base Currency -->
          <div class="rounded-lg border border-navy-100 dark:border-navy-800 bg-navy-50 dark:bg-navy-800/50 p-4">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-custom-600 dark:text-slate-custom-400">Base Currency</label>
            <div class="mt-2 flex items-center gap-3">
              <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950 text-lg font-bold text-cyan-700 dark:text-cyan-300">
                {{ baseCurrencySymbol.charAt(0) }}
              </span>
              <div>
                <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">{{ baseCurrency }}</p>
                <p class="text-xs text-slate-custom-600 dark:text-slate-custom-400">{{ baseCurrencyName }} ({{ baseCurrencySymbol }})</p>
              </div>
            </div>
          </div>

          <!-- Timezone -->
          <div class="rounded-lg border border-navy-100 dark:border-navy-800 bg-navy-50 dark:bg-navy-800/50 p-4">
            <label class="text-xs font-semibold uppercase tracking-wider text-slate-custom-600 dark:text-slate-custom-400">Timezone</label>
            <div class="mt-2 flex items-center gap-3">
              <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950 text-sm font-bold text-cyan-700 dark:text-cyan-300">
                {{ timezoneOffset.replace("GMT", "") || "UTC" }}
              </span>
              <div>
                <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">{{ userTimezone }}</p>
                <p class="text-xs text-slate-custom-600 dark:text-slate-custom-400">{{ timezoneOffset }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ─── Date & Time Format ─── -->
      <section class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900/80 p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">Date & Time Format</h2>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Choose how dates are displayed across the application
        </p>

        <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <button
            v-for="option in dateFormatOptions"
            :key="option.value"
            class="flex flex-col items-start rounded-lg border-2 p-3 text-left transition-all"
            :class="dateFormat === option.value
              ? 'border-cyan-500 bg-cyan-50 dark:border-cyan-600 dark:bg-cyan-950'
              : 'border-navy-200 hover:border-cyan-300 dark:border-navy-700 dark:hover:border-cyan-700'"
            @click="dateFormat = option.value"
          >
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">{{ option.label }}</span>
            <span class="mt-1 text-xs text-slate-custom-600 dark:text-slate-custom-400">{{ option.example }}</span>
          </button>
        </div>
      </section>

      <!-- ─── Appearance ─── -->
      <section class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900/80 p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">Appearance</h2>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Choose your preferred theme for the application
        </p>

        <div class="mt-4 grid gap-3 sm:grid-cols-3">
          <!-- Light -->
          <button
            class="flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all"
            :class="theme === 'light'
              ? 'border-cyan-500 bg-cyan-50 dark:border-cyan-600'
              : 'border-navy-200 hover:border-cyan-300 dark:border-navy-700 dark:hover:border-cyan-700'"
            @click="theme = 'light'"
          >
            <svg class="h-8 w-8 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">Light</span>
          </button>

          <!-- Dark -->
          <button
            class="flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all"
            :class="theme === 'dark'
              ? 'border-cyan-500 bg-cyan-50 dark:border-cyan-600 dark:bg-cyan-950'
              : 'border-navy-200 hover:border-cyan-300 dark:border-navy-700 dark:hover:border-cyan-700'"
            @click="theme = 'dark'"
          >
            <svg class="h-8 w-8 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">Dark</span>
          </button>

          <!-- System -->
          <button
            class="flex flex-col items-center gap-2 rounded-lg border-2 p-4 transition-all"
            :class="theme === 'system'
              ? 'border-cyan-500 bg-cyan-50 dark:border-cyan-600 dark:bg-cyan-950'
              : 'border-navy-200 hover:border-cyan-300 dark:border-navy-700 dark:hover:border-cyan-700'"
            @click="theme = 'system'"
          >
            <svg class="h-8 w-8 text-slate-custom-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">System</span>
          </button>
        </div>

        <p class="mt-3 text-xs text-slate-custom-500 dark:text-slate-custom-500">
          Currently active: <span class="font-medium">{{ effectiveTheme === "dark" ? "Dark mode" : "Light mode" }}</span>
        </p>
      </section>

      <!-- ─── Notification Reminders ─── -->
      <section class="rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900/80 p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">Notification Reminders</h2>
        <p class="mt-1 text-sm text-slate-custom-600 dark:text-slate-custom-400">
          Configure when and how you receive reminders for upcoming events
        </p>

        <div class="mt-4 space-y-4">
          <!-- Bill Reminders -->
          <div class="flex items-center justify-between rounded-lg border border-navy-100 dark:border-navy-800 bg-navy-50 dark:bg-navy-800/50 p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-950">
                <svg class="h-5 w-5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <div>
                <p class="text-sm font-medium text-navy-900 dark:text-navy-100">Bill Due Reminders</p>
                <p class="text-xs text-slate-custom-600 dark:text-slate-custom-400">Notify before bills are due</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <select
                v-model.number="reminders.billDays"
                :disabled="!reminders.billEnabled"
                class="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-900 dark:border-navy-700 dark:bg-navy-800 dark:text-navy-100"
              >
                <option v-for="d in [1, 2, 3, 5, 7, 10, 14]" :key="d" :value="d">{{ d }} days before</option>
              </select>
              <button
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2"
                :class="reminders.billEnabled ? 'bg-cyan-600' : 'bg-navy-300 dark:bg-navy-600'"
                role="switch"
                :aria-checked="reminders.billEnabled"
                @click="reminders.billEnabled = !reminders.billEnabled"
              >
                <span
                  class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                  :class="reminders.billEnabled ? 'translate-x-5' : 'translate-x-0.5'"
                ></span>
              </button>
            </div>
          </div>

          <!-- Insurance Reminders -->
          <div class="flex items-center justify-between rounded-lg border border-navy-100 dark:border-navy-800 bg-navy-50 dark:bg-navy-800/50 p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-green-100 dark:bg-green-950">
                <svg class="h-5 w-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <div>
                <p class="text-sm font-medium text-navy-900 dark:text-navy-100">Insurance Renewal Reminders</p>
                <p class="text-xs text-slate-custom-600 dark:text-slate-custom-400">Notify before policy renewals</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <select
                v-model.number="reminders.insuranceDays"
                :disabled="!reminders.insuranceEnabled"
                class="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-900 dark:border-navy-700 dark:bg-navy-800 dark:text-navy-100"
              >
                <option v-for="d in [7, 14, 30, 45, 60]" :key="d" :value="d">{{ d }} days before</option>
              </select>
              <button
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2"
                :class="reminders.insuranceEnabled ? 'bg-cyan-600' : 'bg-navy-300 dark:bg-navy-600'"
                role="switch"
                :aria-checked="reminders.insuranceEnabled"
                @click="reminders.insuranceEnabled = !reminders.insuranceEnabled"
              >
                <span
                  class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                  :class="reminders.insuranceEnabled ? 'translate-x-5' : 'translate-x-0.5'"
                ></span>
              </button>
            </div>
          </div>

          <!-- Document Expiry Reminders -->
          <div class="flex items-center justify-between rounded-lg border border-navy-100 dark:border-navy-800 bg-navy-50 dark:bg-navy-800/50 p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-950">
                <svg class="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
              </div>
              <div>
                <p class="text-sm font-medium text-navy-900 dark:text-navy-100">Document Expiry Reminders</p>
                <p class="text-xs text-slate-custom-600 dark:text-slate-custom-400">Notify before documents expire</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <select
                v-model.number="reminders.docDays"
                :disabled="!reminders.docEnabled"
                class="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-900 dark:border-navy-700 dark:bg-navy-800 dark:text-navy-100"
              >
                <option v-for="d in [7, 14, 30, 45, 60, 90]" :key="d" :value="d">{{ d }} days before</option>
              </select>
              <button
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2"
                :class="reminders.docEnabled ? 'bg-cyan-600' : 'bg-navy-300 dark:bg-navy-600'"
                role="switch"
                :aria-checked="reminders.docEnabled"
                @click="reminders.docEnabled = !reminders.docEnabled"
              >
                <span
                  class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                  :class="reminders.docEnabled ? 'translate-x-5' : 'translate-x-0.5'"
                ></span>
              </button>
            </div>
          </div>

          <!-- Goal Deadline Reminders -->
          <div class="flex items-center justify-between rounded-lg border border-navy-100 dark:border-navy-800 bg-navy-50 dark:bg-navy-800/50 p-4">
            <div class="flex items-center gap-3">
              <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-5 w-5 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <p class="text-sm font-medium text-navy-900 dark:text-navy-100">Goal Deadline Reminders</p>
                <p class="text-xs text-slate-custom-600 dark:text-slate-custom-400">Notify when savings goals are approaching deadline</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <select
                v-model.number="reminders.goalDays"
                :disabled="!reminders.goalEnabled"
                class="rounded-lg border border-navy-200 bg-white px-3 py-1.5 text-sm text-navy-900 dark:border-navy-700 dark:bg-navy-800 dark:text-navy-100"
              >
                <option v-for="d in [3, 5, 7, 14, 30]" :key="d" :value="d">{{ d }} days before</option>
              </select>
              <button
                class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:ring-offset-2"
                :class="reminders.goalEnabled ? 'bg-cyan-600' : 'bg-navy-300 dark:bg-navy-600'"
                role="switch"
                :aria-checked="reminders.goalEnabled"
                @click="reminders.goalEnabled = !reminders.goalEnabled"
              >
                <span
                  class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
                  :class="reminders.goalEnabled ? 'translate-x-5' : 'translate-x-0.5'"
                ></span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
