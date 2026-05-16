/**
 * Investment Store — Pinia CRUD store for InvestmentAccount entities.
 *
 * Extends standard CRUD with:
 *   - summary — cached portfolio summary (total value, cost basis, gain/loss)
 *   - holdings[] — holdings for the currently viewed investment account
 *   - Holding CRUD (fetchHoldings, createHolding, updateHolding, deleteHolding)
 *   - Soft delete/restore support (no activate/deactivate on investments)
 *
 * InvestmentAccounts link to existing INVESTMENT-type Accounts.
 * Each InvestmentAccount has Holdings (stocks, ETFs, crypto, bonds, etc.)
 * with cost basis, current value, and unrealized gain/loss tracking.
 */

import { defineStore } from "pinia";
import {
  crudState,
  crudGetters,
  crudActions,
  extractErrorMessage,
  extractFieldErrors,
} from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  InvestmentAccountOut,
  InvestmentAccountCreate,
  InvestmentAccountUpdate,
  InvestmentSummary,
  HoldingOut,
  HoldingUpdate,
  MessageOut,
} from "@/lib/ledgerTypes";

export const useInvestmentStore = defineStore("investment", {
  state: () => ({
    ...crudState<InvestmentAccountOut, { limit: number; offset: number }, InvestmentAccountOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    summary: null as InvestmentSummary | null,
    summaryLoaded: false,
    holdings: [] as HoldingOut[],
    holdingsLoaded: false,
  }),

  getters: {
    ...crudGetters<InvestmentAccountOut>(),

    /** Active investment accounts only */
    activeInvestments: (state) => state.items.filter((i) => i.is_active && !i.is_deleted),

    /** Total portfolio value from summary */
    totalPortfolioValue: (state) => {
      if (!state.summary) return 0;
      return parseFloat(state.summary.total_portfolio_value || "0");
    },

    /** Total unrealized gain/loss from summary */
    totalUnrealizedGainLoss: (state) => {
      if (!state.summary) return 0;
      return parseFloat(state.summary.total_unrealized_gain_loss || "0");
    },
  },

  actions: {
    ...crudActions<
      InvestmentAccountOut,
      InvestmentAccountCreate,
      InvestmentAccountUpdate,
      { limit: number; offset: number },
      InvestmentAccountOut
    >({
      storeId: "investment",
      api: {
        list: (filters?) => ledgerApi.investments.list(filters),
        get: (id) => ledgerApi.investments.get(id),
        create: (data) => ledgerApi.investments.create(data),
        update: (id, data) => ledgerApi.investments.update(id, data),
        remove: (id) => ledgerApi.investments.remove(id),
        restore: (id) => ledgerApi.investments.restore(id),
        // Investments don't have activate/deactivate endpoints
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Investment Summary ──

    async fetchSummary(forceRefresh = false): Promise<InvestmentSummary | null> {
      if (this.summaryLoaded && !forceRefresh) {
        return this.summary;
      }
      this.loadingAction = "fetchSummary";
      this.error = null;
      try {
        const data = await ledgerApi.investments.summary();
        this.summary = data;
        this.summaryLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return null;
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Holdings ──

    async fetchHoldings(investmentId: number): Promise<HoldingOut[]> {
      this.loadingAction = "fetchHoldings";
      this.error = null;
      try {
        const data = await ledgerApi.holdings.list(investmentId);
        this.holdings = data;
        this.holdingsLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    async createHolding(
      investmentId: number,
      data: Omit<import("@/lib/ledgerTypes").HoldingCreate, "investment_account_id">,
    ): Promise<HoldingOut | null> {
      this.loadingAction = "createHolding";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.holdings.create(investmentId, data);
        this.holdings.push(result);
        // Refresh the investment to get updated portfolio_value & gain/loss
        await this.fetchOne(investmentId);
        // Refresh summary
        this.summaryLoaded = false;
        this.fetchSummary(true);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        this.fieldErrors = extractFieldErrors(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async updateHolding(
      investmentId: number,
      holdingId: number,
      data: HoldingUpdate,
    ): Promise<HoldingOut | null> {
      this.loadingAction = "updateHolding";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.holdings.update(investmentId, holdingId, data);
        const idx = this.holdings.findIndex((h) => h.id === holdingId);
        if (idx !== -1) {
          this.holdings[idx] = result;
        }
        // Refresh the investment to get updated portfolio_value & gain/loss
        await this.fetchOne(investmentId);
        // Refresh summary
        this.summaryLoaded = false;
        this.fetchSummary(true);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async deleteHolding(investmentId: number, holdingId: number): Promise<MessageOut | null> {
      this.loadingAction = "deleteHolding";
      this.error = null;
      try {
        const result = await ledgerApi.holdings.remove(investmentId, holdingId);
        this.holdings = this.holdings.filter((h) => h.id !== holdingId);
        // Refresh the investment to get updated portfolio_value
        await this.fetchOne(investmentId);
        // Refresh summary
        this.summaryLoaded = false;
        this.fetchSummary(true);
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
      this.summary = null;
      this.summaryLoaded = false;
      this.holdings = [];
      this.holdingsLoaded = false;
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
