/**
 * Debt Store — Pinia CRUD store for DebtFacility entities.
 *
 * Extends standard CRUD with:
 *   - summary — cached debt summary (total borrowed/lent/net position)
 *   - payments[] — payments for the currently viewed debt
 *   - Payment CRUD (fetchPayments, createPayment, updatePayment)
 *   - Activate/deactivate support
 *
 * Debts have a debt_nature (MONEY_BORROWED / MONEY_LENT), debt_type,
 * entity_name, principal_amount, remaining_balance, interest_rate,
 * monthly_payment, and term_months.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  DebtFacilityOut,
  DebtFacilityCreate,
  DebtFacilityUpdate,
  DebtFacilityFilter,
  DebtFacilityListOut,
  DebtSummary,
  DebtPaymentOut,
  DebtPaymentUpdate,
  MessageOut,
} from "@/lib/ledgerTypes";

export const useDebtStore = defineStore("debt", {
  state: () => ({
    ...crudState<DebtFacilityOut, DebtFacilityFilter, DebtFacilityListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    summary: null as DebtSummary | null,
    summaryLoaded: false,
    payments: [] as DebtPaymentOut[],
    paymentsLoaded: false,
  }),

  getters: {
    ...crudGetters<DebtFacilityOut>(),

    /** Debts where user owes money (MONEY_BORROWED) */
    borrowedDebts: (state) => state.items.filter((d) => d.debt_nature === "MONEY_BORROWED"),

    /** Debts where money is owed to user (MONEY_LENT) */
    lentDebts: (state) => state.items.filter((d) => d.debt_nature === "MONEY_LENT"),

    /** Total principal borrowed */
    totalBorrowed: (state) =>
      state.items
        .filter((d) => d.debt_nature === "MONEY_BORROWED" && d.is_active)
        .reduce((sum, d) => sum + parseFloat(d.principal_amount || "0"), 0),

    /** Total principal lent */
    totalLent: (state) =>
      state.items
        .filter((d) => d.debt_nature === "MONEY_LENT" && d.is_active)
        .reduce((sum, d) => sum + parseFloat(d.principal_amount || "0"), 0),

    /** Total remaining balance on borrowed debts */
    totalRemainingBorrowed: (state) =>
      state.items
        .filter((d) => d.debt_nature === "MONEY_BORROWED" && d.is_active)
        .reduce((sum, d) => sum + parseFloat(d.remaining_balance || "0"), 0),

    /** Total remaining balance on lent debts */
    totalRemainingLent: (state) =>
      state.items
        .filter((d) => d.debt_nature === "MONEY_LENT" && d.is_active)
        .reduce((sum, d) => sum + parseFloat(d.remaining_balance || "0"), 0),

    /** Net position: lent - borrowed (positive = net owed to user) */
    netPosition(): number {
      return this.totalRemainingLent - this.totalRemainingBorrowed;
    },
  },

  actions: {
    ...crudActions<
      DebtFacilityOut,
      DebtFacilityCreate,
      DebtFacilityUpdate,
      DebtFacilityFilter,
      DebtFacilityListOut
    >({
      storeId: "debt",
      api: {
        list: ledgerApi.debts.list,
        get: ledgerApi.debts.get,
        create: ledgerApi.debts.create,
        update: ledgerApi.debts.update,
        remove: ledgerApi.debts.remove,
        restore: ledgerApi.debts.restore,
        activate: ledgerApi.debts.activate,
        deactivate: ledgerApi.debts.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Debt Summary ──

    async fetchSummary(forceRefresh = false): Promise<DebtSummary | null> {
      if (this.summaryLoaded && !forceRefresh) {
        return this.summary;
      }
      this.loadingAction = "fetchSummary";
      this.error = null;
      try {
        const data = await ledgerApi.debts.summary();
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

    // ── Debt Payments ──

    async fetchPayments(debtId: number): Promise<DebtPaymentOut[]> {
      this.loadingAction = "fetchPayments";
      this.error = null;
      try {
        const data = await ledgerApi.debtPayments.list(debtId);
        this.payments = data;
        this.paymentsLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    async createPayment(
      debtId: number,
      data: Omit<import("@/lib/ledgerTypes").DebtPaymentCreate, "debt_id">,
    ): Promise<DebtPaymentOut | null> {
      this.loadingAction = "createPayment";
      this.error = null;
      try {
        const result = await ledgerApi.debtPayments.create(debtId, data);
        this.payments.push(result);
        // Refresh the debt to get updated remaining_balance & progress_percent
        await this.fetchOne(debtId);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async updatePayment(
      debtId: number,
      paymentId: number,
      data: DebtPaymentUpdate,
    ): Promise<DebtPaymentOut | null> {
      this.loadingAction = "updatePayment";
      this.error = null;
      try {
        const result = await ledgerApi.debtPayments.update(debtId, paymentId, data);
        const idx = this.payments.findIndex((p) => p.id === paymentId);
        if (idx !== -1) {
          this.payments[idx] = result;
        }
        // Refresh the debt to get updated remaining_balance
        await this.fetchOne(debtId);
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
      this.payments = [];
      this.paymentsLoaded = false;
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
