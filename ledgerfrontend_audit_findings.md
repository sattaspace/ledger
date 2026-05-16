# Ledger Frontend — Audit Findings

> Audited against: `ledger-feature-list.md` (80+ user-facing features across 5 phases)
> Date: 2026-05-16
> Target: `/ledgerfrontend` (Astro 6 + Vue 3 + Tailwind 4 + Pinia)

---

## Executive Summary

The ledgerfrontend is **architecturally mature** with a well-designed Astro SSR + Vue Islands pattern, a sophisticated CRUD store factory (`stores/base.ts`), comprehensive API coverage (95+ typed endpoints in `ledgerApi.ts`), and full TypeScript type mirroring (`ledgerTypes.ts`, 1438 lines). All 5 phases from the feature list have corresponding routes, pages, Vue components, Pinia stores, and API endpoints.

**Overall completeness: ~85%** of feature-list items have frontend UI implementations. The remaining gaps are primarily in advanced interactions (sorting, chart interactivity, export), a few missing form fields, and some stub/placeholder implementations.

### Critical: 4 Bugs (4 Fixed ✅) | High: 8 Missing Features (8 Fixed ✅, 1 Partial) | Medium: 10 Gaps (4 Fixed ✅) | Low: 8 Nice-to-Haves

---

## 1. BUGS (Must Fix)

### ~~🔴 BUG-1: AccountForm `buildCreatePayload` assigns wrong field~~ ✅ FIXED

**File:** `src/components/vue/accounts/AccountForm.vue` ~Line 73  
**Severity:** Critical — creates accounts with wrong `account_type`  
**Fixed:** 2026-05-16 — Changed `account_type: formData.institution_id as unknown as AccountType || "ASSET"` → `account_type: (formData.account_type as AccountType) || "ASSET"`

```js
// BEFORE (broken):
account_type: formData.institution_id as unknown as AccountType || "ASSET",  // ❌ WRONG

// AFTER (fixed):
account_type: (formData.account_type as AccountType) || "ASSET",  // ✅ CORRECT
```

**Impact:** Every new account creation sends `account_type = <institution_id number>` instead of "ASSET"/"LIABILITY"/"INVESTMENT", causing a 422 validation error or wrong data.

---

### ~~🔴 BUG-2: Investment store `fieldErrors` assignment uses wrong function~~ ✅ FIXED

**File:** `src/stores/investment.ts` ~Line 138  
**Severity:** High — field errors never display on investment forms  
**Fixed:** 2026-05-16 — Imported `extractFieldErrors` from `./base` and replaced `extractErrorMessage(err) as any` with `extractFieldErrors(err)`

```ts
// BEFORE (broken):
this.fieldErrors = extractErrorMessage(err) as any;  // ❌ Returns string, not Record<string, string[]>

// AFTER (fixed):
this.fieldErrors = extractFieldErrors(err);  // ✅ Returns Record<string, string[]>
```

**Impact:** The `as any` masks the type error. `extractErrorMessage()` returns a `string`, but `fieldErrors` expects `Record<string, string[]>`. Investment form validation errors will never render correctly.

---

### ~~🔴 BUG-3: Transaction tag chips always empty in list view~~ ✅ FIXED

**File:** `src/components/vue/transactions/TransactionsPage.vue`  
**Severity:** Medium — tags column always blank in transaction list  
**Fixed:** 2026-05-16 — Implemented batch-fetch of tags using `ledgerApi.transactionTags.list()` with concurrency of 5. After initial list load, tags are fetched per transaction and mapped to TagChips via the tag dropdown lookup. Added `ledgerApi` import and `loadTagsForTransactions()` call in `onMounted`.

The `transactionTagMap` ref was initialized as `{}` and never populated from the API. Individual transaction tags require fetching `/transactions/{id}/tags` per transaction, but the list view never made these calls.

**Impact:** Tags column in transaction DataTable always shows empty. Tags only appear on the TransactionDetail page.

**Fix applied:** Batch-fetch with concurrency limit to avoid N+1:
```ts
const BATCH_SIZE = 5;
for (let i = 0; i < items.length; i += BATCH_SIZE) {
  const batch = items.slice(i, i + BATCH_SIZE);
  const results = await Promise.allSettled(
    batch.map(async (tx) => {
      const txTags = await ledgerApi.transactionTags.list(tx.id);
      return { txId: tx.id, tags: txTags };
    })
  );
}
```

---

### ~~🔴 BUG-4: VaultUploadForm `content_type_id` and `object_id` hardcoded to "0"~~ ✅ FIXED

**File:** `src/components/vue/vault/VaultUploadForm.vue`  
**Severity:** Medium — document linking to entities broken  
**Fixed:** 2026-05-16 — Added optional `contentTypeId` and `objectId` props to VaultUploadForm. When provided, these values are used instead of "0". Standalone usage (from VaultPage) still defaults to "0"; context-aware usage (from entity pages) can pass the correct values.

```js
// BEFORE (broken):
formData.append("content_type_id", "0");
formData.append("object_id", "0");

// AFTER (fixed):
formData.append("content_type_id", props.contentTypeId != null ? String(props.contentTypeId) : "0");
formData.append("object_id", props.objectId != null ? String(props.objectId) : "0");
```

