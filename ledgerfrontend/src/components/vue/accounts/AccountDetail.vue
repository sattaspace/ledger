<script setup lang="ts">
/**
 * AccountDetail — Full detail view for a single account.
 *
 * Registered as `ldgr-account-detail`.
 *
 * Features:
 *   - Header: Account name, balance, type badge, status badge
 *   - Detail grid: Institution, currency, credit limit, interest rate,
 *     statement/due day, sort order
 *   - Available credit (for liability accounts)
 *   - Actions: Edit, Delete/Restore, Activate/Deactivate, Recalculate Balance
 *   - Back button to /dashboard/accounts
 */

import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  ConfirmDialog,
  StatusBadge,
  TypeBadge,
  LoadingSkeleton,
} from "@/components/vue";
import { useSoftDelete, useActivator, useDropdownLoader } from "@/composables";
import { useAccountStore } from "@/stores/account";
import { useInstitutionStore } from "@/stores/institution";
import { formatCurrency, getBaseCurrency } from "@/lib/currency";
import { formatDateTime } from "@/lib/timezone";
import type { AccountOut } from "@/lib/ledgerTypes";
import AccountForm from "./AccountForm.vue";

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = defineProps<{
  id: string;
}>();

const emit = defineEmits<{
  back: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const accountStore = useAccountStore();
const institutionStore = useInstitutionStore();
const dropdownLoader = useDropdownLoader();

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true);
const error = ref<string | null>(null);
const account = ref<AccountOut | null>(null);
const showEditForm = ref(false);
const recalculating = ref(false);
const recalcResult = ref<{ old_balance: string; new_balance: string; detail: string } | null>(null);

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<AccountOut>({
  store: accountStore,
  entityName: "Account",
  getEntityLabel: (acc) => acc.name || `Account #${acc.id}`,
  onDeleted: () => {
    navigateBack();
  },
  onRestored: () => {
    loadAccount();
  },
  refreshListAfter: false,
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<AccountOut>({
  store: accountStore,
  entityName: "Account",
  refreshListAfter: false,
  onActivated: () => {
    loadAccount();
  },
  onDeactivated: () => {
    loadAccount();
  },
});

// ─── Type Badge Styling ───────────────────────────────────────────────────────

const accountTypeMap = {
  asset: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300" },
  liability: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300" },
  investment: { bg: "bg-purple-100 dark:bg-purple-950/50", text: "text-purple-800 dark:text-purple-300" },
};

// ─── Balance Formatting ──────────────────────────────────────────────────────

function formatBalance(item: AccountOut): string {
  return formatCurrency(item.current_balance, item.currency, { displayMode: "symbol" });
}

function balanceColor(item: AccountOut): string {
  if (item.account_type === "LIABILITY") return "text-debit";
  return parseFloat(item.current_balance) >= 0 ? "text-credit" : "text-debit";
}

// ─── Institution Name Lookup ─────────────────────────────────────────────────

function getInstitutionName(institutionId: number): string {
  const inst = institutionStore.dropdown.find((i) => i.id === institutionId);
  return inst?.name ?? `Institution #${institutionId}`;
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function navigateBack() {
  if (typeof window !== "undefined") {
    window.location.href = "/dashboard/accounts";
  }
  emit("back");
}

// ─── Recalculate Balance ─────────────────────────────────────────────────────

async function handleRecalculateBalance() {
  if (!account.value) return;

  recalculating.value = true;
  recalcResult.value = null;
  error.value = null;

  try {
    const result = await accountStore.recalculateBalance(account.value.id);
    if (result) {
      recalcResult.value = result;
      // Reload the account to reflect the new balance
      account.value = accountStore.current;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to recalculate balance";
  } finally {
    recalculating.value = false;
  }
}

// ─── Edit Form Handlers ──────────────────────────────────────────────────────

function handleEditSaved() {
  showEditForm.value = false;
  loadAccount();
}

function handleEditCancel() {
  showEditForm.value = false;
}

// ─── Load Account ────────────────────────────────────────────────────────────

async function loadAccount() {
  const accountId = parseInt(props.id, 10);
  if (isNaN(accountId)) {
    error.value = "Invalid account ID";
    loading.value = false;
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    account.value = await accountStore.fetchOne(accountId);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load account";
  } finally {
    loading.value = false;
  }
}

// ─── Is Foreign Currency ─────────────────────────────────────────────────────

const isForeignCurrency = computed(() => {
  if (!account.value) return false;
  return account.value.currency !== getBaseCurrency();
});

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(async () => {
  // Load institution dropdown for lookup
  await dropdownLoader.loadDropdown("institutions", institutionStore);

  // Load the account
  await loadAccount();
});
</script>

<template>
  <div class="ldgr-account-detail space-y-6">
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

    <!-- Account Not Found -->
    <div v-else-if="!account" class="card p-12">
      <p class="text-center text-slate-custom-500">Account not found.</p>
    </div>

    <!-- Account Detail -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-500 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="navigateBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
        Back to Accounts
      </button>

      <!-- Header Card -->
      <div class="card p-6">
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <!-- Left: Color, Name, Type/Status -->
          <div class="flex items-start gap-4">
            <!-- Color Indicator -->
            <div
              v-if="account.color"
              class="flex-shrink-0 h-12 w-12 rounded-xl flex items-center justify-center text-white text-lg font-bold"
              :style="{ backgroundColor: account.color }"
            >
              {{ account.name.charAt(0).toUpperCase() }}
            </div>
            <div
              v-else
              class="flex-shrink-0 h-12 w-12 rounded-xl bg-cyan-100 dark:bg-cyan-950/50 flex items-center justify-center text-cyan-700 dark:text-cyan-300 text-lg font-bold"
            >
              {{ account.name.charAt(0).toUpperCase() }}
            </div>

            <div>
              <h1 class="text-xl font-bold text-navy-900 dark:text-navy-100">
                {{ account.name }}
              </h1>
              <div class="flex items-center gap-2 mt-1.5">
                <TypeBadge :type="account.account_type" :type-map="accountTypeMap" :show-icon="false" />
                <StatusBadge :status="account.is_active ? 'Active' : 'Inactive'" />
                <span
                  v-if="account.is_deleted"
                  class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 dark:bg-red-950/50 text-red-800 dark:text-red-300"
                >
                  Deleted
                </span>
              </div>
              <p class="text-sm text-slate-custom-500 mt-1">
                {{ getInstitutionName(account.institution_id) }}
              </p>
            </div>
          </div>

          <!-- Right: Balance -->
          <div class="text-right">
            <div :class="['text-3xl font-bold', balanceColor(account)]">
              {{ formatBalance(account) }}
            </div>
            <div
              v-if="isForeignCurrency"
              class="text-sm text-slate-custom-500 mt-1"
            >
              {{ account.currency }} (Base: {{ getBaseCurrency() }})
            </div>
            <!-- Available Credit -->
            <div
              v-if="account.available_credit"
              class="text-sm text-slate-custom-600 dark:text-slate-custom-400 mt-1"
            >
              Available: {{ formatCurrency(account.available_credit, account.currency, { displayMode: "symbol" }) }}
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

          <!-- Recalculate Balance -->
          <button
            class="btn-secondary text-sm"
            :disabled="recalculating"
            @click="handleRecalculateBalance"
          >
            <svg
              v-if="recalculating"
              class="h-4 w-4 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <svg v-else class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
            {{ recalculating ? "Recalculating..." : "Recalculate Balance" }}
          </button>

          <!-- Activate / Deactivate -->
          <button
            v-if="account.is_active && !account.is_deleted"
            class="btn-ghost text-sm text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
            @click="activator.confirmToggle(account)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            Deactivate
          </button>
          <button
            v-else-if="!account.is_deleted"
            class="btn-ghost text-sm text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300"
            @click="activator.confirmToggle(account)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
            </svg>
            Activate
          </button>

          <!-- Delete/Restore -->
          <button
            v-if="!account.is_deleted"
            class="btn-ghost text-sm text-debit hover:text-red-700"
            @click="deleter.confirmDelete(account)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
            </svg>
            Delete
          </button>
          <button
            v-else
            class="btn-ghost text-sm text-credit hover:text-green-700"
            @click="deleter.confirmRestore(account)"
          >
            <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
            </svg>
            Restore
          </button>
        </div>
      </div>

      <!-- Recalculate Balance Result -->
      <div v-if="recalcResult" class="card p-4 border-l-4 border-cyan-500">
        <div class="flex items-center gap-3">
          <svg class="h-5 w-5 text-cyan-600 dark:text-cyan-400 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
          </svg>
          <div>
            <p class="text-sm font-medium text-navy-900 dark:text-navy-100">Balance Recalculated</p>
            <p class="text-xs text-slate-custom-500 mt-0.5">
              Old: {{ formatCurrency(recalcResult.old_balance, account.currency, { displayMode: "symbol" }) }}
              &rarr;
              New: {{ formatCurrency(recalcResult.new_balance, account.currency, { displayMode: "symbol" }) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Detail Grid -->
      <div class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Account Details</h2>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
          <!-- Institution -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Institution</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ getInstitutionName(account.institution_id) }}
            </dd>
          </div>

          <!-- Account Type -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Account Type</dt>
            <dd class="mt-1">
              <TypeBadge :type="account.account_type" :type-map="accountTypeMap" :show-icon="false" />
            </dd>
          </div>

          <!-- Currency -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Currency</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ account.currency }}
              <span class="text-slate-custom-500 ml-1">({{ account.currency_symbol }})</span>
            </dd>
          </div>

          <!-- Current Balance -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Current Balance</dt>
            <dd :class="['mt-1 text-sm font-semibold', balanceColor(account)]">
              {{ formatBalance(account) }}
            </dd>
          </div>

          <!-- Credit Limit -->
          <div v-if="account.credit_limit">
            <dt class="text-sm font-medium text-slate-custom-500">Credit Limit</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ formatCurrency(account.credit_limit, account.currency, { displayMode: "symbol" }) }}
            </dd>
          </div>

          <!-- Available Credit -->
          <div v-if="account.available_credit">
            <dt class="text-sm font-medium text-slate-custom-500">Available Credit</dt>
            <dd class="mt-1 text-sm font-semibold text-credit">
              {{ formatCurrency(account.available_credit, account.currency, { displayMode: "symbol" }) }}
            </dd>
          </div>

          <!-- Interest Rate -->
          <div v-if="account.interest_rate && account.interest_rate !== '0.00'">
            <dt class="text-sm font-medium text-slate-custom-500">Interest Rate</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ parseFloat(account.interest_rate).toFixed(2) }}%
            </dd>
          </div>

          <!-- Statement Closing Day -->
          <div v-if="account.statement_closing_day">
            <dt class="text-sm font-medium text-slate-custom-500">Statement Closing Day</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ account.statement_closing_day }}{{ account.statement_closing_day === 1 ? 'st' : account.statement_closing_day === 2 ? 'nd' : account.statement_closing_day === 3 ? 'rd' : 'th' }} of the month
            </dd>
          </div>

          <!-- Due Day -->
          <div v-if="account.due_day">
            <dt class="text-sm font-medium text-slate-custom-500">Payment Due Day</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ account.due_day }}{{ account.due_day === 1 ? 'st' : account.due_day === 2 ? 'nd' : account.due_day === 3 ? 'rd' : 'th' }} of the month
            </dd>
          </div>

          <!-- Sort Order -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Sort Order</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ account.sort_order }}
            </dd>
          </div>

          <!-- Notes -->
          <div v-if="account.notes" class="sm:col-span-2">
            <dt class="text-sm font-medium text-slate-custom-500">Notes</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100 whitespace-pre-wrap">
              {{ account.notes }}
            </dd>
          </div>

          <!-- Created At -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Created</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ formatDateTime(account.created_at) }}
            </dd>
          </div>

          <!-- Updated At -->
          <div>
            <dt class="text-sm font-medium text-slate-custom-500">Last Updated</dt>
            <dd class="mt-1 text-sm text-navy-900 dark:text-navy-100">
              {{ formatDateTime(account.updated_at) }}
            </dd>
          </div>
        </dl>
      </div>
    </template>

    <!-- Edit Account Modal -->
    <Modal
      :open="showEditForm"
      title="Edit Account"
      size="lg"
      @close="handleEditCancel"
    >
      <template #body>
        <AccountForm
          mode="edit"
          :item-id="account?.id"
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

    <!-- Activate/Deactivate Confirmation Dialog -->
    <ConfirmDialog
      :open="activator.showConfirm.value"
      :title="activator.dialogTitle.value"
      :message="activator.dialogMessage.value"
      :confirm-text="activator.confirmText.value"
      :variant="activator.dialogVariant.value"
      :loading="activator.loading.value"
      @confirm="activator.execute()"
      @cancel="activator.cancel()"
    />
  </div>
</template>

<script lang="ts">
export default {
  name: "LdgrAccountDetail",
};
</script>
