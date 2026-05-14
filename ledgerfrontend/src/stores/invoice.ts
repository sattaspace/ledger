/**
 * Invoice Store — Pinia CRUD store for Invoice entities.
 *
 * Extends standard CRUD with:
 *   - overdue — cached list of overdue invoices
 *   - markPaid — mark an invoice as paid (with optional transaction creation)
 *   - lineItems[] — line items for the currently viewed invoice
 *   - Line Item CRUD (fetchLineItems, createLineItem, updateLineItem, deleteLineItem)
 *   - Soft delete/restore (no activate/deactivate on invoices)
 *
 * Invoices have a status lifecycle: DRAFT → SENT → VIEWED → PARTIAL/PAID
 * and can be OVERDUE or CANCELLED. Each invoice has LineItems with
 * description, quantity, unit_price, and auto-calculated total.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  InvoiceOut,
  InvoiceCreate,
  InvoiceUpdate,
  InvoiceFilter,
  InvoiceListOut,
  InvoiceMarkPaid,
  InvoiceLineItemOut,
  InvoiceLineItemCreate,
  InvoiceLineItemUpdate,
  MessageOut,
} from "@/lib/ledgerTypes";

export const useInvoiceStore = defineStore("invoice", {
  state: () => ({
    ...crudState<InvoiceOut, InvoiceFilter, InvoiceListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    overdue: [] as InvoiceListOut[],
    overdueLoaded: false,
    lineItems: [] as InvoiceLineItemOut[],
    lineItemsLoaded: false,
  }),

  getters: {
    ...crudGetters<InvoiceOut>(),

    /** Invoices that are not deleted, grouped by status */
    byStatus(): Record<string, InvoiceOut[]> {
      const map: Record<string, InvoiceOut[]> = {};
      for (const inv of this.items) {
        if (inv.is_deleted) continue;
        const s = inv.status || "DRAFT";
        if (!map[s]) map[s] = [];
        map[s].push(inv);
      }
      return map;
    },

    /** Total amount due across all active non-deleted invoices */
    totalDue: (state) =>
      state.items
        .filter((inv) => !inv.is_deleted && inv.status !== "PAID" && inv.status !== "CANCELLED")
        .reduce((sum, inv) => sum + parseFloat(inv.amount_due || "0"), 0),

    /** Total amount paid across all invoices */
    totalPaid: (state) =>
      state.items
        .filter((inv) => !inv.is_deleted)
        .reduce((sum, inv) => sum + parseFloat(inv.amount_paid || "0"), 0),

    /** Count of overdue invoices */
    overdueCount: (state) => state.items.filter((inv) => !inv.is_deleted && inv.is_overdue).length,
  },

  actions: {
    ...crudActions<InvoiceOut, InvoiceCreate, InvoiceUpdate, InvoiceFilter, InvoiceListOut>({
      storeId: "invoice",
      api: {
        list: ledgerApi.invoices.list,
        get: ledgerApi.invoices.get,
        create: ledgerApi.invoices.create,
        update: ledgerApi.invoices.update,
        remove: ledgerApi.invoices.remove,
        restore: ledgerApi.invoices.restore,
        // Invoices don't have activate/deactivate endpoints
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Overdue Invoices ──

    async fetchOverdue(forceRefresh = false): Promise<InvoiceListOut[]> {
      if (this.overdueLoaded && !forceRefresh) {
        return this.overdue;
      }
      this.loadingAction = "fetchOverdue";
      this.error = null;
      try {
        const data = await ledgerApi.invoices.overdue();
        this.overdue = data;
        this.overdueLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Mark Paid ──

    async markPaid(invoiceId: number, data: InvoiceMarkPaid): Promise<InvoiceOut | null> {
      this.loadingAction = "markPaid";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.invoices.markPaid(invoiceId, data);
        // Update in local items array
        const idx = this.items.findIndex((inv) => inv.id === invoiceId);
        if (idx !== -1) {
          this.items[idx] = result;
        }
        if (this.current?.id === invoiceId) {
          this.current = result;
        }
        // Invalidate overdue cache
        this.overdueLoaded = false;
        this.fetchOverdue(true);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Line Items ──

    async fetchLineItems(invoiceId: number): Promise<InvoiceLineItemOut[]> {
      this.loadingAction = "fetchLineItems";
      this.error = null;
      try {
        const data = await ledgerApi.invoiceLineItems.list(invoiceId);
        this.lineItems = data;
        this.lineItemsLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    async createLineItem(
      invoiceId: number,
      data: Omit<InvoiceLineItemCreate, "invoice_id">,
    ): Promise<InvoiceLineItemOut | null> {
      this.loadingAction = "createLineItem";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.invoiceLineItems.create(invoiceId, data);
        this.lineItems.push(result);
        // Refresh the invoice to get updated totals
        await this.fetchOne(invoiceId);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async updateLineItem(
      invoiceId: number,
      itemId: number,
      data: InvoiceLineItemUpdate,
    ): Promise<InvoiceLineItemOut | null> {
      this.loadingAction = "updateLineItem";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.invoiceLineItems.update(invoiceId, itemId, data);
        const idx = this.lineItems.findIndex((li) => li.id === itemId);
        if (idx !== -1) {
          this.lineItems[idx] = result;
        }
        // Refresh the invoice to get updated totals
        await this.fetchOne(invoiceId);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    async deleteLineItem(invoiceId: number, itemId: number): Promise<MessageOut | null> {
      this.loadingAction = "deleteLineItem";
      this.error = null;
      try {
        const result = await ledgerApi.invoiceLineItems.remove(invoiceId, itemId);
        this.lineItems = this.lineItems.filter((li) => li.id !== itemId);
        // Refresh the invoice to get updated totals
        await this.fetchOne(invoiceId);
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
      this.overdue = [];
      this.overdueLoaded = false;
      this.lineItems = [];
      this.lineItemsLoaded = false;
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