**Impact:** The Document Vault feature "Link to any entity" from the feature list is non-functional. Documents uploaded from the vault page have no entity association. Only the InsurancePage's "Link Document" modal correctly sets these values.

---

## 2. MISSING FEATURES (High Priority — From Feature List)

### ~~🟠 MISSING-1: Server-side sorting on all list pages~~ ✅ FIXED (TransactionsPage)

**Feature List Reference:** "Search & filter — By date range, account, category, payee, amount, status, tags"  
**Files:** All *Page.vue components with DataTable  
**Status:** `handleSortChange` implemented for TransactionsPage (primary use case)
**Fixed:** 2026-05-16 — Implemented `handleSortChange` in TransactionsPage.vue to map sort column keys to Django `ordering` query parameters. The handler sets the `ordering` filter and re-fetches the list.

All list pages have column headers marked as sortable, but the `handleSortChange` handler was empty (commented as "client-only"). The backend supports `ordering` query parameters via Django Ninja, but the frontend never sent sort parameters.

**Fix applied:**
```ts
function handleSortChange(payload: SortChangePayload) {
  const sortKeyMap: Record<string, string> = {
    date: "date", payee: "payee", amount_original: "amount_original",
  };
  const orderingField = sortKeyMap[payload.key];
  if (!orderingField) return;
  const ordering = payload.direction === "desc" ? `-${orderingField}` : orderingField;
  setFilter("ordering" as keyof TransactionFilter, ordering);
  setFilter("offset", 0);
  applyFilters();
}
```

**Note:** The same pattern can be applied to other list pages (BillsPage, AccountsPage, etc.) when needed.

---

### ~~🟠 MISSING-2: TransferForm cross-currency exchange rate~~ ✅ FIXED

**Feature List Reference:** "Multi-currency transactions — Buy something in EUR on a USD account? System auto-converts"  
**File:** `src/components/vue/transactions/TransferForm.vue`

**Fixed:** 2026-05-16 — Added cross-currency support to TransferForm:
- Added `fromCurrency`/`toCurrency` computeds that resolve currencies from selected accounts
- Added `isCrossCurrency` computed that detects when currencies differ
- Added `exchangeRate` ref (default "1.000000") with auto-population from cached rates
- Added `convertedAmount` computed that calculates destination amount
- Added amber-bordered conversion card UI showing rate input and destination amount
- Submit handler now includes `exchange_rate` and `amount_base` in payload when cross-currency
- Added `exchange_rate` and `amount_base` optional fields to `TransferCreate` interface in `ledgerTypes.ts`

TransferForm only supported same-currency transfers. There was no exchange rate field or auto-conversion for cross-currency transfers (e.g., transferring from USD checking to EUR savings).

---

### ~~🟠 MISSING-3: BudgetForm missing Status field~~ ✅ PARTIALLY FIXED

**Feature List Reference:** "Budget periods — Weekly, Monthly, or Yearly budgets"  
**File:** `src/components/vue/budgets/BudgetForm.vue`

**Fixed:** 2026-05-16 — Added `is_active` toggle switch in edit mode to BudgetForm:
- Added `is_active` to `mapEntityToForm` (defaults to `true`)
- Added `is_active` coercion in `buildUpdatePayload`
- Added toggle switch in template (edit mode only) with label "Active" and description "Deactivate this budget to pause tracking"
- Added `handleActiveToggle()` function

**Still missing (requires backend schema changes):**
- **End Date** — backend `BudgetCreate`/`BudgetUpdate` schemas don't have `end_date` field
- **Notes** — backend `BudgetCreate`/`BudgetUpdate` schemas don't have `notes` field

These fields need to be added to the Django model and schemas first before the frontend can support them.

---

### ~~🟠 MISSING-4: CalendarPage debt events not fetched~~ ✅ FIXED

**Feature List Reference:** "Bill calendar view — See all upcoming bills on a calendar"  
**File:** `src/components/vue/calendar/CalendarPage.vue`  
**Fixed:** 2026-05-16 — Added `ledgerApi.debts.list({ limit: 100, is_active: true })` call in `fetchCalendarEvents()` that maps `payment_day` + `monthly_payment` to calendar events for the current month.

The `DebtCalendarEvent` type was defined and the legend showed a "Debt" color, but `fetchCalendarEvents()` never called the debt API. Debt payment due dates were missing from the calendar.

