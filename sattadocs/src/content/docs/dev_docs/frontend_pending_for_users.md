---
title: Frontend Pendings for user
description: A reference page in my new Starlight docs site.
---

# Frontend Pending Items for User-Facing Features

> Gap analysis between backend API endpoints and current frontend implementation.
> Generated: 2026-05-03

---

## Summary

| Metric | Value |
|--------|-------|
| Total user-facing backend endpoints | 42 |
| Fully implemented in frontend | 34 (81%) |
| API function exists but unused | 1 |
| Not implemented at all | 4 |
| Frontend bugs found | 1 |
| GDPR compliance gaps | 1 |

---

## 1. Endpoint-by-Endpoint Status

### Auth Controller (`/auth`) — 10 endpoints

| # | Method | Path | Status | Notes |
|---|--------|------|--------|-------|
| A1 | GET | `/auth/choices` | Done | Timezone/currency/language dropdowns. Used by `RegisterForm.vue` and `ProfileCard.vue`. |
| A2 | POST | `/auth/register` | Done | `RegisterForm.vue` page. |
| A3 | POST | `/auth/login` | Done | `LoginForm.vue` with "remember me" support. |
| A4 | POST | `/auth/token/refresh` | Done | Used internally by `api.ts` on 401 responses (transparent to user). |
| A5 | POST | `/auth/token/verify` | ~~Missing~~ → **N/A (Future)** | No frontend call needed. Tokens are implicitly verified on each API request via JWT decode. Documented as intentionally unused in `auth.ts` (L1 note). Moved to future plan — standalone utility adds no UX value. |
| A6 | POST | `/auth/token/blacklist` | Done | Added to `logout()` in `auth.ts` — blacklists refresh token server-side before clearing local state. |
| A7 | POST | `/auth/password-reset/request` | Done | Step 1 of `ForgotPasswordForm.vue`. |
| A8 | POST | `/auth/password-reset/confirm` | Done | Step 2 of `ForgotPasswordForm.vue` (OTP-based). |
| A9 | POST | `/auth/verify-email/request` | Done | `VerifyEmailForm.vue` + ProfileCard resend button. |
| A10 | POST | `/auth/verify-email/confirm` | Done | `VerifyEmailForm.vue`. |

### User Controller (`/users`) — 11 endpoints

| # | Method | Path | Status | Notes |
|---|--------|------|--------|-------|
| U1 | GET | `/users/me` | Done | Core auth state via `useAuth` composable (fetches `/billing/auth/me` which includes user data). |
| U2 | GET | `/users/{slug}` | **Missing** → **Future Plan** | Public profile by UUID slug. No page, no API call. Would enable shared profile URLs. Deferred to future phase (M5). |
| U3 | PUT | `/users/me` | Done | `ProfileCard.vue` edit mode with timezone/currency/language selectors. |
| U4 | PUT | `/users/me/avatar` | Done | `ProfileCard.vue` with client-side validation (file type, size). |
| U5 | DELETE | `/users/me/avatar` | Done | `ProfileCard.vue` remove avatar button. |
| U6 | POST | `/users/me/change-password` | Done | `SettingsPanel.vue` with current password + new password fields. |
| U7 | POST | `/users/me/confirm-identity` | Done | Password gate implemented in `SettingsPanel.vue` — "Verify your identity" card in Danger Zone with 5-min countdown. Once verified, Change Email and Delete Account skip inline password fields. `confirmIdentity()` added to `auth.ts`. |
| U8 | POST | `/users/me/change-email` | Done | `SettingsPanel.vue` step 1 — requires current password. |
| U9 | POST | `/users/me/change-email/confirm` | Done | `SettingsPanel.vue` step 2 — OTP confirmation. `/auth/email-change/confirm` page exists. |
| U10 | POST | `/users/me/delete-account` | Done | `SettingsPanel.vue` with typed confirmation phrase. |
| U11 | POST | `/users/me/logout` | Done | `SettingsPanel.vue` + sidebar sign-out. |

### Billing Public Controller (`/billing`) — 3 endpoints

| # | Method | Path | Status | Notes |
|---|--------|------|--------|-------|
| B1 | GET | `/billing/products` | Done | `BillingOverview.vue` products catalog. |
| B2 | GET | `/billing/products/{slug}` | Done | `PlanComparison.vue` — returns product + plans + access entries. |
| B3 | GET | `/billing/products/{slug}/plans` | N/A | Dead `getPlansForProduct()` removed from `billing.ts`. Endpoint still works; just no standalone frontend caller needed. |

### Billing Protected Controller (`/billing`) — 14 endpoints

