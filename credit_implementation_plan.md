# Credit System — Implementation Plan

> **Satta Ledger** — Prepaid Credit System for Non-Stripe Subscribers
> Version: 1.0 | Created: 2026-05-29

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Core Concepts](#2-core-concepts)
3. [Data Model Changes (Backend)](#3-data-model-changes-backend)
4. [Unified Access Check](#4-unified-access-check)
5. [Invoice Generation for Compliance](#5-invoice-generation-for-compliance)
6. [Modified `auth/me` Response](#6-modified-authme-response)
7. [Backend API Endpoints](#7-backend-api-endpoints)
8. [Stripe Webhook Parity](#8-stripe-webhook-parity)
9. [Frontend Changes](#9-frontend-changes)
10. [Migration Plan](#10-migration-plan)
11. [Security & Audit](#11-security--audit)
12. [File Inventory](#12-file-inventory)

---

## 1. Design Philosophy

**Problem:** Some users cannot pay via Stripe (no card, local-only banking, regional restrictions). The system needs an alternative payment path that grants **identical access** to sister domains.

**Principle:** Credits are **prepaid monetary balances** tied to specific plans and products. A user who purchases $9.00 of credits for the "Standard" plan gets **exactly the same access duration** as a user who pays $9.00/month via Stripe subscription. There is no per-request consumption — credits map to **billing periods**, just like subscriptions.

**Implication:** Credit purchases must generate **proper invoices** for tax compliance (both for Sattabase's VAT/GST records and for the user's own records).

---

## 2. Core Concepts

### Credit Pools

A user buys credits for a specific **product + plan** combination. The credit pool covers the plan's price for a defined number of billing periods.

**Example:**
- Plan: "Standard" → $9.00/month
- User buys $27.00 of credits → covers 3 months
- System uses the plan's `price_cents` and `billing_cycle` to calculate exactly how many periods are covered

### Active Status Logic

A user is considered **active** for a product if **any** of the following is true:
1. They have an active Stripe subscription (`Subscription.is_effectively_active()`)
2. They have a credit pool (`Credit`) with `status='active'` and remaining periods > 0 and not expired

When both exist, **Stripe subscription takes precedence** (it's the "live" payment). Credits are the fallback.

### Invoice Generation

Every credit purchase creates a locally-generated `CreditInvoice` (separate from the Stripe-linked `Invoice` model). This serves as:
- The user's **receipt** for accounting/tax purposes
- Sattabase's **revenue record** for manual/offline payments
- **Audit trail** for compliance (who bought what, when, paid how)

---

## 3. Data Model Changes (Backend)

### 3.1 New Model: `CreditPool`

Represents a prepaid balance for a specific user + product + plan.

```python
class CreditPool(TimeStampedModel):
    """Prepaid credit balance for a user, tied to a specific plan."""

    class CreditSource(models.TextChoices):
        MANUAL = "manual", _("Manual (Admin)")
        LOCAL_GATEWAY = "local_gateway", _("Local Payment Gateway")
        BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
        CASH = "cash", _("Cash Payment")

    class CreditPoolStatus(models.TextChoices):
        ACTIVE = "active", _("Active")
        EXHAUSTED = "exhausted", _("Exhausted")
        EXPIRED = "expired", _("Expired")
        REFUNDED = "refunded", _("Refunded")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="credit_pools", db_index=True)
    product = models.ForeignKey("billing.Product", on_delete=models.CASCADE,
        related_name="credit_pools", db_index=True)
    plan = models.ForeignKey("billing.Plan", on_delete=models.PROTECT,
        related_name="credit_pools", db_index=True)

    # Financial
    amount_cents = models.PositiveIntegerField(
        _("Amount Paid (cents)"),
        help_text="Total amount the user paid for this credit pool, in cents")
    currency = models.CharField(_("Currency"), max_length=3, default="USD")
    credit_periods = models.PositiveIntegerField(
        _("Billing Periods Covered"),
        help_text="Number of billing periods this credit pool covers, computed from amount_cents / plan.price_cents")
    periods_consumed = models.PositiveIntegerField(
        _("Periods Consumed"), default=0)

    # Source tracking
    source = models.CharField(_("Payment Source"), max_length=20,
        choices=CreditSource.choices, default=CreditSource.MANUAL)
    payment_reference = models.CharField(_("Payment Reference"), max_length=255,
        blank=True, default="",
        help_text="Bank reference, transaction ID, or admin note")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="credits_created",
        help_text="Admin who recorded this payment (null for automated)")

    # Lifecycle
    status = models.CharField(_("Status"), max_length=20,
        choices=CreditPoolStatus.choices, default=CreditPoolStatus.ACTIVE, db_index=True)
    activated_at = models.DateTimeField(_("Activated At"), null=True, blank=True,
        help_text="When the first period begins. Set on creation for immediate activation.")
    current_period_start = models.DateTimeField(null=True, blank=True,
        db_index=True, help_text="Start of the current billing period")
    current_period_end = models.DateTimeField(null=True, blank=True,
        db_index=True, help_text="End of the current billing period")
    expires_at = models.DateTimeField(null=True, blank=True,
        db_index=True, help_text="Hard expiry — credit pool expires even if periods remain")

    class Meta:
        db_table = "billing_credit_pool"
        ordering = ["-created_at"]
        verbose_name = _("Credit Pool")
        verbose_name_plural = _("Credit Pools")

    @property
    def periods_remaining(self) -> int:
        return max(0, self.credit_periods - self.periods_consumed)

    @property
    def is_effectively_active(self) -> bool:
        if self.status != self.CreditPoolStatus.ACTIVE:
            return False
        if self.periods_remaining <= 0:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    @property
    def display_amount(self) -> str:
        return f"{self.amount_cents / 100:.2f} {self.currency}"
```

### 3.2 New Model: `CreditInvoice`

Locally-generated invoice for a credit purchase. This is the **tax-compliant receipt** — it's not linked to Stripe at all.

```python
class CreditInvoice(TimeStampedModel):
    """Locally-generated invoice/credit receipt for a credit pool purchase.

    Serves as the tax-compliant document for non-Stripe payments.
    Mirrors the structure of a subscription invoice for reporting uniformity.
    """

    class CreditInvoiceStatus(models.TextChoices):
        DRAFT = "draft", _("Draft")
        ISSUED = "issued", _("Issued")
        PAID = "paid", _("Paid")
        VOID = "void", _("Void")

    id = models.BigAutoField(primary_key=True)
    credit_pool = models.ForeignKey(CreditPool, on_delete=models.CASCADE,
        related_name="invoices", db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="credit_invoices", db_index=True)
    product = models.ForeignKey("billing.Product", on_delete=models.CASCADE,
        related_name="credit_invoices")
    plan = models.ForeignKey("billing.Plan", on_delete=models.PROTECT,
        related_name="credit_invoices")

    # Invoice fields (mirrors Stripe Invoice structure for uniformity)
    invoice_number = models.CharField(_("Invoice Number"), max_length=50,
        unique=True, db_index=True,
        help_text="Locally generated, e.g. SB-CRED-00001")
    status = models.CharField(_("Status"), max_length=20,
        choices=CreditInvoiceStatus.choices, default=CreditInvoiceStatus.ISSUED)
    amount_cents = models.PositiveIntegerField(_("Amount (cents)"))
    currency = models.CharField(_("Currency"), max_length=3, default="USD")
    tax_cents = models.PositiveIntegerField(_("Tax (cents)"), default=0)
    total_cents = models.PositiveField(_("Total (cents)"), help_text="amount + tax")

    # Billing period this invoice covers
    period_start = models.DateTimeField(null=True, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)

    # Compliance
    payment_reference = models.CharField(_("Payment Reference"), max_length=255,
        blank=True, default="")
    notes = models.TextField(blank=True, default="",
        help_text="Internal notes (not shown to user)")
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "billing_credit_invoice"
        ordering = ["-issued_at"]
        verbose_name = _("Credit Invoice")
        verbose_name_plural = _("Credit Invoices")
```

### 3.3 New Model: `CreditTransaction`

Immutable ledger of all credit pool mutations — purchase, period consumption, refund, expiry, adjustments.

```python
class CreditTransaction(models.Model):
    """Immutable audit ledger for credit pool mutations."""

    class TransactionType(models.TextChoices):
        PURCHASE = "purchase", _("Purchase")
        PERIOD_CONSUME = "period_consume", _("Period Consumed")
        REFUND = "refund", _("Refund")
        ADJUST = "adjust", _("Admin Adjustment")
        EXPIRE = "expire", _("Expiry")

    id = models.BigAutoField(primary_key=True)
    credit_pool = models.ForeignKey(CreditPool, on_delete=models.CASCADE,
        related_name="transactions", db_index=True)
    invoice = models.ForeignKey(CreditInvoice, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="transactions")

    action = models.CharField(_("Action"), max_length=20,
        choices=TransactionType.choices, db_index=True)
    periods_delta = models.IntegerField(
        _("Periods Delta"),
        help_text="Positive for purchase, negative for consume/refund/adjust")
    amount_cents_delta = models.IntegerField(
        _("Amount Delta (cents)"),
        help_text="Positive for purchase, negative for refund/adjust")
    periods_balance = models.PositiveIntegerField(
        _("Running Period Balance"),
        help_text="Periods remaining after this transaction")

    reason = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="credit_transactions_created")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "billing_credit_transaction"
        ordering = ["-created_at"]
        verbose_name = _("Credit Transaction")
        verbose_name_plural = _("Credit Transactions")
```

---

## 4. Unified Access Check

### 4.1 New Service Method in `billing/services.py`

Add to `BillingService`:

```python
@staticmethod
def is_user_active_for_product(user, product) -> dict:
    """
    Check if a user has active access to a product via subscription OR credits.

    Returns:
        {
            "is_active": bool,
            "source": "subscription" | "credit" | None,
            "plan": Plan | None,
            "access_map": dict,
            "current_period_end": datetime | None,
            "expires_at": datetime | None,
            "is_credit_based": bool,
        }
    """
    now = timezone.now()

    # 1. Check Stripe subscription first (takes precedence)
    sub = Subscription.objects.select_related("plan").filter(
        user=user,
        product=product,
        status__in=[
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.CANCELED,
        ],
        current_period_end__gt=now,
    ).first()

    if sub:
        return {
            "is_active": True,
            "source": "subscription",
            "plan": sub.plan,
            "access_map": sub.get_access_map(),
            "current_period_end": sub.current_period_end,
            "expires_at": sub.current_period_end,
            "is_credit_based": False,
        }

    # 2. Check credit pool
    credit_pool = CreditPool.objects.select_related("plan").filter(
        user=user,
        product=product,
        status=CreditPool.CreditPoolStatus.ACTIVE,
        periods_remaining__gt=0,
    ).filter(
        models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now)
    ).order_by("-created_at").first()

    if credit_pool:
        plan = credit_pool.plan
        access_map = {e.key: e.typed_value for e in plan.access_entries.all()}
        return {
            "is_active": True,
            "source": "credit",
            "plan": plan,
            "access_map": access_map,
            "current_period_end": credit_pool.current_period_end,
            "expires_at": credit_pool.current_period_end,
            "is_credit_based": True,
        }

    return {
        "is_active": False,
        "source": None,
        "plan": None,
        "access_map": {},
        "current_period_end": None,
        "expires_at": None,
        "is_credit_based": False,
    }
```

---

## 5. Invoice Generation for Compliance

### 5.1 Invoice Number Generator

Add to `billing/services.py`:

```python
@staticmethod
def generate_credit_invoice_number() -> str:
    """Generate a unique local invoice number: SB-CRED-00001"""
    prefix = "SB-CRED-"
    last = CreditInvoice.objects.order_by("-id").first()
    if last and last.invoice_number.startswith(prefix):
        try:
            num = int(last.invoice_number.split("-")[-1]) + 1
        except ValueError:
            num = 1
    else:
        num = 1
    return f"{prefix}{num:05d}"
```

### 5.2 Invoice Creation on Credit Purchase

When an admin creates a credit pool (or a user completes a local payment flow), the system:

1. Creates a `CreditPool`
2. Creates a `CreditInvoice` with status `PAID` (for manual payments) or `ISSUED` (pending)
3. Creates a `CreditTransaction` of type `PURCHASE`

```python
@staticmethod
def create_credit_pool(user, plan, amount_cents, source="manual",
                       payment_reference="", created_by=None,
                       currency="USD", tax_cents=0):
    """
    Create a credit pool and its associated invoice.
    Returns (CreditPool, CreditInvoice).
    """
    now = timezone.now()
    credit_periods = amount_cents // plan.price_cents if plan.price_cents > 0 else 1

    # Compute billing period dates
    period_start = now
    period_end = BillingService._compute_period_end(
        now, plan.billing_cycle, credit_periods
    )

    pool = CreditPool.objects.create(
        user=user,
        product=plan.product,
        plan=plan,
        amount_cents=amount_cents,
        currency=currency,
        credit_periods=credit_periods,
        source=source,
        payment_reference=payment_reference,
        created_by=created_by,
        status=CreditPool.CreditPoolStatus.ACTIVE,
        activated_at=now,
        current_period_start=period_start,
        current_period_end=period_end,
        expires_at=period_end,
    )

    invoice_number = BillingService.generate_credit_invoice_number()
    invoice = CreditInvoice.objects.create(
        credit_pool=pool,
        user=user,
        product=plan.product,
        plan=plan,
        invoice_number=invoice_number,
        status=CreditInvoice.CreditInvoiceStatus.PAID,
        amount_cents=amount_cents,
        currency=currency,
        tax_cents=tax_cents,
        total_cents=amount_cents + tax_cents,
        period_start=period_start,
        period_end=period_end,
        payment_reference=payment_reference,
        issued_at=now,
    )

    CreditTransaction.objects.create(
        credit_pool=pool,
        invoice=invoice,
        action=CreditTransaction.TransactionType.PURCHASE,
        periods_delta=credit_periods,
        amount_cents_delta=amount_cents,
        periods_balance=credit_periods,
        reason=f"Credit purchase via {source}",
        created_by=created_by,
    )

    return pool, invoice
```

---

## 6. Modified `auth/me` Response

### Schema Changes in `billing/schemas.py`

Add a field to `SubscriptionInfoSchema`:

```python
class SubscriptionInfoSchema(Schema):
    # ... existing fields ...
    is_credit_based: bool = Field(
        False,
        description="True if active via prepaid credits rather than Stripe subscription"
    )
```

The `AuthMeSchema` stays the same structurally, but the service layer populates it with `is_credit_based=True` when the user's access comes from a credit pool.

### Service Layer Change

Modify `BillingService.get_auth_me_data()` to use the new `is_user_active_for_product()` method, which returns `is_credit_based` in the result dict.

---

## 7. Backend API Endpoints

### 7.1 Credit Pool Management (`admin_controller.py`)

| Endpoint | Method | Purpose |
|---|---|---|
| `/admin/credits` | GET | List all credit pools (filters: user, product, status, source) |
| `/admin/credits` | POST | Purchase credits (admin records a manual payment) |
| `/admin/credits/{id}` | GET | Credit pool detail with transaction history |
| `/admin/credits/{id}/refund` | POST | Refund a credit pool (void remaining periods) |
| `/admin/credits/{id}/adjust` | POST | Admin adjustment (add/remove periods) |
| `/admin/credits/{id}/transactions` | GET | Full transaction ledger |

### 7.2 Credit Invoice Endpoints (`admin_controller.py`)

| Endpoint | Method | Purpose |
|---|---|---|
| `/admin/credit-invoices` | GET | List all credit invoices |
| `/admin/credit-invoices/{invoice_number}` | GET | Invoice detail (for download/display) |
| `/admin/credit-invoices/{invoice_number}/void` | POST | Void a credit invoice |

### 7.3 User-Facing Endpoints (`billing/controllers.py` — or wherever the main billing controller lives)

| Endpoint | Method | Purpose |
|---|---|---|
| `/billing/credits` | GET | List current user's credit pools |
| `/billing/credits/invoices` | GET | List current user's credit invoices |
| `/billing/credits/purchase` | POST | Request a credit purchase (generates pending payment for admin review) |

### 7.4 Schemas (`billing/admin_schemas.py`)

New schemas to add:

```python
class AdminCreditPurchaseSchema(Schema):
    """Admin creates a credit purchase record."""
    user_email: str = Field(..., description="Email of the user receiving credits")
    product_slug: str = Field(..., description="Product slug")
    plan_slug: str = Field(..., description="Plan slug")
    amount_cents: int = Field(..., ge=0, description="Amount paid (cents)")
    currency: str = Field("USD", max_length=3)
    source: str = Field("manual", description="manual, local_gateway, bank_transfer, cash")
    payment_reference: str = Field("", description="TXN ID or bank reference")
    tax_cents: int = Field(0, ge=0, description="Tax amount for compliance")
    notes: str = Field("", description="Admin notes")

class AdminCreditRefundSchema(Schema):
    """Refund a credit pool."""
    reason: str = Field(..., description="Reason for the refund")

class AdminCreditAdjustSchema(Schema):
    """Adjust credit balance."""
    periods_delta: int = Field(..., description="Positive to add, negative to remove")
    reason: str = Field(...)
    amount_cents_delta: Optional[int] = Field(None, description="Monetary equivalent")

class CreditPoolOutputSchema(Schema):
    """Credit pool in API responses."""
    id: int
    plan_name: str
    plan_slug: str
    product_name: str
    amount_cents: int
    display_amount: str
    currency: str
    credit_periods: int
    periods_consumed: int
    periods_remaining: int
    source: str
    payment_reference: str
    status: str
    is_effectively_active: bool
    current_period_start: Optional[datetime]
    current_period_end: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
```

---

## 8. Stripe Webhook Parity

### What Happens When a Credit User Converts to Stripe?

When a user with an active credit pool starts a Stripe checkout and the `checkout.session.completed` webhook fires:

1. The existing `CreditPool` should be **cancelled** (status → `CANCELLED`)
2. A `CreditTransaction` of type `ADJUST` records the cancellation
3. Any remaining credit periods are voided (no partial refunds — the Stripe subscription takes over)

This prevents double-access. Add a step to the existing webhook handler (`billing/stripe/webhooks/handlers/checkout.py`).

---

## 9. Frontend Changes

### 9.1 New File: `frontend/src/lib/credits.ts`

```typescript
// Types
export interface CreditPool {
  id: number;
  plan_name: string;
  plan_slug: string;
  product_name: string;
  amount_cents: number;
  display_amount: string;
  currency: string;
  credit_periods: number;
  periods_consumed: number;
  periods_remaining: number;
  source: string;
  status: string;
  is_effectively_active: boolean;
  current_period_start: string | null;
  current_period_end: string | null;
  created_at: string;
}

export interface CreditInvoice {
  id: number;
  invoice_number: string;
  status: string;
  amount_cents: number;
  total_cents: number;
  currency: string;
  plan_name: string;
  product_name: string;
  period_start: string | null;
  period_end: string | null;
  issued_at: string | null;
}

export interface CreditPurchaseResponse {
  pool: CreditPool;
  invoice: CreditInvoice;
}

// API client
export const creditsApi = {
  // User-facing
  async getMyCredits(): Promise<CreditPool[]> { ... },
  async getMyCreditInvoices(): Promise<CreditInvoice[]> { ... },
  async requestCreditPurchase(productSlug: string, planSlug: string, amountCents: number): Promise<{ message: string }> { ... },

  // Admin
  async adminListCredits(params?: AdminCreditListParams): Promise<PaginatedResponse<CreditPool>> { ... },
  async adminPurchaseCredit(payload: AdminCreditPurchasePayload): Promise<CreditPurchaseResponse> { ... },
  async adminRefundCredit(creditId: number, reason: string): Promise<CreditPool> { ... },
  async adminAdjustCredit(creditId: number, payload: AdminCreditAdjustPayload): Promise<CreditPool> { ... },
  async adminGetTransactions(creditId: number): Promise<CreditTransaction[]> { ... },
};
```

### 9.2 New Admin Component: `frontend/src/components/admin/CreditManagement.vue`

- List all credit pools with filters (user, product, status, source)
- "Record Payment" button to create a credit purchase
- Per-pool actions: view, refund, adjust
- Transaction history modal

### 9.3 Modified Component: `frontend/src/lib/billing.ts`

Add `is_credit_based: boolean` to the `SubscriptionInfoSchema` interface so sister domain dashboards can show "Paid via Credits" vs "Paid via Stripe".

### 9.4 Modified Component: Credit Checkout Flow

When the existing Stripe checkout fails or the user selects a "Pay Locally" option:
1. Show amount owed based on selected plan
2. User submits a purchase request
3. Admin records the payment → `CreditPool` + `CreditInvoice` created
4. User gets access immediately (admin-approved flow)

---

## 10. Migration Plan

1. **Django migration** `0019_credit_creditpool_creditinvoice_credittransaction.py`
   - Auto-generated via `python manage.py makemigrations billing`
2. **Data migration** (optional): If existing users need to be migrated from a legacy state
3. **Settings**: Add `SB_CREDIT_INVOICE_PREFIX` and `SB_CREDIT_TAX_RATE` to settings/env

No existing data is modified — this is purely additive.

---

## 11. Security & Audit

- All credit mutations are logged in `CreditTransaction` (immutable — no updates/deletes)
- Admin endpoints require `is_staff=True` (same as existing admin billing endpoints)
- Credit pool creation requires a valid `user_email` + `plan` combination
- Invoice numbers are unique and sequential — cannot be modified after creation
- Refunds require a `reason` field (audit requirement)
- All credit operations are decorated with `@log_admin_access` (same pattern as existing admin endpoints)

---

## 12. File Inventory

### Files to Modify

| File | Change Type | Description |
|---|---|---|
| `backend/billing/models.py` | Append | Add `CreditPool`, `CreditInvoice`, `CreditTransaction` models |
| `backend/billing/schemas.py` | Append | Add `is_credit_based` to `SubscriptionInfoSchema`, credit output schemas |
| `backend/billing/admin_schemas.py` | Append | Add admin credit CRUD schemas |
| `backend/billing/services.py` | Append | Add `is_user_active_for_product()`, `create_credit_pool()`, `generate_credit_invoice_number()` |
| `backend/billing/admin_controller.py` | Append | Add credit pool + invoice management endpoints |
| `backend/billing/stripe/webhooks/handlers/checkout.py` | Modify | Cancel active credit pool on Stripe subscription creation |
| `frontend/src/lib/billing.ts` | Modify | Add `is_credit_based` to `SubscriptionInfoSchema` interface |
| `frontend/src/lib/api.ts` | No change needed | Existing `apiClient` supports all required HTTP methods |

### Files to Create

| File | Description |
|---|---|
| `backend/billing/migrations/0019_credit_creditpool_creditinvoice_credittransaction.py` | Auto-generated migration |
| `frontend/src/lib/credits.ts` | Credit API client types + functions |
| `frontend/src/components/admin/CreditManagement.vue` | Admin credit management UI |

---

*End of plan.*
