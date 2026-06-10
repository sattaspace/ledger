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

import { ref, computed, onMounted, onUnmounted, watch, nextTick } from "vue";
import { requireAuthAsync, getErrorMessage } from "@/lib/auth";
import { useAuth } from "@/composables";
import { useSubscription } from "@/composables";
import { showToast } from "@/lib/toast";
import {
  billingApi,
  formatPrice,
  formatCycle,
  formatDate,
  getUserCurrency,
  setUserCurrency,
  getFeatureValueType,
  formatFeatureValue,
  formatMatrixValue,
  getMatrixCellType,
} from "@/lib/billing";
import type {
  ProductDetailSchema,
  PlanSchema,
  SubscriptionOutputSchema,
  AccessMatrixSchema,
} from "@/lib/billing";

const props = defineProps<{ slug: string }>();
const emit = defineEmits<{ (e: "plan-changed"): void }>();

const loading = ref(true);
const product = ref<ProductDetailSchema | null>(null);
const { subscriptions, refetchSubscriptions } = useSubscription();
// API-2 FIX: Use useAuth() shared state instead of separate getCurrentUser() call.
// Previously this called getCurrentUser() which hit /users/me separately, wasting
// 1 API call per plan page. Now we reuse the user data from useAuth().
const { user: authUser, initAuth } = useAuth();
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
  preview_token: string | null;
  change_type: 'upgrade' | 'downgrade' | 'lateral';
  is_upgrade: boolean;
} | null>(null);
const prorationLoading = ref(false);
const isRedirecting = ref(false);
const accessMatrix = ref<AccessMatrixSchema | null>(null);

// Per-plan feature lists built from the access matrix (dynamic data from API).
// When available, these replace the static plan.features in plan cards.
const planMatrixFeatures = computed(() => {
  if (!accessMatrix.value || accessMatrix.value.rows.length === 0) return null;
  const result: Record<
    string,
    Array<{
      key: string;
      description: string | null;
      value: string | null;
      value_type: "boolean" | "integer" | "string";
    }>
  > = {};
  for (const plan of accessMatrix.value.plans) {
    result[plan.slug] = accessMatrix.value.rows
      .filter(
        (row) =>
          row.values[plan.slug] !== undefined &&
          row.values[plan.slug] !== null,
      )
      .map((row) => ({
        key: row.key,
        description: row.description,
        value: row.values[plan.slug],
        value_type: row.value_type,
      }));
  }
  return result;
});

// 6.5: Return URL for sister-domain billing redirect
const returnUrl = ref<string | null>(null);

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

// UX-10: Calculate annual savings when both monthly and yearly plans exist
const annualSavings = computed(() => {
  if (!product.value) return {} as Record<string, number>;
  const savings: Record<string, number> = {};
  for (const plan of product.value.plans) {
    if (plan.billing_cycle === 'yearly') {
      const monthlyPlan = product.value.plans.find(
        (p) => p.name === plan.name && p.billing_cycle === 'monthly',
      );
      if (monthlyPlan) {
        const monthlyTotal = monthlyPlan.price_cents * 12;
        const yearlyTotal = plan.price_cents;
        const pct = Math.round((1 - yearlyTotal / monthlyTotal) * 100);
        if (pct > 0) {
          savings[plan.name] = pct;
        }
      }
    }
  }
  return savings;
});

