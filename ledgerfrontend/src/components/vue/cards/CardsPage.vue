<script setup lang="ts">
/**
 * CardsPage — Visual card layout for Card entities.
 *
 * Features:
 *   - Card visual layout — each card looks like a physical card with:
 *     card_name, card_type badge, last four (•••• 4242), expiry date,
 *     account link, annual fee amount, color strip
 *   - Filter by card_type, account, is_active
 *   - SearchInput for card name search
 *   - "Add Card" button
 *   - Create/Edit via CardForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - Activate/Deactivate via ConfirmDialog + useActivator
 *   - Pagination via useLedgerPagination
 *   - EmptyState, LoadingSkeleton
 *
 * Registers as `ldgr-cards-page` custom element.
 */

import {
  Modal,
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FilterBar,
} from "@/components/vue";
import type { FilterConfig } from "@/components/vue";
import {
  useLedgerPagination,
  useLedgerFilters,
  useSoftDelete,
  useActivator,
  useDropdownLoader,
} from "@/composables";
import { useCardStore } from "@/stores/card";
import { useAccountStore } from "@/stores/account";
import type {
  CardOut,
  CardFilter,
} from "@/lib/ledgerTypes";
import CardForm from "./CardForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrCardsPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useCardStore();
const accountStore = useAccountStore();
const dropdownLoader = useDropdownLoader();

// ─── Dropdown Data ───────────────────────────────────────────────────────────

onMounted(async () => {
  await dropdownLoader.loadDropdown("accounts", accountStore);
});

const accountDropdown = computed(() =>
  dropdownLoader.getDropdown<{ id: number; name: string }>("accounts"),
);

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string | number, currency = "USD"): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(num);
}

function getAccountName(accountId: number): string {
  const acct = accountDropdown.value.find((a) => a.id === accountId);
  return acct?.name ?? "Unknown Account";
}

function getExpiryClass(date: string | null): string {
  if (!date) return "text-slate-custom-500 dark:text-slate-custom-400";
  const now = new Date();
  const expiry = new Date(date);
  const diffMonths = (expiry.getFullYear() - now.getFullYear()) * 12 + (expiry.getMonth() - now.getMonth());
  if (diffMonths < 0) return "text-red-600 dark:text-red-400";
  if (diffMonths <= 3) return "text-orange-600 dark:text-orange-400";
  return "text-slate-custom-600 dark:text-slate-custom-400";
}

function formatExpiry(date: string | null): string {
  if (!date) return "—";
  const d = new Date(date);
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

// ─── Type Maps ───────────────────────────────────────────────────────────────

const cardTypeMap = {
  credit: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  debit: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
};

const cardStatusColorMap = {
  active: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300", dot: "bg-green-500" },
  inactive: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-600 dark:text-slate-400", dot: "bg-slate-400" },
};

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
} = useLedgerFilters<CardFilter>({
  store,
  defaultFilters: { limit: 25, offset: 0 },
  syncKeys: ["card_type", "account_id", "search"],
});

// ─── Filter Config for FilterBar ─────────────────────────────────────────────

const filterConfigs = computed<FilterConfig[]>(() => [
  {
    key: "card_type",
    label: "Card Type",
    type: "select",
    placeholder: "All Types",
    options: [
      { label: "Credit", value: "CREDIT" },
      { label: "Debit", value: "DEBIT" },
    ],
  },
  {
    key: "account_id",
    label: "Account",
    type: "select",
    placeholder: "All Accounts",
    options: accountDropdown.value.map((a) => ({ label: a.name, value: String(a.id) })),
  },
]);

// ─── Pagination ──────────────────────────────────────────────────────────────

const pagination = useLedgerPagination(
  () => store.total,
  () => store.filters as CardFilter,
  (partial) => store.setFilters(partial as Partial<CardFilter>),
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
  if (key === "account_id") {
    setFilter(key as keyof CardFilter, value ? Number(value) : null);
  } else {
    setFilter(key as keyof CardFilter, value as string | null);
  }
  setFilter("offset", 0);
  applyFilters();
}

function handleFilterReset() {
  searchQuery.value = "";
  resetFilters();
}

function handleFilterModelUpdate(values: Record<string, unknown>) {
  setFilters(values as Partial<CardFilter>);
  setFilter("offset", 0);
  applyFilters();
}

// ─── Pagination Handlers ─────────────────────────────────────────────────────

