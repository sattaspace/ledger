/**
 * Vault Store — Pinia CRUD store for DocumentVault entities.
 *
 * Extends standard CRUD with:
 *   - expiring — cached list of documents expiring within N days
 *   - uploadFile — multipart form data upload (primary creation method)
 *   - Soft delete/restore + activate/deactivate support
 *
 * DocumentVault stores file metadata (title, file_type, file_size,
 * expiry_date) with optional generic relation to other entities
 * (content_type_id + object_id). The actual file upload uses FormData.
 */

import { defineStore } from "pinia";
import { crudState, crudGetters, crudActions, extractErrorMessage } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  DocumentVaultOut,
  DocumentVaultCreate,
  DocumentVaultUpdate,
  DocumentVaultFilter,
  DocumentVaultListOut,
} from "@/lib/ledgerTypes";

export const useVaultStore = defineStore("vault", {
  state: () => ({
    ...crudState<DocumentVaultOut, DocumentVaultFilter, DocumentVaultListOut>({
      limit: 25,
      offset: 0,
    }),
    // ── Domain-specific extra state ──
    expiring: [] as DocumentVaultListOut[],
    expiringLoaded: false,
  }),

  getters: {
    ...crudGetters<DocumentVaultOut>(),

    /** Active, non-deleted documents */
    activeDocuments: (state) => state.items.filter((d) => d.is_active && !d.is_deleted),

    /** Documents grouped by file_type */
    byFileType(): Record<string, DocumentVaultOut[]> {
      const map: Record<string, DocumentVaultOut[]> = {};
      for (const d of this.items) {
        const t = d.file_type || "OTHER";
        if (!map[t]) map[t] = [];
        map[t].push(d);
      }
      return map;
    },

    /** Documents with expiry within 30 days */
    expiringSoon: (state) =>
      state.items.filter((d) => {
        if (!d.expiry_date || d.is_deleted) return false;
        const daysUntil = Math.ceil(
          (new Date(d.expiry_date).getTime() - Date.now()) / (1000 * 60 * 60 * 24),
        );
        return daysUntil >= 0 && daysUntil <= 30;
      }),

    /** Total file size across all active documents (bytes) */
    totalFileSize: (state) =>
      state.items.filter((d) => !d.is_deleted).reduce((sum, d) => sum + (d.file_size || 0), 0),
  },

  actions: {
    ...crudActions<
      DocumentVaultOut,
      DocumentVaultCreate,
      DocumentVaultUpdate,
      DocumentVaultFilter,
      DocumentVaultListOut
    >({
      storeId: "vault",
      api: {
        list: ledgerApi.vault.list,
        get: ledgerApi.vault.get,
        create: ledgerApi.vault.create,
        update: ledgerApi.vault.update,
        remove: ledgerApi.vault.remove,
        restore: ledgerApi.vault.restore,
        activate: ledgerApi.vault.activate,
        deactivate: ledgerApi.vault.deactivate,
      },
      defaultFilters: { limit: 25, offset: 0 },
    }),

    // ── Expiring Documents ──

    async fetchExpiring(days = 30, forceRefresh = false): Promise<DocumentVaultListOut[]> {
      if (this.expiringLoaded && !forceRefresh) {
        return this.expiring;
      }
      this.loadingAction = "fetchExpiring";
      this.error = null;
      try {
        const data = await ledgerApi.vault.expiring(days);
        this.expiring = data;
        this.expiringLoaded = true;
        return data;
      } catch (err: unknown) {
        this.error = extractErrorMessage(err);
        return [];
      } finally {
        this.loadingAction = "";
      }
    },

    // ── File Upload ──

    async uploadFile(formData: FormData): Promise<DocumentVaultOut | null> {
      this.loadingAction = "uploadFile";
      this.error = null;
      this.fieldErrors = {};
      try {
        const result = await ledgerApi.vault.uploadFile(formData);
        // Add to local items and refresh list
        this.items.unshift(result);
        this.total += 1;
        // Invalidate expiring cache
        this.expiringLoaded = false;
        this.fetchExpiring(30, true);
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
      this.expiring = [];
      this.expiringLoaded = false;
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