onMounted(async () => {
  // AUTH-13 FIX: Use requireAuthAsync() to wait for token init before checking
  if (!(await requireAuthAsync())) return;

  // 6.5: Capture return_url from query param or sessionStorage
  const params = new URLSearchParams(window.location.search);
  const incomingReturnUrl = params.get("return_url");
  if (incomingReturnUrl) {
    returnUrl.value = incomingReturnUrl;
    sessionStorage.setItem("billing_return_url", incomingReturnUrl);
  } else {
    returnUrl.value = sessionStorage.getItem("billing_return_url");
  }

  try {
    // API-2 FIX: Use useAuth().user for currency instead of separate getCurrentUser() call.
    // The authUser data is already fetched by initAuth/SessionGuard, so we just read
    // the cached value. If not yet loaded, initAuth() will fetch it (deduplicated).
    await initAuth();
    let userCurrency = getUserCurrency(); // default from Navbar (may be "USD")
    if (authUser.value?.currency) {
      userCurrency = authUser.value.currency;
      setUserCurrency(authUser.value.currency);
    }

    const [productData, , matrixData] = await Promise.all([
      billingApi.getProductBySlug(props.slug, userCurrency),
      refetchSubscriptions(),
      billingApi.getProductAccessMatrix(props.slug).catch(() => null),
    ]);
    product.value = productData;
    accessMatrix.value = matrixData;
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    loading.value = false;
  }
});

