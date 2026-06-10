/**
 * Budget Store — Pinia CRUD store for Budget entities.
 *
 * Extends standard CRUD with:
 *   - overview[] — cached budget overview for dashboard widget
 *   - Extra getters for spending summaries
 *
 * Budgets support activate/deactivate (unlike Tags) and
 * have a special overview endpoint for dashboard display.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  BudgetOut,
  BudgetCreate,
  BudgetUpdate,
  BudgetFilter,
  BudgetListOut,
} from "@/lib/ledgerTypes";

export const useBudgetStore = defineStore("budget", {
  state: () => ({
    ...crudState<BudgetOut, BudgetFilter, BudgetListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    overview: [] as BudgetListOut[],
    overviewLoaded: false,
  }),

  getters: {
    ...crudGetters<BudgetOut>(),

    /** Budgets that are under 70% used */
    healthyBudgets(): BudgetOut[] {
      return this.items.filter((b) => b.percent_used < 70);
    },

    /** Budgets between 70-90% used */
    warningBudgets(): BudgetOut[] {
      return this.items.filter((b) => b.percent_used >= 70 && b.percent_used < 90);
    },

    /** Budgets over 90% used */
    overBudgets(): BudgetOut[] {
      return this.items.filter((b) => b.percent_used >= 90);
    },

    /** Total budget amount across all active budgets */
    totalBudgetAmount: (state) =>
      state.items
        .filter((b) => b.is_active)
        .reduce((sum, b) => sum + parseFloat(b.amount || "0"), 0),

    /** Total spent across all active budgets */
    totalSpent: (state) =>
      state.items
        .filter((b) => b.is_active)
        .reduce((sum, b) => sum + parseFloat(b.spent_amount || "0"), 0),

    /** Total remaining across all active budgets */
    totalRemaining(): number {
      return this.totalBudgetAmount - this.totalSpent;
    },

    /** Average percent used across active budgets */
    averagePercentUsed: (state) => {
      const active = state.items.filter((b) => b.is_active);
      if (active.length === 0) return 0;
      return active.reduce((sum, b) => sum + b.percent_used, 0) / active.length;
    },
  },

  actions: {
    ...crudActions<BudgetOut, BudgetCreate, BudgetUpdate, BudgetFilter, BudgetListOut>({
      storeId: "budget",
      api: {
        list: ledgerApi.budgets.list,
        get: ledgerApi.budgets.get,
        create: ledgerApi.budgets.create,
        update: ledgerApi.budgets.update,
        remove: ledgerApi.budgets.remove,
        restore: ledgerApi.budgets.restore,
        activate: ledgerApi.budgets.activate,
        deactivate: ledgerApi.budgets.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Budget Overview (Dashboard) ──

    async fetchOverview(forceRefresh = false): Promise<BudgetListOut[]> {
      if (this.overviewLoaded && !forceRefresh) {
        return this.overview;
      }
      this.loadingAction = "fetchOverview";
      this.error = null;
      try {
        const data = await ledgerApi.budgets.overview();
        this.overview = data;
        this.overviewLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Reset ──

    /** Reset all state including overview */
    $resetCrud() {
      this.overview = [];
      this.overviewLoaded = false;
      this.items = [];
      this.current = null;
      this.loading = false;
      this.loadingAction = "";
      this.error = null;
      this.fieldErrors = {};
      this.total = 0;
      this.dropdownLoaded = false;
      this.listLoaded = false;
      this.lastFetched = null;
    },
  },
});