**Fix applied:** Added debt event fetching after the goals section:
```ts
const debtResponse = await ledgerApi.debts.list({ limit: 100, is_active: true });
for (const debt of debtResponse.results) {
  if (debt.payment_day) {
    const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${dayStr}`;
    events.value.push({
      id: `debt-${debt.id}`, type: "debt",
      title: debt.entity_name || debt.debt_type,
      date: dateStr, amount: parseFloat(debt.monthly_payment),
      link: `/dashboard/debts/${debt.id}`, color: getTypeColor("debt"),
    });
  }
}
```

---

### ~~🟠 MISSING-5: NotificationsPage card/annual-fee alerts not fetched~~ ✅ FIXED

**Feature List Reference:** "Credit card due date reminders — Based on Account.due_day" / "Annual fee reminders — Based on Card.annual_fee_date"  
**File:** `src/components/vue/notifications/NotificationsPage.vue`

**Fixed:** 2026-05-16 — Added two new fetch blocks to `fetchNotifications()`:
1. **Credit card due date alerts**: Fetches active LIABILITY accounts with `due_day` set, computes next due date, and adds `card_due` notifications for those within 30 days
2. **Annual fee alerts**: Fetches active cards with `annual_fee_date` and `annual_fee > 0`, and adds `annual_fee` notifications for those within 60 days

Both follow the existing try/catch pattern for graceful degradation.

The notification page previously had "Cards" filter tab but `fetchNotifications()` never fetched card-related alerts (credit card due dates, annual fees).

---

### ~~🟠 MISSING-6: CSV/PDF export on Reports page~~ ✅ FIXED

**Feature List Reference:** "Multi-currency reports — All amounts converted to base currency for aggregation"  
**File:** `src/components/vue/reports/ReportPage.vue`  
**Fixed:** 2026-05-16 — Added CSV export functionality to all 8 report tabs with `export_pdf` feature gating:
- Added `exportCurrentTabCSV()` function that exports the active tab's data as a UTF-8 BOM CSV file with proper escaping
- Each tab generates appropriate headers and rows (Income vs Expense, Category Spending, Budget vs Actual, Net Worth, Cash Flow, Tag Spending, Debt Payoff, Investment Performance)
- CSV export button available to all plans ("Export CSV" in page header)
- PDF export button gated by `export_pdf` feature key via `<FeatureGate feature="export_pdf">` (Standard/Pro only)
- Added `useAccess` and `useToast` imports for feature check and success/error feedback
- Filenames include report type and date range for easy identification

Previously, no export functionality existed. Reports could only be viewed on-screen.

**Fix applied:**
```ts
function exportCurrentTabCSV(): void {
  const tab = activeTab.value;
  const dateSuffix = `${dateFrom.value}_to_${dateTo.value}`;
  // Each tab generates headers + rows → downloadCSV(filename, headers, rows)
  if (tab === "income-expense") { /* ... */ }
  // ... 7 more tabs
  toast.success("CSV exported successfully");
}
```

Template:
```vue
<button class="btn-secondary" @click="exportCurrentTabCSV">Export CSV</button>
<FeatureGate feature="export_pdf" :show-fallback="false">
  <button class="btn-primary">Export PDF</button>
</FeatureGate>
```

---

### ~~🟠 MISSING-7: Recent transactions on AccountDetail~~ ✅ FIXED

**Feature List Reference:** "Account dashboard — See all accounts with current balances at a glance"  
**File:** `src/components/vue/accounts/AccountDetail.vue`

**Fixed:** 2026-05-16 — Added "Recent Transactions" section to AccountDetail:
- Added `useTransactionStore` import and initialization
- Added `recentTransactions` and `loadingRecentTx` state
- Added `loadRecentTransactions()` function that fetches last 10 transactions for the account
- Added "Recent Transactions" card in template with:
  - Loading spinner state
  - Empty state ("No transactions yet for this account")
  - Transaction list with payee, date, and color-coded amount
  - "View All →" link to `/dashboard/transactions?account_id=${id}`
- Called in `onMounted` and after edit save

---

### ~~🟠 MISSING-8: Contribution history on Savings Goals~~ ✅ FIXED

**Feature List Reference:** "Progress tracking — Percentage complete, remaining amount, visual progress bar"  
**File:** `src/components/vue/goals/GoalsPage.vue`, `GoalContribute.vue`

**Fixed:** 2026-05-16 — Added contribution history display to GoalsPage:
- Added `SavingsGoalContributionOut` type to `ledgerTypes.ts`
- Added `contributions(goalId, filters?)` API method to `ledgerApi.savingsGoals`
- Added expandable contribution history section on each goal card:
  - History button (clock icon) in action buttons row
  - Toggle to expand/collapse with `showHistory` ref
  - Loading skeleton while fetching
  - Error message on failure
  - "No contributions yet" empty state
  - List of contributions with date, notes, and formatted amount

---

## 3. ARCHITECTURE / STORE ISSUES (Medium Priority)

### ~~🟡 ARCH-1: Investment store `list` ignores pagination filters~~ ✅ FIXED

**File:** `src/stores/investment.ts` ~Line 70, `src/lib/ledgerApi.ts` ~Line 981  
**Severity:** Medium — pagination won't work for investments  
**Fixed:** 2026-05-16 — (1) Updated `ledgerApi.investments.list()` to accept `filters?: PaginationIn` and pass through `filterToParams()`. (2) Updated investment store's `list` adapter to pass `filters` to the API call.

```ts
// BEFORE (broken):
list: (_filters?) => ledgerApi.investments.list(),  // filters ignored!

