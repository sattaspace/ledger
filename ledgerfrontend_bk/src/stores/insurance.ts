/**
 * Insurance Store — Pinia CRUD store for InsurancePolicy entities.
 *
 * Extends standard CRUD with:
 *   - renewals — cached list of policies with upcoming renewals
 *   - Soft delete/restore + activate/deactivate support
 *
 * InsurancePolicies track policy_name, insurance_type, provider,
 * premium_amount, premium_frequency, renewal_date, coverage_amount,
 * and deductible. Renewals endpoint returns policies due within N days.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  InsurancePolicyOut,
  InsurancePolicyCreate,
  InsurancePolicyUpdate,
  InsurancePolicyFilter,
  InsurancePolicyListOut,
} from "@/lib/ledgerTypes";

export const useInsuranceStore = defineStore("insurance", {
  state: () => ({
    ...crudState<InsurancePolicyOut, InsurancePolicyFilter, InsurancePolicyListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    renewals: [] as InsurancePolicyListOut[],
    renewalsLoaded: false,
  }),

  getters: {
    ...crudGetters<InsurancePolicyOut>(),

    /** Active, non-deleted policies */
    activePolicies: (state) => state.items.filter((p) => p.is_active && !p.is_deleted),

    /** Policies grouped by insurance_type */
    byType(): Record<string, InsurancePolicyOut[]> {
      const map: Record<string, InsurancePolicyOut[]> = {};
      for (const p of this.items) {
        const t = p.insurance_type || "OTHER";
        if (!map[t]) map[t] = [];
        map[t].push(p);
      }
      return map;
    },

    /** Total monthly premium cost across all active policies */
    totalMonthlyPremium: (state) => {
      return state.items
        .filter((p) => p.is_active && !p.is_deleted)
        .reduce((sum, p) => {
          const amount = parseFloat(p.premium_amount || "0");
          // Normalize to monthly
          if (p.premium_frequency === "YEARLY") return sum + amount / 12;
          if (p.premium_frequency === "QUARTERLY") return sum + amount / 3;
          return sum + amount; // MONTHLY or default
        }, 0);
    },

    /** Policies with renewal within 30 days */
    upcomingRenewals: (state) =>
      state.items.filter((p) => {
        if (!p.renewal_date || p.is_deleted) return false;
        const daysUntil = Math.ceil(
          (new Date(p.renewal_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
        );
        return daysUntil >= 0 && daysUntil <= 30;
      }),
  },

  actions: {
    ...crudActions<
      InsurancePolicyOut,
      InsurancePolicyCreate,
      InsurancePolicyUpdate,
      InsurancePolicyFilter,
      InsurancePolicyListOut
    >({
      storeId: "insurance",
      api: {
        list: ledgerApi.insurance.list,
        get: ledgerApi.insurance.get,
        create: ledgerApi.insurance.create,
        update: ledgerApi.insurance.update,
        remove: ledgerApi.insurance.remove,
        restore: ledgerApi.insurance.restore,
        activate: ledgerApi.insurance.activate,
        deactivate: ledgerApi.insurance.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Renewals ──

    async fetchRenewals(days = 60, forceRefresh = false): Promise<InsurancePolicyListOut[]> {
      if (this.renewalsLoaded && !forceRefresh) {
        return this.renewals;
      }
      this.loadingAction = "fetchRenewals";
      this.error = null;
      try {
        const data = await ledgerApi.insurance.renewals(days);
        this.renewals = data;
        this.renewalsLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Reset ──

    /** Reset all state including sub-resources */
    $resetCrud() {
      this.renewals = [];
      this.renewalsLoaded = false;
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
