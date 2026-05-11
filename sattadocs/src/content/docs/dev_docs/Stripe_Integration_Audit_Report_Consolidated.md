---
title: Stripe Integration Audit Report Consolidated
description: Sattabase (Multi-Tenant SaaS Billing Platform)
---

# Sattabase — Stripe Integration Audit Report (Consolidated)
...

> **All-in-one audit report combining 3 separate reviews**
> Project: Sattabase (Multi-Tenant SaaS Billing Platform)
> Repository: `sattaspace/sattabase` (GitHub)
> Backend: Django 5.2 + Django Ninja + Daphne (ASGI)
> Frontend: Astro.js 6 + Vue 3 + Tailwind CSS 4
> Billing: Stripe Checkout + Customer Portal + Webhooks

---

## Source Reports

This consolidated report merges three independent Stripe integration audits into a single reference document:

| # | Report | Date | Findings | Focus |
|---|--------|------|----------|-------|
| 1 | Comprehensive Audit (Markdown) | 2026-04-28 | 27 (4 CR, 8 HI, 10 MD, 5 LO) | UX Expert, Finance & Accounting, Financial Compliance |
| 2 | Deep Code Audit (PDF) | 2026-05-xx | 86 (12 CR, 22 HI, 32 MD, 20 LO) | Full codebase line-by-line review (44 backend + 11 frontend files) |
| 3 | Solution Guide Audit (DOCX) v2.0 | 2026-04-28 | 20 (2 CR, 3 HI, 4 MD, 2 LO, 2 INFO) | Actionable solutions with code examples + effort estimates |

---

# PART 1: Solution Guide Audit (v2.0) — With Implementation Steps

> **20 findings with concrete code fixes, Dashboard configuration steps, and effort estimates**

## 1. Executive Summary

This report presents a comprehensive audit of the Stripe payment integration within the Sattabase billing platform, a central multi-tenant subscription management system developed with Django Ninja backend and AstroJS+Vue frontend. The audit was conducted from a financial compliance, legal, and user experience perspective, evaluating the system against industry best practices for SaaS billing platforms. Unlike the initial audit (v1), this version includes a detailed Solution Guide with step-by-step implementation instructions for every finding.

The Sattabase platform uses Stripe Checkout for payment collection and Stripe Customer Portal for self-service billing management. Webhooks drive the ongoing subscription lifecycle synchronization between Stripe and the local database. The system currently manages multiple products with tiered plans supporting monthly billing cycles with configurable trial periods. The dual-path activation architecture (confirm endpoint primary, webhook fallback) demonstrates solid engineering fundamentals.

The audit evaluated 20 specific areas across PCI-DSS compliance, tax and invoicing, data privacy, subscription lifecycle management, webhook reliability, user experience, and legal requirements. Of the 20 findings, 7 passed without issues, 2 were rated Critical, 3 High, 4 Medium, 2 Low, and 2 Informational.

## 2. Findings Summary Table

| # | Finding | Severity | Status & Risk | Solution Summary |
|---|---------|----------|---------------|-----------------|
| 1 | PCI-DSS: No Card Data | Pass | Stripe Checkout + Portal fully outsources card handling. SAQ-A eligible. | No action needed. |
| 2 | Webhook Signature Verification | Pass | All webhooks verified via construct_event() with per-endpoint secret. | No action needed. |
| 3 | Checkout Session Validation | Pass | confirm_checkout_session() verifies user_id metadata match. | No action needed. |
| 4 | Idempotent Webhook Processing | Pass | WebhookEventLog uses unique event_id constraint with get_or_create. | No action needed. |
| 5 | Trial Abuse Prevention | Pass | has_used_trial prevents repeated trial exploitation. | No action needed. |
| 6 | Rate Limiting on Checkout | Pass | check_rate_limit_or_raise() prevents automated abuse. | No action needed. |
| 7 | Webhook Audit Trail | Pass | All events logged with full JSON payload and processing status. | No action needed. |
| 8 | Tax Calculation / Invoicing | Critical | No tax calculation applied. Stripe Tax not configured. No automatic invoicing enabled. | Enable Stripe Tax + automatic_tax + invoice config. |
| 9 | Refund Policy | High | No refund functionality exists. No endpoint, no API calls, no policy displayed. | Create Refund model + stripe.Refund.create() + admin action. |
| 10 | Payment Failure Recovery | High | Payment failed only sets PAST_DUE. No notification, no retry, no grace period. | Enable Smart Retries + dunning notification + Fix Payment button. |
| 11 | No Test Coverage | High | Zero test files for billing app. Changes could silently break payment flow. | Create test_stripe_service.py (8+ tests) + test_controllers.py (5+ tests). |
| 12 | GDPR / Right to Erasure | Medium | No Stripe Customer cleanup on account deletion. PII remains. | Add account deletion hook to delete/anonymize Stripe Customer. |
| 13 | Terms of Service at Checkout | Medium | No TOS or subscription agreement presented during checkout. | Add tos_accepted_at + consent checkbox + consent_collection. |
| 14 | Proration Preview | Medium | Users cannot see proration cost before confirming plan change. | Add get_proration_preview() + preview endpoint + confirmation modal. |
| 15 | Cancellation Email | Medium | No confirmation email sent on cancel. | Enable Stripe built-in emails in Dashboard (zero code, 2 min). |
| 16 | DB Locking for Webhooks | Medium | No select_for_update(). Concurrent webhooks could race on same row. | Wrap in transaction.atomic() + select_for_update(). |
| 17 | Migration Files Missing | Medium | billing/migrations/ only has __init__.py. | Run makemigrations + migrate. |
| 18 | Currency Symbol Hardcoding | Low | Plan.display_price hardcodes $ regardless of currency field. | Replace with currency-aware symbol lookup. |
| 19 | Webhook Timeout Protection | Low | No timeout on webhook processing. | Wrap in asyncio.wait_for() with 15s timeout. |

