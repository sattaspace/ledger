# Sattabase — Development Documentation

> Central Auth & Subscription Platform for Multi-Tenant SaaS
> Version: 2.0.0 | Last Updated: April 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Environment Setup](#5-environment-setup)
6. [Backend — Data Models](#6-backend--data-models)
7. [Backend — Pydantic Schemas](#7-backend--pydantic-schemas)
8. [Backend — Service Layer](#8-backend--service-layer)
9. [Backend — API Endpoints](#9-backend--api-endpoints)
10. [Authentication System](#10-authentication-system)
11. [Billing & Subscription System](#11-billing--subscription-system)
12. [Service-to-Service Auth (SDK Prerequisites)](#12-service-to-service-auth-sdk-prerequisites)
13. [Frontend — Library Layer](#13-frontend--library-layer)
14. [Frontend — Components & Pages](#14-frontend--components--pages)
15. [Security](#15-security)
16. [Infrastructure](#16-infrastructure)
17. [Conventions & Patterns](#17-conventions--patterns)

---

## 1. Project Overview

Sattabase is a full-stack multi-tenant SaaS platform that serves as a central authentication and subscription management hub for multiple independent service domains. The system is built with a decoupled architecture: a Django Ninja backend serves a RESTful JSON API, while an Astro.js frontend consumes it via a centralized API client. The platform handles user registration and authentication (JWT + OTP), subscription billing (via Stripe), feature-level access control per service domain, automated background tasks (via Celery), and service-to-service authentication (via API keys).

### Core Architecture

Each service domain (e.g., `finance.sattabase.tld`, `analytics.sattabase.tld`) authenticates against Sattabase and receives domain-specific access permissions based on the user's subscription plan. The `/billing/auth/me` endpoint is the central integration point — it returns user info, subscription status, and a flat access map for the requesting domain. Service domains call this endpoint to determine which features to show or hide in their own UI.

### Key Design Decisions

- **Email as primary identifier** — the `username` field exists only for Django compatibility; all authentication uses `email` as `USERNAME_FIELD`.
- **OTP-based verification** — no token-bearing URLs; all verification flows use 6-digit OTPs sent via email and validated against Redis cache.
- **Soft delete pattern** — user accounts are never hard-deleted; `is_deleted` and `deleted_at` fields enable data retention and potential account recovery.
- **Async-first services** — every service method has both sync and async variants (`register_user` / `aregister_user`) for compatibility with Django 5.2's async ORM under Daphne/ASGI.
- **Stripe-first mutations** — all payment state changes go through Stripe first; local DB is synced via webhooks. This ensures Stripe remains the single source of truth for billing.
- **Safe plan changes** — plan changes use a two-step preview/confirm flow with a time-limited `preview_token` to prevent stale proration data.
- **Service-to-service API keys** — service domains authenticate via `X-API-Key` header with SHA-256 hashed credentials. Enforcement is opt-in via `SF_API_KEY_ENFORCED` setting for backward compatibility.
- **Dynamic CORS** — origins are checked against active `ServiceDomain` records in the database, cached for 5 minutes. Falls back to `CORS_ALLOW_ALL_ORIGINS` in DEBUG mode.
- **Separate upload endpoint for avatars** — avatar uploads use `PUT /users/me/avatar` with `multipart/form-data` (via `ninja.UploadedFile`), separate from the JSON-based profile update endpoint.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                           │
│                                                                 │
│   Astro.js 6 + Vue 3 Islands + Tailwind CSS 4                  │
│   (Port 4321)                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  JSON / multipart
                           │  JWT Bearer Auth
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO NINJA API                           │
│                      (Port 8000 / Daphne ASGI)                  │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐            │
│  │Controller │→ │   Service    │→ │  ORM / Cache   │            │
│  │  (HTTP)   │  │  (Business)  │  │  (PostgreSQL)  │            │
│  └──────────┘  └──────────────┘  └───────┬───────┘            │
│                                               │                 │
│  Apps: users | billing | common | api        │                 │
│  Auth: ninja_jwt (access + refresh + blacklist)                 │
│  Billing: Stripe SDK + Webhooks                                  │
│  Tasks: Celery + django-celery-beat                             │
│                                        ┌──────▼──────┐         │
│                                        │   Redis     │         │
│                                        │ OTP / Rate   │         │
│                                        │ Limit / Cache│        │
│                                        └──────┬──────┘         │
│                                               │                 │
│                                        ┌──────▼──────┐         │
│                                        │   Stripe    │         │
│                                        │ Payments &  │         │
│                                        │ Subscriptions│        │
│                                        └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE DOMAINS (SDK)                         │
│                                                                 │
│  finance.sattabase.tld  ──┐                                      │
│  analytics.sattabase.tld ─┤── X-Service-Domain + X-API-Key      │
│  reports.sattabase.tld   ──┘── → /billing/auth/me → access map   │
└─────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

1. **Frontend** — Vue component calls a function from `src/lib/auth.ts`
2. **API Client** — `src/lib/api.ts` wraps the call with JWT headers and error handling
3. **Middleware** — `service_domain_cors_middleware` checks origin, injects CORS headers
4. **Backend Router** — Ninja Extra auto-discovers controllers, routes to handler
5. **Controller** — validates rate limit, parses payload via Pydantic schema
6. **Service** — executes business logic (OTP generation, cache checks, DB writes, Stripe calls)
7. **Response** — serialized via `ModelSchema` / `Schema`, returned as JSON

### Authentication Flow

```
Register ──→ Auto-send email verify OTP
    │
    ▼
Login ──→ Validate credentials ──→ Issue JWT pair ──→ Record login history
    │
    ├─ Access Token (60 min) — used in Authorization: Bearer header
    └─ Refresh Token (7 days) — used to obtain new token pair
         │
         └─ 401 response → auto-refresh via api.ts → retry original request
```

### Billing Flow (Checkout)

```
User selects plan ──→ POST /billing/subscriptions/{slug}/checkout
    │                      │
    │                      ├─ Create/get Stripe customer
    │                      ├─ Create Stripe Checkout session
    │                      └─ Return checkout_url
    │
    ▼
Stripe Checkout ──→ Payment success/failure
    │
    ▼
Webhook: checkout.session.completed ──→ Create/activate local subscription
    │
    ▼
GET /billing/auth/me ──→ Returns updated subscription + access map
```

---

## 3. Tech Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Framework | Django + Django Ninja | 5.2 / latest |
| ASGI Server | Daphne | latest |
| Database | PostgreSQL | latest |
| Cache / Broker | Redis | latest |
| Task Queue | Celery + django-celery-beat | latest |
| Payments | Stripe Python SDK | latest |
| JWT | ninja_jwt | latest |
| API Framework | ninja_extra | latest |
| CORS | django-cors-headers | latest |
| Email | Django SMTP (Gmail) | — |
| File Storage | Django FileSystemStorage (Pillow) | — |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Framework | Astro.js | 6.x |
| UI Islands | Vue 3 | 3.5+ |
| Styling | Tailwind CSS | 4.x |
| Language | TypeScript | 5.9+ |
| Runtime | Node.js | 22.12+ |
| Build | Vite (via Astro) | — |

### Infrastructure

| Component | Technology |
|---|---|
| Containers | Docker Compose (PostgreSQL, Redis) |
| Tunneling | ngrok (for local development) |
| Version Control | Git + GitHub |

---

## 4. Project Structure

```
sattaledger/
├── backend/
│   ├── api/                          # API configuration
│   │   ├── views.py                  # NinjaExtraAPI instance, exception handlers
│   │   └── ...
│   ├── common/                       # Shared cross-app utilities
│   │   ├── models.py                 # TimeStampedModel, SoftDeleteModel, ActivatorModel
│   │   ├── permissions.py            # IsAuthenticated, IsAdmin, IsVerified, IsSelfOrAdmin, IsServiceAuthenticated
│   │   ├── rate_limit.py             # check_rate_limit(), get_client_ip()
│   │   ├── exceptions.py             # UnauthorizedException, ForbiddenException, NotFoundException, etc.
│   │   ├── schemas.py                # PaginationInput, PaginatedResponse, MessageResponse, ApiKey schemas
│   │   ├── utils.py                  # get_paginated_data(), generate_api_key()
│   │   ├── cors_middleware.py        # service_domain_cors_middleware (dynamic CORS)
│   │   ├── api_key_auth.py           # validate_api_key() — service-to-service auth
│   │   ├── controllers.py            # AdminApiKeyController (4 endpoints)
│   │   └── management/commands/      # seed_exchange_rates, billing_seed_data
│   ├── users/                        # User authentication & profile app
│   │   ├── models.py                 # User, UserLoginHistory, Choice constants
│   │   ├── managers.py               # CustomUserManager (sync + async)
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── services.py               # AuthService, UserService (business logic)
│   │   ├── controllers.py            # AuthController, UserController (HTTP routing)
│   │   ├── admin.py                  # Django admin registration
│   │   ├── signals.py                # Model signals
│   │   └── migrations/               # Database migrations
│   ├── billing/                      # Billing & subscription app
│   │   ├── models.py                 # 13 models: Product, Plan, Subscription, etc.
│   │   ├── schemas.py                # 21+ Pydantic schemas for billing
│   │   ├── services.py               # BillingService (subscription logic)
│   │   ├── controllers.py            # 4 controllers: Public, Protected, Admin, Webhook
│   │   ├── currency_service.py       # Multi-currency conversion (exchange rates)
│   │   ├── stripe_errors.py          # Stripe error translation
│   │   ├── tasks.py                  # 6 Celery tasks (dunning, revenue, etc.)
│   │   ├── admin.py                  # Django admin (12 models, inlines, read-only)
│   │   ├── stripe/                   # Stripe SDK wrapper (isolation layer)
│   │   │   ├── client.py             # Low-level Stripe adapter (ONLY file importing `stripe`)
│   │   │   ├── customer.py           # Customer management
│   │   │   ├── checkout.py           # Checkout sessions + return_url validation
│   │   │   ├── portal.py             # Customer portal sessions
│   │   │   ├── prices.py             # Price resolution
│   │   │   ├── gdpr.py               # GDPR compliance
│   │   │   └── webhooks/             # Webhook processing
│   │   │       ├── router.py         # Entry point: verify, record, process, reconcile
│   │   │       ├── sync.py           # sync_subscription_from_stripe
│   │   │       └── handlers/         # 10 event handlers (checkout, subscription, invoice, charge)
│   │   └── tests/                    # 6 test files
│   ├── sattaledger/                  # Django project settings
│   │   ├── settings.py               # All configuration
│   │   ├── urls.py                   # Root URL configuration
│   │   ├── asgi.py                   # ASGI entry (Daphne)
│   │   └── ...
│   ├── manage.py
│   └── media/                        # Uploaded files (avatars)
│       └── avatars/YYYY/MM/
│
├── frontend/
│   ├── src/
│   │   ├── lib/                      # Shared utilities
│   │   │   ├── api.ts                # Centralized API client (fetch wrapper)
│   │   │   ├── auth.ts               # Auth functions + types + choice options
│   │   │   └── toast.ts              # Toast notification system
│   │   ├── components/
│   │   │   ├── astro/                # Astro static components
│   │   │   │   ├── Navbar.astro      # Top navigation bar
│   │   │   │   ├── Sidebar.astro     # Dashboard sidebar
│   │   │   │   ├── EmptyState.astro  # Empty state display
│   │   │   │   └── LoadingSpinner.astro
│   │   │   └── vue/                  # Vue interactive islands
│   │   │       ├── LoginForm.vue
│   │   │       ├── RegisterForm.vue
│   │   │       ├── ForgotPasswordForm.vue
│   │   │       ├── ResetPasswordForm.vue
│   │   │       ├── VerifyEmailForm.vue
│   │   │       ├── ProfileCard.vue   # Profile view/edit + avatar upload
│   │   │       ├── SettingsPanel.vue # Account settings (password, email, delete)
│   │   │       ├── SearchableSelect.vue  # Reusable dropdown with search
│   │   │       └── DashboardHome.vue
│   │   ├── layouts/
│   │   │   ├── BaseLayout.astro      # Root layout
│   │   │   ├── AuthLayout.astro      # Unauthenticated layout
│   │   │   └── DashboardLayout.astro # Authenticated layout (navbar + sidebar)
│   │   ├── pages/
│   │   │   ├── index.astro           # Landing / redirect
│   │   │   ├── auth/
│   │   │   │   ├── login.astro
│   │   │   │   ├── register.astro
│   │   │   │   ├── forgot-password.astro
│   │   │   │   ├── reset-password.astro
│   │   │   │   └── verify-email.astro
│   │   │   └── dashboard/
│   │   │       ├── index.astro
│   │   │       ├── profile.astro     # Profile management
│   │   │       └── settings.astro    # Account settings
│   │   └── env.d.ts
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml                # PostgreSQL + Redis
├── enhancement_plan.md               # Enhancement roadmap (Phases 1-8)
├── dev_docs.md                       # This file
└── .env                              # Environment variables (not in repo)
```

---

## 5. Environment Setup

### Prerequisites

- Python 3.10+
- Node.js 22.12+
- Docker & Docker Compose
- Git

### Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services
docker ps
# → local-postgres on port 5432
# → local-redis on port 6379
```

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install django daphne ninja-extra ninja_jwt django-ninja-jwt-token-blacklist \
    django-cors-headers django-redis channels django-celery-results \
    django-celery-beat django-environ Pillow stripe

# Create .env file (see Environment Variables section below)

# Run migrations
python manage.py migrate

# Seed billing data (optional — creates sample products, plans, domains)
python manage.py billing_seed_data

# Seed exchange rates (optional)
python manage.py seed_exchange_rates

# Create superuser
python manage.py createsuperuser

# Start development server (Daphne ASGI)
daphne -b 0.0.0.0 -p 8000 sattaledger.asgi:application

# Start Celery worker (for background tasks)
celery -A sattaledger worker -l info

# Start Celery beat scheduler (for periodic tasks)
celery -A sattaledger beat -l info
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Development server (port 4321)
npm run dev

# Type checking
npm run check

# Production build
npm run build
```

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SF_DEBUG` | Debug mode | `True` |
| `SF_SECRET_KEY` | Django secret key | `django-insecure-...` |
| `SF_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `SFDB_NAME` | PostgreSQL database name | `django_db` |
| `SFDB_USER` | PostgreSQL username | `django_user` |
| `SFDB_PASSWORD` | PostgreSQL password | `django_password` |
| `SFDB_HOST` | PostgreSQL host | `localhost` |
| `SFDB_PORT` | PostgreSQL port | `5432` |
| `SF_REDIS_HOST` | Redis host | `localhost` |
| `SF_REDIS_PORT` | Redis port | `6379` |
| `SF_EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `SF_EMAIL_PORT` | SMTP port | `587` |
| `SF_EMAIL_HOST_USER` | SMTP username | `ledger@gmail.com` |
| `SF_EMAIL_HOST_PASSWORD` | SMTP password (app password) | `app-specific-pass` |
| `SF_DEFAULT_FROM_EMAIL` | Sender email | `ledger@gmail.com` |
| `JWT_SIGNING_KEY` | JWT signing key (prod) | `your-random-key` |
| `JWT_ACCESS_TOKEN_MINUTES` | Access token lifetime | `60` |
| `JWT_REFRESH_TOKEN_DAYS` | Refresh token lifetime | `7` |
| `SF_STRIPE_SECRET_KEY` | Stripe secret key | `sk_live_...` |
| `SF_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | `pk_live_...` |
| `SF_STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `whsec_...` |
| `SF_STRIPE_APP_DOMAIN` | Sattabase app domain | `https://sattabase.tld` |
| `SF_API_KEY_ENFORCED` | Enforce X-API-Key on auth/me | `False` |
| `VITE_API_BASE_URL` | Frontend API URL | `http://localhost:8000/api/v1` |

> **Note**: In production, `JWT_SIGNING_KEY` must be explicitly set and must differ from `SF_SECRET_KEY`. The server will refuse to start without it.

---

## 6. Backend — Data Models

### Abstract Base Models (`common/models.py`)

#### TimeStampedModel

Automatically tracks creation and modification timestamps on every model that inherits it.

| Field | Type | Description |
|---|---|---|
| `created_at` | DateTimeField | Auto-set on creation (`auto_now_add=True`) |
| `updated_at` | DateTimeField | Auto-updated on every save (`auto_now=True`) |

#### SoftDeleteModel

Provides soft-delete functionality. Instead of permanently deleting records, marks them as deleted with a timestamp.

| Field | Type | Default | Description |
|---|---|---|---|
| `is_deleted` | BooleanField | `False` | Whether the record has been soft-deleted |
| `deleted_at` | DateTimeField | `null` | Timestamp of deletion |

**Methods:**
- `soft_delete()` — sets `is_deleted=True` and `deleted_at=now()`
- `restore()` — sets `is_deleted=False` and `deleted_at=None`

#### ActivatorModel

Tracks activation status of records.

| Field | Type | Default | Description |
|---|---|---|---|
| `is_active` | BooleanField | `True` | Whether the record is active |
| `activated_at` | DateTimeField | `null` | Timestamp of activation |

**Methods:**
- `activate()` — sets `is_active=True` and `activated_at=now()`
- `deactivate()` — sets `is_active=False`

### User Model (`users/models.py`)

Inherits from `AbstractUser`, `TimeStampedModel`, and `SoftDeleteModel`.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `username` | CharField(150) | nullable, not unique | Legacy field (not used for auth) |
| `slug` | UUIDField | unique, db_index, auto-generated | Public identifier for URLs |
| `email` | EmailField(255) | unique, db_index, `USERNAME_FIELD` | Primary identifier |
| `first_name` | CharField(150) | blank | First name |
| `last_name` | CharField(150) | blank | Last name |
| `phone` | CharField(30) | blank, default `""` | Phone number |
| `avatar` | ImageField | blank, null, upload `avatars/%Y/%m/` | Profile picture |
| `timezone` | CharField(50) | ChoiceField, default `UTC` | IANA timezone |
| `currency` | CharField(3) | ChoiceField, default `USD` | ISO 4217 currency code |
| `language` | CharField(10) | ChoiceField, default `en` | ISO 639-1 language code |
| `is_email_verified` | BooleanField | default `False` | Email verification status |
| `last_login_ip` | GenericIPAddressField | nullable | IP of last login |
| `role` | CharField(20) | ChoiceField, default `member` | User role (owner/admin/member) |
| `is_active` | BooleanField | from AbstractUser | Account active status |
| `is_deleted` | BooleanField | from SoftDeleteModel | Soft-delete flag |
| `deleted_at` | DateTimeField | from SoftDeleteModel | Deletion timestamp |
| `created_at` | DateTimeField | from TimeStampedModel | Creation timestamp |
| `updated_at` | DateTimeField | from TimeStampedModel | Last modification |

**Database table:** `users_user`

**Properties:**
- `full_name` — `"First Last"` or falls back to email
- `display_name` — first name or email prefix (before `@`)

**Choice Fields:**

| Field | Choices | Count |
|---|---|---|
| Role | owner, admin, member | 3 |
| Timezone | UTC + 54 IANA timezones | 55 |
| Currency | USD, EUR, GBP, JPY, ... | 40 |
| Language | en, es, fr, de, ... | 30 |

### UserLoginHistory Model (`users/models.py`)

Tracks every successful login event for security auditing.

| Field | Type | Description |
|---|---|---|
| `id` | BigAutoField | Primary key |
| `user` | ForeignKey(User) | Related user (CASCADE delete) |
| `ip_address` | GenericIPAddressField | Login origin IP |
| `user_agent` | TextField | Browser/client UA string (truncated to 500 chars) |
| `created_at` | DateTimeField | Login timestamp (auto) |

**Database table:** `users_login_history`

### Billing Models (`billing/models.py`)

The billing app contains 13 models organized in a hierarchical structure:

```
Product ──┬── Plan ──┬── AccessEntry
          │          └── Subscription ──┬── Refund
          │                             ├── Invoice
          │                             ├── PlanChangeLog
          │                             └── RevenueRecognitionEntry
          │
          └── ServiceDomain ── ServiceCredential
```

#### Enums

| Enum | Values |
|---|---|
| `BillingCycle` | `monthly`, `yearly`, `lifetime` |
| `SubscriptionStatus` | `active`, `past_due`, `canceled`, `trialing`, `paused`, `expired` |
| `AccessValueType` | `string`, `boolean`, `integer` |
| `RefundStatus` | `pending`, `completed`, `failed` |
| `InvoiceStatus` | `draft`, `open`, `paid`, `uncollectible`, `void` |

#### Product

Represents a subscription product (e.g., "Finance App", "Analytics Suite"). Each product has its own set of plans and service domains.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `name` | CharField | unique | Product name |
| `slug` | SlugField | unique | URL-safe identifier |
| `description` | TextField | blank | Product description |
| `icon` | ImageField | blank, null | Product icon |
| `home_url` | URLField | blank | Product home page URL |
| `is_active` | BooleanField | default `True` | Active status |
| `stripe_product_id` | CharField | blank, null | Stripe product ID |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_product`

#### ServiceDomain

Represents a domain that belongs to a product (e.g., `finance.sattabase.tld`). Used for domain-aware auth/me responses and dynamic CORS.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `domain` | CharField | unique | Domain name |
| `product` | ForeignKey(Product) | CASCADE | Parent product |
| `is_primary` | BooleanField | default `False` | Primary domain for product |
| `is_active` | BooleanField | default `True` | Active status |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_service_domain`

#### Plan

A subscription plan within a product (e.g., "Free", "Pro", "Enterprise"). Plans define pricing, billing cycles, and feature lists. Each plan has access entries that determine what features are available.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `product` | ForeignKey(Product) | CASCADE | Parent product |
| `name` | CharField(100) | | Plan name |
| `slug` | SlugField | unique with `product` | URL-safe identifier |
| `description` | TextField | blank | Plan description |
| `price_cents` | PositiveIntegerField | default `0` | Price in cents |
| `currency` | CharField(3) | default `USD` | ISO 4217 currency code |
| `billing_cycle` | CharField(20) | choices | Billing frequency |
| `trial_days` | PositiveIntegerField | default `0` | Trial period days |
| `features` | JSONField | default `list` | Feature list for display |
| `stripe_price_id` | CharField | blank, null | Stripe price ID |
| `sort_order` | PositiveIntegerField | default `0` | Display order |
| `is_active` | BooleanField | default `True` | Active status |
| `is_featured` | BooleanField | default `False` | Featured plan badge |
| `tax_inclusive` | BooleanField | default `False` | Tax included in price |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_plan`
**Unique constraint:** `(product_id, slug)`

#### AccessEntry

Defines a feature access rule for a plan. The access map returned by `/billing/auth/me` is built from these entries. Value types determine how the frontend interprets the access: boolean for feature flags, integer for limits (e.g., max bank accounts), string for configuration values.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `plan` | ForeignKey(Plan) | CASCADE | Parent plan |
| `key` | CharField(100) | unique with `plan` | Access key (e.g., `reports`, `max_bank_accounts`) |
| `value` | CharField(255) | | Access value |
| `value_type` | CharField(10) | choices | `string`, `boolean`, `integer` |
| `description` | TextField | blank | Human-readable description |

**Database table:** `billing_access_entry`
**Unique constraint:** `(plan_id, key)`

#### Subscription

Links a user to a plan and product. Tracks billing period, trial status, Stripe IDs, and dunning state. The `user` + `product` combination is unique — a user can have one subscription per product.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `user` | ForeignKey(User) | CASCADE | Subscribed user |
| `plan` | ForeignKey(Plan) | PROTECT | Current plan (protected from deletion) |
| `product` | ForeignKey(Product) | CASCADE | Parent product (denormalized) |
| `status` | CharField(20) | choices | Current subscription status |
| `stripe_subscription_id` | CharField | unique, blank | Stripe subscription ID |
| `stripe_customer_id` | CharField | blank | Stripe customer ID |
| `current_period_start` | DateTimeField | null | Billing period start |
| `current_period_end` | DateTimeField | null | Billing period end |
| `trial_start` | DateTimeField | null | Trial start |
| `trial_end` | DateTimeField | null | Trial end |
| `canceled_at` | DateTimeField | null | Cancellation timestamp |
| `expires_at` | DateTimeField | null | Expiration timestamp |
| `has_used_trial` | BooleanField | default `False` | Whether trial was used |
| `tos_accepted_at` | DateTimeField | null | Terms acceptance timestamp |
| `tos_version` | CharField(20) | blank | Terms version accepted |
| `currency` | CharField(3) | default `USD` | Subscription currency |
| `last_dunning_email_at` | DateTimeField | null | Last dunning email sent |
| `dunning_step` | PositiveIntegerField | default `0` | Current dunning escalation step |
| `past_due_at` | DateTimeField | null | When became past due |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_subscription`
**Unique constraint:** `(user_id, product_id)`

#### Refund

Tracks refund requests with Stripe integration. Supports a two-person approval workflow for larger refunds.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `subscription` | ForeignKey(Subscription) | CASCADE | Related subscription |
| `stripe_refund_id` | CharField | unique, blank | Stripe refund ID |
| `stripe_charge_id` | CharField | blank | Stripe charge ID |
| `amount_cents` | PositiveIntegerField | | Refund amount in cents |
| `currency` | CharField(3) | | ISO 4217 currency code |
| `reason` | TextField | | Refund reason |
| `status` | CharField(20) | choices | `pending`, `completed`, `failed` |
| `initiated_by` | ForeignKey(User) | SET_NULL | Admin who initiated |
| `initiated_by_ip` | GenericIPAddressField | null | Initiator IP |
| `approved_by` | ForeignKey(User) | SET_NULL | Admin who approved |
| `approved_at` | DateTimeField | null | Approval timestamp |
| `reason_category` | CharField(50) | blank | Category tag |
| `admin_notes` | TextField | blank | Internal notes |
| `stripe_response` | JSONField | null | Raw Stripe response |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_refund`

#### ExchangeRate

Stores daily exchange rates for multi-currency plan price conversion. Fetched from open exchange rate APIs.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `base_currency` | CharField(3) | | Base currency code |
| `target_currency` | CharField(3) | | Target currency code |
| `rate` | DecimalField(18,6) | | Exchange rate |
| `fetched_at` | DateTimeField | auto_now_add | When the rate was fetched |

**Database table:** `billing_exchange_rate`
**Unique constraint:** `(base_currency, target_currency)`

#### Invoice

Stores Stripe invoice data for billing history. Read-only — mutations go through Stripe.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `stripe_invoice_id` | CharField | unique | Stripe invoice ID |
| `subscription` | ForeignKey(Subscription) | PROTECT | Related subscription |
| `stripe_subscription_id` | CharField | blank | Stripe subscription ID |
| `number` | CharField | blank | Invoice number |
| `status` | CharField(20) | choices | Invoice status |
| `amount_paid_cents` | IntegerField | default `0` | Amount paid in cents |
| `amount_due_cents` | IntegerField | default `0` | Amount due in cents |
| `tax_cents` | IntegerField | default `0` | Tax in cents |
| `discount_cents` | IntegerField | default `0` | Discount in cents |
| `currency` | CharField(3) | | ISO 4217 currency code |
| `period_start` | DateTimeField | null | Billing period start |
| `period_end` | DateTimeField | null | Billing period end |
| `description` | TextField | blank | Invoice description |
| `hosted_url` | URLField | blank | Stripe hosted URL |
| `pdf_url` | URLField | blank | Stripe PDF URL |
| `stripe_fee_cents` | IntegerField | null | Stripe fee in cents |
| `stripe_fee_currency` | CharField(3) | null | Fee currency |
| `attempt_count` | IntegerField | default `0` | Payment attempt count |
| `next_payment_attempt` | DateTimeField | null | Next retry date |
| `stripe_response` | JSONField | null | Raw Stripe response |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_invoice`

#### PlanChangeLog

Records every plan change for audit trail. Tracks from/to plans, proration amounts, and who initiated the change.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `subscription` | ForeignKey(Subscription) | CASCADE | Related subscription |
| `from_plan` | ForeignKey(Plan) | PROTECT | Previous plan |
| `to_plan` | ForeignKey(Plan) | PROTECT | New plan |
| `proration_amount_cents` | IntegerField | default `0` | Proration amount |
| `currency` | CharField(3) | | ISO 4217 currency code |
| `stripe_proration_id` | CharField | blank | Stripe proration ID |
| `initiated_by` | ForeignKey(User) | SET_NULL | User who initiated |
| `proration_behavior` | CharField(20) | blank | `create_prorations` or `none` |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_plan_change_log`

#### WebhookEventLog

Records every Stripe webhook event for idempotent processing and debugging. Processed events are tracked to prevent duplicate handling.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `event_id` | CharField | unique | Stripe event ID |
| `event_type` | CharField(100) | | Event type (e.g., `invoice.payment_succeeded`) |
| `processed` | BooleanField | default `False` | Whether the event was processed |
| `error_message` | TextField | blank | Error message if processing failed |
| `payload` | JSONField | | Raw Stripe event payload |
| `created_at` | DateTimeField | auto_now_add | Event received timestamp |

**Database table:** `billing_webhook_event_log`

#### RevenueRecognitionEntry

Daily ASC 606 revenue recognition entries. Generated by the `recognize_revenue` Celery task. Each entry represents one day of recognized revenue for a subscription.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `subscription` | ForeignKey(Subscription) | CASCADE | Related subscription |
| `plan` | ForeignKey(Plan) | PROTECT | Plan at time of recognition |
| `amount_cents` | IntegerField | | Recognized amount in cents |
| `currency` | CharField(3) | | ISO 4217 currency code |
| `period_start` | DateTimeField | | Billing period start |
| `period_end` | DateTimeField | | Billing period end |
| `recognized_date` | DateField | | Date of recognition |
| `stripe_invoice_id` | CharField | blank | Source Stripe invoice |
| `source` | CharField(20) | choices | `scheduled`, `webhook`, `backfill` |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `updated_at` | DateTimeField | auto | Last modification |

**Database table:** `billing_revenue_recognition`
**Unique constraint:** `(subscription_id, recognized_date)`

#### ServiceCredential

Stores API key credentials for service-to-service authentication. The raw API key is never stored — only a SHA-256 hash. Each service domain can have one active credential.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `name` | CharField(100) | | Human-readable name (e.g., "Finance Backend") |
| `service_domain` | OneToOneField(ServiceDomain) | CASCADE | Parent service domain |
| `api_key_hash` | CharField(64) | unique, indexed | SHA-256 hash of API key |
| `api_key_prefix` | CharField(12) | indexed | First 12 chars for identification |
| `permissions` | JSONField | default `{}` | Scoped permissions (e.g., `{"auth": true}`) |
| `is_active` | BooleanField | default `True` | Can be revoked instantly |
| `last_used_at` | DateTimeField | null | Last successful auth timestamp |
| `created_at` | DateTimeField | auto | Creation timestamp |
| `created_by` | ForeignKey(User) | SET_NULL | Admin who created the key |

**Database table:** `billing_service_credential`
**API key format:** `sb_live_{43_chars}` (total 50 characters)

---

## 7. Backend — Pydantic Schemas

### User Schemas (`users/schemas.py`)

All schemas serve as both request validation contracts and automatic OpenAPI documentation.

#### Type Aliases for Choice Fields

```python
RoleType = Literal["owner", "admin", "member"]
TimezoneType = Literal["UTC", "America/New_York", ...]  # 55 values
CurrencyType = Literal["USD", "EUR", "GBP", ...]         # 40 values
LanguageType = Literal["en", "es", "fr", ...]            # 30 values
```

#### Request Schemas

| Schema | Fields | Used By |
|---|---|---|
| `RegisterInputSchema` | email, password, first_name, last_name?, timezone, currency, language | `POST /auth/register` |
| `LoginInputSchema` | email, password | `POST /auth/login` |
| `TokenRefreshInputSchema` | refresh | `POST /auth/token/refresh` |
| `TokenVerifyInputSchema` | token | `POST /auth/token/verify` |
| `TokenBlacklistInputSchema` | refresh | `POST /auth/token/blacklist` |
| `PasswordResetRequestSchema` | email | `POST /auth/password-reset/request` |
| `PasswordResetConfirmSchema` | email, otp, new_password, confirm_password | `POST /auth/password-reset/confirm` |
| `EmailVerifyRequestSchema` | email | `POST /auth/verify-email/request` |
| `EmailVerifyConfirmSchema` | email, otp | `POST /auth/verify-email/confirm` |
| `ChangeEmailRequestSchema` | current_password, new_email | `POST /users/me/change-email` |
| `ChangeEmailConfirmOTPSchema` | otp | `POST /users/me/change-email/confirm` |
| `ChangePasswordInputSchema` | current_password, new_password, confirm_password | `POST /users/me/change-password` |
| `PasswordConfirmSchema` | current_password | `POST /users/me/confirm-identity` |
| `DeleteAccountRequestSchema` | current_password | `POST /users/me/delete-account` |
| `UserProfileUpdateInputSchema` | first_name?, last_name?, phone?, timezone?, currency?, language? | `PUT /users/me` |

#### Response Schemas

| Schema | Fields | Used By |
|---|---|---|
| `TokenOutputSchema` | access, refresh | Login, token refresh |
| `UserOutputSchema` | id, slug, email, first_name, last_name, phone, avatar, timezone, currency, language, is_email_verified, is_active, role, created_at, full_name, display_name | All user profile endpoints |
| `ChoicesSchema` | timezones: ChoiceItemSchema[], currencies: ChoiceItemSchema[], languages: ChoiceItemSchema[] | `GET /auth/choices` |
| `ChoiceItemSchema` | value: str, label: str | Used inside ChoicesSchema |
| `MessageSchema` | message, success | All action endpoints |

### Billing Schemas (`billing/schemas.py`)

| Schema | Type | Key Fields | Used By |
|---|---|---|---|
| `ProductOutputSchema` | Output | id, name, slug, description, home_url, is_active, created_at | Product listing |
| `ProductDetailSchema` | Output | ProductOutputSchema + plans, service_domains | Product detail |
| `PlanOutputSchema` | ModelSchema | All plan fields + display_price, is_free, converted_price_cents | Plan listing |
| `PlanDetailSchema` | Output | PlanOutputSchema + access_entries: list[AccessEntryOutputSchema] | Plan detail |
| `AccessEntryOutputSchema` | Output | key, value (Any), description | Access entries |
| `ServiceDomainOutputSchema` | Output | id, domain, product_id, is_primary, is_active | Domain listing |
| `SubscriptionInfoSchema` | Output | plan_name, plan_slug, status, current_period_end, trial_end, is_active | auth/me response |
| `SubscriptionOutputSchema` | Output | Full subscription + computed plan_name, plan_slug, product_name, product_slug | Subscription listing |
| `SubscriptionDetailSchema` | Output | SubscriptionOutputSchema + plan: PlanDetailSchema, access: dict | Subscription detail |
| `AuthMeSchema` | Output | user: UserOutputSchema, subscription: SubscriptionInfoSchema?, access: dict | `/billing/auth/me` |
| `CheckoutInputSchema` | Input | plan_slug, billing_cycle?, tos_accepted, return_url? | Checkout creation |
| `CheckoutOutputSchema` | Output | checkout_url?, reactivated | Checkout response |
| `CheckoutConfirmInputSchema` | Input | session_id | Checkout confirmation |
| `CheckoutConfirmOutputSchema` | Output | plan_name, plan_slug, status, trial_end, current_period_end | Confirm response |
| `PortalInputSchema` | Input | return_url? | Customer portal |
| `PortalOutputSchema` | Output | portal_url | Portal response |
| `ChangePlanInputSchema` | Input | plan_slug, proration_behavior | Legacy plan change |
| `ProrationPreviewOutputSchema` | Output | subtotal, tax, total, next_billing, currency, preview_token, change_type, is_upgrade | Plan preview |
| `ConfirmPlanChangeInputSchema` | Input | plan_slug, preview_token | Plan change confirm |
| `ConfirmPlanChangeOutputSchema` | Output | plan_name, plan_slug, status, change_type, effective_when, amount_charged, currency | Confirm response |
| `RefundInputSchema` | Input | amount_cents?, reason, target_user_id?, reason_category, admin_notes | Admin refund |
| `RefundOutputSchema` | Output | refund_id, stripe_refund_id, amount_cents, currency, status | Refund response |

### Common Schemas (`common/schemas.py`)

| Schema | Type | Key Fields | Used By |
|---|---|---|---|
| `PaginationInput` | Input | page (default 1, min 1), page_size (default 20, max 100) | All paginated endpoints |
| `PaginationMeta` | Output | total_items, total_pages, current_page, page_size, has_next, has_previous | Pagination metadata |
| `PaginatedResponse[T]` | Generic | meta: PaginationMeta, results: list[T] | All paginated responses |
| `MessageResponse` | Output | message, success: True | Action confirmations |
| `ErrorResponse` | Output | detail, code? | Error responses |
| `ApiKeyCreateInputSchema` | Input | name, service_domain_id | API key creation |
| `ApiKeyOutputSchema` | Output | id, name, api_key_prefix, service_domain, permissions, is_active, last_used_at, created_at, created_by | API key listing |
| `ApiKeyCreateOutputSchema` | Output | ApiKeyOutputSchema fields + raw_api_key (shown once) | API key creation response |
| `ApiKeyRotateOutputSchema` | Output | new_api_key, old_prefix, new_prefix | API key rotation response |

### Password Validation

All password fields are validated by `_validate_password_strength()`:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character

### OTP Validation

All OTP fields are validated to be exactly 6 digits (numeric string).

---

## 8. Backend — Service Layer

### AuthService (`users/services.py`)

Handles all authentication-related operations. Every method has both sync and async variants.

| Method | Description | Async Variant |
|---|---|---|
| `register_user()` | Create new user account | `aregister_user()` |
| `authenticate_user()` | Validate email/password | `aauthenticate_user()` |
| `record_login()` | Update `last_login`, create login history entry | `arecord_login()` |
| `change_password()` | Verify current password, set new | `achange_password()` |
| `confirm_identity()` | Verify current password (gate for sensitive ops) | `aconfirm_identity()` |
| `request_password_reset()` | Generate OTP, cache it, send email | `arequest_password_reset()` |
| `confirm_password_reset()` | Validate OTP, set new password | `aconfirm_password_reset()` |
| `request_email_verification()` | Generate OTP, cache, send email | `arequest_email_verification()` |
| `confirm_email_verification()` | Validate OTP, mark email as verified | `aconfirm_email_verification()` |
| `request_email_change()` | Verify password, validate new email, generate OTP | `arequest_email_change()` |
| `confirm_email_change_otp()` | Validate OTP, apply email change | `aconfirm_email_change_otp()` |
| `delete_account()` | Verify password, soft_delete user, deactivate | `adelete_account()` |

### UserService (`users/services.py`)

Handles user profile operations.

| Method | Description | Async Variant |
|---|---|---|
| `get_user_by_id()` | Get user by primary key | `aget_user_by_id()` |
| `get_user_by_email()` | Get user by email (returns None if not found) | `aget_user_by_email()` |
| `get_active_user_by_email()` | Get active, non-deleted user by email | `aget_active_user_by_email()` |
| `get_user_by_slug()` | Get user by public UUID slug | `aget_user_by_slug()` |
| `update_profile()` | Update whitelisted profile fields | `aupdate_profile()` |

### BillingService (`billing/services.py`)

Core billing business logic. All methods are static and have both sync and async variants.

| Method | Description |
|---|---|
| `get_active_products()` | List all active products |
| `get_product_by_slug()` | Get product by slug with plans and domains |
| `get_plans_for_product()` | List active plans for a product (with optional currency conversion) |
| `get_user_subscriptions()` | List all subscriptions for a user |
| `get_user_subscription()` | Get subscription for a specific product |
| `get_subscription_detail()` | Full subscription detail with plan and access map |
| `build_auth_me()` | Assemble auth/me response: user + subscription + access map |
| `cancel_subscription()` | Cancel subscription at period end (Stripe-first) |
| `reactivate_subscription()` | Reactivate canceled subscription |
| `create_checkout_session()` | Create Stripe checkout session with deduplication |
| `confirm_checkout()` | Confirm Stripe checkout, activate subscription |
| `preview_plan_change()` | Preview proration and generate time-limited token |
| `confirm_plan_change()` | Confirm plan change with preview token verification |
| `get_service_domain()` | Get service domain by domain name |
| `get_transaction_history()` | Get billing/transaction history from Stripe |

### CurrencyService (`billing/currency_service.py`)

Multi-currency support with exchange rate management. Rates are fetched from open exchange APIs and cached in the database.

| Function | Description |
|---|---|
| `get_exchange_rate()` | Lookup rate (direct, reverse, or cross-currency via USD) |
| `convert_price()` | Convert a price from one currency to another |
| `convert_plan_prices()` | Batch convert plan prices for display |
| `fetch_exchange_rates()` | Fetch latest rates from APIs (primary: open.er-api.com, fallback: frankfurter.app) |
| `update_exchange_rates()` | Fetch and upsert rates into database |

### OTP Management

All OTP flows follow the same pattern:

1. **Generate** — cryptographically random 6-digit string via `secrets.randbelow(1_000_000).zfill(6)`
2. **Store** — in Redis cache with 10-minute TTL
3. **Send** — via Django's `send_mail()` to the appropriate email address
4. **Validate** — compare against cached OTP, track failed attempts (max 5), invalidate after too many failures
5. **Cleanup** — delete OTP and attempt counter from cache after success or max failures

Cache key patterns:
- Password reset: `pwreset_otp:{email}`, `pwreset_attempts:{email}`
- Email verification: `email_verify_otp:{email}`, `email_verify_attempts:{email}`
- Email change: `email_change_data:{user_id}`, `email_change_attempts:{user_id}`

### Custom User Manager (`users/managers.py`)

The `CustomUserManager` extends `BaseUserManager` with:
- `create_user()` / `acreate_user()` — always sets `is_active=False`, `is_email_verified=False`
- `create_superuser()` / `acreate_superuser()` — sets `is_staff=True`, `is_superuser=True`
- `get_by_natural_key()` / `aget_by_natural_key()` — excludes soft-deleted users
- `email_exists()` / `aemail_exists()` — checks for email uniqueness
- `active()` — returns queryset of active, non-deleted users

---

## 9. Backend — API Endpoints

All endpoints are documented in the auto-generated OpenAPI spec at `/api/v1/docs`.

### Current API: 45 Endpoints

| Controller | Auth | Prefix | Endpoints |
|---|---|---|---|
| `AuthController` | Public | `/auth` | 10 |
| `UserController` | JWT | `/users` | 11 |
| `BillingPublicController` | Public | `/billing` | 3 |
| `BillingProtectedController` | JWT + Verified | `/billing` | 13 |
| `BillingAdminController` | Staff | `/billing/admin` | 5 |
| `BillingWebhookController` | Stripe-Sig | `/billing/webhooks` | 1 |
| `AdminApiKeyController` | Staff | `/admin/api-keys` | 4 (common app) |

### Public Endpoints (no auth required)

#### Authentication (`/api/v1/auth/`)

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/auth/choices` | Get timezone/currency/language choices | 200: `ChoicesSchema` |
| POST | `/auth/register` | Register new account | 201: `MessageSchema` |
| POST | `/auth/login` | Login with credentials | 200: `TokenOutputSchema` |
| POST | `/auth/token/refresh` | Refresh access token | 200: `TokenOutputSchema` |
| POST | `/auth/token/verify` | Verify access token validity | 200: `MessageSchema` |
| POST | `/auth/token/blacklist` | Blacklist a refresh token | 200: `MessageSchema` |

#### Password Reset (OTP-based)

| Method | Path | Description | Response |
|---|---|---|---|
| POST | `/auth/password-reset/request` | Request password reset OTP | 200: `MessageSchema` |
| POST | `/auth/password-reset/confirm` | Reset password with OTP | 200: `MessageSchema` |

#### Email Verification (OTP-based)

| Method | Path | Description | Response |
|---|---|---|---|
| POST | `/auth/verify-email/request` | Request verification OTP | 200: `MessageSchema` |
| POST | `/auth/verify-email/confirm` | Verify email with OTP | 200: `MessageSchema` |

#### Billing — Public (`/api/v1/billing/`)

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/billing/products` | List all active products | 200: `list[ProductOutputSchema]` |
| GET | `/billing/products/{slug}` | Product detail with plans + domains | 200: `ProductDetailSchema` |
| GET | `/billing/products/{slug}/plans` | List plans for a product | 200: `list[PlanOutputSchema]` |

### Protected Endpoints (JWT Bearer token required)

#### Profile (`/api/v1/users/`)

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/users/me` | Get current user profile | 200: `UserOutputSchema` |
| GET | `/users/{slug}` | Get user by slug | 200: `UserOutputSchema` |
| PUT | `/users/me` | Update profile fields | 200: `UserOutputSchema` |
| PUT | `/users/me/avatar` | Upload/update avatar | 200: `UserOutputSchema` |
| DELETE | `/users/me/avatar` | Remove avatar | 200: `UserOutputSchema` |

#### Account Security

| Method | Path | Description | Response |
|---|---|---|---|
| POST | `/users/me/change-password` | Change password | 200: `MessageSchema` |
| POST | `/users/me/confirm-identity` | Verify identity (password gate) | 200: `MessageSchema` |
| POST | `/users/me/change-email` | Request email change OTP | 200: `MessageSchema` |
| POST | `/users/me/change-email/confirm` | Confirm email change with OTP | 200: `MessageSchema` |
| POST | `/users/me/delete-account` | Soft-delete account | 200: `MessageSchema` |
| POST | `/users/me/logout` | Logout notification | 200: `MessageSchema` |

#### Billing — Protected (`/api/v1/billing/`)

Requires `JWTAuth + IsAuthenticated + IsVerified`.

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/billing/auth/me` | User + subscription + access map (domain-aware) | 200: `AuthMeSchema` |
| GET | `/billing/subscriptions` | List all user subscriptions | 200: `list[SubscriptionOutputSchema]` |
| GET | `/billing/subscriptions/transactions` | Transaction history from Stripe | 200 |
| GET | `/billing/subscriptions/{product_slug}` | Subscription detail for a product | 200: `SubscriptionDetailSchema` |
| POST | `/billing/subscriptions/{product_slug}/cancel` | Cancel at period end | 200: `MessageSchema` |
| POST | `/billing/subscriptions/{product_slug}/reactivate` | Reactivate canceled subscription | 200: `MessageSchema` |
| POST | `/billing/subscriptions/{product_slug}/checkout` | Create Stripe checkout session | 200: `CheckoutOutputSchema` |
| POST | `/billing/checkout/confirm` | Confirm Stripe checkout | 200: `CheckoutConfirmOutputSchema` |
| POST | `/billing/portal` | Create Stripe Customer Portal session | 200: `PortalOutputSchema` |
| POST | `/billing/subscriptions/{product_slug}/preview-plan-change` | Preview proration + get token | 200: `ProrationPreviewOutputSchema` |
| POST | `/billing/subscriptions/{product_slug}/confirm-plan-change` | Confirm plan change | 200: `ConfirmPlanChangeOutputSchema` |

### Admin Endpoints (Staff only)

#### Billing Admin (`/api/v1/billing/admin/`)

Requires `JWTAuth + IsAuthenticated + IsAdmin`.

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/billing/admin/refunds` | List all refunds | 200: `list[RefundOutputSchema]` |
| POST | `/billing/admin/refunds/{product_slug}` | Create refund (admin) | 200: `RefundOutputSchema` |
| GET | `/billing/admin/transactions` | Admin transaction history | 200 |
| POST | `/billing/admin/sync-customer/{user_id}` | Sync Stripe customer data | 200: `MessageSchema` |
| POST | `/billing/admin/export/{user_id}` | GDPR data export | 200 |

#### API Key Management (`/api/v1/admin/api-keys/`)

Requires `JWTAuth + IsAuthenticated + IsAdmin`.

| Method | Path | Description | Response |
|---|---|---|---|
| GET | `/admin/api-keys/` | List all service credentials (paginated) | 200: `PaginatedResponse[ApiKeyOutputSchema]` |
| POST | `/admin/api-keys/` | Create new API key (raw key shown once) | 201: `ApiKeyCreateOutputSchema` |
| PATCH | `/admin/api-keys/{key_id}/revoke` | Revoke API key | 200: `MessageResponse` |
| POST | `/admin/api-keys/{key_id}/rotate` | Rotate API key (revoke old, create new) | 200: `ApiKeyRotateOutputSchema` |

### Webhook Endpoint

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/billing/webhooks/stripe` | Stripe signature | Process Stripe webhook events |

### Error Response Format

All endpoints return errors in this format:

```json
{
  "detail": "Validation error",
  "errors": [
    { "field": "email", "message": "A user with this email address already exists." }
  ],
  "code": "validation_error"
}
```

For simple errors:
```json
{
  "message": "Invalid email or password.",
  "success": false
}
```

---

## 10. Authentication System

### JWT Configuration

| Setting | Default | Description |
|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | 60 minutes | Short-lived token for API access |
| `REFRESH_TOKEN_LIFETIME` | 7 days | Long-lived token for obtaining new access tokens |
| `ROTATE_REFRESH_TOKENS` | `True` | New refresh token issued on each refresh |
| `BLACKLIST_AFTER_ROTATION` | `True` | Old refresh token blacklisted after rotation |
| `ALGORITHM` | HS256 | JWT signing algorithm |
| `SIGNING_KEY` | `SECRET_KEY` (dev) / `JWT_SIGNING_KEY` (prod) | Signing key |
| `USER_ID_FIELD` | `id` | User model field stored in JWT |
| `USER_ID_CLAIM` | `user_id` | JWT claim name for user ID |

### Token Storage

Tokens are stored in `localStorage` on the client:
- `access_token` — used in `Authorization: Bearer` header
- `refresh_token` — used for token refresh

### Token Refresh Flow (Automatic)

The `api.ts` client handles 401 responses automatically:

1. Original request fails with 401
2. If a refresh token exists, call `POST /auth/token/refresh`
3. On success: store new tokens, retry original request with new access token
4. On failure: clear tokens, redirect to `/auth/login`

This is transparent to all Vue components — they simply call `apiClient.get()`, `.post()`, etc. and never handle token refresh manually.

### OTP Security

| Property | Value |
|---|---|
| OTP Length | 6 digits |
| OTP Generation | `secrets.randbelow(1_000_000).zfill(6)` (cryptographically random) |
| OTP Expiry | 10 minutes (600 seconds) |
| Max Attempts | 5 per OTP |
| After Max Failures | OTP invalidated, user must request a new one |
| Storage | Redis cache (not database) |

### Rate Limiting

Rate limiting is implemented via Redis-based sliding window. Configured per endpoint:

| Endpoint | Key Pattern | Max Attempts | Window |
|---|---|---|---|
| Register | `register:{client_ip}` | 5 | 1 hour |
| Login | `login:{client_ip}` | 10 | 15 minutes |
| Password reset request | `pwreset_req:{client_ip}` | 5 | 1 hour |
| Password reset confirm | `pwreset_confirm:{client_ip}` | 5 | 1 hour |
| Email verify request | `email_verify_req:{client_ip}` | 5 | 5 minutes |
| Email verify confirm | `email_verify_confirm:{client_ip}` | 10 | 5 minutes |
| Identity confirmation | `confirm_identity:{user_id}:{client_ip}` | 10 | 1 hour |
| Email change | `email_change:{user_id}:{client_ip}` | 5 | 1 hour |
| Email change confirm | `email_change_confirm:{user_id}:{client_ip}` | 10 | 1 hour |
| Account deletion | `delete_account:{user_id}:{client_ip}` | 3 | 1 hour |

Client IP is extracted from `X-Forwarded-For` header (supports ngrok/reverse proxy).

---

## 11. Billing & Subscription System

### Stripe Integration Architecture

The Stripe SDK is isolated in `billing/stripe/client.py` — this is the **only file** in the project that imports the `stripe` package. All other modules interact with Stripe through wrapper functions in the `billing/stripe/` directory. This isolation makes testing easy (mock `client.py`) and keeps Stripe-specific code out of business logic.

```
Controllers → Services → billing/stripe/*.py → billing/stripe/client.py → Stripe API
                     ↑
              stripe_errors.py (translates Stripe errors)
```

### Stripe SDK Wrapper (`billing/stripe/`)

| Module | Purpose |
|---|---|
| `client.py` | Low-level Stripe adapter. Wraps products, prices, customers, checkout sessions, subscriptions, invoices, portal, refunds, webhooks, payment intents. Returns plain dicts. |
| `customer.py` | `get_or_create_customer_id()`, `find_customer_id()`, `sync_customer_to_local()` |
| `checkout.py` | `create_checkout()`, `confirm_checkout()`, `validate_return_url()`, `build_success_url()`, `build_cancel_url()` |
| `portal.py` | `create_portal()` — creates Customer Portal session URL |
| `prices.py` | `ensure_product()`, `ensure_base_price()`, `resolve_price_id()` |
| `gdpr.py` | `delete_or_anonymize_customer()`, `export_user_billing_data()` |

### Webhook Processing

Webhooks are received at `POST /billing/webhooks/stripe` and processed idempotently. The system records every event in `WebhookEventLog` before processing, preventing duplicate handling.

#### Webhook Events Handled (10)

| Event | Handler | Action |
|---|---|---|
| `checkout.session.completed` | `handle_checkout_completed` | Create/activate subscription |
| `customer.subscription.created` | `handle_subscription_created` | Sync subscription from Stripe |
| `customer.subscription.updated` | `handle_subscription_updated` | Sync subscription status/plan changes |
| `customer.subscription.deleted` | `handle_subscription_deleted` | Mark subscription as canceled/expired |
| `invoice.payment_succeeded` | `handle_invoice_payment_succeeded` | Clear past_due status, record invoice |
| `invoice.payment_failed` | `handle_invoice_payment_failed` | Set past_due status, trigger dunning |
| `customer.subscription.trial_will_end` | `handle_trial_will_end` | Notify user trial ending |
| `charge.refunded` | `handle_charge_refunded` | Record refund in local DB |
| `customer.updated` | `handle_customer_updated` | Sync customer metadata |
| `invoice.created` | `handle_invoice_created` | Record draft invoice |

### Subscription Lifecycle

```
No Subscription
    │
    ▼
Checkout ──→ Stripe Checkout Session ──→ webhook: completed ──→ Active/Trialing
    │
    ├─ Cancel ──→ Canceled (still active until period end) ──→ webhook: deleted ──→ Expired
    ├─ Reactivate ──→ Active (before period end)
    │
    ├─ Plan Change (Preview → Confirm):
    │   1. POST preview-plan-change → get proration + preview_token (5-min TTL)
    │   2. POST confirm-plan-change (with preview_token) → Stripe update → webhook sync
    │
    └─ Payment Failure:
        Dunning workflow (4 steps, each with email):
        1. Day 3: Reminder
        2. Day 5: Urgent
        3. Day 7: Restrict features
        4. Day 14: Cancel subscription
```

### Plan Change Safety (Two-Step Flow)

Direct plan changes are risky because proration data can become stale between preview and execution. The two-step flow prevents this:

1. **Preview** — `POST /billing/subscriptions/{slug}/preview-plan-change` calculates proration on Stripe, stores it with a `preview_token` (JWT with 5-minute TTL, stored in Redis)
2. **Confirm** — `POST /billing/subscriptions/{slug}/confirm-plan-change` verifies the token, executes the plan change if still valid, and invalidates the token

### Multi-Currency Support

Plan prices are stored in their native currency. When a user views plans in a different currency, the system:
1. Looks up the exchange rate from `ExchangeRate` table
2. Supports direct rates (USD→EUR), reverse rates (EUR→USD), and cross-rates via USD
3. Falls back to the native price if no rate is available
4. Rates are fetched daily by the `update_exchange_rates` Celery task

### Checkout `return_url` Support

The checkout and portal flows accept an optional `return_url` parameter. When provided:
- **Checkout**: The success/cancel URLs include `return_url` as a query parameter. After Stripe checkout, the user is redirected back to the specified URL with `billing_updated=1` appended.
- **Portal**: The portal session's `return_url` is set to the provided URL.
- **Validation**: `validate_return_url()` checks the URL against registered `ServiceDomain.domain` entries plus the app's own domain, preventing open redirect attacks.
- **Backward compatibility**: All `return_url` changes are opt-in — when `return_url` is `None` (default), the original behavior is preserved. Zero impact on the standalone system.

### Celery Background Tasks

Six automated tasks run on schedules managed by `django-celery-beat` (DatabaseScheduler):

| Task | Schedule | Description |
|---|---|---|
| `reconcile_webhooks` | Every 6 hours | Retry unprocessed webhook events |
| `sync_customer_data` | Daily | Sync Stripe customer metadata to local DB |
| `dunning_retry` | Daily | 4-step dunning escalation for past-due subscriptions |
| `update_exchange_rates` | Daily | Fetch latest exchange rates from APIs |
| `cleanup_stale_webhook_events` | Weekly | Delete webhook events older than 90 days |
| `recognize_revenue` | Daily | ASC 606 daily revenue recognition |

#### Dunning Workflow (4-Step Escalation)

Automated recovery for past-due subscriptions:

| Step | Days Past Due | Action |
|---|---|---|
| 1 | 3 days | Send reminder email |
| 2 | 5 days | Send urgent email |
| 3 | 7 days | Send final warning, restrict features |
| 4 | 14 days | Cancel subscription automatically |

### Stripe Error Translation (`billing/stripe_errors.py`)

The `handle_stripe_error()` function translates cryptic Stripe error messages into user-friendly ones. It pattern-matches on error message strings, error codes, and HTTP status classes. On 401 errors, an admin alert is sent (likely indicates a revoked API key).

### Django Admin (Billing)

All 13 billing models are registered in Django admin with:
- Read-only fieldsets (no manual data editing)
- Inlines for related models (e.g., plans inline on product, access entries inline on plan)
- Custom actions: plan comparison, subscription status changes
- The `ServiceCredentialAdmin` is fully read-only — creation is done via API endpoints only

---

## 12. Service-to-Service Auth (SDK Prerequisites)

### Overview

Service domains authenticate against Sattabase using API keys. This enables secure machine-to-machine communication where the service backend (not the user's browser) calls Sattabase API endpoints.

### API Key Authentication (`common/api_key_auth.py`)

The `validate_api_key(request)` function is called at the controller level (not as middleware) to validate service credentials:

1. **Extract** — reads `X-API-Key` from request header
2. **Hash** — SHA-256 hashes the raw key (same algorithm used at creation time)
3. **Lookup** — queries `ServiceCredential` by hash with `select_related("service_domain", "created_by")`
4. **Validate** — checks `credential.is_active` and `credential.service_domain.is_active`
5. **Audit** — atomically updates `last_used_at` via `.filter(pk=...).update()` to avoid race conditions
6. **Attach** — sets `request.service_credential` and `request.service_domain_from_key` on the request object

### Enforcement Modes

Controlled by `SF_API_KEY_ENFORCED` setting (default `False`):

| Mode | Behavior |
|---|---|
| `False` (default) | If key provided: validate it. If missing/invalid: log warning, allow request through. Backward compatible. |
| `True` (production) | If key missing or invalid: reject with 401 `UnauthorizedException`. All requests must have valid credentials. |

### Key Generation (`common/utils.py`)

```python
generate_api_key() → (raw_key, prefix, sha256_hash)
# raw_key: "sb_live_a1b2c3d4e5f6..."  (50 chars total, shown ONCE at creation)
# prefix:  "sb_live_a1"                  (first 12 chars, for log identification)
# hash:    SHA-256 hex digest            (64 chars, stored in DB)
```

The raw key is returned to the admin **exactly once** at creation time via the `POST /admin/api-keys/` endpoint. It cannot be retrieved again. If lost, the key must be rotated.

### Auth/Me Domain Resolution Priority

When `GET /billing/auth/me` receives a request, the domain is resolved in this priority order:

1. **API Key** — If `X-API-Key` is present and valid, use `request.service_domain_from_key.domain` (the domain associated with the credential)
2. **Header** — If `X-Service-Domain` header is present, look up the domain by name
3. **None** — If neither is provided, return plain user profile without subscription/access data (standalone mode)

### Dynamic CORS (`common/cors_middleware.py`)

The `service_domain_cors_middleware` dynamically checks request origins against active `ServiceDomain` records:

- Origins are cached for **5 minutes** under cache key `"sattabase_allowed_cors_origins"`
- Only `is_active=True` domains are allowed
- In DEBUG mode (`CORS_ALLOW_ALL_ORIGINS=True`), the middleware is a no-op (skips validation)
- Injected headers: `Access-Control-Allow-Origin`, `Allow-Methods`, `Allow-Headers`, `Allow-Credentials`, `Max-Age` (24h), `Expose-Headers` (`X-API-Key`, `X-Service-Domain`)
- Implemented as a function-based middleware using `@sync_and_async_middleware` decorator for Django 5.2 ASGI/WSGI compatibility with Daphne

### IsServiceAuthenticated Permission (`common/permissions.py`)

A permission class for endpoints that require valid service credentials (separate from user JWT auth):

```python
class IsServiceAuthenticated(BasePermission):
    def has_permission(self, request, view):
        return (
            hasattr(request, "service_credential")
            and request.service_credential is not None
            and request.service_credential.is_active
        )
```

### API Key Management Endpoints

| Method | Path | Description | Notes |
|---|---|---|---|
| GET | `/admin/api-keys/` | List all credentials | Paginated, filterable by `service_domain_id` and `is_active` |
| POST | `/admin/api-keys/` | Create new API key | Returns `raw_api_key` in response (only time visible). Enforces one active key per domain. |
| PATCH | `/admin/api-keys/{id}/revoke` | Revoke API key | Sets `is_active=False`. Rejects already-revoked keys. |
| POST | `/admin/api-keys/{id}/rotate` | Rotate API key | Revokes old key, creates new credential for same domain. Returns new `raw_api_key`. |

All mutation endpoints log via `logger.info` with user_id, email, action, IP, and path for audit purposes.

---

## 13. Frontend — Library Layer

### API Client (`src/lib/api.ts`)

Centralized fetch wrapper that handles authentication, error handling, and token refresh.

**Key features:**
- Auto-attaches `Authorization: Bearer` header from localStorage
- Auto-refreshes expired access tokens (transparent 401 handling)
- Standardized error format with field-level error extraction
- Configurable base URL via `VITE_API_BASE_URL` env variable
- FormData upload support via `upload()` and `uploadPut()` methods
- `getMediaUrl()` helper to resolve relative media paths against the backend origin

**Exported API:**

```typescript
apiClient.get<T>(path, options?)
apiClient.post<T>(path, body?, options?)
apiClient.put<T>(path, body?, options?)
apiClient.patch<T>(path, body?, options?)
apiClient.delete<T>(path, options?)
apiClient.upload<T>(path, formData)       // POST with multipart/form-data
apiClient.uploadPut<T>(path, formData)    // PUT with multipart/form-data

authHelpers.setTokens(access, refresh)
authHelpers.clearTokens()
authHelpers.isAuthenticated()

getMediaUrl(path)  // "/media/avatars/..." → full backend URL
```

### Auth Library (`src/lib/auth.ts`)

Authentication functions and shared types.

**Exported types:**

```typescript
interface LoginPayload { email: string; password: string; }
interface RegisterPayload { email, password, first_name, last_name, timezone, currency, language }
interface AuthTokens { access: string; refresh: string; }
interface UserProfile { id, slug, email, first_name, last_name, phone, avatar,
                        timezone, currency, language, is_email_verified, role,
                        created_at, full_name, display_name }
```

**Choice options (served from backend via API):**

Timezone, currency, and language choices are **not hardcoded** in the frontend. They are fetched from the backend `GET /auth/choices` endpoint, which reads directly from Django model enums (`TimezoneChoices`, `CurrencyChoices`, `LanguageChoices`). This ensures the frontend and backend always stay in sync.

```typescript
interface ChoiceOption { value: string; label: string; }
interface Choices {
  timezones: ChoiceOption[];
  currencies: ChoiceOption[];
  languages: ChoiceOption[];
}
```

```typescript
fetchChoices(): Promise<Choices>        // Fetches from GET /auth/choices, caches in-memory
getCachedChoices(): Choices | null       // Returns cached data without API call
```

**Exported functions:**

| Function | Endpoint | Description |
|---|---|---|
| `login(payload)` | POST /auth/login | Login and store tokens |
| `register(payload)` | POST /auth/register | Register new account |
| `logout()` | POST /users/me/logout | Clear tokens, redirect |
| `requestPasswordReset(email)` | POST /auth/password-reset/request | Request password reset OTP |
| `confirmPasswordReset(...)` | POST /auth/password-reset/confirm | Reset password with OTP |
| `changePassword(...)` | POST /users/me/change-password | Change password (authenticated) |
| `requestEmailChange(...)` | POST /users/me/change-email | Request email change OTP |
| `confirmEmailChangeOTP(otp)` | POST /users/me/change-email/confirm | Confirm email change |
| `requestEmailVerification(email)` | POST /auth/verify-email/request | Request email verify OTP |
| `verifyEmail(email, otp)` | POST /auth/verify-email/confirm | Verify email with OTP |
| `getCurrentUser()` | GET /users/me | Get current user profile |
| `updateProfile(data)` | PUT /users/me | Update profile fields |
| `updateAvatar(file)` | PUT /users/me/avatar | Upload avatar (multipart) |
| `deleteAvatar()` | DELETE /users/me/avatar | Remove avatar |
| `deleteAccount(password)` | POST /users/me/delete-account | Soft-delete account |
| `isAuthenticated()` | — | Check localStorage for token |
| `requireAuth()` | — | Redirect to login if unauthenticated |
| `getErrorMessage(error)` | — | Extract user-friendly error string |
| `fetchChoices()` | GET /auth/choices | Fetch timezone/currency/language choices (cached) |
| `getCachedChoices()` | — | Return cached choices if already fetched |
| `detectUserTimezone(choices?)` | — | Auto-detect browser timezone, validate against choices |
| `detectUserLanguage(choices?)` | — | Auto-detect browser language, validate against choices |

### Toast System (`src/lib/toast.ts`)

Lightweight DOM-based toast notification system with zero external dependencies.

```typescript
showToast(message, type?, options?)
// type: "success" | "error" | "info" | "warning"
// options: { duration?: number, action?: { label, onClick } }
```

---

## 14. Frontend — Components & Pages

### Auth Pages (unauthenticated)

| Page | Path | Component | Description |
|---|---|---|---|
| Login | `/auth/login` | `LoginForm.vue` | Email/password login form |
| Register | `/auth/register` | `RegisterForm.vue` | Registration with timezone/currency/language selection |
| Forgot Password | `/auth/forgot-password` | `ForgotPasswordForm.vue` | Enter email to request reset OTP |
| Reset Password | `/auth/reset-password` | `ResetPasswordForm.vue` | Enter OTP + new password |
| Verify Email | `/auth/verify-email` | `VerifyEmailForm.vue` | Enter OTP to verify email |

All auth pages use `AuthLayout.astro` which provides a centered, minimal layout.

### Dashboard Pages (authenticated)

| Page | Path | Component | Description |
|---|---|---|---|
| Dashboard | `/dashboard/` | `DashboardHome.vue` | Overview / landing after login |
| Profile | `/dashboard/profile` | `ProfileCard.vue` | View/edit profile, avatar upload |
| Settings | `/dashboard/settings` | `SettingsPanel.vue` | Password change, email change, account deletion |

All dashboard pages use `DashboardLayout.astro` which includes `Navbar.astro` and `Sidebar.astro`.

### Reusable Components

| Component | Type | Description |
|---|---|---|
| `SearchableSelect.vue` | Vue island | Dropdown with search, grouped options, keyboard nav |
| `EmptyState.astro` | Astro component | Centered empty state with icon and message |
| `LoadingSpinner.astro` | Astro component | CSS-only loading spinner |

### Avatar Upload Implementation

The avatar system spans multiple layers:

1. **UI** (`ProfileCard.vue`) — Hidden `<input type="file">` triggered by a camera icon button. Supports upload (blue circle, bottom-right) and remove (red X, top-right). Shows spinner during upload. Client-side validation: JPEG/PNG/GIF/WebP, max 2 MB.

2. **Auth library** (`auth.ts`) — `updateAvatar(file)` validates client-side, constructs `FormData`, calls `apiClient.uploadPut()`. `deleteAvatar()` calls `apiClient.delete()`.

3. **API client** (`api.ts`) — `uploadPut()` sends FormData with `Content-Type` omitted (browser auto-sets `multipart/form-data` boundary). `getMediaUrl()` converts relative `/media/...` paths to full backend URLs.

4. **Backend** (`controllers.py`) — `PUT /users/me/avatar` uses `ninja.UploadedFile = File(..., alias="avatar")` to parse multipart uploads. Validates file type and size server-side. Deletes old avatar file before saving new one.

---

## 15. Security

### Middleware Stack

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",                          # Static CORS (django-cors-headers)
    "common.cors_middleware.service_domain_cors_middleware",         # Dynamic CORS (ServiceDomain DB)
    "django.middleware.common.CommonMiddleware",
    "ninja.compatibility.files.fix_request_files_middleware",        # File upload support
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

The `service_domain_cors_middleware` uses `@sync_and_async_middleware` (Django 5.2 pattern) for ASGI/WSGI compatibility with Daphne. It checks request origins against active `ServiceDomain` records in the database, with a 5-minute cache.

### JWT Authentication Flow

1. Client sends `Authorization: Bearer <access_token>` header
2. `JWTAuth.authenticate()` decodes the token, extracts `user_id`
3. User is fetched from DB with `is_active=True, is_deleted=False` filter
4. If valid, `request.user` is set; otherwise returns `None` (401)

### Service-to-Service API Key Auth

1. Service backend sends `X-API-Key: sb_live_...` header
2. `validate_api_key()` hashes the key, looks up `ServiceCredential` by hash
3. Checks `credential.is_active` and `credential.service_domain.is_active`
4. Atomically updates `last_used_at`
5. Sets `request.service_credential` and `request.service_domain_from_key`
6. If `SF_API_KEY_ENFORCED=True` and key is missing/invalid: rejects with 401

### Password Security

- Passwords hashed by Django's PBKDF2 (configurable via `AUTH_PASSWORD_VALIDATORS`)
- Custom validator enforces: min 8 chars, uppercase, lowercase, digit, special character
- `check_password()` used for all password verification (never raw comparison)
- Current password required for all sensitive operations (email change, account deletion)

### OTP Security

- Cryptographically random generation (`secrets` module, not `random`)
- 10-minute expiry in Redis (volatile storage)
- Max 5 attempts per OTP; automatic invalidation after limit
- Separate cache keys for OTP value and attempt counter

### Soft Delete

- Accounts are never hard-deleted from the database
- `soft_delete()` sets `is_deleted=True`, `deleted_at=now()`, and `is_active=False`
- All queries filter out soft-deleted users (`is_deleted=False`)
- `get_by_natural_key()` (used by Django auth backend) excludes deleted users
- JWT auth explicitly checks `is_deleted=False`

### Production Security Headers

In production (`DEBUG=False`):
- `CSRF_COOKIE_SECURE = True`
- `SESSION_COOKIE_SECURE = True`
- `SESSION_COOKIE_SAMESITE = "lax"`
- `SESSION_COOKIE_HTTPONLY = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 year)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
- `JWT_SIGNING_KEY` required (must not fall back to `SECRET_KEY`)

### Custom Permissions (`common/permissions.py`)

| Permission | Description |
|---|---|
| `IsAuthenticated` | User must be logged in (`request.user.is_authenticated`) |
| `IsAdmin` | User must be staff (`is_authenticated and is_staff`) |
| `IsVerified` | User must have verified email (`is_authenticated and is_email_verified`) |
| `IsSelfOrAdmin` | User must be the object owner or staff (object-level check) |
| `IsServiceAuthenticated` | Service credential must be valid (`request.service_credential is not None and .is_active`) |

### Custom Exceptions (`common/exceptions.py`)

| Exception | HTTP Status | Description |
|---|---|---|
| `BadRequestException` | 400 | Invalid request data |
| `UnauthorizedException` | 401 | Authentication required |
| `ForbiddenException` | 403 | Insufficient permissions |
| `NotFoundException` | 404 | Resource not found |
| `ConflictException` | 409 | Duplicate resource |
| `TooManyRequestsException` | 429 | Rate limit exceeded |
| `AccountNotActiveException` | 403 | Account is inactive/deleted |

---

## 16. Infrastructure

### Docker Compose

```yaml
services:
  redis:      # Port 6379 — OTP cache, rate limiting, Celery broker, CORS cache
  db:         # Port 5432 — PostgreSQL database
```

### Redis Usage

| Purpose | DB | TTL |
|---|---|---|
| OTP storage (all flows) | DB 2 (via default cache) | 10 minutes |
| Rate limiting | DB 2 (via default cache) | Variable (5 min to 1 hour) |
| CORS origin cache | DB 2 (via default cache) | 5 minutes |
| Plan change preview tokens | DB 2 (via default cache) | 5 minutes |
| Celery broker | DB 1 | — |
| Django Channels | DB 0 (configured separately) | — |

### Celery Configuration

| Setting | Value |
|---|---|
| Broker | `redis://{host}:{port}/1` |
| Result Backend | `django-db` |
| Beat Scheduler | `DatabaseScheduler` (managed via Django admin) |
| Task Time Limit | 30 minutes |
| Timezone | UTC |

Schedules are managed via `django-celery-beat`'s `DatabaseScheduler`, allowing runtime configuration through the Django admin interface without code changes.

### Email Configuration

| Setting | Development | Production |
|---|---|---|
| Backend | `console.EmailBackend` (prints to terminal) | SMTP (Gmail) |
| Host | — | `smtp.gmail.com` |
| Port | — | 587 |
| TLS/SSL | — | SSL enabled |

### File Storage

| Setting | Value |
|---|---|
| `MEDIA_URL` | `/media/` |
| `MEDIA_ROOT` | `backend/media/` |
| Avatar upload path | `media/avatars/YYYY/MM/` |
| Allowed types | JPEG, PNG, GIF, WebP |
| Max size | 2 MB |
| Storage backend | `FileSystemStorage` (local disk) |
| Production serving | Reverse proxy (nginx) required |

### Stripe Configuration

| Setting | Description |
|---|---|
| `SF_STRIPE_SECRET_KEY` | Stripe secret key for API calls |
| `SF_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (frontend) |
| `SF_STRIPE_WEBHOOK_SECRET` | Webhook signing secret for event verification |
| `SF_STRIPE_APP_DOMAIN` | Sattabase base URL (used in checkout/portal URLs) |
| `SF_STRIPE_PORTAL_RETURN_URL` | Default return URL for Customer Portal |
| `SF_STRIPE_SUCCESS_URL` | Default success URL for checkout |
| `SF_STRIPE_CANCEL_URL` | Default cancel URL for checkout |
| `SF_STRIPE_TAX_ENABLED` | Whether to enable Stripe Tax |

---

## 17. Conventions & Patterns

### Backend Patterns

**Controller → Service → ORM**

Controllers are thin HTTP handlers. All business logic lives in services. Controllers handle:
- Rate limiting checks
- Payload parsing (via Pydantic schemas)
- Calling service methods
- Formatting responses

**Sync + Async Methods**

Every service and manager method has both sync and async variants. Async variants are prefixed with `a` (e.g., `register_user` / `aregister_user`). Async methods use Django 5.2's async ORM (`aget`, `afirst`, `asave`, `aexists`) and `sync_to_async` wrappers for cache operations.

**Stripe-First Mutations**

All billing state changes go through Stripe first, then the local database is synced via webhooks. This ensures Stripe is always the single source of truth. Direct DB writes for billing are avoided except for non-payment operations (e.g., admin notes, audit fields).

**Safe Plan Changes (Two-Step)**

Plan changes use a preview/confirm pattern with a time-limited `preview_token` stored in Redis. This prevents stale proration data from being applied. The token has a 5-minute TTL and is invalidated after use.

**API Key Security**

- Raw API keys are never stored — only SHA-256 hashes
- Keys are shown to the admin exactly once at creation time
- `last_used_at` is updated atomically to avoid race conditions
- Enforcement mode is configurable via `SF_API_KEY_ENFORCED` for gradual rollout
- Only the key prefix (first 12 chars) is logged for identification

**Whitelisted Field Updates**

The `update_profile()` service only updates fields in an explicit `allowed_fields` list. This prevents mass-assignment vulnerabilities. To add a new updatable field, add it to the whitelist in both `update_profile()` and `aupdate_profile()`.

**Email Normalization**

All email fields are normalized to lowercase and stripped of whitespace before database operations. This prevents duplicate accounts due to case differences.

**Dynamic CORS via Database**

Rather than maintaining a hardcoded list of allowed origins, the system checks origins against active `ServiceDomain` records in the database. This means adding a new service domain to the system automatically enables CORS for that domain without any code or configuration changes.

**ASGI-Compatible Middleware**

All custom middleware uses Django 5.2's `@sync_and_async_middleware` decorator pattern for compatibility with both Daphne (ASGI) and traditional WSGI servers. The middleware checks `iscoroutinefunction(get_response)` to determine the correct execution path.

### Frontend Patterns

**Centralized API Client**

All HTTP requests go through `apiClient` in `api.ts`. This ensures consistent headers, error handling, and token management across the entire frontend. Vue components never call `fetch()` directly.

**Backend-Driven Choices**

Timezone, currency, and language options are fetched from the backend API (`GET /auth/choices`) rather than hardcoded. This keeps frontend and backend in sync and allows adding new options without a frontend deploy.

**Toast Notifications**

All user feedback uses the `showToast()` function from `toast.ts`. No `alert()` or `confirm()` calls in the codebase. Toasts auto-dismiss after a configurable duration and support action buttons.

### Database Patterns

**Denormalized Product on Subscription**

The `Subscription` model has a `product` FK that duplicates the product from `plan.product`. This denormalization avoids expensive joins when listing subscriptions and makes the data resilient to plan changes.

**Protected Foreign Keys**

The `Subscription.plan` FK uses `on_delete=models.PROTECT`. This prevents accidental deletion of plans that have active subscribers. An admin must cancel/move subscriptions before deleting a plan.

**JSONField for Flexible Data**

`Plan.features` (list of strings for display), `ServiceCredential.permissions` (dict of permission flags), and `WebhookEventLog.payload` (raw Stripe event) use JSONField for schema flexibility without requiring migrations for structural changes.