function goToPage(page: number) {
  pagination.goToPage(page);
  applyFilters();
}

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<CardOut>({
  store,
  entityName: "Card",
  getEntityLabel: (item) => item.card_name,
  onDeleted: () => {
    applyFilters();
  },
  onRestored: () => {
    applyFilters();
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<CardOut>({
  store,
  entityName: "Card",
  getEntityLabel: (item) => item.card_name,
  onActivated: () => {
    applyFilters();
  },
  onDeactivated: () => {
    applyFilters();
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

function openEditForm(item: CardOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: CardOut) {
  closeFormModal();
  applyFilters();
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onEditClick(event: Event, item: CardOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onDeleteClick(event: Event, item: CardOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: CardOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

function onActivateClick(event: Event, item: CardOut) {
  event.stopPropagation();
  activator.confirmActivate(item);
}

function onDeactivateClick(event: Event, item: CardOut) {
  event.stopPropagation();
  activator.confirmDeactivate(item);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading || filtersLoading.value);
const hasItems = computed(() => store.items.length > 0);
</script>

<template>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Cards</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Manage your debit and credit cards linked to accounts
        </p>
      </div>
      <button class="btn-primary" @click="openCreateForm">
        <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
        </svg>
        Add Card
      </button>
    </div>

    <!-- ── Search + Filters ───────────────────────────────────────────────── -->
    <div class="space-y-3">
      <SearchInput
        v-model="searchQuery"
        placeholder="Search cards by name..."
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
    <LoadingSkeleton v-if="isLoading && !hasItems" type="card" :rows="6" />

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!isLoading && !hasItems"
      icon="credit-card"
      title="No cards found"
      :description="hasActiveFilters
        ? 'Try adjusting your filters or search query.'
        : 'Add your first card to start tracking debit and credit cards.'"
      :action-label="hasActiveFilters ? '' : 'Add Card'"
      @action="openCreateForm"
    />

    <!-- ── Card Grid (Physical Card Style) ────────────────────────────────── -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"
    >
      <div
        v-for="card in store.items"
        :key="card.id"
        class="group relative overflow-hidden rounded-xl border border-navy-200 dark:border-navy-700 bg-gradient-to-br from-navy-800 to-navy-900 dark:from-navy-700 dark:to-navy-800 shadow-lg transition-all duration-200 hover:shadow-xl hover:-translate-y-0.5 cursor-pointer"
        :class="{
          'opacity-60': !card.is_active || card.is_deleted,
        }"
        role="button"
        :aria-label="`Card: ${card.card_name}`"
        tabindex="0"
      >
        <!-- Color Strip Top -->
        <div
          class="h-2"
          :style="{ backgroundColor: card.color || '#0891b2' }"
        />

        <!-- Card Content -->
        <div class="p-5 text-white">
          <!-- Card Name + Type Badge -->
          <div class="flex items-start justify-between gap-2 mb-4">
            <div class="flex-1 min-w-0">
              <h3 class="text-base font-semibold text-white truncate">
                {{ card.card_name }}
              </h3>
              <p
                v-if="card.is_deleted"
                class="text-xs text-red-300 mt-0.5"
              >
                Deleted
              </p>
            </div>
            <TypeBadge
              :type="card.card_type"
              :type-map="cardTypeMap"
              :show-icon="false"
              size="sm"
            />
          </div>

          <!-- Last Four Digits -->
          <div class="mb-4">
            <p class="text-lg tracking-[0.3em] font-mono text-white/80">
              •••• {{ card.last_four }}
            </p>
          </div>

          <!-- Expiry + Annual Fee Row -->
          <div class="flex items-end justify-between">
            <div>
              <p class="text-[10px] uppercase tracking-wider text-white/50 mb-0.5">Expires</p>
              <p :class="['text-sm font-medium', getExpiryClass(card.expiry_date)]">
                {{ formatExpiry(card.expiry_date) }}
              </p>
            </div>
            <div v-if="card.annual_fee && parseFloat(card.annual_fee) > 0" class="text-right">
              <p class="text-[10px] uppercase tracking-wider text-white/50 mb-0.5">Annual Fee</p>
              <p class="text-sm font-medium text-white/80">
                {{ formatCurrency(card.annual_fee) }}
              </p>
            </div>
          </div>

          <!-- Account Link -->
          <div class="mt-3 pt-3 border-t border-white/10">
            <p class="text-xs text-white/50">
              {{ getAccountName(card.account_id) }}
            </p>
          </div>
        </div>

        <!-- Hover Action Buttons -->
        <div class="absolute bottom-0 left-0 right-0 bg-navy-900/90 dark:bg-navy-800/90 backdrop-blur-sm p-2 flex items-center justify-end gap-1 translate-y-full group-hover:translate-y-0 transition-transform duration-200">
          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-white/10 text-white/70 hover:text-white transition-colors"
            title="Edit card"
            :aria-label="`Edit ${card.card_name}`"
            @click="onEditClick($event, card as CardOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Activate/Deactivate -->
          <button
            v-if="card.is_active && !card.is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-white/10 text-white/70 hover:text-amber-300 transition-colors"
            title="Deactivate card"
            :aria-label="`Deactivate ${card.card_name}`"
            @click="onDeactivateClick($event, card as CardOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else-if="!card.is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-white/10 text-white/70 hover:text-green-300 transition-colors"
            title="Activate card"
            :aria-label="`Activate ${card.card_name}`"
            @click="onActivateClick($event, card as CardOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!card.is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-white/10 text-white/70 hover:text-red-300 transition-colors"
            title="Delete card"
            :aria-label="`Delete ${card.card_name}`"
            @click="onDeleteClick($event, card as CardOut)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-white/10 text-white/70 hover:text-green-300 transition-colors"
            title="Restore card"
            :aria-label="`Restore ${card.card_name}`"
            @click="onRestoreClick($event, card as CardOut)"
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
    <Modal
      :open="showFormModal"
      :title="formMode === 'create' ? 'Add Card' : 'Edit Card'"
      size="lg"
      @close="closeFormModal"
    >
      <template #body>
        <CardForm
          :mode="formMode"
          :item-id="editingItemId"
          @saved="handleFormSaved"
          @cancel="closeFormModal"
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
</template>
