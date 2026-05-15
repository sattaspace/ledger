<script setup lang="ts">
/**
 * VaultPage — Grid/list toggle view page for DocumentVault entities.
 *
 * Features:
 *   - Page header: "Document Vault" title + "Upload Document" button
 *   - Summary bar: Total Documents count, Total File Size, Expiring Soon count
 *   - Grid/List toggle buttons (grid is default)
 *   - Grid view: document cards in 3-col grid with file_type icon, file_size,
 *     expiry_date coloring, is_deleted overlay
 *   - List view: simple table rows with same info
 *   - Search + FilterBar (file_type select, expiring_within_days)
 *   - Upload via VaultUploadForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Activate/Deactivate via ConfirmDialog + useActivator
 *   - Click card navigates to detail: /dashboard/vault/${id}
 *   - Pagination, EmptyState, LoadingSkeleton
 *
 * Registers as `ldgr-vault-page` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  ConfirmDialog,
  TypeBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import type { FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useVaultStore } from "@/stores/vault";
import type {
  DocumentVaultOut,
  DocumentVaultFilter,
} from "@/lib/ledgerTypes";
import VaultUploadForm from "./VaultUploadForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrVaultPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useVaultStore();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = bytes / Math.pow(k, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString();
}

function getExpiryDateClass(date: string | null): string {
  if (!date) return "text-green-600 dark:text-green-400";
  const now = new Date();
  const expiry = new Date(date);
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return "text-red-600 dark:text-red-400";
  if (diffDays <= 30) return "text-orange-600 dark:text-orange-400";
  return "text-green-600 dark:text-green-400";
}

function getExpiryDateLabel(date: string | null): string {
  if (!date) return "No expiry";
  const now = new Date();
  const expiry = new Date(date);
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return `Expired ${Math.abs(diffDays)} day${Math.abs(diffDays) !== 1 ? "s" : ""} ago`;
  if (diffDays === 0) return "Expires today";
  if (diffDays === 1) return "Expires tomorrow";
  if (diffDays <= 30) return `Expires in ${diffDays} days`;
  return formatDate(date);
}

// ─── File Type Map ───────────────────────────────────────────────────────────

const fileTypeMap: Record<string, { bg: string; text: string }> = {
  pdf: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300" },
  png: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300" },
  jpg: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  xlsx: { bg: "bg-emerald-100 dark:bg-emerald-950/50", text: "text-emerald-800 dark:text-emerald-300" },
  csv: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  other: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

/** File type icon SVG paths (simplified document-style icons) */
const fileTypeIcons: Record<string, string> = {
  pdf: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z",
  png: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z",
  jpg: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z",
  xlsx: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z",
  csv: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z",
  other: "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z",
};

function getFileTypeKey(ft: string): string {
  const lower = ft?.toLowerCase?.();
  if (lower && fileTypeMap[lower]) return lower;
  return "other";
}

// ─── View Mode ───────────────────────────────────────────────────────────────

const viewMode = ref<"grid" | "list">("grid");

// ─── Summary ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  await store.fetchExpiring(30);
});

const totalDocs = computed(() => store.items.length);
const totalSize = computed(() => store.totalFileSize);
const expiringCount = computed(() => store.expiringSoon.length);

// ─── Filters ─────────────────────────────────────────────────────────────────

