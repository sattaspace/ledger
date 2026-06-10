# SattaBase — Developer Documentation

> **Version**: 0.0.1 | **Last Updated**: 2026-06-05 | **Status**: Complete (Sections 1-23 + Appendices A-E)

---

## Table of Contents

- [1. Project Overview & Architecture](#1-project-overview--architecture)
  - [1.1 Purpose & Scope](#11-purpose--scope)
  - [1.2 Technology Stack](#12-technology-stack)
  - [1.3 Architecture Patterns](#13-architecture-patterns)
  - [1.4 Directory Structure](#14-directory-structure)
  - [1.5 System Architecture Diagram Description](#15-system-architecture-diagram-description)
- [2. Backend Architecture Deep Dive](#2-backend-architecture-deep-dive)
  - [2.1 Django Project Structure](#21-django-project-structure)
  - [2.2 All Models with Fields & Relationships](#22-all-models-with-fields--relationships)
  - [2.3 Controllers (Views) Catalog](#23-controllers-views-catalog)
  - [2.4 Services Layer](#24-services-layer)
  - [2.5 Schemas (Pydantic)](#25-schemas-pydantic)
  - [2.6 URLs & Routing](#26-urls--routing)
  - [2.7 Middleware Stack](#27-middleware-stack)
  - [2.8 Signals](#28-signals)
  - [2.9 Celery Tasks](#29-celery-tasks)
- [3. Frontend Architecture Deep Dive](#3-frontend-architecture-deep-dive)
  - [3.1 Astro + Vue Project Structure](#31-astro--vue-project-structure)
  - [3.2 Page Routes & Routing](#32-page-routes--routing)
  - [3.3 Layouts System](#33-layouts-system)
  - [3.4 Vue Components Catalog](#34-vue-components-catalog)
  - [3.5 Composables (State Management)](#35-composables-state-management)
  - [3.6 API Client Layer (lib/)](#36-api-client-layer-lib)
  - [3.7 Authentication & Session Management (Frontend)](#37-authentication--session-management-frontend)
  - [3.8 Styling System](#38-styling-system)
  - [3.9 Astro Server Middleware](#39-astro-server-middleware)
- [4. Authentication & Authorization](#4-authentication--authorization)
  - [4.1 JWT Authentication Flow](#41-jwt-authentication-flow)
  - [4.2 Cookie-Based Token Refresh](#42-cookie-based-token-refresh)
  - [4.3 API Key Authentication (SDK)](#43-api-key-authentication-sdk)
  - [4.4 Permission Classes](#44-permission-classes)
  - [4.5 Rate Limiting](#45-rate-limiting)
  - [4.6 Account Security (Lockout, Deletion)](#46-account-security-lockout-deletion)
  - [4.7 Frontend Auth Flow (End-to-End)](#47-frontend-auth-flow-end-to-end)
- [5. Subscription & Billing System](#5-subscription--billing-system)
  - [5.1 Product, Plan, and Subscription Hierarchy](#51-product-plan-and-subscription-hierarchy)
  - [5.2 Stripe Integration (Checkout, Portal, Webhooks)](#52-stripe-integration-checkout-portal-webhooks)
  - [5.3 Webhook Event Processing](#53-webhook-event-processing)
  - [5.4 Safe Plan Change Flow](#54-safe-plan-change-flow)
  - [5.5 Dunning Workflow](#55-dunning-workflow)
  - [5.6 Revenue Recognition (ASC 606)](#56-revenue-recognition-asc-606)
  - [5.7 Refund System (Two-Person Rule)](#57-refund-system-two-person-rule)
  - [5.8 Multi-Currency Support](#58-multi-currency-support)
- [6. Credit System](#6-credit-system)
  - [6.1 Credit Pools & Lifecycle](#61-credit-pools--lifecycle)
  - [6.2 Credit Purchase Requests (Bank Transfer)](#62-credit-purchase-requests-bank-transfer)
  - [6.3 Credit Consumption & Expiry](#63-credit-consumption--expiry)
  - [6.4 Invoice PDF Generation](#64-invoice-pdf-generation)
  - [6.5 Email Notifications (Approval/Rejection)](#65-email-notifications-approvalrejection)
  - [6.6 Admin Credit Operations](#66-admin-credit-operations)
- [7. Admin Panel Architecture](#7-admin-panel-architecture)
  - [7.1 Admin Controllers Overview](#71-admin-controllers-overview)
  - [7.2 Product & Plan Management](#72-product--plan-management)
  - [7.3 Subscription Administration](#73-subscription-administration)
  - [7.4 User Administration](#74-user-administration)
  - [7.5 Metrics & Reporting](#75-metrics--reporting)
  - [7.6 Audit Logging](#76-audit-logging)
  - [7.7 Webhook Monitoring & Retry](#77-webhook-monitoring--retry)
  - [7.8 Bank Settings Management](#78-bank-settings-management)
- [8. SDK & Sister Domain Integration](#8-sdk--sister-domain-integration)
  - [8.1 Service Domain Model](#81-service-domain-model)
  - [8.2 Service Credential (API Key) System](#82-service-credential-api-key-system)
  - [8.3 API Key Middleware & Validation](#83-api-key-middleware--validation)
  - [8.4 Dynamic CORS for Service Domains](#84-dynamic-cors-for-service-domains)
  - [8.5 SSO Authorization Code Flow](#85-sso-authorization-code-flow)
  - [8.6 Webhook Dispatch for Credential Events](#86-webhook-dispatch-for-credential-events)
  - [8.7 SDK Integration Guide (Sister Domain)](#87-sdk-integration-guide-sister-domain)
  - [8.8 Analytics & Usage Tracking](#88-analytics--usage-tracking)
- [9. API Reference](#9-api-reference)
  - [9.1 API Structure & Versioning](#91-api-structure--versioning)
  - [9.2 Public Endpoints](#92-public-endpoints)
  - [9.3 Protected Endpoints (JWT)](#93-protected-endpoints-jwt)
  - [9.4 Admin Endpoints](#94-admin-endpoints)
  - [9.5 SDK Endpoints (API Key)](#95-sdk-endpoints-api-key)
  - [9.6 Webhook Endpoint (Stripe)](#96-webhook-endpoint-stripe)
  - [9.7 Error Response Format](#97-error-response-format)
  - [9.8 Pagination Convention](#98-pagination-convention)
  - [9.9 Rate Limit Headers & Behavior](#99-rate-limit-headers--behavior)
- [10. Celery Tasks & Background Jobs](#10-celery-tasks--background-jobs)
  - [10.1 Celery Configuration](#101-celery-configuration)
  - [10.2 Scheduled Tasks (Beat)](#102-scheduled-tasks-beat)
  - [10.3 On-Demand Tasks](#103-on-demand-tasks)
  - [10.4 Task Monitoring & Error Handling](#104-task-monitoring--error-handling)
  - [10.5 Redis as Broker & Cache](#105-redis-as-broker--cache)
- [11. Database & Data Layer](#11-database--data-layer)
  - [11.1 Database Configuration](#111-database-configuration)
  - [11.2 Abstract Base Models](#112-abstract-base-models)
  - [11.3 Encrypted Fields](#113-encrypted-fields)
  - [11.4 Migrations Strategy](#114-migrations-strategy)
  - [11.5 Seed Data Commands](#115-seed-data-commands)
  - [11.6 Query Optimization Patterns](#116-query-optimization-patterns)
- [12. Security Architecture](#12-security-architecture)
  - [12.1 Authentication Security](#121-authentication-security)
  - [12.2 CSRF Protection](#122-csrf-protection)
  - [12.3 CORS Security](#123-cors-security)
  - [12.4 Rate Limiting & Brute Force Protection](#124-rate-limiting--brute-force-protection)
  - [12.5 Data Encryption](#125-data-encryption)
  - [12.6 Audit Trail](#126-audit-trail)
  - [12.7 Input Validation & Sanitization](#127-input-validation--sanitization)
- [13. Payment & Stripe Integration](#13-payment--stripe-integration)
  - [13.1 Stripe Configuration](#131-stripe-configuration)
  - [13.2 Checkout Session Flow](#132-checkout-session-flow)
  - [13.3 Customer Portal](#133-customer-portal)
  - [13.4 Webhook Processing Pipeline](#134-webhook-processing-pipeline)
  - [13.5 Refund Processing](#135-refund-processing)
  - [13.6 Stripe Error Handling](#136-stripe-error-handling)
- [14. Email System](#14-email-system)
  - [14.1 Email Configuration](#141-email-configuration)
  - [14.2 Email Templates](#142-email-templates)
  - [14.3 Email Triggers](#143-email-triggers)
- [15. Deployment & DevOps](#15-deployment--devops)
  - [15.1 Docker Configuration](#151-docker-configuration)
  - [15.2 Environment Variables](#152-environment-variables)
  - [15.3 ASGI/WSGI Configuration](#153-asgiwsgi-configuration)
  - [15.4 Static & Media Files](#154-static--media-files)
  - [15.5 Production Checklist](#155-production-checklist)
- [16. Testing Strategy](#16-testing-strategy)
  - [16.1 Backend Test Structure](#161-backend-test-structure)
  - [16.2 Key Test Scenarios](#162-key-test-scenarios)
  - [16.3 Frontend Testing](#163-frontend-testing)
- [17. Error Handling Philosophy](#17-error-handling-philosophy)
  - [17.1 Custom Exception Hierarchy](#171-custom-exception-hierarchy)
  - [17.2 API Error Response Format](#172-api-error-response-format)
  - [17.3 Frontend Error Handling](#173-frontend-error-handling)
- [18. Data Flow Diagrams](#18-data-flow-diagrams)
  - [18.1 User Registration & Login Flow](#181-user-registration--login-flow)
  - [18.2 Subscription Purchase Flow](#182-subscription-purchase-flow)
  - [18.3 Credit Purchase (Bank Transfer) Flow](#183-credit-purchase-bank-transfer-flow)
  - [18.4 SDK SSO Authorization Flow](#184-sdk-sso-authorization-flow)
- [19. Known Issues & Technical Debt](#19-known-issues--technical-debt)
  - [19.1 Known Bugs](#191-known-bugs)
  - [19.2 Technical Debt](#192-technical-debt)
- [20. Development Workflow](#20-development-workflow)
  - [20.1 Local Development Setup](#201-local-development-setup)
  - [20.2 Database Migrations](#202-database-migrations)
  - [20.3 Seed Data](#203-seed-data)
- [21. Contributing Guidelines](#21-contributing-guidelines)
  - [21.1 Code Style](#211-code-style)
  - [21.2 Git Workflow](#212-git-workflow)
  - [21.3 PR Review Process](#213-pr-review-process)
- [22. Glossary](#22-glossary)
  - [22.1 Domain Terms](#221-domain-terms)
  - [22.2 Acronyms](#222-acronyms)
- [23. Changelog & Version History](#23-changelog--version-history)
  - [23.1 Version History](#231-version-history)
- [Appendix A: Environment Variables Reference](#appendix-a-environment-variables-reference)
- [Appendix B: API Endpoint Quick Reference Table](#appendix-b-api-endpoint-quick-reference-table)
- [Appendix C: Model Relationship Diagram Description](#appendix-c-model-relationship-diagram-description)
- [Appendix D: Stripe Webhook Events Reference](#appendix-d-stripe-webhook-events-reference)
- [Appendix E: SattaBase SDK Integration Checklist](#appendix-e-sattabase-sdk-integration-checklist)

---

# 1. Project Overview & Architecture

## 1.1 Purpose & Scope

SattaBase is a **central multi-tenant subscription management and billing platform** that serves as the authentication, billing, and account management hub for a family of sister web applications (called "service domains"). It is not a standalone product — rather, it is the backbone infrastructure that powers user identity, subscription lifecycle, payment processing, and access control across multiple externally-hosted web services.

The platform operates under the brand name **SattaBase** (part of the SattaSpace ecosystem) and is accessible at `baseapi.sattaspace.com` for the API and a separate frontend domain for the user dashboard and admin panel. Its core responsibilities include:

- **User Identity Management**: Registration, login, email verification, password management, profile administration, and account lifecycle (activation, deactivation, soft deletion).
- **Subscription Lifecycle**: Full CRUD for products, plans, and subscriptions with Stripe as the payment provider. Supports monthly, yearly, and lifetime billing cycles, free trials, plan upgrades/downgrades with proration, cancellations, and reactivations.
- **Payment Processing**: Stripe Checkout for card-based subscriptions, a credit/bank-transfer system for users who cannot use international cards (particularly relevant in regions like South Asia), and Stripe Customer Portal for self-service billing management.
- **Credit System**: An offline payment pathway where users submit bank transfer requests, admins approve them, and credits are allocated into credit pools with period-based consumption — running parallel to Stripe subscriptions.
- **Sister Domain Integration (SDK)**: API key authentication, dynamic CORS resolution, SSO via authorization code flow, and webhook dispatch for credential events — enabling sister domains to authenticate users and check subscription access without managing their own billing.
- **Admin Panel**: A comprehensive administration interface with product/plan/subscription/user management, metrics dashboards, refund approval with a two-person rule, audit logging, webhook monitoring, bank settings configuration, and API key administration.
- **Revenue Recognition**: ASC 606-compliant daily revenue recognition entries for active subscriptions, with specific exclusion of past-due subscriptions from recognition.
- **Multi-Currency Support**: Real-time exchange rate fetching with fallback providers, currency conversion for plan prices, and support for 35+ currencies including zero-decimal currencies (JPY, KRW, VND).

The scope intentionally excludes domain-specific business logic — sister domains handle their own features. SattaBase is purely the centralized authentication, billing, and access-control layer.

## 1.2 Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Framework** | Django | 5.2.13 | Core web framework, ORM, admin site |
| **API Framework** | django-ninja-extra | 0.31.4 | Async API controllers with Pydantic schemas |
| **API Base** | django-ninja | 1.6.2 | OpenAPI schema generation, routing |
| **JWT Auth** | django-ninja-jwt | 5.4.4 | Access/refresh token pair with rotation and blacklisting |
| **ASGI Server** | Daphne | 4.2.1 | Production async server |
| **WSGI Server** | Gunicorn | 25.3.0 | Sync fallback, also available via Uvicorn 0.46.0 |
| **Database** | PostgreSQL | — | Production database (SQLite in DEBUG mode) |
| **Task Queue** | Celery | 5.6.3 | Background task execution |
| **Task Scheduler** | django-celery-beat | 2.9.0 | Periodic task scheduling |
| **Task Results** | django-celery-results | — | Celery result backend in Django ORM |
| **Broker** | Redis | 7.4.0 | Celery message broker + cache backend |
| **Cache** | django-redis | 6.0.0 | Django cache framework backed by Redis |
| **Channels** | channels + channels_redis | 4.3.2 | WebSocket support (infrastructure ready) |
| **Payments** | Stripe Python SDK | 15.1.0 | Checkout, portal, webhooks, refunds, customer management |
| **CORS** | django-cors-headers | 4.9.0 | Cross-origin request handling |
| **Encryption** | cryptography | 47.0.0 | Encrypted model fields (bank account numbers, etc.) |
| **PDF Generation** | ReportLab | 4.5.1 | Professional credit invoice PDFs |
| **Image Processing** | Pillow | 12.2.0 | Avatar upload and processing |
| **Database Driver** | psycopg2-binary | 2.9.12 | PostgreSQL adapter |

### Frontend

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Framework** | Astro | 6.x | SSR/SSG hybrid framework with View Transitions |
| **UI Framework** | Vue 3 | 3.5.x | Interactive islands (SPA components) |
| **Integration** | @astrojs/vue | 6.x | Astro-Vue adapter |
| **Server Adapter** | @astrojs/node | 10.x | Node.js standalone server adapter (SSR mode) |
| **CSS** | Tailwind CSS | 4.2.4 | Utility-first CSS with `@theme` directive |
| **Language** | TypeScript | 5.9.3 | Type-safe frontend code |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| **Containerization** | Docker | Separate Dockerfiles for backend and frontend |
| **Database** | PostgreSQL (prod) / SQLite (dev) | Primary data store |
| **Cache/Broker** | Redis (port 6379, DB 2 for cache, DB 0 for broker) | Caching + Celery broker |
| **CDN/Static** | Django static files | Admin interface + media uploads |

## 1.3 Architecture Patterns

SattaBase follows several deliberate architectural patterns that are critical to understand before working with the codebase:

### Stripe-First Mutations

All billing mutations follow a strict "Stripe first, DB second" pattern. When a user cancels a subscription, changes a plan, or initiates a refund, the code first calls the Stripe API to perform the mutation. Only after Stripe confirms success does the local database get updated. This prevents state drift between Stripe and the local database — if Stripe fails, no local record is created, and the user receives a clear error message. If the local DB write fails after Stripe succeeds, webhook handlers will eventually reconcile the state. This pattern is consistently applied across all controllers in `billing/controllers.py` and `billing/admin_controller.py`.

### Dual Authentication (JWT + API Key)

The platform supports two parallel authentication mechanisms:

1. **JWT (frontend)**: Users authenticate via email/password, receiving a short-lived access token (in memory) and a long-lived refresh token (in an httpOnly cookie). This flow is used by the Astro + Vue frontend and follows standard OAuth2 patterns with token rotation and blacklisting.

2. **API Key (SDK)**: Sister domains authenticate via an `X-API-Key` header containing a key prefixed with `sb_live_`. The middleware validates the key by computing a SHA-256 hash, looking up the corresponding `ServiceCredential`, and verifying that the associated `ServiceDomain` is active. This mechanism is enforced at the middleware level (`service_credential_middleware`) and also available at the controller level (`validate_api_key` in `api_key_auth.py`).

The `IsAuthenticatedOrService` permission class allows endpoints to accept either authentication method, enabling shared endpoints like product listing and auth/me to work for both frontend users and SDK clients.

### ASGI-First with sync_to_async

All controller methods are declared as `async def` and run on Daphne's ASGI event loop. However, Django's ORM is fundamentally synchronous, and critical operations like `transaction.atomic()` and `select_for_update()` must run in a synchronous context. The project follows a strict pattern: transactional logic is extracted into a synchronous helper function (e.g., `_cancel_subscription_sync()`), which is then wrapped with `@sync_to_async` for calling from async controller methods. This pattern was established after fixing seven critical `AttributeError: __aenter__` bugs caused by incorrectly using `async with transaction.atomic()` (Django's `transaction.atomic()` is a synchronous context manager and cannot be used with `async with`).

### Controller-Service-Model Separation

The backend follows a layered architecture:

- **Controllers** (`*_controller.py`): Handle HTTP request/response, authentication, permission checks, input validation (via Pydantic schemas), and orchestration. They do not contain business logic directly — they delegate to services.
- **Services** (`services.py`, `currency_service.py`): Contain reusable business logic that may be called from multiple controllers or tasks. Services are stateless classes with static methods.
- **Models** (`models.py`): Django ORM models with field definitions, constraints, and minimal model-level methods (computed properties, soft delete, etc.). Business logic is kept out of models.

This separation ensures that controllers remain thin orchestration layers while services provide testable, reusable business logic.

### Window-Level Shared State (Frontend)

Because Astro's View Transitions can cause JavaScript modules to be re-evaluated (losing module-level state), all Vue composables store their reactive state on the `window` object using keys like `__sb_auth_composable`, `__sb_sub_composable`, `__sb_txn_composable`, etc. When a composable initializes, it first checks if shared state already exists on `window`. If it does, it reuses the existing Vue refs; if not, it creates them. This pattern ensures that state survives View Transition module re-evaluations and prevents duplicate API calls from components that remount after a transition.

### Frozen Shell Layout Pattern

The frontend uses a "frozen shell" layout where the sidebar and navbar persist across page navigations using Astro's `transition:persist` directive. Only the main content area (the "island") swaps during View Transitions. This provides a native-app-like experience where navigation chrome stays fixed while content transitions smoothly. The pattern is implemented in both `DashboardLayout.astro` and `AdminLayout.astro`.

## 1.4 Directory Structure

### Backend (`/backend/`)

```
backend/
├── manage.py                    # Django management CLI
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Backend container build
├── .env                         # Environment variables
├── db.sqlite3                   # SQLite database (dev only)
│
├── base/                        # Django project configuration
│   ├── __init__.py              # Loads Celery app
│   ├── settings.py              # Django settings (557 lines)
│   ├── urls.py                  # Root URL configuration
│   ├── wsgi.py                  # WSGI entrypoint
│   ├── asgi.py                  # ASGI entrypoint
│   └── celery.py                # Celery app configuration
│
├── billing/                     # Core billing & Stripe integration
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                # ~1500 lines: 20+ models
│   ├── views.py
│   ├── controllers.py           # ~1000 lines: 4 controller classes
│   ├── schemas.py               # ~686 lines: user-facing schemas
│   ├── services.py              # ~992 lines: BillingService
│   ├── admin.py
│   ├── admin_controller.py      # ~1134 lines: product/plan admin
│   ├── admin_schemas.py         # ~1143 lines: admin schemas
│   ├── admin_subscription_controller.py  # ~879 lines
│   ├── admin_user_controller.py          # ~628 lines
│   ├── admin_metrics_controller.py       # ~964 lines
│   ├── admin_utils.py
│   ├── currency_service.py      # ~552 lines
│   ├── stripe_errors.py         # ~334 lines
│   ├── fields.py                # EncryptedCharField
│   ├── pdf_utils.py             # ~464 lines: professional PDFs
│   ├── tasks.py                 # ~980 lines: 8 Celery tasks
│   │
│   ├── stripe/                  # Stripe SDK integration
│   │   ├── __init__.py          # Core Stripe functions
│   │   ├── client.py            # Stripe API client wrapper
│   │   ├── customer.py          # Customer CRUD
│   │   ├── checkout.py          # Checkout session creation
│   │   ├── portal.py            # Customer portal session
│   │   ├── prices.py            # Price/sync operations
│   │   └── gdpr.py              # GDPR data deletion
│   │
│   └── stripe/webhooks/         # Webhook handling
│       ├── __init__.py
│       ├── router.py            # Event router
│       ├── sync.py              # Sync handlers
│       ├── utils.py             # Webhook utilities
│       └── handlers/            # Event-type handlers
│           ├── charge.py
│           ├── checkout.py
│           ├── invoice.py
│           └── subscription.py
│
├── users/                       # User accounts & authentication
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                # ~400 lines: User, UserLoginHistory
│   ├── managers.py              # ~151 lines: custom UserManager
│   ├── views.py                 # Empty (Django default)
│   ├── controllers.py           # ~940 lines: AuthController
│   ├── schemas.py               # ~479 lines: auth schemas
│   ├── services.py
│   ├── admin.py
│   ├── signals.py               # Post-save signals
│   └── tests.py
│
├── common/                      # Shared utilities & infrastructure
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                # ~77 lines: abstract base models
│   ├── views.py
│   ├── controllers.py           # ~539 lines: API key admin
│   ├── schemas.py
│   ├── permissions.py           # ~92 lines: 6 permission classes
│   ├── middleware.py            # ~420 lines: API key middleware
│   ├── cors_middleware.py       # ~188 lines: dynamic CORS
│   ├── api_key_auth.py          # ~170 lines: controller-level validation
│   ├── rate_limit.py            # ~185 lines: sliding window
│   ├── exceptions.py            # ~104 lines: 9 custom exceptions
│   ├── utils.py                 # ~122 lines: pagination, key generation
│   ├── audit.py                 # ~87 lines: audit logging
│   ├── analytics.py             # ~167 lines: Redis usage tracking
│   ├── webhooks.py              # ~174 lines: HMAC webhook dispatch
│   ├── signals.py               # ~140 lines: CORS cache invalidation
│   ├── tasks.py                 # Shared Celery tasks
│   ├── admin.py
│   ├── tests.py
│   │
│   └── management/commands/
│       ├── billing_seed_data.py # Seed demo billing data
│       └── seed_exchange_rates.py
│
├── api/                         # API gateway / NinjaExtraAPI instance
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py                # Empty (placeholder)
│   ├── views.py                 # ~251 lines: API config + controller registration
│   ├── admin.py
│   └── tests.py
│
└── logs/                        # Application logs
    ├── debug.log
    ├── info.log
    └── error.log
```

### Frontend (`/frontend/`)

```
frontend/
├── astro.config.mjs             # Astro 6 configuration (SSR, Vue, Tailwind)
├── package.json                 # NPM dependencies & scripts
├── tsconfig.json                # TypeScript configuration
├── Dockerfile                   # Frontend container build
│
├── public/
│   ├── favicon.ico
│   └── favicon.svg
│
└── src/
    ├── env.d.ts                 # TypeScript env declarations
    ├── middleware.ts             # Astro server middleware (auth guards)
    │
    ├── styles/
    │   └── global.css           # Tailwind v4 theme + custom CSS
    │
    ├── pages/                   # Astro page routes (25 pages)
    │   ├── index.astro          # Redirects to /dashboard
    │   │
    │   ├── auth/                # Authentication pages
    │   │   ├── login.astro
    │   │   ├── register.astro
    │   │   ├── callback.astro
    │   │   ├── forgot-password.astro
    │   │   ├── reset-password.astro
    │   │   ├── verify-email.astro
    │   │   └── email-change/confirm.astro
    │   │
    │   ├── dashboard/           # User dashboard pages
    │   │   ├── index.astro
    │   │   ├── profile.astro
    │   │   ├── settings.astro
    │   │   └── billing/
    │   │       ├── index.astro
    │   │       ├── transactions.astro
    │   │       ├── plans/
    │   │       │   ├── index.astro
    │   │       │   └── [slug].astro
    │   │       └── credits/
    │   │           ├── index.astro
    │   │           └── request.astro
    │   │
    │   └── admin/               # Admin panel pages
    │       ├── index.astro
    │       ├── users/
    │       │   ├── index.astro
    │       │   └── [id].astro
    │       ├── products/
    │       │   ├── index.astro
    │       │   └── [id].astro
    │       ├── plans/[planId].astro
    │       ├── subscriptions/
    │       │   ├── index.astro
    │       │   └── [id].astro
    │       ├── credits/index.astro
    │       ├── credit-requests/index.astro
    │       ├── refunds/index.astro
    │       ├── audit-log/index.astro
    │       ├── webhooks/index.astro
    │       ├── api-keys/index.astro
    │       └── bank-settings/index.astro
    │
    ├── components/
    │   ├── vue/                 # User-facing Vue islands (22 components)
    │   │   ├── SessionGuard.vue         # Auth session monitor
    │   │   ├── AdminGuard.vue           # Admin role guard
    │   │   ├── AuthCallbackHandler.vue  # OAuth callback
    │   │   ├── LoginForm.vue
    │   │   ├── RegisterForm.vue
    │   │   ├── ForgotPasswordForm.vue
    │   │   ├── ResetPasswordForm.vue
    │   │   ├── VerifyEmailForm.vue
    │   │   ├── EmailChangeConfirm.vue
    │   │   ├── DashboardHome.vue        # ~688 lines
    │   │   ├── ProfileCard.vue
    │   │   ├── SettingsPanel.vue
    │   │   ├── BillingOverview.vue
    │   │   ├── TransactionHistory.vue
    │   │   ├── PlanComparison.vue
    │   │   ├── PlansLanding.vue
    │   │   ├── UserCreditsClient.vue
    │   │   ├── CreditRequestClient.vue
    │   │   ├── CreditRequestsClient.vue
    │   │   ├── ApiKeysAdmin.vue
    │   │   └── SearchableSelect.vue
    │   │
    │   ├── admin/               # Admin panel Vue islands (17 components)
    │   │   ├── AdminDashboard.vue          # ~593 lines
    │   │   ├── AdminPageHeader.vue
    │   │   ├── AdminStatsCard.vue
    │   │   ├── AdminDataTable.vue
    │   │   ├── AdminFilterBar.vue
    │   │   ├── AdminConfirmDialog.vue
    │   │   ├── AdminStatusBadge.vue
    │   │   ├── AdminEmptyState.vue
    │   │   ├── AdminFeatureMatrix.vue
    │   │   ├── AdminAuditTimeline.vue
    │   │   ├── UsersAdmin.vue
    │   │   ├── UserDetailAdmin.vue
    │   │   ├── ProductsAdmin.vue
    │   │   ├── ProductDetailAdmin.vue
    │   │   ├── PlanDetailAdmin.vue
    │   │   ├── SubscriptionsAdmin.vue
    │   │   ├── SubscriptionDetailAdmin.vue  # ~1615 lines
    │   │   ├── CreditRequestsAdmin.vue
    │   │   ├── CreditManagement.vue
    │   │   ├── RefundsAdmin.vue
    │   │   ├── AuditLogAdmin.vue
    │   │   ├── WebhooksAdmin.vue
    │   │   └── BankSettingsAdmin.vue
    │   │
    │   └── astro/               # Astro layout sub-components
    │       ├── Navbar.astro
    │       ├── Sidebar.astro
    │       ├── AdminNavbar.astro
    │       ├── AdminSidebar.astro
    │       ├── LoadingSpinner.astro
    │       └── EmptyState.astro
    │
    ├── composables/             # Vue composables (14 + 1 barrel)
    │   ├── index.ts             # Barrel export
    │   ├── useAuth.ts           # ~530 lines: shared auth + billing state
    │   ├── useAdminGuard.ts     # ~83 lines: admin role guard
    │   ├── useSubscription.ts   # ~155 lines: subscription state
    │   ├── useAccess.ts         # ~85 lines: feature access checking
    │   ├── useAdminData.ts      # ~208 lines: admin product/domain data
    │   ├── useTransactions.ts   # Shared transaction history state
    │   ├── useProducts.ts       # Shared product catalog state
    │   ├── useFormErrors.ts     # Form field error management
    │   ├── useAsyncAction.ts    # ~66 lines: async action wrapper
    │   ├── useBillingRedirect.ts # ~79 lines: billing return detection
    │   ├── usePasswordStrength.ts # Password validation composable
    │   ├── useOtpInput.ts       # OTP digit input handling
    │   ├── useMediaQuery.ts     # Reactive CSS media query
    │   └── useCooldownTimer.ts  # Countdown timer composable
    │
    ├── layouts/                 # Astro layouts (4)
    │   ├── BaseLayout.astro     # ~109 lines: root HTML shell
    │   ├── AuthLayout.astro     # ~136 lines: auth page layout
    │   ├── DashboardLayout.astro # ~308 lines: user dashboard
    │   └── AdminLayout.astro    # ~323 lines: admin panel
    │
    └── lib/                     # API clients & utilities (6)
        ├── api.ts               # ~1369 lines: core HTTP client
        ├── auth.ts              # ~478 lines: auth API calls
        ├── billing.ts           # ~619 lines: billing API calls
        ├── credits.ts           # ~481 lines: credits API calls
        ├── admin.ts             # ~1263 lines: admin API calls
        └── toast.ts             # ~199 lines: toast notifications
```

## 1.5 System Architecture Diagram Description

The SattaBase system follows a three-tier architecture with multiple integration points:

**Tier 1 — Frontend (Astro SSR + Vue Islands)**
The frontend is an Astro 6 application running in SSR mode on a Node.js server (standalone adapter). When a user requests a page, Astro performs server-side rendering, checking authentication via the Astro middleware (`src/middleware.ts`) which validates the `sb_refresh_token` httpOnly cookie against the backend's refresh endpoint. Authenticated pages are pre-rendered with the appropriate layout (Auth, Dashboard, or Admin). Interactive components are mounted as Vue 3 islands with `client:only="vue"` or `client:load` directives, communicating with the backend through the `apiClient` HTTP wrapper in `lib/api.ts`. The frontend maintains JWT access tokens in memory (window-level shared state) and automatically refreshes them 5 minutes before expiry.

**Tier 2 — Backend (Django + Ninja Extra)**
The backend is a Django 5.2 application running on Daphne (ASGI). All API endpoints are served under `/api/v1/` and are defined using `@api_controller` decorators from django-ninja-extra. The `NinjaExtraAPI` instance in `api/views.py` auto-discovers all controllers and generates an OpenAPI schema. The backend handles JWT authentication, API key validation, Stripe webhook processing, Celery task dispatch, and Redis caching. Two custom middleware intercept every request: `service_credential_middleware` validates API keys on requests that include an `X-API-Key` header, and `service_domain_cors_middleware` dynamically resolves CORS headers based on the `ServiceDomain` database table.

**Tier 3 — External Services**
- **PostgreSQL**: Primary database for all application data
- **Redis**: Dual role as Celery message broker and Django cache backend (rate limiting, CORS origin caching, API key usage analytics)
- **Stripe**: Payment processing, subscription management, and webhook notifications
- **Celery Workers**: Background task execution for dunning emails, exchange rate updates, revenue recognition, credit period consumption, and webhook delivery

**Request Flow — Frontend User**:
1. Browser requests page → Astro middleware checks `sb_refresh_token` cookie
2. Middleware calls `POST /api/v1/auth/token/refresh-cookie` to validate session
3. If valid, page renders with appropriate layout and Vue islands
4. Vue component calls `apiClient.get/post()` → JWT access token added to `Authorization` header
5. Django receives request → JWT auth validates token → controller executes → response returned
6. If access token expired (401), apiClient automatically refreshes via `refresh-cookie` and retries once

**Request Flow — SDK (Sister Domain)**:
1. Sister domain backend sends request with `X-API-Key: sb_live_xxx` and `X-Service-Domain: example.com` headers
2. `service_credential_middleware` validates API key (SHA-256 hash lookup) and domain cross-check
3. `service_domain_cors_middleware` injects CORS headers for the requesting domain
4. Controller receives request with `request.service_credential` and `request.service_domain_from_key` attached
5. Endpoints with `IsAuthenticatedOrService` permission allow the request through

**Request Flow — Stripe Webhook**:
1. Stripe sends POST to `/api/v1/billing/webhooks/stripe`
2. Webhook controller verifies signature using `STRIPE_WEBHOOK_SECRET`
3. Event is routed to appropriate handler in `billing/stripe/webhooks/handlers/`
4. Handler updates database models (subscription status, invoice records, etc.)
5. Async webhook processing logs results to `WebhookEventLog`

---

# 2. Backend Architecture Deep Dive

## 2.1 Django Project Structure

The Django project is configured under the `base/` package (not the typical `config/`). This package contains all top-level Django settings:

**`base/settings.py`** (557 lines) — The central configuration file that defines:
- `INSTALLED_APPS`: 13 apps including `daphne`, `admin_interface`, `channels`, `django_celery_results`, `django_celery_beat`, `ninja_extra`, `ninja_jwt`, `corsheaders`, `users`, `api`, `common`, `billing`, `cache_cleaner`
- `AUTH_USER_MODEL = "users.User"` — Custom user model
- `MIDDLEWARE`: 11 middleware in specific order (see Section 2.7)
- Database: PostgreSQL in production, SQLite when `DEBUG=True`
- Redis: Port 6379, DB 2 for cache, DB 0 for Celery broker
- JWT: Configurable access/refresh token lifetimes, rotation enabled, blacklisting enabled
- Stripe: Secret key, publishable key, webhook secret from environment variables
- Email: SMTP with TLS on port 587, console backend in DEBUG mode
- CORS: `CORS_ALLOW_CREDENTIALS = True`, specific allowed origins from environment

**`base/urls.py`** (25 lines) — Minimal root URL configuration:
```python
urlpatterns = [
    path("admin/", admin.site.urls),        # Django admin (Satta Base admin)
    path("api/v1/", api.urls, name="base"), # NinjaExtraAPI instance
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**`base/celery.py`** — Celery app configuration with Redis broker, django-celery-beat scheduler, and autodiscovery of tasks from all installed apps.

**`base/asgi.py`** — ASGI configuration wrapping Django's ASGI handler with Channels routing.

**`base/__init__.py`** — Imports the Celery app so it's always available when Django starts.

The project has **4 Django apps**: `users`, `billing`, `common`, and `api`. There is no `accounts/` or `sdk/` app — user functionality lives in `users/`, and SDK/API key functionality is distributed across `common/` (middleware, auth, analytics) and `billing/` (ServiceCredential model, service domain model).

## 2.2 All Models with Fields & Relationships

### Abstract Base Models (`common/models.py`)

Three abstract models provide common fields for all concrete models:

- **TimeStampedModel**: `created_at` (auto_now_add, db_index), `updated_at` (auto_now)
- **SoftDeleteModel**: Extends TimeStampedModel. Adds `is_deleted` (default=False), `deleted_at` (null). Provides `soft_delete()` which sets `is_deleted=True` and `deleted_at=now()`, and `restore()` which clears both.
- **ActivatorModel**: Adds `is_active` (default=True), `activated_at` (null). Provides `activate()` and `deactivate()` methods.

### User Models (`users/models.py`)

**User** (extends AbstractUser + TimeStampedModel + SoftDeleteModel):
| Field | Type | Notes |
|---|---|---|
| `slug` | UUID4 | Unique, auto-generated, used in URLs |
| `email` | EmailField | Unique, USERNAME_FIELD |
| `first_name` | CharField(150) | Optional |
| `last_name` | CharField(150) | Optional |
| `phone` | CharField(20) | Optional |
| `avatar` | ImageField | Upload to `avatars/`, optional |
| `timezone` | CharField | 35 IANA timezone choices, default "UTC" |
| `currency` | CharField(3) | 30 ISO 4217 codes, default "USD" |
| `language` | CharField(7) | 28 ISO 639-1 codes, default "en" |
| `is_email_verified` | BooleanField | Default False |
| `last_login_ip` | GenericIPAddressField | Null, captured on login |
| `failed_login_attempts` | PositiveIntegerField | Default 0, CRIT-02 for lockout |
| `locked_until` | DateTimeField | Null, CRIT-02 for lockout |
| `role` | CharField | Choices: owner, admin, member |

Methods: `full_name`, `display_name`, `is_account_locked()`, `increment_failed_login()`, `reset_failed_login_attempts()`

**UserLoginHistory**:
| Field | Type | Notes |
|---|---|---|
| `user` | FK(User, CASCADE) | |
| `ip_address` | GenericIPAddressField | |
| `user_agent` | TextField | |
| `created_at` | DateTimeField | auto_now_add |

### Billing Models (`billing/models.py`)

**Product**:
| Field | Type | Notes |
|---|---|---|
| `name` | CharField(200) | |
| `slug` | SlugField(200) | Unique, auto from name |
| `description` | TextField | Blank |
| `icon` | CharField(100) | Blank, emoji/icon name |
| `home_url` | URLField | Blank, product homepage |
| `is_active` | BooleanField | Default True |
| `stripe_product_id` | CharField(200) | Null/blank, unique constraint on non-null |

**ServiceDomain** (links products to sister domains):
| Field | Type | Notes |
|---|---|---|
| `product` | FK(Product, CASCADE) | |
| `domain` | CharField(255) | Unique |
| `is_primary` | BooleanField | Default False, unique constraint: one primary per product |
| `is_active` | BooleanField | Default True |
| `webhook_url` | URLField | Null/blank, for credential event dispatch |
| `webhook_secret` | CharField(100) | Null/blank, HMAC signing key |

**Plan**:
| Field | Type | Notes |
|---|---|---|
| `product` | FK(Product, CASCADE) | |
| `name` | CharField(100) | |
| `slug` | SlugField(100) | Unique with product |
| `price_cents` | PositiveIntegerField | Price in cents |
| `currency` | CharField(3) | Default "USD" |
| `billing_cycle` | CharField | Choices: monthly, yearly, lifetime |
| `trial_days` | PositiveIntegerField | Default 0 |
| `features` | JSONField | Default dict, feature key-value pairs |
| `stripe_price_id` | CharField(200) | Null/blank |
| `sort_order` | IntegerField | Default 0 |
| `is_active` | BooleanField | Default True |
| `is_featured` | BooleanField | Default False |
| `tax_inclusive` | BooleanField | Default False |

**AccessEntry** (plan feature access control):
| Field | Type | Notes |
|---|---|---|
| `plan` | FK(Plan, CASCADE) | |
| `key` | CharField(100) | Feature key |
| `value_type` | CharField | Choices: string, boolean, integer |
| `string_value` | CharField(500) | Null/blank |
| `boolean_value` | BooleanField | Default False |
| `integer_value` | IntegerField | Null/blank |
| Unique constraint: (plan, key) | | |

**Subscription** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `user` | FK(User, CASCADE) | |
| `plan` | FK(Plan, SET_NULL, null) | |
| `product` | FK(Product, SET_NULL, null) | |
| `status` | CharField | active, past_due, canceled, trialing, paused, expired |
| `stripe_subscription_id` | CharField(200) | Unique |
| `stripe_customer_id` | CharField(200) | |
| `current_period_start` | DateTimeField | |
| `current_period_end` | DateTimeField | |
| `trial_start` | DateTimeField | Null |
| `trial_end` | DateTimeField | Null |
| `canceled_at` | DateTimeField | Null |
| `cancel_at_period_end` | BooleanField | Default False |
| `tos_accepted` | BooleanField | Default False |
| `tos_version` | CharField(10) | Null |
| `dunning_step` | IntegerField | Default 0, for staged dunning |
| `past_due_at` | DateTimeField | Null, for dunning day counting |
| `currency` | CharField(3) | Default "USD" |
| Unique constraint: (user, product) | | Only one subscription per product per user |

**Invoice** (synced from Stripe):
| Field | Type | Notes |
|---|---|---|
| `stripe_invoice_id` | CharField(200) | Unique |
| `subscription` | FK(Subscription, SET_NULL, null) | |
| `user` | FK(User, CASCADE) | |
| `amount_due` | PositiveIntegerField | In cents |
| `amount_paid` | PositiveIntegerField | |
| `tax` | PositiveIntegerField | Default 0 |
| `discount` | PositiveIntegerField | Default 0 |
| `currency` | CharField(3) | |
| `status` | CharField | draft, open, paid, void, uncollectible |
| `period_start` | DateTimeField | |
| `period_end` | DateTimeField | |
| `hosted_url` | URLField | Null |
| `pdf_url` | URLField | Null |
| `stripe_fee` | PositiveIntegerField | Null, in cents |

**InvoiceLineItem**:
| Field | Type | Notes |
|---|---|---|
| `invoice` | FK(Invoice, CASCADE, related_name="line_items") | |
| `description` | TextField | |
| `amount` | PositiveIntegerField | In cents |
| `quantity` | IntegerField | Default 1 |
| `period_start` | DateTimeField | Null |
| `period_end` | DateTimeField | Null |

**Refund** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `subscription` | FK(Subscription, SET_NULL, null) | SET_NULL for audit trail after sub deletion |
| `user` | FK(User, CASCADE) | |
| `stripe_refund_id` | CharField(200) | Unique |
| `stripe_charge_id` | CharField(200) | |
| `amount` | PositiveIntegerField | In cents |
| `currency` | CharField(3) | |
| `reason` | CharField | Choices: duplicate, fraudulent, requested_by_customer, other |
| `status` | CharField | pending, succeeded, failed, canceled |
| `initiated_by` | FK(User, SET_NULL, null) | Who started the refund |
| `initiator_ip` | GenericIPAddressField | Null, CMP-02 audit |
| `approved_by` | FK(User, SET_NULL, null) | Two-person rule approver |
| `admin_reason` | TextField | Blank, internal notes |
| `metadata` | JSONField | Default dict |

**ExchangeRate**:
| Field | Type | Notes |
|---|---|---|
| `base_currency` | CharField(3) | Default "USD" |
| `target_currency` | CharField(3) | |
| `rate` | DecimalField(max_digits=18, decimal_places=8) | |
| `fetched_at` | DateTimeField | auto_now_add |
| Unique constraint: (base_currency, target_currency) | | |

**CreditPool** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `user` | FK(User, CASCADE) | |
| `product` | FK(Product, CASCADE) | |
| `subscription` | FK(Subscription, SET_NULL, null) | Optional link to subscription |
| `total_credits` | PositiveIntegerField | |
| `remaining_credits` | PositiveIntegerField | |
| `credits_per_period` | PositiveIntegerField | Credits consumed per billing period |
| `period_type` | CharField | daily, weekly, monthly, yearly |
| `status` | CharField | active, exhausted, expired, canceled |
| `expires_at` | DateTimeField | Null |
| `purchase_reference` | CharField(100) | Blank, bank transfer reference |

**CreditInvoice** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `invoice_number` | CharField(50) | Unique, auto-generated |
| `user` | FK(User, CASCADE) | |
| `credit_pool` | FK(CreditPool, SET_NULL, null) | |
| `amount` | PositiveIntegerField | In cents |
| `currency` | CharField(3) | |
| `periods` | PositiveIntegerField | Number of billing periods purchased |
| `status` | CharField | issued, paid, void, refunded |
| `bank_reference` | CharField(100) | Blank |
| `issued_at` | DateTimeField | auto_now_add |

**CreditTransaction** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `pool` | FK(CreditPool, CASCADE) | |
| `invoice` | FK(CreditInvoice, SET_NULL, null) | |
| `transaction_type` | CharField | purchase, consumption, refund, adjustment, expiry |
| `amount` | IntegerField | Positive for credit, negative for debit |
| `balance_after` | PositiveIntegerField | Pool balance after transaction |
| `description` | TextField | Blank |

**CreditPurchaseRequest** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `user` | FK(User, CASCADE) | |
| `product` | FK(Product, CASCADE) | |
| `plan` | FK(Plan, SET_NULL, null) | |
| `amount` | PositiveIntegerField | In cents |
| `currency` | CharField(3) | |
| `periods` | PositiveIntegerField | Default 1 |
| `status` | CharField | pending, approved, rejected |
| `bank_reference` | CharField(200) | Blank |
| `bank_details` | TextField | Blank, encrypted |
| `reviewed_by` | FK(User, SET_NULL, null) | |
| `reviewed_at` | DateTimeField | Null |
| `admin_notes` | TextField | Blank |

**BankSettings** (extends TimeStampedModel + ActivatorModel):
| Field | Type | Notes |
|---|---|---|
| `bank_name` | CharField(200) | |
| `account_name` | CharField(200) | |
| `account_number` | EncryptedCharField(200) | Encrypted at rest |
| `routing_info` | TextField | Blank, encrypted |
| `instructions` | TextField | Blank, payment instructions |

**ServiceCredential** (extends TimeStampedModel + ActivatorModel):
| Field | Type | Notes |
|---|---|---|
| `name` | CharField(100) | Human-readable name |
| `api_key_hash` | CharField(64) | SHA-256 hash of the raw key |
| `api_key_prefix` | CharField(12) | First 12 chars for identification |
| `service_domain` | FK(ServiceDomain, CASCADE) | Domain this key is bound to |
| `last_used_at` | DateTimeField | Null |
| `expires_at` | DateTimeField | Null |
| Unique constraint: api_key_hash | | |

**WebhookEventLog** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `event_id` | CharField(200) | Unique, Stripe event ID |
| `event_type` | CharField(200) | e.g., "customer.subscription.updated" |
| `processed` | BooleanField | Default False |
| `error_message` | TextField | Blank |
| `raw_data` | JSONField | Null, full Stripe event payload |

**AdminAuditLog** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `admin_user` | FK(User, SET_NULL, null) | |
| `action` | CharField(100) | e.g., "subscription.override" |
| `resource_type` | CharField(50) | e.g., "subscription" |
| `resource_id` | CharField(100) | |
| `details` | JSONField | Default dict, before/after snapshots |
| `ip_address` | GenericIPAddressField | Null |

**RevenueRecognitionEntry** (extends TimeStampedModel):
| Field | Type | Notes |
|---|---|---|
| `subscription` | FK(Subscription, CASCADE) | |
| `date` | DateField | Recognition date |
| `amount_cents` | PositiveIntegerField | Recognized revenue in cents |
| `currency` | CharField(3) | |
| `recognized_at` | DateTimeField | auto_now_add |
| Unique constraint: (subscription, date) | | Prevents double-recognition |

### Model Relationship Chain

```
Product ──→ ServiceDomain (1:N, one product can have many domains)
Product ──→ Plan (1:N, one product has many plans)
Plan ──→ AccessEntry (1:N, one plan has many feature entries)
User + Product ──→ Subscription (1:1 per product, unique constraint)
Subscription ──→ Invoice (1:N)
Invoice ──→ InvoiceLineItem (1:N)
Subscription ──→ Refund (1:N, SET_NULL for audit)
User ──→ CreditPool (1:N per product)
CreditPool ──→ CreditInvoice (1:N)
CreditPool ──→ CreditTransaction (1:N)
User ──→ CreditPurchaseRequest (1:N)
User ──→ UserLoginHistory (1:N)
ServiceDomain ──→ ServiceCredential (1:N, domain-bound API keys)
```

## 2.3 Controllers (Views) Catalog

All controllers use `@api_controller` from django-ninja-extra and are auto-discovered by the API instance. There are no traditional `urls.py` per app — routing is declarative via decorators.

### BillingPublicController (`/billing`, no auth required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/products` | GET | List all active products |
| `/products/{slug}` | GET | Product detail with plans |
| `/products/{slug}/access-matrix` | GET | Feature access matrix for product |
| `/plans` | GET | List all active plans |
| `/exchange-rates` | GET | Current exchange rates |
| `/currencies` | GET | Supported currency metadata |
| `/bank-settings` | GET | Active bank settings for credit purchases |

### BillingProtectedController (`/billing`, JWT auth required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/auth/me` | GET | Domain-aware auth response with subscription, access map, exchange rates |
| `/subscriptions` | GET | List user's subscriptions |
| `/subscriptions/{id}` | GET | Subscription detail |
| `/subscriptions/{id}/cancel` | POST | Cancel subscription |
| `/subscriptions/{id}/reactivate` | POST | Reactivate canceled subscription |
| `/subscriptions/{id}/change-plan` | POST | Change plan (deprecated, use preview+confirm) |
| `/checkout` | POST | Create Stripe checkout session |
| `/checkout/confirm` | POST | Confirm checkout completion |
| `/portal` | POST | Create Stripe customer portal session |
| `/sync` | POST | Force sync subscription data from Stripe |
| `/transactions` | GET | Unified transaction history (Stripe + credit invoices) |
| `/plan-change/preview` | POST | Preview plan change with proration |
| `/plan-change/confirm` | POST | Confirm plan change with preview token |
| `/export` | GET | Export billing data |

### BillingAdminController (`/billing/admin`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/refunds` | POST | Initiate refund with audit logging |

### BillingWebhookController (`/billing/webhooks`, no auth — Stripe signature verification)
| Endpoint | Method | Purpose |
|---|---|---|
| `/stripe` | POST | Stripe webhook endpoint |

### AdminProductController (`/admin`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/products` | GET/POST | List/Create products |
| `/products/{id}` | GET/PATCH/DELETE | Product CRUD |
| `/products/{id}/service-domains` | GET | List service domains for product |
| `/service-domains` | POST | Create service domain |
| `/service-domains/{id}` | PATCH/DELETE | Update/Delete service domain |

### AdminPlanController (`/admin`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/plans` | GET/POST | List/Create plans |
| `/plans/{id}` | GET/PATCH/DELETE | Plan CRUD |
| `/plans/{id}/duplicate` | POST | Duplicate plan with new slug |
| `/plans/{id}/access-entries` | GET/POST | List/Create access entries |
| `/access-entries/bulk` | PUT | Bulk replace access entries |
| `/access-entries/matrix` | GET/PUT | Feature matrix view/save |

### AdminSubscriptionController (`/admin`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/subscriptions` | GET | Paginated subscription list with filters |
| `/subscriptions/{id}` | GET | Subscription detail with access map |
| `/subscriptions/{id}/override` | PATCH | Override plan/status/period (audit logged) |
| `/subscriptions/{id}/cancel` | PATCH | Force cancel |
| `/subscriptions/{id}/expire` | PATCH | Force expire |
| `/subscriptions/{id}/extend` | PATCH | Extend period by N days |
| `/subscriptions/{id}/plan-changes` | GET | Plan change history |
| `/subscriptions/{id}/invoices` | GET | Invoice history |
| `/subscriptions/{id}/refund` | POST | Issue refund (captures admin IP) |
| `/subscriptions/{id}/refunds` | GET | Refund history |

### AdminUserController (`/admin`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/users` | GET | Paginated user list with subscription counts |
| `/users/{id}` | GET | User detail with all subscriptions |
| `/users/{id}/status` | PATCH | Activate/deactivate (prevents self-deactivation) |
| `/users/{id}/role` | PATCH | Change role (prevents self-demotion, syncs is_staff) |
| `/users/{id}/audit` | GET | Compiled audit trail (login, plan changes, subs, refunds) |

### AdminMetricsController (`/admin`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/metrics/overview` | GET | MRR, subscription counts, churn rate, trial conversion |
| `/metrics/revenue` | GET | Revenue by product, plan, month (12 months) |
| `/metrics/subscriptions` | GET | Subscription funnel with per-product breakdown |
| `/metrics/products` | GET | Per-product metrics (subscribers, MRR, plan distribution) |
| `/audit-log` | GET | Paginated admin audit log |
| `/webhooks` | GET | List webhook events with filters |
| `/webhooks/{id}/retry` | POST | Re-process failed webhook |

### AuthController (`/auth`, public + protected mixed)
| Endpoint | Method | Purpose |
|---|---|---|
| `/login` | POST | Email/password login with rate limiting |
| `/register` | POST | User registration (default is_active=False) |
| `/token/refresh` | POST | Body-based token refresh (blacklists old) |
| `/token/refresh-cookie` | POST | Cookie-based refresh (rotation without blacklisting) |
| `/logout` | POST | Logout with cookie validation (AUTH-2 fix) |
| `/password-reset/request` | POST | Request password reset OTP |
| `/password-reset/confirm` | POST | Confirm reset with OTP + new password |
| `/email-verification/request` | POST | Request email verification |
| `/email-verification/confirm` | POST | Confirm with OTP |
| `/authorize` | GET | SSO authorization code generation |
| `/token/exchange` | POST | Exchange auth code for tokens |
| `/me` | GET | Current user profile |
| `/me` | PATCH | Update profile |
| `/me/password` | POST | Change password |
| `/me/avatar` | POST/DELETE | Upload/delete avatar |
| `/me/email-change` | POST | Request email change |
| `/me/email-change/confirm` | POST | Confirm email change with OTP |
| `/me/delete` | POST | Soft-delete account |
| `/choices` | GET | Enum choices for registration forms |

### AdminApiKeyController (`/admin/api-keys`, JWT + staff required)
| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET/POST | List/Create API keys |
| `/service-domains` | GET | Domains for create-key dropdown |
| `/{id}/revoke` | PATCH | Revoke key + dispatch webhook |
| `/{id}/rotate` | POST | Rotate key (revoke old + create new) |
| `/analytics` | GET | Aggregated usage stats |
| `/{id}/analytics` | GET | Single credential daily stats |

## 2.4 Services Layer

### BillingService (`billing/services.py`, ~992 lines)

The `BillingService` class provides static methods organized into functional groups:

**Product & Plan Queries** (sync + async variants):
- `aget_products()`, `aget_product_by_slug()` — Fetch active products with plans
- `aget_plans_for_product()` — Plans for a specific product
- `aget_subscription_for_product()` — User's subscription for a product (with race condition prevention via `select_for_update`)

**Subscription Management**:
- `cancel_subscription()` / `_cancel_subscription_sync()` — Cancel in Stripe then DB. Uses the `@sync_to_async` pattern for `transaction.atomic()` + `select_for_update()`.
- `reactivate_subscription()` / `_reactivate_subscription_sync()` — Reactivate a canceled subscription in Stripe then DB.
- `change_plan()` — Deprecated direct plan change (replaced by preview+confirm flow)
- `sync_subscription_from_stripe()` — Pull current state from Stripe and update DB

**Auth & Access**:
- `get_auth_me_data()` — Build the comprehensive auth/me response: user profile, subscription info, access map, exchange rates, currencies. Domain-aware: returns access map for the requesting service domain.
- `is_user_active_for_product()` — Unified check: returns True if user has either an active subscription OR an active credit pool for the product.

**Credit System**:
- `create_credit_pool()` — Transactional creation of credit pool, invoice, and initial transaction. Uses `select_for_update` to prevent race conditions (CRIT-03).
- `cancel_credit_pools_for_subscription()` — Cancel all credit pools when a subscription is canceled.

### CurrencyService (`billing/currency_service.py`, ~552 lines)

Static methods for all currency operations:

- **Metadata**: `get_currency_symbol()`, `get_currency_name()`, `get_currency_decimal_digits()` — Lookups for 35+ currencies
- **Conversion**: `convert_price()` — Converts cents between currencies, handles zero-decimal currencies (JPY, KRW, VND) properly (HIGH-08 fix)
- **Batch**: `convert_plan_prices()` — Batch conversion for plan lists; only sets `user_currency` when conversion succeeds
- **Rates**: `get_exchange_rate()` — Handles same-currency, direct, reverse (inverted), and cross-pair via base currency. Guards against zero/tiny rates (MED-06 fix)
- **Fetching**: `fetch_exchange_rates()` — Primary API (open.er-api.com) with fallback (frankfurter.app), admin alert on both failures (CC-03)
- **Updating**: `update_exchange_rates()` — Upserts ExchangeRate table from fetched rates
- **Auth/me helper**: `get_all_rates_for_base()` — Piggybacked on auth/me response

### Stripe Error Handler (`billing/stripe_errors.py`, ~334 lines)

`handle_stripe_error()` provides centralized, user-friendly error translation:

1. **Message patterns** (25+ regex patterns): Covers currency errors, subscription state conflicts, payment method issues (card_declined, insufficient_funds, expired_card), price/product errors, coupon/promo issues, refund conflicts, rate limiting, portal/checkout errors
2. **Error code map**: Fallback for Stripe error codes not caught by message patterns
3. **HTTP status fallback**: 500 → "temporarily unavailable", 429 → rate limit, 401 → CRITICAL alert (invalid API key, emails admins), 404 → not found
4. **Final catch-all**: Generic but not alarming

## 2.5 Schemas (Pydantic)

All API input/output schemas use Pydantic models via django-ninja / django-ninja-extra. There are four schema files:

### `billing/schemas.py` (~686 lines) — User-facing billing schemas

- **Product/Plan/AccessEntry**: Output schemas for public product catalog
- **SubscriptionInfoSchema / SubscriptionOutputSchema / SubscriptionDetailSchema**: Subscription data at different detail levels
- **AuthMeSchema**: Enhanced auth/me response including subscription, access_map, exchange_rates, currencies, credit_pools
- **CheckoutInputSchema / CheckoutOutputSchema**: Stripe checkout session creation
- **PortalOutputSchema**: Stripe customer portal session
- **PlanChangePreviewSchema / ProrationPreviewOutputSchema**: Plan change preview with proration details
- **ConfirmPlanChangeInputSchema / ConfirmPlanChangeOutputSchema**: Plan change confirmation with preview token
- **TransactionItemSchema / TransactionHistoryOutputSchema**: Unified transaction history (Stripe + credit invoices)
- **CreditPoolSchema / CreditInvoiceSchema / CreditTransactionSchema / CreditPurchaseRequestSchema**: Credit system schemas
- **ExchangeRateSchema / CurrencyMetadataSchema**: Currency data

### `billing/admin_schemas.py` (~1143 lines) — Admin-only schemas

Extensive schemas for all admin operations including product CRUD, plan CRUD (with duplicate), access entry bulk operations, credit pool admin operations (purchase, refund, adjust), subscription admin operations (override, extend, plan change log), user admin operations (status, role, audit events), refund admin schemas with two-person approval, metrics schemas (overview, revenue by product/plan/month, subscription funnel, products), audit log, webhook event log, invoice with line items, and service domain admin schemas.

### `users/schemas.py` (~479 lines) — Auth & user schemas

- **Registration/Login**: `RegisterInputSchema`, `LoginInputSchema` (with `remember` flag)
- **Tokens**: `TokenOutputSchema`, `AccessTokenOnlySchema`, `TokenRefreshInputSchema`, `CookieRefreshInputSchema`, `TokenVerifyInputSchema`, `TokenBlacklistInputSchema`
- **SSO**: `AuthorizeOutputSchema`, `TokenExchangeInputSchema`
- **Password**: `PasswordResetRequestSchema`, `PasswordResetConfirmSchema` (OTP-based), `ChangePasswordInputSchema`, `PasswordConfirmSchema`
- **Email**: `ChangeEmailRequestSchema`, `ChangeEmailConfirmOTPSchema`, `EmailVerifyRequestSchema`, `EmailVerifyConfirmSchema`
- **Profile**: `UserOutputSchema` (ModelSchema), `UserProfileUpdateInputSchema`
- **Account**: `DeleteAccountRequestSchema`
- **Choices**: `ChoiceItemSchema`, `ChoicesSchema` — Enum values for registration forms
- **Validation**: `_validate_password_strength()` — Enforces uppercase, lowercase, digit, special character

### `common/schemas.py` — Shared schemas

Pagination metadata, API key output schemas, and common response types.

## 2.6 URLs & Routing

The project does NOT use traditional Django `urls.py` files per app. Instead, routing is handled entirely by **django-ninja-extra's `auto_discover_controllers()`** mechanism.

**How it works**:
1. The `NinjaExtraAPI` instance is created in `api/views.py` with `csrf=False` (API uses JWT, not CSRF tokens)
2. `api.auto_discover_controllers()` scans all installed apps for `@api_controller` decorated classes
3. Admin controllers are explicitly imported because they don't follow naming conventions: `admin_controller`, `admin_subscription_controller`, `admin_user_controller`, `admin_metrics_controller`
4. In `base/urls.py`, the API is mounted at `/api/v1/`:
   ```python
   path("api/v1/", api.urls, name="base")
   ```

**Route prefix convention**:
- `BillingPublicController`: prefix `/billing`
- `BillingProtectedController`: prefix `/billing`
- `BillingAdminController`: prefix `/billing/admin`
- `BillingWebhookController`: prefix `/billing/webhooks`
- `AuthController`: prefix `/auth`
- `AdminProductController`: prefix `/admin`
- `AdminPlanController`: prefix `/admin`
- `AdminSubscriptionController`: prefix `/admin`
- `AdminUserController`: prefix `/admin`
- `AdminMetricsController`: prefix `/admin`
- `AdminApiKeyController`: prefix `/admin/api-keys`

Full URL example: `POST /api/v1/billing/checkout` → `BillingProtectedController.create_checkout()`

## 2.7 Middleware Stack

The middleware chain is defined in `base/settings.py` MIDDLEWARE list in strict order:

| # | Middleware | Purpose |
|---|---|---|
| 1 | `SecurityMiddleware` | Django security headers, SSL redirect, HSTS |
| 2 | `SessionMiddleware` | Django session management |
| 3 | `CorsMiddleware` | django-cors-headers: standard CORS from `CORS_ALLOWED_ORIGINS` |
| 4 | **`service_domain_cors_middleware`** | Custom: Dynamic CORS from ServiceDomain table (Redis cached, 5-min TTL) |
| 5 | `CommonMiddleware` | Django common middleware (URL normalization) |
| 6 | `ninja_file_fix_middleware` | Fixes file upload handling in django-ninja |
| 7 | **`service_credential_middleware`** | Custom: Validates `X-API-Key` header on every request |
| 8 | `CsrfViewMiddleware` | Django CSRF protection |
| 9 | `AuthenticationMiddleware` | Django authentication |
| 10 | `MessageMiddleware` | Django messages framework |
| 11 | `XFrameOptionsMiddleware` | Clickjacking protection |

### Custom: `service_credential_middleware` (`common/middleware.py`, ~420 lines)

This is a dual sync/async middleware (using Django 5.2's `@sync_and_async_middleware` pattern) that validates API key authentication:

1. Checks if request includes `X-API-Key` header — if not, passes through (no-op for browser requests)
2. Validates key prefix is `sb_live_`
3. Checks `X-Service-Domain` header is present
4. Computes SHA-256 hash of the raw key
5. Looks up `ServiceCredential` by hash
6. Verifies credential is active (`is_active=True`)
7. Verifies associated `ServiceDomain` is active
8. **Domain cross-check**: Verifies the `X-Service-Domain` header matches the credential's domain (prevents spoofing)
9. Attaches `request.service_credential` and `request.service_domain_from_key`
10. Atomically updates `last_used_at` and tracks analytics via Redis
11. If `settings.API_KEY_ENFORCED = True`, returns 401 on invalid keys; otherwise logs warnings

### Custom: `service_domain_cors_middleware` (`common/cors_middleware.py`, ~188 lines)

Dual sync/async middleware that provides dynamic CORS based on the `ServiceDomain` database table:

1. Caches allowed origins in Redis (key: `sattabase_allowed_cors_origins`, TTL: 5 minutes)
2. Always includes `FRONTEND_URL` from settings
3. On cache miss, queries all active `ServiceDomain` records for their domain URLs
4. If the request's `Origin` header matches a cached origin, injects specific CORS headers (origin, methods, headers, credentials) overriding wildcard `*`
5. In DEBUG mode with `CORS_ALLOW_ALL_ORIGINS=True`, allows localhost origins for development

## 2.8 Signals

### `common/signals.py` (~140 lines)

Two post-save/post_delete signals on the `ServiceCredential` model:

1. **CORS Cache Invalidation** (`post_save` and `post_delete`): When a ServiceCredential is saved or deleted, the Redis cache key `sattabase_allowed_cors_origins` is deleted. This forces the `service_domain_cors_middleware` to re-query the ServiceDomain table on the next request, ensuring new domains are immediately reflected in CORS headers.

2. **Audit Logging** (`post_save` on create/update, `post_delete`): Writes to `AdminAuditLog` via `common.audit.write_credential_audit()`. Captures action type (create, update, revoke, rotate, delete), credential details (id, prefix, name, service_domain), and changes. This runs synchronously in the same transaction as the model save, ensuring audit records are never orphaned.

Signals are wired in `common/apps.py` `CommonConfig.ready()` method, which imports the signals module.

### `users/signals.py`

Post-save signal on the User model that handles:
- Setting default role on user creation
- Syncing `is_staff` flag when role changes to/from admin/owner

## 2.9 Celery Tasks

### Configuration (`base/celery.py`)

Celery is configured with Redis as the broker (`CELERY_BROKER_URL`), `django-celery-beat` as the scheduler, and `django-celery-results` for storing task results in the Django ORM. Tasks are auto-discovered from all installed apps.

### Scheduled Tasks (`billing/tasks.py`, ~980 lines)

| Task | Schedule | Purpose |
|---|---|---|
| `reconcile_webhooks` | Every 6 hours | Retries failed webhook events from `WebhookEventLog` |
| `sync_customer_data` | Daily | Syncs Stripe customer data to local user profiles |
| `dunning_retry` | Daily | Staged dunning for past_due subscriptions: Day 3 → email reminder, Day 5 → urgent email, Day 7 → restrict access, Day 14 → auto-cancel. Uses `past_due_at` (not `updated_at`) for day counting (MED-04 fix). Only advances dunning step if action succeeds. |
| `update_exchange_rates` | Daily | Delegates to `currency_service.update_exchange_rates()` |
| `cleanup_stale_webhook_events` | Weekly | Deletes processed webhook events older than 90 days |
| `recognize_revenue` | Daily | Creates `RevenueRecognitionEntry` for active/trialing/canceled subscriptions. Excludes PAST_DUE (MED-05 for ASC 606 compliance). Uses `math.ceil` for daily cents, adjusts last day for rounding drift. `bulk_create` with `ignore_conflicts`. |
| `consume_credit_periods` | Daily | Consumes billing periods from active credit pools. Uses `select_for_update` to prevent race conditions (CRIT-04 fix). |

### On-Demand Tasks

| Task | Trigger | Purpose |
|---|---|---|
| `send_credit_request_approved_email` | Admin approval action | Sends professional HTML approval email with credit details and action buttons |
| `send_credit_request_rejected_email` | Admin rejection action | Sends professional HTML rejection email with reason and resubmit button |
| `deliver_credential_webhook` | Credential revoke/rotate | Dispatches HMAC-signed webhook to service domain's webhook_url |

---

# 3. Frontend Architecture Deep Dive

> **Section Status**: ✅ Complete — Added 2026-06-05

## 3.1 Astro + Vue Project Structure

The frontend is built on **Astro 6** running in **SSR mode** (`output: "server"`) with the **Node.js standalone adapter**. Interactive functionality is provided by **Vue 3** components mounted as islands. The project uses **Tailwind CSS v4** configured via the `@theme` directive in `global.css` (replacing the traditional `tailwind.config.js`).

### Configuration Files

**`astro.config.mjs`** — Core Astro configuration:
```javascript
export default defineConfig({
  output: "server",              // SSR mode
  adapter: node({ mode: "standalone" }),
  integrations: [vue()],
  vite: {
    plugins: [tailwindcss()],    // Tailwind v4 via Vite plugin
    ssr: { external: ["vue"] },  // SSR external for Vue
  },
  define: { "process.env.APP_VERSION": JSON.stringify(version) },
});
```

Key architectural decisions:
- **SSR mode** ensures pages are server-rendered for SEO and initial load performance, while Vue islands provide client-side interactivity
- **Standalone adapter** means the frontend runs as a Node.js HTTP server (not static files)
- **Tailwind v4 via Vite plugin** replaces the PostCSS-based approach — CSS is processed at build time
- **Vue external in SSR** prevents Vue from being bundled into the server bundle, reducing server memory usage

**`package.json`** — Minimal dependencies:
- `astro@^6.1.9` — Framework
- `vue@^3.5.33` — Interactive islands
- `@astrojs/vue@^6.0.1` — Astro-Vue integration
- `@astrojs/node@^10.0.6` — Node.js server adapter
- `tailwindcss@^4.2.4` — CSS utility framework
- `typescript@^5.9.3` — Type safety
- No state management library (Pinia/Vuex) — state is managed via composables with window-level shared refs
- No router library — Astro handles routing natively
- No HTTP client library — custom `apiClient` wrapper around `fetch`

**`tsconfig.json`** — TypeScript with strict mode, path aliases (`@/` → `src/`), and Vue JSX support.

### Island Architecture

The project follows Astro's **Islands Architecture** pattern where:
- **Astro components** (`.astro` files) handle static layout, page structure, and server-side data fetching
- **Vue components** (`.vue` files) handle interactive client-side functionality
- Vue islands are mounted with `client:only="vue"` (no SSR for Vue components — they hydrate only on the client) or `client:load` (hydrate immediately on page load)

The choice of `client:only="vue"` for most page-level Vue components means:
- The Astro server renders the layout shell (navbar, sidebar, etc.)
- Vue components are rendered entirely on the client after the page loads
- This avoids SSR complexity with Vue reactivity and browser APIs
- Initial page load shows a loading skeleton, then the Vue component mounts and fetches data

## 3.2 Page Routes & Routing

Astro uses file-system-based routing. The `src/pages/` directory structure directly maps to URL paths. All pages are `.astro` files that serve as thin wrappers mounting Vue islands.

### Route Map

| Route | Page File | Vue Component | Layout | Auth |
|---|---|---|---|---|
| `/` | `index.astro` | (redirects to `/dashboard`) | — | — |
| `/auth/login` | `auth/login.astro` | `LoginForm.vue` | AuthLayout | No |
| `/auth/register` | `auth/register.astro` | `RegisterForm.vue` | AuthLayout | No |
| `/auth/callback` | `auth/callback.astro` | `AuthCallbackHandler.vue` | AuthLayout | No |
| `/auth/forgot-password` | `auth/forgot-password.astro` | `ForgotPasswordForm.vue` | AuthLayout | No |
| `/auth/reset-password` | `auth/reset-password.astro` | `ResetPasswordForm.vue` | AuthLayout | No |
| `/auth/verify-email` | `auth/verify-email.astro` | `VerifyEmailForm.vue` | AuthLayout | No |
| `/auth/email-change/confirm` | `auth/email-change/confirm.astro` | `EmailChangeConfirm.vue` | AuthLayout | No |
| `/dashboard` | `dashboard/index.astro` | `DashboardHome.vue` | DashboardLayout | Yes |
| `/dashboard/profile` | `dashboard/profile.astro` | `ProfileCard.vue` | DashboardLayout | Yes |
| `/dashboard/settings` | `dashboard/settings.astro` | `SettingsPanel.vue` | DashboardLayout | Yes |
| `/dashboard/billing` | `dashboard/billing/index.astro` | `BillingOverview.vue` | DashboardLayout | Yes |
| `/dashboard/billing/transactions` | `dashboard/billing/transactions.astro` | `TransactionHistory.vue` | DashboardLayout | Yes |
| `/dashboard/billing/plans` | `dashboard/billing/plans/index.astro` | `PlansLanding.vue` | DashboardLayout | Yes |
| `/dashboard/billing/plans/:slug` | `dashboard/billing/plans/[slug].astro` | `PlanComparison.vue` | DashboardLayout | Yes |
| `/dashboard/billing/credits` | `dashboard/billing/credits/index.astro` | `UserCreditsClient.vue` | DashboardLayout | Yes |
| `/dashboard/billing/credits/request` | `dashboard/billing/credits/request.astro` | `CreditRequestClient.vue` | DashboardLayout | Yes |
| `/admin` | `admin/index.astro` | `AdminDashboard.vue` | AdminLayout | Yes + Staff |
| `/admin/users` | `admin/users/index.astro` | `UsersAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/users/:id` | `admin/users/[id].astro` | `UserDetailAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/products` | `admin/products/index.astro` | `ProductsAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/products/:id` | `admin/products/[id].astro` | `ProductDetailAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/plans/:planId` | `admin/plans/[planId].astro` | `PlanDetailAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/subscriptions` | `admin/subscriptions/index.astro` | `SubscriptionsAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/subscriptions/:id` | `admin/subscriptions/[id].astro` | `SubscriptionDetailAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/credits` | `admin/credits/index.astro` | `CreditManagement.vue` | AdminLayout | Yes + Staff |
| `/admin/credit-requests` | `admin/credit-requests/index.astro` | `CreditRequestsAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/refunds` | `admin/refunds/index.astro` | `RefundsAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/audit-log` | `admin/audit-log/index.astro` | `AuditLogAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/webhooks` | `admin/webhooks/index.astro` | `WebhooksAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/api-keys` | `admin/api-keys/index.astro` | `ApiKeysAdmin.vue` | AdminLayout | Yes + Staff |
| `/admin/bank-settings` | `admin/bank-settings/index.astro` | `BankSettingsAdmin.vue` | AdminLayout | Yes + Staff |

### Page File Pattern

Every page file follows a minimal pattern:

```astro
---
import DashboardLayout from "@/layouts/DashboardLayout.astro";
import DashboardHome from "@/components/vue/DashboardHome.vue";
---
<DashboardLayout title="Dashboard — SattaBase">
  <DashboardHome client:only="vue" />
</DashboardLayout>
```

The page file only:
1. Imports the appropriate layout
2. Imports the Vue component
3. Passes the component as a `<slot />` to the layout with `client:only="vue"`

No data fetching, no API calls, no business logic lives in `.astro` files — all interactivity is handled by Vue components.

### Dynamic Routes

Three pages use dynamic parameters:
- `[slug].astro` — Product plan pages (`/dashboard/billing/plans/:slug`)
- `[id].astro` — Admin detail pages (users, products, subscriptions)
- `[planId].astro` — Admin plan detail

Parameters are accessed via `Astro.params` in the Astro frontmatter and passed as props to Vue components.

## 3.3 Layouts System

The project has four layouts that form a hierarchy:

### BaseLayout.astro (Root — ~109 lines)

The root HTML shell used by all other layouts. It provides:

- **Meta tags**: viewport, description, generator, canonical URL, Open Graph, theme-color, format-detection
- **Fonts**: Inter (body) + JetBrains Mono (code) via Google Fonts
- **`<ClientRouter />`**: Enables Astro's View Transitions for client-side navigation
- **Dark mode init**: Inline `<script>` that checks `localStorage` and `prefers-color-scheme` to set `.dark` class before first paint (prevents flash of wrong theme)
- **Body**: `h-dvh flex flex-col overflow-hidden` — full viewport height, flex column layout
- **Global scripts**: `registerNavigate(navigate)` from `astro:transitions/client` — registers Astro's navigate function so that the API layer and SessionGuard can use it for programmatic navigation. Also calls `initToasts()` to set up the toast notification container.

### AuthLayout.astro (~136 lines)

Layout for authentication pages (login, register, forgot password, etc.):

- **Animated gradient background**: CSS gradient with pulsing blur blobs for visual appeal
- **Desktop brand panel** (left side on large screens): SattaBase logo, "Auth & Billing Hub" subtitle, description text, and four feature cards (Authentication, Subscriptions, Billing, One Dashboard)
- **Mobile header** (compact on small screens): Logo + "Part of SattaSpace" branding
- **Content card**: `<slot />` rendered inside a styled card div — this is where the auth form Vue component mounts
- **Footer**: "Back to home" link and copyright notice

No guards or session checks — auth pages are accessible to unauthenticated users.

### DashboardLayout.astro (~308 lines)

Layout for all user-facing dashboard pages, implementing the **Frozen Shell** pattern:

**Desktop Layout**:
- **Sidebar** (`transition:persist="app-sidebar"`): Fixed left sidebar with navigation links (Dashboard, Billing, Plans, Credits, Transactions, Settings), user avatar, and plan info. Persists across page navigations via View Transitions.
- **Navbar** (`transition:persist="app-navbar"`): Fixed top bar with search, notifications, and user dropdown. Also persists.
- **Content Island**: Scrollable main content area with `rounded-[25px]` border and `island-fade-in` animation (0.18s). This is the only area that swaps during navigation.

**Mobile Layout**:
- Sidebar becomes an overlay with backdrop, swipe-to-dismiss, and close on Escape key or window resize
- Navbar adapts with a hamburger menu button to toggle the mobile sidebar

**Guards**:
- `<SessionGuard client:load />` — Monitors auth state and redirects to login on session expiry
- Auth check happens at two levels: Astro middleware (server-side, checks refresh cookie) and SessionGuard (client-side, monitors JWT access token)

### AdminLayout.astro (~323 lines)

Mirrors the DashboardLayout with admin-specific differences:

- **Different persist keys**: `admin-sidebar` and `admin-navbar` (to avoid conflicts with user dashboard)
- **Admin components**: Uses `AdminSidebar.astro` and `AdminNavbar.astro` instead of user variants
- **Double guards**: Both `<SessionGuard client:load />` and `<AdminGuard client:load />` — SessionGuard handles auth state, AdminGuard enforces staff/owner/admin role
- **Amber accent**: Logo mark uses `bg-amber-600` and "Sattabase Admin" branding (vs. green for user dashboard)
- Same frozen shell pattern, mobile sidebar, and island styling as DashboardLayout

## 3.4 Vue Components Catalog

### User-Facing Components (`components/vue/`)

These components are mounted in user dashboard pages and handle all interactive functionality for regular (non-admin) users.

#### Auth Components

| Component | Lines | Purpose |
|---|---|---|
| `LoginForm.vue` | ~300 | Email/password login form with "remember me" toggle, rate limit handling, and redirect to previous page |
| `RegisterForm.vue` | ~400 | Registration with field validation, password strength indicator, timezone/currency/language selectors |
| `ForgotPasswordForm.vue` | ~200 | Password reset request form with email input and cooldown timer |
| `ResetPasswordForm.vue` | ~250 | OTP-based password reset confirmation with new password + confirm fields |
| `VerifyEmailForm.vue` | ~200 | Email verification with 6-digit OTP input, resend with cooldown |
| `EmailChangeConfirm.vue` | ~150 | Email change confirmation with OTP verification |
| `AuthCallbackHandler.vue` | ~100 | OAuth callback handler that exchanges authorization codes for tokens |

#### Dashboard Components

| Component | Lines | Purpose |
|---|---|---|
| `DashboardHome.vue` | ~688 | Central dashboard hub: account overview, subscription status, quick actions, recent billing, getting started checklist. Uses `useAuth`, `useSubscription`, `billingApi`, and `creditsApi`. |
| `ProfileCard.vue` | ~250 | User profile editing: first/last name, phone, avatar upload/delete with client-side validation |
| `SettingsPanel.vue` | ~500 | User preferences: timezone, currency, language, password change, email change, account deletion |

#### Billing Components

| Component | Lines | Purpose |
|---|---|---|
| `BillingOverview.vue` | ~400 | Billing summary: current subscription, next payment, credit pools, recent transactions. Handles both Stripe and credit invoice PDF downloads. |
| `TransactionHistory.vue` | ~500 | Full transaction history list with type-specific rendering (Stripe invoice vs. credit invoice), PDF download, status badges, and load-more pagination |
| `PlansLanding.vue` | ~350 | Product selection page with "Can't pay with international card?" info banner linking to credit request |
| `PlanComparison.vue` | ~500 | Plan feature comparison table with access matrix, price conversion, checkout redirect |
| `UserCreditsClient.vue` | ~400 | User's credit pools display, credit invoices with PDF download column, remaining credits visualization |
| `CreditRequestClient.vue` | ~300 | Credit purchase request form: product/plan selection, amount, bank reference, bank details display |
| `CreditRequestsClient.vue` | ~350 | User's credit request history with status tracking |

#### Guard Components

| Component | Lines | Purpose |
|---|---|---|
| `SessionGuard.vue` | ~150 | Invisible side-effect component that monitors auth state and redirects to login on session expiry. Uses multiple redirect mechanisms: Vue watch on `isLoggedIn`, window CustomEvent fallback, periodic 15-second token check, and `astro:page-load` handler for pending redirects. |
| `AdminGuard.vue` | ~30 | Invisible side-effect component that enforces admin role checks via `useAdminGuard()`. Redirects non-staff users to `/dashboard`. |

#### Utility Components

| Component | Lines | Purpose |
|---|---|---|
| `ApiKeysAdmin.vue` | ~400 | API key management (dual-use: appears in both admin and user dashboard contexts) |
| `SearchableSelect.vue` | ~150 | Reusable searchable dropdown component for selecting from lists |

### Admin Components (`components/admin/`)

These components are mounted in admin panel pages and provide the full administration interface.

#### Reusable UI Primitives

| Component | Purpose |
|---|---|
| `AdminPageHeader.vue` | Consistent page header with title, description, and optional action button |
| `AdminStatsCard.vue` | Statistics card with label, value, trend indicator, and icon |
| `AdminDataTable.vue` | Reusable data table with sorting, pagination, and row selection |
| `AdminFilterBar.vue` | Search input and filter controls for data tables |
| `AdminConfirmDialog.vue` | Modal confirmation dialog with slot content and customizable action button |
| `AdminStatusBadge.vue` | Colored status badge for subscription/refund/webhook statuses |
| `AdminEmptyState.vue` | Empty state placeholder with icon, title, and description |
| `AdminFeatureMatrix.vue` | Feature comparison matrix for plan access entries |
| `AdminAuditTimeline.vue` | Chronological audit log display with icons and timestamps |

#### Data Management Components

| Component | Lines | Purpose |
|---|---|---|
| `AdminDashboard.vue` | ~593 | Overview: 5 stats cards (Active Subscriptions, MRR, Trials, Past Due, Churn Rate), SVG revenue trend chart, horizontal bar chart for revenue by product, audit timeline, quick links |
| `UsersAdmin.vue` | ~400 | User listing with filters (active status, email verification, role, search) and navigation to user detail |
| `UserDetailAdmin.vue` | ~800 | User detail: profile info, role/status management, subscriptions tab, credit pools tab, audit trail tab |
| `ProductsAdmin.vue` | ~300 | Product listing with CRUD operations and service domain management |
| `ProductDetailAdmin.vue` | ~500 | Product detail: metadata editing, plan management, service domain configuration, access matrix |
| `PlanDetailAdmin.vue` | ~500 | Plan detail: metadata, pricing, access entries, feature matrix editor |
| `SubscriptionsAdmin.vue` | ~400 | Subscription listing with product/plan/status filters |
| `SubscriptionDetailAdmin.vue` | ~1615 | Full subscription administration: metadata, status override, plan change, period extension, refund issuance, invoice/refund history, credit pool management |
| `CreditRequestsAdmin.vue` | ~500 | Credit request review: approve/reject with admin notes, bank reference verification |
| `CreditManagement.vue` | ~500 | Credit pool management: purchase, refund, adjust credits, view invoices |
| `RefundsAdmin.vue` | ~400 | Refund listing with two-person approval workflow |
| `AuditLogAdmin.vue` | ~300 | Audit log viewer with admin/action/date filtering |
| `WebhooksAdmin.vue` | ~300 | Webhook event log with retry capability |
| `BankSettingsAdmin.vue` | ~300 | Bank account settings CRUD with encrypted account numbers |

### Astro Layout Sub-Components (`components/astro/`)

These are Astro components (not Vue) used within layouts for static/semi-static elements:

| Component | Purpose |
|---|---|
| `Navbar.astro` | User dashboard top navigation bar with user dropdown, theme toggle |
| `Sidebar.astro` | User dashboard left sidebar with navigation links, plan info, user avatar |
| `AdminNavbar.astro` | Admin top navigation with admin-specific user dropdown |
| `AdminSidebar.astro` | Admin left sidebar with admin section navigation |
| `LoadingSpinner.astro` | SVG loading spinner animation |
| `EmptyState.astro` | Generic empty state with icon and message |

The sidebar and navbar components include complex JavaScript for:
- 3-path user info fetch (cached → fetchUser → /users/me fallback)
- Retry with exponential backoff on auth failures
- Cross-component sync events for user state
- Init guards to prevent duplicate listener registration during View Transitions

## 3.5 Composables (State Management)

The project uses Vue 3 composables as its state management layer — no Pinia, no Vuex. All composables follow a consistent pattern using **window-level shared state** to survive Astro View Transition module re-evaluations.

### Shared Pattern: Window-Level Singletons

Every composable that manages shared state follows this pattern:

```typescript
const SB_KEY = "__sb_xxx_composable";

function getSharedState() {
  if (typeof window === "undefined") {
    // SSR fallback — create fresh state
    return { ref1: ref(null), ref2: ref(false), ... };
  }
  const win = window as any;
  if (!win[SB_KEY]) {
    // First initialization — create refs and store on window
    win[SB_KEY] = { ref1: ref(null), ref2: ref(false), ... };
  }
  return win[SB_KEY];
}
```

This ensures that:
1. During SSR, composables create fresh state (no `window` object)
2. On first client-side mount, state is created and stored on `window`
3. After a View Transition (which re-evaluates the module), the composable reconnects to the existing `window` refs instead of creating new ones
4. All components that call the same composable share the same reactive state

### Composable Reference

#### `useAuth.ts` (~530 lines) — Core Authentication State

The most critical composable, providing shared auth + billing state:

**Window-level state**: `__sb_auth_composable`
- `userRef: Ref<UserProfile | null>` — Current user profile
- `subscriptionRef: Ref<SubscriptionOutputSchema[]>` — User's subscriptions
- `accessRef: Ref<Record<string, AccessEntry>>` — Feature access map
- `loadingRef: Ref<boolean>` — Loading state
- `errorRef: Ref<string | null>` — Error state
- `initializedRef: Ref<boolean>` — Whether initial fetch has completed
- `hasTokenRef: Ref<boolean>` — Whether access token exists

**Key features**:
- `isLoggedIn = computed(() => !!sharedUser.value && sharedHasToken.value)` — Checks BOTH user data AND token presence (FIRST-CLICK FIX)
- Event listeners for `auth:logout`, `auth:session-expired`, `auth:token-refreshed` + CustomEvent backups
- `sattabase:billing-updated` listener auto-invalidates and refetches data after billing changes
- `fetchUser()` — Deduplicated (multiple concurrent callers share one promise)
- `useSessionGuard()` — Sets up Vue watch on `isLoggedIn` that redirects to login when it transitions from true → false on a protected page
- `sessionInfo` and `minutesUntilExpiry` computed properties

#### `useAdminGuard.ts` (~83 lines) — Admin Role Guard

Client-side admin route verification:
- Uses `useAuth().initAuth()` instead of separate `/users/me` call (API-1 fix for reducing duplicate calls)
- Checks `is_staff`, `role === "owner"`, or `role === "admin"`
- Not authorized → redirect to `/dashboard` (deferred with setTimeout)
- Auth error → redirect to `/auth/login` (deferred)
- Returns `isAuthorized`, `isLoading`, `adminUser`

#### `useSubscription.ts` (~155 lines) — Subscription State

Shared subscription data with staleness-based caching:
- **Window-level state**: `__sb_sub_composable`
- **Staleness threshold**: 60 seconds
- `fetchSubscriptions()` — Returns cached if fresh; deduplicated with shared promise
- `refetchSubscriptions()` — Forces fresh API call
- `invalidateSubscriptions()` — Marks cache as stale without fetching

#### `useAccess.ts` (~85 lines) — Feature Access Checking

Reactive feature-access checking built on `useAuth().access`:
- `hasAccess(key)` → `ComputedRef<boolean>` — Truthy check for boolean/number/string access values
- `getAccess<T>(key, defaultValue)` → `ComputedRef<T | undefined>` — Typed access value retrieval
- `accessKeys` → `ComputedRef<string[]>` — All available access keys

#### `useAdminData.ts` (~208 lines) — Admin Product/Domain Data

Shared admin data (products, service domains) for admin components:
- **Window-level state**: `__sb_admin_data_composable`
- **Staleness threshold**: 5 minutes (admin data changes rarely)
- `fetchAdminProducts()` — Deduplicated, staleness-based
- `fetchServiceDomains()` — Deduplicated, staleness-based
- All fetches share promises to prevent duplicate concurrent API calls

#### `useTransactions.ts` — Transaction History State

Shared transaction history across billing components:
- **Window-level state**: `__sb_txn_composable`
- **Staleness threshold**: 60 seconds
- Cursor-based pagination: `loadMore()` appends to existing list using `starting_after`
- `refetchTransactions()` — Force fresh (used after checkout/payment)
- `invalidateTransactions()` — Mark stale without fetching

#### `useProducts.ts` — Product Catalog State

Shared product data with per-slug caching:
- **Window-level state**: `__sb_products_composable`
- **Staleness threshold**: 120 seconds (products change rarely)
- `fetchProductDetail(slug, currency)` — Per-slug caching with deduplication
- `fetchAccessMatrix(slug)` — Per-slug caching with deduplication
- `fetchAllProductDetails(currency)` — Parallel batch fetch to avoid N+1 problem (used by PlansLanding)
- `invalidateProductDetail(slug)` — Invalidate a specific product's cache

#### `useFormErrors.ts` — Form Error Management

Simple reactive state for form error handling:
- `fieldErrors: Record<string, string>` — Reactive field-level errors
- `generalError: Ref<string>` — General/non-field error
- `setApiFieldErrors(errors?)` — Maps Django Ninja validation error format to local fieldErrors
- `hasErrors()` — Boolean check for any errors set

#### `useAsyncAction.ts` (~66 lines) — Async Action Wrapper

Generic async action state with toast integration:
- `execute<T>(fn, options?)` — Wraps async function calls with loading/error state
- Options: `successMessage`, `showErrorToast` (default true), `clearErrorBefore` (default true)
- Returns `loading`, `error`, `execute`

#### `useBillingRedirect.ts` (~79 lines) — Billing Return Detection

Detects billing return from Stripe Checkout/Portal:
- Checks for `?billing_updated=1` (or 0) in URL on mount
- Cleans URL via `history.replaceState`
- Dispatches `sattabase:billing-updated` CustomEvent (useAuth listens and auto-refetches)
- Returns `isBillingReturn`, `billingSuccess`, `returnUrl`

#### `usePasswordStrength.ts` — Password Validation

Reactive password strength checking:
- `passwordChecks: ComputedRef<PasswordChecks>` — Individual check results (length, uppercase, lowercase, number, special)
- `passwordStrength: ComputedRef<PasswordStrengthResult>` — Level (0-4), label, color, textClass
- `isValid: ComputedRef<boolean>` — All checks passed
- `strengthSegments: number[]` — [0, 1, 2, 3] for rendering the strength bar

#### `useOtpInput.ts` — OTP Digit Input

Reactive OTP input state with keyboard navigation:
- `digits: string[]` — Reactive array of individual digits
- `otpValue: ComputedRef<string>` — Joined OTP value
- `isComplete: ComputedRef<boolean>` — All digits filled
- `handleInput()`, `handleKeydown()`, `handlePaste()` — Full keyboard navigation with auto-advance
- `handleSimpleInput()`, `handleSimpleKeydown()` — Alternative handlers for single-field OTP inputs
- `reset()` — Clear all digits

#### `useMediaQuery.ts` — Responsive Viewport

Reactive CSS media query matching:
- `matches: Ref<boolean>` — Whether the query currently matches
- Updates automatically on viewport resize
- Cleanup on component unmount

#### `useCooldownTimer.ts` — Countdown Timer

Countdown timer for OTP resend flows:
- `cooldown: Ref<number>` — Seconds remaining
- `isCooling: Ref<boolean>` — Whether cooldown is active
- `startCooldown(seconds?)` — Start countdown (default 60s)
- `stopCooldown()` — Cancel countdown
- Auto-cleanup on component unmount

#### `index.ts` — Barrel Export

Re-exports all composables from a single entry point:
```typescript
export { useAuth } from "./useAuth";
export { useAdminGuard } from "./useAdminGuard";
export { useSubscription } from "./useSubscription";
// ... all 14 composables
```

## 3.6 API Client Layer (lib/)

The `lib/` directory contains six modules that form the complete API communication layer. All API calls from Vue components go through these modules — never directly via `fetch`.

### `api.ts` (~1369 lines) — Core HTTP Client

The central API client that handles all HTTP communication with the Django backend.

**API Base URL Resolution**:
- Development: `http://localhost:8086/api/v1`
- Production: `https://baseapi.sattaspace.com/api/v1`
- Determined by checking `import.meta.env.PROD` and `window.location.hostname`

**JWT Token Management**:
- Access token stored in memory (`window.__sb_auth.accessToken`) — never in localStorage
- Refresh token in httpOnly cookie (`sb_refresh_token`) — not accessible to JavaScript
- Proactive refresh: schedules token refresh 5 minutes before JWT `exp` claim
- Throttled refresh: minimum 30 seconds between refresh attempts, 3-second cooldown after failures
- Deduplicated refresh: multiple concurrent 401s share one refresh promise

**Auth Event System**:
- `auth:logout` — Emitted on explicit logout
- `auth:session-expired` — Emitted when refresh fails (session dead)
- `auth:token-refreshed` — Emitted after successful token refresh
- Dual dispatch: both module-level `Set<Function>` listeners AND `CustomEvent` on `window` (backup for View Transition scenarios where module-level listeners are lost)

**View Transition Integration**:
- `astro:before-preparation` — Cancels transition if session is expired and initialization is complete
- `astro:page-load` — Syncs auth state and reschedules proactive refresh timer

**Request Pipeline** (`apiClient.request()`):
1. Wait for initialization to complete
2. Check if proactive refresh is needed before the request
3. Add `Authorization: Bearer <token>` header
4. For GET requests: use cached response if available (5-second browser cache)
5. For mutations: set `cache: "no-store"` to prevent stale data
6. On 401 response: attempt token refresh, then retry once
7. On other errors: parse response body for field-level errors

**Error Handling**:
- `createApiErrorFromResponse()` — Parses API error responses into structured objects with:
  - `message: string` — Human-readable error message
  - `code: string` — Machine-readable error code (e.g., "validation_error")
  - `fields: Record<string, string[]>` — Field-level validation errors
  - `status: number` — HTTP status code

**`authHelpers`** object provides:
- `setAccessToken(token)` / `clearAuth()` / `getAccessToken()`
- `isAuthenticated()` — Checks for valid access token
- `isAuthReady()` — Checks if initialization is complete
- `navigateTo(path)` — Programmatic navigation using Astro's `navigate()` (registered via `registerNavigate()`)
- `waitForInit()` — Promise that resolves when auth initialization completes

### `auth.ts` (~478 lines) — Auth API Functions

Functions for all authentication-related API calls:

**Core Auth**:
- `login(payload)` → `TokenOutputSchema`
- `register(payload)` → `TokenOutputSchema`
- `logout()` — Cookie-based logout (401 = already logged out)
- `requestPasswordReset(email)` / `confirmPasswordReset(payload)` — OTP-based reset
- `changePassword(payload)` / `confirmIdentity(payload)` — Sensitive action confirmation

**Email Management**:
- `requestEmailChange(payload)` / `confirmEmailChangeOTP(payload)` — Email change with OTP
- `requestEmailVerification(email)` / `verifyEmail(payload)` — Email verification

**Profile**:
- `getCurrentUser()` → `UserProfile`
- `updateProfile(payload)` → `UserProfile`
- `updateAvatar(file)` / `deleteAvatar()` — Avatar management with client-side validation (type/size)

**Account**:
- `deleteAccount(payload)` — Soft-delete account

**SSO**:
- `exchangeAuthCode(code)` — Exchange SSO authorization code for tokens

**Helpers**:
- `isAuthenticated()` / `requireAuth()` — Auth state checks
- `getErrorMessage(error)` — Extract human-readable error from API errors
- `detectUserTimezone()` / `detectUserLanguage()` — Browser-based defaults

### `billing.ts` (~619 lines) — Billing API Functions

All billing-related API calls organized in the `billingApi` object:

**Product/Plan**:
- `getProducts()` → `ProductSchema[]`
- `getProductBySlug(slug, currency?)` → `ProductDetailSchema`
- `getProductAccessMatrix(slug)` → `AccessMatrixSchema`

**Auth/Subscription**:
- `getAuthMe()` → `AuthMeSchema` — Domain-aware auth response
- `getSubscriptions()` → `SubscriptionOutputSchema[]`
- `syncSubscriptions()` — Force sync from Stripe
- `getSubscriptionDetail(id)` → `SubscriptionDetailSchema`
- `cancelSubscription(id)` / `reactivateSubscription(id)`

**Plan Change** (Safe flow):
- `previewPlanChange(payload)` → `ProrationPreviewOutputSchema`
- `confirmPlanChange(payload)` → `ConfirmPlanChangeOutputSchema`
- `changePlan(payload)` — Deprecated direct change

**Checkout/Portal**:
- `createCheckout(payload)` → checkout URL
- `confirmCheckout(sessionId)` — Verify checkout completion
- `createPortalSession()` → portal URL

**History**:
- `getTransactionHistory(limit?, startingAfter?)` → `TransactionHistoryOutputSchema`
- `exportBillingData()` → blob for download

**User Currency**:
- `setUserCurrency(currency)` / `getUserCurrency()` — Currency preference state

**Formatting Helpers**:
- `formatPrice(cents, currency, locale?)` — Locale-aware price formatting
- `formatCycle(cycle)` — Human-readable billing cycle
- `getStatusStyle(status)` — Color classes for subscription status
- `formatDate(date)` — Locale-aware date formatting
- `formatMatrixValue()` / `getMatrixCellType()` / `getFeatureValueType()` / `formatFeatureValue()` — Access matrix formatting utilities

### `credits.ts` (~481 lines) — Credit System API Functions

All credit-related API calls in the `creditsApi` object:

**User Credit Operations**:
- `getMyCredits()` → Credit pool summary
- `getMyCreditPool(poolId)` → Credit pool detail
- `getMyCreditInvoices(poolId?)` → Credit invoice list
- `downloadCreditInvoicePdf(invoiceNumber)` → Blob URL — Uses `fetch()` with `Authorization: Bearer` header, creates Blob URL for in-browser PDF viewing. Revokes Blob URL after 60 seconds.

**Credit Purchase Request**:
- `requestCreditPurchase(payload)` → Credit request response
- `getProducts()` / `getPlans(productId)` / `getBankSettings()` — Reference data for the request form

**Admin Credit Operations**:
- `adminListCredits(filters?)` / `adminGetCreditPool(poolId)` — Listing
- `adminPurchaseCredit(payload)` / `adminRefundCredit(payload)` / `adminAdjustCredit(payload)` — Pool operations
- `adminListCreditInvoices(filters?)` / `adminGetCreditInvoice(id)` — Invoice management

**Admin Credit Request Review**:
- `adminListCreditRequests(filters?)` / `adminGetCreditRequest(id)` — Listing
- `adminApproveCreditRequest(id, payload)` / `adminRejectCreditRequest(id, payload)` — Review actions

**Admin Bank Settings**:
- `adminListBankSettings()` / `createBankSettings(payload)` / `updateBankSettings(id, payload)`
- `toggleBankSettings(id)` / `deleteBankSettings(id)`

### `admin.ts` (~1263 lines) — Admin API Functions

The largest lib module, providing all admin panel API calls via the `adminApi` object:

**API Keys**: Full CRUD + analytics
- `listApiKeys(filters?)`, `createApiKey(payload)`, `revokeApiKey(id)`, `rotateApiKey(id)`
- `getApiKeyAnalytics()`, `getApiKeyDetailAnalytics(id)`
- `listServiceDomains()`

**Products**: CRUD + service domain management
- `listProducts(filters?)`, `getProduct(id)`, `createProduct(payload)`, `updateProduct(id, payload)`, `deleteProduct(id)`
- `createServiceDomain(payload)`, `updateServiceDomain(id, payload)`, `deleteServiceDomain(id)`

**Plans**: CRUD + access entries + feature matrix
- `listPlans(filters?)`, `getPlan(id)`, `createPlan(payload)`, `updatePlan(id, payload)`, `deletePlan(id)`, `duplicatePlan(id)`
- `listAccessEntries(planId)`, `createAccessEntry(payload)`, `updateAccessEntry(id, payload)`, `bulkReplaceAccessEntries(planId, entries)`
- `getAccessMatrix(planId)`, `saveAccessMatrix(planId, rows)`

**Subscriptions**: Comprehensive management
- `listSubscriptions(filters?)`, `getSubscription(id)` — Listing
- `overrideSubscription(id, payload)`, `cancelSubscription(id)`, `expireSubscription(id)`, `extendSubscription(id, payload)` — Lifecycle
- `getSubscriptionPlanChanges(id)`, `getSubscriptionInvoices(id)` — History
- `issueSubscriptionRefund(id, payload)`, `getSubscriptionRefunds(id)` — Refunds

**Users**: Management and audit
- `listUsers(filters?)`, `getUserDetail(id)` — Listing
- `updateUserStatus(id, payload)`, `updateUserRole(id, payload)` — Management
- `getUserAudit(id)` — Audit trail

**Refunds**: Approval workflow
- `listRefunds(filters?)`, `approveRefund(id)`, `rejectRefund(id, payload)`

**Metrics**: Dashboard data
- `getMetricsOverview()`, `getMetricsRevenue()`, `getMetricsSubscriptions()`, `getMetricsProducts()`

**Webhooks**: Monitoring
- `listWebhooks(filters?)`, `retryWebhook(id)`

**Audit Log**: Admin activity
- `listAuditLog(filters?)`

**Formatting Helpers**: `formatKeyPrefix()`, `formatDateTime()`, `formatRelativeTime()`, `getSubscriptionStatusColor()`, `getRefundStatusColor()`, `getWebhookStatusColor()`

### `toast.ts` (~199 lines) — Toast Notifications

Lightweight, dependency-free toast notification system:

- **Types**: `success`, `error`, `info`, `warning`
- **Options**: `duration` (default 4000ms), `action` button with label and callback
- **DOM-based**: Creates `#toast-container` div (fixed top-right, z-index 2147483647)
- **Styling**: Tailwind classes with dark mode support, SVG icons per type
- **Functions**:
  - `showToast(message, type, options?)` — Display a toast notification
  - `initToasts()` — Create the toast container in the DOM
- **Animation**: Dismiss with opacity + translateX transition

## 3.7 Authentication & Session Management (Frontend)

The frontend implements a multi-layered auth system that ensures users are always authenticated on protected pages and gracefully handles session expiry across Astro View Transitions.

### Three-Layer Session Guard

Authentication is enforced at three independent layers, each catching edge cases the others might miss:

**Layer 1: Astro Server Middleware** (`src/middleware.ts`, ~227 lines)
- Runs on every server-side request before the page is rendered
- Checks for `sb_refresh_token` httpOnly cookie
- If no cookie: 302 redirect to `/auth/login?redirect=<current_path>` (preserves intended destination)
- If cookie exists: validates by calling `POST /api/v1/auth/token/refresh-cookie` to the backend
- For admin pages: additionally calls `GET /api/v1/users/me` to check `is_staff`
- If non-staff on admin page: 302 redirect to `/dashboard`
- JSON requests (XHR) receive 401 instead of 302 redirect
- Excludes Django admin (`/admin/django`) which has its own auth
- Protected path prefixes: `/dashboard`, `/admin`, `/settings`, `/profile`

**Layer 2: SessionGuard Vue Component** (`SessionGuard.vue`, ~150 lines)
- Invisible side-effect component mounted in DashboardLayout and AdminLayout
- Monitors `isLoggedIn` computed property from `useAuth()` — when it transitions from true to false on a protected page, schedules redirect to `/auth/login`
- Listens for `auth:session-expired` events from the API layer
- Listens for `sb:auth:session-expired` CustomEvent on window (fallback if module-level listeners were lost during View Transition)
- Periodic health check: every 15 seconds, verifies access token still exists on protected pages
- `astro:page-load` handler: checks for `__sb_redirect_reason` flag set by api.ts during cancelled View Transitions

**Layer 3: API Client** (`lib/api.ts`)
- Proactive token refresh: schedules refresh 5 minutes before JWT `exp` claim
- 401 → refresh → retry: on any API 401, automatically attempts token refresh and retries the request once
- If refresh fails: emits `auth:session-expired` event → SessionGuard handles redirect
- `astro:before-preparation` handler: cancels pending View Transition if session is expired

### Navigation Convention (Vue 3 Pattern)

A critical architectural decision: **the API layer never directly navigates**. Instead:
1. `api.ts` emits events (`auth:logout`, `auth:session-expired`) and sets flags (`__sb_redirect_reason`)
2. `SessionGuard.vue` listens for these events and calls `authHelpers.navigateTo(path)`
3. `navigateTo()` uses Astro's `navigate()` function (registered via `registerNavigate()`)
4. All navigation is **deferred with `setTimeout(0)`** to avoid the "querySelector null" error that occurs when `navigate()` is called synchronously during a View Transition lifecycle event

This separation ensures that navigation always happens through Astro's router, properly integrated with the View Transition lifecycle.

### Token Refresh Flow

```
Browser                    Frontend (api.ts)              Backend (AuthController)
   │                            │                                │
   │  API Request               │                                │
   │  (with Bearer token)       │                                │
   │──────────────────────────→ │  Forward to backend            │
   │                            │──────────────────────────────→ │
   │                            │                                │
   │                            │  401 Unauthorized              │
   │                            │←────────────────────────────── │
   │                            │                                │
   │                            │  POST /auth/token/refresh-cookie│
   │                            │  (httpOnly cookie auto-sent)   │
   │                            │──────────────────────────────→ │
   │                            │                                │
   │                            │  200 OK + new access token     │
   │                            │←────────────────────────────── │
   │                            │                                │
   │                            │  Retry original request        │
   │                            │  (with new Bearer token)       │
   │                            │──────────────────────────────→ │
   │                            │                                │
   │  Original response         │  200 OK                        │
   │←────────────────────────── │←────────────────────────────── │
```

If the refresh also fails (refresh token expired/invalid):
1. `api.ts` emits `auth:session-expired`
2. `SessionGuard.vue` schedules redirect to `/auth/login`
3. `api.ts` clears auth state (`clearAuth()`)

## 3.8 Styling System

### Tailwind CSS v4 Configuration

The project uses **Tailwind CSS v4** configured entirely via CSS — there is no `tailwind.config.js` file. Configuration is done in `global.css` using the `@theme` directive.

**Brand Palette** (Green — mapped to `--color-brand-*`):
- 50: `#f0fdf4` through 950: `#052e16`
- Used for primary actions, buttons, success states, and branding

**Design Token System** (CSS custom properties):
- `--color-background` / `--color-foreground` — Page background and text
- `--color-card` / `--color-card-foreground` — Card containers
- `--color-muted` / `--color-muted-foreground` — Secondary/muted content
- `--color-primary` / `--color-primary-foreground` — Primary buttons/actions
- `--color-secondary` / `--color-secondary-foreground` — Secondary elements
- `--color-accent` / `--color-accent-foreground` — Accent highlights
- `--color-destructive` / `--color-destructive-foreground` — Error/danger states
- `--color-border` / `--color-input` / `--color-ring` — Form elements

**Dark Mode**:
- Class-based (`.dark` class on `<html>` element)
- Set by inline script in `BaseLayout.astro` before first paint
- Checks `localStorage.theme` first, then `prefers-color-scheme`
- `@custom-variant dark (&:is(.dark *))` — Tailwind v4 dark mode variant
- `transition-theme` utility class for smooth dark mode transitions (0.2s on background, border, color)

**Typography**:
- Body: `Inter` (Google Fonts, sans-serif stack)
- Code: `JetBrains Mono` (Google Fonts, monospace stack)
- Font size tokens: `2xs` (0.625rem) through `4xl` (2.25rem) with line heights

**Reusable Component Classes**:
| Class | Purpose |
|---|---|
| `btn-primary` | Green primary button with hover/focus/disabled states |
| `btn-secondary` | Bordered secondary button |
| `btn-destructive` | Red danger button |
| `btn-ghost` | Transparent ghost button |
| `input-field` | Form input with border, focus ring, disabled state |
| `card` | Rounded container with border and shadow |
| `glass` | Glassmorphism effect (backdrop-blur, semi-transparent) |
| `gradient-brand` | Green gradient background |
| `skeleton` | Shimmer loading placeholder animation |

**Animations**:
- `fade-in` (0.3s) — General element appearance
- `slide-up` (0.35s) — Content entrance from below
- `scale-in` (0.2s) — Dialog/modal appearance
- `skeleton-shimmer` (1.8s infinite) — Loading placeholder pulse
- `slide-in` (0.2s) — Toast notification entrance

**Custom Scrollbar**:
- 8px width, rounded thumb
- Hover state with darker thumb
- Firefox support via `scrollbar-width: thin`
- Dark mode: lighter thumb colors

## 3.9 Astro Server Middleware

The Astro middleware (`src/middleware.ts`, ~227 lines) provides server-side route protection for all page requests.

### Protected Path Configuration

```typescript
const PROTECTED_PREFIXES = ["/dashboard", "/admin", "/settings", "/profile"];
```

Any request whose pathname starts with one of these prefixes is subject to authentication checks.

### Authentication Check Flow

For each protected request:

1. **Cookie Check**: Look for `sb_refresh_token` httpOnly cookie and `sb_remember_me` cookie
2. **No Cookie → Redirect**: If no refresh token cookie exists, redirect to `/auth/login?redirect=<current_path>` (preserving the intended destination for post-login redirect)
3. **Cookie Validation**: If the cookie exists, call `POST /api/v1/auth/token/refresh-cookie` to validate it with the backend
4. **Invalid Cookie → Redirect**: If the backend returns an error, the refresh token is expired/invalid — redirect to login
5. **Admin Page Check**: For paths starting with `/admin` (excluding `/admin/django`), additionally call `GET /api/v1/users/me` and check `is_staff`
6. **Non-Staff on Admin → Redirect**: If the user is not staff, redirect to `/dashboard`

### API URL Resolution

The middleware uses the same API URL logic as `api.ts`:
- Development: `http://localhost:8086/api/v1`
- Production: `https://baseapi.sattaspace.com/api/v1`

### Request Type Handling

- **HTML requests** (normal navigation): 302 redirect to login
- **JSON requests** (XHR/fetch): Return 401 status code without redirect

### Django Admin Exclusion

The `/admin/django` path is explicitly excluded because Django's built-in admin has its own authentication system. The middleware only handles SattaBase's custom auth.

### Redirect Parameter

When redirecting to login, the middleware appends the current path as a `redirect` query parameter:
```
/auth/login?redirect=/dashboard/billing/plans
```
After successful login, `LoginForm.vue` reads this parameter and redirects the user back to their intended destination.

---

# 4. Authentication & Authorization

> **Section Status**: ✅ Complete — Added 2026-06-05

SattaBase implements a dual-track authentication system: **JWT-based authentication** for browser/frontend users and **API key authentication** for SDK/service-to-service communication. Both tracks are secured with rate limiting, account lockout, audit logging, and layered session management. This section provides a comprehensive deep dive into every component of the auth system, from token generation to session expiry handling.

## 4.1 JWT Authentication Flow

The platform uses **django-ninja-jwt** (v5.4.4) for JWT token management, configured with access/refresh token pairs, rotation, and blacklisting. JWT configuration in `base/settings.py` under `SIMPLE_JWT` defines token lifetimes, rotation behavior, and signing keys.

### Token Pair Architecture

When a user authenticates successfully, the system generates two tokens:

- **Access Token**: Short-lived JWT (default lifetime configured via `SIMPLE_JWT.ACCESS_TOKEN_LIFETIME`, typically 5-15 minutes) that authorizes API requests. Contains `user_id`, `exp`, `iat`, and `jti` claims. Sent in the `Authorization: Bearer <token>` header on every API request.
- **Refresh Token**: Long-lived JWT (default lifetime typically 7 days) used only to obtain new access tokens. Stored in an httpOnly cookie (`sb_refresh_token`), never exposed to JavaScript. Contains the same claims as the access token plus a `token_type` claim.

### JWTAuth Class

The `JWTAuth` class (defined in `users/controllers.py`) extends `ninja.security.HttpBearer` and serves as the primary authentication backend for all protected endpoints:

```python
class JWTAuth(HttpBearer):
    async def authenticate(self, request, token):
        access_token = AccessToken(token)
        user_id = access_token.get("user_id")
        if not user_id:
            return None
        user = await User.objects.filter(
            id=user_id, is_active=True, is_deleted=False
        ).afirst()
        if user:
            request.user = user
            return user
        return None
```

Key behaviors of the `JWTAuth` class:

1. **Token Decoding**: Decodes the JWT using the configured signing key (`SB_JWT_SIGNING_KEY` in production, Django's `SECRET_KEY` in development)
2. **User Validation**: Queries the database for a user matching the token's `user_id` who is both `is_active=True` and `is_deleted=False` — this means deactivated or soft-deleted accounts are immediately rejected even with a valid token
3. **Async Operation**: The `authenticate` method is `async def`, compatible with Daphne's ASGI event loop, and uses `afirst()` for non-blocking database access
4. **User Attachment**: On success, sets `request.user` so that downstream controllers, permissions, and middleware can access the authenticated user
5. **Silent Failure**: Returns `None` on any error (expired token, invalid signature, user not found), which causes django-ninja to return a 401 Unauthorized response

### Login Flow

The `POST /api/v1/auth/login` endpoint handles user authentication:

1. **Rate Limiting (AUTH-3)**: Two independent rate limit checks are applied — per-IP (10 attempts per 15 minutes) and per-email (10 attempts per 15 minutes per email address). The per-email check prevents attackers from bypassing IP-based rate limits by rotating through proxy networks while targeting a specific account.
2. **Account Lock Check (CRIT-02)**: `AuthService.aauthenticate_user()` checks if the account is locked (`is_account_locked()`) before attempting password verification. If locked, authentication fails immediately.
3. **Password Verification**: Uses Django's `check_password()` to verify the provided password against the stored hash.
4. **Failed Attempt Tracking (CRIT-02)**: On incorrect password, `increment_failed_login()` is called. After 5 consecutive failures, the account is locked for 30 minutes.
5. **Successful Login**: On correct password, `reset_failed_login_attempts()` clears any previous failure count, and login history is recorded (`ip_address`, `user_agent`).
6. **Token Generation**: An access token and refresh token are generated using `AccessToken.for_user()` and `RefreshToken.for_user()` respectively, wrapped in `@sync_to_async` for safe use from async endpoints.
7. **Cookie Setting (HIGH-03)**: The refresh token is set in an httpOnly cookie via `_set_auth_cookie()`. The access token is returned in the JSON response body. The refresh token is **never** returned in the response body (AUTH-1 fix), preventing XSS from stealing it.

### Registration Flow

The `POST /api/v1/auth/register` endpoint creates a new user account:

1. **Rate Limiting**: 5 registrations per hour per IP
2. **User Creation**: `AuthService.aregister_user()` creates the user with `is_active=False` and `is_email_verified=False` — the account cannot be used until email verification is completed
3. **Automatic OTP**: After successful registration, an email verification OTP is automatically sent to the provided email address
4. **Password Validation**: The Pydantic schema enforces password strength (uppercase, lowercase, digit, special character, minimum 8 characters)

### SSO Authorization Code Flow

SattaBase supports cross-domain single sign-on for sister domains using an authorization code flow:

1. **Authorization Code Generation** (`POST /api/v1/auth/authorize`): An authenticated user (with a valid JWT) requests an authorization code. The code is one-time-use, expires in 30 seconds, and is stored in Redis. This is called by the sister domain's frontend when redirecting the user to SattaBase.

2. **Token Exchange** (`POST /api/v1/auth/token/exchange`): The SattaBase callback page exchanges the authorization code for a JWT access token (in the response body) and a refresh token (in an httpOnly cookie). The code is consumed upon use and cannot be replayed. Rate limited to 10 exchanges per minute (CRIT-06 fix).

This flow enables a seamless experience where a user logged into a sister domain can access SattaBase without re-entering credentials.

## 4.2 Cookie-Based Token Refresh

The cookie-based token refresh system is the primary mechanism for maintaining user sessions in browser clients. It was designed with multiple security fixes to prevent XSS, CSRF, and token theft attacks.

### Cookie Configuration

Auth cookies use environment-adaptive settings determined by `_get_cookie_settings()`:

| Setting | Development (DEBUG=True) | Production (DEBUG=False) |
|---|---|---|
| **Secure** | `False` | `True` |
| **SameSite** | `Lax` | `None` |
| **httpOnly** | `True` | `True` |
| **Path** | `/` | `/` |

**Why SameSite=Lax works in development**: The SameSite algorithm checks the "site" (scheme + registrable domain). `http://localhost:4321` and `http://localhost:8086` share the same site (`http` + `localhost`), so Lax cookies are sent on `fetch()` POST requests between them. In production, the frontend and API are on different domains, requiring `SameSite=None` (which mandates `Secure=True` per browser spec).

### Cookie Names

| Cookie | httpOnly | Purpose |
|---|---|---|
| `sb_refresh_token` | Yes | Contains the JWT refresh token — inaccessible to JavaScript |
| `sb_remember_me` | No | Flag indicating persistent session — readable by frontend |

### Refresh Endpoint: `POST /api/v1/auth/token/refresh-cookie`

This is the preferred refresh endpoint for browser clients. The flow is:

1. **Read cookie**: Extract `sb_refresh_token` from the request cookies
2. **Validate token**: Decode the refresh token to extract `user_id`, verify the user is active and not deleted
3. **Generate new access token**: `AccessToken.for_user(user)`
4. **Rotate refresh token**: Generate a new refresh token with a fresh expiry (important for "Remember Me" — without rotation, the JWT expires after its configured lifetime even though the cookie persists for 30 days)
5. **Set new cookie**: The new refresh token replaces the old cookie value
6. **Return access token**: Only the access token is returned in the JSON response body

### Token Rotation Strategy (Critical Design Decision)

The cookie-based refresh endpoint **does NOT blacklist the old refresh token** on rotation. This is intentional and addresses a specific problem with SPAs using Astro View Transitions:

**The Problem**: Multiple concurrent refresh requests (caused by Astro View Transitions, HMR, or multiple browser tabs) each blacklist the previous token, causing cascading 401 failures. Tab A refreshes and gets a new token, blacklisting the old one. Tab B tries to refresh with the old token, which is now blacklisted, so it fails. Tab B retries and fails again, creating an infinite loop.

**The Solution**: Old refresh tokens naturally expire (TTL configured via `SIMPLE_JWT.REFRESH_TOKEN_LIFETIME`, typically 7 days), providing a grace period during which concurrent tabs can still use the old cookie. The browser replaces the old cookie with the new one as soon as any tab receives the refresh response.

**Security Trade-off**: A stolen refresh token remains valid until it expires naturally (up to 7 days), rather than being invalidated immediately on rotation. This is acceptable because:
1. The cookie is httpOnly — XSS cannot steal it
2. SameSite=Lax/None+Secure provides CSRF resistance
3. Natural expiration (7 days) limits the window
4. Explicit logout DOES blacklist the token immediately
5. The alternative (rotation + blacklist) causes constant auth failures in SPAs with View Transitions

### Token Reuse Detection (AUTH-4 Fix)

If a blacklisted token appears in a cookie-based refresh request, it indicates token theft — the legitimate user already logged out (which blacklists the token), but someone else is still using the old cookie. The system responds with:

1. **Forensic Logging**: Logs user_id, IP address, user agent, and error details at `SECURITY_ALERT` level
2. **Mass token revocation**: Blacklists ALL outstanding refresh tokens for the compromised user, immediately invalidating every active session. This is the one case where the "no blacklist on rotation" rule is broken — a blacklisted token being reused means the legitimate session is already over.
3. **Cookie clearing**: The invalid cookie is removed from the browser

### Body-Based Refresh: `POST /api/v1/auth/token/refresh`

This endpoint is provided for non-browser API clients that cannot use cookies. It reads the refresh token from the request body and returns both a new access token and a new refresh token. Unlike the cookie-based endpoint, this endpoint **does blacklist the old refresh token** (CRIT-01 fix) because API clients typically have a single connection and don't face the concurrent-tab problem.

### Logout: `POST /api/v1/auth/logout`

The logout endpoint is secured against CSRF-based forced-logout attacks (AUTH-2 fix):

1. **Cookie validation**: The endpoint reads the `sb_refresh_token` cookie and validates it. If the cookie is missing or the token is invalid, it returns 401 without blacklisting anything (preventing CSRF attacks that would POST to `/auth/logout` from a malicious site)
2. **Token blacklisting**: If the cookie contains a valid refresh token, it is blacklisted so it cannot be used again
3. **Cookie clearing**: Both `sb_refresh_token` and `sb_remember_me` cookies are cleared with matching Secure/SameSite settings (required for the browser to actually delete the cookie)

### "Remember Me" Behavior

When `remember=True` is passed during login:
- The `sb_refresh_token` cookie gets an explicit `Expires` header set to 30 days from now
- The `sb_remember_me` cookie (readable by JavaScript) is set to `"true"` with the same expiry

When `remember=False`:
- The `sb_refresh_token` cookie is a session cookie (no `Expires` header) — it disappears when the browser closes
- The `sb_remember_me` cookie is cleared (`max_age=0`)

On refresh, the "remember me" state is preserved by checking the `sb_remember_me` cookie value and applying it when setting the new refresh cookie.

## 4.3 API Key Authentication (SDK)

API key authentication provides a second authentication track for server-to-service communication between SattaBase and its sister domains. Unlike JWT auth (which identifies a specific user), API key auth identifies a specific service domain and its credential.

### API Key Format

API keys follow the format `sb_live_<43 random characters>` (50 characters total), generated by `common/utils.py`:

```python
def generate_api_key():
    raw_key = f"sb_live_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:12]  # "sb_live_XXXX"
    sha256_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return (raw_key, prefix, sha256_hash)
```

The raw key is shown **exactly once** when created (in the API response body) and is never stored in the database. Instead, only the SHA-256 hash and the first 12 characters (prefix) are persisted. This means that if the database is compromised, attackers cannot reconstruct the raw keys.

### Validation Pipeline

API key validation happens at two levels: **middleware** (automatic, every request) and **controller** (on-demand, per-endpoint).

#### Middleware Validation (`common/middleware.py`)

The `service_credential_middleware` intercepts every request that includes an `X-API-Key` header:

1. **Header detection**: If `X-API-Key` header is absent, the middleware is a no-op — the request passes through for regular JWT authentication
2. **Prefix check**: Validates the key starts with `sb_live_`. Invalid format immediately returns 403 (when enforcement is on)
3. **Domain header requirement**: Requires `X-Service-Domain` header when `X-API-Key` is present. Missing domain header returns 400
4. **SHA-256 hash lookup**: Computes the hash and queries `ServiceCredential.objects.select_related("service_domain").get(api_key_hash=key_hash)`
5. **Active status checks**: Verifies both the credential (`is_active`) and its domain (`service_domain.is_active`) are active
6. **Domain cross-check**: Verifies the `X-Service-Domain` header value matches the credential's bound domain — this prevents a key from domain A being used with domain B's header (anti-spoofing)
7. **Request attachment**: On success, sets `request.service_credential` and `request.service_domain_from_key`
8. **Last-used tracking**: Atomically updates `last_used_at` and tracks usage analytics in Redis
9. **Enforcement mode**: When `API_KEY_ENFORCED=True`, invalid keys return 403/401 JSON immediately. When `False` (default), invalid keys log warnings but the request continues

The middleware uses Django 5.2's `@sync_and_async_middleware` pattern with separate sync and async validation paths. Under Daphne (ASGI), the async path is used with `aget`/`aupdate` ORM calls to avoid blocking the event loop.

#### Controller-Level Validation (`common/api_key_auth.py`)

The `validate_api_key(request)` function provides controller-level validation for endpoints that need explicit API key checks:

1. **Middleware-aware**: If `request.service_credential` is already set (by middleware), it returns the cached credential immediately without re-querying the database
2. **Identical validation**: Same SHA-256 hash lookup, active status checks, and request attachment as the middleware
3. **Flexible enforcement**: When `API_KEY_ENFORCED=False` (default), missing keys return `None` instead of raising — useful for dual-auth endpoints that accept either JWT or API key
4. **Error responses**: When `API_KEY_ENFORCED=True`, raises `UnauthorizedException` with descriptive messages

### Dual-Auth Endpoints

Endpoints like `GET /api/v1/billing/auth/me` use `IsAuthenticatedOrService` permission, which accepts either:
- A valid JWT (`request.user.is_authenticated == True`)
- A valid API key (`request.service_credential.is_active == True`)

This enables the same endpoint to serve both frontend users (via JWT) and SDK clients (via API key). When an API key is used, the endpoint can return domain-aware data by checking `request.service_domain_from_key`.

### API Key Enforcement Mode

The `API_KEY_ENFORCED` setting (default `False`) controls how aggressively API keys are validated:

| Mode | Valid Key | Invalid Key | Missing Key |
|---|---|---|---|
| **Enforced=False** | ✅ Credential attached | ⚠️ Warning logged, request continues | ⚠️ Debug log, request continues |
| **Enforced=True** | ✅ Credential attached | ❌ 403 JSON response | ❌ 401 JSON response |

The default non-enforced mode allows gradual SDK adoption — existing endpoints continue working while SDK clients add API key headers. Once all sister domains are onboarded, enforcement can be enabled for strict security.

## 4.4 Permission Classes

SattaBase defines six permission classes in `common/permissions.py`, all extending `ninja_extra.permissions.BasePermission`:

### IsAuthenticated
The most commonly used permission. Checks `request.user` exists and `is_authenticated` is True. Applied to all user-facing protected endpoints (billing, profile, settings).

### IsAdmin
Checks `request.user.is_staff` in addition to authentication. Used for all admin panel endpoints. The `is_staff` flag is synced with the user's `role` field via signals and the `admin_user_controller` — when a user's role is set to "owner" or "admin", `is_staff` is automatically set to `True`.

### IsVerified
Checks `request.user.is_email_verified` in addition to authentication. Used as a guard for sensitive billing mutations (checkout, plan change, credit request) via the `require_verified_email()` helper. This ensures that unverified users cannot perform financial operations.

### IsSelfOrAdmin
Object-level permission that allows access if the requesting user is the object owner (`obj.user == request.user`) or an admin (`is_staff`). Checks the `user` or `owner` attribute on the target object. Used for endpoints where users should only access their own resources, but admins can access anyone's.

### IsServiceAuthenticated
Checks `request.service_credential` exists and `is_active`. Used for endpoints that are exclusively for SDK/service-to-service communication — no JWT user access.

### IsAuthenticatedOrService
The dual-auth permission. Returns `True` if either JWT authentication (`request.user.is_authenticated`) or API key authentication (`request.service_credential.is_active`) succeeds. This is the primary permission for shared endpoints that serve both frontend users and SDK clients.

**Permission application pattern**: Permissions are declared at the controller class level and can be overridden at the method level. For example:

```python
@api_controller("/billing", auth=JWTAuth(), permissions=[IsAuthenticated])
class BillingProtectedController:
    # All methods require IsAuthenticated by default
    
    @http_get("/auth/me", permissions=[IsAuthenticatedOrService])
    async def auth_me(self, request):
        # This specific method accepts both JWT and API key
```

## 4.5 Rate Limiting

SattaBase implements a sliding-window rate limiting system using Django's cache backend (Redis in production) via `common/rate_limit.py`.

### Sliding Window Algorithm

The `check_rate_limit(key, max_attempts, window_seconds)` function implements a precise sliding window:

1. Retrieves a list of timestamps from cache under `rl:{key}`
2. Prunes timestamps older than `window_seconds`
3. If the remaining count >= `max_attempts`, returns `False` (rate limited)
4. Otherwise, appends the current timestamp and returns `True`

This approach provides smooth rate limiting without the "boundary burst" problem of fixed-window algorithms.

### Rate Limit Key Construction

The `check_rate_limit_or_raise(request, key_prefix, ...)` function builds composite rate limit keys:

**Browser traffic** (no API key): `{key_prefix}:{user_id}:{client_ip}`
- Example: `login:42:192.168.1.100`

**SDK traffic** (with API key): `{key_prefix}:{user_id}:sdk:{api_key_prefix}`
- Example: `cancel_sub:42:sdk:sb_live_XXXX`

This separation ensures that SDK traffic from a sister domain backend (which proxies many users through a single IP) doesn't exhaust the per-IP rate limit bucket for all users on that domain.

### SDK Rate Limit Parameters

When a valid `service_credential` is attached to the request, rate limits automatically switch to SDK-friendly defaults:

| Parameter | Browser Default | SDK Default |
|---|---|---|
| **Max attempts** | 5 (configurable per action) | 1000 |
| **Window** | 3600 seconds (1 hour) | 3600 seconds (1 hour) |

SDK clients get significantly higher limits because they represent server-to-server traffic that naturally has higher volume (e.g., a sister domain checking subscription status for every page load).

### Configured Rate Limits

| Action | Key Prefix | Max Attempts | Window | Notes |
|---|---|---|---|---|
| Login | `login` | 10 | 15 min | Per-IP |
| Login per email | `login_email:{email}` | 10 | 15 min | Per-email (AUTH-3 fix) |
| Register | `register` | 5 | 1 hour | Per-IP |
| Password reset request | `pwreset_req` | 5 | 1 hour | Per-IP |
| Password reset confirm | `pwreset_confirm:{email}` | 5 | 1 hour | Per-email (MED-03 fix) |
| Email verify request | `email_verify_req:{email}` | 3 | 1 hour | Per-email (MED-16 fix) |
| Email verify confirm | `email_verify_confirm` | 10 | 5 min | Per-IP |
| Token exchange | `token_exchange` | 10 | 1 min | Per-IP (CRIT-06 fix) |
| Change password | `change_password` | 5 | 1 hour | Per-IP |
| Confirm identity | `confirm_identity` | 10 | 1 hour | Per-IP |
| Email change | `email_change` | 5 | 1 hour | Per-IP |
| Account deletion | `delete_account` | 3 | 1 hour | Per-IP |
| Admin write operations | Various | Configurable | Configurable | Per-admin + IP |

### Client IP Extraction

The `get_client_ip(request)` function (MED-02 fix) only trusts the `X-Forwarded-For` header when the immediate connecting IP (`REMOTE_ADDR`) is a known trusted proxy. Trusted proxies are configured via `settings.TRUSTED_PROXIES` as a list of IP addresses or CIDR ranges (e.g., `["127.0.0.1", "10.0.0.0/8"]`), defaulting to loopback only. This prevents clients from spoofing the header to bypass rate limiting.

## 4.6 Account Security (Lockout, Deletion)

### Account Lockout (CRIT-02)

The User model includes brute-force protection fields:

| Field | Type | Purpose |
|---|---|---|
| `failed_login_attempts` | PositiveIntegerField | Count of consecutive failed login attempts |
| `locked_until` | DateTimeField | If set, account is temporarily locked until this time |

**Lockout behavior**:
- `increment_failed_login(max_attempts=5, lockout_minutes=30)`: Increments the counter. When it reaches 5 (default), sets `locked_until` to 30 minutes from now and logs a warning
- `is_account_locked()`: Returns `True` if `locked_until` is set and in the future
- `reset_failed_login_attempts()`: Clears both the counter and `locked_until` — called on successful login

The lockout is enforced by `AuthService.aauthenticate_user()` before password verification. A locked account receives the same "Invalid credentials" error as a wrong password, preventing attackers from distinguishing between wrong passwords and locked accounts.

### Soft Delete

The User model extends `SoftDeleteModel`, which provides:

| Field | Type | Purpose |
|---|---|---|
| `is_deleted` | BooleanField | Whether the account has been soft-deleted |
| `deleted_at` | DateTimeField | When the deletion occurred |

**Deletion behavior**:
- `soft_delete()`: Sets `is_deleted=True` and `deleted_at=now()`. The record remains in the database but is excluded from all queries via the `SoftDeleteModel` queryset
- `restore()`: Clears both `is_deleted` and `deleted_at`
- The `JWTAuth.authenticate()` method filters on `is_deleted=False`, so soft-deleted users cannot authenticate even with a valid token
- The `CustomUserManager.get_by_natural_key()` also filters on `is_deleted=False`, preventing Django's auth backend from authenticating soft-deleted users

### Account Lifecycle States

| State | `is_active` | `is_deleted` | `is_email_verified` | Can Login? | Can Use API? |
|---|---|---|---|---|---|
| **New (unverified)** | `False` | `False` | `False` | No | No |
| **Verified** | `True` | `False` | `True` | Yes | Yes |
| **Admin-deactivated** | `False` | `False` | — | No | No (401) |
| **Soft-deleted** | — | `True` | — | No | No (401) |
| **Locked** | `True` | `False` | `True` | No (30 min) | No (until unlock) |

The three distinct "cannot authenticate" responses help API consumers handle each case:
- `AccountNotActiveException` (403): Email not verified — prompt user to verify
- `AccountInactiveException` (401): Admin deactivated — force logout, show support message
- `AccountDeletedException` (401): User deleted — force logout, permanent state

### User Manager Security Features

The `CustomUserManager` enforces security at the data layer:

- `create_user()`: Sets `is_active=False` and `is_email_verified=False` by default — new accounts cannot be used until email verification
- `create_superuser()`: Sets `is_active=True`, `is_email_verified=True`, and `role="owner"` — superusers bypass verification
- `get_by_natural_key()`: Filters on `is_deleted=False` AND `is_active=True` (MED-05 fix) — prevents authentication of deactivated or deleted accounts even at the Django auth backend level

## 4.7 Frontend Auth Flow (End-to-End)

This section traces the complete authentication lifecycle from a frontend perspective, showing how all the pieces described in Sections 4.1-4.6 work together.

### Full Login Sequence

```
User          LoginForm.vue        api.ts           AuthController        Database
  │                │                  │                  │                   │
  │  Email/Pass    │                  │                  │                   │
  │──────────────→ │                  │                  │                   │
  │                │  login()         │                  │                   │
  │                │─────────────────→│                  │                   │
  │                │                  │  POST /auth/login│                   │
  │                │                  │─────────────────→│                   │
  │                │                  │                  │  Rate limit check │
  │                │                  │                  │  Account lock?    │
  │                │                  │                  │  Password check   │
  │                │                  │                  │──────────────────→│
  │                │                  │                  │  ← User record    │
  │                │                  │                  │                   │
  │                │                  │                  │  Reset failed     │
  │                │                  │                  │  login attempts   │
  │                │                  │                  │  Record login IP  │
  │                │                  │                  │  Generate tokens  │
  │                │                  │                  │  Set httpOnly     │
  │                │                  │                  │  cookie           │
  │                │                  │  200 + access    │                   │
  │                │                  │  token (cookie   │                   │
  │                │                  │  set by browser) │                   │
  │                │←─────────────────│                  │                   │
  │                │  Store access    │                  │                   │
  │                │  token in window │                  │                   │
  │                │  .__sb_auth      │                  │                   │
  │                │  Fetch user data │                  │                   │
  │                │  Navigate to     │                  │                   │
  │                │  /dashboard      │                  │                   │
  │  Dashboard     │                  │                  │                   │
  │←───────────────│                  │                  │                   │
```

### Subsequent API Requests

After login, every API request follows this flow in `api.ts`:

1. **Wait for init**: `waitForInit()` ensures the auth system has completed initialization (cookie-based refresh if needed)
2. **Proactive refresh check**: If the access token expires within 5 minutes, `api.ts` proactively refreshes it before making the request
3. **Authorization header**: `Authorization: Bearer <access_token>` is added to every request
4. **Cache control**: GET requests use browser caching (5-second TTL); mutations use `cache: "no-store"`
5. **401 handling**: If the response is 401, `api.ts` attempts a cookie-based refresh and retries the request once
6. **Session expiry**: If the refresh also fails, `api.ts` emits `auth:session-expired`, which `SessionGuard.vue` catches and redirects to login

### Page Navigation with View Transitions

When the user navigates between pages using Astro's View Transitions:

1. **`astro:before-preparation`**: `api.ts` checks if the session is expired. If expired, cancels the transition and sets `__sb_redirect_reason` on window
2. **Module re-evaluation**: Astro may re-evaluate JavaScript modules during View Transitions. The window-level shared state pattern (`window.__sb_auth_composable`) ensures auth state persists across re-evaluations
3. **`astro:page-load`**: `api.ts` reschedules the proactive refresh timer. `SessionGuard.vue` checks for `__sb_redirect_reason` and performs any pending redirects
4. **Cookie auto-refresh**: The `sb_refresh_token` cookie is automatically sent with the page request (because `credentials: include` is set). The Astro server middleware validates it via `POST /auth/token/refresh-cookie`

### Session Expiry Detection (Three Layers)

The system uses three independent layers to detect session expiry, each catching edge cases the others might miss:

**Layer 1 — Astro Server Middleware** (`src/middleware.ts`):
- Runs on every server-side page request
- Validates the `sb_refresh_token` cookie by calling `POST /api/v1/auth/token/refresh-cookie`
- If invalid: 302 redirect to `/auth/login?redirect=<path>` before the page even renders
- Catches: Expired cookies, blacklisted tokens, server-side session validation

**Layer 2 — SessionGuard Vue Component** (`SessionGuard.vue`):
- Runs client-side in the browser
- Watches `isLoggedIn` computed property from `useAuth()` — when it transitions from `true` to `false`, schedules redirect
- Listens for `auth:session-expired` and `sb:auth:session-expired` events
- Runs a 15-second periodic check: verifies access token exists on protected pages
- Catches: API 401 responses, token deletion, module re-evaluation state loss

**Layer 3 — API Client** (`lib/api.ts`):
- Runs on every API request
- Proactive refresh: schedules token refresh 5 minutes before expiry
- 401 → refresh → retry: automatically attempts refresh on any 401
- Cancels View Transitions when session is expired
- Catches: Expired access tokens, network issues, concurrent request failures

### SSO Cross-Domain Flow

When a user on a sister domain needs to access SattaBase:

1. **Sister domain frontend** calls SattaBase `POST /api/v1/auth/authorize` with the user's JWT (from the sister domain's session) → receives a one-time authorization code
2. **Sister domain** redirects the user to `https://sattabase.com/auth/callback?code=<auth_code>`
3. **SattaBase callback page** (`AuthCallbackHandler.vue`) calls `POST /api/v1/auth/token/exchange` with the code → receives access token + httpOnly refresh cookie
4. **User is now authenticated** on SattaBase without re-entering credentials
5. The authorization code is consumed and cannot be reused

---

# 5. Subscription & Billing System

The subscription and billing system is the commercial heart of SattaBase. It manages the entire lifecycle of paid access — from product and plan definition through Stripe checkout, ongoing subscription management, plan changes with proration, payment failure recovery via dunning, revenue recognition under ASC 606, refund processing with a two-person approval rule, and multi-currency price conversion. Every mutation follows the "Stripe first, DB second" pattern described in Section 1.3, and the local database is treated as a read-optimized cache that is ultimately reconciled by Stripe webhooks.

## 5.1 Product, Plan, and Subscription Hierarchy

SattaBase uses a three-level hierarchy to model commercial offerings: **Product** at the top, **Plan** as a tier within a product, and **Subscription** as the join between a user and a plan. This hierarchy is deliberately simple — there are no add-ons, bundles, or usage-based components in the current architecture.

**Product** represents a logical service (e.g., "Satta Finance", "Satta Analytics"). Each product has a unique slug used in URLs, an optional Stripe product ID (created lazily on first checkout), and a relationship to one or more `ServiceDomain` entries that identify the web domains serving the product. A product's `is_active` flag controls whether it appears in public listings and is available for new subscriptions. The model enforces a unique constraint on non-null `stripe_product_id` values while allowing multiple NULL entries (for products that have never been purchased via Stripe). The `save()` method normalizes empty strings to NULL to maintain this constraint correctly (MED-21 fix).

**Plan** defines a pricing tier within a product. Plans are characterized by their `price_cents` (stored as an integer in the smallest currency unit), `currency` (ISO 4217 code, defaulting to USD), `billing_cycle` (monthly, yearly, or lifetime), and `trial_days`. Free plans have `price_cents = 0` and no `stripe_price_id` — they are instantiated directly without Stripe involvement. Each plan has a `features` JSONField for public display (e.g., `{"reports": "Advanced", "storage": "10GB"}`) and an `AccessEntry` set for programmatic feature gating used by the auth/me endpoint. The `tax_inclusive` boolean determines whether Stripe should use `inclusive` or `exclusive` tax behavior at checkout. Plans are ordered by `sort_order` and then `price_cents` when displayed to users.

**AccessEntry** provides the feature gating mechanism. Each entry is a key-value pair bound to a plan, where the `value_type` (string, boolean, or integer) determines how the value is cast when returned via the auth/me access map. For example, a Standard plan might have entries like `{"key": "reports", "value": "true", "value_type": "boolean"}` and `{"key": "max_accounts", "value": "5", "value_type": "integer"}`. The unique constraint on `(plan, key)` prevents duplicate feature definitions. The `typed_value` property handles casting, and the `as_dict()` method produces the format used in API responses.

**Subscription** is the central model that binds a user to a plan for a specific product. The unique constraint `(user, product)` ensures a user can have only one subscription per product — plan changes are handled within the same subscription record, not by creating new ones. The subscription tracks Stripe identifiers (`stripe_subscription_id`, `stripe_customer_id`), billing period boundaries (`current_period_start`, `current_period_end`), trial state (`trial_start`, `trial_end`, `has_used_trial`), cancellation state (`canceled_at`, `cancel_at_period_end`), dunning state (`dunning_step`, `past_due_at`, `last_dunning_email_at`), and the billing currency denormalized from the user's profile at checkout time. The `is_effectively_active()` method determines whether a subscription grants access — it returns True for active, trialing, past_due, and canceled (within period) statuses, but only if the current period has not ended. This is the method that sister domains should rely on when checking access via auth/me.

The subscription model also provides convenience methods: `schedule_cancellation()` sets the status to canceled with `cancel_at_period_end=True`, `reactivate()` restores either trialing or active status depending on whether the trial is still ongoing, and `change_plan(new_plan)` swaps the plan reference after validating that the new plan belongs to the same product (HIGH-15).

## 5.2 Stripe Integration (Checkout, Portal, Webhooks)

SattaBase's Stripe integration is organized as a clean package under `billing/stripe/` with a single public interface exposed through `billing/stripe/__init__.py`. Controllers and tasks import exclusively from this package-level module — never from submodules directly. This separation isolates the rest of the codebase from Stripe SDK changes and provides a single place to audit all Stripe interactions.

**Checkout Flow** (`billing/stripe/checkout.py`): The `create_checkout()` function orchestrates the subscription purchase flow. It validates that the plan is not free (free plans use the change-plan mechanism instead), checks that Stripe Tax is enabled (blocking checkout if tax collection is not configured), resolves the Stripe price ID for the requested currency using `resolve_price_id()`, gets or creates a Stripe customer ID, and creates a Checkout session in `subscription` mode. The session includes automatic tax, Terms of Service consent collection, promotion code support, and metadata carrying `user_id`, `product_slug`, `plan_slug`, and `tos_version`. A deduplication mechanism (CMP-07) caches the checkout URL for 5 minutes per user+product+plan combination to prevent duplicate sessions from rapid button clicks. Return URLs are validated against registered `ServiceDomain` entries to prevent open redirect attacks.

The `confirm_checkout()` function is called when the frontend receives the `{CHECKOUT_SESSION_ID}` after a successful payment. It retrieves the session from Stripe, validates that `payment_status` is `paid`, checks user ownership via metadata, and then syncs the subscription from Stripe using `sync_subscription_from_stripe()`. This runs inside `transaction.atomic()` with `select_for_update()` to prevent race conditions. It also handles the edge case where a user already has a free subscription for the product — it upgrades the existing record rather than creating a duplicate.

**Customer Portal** (`billing/stripe/portal.py`): The `create_portal()` function creates a Stripe Customer Portal session that allows users to self-manage their payment methods, view invoices, and cancel subscriptions. It validates the return URL against registered domains (PT-01), appends a `portal=success` query parameter so the frontend can display a confirmation toast (UX-04), and optionally uses a pre-configured portal configuration from `STRIPE_PORTAL_CONFIGURATION` settings (CMP-08).

**Stripe Package Architecture**: The package is structured as follows:
- `client.py` — Low-level Stripe API wrappers (retrieve_subscription, modify_subscription, create_refund, etc.) that return plain dicts instead of Stripe SDK objects
- `customer.py` — Customer CRUD: `get_or_create_customer_id()`, `sync_customer_to_local()`, `find_customer_id()`
- `prices.py` — `resolve_price_id()` maps a Plan + currency to the correct Stripe Price ID
- `gdpr.py` — `delete_or_anonymize_customer()` for GDPR compliance, `export_user_billing_data()` for data portability
- `webhooks/` — Signature verification, event routing, and per-type handlers (covered in Section 5.3)

The `__init__.py` also exposes higher-level orchestration functions: `cancel_subscription_on_stripe()` sets `cancel_at_period_end=True`, `update_subscription_plan_on_stripe()` swaps the subscription's price item, `reactivate_subscription_on_stripe()` removes the cancellation flag and swaps the price, `get_proration_preview()` retrieves an upcoming invoice preview for plan changes, `create_stripe_refund()` initiates a refund (covered in Section 5.7), and `get_transaction_history()` merges Stripe invoices with local credit invoices.

## 5.3 Webhook Event Processing

Stripe webhooks serve as the safety net that reconciles the local database with Stripe's source of truth. While the primary activation path is always the controller acting after Stripe confirmation (Stripe-first pattern), webhooks handle edge cases: delayed Stripe events, manual changes made in the Stripe Dashboard, and automatic subscription lifecycle transitions (renewals, trial endings, payment retries).

**Router** (`billing/stripe/webhooks/router.py`): The entry point for all webhook processing. The `verify_and_parse()` function verifies the Stripe signature using `STRIPE_WEBHOOK_SECRET`. The `record_event()` function creates or retrieves a `WebhookEventLog` entry for audit. The `process_event()` function routes the event to the appropriate handler using the `_EVENT_MAP` dictionary, executing within `transaction.atomic()` and a 25-second timeout guard. On success, the `WebhookEventLog.processed` flag is set to True. On failure, the `error_message` field is populated. The `reconcile_unprocessed()` function retries failed events and is called by the `reconcile_webhooks` Celery task every 6 hours.

**Handled Events** — The system processes 10 Stripe event types:

| Event Type | Handler | Action |
|---|---|---|
| `checkout.session.completed` | `handle_checkout_completed` | Sync subscription from Stripe; cancel any active credit pools for the same user+product |
| `customer.subscription.created` | `handle_subscription_created` | Log creation (sync handles the rest) |
| `customer.subscription.updated` | `handle_subscription_updated` | Call `sync_subscription_from_stripe()` to update local state |
| `customer.subscription.deleted` | `handle_subscription_deleted` | Mark subscription as EXPIRED with `select_for_update()` |
| `invoice.payment_succeeded` | `handle_invoice_payment_succeeded` | Mark past_due as active, reset dunning, upsert Invoice + line items, fetch Stripe fee, create revenue recognition entry |
| `invoice.payment_failed` | `handle_invoice_payment_failed` | Mark subscription as past_due, set `past_due_at` on first transition, reset dunning step, upsert Invoice |
| `customer.subscription.trial_will_end` | `handle_trial_will_end` | Log trial ending notification |
| `charge.refunded` | `handle_charge_refunded` | Create local Refund record, resolve subscription via charge→payment_intent→invoice chain (CH-01 fix) |
| `customer.updated` | `handle_customer_updated` | Sync email, name, and currency from Stripe to local user |
| `invoice.created` | `handle_invoice_created` | Create local Invoice record for audit trail |

**Invoice Upsert Logic** (`_upsert_invoice()`): Invoice records are created or updated using `update_or_create()` on `stripe_invoice_id`. The handler computes discount totals from both fixed-amount and percentage-based coupons, populates all financial fields, and calls `_sync_invoice_line_items()` to create structured `InvoiceLineItem` records from the Stripe invoice's line data (FIN-01 fix). Line items are cleared and recreated on each upsert since Stripe line items are immutable.

**Payment Success Side Effects**: When `invoice.payment_succeeded` fires for a past_due subscription, the handler performs several critical operations: it transitions the status to active, resets the dunning step and `last_dunning_email_at` to zero, updates billing period boundaries, persists the invoice with line items, fetches the Stripe processing fee from the BalanceTransaction API, and creates an immediate `RevenueRecognitionEntry` for the payment date (FIN-07). This webhook-sourced revenue entry covers the payment day itself, while the scheduled Celery task handles the remaining days.

**Subscription Sync** (`billing/stripe/webhooks/sync.py`): The `sync_subscription_from_stripe()` function is the single source of truth for updating the local subscription record from Stripe data. It retrieves the Stripe subscription, updates all fields (status, period boundaries, trial dates, cancellation flags, plan reference via price→Plan lookup), and saves. Both `confirm_checkout()` and `handle_subscription_updated()` delegate to this function, ensuring consistent state regardless of the activation path.

## 5.4 Safe Plan Change Flow

Plan changes are one of the most financially sensitive operations in the system. An incorrectly executed plan change could result in double-charging, free upgrades, or unexpected proration amounts. SattaBase implements a two-step "preview then confirm" flow with HMAC-signed preview tokens to ensure the user sees exactly what they will be charged before confirming.

**Deprecated Direct Change**: The `POST /billing/subscriptions/{product_slug}/change-plan` endpoint still exists for backward compatibility but now blocks paid-to-paid plan changes. It only allows paid-to-free transitions (which cancel at period end). Attempting a paid-to-paid change returns a 400 error directing the caller to the safe preview→confirm flow.

**Preview Step** (`POST /billing/subscriptions/{product_slug}/preview-plan-change`): The controller validates that the user has an active subscription, the target plan exists and belongs to the same product, and the plan is different from the current one. It then calls `get_proration_preview()` on Stripe, which returns an upcoming invoice preview showing the proration credit for the old plan and the charge for the new plan. The controller also classifies the change type (upgrade, downgrade, or lateral) using `classify_plan_change()`, which compares prices in the same currency. A preview token is generated via `generate_preview_token()`, which creates an HMAC-SHA256 signature binding together `user_id`, `subscription_id`, `plan_slug`, `total_cents`, `currency`, and a timestamp. This token has a 10-minute TTL.

**Confirm Step** (`POST /billing/subscriptions/{product_slug}/confirm-plan-change`): The controller validates the preview token, checks that it has not expired (with a +/-1 cent tolerance for Stripe rounding drift, CTR-04 fix), and then calls `execute_safe_plan_change()`. This function implements different payment gating strategies based on the change type:

- **Upgrade** (higher price): A PaymentIntent is created and confirmed for the proration amount *before* the subscription is modified. This ensures the customer can pay before granting access to the higher tier. The PaymentIntent uses a deterministic idempotency key (`plan-change-{sub.id}-{new_plan_slug}-{price_id}`) so retries are idempotent (STP-04 fix). Only after payment succeeds does the subscription get modified with `proration_behavior="create_prorations"` for immediate effect.
- **Downgrade/Lateral** (same or lower price): The subscription is modified with `proration_behavior="none"`, meaning the change takes effect at the next billing cycle. No immediate charge is created. This prevents giving proration credits for downgrades that could be exploited.

The preview token system prevents several attack vectors: a user cannot change the target plan after previewing (the token is bound to `plan_slug`), cannot change the amount (bound to `total_cents`), cannot replay a token from a different session (bound to `user_id` and `subscription_id`), and cannot use a stale quote (10-minute TTL).

## 5.5 Dunning Workflow

When a subscription payment fails, Stripe automatically retries according to its smart retry schedule. SattaBase augments this with a staged dunning workflow that progressively escalates from friendly reminders to automatic cancellation, implemented in `billing/tasks.py` and driven by the `dunning_retry` Celery task (runs daily).

**Dunning Steps Configuration**: The `DUNNING_STEPS` constant defines four escalation stages:

| Step | Days Past Due | Action | Description |
|---|---|---|---|
| 1 | 3 | `email_reminder` | Friendly reminder to update payment method |
| 2 | 5 | `email_urgent` | Urgent notice with 2-day suspension warning |
| 3 | 7 | `restrict_access` | Flag subscription for access restriction (no email) |
| 4 | 14 | `cancel_subscription` | Auto-cancel on Stripe and locally |

Each step fires only if `dunning_step < step_number`, preventing duplicate actions. Steps are cumulative — a subscription at day 5 will trigger both step 1 and step 2 actions in the same task run.

**Email Throttling**: The `DUNNING_EMAIL_MIN_INTERVAL_HOURS = 24` constant prevents spamming users with multiple dunning emails in a single day. Before sending, the handler checks `last_dunning_email_at` and skips if the minimum interval has not elapsed.

**Days Past Due Calculation** (MED-04 fix): The number of days past due is calculated from `past_due_at` (set once when the subscription first transitions to PAST_DUE) rather than `updated_at`, which advances on every save operation including dunning task writes. Using `updated_at` would artificially keep `days_past_due` low and delay escalation.

**Step Execution**: The `_execute_dunning_step()` function dispatches to the appropriate action. Email steps call `_send_dunning_email()`, which formats a template with the user's name, plan, product, and a portal link. The `restrict_access` step logs a warning — actual access restriction is handled by the `is_effectively_active()` check on the subscription model (past_due subscriptions return False after `current_period_end`). The `cancel_subscription` step calls `cancel_subscription_on_stripe()` and updates the local status. Critically, if the Stripe cancel call fails, the function returns False and the dunning step is NOT advanced (MED-04/HIGH-02 fix), ensuring the system retries the cancellation on the next daily run rather than skipping to a later step.

**Recovery**: When a payment succeeds (via `invoice.payment_succeeded` webhook), the handler resets `dunning_step` to 0 and clears `last_dunning_email_at`, allowing the dunning workflow to start fresh if the subscription goes past_due again in the future.

## 5.6 Revenue Recognition (ASC 606)

SattaBase implements ASC 606-compliant daily revenue recognition through the `RevenueRecognitionEntry` model and the `recognize_revenue` Celery task. Under ASC 606, revenue for subscription services should be recognized over the service period rather than all at once at billing time. This means a $30/month subscription generates approximately $1/day in recognized revenue.

**Model**: Each `RevenueRecognitionEntry` represents revenue recognized for one subscription on one day. The `UniqueConstraint` on `(subscription, recognized_date)` prevents duplicate entries. The `source` field distinguishes between `scheduled` (from the daily Celery task) and `webhook` (from the invoice.payment_succeeded handler). Other fields track the plan, amount in cents, currency, billing period boundaries, and the Stripe invoice ID for reconciliation.

**Celery Task** (`recognize_revenue` in `billing/tasks.py`): Runs daily and processes the previous day's date by default. It queries all subscriptions that are active, trialing, or canceled (but not past_due — MED-05 fix) with `plan.price_cents > 0` where the recognized date falls within the billing period. For each subscription, the daily revenue is calculated as `math.ceil(plan.price_cents / total_days_in_period)`. On the last day of the period, the amount is adjusted to capture any remaining cents lost to ceiling rounding on prior days, with a `max(0, ...)` guard against negative values when `price_cents < total_days` (CRIT-02 fix). Lifetime plans are excluded from the scheduled task — their revenue is recognized entirely on the payment day via the webhook handler.

**Webhook Revenue Entry**: The `handle_invoice_payment_succeeded` handler creates an immediate revenue entry (source=`webhook`) for the payment date. This ensures revenue is never missed if the Celery task fails or is delayed — the daily task uses `ignore_conflicts=True` on bulk_create to skip dates that already have entries from the webhook. The dual-source approach provides both reliability (webhook catches payment day) and completeness (scheduled task catches remaining days).

**Past Due Exclusion**: Subscriptions in `PAST_DUE` status are explicitly excluded from revenue recognition. Under ASC 606, revenue should only be recognized when it is probable that payment will be collected. Including past_due subscriptions would overstate revenue. When a past_due subscription recovers (payment succeeds), the webhook handler creates a retroactive entry for that day, and the daily task will catch any missed days going forward.

## 5.7 Refund System (Two-Person Rule)

Refund processing in SattaBase implements a financial control framework designed for PCI-DSS compliance (CMP-02) and fraud prevention. The core principle is that no single admin can both initiate and approve a refund — a "two-person rule" separates these responsibilities.

**Initiating a Refund**: The `POST /admin/subscriptions/{id}/refund` endpoint (in `AdminSubscriptionController`) accepts a `RefundInputSchema` with `amount_cents` (optional, defaults to full refund), `reason`, `reason_category` (structured codes: customer_request, billing_error, goodwill, policy, chargeback), and `admin_notes`. The controller validates that the subscription has a Stripe subscription ID (free plans cannot be refunded), then calls `create_stripe_refund()`. This function determines the payment intent to refund (either a specific charge ID provided or the latest invoice's payment), validates that the refund amount does not exceed the chargeable amount (FIN-03 cap), creates the refund via Stripe with a deterministic idempotency key (`refund-{sub.id}-{payment_intent_id}-{amount_cents or 'full'}`, STP-03 fix), and creates a local `Refund` record. The initiator's IP address is captured for the audit trail (CMP-02).

**Two-Person Rule**: The refund is created with `status='pending'` and must be approved by a different admin before it is considered complete. The `initiated_by` and `approved_by` fields are separate FK references to User, and the system enforces that they are different users. This prevents a single admin from creating and approving their own refund, which is a standard financial control for preventing fraud. The `initiated_by_ip` field provides an additional audit trail for forensic analysis.

**Stripe-Initiated Refunds**: When a refund is initiated through the Stripe Dashboard (rather than through SattaBase), the `charge.refunded` webhook fires and the `handle_charge_refunded()` handler creates a local Refund record with `initiated_by=None`. The handler resolves the correct subscription by tracing the chain: charge → payment_intent → invoice → subscription_details (CH-01 fix), which replaced a previous broken `.first()` query that could return an arbitrary subscription from the database.

**Refund Amount Capping** (FIN-03): The `create_stripe_refund()` function validates that the requested amount does not exceed the actual amount paid on the charge or invoice. This prevents over-refunding, which could occur if an admin manually enters an amount larger than the payment. When no specific amount is provided, the full payment amount is refunded.

**Audit Trail**: Every refund carries the full Stripe response in the `stripe_response` JSONField, the `reason_category` for structured reporting, the `initiated_by_ip` for compliance, and the `admin_notes` for internal context. The `subscription` FK uses `SET_NULL` on delete (HIGH-17) so that refund records survive subscription deletion, preserving the financial audit trail.

## 5.8 Multi-Currency Support

SattaBase supports displaying plan prices in the user's preferred currency, which is particularly important for users in regions where international card payments are common but local currency display is expected (e.g., Bangladesh, India, Pakistan). The multi-currency system is implemented in `billing/currency_service.py` and operates on a "store once, convert on read" principle — all prices are stored in the plan's base currency (typically USD), and conversion happens at display time.

**Currency Metadata**: The `CURRENCY_META` dictionary is the single source of truth for 36 supported currencies, providing the display symbol, human-readable name, and number of decimal digits for each. Zero-decimal currencies (JPY, KRW, VND, CLP) have `decimal_digits: 0`, which means amounts are in the main unit rather than cents. This metadata is exposed via the `/billing/currencies` endpoint and piggybacked on the `auth/me` response for sister domains, eliminating the need for consumers to hardcode their own symbol maps.

**Exchange Rate Storage**: The `ExchangeRate` model stores rates fetched daily by the `update_exchange_rates` Celery task. Each row maps a `base_currency` → `target_currency` pair to a decimal rate (18 digits precision, 6 decimal places). The unique constraint on `(base_currency, target_currency)` ensures one rate per pair. Rates are upserted on each fetch, so the system always has the latest available rate even if the API is temporarily unavailable.

**Rate Fetching with Fallback** (CC-03): The `fetch_exchange_rates()` function tries the primary API (open.er-api.com) first, and falls back to frankfurter.app if the primary fails. If both APIs fail, an admin alert email is sent via `mail_admins()` warning that rates may be stale. This dual-provider approach ensures the system continues functioning even if one API experiences downtime.

**Conversion Logic**: The `get_exchange_rate()` function handles three lookup strategies: (1) same currency returns 1.0 immediately, (2) direct pair lookup in the database (e.g., USD→BDT), (3) reverse pair with rate inversion (e.g., BDT→USD from a USD→BDT row), and (4) cross-pair via base currency (e.g., EUR→BDT computed as EUR→USD × USD→BDT). A guard against zero or very small rates (MED-06 fix) prevents precision issues from corrupt data.

**Price Conversion** (`convert_price()`): This function converts an amount in cents from one currency to another, correctly handling zero-decimal currencies (HIGH-08 fix). The conversion flow: divide by `10^decimal_digits` of the source currency to get the main unit amount, multiply by the exchange rate, round to the target currency's decimal places, then multiply by `10^decimal_digits` of the target currency to get back to cents. This ensures that 1000 JPY cents (1000 yen, not 10 yen) converts correctly.

**Plan Price Conversion** (`convert_plan_prices()`): When the frontend requests plans with `?currency=BDT`, this function batch-converts all plan prices for the requested currency. It adds `converted_price_cents`, `user_currency`, and `exchange_rate` fields to each plan dict. Critically, `user_currency` is only set when conversion actually succeeds — if no rate is available, the field is None and the frontend falls back to displaying the original price with the plan's base currency symbol, preventing the display of "$9.00" with a taka symbol.

---

# 6. Credit System

The Credit System is SattaBase's alternative payment pathway, designed specifically for users who cannot use international credit cards — a common scenario in South Asian markets where domestic banking infrastructure (bank transfers, mobile financial services) is the norm. While Stripe handles card-based subscription billing (described in Section 5), the Credit System provides a parallel offline payment flow where users submit bank transfer requests, administrators review and approve them, and credits are allocated into period-based pools that behave like subscriptions. The two systems are mutually aware: starting a Stripe subscription automatically cancels any active credit pools for the same product (preventing double access), and the `is_user_active_for_product()` unified access check in `BillingService` checks credit pools as a fallback when no active Stripe subscription exists.

## 6.1 Credit Pools & Lifecycle

The Credit System revolves around three core models that together form a complete ledger of credit allocation, consumption, and invoicing:

**CreditPool** — The central model representing a user's credit allocation for a specific product. A credit pool is analogous to a subscription: it tracks how many billing periods the user has purchased (`credit_periods`), how many have been consumed (`periods_consumed`), and the current billing period boundaries (`current_period_start`, `current_period_end`). The pool's lifecycle follows these states:

- **active**: The pool has remaining periods and is within its validity window. The user has full access to the product features defined by the associated plan.
- **exhausted**: All purchased periods have been consumed. This is set automatically by the `consume_credit_periods` Celery task when `periods_remaining` drops to zero.
- **expired**: The pool's hard expiry date (`expires_at`) has passed, regardless of remaining periods. This handles promotional credits with time-limited validity. Set by the `expire_credit_pools` Celery task.
- **canceled**: The pool was manually canceled, typically because the user converted to a Stripe subscription. Set by `BillingService.cancel_credit_pools_for_subscription()`.

The `is_effectively_active` computed property returns `True` only when the pool is in the `active` state AND either has no `current_period_end` or the current period has not yet ended. This mirrors the subscription model's `is_effectively_active()` check and is used by the unified access system to grant or deny product access.

Each pool is linked to a `Plan` (which defines the feature access level and billing cycle), a `Product` (the product being accessed), and optionally a `Subscription` (if the pool was created alongside or as a replacement for a subscription). The `source` field records how the pool was funded (`"manual"`, `"bank_transfer"`, or `"admin_grant"`), and the `payment_reference` field stores the bank transaction reference for audit traceability.

**CreditInvoice** — The financial record for each credit purchase. Every time a credit pool is created (via admin approval or manual creation), a `CreditInvoice` is generated alongside it within the same `transaction.atomic()` block (CRIT-10 fix). The invoice number follows the format `SB-CRED-XXXXXXXXXX` (10-digit zero-padded pool ID), ensuring uniqueness and traceability. Invoices have their own status lifecycle: `issued`, `paid`, `void`, and `refunded`. For bank-transfer purchases, invoices are created in the `paid` status since the transfer has already been verified by the admin at approval time.

**CreditTransaction** — The immutable ledger entry for every credit pool mutation. Every action that changes a pool's state creates a `CreditTransaction` record with the following fields:
- `action`: The type of mutation (`PURCHASE`, `PERIOD_CONSUME`, `ADJUST`, `REFUND`, `EXPIRE`)
- `periods_delta`: Positive for credit additions, negative for debits
- `amount_cents_delta`: The financial impact (positive for additions, negative for refunds/voids)
- `periods_balance`: The remaining periods after the transaction (running balance)
- `reason`: Human-readable explanation of why the transaction occurred
- `created_by`: The admin user who initiated the transaction (null for automated tasks)

This transaction log provides a complete audit trail for financial compliance. The `periods_balance` field enables point-in-time balance reconstruction without requiring aggregation queries across the full transaction history.

## 6.2 Credit Purchase Requests (Bank Transfer)

The user-facing credit purchase flow follows a request-approve-reject pattern mediated by administrators:

**Step 1 — User Submits Request**: The `POST /api/v1/billing/credits/request` endpoint (in `BillingProtectedController`) accepts a `CreditRequestInputSchema` payload containing the product, plan, number of billing periods, amount in cents, and bank transfer details. The controller performs several validations before creating the `CreditPurchaseRequest`:

1. **Email Verification** (HIGH-04): The `require_verified_email()` check ensures only verified users can submit credit requests, preventing abuse from throwaway email accounts.
2. **Product/Plan Validation**: The product must be active, and the plan must belong to the product and also be active.
3. **Minimum Commitment** (ENHANCEMENT-1): Monthly plans require a minimum of 3 periods, while yearly plans require at least 1 period. This prevents trivial purchases that would cost more in administrative overhead than the revenue generated.
4. **Amount Verification** (ENHANCEMENT-1): The submitted `amount_cents` must exactly equal `credit_periods * plan.price_cents`. This server-side validation prevents price manipulation — a user cannot submit a request for 3 monthly periods at a discounted amount.
5. **Bank Validation** (HIGH-12): The `bank_name` in the request must match an active `BankSettings` record in the database. This prevents users from submitting transfers to arbitrary bank accounts that the system cannot verify.

The `CreditPurchaseRequest` model captures all the information needed for admin review: the user's bank name, account holder name, account number, routing number, transaction reference number, and an optional payment proof note. Requests are created in `pending` status and remain there until an admin takes action.

**Step 2 — Admin Approves**: The `POST /api/v1/admin/credit-requests/{request_id}/approve` endpoint (in `AdminCreditRequestController`) uses `select_for_update()` within a `transaction.atomic()` block (CRIT-03 fix) to prevent race conditions where two admins could approve the same request simultaneously. The approval flow:

1. Lock the `CreditPurchaseRequest` row with `select_for_update()`
2. Verify the request is still in `pending` status
3. Call `BillingService.create_credit_pool()` (wrapped in `sync_to_async`) which atomically creates the `CreditPool`, `CreditInvoice`, and initial `CreditTransaction` record
4. Update the request status to `approved`, record the reviewer and timestamp, and link the created credit pool
5. Dispatch the `send_credit_request_approved_email` Celery task (outside the transaction) to notify the user

**Step 3 — Admin Rejects**: The `POST /api/v1/admin/credit-requests/{request_id}/reject` endpoint updates the request status to `rejected` and dispatches the `send_credit_request_rejected_email` Celery task. The admin can include an optional rejection reason that is included in the email notification.

**Frontend Pages**: Users interact with the credit system through two pages: `/dashboard/billing/credits` (listing their credit pools, rendered by `UserCreditsClient.vue`) and `/dashboard/billing/credits/request` (the request form, rendered by `CreditRequestClient.vue`). The `credits.ts` API client provides typed functions for all credit-related API calls. Admins manage credit requests at `/admin/credit-requests` via `CreditRequestsAdmin.vue`.

## 6.3 Credit Consumption & Expiry

Credit pools behave like subscriptions in that they consume billing periods over time. Two Celery Beat tasks handle the automated lifecycle:

**`consume_credit_periods`** (daily): This task finds all active credit pools where `current_period_end` has passed and processes them. The logic follows these steps for each pool:

1. **First Activation**: If `current_period_start` is null (a newly created pool that hasn't been activated yet), the task sets the period boundaries based on the plan's billing cycle (30 days for monthly, 365 days for yearly) and continues to the next pool without consuming a period.
2. **Period Consumption**: The task increments `periods_consumed` by 1, creates a `CreditTransaction` record with action `PERIOD_CONSUME`, and checks the remaining periods.
3. **Exhaustion Check**: If `periods_remaining <= 0`, the pool status is changed to `exhausted` and the period boundaries are cleared. Otherwise, a new billing period is started with updated start/end dates.

The task uses `select_for_update()` (CRIT-04 fix) to prevent race conditions when multiple Celery workers or overlapping task executions attempt to process the same pool simultaneously. Each pool is processed within its own `transaction.atomic()` block, so a failure on one pool does not affect others.

**`expire_credit_pools`** (daily): This task finds active pools where `expires_at` has passed and marks them as `expired`, regardless of remaining periods. This handles promotional credits, time-limited grants, and any pool where an admin has set a hard expiry date. Each expiry creates a `CreditTransaction` record with action `EXPIRE` and the remaining periods as a negative delta.

**Unified Access Check** (`BillingService.is_user_active_for_product()`): This method provides a single point of truth for determining whether a user has active access to a product, checking both the Stripe subscription and credit pool systems. The logic is:

1. **Subscription First**: Look for an active or trialing Stripe subscription with a future `current_period_end`. If found, return with `source: "subscription"` and `is_credit_based: False`.
2. **Credit Pool Fallback**: If no active subscription exists, look for an active credit pool with `periods_remaining > 0` and either no expiry or a future `expires_at`. If found, return with `source: "credit"` and `is_credit_based: True`.
3. **No Access**: Return `is_active: False` with null values.

This unified check ensures that credit pool users receive the same plan-based access map (feature keys and values from `AccessEntry`) as Stripe subscribers, making the access control layer agnostic to the payment source.

**Cancellation on Stripe Conversion**: When a user starts a Stripe subscription for a product where they have active credit pools, the `BillingService.cancel_credit_pools_for_subscription()` method is called. This method atomically cancels all active pools for that user+product combination, setting their status to `canceled` and creating `ADJUST` transaction records with the voided remaining periods. This prevents double-access where a user could have both a Stripe subscription and a credit pool granting access to the same product.

## 6.4 Invoice PDF Generation

SattaBase generates professional PDF invoices for credit purchases using ReportLab, implemented in `billing/pdf_utils.py`. The `generate_credit_invoice_pdf()` function accepts a `CreditInvoice` model instance (with `select_related("user", "product", "plan", "credit_pool")`) and returns raw PDF bytes.

**Design System**: The PDF follows a modern, branded layout with these visual elements:
- **Brand Colors**: Blue-600 (`#2563EB`) as the primary accent, Blue-800 for dark headers, Blue-50/100 for light backgrounds, and a consistent gray scale (900/500/400/200/50) for text and borders. Green-600 is used for "paid" status badges.
- **Header Section**: Two-column layout with the company name and tagline on the left and the "INVOICE" title on the right, separated by a 2px brand-color horizontal rule.
- **Details Section**: Two-column layout with invoice details (invoice number, issue date, payment method, currency) on the left and billing details (status badge, billed-to email) on the right.
- **Line Items Table**: Professional table with a brand-colored header row, four columns (Description, Qty, Unit Price, Amount), and alternating row shading. Tax rows are included when applicable.
- **Totals Section**: Subtotal, tax, and total rows with the total row highlighted in a Blue-50 background and a brand-color top border.
- **Payment Details**: Optional section showing the payment reference, credit periods, and validity end date.
- **Footer**: A subtle divider line followed by a thank-you message and the company domain/support email.

**Currency Formatting**: The `_format_cents()` helper converts cent amounts to display strings with currency symbols. It handles USD (`$`), EUR, GBP, and falls back to the ISO currency code with a trailing space (e.g., `BDT 1,500.00`). All amounts are formatted with comma-separated thousands and two decimal places.

**Status Colors**: Invoice status badges use semantic colors — green for "paid", blue for "issued"/"open"/"draft", and gray for other statuses — matching the admin panel's visual language.

**Serving PDFs**: The user-facing endpoint `GET /api/v1/billing/credits/invoices/{invoice_number}/pdf` (in `BillingProtectedController`) generates and returns the PDF as a downloadable file. The endpoint validates that the invoice belongs to the authenticated user and requires email verification (HIGH-04). The `generate_credit_invoice_pdf()` call is wrapped in `sync_to_async()` because ReportLab is a synchronous library. The admin panel has a parallel endpoint for admin-only access to any user's credit invoice PDFs.

## 6.5 Email Notifications (Approval/Rejection)

Two Celery tasks handle email notifications for credit purchase request outcomes, both defined in `billing/tasks.py`:

**`send_credit_request_approved_email`**: Dispatched after admin approval (outside the database transaction to avoid sending emails on rollback). Sends a professional HTML email with:
- A blue SattaBase branded header
- A green "Approved" status badge
- A details card showing the product name, plan name, amount, billing periods, invoice number, and payment method
- Two action buttons: "View My Credits" (linking to `/dashboard/billing/credits`) and "Download Invoice" (linking to `/dashboard/billing/transactions`)
- An informational paragraph explaining that credits are active and will be applied automatically each billing cycle
- A plain text fallback for email clients that don't support HTML

The task accepts all necessary details as parameters (user email, name, product/plan names, amount, currency, pool ID, invoice number, periods) rather than querying the database, which avoids stale data issues and keeps the task stateless. It retries up to 3 times with a 60-second delay between retries.

**`send_credit_request_rejected_email`**: Dispatched after admin rejection. Sends a similar branded email but with:
- A red "Not Approved" status badge
- A details card showing the product name, plan name, and requested amount
- An optional reason section (rendered in a red-tinted card) if the admin provided a rejection reason
- A single "Submit New Request" action button linking to `/dashboard/billing/credits/request`

Both tasks use Django's `send_mail()` with `html_message` for the HTML version and `message` for the plain text fallback. The `fail_silently=False` setting ensures that email sending failures are properly caught and trigger the retry mechanism.

## 6.6 Admin Credit Operations

Administrators have two additional credit pool management endpoints beyond the approve/reject flow:

**`POST /api/v1/admin/credits/{credit_id}/adjust`**: Allows admins to add or remove billing periods from an active credit pool. The endpoint uses `select_for_update()` within a `transaction.atomic()` block (CRIT-05 fix) to prevent race conditions during concurrent adjustments. The `AdminCreditAdjustSchema` payload specifies:
- `periods_delta`: The number of periods to add (positive) or remove (negative)
- `amount_cents_delta`: Optional financial impact override. If not provided, it's calculated as `periods_delta * plan.price_cents`
- `reason`: Required explanation for the adjustment (for audit trail)

The adjustment creates an `ADJUST` transaction record and automatically transitions the pool to `exhausted` status if `periods_remaining` drops to zero or below. Negative `periods_delta` values that would result in negative total periods are rejected with a `400 Bad Request`.

**`POST /api/v1/admin/credits/{credit_id}/refund`**: Voids remaining periods on a credit pool and creates a `REFUND` transaction record. Unlike Stripe refunds (which involve actual money movement), credit refunds are administrative actions that remove access from the user's credit pool. The pool's `periods_consumed` is not changed (the user already used those periods), but the remaining periods are voided and the pool status may transition to `exhausted`.

Both operations are protected by the `admin_write_rate_limit` decorator and the `@log_admin_access` audit decorator, ensuring that all credit mutations are rate-limited and logged with the admin's identity and IP address for compliance purposes.

---

# 7. Admin Panel Architecture

The SattaBase admin panel is a comprehensive backend-frontend system that gives staff users full control over the platform's commercial entities — products, plans, subscriptions, users, refunds, credit operations, metrics, webhooks, and bank settings. This section covers the backend controller architecture, the cross-cutting infrastructure that all admin endpoints share, and the frontend components that surface these capabilities.

## 7.1 Admin Controllers Overview

All admin endpoints live under the `/api/v1/admin/` URL prefix and are distributed across **seven dedicated controller classes** in `billing/`. Each controller is a `django-ninja-extra` `@api_controller` class with `auth=JWTAuth()` and `permissions=[IsAuthenticated, IsAdmin]`, ensuring that only staff users can reach them.

| Controller | File | Tag (OpenAPI) | Responsibility |
|---|---|---|---|
| `AdminProductController` | `admin_controller.py` | Admin — Products & Domains | Product CRUD, service domain management |
| `AdminPlanController` | `admin_controller.py` | Admin — Plans & Access Entries | Plan CRUD, access entry CRUD, feature matrix |
| `AdminRefundController` | `admin_controller.py` | Admin — Refunds | Refund listing, approval, rejection (two-person rule) |
| `AdminCreditController` | `admin_controller.py` | Admin — Credits | Credit pool adjust and refund |
| `AdminCreditRequestController` | `admin_controller.py` | Admin — Credit Requests | Credit purchase request listing, approval, rejection |
| `AdminCreditInvoiceController` | `admin_controller.py` | Admin — Credit Invoices | Credit invoice listing and PDF generation |
| `AdminBankSettingsController` | `admin_controller.py` | Admin — Bank Settings | Bank account CRUD for manual transfer payments |
| `AdminSubscriptionController` | `admin_subscription_controller.py` | Admin — Subscriptions | Subscription list/detail, override, cancel, expire, extend, history |
| `AdminUserController` | `admin_user_controller.py` | Admin — Users | User list/detail, status/role changes, audit trail |
| `AdminMetricsController` | `admin_metrics_controller.py` | Admin — Metrics & Audit | Dashboard metrics, revenue breakdown, funnel, audit log, webhook monitoring |

All controllers share two cross-cutting decorators defined in `billing/admin_utils.py`:

**`@log_admin_access`**: A decorator that performs dual logging for every mutation request. First, it emits a structured Python log line (`ADMIN_BILLING_ACCESS: user_id=..., email=..., action=..., ip=..., path=...`) for application-level observability and log aggregation. Second, it persists the action to the `AdminAuditLog` database model after the handler returns, capturing the HTTP status code. The DB write is fire-and-forget — if it fails, the exception is caught and logged so the real request is never blocked.

**`@admin_write_rate_limit` / `@admin_read_rate_limit`**: Decorators that enforce per-admin rate limits using Redis-backed counters. Write endpoints default to 30 requests per 60 seconds; read endpoints default to 120 requests per 60 seconds. The rate limit key is built as `admin_write:{user_id}:{ip}` or `admin_read:{user_id}:{ip}`, giving each admin their own bucket per IP address.

The frontend admin panel is built as a set of 23 Vue components under `src/components/admin/` and 14 page routes under `src/pages/admin/`. The API client is centralized in `src/lib/admin.ts`, which exports typed request functions for every admin endpoint along with helper formatters (status badge colors, date formatting, relative time).

## 7.2 Product & Plan Management

Product and plan management is handled by two controller classes in `admin_controller.py`:

**`AdminProductController`** provides full CRUD for products and their associated service domains:

- `POST /admin/products` — Creates a product with auto-generated slug (from `slugify(name)` if not provided). Validates unique name and slug constraints before creation.
- `GET /admin/products` — Lists all products with annotated `plan_count`, `active_plan_count`, `domain_count`, and per-product `subscriber_count` (counting active + trialing subscriptions). Supports `?is_active=` and `?search=` (name/slug) filters with pagination.
- `GET /admin/products/{id}` — Returns full detail with all plans (each annotated with subscriber count) and service domains.
- `PUT /admin/products/{id}` — Partial update; only provided fields are modified. Name/slug changes validate uniqueness excluding the current record.
- `PATCH /admin/products/{id}/toggle` — Activates or deactivates a product. Rejects deactivation if any active or trialing subscriptions exist (those users would lose access without warning).
- `DELETE /admin/products/{id}` — Soft-delete by setting `is_active=False`. Same active-subscription guard as toggle.

Service domains are managed as nested resources under products. `POST /admin/products/{product_id}/domains` creates a domain; the first domain for a product is auto-set as primary. `PUT /admin/domains/{id}` handles primary domain uniqueness — when setting a domain as primary, the previous primary for the same product is automatically unset. `DELETE /admin/domains/{id}` prevents deleting the primary domain if other domains exist for the same product.

**`AdminPlanController`** manages plans and their access entries:

- `POST /admin/products/{product_id}/plans` — Creates a plan with auto-generated slug, validates unique `(product, slug)` pair, and defaults `sort_order` to `max + 1`.
- `GET /admin/plans/{id}` — Returns plan detail with all access entries.
- `PUT /admin/plans/{id}` — Partial update. If `price_cents` or `billing_cycle` changes and active subscribers exist, a warning is included in the response (but the change is not blocked).
- `PATCH /admin/plans/{id}/toggle` — Toggles `is_active`.
- `PATCH /admin/plans/{id}/feature` — Toggles `is_featured`.
- `POST /admin/plans/{id}/duplicate` — Clones a plan (including its access entries) under the same product.
- `DELETE /admin/plans/{id}` — Hard-deletes a plan.

Access entries (the key-value pairs that define what a plan grants access to) support individual CRUD, bulk replacement, and a feature matrix view. The access matrix endpoint (`GET /admin/products/{product_id}/access-matrix`) returns a transposed view where rows are feature keys and columns are plans, making it easy to compare plans side-by-side. The `PUT /admin/products/{product_id}/access-matrix/row` endpoint saves a single row atomically across multiple plans — creating, updating, or deleting entries as needed in a single `transaction.atomic()` block.

The frontend surfaces these through `ProductsAdmin.vue` (list), `ProductDetailAdmin.vue` (detail with plan and domain management), `PlanDetailAdmin.vue` (plan detail with access entries), and `AdminFeatureMatrix.vue` (the feature comparison matrix).

## 7.3 Subscription Administration

`AdminSubscriptionController` (in `admin_subscription_controller.py`) provides powerful subscription management tools that bypass Stripe workflows for manual corrections and support escalations:

**Read endpoints**:
- `GET /admin/subscriptions` — Lists all subscriptions with user/plan/product context. Supports filtering by `product_id`, `plan_id`, `status`, and `search` (user email/name). Ordered by most recent first with pagination.
- `GET /admin/subscriptions/{id}` — Full detail with trial info, cancellation state, dunning step, ToS acceptance, and a flat access map derived from the plan's access entries.

**Mutation endpoints**:
- `PATCH /admin/subscriptions/{id}/override` — The most powerful admin tool. Changes plan, status, or billing period with full before/after audit logging. Validates that plan changes stay within the same product (cross-product changes are not allowed). When a subscription has an active `stripe_subscription_id`, the response includes a warning that the local override may diverge from Stripe's source of truth. The `reason` field is captured for the audit trail.
- `PATCH /admin/subscriptions/{id}/cancel` — Force-cancel with `cancel_at_period_end=True`, mirroring the user-initiated cancel flow but performed by an admin.
- `PATCH /admin/subscriptions/{id}/expire` — Immediate expiration. The user loses access right away regardless of the billing period. Used for severe violations, chargebacks, or when Stripe has already expired the subscription and local state needs to catch up.
- `PATCH /admin/subscriptions/{id}/extend` — Extends `current_period_end` by a given number of days. Useful for granting complimentary extensions for service outages or goodwill gestures. Does not work on expired subscriptions (use override first) or lifetime plans (use override to set period dates).

**History endpoints**:
- `GET /admin/subscriptions/{id}/plan-changes` — Paginated plan change history from `PlanChangeLog`, including proration details and who initiated the change.
- `GET /admin/subscriptions/{id}/invoices` — Paginated invoice history with Stripe hosted/PDF URLs and fee information.
- `POST /admin/subscriptions/{id}/refund` — Issues a Stripe refund with the two-person approval rule. The refund starts in `pending` status and must be approved by a different admin.
- `GET /admin/subscriptions/{id}/refunds` — Paginated refund history with initiation and approval details.

The frontend uses `SubscriptionsAdmin.vue` (list with filters) and `SubscriptionDetailAdmin.vue` (detail view with tabbed interface for plan changes, invoices, and refunds).

## 7.4 User Administration

`AdminUserController` (in `admin_user_controller.py`) provides user account management with built-in safety guards:

**Read endpoints**:
- `GET /admin/users` — Lists all users with annotated `subscription_count` and `active_subscription_count`. Supports filtering by `is_active`, `is_email_verified`, `role`, and free-text search across email and name fields. Paginated, ordered by most recent first.
- `GET /admin/users/{id}` — Full detail with profile fields (phone, timezone, currency, language), all subscriptions across products, and the 10 most recent login events.

**Mutation endpoints**:
- `PATCH /admin/users/{id}/status` — Activates or deactivates a user account. Two safety guards: admins cannot deactivate their own account (prevents accidental self-lockout), and deactivating a user with active subscriptions triggers a warning (but does not block, since deactivation does not automatically cancel subscriptions).
- `PATCH /admin/users/{id}/role` — Changes a user's role between `owner`, `admin`, and `member`. Validates against the `RoleChoices` enum. Prevents self-demotion (an admin cannot lower their own role) to avoid lockout scenarios. When a role is changed to `owner` or `admin`, `is_staff` is automatically synced to `True`; for `member`, it is set to `False`.

**Audit endpoint**:
- `GET /admin/users/{id}/audit` — Compiles a comprehensive audit trail from four data sources into a single chronological timeline: login events from `UserLoginHistory`, plan changes from `PlanChangeLog`, subscription status events (cancellation/expiration inferred from timestamps), and refund events from `Refund` records. Events are sorted by timestamp descending with in-memory pagination. Each event includes `event_type`, `description`, `metadata` (structured context), `ip_address` (where available), and `timestamp`.

The frontend uses `UsersAdmin.vue` (list with filters) and `UserDetailAdmin.vue` (detail with subscriptions tab and audit timeline via `AdminAuditTimeline.vue`).

## 7.5 Metrics & Reporting

`AdminMetricsController` (in `admin_metrics_controller.py`) provides four metrics endpoints for the admin dashboard, plus the audit log and webhook monitoring endpoints:

**`GET /admin/metrics/overview`** — Aggregate dashboard metrics:
- **MRR** (Monthly Recurring Revenue): Sum of active subscription plan prices. Yearly plans contribute `price_cents / 12`; lifetime plans contribute `0` (they are one-time, not recurring). Supports a `?currency=` parameter for display currency.
- **Subscription counts**: Active, trialing, past-due, and canceled subscriptions.
- **Churn rate**: Subscriptions canceled in the last 30 days divided by active subscriptions 30 days ago.
- **Trial conversion rate**: Trials that started in the last 60 days that converted to paid (active) status.
- **Total users**: All registered users.

**`GET /admin/metrics/revenue`** — Revenue breakdown by product, plan, and month (last 12 months). Queries the `RevenueRecognitionEntry` table for accurate daily recognized revenue:
- **by_product**: Revenue, active subscription count, and trial count per product.
- **by_plan**: Revenue contribution and subscriber count per plan.
- **by_month**: Monthly revenue trend with new subscriptions, churned subscriptions, and net MRR change (current month minus previous month).

**`GET /admin/metrics/subscriptions`** — Subscription funnel metrics over a configurable analysis period (default 30 days, max 365):
- New user registrations, trial starts, trial-to-paid conversions, active-to-canceled transitions, active-to-past-due transitions, and past-due-to-active recoveries.
- Per-product breakdown of the same funnel metrics.

**`GET /admin/metrics/products`** — Per-product summary with total subscribers, active subscribers, MRR contribution (monthly equivalent), and plan distribution (count of active subscriptions per plan).

All metrics computations are wrapped in `@sync_to_async` blocks so the heavy ORM queries run in a sync thread without blocking the ASGI event loop. Currency display uses the centralized `_format_currency()` helper from `currency_service.py`, which handles currency symbols and zero-decimal currencies.

The frontend renders these metrics in `AdminDashboard.vue` (overview with `AdminStatsCard` components), with dedicated pages for revenue, subscription funnel, and per-product views.

## 7.6 Audit Logging

The audit system has two layers that work in tandem:

**Layer 1: `@log_admin_access` decorator** (in `billing/admin_utils.py`). This decorator wraps every admin mutation handler and performs two actions:
1. Emits a structured Python log line (`ADMIN_BILLING_ACCESS: user_id=..., email=..., action=..., ip=..., path=...`) before executing the handler, providing real-time observability.
2. After the handler returns, persists an `AdminAuditLog` database record capturing the admin user, action name (the handler's `__name__`), HTTP method, API path, IP address, response status code, and an optional details dict. The DB write is wrapped in a try/except — if it fails, the error is logged but the original response is still returned. This ensures that audit logging never breaks a real request.

**Layer 2: `write_credential_audit()` function** (in `common/audit.py`). This synchronous helper writes credential lifecycle events (API key created, revoked, rotated, validation failed) to the same `AdminAuditLog` table. It is called from:
- Django signal handlers (`common/signals.py`) — runs synchronously inside the ORM transaction when a `ServiceCredential` is saved or deleted.
- Controllers — for admin-initiated mutations where the request context is available.
- Middleware — for validation failures where the request exists but no admin user is identified.

The `AdminAuditLog` model (in `billing/models.py`) intentionally uses `auto_now_add` for `created_at` instead of inheriting from `TimeStampedModel`. Audit records are immutable — they are never edited after creation, so an `updated_at` field would be misleading. Key fields include:
- `admin_user` — FK to the admin who triggered the action (nullable, for system-initiated events).
- `action` — Dot-separated identifier (e.g., `product.create`, `api_key.revoked`, `subscription.override`).
- `method`, `path`, `ip_address`, `status_code` — HTTP request context.
- `details` — JSON field for structured context (merged with auto-detected fields from the credential instance when applicable).

The `GET /admin/audit-log` endpoint in `AdminMetricsController` provides a paginated, filterable view. Admins can filter by `admin_user_id`, `action` (prefix match, e.g., `product` matches `product.create`, `product.update`), and date range (`date_from`, `date_to`). The frontend renders this in `AuditLogAdmin.vue`.

## 7.7 Webhook Monitoring & Retry

Stripe webhook events are logged to the `WebhookEventLog` model (in `billing/models.py`) before processing. Each entry stores the Stripe event ID, event type, processing status, error message, and the full JSON payload. Failed events remain unprocessed so they can be identified and retried.

`AdminMetricsController` provides two endpoints for webhook monitoring:

**`GET /admin/webhooks`** — Lists all webhook events with filtering by `event_type` and `processed` status (true for successfully processed, false for failed). The response includes a `failed_count` field indicating how many entries in the current page have failed processing, making it easy to spot issues at a glance.

**`POST /admin/webhooks/{id}/retry`** — Re-processes a failed webhook event. The endpoint validates that the event has not already been processed and that a stored payload exists. It then calls `process_event()` from the webhook router, which dispatches the event to the appropriate handler. If re-processing succeeds, the event's `processed` flag is updated; if it fails, the error message is updated. Both outcomes are logged. This is protected by `admin_write_rate_limit` and `@log_admin_access`.

The `WebhookEventLog` model is also cleaned up periodically by the `cleanup_stale_webhook_events` Celery task (FIN-08), which deletes successfully processed events older than the configured retention period. The frontend renders the webhook list in `WebhooksAdmin.vue` with a retry button for failed events.

## 7.8 Bank Settings Management

`AdminBankSettingsController` (in `admin_controller.py`) manages the bank account details displayed to users during credit purchase requests via bank transfer. Since this is a relatively simple CRUD resource, it uses a lightweight approach with Django's async ORM methods (`aget`, `acreate`, `adelete`) rather than the `sync_to_async` wrapper pattern used by the more complex controllers.

Endpoints:
- `GET /admin/bank-settings` — Lists all bank accounts (active and inactive) ordered by active status first.
- `POST /admin/bank-settings` — Creates a new bank account. Includes a MED-13 fix that checks for duplicate bank accounts with the same `bank_name` and `account_number` before creation.
- `PUT /admin/bank-settings/{id}` — Updates an existing bank account.
- `PATCH /admin/bank-settings/{id}/toggle` — Toggles `is_active` status. Only active bank accounts are shown to users on the credit request page.
- `DELETE /admin/bank-settings/{id}` — Permanently deletes a bank account.

Each bank account stores: `bank_name`, `account_holder_name`, `account_number`, `routing_number`, and `is_active`. The `BankSettings` model (in `billing/models.py`) inherits from `TimeStampedModel` and `ActivatorModel`, providing the standard `created_at`/`updated_at` and `is_active`/`deactivate()`/`activate()` patterns.

The workflow integrates with the credit purchase flow (Section 6): when a user submits a credit purchase request, they select from the active bank accounts. After transfer, they provide the transaction reference. Admins review these requests in the `AdminCreditRequestController` and, upon approval, the credit pool is created with a reference to the bank name and payment method.

The frontend renders bank settings management in `BankSettingsAdmin.vue` with a summary dashboard (total, active, inactive counts), a create/edit form, and a list of accounts with edit, toggle, and delete actions. The page also includes an informational section explaining the bank-to-credit workflow for new admins.

---

# 8. SDK & Sister Domain Integration

SattaBase is designed as the centralized billing and authentication hub for a family of sister web applications. Each sister domain (e.g., `finance.sattaspace.tld`, `tools.sattaspace.tld`) integrates with SattaBase through a well-defined SDK layer that provides API key authentication, dynamic CORS resolution, SSO via authorization code flow, webhook notifications for credential lifecycle events, and real-time usage analytics. This section describes every component of that integration layer in detail, from the data models through the middleware pipeline to the integration guide for sister domain developers.

## 8.1 Service Domain Model

The `ServiceDomain` model (`billing/models.py`) is the foundational entity that represents a connected sister application. Each service domain maps to exactly one `Product`, establishing the link between a domain and its subscription plans. The relationship is one-to-many from the product side — a product can have multiple service domains (e.g., a primary domain like `finance.sattaspace.tld` and a custom domain like `app.myfinance.com`), but each domain belongs to only one product.

**Key Fields:**

| Field | Type | Description |
|---|---|---|
| `domain` | CharField(255), unique, indexed | The fully qualified domain name (e.g., `finance.sattaspace.tld`). This is matched against the `X-Service-Domain` header on incoming API requests and against the `Origin` header for CORS resolution. |
| `product` | FK(Product, CASCADE) | The product this domain serves subscriptions for. When a sister domain calls `auth/me`, SattaBase resolves the domain to a product, then returns the user's subscription and access map for that product. |
| `is_primary` | BooleanField, default False | Marks the primary domain for a product. Only one domain per product can be primary (enforced by a unique constraint). Used in product detail responses and admin displays. |
| `is_active` | BooleanField, default True, indexed | Whether this domain is accepting requests. Inactive domains are excluded from CORS whitelisting and API key validation. |
| `webhook_url` | URLField, null/blank | The URL to which SattaBase dispatches credential lifecycle events (revocation, rotation). Opt-in per domain. |
| `webhook_secret` | CharField(100), null/blank | HMAC-SHA256 signing key for webhook payloads. Must be configured alongside `webhook_url` for webhooks to be dispatched. |

**Domain Resolution Priority in `auth/me`:**

When the `BillingProtectedController.get_auth_me()` endpoint is called, the domain is resolved in the following priority order:

1. **Service credential's domain** — if the request included a valid `X-API-Key` header, the middleware has already attached `request.service_domain_from_key`, which is used directly.
2. **`X-Service-Domain` header** — for backward compatibility with direct SDK calls that don't use API key authentication but still want domain-scoped responses.
3. **None** — if no domain identifier is present, the endpoint returns the plain user profile without subscription data.

This model is central to the entire SDK architecture because it bridges the gap between "who is calling" (the credential) and "what product are they asking about" (the domain-to-product mapping). Without a `ServiceDomain` record, a sister domain has no identity within SattaBase and cannot authenticate, receive CORS headers, or retrieve subscription data.

## 8.2 Service Credential (API Key) System

The `ServiceCredential` model (`billing/models.py`) represents an API key credential used for service-to-service authentication. Each `ServiceDomain` has at most one `ServiceCredential` (enforced by a `OneToOneField` relationship), establishing a one-credential-per-domain policy.

**Key Fields:**

| Field | Type | Description |
|---|---|---|
| `name` | CharField(100) | Human-readable identifier (e.g., "Finance Backend Production"). |
| `service_domain` | OneToOneField(ServiceDomain, CASCADE) | The domain this credential is bound to. One credential per domain. |
| `api_key_hash` | CharField(255), unique, indexed | SHA-256 hash of the raw API key. The raw key is never stored. |
| `api_key_prefix` | CharField(12), indexed | First 12 characters of the raw key for identification in logs and admin displays (e.g., `sb_live_a1Bc`). |
| `permissions` | JSONField, default dict | Scoped permissions controlling which API surface the credential can access (e.g., `{"auth": True, "billing_read": True}`). |
| `is_active` | BooleanField, default True, indexed | Can be revoked instantly by setting to False. |
| `last_used_at` | DateTimeField, null | Updated atomically on each successful validation for audit and analytics. |
| `created_by` | FK(User, SET_NULL) | The admin who created this credential. |

**API Key Generation** (`common/utils.py`):

The `generate_api_key()` function creates keys using Python's `secrets.token_urlsafe(32)`, resulting in a 50-character key with the format `sb_live_<43 random chars>`. The function returns a tuple of `(raw_key, prefix, sha256_hash)`. The raw key is shown only once in the creation response and can never be recovered. The hash is stored in the database for lookup, and the prefix is stored for human identification in logs and admin UI.

**Key Lifecycle:**

1. **Creation** — Admin creates a key via `POST /admin/api-keys/`. The raw key is returned in the response body with a warning that it cannot be recovered. If a revoked credential already exists for the domain, it is reused (updated in place) rather than creating a new row.
2. **Active Use** — On every request with a valid `X-API-Key` header, the middleware validates the key, updates `last_used_at`, and tracks usage analytics.
3. **Revocation** — Admin revokes a key via `PATCH /admin/api-keys/{id}/revoke`. The key is immediately invalid. A `credential.revoked` webhook is dispatched to the domain's webhook URL.
4. **Rotation** — Admin rotates a key via `POST /admin/api-keys/{id}/rotate`. The old key is revoked, a new credential is created for the same domain, and the raw new key is returned. A `credential.rotated` webhook is dispatched with both old and new prefixes.

The one-credential-per-domain constraint is enforced at both the application level (the controller checks for existing credentials before creation) and the database level (the `OneToOneField` relationship). If a race condition causes a duplicate, the `IntegrityError` is caught and a `ConflictException` is raised with instructions to rotate the existing key instead.

## 8.3 API Key Middleware & Validation

API key validation occurs at two layers: the middleware layer (`common/middleware.py`) for early request interception, and the controller layer (`common/api_key_auth.py`) for in-handler validation.

### Middleware Layer: `service_credential_middleware`

Registered as `common.middleware.service_credential_middleware` in `settings.MIDDLEWARE`, this middleware is placed after CORS middleware and before CSRF/auth middleware. It uses Django 5.2's `@sync_and_async_middleware` pattern, providing both sync (WSGI) and async (ASGI) paths. Under Daphne, the async path is taken, using `aget`/`aupdate` ORM calls so the event loop is never blocked.

**Opt-in Design:** The middleware only activates when the `X-API-Key` header is present. Requests without the header pass through untouched, preserving regular JWT authentication. This design allows both auth mechanisms to coexist without interference.

**Validation Sequence (on each request with `X-API-Key`):**

1. **Prefix check** — Fast reject if the key doesn't start with `sb_live_`. Returns 403 with code `invalid_api_key_format` (when enforcement is on).
2. **`X-Service-Domain` header required** — If `X-API-Key` is present but `X-Service-Domain` is missing, returns 400 with code `missing_service_domain`. This prevents key usage without domain context.
3. **SHA-256 hash lookup** — The raw key is hashed and used to look up a `ServiceCredential` via `select_related("service_domain", "created_by")`. If not found, returns 403 with code `api_key_forbidden`.
4. **Credential active check** — If `is_active` is False, returns 403 with code `api_key_revoked`.
5. **Domain active check** — If `service_domain.is_active` is False, returns 403 with code `service_domain_inactive`.
6. **Domain cross-check** — The `X-Service-Domain` header value must match `credential.service_domain.domain` exactly. This prevents domain spoofing where a key for domain A is used with the header of domain B. Returns 403 with code `domain_mismatch` on failure.
7. **Success** — Attaches `request.service_credential` and `request.service_domain_from_key` to the request, updates `last_used_at` atomically, and tracks analytics via `track_api_key_usage()`.

**Enforcement Mode** (`settings.API_KEY_ENFORCED`):

- `False` (default) — Invalid keys log a warning but the request continues. Useful for gradual rollout where some endpoints haven't been migrated to require API keys yet.
- `True` — Invalid keys immediately return a JSON error response. Used in production after all endpoints are confirmed to work with API key auth.

### Controller Layer: `validate_api_key()`

The `validate_api_key()` function in `common/api_key_auth.py` provides controller-level validation that is middleware-aware. If the middleware has already validated the key and attached `request.service_credential`, the function returns the cached credential immediately without re-querying the database. This makes controllers that call `validate_api_key()` directly work seamlessly with or without the middleware enabled.

This function is used in the `auth/me` endpoint where the controller needs to call `validate_api_key(request)` to support the `IsAuthenticatedOrService` permission — the endpoint accepts either a JWT (from the frontend) or an API key (from a sister domain SDK), and the validation function gracefully handles both cases by returning `None` when no key is present and enforcement is off.

## 8.4 Dynamic CORS for Service Domains

The `service_domain_cors_middleware` (`common/cors_middleware.py`) extends `django-cors-headers` by dynamically allowing origins from the `ServiceDomain` database table. This eliminates the need to manually configure `CORS_ALLOWED_ORIGINS` in settings every time a new sister domain is added — instead, simply creating a `ServiceDomain` record in the database automatically enables CORS for that domain.

**How It Works:**

1. The middleware checks the `Origin` header on every incoming request.
2. It loads the set of allowed origins from the `ServiceDomain` table (filtered by `is_active=True`), always including the configured `FRONTEND_URL` from `settings.FRONTEND_URL` (set via the `PUBLIC_SITE_URL_SB` environment variable).
3. If the origin matches an allowed domain, the middleware injects CORS headers into the response. Otherwise, it falls through to `django-cors-headers` default behavior.

**CORS Headers Injected:**

| Header | Value |
|---|---|
| `Access-Control-Allow-Origin` | The specific requesting origin (never `*`) |
| `Access-Control-Allow-Methods` | `GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD` |
| `Access-Control-Allow-Headers` | `Authorization, Content-Type, X-API-Key, X-Service-Domain, Accept, Origin, X-Requested-With` |
| `Access-Control-Allow-Credentials` | `true` |
| `Access-Control-Max-Age` | `86400` (24-hour preflight cache) |
| `Access-Control-Expose-Headers` | `X-API-Key, X-Service-Domain` |

**Credential Support:** The middleware always sets `Access-Control-Allow-Credentials: true` and uses the specific origin (not `*`) because the wildcard origin is incompatible with credentials (cookies). This is critical for cookie-based JWT refresh to work across sister domains.

**Cache Layer:** The allowed origins set is cached in Redis with key `sattabase_allowed_cors_origins` and a 5-minute TTL. This avoids a database query on every request. The cache is automatically invalidated by Django signals (`common/signals.py`) whenever a `ServiceCredential` is saved or deleted, ensuring that new domains are recognized within seconds rather than waiting for the TTL to expire.

**ASGI Compatibility:** The middleware uses `@sync_and_async_middleware` and wraps the database query in `sync_to_async` for the ASGI path, ensuring non-blocking operation under Daphne.

**Debug Mode:** When `CORS_ALLOW_ALL_ORIGINS=True` and `DEBUG=True`, the middleware also allows `localhost` and `127.0.0.1` origins with proper credential headers, which is essential for local development where cookie-based auth must work across different local ports.

## 8.5 SSO Authorization Code Flow

The cross-domain Single Sign-On (SSO) flow allows authenticated users on sister domains to access the SattaBase domain (e.g., for billing management) without requiring a second login. This is implemented as an authorization code flow — a lightweight OAuth2-style mechanism that avoids sharing JWT tokens across domains.

**Step 1: Authorization Code Generation** — `POST /api/v1/auth/authorize`

When a user on a sister domain needs to be redirected to SattaBase (e.g., to manage their subscription), the sister domain's frontend first calls this endpoint with the user's existing JWT access token. SattaBase generates a one-time authorization code that expires in 30 seconds and can only be used once. The code is stored in Redis (via `AuthService.agenerate_auth_code()`), making it fast to create and validate without database writes.

**Step 2: Redirect with Code** — The sister domain redirects the user's browser to SattaBase with the authorization code as a URL parameter:

```
https://base.sattaspace.com/auth/callback?code=<authorization_code>
```

**Step 3: Token Exchange** — `POST /api/v1/auth/token/exchange`

The SattaBase callback page (`/auth/callback`) receives the authorization code from the URL and calls this endpoint to exchange it for JWT tokens. The endpoint:

1. **Rate limits** the exchange to prevent brute force attacks on auth codes (CRIT-06 fix: max 10 attempts per 60 seconds).
2. **Consumes the code** — The code is deleted from Redis immediately upon use, preventing replay attacks.
3. **Generates new tokens** — A fresh access token and refresh token pair are created for the user.
4. **Sets the refresh token in an httpOnly cookie** (HIGH-03 fix) — The refresh token is NOT returned in the response body (AUTH-1 fix), only in the cookie. This provides XSS protection.
5. **Returns the access token** — Only the short-lived access token is returned in the JSON response body.

**Schemas:**

- `AuthorizeOutputSchema`: Returns `{ code: str, expires_in: 30 }`
- `TokenExchangeInputSchema`: Accepts `{ code: str }`
- `AccessTokenOnlySchema`: Returns `{ access: str }`

**Security Considerations:**

- The 30-second expiry on authorization codes limits the window for interception.
- Single-use enforcement (code is deleted from Redis on first exchange) prevents replay attacks.
- Rate limiting prevents brute-force guessing of authorization codes.
- The refresh token is never exposed in a URL or response body, only in the httpOnly cookie.
- The entire flow requires an initial valid JWT, ensuring only authenticated users can generate authorization codes.

## 8.6 Webhook Dispatch for Credential Events

When a service credential is revoked or rotated, the sister domain that owns that credential needs to be notified immediately so it can stop using the old key and switch to the new one. The webhook dispatch system (`common/webhooks.py`) provides this real-time notification capability.

**Event Types:**

| Event | Trigger | Payload Includes |
|---|---|---|
| `credential.revoked` | Admin revokes an API key | `credential_id`, `api_key_prefix`, `name`, `is_active`, `service_domain` |
| `credential.rotated` | Admin rotates an API key | Same as above plus `old_prefix` and `new_prefix` |

**Payload Structure:**

```json
{
  "event": "credential.revoked",
  "timestamp": 1715000000,
  "data": {
    "credential_id": 5,
    "api_key_prefix": "sb_live_a1Bc",
    "name": "Finance Backend Production",
    "is_active": false,
    "service_domain": "finance.sattaspace.tld"
  }
}
```

**Security — HMAC-SHA256 Signing:**

Every webhook payload is signed with HMAC-SHA256 using the domain's `webhook_secret`. The signature is sent in the `X-Satta-Signature` header. A `X-Satta-Timestamp` header contains the Unix timestamp for replay protection — receivers should reject payloads older than 5 minutes (300 seconds). The `verify_webhook_signature()` function (also in `webhooks.py`) is provided for receivers to validate signatures using `hmac.compare_digest` for constant-time comparison.

**Delivery Mechanism:**

The `dispatch_credential_webhook()` function is the main entry point for controllers and signals. It does NOT block — it builds the payload, signs it, and queues a Celery task (`deliver_credential_webhook` in `common/tasks.py`) for reliable async delivery. If the domain has no `webhook_url` or `webhook_secret` configured, the call is a no-op (logged at debug level).

**Celery Task — Retry with Exponential Backoff:**

The `deliver_credential_webhook` Celery task sends an HTTP POST with `Content-Type: application/json`, the HMAC signature in `X-Satta-Signature`, and the event type in `X-Satta-Event`. It retries up to 3 times with exponential backoff (1 min, 2 min, 4 min) on connection errors, timeouts, or 5xx responses. The HTTP timeout is 10 seconds per attempt.

**Integration Points:**

Webhook dispatch is triggered from two locations:
1. **Admin controllers** (`common/controllers.py`) — After `revoke_api_key()` and `rotate_api_key()` succeed, `dispatch_credential_webhook()` is called in a try/except block so that webhook failures never block the admin action.
2. **Django signals** (`common/signals.py`) — Signal handlers for `post_save` on `ServiceCredential` also trigger audit logging and webhook dispatch as a safety net.

## 8.7 SDK Integration Guide (Sister Domain)

This subsection provides a practical integration guide for developers building sister domain applications that need to authenticate users against SattaBase and check their subscription access.

**Prerequisites:**

1. A `ServiceDomain` record must exist in SattaBase, linking your domain to a product. This is created by a SattaBase admin.
2. A `ServiceCredential` (API key) must be generated for your domain via the admin panel. The raw key is provided once — store it securely in your backend's environment variables.
3. Your domain's `webhook_url` and `webhook_secret` should be configured if you want to receive credential lifecycle notifications.

**Authentication Flow — Server-to-Server API Calls:**

All API calls from your backend to SattaBase must include two headers:

```
X-API-Key: sb_live_a1BcD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3A4bC5dE6fG
X-Service-Domain: finance.sattaspace.tld
```

The `X-API-Key` identifies your service, and `X-Service-Domain` prevents cross-domain key misuse. Without both headers, SDK-authenticated endpoints will reject the request.

**Checking User Subscription Access:**

Call `GET /api/v1/billing/auth/me` with the two headers above. If the user has a valid JWT session on your domain, include their JWT access token in the `Authorization: Bearer <token>` header as well. The response includes:

- User profile data
- Subscription status for the product associated with your domain
- An `access_map` dictionary derived from `AccessEntry` records, containing the feature keys and values for the user's current plan

If the user's account is deactivated or deleted, the endpoint returns 401 with `account_inactive` or `account_deleted` error codes. Your frontend should treat these as force-logout signals.

**Cross-Domain SSO — Redirecting Users to SattaBase:**

When a user on your domain needs to access the SattaBase dashboard (e.g., to manage billing), use the authorization code flow:

1. Your frontend calls `POST /api/v1/auth/authorize` with the user's JWT.
2. SattaBase returns a one-time authorization code (expires in 30 seconds).
3. Your frontend redirects the user to `https://base.sattaspace.com/auth/callback?code=<code>`.
4. The SattaBase callback page exchanges the code for tokens and logs the user in.

**Handling Webhook Notifications:**

Set up an endpoint on your backend to receive POST requests from SattaBase. Validate each request by:

1. Reading the `X-Satta-Signature` header and the raw request body.
2. Computing HMAC-SHA256 of the body with your `webhook_secret`.
3. Comparing the computed signature with `X-Satta-Signature` using constant-time comparison.
4. Checking `X-Satta-Timestamp` to ensure the payload is less than 5 minutes old.
5. Processing the event based on `X-Satta-Event` type:
   - `credential.revoked` — Immediately stop using the old API key. The key is now invalid.
   - `credential.rotated` — Update your stored key to the new one. The old key is immediately revoked.

**CORS Configuration:**

No additional CORS configuration is needed on your side. SattaBase dynamically whitelists your domain based on the `ServiceDomain` record, including support for credentials (cookies) and all necessary headers.

## 8.8 Analytics & Usage Tracking

The `common/analytics.py` module tracks per-credential daily API request counts using Redis atomic counters, providing O(1) per-request overhead with automatic data expiry after 90 days.

**Redis Key Format:**

```
api_key_usage:{credential_id}:{YYYY-MM-DD} → integer (request count)
```

**`track_api_key_usage(credential_id)`:**

Called by the middleware after every successful API key validation. Uses Redis `INCR` which is atomic — safe for concurrent requests. The counter auto-expires after `RETENTION_DAYS` (90) days. Analytics tracking is wrapped in a try/except so that Redis failures never break a request — a debug log is written instead.

**`get_usage_stats(credential_id, days=30)`:**

Returns daily usage statistics for a single credential as a list of dicts ordered by date descending. Uses a Redis pipeline for efficient multi-key retrieval (one `GET` per day in the lookback period). Days with zero requests are excluded from the results.

**`get_all_usage_stats(days=7)`:**

Returns aggregated usage statistics across all credentials. Uses Redis `SCAN` with the pattern `api_key_usage:*` to find all matching keys, then aggregates request counts by credential ID. For production environments with many credentials, prefer `get_usage_stats()` with a specific credential ID for better performance.

**Admin Analytics Endpoints:**

Two admin endpoints expose the analytics data:

- `GET /admin/api-keys/analytics?days=7` — Aggregated overview across all credentials (total requests, per-credential breakdown).
- `GET /admin/api-keys/{id}/analytics?days=30` — Daily usage stats for a single credential.

Both endpoints use `sync_to_async` wrappers around the synchronous analytics functions and are protected by admin read rate limits (120 requests per minute).

---

# 9. API Reference

This section provides a comprehensive reference for all API endpoints exposed by the SattaBase backend. Every endpoint is served under the `/api/v1/` prefix, defined using django-ninja-extra's `@api_controller` decorator, and auto-registered via `api.auto_discover_controllers()` in `api/views.py`. The API generates an interactive OpenAPI/Swagger documentation at `/api/v1/docs/`.

## 9.1 API Structure & Versioning

The API is versioned via the URL prefix `/api/v1/`. The `NinjaExtraAPI` instance is configured in `api/views.py` with `title="Sattabase API"`, `version="1.0.0"`, and `csrf=False` (JWT-based auth renders CSRF tokens unnecessary). All controller classes are registered with route prefixes that define their namespace:

| Controller | Route Prefix | Auth | Tags |
|---|---|---|---|
| `AuthController` | `/auth` | None (public) | Auth |
| `UserController` | `/users` | JWT required | Users |
| `BillingPublicController` | `/billing` | None (public) | Billing — Public |
| `BillingProtectedController` | `/billing` | JWT or API Key | Billing — Protected |
| `BillingAdminController` | `/billing/admin` | JWT + staff | Billing — Admin |
| `BillingWebhookController` | `/billing` | Signature verification | Billing — Webhooks |
| `AdminProductController` | `/admin/products` | JWT + staff | Admin — Products |
| `AdminSubscriptionController` | `/admin/subscriptions` | JWT + staff | Admin — Subscriptions |
| `AdminUserController` | `/admin/users` | JWT + staff | Admin — Users |
| `AdminMetricsController` | `/admin/metrics` | JWT + staff | Admin — Metrics |
| `AdminApiKeyController` | `/admin/api-keys` | JWT + staff | Admin — API Keys |

Controllers are auto-discovered after the Django app registry is loaded. The four admin controllers that live outside the standard `controllers.py` naming convention (`admin_controller.py`, `admin_subscription_controller.py`, `admin_user_controller.py`, `admin_metrics_controller.py`) are explicitly imported in `api/views.py` before `api.auto_discover_controllers()` is called, ensuring they are registered correctly.

## 9.2 Public Endpoints

Public endpoints require no authentication and expose read-only product/plan information for marketing pages and the registration flow.

**`GET /billing/products`** — Lists all active products ordered by name. Returns a list of `ProductOutputSchema` objects.

**`GET /billing/products/{slug}`** — Returns a product with its plans and service domains. Accepts an optional `?currency=` query parameter to convert plan prices using stored exchange rates. If the currency parameter is provided, the `convert_plan_prices()` function from `currency_service.py` is called to translate prices from the plan's base currency to the requested currency. Returns `ProductDetailSchema` with nested plans and domains.

**`GET /auth/choices`** — Returns available timezone, currency, and language choices for registration forms. Labels are explicitly cast to `str` to resolve Django's lazy translation proxies.

**`POST /auth/register`** — Creates a new user account. Rate limited (5 attempts per hour). Sends an email verification OTP after successful registration.

**`POST /auth/login`** — Authenticates a user with email and password. Returns JWT access token in the response body and sets the refresh token in an `sb_refresh_token` httpOnly cookie. Enforces account lockout after excessive failed attempts.

**`POST /auth/token/refresh`** — Standard refresh token exchange. Accepts a refresh token in the request body.

**`POST /auth/token/refresh-cookie`** — Cookie-based refresh. Reads the refresh token from the `sb_refresh_token` httpOnly cookie. This is the endpoint used by the Astro middleware and the frontend API client for automatic session renewal.

**`POST /auth/token/verify`** — Verifies that a token is valid and not blacklisted.

**`POST /auth/token/blacklist`** — Blacklists a refresh token, preventing further use. Called during logout.

**`POST /auth/password-reset/request`** — Sends a password reset OTP to the user's email.

**`POST /auth/password-reset/confirm`** — Confirms a password reset with the OTP and new password.

**`POST /auth/verify-email`** — Verifies a user's email address with an OTP code.

**`POST /auth/authorize`** — Generates a one-time authorization code for cross-domain SSO. Requires a valid JWT. The code expires in 30 seconds and can only be used once.

**`POST /auth/token/exchange`** — Exchanges an authorization code for JWT tokens. Rate limited (10 attempts per 60 seconds). Returns only the access token in the response body; the refresh token is set in an httpOnly cookie.

## 9.3 Protected Endpoints (JWT)

Protected endpoints require a valid JWT Bearer token in the `Authorization` header. Mutation endpoints additionally require email verification.

**`GET /billing/auth/me`** — Enhanced auth/me endpoint returning user profile, subscription info, and a domain-specific access map. This is the primary endpoint used by sister domain SDKs. Accepts both JWT Bearer tokens (frontend) and `X-API-Key` headers (SDK) via the `IsAuthenticatedOrService` permission. Domain resolution priority: (1) service credential's domain from API key, (2) `X-Service-Domain` header, (3) none (returns plain profile). Checks `user.is_active` and `user.is_deleted` before returning data — deactivated/deleted accounts receive 401 with specific error codes for SDK force-logout signaling.

**`GET /billing/subscriptions`** — Lists all subscriptions for the authenticated user.

**`GET /billing/subscriptions/{product_slug}`** — Returns subscription detail for a specific product.

**`POST /billing/subscriptions/{product_slug}/checkout`** — Creates a Stripe Checkout session for subscribing to a plan. Requires email verification.

**`POST /billing/subscriptions/{product_slug}/cancel`** — Cancels a subscription. Follows the Stripe-first pattern: calls Stripe API first, then updates the local DB. Requires email verification.

**`POST /billing/subscriptions/{product_slug}/reactivate`** — Reactivates a canceled subscription that hasn't yet reached its period end. Requires email verification.

**`POST /billing/subscriptions/{product_slug}/change-plan`** — Changes the subscription plan with proration preview. Two-step flow: (1) preview the change, (2) confirm. Requires email verification.

**`POST /billing/portal`** — Creates a Stripe Customer Portal session for self-service billing management.

**`GET /users/me`** — Returns the authenticated user's profile.

**`PUT /users/me`** — Updates the authenticated user's profile (name, phone, timezone, currency, language, avatar).

**`POST /users/me/change-password`** — Changes the user's password. Requires current password verification.

**`POST /users/me/change-email`** — Initiates an email change. Sends a confirmation OTP to the new email.

## 9.4 Admin Endpoints

All admin endpoints require JWT authentication with `is_staff=True`. Write endpoints are rate-limited to 30 requests per minute; read endpoints to 120 per minute. Every mutation is audit-logged via `@log_admin_access` or explicit `write_credential_audit()` calls.

**Products & Domains** (`/admin/products`):

| Method | Path | Description |
|---|---|---|
| POST | `/admin/products` | Create product |
| GET | `/admin/products` | List products (paginated) |
| GET | `/admin/products/{id}` | Product detail |
| PUT | `/admin/products/{id}` | Update product |
| PATCH | `/admin/products/{id}/toggle` | Activate/deactivate |
| DELETE | `/admin/products/{id}` | Soft-delete |
| POST | `/admin/products/{id}/domains` | Add service domain |
| PUT | `/admin/domains/{id}` | Update domain |
| DELETE | `/admin/domains/{id}` | Remove domain |

**Plans & Access Entries** (`/admin/plans`):

| Method | Path | Description |
|---|---|---|
| POST | `/admin/products/{id}/plans` | Create plan |
| GET | `/admin/products/{id}/plans` | List plans (paginated) |
| GET | `/admin/plans/{id}` | Plan detail with access entries |
| PUT | `/admin/plans/{id}` | Update plan |
| PATCH | `/admin/plans/{id}/toggle` | Toggle is_active |
| PATCH | `/admin/plans/{id}/feature` | Toggle is_featured |
| POST | `/admin/plans/{id}/duplicate` | Duplicate plan |
| DELETE | `/admin/plans/{id}` | Delete plan |
| POST | `/admin/plans/{id}/access-entries` | Create access entry |
| PUT | `/admin/access-entries/{id}` | Update access entry |
| DELETE | `/admin/access-entries/{id}` | Remove access entry |
| POST | `/admin/plans/{id}/access-entries/bulk` | Bulk replace entries |
| GET | `/admin/products/{id}/access-matrix` | Feature matrix view |

**Subscriptions** (`/admin/subscriptions`):

| Method | Path | Description |
|---|---|---|
| GET | `/admin/subscriptions` | List (paginated, filterable) |
| GET | `/admin/subscriptions/{id}` | Detail with access map |
| PATCH | `/admin/subscriptions/{id}/override` | Override plan/status |
| PATCH | `/admin/subscriptions/{id}/cancel` | Force cancel |
| PATCH | `/admin/subscriptions/{id}/expire` | Force expire |
| PATCH | `/admin/subscriptions/{id}/extend` | Extend period |
| GET | `/admin/subscriptions/{id}/plan-changes` | Plan history (paginated) |
| GET | `/admin/subscriptions/{id}/invoices` | Invoices (paginated) |
| GET | `/admin/subscriptions/{id}/refunds` | Refunds (paginated) |

**Users** (`/admin/users`):

| Method | Path | Description |
|---|---|---|
| GET | `/admin/users` | List users (paginated, filterable) |
| GET | `/admin/users/{id}` | User detail |
| PATCH | `/admin/users/{id}/status` | Activate/deactivate |
| PATCH | `/admin/users/{id}/role` | Change role |
| GET | `/admin/users/{id}/audit` | User audit trail (paginated) |

**Refunds** (`/admin/refunds`):

| Method | Path | Description |
|---|---|---|
| GET | `/admin/refunds` | List refunds (paginated, filterable) |
| PATCH | `/admin/refunds/{id}/approve` | Approve (two-person rule) |
| PATCH | `/admin/refunds/{id}/reject` | Reject |

**Metrics** (`/admin/metrics`):

| Method | Path | Description |
|---|---|---|
| GET | `/admin/metrics/overview` | MRR, churn, trial conversion |
| GET | `/admin/metrics/revenue` | Revenue by product/plan/month |
| GET | `/admin/metrics/subscriptions` | Subscription funnel |
| GET | `/admin/metrics/products` | Per-product metrics |

**Other Admin Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | `/admin/audit-log` | Admin action log (paginated) |
| GET | `/admin/webhooks` | List webhook events (paginated) |
| POST | `/admin/webhooks/{id}/retry` | Retry failed webhook |
| GET | `/admin/bank-settings` | List bank accounts |
| POST | `/admin/bank-settings` | Create bank account |
| PUT | `/admin/bank-settings/{id}` | Update bank account |
| PATCH | `/admin/bank-settings/{id}/toggle` | Toggle active status |
| DELETE | `/admin/bank-settings/{id}` | Delete bank account |

## 9.5 SDK Endpoints (API Key)

SDK endpoints are those that accept API key authentication via the `X-API-Key` and `X-Service-Domain` headers. They use the `IsAuthenticatedOrService` permission class, which allows either JWT or API key auth.

**`GET /billing/auth/me`** — The primary SDK endpoint. When called with API key headers, returns user profile, subscription status, and the domain-specific access map for the product associated with the credential's service domain. The middleware has already validated the API key and attached `request.service_credential` and `request.service_domain_from_key`, so the controller uses the credential's domain directly for subscription resolution.

**`GET /billing/products`** — Publicly accessible, but also available via API key. SDK clients can use this to fetch the product catalog.

**`GET /billing/products/{slug}`** — Returns product detail with plans. SDK clients use this to present plan information to users on the sister domain.

## 9.6 Webhook Endpoint (Stripe)

**`POST /billing/webhooks/stripe`** — Receives webhook events from Stripe. No JWT auth is used; instead, the endpoint verifies the `Stripe-Signature` header using `STRIPE_WEBHOOK_SECRET`. The endpoint is rate-limited (100 requests per 60 seconds) to prevent DoS from fake events. After signature verification, the event is recorded in `WebhookEventLog` (idempotent — duplicate event IDs are skipped), then routed to the appropriate handler in `billing/stripe/webhooks/handlers/`. This is the safety net that keeps the local DB in sync with Stripe for events initiated outside the system (e.g., customer cancels via Stripe Portal, Stripe auto-cancels for failed payment after retries).

## 9.7 Error Response Format

All API errors follow a consistent JSON envelope format, defined by the exception handlers registered in `api/views.py`.

**Standard Error Envelope:**

```json
{
  "detail": "Human-readable error message",
  "code": "machine_readable_code"
}
```

**Validation Error Envelope (422 from Pydantic):**

```json
{
  "detail": "Validation error",
  "errors": [
    { "field": "email", "message": "Enter a valid email address." }
  ],
  "code": "validation_error"
}
```

**Custom Exception Classes** (`common/exceptions.py`):

| Exception | Status | Code | Description |
|---|---|---|---|
| `BadRequestException` | 400 | `bad_request` | Invalid or malformed request data |
| `UnauthorizedException` | 401 | `unauthorized` | Authentication required but not provided |
| `AccountInactiveException` | 401 | `account_inactive` | Account deactivated by admin (SDK force-logout signal) |
| `AccountDeletedException` | 401 | `account_deleted` | Account soft-deleted (SDK permanent force-logout signal) |
| `ForbiddenException` | 403 | `forbidden` | Insufficient permissions |
| `AccountNotActiveException` | 403 | `account_not_active` | Email not verified |
| `NotFoundException` | 404 | `not_found` | Requested resource not found |
| `ConflictException` | 409 | `conflict` | Request conflicts with current state |
| `TooManyRequestsException` | 429 | `too_many_requests` | Rate limit exceeded |

**API Key Middleware Errors** (returned directly by middleware, before controller execution):

| Status | Code | Description |
|---|---|---|
| 400 | `missing_service_domain` | `X-API-Key` present but `X-Service-Domain` header missing |
| 403 | `invalid_api_key_format` | Key doesn't start with `sb_live_` |
| 403 | `api_key_forbidden` | No credential found for the hashed key |
| 403 | `api_key_revoked` | Credential's `is_active` is False |
| 403 | `service_domain_inactive` | Domain's `is_active` is False |
| 403 | `domain_mismatch` | `X-Service-Domain` header doesn't match the key's bound domain |

**Catch-All Handler** (500): Any truly unexpected exception is caught by the `unhandled_exception_handler`, which logs the full traceback and returns `{"detail": "An unexpected error occurred. Please try again.", "code": "server_error"}` without exposing internal details.

## 9.8 Pagination Convention

All list endpoints use a consistent pagination format implemented by the `get_paginated_data()` and `get_paginated_data_async()` functions in `common/utils.py`.

**Request Parameters** (via `PaginationInput` schema):

| Parameter | Type | Default | Description |
|---|---|---|---|
| `page` | int | 1 | Current page number (1-indexed) |
| `page_size` | int | 20 | Items per page |

**Response Format:**

```json
{
  "meta": {
    "total_items": 142,
    "total_pages": 8,
    "current_page": 1,
    "page_size": 20,
    "has_next": true,
    "has_previous": false
  },
  "results": [...]
}
```

**Implementation Details:**

- Pages are clamped to valid range (1 to `total_pages`).
- The async version uses `queryset.acount()` and async iteration (`aiterator()`) to avoid blocking the event loop.
- The sync version uses standard `queryset.count()` and slice evaluation.
- All paginated responses are wrapped in `PaginatedResponse[T]` generic schema.

## 9.9 Rate Limit Headers & Behavior

Rate limiting is implemented using a sliding window algorithm (`common/rate_limit.py`) with Redis-backed timestamp storage.

**How It Works:**

Each rate limit bucket stores a list of timestamps in Redis under `rl:{key}`. On each check, timestamps outside the window are pruned, and the remaining count is compared against `max_attempts`. If the limit is exceeded, `TooManyRequestsException` (429) is raised.

**Rate Limit Categories:**

| Category | Default Limit | Window | Scope |
|---|---|---|---|
| Sensitive actions (cancel, checkout, change-plan) | 5 requests | 1 hour | Per user + IP |
| Admin write | 30 requests | 1 minute | Per admin user + IP |
| Admin read | 120 requests | 1 minute | Per admin user + IP |
| Registration | 5 requests | 1 hour | Per IP |
| Token exchange (SSO) | 10 requests | 1 minute | Per IP |
| Webhook (Stripe) | 100 requests | 1 minute | Per IP |
| SDK traffic | 1000 requests | 1 hour | Per API key prefix |

**SDK vs. Browser Rate Limiting:**

When a valid `X-API-Key` is present, the rate limit bucket switches from per-IP to per-API-key-prefix (e.g., `sdk:sb_live_a1Bc`). This prevents a sister domain backend that proxies many users through a single IP from exhausting the shared bucket. SDK traffic also uses higher default limits (`RATE_LIMIT_SDK_ATTEMPTS`/`RATE_LIMIT_SDK_WINDOW`) because server-to-server traffic is inherently more voluminous than individual browser sessions.

**Trusted Proxy Configuration:**

The `get_client_ip()` function only trusts `X-Forwarded-For` when the connecting IP (`REMOTE_ADDR`) is in `settings.TRUSTED_PROXIES` (defaults to loopback only). This prevents clients from spoofing the header to bypass rate limiting. CIDR ranges are supported (e.g., `10.0.0.0/8`).

---

# 10. Celery Tasks & Background Jobs

## 10.1 Celery Configuration

SattaBase uses Celery 5.6.3 as its distributed task queue, with Redis serving as both the message broker and the cache backend. The Celery app is defined in `base/celery.py` and automatically loaded when Django starts via `base/__init__.py`, which imports the Celery app instance at module level. This ensures that Celery is always available regardless of how Django is invoked (management commands, WSGI, ASGI, or standalone worker).

The Celery configuration is driven by settings in `base/settings.py` with the `CELERY_` namespace prefix. The key configuration values are:

| Setting | Value | Purpose |
|---|---|---|
| `CELERY_BROKER_URL` | `redis://{REDIS_HOST}:{REDIS_PORT}/1` | Redis DB 1 for message broker |
| `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP` | `True` | Auto-retry broker connection on worker startup |
| `CELERY_BEAT_SCHEDULER` | `django_celery_beat.schedulers:DatabaseScheduler` | Database-backed beat schedule (admin-editable) |
| `CELERY_RESULT_BACKEND` | `django-db` | Store task results in Django ORM via django-celery-results |
| `CELERY_RESULT_EXTENDED` | `True` | Store extended result metadata (args, kwargs, worker name) |
| `CELERY_CACHE_BACKEND` | `default` | Use Django's Redis cache for Celery's internal caching |
| `CELERY_TASK_TIME_LIMIT` | `30 * 60` (30 minutes) | Hard time limit per task before worker terminates it |
| `CELERY_TASK_TRACK_STARTED` | `True` | Report task start state for monitoring |
| `CELERY_TIMEZONE` | `UTC` | All task scheduling in UTC |

The `base/celery.py` file also sets two additional worker-level flags directly on the app instance: `task_track_started = True` and `worker_send_task_events = True`, which enable real-time task monitoring through tools like Flower. Task autodiscovery is enabled via `app.autodiscover_tasks()`, which scans all `INSTALLED_APPS` for `tasks.py` modules — currently finding tasks in `billing/tasks.py` and `common/tasks.py`.

The beat schedule is defined directly in `base/celery.py` using `app.conf.beat_schedule`, which provides a declarative configuration of all periodic tasks. Because the `django_celery_beat` database scheduler is used, these schedule entries are also visible and editable through the Django admin interface, allowing operators to temporarily disable or reschedule tasks without redeploying.

## 10.2 Scheduled Tasks (Beat)

SattaBase defines **8 scheduled Celery Beat tasks** that run on fixed schedules. All times are in UTC. The schedule is designed so that dependent tasks run in the correct order: exchange rates are fetched before customer data sync, revenue is recognized before dunning, and credit consumption runs after revenue recognition.

| Task | Schedule | Source Module | Purpose |
|---|---|---|---|
| `recognize_revenue` | Daily at 02:30 UTC | `billing/tasks.py` | ASC 606 daily revenue recognition |
| `update_exchange_rates` | Daily at 03:00 UTC | `billing/tasks.py` | Fetch and cache currency exchange rates |
| `sync_customer_data` | Daily at 03:30 UTC | `billing/tasks.py` | Sync Stripe customer profile changes to local DB |
| `dunning_retry` | Daily at 04:00 UTC | `billing/tasks.py` | Process past-due subscriptions through staged dunning |
| `consume_credit_periods` | Daily at 05:00 UTC | `billing/tasks.py` | Consume billing periods from active credit pools |
| `expire_credit_pools` | Daily at 05:30 UTC | `billing/tasks.py` | Mark credit pools past their expiry date |
| `reconcile_webhooks` | Every 6 hours (00:00, 06:00, 12:00, 18:00) | `billing/tasks.py` | Retry failed Stripe webhook events |
| `cleanup_stale_webhook_events` | Weekly Sunday at 05:00 UTC | `billing/tasks.py` | Delete processed webhook events older than 90 days |

### Revenue Recognition (`recognize_revenue`)

This task creates daily `RevenueRecognitionEntry` records for each active (non-past-due) subscription. The daily revenue amount is calculated as `plan.price_cents / days_in_billing_period`, using ceiling division to avoid cent loss. On the last day of each billing period, the amount is adjusted to capture any remaining cents lost to rounding on prior days, with a `max(0, ...)` guard to prevent negative values when price_cents is extremely low relative to the period length.

A critical design decision (MED-05 fix) excludes `PAST_DUE` subscriptions from revenue recognition, consistent with ASC 606 principles that revenue should only be recognized when payment collection is probable. When a past-due subscription's payment succeeds (via `invoice.payment_succeeded` webhook), revenue is recognized retroactively for the gap period. The task uses `bulk_create` with `ignore_conflicts=True` and a `UniqueConstraint` on `(subscription, recognized_date)` to ensure idempotency — if the task runs twice for the same date, duplicate entries are silently skipped.

### Dunning Workflow (`dunning_retry`)

The dunning task implements a four-stage escalation workflow for past-due subscriptions. Each subscription tracks its current `dunning_step` and `last_dunning_email_at` to prevent duplicate actions. The stages are:

1. **Day 3 — `email_reminder`**: Friendly payment reminder with a link to the Stripe Customer Portal. The email uses a professional template that acknowledges the payment may have failed due to an expired card and provides clear instructions for updating payment information.

2. **Day 5 — `email_urgent`**: Stronger-language email warning that access will be suspended in 2 days if payment is not resolved. The tone shifts from helpful to urgent, emphasizing the imminent service interruption.

3. **Day 7 — `restrict_access`**: Silent flagging of the subscription for access restriction. No email is sent at this stage. The `is_effectively_active()` method on the Subscription model returns `False` for past-due subscriptions after their `current_period_end`, which sister domains should check via the `auth/me` endpoint.

4. **Day 14 — `cancel_subscription`**: Automatic cancellation of the subscription on Stripe. If the Stripe cancellation succeeds, the local status is set to `CANCELED`. If it fails, the dunning step is **not** advanced (MED-04/HIGH-02 fix), so the task will retry cancellation on the next daily run. Previously, the step was always advanced even on failure, causing subscriptions to be stuck in a "cancelled" dunning step without actually being cancelled on Stripe.

The `past_due_at` timestamp (not `updated_at`) is used to calculate days past due (MED-04 fix), because `updated_at` advances on every model save — including saves from the dunning task itself — which artificially kept `days_past_due` low and delayed escalation. A minimum interval of 24 hours between dunning emails (`DUNNING_EMAIL_MIN_INTERVAL_HOURS`) prevents spam if the task runs multiple times in a day.

### Exchange Rate Updates (`update_exchange_rates`)

Delegates to `currency_service.update_exchange_rates()`, which fetches rates from the open.er-api.com API with automatic fallback to frankfurter.app. Rates are upserted into the `ExchangeRate` table using `update_or_create`, so the command is idempotent. This task must run before `sync_customer_data` (03:30 UTC) so that currency conversion during the sync uses the latest rates.

### Customer Data Sync (`sync_customer_data`)

Iterates over all subscriptions with a Stripe customer ID and calls `sync_stripe_customer_data()` for each, pulling the latest email, name, and currency from Stripe. This is critical for data integrity when users update their profile via the Stripe Customer Portal — if the `customer.updated` webhook was missed, this task ensures the changes propagate within 24 hours.

### Credit Period Consumption (`consume_credit_periods`)

For each active credit pool where `current_period_end` has passed, this task consumes one billing period: it decrements the pool's remaining credit count, advances the period dates, and creates a `CreditTransaction` record. If no periods remain, the pool status transitions to `exhausted`. The task uses `select_for_update()` within `transaction.atomic()` (CRIT-04 fix) to prevent race conditions when multiple workers or overlapping task runs attempt to process the same pool simultaneously.

### Credit Pool Expiry (`expire_credit_pools`)

Marks credit pools as `expired` when their `expires_at` timestamp has passed. This is a simple batch update that transitions pools from `active` to `expired` status, preventing further credit consumption. Pools that are already `exhausted` or `canceled` are not affected.

### Webhook Reconciliation (`reconcile_webhooks`)

Retries Stripe webhook events that were recorded in `WebhookEventLog` but failed during processing. Runs every 6 hours and only retries events within a configurable time window (`max_age_hours=24` by default). This provides a safety net for transient failures — if a webhook handler throws an exception, the event is logged with `processed=False` and will be retried on the next reconciliation run.

### Stale Webhook Cleanup (`cleanup_stale_webhook_events`)

Deletes `WebhookEventLog` entries that have been successfully processed (`processed=True`) and are older than the retention period (default 90 days). This prevents the table from growing unboundedly, as each event stores several kilobytes of JSON payload. Runs weekly on Sunday at 05:00 UTC.

## 10.3 On-Demand Tasks

In addition to the scheduled Beat tasks, SattaBase defines on-demand tasks that are triggered by user actions or system events rather than a fixed schedule.

### Credit Request Email Notifications

Two email tasks are dispatched when an admin approves or rejects a credit purchase request:

- **`send_credit_request_approved_email`** (`billing/tasks.py`): Sends a professional HTML confirmation email to the user with their credit pool details, invoice number, billing periods, and action buttons linking to the credits dashboard and transactions page. The email includes a styled card with product name, plan, amount, periods, invoice number, and payment method. A plain-text fallback is provided for email clients that do not support HTML.

- **`send_credit_request_rejected_email`** (`billing/tasks.py`): Sends a rejection notification email with a red "Not Approved" badge and, if provided, a highlighted reason section explaining why the request was denied. The email includes a "Submit New Request" button linking back to the credit request page.

Both tasks use `max_retries=3` with a 60-second default retry delay. They are dispatched via `.delay()` from the admin approval/rejection controllers, ensuring that email delivery failures do not block the HTTP response.

### Credential Webhook Delivery (`deliver_credential_webhook`)

Defined in `common/tasks.py`, this task delivers HMAC-signed HTTP POST requests to sister domain webhook URLs when a `ServiceCredential` is revoked or rotated. The dispatch is initiated by `common/webhooks.dispatch_credential_webhook()`, which builds the payload and queues the Celery task without blocking the caller.

The delivery uses the `requests` library with a 10-second timeout. Response handling follows a three-tier strategy:

- **2xx success**: Task completes successfully, returning a `{"status": "delivered"}` result.
- **4xx client error**: Task completes without retry — the URL or payload is likely wrong, and retrying will not help. Returns `{"status": "client_error"}`.
- **5xx server error, timeout, or connection error**: Task retries with exponential backoff (1 minute, 2 minutes, 4 minutes), up to a maximum of 3 attempts.

Every payload is signed with HMAC-SHA256 using the domain's `webhook_secret`, and the signature is sent in the `X-Satta-Signature` header. A `X-Satta-Timestamp` header is included for replay attack protection (receivers should reject payloads older than 5 minutes).

## 10.4 Task Monitoring & Error Handling

### Task Result Storage

SattaBase uses `django-celery-results` with the `django-db` result backend, which stores task execution results in the Django ORM (`celery_results.TaskResult` model). With `CELERY_RESULT_EXTENDED = True`, each result record includes the task name, arguments, keyword arguments, worker name, result payload, and traceback on failure. This allows operators to inspect task outcomes through the Django admin interface without needing external monitoring tools.

### Retry Strategy

All tasks use the `bind=True` parameter, which passes the task instance (`self`) as the first argument, enabling `self.retry()` calls. The retry configuration varies by task:

| Task | Max Retries | Retry Delay | Rationale |
|---|---|---|---|
| `reconcile_webhooks` | 2 | 5 min | Webhook reconciliation is non-urgent; failures will be retried on next 6-hour cycle |
| `sync_customer_data` | 2 | 10 min | Customer sync is important but not time-critical |
| `dunning_retry` | 2 | 10 min | Dunning actions must complete; retry with moderate delay |
| `update_exchange_rates` | 3 | 5 min | Exchange rates are critical for correct pricing; extra retries justified |
| `recognize_revenue` | 2 | 10 min | Revenue recognition is idempotent; failures are retried next day anyway |
| `cleanup_stale_webhook_events` | 2 | 10 min | Cleanup is purely maintenance; low urgency |
| Credit email tasks | 3 | 1 min | Email delivery is user-facing; fast retries minimize notification delay |
| `deliver_credential_webhook` | 3 | 1 min (exponential) | Webhook delivery is security-sensitive; fast initial retry with exponential backoff |

### Error Logging Convention

All tasks follow a consistent error logging pattern: they log the task name, relevant identifiers (subscription ID, user email, credential ID), and the exception with `exc_info=True` for full tracebacks. Success logs include summary statistics (counts of processed, synced, created, etc.). This convention makes it straightforward to grep the application logs for task-specific issues.

### Task Idempotency

Several tasks are designed to be safely re-runnable without side effects:

- `recognize_revenue` uses `bulk_create` with `ignore_conflicts=True` and a `UniqueConstraint` on `(subscription, recognized_date)`.
- `update_exchange_rates` uses `update_or_create` for each rate, so duplicate runs simply update the existing rate.
- `dunning_retry` only advances `dunning_step` when the action succeeds, and the `dunning_step < step_num` check prevents re-execution of already-completed steps.
- `consume_credit_periods` uses `select_for_update()` within `transaction.atomic()` to prevent double-consumption from overlapping runs.
- `cleanup_stale_webhook_events` only deletes processed events, so re-running it is a no-op if the first run succeeded.

## 10.5 Redis as Broker & Cache

Redis plays a dual role in the SattaBase architecture, serving as both the Celery message broker and the Django cache backend. The Redis instance runs on port 6379 with three separate databases:

| Redis DB | Purpose | Configuration Key |
|---|---|---|
| DB 0 | Not directly used by application | — |
| DB 1 | Celery message broker | `CELERY_BROKER_URL = redis://.../1` |
| DB 2 | Django cache backend | `CACHES["default"]["LOCATION"] = redis://.../2` |

The cache backend (`django-redis`) is used for several purposes across the application:

- **Rate limiting**: The sliding-window rate limiter in `common/rate_limit.py` stores request counts and timestamps in Redis with TTL-based expiration.
- **CORS origin caching**: The dynamic CORS middleware (`common/cors_middleware.py`) caches the list of active `ServiceDomain` domains in Redis with a configurable TTL, avoiding a database query on every request.
- **API key usage analytics**: The analytics module (`common/analytics.py`) uses Redis sorted sets to track API key usage counts per time window, enabling the admin dashboard to display real-time SDK usage metrics.
- **Celery internal caching**: With `CELERY_CACHE_BACKEND = "default"`, Celery uses the same Redis instance for its own internal caching needs (e.g., broker transport options).

The `CACHE_MIDDLEWARE_SECONDS` setting defaults to 3600 (1 hour), which is the TTL for cached CORS origin lists. Cache keys are namespaced by module to avoid collisions — for example, `satta:cors:domains` for CORS origins and `satta:ratelimit:{key}` for rate limit buckets.

---

# 11. Database & Data Layer

## 11.1 Database Configuration

SattaBase uses PostgreSQL as its production database and SQLite as the development fallback. The configuration is defined in `base/settings.py` and is determined by the `DEBUG` flag:

**Production (PostgreSQL):**
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("SB_DB_NAME"),
        "USER": env("SB_DB_USER"),
        "PASSWORD": env("SB_DB_PASSWORD"),
        "HOST": env("SB_DB_HOST"),
        "PORT": env("SB_DB_PORT"),
    }
}
```

**Development (SQLite fallback):**
When `DEBUG=True` and PostgreSQL environment variables are not configured, Django falls back to SQLite with the database file at `backend/db.sqlite3`. A warning is printed to the console to make the developer aware that they are running in development mode. The SQLite backend is sufficient for local development but lacks support for `select_for_update()` row locking and concurrent writes, which is why all critical locking logic is only tested under PostgreSQL.

The database driver is `psycopg2-binary` (version 2.9.12), which provides the C-optimized PostgreSQL adapter. Connection pooling is not currently implemented — each Django process maintains its own database connections as managed by Django's `CONN_MAX_AGE` setting.

## 11.2 Abstract Base Models

Three abstract base models in `common/models.py` provide common functionality that is inherited by nearly every concrete model in the project. These models follow Django's best practice of using abstract base classes for shared fields rather than model inheritance with concrete tables.

### TimeStampedModel

Provides automatic `created_at` and `updated_at` timestamp fields on every model that inherits from it. The `created_at` field uses `auto_now_add=True` and `db_index=True` (indexed because it is frequently used in range queries for reporting and filtering). The `updated_at` field uses `auto_now=True` and is also indexed. These fields are set as `editable=False` to prevent them from appearing in Django admin forms or being overwritten by bulk update operations.

This model is inherited by virtually every non-trivial model in the billing app: `Subscription`, `CreditPool`, `CreditInvoice`, `Refund`, `RevenueRecognitionEntry`, `CreditPurchaseRequest`, `CreditTransaction`, and `WebhookEventLog`. The User model indirectly inherits it through `SoftDeleteModel`.

### SoftDeleteModel

Implements soft deletion by adding `is_deleted` (BooleanField, default=False, indexed) and `deleted_at` (DateTimeField, null) fields. Instead of permanently removing records from the database, the `soft_delete()` method sets `is_deleted=True` and records the timestamp. The `restore()` method reverses this operation. Currently, the User model is the primary consumer of this pattern — when a user "deletes" their account, the record is soft-deleted to preserve audit trails and foreign key integrity on related billing records.

An important note: the soft-delete pattern is not enforced at the queryset level — there is no default manager that filters out `is_deleted=True` records. Code that queries models inheriting from `SoftDeleteModel` must explicitly filter `.filter(is_deleted=False)` when soft-deleted records should be excluded. This is a deliberate choice to avoid surprising implicit filtering that could hide data from admin queries.

### ActivatorModel

Adds `is_active` (BooleanField, default=True, indexed) and `activated_at` (DateTimeField, null) fields with `activate()` and `deactivate()` convenience methods. This model is used by models that need a simple on/off toggle, such as `Product`, `ServiceDomain`, and `ServiceCredential`. The `activated_at` timestamp records when the model was last activated, which is useful for audit purposes — for example, tracking when a product was re-enabled after being temporarily disabled.

## 11.3 Encrypted Fields

The `billing/fields.py` module provides two custom Django model fields that encrypt data at rest using Fernet symmetric encryption (from the `cryptography` package). These fields are used to protect sensitive data like bank account numbers stored in the `BankSettings` model.

### EncryptedCharField

A `CharField` subclass that transparently encrypts data before saving to the database and decrypts it when loading. The encryption uses Fernet (AES-128-CBC with HMAC-SHA256 for authentication), which provides both confidentiality and integrity guarantees. The `max_length` parameter applies to the decrypted (plaintext) value — the stored encrypted value is longer due to Fernet's overhead (IV, HMAC, version byte, and base64 encoding), so the field automatically sets the database column's `max_length` to 255 to accommodate the encrypted form.

The field implements three key methods:

- **`get_prep_value()`**: Encrypts the value before writing to the database. If the value is `None` or empty string, it is returned as-is (no encryption of null/empty values).
- **`from_db_value()`**: Decrypts the value when loading from the database. If decryption fails (e.g., the data was not encrypted or the key has changed), the value is returned as-is — this provides a graceful migration path from unencrypted to encrypted storage.
- **`to_python()`**: Handles deserialization for form validation and admin display. Values that look like Fernet tokens (starting with `gAAAAAB`) are automatically decrypted; plain text values are returned as-is.

### EncryptedTextField

A `TextField` subclass with identical encryption behavior but without the `max_length` constraint. Used for longer sensitive content that exceeds CharField limits.

### Key Management

The encryption key is derived from the `SB_CRYPTOGRAPHY_KEY` environment variable. If this variable is not set, the key is derived from Django's `SECRET_KEY` using PBKDF2-HMAC-SHA256 with a fixed salt and 100,000 iterations. While the fixed salt is acceptable for development, production deployments **must** set `SB_CRYPTOGRAPHY_KEY` directly to ensure key independence from Django's `SECRET_KEY`. If the key is changed after data has been encrypted, existing records will become unreadable — the `from_db_value()` fallback returns the encrypted ciphertext as-is, which serves as a signal that the key needs to be restored.

## 11.4 Migrations Strategy

The billing app has **25 migrations** (0001 through 0025) that reflect the iterative development of the billing system. The migration history tells the story of the project's evolution:

- **0001–0003**: Core models (Product, Plan, Subscription, WebhookEventLog)
- **0004**: Stripe product ID sync
- **0005**: Trial usage tracking
- **0006**: Tax-inclusive pricing and TOS acceptance
- **0007**: Multi-currency and ExchangeRate model
- **0008**: Dunning support (step, timestamps, email tracking)
- **0009**: Refund system enhancements
- **0010–0012**: Revenue recognition (ASC 606)
- **0013**: Past-due timestamp for accurate dunning day counting
- **0014**: ServiceCredential model for API key authentication
- **0015**: Cancel-at-period-end support
- **0016**: InvoiceLineItem model for detailed invoice breakdown
- **0017**: AdminAuditLog for compliance audit trail
- **0018**: Webhook secret for HMAC-signed credential dispatch
- **0019**: Credit system (CreditPool, CreditInvoice, CreditTransaction, CreditPurchaseRequest)
- **0020–0025**: Credit system refinements, bank settings, and field adjustments

All migrations are forward-only — there are no reverse migrations in production. The migration strategy follows these conventions:

- **No data migrations in production**: Migrations that populate seed data are handled by management commands, not migration files. This keeps migrations focused on schema changes.
- **`default` values on new non-nullable fields**: Every new non-nullable field includes a sensible default value so that the migration can apply without manual intervention on existing data.
- **`SET_NULL` on foreign keys to soft-deleted models**: The `Refund.subscription` field uses `SET_NULL` rather than `CASCADE` so that the audit trail survives subscription deletion. Similarly, `CreditInvoice.credit_pool` uses `SET_NULL` to preserve invoice records after pool expiration.

## 11.5 Seed Data Commands

Two Django management commands provide seed data for development and testing:

### `billing_seed_data`

The primary seed command, located at `common/management/commands/billing_seed_data.py`. It creates a comprehensive set of demo data using `get_or_create` so it is safe to run multiple times — existing records are skipped rather than duplicated. The seed data includes:

- **3 Products**: Satta Finance, Satta Analytics, and Satta Ledger — each with a full plan hierarchy (Free, Standard/Growth, Pro/Enterprise) and detailed access entries that define feature limits per plan.
- **Service Domains**: Each product gets at least one primary domain. Satta Ledger includes both `ledger.sattaspace.com` and `localhost:4322` for local development.
- **Bank Settings**: Three bank accounts (two active, one inactive) for testing the credit purchase bank transfer flow.
- **Credit Data**: Sample pending credit purchase requests and active credit pools per test user.

The command supports two flags: `--clear` to wipe all billing data before re-seeding (irreversible), and `--verbose` to print one line per created record for debugging.

### `seed_exchange_rates`

Located at `common/management/commands/seed_exchange_rates.py`. Fetches live exchange rates from the configured API and upserts them into the `ExchangeRate` table. Accepts an optional `--base` flag to override the base currency for the run (e.g., `--base=EUR`). This command should be run once after initial migration, after which the daily Celery Beat task keeps rates updated automatically.

## 11.6 Query Optimization Patterns

SattaBase employs several Django ORM query optimization patterns to minimize database round-trips and prevent common performance pitfalls. These patterns are consistently applied across controllers, services, and tasks.

### `select_related` for Foreign Key Joins

The most frequently used optimization, `select_related()` performs a SQL JOIN to fetch related objects in a single query instead of requiring separate queries. This is applied wherever a foreign key is accessed in the response serialization:

```python
# billing/services.py — Plan lookup with product join
plan = Plan.objects.select_related("product").get(slug=slug)

# billing/controllers.py — Subscription with plan and product
qs = Subscription.objects.select_related("plan", "product")

# billing/admin_controller.py — Refund list with multiple joins
Refund.objects.select_related(
    "subscription__plan", "subscription__product",
    "initiated_by", "approved_by"
)
```

Without `select_related`, accessing `subscription.plan.name` would trigger an additional query for each subscription in the queryset (the classic N+1 problem). With `select_related`, all the data is fetched in a single SQL query using JOINs.

### `prefetch_related` for Reverse Relations

Used less frequently than `select_related`, but applied in `billing/services.py` for the plan access entries relationship:

```python
from django.db.models import prefetch_related_objects, Prefetch

plan = Plan.objects.select_related("product").get(slug=slug)
prefetch_related_objects([plan], "access_entries")
```

The `prefetch_related_objects()` utility is used instead of the queryset-level `.prefetch_related()` because the plan object may already be loaded from a parent queryset. This function attaches the prefetched data to the existing object without requiring a new queryset evaluation.

### `select_for_update` for Row-Level Locking

The most critical optimization for data integrity, `select_for_update()` issues a `SELECT ... FOR UPDATE` statement that acquires a row-level exclusive lock within a `transaction.atomic()` block. This prevents race conditions when multiple concurrent requests attempt to modify the same record. The pattern is used in every scenario where a read-modify-write cycle must be atomic:

```python
# billing/controllers.py — Safe plan change with lock
with transaction.atomic():
    sub = Subscription.objects.select_related("plan", "product")
        .select_for_update()
        .get(user=user, product__slug=product_slug)

# billing/admin_controller.py — Credit pool operations
pool = CreditPool.objects.select_related("user", "product")
    .select_for_update()
    .aget(pk=credit_id)

# billing/tasks.py — Credit period consumption
active_pools = CreditPool.objects.filter(
    status=CreditPool.CreditPoolStatus.ACTIVE,
    current_period_end__lte=now,
).select_for_update()
```

The `select_for_update()` pattern is especially important in the ASGI-first architecture because Django's async view handlers can process multiple requests concurrently on the same event loop. Without row locking, two concurrent requests could read the same `remaining_credits` value, both decrement it, and one write would be lost — a classic lost-update anomaly.

### `.only()` and `.defer()` for Column Selection

The `sync_customer_data` task uses `.only()` to limit the columns fetched from the database:

```python
subs = Subscription.objects.exclude(stripe_customer_id="")
    .select_related("user")
    .only("user", "stripe_customer_id")
    .distinct("user_id")
```

This reduces memory usage when iterating over large querysets where only a few fields are needed. The `.distinct("user_id")` clause ensures each user is synced only once, even if they have multiple subscriptions.

### `bulk_create` for Batch Inserts

The revenue recognition task uses `bulk_create` with `ignore_conflicts=True` for efficient batch insertion:

```python
RevenueRecognitionEntry.objects.bulk_create(
    batch,
    ignore_conflicts=True,
)
```

This creates all revenue entries in a single SQL statement rather than issuing individual INSERT statements, which dramatically improves performance when recognizing revenue for hundreds or thousands of subscriptions. The `ignore_conflicts=True` flag handles the idempotency requirement — if an entry already exists for a given `(subscription, recognized_date)` pair, it is silently skipped.

### `update_fields` for Partial Updates

Throughout the codebase, model saves use `update_fields` to avoid overwriting unrelated columns:

```python
sub.dunning_step = step_num
sub.save(update_fields=["dunning_step", "updated_at"])
```

This pattern serves two purposes: it reduces the SQL UPDATE statement to only the changed columns (minor performance improvement), and more importantly, it prevents accidentally overwriting concurrent changes to other fields on the same model. For example, if a dunning task updates `dunning_step` while a webhook handler updates `status`, using `update_fields` ensures neither write clobbers the other's changes.

---

# 12. Security Architecture

SattaBase implements a defense-in-depth security model with multiple overlapping layers that protect against common web application vulnerabilities. Security controls are woven throughout the entire stack — from middleware-level request interception to schema-level input validation, from encrypted data storage to comprehensive audit logging. This section catalogs each security mechanism, explains its rationale, and references the specific code that implements it. Many of these controls were introduced as explicit fixes for identified security findings (e.g., HIGH-03, AUTH-1, CRIT-02), and the original finding identifiers are preserved in both code comments and this documentation for traceability.

## 12.1 Authentication Security

SattaBase's authentication system is built on a hybrid JWT + httpOnly cookie architecture that addresses both XSS and CSRF attack vectors simultaneously. The design reflects lessons learned from several security audit findings (HIGH-03, AUTH-1, AUTH-2, AUTH-4, CRIT-01).

**JWT Token Pair with httpOnly Cookie Storage (HIGH-03 / AUTH-1)**

When a user logs in via `POST /api/v1/auth/login`, the backend generates a JWT access token and a JWT refresh token. The access token is returned in the JSON response body and stored in memory on the frontend (never in localStorage). The refresh token, however, is set exclusively in an httpOnly cookie named `sb_refresh_token` and is never exposed in the response body. This is the HIGH-03 / AUTH-1 fix: previously both tokens were returned as JSON, which meant that an XSS attack could steal the refresh token from the response object. By storing the refresh token in an httpOnly cookie, JavaScript running on the page cannot read it, eliminating the most common XSS-based token theft vector.

The cookie settings are environment-adaptive via the `_get_cookie_settings()` helper:

- **Development** (`DEBUG=True`): `SameSite=Lax`, `Secure=False`. Since both frontend (localhost:4321) and backend (localhost:8086) share the same registrable domain (localhost), `SameSite=Lax` allows cookies on cross-port POST requests. `Secure=False` is required because browsers reject `Secure=True` cookies over plain HTTP.
- **Production** (`DEBUG=False`): `SameSite=None`, `Secure=True`. Required for cross-domain setups where the frontend and backend run on different subdomains (e.g., `app.example.com` → `api.example.com`). `SameSite=None` mandates `Secure=True` per browser specification.

The "Remember Me" functionality controls cookie persistence: when enabled, the cookie expires after 30 days; when disabled, it is a session cookie that expires when the browser closes.

**Token Rotation with Grace Period**

The cookie-based refresh endpoint (`POST /api/v1/auth/token/refresh-cookie`) rotates the refresh token on every successful refresh — issuing a new refresh token with a fresh expiry. However, the old refresh token is intentionally NOT blacklisted on rotation. This design decision prevents race conditions caused by Astro View Transitions, HMR, and multiple browser tabs that may issue concurrent refresh requests. If the old token were blacklisted immediately, any concurrent tab still using the old cookie would receive a 401 and be logged out. Instead, the old token expires naturally based on its JWT TTL (7 days), providing a grace period during which concurrent tabs can still refresh successfully.

Tokens ARE blacklisted on explicit logout, which is the correct point for immediate revocation. This trade-off is acceptable because the httpOnly cookie is not accessible to JavaScript, `SameSite` settings provide CSRF resistance, and the natural expiration limits the damage window.

**Token Reuse Detection (AUTH-4 / MED-02)**

When a blacklisted refresh token is presented to the cookie-based refresh endpoint, it signals a potential security breach — the legitimate user has already logged out (which blacklists their token), but someone else is still using the old cookie. The AUTH-4 fix implements forensic logging and emergency response:

1. The system logs a `SECURITY_ALERT` with the user ID, client IP, user agent, and error details.
2. It decodes the token payload (without full validation) to extract the user ID for forensic purposes.
3. It blacklists ALL outstanding refresh tokens for the affected user, limiting the damage window to only the current access token's remaining lifetime.

**Logout CSRF Protection (AUTH-2)**

The logout endpoint (`POST /api/v1/auth/logout`) validates that the caller possesses a valid refresh token in the httpOnly cookie before processing the logout. Previously, the endpoint was completely unauthenticated — any POST request, including CSRF attacks from a malicious site, would clear the user's cookies and blacklist their refresh token (a forced-logout vulnerability). Now, without a valid refresh cookie, the endpoint returns 401 and does not blacklist anything, preventing CSRF-based forced logout attacks.

**Account Lockout (CRIT-02)**

The `User` model includes `failed_login_attempts` and `locked_until` fields that implement progressive account lockout. After 5 consecutive failed login attempts (configurable via `max_attempts` parameter), the account is locked for 30 minutes. The `is_account_locked()` method checks whether the current time is before `locked_until`. On successful login, `reset_failed_login_attempts()` clears the counter. The lockout is enforced in `AuthService.aauthenticate_user()` before the password check, so a locked account cannot be probed further even with correct credentials.

**Login History Tracking**

Every successful login creates a `UserLoginHistory` record with the IP address and user agent string. This provides a forensic trail for detecting unauthorized access, anomalous login patterns, and supporting incident response investigations.

## 12.2 CSRF Protection

SattaBase disables Django's built-in CSRF protection at the API level (`csrf=False` on the `NinjaExtraAPI` instance in `api/views.py`). This is intentional and correct because the application uses JWT-based authentication, not Django's session-based authentication. Django's CSRF middleware protects against cross-site request forgery for session-cookie-authenticated requests, but SattaBase's API endpoints authenticate via the `Authorization: Bearer <token>` header, which is not automatically included in cross-origin requests by browsers. An attacker's website cannot read or inject a Bearer token into a cross-origin request because of same-origin policy restrictions on JavaScript.

The cookie-based refresh token (`sb_refresh_token`) does use cookies, which could theoretically be sent cross-origin. However, this is mitigated by the `SameSite` attribute:

- In development (`SameSite=Lax`): The cookie is only sent on top-level navigations and same-site POST requests, not on cross-site `fetch()` calls.
- In production (`SameSite=None`): The cookie can be sent cross-origin, but the refresh endpoint validates the token's authenticity and expiry. A CSRF attacker cannot read the response (which contains the new access token), making the attack pointless — they would only refresh the victim's token without gaining access to it.

For production deployments, the following Django security settings are enabled when `DEBUG=False`:

```python
CSRF_COOKIE_SECURE = True       # CSRF cookie only sent over HTTPS
SESSION_COOKIE_SECURE = True    # Session cookie only sent over HTTPS
SECURE_HSTS_SECONDS = 31536000  # 1-year HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True      # Redirect HTTP → HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

The `CSRF_TRUSTED_ORIGINS` setting includes the frontend URL and any additional origins configured via the `SB_CSRF_TRUSTED_ORIGINS` environment variable. The frontend URL is automatically added to ensure it is always trusted.

## 12.3 CORS Security

Cross-Origin Resource Sharing is managed through a two-layer system: the standard `django-cors-headers` package handles static origin configuration, while the custom `service_domain_cors_middleware` provides dynamic origin resolution based on the `ServiceDomain` database table.

**Static CORS Configuration**

In `base/settings.py`, CORS is configured with `CORS_ALLOW_CREDENTIALS = True` (required for httpOnly cookie-based auth) and `CORS_ALLOW_ALL_ORIGINS = False` (HIGH-03 fix — `Access-Control-Allow-Origin: *` is incompatible with `Access-Control-Allow-Credentials: true`). The allowed origins are loaded from the `SB_CORS_ALLOWED_ORIGINS` environment variable, and the frontend URL is always appended automatically.

**Dynamic CORS Middleware**

The `service_domain_cors_middleware` (`common/cors_middleware.py`) extends the static configuration by dynamically allowing origins from the `ServiceDomain` table. This eliminates the need to manually update `CORS_ALLOWED_ORIGINS` every time a new sister domain is registered. The middleware checks the `Origin` header on every request and, if it matches an active `ServiceDomain.domain` or the configured `FRONTEND_URL`, injects the necessary CORS headers directly into the response.

Key security properties of the dynamic CORS system:

- **Exact-match only**: No wildcards are used. The origin must match a registered domain exactly.
- **Active domains only**: Only `ServiceDomain` entries with `is_active=True` are included in the allowed set.
- **5-minute cache TTL**: Allowed origins are cached with a 5-minute TTL (`CACHE_TIMEOUT = 300`) to avoid database lookups on every request. The cache is invalidated via Django signals when `ServiceDomain` records are created, updated, or deleted (see `common/signals.py`).
- **Credential support**: The injected CORS headers always include `Access-Control-Allow-Credentials: true` and set the specific origin (not `*`), ensuring cookie-based authentication works correctly.
- **Preflight caching**: `Access-Control-Max-Age: 86400` (24 hours) reduces preflight request overhead for supported browsers.
- **Development localhost bypass**: In DEBUG mode with `CORS_ALLOW_ALL_ORIGINS=True`, any localhost origin is accepted, enabling local development with cookie-based auth without manual CORS configuration.

The middleware uses Django 5.2's `@sync_and_async_middleware` pattern, with the async path wrapping the database query via `sync_to_async` for safe use under Daphne's ASGI event loop.

## 12.4 Rate Limiting & Brute Force Protection

SattaBase implements a Redis-backed sliding-window rate limiter in `common/rate_limit.py` that protects all sensitive endpoints against brute force attacks, credential stuffing, and API abuse.

**Sliding Window Algorithm**

The `check_rate_limit()` function stores a list of timestamps in Redis under the key `rl:{key}`. On each request, timestamps outside the current window are pruned, and if the remaining count exceeds `max_attempts`, the request is rejected. This provides a true sliding window (as opposed to a fixed window) that prevents the boundary-doubling attack where two bursts at the edge of adjacent fixed windows could exceed the intended rate.

**Dual-Bucket Login Protection (AUTH-3)**

The login endpoint applies two separate rate limits to each request:

1. **Per-IP rate limit** (`login:{ip}`): 10 attempts per 15 minutes per IP address. This is the standard protection against brute force from a single source.
2. **Per-email rate limit** (`login_email:{email}`): 10 attempts per 15 minutes per email address. This prevents attackers from bypassing IP-based limits by rotating through proxy networks — even with unlimited IP addresses, each email target can only be tried 10 times per 15 minutes.

The dual-bucket approach was introduced as the AUTH-3 fix after identifying that per-IP-only rate limiting was insufficient against distributed brute force attacks.

**SDK Traffic Differentiation**

When a valid `X-API-Key` header is present (SDK/server-to-server traffic), the rate limiter switches from per-IP to per-API-key-prefix buckets with significantly higher limits (`RATE_LIMIT_SDK_ATTEMPTS = 1000` per hour vs. the default `RATE_LIMIT_SENSITIVE_ATTEMPTS = 5` per hour). This prevents a sister domain backend that proxies many users through a single IP from exhausting the shared bucket. The differentiation is handled by `_get_sdk_rate_limit_params()` in `rate_limit.py`, which detects the presence of `request.service_credential` (set by the API key middleware).

**Trusted Proxy IP Extraction (MED-02)**

The `get_client_ip()` function only trusts the `X-Forwarded-For` header when the immediate connecting IP (`REMOTE_ADDR`) is listed in `settings.TRUSTED_PROXIES` (defaults to loopback only: `["127.0.0.1", "::1"]`). This prevents clients from spoofing the header to bypass rate limiting — a common attack where an attacker sets `X-Forwarded-For: <random_ip>` on each request to rotate their apparent IP and evade per-IP limits. Only requests arriving through a known reverse proxy (e.g., nginx, Cloudflare) have their forwarded IP respected.

**Rate Limit Configuration**

All rate limit parameters are configurable via environment variables with sensible defaults:

| Setting | Default | Purpose |
|---|---|---|
| `RATE_LIMIT_LOGIN_ATTEMPTS` | 10 | Login attempts per window |
| `RATE_LIMIT_LOGIN_WINDOW` | 900 (15 min) | Login rate limit window |
| `RATE_LIMIT_REGISTER_ATTEMPTS` | 5 | Registration attempts per window |
| `RATE_LIMIT_REGISTER_WINDOW` | 3600 (1 hr) | Registration rate limit window |
| `RATE_LIMIT_PASSWORD_RESET_ATTEMPTS` | 5 | Password reset attempts per window |
| `RATE_LIMIT_PASSWORD_RESET_WINDOW` | 3600 (1 hr) | Password reset rate limit window |
| `RATE_LIMIT_SENSITIVE_ATTEMPTS` | 5 | Generic sensitive action limit |
| `RATE_LIMIT_SENSITIVE_WINDOW` | 3600 (1 hr) | Generic sensitive action window |
| `RATE_LIMIT_SDK_ATTEMPTS` | 1000 | SDK/server-to-server limit |
| `RATE_LIMIT_SDK_WINDOW` | 3600 (1 hr) | SDK rate limit window |

When a rate limit is exceeded, the `check_rate_limit_or_raise()` function raises `TooManyRequestsException` (HTTP 429), which is caught by the registered exception handler in `api/views.py` and returns a standardized error response: `{"detail": "Too many requests. Please try again later.", "code": "too_many_requests"}`.

**Email-Bombing Prevention (MED-16)**

Email verification and password reset endpoints include the email address in the rate limit key (e.g., `email_verify_req:{email}` and `pwreset_confirm:{email}`), preventing an attacker from using a single IP to trigger unlimited emails to different addresses (email bombing). The email verification limit was reduced from 5 per 5 minutes to 3 per hour per email.

## 12.5 Data Encryption

SattaBase encrypts sensitive data at rest using the `cryptography` package's Fernet symmetric encryption, implemented as custom Django model fields in `billing/fields.py`.

**EncryptedCharField and EncryptedTextField**

Two custom field types provide transparent encryption/decryption at the ORM layer:

- `EncryptedCharField`: For short strings (e.g., bank account numbers). Internally overrides `max_length` to 255 to accommodate the Fernet ciphertext overhead (base64 encoding + IV + HMAC + version byte ≈ 60-80 bytes of overhead).
- `EncryptedTextField`: For longer content, using `TextField` storage without length constraints.

Both fields implement the standard Django field interface:

- `get_prep_value()`: Encrypts the plaintext before saving to the database using `Fernet.encrypt()`.
- `from_db_value()`: Decrypts the ciphertext when loading from the database using `Fernet.decrypt()`.
- `to_python()`: Handles deserialization, detecting Fernet tokens by their `gAAAAAB` prefix and attempting decryption. Falls back to returning the value as-is if decryption fails (for migration compatibility from unencrypted to encrypted data).

**Key Management**

The encryption key is derived via `get_encryption_key()`, which follows a two-tier strategy:

1. **Primary**: If `SB_CRYPTOGRAPHY_KEY` is set in the environment, it is used directly. If the value is a valid 32-byte base64-encoded Fernet key, it is used as-is. Otherwise, it is derived through PBKDF2-HMAC-SHA256 with 100,000 iterations and a fixed salt.
2. **Fallback**: If `SB_CRYPTOGRAPHY_KEY` is not set, the key is derived from Django's `SECRET_KEY` using the same PBKDF2 derivation. This is convenient for development but not recommended for production — a separate cryptography key should be configured.

In production, the `CRYPTOGRAPHY_KEY` setting in `base/settings.py` reads from `SB_CRYPTOGRAPHY_KEY` and, if absent, derives a key from `SECRET_KEY` with a warning logged. This ensures the application always starts, but operators are encouraged to set a dedicated key.

**Fernet Properties**

Fernet encryption provides AES-128-CBC with PKCS7 padding and HMAC-SHA256 for authentication, meaning that encrypted data cannot be read or tampered with without the key. Each encryption operation generates a unique IV, so identical plaintext values produce different ciphertexts, preventing pattern analysis attacks.

**Current Usage**

The primary use case for encrypted fields is storing sensitive banking information in the `BankSettings` model — specifically bank account numbers, which must be protected at rest to comply with financial data handling requirements. The `deconstruct()` method ensures that migrations record the original `max_length` rather than the inflated encrypted length, maintaining migration portability.

## 12.6 Audit Trail

SattaBase maintains a comprehensive audit trail that records all admin-initiated mutations, providing accountability, compliance evidence, and forensic investigation capability.

**AdminAuditLog Model**

The `AdminAuditLog` model (`billing/models.py`) is the central audit storage table. Unlike other models, it intentionally uses `auto_now_add` for `created_at` rather than inheriting from `TimeStampedModel`, because audit entries must be immutable — the `updated_at` field would be misleading since audit records are never edited after creation.

| Field | Type | Purpose |
|---|---|---|
| `admin_user` | FK(User, SET_NULL) | The admin who performed the action. Nullable to survive admin deletion. |
| `action` | CharField(100) | Dot-separated identifier, e.g., `product.create`, `subscription.override`, `refund.approve`, `api_key.revoked` |
| `method` | CharField(10) | HTTP method (GET, POST, PUT, PATCH, DELETE) |
| `path` | CharField(255) | API path, e.g., `/api/v1/admin/products/5` |
| `ip_address` | GenericIPAddressField | Client IP of the admin |
| `status_code` | PositiveIntegerField | HTTP response status code |
| `details` | JSONField | Structured context: request body fields, changed fields, before/after state |
| `created_at` | DateTimeField | auto_now_add, immutable timestamp |

The model is indexed on `admin_user`, `action`, and `created_at` for efficient querying by the admin audit log dashboard.

**Credential Audit Helper**

The `write_credential_audit()` function in `common/audit.py` provides a synchronous helper for writing credential lifecycle events to the audit log. It auto-detects fields from the `ServiceCredential` instance (credential ID, API key prefix, name, service domain) and merges them with any additional details passed by the caller. This function is called from:

- **Django signals** (`common/signals.py`): Runs inside the ORM transaction alongside the credential save, ensuring audit entries are always consistent with the database state.
- **Controllers** (`common/controllers.py`): For admin-initiated mutations (create, revoke, rotate) where the full request context (method, path, IP) is available.
- **Middleware** (`common/middleware.py`): For validation failures where the request is available but no admin user is authenticated.

For async code paths, callers wrap the function with `sync_to_async`:

```python
await sync_to_async(write_credential_audit)(
    action="api_key.revoked",
    credential=credential,
    admin_user=request.user,
    method=request.method,
    path=request.path,
    ip_address=get_client_ip(request),
)
```

**Audit Coverage**

All admin write endpoints are covered by audit logging. This includes product/plan CRUD operations, subscription overrides, user status/role changes, refund approvals and rejections, API key lifecycle events, and bank settings updates. Read endpoints (list, detail, metrics) are not audited to avoid excessive log volume, but admin access to user detail pages is tracked via the `log_admin_access` decorator for privacy compliance.

**Queryability**

The audit log is exposed to admins via `GET /api/v1/admin/audit-log`, which returns paginated results with filtering by action type, admin user, and date range. The `SubscriptionDetailAdmin.vue` component surfaces per-subscription audit entries, and the `AuditLogAdmin.vue` component provides a global audit timeline.

## 12.7 Input Validation & Sanitization

SattaBase enforces input validation at the schema layer using Pydantic (via Django Ninja's `Schema` and `ModelSchema` classes), which provides automatic type coercion, constraint enforcement, and detailed error messages before any request reaches business logic.

**Password Strength Validation**

All password inputs (registration, password reset, password change) are validated by the `_validate_password_strength()` function in `users/schemas.py`, which enforces:

- Minimum 8 characters (enforced by `min_length=8`)
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character from the set `[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/~`;'`

This validator is applied via `@field_validator("password")` on each schema that accepts passwords, ensuring consistent enforcement across all authentication endpoints. The password change and reset schemas also include a `@model_validator(mode="after")` that checks `new_password != confirm_password`, providing user-facing confirmation without storing the redundant field.

**Email Normalization**

All email fields are processed through `@field_validator("email")` with the `email_must_be_lowercase()` method, which lowercases and strips whitespace. This prevents duplicate accounts caused by case-sensitive email comparisons and eliminates trailing-space input errors. The normalization is applied consistently across registration, login, password reset, email verification, and email change schemas.

**OTP Validation**

One-time password fields are constrained to exactly 6 digits (`min_length=6`, `max_length=6`) and validated by `otp_must_be_digits()`, which strips whitespace and verifies the input contains only numeric characters. This prevents injection attacks through the OTP field and ensures the value matches the format generated by the backend.

**Choice Field Constraints**

User preference fields (timezone, currency, language) use Python `Literal` types derived from the model's `TextChoices` classes. For example, `TimezoneType = Literal[tuple(TimezoneChoices.values)]` restricts the input to exactly the 35 IANA timezone codes defined in the model. Pydantic rejects any value not in the literal set before the request reaches the controller, preventing invalid or malicious values from being stored.

**Field Length Constraints**

All string fields have explicit `max_length` constraints that match the underlying Django model field lengths. For example, `first_name: str = Field(..., max_length=150)` matches the `CharField(max_length=150)` on the User model. Pydantic rejects inputs exceeding these limits with a validation error. Credit purchase request schemas similarly enforce `max_length` on bank name (100), account holder name (200), account number (50), routing number (50), and transaction reference (255).

**Validation Error Response Format**

When Pydantic validation fails, the `validation_exception_handler` in `api/views.py` catches `NinjaValidationError` and returns a structured error response with per-field details:

```json
{
  "detail": "Validation error",
  "errors": [
    {"field": "password", "message": "Password must contain at least one uppercase letter."},
    {"field": "email", "message": "Value is not a valid email address."}
  ],
  "code": "validation_error"
}
```

This format enables the frontend's `useFormErrors` composable to map errors to specific form fields, providing inline validation feedback without exposing internal implementation details.

**API Key Input Sanitization**

The API key middleware (`common/middleware.py`) strips whitespace from the `X-API-Key` header before processing and performs a fast prefix check (`sb_live_`) before the expensive SHA-256 hash computation and database lookup. This prevents edge-case inputs (whitespace-padded keys, empty strings, keys with wrong prefixes) from reaching the database query layer. The `X-Service-Domain` header is similarly stripped before the cross-check against the credential's bound domain, preventing whitespace-based domain spoofing.

**No Raw Key Material in Logs**

A security audit (E3, 2026-05-07) verified that no raw API key material is ever written to logs, error responses, or exception messages. All log statements use the 12-character `api_key_prefix` (stored in the database) or a truncated `api_key[:12]` slice. The raw key exists only in the HTTP request header (in transit) and the creation/rotation HTTP response body (shown exactly once, never persisted). This prevents sensitive credentials from appearing in log aggregation systems or error monitoring tools.

---

# 13. Payment & Stripe Integration

SattaBase uses Stripe as its sole payment provider, handling the complete subscription lifecycle from checkout through renewal, plan changes, cancellations, and refunds. The Stripe integration follows a layered architecture: `client.py` provides the low-level SDK adapter, domain-specific modules (`checkout.py`, `portal.py`, `customer.py`, `prices.py`) orchestrate business flows, and the public API in `billing/stripe/__init__.py` exposes a clean interface that controllers and tasks consume. This section documents the configuration, each major payment flow, the webhook pipeline that keeps local state in sync with Stripe, the refund system, and the error handling layer that translates Stripe's cryptic error messages into user-friendly responses.

## 13.1 Stripe Configuration

Stripe integration is configured in `base/settings.py` through environment variables, all prefixed with `SB_`:

| Setting | Env Var | Default | Purpose |
|---|---|---|---|
| `STRIPE_SECRET_KEY` | `SB_STRIPE_SECRET_KEY` | `""` | Server-side API key for all Stripe operations |
| `STRIPE_PUBLISHABLE_KEY` | `SB_STRIPE_PUBLISHABLE_KEY` | `""` | Client-side key for Stripe.js (not currently used) |
| `STRIPE_WEBHOOK_SECRET` | `SB_STRIPE_WEBHOOK_SECRET` | `""` | Secret for verifying webhook signatures |
| `STRIPE_APP_DOMAIN` | `SB_STRIPE_APP_DOMAIN` | `FRONTEND_URL` | App's own domain for return URL validation |
| `STRIPE_PORTAL_RETURN_URL` | `SB_STRIPE_PORTAL_RETURN_URL` | `{APP_DOMAIN}/dashboard/billing` | Default redirect after portal session |
| `STRIPE_SUCCESS_URL` | `SB_STRIPE_SUCCESS_URL` | `{APP_DOMAIN}/dashboard/billing?checkout=success` | Checkout success redirect (includes `{CHECKOUT_SESSION_ID}`) |
| `STRIPE_CANCEL_URL` | `SB_STRIPE_CANCEL_URL` | `{APP_DOMAIN}/dashboard/billing?checkout=canceled` | Checkout cancel redirect |
| `STRIPE_TAX_ENABLED` | `SB_STRIPE_TAX_ENABLED` | `False` | Enables Stripe Tax on checkout sessions |
| `STRIPE_PORTAL_CONFIGURATION` | — | `None` | Pre-configured portal config ID |
| `TOS_VERSION` | `SB_TOS_VERSION` | `"1.0"` | Terms of service version tracked per checkout |

The `client.py` module is the only file that imports `stripe` directly. Every function accepts and returns plain `dict` / `list` / primitive types — never raw `StripeObject` instances. This eliminates `.get()` vs bracket-access inconsistencies and decouples the rest of the codebase from the Stripe SDK version. The `get_api_key()` function reads the secret key on every call rather than caching it at module level, ensuring key rotation takes effect immediately without restarting the process.

## 13.2 Checkout Session Flow

The checkout flow creates a Stripe Checkout Session that handles payment collection, card validation, and 3D Secure authentication on Stripe's hosted page. The flow is orchestrated by `billing/stripe/checkout.py` and involves several security-critical steps.

**Creating a Checkout Session**

The `create_checkout()` function validates preconditions, resolves the Stripe Price ID, and creates a Checkout Session with the following properties:

1. **Tax enforcement**: If `STRIPE_TAX_ENABLED` is `False`, checkout is blocked entirely with a critical log and a user-facing error. This prevents tax compliance violations where subscriptions are sold without collecting required taxes.
2. **Price resolution**: The `resolve_price_id()` function from `prices.py` determines the correct Stripe Price for the requested currency. If the target currency differs from the plan's base currency, the function converts the price using the exchange rate service, then creates a new Stripe Price if one doesn't already exist. A `select_for_update()` row-level lock on the Plan record prevents a TOCTOU race condition where two concurrent requests could both list prices (finding no match), then both create duplicate Stripe prices (PR-01 fix).
3. **Customer creation**: `get_or_create_customer_id()` reuses an existing Stripe Customer ID from any of the user's previous subscriptions. If the ID exists but the customer was deleted in Stripe, a new one is created transparently.
4. **Return URL validation**: The `validate_return_url()` function prevents open redirect attacks by checking the return URL's origin against registered `ServiceDomain` entries and the app's own domain. Only validated return URLs are included in the success/cancel URLs.
5. **Checkout deduplication (CMP-07)**: A 5-minute cache key (`checkout_recent_{user_id}_{product_id}_{plan_slug}`) prevents double-checkout when users rapidly click "Subscribe". If a recent checkout URL exists, it is returned instead of creating a duplicate session.
6. **ToS tracking (CMP-06)**: The current `TOS_VERSION` is stored in the checkout session's metadata, enabling version validation at confirmation time.
7. **Automatic tax**: `automatic_tax={"enabled": tax_enabled}` and `customer_update={"address": "auto"}` ensure Stripe Tax calculates and collects the correct tax based on the customer's location.
8. **Consent collection**: `consent_collection={"terms_of_service": "required"}` forces the user to accept the terms of service during checkout.

**Confirming a Checkout**

After the user completes payment on Stripe's hosted page, they are redirected to the success URL with `{CHECKOUT_SESSION_ID}`. The frontend calls `POST /api/v1/billing/checkout/confirm` with the session ID, which triggers `confirm_checkout()`:

1. The session is retrieved from Stripe and its `payment_status` is verified as `"paid"`.
2. The `user_id` from the session's metadata is compared against the authenticated user's ID to prevent session hijacking.
3. The ToS version from the checkout metadata is compared against the current version, logging a warning if they differ (the payment has already been completed, so the subscription is still activated).
4. The local subscription is updated using `sync_subscription_from_stripe()`, which fetches the live Stripe subscription data and overwrites local state.

**Safe Plan Change Flow**

Plan changes follow a preview-then-confirm pattern with an HMAC-signed preview token to prevent tampering:

1. `preview_plan_change()` calls `get_proration_preview()` which uses Stripe's `Invoice.create_preview` API to calculate the proration amount.
2. A preview token is generated via `generate_preview_token()`, which signs `user_id:subscription_id:plan_slug:total_cents:currency:timestamp` with HMAC-SHA256 using Django's `SECRET_KEY`. The token expires after 10 minutes.
3. The frontend presents the proration details and a confirmation button to the user.
4. `confirm_plan_change()` verifies the preview token using `verify_preview_token()`, which checks the HMAC signature, token expiry, and bound values. The CTR-04 fix adds ±1 cent tolerance to handle Stripe's floating-point rounding edge cases between preview and confirm calls.
5. `execute_safe_plan_change()` applies the change with different behavior based on the change type:
   - **Upgrade**: Creates and confirms a PaymentIntent for the proration amount first. Only if payment succeeds is the subscription modified with `proration_behavior="create_prorations"` (immediate change). A deterministic idempotency key (`plan-change-{sub_id}-{plan_slug}-{price_id}`) prevents duplicate charges on retry (STP-04 fix).
   - **Downgrade/Lateral**: Modifies the subscription with `proration_behavior="none"`, so the change takes effect at the next billing cycle with no immediate charge.

## 13.3 Customer Portal

The Stripe Customer Portal allows users to self-manage their billing — updating payment methods, viewing invoices, and canceling subscriptions — without leaving the Stripe-hosted experience. The `create_portal()` function in `portal.py` creates a portal session and returns the URL.

Key implementation details:

- **Customer validation**: If the user has no Stripe Customer ID, a `ValueError` is raised because the portal requires an existing customer record.
- **Return URL validation (PT-01)**: Both the default `STRIPE_PORTAL_RETURN_URL` and any caller-provided `return_url` are validated against registered `ServiceDomain` entries to prevent open redirect attacks. If validation fails, the function falls back to the configured default.
- **Portal success feedback (UX-04)**: A `portal=success` query parameter is appended to the return URL so the frontend can display a feedback toast when the user returns from the portal.
- **Sister-domain pass-through**: If a sister-domain `return_url` is provided and validated, it is passed as a query parameter so the frontend can redirect the user back to the originating domain after the portal interaction.
- **Pre-configured portal (CMP-08)**: If `STRIPE_PORTAL_CONFIGURATION` is set, the configuration ID is passed to Stripe, allowing pre-defined portal features and branding.

## 13.4 Webhook Processing Pipeline

Stripe webhooks are the primary mechanism for keeping local database state in sync with the Stripe platform. Since Stripe is the source of truth for payment and subscription state, webhooks ensure that local records reflect reality even when events occur outside the SattaBase frontend (e.g., automatic renewals, failed payments, portal-initiated cancellations).

**Webhook Endpoint**

The `BillingWebhookController` in `billing/controllers.py` exposes `POST /api/v1/billing/webhooks/stripe`. This endpoint requires no authentication (Stripe sends its own signature), but the payload is cryptographically verified using the `STRIPE_WEBHOOK_SECRET` via `stripe.Webhook.construct_event()`.

**Event Router**

The `billing/stripe/webhooks/router.py` module handles event routing:

1. `verify_and_parse()` verifies the Stripe signature and returns the event dict.
2. `record_event()` logs the event to the `WebhookEventLog` model for audit and retry capability, using `get_or_create()` to handle duplicate deliveries idempotently.
3. `process_event()` routes the event to the appropriate handler based on the event type. The handler runs inside a `transaction.atomic()` block and a cooperative timeout of 25 seconds (portable across Unix and Windows using `threading.Timer` instead of `signal.SIGALRM`).
4. After successful processing, the `WebhookEventLog` entry is marked `processed=True`. On failure, it records the error message for debugging.

**Handled Events**

The system handles 10 Stripe event types:

| Event Type | Handler | Purpose |
|---|---|---|
| `checkout.session.completed` | `handle_checkout_completed` | Confirms payment, activates subscription |
| `customer.subscription.created` | `handle_subscription_created` | Syncs new subscription from Stripe |
| `customer.subscription.updated` | `handle_subscription_updated` | Syncs subscription changes (plan, status, cancellation) |
| `customer.subscription.deleted` | `handle_subscription_deleted` | Marks subscription as expired/canceled |
| `customer.subscription.trial_will_end` | `handle_trial_will_end` | Logs trial expiration warning (3 days before) |
| `invoice.payment_succeeded` | `handle_invoice_payment_succeeded` | Records successful payment, updates invoice |
| `invoice.payment_failed` | `handle_invoice_payment_failed` | Marks subscription as past_due, triggers dunning |
| `invoice.created` | `handle_invoice_created` | Records new invoice for tracking |
| `charge.refunded` | `handle_charge_refunded` | Updates refund status on local records |
| `customer.updated` | `handle_customer_updated` | Syncs customer data changes to local user |

**Subscription Sync — Single Source of Truth**

The `sync_subscription_from_stripe()` function in `webhooks/sync.py` is the ONLY function that writes subscription state from Stripe to the local database. All webhook handlers and the `confirm_checkout` flow delegate to this function, preventing status drift. It:

- Maps Stripe statuses to local `SubscriptionStatus` values via `_STATUS_MAP`.
- Detects plan changes by comparing the Stripe Price ID against the current plan's `stripe_price_id`, falling back to metadata-based detection (`plan_slug` in the subscription's metadata) for currency-converted prices.
- Handles Stripe's dual cancellation signals (`cancel_at_period_end` and `cancel_at`) correctly, including the Stripe Customer Portal's use of `cancel_at` for trial subscriptions.
- Properly clears `canceled_at` on reactivation (when both cancel signals are absent), preventing stale cancellation timestamps from persisting after a user reactivates.

**Webhook Reconciliation**

The `reconcile_unprocessed()` function retries failed webhook events from the last 24 hours, up to 50 events per run. The LOW-09 fix ensures ALL unprocessed events are retried (not just those with error messages), catching events that timed out or crashed before logging an error. This function is called by the Celery Beat periodic task `reconcile_webhook_events`.

## 13.5 Refund Processing

Refunds are created through `create_stripe_refund()` in `billing/stripe/__init__.py`, which follows a strict flow:

1. **Determine the payment to refund**: If a specific `charge_id` is provided (FIN-03: support for refunding historical charges), the corresponding PaymentIntent is extracted from the charge. Otherwise, the latest invoice's payment intent is used.
2. **Validate refund amount**: The refund amount cannot exceed the actual paid amount on the charge/invoice (`amount_paid`, not `amount_due`). This prevents over-refunding due to partial payments or discounts.
3. **Create the Stripe refund**: The `create_refund()` wrapper in `client.py` calls `stripe.Refund.create()` with a deterministic idempotency key (`refund-{sub_id}-{payment_intent_id}-{amount}`) that ensures retries are idempotent rather than creating duplicate refunds (STP-03 fix — no timestamp in the key).
4. **Record the refund locally**: A `Refund` model instance is created with the Stripe refund ID, amount, status (mapped from Stripe's `succeeded` to `RefundStatus.COMPLETED`), and the sanitized Stripe response for audit.

**Two-Person Rule for Admin Refunds**

Admin-initiated refunds require two separate admin actions: one to initiate the refund and another to approve it. The `Refund` model tracks `initiated_by` and `approved_by` as separate foreign keys. The approval endpoint (`PATCH /admin/refunds/{id}/approve`) validates that the approver is not the same user who initiated the refund, and records the approver's IP address for audit. This control prevents a single admin from unilaterally issuing refunds.

## 13.6 Stripe Error Handling

The `billing/stripe_errors.py` module provides centralized translation of Stripe API errors into user-friendly messages. Without this layer, users would see cryptic Stripe error messages containing internal request IDs, resource identifiers, and technical jargon.

**Error Translation Pipeline**

The `handle_stripe_error()` function follows a four-stage matching pipeline:

1. **Message pattern matching**: The Stripe error message (lowercased) is checked against `_ERROR_PATTERNS`, a list of 25+ `(pattern, user_message)` tuples covering currency errors, subscription state errors, customer errors, payment method errors (card declined, insufficient funds, expired card, etc.), price/product errors, coupon/promotion code errors, refund errors, rate limiting, and portal/checkout session errors. First match wins, so more specific patterns are ordered first.

2. **Error code fallback**: If no message pattern matches, the Stripe error's `code` attribute is checked against `_ERROR_CODE_MAP`, which covers 11 common card error codes (`card_declined`, `expired_card`, `incorrect_cvc`, `authentication_required`, etc.).

3. **HTTP status classification**: If neither pattern nor code matches, the HTTP status code determines the response:
   - `5xx`: "Payment provider temporarily unavailable" (transient Stripe error)
   - `429`: "Too many requests" (rate limit)
   - `401`: "Payment system temporarily unavailable" + critical log + admin email alert (API key misconfiguration — all payments broken)
   - `404`: "Resource not found on payment provider"
   - `400`/`402`: "Payment processing failed, verify your details"

4. **Generic fallback**: "Something went wrong with the payment provider" — a safe catch-all that doesn't expose implementation details.

The function returns a `BadRequestException` directly (CC-01 fix) so controllers can simply `raise handle_stripe_error(e)` instead of wrapping it. The full original error is logged at ERROR level with the HTTP status, error code, and Stripe request ID for debugging, while the user sees only the translated message.

**Usage Pattern in Controllers**

```python
from billing.stripe_errors import handle_stripe_error

try:
    await sync_to_async(cancel_subscription_on_stripe)(subscription)
except stripe.error.StripeError as e:
    raise handle_stripe_error(e, context="cancel_subscription")
```

The optional `context` parameter adds a prefix to log entries (e.g., `[cancel_subscription] Stripe error...`), making it easy to trace which operation triggered the error.

---

# 14. Email System

SattaBase sends transactional emails for credit request notifications and dunning workflows. The email system is built on Django's built-in `django.core.mail` framework with SMTP transport in production and console output in development. All email sending is offloaded to Celery tasks to avoid blocking the request-response cycle.

## 14.1 Email Configuration

Email settings are configured in `base/settings.py` through environment variables:

| Setting | Env Var | Default | Purpose |
|---|---|---|---|
| `EMAIL_BACKEND` | — | `smtp.EmailBackend` | Django email backend |
| `EMAIL_HOST` | `SB_EMAIL_HOST` | `smtp.gmail.com` | SMTP server hostname |
| `EMAIL_PORT` | `SB_EMAIL_PORT` | `587` | SMTP server port |
| `EMAIL_USE_TLS` | `SB_EMAIL_USE_TLS` | `True` | Enable STARTTLS for port 587 |
| `EMAIL_USE_SSL` | `SB_EMAIL_USE_SSL` | `False` | Enable SSL (mutually exclusive with TLS) |
| `EMAIL_HOST_USER` | `SB_EMAIL_HOST_USER` | `""` | SMTP authentication username |
| `EMAIL_HOST_PASSWORD` | `SB_EMAIL_HOST_PASSWORD` | `""` | SMTP authentication password |
| `DEFAULT_FROM_EMAIL` | `SB_DEFAULT_FROM_EMAIL` | `noreply@sattabase.com` | Sender address for all outgoing emails |

In `DEBUG=True` mode, the email backend is overridden to `django.core.mail.backends.console.EmailBackend`, which writes email content to the console instead of sending it. This prevents accidental email delivery during development and testing. The TLS/SSL defaults were corrected (TLS=True, SSL=False) to match port 587's STARTTLS protocol — previously both were inverted, causing SMTP connection failures.

## 14.2 Email Templates

SattaBase sends two categories of emails: credit request notifications (HTML) and dunning reminders (plain text).

**Credit Request Approval Email**

The `send_credit_request_approved_email` Celery task sends a professionally branded HTML email when an admin approves a credit purchase request. The email includes:

- Blue branded header with the SattaBase company name
- Green "Approved" status badge
- Two-column details card showing Product/Plan, Amount/Periods, Invoice Number, and Payment Method
- Primary action button: "View My Credits" (links to the dashboard credits page)
- Secondary action button: "Download Invoice" (links to the billing transactions page where PDF download is available)
- Informational section explaining that credits have been added to the user's account
- Professional footer with company domain

The task accepts parameters for the user's name, email, product name, plan name, amount, currency, number of periods, invoice number, and payment method. It builds the HTML body inline (no template files) using a consistent brand color system (blue-600 primary, green status badges). A plain text fallback is included for email clients that don't support HTML.

**Credit Request Rejection Email**

The `send_credit_request_rejected_email` Celery task sends a matching HTML email when an admin rejects a credit request. It features:

- Red "Not Approved" status badge
- Conditional red reason section (displayed only if the admin provided a rejection reason)
- "Submit New Request" action button linking to the credit request form
- Same branded details card layout and footer as the approval email
- Plain text fallback

Both email tasks use `django.core.mail.send_mail()` with the `html_message` parameter for dual-format delivery. Each task returns a status dict (`{"status": "sent"}` or `{"status": "failed"}`) for observability, and logs success/failure at the appropriate level.

**Dunning Reminder Emails**

The dunning system sends plain text reminder emails at configurable intervals during the `past_due` subscription lifecycle. The `_send_dunning_email()` helper function in `billing/tasks.py` handles delivery with a minimum 24-hour interval between emails (configurable via `DUNNING_EMAIL_MIN_INTERVAL_HOURS`) to prevent spam. After sending, the subscription's `last_dunning_email_at` timestamp is updated to enforce the interval. Failed email deliveries are logged at WARNING level but do not block the dunning workflow.

## 14.3 Email Triggers

Emails are triggered from three locations in the codebase:

**1. Admin Credit Request Actions** (`billing/admin_controller.py`)

When an admin approves or rejects a credit request, the corresponding Celery task is dispatched via `.delay()`:

- Approval: `send_credit_request_approved_email.delay(user_name=..., user_email=..., product_name=..., ...)`
- Rejection: `send_credit_request_rejected_email.delay(user_name=..., user_email=..., product_name=..., ...)`

These tasks run asynchronously in the Celery worker, ensuring the admin API response is not delayed by SMTP delivery.

**2. Dunning Workflow** (`billing/tasks.py`)

The `process_dunning_step()` Celery task is triggered by the Beat scheduler and processes `past_due` subscriptions through a staged workflow. Steps 1 and 2 (`email_reminder` and `email_urgent`) send dunning emails. The `_send_dunning_email()` helper enforces the minimum interval and updates the `last_dunning_email_at` timestamp. Step 3 (`restrict_access`) restricts the subscription's feature access without sending an email, and step 4 (`cancel_subscription`) cancels the subscription entirely.

**3. Stripe API Key Alert** (`billing/stripe_errors.py`)

When `handle_stripe_error()` encounters a 401 HTTP status (invalid or missing Stripe API key), it sends a critical admin alert via `mail_admins()` in addition to logging. This ensures that the operations team is immediately notified when the payment system is broken, since all payment processing fails with an invalid key. The alert is sent synchronously (not via Celery) to ensure delivery even when the task queue is unavailable.

---

# 15. Deployment & DevOps

## 15.1 Docker Configuration

SattaBase uses multi-stage Docker builds for both the backend and frontend, optimized for small production images that exclude build-time dependencies. Each service has its own Dockerfile and runs as a non-root user for security.

### Backend Dockerfile

The backend Dockerfile uses a two-stage build process. The first stage (`builder`) installs Python dependencies from `requirements.txt` into a clean virtual environment using `pip install --user`, running on a `python:3.10-slim` base image with `build-essential` and `libpq-dev` installed for compiling native extensions like `psycopg2`. The second stage copies only the installed packages and application code into a fresh `python:3.10-slim` image that has only the runtime library `libpq5` — no compilers, no headers, no build tools.

The runtime image creates a dedicated `appuser` system user (not root) and sets up three directories: `/app/logs` for application log files, `/app/staticfiles` for collected static assets, and `/app/media` for user-uploaded files. All directories are owned by `appuser` with appropriate permissions (`755` for media to allow the web server read access). The container exposes port `8086` and runs Gunicorn with Uvicorn workers as the production server:

```dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8086", "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--access-logfile", "-", "--error-logfile", "-", \
     "base.asgi:application"]
```

The `uvicorn.workers.UvicornWorker` class runs each Gunicorn worker as an async ASGI process, enabling Django's async views and middleware to execute on the event loop. Four workers provide concurrency while keeping memory usage predictable. Access and error logs are sent to stdout/stderr (`"-"`) for container-native log collection. The ASGI application is loaded from `base.asgi:application`, which uses Channels' `ProtocolTypeRouter` to handle both HTTP and WebSocket protocols.

### Frontend Dockerfile

The frontend Dockerfile also uses a two-stage build. The first stage (`build-stage`) runs on `node:24-alpine`, installs all npm dependencies (including devDependencies needed for the build), and runs `npm run build` to produce the Astro SSR output in the `dist/` directory. The second stage (`production-stage`) copies only the built output, `node_modules`, and `package.json` onto a fresh `node:24-alpine` image.

A critical detail of the frontend Docker setup is that SSR mode requires `node_modules` at runtime — unlike a static site where the build output is self-contained, Astro's Node adapter needs the original packages to render pages on the server. The Dockerfile explicitly copies `node_modules` from the build stage with the comment: "CRITICAL: In SSR mode, the Node server needs your node_modules to run." The container runs as the `node` user (built-in to the Alpine Node image) on port `4321`, executing `node ./dist/server/entry.mjs` which is the Astro-generated server entry point.

### Key Differences Between Services

| Aspect | Backend | Frontend |
|---|---|---|
| **Base image** | `python:3.10-slim` | `node:24-alpine` |
| **Runtime user** | `appuser` (custom) | `node` (built-in) |
| **Port** | 8086 | 4321 |
| **Server** | Gunicorn + Uvicorn workers | Node.js (Astro standalone) |
| **Build output** | Installed packages only | `dist/` + `node_modules` |
| **Static files** | Collected to `/app/static` | Served by Node |
| **Media uploads** | `/app/media` directory | N/A |

## 15.2 Environment Variables

All environment variables in SattaBase are prefixed with `SB_` to avoid conflicts with system-level variables. The project uses `environ` (django-environ) to read and cast variables from the `.env` file and the process environment. Variables are read exclusively through `env()`, `env.bool()`, `env.int()`, and `env.list()` calls in `base/settings.py` — no raw `os.environ.get()` calls exist in the settings.

### Core Application Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `SB_DEBUG` | bool | `False` | Enables Django debug mode, SQLite fallback, console email backend |
| `SB_PORT` | int | `8081` | Development server port (not used in Docker) |
| `SB_SECRET_KEY` | str | Required | Django secret key for cryptographic signing |
| `SB_ALLOWED_HOSTS` | list | Required | Comma-separated list of allowed hostnames |

### Database Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `SB_DB_NAME` | str | Required | PostgreSQL database name |
| `SB_DB_USER` | str | Required | PostgreSQL user |
| `SB_DB_PASSWORD` | str | Required | PostgreSQL password |
| `SB_DB_HOST` | str | Required | PostgreSQL host |
| `SB_DB_PORT` | str | Required | PostgreSQL port |

When `SB_DEBUG=True`, all database variables are ignored and Django falls back to SQLite (`db.sqlite3` in the project root). A warning is printed to the console: "WARNING: PostgreSQL settings not fully configured. Falling back to SQLite for development." This ensures developers can start the application without a local PostgreSQL installation, while production always uses PostgreSQL.

### Stripe Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `SB_STRIPE_SECRET_KEY` | str | Required | Stripe API secret key (`sk_live_...` or `sk_test_...`) |
| `SB_STRIPE_PUBLISHABLE_KEY` | str | Required | Stripe publishable key (`pk_live_...` or `pk_test_...`) |
| `SB_STRIPE_WEBHOOK_SECRET` | str | Required | Stripe webhook signing secret (`whsec_...`) |

### Authentication & Security Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `SB_JWT_SIGNING_KEY` | str | Required in prod | Separate signing key for JWT tokens; raises `ImproperlyConfigured` if missing in production |
| `SB_SESSION_COOKIE_NAME` | str | `sessionid` | Django session cookie name |
| `SB_SECURE_HSTS_SECONDS` | int | `31536000` | HSTS max-age (1 year default) |
| `SB_CORS_ALLOW_ALL_ORIGINS` | bool | `False` | Allow all CORS origins (should be `False` in production) |
| `SB_CORS_ALLOWED_ORIGINS` | list | Required | Comma-separated allowed CORS origins |

### Rate Limiting Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `SB_RATE_LIMIT_LOGIN_ATTEMPTS` | int | `10` | Max login attempts per window |
| `SB_RATE_LIMIT_LOGIN_WINDOW` | int | `900` | Login rate limit window (seconds) |
| `SB_RATE_LIMIT_REGISTER_ATTEMPTS` | int | `5` | Max registration attempts per window |
| `SB_RATE_LIMIT_REGISTER_WINDOW` | int | `3600` | Registration rate limit window (seconds) |
| `SB_RATE_LIMIT_PASSWORD_RESET_ATTEMPTS` | int | `5` | Max password reset attempts per window |
| `SB_RATE_LIMIT_PASSWORD_RESET_WINDOW` | int | `3600` | Password reset rate limit window (seconds) |
| `SB_RATE_LIMIT_SENSITIVE_ATTEMPTS` | int | `5` | Max attempts for sensitive operations |
| `SB_RATE_LIMIT_SENSITIVE_WINDOW` | int | `3600` | Sensitive operations rate limit window (seconds) |
| `SB_RATE_LIMIT_SDK_ATTEMPTS` | int | `1000` | Max SDK API key requests per window |
| `SB_RATE_LIMIT_SDK_WINDOW` | int | `3600` | SDK rate limit window (seconds) |
| `SB_API_KEY_ENFORCED` | bool | `False` | Enforce API key validation on all SDK endpoints |

### Email Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `SB_EMAIL_HOST` | str | — | SMTP server hostname |
| `SB_EMAIL_PORT` | int | `587` | SMTP server port |
| `SB_EMAIL_USE_TLS` | bool | `True` | Enable TLS for SMTP |
| `SB_EMAIL_USE_SSL` | bool | `False` | Enable SSL for SMTP |
| `SB_EMAIL_HOST_USER` | str | — | SMTP authentication username |
| `SB_EMAIL_HOST_PASSWORD` | str | — | SMTP authentication password |
| `SB_DEFAULT_FROM_EMAIL` | str | — | Default sender email address |

In `DEBUG=True` mode, the email backend is set to `django.core.mail.backends.console.EmailBackend` and all email variables are ignored — emails are printed to the console instead of being sent.

### Development .env File

The committed `.env` file in the backend directory contains only the minimal settings needed for local development:

```env
SB_PORT=8081
SB_CORS_ALLOW_ALL_ORIGINS=True
SB_DEBUG=True
```

Email configuration is present but commented out, with explanatory notes indicating that real SMTP delivery requires setting `SB_DEBUG=False` and providing the SMTP credentials. Production environment variables should be set through the container orchestration system (e.g., Docker Compose environment directives, Kubernetes secrets, or cloud provider environment variable injection) — never committed to version control.

## 15.3 ASGI/WSGI Configuration

### ASGI Configuration (`base/asgi.py`)

The primary entry point for the backend is the ASGI application, which Django and Daphne use to serve both HTTP and WebSocket requests. The configuration wraps Django's default ASGI handler with Channels' `ProtocolTypeRouter`:

```python
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter([])
        ),
    }
)
```

The HTTP protocol is handled by Django's standard ASGI application, which processes all API requests through the middleware stack and URL routing. The WebSocket protocol is configured with an empty `URLRouter` list — the infrastructure is in place (Channels, `channels_redis`, and the `AuthMiddlewareStack` are all installed), but no WebSocket endpoints are defined yet. This means WebSocket connections will currently receive a 404, but adding new WebSocket routes is a straightforward matter of registering URL patterns in the `URLRouter` list without any architectural changes.

A critical detail is the ordering of `get_asgi_application()` before the `ProtocolTypeRouter` setup. Django's ASGI application must be initialized before Channels' routing is configured, otherwise the Django app registry will not be loaded and models will be unavailable. The `django_asgi_app = get_asgi_application()` call on line 8 ensures this ordering is correct.

### WSGI Configuration (`base/wsgi.py`)

The WSGI configuration is a standard Django WSGI setup that loads `base.settings` and exposes the WSGI callable. While the production deployment uses ASGI exclusively (Gunicorn with Uvicorn workers), the WSGI application is available for scenarios that require synchronous Python — for example, some Django management commands and third-party libraries that are not ASGI-compatible. The `WSGI_APPLICATION = "base.wsgi.application"` setting is defined in `settings.py` but the production `CMD` in the Dockerfile uses `base.asgi:application` instead.

### Why ASGI-First

SattaBase chose ASGI as the primary deployment mode because django-ninja-extra controllers are defined as `async def` methods, and running them on an ASGI server avoids the overhead of thread-pool bridging that a WSGI server would require. Daphne (the reference ASGI server for Django Channels) was originally configured, but the production Dockerfile uses Gunicorn with Uvicorn workers instead, which provides better process management (graceful restarts, worker recycling) while maintaining full ASGI compatibility. The `ASGI_APPLICATION = "base.asgi.application"` setting in `settings.py` ensures Django uses the Channels-aware ASGI application.

## 15.4 Static & Media Files

### Static Files

Django's static file system serves two purposes in SattaBase: the Django admin interface JavaScript/CSS, and any custom static assets. The configuration is straightforward:

```python
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
```

In production, the `collectstatic` management command gathers all static files from each app's `static/` directory and `STATICFILES_DIRS` into the `STATIC_ROOT` directory (`/app/static` in the container). A reverse proxy (nginx, Caddy, or a cloud CDN) should be configured to serve files from `STATIC_URL` directly, bypassing the Django application server for better performance. The Dockerfile creates the `/app/staticfiles` directory and sets appropriate ownership for the `appuser`.

In development, Django's built-in development server automatically serves static files from each app's `static/` subdirectory, so no `collectstatic` or reverse proxy configuration is needed.

### Media Files

User-uploaded files (currently only user avatars) are stored in the media directory:

```python
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
```

The `User.avatar` field uses `ImageField(upload_to="avatars/")`, which stores uploaded avatar images under `/app/media/avatars/`. The Dockerfile creates this directory with `755` permissions so the web server can read the files. In production, media files should be served by the reverse proxy or, preferably, by a cloud storage service (S3, GCS) via Django-storages. The current setup uses local filesystem storage, which means media files are not persisted across container restarts unless a persistent volume is mounted at `/app/media`.

The root URL configuration includes a `static()` catch-all for media files in development mode only:

```python
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", api.urls, name="base"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

The `static()` helper is a no-op when `DEBUG=False`, so production media serving must be handled by the reverse proxy or cloud storage.

### File Upload Limits

Django's file upload size limits are configured in `settings.py` to prevent denial-of-service attacks through oversized uploads:

```python
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440   # 2.5 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 2_621_440   # 2.5 MB
```

These limits apply to all upload endpoints, including avatar uploads. Files larger than 2.5 MB will be rejected before they reach the view layer. For avatar images specifically, Pillow is used to process and resize uploaded images, but the raw upload size limit is enforced at the Django middleware level first.

## 15.5 Production Checklist

Deploying SattaBase to production requires careful attention to security settings that are automatically enforced by the `if not DEBUG:` block in `settings.py`. This section documents every production-critical setting and its expected value.

### Security Settings (Auto-Enforced When DEBUG=False)

The following settings are automatically enabled when `DEBUG=False`:

**Cookie Security:**
- `CSRF_COOKIE_SECURE = True` — CSRF cookies are only sent over HTTPS
- `SESSION_COOKIE_SECURE = True` — Session cookies are only sent over HTTPS
- `SESSION_COOKIE_HTTPONLY = True` — Session cookies are not accessible via JavaScript
- `SESSION_COOKIE_SAMESITE = "lax"` — Session cookies are not sent on cross-site requests

**HTTPS Enforcement:**
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` — Trust the `X-Forwarded-Proto` header from the reverse proxy to detect HTTPS
- `SECURE_HSTS_SECONDS = 31536000` — Tell browsers to use HTTPS exclusively for 1 year
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` — Apply HSTS to all subdomains
- `SECURE_HSTS_PRELOAD = True` — Allow browser vendors to include the domain in their HSTS preload lists
- `SECURE_SSL_HOST = None` — No specific SSL hostname enforced (can be set to a hostname string if needed)

**File Permissions:**
- `FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o777` — Directories created by uploads are world-readable
- `FILE_UPLOAD_PERMISSIONS = 0o644` — Uploaded files are owner-writable, world-readable

### Required Production Environment Variables

Several environment variables must be explicitly set in production. Missing any of these will cause the application to fail to start:

1. **`SB_JWT_SIGNING_KEY`** — Must be set explicitly; the settings file raises `ImproperlyConfigured` if it is `None` in production. This key must not be the same as `SB_SECRET_KEY` to limit the blast radius if either key is compromised.

2. **`SB_ALLOWED_HOSTS`** — Must include all domain names that the application will serve. Requests with a `Host` header not in this list will receive a 400 Bad Request response.

3. **`SB_DB_*`** — All five database variables must be set to point to the production PostgreSQL instance.

4. **`SB_STRIPE_*`** — All three Stripe variables must use live keys (`sk_live_`, `pk_live_`, `whsec_...` for the production webhook endpoint).

5. **`SB_CORS_ALLOWED_ORIGINS`** — Must list the exact frontend domain(s) that are allowed to make cross-origin requests. `SB_CORS_ALLOW_ALL_ORIGINS` should be `False`.

6. **`SB_SECRET_KEY`** — Must be a cryptographically random string of at least 50 characters. Never reuse the development key in production.

### Pre-Deployment Verification Steps

Before deploying to production, verify the following:

1. **`python manage.py check --deploy`** — Django's built-in deployment check flags common security issues. The only silenced check is `security.W019` (SSL redirect), which is intentionally disabled because the reverse proxy handles SSL termination.

2. **`python manage.py migrate`** — Run all pending database migrations before starting the application server.

3. **`python manage.py collectstatic --noinput`** — Collect static files for the reverse proxy to serve.

4. **Stripe webhook endpoint** — Create a production webhook endpoint in the Stripe dashboard pointing to `https://your-domain.com/api/v1/billing/webhooks/stripe` with the events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`, `charge.succeeded`, `charge.refunded`.

5. **Celery workers** — Start at least one Celery worker process and one Beat scheduler process. The worker should have sufficient concurrency for email sending, exchange rate fetching, and webhook delivery tasks.

6. **Redis** — Ensure the Redis instance is accessible and has sufficient memory for both the Celery broker (DB 0) and Django cache (DB 2).

7. **Reverse proxy** — Configure nginx, Caddy, or cloud load balancer to: terminate SSL/TLS, set `X-Forwarded-Proto: https`, serve `/static/` directly from `STATIC_ROOT`, serve `/media/` directly from `MEDIA_ROOT` (or a cloud storage bucket), and proxy all other requests to the backend on port 8086.

8. **Container health checks** — Both Docker containers should have health check endpoints. The backend's `api/v1/auth/choices` endpoint (unauthenticated) can serve as a liveness probe, and the frontend's root URL (`/`) can serve the same purpose for the Node.js server.

---

# 16. Testing Strategy

## 16.1 Backend Test Structure

SattaBase uses `pytest` as its test runner with Django integration, rather than Django's built-in `TestCase` framework. Tests are organized in two locations: a `billing/tests/` subdirectory containing dedicated test modules, and default `tests.py` stubs in each Django app.

### Test Directory Layout

```
backend/
├── billing/
│   ├── tests.py                        # Django default stub (empty)
│   └── tests/
│       ├── test_safe_plan_change.py    # 326 lines, 5 classes, 22 tests
│       ├── test_revenue_recognition.py # 413 lines, 4 classes, 12 tests
│       ├── test_checkout.py            # 78 lines, 1 class, 2 tests
│       ├── test_stripe_errors.py       # 72 lines, 1 class, 8 tests
│       ├── test_currency_service.py    # 85 lines, 3 classes, 6 tests
│       └── test_refund.py             # 18 lines, 1 class, 1 test (placeholder)
├── common/
│   └── tests.py                        # Django default stub (empty)
└── users/
    └── tests.py                        # Django default stub (empty)
```

The `billing/tests/` directory does not contain an `__init__.py` file — tests rely on pytest's auto-discovery mechanism, which finds `test_*.py` files recursively. This is a deliberate choice to avoid import conflicts that can arise when Django's test runner and pytest both try to collect tests from the same package.

### Test Runner Configuration

Tests are executed with `pytest` rather than `python manage.py test`. The pytest configuration allows tests to access Django models and the database through `@pytest.mark.django_db` markers and `@pytest.fixture` decorators. Only `test_revenue_recognition.py` uses the Django test database — the remaining test files are pure unit tests that mock external dependencies and test business logic in isolation.

### Testing Philosophy

The current test suite follows a "test the logic, not the framework" philosophy. Most tests are pure Python unit tests that instantiate business logic classes directly and verify their behavior without touching the database, HTTP layer, or external services. This approach makes tests fast (no database setup/teardown), deterministic (no flaky external API calls), and focused on the actual business rules. The trade-off is that integration paths — the full request-to-response pipeline through controllers, middleware, and serializers — are not covered by automated tests and must be verified manually or through future integration test development.

## 16.2 Key Test Scenarios

### Safe Plan Change Tests (`test_safe_plan_change.py`)

This is the most comprehensive test file in the project, with 22 test methods across 5 test classes covering the entire safe plan change flow from preview token generation to execution:

**`TestPreviewToken`** (10 tests) — Validates the HMAC-based preview token system used to prevent plan change manipulation. Tests cover token creation, verification, tampering detection (modifying the amount, plan ID, user ID, or currency in the token payload causes verification to fail), 10-minute TTL expiry, malformed token rejection, empty token rejection, and uniqueness across different subscriptions. The token system prevents a user from previewing a plan change at one price and then confirming it at a different price by storing the previewed amount in a signed token.

**`TestClassifyPlanChange`** (5 tests) — Tests the `classify_plan_change()` function that determines whether a plan change is an upgrade, downgrade, or lateral move. The classification affects billing behavior: upgrades are charged immediately with proration, downgrades take effect at the next billing cycle with no immediate charge, and lateral moves (same price) require no payment. Tests cover same-currency classification, cross-currency classification, and edge cases where prices are equal.

**`TestExecuteSafePlanChange`** (6 tests) — Tests the decision logic for whether a Stripe PaymentIntent is needed during a plan change. Downgrades skip the charge entirely, upgrades with positive proration create a PaymentIntent, zero-proration upgrades skip the charge, payment failures block the modification, and succeeded/processing PaymentIntent statuses allow the modification to proceed. These tests verify the "safety gate" that prevents a user from changing to a more expensive plan without a confirmed payment method.

**`TestChangePlanSafetyGate`** (4 tests) — Tests the blocking logic for plan changes. Changes between paid plans are blocked if they bypass the payment safety gate, changes from paid to free plans are allowed (no charge needed), subscriptions without a Stripe ID are allowed (offline/bank-transfer subscriptions), and changes from free to paid plans are allowed but redirect to Stripe Checkout instead of using the plan change API.

**`TestPreviewConfirmFlow`** (2 tests) — End-to-end tests for the full upgrade and downgrade flows. The upgrade test verifies that the preview returns immediate proration amounts and the confirm call executes the change with those exact amounts. The downgrade test verifies that the preview returns zero proration and the change takes effect at the next billing cycle.

### Revenue Recognition Tests (`test_revenue_recognition.py`)

This is the only test file that uses the Django test database (via `@pytest.fixture` and `@pytest.mark.django_db`). It contains 12 tests across 4 classes covering the ASC 606 revenue recognition system:

**`TestRevenueRecognitionModel`** (5 tests) — Tests the `RevenueRecognitionEntry` model directly: creation, unique constraint per subscription and date (attempting to create two entries for the same subscription on the same date raises an integrity error), allowing entries for different dates, the `__str__` representation, and the default source field value of "scheduled".

**`TestRecognizeRevenueTask`** (5 tests) — Tests the `recognize_revenue_scheduled` Celery task: monthly subscriptions produce daily amounts ($30/month divided by 30 days = $1/day), free plans are skipped entirely, lifetime plans are skipped (revenue is recognized at purchase time, not daily), duplicate task runs are idempotent (running the task twice for the same subscription and date does not create duplicate entries), and inactive/canceled subscriptions are skipped.

**`TestWebhookRevenueRecognition`** (3 tests) — Tests that Stripe webhook handlers create revenue recognition entries when a subscription payment is confirmed: the `invoice.paid` webhook creates an entry for the payment date, `update_or_create` semantics allow updating existing entries without duplication, and revenue recognition failures are non-fatal to payment processing (a bug in revenue recognition does not prevent the subscription from being marked as paid).

### Checkout Deduplication Tests (`test_checkout.py`)

This file contains 2 tests that verify the checkout session caching mechanism (CMP-07 fix). When a user double-clicks the subscribe button, the second click should return the same checkout URL without creating a duplicate Stripe Checkout session. The tests verify: (1) the cached URL is returned on subsequent requests without making a Stripe API call, and (2) a new checkout session is created and cached when no cached URL exists.

### Stripe Error Handling Tests (`test_stripe_errors.py`)

This file contains 8 tests that verify the `handle_stripe_error()` function translates raw Stripe API errors into user-friendly `SattaBaseException` instances. Each test creates a mock Stripe error object with specific error codes and verifies the resulting exception: card declined (`card_declined`), expired card (`expired_card`), insufficient funds (`insufficient_funds`), currency mismatch, subscription already canceled, server error (502 translated to "temporarily unavailable"), unknown error (fallback message), and rate limit. An additional test verifies that the `context` parameter is logged correctly for debugging.

### Currency Service Tests (`test_currency_service.py`)

This file contains 6 tests across 3 classes covering the `CurrencyService`: same-currency conversion returns a rate of 1.0, currency matching is case-insensitive, basic USD-to-BDT conversion works correctly, requesting a rate for an unsupported currency returns None, converting a zero amount returns zero, the primary API failure triggers the fallback API, and both APIs failing sends an admin alert.

### Refund Validation Tests (`test_refund.py`)

This file is a placeholder with a single test that only verifies mock patching works correctly. The comment states that full integration tests require a database, indicating that comprehensive refund testing (including the two-person approval rule, partial refunds, and Stripe refund creation) is a future development priority.

## 16.3 Frontend Testing

The frontend currently has no automated test suite. No test framework (Vitest, Jest, Playwright, Cypress) is configured in the `package.json` dependencies or scripts. This is a recognized gap in the project's quality assurance strategy.

### Current Manual Testing Approach

Frontend functionality is verified through manual testing during development and before releases. The interactive nature of the Astro + Vue islands architecture makes component-level testing straightforward to add in the future, since each Vue component is a self-contained island with clearly defined props, events, and API interactions.

### Recommended Testing Additions

The highest-priority frontend tests would cover:

1. **Authentication flow** — Login, registration, token refresh, session expiry, and redirect behavior in `api.ts` and `useAuth.ts`. These are the most critical paths and the most likely to regress.

2. **API client error handling** — The `createApiErrorFromResponse()` function and the 401 refresh-retry logic in `api.ts`. These are complex paths with multiple branches that would benefit from unit test coverage.

3. **Form validation** — The `useFormErrors.ts` composable and the `usePasswordStrength.ts` composable are pure logic modules that are straightforward to unit test.

4. **Vue component rendering** — Critical components like `SessionGuard.vue`, `AdminGuard.vue`, and `SubscriptionDetailAdmin.vue` (the largest component at ~1615 lines) would benefit from component testing with Vue Test Utils.

5. **End-to-end flows** — Playwright or Cypress tests for the full user journey: registration → email verification → plan selection → Stripe checkout → subscription activation → profile update. These would catch integration issues that unit tests miss.

The technical foundation for adding tests is already in place: TypeScript provides type safety, the composable pattern makes logic testable in isolation, and the API client layer abstracts HTTP interactions behind a testable interface.

---

# 17. Error Handling Philosophy

## 17.1 Custom Exception Hierarchy

SattaBase defines a custom exception hierarchy in `common/exceptions.py` that extends `ninja_extra.exceptions.APIException`. Every exception class follows a consistent structure with three class-level attributes: `status_code` (HTTP status integer), `default_detail` (human-readable message), and `default_code` (machine-readable string). The `default_code` is consumed by the `_get_error_details()` method inherited from `APIException` and stored inside Django Ninja's `ErrorDetail` object, making it available in the `code` field of API responses.

### Exception Classes

| Exception | Status | Default Code | Purpose |
|---|---|---|---|
| `BadRequestException` | 400 | `bad_request` | Invalid or malformed request data |
| `UnauthorizedException` | 401 | `unauthorized` | Authentication required but not provided |
| `ForbiddenException` | 403 | `forbidden` | Authenticated but lacking permission |
| `NotFoundException` | 404 | `not_found` | Requested resource does not exist |
| `ConflictException` | 409 | `conflict` | Request conflicts with current state |
| `TooManyRequestsException` | 429 | `too_many_requests` | Rate limit exceeded |
| `AccountNotActiveException` | 403 | `account_not_active` | Account not activated (email verification) |
| `AccountInactiveException` | 401 | `account_inactive` | Account deactivated by admin; SDK should force-logout |
| `AccountDeletedException` | 401 | `account_deleted` | Account soft-deleted by user; SDK should force-logout |

### Design Decisions

The three account-status exceptions (`AccountNotActiveException`, `AccountInactiveException`, `AccountDeletedException`) are deliberately separated despite their similar semantics. `AccountNotActiveException` (403) indicates that the user has not verified their email — they are authenticated but restricted from full access. `AccountInactiveException` (401) indicates an admin has deactivated the account — SDK consumers should treat this as a force-logout signal because the user's session is no longer valid. `AccountDeletedException` (401) indicates the user has requested account deletion — this is a permanent force-logout signal. The different status codes (403 vs 401) and machine-readable codes allow frontend and SDK clients to distinguish these states and respond appropriately, rather than showing a generic "unauthorized" message to a user who simply needs to verify their email.

The naming convention `default_detail` (not `default_message`) is required by the `APIException.__init__` contract — the parent class reads `self.default_detail` when no explicit `detail` argument is passed. Similarly, `default_code` must use this exact name because `_get_error_details()` references it internally. Deviating from these names would cause the exception to fall back to the parent class's generic message and code.

## 17.2 API Error Response Format

All API errors in SattaBase follow a consistent response envelope, enforced by the exception handlers registered in `api/views.py`. There are two distinct error response formats: one for validation errors and one for all other custom exceptions.

### Standard Error Envelope

For custom exceptions (400, 401, 403, 404, 409, 429), the response body follows this structure:

```json
{
  "detail": "The requested resource was not found.",
  "code": "not_found"
}
```

The `detail` field contains a human-readable message suitable for displaying to users. The `code` field contains a machine-readable string that frontend and SDK clients can use for programmatic error handling without parsing the message text. This is produced by the shared `_error_response()` helper function:

```python
def _error_response(request, exc):
    return api.create_response(
        request,
        {"detail": str(exc.detail), "code": getattr(exc.detail, "code", "error")},
        status=exc.status_code,
    )
```

The `code` value is read from `exc.detail.code`, which is set by Django Ninja's `ErrorDetail` class based on the exception's `default_code` attribute. If for any reason the code attribute is missing, it falls back to the generic string `"error"`.

### Validation Error Envelope

When Pydantic validation fails (request body doesn't match the schema), the `validation_exception_handler` produces a richer response with field-level details:

```json
{
  "detail": "Validation error",
  "errors": [
    {"field": "payload -> email", "message": "Enter a valid email address."},
    {"field": "payload -> amount", "message": "Ensure this value is greater than 0."}
  ],
  "code": "validation_error"
}
```

The `errors` array contains one object per invalid field, with a `field` path (using ` -> ` as the separator between nesting levels) and a `message` from Pydantic's validation. If the exception object lacks an `errors` attribute (rare edge case), a single non-field error is synthesized with the field name `"non_field"`. The `code` is always `"validation_error"` for this response type.

### Catch-All Server Error

For truly unexpected exceptions that are not caught by any specific handler, the `unhandled_exception_handler` returns a generic 500 response:

```json
{
  "detail": "An unexpected error occurred. Please try again.",
  "code": "server_error"
}
```

The actual exception and full traceback are logged at ERROR level before the response is sent, ensuring developers can diagnose the issue from server logs without exposing internal details to the client. This follows the principle of never leaking stack traces, file paths, or SQL queries in API responses — information that would be useful to an attacker.

### Handler Registration Pattern

Each custom exception has its own registered handler function in `api/views.py`, but all handlers delegate to the same `_error_response()` function. The individual handlers exist so that each exception type can be easily customized in the future (e.g., adding extra logging for `TooManyRequestsException` or triggering an alert for `AccountDeletedException`) without affecting other exception types.

## 17.3 Frontend Error Handling

The frontend implements a multi-layered error handling strategy that spans the API client layer (`lib/api.ts`), the form error management composable (`useFormErrors.ts`), and the session management system (`SessionGuard.vue`).

### API Client Error Processing (`lib/api.ts`)

The `request<T>()` function in `api.ts` is the central error handling point for all API calls. It implements a four-stage error processing pipeline:

**Stage 1: Proactive Token Refresh** — Before making any request, the client checks whether the current access token is expiring soon (within 5 minutes of its `exp` claim). If so, it proactively refreshes the token first, waiting for the refresh to complete before sending the actual request. This eliminates the common "first-click eaten" bug where a user clicks a button, the request goes out with an expired token, gets a 401, refreshes, and then the user has to click again. The proactive refresh was added as a fix for this exact user experience issue.

**Stage 2: 401 Refresh-Retry** — If a request still receives a 401 response (e.g., the token expired between the proactive check and the actual request), the client attempts one token refresh and retries the request with the new token. If the retry also returns 401, the client recognizes this as a permission issue (not a session issue) and lets the error propagate without redirecting to login. This prevents an infinite redirect loop for users who are authenticated but lack access to a specific resource.

**Stage 3: Session-Expired Redirect** — If the refresh attempt itself fails (the httpOnly refresh token cookie is also expired or invalid), the client calls `redirectToLogin()` which emits `auth:session-expired` and `auth:logout` events. It does not directly call `window.location.href` or `router.push()` — instead, it relies on `SessionGuard.vue` to listen for these events and perform the actual navigation. This emit-only pattern ensures that the redirect is handled by the component that owns the Vue Router instance, avoiding race conditions between Astro's SSR and Vue's client-side routing. A 3-second safety timeout clears the `isRedirecting` flag in case the redirect fails for any reason.

**Stage 4: Error Response Parsing** — All non-OK responses are processed by `createApiErrorFromResponse()`, which parses the response body into an `ApiError` object with three fields:

```typescript
interface ApiError {
  status: number;
  message: string;
  errors?: Record<string, string[]>;
}
```

The parser handles multiple response formats: `body.detail` (SattaBase standard envelope), `body.message` (fallback), `body.non_field_errors[0]` (Django REST framework format), and `body.errors` with `code === "validation_error"` (field-level validation errors). For validation errors, the first field error is formatted as a human-readable message: the field name is cleaned (removing `payload.` and `body.` prefixes, replacing underscores with spaces, title-casing) and prepended to the error message. Any additional field-level errors from the response body (keys that are not `detail`, `message`, `non_field_errors`, `code`, or `errors`) are collected into the `errors` dictionary for form-level display.

### Form Error Management (`useFormErrors.ts`)

The `useFormErrors` composable provides a reactive bridge between API error responses and form field display. It is used by every form component in the application — login, registration, password reset, credit requests, and all admin forms. The composable manages two types of errors:

**Field errors** (`fieldErrors`) — A reactive `Record<string, string>` map where keys are form field names and values are error messages. Initialized from a `fields` array parameter that lists all field names, setting each to an empty string. When an API call returns field-level validation errors, the `setApiFieldErrors()` method maps the Django Ninja `Record<string, string[]>` format to the local field names, joining multiple messages with spaces.

**General errors** (`generalError`) — A reactive `ref<string>` for non-field-specific errors like "Invalid credentials" or "An unexpected error occurred." Set via `setGeneralError()` and displayed at the top of the form.

The `clearErrors()` method resets both field and general errors, and `hasErrors()` returns a boolean for conditional rendering. The composable pattern ensures that every form component handles API errors consistently without duplicating error parsing logic.

### SessionGuard Error Integration

The `SessionGuard.vue` component listens for the `auth:session-expired` and `auth:logout` events emitted by `redirectToLogin()` and performs the actual navigation to the login page with a `?reason=session-expired` query parameter. This component is mounted at the top of every authenticated page layout (Dashboard and Admin), ensuring that session expiry is always handled regardless of which Vue island the user is interacting with. The guard also checks the `window.__sb_redirect_reason` flag as a safety net in case event listeners are lost during Astro View Transitions — this window-level flag persists across module re-evaluations.

The combination of proactive token refresh (preventing most 401s), reactive refresh-retry (handling edge-case 401s), and event-driven session expiry handling (decoupling redirect logic from API calls) creates a robust error handling pipeline that is transparent to the user in normal operation and graceful in failure scenarios.

---

# 18. Data Flow Diagrams

This section describes the end-to-end data flow for the four most critical user journeys in SattaBase. Each flow is presented as a step-by-step sequence showing the interaction between the browser/frontend, the Django backend, and external services (Stripe, Redis, Celery). These descriptions serve as the authoritative reference for understanding how data moves through the system.

## 18.1 User Registration & Login Flow

### Registration Flow

```
Browser                   Astro SSR              Django API              Database/Redis
───────                   ──────────             ───────────             ─────────────
1. Submit form ──────►   2. POST /auth/register ─►  3. Rate limit check (5/3600s per IP)
   {email, password,                                    │
    first_name, ...}                          4. AuthService.aregister_user()
                                                ├─ Check email uniqueness → 409 if exists
                                                ├─ Create User (is_email_verified=False)
                                                ├─ Hash password (Django default: PBKDF2)
                                                └─ Return User
                                     5. AuthService.arequest_email_verification()
                                                ├─ Generate 6-digit OTP
                                                ├─ Store in cache (5-min TTL)
                                                └─ Send email (console in DEBUG)
                          ◄── 201 ──────────
   "Registration successful."
6. Redirect to /auth/verify-email
```

The registration endpoint is intentionally separated from authentication — no JWT tokens are returned on registration. The user must verify their email address before they can log in and access protected endpoints. The email verification OTP is sent asynchronously (non-blocking; failure is logged but does not fail the registration request), ensuring that a transient SMTP outage does not prevent account creation.

### Login Flow

```
Browser                   Astro SSR / Vue         Django API              Database/Redis
───────                   ──────────────          ───────────             ─────────────
1. Submit form ──────►   2. POST /auth/login ─────►  3. Per-IP rate limit (10/900s)
   {email, password,                                    Per-email rate limit (10/900s)
    remember}                                 4. AuthService.aauthenticate_user()
                                                ├─ Check is_account_locked() → 403 if locked
                                                ├─ Verify password (bcrypt/PBKDF2)
                                                ├─ Check is_active, is_deleted
                                                ├─ reset_failed_login_attempts()
                                                └─ Return User
                                     5. Generate JWT tokens
                                                ├─ AccessToken (5-min default TTL)
                                                └─ RefreshToken (7-day default TTL)
                                     6. Record login history (IP, user agent)
                                     7. Build response:
                                                ├─ Body: {access: "eyJ..."}
                                                └─ Cookie: Set-Cookie: sb_refresh_token=...;
                                                     HttpOnly; Secure; SameSite=None|Lax
                          ◄── 200 ──────────
8. Store access token in
   window-level shared state
   (useAuth composable)
9. SessionGuard detects
   valid session → renders
   DashboardLayout
```

The critical security design of the login flow is the separation of token storage: the access token is returned in the JSON response body and stored in JavaScript memory (attached to the `window` object via the `useAuth` composable), while the refresh token is set exclusively in an httpOnly cookie that JavaScript cannot read. The `remember` parameter controls cookie persistence: `remember=True` sets a persistent cookie with a 30-day expiry plus a readable `sb_remember_me=true` flag cookie, while `remember=False` sets a session-only cookie that expires when the browser closes. In development mode, the cookie uses `SameSite=Lax; Secure=False` to allow cross-origin requests from the frontend dev server; in production, it uses `SameSite=None; Secure=True` for cross-domain operation.

## 18.2 Subscription Purchase Flow

```
Browser                Vue Component         Django API              Stripe              Database
───────                ─────────────         ───────────             ──────              ────────
1. Click "Subscribe" ─► 2. POST /billing/ ──► 3. require_verified_email()
   on plan card          subscriptions/         ├─ Check ToS acceptance
                         {product}/checkout     ├─ Rate limit check
                                                ├─ Validate plan is active, not free
                                                └─ _process_checkout_with_lock()
                                                     ├─ select_for_update(subscription)
                                                     ├─ If Stripe sub is live → reactivate
                                                     │   → return {reactivated: true}
                                                     └─ Else → check trial eligibility
                                                          → mark has_used_trial
                                                          → return checkout data
                              ◄── {reactivated} ────  (if reactivation)
                              OR:
4. [New checkout] ─────────────────────────► 5. create_checkout()
                                                ├─ Resolve price_id for currency
                                                ├─ CMP-07: Check cache for recent
                                                │   checkout URL → return if exists
                                                ├─ Create Stripe Checkout Session
                                                │   (mode=subscription, automatic_tax,
                                                │    consent_collection=terms_of_service,
                                                │    metadata={user_id, product_slug,
                                                │              plan_slug, tos_version})
                                                ├─ Cache URL for 5 minutes
                                                └─ Return session.url
                              ◄── {checkout_url: "https://checkout.stripe.com/..."}
6. Redirect browser ─────────────────────────────────────────────► 7. Stripe hosted
   to checkout_url                                                                  payment form
                                                                                     ├─ Collect card
                                                                                     ├─ Process payment
                                                                                     └─ On success:
8. Stripe redirects ◄───────────────────────────────────────────── 9. Redirect to
   to success URL                                                    /dashboard/billing?
   /dashboard/billing?                                               checkout_success=true
   checkout_success=true                                             &session_id=cs_xxx

   [Parallel: Stripe webhook]
   Stripe ─────────────────────────────────────────────────────────► 10. POST /billing/webhooks/stripe
                                                                      ├─ Verify signature
                                                                      ├─ Route to handler:
                                                                      │   checkout.session.completed
                                                                      │   → sync_subscription_from_stripe()
                                                                      │     ├─ Create/update Subscription
                                                                      │     ├─ Set status=active/trialing
                                                                      │     └─ Create RevenueRecognitionEntry
                                                                      └─ Log to WebhookEventLog
```

The subscription purchase flow demonstrates the "Stripe-first, DB-second" pattern (Section 1.3). The checkout URL is created on Stripe's servers first, and the local database is only updated when the `checkout.session.completed` webhook arrives confirming payment. The `select_for_update()` lock inside `_process_checkout_with_lock()` prevents a race condition where two concurrent checkout attempts could both bypass the trial-eligibility check — the lock ensures that `has_used_trial` is read and set atomically.

The CMP-07 deduplication cache prevents users from creating duplicate Stripe Checkout sessions by double-clicking the subscribe button. The cache key is `checkout_recent_{user_id}_{product_id}_{plan_slug}` with a 5-minute TTL. If a cached URL exists, it is returned immediately without calling the Stripe API. The `confirm_checkout()` function (called on the success redirect) validates the session's `payment_status`, verifies `metadata.user_id` matches the requesting user (preventing session hijacking), and either syncs the subscription from Stripe or creates it locally.

## 18.3 Credit Purchase (Bank Transfer) Flow

The credit purchase flow is an offline payment pathway for users who cannot use international credit cards — a common scenario in South Asian markets. It operates entirely outside of Stripe, using bank transfers verified by administrators.

```
Browser (User)              Django API                Database               Celery
─────────────              ───────────               ────────               ──────
1. Submit credit request ─► 2. POST /billing/credits/request
   {product, plan,             ├─ require_verified_email()
    periods, bank,              ├─ Validate product & plan active
    reference, proof}           ├─ Validate min commitment (3 monthly / 1 yearly)
                                ├─ Validate amount = periods × plan.price_cents
                                ├─ Validate bank details against BankSettings
                                └─ Create CreditPurchaseRequest
                                     status=PENDING
                               ◄── 201 {id, status: "pending"}
3. "Request submitted"
   confirmation shown

   ───────────────────── [Waiting for admin review] ─────────────────────

Browser (Admin)             Django API                Database               Celery
─────────────              ───────────               ────────               ──────
4. Admin reviews request ─► 5. POST /admin/credit-requests/{id}/approve
   in admin panel              ├─ select_for_update(credit_request)
                                ├─ Validate status=PENDING
                                ├─ BillingService.create_credit_pool()
                                │   ├─ Create CreditPool (total_credits, remaining_credits)
                                │   ├─ Create CreditInvoice (invoice_number auto-generated)
                                │   └─ Create CreditTransaction (type=credit, amount)
                                ├─ Update request: status=APPROVED, reviewed_by, reviewed_at
                                └─ [Outside transaction:]
                                    send_credit_request_approved_email.delay(...)
                                                          │
                                                          ├─ Build HTML email
                                                          ├─ send_mail() with html_message
                                                          └─ Return {status: "sent"}
                               ◄── 200 {id, status: "approved", credit_pool_id, invoice_number}

   OR (rejection path):
4b. Admin rejects ───────► 5b. POST /admin/credit-requests/{id}/reject
                                ├─ Validate status=PENDING
                                ├─ Update: status=REJECTED, review_note=reason
                                └─ send_credit_request_rejected_email.delay(...)

   ───────────────────── [After approval] ─────────────────────

Celery Beat ─────────────► 6. consume_credit_periods (daily scheduled task)
                              ├─ For each active CreditPool with periods > 0:
                              │   ├─ Decrement remaining_periods by 1
                              │   ├─ Create CreditTransaction (type=period_consume)
                              │   └─ If remaining_periods == 0 → expire pool
                              └─ Log results
```

The credit purchase flow highlights a key architectural difference from the Stripe subscription flow: because there is no external payment processor involved, all financial mutations happen directly in the local database. This makes the `select_for_update()` lock on the `CreditPurchaseRequest` even more critical — it prevents a double-approval race condition where two admins could simultaneously approve the same request, creating duplicate credit pools. The `BillingService.create_credit_pool()` method creates three records atomically within the same transaction: the `CreditPool` (tracking remaining credits and periods), the `CreditInvoice` (with an auto-generated invoice number for the PDF), and a `CreditTransaction` (recording the initial credit allocation).

The email sending is intentionally performed outside the database transaction. If the transaction succeeds but the email fails, the credit has already been allocated and the admin can see the approval in the admin panel — the email is a notification, not a guarantee. If email sending were inside the transaction, an SMTP timeout could roll back the entire approval, leaving the credit unallocated even though the admin intended to approve it.

## 18.4 SDK SSO Authorization Flow

The SSO flow enables users authenticated on a sister domain to seamlessly access SattaBase (the base domain) without logging in again. It uses a short-lived authorization code pattern similar to OAuth 2.0, adapted for same-organization cross-domain authentication.

```
Sister Domain                  Browser                   SattaBase Frontend         SattaBase API
─────────────                  ───────                   ──────────────────         ─────────────
1. User clicks
   "Manage Billing"
   or "Account Settings"

2. Frontend has JWT
   access token
   (from sister domain's
   own auth system)

3. POST /auth/authorize ──────────────────────────────────────────────────────────► 4. Validate JWT
    Headers:                                                                          ├─ Extract user
      Authorization: Bearer <sister-domain-JWT>                                       ├─ Generate one-time
      (sent to base API via CORS)                                                     │   auth code (30-sec TTL)
                                                                                      └─ Store code in cache
                                              ◄──────────────────────────────────── {code: "abc123", expires_in: 30}

5. Redirect browser to ──────────────────────────────────────────────► 6. /auth/callback page loads
   https://base.sattaspace.com/                                          ├─ Extract ?code=abc123
   auth/callback?code=abc123                                              └─ Vue component mounts:
                                                                            AuthCallbackHandler.vue

                                                                        7. POST /auth/token/exchange ──► 8. Rate limit (10/60s)
                                                                            {code: "abc123"}               ├─ Validate & consume code
                                                                                                            ├─ Look up user from code
                                                                                                            ├─ Generate JWT tokens
                                                                                                            │   ├─ AccessToken (5-min)
                                                                                                            │   └─ RefreshToken (7-day)
                                                                                                            └─ Set httpOnly cookie
                                                                                                               (session-only, remember=False)
                                              ◄──────────────────────────────────── {access: "eyJ..."}

9. Store access token in
   window-level shared state
   (useAuth composable)

10. SessionGuard detects
    valid session → redirect
    to /dashboard
```

The SSO flow is carefully designed to prevent several attack vectors. The authorization code is single-use and expires in 30 seconds, making it impractical to intercept and replay. The token exchange endpoint is rate-limited to 10 attempts per 60 seconds (CRIT-06 fix), preventing brute-force attacks on the code space. The refresh token is set as a session-only cookie (`remember=False`) rather than a persistent cookie, so closing the browser ends the SSO session on the base domain without affecting the sister domain's session.

A critical aspect of this flow is that the sister domain frontend must make the `/auth/authorize` request with the user's JWT token to the SattaBase API. This works because the `DynamicCorsMiddleware` (`service_domain_cors_middleware`) reads the `ServiceDomain` table and injects the appropriate `Access-Control-Allow-Origin` header for the sister domain, allowing the cross-origin request. Without this dynamic CORS resolution, the browser would block the request as a CORS violation. The API key (`X-API-Key` header) is not used for this flow — the authorize endpoint uses JWT authentication because the user is already logged in on the sister domain and their identity must be verified, not just the sister domain's identity.

---

# 19. Known Issues & Technical Debt

## 19.1 Known Bugs

### Admin User Detail — Subscription View Login Redirect

**Status**: Unresolved | **Severity**: Medium | **First Observed**: 2026-06-05

When an administrator navigates to `/admin/users/{id}` and clicks the "View" button on the subscription tab, the browser is unexpectedly redirected to the login page. The root cause has not been fully investigated, but the suspected mechanism involves the following sequence: the "View" button triggers navigation to `/admin/subscriptions/{subId}`, which is a separate admin page that loads `SubscriptionDetailAdmin.vue`. During this page transition, the Astro middleware validates the session by calling `POST /auth/token/refresh-cookie` server-side. If this validation fails for any reason (e.g., the server-side fetch cannot forward the browser's httpOnly cookie, or the refresh token has been rotated by a concurrent request), the middleware returns a 302 redirect to `/auth/login`.

The failure is likely related to the Astro middleware's `validateRefreshCookie()` function, which manually constructs a `Cookie` header for server-side fetch requests (since Astro's server-side rendering cannot forward the browser's cookies automatically). If the refresh token was recently rotated by another tab or a View Transition module re-evaluation, the server-side fetch may present a stale refresh token that has already been consumed. While the refresh endpoint intentionally does not blacklist old tokens to support concurrent tabs (see Section 4.2), the token may have been blacklisted as part of the AUTH-4 damage containment response if a blacklisted token was detected for the same user, which would cause all outstanding tokens for that user to be invalidated.

**Reproduction Steps**: Log in as an admin user → Navigate to `/admin/users/{id}` → Click the "Subscriptions" tab → Click "View" on any subscription → Observe redirect to login page.

**Workaround**: After the redirect, log in again and navigate directly to `/admin/subscriptions/{subId}` using the URL bar or the subscriptions list page.

## 19.2 Technical Debt

### High Priority

**1. Admin Override for Minimum Commitment Period**

The credit purchase system enforces a minimum commitment period of 3 months for monthly plans and 1 year for yearly plans. However, there is no admin override mechanism to waive or modify this requirement for specific users or deals. This limits the platform's flexibility for enterprise sales and promotional offers. The validation currently lives in `BillingProtectedController.request_credit_purchase()` and would need to accept an optional admin-provided override parameter, with corresponding audit logging.

**2. Credit Transferability Between Users**

Credit pools are currently bound to a single user and cannot be transferred to another user. This limitation was a deliberate initial design decision to simplify the accounting model, but several business scenarios require credit transfers: organizational accounts where a team lead purchases credits for team members, account consolidation during mergers, and error correction when credits are allocated to the wrong user. Implementing this would require a new `CreditTransaction` type (`transfer_out` / `transfer_in`), a `CreditTransfer` model tracking source and destination, and an admin-only transfer API with the same two-person approval rule used for refunds.

**3. Data Retention After Credit Expiry**

When a credit pool expires (all periods consumed), the `CreditPool` and associated `CreditTransaction` records remain in the database indefinitely. There is no data retention policy defining how long expired credit data should be kept, no archival mechanism, and no cleanup task. This is both a storage concern (expiring pools accumulate over time) and a compliance concern (some jurisdictions require financial records to be retained for specific periods, while others require deletion after a defined period). A retention policy should be defined with legal counsel, and a Celery Beat task should be created to enforce it.

**4. Mid-Cycle Credit Purchases**

Users cannot purchase additional credits in the middle of an active credit period. If a user with a monthly credit plan needs more credits before the current period ends, they must either wait for the period to expire or contact support for a manual adjustment. The system should support mid-cycle credit additions that create a supplementary pool or extend the remaining balance of the current pool, with appropriate proration logic.

### Medium Priority

**5. PDF Invoice Design Customization**

Credit invoices are generated using ReportLab with a hardcoded design in `billing/pdf_utils.py`. The layout, colors, and typography cannot be customized without code changes. For a multi-tenant or white-label deployment, the invoice design should be configurable per-product or per-domain, possibly through a template system or CSS-like styling parameters stored in the database.

**6. Email Format Standardization**

Email templates for credit approval/rejection are built inline in `billing/tasks.py` as hardcoded HTML strings. There is no template engine (Jinja2, Django templates), no shared layout system, and no preview mechanism. Adding a new email type requires duplicating the HTML structure. The emails should be migrated to Django template files with a shared base layout and block inheritance, enabling non-developers to customize email content and providing a preview endpoint for admin verification.

**7. Middleware Route Prefixes**

The Astro middleware (`src/middleware.ts`) uses simple string prefix matching (`PROTECTED_PREFIXES = ["/dashboard", "/admin", "/settings", "/profile"]`) to determine which routes require authentication. This approach is fragile — adding a new protected route requires manually updating the array, and a typo or omission silently leaves the route unprotected. The middleware should either read the route manifest from Astro's generated routing table or use a convention-based approach (e.g., all routes under `/dashboard` and `/admin` are protected by default, with explicit public route exceptions).

**8. Admin Redirect After Login**

When an admin user logs in, the standard post-login redirect takes them to `/dashboard` (the user dashboard) rather than `/admin` (the admin panel). Admin users must manually navigate to the admin panel. The login flow should check the user's role and redirect admin users to the admin panel by default, or respect a `redirect` query parameter in the login URL.

### Low Priority

**9. Sidebar Active State Bug**

On certain admin pages, the sidebar does not correctly highlight the active navigation item. The active state is determined by URL matching in the `AdminSidebar.astro` component, but the matching logic does not account for all dynamic route patterns (e.g., `/admin/users/1` should highlight the "Users" nav item, but the current implementation only matches exact paths). The fix requires updating the active state logic to use prefix-based matching with dynamic segment handling.

**10. Cookie Refresh Race Condition**

When a user has multiple tabs open and one tab triggers a token refresh, the other tabs may briefly have a stale access token. The `useAuth` composable stores the access token on the `window` object, which is shared across tabs within the same origin, but the refresh operation does not broadcast to other tabs. The next API call from a stale tab will receive a 401 and trigger its own refresh, which succeeds (because the refresh endpoint intentionally does not blacklist old refresh tokens) but creates an orphaned token. A `BroadcastChannel`-based solution could synchronize refresh events across tabs, eliminating redundant refresh calls and orphaned tokens.

---

# 20. Development Workflow

## 20.1 Local Development Setup

Setting up the SattaBase development environment requires both the backend (Django) and frontend (Astro + Vue) to run simultaneously. The project is designed for a split-terminal workflow: one terminal runs the Django ASGI server, another runs Celery workers, and a third runs the Astro dev server. The following steps guide a new developer from a fresh clone to a fully running local environment.

### Prerequisites

- **Python 3.10+**: The backend requires Python 3.10 or later due to usage of modern type hint syntax and `asyncio` features. Verify with `python3 --version`.
- **Node.js 22.12+**: The frontend requires Node.js 22.12 or later, as specified in the `engines` field of `package.json`. The Astro 6 runtime and Tailwind CSS v4 build pipeline depend on this version. Verify with `node --version`.
- **Redis**: Celery requires a running Redis instance on port 6379. On macOS, install via `brew install redis && brew services start redis`. On Ubuntu, use `sudo apt install redis-server && sudo systemctl start redis`. On Windows, use WSL2 or Docker (`docker run -d -p 6379:6379 redis:7`).
- **Git**: For cloning the repository and branch management.

### Backend Setup

1. **Clone and enter the backend directory**:
   ```bash
   git clone <repo-url> && cd backend
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   This installs all 84 packages listed in `requirements.txt`, including Django 5.2.13, django-ninja-extra 0.31.4, Stripe SDK 15.1.0, Celery 5.6.3, and all transitive dependencies. The local SDK package (`sattabase-sdk`) is referenced as a file dependency and must be available at the path specified in `requirements.txt` if you need SDK integration testing.

4. **Configure environment variables**:
   ```bash
   cp .env.example .env   # If an example file exists
   # Or create .env manually with the minimal set:
   ```
   The minimal `.env` for local development requires only three variables:
   ```env
   SB_PORT=8081
   SB_CORS_ALLOW_ALL_ORIGINS=True
   SB_DEBUG=True
   ```
   With `SB_DEBUG=True`, the backend uses SQLite (auto-created as `db.sqlite3`), the email backend switches to console output, and detailed error pages are shown. No Stripe keys are required for basic development — Stripe-dependent features will return errors but will not crash the server.

5. **Run database migrations**:
   ```bash
   python manage.py migrate
   ```
   This creates all tables using SQLite. The first migration creates the core schema, and subsequent migrations add features like the credit system, bank settings, service credentials, and revenue recognition entries.

6. **Seed demo data** (optional but recommended):
   ```bash
   python manage.py billing_seed_data
   python manage.py seed_exchange_rates
   ```
   The first command creates sample Products (Satta Finance, Satta Analytics, Satta Ledger), Plans (Free/Standard-Pro tiers), AccessEntry records, ServiceDomains, BankSettings, and CreditPool data. The second command fetches live exchange rates from the open.er-api.com API and populates the `ExchangeRate` table. See Section 20.3 for full details on seed commands.

7. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to set email, first name, last name, and password. This user will have `is_staff=True` and `is_superuser=True` for Django admin access, and the `role` field defaults to `owner`.

8. **Start the backend server**:
   ```bash
   python manage.py runserver
   ```
   This starts Daphne on the port specified by `SB_PORT` (default 8081). The API is available at `http://localhost:8081/api/v1/` and the Django admin at `http://localhost:8081/admin/`.

9. **Start Celery workers** (in a separate terminal):
   ```bash
   cd backend && source venv/bin/activate
   celery -A base worker --loglevel=info
   ```
   For scheduled tasks, also start the beat scheduler:
   ```bash
   celery -A base beat --loglevel=info
   ```

### Frontend Setup

1. **Enter the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install Node.js dependencies**:
   ```bash
   npm install
   ```
   This installs Astro 6, Vue 3, Tailwind CSS 4, TypeScript, and the `@astrojs/node` standalone adapter.

3. **Configure the API URL** (if needed):
   The frontend's API client in `lib/api.ts` defaults to `http://localhost:8081/api/v1` for the backend URL. If your backend runs on a different port, update the `API_BASE_URL` constant or set the appropriate environment variable.

4. **Start the development server**:
   ```bash
   npm run dev
   ```
   This starts the Astro dev server (typically on port 4321) with hot module replacement. The frontend is available at `http://localhost:4321/`.

### Verifying the Setup

After both servers are running, verify the full stack by:
1. Navigating to `http://localhost:4321/auth/register` and creating an account
2. Checking the backend console for the email verification link (console email backend)
3. Logging in and verifying the dashboard loads
4. Navigating to `/dashboard/billing/plans` to verify the product catalog (if seeded)
5. Accessing `/admin` with the superuser account to verify the admin panel

## 20.2 Database Migrations

SattaBase uses Django's migration system to manage schema evolution. Migrations are auto-generated from model changes and stored in each app's `migrations/` directory. The project currently has migrations across three apps:

- **`billing/migrations/`**: 25 migration files (0001_initial through 0025), covering the evolution from the initial Product/Plan/Subscription schema to the full credit system, bank settings, service credentials, webhook logging, revenue recognition, and invoice line items.
- **`users/migrations/`**: 13 migration files (0001_initial through 0013), covering the custom User model, slug field, email changes, OTP, password reset tokens, email change tokens, and the account lockout fields (`failed_login_attempts`, `locked_until`).
- **`common/migrations/`**: Contains only `__init__.py` since common provides abstract base models that do not generate their own migrations.
- **`api/migrations/`**: Contains only `__init__.py` since the api app has no models.

### Creating New Migrations

When you modify any model in `billing/models.py` or `users/models.py`, generate migrations automatically:

```bash
python manage.py makemigrations
```

Django detects model changes by comparing the current model definitions against the migration history. It generates a new numbered migration file with `CreateModel`, `AddField`, `AlterField`, or `RunPython` operations. Always review the generated migration before applying it — especially for non-nullable field additions (which may require a default value or a `RunPython` data migration) and for field removals (which are irreversible in production).

### Applying Migrations

```bash
# Apply all pending migrations
python manage.py migrate

# Apply migrations for a specific app only
python manage.py migrate billing

# Roll back to a specific migration
python manage.py migrate billing 0019
```

In development (SQLite), migrations apply instantly. In production (PostgreSQL), long-running migrations that add columns with defaults to large tables should be carefully planned — Django's `AddField` with a default uses `ALTER TABLE ... SET DEFAULT`, which acquires an `ACCESS EXCLUSIVE` lock on PostgreSQL.

### Migration Naming Convention

Auto-generated migrations receive names like `0002_alter_user_email.py`. For significant schema changes that require a data migration or manual review, rename the file descriptively before committing, such as `0019_credit_system.py` instead of `0019_credit_creditpool_creditinvoice.py`. The billing app already follows this convention for several migrations.

### Squashing Migrations

As the number of migrations grows, consider squashing them periodically:
```bash
python manage.py squashmigrations billing 0001 0025
```
This creates an optimized migration that replaces the historical chain. Squashing should be done between major releases, not during active development.

## 20.3 Seed Data

SattaBase provides two management commands for populating the database with realistic development data. Both commands are idempotent — they use `get_or_create` and `update_or_create` internally, so running them multiple times produces the same result without duplicates.

### `billing_seed_data`

**Location**: `common/management/commands/billing_seed_data.py`

**Usage**:
```bash
python manage.py billing_seed_data
python manage.py billing_seed_data --clear      # Delete all billing data, then re-seed
python manage.py billing_seed_data --verbose     # Print one line per created record
```

This command creates the following seed data:

**Products and Plans**: Three products are defined in the `SEED_DATA` list — Satta Finance, Satta Analytics, and Satta Ledger. Each product has a Free plan, a mid-tier plan (Standard or Growth), and a Pro/Enterprise plan. Plans include realistic pricing ($0, $9-$57, $29-$99 monthly), billing cycles (monthly, yearly), trial periods (0, 14, or 30 days), feature dictionaries, and comprehensive AccessEntry records. For example, the Satta Ledger Free plan has 25 AccessEntry records controlling per-feature limits like `max_transactions` (50), `max_accounts` (3), `max_budgets` (1), and boolean feature flags like `investments` (false) and `vault` (false).

**Service Domains**: Each product gets a primary domain (`finance.sattabase.tld`, `analytics.sattabase.tld`, `ledger.sattaspace.com`). Satta Ledger also includes `localhost:4322` as a secondary domain for local development testing of SDK integration.

**Bank Settings**: Three bank account records are created from `BANK_SETTINGS_SEED_DATA` — two active (First National Bank, International Business Bank) and one inactive (Legacy Savings Bank). Bank account numbers are stored using the `EncryptedCharField` and are encrypted at rest using the `CRYPTOGRAPHY_KEY` from settings.

**Credit Data**: If users exist in the database, the command also creates sample credit purchase requests (2 pending) and active credit pools (2 approved), using the `CREDIT_SEED_DATA` definition. This provides realistic test data for the credit management workflows.

The `--clear` flag is destructive — it deletes all billing-related data (Products, Plans, Subscriptions, CreditPools, etc.) before re-seeding. Use it only in development when you need a clean slate.

### `seed_exchange_rates`

**Location**: `common/management/commands/seed_exchange_rates.py`

**Usage**:
```bash
python manage.py seed_exchange_rates
python manage.py seed_exchange_rates --base=EUR   # Override base currency
```

This command calls `CurrencyService.update_exchange_rates()`, which fetches live rates from the open.er-api.com API and upserts them into the `ExchangeRate` table. The default base currency is USD (configurable via `BASE_CURRENCY` in settings). The `--base` flag allows overriding the base currency for a single run without modifying settings.

The command should be run once after initial migration to populate the exchange rate table. After that, the Celery Beat task `update_exchange_rates_task` keeps the rates updated daily. If the external API is unreachable, the command fails with a clear error message, and existing rates remain unchanged.

---

# 21. Contributing Guidelines

## 21.1 Code Style

SattaBase follows consistent code style conventions across the backend and frontend to ensure readability and maintainability. All contributors are expected to adhere to these standards.

### Backend (Python / Django)

- **Formatter**: Use `black` with default settings (88-character line length). No configuration file is needed — run `black .` from the backend directory before committing.
- **Import Ordering**: Use `isort` with the `black` profile to ensure import ordering is compatible with `black`'s formatting. The import order is: standard library, third-party, Django, local application. Within each group, imports are alphabetically sorted.
- **Type Hints**: All controller methods and service methods must include return type hints. Pydantic schema fields must include type annotations. Model field definitions do not require additional type hints (Django's field classes are self-documenting).
- **Naming Conventions**: Models use `PascalCase` (e.g., `CreditPurchaseRequest`). Controllers use `PascalCase` with a suffix (`BillingProtectedController`). Services use `PascalCase` with a `Service` suffix (`BillingService`, `CurrencyService`). Functions and methods use `snake_case` (`get_user_subscription`). Constants use `UPPER_SNAKE_CASE` (`SUBSCRIPTION_STATUS_CHOICES`). Celery task names use `snake_case` (`consume_credit_periods_task`).
- **Docstrings**: All controller classes and public service methods must have docstrings. Use triple-double-quotes with a one-line summary. For complex methods, add a "Returns" and "Raises" section. Management commands must have module-level docstrings explaining usage and options (see `billing_seed_data.py` for the canonical example).
- **Async Patterns**: All controller methods are `async def`. Database operations must use `@sync_to_async` for ORM calls that involve `transaction.atomic()`, `select_for_update()`, or bulk writes. Simple read-only queries may use `sync_to_async(lambda: Model.objects.filter(...))` inline. Never use `async with transaction.atomic()`.
- **Error Handling**: Use the custom exception hierarchy from `common/exceptions.py` (e.g., `BillingError`, `SubscriptionError`, `CreditError`). Raise specific exceptions with descriptive messages. Never raise raw `Exception` or `ValueError` in controller or service code — wrap them in the appropriate domain exception.

### Frontend (TypeScript / Vue / Astro)

- **Formatter**: Use Prettier with the project's `.prettierrc` configuration. Run `npx prettier --write "src/**/*.{ts,vue,astro}"` before committing.
- **Component Naming**: Vue components use `PascalCase` file names (`LoginForm.vue`, `AdminDashboard.vue`). Astro pages use `kebab-case` file names for directories (`credit-requests/`) and `PascalCase` or `kebab-case` for page files (the convention is `index.astro` for list pages, `[id].astro` or `[slug].astro` for detail pages).
- **Composable Naming**: All composables start with `use` prefix (`useAuth`, `useSubscription`, `useFormErrors`). Each composable returns an object with reactive refs and methods. The file name matches the composable name (`useAuth.ts`).
- **API Client Naming**: API functions in `lib/` use `camelCase` (`getUserSubscription`, `cancelSubscription`). Each function is named with a verb prefix (`get`, `create`, `update`, `delete`, `post`) followed by the resource name.
- **TypeScript Strictness**: The project uses `strict: true` in `tsconfig.json`. Avoid `any` types — use proper interfaces or type assertions. API response types should be defined inline or as exported interfaces in the relevant `lib/` file.
- **CSS**: Use Tailwind CSS utility classes exclusively. Avoid inline styles and custom CSS classes unless absolutely necessary (e.g., animations that cannot be expressed as utilities). Use the design tokens defined in `global.css` under `@theme` for colors, spacing, and typography.

## 21.2 Git Workflow

### Branch Naming

All development work should be done on feature branches. Branch names must follow this convention:

```
<type>/<ticket-id>-<short-description>
```

Where `<type>` is one of:
- `feat`: New feature (e.g., `feat/SB-142-credit-transfer`)
- `fix`: Bug fix (e.g., `fix/SB-89-login-redirect`)
- `refactor`: Code restructuring without behavior change (e.g., `refactor/SB-55-extract-service`)
- `docs`: Documentation changes (e.g., `docs/SB-201-api-reference`)
- `chore`: Build, CI, or tooling changes (e.g., `chore/SB-33-update-deps`)

The `main` branch is protected and requires a passing CI check and at least one approval before merging. Never commit directly to `main`.

### Commit Messages

Follow the Conventional Commits specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Examples:
- `feat(billing): add credit transfer API endpoint`
- `fix(auth): resolve login redirect on admin subscription view`
- `refactor(services): extract subscription cancellation to BillingService`
- `docs(api): update endpoint quick reference table`

The `<scope>` should match one of the Django apps (`billing`, `users`, `common`, `api`) or a frontend area (`frontend`, `admin`, `composables`). The `<description>` should be in imperative mood ("add" not "added", "fix" not "fixed").

### Commit Frequency

Make small, focused commits. Each commit should represent a single logical change. If you are adding a new feature and fixing an unrelated bug in the same session, create separate branches and separate commits. This makes it easier to review, revert, and cherry-pick changes.

## 21.3 PR Review Process

### Before Submitting a PR

1. **Run the test suite**: `python manage.py test` (backend) and verify no regressions.
2. **Check code style**: Run `black --check .` and `isort --check .` (backend), and `npx prettier --check "src/**/*.{ts,vue,astro}"` (frontend).
3. **Test manually**: Verify the feature works in the local development environment. For billing changes, test both the happy path and error scenarios (Stripe API errors, invalid input, concurrent requests).
4. **Update documentation**: If your change adds a new API endpoint, model field, or architectural pattern, update the relevant section of this developer documentation.
5. **Write a clear PR description**: Include the "what" (what does this PR change?), the "why" (why is this change needed?), and the "how" (how was it implemented?). Reference the relevant ticket number.

### Review Criteria

Reviewers should check for:

- **Correctness**: Does the code do what the PR claims? Are edge cases handled?
- **Security**: Does the PR introduce any authentication bypass, injection vulnerability, or data exposure? Are new endpoints protected with the correct permission classes?
- **Async Safety**: If the PR modifies controllers, verify that `transaction.atomic()` and `select_for_update()` are used correctly with `@sync_to_async`. Never approve code that uses `async with transaction.atomic()`.
- **Stripe Integration**: If the PR modifies billing logic, verify the "Stripe first, DB second" pattern is maintained. Stripe API calls should happen before database writes, and webhook reconciliation should handle failure cases.
- **Performance**: Are there N+1 queries? Should `select_related` or `prefetch_related` be added? Are database queries inside loops?
- **Breaking Changes**: Does the PR change any API response format, remove any endpoint, or rename any field? If so, document the migration path clearly.
- **Test Coverage**: Does the PR include tests for new functionality? Are error paths tested?

### Approval and Merge

A PR requires at least one approval from a team member with domain knowledge of the affected area (billing, auth, frontend, etc.). For billing-related changes that affect payment processing or refund logic, a second approval is recommended (following the two-person rule philosophy). Once approved, the PR is merged via squash merge to keep the `main` branch history clean.

---

# 22. Glossary

## 22.1 Domain Terms

**Access Entry**: A fine-grained permission record attached to a Plan that defines whether and to what extent a feature is available. Each AccessEntry has a `key` (feature identifier), a `value_type` (boolean, integer, or string), and the corresponding value. Sister domains query these entries to determine what features a subscriber can access. The special key `all` with `boolean_value=true` acts as a wildcard, granting access to every feature on the plan.

**Billing Cycle**: The recurrence interval for a subscription or credit plan. SattaBase supports three billing cycles: `monthly` (billed every month), `yearly` (billed every year), and `lifetime` (one-time payment with no recurrence). The billing cycle determines the duration of subscription periods, credit consumption intervals, and revenue recognition calculations.

**Credit Invoice**: A formal invoice document generated when a credit purchase request is approved. The invoice records the credit amount, currency, credit periods allocated, payment source, and bank details. It is generated as a PDF using ReportLab (`billing/pdf_utils.py`) and can be downloaded by the user from the credits dashboard. Credit invoices serve as financial records for bank-transfer purchases and are separate from Stripe invoices.

**Credit Period**: The fundamental unit of credit consumption. Each credit purchase allocates a number of periods (e.g., 3 months, 12 months). The `consume_credit_periods` Celery task runs daily, decrementing the `remaining_periods` on active credit pools by one for each day that matches the consumption schedule. When `remaining_periods` reaches zero, the pool is marked as expired.

**Credit Pool**: A container for purchased credits that tracks the total amount, remaining balance, and remaining periods. Each pool is associated with a User, Product, and Plan. Credits in a pool are consumed period-by-period (daily decrement) and cannot exceed the allocated periods. A user can have multiple active credit pools for different products simultaneously.

**Credit Purchase Request**: A formal request submitted by a user to purchase credits via bank transfer. The request includes the product, plan, amount, currency, bank account details, and payment proof (transaction reference and notes). Requests require admin approval before credits are allocated. This mechanism provides an alternative payment pathway for users who cannot use international credit cards via Stripe.

**Credit Transaction**: An immutable ledger entry recording a credit operation. Types include `purchase` (credits added from bank transfer), `consumption` (period-based deduction), `adjustment` (admin manual change), `refund` (credits returned), and `expiry` (remaining credits written off). Every credit transaction references a CreditPool and creates an auditable trail.

**Dunning**: The process of communicating with subscribers whose payments have failed. SattaBase implements a staged dunning workflow with incrementally stronger actions: Step 0 (payment failure detected, subscription marked `past_due`), Step 1 (reminder email after 3 days), Step 2 (warning email after 7 days), Step 3 (final notice after 14 days), Step 4 (subscription canceled after 30 days). The `process_dunning` Celery task drives this progression.

**Exchange Rate**: A stored currency conversion rate between the base currency (USD) and a target currency. Exchange rates are fetched daily from an external API, stored in the `ExchangeRate` model, and used by `CurrencyService` to convert plan prices and subscription amounts between currencies. The system supports 35+ currencies including zero-decimal currencies (JPY, KRW, VND).

**Plan**: A specific pricing tier within a Product. A Plan defines the price (in cents), currency, billing cycle, trial period, feature set, and access entries. Plans are linked to Stripe Price objects via `stripe_price_id`. Users subscribe to Plans, not Products — a Product can have multiple Plans (e.g., Free, Standard, Pro) representing different feature tiers and price points.

**Product**: A top-level entity representing a sister application or service within the SattaSpace ecosystem. Each Product has a name, slug, description, icon, home URL, and an optional `stripe_product_id` linking it to Stripe. Products are the organizing principle for Plans, Subscriptions, and ServiceDomains. Examples: Satta Finance, Satta Analytics, Satta Ledger.

**Revenue Recognition Entry**: An ASC 606-compliant journal entry recording the daily portion of earned revenue from an active subscription. The `recognize_revenue` Celery task creates one entry per active subscription per day, calculated as `price / days_in_period`. Subscriptions in `past_due` status are excluded from recognition. Entries include a `source` field tracking whether they were created by the daily task, a webhook event, or a manual adjustment.

**Safe Plan Change**: The two-step process for changing a subscription plan without service interruption or double-charging. Step 1: `preview_plan_change` returns a proration preview showing the credit for the remaining time on the current plan and the charge for the new plan. Step 2: `confirm_plan_change` applies the change at Stripe and updates the local database. The preview step is read-only and does not modify any state, allowing users to review the financial impact before committing.

**Service Credential**: An API key that authenticates a sister domain's requests to the SattaBase API. Each credential has a `key_prefix` (e.g., `sb_live_`), a `key_hash` (SHA-256 of the full key for secure storage), and is associated with a ServiceDomain. Credentials support CRUD operations and can be revoked by admins. The `service_credential_middleware` validates incoming API keys by computing their SHA-256 hash and looking up the matching credential.

**Service Domain**: A registered domain name associated with a Product that is authorized to integrate with SattaBase via the SDK. ServiceDomains enable dynamic CORS resolution (allowing requests from the registered domain), API key validation (keys are scoped to a domain), and SSO authorization code flow. Each Product can have multiple ServiceDomains, with exactly one marked as `is_primary`.

**Sister Domain**: An external web application (e.g., Satta Ledger, Satta Analytics) that integrates with SattaBase for authentication, billing, and subscription management. Sister domains use the SattaBase SDK to authenticate users via SSO, check subscription access via API keys, and receive webhook notifications for credential events. They do not manage their own billing — SattaBase is the centralized billing authority.

**Subscription**: A relationship between a User and a Plan that grants access to a Product for a defined period. Subscriptions have statuses (active, past_due, canceled, trialing, paused, expired) and are synchronized with Stripe via `stripe_subscription_id`. The subscription lifecycle is managed by a combination of user actions (subscribe, cancel, change plan), Stripe webhooks (payment success/failure, renewal), and Celery tasks (dunning, expiry).

**Two-Person Rule**: A security principle requiring two separate authorized individuals to approve a sensitive action. In SattaBase, this applies to refunds: one admin requests the refund, and a different admin approves it. The `Refund` model tracks both the `requested_by` and `approved_by` users, and the system prevents an admin from approving their own refund request.

## 22.2 Acronyms

| Acronym | Full Form | Context |
|---|---|---|
| ASC 606 | Accounting Standards Codification Topic 606 | Revenue from Contracts with Customers — the GAAP standard for revenue recognition that SattaBase follows |
| ASGI | Asynchronous Server Gateway Interface | The Python async server interface used by Daphne to serve the Django application |
| CORS | Cross-Origin Resource Sharing | HTTP mechanism that controls which external domains can access the API; dynamically resolved for service domains |
| CSRF | Cross-Site Request Forgery | Web security vulnerability; CSRF protection is disabled on API endpoints (using JWT instead) but enabled on Django admin |
| DSGVO | Datenschutz-Grundverordnung | German term for GDPR; referenced in the context of data deletion compliance |
| GAAP | Generally Accepted Accounting Principles | The accounting framework that ASC 606 revenue recognition rules fall under |
| GDPR | General Data Protection Regulation | European Union data privacy regulation; SattaBase provides GDPR compliance via Stripe data deletion |
| HMAC | Hash-Based Message Authentication Code | The signing algorithm used for webhook dispatch to sister domains (`common/webhooks.py`) |
| httpOnly | HTTP-Only Cookie Flag | Browser security flag that prevents JavaScript from accessing the cookie; used for refresh tokens |
| JWT | JSON Web Token | The token format used for user authentication (access token + refresh token pair with rotation) |
| MRR | Monthly Recurring Revenue | A key SaaS metric tracked in the admin metrics dashboard |
| OTP | One-Time Password | A short-lived numeric code used for email verification and password reset flows |
| ORM | Object-Relational Mapping | Django's database abstraction layer that maps Python model classes to database tables |
| PR | Pull Request | A code review mechanism where changes are proposed on a branch before merging to main |
| SaaS | Software as a Service | The delivery model for SattaBase and its sister applications |
| SDK | Software Development Kit | The SattaBase SDK package (`sattabase-sdk`) that sister domains integrate for authentication and billing |
| SSO | Single Sign-On | The authentication flow allowing users to log in on SattaBase and be automatically authenticated on sister domains |
| SSR | Server-Side Rendering | The Astro rendering mode where pages are generated on the server for each request |
| WSGI | Web Server Gateway Interface | The Python synchronous server interface; available as a fallback via Gunicorn |

---

# 23. Changelog & Version History

## 23.1 Version History

SattaBase uses semantic versioning (`MAJOR.MINOR.PATCH`) for release tracking. The project is currently in active development at version `0.0.1`, meaning the API is not yet stable and breaking changes may occur without a major version bump. The following version history documents significant milestones, architectural changes, and feature additions in reverse chronological order.

### v0.0.1 (2026-06-05) — Initial Development Release

This is the first documented version of the SattaBase platform, representing the culmination of the initial development phase. The codebase includes a fully functional Django backend with five logical domains (billing, users, common, api, SDK integration), a complete Astro + Vue frontend with 25 page routes and 39 Vue components, Stripe payment integration, and a credit system for bank-transfer purchases. Key features delivered in this version:

**Backend**:
- Complete Django 5.2 project with django-ninja-extra async API controllers
- 20+ models including Product, Plan, Subscription, CreditPool, CreditInvoice, CreditTransaction, CreditPurchaseRequest, ServiceCredential, ServiceDomain, RevenueRecognitionEntry, Refund, AdminAuditLog, WebhookEventLog, BankSettings, ExchangeRate, InvoiceLineItem, and AccessEntry
- Full Stripe integration: Checkout sessions, Customer Portal, webhook processing pipeline with 4 event-type handlers (charge, checkout, invoice, subscription), error handling with `StripeErrorHandler`, and GDPR data deletion
- Safe plan change flow with proration preview and confirmation
- ASC 606 revenue recognition with daily task and past-due exclusion
- Credit system with bank-transfer purchase requests, admin approval workflow, period-based consumption, and PDF invoice generation via ReportLab
- Two-person rule for refund approval
- Multi-currency support with daily exchange rate updates and zero-decimal currency handling
- Celery task queue with 8 scheduled/on-demand tasks
- Hybrid JWT + httpOnly cookie authentication with rotation and blacklisting
- API key authentication (SHA-256 hashed) with middleware-level validation
- Dynamic CORS resolution based on ServiceDomain records
- SSO authorization code flow for sister domain integration
- HMAC webhook dispatch for credential events to sister domains
- Account lockout after 5 failed login attempts (CRIT-02)
- Encrypted model fields for bank account numbers
- Sliding window rate limiting
- Comprehensive audit logging via `AdminAuditLog`
- Custom exception hierarchy with 9 domain-specific exceptions

**Frontend**:
- Astro 6 SSR application with Vue 3 islands architecture
- 25 page routes across auth (7), dashboard (7), and admin (11) sections
- 39 Vue components (22 user-facing, 17 admin)
- 4 layout systems (Base, Auth, Dashboard, Admin) with frozen shell pattern
- 15 composables with window-level shared state for View Transition resilience
- 6 API client modules (api, auth, billing, credits, admin, toast)
- 3-layer session guard (Astro middleware, SessionGuard.vue, API client)
- Tailwind CSS 4 with `@theme` design tokens and brand palette
- Dark mode support

**Infrastructure**:
- Docker configuration with multi-stage builds
- Celery Beat scheduler with django-celery-beat
- Redis dual-role (broker + cache)
- PostgreSQL production / SQLite development database switching
- Comprehensive `.env`-based configuration with `SB_` prefix

**Known Issues at Release**:
- Admin user detail subscription view "View" button redirects to login page (unresolved)
- Sidebar active state does not match on all dynamic routes
- No frontend testing infrastructure
- Cookie refresh race condition across multiple browser tabs
- No admin override for minimum commitment periods
- No credit transferability between users
- No data retention policy for expired credit data
- No mid-cycle credit purchase support

**Bug Fixes During Development**:
- Fixed 7 `AttributeError: __aenter__` bugs caused by incorrect `async with transaction.atomic()` usage across billing controllers and admin controllers
- Fixed `AdminConfirmDialog.vue` slot bug where the default slot content was not rendering
- Fixed `SubscriptionDetailAdmin.vue` issues with data loading and status display

This version represents a feature-complete billing and subscription management platform ready for internal testing and integration with the first sister domain (Satta Ledger). Subsequent versions will focus on production hardening, frontend testing, and the remaining technical debt items documented in Section 19.2.

---

# Appendix A: Environment Variables Reference

All SattaBase environment variables use the `SB_` prefix to avoid collisions with system-level or third-party variables. They are loaded by `django-environ` from a `.env` file at the project root (parent of the `backend/` directory) or from the process environment. The `settings.py` file reads each variable using `env()` with a default value for development convenience. Variables marked **Required** must be set in production; those marked **Optional** have sensible defaults.

## Core Application

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_SECRET_KEY` | string | — | **Yes** | Django secret key for cryptographic signing (session cookies, CSRF tokens, password reset tokens). Must be a long, random, unique string in production. |
| `SB_DEBUG` | bool | `False` | No | Enables Django debug mode. When `True`, uses SQLite, console email backend, detailed error pages, and relaxed security settings. Never set to `True` in production. |
| `SB_PORT` | int | `8081` | No | The port on which Daphne serves the backend. Used by the `runserver` command in development. |
| `SB_ALLOWED_HOSTS` | list | — | **Yes** | Comma-separated list of host/domain names that this Django site can serve. Required in production to prevent HTTP Host header attacks. |

## Frontend & CORS

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `PUBLIC_SITE_URL_SB` | string | `http://localhost:4321` | No | The frontend's public URL. Automatically appended to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`. In production, set to `https://your-frontend-domain.com`. |
| `SB_CORS_ALLOWED_ORIGINS` | list | `http://localhost:4321`, `http://localhost:8086`, `http://127.0.0.1:4321`, `http://127.0.0.1:8086` | No | Comma-separated list of origins allowed for CORS. Must include the frontend URL and any admin panel URLs. |
| `SB_CSRF_TRUSTED_ORIGINS` | list | Same defaults as CORS | No | Comma-separated list of trusted origins for CSRF. Must include the frontend URL. |
| `SB_CORS_ALLOW_ALL_ORIGINS` | bool | `False` | No | If `True`, allows all origins (incompatible with cookie-based auth — browsers reject `Access-Control-Allow-Credentials: true` with wildcard origin). Only for development debugging. |

## Database

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_DB_NAME` | string | — | **Yes** (prod) | PostgreSQL database name. Ignored in DEBUG mode (SQLite is used instead). |
| `SB_DB_USER` | string | — | **Yes** (prod) | PostgreSQL database user. |
| `SB_DB_PASSWORD` | string | — | **Yes** (prod) | PostgreSQL database password. |
| `SB_DB_HOST` | string | — | **Yes** (prod) | PostgreSQL host (e.g., `localhost` or a cloud DB endpoint). |
| `SB_DB_PORT` | string | — | **Yes** (prod) | PostgreSQL port (typically `5432`). |

## Redis & Celery

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_REDIS_HOST` | string | `localhost` | No | Redis host for Celery broker, Django cache, and Channels. |
| `SB_REDIS_PORT` | int | `6379` | No | Redis port. DB 1 is used for Celery broker, DB 2 for Django cache. |

## JWT Authentication

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_JWT_SIGNING_KEY` | string | Falls back to `SB_SECRET_KEY` | **Yes** (prod) | The key used to sign JWT tokens. In production, must be set explicitly (Django raises `ImproperlyConfigured` if not set when `DEBUG=False`). In development, defaults to `SECRET_KEY` for convenience. |
| `SB_JWT_ACCESS_TOKEN_MINUTES` | int | `60` | No | Access token lifetime in minutes. Short-lived tokens reduce the window for token theft. |
| `SB_JWT_REFRESH_TOKEN_DAYS` | int | `7` | No | Refresh token lifetime in days. Stored as an httpOnly cookie. |
| `SB_JWT_ROTATE_REFRESH_TOKENS` | bool | `True` | No | When `True`, each refresh request issues a new refresh token and blacklists the old one. |
| `SB_JWT_BLACKLIST_AFTER_ROTATION` | bool | `True` | No | When `True`, rotated refresh tokens are added to the blacklist to prevent replay. |
| `SB_JWT_ALGORITHM` | string | `HS256` | No | The JWT signing algorithm. Should be `HS256` unless you have specific requirements. |

## Encryption & Security

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_CRYPTOGRAPHY_KEY` | string | Derived from `SECRET_KEY` via SHA-256 | **Yes** (prod) | The Fernet encryption key used by `EncryptedCharField` to encrypt bank account numbers at rest. Should be a 32-byte key (64 hex characters). If not set, a key is derived from `SECRET_KEY` (not recommended for production). |
| `SB_SECURE_HSTS_SECONDS` | int | `31536000` (1 year) | No | Duration for the `Strict-Transport-Security` header. Only active when `DEBUG=False`. |

## Stripe

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_STRIPE_SECRET_KEY` | string | `""` | **Yes** (prod) | Stripe secret key for server-side API calls (`sk_live_...` or `sk_test_...`). |
| `SB_STRIPE_PUBLISHABLE_KEY` | string | `""` | No | Stripe publishable key for client-side Checkout (`pk_live_...` or `pk_test_...`). |
| `SB_STRIPE_WEBHOOK_SECRET` | string | `""` | **Yes** (prod) | Stripe webhook signing secret (`whsec_...`) used to verify webhook event signatures. |
| `SB_STRIPE_APP_DOMAIN` | string | Same as `PUBLIC_SITE_URL_SB` | No | Domain used for Stripe Checkout success/cancel redirect URLs. |
| `SB_STRIPE_PORTAL_RETURN_URL` | string | `{APP_DOMAIN}/dashboard/billing` | No | URL where Stripe Customer Portal redirects after session ends. |
| `SB_STRIPE_SUCCESS_URL` | string | `{APP_DOMAIN}/dashboard/billing?checkout=success` | No | URL for Stripe Checkout success redirect. |
| `SB_STRIPE_CANCEL_URL` | string | `{APP_DOMAIN}/dashboard/billing?checkout=canceled` | No | URL for Stripe Checkout cancel redirect. |
| `SB_STRIPE_TAX_ENABLED` | bool | `False` | No | Must be `True` when Stripe Tax is activated in the Stripe Dashboard. Controls whether `automatic_tax` is enabled at checkout. |

## Email (SMTP)

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_EMAIL_HOST` | string | `smtp.gmail.com` | No | SMTP server hostname. |
| `SB_EMAIL_PORT` | int | `587` | No | SMTP port. Port 587 uses STARTTLS; port 465 uses implicit SSL. These are mutually exclusive. |
| `SB_EMAIL_USE_TLS` | bool | `True` | No | Enable STARTTLS (for port 587). Mutually exclusive with `SB_EMAIL_USE_SSL`. |
| `SB_EMAIL_USE_SSL` | bool | `False` | No | Enable implicit SSL (for port 465). Mutually exclusive with `SB_EMAIL_USE_TLS`. |
| `SB_EMAIL_HOST_USER` | string | `""` | **Yes** (prod) | SMTP authentication username (typically the email address). |
| `SB_EMAIL_HOST_PASSWORD` | string | `""` | **Yes** (prod) | SMTP authentication password or app-specific password. |
| `SB_DEFAULT_FROM_EMAIL` | string | `noreply@sattabase.com` | No | Default sender address for outgoing emails. |

## Rate Limiting

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_RATE_LIMIT_LOGIN_ATTEMPTS` | int | `10` | No | Maximum login attempts per IP within the login window. |
| `SB_RATE_LIMIT_LOGIN_WINDOW` | int | `900` (15 min) | No | Sliding window in seconds for login rate limiting. |
| `SB_RATE_LIMIT_REGISTER_ATTEMPTS` | int | `5` | No | Maximum registration attempts per IP within the registration window. |
| `SB_RATE_LIMIT_REGISTER_WINDOW` | int | `3600` (1 hour) | No | Sliding window in seconds for registration rate limiting. |
| `SB_RATE_LIMIT_PASSWORD_RESET_ATTEMPTS` | int | `5` | No | Maximum password reset requests per IP within the window. |
| `SB_RATE_LIMIT_PASSWORD_RESET_WINDOW` | int | `3600` (1 hour) | No | Sliding window in seconds for password reset rate limiting. |
| `SB_RATE_LIMIT_SENSITIVE_ATTEMPTS` | int | `5` | No | Maximum attempts for sensitive operations (e.g., email change, account deletion). |
| `SB_RATE_LIMIT_SENSITIVE_WINDOW` | int | `3600` (1 hour) | No | Sliding window in seconds for sensitive operation rate limiting. |
| `SB_RATE_LIMIT_SDK_ATTEMPTS` | int | `1000` | No | Maximum API requests per SDK credential within the window. Higher than per-IP limits because SDK traffic proxies many users. |
| `SB_RATE_LIMIT_SDK_WINDOW` | int | `3600` (1 hour) | No | Sliding window in seconds for SDK rate limiting. |

## API Key & SDK

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_API_KEY_ENFORCED` | bool | `False` | No | When `True`, requests with invalid or revoked `X-API-Key` receive an immediate `403`. When `False`, invalid keys log warnings but the request passes through. **Must be `True` in production** when SDK consumers are deployed. |

## Billing & Currency

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_BASE_CURRENCY` | string | `USD` | No | The base currency for all plan prices. Exchange rates are fetched relative to this currency. |
| `SB_EXCHANGE_RATE_API_URL` | string | `https://open.er-api.com/v6/latest` | No | The external API endpoint for fetching daily exchange rates. The default provider requires no API key. |
| `SB_TOS_VERSION` | string | `1.0` | No | Current Terms of Service version. Increment when updating ToS. Tracked in subscription records for audit. |

## Token Expiry

| Variable | Type | Default | Required | Description |
|---|---|---|---|---|
| `SB_PASSWORD_RESET_TOKEN_EXPIRY` | int | `900` (15 min) | No | Password reset OTP validity in seconds. |
| `SB_EMAIL_CHANGE_TOKEN_EXPIRY` | int | `3600` (1 hour) | No | Email change OTP validity in seconds. |

---

# Appendix B: API Endpoint Quick Reference Table

All endpoints are served under the base URL `/api/v1/`. Authentication requirements are noted per controller: **Public** (no auth), **JWT** (Bearer token required), **Staff** (JWT + `is_staff=True`), **API Key** (`X-API-Key` + `X-Service-Domain` headers), or **Signature** (Stripe webhook signature verification).

## AuthController — `/api/v1/auth/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/auth/choices` | Public | Timezone, currency, language choices for registration forms |
| POST | `/auth/register` | Public | Register a new account (sends email OTP) |
| POST | `/auth/login` | Public | Login — returns access token; refresh in httpOnly cookie |
| POST | `/auth/token/refresh` | Public | Exchange refresh token for new pair (body-based) |
| POST | `/auth/token/refresh-cookie` | Public | Refresh using httpOnly cookie (preferred for browsers) |
| POST | `/auth/token/verify` | Public | Verify access token validity |
| POST | `/auth/token/blacklist` | JWT | Blacklist a refresh token |
| POST | `/auth/logout` | JWT | Logout — blacklists refresh cookie, clears cookies |
| POST | `/auth/password-reset/request` | Public | Request password reset OTP via email |
| POST | `/auth/password-reset/confirm` | Public | Confirm password reset with OTP |
| POST | `/auth/verify-email/request` | JWT | Request email verification OTP |
| POST | `/auth/verify-email/confirm` | JWT | Confirm email with OTP |
| POST | `/auth/authorize` | JWT | Generate SSO authorization code for sister domain |
| POST | `/auth/token/exchange` | Public | Exchange SSO auth code for tokens (cross-domain) |

## UserController — `/api/v1/users/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/users/me` | JWT | Get current user profile |
| GET | `/users/{slug}` | Public | Get user public profile by slug |
| PUT | `/users/me` | JWT | Update user profile fields |
| PUT | `/users/me/avatar` | JWT | Upload avatar (multipart, max 2MB) |
| DELETE | `/users/me/avatar` | JWT | Delete avatar |
| POST | `/users/me/change-password` | JWT | Change password (requires current password) |
| POST | `/users/me/confirm-identity` | JWT | Verify identity with current password |
| POST | `/users/me/change-email` | JWT | Request email change (sends OTP to current email) |
| POST | `/users/me/change-email/confirm` | JWT | Confirm email change with OTP |
| POST | `/users/me/delete-account` | JWT | Soft-delete account (requires password) |

## BillingPublicController — `/api/v1/billing/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/billing/products` | Public | List all active products |
| GET | `/billing/products/{slug}` | Public / API Key | Product detail with plans and domains (supports `?currency=`) |
| GET | `/billing/products/{slug}/plans` | Public / API Key | List plans for a product (supports `?currency=`) |
| GET | `/billing/exchange-rates` | Public | List exchange rates (supports `?base=`) |
| GET | `/billing/exchange-rates/{from}/{to}` | Public | Get specific exchange rate pair |
| GET | `/billing/currencies` | Public | List supported currency metadata |
| GET | `/billing/bank-settings` | Public | Get active bank settings (masked account numbers) |
| GET | `/billing/products/{slug}/access-matrix` | Public / API Key | Feature comparison matrix for active plans |

## BillingProtectedController — `/api/v1/billing/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/billing/auth/me` | JWT / API Key | User info + subscription + access map (uses `X-Service-Domain`) |
| GET | `/billing/subscriptions` | JWT | List user subscriptions (paginated) |
| GET | `/billing/subscriptions/transactions` | JWT | Get billing history from Stripe |
| POST | `/billing/subscriptions/sync` | JWT | Force-sync subscriptions from Stripe |
| GET | `/billing/subscriptions/{product_slug}` | JWT | Get subscription detail for a product |
| POST | `/billing/subscriptions/{product_slug}/cancel` | JWT | Cancel subscription at period end |
| POST | `/billing/subscriptions/{product_slug}/reactivate` | JWT | Reactivate canceled subscription |
| POST | `/billing/subscriptions/{product_slug}/checkout` | JWT | Create Stripe checkout session |
| POST | `/billing/checkout/confirm` | JWT | Confirm Stripe checkout and activate subscription |
| POST | `/billing/portal` | JWT | Create Stripe Customer Portal session |
| POST | `/billing/subscriptions/{product_slug}/preview-plan-change` | JWT | Preview plan change proration (read-only) |
| POST | `/billing/subscriptions/{product_slug}/confirm-plan-change` | JWT | Confirm plan change (safe preview-then-confirm flow) |
| GET | `/billing/export-data` | JWT | Export billing data (GDPR Article 20) |
| GET | `/billing/credits` | JWT | List my credit pools |
| GET | `/billing/credits/invoices` | JWT | List my credit invoices |
| GET | `/billing/credits/invoices/{invoice_number}/pdf` | JWT | Download my credit invoice PDF |
| POST | `/billing/credits/request` | JWT | Submit credit purchase request (bank transfer) |
| GET | `/billing/credits/{credit_id}` | JWT | Get credit pool detail with transaction history |

## BillingAdminController — `/api/v1/billing/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/billing/admin/subscriptions/{product_slug}/refund` | Staff | Issue refund for subscription |
| POST | `/billing/admin/transactions` | Staff | Get transaction history from Stripe |
| POST | `/billing/admin/sync-customer` | Staff | Sync Stripe customer data to local profile |

## BillingWebhookController — `/api/v1/billing/`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/billing/webhooks/stripe` | Signature | Handle Stripe webhook events (10 event types) |

## AdminProductController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/admin/products` | Staff | Create product |
| GET | `/admin/products` | Staff | List products (paginated, `?is_active=`, `?search=`) |
| GET | `/admin/products/{product_id}` | Staff | Product detail with plans and domains |
| PUT | `/admin/products/{product_id}` | Staff | Update product |
| PATCH | `/admin/products/{product_id}/toggle` | Staff | Activate/deactivate product |
| DELETE | `/admin/products/{product_id}` | Staff | Soft-delete product |
| POST | `/admin/products/{product_id}/domains` | Staff | Add service domain |
| PUT | `/admin/domains/{domain_id}` | Staff | Update service domain |
| DELETE | `/admin/domains/{domain_id}` | Staff | Remove service domain |

## AdminPlanController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/admin/products/{product_id}/plans` | Staff | Create plan |
| GET | `/admin/products/{product_id}/plans` | Staff | List plans for product (paginated) |
| GET | `/admin/plans/{plan_id}` | Staff | Plan detail with access entries |
| PUT | `/admin/plans/{plan_id}` | Staff | Update plan |
| PATCH | `/admin/plans/{plan_id}/toggle` | Staff | Toggle plan `is_active` |
| PATCH | `/admin/plans/{plan_id}/feature` | Staff | Toggle plan `is_featured` |
| POST | `/admin/plans/{plan_id}/duplicate` | Staff | Duplicate plan with access entries |
| DELETE | `/admin/plans/{plan_id}` | Staff | Delete plan |
| POST | `/admin/plans/{plan_id}/access-entries` | Staff | Create access entry |
| PUT | `/admin/access-entries/{entry_id}` | Staff | Update access entry |
| DELETE | `/admin/access-entries/{entry_id}` | Staff | Remove access entry |
| POST | `/admin/plans/{plan_id}/access-entries/bulk` | Staff | Bulk replace access entries |
| GET | `/admin/products/{product_id}/access-matrix` | Staff | Feature comparison matrix (all plans) |
| PUT | `/admin/products/{product_id}/access-matrix/row` | Staff | Atomic row save across plans |

## AdminRefundController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/refunds` | Staff | List refunds (filterable, paginated) |
| PATCH | `/admin/refunds/{refund_id}/approve` | Staff | Approve pending refund (two-person rule) |
| PATCH | `/admin/refunds/{refund_id}/reject` | Staff | Reject pending refund |

## AdminCreditController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/credits` | Staff | List credit pools (filterable, paginated) |
| GET | `/admin/credits/{credit_id}` | Staff | Credit pool detail with transactions |
| POST | `/admin/credits` | Staff | Create manual/offline credit purchase |
| POST | `/admin/credits/{credit_id}/refund` | Staff | Refund credit pool and void remaining periods |
| POST | `/admin/credits/{credit_id}/adjust` | Staff | Adjust credit pool periods |

## AdminCreditRequestController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/credit-requests` | Staff | List credit purchase requests |
| POST | `/admin/credit-requests/{request_id}/approve` | Staff | Approve credit request |
| POST | `/admin/credit-requests/{request_id}/reject` | Staff | Reject credit request |

## AdminCreditInvoiceController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/credit-invoices` | Staff | List credit invoices (filterable, paginated) |
| GET | `/admin/credit-invoices/{invoice_number}` | Staff | Credit invoice detail |
| GET | `/admin/credit-invoices/{invoice_number}/pdf` | Staff | Download credit invoice PDF |

## AdminBankSettingsController — `/api/v1/admin/bank-settings/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/bank-settings` | Staff | List all bank settings |
| POST | `/admin/bank-settings` | Staff | Create bank settings |
| PUT | `/admin/bank-settings/{settings_id}` | Staff | Update bank settings |
| PATCH | `/admin/bank-settings/{settings_id}/toggle` | Staff | Toggle active status |
| DELETE | `/admin/bank-settings/{settings_id}` | Staff | Delete bank settings |

## AdminSubscriptionController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/subscriptions` | Staff | List subscriptions (filterable, paginated) |
| GET | `/admin/subscriptions/{subscription_id}` | Staff | Subscription detail with access map |
| PATCH | `/admin/subscriptions/{subscription_id}/override` | Staff | Override plan/status/period |
| PATCH | `/admin/subscriptions/{subscription_id}/cancel` | Staff | Force cancel subscription |
| PATCH | `/admin/subscriptions/{subscription_id}/expire` | Staff | Force expire immediately |
| PATCH | `/admin/subscriptions/{subscription_id}/extend` | Staff | Extend billing period |
| GET | `/admin/subscriptions/{subscription_id}/plan-changes` | Staff | Plan change history (paginated) |
| GET | `/admin/subscriptions/{subscription_id}/invoices` | Staff | Invoice history (paginated) |
| POST | `/admin/subscriptions/{subscription_id}/refund` | Staff | Issue refund for subscription |
| GET | `/admin/subscriptions/{subscription_id}/refunds` | Staff | Refund history (paginated) |

## AdminUserController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/users` | Staff | List users (filterable, paginated) |
| GET | `/admin/users/{user_id}` | Staff | User detail with subscriptions |
| PATCH | `/admin/users/{user_id}/status` | Staff | Activate/deactivate user |
| PATCH | `/admin/users/{user_id}/role` | Staff | Change user role |
| GET | `/admin/users/{user_id}/audit` | Staff | User audit trail (paginated) |

## AdminMetricsController — `/api/v1/admin/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/metrics/overview` | Staff | MRR, churn, trial conversion, user count |
| GET | `/admin/metrics/revenue` | Staff | Revenue by product/plan/month |
| GET | `/admin/metrics/subscriptions` | Staff | Subscription funnel metrics |
| GET | `/admin/metrics/products` | Staff | Per-product metrics |
| GET | `/admin/audit-log` | Staff | Admin action log (paginated, filterable) |
| GET | `/admin/webhooks` | Staff | List webhook events (paginated) |
| POST | `/admin/webhooks/{event_id}/retry` | Staff | Retry failed webhook event |

## AdminApiKeyController — `/api/v1/admin/api-keys/`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/api-keys/` | Staff | List API keys (paginated, filterable) |
| GET | `/admin/api-keys/service-domains` | Staff | List service domains for key creation dropdown |
| POST | `/admin/api-keys/` | Staff | Create API key (raw key returned once only) |
| PATCH | `/admin/api-keys/{key_id}/revoke` | Staff | Revoke API key |
| POST | `/admin/api-keys/{key_id}/rotate` | Staff | Rotate API key (revoke old, create new) |
| GET | `/admin/api-keys/analytics` | Staff | Aggregated API key usage statistics |
| GET | `/admin/api-keys/{key_id}/analytics` | Staff | Single credential daily usage statistics |

## Summary

| Category | Count |
|---|---|
| Total Controller Classes | 17 |
| Total Endpoints | ~105 |
| Public Endpoints (no auth) | ~14 |
| JWT Authenticated Endpoints | ~20 |
| Dual Auth (JWT / API Key) | ~2 |
| Admin Endpoints (JWT + Staff) | ~62 |
| Webhook Endpoints (Signature) | 1 |
| Stripe Event Types Handled | 10 |

---

# Appendix C: Model Relationship Diagram Description

This appendix provides a textual description of the SattaBase data model relationships. The model graph centers on the `User` model and fans out through subscriptions, credit pools, and service credentials. Understanding these relationships is essential for writing efficient queries (choosing the right `select_related` vs. `prefetch_related`) and for maintaining referential integrity during mutations.

## Core Entity Hierarchy

```
User (users.User)
 ├── UserLoginHistory (FK → User, CASCADE)
 ├── Subscription (FK → User, CASCADE)
 │    ├── Plan (FK → Plan, SET_NULL) ──┐
 │    │    └── Product (FK → Product, CASCADE)
 │    └── Product (FK → Product, SET_NULL)
 │         └── ServiceDomain (FK → Product, CASCADE)
 │              └── ServiceCredential (FK → ServiceDomain, CASCADE)
 ├── CreditPool (FK → User, CASCADE)
 │    ├── CreditInvoice (FK → CreditPool, SET_NULL)
 │    └── CreditTransaction (FK → CreditPool, CASCADE)
 ├── CreditPurchaseRequest (FK → User, CASCADE)
 │    ├── Plan (FK → Plan, SET_NULL)
 │    └── Product (FK → Product, SET_NULL)
 └── [Stripe entities via stripe_customer_id]
      ├── Invoice (FK → Subscription, CASCADE; FK → User, CASCADE)
      │    └── InvoiceLineItem (FK → Invoice, CASCADE)
      ├── Refund (FK → Subscription, SET_NULL; FK → User, SET_NULL)
      └── RevenueRecognitionEntry (FK → Subscription, SET_NULL; FK → User, SET_NULL)
```

## Product and Plan Hierarchy

The Product-Plan-AccessEntry hierarchy is the foundation of the billing catalog:

```
Product
 ├── ServiceDomain (FK → Product, CASCADE)
 │    └── ServiceCredential (OneToOne → ServiceDomain, CASCADE)
 ├── Plan (FK → Product, CASCADE)
 │    └── AccessEntry (FK → Plan, CASCADE)
 └── Subscription (FK → Product, SET_NULL)
```

A Product can have multiple Plans (e.g., Free, Standard, Pro). Each Plan can have multiple AccessEntry records defining feature access (e.g., `max_transactions: 50`, `reports: true`). A Product can have multiple ServiceDomains (sister domains), but only one can be `is_primary=True` per product. Each ServiceDomain has exactly one ServiceCredential (API key) via a OneToOne relationship.

The `SET_NULL` on-delete behavior for `Subscription.plan` and `Subscription.product` is intentional: if a Plan or Product is deleted, the Subscription record is preserved for audit purposes but loses its reference to the deleted entity. This ensures that historical billing data remains queryable.

## Subscription Lifecycle Models

The Subscription model is the most interconnected entity in the system:

```
Subscription
 ├── User (FK, CASCADE)
 ├── Plan (FK, SET_NULL)
 ├── Product (FK, SET_NULL)
 ├── Invoice (reverse FK, CASCADE)
 │    └── InvoiceLineItem (reverse FK, CASCADE)
 ├── Refund (reverse FK, SET_NULL)
 │    ├── requested_by → User (FK, SET_NULL)
 │    └── approved_by → User (FK, SET_NULL, null)
 ├── RevenueRecognitionEntry (reverse FK, SET_NULL)
 └── PlanChangeHistory (reverse FK, CASCADE)
      ├── old_plan → Plan (FK, SET_NULL)
      └── new_plan → Plan (FK, SET_NULL)
```

The Refund model implements the two-person rule: `requested_by` records the admin who initiated the refund, and `approved_by` records a different admin who approved it. The system prevents an admin from approving their own refund request. Both fields use `SET_NULL` to preserve audit records if either admin account is deleted.

The RevenueRecognitionEntry model has a `source` field (`task`, `webhook`, or `manual`) tracking how the entry was created, enabling reconciliation between the daily Celery task entries and webhook-triggered entries.

## Credit System Models

The credit system operates in parallel with the Stripe subscription system:

```
User
 ├── CreditPool (FK, CASCADE)
 │    ├── Product (FK, SET_NULL)
 │    ├── Plan (FK, SET_NULL)
 │    ├── CreditInvoice (FK → CreditPool, SET_NULL)
 │    │    └── CreditTransaction (FK → CreditInvoice, SET_NULL)
 │    └── CreditTransaction (FK → CreditPool, CASCADE)
 │         └── CreditInvoice (FK, SET_NULL)
 ├── CreditPurchaseRequest (FK, CASCADE)
 │    ├── Product (FK, SET_NULL)
 │    ├── Plan (FK, SET_NULL)
 │    └── reviewed_by → User (FK, SET_NULL)
 └── BankSettings (standalone, no FK to User)
```

A CreditPool tracks the total amount and remaining periods. CreditTransaction records are immutable ledger entries with types: `purchase`, `consumption`, `adjustment`, `refund`, and `expiry`. Each transaction can optionally reference a CreditInvoice. The CreditPurchaseRequest model tracks the bank-transfer approval workflow: a user submits a request, an admin reviews it (`reviewed_by`), and on approval, a CreditPool and CreditInvoice are created.

## SDK Integration Models

The SDK-related models link Products to external domains and API credentials:

```
Product
 └── ServiceDomain (FK, CASCADE)
      ├── domain (unique)
      ├── is_primary (unique constraint: one per product)
      ├── webhook_url
      ├── webhook_secret
      └── ServiceCredential (OneToOne, CASCADE)
           ├── api_key_prefix (first 12 chars for identification)
           ├── api_key_hash (SHA-256 of full key for secure lookup)
           ├── permissions (JSON: {"auth": true, "billing_read": true})
           └── last_used_at (updated on every validated request)
```

The OneToOne relationship between ServiceCredential and ServiceDomain ensures that each domain has exactly one API key at a time. Key rotation creates a new credential and deactivates the old one.

## Cross-Cutting Models

Several models sit outside the primary hierarchies:

- **WebhookEventLog** (`billing`): Records every Stripe webhook event received. References Subscription via `stripe_subscription_id` (not a FK). Used for monitoring, debugging, and retry.
- **AdminAuditLog** (`billing`): Records admin actions with `admin_user` (FK → User), `action`, `resource_type`, `resource_id`, and `changes` (JSON). Independently queryable for compliance.
- **ExchangeRate** (`billing`): Standalone model with `base_currency`, `target_currency`, `rate`, and `last_updated`. No FK relationships.
- **BankSettings** (`billing`): Standalone model with `bank_name`, `account_holder_name`, `account_number` (encrypted), `routing_number`, and `is_active`. No FK relationships.
- **InvoiceLineItem** (`billing`): FK to Invoice (CASCADE). Stores individual line items from Stripe invoices with `description`, `quantity`, `unit_amount`, and `amount`.

## Key Query Patterns

Understanding these relationships helps write efficient queries:

- **Subscription with plan and product**: `Subscription.objects.select_related('plan', 'plan__product', 'user')` — use `select_related` for FK traversals.
- **User with all subscriptions and plans**: `User.objects.prefetch_related('subscription_set__plan')` — use `prefetch_related` for reverse FK.
- **Credit pool with transactions**: `CreditPool.objects.prefetch_related('transactions')` — the `CreditTransaction` model has a reverse FK from `CreditPool`.
- **Subscription with invoices and line items**: `Subscription.objects.prefetch_related('invoice_set__line_items')` — two levels of prefetch.
- **Lock subscription for update**: `Subscription.objects.select_for_update().select_related('plan').get(pk=pk)` — always pair `select_for_update` with `select_related` to avoid N+1 inside transactions.

---

# Appendix D: Stripe Webhook Events Reference

SattaBase handles 10 Stripe webhook event types through a structured processing pipeline. All webhook events are received at `POST /api/v1/billing/webhooks/stripe`, verified using the `STRIPE_WEBHOOK_SECRET`, and routed by the event router in `billing/stripe/webhooks/router.py`. Each handler runs synchronously inside a `transaction.atomic()` block with a 25-second cooperative timeout. All events are logged to the `WebhookEventLog` model for monitoring, debugging, and retry.

## Event Processing Pipeline

1. Stripe sends a POST with the event payload and a `Stripe-Signature` header
2. The webhook controller verifies the signature using `STRIPE_WEBHOOK_SECRET`
3. The event is recorded in `WebhookEventLog` (idempotent via `get_or_create` with `stripe_event_id`)
4. The router's `_EVENT_MAP` maps the event type to a handler function
5. The handler runs inside `transaction.atomic()` with a 25-second cooperative timeout (a `threading.Timer` that raises an exception if the handler takes too long)
6. On success, `WebhookEventLog.processed` is set to `True`
7. On failure, the error is logged and the event remains unprocessed for later retry

## Event Type Reference

### `checkout.session.completed`

| Property | Value |
|---|---|
| **Handler** | `handle_checkout_completed` |
| **File** | `billing/stripe/webhooks/handlers/checkout.py` |
| **Models Modified** | CreditPool (cancel), Subscription (create/update via sync) |
| **Purpose** | Completes a new subscription purchase initiated via Stripe Checkout. Extracts `user_id`, `product_slug`, and `plan_slug` from the checkout session metadata, cancels any active CreditPool for the same user+product combination (preventing double access), and delegates to `sync_subscription_from_stripe()` to create or update the local Subscription record from the live Stripe data. |

### `customer.subscription.created`

| Property | Value |
|---|---|
| **Handler** | `handle_subscription_created` |
| **File** | `billing/stripe/webhooks/handlers/subscription.py` |
| **Models Modified** | None (log-only) |
| **Purpose** | Logs the subscription creation event for audit purposes. No model mutations are performed — the actual subscription state synchronization is handled by the `checkout.session.completed` handler (for new subscriptions) and the `customer.subscription.updated` handler (for subsequent changes). |

### `customer.subscription.updated`

| Property | Value |
|---|---|
| **Handler** | `handle_subscription_updated` |
| **File** | `billing/stripe/webhooks/handlers/subscription.py` |
| **Models Modified** | Subscription, Plan |
| **Purpose** | The primary subscription state synchronization handler. Delegates entirely to `sync_subscription_from_stripe()`, which is the single source-of-truth function for subscription state. Performs a live Stripe API fetch and overwrites all local Subscription fields including: status mapping (active, trialing, past_due, canceled, paused, expired), plan change detection (via price ID or metadata `plan_slug`), period dates, trial dates, cancellation state (`cancel_at_period_end`, `canceled_at`), and currency. Handles reactivation by clearing `canceled_at` when the subscription is no longer canceling. |

### `customer.subscription.deleted`

| Property | Value |
|---|---|
| **Handler** | `handle_subscription_deleted` |
| **File** | `billing/stripe/webhooks/handlers/subscription.py` |
| **Models Modified** | Subscription |
| **Purpose** | Marks the subscription as expired when Stripe confirms deletion. Sets `Subscription.status = EXPIRED` and `current_period_end` to Stripe's `ended_at` timestamp (falling back to `now()` if `ended_at` is not present). This is a terminal state — the subscription cannot be reactivated after deletion. |

### `customer.subscription.trial_will_end`

| Property | Value |
|---|---|
| **Handler** | `handle_trial_will_end` |
| **File** | `billing/stripe/webhooks/handlers/subscription.py` |
| **Models Modified** | None (log-only) |
| **Purpose** | Logs a warning that a trial period is ending soon (Stripe sends this approximately 3 days before trial expiry). Currently no automated action is taken, but the log entry is available for future implementation of trial-ending notification emails. |

### `invoice.payment_succeeded`

| Property | Value |
|---|---|
| **Handler** | `handle_invoice_payment_succeeded` |
| **File** | `billing/stripe/webhooks/handlers/invoice.py` |
| **Models Modified** | Subscription, Invoice, InvoiceLineItem, RevenueRecognitionEntry |
| **Purpose** | Processes successful subscription payments. If the subscription was `PAST_DUE`, transitions it to `ACTIVE` (payment recovered). Resets dunning state (`dunning_step=0`). Upserts the Invoice record with InvoiceLineItem details. Fetches and stores the Stripe processing fee. Creates a RevenueRecognitionEntry for the payment date with `source=webhook`. This is the most complex handler in terms of models touched. |

### `invoice.payment_failed`

| Property | Value |
|---|---|
| **Handler** | `handle_invoice_payment_failed` |
| **File** | `billing/stripe/webhooks/handlers/invoice.py` |
| **Models Modified** | Subscription, Invoice, InvoiceLineItem |
| **Purpose** | Handles payment failures. Sets `Subscription.status = PAST_DUE` and initializes dunning state (`dunning_step=0`, `past_due_at=now()` on first transition). Performs a single `save()` call (IN-01 fix to avoid race conditions from split saves). Upserts the failed Invoice record for audit trail. The actual dunning progression (reminder emails, escalation) is handled by the `process_dunning` Celery task, not by this handler. |

### `invoice.created`

| Property | Value |
|---|---|
| **Handler** | `handle_invoice_created` |
| **File** | `billing/stripe/webhooks/handlers/invoice.py` |
| **Models Modified** | Invoice, InvoiceLineItem |
| **Purpose** | Creates or updates a local Invoice record whenever Stripe generates an invoice. This provides an early audit trail before payment succeeds or fails. The invoice may later be updated by the `payment_succeeded` or `payment_failed` handlers with additional details (payment status, Stripe fees). |

### `charge.refunded`

| Property | Value |
|---|---|
| **Handler** | `handle_charge_refunded` |
| **File** | `billing/stripe/webhooks/handlers/charge.py` |
| **Models Modified** | Refund |
| **Purpose** | Records Stripe-initiated refunds in the local database. Traces the charge back through `payment_intent` → `invoice` → `subscription` to resolve the correct local subscription (CH-01 fix; previously used `.first()` which could return arbitrary results). Creates a Refund record with status `COMPLETED` or `PENDING` based on the Stripe refund status. Deduplicates by `stripe_refund_id` to prevent duplicate records from duplicate webhook deliveries. |

### `customer.updated`

| Property | Value |
|---|---|
| **Handler** | `handle_customer_updated` |
| **File** | `billing/stripe/webhooks/handlers/charge.py` |
| **Models Modified** | User |
| **Purpose** | Synchronizes customer profile changes from Stripe back to the local User model. Finds the local User by looking up the `stripe_customer_id` on the Subscription model. Updates email, name (splitting Stripe's `name` field into `first_name` and `last_name`), and preferred currency from Stripe customer metadata. This ensures that changes made via the Stripe Customer Portal (e.g., email update) are reflected in SattaBase. |

## Supporting Infrastructure

### `sync_subscription_from_stripe()` — `billing/stripe/webhooks/sync.py`

The single source-of-truth function for subscription state synchronization. Called by both `handle_checkout_completed` and `handle_subscription_updated`. Performs a live Stripe API fetch (`stripe.Subscription.retrieve()`) and overwrites all local Subscription fields. Handles plan change detection by matching `stripe_price_id` against Plan records, with a fallback to the `plan_slug` in Stripe metadata. Uses a `_STATUS_MAP` to translate Stripe statuses to local `SubscriptionStatus` enum values. When a local subscription is not found (e.g., created directly in Stripe Dashboard), it auto-creates one via `BillingService.get_or_create_free_subscription()`.

### `WebhookEventLog` Model

Every webhook event is recorded with:
- `stripe_event_id` (unique, used for idempotent `get_or_create`)
- `event_type` (the Stripe event type string)
- `payload` (sanitized JSON — `Decimal` values converted to `float` for safe serialization)
- `processed` (boolean, set to `True` on successful handler execution)
- `error_message` (populated on handler failure)
- `created_at` and `updated_at` timestamps

The `reconcile_unprocessed()` function in the router retries all events where `processed=False`, enabling recovery from transient failures.

### Timeout Protection

Each handler invocation is wrapped in a 25-second cooperative timeout using `threading.Timer`. If the handler does not complete within 25 seconds, a `TimeoutError` is raised, the transaction is rolled back, and the event remains unprocessed for later retry. This prevents long-running handlers (e.g., slow Stripe API calls) from blocking the webhook processing pipeline.

---

# Appendix E: SattaBase SDK Integration Checklist

This checklist guides a sister domain team through integrating with the SattaBase platform. Each step must be completed in order — later steps depend on earlier ones. The entire integration can typically be completed in 2-3 days for a team familiar with REST APIs and OAuth-style flows.

## Step 1: Register a Service Domain

**Who**: SattaBase admin

**What**: Create a `ServiceDomain` record in the SattaBase admin panel (`/admin/api-keys/` or via the AdminApiKeyController endpoints) that maps your domain to a Product.

**Required information**:
- **Domain**: The exact FQDN of your application (e.g., `finance.sattabase.tld`). This must match the `X-Service-Domain` header your backend sends in every request.
- **Product**: The SattaBase Product your domain is associated with (e.g., "Satta Finance").
- **Is Primary**: Set to `True` if this is the main domain for the product (only one primary per product).
- **Webhook URL** (optional): An HTTPS endpoint on your server that will receive credential events (`credential.revoked`, `credential.rotated`).
- **Webhook Secret** (optional): A shared secret for HMAC-SHA256 signature verification of webhook payloads.

**Verification**: After registration, the domain is automatically added to the CORS whitelist (cached for 5 minutes). Requests from this domain will receive proper CORS headers without manual `CORS_ALLOWED_ORIGINS` configuration.

**Checklist**:
- [ ] ServiceDomain record created with correct FQDN
- [ ] Domain resolves to your application's IP
- [ ] Webhook URL is HTTPS and accessible from SattaBase servers (if providing)
- [ ] Webhook secret is a strong random string (if providing)

## Step 2: Obtain an API Key

**Who**: SattaBase admin

**What**: Create a `ServiceCredential` (API key) for your ServiceDomain via the admin panel.

**API Key Format**: `sb_live_` followed by 43 characters from `secrets.token_urlsafe(32)`, totaling 50 characters. Example: `sb_live_a1BcDeFgHiJkLmNoPqRsTuVwXyZ0123456789aBcD`

**Critical**: The full raw key is returned **only at creation time** and is never stored in the database. The database stores only:
- `api_key_prefix`: First 12 characters (e.g., `sb_live_a1Bc`) for log identification
- `api_key_hash`: SHA-256 hex digest of the full key for secure lookup during validation

If you lose the key, you must rotate it (revoke old, create new).

**Checklist**:
- [ ] API key created via `POST /admin/api-keys/`
- [ ] Full raw key stored securely (e.g., in a secrets manager, not in code or environment variables accessible to developers)
- [ ] Key prefix noted for log correlation

## Step 3: Implement Authentication Headers

**Who**: Sister domain backend team

**What**: Add the required HTTP headers to every request your backend makes to the SattaBase API.

**Required Headers**:
```
X-API-Key: sb_live_a1BcDeFgHiJkLmNoPqRsTuVwXyZ0123456789aBcD
X-Service-Domain: finance.sattabase.tld
```

**Validation Sequence** (what SattaBase checks on every request):
1. Key must start with `sb_live_` prefix — else `403 invalid_api_key_format`
2. `X-Service-Domain` header must be present — else `400 missing_service_domain`
3. SHA-256 hash of the key must match a stored `ServiceCredential` — else `403 api_key_forbidden`
4. The credential must be `is_active=True` — else `403 api_key_revoked`
5. The associated ServiceDomain must be `is_active=True` — else `403 service_domain_inactive`
6. The `X-Service-Domain` header must match the credential's ServiceDomain — else `403 domain_mismatch`

**On success**, the middleware attaches to the Django request object:
- `request.service_credential` — the `ServiceCredential` instance
- `request.service_domain_from_key` — the `ServiceDomain` instance

**CORS Headers** (automatically set by `service_domain_cors_middleware` for your domain):
```
Access-Control-Allow-Origin: https://finance.sattabase.tld
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD
Access-Control-Allow-Headers: Authorization, Content-Type, X-API-Key, X-Service-Domain, Accept, Origin, X-Requested-With
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 86400
```

**Key SDK Endpoints** (accessible with API Key auth):
- `GET /billing/products` — list products
- `GET /billing/products/{slug}` — product detail with plans
- `GET /billing/products/{slug}/access-matrix` — feature comparison matrix
- `GET /billing/auth/me` — user info + subscription + access map (requires `X-Service-Domain` header)

**Checklist**:
- [ ] HTTP client configured to send both headers on every SattaBase request
- [ ] Error handling implemented for 403 responses (key revoked, domain inactive, mismatch)
- [ ] API key stored in environment variable or secrets manager, not hardcoded
- [ ] Verified: `GET /billing/products` returns product list successfully

## Step 4: Set Up Webhook Receiver

**Who**: Sister domain backend team

**What**: Implement an HTTPS endpoint that receives credential event webhooks from SattaBase.

**Supported Event Types**:
| Event | Trigger | Action Required |
|---|---|---|
| `credential.revoked` | API key deactivated | Immediately stop using the revoked key; fall back to a cached key or alert an admin |
| `credential.rotated` | API key replaced (old key revoked, new key issued) | Update your stored key to the new one (included in payload) |

**Webhook Payload Format**:
```json
{
  "event": "credential.revoked",
  "timestamp": 1746892800,
  "data": {
    "credential_id": 42,
    "api_key_prefix": "sb_live_a1Bc",
    "name": "Finance Backend Production",
    "is_active": false,
    "service_domain": "finance.sattabase.tld"
  }
}
```

For `credential.rotated`, the payload includes additional fields: `old_prefix` and `new_prefix` (but not the full new key — you must retrieve the new key from your secrets manager where the admin stored it after rotation).

**Signature Verification** (HMAC-SHA256):
1. Receive the raw request body
2. Compute HMAC-SHA256 of the body using the `webhook_secret` shared in Step 1
3. Compare with the `X-Satta-Signature` header using constant-time comparison (`hmac.compare_digest`)
4. Reject if signatures do not match

**HTTP Headers Sent by SattaBase**:
```
Content-Type: application/json
X-Satta-Signature: <hex HMAC-SHA256>
X-Satta-Event: credential.revoked | credential.rotated
User-Agent: Sattabase-Webhook/1.0
```

**Retry Logic** (SattaBase side):
- 2xx response: success, no retry
- 5xx or connection error: retry up to 3 times with exponential backoff (1 min, 2 min, 4 min)
- 4xx response: no retry (your server rejected the payload)
- Per-attempt timeout: 10 seconds

**Replay Protection**: Reject payloads with `timestamp` older than 5 minutes (`MAX_TIMESTAMP_AGE = 300`) to prevent replay attacks.

**Checklist**:
- [ ] HTTPS endpoint implemented at the webhook_url registered in Step 1
- [ ] HMAC-SHA256 signature verification implemented using constant-time comparison
- [ ] `credential.revoked` handler: invalidate cached API key, log event, alert admin
- [ ] `credential.rotated` handler: update stored API key from secrets manager
- [ ] Replay protection: reject payloads with stale timestamps (>5 minutes old)
- [ ] Endpoint returns 2xx on successful processing
- [ ] Endpoint returns 5xx only on transient failures (triggers retry)

## Step 5: Implement SSO Authorization Code Flow

**Who**: Sister domain frontend and backend teams

**What**: Implement the SSO flow that allows an authenticated user on your domain to seamlessly access SattaBase without re-entering credentials.

**Flow Overview**:
```
Sister Domain Frontend          SattaBase API              SattaBase Frontend
        │                           │                           │
        │  POST /auth/authorize     │                           │
        │  (Bearer: user JWT) ────> │                           │
        │                           │                           │
        │  <─── {code: "abc123"} ── │                           │
        │                           │                           │
        │  Redirect browser ────────┼────────────────────────> │
        │  ?code=abc123             │                           │
        │                           │                           │
        │                           │  POST /auth/token/exchange│
        │                           │  <────────────────────── │
        │                           │                           │
        │                           │  ── {access_token} ─────> │
        │                           │  (refresh in httpOnly     │
        │                           │   cookie)                 │
```

**Step-by-step Implementation**:

1. **On your domain**: User is authenticated with your local session/JWT. When the user needs to access SattaBase (e.g., billing management), your backend calls `POST /api/v1/auth/authorize` with the user's Bearer token.
2. **SattaBase responds**: Returns a one-time authorization code (`code`) valid for 30 seconds. The code is stored in Redis with a 30-second TTL and is single-use (deleted on exchange).
3. **Redirect**: Your frontend redirects the user to the SattaBase frontend with `?code=abc123` in the URL.
4. **SattaBase callback page**: The SattaBase `AuthCallbackHandler.vue` component extracts the code and calls `POST /api/v1/auth/token/exchange` with `{"code": "abc123"}`.
5. **Token exchange**: SattaBase validates the code (Redis lookup + delete for one-time use), returns a JWT access token in the response body, and sets the refresh token as an httpOnly cookie.
6. **User is authenticated**: The user can now access all SattaBase features (dashboard, billing, etc.) without re-entering credentials.

**Security Controls**:
- Auth code expires in 30 seconds (short window to prevent code theft)
- Auth code is single-use (deleted from Redis immediately on exchange)
- Rate limited: 10 exchanges per 60 seconds per IP
- Constant-time response (10ms delay) to prevent timing attacks
- User must be `is_active=True` on both authorize and exchange steps

**Checklist**:
- [ ] Backend: `POST /auth/authorize` call implemented with Bearer token forwarding
- [ ] Frontend: Redirect logic to SattaBase with `?code=` parameter
- [ ] Error handling: authorization code expired, invalid code, rate limit exceeded
- [ ] Tested: seamless SSO from sister domain to SattaBase dashboard
- [ ] Tested: expired code returns appropriate error
- [ ] Tested: concurrent SSO attempts work correctly

## Step 6: Access User Subscription Data

**Who**: Sister domain backend team

**What**: Use the API key to check a user's subscription status and feature access.

**Primary Endpoint**: `GET /api/v1/billing/auth/me`

This endpoint accepts both JWT (frontend) and API key (SDK) authentication. When called with an API key, you must also send the `X-Service-Domain` header. The response includes:
- User profile data
- Active subscriptions with plan details
- An `access_map` object that maps product slugs to their feature access entries, pre-filtered for the requesting service domain

**Example Request**:
```http
GET /api/v1/billing/auth/me
X-API-Key: sb_live_a1BcDeFgHiJkLmNoPqRsTuVwXyZ0123456789aBcD
X-Service-Domain: finance.sattabase.tld
```

**Example Response (relevant fields)**:
```json
{
  "user": { "id": 1, "email": "user@example.com", "slug": "abc-123" },
  "subscriptions": [
    {
      "product_slug": "finance",
      "plan_name": "Standard",
      "status": "active",
      "current_period_end": "2026-07-01T00:00:00Z"
    }
  ],
  "access_map": {
    "finance": {
      "dashboard": true,
      "expense_tracking": true,
      "budget_categories": 0,
      "reports": true,
      "export_pdf": true,
      "api_access": true,
      "max_bank_accounts": 5
    }
  }
}
```

**Caching Recommendation**: Cache the `access_map` response in Redis with a TTL of 5-15 minutes. Subscription changes are infrequent, and stale data within this window is acceptable for feature gating. Invalidate the cache when you receive a webhook event (credential rotation is a good trigger to re-fetch).

**Checklist**:
- [ ] `/billing/auth/me` endpoint called successfully with API key headers
- [ ] Access map parsed and applied to feature gating logic
- [ ] Response cached with appropriate TTL
- [ ] Cache invalidation triggered on credential webhook events

## Step 7: Monitor and Maintain

**Who**: Both teams (ongoing)

**Ongoing Maintenance Tasks**:
- **API Key Rotation**: Rotate keys periodically (recommended: every 90 days) or immediately if compromised. Use `POST /admin/api-keys/{key_id}/rotate` to rotate.
- **Usage Monitoring**: Check `GET /admin/api-keys/analytics` for usage patterns and anomaly detection.
- **Webhook Health**: Monitor `GET /admin/webhooks` for failed deliveries. Retry with `POST /admin/webhooks/{event_id}/retry`.
- **CORS Verification**: If your domain changes, update the ServiceDomain record. The CORS cache refreshes within 5 minutes.
- **Rate Limit Awareness**: SDK rate limits default to 1000 requests/hour per credential. If you need higher limits, contact the SattaBase team to adjust `SB_RATE_LIMIT_SDK_ATTEMPTS`.

**Checklist**:
- [ ] API key rotation schedule established
- [ ] Usage monitoring dashboard configured
- [ ] Webhook delivery failure alerting implemented
- [ ] Contact established with SattaBase team for support