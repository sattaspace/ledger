/**
 * SavingsGoal Store — Pinia CRUD store for SavingsGoal entities.
 *
 * Extends standard CRUD with:
 *   - dashboard — cached list of active/uncompleted goals for dashboard widget
 *   - contribute — add a contribution to a goal (updates current_amount + progress)
 *   - Soft delete/restore + activate/deactivate support
 *
 * SavingsGoals track progress toward a financial target with
 * current_amount, target_amount, deadline, and optional linked account.
 * Backend computes progress_percent, remaining, is_completed, days_remaining.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  SavingsGoalOut,
  SavingsGoalCreate,
  SavingsGoalUpdate,
  SavingsGoalFilter,
  SavingsGoalListOut,
  SavingsContribution,
  SavingsContributionOut,
} from "@/lib/ledgerTypes";

export const useSavingsGoalStore = defineStore("savingsGoal", {
  state: () => ({
    ...crudState<SavingsGoalOut, SavingsGoalFilter, SavingsGoalListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    dashboard: [] as SavingsGoalListOut[],
    dashboardLoaded: false,
  }),

  getters: {
    ...crudGetters<SavingsGoalOut>(),

    /** Active goals that are not yet completed */
    activeGoals: (state) =>
      state.items.filter((g) => g.is_active && !g.is_deleted && !g.is_completed),

    /** Goals that have been completed */
    completedGoals: (state) => state.items.filter((g) => g.is_completed && !g.is_deleted),

    /** Total saved across all active goals */
    totalSaved: (state) =>
      state.items
        .filter((g) => g.is_active && !g.is_deleted)
        .reduce((sum, g) => sum + parseFloat(g.current_amount || "0"), 0),

    /** Total target across all active goals */
    totalTarget: (state) =>
      state.items
        .filter((g) => g.is_active && !g.is_deleted)
        .reduce((sum, g) => sum + parseFloat(g.target_amount || "0"), 0),

    /** Overall progress percent across all active goals */
    overallProgress(): number {
      if (this.totalTarget === 0) return 0;
      return Math.min(Math.round((this.totalSaved / this.totalTarget) * 100), 100);
    },
  },

  actions: {
    ...crudActions<
      SavingsGoalOut,
      SavingsGoalCreate,
      SavingsGoalUpdate,
      SavingsGoalFilter,
      SavingsGoalListOut
    >({
      storeId: "savingsGoal",
      api: {
        list: ledgerApi.savingsGoals.list,
        get: ledgerApi.savingsGoals.get,
        create: ledgerApi.savingsGoals.create,
        update: ledgerApi.savingsGoals.update,
        remove: ledgerApi.savingsGoals.remove,
        restore: ledgerApi.savingsGoals.restore,
        activate: ledgerApi.savingsGoals.activate,
        deactivate: ledgerApi.savingsGoals.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Dashboard ──

    async fetchDashboard(forceRefresh = false): Promise<SavingsGoalListOut[]> {
      if (this.dashboardLoaded && !forceRefresh) {
        return this.dashboard;
      }
      this.loadingAction = "fetchDashboard";
      this.error = null;
      try {
        const data = await ledgerApi.savingsGoals.dashboard();
        this.dashboard = data;
        this.dashboardLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Contribute ──

    async contribute(
      goalId: number,
      data: SavingsContribution,
    ): Promise<SavingsContributionOut | null> {
      this.loadingAction = "contribute";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.savingsGoals.contribute(goalId, data);
        // Refresh the goal to get updated current_amount, progress_percent, is_completed
        await this.fetchOne(goalId);
        // Invalidate dashboard
        this.dashboardLoaded = false;
        this.fetchDashboard(true);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Reset ──

    /** Reset all state including sub-resources */
    $resetCrud() {
      this.dashboard = [];
      this.dashboardLoaded = false;
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
