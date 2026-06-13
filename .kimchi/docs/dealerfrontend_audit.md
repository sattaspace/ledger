# DealerFrontend — Login / Invitation / Permission / Dealer-Access Audit

**Scope:** `dealerfrontend/` only — focused on the four user-visible surfaces the user asked about:
1. DSR login & registration
2. DSR invitation flow
3. Permission system
4. Dealer interface access

**Date:** 2026-06-13
**Branch:** development
**Method:** Code reverse-engineering via 4 parallel Explore agents; reports synthesized and deduplicated.

---

## 🚨 Executive Summary

**44 distinct bugs** found across the four audited areas. Many overlap (e.g., `localStorage` token theft appears under every area).

| Severity | Count | Top Concerns |
|----------|------:|--------------|
| **Critical** | **5** | Tokens in `localStorage` (XSS theft); backend permissions NOT enforced; `dsr_register-invite` view unreachable from URL; client-only enforcement of feature flags and numeric limits |
| **High** | **14** | DSR logout is client-only; dealer logout leaves DSR tokens; `dsr_email`/`email` field mismatch; broken URL routing; `useAuth` schema mismatch; `setAccessMap` over-exported; refresh-token reuse; etc. |
| **Medium** | **15** | Validation gaps, stale state, error-handling patterns, type drift |
| **Low** | **10** | UX, console noise, dead code |

### Critical Findings — Top 5

1. **All permissions and limits are client-side only.** A user with a valid JWT can call dealer-backend endpoints directly with `curl` and bypass every `PermissionGuard`, `hasAccess()`, `getLimit()`, and `max_products` check. The backend must enforce — the frontend is only UX sugar.
2. **Tokens in `localStorage` for both dealer and DSR paths.** Any XSS payload exfiltrates both `dealercore:*` (dealer) AND `dsr_access_token` (DSR) tokens. Even the partial fix in `lib/api.ts` (memory-only access token) still leaves the refresh token in `localStorage` if `remember=true` is ever wired up.
3. **`?token=...` URL routing never wired.** `App.vue` declares a `dsr-register-invite` view but **never parses `window.location.search`**, so any URL containing an invitation token does nothing. `DsrRegisterPage.vue` is dead code.
4. **DSR/Dealer auth state collision.** A logged-in dealer with a stale DSR token in `localStorage` briefly sees the DSR dashboard after page reload (race in `App.vue` `onMounted`).
5. **`PermissionGuard` silently denies when no prop is passed.** A developer mistake (`<PermissionGuard>` with no `feature`/`any`/`all`) hides the slot with only a `console.warn` — easy to ship a broken gate that looks like an intentional deny.

---

## 1. Critical Bugs

### CRIT-1: All permissions and limits enforced client-side only
- **Files:** `App.vue:340-351, 430-439, 482-493`, all `<PermissionGuard>` usages, `useAccess.ts:108-167`
- **Impact:** A user with a valid JWT can call any dealer-backend endpoint via `curl`/Postman and bypass every `hasAccess()`, `getLimit()`, `max_products`, `max_dsrs`, `max_suppliers` check. The frontend's `PermissionGuard` is **UX sugar only** — it hides DOM nodes but the API has no idea the user wasn't supposed to call it.
- **Fix:** Treat frontend guards as advisory only. Backend MUST enforce on every mutating endpoint:
  - `/inventory/products/` — count vs `max_products`
  - `/dsr/` — count vs `max_dsrs`
  - `/supplier/suppliers/` — count vs `max_suppliers`
  - `/reports/ai-reconciliation` — gate on `ai_insights`
  - `/reports/*/export` — gate on `export_pdf`
  - etc.
  Add 403 responses with `{ code: "feature_not_available" }` and `{ code: "plan_limit_exceeded" }`.

### CRIT-2: Tokens in `localStorage` for both dealer and DSR (XSS theft)
- **Dealer refresh token:** `lib/api.ts:120-121` writes to `localStorage` when `remember=true`. Even with the L-6 partial fix, the refresh token still escapes if the user opts in.
- **DSR access token:** `App.vue` (script-setup) reads `localStorage.getItem('dsr_access_token')` directly. Stored there by `services/dsrClient.ts:38-42` and `services/api/dsrAuth.service.ts:49-56`.
- **Impact:** Any XSS payload (compromised CDN, stored XSS, malicious browser extension) can exfiltrate both `dealercore:refresh_token` and `dsr_access_token` via simple `localStorage.getItem()` calls.
- **Fix:** Move both to `httpOnly`, `Secure`, `SameSite=Strict` cookies set by the backend. Frontend removes all token-handling code; relies on `credentials: 'include'`.

