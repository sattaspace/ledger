---
title: Stripe Dashboard Implementation Required
description: A reference page in my new Starlight docs site.
---

# Stripe Dashboard Implementation Required

> **This document lists all manual configuration steps required in the Stripe Dashboard.**
> Code changes have been implemented in the backend. Complete these steps before going to production.

## What YOU Must Do (Master Checklist)

Use this checklist to track your Stripe Dashboard setup progress:

### 1. Tax Configuration (C1)
- [ ] Go to **Stripe Dashboard → Tax** and click **"Activate Stripe Tax"**
- [ ] Register tax registrations (EU VAT / Indian GSTIN / US nexus)
- [ ] Set `STRIPE_TAX_ENABLED=True` in your `.env` file (blocks checkout until enabled — F6)
- [ ] Verify: Create a test checkout with a customer from a different country — confirm tax is calculated

### 2. Invoicing & Business Details (C2)
- [ ] Go to **Settings → Billing → Invoices** and set invoice number prefix
- [ ] Add business legal name, registered address, tax ID, support email
- [ ] Enable "Attach PDF to invoice emails"
- [ ] Verify: Complete a test payment — check that an invoice PDF is generated and emailed

### 3. Email Notifications (C2/M4)
- [ ] Go to **Settings → Emails** and enable ALL of these:
  - [ ] Payment confirmation (successful payment)
  - [ ] Subscription trial will end (3 days before)
  - [ ] Payment failed (charge decline + retry reminders)
  - [ ] Subscription canceled
  - [ ] Invoice receipt (with PDF)
- [ ] Verify: Trigger each event type — confirm emails are received

### 4. Smart Retries (H2)
- [ ] Go to **Settings → Billing → Subscriptions** and enable **Smart Retries**
- [ ] Configure: retry immediately (on), max 4 attempts, schedule: 1d, 3d, 5d, 7d
- [ ] Verify: Use Stripe test card `4000 0000 0000 0002` (decline) — confirm retry emails sent

### 5. Webhook Endpoint (CRITICAL)
- [ ] Go to **Developers → Webhooks** and add endpoint:
  `https://yourdomain.com/api/v1/billing/webhooks/stripe`
- [ ] Listen for ALL of these events (updated with F2, F8, F9):
  - [ ] `checkout.session.completed`
  - [ ] `customer.subscription.created`
  - [ ] `customer.subscription.updated`
  - [ ] `customer.subscription.deleted`
  - [ ] `customer.subscription.trial_will_end`
  - [ ] `invoice.payment_succeeded`
  - [ ] `invoice.payment_failed`
  - [ ] `invoice.created` (F9 — audit trail)
  - [ ] `charge.refunded` (F2 — refund audit trail)
  - [ ] `customer.updated` (F8/F9 — profile sync)
- [ ] Copy the **Signing secret** (`whsec_...`) to `SF_STRIPE_WEBHOOK_SECRET` in `.env`

### 6. Customer Portal Customization (MEDIUM)
- [ ] Go to **Settings → Billing → Customer portal**
- [ ] Set business name, logo, allowed features (cancel, update payment, download invoices)
- [ ] Verify: Log in as test customer — confirm portal shows subscription, invoices, payment method update

### 7. Refund Configuration (F1/F3)
- [ ] Refunds are now **admin-only** via `/billing/admin/subscriptions/{slug}/refund`
- [ ] Regular users cannot refund — they must contact support
- [ ] All refunds include **idempotency keys** (F3) to prevent double-refund on retries
- [ ] `charge.refunded` webhook (F2) captures refunds initiated from Stripe Dashboard
- [ ] Verify: Initiate a test refund from Django admin — confirm Refund record created and Stripe refund processed

### 8. Environment Variables (PRODUCTION)
- [ ] Set these in your `.env` file:

```env
# Stripe Core
SF_STRIPE_SECRET_KEY=sk_live_...
SF_STRIPE_PUBLISHABLE_KEY=pk_live_...
SF_STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Integration
SF_STRIPE_APP_DOMAIN=https://yourdomain.com
STRIPE_SUCCESS_URL=https://yourdomain.com/dashboard/billing?success=true
STRIPE_CANCEL_URL=https://yourdomain.com/dashboard/billing
STRIPE_PORTAL_RETURN_URL=https://yourdomain.com/dashboard/billing

# Tax (F6 — REQUIRED, blocks checkout if missing)
STRIPE_TAX_ENABLED=True

# Terms of Service (F7 — read by checkout, not hardcoded)
TOS_VERSION=1.0
```

### 9. Celery Beat Scheduler (F5/F8/F10)
- [ ] Ensure Celery worker + beat are running in production
- [ ] Beat schedule includes:
  - `reconcile_webhooks` — every 6 hours (retries failed webhooks)
  - `sync_customer_data` — daily at 3:30 AM UTC (syncs Stripe customer profiles)
  - `dunning_retry` — daily at 4:00 AM UTC (logs past_due subscriptions > 7 days)
- [ ] Verify: Check Celery worker logs for task execution

### 10. Database Migration (F12)
- [ ] Run `python manage.py migrate billing` to apply the `currency` field on Subscription
- [ ] The field is nullable/blank-safe — existing subscriptions get empty string (fallback to plan.currency)

---

## Detailed Configuration Sections

## C1: Enable Stripe Tax (CRITICAL)

Stripe Tax is required for legal compliance in most jurisdictions (EU VAT, Indian GST, US sales tax).

