/**
 * Reusable Vue Components — barrel export.
 *
 * Import all shared components from this single entry point:
 *
 *   import { DataTable, Modal, StatusBadge } from "@/components/vue";
 */

// ─── Data Display ─────────────────────────────────────────────────────────────
export { default as DataTable } from "./DataTable.vue";
export type { DataTableColumn, SortDirection, SortChangePayload } from "./DataTable.vue";

export { default as StatusBadge } from "./StatusBadge.vue";
export type { StatusColorMap } from "./StatusBadge.vue";

export { default as TypeBadge } from "./TypeBadge.vue";
export type { TypeStyleMap } from "./TypeBadge.vue";

export { default as ProgressBar } from "./ProgressBar.vue";

export { default as EmptyState } from "./EmptyState.vue";

export { default as TagChips } from "./TagChips.vue";
export type { TagItem } from "./TagChips.vue";

export { default as LoadingSkeleton } from "./LoadingSkeleton.vue";

// ─── Overlays & Dialogs ───────────────────────────────────────────────────────
export { default as Modal } from "./Modal.vue";

export { default as ConfirmDialog } from "./ConfirmDialog.vue";

export { default as ToastContainer } from "./ToastContainer.vue";

// ─── Form Controls ────────────────────────────────────────────────────────────
export { default as SearchInput } from "./SearchInput.vue";

export { default as FilterBar } from "./FilterBar.vue";
export type { FilterOption, FilterConfig } from "./FilterBar.vue";

export { default as CurrencyInput } from "./CurrencyInput.vue";
export type { CurrencyInputValue } from "./CurrencyInput.vue";

export { default as DateRangePicker } from "./DateRangePicker.vue";
export type { DateRange, DatePreset } from "./DateRangePicker.vue";

export { default as CategoryTreeSelect } from "./CategoryTreeSelect.vue";
export type { TreeNode } from "./CategoryTreeSelect.vue";

export { default as FormErrors } from "./FormErrors.vue";

// ─── Feature Gating ───────────────────────────────────────────────────────────
export { default as FeatureGate } from "./FeatureGate.vue";

export { default as UpgradePrompt } from "./UpgradePrompt.vue";

// ─── Plan Limits ────────────────────────────────────────────────────────────
export { default as PlanLimitBadge } from "./PlanLimitBadge.vue";