## 3. Critical Findings — Solution Guide

### 3.1 C1: Tax Calculation (Critical)

**Problem**: No tax calculation is applied to subscription charges. Prices are displayed and charged as flat amounts without any tax component. This creates immediate legal compliance issues in virtually all jurisdictions: Bangladesh requires 15% VAT, the EU requires 15-27% VAT, India requires GST, US requires state/local sales tax. Operating without tax calculation exposes Sattabase to liability for uncollected tax amounts and potential fines.

**Solution**:

**Step 1**: Enable Stripe Tax in Dashboard. Navigate to Stripe Dashboard > Settings > Tax. Click 'Activate automatic tax'. Enter business details including registration numbers (VAT, GST) for each jurisdiction. Select 'Automatic' tax calculation mode.

**Step 2**: Add `automatic_tax` to checkout session creation:

```python
# In billing/stripe_service.py - create_checkout_session()
session = stripe.checkout.Session.create(
    api_key=api_key,
    mode="subscription",
    customer=customer_id,
    line_items=[{"price": price_id, "quantity": 1}],
    success_url=success_url,
    cancel_url=cancel_url,
    automatic_tax={"enabled": True},  # <-- ADD THIS
    ...
)
```

**Step 3** (Optional): Add `tax_inclusive` field to Plan model for per-plan tax behavior control.

**Files to modify**: `billing/stripe_service.py`, `billing/models.py` (optional). **Effort**: ~1 hour.

### 3.2 C2: Automatic Invoicing (Critical)

**Problem**: No invoice PDF generation or delivery mechanism exists. EU Directive 2006/112/EC requires sequential invoice numbers, business address, and tax identification numbers on every invoice for B2B transactions.

**Solution**:

**Step 1**: Configure Stripe invoicing in Dashboard. Navigate to Dashboard > Settings > Billing. Set custom invoice prefix (e.g., `SATTABASE-{YEAR}-{SEQ}`). Add business name, address, tax ID, support email. Enable 'Send invoice PDF via email'.

**Step 2**: Enhance webhook handlers to log invoice details:

```python
# In _handle_invoice_payment_succeeded and _handle_invoice_payment_failed
invoice_number = invoice.get("number")
hosted_url = invoice.get("hosted_invoice_url")
logger.info(f"Invoice {invoice_number}: {hosted_url}")
```

**Effort**: ~1 hour (mostly Dashboard configuration).

## 4. High Priority Findings — Solution Guide

### 4.1 H1: Refund Mechanism (High)

**Problem**: No refund functionality exists. No Refund model, no admin action, no API endpoint, no refund policy displayed.

**Solution**:

**Step 1**: Create Refund model:

```python
class Refund(TimeStampedModel):
    id = models.BigAutoField(primary_key=True)
    subscription = models.ForeignKey(Subscription, CASCADE, related_name="refunds")
    stripe_refund_id = models.CharField(max_length=100, unique=True, blank=True)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="USD")
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, default="pending")
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, CASCADE, null=True)
```

**Step 2**: Add `create_stripe_refund()`:

```python
def create_stripe_refund(subscription, amount_cents=None, reason=""):
    stripe_sub = stripe.Subscription.retrieve(
        subscription.stripe_subscription_id, api_key=_get_stripe_api_key())
    latest_invoice = stripe.Invoice.retrieve(
        stripe_sub.latest_invoice, api_key=_get_stripe_api_key())
    refund = stripe.Refund.create(
        payment_intent=latest_invoice.payment_intent,
        amount=amount_cents,  # None = full refund
        reason="requested_by_customer",
        metadata={"subscription_id": str(subscription.id)})
    return refund
```

