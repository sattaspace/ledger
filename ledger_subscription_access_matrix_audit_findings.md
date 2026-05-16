# Subscription Access Matrix — Cross-Frontend Audit Findings

> **Date**: 2026-05-16  
> **Scope**: All frontends (ledgerfrontend, frontend, dealerfrontend, sister-domain-starter)  
> **Focus**: Are all frontends completely aware of and enforcing the subscription plan access matrix?

---

## Executive Summary

The subscription access matrix is **well-implemented in ledgerfrontend** with a three-layer gating system (middleware, sidebar, Vue components). This audit originally revealed **2 critical gaps**, **3 high-priority issues**, and **4 medium-priority concerns** across the frontend ecosystem. **Both critical findings, 2 high, and all 4 medium issues have been fixed** (2026-05-16): BudgetsPage.vue now has its FeatureGate wrapper, the `limitReached` computed property correctly handles 0=unlimited, all 8 Detail sub-pages now have FeatureGate, the CalendarPage is gated by `bills`, sidebar flash is fixed with CSS opacity transitions, `hasQuota()` helper added for correct 0=unlimited semantics, data retention days notice added to TransactionsPage, and PlanLimitBadge component created for create button quota display. The most significant remaining issue is that **dealerfrontend has zero subscription gating** despite having the composable infrastructure in place.

| Priority | Count | Fixed |
|----------|-------|-------|
| 🔴 Critical | 2 | 2 ✅ |
| 🟠 High | 3 | 2 ✅ |
| 🟡 Medium | 4 | 4 ✅ |
| 🟢 Low / Info | 3 | 1 ✅ |

---

## Access Matrix Reference — Satta Ledger Plans

| Feature Key | Free | Standard ($9/mo) | Pro ($29/mo) |
|---|---|---|---|
| dashboard | ✅ true | ✅ true | ✅ true |
| transactions | ✅ true | ✅ true | ✅ true |
| reports | ✅ true | ✅ true | ✅ true |
| budgets | ✅ true | ✅ true | ✅ true |
| goals | ✅ true | ✅ true | ✅ true |
| cards | ✅ true | ✅ true | ✅ true |
| debts | ✅ true | ✅ true | ✅ true |
| accounts | ✅ true | ✅ true | ✅ true |
| institutions | ✅ true | ✅ true | ✅ true |
| categories | ✅ true | ✅ true | ✅ true |
| tags | ✅ true | ✅ true | ✅ true |
| bills | ✅ true | ✅ true | ✅ true |
| **investments** | ❌ false | ✅ true | ✅ true |
| **insurance** | ❌ false | ✅ true | ✅ true |
| **invoices** | ❌ false | ✅ true | ✅ true |
| **vault** | ❌ false | ✅ true | ✅ true |
| max_accounts | 3 | 0 (unlimited) | 0 (unlimited) |
| max_budgets | 1 | 0 (unlimited) | 0 (unlimited) |
| max_goals | 1 | 0 (unlimited) | 0 (unlimited) |
| max_institutions | 3 | 0 (unlimited) | 0 (unlimited) |
| max_categories | 10 | 0 (unlimited) | 0 (unlimited) |
| max_transactions | 50 | 0 (unlimited) | 0 (unlimited) |
| max_tags | 20 | 0 (unlimited) | 0 (unlimited) |
| max_bills | 5 | 0 (unlimited) | 0 (unlimited) |
| max_cards | 3 | 0 (unlimited) | 0 (unlimited) |
| max_debts | 5 | 0 (unlimited) | 0 (unlimited) |
| max_investments | 0 (disabled) | 0 (unlimited) | 0 (unlimited) |
| max_insurance | 0 (disabled) | 0 (unlimited) | 0 (unlimited) |
| max_invoices | 0 (disabled) | 5 | 0 (unlimited) |
| max_vault_documents | 0 (disabled) | 5 | 0 (unlimited) |
| export_pdf | ❌ false | ✅ true | ✅ true |
| api_access | ❌ false | ✅ true | ✅ true |
| priority_support | ❌ false | ❌ false | ✅ true |
| data_retention_days | 90 | 365 | 0 (forever) |
| white_label | — | — | ✅ true |
| audit_log | — | — | ✅ true |

