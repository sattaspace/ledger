<script setup lang="ts">
/**
 * TransactionDetail — Full detail view for a single transaction.
 *
 * Registered as `ldgr-transaction-detail`.
 *
 * Features:
 *   - Header: Date, Payee, Amount (colored by type), Type badge, Status badge
 *   - Detail grid: Account, Category, Description, Reference, Currency/Exchange rate
 *   - Splits section (if transaction has splits)
 *   - Tags section (TagChips display)
 *   - Transfer pair link (if transfer_pair_id exists)
 *   - Bill link (if bill_id exists)
 *   - Actions: Edit, Delete/Restore, Status change buttons
 *   - Back button to /dashboard/transactions
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  TagChips,
  FormErrors,
  CategoryTreeSelect,
  LoadingSkeleton,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import type { TagItem } from "@/components/vue";

import { useSoftDelete, useDropdownLoader } from "@/composables";

import { useTransactionStore } from "@/stores/transaction";
import { useAccountStore } from "@/stores/account";
import { useCategoryStore } from "@/stores/category";
import { useTagStore } from "@/stores/tag";
import { useCardStore } from "@/stores/card";

import { formatCurrency, formatTransactionAmount, getBaseCurrency } from "@/lib/currency";
import { formatDateTime, formatInUserTimezone } from "@/lib/timezone";

import type {
  TransactionOut,
  TransactionSplitOut,
  TransactionStatus,
  TransactionTagOut,
} from "@/lib/ledgerTypes";

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = defineProps<{
  id: string;
}>();

const emit = defineEmits<{
  back: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const transactionStore = useTransactionStore();
const accountStore = useAccountStore();
const categoryStore = useCategoryStore();
const tagStore = useTagStore();
const cardStore = useCardStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true);
const error = ref<string | null>(null);
const transaction = ref<TransactionOut | null>(null);
const splits = ref<TransactionSplitOut[]>([]);
const tags = ref<TagItem[]>([]);
const showEditForm = ref(false);
const statusChanging = ref(false);

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<TransactionOut>({
  store: transactionStore,
  entityName: "Transaction",
  getEntityLabel: (tx) => tx.payee || `Transaction #${tx.id}`,
  onDeleted: () => {
    navigateBack();
  },
  onRestored: () => {
    loadTransaction();
  },
  refreshListAfter: false,
});

// ─── Amount Formatting ───────────────────────────────────────────────────────

function formatAmount(tx: TransactionOut) {
  const prefix = tx.transaction_type === "EXPENSE" ? "-" : tx.transaction_type === "INCOME" ? "+" : "";
  const color =
    tx.transaction_type === "EXPENSE"
      ? "text-debit"
      : tx.transaction_type === "INCOME"
        ? "text-credit"
        : "text-slate-custom-700 dark:text-slate-custom-300";
  const formatted = `${prefix}${formatCurrency(tx.amount_original, tx.currency_original, { displayMode: "symbol" })}`;
  return { formatted, color, currency: tx.currency_original };
}

// ─── Date Badge Computed ──────────────────────────────────────────────────────

const dateBadgeMonth = computed(() => {
  if (!transaction.value) return "";
  return formatInUserTimezone(transaction.value.date + "T00:00:00", { month: "short" });
});

const dateBadgeDay = computed(() => {
  if (!transaction.value) return "";
  return formatInUserTimezone(transaction.value.date + "T00:00:00", { day: "numeric" });
});

// ─── Lookups ─────────────────────────────────────────────────────────────────

function getAccountName(accountId: number): string {
  const account = accountStore.dropdown.find((a) => a.id === accountId);
  return account?.name ?? `Account #${accountId}`;
}

function getCategoryName(categoryId: number | null): string {
  if (!categoryId) return "—";
  const category = categoryStore.dropdown.find((c) => c.id === categoryId);
  return category?.name ?? `Category #${categoryId}`;
}

function getCardName(cardId: number | null): string {
  if (!cardId) return "—";
  const card = cardStore.dropdown.find((c) => c.id === cardId);
  return card ? `${card.card_name} (•••• ${card.last_four})` : `Card #${cardId}`;
}

// ─── Status Change ───────────────────────────────────────────────────────────

const nextStatusMap: Record<string, TransactionStatus> = {
  PENDING: "CLEARED",
  CLEARED: "VOID",
  VOID: "PENDING",
};

async function changeStatus(newStatus: TransactionStatus) {
  if (!transaction.value) return;

  statusChanging.value = true;
  try {
    await transactionStore.update(transaction.value.id, { status: newStatus });
    transaction.value = transactionStore.current;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to update status";
  } finally {
    statusChanging.value = false;
  }
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateBack() {
  if (typeof window !== "undefined") {
    window.location.href = "/dashboard/transactions";
  }
  emit("back");
}

function navigateToTransferPair(pairId: number) {
  if (typeof window !== "undefined") {
    window.location.href = `/dashboard/transactions/${pairId}`;
  }
}

function navigateToBill(billId: number) {
  // There may not be a bill detail page yet; link to bills page for now
  if (typeof window !== "undefined") {
    window.location.href = `/dashboard/bills?id=${billId}`;
  }
}

// ─── Edit Form Handlers ──────────────────────────────────────────────────────

function handleEditSaved() {
  showEditForm.value = false;
  loadTransaction();
}

function handleEditCancel() {
  showEditForm.value = false;
}

// ─── Load Transaction ────────────────────────────────────────────────────────

async function loadTransaction() {
  const txId = parseInt(props.id, 10);
  if (isNaN(txId)) {
    error.value = "Invalid transaction ID";
    loading.value = false;
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    // Load transaction data
    transaction.value = await transactionStore.fetchOne(txId);

    // Load splits and tags in parallel
    const [, tagsResult] = await Promise.all([
      transactionStore.fetchSplits(txId),
      transactionStore.fetchTags(txId),
    ]);

    splits.value = transactionStore.splits;
    tags.value = transactionStore.tags.map((t: TransactionTagOut) => {
      const tagData = tagStore.dropdown.find((tag) => tag.id === t.tag_id);
      return {
        id: t.tag_id,
        name: tagData?.name ?? `Tag #${t.tag_id}`,
        color: tagData?.color,
      };
    });
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load transaction";
  } finally {
    loading.value = false;
  }
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(async () => {
  // Load dropdown data
  await Promise.all([
    dropdownLoader.loadDropdown("accounts", accountStore),
    dropdownLoader.loadDropdown("categories", categoryStore),
    dropdownLoader.loadDropdown("tags", tagStore),
    dropdownLoader.loadDropdown("cards", cardStore),
  ]);

  // Load the transaction
  await loadTransaction();
});
</script>

<template>
  <FeatureGate feature="transactions" show-fallback>
  <div class="ldgr-transaction-detail space-y-6">
    <!-- Loading State -->
    <LoadingSkeleton v-if="loading" type="detail" />

    <!-- Error State -->
    <div v-else-if="error" class="card p-6">
      <div class="flex items-center gap-3 text-debit">
        <svg class="h-6 w-6 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-sm">{{ error }}</p>
      </div>
    </div>

    <!-- Transaction Not Found -->
    <div v-else-if="!transaction" class="card p-12">
      <p class="text-center text-slate-custom-500">Transaction not found.</p>
    </div>

    <!-- Transaction Detail -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-500 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="navigateBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
        Back to Transactions
      </button>

      <!-- Header Card -->
      <div class="card p-6">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <!-- Left: Date, Payee, Amount -->
          <div class="flex items-start gap-4">
            <!-- Date Badge -->
            <div class="flex-shrink-0 rounded-lg bg-navy-100 dark:bg-navy-800 p-3 text-center min-w-[60px]">
              <div class="text-xs font-medium text-slate-custom-500 uppercase">
                {{ dateBadgeMonth }}
              </div>
              <div class="text-lg font-bold text-navy-900 dark:text-navy-100">
                {{ dateBadgeDay }}
              </div>
            </div>

            <div>
              <h1 class="text-xl font-bold text-navy-900 dark:text-navy-100">
                {{ transaction.payee || "Unnamed Transaction" }}
              </h1>
              <div class="flex items-center gap-2 mt-1.5">
                <TypeBadge :type="transaction.transaction_type" />
                <StatusBadge :status="transaction.status" />
              </div>
            </div>
          </div>

          <!-- Right: Amount -->
          <div class="text-right">
            <div :class="['text-2xl font-bold', formatAmount(transaction).color]">
              {{ formatAmount(transaction).formatted }}
            </div>
            <div
              v-if="formatAmount(transaction).currency !== getBaseCurrency()"
              class="text-sm text-slate-custom-500 mt-0.5"
            >
              {{ formatAmount(transaction).currency }}
              <span v-if="transaction.exchange_rate && transaction.exchange_rate !== '1.000000'">
                (rate: {{ parseFloat(transaction.exchange_rate).toFixed(4) }})
              </span>
            </div>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-navy-200 dark:border-navy-700">
          <!-- Edit -->
          <button class="btn-secondary text-sm" @click="showEditForm = true">
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
            Edit
          </button>

          <!-- Status Change Buttons -->
          <div class="flex items-center gap-1">
            <button
              v-for="st in ['PENDING', 'CLEARED', 'VOID']"
              :key="st"
              :class="[
                'rounded-lg px-3 py-2 text-xs font-medium transition-colors',
                transaction.status === st
                  ? 'bg-cyan-600 text-white'
                  : 'bg-navy-100 dark:bg-navy-800 text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-700',
                statusChanging ? 'opacity-50 cursor-not-allowed' : '',
              ]"
              :disabled="statusChanging || transaction.status === st"
              @click="changeStatus(st as TransactionStatus)"
            >
              {{ st.charAt(0) + st.slice(1).toLowerCase() }}
            </button>
          </div>

          <!-- Delete/Restore -->
          <button
            v-if="!transaction.is_deleted"
            class="btn-ghost text-sm text-debit hover:text-red-700"
            @click="deleter.confirmDelete(transaction)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            Delete
          </button>
          <button
            v-else
            class="btn-ghost text-sm text-credit hover:text-green-700"
            @click="deleter.confirmRestore(transaction)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
            Restore
          </button>
        </div>
      </div>

      <!-- Detail Grid -->
      <div class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Details</h2>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
          <!-- Account -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Account</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ getAccountName(transaction.account_id) }}
            </dd>
          </div>

          <!-- Category -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Category</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ getCategoryName(transaction.category_id) }}
            </dd>
          </div>

          <!-- Card -->
          <div v-if="transaction.card_id">
            <dt class="text-sm font-medium text-slate-custom-500">Card</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ getCardName(transaction.card_id) }}
            </dd>
          </div>

          <!-- Description -->
          <div v-if="transaction.description" class="sm:col-span-2">
            <dt class="text-sm font-medium text-slate-custom-500">Description</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100 whitespace-pre-wrap">
              {{ transaction.description }}
            </dd>
          </div>

          <!-- Reference Number -->
          <div v-if="transaction.reference_number">
            <dt class="text-sm font-medium text-slate-custom-500">Reference #</dt>
            <dd class="mt-1 text-sm font-mono text-navy-900 dark:text-navy-100">
              {{ transaction.reference_number }}
            </dd>
          </div>

          <!-- Currency / Exchange Rate -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Currency</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ transaction.currency_original }}
              <span
                v-if="transaction.exchange_rate && transaction.exchange_rate !== '1.000000'"
                class="text-slate-custom-500 ml-1"
              >
                (Exchange rate: {{ parseFloat(transaction.exchange_rate).toFixed(4) }})
              </span>
            </dd>
          </div>

          <!-- Base Amount -->
          <div v-if="transaction.amount_base && transaction.currency_original !== getBaseCurrency()">
            <dt class="text-sm font-medium text-slate-custom-500">Base Amount ({{ getBaseCurrency() }})</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ formatCurrency(transaction.amount_base, getBaseCurrency()) }}
            </dd>
          </div>

          <!-- Current Value (for foreign currency transactions) -->
          <div v-if="transaction.currency_original !== getBaseCurrency() && transaction.exchange_rate && transaction.exchange_rate !== '1.000000'">
            <dt class="text-sm font-medium text-slate-custom-500">
              Value at Recording
              <span class="text-xs ml-1">(historical)</span>
            </dt>
            <dd class="mt-1 text-sm font-medium text-navy-900 dark:text-navy-100">
              {{ formatTransactionAmount(transaction.amount_original, transaction.currency_original, transaction.amount_base, transaction.exchange_rate) }}
            </dd>
          </div>

          <!-- Recurring -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Recurring</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ transaction.is_recurring ? "Yes" : "No" }}
            </dd>
          </div>

          <!-- Created At -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Created</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ formatDateTime(transaction.created_at) }}
            </dd>
          </div>

          <!-- Updated At -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Last Updated</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ formatDateTime(transaction.updated_at) }}
            </dd>
          </div>
        </dl>
      </div>

      <!-- Splits Section -->
      <div v-if="splits.length > 0" class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Splits</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-navy-200 dark:border-navy-700">
                <th class="px-4 py-2 text-left font-medium text-slate-custom-500">Category</th>
                <th class="px-4 py-2 text-right font-medium text-slate-custom-500">Amount</th>
                <th class="px-4 py-2 text-left font-medium text-slate-custom-500">Notes</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-navy-100 dark:divide-navy-800">
              <tr
                v-for="split in splits"
                :key="split.id"
                class="hover:bg-cyan-50/50 dark:hover:bg-navy-800/50 transition-colors"
              >
                <td class="px-4 py-2 text-navy-900 dark:text-navy-100">
                  {{ getCategoryName(split.category_id) }}
                </td>
                <td class="px-4 py-2 text-right font-medium text-navy-900 dark:text-navy-100">
                  {{ formatCurrency(split.amount, transaction.currency_original, { displayMode: "symbol" }) }}
                </td>
                <td class="px-4 py-2 text-slate-custom-600 dark:text-slate-custom-400">
                  {{ split.notes || "—" }}
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="border-t-2 border-navy-200 dark:border-navy-700">
                <td class="px-4 py-2 font-semibold text-navy-900 dark:text-navy-100">Total</td>
                <td class="px-4 py-2 text-right font-semibold text-navy-900 dark:text-navy-100">
                  {{ formatCurrency(splits.reduce((sum, s) => sum + parseFloat(s.amount), 0), transaction.currency_original, { displayMode: "symbol" }) }}
                </td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- Tags Section -->
      <div v-if="tags.length > 0" class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-3">Tags</h2>
        <TagChips :tags="tags" :size="'md'" />
      </div>

      <!-- Transfer Pair Link -->
      <div v-if="transaction.transfer_pair_id" class="card p-6">
        <div class="flex items-center gap-3">
          <div class="flex-shrink-0 rounded-full bg-cyan-100 dark:bg-cyan-950/50 p-2">
            <svg class="h-5 w-5 text-cyan-600 dark:text-cyan-400" viewBox="0 0 20 20" fill="currentColor">
              <path d="M8 5a1 1 0 100 2h5.586l-1.293 1.293a1 1 0 001.414 1.414l3-3a1 1 0 000-1.414l-3-3a1 1 0 10-1.414 1.414L13.586 5H8zM12 15a1 1 0 100-2H6.414l1.293-1.293a1 1 0 10-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L6.414 15H12z" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
              Transfer Pair
            </p>
            <p class="text-xs text-slate-custom-500 mt-0.5">
              This transaction is part of a transfer.
            </p>
          </div>
          <button
            class="btn-ghost text-sm text-cyan-600 dark:text-cyan-400 ml-auto"
            @click="navigateToTransferPair(transaction.transfer_pair_id!)"
          >
            View Pair →
          </button>
        </div>
      </div>

      <!-- Bill Link -->
      <div v-if="transaction.bill_id" class="card p-6">
        <div class="flex items-center gap-3">
          <div class="flex-shrink-0 rounded-full bg-amber-100 dark:bg-amber-950/50 p-2">
            <svg class="h-5 w-5 text-amber-600 dark:text-amber-400" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
            </svg>
          </div>
          <div>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
              Generated from Bill #{{ transaction.bill_id }}
            </p>
            <p class="text-xs text-slate-custom-500 mt-0.5">
              This transaction was automatically created from a recurring bill.
            </p>
          </div>
          <button
            class="btn-ghost text-sm text-amber-600 dark:text-amber-400 ml-auto"
            @click="navigateToBill(transaction.bill_id!)"
          >
            View Bill →
          </button>
        </div>
      </div>
    </template>

    <!-- Edit Transaction Modal -->
    <Modal
      :open="showEditForm"
      title="Edit Transaction"
      size="lg"
      @close="handleEditCancel"
    >
      <template #body>
        <TransactionForm
          mode="edit"
          :item-id="transaction?.id"
          @saved="handleEditSaved"
          @cancel="handleEditCancel"
        />
      </template>
    </Modal>

    <!-- Delete/Restore Confirmation Dialog -->
    <ConfirmDialog
      :open="deleter.showConfirm.value"
      :title="deleter.dialogTitle.value"
      :message="deleter.dialogMessage.value"
      :confirm-text="deleter.confirmText.value"
      :variant="deleter.dialogVariant.value"
      :loading="deleter.loading.value"
      @confirm="deleter.execute()"
      @cancel="deleter.cancel()"
    />
  </div>
  <template #no-access>
    <UpgradePrompt feature="transactions" />
  </template>
  </FeatureGate>
</template>

<script lang="ts">
import TransactionForm from "./TransactionForm.vue";

export default {
  name: "LdgrTransactionDetail",
};
</script>
