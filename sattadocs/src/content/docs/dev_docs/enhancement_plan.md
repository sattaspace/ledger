---
title: Enhancement plans
description: A reference page in my new Starlight docs site.
---

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

## 2. Completed Work (Phases 1–5)

The following have been fully implemented and are in production code:

### Phase 1: Core Models & Admin — DONE

- `billing` Django app with 12 models
- Django admin with inlines, custom actions, read-only enforcement
- Migrations, plan comparison via admin, seed data ready

### Phase 2: Enhanced auth/me Endpoint — DONE

- `GET /api/v1/billing/auth/me` with `X-Service-Domain` header
- Returns user + subscription + access map (domain-aware)
- Fallback to plain user profile when no domain header

### Phase 3: Stripe Integration — DONE

- Stripe SDK wrapper in `billing/stripe/` (client, customer, checkout, portal, prices, gdpr, webhooks)
- Webhook handler: 10 event types, idempotent processing, signature verification
- Checkout flow with deduplication, ToS tracking
- Customer portal integration

### Phase 4: Subscription Management — DONE

- Full subscription lifecycle: list, detail, cancel, reactivate, checkout, confirm
- Safe plan change: `preview-plan-change` → `preview_token` → `confirm-plan-change`
- Stripe-first mutations with local DB sync via webhooks
- Transaction history, GDPR data export
- Admin endpoints: refund, admin transactions, customer sync

### Phase 5: Automation & Notifications — DONE

- 6 Celery tasks: reconcile webhooks (6hr), exchange rates (daily), customer sync (daily), dunning retry (daily), revenue recognition (daily), webhook cleanup (weekly)
- Dunning workflow: 4-step escalation (3→5→7→14 day stages)
- ASC 606 daily revenue recognition
- Dual-API currency conversion with stale rate alerting

### Current API: 41 Endpoints

| Controller | Auth | Endpoints |
|-----------|------|-----------|
| `AuthController` | Public | 10 (register, login, token, password reset, email verify) |
| `UserController` | JWT | 11 (profile CRUD, avatar, password change, email change, delete account) |
| `BillingPublicController` | Public | 3 (products, plans listing) |
| `BillingProtectedController` | JWT + Verified | 13 (auth/me, subscriptions, checkout, cancel, reactivate, plan change, portal, export) |
| `BillingAdminController` | Staff only | 3 (refund, admin transactions, customer sync) |
| `BillingWebhookController` | Stripe-Sig | 1 (stripe webhook) |

---

## 3. SDK Strategy — Service Domain Integration

### 3.1 Problem Statement

Service domains need to authenticate users and determine what features they can access. Today the only integration method is raw HTTP calls with JWT tokens. Every sister concern must independently implement token management, refresh logic, error handling, domain header injection, and access map parsing.

### 3.2 SDK Scope — Auth + Permissions Only

**Billing, payments, and subscription management are NOT part of the SDK.** Stripe is the single source of truth for all payment state. The Sattabase frontend owns the entire billing UX — checkout, plan changes, cancellations, invoices, refunds. Sister service domains never touch payment flows directly.

```
┌─────────────────────────────────────────────────────────────────┐
│                    SDK Scope (Auth + Access)                    │
│                                                                 │
│  ✅ login / register / logout                                   │
│  ✅ token lifecycle (refresh, verify, blacklist)                 │
│  ✅ auth/me → user + subscription status + access map            │
│  ✅ feature gate helpers (hasAccess, getAccess)                  │
│  ✅ billing redirect helper → send user to Sattabase for plan mgmt│
│  ✅ password reset / email verification flows                    │
│                                                                 │
│  ❌ checkout / plan change / cancel / reactivate                │
│  ❌ invoice listing / transaction history                       │
│  ❌ refund initiation / approval                                │
│  ❌ Stripe Customer Portal                                      │
│  ❌ any payment-related mutation                                 │
└─────────────────────────────────────────────────────────────────┘

When a user needs to manage billing (upgrade, downgrade, cancel, view invoices):
  → SDK provides redirect URL to Sattabase billing page
  → User completes the flow on Sattabase centrally
  → User returns to sister domain
  → Sister domain calls auth/me → access map is updated
```

**Why this scope:**
- Payment state belongs to Stripe + Sattabase only — no partial writes from service domains
- Billing UX is centralized — one place to maintain, one codebase to update
- SDK surface area is small and stable — auth schemas rarely change, billing schemas change often
- Service domains stay simple — they only care about "who is this user?" and "what can they do?"

### 3.3 SDK Architecture Decision

**Approach: Hand-written lightweight SDK with typed clients.**

While Django Ninja generates an OpenAPI spec, the SDK surface is intentionally small (auth + permissions only). A hand-written SDK gives us full control over:
- Token lifecycle management (auto-refresh, retry on 401)
- Domain header injection (`X-Service-Domain`)
- Feature gate helpers (`hasAccess`, `getAccess`)
- Billing redirect URL generation
- Framework-specific integrations (Django middleware, Vue composables)

The OpenAPI spec remains available at `/api/v1/openapi.json` for any service that wants to generate its own client for the full API. The SDK is the **recommended** path for the common auth + permissions use case.

### 3.4 SDK Design — Python Package (`sattabase-sdk`)

A lightweight Python SDK for service domain backends. Handles authentication, token lifecycle, access control, and billing redirects.

#### Package Structure

```
sattabase-sdk/
├── pyproject.toml
├── src/
│   └── sattabase/
│       ├── __init__.py
│       ├── client.py          # SattabaseClient — main entry point
│       ├── auth.py            # Auth methods (login, register, token refresh)
│       ├── access.py          # Permission/access helpers
│       ├── redirect.py        # Billing redirect URL generation
│       ├── exceptions.py      # Typed exceptions
│       ├── models.py          # Pydantic models (mirrors backend schemas)
│       ├── middleware.py      # Django/Flask middleware (auto-auth per request)
│       └── config.py          # Configuration
└── tests/
```

#### Client Interface

```python
from sattabase import SattabaseClient

# Initialize — single config, reused across the app
client = SattabaseClient(
    base_url="https://sattabase.tld/api/v1",
    service_domain="finance.sattabase.tld",  # identifies THIS service
    api_key="sb_live_...",                     # service credential (from admin)
 timeout=10,
)

# ── Auth: Delegate user login (service domain acts as auth proxy) ──
result = await client.auth.login(email="user@example.com", password="...")
# result.access_token, result.refresh_token

# ── Auth Me: Get user + subscription status + access map for THIS domain ──
# Automatically injects X-Service-Domain + X-API-Key headers
auth_me = await client.auth.me(token=result.access_token)
# auth_me.user.email
# auth_me.subscription.plan_name, auth_me.subscription.status
# auth_me.access.reports → True/False
# auth_me.access.max_bank_accounts → 5

# ── Feature Gates: Check permissions ──
if auth_me.has_access("reports"):
    # Show reports
    pass

max_accounts = auth_me.get_access("max_bank_accounts", default=0)

# ── Billing Redirect: Send user to Sattabase for plan management ──
# SDK generates the URL — user leaves sister domain, manages billing on Sattabase,
# then returns. Next auth/me call reflects the change.
billing_url = client.billing.manage_subscription(token, product_slug="finance")
# → "https://sattabase.tld/billing/finance?token=...&return_url=https://finance.sattabase.tld/settings"

upgrade_url = client.billing.upgrade(token, product_slug="finance")
# → "https://sattabase.tld/billing/finance/upgrade?token=...&return_url=..."

# ── Password Reset ──
await client.auth.request_password_reset(email="user@example.com")
await client.auth.confirm_password_reset(email, otp="123456", new_password="...")

# ── Email Verification ──
await client.auth.request_email_verification(email="user@example.com")
await client.auth.confirm_email_verification(email, otp="123456")

# ── Token lifecycle (automatic) ──
# Client handles refresh automatically when token expires
# Stores tokens in provided token store (Redis, DB, session, etc.)
```

#### Token Store Interface

The SDK does NOT dictate how tokens are stored. Each service domain provides a token store:

```python
class TokenStore(Protocol):
    async def get_tokens(self, user_id: str) -> TokenPair | None: ...
    async def set_tokens(self, user_id: str, tokens: TokenPair) -> None: ...
    async def delete_tokens(self, user_id: str) -> None: ...
```

Implementations:
- `RedisTokenStore` — for server-side sessions (Django/Flask backends)
- `CookieTokenStore` — for API-only backends (tokens in httpOnly cookies)
- `DatabaseTokenStore` — for persistent sessions

#### Auto-Refresh Middleware

The client intercepts 401 responses, attempts token refresh, and retries the original request:

```python
# Client config
client = SattabaseClient(
    base_url="...",
    service_domain="...",
    token_store=RedisTokenStore(redis_client),
    auto_refresh=True,          # Enable automatic token refresh
    max_retries=1,              # Retry once after refresh
)
```

#### Error Handling

All SDK methods raise typed exceptions:

```python
from sattabase import SattabaseClient
from sattabase.exceptions import (
    AuthenticationError,    # 401
    ForbiddenError,         # 403
    NotFoundError,          # 404
    ConflictError,          # 409
    RateLimitError,         # 429
    SattabaseError,         # Base — 5xx, network errors
)

try:
    auth_me = await client.auth.me(token)
except AuthenticationError:
    # Token invalid or expired → redirect to login
except RateLimitError as e:
    # e.retry_after → seconds until reset
    pass
```

### 3.5 SDK Design — TypeScript Package (`@sattabase/sdk`)

A lightweight TypeScript SDK for service domain frontends (Astro, Next.js, Vue, React).

#### Package Structure

```
@sattabase/sdk/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts
│   ├── client.ts           # SattabaseClient
│   ├── auth.ts             # Auth methods (login, register, token)
│   ├── access.ts           # Permission/access helpers
│   ├── redirect.ts         # Billing redirect URL generation
│   ├── exceptions.ts       # Typed errors
│   ├── types.ts            # TypeScript interfaces (mirrors backend schemas)
│   ├── storage.ts          # Browser token storage (localStorage, httpOnly cookie)
│   └── vue/
│       └── index.ts        # Vue composable hooks
└── tests/
```

#### Client Interface

```typescript
import { SattabaseClient } from "@sattabase/sdk";

const client = new SattabaseClient({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "finance.sattabase.tld",
  storage: "localStorage", // or "cookie" or custom TokenStore
});

// ── Login ──
await client.auth.login({ email: "user@example.com", password: "..." });
// Token automatically stored

// ── Auth Me (auto-injects token + domain header) ──
const authMe = await client.auth.me();
// authMe.user.email
// authMe.subscription?.plan_name
// authMe.subscription?.status
// authMe.access.reports → true/false
// authMe.access.max_bank_accounts → 5

// ── Feature gate helper ──
if (client.hasAccess("reports")) {
  // Show reports feature
}

const maxAccounts = client.getAccess<number>("max_bank_accounts", 0);

// ── Billing Redirect: Send to Sattabase for plan management ──
// User leaves to manage billing centrally, then returns
const billingUrl = client.billing.manageSubscription({
  productSlug: "finance",
  returnUrl: window.location.href,  // bring user back here
});
window.location.href = billingUrl;
// → "https://sattabase.tld/billing/finance?return_url=https://finance.sattabase.tld/dashboard"

const upgradeUrl = client.billing.upgrade({
  productSlug: "finance",
  returnUrl: window.location.href,
});
window.location.href = upgradeUrl;

// ── Logout ──
await client.auth.logout();
// Clears token, calls server blacklist

// ── Vue Composable ──
import { useAuth, useAccess } from "@sattabase/sdk/vue";

// Reactive auth state — auto-fetches on mount
const { user, subscription, access, loading, error, refetch } = useAuth();

// Feature gate composable
const { hasAccess, getAccess } = useAccess();
const showReports = hasAccess("reports");
const maxAccounts = getAccess<number>("max_bank_accounts", 0);
```

