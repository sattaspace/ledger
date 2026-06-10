<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  ArrowLeft, 
  Plus, 
  Trash2, 
  Wallet, 
  Activity, 
  X,
  CreditCard,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  ArrowRight,
  ShieldAlert,
  Calendar,
  Layers,
  Sparkles,
  PieChart,
  Settings,
  Pencil
} from 'lucide-vue-next';
import { type Group, type AccountTransaction } from '../types';
import { db } from '../firebase';
import { collection, query, onSnapshot, orderBy, doc, deleteDoc, updateDoc, setDoc, Timestamp, serverTimestamp } from 'firebase/firestore';
import { formatCurrency } from '../utils/format';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { getCurrencySymbol, CURRENCIES } from '../utils/currency';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

const group = ref<Group | null>(null);
const transactions = ref<AccountTransaction[]>([]);
const otherAccounts = ref<Group[]>([]);
const loading = ref(true);

const filterCategory = ref('all');
const activeTab = ref<'ledger' | 'analytics'>('ledger');

// Modals
const isAddTransactionOpen = ref(false);
const isEditTransactionOpen = ref(false);
const isTransferOpen = ref(false);
const isSettingsOpen = ref(false);
const isDeleteConfirmOpen = ref(false);

const editName = ref('');
const editBankName = ref('');
const editAccountType = ref<'checking' | 'savings' | 'credit_card' | 'debit_card'>('checking');
const editCreditLimit = ref('');
const editColor = ref('slate');
const editCurrencyCode = ref('USD');

// New Transaction State
const txAmount = ref('');
const txDescription = ref('');
const txCategory = ref('Utilities & Bills');
const txDate = ref(new Date().toISOString().split('T')[0]);
const txNote = ref('');
const txType = ref<'expense' | 'deposit'>('expense');

// Edit Transaction State
const editingTransaction = ref<AccountTransaction | null>(null);
const editTxAmount = ref('');
const editTxDescription = ref('');
const editTxCategory = ref('Utilities & Bills');
const editTxDate = ref(new Date().toISOString().split('T')[0]);
const editTxNote = ref('');
const editTxType = ref<'expense' | 'deposit'>('expense');

// Transfer State
const toGroupId = ref('');
const transferAmount = ref('');
const transferDate = ref(new Date().toISOString().split('T')[0]);
const transferNote = ref('');

const categories = [
  'Dining Out',
  'Groceries',
  'Fuel & Transit',
  'Shopping',
  'Entertainment',
  'Utilities & Bills',
  'Salary & Deposit',
  'Card Payment',
  'Transfer',
  'Other'
];

const cardColors = [
  { id: 'slate', bg: 'bg-gradient-to-br from-zinc-800 via-zinc-900 to-black', text: 'text-zinc-100', accent: 'border-zinc-700' },
  { id: 'indigo', bg: 'bg-gradient-to-br from-indigo-700 via-violet-700 to-indigo-950', text: 'text-white', accent: 'border-indigo-500/30' },
  { id: 'emerald', bg: 'bg-gradient-to-br from-teal-600 via-emerald-700 to-teal-950', text: 'text-emerald-50', accent: 'border-emerald-500/30' },
  { id: 'rose', bg: 'bg-gradient-to-br from-rose-600 via-pink-700 to-red-950', text: 'text-white', accent: 'border-rose-500/30' },
  { id: 'amber', bg: 'bg-gradient-to-br from-amber-500 via-orange-600 to-yellow-950', text: 'text-amber-50', accent: 'border-amber-500/30' }
];

const unsubscribes = ref<(() => void)[]>([]);

const filteredTransactions = computed(() => {
  let list = transactions.value;
  if (filterCategory.value !== 'all') {
    list = list.filter(t => t.category === filterCategory.value);
  }
  return list;
});

// Category Breakdown Calculation
const categoryBreakdown = computed(() => {
  const map = new Map<string, number>();
  let totalSpent = 0;

  transactions.value.forEach(tx => {
    if (tx.amount < 0) {
      const abs = Math.abs(tx.amount);
      map.set(tx.category, (map.get(tx.category) || 0) + abs);
      totalSpent += abs;
    }
  });

  const list: { category: string; value: number; percent: number }[] = [];
  map.forEach((value, category) => {
    list.push({
      category,
      value,
      percent: totalSpent > 0 ? (value / totalSpent) * 100 : 0
    });
  });

  return list.sort((a, b) => b.value - a.value);
});

