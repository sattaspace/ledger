# Sattabase — Central Auth & Subscription Platform

> Multi-tenant subscription management serving multiple service domains
> Enhancement Plan for the existing Ledger project

---

## 1. Vision

Transform the existing Ledger auth system into **Sattabase** — a central platform that handles user authentication, subscription billing, and feature-level access control for multiple independent service domains. Each service domain (e.g., `finance.sattabase.tld`, `analytics.sattabase.tld`) authenticates against Sattabase and receives domain-specific access permissions based on the user's subscription plan.

### Core Principle

```
Service Domain (e.g., finance.sattabase.tld)
        │
        ▼
   auth/me ─────► Returns user info + subscription + access entries
        │               (specific to THIS domain only)
        │
        ▼
   Frontend checks access entries → show/hide features
```

### Design Goals

| Goal | Description |
|------|-------------|
| **Domain autonomy** | Each service domain gets its own plan set and access keys — no collision |
| **Central control** | All products, plans, and access entries live in Sattabase DB — service apps never manage billing |
| **Simple frontend check** | `if (access.reports)` — no complex permission engine needed on the service side |
| **Instant plan changes** | Admin changes access entries on a plan → immediately reflected in next `auth/me` call |
| **Scalable** | Adding a new service = create Product + Plans + Access Entries. No code changes needed |
| **Zero coupling** | Finance plan changes don't touch Analytics plans at all |

---

## 2. Model Architecture

### Entity Relationship

```
Product (one per service domain)
  └── Plan (multiple per product — Free, Standard, Pro, etc.)
        ├── AccessEntry (many key-value pairs per plan)
        └── Subscription (one per user per product)
              ├── user → FK User
              ├── plan → FK Plan
              ├── status → active / past_due / canceled / trialing
              └── billing period (start, end)
```

### New Django App: `billing`

A new Django app `billing` will house all subscription-related models, services, and controllers. This keeps billing concerns cleanly separated from the existing `users` app.

---

## 3. Data Models (Detailed)

### 3.1 ServiceDomain

Represents a connected service domain (e.g., `finance.sattabase.tld`). Each service domain maps to one product via FK. A product can have multiple domains (e.g., subdomain + custom domain).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `domain` | CharField(255) | unique, db_index | Service domain, e.g. "finance.sattabase.tld" |
| `product` | ForeignKey(Product) | CASCADE, db_index | The product this domain serves |
| `is_primary` | BooleanField | default False, db_index | Primary domain for the product |
| `is_active` | BooleanField | default True, db_index | Whether domain is accepting requests |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last modification |

**Database table:** `billing_service_domain`

### 3.2 Product

Represents a product managed by Sattabase. A product is a logical grouping of plans and access entries. Service domains link to a product via FK.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `name` | CharField(100) | unique | Display name, e.g. "Satta Finance" |
| `slug` | SlugField(50) | unique, db_index | URL-safe identifier, e.g. "finance" |
| `description` | TextField | blank | Product description |
| `is_active` | BooleanField | default True | Whether product is accepting new signups |
| `icon` | ImageField | blank, null | Product icon/logo |
| `home_url` | URLField | blank | Landing page URL |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last modification |

**Database table:** `billing_product`

**Methods:**
- `get_primary_domain()` → Returns the primary ServiceDomain for this product
- `get_free_plan()` → Returns the plan where `price=0` for this product
- `get_plans()` → Returns ordered queryset of active plans (by price ascending)

### 3.3 Plan

Represents a subscription tier within a product. Each product has multiple plans (Free, Standard, Pro, Enterprise, etc.).

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `product` | ForeignKey(Product) | CASCADE, db_index | Parent product |
| `name` | CharField(50) | | Plan name, e.g. "Free", "Standard" |
| `slug` | SlugField(50) | | URL-safe identifier |
| `description` | TextField | blank | Plan description shown to users |
| `price_cents` | PositiveIntegerField | default 0 | Price in cents (0 = free plan) |
| `currency` | CharField(3) | default "USD" | ISO 4217 currency code |
| `billing_cycle` | CharField(20) | choices, default "monthly" | monthly, yearly, lifetime |
| `trial_days` | PositiveIntegerField | default 0 | Free trial duration (0 = no trial) |
| `features` | JSONField | default dict | Public feature list for display (e.g., `{"reports": "Advanced", "storage": "10GB"}`) |
| `stripe_price_id` | CharField(100) | blank, null | Stripe Price ID (null for free plans) |
| `sort_order` | PositiveIntegerField | default 0 | Display order |
| `is_active` | BooleanField | default True | Whether plan is available for new subscriptions |
| `is_featured` | BooleanField | default False | Highlight in plan comparison UI |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| **Unique constraint** | | | `(product, slug)` must be unique |

**Database table:** `billing_plan`

**BillingCycle choices:**
```python
class BillingCycle(models.TextChoices):
    MONTHLY = "monthly", _("Monthly")
    YEARLY = "yearly", _("Yearly")
    LIFETIME = "lifetime", _("Lifetime")
```

**Properties:**
- `display_price` → Human-readable price string, e.g. "$9.00/mo"
- `is_free` → `self.price_cents == 0`

### 3.4 AccessEntry

Key-value pairs defining what a plan grants. This is the core mechanism for feature gating.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `plan` | ForeignKey(Plan) | CASCADE, db_index | Parent plan |
| `key` | CharField(100) | | Access key, e.g. "reports", "max_accounts" |
| `value` | CharField(255) | | Access value, e.g. "true", "5", "1000" |
| `value_type` | CharField(10) | choices, default "string" | string, boolean, integer |
| `description` | TextField | blank | Human-readable description of this access entry |
| **Unique constraint** | | | `(plan, key)` must be unique |

**Database table:** `billing_access_entry`

**ValueType choices:**
```python
class AccessValueType(models.TextChoices):
    STRING = "string", _("String")
    BOOLEAN = "boolean", _("Boolean")
    INTEGER = "integer", _("Integer")
```

**Methods:**
- `typed_value` → Returns the value cast to its declared type (bool for "true"/"false", int for integers)
- `as_dict` → `{"key": self.key, "value": self.typed_value, "description": self.description}`

**Example access entries for a Standard finance plan:**

| key | value | value_type | description |
|-----|-------|------------|-------------|
| dashboard | true | boolean | Access to main dashboard |
| reports | true | boolean | Generate financial reports |
| export_pdf | true | boolean | Export reports as PDF |
| api_access | true | boolean | REST API access |
| max_bank_accounts | 5 | integer | Maximum connected bank accounts |
| max_team_members | 3 | integer | Maximum team collaborators |
| priority_support | false | boolean | Priority customer support |
| data_retention_days | 365 | integer | Historical data retention period |

