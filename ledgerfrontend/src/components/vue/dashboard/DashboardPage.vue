<script setup lang="ts">
/**
 * DashboardPage — Financial overview dashboard with 12 widget cards.
 *
 * Features:
 *   - Net Worth hero card (assets - liabilities) with investment breakdown
 *   - Account Balances — small cards grouped by type (Asset, Liability, Investment)
 *   - Monthly Spending — spending breakdown across active budgets
 *   - Budget Status — progress bars (green/amber/red) for each active budget
 *   - Upcoming Bills — list of bills due within 30 days
 *   - Recent Transactions — compact list of latest 10 transactions
 *   - Savings Goals — progress bars for active goals
 *   - Debt Progress — remaining balance vs principal for top debts
 *   - Investment Snapshot — total portfolio value + gain/loss
 *   - Insurance Renewals — alert list of policies due for renewal
 *   - Overdue Invoices — alert list of unpaid past-due invoices
 *   - Expiring Documents — alert list of documents expiring within 30 days
 *   - Pull-to-refresh / manual refresh button
 *   - Stale-while-revalidate caching (5-min threshold)
 *   - Loading skeleton while fetching
 *   - Responsive grid: 2-3 cols desktop, 1 col mobile
 *
 * Registers as `ldgr-dashboard-page` custom element.
 */

import { ProgressBar, LoadingSkeleton, StatusBadge } from "@/components/vue";
import { formatCurrency, getBaseCurrency } from "@/lib/currency";
import { formatDateShort, formatRelativeTime } from "@/lib/timezone";
import { useDashboardStore } from "@/stores/dashboard";
import type {
  AccountOut,
  TransactionListOut,
  BillListOut,
  BudgetListOut,
  CardListOut,
  SavingsGoalListOut,
  InsurancePolicyListOut,
  InvoiceListOut,
  DocumentVaultListOut,
} from "@/lib/ledgerTypes";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrDashboardPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useDashboardStore();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getBudgetColor(percent: number): "green" | "amber" | "red" {
  if (percent >= 90) return "red";
  if (percent >= 70) return "amber";
  return "green";
}

