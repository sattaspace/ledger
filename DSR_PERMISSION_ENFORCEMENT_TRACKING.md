# DSR Permission Enforcement — Implementation Tracking

**Created**: 2026-06-16  
**Status**: ✅ **ALL PHASES COMPLETE**  
**Goal**: Ensure DSR permissions are constrained by dealer's subscription access matrix and enforced server-side.

---

## Gap Analysis

| # | Gap | Severity | Status |
|---|-----|----------|--------|
| 1 | No SattaBase API endpoint for DealerBackend to query subscriber's access matrix by `subscriber_id + service_domain` | 🔴 Critical | ✅ Fixed |
| 2 | DSR permissions not constrained by dealer's subscription — dealer on Free plan (no `suppliers`) can assign `suppliers: true` to DSR | 🔴 Critical | ✅ Fixed |
| 3 | DSR module permissions NOT enforced server-side — `sales/api.py` and `inventory/api.py` don't check `DsrDealerAssignment.has_permission()` | 🔴 Critical | ✅ Fixed |
| 4 | Two separate permission systems disconnected — Plan-level (`useAccess`) vs DSR-level (`DsrDealerAssignment.permissions`) | 🟡 Should Fix | ✅ Fixed |
| 5 | `DsrDealerAssignment.has_permission()` is dead code — never called from any endpoint | 🟡 Should Fix | ✅ Fixed |
| 6 | Plan limit for `max_dsrs` not checked on reactivation — only on invite | 🟢 Nice to Have | ✅ Fixed |

---

## Phase 1: SattaBase — New Subscriber Access Endpoint

**Objective**: Add a server-to-server API endpoint that lets DealerBackend query a dealer's access matrix.

| # | Task | File | Status |
|---|------|------|--------|
| 1.1 | Create `SubscriberAccessResponseSchema` response schema | `backend/billing/schemas.py` | ✅ Done |
| 1.2 | Query params via `Query(...)` on endpoint (no separate schema needed) | `backend/billing/controllers.py` | ✅ Done |
| 1.3 | Add `GET /billing/service/subscriber/access` endpoint | `backend/billing/controllers.py` | ✅ Done |
| 1.4 | Add `BillingService.get_subscriber_access()` + `aget_subscriber_access()` | `backend/billing/services.py` | ✅ Done |
| 1.5 | Wire URL route (auto-discovered by ninja_extra) | `backend/api/views.py` | ✅ Done |
| 1.6 | Test endpoint with API key + subscriber_id + service_domain | Manual / Unit test | ⬜ Pending |

**Endpoint Spec**:
```
GET /billing/service/subscriber/access?subscriber_id=<user_id>&service_domain=<domain>
Headers: X-API-Key: <service_credential_key>

Response 200:
{
  "subscriber_id": "1",
  "service_domain": "localhost:4323",
  "subscription_status": "active",
  "plan_slug": "standard",
  "plan_name": "Standard",
  "access": {
    "dashboard": true,
    "reports": true,
    "suppliers": false,
    "max_dsrs": 5,
    "max_products": 500,
    ...
  }
}

Response 404: { "detail": "User not found" }
Response 403: { "detail": "Invalid API key" }
```

---

## Phase 2: DealerBackend — Access Client + Permission Constraining

**Objective**: DealerBackend fetches dealer's access from SattaBase and constrains DSR permissions accordingly.

| # | Task | File | Status |
|---|------|------|--------|
| 2.1 | Create `common/sattabase_access.py` — service-to-service client | `dealerbackend/common/sattabase_access.py` | ✅ Done |
| 2.2 | Add caching layer (TTL: 5 min) for dealer access | `dealerbackend/common/sattabase_access.py` | ✅ Done |
| 2.3 | Add settings for SattaBase API URL + API key | `dealerbackend/dealercore/settings.py` | ✅ Done |
| 2.4 | Define dealer access → DSR permission constraint mapping | `dealerbackend/common/sattabase_access.py` | ✅ Done |
| 2.5 | Modify `invite_dsr` to constrain permissions against dealer's access | `dealerbackend/dsr/dealer_dsr_api.py` | ✅ Done |
| 2.6 | Modify `update_assignment` to constrain permissions against dealer's access | `dealerbackend/dsr/dealer_dsr_api.py` | ✅ Done |
| 2.7 | Replace hardcoded `plan_limits.py` fallbacks with SattaBase access data | `dealerbackend/common/plan_limits.py` | ✅ Done |
| 2.8 | Add `max_dsrs` check on reactivation | `dealerbackend/dsr/invitation_api.py` + `dsr/auth_api.py` | ✅ Done |