### 3.5 Subscription

The join between a user and a plan. One subscription per user per product.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `user` | ForeignKey(User) | CASCADE, db_index | Subscribed user |
| `plan` | ForeignKey(Plan) | PROTECT, db_index | Current plan (PROTECT prevents deleting active plans) |
| `product` | ForeignKey(Product) | CASCADE, db_index | Cached product reference (denormalized for query speed) |
| `status` | CharField(20) | choices, default "active" | Subscription status |
| `stripe_subscription_id` | CharField(100) | blank, null, unique | Stripe Subscription ID |
| `stripe_customer_id` | CharField(100) | blank, null | Stripe Customer ID |
| `current_period_start` | DateTimeField | | Current billing period start |
| `current_period_end` | DateTimeField | | Current billing period end |
| `trial_start` | DateTimeField | null | Trial period start |
| `trial_end` | DateTimeField | null | Trial period end |
| `canceled_at` | DateTimeField | null | When user canceled (active until period end) |
| `expires_at` | DateTimeField | null | Hard expiration for lifetime plans |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last modification |
| **Unique constraint** | | | `(user, product)` — one subscription per user per product |

**Database table:** `billing_subscription`

**SubscriptionStatus choices:**
```python
class SubscriptionStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    PAST_DUE = "past_due", _("Past Due")
    CANCELED = "canceled", _("Canceled")
    TRIALING = "trialing", _("Trialing")
    PAUSED = "paused", _("Paused")
    EXPIRED = "expired", _("Expired")
```

**Methods:**
- `is_active()` → True if status is active or trialing, and period_end hasn't passed
- `get_access_map()` → Returns `{key: typed_value}` dict from plan's access entries
- `cancel_at_period_end()` → Sets status to canceled, keeps active until period_end
- `reactivate()` → Sets status back to active, clears canceled_at
- `change_plan(new_plan)` → Switches to a different plan within the same product

**Manager methods:**
- `get_active_for_user(user, product)` → Get user's active subscription for a product
- `get_or_create_free(user, product)` → Get existing subscription or create with the product's free plan

---

## 4. Enhanced auth/me Endpoint

The existing `GET /users/me` returns only user profile data. This must be enhanced to include subscription and access information when called from a service domain.

### 4.1 Domain Identification

Service domains identify themselves via a custom header:

```
GET /api/v1/auth/me
Authorization: Bearer <token>
X-Service-Domain: finance.sattabase.tld
```

Alternatively, a `client_id` approach using a registered OAuth-like credential:

```
GET /api/v1/auth/me
Authorization: Bearer <token>
X-Client-ID: sb_finance_prod_a1b2c3
```

**Recommended: X-Service-Domain header** — simpler for internal subdomain architecture. The `client_id` approach adds complexity (secret management, rotation) that isn't needed when all domains are first-party.

### 4.2 New Response Schema: AuthMeSchema

```python
class AccessEntrySchema(Schema):
    key: str
    value: Any          # bool, int, or str depending on value_type
    description: str | None = None

class SubscriptionInfoSchema(Schema):
    plan_name: str
    plan_slug: str
    status: str
    current_period_end: datetime | None = None
    trial_end: datetime | None = None
    is_active: bool

class AuthMeSchema(Schema):
    user: UserOutputSchema
    subscription: SubscriptionInfoSchema | None = None
    access: dict[str, Any]        # flat key-value map from AccessEntry
```

### 4.3 Example Responses

**Request from `finance.sattabase.tld`:**

```json
{
  "user": {
    "id": 1,
    "slug": "a1b2c3d4-...",
    "email": "rahim@example.com",
    "first_name": "Rahim",
    "last_name": "Uddin",
    "phone": "+880...",
    "avatar": "/media/avatars/2026/04/photo.jpg",
    "timezone": "Asia/Dhaka",
    "currency": "BDT",
    "language": "en",
    "is_email_verified": true,
    "is_active": true,
    "role": "member",
    "created_at": "2026-04-27T10:00:00Z",
    "full_name": "Rahim Uddin",
    "display_name": "Rahim"
  },
  "subscription": {
    "plan_name": "Standard",
    "plan_slug": "standard",
    "status": "active",
    "current_period_end": "2026-05-27T00:00:00Z",
    "trial_end": null,
    "is_active": true
  },
  "access": {
    "dashboard": true,
    "reports": true,
    "export_pdf": true,
    "api_access": true,
    "max_bank_accounts": 5,
    "max_team_members": 3,
    "priority_support": false,
    "data_retention_days": 365
  }
}
```

**Same user on `analytics.sattabase.tld` (free plan):**

```json
{
  "user": { "..." : "..." },
  "subscription": {
    "plan_name": "Free",
    "plan_slug": "free",
    "status": "active",
    "is_active": true
  },
  "access": {
    "dashboard": true,
    "reports": false,
    "real_time_data": false,
    "max_dashboards": 2,
    "data_retention_days": 7
  }
}
```

**Request without X-Service-Domain header (plain profile):**

```json
{
  "user": { "..." : "..." },
  "subscription": null,
  "access": {}
}
```

### 4.4 Backend Logic Flow

```python
async def get_auth_me(request):
    # 1. Token already validated by JWTAuth → request.user is set
    user = request.user

    # 2. Check for domain header
    domain = request.headers.get("X-Service-Domain")

    if not domain:
        # No domain → return plain user profile (backward compatible)
        return {"user": user, "subscription": None, "access": {}}

    # 3. Look up service domain → product
    service_domain = await ServiceDomain.objects.filter(
        domain=domain, is_active=True
    ).select_related("product").afirst()
    if not service_domain or not service_domain.product.is_active:
        return {"user": user, "subscription": None, "access": {}}
    product = service_domain.product

    # 4. Get user's subscription for this product (or free plan)
    subscription = await Subscription.get_or_create_free(user, product)
    if not subscription:
        return {"user": user, "subscription": None, "access": {}}

    # 5. Build access map from plan's access entries
    access_map = await subscription.get_access_map()

    return {
        "user": user,
        "subscription": subscription_info,
        "access": access_map,
    }
```

---

## 5. New API Endpoints

### 5.1 Public Endpoints (no auth)

#### Product & Plan Discovery

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| GET | `/billing/products` | List all active products | `list[ProductSchema]` |
| GET | `/billing/products/{slug}` | Get product detail with plans | `ProductDetailSchema` |
| GET | `/billing/products/{slug}/plans` | List plans for a product | `list[PlanSchema]` |

### 5.2 Protected Endpoints (JWT required)

#### Subscription Management