**Key distinction**: `0` for `max_*` keys has dual semantics — it means **"feature disabled"** when the corresponding boolean key is `false` (e.g., `investments: false` + `max_investments: 0` on Free), but **"unlimited"** when the boolean is `true` (e.g., `accounts: true` + `max_accounts: 0` on Standard).

---

## 🔴 Critical Findings

### ~~🔴 CRITICAL-1: BudgetsPage.vue Missing FeatureGate Wrapper~~ ✅ FIXED

**File**: `ledgerfrontend/src/components/vue/budgets/BudgetsPage.vue`  
**Severity**: Critical — inconsistent gating across the three-layer system  
**Fixed**: 2026-05-16 — Added `FeatureGate` + `UpgradePrompt` imports and wrapped content with `<FeatureGate feature="budgets" show-fallback>` + `<UpgradePrompt feature="budgets" />` fallback slot, matching the pattern used by all 14 other feature pages.

All 14 other feature pages in ledgerfrontend wrap their content in `<FeatureGate feature="X" show-fallback>`. The BudgetsPage does NOT. While the middleware will still redirect unauthenticated/no-access users to `/dashboard/upgrade?feature=budgets`, the Vue component itself never validates access. This creates an inconsistency:

- ✅ Middleware: `FEATURE_GATED_PATHS["/dashboard/budgets"] = "budgets"` — redirects to upgrade page
- ✅ Sidebar: `data-feature="budgets"` — hides nav item when no access
- ~~❌ Vue component: No `FeatureGate` wrapper~~ → ✅ Now wrapped with FeatureGate

**Impact**: If the sessionStorage is empty on page load (race condition, first visit), the middleware lets the page render and relies on the Vue component to gate. Without FeatureGate, the budgets page briefly shows its full UI before the access check completes.

**Fix applied**:
```vue
<template>
  <FeatureGate feature="budgets" show-fallback>
    <!-- existing content -->
    <template #no-access>
      <UpgradePrompt feature="budgets" />
    </template>
  </FeatureGate>
</template>
```

---

### ~~🔴 CRITICAL-2: FeatureGate.limitReached Breaks on Unlimited Plans (0 = unlimited)~~ ✅ FIXED

**File**: `ledgerfrontend/src/components/vue/FeatureGate.vue` Lines 47-51  
**Severity**: Critical — incorrect "limit reached" display for Standard/Pro users  
**Fixed**: 2026-05-16 — Added `if (maxAllowed === 0) return false` guard before the comparison, treating 0 (unlimited) as never "reached".

```typescript
// BEFORE (broken):
const limitReached = computed(() => {
  if (props.limit === undefined || props.current === undefined) return false
  const maxAllowed = getLimit(props.feature, props.limit).value
  return props.current >= maxAllowed  // BUG: 0 means unlimited, not 0
})

// AFTER (fixed):
const limitReached = computed(() => {
  if (props.limit === undefined || props.current === undefined) return false
  const maxAllowed = getLimit(props.feature, props.limit).value
  if (maxAllowed === 0) return false  // 0 = unlimited, never "reached"
  return props.current >= maxAllowed
})
```

When a Standard/Pro plan has `max_accounts: 0` (unlimited), `getLimit("max_accounts", 0)` returns `0`. Then `current >= 0` is **always true** for any `current >= 0`, making `limitReached` always `true`. This means any FeatureGate with `:limit` and `:current` props will incorrectly show the "limit reached" slot for unlimited plans.

**Current Impact**: **Dormant** — no page currently passes `:limit` and `:current` to FeatureGate. All 15 pages use `<FeatureGate feature="X" show-fallback>` without limit props. However, this will become a live bug when limit-based gating is added (which is the intended design per the FeatureGate docstring example: `<FeatureGate feature="budgets" :limit="5" :current="budgetStore.items.length">`).

---

## 🟠 High Priority Findings