// Load streams
const initDataStreams = () => {
  unsubscribes.value.forEach(unsub => unsub());
  unsubscribes.value = [];

  // 1. Fetch current Account metadata from top-level Group document
  const unsubGroup = onSnapshot(doc(db, 'groups', props.groupId), (snap) => {
    if (snap.exists()) {
      const data = snap.data();
      group.value = { id: snap.id, ...data } as Group;
      if (!isSettingsOpen.value) {
        editName.value = data.name || '';
        editBankName.value = data.bankName || 'Generic Bank';
        editAccountType.value = data.accountType || 'checking';
        editCreditLimit.value = data.creditLimit?.toString() || '';
        editColor.value = data.color || 'slate';
        editCurrencyCode.value = data.currencyCode || 'USD';
      }
      loading.value = false;
    } else {
      emit('back');
    }
  });
  unsubscribes.value.push(unsubGroup);

  // 2. Fetch list of other direct accounts for transfers
  const unsubOtherGroups = onSnapshot(collection(db, 'groups'), (snap) => {
    const list: Group[] = [];
    snap.docs.forEach(doc => {
      const data = doc.data();
      if (data.service === 'accounts' && doc.id !== props.groupId) {
        list.push({ id: doc.id, ...data } as Group);
      }
    });
    otherAccounts.value = list;
    if (list.length > 0 && !toGroupId.value) {
      toGroupId.value = list[0].id;
    }
  });
  unsubscribes.value.push(unsubOtherGroups);

  // 3. Fetch Transaction Log under this account page
  const txQuery = query(
    collection(db, 'groups', props.groupId, 'account_transactions'),
    orderBy('createdAt', 'desc')
  );
  const unsubTx = onSnapshot(txQuery, (snap) => {
    transactions.value = snap.docs.map(d => {
      const data = d.data();
      let resolvedDate = data.date;
      if (typeof resolvedDate === 'string') {
        resolvedDate = { toMillis: () => Date.parse(resolvedDate), toDate: () => new Date(resolvedDate) };
      }
      return { id: d.id, ...data, date: resolvedDate } as AccountTransaction;
    });
  });
  unsubscribes.value.push(unsubTx);
};

onMounted(() => {
  initDataStreams();
});

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

const handleAddTransaction = async () => {
  if (!txDescription.value.trim() || !group.value) return;

  try {
    const amtRaw = parseFloat(txAmount.value) || 0;
    const finalAmt = txType.value === 'expense' ? -amtRaw : amtRaw;

    const newTx: AccountTransaction = {
      id: crypto.randomUUID(),
      groupId: props.groupId,
      accountId: props.groupId, // direct account
      amount: finalAmt,
      description: txDescription.value.trim(),
      category: txCategory.value,
      date: Timestamp.fromDate(new Date(txDate.value)),
      createdAt: Timestamp.now(),
      note: txNote.value.trim() || undefined,
      type: txType.value
    };

    // Commit transaction
    await setDoc(doc(db, 'groups', props.groupId, 'account_transactions', newTx.id), newTx);

    // Compute and update balance immediately
    let newBal = parseFloat(group.value.balance as any || 0);
    if (group.value.accountType === 'credit_card') {
      newBal = newBal - finalAmt; // expense is negative, subtracting a negative increases outstanding charges
    } else {
      newBal = newBal + finalAmt; // standard checkings/savings adjustment
    }

    await updateDoc(doc(db, 'groups', props.groupId), { balance: newBal });

    isAddTransactionOpen.value = false;
    txAmount.value = '';
    txDescription.value = '';
    txNote.value = '';
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'account_transactions');
  }
};

const handleTransfer = async () => {
  if (!props.groupId || !toGroupId.value || !transferAmount.value || !group.value) return;

  try {
    const amt = parseFloat(transferAmount.value) || 0;
    if (amt <= 0) return;

    const targetGroup = otherAccounts.value.find(g => g.id === toGroupId.value);
    if (!targetGroup) return;

    // 1. Debit Source Account
    const sourceTx: AccountTransaction = {
      id: crypto.randomUUID(),
      groupId: props.groupId,
      accountId: props.groupId,
      amount: -amt,
      description: `Transfer to ${targetGroup.name}`,
      category: 'Transfer',
      date: Timestamp.fromDate(new Date(transferDate.value)),
      createdAt: Timestamp.now(),
      note: transferNote.value.trim() || undefined,
      transferToAccountId: toGroupId.value,
      type: 'transfer'
    };
    await setDoc(doc(db, 'groups', props.groupId, 'account_transactions', sourceTx.id), sourceTx);

    let newSourceBal = parseFloat(group.value.balance as any || 0);
    if (group.value.accountType === 'credit_card') {
      newSourceBal = newSourceBal + amt; // subtracting from card increases liability
    } else {
      newSourceBal = newSourceBal - amt; // normal check/savings decreases
    }
    await updateDoc(doc(db, 'groups', props.groupId), { balance: newSourceBal });

    // 2. Credit Target Account
    const targetTx: AccountTransaction = {
      id: crypto.randomUUID(),
      groupId: toGroupId.value,
      accountId: toGroupId.value,
      amount: amt,
      description: `Transfer from ${group.value.name}`,
      category: 'Transfer',
      date: Timestamp.fromDate(new Date(transferDate.value)),
      createdAt: Timestamp.now(),
      note: transferNote.value.trim() || undefined,
      type: 'transfer'
    };
    await setDoc(doc(db, 'groups', toGroupId.value, 'account_transactions', targetTx.id), targetTx);

    let newTargetBal = parseFloat(targetGroup.balance as any || 0);
    if (targetGroup.accountType === 'credit_card') {
      newTargetBal = newTargetBal - amt; // depositing into card pays off/reduces liability
    } else {
      newTargetBal = newTargetBal + amt; // checkings/savings increases
    }
    await updateDoc(doc(db, 'groups', toGroupId.value), { balance: newTargetBal });

    isTransferOpen.value = false;
    transferAmount.value = '';
    transferNote.value = '';
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'transfers');
  }
};

