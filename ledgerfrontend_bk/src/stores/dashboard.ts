/**
 * Dashboard Store — Aggregates data from multiple domain stores for the
 * main dashboard view.
 *
 * Unlike the domain CRUD stores, this store does NOT extend the base CRUD
 * pattern. Instead it composes data from account, transaction, bill, budget,
 * debt, investment, savingsGoal, insurance, invoice, and vault stores.
 *
 * Key features:
 *   - fetchAll() — parallel fetch of all widget data with 5-min staleness
 *   - refreshAll() — force-refresh all widget data
 *   - Computed getters for net worth, total assets/liabilities, alert counts
 *   - Staleness tracking via lastFetched timestamp
 */

import { defineStore } from "pinia";
import { ledgerApi } from "@/lib/ledgerApi";
import { extractErrorMessage } from "./base";
import type {
  AccountOut,
  TransactionListOut,
  BillListOut,
  BudgetListOut,
  CardListOut,
  DebtSummary,
  InvestmentSummary,
  SavingsGoalListOut,
  InsurancePolicyListOut,
  InvoiceListOut,
  DocumentVaultListOut,
} from "@/lib/ledgerTypes";

/** Staleness threshold in milliseconds — 5 minutes. */
const STALE_THRESHOLD = 5 * 60 * 1000;

