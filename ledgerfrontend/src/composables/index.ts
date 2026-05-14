/**
 * Vue Composables — barrel export for all shared composables.
 *
 * Composables extract duplicated patterns from Vue components into
 * reusable, reactive functions. This reduces code duplication,
 * improves maintainability, and provides shared state across components.
 *
 * Available composables:
 *
 *   ── Sattabase Core (existing) ──────────────────────────────────────────
 *   useAuth()               — Shared auth + billing state (user, subscription, access, error, refetch)
 *   useSubscription()       — Shared subscription list state (deduplicates concurrent fetches)
 *   useAccess()             — Reactive feature-access checking (hasAccess, getAccess, accessKeys)
 *   useBillingRedirect()    — Detect billing return from Sattabase (triggers useAuth refetch)
 *
 *   ── Ledger Domain (new) ────────────────────────────────────────────────
 *   useLedgerPagination()   — Offset/limit pagination state + helpers for DataTable
 *   useLedgerFilters()      — Filter state management + URL query param sync
 *   useCrudForm()           — Create/edit form lifecycle (load, validate, submit, redirect)
 *   useSoftDelete()         — Delete + restore confirmation flow
 *   useActivator()          — Activate/deactivate toggle with confirmation
 *   useDropdownLoader()     — Lazy-load dropdown data from multiple stores with caching
 */

// ─── Sattabase Core ───────────────────────────────────────────────────────────

export { useAuth } from "./useAuth";
export { useSubscription } from "./useSubscription";
export { useAccess } from "./useAccess";
export { useBillingRedirect } from "./useBillingRedirect";

// ─── Ledger Domain ────────────────────────────────────────────────────────────

export { useLedgerPagination } from "./useLedgerPagination";
export type { LedgerPagination, PAGE_SIZE_OPTIONS } from "./useLedgerPagination";

export { useLedgerFilters } from "./useLedgerFilters";
export type { UseLedgerFiltersConfig, LedgerFilters } from "./useLedgerFilters";

export { useCrudForm } from "./useCrudForm";
export type { FormMode, UseCrudFormConfig, CrudForm } from "./useCrudForm";

export { useSoftDelete } from "./useSoftDelete";
export type { SoftDeleteAction, UseSoftDeleteConfig, SoftDeleteHandler } from "./useSoftDelete";

export { useActivator } from "./useActivator";
export type { ActivatorAction, UseActivatorConfig, ActivatorHandler } from "./useActivator";

export { useDropdownLoader } from "./useDropdownLoader";
export type { UseDropdownLoaderConfig, DropdownLoader } from "./useDropdownLoader";

export { useToast } from "./useToast";
export type { ToastComposable, Toast, ToastVariant, ToastOptions } from "./useToast";

export { useHotkeys } from "./useHotkeys";
export type { HotkeysComposable } from "./useHotkeys";