const handleDeleteTransaction = async (tx: AccountTransaction) => {
  if (!confirm("Are you sure you want to permanently delete this transaction? Balance will adjust.") || !group.value) return;

  try {
    let rolledBal = parseFloat(group.value.balance as any || 0);
    if (group.value.accountType === 'credit_card') {
      rolledBal = rolledBal + tx.amount; // reversing outstanding charges
    } else {
      rolledBal = rolledBal - tx.amount; // reversing checking deposits/expenses
    }

    await updateDoc(doc(db, 'groups', props.groupId), { balance: rolledBal });
    await deleteDoc(doc(db, 'groups', props.groupId, 'account_transactions', tx.id));
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, 'account_transactions');
  }
};

const handleOpenEditTransaction = (tx: AccountTransaction) => {
  editingTransaction.value = tx;
  editTxAmount.value = Math.abs(tx.amount).toString();
  editTxDescription.value = tx.description;
  editTxCategory.value = tx.category;
  editTxDate.value = tx.date?.toDate ? tx.date.toDate().toISOString().split('T')[0] : new Date(tx.date as any).toISOString().split('T')[0];
  editTxNote.value = tx.note || '';
  editTxType.value = tx.amount >= 0 ? 'deposit' : 'expense';
  isEditTransactionOpen.value = true;
};

const handleUpdateTransaction = async () => {
  if (!editingTransaction.value || !editTxDescription.value.trim() || !group.value) return;

  try {
    const amtRaw = parseFloat(editTxAmount.value) || 0;
    const finalAmt = editTxType.value === 'expense' ? -amtRaw : amtRaw;

    const oldAmt = editingTransaction.value.amount;
    const diff = finalAmt - oldAmt;

    let newBal = parseFloat(group.value.balance as any || 0);
    if (group.value.accountType === 'credit_card') {
      newBal = newBal - diff;
    } else {
      newBal = newBal + diff;
    }

    const updatedTx: Partial<AccountTransaction> = {
      amount: finalAmt,
      description: editTxDescription.value.trim(),
      category: editTxCategory.value,
      date: Timestamp.fromDate(new Date(editTxDate.value)),
      note: editTxNote.value.trim() || undefined,
      type: editTxType.value
    };

    await updateDoc(doc(db, 'groups', props.groupId, 'account_transactions', editingTransaction.value.id), updatedTx);
    await updateDoc(doc(db, 'groups', props.groupId), { balance: newBal });

    isEditTransactionOpen.value = false;
    editingTransaction.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, 'account_transactions');
  }
};

const handleUpdateSettings = async () => {
  if (!editName.value.trim() || !group.value) return;

  try {
    const updatedData = {
      name: editName.value.trim(),
      bankName: editBankName.value.trim() || 'Generic Bank',
      accountType: editAccountType.value,
      creditLimit: editAccountType.value === 'credit_card' ? (parseFloat(editCreditLimit.value) || 0) : 0,
      color: editColor.value,
      currencyCode: editCurrencyCode.value
    };

    await updateDoc(doc(db, 'groups', props.groupId), updatedData);
    isSettingsOpen.value = false;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/${props.groupId}`);
  }
};

const handleDeleteGroup = async () => {
  if (!group.value) return;
  try {
    await deleteDoc(doc(db, 'groups', props.groupId));
    isDeleteConfirmOpen.value = false;
    emit('back');
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/${props.groupId}`);
  }
};

const getCardClass = (colorId: string | undefined) => {
  const clr = cardColors.find(c => c.id === colorId) || cardColors[0];
  return `${clr.bg} ${clr.text} border-2 ${clr.accent}`;
};
</script>