| # | Method | Path | Status | Notes |
|---|--------|------|--------|-------|
| B4 | GET | `/billing/auth/me` | Done | Foundational — powers `useAuth` composable. |
| B5 | GET | `/billing/subscriptions` | Done | `useSubscription` composable. |
| B6 | GET | `/billing/subscriptions/transactions` | Done | Full transaction history with pagination in `BillingOverview.vue` + summary in `DashboardHome.vue`. |
| B7 | POST | `/billing/subscriptions/sync` | Done | `BillingOverview.vue` — called after Stripe Portal return. |
| B8 | GET | `/billing/subscriptions/{product_slug}` | **Unused API** | `billingApi.getSubscriptionDetail()` exists in `billing.ts:229` but no component calls it. Detailed subscription data (plan features, access entries) is never displayed. |
| B9 | POST | `.../cancel` | Done | `BillingOverview.vue` with cancel modal + optional reason. |
| B10 | POST | `.../reactivate` | Done | `BillingOverview.vue` reactivate button. |
| B11 | POST | `.../change-plan` | Done | `PlanComparison.vue` — used for paid-to-free downgrade path. |
| B12 | POST | `.../checkout` | Done | `PlanComparison.vue` — Free-to-Paid and Canceled-to-Paid checkout. |
| B13 | POST | `/billing/checkout/confirm` | Done | `BillingOverview.vue` — handles `?checkout=success&session_id=...` return URL. |
| B14 | POST | `/billing/portal` | Done | `BillingOverview.vue` + `DashboardHome.vue` — Stripe Customer Portal. |
| B15 | POST | `.../preview-plan-change` | Done | `PlanComparison.vue` — proration preview modal before plan change. |
| B16 | POST | `.../confirm-plan-change` | Done | `PlanComparison.vue` — safe two-step plan change confirmation. |
| B17 | GET | `/billing/export-data` | Done | `billingApi.exportBillingData()` in `billing.ts`, "Export Your Data" button in `SettingsPanel.vue` with JSON download. |

---

## 2. Bugs Found

### ~~BUG-1: Sidebar Always Shows "Free Plan"~~ — FIXED

**File:** `frontend/src/components/astro/Sidebar.astro` (lines 495-517)

**Problem:** The sidebar subscription display calls `apiClient.get("/billing/subscriptions")` and checks `Array.isArray(data)` to find the active subscription. However, the backend endpoint now returns a paginated response:

```json
{ "items": [...], "total": 1, "has_more": false }
```

Since `data` is an object (not an array), `Array.isArray(data)` returns `false`, so `activeSub` is always `null`, and the sidebar always falls back to displaying **"Free Plan"** regardless of the user's actual subscription.

**Fix:**
```javascript
// Line 495-497 — change from:
const data = await apiClient.get<any[]>("/billing/subscriptions");
const activeSub = Array.isArray(data)
  ? data.find((s: any) => s.status === "active" || s.status === "trialing")
  : null;

// To:
const data = await apiClient.get<{ items: any[] }>("/billing/subscriptions");
const subs = data?.items || [];
const activeSub = subs.find(
  (s: any) => s.status === "active" || s.status === "trialing"
);
```

**Impact:** Every user with an active/paid subscription sees "Free Plan" in the sidebar. This is visually broken and undermines the billing UX.

**Status:** Fixed in `Sidebar.astro` L495-497 — now reads `data.items` instead of treating `data` as a flat array.

---

## 3. Navigation Gaps

### ~~NAV-1: Plans Nav Item Disabled~~ — FIXED

**File:** `frontend/src/components/astro/Sidebar.astro` (line 29)

The sidebar shows "Plans" as disabled with a "Coming Soon" badge, but the plan comparison page at `/dashboard/billing/plans/[slug]` is fully implemented and functional (accessible via direct URL). The nav item should be activated.

**Current:**
```javascript
{ label: "Plans", href: "/dashboard/billing", icon: "plans",
  disabled: true, badge: "Coming Soon", badgeColor: "brand",
  tooltip: "Plan comparison and switching will be available soon" },
```

**Fix:** Removed `disabled: true` and `badge`, set href to `/dashboard/billing/plans/sattabase`.

**Status:** Fixed in `Sidebar.astro` L29.

### NAV-2: Finance Section Entirely Placeholder

Lines 37-41 define "Transactions", "Accounts", "Budgets", "Reports" — all disabled with "Soon" badges. Transaction history is already partially shown inside `BillingOverview.vue`, so having it disabled in the nav is misleading. Either:
- Enable "Transactions" pointing to a dedicated `/dashboard/billing/transactions` page, or
- Remove the entire Finance section until those features are built

### ~~NAV-3: No GDPR Export Entry Point~~ — FIXED

The backend `GET /billing/export-data` now has a corresponding "Export Your Data" button in Settings page. Downloads all billing data as a formatted JSON file.

**Status:** Fixed — added to `SettingsPanel.vue` with `billingApi.exportBillingData()` + browser download trigger.

