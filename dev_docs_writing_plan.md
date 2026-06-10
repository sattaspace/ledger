# SattaBase Developer Documentation — Writing Plan

> This plan defines every section and subsection of `dev_docs.md` with estimated word counts and source files to reference. No point should be skipped.

---

## Section 1: Project Overview & Architecture (~2500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 1.1 | Purpose & Scope | 400 | base/settings.py (project metadata), api/views.py (API description) |
| 1.2 | Technology Stack | 500 | requirements.txt, package.json, base/settings.py (Django, DB, Celery, Redis, Stripe, Astro, Vue, Tailwind) |
| 1.3 | Architecture Patterns | 600 | controllers.py, services.py, api_key_auth.py, middleware.py |
| 1.4 | Directory Structure | 600 | Full tree listing of backend/ and frontend/ |
| 1.5 | System Architecture Diagram Description | 400 | Overall request flow (client → Astro SSR → Django API → Stripe/Redis/DB) |

---

## Section 2: Backend Architecture Deep Dive (~5000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 2.1 | Django Project Structure | 300 | base/ (settings, urls, wsgi, asgi, celery) |
| 2.2 | All Models with Fields/Relationships | 1500 | billing/models.py, users/models.py, common/models.py |
| 2.3 | Controllers (Views) Catalog | 800 | billing/controllers.py, billing/admin_controller.py, billing/admin_subscription_controller.py, billing/admin_user_controller.py, billing/admin_metrics_controller.py, users/controllers.py, common/controllers.py |
| 2.4 | Services Layer | 500 | billing/services.py, billing/currency_service.py, billing/stripe_errors.py |
| 2.5 | Schemas (Pydantic) | 500 | billing/schemas.py, billing/admin_schemas.py, users/schemas.py, common/schemas.py |
| 2.6 | URLs & Routing | 200 | base/urls.py, api/views.py (auto_discover_controllers) |
| 2.7 | Middleware Stack | 500 | base/settings.py (MIDDLEWARE), common/middleware.py, common/cors_middleware.py |
| 2.8 | Signals | 300 | common/signals.py, users/signals.py |
| 2.9 | Celery Tasks | 400 | billing/tasks.py, base/celery.py |

---

## Section 3: Frontend Architecture Deep Dive (~4500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 3.1 | Astro + Vue Project Structure | 300 | astro.config.mjs, package.json, tsconfig.json |
| 3.2 | Page Routes & Routing | 400 | All files under src/pages/ |
| 3.3 | Layouts System | 500 | BaseLayout, AuthLayout, DashboardLayout, AdminLayout |
| 3.4 | Vue Components Catalog | 800 | All .vue files under components/vue/ and components/admin/ |
| 3.5 | Composables (State Management) | 800 | All files under src/composables/ |
| 3.6 | API Client Layer (lib/) | 700 | api.ts, auth.ts, billing.ts, credits.ts, admin.ts, toast.ts |
| 3.7 | Authentication & Session Management (Frontend) | 600 | middleware.ts, SessionGuard.vue, AdminGuard.vue, useAuth.ts, useAdminGuard.ts |
| 3.8 | Styling System | 300 | global.css (Tailwind v4, theme, dark mode) |
| 3.9 | Astro Server Middleware | 300 | src/middleware.ts |

---

## Section 4: Authentication & Authorization (~3000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 4.1 | JWT Authentication Flow | 500 | users/controllers.py, django-ninja-jwt config |
| 4.2 | Cookie-Based Token Refresh | 500 | users/controllers.py (cookie-based refresh) |
| 4.3 | API Key Authentication (SDK) | 400 | common/api_key_auth.py, common/middleware.py |
| 4.4 | Permission Classes | 300 | common/permissions.py |
| 4.5 | Rate Limiting | 300 | common/rate_limit.py |
| 4.6 | Account Security (Lockout, Deletion) | 500 | users/models.py (failed_login_attempts, locked_until, soft delete) |
| 4.7 | Frontend Auth Flow (End-to-End) | 500 | api.ts, useAuth.ts, SessionGuard.vue, middleware.ts |

---

