# Credit Request System Enhancement Plan

> **Status:** In Progress  
> **Created:** 2026-06-03  
> **Updated:** 2026-06-04  
> **Scope:** Billing / Credit Request & Pool Lifecycle  
>  
> **Progress:** Enhancement 1 ✅ | Enhancement 2 ✅ | Enhancement 3 ⬜ | Enhancement 4 ⬜ | Enhancement 5 ⬜  

---

## Executive Summary

The current credit request system allows users to purchase subscription access via bank transfer as an alternative to Stripe. However, several gaps undermine professionalism, compliance, and user clarity:

1. **No explicit commitment period** — Users submit an `amount_cents` value; periods are derived behind the scenes. There is no minimum commitment, and the UI does not make the user choose or acknowledge a duration.
2. **Validity and compliance messaging is incomplete** — Approval emails and PDF invoices do not clearly state the commitment duration, non-refundability, or what happens when credits expire.
3. **No pre-expiry notifications** — Unlike Stripe subscriptions (which send renewal reminders), credit pools silently expire or exhaust without warning the user.

This document proposes a phased enhancement plan to address these gaps.

---

## Current System Analysis

### How It Works Today

| Step | What Happens |
|------|-------------|
| **1. User submits request** | Fills in product, plan, `amount_cents`, and bank transfer details. **No months/periods field.** |
| **2. Admin approves** | `credit_periods` is **derived** as `max(1, amount_cents // plan.price_cents)`. A `CreditPool` and `CreditInvoice` are created. |
| **3. Period consumption** | A daily Celery task (`consume_credit_periods`) at 05:00 UTC checks pools whose `current_period_end <= now` and increments `periods_consumed`. |
| **4. Expiry** | When `periods_remaining == 0`, the pool is marked `EXHAUSTED`. If `expires_at <= now`, it's marked `EXPIRED`. No notification is sent. |
| **5. User finds out** | Only when they notice their access has changed or check the dashboard manually. |

### Key Gaps Identified

| Gap | Impact |
|-----|--------|
| No `months`/`periods` field on `CreditPurchaseRequest` or the frontend form | Users cannot express intent for a specific duration; admin has no visibility into user's commitment expectation |
| No minimum commitment enforced | Users could theoretically request 1 month of credit (same as month-to-month, undermining the prepaid commitment model) |
| Period derivation via `amount_cents // plan.price_cents` is fragile | Rounding, partial payments, and plan price changes can cause incorrect period counts |
| `expires_at` is always set to `period_end` at creation | No distinction between "soft expiry" (all periods consumed) and "hard expiry" (calendar deadline) |
| Period consumption uses `timedelta(days=30)` instead of `relativedelta` | Month boundaries drift — February is treated as 30 days, causing misalignment with actual calendar months |
| No pre-expiry or pre-exhaustion notifications | Users have no warning before losing access |
| Approval email does not show validity end date or commitment terms | Users may not understand what they've committed to or when it ends |
| PDF invoice does not show remaining periods or commitment terms | Limited value as a compliance/audit document |

---

## Enhancement 1: Commitment Period Field & Minimum Enforcement

### Problem

