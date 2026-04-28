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
import { getCurrentUser } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import {
  billingApi,
  formatPrice,
  formatCycle,
  formatDate,
  getUserCurrency,
  setUserCurrency,
} from "@/lib/billing";
import type {
  ProductDetailSchema,
  PlanSchema,
  SubscriptionOutputSchema,
} from "@/lib/billing";

const props = defineProps<{ slug: string }>();
const emit = defineEmits<{ (e: "plan-changed"): void }>();

const loading = ref(true);
const product = ref<ProductDetailSchema | null>(null);
const subscriptions = ref<SubscriptionOutputSchema[]>([]);
const actionLoading = ref<string | null>(null);
const tosAccepted = ref(false);
const prorationBehavior = ref<"create_prorations" | "none">("create_prorations");
const showProrationModal = ref(false);
const prorationPreview = ref<{
  subtotal: number;
  tax: number;
  total: number;
  next_billing: number;
  currency: string;
} | null>(null);
const prorationLoading = ref(false);

const currentSubscription = computed(() => {
  return subscriptions.value.find((s) => s.product_slug === props.slug) || null;
});

const currentPlanSlug = computed(() => {
  return currentSubscription.value?.plan_slug || null;
});

const status = computed(() => {
  return currentSubscription.value?.status || null;
});

const isSubscriptionCanceled = computed(() => {
  return status.value === 'canceled';
});

const trialEnd = computed(() => {
  const sub = subscriptions.value.find((s) => s.product_slug === props.slug);
  return sub?.trial_end || null;
});