**Step 3**: Add admin action and `POST /billing/admin/subscriptions/{id}/refund` endpoint. **Effort**: ~2-3 hours.

### 4.2 H2: Payment Failure Recovery / Dunning (High)

**Problem**: When `invoice.payment_failed` fires, subscription is marked `PAST_DUE` but the user receives no notification.

**Solution**:

**Step 1**: Enable Stripe Smart Retries (zero code, 5 min). Navigate to Dashboard > Settings > Billing > Smart Retries.

**Step 2**: Enhance `_handle_invoice_payment_failed`:

```python
def _handle_invoice_payment_failed(event):
    # ... existing status update code ...
    attempt = invoice.get("attempt_count", 1)
    next_retry = _ts_to_datetime(invoice.get("next_payment_attempt"))
    logger.warning(
        f"Payment failed attempt {attempt} for sub={sub.id}. "
        f"Next retry: {next_retry}. User must update payment method.")
```

**Step 3**: Add "Fix Payment" button in BillingOverview.vue when status is PAST_DUE. **Effort**: ~2 hours.

### 4.3 H3: Test Coverage (High)

**Problem**: Zero test files exist for the billing application.

**Solution**: Create comprehensive test suite:

- `billing/tests/test_stripe_service.py` — 8+ tests (create product/price, confirm checkout, webhook duplicate, trial abuse prevention)
- `billing/tests/test_controllers.py` — 5+ tests (create checkout, confirm checkout, plan change, cancel subscription)

Use Stripe test cards: `4242424242424242` (success), `4000000000000002` (decline), `4000000000009995` (insufficient funds).

**Effort**: ~4-5 hours.

## 5. Medium Priority Findings — Solution Guide

### 5.1 M1: GDPR / Right to Erasure

Add a cleanup hook in the user account deletion flow:

```python
def cleanup_stripe_customer(user):
    sub = Subscription.objects.filter(user=user).exclude(stripe_customer_id="").first()
    if not sub or not sub.stripe_customer_id:
        return
    api_key = _get_stripe_api_key()
    has_active = Subscription.objects.filter(
        user=user, status__in=["active","trialing","past_due"]).exists()
    if has_active:
        stripe.Customer.modify(sub.stripe_customer_id,
            email=f"deleted_{user.id}@redacted.com",
            name="Deleted User", api_key=api_key)
    else:
        try:
            stripe.Customer.del(sub.stripe_customer_id, api_key=api_key)
        except stripe.InvalidRequestError:
            pass
```

**Effort**: ~1 hour.

### 5.2 M2: Terms of Service at Checkout

(1) Add `tos_accepted_at` and `tos_version` to Subscription model. (2) Add required 'I agree to TOS' checkbox in PlanComparison.vue. (3) Use Stripe's `consent_collection={'terms_of_service': 'required'}`. **Effort**: ~1 hour.

### 5.3 M3: Proration Preview

```python
def get_proration_preview(subscription, new_plan):
    price_id = ensure_stripe_product_and_price(new_plan)
    stripe_sub = stripe.Subscription.retrieve(
        subscription.stripe_subscription_id, api_key=_get_stripe_api_key())
    items = stripe_sub.get("items", {}).get("data", [])
    preview = stripe.Subscription.retrieve_upcoming(
        customer=subscription.stripe_customer_id,
        subscription=subscription.stripe_subscription_id,
        subscription_items=[{"id": items[0].id, "price": price_id}])
    return {
        "subtotal": preview.get("subtotal_excluding_tax", 0) / 100,
        "tax": preview.get("tax", 0) / 100,
        "total": preview.get("total", 0) / 100
    }
```

**Effort**: ~2 hours.

### 5.4 M4: Cancellation Confirmation Email

Navigate to Dashboard > Settings > Email. Enable all five email templates (payment confirmation, trial ending, payment failed, cancellation, invoice receipt). **Effort**: 2 minutes (zero code).

### 5.5 M5: Database Locking for Concurrent Webhooks

```python
from django.db import transaction

def _handle_subscription_updated(event):
    stripe_sub = event["data"]["object"]
    stripe_sub_id = stripe_sub["id"]
    with transaction.atomic():
        sub = (Subscription.objects
               .select_for_update()
               .select_related("plan", "plan__product")
               .get(stripe_subscription_id=stripe_sub_id))
        # ... update fields ...
        sub.save()
```