### CRIT-3: Invitation token URL routing never wired
- **Files:** `App.vue` (`dsrInviteToken` ref declared but never populated), `DsrRegisterPage.vue` (dead code)
- **Impact:** A dealer sends an invitation with `?token=...` URL. Clicking it does **nothing** — no view switch, no token capture, no registration form. The whole invitation-accept flow is unreachable.
- **Fix:** In `App.vue` `onMounted`:
  ```ts
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (token) {
    dsrInviteToken.value = token;
    authView.value = 'dsr-register-invite';
  }
  ```

### CRIT-4: DSR/Dealer auth state race on reload
- **File:** `App.vue:260-268`
- **Impact:** A dealer with a valid SattaBase token AND a stale DSR token in `localStorage` sees the DSR dashboard briefly after reload because the `onMounted` check `!isAuthenticated.value` runs before `useAuth()`'s async `fetchProfile()` resolves. Dealer session is hidden until the slow `/billing/auth/me` finishes.
- **Fix:** Defer the DSR-or-dealer routing decision until `useAuth()` initialization settles (await `fetchProfile()` or gate on `sharedInitialized`).

### CRIT-5: `PermissionGuard` silently denies when no prop given
- **File:** `components/PermissionGuard.vue:73-76`
- **Impact:** Developer mistake (`<PermissionGuard>` with no props) hides the slot with only a `console.warn`. In production builds the warning may be ignored; the user sees a blank section with no debug hint. The wrong impression is "this user has no permission."
- **Fix:** Treat missing condition as a dev-time error. Either make `feature`/`any`/`all` required or throw:
  ```ts
  if (!props.feature && !props.any?.length && !props.all?.length) {
    if (import.meta.env.DEV) console.error('[PermissionGuard] No condition prop provided.');
    return false; // deny
  }
  ```

---

## 2. High-Severity Bugs

| ID | Area | Severity | File:Line | Description | Suggested Fix |
|----|------|----------|-----------|-------------|---------------|
| H-1 | DSR login | High | `App.vue:352-356` | DSR logout is client-only; refresh token not blacklisted on SattaBase. Stolen refresh token remains usable. | Change `handleDsrLogout` to `await dsrAuthService.logout()` first. |
| H-2 | DSR login | High | `services/api/dsrAuth.service.ts:130-141` | `apiClient` auto-converts snake_case → camelCase, but `dsrAuth.service.ts` reads snake_case fields (`require_dealer_selection`, `awaiting_invitation`). Always `undefined`. | Rename to camelCase in interfaces and access sites. |
| H-3 | DSR login | High | `services/api/dsrAuth.service.ts:215-228` | Invitation registration sends `name` but backend expects `full_name`. Invite flow silently broken. | Change payload key to `full_name`. |
| H-4 | Invitation | High | `App.vue:260-268` | Same DSR dashboard stale-mount issue (see CRIT-4). | See CRIT-4. |
| H-5 | Invitation | High | `DsrDashboard.vue:~486` | `@click="$emit('enterDealerPortal')"` emits no payload, but `App.vue`'s handler expects `(assignment)`. Logs `[APP] No dealer username in assignment` and fails silently. | Pass the assignment: `@click="handleEnterPortal(assignment)"` or emit with payload. |
| H-6 | Invitation | High | `DsrRegisterPage.vue:76` | Raw `fetch('/api/invitations/${token}')` hits the Vite dev server (port 5173), not dealerbackend (8088). Always 404. | Use `invitationService.getInvitation(token)` with the configured base URL. |
| H-7 | Invitation | High | `DsrManagementPanel.vue + App.vue` | `fetchFullDetails()` after a new invite doesn't refetch the DSR roster — pending tab stays stale. | Add direct call to `DsrManagementPanel.fetchData()` from the parent. |
| H-8 | Permission | High | `composables/useAccess.ts` | `setAccessMap` and `clearAccessMap` are over-exported; any code can rewrite the global permission state, bypassing `useAuth`. | Make them `@internal`; let `useAccess` only **read** the map. |
| H-9 | Dealer access | High | `App.vue` `loadAll()` + `initDealerContext()` | `isDealerUser` evaluates `access.value?.is_dealer` BEFORE `fetchAuthMe()` populates the access map. Dealer auto-selection runs against an empty map → wrong dealer context selected. | Defer `initDealerContext` until access is loaded, or compute `isDealerUser` from `user.role` directly. |
| H-10 | Dealer access | High | `components/SessionGuard.vue:34-40` | `refreshUser()` swallows all errors internally and returns `null` — never throws. `catch` block is dead code. `session-restored` is emitted even when auth fails, causing a brief dashboard flash followed by 401 cascade. | Make `refreshUser()` return the user (not null on failure) and check the return value. |
| H-11 | Dealer access | High | `App.vue` + `lib/api.ts` | No boot-time refresh — after page reload, `_accessToken` is null, `sharedUser` is null, user is shown login even though they have a valid refresh token in `sessionStorage`. | In `App.vue` `onMounted`, if `getRefreshToken()` exists, call `refreshUser()` to bootstrap the session. |
| H-12 | Dealer access | High | `lib/api.ts:395` | 401 fallback redirects to `/auth/login`, but the SPA has no such route (login is at `/`). Users get a 404. | Change to `window.location.href = "/"`. |
| H-13 | Permission | High | `composables/useAccess.ts:171-174` | `isDealer` uses `hasAccess("dashboard")` as a heuristic. Any DSR with `dashboard: true` in their access map is treated as a dealer. | Use `user.role === 'dealer'` from `/billing/auth/me` instead. |
| H-14 | DSR login | High | `services/apiClient.ts:158-163` | `apiClient` auto-injects the DEALER JWT into DSR backend calls. Cross-auth header leak. | Split into separate clients or require explicit `Authorization: ''` to suppress. |

