# Satta Ledger — Development Documentation

> Personal Accounting & Billing SaaS
> Version: 1.0.0 | Last Updated: May 2026 (docs refreshed 2026-05-07)

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
11. [Service-to-Service API Key Authentication](#11-service-to-service-api-key-authentication)
12. [Frontend — Library Layer](#12-frontend--library-layer)
13. [Frontend — Components & Pages](#13-frontend--components--pages)
14. [Security](#14-security)
15. [Infrastructure](#15-infrastructure)
16. [Conventions & Patterns](#16-conventions--patterns)

---

## 1. Project Overview

Satta Ledger is a full-stack multi-tenant SaaS application for personal accounting, financial notifications, and subscription billing. The system is built with a decoupled architecture: a Django Ninja backend serves a RESTful JSON API, while an Astro.js frontend consumes it via a centralized API client. Authentication is JWT-based with OTP-verified flows for email verification, password reset, and email changes. The billing module integrates Stripe for subscription lifecycle management (checkout, portal, webhooks, invoices, refunds, proration). The project is designed for multi-tenant SaaS use with role-based access, soft-delete patterns, and comprehensive rate limiting.

### Key Design Decisions

- **Email as primary identifier** — the `username` field exists only for Django compatibility; all authentication uses `email` as `USERNAME_FIELD`.
- **OTP-based verification** — no token-bearing URLs; all verification flows use 6-digit OTPs sent via email and validated against Redis cache.
- **Soft delete pattern** — user accounts are never hard-deleted; `is_deleted` and `deleted_at` fields enable data retention and potential account recovery.
- **Async-first services** — every service method has both sync and async variants (`register_user` / `aregister_user`) for compatibility with Django 5.2's async ORM under Daphne/uvicorn.
- **Separate upload endpoint for avatars** — avatar uploads use `PUT /users/me/avatar` with `multipart/form-data` (via `ninja.UploadedFile`), separate from the JSON-based profile update endpoint.
- **Stripe as billing engine** — all subscription lifecycle operations (checkout, renewal, cancellation, refund) go through Stripe APIs. The local database mirrors Stripe state via webhooks for fast reads and audit trails.
- **Modular Stripe integration** — Stripe API calls are encapsulated in `billing/stripe/` sub-package (client, checkout, customer, portal, prices, gdpr, webhooks) rather than scattered across the codebase.
- **Idempotent plan changes** — plan changes use a two-step preview-then-confirm flow with server-side tokens to prevent double-charges.
- **Service-to-service API key authentication** — sister domain backends authenticate via `X-API-Key` header validated by `service_credential_middleware` (global Django middleware using ``@sync_and_async_middleware`` pattern for full ASGI compatibility). Keys are stored as SHA-256 hashes with `sb_live_` prefix, one active key per `ServiceDomain`. Enforcement mode (`API_KEY_ENFORCED`) allows gradual rollout.

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
│                      (Port 8000)                                │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐            │
│  │Controller │→ │   Service    │→ │  ORM / Cache   │            │
│  │  (HTTP)   │  │  (Business)  │  │  (PostgreSQL)  │            │
│  └──────────┘  └──────┬───────┘  └───────┬───────┘            │
│                        │                   │                    │
│               ┌────────▼────────┐  ┌──────▼──────┐            │
│               │ billing/stripe/ │  │   Redis     │            │
│               │ (Stripe API)    │  │ OTP / Rate   │            │
│               └────────┬────────┘  │ Limit / Celery│           │
│                        │           └─────────────┘            │
│               ┌────────▼────────┐                                │
│               │ Stripe Webhooks │                                │
│               │ (async inbound) │                                │
│               └─────────────────┘                                │
│                                                                 │
│  Apps: users | api | common | billing                           │
│  Auth: ninja_jwt (access + refresh + blacklist)                  │
│  Payments: Stripe (checkout, portal, webhooks, invoices)        │
└─────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

1. **Frontend** — Vue component calls a function from `src/lib/auth.ts` or `src/lib/billing.ts`
2. **API Client** — `src/lib/api.ts` wraps the call with JWT headers and error handling
3. **Django Middleware** — `service_credential_middleware` validates `X-API-Key` if present (sets `request.service_credential`); CORS middleware handles domain origins; regular user auth untouched
4. **Backend Router** — Ninja Extra auto-discovers controllers, routes to handler
5. **Controller** — validates rate limit (per-IP for browser traffic, per-API-key for SDK traffic), parses payload via Pydantic schema
6. **Service** — executes business logic (OTP generation, cache checks, DB writes, Stripe API calls)
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

### Service-to-Service (SDK) Authentication Flow

```
Sister Domain Backend (SDK)
    │
    │  X-API-Key: sb_live_...        ← service_credential_middleware validates
    │  X-Service-Domain: docs.example.com  ← Cross-checked against credential
    │  Authorization: Bearer <jwt>   (optional, for user-scoped endpoints)
    │
    ▼
Django Middleware Layer
    │  1. service_credential_middleware:
    │     ├─ No X-API-Key → pass through (regular user auth)
    │     ├─ Invalid prefix → 403 (or warn if enforcement off)
    │     ├─ Missing X-Service-Domain → 400
    │     ├─ Key not found → 403
    │     ├─ Credential revoked → 403
    │     ├─ Domain inactive → 403
    │     ├─ Domain mismatch → 403
    │     └─ Valid → set request.service_credential + request.service_domain_from_key
    │
    ▼
Controller (e.g., auth/me)
    │  Uses request.service_domain_from_key for domain-scoped access map
    │  Rate limiter uses API key prefix as bucket (1000 req/hr)
    │
    ▼
Response
```

### Subscription Billing Flow

```
User selects plan ──→ POST /billing/subscriptions/{slug}/checkout
    │
    ▼
Stripe Checkout Session created ──→ Redirect to Stripe hosted page
    │
    ▼
Payment success ──→ Stripe webhook: checkout.session.completed
    │
    ▼
Subscription activated ──→ Invoice generated ──→ Access granted
    │
    ├─ Plan change ──→ Preview proration ──→ Confirm with token
    ├─ Cancel ──→ Portal URL or API cancel ──→ Access until period end
    └─ Refund ──→ Admin-only ──→ Stripe refund API ──→ Webhook confirms
```

---

## 3. Tech Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Framework | Django + Django Ninja | 5.2 / 1.6 |
| ASGI Server | Daphne | 4.2 |
| Database | PostgreSQL | latest |
| Cache / Broker | Redis | 7.4 |
| Task Queue | Celery + django-celery-beat | 5.6 / 2.9 |
| JWT | ninja_jwt | 5.4 |
| API Framework | ninja_extra | 0.31 |
| Payments | Stripe SDK | 15.1 |
| Real-time | Django Channels + channels-redis | 4.3 |
| Email | Django SMTP (Gmail) | — |
| File Storage | Django FileSystemStorage (Pillow) | — |
| Schema Validation | Pydantic | 2.13 |

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
sattabase/
├── backend/
│   ├── api/                          # API configuration
│   │   ├── views.py                  # NinjaExtraAPI instance, exception handlers
│   │   └── ...
│   ├── common/                       # Shared utilities
│   │   ├── models.py                 # TimeStampedModel, SoftDeleteModel, ActivatorModel
│   │   ├── middleware.py             # service_credential_middleware (API key validation)
│   │   ├── cors_middleware.py        # service_domain_cors_middleware (dynamic CORS, includes FRONTEND_URL)
│   │   ├── api_key_auth.py           # validate_api_key() utility (middleware-aware)
│   │   ├── controllers.py            # AdminApiKeyController (6 endpoints: CRUD + analytics)
│   │   ├── schemas.py                # API key Pydantic schemas + analytics schemas
│   │   ├── admin_schemas.py          # Admin-specific Pydantic schemas
│   │   ├── admin_utils.py            # Admin utility helpers
│   │   ├── permissions.py            # IsAuthenticated, IsAdmin, IsVerified, IsSelfOrAdmin, IsServiceAuthenticated, IsAuthenticatedOrService
│   │   ├── rate_limit.py             # check_rate_limit(), get_client_ip() (per-API-key buckets)
│   │   ├── exceptions.py             # Custom APIException classes
│   │   ├── analytics.py              # Redis-based API key usage analytics
│   │   ├── audit.py                  # Audit logging helpers
│   │   ├── webhooks.py               # Webhook dispatch utilities
│   │   ├── signals.py                # ServiceCredential lifecycle signals (CORS cache invalidation)
│   │   ├── tasks.py                  # Common Celery tasks
│   │   ├── utils.py                  # generate_api_key(), pagination helpers
│   │   ├── apps.py                   # App configuration
│   │   ├── admin.py                  # Django admin registration
│   │   ├── views.py                  # Common views
│   │   └── management/
│   │       └── commands/
│   │           ├── billing_seed_data.py    # Seed billing plans/products
│   │           └── seed_exchange_rates.py # Fetch daily exchange rates
│   ├── users/                        # User authentication & profile app
│   │   ├── models.py                 # User, UserLoginHistory, Choice constants
│   │   ├── managers.py               # CustomUserManager (sync + async)
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── services.py               # AuthService, UserService (business logic)
│   │   ├── controllers.py            # AuthController, UserController (HTTP routing)
│   │   ├── admin.py                  # Django admin registration
│   │   ├── signals.py                # Model signals
│   │   └── migrations/               # Database migrations
│   ├── billing/                      # Stripe billing & subscription app
│   │   ├── models.py                 # Product, Plan, Subscription, Invoice, Refund, etc.
│   │   ├── schemas.py                # Billing Pydantic schemas
│   │   ├── services.py               # BillingService (business logic)
│   │   ├── controllers.py            # BillingProtectedController, BillingPublicController, BillingAdminController
│   │   ├── views.py                  # Legacy router (backward compat)
│   │   ├── tasks.py                  # Celery tasks (revenue recognition, dunning, FX)
│   │   ├── currency_service.py       # Multi-currency price conversion
│   │   ├── stripe_errors.py          # Custom Stripe exception classes
│   │   ├── admin.py                  # Django admin registration
│   │   ├── admin_controller.py       # BillingAdminController (refund, sync, metrics)
│   │   ├── admin_schemas.py          # Admin Pydantic schemas
│   │   ├── admin_utils.py            # Admin utility helpers
│   │   ├── admin_subscription_controller.py  # Admin subscription endpoints
│   │   ├── admin_user_controller.py  # Admin user management endpoints
│   │   ├── admin_metrics_controller.py  # Admin analytics/metrics endpoints
│   │   ├── stripe/                   # Stripe API integration package
│   │   │   ├── client.py             # Low-level Stripe API client wrapper
│   │   │   ├── checkout.py           # Checkout Session creation
│   │   │   ├── customer.py           # Stripe Customer CRUD
│   │   │   ├── portal.py             # Customer Portal session creation
│   │   │   ├── prices.py             # Stripe Price/Plan sync
│   │   │   ├── gdpr.py               # GDPR customer data deletion
│   │   │   └── webhooks/             # Webhook processing pipeline
│   │   │       ├── router.py         # Event type routing
│   │   │       ├── sync.py           # Synchronous processing orchestration
│   │   │       └── handlers/         # Individual event handlers
│   │   │           ├── checkout.py   # checkout.session.completed
│   │   │           ├── subscription.py # customer.subscription.*
│   │   │           ├── invoice.py    # invoice.* events
│   │   │           └── charge.py     # charge.* events (refunds, disputes)
│   │   └── migrations/               # 18 billing migrations (0001–0018)
│   ├── base/                  # Django project settings
│   │   ├── settings.py               # All configuration (includes FRONTEND_URL)
│   │   ├── urls.py                   # Root URL configuration
│   │   ├── asgi.py                   # ASGI entry (Daphne)
│   │   ├── wsgi.py                   # WSGI entry (gunicorn fallback)
│   │   ├── celery.py                 # Celery app configuration
│   │   └── __init__.py
│   ├── manage.py
│   ├── Dockerfile                     # Backend Docker image
│   ├── requirements.txt              # Python dependencies
│   └── media/                        # Uploaded files (avatars, product icons)
│       └── avatars/YYYY/MM/
│
├── frontend/
│   ├── src/
│   │   ├── lib/                      # Shared utilities
│   │   │   ├── api.ts                # Centralized API client (fetch wrapper + token storage)
│   │   │   ├── auth.ts               # Auth functions + types + choice options
│   │   │   ├── billing.ts            # Billing API client + types + formatting helpers
│   │   │   ├── admin.ts              # Admin API client (API key management)
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
│   │   │       ├── EmailChangeConfirm.vue
│   │   │       ├── ProfileCard.vue   # Profile view/edit + avatar upload
│   │   │       ├── SettingsPanel.vue # Account settings (password, email, delete)
│   │   │       ├── DashboardHome.vue
│   │   │       ├── BillingOverview.vue   # Subscription management + transactions
│   │   │       ├── PlansLanding.vue      # Product catalog landing page
│   │   │       ├── PlanComparison.vue    # Plan selection, upgrade/downgrade, proration
│   │   │       ├── TransactionHistory.vue # Paginated transaction/invoice list
│   │   │       ├── ApiKeysAdmin.vue      # Admin API key management (CRUD + modals)
│   │   │       └── SearchableSelect.vue  # Reusable dropdown with search
│   │   ├── layouts/
│   │   │   ├── BaseLayout.astro      # Root layout
│   │   │   ├── DashboardLayout.astro # Authenticated layout (navbar + sidebar)
│   │   │   └── AuthLayout.astro      # Auth pages layout (centered card)
│   │   ├── composables/               # Vue composables (11 files)
│   │   ├── pages/
│   │   │   ├── index.astro           # Landing / redirect
│   │   │   ├── auth/
│   │   │   │   ├── login.astro
│   │   │   │   ├── register.astro
│   │   │   │   ├── forgot-password.astro
│   │   │   │   ├── reset-password.astro
│   │   │   │   ├── verify-email.astro
│   │   │   │   └── email-change/
│   │   │   │       └── confirm.astro # Email change OTP confirmation
│   │   │   └── dashboard/
│   │   │       ├── index.astro
│   │   │       ├── profile.astro     # Profile management
│   │   │       ├── settings.astro    # Account settings
│   │   │       └── billing/
│   │   │           ├── index.astro   # Billing overview page
│   │   │           ├── plans/
│   │   │           │   ├── index.astro    # Plans landing page
│   │   │           │   └── [slug].astro  # Plan comparison page
│   │   │           └── transactions.astro # Transaction history page
│   │   │       └── admin/
│   │   │           └── api-keys/
│   │   │               └── index.astro  # Admin API key management (owner/admin only)
│   │   └── env.d.ts
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml                # PostgreSQL + Redis
├── .env                              # Environment variables (not in repo)
└── dev_docs.md                       # This file
```

---

## 5. Environment Setup

### Prerequisites

- Python 3.10+
- Node.js 22.12+
- Docker & Docker Compose
- Git
- Stripe account (test mode for development)

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

# Install dependencies (or use requirements.txt)
pip install django daphne ninja-extra ninja_jwt django-ninja-jwt-token-blacklist \
    django-cors-headers django-redis channels channels-redis \
    django-celery-results django-celery-beat django-environ \
    Pillow stripe pydantic psycopg2-binary

# Create .env file (see Environment Variables section below)

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server (Daphne ASGI)
daphne -b 0.0.0.0 -p 8000 base.asgi:application

# In a separate terminal, start Celery worker + beat scheduler
celery -A base worker -l info
celery -A base beat -l info
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

#### Core Django Settings

| Variable | Description | Example |
|---|---|---|
| `SB_DEBUG` | Debug mode (`true`/`false`) | `true` |
| `SB_SECRET_KEY` | Django secret key | `django-insecure-...` |
| `SB_SESSION_COOKIE_NAME` | Session cookie name | `sattabase_session_cookie` |

#### Security & Network (Hosts & CORS)

| Variable | Description | Example |
|---|---|---|
| `SB_ALLOWED_HOSTS` | Django ALLOWED_HOSTS | `localhost,127.0.0.1` |
| `SB_CSRF_TRUSTED_ORIGINS` | CSRF-trusted origins | `http://localhost:4321,...` |
| `SB_CORS_ALLOW_ALL_ORIGINS` | Allow all CORS origins (default: `DEBUG`) | `true` |
| `SB_CORS_ALLOWED_ORIGINS` | Explicit CORS allowed origins | `http://localhost:4321,...` |
| `PUBLIC_SITE_URL_SB` | Frontend URL (auto-added to CORS/CSRF) | `http://localhost:4321` |

#### Database

| Variable | Description | Example |
|---|---|---|
| `SB_DB_NAME` | PostgreSQL database name | `sattabase_db` |
| `SB_DB_USER` | PostgreSQL username | `sattabase_user` |
| `SB_DB_PASSWORD` | PostgreSQL password | `sattabase_password` |
| `SB_DB_HOST` | PostgreSQL host | `localhost` |
| `SB_DB_PORT` | PostgreSQL port | `5432` |
| `SB_DATABASE_URL` | Full PostgreSQL connection URL | `postgres://user:pass@host:5432/db` |

#### Redis & Celery

| Variable | Description | Example |
|---|---|---|
| `SB_REDIS_HOST` | Redis host | `localhost` |
| `SB_REDIS_PORT` | Redis port | `6379` |

#### JWT Authentication

| Variable | Description | Default | Example |
|---|---|---|---|
| `SB_JWT_SIGNING_KEY` | JWT signing key (**must set in prod**) | — | `your-random-key` |
| `SB_JWT_ACCESS_TOKEN_MINUTES` | Access token lifetime | `60` | `60` |
| `SB_JWT_REFRESH_TOKEN_DAYS` | Refresh token lifetime | `7` | `7` |
| `SB_JWT_ALGORITHM` | JWT algorithm | `HS256` | `HS256` |
| `SB_JWT_ROTATE_REFRESH_TOKENS` | Rotate refresh tokens on use | `True` | `True` |
| `SB_JWT_BLACKLIST_AFTER_ROTATION` | Blacklist old refresh tokens | `True` | `True` |

#### Rate Limiting & Password Security

| Variable | Description | Default |
|---|---|---|
| `SB_RATE_LIMIT_LOGIN_ATTEMPTS` | Max login attempts per window | `10` |
| `SB_RATE_LIMIT_LOGIN_WINDOW` | Login rate limit window (seconds) | `900` |
| `SB_RATE_LIMIT_REGISTER_ATTEMPTS` | Max register attempts per window | `5` |
| `SB_RATE_LIMIT_REGISTER_WINDOW` | Register rate limit window (seconds) | `3600` |
| `SB_RATE_LIMIT_PASSWORD_RESET_ATTEMPTS` | Max password reset attempts per window | `5` |
| `SB_RATE_LIMIT_PASSWORD_RESET_WINDOW` | Password reset rate limit window (seconds) | `3600` |
| `SB_RATE_LIMIT_SDK_ATTEMPTS` | SDK rate limit (requests per window) | `1000` |
| `SB_RATE_LIMIT_SDK_WINDOW` | SDK rate limit window (seconds) | `3600` |
| `SB_RATE_LIMIT_SENSITIVE_ATTEMPTS` | Sensitive action rate limit | `5` |
| `SB_RATE_LIMIT_SENSITIVE_WINDOW` | Sensitive action rate limit window (seconds) | `3600` |
| `SB_PASSWORD_RESET_TOKEN_EXPIRY` | Password reset token TTL (seconds) | `900` |

#### Email Configuration

| Variable | Description | Example |
|---|---|---|
| `SB_EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `SB_EMAIL_PORT` | SMTP port | `587` |
| `SB_EMAIL_USE_TLS` | Use TLS for SMTP | `true` |
| `SB_EMAIL_HOST_USER` | SMTP username | `base@sattaspace.com` |
| `SB_EMAIL_HOST_PASSWORD` | SMTP password (app password) | `app-specific-pass` |
| `SB_DEFAULT_FROM_EMAIL` | Sender email | `base@sattaspace.com` |

#### Stripe Integration

| Variable | Description | Example |
|---|---|---|
| `SB_STRIPE_SECRET_KEY` | Stripe secret key | `sk_test_...` |
| `SB_STRIPE_PUBLISHABLE_KEY` | Stripe publishable key | `pk_test_...` |
| `SB_STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret | `whsec_...` |
| `SB_STRIPE_APP_DOMAIN` | App domain for portal/checkout URLs (default: `PUBLIC_SITE_URL_SB`) | `http://localhost:4321` |
| `SB_STRIPE_TAX_ENABLED` | Enable Stripe Tax at checkout | `True` |

#### URL & App Settings

| Variable | Description | Example |
|---|---|---|
| `PUBLIC_APP_NAME-SB` | App display name | `SattaBase` |
| `PUBLIC_SITE_URL_SB` | Public site URL | `http://localhost:4321` |

| `PUBLIC_API_BASE_URL_SB` | Frontend API URL (Astro env) | `http://localhost:8000/api/v1` |
| `SB_TOS_VERSION` | Terms of Service version | `1.0` |
| `SB_BASE_CURRENCY` | Base currency for billing | `USD` |
| `SB_EXCHANGE_RATE_API_URL` | Exchange rate API URL | `https://open.er-api.com/v6/latest` |

#### Service-to-Service (API Key)

| Variable | Description | Default |
|---|---|---|
| `SB_API_KEY_ENFORCED` | Reject invalid API keys (False = warn only) | `False` |

> **Note**: In production, `SB_JWT_SIGNING_KEY` must be explicitly set and must differ from `SB_SECRET_KEY`. The server will refuse to start without it.
>
> **Note**: `PUBLIC_SITE_URL_SB` is automatically added to both `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` in settings. Set this once and it covers CORS/CSRF for the frontend domain. In production, `SB_CORS_ALLOW_ALL_ORIGINS` defaults to `False`, so `PUBLIC_SITE_URL_SB` and `SB_CORS_ALLOWED_ORIGINS` must list all allowed domains.
>
> **Note**: `SB_API_KEY_ENFORCED` defaults to `False` for gradual rollout. When `True`, all requests with an invalid or revoked `X-API-Key` receive an immediate 403 response. Set this to `True` before deploying SDK consumers to production. A `RuntimeWarning` is emitted at startup if `DEBUG=False` and enforcement is off.
>
> **Note**: In `DEBUG=True`, PostgreSQL settings are ignored and SQLite is used instead (no Docker required for local development).

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
- `full_name` → `"First Last"` or falls back to email
- `display_name` → first name or email prefix (before `@`)

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

#### TextChoices (Enums)

| Class | Values |
|-------|--------|
| `BillingCycle` | `monthly`, `yearly`, `lifetime` |
| `SubscriptionStatus` | `active`, `past_due`, `canceled`, `trialing`, `paused`, `expired` |
| `AccessValueType` | `string`, `boolean`, `integer` |
| `RefundStatus` | `pending`, `completed`, `failed` |
| `InvoiceStatus` | `draft`, `open`, `paid`, `uncollectible`, `void` |

#### Product

Represents a billable product (e.g. "Satta Ledger Finance", "Satta Ledger Pro"). Each product contains one or more plans.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `name` | CharField(100) | unique | Product display name |
| `slug` | SlugField(50) | unique | URL-safe identifier |
| `description` | TextField | blank | Product description |
| `icon` | ImageField | blank, upload `products/%Y/%m/` | Product icon |
| `home_url` | URLField | blank | Product homepage URL |
| `is_active` | BooleanField | default `True` | Whether product is available |
| `stripe_product_id` | CharField(100) | blank, nullable | Stripe Product ID |

**Database table:** `billing_product`

#### Plan

A pricing tier within a product (e.g. "Free", "Starter", "Professional").

| Field | Type | Constraints | Description |
|---|---|---|---|
| `product` | ForeignKey(Product) | CASCADE, related `plans` | Parent product |
| `name` | CharField(50) | — | Plan display name |
| `slug` | CharField(50) | — | URL-safe identifier |
| `description` | TextField | blank | Plan description |
| `price_cents` | PositiveIntegerField | default `0` | Price in smallest currency unit |
| `currency` | CharField(3) | default `USD` | ISO 4217 currency code |
| `billing_cycle` | CharField | `BillingCycle` choices | Billing period |
| `trial_days` | PositiveIntegerField | default `0` | Free trial length |
| `features` | JSONField | default `dict` | Feature list for display |
| `stripe_price_id` | CharField(100) | blank, nullable | Stripe Price ID |
| `sort_order` | PositiveIntegerField | default `0` | Display ordering |
| `is_active` | BooleanField | default `True` | Whether plan is available |
| `is_featured` | BooleanField | default `False` | Highlight in UI |
| `tax_inclusive` | BooleanField | default `False` | Whether price includes tax |

**Unique constraint:** `(product, slug)`
**Database table:** `billing_plan`

#### ServiceDomain

Maps custom domains to products. Used for multi-product routing via `X-Service-Domain` header.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `domain` | CharField | unique | Domain name |
| `product` | ForeignKey(Product) | CASCADE | Associated product |
| `is_primary` | BooleanField | default `False` | Primary domain for product |
| `is_active` | BooleanField | default `True` | Whether domain is active |
| `webhook_url` | URLField | blank | Webhook URL for credential status propagation |
| `webhook_secret` | CharField | blank | HMAC signing secret for webhook payloads |

**Database table:** `billing_service_domain`

#### ServiceCredential

Stores API key credentials for service-to-service authentication. Each `ServiceDomain` can have one active credential at a time. The raw API key is **never stored** — only its SHA-256 hash is persisted. The raw key is returned only once at creation time and during rotation.

Inherits from `TimeStampedModel` (auto `created_at` / `updated_at`).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `name` | CharField(100) | — | Human-readable label (e.g. "Finance App Production") |
| `service_domain` | OneToOneField(ServiceDomain) | CASCADE, related `credential` | Associated domain |
| `api_key_hash` | CharField(255) | unique, db_index | SHA-256 hash of raw API key |
| `api_key_prefix` | CharField(12) | db_index | First 12 chars (e.g. `sb_live_aBcD`) for admin identification |
| `permissions` | JSONField | default `dict` | Scoped permissions: `{'auth': True, 'billing_read': True}` |
| `is_active` | BooleanField | default `True`, db_index | Whether key is valid |
| `last_used_at` | DateTimeField | null | Last successful validation timestamp |
| `created_by` | ForeignKey(User) | SET_NULL | Admin who created this credential |

**Key format:** `sb_live_` + `secrets.token_urlsafe(32)` = 50 characters total.

**Database table:** `billing_service_credential`

**Django admin:** Read-only list view with bulk revoke action. Credentials are created via the API endpoint (`POST /admin/api-keys/`), not through the Django admin. See `billing/admin.py` → `ServiceCredentialAdmin`.

#### AccessEntry

Key-value feature flags tied to a plan. Controls what features a user can access.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `plan` | ForeignKey(Plan) | CASCADE, related `access_entries` | Parent plan |
| `key` | CharField | — | Feature key (e.g. `max_projects`) |
| `value` | CharField | — | Feature value |
| `value_type` | CharField | `AccessValueType` choices | Value type for parsing |
| `description` | TextField | blank | Human-readable description |

**Unique constraint:** `(plan, key)`
**Database table:** `billing_access_entry`

#### Subscription

Links a user to a plan within a product. Represents the active billing relationship.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `user` | ForeignKey(User) | CASCADE | Subscribed user |
| `plan` | ForeignKey(Plan) | PROTECT | Current plan |
| `product` | ForeignKey(Product) | CASCADE | Denormalized product ref |
| `status` | CharField | `SubscriptionStatus` choices | Current status |
| `stripe_subscription_id` | CharField | unique | Stripe Subscription ID |
| `stripe_customer_id` | CharField | blank | Stripe Customer ID |
| `current_period_start` | DateTimeField | — | Current billing period start |
| `current_period_end` | DateTimeField | — | Current billing period end |
| `trial_start` | DateTimeField | null | Trial start |
| `trial_end` | DateTimeField | null | Trial end |
| `canceled_at` | DateTimeField | null | When cancellation was requested |
| `expires_at` | DateTimeField | null | When access actually ends |
| `has_used_trial` | BooleanField | default `False` | Whether free trial was used |
| `tos_accepted_at` | DateTimeField | null | Terms of service acceptance |
| `tos_version` | CharField | blank | TOS version accepted |
| `currency` | CharField(3) | default `""`, blank | Subscription currency |
| `last_dunning_email_at` | DateTimeField | null | Last dunning email sent |
| `dunning_step` | PositiveIntegerField | default `0` | Current dunning attempt |
| `past_due_at` | DateTimeField | null | When subscription became past due |
| `cancel_at_period_end` | BooleanField | default `False` | Scheduled cancel at period end |

**Unique constraint:** `(user, product)`
**Database table:** `billing_subscription`

#### Invoice

Mirrors Stripe invoices for fast local reads and audit trails.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `stripe_invoice_id` | CharField | unique | Stripe Invoice ID |
| `subscription` | ForeignKey(Subscription) | CASCADE | Related subscription |
| `stripe_subscription_id` | CharField | — | Denormalized Stripe sub ID |
| `number` | CharField | — | Invoice number |
| `status` | CharField | `InvoiceStatus` choices | Invoice status |
| `amount_paid_cents` | PositiveIntegerField | default `0` | Amount paid |
| `amount_due_cents` | PositiveIntegerField | default `0` | Amount due |
| `tax_cents` | PositiveIntegerField | default `0` | Tax amount |
| `discount_cents` | PositiveIntegerField | default `0` | Discount amount |
| `currency` | CharField(3) | — | ISO 4217 currency |
| `period_start` | DateTimeField | — | Billing period start |
| `period_end` | DateTimeField | — | Billing period end |
| `description` | CharField(255) | blank | Invoice description |
| `hosted_url` | URLField | blank | Stripe hosted invoice URL |
| `pdf_url` | URLField | blank | Stripe invoice PDF URL |
| `stripe_fee_cents` | PositiveIntegerField | default `0` | Stripe processing fee |
| `stripe_fee_currency` | CharField(3) | blank | Fee currency |
| `attempt_count` | PositiveIntegerField | default `1` | Payment attempt count |
| `next_payment_attempt` | DateTimeField | null | Next retry date |
| `stripe_response` | JSONField | default `dict` | Raw Stripe API response |

**Database table:** `billing_invoice`

#### InvoiceLineItem

Structured line items for each invoice.

| Field | Type | Description |
|---|---|---|
| `invoice` | ForeignKey(Invoice) | Parent invoice (CASCADE) |
| `stripe_line_item_id` | CharField | Stripe Line Item ID |
| `description` | CharField(255) | blank | Line item description |
| `amount_cents` | IntegerField | Line item amount (can be negative) |
| `currency` | CharField(3) | ISO 4217 currency |
| `quantity` | PositiveIntegerField | default `1` | Quantity |
| `period_start` | DateTimeField | Service period start |
| `period_end` | DateTimeField | Service period end |
| `proration` | BooleanField | Whether this is a proration |
| `discount_amount_cents` | IntegerField | Discount on this line |
| `tax_amount_cents` | IntegerField | Tax on this line |
| `type` | CharField | Line item type |

**Database table:** `billing_invoice_line_item`

#### Refund

Tracks refund requests and their Stripe processing status. Admin-initiated only.

| Field | Type | Description |
|---|---|---|
| `subscription` | ForeignKey(Subscription) | Related subscription |
| `stripe_refund_id` | CharField (unique) | Stripe Refund ID |
| `stripe_charge_id` | CharField | Associated Stripe Charge |
| `amount_cents` | PositiveIntegerField | Refund amount |
| `currency` | CharField(3) | ISO 4217 currency |
| `reason` | CharField(255) | blank | Refund reason |
| `status` | CharField | `RefundStatus` choices |
| `initiated_by` | ForeignKey(User) | Admin who initiated |
| `initiated_by_ip` | GenericIPAddressField | Admin IP |
| `approved_by` | ForeignKey(User) | Admin who approved |
| `approved_at` | DateTimeField | Approval timestamp |
| `reason_category` | CharField | Categorization |
| `admin_notes` | TextField | Internal notes |
| `stripe_response` | JSONField | Raw Stripe response |

**Database table:** `billing_refund`

#### ExchangeRate

Cached exchange rates for multi-currency price display.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `base_currency` | CharField(3) | — | Source currency |
| `target_currency` | CharField(3) | — | Target currency |
| `rate` | DecimalField | — | Exchange rate |
| `fetched_at` | DateTimeField | auto | When rate was fetched |

**Unique constraint:** `(base_currency, target_currency)`
**Database table:** `billing_exchange_rate`

#### PlanChangeLog

Audit trail of plan changes with proration details.

| Field | Type | Description |
|---|---|---|
| `subscription` | ForeignKey(Subscription) | Related subscription |
| `from_plan` | ForeignKey(Plan) | Previous plan |
| `to_plan` | ForeignKey(Plan) | New plan |
| `proration_amount_cents` | IntegerField | Proration charge/credit |
| `currency` | CharField(3) | ISO 4217 currency |
| `stripe_proration_id` | CharField | Stripe Proration ID |
| `initiated_by` | ForeignKey(User) | User who changed plan |
| `proration_behavior` | CharField | `create_prorations` or `none` |

**Database table:** `billing_plan_change_log`

#### WebhookEventLog

Deduplication and audit log for all incoming Stripe webhooks.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `event_id` | CharField | unique | Stripe event ID |
| `event_type` | CharField | — | Event type (e.g. `invoice.paid`) |
| `processed` | BooleanField | default `False` | Whether event was processed |
| `error_message` | TextField | blank | Error if processing failed |
| `payload` | JSONField | — | Raw webhook payload |
| `created_at` | DateTimeField | auto | Event received timestamp |

**Database table:** `billing_webhook_event_log`

#### RevenueRecognitionEntry

Daily revenue recognition entries for accounting (generated by Celery tasks).

| Field | Type | Constraints | Description |
|---|---|---|---|
| `subscription` | ForeignKey(Subscription) | CASCADE | Related subscription |
| `plan` | ForeignKey(Plan) | PROTECT | Plan at time of recognition |
| `amount_cents` | PositiveIntegerField | — | Recognized amount |
| `currency` | CharField(3) | — | ISO 4217 currency |
| `period_start` | DateTimeField | — | Service period start |
| `period_end` | DateTimeField | — | Service period end |
| `recognized_date` | DateField | — | Accounting recognition date |
| `stripe_invoice_id` | CharField | blank | Source invoice |
| `source` | CharField | — | Recognition source |

**Unique constraint:** `(subscription, recognized_date)`
**Database table:** `billing_revenue_recognition`

#### AdminAuditLog

Audit trail for admin actions including API key lifecycle events. Uses plain `models.Model` (not `TimeStampedModel`) since `created_at` is auto-set and immutable.

| Field | Type | Description |
|---|---|---|
| `admin_user` | FK(User, SET_NULL) | Admin who performed the action |
| `action` | CharField(100) | Action identifier (e.g. `api_key.created`, `api_key.revoked`, `api_key.rotated`) |
| `method` | CharField(10) | HTTP method (POST, PATCH, etc.) |
| `path` | CharField(255) | API path |
| `ip_address` | GenericIPAddressField | Client IP |
| `status_code` | PositiveIntegerField | HTTP response status |
| `details` | JSONField | Additional context (credential ID, prefix, etc.) |
| `created_at` | DateTimeField(auto_now_add) | Immutable timestamp |

**Database table:** `billing_admin_audit_log`

### Model Relationship Hierarchy

```
ServiceDomain → ServiceCredential (one-to-one)
ServiceDomain → Product → Plan → AccessEntry
                             └── Subscription → Refund
                                          ├── Invoice → InvoiceLineItem
                                          ├── PlanChangeLog
                                          ├── RevenueRecognitionEntry
                                          └── WebhookEventLog (standalone log)
AdminAuditLog (standalone audit trail)
ExchangeRate (standalone)
```

---

## 7. Backend — Pydantic Schemas

### User Schemas (`users/schemas.py`)

All user-related schemas serve as both request validation contracts and automatic OpenAPI documentation.

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

Billing schemas handle product/plan/subscription/invoice/refund request/response DTOs.

#### Key Request Schemas

| Schema | Fields | Used By |
|---|---|---|
| `CheckoutInputSchema` | plan_slug, billing_cycle?, tos_accepted? | `POST /billing/subscriptions/{slug}/checkout` |
| `ChangePlanInputSchema` | plan_slug, proration_behavior? | `POST /billing/subscriptions/{slug}/change-plan` |
| `ConfirmPlanChangeInputSchema` | plan_slug, preview_token | `POST /billing/subscriptions/{slug}/confirm-plan-change` |
| `RefundInputSchema` | amount_cents?, reason | `POST /billing/admin/subscriptions/{slug}/refund` |

#### Key Response Schemas

| Schema | Fields | Used By |
|---|---|---|
| `ProductDetailSchema` | id, name, slug, description, plans[], service_domains[] | `GET /billing/products/{slug}` |
| `SubscriptionDetailSchema` | Full subscription with nested plan + access map | `GET /billing/subscriptions/{slug}` |
| `ProrationPreviewOutputSchema` | subtotal, tax, total, next_billing, change_type, preview_token | Plan change preview |
| `TransactionItemSchema` | id, type, amounts, hosted_url, pdf_url, card_brand | Transaction history |

### Common API Key Schemas (`common/schemas.py`)

Schemas for the admin API key management endpoints. These live in the `common` app because API key authentication is cross-app (used by billing, users, and future apps).

| Schema | Type | Fields | Used By |
|---|---|---|---|
| `ApiKeyCreateInputSchema` | Request | `name` (str, 1-100), `service_domain_id` (int) | `POST /admin/api-keys/` |
| `ApiKeyOutputSchema` | Response | id, name, api_key_prefix, service_domain, permissions, is_active, last_used_at, created_at, created_by | `GET /admin/api-keys/` |
| `ApiKeyCreateOutputSchema` | Response | All OutputSchema fields + `raw_api_key`, `warning` | `POST /admin/api-keys/` (201) |
| `ApiKeyRotateOutputSchema` | Response | id, name, old_prefix, new_api_key, new_prefix, service_domain, is_active, `warning` | `POST /admin/api-keys/{id}/rotate` |
| `ApiKeyUsageDaySchema` | Response | `date`, `requests` | `GET /admin/api-keys/{id}/analytics` |
| `ApiKeyAnalyticsResponse` | Response | id, name, prefix, domain, total_requests, daily_usage[] | `GET /admin/api-keys/{id}/analytics` |
| `ApiKeyAnalyticsOverviewSchema` | Response | total_credentials, total_requests, active_credentials | `GET /admin/api-keys/analytics` |

> **Security note:** The `raw_api_key` field is included only in creation and rotation responses. It is **never** stored in the database and cannot be recovered after the response is sent.

### Password Validation

All password fields are validated by `_validate_password_strength()`:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (`!@#$%^&*(),.?":{}|<>_\-+=[]\/~`;'`)

### OTP Validation

All OTP fields are validated to be exactly 6 digits (numeric string).

---

## 8. Backend — Service Layer

### User Services (`users/services.py`)

#### AuthService

Handles all authentication-related operations.

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

#### UserService

Handles user profile operations.

| Method | Description | Async Variant |
|---|---|---|
| `get_user_by_id()` | Get user by primary key | `aget_user_by_id()` |
| `get_user_by_email()` | Get user by email (returns None if not found) | `aget_user_by_email()` |
| `get_active_user_by_email()` | Get active, non-deleted user by email | `aget_active_user_by_email()` |
| `get_user_by_slug()` | Get user by public UUID slug | `aget_user_by_slug()` |
| `update_profile()` | Update whitelisted profile fields | `aupdate_profile()` |

### Billing Services (`billing/services.py`)

Core billing operations including subscription lifecycle, plan changes, access control, and Stripe orchestration.

| Method | Description |
|---|---|
| `get_auth_me_data()` | Get user + subscription + access map (read-first pattern) |
| `get_or_create_free_subscription()` | Auto-grant free plan (atomic + row-level lock) |
| `create_checkout_session()` | Create Stripe Checkout for new/reactivated subscriptions |
| `confirm_checkout()` | Verify checkout session and activate subscription |
| `cancel_subscription()` | Cancel at period end or immediately |
| `reactivate_subscription()` | Reactivate canceled subscription before period end |
| `change_plan()` | Change subscription plan with proration |
| `preview_plan_change()` | Generate proration preview token |
| `confirm_plan_change()` | Execute plan change using preview token |
| `get_subscription_detail()` | Get full subscription with plan + access |
| `list_subscriptions()` | List user subscriptions (paginated) |
| `get_transaction_history()` | List Stripe transactions (paginated) |
| `create_portal_session()` | Create Stripe Customer Portal session |

### Celery Tasks (`billing/tasks.py`)

Background async jobs for billing operations.

| Task | Description | Schedule |
|---|---|---|
| `recognize_daily_revenue` | Generate daily revenue recognition entries | Daily |
| `process_dunning` | Send payment failure reminder emails | Daily |
| `update_exchange_rates` | Fetch latest FX rates from Stripe | Hourly |
| `cleanup_stale_webhook_logs` | Remove processed webhook logs older than 30 days | Daily |
| `sync_stripe_prices` | Sync Stripe prices to local Plan records | On-demand |

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

### Public Endpoints (no auth required)

#### Authentication (`/api/v1/auth/`)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| GET | `/auth/choices` | Get timezone/currency/language choices | — | 200: `ChoicesSchema` |
| POST | `/auth/register` | Register new account | `RegisterInputSchema` | 201: `MessageSchema` |
| POST | `/auth/login` | Login with credentials | `LoginInputSchema` | 200: `TokenOutputSchema` |
| POST | `/auth/token/refresh` | Refresh access token | `TokenRefreshInputSchema` | 200: `TokenOutputSchema` |
| POST | `/auth/token/verify` | Verify access token validity | `TokenVerifyInputSchema` | 200: `MessageSchema` |
| POST | `/auth/token/blacklist` | Blacklist a refresh token | `TokenBlacklistInputSchema` | 200: `MessageSchema` |

#### Password Reset (OTP-based)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/auth/password-reset/request` | Request password reset OTP | `PasswordResetRequestSchema` | 200: `MessageSchema` |
| POST | `/auth/password-reset/confirm` | Reset password with OTP | `PasswordResetConfirmSchema` | 200: `MessageSchema` |

#### Email Verification (OTP-based)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/auth/verify-email/request` | Request verification OTP | `EmailVerifyRequestSchema` | 200: `MessageSchema` |
| POST | `/auth/verify-email/confirm` | Verify email with OTP | `EmailVerifyConfirmSchema` | 200: `MessageSchema` |

#### Billing — Products & Plans (public read)

| Method | Path | Description | Query Params | Response |
|---|---|---|---|---|
| GET | `/billing/products` | List all public products | — | Product list |
| GET | `/billing/products/{slug}` | Get product detail with plans | `?currency=` | `ProductDetailSchema` |
| GET | `/billing/products/{slug}/plans` | List plans for a product | `?currency=` | Plan list |

### Stripe Webhook Endpoint

| Method | Path | Description | Auth |
|---|---|---|---|
| POST | `/billing/webhook/stripe` | Receive Stripe webhook events | Stripe webhook signature |

### Protected Endpoints (JWT Bearer token required)

#### Profile (`/api/v1/users/`)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| GET | `/users/me` | Get current user profile | — | 200: `UserOutputSchema` |
| GET | `/users/{slug}` | Get user by slug | — | 200: `UserOutputSchema` |
| PUT | `/users/me` | Update profile fields | `UserProfileUpdateInputSchema` | 200: `UserOutputSchema` |
| PUT | `/users/me/avatar` | Upload/update avatar | `multipart/form-data` (file field: `avatar`) | 200: `UserOutputSchema` |
| DELETE | `/users/me/avatar` | Remove avatar | — | 200: `UserOutputSchema` |

#### Account Security

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/users/me/change-password` | Change password | `ChangePasswordInputSchema` | 200: `MessageSchema` |
| POST | `/users/me/confirm-identity` | Verify identity (password gate) | `PasswordConfirmSchema` | 200: `MessageSchema` |
| POST | `/users/me/change-email` | Request email change OTP | `ChangeEmailRequestSchema` | 200: `MessageSchema` |
| POST | `/users/me/change-email/confirm` | Confirm email change with OTP | `ChangeEmailConfirmOTPSchema` | 200: `MessageSchema` |
| POST | `/users/me/delete-account` | Soft-delete account | `DeleteAccountRequestSchema` | 200: `MessageSchema` |
| POST | `/users/me/logout` | Logout notification | — | 200: `MessageSchema` |

#### Billing — Subscriptions

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| GET | `/billing/auth/me` | Get user subscription + access | Header: `X-Service-Domain` | `AuthMeSchema` |
| GET | `/billing/subscriptions` | List user subscriptions | `?limit=&offset=` | Subscription list |
| GET | `/billing/subscriptions/{productSlug}` | Get subscription detail | — | `SubscriptionDetailSchema` |
| POST | `/billing/subscriptions/{productSlug}/checkout` | Create Stripe checkout session | `CheckoutInputSchema` | `{checkout_url, reactivated}` |
| POST | `/billing/checkout/confirm` | Confirm checkout after redirect | `{session_id}` | Subscription info |
| POST | `/billing/subscriptions/{productSlug}/cancel` | Cancel subscription | Query: `?reason=` | `MessageSchema` |
| POST | `/billing/subscriptions/{productSlug}/reactivate` | Reactivate canceled sub | — | Subscription info |
| POST | `/billing/subscriptions/{productSlug}/change-plan` | Change plan directly | `ChangePlanInputSchema` | Subscription info |
| POST | `/billing/subscriptions/{productSlug}/preview-plan-change` | Preview proration costs | `{plan_slug, proration_behavior}` | `ProrationPreviewOutputSchema` |
| POST | `/billing/subscriptions/{productSlug}/confirm-plan-change` | Confirm plan change | `ConfirmPlanChangeInputSchema` | `ConfirmPlanChangeOutputSchema` |
| POST | `/billing/portal` | Create Stripe Portal session | — | `{portal_url}` |
| GET | `/billing/subscriptions/transactions` | Transaction history | `?limit=&starting_after=` | Transaction list |

#### Billing — Admin (IsAdmin required)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/billing/admin/subscriptions/{productSlug}/refund` | Issue refund | `RefundInputSchema` | `RefundOutputSchema` |
| GET | `/billing/admin/refunds/{productSlug}` | List refunds for subscription | `?limit=&offset=` | Refund list |
| POST | `/billing/admin/sync-customer` | Sync customer data with Stripe | — | `MessageSchema` |

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

Tokens are persisted in the browser's Web Storage with two strategies:

| "Remember me" | Storage | Duration | Cross-tab |
|---|---|---|---|
| Unchecked (default) | `sessionStorage` | Survives reloads, cleared on tab close | No |
| Checked | `localStorage` | Persists across tabs and browser restarts | Yes |

Storage keys:
- `auth_access_token` — used in `Authorization: Bearer` header
- `auth_refresh_token` — used for token refresh
- `auth_remember_me` — `"true"` or `"false"` (controls which storage backend is used)

On page load, tokens are recovered from storage into memory before any Vue component mounts. The `initTokens()` function runs immediately when `api.ts` is imported.

### Token Refresh Flow (Automatic)

The `api.ts` client handles 401 responses automatically:

1. Original request fails with 401
2. If a refresh token exists, call `POST /auth/token/refresh`
3. On success: store new tokens (both memory and storage), retry original request with new access token
4. On failure: clear all tokens (memory and both storage backends), redirect to `/auth/login`

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
| Checkout confirm | `checkout_confirm:{user_id}:{client_ip}` | 10 | 1 hour |
| Cancel subscription | `cancel_sub:{user_id}:{client_ip}` | 5 | 1 hour |
| Reactivate subscription | `reactivate_sub:{user_id}:{client_ip}` | 5 | 1 hour |
| Change plan | `change_plan:{user_id}:{client_ip}` | 5 | 1 hour |
| Sync subscriptions | `sync_subs:{user_id}` | 5 | 1 hour |

Client IP is extracted from `X-Forwarded-For` header with `TRUSTED_PROXIES` CIDR support.

---

## 11. Service-to-Service API Key Authentication

Sister domain backends (e.g., `docs.sattaspace.com`, `finance.sattaspace.com`) authenticate against Sattabase using API keys rather than user JWT tokens. This enables server-to-server communication where the sister domain acts on behalf of its users.

### Architecture Overview

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│  Sister Domain Backend    │         │     Sattabase Backend        │
│  (uses API key auth)    │         │     (Django Ninja + Daphne)   │
│                           │         │                              │
│  Config:                  │         │  Middleware Layer:           │
│  - baseUrl                │ ──────> │  ┌─ service_credential_middleware │
│  - apiKey (sb_live_...)  │  HTTP   │  │  Validates X-API-Key       │
│  - serviceDomain          │         │  │  Cross-checks X-Service-    │
│                           │  JSON   │  │    Domain against credential  │
│  Every request includes:  │         │  └────────────────────────── │
│  - X-API-Key header       │         │  Controller Layer:           │
│  - X-Service-Domain header│         │  Uses request.service_       │
│  - Authorization: Bearer  │         │    domain_from_key for       │
│    (user JWT, optional)   │         │    domain-scoped data        │
└─────────────────────────┘         └──────────────────────────────┘
```

### Key Files

| File | Purpose |
|---|---|
| `common/middleware.py` | `service_credential_middleware` — global Django middleware (``@sync_and_async_middleware`` pattern), validates `X-API-Key` on every request |
| `common/cors_middleware.py` | `service_domain_cors_middleware` — dynamic CORS for registered service domains (5-min cache) |
| `common/api_key_auth.py` | `validate_api_key()` — standalone utility function (middleware-aware, skips if already validated) |
| `common/controllers.py` | `AdminApiKeyController` — CRUD endpoints for API key management |
| `common/schemas.py` | `ApiKeyCreateInputSchema`, `ApiKeyOutputSchema`, `ApiKeyCreateOutputSchema`, `ApiKeyRotateOutputSchema` |
| `common/permissions.py` | `IsServiceAuthenticated` — permission class for endpoints requiring service identity |
| `common/utils.py` | `generate_api_key()` — generates `sb_live_` + `token_urlsafe(32)` key |
| `common/rate_limit.py` | `_get_sdk_rate_limit_params()` — switches rate limit bucket from per-IP to per-API-key for SDK traffic |
| `billing/models.py` | `ServiceCredential` model — stores hashed keys with domain association |
| `billing/admin.py` | `ServiceCredentialAdmin` — read-only Django admin with bulk revoke action |

### service_credential_middleware (`common/middleware.py`)

A Django middleware registered in ``MIDDLEWARE`` as ``common.middleware.service_credential_middleware`` (runs after CORS, before CSRF and auth). It uses Django 5.2's ``@sync_and_async_middleware`` decorator for full ASGI compatibility — the async path uses ``aget``/``aupdate`` ORM calls so the event loop is never blocked, while the sync path uses regular ``get``/``update`` calls for WSGI servers.

It activates **only when `X-API-Key` header is present** — requests without the header pass through untouched, preserving regular user JWT authentication.

**Validation flow:**

1. Read `X-API-Key` from request headers. If absent, pass through immediately.
2. Validate `sb_live_` prefix (fast reject without DB lookup).
3. Verify `X-Service-Domain` header is also present (returns 400 if missing).
4. SHA-256 hash the raw key, look up `ServiceCredential` by hash.
5. Check `is_active` on both credential and service domain.
6. **Cross-check**: verify the `X-Service-Domain` header value matches the domain bound to this credential (prevents domain spoofing).
7. On success: attach `request.service_credential` and `request.service_domain_from_key`, update `last_used_at`.
8. On failure: log warning. If `API_KEY_ENFORCED=True`, return JSON 403/400 response. If `False`, log and allow the request to continue.

**Error response format:**

```json
{"detail": "Invalid API key. No credential found for the provided key.", "code": "api_key_forbidden"}
```

| Error Code | HTTP Status | Condition |
|---|---|---|
| `invalid_api_key_format` | 403 | Key doesn't start with `sb_live_` |
| `missing_service_domain` | 400 | `X-API-Key` present but `X-Service-Domain` missing |
| `api_key_forbidden` | 403 | No credential found for the provided key hash |
| `api_key_revoked` | 403 | Credential exists but `is_active=False` |
| `service_domain_inactive` | 403 | Associated `ServiceDomain.is_active=False` |
| `domain_mismatch` | 403 | `X-Service-Domain` header doesn't match credential's domain |

### Enforcement Mode (`API_KEY_ENFORCED`)

| Setting | Behavior |
|---|---|
| `False` (default) | Invalid keys log a warning but the request continues. Used for gradual rollout — monitor logs for failed validations before enabling strict mode. |
| `True` | Invalid/missing/revoked keys return an immediate 403 JSON response. **Must be set before deploying SDK consumers to production.** |

### Admin API Key Endpoints (`common/controllers.py`)

All endpoints require staff JWT authentication (`IsAuthenticated` + `IsAdmin` permissions).

| Method | Route | Description | Rate Limit |
|---|---|---|---|
| `GET` | `/api/v1/admin/api-keys/` | List all API keys (paginated, filterable by `service_domain_id` and `is_active`) | 120/min |
| `POST` | `/api/v1/admin/api-keys/` | Create new API key. Raw key returned **only once** in the response. | 30/min |
| `PATCH` | `/api/v1/admin/api-keys/{id}/revoke` | Revoke an API key (sets `is_active=False`). Immediately invalid. | 30/min |
| `POST` | `/api/v1/admin/api-keys/{id}/rotate` | Rotate: revoke old key, create new one. New raw key returned **only once**. | 30/min |
| `GET` | `/api/v1/admin/api-keys/analytics` | Aggregated usage statistics across all credentials (Redis-backed) | 120/min |
| `GET` | `/api/v1/admin/api-keys/{id}/analytics` | Daily usage for a single credential (Redis-backed) | 120/min |

**Key creation example:**

```bash
curl -X POST /api/v1/admin/api-keys/ \
  -H "Authorization: Bearer <staff_jwt>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Finance App Production", "service_domain_id": 1}'

# Response (201):
# {
#   "id": 1,
#   "name": "Finance App Production",
#   "api_key_prefix": "sb_live_aBcD",
#   "raw_api_key": "sb_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ01234",  ← SAVE THIS NOW
#   "service_domain": "finance.sattaspace.com",
#   "is_active": true,
#   "created_at": "2026-05-06T10:00:00Z",
#   "warning": "Save this API key now. It cannot be recovered after this response."
# }
```

### Per-API-Key Rate Limiting

When a valid `X-API-Key` is present, the rate limiter (`common/rate_limit.py`) switches from per-IP buckets to per-API-key-prefix buckets with higher limits. This prevents a sister domain backend that proxies many users through a single IP from exhausting the shared bucket.

| Traffic Type | Bucket | Max Attempts | Window |
|---|---|---|---|
| Browser/direct | `action:{user_id}:{client_ip}` | 5 (sensitive) | 3600s |
| SDK/server-to-server | `action:{user_id}:sdk:{api_key_prefix}` | 1000 | 3600s |

### `IsServiceAuthenticated` Permission (`common/permissions.py`)

Two service-aware permission classes are available:

**`IsServiceAuthenticated`** — strict: requires a valid `X-API-Key` header. Returns `True` only if `request.service_credential` is set and active. Use on endpoints that must only be accessed by SDK consumers.

**`IsAuthenticatedOrService`** — flexible (OR combinator): allows access if the request has **either** a valid JWT Bearer token **or** a valid service API key. This is used on `GET /billing/auth/me` since that endpoint serves both the SattaBase frontend (JWT) and sister-domain SDKs (`X-API-Key`).

```python
from common.permissions import IsAuthenticatedOrService

@http_get("/billing/auth/me")
@permissions([IsAuthenticatedOrService])
async def auth_me(self, request):
    # request.service_credential is available if SDK call
    # request.user is available if frontend call
    domain = request.service_domain_from_key.domain if hasattr(request, "service_domain_from_key") else None
    return await BillingService.aget_auth_me_data(request.user, domain)
```

> **Note:** When `API_KEY_ENFORCED=True`, invalid API keys are rejected with 403 by the middleware *before* any permission is evaluated. The permission layer is an additional guard for the case where `API_KEY_ENFORCED=False` (development mode).

### Django Admin (`billing/admin.py`)

The `ServiceCredentialAdmin` provides a read-only audit view:

- **List display:** name, domain, api_key_prefix, is_active, last_used_at, created_by, created_at
- **No add/change forms:** creation is API-only (prevents accidental admin creation without secure key storage)
- **Actions:** "Revoke selected" (bulk `is_active=False`)
- **Filters:** is_active, service_domain, created_at
- **Search:** name, api_key_prefix, service_domain__domain

**Creating API keys from Django admin:** The `ServiceDomainAdmin` has a **"Create API key credential for selected domain(s)"** action. Select one or more service domains in the ServiceDomain list view, click the action, and the raw API key is displayed once in the admin success message. This uses the same `generate_api_key()` logic as `POST /admin/api-keys/`. The list view also shows an "API Key" column linking to the active credential (or "No active key" if none).

### Key Generation Utility (`common/utils.py`)

```python
from common.utils import generate_api_key

raw_key, prefix, key_hash = generate_api_key()
# raw_key = "sb_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ01234"  (50 chars)
# prefix   = "sb_live_aBcD"                            (12 chars)
# key_hash = "5f4dcc3b5aa765d..."                       (64 hex chars)
```

---

## 12. Frontend — Library Layer

### API Client (`src/lib/api.ts`)

Centralized fetch wrapper that handles authentication, error handling, and token refresh.

**Key features:**
- Auto-attaches `Authorization: Bearer` header from in-memory token (recovered from storage on init)
- Auto-refreshes expired access tokens (transparent 401 handling)
- Persists refreshed tokens to storage so they survive page reloads
- Standardized error format with field-level error extraction
- Configurable base URL via `PUBLIC_API_BASE_URL_SB` env variable
- FormData upload support via `upload()` and `uploadPut()` methods
- `getMediaUrl()` helper to resolve relative media paths against the backend origin
- `cache: "no-store"` on every request to prevent stale data

**Exported API:**

```typescript
apiClient.get<T>(path, options?)
apiClient.post<T>(path, body?, options?)
apiClient.put<T>(path, body?, options?)
apiClient.patch<T>(path, body?, options?)
apiClient.delete<T>(path, options?)
apiClient.upload<T>(path, formData)       // POST with multipart/form-data
apiClient.uploadPut<T>(path, formData)    // PUT with multipart/form-data

authHelpers.setTokens(access, refresh, remember?)
authHelpers.clearTokens()
authHelpers.isAuthenticated()

getMediaUrl(path)  // "/media/avatars/..." → full backend URL
```

### Auth Library (`src/lib/auth.ts`)

Authentication functions and shared types.

**Exported types:**

```typescript
interface LoginPayload { email: string; password: string; remember?: boolean; }
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
| `login(payload)` | POST /auth/login | Login, store tokens (respects `remember` flag) |
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
| `isAuthenticated()` | — | Check in-memory token (recovered from storage on init) |
| `requireAuth()` | — | Redirect to login if unauthenticated |
| `getErrorMessage(error)` | — | Extract user-friendly error string |
| `fetchChoices()` | GET /auth/choices | Fetch timezone/currency/language choices (cached) |
| `getCachedChoices()` | — | Return cached choices if already fetched |
| `detectUserTimezone(choices?)` | — | Auto-detect browser timezone, validate against choices |
| `detectUserLanguage(choices?)` | — | Auto-detect browser language, validate against choices |

### Billing Library (`src/lib/billing.ts`)

Billing API client, types, and formatting helpers. Uses the same `apiClient` from `api.ts` for all requests.

**Exported types (17 interfaces):**

`AccessEntrySchema`, `PlanSchema`, `PlanDetailSchema`, `ServiceDomainSchema`, `ProductSchema`, `ProductDetailSchema`, `SubscriptionInfoSchema`, `SubscriptionOutputSchema`, `SubscriptionDetailSchema`, `AuthMeSchema`, `CheckoutInputSchema`, `RefundInputSchema`, `RefundOutputSchema`, `ProrationPreviewOutputSchema`, `ConfirmPlanChangeOutputSchema`, `TransactionItemSchema`, `ChangePlanInputSchema`

**Exported API (`billingApi` object):**

| Method | Endpoint | Description |
|---|---|---|
| `getProducts()` | GET /billing/products | List all public products |
| `getProductBySlug(slug, currency?)` | GET /billing/products/{slug} | Get product with plans + currency conversion |
| `getPlansForProduct(slug, currency?)` | GET /billing/products/{slug}/plans | List plans with optional FX conversion |
| `getAuthMe(domain?)` | GET /billing/auth/me | Get subscription + access (supports `X-Service-Domain` header) |
| `getSubscriptions()` | GET /billing/subscriptions | List user subscriptions |
| `getSubscriptionDetail(slug)` | GET /billing/subscriptions/{slug} | Get subscription with plan + access map |
| `cancelSubscription(slug, reason?)` | POST /billing/subscriptions/{slug}/cancel | Cancel subscription |
| `reactivateSubscription(slug)` | POST /billing/subscriptions/{slug}/reactivate | Reactivate canceled subscription |
| `changePlan(slug, planSlug, behavior?)` | POST /billing/subscriptions/{slug}/change-plan | Change plan directly |
| `createCheckout(slug, planSlug, cycle?, tos?)` | POST /billing/subscriptions/{slug}/checkout | Create Stripe checkout session |
| `confirmCheckout(sessionId)` | POST /billing/checkout/confirm | Confirm checkout after redirect |
| `createPortalSession()` | POST /billing/portal | Create Stripe Customer Portal session |
| `refundSubscription(slug, payload)` | POST /billing/admin/subscriptions/{slug}/refund | **Admin-only** refund |
| `previewPlanChange(slug, planSlug, behavior?)` | POST /billing/subscriptions/{slug}/preview-plan-change | Preview proration costs |
| `confirmPlanChange(slug, planSlug, token)` | POST /billing/subscriptions/{slug}/confirm-plan-change | Confirm plan change |
| `getTransactionHistory(limit?, after?)` | GET /billing/subscriptions/transactions | Paginated transaction history |
| `syncCustomerData()` | POST /billing/admin/sync-customer | **Admin-only** sync with Stripe |

**Exported helper functions:**

| Function | Description |
|---|---|
| `setUserCurrency(currency)` | Set user's preferred display currency (default: `"USD"`) |
| `getUserCurrency()` | Get current display currency |
| `formatPrice(cents, currency?)` | Format cents to `"$9.00"` (returns `"Free"` for 0) |
| `formatCycle(cycle)` | Map billing cycle to `"/mo"`, `"/yr"`, or `"one-time"` |
| `getStatusStyle(status)` | Return Tailwind CSS badge classes for subscription status |
| `formatDate(dateStr)` | Format ISO date to `"Mon DD, YYYY"` |

### Toast System (`src/lib/toast.ts`)

Lightweight DOM-based toast notification system with zero external dependencies.

```typescript
showToast(message, type?, options?)
// type: "success" | "error" | "info" | "warning"
// options: { duration?: number, action?: { label, onClick } }
```

---

## 13. Frontend — Components & Pages

### Auth Pages (unauthenticated)

| Page | Path | Component | Description |
|---|---|---|---|
| Login | `/auth/login` | `LoginForm.vue` | Email/password login with "Remember me" |
| Register | `/auth/register` | `RegisterForm.vue` | Registration with timezone/currency/language selection |
| Forgot Password | `/auth/forgot-password` | `ForgotPasswordForm.vue` | Enter email to request reset OTP |
| Reset Password | `/auth/reset-password` | `ResetPasswordForm.vue` | Enter OTP + new password |
| Verify Email | `/auth/verify-email` | `VerifyEmailForm.vue` | Enter OTP to verify email |
| Email Change Confirm | `/auth/email-change/confirm` | `EmailChangeConfirm.vue` | Confirm email change with OTP |

All auth pages use `AuthLayout.astro` which provides a centered, minimal layout.

### Dashboard Pages (authenticated)

| Page | Path | Component | Description |
|---|---|---|---|
| Dashboard | `/dashboard/` | `DashboardHome.vue` | Overview / landing after login |
| Profile | `/dashboard/profile` | `ProfileCard.vue` | View/edit profile, avatar upload |
| Settings | `/dashboard/settings` | `SettingsPanel.vue` | Password change, email change, account deletion |
| Billing Overview | `/dashboard/billing` | `BillingOverview.vue` | Subscriptions, transactions, invoices, cancel/reactivate |
| Plans Landing | `/dashboard/billing/plans` | `PlansLanding.vue` | Product catalog with plan cards |
| Plan Comparison | `/dashboard/billing/plans/{slug}` | `PlanComparison.vue` | Plan selection, upgrade/downgrade with proration preview |
| Transactions | `/dashboard/billing/transactions` | `TransactionHistory.vue` | Paginated invoice/transaction list |
| Admin API Keys | `/dashboard/admin/api-keys` | `ApiKeysAdmin.vue` | API key management (owner/admin only) |

All dashboard pages use `DashboardLayout.astro` which includes `Navbar.astro` and `Sidebar.astro`.

### Reusable Components

| Component | Type | Description |
|---|---|---|
| `SearchableSelect.vue` | Vue island | Dropdown with search, grouped options, keyboard nav |
| `BillingOverview.vue` | Vue island | Subscription management, transaction history, cancel/reactivate, portal link |
| `PlansLanding.vue` | Vue island | Product catalog with plan cards |
| `TransactionHistory.vue` | Vue island | Paginated transaction/invoice list |
| `PlanComparison.vue` | Vue island | Plan cards, feature comparison, upgrade/downgrade flows, proration modal |
| `ApiKeysAdmin.vue` | Vue island | Admin API key management (create, list, revoke, rotate with modals) |
| `EmptyState.astro` | Astro component | Centered empty state with icon and message |
| `LoadingSpinner.astro` | Astro component | CSS-only loading spinner |

### Avatar Upload Implementation

The avatar system spans multiple layers:

1. **UI** (`ProfileCard.vue`) — Hidden `<input type="file">` triggered by a camera icon button. Supports upload (blue circle, bottom-right) and remove (red X, top-right). Shows spinner during upload. Client-side validation: JPEG/PNG/GIF/WebP, max 2 MB.

2. **Auth library** (`auth.ts`) — `updateAvatar(file)` validates client-side, constructs `FormData`, calls `apiClient.uploadPut()`. `deleteAvatar()` calls `apiClient.delete()`.

3. **API client** (`api.ts`) — `uploadPut()` sends FormData with `Content-Type` omitted (browser auto-sets `multipart/form-data` boundary). `getMediaUrl()` converts relative `/media/...` paths to full backend URLs.

4. **Backend** (`controllers.py`) — `PUT /users/me/avatar` uses `ninja.UploadedFile = File(..., alias="avatar")` to parse multipart uploads. Validates file type and size server-side. Deletes old avatar file before saving new one.

---

## 14. Security

### Middleware Stack

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",           # Static CORS handling
    "common.cors_middleware.service_domain_cors_middleware",  # Dynamic CORS for ServiceDomain
    "django.middleware.common.CommonMiddleware",
    "ninja.compatibility.files.fix_request_files_middleware",  # File upload support
    "common.middleware.service_credential_middleware",  # API key validation (opt-in)
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

### JWT Authentication Flow

1. Client sends `Authorization: Bearer <access_token>` header
2. `JWTAuth.authenticate()` decodes the token, extracts `user_id`
3. User is fetched from DB with `is_active=True, is_deleted=False` filter
4. If valid, `request.user` is set; otherwise returns `None` (401)

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

### Stripe Security

- Webhook events verified with Stripe signature (`stripe.webhooks.construct_event`)
- Webhook deduplication via `WebhookEventLog` (unique `event_id`)
- Idempotent plan changes using server-side preview tokens with expiry
- Row-level DB locking (`select_for_update()`) in webhook handlers to prevent race conditions
- Stripe API errors caught specifically (no bare `except Exception`)
- `rel="noopener noreferrer"` on all external links (Stripe portal, hosted invoices)
- Admin-only access for refund and sync endpoints (rate-limited, logged)

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
| `IsAuthenticated` | User must be logged in |
| `IsAdmin` | User must be staff |
| `IsVerified` | User must have verified email |
| `IsSelfOrAdmin` | User must be the object owner or staff |
| `IsServiceAuthenticated` | Request must carry a valid `X-API-Key` (service-to-service) |
| `IsAuthenticatedOrService` | Request must have valid JWT **or** valid `X-API-Key` (used on `auth/me`) |

---

## 15. Infrastructure

### Docker Compose

```yaml
services:
  redis:      # Port 6379 — OTP cache, rate limiting, Celery broker, Channels
  db:         # Port 5432 — PostgreSQL database
```

### Redis Usage

| Purpose | DB | TTL |
|---|---|---|
| OTP storage (all flows) | DB 0 (via default cache) | 10 minutes |
| Rate limiting | DB 0 (via default cache) | Variable (5 min to 1 hour) |
| Celery broker | DB 1 | — |
| Django Channels | DB 0 (configured separately) | — |

### Celery Tasks

| Task | Schedule | Description |
|---|---|---|
| `recognize_daily_revenue` | Daily | Generate revenue recognition entries |
| `process_dunning` | Daily | Send payment failure reminders |
| `update_exchange_rates` | Hourly | Fetch FX rates from Stripe |
| `cleanup_stale_webhook_logs` | Daily | Remove old webhook logs |
| `sync_stripe_prices` | On-demand | Sync Stripe prices to local DB |

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
| Product icon path | `products/%Y/%m/` |
| Allowed types | JPEG, PNG, GIF, WebP |
| Max size | 2 MB |
| Storage backend | `FileSystemStorage` (local disk) |
| Production serving | Reverse proxy (nginx) required |

---

## 16. Conventions & Patterns

### Backend Patterns

**Controller → Service → ORM**

Controllers are thin HTTP handlers. All business logic lives in services. Controllers handle:
- Rate limiting checks
- Payload parsing (via Pydantic schemas)
- Calling service methods
- Formatting responses

**Sync + Async Methods**

Every service and manager method has both sync and async variants. Async variants are prefixed with `a` (e.g., `register_user` / `aregister_user`). Async methods use Django 5.2's async ORM (`aget`, `afirst`, `asave`, `aexists`) and `sync_to_async` wrappers for cache operations.

**Whitelisted Field Updates**

The `update_profile()` service only updates fields in an explicit `allowed_fields` list. This prevents mass-assignment vulnerabilities. To add a new updatable field, add it to the whitelist in both `update_profile()` and `aupdate_profile()`.

**Email Normalization**

All email fields are normalized to lowercase and stripped of whitespace before database operations. This prevents duplicate accounts due to case differences.

**Stripe Integration Pattern**

All Stripe API calls go through `billing/stripe/client.py` which configures the `stripe` library with `STRIPE_SECRET_KEY` and provides typed wrapper methods. Controllers and services never import `stripe` directly (except webhook handlers which use inline imports for specific Stripe object types).

**Webhook Processing Pipeline**

```
Stripe → POST /billing/webhook/stripe
  → Verify signature (stripe.webhooks.construct_event)
  → Deduplicate (WebhookEventLog, unique event_id)
  → Route by event_type (billing/stripe/webhooks/router.py)
  → Handler processes event (handlers/checkout.py, subscription.py, invoice.py, charge.py)
  → Handler updates DB (with select_for_update where needed)
  → Mark event as processed
```

**Idempotent Plan Changes**

Plan changes use a two-step flow to prevent double-charges:
1. `POST /preview-plan-change` → server generates HMAC token with proration details, stores in cache
2. `POST /confirm-plan-change` → server validates token (exact amount match with ±1 cent tolerance), executes change

**Row-Level Locking**

Webhook handlers that modify subscription state use `select_for_update()` inside `transaction.atomic()` to prevent race conditions when multiple webhook events arrive simultaneously.

### Frontend Patterns

**Centralized API Client**

All API calls go through `src/lib/api.ts`. Vue components never use `fetch()` directly. This ensures consistent auth headers, error handling, and token refresh across the entire application.

**Storage-Based Token Persistence**

JWT tokens are persisted in `sessionStorage` (default) or `localStorage` ("Remember me"). On page load, `initTokens()` recovers them into memory before any component mounts. This balances security (tokens cleared on tab close) with convenience (survives full page reloads).

**Billing Currency Display**

The `billingApi` supports optional `?currency=` query parameter on product/plan endpoints. When provided, the backend converts prices using cached exchange rates. The frontend provides `formatPrice()` and `getUserCurrency()` helpers for consistent display.

**Toast-First Feedback**

User-facing actions (login, plan changes, cancellations) provide immediate feedback via the toast system (`showToast()`). Errors from API calls are displayed both as inline form errors (when applicable) and as toast notifications.

**Confirmation Patterns for Destructive Actions**

- Plan downgrade (paid → free): `window.confirm()` dialog (not toast)
- Subscription cancel: Confirmation dialog in BillingOverview with reason input
- Account deletion: Requires current password + explicit confirmation in SettingsPanel
