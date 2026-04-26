<script setup lang="ts">
// Dashboard home — Vue interactive island
// Shows user greeting, quick stats, quick actions, recent transactions, and getting started checklist

import { ref, onMounted } from "vue";
import { getCurrentUser, requireAuth, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import type { UserProfile } from "@/lib/auth";

const user = ref<UserProfile | null>(null);
const loading = ref(true);

const stats = ref([
  { label: "Total Balance", value: "--", icon: "wallet" },
  { label: "Monthly Income", value: "--", icon: "trending-up" },
  { label: "Monthly Expenses", value: "--", icon: "trending-down" },
  { label: "Transactions", value: "0", icon: "repeat" },
]);

const gettingStartedItems = ref([
  { id: "profile", label: "Complete your profile", description: "Add your name and preferences" },
  { id: "category", label: "Set up categories", description: "Organize transactions by type" },
  { id: "budget", label: "Create a budget", description: "Set spending limits for each category" },
  { id: "transaction", label: "Add your first transaction", description: "Start tracking income and expenses" },
]);

onMounted(async () => {
  if (!requireAuth()) return;

  try {
    user.value = await getCurrentUser();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    loading.value = false;
  }
});

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
</script>

<template>
  <div>
    <!-- Email Verification Banner -->
    <div
      v-if="!loading && user && !user.is_email_verified"
      class="mb-6 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 dark:border-yellow-800 dark:bg-yellow-950"
    >
      <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-start gap-3">
          <svg class="mt-0.5 h-5 w-5 shrink-0 text-yellow-600 dark:text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
          </svg>
          <div>
            <p class="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Your email is not verified
            </p>
            <p class="text-xs text-yellow-700 dark:text-yellow-300 mt-0.5">
              Please verify your email address to unlock all features. A verification code can be sent to your inbox.
            </p>
          </div>
        </div>
        <a
          href="/auth/verify-email"
          class="inline-flex shrink-0 items-center gap-1.5 rounded-lg bg-yellow-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-yellow-700 dark:bg-yellow-500 dark:hover:bg-yellow-600"
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Verify now
        </a>
      </div>
    </div>

    <!-- Welcome Header -->
    <div class="mb-8">
      <h1 v-if="loading" class="text-2xl font-bold tracking-tight md:text-3xl">
        <span class="inline-block h-8 w-48 animate-pulse rounded bg-[var(--color-muted)]" />
      </h1>
      <h1 v-else class="text-2xl font-bold tracking-tight md:text-3xl">
        {{ getGreeting() }}{{ user ? `, ${user.first_name}` : "" }}
      </h1>
      <p class="mt-1 text-[var(--color-muted-foreground)]">
        Here's an overview of your finances.
      </p>
    </div>

    <!-- Loading Skeleton -->
    <template v-if="loading">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <div v-for="i in 4" :key="i" class="card p-6 animate-pulse">
          <div class="flex items-center justify-between">
            <div class="h-4 w-28 rounded bg-[var(--color-muted)]" />
            <div class="h-8 w-8 rounded-lg bg-[var(--color-muted)]" />
          </div>
          <div class="mt-3 h-7 w-20 rounded bg-[var(--color-muted)]" />
        </div>
      </div>
      <div class="card animate-pulse mb-8">
        <div class="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
          <div class="h-5 w-40 rounded bg-[var(--color-muted)]" />
        </div>
        <div class="flex flex-col items-center justify-center py-16">
          <div class="h-12 w-12 rounded-full bg-[var(--color-muted)]" />
        </div>
      </div>
      <div class="grid gap-6 lg:grid-cols-3">
        <div class="card p-6 animate-pulse lg:col-span-2">
          <div class="h-5 w-40 rounded bg-[var(--color-muted)] mb-4" />
          <div class="space-y-3">
            <div v-for="i in 3" :key="i" class="flex items-center gap-3">
              <div class="h-4 w-4 rounded bg-[var(--color-muted)]" />
              <div class="flex-1">
                <div class="h-4 w-48 rounded bg-[var(--color-muted)]" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <!-- Stats Grid -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <div
          v-for="stat in stats"
          :key="stat.label"
          class="card p-6"
        >
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">
              {{ stat.label }}
            </p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-950">
              <svg
                v-if="stat.icon === 'wallet'"
                class="h-4 w-4 text-brand-600 dark:text-brand-400"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
              <svg
                v-else-if="stat.icon === 'trending-up'"
                class="h-4 w-4 text-green-600 dark:text-green-400"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              <svg
                v-else-if="stat.icon === 'trending-down'"
                class="h-4 w-4 text-red-600 dark:text-red-400"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
              </svg>
              <svg
                v-else
                class="h-4 w-4 text-[var(--color-muted-foreground)]"
                fill="none" stroke="currentColor" viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ stat.value }}</p>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="mb-8">
        <h2 class="text-lg font-semibold mb-4">Quick Actions</h2>
        <div class="grid gap-3 sm:grid-cols-3">
          <button
            disabled
            class="card flex items-center gap-3 p-4 text-left opacity-60 cursor-not-allowed transition-colors hover:bg-[var(--color-accent)]"
            aria-label="Add Transaction — coming soon"
          >
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-950">
              <svg class="h-5 w-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </div>
            <div>
              <p class="text-sm font-medium">Add Transaction</p>
              <p class="text-xs text-[var(--color-muted-foreground)]">Coming soon</p>
            </div>
          </button>
          <button
            disabled
            class="card flex items-center gap-3 p-4 text-left opacity-60 cursor-not-allowed transition-colors hover:bg-[var(--color-accent)]"
            aria-label="View Reports — coming soon"
          >
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-950">
              <svg class="h-5 w-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <p class="text-sm font-medium">View Reports</p>
              <p class="text-xs text-[var(--color-muted-foreground)]">Coming soon</p>
            </div>
          </button>
          <button
            disabled
            class="card flex items-center gap-3 p-4 text-left opacity-60 cursor-not-allowed transition-colors hover:bg-[var(--color-accent)]"
            aria-label="Set Budget — coming soon"
          >
            <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-950">
              <svg class="h-5 w-5 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <p class="text-sm font-medium">Set Budget</p>
              <p class="text-xs text-[var(--color-muted-foreground)]">Coming soon</p>
            </div>
          </button>
        </div>
      </div>

      <!-- Two Column: Recent Transactions + Getting Started -->
      <div class="grid gap-6 lg:grid-cols-3">
        <!-- Recent Transactions -->
        <div class="card lg:col-span-2">
          <div class="flex items-center justify-between border-b border-[var(--color-border)] px-6 py-4">
            <h2 class="text-lg font-semibold">Recent Transactions</h2>
            <span class="text-sm text-[var(--color-muted-foreground)]">Coming soon</span>
          </div>
          <div class="flex flex-col items-center justify-center py-16 text-center px-6">
            <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-muted)]">
              <svg class="h-8 w-8 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">No transactions yet</p>
            <p class="mt-1 text-xs text-[var(--color-muted-foreground)] max-w-xs">
              Start tracking your finances by adding your first income or expense transaction.
            </p>
          </div>
        </div>

        <!-- Getting Started Checklist -->
        <div class="card p-6">
          <h2 class="text-lg font-semibold mb-4 flex items-center gap-2">
            <svg class="h-5 w-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Getting Started
          </h2>
          <ul class="space-y-3" role="list">
            <li
              v-for="item in gettingStartedItems"
              :key="item.id"
              class="flex items-start gap-3"
            >
              <div class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded border-2 border-[var(--color-border)] bg-[var(--color-background)]">
              </div>
              <div class="min-w-0">
                <p class="text-sm font-medium leading-tight">{{ item.label }}</p>
                <p class="text-xs text-[var(--color-muted-foreground)] mt-0.5">{{ item.description }}</p>
              </div>
            </li>
          </ul>
          <p class="mt-4 text-xs text-[var(--color-muted-foreground)]">
            Complete these steps to get the most out of Satta Ledger.
          </p>
        </div>
      </div>
    </template>
  </div>
</template>