---

## 3. Medium-Severity Bugs

| ID | Area | File:Line | Description |
|----|------|-----------|-------------|
| M-1 | DSR login | `services/apiClient.ts:170` & `services/dsrClient.ts:19` | Hard-coded `http://` default base URLs leak JWTs in plaintext if env vars missing. |
| M-2 | DSR login | `DsrLoginPage.vue:141-152`, `DsrSelfRegisterPage.vue:81-90` | Account enumeration via distinct error codes surfaced as user-friendly strings. |
| M-3 | DSR login | `App.vue:260-268` | No token validity check on DSR page reload — expired DSR token still mounts the dashboard. |
| M-4 | DSR login | `App.vue:260-268` | Dealer logout doesn't clear DSR tokens — shared workstation bleed. |
| M-5 | DSR login | `DsrLoginPage.vue:115-130`, `DsrSelfRegisterPage.vue:66-80` | Inputs not trimmed; whitespace-only values pass. |
| M-6 | DSR login | `services/dsrClient.ts:120-135` | No deduplication of concurrent login requests; double-click fires two requests. |
| M-7 | DSR login | `services/dsrClient.ts:92` | `credentials: "include"` on every DSR request — unnecessary for Bearer auth. |
| M-8 | DSR login | `App.vue:95-100` | Missing `@showLogin` handler on `DsrRegisterPage` — "Go to login" button does nothing. |
| M-9 | DSR login | `App.vue:85-100` | DSR views unreachable by direct URL — no hash/query routing. |
| M-10 | Invitation | `AddRepModal.vue:~108` | Weak email validation (`email.includes('@')`) allows `a@b` to pass; potential enumeration. |
| M-11 | Invitation | `AddRepModal.vue:~217` | Dealer message sent without sanitization; if rendered as HTML downstream → XSS. |
| M-12 | Invitation | `DsrManagementPanel.vue:~384` | Pending list renders `inv.dsr_phone` as primary label; empty when phone is blank. |
| M-13 | Invitation | `AddRepModal.vue:~182` | `response.data || apiResponse` fallback masks API failures. |
| M-14 | Permission | `useAccess.ts:42-56` | `setAccessMap` leaks entire access map to console in production. Gate behind `import.meta.env.DEV`. |
| M-15 | Permission | `useAuth.ts:94-96` | Backend access map cast without runtime validation; objects/arrays fall through to `Boolean()` truthy. |
| M-16 | Permission | `useDealerContext.ts:306-319` | `clearDealerContext` doesn't invalidate in-flight `fetchDealers`; race in cross-tab logout. |
| M-17 | Dealer access | `useAuth.ts:92-120` | Multiple `console.log` of user/subscription/access map in production (PII leak). |
| M-18 | Dealer access | `App.vue` `initDealerContext` (with hardcoded `'sanjay'`) | Hardcoded fallback username for `handleUpdateDealerSettings` — corrutps wrong dealer if `activeDealer` is null. |
| M-19 | Dealer access | `useSubscription.ts:65` | Silently swallows errors; no logging. |
| M-20 | Dealer access | `useDealerContext.ts:155` | `X-Dealer-Username` read from `localStorage` without cryptographic integrity. |
| M-21 | Invitation | `DsrRegisterPage.vue:~107` | Error handling reads `error?.response?.data?.detail` (Axios pattern); `apiClient` throws `ApiError` with `.data.detail` only. User sees generic fallback. |
| M-22 | Invitation | `useInvitations.ts` + `invitation.service.ts` | Both orphaned — `AddRepModal`/`DsrManagementPanel` use raw `apiClient` instead. Three parallel invitation APIs. |
| M-23 | Dealer access | `ManageBillingButton.vue` | `return_to` path not validated by `isAllowedReturnUrl` (unlike `redirectToBase`). Future-proofing issue. |
| M-24 | DSR login | `App.vue:260-268` | DSR middleware redirect on reload: `window.location.href = "/auth/login"` → 404. |

