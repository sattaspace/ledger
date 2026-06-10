/**
 * Transaction Store — Pinia CRUD store for Transaction entities.
 *
 * The heaviest store in Phase 1. Extends standard CRUD with:
 *   - recent[] — cached recent transactions for dashboard
 *   - splits[] — splits for the current transaction
 *   - tags[] — tags for the current transaction
 *   - createTransfer() — internal transfer between accounts
 *   - Split CRUD (fetchSplits, createSplit, updateSplit, deleteSplit)
 *   - Tag management (fetchTags, addTag, bulkSetTags, removeTag)
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  TransactionOut,
  TransactionCreate,
  TransactionUpdate,
  TransactionFilter,
  TransactionListOut,
  TransferCreate,
  TransferOut,
  TransactionSplitOut,
  TransactionSplitCreate,
  TransactionSplitUpdate,
  TransactionTagOut,
  TransactionTagBulkOut,
  MessageOut,
} from "@/lib/ledgerTypes";

export const useTransactionStore = defineStore("transaction", {
  state: () => ({
    ...crudState<TransactionOut, TransactionFilter, TransactionListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    /** Recent transactions for dashboard widget. */
    recent: [] as TransactionListOut[],
    /** Whether recent transactions have been loaded. */
    recentLoaded: false,
    /** Splits for the currently viewed transaction. */
    splits: [] as TransactionSplitOut[],
    /** Tags for the currently viewed transaction. */
    tags: [] as TransactionTagOut[],
  }),

  getters: {
    ...crudGetters<TransactionOut>(),
    // ── Domain-specific extra getters ──
    /** Income transactions only. */
    incomeTransactions: (state) => state.items.filter((t) => t.transaction_type === "INCOME"),
    /** Expense transactions only. */
    expenseTransactions: (state) => state.items.filter((t) => t.transaction_type === "EXPENSE"),
    /** Transfer transactions only. */
    transferTransactions: (state) => state.items.filter((t) => t.transaction_type === "TRANSFER"),
    /** Whether the current transaction has splits. */
    currentHasSplits: (state) => state.splits.length > 0,
    /** Total amount from splits (should match transaction amount). */
    splitsTotal: (state) => state.splits.reduce((sum, s) => sum + parseFloat(s.amount || "0"), 0),
  },

  actions: {
    ...crudActions<
      TransactionOut,
      TransactionCreate,
      TransactionUpdate,
      TransactionFilter,
      TransactionListOut
    >({
      storeId: "transaction",
      api: {
        list: ledgerApi.transactions.list,
        get: ledgerApi.transactions.get,
        create: ledgerApi.transactions.create,
        update: ledgerApi.transactions.update,
        remove: ledgerApi.transactions.remove,
        restore: ledgerApi.transactions.restore,
        // No dropdown for transactions
        // No activate/deactivate for transactions
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Recent Transactions ────────────────────────────────────────────

    /**
     * Fetch recent transactions for the dashboard widget.
     * Cached — subsequent calls return cached data unless forceRefresh.
     */
    async fetchRecent(forceRefresh = false, limit = 10): Promise<TransactionListOut[]> {
      if (this.recentLoaded && !forceRefresh) {
        return this.recent;
      }

      this.loadingAction = "fetchRecent";
      this.error = null;

      try {
        const data = await ledgerApi.transactions.recent(limit);
        this.recent = data;
        this.recentLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Transfer ───────────────────────────────────────────────────────

    /**
     * Create an internal transfer between two accounts.
     * This creates two linked transactions (outflow + inflow).
     */
    async createTransfer(data: TransferCreate): Promise<TransferOut | null> {
      this.loading = true;
      this.loadingAction = "createTransfer";
      this.error = null;
      this.fieldErrors = {};

      try {
        const result = await ledgerApi.transactions.createTransfer(data);
        // Invalidate the list since we added new transactions
        this.invalidate();
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        this.fieldErrors = extractErrorMessage(err) ? {} : (err as Record<string, string[]>);
        throw err;
      } finally {
        this.loading = false;
        this.loadingAction = "";
      }
    },

    // ── Transaction Splits ─────────────────────────────────────────────

    /** Fetch splits for a specific transaction. */
    async fetchSplits(transactionId: number): Promise<TransactionSplitOut[]> {
      this.loadingAction = "fetchSplits";
      this.error = null;

      try {
        const data = await ledgerApi.splits.list(transactionId);
        this.splits = data;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    /** Create a split for a transaction. */
    async createSplit(
      transactionId: number,
      data: Omit<TransactionSplitCreate, "transaction_id">,
    ): Promise<TransactionSplitOut | null> {
      this.loadingAction = "createSplit";
      this.error = null;

      try {
        const result = await ledgerApi.splits.create(transactionId, data);
        this.splits.push(result);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    /** Update an existing split. */
    async updateSplit(
      transactionId: number,
      splitId: number,
      data: TransactionSplitUpdate,
    ): Promise<TransactionSplitOut | null> {
      this.loadingAction = "updateSplit";
      this.error = null;

      try {
        const result = await ledgerApi.splits.update(transactionId, splitId, data);
        // Update in splits list
        const idx = this.splits.findIndex((s) => s.id === splitId);
        if (idx !== -1) {
          this.splits[idx] = result;
        }
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    /** Delete a split from a transaction. */
    async deleteSplit(transactionId: number, splitId: number): Promise<MessageOut | null> {
      this.loadingAction = "deleteSplit";
      this.error = null;

      try {
        const result = await ledgerApi.splits.remove(transactionId, splitId);
        this.splits = this.splits.filter((s) => s.id !== splitId);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    // ── Transaction Tags ───────────────────────────────────────────────

    /** Fetch tags for a specific transaction. */
    async fetchTags(transactionId: number): Promise<TransactionTagOut[]> {
      this.loadingAction = "fetchTags";
      this.error = null;

      try {
        const data = await ledgerApi.transactionTags.list(transactionId);
        this.tags = data;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    /** Attach a tag to a transaction. */
    async addTag(transactionId: number, tagId: number): Promise<TransactionTagOut | null> {
      this.loadingAction = "addTag";
      this.error = null;

      try {
        const result = await ledgerApi.transactionTags.attach(transactionId, {
          tag_id: tagId,
        });
        this.tags.push(result);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    /** Replace all tags on a transaction with the provided tag IDs. */
    async bulkSetTags(
      transactionId: number,
      tagIds: number[],
    ): Promise<TransactionTagBulkOut | null> {
      this.loadingAction = "bulkSetTags";
      this.error = null;

      try {
        const result = await ledgerApi.transactionTags.bulkSet(transactionId, {
          tag_ids: tagIds,
        });
        // Refresh tags after bulk set
        await this.fetchTags(transactionId);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },

    /** Detach a tag from a transaction. */
    async removeTag(transactionId: number, tagId: number): Promise<MessageOut | null> {
      this.loadingAction = "removeTag";
      this.error = null;

      try {
        const result = await ledgerApi.transactionTags.detach(transactionId, tagId);
        this.tags = this.tags.filter((t) => t.tag_id !== tagId);
        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        throw err;
      } finally {
        this.loadingAction = "";
      }
    },
  },
});
