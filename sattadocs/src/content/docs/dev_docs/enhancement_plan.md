---
title: Enhancement plan
description:  Sattabase — Central Auth & Subscription Platform
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
- [x] 6.2.4 Add `API_KEY_ENFORCED` setting in `base/settings.py` (default `False`) — soft deprecation period
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

### Phase 10: Admin Frontend (10.1–10.9 COMPLETE)

**Goal:** Build the dedicated admin dashboard at `/admin/*` using the existing Astro + Vue + Tailwind stack.

#### 10.1 Admin Layout & Infrastructure — DONE

- [x] 10.1.1 Create `AdminLayout.astro` — separate from `DashboardLayout.astro`; uses same frozen shell pattern (h-dvh, overflow-hidden) but with admin-specific sidebar and navbar. **Implemented as Astro component with `transition:persist` keys (`admin-sidebar`, `admin-navbar`) to avoid DOM reuse conflicts with user dashboard.**
- [x] 10.1.2 Create `AdminNavbar.astro` — shows "Sattabase Admin" breadcrumb branding, staff user badge (name + role label), link to user-facing dashboard, link to Django admin (`/admin/django/`), dark mode toggle, user dropdown with sign out. **Built as Astro component (not Vue) matching existing Navbar pattern.**
- [x] 10.1.3 Create `AdminSidebar.astro` — amber-accented admin navigation with 3 sections: Overview (Dashboard), Management (Products, Subscriptions, Users, Refunds), System (API Keys, Webhooks, Audit Log). Includes "Back to Dashboard" and "Django Admin" links. Collapsible on mobile. **Distinct amber color theme differentiates from green user dashboard.**
- [x] 10.1.4 Create admin route guard — `src/middleware.ts` (Astro server middleware skeleton for `/admin/*` route protection) + `src/composables/useAdminGuard.ts` (Vue composable for client-side admin auth verification checking `is_staff` or owner/admin role). **True SSR guard noted as requiring httpOnly cookie; current implementation relies on client-side check.**
- [x] 10.1.5 Create `frontend/src/lib/admin.ts` — typed API client for all admin endpoints covering: Products, Service Domains, Plans, Access Entries, Subscriptions, Users, Refunds, Metrics, Webhooks, Audit Log. Includes helper functions: `formatRelativeTime`, `getSubscriptionStatusColor`, `getRefundStatusColor`, `getWebhookStatusColor`. **Wraps fetch with JWT auth from localStorage.**
- [x] 10.1.6 Create admin page structure under `frontend/src/pages/admin/` — 8 pages created: `index.astro` (dashboard with quick links), `products/index.astro`, `subscriptions/index.astro`, `users/index.astro`, `refunds/index.astro`, `api-keys/index.astro` (renders existing `ApiKeysAdmin.vue`), `webhooks/index.astro`, `audit-log/index.astro`. Old `/dashboard/admin/api-keys` migrated to redirect → `/admin/api-keys`. User sidebar updated: admin nav item changed from "API Keys" → "Admin Panel" with `href=/admin`.

#### 10.2 Reusable Admin Components — DONE

- [x] 10.2.1 `AdminDataTable.vue` — sortable columns, server-side pagination, per-column filters, bulk selection with checkboxes, loading skeleton, empty state. **Implemented in `src/components/admin/AdminDataTable.vue`. Supports column definitions with sortable/defaultSort/width/align/hideOnMobile, row selection via checkboxes with select-all, loading skeleton with shimmer, empty state slot, pagination controls, cell customization via named slots (`#cell-{key}`), and row-click support.**
- [x] 10.2.2 `AdminStatsCard.vue` — label, value (formatted), change percentage (green/red), trend icon (up/down), optional sparkline. **Implemented in `src/components/admin/AdminStatsCard.vue`. Supports 6 icon variants (currency/users/chart/activity/warning/info) with color-mapped backgrounds, locale-aware number formatting, percentage change with up/down arrows, and SVG sparkline generation from data points.**
- [x] 10.2.3 `AdminPageHeader.vue` — page title, breadcrumb trail, primary + secondary action buttons (slots). **Implemented in `src/components/admin/AdminPageHeader.vue`. Supports breadcrumb navigation with linked/text items, title + description, and `primary-action`/`secondary-action` named slots.**
- [x] 10.2.4 `AdminConfirmDialog.vue` — modal with title, message, confirm/cancel buttons, destructive variant (red confirm button). **Implemented in `src/components/admin/AdminConfirmDialog.vue`. Teleported modal with backdrop blur, Escape key + backdrop click to close, destructive (red) and warning (amber) icon variants, loading spinner on confirm, body scroll lock when open, v-model:open binding, accessible with role="dialog" and aria-modal.**
- [x] 10.2.5 `AdminFilterBar.vue` — search input, dropdown filters, date range picker, active filter count badge, clear all button. **Implemented in `src/components/admin/AdminFilterBar.vue`. Supports debounced search (300ms), dynamic dropdown filters from FilterDef array, optional date range picker (start/end), active filter count badge (amber), and clear-all button.**
- [x] 10.2.6 `AdminStatusBadge.vue` — colored badge for subscription status (active=green, past_due=yellow, canceled=gray, trialing=blue, expired=red, paused=orange). **Implemented in `src/components/admin/AdminStatusBadge.vue`. Supports 6 type modes (subscription/refund/webhook/generic/active-inactive/custom), uses getSubscriptionStatusColor/getRefundStatusColor/getWebhookStatusColor from lib/admin.ts, 8 custom color overrides (green/red/amber/blue/orange/gray/purple/sky), dot indicator, and smart generic fallback that infers color from common status values.**
- [x] 10.2.7 `AdminEmptyState.vue` — icon, title, description, optional CTA button. **Implemented in `src/components/admin/AdminEmptyState.vue`. Supports 8 icon variants (box/key/users/document/clipboard/webhook/search/generic) with matching inline SVGs, title + description, and `action` named slot for CTA button.**
- [x] 10.2.8 `AdminFeatureMatrix.vue` — table with plans as columns, access keys as rows, values in cells; checkmarks for boolean true, values for integers, empty for false/unset. **Implemented in `src/components/admin/AdminFeatureMatrix.vue`. Renders AccessMatrixEntry[] from lib/admin.ts, displays checkmark icons for boolean true, formatted values for integers/strings, em-dash for empty/falsy, with loading skeleton and empty state.**
- [x] 10.2.9 `AdminAuditTimeline.vue` — chronological list of events with icon, description, timestamp, admin user name. **Implemented in `src/components/admin/AdminAuditTimeline.vue`. Supports both AuditLogEntry and UserAuditEntry types, color-coded action icons (create=green, delete=red, update=amber, auth=blue, view=gray), vertical timeline connector, relative timestamps with full date on hover, expandable request details (JSON) for AuditLogEntry, and loading skeleton.**

#### 10.3 Admin Dashboard Page — DONE