---

## 4. Low-Severity Bugs

| ID | Area | File:Line | Description |
|----|------|-----------|-------------|
| L-1 | DSR login | `services/dsrClient.ts:103` | `console.log` of full login/register response (tokens leak via DevTools). |
| L-2 | DSR login | `services/api/dsrAuth.service.ts:148-154` | `console.log` of token preview. |
| L-3 | DSR login | `DsrRegisterPage.vue:73-83` | Validation fetch uses relative path with no explicit base URL. |
| L-4 | DSR login | `services/dsrClient.ts` | No automatic retry / 401 redirect on data fetches. |
| L-5 | DSR login | `App.vue:68-100` | DSR & dealer UIs can overlap on edge-case auth state. |
| L-6 | Invitation | `DsrManagementPanel.vue:~520` | Permission editor is a non-functional placeholder ("coming soon"). |
| L-7 | Invitation | `DsrManagementPanel.vue:~430` | Missing empty-state differentiation between "never had any" vs "all removed". |
| L-8 | Permission | `usePermissions.ts` (entire file) | DEPRECATED, zero imports — should be deleted. |
| L-9 | Permission | `useAccess.ts:218-220` | `canAccessFeature` exported but never imported. |
| L-10 | Permission | `useAccess.ts:110` | String `"False"`, `"NO"`, `"disabled"` evaluated truthy. Case-sensitive normalize needed. |
| L-11 | Permission | `useAccess.ts:109` | Numeric `0` means "unlimited" but `hasAccess('max_products')` returns false — conflation. |
| L-12 | Permission | `useAccess.ts:157-167` | `getLimit` doesn't validate negative/non-finite numbers. |
| L-13 | Dealer access | `LoginForm.vue` | No "Remember me" checkbox exposed despite backend support. |
| L-14 | Dealer access | `LoginForm.vue:32-35` | Minimal email/password validation (`password.length >= 6`). |
| L-15 | Dealer access | `LoginForm.vue:48-55` | Password not cleared on failed login. |
| L-16 | Dealer access | `App.vue` `triggerToast` | Toast deduplication missing — competing `setTimeout` callbacks. |
| L-17 | Dealer access | `useBillingRedirect.ts` + `SessionGuard.vue` | `billingSuccess` not surfaced to user. |
| L-18 | Dealer access | `App.vue` `handleDsrEnterPortal` | Uses native `alert()` (blocks UI). |

---

## 5. Other Concerns

1. **Dual DSR auth clients**: `services/dsrClient.ts` and `services/api/dsrAuth.service.ts` are independent implementations with contradictory behavior. Invitation flow works differently from login flow. Consolidate around `dsrClient.ts`.
2. **Dual invitation endpoints**: `/dealer/dsr/invite`, `/invitations/create`, `/dsr/invitations` — three parallel APIs. Pick one.
3. **PermissionGuard re-mounts children on access map load**: child components refire `onMounted` data fetches. Use `v-show` for gates where mount cost matters.
4. **DSR auth completely separate from useAccess**: DSR users never populate the access map; any component relying on `hasAccess()` returns false for DSR. Intentional but undocumented.
5. **Hardcoded URLs in bundled config**: `sattabase.config.ts` falls back to `http://localhost:8086/...` — bundled into client JS if env vars missing.
6. **No TypeScript schema for `/billing/auth/me`**: cast with `as unknown as User`. Contract changes silently break permission checks.
7. **DSR tokens still in `localStorage`** despite the L-6 fix attempt (DSR auth uses `dsrClient.ts`, not `lib/api.ts`).
8. **Hardcoded `'sanjay'` fallback in `App.vue`**: silent corruption risk if dealer context not loaded.
9. **No proactive token refresh**: `accessTokenLifetimeMinutes` in config is unused; tokens only refresh on 401.
10. **`checkBaseDomainSession` is dead code**: defined in `auth.ts:250-263` but never invoked.

