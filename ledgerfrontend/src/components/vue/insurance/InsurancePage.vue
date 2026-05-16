<script setup lang="ts">
/**
 * InsurancePage — Card grid list page for InsurancePolicy entities.
 *
 * Features:
 *   - Summary bar: Total Monthly Premium, Active Policies, Upcoming Renewals
 *   - Policy cards in grid (2 cols on md): policy_name, insurance_type badge,
 *     provider, premium amount + frequency badge, renewal date (color-coded),
 *     coverage amount, deductible, days-to-renewal badge
 *   - SearchInput + FilterBar (insurance_type select, is_active toggle)
 *   - Create/Edit via InsurancePolicyForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Activate/Deactivate via ConfirmDialog + useActivator
 *   - Pagination via useLedgerPagination
 *   - EmptyState, LoadingSkeleton
 *
 * Registers as `LdgrInsurancePage` custom element.
 */

import { ref, computed, onMounted } from "vue";
import {
  Modal,
  ConfirmDialog,
  TypeBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  FormErrors,
  FeatureGate,
  UpgradePrompt,
  PlanLimitBadge,
} from "@/components/vue";
import type { FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useInsuranceStore } from "@/stores/insurance";
import { useVaultStore } from "@/stores/vault";
import type {
  InsurancePolicyOut,
  InsurancePolicyFilter,
  DocumentVaultCreate,
} from "@/lib/ledgerTypes";
import InsurancePolicyForm from "./InsurancePolicyForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrInsurancePage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useInsuranceStore();
const vaultStore = useVaultStore();

// ─── Document Linking ────────────────────────────────────────────────────────

const showLinkDocModal = ref(false);
const linkingPolicy = ref<InsurancePolicyOut | null>(null);
const linkDocLoading = ref(false);
const linkDocError = ref<string | null>(null);
const linkDocForm = ref({
  document_name: "",
  document_type: "INSURANCE_POLICY" as string,
  file_number: "",
  notes: "",
});

function openLinkDocModal(item: InsurancePolicyOut, event?: Event) {
  if (event) event.stopPropagation();
  linkingPolicy.value = item;
  linkDocForm.value = {
    document_name: `${item.policy_name} - Policy Document`,
    document_type: "INSURANCE_POLICY",
    file_number: "",
    notes: `Linked to insurance policy: ${item.policy_name}`,
  };
  linkDocError.value = null;
  showLinkDocModal.value = true;
}

function closeLinkDocModal() {
  showLinkDocModal.value = false;
  linkingPolicy.value = null;
}