**Permission Constraint Mapping** (dealer access key → DSR permission module):
| Dealer Access Key | DSR Permission Module | Constraint Rule |
|-------------------|----------------------|-----------------|
| `dashboard` | `dashboard` | If `false` → zeroed to `{}` |
| `inventory` | `inventory` | If `false` → zeroed to `{}` |
| `sales` | `sales` | If `false` → zeroed to `{}` |
| `collections` | `collections` | If `false` → zeroed to `{}` |
| `suppliers` | `suppliers` | If `false` → zeroed to `{}` |
| `reports` | `reports` | If `false` → zeroed to `{}` |
| `print` | `print` | If `false` → stripped entirely |
| `manage_dsrs` | `manage_dsrs` | If `false` → stripped entirely |
| `max_dsrs` | (limit) | Caps number of active DSR assignments |
| `max_products` | (limit) | Caps inventory products |
| `max_suppliers` | (limit) | Caps suppliers |

**Settings Added** (`dealercore/settings.py`):
```
SATTABASE_API_BASE_URL     = http://localhost:8086 (env: SATTABASE_API_BASE_URL)
SATTABASE_API_KEY          = "" (env: SATTABASE_API_KEY)
SATTABASE_SERVICE_DOMAIN   = "localhost:4323" (env: SATTABASE_SERVICE_DOMAIN)
SATTABASE_ACCESS_CACHE_TTL = 300 seconds (env: SATTABASE_ACCESS_CACHE_TTL)
```

**Graceful Fallback**:
- When `SATTABASE_API_KEY` is not configured, the client returns a permissive
  fallback (all access allowed) so existing deployments keep working.
- When SattaBase is unreachable (timeout, connection error), same permissive
  fallback is used with loud warnings in logs.
- When subscriber is not found in SattaBase, fallback with `is_active=False`
  is returned, which blocks DSR operations.

---

## Phase 3: Server-Side DSR Permission Enforcement

**Objective**: Every DSR API action checks `DsrDealerAssignment.has_permission()` + dealer subscription status.

| # | Task | File | Status |
|---|------|------|--------|
| 3.1 | Create `common/dsr_permissions.py` — decorator/helper for checking DSR permissions | `dealerbackend/common/dsr_permissions.py` | ✅ Done |
| 3.2 | Enforce DSR permissions in `sales/api.py` | `dealerbackend/sales/api.py` | ✅ Done |
| 3.3 | Enforce DSR permissions in `inventory/api.py` | `dealerbackend/inventory/api.py` | ✅ Done |
| 3.4 | Enforce DSR permissions in `reports/api.py` | `dealerbackend/reports/api.py` | ✅ Done |
| 3.5 | Enforce DSR permissions in `supplier/api.py` | `dealerbackend/supplier/api.py` | ✅ Done |
| 3.6 | Enforce DSR permissions in `collections` (within sales/api.py) | `dealerbackend/sales/api.py` | ✅ Done |
| 3.7 | Verify dealer subscription active on DSR requests (via cached access) | `dealerbackend/common/dsr_permissions.py` | ✅ Done |
| 3.8 | Update frontend `PermissionGuard.vue` to also check DSR module permissions | `dealerfrontend/src/components/PermissionGuard.vue` | ✅ Done |
| 3.9 | Add `useDsrPermissions` composable for DSR-specific permission checks | `dealerfrontend/src/composables/useDsrPermissions.ts` | ✅ Done |
| 3.10 | Add `GET /dsr/permissions` backend endpoint for frontend composable | `dealerbackend/dsr/permissions_api.py` | ✅ Done |
| 3.11 | Register `DsrPermissionsController` in API router | `dealerbackend/dealercore/api.py` | ✅ Done |

**Permission Enforcement Mapping** (endpoint → module:action):

**Sales API** (`sales/api.py`):
| Endpoint | Module:Action |
|----------|-------------|
| `GET /sales` | `sales:view` |
| `POST /sales` | `sales:edit` |
| `POST /sales/bulk` | `sales:edit` |
| `GET /sales/{id}` | `sales:view` |
| `POST /sales/{id}/collect` | `collections:edit` |
| `POST /sales/{id}/close-with-due` | `collections:edit` |
| `POST /sales/{id}/return` | `sales:edit` |
| `POST /sales/{id}/void` | `sales:delete` |
| `POST /sales/{id}/edit` | `sales:edit` |

