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

### 3.1 Product

Represents a service domain. Each product maps to exactly one subdomain or custom domain.

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `name` | CharField(100) | unique | Display name, e.g. "Satta Finance" |
| `slug` | SlugField(50) | unique, db_index | URL-safe identifier, e.g. "finance" |
| `domain` | CharField(255) | unique, db_index | Service domain, e.g. "finance.sattabase.tld" |
| `description` | TextField | blank | Product description |
| `is_active` | BooleanField | default True | Whether product is accepting new signups |
| `icon` | ImageField | blank, null | Product icon/logo |
| `home_url` | URLField | blank | Landing page URL |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last modification |

**Database table:** `billing_product`

**Methods:**
- `get_free_plan()` → Returns the plan where `price=0` for this product
- `get_plans()` → Returns ordered queryset of active plans (by price ascending)

### 3.2 Plan

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

### 3.3 AccessEntry

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

### 3.4 Subscription

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

    # 3. Look up product by domain
    product = await Product.objects.filter(domain=domain, is_active=True).afirst()
    if not product:
        return {"user": user, "subscription": None, "access": {}}

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

## 9. Admin Interface

### Django Admin Panels

| Model | Fields Shown | Actions |
|-------|-------------|---------|
| Product | name, domain, slug, is_active | Activate/Deactivate, View Plans |
| Plan | name, product, price, billing_cycle, is_active, is_featured | Activate/Deactivate, View Access Entries, Duplicate Plan |
| AccessEntry | plan, key, value, value_type, description | Edit, Delete |
| Subscription | user, plan, product, status, current_period_end | Cancel, Override Plan, Extend Period |

### Plan Comparison View (custom admin page)

A custom Django admin view at `/admin/billing/product/{id}/plan-comparison/` that displays a side-by-side table of all plans for a product with their access entries — making it easy to see and manage the feature matrix.

---

## 10. New Celery Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `check_expired_subscriptions` | Daily (midnight) | Expire subscriptions past their period_end |
| `send_trial_ending_reminder` | Daily | Email users whose trial ends in 3 days |
| `send_subscription_renewal_reminder` | Daily | Email users whose subscription renews in 3 days |
| `cleanup_stale_webhook_events` | Weekly | Remove processed webhook event logs older than 30 days |
| `sync_stripe_subscriptions` | Hourly | Reconcile local DB with Stripe (catch missed webhooks) |

---

## 11. Implementation Phases

### Phase 1: Core Models & Admin (Foundation)

**Goal:** Get the data model in place with Django admin for manual management.

- [ ] Create `billing` Django app
- [ ] Implement `Product` model with admin
- [ ] Implement `Plan` model with admin
- [ ] Implement `AccessEntry` model with admin
- [ ] Implement `Subscription` model with admin
- [ ] Write database migrations
- [ ] Register all models in Django admin with custom list displays
- [ ] Add plan comparison admin view
- [ ] Seed initial Product + Plans + AccessEntries via fixtures/data migration

**Deliverable:** Admin can create products, plans, and access entries via Django admin UI.

### Phase 2: Enhanced auth/me Endpoint

**Goal:** Service domains can authenticate and receive domain-specific access maps.

- [ ] Create `AuthMeSchema` (user + subscription + access)
- [ ] Create `SubscriptionInfoSchema`
- [ ] Implement `BillingService.get_user_subscription_for_domain()`
- [ ] Enhance `GET /auth/me` (or create new `GET /billing/auth/me`) to:
  - Read `X-Service-Domain` header
  - Look up product by domain
  - Get/create free subscription
  - Build access map from plan's AccessEntry records
  - Return full `AuthMeSchema`
- [ ] Add `BillingController` with auth/me endpoint
- [ ] Update `dev_docs.md` with new endpoint documentation

**Deliverable:** `auth/me` returns subscription + access data when domain header is present.

### Phase 3: Stripe Integration

**Goal:** Users can subscribe to paid plans via Stripe checkout.

- [ ] Install `stripe` Python package
- [ ] Add Stripe env variables to settings
- [ ] Implement `StripeService`:
  - `create_checkout_session()` — create Stripe Checkout
  - `create_customer()` — create/retrieve Stripe Customer
  - `create_portal_session()` — create Customer Portal session
  - `handle_webhook_event()` — process Stripe events
- [ ] Implement webhook endpoint `POST /billing/webhooks/stripe`
  - Signature verification
  - Event routing (checkout.completed, subscription.*, invoice.*)
  - Idempotent processing
- [ ] Implement checkout controller: `POST /billing/subscriptions/{product}/checkout`
- [ ] Implement portal controller: `POST /billing/portal`
- [ ] Add WebhookEventLog model for debugging

**Deliverable:** Users can subscribe via Stripe, webhooks update subscription status.

### Phase 4: Subscription Management Endpoints

**Goal:** Users can manage their subscriptions (cancel, reactivate, change plan).

- [ ] Implement `GET /billing/subscriptions` — list user's subscriptions
- [ ] Implement `GET /billing/subscriptions/{product}` — subscription detail
- [ ] Implement `POST /billing/subscriptions/{product}/cancel` — cancel at period end
- [ ] Implement `POST /billing/subscriptions/{product}/reactivate` — uncancel
- [ ] Implement `POST /billing/subscriptions/{product}/change-plan` — plan upgrade/downgrade
- [ ] Plan change logic:
  - Same billing cycle: prorate via Stripe
  - Different billing cycle: create new subscription
  - Downgrade: apply at period end
- [ ] Public plan listing: `GET /billing/products/{slug}/plans`

**Deliverable:** Full subscription lifecycle management via API.

### Phase 5: Automation & Notifications

**Goal:** Background tasks handle expiry, reminders, and reconciliation.

- [ ] Implement `check_expired_subscriptions` Celery task
- [ ] Implement `send_trial_ending_reminder` Celery task
- [ ] Implement `send_subscription_renewal_reminder` Celery task
- [ ] Implement `sync_stripe_subscriptions` Celery task
- [ ] Register all tasks with django-celery-beat schedules
- [ ] Implement email templates for subscription notifications
- [ ] Implement `cleanup_stale_webhook_events` task

**Deliverable:** Automated subscription lifecycle management.

### Phase 6: Frontend (Sattabase Billing UI)

**Goal:** Sattabase has its own UI for billing management (optional, can be Django admin only).

- [ ] Billing page: show current subscriptions across all products
- [ ] Plan selection page per product (comparison table)
- [ ] Upgrade/downgrade flow
- [ ] Invoice/payment history
- [ ] Billing portal redirect (Stripe-hosted)
- [ ] Admin dashboard: subscription metrics, MRR, churn

---

## 12. File Structure (New Files)

```
backend/
├── billing/                         # NEW app
│   ├── __init__.py
│   ├── models.py                    # Product, Plan, AccessEntry, Subscription
│   ├── schemas.py                   # Pydantic schemas for billing
│   ├── services.py                  # BillingService, StripeService
│   ├── controllers.py               # BillingController
│   ├── admin.py                     # Django admin registration
│   ├── tasks.py                     # Celery tasks
│   ├── migrations/
│   └── tests/
│
├── users/
│   ├── controllers.py               # MODIFY: enhance auth/me (or keep separate)
│   └── ...
│
└── common/
    └── permissions.py               # ADD: IsSubscribed, HasAccess("reports")
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
