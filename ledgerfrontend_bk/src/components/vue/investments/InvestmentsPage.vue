<script setup lang="ts">
/**
 * InvestmentsPage — Portfolio overview + Investment account list.
 *
 * Features:
 *   - Summary cards at top: Total Portfolio Value, Total Cost Basis,
 *     Total Unrealized Gain/Loss (green/red), Gain/Loss %, Account Count
 *   - Investment account cards: account name, portfolio_value, cost_basis,
 *     unrealized gain/loss, last_synced_at
 *   - Create/Edit via InvestmentForm in Modal
 *   - Delete/Restore via ConfirmDialog + useSoftDelete
 *   - EmptyState, LoadingSkeleton
 *
 * Registers as `ldgr-investments-page` custom element.
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  ConfirmDialog,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  TypeBadge,
  FeatureGate,
  UpgradePrompt,
  PlanLimitBadge,
} from "@/components/vue";
import {
  useSoftDelete,
  useDropdownLoader,
} from "@/composables";
import { useInvestmentStore } from "@/stores/investment";
import { useAccountStore } from "@/stores/account";
import type {
  InvestmentAccountOut,
} from "@/lib/ledgerTypes";
import InvestmentForm from "./InvestmentForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrInvestmentsPage",
});

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useInvestmentStore();
const accountStore = useAccountStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

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

function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

// ─── Account Lookup ──────────────────────────────────────────────────────────

const accountMap = computed(() => {
  const map = new Map<number, string>();
  for (const acct of dropdownLoader.getDropdown<{ id: number; name: string }>("accounts")) {
    map.set(acct.id, acct.name);
  }
  return map;
});

function getAccountName(accountId: number): string {
  return accountMap.value.get(accountId) ?? "Unknown Account";
}

// ─── Gain/Loss Color Helpers ─────────────────────────────────────────────────

function gainLossColor(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return "text-slate-custom-600 dark:text-slate-custom-400";
  return num > 0
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";
}

function gainLossBg(value: string | number): string {
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return "bg-slate-100 dark:bg-slate-800/50";
  return num > 0
    ? "bg-green-100 dark:bg-green-950/50"
    : "bg-red-100 dark:bg-red-950/50";
}

// ─── Asset Type Badge Map ────────────────────────────────────────────────────

const assetTypeMap: Record<string, { bg: string; text: string }> = {
  STOCK: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  ETF: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  CRYPTO: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  BOND: { bg: "bg-emerald-100 dark:bg-emerald-950/50", text: "text-emerald-800 dark:text-emerald-300" },
  MUTUAL_FUND: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  OTHER: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

// ─── Summary ─────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([
    dropdownLoader.loadDropdown("accounts", accountStore),
    store.fetchList(),
    store.fetchSummary(),
  ]);
});

const summary = computed(() => store.summary);

// ─── Search ──────────────────────────────────────────────────────────────────

const searchQuery = ref("");

function handleSearch(query: string) {
  searchQuery.value = query;
  // Client-side filter since investments API doesn't support search
}

const filteredItems = computed(() => {
  if (!searchQuery.value) return store.items;
  const q = searchQuery.value.toLowerCase();
  return store.items.filter((inv) => {
    const accountName = getAccountName(inv.account_id).toLowerCase();
    return accountName.includes(q);
  });
});

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<InvestmentAccountOut>({
  store,
  entityName: "Investment Account",
  getEntityLabel: (item) => getAccountName(item.account_id),
  onDeleted: () => {
    store.fetchList();
    store.fetchSummary(true);
  },
  onRestored: () => {
    store.fetchList();
    store.fetchSummary(true);
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

function openEditForm(item: InvestmentAccountOut) {
  formMode.value = "edit";
  editingItemId.value = item.id;
  showFormModal.value = true;
}

function closeFormModal() {
  showFormModal.value = false;
  editingItemId.value = undefined;
}

function handleFormSaved(_item: InvestmentAccountOut) {
  closeFormModal();
  store.fetchList();
  store.fetchSummary(true);
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateToDetail(item: InvestmentAccountOut) {
  window.location.href = `/dashboard/investments/${item.id}`;
}

// ─── Action Button Stop Propagation ──────────────────────────────────────────

function onEditClick(event: Event, item: InvestmentAccountOut) {
  event.stopPropagation();
  openEditForm(item);
}

function onDeleteClick(event: Event, item: InvestmentAccountOut) {
  event.stopPropagation();
  deleter.confirmDelete(item);
}

function onRestoreClick(event: Event, item: InvestmentAccountOut) {
  event.stopPropagation();
  deleter.confirmRestore(item);
}

// ─── Computed ────────────────────────────────────────────────────────────────

const isLoading = computed(() => store.loading);
const hasItems = computed(() => store.items.length > 0);
</script>

<template>
  <FeatureGate feature="investments" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ────────────────────────────────────────────────────── -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">Investments</h1>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1">
          Track your investment portfolio and holdings
        </p>
      </div>
      <div class="flex items-center gap-3">
        <button class="btn-primary" @click="openCreateForm">
          <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Add Investment Account
        </button>
        <PlanLimitBadge max-key="max_investments" feature-key="investments" :current="store.items.length" />
      </div>
    </div>

    <!-- ── Summary Cards ─────────────────────────────────────────────────── -->
    <div
      v-if="summary"
      class="grid grid-cols-2 sm:grid-cols-5 gap-4"
    >
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Portfolio Value</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ formatCurrency(summary.total_portfolio_value) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Cost Basis</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ formatCurrency(summary.total_cost_basis) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Unrealized G/L</p>
        <p :class="['text-xl font-bold', gainLossColor(summary.total_unrealized_gain_loss)]">
          {{ formatCurrency(summary.total_unrealized_gain_loss) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Gain/Loss %</p>
        <p :class="['text-xl font-bold', gainLossColor(summary.total_gain_loss_percent)]">
          {{ formatPercent(summary.total_gain_loss_percent) }}
        </p>
      </div>
      <div class="card p-4">
        <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Accounts</p>
        <p class="text-xl font-bold text-navy-900 dark:text-navy-100">
          {{ summary.account_count }}
        </p>
      </div>
    </div>

    <!-- ── Search ─────────────────────────────────────────────────────────── -->
    <SearchInput
      v-model="searchQuery"
      placeholder="Search investments by account name..."
      @search="handleSearch"
    />

    <!-- ── Loading State ──────────────────────────────────────────────────── -->
    <LoadingSkeleton v-if="isLoading && !hasItems" type="card" :rows="3" />

    <!-- ── Empty State ────────────────────────────────────────────────────── -->
    <EmptyState
      v-else-if="!isLoading && !hasItems"
      icon="chart"
      title="No investment accounts"
      description="Add your first investment account to start tracking your portfolio performance."
      action-label="Add Investment Account"
      @action="openCreateForm"
    />

    <!-- ── Investment Account Cards ───────────────────────────────────────── -->
    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 gap-4"
    >
      <div
        v-for="inv in filteredItems"
        :key="inv.id"
        class="card p-5 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-cyan-300 dark:hover:border-cyan-700 hover:-translate-y-0.5 group"
        :class="{
          'opacity-60': !inv.is_active || inv.is_deleted,
        }"
        role="button"
        :aria-label="`View ${getAccountName(inv.account_id)} details`"
        tabindex="0"
        @click="navigateToDetail(inv)"
        @keydown.enter="navigateToDetail(inv)"
      >
        <!-- Header: Account Name + Status -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="text-base font-semibold text-navy-900 dark:text-navy-100 truncate">
              {{ getAccountName(inv.account_id) }}
            </h3>
            <p
              v-if="inv.is_deleted"
              class="text-xs text-debit mt-0.5"
            >
              Deleted
            </p>
            <p
              v-if="inv.last_synced_at"
              class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mt-0.5"
            >
              Last synced: {{ formatDate(inv.last_synced_at) }}
            </p>
          </div>
          <!-- Gain/Loss Badge -->
          <span
            :class="[
              'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
              gainLossBg(inv.unrealized_gain_loss),
              gainLossColor(inv.unrealized_gain_loss),
            ]"
          >
            {{ formatPercent(inv.unrealized_gain_loss_percent) }}
          </span>
        </div>

        <!-- Portfolio Value + Cost Basis -->
        <div class="grid grid-cols-2 gap-4 mb-3">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Portfolio Value</p>
            <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(inv.portfolio_value) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Cost Basis</p>
            <p class="text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(inv.cost_basis_total) }}
            </p>
          </div>
        </div>

        <!-- Unrealized Gain/Loss -->
        <div class="mb-3">
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Unrealized Gain/Loss</p>
          <p :class="['text-sm font-bold', gainLossColor(inv.unrealized_gain_loss)]">
            {{ formatCurrency(inv.unrealized_gain_loss) }}
          </p>
        </div>

        <!-- Action Buttons -->
        <div class="flex items-center gap-1 pt-3 border-t border-navy-100 dark:border-navy-800">
          <!-- Edit -->
          <button
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-cyan-50 dark:hover:bg-navy-800 text-slate-custom-600 dark:text-slate-custom-400 hover:text-cyan-700 dark:hover:text-cyan-400 transition-colors"
            title="Edit investment"
            :aria-label="`Edit ${getAccountName(inv.account_id)}`"
            @click="onEditClick($event, inv)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          </button>

          <!-- Delete / Restore -->
          <button
            v-if="!inv.is_deleted"
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-debit transition-colors"
            title="Delete investment"
            :aria-label="`Delete ${getAccountName(inv.account_id)}`"
            @click="onDeleteClick($event, inv)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
          </button>
          <button
            v-else
            class="btn-ghost px-2 py-1.5 text-xs rounded-md hover:bg-green-50 dark:hover:bg-green-950/30 text-slate-custom-600 dark:text-slate-custom-400 hover:text-credit transition-colors"
            title="Restore investment"
            :aria-label="`Restore ${getAccountName(inv.account_id)}`"
            @click="onRestoreClick($event, inv)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- ── Create / Edit Modal ────────────────────────────────────────────── -->
    <Modal
      :open="showFormModal"
      :title="formMode === 'create' ? 'Add Investment Account' : 'Edit Investment Account'"
      size="lg"
      @close="closeFormModal"
    >
      <template #body>
        <InvestmentForm
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
  </div>
  <template #no-access>
    <UpgradePrompt feature="investments" />
  </template>
  </FeatureGate>
</template>