### 3.6 Service Domain Authentication Flow

There are two distinct auth patterns depending on the service domain architecture:

#### Pattern A: Service Domain Has Its Own Backend (Recommended)

The service backend holds user tokens securely (server-side) and proxies requests to Sattabase. The user never sees Sattabase tokens.

```
User Browser → Service Backend → Sattabase API
     │              │                │
     │  Login ──────┤── POST /auth/login (proxy with X-API-Key)
     │              │◄── {access, refresh} (store in Redis)
     │              │
     │  Dashboard ──┤── GET /billing/auth/me (with stored token + X-API-Key)
     │              │◄── {user, subscription, access}
     │              │
     │              │── Return to frontend (no tokens exposed)
     │◄─────────────┘

     User needs to manage billing?
     │
     │── "Upgrade Plan" button
     │◄── SDK generates redirect URL → sattabase.tld/billing/finance?return_url=...
     │── User manages plan on Sattabase
     │── User returns → auth/me refetches → access map updated
```

Benefits: Tokens never touch the browser, can use server-side caching, can add service-specific middleware.

#### Pattern B: Service Domain Is SPA Only (Browser-Side)

The browser holds tokens directly (localStorage/httpOnly cookies) and calls Sattabase API directly with CORS.

```
User Browser → Sattabase API (direct, CORS-enabled)
     │              │
     │── POST /auth/login ──► {access, refresh}
     │◄───────────────────── (store in localStorage)
     │
     │── GET /billing/auth/me ──► {user, subscription, access}
     │◄────────────────────────── (feature gating)
     │
     │── "Upgrade" button ──► redirect to sattabase.tld/billing/finance
     │◄── user returns ──► auth/me refetches → access map updated
```

Benefits: Simpler architecture, no backend needed for auth. Sattabase must allow the service domain origin in CORS.

### 3.7 Service Domain Identity — API Key System

Currently, service domains identify themselves via `X-Service-Domain` header with no credential. This means any client can claim to be any domain. For production security, we need **service credentials**:

#### New Model: `ServiceCredential`

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `name` | CharField(100) | | Human-readable name (e.g. "Finance Backend") |
| `service_domain` | FK(ServiceDomain) | CASCADE, unique | One credential per domain |
| `api_key_hash` | CharField(255) | unique, indexed | SHA-256 hash of the API key (never stored raw) |
| `api_key_prefix` | CharField(8) | indexed | First 8 chars for identification (e.g. `sb_live_a1`) |
| `permissions` | JSONField | default `{}` | Scoped permissions (e.g. `{"auth": true, "billing_read": true}`) |
| `is_active` | BooleanField | default True | Can be revoked instantly |
| `last_used_at` | DateTimeField | null | Audit: when was this key last used |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `created_by` | FK(User) | SET_NULL | Admin who created the key |

#### API Key Auth Flow

```
Service Backend → Sattabase API
        │
        ▼
Headers:
  Authorization: Bearer <user_jwt_token>     (for user-scoped requests)
  X-Service-Domain: finance.sattabase.tld    (domain identification)
  X-API-Key: sb_live_a1b2c3d4...              (service credential — REQUIRED for M2M)
        │
        ▼
Backend validates:
  1. X-API-Key → hash lookup → ServiceCredential → ServiceDomain
  2. ServiceDomain.is_active = True
  3. ServiceDomain.product matches X-Service-Domain (if both provided)
  4. If user JWT present → validate and return user-scoped data
  5. If no user JWT → service-scoped requests only (product/plan listing)
```

#### Key Generation

```python
import secrets, hashlib

def generate_api_key() -> tuple[str, str, str]:
    """
    Returns: (raw_key, prefix, hash)
    raw_key is shown ONCE to admin at creation time.
    hash is stored in DB. prefix is for identification in logs.
    """
    raw = f"sb_live_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]  # "sb_live_a1"
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, key_hash
```

### 3.8 SDK Implementation Plan

| Step | Task | Deliverable |
|------|------|-------------|
| 3.8.1 | Add `ServiceCredential` model + migration | DB table for API keys |
| 3.8.2 | Add API key auth middleware (validate `X-API-Key` header) | Service-to-service auth |
| 3.8.3 | Add API key management endpoints (admin-only: create, revoke, rotate, list) | Admin CRUD for keys |
| 3.8.4 | Build `sattabase-sdk` Python package (auth + access + redirect) | Published to private PyPI |
| 3.8.5 | Build `@sattabase/sdk` TypeScript package (auth + access + redirect + Vue composables) | Published to private npm |
| 3.8.6 | Add `return_url` support to Sattabase billing pages (accept and redirect back) | Seamless billing redirect flow |
| 3.8.7 | Write integration guide for service domains | Documentation |
| 3.8.8 | Add `X-API-Key` requirement to auth/me endpoint (soft deprecation, then enforce) | Security hardening |

### 3.9 Billing Redirect Flow — Detailed

The redirect flow is the bridge between SDK (auth + access) and Sattabase (billing). Here's how it works end-to-end:

```
1. Sister Domain Frontend
   User clicks "Upgrade Plan" button
        │
        ▼
   SDK: client.billing.upgrade({ productSlug, returnUrl })
        │
        ▼
   Generates URL: https://sattabase.tld/billing/{product}/upgrade
        ?token={jwt}                    (auto-appended)
        &return_url={sister_domain_url}  (passed by SDK)
        │
        ▼
2. Sattabase Billing Page (already authenticated via token param)
   - Shows plan comparison for the product
   - User selects plan → Stripe Checkout
   - Checkout completes → webhook updates subscription
   - OR user cancels → no change
        │
        ▼
3. Redirect back to sister domain
   Sattabase redirects to: {return_url}?billing_updated=1
        │
        ▼
4. Sister Domain Frontend
   - Detects `billing_updated` query param
   - Calls client.auth.me() to refresh access map
   - UI updates to reflect new plan/features
```

**What the SDK generates (not the full URL — a helper that builds it):**

```python
# Python
client.billing.manage_subscription(product_slug, return_url)
# → returns URL string

client.billing.upgrade(product_slug, return_url)
# → returns URL string
```

```typescript
// TypeScript
client.billing.manageSubscription({ productSlug, returnUrl })
// → returns URL string

client.billing.upgrade({ productSlug, returnUrl })
// → returns URL string
```

The SDK does NOT make any API call for billing — it only constructs the redirect URL. All billing logic runs on Sattabase.

---

## 4. Admin Interface — Dedicated Staff Dashboard

### 4.1 Problem Statement

Currently admin operations are split between Django admin (`/admin/`) and 3 API endpoints (`/billing/admin/`). Django admin is powerful but not designed for a modern staff workflow. The API endpoints exist but have no dedicated UI. We need a **unified admin interface** accessible via the Sattabase frontend, strictly gated to `is_staff=True` users.