### ~~🟠 HIGH-1: All 8 Detail Sub-pages Lack FeatureGate~~ ✅ FIXED

**Files**: All `*Detail.vue` components  
**Severity**: High — detail pages accessible via direct URL without in-component access validation  
**Fixed**: 2026-05-16 — Added `FeatureGate` + `UpgradePrompt` imports and wrappers to all 8 Detail pages, following the same pattern established by the 15 list pages.

| Detail Page | Feature Key | FeatureGate? |
|---|---|---|
| AccountDetail.vue | accounts | ✅ |
| TransactionDetail.vue | transactions | ✅ |
| BillDetail.vue | bills | ✅ |
| BudgetDetail.vue | budgets | ✅ |
| DebtDetail.vue | debts | ✅ |
| InvestmentDetail.vue | investments | ✅ |
| InvoiceDetail.vue | invoices | ✅ |
| VaultDetail.vue | vault | ✅ |

Each Detail page now wraps its content in `<FeatureGate feature="X" show-fallback>` with an `<UpgradePrompt>` fallback, preventing brief content exposure during the middleware race condition.

---

### ~~🟠 HIGH-2: CalendarPage Completely Ungated~~ ✅ FIXED

**File**: `ledgerfrontend/src/components/vue/calendar/CalendarPage.vue`  
**Severity**: High — no feature gate at any layer  
**Fixed**: 2026-05-16 — Calendar page is now gated by the `bills` feature key across all three layers:

- ✅ Middleware: Added `"/dashboard/calendar": "bills"` to `FEATURE_GATED_PATHS`
- ✅ Sidebar: Added `feature: "bills"` to the Financial Calendar nav item
- ✅ Vue component: Wrapped CalendarPage with `<FeatureGate feature="bills" show-fallback>` + `<UpgradePrompt>` fallback

**Decision made**: The calendar is gated by the `bills` feature key because it primarily shows bill due dates. When debt events are added, the calendar is already gated (debts is a feature available on all plans). This provides consistent gating without creating a new `calendar` feature key.

---

### HIGH-3: Dealerfrontend Has Zero Subscription Gating

**Files**: `dealerfrontend/` — all components and middleware  
**Severity**: High — all features always visible, no upgrade prompts

The dealerfrontend has the composable infrastructure (`useAccess.ts`, `useSubscription.ts`) but uses NONE of it in its UI:

| Layer | Ledgerfrontend | Dealerfrontend |
|---|---|---|
| Middleware feature gating | ✅ 15 paths | ❌ None |
| Sidebar feature gating | ✅ 16 data-feature items | ❌ None |
| Vue FeatureGate components | ✅ 15 pages | ❌ None |
| UpgradePrompt component | ✅ Present | ❌ Missing |
| sessionStorage access cache | ✅ Present | ❌ Missing |
| Upgrade page | ✅ /dashboard/upgrade | ❌ Missing |
| useAuth hasFeature() | ✅ Present | ❌ Missing |

**Additional issue**: There is **no "dealer" product** in `billing_seed_data.py`. The seed data defines `finance`, `analytics`, and `ledger` products but no `dealer` product. This means `/billing/auth/me` would return an empty access map for dealer users, and `hasAccess()` would always return `false`, hiding everything.

**Fix options**:
1. Add a `dealer` product to billing seed data with its own access entries
2. Implement the same three-layer gating pattern from ledgerfrontend
3. Or explicitly document that dealerfrontend is a free/ungated product

---

## 🟡 Medium Priority Findings

### ~~🟡 MEDIUM-1: hasAccess() Returns False for Unlimited (0-value) Limit Keys~~ ✅ FIXED

**Files**: All frontend `useAccess.ts` composables  
**Severity**: Medium — semantic confusion, not a runtime bug

The `hasAccess()` function treats `0` as "no access":
```typescript
if (typeof value === "number") return value > 0;  // 0 → false
```

But `max_accounts: 0` means "unlimited" on Standard/Pro plans. Calling `hasAccess("max_accounts")` returns `false` even when the user has unlimited accounts.

