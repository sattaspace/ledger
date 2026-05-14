<script setup lang="ts">
/**
 * InvestmentDetail — Full detail view for a single InvestmentAccount.
 *
 * Features:
 *   - Header card: Account name, portfolio_value, cost_basis, unrealized gain/loss
 *   - Tab layout: Overview, Holdings
 *   - Overview: all investment fields in detail grid
 *   - Holdings: DataTable with Symbol, Asset Name, Asset Type badge,
 *     Quantity, Cost Basis, Current Price, Current Value,
 *     Unrealized Gain/Loss ($), Unrealized Gain/Loss (%)
 *   - Add/Edit Holding via HoldingForm modal
 *   - Delete holding via ConfirmDialog
 *   - Sort holdings by: value (default desc), gain/loss, symbol
 *   - Unrealized gain/loss color coding: positive = green, negative = red
 *
 * Registers as `ldgr-investment-detail` custom element.
 */

import {
  ConfirmDialog,
  TypeBadge,
  LoadingSkeleton,
  FormErrors,
  DataTable,
  Modal,
} from "@/components/vue";
import type { DataTableColumn } from "@/components/vue";
import {
  useSoftDelete,
  useDropdownLoader,
} from "@/composables";
import { useInvestmentStore } from "@/stores/investment";
import { useAccountStore } from "@/stores/account";
import type {
  InvestmentAccountOut,
  HoldingOut,
} from "@/lib/ledgerTypes";
import InvestmentForm from "./InvestmentForm.vue";
import HoldingForm from "./HoldingForm.vue";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrInvestmentDetail",
});

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  /** Investment ID from Astro route param. */
  id: string;
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const investmentStore = useInvestmentStore();
const accountStore = useAccountStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── State ───────────────────────────────────────────────────────────────────

const investmentId = computed(() => parseInt(props.id, 10));
const activeTab = ref<"overview" | "holdings">("overview");
const showEditModal = ref(false);
const showHoldingModal = ref(false);
const editingHolding = ref<HoldingOut | undefined>(undefined);
const holdingToDelete = ref<HoldingOut | null>(null);
const showDeleteHoldingConfirm = ref(false);

// ─── Sort State for Holdings ─────────────────────────────────────────────────

const holdingSortKey = ref<string>("current_value");
const holdingSortDir = ref<"asc" | "desc">("desc");

// ─── Account Lookup ──────────────────────────────────────────────────────────

const accountMap = computed(() => {
  const map = new Map<number, string>();
  for (const acct of dropdownLoader.getDropdown<{ id: number; name: string }>("accounts")) {
    map.set(acct.id, acct.name);
  }
  return map;
});

function getAccountName(accountId: number | null): string {
  if (!accountId) return "—";
  return accountMap.value.get(accountId) ?? "Unknown Account";
}

// ─── Load Data ───────────────────────────────────────────────────────────────

const isLoading = ref(true);
const loadError = ref<string | null>(null);