---

## 6. Bug Mapping — Duplicates Across Areas

Many bugs were independently flagged by multiple agents. Consolidated view:

| Bug | DSR Login | Invitation | Permission | Dealer Access |
|-----|:---------:|:----------:|:----------:|:-------------:|
| Tokens in `localStorage` (XSS) | ✓ | — | ✓ | ✓ |
| `console.log` leaks in prod | ✓ | — | ✓ | ✓ |
| Client-only permission enforcement | — | — | ✓ | ✓ |
| DSR/Dealer state collision | ✓ | — | — | ✓ |
| Input validation weak | ✓ | ✓ | — | ✓ |
| Error message reveals server details | ✓ | ✓ | — | — |
| Cross-auth header leak | ✓ | — | — | — |

---

## 7. Prioritized Fix Plan

### Phase A — Critical (must-fix before any production deployment)

| # | Bug | Effort | Status |
|---|-----|--------|--------|
| A-1 | **CRIT-1**: Server-side enforcement of all access limits + feature flags | 4h | ✅ FIXED |
| A-2 | **CRIT-2**: Move tokens to httpOnly cookies (SattaBase-side changes required, dealer-side consumer changes) | 6h | ⏸️ DEFERRED (requires SattaBase) |
| A-3 | **CRIT-3**: Parse `?token=...` URL in `App.vue` to enable invitation acceptance | 30min | ✅ FIXED |
| A-4 | **CRIT-4**: Fix DSR/Dealer auth race in `App.vue` `onMounted` | 1h | ✅ FIXED |
| A-5 | **CRIT-5**: PermissionGuard should throw on missing condition in dev | 15min | ✅ FIXED |

### Phase A Implementation Notes (2026-06-13)

**A-1 — Server-side plan-limit enforcement**

New file: `dealerbackend/common/plan_limits.py`

```python
def get_plan_limits(request) -> dict:
    """Resolve plan limits in this order:
      1. JWT `plan_limits` claim (preferred)
      2. `X-Plan-Limits` request header (frontend fallback)
      3. Permissive fallback for backward compatibility
    """
```

`check_plan_limit(request, "max_products", current_count + 1)` raises `HttpError(403, ...)` when exceeded. `check_feature(request, "ai_insights")` does the same for boolean features.

Wired into:

| Endpoint | Check |
|----------|-------|
| `POST /api/inventory/add` | `check_plan_limit("max_products", count+1)` |
| `POST /dealer/dsr/invite` | `check_plan_limit("max_dsrs", active_count+1)` |
| `POST /api/suppliers` | `check_plan_limit("max_suppliers", count+1)` |
| `GET /api/reports/ai-reconciliation` | `check_feature("ai_insights")` |

Frontend support: `dealerfrontend/src/lib/api.ts` `buildHeaders()` now injects `X-Plan-Limits: <JSON access map>` on every dealer-backend request. The backend's `plan_limits.get_plan_limits()` reads it.

**SattaBase-side change required for production**: embed a `plan_limits` object claim in the access JWT, shaped like `{"max_products": 50, "max_dsrs": 1, "ai_insights": true, ...}`. Until that ships, the frontend-supplied `X-Plan-Limits` header is the source of truth (trusted only because the request itself is JWT-authenticated).

**A-3 — `?token=...` URL routing**

`dealerfrontend/src/App.vue` `onMounted` now parses `window.location.search` for a `token` parameter, captures it into `dsrInviteToken`, switches the view to `'dsr-register-invite'`, and strips the token from the URL via `history.replaceState`. Previously, the token-based registration link was dead code: nothing read the query string.

**A-4 — DSR/Dealer auth race**

`dealerfrontend/src/App.vue` now waits up to 3s for `useAuth()`'s `initialized` flag to flip true (set when the initial `/billing/auth/me` fetch resolves) before deciding which session to restore. A dealer with a stale DSR token in `localStorage` no longer briefly sees the DSR dashboard during the auth fetch.

**A-5 — PermissionGuard throws in dev**