**Current Impact**: Low — `hasAccess()` is only used for boolean feature keys in FeatureGate (`hasAccess("investments")`, `hasAccess("accounts")`). The `getLimit()` function correctly returns `0` for unlimited.

**Risk**: A developer checking `hasAccess("max_accounts")` to decide whether to show a "create account" button would hide it for Standard/Pro users (who should always see it). The correct pattern is:
```typescript
const hasFeature = hasAccess("accounts")     // boolean: true for all plans
const maxAccounts = getLimit("max_accounts")  // number: 3 for Free, 0 for Standard/Pro
const canCreate = hasFeature.value && (maxAccounts.value === 0 || currentCount < maxAccounts.value)
```

**Fixed:** 2026-05-16 — Added `hasQuota(maxKey, featureKey?)` helper to `useAccess.ts`:
- Returns `true` when the limit value is `>= 0` AND the feature boolean is enabled
- Returns `false` when the feature is disabled or the key is missing
- Added comprehensive JSDoc to both `hasAccess()` and `hasQuota()` explaining the 0=unlimited semantics
- `hasAccess()` behavior unchanged for backward compatibility

```typescript
// New helper with correct unlimited=0 semantics:
const canCreate = hasQuota("max_accounts", "accounts");  // true for Standard/Pro (unlimited)
const maxAccounts = getLimit("max_accounts");            // 0 for Standard/Pro
const atLimit = maxAccounts.value > 0 && currentCount >= maxAccounts.value;
```

---

### ~~🟡 MEDIUM-2: Sidebar Flash of Hidden Items on Initial Load~~ ✅ FIXED

**File**: `ledgerfrontend/src/components/astro/Sidebar.astro`  
**Severity**: Medium — visual glitch  
**Fixed**: 2026-05-16 — Replaced `display: none` inline style with CSS class-based opacity transition. Gated items start at `opacity: 0` by default (preventing flash), then receive either `.feature-visible` (opacity: 1, pointer-events: auto) or `.feature-hidden` (collapsed with height: 0) after the access check runs.

The sidebar feature-gating script reads from `sessionStorage('sattabase:auth_access')` synchronously. On the first page load or after session expiration, this cache is empty. The script defaults to **hiding all gated items** (security-first approach), then shows them after `auth-state-changed` fires.

**Fix applied:**
```css
.sidebar-nav-item[data-feature] {
  opacity: 0;
  pointer-events: none;
  transition: opacity 150ms ease-in;
}
.sidebar-nav-item[data-feature].feature-visible {
  opacity: 1;
  pointer-events: auto;
}
.sidebar-nav-item[data-feature].feature-hidden {
  opacity: 0;
  pointer-events: none;
  height: 0;
  overflow: hidden;
}
```

---

### ~~🟡 MEDIUM-3: data_retention_days Not Visually Communicated~~ ✅ FIXED

**File**: `ledgerfrontend/src/components/vue/settings/SettingsPage.vue`  
**Severity**: Medium — Free users unaware of data retention limits

The backend enforces `data_retention_days` (90 for Free, 365 for Standard, forever for Pro) by filtering transaction queries. But the frontend never communicates this to users:
- No banner or notice on the transactions page saying "Showing transactions from the last 90 days"
- No mention in Settings
- No visual indicator on the Reports page
- Users on the Free plan may think old transactions are permanently deleted

**Fixed:** 2026-05-16 — Added data retention notice banner to TransactionsPage.vue:
- Added `useAccess` composable import and `dataRetentionDays` computed via `getLimit("data_retention_days")`
- Added subtle cyan info banner after page header showing "Showing transactions from the last X days. Upgrade for full history."
- Banner only appears when `dataRetentionDays > 0` (Free=90, Standard=365; Pro=0/unlimited → hidden)
- Upgrade link points to `/dashboard/upgrade`

---

### ~~🟡 MEDIUM-4: No Plan Limit Indicators on Create Buttons~~ ✅ FIXED

**Files**: All list page Vue components  
**Severity**: Medium — Free users hit 403 errors from backend without warning