### 4.2 Admin Access Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Sattabase Frontend                     │
│                                                          │
│  /dashboard/*           → Regular user pages             │
│  /admin/*               → Staff-only pages (is_staff)     │
│                                                          │
│  Access Control:                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Middleware / Route Guard                         │   │
│  │  1. Check localStorage token                     │   │
│  │  2. GET /users/me → check user.is_staff          │   │
│  │  3. If not staff → redirect to /dashboard        │   │
│  │  4. If staff → render admin layout               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Sattabase API                          │
│                                                          │
│  /api/v1/billing/admin/*     → Staff-only (is_staff)     │
│  /api/v1/users/*             → Staff can view any user   │
│  /api/v1/billing/products/*  → Staff can manage products │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 4.3 Admin Backend Endpoints

All admin endpoints require `JWTAuth + IsAuthenticated + is_staff=True`. Every mutation is audit-logged via `@log_admin_access` decorator (logs user_id, email, action, IP, path, timestamp).

#### Product Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/products` | Create product |
| `GET` | `/admin/products` | List all products (with plan counts, subscriber counts) |
| `GET` | `/admin/products/{id}` | Product detail with plans + domains |
| `PUT` | `/admin/products/{id}` | Update product |
| `PATCH` | `/admin/products/{id}/toggle` | Activate/deactivate product |
| `DELETE` | `/admin/products/{id}` | Soft-delete product (only if no active subscriptions) |

#### Service Domain Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/products/{product_id}/domains` | Add service domain to product |
| `PUT` | `/admin/domains/{id}` | Update domain (set primary, toggle active) |
| `DELETE` | `/admin/domains/{id}` | Remove domain |

#### Plan Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/products/{product_id}/plans` | Create plan |
| `GET` | `/admin/products/{product_id}/plans` | List plans for product (with access entries) |
| `GET` | `/admin/plans/{id}` | Plan detail with full access matrix |
| `PUT` | `/admin/plans/{id}` | Update plan (name, price, features, etc.) |
| `PATCH` | `/admin/plans/{id}/toggle` | Activate/deactivate plan |
| `PATCH` | `/admin/plans/{id}/feature` | Toggle `is_featured` flag |
| `POST` | `/admin/plans/{id}/duplicate` | Duplicate plan (with all access entries) |
| `DELETE` | `/admin/plans/{id}` | Delete plan (only if no active subscribers) |

#### Access Entry Management

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/plans/{plan_id}/access-entries` | Add access entry |
| `PUT` | `/admin/access-entries/{id}` | Update access entry (key, value, type, description) |
| `DELETE` | `/admin/access-entries/{id}` | Remove access entry |
| `POST` | `/admin/plans/{plan_id}/access-entries/bulk` | Bulk set access entries (replace all) |
| `GET` | `/admin/products/{product_id}/access-matrix` | Feature comparison matrix across all plans |

#### Subscription Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/subscriptions` | List all subscriptions (filterable by product, plan, status) |
| `GET` | `/admin/subscriptions/{id}` | Subscription detail with full history |
| `PATCH` | `/admin/subscriptions/{id}/override` | Override plan, status, period dates (audit logged) |
| `PATCH` | `/admin/subscriptions/{id}/cancel` | Force-cancel subscription |
| `PATCH` | `/admin/subscriptions/{id}/expire` | Force-expire subscription |
| `PATCH` | `/admin/subscriptions/{id}/extend` | Extend billing period |
| `GET` | `/admin/subscriptions/{id}/plan-changes` | Plan change history for subscription |
| `GET` | `/admin/subscriptions/{id}/invoices` | Invoice history for subscription |
| `GET` | `/admin/subscriptions/{id}/refunds` | Refund history for subscription |

#### User Management (Admin View)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/users` | List all users (filterable, searchable, paginated) |
| `GET` | `/admin/users/{id}` | User detail with all subscriptions across products |
| `PATCH` | `/admin/users/{id}/status` | Activate/deactivate user account |
| `PATCH` | `/admin/users/{id}/role` | Change user role (owner/admin/member) |
| `GET` | `/admin/users/{id}/audit` | User audit trail (login history, plan changes, etc.) |

#### Refund Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/refunds` | List all refunds (filterable by status) |
| `POST` | `/admin/subscriptions/{id}/refund` | Initiate refund (existing endpoint) |
| `PATCH` | `/admin/refunds/{id}/approve` | Approve pending refund (two-person rule) |
| `PATCH` | `/admin/refunds/{id}/reject` | Reject pending refund |

#### Service Credential Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/api-keys` | List all service credentials (with domain, last used) |
| `POST` | `/admin/api-keys` | Create new API key (returns raw key ONCE) |
| `PATCH` | `/admin/api-keys/{id}/revoke` | Revoke API key |
| `POST` | `/admin/api-keys/{id}/rotate` | Rotate API key (invalidates old, creates new) |

#### Admin Dashboard / Analytics

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/metrics/overview` | Key metrics: MRR, active subs, churn rate, trial conversions |
| `GET` | `/admin/metrics/revenue` | Revenue breakdown by product, plan, period |
| `GET` | `/admin/metrics/subscriptions` | Subscription funnel: trials, conversions, cancellations |
| `GET` | `/admin/metrics/products` | Per-product metrics: subscriber counts, plan distribution |
| `GET` | `/admin/audit-log` | Admin action audit trail (paginated, filterable) |

#### Webhook Management

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/admin/webhooks` | Recent webhook events (paginated, filterable by type/status) |
| `POST` | `/admin/webhooks/{id}/retry` | Manually retry a failed webhook event |

### 4.4 Admin Frontend — Route Structure

```
/admin
├── /admin/                           → Dashboard (metrics overview)
│
├── /admin/products                   → Product list
│   ├── /admin/products/new           → Create product
│   ├── /admin/products/:id           → Product detail
│   │   ├── /domains                  → Domain management
│   │   ├── /plans                    → Plan list for product
│   │   │   ├── /plans/new            → Create plan
│   │   │   ├── /plans/:planId        → Plan detail + access entries
│   │   │   └── /access-matrix        → Feature comparison matrix
│   │   └── /metrics                  → Product-specific metrics
│
├── /admin/subscriptions              → All subscriptions (global view)
│   ├── /admin/subscriptions/:id      → Subscription detail
│   │   ├── /plan-changes             → Plan change history
│   │   ├── /invoices                 → Invoice history
│   │   └── /refunds                  → Refund history
│
├── /admin/users                      → User list (searchable, filterable)
│   ├── /admin/users/:id              → User detail + all subscriptions
│   └── /admin/users/:id/audit        → User audit trail
│
├── /admin/refunds                    → Refund list
│   └── /admin/refunds/:id            → Refund detail (approve/reject)
│
├── /admin/api-keys                   → Service credential management
│   └── /admin/api-keys/new           → Create new API key
│
├── /admin/webhooks                   → Webhook event log
│
└── /admin/audit-log                  → Admin action audit trail
```

### 4.5 Admin Layout

The admin interface uses a **separate layout** from the regular dashboard. Staff users see a different navigation structure:

```
┌──────────────────────────────────────────────────────────┐
│  Admin Navbar (distinct from user navbar)                  │
│  ┌────────┐  Sattabase Admin     [metrics] [audit] [user] │
│  │  Logo  │                               [staff badge]   │
│  └────────┘                                                │
├──────────┬───────────────────────────────────────────────┤
│          │                                                │
│  Admin   │  Admin Content Area                            │
│  Sidebar │  (tables, forms, charts, detail views)         │
│          │                                                │
│ Products │                                                │
│ Subs     │                                                │
│ Users    │                                                │
│ Refunds  │                                                │
│ API Keys │                                                │
│ Webhooks │                                                │
│ Audit    │                                                │
│          │                                                │
└──────────┴───────────────────────────────────────────────┘
```

Key differences from user dashboard:
- Admin navbar shows staff badge and links to admin audit log
- Admin sidebar has admin-specific navigation (products, subscriptions, users, refunds, etc.)
- No billing/subscription sidebar items for self (admin manages ALL subscriptions)
- Data tables with sorting, filtering, pagination, bulk actions
- Confirmation modals for destructive actions (delete plan, revoke API key, etc.)

### 4.6 Admin API Schemas

All admin request/response schemas follow the existing Pydantic pattern. Key schemas needed:

```python
# Product management
class AdminProductCreateSchema(Schema): ...
class AdminProductUpdateSchema(Schema): ...
class AdminProductListSchema(Schema): ...  # includes plan_count, subscriber_count

# Plan management
class AdminPlanCreateSchema(Schema): ...
class AdminAccessEntryBulkSchema(Schema): ...  # list of {key, value, value_type, description}
class AdminAccessMatrixSchema(Schema): ...  # plans × access keys matrix

# Subscription management
class AdminSubscriptionListSchema(Schema): ...  # includes user info
class AdminSubscriptionOverrideSchema(Schema): ...  # plan_id, status, period dates

# User management
class AdminUserListSchema(Schema): ...  # includes subscription_count, last_active
class AdminUserDetailSchema(Schema): ...  # includes all subscriptions across products

# Metrics
class AdminMetricsOverviewSchema(Schema): ...
class AdminMetricsRevenueSchema(Schema): ...
class AdminMetricsSubscriptionFunnelSchema(Schema): ...

# API Key management
class AdminApiKeyCreateSchema(Schema): ...
class AdminApiKeyOutputSchema(Schema): ...  # prefix, name, domain, last_used, is_active

# Refund management
class AdminRefundApprovalSchema(Schema): ...  # approved: bool, notes: str
```

### 4.7 Admin Frontend Components

Reusable admin UI components (built with Vue + Tailwind, matching existing design system):

| Component | Purpose |
|-----------|---------|
| `AdminDataTable` | Sortable, filterable, paginated data table with bulk actions |
| `AdminStatsCard` | Metric card (label, value, change %, trend icon) |
| `AdminPageHeader` | Page title + breadcrumb + action buttons |
| `AdminConfirmDialog` | Destructive action confirmation modal |
| `AdminFeatureMatrix` | Plan comparison table (rows = access keys, columns = plans) |
| `AdminSubscriptionDetail` | Subscription overview card (status badge, plan, period, user) |
| `AdminAuditTimeline` | Chronological audit event list |
| `AdminApiKeyCard` | API key display with copy-to-clipboard, revoke button |
| `AdminFilterBar` | Reusable filter/search bar for data tables |
| `AdminEmptyState` | Empty state placeholder with CTA |

### 4.8 Admin Permission Model

```python
# Future: Role-based admin permissions (beyond is_staff boolean)
class AdminPermission(models.TextChoices):
    PRODUCTS_READ = "products:read"
    PRODUCTS_WRITE = "products:write"
    PLANS_READ = "plans:read"
    PLANS_WRITE = "plans:write"
    SUBSCRIPTIONS_READ = "subscriptions:read"
    SUBSCRIPTIONS_WRITE = "subscriptions:write"
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    REFUNDS_READ = "refunds:read"
    REFUNDS_WRITE = "refunds:write"
    API_KEYS_READ = "api_keys:read"
    API_KEYS_WRITE = "api_keys:write"
    AUDIT_READ = "audit:read"
    METRICS_READ = "metrics:read"
```

**Phase 1 (current):** Use `is_staff` boolean — all staff can access everything.
**Phase 2 (future):** Add granular admin roles (e.g., "Support" can read subscriptions but not modify products, "Finance" can manage refunds but not users).

---

## 5. Implementation Steps

### Phase 6: Backend Prerequisites for SDK (6.1–6.7 COMPLETE)

**Goal:** Add service-to-service auth infrastructure and billing redirect support to the Sattabase backend.

#### 6.1 Service Credential Model — DONE

- [x] 6.1.1 Create `ServiceCredential` model in `billing/models.py` (after RevenueRecognitionEntry) with fields: `name`, `service_domain` (FK → ServiceDomain, unique, CASCADE), `api_key_hash` (unique, indexed), `api_key_prefix` (indexed), `permissions` (JSONField), `is_active`, `last_used_at`, `created_by` (FK → User, SET_NULL)
- [x] 6.1.2 Add `generate_api_key()` utility function in `common/utils.py` — returns `(raw_key, prefix, sha256_hash)`, format `sb_live_{token_urlsafe(32)}`
- [x] 6.1.3 Run `makemigrations` and `migrate` — **pending (run locally)**
- [x] 6.1.4 Register `ServiceCredential` in `billing/admin.py` — read-only list display, no manual creation (admin uses API endpoint to create)
- [x] 6.1.5 `on_delete=models.CASCADE` on ServiceDomain FK → cascades to credential when domain is deleted
- [ ] 6.1.6 Write unit tests: key generation uniqueness, hash verification, cascade delete — **pending**

#### 6.2 API Key Auth Middleware — DONE

- [x] 6.2.1 Create `common/api_key_auth.py` — `validate_api_key(request)` function that: extracts `X-API-Key` from header, hashes it with SHA-256, looks up `ServiceCredential` by hash, checks `is_active`, sets `request.service_credential` and `request.service_domain_from_key` on the request object
- [x] 6.2.2 Update `last_used_at` on `ServiceCredential` on each valid request (atomic `.update()` to avoid race conditions)
- [x] 6.2.3 Add `IsServiceAuthenticated` permission class in `common/permissions.py` — checks `request.service_credential is not None`
- [x] 6.2.4 Add `API_KEY_ENFORCED` setting in `sattaledger/settings.py` (default `False`) — soft deprecation period
- [x] 6.2.5 When `API_KEY_ENFORCED=False`: validate key if provided, log warning if missing, allow request through. When `True`: reject with `401 UnauthorizedException`
- [x] 6.2.6 Apply API key validation to `BillingProtectedController.get_auth_me()` — `validate_api_key()` called at method level
- [x] 6.2.7 Update `GET /billing/auth/me` to use `request.service_domain_from_key.domain` when credential present, fallback to `X-Service-Domain` header
- [ ] 6.2.8 Write unit tests: valid key, invalid key, revoked key, missing key (both enforced and non-enforced modes), credential–domain mismatch — **pending**

#### 6.3 Admin API Key Management Endpoints — DONE

- [x] 6.3.1 Create `AdminApiKeyController` in `common/controllers.py` — prefix `/admin/api-keys`, auth `JWTAuth + IsAuthenticated + IsAdmin`, auto-discovered by ninja_extra
- [x] 6.3.2 Define schemas in `common/schemas.py`: `ApiKeyCreateInputSchema` (name, service_domain_id), `ApiKeyOutputSchema` (id, name, prefix, service_domain, permissions, is_active, last_used_at, created_at, created_by), `ApiKeyCreateOutputSchema` (includes raw_api_key), `ApiKeyRotateOutputSchema` (includes new_api_key + old_prefix)
- [x] 6.3.3 `GET /admin/api-keys/` — list all credentials with `select_related("service_domain", "created_by")`, filterable by `service_domain_id` and `is_active`, paginated
- [x] 6.3.4 `POST /admin/api-keys/` — validate service_domain_id exists, check uniqueness, generate key, create `ServiceCredential`, return raw key in response (only time it's visible)
- [x] 6.3.5 `PATCH /admin/api-keys/{key_id}/revoke` — set `is_active=False`, log audit action
- [x] 6.3.6 `POST /admin/api-keys/{key_id}/rotate` — revoke old key, generate new key, create new `ServiceCredential` for same domain, return new raw key
- [x] 6.3.7 All mutation endpoints log via logger.info with user_id, email, action, IP, path
- [ ] 6.3.8 Write unit tests: create, list, revoke, rotate, duplicate domain prevention — **pending**

#### 6.4 CORS Configuration for Service Domains — DONE

- [x] 6.4.1 Create `common/cors_middleware.py` — `ServiceDomainCorsMiddleware` that dynamically checks request origin against active `ServiceDomain.domain` table
- [x] 6.4.2 Origins cached with 5-minute TTL via Django cache framework
- [x] 6.4.3 `CORS_ALLOW_ALL_ORIGINS = DEBUG` for local development still works (middleware skips when True)
- [x] 6.4.4 `SECURE_SSL_REDIRECT` and `SECURE_PROXY_SSL_HEADER` already in settings (production block)
- [ ] 6.4.5 Test CORS from a registered service domain origin and an unregistered origin — **pending**

#### 6.5 Billing Redirect Support (return_url) — DONE

- [x] 6.5.1 Backend: `validate_return_url()` in `billing/stripe/checkout.py` — validates URL against registered `ServiceDomain.domain` entries + app's own domain, prevents open redirect
- [x] 6.5.2 Backend: `build_success_url()` and `build_cancel_url()` accept optional `return_url` param, validated before inclusion in Stripe redirect URLs
- [x] 6.5.3 Backend: `CheckoutInputSchema` extended with `return_url` field; `create_checkout` controller passes it to Stripe URL builders
- [x] 6.5.4 Backend: `PortalInputSchema` created; `create_portal` controller validates and passes `return_url` to Stripe portal session
- [x] 6.5.5 Frontend: `BillingOverview.vue` — reads `return_url` from query param or `sessionStorage`, stores across redirect chain
- [x] 6.5.6 Frontend: After checkout success → `confirmCheckout()` → redirect to `{return_url}?billing_updated=1`
- [x] 6.5.7 Frontend: After checkout cancel → redirect to `{return_url}?billing_updated=0`
- [x] 6.5.8 Frontend: After portal session → redirect to `{return_url}?billing_updated=1`
- [x] 6.5.9 Frontend: `PlanComparison.vue` — captures `return_url` from query param, passes to `createCheckout()` API call
- [x] 6.5.10 Frontend: `billing.ts` — `createCheckout()` and `createPortalSession()` accept `returnUrl` parameter
- [ ] 6.5.11 Sister domain SDK must detect `billing_updated` query param and auto-refetch `auth/me` — handled in Phase 7 (SDK)
- [ ] 6.5.12 Test: full round-trip from sister domain → Sattabase billing → back to sister domain with updated access map

#### 6.6 Per-Service-Domain Rate Limiting — DONE

**Problem:** Current rate limiting uses `rl:{action}:{user_id}:{client_ip}`. When a sister domain backend proxies requests to Sattabase, ALL users on that domain share the same server IP. This means one sister domain with 100 active users can exhaust the rate limit bucket for every user on that domain.

**Example:**
```
Finance backend (IP: 10.0.1.5) proxies 50 users' auth/me calls
→ All 50 calls use key: "auth_me:user123:10.0.1.5"
→ Rate limit (default 5/hr) exhausted after 5th user
→ Remaining 45 users get 429 Too Many Requests
```

**Solution:** When a valid `X-API-Key` is present (SDK traffic), use the API key prefix as the rate limit bucket instead of the client IP. This isolates rate limits per service domain.

- [x] 6.6.1 Update `check_rate_limit_or_raise()` in `common/rate_limit.py` — added `_get_sdk_rate_limit_params()` helper; when `request.service_credential` exists, rate limit key uses `rl:{action}:{user_id}:sdk:{api_key_prefix}` instead of `rl:{action}:{user_id}:{client_ip}`; SDK traffic uses separate higher limits
- [x] 6.6.2 Add `RATE_LIMIT_SDK_ATTEMPTS` setting (default: 1000/hr per service domain) — higher than per-IP limits since SDK traffic is server-to-server
- [x] 6.6.3 Add `RATE_LIMIT_SDK_WINDOW` setting (default: 3600 seconds)
- [ ] 6.6.4 Write unit tests: SDK traffic uses api_key_prefix bucket, direct traffic still uses client_ip bucket — **pending**

#### 6.7 User Account Status Enforcement in auth/me — DONE

**Problem:** When a user is deactivated (`is_active=False`) or soft-deleted (`is_deleted=True`) on Sattabase, their JWT may still be valid until it expires (up to 60 minutes). During this window, a sister domain calling `auth/me` with that JWT would still receive user data. This means:
- Deactivated user's records remain accessible on sister domains until JWT expiry
- Deleted user's data could still be served

**Solution:** `auth/me` explicitly checks user account status before returning data. Deactivated/deleted accounts receive a 401 with a specific error code (`account_inactive` / `account_deleted`) so the SDK can force-logout the user. An `account_status` field is also added to the response for defensive checks.

- [x] 6.7.1 Update `get_auth_me()` in `BillingProtectedController` — after JWT validation, check `user.is_deleted` (raise `AccountDeletedException`, code `account_deleted`) and `user.is_active` (raise `AccountInactiveException`, code `account_inactive`); checks happen before any data is returned
- [x] 6.7.2 Add `account_status` field to `AuthMeSchema` — returns `"active"`, `"inactive"`, or `"deleted"` via `_get_account_status()` helper in `BillingService`; included in both sync and async `get_auth_me_data()` response dicts
- [x] 6.7.3 Add `AccountInactiveException` and `AccountDeletedException` in `common/exceptions.py` — both return 401 with distinct error codes for SDK consumers to handle
- [ ] 6.7.4 Write unit tests: auth/me for active user (normal), inactive user (401), deleted user (401), verified vs unverified email — **pending**

#### 6.8 SDK Readiness Summary

The Sattabase backend is ready for SDK development with the following status:

```
┌──────────────────────────────────────────────────────────────────┐
│                    SDK READINESS CHECKLIST                       │
│                                                                  │
│  ✅ User Authentication (JWT login/register)                     │
│  ✅ User Identity (user.id returned in auth/me)                  │
│  ✅ Per-User Record Isolation (sister domain uses user.id as FK) │
│  ✅ Subscription Status per Domain (auth/me domain-aware)        │
│  ✅ Access Map / Feature Gating (plan → access entries)          │
│  ✅ Service Domain Auth (X-API-Key → ServiceCredential)          │
│  ✅ Dynamic CORS (ServiceDomain origins)                         │
│  ✅ Billing Redirect (validate_return_url)                       │
│  ✅ Admin API Key Management (create/revoke/rotate/list)         │
│  ✅ Per-Service-Domain Rate Limiting (6.6)                       │
│  ✅ User Account Status Enforcement (6.7)                        │
│                                                                  │
│  📋 User Lifecycle Webhooks (future — not blocking for MVP)      │
│  📋 ServiceCredential.permissions enforcement (future)           │
└──────────────────────────────────────────────────────────────────┘
```

**Per-user record isolation architecture:**

```
Sattabase (base system)           Sister Domain (e.g. finance app)
┌───────────────────────┐        ┌──────────────────────────────────┐
│ User (id=42)          │◄──FK── │ BankAccount (sattabase_user_id=42)│
│ Subscription          │        │ Transaction (sattabase_user_id=42)│
│ AccessEntry → Plan    │        │ Invoice (sattabase_user_id=42)    │
│ Product/ServiceDomain │        │ ...all records WHERE user_id=42   │
└───────────────────────┘        └──────────────────────────────────┘
      ↑                                  ↑
   SDK calls auth/me              Sister domain uses user.id
   → gets user.id=42              from Sattabase as FK for isolation
```

Each sister concern domain has its OWN database with its OWN models. The SDK provides only the **identity layer** (who is this user?) and **permission layer** (what can they do?). The sister domain is fully responsible for its own data models, record storage, and per-user isolation using the Sattabase `user.id` as a foreign key.

---

### Phase 7: Python SDK (`sattabase-sdk`) — DONE

**Goal:** Build and publish the Python SDK package for service domain backends.

> **Phase 6 context (what already exists on the backend):**
> - `ServiceCredential` model with `api_key_hash`, `api_key_prefix` (12 chars: `sb_live_` + 6), `permissions` (JSONField)
> - `validate_api_key()` in `common/api_key_auth.py` — SHA-256 hash lookup, sets `request.service_credential` and `request.service_domain_from_key`
> - `validate_return_url()` in `billing/stripe/checkout.py` — validates against `ServiceDomain` + `STRIPE_APP_DOMAIN`, cached 5-min
> - `ServiceDomainCorsMiddleware` — `@sync_and_async_middleware` pattern, dynamic CORS from DB
> - `API_KEY_ENFORCED` setting — soft (log warning) vs hard (401) enforcement
> - `AdminApiKeyController` at `/admin/api-keys` — create, list, revoke, rotate
> - `return_url` support in `build_success_url()`, `build_cancel_url()`, `create_portal()` — all backward-compatible (optional param, `None` default)

#### 7.1 Project Scaffolding

- [x] 7.1.1 Create new repo `sattabase-sdk-python` — Done, implemented in-repo at `sdk/python/`
- [x] 7.1.2 Set up `pyproject.toml` with: `hatch` build backend, `httpx` (async HTTP), `pydantic>=2.0` (models), Python 3.10+ support
- [x] 7.1.3 Create package structure: `src/sattabase/` with `__init__.py`, `client.py`, `auth.py`, `access.py`, `redirect.py`, `exceptions.py`, `models.py`, `config.py`, `middleware.py`
- [x] 7.1.4 Create `tests/` directory with `conftest.py`, `test_auth.py`, `test_access.py`, `test_redirect.py`, `test_middleware.py`
- [x] 7.1.5 Set up CI: `pytest`, `ruff` (linting), `mypy` (type checking), `coverage >= 80%`

#### 7.2 Configuration & Client Core

- [x] 7.2.1 Create `config.py` — `SattabaseConfig` dataclass with validated fields:
  - `base_url: str` — Sattabase API base URL (e.g. `https://sattabase.tld/api/v1`)
  - `service_domain: str` — identifies this service domain (e.g. `finance.sattabase.tld`)
  - `api_key: str` — service credential raw key (format: `sb_live_{token_urlsafe(32)}`), SDK stores this in memory, never persists to disk
  - `timeout: float = 10` — HTTP request timeout in seconds
  - `auto_refresh: bool = True` — enable automatic token refresh on 401
  - `max_retries: int = 1` — max retries after token refresh
  - Validation: `api_key` must start with `sb_live_`, `base_url` must be https in non-debug mode
- [x] 7.2.2 Create `exceptions.py` — typed exception hierarchy:
  - `SattabaseError(Exception)` — base, has `status: int`, `message: str`, `detail: Any | None`
  - `AuthenticationError(SattabaseError)` — 401 (invalid/expired token or API key)
  - `ForbiddenError(SattabaseError)` — 403 (insufficient permissions)
  - `NotFoundError(SattabaseError)` — 404
  - `ConflictError(SattabaseError)` — 409
  - `RateLimitError(SattabaseError)` — 429, has `retry_after: int | None` attribute
  - `ValidationError(SattabaseError)` — 422 (invalid request body)
  - `ApiServerError(SattabaseError)` — 5xx + network errors
- [x] 7.2.3 Create `models.py` — Pydantic v2 models that **exactly mirror** the actual backend schemas:
  - `TokenPair(BaseModel)` — fields: `access: str`, `refresh: str` (matches `TokenOutputSchema`)
  - `User(BaseModel)` — matches `UserOutputSchema`: `id: int`, `slug: str`, `email: str`, `first_name: str`, `last_name: str`, `is_active: bool`, `is_verified: bool`, `is_staff: bool`, `date_joined: datetime`, `avatar: str | None`, `currency: str | None`
  - `SubscriptionInfo(BaseModel)` — matches `SubscriptionInfoSchema`: `plan_name: str`, `plan_slug: str`, `status: str`, `current_period_end: datetime | None`, `trial_end: datetime | None`, `is_active: bool`
  - `AuthMeResponse(BaseModel)` — matches `AuthMeSchema`: `user: User`, `subscription: SubscriptionInfo | None`, `access: dict[str, Any]`
  - `MessageResponse(BaseModel)` — `message: str`, `success: bool` (generic response)
  - Add helper methods on `AuthMeResponse`:
    - `has_access(key: str) -> bool` — checks `self.access[key]`, coerces string `"true"`/`"false"` to bool
    - `get_access(key: str, default: Any = None) -> Any` — returns `self.access.get(key, default)`
    - `access_keys: list[str]` — returns `list(self.access.keys())`
- [x] 7.2.4 Create `client.py` — `SattabaseClient` class:
  - `__init__(self, config: SattabaseConfig, token_store: TokenStore | None = None)` — creates `httpx.AsyncClient`, exposes `self.auth`, `self.access`, `self.billing` namespaces
  - Derive `app_base_url` from `config.base_url` (strip `/api/v1` to get `https://sattabase.tld`) for redirect URL construction
  - `async close()` — close httpx client (support `async with` context manager)
- [x] 7.2.5 Build internal `_request()` method:
  - Accepts: `method`, `path`, `token: str | None = None`, `json: dict | None = None`, `**kwargs`
  - Builds full URL: `f"{self.config.base_url}{path}"`
  - Injects headers: `X-API-Key: {api_key}`, `X-Service-Domain: {service_domain}`, `Authorization: Bearer {token}` (if provided), `Content-Type: application/json`
  - Sends request via `self._http_client`
  - On success: returns parsed JSON response body
  - On error: maps HTTP status to typed exception (see 7.2.2), parses error body for `detail`/`message`
  - Logs request/response at DEBUG level (URL, method, status, timing)
- [x] 7.2.6 Implement auto-refresh:
  - When `auto_refresh=True` and a request returns 401:
    1. Check if the failing request had an `Authorization` header (skip for API-key-only requests)
    2. Extract refresh token from `token_store` (if configured)
    3. Call `POST /auth/token/refresh` with `{ refresh: refresh_token }`
    4. If refresh succeeds: update `token_store` with new `TokenPair`, retry original request with new access token
    5. If refresh fails: raise `AuthenticationError("Token refresh failed")`
    6. Use a lock/flag to prevent concurrent refresh requests (multiple 401s should not trigger multiple refreshes)

#### 7.3 Auth Module (`auth.py`)

These methods map 1:1 to the existing `AuthController` endpoints. Each method uses `_request()` internally, which auto-injects `X-API-Key` and `X-Service-Domain`.

- [x] 7.3.1 `auth.login(email: str, password: str) -> TokenPair` → `POST /auth/login` body: `{ email, password }` → returns `TokenPair`
- [x] 7.3.2 `auth.register(email: str, password: str, first_name: str, last_name: str, ...) -> MessageResponse` → `POST /auth/register` → returns `MessageResponse`
- [x] 7.3.3 `auth.me(token: str | None = None) -> AuthMeResponse` → `GET /billing/auth/me`
  - Uses provided `token` or falls back to `token_store.get_tokens()` if configured
  - Injects `Authorization: Bearer {token}` header
  - Backend resolves domain via `X-API-Key` → `ServiceDomain` (priority) or `X-Service-Domain` header (fallback)
  - Returns domain-scoped user + subscription + access map
- [x] 7.3.4 `auth.refresh(refresh_token: str) -> TokenPair` → `POST /auth/token/refresh` body: `{ refresh: refresh_token }`
- [x] 7.3.5 `auth.verify(token: str) -> MessageResponse` → `POST /auth/token/verify` body: `{ token }`
- [x] 7.3.6 `auth.blacklist(refresh_token: str) -> MessageResponse` → `POST /auth/token/blacklist` body: `{ refresh: refresh_token }`
- [x] 7.3.7 `auth.logout(token: str, refresh_token: str) -> None` → calls `blacklist(refresh_token)`, clears `token_store` if configured
- [x] 7.3.8 `auth.request_password_reset(email: str) -> MessageResponse` → `POST /auth/password-reset/request`
- [x] 7.3.9 `auth.confirm_password_reset(email: str, otp: str, new_password: str, confirm_password: str) -> MessageResponse` → `POST /auth/password-reset/confirm`
- [x] 7.3.10 `auth.request_email_verification(email: str) -> MessageResponse` → `POST /auth/verify-email/request`
- [x] 7.3.11 `auth.confirm_email_verification(email: str, otp: str) -> MessageResponse` → `POST /auth/verify-email/confirm`

#### 7.4 Access Module (`access.py`)

Thin wrapper around `AuthMeResponse` helper methods with optional client-side caching.

- [x] 7.4.1 `access.has_access(key: str, token: str | None = None) -> bool`
  - Calls `auth.me(token)` to get latest `AuthMeResponse`
  - Returns `auth_me.has_access(key)`
  - Optional: cache `AuthMeResponse` in memory with configurable TTL (default 60s) to avoid repeated calls
- [x] 7.4.2 `access.get_access(key: str, default: Any = None, token: str | None = None) -> Any`
  - Same pattern, returns `auth_me.get_access(key, default)`
- [x] 7.4.3 `access.keys(token: str | None = None) -> list[str]`
  - Returns `list(auth_me.access.keys())`
- [x] 7.4.4 `access.invalidate_cache()` — clears cached `AuthMeResponse`, forcing next call to re-fetch

#### 7.5 Redirect Module (`redirect.py`)

**Zero API calls.** These methods only construct URL strings. The actual `return_url` validation happens server-side in `validate_return_url()` (Phase 6.5).

- [x] 7.5.1 `billing.manage_subscription(product_slug: str, return_url: str | None = None) -> str`
  - Constructs: `{app_base_url}/billing/{product_slug}?return_url={encoded_return_url}`
  - `app_base_url` derived from `config.base_url` (strip `/api/v1`)
  - `return_url` is URL-encoded. If `None`, Sattabase uses its own default redirect
  - Example output: `https://sattabase.tld/billing/finance?return_url=https%3A%2F%2Ffinance.sattabase.tld%2Fsettings`
- [x] 7.5.2 `billing.upgrade(product_slug: str, return_url: str | None = None) -> str`
  - Constructs: `{app_base_url}/billing/{product_slug}/upgrade?return_url={encoded_return_url}`
- [x] 7.5.3 `billing.portal(return_url: str | None = None) -> str`
  - Constructs: `{app_base_url}/billing/portal?return_url={encoded_return_url}`
- [x] 7.5.4 `billing.detect_billing_update(url: str) -> tuple[bool, int | None]`
  - Utility: parses a URL for `billing_updated` query param
  - Returns `(True, 1)` for `?billing_updated=1`, `(True, 0)` for `?billing_updated=0`, `(False, None)` otherwise
  - Sister domains call this on page load to detect return from billing redirect (Phase 6.5.11)

#### 7.6 Token Store & Middleware

- [x] 7.6.1 Define `TokenStore` protocol in `client.py`:
  ```python
  class TokenStore(Protocol):
      async def get_tokens(self, user_id: str) -> TokenPair | None: ...
      async def set_tokens(self, user_id: str, tokens: TokenPair) -> None: ...
      async def delete_tokens(self, user_id: str) -> None: ...
  ```
- [x] 7.6.2 Implement `RedisTokenStore(redis_client, key_prefix: str = "sb:")`
  - Stores `TokenPair` as JSON in Redis key `{key_prefix}tokens:{user_id}`
  - Configurable TTL (default: 7 days, matching JWT refresh token expiry)
  - `get_tokens` → `redis.get()` → deserialize JSON → `TokenPair`
  - `set_tokens` → serialize to JSON → `redis.setex()`
  - `delete_tokens` → `redis.delete()`
- [x] 7.6.3 Implement `DatabaseTokenStore(session_factory, model: type)`
  - Stores tokens in a database table with columns: `user_id`, `access_token`, `refresh_token`, `expires_at`
  - `model` is a SQLAlchemy/ Django model — the SDK provides a mixin class `TokenStoreMixin` with the required fields
  - `set_tokens` → upsert (create or update), `get_tokens` → select, `delete_tokens` → delete
- [x] 7.6.4 Create `middleware.py` — Django middleware for Pattern A (backend proxy):
  ```python
  class SattabaseAuthMiddleware:
      """Extracts user session, calls auth/me, sets request.sattabase_user + request.sattabase_access."""
      async_capable = True
      sync_capable = True  # Uses @sync_and_async_middleware pattern

      def __call__(self, request):
          # 1. Extract user_id from Django session
          # 2. Get tokens from token_store
          # 3. Call client.auth.me(token) with short cache (per-request)
          # 4. Set request.sattabase_user = auth_me.user
          # 5. Set request.sattabase_access = auth_me.access
          # 6. Set request.sattabase_subscription = auth_me.subscription
          # 7. On failure: set request.sattabase_user = None (graceful degradation)
  ```
  - Also provide a Flask decorator `@sattabase_auth` for non-Django backends
- [x] 7.6.5 Write integration tests:
  - Mock `httpx` responses to simulate Sattabase API
  - Test full login → auth.me → has_access flow
  - Test auto-refresh on 401
  - Test redirect URL construction
  - Test middleware sets correct attributes on request

#### 7.7 Documentation & Publishing

- [x] 7.7.1 Write README.md: quickstart, installation (`pip install sattabase-sdk`), configuration, auth flows, feature gates, billing redirect, token store setup, middleware setup
- [x] 7.7.2 Write integration guide: step-by-step for Django backend (Pattern A with `SattabaseAuthMiddleware`) and for SPA proxy backend (Pattern B)
- [x] 7.7.3 Add `py.typed` marker for PEP 561 compliance
- [x] 7.7.4 Publish to private PyPI (test first, then production)
- [x] 7.7.5 Add `CHANGELOG.md` file

---

### Phase 8: TypeScript SDK (`@sattabase/sdk`) — DONE

**Goal:** Build and publish the TypeScript SDK package for service domain frontends.

> **Phase 6 context (same as Phase 7):**
> - All backend infrastructure is ready: API key auth, CORS, return_url validation
> - The TypeScript SDK mirrors the Python SDK's surface but targets browser environments
> - Python SDK `models.py` → TypeScript `types.ts` must use the same field names as the actual backend schemas

#### 8.1 Project Scaffolding

- [x] 8.1.1 Create new repo `sattabase-sdk-typescript` — Done, implemented in-repo at `sdk/typescript/`
- [x] 8.1.2 Set up `package.json`: name `@sattabase/sdk`, build with `tsup`, dev dependencies: `vitest`, `typescript`, `vue`
- [x] 8.1.3 Create `tsconfig.json` — target ES2020, module ESNext, strict mode, declaration output
- [x] 8.1.4 Create package structure: `src/client.ts`, `src/auth.ts`, `src/access.ts`, `src/redirect.ts`, `src/exceptions.ts`, `src/types.ts`, `src/storage.ts`, `src/vue/index.ts`
- [x] 8.1.5 Create `tests/` with `vitest` setup
- [x] 8.1.6 Set up CI: `vitest`, `eslint`, `prettier`, `typecheck`

#### 8.2 Types & Exceptions

- [x] 8.2.1 Create `types.ts` — TypeScript interfaces that **exactly mirror** the actual backend schemas:
  ```typescript
  // Matches TokenOutputSchema
  interface TokenPair { access: string; refresh: string; }

  // Matches UserOutputSchema
  interface User {
    id: number; slug: string; email: string;
    first_name: string; last_name: string;
    is_active: boolean; is_verified: boolean; is_staff: boolean;
    date_joined: string; avatar: string | null; currency: string | null;
  }

  // Matches SubscriptionInfoSchema
  interface SubscriptionInfo {
    plan_name: string; plan_slug: string; status: string;
    current_period_end: string | null;
    trial_end: string | null;
    is_active: boolean;
  }

  // Matches AuthMeSchema
  interface AuthMeResponse {
    user: User;
    subscription: SubscriptionInfo | null;
    access: Record<string, any>;
  }

  // Generic response
  interface MessageResponse { message: string; success: boolean; }

  // Config
  interface SattabaseConfig {
    baseUrl: string;
    serviceDomain: string;
    apiKey?: string;  // Optional for browser-side (Pattern B may not need it)
    storage?: TokenStore | "localStorage" | "cookie";
    autoRefresh?: boolean;
    timeout?: number;
  }

  // Billing update detection
  type BillingUpdateStatus = { updated: boolean; success: boolean | null };
  ```
- [x] 8.2.2 Create `exceptions.ts` — `SattabaseError` (base, has `status` and `code`) + `AuthenticationError(401)`, `ForbiddenError(403)`, `NotFoundError(404)`, `ConflictError(409)`, `RateLimitError(429, retryAfter?)`

#### 8.3 Storage Layer

- [x] 8.3.1 Create `storage.ts` — `TokenStore` interface:
  ```typescript
  interface TokenStore {
    getTokens(): TokenPair | null;
    setTokens(pair: TokenPair): void;
    clearTokens(): void;
    getAccessToken(): string | null;
    getRefreshToken(): string | null;
  }
  ```
- [x] 8.3.2 Implement `LocalStorageTokenStore` — stores `TokenPair` + `expires_at` in `localStorage` under configurable key prefix (default `sb_auth:`)
  - `setTokens()`: stores `{ access, refresh, expires_at }` as JSON
  - `getTokens()`: parses JSON, checks `expires_at` — returns `null` if expired
  - `clearTokens()`: removes key from localStorage
- [x] 8.3.3 Implement `CookieTokenStore` — stores tokens in cookies
  - Configurable: `httpOnly: boolean`, `secure: boolean`, `sameSite: "Lax" | "Strict" | "None"`, `path: string`
  - `httpOnly=true` means tokens only sent to same-origin API calls (useful for Pattern B backend proxy)
- [x] 8.3.4 Built-in factory: `createDefaultStorage(config)` — returns `LocalStorageTokenStore` or `CookieTokenStore` based on config string `"localStorage"` / `"cookie"`

#### 8.4 Client Core

- [x] 8.4.1 Create `client.ts` — `SattabaseClient` class:
  - Constructor accepts `SattabaseConfig`
  - Initializes storage via `createDefaultStorage(config)` if string, or uses provided `TokenStore` instance
  - Derives `appBaseUrl` from `config.baseUrl` (strip `/api/v1`) for redirect URLs
  - Exposes `this.auth`, `this.access`, `this.billing` as module instances
- [x] 8.4.2 Build internal `_fetch()` method:
  - Builds URL: `${this.config.baseUrl}${path}`
  - Injects headers: `X-Service-Domain: ${config.serviceDomain}`, `X-API-Key: ${config.apiKey}` (if provided)
  - For authenticated requests: reads access token from storage, adds `Authorization: Bearer ${token}`
  - Parses JSON response, maps HTTP status to typed exceptions (same mapping as Python SDK)
  - On 401 + `autoRefresh=true`: attempt refresh, retry once
- [x] 8.4.3 Implement auto-refresh (browser-side):
  - On 401: call `POST /auth/token/refresh` with stored refresh token
  - If success: update storage with new `TokenPair`, retry original request
  - If failure: clear storage, throw `AuthenticationError`
  - Use a promise-based mutex to prevent concurrent refresh (multiple tabs/requests)
- [x] 8.4.4 Expose namespaces: `this.auth` (AuthModule), `this.access` (AccessModule), `this.billing` (RedirectModule)

#### 8.5 Auth Module (`auth.ts`)

- [x] 8.5.1 `auth.login({ email, password }) -> Promise<TokenPair>` — POST, auto-stores tokens in storage, returns `TokenPair`
- [x] 8.5.2 `auth.register({ email, password, first_name, last_name, ... }) -> Promise<MessageResponse>`
- [x] 8.5.3 `auth.me() -> Promise<AuthMeResponse>` — GET, uses stored access token, returns `AuthMeResponse`
- [x] 8.5.4 `auth.refresh() -> Promise<TokenPair>` — POST, updates stored tokens, returns new `TokenPair`
- [x] 8.5.5 `auth.verify() -> Promise<MessageResponse>` — POST, checks if current access token is valid
- [x] 8.5.6 `auth.logout() -> Promise<void>` — blacklist refresh token via API + `storage.clearTokens()`
- [x] 8.5.7 `auth.requestPasswordReset(email)` / `auth.confirmPasswordReset(email, otp, newPassword, confirmPassword)`
- [x] 8.5.8 `auth.requestEmailVerification(email)` / `auth.confirmEmailVerification(email, otp)`
- [x] 8.5.9 `auth.isAuthenticated() -> boolean` — checks if access token exists in storage and `expires_at` has not passed

#### 8.6 Access Module (`access.ts`)

- [x] 8.6.1 `client.hasAccess(key: string) -> Promise<boolean>` — calls `auth.me()` if not cached, checks `access[key]` with boolean coercion (`"true"` → `true`, `"false"` → `false`, truthy/falsy for other types)
- [x] 8.6.2 `client.getAccess<T>(key: string, defaultValue?: T) -> Promise<T>` — typed access to access map values
- [x] 8.6.3 Internal cache: store latest `AuthMeResponse` in memory (module-level variable), invalidate on token change, `logout()`, or explicit `access.invalidate()`

#### 8.7 Redirect Module (`redirect.ts`)

- [x] 8.7.1 `billing.manageSubscription({ productSlug, returnUrl? }) -> string` — builds URL: `{appBaseUrl}/billing/{productSlug}?return_url={encoded}` (no API call)
- [x] 8.7.2 `billing.upgrade({ productSlug, returnUrl? }) -> string` — builds URL: `{appBaseUrl}/billing/{productSlug}/upgrade?return_url={encoded}`
- [x] 8.7.3 `billing.portal({ returnUrl? }) -> string` — builds URL: `{appBaseUrl}/billing/portal?return_url={encoded}`
- [x] 8.7.4 `billing.detectBillingUpdate() -> BillingUpdateStatus` — reads current `window.location.search` for `billing_updated` param, returns `{ updated: true, success: 1 | 0 }` or `{ updated: false, success: null }`. Sister domains call this on mount to detect return from Sattabase billing redirect.

#### 8.8 Vue Composables (`vue/index.ts`) — DONE

- [x] 8.8.1 `useAuth()` composable:
  ```typescript
  const { user, subscription, access, loading, error, refetch } = useAuth();
  ```
  - Auto-fetches `auth.me()` on mount (calls `client.auth.me()`)
  - Returns reactive `ref()` for: `user`, `subscription`, `access`
  - `loading: ComputedRef<boolean>`, `error: Ref<Error | null>`
  - `refetch()` — re-calls `auth.me()`, updates all refs
  - Auto-invalidates on `billing.detectBillingUpdate().updated` (listens to route change or `popstate`)
- [x] 8.8.2 `useAccess()` composable:
  ```typescript
  const { hasAccess, getAccess, accessKeys, loading, refetch } = useAccess();
  ```
  - `hasAccess(key)` — reactive boolean, auto-fetches `auth.me()` on first call
  - `getAccess<T>(key, defaultValue?)` — typed access
  - `accessKeys` — reactive list of all available access keys
  - Internally uses `useAuth()` for the data source
- [x] 8.8.3 `useBillingRedirect()` composable:
  ```typescript
  const { isBillingReturn, billingSuccess, returnUrl } = useBillingRedirect();
  ```
  - On mount: calls `billing.detectBillingUpdate()`, sets reactive state
  - `isBillingReturn: boolean` — `true` if `billing_updated` param is present
  - `billingSuccess: boolean | null` — `true` for `billing_updated=1`, `false` for `billing_updated=0`
  - Sister domains use this in their root layout to detect billing return and trigger `refetch()`

#### 8.9 Documentation & Publishing

- [x] 8.9.1 Write README.md: quickstart (`npm install @sattabase/sdk`), configuration, browser setup (Pattern B), Vue integration, feature gates, billing redirect
- [x] 8.9.2 Write Vue integration guide: setup with `provide/inject`, route guards, auto-refresh
- [x] 8.9.3 Add TSDoc comments to all public methods and types
- [x] 8.9.4 Publish to private npm (test first, then production)
- [x] 8.9.5 Add `CHANGELOG.md`

#### 8.10 SDK Implementation Summary

Both SDKs are implemented in-repo under `sdk/`:

| SDK | Path | Language | Tests | Build Tool | Dependencies |
|-----|------|----------|-------|------------|--------------|
| `sattabase-sdk` | `sdk/python/` | Python 3.10+ | 6 test files (pytest) | hatch | httpx, pydantic>=2.0 |
| `@sattabase/sdk` | `sdk/typescript/` | TypeScript (ES2020) | 50 tests (vitest) | tsup | zero runtime deps |

**SDK modules (both SDKs mirror each other):**
- `config` — SattabaseConfig with validation
- `client` — SattabaseClient with auto-refresh, X-API-Key/X-Service-Domain headers
- `auth` — login, register, me, refresh, verify, blacklist, logout, password reset, email verification
- `access` — cached feature gating (hasAccess, getAccess, keys)
- `redirect` — billing URL constructors (manageSubscription, upgrade, portal) + detectBillingUpdate
- `models` — TokenPair, User, SubscriptionInfo, AuthMeResponse, MessageResponse
- `exceptions` — typed exception hierarchy + buildError mapper
- `token-store` — TokenStore interface + in-memory + localStorage implementations

**Remaining (not yet implemented):**
- Publishing to PyPI/npm (both SDKs are local-only)
- CHANGELOG.md for both SDKs

---

### Phase 9: Admin Backend (API Layer)

**Goal:** Complete admin API with all CRUD endpoints, analytics, and audit logging.

#### 9.1 Admin Schemas

- [x] 9.1.1 Create `billing/admin_schemas.py` (or add to existing `billing/schemas.py`)
- [x] 9.1.2 Product schemas: `AdminProductCreateSchema`, `AdminProductUpdateSchema`, `AdminProductListItemSchema` (includes `plan_count`, `subscriber_count`, `domain_count`), `AdminProductDetailSchema` (includes plans, domains)
- [x] 9.1.3 Plan schemas: `AdminPlanCreateSchema`, `AdminPlanUpdateSchema`, `AdminPlanListItemSchema`, `AdminPlanDetailSchema` (includes access entries), `AdminPlanDuplicateSchema`
- [x] 9.1.4 Access entry schemas: `AdminAccessEntryCreateSchema`, `AdminAccessEntryUpdateSchema`, `AdminAccessEntryBulkSchema` (list of entries), `AdminAccessMatrixRowSchema`, `AdminAccessMatrixSchema` (plans × keys grid)
- [x] 9.1.5 Subscription schemas: `AdminSubscriptionListItemSchema` (includes user email, product name), `AdminSubscriptionDetailSchema`, `AdminSubscriptionOverrideSchema` (plan_id, status, period_start, period_end), `AdminSubscriptionExtendSchema`
- [x] 9.1.6 User schemas: `AdminUserListItemSchema` (includes subscription_count, last_login_at), `AdminUserDetailSchema` (includes all subscriptions), `AdminUserStatusUpdateSchema`, `AdminUserRoleUpdateSchema`
- [x] 9.1.7 Refund schemas: `AdminRefundListItemSchema`, `AdminRefundDetailSchema`, `AdminRefundApprovalSchema` (approved, notes)
- [x] 9.1.8 Metrics schemas: `AdminMetricsOverviewSchema` (mrr, active_subs, trial_subs, churn_rate, conversion_rate), `AdminMetricsRevenueSchema` (by_product, by_plan, by_period), `AdminMetricsSubscriptionFunnelSchema`
- [x] 9.1.9 Audit log schema: `AdminAuditLogItemSchema` (admin_user, action, path, ip, timestamp, details_json), `AdminAuditLogListSchema` (paginated)

#### 9.2 Admin Controller — Products & Domains

- [x] 9.2.1 Create `AdminController` in `billing/admin_controller.py` — prefix `/admin`, auth `JWTAuth + IsAuthenticated + IsAdmin`, all methods gated by is_staff
- [x] 9.2.2 `POST /admin/products` — create product with slug auto-generation, validate unique name/slug
- [x] 9.2.3 `GET /admin/products` — list with annotated `plan_count`, `subscriber_count` (via Subscription), `domain_count`; support `?is_active=` filter, `?search=` (name/slug)
- [x] 9.2.4 `GET /admin/products/{id}` — detail with plans + domains, annotated subscriber counts per plan
- [x] 9.2.5 `PUT /admin/products/{id}` — update name, description, home_url; partial update via schema
- [x] 9.2.6 `PATCH /admin/products/{id}/toggle` — toggle `is_active`; reject if product has active subscriptions and trying to deactivate
- [x] 9.2.7 `DELETE /admin/products/{id}` — soft-delete via set `is_active=False`; reject if any active subscriptions exist
- [x] 9.2.8 `POST /admin/products/{product_id}/domains` — create ServiceDomain with domain validation (unique), set `is_primary` if first domain for product
- [x] 9.2.9 `PUT /admin/domains/{id}` — update domain, toggle `is_primary` (only one primary per product), toggle `is_active`
- [x] 9.2.10 `DELETE /admin/domains/{id}` — remove domain; prevent deleting primary domain if other domains exist
- [x] 9.2.11 Apply `@log_admin_access` to all mutation endpoints

#### 9.3 Admin Controller — Plans & Access Entries

- [x] 9.3.1 `POST /admin/products/{product_id}/plans` — create plan with auto slug, validate unique (product, slug), default sort_order
- [x] 9.3.2 `GET /admin/products/{product_id}/plans` — list plans ordered by sort_order with `prefetch_related("access_entries")`
- [x] 9.3.3 `GET /admin/plans/{id}` — detail with all access entries, annotated subscriber count
- [x] 9.3.4 `PUT /admin/plans/{id}` — update all plan fields; if price or billing_cycle changes, warn if active subscribers exist
- [x] 9.3.5 `PATCH /admin/plans/{id}/toggle` — toggle `is_active`
- [x] 9.3.6 `PATCH /admin/plans/{id}/feature` — toggle `is_featured`
- [x] 9.3.7 `POST /admin/plans/{id}/duplicate` — deep copy plan + all AccessEntry records; append "(Copy)" to name, increment sort_order
- [x] 9.3.8 `DELETE /admin/plans/{id}` — delete plan; reject if any Subscription references this plan (PROTECT FK already blocks this, return user-friendly error)
- [x] 9.3.9 `POST /admin/plans/{plan_id}/access-entries` — create single access entry; validate unique (plan, key)
- [x] 9.3.10 `PUT /admin/access-entries/{id}` — update key, value, value_type, description
- [x] 9.3.11 `DELETE /admin/access-entries/{id}` — remove access entry
- [x] 9.3.12 `POST /admin/plans/{plan_id}/access-entries/bulk` — replace all access entries for a plan in a single transaction (delete existing, create new)
- [x] 9.3.13 `GET /admin/products/{product_id}/access-matrix` — return 2D grid: rows = unique access keys across all plans, columns = plans, cells = typed values (or empty)
- [x] 9.3.14 Apply `@log_admin_access` to all mutation endpoints

#### 9.4 Admin Controller — Subscriptions

- [x] 9.4.1 `GET /admin/subscriptions` — list with `select_related("user", "plan", "product")`; filters: `?product_id=`, `?plan_id=`, `?status=`, `?search=` (user email); paginated
- [x] 9.4.2 `GET /admin/subscriptions/{id}` — detail with plan info, user info, access entries from plan
- [x] 9.4.3 `PATCH /admin/subscriptions/{id}/override` — admin sets plan_id and/or status; log before/after state; handle Stripe sync if needed (warn if subscription has active Stripe subscription)
- [x] 9.4.4 `PATCH /admin/subscriptions/{id}/cancel` — force cancel: set status=canceled, canceled_at=now, keep active until period_end
- [x] 9.4.5 `PATCH /admin/subscriptions/{id}/expire` — force expire: set status=expired, effective immediately
- [x] 9.4.6 `PATCH /admin/subscriptions/{id}/extend` — extend period_end by given number of days
- [x] 9.4.7 `GET /admin/subscriptions/{id}/plan-changes` — list PlanChangeLog entries for this subscription, ordered by created_at desc
- [x] 9.4.8 `GET /admin/subscriptions/{id}/invoices` — list Invoice entries for this subscription, ordered by created_at desc
- [x] 9.4.9 `GET /admin/subscriptions/{id}/refunds` — list Refund entries for this subscription
- [x] 9.4.10 Apply `@log_admin_access` to all mutation endpoints

#### 9.5 Admin Controller — Users

- [x] 9.5.1 `GET /admin/users` — list users with annotated `subscription_count`; filters: `?is_active=`, `?is_email_verified=`, `?role=`, `?search=` (email, name); paginated
- [x] 9.5.2 `GET /admin/users/{id}` — detail with `prefetch_related("subscriptions")` (all products), include login history (last 10)
- [x] 9.5.3 `PATCH /admin/users/{id}/status` — activate/deactivate; if deactivating, log warning if user has active subscriptions
- [x] 9.5.4 `PATCH /admin/users/{id}/role` — change role (owner/admin/member)
- [x] 9.5.5 `GET /admin/users/{id}/audit` — compile audit trail from: UserLoginHistory (logins), PlanChangeLog (plan changes), Refund (refund history), Subscription (status changes via updated_at) — return chronological list

#### 9.6 Admin Controller — Refunds

- [x] 9.6.1 `GET /admin/refunds` — list refunds with `select_related("subscription__user", "subscription__plan", "initiated_by", "approved_by")`; filters: `?status=`, `?reason_category=`, `?subscription_id=`, `?date_from=`, `?date_to=`; paginated
- [x] 9.6.2 `PATCH /admin/refunds/{id}/approve` — set `approved_by=request.user`, `approved_at=now`, `status="completed"`; log audit; validate that `initiated_by != approved_by` (two-person rule)
- [x] 9.6.3 `PATCH /admin/refunds/{id}/reject` — set `status="failed"`, add rejection notes; log audit
- [x] 9.6.4 Apply `@log_admin_access` to approve/reject endpoints

#### 9.7 Admin Controller — Metrics & Audit

- [x] 9.7.1 `GET /admin/metrics/overview` — aggregate queries: MRR (sum of active subscription plan prices), active subscription count, trial count, past_due count, churn rate (canceled last 30 days / total active 30 days ago), trial conversion rate
- [x] 9.7.2 `GET /admin/metrics/revenue` — revenue by product (sum of invoice amount_paid_cents, grouped by product), by plan, by month (last 12 months); use RevenueRecognitionEntry table
- [x] 9.7.3 `GET /admin/metrics/subscriptions` — subscription funnel: new registrations (last 30 days), trial starts, trial→paid conversions, active→canceled, active→past_due; breakdown by product
- [x] 9.7.4 `GET /admin/metrics/products` — per-product: total subscribers, active subscribers, MRR, plan distribution (count per plan)
- [x] 9.7.5 Create `AdminAuditLog` model or use existing logging mechanism — `GET /admin/audit-log` returns paginated list of admin actions (filterable by admin_user, action_type, date range)
- [x] 9.7.6 `GET /admin/webhooks` — list WebhookEventLog entries (filterable by event_type, processed status); paginated
- [x] 9.7.7 `POST /admin/webhooks/{id}/retry` — re-process a failed webhook event (call existing `process_webhook_event`)

#### 9.8 Admin Infrastructure

- [x] 9.8.1 Add admin-specific rate limiting: stricter limits on mutation endpoints (e.g., 30/min for reads, 10/min for writes)
- [x] 9.8.2 Ensure all admin endpoints return consistent error format with `code` field for frontend handling
- [x] 9.8.3 Add pagination support to all list endpoints: `?page=`, `?page_size=` (default 20, max 100), return `{items, meta: {page, page_size, total, total_pages}}`
- [ ] 9.8.4 Write integration tests for all admin endpoints using Django test client
- [x] 9.8.5 Update OpenAPI schema description with admin endpoints documented

---

### Phase 10: Admin Frontend

**Goal:** Build the dedicated admin dashboard at `/admin/*` using the existing Astro + Vue + Tailwind stack.

#### 10.1 Admin Layout & Infrastructure

- [ ] 10.1.1 Create `AdminLayout.astro` — separate from `DashboardLayout.astro`; uses same frozen shell pattern (h-dvh, overflow-hidden) but with admin-specific sidebar and navbar
- [ ] 10.1.2 Create `AdminNavbar.vue` — shows "Sattabase Admin" branding, staff user badge (name + role), link to user-facing dashboard, link to Django admin (`/admin/django/`)
- [ ] 10.1.3 Create `AdminSidebar.vue` — navigation items: Dashboard, Products, Subscriptions, Users, Refunds, API Keys, Webhooks, Audit Log; collapsible on mobile
- [ ] 10.1.4 Create admin route guard in `frontend/src/middleware/` or layout script: on `/admin/*` routes, check `user.is_staff` via stored auth state; redirect to `/dashboard` if not staff
- [ ] 10.1.5 Create `frontend/src/lib/admin-api.ts` — typed API client for all admin endpoints (wraps fetch with JWT auth)
- [ ] 10.1.6 Create admin page structure under `frontend/src/pages/admin/`

#### 10.2 Reusable Admin Components

- [ ] 10.2.1 `AdminDataTable.vue` — sortable columns, server-side pagination, per-column filters, bulk selection with checkboxes, loading skeleton, empty state
- [ ] 10.2.2 `AdminStatsCard.vue` — label, value (formatted), change percentage (green/red), trend icon (up/down), optional sparkline
- [ ] 10.2.3 `AdminPageHeader.vue` — page title, breadcrumb trail, primary + secondary action buttons (slots)
- [ ] 10.2.4 `AdminConfirmDialog.vue` — modal with title, message, confirm/cancel buttons, destructive variant (red confirm button)
- [ ] 10.2.5 `AdminFilterBar.vue` — search input, dropdown filters, date range picker, active filter count badge, clear all button
- [ ] 10.2.6 `AdminStatusBadge.vue` — colored badge for subscription status (active=green, past_due=yellow, canceled=gray, trialing=blue, expired=red, paused=orange)
- [ ] 10.2.7 `AdminEmptyState.vue` — icon, title, description, optional CTA button
- [ ] 10.2.8 `AdminFeatureMatrix.vue` — table with plans as columns, access keys as rows, values in cells; checkmarks for boolean true, values for integers, empty for false/unset
- [ ] 10.2.9 `AdminAuditTimeline.vue` — chronological list of events with icon, description, timestamp, admin user name

#### 10.3 Admin Dashboard Page

- [ ] 10.3.1 Create `frontend/src/pages/admin/index.astro` — dashboard overview page
- [ ] 10.3.2 Stats row: Active Subscriptions (count), MRR (formatted currency), Trials (count), Past Due (count), Churn Rate (percentage)
- [ ] 10.3.3 Subscription trend chart: line chart showing active subscriptions over last 12 months (using chart library)
- [ ] 10.3.4 Revenue by product: horizontal bar chart or pie chart
- [ ] 10.3.5 Recent activity feed: last 10 admin actions from audit log
- [ ] 10.3.6 Quick links: "View All Subscriptions", "Manage Products", "API Keys"

#### 10.4 Product Management Pages

- [ ] 10.4.1 `GET /admin/products` — data table with columns: name, slug, plan count, subscriber count, status badge, actions (view, edit, toggle active)
- [ ] 10.4.2 `GET /admin/products/new` — form: name, slug (auto-generated), description, home_url, icon upload
- [ ] 10.4.3 `GET /admin/products/[id]` — product detail: info card (name, slug, description, status), tab navigation: Plans | Domains | Metrics
- [ ] 10.4.4 Plans tab: data table with plan name, price, billing cycle, subscriber count, status badge, actions (view, edit, duplicate, delete)
- [ ] 10.4.5 Domains tab: data table with domain URL, is_primary badge, is_active badge, actions (edit primary, toggle active, delete)
- [ ] 10.4.6 `GET /admin/products/[id]/plans/new` — form: name, slug, price, currency, billing_cycle, trial_days, features (JSON editor or key-value list), is_featured, sort_order
- [ ] 10.4.7 `GET /admin/products/[id]/plans/[planId]` — plan detail: info card + access entries table (key, value, type, description, actions: edit, delete) + "Add Access Entry" form + "Bulk Update" button
- [ ] 10.4.8 Access matrix page: `GET /admin/products/[id]/access-matrix` — feature comparison table across all plans

#### 10.5 Subscription Management Pages

- [ ] 10.5.1 `GET /admin/subscriptions` — data table with columns: user email, product, plan, status badge, period end, actions (view, cancel, expire)
- [ ] 10.5.2 Filters: product dropdown, plan dropdown, status dropdown, search by email
- [ ] 10.5.3 `GET /admin/subscriptions/[id]` — subscription detail: info card (user, plan, product, status, period), tab navigation: Overview | Plan Changes | Invoices | Refunds
- [ ] 10.5.4 Overview tab: subscription info, override form (change plan, change status, extend period), cancel/expire buttons with confirmation dialogs
- [ ] 10.5.5 Plan Changes tab: chronological table of plan changes (from_plan, to_plan, proration amount, date, initiated_by)
- [ ] 10.5.6 Invoices tab: table of invoices (number, amount, status, date, actions: view hosted URL, view PDF)
- [ ] 10.5.7 Refunds tab: table of refunds (amount, status, reason, initiated_by, approved_by, date)

#### 10.6 User Management Pages

- [ ] 10.6.1 `GET /admin/users` — data table with columns: name, email, role badge, email verified badge, subscription count, last login, status badge, actions (view)
- [ ] 10.6.2 Filters: role dropdown, status dropdown, email verified toggle, search by email/name
- [ ] 10.6.3 `GET /admin/users/[id]` — user detail: profile card (avatar, name, email, role, joined date), subscriptions list (product, plan, status for each), action buttons (activate/deactivate, change role)
- [ ] 10.6.4 `GET /admin/users/[id]/audit` — audit timeline: login events, plan changes, subscription status changes, refund events — all in chronological order

#### 10.7 Refund Management Pages

- [ ] 10.7.1 `GET /admin/refunds` — data table with columns: subscription (user + product), amount, status badge, reason category, initiated by, approved by, date, actions (approve, reject for pending refunds)
- [ ] 10.7.2 Filters: status dropdown, reason category dropdown, date range
- [ ] 10.7.3 Approve/reject modals: show refund details, notes textarea, confirm button; enforce two-person rule (approver cannot be same as initiator)

#### 10.8 API Key Management Pages

- [ ] 10.8.1 `GET /admin/api-keys` — card list or table with: name, service domain, prefix (masked), is_active badge, last used (relative time), created date, actions (revoke, rotate)
- [ ] 10.8.2 `GET /admin/api-keys/new` — form: name, service domain dropdown; on submit: show raw key ONCE in a "copy this now" modal with countdown warning (key disappears after modal close)
- [ ] 10.8.3 Revoke confirmation dialog: "This will immediately disable the key. Services using it will lose access."
- [ ] 10.8.4 Rotate flow: confirmation dialog → call rotate → show new raw key in modal (old key is now invalid)

#### 10.9 Webhook & Audit Log Pages

- [ ] 10.9.1 `GET /admin/webhooks` — data table: event ID, event type, status badge (processed/pending/failed), created date, error message (if failed), action (retry for failed)
- [ ] 10.9.2 Filters: event type dropdown, status dropdown, date range
- [ ] 10.9.3 `GET /admin/audit-log` — data table: admin user, action (path), method, IP address, timestamp; expandable row for request details
- [ ] 10.9.4 Filters: admin user dropdown, action type, date range

---

### Phase 11: Admin RBAC (Future)

**Goal:** Granular admin roles beyond `is_staff` boolean.

- [ ] 11.1 Design admin role model: define roles (Super Admin, Product Manager, Support, Finance, Read-Only) with permission sets
- [ ] 11.2 Add `AdminRole` model with `name`, `description`, `permissions` (JSONField — list of permission strings)
- [ ] 11.3 Add `admin_role` FK to User model (nullable, default None — staff without role gets all permissions like current behavior)
- [ ] 11.4 Create permission check decorator/utility: `require_permission("products:write")` — checks user's admin_role permissions
- [ ] 11.5 Apply permission checks to all admin endpoints (read vs write separation)
- [ ] 11.6 Add admin role management UI: list roles, create/edit roles (permission checkbox matrix), assign role to user
- [ ] 11.7 Frontend: hide/disable UI sections based on current user's admin role permissions

---

## 6. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SDK = Auth + Permissions only | Stripe is single source of truth for payments; billing UX centralized on Sattabase |
| Hand-written SDK (not generated) | Small surface area (auth only); full control over token lifecycle, auto-refresh, middleware |
| Billing via redirect, not API | Service domains never touch payment state; user goes to Sattabase, manages billing, returns |
| Separate `ServiceCredential` model | Service domains need their own identity beyond user JWT; enables audit and revocation |
| API key hash storage | Never store raw keys; SHA-256 hash + prefix for identification |
| Two auth patterns (proxy vs direct) | Some sister services have backends (Pattern A), some are SPA-only (Pattern B); support both |
| Dedicated admin layout | Admin UX is fundamentally different from user dashboard; separate routes prevent accidental cross-access |
| `is_staff` first, RBAC later | Start simple, add granularity when team grows; the audit logging infrastructure is already in place |
| Admin endpoints under `/admin/` | Clear URL separation; existing `/billing/admin/` endpoints migrate to `/admin/billing/` |
| Feature matrix endpoint | Critical for admin UX — comparing plans side-by-side is the #1 admin task |
| Bulk access entry update | Admins need to update all access entries for a plan at once (e.g., new feature added to all tiers) |
| Soft-delete on plans/products | Prevents accidental data loss; can be restored if subscriptions still reference them |

---

## 7. Security Considerations

| Concern | Mitigation |
|---------|------------|
| API key leakage | Keys shown only ONCE at creation; stored as hashes; revocable instantly |
| Domain spoofing | `X-Service-Domain` validated against `ServiceCredential` + `ServiceDomain` table |
| Admin endpoint abuse | `is_staff` + `@log_admin_access` on every mutation; rate limiting |
| Admin privilege escalation | Future RBAC limits what each staff role can access |
| Subscription override abuse | All overrides are audit-logged with admin user, IP, and before/after state |
| Refund fraud | Two-person approval (initiated_by + approved_by); reason category required |
| SDK token exposure | Pattern A (proxy) recommended for backends; Pattern B (SPA) uses httpOnly cookies where possible |
| OpenAPI schema exposure | Schema is public (for SDK generation); sensitive operations require auth regardless |
| Admin frontend access | Route guard checks `is_staff` on every navigation; API rejects non-staff at auth layer |