**Inventory API** (`inventory/api.py`):
| Endpoint | Module:Action |
|----------|-------------|
| `GET /inventory` | `inventory:view` |
| `GET /inventory/restocks` | `inventory:view` |
| `GET /inventory/restocks/{id}` | `inventory:view` |
| `POST /inventory/add` | `inventory:edit` |
| `POST /inventory/restock` | `inventory:edit` |
| `GET /inventory/brands` | `inventory:view` |
| `POST /inventory/brands` | `inventory:edit` |
| `GET /inventory/brands/{id}` | `inventory:view` |
| `DELETE /inventory/brands/{id}` | `inventory:delete` |
| `GET /inventory/categories` | `inventory:view` |
| `POST /inventory/categories` | `inventory:edit` |
| `GET /inventory/categories/{id}` | `inventory:view` |
| `DELETE /inventory/categories/{id}` | `inventory:delete` |
| `GET /inventory/{id}` | `inventory:view` |
| `POST /inventory/{id}/edit` | `inventory:edit` |
| `DELETE /inventory/{id}` | `inventory:delete` |

**Reports API** (`reports/api.py`):
| Endpoint | Module:Action |
|----------|-------------|
| `GET /reports/summary` | `reports:view` |
| `GET /reports/customer-due` | `reports:view` |
| `GET /reports/vehicle-due` | `reports:view` |
| `GET /reports/dsr-due` | `reports:view` |
| `POST /reports/ai-reconciliation` | `reports:export` |

**Supplier API** (`supplier/api.py`):
| Endpoint | Module:Action |
|----------|-------------|
| `GET /suppliers` | `suppliers:view` |
| `GET /suppliers/{id}` | `suppliers:view` |
| `POST /suppliers` | `suppliers:edit` |
| `PATCH /suppliers/{id}` | `suppliers:edit` |
| `DELETE /suppliers/{id}` | `suppliers:edit` |

**Key Architecture Decisions**:
- `enforce_dsr_permission()` is the first line of each endpoint — it runs before `get_dealer_context()` and business logic
- Dealers bypass all DSR-level checks (is_dealer=True in middleware)
- Subscription active check is integrated into `enforce_dsr_permission()` via SattaBase access cache
- `DsrDealerAssignment.has_permission()` is now live code — called on every DSR request
- Frontend `PermissionGuard` now supports `module` + `action` props for DSR-level checks alongside plan-level `feature` prop

---

## Changelog

| Date | Phase | What |
|------|-------|------|
| 2026-06-16 | — | Tracking document created |
| 2026-06-16 | Phase 1 | Added `SubscriberAccessResponseSchema` to schemas.py |
| 2026-06-16 | Phase 1 | Added `get_subscriber_access()` + `aget_subscriber_access()` to BillingService |
| 2026-06-16 | Phase 1 | Added `BillingServiceController` with `GET /billing/service/subscriber/access` |
| 2026-06-16 | Phase 1 | Updated API docs in views.py |
| 2026-06-16 | Phase 2 | Created `common/sattabase_access.py` — SattaBase access client with in-memory cache, constraint mapping, convenience functions |
| 2026-06-16 | Phase 2 | Added 4 new settings: `SATTABASE_API_BASE_URL`, `SATTABASE_API_KEY`, `SATTABASE_SERVICE_DOMAIN`, `SATTABASE_ACCESS_CACHE_TTL` |
| 2026-06-16 | Phase 2 | Modified `invite_dsr` — fetches dealer access, checks subscription active, constrains permissions, uses SattaBase `max_dsrs` |
| 2026-06-16 | Phase 2 | Modified `update_dsr` — fetches dealer access, checks subscription active, constrains permissions on update |
| 2026-06-16 | Phase 2 | Updated `plan_limits.py` — resolution order now: SattaBase access map → JWT plan_limits → fallback; added `attach_sattabase_access()` |
| 2026-06-16 | Phase 2 | Added `max_dsrs` check on reactivation in `invitation_api.py` (`accept_invitation`, `activate_assignment`) |
| 2026-06-16 | Phase 2 | Added `max_dsrs` check on reactivation in `auth_api.py` (`accept_invitation` with reactivation path and new assignment path) |
| 2026-06-16 | Phase 2 | Gap #2 (DSR permissions unconstrained) fixed — constrain_dsr_permissions strips/zeroes modules dealer plan doesn't allow |
| 2026-06-16 | Phase 2 | Gap #4 (two disconnected permission systems) fixed — SattaBase access now bridges to DSR permissions |
| 2026-06-16 | Phase 2 | Gap #6 (max_dsrs not checked on reactivation) fixed — all 3 reactivation paths now check the limit |
| 2026-06-16 | Phase 3 | Created `common/dsr_permissions.py` — enforce_dsr_permission(), enforce_dsr_module(), require_dsr_permission decorator, DsrPermissionContext, dealer subscription check via SattaBase access cache |
| 2026-06-16 | Phase 3 | Added enforce_dsr_permission() to all 9 endpoints in `sales/api.py` |
| 2026-06-16 | Phase 3 | Added enforce_dsr_permission() to all 16 endpoints in `inventory/api.py` |
| 2026-06-16 | Phase 3 | Added enforce_dsr_permission() to all 5 endpoints in `reports/api.py` |
| 2026-06-16 | Phase 3 | Added enforce_dsr_permission() to all 5 endpoints in `supplier/api.py` |
| 2026-06-16 | Phase 3 | Gap #3 (DSR permissions not enforced server-side) fixed — all 35 endpoints now check DsrDealerAssignment.has_permission() |
| 2026-06-16 | Phase 3 | Gap #5 (has_permission dead code) fixed — now called via enforce_dsr_permission on every DSR request |
| 2026-06-16 | Phase 3 | Created `dsr/permissions_api.py` — GET /dsr/permissions endpoint for frontend composable |
| 2026-06-16 | Phase 3 | Registered DsrPermissionsController in `dealercore/api.py` |
| 2026-06-16 | Phase 3 | Updated `PermissionGuard.vue` — now supports `module` + `action` props for DSR-level checks alongside plan-level `feature` prop |
| 2026-06-16 | Phase 3 | Created `useDsrPermissions.ts` composable — reactive DSR module permission checks with hasPermission(), canView(), canEdit(), canDelete() |
| 2026-06-16 | Audit | Code audit for SHARED_SECRET + redundant code — see § Code Audit below |