async function handleLinkDoc() {
  if (!linkingPolicy.value) return;
  linkDocLoading.value = true;
  linkDocError.value = null;
  try {
    // Get content_type_id for insurance policy (typically set by backend ContentType)
    // We use the generic vault create with object_id pointing to the insurance policy
    const payload: DocumentVaultCreate = {
      document_name: linkDocForm.value.document_name,
      document_type: linkDocForm.value.document_type as DocumentVaultCreate['document_type'],
      file_number: linkDocForm.value.file_number || null,
      notes: linkDocForm.value.notes || null,
      content_type_id: null, // Backend resolves the content type
      object_id: linkingPolicy.value.id,
      issue_date: null,
      expiry_date: linkingPolicy.value.renewal_date || null,
    };
    await vaultStore.create(payload);
    closeLinkDocModal();
  } catch (err) {
    linkDocError.value = err instanceof Error ? err.message : "Failed to link document";
  } finally {
    linkDocLoading.value = false;
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string | number, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "$0.00";
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(num);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString();
}

function daysUntilRenewal(dateStr: string): number {
  const renewal = new Date(dateStr);
  const now = new Date();
  return Math.ceil((renewal.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
}

function getRenewalDateClass(dateStr: string): string {
  const days = daysUntilRenewal(dateStr);
  if (days < 0) return "text-red-600 dark:text-red-400";
  if (days <= 30) return "text-orange-600 dark:text-orange-400";
  if (days <= 60) return "text-amber-600 dark:text-amber-400";
  return "text-green-600 dark:text-green-400";
}

function getRenewalBorderColor(dateStr: string): string {
  const days = daysUntilRenewal(dateStr);
  if (days < 0) return "border-l-4 border-l-red-500";
  if (days <= 30) return "border-l-4 border-l-orange-500";
  if (days <= 60) return "border-l-4 border-l-amber-400";
  return "border-l-4 border-l-green-500";
}

function getDaysToRenewalLabel(dateStr: string): string {
  const days = daysUntilRenewal(dateStr);
  if (days < 0) return `${Math.abs(days)}d overdue`;
  if (days === 0) return "Due today";
  if (days === 1) return "1 day left";
  return `${days} days left`;
}

// ─── Type Maps ───────────────────────────────────────────────────────────────

const insuranceTypeMap = {
  HEALTH: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300" },
  AUTO: { bg: "bg-blue-100 dark:bg-blue-950/50", text: "text-blue-800 dark:text-blue-300" },
  HOME: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  LIFE: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  TRAVEL: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  BUSINESS: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  OTHER: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

const frequencyLabelMap: Record<string, string> = {
  MONTHLY: "Monthly",
  QUARTERLY: "Quarterly",
  YEARLY: "Yearly",
};

// ─── Summary ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  await store.fetchRenewals(60);
  applyFilters();
});

const totalMonthlyPremium = computed(() => store.totalMonthlyPremium);
const activePoliciesCount = computed(() => store.activePolicies.length);
const upcomingRenewalsCount = computed(() => store.upcomingRenewals.length);

// ─── Filters ─────────────────────────────────────────────────────────────────

const {
  filters,
  setFilter,
  setFilters,
  resetFilters,
  applyFilters,
  loading: filtersLoading,
  hasActiveFilters,
} = useLedgerFilters<InsurancePolicyFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["insurance_type", "is_active", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "insurance_type",
    label: "Insurance Type",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "Health", value: "HEALTH" },
      { label: "Auto", value: "AUTO" },
      { label: "Home", value: "HOME" },
      { label: "Life", value: "LIFE" },
      { label: "Travel", value: "TRAVEL" },
      { label: "Business", value: "BUSINESS" },
      { label: "Other", value: "OTHER" },
    ],
  },
  {
    key: "is_active",
    label: "Active Only",
    type: "toggle",
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as InsurancePolicyFilter,
  (partial) => store.setFilters(partial as Partial<InsurancePolicyFilter>),
);

// ─── Search ──────────────────────────────────────────────────────────────────

const searchQuery = ref("");

