<script setup lang="ts">
/**
 * UserCreditsClient — User-facing credit pools and invoices dashboard.
 *
 * Features:
 *   - Displays active credit pools with status, periods remaining, and expiry
 *   - Shows credit invoices history with status badges
 *   - Provides link to request new credits via bank transfer
 *   - Responsive card layout with loading and empty states
 *   - View transaction history for each credit pool
 *
 * Used on: /dashboard/billing/credits
 */

import { ref, computed, onMounted } from "vue";
import { requireAuthAsync, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import { creditsApi } from "@/lib/credits";
import type { CreditPool, CreditInvoice, CreditTransaction, ExpiringCreditPool } from "@/lib/credits";

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true);
const loadError = ref<string | null>(null);
const credits = ref<CreditPool[]>([]);
const invoices = ref<CreditInvoice[]>([]);
const activeTab = ref<"pools" | "invoices">("pools");

// ── Credit Expiry Warning (Enhancement 3) ──
const expiringCredits = ref<ExpiringCreditPool[]>([]);
const expiryBannerDismissed = ref(false);

const showExpiryBanner = computed(() =>
  expiringCredits.value.length > 0 && !expiryBannerDismissed.value
);

// Detail modal state
const showDetailModal = ref(false);
const detailLoading = ref(false);
const selectedCredit = ref<(CreditPool & { transactions: CreditTransaction[] }) | null>(null);

// ─── Computed ────────────────────────────────────────────────────────────────

const activeCredits = computed(() =>
  credits.value.filter((c) => c.is_effectively_active)
);

const totalPeriodsRemaining = computed(() =>
  activeCredits.value.reduce((sum, c) => sum + c.periods_remaining, 0)
);

const totalValue = computed(() =>
  activeCredits.value.reduce((sum, c) => sum + c.amount_cents, 0)
);

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(async () => {
  // AUTH-13 FIX: Use requireAuthAsync() to wait for token init before checking
  if (!(await requireAuthAsync())) return;
  await fetchData();
});

async function fetchData() {
  loading.value = true;
  loadError.value = null;
  try {
    const [creditsData, invoicesData] = await Promise.all([
      creditsApi.getMyCredits(),
      creditsApi.getMyCreditInvoices(),
    ]);
    credits.value = creditsData;
    invoices.value = invoicesData;

    // Fetch expiring credits for warning banner
    try {
      expiringCredits.value = await creditsApi.getExpiringCredits();
    } catch {
      // Non-critical
    }
  } catch (err) {
    loadError.value = getErrorMessage(err);
    showToast("Failed to load credits", "error");
  } finally {
    loading.value = false;
  }
}

// ─── Actions ─────────────────────────────────────────────────────────────────

