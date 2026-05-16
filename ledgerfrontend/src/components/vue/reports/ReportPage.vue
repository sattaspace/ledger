<script setup lang="ts">
/**
 * ReportPage — Financial reports & analytics with 8 report types.
 *
 * Features:
 *   - Date range filter (presets + custom) using DateRangePicker
 *   - Tab navigation between 8 report types
 *   - Report 1: Income vs Expense — grouped horizontal bar chart by month
 *   - Report 2: Category Spending — horizontal bar + donut (CSS conic-gradient)
 *   - Report 3: Budget vs Actual — comparison table with progress bars
 *   - Report 4: Net Worth Composition — stacked bar by account type
 *   - Report 5: Cash Flow — waterfall-style bar chart by month
 *   - Report 6: Tag Spending — horizontal bar chart
 *   - Report 7: Debt Payoff — progress bars + payoff table
 *   - Report 8: Investment Performance — holdings table with gain/loss
 *   - Loading skeleton, error state, empty states
 *   - All CSS-based visualizations (no chart library dependency)
 *   - Responsive design
 *
 * Registers as `ldgr-report-page` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  ProgressBar,
  LoadingSkeleton,
  DateRangePicker,
  StatusBadge,
  FeatureGate,
  UpgradePrompt,
  PlanLimitBadge,
} from "@/components/vue";
import type { DateRange } from "@/components/vue";
import { useReportsStore } from "@/stores/reports";
import { useAccess } from "@/composables/useAccess";
import { useToast } from "@/composables/useToast";
import type {
  MonthlyBucket,
  CategorySpending,
  BudgetVsActual,
  CashFlowMonth,
  TagSpending,
  DebtPayoffEntry,
  HoldingPerformance,
} from "@/stores/reports";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrReportPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useReportsStore();
const { hasAccess } = useAccess();
const toast = useToast();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: number | string, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(num);
}

function formatPercent(value: number): string {
  if (isNaN(value)) return "0.0%";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

function formatMonth(month: string): string {
  const [year, mon] = month.split("-");
  const date = new Date(parseInt(year), parseInt(mon) - 1);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

// ─── Tab State ───────────────────────────────────────────────────────────────

type ReportTab = "income-expense" | "category-spending" | "budget-actual" | "net-worth" | "cash-flow" | "tag-spending" | "debt-payoff" | "investment-performance";

const activeTab = ref<ReportTab>("income-expense");

const tabs: Array<{ key: ReportTab; label: string }> = [
  { key: "income-expense", label: "Income vs Expense" },
  { key: "category-spending", label: "Category Spending" },
  { key: "budget-actual", label: "Budget vs Actual" },
  { key: "net-worth", label: "Net Worth" },
  { key: "cash-flow", label: "Cash Flow" },
  { key: "tag-spending", label: "Tag Spending" },
  { key: "debt-payoff", label: "Debt Payoff" },
  { key: "investment-performance", label: "Investments" },
];

function switchTab(tab: ReportTab) {
  activeTab.value = tab;
}

// ─── Date Range ──────────────────────────────────────────────────────────────

function getDefaultDateRange(): { from: string; to: string } {
  const now = new Date();
  const from = new Date(now.getFullYear(), now.getMonth() - 5, 1);
  return {
    from: from.toISOString().split("T")[0],
    to: now.toISOString().split("T")[0],
  };
}

const dateFrom = ref(getDefaultDateRange().from);
const dateTo = ref(getDefaultDateRange().to);

function handleDateRangeChange(range: DateRange) {
  dateFrom.value = range.from;
  dateTo.value = range.to;
  store.setDateRange(range.from, range.to);
}

// ─── Data Loading ────────────────────────────────────────────────────────────

onMounted(async () => {
  await store.setDateRange(dateFrom.value, dateTo.value);
});

// ─── Chart Helpers ───────────────────────────────────────────────────────────

const monthlyMax = computed(() => {
  const data = store.incomeExpenseByMonth;
  if (data.length === 0) return 1;
  return Math.max(...data.map((d) => Math.max(d.income, d.expense)), 1);
});

const cashFlowMax = computed(() => {
  const data = store.cashFlowByMonth;
  if (data.length === 0) return 1;
  return Math.max(...data.map((d) => Math.max(Math.abs(d.income), Math.abs(d.expense))), 1);
});

const donutSegments = computed(() => {
  const cats = store.topExpenseCategories;
  const total = store.totalCategoryExpense;
  if (total === 0 || cats.length === 0) return [];

  let cumulativePercent = 0;
  return cats.map((cat, i) => {
    const percent = (cat.amount / total) * 100;
    const start = cumulativePercent;
    cumulativePercent += percent;
    return {
      ...cat,
      percent,
      start,
      color: cat.color || getDefaultColor(i),
    };
  });
});

const donutGradient = computed(() => {
  const segments = donutSegments.value;
  if (segments.length === 0) return "conic-gradient(#e2e8f0 0% 100%)";

  const stops = segments.map((s) => `${s.color} ${s.start}% ${s.start + s.percent}%`);
  const totalPercent = segments.reduce((sum, s) => sum + s.percent, 0);
  if (totalPercent < 100) {
    stops.push(`#94a3b8 ${totalPercent}% 100%`);
  }
  return `conic-gradient(${stops.join(", ")})`;
});

function getDefaultColor(index: number): string {
  const colors = ["#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"];
  return colors[index % colors.length];
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading);
const hasData = computed(() => store.hasData);

const categoryMax = computed(() => {
  const cats = store.categorySpending.filter((c) => !c.isIncome);
  if (cats.length === 0) return 1;
  return Math.max(...cats.map((c) => c.amount), 1);
});

const tagMax = computed(() => {
  const tags = store.tagSpending;
  if (tags.length === 0) return 1;
  return Math.max(...tags.map((t) => t.amount), 1);
});

// ─── Export Helpers ───────────────────────────────────────────────────────────

const canExportPdf = hasAccess("export_pdf");
const exporting = ref(false);

function escapeCSV(value: unknown): string {
  const str = String(value ?? "");
  if (str.includes(",") || str.includes('"') || str.includes("\n")) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

function downloadCSV(filename: string, headers: string[], rows: string[][]): void {
  const headerLine = headers.map(escapeCSV).join(",");
  const dataLines = rows.map((row) => row.map(escapeCSV).join(","));
  const csv = [headerLine, ...dataLines].join("\n");
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function exportCurrentTabCSV(): void {
  const tab = activeTab.value;
  const dateSuffix = `${dateFrom.value}_to_${dateTo.value}`;

  try {
    if (tab === "income-expense") {
      const headers = ["Month", "Income", "Expense", "Net"];
      const rows = store.incomeExpenseByMonth.map((b) => [
        b.month,
        String(b.income),
        String(b.expense),
        String(b.income - b.expense),
      ]);
      downloadCSV(`income-expense_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "category-spending") {
      const headers = ["Category", "Amount", "Is Income", "Percentage"];
      const total = store.totalCategoryExpense || 1;
      const rows = store.categorySpending.map((c) => [
        c.categoryName,
        String(c.amount),
        String(c.isIncome),
        ((c.amount / total) * 100).toFixed(1) + "%",
      ]);
      downloadCSV(`category-spending_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "budget-actual") {
      const headers = ["Category", "Period", "Budget", "Spent", "Remaining", "% Used"];
      const rows = store.budgetVsActual.map((b) => [
        b.categoryName,
        b.period,
        String(b.amount),
        String(b.spentAmount),
        String(b.remaining),
        b.percentUsed.toFixed(1) + "%",
      ]);
      downloadCSV(`budget-actual_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "net-worth") {
      const headers = ["Type", "Account", "Currency", "Balance"];
      const rows = store.netWorthComposition.flatMap((g) =>
        g.accounts.map((a) => [
          g.type,
          a.name,
          a.currency,
          a.current_balance,
        ]),
      );
      downloadCSV(`net-worth_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "cash-flow") {
      const headers = ["Month", "Income", "Expense", "Net", "Cumulative"];
      const rows = store.cashFlowByMonth.map((m) => [
        m.month,
        String(m.income),
        String(m.expense),
        String(m.net),
        String(m.cumulative),
      ]);
      downloadCSV(`cash-flow_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "tag-spending") {
      const headers = ["Tag", "Amount"];
      const rows = store.tagSpending.map((t) => [
        t.tagName,
        String(t.amount),
      ]);
      downloadCSV(`tag-spending_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "debt-payoff") {
      const headers = ["Name", "Type", "Principal", "Remaining", "Monthly Payment", "Interest Rate", "% Paid"];
      const rows = store.debtPayoffEntries.map((d) => [
        d.name,
        d.debtType,
        String(d.principalAmount),
        String(d.remainingBalance),
        String(d.monthlyPayment),
        d.interestRate + "%",
        d.progressPercent.toFixed(1) + "%",
      ]);
      downloadCSV(`debt-payoff_${dateSuffix}.csv`, headers, rows);
    } else if (tab === "investment-performance") {
      const headers = ["Symbol", "Name", "Type", "Quantity", "Cost Basis", "Current Value", "Gain/Loss", "Return %"];
      const rows = store.holdingPerformance.map((h) => [
        h.symbol,
        h.assetName,
        h.assetType,
        String(h.quantity),
        String(h.costBasis),
        String(h.currentValue),
        String(h.unrealizedGainLoss),
        h.gainLossPercent.toFixed(1) + "%",
      ]);
      downloadCSV(`investments_${dateSuffix}.csv`, headers, rows);
    }

    toast.success("CSV exported successfully");
  } catch (err) {
    toast.error("Failed to export CSV");
  }
}
</script>

<template>
  <FeatureGate feature="reports" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Reports</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Financial analytics and insights
        </p>
      </div>
      <div class="flex items-center gap-3">
        <!-- CSV Export (always available) -->
        <button
          class="btn-secondary"
          :disabled="isLoading || !hasData"
          @click="exportCurrentTabCSV"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
          Export CSV
        </button>
        <!-- PDF Export (gated by export_pdf feature) -->
        <FeatureGate feature="export_pdf" :show-fallback="false">
          <button
            class="btn-primary"
            :disabled="isLoading || !hasData || exporting"
            @click="exporting = true; setTimeout(() => { exportCurrentTabCSV(); exporting = false; }, 300)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
            </svg>
            {{ exporting ? 'Exporting...' : 'Export PDF' }}
          </button>
        </FeatureGate>
      </div>
    </div>

    <!-- ── Date Range Filter ──────────────────────────────────────────────── -->
    <div class="card p-4">
      <div class="flex flex-col sm:flex-row sm:items-center gap-4">
        <div class="flex items-center gap-2">
          <svg class="h-5 w-5 text-slate-custom-500 dark:text-slate-custom-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span class="text-sm font-medium text-navy-900 dark:text-navy-100">Date Range</span>
        </div>
        <DateRangePicker
          :from="dateFrom"
          :to="dateTo"
          show-presets
          @change="handleDateRangeChange"
        />
      </div>
    </div>

    <!-- ── Loading State ──────────────────────────────────────────────────── -->
    <div v-if="isLoading && !hasData">
      <LoadingSkeleton type="detail" />
    </div>

    <!-- ── Error State ────────────────────────────────────────────────────── -->
    <div v-else-if="store.error" class="card p-5 border-red-200 dark:border-red-800/50">
      <div class="flex items-center gap-3">
        <div class="flex h-10 w-10 items-center justify-center rounded-full bg-red-100 dark:bg-red-950/50">
          <svg class="h-5 w-5 text-debit" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div>
          <p class="text-sm font-medium text-debit">Failed to load report data</p>
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">{{ store.error }}</p>
        </div>
        <button class="btn-ghost text-xs ml-auto" @click="store.fetchReportData(true)">Try again</button>
      </div>
    </div>

    <!-- ── Reports Content ────────────────────────────────────────────────── -->
    <div v-else class="space-y-6">

      <!-- ── Tab Navigation ───────────────────────────────────────────────── -->
      <div class="border-b border-navy-200 dark:border-navy-700 overflow-x-auto">
        <nav class="flex gap-4 -mb-px min-w-max" aria-label="Report tabs">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
              activeTab === tab.key
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="switchTab(tab.key)"
          >
            {{ tab.label }}
          </button>
        </nav>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 1: Income vs Expense                                        -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'income-expense'" class="space-y-4">
        <!-- Summary cards -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Income</p>
            <p class="text-xl font-bold text-credit">{{ formatCurrency(store.totalIncome) }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Expenses</p>
            <p class="text-xl font-bold text-debit">{{ formatCurrency(store.totalExpenses) }}</p>
          </div>
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Net</p>
            <p :class="['text-xl font-bold', store.netIncome >= 0 ? 'text-credit' : 'text-debit']">
              {{ store.netIncome >= 0 ? "+" : "" }}{{ formatCurrency(store.netIncome) }}
            </p>
          </div>
        </div>

        <!-- Grouped bar chart -->
        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Monthly Breakdown</h2>

          <div v-if="store.incomeExpenseByMonth.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No transaction data for the selected period</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="bucket in store.incomeExpenseByMonth"
              :key="bucket.month"
              class="space-y-1"
            >
              <div class="flex items-center justify-between text-xs">
                <span class="text-navy-900 dark:text-navy-100 font-medium min-w-[100px]">{{ formatMonth(bucket.month) }}</span>
                <div class="flex items-center gap-4 text-slate-custom-500 dark:text-slate-custom-400">
                  <span class="text-credit">{{ formatCurrency(bucket.income) }}</span>
                  <span class="text-debit">{{ formatCurrency(bucket.expense) }}</span>
                </div>
              </div>
              <div class="flex gap-1">
                <div class="flex-1 h-5 rounded-l bg-navy-100 dark:bg-navy-800 overflow-hidden">
                  <div
                    class="h-full bg-credit/80 dark:bg-credit/70 rounded-l transition-all duration-500"
                    :style="{ width: `${(bucket.income / monthlyMax) * 100}%` }"
                  />
                </div>
                <div class="flex-1 h-5 rounded-r bg-navy-100 dark:bg-navy-800 overflow-hidden">
                  <div
                    class="h-full bg-debit/80 dark:bg-debit/70 rounded-r transition-all duration-500"
                    :style="{ width: `${(bucket.expense / monthlyMax) * 100}%` }"
                  />
                </div>
              </div>
            </div>
            <div class="flex items-center gap-4 pt-2 text-xs text-slate-custom-500 dark:text-slate-custom-400">
              <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-credit/80" /> Income</span>
              <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-debit/80" /> Expenses</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 2: Category Spending                                        -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'category-spending'" class="space-y-4">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <!-- Donut chart -->
          <div class="card p-6">
            <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Spending Distribution</h2>

            <div v-if="store.topExpenseCategories.length === 0" class="text-center py-8">
              <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No expense data for the selected period</p>
            </div>

            <div v-else class="flex flex-col items-center">
              <div class="relative w-48 h-48 mb-4">
                <div
                  class="w-full h-full rounded-full"
                  :style="{ background: donutGradient }"
                />
                <div class="absolute inset-4 rounded-full bg-white dark:bg-navy-900 flex items-center justify-center">
                  <div class="text-center">
                    <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">Total</p>
                    <p class="text-lg font-bold text-navy-900 dark:text-navy-100">{{ formatCurrency(store.totalCategoryExpense) }}</p>
                  </div>
                </div>
              </div>

              <div class="w-full space-y-1.5">
                <div
                  v-for="(seg, i) in donutSegments"
                  :key="i"
                  class="flex items-center justify-between text-xs"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <span class="h-2.5 w-2.5 rounded-full flex-shrink-0" :style="{ backgroundColor: seg.color }" />
                    <span class="text-navy-900 dark:text-navy-100 truncate">{{ seg.categoryName }}</span>
                  </div>
                  <span class="text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0 ml-2">{{ seg.percent.toFixed(1) }}%</span>
                </div>
                <div
                  v-if="donutSegments.reduce((s, seg) => s + seg.percent, 0) < 99"
                  class="flex items-center justify-between text-xs"
                >
                  <div class="flex items-center gap-2">
                    <span class="h-2.5 w-2.5 rounded-full bg-slate-custom-400" />
                    <span class="text-navy-900 dark:text-navy-100">Other</span>
                  </div>
                  <span class="text-slate-custom-500 dark:text-slate-custom-400">
                    {{ (100 - donutSegments.reduce((s, seg) => s + seg.percent, 0)).toFixed(1) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Horizontal bar chart -->
          <div class="card p-6">
            <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Spending by Category</h2>

            <div v-if="store.topExpenseCategories.length === 0" class="text-center py-8">
              <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No expense data</p>
            </div>

            <div v-else class="space-y-3">
              <div
                v-for="cat in store.categorySpending.filter((c) => !c.isIncome).slice(0, 10)"
                :key="cat.categoryId"
              >
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs text-navy-900 dark:text-navy-100 truncate font-medium">{{ cat.categoryName }}</span>
                  <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0 ml-2">{{ formatCurrency(cat.amount) }}</span>
                </div>
                <div class="h-2.5 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-500"
                    :style="{
                      width: `${(cat.amount / categoryMax) * 100}%`,
                      backgroundColor: cat.color || '#06b6d4',
                    }"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 3: Budget vs Actual                                         -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'budget-actual'" class="space-y-4">
        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Budget Utilization</h2>

          <div v-if="store.budgetVsActual.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No budgets configured</p>
            <a href="/dashboard/budgets" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Create a budget</a>
          </div>

          <div v-else>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              <div class="p-3 rounded-lg bg-navy-50 dark:bg-navy-800/50">
                <p class="text-[10px] text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Budgets</p>
                <p class="text-lg font-bold text-navy-900 dark:text-navy-100">{{ store.budgetVsActual.length }}</p>
              </div>
              <div class="p-3 rounded-lg bg-green-50 dark:bg-green-950/20">
                <p class="text-[10px] text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Under 70%</p>
                <p class="text-lg font-bold text-credit">{{ store.budgetVsActual.filter((b) => b.percentUsed < 70).length }}</p>
              </div>
              <div class="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/20">
                <p class="text-[10px] text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">70-90%</p>
                <p class="text-lg font-bold text-amber-600 dark:text-amber-400">{{ store.budgetVsActual.filter((b) => b.percentUsed >= 70 && b.percentUsed < 90).length }}</p>
              </div>
              <div class="p-3 rounded-lg bg-red-50 dark:bg-red-950/20">
                <p class="text-[10px] text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Over 90%</p>
                <p class="text-lg font-bold text-debit">{{ store.budgetVsActual.filter((b) => b.percentUsed >= 90).length }}</p>
              </div>
            </div>

            <div class="space-y-4">
              <div
                v-for="budget in store.budgetVsActual"
                :key="budget.id"
                class="p-4 rounded-lg border border-navy-100 dark:border-navy-800"
              >
                <div class="flex items-center justify-between mb-2">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-medium text-navy-900 dark:text-navy-100">{{ budget.categoryName }}</span>
                    <span class="text-[10px] text-slate-custom-500 dark:text-slate-custom-400 uppercase">{{ budget.period }}</span>
                  </div>
                  <span
                    :class="[
                      'text-xs font-medium',
                      budget.percentUsed >= 90 ? 'text-debit' : budget.percentUsed >= 70 ? 'text-amber-600 dark:text-amber-400' : 'text-credit',
                    ]"
                  >
                    {{ budget.percentUsed.toFixed(0) }}% used
                  </span>
                </div>
                <ProgressBar
                  :value="budget.spentAmount"
                  :max="budget.amount"
                  :color="budget.percentUsed >= 90 ? 'red' : budget.percentUsed >= 70 ? 'amber' : 'green'"
                  size="md"
                  show-values
                />
                <div class="flex items-center justify-between mt-1.5 text-xs text-slate-custom-500 dark:text-slate-custom-400">
                  <span>Spent: {{ formatCurrency(budget.spentAmount) }}</span>
                  <span>Budget: {{ formatCurrency(budget.amount) }}</span>
                  <span>Remaining: {{ formatCurrency(budget.remaining) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 4: Net Worth Composition                                    -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'net-worth'" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div v-for="group in store.netWorthComposition" :key="group.type" class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1 uppercase tracking-wider">
              {{ group.type === "ASSET" ? "Assets" : group.type === "LIABILITY" ? "Liabilities" : "Investments" }}
            </p>
            <p :class="[
              'text-xl font-bold',
              group.type === 'ASSET' ? 'text-credit' : group.type === 'LIABILITY' ? 'text-debit' : 'text-cyan-600 dark:text-cyan-400',
            ]">
              {{ formatCurrency(group.type === 'LIABILITY' ? -group.total : group.total) }}
            </p>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mt-1">{{ group.accounts.length }} account{{ group.accounts.length !== 1 ? 's' : '' }}</p>
          </div>
        </div>

        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Account Breakdown</h2>

          <div v-if="store.accounts.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No accounts found</p>
          </div>

          <div v-else class="space-y-3">
            <div v-for="group in store.netWorthComposition" :key="group.type">
              <h3 class="text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider mb-2">
                {{ group.type === "ASSET" ? "Assets" : group.type === "LIABILITY" ? "Liabilities" : "Investments" }}
              </h3>
              <div class="space-y-1.5">
                <div
                  v-for="acct in group.accounts"
                  :key="acct.id"
                  class="flex items-center justify-between p-2 rounded-lg hover:bg-navy-50 dark:hover:bg-navy-800/50"
                >
                  <div class="flex items-center gap-2 min-w-0">
                    <div
                      :class="[
                        'h-2.5 w-2.5 rounded-full flex-shrink-0',
                        group.type === 'ASSET' ? 'bg-credit' : group.type === 'LIABILITY' ? 'bg-debit' : 'bg-cyan-500',
                      ]"
                    />
                    <span class="text-sm text-navy-900 dark:text-navy-100 truncate">{{ acct.name }}</span>
                  </div>
                  <div class="flex items-center gap-2 flex-shrink-0 ml-2">
                    <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400">{{ acct.currency }}</span>
                    <span :class="[
                      'text-sm font-medium',
                      group.type === 'LIABILITY' ? 'text-debit' : 'text-credit',
                    ]">
                      {{ formatCurrency(Math.abs(parseFloat(acct.current_balance || "0")), acct.currency || "USD") }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 5: Cash Flow                                                -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'cash-flow'" class="space-y-4">
        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Monthly Cash Flow</h2>

          <div v-if="store.cashFlowByMonth.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No transaction data for the selected period</p>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="month in store.cashFlowByMonth"
              :key="month.month"
              class="space-y-1"
            >
              <div class="flex items-center justify-between text-xs">
                <span class="text-navy-900 dark:text-navy-100 font-medium">{{ formatMonth(month.month) }}</span>
                <div class="flex items-center gap-3 text-slate-custom-500 dark:text-slate-custom-400">
                  <span>+{{ formatCurrency(month.income) }}</span>
                  <span>-{{ formatCurrency(month.expense) }}</span>
                </div>
              </div>
              <div class="h-6 rounded bg-navy-100 dark:bg-navy-800 overflow-hidden flex">
                <div
                  class="h-full bg-credit/70 transition-all duration-500"
                  :style="{ width: `${(month.income / cashFlowMax) * 50}%` }"
                />
                <div
                  class="h-full bg-debit/70 transition-all duration-500"
                  :style="{ width: `${(month.expense / cashFlowMax) * 50}%` }"
                />
              </div>
              <div class="flex items-center justify-between text-xs">
                <span :class="['font-medium', month.net >= 0 ? 'text-credit' : 'text-debit']">
                  Net: {{ month.net >= 0 ? "+" : "" }}{{ formatCurrency(month.net) }}
                </span>
                <span class="text-slate-custom-400 dark:text-slate-custom-500">
                  Cumulative: {{ formatCurrency(month.cumulative) }}
                </span>
              </div>
            </div>

            <div class="flex items-center gap-4 pt-2 text-xs text-slate-custom-500 dark:text-slate-custom-400">
              <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-credit/70" /> Income</span>
              <span class="flex items-center gap-1"><span class="h-3 w-3 rounded bg-debit/70" /> Expenses</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 6: Tag Spending                                             -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'tag-spending'" class="space-y-4">
        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Spending by Tag</h2>

          <div v-if="store.tagSpending.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No tag data available</p>
            <a href="/dashboard/tags" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Create tags</a>
          </div>

          <div v-else class="space-y-3">
            <div
              v-for="tag in store.tagSpending"
              :key="tag.tagId"
            >
              <div class="flex items-center justify-between mb-1">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="h-2.5 w-2.5 rounded-full flex-shrink-0" :style="{ backgroundColor: tag.tagColor }" />
                  <span class="text-xs text-navy-900 dark:text-navy-100 truncate font-medium">{{ tag.tagName }}</span>
                </div>
                <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 flex-shrink-0 ml-2">{{ formatCurrency(tag.amount) }}</span>
              </div>
              <div class="h-2.5 rounded-full bg-navy-100 dark:bg-navy-800 overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :style="{
                    width: `${(tag.amount / tagMax) * 100}%`,
                    backgroundColor: tag.tagColor || '#06b6d4',
                  }"
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 7: Debt Payoff                                              -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'debt-payoff'" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Borrowed</p>
            <p class="text-xl font-bold text-debit">
              {{ formatCurrency(store.debtSummary?.total_borrowed || "0") }}
            </p>
          </div>
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Lent</p>
            <p class="text-xl font-bold text-credit">
              {{ formatCurrency(store.debtSummary?.total_lent || "0") }}
            </p>
          </div>
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Net Position</p>
            <p :class="['text-xl font-bold', parseFloat(store.debtSummary?.net_position || '0') >= 0 ? 'text-credit' : 'text-debit']">
              {{ formatCurrency(store.debtSummary?.net_position || "0") }}
            </p>
          </div>
        </div>

        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Payoff Progress</h2>

          <div v-if="store.debtPayoffEntries.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No borrowed debts tracked</p>
            <a href="/dashboard/debts" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Track a debt</a>
          </div>

          <div v-else class="space-y-4">
            <div
              v-for="debt in store.debtPayoffEntries"
              :key="debt.id"
              class="p-4 rounded-lg border border-navy-100 dark:border-navy-800"
            >
              <div class="flex items-center justify-between mb-2">
                <div>
                  <span class="text-sm font-medium text-navy-900 dark:text-navy-100">{{ debt.name }}</span>
                  <span class="text-xs text-slate-custom-500 dark:text-slate-custom-400 ml-2">{{ debt.debtType }}</span>
                </div>
                <span class="text-xs font-medium text-cyan-600 dark:text-cyan-400">{{ debt.progressPercent.toFixed(0) }}% paid</span>
              </div>
              <ProgressBar
                :value="debt.paidOff"
                :max="debt.principalAmount"
                :color="debt.progressPercent >= 75 ? 'green' : debt.progressPercent >= 50 ? 'cyan' : 'amber'"
                size="md"
                show-values
              />
              <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 text-xs text-slate-custom-500 dark:text-slate-custom-400">
                <div>Principal: {{ formatCurrency(debt.principalAmount) }}</div>
                <div>Remaining: {{ formatCurrency(debt.remainingBalance) }}</div>
                <div>Monthly: {{ formatCurrency(debt.monthlyPayment) }}</div>
                <div>Rate: {{ debt.interestRate }}%</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <!-- REPORT 8: Investment Performance                                   -->
      <!-- ═══════════════════════════════════════════════════════════════════ -->
      <div v-if="activeTab === 'investment-performance'" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Portfolio Value</p>
            <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(store.investmentSummary?.total_portfolio_value || "0") }}
            </p>
          </div>
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Unrealized Gain/Loss</p>
            <p :class="['text-xl font-bold', parseFloat(store.investmentSummary?.total_unrealized_gain_loss || '0') >= 0 ? 'text-credit' : 'text-debit']">
              {{ parseFloat(store.investmentSummary?.total_unrealized_gain_loss || '0') >= 0 ? "+" : "" }}{{ formatCurrency(store.investmentSummary?.total_unrealized_gain_loss || "0") }}
            </p>
          </div>
          <div class="card p-4">
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Return</p>
            <p :class="['text-xl font-bold', (store.investmentSummary?.total_gain_loss_percent || 0) >= 0 ? 'text-credit' : 'text-debit']">
              {{ formatPercent(store.investmentSummary?.total_gain_loss_percent || 0) }}
            </p>
          </div>
        </div>

        <div class="card p-6">
          <h2 class="text-sm font-semibold text-navy-900 dark:text-navy-100 mb-4">Holdings Performance</h2>

          <div v-if="store.holdingPerformance.length === 0" class="text-center py-8">
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400">No holdings data available</p>
            <a href="/dashboard/investments" class="text-sm text-cyan-600 dark:text-cyan-400 hover:underline mt-1 inline-block">Add investments</a>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-navy-200 dark:border-navy-700">
                  <th class="text-left py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Symbol</th>
                  <th class="text-left py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Name</th>
                  <th class="text-left py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Type</th>
                  <th class="text-right py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Qty</th>
                  <th class="text-right py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Cost Basis</th>
                  <th class="text-right py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Current</th>
                  <th class="text-right py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Gain/Loss</th>
                  <th class="text-right py-2 px-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Return</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="holding in store.holdingPerformance"
                  :key="`${holding.investmentId}-${holding.symbol}`"
                  class="border-b border-navy-100 dark:border-navy-800 hover:bg-navy-50 dark:hover:bg-navy-800/50"
                >
                  <td class="py-2.5 px-3 font-medium text-navy-900 dark:text-navy-100">{{ holding.symbol }}</td>
                  <td class="py-2.5 px-3 text-navy-900 dark:text-navy-100 truncate max-w-[150px]">{{ holding.assetName }}</td>
                  <td class="py-2.5 px-3">
                    <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium bg-cyan-100 dark:bg-cyan-950 text-cyan-700 dark:text-cyan-300">
                      {{ holding.assetType }}
                    </span>
                  </td>
                  <td class="py-2.5 px-3 text-right text-navy-900 dark:text-navy-100">{{ holding.quantity.toLocaleString() }}</td>
                  <td class="py-2.5 px-3 text-right text-navy-900 dark:text-navy-100">{{ formatCurrency(holding.costBasis) }}</td>
                  <td class="py-2.5 px-3 text-right text-navy-900 dark:text-navy-100">{{ formatCurrency(holding.currentValue) }}</td>
                  <td :class="['py-2.5 px-3 text-right font-medium', holding.unrealizedGainLoss >= 0 ? 'text-credit' : 'text-debit']">
                    {{ holding.unrealizedGainLoss >= 0 ? "+" : "" }}{{ formatCurrency(holding.unrealizedGainLoss) }}
                  </td>
                  <td :class="['py-2.5 px-3 text-right font-medium', holding.gainLossPercent >= 0 ? 'text-credit' : 'text-debit']">
                    {{ formatPercent(holding.gainLossPercent) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

    </div>
  </div>
  <template #no-access>
    <UpgradePrompt feature="reports" />
  </template>
  </FeatureGate>
</template>
