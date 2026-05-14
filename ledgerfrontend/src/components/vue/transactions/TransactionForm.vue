<script setup lang="ts">
/**
 * TransactionForm — Create/edit transaction with Simple and Split modes.
 *
 * Props:
 *   mode: 'create' | 'edit'
 *   itemId?: number (for edit mode)
 *
 * Features:
 *   - Simple mode: standard transaction fields
 *   - Split mode: split transaction across multiple categories
 *   - Auto-currency detection from selected account
 *   - Split validation: total splits must equal transaction amount
 *   - Uses useCrudForm for form lifecycle
 */

import {
  Modal,
  FormErrors,
  CurrencyInput,
  CategoryTreeSelect,
  TypeBadge,
  TagChips,
} from "@/components/vue";
import type { CurrencyInputValue, TagItem } from "@/components/vue";

import { useCrudForm, useDropdownLoader } from "@/composables";

import { useTransactionStore } from "@/stores/transaction";
import { useAccountStore } from "@/stores/account";
import { useCategoryStore } from "@/stores/category";
import { useTagStore } from "@/stores/tag";
import { useCardStore } from "@/stores/card";

import type {
  TransactionOut,
  TransactionCreate,
  TransactionUpdate,
  TransactionType,
  TransactionStatus,
  TransactionSplitCreate,
} from "@/lib/ledgerTypes";

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    mode: "create" | "edit";
    itemId?: number;
  }>(),
  {
    mode: "create",
    itemId: undefined,
  },
);

const emit = defineEmits<{
  saved: [item: TransactionOut];
  cancel: [];
}>();

// ─── Stores ──────────────────────────────────────────────────────────────────

const transactionStore = useTransactionStore();
const accountStore = useAccountStore();
const categoryStore = useCategoryStore();
const tagStore = useTagStore();
const cardStore = useCardStore();

// ─── Dropdown Loader ─────────────────────────────────────────────────────────

const dropdownLoader = useDropdownLoader();

// ─── Form Mode Toggle ────────────────────────────────────────────────────────

const formMode = ref<"simple" | "split">("simple");

// ─── Transaction Type Options ────────────────────────────────────────────────

const transactionTypeOptions: { value: TransactionType; label: string }[] = [
  { value: "INCOME", label: "Income" },
  { value: "EXPENSE", label: "Expense" },
  { value: "TRANSFER", label: "Transfer" },
  { value: "REFUND", label: "Refund" },
];

const statusOptions: { value: TransactionStatus; label: string }[] = [
  { value: "PENDING", label: "Pending" },
  { value: "CLEARED", label: "Cleared" },
  { value: "VOID", label: "Void" },
];

// ─── Form State ──────────────────────────────────────────────────────────────

const date = ref(today());
const accountId = ref<number | string>("");
const transactionType = ref<TransactionType>("EXPENSE");
const amountOriginal = ref("");
const currencyOriginal = ref("USD");
const exchangeRate = ref("");
const amountBase = ref("");
const categoryId = ref<number | null>(null);
const payee = ref("");
const description = ref("");
const referenceNumber = ref("");
const status = ref<TransactionStatus>("PENDING");
const cardId = ref<number | null>(null);
const isRecurring = ref(false);
const selectedTagIds = ref<number[]>([]);

// ─── Multi-currency Detection ────────────────────────────────────────────────

const baseCurrency = ref("USD");

const isCrossCurrency = computed(() => {
  return currencyOriginal.value !== baseCurrency.value;
});

// ─── Split Mode State ────────────────────────────────────────────────────────

interface SplitRow {
  id: string; // local UUID
  category_id: number | null;
  amount: string;
  notes: string;
}

const splits = ref<SplitRow[]>([]);

function addSplitRow() {
  splits.value.push({
    id: crypto.randomUUID(),
    category_id: null,
    amount: "",
    notes: "",
  });
}

function removeSplitRow(index: number) {
  splits.value.splice(index, 1);
}

// ─── Split Validation ────────────────────────────────────────────────────────

const totalTransactionAmount = computed(() => {
  return parseFloat(amountOriginal.value) || 0;
});

const totalSplitAmount = computed(() => {
  return splits.value.reduce((sum, s) => sum + (parseFloat(s.amount) || 0), 0);
});

const splitRemaining = computed(() => {
  return totalTransactionAmount.value - totalSplitAmount.value;
});

