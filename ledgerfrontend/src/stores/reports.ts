/**
 * Reports Store — Aggregates and processes financial data for the
 * Reports page at /dashboard/reports.
 *
 * Unlike domain CRUD stores, this store does NOT extend the base CRUD
 * pattern. It fetches bulk transaction data with date-range filters and
 * aggregates it client-side into report-ready structures. It also pulls
 * budget overview, debt, investment, and category/tag data for
 * cross-referencing.
 *
 * Key features:
 *   - fetchReportData() — parallel fetch of all data needed for reports
 *   - Client-side aggregation: income vs expense by month, category spending,
 *     tag spending, cash flow, net worth composition
 *   - Date range filter support via TransactionFilter.date_from / date_to
 *   - Computed getters for each report type
 */

import { defineStore } from "pinia";
import { ledgerApi } from "@/lib/ledgerApi";
import { extractErrorMessage } from "./base";
import type {
  TransactionOut,
  TransactionFilter,
  CategoryOut,
  CategoryListOut,
  TagOut,
  BudgetListOut,
  DebtFacilityOut,
  DebtSummary,
  InvestmentAccountOut,
  InvestmentSummary,
  HoldingOut,
  AccountOut,
} from "@/lib/ledgerTypes";

// ── Aggregation Types ──

/** Monthly income vs expense bucket. */
export interface MonthlyBucket {
  month: string; // "YYYY-MM"
  income: number;
  expense: number;
  net: number; // income - expense
}

/** Category spending aggregate. */
export interface CategorySpending {
  categoryId: number;
  categoryName: string;
  icon: string;
  color: string;
  isIncome: boolean;
  amount: number;
  transactionCount: number;
}

/** Tag spending aggregate. */
export interface TagSpending {
  tagId: number;
  tagName: string;
  tagColor: string;
  amount: number;
  transactionCount: number;
}

/** Single investment holding for performance table. */
export interface HoldingPerformance {
  investmentId: number;
  investmentAccountId: number;
  symbol: string;
  assetName: string;
  assetType: string;
  quantity: number;
  costBasis: number;
  currentValue: number;
  unrealizedGainLoss: number;
  gainLossPercent: number;
}

/** Debt payoff entry. */
export interface DebtPayoffEntry {
  id: number;
  name: string;
  debtType: string;
  principalAmount: number;
  remainingBalance: number;
  paidOff: number;
  progressPercent: number;
  monthlyPayment: number;
  interestRate: number;
}

/** Budget vs Actual entry. */
export interface BudgetVsActual {
  id: number;
  categoryName: string;
  amount: number;
  spentAmount: number;
  remaining: number;
  percentUsed: number;
  period: string;
  currency: string;
}

/** Cash flow month (extended MonthlyBucket with cumulative). */
export interface CashFlowMonth extends MonthlyBucket {
  cumulative: number;
}