function getDaysUntilDue(dateStr: string): number {
  const date = new Date(dateStr);
  const now = new Date();
  return Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function getDueDateBadgeClass(dateStr: string): string {
  const days = getDaysUntilDue(dateStr);
  if (days < 0) return "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300";
  if (days <= 3) return "bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300";
  if (days <= 7) return "bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300";
  return "bg-green-100 dark:bg-green-950/50 text-green-700 dark:text-green-300";
}

function getTransactionTypeColor(type: string): string {
  switch (type) {
    case "INCOME":
      return "text-credit";
    case "EXPENSE":
      return "text-debit";
    case "TRANSFER":
      return "text-cyan-600 dark:text-cyan-400";
    default:
      return "text-navy-900 dark:text-navy-100";
  }
}

function getTransactionTypePrefix(type: string): string {
  switch (type) {
    case "INCOME":
      return "+";
    case "EXPENSE":
      return "-";
    default:
      return "";
  }
}

// ─── Data Loading ────────────────────────────────────────────────────────────

onMounted(() => {
  store.fetchAll();
});

// ─── Refresh ─────────────────────────────────────────────────────────────────

function handleRefresh() {
  store.refreshAll();
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading);
const hasData = computed(() => store.hasData);

// Grouped accounts
const assetAccounts = computed(() =>
  store.accounts.filter((a) => a.is_active && a.account_type === "ASSET"),
);
const liabilityAccounts = computed(() =>
  store.accounts.filter((a) => a.is_active && a.account_type === "LIABILITY"),
);
const investmentAccounts = computed(() =>
  store.accounts.filter((a) => a.is_active && a.account_type === "INVESTMENT"),
);

// Top 5 budgets by percent_used (most urgent)
const topBudgets = computed(() =>
  [...store.budgetOverview]
    .filter((b) => b.is_active)
    .sort((a, b) => b.percent_used - a.percent_used)
    .slice(0, 5),
);

// Top 5 goals by progress (least complete first)
const topGoals = computed(() =>
  [...store.savingsGoalDashboard]
    .filter((g) => g.is_active && !g.is_completed)
    .sort((a, b) => a.progress_percent - b.progress_percent)
    .slice(0, 5),
);

// Alert items combined for notification summary
const alertItems = computed(() => {
  const items: Array<{ type: string; label: string; date: string; route: string; urgent?: boolean }> = [];
  for (const inv of store.overdueInvoices.slice(0, 3)) {
    items.push({
      type: "invoice",
      label: (inv as InvoiceListOut).invoice_number || `Invoice #${(inv as InvoiceListOut).id}`,
      date: (inv as InvoiceListOut).due_date || "",
      route: "/dashboard/invoices",
      urgent: true,
    });
  }
  for (const r of store.insuranceRenewals.slice(0, 3)) {
    items.push({
      type: "insurance",
      label: (r as InsurancePolicyListOut).policy_name,
      date: (r as InsurancePolicyListOut).renewal_date || "",
      route: "/dashboard/insurance",
    });
  }
  for (const d of store.expiringDocuments.slice(0, 3)) {
    items.push({
      type: "vault",
      label: (d as DocumentVaultListOut).title,
      date: (d as DocumentVaultListOut).expiry_date || "",
      route: "/dashboard/vault",
    });
  }
  for (const c of store.upcomingAnnualFees.slice(0, 3)) {
    items.push({
      type: "card-fee",
      label: (c as CardListOut).name || `Card #${(c as CardListOut).id}`,
      date: (c as CardListOut).annual_fee_date || "",
      route: "/dashboard/cards",
    });
  }
  for (const a of store.creditCardDueAlerts.slice(0, 3)) {
    items.push({
      type: "card-due",
      label: a.name,
      date: "",
      route: "/dashboard/cards",
    });
  }
  return items;
});

// ── Goal deadline helpers ──

function getDaysUntilDeadline(deadline: string | null): number | null {
  if (!deadline) return null;
  const date = new Date(deadline);
  const now = new Date();
  return Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function getGoalDeadlineClass(goal: SavingsGoalListOut): string {
  const days = getDaysUntilDeadline((goal as SavingsGoalListOut).deadline);
  if (days === null) return "";
  if (days < 0) return "border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-950/20";
  if (days <= 7) return "border-l-4 border-l-red-500 bg-red-50/50 dark:bg-red-950/20";
  if (days <= 30) return "border-l-4 border-l-amber-500 bg-amber-50/50 dark:bg-amber-950/20";
  return "";
}
</script>

<template>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Dashboard</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Your financial overview at a glance
        </p>
      </div>
      <button
        class="btn-secondary flex items-center gap-2"
        :disabled="isLoading"
        @click="handleRefresh"
      >
        <svg
          :class="['h-4 w-4 transition-transform', isLoading ? 'animate-spin' : '']"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        {{ isLoading ? "Refreshing..." : "Refresh" }}
      </button>
    </div>

    <!-- ── Loading Skeleton ───────────────────────────────────────────────── -->
    <div v-if="isLoading && !hasData">
      <LoadingSkeleton type="detail" />
    </div>

    <!-- ── Dashboard Content ──────────────────────────────────────────────── -->
    <div v-else class="space-y-6">

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- ROW 1: Net Worth + Account Balances                                -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- ── Net Worth Hero Card ─────────────────────────────────────────── -->
        <div class="card p-6 lg:col-span-1 bg-gradient-to-br from-navy-900 to-navy-800 dark:from-navy-950 dark:to-navy-900 border-navy-800 dark:border-navy-700">
          <div class="flex items-center gap-2 mb-4">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/20">
              <svg class="h-5 w-5 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p class="text-xs text-cyan-300 uppercase tracking-wider font-medium">Net Worth</p>
          </div>
          <p class="text-3xl font-bold text-white mb-4">
            {{ formatCurrency(store.netWorth, getBaseCurrency()) }}
          </p>
          <div class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span class="text-navy-300">Assets</span>
              <span class="text-credit font-medium">{{ formatCurrency(store.totalAssets, getBaseCurrency()) }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-navy-300">Liabilities</span>
              <span class="text-debit font-medium">{{ formatCurrency(store.totalLiabilities, getBaseCurrency()) }}</span>
            </div>
            <div class="h-px bg-navy-700 my-1" />
            <div class="flex items-center justify-between text-sm">
              <span class="text-navy-300">Investments</span>
              <span class="text-cyan-300 font-medium">{{ formatCurrency(store.investmentValue, getBaseCurrency()) }}</span>
            </div>
          </div>
        </div>

        <!-- ── Account Balances ────────────────────────────────────────────── -->
        <div class="card p-6 lg:col-span-2">
          <div class="flex items-center gap-2 mb-4">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
              <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
              </svg>
            </div>
            <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Account Balances</h2>
          </div>

          <!-- No accounts -->
          <div v-if="store.accounts.length === 0" class="text-center py-6">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No accounts yet</p>
            <a href="/dashboard/accounts" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Add your first account</a>
          </div>

          <!-- Account groups -->
          <div v-else class="space-y-4">
            <!-- Assets -->
            <div v-if="assetAccounts.length > 0">
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2 font-medium">
                Assets ({{ assetAccounts.length }})
              </p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div
                  v-for="acct in assetAccounts.slice(0, 4)"
                  :key="acct.id"
                  class="flex items-center justify-between p-2.5 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-900/50"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <div class="h-2 w-2 rounded-full bg-credit flex-shrink-0" />
                    <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ acct.name }}</span>
                  </div>
                  <span class="text-sm font-medium text-credit flex-shrink-0 ml-2">
                    {{ formatCurrency(acct.current_balance, acct.currency || "USD") }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Liabilities -->
            <div v-if="liabilityAccounts.length > 0">
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2 font-medium">
                Liabilities ({{ liabilityAccounts.length }})
              </p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div
                  v-for="acct in liabilityAccounts.slice(0, 4)"
                  :key="acct.id"
                  class="flex items-center justify-between p-2.5 rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <div class="h-2 w-2 rounded-full bg-debit flex-shrink-0" />
                    <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ acct.name }}</span>
                  </div>
                  <span class="text-sm font-medium text-debit flex-shrink-0 ml-2">
                    {{ formatCurrency(Math.abs(parseFloat(acct.current_balance || "0")), acct.currency || "USD") }}
                  </span>
                </div>
              </div>
            </div>

            <!-- Investments -->
            <div v-if="investmentAccounts.length > 0">
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2 font-medium">
                Investments ({{ investmentAccounts.length }})
              </p>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <div
                  v-for="acct in investmentAccounts.slice(0, 4)"
                  :key="acct.id"
                  class="flex items-center justify-between p-2.5 rounded-lg bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-900/50"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <div class="h-2 w-2 rounded-full bg-cyan-500 flex-shrink-0" />
                    <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ acct.name }}</span>
                  </div>
                  <span class="text-sm font-medium text-cyan-600 dark:text-cyan-400 flex-shrink-0 ml-2">
                    {{ formatCurrency(acct.current_balance, acct.currency || "USD") }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- ROW 2: Budget Status + Spending + Investment Snapshot               -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- ── Budget Status ───────────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Budget Status</h2>
            </div>
            <a v-if="store.budgetOverview.length > 0" href="/dashboard/budgets" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline">View all</a>
          </div>

          <div v-if="store.budgetOverview.length === 0" class="text-center py-6">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No budgets yet</p>
            <a href="/dashboard/budgets" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Create a budget</a>
          </div>

          <div v-else class="space-y-3">
            <!-- Summary bar -->
            <div class="flex items-center justify-between text-xs mb-2">
              <span class="text-slate-custom-500 dark:text-slate-custom-400">
                {{ formatCurrency(store.totalSpent, getBaseCurrency()) }} of {{ formatCurrency(store.totalBudgeted, getBaseCurrency()) }} spent
              </span>
              <span
                v-if="store.overBudgetCount > 0"
                class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300"
              >
                {{ store.overBudgetCount }} over budget
              </span>
            </div>

            <!-- Budget progress bars -->
            <div
              v-for="budget in topBudgets"
              :key="budget.id"
              class="space-y-1"
            >
              <div class="flex items-center justify-between">
                <span class="text-xs text-navy-900 dark:text-navy-100 truncate font-medium">{{ budget.name }}</span>
                <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0 ml-2">{{ budget.percent_used }}%</span>
              </div>
              <ProgressBar
                :value="parseFloat(budget.spent_amount || '0')"
                :max="parseFloat(budget.amount || '1')"
                :color="getBudgetColor(budget.percent_used)"
                size="sm"
              />
            </div>
          </div>
        </div>

        <!-- ── Monthly Spending ────────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center gap-2 mb-4">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
              <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Spending Overview</h2>
          </div>

          <div v-if="store.budgetOverview.length === 0" class="text-center py-6">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No spending data</p>
          </div>

          <div v-else class="space-y-2">
            <!-- Spending by category (from budget overview) -->
            <div
              v-for="budget in [...store.budgetOverview].filter((b) => b.is_active).sort((a, b) => parseFloat(b.spent_amount || '0') - parseFloat(a.spent_amount || '0')).slice(0, 6)"
              :key="budget.id"
              class="flex items-center gap-3"
            >
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between mb-0.5">
                  <span class="text-xs text-navy-900 dark:text-navy-100 truncate">{{ budget.name }}</span>
                  <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0 ml-2">
                    {{ formatCurrency(budget.spent_amount, getBaseCurrency()) }}
                  </span>
                </div>
                <div class="h-1.5 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
                  <div
                    class="h-full rounded-full bg-cyan-500 dark:bg-cyan-400 transition-all duration-500"
                    :style="{
                      width: `${store.totalBudgeted > 0 ? Math.min((parseFloat(budget.spent_amount || '0') / store.totalBudgeted) * 100, 100) : 0}%`,
                    }"
                  />
                </div>
              </div>
            </div>

            <!-- Total -->
            <div class="h-px bg-navy-200 dark:bg-navy-700 my-2" />
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-navy-900 dark:text-navy-100">Total Spent</span>
              <span class="text-sm font-bold text-debit">{{ formatCurrency(store.totalSpent, getBaseCurrency()) }}</span>
            </div>
          </div>
        </div>

        <!-- ── Investment Snapshot ─────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Investments</h2>
            </div>
            <a v-if="store.investmentSummary" href="/dashboard/investments" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline">View all</a>
          </div>

          <div v-if="!store.investmentSummary" class="text-center py-6">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No investments yet</p>
            <a href="/dashboard/investments" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Add an investment</a>
          </div>

          <div v-else class="space-y-3">
            <!-- Portfolio value -->
            <div>
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Portfolio Value</p>
              <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
                {{ formatCurrency(store.investmentValue, getBaseCurrency()) }}
              </p>
            </div>

            <!-- Gain/Loss -->
            <div class="flex items-center gap-2">
              <svg
                :class="['h-5 w-5', store.investmentGainLoss >= 0 ? 'text-credit' : 'text-debit']"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  v-if="store.investmentGainLoss >= 0"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                />
                <path
                  v-else
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width="2"
                  d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
                />
              </svg>
              <div>
                <p :class="['text-sm font-semibold', store.investmentGainLoss >= 0 ? 'text-credit' : 'text-debit']">
                  {{ store.investmentGainLoss >= 0 ? "+" : "" }}{{ formatCurrency(store.investmentGainLoss, getBaseCurrency()) }}
                </p>
                <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
                  {{ store.investmentGainLossPercent >= 0 ? "+" : "" }}{{ store.investmentGainLossPercent.toFixed(2) }}%
                </p>
              </div>
            </div>

            <!-- Cost basis -->
            <div class="h-px bg-navy-200 dark:bg-navy-700" />
            <div class="flex items-center justify-between text-xs">
              <span class="text-slate-custom-500 dark:text-slate-custom-400">Cost Basis</span>
              <span class="text-navy-900 dark:text-navy-100 font-medium">
                {{ formatCurrency(store.investmentSummary.total_cost_basis, getBaseCurrency()) }}
              </span>
            </div>
            <div class="flex items-center justify-between text-xs">
              <span class="text-slate-custom-500 dark:text-slate-custom-400">Accounts</span>
              <span class="text-navy-900 dark:text-navy-100 font-medium">
                {{ store.investmentSummary.account_count }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- ROW 3: Upcoming Bills + Recent Transactions                        -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- ── Upcoming Bills ──────────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Upcoming Bills</h2>
              <span
                v-if="store.upcomingBills.length > 0"
                class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300"
              >
                {{ store.upcomingBills.length }}
              </span>
            </div>
            <a v-if="store.upcomingBills.length > 0" href="/dashboard/bills" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline">View all</a>
          </div>

          <div v-if="store.upcomingBills.length === 0" class="text-center py-6">
            <svg class="h-10 w-10 text-slate-custom-300 dark:text-slate-custom-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No upcoming bills</p>
          </div>

          <div v-else class="space-y-2">
            <div
              v-for="bill in store.upcomingBills.slice(0, 5)"
              :key="bill.id"
              class="flex items-center justify-between p-2.5 rounded-lg hover:bg-navy-50 dark:hover:bg-navy-800/50 transition-colors"
            >
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-navy-900 dark:text-navy-100 truncate">
                    {{ (bill as BillListOut).payee_name || "Bill" }}
                  </p>
                  <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
                    {{ formatDateShort((bill as BillListOut).next_due_date) }}
                  </p>
                </div>
              </div>
              <div class="flex items-center gap-2 flex-shrink-0 ml-3">
                <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
                  {{ formatCurrency((bill as BillListOut).amount, (bill as BillListOut).currency || "USD") }}
                </span>
                <span
                  :class="['inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium', getDueDateBadgeClass((bill as BillListOut).next_due_date)]"
                >
                  {{ formatRelativeTime((bill as BillListOut).next_due_date) }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Recent Transactions ─────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Recent Transactions</h2>
            </div>
            <a v-if="store.recentTransactions.length > 0" href="/dashboard/transactions" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline">View all</a>
          </div>

          <div v-if="store.recentTransactions.length === 0" class="text-center py-6">
            <svg class="h-10 w-10 text-slate-custom-300 dark:text-slate-custom-600 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
            </svg>
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No transactions yet</p>
          </div>

          <div v-else class="space-y-1">
            <div
              v-for="txn in store.recentTransactions.slice(0, 8)"
              :key="txn.id"
              class="flex items-center justify-between p-2 rounded-lg hover:bg-navy-50 dark:hover:bg-navy-800/50 transition-colors"
            >
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <div
                  :class="[
                    'flex h-7 w-7 items-center justify-center rounded-full flex-shrink-0',
                    (txn as TransactionListOut).transaction_type === 'INCOME'
                      ? 'bg-green-100 dark:bg-green-950/50'
                      : (txn as TransactionListOut).transaction_type === 'EXPENSE'
                        ? 'bg-red-100 dark:bg-red-950/50'
                        : 'bg-cyan-100 dark:bg-cyan-950/50',
                  ]"
                >
                  <svg
                    v-if="(txn as TransactionListOut).transaction_type === 'INCOME'"
                    class="h-3.5 w-3.5 text-credit"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                  </svg>
                  <svg
                    v-else-if="(txn as TransactionListOut).transaction_type === 'EXPENSE'"
                    class="h-3.5 w-3.5 text-debit"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                  </svg>
                  <svg
                    v-else
                    class="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                  </svg>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm text-navy-900 dark:text-navy-100 truncate">
                    {{ (txn as TransactionListOut).payee_name || (txn as TransactionListOut).description || "Transaction" }}
                  </p>
                  <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
                    {{ formatDateShort((txn as TransactionListOut).date) }}
                  </p>
                </div>
              </div>
              <span
                :class="['text-sm font-medium flex-shrink-0 ml-3', getTransactionTypeColor((txn as TransactionListOut).transaction_type)]"
              >
                {{ getTransactionTypePrefix((txn as TransactionListOut).transaction_type) }}{{ formatCurrency((txn as TransactionListOut).amount_original, (txn as TransactionListOut).currency || "USD") }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- ROW 4: Savings Goals + Debt Progress                               -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- ── Savings Goals ───────────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Savings Goals</h2>
            </div>
            <a v-if="store.savingsGoalDashboard.length > 0" href="/dashboard/goals" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline">View all</a>
          </div>

          <div v-if="store.savingsGoalDashboard.length === 0" class="text-center py-6">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No savings goals yet</p>
            <a href="/dashboard/goals" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Create a goal</a>
          </div>

          <div v-else class="space-y-3">
            <!-- Summary -->
            <div class="flex items-center justify-between text-xs mb-2">
              <span class="text-slate-custom-500 dark:text-slate-custom-400">
                {{ formatCurrency(store.totalGoalsSaved, getBaseCurrency()) }} of {{ formatCurrency(store.totalGoalsTarget, getBaseCurrency()) }}
              </span>
              <span class="text-cyan-600 dark:text-cyan-400 font-medium">{{ store.goalsProgressPercent }}%</span>
            </div>

            <!-- Goal progress bars -->
            <div
              v-for="goal in topGoals"
              :key="goal.id"
              :class="['space-y-1 rounded-lg p-2 -mx-2 transition-colors', getGoalDeadlineClass(goal as SavingsGoalListOut)]"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2 min-w-0 flex-1">
                  <span v-if="(goal as SavingsGoalListOut).icon" class="text-sm flex-shrink-0">{{ (goal as SavingsGoalListOut).icon }}</span>
                  <span class="text-xs text-navy-900 dark:text-navy-100 truncate font-medium">{{ (goal as SavingsGoalListOut).name }}</span>
                  <span
                    v-if="getDaysUntilDeadline((goal as SavingsGoalListOut).deadline) !== null && (getDaysUntilDeadline((goal as SavingsGoalListOut).deadline) ?? 0) <= 30"
                    :class="[
                      'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                      (getDaysUntilDeadline((goal as SavingsGoalListOut).deadline) ?? 0) <= 7
                        ? 'bg-red-100 dark:bg-red-950/50 text-red-700 dark:text-red-300'
                        : 'bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300'
                    ]"
                  >
                    {{ (getDaysUntilDeadline((goal as SavingsGoalListOut).deadline) ?? 0) <= 0 ? 'Overdue' : `${getDaysUntilDeadline((goal as SavingsGoalListOut).deadline)}d left` }}
                  </span>
                </div>
                <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0 ml-2">
                  {{ (goal as SavingsGoalListOut).progress_percent }}%
                </span>
              </div>
              <ProgressBar
                :value="parseFloat((goal as SavingsGoalListOut).current_amount || '0')"
                :max="parseFloat((goal as SavingsGoalListOut).target_amount || '1')"
                :color="(goal as SavingsGoalListOut).progress_percent >= 100 ? 'cyan' : (goal as SavingsGoalListOut).progress_percent >= 50 ? 'green' : 'amber'"
                size="sm"
              />
            </div>
          </div>
        </div>

        <!-- ── Debt Progress ───────────────────────────────────────────────── -->
        <div class="card p-6">
          <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
              <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 dark:bg-cyan-950">
                <svg class="h-4 w-4 text-cyan-600 dark:text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Debt Overview</h2>
            </div>
            <a v-if="store.debtSummary" href="/dashboard/debts" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline">View all</a>
          </div>

          <div v-if="!store.debtSummary" class="text-center py-6">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No debt data</p>
            <a href="/dashboard/debts" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Track a debt</a>
          </div>

          <div v-else class="space-y-3">
            <!-- Borrowed vs Lent -->
            <div class="grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Total Borrowed</p>
                <p class="text-lg font-bold text-debit">
                  {{ formatCurrency(store.debtSummary.total_borrowed, getBaseCurrency()) }}
                </p>
              </div>
              <div>
                <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Total Lent</p>
                <p class="text-lg font-bold text-credit">
                  {{ formatCurrency(store.debtSummary.total_lent, getBaseCurrency()) }}
                </p>
              </div>
            </div>

            <!-- Net Position -->
            <div class="h-px bg-navy-200 dark:bg-navy-700" />
            <div class="flex items-center justify-between">
              <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">Net Position</span>
              <span
                :class="[
                  'text-sm font-bold',
                  parseFloat(store.debtSummary.net_position) >= 0 ? 'text-credit' : 'text-debit',
                ]"
              >
                {{ parseFloat(store.debtSummary.net_position) >= 0 ? "+" : "" }}{{ formatCurrency(store.debtSummary.net_position, getBaseCurrency()) }}
              </span>
            </div>

            <!-- Visual bar showing borrowed vs lent -->
            <div class="mt-2">
              <div class="h-3 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden flex">
                <div
                  v-if="parseFloat(store.debtSummary.total_borrowed) > 0"
                  class="h-full bg-debit transition-all duration-500"
                  :style="{
                    width: `${
                      (parseFloat(store.debtSummary.total_borrowed) /
                        (parseFloat(store.debtSummary.total_borrowed) + parseFloat(store.debtSummary.total_lent) || 1)) *
                      100
                    }%`,
                  }"
                />
                <div
                  v-if="parseFloat(store.debtSummary.total_lent) > 0"
                  class="h-full bg-credit transition-all duration-500"
                  :style="{
                    width: `${
                      (parseFloat(store.debtSummary.total_lent) /
                        (parseFloat(store.debtSummary.total_borrowed) + parseFloat(store.debtSummary.total_lent) || 1)) *
                      100
                    }%`,
                  }"
                />
              </div>
              <div class="flex items-center justify-between mt-1">
                <span class="text-[10px] text-debit">Borrowed</span>
                <span class="text-[10px] text-credit">Lent</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- ROW 5: Alerts — Insurance Renewals + Overdue Invoices + Expiring   -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->

      <div v-if="alertItems.length > 0" class="space-y-4">
        <!-- Alert header -->
        <div class="flex items-center gap-2">
          <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-950">
            <svg class="h-4 w-4 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100">Attention Needed</h2>
          <span
            class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-amber-100 dark:bg-amber-950 text-amber-700 dark:text-amber-300"
          >
            {{ alertItems.length }} item{{ alertItems.length !== 1 ? "s" : "" }}
          </span>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <!-- ── Insurance Renewals ─────────────────────────────────────────── -->
          <div v-if="store.insuranceRenewals.length > 0" class="card p-5 border-amber-200 dark:border-amber-800/50">
            <div class="flex items-center gap-2 mb-3">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-950">
                <svg class="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 class="text-xs font-semibold text-navy-900 dark:text-navy-100 uppercase tracking-wider">Insurance Renewals</h3>
            </div>
            <div class="space-y-2">
              <div
                v-for="policy in store.insuranceRenewals.slice(0, 3)"
                :key="policy.id"
                class="flex items-center justify-between"
              >
                <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ (policy as InsurancePolicyListOut).policy_name }}</span>
                <span class="text-xs text-amber-600 dark:text-amber-400 flex-shrink-0 ml-2">
                  {{ formatRelativeTime((policy as InsurancePolicyListOut).renewal_date || "") }}
                </span>
              </div>
            </div>
            <a href="/dashboard/insurance" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline mt-2 inline-block">View policies</a>
          </div>

          <!-- ── Overdue Invoices ───────────────────────────────────────────── -->
          <div v-if="store.overdueInvoices.length > 0" class="card p-5 border-red-300 dark:border-red-700 bg-red-50/30 dark:bg-red-950/10">
            <div class="flex items-center gap-2 mb-3">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-red-100 dark:bg-red-950">
                <svg class="h-3.5 w-3.5 text-debit" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 class="text-xs font-semibold text-red-700 dark:text-red-400 uppercase tracking-wider">Overdue Invoices</h3>
              <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold bg-red-600 text-white animate-pulse">
                {{ store.overdueInvoices.length }} URGENT
              </span>
            </div>
            <div class="space-y-2">
              <div
                v-for="invoice in store.overdueInvoices.slice(0, 3)"
                :key="invoice.id"
                class="flex items-center justify-between"
              >
                <span class="text-sm text-navy-900 dark:text-navy-100 truncate">
                  {{ (invoice as InvoiceListOut).invoice_number || `#${(invoice as InvoiceListOut).id}` }}
                </span>
                <span class="text-xs text-debit font-medium flex-shrink-0 ml-2">
                  {{ formatCurrency((invoice as InvoiceListOut).amount_due, getBaseCurrency()) }}
                </span>
              </div>
            </div>
            <a href="/dashboard/invoices" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline mt-2 inline-block">View invoices</a>
          </div>

          <!-- ── Expiring Documents ─────────────────────────────────────────── -->
          <div v-if="store.expiringDocuments.length > 0" class="card p-5 border-amber-200 dark:border-amber-800/50">
            <div class="flex items-center gap-2 mb-3">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-100 dark:bg-amber-950">
                <svg class="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 class="text-xs font-semibold text-navy-900 dark:text-navy-100 uppercase tracking-wider">Expiring Documents</h3>
            </div>
            <div class="space-y-2">
              <div
                v-for="doc in store.expiringDocuments.slice(0, 3)"
                :key="doc.id"
                class="flex items-center justify-between"
              >
                <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ (doc as DocumentVaultListOut).title }}</span>
                <span class="text-xs text-amber-600 dark:text-amber-400 flex-shrink-0 ml-2">
                  {{ formatRelativeTime((doc as DocumentVaultListOut).expiry_date || "") }}
                </span>
              </div>
            </div>
            <a href="/dashboard/vault" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline mt-2 inline-block">View documents</a>
          </div>

          <!-- ── Annual Fee & Card Due Alerts ─────────────────────────────── -->
          <div v-if="store.upcomingAnnualFees.length > 0 || store.creditCardDueAlerts.length > 0" class="card p-5 border-warm-200 dark:border-warm-800/50">
            <div class="flex items-center gap-2 mb-3">
              <div class="flex h-7 w-7 items-center justify-center rounded-lg bg-warm-100 dark:bg-warm-950">
                <svg class="h-3.5 w-3.5 text-warm-600 dark:text-warm-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <h3 class="text-xs font-semibold text-navy-900 dark:text-navy-100 uppercase tracking-wider">Card Alerts</h3>
            </div>
            <div class="space-y-2">
              <!-- Annual fee alerts -->
              <div
                v-for="card in store.upcomingAnnualFees.slice(0, 2)"
                :key="`fee-${card.id}`"
                class="flex items-center justify-between"
              >
                <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ (card as CardListOut).name || `Card #${(card as CardListOut).id}` }}</span>
                <div class="flex items-center gap-2 flex-shrink-0 ml-2">
                  <span class="text-xs text-warm-600 dark:text-warm-400 font-medium">Fee: {{ formatCurrency((card as CardListOut).annual_fee || '0', getBaseCurrency()) }}</span>
                  <span class="text-xs text-amber-600 dark:text-amber-400">{{ formatRelativeTime((card as CardListOut).annual_fee_date || '') }}</span>
                </div>
              </div>
              <!-- Credit card due alerts -->
              <div
                v-for="acct in store.creditCardDueAlerts.slice(0, 2)"
                :key="`due-${acct.id}`"
                class="flex items-center justify-between"
              >
                <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ acct.name }}</span>
                <span class="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium bg-amber-100 dark:bg-amber-950/50 text-amber-700 dark:text-amber-300">
                  Payment due soon
                </span>
              </div>
            </div>
            <a href="/dashboard/cards" class="text-xs text-cyan-600 dark:text-cyan-400 hover:underline mt-2 inline-block">View cards</a>
          </div>
        </div>
      </div>

      <!-- ── No alerts message ────────────────────────────────────────────── -->
      <div v-else-if="hasData" class="card p-5">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-950/50">
            <svg class="h-5 w-5 text-credit" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">All clear!</p>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">No upcoming alerts, overdue invoices, or expiring documents.</p>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Error State ────────────────────────────────────────────────────── -->
    <div v-if="store.error && !isLoading" class="card p-5 border-red-200 dark:border-red-800/50">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-950/50">
          <svg class="h-5 w-5 text-debit" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div>
          <p class="text-sm font-medium text-debit">Failed to load dashboard data</p>
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">{{ store.error }}</p>
        </div>
        <button class="btn-ghost text-xs ml-auto" @click="handleRefresh">Try again</button>
      </div>
    </div>
  </div>
</template>
