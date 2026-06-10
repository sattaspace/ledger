/**
 * Bill Store — Pinia CRUD store for Bill entities.
 *
 * Extends standard CRUD with:
 *   - upcoming[] — cached upcoming bills for dashboard widget
 *   - payments[] — payments for the currently viewed bill
 *   - generateTransaction() — create a transaction from a bill
 *   - pause/cancel/reactivate — bill lifecycle actions
 *   - Payment CRUD (fetchPayments, createPayment, updatePayment)
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  BillOut,
  BillCreate,
  BillUpdate,
  BillFilter,
  BillListOut,
  BillGenerateTransactionOut,
  BillPaymentOut,
  BillPaymentUpdate,
  MessageOut,
} from "@/lib/ledgerTypes";

export const useBillStore = defineStore("bill", {
  state: () => ({
    ...crudState<BillOut, BillFilter, BillListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    upcoming: [] as BillListOut[],
    upcomingLoaded: false,
    payments: [] as BillPaymentOut[],
    paymentsLoaded: false,
  }),

  getters: {
    ...crudGetters<BillOut>(),

    /** Bills filtered to ACTIVE status */
    activeBills: (state) => state.items.filter((b) => b.status === "ACTIVE"),

    /** Bills filtered to PAUSED status */
    pausedBills: (state) => state.items.filter((b) => b.status === "PAUSED"),

    /** Bills filtered to CANCELLED status */
    cancelledBills: (state) => state.items.filter((b) => b.status === "CANCELLED"),

    /** Bills that are overdue (next_due_date is in the past and status is ACTIVE) */
    overdueBills: (state) => {
      const now = new Date().toISOString().split("T")[0];
      return state.items.filter((b) => b.status === "ACTIVE" && b.next_due_date < now);
    },
  },

  actions: {
    ...crudActions<BillOut, BillCreate, BillUpdate, BillFilter, BillListOut>({
      storeId: "bill",
      api: {
        list: ledgerApi.bills.list,
        get: ledgerApi.bills.get,
        create: ledgerApi.bills.create,
        update: ledgerApi.bills.update,
        remove: ledgerApi.bills.remove,
        restore: ledgerApi.bills.restore,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Upcoming Bills (Dashboard) ──

    async fetchUpcoming(forceRefresh = false, days = 30): Promise<BillListOut[]> {
      if (this.upcomingLoaded && !forceRefresh) {
        return this.upcoming;
      }
      this.loadingAction = "fetchUpcoming";
      this.error = null;
      try {
        const data = await ledgerApi.bills.upcoming(days);
        this.upcoming = data;
        this.upcomingLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Bill Lifecycle Actions ──

    async generateTransaction(id: number): Promise<BillGenerateTransactionOut | null> {
      this.loadingAction = "generateTransaction";
      this.error = null;
      try {
        const result = await ledgerApi.bills.generateTransaction(id);
        // Refresh the bill to get updated next_due_date
        await this.fetchOne(id);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async pause(id: number): Promise<MessageOut | null> {
      this.loadingAction = "pause";
      this.error = null;
      try {
        const result = await ledgerApi.bills.pause(id);
        // Optimistic update: set status to PAUSED
        const idx = this.items.findIndex((b) => b.id === id);
        if (idx !== -1) {
          this.items[idx] = { ...this.items[idx], status: "PAUSED" };
        }
        if (this.current?.id === id) {
          this.current = { ...this.current, status: "PAUSED" };
        }
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        // Rollback: re-fetch the bill
        await this.fetchOne(id);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async cancel(id: number): Promise<MessageOut | null> {
      this.loadingAction = "cancel";
      this.error = null;
      try {
        const result = await ledgerApi.bills.cancel(id);
        // Optimistic update: set status to CANCELLED
        const idx = this.items.findIndex((b) => b.id === id);
        if (idx !== -1) {
          this.items[idx] = { ...this.items[idx], status: "CANCELLED" };
        }
        if (this.current?.id === id) {
          this.current = { ...this.current, status: "CANCELLED" };
        }
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        await this.fetchOne(id);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async reactivate(id: number): Promise<MessageOut | null> {
      this.loadingAction = "reactivate";
      this.error = null;
      try {
        const result = await ledgerApi.bills.reactivate(id);
        // Optimistic update: set status to ACTIVE
        const idx = this.items.findIndex((b) => b.id === id);
        if (idx !== -1) {
          this.items[idx] = { ...this.items[idx], status: "ACTIVE" };
        }
        if (this.current?.id === id) {
          this.current = { ...this.current, status: "ACTIVE" };
        }
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        await this.fetchOne(id);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Bill Payments ──

    async fetchPayments(billId: number): Promise<BillPaymentOut[]> {
      this.loadingAction = "fetchPayments";
      this.error = null;
      try {
        const data = await ledgerApi.billPayments.list(billId);
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
      billId: number,
      data: Omit<import("@/lib/ledgerTypes").BillPaymentCreate, "bill_id">,
    ): Promise<BillPaymentOut | null> {
      this.loadingAction = "createPayment";
      this.error = null;
      try {
        const result = await ledgerApi.billPayments.create(billId, data);
        this.payments.push(result);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async updatePayment(
      billId: number,
      paymentId: number,
      data: BillPaymentUpdate,
    ): Promise<BillPaymentOut | null> {
      this.loadingAction = "updatePayment";
      this.error = null;
      try {
        const result = await ledgerApi.billPayments.update(billId, paymentId, data);
        const idx = this.payments.findIndex((p) => p.id === paymentId);
        if (idx !== -1) {
          this.payments[idx] = result;
        }
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
      this.upcoming = [];
      this.upcomingLoaded = false;
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