function handleSearch(query: string) {
  searchQuery.value = query;
  setFilter("search", query || null);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Filter Change Handler ───────────────────────────────────────────────────

function handleFilterChange(key: string, value: unknown) {
  if (key === "is_active") {
    setFilter(key as keyof InsurancePolicyFilter, value ? true : null);
  } else {
    setFilter(key as keyof InsurancePolicyFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<InsurancePolicyFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<InsurancePolicyOut>({
  store,
  entityName: "Policy",
  getEntityLabel: (item) => item.policy_name,
  onDeleted: () => {
    applyFilters();
    store.fetchRenewals(60, true);
  },
  onRestored: () => {
    applyFilters();
    store.fetchRenewals(60, true);
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<InsurancePolicyOut>({
  store,
  entityName: "Policy",
  getEntityLabel: (item) => item.policy_name,
  onActivated: () => {
    applyFilters();
    store.fetchRenewals(60, true);
  },
  onDeactivated: () => {
    applyFilters();
    store.fetchRenewals(60, true);
  },
});

// ─── Create / Edit Modal ─────────────────────────────────────────────────────

const showFormModal = ref(false);
const formMode = ref<"create" | "edit">("create");
const editingItemId = ref<number | undefined>(undefined);

function openCreateForm() {
  formMode.value = "create";
  editingItemId.value = undefined;
  showFormModal.value = true;
}

function openEditForm(item: InsurancePolicyOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: InsurancePolicyOut) {
  closeFormModal();
  applyFilters();
  store.fetchRenewals(60, true);
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onEditClick(event: Event, item: InsurancePolicyOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onDeleteClick(event: Event, item: InsurancePolicyOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: InsurancePolicyOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onActivateClick(event: Event, item: InsurancePolicyOut) {
  event.stopPropagation();
  activator.confirmActivate(item);
}

function onDeactivateClick(event: Event, item: InsurancePolicyOut) {
  event.stopPropagation();
  activator.confirmDeactivate(item);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);
</script>

<template>
  <FeatureGate feature="insurance" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Insurance</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Manage your insurance policies and track renewals
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-primary" @click="openCreateForm">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Add Policy
        </button>
        <PlanLimitBadge max-key="max_insurance" feature-key="insurance" :current="store.items.length" />
      </div>
    </div>

    <!-- ── Summary Bar ────────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Monthly Premium</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ formatCurrency(totalMonthlyPremium) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Active Policies</p>
        <p class="text-xl font-bold text-green-600 dark:text-green-400">
          {{ activePoliciesCount }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Upcoming Renewals</p>
        <p class="text-xl font-bold text-amber-600 dark:text-amber-400">
          {{ upcomingRenewalsCount }}
        </p>
      </div>
    </div>

    <!-- ── Search + Filters ───────────────────────────────────────────────── -->
    <div class="space-y-3">
      <SearchInput
        v-model="searchQuery"
        placeholder="Search policies by name or provider..."
        @search="handleSearch"
      />
      <FilterBar
        :filters="filterConfigs"
        :model-value="{}"
        :loading="isLoading"
        @filter-change="handleFilterChange"
        @reset="handleFilterReset"
        @update:model-value="handleFilterModelUpdate"
      />
    </div>

    <!-- ── Loading State ──────────────────────────────────────────────────── -->
    <LoadingSkeleton v-if="isLoading && !hasItems" type="card" :rows="4" />

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!isLoading && !hasItems"
      icon="shield"
      title="No insurance policies found"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : 'Add your first insurance policy to start tracking coverage and renewals.'"
      :action-label="hasActiveFilters ? '' : 'Add Policy'"
      @action="openCreateForm"
    />

    <!-- ── Policy Cards ───────────────────────────────────────────────────── -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 gap-4"
    >
      <div
        v-for="policy in store.items"
        :key="policy.id"
        class="card p-5 transition-all duration-200 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-700 hover:-translate-y-0.5 group"
        :class="[
          getRenewalBorderColor((policy as InsurancePolicyOut).renewal_date),
          {
            'opacity-60': !policy.is_active || policy.is_deleted,
          },
        ]"
      >
        <!-- Header: Policy Name + Type Badge -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate">
              {{ (policy as InsurancePolicyOut).policy_name }}
            </h3>
            <p class="text-sm text-slate-custom-500 dark:text-slate-custom-400 truncate">
              {{ (policy as InsurancePolicyOut).provider }}
            </p>
            <p
              v-if="(policy as InsurancePolicyOut).is_deleted"
              class="text-xs text-debit mt-0.5"
            >
              Deleted
            </p>
          </div>
          <TypeBadge
            :type="(policy as InsurancePolicyOut).insurance_type"
            :type-map="insuranceTypeMap"
            :show-icon="false"
            size="sm"
          />
        </div>

        <!-- Premium Amount + Frequency Badge -->
        <div class="flex items-baseline gap-2 mb-3">
          <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
            {{ formatCurrency((policy as InsurancePolicyOut).premium_amount, (policy as InsurancePolicyOut).currency || "USD") }}
          </p>
          <span class="inline-flex items-center rounded-full bg-navy-100 dark:bg-navy-800 px-2 py-0.5 text-xs font-medium text-navy-700 dark:text-navy-300">
            {{ frequencyLabelMap[(policy as InsurancePolicyOut).premium_frequency] || (policy as InsurancePolicyOut).premium_frequency }}
          </span>
        </div>

        <!-- Renewal Date + Days Badge -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Renewal Date</p>
            <p :class="['text-sm font-medium', getRenewalDateClass((policy as InsurancePolicyOut).renewal_date)]">
              {{ formatDate((policy as InsurancePolicyOut).renewal_date) }}
            </p>
          </div>
          <div class="text-right">
            <span
              :class="[
                'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
                daysUntilRenewal((policy as InsurancePolicyOut).renewal_date) <= 30
                  ? 'bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-300'
                  : daysUntilRenewal((policy as InsurancePolicyOut).renewal_date) <= 60
                    ? 'bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300'
                    : 'bg-green-100 dark:bg-green-950/50 text-green-800 dark:text-green-300',
              ]"
            >
              {{ getDaysToRenewalLabel((policy as InsurancePolicyOut).renewal_date) }}
            </span>
          </div>
        </div>

        <!-- Coverage + Deductible -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Coverage</p>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ (policy as InsurancePolicyOut).coverage_amount ? formatCurrency((policy as InsurancePolicyOut).coverage_amount!, (policy as InsurancePolicyOut).currency || "USD") : "—" }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Deductible</p>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ (policy as InsurancePolicyOut).deductible ? formatCurrency((policy as InsurancePolicyOut).deductible!, (policy as InsurancePolicyOut).currency || "USD") : "—" }}
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Edit policy"
            :aria-label="`Edit ${(policy as InsurancePolicyOut).policy_name}`"
            @click="onEditClick($event, policy as InsurancePolicyOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Activate/Deactivate -->
          <button
            v-if="(policy as InsurancePolicyOut).is_active && !(policy as InsurancePolicyOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            title="Deactivate policy"
            :aria-label="`Deactivate ${(policy as InsurancePolicyOut).policy_name}`"
            @click="onDeactivateClick($event, policy as InsurancePolicyOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else-if="!(policy as InsurancePolicyOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
            title="Activate policy"
            :aria-label="`Activate ${(policy as InsurancePolicyOut).policy_name}`"
            @click="onActivateClick($event, policy as InsurancePolicyOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Link Document -->
          <button
            v-if="!(policy as InsurancePolicyOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-cyan-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-600 dark:hover:text-cyan-400 transition-colors"
            title="Link document"
            :aria-label="`Link document for ${(policy as InsurancePolicyOut).policy_name}`"
            @click="openLinkDocModal(policy as InsurancePolicyOut, $event)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!(policy as InsurancePolicyOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete policy"
            :aria-label="`Delete ${(policy as InsurancePolicyOut).policy_name}`"
            @click="onDeleteClick($event, policy as InsurancePolicyOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore policy"
            :aria-label="`Restore ${(policy as InsurancePolicyOut).policy_name}`"
            @click="onRestoreClick($event, policy as InsurancePolicyOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ── Pagination ─────────────────────────────────────────────────────── -->
    <div
      v-if="pagination.showPagination.value && hasItems"
      class="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-navy-200 dark:border-navy-700"
    >
      <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
        {{ pagination.showingRange.value }}
      </p>
      <div class="flex items-center gap-1">
        <button
          class="btn-ghost px-3 py-1.5 text-sm"
          :disabled="!pagination.hasPrev.value"
          @click="goToPage(pagination.currentPage.value - 1)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
        <template v-for="page in pagination.totalPages.value" :key="page">
          <button
            v-if="page <= 7 || Math.abs(page - pagination.currentPage.value) <= 1 || page === pagination.totalPages.value"
            :class="[
              'px-3 py-1.5 text-sm rounded-lg transition-colors',
              page === pagination.currentPage.value
                ? 'bg-cyan-600 text-white'
                : 'btn-ghost',
            ]"
            @click="goToPage(page)"
          >
            {{ page }}
          </button>
          <span
            v-else-if="page === 2 || page === pagination.totalPages.value - 1"
            class="px-1 text-slate-custom-400"
          >
            &hellip;
          </span>
        </template>
        <button
          class="btn-ghost px-3 py-1.5 text-sm"
          :disabled="!pagination.hasNext.value"
          @click="goToPage(pagination.currentPage.value + 1)"
        >
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>

    <!-- ── Create / Edit Modal ────────────────────────────────────────────── -->
    <InsurancePolicyForm
      :mode="formMode"
      :item-id="editingItemId"
      :open="showFormModal"
      @saved="handleFormSaved"
      @cancel="closeFormModal"
    />

    <!-- ── Soft Delete / Restore Confirm ──────────────────────────────────── -->
    <ConfirmDialog
      :open="deleter.showConfirm.value"
      :title="deleter.dialogTitle.value"
      :message="deleter.dialogMessage.value"
      :variant="deleter.dialogVariant.value"
      :confirm-text="deleter.confirmText.value"
      :loading="deleter.loading.value"
      @confirm="deleter.execute()"
      @cancel="deleter.cancel()"
    />

    <!-- ── Activate / Deactivate Confirm ──────────────────────────────────── -->
    <ConfirmDialog
      :open="activator.showConfirm.value"
      :title="activator.dialogTitle.value"
      :message="activator.dialogMessage.value"
      :variant="activator.dialogVariant.value"
      :confirm-text="activator.confirmText.value"
      :loading="activator.loading.value"
      @confirm="activator.execute()"
      @cancel="activator.cancel()"
    />

    <!-- ── Link Document Modal ────────────────────────────────────────────── -->
    <Modal
      :open="showLinkDocModal"
      title="Link Document to Policy"
      size="md"
      @close="closeLinkDocModal"
    >
      <template #body>
        <div class="space-y-4">
          <FormErrors :errors="linkDocError" />

          <div v-if="linkingPolicy" class="rounded-lg bg-cyan-50 dark:bg-cyan-950/20 p-3 border border-cyan-200 dark:border-cyan-800">
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ linkingPolicy.policy_name }}
            </p>
            <p class="text-xs text-slate-custom-500">{{ linkingPolicy.provider }}</p>
          </div>

          <div class="space-y-1.5">
            <label class="label-text">Document Name <span class="text-debit">*</span></label>
            <input v-model="linkDocForm.document_name" type="text" class="input-field w-full" placeholder="e.g. Health Insurance Policy" />
          </div>

          <div class="space-y-1.5">
            <label class="label-text">Document Type</label>
            <select v-model="linkDocForm.document_type" class="input-field w-full">
              <option value="INSURANCE_POLICY">Insurance Policy</option>
              <option value="CONTRACT">Contract</option>
              <option value="TAX_DOCUMENT">Tax Document</option>
              <option value="OTHER">Other</option>
            </select>
          </div>

          <div class="space-y-1.5">
            <label class="label-text">File / Reference Number</label>
            <input v-model="linkDocForm.file_number" type="text" class="input-field w-full" placeholder="e.g. POL-2024-001" />
          </div>

          <div class="space-y-1.5">
            <label class="label-text">Notes</label>
            <textarea v-model="linkDocForm.notes" class="input-field w-full min-h-[60px] resize-y" placeholder="Optional notes..." rows="2" />
          </div>
        </div>
      </template>

      <template #footer>
        <button type="button" class="btn-secondary" :disabled="linkDocLoading" @click="closeLinkDocModal">
          Cancel
        </button>
        <button type="button" class="btn-primary" :disabled="linkDocLoading || !linkDocForm.document_name" @click="handleLinkDoc">
          <svg v-if="linkDocLoading" class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Link Document
        </button>
      </template>
    </Modal>
  </div>
  <template #no-access>
    <UpgradePrompt feature="insurance" />
  </template>
  </FeatureGate>
</template>