Apply the same pattern to all webhook handlers. **Effort**: ~1 hour.

### 5.6 M6: Migration Files Missing

```bash
cd backend
python manage.py makemigrations billing
python manage.py migrate
```

**Effort**: 5 minutes.

## 6. Low Priority Findings — Solution Guide

### 6.1 L1: Currency Symbol Hardcoding

```python
@property
def display_price(self) -> str:
    if self.price_cents == 0:
        return str(_("Free"))
    amount = self.price_cents / 100
    symbols = {"USD": "$", "EUR": "EUR", "GBP": "GBP", "BDT": "BDT", "INR": "INR"}
    symbol = symbols.get(self.currency.upper(), f"{self.currency} ")
    cycle_labels = {BillingCycle.MONTHLY: "/mo", BillingCycle.YEARLY: "/yr", BillingCycle.LIFETIME: ""}
    cycle = cycle_labels.get(self.billing_cycle, "")
    return f"{symbol}{amount:.2f}{cycle}"
```

**Effort**: ~30 minutes.

### 6.2 L2: Webhook Timeout Protection

```python
import asyncio

async def stripe_webhook(self, request):
    # ... verification code ...
    try:
        await asyncio.wait_for(
            sync_to_async(process_webhook_event)(event),
            timeout=15.0)
    except asyncio.TimeoutError:
        logger.warning(f"Webhook {event['type']} timed out")
    return MessageResponse(message="Webhook processed.")
```

**Effort**: ~1 hour.

## 7. Implementation Roadmap

| Phase | Timeline | Effort | Items |
|-------|----------|--------|-------|
| Phase 1 | Today | 15 min, zero code | Enable Stripe email templates, Smart Retries, run migrations |
| Phase 2 | This week | ~2 hours | Enable Stripe Tax, configure invoicing, fix currency symbol |
| Phase 3 | Next sprint | ~8-10 hours | Dunning flow, TOS tracking, proration preview, DB locking, GDPR hook, portal config |
| Phase 4 | Following sprint | ~4-6 hours | Refund mechanism, test coverage, webhook timeout, custom emails |

**Total estimated effort**: ~15-19 hours across four phases.

---

# PART 2: Comprehensive Audit — UX, Finance & Compliance

> **27 findings across three expert perspectives**

## 8. Audit Perspective 1 — User Experience Expert

### UX-01 CRITICAL — No Dunning Email Notifications

**File**: `backend/billing/tasks.py` (lines 118-147)

**Problem**: The `dunning_retry` Celery task detects past-due subscriptions older than 7 days but only logs a warning. The comment says `# Future: Send dunning email here` — this is never implemented. Users whose cards fail get zero communication from the system. They only discover the problem when they lose access.

**Impact**: Users lose service unexpectedly without warning. This is the number-one cause of involuntary churn in SaaS.

**Solution**: Send emails at 3-day, 5-day, and 7-day marks with increasingly urgent language. Add `last_dunning_email_at` to the Subscription model to prevent duplicate emails.

### UX-02 HIGH — No Cancellation Confirmation Flow

**File**: `frontend/src/components/vue/BillingOverview.vue` (lines 128-148)

**Problem**: Cancel confirmation uses only a toast with "Yes, cancel" — no full modal explaining consequences (exact date access ends, features lost, save-the-deal offer, feedback form).

**Solution**: Build `CancelSubscriptionModal.vue` with feature comparison, "Pause instead" option, and feedback form.

### UX-03 HIGH — Currency Mismatch Error Is Hard to Recover From

**File**: `backend/billing/controllers.py` (lines 699-710)

**Problem**: When a user hits currency mismatch, error says "change your currency preference" but there is no UI to do this. The user is stuck.

**Solution**: Add currency selector dropdown on billing overview page. When API returns currency mismatch error, show prominent banner with auto-switch option.

### UX-04 HIGH — No Payment Method Change Feedback on Portal Return

**File**: `frontend/src/components/vue/BillingOverview.vue`

**Problem**: After returning from Stripe Portal, the page shows no feedback about what changed.

**Solution**: Add `?portal=success` parameter to return URL. Handle it like `checkout=success` with toast notification and re-fetch.

### UX-05 MEDIUM — Transaction History Requires Admin Endpoint

**File**: `frontend/src/lib/billing.ts` (line 267-281)

**Problem**: Transaction history fetched from `/billing/admin/transactions` — an admin-only endpoint. Regular users calling this get 403.

**Solution**: Create user-facing `GET /billing/subscriptions/transactions` under `BillingProtectedController`.

### UX-06 MEDIUM — No Loading State During Initial Checkout

**File**: `frontend/src/components/vue/PlanComparison.vue` (lines 225-269)

