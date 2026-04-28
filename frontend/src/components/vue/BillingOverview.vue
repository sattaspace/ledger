<script setup lang="ts">
/**
 * BillingOverview — Main billing dashboard Vue island.
 *
 * Displays:
 *  - Stats row: active subscriptions count, products, next billing date
 *  - Subscription cards per product with status, plan, period end
 *  - Quick actions: manage subscription, view plans, change plan
 *  - Products catalog with links to plan comparison pages
 */

import { ref, computed, onMounted } from "vue";
import { requireAuth, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import {
  billingApi,
  formatPrice,
  formatCycle,
  formatDate,
  getStatusStyle,
} from "@/lib/billing";
import type {
  ProductSchema,
  SubscriptionOutputSchema,
} from "@/lib/billing";

const loading = ref(true);
const products = ref<ProductSchema[]>([]);
const subscriptions = ref<SubscriptionOutputSchema[]>([]);
const actionLoading = ref<string | null>(null);

const activeSubscriptions = computed(() =>
  subscriptions.value.filter((s) => ["active", "trialing", "past_due", "canceled"].includes(s.status)),
);

const hasPaidSubscription = computed(() =>
  subscriptions.value.some(
    (s) => ["active", "trialing", "past_due"].includes(s.status) && s.plan_slug !== "free",
  ),
);

const stats = computed(() => {
  const active = subscriptions.value.filter((s) =>
    ["active", "trialing"].includes(s.status),
  );
  const nextEnd = subscriptions.value
    .filter((s) => s.current_period_end && s.status !== "expired")
    .sort((a, b) => new Date(a.current_period_end!).getTime() - new Date(b.current_period_end!).getTime());
  const paidCount = active.filter((s) => {
    const plan = subscriptions.value.find((sub) => sub.id === s.id);
    return plan && !plan.plan_slug.includes("free");
  });

  return {
    activeCount: active.length,
    productCount: products.value.length,
    nextBillingDate: nextEnd.length > 0 ? nextEnd[0].current_period_end : null,
    paidPlans: paidCount.length,
  };
});

onMounted(async () => {
  if (!requireAuth()) return;

  // Handle Stripe checkout redirect feedback
  const params = new URLSearchParams(window.location.search);
  const checkoutStatus = params.get("checkout");
  const sessionId = params.get("session_id");
  if (checkoutStatus === "success" && sessionId) {
    try {
      showToast("Processing payment...", "info", { duration: 3000 });
      const result = await billingApi.confirmCheckout(sessionId);
      const trialNote = result.status === "trialing"
        ? ` (trial ends ${new Date(result.trial_end!).toLocaleDateString()})`
        : "";
      showToast(`Upgraded to ${result.plan_name}!${trialNote}`, "success", { duration: 8000 });
    } catch (err) {
      showToast(getErrorMessage(err), "error", { duration: 8000 });
    }
    window.history.replaceState({}, "", "/dashboard/billing");
  } else if (checkoutStatus === "canceled") {
    showToast("Checkout was canceled. No changes were made.", "info", { duration: 5000 });
    window.history.replaceState({}, "", "/dashboard/billing");
  }

  try {
    const [productsData, subsData] = await Promise.all([
      billingApi.getProducts(),
      billingApi.getSubscriptions(),
    ]);
    products.value = productsData;
    subscriptions.value = subsData;
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    loading.value = false;
  }
});

async function handleCancel(productSlug: string) {
  showToast("Are you sure? You'll retain access until the end of your billing period.", "warning", {
    duration: 0,
    action: {
      label: "Yes, cancel",
      onClick: () => executeCancel(productSlug),
    },
  });
}

async function executeCancel(productSlug: string) {
  actionLoading.value = `cancel-${productSlug}`;
  try {
    await billingApi.cancelSubscription(productSlug);
    showToast("Subscription canceled. Access continues until period end.", "success");
    subscriptions.value = await billingApi.getSubscriptions();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function handleReactivate(productSlug: string) {
  actionLoading.value = `reactivate-${productSlug}`;
  try {
    await billingApi.reactivateSubscription(productSlug);
    showToast("Subscription reactivated successfully.", "success");
    subscriptions.value = await billingApi.getSubscriptions();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function handleManageBilling() {
  actionLoading.value = "portal";
  try {
    const result = await billingApi.createPortalSession();
    window.location.href = result.portal_url;
  } catch (err) {
    showToast(getErrorMessage(err), "error");
    actionLoading.value = null;
  }
}
</script>

<template>
  <div>
    <!-- Page Header -->
    <div class="mb-8">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight md:text-3xl">Billing &amp; Subscriptions</h1>
          <p class="mt-1 text-[var(--color-muted-foreground)]">
            Manage your subscriptions, view plans, and control access across all products.
          </p>
        </div>
        <button
          v-if="hasPaidSubscription"
          :disabled="actionLoading === 'portal'"
          class="btn-secondary text-sm shrink-0"
          @click="handleManageBilling"
        >
          <svg class="h-4 w-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          {{ actionLoading === 'portal' ? 'Opening...' : 'Manage Billing' }}
        </button>
      </div>
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
      <div v-for="i in 3" :key="'sub-' + i" class="card p-6 animate-pulse mb-4">
        <div class="flex items-center justify-between mb-4">
          <div class="h-5 w-40 rounded bg-[var(--color-muted)]" />
          <div class="h-6 w-24 rounded-full bg-[var(--color-muted)]" />
        </div>
        <div class="h-4 w-64 rounded bg-[var(--color-muted)]" />
      </div>
    </template>

    <template v-else>
      <!-- Stats Row -->
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <!-- Active Subscriptions -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Active Plans</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-100 dark:bg-brand-950">
              <svg class="h-4 w-4 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ stats.activeCount }}</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">across {{ stats.productCount }} product{{ stats.productCount !== 1 ? 's' : '' }}</p>
        </div>

        <!-- Products -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Products</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-950">
              <svg class="h-4 w-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ stats.productCount }}</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">available services</p>
        </div>

        <!-- Next Billing -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Next Billing</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 dark:bg-purple-950">
              <svg class="h-4 w-4 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ stats.nextBillingDate ? formatDate(stats.nextBillingDate) : '—' }}</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">earliest renewal</p>
        </div>

        <!-- Paid Plans -->
        <div class="card p-6">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Paid Plans</p>
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-950">
              <svg class="h-4 w-4 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <p class="mt-2 text-2xl font-bold">{{ stats.paidPlans }}</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)]">premium subscriptions</p>
        </div>
      </div>

      <!-- Subscriptions Section -->
      <div class="mb-8">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">Your Subscriptions</h2>
          <span class="text-sm text-[var(--color-muted-foreground)]">
            {{ activeSubscriptions.length }} active
          </span>
        </div>

        <!-- No subscriptions state -->
        <div v-if="subscriptions.length === 0" class="card flex flex-col items-center justify-center py-16 text-center px-6">
          <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-muted)]">
            <svg class="h-8 w-8 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <p class="text-sm font-medium text-[var(--color-muted-foreground)]">No subscriptions yet</p>
          <p class="mt-1 text-xs text-[var(--color-muted-foreground)] max-w-xs">
            Browse available products and plans below to get started.
          </p>
        </div>

        <!-- Subscription Cards -->
        <div v-else class="space-y-4">
          <div
            v-for="sub in subscriptions"
            :key="sub.id"
            class="card p-6 transition-all duration-200 hover:shadow-md"
          >
            <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <!-- Left: Product + Plan info -->
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-3 mb-2">
                  <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg gradient-brand text-white text-sm font-bold shadow-md shadow-brand-600/20">
                    {{ sub.product_name.charAt(0) }}
                  </div>
                  <div>
                    <h3 class="text-base font-semibold truncate">{{ sub.product_name }}</h3>
                    <p class="text-sm text-[var(--color-muted-foreground)]">
                      {{ sub.plan_name }} Plan
                    </p>
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-3 text-sm text-[var(--color-muted-foreground)]">
                  <!-- Status Badge -->
                  <span
                    :class="[getStatusStyle(sub.status).bg, getStatusStyle(sub.status).text]"
                    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                  >
                    <span
                      :class="getStatusStyle(sub.status).dot"
                      class="h-1.5 w-1.5 rounded-full"
                    />
                    {{ sub.status.charAt(0).toUpperCase() + sub.status.slice(1).replace('_', ' ') }}
                  </span>

                  <!-- Trial end date -->
                  <span v-if="sub.status === 'trialing' && sub.trial_end" class="flex items-center gap-1 text-blue-600 dark:text-blue-400">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Trial ends {{ formatDate(sub.trial_end) }}
                  </span>

                  <!-- Renewal date (non-trial active) -->
                  <span v-if="sub.current_period_end && sub.status !== 'trialing'" class="flex items-center gap-1">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    Renews {{ formatDate(sub.current_period_end) }}
                  </span>

                  <!-- First billing after trial -->
                  <span v-if="sub.status === 'trialing' && sub.current_period_end" class="text-[var(--color-muted-foreground)]">
                    First bill {{ formatDate(sub.current_period_end) }}
                  </span>

                  <span v-if="sub.canceled_at" class="text-orange-600 dark:text-orange-400">
                    Canceled {{ formatDate(sub.canceled_at) }}
                  </span>
                </div>
              </div>

              <!-- Right: Actions -->
              <div class="flex items-center gap-2 shrink-0">
                <a
                  :href="`/dashboard/billing/plans/${sub.product_slug}`"
                  class="btn-secondary text-xs"
                >
                  View Plans
                </a>

                <!-- Manage Billing (Stripe Portal) -->
                <button
                  v-if="sub.plan_slug !== 'free' && ['active', 'trialing'].includes(sub.status)"
                  :disabled="actionLoading === `portal-${sub.product_slug}`"
                  class="btn-ghost text-xs text-brand-600 dark:text-brand-400 hover:text-brand-700"
                  @click="handleManageBilling"
                >
                  <svg class="h-3.5 w-3.5 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {{ actionLoading === 'portal' ? 'Opening...' : 'Manage' }}
                </button>

                <button
                  v-if="sub.plan_slug !== 'free' && ['active', 'trialing'].includes(sub.status)"
                  :disabled="actionLoading === `cancel-${sub.product_slug}`"
                  class="btn-ghost text-xs text-destructive hover:text-destructive"
                  @click="handleCancel(sub.product_slug)"
                >
                  Cancel
                </button>

                <button
                  v-if="sub.status === 'canceled'"
                  :disabled="actionLoading === `reactivate-${sub.product_slug}`"
                  class="btn-ghost text-xs text-brand-600 dark:text-brand-400 hover:text-brand-700"
                  @click="handleReactivate(sub.product_slug)"
                >
                  {{ actionLoading === `reactivate-${sub.product_slug}` ? 'Reactivating...' : 'Reactivate' }}
                </button>

                <button
                  v-if="sub.status === 'past_due'"
                  disabled
                  class="btn-ghost text-xs cursor-not-allowed opacity-60"
                >
                  Payment Due
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Products Catalog -->
      <div>
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold">Available Products</h2>
          <span class="text-sm text-[var(--color-muted-foreground)]">
            {{ products.length }} product{{ products.length !== 1 ? 's' : '' }}
          </span>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <a
            v-for="product in products"
            :key="product.id"
            :href="`/dashboard/billing/plans/${product.slug}`"
            class="card group p-6 transition-all duration-200 hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700"
          >
            <div class="flex items-start gap-4">
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl gradient-brand text-white text-lg font-bold shadow-md shadow-brand-600/20 transition-transform duration-150 group-hover:scale-110">
                {{ product.name.split(' ').map(w => w[0]).join('').slice(0, 2) }}
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-semibold group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                  {{ product.name }}
                </h3>
                <p class="mt-1 text-sm text-[var(--color-muted-foreground)] line-clamp-2">
                  {{ product.description || 'No description available.' }}
                </p>
                <div class="mt-3 flex items-center gap-2 text-xs text-brand-600 dark:text-brand-400 font-medium">
                  <span>View plans</span>
                  <svg class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </div>
            </div>
          </a>
        </div>
      </div>
    </template>
  </div>
</template>
