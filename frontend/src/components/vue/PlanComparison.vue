<script setup lang="ts">
/**
 * PlanComparison — Plan cards side-by-side with feature comparison.
 *
 * Props:
 *   slug: Product slug (from URL param)
 *
 * Features:
 *   - Product header with description and service domains
 *   - Side-by-side plan cards (Free, Standard, Pro, etc.)
 *   - Featured plan highlight with gradient border
 *   - Feature matrix with check/cross indicators
 *   - Change plan action (requires backend integration)
 */

import { ref, computed, onMounted } from "vue";
import { requireAuth, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import {
  billingApi,
  formatPrice,
  formatCycle,
  formatDate,
} from "@/lib/billing";
import type {
  ProductDetailSchema,
  PlanSchema,
  SubscriptionOutputSchema,
} from "@/lib/billing";

const props = defineProps<{ slug: string }>();

const loading = ref(true);
const product = ref<ProductDetailSchema | null>(null);
const subscriptions = ref<SubscriptionOutputSchema[]>([]);
const actionLoading = ref<string | null>(null);

const currentPlanSlug = computed(() => {
  const sub = subscriptions.value.find((s) => s.product_slug === props.slug);
  return sub?.plan_slug || null;
});

const status = computed(() => {
  const sub = subscriptions.value.find((s) => s.product_slug === props.slug);
  return sub?.status || null;
});

const trialEnd = computed(() => {
  const sub = subscriptions.value.find((s) => s.product_slug === props.slug);
  return sub?.trial_end || null;
});

const periodEnd = computed(() => {
  const sub = subscriptions.value.find((s) => s.product_slug === props.slug);
  return sub?.current_period_end || null;
});

// Collect all unique feature keys across all plans
const featureKeys = computed(() => {
  if (!product.value) return [];
  const keys = new Set<string>();
  for (const plan of product.value.plans) {
    for (const key of Object.keys(plan.features)) {
      keys.add(key);
    }
  }
  return Array.from(keys);
});

onMounted(async () => {
  if (!requireAuth()) return;
  try {
    const [productData, subsData] = await Promise.all([
      billingApi.getProductBySlug(props.slug),
      billingApi.getSubscriptions(),
    ]);
    product.value = productData;
    subscriptions.value = subsData;
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    loading.value = false;
  }
});

function handleChangePlan(planSlug: string) {
  if (planSlug === currentPlanSlug.value) return;

  const targetPlan = product.value?.plans.find((p) => p.slug === planSlug);
  const isTargetPaid = targetPlan && !targetPlan.is_free;
  const currentPlan = product.value?.plans.find(
    (p) => p.slug === currentPlanSlug.value,
  );
  const isCurrentlyFree = !currentPlan || currentPlan.is_free;

  // Free → Paid: Stripe Checkout (redirect to Stripe's hosted payment page)
  // Paid → Paid or Paid → Free: local plan switch via API
  const actionLabel = isTargetPaid && isCurrentlyFree ? "Proceed to Checkout" : "Switch";
  const message =
    isTargetPaid && isCurrentlyFree
      ? `Upgrade to the ${planSlug} plan? You'll be redirected to complete payment.`
      : `Switch to the ${planSlug} plan?`;

  showToast(message, "warning", {
    duration: 0,
    action: {
      label: actionLabel,
      onClick: () => executeChangePlan(planSlug),
    },
  });
}

async function executeChangePlan(planSlug: string) {
  actionLoading.value = `change-${planSlug}`;
  try {
    const targetPlan = product.value?.plans.find((p) => p.slug === planSlug);
    const currentPlan = product.value?.plans.find(
      (p) => p.slug === currentPlanSlug.value,
    );
    const isTargetPaid = targetPlan && !targetPlan.is_free;
    const isCurrentlyFree = !currentPlan || currentPlan.is_free;

    // Free → Paid: create Stripe checkout session and redirect
    if (isTargetPaid && isCurrentlyFree) {
      showToast("Redirecting to checkout...", "info", { duration: 3000 });
      const result = await billingApi.createCheckout(
        props.slug,
        planSlug,
      );
      window.location.href = result.checkout_url;
      return; // Don't clear loading — user is leaving the page
    }

    // Paid → Paid or Paid → Free: local plan switch
    await billingApi.changePlan(props.slug, planSlug);
    showToast("Plan changed successfully.", "success");
    subscriptions.value = await billingApi.getSubscriptions();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}
</script>

<template>
  <div>
    <!-- Back Link -->
    <a
      href="/dashboard/billing"
      class="mb-6 inline-flex items-center gap-1.5 text-sm text-[var(--color-muted-foreground)] hover:text-foreground transition-colors"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
      </svg>
      Back to Billing
    </a>

    <!-- Loading Skeleton -->
    <template v-if="loading">
      <div class="animate-pulse mb-6">
        <div class="h-8 w-48 rounded bg-[var(--color-muted)] mb-2" />
        <div class="h-4 w-96 rounded bg-[var(--color-muted)]" />
      </div>
      <div class="grid gap-6 md:grid-cols-3">
        <div v-for="i in 3" :key="i" class="card p-6 animate-pulse">
          <div class="h-5 w-24 rounded bg-[var(--color-muted)] mb-4" />
          <div class="h-8 w-20 rounded bg-[var(--color-muted)] mb-1" />
          <div class="h-4 w-16 rounded bg-[var(--color-muted)] mb-6" />
          <div class="space-y-2">
            <div v-for="j in 6" :key="j" class="h-4 rounded bg-[var(--color-muted)]" />
          </div>
          <div class="h-10 w-full rounded-lg bg-[var(--color-muted)] mt-6" />
        </div>
      </div>
    </template>

    <!-- Not Found -->
    <div v-else-if="!product" class="card flex flex-col items-center justify-center py-20 text-center px-6">
      <div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-muted)]">
        <svg class="h-8 w-8 text-[var(--color-muted-foreground)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <p class="text-sm font-medium text-[var(--color-muted-foreground)]">Product not found</p>
      <a href="/dashboard/billing" class="mt-3 text-sm text-brand-600 dark:text-brand-400 hover:underline">
        Return to billing overview
      </a>
    </div>

    <template v-else>
      <!-- Product Header -->
      <div class="mb-8">
        <h1 class="text-2xl font-bold tracking-tight md:text-3xl">{{ product.name }}</h1>
        <p class="mt-1 text-[var(--color-muted-foreground)] max-w-2xl">
          {{ product.description || 'Choose the plan that fits your needs.' }}
        </p>
        <!-- Service Domains -->
        <div v-if="product.service_domains.length > 0" class="flex flex-wrap gap-2 mt-3">
          <span
            v-for="domain in product.service_domains"
            :key="domain.id"
            class="inline-flex items-center gap-1.5 rounded-md bg-[var(--color-muted)] px-2.5 py-1 text-xs font-medium text-[var(--color-muted-foreground)]"
          >
            <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
            </svg>
            {{ domain.domain }}
            <span v-if="domain.is_primary" class="text-brand-600 dark:text-brand-400 font-semibold">primary</span>
          </span>
        </div>
        <!-- Current plan indicator -->
        <div v-if="currentPlanSlug" class="mt-3 text-sm">
          <span class="text-[var(--color-muted-foreground)]">Current plan:</span>
          <span class="ml-1 font-semibold text-foreground capitalize">{{ currentPlanSlug }}</span>
          <span v-if="status" class="ml-2 rounded-full px-2 py-0.5 text-xs font-medium" :class="{
            'bg-blue-50 text-blue-700 dark:bg-blue-950/50 dark:text-blue-300': status === 'trialing',
            'bg-brand-50 text-brand-700 dark:bg-brand-950/50 dark:text-brand-300': status === 'active',
            'bg-orange-50 text-orange-700 dark:bg-orange-950/50 dark:text-orange-300': status === 'canceled',
          }">{{ status }}</span>
          <span v-if="status === 'trialing' && trialEnd" class="ml-2 text-xs text-blue-600 dark:text-blue-400">
            — trial ends {{ formatDate(trialEnd) }}
          </span>
          <span v-if="status === 'active' && periodEnd" class="ml-2 text-xs text-[var(--color-muted-foreground)]">
            — renews {{ formatDate(periodEnd) }}
          </span>
        </div>
      </div>

      <!-- Plans Grid -->
      <div
        class="grid gap-6"
        :class="{
          'md:grid-cols-2': product.plans.length === 2,
          'lg:grid-cols-3': product.plans.length >= 3,
        }"
      >
        <div
          v-for="plan in product.plans"
          :key="plan.id"
          class="card relative flex flex-col p-6 transition-all duration-200"
          :class="{
            'ring-2 ring-brand-500 dark:ring-brand-400 shadow-lg shadow-brand-500/10': plan.is_featured,
            'hover:shadow-md': !plan.is_featured,
            'opacity-75': currentPlanSlug === plan.slug,
          }"
        >
          <!-- Featured badge -->
          <div v-if="plan.is_featured" class="absolute -top-3 left-1/2 -translate-x-1/2">
            <span class="inline-flex items-center rounded-full gradient-brand px-3 py-1 text-xs font-semibold text-white shadow-sm">
              Most Popular
            </span>
          </div>

          <!-- Current plan badge -->
          <div v-if="currentPlanSlug === plan.slug" class="absolute -top-3 right-4">
            <span class="inline-flex items-center rounded-full bg-brand-100 dark:bg-brand-950 px-3 py-1 text-xs font-semibold text-brand-700 dark:text-brand-300">
              Current
            </span>
          </div>

          <!-- Plan Name -->
          <h3 class="text-lg font-semibold">{{ plan.name }}</h3>

          <!-- Description -->
          <p v-if="plan.description" class="mt-1 text-sm text-[var(--color-muted-foreground)]">
            {{ plan.description }}
          </p>

          <!-- Price -->
          <div class="mt-4 mb-6">
            <span class="text-3xl font-bold">
              {{ plan.is_free ? 'Free' : formatPrice(plan.price_cents, plan.currency) }}
            </span>
            <span v-if="!plan.is_free" class="text-sm text-[var(--color-muted-foreground)]">
              /{{ formatCycle(plan.billing_cycle).replace('/', '') }}
            </span>
            <p v-if="plan.trial_days > 0" class="mt-1 text-xs text-brand-600 dark:text-brand-400">
              {{ plan.trial_days }}-day free trial
            </p>
          </div>

          <!-- Features list -->
          <ul class="flex-1 space-y-3 mb-6" role="list">
            <li
              v-for="(value, key) in plan.features"
              :key="key"
              class="flex items-start gap-2.5 text-sm"
            >
              <!-- Check icon -->
              <svg class="mt-0.5 h-4 w-4 shrink-0 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <span class="font-medium capitalize">{{ String(key).replace(/_/g, ' ') }}</span>
                <span class="text-[var(--color-muted-foreground)]"> — {{ value }}</span>
              </div>
            </li>
          </ul>

          <!-- CTA Button -->
          <button
            v-if="currentPlanSlug === plan.slug"
            disabled
            class="btn-secondary w-full justify-center opacity-60 cursor-not-allowed"
          >
            Current Plan
          </button>
          <button
            v-else-if="plan.is_free"
            :disabled="actionLoading === `change-${plan.slug}`"
            class="btn-secondary w-full justify-center"
            @click="handleChangePlan(plan.slug)"
          >
            {{ actionLoading === `change-${plan.slug}` ? 'Switching...' : 'Downgrade to Free' }}
          </button>
          <button
            v-else
            :disabled="actionLoading === `change-${plan.slug}`"
            class="btn-primary w-full justify-center"
            @click="handleChangePlan(plan.slug)"
          >
            {{ actionLoading === `change-${plan.slug}` ? 'Switching...' : 'Upgrade Now' }}
          </button>
        </div>
      </div>
    </template>
  </div>
</template>