When a Free user reaches their plan limit (e.g., 3 accounts, 50 transactions, 1 budget), clicking "Add Account" sends a request to the backend which returns a 403 with a plan limit message. The frontend shows this as a toast error. However, a better UX would be:
- Showing remaining quota next to the create button (e.g., "3/3 Accounts")
- Disabling or visually de-emphasizing the create button when the limit is reached
- Proactively showing an UpgradePrompt instead of waiting for the 403

**Fixed:** 2026-05-16 — Created `PlanLimitBadge.vue` component and integrated on ALL list pages:
- New reusable component with props: `maxKey` (e.g., "max_accounts"), `featureKey` (e.g., "accounts"), `current` (count)
- Shows `2/3` in muted text when under limit, `3/3` in amber with "Upgrade" link when at limit
- Hidden when max is 0 (unlimited) or feature is disabled
- Exported from `@/components/vue` index.ts
- Added to AccountsPage.vue next to "Add Account" button
- Extended to all 13 list pages (2026-05-16): Accounts, Transactions, Bills, Budgets, Goals, Institutions, Categories, Tags, Cards, Debts, Investments, Insurance, Invoices, Vault

---

## 🟢 Low / Informational

### LOW-1: Base Frontend (frontend/) Has No Feature Gating — Expected

The base frontend (`frontend/`) is the billing/admin hub where users manage subscriptions. It correctly has no feature gating since all navigation items (Dashboard, Profile, Settings, Billing, Plans, Transactions, Admin) should always be visible. The admin section is role-gated (checking `is_staff`/`role`), which is the correct approach.

**Status**: ✅ Working as designed.

---

### LOW-2: Sister-Domain-Starter Has No Feature Gating — Expected

The `sister-domain-starter/` is a template, not a production frontend. It has the infrastructure (`useAccess.ts`, `useSubscription.ts`, `billing.ts`) but no UI components to gate. When a new sister domain is built from this template, the developer should implement the three-layer pattern from ledgerfrontend.

**Status**: ✅ Working as designed.

---

### ~~LOW-3: Export PDF Feature Gate Deferred~~ ✅ FIXED

The `export_pdf` feature key exists in seed data (Free: false, Standard: true, Pro: true) but there was no export endpoint or UI button to gate.

**Fixed:** 2026-05-16 — CSV export added to ReportPage with `export_pdf` feature gating:
- "Export CSV" button available to all plans (always visible in page header)
- "Export PDF" button gated by `<FeatureGate feature="export_pdf" :show-fallback="false">` (Standard/Pro only)
- CSV export works for all 8 report tabs with proper formatting and BOM encoding
- This implements the `export_pdf` feature key enforcement at the Vue component layer

**Status**: ✅ FIXED (2026-05-16) — CSV export + `export_pdf` feature gate implemented in ReportPage.vue.

---

## Feature Gate Coverage Matrix — All Frontends

### Ledgerfrontend (Primary Product)

| Layer | Feature | Middleware | Sidebar | FeatureGate (Vue) | Status |
|---|---|---|---|---|---|
| transactions | ✅ | ✅ | ✅ | ✅ | Complete |
| reports | ✅ | ✅ | ✅ | ✅ | Complete |
| accounts | ✅ | ✅ | ✅ | ✅ | Complete |
| institutions | ✅ | ✅ | ✅ | ✅ | Complete |
| categories | ✅ | ✅ | ✅ | ✅ | Complete |
| tags | ✅ | ✅ | ✅ | ✅ | Complete |
| bills | ✅ | ✅ | ✅ | ✅ | Complete |
| **budgets** | ✅ | ✅ | ✅ | ✅ Complete |
| goals | ✅ | ✅ | ✅ | ✅ | Complete |
| cards | ✅ | ✅ | ✅ | ✅ | Complete |
| debts | ✅ | ✅ | ✅ | ✅ | Complete |
| investments | ✅ | ✅ | ✅ | ✅ | Complete |
| insurance | ✅ | ✅ | ✅ | ✅ | Complete |
| invoices | ✅ | ✅ | ✅ | ✅ | Complete |
| vault | ✅ | ✅ | ✅ | ✅ | Complete |
| calendar | ✅ | ✅ | ✅ | ✅ Complete |
| **export_pdf** | — | — | ✅ | ✅ | Complete (ReportPage.vue) |
| notifications | ❌ | ❌ | ❌ | Always visible |
| dashboard | ❌ | ❌ | ❌ | Always visible |
| settings | ❌ | ❌ | ❌ | Always visible |