async function handleChangePlan(planSlug: string) {
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

  // UX-07 Fix: Paid → Free downgrade now uses a confirmation dialog pattern
  // (matching the modal UX used in BillingOverview's cancel flow) instead
  // of a toast with action button. This provides a more deliberate
  // confirmation experience for irreversible plan changes.
  const message = `Switch to the free ${planSlug} plan? Your paid plan features will be removed at the end of this billing period.`;
  if (window.confirm(message)) {
    await executeChangePlan(planSlug);
  }
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

async function confirmProrationChange() {
  if (!prorationPreview.value || !prorationPreview.value.preview_token) return;
  const targetPlan = product.value?.plans.find(
    (p) => p.slug !== currentPlanSlug.value && !p.is_free,
  );
  if (!targetPlan) return;

  actionLoading.value = `change-${targetPlan.slug}`;
  try {
    const result = await billingApi.confirmPlanChange(
      props.slug,
      targetPlan.slug,
      prorationPreview.value.preview_token,
    );
    closeProrationModal();

    if (result.effective_when === 'immediately') {
      showToast(`Upgraded to ${result.plan_name}. Amount charged: ${formatPrice(result.amount_charged * 100, result.currency)}.`, 'success');
    } else {
      showToast(`Plan change to ${result.plan_name} will take effect at your next billing cycle.`, 'success');
    }
    emit('plan-changed');
    await refetchSubscriptions();
  } catch (err) {
    showToast(getErrorMessage(err), 'error');
  } finally {
    actionLoading.value = null;
  }
}

// A11Y-01: Proration modal refs and accessibility handlers
const prorationModalRef = ref<HTMLElement | null>(null);
const prorationCancelBtn = ref<HTMLElement | null>(null);
const previouslyFocusedProration = ref<HTMLElement | null>(null);

function closeProrationModal() {
  showProrationModal.value = false;
  previouslyFocusedProration.value?.focus();
}

function handleProrationEscape(e: KeyboardEvent) {
  if (e.key === "Escape" && showProrationModal.value) {
    closeProrationModal();
  }
}

function trapProrationFocus(e: KeyboardEvent) {
  if (!showProrationModal.value || !prorationModalRef.value) return;
  const modal = prorationModalRef.value;
  const focusable = modal.querySelectorAll<HTMLElement>(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.key === "Tab") {
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
}

watch(showProrationModal, async (isOpen) => {
  if (isOpen) {
    previouslyFocusedProration.value = document.activeElement as HTMLElement;
    document.addEventListener("keydown", handleProrationEscape);
    document.addEventListener("keydown", trapProrationFocus);
    await nextTick();
    // Auto-focus the cancel button for accessibility
    prorationCancelBtn.value?.focus();
  } else {
    document.removeEventListener("keydown", handleProrationEscape);
    document.removeEventListener("keydown", trapProrationFocus);
  }
});

onUnmounted(() => {
  document.removeEventListener("keydown", handleProrationEscape);
  document.removeEventListener("keydown", trapProrationFocus);
});

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
        returnUrl.value || undefined, // 6.5: pass return_url for sister-domain redirect
      );

      // If the backend reactivated an existing cancelled subscription,
      // there's no checkout URL — just reload the plan data.
      if (result.reactivated || !result.checkout_url) {
        showToast("Subscription reactivated successfully.", "success");
        emit("plan-changed");
        await refetchSubscriptions();
        return;
      }

      isRedirecting.value = true;
      window.location.href = result.checkout_url;
      return;
    }

    // Paid → Paid or Paid → Free: local plan switch with proration behavior
    await billingApi.changePlan(props.slug, planSlug, prorationBehavior.value);
    const behaviorLabel = prorationBehavior.value === "none" ? " at next billing cycle" : " with proration";
    showToast(`Plan changed successfully${behaviorLabel}.`, "success");
    await refetchSubscriptions();
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
            <a href="/terms-of-service" target="_blank" rel="noopener noreferrer" class="text-brand-600 dark:text-brand-400 hover:underline font-medium">Terms of Service</a>
          </span>
        </label>

        <!-- Proration behavior is now automatic: upgrades charge immediately,
             downgrades apply at next billing cycle. No manual toggle needed. -->
      </div>

      <!-- Alternative payment: bank transfer credits -->
      <div v-if="!loading && product" class="mb-6 flex items-start gap-2.5 rounded-lg border border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-950/30 px-4 py-3">
        <svg class="h-5 w-5 shrink-0 text-blue-600 dark:text-blue-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <div class="text-sm">
          <p class="text-blue-800 dark:text-blue-300 font-medium">Can't pay with an international card?</p>
          <p class="text-blue-700 dark:text-blue-400 mt-0.5">
            You can also <a href="/dashboard/billing/credits/request" class="font-semibold underline underline-offset-2 hover:text-blue-900 dark:hover:text-blue-200">purchase credits via bank transfer</a> to activate this plan. No international payment method required.
          </p>
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
            <!-- FIN-05: Disclaimer for converted (non-base) currencies -->
            <p v-if="!plan.is_free && plan.user_currency && plan.user_currency !== plan.currency" class="mt-1 text-xs text-amber-600 dark:text-amber-400">
              Prices in {{ plan.user_currency.toUpperCase() }} are approximate. Final charge is in {{ plan.currency.toUpperCase() }}.
            </p>
            <p v-if="plan.trial_days > 0" class="mt-1 text-xs text-brand-600 dark:text-brand-400">
              {{ plan.trial_days }}-day free trial
            </p>
            <!-- UX-10: Annual savings badge -->
            <p
              v-if="annualSavings[plan.name]"
              class="mt-1 text-xs font-semibold text-green-600 dark:text-green-400"
            >
              Save {{ annualSavings[plan.name] }}% vs monthly
            </p>
          </div>

          <!-- Feature list — uses access matrix data when available, falls back to static plan.features -->
          <ul class="flex-1 space-y-3 mb-6" role="list">
            <!-- Dynamic features from Access Matrix (synchronized with admin) -->
            <template v-if="planMatrixFeatures && planMatrixFeatures[plan.slug]">
              <li
                v-for="feat in planMatrixFeatures[plan.slug]"
                :key="feat.key"
                class="flex items-start gap-2.5 text-sm"
              >
                <!-- Boolean true: green checkmark -->
                <svg
                  v-if="getMatrixCellType(feat.value, feat.value_type) === 'boolean-true'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-brand-500"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <!-- Boolean false: red cross -->
                <svg
                  v-else-if="getMatrixCellType(feat.value, feat.value_type) === 'boolean-false'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-red-400"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
                <!-- Unlimited (integer 0): purple infinity -->
                <svg
                  v-else-if="getMatrixCellType(feat.value, feat.value_type) === 'unlimited'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-purple-500"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 0C9.5 2 7 4.5 7 7.5S9.5 13 12 13s5-2.5 5-5.5S14.5 2 12 2zm0 0c2.5 0 5 2.5 5 5.5S14.5 13 12 13" />
                </svg>
                <!-- Numeric limit (integer N>0): blue hash -->
                <svg
                  v-else-if="getMatrixCellType(feat.value, feat.value_type) === 'numeric'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-blue-500"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                </svg>
                <!-- String: green checkmark -->
                <svg
                  v-else
                  class="mt-0.5 h-4 w-4 shrink-0 text-brand-500"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <div>
                  <span class="font-medium capitalize" :class="{ 'text-brand-700 dark:text-brand-300': feat.key === 'all' }">
                    {{ feat.key === 'all' ? 'All Features' : feat.key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) }}
                  </span>
                  <span
                    class="text-[var(--color-muted-foreground)]"
                    :class="{
                      'text-brand-600 dark:text-brand-400 font-medium ml-1.5': getMatrixCellType(feat.value, feat.value_type) === 'boolean-true',
                      'text-red-500 dark:text-red-400 font-medium ml-1.5': getMatrixCellType(feat.value, feat.value_type) === 'boolean-false',
                      'text-purple-600 dark:text-purple-400 inline-flex items-center ml-1.5 rounded-full px-1.5 py-0.5 text-xs font-semibold bg-purple-50 dark:bg-purple-950/50': getMatrixCellType(feat.value, feat.value_type) === 'unlimited',
                      'text-blue-600 dark:text-blue-400 inline-flex items-center ml-1.5 rounded-full px-1.5 py-0.5 text-xs font-semibold bg-blue-50 dark:bg-blue-950/50': getMatrixCellType(feat.value, feat.value_type) === 'numeric',
                      'ml-1.5': getMatrixCellType(feat.value, feat.value_type) === 'string',
                    }"
                  >{{ formatMatrixValue(feat.value, feat.value_type) }}</span>
                </div>
              </li>
            </template>
            <!-- Fallback: static plan.features (legacy, used when access matrix has no data) -->
            <template v-else>
              <li
                v-for="(value, key) in plan.features"
                :key="key"
                class="flex items-start gap-2.5 text-sm"
              >
                <!-- Boolean true: green checkmark -->
                <svg
                  v-if="getFeatureValueType(value) === 'boolean-true'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-brand-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <!-- Boolean false: red cross -->
                <svg
                  v-else-if="getFeatureValueType(value) === 'boolean-false'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
                <!-- Unlimited (integer 0): purple infinity -->
                <svg
                  v-else-if="getFeatureValueType(value) === 'unlimited'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-purple-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 0C9.5 2 7 4.5 7 7.5S9.5 13 12 13s5-2.5 5-5.5S14.5 2 12 2zm0 0c2.5 0 5 2.5 5 5.5S14.5 13 12 13" />
                </svg>
                <!-- Numeric limit (integer N>0): blue hash -->
                <svg
                  v-else-if="getFeatureValueType(value) === 'numeric'"
                  class="mt-0.5 h-4 w-4 shrink-0 text-blue-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                </svg>
                <!-- String: green checkmark -->
                <svg
                  v-else
                  class="mt-0.5 h-4 w-4 shrink-0 text-brand-500"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <div>
                  <span class="font-medium capitalize">{{ String(key).replace(/_/g, ' ') }}</span>
                  <span
                    class="text-[var(--color-muted-foreground)]"
                    :class="{
                      'text-brand-600 dark:text-brand-400 font-medium ml-1.5': getFeatureValueType(value) === 'boolean-true',
                      'text-red-500 dark:text-red-400 font-medium ml-1.5': getFeatureValueType(value) === 'boolean-false',
                      'text-purple-600 dark:text-purple-400 inline-flex items-center ml-1.5 rounded-full px-1.5 py-0.5 text-xs font-semibold bg-purple-50 dark:bg-purple-950/50': getFeatureValueType(value) === 'unlimited',
                      'text-blue-600 dark:text-blue-400 inline-flex items-center ml-1.5 rounded-full px-1.5 py-0.5 text-xs font-semibold bg-blue-50 dark:bg-blue-950/50': getFeatureValueType(value) === 'numeric',
                      'ml-1.5': getFeatureValueType(value) === 'string',
                    }"
                  >{{ formatFeatureValue(value) }}</span>
                </div>
              </li>
            </template>
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

      <!-- Access Matrix Comparison Table -->
      <div v-if="accessMatrix && accessMatrix.rows.length > 0" class="mt-10">
        <h2 class="text-xl font-bold mb-1">Feature Comparison</h2>
        <p class="text-sm text-[var(--color-muted-foreground)] mb-4">
          Detailed access matrix across all plans. <span v-if="accessMatrix.rows.some(r => r.key === 'all')" class="text-brand-600 dark:text-brand-400">The "All Features" row grants access to every feature.</span>
        </p>
        <div class="card overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-[var(--color-border)] bg-[var(--color-muted)]/50">
                  <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-[var(--color-muted-foreground)]" scope="col">
                    Feature
                  </th>
                  <th
                    v-for="plan in accessMatrix.plans"
                    :key="plan.slug"
                    class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wide text-[var(--color-muted-foreground)]"
                    scope="col"
                  >
                    {{ plan.name }}
                  </th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--color-border)]">
                <tr
                  v-for="row in accessMatrix.rows"
                  :key="row.key"
                  class="hover:bg-[var(--color-muted)]/30 transition-colors"
                  :class="{ 'bg-brand-50/50 dark:bg-brand-950/20': row.key === 'all' }"
                >
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-2">
                      <span class="font-medium text-sm" :class="{ 'text-brand-700 dark:text-brand-300': row.key === 'all' }">
                        {{ row.key === 'all' ? 'All Features' : row.key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) }}
                      </span>
                      <span
                        v-if="row.key === 'all'"
                        class="inline-flex items-center rounded-full gradient-brand px-2 py-0.5 text-[10px] font-semibold text-white"
                      >
                        Wildcard
                      </span>
                    </div>
                    <p v-if="row.description && row.key !== 'all'" class="text-xs text-[var(--color-muted-foreground)] mt-0.5">
                      {{ row.description }}
                    </p>
                    <p v-else-if="row.key === 'all'" class="text-xs text-brand-600 dark:text-brand-400 mt-0.5">
                      Grants access to all features — overrides individual settings
                    </p>
                  </td>
                  <td
                    v-for="plan in accessMatrix.plans"
                    :key="plan.slug"
                    class="px-4 py-3 text-center"
                  >
                    <!-- Boolean true: green checkmark -->
                    <svg
                      v-if="getMatrixCellType(row.values[plan.slug], row.value_type) === 'boolean-true'"
                      class="mx-auto h-5 w-5 text-green-600 dark:text-green-400"
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <!-- Boolean false: red X -->
                    <svg
                      v-else-if="getMatrixCellType(row.values[plan.slug], row.value_type) === 'boolean-false'"
                      class="mx-auto h-5 w-5 text-red-400"
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    <!-- Unlimited (integer 0): purple badge -->
                    <span
                      v-else-if="getMatrixCellType(row.values[plan.slug], row.value_type) === 'unlimited'"
                      class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-purple-50 text-purple-600 dark:bg-purple-950/50 dark:text-purple-400"
                    >
                      Unlimited
                    </span>
                    <!-- Numeric: blue badge -->
                    <span
                      v-else-if="getMatrixCellType(row.values[plan.slug], row.value_type) === 'numeric'"
                      class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400"
                    >
                      {{ row.values[plan.slug] }}
                    </span>
                    <!-- String value -->
                    <span
                      v-else-if="getMatrixCellType(row.values[plan.slug], row.value_type) === 'string'"
                      class="text-sm font-medium text-foreground"
                    >
                      {{ row.values[plan.slug] }}
                    </span>
                    <!-- Not defined: dash -->
                    <span v-else class="text-[var(--color-muted-foreground)]/40">&mdash;</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- A11Y-01 Fix: Proration Preview Modal with full accessibility.
         Added role="dialog", aria-modal, aria-labelledby, focus trap,
         Escape key handler, and auto-focus on mount. Previously the modal
         had none of these, making it inaccessible to keyboard and
         screen reader users. -->
    <Teleport to="body">
      <div
        v-if="showProrationModal && prorationPreview"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
        @click.self="closeProrationModal"
        @keydown.escape="closeProrationModal"
      >
        <div
          ref="prorationModalRef"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="proration-modal-title"
          class="w-full max-w-md rounded-xl bg-white dark:bg-gray-900 shadow-2xl p-6"
        >
          <h3 id="proration-modal-title" class="text-lg font-semibold mb-1">
            {{ prorationPreview.is_upgrade ? 'Upgrade' : prorationPreview.change_type === 'downgrade' ? 'Downgrade' : 'Switch Plan' }}
          </h3>
          <p class="text-sm text-[var(--color-muted-foreground)] mb-4">
            {{ prorationPreview.is_upgrade ? 'You will be charged immediately for the remaining time in your billing cycle.' : 'Your new rate starts at the next billing cycle.' }}
          </p>

          <div class="space-y-3 mb-6">
            <!-- Upgrade: show charge amount -->
            <template v-if="prorationPreview.is_upgrade">
              <div class="flex items-center justify-between text-sm">
                <span class="text-[var(--color-muted-foreground)]">Amount due now</span>
                <span class="font-semibold text-foreground">
                  {{ formatPrice(prorationPreview.total * 100, prorationPreview.currency) }}
                </span>
              </div>
              <div v-if="prorationPreview.tax > 0" class="flex items-center justify-between text-sm">
                <span class="text-[var(--color-muted-foreground)]">Includes tax</span>
                <span class="font-medium">{{ formatPrice(prorationPreview.tax * 100, prorationPreview.currency) }}</span>
              </div>
            </template>
            <!-- Downgrade: show credit -->
            <template v-else>
              <div class="flex items-center justify-between text-sm">
                <span class="text-[var(--color-muted-foreground)]">Prorated credit</span>
                <span class="font-medium text-green-600 dark:text-green-400">
                  {{ formatPrice(Math.abs(prorationPreview.total * 100), prorationPreview.currency) }}
                </span>
              </div>
            </template>
            <hr class="border-[var(--color-border)]" />
            <div class="flex items-center justify-between text-sm">
              <span class="text-[var(--color-muted-foreground)]">Next billing amount</span>
              <span class="font-semibold">{{ formatPrice(prorationPreview.next_billing * 100, prorationPreview.currency) }}</span>
            </div>
          </div>

          <div v-if="!prorationPreview.is_upgrade" class="mb-4 rounded-md bg-blue-50 dark:bg-blue-950/30 p-3 text-sm text-blue-700 dark:text-blue-300">
            Change will take effect at your next billing cycle.
          </div>
          <div v-else class="mb-4 rounded-md bg-amber-50 dark:bg-amber-950/30 p-3 text-sm text-amber-700 dark:text-amber-300">
            Your card will be charged immediately for the prorated amount.
          </div>

          <div class="flex items-center gap-2">
            <button
              ref="prorationCancelBtn"
              class="btn-secondary flex-1"
              @click="closeProrationModal"
              :disabled="!!actionLoading"
            >
              Cancel
            </button>
            <button
              class="btn-primary flex-1"
              :disabled="!!actionLoading"
              @click="confirmProrationChange()"
            >
              {{ actionLoading ? 'Processing...' : (prorationPreview?.is_upgrade ? 'Pay & Upgrade' : 'Confirm Change') }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- UX-06: Full-page redirect overlay during Stripe checkout -->
    <Teleport to="body">
      <div
        v-if="isRedirecting"
        class="fixed inset-0 z-50 flex items-center justify-center bg-white/80 dark:bg-gray-900/80"
      >
        <div class="text-center">
          <div class="animate-spin h-8 w-8 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
          <p class="text-sm font-medium text-foreground">Redirecting to secure checkout...</p>
        </div>
      </div>
    </Teleport>
  </div>
</template>