<template>
  <div v-if="loading" class="flex justify-center items-center py-24">
    <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
  </div>

  <div v-else class="space-y-8">
    
    <!-- Header Navigation -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-100 dark:border-white/5 pb-6">
      <div class="flex items-center gap-4">
        <button 
          @click="$emit('back')" 
          class="p-3 bg-white dark:bg-[#0d151a] hover:bg-zinc-50 dark:hover:bg-white/5 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-white/5 rounded-2xl transition-all cursor-pointer shadow-sm shrink-0"
        >
          <ArrowLeft class="w-5 h-5" />
        </button>
        <div>
          <div class="flex items-center gap-2 mb-0.5">
            <span class="text-[10px] font-bold uppercase tracking-wider text-teal-600 dark:text-teal-400 font-mono">
              {{ group?.bankName || 'Direct' }} &bull; {{ group?.accountType }} Ledger
            </span>
          </div>
          <h1 class="text-2xl font-bold text-zinc-900 dark:text-white font-display">{{ group?.name }}</h1>
        </div>
      </div>

      <div class="flex items-center gap-2">
        <button 
          v-if="otherAccounts.length > 0"
          @click="isTransferOpen = true" 
          class="px-4 py-3.5 bg-zinc-50 dark:bg-white/5 hover:bg-zinc-100 dark:hover:bg-white/10 text-zinc-700 dark:text-zinc-300 border border-zinc-200 dark:border-white/10 rounded-xl text-xs font-bold font-display cursor-pointer transition-all flex items-center gap-2"
        >
          <RefreshCw class="w-4 h-4" /> Transfer Funds
        </button>
        <button 
          @click="isAddTransactionOpen = true" 
          class="px-4 py-3.5 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 rounded-xl text-xs font-bold font-display cursor-pointer hover:opacity-90 transition-all flex items-center gap-2 border-none shadow-sm"
        >
          <Plus class="w-4 h-4" /> Add Transaction
        </button>
        <button 
          v-if="user.uid === group?.createdBy"
          @click="isSettingsOpen = true" 
          class="p-3 bg-white dark:bg-[#0d151a] hover:bg-zinc-50 dark:hover:bg-white/5 text-zinc-600 dark:text-zinc-400 border border-zinc-200 dark:border-white/5 rounded-2xl transition-all cursor-pointer shadow-sm shrink-0"
          title="Account Settings"
        >
          <Settings class="w-5 h-5" />
        </button>
      </div>
    </div>

    <!-- Main visual content split -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
      
      <!-- Holographic card representation & details info -->
      <div class="space-y-6">
        <h3 class="text-[10px] font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 font-display">Active Card Details</h3>
        
        <div 
          class="p-7 rounded-[32px] overflow-hidden shadow-xl min-h-[220px] flex flex-col justify-between relative border-none"
          :class="getCardClass(group?.color)"
        >
          <!-- Shiny shimmer glaze -->
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:animate-shimmer pointer-events-none" />

          <!-- Header -->
          <div class="flex items-start justify-between relative z-10">
            <div>
              <p class="text-[9px] font-bold tracking-widest uppercase opacity-60 font-mono mb-1 leading-none">
                {{ group?.bankName || 'Direct Asset' }}
              </p>
              <h3 class="text-xl font-bold leading-tight font-sans tracking-tight">{{ group?.name }}</h3>
            </div>
            <div class="px-3 py-1.5 bg-black/15 dark:bg-black/30 rounded-xl text-[10px] font-bold font-mono tracking-wider opacity-90">
              <span v-if="group?.accountType === 'checking'">CHECKING</span>
              <span v-else-if="group?.accountType === 'savings'">SAVINGS</span>
              <span v-else-if="group?.accountType === 'credit_card'">CREDIT</span>
              <span v-else-if="group?.accountType === 'debit_card'">DEBIT</span>
              <span v-else class="uppercase">{{ group?.accountType || 'CASH' }}</span>
            </div>
          </div>

          <!-- Chip & Number -->
          <div class="flex items-center gap-4 py-4 relative z-10">
            <div class="w-9 h-7 bg-amber-400/35 border border-amber-300/30 rounded-md relative shadow-inner overflow-hidden shrink-0">
              <div class="absolute left-1.5 top-0 h-full w-[1px] bg-white/20" />
              <div class="absolute left-3 top-0 h-full w-[1px] bg-white/20" />
              <div class="absolute top-1.5 left-0 w-full h-[1px] bg-white/20" />
              <div class="absolute top-3.5 left-0 w-full h-[1px] bg-white/20" />
            </div>
            <p class="font-mono text-sm tracking-widest opacity-80">{{ group?.cardNumber || '•••• •••• •••• 8888' }}</p>
          </div>

          <!-- Bottom calculations -->
          <div class="pt-4 border-t border-white/10 flex items-end justify-between relative z-10">
            <div>
              <p class="text-[8px] font-bold uppercase tracking-wider opacity-60 leading-none mb-1.5 font-mono">
                {{ group?.accountType === 'credit_card' ? 'Outstanding Charges' : 'Asset Balance' }}
              </p>
              <p class="text-2xl font-bold font-mono tracking-tight leading-none">
                {{ formatCurrency(group?.balance || 0, group?.currencyCode || user?.defaultCurrency || 'USD') }}
              </p>
            </div>
          </div>
        </div>

        <!-- Limits guidelines if credit card -->
        <div v-if="group?.accountType === 'credit_card'" class="bg-zinc-50 dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[28px] p-6 space-y-4">
          <div class="flex justify-between text-xs">
            <span class="font-bold text-zinc-400 uppercase tracking-wider">Credit Limit</span>
            <span class="font-bold text-zinc-900 dark:text-white font-mono">
              {{ formatCurrency(group?.creditLimit || 0, group?.currencyCode || 'USD') }}
            </span>
          </div>
          <div class="flex justify-between text-xs pt-3 border-t border-zinc-100 dark:border-white/5">
            <span class="font-bold text-zinc-400 uppercase tracking-wider">Available Credit</span>
            <span class="font-bold font-mono" :class="(group?.creditLimit || 0) - (group?.balance || 0) > (group?.creditLimit || 0) * 0.7 ? 'text-emerald-500' : 'text-rose-500'">
              {{ formatCurrency(Math.max((group?.creditLimit || 0) - (group?.balance || 0), 0), group?.currencyCode || 'USD') }}
            </span>
          </div>

          <div v-if="(group?.balance || 0) > (group?.creditLimit || 0) * 0.3" class="p-3 bg-rose-50 dark:bg-rose-500/10 border border-rose-500/10 text-rose-600 dark:text-rose-400 rounded-xl text-xs flex items-center gap-2">
            <ShieldAlert class="w-4 h-4 shrink-0" />
            <span>High credit utilization! Pay outstanding debt immediately.</span>
          </div>
        </div>

      </div>

      <!-- Right 2 cols Tabs content -->
      <div class="lg:col-span-2 space-y-6">
        
        <!-- Tab Selector -->
        <div class="bg-zinc-100 dark:bg-white/5 p-1 rounded-2xl flex items-center max-w-xs sm:max-w-[240px]">
          <button 
            @click="activeTab = 'ledger'" 
            class="flex-1 py-2 text-xs font-bold font-display rounded-xl transition-all border-none cursor-pointer bg-transparent" 
            :class="activeTab === 'ledger' ? 'bg-white dark:bg-zinc-900 text-zinc-950 dark:text-white shadow-sm' : 'text-zinc-500'"
          >
            Ledger Log
          </button>
          <button 
            @click="activeTab = 'analytics'" 
            class="flex-1 py-2 text-xs font-bold font-display rounded-xl transition-all border-none cursor-pointer bg-transparent" 
            :class="activeTab === 'analytics' ? 'bg-white dark:bg-zinc-900 text-zinc-950 dark:text-white shadow-sm' : 'text-zinc-500'"
          >
            Analytics
          </button>
        </div>

        <!-- Ledger tab content -->
        <div v-if="activeTab === 'ledger'" class="space-y-4">
          <div class="flex items-center justify-between">
            <h3 class="text-[10px] font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-500 font-display">Account Postings</h3>
            
            <select 
              v-model="filterCategory"
              class="px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-white/5 rounded-xl text-zinc-600 dark:text-zinc-300 font-bold text-xs cursor-pointer focus:outline-none"
            >
              <option value="all">All Categories</option>
              <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
            </select>
          </div>

          <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[32px] p-6 shadow-sm overflow-x-auto">
            <div-table class="w-full text-left min-w-[500px]">
              <div class="flex justify-between border-b border-zinc-100 dark:border-white/5 text-[10px] font-bold uppercase tracking-widest text-zinc-400 pb-3 mb-2 px-2">
                <span class="w-2/5">Merchant / Description</span>
                <span class="w-1/4">Date</span>
                <span class="w-1/5">Category</span>
                <span class="w-1/6 text-right">Amount</span>
              </div>

              <div v-if="filteredTransactions.length === 0" class="py-12 text-center text-zinc-400 dark:text-zinc-500 italic text-sm">
                No ledger postings found matching the filter.
              </div>

              <div 
                v-for="tx in filteredTransactions" 
                :key="tx.id"
                class="flex items-center justify-between py-4 hover:bg-zinc-50/50 dark:hover:bg-white/5 rounded-2xl px-2 group transition-all"
              >
                <!-- Desc -->
                <div class="w-2/5 min-w-0 flex items-center gap-3">
                  <div class="p-2 shrink-0 rounded-xl" :class="tx.amount >= 0 ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'">
                    <TrendingUp v-if="tx.amount >= 0" class="w-3.5 h-3.5" />
                    <TrendingDown v-else class="w-3.5 h-3.5" />
                  </div>
                  <div class="min-w-0">
                    <p class="font-bold text-zinc-900 dark:text-white text-sm truncate">{{ tx.description }}</p>
                    <p v-if="tx.note" class="text-xs text-zinc-400 dark:text-zinc-500 italic mt-0.5 truncate">{{ tx.note }}</p>
                  </div>
                </div>

                <!-- Date -->
                <span class="w-1/4 text-xs font-mono text-zinc-500 dark:text-zinc-400">
                  {{ tx.date?.toDate ? tx.date.toDate().toLocaleDateString() : new Date(tx.date as any).toLocaleDateString() }}
                </span>

                <!-- Category -->
                <span class="w-1/5 text-xs font-semibold text-zinc-400 max-w-[120px] truncate uppercase tracking-wider font-mono">
                  {{ tx.category }}
                </span>

                <!-- Amount & Delete -->
                <div class="w-1/6 flex items-center justify-end gap-1.5 shrink-0">
                  <span class="font-bold font-mono text-sm whitespace-nowrap" :class="tx.amount >= 0 ? 'text-emerald-500' : 'text-zinc-900 dark:text-white'">
                    {{ tx.amount >= 0 ? '+' : '' }}{{ formatCurrency(tx.amount, group?.currencyCode || 'USD') }}
                  </span>
                  
                  <button 
                    @click.stop="handleOpenEditTransaction(tx)"
                    class="p-1 text-zinc-400 hover:text-indigo-400 hover:bg-indigo-550/15 dark:hover:bg-indigo-500/20 rounded-lg transition-colors border-none bg-transparent opacity-0 group-hover:opacity-100 cursor-pointer"
                    title="Edit Entry"
                  >
                    <Pencil class="w-4 h-4" />
                  </button>

                  <button 
                    @click.stop="handleDeleteTransaction(tx)"
                    class="p-1 text-zinc-450 hover:text-rose-400 hover:bg-rose-500/15 dark:hover:bg-rose-500/20 rounded-lg transition-colors border-none bg-transparent opacity-0 group-hover:opacity-100 cursor-pointer"
                    title="Remove Entry"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div-table>
          </div>
        </div>

        <!-- Analytics tab content -->
        <div v-if="activeTab === 'analytics'" class="space-y-6">
          <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[32px] p-6 shadow-sm">
            <h4 class="font-bold text-zinc-900 dark:text-white mb-6 flex items-center gap-2 text-sm font-display uppercase tracking-wider">
              <PieChart class="w-4 h-4 text-teal-600" /> Expense Allocation by Category
            </h4>

            <div v-if="categoryBreakdown.length === 0" class="py-12 text-center text-zinc-400 italic text-sm">
              Deploy card postings to track dynamic categorical spending metrics.
            </div>

            <div v-else class="space-y-5">
              <div v-for="item in categoryBreakdown" :key="item.category" class="space-y-1.5">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-bold text-zinc-650 dark:text-zinc-300 uppercase tracking-wide font-mono">{{ item.category }}</span>
                  <div class="flex items-center gap-2 font-mono">
                    <span class="font-semibold text-zinc-400">({{ item.percent.toFixed(0) }}%)</span>
                    <span class="font-bold text-zinc-900 dark:text-white">{{ formatCurrency(item.value, group?.currencyCode || 'USD') }}</span>
                  </div>
                </div>
                <div class="w-full bg-zinc-100 dark:bg-white/5 h-2 rounded-full overflow-hidden">
                  <div class="h-full bg-teal-500 rounded-full" :style="`width: ${item.percent}%`" />
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

    </div>

    <!-- Modals -->

    <!-- Add Transaction Modal -->
    <transition name="fade">
      <div v-if="isAddTransactionOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddTransactionOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />

        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-[32px] shadow-2xl overflow-y-auto max-h-[90vh] z-10 transition-all">
          <div class="p-8">
            <div class="flex items-center justify-between mb-8">
              <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">New Ledger Posting</h3>
              <button @click="isAddTransactionOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl transition-colors text-zinc-455 bg-transparent border-none cursor-pointer">
                <X class="w-6 h-6" />
              </button>
            </div>

            <form @submit.prevent="handleAddTransaction" class="space-y-6">
              <!-- Type -->
              <div class="grid grid-cols-2 gap-4 bg-zinc-50 dark:bg-zinc-950 p-1 rounded-2xl border border-zinc-150 dark:border-white/5">
                <button
                  type="button"
                  @click="txType = 'expense'"
                  class="py-3 text-xs font-bold rounded-xl transition-all border-none cursor-pointer"
                  :class="txType === 'expense' ? 'bg-white dark:bg-zinc-900 text-rose-500 shadow-sm' : 'text-zinc-500 bg-transparent'"
                >
                  Charge / expense
                </button>
                <button
                  type="button"
                  @click="txType = 'deposit'"
                  class="py-3 text-xs font-bold rounded-xl transition-all border-none cursor-pointer"
                  :class="txType === 'deposit' ? 'bg-white dark:bg-zinc-900 text-emerald-500 shadow-sm' : 'text-zinc-500 bg-transparent'"
                >
                  Payment / deposit
                </button>
              </div>

              <!-- Amount & Desc -->
              <div class="space-y-4">
                <div>
                  <label for="tx-amount" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Posting Amount</label>
                  <input
                    id="tx-amount"
                    type="number"
                    step="0.01"
                    v-model="txAmount"
                    placeholder="0.00"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label for="tx-desc" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Merchant / Description</label>
                  <input
                    id="tx-desc"
                    type="text"
                    v-model="txDescription"
                    placeholder="e.g. Starbucks, Amazon, Rent payment"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                    required
                  />
                </div>
              </div>

              <!-- Date & Category -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label for="tx-date" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Posting Date</label>
                  <input
                    id="tx-date"
                    type="date"
                    v-model="txDate"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                    required
                  />
                </div>
                <div>
                  <label for="tx-cat" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Category</label>
                  <select
                    id="tx-cat"
                    v-model="txCategory"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                  >
                    <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                  </select>
                </div>
              </div>

              <!-- Note -->
              <div>
                <label for="tx-note" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Notes (Optional)</label>
                <input
                  id="tx-note"
                  type="text"
                  v-model="txNote"
                  placeholder="Additional receipt notes"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-medium text-zinc-900 dark:text-white"
                />
              </div>

              <button
                type="submit"
                class="w-full py-4.5 bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-2xl font-bold font-display text-xs transition-all tracking-wider shadow-lg shadow-indigo-500/20 cursor-pointer border-none mt-4 uppercase outline-none focus:ring-4 focus:ring-indigo-500/40"
              >
                Post Ledger Entry
              </button>
            </form>
          </div>
        </div>
      </div>
    </transition>

    <!-- Edit Transaction Modal -->
    <transition name="fade">
      <div v-if="isEditTransactionOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isEditTransactionOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />

        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-[32px] shadow-2xl overflow-y-auto max-h-[90vh] z-10 transition-all">
          <div class="p-8">
            <div class="flex items-center justify-between mb-8">
              <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Ledger Posting</h3>
              <button @click="isEditTransactionOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl transition-colors text-zinc-455 bg-transparent border-none cursor-pointer">
                <X class="w-6 h-6" />
              </button>
            </div>

            <form @submit.prevent="handleUpdateTransaction" class="space-y-6">
              <!-- Type -->
              <div class="grid grid-cols-2 gap-4 bg-zinc-50 dark:bg-zinc-950 p-1 rounded-2xl border border-zinc-150 dark:border-white/5">
                <button
                  type="button"
                  @click="editTxType = 'expense'"
                  class="py-3 text-xs font-bold rounded-xl transition-all border-none cursor-pointer"
                  :class="editTxType === 'expense' ? 'bg-white dark:bg-zinc-900 text-rose-500 shadow-sm' : 'text-zinc-500 bg-transparent'"
                >
                  Charge / expense
                </button>
                <button
                  type="button"
                  @click="editTxType = 'deposit'"
                  class="py-3 text-xs font-bold rounded-xl transition-all border-none cursor-pointer"
                  :class="editTxType === 'deposit' ? 'bg-white dark:bg-zinc-900 text-emerald-500 shadow-sm' : 'text-zinc-500 bg-transparent'"
                >
                  Payment / deposit
                </button>
              </div>

              <!-- Amount & Desc -->
              <div class="space-y-4">
                <div>
                  <label for="edit-tx-amount" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Posting Amount</label>
                  <input
                    id="edit-tx-amount"
                    type="number"
                    step="0.01"
                    v-model="editTxAmount"
                    placeholder="0.00"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                    required
                  />
                </div>

                <div>
                  <label for="edit-tx-desc" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Merchant / Description</label>
                  <input
                    id="edit-tx-desc"
                    type="text"
                    v-model="editTxDescription"
                    placeholder="e.g. Starbucks, Amazon"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                    required
                  />
                </div>
              </div>

              <!-- Date & Category -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label for="edit-tx-date" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Posting Date</label>
                  <input
                    id="edit-tx-date"
                    type="date"
                    v-model="editTxDate"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                    required
                  />
                </div>
                <div>
                  <label for="edit-tx-cat" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Category</label>
                  <select
                    id="edit-tx-cat"
                    v-model="editTxCategory"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                  >
                    <option v-for="cat in categories" :key="cat" :value="cat">{{ cat }}</option>
                  </select>
                </div>
              </div>

              <!-- Note -->
              <div>
                <label for="edit-tx-note" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Notes (Optional)</label>
                <input
                  id="edit-tx-note"
                  type="text"
                  v-model="editTxNote"
                  placeholder="Additional receipt notes"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-medium text-zinc-900 dark:text-white"
                />
              </div>

              <button
                type="submit"
                class="w-full py-4.5 bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-2xl font-bold font-display text-xs transition-all tracking-wider shadow-lg shadow-indigo-500/20 cursor-pointer border-none mt-4 uppercase outline-none focus:ring-4 focus:ring-indigo-500/40"
              >
                Save Changes
              </button>
            </form>
          </div>
        </div>
      </div>
    </transition>

    <!-- Transfer Funds Modal -->
    <transition name="fade">
      <div v-if="isTransferOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isTransferOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />

        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-[32px] shadow-2xl overflow-y-auto max-h-[90vh] z-10 transition-all">
          <div class="p-8">
            <div class="flex items-center justify-between mb-8">
              <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Fund Transfer Setup</h3>
              <button @click="isTransferOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl transition-colors text-zinc-455 bg-transparent border-none cursor-pointer">
                <X class="w-6 h-6" />
              </button>
            </div>

            <form @submit.prevent="handleTransfer" class="space-y-6">
              <!-- Source (Fixed to this account page) -->
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Source Account</label>
                <div class="px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-150 dark:border-white/5 rounded-2xl font-bold text-zinc-600 dark:text-zinc-400">
                  {{ group?.name }} (Current)
                </div>
              </div>

              <!-- Destination Account selector -->
              <div>
                <label for="to-group-val" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Destination Account / Card</label>
                <select
                  id="to-group-val"
                  v-model="toGroupId"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                  required
                >
                  <option v-for="g in otherAccounts" :key="g.id" :value="g.id">{{ g.name }} ({{ g.bankName }})</option>
                </select>
              </div>

              <!-- Transfer Amount -->
              <div>
                <label for="tr-amount" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Transfer Amount</label>
                <input
                  id="tr-amount"
                  type="number"
                  step="0.01"
                  v-model="transferAmount"
                  placeholder="0.00"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                  required
                />
              </div>

              <!-- Date & Note -->
              <div class="grid grid-cols-1 gap-4">
                <div>
                  <label for="tr-date" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Transfer Date</label>
                  <input
                    id="tr-date"
                    type="date"
                    v-model="transferDate"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                    required
                  />
                </div>
                <div>
                  <label for="tr-note" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Notes / memo</label>
                  <input
                    id="tr-note"
                    type="text"
                    v-model="transferNote"
                    placeholder="e.g. Card payment, Savings contribution"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-medium text-zinc-900 dark:text-white"
                  />
                </div>
              </div>

              <button
                type="submit"
                class="w-full py-4.5 bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-2xl font-bold font-display text-xs transition-all tracking-wider shadow-lg shadow-indigo-500/20 cursor-pointer border-none mt-4 uppercase outline-none focus:ring-4 focus:ring-indigo-500/40"
              >
                Execute Secure Transfer
              </button>
            </form>
          </div>
        </div>
      </div>
    </transition>

    <!-- Account Configuration Modal (Settings) -->
    <transition name="fade">
      <div v-if="isSettingsOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isSettingsOpen = false" class="absolute inset-0 bg-zinc-950/65 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg bg-white dark:bg-[#0c1216] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display flex items-center gap-2">
              <Settings class="w-6 h-6 text-indigo-500" />
              Account Configuration
            </h3>
            <button @click="isSettingsOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer text-zinc-500 border-none bg-transparent">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateSettings" class="space-y-6">
            <div>
              <label for="edit-account-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Account Name</label>
              <input
                id="edit-account-name"
                v-model="editName"
                type="text"
                placeholder="e.g. Primary Checkings"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold text-zinc-900 dark:text-white"
                required
              />
            </div>

            <div>
              <label for="edit-bank-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Bank Name</label>
              <input
                id="edit-bank-name"
                v-model="editBankName"
                type="text"
                placeholder="e.g. Chase Bank, Fidelity"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold text-zinc-900 dark:text-white"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label for="edit-acct-type" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Account Type</label>
                <select
                  id="edit-acct-type"
                  v-model="editAccountType"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
                >
                  <option value="checking">Checking Account</option>
                  <option value="savings">Savings Account</option>
                  <option value="credit_card">Credit Card</option>
                  <option value="debit_card">Debit Card</option>
                </select>
              </div>

              <div>
                <label for="edit-currency" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Currency</label>
                <select
                  id="edit-currency"
                  v-model="editCurrencyCode"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }} ({{ c.symbol }})</option>
                </select>
              </div>
            </div>

            <div v-if="editAccountType === 'credit_card'">
              <label for="edit-limit" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Credit Limit</label>
              <div class="relative">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                  {{ getCurrencySymbol(editCurrencyCode) }}
                </span>
                <input
                  id="edit-limit"
                  type="number"
                  step="0.01"
                  v-model="editCreditLimit"
                  class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                  required
                />
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-3 font-display">Card Theme Color</label>
              <div class="flex items-center gap-3">
                <button
                  v-for="color in cardColors"
                  :key="color.id"
                  type="button"
                  @click="editColor = color.id"
                  class="w-10 h-10 rounded-full cursor-pointer transition-all border-4 relative"
                  :class="[
                    color.bg,
                    editColor === color.id ? 'border-indigo-500 scale-110 shadow-lg' : 'border-transparent hover:scale-105'
                  ]"
                >
                  <span v-if="editColor === color.id" class="absolute inset-0 flex items-center justify-center text-white text-[10px] font-bold">✓</span>
                </button>
              </div>
            </div>

            <div class="flex flex-col gap-3 pt-4">
              <button
                type="submit"
                class="w-full py-4.5 bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-2xl font-bold font-display text-xs transition-all tracking-wider shadow-lg shadow-indigo-500/20 active:scale-95 cursor-pointer border-none uppercase"
              >
                Apply Changes
              </button>

              <button
                type="button"
                @click="isSettingsOpen = false; isDeleteConfirmOpen = true"
                class="w-full py-4.5 bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 rounded-2xl font-bold hover:bg-rose-100 dark:hover:bg-rose-500/20 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer border border-transparent dark:border-rose-900/10 font-display text-xs tracking-wider uppercase"
              >
                <Trash2 class="w-4 h-4" />
                Deconstruct Account
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- Delete Group Confirmation Modal -->
    <transition name="fade">
      <div v-if="isDeleteConfirmOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div @click="isDeleteConfirmOpen = false" class="absolute inset-0 bg-black/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0c1216] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 text-center">
          <div class="w-16 h-16 bg-red-50 dark:bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6 text-red-500 dark:text-red-400 font-bold">
            <ShieldAlert class="w-8 h-8" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display mb-3">Deconstruct Account?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-8 leading-relaxed">
            This will permanently delete <span class="font-bold text-zinc-900 dark:text-white">"{{ group?.name }}"</span> and erase its transaction logs and historical ledger. This operation is absolute and cannot be undone.
          </p>
          <div class="flex items-center gap-4">
            <button
              @click="isDeleteConfirmOpen = false"
              type="button"
              class="flex-1 py-4.5 bg-zinc-100 dark:bg-white/5 text-zinc-700 dark:text-zinc-300 font-bold rounded-2xl border-none hover:bg-zinc-200 dark:hover:bg-white/10 transition-all active:scale-95 cursor-pointer text-xs uppercase"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteGroup"
              type="button"
              class="flex-1 py-4.5 bg-red-600 text-white font-bold rounded-2xl border-none hover:bg-red-700 transition-all active:scale-95 cursor-pointer shadow-lg shadow-red-500/20 text-xs uppercase"
            >
              Confirm Deconstruct
            </button>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<style scoped>
@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}
.animate-shimmer {
  transform: translateX(-100%);
  animation: shimmer 1.5s infinite;
}
</style>