| Method | Path | Description | Request Body | Response |
|--------|------|-------------|--------------|----------|
| GET | `/billing/subscriptions` | List user's all subscriptions | — | `list[SubscriptionSchema]` |
| GET | `/billing/subscriptions/{product_slug}` | Get subscription for a product | — | `SubscriptionDetailSchema` |
| POST | `/billing/subscriptions/{product_slug}/checkout` | Create Stripe checkout session | `{plan_slug, billing_cycle}` | `{checkout_url}` |
| POST | `/billing/subscriptions/{product_slug}/cancel` | Cancel subscription (at period end) | — | `SubscriptionSchema` |
| POST | `/billing/subscriptions/{product_slug}/reactivate` | Reactivate canceled subscription | — | `SubscriptionSchema` |
| POST | `/billing/subscriptions/{product_slug}/change-plan` | Switch to different plan | `{plan_slug}` | `SubscriptionSchema` |

#### Billing Portal

| Method | Path | Description | Response |
|--------|------|-------------|----------|
| POST | `/billing/portal` | Create Stripe Customer Portal session | `{portal_url}` |

### 5.3 Webhook Endpoints (Stripe signature verification)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/billing/webhooks/stripe` | Stripe webhook handler (all events) |

**Handled Stripe events:**
- `checkout.session.completed` — Activate subscription after payment
- `customer.subscription.created` — New subscription
- `customer.subscription.updated` — Plan change, status change
- `customer.subscription.deleted` — Subscription ended
- `customer.subscription.trial_will_end` — Notify user (3 days before trial ends)
- `invoice.payment_failed` — Mark as past_due
- `invoice.payment_succeeded` — Mark as active, update period dates
- `invoice.paid` — Record payment

### 5.4 Admin Endpoints (IsAdmin required)

| Method | Path | Description |
|--------|------|-------------|
| Full CRUD | `/admin/billing/product/` | Product management (Django admin) |
| Full CRUD | `/admin/billing/plan/` | Plan management (Django admin) |
| Full CRUD | `/admin/billing/accessentry/` | Access entry management (Django admin) |
| GET | `/admin/billing/subscriptions/` | View all subscriptions |
| POST | `/admin/billing/subscriptions/{id}/override` | Manually set plan/status |

---

## 6. Payment Integration (Stripe)

### 6.1 Configuration

New environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SF_STRIPE_SECRET_KEY` | Stripe secret key | `sk_live_...` |
| `SF_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (sent to frontend) | `pk_live_...` |
| `SF_STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `whsec_...` |

### 6.2 Checkout Flow

```
User selects plan on service domain
        │
        ▼
Frontend calls POST /billing/subscriptions/{product}/checkout
        │  Body: {plan_slug: "standard", billing_cycle: "monthly"}
        ▼
Backend creates Stripe Checkout Session
        │  - mode: "subscription"
        │  - line_items: [{price: plan.stripe_price_id, quantity: 1}]
        │  - success_url: https://finance.sattabase.tld/billing/success?session_id={CHECKOUT_SESSION_ID}
        │  - cancel_url: https://finance.sattabase.tld/billing/cancel
        │  - metadata: {user_id, product_slug, plan_slug}
        ▼
Return {checkout_url} to frontend
        │
        ▼
Frontend redirects to Stripe Checkout
        │
        ▼
Stripe processes payment
        │
        ▼
Webhook: checkout.session.completed
        │  → Create/update Subscription record
        │  → Set status = active
        ▼
Stripe redirects to success_url
        │
        ▼
Frontend calls auth/me → gets updated access
```

### 6.3 Stripe Customer Management

Each user gets a Stripe Customer record when they first initiate a checkout. The `stripe_customer_id` is stored on the Subscription model for billing portal access.

```
User → first checkout
  → Backend: stripe.Customer.create(email=user.email, metadata={user_id})
  → Store customer_id on subscription
```

### 6.4 Webhook Security

- Webhook endpoint verifies Stripe signature using `SF_STRIPE_WEBHOOK_SECRET`
- All webhook processing is idempotent (safe to receive duplicate events)
- Webhook failures are logged but don't crash the server
- Stripe will retry failed webhook deliveries

---

## 7. Subscription Lifecycle

### State Machine

```
                    ┌──────────────┐
        ┌──────────│    TRIALING   │──────────────┐
        │          └──────┬───────┘               │
        │                 │ Trial ends             │
        │                 │ (payment succeeds)     │
        │                 ▼                        │
   ┌────┴────┐     ┌──────────────┐         ┌─────┴─────┐
   │  PAUSED  │────▶│    ACTIVE    │────────▶│ PAST_DUE  │
   └─────────┘     └──────┬───────┘         └───────────┘
        ▲                │                       │
        │                │ Cancel                 │ Payment
        │                ▼                       │ succeeds
        │          ┌──────────────┐               │
        │          │   CANCELED   │◀──────────────┘
        │          └──────┬───────┘
        │                 │ Period ends
        │                 ▼
        │          ┌──────────────┐
        └──────────│   EXPIRED    │
                   └──────────────┘
```

### State Descriptions

| Status | Description | Access Granted? |
|--------|-------------|-----------------|
| `trialing` | Free trial period — full plan access | Yes (plan access) |
| `active` | Paid subscription, current period valid | Yes (plan access) |
| `past_due` | Payment failed — temporary grace period | Yes (plan access) |
| `canceled` | User canceled — active until period end | Yes (plan access) |
| `paused` | Admin paused — no access | No (free plan access) |
| `expired` | Period ended, not renewed | No (free plan access) |

### Grace Period Logic

When a subscription becomes `past_due` or `canceled`, access continues until `current_period_end`. After that:

1. Celery beat task runs daily: `check_expired_subscriptions()`
2. Finds subscriptions where `status != expired` AND `current_period_end < now()`
3. Sets `status = expired`
4. Optional: send email notification

### Automatic Free Plan Fallback

When a user has no subscription for a product (or their subscription expires), they are automatically assigned the product's free plan. This means:

- New users always get access to the free tier immediately
- Downgrading from paid always returns to free, not to nothing
- Service domains can rely on `auth/me` always returning an `access` map

---

## 8. Service Domain Integration Guide

### 8.1 How a Service Domain Uses Sattabase

Each service domain is a **separate application** (could be any tech stack) that:

1. **Authenticates** users against Sattabase (same JWT flow as current Ledger)
2. **Calls `auth/me`** with the `X-Service-Domain` header
3. **Reads the `access` map** to determine feature availability
4. **Redirects to Sattabase** for billing/plan changes

### 8.2 Minimal Integration Example (JavaScript)

```typescript
// Service domain's auth library
async function getUserAccess() {
  const response = await fetch('https://sattabase.tld/api/v1/auth/me', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'X-Service-Domain': 'finance.sattabase.tld'
    }
  })
  const data = await response.json()

  // data.access is your feature map
  if (data.access.reports) {
    showReportsButton()
  }
  if (data.access.max_bank_accounts) {
    disableAddAccountWhen(data.bankAccountCount >= data.access.max_bank_accounts)
  }
}
```

### 8.3 Plan Change / Upgrade Flow

```
User clicks "Upgrade" on service domain
        │
        ▼
