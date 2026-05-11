# Sister Domain Connection Guide

> How to create and connect sister domains to Sattabase — the central authentication, subscription, and access-control platform.
>
> Version: 1.0 | Last Updated: May 2026

---

## Table of Contents

1. [Core Concept](#1-core-concept)
2. [Sattabase Setup for a Sister Domain](#2-sattabase-setup-for-a-sister-domain)
3. [Sister Domain Patterns](#3-sister-domain-patterns)
4. [Pattern A — Backend + Frontend (Django/Python)](#4-pattern-a--backend--frontend-djangopython)
5. [Pattern B — Backend + Frontend (Node.js/TypeScript)](#5-pattern-b--backend--frontend-nodejstypescript)
6. [Pattern C — Frontend Only (TypeScript SPA)](#6-pattern-c--frontend-only-typescript-spa)
7. [Feature Gating and Access Limits](#7-feature-gating-and-access-limits)
8. [Billing Redirect Flow](#8-billing-redirect-flow)
9. [CORS and Cross-Domain Setup](#9-cors-and-cross-domain-setup)
10. [Security Best Practices](#10-security-best-practices)
11. [Error Handling Patterns](#11-error-handling-patterns)
12. [Checklist: Connecting a New Sister Domain](#12-checklist-connecting-a-new-sister-domain)

---

## 1. Core Concept

Sattabase is the **auth and billing engine** for all sister domains. It owns the user identity, subscriptions, and feature access. Sister domains own only their **service-specific data**, scoped to each user.

```
Sattabase = WHO are you? + WHAT can you do?
Sister domain = YOUR data (scoped to who you are)

Connection = single integer: user.id
```

### The `user.id` Foreign Key

Every sister domain stores the Sattabase `user.id` (an integer) as a foreign key on every table. The sister domain **never** duplicates user profiles, passwords, or emails. It only persists `user.id` and uses it to scope all database queries.

```
Sattabase (user.id = 42)  ─── FK ───→  sister_domain.account.user_id = 42
                                         sister_domain.transaction.user_id = 42
                                         sister_domain.category.user_id = 42
```

The backend **re-validates on every request** — it never trusts the frontend's claim about who the user is. API calls use two authentication paths depending on where they originate:

- **Server-to-server** (backend → Sattabase): `X-API-Key` + `X-Service-Domain` + `Authorization: Bearer <jwt>`. The API key cryptographically proves which domain is calling, preventing domain spoofing.
- **Browser-to-Sattabase** (frontend → Sattabase directly): `X-Service-Domain` + `Authorization: Bearer <jwt>` only. No API key — it must never be exposed in browser code. The backend accepts JWT-only requests via the `IsAuthenticatedOrService` permission.

Sattabase resolves both credential types and returns the user's identity and access map scoped to the sister domain's product.

### What the SDK Handles

The SDK (Python or TypeScript) provides three modules:

| Module | Purpose | API Calls? |
|--------|---------|-----------|
| `client.auth` | Login, register, `auth/me`, refresh, verify, blacklist, password reset, email verification | Yes — HTTP calls to Sattabase |
| `client.access` | Cached feature gating — `hasAccess()`, `getAccess()`, `keys()` | Yes — wraps `auth.me()` with TTL cache |
| `client.billing` | URL constructors for billing redirects, `detectBillingUpdate()` | **No** — pure string builders |

### What the Sister Domain Handles

The sister domain handles:
- Its own database (user-isolated)
- Its own business logic
- Its own frontend/backend architecture
- Displaying the user's name/email from `auth.me()` response
- Enforcing feature gates and numeric limits from the access map
- Redirecting users to Sattabase for plan changes and subscription management

---

## 2. Sattabase Setup for a Sister Domain

Before a sister domain can connect, it must be registered in Sattabase. This is a one-time setup performed by an admin through the Sattabase Django admin or the admin API.

### Step 1: Create a Product

A product represents a billable service. Each product has one or more plans (Free, Starter, Pro, etc.).

```bash
# Via Django management command (seeds default plans)
python manage.py billing_seed_data

# Or create manually via Django admin at /admin/billing/product/
# Or via the admin API if custom products are needed
```

Each plan can have `AccessEntry` records that define feature flags. For example, a "Finance" product might have:

| Plan | Access Key | Value | Type |
|------|-----------|-------|------|
| Free | `dashboard` | `true` | boolean |
| Free | `max_bank_accounts` | `2` | integer |
| Starter | `dashboard` | `true` | boolean |
| Starter | `reports` | `true` | boolean |
| Starter | `max_bank_accounts` | `10` | integer |
| Starter | `export_pdf` | `true` | boolean |
| Pro | `dashboard` | `true` | boolean |
| Pro | `reports` | `true` | boolean |
| Pro | `max_bank_accounts` | `50` | integer |
| Pro | `export_pdf` | `true` | boolean |
| Pro | `api_access` | `true` | boolean |

### Step 2: Create a ServiceDomain

A `ServiceDomain` maps a domain name to a product. This is what the `X-Service-Domain` header resolves against.

```
Domain: finance.sattaspace.com → Product: "Satta Ledger Finance"
```

This is created via Django admin at `/admin/billing/servicedomain/`. Set `is_active=True` and `is_primary=True` (if this is the main domain for the product).

### Step 3: Create an API Key Credential

Each `ServiceDomain` has one active `ServiceCredential` (API key). The raw key is shown **only once** at creation.

**Via Django admin:**
1. Go to `/admin/billing/servicedomain/`
2. Select the domain row(s)
3. Click "Create API key credential for selected domain(s)" from the action dropdown
4. Copy the raw key from the success message — it cannot be recovered later

**Via admin API:**
```bash
curl -X POST https://sattabase.tld/api/v1/admin/api-keys/ \
  -H "Authorization: Bearer <staff_jwt>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Finance App Production",
    "service_domain_id": 1
  }'

# Response includes raw_api_key (SAVE THIS NOW):
# {
#   "raw_api_key": "sb_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ01234",
#   "api_key_prefix": "sb_live_aBcD",
#   "warning": "Save this API key now. It cannot be recovered after this response."
# }
```

The raw key format is `sb_live_` + `secrets.token_urlsafe(32)` = 50 characters total. Only the SHA-256 hash is stored in the database — the raw key is never persisted.

### Step 4: Configure CORS

The sister domain's origin must be allowed by Sattabase. There are two ways:

1. **ServiceDomain-based (automatic):** The `service_domain_cors_middleware` in Sattabase automatically adds all active `ServiceDomain.domain` values to the CORS allowed origins with a 5-minute cache. This requires no extra configuration.

2. **`PUBLIC_SITE_URL_SB` setting:** If the Sattabase frontend itself runs on a separate domain, set `PUBLIC_SITE_URL_SB` in the `.env` file. It is automatically added to both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

In production (`CORS_ALLOW_ALL_ORIGINS=False`), both methods contribute to the allowed origins list.

### Step 5: Enable API Key Enforcement

Set `SB_API_KEY_ENFORCED=True` in the Sattabase `.env` before deploying to production. In development (`SB_API_KEY_ENFORCED=False`), invalid API keys log a warning but the request continues — useful for gradual rollout.

---

## 3. Sister Domain Patterns

A sister domain can be:

| Pattern | Backend | Frontend | SDK | Data Storage |
|---------|---------|----------|-----|-------------|
| **A** — Django/Python | Django or FastAPI | Vue/React/Astro | Python SDK | PostgreSQL |
| **B** — Node.js/TypeScript | Express/Fastify/Next.js API | React/Next.js | TypeScript SDK | PostgreSQL/MySQL |
| **C** — Frontend Only | None | Vue/React SPA | TypeScript SDK | localStorage / IndexedDB |

The choice depends on the service's complexity:
- **Pattern A** suits data-heavy services (Ledger, CRM, ERP) that need server-side processing, complex queries, and background tasks.
- **Pattern B** suits teams that work in TypeScript end-to-end and want a unified language across frontend and backend.
- **Pattern C** suits lightweight tools (Notes, Bookmarks, Checklists) where data can live entirely in the browser.

All three patterns share the same authentication flow — the only difference is where `auth.me()` is called and how data is stored.

---

## 4. Pattern A — Backend + Frontend (Django/Python)

### Architecture

```
+---------------------------+         SDK (Python)         +-------------------+
|  Sister Domain             |                              |    Sattabase      |
|  (e.g., Ledger SaaS)       |                              |                   |
|                            |   X-API-Key: sb_live_...    |                   |
|  Frontend (Vue/React)      |   X-Service-Domain          |  Django Ninja API |
|    Login → SDK auth.login  |   Authorization: Bearer     |  Stripe           |
|    API calls → own backend |                              |  PostgreSQL       |
|                            |                              |                   |
|  Backend (Django)          |                              |                   |
|    SattabaseAuthMiddleware |   GET /billing/auth/me       |                   |
|    All models: user_id FK  |   → user.id, access map      |                   |
|    Own database             |                              |                   |
+---------------------------+                              +-------------------+
        |                                                       |
        |  billing_updated=1 (redirect back)                    |  Stripe
        +<------------------------------------------------------+  (payments)
```

### SDK Installation and Configuration

```bash
pip install "sattabase-sdk[redis]"
```

```python
# sister_domain/settings.py
SATTABASE_BASE_URL = "https://sattabase.tld/api/v1"
SATTABASE_SERVICE_DOMAIN = "finance.sattaspace.com"
SATTABASE_API_KEY = "sb_live_..."               # from Step 3 above
SATTABASE_AUTH_TIMEOUT = 5                      # seconds (default: 5)
SATTABASE_AUTH_CACHE_TTL = 60                   # seconds (default: 60)
```

### Django Middleware Setup

The Python SDK provides `SattabaseAuthMiddleware` that automatically calls `auth/me()` on every request and attaches user data. This is the recommended approach for Django sister domains.

```python
# sister_domain/settings.py
MIDDLEWARE = [
    # ... existing middleware (Session, CORS, CSRF, etc.)
    "sattabase_sdk.middleware.SattabaseAuthMiddleware",
    # ... view middleware
]
```

After the middleware, every request has three attributes:

```python
request.sattabase_user          # User | None
request.sattabase_access        # dict[str, Any]
request.sattabase_subscription  # SubscriptionInfo | None
```

The middleware extracts the JWT from `Authorization: Bearer` header, `access_token` cookie, or session. If `auth.me()` fails (network error, 401, etc.), all three attributes are set to `None` — graceful degradation.

### Database Models

Every table has `user_id` as the **first non-PK column**, `NOT NULL`, with a database index. Self-referencing foreign keys are safe because both rows share the same `user_id` — but always verify ownership in views.

```python
# ledger/models.py
from django.db import models
from django.conf import settings


class Account(models.Model):
    """User's financial account (bank account, cash, credit card, etc.)."""

    user_id = models.PositiveIntegerField(db_index=True)  # Sattabase user.id
    name = models.CharField(max_length=100)
    account_type = models.CharField(
        max_length=20,
        choices=[("bank", "Bank"), ("cash", "Cash"), ("credit_card", "Credit Card")],
    )
    currency = models.CharField(max_length=3, default="BDT")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ledger_accounts"
        indexes = [
            models.Index(fields=["user_id", "is_active"], name="idx_account_user_active"),
        ]

    def __str__(self):
        return f"{self.name} ({self.currency})"


class Category(models.Model):
    """User-defined transaction category for income/expense classification."""

    user_id = models.PositiveIntegerField(db_index=True)
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=10, default="folder")
    category_type = models.CharField(
        max_length=10,
        choices=[("income", "Income"), ("expense", "Expense")],
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_categories"
        unique_together = [["user_id", "name"]]
        indexes = [
            models.Index(fields=["user_id", "category_type"], name="idx_category_user_type"),
        ]


class Transaction(models.Model):
    """Financial transaction linked to an account and optional category."""

    user_id = models.PositiveIntegerField(db_index=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=[("income", "Income"), ("expense", "Expense"), ("transfer", "Transfer")],
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField(blank=True, default="")
    date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ledger_transactions"
        indexes = [
            models.Index(fields=["user_id", "date"], name="idx_transaction_user_date"),
            models.Index(fields=["user_id", "account"], name="idx_transaction_user_account"),
        ]
        ordering = ["-date"]


class Budget(models.Model):
    """Monthly spending budget per category."""

    user_id = models.PositiveIntegerField(db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    month = models.DateField()  # First day of the budget month
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ledger_budgets"
        unique_together = [["user_id", "category", "month"]]
```

**Key model design rules:**

1. **`user_id` on every table** — No exceptions. Every row belongs to exactly one user.
2. **Always indexed** — Every query starts with `WHERE user_id = ?`. Without an index, every query is a full table scan.
3. **Composite indexes for common queries** — e.g., `(user_id, date)` for date-range queries, `(user_id, is_active)` for filtered lists.
4. **`unique_together` for per-user uniqueness** — e.g., category names must be unique per user, not globally.
5. **Self-referencing FKs are user-scoped by convention** — `Transaction.account` references an `Account` that must belong to the same `user_id`. Always verify in views.
6. **No `User` model** — The sister domain does not duplicate Sattabase user data. It stores only the integer `user_id`.

### Django Views / Controllers

```python
# ledger/controllers.py
from ninja import Router
from django.http import JsonResponse

router = Router()


@router.get("/accounts")
def list_accounts(request):
    """List all accounts for the authenticated user."""
    user = request.sattabase_user
    if user is None:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    accounts = Account.objects.filter(user_id=user.id, is_active=True)
    return [
        {"id": a.id, "name": a.name, "type": a.account_type, "currency": a.currency, "balance": str(a.balance)}
        for a in accounts
    ]


@router.post("/accounts")
def create_account(request):
    """Create a new account (with plan limit check)."""
    user = request.sattabase_user
    access = request.sattabase_access

    if user is None:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    # Feature gating: check plan allows account creation
    if access.get("max_bank_accounts"):
        current_count = Account.objects.filter(user_id=user.id, is_active=True).count()
        max_allowed = int(access["max_bank_accounts"])
        if current_count >= max_allowed:
            return JsonResponse(
                {
                    "detail": f"Account limit reached ({max_allowed}). Upgrade your plan for more accounts.",
                    "code": "plan_limit_reached",
                    "upgrade_url": "https://sattabase.tld/dashboard/billing/plans/finance",
                },
                status=403,
            )

    # Create the account
    account = Account.objects.create(
        user_id=user.id,
        name=request.data.get("name", "New Account"),
        account_type=request.data.get("type", "bank"),
        currency=request.data.get("currency", "BDT"),
    )
    return {"id": account.id, "name": account.name}


@router.post("/transactions")
def create_transaction(request):
    """Create a transaction with ownership validation."""
    user = request.sattabase_user
    if user is None:
        return JsonResponse({"detail": "Authentication required"}, status=401)

    account_id = request.data.get("account_id")

    # CRITICAL: Verify the account belongs to THIS user
    try:
        account = Account.objects.get(id=account_id, user_id=user.id, is_active=True)
    except Account.DoesNotExist:
        return JsonResponse({"detail": "Account not found"}, status=404)

    # Also verify category ownership if provided
    category = None
    category_id = request.data.get("category_id")
    if category_id:
        try:
            category = Category.objects.get(id=category_id, user_id=user.id, is_active=True)
        except Category.DoesNotExist:
            return JsonResponse({"detail": "Category not found"}, status=404)

    transaction = Transaction.objects.create(
        user_id=user.id,
        account=account,
        category=category,
        transaction_type=request.data.get("type", "expense"),
        amount=request.data.get("amount", 0),
        description=request.data.get("description", ""),
        date=request.data.get("date"),
    )
    return {"id": transaction.id, "amount": str(transaction.amount)}
```

### Frontend SDK Usage

```python
# In the sister domain's Django views, or in a management command,
# or in a Celery task — the SDK works anywhere async code runs.

import asyncio
from sattabase_sdk import SattabaseClient, SattabaseConfig

config = SattabaseConfig(
    base_url="https://sattabase.tld/api/v1",
    service_domain="finance.sattaspace.com",
    api_key="sb_live_...",
)

async def get_user_access(token: str):
    async with SattabaseClient(config) as client:
        auth_me = await client.auth.me(token)
        return {
            "user_id": auth_me.user.id,
            "user_email": auth_me.user.email,
            "plan": auth_me.subscription.plan_name if auth_me.subscription else "Free",
            "access": auth_me.access,
        }
```

---

## 5. Pattern B — Backend + Frontend (Node.js/TypeScript)

### Architecture

```
+---------------------------+         SDK (TypeScript)     +-------------------+
|  Sister Domain             |                              |    Sattabase      |
|  (e.g., Analytics SaaS)    |                              |                   |
|                            |   X-API-Key: sb_live_...    |                   |
|  Frontend (Next.js/React)  |   X-Service-Domain          |  Django Ninja API |
|    Login → SDK auth.login  |   Authorization: Bearer     |  Stripe           |
|    API calls → own backend |                              |  PostgreSQL       |
|                            |                              |                   |
|  Backend (Express/Fastify) |   GET /billing/auth/me       |                   |
|    Auth middleware          |   → user.id, access map      |                   |
|    Prisma/Drizzle ORM       |                              |                   |
|    Own PostgreSQL           |                              |                   |
+---------------------------+                              +-------------------+
```

### SDK Installation

```bash
npm install @sattabase/sdk
```

### Backend Configuration

```typescript
// server/config/sattabase.ts
import { SattabaseClient, SattabaseConfig } from "@sattabase/sdk";
import { InMemoryTokenStore } from "@sattabase/sdk";

const config = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "analytics.sattaspace.com",
  apiKey: "sb_live_...",
  timeout: 10_000,
});

const tokenStore = new InMemoryTokenStore();
export const sattabaseClient = new SattabaseClient(config, tokenStore);
export { config as sattabaseConfig };
```

### Auth Middleware (Express Example)

```typescript
// server/middleware/requireAuth.ts
import type { Request, Response, NextFunction } from "express";
import { sattabaseClient } from "../config/sattabase";

declare global {
  namespace Express {
    interface Request {
      userId?: number;
      userEmail?: string;
      access?: Record<string, boolean | number | string>;
      subscription?: { plan_name: string; status: string; is_active: boolean } | null;
    }
  }
}

export async function requireAuth(req: Request, res: Response, next: NextFunction) {
  const token = req.headers.authorization?.replace("Bearer ", "");

  if (!token) {
    return res.status(401).json({ detail: "Authentication required" });
  }

  try {
    const authMe = await sattabaseClient.auth.me(token);

    req.userId = authMe.user.id;
    req.userEmail = authMe.user.email;
    req.access = authMe.access;
    req.subscription = authMe.subscription
      ? {
          plan_name: authMe.subscription.plan_name,
          status: authMe.subscription.status,
          is_active: authMe.subscription.is_active,
        }
      : null;

    next();
  } catch (err: any) {
    if (err.constructor?.name === "AccountDeletedError") {
      return res.status(401).json({ detail: "Account deleted", code: "account_deleted" });
    }
    if (err.constructor?.name === "AccountInactiveError") {
      return res.status(401).json({ detail: "Account deactivated", code: "account_inactive" });
    }
    return res.status(401).json({ detail: "Authentication failed" });
  }
}
```

### Prisma Schema

```prisma
// prisma/schema.prisma

datasource {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model Dashboard {
  id        Int      @id @default(autoincrement())
  userId    Int      @map("user_id")   // Sattabase user.id (NOT a FK in DB)
  name      String
  config    Json     @default("{}")
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  widgets   Widget[]

  @@index([userId])
  @@map("dashboards")
}

model Widget {
  id          Int       @id @default(autoincrement())
  userId      Int       @map("user_id")
  dashboardId Int       @map("dashboard_id")
  type        String
  title       String
  positionX   Int       @default(0) @map("position_x")
  positionY   Int       @default(0) @map("position_y")
  width       Int       @default(4)
  height      Int       @default(3)
  config      Json      @default("{}")

  dashboard   Dashboard @relation(fields: [dashboardId], references: [id], onDelete: Cascade)

  @@index([userId])
  @@map("widgets")
}

model DataSource {
  id        Int      @id @default(autoincrement())
  userId    Int      @map("user_id")
  name      String
  type      String   // "postgres" | "mysql" | "api"
  config    Json     // Encrypted connection details
  isHealthy Boolean  @default(false) @map("is_healthy")
  lastCheckedAt DateTime? @map("last_checked_at")
  createdAt DateTime @default(now()) @map("created_at")

  @@index([userId])
  @@map("data_sources")
}
```

### Express Routes

```typescript
// server/routes/dashboards.ts
import { Router } from "express";
import { PrismaClient } from "@prisma/client";
import { requireAuth } from "../middleware/requireAuth";

const router = Router();
const prisma = new PrismaClient();

// List dashboards — user-isolated
router.get("/dashboards", requireAuth, async (req, res) => {
  const dashboards = await prisma.dashboard.findMany({
    where: { userId: req.userId },
    include: { widgets: true },
    orderBy: { createdAt: "desc" },
  });
  res.json(dashboards);
});

// Create dashboard — with feature gate
router.post("/dashboards", requireAuth, async (req, res) => {
  const maxDashboards = req.access?.max_dashboards
    ? Number(req.access.max_dashboards)
    : 3; // default for free plan

  const currentCount = await prisma.dashboard.count({
    where: { userId: req.userId },
  });

  if (currentCount >= maxDashboards) {
    return res.status(403).json({
      detail: `Dashboard limit reached (${maxDashboards}). Upgrade your plan.`,
      code: "plan_limit_reached",
    });
  }

  const dashboard = await prisma.dashboard.create({
    data: {
      userId: req.userId!,
      name: req.body.name || "New Dashboard",
      config: req.body.config || {},
    },
  });

  res.status(201).json(dashboard);
});

// Get single dashboard — with ownership check
router.get("/dashboards/:id", requireAuth, async (req, res) => {
  const dashboard = await prisma.dashboard.findFirst({
    where: { id: Number(req.params.id), userId: req.userId },
    include: { widgets: true },
  });

  if (!dashboard) {
    return res.status(404).json({ detail: "Dashboard not found" });
  }

  res.json(dashboard);
});
```

### Frontend SDK Usage (Browser Mode)

> **Important:** In browser/frontend code, **never include the API key**. The `apiKey` parameter is optional in the TypeScript SDK. When omitted, the SDK operates in browser mode — sending only `Authorization: Bearer` and `X-Service-Domain` headers. The Sattabase backend accepts JWT-only requests on endpoints with the `IsAuthenticatedOrService` permission.

```typescript
// src/lib/sattabase.ts
import { SattabaseClient, SattabaseConfig, LocalStorageTokenStore } from "@sattabase/sdk";

const store = new LocalStorageTokenStore("analytics:");
const config = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "analytics.sattaspace.com",
  // apiKey is OMITTED — no secret in browser code!
  debug: false,
});

export const sattabase = new SattabaseClient(config, store);

// Usage in a composable:
// const tokens = await sattabase.auth.login(email, password);
// const authMe = await sattabase.auth.me(tokens.access);
// console.log(authMe.user.display_name);
// console.log(authMe.hasAccess("export_data"));
```

---

## 6. Pattern C — Frontend Only (TypeScript SPA)

### Architecture

```
+---------------------------+         SDK (TypeScript)     +-------------------+
|  Sister Domain             |                              |                   |
|  (e.g., Notes SPA)         |   X-Service-Domain          |    Sattabase      |
|                            |   Authorization: Bearer     |                   |
|  Frontend (Vue/React SPA)  |   (no API key in browser!)  |  Django Ninja API |
|    Login → SDK auth.login  |                              |  Stripe           |
|    auth.me() → user.id     |   GET /billing/auth/me       |                   |
|    Data in localStorage    |   → user.id, access map      |                   |
|    Data in IndexedDB       |                              |                   |
+---------------------------+                              +-------------------+
```

### Data Storage Strategy

Data is stored client-side, keyed by `user.id`. When the user logs out or switches accounts, the current user's data is preserved and the new user's data is loaded.

```
localStorage key pattern:  "notesapp:{user_id}:settings"
IndexedDB database name:   "notesapp_user_{user_id}"
```

### SDK Setup (Browser Mode)

> **Important:** Pattern C has no backend — the SDK runs entirely in the browser. **Never include the API key** in browser code. When `apiKey` is omitted, the SDK sends only JWT and `X-Service-Domain` headers. The Sattabase backend accepts JWT-only requests via the `IsAuthenticatedOrService` permission.

```typescript
// src/lib/sattabase.ts
import { SattabaseClient, SattabaseConfig, LocalStorageTokenStore } from "@sattabase/sdk";

export const config = new SattabaseConfig({
  baseUrl: "https://sattabase.tld/api/v1",
  serviceDomain: "notes.sattaspace.com",
  // apiKey is OMITTED — no secret in browser code!
  debug: true, // for localhost development
});

const store = new LocalStorageTokenStore("notes:");
export const client = new SattabaseClient(config, store);
```

### Auth Flow in the SPA

```typescript
// src/composables/useAuth.ts
import { ref } from "vue";
import { client } from "@/lib/sattabase";
import type { AuthMeResponse } from "@sattabase/sdk";

const authMe = ref<AuthMeResponse | null>(null);

export function useAuth() {
  async function login(email: string, password: string) {
    const tokens = await client.auth.login(email, password);
    // Tokens are auto-stored by the SDK via LocalStorageTokenStore
    await loadProfile();
  }

  async function loadProfile() {
    authMe.value = await client.auth.me();
    // Initialize user-scoped storage
    initUserStorage(authMe.value!.user.id);
  }

  async function logout() {
    const tokens = store.getFirstTokenPair();
    if (tokens) {
      await client.auth.logout(tokens.access, tokens.refresh);
    }
    authMe.value = null;
  }

  function canAccess(feature: string): boolean {
    return authMe.value?.hasAccess(feature) ?? false;
  }

  function getLimit(key: string, defaultVal: number): number {
    const val = authMe.value?.getAccess(key, defaultVal);
    return typeof val === "number" ? val : defaultVal;
  }

  return { authMe, login, logout, loadProfile, canAccess, getLimit };
}
```

### User-Scoped IndexedDB

```typescript
// src/lib/db.ts
import { openDB, type IDBPDatabase } from "idb";

let dbInstance: IDBPDatabase | null = null;

export async function getDB(userId: number): Promise<IDBPDatabase> {
  if (dbInstance) return dbInstance;

  dbInstance = await openDB(`notesapp_user_${userId}`, 1, {
    upgrade(db) {
      if (!db.objectStoreNames.contains("notes")) {
        const store = db.createObjectStore("notes", { keyPath: "id" });
        store.createIndex("by-updated", "updatedAt");
        store.createIndex("by-folder", "folderId");
      }
      if (!db.objectStoreNames.contains("folders")) {
        db.createObjectStore("folders", { keyPath: "id" });
      }
    },
  });

  return dbInstance;
}

// Usage:
// const db = await getDB(authMe.value.user.id);
// const notes = await db.getAll("notes");
```

---

## 7. Feature Gating and Access Limits

The `auth.me()` response includes an `access` map — a dictionary of key-value pairs that define what the user can do. These are derived from the `AccessEntry` records on the user's current plan, scoped to the sister domain's product.

### Boolean Access Flags

Check if a user has access to a feature:

```python
# Python SDK
auth_me = await client.auth.me(tokens.access)

if auth_me.has_access("reports"):
    # Show the reports section
    pass

if auth_me.has_access("export_pdf"):
    # Enable the export button
    pass
```

```typescript
// TypeScript SDK
const authMe = await client.auth.me(tokens.access);

if (authMe.hasAccess("reports")) {
  // Show the reports section
}

if (authMe.hasAccess("export_pdf")) {
  // Enable the export button
}
```

The `has_access()` / `hasAccess()` method coerces values intelligently:
- `"true"`, `"1"`, `"yes"` → `true`
- `"false"`, `"0"`, `"no"` → `false`
- Non-zero integers → `true`
- `0` → `false`

### Numeric Limits

Check numeric limits (like "max 5 bank accounts"):

```python
# Python SDK
max_accounts = auth_me.get_access("max_bank_accounts", default=1)
# Returns the raw value: 5 (integer from backend)

current_count = Account.objects.filter(user_id=user.id).count()
if current_count >= int(max_accounts):
    # Redirect to upgrade
    upgrade_url = client.billing.upgrade("finance", return_url="https://finance.sattaspace.com/settings")
```

```typescript
// TypeScript SDK
const maxAccounts = authMe.getAccess("max_bank_accounts", 1);
// Returns the raw value: 5

const currentCount = await prisma.account.count({ where: { userId: req.userId } });
if (currentCount >= Number(maxAccounts)) {
  // Redirect to upgrade
}
```

### Access Module with Caching

Both SDKs provide an `access` module that caches the `auth.me()` response for a configurable TTL (default 60 seconds). This avoids calling `auth.me()` on every feature check within a short window.

```python
# Python SDK — access module
can_export = await client.access.has_access("export_pdf", token=tokens.access)
max_accounts = await client.access.get_access("max_bank_accounts", default=1, token=tokens.access)
all_keys = await client.access.keys(token=tokens.access)

# Force re-fetch after billing redirect
client.access.invalidate_cache()
```

```typescript
// TypeScript SDK — access module
const canExport = await client.access.hasAccess("export_pdf", tokens.access);
const maxAccounts = await client.access.getAccess("max_bank_accounts", 1, tokens.access);
const allKeys = await client.access.keys(tokens.access);

// Force re-fetch after billing redirect
client.access.invalidateCache();
```

### Where to Gate

Feature gates should be enforced at **two levels**:

1. **Frontend (UX):** Hide, disable, or gray out features the user doesn't have access to. Show upgrade prompts.
2. **Backend (security):** Reject requests for gated features with `403 Forbidden`. Never trust the frontend alone.

```
Frontend: "I'll hide the Export button if they don't have export_pdf access"
Backend:  "I'll reject the POST /export request with 403 if they don't have export_pdf access"
```

---

## 8. Billing Redirect Flow

Sister domains never handle billing directly. Instead, they redirect users to Sattabase's billing pages. The SDK's `billing` module constructs these URLs with zero API calls.

### Upgrade / Plan Change

When a user hits a plan limit or wants to upgrade:

```python
# Python SDK — construct upgrade URL
upgrade_url = client.billing.upgrade(
    product_slug="finance",
    return_url="https://finance.sattaspace.com/settings",
)
# → "https://sattabase.tld/dashboard/billing/plans/finance?return_url=https://finance.sattaspace.com/settings"
```

```typescript
// TypeScript SDK — construct upgrade URL
const upgradeUrl = client.billing.upgrade(
  "finance",
  "https://finance.sattaspace.com/settings",
);
```

### Subscription Management

Redirect to the plan management page:

```python
# Python SDK
manage_url = client.billing.manage_subscription(
    product_slug="finance",
    return_url="https://finance.sattaspace.com/billing",
)
```

### Stripe Customer Portal

Redirect to the Stripe-hosted portal for cancellation and invoice management:

```python
# Python SDK
portal_url = client.billing.portal(
    return_url="https://finance.sattaspace.com/dashboard",
)
```

### Detecting Billing Updates

After a user returns from a billing redirect, Sattabase appends a `billing_updated` query parameter to the `return_url`. Check this parameter to refresh the user's access data.

```python
# Python SDK
from sattabase_sdk.redirect import BillingRedirectModule

detected, value = BillingRedirectModule.detect_billing_update(request_url)
if detected and value == 1:
    # Billing was updated — refresh access
    client.access.invalidate_cache()
    auth_me = await client.auth.me(tokens.access)
elif detected and value == 0:
    # User cancelled or payment failed
    pass
```

```typescript
// TypeScript SDK
import { BillingRedirect } from "@sattabase/sdk";

const status = BillingRedirect.detectBillingUpdate(window.location.href);
if (status.updated && status.success === 1) {
  client.access.invalidateCache();
  const authMe = await client.auth.me(tokens.access);
}
```

| Return Value | Meaning |
|---|---|
| `(True, 1)` | Billing action succeeded — refresh access data |
| `(True, 0)` | Action cancelled or payment failed |
| `(False, None)` | No `billing_updated` parameter — normal page load |

---

## 9. CORS and Cross-Domain Setup

### How CORS Works for Sister Domains

When a sister domain's frontend (e.g., `https://finance.sattaspace.com`) makes API calls to Sattabase (e.g., `https://sattabase.tld`), the browser sends a CORS preflight request. Sattabase must allow the origin.

There are two mechanisms:

1. **Automatic (ServiceDomain-based):** The `service_domain_cors_middleware` in Sattabase dynamically adds all active `ServiceDomain.domain` values to the CORS allowed origins. This requires no extra configuration — just create the `ServiceDomain` record with `is_active=True`.

2. **Explicit (`PUBLIC_SITE_URL_SB`):** If the Sattabase frontend runs on its own domain (e.g., `https://app.sattabase.tld`), set `PUBLIC_SITE_URL_SB=https://app.sattabase.tld` in the Sattabase `.env`. This is automatically added to both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`.

### Behavior by Environment

| Environment | `CORS_ALLOW_ALL_ORIGINS` | Effect |
|---|---|---|
| Development (`SB_DEBUG=True`) | `True` | All origins allowed — no CORS issues |
| Production (`SB_DEBUG=False`) | `False` | Only explicitly listed origins allowed |

In production, make sure:
- The `ServiceDomain` record for the sister domain is `is_active=True`
- `PUBLIC_SITE_URL_SB` is set to the Sattabase frontend domain
- `SB_CORS_ALLOWED_ORIGINS` includes any additional domains if needed

### Sister Domain Backend Calling Sattabase

CORS is a **browser-enforced** policy. Server-to-server calls (sister domain backend calling Sattabase) are **not affected by CORS** — the SDK's HTTP client (httpx for Python, native fetch for TypeScript) does not use a browser and thus bypasses CORS entirely.

---

## 10. Security Best Practices

### Never Trust the Frontend

The backend must always re-validate the user's identity by calling `auth.me()` (or using the middleware which does it automatically). Never accept `user_id` from a request body or header without verification.

```python
# WRONG — user_id from request body, not verified
def create_account(request):
    Account.objects.create(user_id=request.data["user_id"], ...)  # SECURITY RISK

# CORRECT — user_id from auth.me() via middleware
def create_account(request):
    Account.objects.create(user_id=request.sattabase_user.id, ...)
```

### Always Verify Ownership on Related Records

When creating or updating records with foreign keys, verify the related record belongs to the same user:

```python
# WRONG — no ownership check
def create_transaction(request):
    account = Account.objects.get(id=request.data["account_id"])  # Could be another user's
    Transaction.objects.create(account=account, ...)

# CORRECT — ownership verified
def create_transaction(request):
    account = Account.objects.get(id=request.data["account_id"], user_id=request.sattabase_user.id)
    Transaction.objects.create(account=account, ...)
```

### Protect the API Key

The Sattabase API key (`sb_live_...`) must only exist on the **sister domain backend**. It must never be exposed to the frontend, committed to version control, or logged.

- Store it in environment variables, never in source code
- Use `.env` files (excluded from git via `.gitignore`)
- The SDK stores it in memory only — it is never persisted to disk
- **In the TypeScript SDK, `apiKey` is optional** — omit it in browser/frontend code. The SDK automatically operates in browser mode, sending only `Authorization: Bearer` and `X-Service-Domain` headers
- The backend accepts JWT-only requests via the `IsAuthenticatedOrService` permission — no API key needed for browser-originated requests

### Why the API Key Still Matters for Backend

The API key serves a **different purpose** than JWT. While JWT proves *who the user is*, the API key proves *which domain is calling*. This is critical for:

1. **Server-to-server calls**: When a backend calls Sattabase without a user's JWT, the API key is the only way to authenticate and resolve the domain
2. **Domain spoofing prevention**: The API key is cryptographically bound to a `ServiceDomain` in the database. The middleware cross-checks the `X-Service-Domain` header against the key's bound domain, preventing a compromised server from impersonating another domain
3. **Trusted domain resolution**: On `GET /billing/auth/me`, the backend uses the API key's bound domain as the **priority** source for domain resolution (over the untrusted `X-Service-Domain` header)

In short: JWT = *user identity*, API key = *domain identity*. Both are needed for secure server-to-server communication, but only JWT is needed for browser-to-server communication.

### Handle Account Lifecycle Events

Sattabase communicates account status changes through the `auth.me()` response and specific error codes:

| Error | SDK Exception | Meaning | Action |
|---|---|---|---|
| Account deactivated | `AccountInactiveError` | Admin deactivated the account | Force logout, show "contact support" |
| Account deleted | `AccountDeletedError` | User soft-deleted their account | Force logout, clear local data |
| Email not verified | `AccountNotActiveError` (403) | User hasn't verified email | Redirect to email verification |

```python
# Python SDK — handle lifecycle events
try:
    auth_me = await client.auth.me(token)
except AccountDeletedError:
    # Clear all local data for this user
    force_logout_and_clear_data()
except AccountInactiveError:
    # Show "account deactivated" message
    show_deactivated_notice()
except AccountNotActiveError:
    # Redirect to email verification
    redirect_to_verify_email()
except AuthenticationError:
    # Token expired — redirect to login
    redirect_to_login()
```

### Use HTTPS in Production

The SDK enforces HTTPS by default. The `debug` flag relaxes this for local development:

```python
# Development — allows http://
config = SattabaseConfig(base_url="http://localhost:8000/api/v1", ..., debug=True)

# Production — HTTPS required
config = SattabaseConfig(base_url="https://sattabase.tld/api/v1", ..., debug=False)
```

---

## 11. Error Handling Patterns

### Backend Error Handling

Both SDKs map HTTP errors to typed exceptions with a priority system:

1. Match by `code` field from response body (e.g., `account_deleted`) — most specific
2. Fall back to HTTP status code (e.g., 401 → `AuthenticationError`)
3. Final fallback: `ApiServerError` (5xx or network failure)

```python
# Python SDK — exception hierarchy
try:
    auth_me = await client.auth.me(token)
except AccountDeletedError as exc:
    logger.info("User deleted their account: %s", exc.message)
    force_logout()
except AccountInactiveError as exc:
    logger.info("Account deactivated: %s", exc.message)
    force_logout()
except RateLimitError as exc:
    # Retry after the suggested delay
    await asyncio.sleep(exc.retry_after or 60)
except AuthenticationError:
    # Token expired or invalid
    redirect_to_login()
except SattabaseError as exc:
    # Generic — log and show error
    logger.error("Sattabase error: %s (status=%d)", exc.message, exc.status)
```

```typescript
// TypeScript SDK — exception hierarchy
try {
  const authMe = await client.auth.me(token);
} catch (err) {
  if (err instanceof AccountDeletedError) {
    // User deleted their account
    forceLogout();
  } else if (err instanceof AccountInactiveError) {
    // Account deactivated
    showDeactivatedNotice();
  } else if (err instanceof RateLimitError) {
    // Wait and retry
    await new Promise((r) => setTimeout(r, err.retryAfter ?? 60_000));
  } else if (err instanceof SattabaseError) {
    console.error(`Sattabase error: ${err.message} (status=${err.status})`);
  }
}
```

### Middleware Graceful Degradation

The Python SDK's Django middleware never crashes your app. On any failure, it sets all request attributes to `None`:

```python
def my_view(request):
    # Always check — middleware sets these to None on failure
    if request.sattabase_user is None:
        return redirect("login")

    # Safe to use — middleware guarantees these are valid when user is not None
    user_id = request.sattabase_user.id
    access = request.sattabase_access

    if "reports" in access:
        # Show reports
        pass
```

---

## 12. Checklist: Connecting a New Sister Domain

### Sattabase Side (one-time admin setup)

- [ ] Create a `Product` (or use existing) with appropriate plans
- [ ] Create `AccessEntry` records for each plan (feature flags and limits)
- [ ] Create a `ServiceDomain` record with `domain`, `product`, `is_active=True`
- [ ] Create a `ServiceCredential` (API key) for the domain — save the raw key
- [ ] Set `SB_API_KEY_ENFORCED=True` in production
- [ ] Verify CORS: the sister domain origin is either a registered `ServiceDomain` or in `SB_CORS_ALLOWED_ORIGINS`

### Sister Domain Side (application code)

- [ ] Install the appropriate SDK (`pip install sattabase-sdk` or `npm install @sattabase/sdk`)
- [ ] Configure `SattabaseConfig` with `base_url`, `service_domain`, and `api_key` (server) or omit `api_key` (browser)
- [ ] Store API key in environment variables (never in source code or browser code)
- [ ] Set up auth middleware (Django middleware or Express middleware)
- [ ] Design all database models with `user_id` (NOT NULL, indexed) on every table
- [ ] Implement ownership validation on all foreign key lookups
- [ ] Implement feature gating at both frontend and backend levels
- [ ] Implement numeric limit enforcement at the backend level
- [ ] Set up billing redirect URLs for upgrade and plan management
- [ ] Handle `billing_updated` parameter on return from billing redirect
- [ ] Handle `AccountDeletedError`, `AccountInactiveError`, `AccountNotActiveError`
- [ ] Test with both a Free plan user and a paid plan user
- [ ] Test cross-user isolation (User A cannot access User B's data)

---

## Architecture Overview

```
+-------------------+         SDK Scope          +-------------------+
|                   |  (Auth + Permissions)      |                   |
|  Sister Domain    | <========================> |    Sattabase      |
|  (any service)    |                            |   (this platform) |
|                   |                            |                   |
|  - Any backend    |   X-API-Key               |  - Django Ninja   |
|  - Any frontend   |   X-Service-Domain        |  - Stripe         |
|  - Own database   |   Authorization: Bearer    |  - User records   |
|    Uses user.id   |                            |  - Subscriptions  |
|    as foreign key |                            |  - Access entries |
+-------------------+                            +-------------------+
        |                                                |
        |  billing_updated=1                              |  Stripe
        |  (redirect back)                                |  (payments)
        +<-----------------------------------------------+
```

**Key principles:**

- **SDK surface is small and stable** — auth schemas rarely change, while billing schemas change often. This keeps the SDK version-pinned and reliable.
- **Each sister domain has its own database** — the SDK provides only the identity layer (who is this user?) and permission layer (what can they do?). The sister domain uses `user.id` as a foreign key for its own data models.
- **Billing is never proxied** — for subscription management, plan changes, and cancellations, the SDK generates redirect URLs to Sattabase. Stripe is the single source of truth for all payment state.
- **Auto-refresh is built-in** — when enabled, the SDK automatically handles token refresh on 401 responses using an async lock (Python) or promise-based lock (TypeScript) to prevent race conditions.
- **Graceful degradation** — the Django middleware never crashes your app. On Sattabase failures, it sets all request attributes to `None`.
- **Zero dependencies (TypeScript SDK)** — uses native `fetch`, works in browser and Node.js 18+.