- [x] 10.3.1 Create `frontend/src/pages/admin/index.astro` — dashboard overview page. **Implemented as Astro page mounting `AdminDashboard.vue` inside `AdminLayout` with `client:only="vue"` for SPA hydration.**
- [x] 10.3.2 Stats row: Active Subscriptions (count), MRR (formatted currency), Trials (count), Past Due (count), Churn Rate (percentage). **Implemented using 5 `AdminStatsCard` components (10.2.2) in a responsive `lg:grid-cols-5` grid. Each card has appropriate icon variant, loading skeleton, and formatted values from `adminApi.getMetricsOverview()`. Churn rate displayed as percentage with `toFixed(1)`.**
- [x] 10.3.3 Subscription trend chart: line chart showing active subscriptions over last 12 months (using chart library). **Implemented as hand-built SVG line chart with area fill, Y/X axis labels, grid lines, and data points. Uses `MetricsRevenue.by_month` data from `adminApi.getMetricsRevenue()`. Chart titled "Revenue Trend" showing monthly revenue rather than subscription count. Includes loading skeleton and empty state. No external chart library used — pure SVG for zero-dependency rendering.**
- [x] 10.3.4 Revenue by product: horizontal bar chart or pie chart. **Implemented as horizontal bar chart with colored bars, product names, MRR display, and active/trial subscription counts. Uses `MetricsRevenue.by_product` data. 6 rotating bar colors with dark mode variants. Includes loading skeleton and empty state.**
- [x] 10.3.5 Recent activity feed: last 10 admin actions from audit log. **Implemented using `AdminAuditTimeline` component (10.2.9) with `adminApi.listAuditLog({ page: 1, page_size: 10 })`. Includes "View all →" link to `/admin/audit-log`, loading skeleton, and empty state.**
- [x] 10.3.6 Quick links: "View All Subscriptions", "Manage Products", "API Keys". **Implemented with 7 quick links (exceeds spec): Subscriptions, Products, API Keys, Users, Refunds, Webhooks, plus Django Admin (external link with separator). Each has inline SVG icon and hover states.**
- **10.3 additional notes:** Data fetching uses `Promise.allSettled()` for parallel loading with graceful degradation (partial failures shown). Error state with retry button. `AdminPageHeader` (10.2.3) used for page title and breadcrumbs.

#### 10.4 Product Management Pages — DONE

