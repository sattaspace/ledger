/**
 * Tag Store — Pinia CRUD store for Tag entities.
 *
 * Uses defineCrudStore for standard CRUD + soft-delete.
 * Tags do NOT support activate/deactivate.
 */

import { defineCrudStore } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type { TagOut, TagCreate, TagUpdate, TagFilter, TagListOut } from "@/lib/ledgerTypes";

export const useTagStore = defineCrudStore<TagOut, TagCreate, TagUpdate, TagFilter, TagListOut>({
  storeId: "tag",
  api: {
    list: ledgerApi.tags.list,
    get: ledgerApi.tags.get,
    create: ledgerApi.tags.create,
    update: ledgerApi.tags.update,
    remove: ledgerApi.tags.remove,
    restore: ledgerApi.tags.restore,
    dropdown: ledgerApi.tags.dropdown,
    // No activate/deactivate for tags
  },
  defaultFilters: { limit: 25, offset: 0 },
});