async function loadInvestment() {
  if (isNaN(investmentId.value)) {
    loadError.value = "Invalid investment ID";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = null;
  try {
    await investmentStore.fetchOne(investmentId.value);
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load investment";
  } finally {
    isLoading.value = false;
  }
}

async function loadHoldings() {
  if (!isNaN(investmentId.value)) {
    await investmentStore.fetchHoldings(investmentId.value);
  }
}

onMounted(async () => {
  await dropdownLoader.loadDropdown("accounts", accountStore);
  await loadInvestment();
  await loadHoldings();
});

watch(() => props.id, () => {
  loadInvestment();
  loadHoldings();
});

// ─── Computed ────────────────────────────────────────────────────────────────

const investment = computed<InvestmentAccountOut | null>(() => investmentStore.current);

// ─── Sorted Holdings ─────────────────────────────────────────────────────────

const sortedHoldings = computed(() => {
  const holdings = [...investmentStore.holdings];
  const key = holdingSortKey.value;
  const dir = holdingSortDir.value;

  return holdings.sort((a, b) => {
    let valA: number;
    let valB: number;

    switch (key) {
      case "symbol":
        return dir === "asc"
          ? a.symbol.localeCompare(b.symbol)
          : b.symbol.localeCompare(a.symbol);
      case "unrealized_gain_loss":
        valA = parseFloat(a.unrealized_gain_loss || "0");
        valB = parseFloat(b.unrealized_gain_loss || "0");
        break;
      case "current_value":
        valA = parseFloat(a.current_value || "0");
        valB = parseFloat(b.current_value || "0");
        break;
      case "cost_basis":
        valA = parseFloat(a.cost_basis || "0");
        valB = parseFloat(b.cost_basis || "0");
        break;
      default:
        valA = parseFloat(a.current_value || "0");
        valB = parseFloat(b.current_value || "0");
    }

    return dir === "asc" ? valA - valB : valB - valA;
  });
});

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatCurrency(amount: string | number | null, currency = "USD"): string {
  if (amount === null || amount === undefined) return "$0.00";
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

function gainLossColor(value: string | number | null): string {
  if (value === null || value === undefined) return "text-slate-custom-600 dark:text-slate-custom-400";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num) || num === 0) return "text-slate-custom-600 dark:text-slate-custom-400";
  return num > 0
    ? "text-green-600 dark:text-green-400"
    : "text-red-600 dark:text-red-400";
}

function holdingGainLossPercent(holding: HoldingOut): number {
  const costBasis = parseFloat(holding.cost_basis || "0");
  const currentValue = parseFloat(holding.current_value || "0");
  if (costBasis === 0) return 0;
  return ((currentValue - costBasis) / costBasis) * 100;
}

// ─── Type Maps ───────────────────────────────────────────────────────────────