Redirect to Sattabase billing page (or modal):
  https://sattabase.tld/billing/finance/upgrade
        │  (pre-authenticated via JWT in URL or session)
        ▼
User selects new plan → Stripe checkout
        │
        ▼
Webhook updates subscription
        │
        ▼
User returns to service domain → auth/me reflects new plan
```

### 8.4 CORS Configuration

Sattabase must allow cross-origin requests from all registered service domains:

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://sattabase.tld",
    "https://finance.sattabase.tld",
    "https://analytics.sattabase.tld",
    # ... dynamically managed
]

# Or use CORS_ALLOW_ALL_ORIGINS in development
```

---

## 9. Admin Interface ⚠️ 1/2

### Django Admin Panels ✅

| Model | Fields Shown | Actions | Status |
|-------|-------------|---------|--------|
| Product | name, domain, slug, is_active | Activate/Deactivate, View Plans | ✅ Registered |
| Plan | name, product, price, billing_cycle, is_active, is_featured | Activate/Deactivate, View Access Entries, Duplicate Plan | ✅ Registered |
| AccessEntry | plan, key, value, value_type, description | Edit, Delete | ✅ Registered |
| Subscription | user, plan, product, status, current_period_end | Cancel, Override Plan, Extend Period | ✅ Registered |

> **Also registered:** ServiceDomain, WebhookEventLog, Refund, ExchangeRate — 8 model admins total with custom list displays, filters, and inline editors.

### Plan Comparison View (custom admin page) ❌

A custom Django admin view at `/admin/billing/product/{id}/plan-comparison/` that displays a side-by-side table of all plans for a product with their access entries — making it easy to see and manage the feature matrix.

**Status:** Not implemented. ProductAdmin has inlines for PlanInline and ServiceDomainInline but no dedicated comparison URL.

---

## 10. New Celery Tasks ⚠️ 1/5 implemented + 4 additional tasks

### Originally Planned Tasks

| Task | Schedule | Description | Status |
|------|----------|-------------|--------|
| `check_expired_subscriptions` | Daily (midnight) | Expire subscriptions past their period_end | ❌ Not implemented — dunning handles expiry only at day 14 |
| `send_trial_ending_reminder` | Daily | Email users whose trial ends in 3 days | ❌ Not implemented — webhook handler only logs, no email sent |
| `send_subscription_renewal_reminder` | Daily | Email users whose subscription renews in 3 days | ❌ Not implemented — no task or email mechanism |
| `cleanup_stale_webhook_events` | Weekly | Remove processed webhook event logs older than 30 days | ✅ Implemented — `tasks.py` line 410 (weekly, 90-day retention) |
| `sync_stripe_subscriptions` | Hourly | Reconcile local DB with Stripe (catch missed webhooks) | ❌ Not implemented — only `sync_customer_data` exists (customer profile sync, not subscription state) |

### Actually Implemented Tasks (beyond original plan)

| Task | Schedule | Description | Status |
|------|----------|-------------|--------|
| `reconcile_webhooks` | Every 6 hours | Retry failed webhook events (up to 50, max 24h old) | ✅ `tasks.py` line 213 |
| `sync_customer_data` | Daily 3:30 AM UTC | Sync Stripe customer data to local profiles | ✅ `tasks.py` line 238 |
| `dunning_retry` | Daily 4:00 AM UTC | Staged dunning: Day 3 reminder → Day 5 urgent → Day 7 restrict → Day 14 auto-cancel | ✅ `tasks.py` line 296 |
| `update_exchange_rates` | Daily 3:00 AM UTC | Fetch exchange rates (open.er-api.com, fallback: frankfurter.app) | ✅ `tasks.py` line 383 |
| `recognize_revenue` | Daily 2:30 AM UTC | ASC 606 daily revenue recognition for active subscriptions | ✅ `tasks.py` line 447 |

### Still Missing

- [ ] HTML email templates — all emails are plain-text inline f-strings, no template directory
- [ ] `sync_stripe_subscriptions` task — subscription state reconciliation (not just customer profile)
- [ ] Reminder email infrastructure — trial ending, renewal, payment failure notifications

---

## 10.1 Frontend & Operational Feature Gaps

> Audit performed on 2026-05-03. Cross-referencing all backend models, API endpoints, and webhook handlers against the current frontend pages and Vue components revealed the following gaps. These items have backend infrastructure in place but lack user-facing frontend visibility or operational tooling.

### Gap Matrix

| # | Gap | Backend Status | Frontend Status | Severity |
|---|-----|---------------|-----------------|----------|
| G1 | **InvoiceLineItem model missing** | Documented in `dev_docs.md` with 12 fields, migration `0016` referenced, but model does NOT exist in `billing/models.py` | N/A | Critical |
| G2 | **Invoice detail page** | `Invoice` model exists (20 fields, populated by webhooks). `pdf_url`, `stripe_fee_cents`, `discount_cents` all stored locally | Billing history is a flat list pulled live from Stripe API — local `Invoice` model is never queried; no detail/line-item drill-down, no PDF download button | High |
| G3 | **Plans sidebar link broken** | `/dashboard/billing/plans/[slug]` page exists with full `PlanComparison.vue` | `Sidebar.astro` marks Plans as disabled with "Coming Soon" badge — users cannot navigate there from sidebar | High |
| G4 | **Refund management — no admin UI** | `Refund` model (14 fields), `POST /billing/admin/refunds` API, full PCI-DSS audit trail (IP, approval, reason, admin notes) | Zero frontend — no refund creation, no refund history, no approval workflow UI | High |
| G5 | **Plan change history — never shown** | `PlanChangeLog` model auto-created on every plan change (from_plan, to_plan, proration amount, initiator) | Zero frontend — users/admins cannot see plan change history | Medium |
| G6 | **Login history / security audit — invisible** | `UserLoginHistory` model records every login (IP, user agent, timestamp) | Zero frontend — no security log, no "recent logins" view, no device management | Medium |
| G7 | **Admin API endpoints — no UI** | 5 admin endpoints exist: refund, transaction lookup, customer sync, GDPR export, GDPR delete | None are exposed in any frontend page | High |
| G8 | **Webhook monitoring — no admin view** | `WebhookEventLog` model logs every event (id, type, processed status, error, payload). Failed events retried by Celery | No admin dashboard to monitor failed/successful webhooks or trigger manual retries | Medium |
| G9 | **Revenue recognition — no visibility** | `RevenueRecognitionEntry` model + daily Celery task for ASC 606 compliance | No admin dashboard to view recognized revenue, MRR breakdown, or deferred revenue | Medium |
| G10 | **Notification system — placeholder** | No backend notification model, no API endpoints | Navbar bell icon exists with empty dropdown ("No notifications yet") | Low |
| G11 | **Finance features — all disabled** | No backend models for Transactions, Accounts, Budgets, Reports | 4 sidebar menu items disabled with "Soon" badges | Low (future scope) |
| G12 | **PDF download for invoices** | `Invoice.pdf_url` stored in local model and returned by Stripe API | Not rendered in billing history list — only "View" (hosted_url) link shown | Low |
| G13 | **Discount & Stripe fee display** | `Invoice.discount_cents` and `Invoice.stripe_fee_cents` stored locally | Not displayed anywhere in the billing UI | Low |
| G14 | **Exchange rate display** | `ExchangeRate` model populated daily by Celery; used for `?currency=` price conversion | No UI to show exchange rates or allow user to pick display currency (auto-detected only) | Low |