- [x] 10.4.1 `GET /admin/products` — data table with columns: name, slug, plan count, subscriber count, status badge, actions (view, edit, toggle active). **Implemented as `ProductsAdmin.vue` using AdminDataTable, AdminFilterBar (search + status filter), AdminStatusBadge, AdminConfirmDialog. Supports client-side search, server-side status filtering, client-side sort, server-side pagination. Row click navigates to product detail.**
- [x] 10.4.2 `GET /admin/products/new` — form: name, slug (auto-generated), description, home_url, icon upload. **Implemented as inline modal form inside ProductsAdmin.vue. Auto-generates slug from name using snake_case. No icon upload yet (backend API doesn't support it).**
- [x] 10.4.3 `GET /admin/products/[id]` — product detail: info card (name, slug, description, status), tab navigation: Plans | Domains | Metrics. **Implemented as `ProductDetailAdmin.vue` with Astro dynamic route at `products/[id].astro`. Info card shows slug, status badge, home URL, created date. Tab navigation: Plans | Domains | Access Matrix (Metrics not yet available in API). Edit/toggle/delete actions in page header.**
- [x] 10.4.4 Plans tab: data table with plan name, price, billing cycle, subscriber count, status badge, actions (view, edit, duplicate, delete). **Implemented inside ProductDetailAdmin.vue using AdminDataTable. Actions: edit (modal), feature/unfeature toggle, duplicate, activate/deactivate, delete. Row click navigates to plan detail. Featured badge shown inline.**
- [x] 10.4.5 Domains tab: data table with domain URL, is_primary badge, is_active badge, actions (edit primary, toggle active, delete). **Implemented inside ProductDetailAdmin.vue as card-based list (not table, since domains are typically few). Add domain modal, edit domain modal (domain, is_primary, is_active checkboxes), delete with AdminConfirmDialog. Primary badge and active status shown inline.**
- [x] 10.4.6 `GET /admin/products/[id]/plans/new` — form: name, slug, price, currency, billing_cycle, trial_days, features (JSON editor or key-value list), is_featured, sort_order. **Implemented as inline modal form inside ProductDetailAdmin.vue. Fields: name, slug (auto-generated), price, currency (USD/EUR/GBP/BDT), billing_cycle (monthly/yearly), trial_days, is_featured checkbox, sort_order. Access entries added separately in plan detail.**
- [x] 10.4.7 `GET /admin/products/[id]/plans/[planId]` — plan detail: info card + access entries table (key, value, type, description, actions: edit, delete) + "Add Access Entry" form + "Bulk Update" button. **Implemented as `PlanDetailAdmin.vue` with Astro dynamic route at `plans/[planId].astro`. Info card shows price, billing cycle, trial, subscribers, status, sort order. Actions: edit, feature/unfeature, duplicate, activate/deactivate, delete. Access entries shown in AdminDataTable with key (code-styled), value, value_type (color badge), description columns. Add/edit entry modals. Bulk update not yet implemented (single entry CRUD covers most use cases).**
- [x] 10.4.8 Access matrix page: `GET /admin/products/[id]/access-matrix` — feature comparison table across all plans. **Implemented as "Access Matrix" tab inside ProductDetailAdmin.vue using AdminFeatureMatrix component (10.2.8). Lazy-loaded when tab is selected. Shows plans as columns, access keys as rows, checkmarks for boolean, values for integer/string.**

**10.4 Architecture Notes:**
- Three Vue components created: `ProductsAdmin.vue` (22.6 KB), `ProductDetailAdmin.vue` (56.1 KB), `PlanDetailAdmin.vue` (33.4 KB)
- Two Astro dynamic routes created: `products/[id].astro`, `plans/[planId].astro`
- All pages use 10.2 reusable components: AdminPageHeader, AdminDataTable, AdminFilterBar, AdminConfirmDialog, AdminStatusBadge, AdminFeatureMatrix
- Product CRUD, Plan CRUD, Domain CRUD, and Access Entry CRUD all fully wired to lib/admin.ts API methods
- Consistent modal pattern (Teleport to body, backdrop blur, ESC to close) for create/edit forms
- AdminConfirmDialog used for all destructive actions with appropriate detail text

**10.4 Bugfix (2026-05-10):**
- **Trailing slash mismatch**: Frontend `admin.ts` had trailing slashes on collection endpoints (`/admin/products/`, `/admin/subscriptions/`, etc.) but backend routes have no trailing slash (`@http_get("/products")`). Only `/admin/api-keys/` worked because its route is `@http_get("/")`. Fixed by removing trailing slashes from all frontend admin paths except API keys.
- **Price field name mismatch**: Frontend `PlanItem.price` expected `price` but backend returns `price_cents`. Fixed by updating `PlanItem`, `PlanCreatePayload`, `PlanUpdatePayload` to use `price_cents`. Added `formatCents()` / `dollarsToCents()` / `centsToDollars()` helpers in components. Forms now accept dollar input and convert to cents for API submission.
- **Access entries missing IDs**: Backend `_serialize_plan_detail()` returned access entries without `id`, `value_type`, `plan_id`, `plan_name` — needed for the admin CRUD (edit/delete entries by ID). Fixed by including all fields in the serialization.
- **Product detail domains key**: Frontend used `product.domains` but backend returns `service_domains`. Fixed `ProductDetailAdmin.vue` and `ProductDetail` type to use `service_domains`.

**10.4 Bugfix (2026-05-10) — Access Matrix Save:**
- **typed_value vs value inconsistency**: Backend `create_access_entry`, `update_access_entry`, and `get_access_matrix` returned `entry.typed_value` (cast to Python `bool`/`int`) instead of raw `entry.value` (always a string). Frontend TypeScript types expect `string`. The frontend worked at runtime due to `String()` coercion but this was a type contract violation. Fixed by returning `entry.value` in all three endpoints, consistent with `_serialize_plan_detail()`.
- **Non-atomic multi-plan save**: The access matrix UI edits one key across multiple plans, but the backend only had per-plan CRUD endpoints (`POST /plans/{id}/access-entries`, `PUT /access-entries/{id}`, `DELETE /access-entries/{id}`). The frontend made N sequential API calls to save a single matrix row — if one failed midway, the matrix was left in a partial state. Fixed by adding a new atomic endpoint `PUT /admin/products/{product_id}/access-matrix/row` that creates/updates/deletes entries for one access key across all plans in a single database transaction. The frontend `handleAddEntry` and `handleEditEntrySubmit` now use this endpoint instead of multiple individual calls. Supports key renaming via `original_key` field.

#### 10.5 Subscription Management Pages — DONE

*Two Vue components + two Astro pages. All 9 subscription admin endpoints wired.*

- [x] 10.5.1 `GET /admin/subscriptions` — data table with columns: user email, product, plan, status badge, period end, actions (view, cancel, expire). **Implemented as `SubscriptionsAdmin.vue` using AdminDataTable, AdminFilterBar, AdminStatusBadge, AdminConfirmDialog. Supports server-side pagination, search by email, filter by product/plan/status. Cancel/expire actions with confirmation dialogs. Row click navigates to detail.**
- [x] 10.5.2 Filters: product dropdown, plan dropdown, status dropdown, search by email. **Implemented using AdminFilterBar with 3 dropdown filters (product, plan, status) + search. Product dropdown populated from API. Plan dropdown cascades from product selection (refreshed via watch). Status options: Active, Trialing, Past Due, Canceled, Expired, Paused.**
- [x] 10.5.3 `GET /admin/subscriptions/[id]` — subscription detail: info card (user, plan, product, status, period), tab navigation: Overview | Plan Changes | Invoices | Refunds. **Implemented as `SubscriptionDetailAdmin.vue` with Astro dynamic route at `subscriptions/[id].astro`. Info card shows user, product/plan, status badge, current period, trial info, Stripe subscription ID. Tab navigation with count badges on Plan Changes, Invoices, Refunds tabs.**
- [x] 10.5.4 Overview tab: subscription info, override form (change plan, change status, extend period), cancel/expire buttons with confirmation dialogs. **Two-column layout: subscription details (dl list with all fields) + quick actions card + Stripe integration card. Override modal with plan dropdown (populated from listPlans API), status dropdown (6 statuses), period end date input. Extend modal with days input and live preview of new end date. Cancel/expire via AdminConfirmDialog with destructive variant.**
- [x] 10.5.5 Plan Changes tab: chronological table of plan changes (from_plan, to_plan, proration amount, date, initiated_by). **Implemented using AdminDataTable with custom cell renderers. Proration amounts: green for negative (credit), normal for positive. Date formatting with formatDateTime. AdminEmptyState when no plan changes. Lazy-loaded on tab selection.**
- [x] 10.5.6 Invoices tab: table of invoices (number, amount, status, date, actions: view hosted URL). **Implemented using AdminDataTable. Invoice number in monospace font. Amount formatted as currency via formatCents. Status with AdminStatusBadge type="generic". "View" link button to hosted_url (external). AdminEmptyState when no invoices. Lazy-loaded on tab selection.**
- [x] 10.5.7 Refunds tab: table of refunds (amount, status, reason, initiated_by, approved_by, date). **Implemented using AdminDataTable. Amount formatted as currency. Status with AdminStatusBadge type="refund". Reason, initiated_by, approved_by columns. AdminEmptyState when no refunds. Lazy-loaded on tab selection.**

**10.5 Architecture Notes:**
- Two Vue components created: `SubscriptionsAdmin.vue` (~471 lines), `SubscriptionDetailAdmin.vue` (~1,163 lines)
- Two Astro routes: `subscriptions/index.astro` (replaced placeholder), `subscriptions/[id].astro` (new)
- All pages use 10.2 reusable components: AdminPageHeader, AdminDataTable, AdminFilterBar, AdminConfirmDialog, AdminStatusBadge, AdminEmptyState
- Consistent modal pattern (Teleport to body, backdrop blur, ESC to close) for override and extend forms
- AdminConfirmDialog used for cancel/expire destructive actions with appropriate detail text
- Lazy-loaded tab data: plan changes, invoices, and refunds fetched only when their tab is selected
- Tab data invalidated (re-fetched) after override/cancel/expire/extend actions
- View Transitions support via astro:page-load event listener (same pattern as ProductDetailAdmin)
- URL-based subscription ID extraction with prop fallback (same pattern as ProductDetailAdmin)

#### 10.6 User Management Pages — DONE

*Two Vue components + two Astro pages. All 5 user admin endpoints wired (list, detail, status, role, audit).*

- [x] 10.6.1 `GET /admin/users` — data table with columns: name, email, role badge, email verified badge, subscription count, last login, status badge, actions (view). **Implemented as `UsersAdmin.vue` using AdminDataTable, AdminFilterBar, AdminStatusBadge, AdminConfirmDialog. Supports server-side pagination, search by email/name, filter by role/status/email verified. Activate/deactivate and change role actions with confirmation dialogs. Row click navigates to user detail.**
- [x] 10.6.2 Filters: role dropdown, status dropdown, email verified toggle, search by email/name. **Implemented using AdminFilterBar with 3 dropdown filters (role, status, email verified) + search. Role options: Owner, Admin, Member. Status: Active, Inactive. Email verified: Verified, Not Verified.**
- [x] 10.6.3 `GET /admin/users/[id]` — user detail: profile card (avatar, name, email, role, joined date), subscriptions list (product, plan, status for each), action buttons (activate/deactivate, change role). **Implemented as `UserDetailAdmin.vue` with Astro dynamic route at `users/[id].astro`. Info card shows full name, email, role badge, status badge, email verified, staff access, subscriptions summary. Tab navigation: Profile | Subscriptions | Audit Trail. Profile tab has user details + quick actions card + subscription summary card. Subscriptions tab lists all subscriptions across products using AdminDataTable with status badges and "View" link to subscription detail.**
- [x] 10.6.4 `GET /admin/users/[id]/audit` — audit timeline: login events, plan changes, subscription status changes, refund events — all in chronological order. **Implemented as "Audit Trail" tab inside UserDetailAdmin.vue using AdminAuditTimeline component. Supports paginated audit events with Previous/Next controls. Lazy-loaded on tab selection. Events include: login (auth icon), plan_change (update icon), subscription_status (delete icon for cancel/expire), refund (update icon).**

**10.6 Architecture Notes:**
- Two Vue components created: `UsersAdmin.vue` (~540 lines), `UserDetailAdmin.vue` (~750 lines)
- Two Astro routes: `users/index.astro` (replaced placeholder), `users/[id].astro` (new)
- All pages use 10.2 reusable components: AdminPageHeader, AdminDataTable, AdminFilterBar, AdminConfirmDialog, AdminStatusBadge, AdminEmptyState, AdminAuditTimeline
- Frontend types in `lib/admin.ts` updated to match backend `AdminUserListItemSchema` and `AdminUserDetailSchema`: `UserItem` now includes `full_name`, `first_name`, `last_name`, `avatar`, `active_subscription_count`, `is_email_verified`, `last_login_at`; `UserDetail` adds `phone`, `timezone`, `currency`, `language`, `subscriptions: UserSubscriptionItem[]`; `UserAuditEntry` updated to match `AdminAuditEventSchema` with `event_type`, `description`, `metadata`, `ip_address`, `timestamp`
- `AdminAuditTimeline.vue` updated to handle both `AuditLogEntry` and `UserAuditEntry` types with type guards and unified timestamp accessor
- Consistent modal pattern (AdminConfirmDialog) for activate/deactivate and change role actions, with optional reason field
- View Transitions support via astro:page-load event listener (same pattern as SubscriptionDetailAdmin)
- URL-based user ID extraction with prop fallback (same pattern as other detail pages)
- Backend endpoints already implemented in `admin_user_controller.py` — no backend changes needed

#### 10.7 Refund Management Pages — DONE

*One Vue component + one Astro page + refund initiation UI. All 4 refund admin endpoints wired (list, initiate, approve, reject). Two-person rule enforced both client-side and server-side.*

- [x] 10.7.1 `GET /admin/refunds` — data table with columns: subscription (user + product), amount, status badge, reason category, initiated by, approved by, date, actions (approve, reject for pending refunds). **Implemented as `RefundsAdmin.vue` using AdminDataTable, AdminFilterBar, AdminStatusBadge, AdminConfirmDialog. Supports server-side pagination, filter by status/reason category/date range. View details modal shows full refund info. Approve/reject actions with confirmation dialogs.**
- [x] 10.7.2 Filters: status dropdown, reason category dropdown, date range. **Implemented using AdminFilterBar with 2 dropdown filters (status, category) + date range picker (date_from/date_to). Status options: Pending, Completed, Failed. Category options: Customer Request, Billing Error, Goodwill, Policy, Chargeback.**
- [x] 10.7.3 Approve/reject modals: show refund details, notes textarea, confirm button; enforce two-person rule (approver cannot be same as initiator). **Implemented with AdminConfirmDialog for both approve and reject. Refund summary shown in dialog body. Notes textarea for approval/rejection reason. Client-side two-person rule: current admin ID fetched on mount, approve button hidden if current admin is the initiator; warning icon shown instead. Server-side two-person rule enforced by backend AdminRefundController.**
- [x] 10.7.4 Refund initiation: admin can issue refunds from subscription detail page. **Added `POST /admin/subscriptions/{id}/refund` endpoint in AdminSubscriptionController. Validates subscription has Stripe payment, calls create_stripe_refund() with amount/reason/category/admin notes, captures admin IP for CMP-02 audit trail. Frontend: "Issue Refund" button in SubscriptionDetailAdmin.vue (both Quick Actions section and Refunds tab header). Full modal with subscription summary, two-person rule warning (amber banner), amount field (optional, defaults to full), reason category dropdown (5 categories), reason textarea, admin notes textarea. `canIssueRefund` computed: requires stripe_subscription_id + active/trialing/past_due/canceled status.**

**10.7 Architecture Notes:**
- One Vue component created: `RefundsAdmin.vue` (~480 lines)
- One existing Vue component enhanced: `SubscriptionDetailAdmin.vue` — added Issue Refund button + modal (~150 additional lines)
- One Astro route updated: `refunds/index.astro` (replaced placeholder with Vue component mount)
- All pages use 10.2 reusable components: AdminPageHeader, AdminDataTable, AdminFilterBar, AdminConfirmDialog, AdminStatusBadge
- Frontend types in `lib/admin.ts` updated: `listRefunds` now supports `subscription_id`, `date_from`, `date_to` params (matching backend filters)
- Frontend API client updated: added `IssueRefundPayload`, `IssueRefundResponse` types and `adminApi.issueRefund()` function
- `getRefundStatusColor` updated to handle `completed` status (green) — backend RefundStatus uses pending/completed/failed, not approved/rejected
- `AdminStatusBadge.vue` updated to handle `completed` dot color (green) for refund type
- Backend: new `POST /admin/subscriptions/{id}/refund` endpoint in AdminSubscriptionController (distinct from the pre-existing `POST /billing/subscriptions/{product_slug}/refund` in BillingAdminController)
- Backend fix: `datetime.now()` → `django_timezone.now()` in `AdminRefundController.approve_refund` for timezone-aware timestamps
- Detail modal with Teleport (same pattern as SubscriptionDetailAdmin) shows full refund info including Stripe IDs, IP, notes, two-person rule warning
- Complete refund flow: Admin initiates from subscription detail → Stripe processes refund → DB record created → Two-person rule requires another admin to approve via /admin/refunds page

#### 10.8 API Key Management Pages — DONE (pre-existing component, functional)

*`api-keys/index.astro` mounts the pre-existing `ApiKeysAdmin.vue` (from `components/vue/`) inside AdminLayout. This component predates Phase 10 and was migrated from `/dashboard/admin/api-keys`. All 4 workflows are functional (list, create, revoke, rotate). Uses custom card layout and hand-rolled modals instead of Phase 10.2 reusable components — a cosmetic refactor could align it with the admin design system but is not strictly required.*

- [x] 10.8.1 `GET /admin/api-keys` — card list with: name, service domain, prefix (masked), is_active badge, last used, created by, actions (revoke, rotate). **Implemented as card-based layout in `ApiKeysAdmin.vue` with pagination, search, filter by active status and service domain. Uses `TransitionGroup` for card animations. Minor deviations from spec: `created_at` date not displayed (only `created_by`); `last_used_at` shown as absolute datetime instead of relative time.**
- [x] 10.8.2 Create API key: modal form with name + service domain dropdown; on submit: show raw key ONCE with copy-to-clipboard button and warning text. **Implemented as modal on index page (not separate `/new` route). Raw key shown with copy button and "Save this key now. It cannot be recovered after closing this dialog." warning. No countdown timer (spec deviation).**
- [x] 10.8.3 Revoke confirmation dialog: destructive modal with warning about key immediately stopping. **Implemented with custom Teleport modal. Message: "This action cannot be undone. The key will stop working immediately." Close in spirit to spec wording.**
- [x] 10.8.4 Rotate flow: confirmation dialog → call rotate → show new raw key in modal. **Full two-phase flow: confirmation modal warns old key will stop → calls `adminApi.rotateApiKey()` → shows new raw key with copy button and "Done — I've saved the new key" button.**

**10.8 Architecture Notes:**
- Pre-existing Vue component: `ApiKeysAdmin.vue` (~560 lines) in `components/vue/` (not `components/admin/`)
- Backend: 5 endpoints in `AdminApiKeyController` — list, create, revoke, rotate, service-domains dropdown
- Frontend API client: 5 functions in `lib/admin.ts` — `listApiKeys`, `createApiKey`, `revokeApiKey`, `rotateApiKey`, `fetchServiceDomains` with full TypeScript types
- Does NOT use Phase 10.2 reusable components (AdminDataTable, AdminConfirmDialog, AdminStatusBadge) — uses custom card layout and hand-rolled Teleport modals
- Accepted deviations: modal-based create (not separate route), no countdown timer, absolute datetime for last used, created_at not displayed
- A future refactor to use 10.2 components would improve visual consistency but is not blocking

#### 10.9 Webhook & Audit Log Pages — DONE

*Two Vue components + two Astro pages. Webhook monitoring with retry; audit log with detail modals.*

- [x] 10.9.1 `GET /admin/webhooks` — data table: event ID, event type, status badge (processed/pending/failed), created date, error message (if failed), action (retry for failed). **Implemented as `WebhooksAdmin.vue` using AdminDataTable, AdminFilterBar, AdminStatusBadge, AdminConfirmDialog. Columns: Event ID (truncated monospace), Event Type (formatted with arrows), Status (AdminStatusBadge type="webhook"), Received (relative + absolute time), Error (red for failed), Actions (view details, retry). Retry button only shown for unprocessed events. Detail modal shows full event info. Failed count warning banner in page header when failed events exist.**
- [x] 10.9.2 Filters: event type dropdown, status dropdown, date range. **Implemented using AdminFilterBar with 2 dropdown filters (event type — 10 Stripe event types from backend HANDLED_EVENTS, status — Processed/Failed) + date range picker. Status filter maps to backend `processed` boolean param (Processed → true, Failed → false).**
- [x] 10.9.3 `GET /admin/audit-log` — data table: admin user, action (path), method, IP address, timestamp; detail modal for request details. **Implemented as `AuditLogAdmin.vue` using AdminDataTable, AdminFilterBar. Columns: Admin User (email), Action (formatted with arrows), Method (color-coded badge — GET=blue, POST=green, PUT/PATCH=amber, DELETE=red), Path (monospace truncated), IP (monospace), Status Code (color-coded — 2xx=green, 4xx=amber, 5xx=red), Time (relative + absolute), Actions (view details with JSON indicator). Detail modal shows full entry info including pretty-printed JSON details.**
- [x] 10.9.4 Filters: action type dropdown, date range. **Implemented using AdminFilterBar with 1 dropdown filter (action type — 8 action groups: Product, Plan, Subscription, Refund, API Key, User, Domain, Access Entry) + date range picker. Action filter maps to backend `action` param with icontains matching.**

**10.9 Architecture Notes:**
- Two Vue components created: `WebhooksAdmin.vue` (~500 lines), `AuditLogAdmin.vue` (~420 lines)
- Two Astro routes updated: `webhooks/index.astro`, `audit-log/index.astro` (replaced placeholders with Vue component mounts)
- All pages use 10.2 reusable components: AdminPageHeader, AdminDataTable, AdminFilterBar, AdminConfirmDialog (webhooks), AdminStatusBadge (webhooks)
- Frontend types in `lib/admin.ts` fixed to match backend schemas:
  - `WebhookEvent.processed: boolean` (was incorrectly `status: string`) — backend returns `processed` boolean, not `status` string
  - `WebhookListResponse` changed from `extends PaginatedResponse<WebhookEvent>` to standalone `{ items, total, failed_count }` — backend returns custom format, not PaginatedResponse
  - `AuditLogEntry.timestamp` (was incorrectly `created_at`) — backend uses `timestamp` field
  - `AuditLogEntry.details: Record<string, unknown>` (was `| null`) — backend returns `{}` not null
  - `listWebhooks` params: `processed: boolean` (was `status: string`) — maps to backend `processed` query param
  - `listAuditLog` params: `admin_user_id: number` + `date_from`/`date_to` (was `admin_user: string`) — matches backend query params
  - `retryWebhook` return type: full response with `id`, `event_id`, `event_type`, `processed`, `error_message`, `message` (was `{ message: string }`)
- Webhook pagination: backend returns `{ items, total, failed_count }` without PaginatedResponse meta. Frontend computes `PaginationMeta` from `total` + `pageSize`
- Backend bug fix: `meta["total"]` → `meta["total_items"]` in `AdminMetricsController.list_webhooks` — key name mismatch with `get_paginated_data_async` return dict
- `WebhooksAdmin` converts `processed: boolean` to display-friendly status string ("processed"/"failed"/"pending") via `getWebhookStatus()` helper for AdminStatusBadge compatibility

---

### Phase 11: Admin RBAC — Granular Admin Roles with Product Scoping

**Goal:** Replace the binary `is_staff` boolean with a granular role-based access control system for the admin interface. Current state: every `is_staff=True` user can access ALL admin operations across ALL products/domains. RBAC adds fine-grained permissions so a Support agent can view subscriptions but not manage products, and a Finance officer can handle refunds but not change user roles. **Critically, Sattabase is a multi-domain auth & subscription engine** — permissions must be scoppable per Product so that a "Finance Product Manager" only sees Finance data, not Analytics data.

**Backward compatibility:** Existing `is_staff=True` users with `admin_role=None` continue to get full access (implicit Super Admin) across ALL products. No behavior change until roles are explicitly assigned.

#### Three Role Layers — Critical Context

Sattabase has **three separate role/permission layers** that interact. Phase 11 must account for all three:

| Layer | Field | Values | Purpose | Scope |
|-------|-------|--------|---------|-------|
| **Tenant Role** | `User.role` | `owner`, `admin`, `member` | Position within the SaaS platform (who manages team billing) | User dashboard + team management |
| **Admin Role** (Phase 11) | `User.admin_role` → `AdminRole` | Super Admin, Product Manager, Support, Finance, Read Only, custom | Granular admin panel permissions | Admin panel (`/admin/*`) only |
| **Product Scope** (Phase 11) | `AdminRoleAssignment.scope_products` → M2M `Product` | Which products this admin can see/manage | Domain-level data isolation | Per-product filtering within admin panel |

**Why product scoping matters:** Sattabase serves multiple sister domains (e.g., `finance.sattabase.tld`, `analytics.sattabase.tld`). Each Product has its own plans, subscriptions, API keys, and users. Without product scoping, a Support agent for the Finance product would also see Analytics subscriptions — a data isolation violation in a multi-domain platform.

**Current coupling (must be reconciled):**

1. **`AdminUserController.update_user_role()`** syncs `is_staff` based on tenant role:
   - `role="owner"` → `is_staff=True` (auto-grants admin panel access)
   - `role="admin"` → `is_staff=True` (auto-grants admin panel access)
   - `role="member"` → `is_staff=False` (removes admin panel access)
2. **`useAdminGuard.ts`** grants admin panel access to `owner`/`admin` roles even without `is_staff`
3. **`create_superuser`** sets `role="owner"` + `is_staff=True` + `is_superuser=True`
4. **All admin endpoints** return data across ALL products — no product-level filtering by default (some endpoints accept `product_id` as a query filter, but it's not enforced)

**Resolution strategy:**

- **Tenant role** (`owner/admin/member`) → determines **whether** a user can access the admin panel
- **Admin role** (`AdminRole`) → determines **what actions** they can perform (read/write per domain)
- **Product scope** (`scope_products`) → determines **which products' data** they can see/modify

These three layers are independent — a user can be `role=owner` (tenant) + `admin_role=Support` (restricted actions) + `scope_products=[Finance]` (only Finance data).

**Auto-assignment rules (new):**

| Tenant Role Change | `is_staff` | `admin_role` | `scope_products` |
|--------------------|-----------|-------------|-----------------|
| → `owner` | `True` | `None` (implicit Super Admin) | None (all products — global scope) |
| → `admin` | `True` | `None` (implicit Super Admin) | None (all products — global scope) |
| → `member` | `False` | `None` | None (no admin access) |

#### 11.1 AdminRole + AdminRoleAssignment Models + Migration

- [ ] 11.1.1 Create `AdminRole` model in `billing/models.py` (after `AdminAuditLog`)

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `name` | CharField(50) | unique, indexed | e.g. "Super Admin", "Support", "Finance" |
| `description` | TextField | blank=True | Human-readable role description |
| `permissions` | JSONField | default=`[]` | List of permission strings from `AdminPermission` enum |
| `is_system` | BooleanField | default=False, indexed | System roles cannot be deleted (Super Admin, Read Only) |
| `created_at` | DateTimeField | auto_now_add | Creation timestamp |
| `updated_at` | DateTimeField | auto_now | Last modification timestamp |

- [ ] 11.1.2 Create `AdminRoleAssignment` model — the **through-model** that links a User to an AdminRole with an optional product scope. This is what makes a role assignment domain-specific:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | BigAutoField | PK | Auto primary key |
| `user` | FK(User) | CASCADE, indexed | The staff user |
| `admin_role` | FK(AdminRole) | CASCADE, indexed | The role being assigned |
| `scope_products` | M2M(Product) | blank=True | Products this assignment applies to. Empty = all products (global scope) |
| `assigned_by` | FK(User) | SET_NULL, null=True | Admin who made the assignment |
| `assigned_at` | DateTimeField | auto_now_add | When the assignment was created |
| `is_active` | BooleanField | default=True | Can be deactivated without deleting |

**Design rationale for `AdminRoleAssignment` (instead of a simple FK on User):**

A user can hold **multiple role assignments**, each scoped to different products. Examples:
- Assignment 1: `Support` role → scope: `[Finance]` (can view Finance subscriptions only)
- Assignment 2: `Finance` role → scope: `[Analytics]` (can manage Analytics refunds only)
- Single assignment: `Super Admin` role → scope: `[]` (all products — global)

The user's **effective permissions** are the union of all active assignments. For product-scoped queries, only the assignments that include the target product (or have no scope = global) contribute permissions.

- [ ] 11.1.3 Register `AdminRole` and `AdminRoleAssignment` in `billing/admin.py`. System roles are read-only. Role assignments shown as inline on User admin.
- [ ] 11.1.4 Create seed migration with 5 pre-defined system roles:

| Role | Permissions | Description |
|------|------------|-------------|
| **Super Admin** | ALL 16 permissions | Full access to everything across all products. Cannot be deleted. |
| **Product Manager** | `products:read`, `products:write`, `plans:read`, `plans:write`, `metrics:read` | Manages products, plans, and access entries. Typically scoped to specific products. |
| **Support** | `subscriptions:read`, `users:read`, `audit:read`, `metrics:read` | Views subscriptions and users for customer support. Typically scoped to specific products. |
| **Finance** | `refunds:read`, `refunds:write`, `subscriptions:read`, `metrics:read` | Manages refunds and views financial metrics. Typically scoped to specific products. |
| **Read Only** | All `:read` permissions (8 total) | Views all admin data but cannot modify anything. Cannot be deleted. |

- [ ] 11.1.5 Run `makemigrations` and `migrate`

#### 11.2 Update User Model for Backward Compatibility

- [ ] 11.2.1 Do NOT add `admin_role` FK to User model — the `AdminRoleAssignment` through-model replaces the need for a direct FK. The relationship is accessed via `user.admin_role_assignments.all()`.
- [ ] 11.2.2 Add `admin_role` property on User model for convenience:

```python
@property
def admin_role(self):
    """Return the first active admin role assignment, or None."""
    assignment = self.admin_role_assignments.filter(is_active=True).first()
    return assignment.admin_role if assignment else None
```

- [ ] 11.2.3 Add `get_effective_admin_permissions(product=None)` method on User model:

```python
def get_effective_admin_permissions(self, product=None):
    """Return union of all permissions from active assignments.

    If product is given, only include assignments whose scope
    includes the product or has no scope (global).
    If no product, return all permissions (legacy/global behavior).
    """
    if not self.is_staff:
        return []

    assignments = self.admin_role_assignments.filter(is_active=True)

    if product is not None:
        # Include global assignments (no scope_products) + assignments that include this product
        assignments = assignments.filter(
            models.Q(scope_products__isnull=True) | models.Q(scope_products=product)
        ).distinct()

    permissions = set()
    for assignment in assignments:
        permissions.update(assignment.admin_role.permissions or [])

    # Backward compat: no assignments = implicit Super Admin = all permissions
    if not self.admin_role_assignments.filter(is_active=True).exists():
        return [p.value for p in AdminPermission]

    return list(permissions)
```

- [ ] 11.2.4 Run `makemigrations` and `migrate` — no schema changes to User table (property/method only)
- [ ] 11.2.5 Update `AdminUserListSchema` and `AdminUserDetailSchema` to include `admin_role_assignments` list (each with role, scope_products, is_active)
- [ ] 11.2.6 Update frontend `UserItem` and `UserDetail` types to include `admin_role_assignments: AdminRoleAssignment[]`

#### 11.3 Permission Check Infrastructure (with Product Scoping)

- [ ] 11.3.1 Update `AdminPermission` enum in `billing/models.py` with 16 permission strings:

```
products:read, products:write, plans:read, plans:write,
subscriptions:read, subscriptions:write, users:read, users:write,
refunds:read, refunds:write, api_keys:read, api_keys:write,
audit:read, metrics:read, webhooks:read, webhooks:write
```

- [ ] 11.3.2 Create `common/admin_permissions.py` with:
  - `user_has_admin_permission(user, permission: str, product=None) -> bool` — checks permissions across all active assignments; if `product` given, only checks assignments scoped to that product or global; returns `True` if no assignments exist (backward compatible Super Admin); returns `False` if not staff
  - `user_has_any_admin_permission(user, *permissions: str, product=None) -> bool` — OR check
  - `get_user_admin_permissions(user, product=None) -> list[str]` — returns full permission list for given product context
  - `get_user_scoped_products(user) -> list[Product]` — returns products the user has any admin access to. Returns all products if global scope (no assignments or Super Admin with empty scope).
  - `user_can_access_product(user, product) -> bool` — True if user has any assignment that includes this product or is global
- [ ] 11.3.3 Create `IsAdminWithPermission` permission class in `common/permissions.py` — extends `IsAdmin`, adds configurable permission check. For endpoints with `product_id` in path, automatically extracts product and passes to permission check.
- [ ] 11.3.4 Create `@require_admin_permission("products:write")` decorator for per-endpoint granularity. For product-scoped endpoints, auto-extracts `product_id` from path/query params and enforces product scope.
- [ ] 11.3.5 Create `ScopedQuerySetMixin` — utility mixin for admin list endpoints that automatically filters querysets by the user's product scope. Example: `AdminSubscriptionController.list_subscriptions()` auto-filters to `Subscription.objects.filter(product_id__in=user_scoped_product_ids)` instead of returning all subscriptions.
- [ ] 11.3.6 Add `GET /admin/me/permissions` endpoint — returns full permission context. Response shape:

```python
{
    "tenant_role": "owner",
    "is_staff": True,
    "is_super_admin": True,             # no assignments = full access
    "assignments": [
        {
            "id": 1,
            "admin_role": {"id": 3, "name": "Support", "permissions": ["subscriptions:read", ...]},
            "scope_products": [
                {"id": 1, "name": "Satta Finance", "slug": "finance"},
            ],
            "scope_is_global": False,   # empty scope_products on this assignment
            "is_active": True,
        }
    ],
    "effective_permissions": {
        # Global permissions (union of all assignments with no product scope)
        "global": ["audit:read"],
        # Per-product permissions
        "finance": ["subscriptions:read", "users:read", "metrics:read"],
    },
    "accessible_products": [
        {"id": 1, "name": "Satta Finance", "slug": "finance"},
    ],
    "accessible_product_ids": [1],
}
```

#### 11.4 Apply Permission + Scope Checks to All Admin Controllers

- [ ] 11.4.1 `AdminProductController` — GET endpoints: `products:read` + filter to scoped products. Mutation endpoints: `products:write` + validate product is in user's scope. Admin without Finance scope cannot `GET /admin/products/{finance_id}`.
- [ ] 11.4.2 `AdminPlanController` — GET: `plans:read` + auto-filter plans to scoped products. Mutations: `plans:write` + validate plan's product is in scope.
- [ ] 11.4.3 `AdminSubscriptionController` — GET: `subscriptions:read` + auto-filter by `ScopedQuerySetMixin` (only subscriptions for scoped products). Mutations: `subscriptions:write` + validate subscription's product is in scope.
- [ ] 11.4.4 `AdminUserController` — GET: `users:read`. Mutations: `users:write`. Users and audit are **NOT product-scoped** (a user exists across all products). However, user subscriptions shown in detail view are filtered to scoped products.
- [ ] 11.4.5 `AdminRefundController` — GET: `refunds:read` + auto-filter refunds by scoped products. Mutations: `refunds:write` + validate refund's subscription product is in scope.
- [ ] 11.4.6 `AdminApiKeyController` — GET: `api_keys:read` + auto-filter by scoped products (via ServiceDomain → Product). Mutations: `api_keys:write` + validate domain's product is in scope.
- [ ] 11.4.7 `AdminMetricsController` — `metrics:read` + auto-scope metrics to scoped products. If user only has Finance scope, `metrics/overview` returns Finance-only MRR/churn. `metrics/revenue` filters `by_product` to scoped products.
- [ ] 11.4.8 Audit log endpoints: `audit:read`. Audit is **partially product-scoped** — admin actions on specific products are filterable by product, but global actions (role changes, API key management) are visible to all.
- [ ] 11.4.9 Webhook endpoints — GET: `webhooks:read`. Webhooks are **NOT product-scoped** (Stripe webhooks are global). However, retry is `webhooks:write` and remains global.
- [ ] 11.4.10 Return 403 with clear `permission_required` and `product_scope_required` fields when check fails.

**Permission + scope mapping summary:**

| Admin Controller | Permission | Product-Scoped? | Scope Enforcement |
|-----------------|-----------|----------------|-------------------|
| `AdminProductController` | `products:read/write` | ✅ Yes | Filter list to scoped products; block access to out-of-scope product IDs |
| `AdminPlanController` | `plans:read/write` | ✅ Yes | Filter by scoped products; block access to plans of out-of-scope products |
| `AdminSubscriptionController` | `subscriptions:read/write` | ✅ Yes | Filter by scoped products; block mutations on out-of-scope subscriptions |
| `AdminUserController` | `users:read/write` | ❌ No (global) | Users span all products; but subscription data in detail view is scoped |
| `AdminRefundController` | `refunds:read/write` | ✅ Yes | Filter by subscription → product; block out-of-scope refunds |
| `AdminApiKeyController` | `api_keys:read/write` | ✅ Yes | Filter by service_domain → product; block out-of-scope keys |
| `AdminMetricsController` | `metrics:read` | ✅ Yes | Filter metrics to scoped products; global metrics only for global scope |
| Audit log | `audit:read` | Partial | Product-specific actions filterable by scope; global actions visible to all |
| Webhook endpoints | `webhooks:read/write` | ❌ No (global) | Stripe webhooks are platform-wide, not per-product |

#### 11.5 Admin Role Management API Endpoints

- [ ] 11.5.1 Create `AdminRoleController` in `billing/admin_role_controller.py` — prefix `/admin/roles`, auth `JWTAuth + IsAuthenticated + IsAdmin`, requires `users:read` for GET, `users:write` for mutations
- [ ] 11.5.2 Define schemas in `billing/admin_schemas.py`: `AdminRoleListSchema`, `AdminRoleDetailSchema`, `AdminRoleCreateSchema`, `AdminRoleUpdateSchema`, `AdminRoleAssignmentSchema` (includes role, scope_products, is_active), `AdminRoleAssignmentCreateSchema` (admin_role_id, scope_product_ids, user_id)
- [ ] 11.5.3 `GET /admin/roles` — list all roles with user counts, paginated
- [ ] 11.5.4 `GET /admin/roles/{id}` — role detail with full permission list + assigned users summary
- [ ] 11.5.5 `POST /admin/roles` — create custom role (validate permission strings against `AdminPermission` enum)
- [ ] 11.5.6 `PUT /admin/roles/{id}` — update role. System roles: only description can be changed.
- [ ] 11.5.7 `DELETE /admin/roles/{id}` — delete custom role. System roles return 403.
- [ ] 11.5.8 `GET /admin/roles/permissions` — returns all available permission strings grouped by domain
- [ ] 11.5.9 `GET /admin/users/{id}/admin-role-assignments` — list all role assignments for a user (with scope info)
- [ ] 11.5.10 `POST /admin/users/{id}/admin-role-assignments` — create a new role assignment (specify admin_role_id + scope_product_ids). Validates: user is staff, role exists, products exist. Audit-logged.
- [ ] 11.5.11 `PATCH /admin/users/{id}/admin-role-assignments/{assignment_id}` — update assignment (change scope_products, toggle is_active). Audit-logged.
- [ ] 11.5.12 `DELETE /admin/users/{id}/admin-role-assignments/{assignment_id}` — remove assignment. Audit-logged.
- [ ] 11.5.13 All mutation endpoints are audit-logged via `AdminAuditLog`

#### 11.6 Tenant Role ↔ Admin Role Assignment Sync

- [ ] 11.6.1 Update `AdminUserController.update_user_role()` — after syncing `is_staff`:
  - If tenant role changed to `owner`/`admin` AND user has NO active assignments → no auto-assignment needed (backward compat: no assignments = implicit Super Admin)
  - If tenant role changed to `member` → deactivate all admin role assignments (set `is_active=False` on all `AdminRoleAssignment` rows for this user)
  - **Important:** Do NOT delete assignments on demotion — just deactivate them, so they can be reactivated if role is restored.
- [ ] 11.6.2 Validate in `POST /admin/users/{id}/admin-role-assignments` that target user has `is_staff=True`
- [ ] 11.6.3 Update user detail API response to clearly distinguish all layers:

```python
{
    "role": "owner",                           # tenant role
    "is_staff": True,                          # admin panel access gate
    "admin_role_assignments": [                # admin panel capability + scope
        {
            "id": 1,
            "admin_role": {"id": 3, "name": "Support", "permissions": [...]},
            "scope_products": [{"id": 1, "name": "Satta Finance", "slug": "finance"}],
            "scope_is_global": False,
            "is_active": True,
        }
    ],
    "effective_admin_permissions": {           # resolved for UI display
        "global": ["audit:read"],
        "finance": ["subscriptions:read", "users:read"],
    },
}
```

#### 11.7 Frontend: `useAdminPermissions` Composable

- [ ] 11.7.1 Create `frontend/src/composables/useAdminPermissions.ts`
- [ ] 11.7.2 On mount, call `GET /admin/me/permissions` — returns `{ tenant_role, is_staff, is_super_admin, assignments, effective_permissions, accessible_products, accessible_product_ids }`
- [ ] 11.7.3 Provide reactive refs: `tenantRole`, `isSuperAdmin`, `assignments`, `effectivePermissions: Record<string, string[]>` (keyed by product slug or "global"), `accessibleProducts`, `accessibleProductIds`, `isLoading`, `error`
- [ ] 11.7.4 Provide methods:
  - `hasAdminPermission(perm, productSlug?) -> ComputedRef<boolean>` — checks effective permissions for given product context (or global if no slug)
  - `canRead(domain, productSlug?) -> ComputedRef<boolean>` — shorthand for `hasAdminPermission("${domain}:read", productSlug?)`
  - `canWrite(domain, productSlug?) -> ComputedRef<boolean>` — shorthand for `hasAdminPermission("${domain}:write", productSlug?)`
  - `canAccessProduct(productSlug) -> ComputedRef<boolean>` — True if product is in accessible_products or is global
  - `getScopedProductIds() -> number[]` — returns product IDs the admin can see
- [ ] 11.7.5 Cache permissions in sessionStorage (invalidate on login/logout/role change)
- [ ] 11.7.6 Update `useAdminGuard.ts` — after checking tenant role/is_staff, also load admin permissions

#### 11.8 Frontend: Permission-Aware Admin Sidebar

- [ ] 11.8.1 Update `AdminSidebar.astro` — conditionally render nav items based on permissions:
  - Dashboard → `metrics:read`
  - Products → `products:read` + only show products in `accessibleProducts`
  - Subscriptions → `subscriptions:read`
  - Users → `users:read`
  - Refunds → `refunds:read`
  - API Keys → `api_keys:read`
  - Webhooks → `webhooks:read`
  - Audit Log → `audit:read`
- [ ] 11.8.2 Products sidebar item: if admin has scoped products, show a **sub-menu** listing only accessible products (e.g., "Finance", "Analytics"). If global scope, show flat "Products" link.
- [ ] 11.8.3 Add "Roles" nav item under System section (visible only with `users:read` permission)
- [ ] 11.8.4 Show admin role badge + scope indicator next to user name:
  - "Finance Support" (if single scoped product + role)
  - "Global Super Admin" (if no scope = all products)
  - "Multi-domain Admin" (if scoped to 2+ products)

#### 11.9 Frontend: Admin Page Component Read/Write + Scope Guards

- [ ] 11.9.1 Update all admin Vue components to check write permissions before showing action buttons (same as before, but now product-context-aware):
  - `ProductsAdmin.vue` — only show products in `accessibleProducts`. Hide Create button without `products:write`.
  - `ProductDetailAdmin.vue` — block access if product not in scope. Hide edit/toggle/delete without `products:write`.
  - `PlanDetailAdmin.vue` — block if parent product not in scope. Hide mutations without `plans:write`.
  - `SubscriptionDetailAdmin.vue` — auto-filter subscriptions to scoped products. Hide mutations without `subscriptions:write`.
  - `UsersAdmin.vue` / `UserDetailAdmin.vue` — show all users (not product-scoped) but filter displayed subscriptions to scoped products. Show two role sections (tenant + admin assignments).
  - `RefundsAdmin.vue` — auto-filter refunds to scoped products. Hide mutations without `refunds:write`.
  - `ApiKeysAdmin.vue` — auto-filter API keys to scoped products (via service domain). Hide mutations without `api_keys:write`.
  - `WebhooksAdmin.vue` — not product-scoped. Hide Retry without `webhooks:write`.
- [ ] 11.9.2 Add **product scope indicator** to page headers — "Showing Finance data" badge when scoped, "All Products" when global
- [ ] 11.9.3 Show "View Only" badge when `:read` but not `:write`
- [ ] 11.9.4 Graceful 403 handling with `permission_required` and `product_scope_required` fields
- [ ] 11.9.5 Add product filter dropdown to list pages that shows only accessible products

#### 11.10 Frontend: AdminRolesAdmin.vue Page

- [ ] 11.10.1 Create `AdminRolesAdmin.vue` component in `frontend/src/components/admin/`
- [ ] 11.10.2 Role list view — table with name, description, permission count, user count, is_system badge, actions
- [ ] 11.10.3 Create/edit role modal — permission checkbox matrix (8 domains × read/write columns)
- [ ] 11.10.4 **Product scope selector** in role assignment UI — when assigning a role to a user, show multi-select dropdown of all products. Empty selection = global scope. Show clear warning: "No products selected = access to ALL products"
- [ ] 11.10.5 User's active assignments view — card-based layout showing each assignment with role badge + product scope chips
- [ ] 11.10.6 Delete confirmation modal — blocked for system roles; warns about scope implications
- [ ] 11.10.7 Create Astro page `frontend/src/pages/admin/roles/index.astro` mounting the component
- [ ] 11.10.8 Add admin API functions to `admin.ts`: `listAdminRoles`, `getAdminRole`, `createAdminRole`, `updateAdminRole`, `deleteAdminRole`, `getPermissionGroups`, `listRoleAssignments`, `createRoleAssignment`, `updateRoleAssignment`, `deleteRoleAssignment`

#### 11.11 Audit Integration for RBAC Events

- [ ] 11.11.1 Log `admin.permission_denied` to `AdminAuditLog` (includes user, required_permission, product_scope, attempted_path)
- [ ] 11.11.2 Log `user.admin_role_assigned` (includes admin_role, scope_products, assigned_by)
- [ ] 11.11.3 Log `user.admin_role_deactivated` (when tenant role demoted to member)
- [ ] 11.11.4 Log `user.admin_role_reactivated` (when tenant role restored)
- [ ] 11.11.5 Log `admin_role.created`, `admin_role.updated`, `admin_role.deleted`
- [ ] 11.11.6 Log `admin_role_assignment.scope_changed` (when product scope modified)
- [ ] 11.11.7 Add `admin_role` and `product_id` filter options to `GET /admin/audit-log`

#### Backward Compatibility & Migration Strategy

| Scenario | `is_staff` | Assignments | Product Scope | Admin Capabilities |
|----------|-----------|-------------|---------------|-------------------|
| `role=owner` + no assignments | `True` | None | Global (all products) | Full Super Admin (unchanged) |
| `role=owner` + Support role, Finance scope | `True` | 1 active | Finance only | Support perms on Finance data only |
| `role=admin` + Finance role, Finance+Analytics scope | `True` | 1 active | Finance + Analytics | Finance perms on Finance & Analytics |
| `role=admin` + 2 assignments (different roles per product) | `True` | 2 active | Per-assignment | Different permissions per product |
| `role=member` + deactivated assignments | `False` | All inactive | N/A | No admin access (assignments preserved for reactivation) |
| `role=member` + manual `is_staff=True` | `True` | None | Global | Full Super Admin |
| Assignment deleted while assigned | Unchanged | Removed | N/A | Falls back to other assignments or implicit Super Admin |

**Key principles:**
1. **Tenant role** controls panel **entry**. **Admin role + product scope** controls panel **capabilities and data visibility**.
2. **No assignments = implicit Super Admin** (backward compatible — zero behavior change for existing staff).
3. **Product scope is additive**: multiple assignments can grant different permissions for different products. The effective permissions for a product are the union of all matching assignments.
4. **Deactivation, not deletion**: when a user is demoted to `member`, assignments are deactivated (not deleted) so they can be restored if the user is re-promoted.

Migration is **zero-downtime**: deploy backend first (permissions checked but no assignments = full access), then create assignments via admin UI, then deploy frontend.

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
| `is_staff` first, RBAC via Phase 11 | Phase 1–10 used `is_staff` boolean; Phase 11 adds `AdminRole` + `AdminRoleAssignment` with 16 granular permissions across 8 domains AND product-level scoping. Tenant role (`owner/admin/member`) remains separate — controls panel entry via `is_staff` sync; admin role + product scope controls capabilities and data visibility per sister domain. |
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
| Admin privilege escalation | Phase 11 RBAC limits what each staff role can access (16 permissions across 8 domains); `admin_role=None` = implicit Super Admin for backward compatibility |
| Subscription override abuse | All overrides are audit-logged with admin user, IP, and before/after state |
| Refund fraud | Two-person approval (initiated_by + approved_by); reason category required |
| SDK token exposure | Pattern A (proxy) recommended for backends; Pattern B (SPA) uses httpOnly cookies where possible |
| OpenAPI schema exposure | Schema is public (for SDK generation); sensitive operations require auth regardless |
| Admin frontend access | Route guard checks `is_staff` on every navigation; API rejects non-staff at auth layer |