const assetTypeMap: Record<string, { bg: string; text: string }> = {
  STOCK: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  ETF: { bg: "bg-indigo-100 dark:bg-indigo-950/50", text: "text-indigo-800 dark:text-indigo-300" },
  CRYPTO: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  BOND: { bg: "bg-emerald-100 dark:bg-emerald-950/50", text: "text-emerald-800 dark:text-emerald-300" },
  MUTUAL_FUND: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
  OTHER: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

// ─── Soft Delete (investment account) ────────────────────────────────────────

const deleter = useSoftDelete<InvestmentAccountOut>({
  store: investmentStore,
  entityName: "Investment Account",
  getEntityLabel: (item) => getAccountName(item.account_id),
  onDeleted: () => {
    window.location.href = "/dashboard/investments";
  },
  onRestored: () => {
    loadInvestment();
  },
});

// ─── Edit Investment Modal ───────────────────────────────────────────────────

function closeEditModal() {
  showEditModal.value = false;
}

function handleFormSaved() {
  closeEditModal();
  loadInvestment();
  investmentStore.fetchSummary(true);
}

// ─── Holding Modal ───────────────────────────────────────────────────────────

function openAddHolding() {
  editingHolding.value = undefined;
  showHoldingModal.value = true;
}

function openEditHolding(holding: HoldingOut) {
  editingHolding.value = holding;
  showHoldingModal.value = true;
}

function closeHoldingModal() {
  showHoldingModal.value = false;
  editingHolding.value = undefined;
}

function handleHoldingSaved() {
  closeHoldingModal();
  loadHoldings();
  // Investment is refreshed by the store after holding mutation
}

// ─── Delete Holding ──────────────────────────────────────────────────────────

function confirmDeleteHolding(holding: HoldingOut) {
  holdingToDelete.value = holding;
  showDeleteHoldingConfirm.value = true;
}

async function executeDeleteHolding() {
  if (!holdingToDelete.value || !investment.value) return;
  try {
    await investmentStore.deleteHolding(investment.value.id, holdingToDelete.value.id);
    showDeleteHoldingConfirm.value = false;
    holdingToDelete.value = null;
  } catch {
    // Error is set in the store
  }
}

function cancelDeleteHolding() {
  showDeleteHoldingConfirm.value = false;
  holdingToDelete.value = null;
}

// ─── Sort Handler ────────────────────────────────────────────────────────────

function handleSortChange(payload: { key: string; direction: "asc" | "desc" }) {
  holdingSortKey.value = payload.key;
  holdingSortDir.value = payload.direction;
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function goBack() {
  window.location.href = "/dashboard/investments";
}

// ─── Tab Switch ──────────────────────────────────────────────────────────────

function switchTab(tab: "overview" | "holdings") {
  activeTab.value = tab;
  if (tab === "holdings") {
    loadHoldings();
  }
}

// ─── Holdings Table Columns ──────────────────────────────────────────────────

const holdingColumns: DataTableColumn[] = [
  { key: "symbol", label: "Symbol", sortable: true },
  { key: "asset_name", label: "Asset Name", sortable: true },
  { key: "asset_type", label: "Type", sortable: true },
  { key: "quantity", label: "Qty", sortable: true },
  { key: "cost_basis", label: "Cost Basis", sortable: true },
  { key: "current_price", label: "Current Price", sortable: true },
  { key: "current_value", label: "Current Value", sortable: true },
  { key: "unrealized_gain_loss", label: "G/L ($)", sortable: true },
  { key: "gain_loss_pct", label: "G/L (%)", sortable: false },
  { key: "actions", label: "", align: "right" as const },
];
</script>

<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <LoadingSkeleton v-if="isLoading" type="detail" />

    <!-- Error State -->
    <div v-else-if="loadError" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-debit" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-debit font-medium">Failed to load investment</p>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ loadError }}</p>
        <button class="btn-secondary" @click="loadInvestment">Try Again</button>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else-if="!investment" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <p class="text-navy-900 dark:text-navy-100 font-medium">Investment not found</p>
        <button class="btn-secondary" @click="goBack">Back to Investments</button>
      </div>
    </div>

    <!-- Investment Detail Content -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="goBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        Back to Investments
      </button>

      <!-- Header Card -->
      <div class="card p-6">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <!-- Left: Investment Info -->
          <div class="flex-1 space-y-3">
            <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
              {{ getAccountName(investment.account_id) }}
            </h1>
            <div class="flex flex-wrap items-center gap-2">
              <span
                v-if="investment.is_deleted"
                class="inline-flex items-center rounded-full bg-red-100 dark:bg-red-950/50 px-2.5 py-1 text-xs font-medium text-red-800 dark:text-red-300"
              >
                Deleted
              </span>
              <span
                v-else-if="!investment.is_active"
                class="inline-flex items-center rounded-full bg-slate-100 dark:bg-slate-800/50 px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-400"
              >
                Inactive
              </span>
              <span
                :class="[
                  'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium',
                  parseFloat(investment.unrealized_gain_loss) >= 0
                    ? 'bg-green-100 dark:bg-green-950/50 text-green-800 dark:text-green-300'
                    : 'bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-300',
                ]"
              >
                {{ formatPercent(investment.unrealized_gain_loss_percent) }}
              </span>
            </div>
          </div>

          <!-- Right: Actions -->
          <div class="flex flex-col gap-2 md:items-end">
            <button class="btn-primary" @click="showEditModal = true">
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
              Edit
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!investment.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="deleter.confirmDelete(investment)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Delete
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="deleter.confirmRestore(investment)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              Restore
            </button>
          </div>
        </div>

        <!-- Summary Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-navy-100 dark:border-navy-800">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Portfolio Value</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(investment.portfolio_value) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Cost Basis</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatCurrency(investment.cost_basis_total) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Unrealized G/L</p>
            <p :class="['text-lg font-bold', gainLossColor(investment.unrealized_gain_loss)]">
              {{ formatCurrency(investment.unrealized_gain_loss) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">G/L %</p>
            <p :class="['text-lg font-bold', gainLossColor(investment.unrealized_gain_loss_percent)]">
              {{ formatPercent(investment.unrealized_gain_loss_percent) }}
            </p>
          </div>
        </div>

        <!-- Store Error -->
        <FormErrors
          v-if="investmentStore.error"
          :errors="investmentStore.error"
          class="mt-4"
        />
      </div>

      <!-- Tabs -->
      <div class="border-b border-navy-200 dark:border-navy-700">
        <nav class="flex gap-6 -mb-px" aria-label="Investment detail tabs">
          <button
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'overview'
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="switchTab('overview')"
          >
            Overview
          </button>
          <button
            :class="[
              'pb-3 text-sm font-medium border-b-2 transition-colors',
              activeTab === 'holdings'
                ? 'border-cyan-600 text-cyan-700 dark:text-cyan-400'
                : 'border-transparent text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 hover:border-navy-300 dark:hover:border-navy-600',
            ]"
            @click="switchTab('holdings')"
          >
            Holdings ({{ investmentStore.holdings.length }})
          </button>
        </nav>
      </div>

      <!-- Tab: Overview -->
      <div v-if="activeTab === 'overview'" class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Investment Details</h2>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Account</dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ getAccountName(investment.account_id) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Portfolio Value</dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatCurrency(investment.portfolio_value) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Cost Basis Total</dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatCurrency(investment.cost_basis_total) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Unrealized Gain/Loss</dt>
            <dd :class="['text-sm font-medium', gainLossColor(investment.unrealized_gain_loss)]">
              {{ formatCurrency(investment.unrealized_gain_loss) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Gain/Loss %</dt>
            <dd :class="['text-sm font-medium', gainLossColor(investment.unrealized_gain_loss_percent)]">
              {{ formatPercent(investment.unrealized_gain_loss_percent) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Last Synced</dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatDate(investment.last_synced_at) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Created</dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatDate(investment.created_at) }}
            </dd>
          </div>
          <div class="flex flex-col">
            <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Last Updated</dt>
            <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatDate(investment.updated_at) }}
            </dd>
          </div>
        </dl>
      </div>

      <!-- Tab: Holdings -->
      <div v-if="activeTab === 'holdings'" class="card overflow-hidden">
        <div class="p-4 flex items-center justify-between border-b border-navy-100 dark:border-navy-800">
          <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100">Holdings</h2>
          <button
            v-if="!investment.is_deleted"
            class="btn-primary text-sm"
            @click="openAddHolding"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path fill-rule="evenodd" d="M10 5a1 1 0 011 1v3h3a1 1 0 110 2h-3v3a1 1 0 11-2 0v-3H6a1 1 0 110-2h3V6a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
            Add Holding
          </button>
        </div>

        <!-- Holdings DataTable -->
        <DataTable
          :columns="holdingColumns"
          :rows="(sortedHoldings as Record<string, unknown>[])"
          :loading="investmentStore.loadingAction === 'fetchHoldings'"
          :total="sortedHoldings.length"
          :limit="sortedHoldings.length || 25"
          :offset="0"
          @sort-change="handleSortChange"
        >
          <!-- Symbol Column -->
          <template #cell-symbol="{ row }">
            <span class="text-sm font-semibold text-navy-900 dark:text-navy-100">
              {{ (row as HoldingOut).symbol }}
            </span>
          </template>

          <!-- Asset Name Column -->
          <template #cell-asset_name="{ row }">
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ (row as HoldingOut).asset_name }}
            </span>
          </template>

          <!-- Asset Type Column -->
          <template #cell-asset_type="{ row }">
            <TypeBadge
              :type="(row as HoldingOut).asset_type"
              :type-map="assetTypeMap"
              :show-icon="false"
              size="sm"
            />
          </template>

          <!-- Quantity Column -->
          <template #cell-quantity="{ row }">
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ parseFloat((row as HoldingOut).quantity || "0").toFixed(4) }}
            </span>
          </template>

          <!-- Cost Basis Column -->
          <template #cell-cost_basis="{ row }">
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatCurrency((row as HoldingOut).cost_basis, (row as HoldingOut).currency || "USD") }}
            </span>
          </template>

          <!-- Current Price Column -->
          <template #cell-current_price="{ row }">
            <span class="text-sm text-navy-900 dark:text-navy-100">
              {{ formatCurrency((row as HoldingOut).current_price, (row as HoldingOut).currency || "USD") }}
            </span>
          </template>

          <!-- Current Value Column -->
          <template #cell-current_value="{ row }">
            <span class="text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatCurrency((row as HoldingOut).current_value, (row as HoldingOut).currency || "USD") }}
            </span>
          </template>

          <!-- Unrealized Gain/Loss ($) Column -->
          <template #cell-unrealized_gain_loss="{ row }">
            <span :class="['text-sm font-medium', gainLossColor((row as HoldingOut).unrealized_gain_loss)]">
              {{ formatCurrency((row as HoldingOut).unrealized_gain_loss, (row as HoldingOut).currency || "USD") }}
            </span>
          </template>

          <!-- Gain/Loss % Column -->
          <template #cell-gain_loss_pct="{ row }">
            <span :class="['text-sm font-medium', gainLossColor(holdingGainLossPercent(row as HoldingOut))]">
              {{ formatPercent(holdingGainLossPercent(row as HoldingOut)) }}
            </span>
          </template>

          <!-- Actions Column -->
          <template #cell-actions="{ row }">
            <div class="flex items-center gap-1">
              <button
                v-if="!investment.is_deleted"
                class="btn-ghost px-2 py-1 text-sm"
                title="Edit holding"
                aria-label="Edit holding"
                @click.stop="openEditHolding(row as HoldingOut)"
              >
                <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
              </button>
              <button
                v-if="!investment.is_deleted"
                class="btn-ghost px-2 py-1 text-sm hover:text-debit"
                title="Delete holding"
                aria-label="Delete holding"
                @click.stop="confirmDeleteHolding(row as HoldingOut)"
              >
                <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </button>
            </div>
          </template>
        </DataTable>

        <!-- Empty holdings -->
        <div
          v-if="investmentStore.holdings.length === 0 && investmentStore.loadingAction !== 'fetchHoldings'"
          class="p-8 text-center"
        >
          <svg class="h-10 w-10 text-slate-custom-400 mx-auto mb-3" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
            No holdings yet. Click "Add Holding" to track an asset.
          </p>
        </div>
      </div>

      <!-- Edit Investment Modal -->
      <InvestmentForm
        mode="edit"
        :item-id="investmentId"
        :open="showEditModal"
        @saved="handleFormSaved"
        @cancel="closeEditModal"
      />

      <!-- Add/Edit Holding Modal -->
      <Modal
        :open="showHoldingModal"
        :title="editingHolding ? 'Edit Holding' : 'Add Holding'"
        size="lg"
        @close="closeHoldingModal"
      >
        <template #body>
          <HoldingForm
            :investment-id="investment.id"
            :holding="editingHolding"
            @saved="handleHoldingSaved"
            @cancel="closeHoldingModal"
          />
        </template>
      </Modal>

      <!-- Delete Investment ConfirmDialog -->
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

      <!-- Delete Holding ConfirmDialog -->
      <ConfirmDialog
        :open="showDeleteHoldingConfirm"
        title="Delete Holding"
        :message="`Are you sure you want to delete ${holdingToDelete?.symbol || ''} — ${holdingToDelete?.asset_name || ''}? This will also update the portfolio value.`"
        variant="destructive"
        confirm-text="Delete"
        :loading="investmentStore.loadingAction === 'deleteHolding'"
        @confirm="executeDeleteHolding"
        @cancel="cancelDeleteHolding"
      />
    </template>
  </div>
</template>