const {
  filters,
  setFilter,
  setFilters,
  resetFilters,
  applyFilters,
  applyPage,
  loading: filtersLoading,
  hasActiveFilters,
} = useLedgerFilters<DocumentVaultFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["file_type", "expiring_within_days", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "file_type",
    label: "File Type",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "PDF", value: "PDF" },
      { label: "PNG", value: "PNG" },
      { label: "JPG", value: "JPG" },
      { label: "XLSX", value: "XLSX" },
      { label: "CSV", value: "CSV" },
      { label: "OTHER", value: "OTHER" },
    ],
  },
  {
    key: "expiring_within_days",
    label: "Expiring Within",
    type: "select",
    placeholder: "Any Time",
    options: [
      { label: "7 days", value: "7" },
      { label: "14 days", value: "14" },
      { label: "30 days", value: "30" },
      { label: "60 days", value: "60" },
      { label: "90 days", value: "90" },
    ],
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as DocumentVaultFilter,
  (partial) => store.setFilters(partial as Partial<DocumentVaultFilter>),
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
  if (key === "expiring_within_days") {
    setFilter(key as keyof DocumentVaultFilter, value ? Number(value) : null);
  } else {
    setFilter(key as keyof DocumentVaultFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<DocumentVaultFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<DocumentVaultOut>({
  store,
  entityName: "Document",
  getEntityLabel: (item) => item.title,
  onDeleted: () => {
    applyFilters();
  },
  onRestored: () => {
    applyFilters();
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<DocumentVaultOut>({
  store,
  entityName: "Document",
  getEntityLabel: (item) => item.title,
  onActivated: () => {
    applyFilters();
  },
  onDeactivated: () => {
    applyFilters();
  },
});

// ─── Upload Modal ────────────────────────────────────────────────────────────

const showUploadModal = ref(false);

function openUploadForm() {
  showUploadModal.value = true;
}

function closeUploadModal() {
  showUploadModal.value = false;
}

function handleUploadSaved(_item: DocumentVaultOut) {
  closeUploadModal();
  applyFilters();
  store.fetchExpiring(30, true);
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateToDetail(item: DocumentVaultOut) {
  window.location.href = `/dashboard/vault/${item.id}`;
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onDeleteClick(event: Event, item: DocumentVaultOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: DocumentVaultOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onActivateClick(event: Event, item: DocumentVaultOut) {
  event.stopPropagation();
  activator.confirmActivate(item);
}

function onDeactivateClick(event: Event, item: DocumentVaultOut) {
  event.stopPropagation();
  activator.confirmDeactivate(item);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);
</script>

<template>
  <FeatureGate feature="vault" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Document Vault</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Store and manage your important documents and files
        </p>
      </div>
      <button class="btn-primary" @click="openUploadForm">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Upload Document
      </button>
    </div>

    <!-- ── Summary Bar ────────────────────────────────────────────────────── -->
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total Documents</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ totalDocs }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Total File Size</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ formatFileSize(totalSize) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Expiring Soon</p>
        <p
          :class="[
            'text-xl font-bold',
            expiringCount > 0
              ? 'text-orange-600 dark:text-orange-400'
              : 'text-green-600 dark:text-green-400',
          ]"
        >
          {{ expiringCount }}
        </p>
      </div>
    </div>

    <!-- ── Search + Filters + View Toggle ─────────────────────────────────── -->
    <div class="space-y-3">
      <div class="flex items-center gap-3">
        <div class="flex-1">
          <SearchInput
            v-model="searchQuery"
            placeholder="Search documents by title..."
            @search="handleSearch"
          />
        </div>
        <!-- View Toggle -->
        <div class="flex items-center border border-navy-200 dark:border-navy-700 rounded-lg overflow-hidden">
          <button
            :class="[
              'p-2 transition-colors',
              viewMode === 'grid'
                ? 'bg-cyan-50 dark:bg-cyan-950/30 text-cyan-700 dark:text-cyan-400'
                : 'text-slate-custom-500 dark:text-slate-custom-400 hover:bg-navy-50 dark:hover:bg-navy-800',
            ]"
            title="Grid view"
            aria-label="Grid view"
            @click="viewMode = 'grid'"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </button>
          <button
            :class="[
              'p-2 transition-colors',
              viewMode === 'list'
                ? 'bg-cyan-50 dark:bg-cyan-950/30 text-cyan-700 dark:text-cyan-400'
                : 'text-slate-custom-500 dark:text-slate-custom-400 hover:bg-navy-50 dark:hover:bg-navy-800',
            ]"
            title="List view"
            aria-label="List view"
            @click="viewMode = 'list'"
          >
            <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
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
    <LoadingSkeleton v-if="isLoading && !hasItems" type="card" :rows="6" />

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!isLoading && !hasItems"
      icon="file"
      title="No documents found"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : 'Upload your first document to get started.'"
      :action-label="hasActiveFilters ? '' : 'Upload Document'"
      @action="openUploadForm"
    />

    <!-- ── Grid View ──────────────────────────────────────────────────────── -->
    <div
      v-else-if="viewMode === 'grid'"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <div
        v-for="doc in store.items"
        :key="doc.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-700 hover:-translate-y-0.5 group relative"
        :class="{
          'opacity-60': !doc.is_active || doc.is_deleted,
        }"
        role="button"
        :aria-label="`View ${doc.title} details`"
        tabindex="0"
        @click="navigateToDetail(doc as DocumentVaultOut)"
        @keydown.enter="navigateToDetail(doc as DocumentVaultOut)"
      >
        <!-- Deleted Overlay Badge -->
        <div
          v-if="(doc as DocumentVaultOut).is_deleted"
          class="absolute top-3 right-3"
        >
          <span class="inline-flex items-center rounded-full bg-red-100 dark:bg-red-950/50 px-2 py-0.5 text-xs font-medium text-red-800 dark:text-red-300">
            Deleted
          </span>
        </div>

        <!-- File Type Icon + Title -->
        <div class="flex items-start gap-3 mb-3">
          <div
            :class="[
              'flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
              fileTypeMap[getFileTypeKey((doc as DocumentVaultOut).file_type)]?.bg ?? fileTypeMap.other.bg,
            ]"
          >
            <svg
              :class="[
                'h-5 w-5',
                fileTypeMap[getFileTypeKey((doc as DocumentVaultOut).file_type)]?.text ?? fileTypeMap.other.text,
              ]"
              viewBox="0 0 20 20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path :d="fileTypeIcons[getFileTypeKey((doc as DocumentVaultOut).file_type)] ?? fileTypeIcons.other" />
            </svg>
          </div>
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate">
              {{ (doc as DocumentVaultOut).title }}
            </h3>
            <div class="flex items-center gap-2 mt-1">
              <TypeBadge
                :type="getFileTypeKey((doc as DocumentVaultOut).file_type)"
                :type-map="fileTypeMap"
                :show-icon="false"
                size="sm"
              />
            </div>
          </div>
        </div>

        <!-- File Size + Expiry Date -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">File Size</p>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatFileSize((doc as DocumentVaultOut).file_size) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Expiry</p>
            <p :class="['text-sm font-medium', getExpiryDateClass((doc as DocumentVaultOut).expiry_date)]">
              {{ getExpiryDateLabel((doc as DocumentVaultOut).expiry_date) }}
            </p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Activate/Deactivate -->
          <button
            v-if="(doc as DocumentVaultOut).is_active && !(doc as DocumentVaultOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            title="Deactivate document"
            :aria-label="`Deactivate ${(doc as DocumentVaultOut).title}`"
            @click="onDeactivateClick($event, doc as DocumentVaultOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else-if="!(doc as DocumentVaultOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
            title="Activate document"
            :aria-label="`Activate ${(doc as DocumentVaultOut).title}`"
            @click="onActivateClick($event, doc as DocumentVaultOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!(doc as DocumentVaultOut).is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete document"
            :aria-label="`Delete ${(doc as DocumentVaultOut).title}`"
            @click="onDeleteClick($event, doc as DocumentVaultOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore document"
            :aria-label="`Restore ${(doc as DocumentVaultOut).title}`"
            @click="onRestoreClick($event, doc as DocumentVaultOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ── List View ──────────────────────────────────────────────────────── -->
    <div v-else class="card overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-navy-200 dark:border-navy-700">
              <th class="text-left px-4 py-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Document</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Type</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Size</th>
              <th class="text-left px-4 py-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Expiry</th>
              <th class="text-right px-4 py-3 text-xs font-medium text-slate-custom-500 dark:text-slate-custom-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-navy-100 dark:divide-navy-800">
            <tr
              v-for="doc in store.items"
              :key="doc.id"
              class="cursor-pointer transition-colors hover:bg-cyan-50/50 dark:hover:bg-navy-800/50"
              :class="{ 'opacity-60': !(doc as DocumentVaultOut).is_active || (doc as DocumentVaultOut).is_deleted }"
              @click="navigateToDetail(doc as DocumentVaultOut)"
            >
              <!-- Document Title -->
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div
                    :class="[
                      'flex-shrink-0 w-8 h-8 rounded flex items-center justify-center',
                      fileTypeMap[getFileTypeKey((doc as DocumentVaultOut).file_type)]?.bg ?? fileTypeMap.other.bg,
                    ]"
                  >
                    <svg
                      :class="[
                        'h-4 w-4',
                        fileTypeMap[getFileTypeKey((doc as DocumentVaultOut).file_type)]?.text ?? fileTypeMap.other.text,
                      ]"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path :d="fileTypeIcons[getFileTypeKey((doc as DocumentVaultOut).file_type)] ?? fileTypeIcons.other" />
                    </svg>
                  </div>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-navy-900 dark:text-navy-100 truncate">
                      {{ (doc as DocumentVaultOut).title }}
                    </p>
                    <p
                      v-if="(doc as DocumentVaultOut).is_deleted"
                      class="text-xs text-debit"
                    >
                      Deleted
                    </p>
                  </div>
                </div>
              </td>

              <!-- File Type -->
              <td class="px-4 py-3">
                <TypeBadge
                  :type="getFileTypeKey((doc as DocumentVaultOut).file_type)"
                  :type-map="fileTypeMap"
                  :show-icon="false"
                  size="sm"
                />
              </td>

              <!-- File Size -->
              <td class="px-4 py-3">
                <span class="text-sm text-navy-900 dark:text-navy-100">
                  {{ formatFileSize((doc as DocumentVaultOut).file_size) }}
                </span>
              </td>

              <!-- Expiry Date -->
              <td class="px-4 py-3">
                <span :class="['text-sm font-medium', getExpiryDateClass((doc as DocumentVaultOut).expiry_date)]">
                  {{ getExpiryDateLabel((doc as DocumentVaultOut).expiry_date) }}
                </span>
              </td>

              <!-- Actions -->
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-1" @click.stop>
                  <!-- Activate/Deactivate -->
                  <button
                    v-if="(doc as DocumentVaultOut).is_active && !(doc as DocumentVaultOut).is_deleted"
                    class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-amber-50 dark:hover:bg-amber-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
                    title="Deactivate"
                    :aria-label="`Deactivate ${(doc as DocumentVaultOut).title}`"
                    @click="onDeactivateClick($event, doc as DocumentVaultOut)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button
                    v-else-if="!(doc as DocumentVaultOut).is_deleted"
                    class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-green-600 dark:hover:text-green-400 transition-colors"
                    title="Activate"
                    :aria-label="`Activate ${(doc as DocumentVaultOut).title}`"
                    @click="onActivateClick($event, doc as DocumentVaultOut)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
                    </svg>
                  </button>

                  <!-- Delete / Restore -->
                  <button
                    v-if="!(doc as DocumentVaultOut).is_deleted"
                    class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
                    title="Delete"
                    :aria-label="`Delete ${(doc as DocumentVaultOut).title}`"
                    @click="onDeleteClick($event, doc as DocumentVaultOut)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button
                    v-else
                    class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
                    title="Restore"
                    :aria-label="`Restore ${(doc as DocumentVaultOut).title}`"
                    @click="onRestoreClick($event, doc as DocumentVaultOut)"
                  >
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
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

    <!-- ── Upload Modal ───────────────────────────────────────────────────── -->
    <Modal
      :open="showUploadModal"
      title="Upload Document"
      size="lg"
      @close="closeUploadModal"
    >
      <template #body>
        <VaultUploadForm
          :open="showUploadModal"
          @saved="handleUploadSaved"
          @cancel="closeUploadModal"
        />
      </template>
    </Modal>

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
  </div>
  <template #no-access>
    <UpgradePrompt feature="vault" />
  </template>
  </FeatureGate>
</template>
