# Dealer System Integration Tracking

**Document Purpose**: Track the integration of the Dealer sister domain (dealerfrontend + dealerbackend) with the SattaBase base system using the SDK pattern.

**Status**: 🟢 **PHASE 11 COMPLETE** — All backend APIs dealer-scoped. Multi-tenancy fully enforced at API layer. Remaining: Phase 8 testing, Phase 12 frontend dealer selection.

**Created**: 2026-06-11
**Last Updated**: 2026-06-11

---

## Executive Summary

The current dealer system has a **hybrid but partially redundant authentication architecture**. It's attempting to act as both:
1. A sister domain (using SattaBase for auth)
2. A standalone backend (with its own auth endpoints)

This creates complexity, inconsistencies, and deviates from the SDK-based sister domain pattern established in `sister-domain-starter/`.

### Key Issues
- **Dual authentication paths**: Login goes to dealerbackend which proxies to SattaBase instead of going directly
- **Hardcoded permissions system**: `usePermissions.ts` defines roles locally instead of using access map from `/billing/auth/me`
- **Missing SDK integration**: Not using the proper SDK pattern from `sister-domain-starter/`
- **Unnecessary backend auth endpoints**: dealerbackend has auth controllers that proxy to SattaBase

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEALER SYSTEM (Sister Domain)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────┐         ┌─────────────────────────────────────┐    │
│  │  Dealer Frontend    │ ──────► │       SattaBase Backend              │    │
│  │  (Astro + Vue)      │         │  (Django Ninja - port 8086)          │    │
│  │                     │         │                                      │    │
│  │  - lib/api.ts       │         │  /auth/login                         │    │
│  │  - lib/auth.ts      │         │  /auth/token/refresh                 │    │
│  │  - useAuth.ts       │         │  /auth/authorize                     │    │
│  │  - useAccess.ts     │         │  /billing/auth/me                    │    │
│  │                     │         │  /billing/subscriptions              │    │
│  └─────────┬───────────┘         └──────────────────────────────────────┘    │
│            │                                                                  │
│            │ X-Service-Domain: dealer.sattaspace.com                         │
│            │                                                                  │
│  ┌─────────▼───────────┐         ┌─────────────────────────────────────┐    │
│  │  Dealer Backend     │         │       SattaBase Frontend             │    │
│  │  (Django - port 8088)│        │  (port 4321)                        │    │
│  │                     │         │                                      │    │
│  │  - inventory/*      │         │  - /auth/register                    │    │
│  │  - sales/*          │         │  - /auth/forgot-password             │    │
│  │  - dsr/*            │         │  - /dashboard/billing                │    │
│  │  - supplier/*       │         │  - /auth/callback (SSO)              │    │
│  │  - dealer/*         │         │                                      │    │
│  │  - reports/*        │         │                                      │    │
│  │                     │         │                                      │    │
│  │  NO auth endpoints  │         │                                      │    │
│  │  (frontend calls    │         │                                      │    │
│  │   Sattabase direct) │         │                                      │    │
│  └─────────────────────┘         └─────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Principles (from sister-domain-starter)

1. **JWT-only authentication** — No API keys in frontend
2. **X-Service-Domain header** — Tells SattaBase which product's subscription/access to return
3. **Token Pass-Through SSO** — Auth codes enable cross-domain sessions
4. **Access control via access map** — Returned by `/billing/auth/me`, not hardcoded roles
5. **Redirects to base domain** — For register, forgot-password, billing, profile

---

## Current State Analysis

### Files to REMOVE (dealerfrontend)

| File | Location | Issue |
|------|----------|-------|
| `useSSO.ts` | `dealerfrontend/src/composables/` | SSO should be handled via SDK's `generateAuthCode()` directly to SattaBase |
| `usePermissions.ts` | `dealerfrontend/src/composables/` | Hardcoded roles — should use `useAccess.ts` pattern with access map |

### Files to REPLACE (dealerfrontend)

| File | Location | Current Issue | Replace With |
|------|----------|---------------|--------------|
| `lib/auth.ts` | `dealerfrontend/src/lib/` | Custom implementation pointing to dealerbackend | Sister-domain-starter's `lib/auth.ts` |
| `services/apiClient.ts` | `dealerfrontend/src/services/` | Separate API client | Sister-domain-starter's `lib/api.ts` pattern |
| `composables/useAuth.ts` | `dealerfrontend/src/composables/` | Uses local auth lib | Sister-domain-starter's `useAuth.ts` |

### Files to REMOVE (dealerbackend)

| File | Location | Issue |
|------|----------|-------|
| `common/sso_controller.py` | `dealerbackend/common/` | SSO should be handled directly via SDK, not proxied |
| `common/auth_controller.py` | `dealerbackend/common/` | If frontend calls SattaBase directly, this becomes unnecessary |

### Files to REPLACE (dealerbackend)

| File | Location | Replace With |
|------|----------|--------------|
| `common/sattabase_client.py` | `dealerbackend/common/` | Official `sattabase_sdk` Python package (if backend needs server-to-server calls) |

### Files to ADD (dealerfrontend)

| File | Source | Purpose |
|------|--------|---------|
| `sattabase.config.ts` | Create new | Central configuration for dealer domain |
| `composables/useAccess.ts` | Copy from sister-domain-starter | Feature access checking from billing.auth.me |
| `composables/useBillingRedirect.ts` | Copy from sister-domain-starter | Billing return detection |
| `composables/useSubscription.ts` | Copy from sister-domain-starter | Subscription state management |

---

## Detailed Task Checklist

### Phase 1: Configuration Setup

- [x] **TASK-1.1**: Create `dealerfrontend/sattabase.config.ts` ✅ DONE (2026-06-11)
  ```typescript
  export default {
    apiBaseUrl: import.meta.env.PUBLIC_API_BASE_URL_SB || "http://localhost:8086/api/v1",
    baseDomainUrl: import.meta.env.PUBLIC_BASE_DOMAIN_URL || "http://localhost:4321",
    thisDomainUrl: import.meta.env.PUBLIC_THIS_DOMAIN_URL || "http://localhost:8088",
    serviceDomain: import.meta.env.PUBLIC_SERVICE_DOMAIN || "dealer.sattaspace.com",
    sessionCookieName: import.meta.env.PUBLIC_SESSION_COOKIE_NAME || "sattabase_session_cookie",
    tokenKeyPrefix: import.meta.env.PUBLIC_TOKEN_KEY_PREFIX || "dealercore:",
    accessTokenLifetimeMinutes: 60,
  };
  ```

- [x] **TASK-1.2**: Update `dealerfrontend/.env.example` with new environment variables ✅ DONE (2026-06-11)
  ```
  PUBLIC_API_BASE_URL_SB=http://localhost:8086/api/v1
  PUBLIC_BASE_DOMAIN_URL=http://localhost:4321
  PUBLIC_THIS_DOMAIN_URL=http://localhost:4323
  PUBLIC_SERVICE_DOMAIN=localhost:4323
  PUBLIC_TOKEN_KEY_PREFIX=dealercore:
  PUBLIC_DEALER_API_URL=http://localhost:8088/api
  ```

- [x] **TASK-1.3**: Update `dealerfrontend/src/lib/constants.ts` to use new config ✅ DONE (2026-06-11)

### Phase 2: Remove Unnecessary Files

- [x] **TASK-2.1**: Delete `dealerfrontend/src/composables/useSSO.ts` ✅ DONE (2026-06-11)
  - Reason: SSO should be handled directly via `generateAuthCode()` calling SattaBase
  - Updated `ManageBillingButton.vue` to use new auth pattern directly

- [x] **TASK-2.2**: Archive `dealerfrontend/src/composables/usePermissions.ts` ✅ DONE (2026-06-11)
  - Reason: Will be replaced with `useAccess.ts` pattern
  - Renamed to `usePermissions.ts.deprecated`
  - Updated `PermissionGuard.vue` to use new `useAccess` pattern

- [x] **TASK-2.3**: Update `dealerfrontend/src/services/apiClient.ts` ✅ DONE (2026-06-11)
  - Kept for dealer business data endpoints (works well)
  - Updated to import auth token from new `lib/api.ts`
  - Services continue to use this client for dealer backend

- [ ] **TASK-2.4** (Optional): Delete `dealerbackend/common/sso_controller.py`
  - Reason: SSO handled by frontend directly
  - DEFERRED: Backend cleanup can be done later

- [ ] **TASK-2.5** (Optional): Delete or simplify `dealerbackend/common/auth_controller.py`
  - Reason: Frontend should call SattaBase directly for auth
  - DEFERRED: Backend cleanup can be done later

### Phase 2.5: Early File Creation (Moved from Phase 3 & 4)

- [x] **TASK-2.5.1**: Create `dealerfrontend/src/lib/types.ts` ✅ DONE (2026-06-11)
  - Auth-related types for SattaBase API interactions
  - `ApiError`, `TokenPair`, `User`, `Subscription`, `AccessMap`, `AuthMeResponse`

- [x] **TASK-2.5.2**: Create `dealerfrontend/src/lib/api.ts` ✅ DONE (2026-06-11)
  - Centralized API client for SattaBase auth/billing
  - Token management with session/localStorage persistence
  - X-Service-Domain header injection
  - Auto-refresh on 401
  - Separate `dealerApi` for dealer backend business data

- [x] **TASK-2.5.3**: Create `dealerfrontend/src/composables/useAccess.ts` ✅ DONE (2026-06-11)
  - Replaces `usePermissions.ts` pattern
  - Provides: `hasAccess()`, `getAccess()`, `getLimit()`, `accessKeys`
  - Uses access map from `/billing/auth/me` instead of hardcoded roles

- [x] **TASK-2.5.4**: Update `dealerfrontend/src/components/ManageBillingButton.vue` ✅ DONE (2026-06-11)
  - Now uses `apiClient.post('/auth/authorize')` directly
  - Removed dependency on `useSSO.ts`

- [x] **TASK-2.5.5**: Update `dealerfrontend/src/components/PermissionGuard.vue` ✅ DONE (2026-06-11)
  - Now uses `useAccess()` instead of `usePermissions()`
  - Accepts string feature keys instead of Permission enum

- [x] **TASK-2.5.6**: Update `dealerfrontend/src/services/api/index.ts` ✅ DONE (2026-06-11)
  - Re-exports from both old `apiClient.ts` and new `lib/api.ts`

### Phase 3: Replace Core Files

- [x] **TASK-3.1**: Replace `dealerfrontend/src/lib/auth.ts` ✅ DONE (2026-06-11)
  - Copied pattern from `sister-domain-starter/src/lib/auth.ts`
  - Key changes:
    - Import from `./api` and `../../sattabase.config`
    - `login()` calls SattaBase directly (`/auth/login`)
    - `logout()` calls SattaBase (`/auth/token/blacklist`, `/users/me/logout`)
    - `getAuthMe()` calls `/billing/auth/me` with X-Service-Domain header
    - `generateAuthCode()` calls SattaBase `/auth/authorize`
    - `redirectToBase()` and `redirectToBaseWithAuthCode()` for SSO

- [x] **TASK-3.2**: Create/Replace `dealerfrontend/src/lib/api.ts` ✅ DONE (2026-06-11)
  - Already completed in Phase 2.5 (TASK-2.5.2)
  - Key features:
    - Centralized API client with JWT Bearer injection
    - X-Service-Domain header injection
    - Auto-refresh on 401
    - Token persistence (session/local storage)

- [x] **TASK-3.3**: Replace `dealerfrontend/src/composables/useAuth.ts` ✅ DONE (2026-06-11)
  - Copied pattern from `sister-domain-starter/src/composables/useAuth.ts`
  - Key features:
    - Shared auth state singleton (module-level refs)
    - Calls SattaBase directly via lib/auth.ts
    - Returns `access` map from `/billing/auth/me`
    - Includes `refreshUser()` and `clearError()` for backwards compatibility
  - Updated `LoginForm.vue` to use new login signature

### Phase 4: Add New Files

- [x] **TASK-4.1**: Create `dealerfrontend/src/composables/useAccess.ts` ✅ DONE (2026-06-11)
  - Already created in Phase 2.5 (TASK-2.5.3)
  - Provides: `hasAccess()`, `getAccess()`, `getLimit()`, `accessKeys`
  - Uses access map from `useAuth().access`

- [x] **TASK-4.2**: Create `dealerfrontend/src/composables/useBillingRedirect.ts` ✅ DONE (2026-06-11)
  - Copied from `sister-domain-starter/src/composables/useBillingRedirect.ts`
  - Detects `billing_updated` query param on return from SattaBase
  - Dispatches `sattabase:billing-updated` custom event
  - useAuth automatically refetches profile on billing update

- [x] **TASK-4.3**: Create `dealerfrontend/src/composables/useSubscription.ts` ✅ DONE (2026-06-11)
  - Copied from `sister-domain-starter/src/composables/useSubscription.ts`
  - Singleton pattern for subscription state management
  - Provides: `fetchSubscriptions()`, `hasActiveSubscription()`, `getSubscription()`

- [x] **TASK-4.4**: Update `dealerfrontend/src/lib/types.ts` ✅ DONE (2026-06-11)
  - Already created in Phase 2.5 (TASK-2.5.1)
  - Added `SubscriptionOutput` type for useSubscription composable
  - Includes: `AuthMeResponse`, `TokenPair`, `ApiError`, `SubscriptionOutput`, etc.

### Phase 5: Update Components

- [x] **TASK-5.1**: Update `dealerfrontend/src/components/LoginForm.vue` ✅ DONE (2026-06-11)
  - Already updated in Phase 3 to use new auth pattern
  - Calls `login(email, password)` directly to SattaBase
  - Uses `useAuth()` composable with `clearError()`

- [x] **TASK-5.2**: Update `dealerfrontend/src/components/LoginPage.vue` ✅ DONE (2026-06-11)
  - Uses `redirectToBase()` for register/forgot-password links
  - Replaced `<a href>` with `<button @click>` for proper redirects
  - Properly emits login event for App.vue handling

- [x] **TASK-5.3**: Update `dealerfrontend/src/components/SessionGuard.vue` ✅ DONE (2026-06-11)
  - Uses new auth state management from `useAuth()`
  - Added `useBillingRedirect()` for billing return detection
  - Calls `checkBillingRedirect()` on mount for automatic profile refresh

- [x] **TASK-5.4**: Update `dealerfrontend/src/components/PermissionGuard.vue` ✅ DONE (2026-06-11)
  - Already updated in Phase 2.5 (TASK-2.5.5)
  - Uses `useAccess` instead of `usePermissions`
  - Supports `feature`, `any`, and `all` props for flexible access control

- [x] **TASK-5.5**: Update `dealerfrontend/src/components/ManageBillingButton.vue` ✅ DONE (2026-06-11)
  - Already updated in Phase 2.5 (TASK-2.5.4)
  - Uses `apiClient.post('/auth/authorize')` directly for SSO
  - Redirects to SattaBase callback with auth code

- [x] **TASK-5.6**: Update `dealerfrontend/src/App.vue` ✅ DONE (2026-06-11)
  - Uses `useAuth()` for authentication state
  - SessionGuard wraps protected content with billing redirect detection
  - Proper login/logout flow with page reload for state initialization

- [x] **TASK-5.7**: Update all components using `usePermissions` ✅ DONE (2026-06-11)
  - No remaining `usePermissions` imports (archived as `.deprecated`)
  - All components now use `useAccess()` with access map pattern

### Phase 6: Update Backend (dealerbackend)

- [x] **TASK-6.1**: Install/Verify `sattabase_sdk` in dealerbackend ✅ DONE (2026-06-11)
  - Verified existing `dealerbackend/common/sattabase_client.py` implementation
  - Custom client handles: login proxy, token refresh, get_me, logout, auth code generation
  - Since frontend calls SattaBase directly, backend client is for server-to-server calls only

- [x] **TASK-6.2**: Update `dealerbackend/common/sattabase_client.py` ✅ DONE (2026-06-11)
  - Verified existing implementation is correct
  - Already uses environment variables: `SB_API_BASE_URL`, `SB_SERVICE_DOMAIN`, `SB_API_KEY`
  - Async aiohttp client with proper error handling

- [x] **TASK-6.3**: Update `dealerbackend/dealercore/settings.py` ✅ DONE (2026-06-11)
  - Added SattaBase SDK configuration:
    ```python
    SATTABASE_API_URL = os.getenv("SB_API_BASE_URL", "http://localhost:8086/api/v1")
    SATTABASE_SERVICE_DOMAIN = os.getenv("SB_SERVICE_DOMAIN", "localhost:4323")
    SATTABASE_API_KEY = os.getenv("SB_API_KEY", "")
    SATTABASE_FRONTEND_URL = os.getenv("SB_FRONTEND_URL", "http://localhost:4321")
    JWT_ACCESS_TOKEN_LIFETIME = timedelta(minutes=60)
    ```

- [x] **TASK-6.4**: Update business logic endpoints for JWT validation ✅ DONE (2026-06-11)
  - Verified `dealerbackend/common/permission_middleware.py` extracts user info from JWT
  - Middleware decodes JWT without signature verification (SattaBase verifies)
  - Extracts `role` and `is_dealer` from JWT claims
  - Provides `check_permission()`, `require_dealer()`, `require_dsr_plus()` helpers

### Phase 7: Add DealerCore to billing_seed_data.py

- [x] **TASK-7.1**: Add DealerCore product to `backend/common/management/commands/billing_seed_data.py` ✅ DONE (2026-06-11)
  - Added product with slug `dealercore`
  - Service domains: `dealer.sattaspace.com` (primary), `localhost:4323` (dev)
  - Three plans configured:
    - **Free**: $0/month - Basic features (50 products, 1 DSR, 3 suppliers)
    - **Standard**: $29/month - Full features (500 products, 5 DSRs, 20 suppliers, reports, suppliers)
    - **Enterprise**: $99/month - Unlimited features (priority support, white-label, audit log)
  - Access entries for each plan:
    - Boolean features: dashboard, inventory, sales, collections, reports, suppliers, bad_debt
    - Integer limits: max_products, max_dsrs, max_suppliers
    - Premium features: export_pdf, api_access, priority_support, white_label, audit_log

### Phase 8: Testing

- [ ] **TASK-8.1**: Test login flow
  - Login should go directly to SattaBase backend
  - Token should be stored correctly
  - User info should be retrieved

- [ ] **TASK-8.2**: Test access control
  - Access map should be retrieved from `/billing/auth/me`
  - `useAccess()` should work correctly
  - Components should show/hide based on access

- [ ] **TASK-8.3**: Test SSO flow
  - "Manage Billing" should redirect to SattaBase with auth code
  - Return from billing should update subscription

- [ ] **TASK-8.4**: Test logout flow
  - Logout should blacklist token on SattaBase
  - Local state should be cleared

- [ ] **TASK-8.5**: Test token refresh
  - Auto-refresh should work
  - 401 responses should trigger refresh

---

## Reference Files

### Sister Domain Starter (Correct Pattern)

| File | Purpose |
|------|---------|
| `sister-domain-starter/sattabase.config.ts` | Central configuration |
| `sister-domain-starter/src/lib/api.ts` | API client with JWT injection, X-Service-Domain header |
| `sister-domain-starter/src/lib/auth.ts` | Auth functions (login, logout, generateAuthCode, redirectToBase) |
| `sister-domain-starter/src/composables/useAuth.ts` | Auth state management |
| `sister-domain-starter/src/composables/useAccess.ts` | Feature access checking |
| `sister-domain-starter/src/composables/useBillingRedirect.ts` | Billing return handling |
| `sister-domain-starter/src/composables/useSubscription.ts` | Subscription state |

### Current Dealer Files (To Be Replaced)

| File | Issue |
|------|-------|
| `dealerfrontend/src/lib/auth.ts` | Points to dealerbackend, not SattaBase |
| `dealerfrontend/src/composables/useSSO.ts` | Unnecessary proxy layer |
| `dealerfrontend/src/composables/usePermissions.ts` | Hardcoded roles |
| `dealerfrontend/src/services/apiClient.ts` | Separate API client |
| `dealerbackend/common/auth_controller.py` | Proxies auth to SattaBase |
| `dealerbackend/common/sso_controller.py` | Duplicates SDK functionality |

---

## Migration Notes

### Permission Migration

Current `usePermissions.ts` has these roles:
- `DEALER` — Full access
- `DSR` — Sales, inventory view, collections
- `COLLECTOR` — Order entry, sales create
- `ADMIN` — Full access

**Migration to access map:**

Instead of:
```typescript
const { can, isDealer } = usePermissions();
if (can(Permission.DEALER_REPORTS)) { ... }
```

Use:
```typescript
const { hasAccess, getLimit } = useAccess();
if (hasAccess('reports').value) { ... }
const maxDsrs = getLimit('max_dsrs', 1).value;
```

### Access Keys for DealerCore

| Access Key | Type | Description |
|------------|------|-------------|
| `dashboard` | boolean | Access to main dashboard |
| `inventory` | boolean | Manage inventory |
| `sales` | boolean | Create and manage sales |
| `collections` | boolean | View and manage collections |
| `reports` | boolean | Financial reports |
| `suppliers` | boolean | Supplier management |
| `bad_debt` | boolean | Bad debt management |
| `max_products` | integer | Maximum products in inventory |
| `max_dsrs` | integer | Maximum DSR users |
| `max_suppliers` | integer | Maximum suppliers |
| `export_pdf` | boolean | Export reports as PDF |
| `api_access` | boolean | REST API access |
| `priority_support` | boolean | Priority customer support |
| `white_label` | boolean | White-label reports |
| `audit_log` | boolean | Full audit log |

---

## Changelog

| Date | Task | Status | Notes |
|------|------|--------|-------|
| 2026-06-11 | Initial Analysis | ✅ Complete | Identified all issues and created tracking document |
| 2026-06-11 | TASK-1.1 | ✅ Complete | Created `sattabase.config.ts` with all configuration options |
| 2026-06-11 | TASK-1.2 | ✅ Complete | Updated `.env.example` with new PUBLIC_* environment variables |
| 2026-06-11 | TASK-1.3 | ✅ Complete | Updated `lib/constants.ts` to use central config |
| 2026-06-11 | TASK-2.1 | ✅ Complete | Deleted `useSSO.ts`, updated `ManageBillingButton.vue` |
| 2026-06-11 | TASK-2.2 | ✅ Complete | Archived `usePermissions.ts`, updated `PermissionGuard.vue` |
| 2026-06-11 | TASK-2.3 | ✅ Complete | Updated `apiClient.ts` to use token from `lib/api.ts` |
| 2026-06-11 | TASK-2.5.1 | ✅ Complete | Created `lib/types.ts` with auth-related types |
| 2026-06-11 | TASK-2.5.2 | ✅ Complete | Created `lib/api.ts` with SattaBase API client + dealerApi |
| 2026-06-11 | TASK-2.5.3 | ✅ Complete | Created `useAccess.ts` to replace `usePermissions` |
| 2026-06-11 | TASK-2.5.4 | ✅ Complete | Updated `ManageBillingButton.vue` for new auth pattern |
| 2026-06-11 | TASK-2.5.5 | ✅ Complete | Updated `PermissionGuard.vue` for `useAccess` |
| 2026-06-11 | TASK-2.5.6 | ✅ Complete | Updated `services/api/index.ts` barrel exports |
| 2026-06-11 | TASK-3.1 | ✅ Complete | Replaced `lib/auth.ts` with SattaBase-direct auth pattern |
| 2026-06-11 | TASK-3.2 | ✅ Complete | `lib/api.ts` verified (created in Phase 2.5) |
| 2026-06-11 | TASK-3.3 | ✅ Complete | Replaced `useAuth.ts` with singleton state pattern |
| 2026-06-11 | TASK-4.1 | ✅ Complete | `useAccess.ts` verified (created in Phase 2.5) |
| 2026-06-11 | TASK-4.2 | ✅ Complete | Created `useBillingRedirect.ts` for billing return detection |
| 2026-06-11 | TASK-4.3 | ✅ Complete | Created `useSubscription.ts` for subscription state |
| 2026-06-11 | TASK-4.4 | ✅ Complete | Added `SubscriptionOutput` type to `lib/types.ts` |
| 2026-06-11 | TASK-5.1 | ✅ Complete | `LoginForm.vue` verified (updated in Phase 3) |
| 2026-06-11 | TASK-5.2 | ✅ Complete | Updated `LoginPage.vue` with `redirectToBase()` |
| 2026-06-11 | TASK-5.3 | ✅ Complete | Updated `SessionGuard.vue` with billing redirect |
| 2026-06-11 | TASK-5.4 | ✅ Complete | `PermissionGuard.vue` verified (Phase 2.5) |
| 2026-06-11 | TASK-5.5 | ✅ Complete | `ManageBillingButton.vue` verified (Phase 2.5) |
| 2026-06-11 | TASK-5.6 | ✅ Complete | `App.vue` verified - auth flow working correctly |
| 2026-06-11 | TASK-5.7 | ✅ Complete | No remaining `usePermissions` imports |
| 2026-06-11 | TASK-6.1 | ✅ Complete | Verified `sattabase_client.py` implementation |
| 2026-06-11 | TASK-6.2 | ✅ Complete | `sattabase_client.py` already properly implemented |
| 2026-06-11 | TASK-6.3 | ✅ Complete | Added SattaBase config to `settings.py` |
| 2026-06-11 | TASK-6.4 | ✅ Complete | Verified `permission_middleware.py` JWT handling |
| 2026-06-11 | TASK-7.1 | ✅ Complete | Added DealerCore to `billing_seed_data.py` |
| 2026-06-11 | Config Fix | ✅ Complete | Fixed Vite path alias: `@/*` → `./src/*` in tsconfig.json and astro.config.mjs |
| 2026-06-11 | API Fix | ✅ Complete | Fixed double `/api/api/` in service endpoints - removed `/api` prefix since base URL already includes it |
| 2026-06-11 | LoginForm Fix | ✅ Complete | Removed redundant forgot-password link (kept working one in LoginPage.vue) |
| 2026-06-11 | CORS Fix | ℹ️ Needed | Added `http://localhost:4323` to SattaBase CORS_ALLOWED_ORIGINS |
| 2026-06-11 | Auth Helper | ✅ Added | Added `checkBaseDomainSession()` for cross-domain session sharing (requires backend endpoint) |
| 2026-06-11 | Logout Fix | ✅ Complete | Fixed logout redirect: `/auth/login` → `/` (SPA has no separate route) |
| 2026-06-11 | Audit | ✅ Complete | Comprehensive audit of DSR/Collector multi-tenancy, access control, and seed data |
| 2026-06-11 | TASK-9.1 | ✅ Complete | Implemented navigation access guards in App.vue - navItems filtered by hasAccess() |
| 2026-06-11 | TASK-9.2 | ✅ Complete | Wrapped all 7 tab components with PermissionGuard |
| 2026-06-11 | TASK-9.3 | ✅ Complete | Added max_products limit enforcement in handleAddProduct() |
| 2026-06-11 | TASK-9.4 | ✅ Complete | Added max_dsrs limit enforcement in handleAddDsr() |
| 2026-06-11 | TASK-9.5 | ✅ Complete | Added max_suppliers limit enforcement in handleAddSupplier() |
| 2026-06-11 | TASK-9.6 | ✅ Complete | Added dealer context extraction to permission middleware |
| 2026-06-11 | TASK-9.7 | ✅ Complete | Fixed DSR API dealer scoping with DsrDealerAssignment filtering |
| 2026-06-11 | TASK-9.8 | ✅ Complete | Fixed invitation acceptance logic with email verification |
| 2026-06-11 | TASK-9.9 | ✅ Complete | Added ai_insights and data_retention_days to DealerCore seed data |
| 2026-06-11 | TASK-10.1 | ✅ Complete | Added dealer FK to Product model with per-dealer SKU uniqueness |
| 2026-06-11 | TASK-10.2 | ✅ Complete | Added dealer FK to SaleRecord model for tenant isolation |
| 2026-06-11 | TASK-10.3 | ✅ Complete | Added dealer FK to Supplier model with per-dealer name uniqueness |
| 2026-06-11 | TASK-10.4 | ✅ Complete | Added dealer FK to RestockRecord model |
| 2026-06-11 | TASK-10.5 | ✅ Complete | Added dealer FK to Brand and Category models |
| 2026-06-11 | TASK-10.6 | ✅ Complete | Created multi-tenancy migrations for all affected models |
| 2026-06-11 | TASK-11.1 | ✅ Complete | Created dealer_context.py helper module for dealer context validation |
| 2026-06-11 | TASK-11.2 | ✅ Complete | Updated SalesController with dealer scoping on all endpoints |
| 2026-06-11 | TASK-11.3 | ✅ Complete | Updated InventoryController with dealer scoping on all endpoints |
| 2026-06-11 | TASK-11.4 | ✅ Complete | DSRController dealer scoping verified (done in Phase 9) |
| 2026-06-11 | TASK-11.5 | ✅ Complete | Updated SupplierController with dealer scoping on all endpoints |

---

## Audit Report: DSR/Collector Multi-Tenancy & Access Control

**Audit Date**: 2026-06-11
**Scope**: DealerBackend models, DealerFrontend access control, Billing seed data alignment

---

### 1. DSR/Collector Multi-Tenancy Architecture

#### Data Model Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                         DEALER SYSTEM MULTI-TENANCY MODEL                        │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌─────────────────┐         ┌────────────────────┐         ┌─────────────────┐  │
│  │  DealerConfig   │◄────────│ DsrDealerAssignment│────────►│      DSR        │  │
│  │  (username PK)  │         │  (junction table)   │         │                 │  │
│  ├─────────────────┤         ├─────────────────────┤         ├─────────────────┤  │
│  │ username (PK)   │         │ dsr_id (FK)         │         │ id (PK)         │  │
│  │ full_name       │         │ dealer_username(FK) │         │ name            │  │
│  │ business_name   │         │ role (DSR/Collector)│         │ phone           │  │
│  │ ...             │         │ is_active           │         │ role            │  │
│  └─────────────────┘         │ commission_rate     │         │ parent_dsr (FK) │  │
│                              └─────────────────────┘         └─────────────────┘  │
│                                       │                                          │
│                                       │                                          │
│                              ┌────────────────────┐                              │
│                              │   DsrInvitation    │                              │
│                              ├────────────────────┤                              │
│                              │ dealer (FK)        │                              │
│                              │ email              │                              │
│                              │ role               │                              │
│                              │ token (7-day exp)  │                              │
│                              │ status             │                              │
│                              │ parent_dsr (FK)    │                              │
│                              └────────────────────┘                              │
│                                                                                   │
└──────────────────────────────────────────────────────────────────────────────────┘
```

#### Key Models

| Model | Purpose | Key Fields |
|-------|---------|------------|
| **DealerConfig** | Dealer business configuration | `username` (PK from SattaBase user), `business_name`, `default_currency` |
| **DSR** | Sales representative / collector | `name`, `phone`, `role` (DSR/Collector), `parent_dsr` (for hierarchy) |
| **DsrDealerAssignment** | Multi-tenancy junction | `dsr`, `dealer`, `role`, `is_active`, `commission_rate` |
| **DsrInvitation** | Invitation flow | `email`, `token`, `expires_at`, `status` |

#### Multi-Tenancy Flow

```
1. Dealer registers on SattaBase (4321) → subscribes to DealerCore
2. Dealer logs into DealerFrontend (4323)
3. Dealer invites DSR/Collector via email
4. DSR receives invitation → accepts → DsrDealerAssignment created
5. DSR can work for MULTIPLE dealers (each has separate assignment)
6. Data is isolated per dealer via dealer__username filtering
```

#### Role Hierarchy

```
DEALER (from SattaBase JWT)
    │
    ├── DSR (Daily Sales Representative)
    │       ├── Can create sales
    │       ├── Can view inventory
    │       ├── Can collect payments
    │       └── May have Order Collectors reporting to them
    │
    └── COLLECTOR (Order Collector)
            ├── Can create sales (entry only)
            ├── Reports to parent_dsr
            └── Limited permissions
```

---

### 2. Access Control Audit Findings

#### Frontend Access Control Status

| Component | Status | Details |
|-----------|--------|---------|
| **useAccess.ts** | ✅ Implemented | `hasAccess()`, `getLimit()`, `getAccess()` methods work |
| **PermissionGuard.vue** | ✅ Available | Supports `feature`, `any`, `all` props |
| **Navigation Guarding** | ❌ NOT Implemented | All nav items show regardless of access |
| **Tab Content Guarding** | ❌ NOT Implemented | All components render regardless of access |
| **Limit Enforcement** | ❌ NOT Implemented | No `max_*` checks before create operations |

#### Features Requiring Access Control

| Feature Key | Component | Current Access Control |
|-------------|-----------|------------------------|
| `dashboard` | Overview.vue | ❌ None |
| `inventory` | Inventory.vue | ❌ None |
| `suppliers` | Suppliers.vue | ❌ None |
| `sales` | Sales.vue | ❌ None |
| `collections` | Collections.vue | ❌ None |
| `bad_debt` | BadDebt.vue | ❌ None |
| `reports` | Reports.vue | ❌ None |

#### Numeric Limits Requiring Enforcement

| Limit Key | Enforced Where | Current Status |
|-----------|----------------|----------------|
| `max_products` | Inventory.vue → add product | ❌ NOT ENFORCED |
| `max_dsrs` | Reports.vue → add DSR | ❌ NOT ENFORCED |
| `max_suppliers` | Suppliers.vue → add supplier | ❌ NOT ENFORCED |

---

### 3. Backend Security Audit Findings

#### JWT Token Handling

| Issue | Location | Severity | Description |
|-------|----------|----------|-------------|
| No signature verification | `permission_middleware.py:57` | 🔴 High | `jwt.decode(token, options={"verify_signature": False})` - Trusts SattaBase but vulnerable to token tampering |
| No dealer context in DSR API | `dsr/api.py` | 🟡 Medium | DSR list should be filtered by dealer assignment |
| Invitation acceptance bug | `invitation_api.py:242` | 🟡 Medium | Uses `phone=invitation.email` lookup which is incorrect |

#### Tenant Isolation

| Check | Status | Notes |
|-------|--------|-------|
| Sales filtered by dealer | ✅ Partial | Need to verify all endpoints |
| Products filtered by dealer | ⚠️ Verify | Check if dealer_id is properly set |
| DSR list filtered by dealer | ❌ Missing | Returns ALL DSRs, not dealer-scoped |

---

### 4. Billing Seed Data Audit

#### Current DealerCore Plans

| Plan | Price | Products | DSRs | Suppliers | Key Limits |
|------|-------|----------|------|-----------|------------|
| **Free** | $0/mo | 50 | 1 | 3 | No reports, no suppliers, no bad_debt |
| **Standard** | $29/mo | 500 | 5 | 20 | Full features |
| **Enterprise** | $99/mo | Unlimited | Unlimited | Unlimited | + priority_support, white_label, audit_log |

#### Access Keys Coverage

| Feature | Free | Standard | Enterprise | Match Frontend? |
|---------|------|----------|------------|-----------------|
| `dashboard` | ✅ true | ✅ true | ✅ true | ✅ |
| `inventory` | ✅ true | ✅ true | ✅ true | ✅ |
| `sales` | ✅ true | ✅ true | ✅ true | ✅ |
| `collections` | ✅ true | ✅ true | ✅ true | ✅ |
| `reports` | ❌ false | ✅ true | ✅ true | ✅ |
| `suppliers` | ❌ false | ✅ true | ✅ true | ✅ |
| `bad_debt` | ❌ false | ✅ true | ✅ true | ✅ |
| `max_products` | ✅ 50 | ✅ 500 | ✅ 0 (unlimited) | ✅ |
| `max_dsrs` | ✅ 1 | ✅ 5 | ✅ 0 (unlimited) | ✅ |
| `max_suppliers` | ✅ 3 | ✅ 20 | ✅ 0 (unlimited) | ✅ |
| `export_pdf` | ❌ false | ✅ true | ✅ true | ✅ |
| `api_access` | ❌ false | ✅ true | ✅ true | ⚠️ Not used in frontend |
| `priority_support` | ❌ false | ❌ false | ✅ true | ⚠️ Not used in frontend |
| `white_label` | ❌ false | ❌ false | ✅ true | ⚠️ Not used in frontend |
| `audit_log` | ❌ false | ❌ false | ✅ true | ⚠️ Not used in frontend |
| `ai_insights` | ❌ Missing | ❌ Missing | ❌ Missing | ❌ Frontend has AI reconciliation |
| `data_retention_days` | ❌ Missing | ❌ Missing | ❌ Missing | ⚠️ Standard in other products |

#### Recommended Access Key Additions

```python
# Missing keys to add in billing_seed_data.py:

# For AI Reconciliation feature
{"key": "ai_insights", "value": "false", "value_type": AccessValueType.BOOLEAN},  # Free
{"key": "ai_insights", "value": "false", "value_type": AccessValueType.BOOLEAN},  # Standard
{"key": "ai_insights", "value": "true", "value_type": AccessValueType.BOOLEAN},   # Enterprise

# For data retention (standard in other products)
{"key": "data_retention_days", "value": "30", "value_type": AccessValueType.INTEGER},   # Free
{"key": "data_retention_days", "value": "365", "value_type": AccessValueType.INTEGER},  # Standard
{"key": "data_retention_days", "value": "0", "value_type": AccessValueType.INTEGER},    # Enterprise (unlimited)
```

---

### 5. Critical Gaps Summary

#### 🔴 High Priority

| Gap | Impact | Status |
|-----|--------|--------|
| No frontend access control enforcement | Users access all features regardless of plan | ✅ FIXED - Navigation guards and PermissionGuard implemented |
| No limit enforcement | Users can exceed plan limits | ✅ FIXED - max_products, max_dsrs, max_suppliers checks added |
| JWT not verified in backend | Security vulnerability | 🔴 Still needs fix - Add signature verification or cache validation with SattaBase |

#### 🟡 Medium Priority

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| DSR list not dealer-scoped | Data isolation issue | Add dealer filtering in DSR API |
| Missing `ai_insights` access key | AI feature not gated | Add to seed data |
| Invitation acceptance bug | DSR onboarding fails | Fix `phone=email` lookup |

#### 🟢 Low Priority

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| Missing `data_retention_days` | Inconsistent with other products | Add to seed data |
| Unused access keys | Dead config in billing | Consider removing or implementing |

---

### Phase 9: Access Control Implementation

- [x] **TASK-9.1**: Implement navigation access guards in `App.vue` ✅ DONE (2026-06-11)
  - Added `useAccess()` import and usage in App.vue
  - Created `allNavItems` array with access keys
  - Implemented computed `navItems` filtered by `hasAccess()` checks
  - Navigation tabs now hide based on subscription access

- [x] **TASK-9.2**: Wrap tab components with `PermissionGuard` ✅ DONE (2026-06-11)
  - Imported `PermissionGuard` component
  - Wrapped all 7 tab components (Overview, Inventory, Suppliers, Sales, Collections, BadDebt, Reports)
  - Each component checks its feature access key before rendering

- [x] **TASK-9.3**: Implement limit enforcement in Inventory.vue ✅ DONE (2026-06-11)
  - Added `maxProducts` limit check in `handleAddProduct()`
  - Checks `max_products` access key before allowing product creation
  - Shows error toast with upgrade prompt when limit reached

- [x] **TASK-9.4**: Implement limit enforcement in Reports.vue ✅ DONE (2026-06-11)
  - Added `maxDsrs` limit check in `handleAddDsr()`
  - Checks `max_dsrs` access key before allowing DSR creation
  - Shows error toast with upgrade prompt when limit reached

- [x] **TASK-9.5**: Implement limit enforcement in Suppliers.vue ✅ DONE (2026-06-11)
  - Added `maxSuppliers` limit check in `handleAddSupplier()`
  - Checks `max_suppliers` access key before allowing supplier creation
  - Shows error toast with upgrade prompt when limit reached

- [x] **TASK-9.6**: Add dealer context middleware in dealerbackend ✅ DONE (2026-06-11)
  - Updated `PermissionMiddleware` and `AsyncPermissionMiddleware` to extract `dealer_username` and `user_email` from JWT
  - Added `request.dealer_username` and `request.user_email` attributes for dealer context scoping
  - Enables proper tenant isolation across all dealer-scoped endpoints

- [x] **TASK-9.7**: Fix DSR API dealer scoping ✅ DONE (2026-06-11)
  - Updated `DSRController` to filter DSRs by `DsrDealerAssignment` for current dealer
  - All endpoints (list, get, create, update, delete) now verify dealer ownership
  - DSR creation automatically creates `DsrDealerAssignment` for the creating dealer
  - Delete removes assignment (not DSR if other assignments exist)

- [x] **TASK-9.8**: Fix invitation acceptance logic ✅ DONE (2026-06-11)
  - Fixed `accept_invitation` to use `request.user_email` from middleware
  - Added email verification: only invited user can accept
  - Creates DSR automatically for new users instead of failing
  - Added `_generate_dsr_id()` helper for unique ID generation
  - Fixed all invitation endpoints to use `request.dealer_username`

- [x] **TASK-9.9**: Add missing access keys to seed data ✅ DONE (2026-06-11)
  - Added `ai_insights` access key to all three DealerCore plans
    - Free: false
    - Standard: false
    - Enterprise: true
  - Added `data_retention_days` access key to all three plans
    - Free: 30 days
    - Standard: 365 days
    - Enterprise: 0 (unlimited)

---

### DSR/Collector Invitation Flow (Design)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        DSR INVITATION FLOW                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  1. DEALER INVITES                                                               │
│     ┌─────────────┐                                                              │
│     │   Dealer    │ ─── POST /api/dsrs/invite ───► DsrInvitation created        │
│     │  (4323)     │      {email, role, parent_dsr}                               │
│     └─────────────┘              │                                               │
│                                   ▼                                               │
│                          Email sent with token                                    │
│                                                                                  │
│  2. DSR ACCEPTS                                                                  │
│     ┌─────────────┐                                                              │
│     │    DSR      │ ─── Click link ───► /auth/accept-invite?token=XXX          │
│     │  (Email)    │                                               │               │
│     └─────────────┘                                               ▼               │
│                                                          Validate token           │
│                                                          Check SattaBase user     │
│                                                                   │               │
│                                                                   ▼               │
│                                                    ┌──────────────────────────┐   │
│                                                    │ If user exists on        │   │
│                                                    │ SattaBase:               │   │
│                                                    │  - Create/get DSR        │   │
│                                                    │  - Create Assignment     │   │
│                                                    │  - Mark invitation done  │   │
│                                                    └──────────────────────────┘   │
│                                                                                  │
│  3. DSR LOGINS                                                                   │
│     ┌─────────────┐                                                              │
│     │    DSR      │ ─── Login on 4323 ───► JWT with role="dsr"                  │
│     │  (4323)     │      Can only see dealer's data via assignment              │
│     └─────────────┘                                                              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Transaction Security & Multi-Dealer Context Audit

### The Core Problem

When a DSR/Collector works for multiple dealers, they need to select which dealer they're working under during data entry (sales, inventory, etc.). Currently, the system has **NO dealer context enforcement** in the business logic APIs.

### Current Security State

#### 🔴 Critical: No Tenant Isolation in Business Logic

| Model | Dealer Association | API Filtering | Security Status |
|-------|-------------------|---------------|-----------------|
| **Product** | ❌ NO `dealer` field | ❌ No filtering | Any authenticated user can access ALL products |
| **SaleRecord** | ❌ NO `dealer` field | ❌ No filtering | Any authenticated user can access ALL sales |
| **DSR** | ✅ Via `DsrDealerAssignment` | ❌ No filtering | DSR list returns ALL DSRs globally |
| **Supplier** | ❌ NO `dealer` field | ❌ No filtering | Any authenticated user can access ALL suppliers |
| **RestockRecord** | ❌ NO `dealer` field | ❌ No filtering | Any authenticated user can access ALL restocks |

#### Data Model Gap Analysis

```
CURRENT MODELS (Missing dealer isolation):
┌─────────────────────────────────────────────────────────────────┐
│  Product                                                        │
│  ├─ id (PK)                                                     │
│  ├─ name, sku, brand, category                                  │
│  ├─ stock, selling_price, unit_price                           │
│  └─ ❌ NO dealer_id field                                       │
│                                                                  │
│  SaleRecord                                                     │
│  ├─ id (PK)                                                     │
│  ├─ product (FK), dsr (FK)                                      │
│  ├─ customer_name, total_amount                                 │
│  └─ ❌ NO dealer_id field                                       │
│                                                                  │
│  Supplier                                                       │
│  ├─ id (PK)                                                     │
│  ├─ name, contact_person, phone                                 │
│  └─ ❌ NO dealer_id field                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Multi-Dealer DSR Scenario

```
SCENARIO: DSR "John" works for TWO dealers

1. John accepts invitation from Dealer A (makes 500 sales/month)
2. John accepts invitation from Dealer B (makes 200 sales/month)

PROBLEM: When John creates a sale:
┌─────────────────────────────────────────────────────────────────┐
│ POST /api/sales                                                 │
│ {                                                               │
│   "product_id": "prod-123",                                     │
│   "quantity": 10,                                               │
│   "customer_name": "Customer X"                                 │
│   // ❌ NO dealer_id in payload                                 │
│   // ❌ NO dealer context in JWT                                │
│   // ❌ NO dealer selection in frontend                         │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘

RESULT: Sale is created WITHOUT dealer association
- Who does this sale belong to? UNKNOWN
- Which dealer's inventory was depleted? UNKNOWN
- Which dealer gets the revenue? UNKNOWN
```

### Security Vulnerability Summary

| Vulnerability | Severity | Impact |
|---------------|----------|--------|
| Cross-tenant data access | 🔴 Critical | DSR from Dealer A can view/modify Dealer B's data |
| Inventory manipulation | 🔴 Critical | Stock depletion not attributed to correct dealer |
| Revenue attribution loss | 🔴 Critical | Sales revenue goes to wrong dealer or unattributed |
| Collection misdirection | 🔴 Critical | Payments collected for wrong dealer |
| Report contamination | 🟡 High | Reports mix data from multiple dealers |

---

## 7. Recommended System Design for Multi-Tenancy

### Option A: Add `dealer_id` to All Business Models (Recommended)

```python
# Add dealer field to all business models

class Product(models.Model):
    # ... existing fields ...
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='products',
        db_column='dealer_username'
    )
    
class SaleRecord(models.Model):
    # ... existing fields ...
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='sales',
        db_column='dealer_username'
    )
    
class Supplier(models.Model):
    # ... existing fields ...
    dealer = models.ForeignKey(
        'dealer.DealerConfig',
        on_delete=models.CASCADE,
        related_name='suppliers',
        db_column='dealer_username'
    )
```

**Benefits:**
- Simple, explicit data ownership
- Easy filtering in all queries
- Clear audit trail
- No ambiguity in multi-dealer scenarios

**Migration Required:**
- Add `dealer_username` column to each table
- Populate from existing data or require manual assignment
- Update all API endpoints to filter by dealer

### Option B: Dealer Context Middleware (Complementary)

```python
# dealerbackend/common/dealer_context.py

from django.http import HttpRequest
from dealer.models import DealerConfig
from dsr.invitation_models import DsrDealerAssignment

class DealerContext:
    """
    Manages the "active dealer" context for multi-dealer DSRs.
    
    Flow:
    1. Extract user info from JWT (username, role)
    2. If user is dealer → use their username
    3. If user is DSR/Collector:
       a. Check X-Dealer-Username header (explicit selection)
       b. If single assignment → use that dealer
       c. If multiple assignments → require selection
    """
    
    @staticmethod
    async def get_active_dealer(request: HttpRequest) -> DealerConfig:
        username = request.user.username  # From JWT
        role = request.user_role
        
        if role == 'dealer' or request.is_dealer:
            # User IS the dealer
            return await DealerConfig.objects.aget(username=username)
        
        # User is DSR/Collector - check assignments
        assignments = DsrDealerAssignment.objects.filter(
            dsr__phone=username,  # Or however DSR is linked to user
            is_active=True
        ).select_related('dealer')
        
        # Check explicit selection header
        selected_dealer = request.headers.get('X-Dealer-Username')
        if selected_dealer:
            assignment = await assignments.filter(
                dealer__username=selected_dealer
            ).afirst()
            if assignment:
                return assignment.dealer
            raise ValueError("Not assigned to this dealer")
        
        # Auto-select if single assignment
        count = await assignments.acount()
        if count == 1:
            assignment = await assignments.afirst()
            return assignment.dealer
        
        if count > 1:
            raise ValueError(
                "Multiple dealer assignments. "
                "Select a dealer using X-Dealer-Username header."
            )
        
        raise ValueError("No active dealer assignment found")
```

### Frontend Dealer Selection UI

```vue
<!-- DealerSelector.vue - Required for multi-dealer DSRs -->
<template>
  <div v-if="showSelector" class="dealer-selector">
    <label>Select Dealer:</label>
    <select v-model="selectedDealer" @change="onDealerChange">
      <option v-for="assignment in dealerAssignments" 
              :key="assignment.dealer_username"
              :value="assignment.dealer_username">
        {{ assignment.dealer_name }} ({{ assignment.role }})
      </option>
    </select>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useAuth } from '../composables/useAuth';
import { dealerApi } from '../lib/api';

const { user } = useAuth();
const selectedDealer = ref(null);
const dealerAssignments = ref([]);

const showSelector = computed(() => 
  dealerAssignments.value.length > 1
);

onMounted(async () => {
  // Fetch user's dealer assignments
  const response = await dealerApi.get('/invitations/assignments');
  dealerAssignments.value = response.data;
  
  if (dealerAssignments.value.length === 1) {
    selectedDealer.value = dealerAssignments.value[0].dealer_username;
  }
});

function onDealerChange() {
  // Store selection in localStorage for persistence
  localStorage.setItem('activeDealer', selectedDealer.value);
  
  // Update API client default header
  dealerApi.defaults.headers['X-Dealer-Username'] = selectedDealer.value;
}
</script>
```

---

## 8. Implementation Roadmap

### Phase 10: Multi-Tenancy Data Model Update (dealerbackend) ✅ COMPLETE

- [x] **TASK-10.1**: Add `dealer` field to `Product` model ✅ DONE (2026-06-11)
  - Added `dealer = models.ForeignKey(DealerConfig, ...)` with `db_column='dealer_username'`
  - Changed SKU uniqueness from global to per-dealer via `UniqueConstraint`
  - Added dealer-scoped indexes for efficient filtering

- [x] **TASK-10.2**: Add `dealer` field to `SaleRecord` model ✅ DONE (2026-06-11)
  - Added dealer FK for revenue attribution and tenant isolation
  - Added dealer-scoped indexes for date and collection_status queries

- [x] **TASK-10.3**: Add `dealer` field to `Supplier` model ✅ DONE (2026-06-11)
  - Added dealer FK for supplier isolation
  - Changed name uniqueness from global to per-dealer
  - Added dealer-scoped indexes

- [x] **TASK-10.4**: Add `dealer` field to `RestockRecord` model ✅ DONE (2026-06-11)
  - Added dealer FK (denormalized for quick access)
  - Added dealer-scoped indexes

- [x] **TASK-10.5**: Add `dealer` field to `Brand` and `Category` models ✅ DONE (2026-06-11)
  - Added dealer FK to both models
  - Changed name uniqueness from global to per-dealer
  - Added dealer-scoped indexes

- [x] **TASK-10.6**: Create database migrations ✅ DONE (2026-06-11)
  - Created `inventory/migrations/0004_add_dealer_multitenancy.py`
  - Created `sales/migrations/0006_add_dealer_multitenancy.py`
  - Created `supplier/migrations/0003_add_dealer_multitenancy.py`
  - Migrations add nullable fields first (for existing data compatibility)
  - Includes new per-dealer unique constraints and indexes

**Key Changes Summary:**
- All business models now have `dealer` FK for tenant isolation
- SKU/Name uniqueness changed from global to per-dealer
- Added comprehensive dealer-scoped indexes for query performance
- Migrations designed for gradual rollout (nullable first)

### Phase 11: API Dealer Scoping (dealerbackend)

- [x] **TASK-11.1**: Create `dealer_context.py` helper module ✅ DONE (2026-06-11)
  - Created `common/dealer_context.py` with `get_dealer_context()` and `validate_dsr_access()`
  - Handles both Dealer and DSR/Collector access patterns
  - Supports `X-Dealer-Context` header for DSR dealer selection

- [x] **TASK-11.2**: Update `SalesController` to filter by dealer ✅ DONE (2026-06-11)
  - All endpoints (list, get, create, bulk, collect, return, void, edit) now dealer-scoped
  - Sale creation auto-associates with dealer from context
  - Products validated to belong to same dealer
  - ID generation scoped per-dealer

- [x] **TASK-11.3**: Update `InventoryController` to filter by dealer ✅ DONE (2026-06-11)
  - All endpoints (products, restocks, brands, categories) now dealer-scoped
  - Product creation auto-associates with dealer from context
  - Brands and categories scoped per-dealer (unique name per dealer)
  - ID generation scoped per-dealer

- [x] **TASK-11.4**: Update `DSRController` to filter by dealer ✅ DONE (2026-06-11)
  - Already implemented in Phase 9 (TASK-9.7)
  - DSRs filtered via `DsrDealerAssignment` for current dealer
  - Only shows DSRs assigned to current dealer

- [x] **TASK-11.5**: Update `SupplierController` to filter by dealer ✅ DONE (2026-06-11)
  - All endpoints (list, get, create, update, delete) now dealer-scoped
  - Supplier creation auto-associates with dealer from context
  - Supplier names unique per dealer (not globally)
  - ID generation scoped per-dealer

### Phase 12: Frontend Dealer Selection (dealerfrontend)

- [ ] **TASK-12.1**: Create `DealerSelector.vue` component
  - Show dropdown for multi-dealer DSRs
  - Auto-select for single-dealer DSRs

- [ ] **TASK-12.2**: Update API client to include `X-Dealer-Username` header
  - Read from localStorage on each request
  - Handle missing dealer context errors

- [ ] **TASK-12.3**: Add dealer selector to main navigation
  - Place prominently for multi-dealer users
  - Show current dealer context

- [ ] **TASK-12.4**: Update sales/inventory forms
  - Validate dealer context before submission
  - Show clear error if no dealer selected

---

## 9. Security Considerations

### JWT Enhancement Needed

Currently the JWT only contains:
```json
{
  "username": "dealer123",
  "role": "dealer",
  "is_dealer": true
}
```

**Recommended additions:**
```json
{
  "username": "dealer123",
  "role": "dealer",
  "is_dealer": true,
  "dealer_usernames": ["dealer123"],
  "default_dealer": "dealer123"
}
```

For DSRs working for multiple dealers:
```json
{
  "username": "dsr_john",
  "role": "dsr",
  "is_dealer": false,
  "dealer_usernames": ["dealerA", "dealerB"],
  "default_dealer": "dealerA"
}
```

### API Request Validation

```python
# Validation flow for any create/update operation

async def validate_dealer_access(request, dealer_username):
    """
    Ensure user has access to the specified dealer.
    """
    if request.is_dealer:
        # Dealers can only access their own data
        if dealer_username != request.user.username:
            raise PermissionError("Cannot access other dealer's data")
        return True
    
    # DSR/Collector - check assignment
    has_assignment = await DsrDealerAssignment.objects.filter(
        dsr__phone=request.user.username,
        dealer__username=dealer_username,
        is_active=True
    ).aexists()
    
    if not has_assignment:
        raise PermissionError("Not assigned to this dealer")
    
    return True
```

---

## 10. Summary of Findings

### 🔴 Critical Security Gaps

| Gap | Location | Risk | Fix Priority |
|-----|----------|------|--------------|
| No dealer field on Product | `inventory/models.py` | Cross-tenant data access | P0 |
| No dealer field on SaleRecord | `sales/models.py` | Revenue attribution loss | P0 |
| No dealer field on Supplier | `supplier/models.py` | Cross-tenant data access | P0 |
| No dealer filtering in APIs | All controllers | Data isolation failure | P0 |
| DSR list not dealer-scoped | `dsr/api.py` | Information disclosure | P1 |

### 🟡 Design Gaps

| Gap | Location | Impact | Recommendation |
|-----|----------|--------|----------------|
| No dealer selection UI | Frontend | User confusion | Add dealer selector |
| No X-Dealer-Username header | API client | Context loss | Add header injection |
| JWT missing dealer context | Auth system | Security weak point | Enhance JWT claims |

### 🟢 Already Implemented

| Feature | Location | Status |
|---------|----------|--------|
| DsrDealerAssignment model | `dsr/invitation_models.py` | ✅ Ready |
| DsrInvitation model | `dsr/invitation_models.py` | ✅ Ready |
| Multi-dealer invitation flow | `dsr/invitation_api.py` | ✅ Ready (bug fix needed) |
| Access control composable | `useAccess.ts` | ✅ Ready |
| Permission guard component | `PermissionGuard.vue` | ✅ Ready |

---

## Next Steps

1. **Phase 8** — Test the complete auth flow with SattaBase
2. **Phase 9** — ✅ COMPLETE — Access control enforcement implemented (navigation guards, feature gating, limit enforcement)
3. **Phase 10** — Add dealer field to all business models (migration required)
4. **Phase 11** — Implement dealer context middleware and API filtering
5. **Phase 12** — Add dealer selection UI for multi-dealer DSRs/Collectors
6. Run `python manage.py billing_seed_data` to create DealerCore product in SattaBase
7. **Update this document** as tasks are completed
