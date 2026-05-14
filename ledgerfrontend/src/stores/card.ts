/**
 * Card Store — Pinia CRUD store for Card entities.
 *
 * Extends standard CRUD with:
 *   - Dropdown support for card selection (e.g. in Transaction form)
 *   - Activate/deactivate support for card status toggling
 *
 * Cards are linked to Accounts and have a card_type (DEBIT/CREDIT),
 * last_four digits, expiry_date, annual_fee, and a color strip.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type { CardOut, CardCreate, CardUpdate, CardFilter, CardListOut } from "@/lib/ledgerTypes";

export const useCardStore = defineStore("card", {
  state: () => ({
    ...crudState<CardOut, CardFilter, CardListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
  }),

  getters: {
    ...crudGetters<CardOut>(),

    /** Cards filtered to CREDIT type */
    creditCards: (state) => state.items.filter((c) => c.card_type === "CREDIT"),

    /** Cards filtered to DEBIT type */
    debitCards: (state) => state.items.filter((c) => c.card_type === "DEBIT"),

    /** Cards that are expiring within the next 90 days */
    expiringCards: (state) => {
      const now = new Date();
      const threshold = new Date();
      threshold.setDate(threshold.getDate() + 90);
      return state.items.filter((c) => {
        if (!c.expiry_date) return false;
        const expiry = new Date(c.expiry_date);
        return expiry >= now && expiry <= threshold;
      });
    },
  },

  actions: {
    ...crudActions<CardOut, CardCreate, CardUpdate, CardFilter, CardListOut>({
      storeId: "card",
      api: {
        list: ledgerApi.cards.list,
        get: ledgerApi.cards.get,
        create: ledgerApi.cards.create,
        update: ledgerApi.cards.update,
        remove: ledgerApi.cards.remove,
        restore: ledgerApi.cards.restore,
        dropdown: ledgerApi.cards.dropdown,
        activate: ledgerApi.cards.activate,
        deactivate: ledgerApi.cards.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Reset ──

    /** Reset all state */
    $resetCrud() {
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