**Solution**: Add full-page overlay during Stripe redirect with spinner and "Redirecting to secure checkout..." text.

### UX-07 MEDIUM — No "Per-Seat" or "Usage" Display for Plans

**Solution**: Add semantic rendering to feature lists — numeric limit badges, infinity icons for unlimited, checkmarks for boolean true.

### UX-08 MEDIUM — No Webhook Timeout Fallback (UX Impact)

**File**: `backend/billing/stripe/webhooks/router.py` (lines 62-78)

**Problem**: `_timeout` context manager uses `signal.SIGALRM` which only works on Unix. On Windows or some containers, SIGALRM silently fails.

**Solution**: Replace with portable timeout using threading or Django's configurable worker timeout.

### UX-09 LOW — "Free Plan" Has No Upgrade CTA

**Solution**: Add highlighted "Upgrade" CTA button specifically for free-plan subscriptions.

### UX-10 LOW — Plan Comparison Doesn't Show Annual Savings

**Solution**: Calculate and display annual savings percentage when both monthly and yearly billing cycles are available.

## 9. Audit Perspective 2 — Finance & Accounting Expert

### FIN-01 CRITICAL — No Invoice Line Item Data Stored Locally

**File**: `backend/billing/stripe/webhooks/handlers/invoice.py` (lines 59-66)

**Problem**: `handle_invoice_created` only logs invoice number and amount. No `Invoice` model exists. Cannot generate itemized statements, tax reporting, or revenue recognition without calling Stripe API each time.

**Solution**: Create `Invoice` model with fields: `stripe_invoice_id`, `subscription` FK, `number`, `status`, `amount_paid_cents`, `amount_due_cents`, `tax_cents`, `currency`, `period_start/end`, `hosted_url`, `pdf_url`, `stripe_response`.

### FIN-02 CRITICAL — No Payment Retry Logic (Dunning Automation)

**File**: `backend/billing/tasks.py` (lines 99-147)

**Solution**: Build proper dunning workflow with 4-step escalation:

```python
DUNNING_STEPS = [
    {"days": 3, "action": "email_reminder"},
    {"days": 5, "action": "email_urgent"},
    {"days": 7, "action": "restrict_access"},
    {"days": 14, "action": "cancel_subscription"},
]
```

### FIN-03 HIGH — Refund Amount Not Validated Against Invoice

**Solution**: Add validation to ensure refund amount does not exceed charge amount. Support targeting specific charges via `charge_id` parameter.

### FIN-04 HIGH — No Prorated Credit Tracking

**Solution**: Create `PlanChangeLog` model to persist proration records for audit and reconciliation.

### FIN-05 HIGH — Exchange Rate Used for Display, Not for Billing

**Problem**: Free-tier exchange rate API (`open.er-api.com`) may drift from Stripe's rates. Users may be charged slightly differently than displayed.

**Solution**: Add disclaimer on frontend. Consider Stripe's multi-currency pricing. Store exchange rate at time of price creation in metadata.

### FIN-06 HIGH — Transaction History Schema Mismatch

**Problem**: Frontend `TransactionItemSchema` expects fields not returned by backend. UI renders empty/undefined values.

**Solution**: Expand backend `get_transaction_history()` to include all expected fields (tax, pdf_url, period, charge info, payment method).

### FIN-07 MEDIUM — No Revenue Recognition Support

**Solution**: Add `RevenueRecognitionEntry` model populated by Celery task for ASC 606 compliance.

### FIN-08 MEDIUM — Webhook Event Log Has No Cleanup Strategy

**Solution**: Add `cleanup_stale_webhook_events` Celery task with 90-day retention.

### FIN-09 LOW — No Stripe Fee Tracking

**Solution**: Fetch and store Stripe Balance Transaction fee amounts from webhook handlers.

## 10. Audit Perspective 3 — Financial Compliance Expert

### CMP-01 CRITICAL — No GDPR Data Export for Billing Data

**File**: `backend/billing/stripe/gdpr.py`

**Problem**: GDPR Article 20 (Right to Data Portability) requires users can export all personal data including billing history. No export endpoint exists.

**Solution**: Add `export_user_billing_data()` function and `GET /billing/export-data` endpoint.

### CMP-02 HIGH — No Audit Trail for Admin Refund Actions

**Solution**: Extend Refund model with `initiated_by_ip`, `approved_by`, `approved_at`, `reason_category`, `admin_notes` fields.

### CMP-03 HIGH — Webhook Signature Verification Returns Parsed JSON, Not Verified Object

**Solution**: Return `event.to_dict()` instead of manually re-parsing raw JSON.