### Detailed Gap Analysis

#### G1: InvoiceLineItem Model — Documented but Not Implemented

**Current state:** `dev_docs.md` describes an `InvoiceLineItem` model with 12 fields (invoice FK, stripe_line_item_id, description, amount_cents, currency, quantity, period_start, period_end, proration, discount_amount_cents, tax_amount_cents, type) and references migration `0016_invoice_line_items.py`. However, the model does NOT exist in `billing/models.py` — zero references in any Python file across the entire codebase. This is a phantom model.

**Impact:** Webhook handlers (`invoice.created`, `invoice.payment_succeeded`) create `Invoice` records but cannot store individual line items. The Stripe API returns line item data (from `invoice.lines.data`), but it is discarded after extracting only the first description.

**Required work:**
1. Create `InvoiceLineItem` model in `billing/models.py` with the 12 documented fields
2. Generate and run migration
3. Update webhook handlers to populate line items when creating/updating `Invoice` records
4. Add admin endpoint `GET /billing/invoices/{invoice_id}` with line items
5. Build frontend invoice detail page (see G2)

#### G2: Invoice Detail Page — Users Can't Drill Into Invoices

**Current state:** `BillingOverview.vue` fetches transaction history directly from Stripe's live API via `get_transaction_history()` and displays a flat list: status, invoice number, amount, tax, period, card brand, and a "View" link (hosted_url). There is no individual invoice detail page, no line item breakdown, and no PDF download button.

Meanwhile, the backend `Invoice` model (20 fields) is populated by webhooks and stores locally: `pdf_url`, `stripe_fee_cents`, `discount_cents`, `attempt_count`, `next_payment_attempt`, `stripe_response` (full JSON). None of this local data is used by the frontend.

**Required work:**
1. Create `GET /billing/invoices/{stripe_invoice_id}` endpoint that queries the local `Invoice` model (with line items once G1 is done) — avoids repeated Stripe API calls
2. Create `/dashboard/billing/invoices/[id].astro` page with `InvoiceDetail.vue` component
3. Display: line items table (description, amount, quantity, period), subtotal, tax, discount, Stripe fee, total, payment method
4. Add PDF download button (link to `invoice.pdf_url`)
5. Add Stripe fee and discount to the billing history list items (G12, G13)
6. Consider switching billing history from Stripe live API to local `Invoice` model for performance

#### G3: Plans Sidebar Link — Page Exists but Navigation Says "Coming Soon"

**Current state:** `Sidebar.astro` has a "Plans" link under BILLING section marked as disabled with a "Coming Soon" tooltip. However, `/dashboard/billing/plans/[slug].astro` page fully exists with `PlanComparison.vue` component — side-by-side plan cards, pricing with currency conversion, proration preview, Stripe checkout, ToS agreement, reactivation flow. The page is fully functional and accessible via direct URL.

**Required work:**
1. Remove `disabled` attribute from Plans sidebar link
2. Set `href` to `/dashboard/billing` (main billing page where products are listed — users click a product to see plans)
3. Remove "Coming Soon" badge
4. Optionally: if multi-product, link to the user's first active product's plan page

#### G4: Refund Management — Full Backend, No Frontend

**Current state:** The `Refund` model has 14 fields including PCI-DSS audit fields (`initiated_by_ip`, `approved_by`, `approved_at`, `admin_notes`, `reason_category`, `stripe_response`). The `POST /billing/admin/refunds` endpoint supports creating refunds with idempotency, caps at invoice `amount_paid`, and supports historical charge refunds. There is no UI for any of this.

**Required work:**
1. Create `/dashboard/admin/refunds.astro` page with `RefundManager.vue` component
2. Refund creation form: select user (by email/user_id), select charge, enter amount and reason
3. Refund history table: all refunds with status (pending/completed/failed), amounts, dates, initiator
4. Approval workflow (if multi-step approval is desired)
5. Refund detail view with full audit trail (who, when, IP, reason, Stripe response)
6. Guard page with admin/superuser role check

#### G5: Plan Change History — Tracked but Never Displayed

**Current state:** `PlanChangeLog` records are auto-created by `confirm_plan_change` and `change_plan` endpoints. Each record has: subscription, from_plan, to_plan, proration_amount_cents, currency, stripe_proration_id, initiated_by, proration_behavior, timestamps. There is no frontend endpoint or page to view this history.

**Required work:**
1. Create `GET /billing/subscriptions/{product_slug}/change-history` endpoint
2. Add a "Plan History" tab/section in `BillingOverview.vue` or a dedicated section on the subscription card
3. Display timeline: date, old plan → new plan, proration amount, who initiated

#### G6: Login History / Security Audit — Tracked but Never Displayed

**Current state:** `UserLoginHistory` records IP address, user agent, and timestamp for every login. There is no API endpoint to list login history and no frontend page to display it.

**Required work:**
1. Create `GET /users/me/login-history` endpoint (paginated, last 50 entries)
2. Add a "Security" or "Login History" section in `SettingsPanel.vue` or create a dedicated page
3. Display: timestamp, IP address, user agent (browser/OS parsed), location (optional, via IP geolocation)
4. "Sign out all other sessions" button (requires token blacklisting logic)

#### G7: Admin API Endpoints — 5 Endpoints With No UI

**Current state:** Five admin-only API endpoints exist but have no frontend exposure:

| Endpoint | Purpose | UI Needed |
|---|---|---|
| `POST /billing/admin/refunds` | Create refund | Covered by G4 |
| `GET /billing/admin/transactions` | View any user's transactions by email/user_id | User lookup + transaction list |
| `POST /billing/admin/sync-customer` | Sync Stripe customer to local profile | Manual sync button per user |
| `GET /billing/admin/gdpr-export/{slug}` | GDPR Article 20 data export | Export button + download |
| `DELETE /billing/admin/gdpr-delete/{slug}` | GDPR data deletion | Delete confirmation with safeguards |

**Required work:**
1. Create `/dashboard/admin/` route group with admin layout
2. Build admin user lookup component (search by email/user_id)
3. Build GDPR tools page with export/delete actions (require double confirmation for delete)
4. Build customer sync action accessible from user detail view
5. Guard all admin routes with role-based access (superuser/staff only)

#### G8: Webhook Monitoring — No Admin Dashboard

**Current state:** `WebhookEventLog` stores every Stripe webhook with event_id, event_type, processed status, error_message, payload JSON. Failed events are retried by `reconcile_webhooks` Celery task (every 6 hours). There is no admin view to monitor this.

**Required work:**
1. Create `GET /billing/admin/webhooks` endpoint (list, filter by status/type)
2. Create admin webhook monitoring page: table of events, success/fail indicators, error messages
3. Manual retry button for failed events
4. Filter by event type (e.g., only show failed `invoice.payment_failed`)
5. Payload inspector (expandable JSON view)

#### G9: Revenue Recognition — No Visibility

**Current state:** `RevenueRecognitionEntry` model + daily Celery task (`recognize_revenue`) handles ASC 606-compliant revenue recognition for active subscriptions. No admin can view this data.

**Required work:**
1. Create `GET /billing/admin/revenue` endpoint (summary + detailed entries)
2. Create admin revenue dashboard: MRR, recognized vs deferred, by-plan breakdown
3. Date range filter and export to CSV

#### G10: Notification System — Placeholder Only

**Current state:** Navbar has a bell icon with a dropdown that permanently shows "No notifications yet." No backend notification model, no API, no real-time push.

**Required work:**
1. Design notification model (type, title, message, read status, user FK, related object FK)
2. Create CRUD API endpoints
3. Connect to existing events (payment failed, subscription canceled, plan changed, trial ending)
4. Replace placeholder dropdown with real notification list + unread badge count
5. Optional: WebSocket for real-time push

#### G11–G14: Minor Gaps

- **G11 (Finance features):** Future scope — no backend models. Sidebar items are aspirational placeholders for the Ledger product itself.
- **G12 (PDF download):** Add a download icon button next to "View" link in billing history, linking to `tx.pdf_url`.
- **G13 (Discount & fee display):** Add `tx.discount` and Stripe fee (not currently in `TransactionItemSchema`) to the billing history list and invoice detail.
- **G14 (Exchange rate/currency picker):** Add a currency selector dropdown in the billing page header so users can switch display currency without relying on auto-detection only.

---

## 11. Implementation Phases

> **Legend:** ✅ = Implemented and verified in codebase · ❌ = Not yet implemented
> **Verification date:** 2026-05-03

---

### ✅ COMPLETED WORK (Phases 1–6) — 42 of 53 items done (79%)

---

### Phase 1: Core Models & Admin (Foundation) — 8/9 ✅

**Goal:** Get the data model in place with Django admin for manual management.

- [x] Create `billing` Django app
- [x] Implement `Product` model with admin — `@admin.register(Product)` with fieldsets, inlines, list_display
- [x] Implement `Plan` model with admin — `@admin.register(Plan)` with AccessEntryInline, duplicate action
- [x] Implement `AccessEntry` model with admin — `@admin.register(AccessEntry)` with product/plan/type filters
- [x] Implement `Subscription` model with admin — `@admin.register(Subscription)` with cancel/expire/activate actions
- [x] Write database migrations — 13 migrations (0001–0013)
- [x] Register all models in Django admin with custom list displays — 8 model admins total
- [x] Seed initial Product + Plans + AccessEntries via fixtures/data migration — `billing_seed_data` management command (2 products, 6 plans)
- [ ] Add plan comparison admin view — No custom admin URL/view for side-by-side plan comparison in Django admin

**Deliverable:** ✅ Admin can create products, plans, and access entries via Django admin UI. (plan comparison view pending)

---

### Phase 2: Enhanced auth/me Endpoint — 4/4 ✅

**Goal:** Service domains can authenticate and receive domain-specific access maps.

- [x] Create `AuthMeSchema` (user + subscription + access) — `billing/schemas.py` line 194
- [x] Create `SubscriptionInfoSchema` — `billing/schemas.py` line 137
- [x] Implement `BillingService.get_user_subscription_for_domain()` — `services.py` line 462
- [x] Enhance `GET /billing/auth/me` to:
  - [x] Read `X-Service-Domain` header
  - [x] Look up product by domain
  - [x] Get/create free subscription
  - [x] Build access map from plan's AccessEntry records
  - [x] Return full `AuthMeSchema`
- [x] Add `BillingController` with auth/me endpoint — `BillingProtectedController` in `controllers.py` line 307

**Deliverable:** ✅ `auth/me` returns subscription + access data when domain header is present.

---

### Phase 3: Stripe Integration — 10/10 ✅

**Goal:** Users can subscribe to paid plans via Stripe checkout.

- [x] Install `stripe` Python package — `stripe==15.1.0`
- [x] Add Stripe env variables to settings — 10 variables in `settings.py` lines 396–417
- [x] Implement `StripeService`:
  - [x] `create_checkout_session()` — `stripe/checkout.py` line 55
  - [x] `create_customer()` / `retrieve_customer()` — `stripe/customer.py`
  - [x] `create_portal_session()` — `stripe/portal.py` line 13
  - [x] `handle_webhook_event()` — `webhooks/router.py` with 11 event handlers
- [x] Implement webhook endpoint `POST /billing/webhooks/stripe`
  - [x] Signature verification — `stripe/client.py`
  - [x] Event routing (checkout.completed, subscription.*, invoice.*, charge.refunded, customer.updated)
  - [x] Idempotent processing — `WebhookEventLog` with unique `event_id`
- [x] Implement checkout controller: `POST /billing/subscriptions/{product}/checkout` — `controllers.py` line 663
- [x] Implement portal controller: `POST /billing/portal` — `controllers.py` line 867

**Deliverable:** ✅ Users can subscribe via Stripe, webhooks update subscription status.

---

### Phase 4: Subscription Management Endpoints — 7/7 ✅

**Goal:** Users can manage their subscriptions (cancel, reactivate, change plan).