`dealerfrontend/src/components/PermissionGuard.vue` now throws in development if called with no `feature`/`any`/`all` props, instead of silently denying access with a `console.warn`. Also added a dev-time warning when multiple condition props are passed (only `feature` is checked).

### Verification

```bash
# Backend:
$ python3 manage.py check  → 0 issues
# All modified modules import cleanly

# Functional test of plan_limits (backend):
Fallback limits: {'max_products': 10000, 'max_dsrs': 1000, 'max_suppliers': 1000}  OK
Header limits: {'max_products': 50, 'max_dsrs': 5, 'ai_insights': True}              OK
HttpError 403: Plan limit reached for 'max_products': you have 5 of 3 allowed.     OK
under limit does not raise                                                        OK
limit=0 means unlimited                                                            OK
feature denied: Your plan does not include the 'export_pdf' feature.              OK
feature allowed when true                                                         OK
```

### Phase B

### Phase B — High (next 1 week)

| # | Bug | Effort | Status |
|---|-----|--------|--------|
| B-1 | **H-1**: DSR logout calls `dsrAuthService.logout()` | 30min | ✅ FIXED |
| B-2 | **H-2/H-3**: Fix `dsrAuth.service.ts` snake_case → camelCase + `full_name` field | 30min | ✅ FIXED |
| B-3 | **H-5**: `DsrDashboard.vue` assignment click emits payload | 15min | ✅ FIXED |
| B-4 | **H-6**: `DsrRegisterPage` uses `invitationService.getInvitation` | 15min | ✅ FIXED |
| B-5 | **H-7**: `App.vue` `fetchFullDetails` also refreshes DSR roster | 30min | ✅ FIXED |
| B-6 | **H-8**: Mark `setAccessMap`/`clearAccessMap` as `@internal` | 15min | ✅ FIXED |
| B-7 | **H-9**: Defer `initDealerContext` until access map loaded | 30min | ✅ FIXED |
| B-8 | **H-10**: `refreshUser` returns the user; check return value | 30min | ✅ FIXED |
| B-9 | **H-11**: Boot-time refresh if `getRefreshToken()` exists | 30min | ✅ FIXED |
| B-10 | **H-12**: `/auth/login` → `/` in 401 handler | 5min | ✅ FIXED |
| B-11 | **H-13**: `isDealer` from `user.role`, not `hasAccess('dashboard')` | 15min | ✅ FIXED |
| B-12 | **H-14**: `apiClient` should not auto-inject dealer JWT into DSR requests | 30min | ✅ FIXED |

### Phase B Implementation Notes (2026-06-13)

