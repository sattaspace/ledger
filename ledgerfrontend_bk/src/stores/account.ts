/**
 * Account Store — Pinia CRUD store for Account entities.
 *
 * Extends the standard CRUD pattern with:
 *   - recalculateBalance() — recalculate balance from transactions
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  AccountOut,
  AccountCreate,
  AccountUpdate,
  AccountFilter,
  AccountListOut,
  BalanceRecalculateOut,
} from "@/lib/ledgerTypes";

export const useAccountStore = defineStore("account", {
  state: () => ({
    ...crudState<AccountOut, AccountFilter, AccountListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    /** Result of the last recalculate-balance call. */
    balanceRecalcResult: null as BalanceRecalculateOut | null,
  }),

  getters: {
    ...crudGetters<AccountOut>(),
    // ── Domain-specific extra getters ──
    /** Accounts grouped by institution_id for card grid display. */
    groupedByInstitution: (state) => {
      const groups: Record<number, AccountOut[]> = {};
      for (const account of state.items) {
        const key = account.institution_id;
        if (!groups[key]) groups[key] = [];
        groups[key].push(account);
      }
      return groups;
    },
    /** Total balance across all accounts (sum of current_balance as float). */
    totalBalance: (state) => {
      return state.items.reduce((sum, a) => sum + parseFloat(a.current_balance || "0"), 0);
    },
    /** Asset accounts only. */
    assetAccounts: (state) => state.items.filter((a) => a.account_type === "ASSET"),
    /** Liability accounts only. */
    liabilityAccounts: (state) => state.items.filter((a) => a.account_type === "LIABILITY"),
    /** Investment accounts only. */
    investmentAccounts: (state) => state.items.filter((a) => a.account_type === "INVESTMENT"),
  },

  actions: {
    ...crudActions<AccountOut, AccountCreate, AccountUpdate, AccountFilter, AccountListOut>({
      storeId: "account",
      api: {
        list: ledgerApi.accounts.list,
        get: ledgerApi.accounts.get,
        create: ledgerApi.accounts.create,
        update: ledgerApi.accounts.update,
        remove: ledgerApi.accounts.remove,
        restore: ledgerApi.accounts.restore,
        dropdown: ledgerApi.accounts.dropdown,
        activate: ledgerApi.accounts.activate,
        deactivate: ledgerApi.accounts.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Domain-specific extra actions ──

    /**
     * Recalculate account balance from transactions.
     * Useful when the cached balance may be out of sync.
     */
    async recalculateBalance(id: number): Promise<BalanceRecalculateOut | null> {
      this.loadingAction = "recalculateBalance";
      this.error = null;

      try {
        const result = await ledgerApi.accounts.recalculateBalance(id);
        this.balanceRecalcResult = result;

        // Update the account in the items list if present
        const idx = this.items.findIndex((a: AccountOut) => a.id === id);
        if (idx !== -1) {
          // Refetch the single account to get the updated balance
          const updated = await ledgerApi.accounts.get(id);
          this.items[idx] = updated;
          if (this.current?.id === id) {
            this.current = updated;
          }
        }

        return result;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return null;
      } finally {
        this.loadingAction = "";
      }
    },
  },
});