### CMP-04 HIGH — Stripe API Key Logged on 401 Errors

**Solution**: Replace logging with active alert mechanism (email admins via `mail_admins()`).

### CMP-05 HIGH — No Webhook Endpoint Rate Limiting

**Solution**: Add IP-based rate limiting to webhook endpoint.

### CMP-06 MEDIUM — ToS Acceptance Not Version-Controlled Per Checkout

**Solution**: Add `tos_version` to checkout metadata and validate at confirmation time.

### CMP-07 MEDIUM — No Idempotency Key on Checkout Creation

**Solution**: Add local deduplication check for active checkout sessions in the last 5 minutes.

### CMP-08 MEDIUM — Customer Portal Configuration Is Minimal

**Solution**: Configure portal features, business info, and branding in Stripe Dashboard or via configuration parameter.

### CMP-09 LOW — No Access Logging for Billing Admin Endpoints

**Solution**: Add `@log_admin_access` decorator logging user_id, email, action, IP, path, timestamp.

## 11. Cross-Cutting Findings

### CC-01 MEDIUM — `handle_stripe_error` Returns String but Is Used Inconsistently

**Solution**: Make `handle_stripe_error` return `BadRequestException` directly.

### CC-02 MEDIUM — No Integration Tests for Stripe Flows

**Solution**: Create comprehensive test suite covering checkout, webhooks, plan changes, refunds, currency, GDPR.

### CC-03 MEDIUM — `currency_service.py` Uses Free API Without Fallback

**Solution**: Add fallback API, cache last known good rates, alert if rates are stale.

### CC-04 LOW — Stripe `to_dict()` Drops `None` Values

**Solution**: Handle `None` values explicitly when converting Stripe objects to dicts.

---

# PART 3: Deep Code Audit — Full Codebase Review

> **86 findings across 44 backend files (~9,330 lines Python) and 11 frontend files (~2,200 lines Vue/TS/Astro)**

## 12. Executive Summary

This report presents the findings of a comprehensive line-by-line audit of the Sattabase SaaS billing platform's Stripe integration. The audit scope is exclusively end-user focused: no admin dashboard features were evaluated.

### Findings Overview

| Severity | Count | Key Themes |
|----------|-------|-----------|
| CRITICAL | 12 | Missing auth guards, random subscription association, zero error handling in Stripe client, revenue recognition broken |
| HIGH | 22 | Race conditions, missing rate limits, swallowed exceptions, GDPR orphan data, stale exchange rates, broken imports |
| MEDIUM | 32 | Webhook reliability, schema validation gaps, logger bugs, dunning timer issues, currency formatting, missing PDF downloads |
| LOW | 20 | Code quality, minor UX polish, documentation, hardcoded strings, style inconsistencies |

## 13. Critical Findings (12)

### 13.1 Backend Security

#### CTR-01: Missing is_staff Guard on Admin Endpoints

**File**: `controllers.py:1242, 1273`

Two admin endpoints (`get_transactions` and `sync_customer`) have no `is_staff` guard. Any authenticated user can call `POST /billing/admin/transactions` and `POST /billing/admin/sync-customer`.

**Recommendation**: Add `is_staff` guard to ALL methods in `BillingAdminController`, or create an `IsStaff` permission class at controller level.

#### CTR-02: Admin Refund Broken — Filters by Admin's Own User

**File**: `controllers.py:1190-1194`

Admin `refund_subscription` calls `aget_subscription_for_product(request.user, product_slug)` which filters by the requesting admin's user, not the target user. Admins cannot refund any user's subscription except their own.

**Recommendation**: Add `target_user_id` or `target_email` field. Query subscription for the target user.

### 13.2 Financial / Compliance

#### CRIT-01: Missing Celery Beat Entries for Revenue + Cleanup Tasks

**File**: `celery.py` `beat_schedule`

Two of six defined Celery tasks (`recognize_revenue` and `cleanup_stale_webhook_events`) are completely absent from `beat_schedule`. Only 4 of 6 tasks are scheduled.

**Impact**: Revenue recognition never runs automatically. Financial reporting is fundamentally broken. Webhook event logs grow unboundedly.

#### CRIT-02: Negative Revenue Recognition Calculation

**File**: `tasks.py:511-517`

Revenue recognition uses `math.ceil(price_cents / total_days)` for non-last days, then adjusts last day as `price_cents - (daily_cents * (total_days - 1))`. When `ceil * (total_days-1) > price_cents`, the last day becomes negative.

**Recommendation**: Use proper remainder distribution: `base_daily = price // days`, `remainder = price % days`. First `remainder` days get `base+1`, rest get `base`.