- [x] Implement `GET /billing/subscriptions` — list user's subscriptions — `controllers.py` line 328
- [x] Implement `GET /billing/subscriptions/{product}` — subscription detail — `controllers.py` line 397
- [x] Implement `POST /billing/subscriptions/{product}/cancel` — cancel at period end — `controllers.py` line 427
- [x] Implement `POST /billing/subscriptions/{product}/reactivate` — uncancel — `controllers.py` line 476
- [x] Implement `POST /billing/subscriptions/{product}/change-plan` — plan upgrade/downgrade — `controllers.py` line 519
- [x] Safe plan change with preview + HMAC token — preview at line 898, confirm at line 968, 10-min TTL
- [x] Public plan listing: `GET /billing/products/{slug}/plans` with `?currency=` param — `controllers.py` line 250

**Deliverable:** ✅ Full subscription lifecycle management via API.

---

### Phase 5: Automation & Notifications — 6/10 ⚠️

**Goal:** Background tasks handle expiry, reminders, and reconciliation.

- [x] Register all tasks with django-celery-beat schedules — 6 tasks in `celery.py` beat_schedule
- [x] Implement `cleanup_stale_webhook_events` task — `tasks.py` line 410 (weekly, 90-day retention)
- [x] Implement `recognize_revenue` task — `tasks.py` line 447 (daily ASC 606 compliance)
- [x] Implement `update_exchange_rates` task — `tasks.py` line 383 (daily, with fallback API)
- [x] Implement `reconcile_webhooks` task — `tasks.py` line 213 (every 6h, retries failed events)
- [x] Implement `sync_customer_data` task — `tasks.py` line 238 (daily, syncs Stripe customer profiles)
- [ ] Implement `check_expired_subscriptions` Celery task — no standalone task; dunning handles expiry only at day 14
- [ ] Implement `send_trial_ending_reminder` Celery task — webhook handler only logs, no email sent
- [ ] Implement `send_subscription_renewal_reminder` Celery task — no task or email mechanism
- [ ] Implement `sync_stripe_subscriptions` task — only customer profile sync exists, not subscription state sync
- [ ] Implement email templates for subscription notifications — all emails are plain-text inline f-strings, no HTML templates

**Deliverable:** ⚠️ Partial — webhook retry, revenue recognition, and cleanup are automated. Missing: standalone expiry checker, reminder emails, HTML templates.

---

### Phase 6: Frontend (Sattabase Billing UI) — 5/6 ✅

**Goal:** Sattabase has its own UI for billing management.

- [x] Billing page: show current subscriptions across all products — `BillingOverview.vue` with stats, cards, actions
- [x] Plan selection page per product (comparison table) — `PlanComparison.vue` with pricing, features, ToS
- [x] Upgrade/downgrade flow — proration preview modal → HMAC-confirmed plan change or Stripe checkout
- [x] Invoice/payment history — Stripe-sourced transaction list with pagination, status, card brand
- [x] Billing portal redirect (Stripe-hosted) — `createPortalSession()` → redirect + success toast
- [ ] Admin dashboard: subscription metrics, MRR, churn — no admin dashboard page exists

**Deliverable:** ✅ Full user-facing billing UI. (admin metrics dashboard pending → moved to Phase 9)

---

### ❌ PENDING WORK (Phases 7–10) — From Gap Audit (Section 10.1)

> The following phases address gaps identified in the 2026-05-03 audit. None are started.

---

### Phase 7: Invoice Detail & Line Items (G1 + G2 + G12 + G13)

**Goal:** Users can view detailed invoice breakdowns with line items, download PDFs, and see fees/discounts.

**Prerequisites:** G1 (InvoiceLineItem model) must be implemented first.

- [ ] Create `InvoiceLineItem` model in `billing/models.py` (12 fields as documented in dev_docs.md)
- [ ] Generate and run migration for `InvoiceLineItem`
- [ ] Update `handle_invoice_created` and `handle_invoice_payment_succeeded` webhook handlers to populate line items from `invoice.lines.data`
- [ ] Create `GET /billing/invoices/{stripe_invoice_id}` endpoint (queries local model with line items, not live Stripe)
- [ ] Create `/dashboard/billing/invoices/[id].astro` page with `InvoiceDetail.vue` component
- [ ] Invoice detail displays: line items table (description, amount, quantity, period), subtotal, tax, discount, Stripe fee, total, payment method, attempt count
- [ ] Add PDF download button linking to `invoice.pdf_url`
- [ ] Update billing history list in `BillingOverview.vue`: add PDF download icon, discount amount, Stripe fee
- [ ] Update `TransactionItemSchema` in `billing.ts` to include `discount` and `stripe_fee` fields
- [ ] Consider switching billing history from Stripe live API to local `Invoice` model for better performance

**Deliverable:** Clickable invoice list → full invoice detail page with line items and PDF download.

### Phase 8: History & Security Visibility (G5 + G6)

**Goal:** Users and admins can view plan change history and login security audit trails.

- [ ] Create `GET /billing/subscriptions/{product_slug}/change-history` endpoint (paginated)
- [ ] Add "Plan History" timeline section to `BillingOverview.vue` subscription card (date, old plan → new plan, proration, initiator)
- [ ] Create `GET /users/me/login-history` endpoint (paginated, last 50 entries)
- [ ] Add "Login History" section to `SettingsPanel.vue` (timestamp, IP, user agent/browser)
- [ ] Optional: "Sign out all other sessions" button (extend token blacklisting)
- [ ] Optional: IP geolocation for login history entries

**Deliverable:** Users can see their plan change timeline and login security history.

### Phase 9: Admin Panel & Operational Tools (G4 + G7 + G8 + G9)

**Goal:** Admins have a full UI for refunds, user management, webhook monitoring, GDPR compliance, and revenue reporting.

**Prerequisites:** Phase 7 (invoice detail) should be completed first for full transaction context.

- [ ] Create `/dashboard/admin/` route group with admin-only layout (role guard: superuser/staff)
- [ ] Build admin user lookup component (search by email or user_id)
- [ ] Build refund management page (`RefundManager.vue`): creation form, history table, detail view with audit trail, approval workflow
- [ ] Build admin transaction viewer: search any user's billing history
- [ ] Build GDPR tools page: data export (download JSON/CSV) and data deletion (double confirmation)
- [ ] Build webhook monitoring page: event list with filters (status, type), error messages, manual retry, payload inspector (expandable JSON)
- [ ] Create `GET /billing/admin/webhooks` endpoint (list, filter by processed/event_type)
- [ ] Create `GET /billing/admin/revenue` endpoint (summary + detail with date range filter)
- [ ] Build revenue recognition dashboard: MRR chart, recognized vs deferred, by-plan breakdown, CSV export
- [ ] Add customer sync action to user detail view (`POST /billing/admin/sync-customer`)
- [ ] Add admin navigation items to sidebar (only visible for admin/staff roles)

**Deliverable:** Full admin panel for billing operations, compliance, and monitoring.

