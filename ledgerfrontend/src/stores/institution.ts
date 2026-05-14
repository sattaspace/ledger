/**
 * Institution Store — Pinia CRUD store for Institution entities.
 *
 * Uses defineCrudStore for standard CRUD + soft-delete + activate/deactivate.
 * No domain-specific extra state or actions needed.
 */

import { defineCrudStore } from "./base";
import { ledgerApi } from "@/lib/ledgerApi";
import type {
  InstitutionOut,
  InstitutionCreate,
  InstitutionUpdate,
  InstitutionFilter,
  InstitutionListOut,
} from "@/lib/ledgerTypes";

export const useInstitutionStore = defineCrudStore<
  InstitutionOut,
  InstitutionCreate,
  InstitutionUpdate,
  InstitutionFilter,
  InstitutionListOut
>({
  storeId: "institution",
  api: {
    list: ledgerApi.institutions.list,
    get: ledgerApi.institutions.get,
    create: ledgerApi.institutions.create,
    update: ledgerApi.institutions.update,
    remove: ledgerApi.institutions.remove,
    restore: ledgerApi.institutions.restore,
    dropdown: ledgerApi.institutions.dropdown,
    activate: ledgerApi.institutions.activate,
    deactivate: ledgerApi.institutions.deactivate,
  },
  defaultFilters: { limit: 25, offset: 0 },
});