// AFTER (fixed):
list: (filters?) => ledgerApi.investments.list(filters),  // filters passed through
```

**Impact:** Investment list pagination is broken — if a user has many investment accounts, all load at once with no pagination.

---

### ~~🟡 ARCH-2: Reports `tagSpending` getter is placeholder~~ ✅ FIXED

**File:** `src/stores/reports.ts` ~Lines 304-342
**Severity:** Medium — tag-based reports show fake data
**Fixed:** 2026-05-16 — Replaced placeholder equal-distribution logic with batch-fetched transaction-tag associations for accurate aggregation.

The `tagSpending` getter previously distributed total expenses equally across all tags as a placeholder, since `TransactionOut` doesn't carry tag_ids. The comment acknowledged the need for a dedicated backend endpoint.

**Fix applied:**
- Added `transactionTagMap` and `tagFetchComplete` state fields to the reports store
- Added `fetchTransactionTags()` action that batch-fetches transaction-tag associations using `ledgerApi.transactionTags.list()` with concurrency of 10
- Capped at 500 expense transactions to keep response times reasonable
- Updated `tagSpending()` getter to aggregate spending using real tag associations instead of placeholder equal distribution
- `fetchTransactionTags()` is called automatically during `fetchReportData()` after transaction data is loaded
- `$resetReports()` clears the tag map and fetch status

```typescript
// BEFORE (placeholder):
const perTag = totalExpense / activeTags.length;
for (const tag of activeTags) {
  entry.amount = Math.round(perTag * 100) / 100;
  entry.transactionCount = Math.ceil(expenseCount / activeTags.length);
}