async function viewCreditDetail(credit: CreditPool) {
  showDetailModal.value = true;
  detailLoading.value = true;
  selectedCredit.value = null;
  try {
    const data = await creditsApi.getMyCreditPool(credit.id);
    selectedCredit.value = data;
  } catch (err) {
    showToast(getErrorMessage(err), "error");
    showDetailModal.value = false;
  } finally {
    detailLoading.value = false;
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatPrice(cents: number, currency: string): string {
  return new Intl.NumberFormat(navigator.language, {
    style: "currency",
    currency: currency,
  }).format(cents / 100);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString(navigator.language, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

// ENHANCEMENT-2/4: Use server-provided commitment_end instead of client-side calculation.
// The commitment_end property is computed from activated_at + credit_periods * billing_cycle
// on the backend model, ensuring consistency with the period consumption logic.
// This replaces the previous getCommitmentEnd() which used setMonth() locally.
function getCommitmentEnd(credit: CreditPool): string | null {
  // Prefer the server-computed commitment_end; fall back to expires_at for legacy pools
  return credit.commitment_end || credit.expires_at;
}

function getStatusStyle(status: string): { bg: string; text: string; dot: string } {
  switch (status) {
    case "active":
      return {
        bg: "bg-green-100 dark:bg-green-950/40",
        text: "text-green-700 dark:text-green-400",
        dot: "bg-green-500",
      };
    case "exhausted":
      return {
        bg: "bg-gray-100 dark:bg-gray-950/40",
        text: "text-gray-700 dark:text-gray-400",
        dot: "bg-gray-500",
      };
    case "expired":
      return {
        bg: "bg-red-100 dark:bg-red-950/40",
        text: "text-red-700 dark:text-red-400",
        dot: "bg-red-500",
      };
    case "refunded":
      return {
        bg: "bg-amber-100 dark:bg-amber-950/40",
        text: "text-amber-700 dark:text-amber-400",
        dot: "bg-amber-500",
      };
    case "cancelled":
      return {
        bg: "bg-gray-100 dark:bg-gray-950/40",
        text: "text-gray-700 dark:text-gray-400",
        dot: "bg-gray-500",
      };
    default:
      return {
        bg: "bg-gray-100 dark:bg-gray-950/40",
        text: "text-gray-700 dark:text-gray-400",
        dot: "bg-gray-500",
      };
  }
}

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    manual: "Manual Entry",
    local_gateway: "Local Gateway",
    bank_transfer: "Bank Transfer",
    cash: "Cash Payment",
  };
  return labels[source] || source;
}

function getInvoiceStatusStyle(status: string): { bg: string; text: string; dot: string } {
  switch (status) {
    case "paid":
      return {
        bg: "bg-green-100 dark:bg-green-950/40",
        text: "text-green-700 dark:text-green-400",
        dot: "bg-green-500",
      };
    case "issued":
      return {
        bg: "bg-blue-100 dark:bg-blue-950/40",
        text: "text-blue-700 dark:text-blue-400",
        dot: "bg-blue-500",
      };
    case "draft":
      return {
        bg: "bg-gray-100 dark:bg-gray-950/40",
        text: "text-gray-700 dark:text-gray-400",
        dot: "bg-gray-500",
      };
    case "void":
      return {
        bg: "bg-red-100 dark:bg-red-950/40",
        text: "text-red-700 dark:text-red-400",
        dot: "bg-red-500",
      };
    default:
      return {
        bg: "bg-gray-100 dark:bg-gray-950/40",
        text: "text-gray-700 dark:text-gray-400",
        dot: "bg-gray-500",
      };
  }
}

function getExpiryUrgencyStyle(urgency: string): { bg: string; border: string; text: string; badge: string } {
  switch (urgency) {
    case "urgent":
    case "grace_period":
      return {
        bg: "bg-red-50 dark:bg-red-950",
        border: "border-red-200 dark:border-red-800",
        text: "text-red-800 dark:text-red-200",
        badge: "bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400",
      };
    case "warning":
      return {
        bg: "bg-orange-50 dark:bg-orange-950",
        border: "border-orange-200 dark:border-orange-800",
        text: "text-orange-800 dark:text-orange-200",
        badge: "bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-400",
      };
    default:
      return {
        bg: "bg-amber-50 dark:bg-amber-950",
        border: "border-amber-200 dark:border-amber-800",
        text: "text-amber-800 dark:text-amber-200",
        badge: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-400",
      };
  }
}

function getTransactionActionLabel(action: string): string {
  const labels: Record<string, string> = {
    purchase: "Purchase",
    period_consume: "Period Consumed",
    refund: "Refund",
    adjust: "Adjustment",
    expire: "Expired",
  };
  return labels[action] || action;
}

// ── Credit Invoice PDF Download ────────────────────────────────────────────────
// Credit invoice PDFs require Authorization header (JWTAuth(HttpBearer)),
// so we can't use a plain <a href> link. We use fetch() with Bearer token,
// then open the resulting Blob URL.

const downloadingInvoice = ref<string | null>(null);

async function downloadInvoicePdf(invoiceNumber: string) {
  downloadingInvoice.value = invoiceNumber;
  try {
    const blobUrl = await creditsApi.downloadCreditInvoicePdf(invoiceNumber);
    window.open(blobUrl, "_blank");
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  } catch (err: any) {
    showToast(err.message || "Failed to download invoice PDF", "error");
  } finally {
    downloadingInvoice.value = null;
  }
}
</script>

<template>
  <div>
    <!-- Page Header -->
    <div class="mb-8">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight md:text-3xl">Credit Pools</h1>
          <p class="mt-1 text-[var(--color-muted-foreground)]">
            Manage your prepaid credits and view purchase history.
          </p>
        </div>
        <a href="/dashboard/billing/credits/request" class="btn-primary text-sm shrink-0">
          <svg class="h-4 w-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          Request Credits
        </a>
      </div>
    </div>

    <!-- ── Credit Expiry Warning Banner (Enhancement 3) ── -->
    <div v-if="showExpiryBanner" class="space-y-3 mb-6">
      <div
        v-for="exp in expiringCredits"
        :key="exp.id"
        :class="[
          getExpiryUrgencyStyle(exp.urgency).bg,
          getExpiryUrgencyStyle(exp.urgency).border,
          getExpiryUrgencyStyle(exp.urgency).text,
        ]"
        class="rounded-lg border px-4 py-3"
      >
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div class="flex items-start gap-3">
            <svg class="mt-0.5 h-5 w-5 shrink-0 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium">
                  {{ exp.product_name }} — {{ exp.plan_name }}
                </p>
                <span :class="getExpiryUrgencyStyle(exp.urgency).badge" class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide">
                  <span v-if="exp.in_grace_period">Grace Period</span>
                  <span v-else-if="exp.urgency === 'urgent'">{{ exp.days_until_expiry }}d left</span>
                  <span v-else-if="exp.urgency === 'warning'">{{ exp.days_until_expiry }}d left</span>
                  <span v-else>{{ exp.days_until_expiry }}d left</span>
                </span>
              </div>
              <p class="text-xs mt-0.5 opacity-80">
                <span v-if="exp.in_grace_period">Your credit is in the 24-hour grace period. Access will be revoked after grace period ends.</span>
                <span v-else>Expires on {{ formatDate(exp.commitment_end || exp.expires_at || exp.current_period_end) }}. {{ exp.periods_remaining }} period(s) remaining.</span>
              </p>
            </div>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <a
              href="/dashboard/billing/credits/request"
              class="inline-flex items-center gap-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 px-3 py-1.5 text-xs font-medium text-white transition-colors"
            >
              Renew Credits
            </a>
            <a
              href="/dashboard/billing"
              class="inline-flex items-center gap-1.5 rounded-lg bg-white/60 dark:bg-white/10 px-3 py-1.5 text-xs font-medium transition-colors hover:bg-white/80 dark:hover:bg-white/20"
            >
              Use Stripe
            </a>
          </div>
        </div>
      </div>
      <div class="flex justify-end">
        <button
          @click="expiryBannerDismissed = true"
          class="text-xs text-[var(--color-muted-foreground)] hover:text-foreground transition-colors"
        >
          Dismiss warnings
        </button>
      </div>
    </div>

    <!-- Loading Skeleton -->
    <template v-if="loading">
      <div class="grid gap-4 sm:grid-cols-3 mb-8">
        <div v-for="i in 3" :key="'skel-stat-' + i" class="card p-6 animate-pulse">
          <div class="h-4 w-28 rounded bg-[var(--color-muted)]"></div>
          <div class="mt-3 h-7 w-24 rounded bg-[var(--color-muted)]"></div>
        </div>
      </div>
    </template>

    <!-- Error State -->
    <template v-else-if="loadError">
      <div class="card flex flex-col items-center justify-center py-16 text-center px-6">
        <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100 dark:bg-red-950">
          <svg class="h-8 w-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 class="text-lg font-semibold text-red-800 dark:text-red-300">Failed to Load Credits</h3>
        <p class="mt-2 text-sm text-[var(--color-muted-foreground)] max-w-sm">{{ loadError }}</p>
        <button class="btn-secondary mt-4" @click="fetchData">Try Again</button>
      </div>
    </template>

    <template v-else>
      <!-- Summary Stats -->
      <div class="grid gap-4 sm:grid-cols-3 mb-8">
        <!-- Active Credit Pools -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Active Pools</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-950">
              <svg class="h-4 w-4 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ activeCredits.length }}</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">
            {{ credits.length - activeCredits.length }} inactive
          </p>
        </div>

        <!-- Periods Remaining -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Periods Remaining</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-green-100 dark:bg-green-950">
              <svg class="h-4 w-4 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ totalPeriodsRemaining }}</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">billing cycles</p>
        </div>

        <!-- Total Value -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Total Value</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-950">
              <svg class="h-4 w-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">
            {{ activeCredits.length > 0 ? formatPrice(totalValue, activeCredits[0].currency) : "—" }}
          </p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">active credit value</p>
        </div>
      </div>

      <!-- Tab Navigation -->
      <div class="flex items-center gap-1 rounded-lg bg-[var(--color-muted)] p-1 mb-6 w-fit">
        <button
          class="rounded-md px-4 py-2 text-sm font-medium transition-all duration-150"
          :class="activeTab === 'pools'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-[var(--color-muted-foreground)] hover:text-foreground'"
          @click="activeTab = 'pools'"
        >
          Credit Pools
          <span
            v-if="credits.length > 0"
            class="ml-1.5 inline-flex items-center justify-center h-5 min-w-[20px] rounded-full px-1.5 text-[10px] font-semibold"
            :class="activeTab === 'pools' ? 'bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-400' : 'bg-background/50'"
          >
            {{ credits.length }}
          </span>
        </button>
        <button
          class="rounded-md px-4 py-2 text-sm font-medium transition-all duration-150"
          :class="activeTab === 'invoices'
            ? 'bg-background text-foreground shadow-sm'
            : 'text-[var(--color-muted-foreground)] hover:text-foreground'"
          @click="activeTab = 'invoices'"
        >
          Invoices
          <span
            v-if="invoices.length > 0"
            class="ml-1.5 inline-flex items-center justify-center h-5 min-w-[20px] rounded-full px-1.5 text-[10px] font-semibold"
            :class="activeTab === 'invoices' ? 'bg-brand-100 text-brand-700 dark:bg-brand-950 dark:text-brand-400' : 'bg-background/50'"
          >
            {{ invoices.length }}
          </span>
        </button>
      </div>

      <!-- Credit Pools Tab -->
      <div v-if="activeTab === 'pools'">
        <!-- Empty State -->
        <div v-if="credits.length === 0" class="card flex flex-col items-center justify-center py-16 text-center px-6">
          <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-muted)]">
            <svg class="h-8 w-8 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 class="text-base font-semibold">No credit pools yet</h3>
          <p class="mt-1 text-sm text-[var(--color-muted-foreground)] max-w-sm">
            Credits are issued when you pay via bank transfer. Request credits to get started.
          </p>
          <a href="/dashboard/billing/credits/request" class="btn-primary mt-4 text-sm">
            Request Credits
          </a>
        </div>

        <!-- Credit Pools List -->
        <div v-else class="space-y-4">
          <div
            v-for="credit in credits"
            :key="credit.id"
            class="card p-6 transition-all duration-200 hover:shadow-md cursor-pointer"
            @click="viewCreditDetail(credit)"
          >
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <!-- Left: Info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-3 mb-2">
                  <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg gradient-brand text-white text-sm font-bold shadow-md shadow-brand-600/20">
                    {{ credit.product_name.charAt(0) }}
                  </div>
                  <div>
                    <h3 class="text-base font-semibold truncate">{{ credit.product_name }}</h3>
                    <p class="text-sm text-[var(--color-muted-foreground)]">{{ credit.plan_name }} Plan</p>
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-3 text-sm text-[var(--color-muted-foreground)]">
                  <!-- Status Badge -->
                  <span
                    :class="[getStatusStyle(credit.status).bg, getStatusStyle(credit.status).text]"
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  >
                    <span :class="getStatusStyle(credit.status).dot" class="h-1.5 w-1.5 rounded-full" />
                    {{ credit.status.charAt(0).toUpperCase() + credit.status.slice(1) }}
                  </span>

                  <!-- ENHANCEMENT-2/5: Commitment Period with date range -->
                  <span class="flex items-center gap-1">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    {{ credit.credit_periods }}-period commitment
                    <template v-if="credit.current_period_start">
                      ({{ formatDate(credit.current_period_start) }} – {{ formatDate(getCommitmentEnd(credit)) }})
                    </template>
                  </span>

                  <!-- ENHANCEMENT-5: Hard expiry indicator when expires_at is set -->
                  <span v-if="credit.expires_at" class="flex items-center gap-1 text-red-600 dark:text-red-400">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Hard deadline: {{ formatDate(credit.expires_at) }}
                  </span>

                  <!-- Periods Progress -->
                  <span class="flex items-center gap-1">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {{ credit.periods_remaining }} / {{ credit.credit_periods }} remaining
                  </span>

                  <!-- Source -->
                  <span class="flex items-center gap-1">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                    {{ getSourceLabel(credit.source) }}
                  </span>
                </div>

                <!-- ENHANCEMENT-2/5: Non-renewal notice for active pools -->
                <div v-if="credit.status === 'active' && credit.is_effectively_active" class="mt-3 flex items-start gap-2 text-xs text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 rounded-md px-3 py-2 border border-amber-200 dark:border-amber-800">
                  <svg class="h-3.5 w-3.5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span v-if="credit.expires_at">
                    This credit has a hard deadline of {{ formatDate(credit.expires_at) }} and will expire on that date regardless of remaining periods. Credits do not auto-renew.
                  </span>
                  <span v-else>
                    This credit does not auto-renew. Purchase new credits before expiry to maintain uninterrupted access.
                  </span>
                </div>
              </div>

              <!-- Right: Value -->
              <div class="text-right shrink-0">
                <p class="text-lg font-bold">{{ credit.display_amount }}</p>
                <p class="text-xs text-[var(--color-muted-foreground)]">
                  Issued {{ formatDate(credit.created_at) }}
                </p>
                <p class="text-xs text-brand-600 dark:text-brand-400 mt-1">
                  Click to view details →
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Invoices Tab -->
      <div v-if="activeTab === 'invoices'">
        <!-- Empty State -->
        <div v-if="invoices.length === 0" class="card flex flex-col items-center justify-center py-16 text-center px-6">
          <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-muted)]">
            <svg class="h-8 w-8 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 class="text-base font-semibold">No credit invoices</h3>
          <p class="mt-1 text-sm text-[var(--color-muted-foreground)] max-w-sm">
            Invoices are generated when your credit request is approved.
          </p>
        </div>

        <!-- Invoices Table -->
        <div v-else class="card overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-[var(--color-muted)]/50 text-xs font-semibold uppercase tracking-wider text-[var(--color-muted-foreground)]">
                <tr>
                  <th class="px-6 py-3 text-left">Invoice</th>
                  <th class="px-6 py-3 text-left">Product / Plan</th>
                  <th class="px-6 py-3 text-center">Status</th>
                  <th class="px-6 py-3 text-right">Amount</th>
                  <th class="px-6 py-3 text-right">Issued</th>
                  <th class="px-6 py-3 text-right">PDF</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border">
                <tr
                  v-for="invoice in invoices"
                  :key="invoice.id"
                  class="transition-colors hover:bg-[var(--color-muted)]/20"
                >
                  <td class="px-6 py-4">
                    <span class="font-mono text-sm font-medium">{{ invoice.invoice_number }}</span>
                  </td>
                  <td class="px-6 py-4">
                    <p class="text-sm font-medium">{{ invoice.product_name }}</p>
                    <p class="text-xs text-[var(--color-muted-foreground)]">{{ invoice.plan_name }}</p>
                  </td>
                  <td class="px-6 py-4 text-center">
                    <span
                      :class="[getInvoiceStatusStyle(invoice.status).bg, getInvoiceStatusStyle(invoice.status).text]"
                      class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                    >
                      <span :class="getInvoiceStatusStyle(invoice.status).dot" class="h-1.5 w-1.5 rounded-full" />
                      {{ invoice.status.charAt(0).toUpperCase() + invoice.status.slice(1) }}
                    </span>
                  </td>
                  <td class="px-6 py-4 text-right">
                    <p class="text-sm font-semibold">{{ formatPrice(invoice.total_cents, invoice.currency) }}</p>
                    <p v-if="invoice.tax_cents > 0" class="text-xs text-[var(--color-muted-foreground)]">
                      incl. {{ formatPrice(invoice.tax_cents, invoice.currency) }} tax
                    </p>
                  </td>
                  <td class="px-6 py-4 text-right text-sm text-[var(--color-muted-foreground)]">
                    {{ formatDate(invoice.issued_at || invoice.created_at) }}
                  </td>
                  <td class="px-6 py-4 text-right">
                    <button
                      :disabled="downloadingInvoice === invoice.invoice_number"
                      class="inline-flex items-center justify-center h-7 w-7 rounded-md text-[var(--color-muted-foreground)] hover:text-foreground hover:bg-accent transition-colors disabled:opacity-50 disabled:cursor-wait"
                      title="Download PDF"
                      @click="downloadInvoicePdf(invoice.invoice_number)"
                    >
                      <svg v-if="downloadingInvoice === invoice.invoice_number" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17v3a2 2 0 002 2h14a2 2 0 002-2v-3" />
                      </svg>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Credit Detail Modal                                                      -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <div
      v-if="showDetailModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      @click.self="showDetailModal = false"
    >
      <div class="bg-background rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div class="p-6 border-b border-border">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold">Credit Pool Details</h2>
            <button
              type="button"
              class="text-muted-foreground hover:text-foreground"
              @click="showDetailModal = false"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div v-if="detailLoading" class="p-6 animate-pulse space-y-4">
          <div class="h-4 w-32 rounded bg-muted"></div>
          <div class="h-8 w-48 rounded bg-muted"></div>
        </div>

        <template v-else-if="selectedCredit">
          <div class="p-6 space-y-6">
            <!-- Info Grid -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-muted-foreground">Product</p>
                <p class="text-sm font-medium">{{ selectedCredit.product_name }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">Plan</p>
                <p class="text-sm">{{ selectedCredit.plan_name }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">Status</p>
                <span
                  :class="[getStatusStyle(selectedCredit.status).bg, getStatusStyle(selectedCredit.status).text]"
                  class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                >
                  <span :class="getStatusStyle(selectedCredit.status).dot" class="h-1.5 w-1.5 rounded-full" />
                  {{ selectedCredit.status.charAt(0).toUpperCase() + selectedCredit.status.slice(1) }}
                </span>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">Amount</p>
                <p class="text-sm font-semibold">{{ selectedCredit.display_amount }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">Periods Remaining</p>
                <p class="text-sm">{{ selectedCredit.periods_remaining }} / {{ selectedCredit.credit_periods }}</p>
              </div>
              <div>
                <p class="text-xs text-muted-foreground">Source</p>
                <p class="text-sm capitalize">{{ getSourceLabel(selectedCredit.source) }}</p>
              </div>
            </div>

            <!-- ENHANCEMENT-2/5: Commitment Details Section in Detail Modal -->
            <div class="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4">
              <h4 class="text-xs font-semibold text-amber-900 dark:text-amber-200 uppercase tracking-wide mb-3">Commitment Details</h4>
              <div class="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span class="text-amber-700 dark:text-amber-400 text-xs">Commitment Duration</span>
                  <p class="font-medium text-amber-900 dark:text-amber-200">{{ selectedCredit.credit_periods }} period(s)</p>
                </div>
                <div>
                  <span class="text-amber-700 dark:text-amber-400 text-xs">Auto-Renewal</span>
                  <p class="font-medium text-amber-900 dark:text-amber-200">No</p>
                </div>
                <div>
                  <span class="text-amber-700 dark:text-amber-400 text-xs">Start Date</span>
                  <p class="font-medium text-amber-900 dark:text-amber-200">{{ formatDate(selectedCredit.current_period_start) }}</p>
                </div>
                <div>
                  <!-- ENHANCEMENT-5: Show commitment end with appropriate label -->
                  <span class="text-amber-700 dark:text-amber-400 text-xs">Commitment End</span>
                  <p class="font-medium text-amber-900 dark:text-amber-200">{{ formatDate(getCommitmentEnd(selectedCredit)) }}</p>
                </div>
                <!-- ENHANCEMENT-5: Show hard expiry when set, distinguishing from commitment end -->
                <div v-if="selectedCredit.expires_at" class="col-span-2">
                  <span class="text-red-600 dark:text-red-400 text-xs font-medium">Hard Expiry Deadline</span>
                  <p class="font-medium text-red-700 dark:text-red-300">{{ formatDate(selectedCredit.expires_at) }}</p>
                  <p class="text-xs text-red-600/70 dark:text-red-400/70 mt-0.5">Access ends on this date regardless of remaining periods.</p>
                </div>
              </div>
              <div class="mt-3 flex items-start gap-2 text-xs text-amber-800 dark:text-amber-300">
                <svg class="h-3.5 w-3.5 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span v-if="selectedCredit.expires_at">
                  Non-refundable prepaid commitment with a hard expiry deadline. Access will end on {{ formatDate(selectedCredit.expires_at) }} even if periods remain unused. Credits do not auto-renew.
                </span>
                <span v-else>
                  Non-refundable prepaid commitment. Access will be revoked when all periods are consumed. Credits do not auto-renew.
                </span>
              </div>
            </div>

            <!-- Transactions -->
            <div v-if="selectedCredit.transactions && selectedCredit.transactions.length > 0">
              <h3 class="text-sm font-semibold mb-3">Transaction History</h3>
              <div class="border border-border rounded-lg overflow-hidden">
                <table class="w-full text-sm">
                  <thead class="bg-muted/50">
                    <tr>
                      <th class="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Action</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Periods</th>
                      <th class="px-3 py-2 text-right text-xs font-medium text-muted-foreground">Balance</th>
                      <th class="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Reason</th>
                      <th class="px-3 py-2 text-left text-xs font-medium text-muted-foreground">Date</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border">
                    <tr v-for="tx in selectedCredit.transactions" :key="tx.id">
                      <td class="px-3 py-2">{{ getTransactionActionLabel(tx.action) }}</td>
                      <td class="px-3 py-2 text-right font-mono">
                        <span :class="tx.periods_delta > 0 ? 'text-green-600' : tx.periods_delta < 0 ? 'text-red-600' : ''">
                          {{ tx.periods_delta > 0 ? '+' : '' }}{{ tx.periods_delta }}
                        </span>
                      </td>
                      <td class="px-3 py-2 text-right font-mono">{{ tx.periods_balance }}</td>
                      <td class="px-3 py-2 text-muted-foreground">{{ tx.reason || '—' }}</td>
                      <td class="px-3 py-2 text-muted-foreground">{{ formatDate(tx.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <div v-else class="text-center py-4 text-muted-foreground text-sm">
              No transactions recorded yet.
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>