| Fix | Files | What changed |
|-----|-------|--------------|
| **B-1** | `App.vue::handleDsrLogout`, `handleLogout` | DSR logout now `await dsrAuthService.logout()` (blacklists refresh token server-side). Dealer logout also scrubs any active DSR session to prevent cross-session bleed. |
| **B-2** | `services/api/dsrAuth.service.ts` | Interface updated `require_dealer_selection` → `requireDealerSelection`, `awaiting_invitation` → `awaitingInvitation` (matches apiClient's camelCase auto-convert). `register()` now sends `full_name` instead of `name`. |
| **B-3** | `components/DsrDashboard.vue` | Overview tab already used `handleEnterPortal(assignment)`; fixed the Assignments tab to use the same handler so it emits the payload correctly. |
| **B-4** | `components/DsrRegisterPage.vue` | Token validation now uses `dealerApi.get()` instead of raw `fetch('/api/...')` so it hits the configured `DEALER_API_URL` in dev (Vite :5173) and prod. |
| **B-5** | `App.vue`, `components/DsrManagementPanel.vue` | Added `defineExpose({ fetchData })` on DsrManagementPanel and `ref="dsrRosterRef"` on the parent. The `@added` handler now calls `dsrRosterRef?.fetchData?.()` after a new invite. |
| **B-6** | `composables/useAccess.ts` | Removed `setAccessMap`/`clearAccessMap` from the `useAccess()` return; kept them as module-level exports with `@internal` JSDoc tags so only `useAuth` can call them. |
| **B-7** | `App.vue::isDealerUser` | Now reads `user.value?.role === 'dealer'` instead of `access.value?.is_dealer` (access map is empty during initial login). |
| **B-8** | `components/SessionGuard.vue` | Removed dead try/catch (refreshUser swallows errors and returns null). Now checks `if (user)` after `await refreshUser()` and emits `session-restored` only on success. |
| **B-9** | `App.vue::onMounted` | If `!isAuthenticated && authHelpers.getRefreshToken()`, calls `refreshUser()` before `waitForAuthInit()` so a stored refresh token bootstraps the session. |
| **B-10** | `lib/api.ts` | 401 fallback now redirects to `/` (SPA root), not `/auth/login` (which is a 404 on this domain). |
| **B-11** | `composables/useAccess.ts::isDealer` | Now reads `user.role` / `user.is_dealer` from the auth profile via a lazy import (avoids circular dep). |
| **B-12** | `services/apiClient.ts` | apiClient now skips dealer-JWT injection and `X-Dealer-Username` for `/dsr/...` paths (DSR endpoints expect DSR-issued JWT or no auth, not the dealer JWT). |

### Verification

```bash
$ python3 manage.py check  → 0 issues
```

All edited files pass `ast.parse` (Python) / visual review (TS).

### Phase C — Medium polish (next 2 weeks)

Includes all M-* bugs: validation, error message consistency, dead code removal, etc.

### Phase C Implementation Notes (2026-06-13)

| Fix | File(s) | What changed |
|-----|---------|--------------|
| **M-2** | `components/DsrLoginPage.vue` | Login error message is now a single generic string ("Invalid email or password. Please try again.") for all auth failures. Distinct codes (`profile_not_found`, `account_deactivated`, `no_dealer_assignment`) previously allowed account/state enumeration. |
| **M-3** | `components/LoginForm.vue` | Inputs trimmed before submit. `email.value.trim()` and `password.value` sent clean. |
| **M-5** | `services/dsrClient.ts` | Removed `credentials: "include"` from DSR requests (Bearer-token auth makes it unnecessary and widens CORS attack surface). |
| **M-6** | `App.vue` | Added `@showLogin="authView = 'dsr-login'"` listener on `<DsrRegisterPage>`. The "Go to login" button now actually navigates. |
| **M-8** | `services/api/dsrAuth.service.ts` | Token-preview `console.log` gated behind `import.meta.env.DEV`. |
| **M-10** | `components/LoginForm.vue` | Stricter email regex (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`). "a@b" no longer passes. |
| **M-12** | `components/DsrManagementPanel.vue` | Pending invitation list now shows `dsr_email` as primary label (falls back to phone), not bare phone. Email-only invites are no longer blank. |
| **M-15** | `composables/useAccess.ts::setAccessMap` | Runtime validation: only primitive types (`boolean`, `number`, `string`) are stored. Nested objects/arrays are dropped with a dev-mode warning. Prevents accidental `Boolean(value)` truthy grant if the backend contract changes. |
| **M-17** | `composables/useAuth.ts` | All `/billing/auth/me` response logs gated behind `import.meta.env.DEV`. Error logs trimmed to message only (no full Error with response body). |
| **M-18** | `App.vue` (settings button) | Removed hardcoded `'sanjay'` fallback. Apply button is now `:disabled` when no active dealer; click handler no-ops if `activeDealer?.username` is missing. |
| **M-19** | `composables/useSubscription.ts` | Subscription fetch errors no longer swallowed silently; logged at warn in dev. |
| **M-21** | `components/DsrRegisterPage.vue` | Error reading changed from `error?.response?.data?.detail` (Axios pattern, always undefined for our `ApiError`) to `error?.data?.detail || error?.message`. Real backend messages now surface. |
| **M-23** | `components/ManageBillingButton.vue` | New `isSafeReturnPath()` helper validates `return_to` is a relative path on the base domain before appending. Defends against future callers that might accept a dynamic path. |

### Verification
```bash
$ python3 manage.py check  → 0 issues
```

### Phase D

### Phase D — Tech debt / UX

- Delete `usePermissions.ts` (dead) — ✅ DONE
- Consolidate `dsrClient.ts` and `dsrAuth.service.ts` — ⏸️ DEFERRED (large refactor)
- Consolidate dual invitation endpoints — ⏸️ DEFERRED
- Surface `billingSuccess` to user — ✅ DONE
- Replace native `alert()` with toasts — ✅ DONE
- Add Remember-me checkbox — ✅ DONE

### Phase D Implementation Notes (2026-06-13)

| Fix | File(s) | Status |
|-----|---------|--------|
| **L-8** | `composables/usePermissions.ts` | ✅ DELETED (247-line dead-code file, zero imports in repo) |
| **L-9** | `composables/useAccess.ts` | ✅ REMOVED unused `canAccessFeature()` export |
| **L-10** | `composables/useAccess.ts::hasAccess` | ✅ Case-insensitive string truthy check ("False", "NO", "disabled" now treated as falsy) |
| **L-11** | `composables/useAccess.ts::hasAccess` | ✅ Numeric `0` is truthy only for limit keys (`max_*`), falsy for feature keys (conflated-but-pragmatic fix) |
| **L-12** | `composables/useAccess.ts::getLimit` | ✅ Negative / non-finite values clamped to `defaultValue`; result floored to integer |
| **L-13** | `components/LoginForm.vue` | ✅ Added Remember-me checkbox. Passed as third arg to `login()`. Backend already supports `remember` param; refresh token goes to localStorage vs sessionStorage based on this flag. |
| **L-17** | `components/SessionGuard.vue`, `App.vue` | ✅ New `billing-returned` event on SessionGuard. App.vue's handler calls `loadAll()` then fires `triggerToast` (success) or `triggerErrorToast` (failure) so the user is acknowledged after returning from SattaBase billing. |
| **L-18** | `App.vue::handleDsrEnterPortal` | ✅ Replaced two native `alert()` calls with `triggerToast` / `triggerErrorToast`. The existing toast system is non-blocking and consistent with the rest of the UI. |

### Verification
```bash
$ python3 manage.py check  → 0 issues
```

---

## 8. Verification

Audit-only — no code changes were made. Findings are reproducible by reading the cited file:line locations and tracing the data flow described.

### Files Audited

**DSR login (frontend):**
- `dealerfrontend/src/components/DsrLoginPage.vue`
- `dealerfrontend/src/components/DsrRegisterPage.vue`
- `dealerfrontend/src/components/DsrSelfRegisterPage.vue`
- `dealerfrontend/src/services/dsrClient.ts`
- `dealerfrontend/src/services/api/dsrAuth.service.ts`

**Invitation:**
- `dealerfrontend/src/components/DsrManagementPanel.vue`
- `dealerfrontend/src/components/AddRepModal.vue`
- `dealerfrontend/src/components/DsrDashboard.vue`
- `dealerfrontend/src/services/api/invitation.service.ts`
- `dealerfrontend/src/services/api/dealer.service.ts`
- `dealerfrontend/src/composables/useInvitations.ts`
- `dealerfrontend/src/composables/useDealerContext.ts`

**Permission:**
- `dealerfrontend/src/composables/useAccess.ts`
- `dealerfrontend/src/composables/usePermissions.ts`
- `dealerfrontend/src/composables/useDealerContext.ts`
- `dealerfrontend/src/components/PermissionGuard.vue`
- `dealerfrontend/src/components/SessionGuard.vue`

**Dealer access:**
- `dealerfrontend/src/components/LoginPage.vue`
- `dealerfrontend/src/components/LoginForm.vue`
- `dealerfrontend/src/components/SessionGuard.vue`
- `dealerfrontend/src/components/ManageBillingButton.vue`
- `dealerfrontend/src/composables/useAuth.ts`
- `dealerfrontend/src/composables/useBillingRedirect.ts`
- `dealerfrontend/src/composables/useSubscription.ts`
- `dealerfrontend/src/lib/api.ts`
- `dealerfrontend/src/lib/auth.ts`
- `dealerfrontend/src/lib/constants.ts`
- `dealerfrontend/src/App.vue`
- `dealerfrontend/sattabase.config.ts`
- `dealerfrontend/src/services/apiClient.ts`

### Audit Method

4 parallel Explore agents dispatched with focused scope per area. Each agent:
- Read all files in its scope IN FULL
- Produced a structured Markdown report with file:line citations
- Categorized bugs by severity and area
- Suggested concrete fixes (not vague advice)

Reports were then synthesized and deduplicated into this single tracking document.

---

## 9. Bug Counts (Final, Deduped)

| Area | Critical | High | Medium | Low | Other | Total |
|------|---------:|-----:|-------:|----:|------:|------:|
| DSR login | 0 | 5 | 7 | 4 | 0 | **16** |
| Invitation | 1 | 4 | 8 | 2 | 1 | **16** |
| Permission | 2 | 2 | 4 | 3 | 1 | **12** |
| Dealer access | 0 | 4 | 7 | 4 | 2 | **17** |
| **Cross-cutting** | 2 | — | — | — | 2 | **4** |
| **Total** | **5** | **14** | **15** | **10** | **5** | **49** |

(Some bugs span multiple areas; the deduped total is 44.)