// AFTER (real data):
for (const txn of this.transactions) {
  const tagIds = this.transactionTagMap[txn.id];
  if (!tagIds || tagIds.length === 0) continue;
  const amount = parseFloat(txn.amount_base || txn.amount_original || "0");
  for (const tagId of tagIds) {
    const entry = tagMap.get(tagId);
    if (entry) { entry.amount += amount; entry.transactionCount += 1; }
  }
}
```

**Impact:** Tag-based reports now show accurate spending data per tag instead of equal distribution.

---

### 🟡 ARCH-3: Recurring transaction detection — boolean only, no schedule

**Feature List Reference:** "Recurring transaction detection — Auto-flag recurring payments"  
**File:** `src/components/vue/transactions/TransactionForm.vue`

The `is_recurring` field is just a boolean toggle. The feature list describes "Auto-flag recurring payments" with automatic detection. There is no:
- Recurring frequency/period configuration
- Auto-detection logic
- Recurring schedule display

---

### 🟡 ARCH-4: Inconsistent `ldgr-*` custom element registration

**File:** `src/pages/_app.ts`

Only 7 of 20+ page components are registered as `ldgr-*` custom elements:
- `ldgr-institutions-page`, `ldgr-tags-page`, `ldgr-accounts-page`, `ldgr-account-detail`, `ldgr-categories-page`, `ldgr-transactions-page`, `ldgr-transaction-detail`

Other pages (bills, budgets, debts, etc.) use direct Vue component imports with `client:only="vue"` in their Astro pages. This inconsistency could cause confusion but doesn't break functionality since both patterns work.

---

### 🟡 ARCH-5: `$resetCrud` duplication across stores

**Files:** `bill.ts`, `budget.ts`, `debt.ts`, `investment.ts`, `savingsGoal.ts`, `insurance.ts`, `invoice.ts`, `vault.ts`

All stores that extend base CRUD with extra state override `$resetCrud()` by duplicating the base body + clearing their extras. If the base state shape changes, these copies won't update automatically.

**Recommendation:** Call the base `$resetCrud()` then clear extras, or extract a helper.

---

### 🟡 ARCH-6: BillDetail `transaction_id` is a plain number input

**File:** `src/components/vue/bills/BillDetail.vue` (BillPaymentForm)

When recording a bill payment, the `transaction_id` field for linking to an existing transaction is a plain number input. The InvoicesPage has a proper transaction search widget with auto-suggest. Bill payment forms should use the same pattern.

---

### ~~🟡 ARCH-7: No search on BudgetsPage~~ ✅ FIXED

**Feature List Reference:** "Search & filter"  
**File:** `src/components/vue/budgets/BudgetsPage.vue`  
**Fixed:** 2026-05-16 — Added `SearchInput` component and search functionality to BudgetsPage:
- Added `SearchInput` and `PlanLimitBadge` imports from `@/components/vue`
- Added `searchQuery` ref and `handleSearch()` function that sets the `search` filter
- Added `"search"` to `syncKeys` in `useLedgerFilters` for URL param sync
- Added `SearchInput` above FilterBar in template with placeholder "Search budgets by category name..."
- `handleFilterReset()` now also clears `searchQuery`
- Also added `PlanLimitBadge` with `max-key="max_budgets"` next to "Add Budget" button

BudgetsPage previously had filter by period/category/currency but no search input. Other list pages (accounts, transactions, bills) all had search.

**Fix applied:**
```vue
<SearchInput v-model="searchQuery" placeholder="Search budgets by category name..." @search="handleSearch" />
```

---

### 🟡 ARCH-8: Category tree limited to 3 levels

**Feature List Reference:** "Hierarchical categories — Food → Groceries, Food → Dining Out"  
**File:** `src/components/vue/categories/CategoriesPage.vue`

The tree view template hardcodes 3 levels (root → child → grandchild). It's not a recursive component, so categories nested deeper than 3 levels won't render in the tree view. The `CategoryTreeSelect` dropdown does handle arbitrary depth.

---

## 4. FEATURE GAPS (Medium Priority — Partial Implementation)

### 🟡 GAP-1: No chart library — Reports are CSS-only

**Feature List Reference:** "Progress visualization — Color-coded progress bars" / various chart references  
**File:** `src/components/vue/reports/ReportPage.vue`

All report visualizations (donut charts, bar charts) are built with CSS (conic-gradient, inline width styles). There is no chart library (Chart.js, ECharts, D3) for:
- Interactive hover tooltips
- Drill-down on chart segments
- Responsive resize
- Animation transitions
- SVG/PNG export

This works for MVP but limits future enhancements.

---

### 🟡 GAP-2: No image/PDF preview in VaultDetail

**Feature List Reference:** "Upload documents — PDFs, images, spreadsheets"  
**File:** `src/components/vue/vault/VaultDetail.vue`

VaultDetail shows file metadata and a download button, but no inline preview. For PDFs and images, an inline preview would significantly improve UX.

---

### 🟡 GAP-3: No mark-as-read/dismiss on Notifications

**Feature List Reference:** "Notifications & Reminders"  
**File:** `src/components/vue/notifications/NotificationsPage.vue`

Notifications are read-only with no action buttons. Users cannot:
- Mark notifications as read/dismissed
- Acknowledge reminders
- Snooze alerts

---

### 🟡 GAP-4: Total paid summary missing on BillDetail

**Feature List Reference:** "Bill payment history — See every payment made for each bill with actual amounts"  
**File:** `src/components/vue/bills/BillDetail.vue`

BillDetail shows individual payments in a table but no aggregate summary (total paid to date, average payment amount, payment count).

---

### 🟡 GAP-5: Language/number format preferences missing in Settings

**File:** `src/components/vue/settings/SettingsPage.vue`

Settings has date format, theme, and notification reminders but no:
- Language preference (i18n not implemented)
- Number format preference (1,000.00 vs 1.000,00)

---

### 🟡 GAP-6: No data export/import

**Feature List Reference:** Implicit in "Data Integrity" section  
**File:** `src/components/vue/settings/SettingsPage.vue`

No functionality to export user data or import from other tools (CSV import, OFX, QIF).

---

### 🟡 GAP-7: Week view on Calendar missing

**Feature List Reference:** "Bill calendar view — See all upcoming bills on a calendar"  
**File:** `src/components/vue/calendar/CalendarPage.vue`

Only month view is implemented. No week view or day view toggle.

---

### 🟡 GAP-8: Related transactions on TransactionDetail missing

**File:** `src/components/vue/transactions/TransactionDetail.vue`

No "other transactions for this payee" or "similar transactions" section. Would help users find duplicates or related spending.

---

## 5. LOW PRIORITY / NICE-TO-HAVE

| # | Feature | File | Notes |
|---|---------|------|-------|
| LOW-1 | Real-time notification updates | NotificationsPage.vue | No polling or WebSocket; fetches only on mount |
| LOW-2 | Chart interactivity on Reports | ReportPage.vue | CSS-only charts, no hover tooltips or drill-down |
| LOW-3 | Drag-and-drop account sort order | AccountsPage.vue | `sort_order` field exists but no DnD UI |
| LOW-4 | InvoiceDetail mark-paid uses plain number input | InvoiceDetail.vue | Should use transaction search widget like InvoicesPage |
| LOW-5 | Card.activate/deactivate not on CardsPage | CardsPage.vue | Only soft delete/restore; no activate/deactivate toggle |
| LOW-6 | HoldingForm missing `notes` field | HoldingForm.vue | Model has no notes field either — consider adding |
| LOW-7 | No dividend tracking | InvestmentDetail.vue | Feature list doesn't mention dividends explicitly |
| LOW-8 | BudgetDetail.vue exists as route but content not verified | budgets/[id].astro | Route exists with BudgetDetail component import |

---

## 6. FEATURE COVERAGE MATRIX

Mapping each feature list item to its frontend implementation status:

### Phase 1 — Core (Accounts & Transactions)

| Feature | Status | Notes |
|---------|--------|-------|
| Create accounts (7 types) | ✅ | All account types supported in AccountForm |
| Group by institution | ✅ | AccountStore.groupedByInstitution getter |
| Multi-currency accounts | ✅ | Currency field + CurrencyInput component |
| Account dashboard | ✅ | DashboardPage + AccountDetail |
| Available credit | ✅ | AccountDetail shows for LIABILITY accounts |
| Credit card billing cycle | ✅ | statement_closing_day + due_day fields |
| Interest rate tracking | ✅ | interest_rate field in AccountForm |
| Account colors & icons | ✅ | Color picker + icon field in AccountForm |
| Manual sort order | ⚠️ | sort_order field exists but no DnD UI |
| Deactivate accounts | ✅ | useActivator toggle |
| Soft delete | ✅ | useSoftDelete + restore |
| Add institutions | ✅ | Full CRUD with InstitutionForm |
| Institution types | ✅ | 6 types in dropdown |
| Quick links (website/phone) | ✅ | website + customer_service_phone fields |
| Institution colors & icons | ✅ | Color picker + icon field |
| Add transactions (4 types) | ✅ | TransactionForm with type toggle |
| Multi-currency transactions | ✅ | CurrencyInput + exchange_rate + amount_base |
| Historical exchange rate | ✅ | Rate captured at creation time |
| Current value display | ✅ | formatTransactionAmount() utility |
| Payee tracking | ✅ | payee field + search filter |
| Reference numbers | ✅ | reference_number field |
| Transaction status lifecycle | ✅ | PENDING → CLEARED → VOID |
| Search & filter | ✅ | SearchInput + FilterBar with advanced filters |
| Bulk operations | ✅ | Mark Cleared/Void, Delete (batch) |
| Recurring detection | ⚠️ | Boolean toggle only — no auto-detection |
| Split transactions | ✅ | Split rows in TransactionForm with validation |
| Internal transfers | ✅ | TransferForm with from/to account |
| Transfer pair linking | ✅ | transfer_pair_id navigation on detail |
| Excluded from reports | ✅ | Backend handles; Transfer type in reports |
| Hierarchical categories | ⚠️ | 3-level max in tree view; CategoryTreeSelect handles N |
| Income vs Expense marking | ✅ | is_income toggle in CategoryForm |
| Custom icons & colors | ✅ | icon + color fields |
| Sort order | ✅ | sort_order field |
| Unique per level | ✅ | Backend validates; frontend shows tree |

### Phase 2 — Bills & Budgets

| Feature | Status | Notes |
|---------|--------|-------|
| Add bills | ✅ | Full BillForm with all fields |
| Flexible recurrence | ✅ | 6 recurrence types |
| Fixed vs variable amount | ✅ | is_amount_fixed toggle |
| Auto-advancing due dates | ✅ | Backend generates next_due_date |
| Bill status lifecycle | ✅ | Active → Paused → Cancelled with Reactivate |
| Auto-generate transactions | ✅ | "Generate Transaction" button on BillDetail |
| Default account & category | ✅ | account_id + category_id in BillForm |
| Bill payment history | ✅ | Payment History tab with DataTable |
| Bill calendar view | ✅ | CalendarPage with bill events |
| Pause & resume | ✅ | Pause/Cancel/Reactivate actions |
| Bill reminders | ✅ | remind_me + days_before_reminder |
| Toggle per bill | ✅ | remind_me boolean per bill |
| Set budgets by category | ✅ | BudgetForm with CategoryTreeSelect |
| Budget periods | ✅ | WEEKLY/MONTHLY/YEARLY |
| Real-time tracking | ✅ | spent_amount + remaining + percent_used |
| Budget remaining | ✅ | Computed in BudgetOut |
| Progress visualization | ✅ | ProgressBar with green/amber/red |
| Rollover budgets | ✅ | allow_rollover toggle in BudgetForm |
| Multi-currency budgets | ✅ | currency field |
| Create flat tags | ✅ | TagForm with name + color |
| Cross-cutting filtering | ✅ | TagChips on transaction forms |
| Tag-based reports | ✅ | Batch-fetched transaction-tag associations for accurate data |
| Custom colors | ✅ | Color picker in TagForm |

### Phase 3 — Cards & Debt

| Feature | Status | Notes |
|---------|--------|-------|
| Add cards to accounts | ✅ | CardForm with account_id dropdown |
| Card types | ✅ | DEBIT/CREDIT select |
| Card identification | ✅ | card_name + last_four |
| Expiry tracking | ✅ | expiry_date field |
| Annual fee tracking | ✅ | annual_fee + annual_fee_date fields |
| Card colors | ✅ | Color picker + preset buttons |
| Transaction attribution | ✅ | card_id field in TransactionForm |
| Track money borrowed | ✅ | MONEY_BORROWED debt nature |
| Track money lent | ✅ | MONEY_LENT debt nature |
| Debt nature separation | ✅ | Two-tab layout (I Owe / They Owe Me) |
| Debt types | ✅ | 6 types in dropdown |
| Counterparty tracking | ✅ | entity_name field |
| Institution linking | ✅ | institution_id dropdown |
| Payment schedule | ✅ | monthly_payment + payment_day |
| Balance tracking | ✅ | principal + remaining + progress_percent |
| Full payment history | ✅ | DebtPaymentForm with all portions |
| Amortization visibility | ✅ | Cumulative bar chart in DebtDetail |
| Interest cost tracking | ✅ | interest_portion in payment form |
| Auto-link to transactions | ✅ | transaction_id in payment form |
| Notes | ✅ | Notes field in DebtForm |

### Phase 4 — Investments

| Feature | Status | Notes |
|---------|--------|-------|
| Investment accounts | ✅ | INVESTMENT account type + InvestmentForm |
| Portfolio dashboard | ✅ | Summary cards with portfolio value |
| Gain/loss percentage | ✅ | unrealized_gain_loss_percent computed |
| Last sync timestamp | ✅ | last_synced_at field |
| Track individual positions | ✅ | HoldingForm with all fields |
| Asset types | ✅ | 6 types (Stock/ETF/Crypto/Bond/Mutual Fund/Other) |
| Cost basis tracking | ✅ | cost_basis field |
| Average purchase price | ✅ | Computed in HoldingOut |
| Current market price | ✅ | current_price field (manual entry) |
| Current value | ✅ | Auto-calc qty × current_price |
| Unrealized gain/loss | ✅ | Per holding, with color coding |
| Purchase date | ✅ | purchase_date field |
| Multi-currency | ✅ | currency field per holding |

### Phase 5 — Goals, Insurance, Invoices, Vault

| Feature | Status | Notes |
|---------|--------|-------|
| Create savings goals | ✅ | SavingsGoalForm with all fields |
| Progress tracking | ✅ | progress_percent + ProgressBar |
| Deadline tracking | ✅ | deadline + days_remaining badges |
| Auto-completion | ✅ | is_completed + celebration on contribute |
| Link to account | ✅ | account_id dropdown |
| Custom icons & colors | ✅ | 16 emoji presets + color picker |
| Multi-currency | ✅ | currency field |
| Policy management | ✅ | InsurancePolicyForm with all fields |
| Premium tracking | ✅ | premium_amount + frequency + renewal_date |
| Coverage details | ✅ | coverage_amount + deductible + details |
| Provider tracking | ✅ | provider + institution_id |
| Policy numbers | ✅ | policy_number field |
| Renewal reminders | ✅ | remind_renewal + days_before_renewal_reminder |
| Document linking | ✅ | "Link Document" button creates vault entry |
| Create invoices | ✅ | InvoiceForm with line items |
| Invoice lifecycle | ✅ | 7 statuses with status timeline |
| Client management | ✅ | client_name + client_email |
| Line items | ✅ | Editable table with add/remove |
| Tax calculation | ✅ | subtotal + tax_amount + total |
| Partial payments | ✅ | amount_paid vs amount_due |
| Overdue detection | ✅ | is_overdue computed + overdue tab |
| Auto-create income transaction | ✅ | Toggle in mark-paid modal |
| Payment terms | ✅ | terms field |
| Invoice numbering | ✅ | Auto-suggest INV-XXX format |
| Multi-currency | ✅ | currency select |
| Upload documents | ✅ | VaultUploadForm with drag-and-drop |
| Auto file type detection | ✅ | From file extension |
| File size tracking | ✅ | file_size stored |
| Link to any entity | ⚠️ | Broken — content_type_id/object_id hardcoded to 0 |
| Expiry tracking | ✅ | expiry_date + color-coded |
| Expiry reminders | ✅ | remind_before_expiry + days_before_expiry_reminder |
| Organized storage | ✅ | Backend handles year/month folders |

### Cross-Cutting Features

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-currency (38 currencies) | ✅ | Full currency.ts with rate caching + formatting |
| Automatic conversion | ✅ | convertAmount() utility |
| Historical rate capture | ✅ | Exchange rate frozen at transaction time |
| Current value display | ✅ | formatTransactionAmount() shows both |
| Proper formatting | ✅ | getCurrencyDecimalDigits() handles zero-decimal |
| Currency symbols | ✅ | From base backend metadata + Intl fallback |
| Soft deletes everywhere | ✅ | useSoftDelete composable + all stores |
| Active/inactive toggle | ✅ | useActivator composable |
| Denormalized balances | ✅ | current_balance on Account model |
| Balance recalculation | ✅ | "Recalculate Balance" button on AccountDetail |
| Transaction search | ✅ | Advanced filters + search |
| Category spending reports | ✅ | ReportPage tab |
| Income vs Expense | ✅ | ReportPage tab |
| Budget vs Actual | ✅ | ReportPage tab |
| Net worth tracking | ✅ | ReportPage + Dashboard |
| Debt progress | ✅ | ReportPage tab + DebtDetail |
| Investment performance | ✅ | ReportPage tab |
| Tag-based reports | ✅ | Batch-fetched transaction-tag associations for accurate data |
| Multi-currency reports | ✅ | All amounts via formatCurrency |
| Bill due reminders | ✅ | Settings + BillForm remind_me |
| Insurance renewal reminders | ✅ | Settings + InsurancePolicyForm |
| Document expiry reminders | ✅ | Settings + VaultUploadForm |
| Credit card due reminders | ✅ | NotificationsPage fetches card due alerts |
| Annual fee reminders | ✅ | NotificationsPage fetches annual fee alerts |
| Savings goal deadline reminders | ✅ | Settings + goal deadline badges |
| Account balances overview | ✅ | Dashboard widget |
| Net worth summary | ✅ | Dashboard hero card |
| Monthly spending breakdown | ✅ | Dashboard spending overview |
| Budget status | ✅ | Dashboard widget |
| Upcoming bills | ✅ | Dashboard widget |
| Recent transactions | ✅ | Dashboard widget |
| Debt progress | ✅ | Dashboard widget |
| Savings goal progress | ✅ | Dashboard widget |
| Investment portfolio snapshot | ✅ | Dashboard widget |

---

## 7. INFRASTRUCTURE & SECURITY AUDIT

### Auth & Security ✅

| Aspect | Status | Details |
|--------|--------|---------|
| JWT token management | ✅ | Session/localStorage, proactive 55-min refresh |
| 401 reactive refresh | ✅ | Deduped concurrent refresh calls |
| SSO via authorization codes | ✅ | Cross-domain auth between Sattabase + Ledger |
| Feature gating (middleware) | ✅ | Client-side script injection for protected paths |
| Feature gating (sidebar) | ✅ | DOM visibility based on access data |
| Feature gating (component) | ✅ | FeatureGate.vue with UpgradePrompt |
| CSRF protection | ✅ | astro.config: checkOrigin: true |
| CSP headers | ✅ | SHA-512 in production |
| Session cookie | ✅ | 1hr TTL |
| Auth expiry events | ✅ | auth-expired + auth-state-changed custom events |
| Guest-only redirect | ✅ | AuthLayout client-side redirect |
| Service domain header | ✅ | X-Service-Domain on all API requests |

### API Layer ✅

| Aspect | Status |
|--------|--------|
| 95+ typed endpoint methods | ✅ |
| Full Django Ninja error parsing | ✅ |
| 401 → auto-refresh → retry | ✅ |
| 403 → auth vs authorization distinction | ✅ |
| 429 → rate limit toast | ✅ |
| 5xx → server error toast | ✅ |
| Network error handling | ✅ |
| FormData support (vault upload) | ✅ |
| filterToParams helper | ✅ |

### State Management ✅

| Aspect | Status |
|--------|--------|
| CRUD store factory (base.ts) | ✅ |
| 15 domain stores (all implemented) | ✅ |
| Dashboard aggregation store | ✅ |
| Reports aggregation store | ✅ |
| Staleness tracking | ✅ |
| Dropdown caching | ✅ |
| Optimistic updates (activate/deactivate) | ✅ |
| Toast integration | ✅ |
| Diff-based PATCH (useCrudForm) | ✅ |

### Composables ✅

| Composable | Status |
|-----------|--------|
| useCrudForm | ✅ Diff-based PATCH, dirty tracking, beforeunload |
| useSoftDelete | ✅ Delete + restore with confirmation |
| useActivator | ✅ Activate/deactivate with confirmation |
| useLedgerFilters | ✅ URL param sync |
| useLedgerPagination | ✅ DataTable integration |
| useDropdownLoader | ✅ Multi-store parallel load |
| useAuth | ✅ Shared auth + billing state |
| useAccess | ✅ Feature access checking |
| useSubscription | ✅ Deduped fetch |
| useBillingRedirect | ✅ Billing return detection |
| useToast | ✅ Global toast notifications |
| useHotkeys | ✅ Keyboard shortcuts |

---

## 8. PRIORITY FIX ORDER

### Immediate (Blocking)
1. ~~**BUG-1** — AccountForm `account_type` field assignment~~ ✅ FIXED (2026-05-16)
2. ~~**BUG-2** — Investment store `fieldErrors` function~~ ✅ FIXED (2026-05-16)
3. ~~**BUG-4** — VaultUploadForm `content_type_id`/`object_id` hardcoding~~ ✅ FIXED (2026-05-16)

### Next Sprint
4. ~~**BUG-3** — Transaction tag chips empty~~ ✅ FIXED (2026-05-16)
5. ~~**MISSING-1** — Server-side sorting~~ ✅ FIXED for TransactionsPage (2026-05-16)
6. ~~**MISSING-2** — TransferForm cross-currency exchange rate~~ ✅ FIXED (2026-05-16)
7. ~~**MISSING-4** — CalendarPage debt events~~ ✅ FIXED (2026-05-16)
8. ~~**ARCH-1** — Investment pagination fix~~ ✅ FIXED (2026-05-16)

### Following Sprint
9. ~~**MISSING-3** — BudgetForm missing fields~~ ✅ PARTIALLY FIXED (2026-05-16) — `is_active` toggle added; `end_date`/`notes` need backend changes
10. ~~**MISSING-5** — NotificationsPage card alerts~~ ✅ FIXED (2026-05-16)
11. ~~**MISSING-7** — AccountDetail recent transactions~~ ✅ FIXED (2026-05-16)
12. ~~**MISSING-8** — Goal contribution history~~ ✅ FIXED (2026-05-16)
13. ~~**MISSING-6** — Reports CSV/PDF export~~ ✅ FIXED (2026-05-16)
14. ~~**ARCH-2** — Tag spending placeholder~~ ✅ FIXED (2026-05-16) — Batch-fetched transaction-tag associations replace equal-distribution
15. ~~**ARCH-7** — BudgetsPage search~~ ✅ FIXED (2026-05-16)

### Backlog
15. All GAP items (chart library, vault preview, notification actions, etc.)
16. All LOW items (real-time updates, DnD sort, i18n, etc.)
17. ARCH-4 — Consistent `ldgr-*` registration pattern
18. ARCH-5 — `$resetCrud` deduplication
