# Stripe Integration — Comprehensive Audit Report

**Project**: Sattabase / Satta Ledger  
**Repository**: `sattaspace/ledger` (development branch, commit `6df22a3`)  
**Audit Date**: 2026-04-28  
**Scope**: All Stripe integration code — backend (`billing/`), frontend (`frontend/`), Celery tasks, webhooks, error handling

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Audit Perspective 1 — User Experience Expert](#2-audit-perspective-1--user-experience-expert)
3. [Audit Perspective 2 — Finance & Accounting Expert](#3-audit-perspective-2--finance--accounting-expert)
4. [Audit Perspective 3 — Financial Compliance Expert](#4-audit-perspective-3--financial-compliance-expert)
5. [Cross-Cutting Findings](#5-cross-cutting-findings)
6. [Prioritized Implementation Roadmap](#6-prioritized-implementation-roadmap)

---

## 1. Executive Summary

This audit examines the entire Stripe billing integration across three expert perspectives: User Experience (UX), Finance & Accounting, and Financial Compliance. The codebase demonstrates a generally strong architecture — the "Stripe first, DB second" pattern is correctly implemented, the modular `billing/stripe/` package is well-structured, and centralized error handling is in place.

However, the audit identifies **27 findings** across severity levels:

| Severity | Count |
|----------|-------|
| 🔴 Critical | 4 |
| 🟠 High | 8 |
| 🟡 Medium | 10 |
| 🔵 Low | 5 |

The most urgent issues are: missing dunning email notifications, an insecure webhook timeout mechanism, no invoice itemization for customers, and the absence of payment retry automation.

---

## 2. Audit Perspective 1 — User Experience Expert

### UX-01 🔴 Critical — No Dunning Email Notifications

**File**: `backend/billing/tasks.py` (lines 118-147)  
**Problem**: The `dunning_retry` Celery task detects past-due subscriptions older than 7 days but only logs a warning. The comment on line 136 says `# Future: Send dunning email here` — this is never implemented. Users whose cards fail get **zero communication** from the system. They only discover the problem when they lose access.

**Impact**: Users lose service unexpectedly without warning. This is the number-one cause of involuntary churn in SaaS.

**Solution**:

```python
# backend/billing/tasks.py — dunning_retry()
# Add after line 136:
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

portal_link = f"{settings.STRIPE_APP_DOMAIN}/dashboard/billing"

send_mail(
    subject="Action Required: Update Your Payment Method",
    message=(
        f"Hi {sub.user.first_name or sub.user.email},\n\n"
        f"We were unable to process your {sub.plan.name} subscription payment "
        f"for {sub.product.name}. Your access will be suspended if payment "
        f"is not updated.\n\n"
        f"Please update your payment method here: {portal_link}\n\n"
        f"If you believe this is an error, please contact support."
    ),
    from_email=settings.DEFAULT_FROM_EMAIL,
    recipient_list=[sub.user.email],
    fail_silently=True,
)
logger.info(f"Dunning email sent to {sub.user.email} for sub={sub.id}")
```

Additionally, send email at **3-day** and **5-day** marks (not just 7 days), with increasingly urgent language. Add `last_dunning_email_at` to the Subscription model to prevent duplicate emails.

---

### UX-02 🟠 High — No Cancellation Confirmation Flow

**File**: `frontend/src/components/vue/BillingOverview.vue` (lines 128-148)  
**Problem**: The cancel confirmation uses only a toast with "Yes, cancel" — no full modal explaining the consequences. Users don't see their exact renewal date, what features they lose, or a save-the-deal offer.

**Solution**: Build a `CancelSubscriptionModal.vue` component that shows:
- Exact date access ends
- Feature comparison (current plan vs. free plan)
- "Pause instead" option (if applicable)
- Feedback form ("Why are you leaving?") — this data is gold for retention
- Clear "Keep my plan" primary CTA with "Cancel anyway" as a subdued secondary action

---

### UX-03 🟠 High — Currency Mismatch Error Is Hard to Recover From

**File**: `backend/billing/controllers.py` (lines 699-710)  
**Problem**: When a user hits the currency mismatch, the error message says "change your currency preference" — but there is no UI to do this on the billing page. The user is stuck.

**Solution**: Add a currency selector dropdown on the billing overview page and the plan comparison page. When the API returns a currency mismatch error, the frontend should:
1. Parse the error to extract the locked currency
2. Show a prominent banner: "Your billing is locked to EUR. Switch to EUR pricing?"
3. Auto-switch the `userCurrency` ref and re-fetch plans in the correct currency

```vue
<!-- BillingOverview.vue — add after stats row -->
<div class="mb-4 rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30 p-4"
     v-if="currencyMismatch">
  <p class="text-sm font-medium text-blue-800 dark:text-blue-300">
    Your billing account uses {{ lockedCurrency }}.
  </p>
  <p class="mt-1 text-sm text-blue-700 dark:text-blue-400">
    Switch pricing to {{ lockedCurrency }} to continue.
  </p>
  <button class="btn-primary text-xs mt-2" @click="switchCurrency(lockedCurrency)">
    Switch to {{ lockedCurrency }}
  </button>
</div>
```

---

### UX-04 🟠 High — No Payment Method Change Feedback on Portal Return

**File**: `frontend/src/components/vue/BillingOverview.vue`  
**Problem**: After returning from Stripe Portal, the page shows no feedback about what changed. If a user updates their card via Portal, they get no confirmation.

**Solution**: After `handleManageBilling()`, the Stripe Portal redirects back to `STRIPE_PORTAL_RETURN_URL`. Add a `?portal=success` parameter to the return URL and handle it like `checkout=success`:

```javascript
// In onMounted(), add alongside checkout handling:
const portalStatus = params.get("portal");
if (portalStatus === "success") {
  showToast("Billing settings updated successfully.", "success", { duration: 5000 });
  window.history.replaceState({}, "", "/dashboard/billing");
  // Re-fetch subscriptions to reflect any portal changes
  subscriptions.value = await billingApi.getSubscriptions();
}
```

Also update the return URL builder in `portal.py` to append `?portal=success`.

---

### UX-05 🟡 Medium — Transaction History Requires Admin Endpoint

**File**: `frontend/src/lib/billing.ts` (line 267-281), `BillingOverview.vue` (line 191)  
**Problem**: Transaction history is fetched from `/billing/admin/transactions` — an admin-only endpoint. Regular users calling this will get a 403 error if the admin guard fires. While the controller does check `is_staff`, the fact that a regular user page calls an admin endpoint is architecturally wrong.

**Solution**: Create a new user-facing endpoint `GET /billing/subscriptions/transactions` under `BillingProtectedController` that only returns the current user's invoices. Remove the admin transaction endpoint or keep it only for admin-only views with broader query capabilities.

```python
# controllers.py — add to BillingProtectedController
@http_get("/transactions", response=dict, summary="Get my billing history")
async def get_my_transactions(self, request, limit: int = 25, starting_after: str = None):
    """Get the authenticated user's own transaction history from Stripe."""
    try:
        result = await sync_to_async(get_transaction_history)(
            user=request.user, limit=min(limit, 100), starting_after=starting_after,
        )
    except stripe.error.StripeError as e:
        raise BadRequestException(handle_stripe_error(e, context="get_transactions"))
    return result
```

---

### UX-06 🟡 Medium — No Loading State During Initial Checkout

**File**: `frontend/src/components/vue/PlanComparison.vue` (lines 225-269)  
**Problem**: When the user clicks "Upgrade Now" or "Subscribe", there is a loading state (`actionLoading`), but during the Stripe redirect there is no visual indication that the user is being redirected. On slow connections, users may click multiple times.

**Solution**: Add a full-page overlay during redirect:

```vue
<Teleport to="body">
  <div v-if="isRedirecting" class="fixed inset-0 z-50 flex items-center justify-center bg-white/80 dark:bg-gray-900/80">
    <div class="text-center">
      <div class="animate-spin h-8 w-8 border-4 border-brand-500 border-t-transparent rounded-full mx-auto mb-4" />
      <p class="text-sm font-medium">Redirecting to secure checkout...</p>
    </div>
  </div>
</Teleport>
```

---

### UX-07 🟡 Medium — No "Per-Seat" or "Usage" Display for Plans

**File**: `frontend/src/components/vue/PlanComparison.vue`  
**Problem**: Plans show features as key-value text but no visual distinction between "10 team members" and "unlimited storage". Feature lists should use consistent iconography (checkmark vs. infinity vs. number badge).

**Solution**: Add semantic rendering to the feature list:

```vue
<li v-for="(value, key) in plan.features" :key="key" class="flex items-start gap-2.5 text-sm">
  <!-- Numeric limit -->
  <svg v-if="typeof value === 'number' || String(value).match(/^\d+$/)" class="...">
    <text>{{ value }}</text>
  </svg>
  <!-- Unlimited -->
  <svg v-else-if="String(value).match(/unlimited|infinity/i)" class="...">
    <path d="M12 2v20" /> <!-- infinity icon -->
  </svg>
  <!-- Boolean true -->
  <svg v-else class="...">
    <path d="M5 13l4 4L19 7" /> <!-- checkmark -->
  </svg>
  <span>{{ String(key).replace(/_/g, ' ') }} — {{ value }}</span>
</li>
```

---

### UX-08 🟡 Medium — No Webhook Timeout Fallback (UX Impact)

**File**: `backend/billing/stripe/webhooks/router.py` (lines 62-78)  
**Problem**: The `_timeout` context manager uses `signal.SIGALRM` which only works on Unix. On Windows or in some container environments, SIGALRM silently fails, meaning webhooks can hang indefinitely. From a UX perspective, a hanging webhook means subscription activation is delayed after checkout.

**Solution**: Replace with a portable timeout using threading:

```python
import threading

@contextmanager
def _timeout(seconds: int):
    result = [None]
    def _target():
        try:
            handler(*args, **kwargs)
        except Exception as e:
            result[0] = e
    
    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    thread.join(timeout=seconds)
    if thread.is_alive():
        raise TimeoutError(f"Webhook processing exceeded {seconds}s")
    if result[0]:
        raise result[0]
```

Or use Django's built-in `django.utils.module_loading.import_string` with a configurable timeout. Alternatively, set a Gunicorn/uWSGI worker timeout.

---

### UX-09 🔵 Low — "Free Plan" Has No Upgrade CTA on Billing Overview

**File**: `frontend/src/components/vue/BillingOverview.vue`  
**Problem**: When a user is on the Free plan, the subscription card shows "Free Plan" with a "View Plans" button, but no prominent "Upgrade" CTA. The "View Plans" link is the same weight as a regular action.

**Solution**: Add an "Upgrade" badge or a highlighted CTA button specifically for free-plan subscriptions:

```vue
<button v-if="sub.plan_slug === 'free'" class="btn-primary text-xs">
  Upgrade
</button>
```

---

### UX-10 🔵 Low — Plan Comparison Page Doesn't Show Savings for Annual

**File**: `frontend/src/components/vue/PlanComparison.vue`  
**Problem**: If both monthly and yearly billing cycles are available, users can't see the annual savings. No comparison or "Save 20%" badge is shown.

**Solution**: When a product has both monthly and yearly versions of the same plan, calculate and display the annual savings percentage:

```javascript
const annualSavings = computed(() => {
  if (!product.value) return {};
  const savings = {};
  for (const plan of product.value.plans) {
    if (plan.billing_cycle === 'yearly') {
      const monthlyPlan = product.value.plans.find(
        p => p.slug === plan.slug && p.billing_cycle === 'monthly'
      );
      if (monthlyPlan) {
        const monthlyTotal = monthlyPlan.price_cents * 12;
        const yearlyTotal = plan.price_cents;
        savings[plan.slug] = Math.round((1 - yearlyTotal / monthlyTotal) * 100);
      }
    }
  }
  return savings;
});
```

---

## 3. Audit Perspective 2 — Finance & Accounting Expert

### FIN-01 🔴 Critical — No Invoice Line Item Data Stored Locally

**File**: `backend/billing/stripe/webhooks/handlers/invoice.py` (lines 59-66)  
**Problem**: The `handle_invoice_created` handler only logs the invoice number and amount. It does **not** store invoice line items (plan name, period, tax breakdown, discount) in the local database. The `Refund` model stores `stripe_response` as JSON, but there is no `Invoice` model at all.

**Impact**: 
- Cannot generate itemized statements without calling Stripe API each time
- Revenue recognition reporting requires pulling all invoices from Stripe
- Tax reporting (VAT/GST) requires real-time Stripe API calls
- Dispute resolution requires manual Stripe Dashboard access

**Solution**: Create an `Invoice` model:

```python
# backend/billing/models.py
class Invoice(TimeStampedModel):
    stripe_invoice_id = models.CharField(max_length=100, unique=True, db_index=True)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="invoices")
    stripe_subscription_id = models.CharField(max_length=100, db_index=True)
    number = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20)  # draft, open, paid, uncollectible, void
    amount_paid_cents = models.PositiveIntegerField(default=0)
    amount_due_cents = models.PositiveIntegerField(default=0)
    tax_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    period_start = models.DateTimeField(null=True)
    period_end = models.DateTimeField(null=True)
    hosted_url = models.URLField(blank=True)
    pdf_url = models.URLField(blank=True)
    stripe_response = models.JSONField(default=dict)
    
    class Meta:
        db_table = "billing_invoice"
        ordering = ["-created_at"]
```

Update `handle_invoice_created` and `handle_invoice_payment_succeeded` to create/update this record from the Stripe event data.

---

### FIN-02 🔴 Critical — No Payment Retry Logic (Dunning Automation)

**File**: `backend/billing/tasks.py` (lines 99-147)  
**Problem**: The `dunning_retry` task only logs warnings. Stripe has its own retry schedule, but the local system does nothing to proactively manage failed payments. There is no logic to:
- Retry payment after configurable intervals
- Escalate from email notification to access restriction
- Automatically cancel after N failed attempts
- Sync Stripe's `next_payment_attempt` timestamp locally

**Solution**: Build a proper dunning workflow:

```python
# backend/billing/tasks.py — enhanced dunning_retry
DUNNING_STEPS = [
    {"days": 3, "action": "email_reminder"},
    {"days": 5, "action": "email_urgent"},
    {"days": 7, "action": "restrict_access"},  # Downgrade to free features
    {"days": 14, "action": "cancel_subscription"},
]

def dunning_retry(self):
    for sub in past_due_subs:
        days_past_due = (timezone.now() - sub.updated_at).days
        for step in DUNNING_STEPS:
            if days_past_due >= step["days"]:
                execute_dunning_step(sub, step["action"])
```

This creates a predictable, transparent dunning schedule that users understand.

---

### FIN-03 🟠 High — Refund Amount Not Validated Against Invoice

**File**: `backend/billing/stripe/__init__.py` (lines 197-249)  
**Problem**: `create_stripe_refund()` accepts `amount_cents` from the admin payload but does NOT validate it against the actual invoice payment amount before sending to Stripe. While Stripe will reject over-refunds, the local `Refund` record could still be created with an incorrect amount if the Stripe call succeeds for a different amount than requested.

Additionally, the refund is always against the **latest** invoice's `payment_intent`. If a user has been subscribed for 12 months, the admin can only refund the most recent month — there's no way to refund a specific historical payment.

**Solution**: Add validation and support for specific charge targeting:

```python
def create_stripe_refund(subscription, amount_cents=None, reason="", initiated_by=None,
                         charge_id=None):  # Allow targeting specific charges
    # ... existing code ...
    
    # Validate amount does not exceed charge amount
    if amount_cents and amount_cents > refund_max:
        raise ValueError(
            f"Refund amount ({amount_cents/100:.2f}) exceeds maximum "
            f"chargeable amount ({refund_max/100:.2f})"
        )
```

Also fetch and store `amount_paid` from the invoice to use as the cap.

---

### FIN-04 🟠 High — No Prorated Credit Tracking

**File**: `backend/billing/schemas.py` (lines 336-343)  
**Problem**: The `ProrationPreviewOutputSchema` shows a proration total but there is no `Proration` model to persist these records. When a plan change happens, the proration credit/charge from Stripe's upcoming invoice is shown once and then lost. This means:
- No historical record of what credits were applied
- Cannot audit whether a user's plan change was correctly billed
- No way to reconcile Stripe's proration amounts with local records

**Solution**: Create a `PlanChangeLog` model:

```python
class PlanChangeLog(TimeStampedModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name="plan_changes")
    from_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="+")
    to_plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="+")
    proration_amount_cents = models.IntegerField()  # Negative = credit, Positive = charge
    currency = models.CharField(max_length=3)
    stripe_proration_id = models.CharField(max_length=100, blank=True)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    proration_behavior = models.CharField(max_length=30)  # create_prorations, none
    
    class Meta:
        db_table = "billing_plan_change_log"
        ordering = ["-created_at"]
```

---

### FIN-05 🟠 High — Exchange Rate Used for Display, Not for Billing

**File**: `backend/billing/currency_service.py`, `backend/billing/stripe/prices.py`  
**Problem**: The `ExchangeRate` table is used for two purposes: (1) displaying converted prices on the frontend, and (2) creating Stripe prices in non-base currencies (line 131 of `prices.py`). The exchange rate API (`open.er-api.com`) is a free tier service that:
- May have rates that differ from Stripe's own exchange rates
- Updates only once daily via Celery, but Stripe may update more frequently
- Has no SLA or guarantee of availability

If the exchange rate drifts between the time a price is created and the time Stripe processes the payment, the user may be charged slightly more or less than displayed.

**Solution**: 
1. Add a disclaimer on the frontend: "Prices in [currency] are approximate. Final charge is in [base currency]."
2. Consider using Stripe's own multi-currency pricing (create prices in each currency manually) instead of computing from exchange rates.
3. Store the `exchange_rate` at the time of price creation in the Stripe price metadata (already partially done in `prices.py` line 147).
4. Log the exchange rate used for each checkout in a `CheckoutLog` for reconciliation.

---

### FIN-06 🟠 High — Transaction History Schema Mismatch

**File**: `frontend/src/lib/billing.ts` (lines 143-163), `backend/billing/stripe/__init__.py` (lines 257-290)  
**Problem**: The frontend `TransactionItemSchema` expects fields like `type`, `amount_due`, `tax`, `description`, `pdf_url`, `period_start`, `period_end`, `paid`, `attempt_count`, `charge_id`, `payment_method`, `card_brand` — but the backend `get_transaction_history()` returns a much simpler object with only `id`, `number`, `amount`, `currency`, `status`, `hosted_url`, `created`.

The frontend will render empty/undefined values for all the extra fields, showing broken UI.

**Solution**: Expand the backend to include the missing fields:

```python
# backend/billing/stripe/__init__.py — get_transaction_history()
for inv in result["data"]:
    charge = inv.get("charge") or {}
    charge_obj = charge if isinstance(charge, dict) else {}
    payment_method = charge_obj.get("payment_method_details") or {}
    card = payment_method.get("card") or {}
    
    transactions.append({
        "id": inv.get("id"),
        "number": inv.get("number"),
        "amount": (inv.get("amount_paid") or 0) / 100,
        "amount_due": (inv.get("amount_due") or 0) / 100,
        "tax": (inv.get("tax") or 0) / 100,
        "currency": (inv.get("currency") or "usd").upper(),
        "status": inv.get("status"),
        "hosted_url": inv.get("hosted_invoice_url"),
        "pdf_url": inv.get("invoice_pdf"),
        "created": inv.get("created"),
        "period_start": inv.get("period_start"),
        "period_end": inv.get("period_end"),
        "paid": inv.get("status") == "paid",
        "attempt_count": inv.get("attempt_count", 1),
        "charge_id": charge_obj.get("id"),
        "payment_method": (card.get("last4") or ""),
        "card_brand": (card.get("brand") or ""),
        "description": inv.get("description") or f"Invoice for {inv.get('lines', {}).get('data', [{}])[0].get('description', 'Subscription')}" if inv.get('lines') else "Invoice",
    })
```

---

### FIN-07 🟡 Medium — No Revenue Recognition Support

**File**: Backend billing models overall  
**Problem**: There is no `Revenue` or `LedgerEntry` model to track recognized revenue vs. deferred revenue. For monthly/annual subscriptions, revenue should be recognized daily/monthly, not all at once at billing time. This is a fundamental accounting requirement for any SaaS that wants accurate financial reporting.

**Solution**: Add a `RevenueRecognitionEntry` model that gets populated by a Celery task:

```python
class RevenueRecognitionEntry(TimeStampedModel):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    recognized_date = models.DateField(db_index=True)  # Daily recognition
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    
    class Meta:
        db_table = "billing_revenue_recognition"
        unique_together = ["subscription", "recognized_date"]
```

---

### FIN-08 🟡 Medium — Webhook Event Log Has No Cleanup Strategy

**File**: `backend/billing/models.py` (lines 808-865), `backend/billing/tasks.py`  
**Problem**: The `WebhookEventLog` stores the full Stripe event payload as JSON. Over time, this table will grow unboundedly — each event can be several KB of JSON. The comment references a "Phase 5" cleanup task that doesn't exist.

**Solution**: Add a cleanup Celery task:

```python
@shared_task
def cleanup_stale_webhook_events(self, retention_days: int = 90):
    """Delete processed webhook events older than retention period."""
    from django.utils import timezone
    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    deleted, _ = WebhookEventLog.objects.filter(
        processed=True,
        created_at__lte=cutoff,
    ).delete()
    logger.info(f"Cleaned up {deleted} stale webhook events (retention={retention_days}d)")
    return {"deleted": deleted}
```

---

### FIN-09 🔵 Low — No Stripe Fee Tracking

**File**: Backend billing models  
**Problem**: Stripe charges a processing fee (typically 2.9% + $0.30 per transaction), but this is not tracked locally. For accurate gross vs. net revenue reporting, the fee amount should be stored.

**Solution**: When processing `invoice.payment_succeeded`, fetch the associated Stripe Balance Transaction and store the fee:

```python
# In webhook handler or reconciliation task
balance_tx = stripe.BalanceTransaction.retrieve(charge["balance_transaction"])
fee_cents = balance_tx["fee"]
```

---

## 4. Audit Perspective 3 — Financial Compliance Expert

### CMP-01 🔴 Critical — No GDPR Data Export for Billing Data

**File**: `backend/billing/stripe/gdpr.py`  
**Problem**: The GDPR module only handles deletion/anonymization. GDPR Article 20 (Right to Data Portability) requires that users can export all their personal data, including billing history. Currently:
- There is no endpoint to export billing data
- Stripe customer data is not pulled into a downloadable format
- Refund history, subscription history, and invoice history cannot be bulk-exported

**Solution**: Add a data export function:

```python
# backend/billing/stripe/gdpr.py
def export_user_billing_data(user) -> dict:
    """Export all billing data for a user (GDPR Art. 20)."""
    from ..models import Subscription, Refund
    
    subscriptions = Subscription.objects.filter(user=user).select_related("plan", "product")
    refunds = Refund.objects.filter(subscription__user=user)
    
    customer_id = find_customer_id(user)
    stripe_data = {}
    if customer_id:
        stripe_data = retrieve_customer(customer_id)
    
    return {
        "user": {"email": user.email, "name": user.get_full_name()},
        "stripe_customer": {
            "id": customer_id,
            "created": stripe_data.get("created"),
            "currency": stripe_data.get("metadata", {}).get("preferred_currency"),
        },
        "subscriptions": [
            {
                "product": s.product.name,
                "plan": s.plan.name,
                "status": s.status,
                "currency": s.currency,
                "created": s.created_at.isoformat(),
                "canceled_at": s.canceled_at.isoformat() if s.canceled_at else None,
            }
            for s in subscriptions
        ],
        "refunds": [
            {
                "amount": r.amount_cents,
                "currency": r.currency,
                "status": r.status,
                "reason": r.reason,
                "created": r.created_at.isoformat(),
            }
            for r in refunds
        ],
        "exported_at": timezone.now().isoformat(),
    }
```

And add a controller endpoint:

```python
@http_get("/export-data", response=dict, summary="Export billing data (GDPR)")
async def export_billing_data(self, request):
    """Export all billing data for the authenticated user."""
    require_verified_email(request)
    data = await sync_to_async(export_user_billing_data)(request.user)
    return data
```

---

### CMP-02 🟠 High — No Audit Trail for Admin Refund Actions

**File**: `backend/billing/models.py` (lines 650-735)  
**Problem**: The `Refund` model tracks `initiated_by` (admin user) but does not track:
- The admin's IP address
- The reason category (customer request, error, goodwill, policy)
- Approval workflow (if multi-step approval is needed)
- Timestamp of when the refund was initiated vs. when it was completed by Stripe

For PCI-DSS compliance and financial audits, there must be a complete chain of custody for refund actions.

**Solution**: Extend the `Refund` model:

```python
class Refund(TimeStampedModel):
    # ... existing fields ...
    
    # Audit trail additions
    initiated_by_ip = models.GenericIPAddressField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="approved_refunds",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    reason_category = models.CharField(
        max_length=30, blank=True,
        choices=[
            ("customer_request", "Customer Request"),
            ("billing_error", "Billing Error"),
            ("goodwill", "Goodwill"),
            ("policy", "Policy Refund"),
            ("chargeback", "Chargeback"),
        ],
    )
    admin_notes = models.TextField(blank=True)
```

Capture the IP in the controller:

```python
from django.contrib.geoip import GeoIP2  # or use request.META['REMOTE_ADDR']
refund = create_stripe_refund(
    subscription=subscription,
    amount_cents=validated.amount_cents,
    reason=validated.reason,
    initiated_by=request.user,
)
refund.initiated_by_ip = request.META.get("REMOTE_ADDR")
refund.save(update_fields=["initiated_by_ip"])
```

---

### CMP-03 🟠 High — Webhook Signature Verification Returns Parsed JSON, Not Verified Object

**File**: `backend/billing/stripe/client.py` (lines 282-287)  
**Problem**: The `verify_webhook_signature()` function calls `stripe.Webhook.construct_event()` but then discards the returned event object and manually parses `payload.decode("utf-8")` back into JSON. This is problematic because:
- The original Stripe event object has typed fields and methods
- Manual JSON parsing could theoretically be tampered with (though the signature check happens first)
- The function name says "verify" but actually returns unverified raw JSON

**Solution**: Return the Stripe event object converted to dict via `to_dict()`:

```python
def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verify Stripe signature and return verified event dict."""
    event = stripe.Webhook.construct_event(payload, sig_header, get_webhook_secret())
    return to_dict(event)  # Use the verified event, not re-parsed raw JSON
```

---

### CMP-04 🟠 High — Stripe API Key Logged on 401 Errors

**File**: `backend/billing/stripe_errors.py` (lines 283-289)  
**Problem**: On HTTP 401 errors, the code logs at CRITICAL level: `"Stripe API key is invalid or missing!"`. While this doesn't log the key itself, in a cloud logging environment (CloudWatch, Datadog, etc.), the log context (request headers, stack trace) might leak the key through settings files. More importantly, this should be an alert, not just a log.

**Solution**: Replace logging with an active alert mechanism:

```python
if http_status == 401:
    logger.critical(
        f"{log_ctx}Stripe API key is invalid or missing! "
        f"Check SF_STRIPE_SECRET_KEY in settings."
    )
    # Send admin alert (Slack, email, PagerDuty)
    from django.core.mail import mail_admins
    mail_admins(
        "CRITICAL: Stripe API Key Invalid",
        f"The Stripe API key is invalid or missing. "
        f"All payment processing is currently broken. "
        f"Context: {context}",
        fail_silently=True,
    )
    return "Payment system is temporarily unavailable. Please contact support."
```

---

### CMP-05 🟠 High — No Webhook Endpoint Rate Limiting

**File**: `backend/billing/controllers.py` (lines 1000+)  
**Problem**: The webhook endpoint has no rate limiting. An attacker could flood the webhook URL with fake events. While signature verification would reject invalid signatures, the verification itself consumes resources. A high volume of invalid requests could cause denial of service.

**Solution**: Add IP-based rate limiting to the webhook endpoint:

```python
from common.rate_limit import check_rate_limit_or_raise

@api_controller("/billing", tags=["Billing — Webhooks"], auth=None)
class BillingWebhookController:
    
    @http_post("/webhooks/stripe")
    async def stripe_webhook(self, request: HttpRequest):
        check_rate_limit_or_raise(request, "webhook", max_requests=100, window_seconds=60)
        # ... rest of webhook processing
```

---

### CMP-06 🟡 Medium — ToS Acceptance Not Version-Controlled Per Checkout

**File**: `backend/billing/controllers.py` (lines 606-609, 666-674)  
**Problem**: `tos_accepted` is checked as a boolean and `tos_version` is set from `settings.TOS_VERSION`. But there is no per-checkout ToS acceptance record. If the ToS changes while a user is mid-checkout, the old session's ToS acceptance could become invalid.

**Solution**: Add `tos_accepted_at` and `tos_version` to the checkout metadata sent to Stripe, and validate the version at confirmation time:

```python
# In create_checkout():
tos_version = getattr(settings, "TOS_VERSION", "1.0")
session = _create_checkout(
    # ... existing params ...
    metadata={
        # ... existing metadata ...
        "tos_version": tos_version,
    },
)

# In confirm_checkout():
checkout_tos_version = metadata.get("tos_version")
current_tos_version = getattr(settings, "TOS_VERSION", "1.0")
if checkout_tos_version != current_tos_version:
    logger.warning(f"ToS version mismatch for checkout {session_id}: "
                    f"checkout={checkout_tos_version}, current={current_tos_version}")
```

---

### CMP-07 🟡 Medium — No Idempotency Key on Checkout Creation

**File**: `backend/billing/stripe/checkout.py` (lines 55-117)  
**Problem**: The checkout session creation has no idempotency key. If a user double-clicks the checkout button (or a network retry triggers the API call twice), two checkout sessions could be created, potentially resulting in double charges.

The refund function (`create_stripe_refund`) correctly uses idempotency keys (line 217-219 of `__init__.py`), but checkout does not.

**Solution**: Add idempotency key to checkout:

```python
import hashlib
import time

def create_checkout(user, plan, product, currency, trial_days=None):
    # ... existing validation ...
    
    idempotency_key = f"checkout-{user.id}-{product.slug}-{plan.slug}-{int(time.time())}"
    
    session = _create_checkout(
        # ... existing params ...
        # Note: stripe.checkout.Session.create doesn't support idempotency_key
        # directly, but we can check for existing active sessions
    )
```

Since Stripe Checkout doesn't natively support idempotency keys, add a local deduplication check:

```python
# Check for existing active checkout in the last 5 minutes
from ..models import WebhookEventLog  # Or use a CheckoutSession model
recent_checkout = CheckoutSession.objects.filter(
    user=user, plan=plan,
    status="open",
    created_at__gte=timezone.now() - timezone.timedelta(minutes=5),
).first()
if recent_checkout:
    return recent_checkout.url  # Return existing session
```

---

### CMP-08 🟡 Medium — Customer Portal Configuration Is Minimal

**File**: `backend/billing/stripe/portal.py`  
**Problem**: The portal session is created with only `customer_id` and `return_url`. Stripe Customer Portal supports extensive configuration:
- Which features are enabled (cancellation, payment method update, subscription pause)
- Business information (company name, address, privacy policy URL)
- Custom branding

Without proper configuration, users see Stripe's default portal which may not match the product's branding or may expose features you want to disable (e.g., self-service cancellation without confirmation).

**Solution**: Configure the portal in Stripe Dashboard or via the API when creating sessions:

```python
def create_portal(user, return_url: str = None) -> str:
    customer_id = find_customer_id(user)
    if not customer_id:
        raise ValueError("No Stripe customer found. Complete a checkout first.")
    
    _return_url = return_url or getattr(settings, "STRIPE_PORTAL_RETURN_URL", "")
    
    session = _create_portal(
        customer_id=customer_id,
        return_url=_return_url,
        # Add configuration:
        configuration="bpc_XXXX",  # Pre-configured portal configuration ID
    )
    return session["url"]
```

---

### CMP-09 🔵 Low — No Access Logging for Billing Admin Endpoints

**File**: `backend/billing/controllers.py` (lines 860-992)  
**Problem**: Admin endpoints (refund, sync, transactions) don't log who accessed them, when, and from where. For financial compliance, all admin access to billing data must be logged.

**Solution**: Add an access log decorator or middleware:

```python
def log_admin_access(func):
    @wraps(func)
    async def wrapper(self, request, *args, **kwargs):
        logger.info(
            f"ADMIN_BILLING_ACCESS: user={request.user.id}, "
            f"email={request.user.email}, action={func.__name__}, "
            f"ip={request.META.get('REMOTE_ADDR')}, "
            f"path={request.path}"
        )
        return await func(self, request, *args, **kwargs)
    return wrapper
```

---

## 5. Cross-Cutting Findings

### CC-01 🟡 Medium — `handle_stripe_error` Returns String but Is Used Inconsistent Ways

**File**: `backend/billing/controllers.py`, `backend/billing/stripe_errors.py`  
**Problem**: `handle_stripe_error()` returns a string, but controllers wrap it in `BadRequestException(handle_stripe_error(e))`. In the `cancel_subscription` endpoint (lines 391-393), the pattern is:

```python
raise BadRequestException(
    handle_stripe_error(e, context="cancel_subscription")
)
```

But `handle_stripe_error` already returns a user-friendly string. Wrapping it in another exception may cause the error handler in `api/views.py` to double-wrap or format the message inconsistently.

**Solution**: Make `handle_stripe_error` return a `BadRequestException` directly:

```python
def handle_stripe_error(error, context=None) -> BadRequestException:
    """Translate Stripe error into a BadRequestException."""
    # ... existing matching logic ...
    return BadRequestException(user_message)
```

Then in controllers: `raise handle_stripe_error(e, context="cancel_subscription")`

---

### CC-02 🟡 Medium — No Integration Tests for Stripe Flows

**File**: `backend/billing/tests.py` (not yet read but observed as essentially empty)  
**Problem**: There are no tests for the critical billing flows. Given the financial nature of this code, every flow should have:
- Unit tests with `unittest.mock.patch` for Stripe SDK calls
- Integration tests with Stripe's test mode API
- Edge case tests for error paths (currency mismatch, card declined, etc.)

**Solution**: Create comprehensive test suite:

```
backend/billing/tests/
├── __init__.py
├── test_stripe_errors.py      # Pattern matching tests
├── test_checkout.py           # Checkout + confirm flow
├── test_cancel_reactivate.py  # Cancel/reactivate flow
├── test_change_plan.py        # Plan change + proration
├── test_webhooks.py           # All webhook handlers
├── test_currency_service.py   # Exchange rate conversion
├── test_refund.py             # Admin refund flow
├── test_portal.py             # Portal session creation
└── test_gdpr.py               # Deletion/anonymization/export
```

Use Stripe's test mode with test card numbers:
- `4242424242424242` — succeeds
- `4000000000000002` — card declined
- `4000000000009995` — insufficient funds
- `4000000000000341` — expired card

---

### CC-03 🟡 Medium — `currency_service.py` Uses Free API Without Fallback

**File**: `backend/billing/currency_service.py` (lines 172-203)  
**Problem**: The exchange rate API (`open.er-api.com`) is free, has no SLA, and is rate-limited. If the API is down when the Celery task runs, no rates are updated, and all currency conversions will fail silently (returning `None`, which causes the frontend to show base prices without any indication of an error).

**Solution**: 
1. Add a fallback API (e.g., `exchangerate.host`, `frankfurter.app`)
2. Cache the last known good rates — never overwrite with empty data
3. Alert if rates are stale (>48 hours old):
```python
def update_exchange_rates():
    try:
        result = _fetch_and_update_rates()
    except Exception:
        # Try fallback API
        try:
            result = _fetch_from_fallback_api()
        except Exception as e:
            logger.error(f"All exchange rate APIs failed: {e}")
            # Alert — rates are stale
            mail_admins("Exchange Rate Update Failed", str(e), fail_silently=True)
            return {"updated": 0, "skipped": 0, "error": str(e)}
```

---

### CC-04 🔵 Low — Stripe `to_dict()` Drops `None` Values

**File**: `backend/billing/stripe/client.py` (lines 52-58)  
**Problem**: The `to_dict()` helper converts Stripe objects to dicts, but Stripe's `to_dict()` method may omit `None` values. This means code that does `stripe_sub.get("canceled_at")` might get `None` or might not get the key at all, leading to subtle bugs.

**Solution**: Use a more robust conversion:

```python
def to_dict(obj) -> dict:
    if hasattr(obj, "to_dict"):
        d = obj.to_dict()
        # Ensure all expected keys exist (set missing to None)
        if isinstance(d, dict):
            return d
    if isinstance(obj, dict):
        return obj
    return dict(obj)
```

The current code is already defensive with `.get()` calls, so this is low severity, but a custom serializer that guarantees all known keys would be safer.

---

## 6. Prioritized Implementation Roadmap

### Phase 1 — Critical (This Week)

| ID | Finding | Effort | Impact |
|----|---------|--------|--------|
| UX-01 | Dunning email notifications | 2h | Prevents involuntary churn |
| FIN-01 | Invoice model + storage | 4h | Enables financial reporting |
| FIN-02 | Payment retry automation | 3h | Recovers failed revenue |
| CMP-01 | GDPR data export endpoint | 2h | Legal compliance |

### Phase 2 — High (Next Sprint)

| ID | Finding | Effort | Impact |
|----|---------|--------|--------|
| UX-02 | Cancel confirmation modal | 3h | Reduces cancellation rate |
| UX-03 | Currency mismatch recovery UI | 2h | Removes billing blocker |
| UX-04 | Portal return feedback | 1h | User confidence |
| UX-05 | User-facing transaction endpoint | 2h | Fix 403 error for regular users |
| FIN-03 | Refund validation + historical | 2h | Prevents refund errors |
| FIN-04 | Plan change audit log | 2h | Billing audit trail |
| FIN-05 | Exchange rate disclaimer | 1h | Prevents disputes |
| FIN-06 | Transaction schema alignment | 2h | Fix broken billing history UI |
| CMP-02 | Refund audit trail | 2h | Compliance |
| CMP-03 | Webhook verification fix | 1h | Security hardening |
| CMP-04 | API key alert mechanism | 1h | Operational monitoring |
| CMP-05 | Webhook rate limiting | 1h | DoS protection |

### Phase 3 — Medium (Following Sprint)

| ID | Finding | Effort | Impact |
|----|---------|--------|--------|
| UX-06 | Checkout redirect overlay | 1h | Prevents double-clicks |
| UX-07 | Feature list iconography | 1h | Visual polish |
| UX-08 | Portable webhook timeout | 2h | Cross-platform reliability |
| FIN-07 | Revenue recognition model | 4h | Accounting compliance |
| FIN-08 | Webhook log cleanup task | 1h | Database maintenance |
| CMP-06 | ToS version control | 1h | Legal protection |
| CMP-07 | Checkout idempotency | 2h | Prevent double charges |
| CMP-08 | Portal configuration | 1h | Branding consistency |
| CC-01 | Error handler consistency | 1h | Code quality |
| CC-02 | Billing test suite | 8h | Confidence in changes |
| CC-03 | Exchange rate fallback | 2h | Rate reliability |

### Phase 4 — Low (When Time Permits)

| ID | Finding | Effort | Impact |
|----|---------|--------|--------|
| UX-09 | Free plan upgrade CTA | 0.5h | Conversion optimization |
| UX-10 | Annual savings display | 1h | Upsell improvement |
| FIN-09 | Stripe fee tracking | 2h | Revenue accuracy |
| CMP-09 | Admin access logging | 1h | Audit compliance |
| CC-04 | to_dict() robustness | 1h | Code safety |

---

## Appendix A — Files Audited

### Backend (30 files)
| File | Lines | Purpose |
|------|-------|---------|
| `billing/controllers.py` | ~1050 | HTTP routing, Stripe-first architecture |
| `billing/stripe_errors.py` | 308 | Centralized Stripe error translation |
| `billing/models.py` | 866 | Subscription, Product, Plan, Refund, ExchangeRate, WebhookEventLog |
| `billing/schemas.py` | 343 | Pydantic request/response schemas |
| `billing/services.py` | 581 | Business logic, auth/me, subscription management |
| `billing/currency_service.py` | 289 | Exchange rate fetching, price conversion |
| `billing/tasks.py` | 175 | Celery tasks: reconcile, sync, dunning, exchange rates |
| `billing/stripe/__init__.py` | 298 | Public API: cancel, reactivate, change plan, refund, transactions |
| `billing/stripe/client.py` | 314 | Low-level Stripe SDK adapter |
| `billing/stripe/checkout.py` | 199 | Checkout session creation and confirmation |
| `billing/stripe/customer.py` | 127 | Customer creation, lookup, sync |
| `billing/stripe/portal.py` | 32 | Customer Portal session |
| `billing/stripe/prices.py` | 155 | Price resolution in any currency |
| `billing/stripe/gdpr.py` | 61 | GDPR deletion/anonymization |
| `billing/stripe/webhooks/router.py` | 176 | Signature verification, event logging, handler dispatch |
| `billing/stripe/webhooks/sync.py` | 174 | Single-source-of-truth subscription sync |
| `billing/stripe/webhooks/handlers/checkout.py` | 36 | checkout.session.completed handler |
| `billing/stripe/webhooks/handlers/subscription.py` | 69 | subscription CRUD event handlers |
| `billing/stripe/webhooks/handlers/charge.py` | 109 | charge.refunded + customer.updated handlers |
| `billing/stripe/webhooks/handlers/invoice.py` | 67 | invoice payment handlers |
| `sattaledger/settings.py` | (grep) | Stripe configuration variables |

### Frontend (6 files)
| File | Lines | Purpose |
|------|-------|---------|
| `lib/billing.ts` | 378 | API client, types, formatting helpers |
| `components/vue/BillingOverview.vue` | 624 | Billing dashboard with subscription cards, transactions |
| `components/vue/PlanComparison.vue` | 558 | Plan cards, feature comparison, checkout/proration flows |
| `pages/dashboard/billing/index.astro` | 7 | Billing page shell |
| `pages/dashboard/billing/plans/[slug].astro` | 9 | Plan detail page shell |

---

## Appendix B — Configuration Variables

| Variable | Setting | Purpose |
|----------|---------|---------|
| `SF_STRIPE_SECRET_KEY` | Required | Stripe secret API key |
| `SF_STRIPE_PUBLISHABLE_KEY` | Required | Stripe publishable key (frontend) |
| `SF_STRIPE_WEBHOOK_SECRET` | Required | Webhook signature verification |
| `SF_STRIPE_APP_DOMAIN` | `localhost:8000` | Base URL for redirect URLs |
| `SF_STRIPE_PORTAL_RETURN_URL` | `{APP_DOMAIN}/dashboard/billing` | Portal return URL |
| `SF_STRIPE_SUCCESS_URL` | `{APP_DOMAIN}/dashboard/billing?checkout=success` | Checkout success URL |
| `SF_STRIPE_CANCEL_URL` | `{APP_DOMAIN}/dashboard/billing?checkout=canceled` | Checkout cancel URL |
| `SF_STRIPE_TAX_ENABLED` | `False` | **Tax collection is DISABLED — checkouts will fail!** |
| `SF_BASE_CURRENCY` | `USD` | Base currency for exchange rates |
| `SF_EXCHANGE_RATE_API_URL` | `open.er-api.com/v6/latest` | Exchange rate data source |
| `SF_TOS_VERSION` | `1.0` | Current Terms of Service version |