export const useReportsStore = defineStore("reports", {
  state: () => ({
    // ── Loading state ──
    loading: false,
    loadingAction: "",
    error: null as string | null,

    // ── Raw data from API ──
    transactions: [] as TransactionOut[],
    categories: [] as CategoryOut[],
    categoryDropdown: [] as CategoryListOut[],
    tags: [] as TagOut[],
    budgetOverview: [] as BudgetListOut[],
    debts: [] as DebtFacilityOut[],
    debtSummary: null as DebtSummary | null,
    investments: [] as InvestmentAccountOut[],
    investmentSummary: null as InvestmentSummary | null,
    holdings: [] as HoldingOut[],
    accounts: [] as AccountOut[],

    // ── Transaction-to-tag associations (fetched during report load) ──
    transactionTagMap: {} as Record<number, number[]>,
    tagFetchComplete: false,

    // ── Date range filter ──
    dateFrom: "" as string,
    dateTo: "" as string,

    // ── Cache tracking ──
    lastFetched: null as number | null,
  }),

  getters: {
    /** Whether any data has been loaded. */
    hasData(): boolean {
      return this.transactions.length > 0 || this.budgetOverview.length > 0;
    },

    // ── 1. Income vs Expense by Month ──

    /** Monthly income/expense buckets sorted by month. */
    incomeExpenseByMonth(): MonthlyBucket[] {
      const buckets = new Map<string, MonthlyBucket>();

      for (const txn of this.transactions) {
        if (txn.is_deleted || txn.transaction_type === "TRANSFER") continue;
        const month = txn.date.substring(0, 7); // "YYYY-MM"
        if (!buckets.has(month)) {
          buckets.set(month, { month, income: 0, expense: 0, net: 0 });
        }
        const bucket = buckets.get(month)!;
        const amount = parseFloat(txn.amount_base || txn.amount_original || "0");

        if (txn.transaction_type === "INCOME") {
          bucket.income += amount;
        } else if (txn.transaction_type === "EXPENSE") {
          bucket.expense += amount;
        }
        bucket.net = bucket.income - bucket.expense;
      }

      return Array.from(buckets.values()).sort((a, b) => a.month.localeCompare(b.month));
    },

    /** Total income across all filtered transactions. */
    totalIncome(): number {
      return this.transactions
        .filter((t) => !t.is_deleted && t.transaction_type === "INCOME")
        .reduce((sum, t) => sum + parseFloat(t.amount_base || t.amount_original || "0"), 0);
    },

    /** Total expenses across all filtered transactions. */
    totalExpenses(): number {
      return this.transactions
        .filter((t) => !t.is_deleted && t.transaction_type === "EXPENSE")
        .reduce((sum, t) => sum + parseFloat(t.amount_base || t.amount_original || "0"), 0);
    },

    /** Net income (income - expenses). */
    netIncome(): number {
      return this.totalIncome - this.totalExpenses;
    },

    // ── 2. Category Spending ──

    /** Expense spending grouped by category. */
    categorySpending(): CategorySpending[] {
      const catMap = new Map<number, CategorySpending>();
      const catNameMap = new Map(this.categoryDropdown.map((c) => [c.id, c]));
      const catFullMap = new Map(this.categories.map((c) => [c.id, c]));

      for (const txn of this.transactions) {
        if (txn.is_deleted || !txn.category_id) continue;
        const amount = parseFloat(txn.amount_base || txn.amount_original || "0");
        const isIncome = txn.transaction_type === "INCOME";

        if (!catMap.has(txn.category_id)) {
          const cat = catNameMap.get(txn.category_id);
          const catFull = catFullMap.get(txn.category_id);
          catMap.set(txn.category_id, {
            categoryId: txn.category_id,
            categoryName: cat?.name || `Category #${txn.category_id}`,
            icon: cat?.icon || catFull?.icon || "",
            color: cat?.color || catFull?.color || "#6366f1",
            isIncome,
            amount: 0,
            transactionCount: 0,
          });
        }

        const entry = catMap.get(txn.category_id)!;
        entry.amount += amount;
        entry.transactionCount += 1;
      }

      return Array.from(catMap.values()).sort((a, b) => b.amount - a.amount);
    },

    /** Top 8 expense categories (for donut chart). */
    topExpenseCategories(): CategorySpending[] {
      return this.categorySpending.filter((c) => !c.isIncome).slice(0, 8);
    },

    /** Total expense category spending. */
    totalCategoryExpense(): number {
      return this.categorySpending.filter((c) => !c.isIncome).reduce((sum, c) => sum + c.amount, 0);
    },

    // ── 3. Budget vs Actual ──

    /** Budget overview with category names resolved. */
    budgetVsActual(): BudgetVsActual[] {
      const catNameMap = new Map(this.categoryDropdown.map((c) => [c.id, c]));

      return this.budgetOverview
        .filter((b) => b.is_active !== false)
        .map((b) => {
          const cat = catNameMap.get(b.category_id);
          return {
            id: b.id,
            categoryName: cat?.name || `Category #${b.category_id}`,
            amount: parseFloat(b.amount || "0"),
            spentAmount: parseFloat(b.spent_amount || "0"),
            remaining: parseFloat(b.remaining || "0"),
            percentUsed: b.percent_used,
            period: b.period,
            currency: b.currency,
          };
        })
        .sort((a, b) => b.percentUsed - a.percentUsed);
    },

    // ── 4. Net Worth Composition ──

    /** Account balances grouped by type for net worth report. */
    netWorthComposition(): { type: string; total: number; accounts: AccountOut[] }[] {
      const groups: Record<string, { total: number; accounts: AccountOut[] }> = {};

      for (const acct of this.accounts) {
        if (acct.is_deleted) continue;
        const type = acct.account_type;
        if (!groups[type]) groups[type] = { type, total: 0, accounts: [] };
        groups[type].total += parseFloat(acct.current_balance || "0");
        groups[type].accounts.push(acct);
      }

      return Object.values(groups).sort((a, b) => b.total - a.total);
    },

    /** Total net worth from accounts. */
    accountNetWorth(): number {
      return this.accounts
        .filter((a) => !a.is_deleted && a.is_active)
        .reduce((sum, a) => {
          const balance = parseFloat(a.current_balance || "0");
          if (a.account_type === "LIABILITY") return sum + Math.abs(balance);
          return sum + balance;
        }, 0);
    },

    // ── 5. Cash Flow ──

    /** Cash flow per month with cumulative running total. */
    cashFlowByMonth(): CashFlowMonth[] {
      let cumulative = 0;
      return this.incomeExpenseByMonth.map((bucket) => {
        cumulative += bucket.net;
        return { ...bucket, cumulative };
      });
    },

    // ── 6. Tag Spending ──

    /** Expense spending grouped by tag. Uses batch-fetched transaction-tag
     *  associations from fetchTransactionTags() for accurate aggregation.
     *  Transactions without tag associations are excluded from tag totals. */
    tagSpending(): TagSpending[] {
      const tagMap = new Map<number, TagSpending>();
      const tagLookup = new Map(this.tags.map((t) => [t.id, t]));

      // Initialize entries for all active tags
      for (const tag of this.tags) {
        if (tag.is_deleted) continue;
        tagMap.set(tag.id, {
          tagId: tag.id,
          tagName: tag.name,
          tagColor: tag.color,
          amount: 0,
          transactionCount: 0,
        });
      }

      // Aggregate spending using real transaction-tag associations
      for (const txn of this.transactions) {
        if (txn.is_deleted || txn.transaction_type === "TRANSFER") continue;
        const tagIds = this.transactionTagMap[txn.id];
        if (!tagIds || tagIds.length === 0) continue;

        const amount = parseFloat(txn.amount_base || txn.amount_original || "0");
        for (const tagId of tagIds) {
          const entry = tagMap.get(tagId);
          if (entry) {
            entry.amount += amount;
            entry.transactionCount += 1;
          }
        }
      }

      return Array.from(tagMap.values())
        .filter((t) => t.amount > 0)
        .sort((a, b) => b.amount - a.amount);
    },

    // ── 7. Debt Payoff ──

    /** Debt entries with payoff progress. */
    debtPayoffEntries(): DebtPayoffEntry[] {
      return this.debts
        .filter((d) => !d.is_deleted && d.debt_nature === "MONEY_BORROWED" && d.is_active)
        .map((d) => ({
          id: d.id,
          name: d.name,
          debtType: d.debt_type,
          principalAmount: parseFloat(d.principal_amount || "0"),
          remainingBalance: parseFloat(d.remaining_balance || "0"),
          paidOff: parseFloat(d.principal_amount || "0") - parseFloat(d.remaining_balance || "0"),
          progressPercent: d.progress_percent || 0,
          monthlyPayment: parseFloat(d.monthly_payment || "0"),
          interestRate: parseFloat(d.interest_rate || "0"),
        }))
        .sort((a, b) => a.remainingBalance - b.remainingBalance);
    },

    // ── 8. Investment Performance ──

    /** Holdings with performance metrics. */
    holdingPerformance(): HoldingPerformance[] {
      return this.holdings
        .filter((h) => !h.is_deleted)
        .map((h) => {
          const costBasis = parseFloat(h.cost_basis || "0");
          const currentValue = parseFloat(h.current_value || "0");
          const gainLoss = parseFloat(h.unrealized_gain_loss || "0");
          const gainLossPercent = costBasis > 0 ? (gainLoss / costBasis) * 100 : 0;

          return {
            investmentId: h.investment_account_id,
            investmentAccountId: h.investment_account_id,
            symbol: h.symbol,
            assetName: h.asset_name,
            assetType: h.asset_type,
            quantity: parseFloat(h.quantity || "0"),
            costBasis,
            currentValue,
            unrealizedGainLoss: gainLoss,
            gainLossPercent,
          };
        })
        .sort((a, b) => b.unrealizedGainLoss - a.unrealizedGainLoss);
    },
  },

  actions: {
    /**
     * Fetch all data needed for reports.
     * Uses TransactionFilter with date_from/date_to for date range.
     * Fetches transactions in bulk (limit: 9999) for client-side aggregation.
     */
    async fetchReportData(forceRefresh = false): Promise<void> {
      this.loading = true;
      this.loadingAction = "fetchReportData";
      this.error = null;

      try {
        // Build transaction filter with date range
        const txnFilter: TransactionFilter = {
          limit: 9999,
          offset: 0,
        };
        if (this.dateFrom) txnFilter.date_from = this.dateFrom;
        if (this.dateTo) txnFilter.date_to = this.dateTo;

        const results = await Promise.allSettled([
          ledgerApi.transactions.list(txnFilter),
          ledgerApi.categories.list({ limit: 9999, offset: 0 }),
          ledgerApi.categories.dropdown(),
          ledgerApi.tags.list({ limit: 9999, offset: 0 }),
          ledgerApi.budgets.overview(),
          ledgerApi.debts.list({ limit: 9999, offset: 0 }),
          ledgerApi.debts.summary(),
          ledgerApi.investments.list(),
          ledgerApi.investments.summary(),
          ledgerApi.accounts.list({ limit: 9999, offset: 0 }),
        ]);

        const [
          txnRes,
          catRes,
          catDropRes,
          tagRes,
          budgetRes,
          debtRes,
          debtSumRes,
          investRes,
          investSumRes,
          accountRes,
        ] = results;

        // Unpack transactions (paginated response)
        this.transactions =
          txnRes.status === "fulfilled"
            ? (txnRes.value as { items: TransactionOut[] }).items || []
            : [];

        // Unpack categories
        this.categories =
          catRes.status === "fulfilled"
            ? (catRes.value as { items: CategoryOut[] }).items || []
            : [];

        this.categoryDropdown = catDropRes.status === "fulfilled" ? catDropRes.value : [];

        // Unpack tags
        this.tags =
          tagRes.status === "fulfilled" ? (tagRes.value as { items: TagOut[] }).items || [] : [];

        this.budgetOverview = budgetRes.status === "fulfilled" ? budgetRes.value : [];

        // Unpack debts
        this.debts =
          debtRes.status === "fulfilled"
            ? (debtRes.value as { items: DebtFacilityOut[] }).items || []
            : [];

        this.debtSummary = debtSumRes.status === "fulfilled" ? debtSumRes.value : null;

        // Unpack investments
        this.investments =
          investRes.status === "fulfilled"
            ? (investRes.value as { items: InvestmentAccountOut[] }).items || []
            : [];

        this.investmentSummary = investSumRes.status === "fulfilled" ? investSumRes.value : null;

        // Unpack accounts
        this.accounts =
          accountRes.status === "fulfilled"
            ? (accountRes.value as { items: AccountOut[] }).items || []
            : [];

        // Batch-fetch transaction-tag associations for expense/refund transactions
        // This enables accurate tag-based spending reports instead of placeholder data
        await this.fetchTransactionTags();

        // Fetch holdings for each investment account
        if (this.investments.length > 0) {
          const holdingsResults = await Promise.allSettled(
            this.investments
              .filter((inv) => !inv.is_deleted)
              .map((inv) => ledgerApi.holdings.list(inv.id)),
          );
          this.holdings = holdingsResults
            .filter((r): r is PromiseFulfilledResult<HoldingOut[]> => r.status === "fulfilled")
            .flatMap((r) => r.value);
        } else {
          this.holdings = [];
        }

        this.lastFetched = Date.now();
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
      } finally {
        this.loading = false;
        this.loadingAction = "";
      }
    },

    /**
     * Update the date range filter and refetch.
     */
    async setDateRange(from: string, to: string): Promise<void> {
      this.dateFrom = from;
      this.dateTo = to;
      await this.fetchReportData(true);
    },

    /**
     * Batch-fetch transaction-tag associations for expense transactions.
     *
     * Uses concurrent batching (10 at a time) to avoid overwhelming the API.
     * Caps at 500 expense transactions to keep response times reasonable;
     * for datasets larger than 500, a dedicated backend aggregation endpoint
     * would be the proper solution.
     */
    async fetchTransactionTags(): Promise<void> {
      this.transactionTagMap = {};
      this.tagFetchComplete = false;

      const expenseTxns = this.transactions.filter(
        (t) => !t.is_deleted && t.transaction_type !== "TRANSFER",
      );

      // Cap the number of transactions we fetch tags for to keep things performant
      const MAX_TAG_FETCH = 500;
      const txnsToFetch = expenseTxns.slice(0, MAX_TAG_FETCH);

      if (txnsToFetch.length === 0) {
        this.tagFetchComplete = true;
        return;
      }

      const BATCH_SIZE = 10;
      for (let i = 0; i < txnsToFetch.length; i += BATCH_SIZE) {
        const batch = txnsToFetch.slice(i, i + BATCH_SIZE);
        const results = await Promise.allSettled(
          batch.map(async (txn) => {
            try {
              const txTags = await ledgerApi.transactionTags.list(txn.id);
              return { txnId: txn.id, tagIds: txTags.map((t) => t.tag_id) };
            } catch {
              return { txnId: txn.id, tagIds: [] as number[] };
            }
          }),
        );

        for (const result of results) {
          if (result.status === "fulfilled") {
            const { txnId, tagIds } = result.value;
            if (tagIds.length > 0) {
              this.transactionTagMap[txnId] = tagIds;
            }
          }
        }
      }

      this.tagFetchComplete = true;
    },

    /**
     * Reset all report state.
     */
    $resetReports(): void {
      this.loading = false;
      this.loadingAction = "";
      this.error = null;
      this.transactions = [];
      this.categories = [];
      this.categoryDropdown = [];
      this.tags = [];
      this.budgetOverview = [];
      this.debts = [];
      this.debtSummary = null;
      this.investments = [];
      this.investmentSummary = null;
      this.holdings = [];
      this.accounts = [];
      this.transactionTagMap = {};
      this.tagFetchComplete = false;
      this.dateFrom = "";
      this.dateTo = "";
      this.lastFetched = null;
    },
  },
});