#### CH-01: Random Subscription Association in Refund Webhook Handler

**File**: `webhooks/handlers/charge.py:32`

The `charge.refunded` handler does `Subscription.objects.filter(stripe_subscription_id__isnull=False).first()` which returns an arbitrary subscription from the entire database.

**Impact**: Refund records associated with wrong subscriptions in multi-tenant environment.

#### CTR-09: Admin Refund Schema Validation Bypassed

**File**: `controllers.py:1176`

Admin refund endpoint accepts `payload: dict` instead of `payload: RefundInputSchema`. Ninja's automatic validation is completely bypassed.

### 13.3 Backend Reliability

#### STP-01: Zero Error Handling in Stripe Client

**File**: `stripe/client.py` (all 15 functions)

None of the 15 functions that call the Stripe SDK catch any `stripe.error.*` exceptions or network errors. Every transient Stripe outage propagates uncaught.

**Recommendation**: Wrap every Stripe SDK call in `try/except stripe.error.StripeError`. Distinguish `RateLimitError` (retry), `CardError` (surface to user), `APIConnectionError` (transient).

#### STP-02: Stripe Import Outside client.py

**File**: `stripe/__init__.py:53, 237`

The `__init__.py` directly imports `stripe` and calls `stripe.Charge.retrieve()`, bypassing `client.py` which is supposed to be the ONLY module that imports `stripe`.

#### IN-01: Double-Save Race Condition in Invoice Handler

**File**: `webhooks/handlers/invoice.py:184, 188`

`handle_invoice_payment_failed` saves subscription twice — once for `status=PAST_DUE`, then for `dunning_step=0`. Between saves, concurrent webhook could cause data loss.

#### IN-02: Type Confusion in Fee Extraction

**File**: `webhooks/handlers/invoice.py:104-115`

Fee extraction code mixes `dict.get()` and attribute access on what could be either StripeObject or dict. Works by accident but fragile.

### 13.4 Frontend Security

#### SEC-01: Missing rel="noopener noreferrer" on External Links

**Files**: `BillingOverview.vue:697`, `PlanComparison.vue:323`, `Navbar.astro:133-145`, `index.astro:100-104`

Every `target="_blank"` link lacks `rel="noopener noreferrer"`, exposing the site to reverse tabnabbing.

#### HIGH-03: Stripe Keys Have No Startup Validation

**File**: `settings.py:396-398`

All three Stripe keys default to empty string. No startup validation. Empty `STRIPE_WEBHOOK_SECRET` means signatures are not verified.

## 14. High Severity Findings (22)

### 14.1 Backend Issues

| ID | Finding | Location |
|----|---------|----------|
| CTR-04 | Plan change preview token has no tolerance for 1-cent drift | controllers.py:977-1002 |
| CTR-05 | confirm_checkout has no rate limiting | controllers.py:808-829 |
| CTR-06 | Five mutation endpoints have no rate limiting | controllers.py:401,449,492,871,841 |
| CTR-10 | confirm_checkout skips email verification check | controllers.py:808 |
| SVC-01 | Race condition in aget_or_create_free_subscription | services.py:268-297 |
| SVC-02 | GET auth/me creates subscriptions as side effect | services.py:502, 553 |
| CTR-08 | list_subscriptions returns no pagination | controllers.py:327-359 |
| CL-01 | list_prices() uses auto_paging_iter() with no upper bound | stripe/client.py:137 |
| CK-01 | confirm_checkout swallows ALL exceptions | stripe/checkout.py:164-166 |
| PT-01 | create_portal accepts arbitrary return_url | stripe/portal.py:13 |
| GD-01 | GDPR anonymization leaves stripe_subscription_id intact | stripe/gdpr.py:57 |
| PR-01 | No locking between list_prices() and create_price() | stripe/prices.py:115-154 |
| IN-03 | Percentage-based discounts explicitly skipped | webhooks/handlers/invoice.py:26-30 |
| STP-03 | Refund idempotency key includes timestamp (defeats purpose) | stripe/__init__.py:267-269 |
| STP-04 | Plan change idempotency key includes timestamp | stripe/__init__.py:557-559 |
| HIGH-01 | Dunning cancel step catches ALL exceptions | tasks.py:172-193 |
| HIGH-02 | Dunning step advanced even when email fails | tasks.py:154-155 |
| HIGH-04 | ExchangeRate.fetched_at frozen after first insert | models.py:841-844 |

### 14.2 Frontend Issues

| ID | Finding | Location |
|----|---------|----------|
| SEC-02 | Cancel reason dropdown value is ignored | BillingOverview.vue:753 |
| UX-01 | loadTransactions() never called on mount | BillingOverview.vue:239-251 |
| UX-04 | No error state or retry button on initial fetch failure | BillingOverview.vue:122-147 |
| NAV-01 | Sidebar Plans link hardcoded to /finance slug | Sidebar.astro:25 |