Currently the user only submits `amount_cents`. Periods are derived as `amount_cents // plan.price_cents`, which means:
- A user paying exactly 1 month's price gets 1 period — no commitment advantage over Stripe
- There's no explicit acknowledgment of commitment duration
- Rounding can produce unexpected period counts (e.g., paying 2.5 months' worth yields only 2 periods)

Since Stripe subscriptions auto-renew from saved payment methods, the credit system needs a fundamentally different model: **a prepaid commitment for a defined number of periods**, not a month-to-month arrangement. Users who choose credits over Stripe are typically those who cannot pay internationally — they should commit to a minimum duration that makes the manual bank transfer process worthwhile for both parties.

### Proposed Changes

#### 1A. Add `credit_periods` Field to `CreditPurchaseRequest` Model

**File:** `billing/models.py` — `CreditPurchaseRequest`

```python
credit_periods = PositiveIntegerField(
    default=1,
    help_text="Number of billing periods (months/years) the user is committing to.",
)
```

This captures the user's intended commitment duration at request time, giving admin a clear signal of intent.

#### 1B. Add `credit_periods` to Frontend Form & API Schema

**File:** `billing/schemas.py` — `CreditRequestInputSchema`

```python
credit_periods: int = Field(
    default=3,
    ge=3,           # Minimum 3 periods (3 months for monthly plans)
    le=36,          # Maximum 36 periods (3 years)
    description="Number of billing periods to commit. Minimum 3 for monthly plans.",
)
```

**Frontend:** `CreditRequestForm.vue` — Add a period selector:
- Show the per-period price (from plan)
- Let user choose number of months (minimum 3 for monthly, minimum 1 for yearly)
- Auto-calculate `amount_cents = credit_periods * plan.price_cents`
- Show a clear "Commitment Summary" box before submission:

  > **3-month commitment at $29/month = $87 total**  
  > This is a non-refundable prepaid commitment for 3 billing periods.

#### 1C. Enforce Minimum Commitment at Backend

**File:** `billing/controllers.py` — `create_credit_request` endpoint

```python
# Validate minimum commitment
plan = await Plan.objects.select_related("product").aget(slug=payload.plan_slug)
min_periods = 3 if plan.billing_cycle == "monthly" else 1
if payload.credit_periods < min_periods:
    raise BadRequestException(
        f"Minimum commitment is {min_periods} period(s) for {plan.billing_cycle} plans."
    )
```

#### 1D. Use User-Submitted Periods at Approval (Not Derived)

**File:** `billing/admin_controller.py` — `approve_credit_request`

Replace the current period derivation:
```python
# OLD: credit_periods = max(1, amount_cents // plan.price_cents)
# NEW: Use the user-submitted commitment
credit_periods = cr.credit_periods
```

The `amount_cents` on the request should match `credit_periods * plan.price_cents` (validated at request creation time), but the source of truth for periods is now the explicit field.

#### 1E. Validate Amount Consistency

**File:** `billing/controllers.py` — `create_credit_request` endpoint

```python
expected_amount = payload.credit_periods * plan.price_cents
if payload.amount_cents != expected_amount:
    raise BadRequestException(
        f"Amount must equal {payload.credit_periods} x {plan.display_price} = "
        f"${expected_amount / 100:.2f}"
    )
```

This prevents users from submitting mismatched amounts and periods.

---

## Enhancement 2: Compliance & Validity Period Messaging ✅ COMPLETED

> **Implemented:** 2026-06-04 — All sub-items (2A–2E) completed.

### Problem

When a credit request is approved:
- The approval email shows "periods: 3" but not the actual end date, non-refundability, or what happens when credits run out
- The PDF invoice shows "Valid Until" but not the commitment terms or non-refundability clause
- There is no explicit acknowledgment that credits are non-refundable and represent a prepaid commitment

This creates compliance risk and user confusion. The credit model is fundamentally different from Stripe — credits grant access to a feature matrix for a defined period. Users need to understand that:
- They are prepaying for a fixed duration
- Credits are consumed at the start of each billing period (not based on usage)
- Unused periods are non-refundable
- Access is revoked when the commitment ends

### Proposed Changes

#### 2A. Approval Email — Add Validity & Commitment Section

**File:** `billing/tasks.py` — `send_credit_request_approved_email`

Add a prominent "Commitment Details" section to the approval email:

```
+-------------------------------------------------------------+
|  COMMITMENT DETAILS                                          |
|                                                              |
|  Product:          Pro                                       |
|  Plan:             Professional                              |
|  Billing Cycle:    Monthly                                   |
|  Commitment:       3 months                                  |
|  Start Date:       June 3, 2026                              |
|  End Date:         September 3, 2026                         |
|  Total Amount:     $87.00 USD                                |
|                                                              |
|  IMPORTANT:                                                  |
|  - This is a non-refundable prepaid commitment for 3         |
|    billing periods.                                          |
|  - Credits are consumed at the start of each billing         |
|    period and grant access to all features of your plan.     |
|  - Access will be revoked when all periods are consumed      |
|    or the commitment expires.                                |
|  - Unused periods are not refundable.                        |
|  - Credits do not auto-renew. Purchase new credits before    |
|    expiry to maintain uninterrupted access.                  |
+-------------------------------------------------------------+
```

Add parameters to the Celery task:
- `commitment_start` — ISO date string
- `commitment_end` — ISO date string
- `billing_cycle` — "monthly" or "yearly"
- `non_refundable_notice` — boolean (always True for credit purchases)

#### 2B. PDF Invoice — Add Commitment & Validity Section

**File:** `billing/pdf_utils.py` — `generate_credit_invoice_pdf`

After the "Payment Details" section, add a "Commitment & Validity" section:

| Field | Value |
|-------|-------|
| Commitment Duration | 3 months (3 billing periods) |
| Commitment Start | June 3, 2026 |
| Commitment End | September 3, 2026 |
| Billing Cycle | Monthly |
| Non-Refundable | Yes — this is a prepaid commitment |
| Auto-Renewal | No — credits do not auto-renew |

Also add a "Terms" note at the bottom of the PDF:

> This invoice represents a non-refundable prepaid commitment for the billing periods stated above. Access to the subscribed plan is granted for the duration of the commitment. Upon expiry of all credited periods, access will be revoked unless a new credit purchase or Stripe subscription is active. Unused periods are not eligible for refund or credit transfer.

#### 2C. Credit Request Form — Add Pre-Submission Acknowledgment

**Frontend:** `CreditRequestForm.vue`

Before the submit button, add a mandatory checkbox:

> [ ] I understand that this is a **non-refundable prepaid commitment** for **{N} billing period(s)**. I acknowledge that:
> - Credits are consumed at the start of each billing period
> - Unused periods are not refundable
> - Access will be revoked when the commitment ends unless renewed
> - This is not an auto-renewing subscription

The form cannot be submitted unless this checkbox is checked.

#### 2D. Admin Approval — Show Commitment Summary

**Frontend:** Admin credit request detail/approval view

Show a clear summary before admin clicks "Approve":

```
Commitment Summary:
  Duration:     3 months
  Per Period:   $29.00
  Total:        $87.00
  Valid Until:  September 3, 2026
  
  Non-refundable prepaid commitment
```

#### 2E. User Dashboard — Credit Validity Display

**Frontend:** `UserCreditsClient.vue` — Credit Pool cards

Enhance the credit pool display to show:
- **Commitment period**: "3-month commitment (Jun 3 - Sep 3, 2026)"
- **Status timeline**: Visual indicator of periods consumed vs. remaining
- **Next period start**: When the next billing period begins
- **Non-renewal notice**: "This credit does not auto-renew. Purchase new credits before expiry to maintain access."

---

## Enhancement 3: Pre-Expiry & Pre-Exhaustion Notifications

### Problem

Stripe automatically sends subscription renewal reminders. Credit pools have no equivalent. Users can lose access without any warning, leading to:
- Surprise loss of access to paid features
- Support tickets and complaints
- Potential data loss if features are revoked abruptly

The credit system needs to match the professionalism of Stripe's notification system. Since credits don't auto-renew, the notification is even more critical — users must take manual action (purchase new credits or start a Stripe subscription) before their access expires.

### Proposed Changes

#### 3A. New Celery Task: `send_credit_expiry_warning`

**File:** `billing/tasks.py`

Create a new daily Celery task that sends warning emails at configurable intervals before credit expiry:

```
Schedule: crontab(minute=15, hour=5) — daily at 05:15 UTC
```

**Logic:**
1. Find all `CreditPool` with `status=ACTIVE`
2. For each pool, calculate days until expiry:
   - Primary: `current_period_end - now` (next period boundary)
   - Secondary: `expires_at - now` (hard deadline, if set)
3. Send warnings at these thresholds:
   - **14 days** before the last period starts (the final period begins — this is the last chance to renew with overlap)
   - **7 days** before `expires_at` (hard deadline approaching)
   - **1 day** before `expires_at` (urgent final notice)

**Warning Email Content:**

For 14-day notice:
```
Subject: Your credit commitment ends in 2 weeks

Your {product} - {plan} credit commitment will end on {end_date}.
You have {periods_remaining} billing period(s) remaining.

To maintain uninterrupted access, please:
  - Purchase new credits before your current commitment ends
  - Or subscribe via Stripe for automatic renewal

[Purchase Credits]  [Subscribe with Stripe]
```

For 7-day and 1-day notices:
```
Subject: Your access will expire in {N} day(s)

Your {product} - {plan} credit commitment expires on {end_date}.
After expiry, you will lose access to premium features.

Don't lose your progress — renew now:
  [Purchase Credits]  [Subscribe with Stripe]
```

#### 3B. Track Notification Delivery (Avoid Spam)

**New Model:** `CreditNotificationLog`

```python
class CreditNotificationLog(TimeStampedModel):
    credit_pool = ForeignKey(CreditPool, on_delete=CASCADE)
    notification_type = CharField(max_length=30)  # "expiry_14d", "expiry_7d", "expiry_1d"
    sent_at = DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [("credit_pool", "notification_type")]
```

This ensures each warning is sent **at most once** per pool, preventing duplicate emails if the task runs multiple times or is retried.

#### 3C. Admin Configuration for Notification Thresholds

**File:** `billing/models.py` or site settings

Add configurable notification thresholds (default: 14, 7, 1 days):

```python
# In Django settings or SiteSettings model
CREDIT_EXPIRY_WARNING_DAYS = [14, 7, 1]  # Days before expiry to send warnings
```

This could be stored in a `SiteSettings` model or as Django settings for now, with an admin UI added later.

#### 3D. Grace Period Before Access Revocation

**File:** `billing/tasks.py` — `expire_credit_pools`

Instead of immediately marking a pool as `EXPIRED` when `expires_at <= now`, introduce a 24-hour grace period:

```python
# Instead of: expires_at <= now
# Use: now >= expires_at + timedelta(hours=24)
# During the grace period, the pool is still ACTIVE but flagged for warning

grace_period_end = expires_at + timedelta(hours=24)
if now >= grace_period_end:
    pool.status = EXPIRED
```

During the grace period:
- Access is still granted (pool remains `ACTIVE`)
- A final "last chance" email is sent (the 1-day notification)
- The dashboard shows an urgent "Credits expiring today!" banner

This prevents abrupt access loss and gives users a final window to renew.

#### 3E. Dashboard Expiry Warning Banner

**Frontend:** `DashboardHome.vue` and `UserCreditsClient.vue`

When the user has credit pools expiring within 7 days, show a prominent warning banner:

```
+------------------------------------------------------------------+
|  Your {product} credit expires in {N} day(s) on {end_date}.      |
|  Purchase new credits or subscribe via Stripe to maintain access. |
|  [Purchase Credits]  [Subscribe with Stripe]                      |
+------------------------------------------------------------------+
```

The banner should appear:
- On the main dashboard homepage
- On the Credits page
- With increasing urgency (yellow at 14 days, orange at 7 days, red at 1 day)

---

## Enhancement 4: Fix Period Consumption Drift (Bug Fix)

### Problem

The daily `consume_credit_periods` task uses `timedelta(days=30)` for monthly plans and `timedelta(days=365)` for yearly plans. This causes drift from actual calendar months:
- February gets 30 days instead of 28/29
- 30-day months get treated the same as 31-day months
- Over multiple periods, the cumulative drift grows significantly

Meanwhile, `_compute_period_end()` in `services.py` uses `relativedelta(months=N)` which correctly handles calendar month boundaries.

### Proposed Fix

**File:** `billing/tasks.py` — `consume_credit_periods`

Replace the hardcoded timedelta approach with `relativedelta`:

```python
from dateutil.relativedelta import relativedelta

# OLD:
# next_end = now + timedelta(days=30)   # monthly
# next_end = now + timedelta(days=365)  # yearly

# NEW:
if plan.billing_cycle == "monthly":
    next_end = now + relativedelta(months=1)
elif plan.billing_cycle == "yearly":
    next_end = now + relativedelta(years=1)
else:
    next_end = now + relativedelta(months=1)  # default to monthly
```

This ensures period boundaries align with actual calendar months, just like the initial creation logic does.

---

## Enhancement 5: Distinguish Soft Expiry from Hard Expiry

### Problem

Currently `expires_at` is always set to the computed `period_end` (end of all periods). This conflates two concepts:

- **Soft expiry** — All periods have been consumed (natural end of commitment)
- **Hard expiry** — A calendar deadline after which the pool is invalid regardless of remaining periods

In the current design they're always the same, but they shouldn't be. For example:
- An admin might want to set a hard deadline for a promotional credit
- A credit might need to expire at the end of a calendar year for accounting purposes
- A promotional credit with 6 months of access should expire after 6 calendar months, even if the user hasn't "consumed" all 6 periods

### Proposed Changes

#### 5A. Stop Setting `expires_at` at Creation

**File:** `billing/services.py` — `create_credit_pool`

```python
# Keep expires_at for hard expiry (admin override or promotional deadline)
# Default: None (no hard expiry — pool only expires when periods are consumed)
pool = CreditPool.objects.create(
    ...,
    expires_at=None,  # No hard expiry by default; soft expiry via period consumption
)
```

The `is_effectively_active` property already handles `None` `expires_at`:
```python
is_effectively_active = (
    status == ACTIVE 
    AND periods_remaining > 0 
    AND (expires_at is None OR expires_at > now)
)
```

So this already works correctly — we just need to stop setting `expires_at = period_end` at creation.

#### 5B. Add `commitment_end` Computed Property

**File:** `billing/models.py` — `CreditPool`

```python
@property
def commitment_end(self):
    """The date when the commitment naturally ends (all periods consumed)."""
    if not self.activated_at:
        return None
    from dateutil.relativedelta import relativedelta
    if self.plan.billing_cycle == "yearly":
        delta = relativedelta(years=self.credit_periods)
    else:
        delta = relativedelta(months=self.credit_periods)
    return self.activated_at + delta
```

This gives us a clean way to show the expected end date without conflating it with `expires_at`. The `commitment_end` is the natural end based on periods, while `expires_at` is an optional hard deadline set by admins.

---

## Implementation Phases

### Phase 1: Commitment Period & Minimum (Priority: HIGH)

**Estimated effort:** 2-3 days

| Task | Files |
|------|-------|
| Add `credit_periods` to `CreditPurchaseRequest` model + migration | `billing/models.py`, `billing/migrations/` |
| Add `credit_periods` to `CreditRequestInputSchema` | `billing/schemas.py` |
| Update credit request API endpoint (validation, amount consistency) | `billing/controllers.py` |
| Update admin approve endpoint (use submitted periods) | `billing/admin_controller.py` |
| Update `BillingService.create_credit_pool()` (accept periods param) | `billing/services.py` |
| Add period selector to frontend credit request form | `CreditRequestForm.vue` |
| Add pre-submission acknowledgment checkbox | `CreditRequestForm.vue` |
| Add commitment summary to admin approval view | Admin credit request component |

### Phase 2: Compliance & Validity Messaging (Priority: HIGH)

**Estimated effort:** 1-2 days

| Task | Files |
|------|-------|
| Enhance approval email with commitment details & terms | `billing/tasks.py` |
| Enhance PDF invoice with commitment & validity section | `billing/pdf_utils.py` |
| Update admin approval view summary | Admin credit request component |
| Enhance user dashboard credit pool display | `UserCreditsClient.vue` |
| Add non-renewal notice to credit pool cards | `UserCreditsClient.vue` |

### Phase 3: Pre-Expiry Notifications (Priority: HIGH)

**Estimated effort:** 2-3 days

| Task | Files |
|------|-------|
| Create `CreditNotificationLog` model + migration | `billing/models.py`, `billing/migrations/` |
| Create `send_credit_expiry_warning` Celery task | `billing/tasks.py` |
| Add Celery beat schedule for the task | `base/celery.py` |
| Implement 14-day, 7-day, 1-day warning emails | `billing/tasks.py` |
| Add notification log tracking to prevent duplicates | `billing/tasks.py` |
| Add grace period to `expire_credit_pools` task | `billing/tasks.py` |
| Add urgent expiry banner to user dashboard | `DashboardHome.vue`, `UserCreditsClient.vue` |

### Phase 4: Bug Fixes & Architecture Improvements (Priority: MEDIUM)

**Estimated effort:** 1 day

| Task | Files |
|------|-------|
| Fix period consumption drift (use `relativedelta`) | `billing/tasks.py` |
| Separate `expires_at` from `period_end` | `billing/services.py` |
| Add `commitment_end` computed property to `CreditPool` | `billing/models.py` |
| Update all references to `expires_at` that assumed it equals `period_end` | Various |

---

## Data Migration Notes

### Phase 1 Migration: Adding `credit_periods` to `CreditPurchaseRequest`

For existing `PENDING` requests, set `credit_periods` based on the current derivation logic:

```python
def forwards(apps, schema_editor):
    CreditPurchaseRequest = apps.get_model("billing", "CreditPurchaseRequest")
    for req in CreditPurchaseRequest.objects.filter(status="pending"):
        plan = req.plan
        req.credit_periods = max(1, req.amount_cents // plan.price_cents)
        req.save(update_fields=["credit_periods"])
```

For existing `APPROVED` requests, the `credit_periods` value is informational only (the pool already exists), so we can backfill it the same way for audit consistency.

### Phase 3 Migration: `CreditNotificationLog`

No data migration needed — this is a new table.

### Phase 4 Migration: `expires_at` Cleanup

For existing pools where `expires_at` equals the computed `period_end`, set `expires_at` to `None` (rely on soft expiry via period consumption). For pools where an admin explicitly set `expires_at` to a different value, keep it.

```python
def forwards(apps, schema_editor):
    CreditPool = apps.get_model("billing", "CreditPool")
    for pool in CreditPool.objects.filter(status="active", expires_at__isnull=False):
        # Compute what period_end would have been at creation
        from dateutil.relativedelta import relativedelta
        if pool.plan.billing_cycle == "yearly":
            expected_end = pool.activated_at + relativedelta(years=pool.credit_periods)
        else:
            expected_end = pool.activated_at + relativedelta(months=pool.credit_periods)
        
        # If expires_at matches the computed period_end, it was auto-set — clear it
        if abs((pool.expires_at - expected_end).total_seconds()) < 86400:  # within 1 day
            pool.expires_at = None
            pool.save(update_fields=["expires_at"])
```

---

## Testing Checklist

### Commitment Period (Phase 1)
- [ ] User can select commitment periods on the credit request form
- [ ] Minimum 3 periods enforced for monthly plans on frontend
- [ ] Minimum 3 periods enforced for monthly plans on backend API
- [ ] `amount_cents` is auto-calculated from `credit_periods * plan.price_cents`
- [ ] Amount/periods mismatch is rejected by the API
- [ ] Admin sees the user's intended commitment duration
- [ ] Approval creates a pool with the correct number of periods (from user input, not derived)
- [ ] Pre-submission acknowledgment checkbox is required before form submission
- [ ] Existing pending requests are migrated with backfilled `credit_periods`

### Compliance Messaging (Phase 2)
- [ ] Approval email contains commitment start/end dates
- [ ] Approval email contains non-refundable notice
- [ ] Approval email states credits do not auto-renew
- [ ] PDF invoice contains commitment & validity section
- [ ] PDF invoice contains terms text about non-refundability
- [ ] Dashboard credit pool card shows commitment details
- [ ] Non-renewal notice is visible on active credit pools
- [ ] Admin approval view shows commitment summary

### Pre-Expiry Notifications (Phase 3)
- [ ] 14-day warning email is sent for pools approaching their last period
- [ ] 7-day warning email is sent for pools approaching hard expiry
- [ ] 1-day urgent email is sent as final notice
- [ ] No duplicate emails are sent (logged in `CreditNotificationLog`)
- [ ] Grace period allows access for 24 hours after `expires_at`
- [ ] Dashboard shows urgent expiry banner during grace period and within 7 days of expiry
- [ ] Expired pools are properly marked after grace period
- [ ] Warning emails include both "Purchase Credits" and "Subscribe with Stripe" CTAs

### Bug Fixes (Phase 4)
- [ ] Period consumption uses `relativedelta` instead of `timedelta(days=30)`
- [ ] `expires_at` is `None` by default for new pools
- [ ] `commitment_end` property returns correct calendar date
- [ ] `is_effectively_active` still works correctly with `None` `expires_at`
- [ ] Existing pools with auto-set `expires_at` are migrated to `None`
- [ ] Admins can still set explicit `expires_at` for promotional credits

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Existing pending requests have no `credit_periods` | Certain | Low | Migration backfills from `amount_cents // plan.price_cents` |
| Minimum 3-month commitment may deter some users | Medium | Medium | Show clear value proposition: "Save by committing longer" with per-month cost comparison; highlight that bank transfer avoids international payment fees |
| Email notification task fails silently | Low | High | Use existing `@shared_task(bind=True, max_retries=3)` pattern with error logging and retry logic |
| Grace period could be abused to extend access | Low | Low | 24-hour maximum, clearly communicated as a courtesy, not a feature |
| Period consumption drift fix changes existing behavior | Medium | Medium | Only affects future consumption; already-consumed periods are historical and unchanged. Test with real data before deploying |
| Separating `expires_at` from `period_end` changes `is_effectively_active` | Low | High | The property already handles `None` `expires_at` correctly; existing pools with `expires_at` set continue to work. Migration carefully distinguishes auto-set vs. admin-set values |
| Notification emails land in spam | Medium | Medium | Use proper email headers, SPF/DKIM configuration, and include plain-text fallback |

---

## Open Questions

1. **Should the minimum commitment differ by plan tier?**  
   Currently proposing 3 months for all monthly plans. Should premium/higher-tier plans have a different minimum (e.g., 6 months)?

2. **Should admins be able to override the minimum commitment?**  
   For special cases (promotional credits, beta users, enterprise customers), should admins bypass the 3-month minimum when manually creating credit pools?

3. **Should credits be transferable between plans?**  
   Currently credits are locked to a specific product+plan. Should users be able to upgrade/downgrade within their commitment? If so, how should the price difference be handled?

4. **What happens to user data when credits expire?**  
   Should there be a data retention period? How long should users have to renew before their data is deleted or downgraded?

5. **Should notification thresholds be configurable via admin UI?**  
   Or is the code-level configuration (`CREDIT_EXPIRY_WARNING_DAYS = [14, 7, 1]`) sufficient for now? An admin UI would allow non-technical staff to adjust timing.

6. **Should the commitment period allow for discounts?**  
   E.g., 3-month commitment at full price, 6-month at 5% off, 12-month at 10% off? This would incentivize longer commitments but adds pricing complexity.

7. **How should mid-cycle credit purchases be handled?**  
   If a user's current credit pool expires on July 15 and they purchase a new 3-month commitment on July 10, should the new commitment start on July 15 (continuity) or July 10 (immediate)?