export const useDashboardStore = defineStore("dashboard", {
  state: () => ({
    // ── Loading state ──
    loading: false,
    loadingAction: "",
    error: null as string | null,

    // ── Widget data ──
    accounts: [] as AccountOut[],
    recentTransactions: [] as TransactionListOut[],
    upcomingBills: [] as BillListOut[],
    budgetOverview: [] as BudgetListOut[],
    debtSummary: null as DebtSummary | null,
    investmentSummary: null as InvestmentSummary | null,
    savingsGoalDashboard: [] as SavingsGoalListOut[],
    insuranceRenewals: [] as InsurancePolicyListOut[],
    overdueInvoices: [] as InvoiceListOut[],
    expiringDocuments: [] as DocumentVaultListOut[],
    cards: [] as CardListOut[],

    // ── Cache tracking ──
    lastFetched: null as number | null,
  }),

  getters: {
    /** Whether the dashboard data is stale (older than 5 minutes). */
    isStale(): boolean {
      if (!this.lastFetched) return true;
      return Date.now() - this.lastFetched > STALE_THRESHOLD;
    },

    /** True if any data has been loaded. */
    hasData(): boolean {
      return (
        this.accounts.length > 0 ||
        this.recentTransactions.length > 0 ||
        this.upcomingBills.length > 0 ||
        this.budgetOverview.length > 0 ||
        this.savingsGoalDashboard.length > 0
      );
    },

    // ── Net Worth ──

    /** Sum of all active ASSET account balances. */
    totalAssets(): number {
      return this.accounts
        .filter((a) => a.is_active && a.account_type === "ASSET")
        .reduce((sum, a) => sum + parseFloat(a.current_balance || "0"), 0);
    },

    /** Sum of all active LIABILITY account balances (absolute value). */
    totalLiabilities(): number {
      return this.accounts
        .filter((a) => a.is_active && a.account_type === "LIABILITY")
        .reduce((sum, a) => sum + Math.abs(parseFloat(a.current_balance || "0")), 0);
    },

    /** Net worth = total assets - total liabilities. */
    netWorth(): number {
      return this.totalAssets - this.totalLiabilities;
    },

    /** Total investment portfolio value from summary. */
    investmentValue(): number {
      if (!this.investmentSummary) return 0;
      return parseFloat(this.investmentSummary.total_portfolio_value || "0");
    },

    /** Unrealized gain/loss from investments. */
    investmentGainLoss(): number {
      if (!this.investmentSummary) return 0;
      return parseFloat(this.investmentSummary.total_unrealized_gain_loss || "0");
    },

    /** Investment gain/loss as percentage. */
    investmentGainLossPercent(): number {
      if (!this.investmentSummary) return 0;
      return this.investmentSummary.total_gain_loss_percent || 0;
    },

    // ── Budget Summary ──

    /** Total budgeted amount across active budgets. */
    totalBudgeted(): number {
      return this.budgetOverview
        .filter((b) => b.is_active)
        .reduce((sum, b) => sum + parseFloat(b.amount || "0"), 0);
    },

    /** Total spent across active budgets. */
    totalSpent(): number {
      return this.budgetOverview
        .filter((b) => b.is_active)
        .reduce((sum, b) => sum + parseFloat(b.spent_amount || "0"), 0);
    },

    /** Budgets that are over 90% used. */
    overBudgetCount(): number {
      return this.budgetOverview.filter((b) => b.is_active && b.percent_used >= 90).length;
    },

    // ── Debt Summary ──

    /** Total remaining balance on borrowed debts. */
    totalDebtRemaining(): number {
      if (!this.debtSummary) return 0;
      return parseFloat(this.debtSummary.total_borrowed || "0");
    },

    /** Net debt position (borrowed - lent). */
    netDebtPosition(): number {
      if (!this.debtSummary) return 0;
      return parseFloat(this.debtSummary.net_position || "0");
    },

    // ── Savings Goals Summary ──

    /** Total saved across active goals. */
    totalGoalsSaved(): number {
      return this.savingsGoalDashboard
        .filter((g) => g.is_active)
        .reduce((sum, g) => sum + parseFloat(g.current_amount || "0"), 0);
    },

    /** Total target across active goals. */
    totalGoalsTarget(): number {
      return this.savingsGoalDashboard
        .filter((g) => g.is_active)
        .reduce((sum, g) => sum + parseFloat(g.target_amount || "0"), 0);
    },

    /** Overall savings goal progress percent. */
    goalsProgressPercent(): number {
      if (this.totalGoalsTarget === 0) return 0;
      return Math.min(Math.round((this.totalGoalsSaved / this.totalGoalsTarget) * 100), 100);
    },

    // ── Alerts ──

    /** Count of upcoming bills due within 7 days. */
    urgentBillsCount(): number {
      const now = new Date();
      const sevenDays = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      return this.upcomingBills.filter((b) => {
        const due = new Date(b.next_due_date);
        return due <= sevenDays;
      }).length;
    },

    /** Total count of alert items (renewals + overdue invoices + expiring docs + card alerts). */
    alertCount(): number {
      return (
        this.insuranceRenewals.length +
        this.overdueInvoices.length +
        this.expiringDocuments.length +
        this.upcomingAnnualFees.length +
        this.creditCardDueAlerts.length
      );
    },

    // ── Credit Card & Annual Fee Alerts ──

    /** Cards with annual_fee_date approaching within 30 days. */
    upcomingAnnualFees(): CardListOut[] {
      const now = new Date();
      const thirtyDays = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000);
      return this.cards.filter((c) => {
        if (!c.annual_fee_date || !c.is_active) return false;
        const feeDate = new Date(c.annual_fee_date);
        // Compare month/day in current year or next year
        const thisYear = new Date(now.getFullYear(), feeDate.getMonth(), feeDate.getDate());
        const nextYear = new Date(now.getFullYear() + 1, feeDate.getMonth(), feeDate.getDate());
        const upcoming = thisYear >= now ? thisYear : nextYear;
        return upcoming <= thirtyDays;
      });
    },

    /** Liability accounts with due_day approaching within 7 days. */
    creditCardDueAlerts(): AccountOut[] {
      const now = new Date();
      const currentDay = now.getDate();
      const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
      return this.accounts.filter((a) => {
        if (!a.is_active || a.account_type !== "LIABILITY") return false;
        // Check if the account has a due_day (credit card account)
        const dueDay = (a as AccountOut & { due_day?: number | null }).due_day;
        if (!dueDay || dueDay <= 0) return false;
        const effectiveDueDay = Math.min(dueDay, daysInMonth);
        const daysUntilDue = effectiveDueDay - currentDay;
        // Also check next month if due_day has passed
        return daysUntilDue >= 0 && daysUntilDue <= 7;
      });
    },
  },

  actions: {
    /**
     * Fetch all widget data in parallel.
     * Respects staleness — skips if data was fetched less than 5 minutes ago
     * unless forceRefresh is true.
     */
    async fetchAll(forceRefresh = false): Promise<void> {
      if (!forceRefresh && !this.isStale && this.hasData) {
        return;
      }

      this.loading = true;
      this.loadingAction = "fetchAll";
      this.error = null;

      try {
        const results = await Promise.allSettled([
          ledgerApi.accounts.list({ limit: 100, offset: 0 }),
          ledgerApi.transactions.recent(10),
          ledgerApi.bills.upcoming(30),
          ledgerApi.budgets.overview(),
          ledgerApi.debts.summary(),
          ledgerApi.investments.summary(),
          ledgerApi.savingsGoals.dashboard(),
          ledgerApi.insurance.renewals(60),
          ledgerApi.invoices.overdue(),
          ledgerApi.vault.expiring(30),
          ledgerApi.cards.list({ limit: 100, offset: 0 }),
        ]);

        // Unpack results — failed promises yield empty/default
        const [
          accountsRes,
          recentRes,
          upcomingRes,
          budgetRes,
          debtRes,
          investmentRes,
          goalsRes,
          renewalsRes,
          overdueRes,
          expiringRes,
          cardsRes,
        ] = results;

        this.accounts =
          accountsRes.status === "fulfilled"
            ? (accountsRes.value as { items: AccountOut[] }).items || []
            : [];
        this.recentTransactions = recentRes.status === "fulfilled" ? recentRes.value : [];
        this.upcomingBills = upcomingRes.status === "fulfilled" ? upcomingRes.value : [];
        this.budgetOverview = budgetRes.status === "fulfilled" ? budgetRes.value : [];
        this.debtSummary = debtRes.status === "fulfilled" ? debtRes.value : null;
        this.investmentSummary = investmentRes.status === "fulfilled" ? investmentRes.value : null;
        this.savingsGoalDashboard = goalsRes.status === "fulfilled" ? goalsRes.value : [];
        this.insuranceRenewals = renewalsRes.status === "fulfilled" ? renewalsRes.value : [];
        this.overdueInvoices = overdueRes.status === "fulfilled" ? overdueRes.value : [];
        this.expiringDocuments = expiringRes.status === "fulfilled" ? expiringRes.value : [];
        this.cards =
          cardsRes.status === "fulfilled"
            ? (cardsRes.value as { items: CardListOut[] }).items || []
            : [];

        this.lastFetched = Date.now();
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
      } finally {
        this.loading = false;
        this.loadingAction = "";
      }
    },

    /**
     * Force-refresh all widget data.
     */
    async refreshAll(): Promise<void> {
      await this.fetchAll(true);
    },

    /**
     * Reset all dashboard state.
     */
    $resetDashboard(): void {
      this.loading = false;
      this.loadingAction = "";
      this.error = null;
      this.accounts = [];
      this.recentTransactions = [];
      this.upcomingBills = [];
      this.budgetOverview = [];
      this.debtSummary = null;
      this.investmentSummary = null;
      this.savingsGoalDashboard = [];
      this.insuranceRenewals = [];
      this.overdueInvoices = [];
      this.expiringDocuments = [];
      this.cards = [];
      this.lastFetched = null;
    },
  },
});