## Section 5: Subscription & Billing System (~3500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 5.1 | Product → Plan → Subscription Hierarchy | 500 | billing/models.py |
| 5.2 | Stripe Integration (Checkout, Portal, Webhooks) | 600 | billing/stripe/*.py |
| 5.3 | Webhook Event Processing | 400 | billing/stripe/webhooks/*.py |
| 5.4 | Safe Plan Change Flow | 400 | billing/controllers.py (preview + confirm) |
| 5.5 | Dunning Workflow | 300 | billing/tasks.py |
| 5.6 | Revenue Recognition (ASC 606) | 400 | billing/models.py (RevenueRecognitionEntry), billing/tasks.py |
| 5.7 | Refund System (Two-Person Rule) | 400 | billing/models.py (Refund), admin_subscription_controller.py |
| 5.8 | Multi-Currency Support | 500 | billing/currency_service.py, billing/models.py (ExchangeRate) |

---

## Section 6: Credit System (~2000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 6.1 | Credit Pools & Lifecycle | 400 | billing/models.py (CreditPool, CreditInvoice, CreditTransaction) |
| 6.2 | Credit Purchase Requests (Bank Transfer) | 400 | billing/controllers.py, billing/admin_controller.py |
| 6.3 | Credit Consumption & Expiry | 300 | billing/tasks.py (consume_credit_periods), billing/services.py |
| 6.4 | Invoice PDF Generation | 400 | billing/pdf_utils.py, billing/controllers.py |
| 6.5 | Email Notifications (Approval/Rejection) | 300 | billing/tasks.py |
| 6.6 | Admin Credit Operations | 200 | billing/admin_controller.py (adjust, refund) |

---

## Section 7: Admin Panel Architecture (~2500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 7.1 | Admin Controllers Overview | 300 | admin_controller.py, admin_subscription_controller.py, admin_user_controller.py, admin_metrics_controller.py |
| 7.2 | Product & Plan Management | 400 | admin_controller.py |
| 7.3 | Subscription Administration | 400 | admin_subscription_controller.py |
| 7.4 | User Administration | 300 | admin_user_controller.py |
| 7.5 | Metrics & Reporting | 400 | admin_metrics_controller.py |
| 7.6 | Audit Logging | 300 | common/audit.py, common/signals.py |
| 7.7 | Webhook Monitoring & Retry | 200 | admin_metrics_controller.py (webhook endpoints) |
| 7.8 | Bank Settings Management | 200 | billing/admin_controller.py |

---

## Section 8: SDK & Sister Domain Integration (~2500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 8.1 | Service Domain Model | 300 | billing/models.py (ServiceDomain) |
| 8.2 | Service Credential (API Key) System | 400 | billing/models.py (ServiceCredential), common/utils.py |
| 8.3 | API Key Middleware & Validation | 400 | common/middleware.py, common/api_key_auth.py |
| 8.4 | Dynamic CORS for Service Domains | 300 | common/cors_middleware.py |
| 8.5 | SSO Authorization Code Flow | 400 | users/controllers.py (authorize, token exchange) |
| 8.6 | Webhook Dispatch for Credential Events | 300 | common/webhooks.py |
| 8.7 | SDK Integration Guide (Sister Domain) | 400 | All SDK-related files |
| 8.8 | Analytics & Usage Tracking | 200 | common/analytics.py |

---

## Section 9: API Reference (~3000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 9.1 | API Structure & Versioning | 200 | api/views.py, base/urls.py |
| 9.2 | Public Endpoints | 300 | BillingPublicController |
| 9.3 | Protected Endpoints (JWT) | 500 | BillingProtectedController, AuthController |
| 9.4 | Admin Endpoints | 500 | All admin controllers |
| 9.5 | SDK Endpoints (API Key) | 300 | BillingPublicController (with IsServiceAuthenticated) |
| 9.6 | Webhook Endpoint (Stripe) | 200 | BillingWebhookController |
| 9.7 | Error Response Format | 300 | api/views.py (exception handlers), common/exceptions.py |
| 9.8 | Pagination Convention | 200 | common/utils.py |
| 9.9 | Rate Limit Headers & Behavior | 200 | common/rate_limit.py |

---

## Section 10: Celery Tasks & Background Jobs (~1500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 10.1 | Celery Configuration | 300 | base/celery.py, base/settings.py |
| 10.2 | Scheduled Tasks (Beat) | 400 | billing/tasks.py |
| 10.3 | On-Demand Tasks | 300 | billing/tasks.py (emails), common/webhooks.py (delivery) |
| 10.4 | Task Monitoring & Error Handling | 300 | settings.py (django-celery-results), task implementations |
| 10.5 | Redis as Broker & Cache | 200 | settings.py (CACHES, CELERY_BROKER_URL) |

---

## Section 11: Database & Data Layer (~1500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 11.1 | Database Configuration | 200 | base/settings.py (PostgreSQL vs SQLite) |
| 11.2 | Abstract Base Models | 300 | common/models.py (TimeStampedModel, SoftDeleteModel, ActivatorModel) |
| 11.3 | Encrypted Fields | 200 | billing/fields.py |
| 11.4 | Migrations Strategy | 200 | billing/migrations/ |
| 11.5 | Seed Data Commands | 200 | common/management/commands/ |
| 11.6 | Query Optimization Patterns | 400 | select_for_update, select_related, prefetch_related in services/controllers |

---

## Section 12: Security Architecture (~2000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 12.1 | Authentication Security | 300 | users/controllers.py, users/models.py |
| 12.2 | CSRF Protection | 200 | base/settings.py, api/views.py (csrf=False on API) |
| 12.3 | CORS Security | 300 | common/cors_middleware.py, settings.py |
| 12.4 | Rate Limiting & Brute Force Protection | 300 | common/rate_limit.py, users/controllers.py |
| 12.5 | Data Encryption | 200 | billing/fields.py, settings.py (CRYPTOGRAPHY_KEY) |
| 12.6 | Audit Trail | 300 | billing/models.py (AdminAuditLog), common/audit.py |
| 12.7 | Input Validation & Sanitization | 300 | schemas.py files (Pydantic validation) |

---

## Section 13: Payment & Stripe Integration (~2000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 13.1 | Stripe Configuration | 200 | base/settings.py |
| 13.2 | Checkout Session Flow | 400 | billing/stripe/checkout.py |
| 13.3 | Customer Portal | 200 | billing/stripe/portal.py |
| 13.4 | Webhook Processing Pipeline | 500 | billing/stripe/webhooks/ |
| 13.5 | Refund Processing | 300 | billing/stripe/ (refund flows) |
| 13.6 | Stripe Error Handling | 400 | billing/stripe_errors.py |

---

## Section 14: Email System (~800 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 14.1 | Email Configuration | 200 | base/settings.py |
| 14.2 | Email Templates | 300 | billing/tasks.py (approval/rejection HTML emails) |
| 14.3 | Email Triggers | 300 | tasks.py, controllers.py |

---

## Section 15: Deployment & DevOps (~1500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 15.1 | Docker Configuration | 300 | backend/Dockerfile, frontend/Dockerfile |
| 15.2 | Environment Variables | 400 | backend/.env, base/settings.py |
| 15.3 | ASGI/WSGI Configuration | 200 | base/asgi.py, base/wsgi.py |
| 15.4 | Static & Media Files | 200 | base/settings.py, base/urls.py |
| 15.5 | Production Checklist | 400 | base/settings.py (DEBUG, ALLOWED_HOSTS, SECURE_* settings) |

---

## Section 16: Testing Strategy (~1000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 16.1 | Backend Test Structure | 300 | billing/tests/ |
| 16.2 | Key Test Scenarios | 400 | test_checkout.py, test_safe_plan_change.py, test_revenue_recognition.py, test_refund.py, test_stripe_errors.py, test_currency_service.py |
| 16.3 | Frontend Testing | 300 | (future) |

---

## Section 17: Error Handling Philosophy (~800 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 17.1 | Custom Exception Hierarchy | 300 | common/exceptions.py |
| 17.2 | API Error Response Format | 200 | api/views.py (exception handlers) |
| 17.3 | Frontend Error Handling | 300 | api.ts (createApiErrorFromResponse), useFormErrors.ts |

---

## Section 18: Data Flow Diagrams (~1000 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 18.1 | User Registration & Login Flow | 200 | users/controllers.py, auth.ts, LoginForm.vue |
| 18.2 | Subscription Purchase Flow | 300 | billing/controllers.py, billing/stripe/checkout.py, Stripe webhooks |
| 18.3 | Credit Purchase (Bank Transfer) Flow | 300 | billing/controllers.py, billing/admin_controller.py, billing/tasks.py |
| 18.4 | SDK SSO Authorization Flow | 200 | users/controllers.py, common/middleware.py |

---

## Section 19: Known Issues & Technical Debt (~500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 19.1 | Known Bugs | 200 | Session context (login redirect on admin/users subscription view) |
| 19.2 | Technical Debt | 300 | Enhancement notes, audit findings |

---

## Section 20: Development Workflow (~800 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 20.1 | Local Development Setup | 300 | requirements.txt, package.json, .env |
| 20.2 | Database Migrations | 200 | manage.py, migrations/ |
| 20.3 | Seed Data | 300 | common/management/commands/ |

---

## Section 21: Contributing Guidelines (~500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 21.1 | Code Style | 200 | Project conventions |
| 21.2 | Git Workflow | 150 | Branch naming, commit format |
| 21.3 | PR Review Process | 150 | Checklist |

---

## Section 22: Glossary (~500 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 22.1 | Domain Terms | 300 | All files |
| 22.2 | Acronyms | 200 | All files |

---

## Section 23: Changelog & Version History (~300 words)

| # | Subsection | Est. Words | Source Files |
|---|---|---|---|
| 23.1 | Version History | 300 | Enhancement docs, audit trail |

---

## Appendices

| # | Appendix | Est. Words | Source Files |
|---|---|---|---|
| A | Environment Variables Reference | 600 | base/settings.py, backend/.env |
| B | API Endpoint Quick Reference Table | 500 | All controllers |
| C | Model Relationship Diagram Description | 400 | billing/models.py, users/models.py |
| D | Stripe Webhook Events Reference | 300 | billing/stripe/webhooks/handlers/ |
| E | SattaBase SDK Integration Checklist | 400 | SDK-related files |

---

**Total estimated words: ~43,300**

---

## Progress Tracking

| Section | Status | Completed Date |
|---|---|---|
| 1. Project Overview & Architecture | ✅ Written | 2026-06-05 |
| 2. Backend Architecture Deep Dive | ✅ Written | 2026-06-05 |
| 3. Frontend Architecture Deep Dive | ✅ Written | 2026-06-05 |
| 4. Authentication & Authorization | ✅ Written | 2026-06-05 |
| 5. Subscription & Billing System | ✅ Written | 2026-06-05 |
| 6. Credit System | ✅ Written | 2026-06-05 |
| 7. Admin Panel Architecture | ✅ Written | 2026-06-05 |
| 8. SDK & Sister Domain Integration | ✅ Written | 2026-06-05 |
| 9. API Reference | ✅ Written | 2026-06-05 |
| 10. Celery Tasks & Background Jobs | ✅ Written | 2026-06-05 |
| 11. Database & Data Layer | ✅ Written | 2026-06-05 |
| 12. Security Architecture | ✅ Written | 2026-06-05 |
| 13. Payment & Stripe Integration | ✅ Written | 2026-06-05 |
| 14. Email System | ✅ Written | 2026-06-05 |
| 15. Deployment & DevOps | ✅ Written | 2026-06-05 |
| 16. Testing Strategy | ✅ Written | 2026-06-05 |
| 17. Error Handling Philosophy | ✅ Written | 2026-06-05 |
| 18. Data Flow Diagrams | ✅ Written | 2026-06-05 |
| 19. Known Issues & Technical Debt | ✅ Written | 2026-06-05 |
| 20. Development Workflow | ✅ Written | 2026-06-05 |
| 21. Contributing Guidelines | ✅ Written | 2026-06-05 |
| 22. Glossary | ✅ Written | 2026-06-05 |
| 23. Changelog & Version History | ✅ Written | 2026-06-05 |
| Appendix A-E | ✅ Written | 2026-06-05 |
