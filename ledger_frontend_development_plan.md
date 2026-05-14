# Ledger Frontend — Development Plan

> **Project**: Sattabase Ledger — Sister Domain Frontend  
> **Stack**: Astro 6 + Vue 3 + Tailwind 4 + Pinia  
> **Backend API**: 95 endpoints across 13 domain controllers  
> **Source Documents**: ledger-feature-list.md, ledger-database-plan.md, implemented models/schemas/controllers  
> **Date**: May 2026  

---

## Table of Contents

1. [Current State Assessment](#1-current-state-assessment)
2. [Architecture & Patterns](#2-architecture--patterns)
3. [Phase 0 — Foundation Layer](#3-phase-0--foundation-layer)
4. [Phase 1 — Core: Accounts & Transactions ✅ DONE](#4-phase-1--core-accounts--transactions-✅-done)
5. [Phase 2 — Bills & Budgets ✅ DONE](#5-phase-2--bills--budgets-✅-done)
6. [Phase 3 — Cards & Debt](#6-phase-3--cards--debt)
7. [Phase 4 — Investments](#7-phase-4--investments)
8. [Phase 5 — Goals, Insurance, Invoices, Vault](#8-phase-5--goals-insurance-invoices-vault)
9. [Phase 6 — Dashboard & Reporting](#9-phase-6--dashboard--reporting)
10. [Phase 7 — Polish & Production](#10-phase-7--polish--production)
11. [File Structure Map](#11-file-structure-map)
12. [Component Catalog](#12-component-catalog)
13. [API Integration Map](#13-api-integration-map)
14. [Pinia Store Catalog](#14-pinia-store-catalog)
15. [Page & Route Catalog](#15-page--route-catalog)
16. [Implementation Priority Matrix](#16-implementation-priority-matrix)
17. [Cross-Cutting Concerns](#17-cross-cutting-concerns)
18. [Testing Strategy](#18-testing-strategy)
19. [Risk & Mitigation](#19-risk--mitigation)

---

## 1. Current State Assessment

### 1.1 What's Built (Infrastructure Layer)

| Layer | Status | Details |
|-------|--------|---------|
| **Astro 6 + Vue 3** | ✅ Complete | SSR with Vue islands, `client:only="vue"` for interactive components |
| **Tailwind 4 Theme** | ✅ Complete | Navy/Cyan/Warm palette, component classes (`btn-primary`, `card`, `input-field`), dark mode, glass morphism, animations |
| **API Client** | ✅ Complete | `apiClient.get/post/put/patch/del<T>()`, JWT Bearer injection, auto-refresh on 401, deduped refresh, `X-Service-Domain` header, Django Ninja error parsing |
| **Auth Flow** | ✅ Complete | Login/logout, SSO authorization code exchange, token persistence (sessionStorage/localStorage), `requireAuth()`/`checkAuth()` guards |
| **Composables** | ✅ Complete | `useAuth` (shared user state + profile fetch), `useAccess` (feature gating), `useSubscription` (subscription state), `useBillingRedirect` (cross-domain billing) |
| **Currency Utils** | ✅ Complete | `formatCurrency()`, `convertAmount()`, `getCurrencySymbol()`, metadata from backend cached in localStorage, rates in sessionStorage |
| **Timezone Utils** | ✅ Complete | `formatInUserTimezone()`, `formatDateShort()`, `formatDateTime()`, `formatRelativeTime()`, user timezone cached |
| **Layouts** | ✅ Complete | `BaseLayout.astro` (HTML shell, fonts, dark mode), `DashboardLayout.astro` (sidebar, top bar, user info, sign-out, theme toggle) |
| **Pages** | ⚠️ 2 only | `/auth/login` and `/dashboard` (placeholder with plan/access/billing cards) |
| **Components** | ⚠️ 2 only | `LoginForm.vue` and `LoadingSpinner.astro` |

### 1.2 What's Missing (Everything Domain-Specific)

- **0 Pinia stores** — declared in `_app.ts` but no store files exist
- **0 ledger API calls** — frontend only calls Sattabase Core (`/auth/login`, `/billing/auth/me`), not ledgerbackend (`localhost:8087`)
- **0 domain pages** — no transactions, accounts, bills, budgets, etc.
- **0 domain Vue components** — no forms, tables, charts, modals for ledger features
- **0 Zod validators** — declared in deps but not used
- **0 shared composables** — no `useLedgerApi`, `usePagination`, `useFilters`, etc.

### 1.3 Backend API Ready for Consumption

All 95 endpoints are implemented and follow consistent patterns:

| Pattern | Endpoints | Description |
|---------|-----------|-------------|
| **CRUD** | List → Get → Create → Update → Delete | Every domain entity |
| **Soft Delete** | `DELETE /{id}` + `POST /{id}/restore` | All entities except Tags, TransactionTags |
| **Active/Inactive** | `POST /{id}/activate` + `POST /{id}/deactivate` | Most entities except Tags, TransactionTags |
| **Dropdown** | `GET /dropdown` | Institutions, Accounts, Categories, Tags, Cards |
| **Dashboard** | `GET /recent`, `GET /upcoming`, `GET /summary`, `GET /overview`, `GET /expiring`, `GET /renewals`, `GET /overdue` | Lightweight lists for dashboard widgets |
| **Sub-resources** | Bills→Payments, Debts→Payments, Investments→Holdings, Invoices→LineItems, Transactions→Splits, Transactions→Tags | Nested CRUD |
| **Special Actions** | Transfer, Recalculate-Balance, Bill-Generate, Bill-Pause/Cancel/Reactivate, Savings-Contribute, Invoice-Mark-Paid | Domain-specific operations |

---

## 2. Architecture & Patterns

### 2.1 Astro + Vue Islands Architecture

```
Astro Page (.astro)                  Vue Island (.vue)
┌─────────────────────┐             ┌──────────────────┐
│ Server-rendered HTML │──client:──▶ │ Interactive SPA  │
│ SEO-friendly shell   │  only="vue" │ Full reactivity  │
│ Static layout        │             │ Pinia stores     │
│ CSS-loaded           │             │ Event handlers   │
└─────────────────────┘             └──────────────────┘
```

**Rules:**
- Astro pages handle: routing, layout, meta tags, server-side data prefetch
- Vue islands handle: forms, tables, modals, charts, interactive state
- Use `client:only="vue"` for authenticated pages (no SSR needed — data is user-specific)
- Use `client:visible` for below-fold interactive components
- Use `client:idle` for non-critical interactive widgets

### 2.2 State Management — Pinia Stores

Migration from composable singletons to Pinia stores for ledger domain state. Composables remain for Sattabase Core concerns (auth, access, subscription).

**Why Pinia over composables for domain state:**
- DevTools integration for time-travel debugging
- `$reset()` for form/component cleanup
- SSR hydration support
- Computed getters + actions pattern matches API call flow
- Store-to-store composition (`useAccountStore` inside `useTransactionStore`)

### 2.3 API Integration — Ledger API Service

New `src/lib/ledgerApi.ts` that wraps `apiClient` with ledgerbackend-specific configuration:

```typescript
// Base URL: localhost:8087/api/v1/ (from sattabase.config.ts)
// All calls inherit JWT auth + X-Service-Domain from apiClient
// Typed request/response using schema-mirroring interfaces
```

### 2.4 Component Design System

**Existing Tailwind classes:**
- `.btn-primary` (cyan), `.btn-secondary`, `.btn-destructive` (debit red), `.btn-ghost`
- `.input-field`, `.card`, `.label-text`, `.focus-ring`, `.skeleton`
- `.bg-navy-gradient`, `.bg-cyan-gradient`, `.bg-warm-gradient`
- `.glass-navy`, `.glass-white`

**New reusable components to build** (see Section 12 for full catalog):
- `DataTable` — sortable, paginated, filterable table
- `Modal` — confirmation, form, detail view
- `FormBuilder` — auto-generate forms from schemas
- `StatusBadge` — colored status indicators
- `ProgressBar` — budget/savings/goal progress
- `EmptyState` — "no data" illustrations
- `ConfirmDialog` — destructive action confirmation
- `CurrencyInput` — amount + currency code selector
- `DateRangePicker` — from/to with presets
- `CategoryTree` — hierarchical tree selector

### 2.5 Page Layout Convention

Every dashboard page follows this structure:

```
DashboardLayout.astro
├── Page Header (title + description + action button)
├── Filter Bar (search, date range, status, type filters)
├── Content Area (DataTable, Card Grid, or custom layout)
└── Pagination (limit/offset with total count)
```

---

## 3. Phase 0 — Foundation Layer

> **Goal**: Build the shared infrastructure that every feature page depends on — Pinia stores, API service, types, reusable components. Zero user-visible features.

### 3.1 TypeScript Types — `src/lib/ledgerTypes.ts` ✅ DONE

Mirror all 80+ backend schema classes as TypeScript interfaces. Organized by domain to match backend structure:

```typescript
// ── Common ──
interface PaginatedResponse<T> { items: T[]; total: number; limit: number; offset: number }
interface MessageOut { message: string }
interface BulkResponse { success: number; failed: number; errors?: string[] }

// ── Core ──
interface Institution { id: number; user_id: number; name: string; institution_type: string; ... }
interface InstitutionCreate { name: string; institution_type?: string; ... }
interface InstitutionUpdate { name?: string; ... }
interface Account { id: number; name: string; institution_id: number; account_type: string; currency: string; current_balance: string; ... }
interface AccountCreate { name: string; institution_id: number; account_type: string; currency: string; ... }
interface Transaction { id: number; date: string; account_id: number; transaction_type: string; amount_original: string; ... }
interface TransactionCreate { date: string; account_id: number; transaction_type: string; amount_original: number; ... }
interface TransactionSplit { id: number; transaction_id: number; category_id: number; amount: string; ... }
interface TransferCreate { from_account_id: number; to_account_id: number; amount: number; ... }
interface TransferOut { outflow: Transaction; inflow: Transaction }

// ── Categories ──
interface Category { id: number; name: string; parent_id: number | null; is_income: boolean; icon: string; color: string; ... }
interface CategoryTree { id: number; name: string; children: CategoryTree[]; ... }
interface Tag { id: number; name: string; color: string; ... }

// ── Bills, Budgets, Cards, Debt, Investments, Goals, Insurance, Invoices, Vault ──
// ... (full type definitions for every schema)
```

**Estimated count**: ~80 interfaces/types → **Actual: 85+ interfaces/types** (completed)

**Time estimate**: 1 day → **Completed**

### 3.2 Ledger API Service — `src/lib/ledgerApi.ts` ✅ DONE

Thin typed wrapper around `apiClient` for all 95 ledgerbackend endpoints:

```typescript
class LedgerApiService {
  private baseUrl = config.ledgerApiUrl  // new config entry: localhost:8087/api/v1

  // ── Institutions ──
  listInstitutions(params?: InstitutionFilter): Promise<PaginatedResponse<Institution>>
  getInstitutionDropdown(): Promise<Institution[]>
  getInstitution(id: number): Promise<Institution>
  createInstitution(data: InstitutionCreate): Promise<Institution>
  updateInstitution(id: number, data: InstitutionUpdate): Promise<Institution>
  deleteInstitution(id: number): Promise<MessageOut>
  restoreInstitution(id: number): Promise<MessageOut>
  activateInstitution(id: number): Promise<MessageOut>
  deactivateInstitution(id: number): Promise<MessageOut>

  // ── Accounts ──
  listAccounts(params?: AccountFilter): Promise<PaginatedResponse<Account>>
  getAccountDropdown(): Promise<Account[]>
  getAccount(id: number): Promise<Account>
  createAccount(data: AccountCreate): Promise<Account>
  updateAccount(id: number, data: AccountUpdate): Promise<Account>
  recalculateBalance(id: number): Promise<BalanceRecalculateOut>
  deleteAccount(id: number): Promise<MessageOut>
  restoreAccount(id: number): Promise<MessageOut>
  activateAccount(id: number): Promise<MessageOut>
  deactivateAccount(id: number): Promise<MessageOut>

  // ── Transactions ──
  listTransactions(params?: TransactionFilter): Promise<PaginatedResponse<Transaction>>
  getRecentTransactions(limit?: number): Promise<Transaction[]>
  getTransaction(id: number): Promise<Transaction>
  createTransaction(data: TransactionCreate): Promise<Transaction>
  updateTransaction(id: number, data: TransactionUpdate): Promise<Transaction>
  createTransfer(data: TransferCreate): Promise<TransferOut>
  deleteTransaction(id: number): Promise<MessageOut>
  restoreTransaction(id: number): Promise<MessageOut>

  // ── Transaction Splits ──
  listSplits(transactionId: number): Promise<TransactionSplit[]>
  createSplit(transactionId: number, data: TransactionSplitCreate): Promise<TransactionSplit>
  updateSplit(transactionId: number, splitId: number, data: TransactionSplitUpdate): Promise<TransactionSplit>
  deleteSplit(transactionId: number, splitId: number): Promise<MessageOut>

  // ── Transaction Tags ──
  listTransactionTags(transactionId: number): Promise<TransactionTag[]>
  addTransactionTag(transactionId: number, data: TransactionTagCreate): Promise<TransactionTag>
  bulkSetTransactionTags(transactionId: number, data: TransactionTagBulkCreate): Promise<TransactionTagBulkOut>
  removeTransactionTag(transactionId: number, tagId: number): Promise<MessageOut>

  // ── Categories ──
  listCategories(params?: CategoryFilter): Promise<PaginatedResponse<Category>>
  getCategoryDropdown(): Promise<Category[]>
  getCategoryTree(): Promise<CategoryTree[]>
  getCategory(id: number): Promise<Category>
  createCategory(data: CategoryCreate): Promise<Category>
  updateCategory(id: number, data: CategoryUpdate): Promise<Category>
  deleteCategory(id: number): Promise<MessageOut>
  restoreCategory(id: number): Promise<MessageOut>
  activateCategory(id: number): Promise<MessageOut>
  deactivateCategory(id: number): Promise<MessageOut>

  // ── Tags ──
  listTags(params?: TagFilter): Promise<PaginatedResponse<Tag>>
  getTagDropdown(): Promise<Tag[]>
  getTag(id: number): Promise<Tag>
  createTag(data: TagCreate): Promise<Tag>
  updateTag(id: number, data: TagUpdate): Promise<Tag>
  deleteTag(id: number): Promise<MessageOut>
  restoreTag(id: number): Promise<MessageOut>

  // ── Cards ──
  listCards(params?: CardFilter): Promise<PaginatedResponse<Card>>
  getCardDropdown(): Promise<Card[]>
  getCard(id: number): Promise<Card>
  createCard(data: CardCreate): Promise<Card>
  updateCard(id: number, data: CardUpdate): Promise<Card>
  deleteCard(id: number): Promise<MessageOut>
  restoreCard(id: number): Promise<MessageOut>
  activateCard(id: number): Promise<MessageOut>
  deactivateCard(id: number): Promise<MessageOut>

  // ── Bills ──
  listBills(params?: BillFilter): Promise<PaginatedResponse<Bill>>
  getUpcomingBills(days?: number): Promise<Bill[]>
  getBill(id: number): Promise<Bill>
  createBill(data: BillCreate): Promise<Bill>
  updateBill(id: number, data: BillUpdate): Promise<Bill>
  generateBillTransaction(id: number): Promise<BillGenerateTransactionOut>
  deleteBill(id: number): Promise<MessageOut>
  restoreBill(id: number): Promise<MessageOut>
  pauseBill(id: number): Promise<MessageOut>
  cancelBill(id: number): Promise<MessageOut>
  reactivateBill(id: number): Promise<MessageOut>
  listBillPayments(billId: number): Promise<BillPayment[]>
  createBillPayment(billId: number, data: BillPaymentCreate): Promise<BillPayment>
  updateBillPayment(billId: number, paymentId: number, data: BillPaymentUpdate): Promise<BillPayment>

  // ── Debts ──
  listDebts(params?: DebtFacilityFilter): Promise<PaginatedResponse<DebtFacility>>
  getDebtSummary(): Promise<DebtSummary>
  getDebt(id: number): Promise<DebtFacility>
  createDebt(data: DebtFacilityCreate): Promise<DebtFacility>
  updateDebt(id: number, data: DebtFacilityUpdate): Promise<DebtFacility>
  deleteDebt(id: number): Promise<MessageOut>
  restoreDebt(id: number): Promise<MessageOut>
  activateDebt(id: number): Promise<MessageOut>
  deactivateDebt(id: number): Promise<MessageOut>
  listDebtPayments(debtId: number): Promise<DebtPayment[]>
  createDebtPayment(debtId: number, data: DebtPaymentCreate): Promise<DebtPayment>
  updateDebtPayment(debtId: number, paymentId: number, data: DebtPaymentUpdate): Promise<DebtPayment>

  // ── Budgets ──
  listBudgets(params?: BudgetFilter): Promise<PaginatedResponse<Budget>>
  getBudgetOverview(): Promise<Budget[]>
  getBudget(id: number): Promise<Budget>
  createBudget(data: BudgetCreate): Promise<Budget>
  updateBudget(id: number, data: BudgetUpdate): Promise<Budget>
  deleteBudget(id: number): Promise<MessageOut>
  restoreBudget(id: number): Promise<MessageOut>
  activateBudget(id: number): Promise<MessageOut>
  deactivateBudget(id: number): Promise<MessageOut>

  // ── Investments ──
  listInvestments(): Promise<PaginatedResponse<InvestmentAccount>>
  getInvestmentSummary(): Promise<InvestmentSummary>
  getInvestment(id: number): Promise<InvestmentAccount>
  createInvestment(data: InvestmentAccountCreate): Promise<InvestmentAccount>
  updateInvestment(id: number, data: InvestmentAccountUpdate): Promise<InvestmentAccount>
  deleteInvestment(id: number): Promise<MessageOut>
  restoreInvestment(id: number): Promise<MessageOut>
  listHoldings(investmentId: number): Promise<Holding[]>
  createHolding(investmentId: number, data: HoldingCreate): Promise<Holding>
  updateHolding(investmentId: number, holdingId: number, data: HoldingUpdate): Promise<Holding>
  deleteHolding(investmentId: number, holdingId: number): Promise<MessageOut>

  // ── Savings Goals ──
  listSavingsGoals(params?: SavingsGoalFilter): Promise<PaginatedResponse<SavingsGoal>>
  getSavingsGoalDashboard(): Promise<SavingsGoal[]>
  getSavingsGoal(id: number): Promise<SavingsGoal>
  createSavingsGoal(data: SavingsGoalCreate): Promise<SavingsGoal>
  updateSavingsGoal(id: number, data: SavingsGoalUpdate): Promise<SavingsGoal>
  contributeToGoal(id: number, data: SavingsContribution): Promise<SavingsContributionOut>
  deleteSavingsGoal(id: number): Promise<MessageOut>
  restoreSavingsGoal(id: number): Promise<MessageOut>
  activateSavingsGoal(id: number): Promise<MessageOut>
  deactivateSavingsGoal(id: number): Promise<MessageOut>

  // ── Insurance ──
  listInsurance(params?: InsurancePolicyFilter): Promise<PaginatedResponse<InsurancePolicy>>
  getInsuranceRenewals(days?: number): Promise<InsurancePolicy[]>
  getInsurance(id: number): Promise<InsurancePolicy>
  createInsurance(data: InsurancePolicyCreate): Promise<InsurancePolicy>
  updateInsurance(id: number, data: InsurancePolicyUpdate): Promise<InsurancePolicy>
  deleteInsurance(id: number): Promise<MessageOut>
  restoreInsurance(id: number): Promise<MessageOut>
  activateInsurance(id: number): Promise<MessageOut>
  deactivateInsurance(id: number): Promise<MessageOut>

  // ── Invoices ──
  listInvoices(params?: InvoiceFilter): Promise<PaginatedResponse<Invoice>>
  getOverdueInvoices(): Promise<Invoice[]>
  getInvoice(id: number): Promise<Invoice>
  createInvoice(data: InvoiceCreate): Promise<Invoice>
  updateInvoice(id: number, data: InvoiceUpdate): Promise<Invoice>
  markInvoicePaid(id: number, data: InvoiceMarkPaid): Promise<Invoice>
  deleteInvoice(id: number): Promise<MessageOut>
  restoreInvoice(id: number): Promise<MessageOut>
  listInvoiceLineItems(invoiceId: number): Promise<InvoiceLineItem[]>
  createInvoiceLineItem(invoiceId: number, data: InvoiceLineItemCreate): Promise<InvoiceLineItem>
  updateInvoiceLineItem(invoiceId: number, itemId: number, data: InvoiceLineItemUpdate): Promise<InvoiceLineItem>
  deleteInvoiceLineItem(invoiceId: number, itemId: number): Promise<MessageOut>

  // ── Vault ──
  listDocuments(params?: DocumentVaultFilter): Promise<PaginatedResponse<DocumentVault>>
  getExpiringDocuments(days?: number): Promise<DocumentVault[]>
  getDocument(id: number): Promise<DocumentVault>
  createDocument(data: FormData): Promise<DocumentVault>  // multipart upload
  updateDocument(id: number, data: DocumentVaultUpdate): Promise<DocumentVault>
  deleteDocument(id: number): Promise<MessageOut>
  restoreDocument(id: number): Promise<MessageOut>
  activateDocument(id: number): Promise<MessageOut>
  deactivateDocument(id: number): Promise<MessageOut>
}

export const ledgerApi = new LedgerApiService()
```

**Time estimate**: 2 days → **Completed**

> **Implementation note**: Instead of a single `LedgerApiService` class, the service is structured as **20 namespaced endpoint groups** (`institutions`, `accounts`, `transactions`, `splits`, `transactionTags`, `categories`, `tags`, `cards`, `bills`, `billPayments`, `debts`, `debtPayments`, `budgets`, `investments`, `holdings`, `savingsGoals`, `insurance`, `invoices`, `invoiceLineItems`, `vault`) exported as a unified `ledgerApi` object. This provides better tree-shaking and cleaner imports like `ledgerApi.institutions.list()`. The internal `ledgerRequest()` function shares the same JWT pool and 401-refresh logic as the core `apiClient` but targets `config.ledgerApiUrl` (localhost:8087). Total: **95+ endpoint methods** mapped 1:1 to backend controllers.

### 3.3 Configuration Update — `sattabase.config.ts` ✅ DONE

Add ledgerbackend API URL:

```typescript
ledgerApiUrl: import.meta.env.PUBLIC_LEDGER_API_URL || 'http://localhost:8087/api/v1'
```

### 3.4 Pinia Store Base — `src/stores/base.ts` ✅ DONE

Shared store patterns for CRUD operations — composable factories that domain stores spread into their own `defineStore()`:

```typescript
// ── State Interface ──
interface CrudStoreState<T, TFilter, TDropdown> {
  items: T[]
  current: T | null
  loading: boolean
  loadingAction: string          // 'fetchList' | 'create' | 'update' | etc.
  error: string | null
  fieldErrors: Record<string, string[]>  // Django Ninja validation errors
  total: number
  filters: TFilter
  dropdown: TDropdown[]
  dropdownLoaded: boolean
  listLoaded: boolean
  lastFetched: number | null     // staleness tracking (ms)
}

// ── Composable Factories ──
crudState<T, F, D>(defaultFilters?)   // → initial state object
crudGetters<T>(staleThreshold?)       // → activeItems, hasItems, hasError, isStale, totalPages, currentPage
crudActions<T, C, U, F>(config)       // → fetchList, fetchOne, fetchDropdown, refreshIfStale,
                                       //    create, update, remove, restore,
                                       //    activate, deactivate,
                                       //    clearError, clearCurrent, setFilters, resetFilters,
                                       //    setPage, invalidate, $resetCrud

// ── Convenience Factory ──
defineCrudStore<T, C, U, F, D>(config) // → full defineStore() result

// ── Error Utilities ──
extractErrorMessage(err)  // → string (handles ApiError, Django Ninja, Error, string)
extractFieldErrors(err)   // → Record<string, string[]>
isApiError(err)           // → type guard

// ── Usage Pattern ──
export const useXxxStore = defineStore('xxx', {
  state: () => ({
    ...crudState<XxxOut, XxxFilter, XxxListOut>(),
    // domain-specific extra state
  }),
  getters: {
    ...crudGetters<XxxOut>(),
    // domain-specific extra getters
  },
  actions: {
    ...crudActions<XxxOut, XxxCreate, XxxUpdate, XxxFilter>({
      api: { list, get, create, update, remove, restore, dropdown, activate, deactivate },
    }),
    // domain-specific extra actions
  },
});
```

**Key design decisions:**
- Composable spread pattern over class inheritance — Pinia-compatible, tree-shakeable
- Optimistic updates for activate/deactivate with rollback on error
- Dropdown caching with `dropdownLoaded` flag to avoid redundant API calls
- Staleness tracking via `lastFetched` timestamp + `refreshIfStale()` action
- Granular `loadingAction` string so UI can show per-action spinners
- Field-level error extraction for Django Ninja validation error format

### 3.5 Reusable Vue Components ✅ DONE

15 shared components built in `src/components/vue/` with barrel export `index.ts`:

| Component | Purpose | Key Props / Features |
|-----------|---------|----------------------|
| `DataTable.vue` | Sortable, paginated table | `columns`, `rows`, `loading`, `total`, `limit`, `offset`, `selectable`, `stickyHeader`, `compact`; cell slots `#cell-{key}`, pagination, sort indicators, checkbox selection |
| `Modal.vue` | Overlay dialog with Teleport | `open`, `title`, `size` (sm/md/lg/xl/full), `closeable`; backdrop blur, Escape dismiss, body scroll lock, header/body/footer slots |
| `ConfirmDialog.vue` | Destructive action confirmation | `open`, `title`, `message`, `confirmText`, `variant` (destructive/warning/primary/success), `loading`; variant-colored icon + button |
| `StatusBadge.vue` | Colored status pill with dot | `status`, `colorMap`, `showDot`, `size`; built-in maps for ACTIVE/PAID/PENDING/CANCELLED/OVERDUE etc. |
| `TypeBadge.vue` | Account/transaction type indicator | `type`, `typeMap`, `showIcon`, `size`; built-in maps for INCOME/EXPENSE/TRANSFER, ASSET/LIABILITY/INVESTMENT, DEBIT/CREDIT + SVG icons |
| `ProgressBar.vue` | Horizontal progress bar | `value`, `max`, `color` (cyan/green/amber/red/navy), `showLabel`, `showValues`, `size` (sm/md/lg); auto-red when >= 100% |
| `EmptyState.vue` | No-data illustration + CTA | `title`, `description`, `icon` (inbox/search/folder/credit-card/chart), `actionLabel`, `@action` |
| `SearchInput.vue` | Debounced search field | `modelValue`, `placeholder`, `debounceMs`, `size`, `disabled`; search icon, clear button, emits `search` after debounce |
| `FilterBar.vue` | Horizontal filter strip | `filters` config array (search/select/date/toggle), `modelValue`, `showReset`, `loading`; auto-reset button |
| `CurrencyInput.vue` | Amount + currency code selector | `amount`, `currency`, `currencies`, `showCurrencySelect`, `step`; 20+ currency symbols |
| `DateRangePicker.vue` | From/To date with presets | `from`, `to`, `presets`, `showPresets`; 6 built-in presets (Today, Last 7/30/90 Days, This Month, This Year), clear button |
| `CategoryTreeSelect.vue` | Hierarchical category picker | `categories` (TreeNode), `modelValue`, `searchable`, `showTypeIndicator`; expand/collapse, search filter, income/expense badge, click-outside close |
| `FormErrors.vue` | Django Ninja error display | `errors` (general), `fieldErrors` (Record<string, string[]>); error icon, formatted field names |
| `TagChips.vue` | Display + edit tag list | `tags`, `editable`, `availableTags`, `size`; color-styled chips, remove button, autocomplete add |
| `LoadingSkeleton.vue` | Content placeholder with shimmer | `rows`, `type` (table/card/detail); matches DataTable card and detail layouts |

**Barrel export**: `src/components/vue/index.ts` — `import { DataTable, Modal, ... } from "@/components/vue"`

**Design system compliance**: All components use the Tailwind 4 theme tokens (`navy-*`, `cyan-*`, `slate-custom-*`, `debit`, `credit`), CSS component classes (`btn-primary`, `input-field`, `card`, `skeleton`), dark mode throughout, `animate-*` transitions, and inline SVG icons.

**Time estimate**: ~~4-5 days~~ → Completed

### 3.6 Shared Composables — `src/composables/` ✅ DONE

| Composable | Purpose |
|------------|---------|
| `useLedgerPagination.ts` | Offset/limit pagination state + helpers |
| `useLedgerFilters.ts` | Filter state management + URL sync |
| `useCrudForm.ts` | Create/edit form lifecycle (load, validate, submit, redirect) |
| `useSoftDelete.ts` | Delete + restore confirmation flow |
| `useActivator.ts` | Activate/deactivate toggle with confirmation |
| `useDropdownLoader.ts` | Lazy-load dropdown data with caching |

**Barrel export**: `src/composables/index.ts` — `import { useLedgerPagination, useCrudForm, ... } from "@/composables"`

**Key design decisions:**
- `useLedgerPagination` — computed pagination state from store filters; `goToPage`, `nextPage`, `prevPage`, `changePageSize`, `resetToFirstPage`; page size options exported as `PAGE_SIZE_OPTIONS`
- `useLedgerFilters` — reactive filter state with bidirectional URL query param sync via `history.replaceState`; supports param prefixing, debounced auto-apply, `hasActiveFilters` computed; reads URL on mount
- `useCrudForm` — handles both create/edit modes; dirty tracking with `beforeunload` warning; `beforeSubmit` transform hook; `mapEntityToForm` / `buildCreatePayload` / `buildUpdatePayload` customization; `computeDiff` for PATCH semantics; proxies store loading/error/fieldErrors
- `useSoftDelete` — confirmation dialog flow with `confirmDelete` / `confirmRestore`; computed `dialogTitle`, `dialogMessage`, `dialogVariant`, `confirmText`; direct operation variants for bulk flows; `refreshListAfter` option
- `useActivator` — toggle with `confirmToggle` (auto-detects is_active); optional confirmation for activate (default: skip); confirmation always required for deactivate; same dialog props pattern as useSoftDelete; direct operation variants
- `useDropdownLoader` — multi-store dropdown cache; `loadDropdown` / `loadMultiple` (parallel); `getDropdown`, `isLoaded`, `isLoading`, `getError` accessors; `invalidate` / `invalidateAll` for cache busting; `anyLoading` computed

**Time estimate**: ~~2 days~~ → Completed

### 3.7 Phase 0 Summary

| Deliverable | Files | Est. Time |
|-------------|-------|-----------|
| TypeScript types | `src/lib/ledgerTypes.ts` | ~~1 day~~ ✅ DONE |
| Ledger API service | `src/lib/ledgerApi.ts` | ~~2 days~~ ✅ DONE |
| Config update | `sattabase.config.ts` | ~~0.5 hour~~ ✅ DONE |
| Pinia store base | `src/stores/base.ts` | ~~1 day~~ ✅ DONE |
| Reusable components (15) | `src/components/vue/` | ~~4-5 days~~ ✅ DONE |
| Shared composables (6) | `src/composables/` | ~~2 days~~ ✅ DONE |
| **Total Phase 0** | | **~11 days** ✅ ALL DONE |

---

## 4. Phase 1 — Core: Accounts & Transactions ✅ DONE

> **Goal**: The heart of the app. Users can create institutions, accounts, categories, tags, and record transactions with splits and transfers. This phase delivers the minimum viable financial tracking loop: **Institution → Account → Category/Tag → Transaction**.

### 4.1 Pinia Stores — `src/stores/` ✅ DONE

Five domain stores built on the Phase 0 `crudState` / `crudGetters` / `crudActions` composable spread pattern. Each store wires to the corresponding `ledgerApi` endpoint group and adds domain-specific state, getters, and actions where needed.

#### 4.1.1 `useInstitutionStore` — `src/stores/institution.ts` ✅ DONE

The simplest store — pure CRUD with no domain-specific extensions. Uses `defineCrudStore` one-liner since the institution domain has no extra state or actions beyond the standard 16 CRUD actions.

```typescript
import { defineCrudStore } from './base'
import { ledgerApi } from '@/lib/ledgerApi'
import type {
  InstitutionOut, InstitutionCreate, InstitutionUpdate,
  InstitutionFilter, InstitutionListOut,
} from '@/lib/ledgerTypes'

export const useInstitutionStore = defineCrudStore<
  InstitutionOut,
  InstitutionCreate,
  InstitutionUpdate,
  InstitutionFilter,
  InstitutionListOut
>({
  storeId: 'institution',
  api: {
    list: (filters?) => ledgerApi.institutions.list(filters),
    get: (id) => ledgerApi.institutions.get(id),
    create: (data) => ledgerApi.institutions.create(data),
    update: (id, data) => ledgerApi.institutions.update(id, data),
    remove: (id) => ledgerApi.institutions.remove(id),
    restore: (id) => ledgerApi.institutions.restore(id),
    dropdown: () => ledgerApi.institutions.dropdown(),
    activate: (id) => ledgerApi.institutions.activate(id),
    deactivate: (id) => ledgerApi.institutions.deactivate(id),
  },
})
```

**Provides** (all from `defineCrudStore`): `items`, `current`, `loading`, `loadingAction`, `error`, `fieldErrors`, `total`, `filters`, `dropdown`, `dropdownLoaded`, `lastFetched` + getters `activeItems`, `hasItems`, `hasError`, `isStale`, `totalPages`, `currentPage` + actions `fetchList`, `fetchOne`, `fetchDropdown`, `refreshIfStale`, `create`, `update`, `remove`, `restore`, `activate`, `deactivate`, `clearError`, `clearCurrent`, `setFilters`, `resetFilters`, `setPage`, `invalidate`, `$resetCrud`.

#### 4.1.2 `useAccountStore` — `src/stores/account.ts` ✅ DONE

Standard CRUD plus one domain-specific action: `recalculateBalance`. Also adds extra getters for grouped account views and net-worth computation.

```typescript
import { defineStore } from 'pinia'
import { crudState, crudGetters, crudActions } from './base'
import { ledgerApi } from '@/lib/ledgerApi'
import type {
  AccountOut, AccountCreate, AccountUpdate,
  AccountFilter, AccountListOut, BalanceRecalculateOut,
} from '@/lib/ledgerTypes'

export const useAccountStore = defineStore('account', {
  state: () => ({
    ...crudState<AccountOut, AccountFilter, AccountListOut>(),
  }),

  getters: {
    ...crudGetters<AccountOut>(),

    /** Accounts filtered to ASSET type only */
    assetAccounts: (state) => state.items.filter(a => a.account_type === 'ASSET'),

    /** Accounts filtered to LIABILITY type only */
    liabilityAccounts: (state) => state.items.filter(a => a.account_type === 'LIABILITY'),

    /** Accounts filtered to INVESTMENT type only */
    investmentAccounts: (state) => state.items.filter(a => a.account_type === 'INVESTMENT'),

    /** Sum of all active ASSET balances (string → number conversion) */
    totalAssets: (state) => {
      return state.items
        .filter(a => a.is_active && a.account_type === 'ASSET')
        .reduce((sum, a) => sum + parseFloat(a.current_balance || '0'), 0)
    },

    /** Sum of all active LIABILITY balances (absolute value) */
    totalLiabilities: (state) => {
      return state.items
        .filter(a => a.is_active && a.account_type === 'LIABILITY')
        .reduce((sum, a) => sum + Math.abs(parseFloat(a.current_balance || '0')), 0)
    },

    /** Net worth = total assets - total liabilities */
    netWorth() {
      return this.totalAssets - this.totalLiabilities
    },
  },

  actions: {
    ...crudActions<AccountOut, AccountCreate, AccountUpdate, AccountFilter>({
      storeId: 'account',
      api: {
        list: (filters?) => ledgerApi.accounts.list(filters),
        get: (id) => ledgerApi.accounts.get(id),
        create: (data) => ledgerApi.accounts.create(data),
        update: (id, data) => ledgerApi.accounts.update(id, data),
        remove: (id) => ledgerApi.accounts.remove(id),
        restore: (id) => ledgerApi.accounts.restore(id),
        dropdown: () => ledgerApi.accounts.dropdown(),
        activate: (id) => ledgerApi.accounts.activate(id),
        deactivate: (id) => ledgerApi.accounts.deactivate(id),
      },
    }),

    /** Trigger backend balance recalculation for a specific account */
    async recalculateBalance(id: number): Promise<BalanceRecalculateOut> {
      this.loadingAction = 'recalculateBalance'
      this.error = null
      try {
        const result = await ledgerApi.accounts.recalculateBalance(id)
        // Update the account in local items array
        const idx = this.items.findIndex(a => a.id === id)
        if (idx !== -1) {
          // Re-fetch the account to get updated balance
          const updated = await ledgerApi.accounts.get(id)
          this.items[idx] = updated
        }
        if (this.current?.id === id) {
          this.current = await ledgerApi.accounts.get(id)
        }
        return result
      } catch (err) {
        this.error = extractErrorMessage(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },
  },
})
```

**Extra getters**: `assetAccounts`, `liabilityAccounts`, `investmentAccounts`, `totalAssets`, `totalLiabilities`, `netWorth`

**Extra action**: `recalculateBalance(id)` — calls `ledgerApi.accounts.recalculateBalance(id)`, then refreshes the affected account in both `items[]` and `current`.

#### 4.1.3 `useCategoryStore` — `src/stores/category.ts` ✅ DONE

Standard CRUD plus `tree[]` state and `fetchTree` action. Categories have a hierarchical parent-child relationship that requires separate tree-loading and a flat-list-to-tree conversion getter.

```typescript
import { defineStore } from 'pinia'
import { crudState, crudGetters, crudActions, extractErrorMessage } from './base'
import { ledgerApi } from '@/lib/ledgerApi'
import type {
  CategoryOut, CategoryCreate, CategoryUpdate,
  CategoryFilter, CategoryListOut, CategoryTreeOut,
} from '@/lib/ledgerTypes'

export const useCategoryStore = defineStore('category', {
  state: () => ({
    ...crudState<CategoryOut, CategoryFilter, CategoryListOut>(),
    // ── Domain-specific extra state ──
    tree: [] as CategoryTreeOut[],
    treeLoaded: false,
  }),

  getters: {
    ...crudGetters<CategoryOut>(),

    /** Categories with is_income = true */
    incomeCategories: (state) => state.items.filter(c => c.is_income),

    /** Categories with is_income = false */
    expenseCategories: (state) => state.items.filter(c => !c.is_income),

    /** Flat list with parent name resolved — useful for DataTable display */
    flatList(state): Array<CategoryOut & { parent_name: string | null }> {
      const nameMap = new Map(state.items.map(c => [c.id, c.name]))
      return state.items.map(c => ({
        ...c,
        parent_name: c.parent_id ? nameMap.get(c.parent_id) ?? null : null,
      }))
    },
  },

  actions: {
    ...crudActions<CategoryOut, CategoryCreate, CategoryUpdate, CategoryFilter>({
      storeId: 'category',
      api: {
        list: (filters?) => ledgerApi.categories.list(filters),
        get: (id) => ledgerApi.categories.get(id),
        create: (data) => ledgerApi.categories.create(data),
        update: (id, data) => ledgerApi.categories.update(id, data),
        remove: (id) => ledgerApi.categories.remove(id),
        restore: (id) => ledgerApi.categories.restore(id),
        dropdown: () => ledgerApi.categories.dropdown(),
        activate: (id) => ledgerApi.categories.activate(id),
        deactivate: (id) => ledgerApi.categories.deactivate(id),
      },
    }),

    /** Fetch the hierarchical category tree from backend */
    async fetchTree(force = false): Promise<void> {
      if (this.treeLoaded && !force) return
      this.loadingAction = 'fetchTree'
      this.error = null
      try {
        this.tree = await ledgerApi.categories.tree()
        this.treeLoaded = true
      } catch (err) {
        this.error = extractErrorMessage(err)
      } finally {
        this.loadingAction = ''
      }
    },

    /** Override $resetCrud to also clear tree state */
    $resetCrud() {
      // Call the base $resetCrud from crudActions
      // (spread actions include it, but we need to also reset tree)
      this.tree = []
      this.treeLoaded = false
      // Reset base CRUD state
      this.items = []
      this.current = null
      this.loading = false
      this.loadingAction = ''
      this.error = null
      this.fieldErrors = {}
      this.total = 0
      this.dropdownLoaded = false
      this.listLoaded = false
      this.lastFetched = null
    },
  },
})
```

**Extra state**: `tree: CategoryTreeOut[]`, `treeLoaded: boolean`

**Extra getters**: `incomeCategories`, `expenseCategories`, `flatList` (with `parent_name` resolved)

**Extra action**: `fetchTree(force?)` — calls `ledgerApi.categories.tree()`, caches in `tree[]` with `treeLoaded` flag. After any create/update/remove action, the tree should be invalidated by setting `treeLoaded = false` so the next `fetchTree` re-fetches.

#### 4.1.4 `useTagStore` — `src/stores/tag.ts` ✅ DONE

Subset of standard CRUD — tags do NOT support activate/deactivate actions (the backend `TagController` has no activate/deactivate endpoints). Uses the composable spread pattern with optional `activate`/`deactivate` omitted.

```typescript
import { defineCrudStore } from './base'
import { ledgerApi } from '@/lib/ledgerApi'
import type {
  TagOut, TagCreate, TagUpdate,
  TagFilter, TagListOut,
} from '@/lib/ledgerTypes'

export const useTagStore = defineCrudStore<
  TagOut,
  TagCreate,
  TagUpdate,
  TagFilter,
  TagListOut
>({
  storeId: 'tag',
  api: {
    list: (filters?) => ledgerApi.tags.list(filters),
    get: (id) => ledgerApi.tags.get(id),
    create: (data) => ledgerApi.tags.create(data),
    update: (id, data) => ledgerApi.tags.update(id, data),
    remove: (id) => ledgerApi.tags.remove(id),
    restore: (id) => ledgerApi.tags.restore(id),
    dropdown: () => ledgerApi.tags.dropdown(),
    // No activate/deactivate — TagController doesn't expose these
  },
})
```

**Note**: The `crudActions` factory handles optional `activate`/`deactivate` gracefully — if omitted from the `api` config, those actions simply won't be available on the store. UI components should check for tag-specific feature support (no activate/deactivate buttons on tag rows).

#### 4.1.5 `useTransactionStore` — `src/stores/transaction.ts` ✅ DONE

The heaviest store. Composes three API groups (`transactions`, `splits`, `transactionTags`) and adds significant domain-specific state and actions. The base CRUD spread handles the primary transaction entity; split and tag sub-resources are managed by additional state and actions.

```typescript
import { defineStore } from 'pinia'
import { crudState, crudGetters, crudActions, extractErrorMessage } from './base'
import { ledgerApi } from '@/lib/ledgerApi'
import type {
  TransactionOut, TransactionCreate, TransactionUpdate,
  TransactionFilter, TransactionListOut,
  TransferCreate, TransferOut,
  TransactionSplitOut, TransactionSplitCreate, TransactionSplitUpdate,
  TransactionTagOut, TransactionTagCreate, TransactionTagBulkCreate, TransactionTagBulkOut,
} from '@/lib/ledgerTypes'

export const useTransactionStore = defineStore('transaction', {
  state: () => ({
    ...crudState<TransactionOut, TransactionFilter, TransactionListOut>(),
    // ── Sub-resource: Recent transactions (dashboard widget) ──
    recent: [] as TransactionListOut[],
    recentLoaded: false,
    // ── Sub-resource: Transaction Splits ──
    splits: [] as TransactionSplitOut[],
    splitsLoaded: false,
    // ── Sub-resource: Transaction Tags ──
    tags: [] as TransactionTagOut[],
    tagsLoaded: false,
  }),

  getters: {
    ...crudGetters<TransactionOut>(),

    /** Transactions grouped by account_id */
    byAccount(state): Map<number, TransactionOut[]> {
      const map = new Map<number, TransactionOut[]>()
      for (const t of state.items) {
        const list = map.get(t.account_id) ?? []
        list.push(t)
        map.set(t.account_id, list)
      }
      return map
    },

    /** Transactions grouped by category_id */
    byCategory(state): Map<number | null, TransactionOut[]> {
      const map = new Map<number | null, TransactionOut[]>()
      for (const t of state.items) {
        const key = (t as any).category_id ?? null
        const list = map.get(key) ?? []
        list.push(t)
        map.set(key, list)
      }
      return map
    },

    /** Transactions grouped by transaction_type */
    byType(state): Record<string, TransactionOut[]> {
      const record: Record<string, TransactionOut[]> = {}
      for (const t of state.items) {
        const key = t.transaction_type
        if (!record[key]) record[key] = []
        record[key].push(t)
      }
      return record
    },
  },

  actions: {
    ...crudActions<TransactionOut, TransactionCreate, TransactionUpdate, TransactionFilter>({
      storeId: 'transaction',
      api: {
        list: (filters?) => ledgerApi.transactions.list(filters),
        get: (id) => ledgerApi.transactions.get(id),
        create: (data) => ledgerApi.transactions.create(data),
        update: (id, data) => ledgerApi.transactions.update(id, data),
        remove: (id) => ledgerApi.transactions.remove(id),
        restore: (id) => ledgerApi.transactions.restore(id),
        // No dropdown — transactions don't have a dropdown endpoint
      },
    }),

    // ── Recent Transactions (Dashboard) ──

    /** Fetch recent transactions for dashboard widget */
    async fetchRecent(limit = 10, force = false): Promise<void> {
      if (this.recentLoaded && !force) return
      this.loadingAction = 'fetchRecent'
      this.error = null
      try {
        this.recent = await ledgerApi.transactions.recent(limit)
        this.recentLoaded = true
      } catch (err) {
        this.error = extractErrorMessage(err)
      } finally {
        this.loadingAction = ''
      }
    },

    // ── Transfer ──

    /** Create a transfer (generates outflow + inflow transaction pair) */
    async createTransfer(data: TransferCreate): Promise<TransferOut> {
      this.loadingAction = 'createTransfer'
      this.error = null
      this.clearFieldErrors()
      try {
        const result = await ledgerApi.transactions.createTransfer(data)
        // Add both sides to local items list
        this.items.unshift(result.outflow)
        this.items.unshift(result.inflow)
        this.total += 2
        return result
      } catch (err) {
        this.error = extractErrorMessage(err)
        this.fieldErrors = extractFieldErrors(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    // ── Transaction Splits ──

    /** Fetch all splits for a transaction */
    async fetchSplits(transactionId: number, force = false): Promise<void> {
      if (this.splitsLoaded && !force) return
      this.loadingAction = 'fetchSplits'
      this.error = null
      try {
        this.splits = await ledgerApi.splits.list(transactionId)
        this.splitsLoaded = true
      } catch (err) {
        this.error = extractErrorMessage(err)
      } finally {
        this.loadingAction = ''
      }
    },

    /** Create a new split for a transaction */
    async createSplit(transactionId: number, data: TransactionSplitCreate): Promise<TransactionSplitOut> {
      this.loadingAction = 'createSplit'
      this.error = null
      try {
        const split = await ledgerApi.splits.create(transactionId, data)
        this.splits.push(split)
        return split
      } catch (err) {
        this.error = extractErrorMessage(err)
        this.fieldErrors = extractFieldErrors(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    /** Update an existing split */
    async updateSplit(transactionId: number, splitId: number, data: TransactionSplitUpdate): Promise<TransactionSplitOut> {
      this.loadingAction = 'updateSplit'
      this.error = null
      try {
        const updated = await ledgerApi.splits.update(transactionId, splitId, data)
        const idx = this.splits.findIndex(s => s.id === splitId)
        if (idx !== -1) this.splits[idx] = updated
        return updated
      } catch (err) {
        this.error = extractErrorMessage(err)
        this.fieldErrors = extractFieldErrors(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    /** Delete a split */
    async deleteSplit(transactionId: number, splitId: number): Promise<void> {
      this.loadingAction = 'deleteSplit'
      this.error = null
      try {
        await ledgerApi.splits.remove(transactionId, splitId)
        this.splits = this.splits.filter(s => s.id !== splitId)
      } catch (err) {
        this.error = extractErrorMessage(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    // ── Transaction Tags ──

    /** Fetch tags attached to a transaction */
    async fetchTags(transactionId: number, force = false): Promise<void> {
      if (this.tagsLoaded && !force) return
      this.loadingAction = 'fetchTags'
      this.error = null
      try {
        this.tags = await ledgerApi.transactionTags.list(transactionId)
        this.tagsLoaded = true
      } catch (err) {
        this.error = extractErrorMessage(err)
      } finally {
        this.loadingAction = ''
      }
    },

    /** Add a single tag to a transaction */
    async addTag(transactionId: number, data: TransactionTagCreate): Promise<TransactionTagOut> {
      this.loadingAction = 'addTag'
      this.error = null
      try {
        const tag = await ledgerApi.transactionTags.attach(transactionId, data)
        this.tags.push(tag)
        return tag
      } catch (err) {
        this.error = extractErrorMessage(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    /** Bulk set all tags on a transaction (replaces existing) */
    async bulkSetTags(transactionId: number, data: TransactionTagBulkCreate): Promise<TransactionTagBulkOut> {
      this.loadingAction = 'bulkSetTags'
      this.error = null
      try {
        const result = await ledgerApi.transactionTags.bulkSet(transactionId, data)
        // Refresh tags from result
        this.tags = result.tag_ids.map(tagId => ({ id: 0, transaction_id: transactionId, tag_id: tagId, user_id: 0, created_at: '' }))
        this.tagsLoaded = true
        return result
      } catch (err) {
        this.error = extractErrorMessage(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    /** Remove a tag from a transaction */
    async removeTag(transactionId: number, tagId: number): Promise<void> {
      this.loadingAction = 'removeTag'
      this.error = null
      try {
        await ledgerApi.transactionTags.detach(transactionId, tagId)
        this.tags = this.tags.filter(t => t.tag_id !== tagId)
      } catch (err) {
        this.error = extractErrorMessage(err)
        throw err
      } finally {
        this.loadingAction = ''
      }
    },

    // ── Overridden $resetCrud ──

    /** Reset all state including sub-resources */
    $resetCrud() {
      this.recent = []
      this.recentLoaded = false
      this.splits = []
      this.splitsLoaded = false
      this.tags = []
      this.tagsLoaded = false
      this.items = []
      this.current = null
      this.loading = false
      this.loadingAction = ''
      this.error = null
      this.fieldErrors = {}
      this.total = 0
      this.dropdownLoaded = false
      this.listLoaded = false
      this.lastFetched = null
    },
  },
})
```

**Extra state**: `recent[]`, `recentLoaded`, `splits[]`, `splitsLoaded`, `tags[]`, `tagsLoaded`

**Extra getters**: `byAccount`, `byCategory`, `byType`

**Extra actions**: `fetchRecent`, `createTransfer`, `fetchSplits`, `createSplit`, `updateSplit`, `deleteSplit`, `fetchTags`, `addTag`, `bulkSetTags`, `removeTag`

**Key design decisions for Transaction store**:
- Sub-resource state (`splits`, `tags`) is scoped to the currently-viewed transaction. When navigating to a different transaction detail, `splitsLoaded`/`tagsLoaded` must be reset to `false` so the next `fetchSplits`/`fetchTags` call fetches fresh data.
- `createTransfer` adds both outflow and inflow transactions to the local `items[]` immediately for optimistic UI, and increments `total` by 2.
- `bulkSetTags` replaces the entire tag list on a transaction — used by the tag editor chip component when the user adds/removes multiple tags at once.
- No `dropdown` endpoint for transactions — the base `fetchDropdown` action is not wired and should not be called.

### 4.2 Feature Pages ✅ DONE

#### 4.2.1 Institutions — `/dashboard/institutions` ✅ DONE

**Files created:**
- `src/pages/dashboard/institutions/index.astro` — Astro page shell
- `src/components/vue/institutions/InstitutionList.vue` — Main list component
- `src/components/vue/institutions/InstitutionForm.vue` — Create/edit modal form

**Astro Page** (`src/pages/dashboard/institutions/index.astro`)
```astro
---
import DashboardLayout from '@/layouts/DashboardLayout.astro'
import InstitutionList from '@/components/vue/institutions/InstitutionList.vue'
---
<DashboardLayout title="Institutions">
  <InstitutionList client:only="vue" />
</DashboardLayout>
```

**InstitutionList.vue** — Full-featured list page with DataTable, search, filters, and CRUD actions.

| Feature | Implementation |
|---------|---------------|
| **Data table** | `<DataTable>` with columns: Name, Type, Website, Status, Actions |
| **Search** | `<SearchInput>` bound to `filters.search`, debounced 300ms |
| **Filters** | `<FilterBar>` with `institution_type` (select) and `is_active` (toggle) |
| **Type column** | `<TypeBadge>` with `typeMap` for `BANK/CREDIT_UNION/BROKERAGE/CRYPTO/WALLET/OTHER` + SVG icons |
| **Status column** | `<StatusBadge>` with `colorMap`: `ACTIVE=green`, `INACTIVE=slate` |
| **Actions** | Edit (pencil icon → opens modal), Delete (trash → `<ConfirmDialog>`), Activate/Deactivate (power icon → `useActivator`) |
| **Add button** | Top-right "Add Institution" → opens `<Modal>` with `<InstitutionForm>` |
| **Empty state** | `<EmptyState icon="folder" actionLabel="Add Institution">` when no items |
| **Pagination** | `useLedgerPagination` wired to store `total`/`limit`/`offset` |
| **Loading** | `<LoadingSkeleton type="table">` while `store.loading && loadingAction === 'fetchList'` |
| **Dropdown pre-load** | `useDropdownLoader` to warm institution dropdown cache on mount |

**InstitutionForm.vue** — Modal form for create and edit.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `name` | text input (required) | Required, unique (check against `store.items` on blur) | Max 100 chars |
| `institution_type` | select dropdown | Optional, defaults to `BANK` | Options: Bank, Credit Union, Brokerage, Crypto, Wallet, Other |
| `website` | URL input | Optional, valid URL format | |
| `customer_service_phone` | tel input | Optional, phone format | |
| `icon` | text input | Optional | Emoji or icon name |
| `color` | color picker | Optional | Hex color, 6 predefined swatches + custom |
| `notes` | textarea | Optional | Max 500 chars |

**Composable wiring:**
- `useCrudForm<InstitutionCreate, InstitutionUpdate, InstitutionOut>` — handles create/edit mode, dirty tracking, form submission, error display
- `useDropdownLoader` — for institution dropdown if needed in other forms

**Detail view**: Inline expansion in DataTable — clicking a row expands to show linked accounts (fetched from `useAccountStore` filtered by `institution_id`). No separate detail page for institutions.

---

#### 4.2.2 Accounts — `/dashboard/accounts` ✅ DONE

**Files created:**
- `src/pages/dashboard/accounts/index.astro` — List page shell
- `src/pages/dashboard/accounts/[id].astro` — Detail page shell
- `src/components/vue/accounts/AccountList.vue` — Card grid list
- `src/components/vue/accounts/AccountCard.vue` — Single account card
- `src/components/vue/accounts/AccountForm.vue` — Create/edit form
- `src/components/vue/accounts/AccountDetail.vue` — Detail view with tabs

**Astro Pages:**
```astro
<!-- index.astro -->
<DashboardLayout title="Accounts">
  <AccountList client:only="vue" />
</DashboardLayout>

<!-- [id].astro -->
---
import AccountDetail from '@/components/vue/accounts/AccountDetail.vue'
const { id } = Astro.params
---
<DashboardLayout title="Account Detail">
  <AccountDetail client:only="vue" accountId={id} />
</DashboardLayout>
```

**AccountList.vue** — Card grid layout with grouped sections.

| Feature | Implementation |
|---------|---------------|
| **Layout** | Card grid (not table) — accounts are visual, users identify by name/institution/balance |
| **Grouping** | Three sections: Asset Accounts, Liability Accounts, Investment Accounts — uses `store.assetAccounts`, `store.liabilityAccounts`, `store.investmentAccounts` |
| **Net worth summary** | Top banner: "Net Worth: $X" using `store.netWorth`, "Assets: $Y", "Liabilities: $Z" |
| **AccountCard** | Each card shows: institution name (small text), account name (bold), `<TypeBadge>` for account_type, currency code, current balance (formatted via `formatCurrency()`), available credit line (if liability) |
| **Balance coloring** | Positive balance = `text-credit` (green), Negative balance = `text-debit` (red), Zero = `text-slate-400` |
| **Filters** | `<FilterBar>` with `institution_id` (select from dropdown), `account_type` (ASSET/LIABILITY/INVESTMENT), `currency` (3-letter codes), `is_active` (toggle) |
| **Sort** | Dropdown: name, balance, sort_order |
| **Search** | `<SearchInput>` on account name |
| **Add button** | "Add Account" → `<Modal>` with `<AccountForm>` |
| **Card actions** | Edit (→ modal), Delete/Restore (`<ConfirmDialog>`), Activate/Deactivate, "Recalculate Balance" button |
| **Card click** | Navigate to `/dashboard/accounts/{id}` detail page |
| **Empty state** | `<EmptyState icon="credit-card" actionLabel="Add Account">` |
| **Dropdown pre-load** | `useDropdownLoader` to warm institution + account dropdown caches |

**AccountCard.vue** — Visual card component.

| Prop | Type | Description |
|------|------|-------------|
| `account` | `AccountOut` | Full account object |
| `institutionName` | `string` | Resolved institution name |

| Feature | Detail |
|---------|--------|
| **Layout** | White card with left color strip (from `account.color`), rounded corners, shadow |
| **Header** | Institution name (small, muted) + account name (h3, bold) |
| **Badge row** | `<TypeBadge type={account.account_type}>` + currency code badge |
| **Balance** | Large formatted amount with `formatCurrency()`, colored by sign |
| **Credit** | If `account_type === 'LIABILITY'`, show "Available: {credit_limit - current_balance}" |
| **Actions** | Hover overlay with Edit/Delete/Activate icons |

**AccountForm.vue** — Multi-section create/edit form with conditional fields.

| Section | Fields | Conditional |
|---------|--------|-------------|
| **Institution** | `institution_id` (dropdown from `useInstitutionStore.dropdown`) | Always shown; "Create New" link opens inline `InstitutionForm` |
| **Basic Info** | `name` (required), `account_type` (select with icons: ASSET/LIABILITY/INVESTMENT), `currency` (searchable dropdown from cached currency metadata) | Always shown |
| **Financial Details** | `current_balance` (`<CurrencyInput>`), `credit_limit` (show only if LIABILITY), `interest_rate` (%) | `credit_limit` & `interest_rate` conditional |
| **Schedule** | `statement_closing_day` (1-28 dropdown), `due_day` (1-28 dropdown) | Show only if LIABILITY |
| **Appearance** | `icon` (emoji/text), `color` (color picker), `sort_order` (number) | Always shown |
| **Notes** | `notes` (textarea) | Always shown |

**Auto-currency logic**: When user selects an institution, auto-set currency to the institution's most common currency (or first linked account's currency). User can override.

**AccountDetail.vue** — Tabbed detail view.

| Tab | Content |
|-----|---------|
| **Overview** | Account header (name, institution, type badge, balance), key financial metrics, "Recalculate Balance" button with confirmation |
| **Transactions** | Filtered transaction list using `useTransactionStore.fetchList({ account_id })` — reuses `TransactionList` component (or simplified inline version) |
| **Cards** | Cards linked to this account (Phase 3 — placeholder) |
| **Bills** | Bills linked to this account (Phase 2 — placeholder) |

**Composable wiring:**
- `useCrudForm<AccountCreate, AccountUpdate, AccountOut>` — form lifecycle
- `useSoftDelete` — delete/restore confirmation
- `useActivator` — activate/deactivate toggle
- `useDropdownLoader` — loads institution dropdown + currency metadata

---

#### 4.2.3 Categories — `/dashboard/categories` ✅ DONE

**Files created:**
- `src/pages/dashboard/categories/index.astro` — List page shell
- `src/components/vue/categories/CategoryTree.vue` — Hierarchical tree view
- `src/components/vue/categories/CategoryList.vue` — Flat DataTable view
- `src/components/vue/categories/CategoryForm.vue` — Create/edit form

**Astro Page:**
```astro
<DashboardLayout title="Categories">
  <CategoryTree client:only="vue" />
</DashboardLayout>
```

**CategoryTree.vue** — Primary view with hierarchical tree + flat list toggle.

| Feature | Implementation |
|---------|---------------|
| **View toggle** | Two buttons: "Tree View" / "List View" — toggles between `CategoryTree` content and `<CategoryList>` component |
| **Tree view** | Recursive rendering of `store.tree` (CategoryTreeOut[]) — each node shows: icon, color dot, name, is_income badge (`<TypeBadge type={is_income ? 'INCOME' : 'EXPENSE'}>`), transaction count (placeholder) |
| **Expand/collapse** | All nodes start collapsed; click chevron to expand/collapse children |
| **Node actions** | Click node → select; hover → show Edit/Delete/Activate icons |
| **Add button** | "Add Category" button → `<Modal>` with `<CategoryForm>` |
| **Drag-and-drop reorder** | HTML5 Drag API — drag nodes to reorder siblings or change parent; calls `store.update(id, { sort_order, parent_id })` on drop. Visual feedback: drop indicator line between nodes |
| **Inline create** | "+" button at bottom of each group → inline `<CategoryForm>` with pre-set `parent_id` |
| **Empty state** | `<EmptyState icon="folder" actionLabel="Add Category">` when tree is empty |
| **Loading** | `<LoadingSkeleton type="card" :rows="5">` while `store.loadingAction === 'fetchTree'` |

**CategoryList.vue** — Alternative flat DataTable view.

| Feature | Implementation |
|---------|---------------|
| **DataTable** | Columns: Name, Parent, Type (Income/Expense), Sort Order, Status, Actions |
| **Parent column** | Shows full path e.g. "Food > Groceries" using `store.flatList` getter |
| **Filters** | `<FilterBar>` with `is_income` (toggle), `parent_id` (tree select), `is_active` (toggle) |
| **Search** | `<SearchInput>` on category name |
| **Actions** | Edit, Delete/Restore, Activate/Deactivate |

**CategoryForm.vue** — Create/edit form with parent tree select.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `name` | text input (required) | Required, unique at same parent level (check against `store.items`) | |
| `parent_id` | `<CategoryTreeSelect>` | Optional | Shows full hierarchy, searchable. Excludes current category from tree (prevent circular parent) |
| `is_income` | toggle switch | Defaults to `false` | Changes badge display in tree |
| `icon` | text input | Optional | Emoji or icon name |
| `color` | color picker | Optional | Hex color, 6 predefined swatches (income: greens, expense: reds/oranges) + custom |
| `sort_order` | number input | Optional | Auto-assigned as last in group if not specified |

**Parent selection edge cases:**
- Creating a child category: parent_id pre-set from inline "+" button
- Editing a category: cannot set parent to self or any descendant (prevents circular references)
- Moving a category: changing parent_id moves the entire subtree

**Composable wiring:**
- `useCrudForm<CategoryCreate, CategoryUpdate, CategoryOut>` — form lifecycle
- After create/update/remove → invalidate `store.treeLoaded = false` so tree re-fetches on next view
- `useSoftDelete` — delete/restore confirmation
- `useActivator` — activate/deactivate toggle

---

#### 4.2.4 Tags — `/dashboard/tags` ✅ DONE

**Files created:**
- `src/pages/dashboard/tags/index.astro` — List page shell
- `src/components/vue/tags/TagList.vue` — Chip grid with inline create
- `src/components/vue/tags/TagForm.vue` — Inline/modal edit form

**Astro Page:**
```astro
<DashboardLayout title="Tags">
  <TagList client:only="vue" />
</DashboardLayout>
```

**TagList.vue** — Grid of tag chips with inline create.

| Feature | Implementation |
|---------|---------------|
| **Layout** | Flex-wrap grid of colored chip buttons — each chip shows: color dot, tag name |
| **Inline create** | Top row: text input + color picker + "Add" button (or Enter to save) — calls `store.create({ name, color })` |
| **Click to edit** | Click chip → opens `<Modal>` with `<TagForm>` for editing name/color |
| **Delete** | Trash icon on hover → `<ConfirmDialog>` → `store.remove(id)` |
| **Search** | `<SearchInput>` to filter visible chips by name |
| **Empty state** | `<EmptyState icon="inbox" actionLabel="Create Tag">` when no tags |
| **Restore** | If deleted tags exist, show "Show deleted" toggle at bottom; restored chips appear with restore button |
| **Color dots** | Small circle before tag name, filled with `tag.color` |
| **Tag count** | (Future Phase 6) Show transaction count per tag from analytics endpoint |

**TagForm.vue** — Simple create/edit form.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `name` | text input (required) | Required, unique (check `store.items`) | Max 50 chars |
| `color` | color picker | Optional, defaults to auto-assigned color | 12 predefined swatches (rainbow) + custom hex input |

**Note**: Tags do NOT support activate/deactivate. The `useTagStore` has no `activate`/`deactivate` actions. UI should not show activate/deactivate buttons for tags.

**Composable wiring:**
- `useCrudForm<TagCreate, TagUpdate, TagOut>` — form lifecycle
- `useSoftDelete` — delete/restore confirmation (no activator)

---

#### 4.2.5 Transactions — `/dashboard/transactions` ✅ DONE

The most complex feature in the entire application. Multiple sub-views, advanced filtering, dual-mode forms (simple + split), transfer creation, and detail view with split/tag management.

**Files created:**
- `src/pages/dashboard/transactions/index.astro` — List page shell
- `src/pages/dashboard/transactions/[id].astro` — Detail page shell
- `src/components/vue/transactions/TransactionList.vue` — Main list with filters
- `src/components/vue/transactions/TransactionFilters.vue` — Advanced filter bar
- `src/components/vue/transactions/TransactionForm.vue` — Create/edit (simple + split modes)
- `src/components/vue/transactions/SplitEditor.vue` — Inline split rows editor
- `src/components/vue/transactions/TransferForm.vue` — Transfer-specific form
- `src/components/vue/transactions/TransactionDetail.vue` — Detail view

**Astro Pages:**
```astro
<!-- index.astro -->
<DashboardLayout title="Transactions">
  <TransactionList client:only="vue" />
</DashboardLayout>

<!-- [id].astro -->
---
import TransactionDetail from '@/components/vue/transactions/TransactionDetail.vue'
const { id } = Astro.params
---
<DashboardLayout title="Transaction Detail">
  <TransactionDetail client:only="vue" transactionId={id} />
</DashboardLayout>
```

**TransactionList.vue** — Full-featured table with advanced filters and row expansion.

| Feature | Implementation |
|---------|---------------|
| **DataTable** | Columns: Date, Payee, Category, Account, Amount, Status, Tags, Actions |
| **Date column** | Formatted via `formatDateShort()`, sorted desc by default |
| **Payee column** | Truncated to 30 chars with tooltip for full text |
| **Category column** | Category name from store lookup, show "—" if uncategorized; for split transactions show "Split (N)" |
| **Account column** | Account name from `useAccountStore` dropdown cache lookup |
| **Amount column** | Color-coded: Income = `text-credit` (green), Expense = `text-debit` (red), Transfer = `text-slate-500`, Refund = `text-credit`. Shows `formatCurrency(amount_original, currency_original)`. If different from base currency, show base equivalent in tooltip |
| **Status column** | `<StatusBadge>` with `colorMap`: `PENDING=amber`, `CLEARED=green`, `VOID=slate` |
| **Tags column** | `<TagChips>` with compact size, max 3 visible + "+N more" |
| **Actions column** | Edit, Delete/Restore, View Detail (→ navigate to `/dashboard/transactions/{id}`) |
| **Row expansion** | Click row → expand to show: split breakdown (if split transaction), tag list, description, reference number |
| **Add button** | Dropdown: "Transaction" → `<Modal>` with `<TransactionForm>`, "Transfer" → `<Modal>` with `<TransferForm>` |
| **Empty state** | `<EmptyState icon="inbox" actionLabel="Add Transaction">` |
| **Pagination** | `useLedgerPagination` with `total`/`limit`/`offset` from store |
| **Loading** | `<LoadingSkeleton type="table">` while `store.loadingAction === 'fetchList'` |
| **Dropdown pre-load** | `useDropdownLoader` to warm account + category + tag dropdown caches on mount |

**TransactionFilters.vue** — Advanced filter bar with 8 filter dimensions.

| Filter | Component | Type | Backend Param |
|--------|-----------|------|---------------|
| Date range | `<DateRangePicker>` | from/to with presets | `date_from`, `date_to` |
| Account | Select dropdown | Single select from account dropdown | `account_id` |
| Transaction type | Multi-select chips | INCOME, EXPENSE, TRANSFER, REFUND | `transaction_type` |
| Status | Multi-select chips | PENDING, CLEARED, VOID | `status` |
| Category | `<CategoryTreeSelect>` | Single select from category tree | `category_id` |
| Tags | Multi-select with `<TagChips>` | Multiple tag IDs | `tag_ids` |
| Amount range | Two number inputs (min/max) | Numeric range | `amount_min`, `amount_max` |
| Payee | `<SearchInput>` | Debounced text search | `payee` |

**Filter bar layout**: Horizontal strip above table. Collapsed by default showing only Date Range + Account. "More Filters" button expands to show all 8 filters. Active filter count badge on the button. "Reset All" link clears everything.

**Composable wiring**: `useLedgerFilters` with URL sync — filter state auto-persists in URL query params for bookmarkable filtered views.

**TransactionForm.vue** — Dual-mode form (Simple + Split).

**Simple mode** (default):

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `date` | Date picker | Required, defaults to today | |
| `account_id` | Account dropdown | Required | From `useAccountStore.dropdown`; auto-sets currency |
| `transaction_type` | Select with icons | Required, defaults to EXPENSE | INCOME/EXPENSE/TRANSFER/REFUND |
| `amount_original` | `<CurrencyInput>` | Required, > 0 | Amount + currency; currency auto-set from account |
| `category_id` | `<CategoryTreeSelect>` | Optional but recommended | Filtered by `is_income` matching transaction_type |
| `payee` | Text input with autocomplete | Optional | Autocomplete from unique payees in existing transactions |
| `description` | Textarea | Optional | |
| `reference_number` | Text input | Optional | |
| `status` | Select | PENDING (default) / CLEARED | |
| `tags` | `<TagChips>` with add | Optional | Multi-select from `useTagStore.dropdown` |

**Split mode** (toggle button "Split Transaction"):

| Element | Detail |
|---------|--------|
| **Header fields** | Same as Simple: date, account, type, total amount |
| **Split rows** | Each row: category (`<CategoryTreeSelect>`), amount (`<CurrencyInput>`), notes (text input) |
| **Add row** | "+ Add Split" button appends empty row |
| **Remove row** | "×" button removes row (minimum 2 splits required) |
| **Allocation summary** | Fixed bar at bottom: "$X of $Y allocated, $Z remaining" — green if balanced, red if over/under |
| **Validation** | Total splits must exactly equal transaction amount; each split amount > 0; each split must have a category |
| **Mode toggle** | Switch between Simple ↔ Split; warns if switching from Split with existing splits (data loss) |

**Auto-currency logic**:
1. When `account_id` is selected → set `currency_original` to the account's `currency`
2. If `currency_original` differs from base currency → show exchange rate input + converted amount display
3. `amount_base` is auto-calculated: `amount_original * exchange_rate`

**SplitEditor.vue** — Manages the split rows within TransactionForm.

| Prop | Type | Description |
|------|------|-------------|
| `modelValue` | `TransactionSplitCreate[]` | Array of split row data |
| `totalAmount` | `number` | The parent transaction total amount |
| `currency` | `string` | Currency code for amount display |

| Event | Payload | Description |
|-------|---------|-------------|
| `update:modelValue` | `TransactionSplitCreate[]` | Updated splits array |
| `allocationStatus` | `{ allocated, remaining, isBalanced }` | Real-time allocation tracking |

| Feature | Detail |
|---------|--------|
| **Split rows** | V-for over splits array, each with: category tree select, currency amount input, notes text input, remove button |
| **Add row** | "+ Add Split" button — appends `{ category_id: null, amount: 0, notes: '' }` |
| **Allocation bar** | Sticky bottom bar: `formatCurrency(allocated)` of `formatCurrency(total)` — `formatCurrency(remaining)` remaining. Color: green if `isBalanced`, amber if `remaining > 0`, red if `remaining < 0` |
| **Validation** | All splits must have `category_id` and `amount > 0`; total must equal parent amount |
| **Keyboard** | Tab navigates between fields; Enter on last field adds new row |

**TransferForm.vue** — Dedicated form for creating transfers between accounts.

| Field | Type | Validation | Notes |
|-------|------|-----------|-------|
| `from_account_id` | Account dropdown | Required | Filtered to active accounts |
| `to_account_id` | Account dropdown | Required, must differ from from_account_id | Filtered to active accounts |
| `amount` | `<CurrencyInput>` | Required, > 0 | Single amount; currency from from_account |
| `date` | Date picker | Required, defaults to today | |
| `description` | Text input | Optional | Applied to both outflow and inflow |
| `status` | Select | PENDING / CLEARED | Applied to both sides |

**Post-submit**: `store.createTransfer()` returns `TransferOut` containing both outflow and inflow transactions. Both are added to the local `items[]`. User is navigated to the outflow transaction detail page.

**TransactionDetail.vue** — Full detail view with splits, tags, and transfer link.

| Section | Content |
|---------|---------|
| **Header** | Date, Payee, Amount (color-coded), Transaction Type badge, Status badge |
| **Details grid** | Account (link to account detail), Category (link to category), Description, Reference Number, Exchange Rate (if multi-currency), Bill link (if generated from bill) |
| **Splits** | If transaction has splits: table showing Category, Amount, Notes per split. "Edit Splits" button opens `<SplitEditor>` in modal |
| **Tags** | `<TagChips>` in editable mode — add/remove tags via `store.addTag`/`store.removeTag`/`store.bulkSetTags` |
| **Transfer pair** | If transaction is a transfer: show linked transaction card (the other side) with link to navigate to it. Uses `transfer_pair_id` field |
| **Actions** | Edit (→ modal with TransactionForm), Delete/Restore, Status change buttons (Pending → Cleared → Void), "Recalculate" (if admin) |

**Composable wiring for transaction pages:**
- `useCrudForm<TransactionCreate, TransactionUpdate, TransactionOut>` — form lifecycle for TransactionForm
- `useCrudForm<TransferCreate, never, TransferOut>` — form lifecycle for TransferForm (create-only, no edit)
- `useSoftDelete` — delete/restore confirmation
- `useLedgerFilters` — filter state with URL sync for TransactionFilters
- `useLedgerPagination` — pagination for TransactionList
- `useDropdownLoader` — pre-loads account, category, and tag dropdowns

### 4.3 Sidebar Navigation Update ✅ DONE

Phase 1 requires updating `DashboardLayout.astro` sidebar navigation to include the five new routes:

```typescript
// Add to sidebar nav items array:
{ label: 'Institutions', href: '/dashboard/institutions', icon: 'building' },
{ label: 'Accounts', href: '/dashboard/accounts', icon: 'wallet' },
{ label: 'Categories', href: '/dashboard/categories', icon: 'tag' },
{ label: 'Tags', href: '/dashboard/tags', icon: 'hashtag' },
{ label: 'Transactions', href: '/dashboard/transactions', icon: 'arrow-right-left' },
```

### 4.4 Phase 1 Summary

| Deliverable | Files | Est. Time |
|-------------|-------|-----------|
| **4.1.1 Institution store** | `src/stores/institution.ts` | ~~0.5 day~~ ✅ DONE |
| **4.1.2 Account store** | `src/stores/account.ts` | ~~0.5 day~~ ✅ DONE |
| **4.1.3 Category store** | `src/stores/category.ts` | ~~0.5 day~~ ✅ DONE |
| **4.1.4 Tag store** | `src/stores/tag.ts` | ~~0.5 day~~ ✅ DONE |
| **4.1.5 Transaction store** | `src/stores/transaction.ts` | ~~1 day~~ ✅ DONE |
| **4.2.1 Institutions pages/components** | `index.astro`, `InstitutionsPage.vue`, `InstitutionForm.vue` | ~~1.5 days~~ ✅ DONE |
| **4.2.2 Accounts pages/components** | `index.astro`, `[id].astro`, `AccountsPage.vue`, `AccountForm.vue`, `AccountDetail.vue` | ~~2.5 days~~ ✅ DONE |
| **4.2.3 Categories pages/components** | `index.astro`, `CategoriesPage.vue`, `CategoryForm.vue` | ~~2 days~~ ✅ DONE |
| **4.2.4 Tags pages/components** | `index.astro`, `TagsPage.vue`, `TagForm.vue` | ~~1 day~~ ✅ DONE |
| **4.2.5 Transactions pages/components** | `index.astro`, `[id].astro`, `TransactionsPage.vue`, `TransactionForm.vue`, `TransferForm.vue`, `TransactionDetail.vue` | ~~4 days~~ ✅ DONE |
| **4.3 Sidebar nav update** | `DashboardLayout.astro` | ~~0.5 hour~~ ✅ DONE |
| **Total Phase 1** | **5 stores + 13 components + 7 pages + sidebar** | **~14 days** ✅ ALL DONE |

**Dependency chain**: Stores (4.1) → Simple pages (4.2.1 Institutions → 4.2.4 Tags) → Complex pages (4.2.2 Accounts → 4.2.3 Categories → 4.2.5 Transactions)

**Risk factors**:
- Transaction split form is the most complex single component — dual-mode UI, real-time allocation validation, and multi-currency handling
- Category drag-and-drop reorder requires careful state management to avoid flicker
- Account net-worth computation depends on all accounts being loaded (no pagination for summary)
- Multi-currency display in transaction amounts requires exchange rate metadata from backend

---

## 5. Phase 2 — Bills & Budgets ✅ DONE

### 5.1 Pinia Stores ✅ DONE

| Store | File | Key Actions |
|-------|------|-------------|
| `useBillStore` | `src/stores/bill.ts` ✅ | fetchList, fetchUpcoming, fetchOne, create, update, generateTransaction, remove, restore, pause, cancel, reactivate, fetchPayments, createPayment, updatePayment |
| `useBudgetStore` | `src/stores/budget.ts` ✅ | fetchList, fetchOverview, fetchOne, create, update, remove, restore, activate, deactivate |

### 5.2 Bills — `/dashboard/bills` ✅ DONE

**List Page** (`src/pages/dashboard/bills/index.astro`)
- Card grid showing: Payee, Amount, Currency, Recurrence badge, Next Due Date, Status badge
- Color-coded due dates: overdue = red, due this week = orange, due this month = yellow, later = green
- Filter by status (Active/Paused/Cancelled), recurrence, account, due_within_days
- Sort by next_due_date (default), amount, payee
- "Add Bill" button

**Upcoming Bills Widget** — sidebar or separate view showing bills due within N days

**Create/Edit Form** (`BillForm.vue`) ✅
- Fields: payee, amount, currency, is_amount_fixed (toggle), recurrence (select), start_date, end_date (optional), next_due_date (auto-calculated), account (dropdown), category (tree select), status, remind_me (toggle), days_before_reminder, notes
- Variable amount mode: when `is_amount_fixed=false`, show note about variable bills
- Recurrence visual: show next 3 due dates as preview

**Bill Detail** — `/dashboard/bills/[id].astro` ✅
- Header: Payee, amount, recurrence, next due, status
- Payment history table: Date, Amount, Transaction link, Notes
- Actions: Record Payment, Generate Transaction, Pause/Cancel/Reactivate
- Record Payment form: payment_date, amount (default to bill amount), notes

### 5.3 Budgets — `/dashboard/budgets` ✅ DONE

**Overview Page** (`src/pages/dashboard/budgets/index.astro`)
- Card grid for each budget showing:
  - Category name + icon
  - Amount (limit) formatted with currency
  - Spent amount formatted
  - Remaining amount formatted
  - Progress bar (color: green < 70%, yellow 70-90%, red > 90%)
  - Percentage used text
  - Period badge (Weekly/Monthly/Yearly)
  - Rollover indicator
- Filter by period, category, is_active

**Create/Edit Form** (`BudgetForm.vue`) ✅
- Fields: category (tree select, one per budget), amount, currency, period, start_date, allow_rollover
- Validation: one budget per category per period per start_date

**Budget Detail** — `/dashboard/budgets/[id].astro` ✅
- Budget card (large version with more detail)
- Spending breakdown by subcategory (if category has children)
- Transaction list filtered to budget's category + period

**Time estimate for Phase 2**: ~~8-10 days~~ ✅ DONE

| Deliverable | Files | Est. Time |
|-------------|-------|-----------|
| **5.1 Bill store** | `src/stores/bill.ts` | ~~1.5 days~~ ✅ DONE |
| **5.1 Budget store** | `src/stores/budget.ts` | ~~0.5 day~~ ✅ DONE |
| **5.2 Bills pages/components** | `index.astro`, `[id].astro`, `BillsPage.vue`, `BillForm.vue`, `BillDetail.vue`, `BillPaymentForm.vue` | ~~4 days~~ ✅ DONE |
| **5.3 Budgets pages/components** | `index.astro`, `[id].astro`, `BudgetsPage.vue`, `BudgetForm.vue`, `BudgetDetail.vue` | ~~3 days~~ ✅ DONE |
| **Sidebar nav update** | `DashboardLayout.astro` (Bills + Budgets) | ~~0.5 hour~~ ✅ DONE |
| **Total Phase 2** | **2 stores + 7 components + 4 pages + sidebar** | **~9 days** ✅ ALL DONE |

---

## 6. Phase 3 — Cards & Debt ✅ DONE

### 6.1 Pinia Stores ✅ DONE

| Store | File | Key Actions | Status |
|-------|------|-------------|--------|
| `useCardStore` | `src/stores/card.ts` | fetchList, fetchDropdown, fetchOne, create, update, remove, restore, activate, deactivate | ✅ DONE |
| `useDebtStore` | `src/stores/debt.ts` | fetchList, fetchSummary, fetchOne, create, update, remove, restore, activate, deactivate, fetchPayments, createPayment, updatePayment | ✅ DONE |

### 6.2 Cards — `/dashboard/cards` ✅ DONE

**List Page** (`src/pages/dashboard/cards/index.astro`) ✅ DONE
- Card visual layout — each card looks like a physical card:
  - Card name, card type badge, last four (•••• 4242), expiry date
  - Account link, annual fee amount, color strip
- Filter by card_type, account, is_active
- "Add Card" button
- Hover action buttons: Edit, Delete/Restore, Activate/Deactivate

**CardsPage.vue** ✅ DONE — Physical card-style grid layout with dark navy gradient cards, color strip, hover action bar, search, FilterBar, soft-delete, activator, pagination

**CardForm.vue** ✅ DONE — Modal form with account dropdown, card_type select, last_four input, expiry_date, annual_fee (CurrencyInput), annual_fee_date, color picker (preset + custom), sort_order

### 6.3 Debt — `/dashboard/debts` ✅ DONE

**List Page** (`src/pages/dashboard/debts/index.astro`) ✅ DONE
- Two tabs: "Money I Owe" (MONEY_BORROWED) and "Money Owed to Me" (MONEY_LENT)
- Each debt card shows: Name, entity_name, debt_type badge, principal, remaining balance, progress bar, interest rate, monthly payment
- Summary bar at top: Total Borrowed, Total Lent, Net Position
- Filter by debt_nature, debt_type, is_active

**DebtsPage.vue** ✅ DONE — Tabbed card layout with debt_nature filter switching, summary bar (3 cards), progress bars with color coding, search, FilterBar, soft-delete, activator, pagination

**DebtForm.vue** ✅ DONE — Modal form with debt_nature toggle (I Owe / They Owe Me), debt_type select, entity_name, institution dropdown, principal_amount (CurrencyInput with auto-fill remaining_balance), remaining_balance, interest_rate, monthly_payment, start/end dates, term_months, payment_day, account dropdown, notes

**Debt Detail** — `/dashboard/debts/[id].astro` ✅ DONE
- Header: Name, entity, type, nature indicator
- Summary: Principal, Remaining, Progress %, Interest Rate, Monthly Payment with mini progress bar
- Payment history table: Date, Total Amount, Principal Portion, Interest Portion, Extra Payment, Notes
- "Record Payment" button → DebtPaymentForm: payment_date, amount, principal_portion, interest_portion, extra_payment, notes
- Amortization visualization: cumulative progress bars over time

**DebtDetail.vue** ✅ DONE — Full detail view with overview/payments tabs, summary grid, DataTable with payment CRUD, amortization progress visualization, edit/delete/restore/activate/deactivate actions

**DebtPaymentForm.vue** ✅ DONE — Inline form (non-modal) for recording/editing payments with CurrencyInput for amount/principal/interest/extra

**Sidebar Navigation** ✅ DONE — Added "Cards & Debt" section with Cards and Debts links

---

## 7. Phase 4 — Investments

### 7.1 Pinia Store

| Store | File | Key Actions |
|-------|------|-------------|
| `useInvestmentStore` | `src/stores/investment.ts` | fetchList, fetchSummary, fetchOne, create, update, remove, restore, fetchHoldings, createHolding, updateHolding, deleteHolding |

### 7.2 Investments — `/dashboard/investments`

**Portfolio Overview** (`src/pages/dashboard/investments/index.astro`)
- Summary cards at top: Total Portfolio Value, Total Cost Basis, Total Unrealized Gain/Loss (green/red), Gain/Loss %, Account Count
- Investment account list: each shows account name, portfolio_value, cost_basis, unrealized gain/loss, last_synced_at
- "Add Investment Account" button

**Create/Edit Investment** (`InvestmentForm.vue`)
- Select existing Account (only INVESTMENT type accounts), portfolio_value, cost_basis_total
- Holdings managed on detail page

**Investment Detail** — `/dashboard/investments/[id].astro`
- Holdings table: Symbol, Asset Name, Asset Type badge, Quantity, Cost Basis, Current Price, Current Value, Unrealized Gain/Loss ($), Unrealized Gain/Loss (%)
- Add/Edit Holding form: symbol, asset_name, asset_type (Stock/ETF/Crypto/Bond/Mutual Fund/Other), quantity, cost_basis, current_price, current_value, currency, purchase_date
- Unrealized gain/loss color coding: positive = green, negative = red
- Sort holdings by: value (default desc), gain/loss, symbol

**Time estimate for Phase 4**: 5-6 days

---

## 8. Phase 5 — Goals, Insurance, Invoices, Vault

### 8.1 Pinia Stores

| Store | File | Key Actions |
|-------|------|-------------|
| `useSavingsGoalStore` | `src/stores/savingsGoal.ts` | fetchList, fetchDashboard, fetchOne, create, update, contribute, remove, restore, activate, deactivate |
| `useInsuranceStore` | `src/stores/insurance.ts` | fetchList, fetchRenewals, fetchOne, create, update, remove, restore, activate, deactivate |
| `useInvoiceStore` | `src/stores/invoice.ts` | fetchList, fetchOverdue, fetchOne, create, update, markPaid, remove, restore, fetchLineItems, createLineItem, updateLineItem, deleteLineItem |
| `useVaultStore` | `src/stores/vault.ts` | fetchList, fetchExpiring, fetchOne, create (multipart), update, remove, restore, activate, deactivate |

### 8.2 Savings Goals — `/dashboard/goals`

**List Page** (`src/pages/dashboard/goals/index.astro`)
- Goal cards: Name, progress bar (current/target), percentage, remaining amount, deadline, days remaining badge, linked account
- Color: incomplete = navy, complete = cyan (celebration state)
- Filter by is_active, is_completed
- "Add Goal" button

**Create/Edit Form** (`SavingsGoalForm.vue`)
- Fields: name, target_amount, current_amount, currency, deadline, account (dropdown), icon, color

**Contribute Flow** (`GoalContribute.vue`)
- Modal: amount, create_transaction (toggle), account (if creating transaction)
- On success: show updated progress, trigger celebration if goal completed

### 8.3 Insurance — `/dashboard/insurance`

**List Page** (`src/pages/dashboard/insurance/index.astro`)
- Policy cards: Policy name, insurance_type badge, provider, premium amount + frequency, renewal date, coverage amount, deductible
- Renewal date color: within 30 days = orange, within 60 days = yellow, later = green
- Filter by insurance_type, renewal_within_days, is_active
- "Add Policy" button

**Create/Edit Form** (`InsurancePolicyForm.vue`)
- Fields: policy_name, insurance_type (Health/Auto/Home/Life/Travel/Business/Other), provider, institution (optional), policy_number, premium_amount, premium_frequency, currency, renewal_date, coverage_amount, deductible, notes

### 8.4 Invoices — `/dashboard/invoices`

**List Page** (`src/pages/dashboard/invoices/index.astro`)
- DataTable: Invoice #, Client, Issue Date, Due Date, Total, Paid, Due, Status badge
- Status colors: Draft=slate, Sent=cyan, Viewed=blue, Partial=yellow, Paid=green, Overdue=red, Cancelled=gray
- Filter by status, date range, overdue, search by client/invoice_number
- "Create Invoice" button

**Create/Edit Form** (`InvoiceForm.vue`)
- Header: invoice_number (auto-generated or manual), client_name, client_email, issue_date, due_date, currency, payment_terms, status, notes
- Line items section (editable table):
  - Each row: description, quantity, unit_price, total (auto-calculated)
  - Add/remove rows
  - Subtotal, tax_amount, total_amount auto-calculated
- "Mark as Paid" action → modal: amount_paid, create_transaction (toggle)

**Invoice Detail** — `/dashboard/invoices/[id].astro`
- Invoice preview (formatted like a real invoice)
- Line items table
- Payment status: total, paid, due
- Status timeline: Draft → Sent → Viewed → Partial/Paid
- Actions: Edit, Mark Paid, Send (copy link), Cancel, Delete

### 8.5 Document Vault — `/dashboard/vault`

**List Page** (`src/pages/dashboard/vault/index.astro`)
- Grid/List toggle view
- Each document: title, file_type icon, file_size, expiry_date (if any), linked entity
- Expiring documents highlighted (orange/red)
- Filter by file_type, content_type, expiring_within_days
- Upload button

**Upload Form** (`VaultUploadForm.vue`)
- File upload (drag-and-drop zone, accept PDF/PNG/JPG/XLSX/CSV)
- Auto-detect file_type from extension
- Fields: title, expiry_date (optional), content_type (dropdown: Account, Transaction, InsurancePolicy, DebtFacility, etc.), object_id
- Show file_size after selection

**Document Detail** — `/dashboard/vault/[id].astro`
- File preview (image/PDF inline, others download)
- Metadata: title, file_type, file_size, upload date, expiry_date
- Linked entity (clickable link)
- Actions: Edit metadata, Download, Delete

**Time estimate for Phase 5**: 10-12 days

---

## 9. Phase 6 — Dashboard & Reporting

### 9.1 Dashboard Redesign — `/dashboard`

Transform the placeholder dashboard into a real financial dashboard with widgets:

**Widget Layout** (responsive grid, 2-3 columns desktop, 1 column mobile):

| Widget | Data Source | Display |
|--------|-----------|---------|
| **Net Worth** | Sum of ASSET balances - Sum of LIABILITY balances | Large number with trend arrow |
| **Account Balances** | Account list grouped by type | Small cards: name + balance |
| **Monthly Spending** | Current month expenses by category | Donut chart (top 5 + Other) |
| **Budget Status** | Active budgets overview | Progress bars (green/yellow/red) |
| **Upcoming Bills** | `GET /bills/upcoming?days=7` | List: payee + amount + due date |
| **Recent Transactions** | `GET /transactions/recent?limit=10` | Compact list: date + payee + amount |
| **Savings Goals** | `GET /savings-goals/dashboard` | Progress bars |
| **Debt Progress** | Debt summary | Progress bars for top debts |
| **Investment Snapshot** | Investment summary | Total value + gain/loss |
| **Insurance Renewals** | `GET /insurance/renewals?days=60` | Alert list |
| **Overdue Invoices** | `GET /invoices/overdue` | Alert list |
| **Expiring Documents** | `GET /vault/expiring?days=30` | Alert list |

**Dashboard Pinia Store** — `src/stores/dashboard.ts`
- Fetches all widget data in parallel
- Caches for 5 minutes (stale-while-revalidate)
- `refreshAll()` action

**Time estimate**: 5-6 days

### 9.2 Reports Page — `/dashboard/reports`

**Report Types**:

| Report | Data Source | Visualization |
|--------|-----------|---------------|
| **Income vs Expense** | Transaction aggregation by month/quarter/year | Bar chart (grouped), line trend |
| **Category Spending** | Expense transactions grouped by category | Donut chart, horizontal bar |
| **Budget vs Actual** | Budget overview with spent amounts | Progress bars, comparison table |
| **Net Worth Over Time** | Account balance snapshots (monthly) | Line chart |
| **Cash Flow** | Income - Expenses per month | Waterfall chart |
| **Tag Spending** | Tag-based expense grouping | Horizontal bar |
| **Debt Payoff** | Remaining balance over time | Line chart per debt |
| **Investment Performance** | Holdings gain/loss | Table with sparklines |

**Report Filters**:
- Date range (presets + custom)
- Accounts (multi-select)
- Categories (multi-select)
- Currency conversion (all to base)

**Time estimate**: 8-10 days

---

## 10. Phase 7 — Polish & Production

### 10.1 UX Polish

| Item | Description |
|------|-------------|
| **Loading states** | Skeleton loaders for every list/table, spinner for forms |
| **Error handling** | Toast notifications for API errors, inline field errors |
| **Empty states** | Custom illustrations + CTAs for each feature ("No transactions yet — add your first!") |
| **Confirmation dialogs** | Destructive actions (delete, cancel, void) always confirmed |
| **Optimistic updates** | Toggle actions (activate/deactivate) update UI immediately |
| **Keyboard shortcuts** | Quick-add transaction (Ctrl+N), search (Ctrl+K), navigation |
| **Responsive design** | Mobile-first testing for all pages |
| **Accessibility** | ARIA labels, focus management, keyboard navigation |

### 10.2 Performance

| Item | Description |
|------|-------------|
| **Code splitting** | Each feature page as separate Vue chunk |
| **Lazy loading** | Vue islands with `client:visible` for below-fold |
| **Store caching** | Dropdown data cached in Pinia (don't re-fetch), invalidated on mutation |
| **Debounced search** | 300ms debounce on all search inputs |
| **Pagination** | Virtual scrolling consideration for large transaction lists |

### 10.3 Notifications & Reminders

| Reminder | Trigger | Display |
|----------|---------|---------|
| Bill due reminder | Bill.remind_me + days_before_reminder | Toast + notification badge |
| Insurance renewal | Policy.renewal_date - N days | Alert card on dashboard |
| Document expiry | Document.expiry_date - N days | Alert card on dashboard |
| Credit card due | Account.due_day approaching | Toast + notification badge |
| Annual fee | Card.annual_fee_date approaching | Toast |
| Goal deadline | SavingsGoal.deadline approaching | Progress card highlight |
| Overdue invoice | Invoice past due_date, not paid | Red alert badge |

**Time estimate for Phase 7**: 8-10 days

---

## 11. File Structure Map

```
ledgerfrontend/src/
├── middleware.ts                         # Route protection (existing)
├── pages/
│   ├── _app.ts                          # Vue app entrypoint (existing)
│   ├── auth/
│   │   └── login.astro                  # Login page (existing)
│   └── dashboard/
│       ├── index.astro                  # Dashboard (redesign in Phase 6)
│       ├── institutions/
│       │   └── index.astro              # Institution list (Phase 1)
│       ├── accounts/
│       │   ├── index.astro              # Account list (Phase 1)
│       │   └── [id].astro               # Account detail (Phase 1)
│       ├── categories/
│       │   └── index.astro              # Category tree + list (Phase 1)
│       ├── tags/
│       │   └── index.astro              # Tag management (Phase 1)
│       ├── transactions/
│       │   ├── index.astro              # Transaction list (Phase 1)
│       │   └── [id].astro               # Transaction detail (Phase 1)
│       ├── cards/
│       │   └── index.astro              # Card list (Phase 3)
│       ├── bills/
│       │   ├── index.astro              # Bill list (Phase 2)
│       │   └── [id].astro               # Bill detail + payments (Phase 2)
│       ├── budgets/
│       │   ├── index.astro              # Budget overview (Phase 2)
│       │   └── [id].astro               # Budget detail (Phase 2)
│       ├── debts/
│       │   ├── index.astro              # Debt list (Phase 3)
│       │   └── [id].astro               # Debt detail + payments (Phase 3)
│       ├── investments/
│       │   ├── index.astro              # Investment list (Phase 4)
│       │   └── [id].astro               # Investment detail + holdings (Phase 4)
│       ├── goals/
│       │   └── index.astro              # Savings goals (Phase 5)
│       ├── insurance/
│       │   └── index.astro              # Insurance policies (Phase 5)
│       ├── invoices/
│       │   ├── index.astro              # Invoice list (Phase 5)
│       │   └── [id].astro               # Invoice detail + line items (Phase 5)
│       ├── vault/
│       │   ├── index.astro              # Document list (Phase 5)
│       │   └── [id].astro               # Document detail (Phase 5)
│       └── reports/
│           └── index.astro              # Reports & analytics (Phase 6)
│
├── components/
│   ├── vue/                             # Vue interactive islands
│   │   ├── shared/                      # Reusable components (Phase 0)
│   │   │   ├── DataTable.vue
│   │   │   ├── Modal.vue
│   │   │   ├── ConfirmDialog.vue
│   │   │   ├── StatusBadge.vue
│   │   │   ├── TypeBadge.vue
│   │   │   ├── ProgressBar.vue
│   │   │   ├── EmptyState.vue
│   │   │   ├── SearchInput.vue
│   │   │   ├── FilterBar.vue
│   │   │   ├── CurrencyInput.vue
│   │   │   ├── DateRangePicker.vue
│   │   │   ├── CategoryTreeSelect.vue
│   │   │   ├── FormErrors.vue
│   │   │   ├── TagChips.vue
│   │   │   ├── LoadingSkeleton.vue
│   │   │   └── Toast.vue
│   │   ├── institutions/               # Institution components (Phase 1)
│   │   │   ├── InstitutionList.vue
│   │   │   └── InstitutionForm.vue
│   │   ├── accounts/                   # Account components (Phase 1)
│   │   │   ├── AccountList.vue
│   │   │   ├── AccountCard.vue
│   │   │   ├── AccountForm.vue
│   │   │   └── AccountDetail.vue
│   │   ├── categories/                 # Category components (Phase 1)
│   │   │   ├── CategoryTree.vue
│   │   │   ├── CategoryList.vue
│   │   │   └── CategoryForm.vue
│   │   ├── tags/                       # Tag components (Phase 1)
│   │   │   ├── TagList.vue
│   │   │   └── TagForm.vue
│   │   ├── transactions/               # Transaction components (Phase 1)
│   │   │   ├── TransactionList.vue
│   │   │   ├── TransactionForm.vue
│   │   │   ├── TransferForm.vue
│   │   │   ├── TransactionDetail.vue
│   │   │   ├── SplitEditor.vue
│   │   │   └── TransactionFilters.vue
│   │   ├── cards/                      # Card components (Phase 3)
│   │   │   ├── CardList.vue
│   │   │   ├── CardVisual.vue
│   │   │   └── CardForm.vue
│   │   ├── bills/                      # Bill components (Phase 2)
│   │   │   ├── BillList.vue
│   │   │   ├── BillForm.vue
│   │   │   ├── BillDetail.vue
│   │   │   └── BillPaymentForm.vue
│   │   ├── budgets/                    # Budget components (Phase 2)
│   │   │   ├── BudgetOverview.vue
│   │   │   ├── BudgetCard.vue
│   │   │   ├── BudgetForm.vue
│   │   │   └── BudgetDetail.vue
│   │   ├── debts/                      # Debt components (Phase 3)
│   │   │   ├── DebtList.vue
│   │   │   ├── DebtCard.vue
│   │   │   ├── DebtForm.vue
│   │   │   ├── DebtDetail.vue
│   │   │   └── DebtPaymentForm.vue
│   │   ├── investments/               # Investment components (Phase 4)
│   │   │   ├── InvestmentList.vue
│   │   │   ├── InvestmentSummary.vue
│   │   │   ├── InvestmentForm.vue
│   │   │   ├── HoldingsTable.vue
│   │   │   └── HoldingForm.vue
│   │   ├── goals/                     # Savings goal components (Phase 5)
│   │   │   ├── GoalList.vue
│   │   │   ├── GoalCard.vue
│   │   │   ├── GoalForm.vue
│   │   │   └── GoalContribute.vue
│   │   ├── insurance/                 # Insurance components (Phase 5)
│   │   │   ├── InsuranceList.vue
│   │   │   ├── InsuranceForm.vue
│   │   │   └── InsuranceDetail.vue
│   │   ├── invoices/                  # Invoice components (Phase 5)
│   │   │   ├── InvoiceList.vue
│   │   │   ├── InvoiceForm.vue
│   │   │   ├── InvoiceDetail.vue
│   │   │   ├── LineItemEditor.vue
│   │   │   └── MarkPaidModal.vue
│   │   ├── vault/                     # Vault components (Phase 5)
│   │   │   ├── DocumentList.vue
│   │   │   ├── VaultUploadForm.vue
│   │   │   └── DocumentDetail.vue
│   │   ├── dashboard/                 # Dashboard widgets (Phase 6)
│   │   │   ├── DashboardGrid.vue
│   │   │   ├── NetWorthWidget.vue
│   │   │   ├── AccountBalancesWidget.vue
│   │   │   ├── SpendingBreakdownWidget.vue
│   │   │   ├── BudgetStatusWidget.vue
│   │   │   ├── UpcomingBillsWidget.vue
│   │   │   ├── RecentTransactionsWidget.vue
│   │   │   ├── SavingsGoalsWidget.vue
│   │   │   ├── DebtProgressWidget.vue
│   │   │   ├── InvestmentSnapshotWidget.vue
│   │   │   ├── InsuranceRenewalsWidget.vue
│   │   │   ├── OverdueInvoicesWidget.vue
│   │   │   └── ExpiringDocsWidget.vue
│   │   └── reports/                   # Report components (Phase 6)
│   │       ├── ReportPage.vue
│   │       ├── IncomeExpenseChart.vue
│   │       ├── CategorySpendingChart.vue
│   │       ├── BudgetVsActualChart.vue
│   │       ├── NetWorthChart.vue
│   │       ├── CashFlowChart.vue
│   │       └── TagSpendingChart.vue
│   └── astro/                         # Astro static components
│       └── LoadingSpinner.astro       # (existing)
│
├── layouts/
│   ├── BaseLayout.astro               # (existing)
│   └── DashboardLayout.astro          # (existing — update sidebar nav)
│
├── stores/                            # Pinia stores
│   ├── base.ts                        # CRUD store base (Phase 0)
│   ├── institution.ts                 # (Phase 1)
│   ├── account.ts                     # (Phase 1)
│   ├── category.ts                    # (Phase 1)
│   ├── tag.ts                         # (Phase 1)
│   ├── transaction.ts                 # (Phase 1)
│   ├── bill.ts                        # (Phase 2)
│   ├── budget.ts                      # (Phase 2)
│   ├── card.ts                        # (Phase 3)
│   ├── debt.ts                        # (Phase 3)
│   ├── investment.ts                  # (Phase 4)
│   ├── savingsGoal.ts                 # (Phase 5)
│   ├── insurance.ts                   # (Phase 5)
│   ├── invoice.ts                     # (Phase 5)
│   ├── vault.ts                       # (Phase 5)
│   └── dashboard.ts                   # (Phase 6)
│
├── composables/                       # Vue composables
│   ├── useAuth.ts                     # (existing)
│   ├── useAccess.ts                   # (existing)
│   ├── useSubscription.ts             # (existing)
│   ├── useBillingRedirect.ts          # (existing)
│   ├── useLedgerPagination.ts         # (Phase 0)
│   ├── useLedgerFilters.ts            # (Phase 0)
│   ├── useCrudForm.ts                 # (Phase 0)
│   ├── useSoftDelete.ts               # (Phase 0)
│   ├── useActivator.ts                # (Phase 0)
│   └── useDropdownLoader.ts           # (Phase 0)
│
├── lib/
│   ├── api.ts                         # Sattabase Core API client (existing)
│   ├── ledgerApi.ts                   # Ledger backend API service (Phase 0)
│   ├── ledgerTypes.ts                 # TypeScript interfaces for all schemas (Phase 0)
│   ├── auth.ts                        # (existing)
│   ├── billing.ts                     # (existing)
│   ├── types.ts                       # Sattabase Core types (existing)
│   ├── currency.ts                    # (existing)
│   └── timezone.ts                    # (existing)
│
└── styles/
    └── global.css                     # (existing — extend with new component classes)
```

---

## 12. Component Catalog

### 12.1 Shared Components (Phase 0)

| Component | Props | Events | Description |
|-----------|-------|--------|-------------|
| `DataTable` | columns, rows, loading, total, limit, offset, sortable | page-change, sort-change, row-click | Paginated table with sorting |
| `Modal` | open, title, size (sm/md/lg/xl) | close | Overlay dialog |
| `ConfirmDialog` | open, title, message, confirmText, variant (danger/warning) | confirm, cancel | Destructive action confirmation |
| `StatusBadge` | status, colorMap | — | Colored status pill |
| `TypeBadge` | type, typeMap | — | Type indicator with icon |
| `ProgressBar` | value, max, color, showLabel, size (sm/md/lg) | — | Horizontal progress |
| `EmptyState` | title, description, icon, actionLabel | action | No-data state |
| `SearchInput` | modelValue, placeholder, debounceMs | update:modelValue | Debounced search |
| `FilterBar` | filters (config array) | filter-change, reset | Horizontal filter strip |
| `CurrencyInput` | amount, currency, currencies | update:amount, update:currency | Amount + currency selector |
| `DateRangePicker` | from, to, presets | change | Date range with presets |
| `CategoryTreeSelect` | categories, modelValue, showIncome | select | Hierarchical picker |
| `FormErrors` | errors, fieldErrors | — | Django Ninja error display |
| `TagChips` | tags, editable | add, remove | Tag display + edit |
| `LoadingSkeleton` | rows, type | — | Content placeholder |
| `Toast` | message, type (success/error/warning/info), duration | — | Notification toast |

### 12.2 Domain Components (Phases 1-5)

| Component | Phase | Key Features |
|-----------|-------|-------------|
| `InstitutionList` | 1 | Table with type badges, search, filter |
| `InstitutionForm` | 1 | Create/edit modal form |
| `AccountList` | 1 | Card grid with balance display, type grouping |
| `AccountCard` | 1 | Single account card with balance, available credit |
| `AccountForm` | 1 | Multi-section form with conditional fields |
| `AccountDetail` | 1 | Tabs: transactions, cards, bills |
| `CategoryTree` | 1 | Recursive tree with expand/collapse, drag reorder |
| `CategoryForm` | 1 | Form with parent selector |
| `TagList` | 1 | Chip grid with inline create |
| `TagForm` | 1 | Inline create: name + color |
| `TransactionList` | 1 | Full-featured table with filters, color-coded amounts |
| `TransactionForm` | 1 | Simple + Split modes, auto-currency |
| `TransferForm` | 1 | From/To account, creates linked pair |
| `TransactionDetail` | 1 | Full view with splits, tags, transfer link |
| `SplitEditor` | 1 | Add/edit/remove splits with validation |
| `TransactionFilters` | 1 | Advanced filter bar (date, type, status, category, tags, amount, payee) |
| `CardList` | 3 | Visual card layout |
| `CardVisual` | 3 | Physical card appearance |
| `CardForm` | 3 | Card creation with account link |
| `BillList` | 2 | Card grid with due date coloring |
| `BillForm` | 2 | Recurrence config, variable amount toggle |
| `BillDetail` | 2 | Payment history, action buttons |
| `BillPaymentForm` | 2 | Record payment with amount |
| `BudgetOverview` | 2 | Progress bar grid |
| `BudgetCard` | 2 | Category + progress + spent/remaining |
| `BudgetForm` | 2 | Category + amount + period |
| `BudgetDetail` | 2 | Spending breakdown by subcategory |
| `DebtList` | 3 | Two-tab view: I Owe / Owed to Me |
| `DebtCard` | 3 | Progress bar + summary |
| `DebtForm` | 3 | Nature toggle + terms |
| `DebtDetail` | 3 | Payment history + amortization |
| `DebtPaymentForm` | 3 | Principal/interest/extra breakdown |
| `InvestmentList` | 4 | Portfolio summary + account list |
| `InvestmentSummary` | 4 | Total value + gain/loss cards |
| `InvestmentForm` | 4 | Link to investment account |
| `HoldingsTable` | 4 | Sortable table with gain/loss coloring |
| `HoldingForm` | 5 | Asset details + price input |
| `GoalList` | 5 | Goal cards with progress |
| `GoalCard` | 5 | Visual progress + deadline |
| `GoalForm` | 5 | Target + deadline + account |
| `GoalContribute` | 5 | Contribution modal |
| `InsuranceList` | 5 | Policy cards with renewal alerts |
| `InsuranceForm` | 5 | Policy details + premium |
| `InsuranceDetail` | 5 | Coverage details + linked docs |
| `InvoiceList` | 5 | Table with status badges |
| `InvoiceForm` | 5 | Header + line items editor |
| `InvoiceDetail` | 5 | Invoice preview + status timeline |
| `LineItemEditor` | 5 | Add/edit/remove line items |
| `MarkPaidModal` | 5 | Payment recording + transaction creation |
| `DocumentList` | 5 | Grid/list with expiry alerts |
| `VaultUploadForm` | 5 | Drag-and-drop + entity linking |
| `DocumentDetail` | 5 | Preview + metadata |

### 12.3 Dashboard & Report Components (Phase 6)

| Component | Type | Description |
|-----------|------|-------------|
| `DashboardGrid` | Layout | Responsive widget grid |
| `NetWorthWidget` | Metric | Large number + trend |
| `AccountBalancesWidget` | List | Accounts grouped by type |
| `SpendingBreakdownWidget` | Chart | Donut chart by category |
| `BudgetStatusWidget` | List | Budget progress bars |
| `UpcomingBillsWidget` | List | Bills due within 7 days |
| `RecentTransactionsWidget` | List | Last 10 transactions |
| `SavingsGoalsWidget` | List | Goal progress bars |
| `DebtProgressWidget` | List | Debt payoff progress |
| `InvestmentSnapshotWidget` | Metric | Portfolio value + gain/loss |
| `InsuranceRenewalsWidget` | Alert | Upcoming renewals |
| `OverdueInvoicesWidget` | Alert | Unpaid overdue invoices |
| `ExpiringDocsWidget` | Alert | Documents expiring soon |
| `IncomeExpenseChart` | Chart | Bar chart by month |
| `CategorySpendingChart` | Chart | Donut/bar by category |
| `BudgetVsActualChart` | Chart | Comparison bars |
| `NetWorthChart` | Chart | Line over time |
| `CashFlowChart` | Chart | Waterfall |
| `TagSpendingChart` | Chart | Horizontal bar by tag |

---

## 13. API Integration Map

### 13.1 Endpoint → Store → Component Mapping

| Backend Endpoint | Store Action | Component(s) |
|-----------------|-------------|-------------|
| `GET /institutions` | institutionStore.fetchList | InstitutionList |
| `GET /institutions/dropdown` | institutionStore.fetchDropdown | AccountForm, BillForm, DebtForm, InsuranceForm |
| `GET /institutions/{id}` | institutionStore.fetchOne | InstitutionForm |
| `POST /institutions` | institutionStore.create | InstitutionForm |
| `PATCH /institutions/{id}` | institutionStore.update | InstitutionForm |
| `DELETE /institutions/{id}` | institutionStore.remove | InstitutionList (action) |
| `POST /institutions/{id}/restore` | institutionStore.restore | InstitutionList (action) |
| `POST /institutions/{id}/activate` | institutionStore.activate | InstitutionList (action) |
| `POST /institutions/{id}/deactivate` | institutionStore.deactivate | InstitutionList (action) |
| `GET /accounts` | accountStore.fetchList | AccountList, DashboardGrid |
| `GET /accounts/dropdown` | accountStore.fetchDropdown | TransactionForm, TransferForm, BillForm, DebtForm, GoalForm |
| `GET /accounts/{id}` | accountStore.fetchOne | AccountDetail |
| `POST /accounts` | accountStore.create | AccountForm |
| `PATCH /accounts/{id}` | accountStore.update | AccountForm |
| `POST /accounts/{id}/recalculate-balance` | accountStore.recalculateBalance | AccountDetail (action) |
| `DELETE /accounts/{id}` | accountStore.remove | AccountList (action) |
| `POST /accounts/{id}/restore` | accountStore.restore | AccountList (action) |
| `POST /accounts/{id}/activate` | accountStore.activate | AccountList (action) |
| `POST /accounts/{id}/deactivate` | accountStore.deactivate | AccountList (action) |
| `GET /categories` | categoryStore.fetchList | CategoryList |
| `GET /categories/dropdown` | categoryStore.fetchDropdown | TransactionForm, SplitEditor |
| `GET /categories/tree` | categoryStore.fetchTree | CategoryTree, CategoryTreeSelect, BudgetForm |
| `GET /categories/{id}` | categoryStore.fetchOne | CategoryForm |
| `POST /categories` | categoryStore.create | CategoryForm |
| `PATCH /categories/{id}` | categoryStore.update | CategoryForm |
| `DELETE /categories/{id}` | categoryStore.remove | CategoryList (action) |
| `POST /categories/{id}/restore` | categoryStore.restore | CategoryList (action) |
| `POST /categories/{id}/activate` | categoryStore.activate | CategoryList (action) |
| `POST /categories/{id}/deactivate` | categoryStore.deactivate | CategoryList (action) |
| `GET /tags` | tagStore.fetchList | TagList |
| `GET /tags/dropdown` | tagStore.fetchDropdown | TagChips, TransactionFilters |
| `GET /tags/{id}` | tagStore.fetchOne | TagForm |
| `POST /tags` | tagStore.create | TagForm |
| `PATCH /tags/{id}` | tagStore.update | TagForm |
| `DELETE /tags/{id}` | tagStore.remove | TagList (action) |
| `POST /tags/{id}/restore` | tagStore.restore | TagList (action) |
| `GET /transactions` | transactionStore.fetchList | TransactionList |
| `GET /transactions/recent` | transactionStore.fetchRecent | RecentTransactionsWidget, DashboardGrid |
| `GET /transactions/{id}` | transactionStore.fetchOne | TransactionDetail |
| `POST /transactions` | transactionStore.create | TransactionForm |
| `PATCH /transactions/{id}` | transactionStore.update | TransactionForm |
| `POST /transactions/transfer` | transactionStore.createTransfer | TransferForm |
| `DELETE /transactions/{id}` | transactionStore.remove | TransactionList (action) |
| `POST /transactions/{id}/restore` | transactionStore.restore | TransactionList (action) |
| `GET /transactions/{id}/splits` | transactionStore.fetchSplits | SplitEditor, TransactionDetail |
| `POST /transactions/{id}/splits` | transactionStore.createSplit | SplitEditor |
| `PATCH /transactions/{id}/splits/{sid}` | transactionStore.updateSplit | SplitEditor |
| `DELETE /transactions/{id}/splits/{sid}` | transactionStore.deleteSplit | SplitEditor |
| `GET /transactions/{id}/tags` | transactionStore.fetchTags | TagChips, TransactionDetail |
| `POST /transactions/{id}/tags` | transactionStore.addTag | TagChips |
| `POST /transactions/{id}/tags/bulk` | transactionStore.bulkSetTags | TagChips |
| `DELETE /transactions/{id}/tags/{tag_id}` | transactionStore.removeTag | TagChips |
| `GET /cards` | cardStore.fetchList | CardList |
| `GET /cards/dropdown` | cardStore.fetchDropdown | TransactionForm |
| `GET /cards/{id}` | cardStore.fetchOne | CardVisual |
| `POST /cards` | cardStore.create | CardForm |
| `PATCH /cards/{id}` | cardStore.update | CardForm |
| `DELETE /cards/{id}` | cardStore.remove | CardList (action) |
| `POST /cards/{id}/restore` | cardStore.restore | CardList (action) |
| `POST /cards/{id}/activate` | cardStore.activate | CardList (action) |
| `POST /cards/{id}/deactivate` | cardStore.deactivate | CardList (action) |
| `GET /bills` | billStore.fetchList | BillList |
| `GET /bills/upcoming` | billStore.fetchUpcoming | UpcomingBillsWidget, DashboardGrid |
| `GET /bills/{id}` | billStore.fetchOne | BillDetail |
| `POST /bills` | billStore.create | BillForm |
| `PATCH /bills/{id}` | billStore.update | BillForm |
| `POST /bills/{id}/generate` | billStore.generateTransaction | BillDetail (action) |
| `DELETE /bills/{id}` | billStore.remove | BillList (action) |
| `POST /bills/{id}/restore` | billStore.restore | BillList (action) |
| `POST /bills/{id}/pause` | billStore.pause | BillDetail (action) |
| `POST /bills/{id}/cancel` | billStore.cancel | BillDetail (action) |
| `POST /bills/{id}/reactivate` | billStore.reactivate | BillDetail (action) |
| `GET /bills/{id}/payments` | billStore.fetchPayments | BillDetail |
| `POST /bills/{id}/payments` | billStore.createPayment | BillPaymentForm |
| `PATCH /bills/{id}/payments/{pid}` | billStore.updatePayment | BillPaymentForm |
| `GET /debts` | debtStore.fetchList | DebtList |
| `GET /debts/summary` | debtStore.fetchSummary | DebtProgressWidget, DashboardGrid |
| `GET /debts/{id}` | debtStore.fetchOne | DebtDetail |
| `POST /debts` | debtStore.create | DebtForm |
| `PATCH /debts/{id}` | debtStore.update | DebtForm |
| `DELETE /debts/{id}` | debtStore.remove | DebtList (action) |
| `POST /debts/{id}/restore` | debtStore.restore | DebtList (action) |
| `POST /debts/{id}/activate` | debtStore.activate | DebtList (action) |
| `POST /debts/{id}/deactivate` | debtStore.deactivate | DebtList (action) |
| `GET /debts/{id}/payments` | debtStore.fetchPayments | DebtDetail |
| `POST /debts/{id}/payments` | debtStore.createPayment | DebtPaymentForm |
| `PATCH /debts/{id}/payments/{pid}` | debtStore.updatePayment | DebtPaymentForm |
| `GET /budgets` | budgetStore.fetchList | BudgetOverview |
| `GET /budgets/overview` | budgetStore.fetchOverview | BudgetStatusWidget, DashboardGrid |
| `GET /budgets/{id}` | budgetStore.fetchOne | BudgetDetail |
| `POST /budgets` | budgetStore.create | BudgetForm |
| `PATCH /budgets/{id}` | budgetStore.update | BudgetForm |
| `DELETE /budgets/{id}` | budgetStore.remove | BudgetOverview (action) |
| `POST /budgets/{id}/restore` | budgetStore.restore | BudgetOverview (action) |
| `POST /budgets/{id}/activate` | budgetStore.activate | BudgetOverview (action) |
| `POST /budgets/{id}/deactivate` | budgetStore.deactivate | BudgetOverview (action) |
| `GET /investments` | investmentStore.fetchList | InvestmentList |
| `GET /investments/summary` | investmentStore.fetchSummary | InvestmentSnapshotWidget, DashboardGrid |
| `GET /investments/{id}` | investmentStore.fetchOne | InvestmentDetail |
| `POST /investments` | investmentStore.create | InvestmentForm |
| `PATCH /investments/{id}` | investmentStore.update | InvestmentForm |
| `DELETE /investments/{id}` | investmentStore.remove | InvestmentList (action) |
| `POST /investments/{id}/restore` | investmentStore.restore | InvestmentList (action) |
| `GET /investments/{id}/holdings` | investmentStore.fetchHoldings | HoldingsTable |
| `POST /investments/{id}/holdings` | investmentStore.createHolding | HoldingForm |
| `PATCH /investments/{id}/holdings/{hid}` | investmentStore.updateHolding | HoldingForm |
| `DELETE /investments/{id}/holdings/{hid}` | investmentStore.deleteHolding | HoldingsTable (action) |
| `GET /savings-goals` | savingsGoalStore.fetchList | GoalList |
| `GET /savings-goals/dashboard` | savingsGoalStore.fetchDashboard | SavingsGoalsWidget, DashboardGrid |
| `GET /savings-goals/{id}` | savingsGoalStore.fetchOne | GoalForm |
| `POST /savings-goals` | savingsGoalStore.create | GoalForm |
| `PATCH /savings-goals/{id}` | savingsGoalStore.update | GoalForm |
| `POST /savings-goals/{id}/contribute` | savingsGoalStore.contribute | GoalContribute |
| `DELETE /savings-goals/{id}` | savingsGoalStore.remove | GoalList (action) |
| `POST /savings-goals/{id}/restore` | savingsGoalStore.restore | GoalList (action) |
| `POST /savings-goals/{id}/activate` | savingsGoalStore.activate | GoalList (action) |
| `POST /savings-goals/{id}/deactivate` | savingsGoalStore.deactivate | GoalList (action) |
| `GET /insurance` | insuranceStore.fetchList | InsuranceList |
| `GET /insurance/renewals` | insuranceStore.fetchRenewals | InsuranceRenewalsWidget, DashboardGrid |
| `GET /insurance/{id}` | insuranceStore.fetchOne | InsuranceDetail |
| `POST /insurance` | insuranceStore.create | InsuranceForm |
| `PATCH /insurance/{id}` | insuranceStore.update | InsuranceForm |
| `DELETE /insurance/{id}` | insuranceStore.remove | InsuranceList (action) |
| `POST /insurance/{id}/restore` | insuranceStore.restore | InsuranceList (action) |
| `POST /insurance/{id}/activate` | insuranceStore.activate | InsuranceList (action) |
| `POST /insurance/{id}/deactivate` | insuranceStore.deactivate | InsuranceList (action) |
| `GET /invoices` | invoiceStore.fetchList | InvoiceList |
| `GET /invoices/overdue` | invoiceStore.fetchOverdue | OverdueInvoicesWidget, DashboardGrid |
| `GET /invoices/{id}` | invoiceStore.fetchOne | InvoiceDetail |
| `POST /invoices` | invoiceStore.create | InvoiceForm |
| `PATCH /invoices/{id}` | invoiceStore.update | InvoiceForm |
| `POST /invoices/{id}/mark-paid` | invoiceStore.markPaid | MarkPaidModal |
| `DELETE /invoices/{id}` | invoiceStore.remove | InvoiceList (action) |
| `POST /invoices/{id}/restore` | invoiceStore.restore | InvoiceList (action) |
| `GET /invoices/{id}/line-items` | invoiceStore.fetchLineItems | LineItemEditor |
| `POST /invoices/{id}/line-items` | invoiceStore.createLineItem | LineItemEditor |
| `PATCH /invoices/{id}/line-items/{iid}` | invoiceStore.updateLineItem | LineItemEditor |
| `DELETE /invoices/{id}/line-items/{iid}` | invoiceStore.deleteLineItem | LineItemEditor |
| `GET /vault` | vaultStore.fetchList | DocumentList |
| `GET /vault/expiring` | vaultStore.fetchExpiring | ExpiringDocsWidget, DashboardGrid |
| `GET /vault/{id}` | vaultStore.fetchOne | DocumentDetail |
| `POST /vault` | vaultStore.create | VaultUploadForm |
| `PATCH /vault/{id}` | vaultStore.update | VaultUploadForm |
| `DELETE /vault/{id}` | vaultStore.remove | DocumentList (action) |
| `POST /vault/{id}/restore` | vaultStore.restore | DocumentList (action) |
| `POST /vault/{id}/activate` | vaultStore.activate | DocumentList (action) |
| `POST /vault/{id}/deactivate` | vaultStore.deactivate | DocumentList (action) |

---

## 14. Pinia Store Catalog

| Store | File | State Shape | Key Getters | Key Actions |
|-------|------|-------------|-------------|-------------|
| `useInstitutionStore` | `institution.ts` | items[], dropdown[], current, loading, total, filters | activeItems, byType | fetchList, fetchDropdown, fetchOne, create, update, remove, restore, activate, deactivate |
| `useAccountStore` | `account.ts` | items[], dropdown[], current, loading, total, filters | activeItems, assetAccounts, liabilityAccounts, investmentAccounts, totalAssets, totalLiabilities, netWorth | fetchList, fetchDropdown, fetchOne, create, update, recalculateBalance, remove, restore, activate, deactivate |
| `useCategoryStore` | `category.ts` | items[], dropdown[], tree[], current, loading, total, filters | activeItems, incomeCategories, expenseCategories, flatList | fetchList, fetchDropdown, fetchTree, fetchOne, create, update, remove, restore, activate, deactivate |
| `useTagStore` | `tag.ts` | items[], dropdown[], current, loading, total, filters | activeItems | fetchList, fetchDropdown, fetchOne, create, update, remove, restore |
| `useTransactionStore` | `transaction.ts` | items[], recent[], current, splits[], tags[], loading, total, filters | byAccount, byCategory, byType | fetchList, fetchRecent, fetchOne, create, update, createTransfer, remove, restore, fetchSplits, createSplit, updateSplit, deleteSplit, fetchTags, addTag, bulkSetTags, removeTag |
| `useBillStore` | `bill.ts` | items[], upcoming[], current, payments[], loading, total, filters | activeBills, pausedBills, cancelledBills | fetchList, fetchUpcoming, fetchOne, create, update, generateTransaction, remove, restore, pause, cancel, reactivate, fetchPayments, createPayment, updatePayment |
| `useBudgetStore` | `budget.ts` | items[], overview[], current, loading, total, filters | onTrack, approaching, overBudget | fetchList, fetchOverview, fetchOne, create, update, remove, restore, activate, deactivate |
| `useCardStore` | `card.ts` | items[], dropdown[], current, loading, total, filters | debitCards, creditCards | fetchList, fetchDropdown, fetchOne, create, update, remove, restore, activate, deactivate |
| `useDebtStore` | `debt.ts` | items[], summary, current, payments[], loading, total, filters | borrowed, lent | fetchList, fetchSummary, fetchOne, create, update, remove, restore, activate, deactivate, fetchPayments, createPayment, updatePayment |
| `useInvestmentStore` | `investment.ts` | items[], summary, current, holdings[], loading, total | totalValue, totalGainLoss | fetchList, fetchSummary, fetchOne, create, update, remove, restore, fetchHoldings, createHolding, updateHolding, deleteHolding |
| `useSavingsGoalStore` | `savingsGoal.ts` | items[], dashboard[], current, loading, total, filters | activeGoals, completedGoals | fetchList, fetchDashboard, fetchOne, create, update, contribute, remove, restore, activate, deactivate |
| `useInsuranceStore` | `insurance.ts` | items[], renewals[], current, loading, total, filters | byType | fetchList, fetchRenewals, fetchOne, create, update, remove, restore, activate, deactivate |
| `useInvoiceStore` | `invoice.ts` | items[], overdue[], current, lineItems[], loading, total, filters | byStatus, totalRevenue, totalOutstanding | fetchList, fetchOverdue, fetchOne, create, update, markPaid, remove, restore, fetchLineItems, createLineItem, updateLineItem, deleteLineItem |
| `useVaultStore` | `vault.ts` | items[], expiring[], current, loading, total, filters | byFileType | fetchList, fetchExpiring, fetchOne, create, update, remove, restore, activate, deactivate |
| `useDashboardStore` | `dashboard.ts` | loading, lastFetched, all widget data | isStale (>5min) | fetchAll, refreshAll |

---

## 15. Page & Route Catalog

| Route | Astro Page | Primary Vue Island | Phase |
|-------|-----------|-------------------|-------|
| `/auth/login` | `auth/login.astro` | `LoginForm.vue` | ✅ Existing |
| `/dashboard` | `dashboard/index.astro` | `DashboardGrid.vue` | 6 |
| `/dashboard/institutions` | `dashboard/institutions/index.astro` | `InstitutionList.vue` | 1 |
| `/dashboard/accounts` | `dashboard/accounts/index.astro` | `AccountList.vue` | 1 |
| `/dashboard/accounts/[id]` | `dashboard/accounts/[id].astro` | `AccountDetail.vue` | 1 |
| `/dashboard/categories` | `dashboard/categories/index.astro` | `CategoryTree.vue` | 1 |
| `/dashboard/tags` | `dashboard/tags/index.astro` | `TagList.vue` | 1 |
| `/dashboard/transactions` | `dashboard/transactions/index.astro` | `TransactionList.vue` | 1 |
| `/dashboard/transactions/[id]` | `dashboard/transactions/[id].astro` | `TransactionDetail.vue` | 1 |
| `/dashboard/cards` | `dashboard/cards/index.astro` | `CardList.vue` | 3 |
| `/dashboard/bills` | `dashboard/bills/index.astro` | `BillList.vue` | 2 |
| `/dashboard/bills/[id]` | `dashboard/bills/[id].astro` | `BillDetail.vue` | 2 |
| `/dashboard/budgets` | `dashboard/budgets/index.astro` | `BudgetOverview.vue` | 2 |
| `/dashboard/budgets/[id]` | `dashboard/budgets/[id].astro` | `BudgetDetail.vue` | 2 |
| `/dashboard/debts` | `dashboard/debts/index.astro` | `DebtList.vue` | 3 |
| `/dashboard/debts/[id]` | `dashboard/debts/[id].astro` | `DebtDetail.vue` | 3 |
| `/dashboard/investments` | `dashboard/investments/index.astro` | `InvestmentList.vue` | 4 |
| `/dashboard/investments/[id]` | `dashboard/investments/[id].astro` | `InvestmentDetail.vue` | 4 |
| `/dashboard/goals` | `dashboard/goals/index.astro` | `GoalList.vue` | 5 |
| `/dashboard/insurance` | `dashboard/insurance/index.astro` | `InsuranceList.vue` | 5 |
| `/dashboard/invoices` | `dashboard/invoices/index.astro` | `InvoiceList.vue` | 5 |
| `/dashboard/invoices/[id]` | `dashboard/invoices/[id].astro` | `InvoiceDetail.vue` | 5 |
| `/dashboard/vault` | `dashboard/vault/index.astro` | `DocumentList.vue` | 5 |
| `/dashboard/vault/[id]` | `dashboard/vault/[id].astro` | `DocumentDetail.vue` | 5 |
| `/dashboard/reports` | `dashboard/reports/index.astro` | `ReportPage.vue` | 6 |

**Total: 25 routes** (2 existing + 23 new)

---

## 16. Implementation Priority Matrix

| Priority | Phase | Module | Est. Days | Dependencies | User Impact |
|----------|-------|--------|-----------|-------------|-------------|
| **P0** | 0 | Foundation (types, API, stores, components) | 11 | None | Enables all features |
| **P1** | 1 | Institutions + Accounts | 5 | P0 | Core — everything depends on accounts |
| **P1** | 1 | Categories + Tags | 3 | P0 | Core — transactions need categories |
| **P1** | 1 | Transactions + Splits + Transfers | 7 | P1 (accounts, categories) | **Heart of the app** |
| **P2** | 2 | Bills + BillPayments | 5 | P1 | Recurring payment tracking |
| **P2** | 2 | Budgets | 3 | P1 (categories) | Spending limits |
| **P3** | 3 | Cards | 2 | P1 (accounts) | Card management |
| **P3** | 3 | Debts + DebtPayments | 5 | P1 (institutions, accounts) | Loan tracking |
| **P4** | 4 | Investments + Holdings | 5 | P1 (accounts) | Portfolio management |
| **P5** | 5 | Savings Goals | 3 | P1 (accounts) | Goal-based saving |
| **P5** | 5 | Insurance | 2 | P1 (institutions) | Policy tracking |
| **P5** | 5 | Invoices + LineItems | 4 | None (standalone) | Freelancer invoicing |
| **P5** | 5 | Document Vault | 3 | None (standalone) | Document management |
| **P6** | 6 | Dashboard Widgets | 5 | P1-P5 | **First thing users see** |
| **P6** | 6 | Reports & Analytics | 8 | P1-P5 | Financial insights |
| **P7** | 7 | Polish & Production | 8 | P1-P6 | Production readiness |

**Total estimated effort: ~79 days (~16 weeks / ~4 months for one developer)**

### Critical Path

```
P0 (Foundation) → P1 (Accounts + Categories + Transactions) → P2 (Bills + Budgets) → P6 (Dashboard + Reports)
                                                                                     ↑
                                                              P3 (Cards + Debts) ────┘
                                                              P4 (Investments) ──────┘
                                                              P5 (Goals/Insurance/Invoices/Vault) ─┘
```

The critical path is **P0 → P1 → P6**, because the dashboard depends on all domain data. However, a minimal viable dashboard can be built with just accounts and transactions (P0 + P1 + partial P6).

---

## 17. Cross-Cutting Concerns

### 17.1 Multi-Currency Display

Every monetary amount in the UI must be formatted using the existing `formatCurrency()` utility from `src/lib/currency.ts`. Rules:

| Scenario | Display | Example |
|----------|---------|---------|
| Same as base currency | Amount with symbol | $1,250.00 |
| Different from base | Amount with code | €89.50 |
| Transaction detail (foreign) | Original + Base equivalent | €89.50 (~$97.23 @ 1.0864) |
| Aggregation/reports | All in base currency | $4,523.12 |
| Zero-decimal currency | No decimals | ¥15,000 |
| Unknown currency | Raw code | XYZ 100.00 |

### 17.2 Timezone Handling

All dates from the backend are UTC. Display rules:

| Data Type | Display Method | Example |
|-----------|---------------|---------|
| Transaction date | `formatDateShort()` in user timezone | "Jan 15, 2026" |
| Created/Updated timestamps | `formatDateTime()` in user timezone | "Jan 15, 2026, 3:45 PM" |
| Relative times (activity feed) | `formatRelativeTime()` | "2 hours ago" |
| Due dates (bills, invoices) | `formatDateShort()` | "Feb 1, 2026" |
| Time-only (reminders) | `formatTimeOnly()` | "9:00 AM" |

### 17.3 Error Handling

| Error Type | Display | Action |
|------------|---------|--------|
| 401 Unauthorized | Redirect to login | Auto-refresh attempt first |
| 403 Forbidden | Toast: "You don't have access" | Stay on page |
| 404 Not Found | Empty state or redirect | Show "not found" message |
| 400 Validation Error | Inline field errors | Highlight fields, show messages |
| 500 Server Error | Toast: "Something went wrong" | Retry button |
| Network Error | Toast: "Network error" | Retry button |
| Rate Limited (429) | Toast: "Too many requests" | Auto-retry after delay |

### 17.4 Loading States

| State | Component | Pattern |
|-------|-----------|---------|
| Initial page load | `LoadingSkeleton` | Skeleton shimmer matching page layout |
| Form submission | Button spinner | Disable button, show spinner |
| Inline mutation | Optimistic update | Update UI immediately, revert on error |
| Background refresh | Subtle indicator | Small spinner in header |

### 17.5 Feature Gating

Use the existing `useAccess()` composable to gate features:

```typescript
// Example: Investment features only for Premium plan
const { hasAccess } = useAccess()
const canAccessInvestments = hasAccess('investments')

// Example: Budget limits
const { getLimit } = useAccess()
const maxBudgets = getLimit('budgets', 10)
```

### 17.6 Dark Mode

All components must work in both light and dark mode. The existing Tailwind theme defines dark variants. Rules:

- Use `dark:` variant classes for component-level overrides
- Test every component in both modes
- Charts must have dark-mode color palettes
- Images/icons must have appropriate contrast in both modes

### 17.7 Responsive Design

| Breakpoint | Layout | Navigation |
|-----------|--------|------------|
| < 640px (mobile) | Single column, stacked cards | Hamburger menu |
| 640-1024px (tablet) | 2 columns | Collapsible sidebar |
| > 1024px (desktop) | 3 columns for dashboard, 2 for lists | Full sidebar |

Specific responsive rules:
- DataTables become card lists on mobile
- Side-by-side forms stack vertically on mobile
- Modal dialogs become full-screen on mobile
- Dashboard widgets stack in single column on mobile

---

## 18. Testing Strategy

### 18.1 Unit Tests (Vitest + Vue Test Utils)

| What to Test | Tool | Priority |
|-------------|------|----------|
| Pinia store actions | Vitest | P0 — test all CRUD flows |
| Utility functions (currency, timezone) | Vitest | P1 — test edge cases |
| Vue component rendering | Vue Test Utils | P2 — test key interactions |
| Form validation | Vitest | P2 — test Zod validators |

### 18.2 Integration Tests

| What to Test | Tool | Priority |
|-------------|------|----------|
| API service calls (mocked) | Vitest + MSW | P1 — test all endpoint wrappers |
| Store + API integration | Vitest | P1 — test fetch → state → render flow |
| Auth flow end-to-end | Playwright | P2 — test login → dashboard → action |

### 18.3 Visual Regression (Optional)

| What to Test | Tool | Priority |
|-------------|------|----------|
| Component screenshots | Playwright screenshots | P3 |
| Dark mode comparison | Playwright | P3 |

---

## 19. Risk & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **API contract mismatch** (frontend types don't match backend schemas) | High | High | Generate TypeScript types from backend schema definitions; add CI check for type consistency |
| **Currency formatting bugs** (zero-decimal currencies, missing symbols) | Medium | Medium | Comprehensive test suite for `formatCurrency()` with 38 currencies; use backend metadata as source of truth |
| **Performance with large transaction lists** (>10K rows) | Medium | High | Implement virtual scrolling; server-side pagination (already supported); limit default page size to 25 |
| **Chart library weight** (bundle size) | Low | Medium | Use lightweight chart library (Chart.js or ApexCharts); lazy-load chart components |
| **Mobile UX complexity** (transaction form on small screens) | Medium | Medium | Mobile-first design for forms; step-by-step wizard on mobile; full form on desktop |
| **Cross-domain auth edge cases** (token expiry during action) | Low | High | Auto-refresh already implemented; test 401 mid-action scenarios; show clear "session expired" message |
| **File upload security** (vault) | Low | Medium | Validate file type on frontend; enforce size limits; rely on backend validation |
| **Dark mode contrast issues** | Medium | Low | Systematic dark-mode testing; use established palette colors; test with accessibility tools |

---

## Appendix A — DashboardLayout Sidebar Navigation

The existing sidebar needs navigation links added for all feature pages:

```
Ledger Logo
───────────
Dashboard       → /dashboard
───────────
Accounts        → /dashboard/accounts
Transactions    → /dashboard/transactions
Categories      → /dashboard/categories
Tags            → /dashboard/tags
───────────
Bills           → /dashboard/bills
Budgets         → /dashboard/budgets
───────────
Cards           → /dashboard/cards
Debts           → /dashboard/debts
───────────
Investments     → /dashboard/investments
───────────
Goals           → /dashboard/goals
Insurance       → /dashboard/insurance
Invoices        → /dashboard/invoices
Vault           → /dashboard/vault
───────────
Reports         → /dashboard/reports
───────────
User Info
Sign Out
```

## Appendix B — Chart Library Recommendation

For the reporting phase (Phase 6), evaluate these options:

| Library | Size | Vue Integration | Chart Types | Recommendation |
|---------|------|----------------|-------------|---------------|
| **Chart.js** + vue-chartjs | ~65KB gzip | Good | Bar, Line, Pie, Doughnut, Radar | ✅ Best balance of size, features, Vue support |
| ApexCharts + vue3-apexcharts | ~130KB gzip | Excellent | All types + sparklines + range | Good if more interactivity needed |
| ECharts + vue-echarts | ~300KB+ (tree-shakeable) | Good | All types + maps | Overkill for personal finance charts |
| D3.js | Variable | Manual | Everything | Too low-level, too much custom code |

**Recommended: Chart.js + vue-chartjs** — smallest bundle, sufficient chart types, good Vue 3 integration, active maintenance.

## Appendix C — New Tailwind Component Classes to Add

Add these to `src/styles/global.css` alongside existing component classes:

```css
/* Financial-specific components */
.debit-amount { @apply text-debit font-semibold; }
.credit-amount { @apply text-credit font-semibold; }
.neutral-amount { @apply text-slate-600 dark:text-slate-400 font-semibold; }

/* Status indicators */
.status-active { @apply bg-credit/10 text-credit border border-credit/20; }
.status-paused { @apply bg-warm/10 text-warm border border-warm/20; }
.status-cancelled { @apply bg-slate-100 text-slate-500 border border-slate-200 dark:bg-slate-800 dark:text-slate-400; }
.status-overdue { @apply bg-debit/10 text-debit border border-debit/20; }
.status-pending { @apply bg-cyan/10 text-cyan border border-cyan/20; }

/* Type badges */
.type-asset { @apply bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/20 dark:text-blue-300; }
.type-liability { @apply bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/20 dark:text-red-300; }
.type-investment { @apply bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-900/20 dark:text-purple-300; }

/* Progress bars */
.progress-safe { @apply bg-credit; }
.progress-warning { @apply bg-warm; }
.progress-danger { @apply bg-debit; }

/* Card-like visual for physical cards */
.card-visual { @apply rounded-xl p-5 text-white shadow-lg; }

/* Sidebar navigation */
.nav-item { @apply flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors; }
.nav-item-active { @apply bg-cyan/10 text-cyan font-medium; }
.nav-item-inactive { @apply text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800; }
```