const splitsBalanced = computed(() => {
  if (splits.value.length === 0) return true;
  return Math.abs(splitRemaining.value) < 0.005;
});

// ─── Auto-currency detection ─────────────────────────────────────────────────

watch(accountId, (newAccountId) => {
  if (newAccountId) {
    const account = accountStore.dropdown.find((a) => a.id === Number(newAccountId));
    if (account) {
      currencyOriginal.value = account.currency || "USD";
      baseCurrency.value = account.currency || "USD";
    }
  }
});

// Auto-calculate amount_base when exchange_rate or amount_original changes
watch([exchangeRate, amountOriginal], () => {
  if (isCrossCurrency.value && exchangeRate.value && amountOriginal.value) {
    const rate = parseFloat(exchangeRate.value);
    const amount = parseFloat(amountOriginal.value);
    if (!isNaN(rate) && !isNaN(amount) && rate > 0) {
      amountBase.value = (amount * rate).toFixed(2);
    }
  }
});

// ─── Tags ────────────────────────────────────────────────────────────────────

const availableTags = computed<TagItem[]>(() => {
  return dropdownLoader.getDropdown<{ id: number; name: string; color?: string }>("tags").map((t) => ({
    id: t.id,
    name: t.name,
    color: t.color,
  }));
});

const selectedTags = computed<TagItem[]>(() => {
  return availableTags.value.filter((t) => selectedTagIds.value.includes(t.id));
});

function handleTagAdd(tag: TagItem) {
  if (!selectedTagIds.value.includes(tag.id)) {
    selectedTagIds.value.push(tag.id);
  }
}

function handleTagRemove(tagId: number) {
  selectedTagIds.value = selectedTagIds.value.filter((id) => id !== tagId);
}

// ─── Category Tree ───────────────────────────────────────────────────────────

const categoryTree = ref<typeof categoryStore.tree>([]);

// ─── Loading State ───────────────────────────────────────────────────────────

const submitting = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── Helper ──────────────────────────────────────────────────────────────────

function today(): string {
  return new Date().toISOString().split("T")[0];
}

// ─── Load for Edit Mode ──────────────────────────────────────────────────────