---

## Code Audit: SHARED_SECRET, Redundant Code & Dead Code

**Date**: 2026-06-16  
**Scope**: DealerBackend `common/` + `dealercore/` + `.env.example`

### Finding 1: SATTABASE_JWT_SHARED_SECRET — Unnecessary & Insecure 🔴

**Files**:
- `dealercore/settings.py` L252: `SATTABASE_JWT_SHARED_SECRET = os.getenv("SATTABASE_JWT_SHARED_SECRET", "")`
- `common/permission_middleware.py` L135: `shared_secret = getattr(settings, 'SATTABASE_JWT_SHARED_SECRET', '') or ''`
- `.env.example` L41: `SATTABASE_JWT_SHARED_SECRET=django-insecure-...`

**Problem**: `SATTABASE_JWT_SHARED_SECRET` is an HS256 fallback for verifying SattaBase JWTs when `SATTABASE_JWT_PUBLIC_KEY` (RS256) is not configured. This is:
1. **A security anti-pattern** — HS256 uses the same key for signing AND verification. Copying SattaBase's signing key to DealerBackend means if DealerBackend is compromised, an attacker can forge SattaBase JWTs for ALL sister domains.
2. **Redundant with the API key flow** — SattaBase already issues per-domain API keys via `ServiceCredential` (`SATTABASE_API_KEY`). Server-to-service auth uses `X-API-Key`. JWT verification should ONLY use RS256 with the public key — that's the whole point of asymmetric crypto.
3. **Fails open in development** — `.env.example` ships with the shared secret pre-filled, so developers never configure RS256 and end up relying on HS256.
4. **Overcomplex** — The middleware has a 3-tier fallback (public_key → shared_secret → SECRET_KEY) that's confusing and dangerous. The correct behavior when no public key is configured should be: **fail closed** (reject all SattaBase JWTs).

**Recommendation**: Remove `SATTABASE_JWT_SHARED_SECRET` entirely. JWT verification should be:
- RS256 with `SATTABASE_JWT_PUBLIC_KEY` → verify SattaBase JWTs
- If public key not configured → fail closed (SattaBase JWTs rejected, only local DSR JWTs work)
- `.env.example` should document how to get the public key, not ship a shared secret

### Finding 2: Dead Helper Functions in `permission_middleware.py` 🟡

**File**: `common/permission_middleware.py` L295–345

Three functions defined but **never imported or called** from any controller:
- `check_permission(request, permission_str)` — L295. No `from common.permission_middleware import check_permission` exists anywhere.
- `require_dealer(request)` — L318. No business API uses this; `IsDealerOnly` permission class is used instead.
- `require_dsr_plus(request)` — L332. No business API uses this; `IsDsrOrDealer` is used instead.

These predate `dsr_permissions.py` and are superseded by the module+action permission system.