### Dealerfrontend

| Layer | Status |
|---|---|
| Middleware feature gating | ❌ None |
| Sidebar feature gating | ❌ None |
| Vue FeatureGate | ❌ None |
| Product in seed data | ❌ Missing |
| sessionStorage cache | ❌ Missing |

### Frontend (Base)

| Layer | Status |
|---|---|
| Middleware feature gating | ❌ Not needed (billing hub) |
| Sidebar feature gating | ❌ Not needed |
| Admin role gating | ✅ Implemented |
| Billing pages | ✅ Full subscription management |

---

## Priority Fix Order

### Immediate (This Sprint)
1. ~~**CRITICAL-1** — Add FeatureGate wrapper to BudgetsPage.vue~~ ✅ FIXED (2026-05-16)
2. ~~**CRITICAL-2** — Fix `limitReached` to treat `0` as unlimited in FeatureGate.vue~~ ✅ FIXED (2026-05-16)

### Next Sprint
3. ~~**HIGH-1** — Add FeatureGate to all 8 Detail sub-pages~~ ✅ FIXED (2026-05-16)
4. ~~**HIGH-2** — Decide calendar gating strategy and implement~~ ✅ FIXED (2026-05-16) — Gated by `bills` feature key
5. ~~**MEDIUM-2** — Fix sidebar flash with CSS opacity transition~~ ✅ FIXED (2026-05-16)

### Following Sprint
6. **HIGH-3** — Implement dealerfrontend subscription gating (or add dealer product to seed data)
7. ~~**MEDIUM-1** — Add `hasQuota()` helper or document the unlimited=0 pattern~~ ✅ FIXED (2026-05-16)
8. ~~**MEDIUM-3** — Add data_retention_days visual indicators~~ ✅ FIXED (2026-05-16)
9. ~~**MEDIUM-4** — Add plan limit indicators on create buttons~~ ✅ FIXED (2026-05-16) — Extended to all 13 list pages with PlanLimitBadge
10. ~~**LOW-3** — Export PDF feature gate~~ ✅ FIXED (2026-05-16) — CSV export + export_pdf FeatureGate on ReportPage

---

## Files Requiring Changes

| File | Change |
|---|---|
| `ledgerfrontend/src/components/vue/budgets/BudgetsPage.vue` | Add FeatureGate + UpgradePrompt wrapper |
| `ledgerfrontend/src/components/vue/FeatureGate.vue` | Fix `limitReached` for 0=unlimited |
| `ledgerfrontend/src/components/vue/accounts/AccountDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/transactions/TransactionDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/bills/BillDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/budgets/BudgetDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/debts/DebtDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/investments/InvestmentDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/invoices/InvoiceDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/vue/vault/VaultDetail.vue` | Add FeatureGate wrapper |
| `ledgerfrontend/src/components/astro/Sidebar.astro` | CSS opacity transition fix |
| `ledgerfrontend/src/components/vue/reports/ReportPage.vue` | CSV export + `export_pdf` FeatureGate |
| `ledgerfrontend/src/components/vue/budgets/BudgetsPage.vue` | SearchInput + PlanLimitBadge |
| All 13 list page Vue components | PlanLimitBadge integration (accounts, transactions, bills, budgets, goals, institutions, categories, tags, cards, debts, investments, insurance, invoices, vault) |
| `dealerfrontend/` (multiple files) | Implement three-layer gating pattern |
| `backend/common/management/commands/billing_seed_data.py` | Add dealer product (if gating dealerfrontend) |