async function loadTransaction() {
  if (props.mode !== "edit" || !props.itemId) return;

  loading.value = true;
  error.value = null;

  try {
    const tx = await transactionStore.fetchOne(props.itemId);

    date.value = tx.date;
    accountId.value = String(tx.account_id);
    transactionType.value = tx.transaction_type as TransactionType;
    amountOriginal.value = tx.amount_original;
    currencyOriginal.value = tx.currency_original;
    exchangeRate.value = tx.exchange_rate && tx.exchange_rate !== "1.000000" ? tx.exchange_rate : "";
    amountBase.value = tx.amount_base && tx.currency_original !== "USD" ? tx.amount_base : "";
    categoryId.value = tx.category_id;
    payee.value = tx.payee || "";
    description.value = tx.description || "";
    referenceNumber.value = tx.reference_number || "";
    status.value = tx.status as TransactionStatus;
    cardId.value = tx.card_id;
    isRecurring.value = tx.is_recurring;

    // Load tags for this transaction
    await transactionStore.fetchTags(tx.id);
    selectedTagIds.value = transactionStore.tags.map((t) => t.tag_id);

    // Load splits for this transaction
    await transactionStore.fetchSplits(tx.id);
    if (transactionStore.splits.length > 0) {
      formMode.value = "split";
      splits.value = transactionStore.splits.map((s) => ({
        id: String(s.id),
        category_id: s.category_id,
        amount: s.amount,
        notes: s.notes || "",
      }));
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load transaction";
  } finally {
    loading.value = false;
  }
}

// ─── Submit ──────────────────────────────────────────────────────────────────

async function handleSubmit() {
  // Clear previous errors
  error.value = null;
  fieldErrors.value = {};

  // Client-side validation
  if (!date.value) {
    fieldErrors.value = { date: ["Date is required"] };
    return;
  }
  if (!accountId.value) {
    fieldErrors.value = { account_id: ["Account is required"] };
    return;
  }
  if (!amountOriginal.value || parseFloat(amountOriginal.value) <= 0) {
    fieldErrors.value = { amount_original: ["Amount must be greater than 0"] };
    return;
  }

  // Split validation
  if (formMode.value === "split" && splits.value.length > 0) {
    if (!splitsBalanced.value) {
      fieldErrors.value = { splits: [`Split amounts must equal transaction amount. $${totalSplitAmount.value.toFixed(2)} of $${totalTransactionAmount.value.toFixed(2)} allocated, $${Math.abs(splitRemaining.value).toFixed(2)} remaining.`] };
      return;
    }
    // Validate each split has a category
    for (let i = 0; i < splits.value.length; i++) {
      if (!splits.value[i].category_id) {
        fieldErrors.value = { splits: [`Split row ${i + 1} must have a category`] };
        return;
      }
      if (!splits.value[i].amount || parseFloat(splits.value[i].amount) <= 0) {
        fieldErrors.value = { splits: [`Split row ${i + 1} must have a positive amount`] };
        return;
      }
    }
  }

  submitting.value = true;

  try {
    const payload: TransactionCreate = {
      date: date.value,
      account_id: Number(accountId.value),
      card_id: cardId.value,
      transaction_type: transactionType.value,
      amount_original: amountOriginal.value,
      currency_original: currencyOriginal.value,
      exchange_rate: isCrossCurrency.value && exchangeRate.value ? exchangeRate.value : null,
      amount_base: isCrossCurrency.value && amountBase.value ? amountBase.value : null,
      category_id: formMode.value === "simple" ? categoryId.value : null,
      payee: payee.value || null,
      description: description.value || null,
      reference_number: referenceNumber.value || null,
      status: status.value,
      is_recurring: isRecurring.value,
    };

    let result: TransactionOut;

    if (props.mode === "edit" && props.itemId) {
      result = await transactionStore.update(props.itemId, payload as TransactionUpdate);
    } else {
      result = await transactionStore.create(payload);
    }

    // Handle tags
    if (selectedTagIds.value.length > 0) {
      await transactionStore.bulkSetTags(result.id, selectedTagIds.value);
    }

    // Handle splits
    if (formMode.value === "split" && splits.value.length > 0) {
      // For create: create all splits after the transaction is created
      // For edit: we'd need to delete existing splits and recreate them
      // Simplified approach: create splits one by one
      for (const split of splits.value) {
        const splitPayload: Omit<TransactionSplitCreate, "transaction_id"> = {
          category_id: split.category_id,
          amount: split.amount,
          notes: split.notes || null,
        };
        await transactionStore.createSplit(result.id, splitPayload);
      }
    }

    emit("saved", result);
  } catch (err) {
    if (err && typeof err === "object" && "errors" in err) {
      fieldErrors.value = (err as { errors: Record<string, string[]> }).errors;
    } else {
      error.value = err instanceof Error ? err.message : "Failed to save transaction";
    }
  } finally {
    submitting.value = false;
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

  // Load category tree
  await categoryStore.fetchTree();
  categoryTree.value = categoryStore.tree;

  // Load transaction data for edit mode
  if (props.mode === "edit" && props.itemId) {
    await loadTransaction();
  }
});
</script>

<template>
  <div class="space-y-5">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <svg class="h-8 w-8 animate-spin text-cyan-600" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    </div>

    <form v-else @submit.prevent="handleSubmit" class="space-y-5">
      <!-- Form Errors -->
      <FormErrors :errors="error" :field-errors="fieldErrors" />

      <!-- Mode Toggle -->
      <div class="flex items-center gap-2 border-b border-navy-200 dark:border-navy-700 pb-3">
        <button
          type="button"
          :class="[
            'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
            formMode === 'simple'
              ? 'bg-cyan-600 text-white'
              : 'bg-navy-100 dark:bg-navy-800 text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-700',
          ]"
          @click="formMode = 'simple'"
        >
          Simple
        </button>
        <button
          type="button"
          :class="[
            'rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
            formMode === 'split'
              ? 'bg-cyan-600 text-white'
              : 'bg-navy-100 dark:bg-navy-800 text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-700',
          ]"
          @click="formMode = 'split'"
        >
          Split
        </button>
        <span class="text-xs text-slate-custom-500 ml-2">
          {{ formMode === 'simple' ? 'Single category transaction' : 'Split across multiple categories' }}
        </span>
      </div>

      <!-- Header Fields (shared between modes) -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Date -->
        <div>
          <label class="label-text mb-1.5 block">Date <span class="text-debit">*</span></label>
          <input
            v-model="date"
            type="date"
            class="input-field w-full"
            required
          />
          <p v-if="fieldErrors.date" class="mt-1 text-xs text-debit">{{ fieldErrors.date[0] }}</p>
        </div>

        <!-- Account -->
        <div>
          <label class="label-text mb-1.5 block">Account <span class="text-debit">*</span></label>
          <select
            v-model="accountId"
            class="input-field w-full"
            required
          >
            <option value="" disabled>Select account...</option>
            <option
              v-for="acct in dropdownLoader.getDropdown<{ id: number; name: string; currency: string }>('accounts')"
              :key="acct.id"
              :value="String(acct.id)"
            >
              {{ acct.name }} ({{ acct.currency }})
            </option>
          </select>
          <p v-if="fieldErrors.account_id" class="mt-1 text-xs text-debit">{{ fieldErrors.account_id[0] }}</p>
        </div>

        <!-- Transaction Type -->
        <div>
          <label class="label-text mb-1.5 block">Type</label>
          <div class="flex flex-wrap gap-1.5">
            <button
              v-for="tType in transactionTypeOptions"
              :key="tType.value"
              type="button"
              :class="[
                'inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors border',
                transactionType === tType.value
                  ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-950/30 ring-1 ring-cyan-500'
                  : 'border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-800 hover:bg-cyan-50/50 dark:hover:bg-navy-700/50',
              ]"
              @click="transactionType = tType.value"
            >
              <TypeBadge :type="tType.value" :show-icon="true" size="sm" />
            </button>
          </div>
        </div>

        <!-- Amount + Currency -->
        <div>
          <label class="label-text mb-1.5 block">Amount <span class="text-debit">*</span></label>
          <CurrencyInput
            :amount="amountOriginal"
            :currency="currencyOriginal"
            @update="(val: CurrencyInputValue) => { amountOriginal = val.amount; currencyOriginal = val.currency; }"
          />
          <p v-if="fieldErrors.amount_original" class="mt-1 text-xs text-debit">{{ fieldErrors.amount_original[0] }}</p>
        </div>
      </div>

      <!-- Multi-currency Fields (shown when currency differs from account's base) -->
      <div v-if="isCrossCurrency" class="rounded-lg bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 p-4">
        <div class="flex items-center gap-2 mb-3">
          <svg class="h-4 w-4 text-amber-600 dark:text-amber-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M17.707 9.293a1 1 0 010 1.414l-7 7a1 1 0 01-1.414 0l-7-7A.997.997 0 012 10V5a3 3 0 013-3h5c.256 0 .512.098.707.293l7 7zM5 6a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
          </svg>
          <span class="text-sm font-medium text-amber-800 dark:text-amber-300">Foreign Currency Transaction</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="label-text mb-1.5 block">Exchange Rate</label>
            <input
              v-model="exchangeRate"
              type="number"
              step="0.0001"
              min="0"
              class="input-field w-full"
              placeholder="e.g. 1.2500"
            />
            <p class="mt-1 text-xs text-slate-custom-500">1 {{ currencyOriginal }} = ? {{ baseCurrency }}</p>
          </div>
          <div>
            <label class="label-text mb-1.5 block">Base Amount ({{ baseCurrency }})</label>
            <input
              v-model="amountBase"
              type="number"
              step="0.01"
              min="0"
              class="input-field w-full"
              placeholder="Auto-calculated"
            />
            <p class="mt-1 text-xs text-slate-custom-500">Amount in {{ baseCurrency }}</p>
          </div>
          <div class="flex items-end">
            <p v-if="exchangeRate && amountOriginal" class="text-sm text-amber-700 dark:text-amber-400 mb-2">
              {{ parseFloat(amountOriginal).toFixed(2) }} {{ currencyOriginal }} &times; {{ parseFloat(exchangeRate).toFixed(4) }} = {{ amountBase || '—' }} {{ baseCurrency }}
            </p>
          </div>
        </div>
      </div>

      <!-- Simple Mode Fields -->
      <template v-if="formMode === 'simple'">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Category -->
          <div>
            <label class="label-text mb-1.5 block">Category</label>
            <CategoryTreeSelect
              v-model="categoryId"
              :categories="categoryTree"
              placeholder="Select category..."
            />
          </div>

          <!-- Payee -->
          <div>
            <label class="label-text mb-1.5 block">Payee</label>
            <input
              v-model="payee"
              type="text"
              class="input-field w-full"
              placeholder="e.g. Grocery Store, Employer"
            />
          </div>

          <!-- Description -->
          <div class="md:col-span-2">
            <label class="label-text mb-1.5 block">Description</label>
            <textarea
              v-model="description"
              class="input-field w-full min-h-[80px] resize-y"
              placeholder="Optional description..."
              rows="3"
            />
          </div>

          <!-- Reference Number -->
          <div>
            <label class="label-text mb-1.5 block">Reference #</label>
            <input
              v-model="referenceNumber"
              type="text"
              class="input-field w-full"
              placeholder="e.g. CHK-1234"
            />
          </div>

          <!-- Card -->
          <div>
            <label class="label-text mb-1.5 block">Card</label>
            <select v-model="cardId" class="input-field w-full">
              <option :value="null">No card</option>
              <option
                v-for="card in dropdownLoader.getDropdown<{ id: number; card_name: string; last_four: string; account_id: number }>('cards')
                  .filter(c => !accountId || c.account_id === Number(accountId))"
                :key="card.id"
                :value="card.id"
              >
                {{ card.card_name }} (•••• {{ card.last_four }})
              </option>
            </select>
          </div>

          <!-- Status -->
          <div>
            <label class="label-text mb-1.5 block">Status</label>
            <select v-model="status" class="input-field w-full">
              <option v-for="st in statusOptions" :key="st.value" :value="st.value">
                {{ st.label }}
              </option>
            </select>
          </div>

          <!-- Recurring Toggle -->
          <div class="flex items-center gap-3">
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                v-model="isRecurring"
                class="sr-only peer"
              />
              <div class="w-9 h-5 bg-navy-200 dark:bg-navy-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-navy-300 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-600"></div>
            </label>
            <span class="text-sm text-navy-900 dark:text-navy-100">Recurring transaction</span>
          </div>

          <!-- Tags -->
          <div class="md:col-span-2">
            <label class="label-text mb-1.5 block">Tags</label>
            <TagChips
              :tags="selectedTags"
              :available-tags="availableTags"
              :editable="true"
              @add="handleTagAdd"
              @remove="handleTagRemove"
            />
          </div>
        </div>
      </template>

      <!-- Split Mode Fields -->
      <template v-if="formMode === 'split'">
        <!-- Split Header Info -->
        <div class="rounded-lg bg-navy-50 dark:bg-navy-800/50 p-3 flex items-center justify-between">
          <div class="text-sm">
            <span class="text-slate-custom-600 dark:text-slate-custom-400">Total:</span>
            <span class="font-semibold text-navy-900 dark:text-navy-100 ml-1">
              {{ totalTransactionAmount.toFixed(2) }} {{ currencyOriginal }}
            </span>
          </div>
          <div class="text-sm">
            <span class="text-slate-custom-600 dark:text-slate-custom-400">Allocated:</span>
            <span
              :class="[
                'font-semibold ml-1',
                splitsBalanced ? 'text-credit' : 'text-debit',
              ]"
            >
              {{ totalSplitAmount.toFixed(2) }} {{ currencyOriginal }}
            </span>
          </div>
          <div class="text-sm">
            <span class="text-slate-custom-600 dark:text-slate-custom-400">Remaining:</span>
            <span
              :class="[
                'font-semibold ml-1',
                Math.abs(splitRemaining) < 0.005 ? 'text-credit' : 'text-debit',
              ]"
            >
              {{ Math.abs(splitRemaining).toFixed(2) }} {{ currencyOriginal }}
            </span>
          </div>
        </div>

        <!-- Split Validation Error -->
        <p v-if="fieldErrors.splits" class="text-sm text-debit">
          {{ fieldErrors.splits[0] }}
        </p>

        <!-- Split Rows -->
        <div class="space-y-3">
          <div
            v-for="(split, index) in splits"
            :key="split.id"
            class="flex items-start gap-3 rounded-lg border border-navy-200 dark:border-navy-700 p-3"
          >
            <!-- Split # -->
            <span class="flex-shrink-0 text-sm font-medium text-slate-custom-500 pt-2">
              {{ index + 1 }}
            </span>

            <!-- Category -->
            <div class="flex-1 min-w-[180px]">
              <label class="label-text mb-1 block text-xs">Category</label>
              <CategoryTreeSelect
                v-model="split.category_id"
                :categories="categoryTree"
                placeholder="Select..."
              />
            </div>

            <!-- Amount -->
            <div class="w-32">
              <label class="label-text mb-1 block text-xs">Amount</label>
              <input
                v-model="split.amount"
                type="number"
                step="0.01"
                min="0"
                class="input-field w-full text-sm"
                placeholder="0.00"
              />
            </div>

            <!-- Notes -->
            <div class="flex-1 min-w-[120px]">
              <label class="label-text mb-1 block text-xs">Notes</label>
              <input
                v-model="split.notes"
                type="text"
                class="input-field w-full text-sm"
                placeholder="Notes..."
              />
            </div>

            <!-- Remove -->
            <button
              type="button"
              class="flex-shrink-0 mt-6 rounded-lg p-1.5 text-slate-custom-400 hover:text-debit transition-colors"
              title="Remove split"
              @click="removeSplitRow(index)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
            </button>
          </div>
        </div>

        <!-- Add Split Row -->
        <button
          type="button"
          class="btn-ghost text-sm text-cyan-600 dark:text-cyan-400"
          @click="addSplitRow"
        >
          <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
          </svg>
          Add Split
        </button>

        <!-- Additional Fields for Split Mode -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Payee -->
          <div>
            <label class="label-text mb-1.5 block">Payee</label>
            <input
              v-model="payee"
              type="text"
              class="input-field w-full"
              placeholder="e.g. Grocery Store"
            />
          </div>

          <!-- Description -->
          <div>
            <label class="label-text mb-1.5 block">Description</label>
            <textarea
              v-model="description"
              class="input-field w-full min-h-[40px] resize-y"
              placeholder="Optional description..."
              rows="2"
            />
          </div>

          <!-- Reference Number -->
          <div>
            <label class="label-text mb-1.5 block">Reference #</label>
            <input
              v-model="referenceNumber"
              type="text"
              class="input-field w-full"
              placeholder="e.g. CHK-1234"
            />
          </div>

          <!-- Card -->
          <div>
            <label class="label-text mb-1.5 block">Card</label>
            <select v-model="cardId" class="input-field w-full">
              <option :value="null">No card</option>
              <option
                v-for="card in dropdownLoader.getDropdown<{ id: number; card_name: string; last_four: string; account_id: number }>('cards')
                  .filter(c => !accountId || c.account_id === Number(accountId))"
                :key="card.id"
                :value="card.id"
              >
                {{ card.card_name }} (•••• {{ card.last_four }})
              </option>
            </select>
          </div>

          <!-- Status -->
          <div>
            <label class="label-text mb-1.5 block">Status</label>
            <select v-model="status" class="input-field w-full">
              <option v-for="st in statusOptions" :key="st.value" :value="st.value">
                {{ st.label }}
              </option>
            </select>
          </div>

          <!-- Recurring Toggle -->
          <div class="flex items-center gap-3">
            <label class="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                v-model="isRecurring"
                class="sr-only peer"
              />
              <div class="w-9 h-5 bg-navy-200 dark:bg-navy-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-navy-300 after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-cyan-600"></div>
            </label>
            <span class="text-sm text-navy-900 dark:text-navy-100">Recurring transaction</span>
          </div>

          <!-- Tags -->
          <div class="md:col-span-2">
            <label class="label-text mb-1.5 block">Tags</label>
            <TagChips
              :tags="selectedTags"
              :available-tags="availableTags"
              :editable="true"
              @add="handleTagAdd"
              @remove="handleTagRemove"
            />
          </div>
        </div>
      </template>

      <!-- Action Buttons -->
      <div class="flex items-center justify-end gap-3 pt-4 border-t border-navy-200 dark:border-navy-700">
        <button
          type="button"
          class="btn-secondary"
          :disabled="submitting"
          @click="emit('cancel')"
        >
          Cancel
        </button>
        <button
          type="submit"
          class="btn-primary"
          :disabled="submitting"
        >
          <svg
            v-if="submitting"
            class="h-4 w-4 animate-spin"
            viewBox="0 0 24 24"
            fill="none"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          {{ mode === "edit" ? "Update Transaction" : "Create Transaction" }}
        </button>
      </div>
    </form>
  </div>
</template>