### Phase 10: UX Polish & Quick Wins (G3 + G10 + G11 + G14)

**Goal:** Fix broken navigation, replace placeholder UI, and improve user experience.

- [ ] **G3:** Fix Plans sidebar link — remove `disabled` attribute, remove "Coming Soon" badge, set `href` to `/dashboard/billing`
- [ ] **G10:** Implement notification system:
  - [ ] Create `Notification` model (type, title, message, read, user FK, related object FK)
  - [ ] Create CRUD API endpoints (`GET /notifications`, `POST /notifications/{id}/read`, `POST /notifications/read-all`)
  - [ ] Connect to billing events (payment failed, subscription canceled, plan changed, trial ending)
  - [ ] Replace Navbar placeholder dropdown with real notification list + unread count badge
  - [ ] Optional: WebSocket for real-time push notifications
- [ ] **G14:** Add currency selector dropdown in billing page header (query `ExchangeRate` model, apply `?currency=` to plan API calls)
- [ ] **G11:** Leave Finance sidebar items as disabled "Soon" badges (future scope — no backend models yet)

**Deliverable:** Plans accessible from sidebar, real notifications, currency picker, all placeholders replaced.

---

## 12. File Structure (New Files)

```
backend/
├── billing/                         # NEW app
│   ├── __init__.py
│   ├── models.py                    # Product, Plan, AccessEntry, Subscription, Invoice,
│   │                                 #   InvoiceLineItem, Refund, PlanChangeLog, etc.
│   ├── schemas.py                   # Pydantic schemas for billing
│   ├── services.py                  # BillingService, StripeService
│   ├── controllers.py               # BillingController (public + protected + admin)
│   ├── admin.py                     # Django admin registration
│   ├── tasks.py                     # Celery tasks
│   ├── stripe/                      # Stripe integration module
│   │   ├── __init__.py              # Core Stripe functions
│   │   ├── checkout.py              # Checkout session creation
│   │   └── webhooks/                # Webhook handlers
│   │       ├── router.py
│   │       └── handlers/
│   ├── migrations/
│   └── tests/
│
├── users/
│   ├── controllers.py               # Auth + user management endpoints
│   ├── models.py                    # User, UserLoginHistory
│   └── ...
│
└── common/
    └── permissions.py               # IsSubscribed, HasAccess("reports")

frontend/src/
├── pages/
│   ├── auth/                        # Login, Register, ForgotPassword, VerifyEmail, EmailChange
│   └── dashboard/
│       ├── index.astro              # DashboardHome
│       ├── profile.astro            # ProfileCard
│       ├── settings.astro           # SettingsPanel
│       ├── billing/
│       │   ├── index.astro          # BillingOverview
│       │   ├── plans/[slug].astro   # PlanComparison
│       │   └── invoices/[id].astro  # InvoiceDetail (Phase 7 — NEW)
│       └── admin/                   # Phase 9 — NEW
│           ├── index.astro          # Admin dashboard
│           ├── refunds.astro        # RefundManager
│           ├── users.astro          # User lookup + transaction viewer
│           ├── webhooks.astro       # Webhook monitoring
│           ├── revenue.astro        # Revenue recognition dashboard
│           └── gdpr.astro           # GDPR export/delete tools
│
├── components/
│   ├── vue/
│   │   ├── LoginForm.vue
│   │   ├── RegisterForm.vue
│   │   ├── ForgotPasswordForm.vue
│   │   ├── VerifyEmailForm.vue
│   │   ├── EmailChangeConfirm.vue
│   │   ├── DashboardHome.vue
│   │   ├── ProfileCard.vue
│   │   ├── SettingsPanel.vue
│   │   ├── BillingOverview.vue
│   │   ├── PlanComparison.vue
│   │   ├── InvoiceDetail.vue        # Phase 7 — NEW
│   │   ├── RefundManager.vue        # Phase 9 — NEW
│   │   ├── AdminUserLookup.vue      # Phase 9 — NEW
│   │   ├── WebhookMonitor.vue       # Phase 9 — NEW
│   │   ├── RevenueDashboard.vue     # Phase 9 — NEW
│   │   ├── GdprTools.vue            # Phase 9 — NEW
│   │   └── NotificationDropdown.vue # Phase 10 — NEW
│   ├── astro/
│   │   ├── Navbar.astro
│   │   ├── Sidebar.astro
│   │   ├── EmptyState.astro
│   │   └── LoadingSpinner.astro
│   └── AdminLayout.astro            # Phase 9 — NEW
│
├── lib/
│   ├── api.ts                       # Core HTTP client + JWT token management
│   ├── auth.ts                      # Auth API functions
│   ├── billing.ts                   # Billing API functions
│   ├── admin.ts                     # Admin API functions (Phase 9 — NEW)
│   └── toast.ts                     # Toast notification system
│
└── styles/
    └── global.css                   # Tailwind + custom CSS variables
```

---

## 13. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Separate `billing` app | Keeps subscription logic isolated from user auth; can be extended independently |
| `X-Service-Domain` header | Simpler than OAuth client_id for first-party subdomains; no secret rotation needed |
| Access entries as key-value | Maximum flexibility — each product defines its own access keys without schema changes |
| `value_type` on AccessEntry | Enables proper type casting (boolean, integer) so frontend doesn't have to parse strings |
| Denormalized `product` on Subscription | Avoids extra JOIN on every `auth/me` call |
| PROTECT on Plan FK in Subscription | Prevents accidental deletion of plans that have active subscribers |
| One subscription per user per product | Simplifies logic — no need to handle "which subscription is current?" |
| Free plan auto-creation | Every user always has access to something — no null subscription states |
| Celery for lifecycle tasks | Stripe webhooks are the primary trigger, but Celery provides safety net for missed webhooks |
| Django admin for plan management | No need to build a custom admin UI immediately — Django admin is sufficient |
| Stripe Checkout (not Elements) | Hosted checkout page is simpler, more secure, handles SCA/3DS automatically |

---

## 14. Security Considerations

| Concern | Mitigation |
|---------|------------|
| Domain spoofing (fake X-Service-Domain) | Validate domain against registered products table; return empty access for unknown domains |
| Webhook forgery | Stripe signature verification on every webhook call |
| Access escalation | Backend always computes access from plan entries; frontend access checks are UI-only |
| Subscription tampering | Plan FK is PROTECT; only Stripe webhooks and admin can change subscription status |
| CORS abuse | `CORS_ALLOWED_ORIGINS` restricted to registered domains |
| Rate limiting on billing endpoints | Apply existing Redis-based rate limiting to checkout/portal/cancel endpoints |
| Webhook replay | Stripe `evt_id` is stored in `WebhookEventLog` — duplicate events are skipped |
