/**
 * Category Store — Pinia CRUD store for Category entities.
 *
 * Extends the standard CRUD pattern with:
 *   - tree[] — cached category tree for hierarchical display
 *   - fetchTree() — load the tree structure
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  CategoryOut,
  CategoryCreate,
  CategoryUpdate,
  CategoryFilter,
  CategoryListOut,
  CategoryTreeOut,
} from "@/lib/ledgerTypes";

export const useCategoryStore = defineStore("category", {
  state: () => ({
    ...crudState<CategoryOut, CategoryFilter, CategoryListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    /** Cached category tree (hierarchical). */
    tree: [] as CategoryTreeOut[],
    /** Whether the tree has been loaded. */
    treeLoaded: false,
  }),

  getters: {
    ...crudGetters<CategoryOut>(),
    // ── Domain-specific extra getters ──
    /** Top-level categories (no parent). */
    rootCategories: (state) => state.items.filter((c) => c.parent_id === null),
    /** Income categories only. */
    incomeCategories: (state) => state.items.filter((c) => c.is_income === true),
    /** Expense categories only. */
    expenseCategories: (state) => state.items.filter((c) => c.is_income === false),
  },

  actions: {
    ...crudActions<CategoryOut, CategoryCreate, CategoryUpdate, CategoryFilter, CategoryListOut>({
      storeId: "category",
      api: {
        list: ledgerApi.categories.list,
        get: ledgerApi.categories.get,
        create: ledgerApi.categories.create,
        update: ledgerApi.categories.update,
        remove: ledgerApi.categories.remove,
        restore: ledgerApi.categories.restore,
        dropdown: ledgerApi.categories.dropdown,
        activate: ledgerApi.categories.activate,
        deactivate: ledgerApi.categories.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Domain-specific extra actions ──

    /**
     * Fetch the category tree structure for hierarchical display.
     * Cached — subsequent calls return cached data unless forceRefresh.
     */
    async fetchTree(forceRefresh = false): Promise<CategoryTreeOut[]> {
      if (this.treeLoaded && !forceRefresh) {
        return this.tree;
      }

      this.loadingAction = "fetchTree";
      this.error = null;

      try {
        const data = await ledgerApi.categories.tree();
        this.tree = data;
        this.treeLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },
  },
});