const periodEnd = computed(() => {
  return currentSubscription.value?.current_period_end || null;
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
    // Fetch user's preferred currency directly from /users/me to avoid
    // race condition with Navbar's async populateUserInfo(). Also update
    // the global _userCurrency so other components benefit.
    let userCurrency = getUserCurrency(); // default from Navbar (may be "USD")
    try {
      const user = await getCurrentUser();
      if (user?.currency) {
        userCurrency = user.currency;
        setUserCurrency(user.currency);
      }
    } catch {
      // Non-critical — fall back to global default
    }

    const [productData, subsData] = await Promise.all([
      billingApi.getProductBySlug(props.slug, userCurrency),
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
  // Allow clicking current plan only when subscription is canceled (reactivation)
  if (planSlug === currentPlanSlug.value && !isSubscriptionCanceled.value) return;

  const targetPlan = product.value?.plans.find((p) => p.slug === planSlug);
  const isTargetPaid = targetPlan && !targetPlan.is_free;
  const currentPlan = product.value?.plans.find(
    (p) => p.slug === currentPlanSlug.value,
  );
  const isCurrentlyFree = !currentPlan || currentPlan.is_free;
  const isCurrentlyPaid = currentPlan && !currentPlan.is_free;

  // Canceled subscription: any paid plan action goes through checkout
  // (backend reactivates the existing Stripe subscription)
  if (isSubscriptionCanceled.value && isTargetPaid) {
    if (!tosAccepted.value) {
      showToast("Please accept the Terms of Service first.", "warning");
      return;
    }
    const isSamePlan = planSlug === currentPlanSlug.value;
    const message = isSamePlan
      ? `Reactivate your ${currentPlan?.name || planSlug} plan?`
      : `Switch to the ${planSlug} plan?`;
    showToast(message, "warning", {
      duration: 0,
      action: {
        label: isSamePlan ? "Reactivate" : "Proceed to Checkout",
        onClick: () => executeChangePlan(planSlug),
      },
    });
    return;
  }

  // Free → Paid: Stripe Checkout (redirect to Stripe's hosted payment page)
  if (isTargetPaid && isCurrentlyFree) {
    if (!tosAccepted.value) {
      showToast("Please accept the Terms of Service first.", "warning");
      return;
    }
    const message = `Upgrade to the ${planSlug} plan? You'll be redirected to complete payment.`;
    showToast(message, "warning", {
      duration: 0,
      action: {
        label: "Proceed to Checkout",
        onClick: () => executeChangePlan(planSlug),
      },
    });
    return;
  }

  // Paid → Paid: Show proration preview first
  if (isTargetPaid && isCurrentlyPaid && currentPlanSlug.value) {
    showProrationPreviewAndConfirm(planSlug);
    return;
  }

  // Paid → Free: direct downgrade
  const actionLabel = "Downgrade";
  const message = `Switch to the ${planSlug} plan?`;
  showToast(message, "warning", {
    duration: 0,
    action: {
      label: actionLabel,
      onClick: () => executeChangePlan(planSlug),
    },
  });
}

async function showProrationPreviewAndConfirm(planSlug: string) {
  prorationLoading.value = true;
  try {
    const preview = await billingApi.previewPlanChange(
      props.slug,
      planSlug,
      prorationBehavior.value,
    );
    prorationPreview.value = preview;
    showProrationModal.value = true;
  } catch (err) {
    // If preview fails (e.g., no Stripe sub), fall back to direct confirmation
    showToast(getErrorMessage(err), "error");
    const message = `Switch to the ${planSlug} plan?`;
    showToast(message, "warning", {
      duration: 0,
      action: {
        label: "Switch",
        onClick: () => executeChangePlan(planSlug),
      },
    });
  } finally {
    prorationLoading.value = false;
  }
}

function confirmProrationChange() {
  if (!prorationPreview.value) return;
  const targetPlan = product.value?.plans.find(
    (p) => p.slug !== currentPlanSlug.value && !p.is_free,
  );
  if (targetPlan) {
    showProrationModal.value = false;
    executeChangePlan(targetPlan.slug);
  }
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

    // Canceled → Paid (reactivate same plan or switch to different paid plan):
    // Goes through checkout which auto-detects and reuses existing Stripe sub.
    // Free → Paid (new checkout): also goes through checkout.
    if (isTargetPaid && (isCurrentlyFree || isSubscriptionCanceled.value)) {
      showToast("Redirecting to checkout...", "info", { duration: 3000 });
      const result = await billingApi.createCheckout(
        props.slug,
        planSlug,
        undefined,
        true, // tos_accepted
      );

      // If the backend reactivated an existing cancelled subscription,
      // there's no checkout URL — just reload the plan data.
      if (result.reactivated || !result.checkout_url) {
        showToast("Subscription reactivated successfully.", "success");
        emit("plan-changed");
        subscriptions.value = await billingApi.getSubscriptions();
        return;
      }

      window.location.href = result.checkout_url;
      return;
    }

    // Paid → Paid or Paid → Free: local plan switch with proration behavior
    await billingApi.changePlan(props.slug, planSlug, prorationBehavior.value);
    const behaviorLabel = prorationBehavior.value === "none" ? " at next billing cycle" : " with proration";
    showToast(`Plan changed successfully${behaviorLabel}.`, "success");
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
          <span v-if="isSubscriptionCanceled && periodEnd" class="ml-2 text-xs text-orange-600 dark:text-orange-400">
            — access until {{ formatDate(periodEnd) }}
          </span>
        </div>
      </div>

      <!-- ToS & Proration Options -->
      <div v-if="!loading && product" class="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-muted)]/30 p-4">
        <!-- Terms of Service Checkbox (M1) -->
        <label class="flex items-start gap-2.5 cursor-pointer select-none">
          <input
            v-model="tosAccepted"
            type="checkbox"
            class="mt-0.5 h-4 w-4 rounded border-[var(--color-border)] text-brand-600 focus:ring-brand-500"
          />
          <span class="text-sm text-[var(--color-muted-foreground)]">
            I agree to the
            <a href="/terms-of-service" target="_blank" class="text-brand-600 dark:text-brand-400 hover:underline font-medium">Terms of Service</a>
          </span>
        </label>

        <!-- Proration Behavior Toggle (M5) -->
        <div v-if="currentPlanSlug" class="flex items-center gap-3 text-sm">
          <span class="text-[var(--color-muted-foreground)]">Plan change:</span>
          <button
            :class="prorationBehavior === 'create_prorations' ? 'btn-primary text-xs !py-1 !px-3' : 'btn-ghost text-xs !py-1 !px-3'"
            @click="prorationBehavior = 'create_prorations'"
          >
            Apply Now
          </button>
          <button
            :class="prorationBehavior === 'none' ? 'btn-primary text-xs !py-1 !px-3' : 'btn-ghost text-xs !py-1 !px-3'"
            @click="prorationBehavior = 'none'"
          >
            Next Billing
          </button>
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
            'opacity-75': currentPlanSlug === plan.slug && !isSubscriptionCanceled,
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
              {{ plan.is_free ? 'Free' : formatPrice(plan.converted_price_cents ?? plan.price_cents, plan.user_currency ?? plan.currency) }}
            </span>
            <span v-if="!plan.is_free" class="text-sm text-[var(--color-muted-foreground)]">
              /{{ formatCycle(plan.billing_cycle).replace('/', '') }}
            </span>
            <!-- Show base price when converted price differs -->
            <p v-if="!plan.is_free && plan.converted_price_cents != null && plan.user_currency && plan.user_currency !== plan.currency" class="mt-1 text-xs text-[var(--color-muted-foreground)]">
              {{ formatPrice(plan.price_cents, plan.currency) }}
            </p>
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
          <!-- CANCELED current plan: show Reactivate -->
          <button
            v-if="currentPlanSlug === plan.slug && isSubscriptionCanceled"
            :disabled="actionLoading === `change-${plan.slug}`"
            class="btn-primary w-full justify-center"
            @click="handleChangePlan(plan.slug)"
          >
            {{ actionLoading === `change-${plan.slug}` ? 'Reactivating...' : 'Reactivate Plan' }}
          </button>
          <!-- Active/trialing current plan: disabled -->
          <button
            v-else-if="currentPlanSlug === plan.slug"
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
            {{ actionLoading === `change-${plan.slug}` ? 'Switching...' : (isSubscriptionCanceled ? 'Subscribe' : 'Upgrade Now') }}
          </button>
        </div>
      </div>
    </template>

    <!-- Proration Preview Modal (M3) -->
    <Teleport to="body">
      <div
        v-if="showProrationModal && prorationPreview"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="showProrationModal = false"
      >
        <div class="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 shadow-2xl p-6">
          <h3 class="text-lg font-semibold mb-1">Plan Change Summary</h3>
          <p class="text-sm text-[var(--color-muted-foreground)] mb-4">Review the cost adjustment for your plan change.</p>

          <div class="space-y-3 mb-6">
            <div class="flex items-center justify-between text-sm">
              <span class="text-[var(--color-muted-foreground)]">Prorated credit/charge</span>
              <span class="font-medium" :class="prorationPreview.total < 0 ? 'text-green-600 dark:text-green-400' : 'text-foreground'">
                {{ prorationPreview.total < 0 ? '-' : '' }}{{ formatPrice(Math.abs(prorationPreview.total * 100), prorationPreview.currency) }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-[var(--color-muted-foreground)]">Tax</span>
              <span class="font-medium">{{ formatPrice(prorationPreview.tax * 100, prorationPreview.currency) }}</span>
            </div>
            <hr class="border-[var(--color-border)]" />
            <div class="flex items-center justify-between text-sm">
              <span class="text-[var(--color-muted-foreground)]">Next billing amount</span>
              <span class="font-semibold">{{ formatPrice(prorationPreview.next_billing * 100, prorationPreview.currency) }}</span>
            </div>
          </div>

          <div v-if="prorationBehavior === 'none'" class="mb-4 rounded-md bg-blue-50 dark:bg-blue-950/30 p-3 text-sm text-blue-700 dark:text-blue-300">
            Change will take effect at your next billing cycle.
          </div>

          <div class="flex items-center gap-2">
            <button
              class="btn-secondary flex-1"
              @click="showProrationModal = false"
            >
              Cancel
            </button>
            <button
              class="btn-primary flex-1"
              @click="confirmProrationChange()"
            >
              Confirm Change
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