### Steps:
1. Go to **Stripe Dashboard → Tax** (https://dashboard.stripe.com/settings/tax)
2. Click **"Activate Stripe Tax"**
3. Register your tax registrations:
   - **EU**: Add your VAT number (e.g., `DE123456789`) — Stripe will auto-calculate VAT based on customer location
   - **India**: Add your GSTIN (e.g., `29AABCU9603R1ZM`) — Stripe handles IGST/CGST/SGST split
   - **US**: Enable "Automated tax calculation" — Stripe determines nexus based on state
4. Configure tax settings:
   - **Default tax behavior**: `exclusive` (tax added on top) — this is the most common for B2C SaaS
   - For tax-inclusive pricing (B2B, some markets): Set `tax_inclusive = True` on individual Plans in Django Admin

### Code Support:
- `create_checkout_session()` now passes `automatic_tax={'enabled': True}`
- `Plan.tax_inclusive` field controls `tax_behavior='inclusive'` vs `'exclusive'` per plan
- `consent_collection={'terms_of_service': 'required'}` is enabled at checkout
- **F6 Guard**: Checkout is BLOCKED until `STRIPE_TAX_ENABLED=True` is set in `.env`

---

## C2: Configure Customer Invoicing (CRITICAL)

EU Directive 2006/112/EC requires sequential invoice numbers, business address, tax ID.

### Steps:
1. Go to **Stripe Dashboard → Settings → Billing → Invoices** (https://dashboard.stripe.com/settings/billing/invoice)
2. Set **Invoice number prefix**: `SATTABASE-{YEAR}-{SEQ}` (or your preferred format)
3. Add **Business details**:
   - Business legal name
   - Registered address (street, city, country, postal code)
   - Tax ID / VAT number
   - Support email (shown on invoices)
4. Configure **Invoice PDF settings**:
   - Enable "Attach PDF to invoice emails"
   - Customize invoice template (logo, colors, footer text) if desired

### Code Support:
- `_handle_invoice_payment_succeeded` logs `invoice.number` and `invoice.hosted_invoice_url`
- `_handle_invoice_payment_failed` logs attempt count, next retry date, invoice URL
- `_handle_invoice_created` (F9) logs every new invoice for complete audit trail
- Stripe auto-generates invoices for subscriptions — no additional code needed

---

## H2: Enable Smart Retries (HIGH)

Smart Retries is a FREE Stripe feature that automatically reschedules failed payment attempts with decreasing frequency. Without this, Stripe's default retry behavior is suboptimal.

### Steps:
1. Go to **Stripe Dashboard → Settings → Billing → Subscriptions** (https://dashboard.stripe.com/settings/billing/subscriptions)
2. Under **"Smart Retries"**, click **"Enable"**
3. Configure retry schedule (recommended defaults):
   - **Retry immediately**: On (first retry within 1 hour)
   - **Maximum retry attempts**: 4
   - **Retry every**: 1 day, 3 days, 5 days, 7 days
4. This handles the entire dunning flow automatically — Stripe sends payment failure emails and retries on your behalf

### Code Support:
- `_handle_invoice_payment_failed` logs `attempt_count` and `next_payment_attempt` for debugging
- Frontend shows PAST_DUE banner with "Update Payment Method" button → redirects to Stripe Portal
- Celery Beat `dunning_retry` task logs subscriptions past_due > 7 days for manual review

---

## M4: Enable Built-in Email Notifications (MEDIUM — Already covered in C2)

All customer-facing email notifications are handled by Stripe's built-in email system (configured in C2 above). These require ZERO code changes:

| Event | Email | Status |
|-------|-------|--------|
| Successful payment | Payment confirmation | ✅ Enable in Dashboard |
| Trial ending (3 days) | Trial will end warning | ✅ Enable in Dashboard |
| Payment failed | Payment failure + retry reminder | ✅ Enable in Dashboard |
| Subscription canceled | Cancellation confirmation | ✅ Enable in Dashboard |
| Invoice created | Invoice receipt with PDF | ✅ Enable in Dashboard |

For **custom-branded emails** using your own email service (SendGrid, SES, etc.), defer to a future phase with Celery tasks that read webhook events and send via your own email backend.

---

## Customer Portal Customization (MEDIUM)

1. Go to **Stripe Dashboard → Settings → Billing → Customer portal** (https://dashboard.stripe.com/settings/billing/portal)
2. Configure:
   - Business name and logo
   - Allowed features (cancel subscriptions, update payment method, download invoices)
   - Appearance (colors, layout)
3. The portal is already integrated via `create_portal_session()` in the codebase

---

## Post-Configuration Verification

After completing all steps above, verify by:

1. **Tax**: Create a test checkout with a customer from a different country — confirm tax is calculated
2. **Invoicing**: Complete a test payment — check that an invoice PDF is generated and emailed
3. **Smart Retries**: Use Stripe's test card `4000 0000 0000 0002` (decline) — confirm retry emails are sent
4. **Emails**: Trigger each event type — confirm emails are received
5. **Portal**: Log in as a test customer — confirm portal shows subscription, invoices, and payment method update
6. **Refunds (F1/F3)**: Issue a test refund via admin endpoint — confirm idempotency key prevents double-refund
7. **Customer Sync (F8)**: Update customer email in Stripe Portal — confirm local profile syncs via webhook
8. **Transaction History (F11)**: Load billing page — confirm invoice/charge history pulled from Stripe