---

## 4. Items by Priority

### Critical (Fix Now)

| # | Item | Type | File(s) | Effort |
|---|------|------|---------|--------|
| ~~**C1**~~ | ~~Sidebar subscription display bug~~ | Bug | `Sidebar.astro` L495-517 | S |
| ~~**C2**~~ | ~~GDPR billing data export~~ | Missing feature | `billing.ts` + `SettingsPanel.vue` | M |

### High Priority

| # | Item | Type | File(s) | Effort |
|---|------|------|---------|--------|
| ~~**H1**~~ | ~~Token blacklisting on logout~~ | Security | `lib/auth.ts` L132-142 | S |
| ~~**H2**~~ | ~~Plans nav item disabled~~ | Nav gap | `Sidebar.astro` L29 | S |
| ~~**H3**~~ | ~~Dedicated billing transactions page with full pagination, invoice PDFs, filters~~ | Missing page | New page + route | L |

### Medium Priority

| # | Item | Type | File(s) | Effort |
|---|------|------|---------|--------|
| ~~**M1**~~ | ~~`getSubscriptionDetail()` API function exists but never used — detailed subscription view (plan features, access entries) now shown via expandable panel~~ | Unused API | `billing.ts` L229, `BillingOverview.vue` | M |
| ~~**M2**~~ | ~~DashboardHome transaction list shows fewer fields than BillingOverview (missing tax, period dates, PDF download links)~~ | UX inconsistency | `DashboardHome.vue` | S |
| ~~**M3**~~ | ~~`getPlansForProduct()` dead code~~ | Dead code | `billing.ts` L201-205 | S |
| ~~**M4**~~ | ~~Finance section in sidebar is entirely placeholder — either enable Transactions or remove section~~ | Nav cleanup | `Sidebar.astro` L37-41 | S |
| **M5** | `GET /users/{slug}` public profile endpoint has no frontend page | Future Plan | New page | M |
| ~~**M6**~~ | ~~`POST /users/me/confirm-identity` — danger zone identity confirmation flow with 5-min countdown~~ | ~~Done~~ | ~~`auth.ts` + `SettingsPanel.vue`~~ | ~~M~~ |

### Low Priority

| # | Item | Type | File(s) | Effort |
|---|------|------|---------|--------|
| **L1** | `POST /auth/token/verify` standalone verification — documented as intentionally unused in `auth.ts`; implicit JWT verify works fine | N/A (Future) | — | — |
| **L2** | Inline email verification modal — currently requires navigating to `/auth/verify-email`; deferred to future phase | Future Plan | `DashboardHome.vue` | L |

---

## 5. Recommended Implementation Order

If we address these before moving to Phase 10 (Admin Frontend), the user-facing experience will be fully in sync with the backend:

1. ~~**C1** — Fix sidebar subscription bug~~ Done
2. ~~**H1** — Add token blacklist on logout~~ Done
3. ~~**H2** — Enable Plans nav item~~ Done
4. ~~**M3** — Remove dead `getPlansForProduct()`~~ Done
5. ~~**C2** — Add GDPR export button in Settings~~ Done
6. ~~**M4** — Clean up Finance nav section~~ Done
7. ~~**M2** — Sync DashboardHome transaction fields with BillingOverview~~ Done
8. ~~**M1** — Add subscription detail view using existing API function~~ Done
9. ~~**H3** — Dedicated transactions page~~ Done
10. **M5** — Public profile page (Future Plan)
11. ~~**M6** — Danger zone identity confirmation flow~~ Done
12. **L2** — Inline email verification modal (Future Plan)
- **L1** — Token verify endpoint (N/A — documented as intentionally unused)

Items 1-4 can be done in under 10 minutes. Items 1-8 cover everything that's "already built but not wired up." Items 9-12 are new feature work.

---

## 6. Dead Code to Clean Up

| File | Line(s) | Code | Reason |
|------|---------|------|--------|
| ~~`lib/billing.ts`~~ | ~~201-205~~ | ~~`getPlansForProduct()`~~ | Removed. `getProductBySlug()` returns plans inline. |
| ~~`lib/billing.ts`~~ | ~~119-132~~ | ~~`RefundInputSchema`, `RefundOutputSchema`~~ | Removed. Admin-only types — only used by `refundSubscription()`. Will be in admin API client (Phase 10). |
| ~~`lib/billing.ts`~~ | ~~270-275~~ | ~~`refundSubscription()`~~ | Removed. Admin-only endpoint moved out of user-facing API client. Will be in admin API client (Phase 10). |
| ~~`lib/billing.ts`~~ | ~~300-314~~ | ~~`syncCustomerData()`~~ | Removed. Admin-only endpoint moved out of user-facing API client. Same as above. |