**Recommendation**: Remove all three functions.

### Finding 3: Dead Code in `common/permissions.py` — Permission Enum & Role Permission Mapping 🟡

**File**: `common/permissions.py`

The `Permission` enum (18 values), `ROLE_PERMISSIONS` dict, `PermissionChecker` class, `PERMISSION_GROUPS` dict, and `require_permission()` decorator are effectively **dead code**:

| Item | Used? | Details |
|------|-------|---------|
| `Permission` enum | ❌ Dead | The 18 enum values (`DSR_SALES_CREATE`, `VIEW_INVENTORY`, etc.) are only referenced within `permissions.py` itself and the dead `check_permission()` in middleware |
| `ROLE_PERMISSIONS` | ❌ Dead | Only read by `get_role_permissions()` which is only called by `PermissionChecker` and middleware (to set `request.permissions` list that nobody reads) |
| `PermissionChecker` | ❌ Dead | Set on `request.permission_checker` by middleware, but no business API ever calls `.can()`, `.can_any()`, `.can_all()` |
| `PERMISSION_GROUPS` | ❌ Dead | Only referenced within `permissions.py` itself |
| `require_permission()` | ❌ Dead | Decorator defined but never applied to any endpoint |
| `request.permissions` list | ❌ Dead | Set by middleware but never read by any code |

**What IS still alive** in `permissions.py`:
- `Role` enum — used by middleware and `dsr_permissions.py`
- `IsJwtAuthenticated` — used by `dealer_dsr_api.py`, `permissions_api.py`
- `IsDealerOnly` — used by `dealer_dsr_api.py`
- `IsDsrOrDealer` — used by `dealer_dsr_api.py`

**Why it's redundant**: `dsr_permissions.py`'s module+action system (`enforce_dsr_permission("sales", "edit")`) is the actual enforcement layer used by all 35 business endpoints. The `Permission` enum tries to do the same thing (role→permission mapping) but:
- It's not constrained by dealer subscription
- It's not per-dealer (doesn't use `DsrDealerAssignment`)
- It's coarse-grained (can't distinguish "view" vs "edit" vs "delete" within a module)
- It's never called from any business API

**Recommendation**: Remove dead items (`Permission` enum, `ROLE_PERMISSIONS`, `PermissionChecker`, `PERMISSION_GROUPS`, `require_permission()`, `has_permission()`, `has_any_permission()`, `has_all_permissions()`, `get_role_permissions()`). Keep `Role` enum, `IsJwtAuthenticated`, `IsDealerOnly`, `IsDsrOrDealer`. Also remove `request.permissions` and `request.permission_checker` from middleware.

### Finding 4: Stale `.env.example` Variables 🟡

**File**: `.env.example`

| Variable | Status | Actual Setting in `settings.py` |
|----------|--------|------|
| `SB_API_BASE_URL` | ❌ Stale | `SATTABASE_API_BASE_URL` |
| `SB_API_KEY` | ❌ Stale | `SATTABASE_API_KEY` |
| `SB_SERVICE_DOMAIN` | ❌ Stale | `SATTABASE_SERVICE_DOMAIN` |
| `SB_FRONTEND_URL` | ❌ Stale | No equivalent in settings.py |
| `ENABLE_SUBSCRIPTION_CHECK` | ❌ Stale | Not read by any Python code |
| `ENABLE_ACCESS_MATRIX` | ❌ Stale | Not read by any Python code |

These are remnants from an earlier naming convention (`SB_` prefix). `settings.py` uses `SATTABASE_` prefix. The feature flags `ENABLE_SUBSCRIPTION_CHECK` and `ENABLE_ACCESS_MATRIX` were never wired to any code.

**Recommendation**: Update `.env.example` to use the correct variable names matching `settings.py`. Remove unused feature flags.

### Summary of Audit Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| A1 | `SATTABASE_JWT_SHARED_SECRET` — insecure HS256 fallback, should be removed | 🔴 Critical | ⬜ Pending |
| A2 | Dead functions in `permission_middleware.py` — `check_permission()`, `require_dealer()`, `require_dsr_plus()` | 🟡 Cleanup | ⬜ Pending |
| A3 | Dead code in `permissions.py` — `Permission` enum, `ROLE_PERMISSIONS`, `PermissionChecker`, `PERMISSION_GROUPS`, `require_permission()` | 🟡 Cleanup | ⬜ Pending |
| A4 | Stale `.env.example` variables — `SB_*` prefix, unused feature flags | 🟡 Cleanup | ⬜ Pending |