## 15. Medium Severity Findings (32) — Selected Highlights

### Backend

| ID | Finding | Location |
|----|---------|----------|
| CTR-12 | Checkout reactivation catches StripeError generically | controllers.py:727 |
| CTR-13 | reactivate doesn't check if period has expired | controllers.py:466 |
| SVC-03 | Plan change log records same old/new plan | services.py:349-370 |
| MED-04 | Dunning days_past_due uses auto_now updated_at | tasks.py:323 |
| MED-05 | Revenue recognition includes PAST_DUE status | tasks.py:468-474 |
| MED-02 | get_client_ip trusts X-Forwarded-For unconditionally | rate_limit.py:98-102 |

### Frontend

| ID | Finding | Location |
|----|---------|----------|
| UX-03 | activeSubscriptions filter vs stats.activeCount mismatch | BillingOverview.vue:47-49 |
| UX-13 | formatPrice uses hardcoded en-US locale | billing.ts:353 |
| UX-14 | pdf_url field exists but never used in template | BillingOverview.vue:694-702 |
| NAV-04 | No public-facing pricing page | index.astro:69 |
| UX-07 | Downgrade uses toast but cancel uses modal | PlanComparison.vue:202-211 |
| A11Y-01 | Modals lack focus trap, ARIA, Escape handler | BillingOverview.vue:709-781 |
| SEC-03 | JWT tokens in localStorage (XSS risk) | api.ts:36-38 |

## 16. Positive Observations

1. **Stripe-first architecture** — All subscription mutations call Stripe first, then update local DB.
2. **PCI compliance** — No card data stored locally. SAQ-A eligible.
3. **Webhook signature verification** — Proper `construct_event()` usage.
4. **Idempotent webhook processing** — `get_or_create` with `event_id` as natural key.
5. **Safe plan change flow** — Preview-token-confirm with HMAC binding.
6. **Checkout deduplication** — Cache-based double-click prevention.
7. **Webhook reconciliation** — `reconcile_unprocessed` Celery task.
8. **Audit trail** — PlanChangeLog with from/to plan, proration, initiated_by, IP.
9. **GDPR foundation** — Data export and anonymization endpoints exist.
10. **Secret handling** — No hardcoded API keys. All from environment variables.

## 17. Priority Remediation Roadmap

### 17.1 Immediate (This Week) — P0

| Finding | Action |
|---------|--------|
| CTR-01/03 | Add is_staff guard to ALL admin controller methods |
| CTR-02 | Redesign admin refund to accept target user parameter |
| HIGH-03 | Add Stripe key startup validation in AppConfig.ready() |
| SEC-01 | Add rel="noopener noreferrer" to all target="_blank" links |
| CRIT-01 | Add missing Celery beat entries for revenue + cleanup |
| CRIT-02 | Fix negative revenue calculation with remainder distribution |
| CH-01 | Fix random subscription association in refund webhook handler |

### 17.2 This Sprint — P1

| Finding | Action |
|---------|--------|
| STP-01 | Add error handling to all client.py Stripe API calls |
| CTR-05/06 | Add rate limiting to all unrate-limited mutation endpoints |
| CTR-09/10 | Fix admin refund schema + email verification on confirm |
| SVC-01 | Fix race condition in aget_or_create_free_subscription |
| STP-03/04 | Fix broken idempotency keys in refund and plan change |
| HIGH-01/02 | Fix dunning step advancement logic |
| HIGH-04 | Fix ExchangeRate.fetched_at auto_now_add to auto_now |
| IN-01/02 | Fix double-save race + type confusion in webhook handlers |
| UX-01/SEC-02 | Auto-load transactions + fix cancel reason not sent |
| UX-04/NAV-01 | Add error state with retry + fix hardcoded finance slug |

### 17.3 Next Sprint — P2

| Finding | Action |
|---------|--------|
| SVC-02 | Remove auto-creation from auth/me GET endpoint |
| GD-01 | Clear stripe_subscription_id during GDPR anonymization |
| PT-01 | Validate return_url against ALLOWED_HOSTS in create_portal |
| PR-01 | Add locking or idempotency key to resolve_price_id |
| MED-04/05 | Fix dunning timer + remove PAST_DUE from revenue recognition |
| UX-13/14 | Fix locale-aware pricing + add PDF download for invoices |
| NAV-04 | Create public pricing page |
| A11Y-01 | Add ARIA attributes, focus trap, Escape handler to modals |
