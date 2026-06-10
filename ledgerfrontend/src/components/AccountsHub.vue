<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  CreditCard, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Plus, 
  Trash2, 
  ChevronRight, 
  Building2, 
  PiggyBank, 
  Wallet,
  AlertTriangle,
  History,
  ShieldCheck,
  TrendingUp as ArrowUpRight,
  Pencil,
  X
} from 'lucide-vue-next';
import { type Group, type AccountTransaction } from '../types';
import { db } from '../firebase';
import { collection, query, onSnapshot, orderBy, doc, deleteDoc, setDoc, updateDoc } from 'firebase/firestore';
import { formatCurrency } from '../utils/format';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { getCurrencySymbol, CURRENCIES, convertCurrency } from '../utils/currency';

const props = defineProps<{
  user: any;
  groups: Group[];
}>();

const emit = defineEmits<{
  (e: 'selectGroup', id: string): void;
}>();

const recentTransactions = ref<(AccountTransaction & { accountName: string; groupName: string })[]>([]);
const unsubscribes = ref<(() => void)[]>([]);

const cardColors = [
  { id: 'slate', name: 'Midnight Graphite', bg: 'bg-gradient-to-br from-zinc-800 via-zinc-900 to-black', text: 'text-zinc-100', accent: 'border-zinc-700' },
  { id: 'indigo', name: 'Royal Sapphire', bg: 'bg-gradient-to-br from-indigo-700 via-violet-700 to-indigo-950', text: 'text-white', accent: 'border-indigo-500/30' },
  { id: 'emerald', name: 'Emerald Velvet', bg: 'bg-gradient-to-br from-teal-600 via-emerald-700 to-teal-950', text: 'text-emerald-50', accent: 'border-teal-500/30' },
  { id: 'rose', name: 'Rose Gold', bg: 'bg-gradient-to-br from-rose-600 via-pink-700 to-red-950', text: 'text-white', accent: 'border-rose-500/30' },
  { id: 'amber', name: 'Golden Amber', bg: 'bg-gradient-to-br from-amber-500 via-orange-600 to-yellow-950', text: 'text-amber-50', accent: 'border-amber-500/30' }
];

// Computed list of Direct Accounts/Cards from Groups
const accountGroups = computed(() => {
  return props.groups.filter(g => g.service === 'accounts');
});

// Dynamic calculations directly from Account Groups
const totalAssetBalance = computed(() => {
  return accountGroups.value
    .filter(g => g.accountType !== 'credit_card')
    .reduce((sum, g) => sum + convertCurrency(parseFloat(g.balance as any) || 0, g.currencyCode || 'USD', props.user?.defaultCurrency || 'USD'), 0);
});

const totalCreditBalance = computed(() => {
  return accountGroups.value
    .filter(g => g.accountType === 'credit_card')
    .reduce((sum, g) => sum + convertCurrency(parseFloat(g.balance as any) || 0, g.currencyCode || 'USD', props.user?.defaultCurrency || 'USD'), 0);
});

const totalCreditLimit = computed(() => {
  return accountGroups.value
    .filter(g => g.accountType === 'credit_card')
    .reduce((sum, g) => sum + convertCurrency(parseFloat(g.creditLimit as any) || 0, g.currencyCode || 'USD', props.user?.defaultCurrency || 'USD'), 0);
});

const totalBalance = computed(() => {
  return totalAssetBalance.value - totalCreditBalance.value;
});

const creditUtilization = computed(() => {
  if (totalCreditLimit.value > 0) {
    return Math.min((totalCreditBalance.value / totalCreditLimit.value) * 100, 100);
  }
  return 0;
});

// Realtime subscriptions for recent transactions
const setupSubscriptions = () => {
  unsubscribes.value.forEach(unsub => unsub());
  unsubscribes.value = [];

  const tempTransactions = ref<Map<string, (AccountTransaction & { accountName: string; groupName: string })[]>>(new Map());

  if (accountGroups.value.length === 0) {
    recentTransactions.value = [];
    return;
  }

  accountGroups.value.forEach(group => {
    const q = query(
      collection(db, 'groups', group.id, 'account_transactions'),
      orderBy('createdAt', 'desc')
    );

    const unsub = onSnapshot(q, (snap) => {
      const list = snap.docs.map(doc => {
        const data = doc.data();
        let resolvedDate = data.date;
        if (typeof resolvedDate === 'string') {
          resolvedDate = { toMillis: () => Date.parse(resolvedDate), toDate: () => new Date(resolvedDate) };
        }
        return {
          id: doc.id,
          accountName: group.name,
          groupName: group.name,
          ...data,
          date: resolvedDate
        } as AccountTransaction & { accountName: string; groupName: string };
      });

      tempTransactions.value.set(group.id, list);
      rebuildTransactions();
    }, () => {
      // ignore missing permissions errors during setup
    });

    unsubscribes.value.push(unsub);
  });

  const rebuildTransactions = () => {
    const flattened: (AccountTransaction & { accountName: string; groupName: string })[] = [];
    tempTransactions.value.forEach(list => flattened.push(...list));

    // Sort globally by date
    flattened.sort((a, b) => {
      const tA = a.createdAt?.seconds ? a.createdAt.seconds * 1000 : (a.date?.toMillis ? a.date.toMillis() : 0);
      const tB = b.createdAt?.seconds ? b.createdAt.seconds * 1000 : (b.date?.toMillis ? b.date.toMillis() : 0);
      return tB - tA;
    });

    recentTransactions.value = flattened.slice(0, 7);
  };
};

onMounted(() => {
  setupSubscriptions();
});

watch(() => props.groups, () => {
  setupSubscriptions();
}, { deep: true });

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

const triggerCreateAccount = () => {
  if (typeof (window as any).openCreateGroupModal === 'function') {
    (window as any).openCreateGroupModal();
  }
};

const editingAccount = ref<Group | null>(null);
const editName = ref('');
const editBankName = ref('');
const editAccountType = ref<'checking' | 'savings' | 'credit_card' | 'debit_card'>('checking');
const editCreditLimit = ref('');
const editColor = ref('slate');
const editCurrencyCode = ref('USD');

watch(editingAccount, (newVal) => {
  if (newVal) {
    editName.value = newVal.name || '';
    editBankName.value = newVal.bankName || 'Generic Bank';
    editAccountType.value = newVal.accountType || 'checking';
    editCreditLimit.value = newVal.creditLimit?.toString() || '';
    editColor.value = newVal.color || 'slate';
    editCurrencyCode.value = newVal.currencyCode || 'USD';
  }
});

const handleUpdateAccount = async () => {
  if (!editingAccount.value || !editName.value.trim()) return;

  try {
    const updatedData = {
      name: editName.value.trim(),
      bankName: editBankName.value.trim() || 'Generic Bank',
      accountType: editAccountType.value,
      creditLimit: editAccountType.value === 'credit_card' ? (parseFloat(editCreditLimit.value) || 0) : 0,
      color: editColor.value,
      currencyCode: editCurrencyCode.value
    };

    await updateDoc(doc(db, 'groups', editingAccount.value.id), updatedData);
    editingAccount.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/${editingAccount.value.id}`);
  }
};

const handleDeleteAccount = async (id: string, name: string) => {
  if (!confirm(`Are you sure you want to permanently delete '${name}'? This deconstructs the ledger collection.`)) return;
  try {
    await deleteDoc(doc(db, 'groups', id));
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, 'groups');
  }
};

const getCardStyle = (colorId: string | undefined) => {
  const cfg = cardColors.find(c => c.id === colorId) || cardColors[0];
  return `${cfg.bg} ${cfg.text} border ${cfg.accent}`;
};
</script>

<template>
  <div class="space-y-10">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-2">
      <div>
        <div class="flex items-center gap-3 mb-2">
          <div class="p-2 bg-gradient-to-br from-teal-500/10 to-emerald-500/10 dark:from-teal-500/20 dark:to-emerald-500/20 border border-teal-500/20 rounded-xl text-teal-600 dark:text-teal-400">
            <CreditCard class="w-5 h-5" />
          </div>
          <span class="text-xs font-bold uppercase tracking-widest text-[#005253] dark:text-teal-400 font-display">Financial Assets</span>
        </div>
        <h1 class="text-3xl sm:text-4xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Direct Accounts & Cards</h1>
        <p class="text-zinc-500 dark:text-zinc-400 mt-1 text-sm font-sans">Streamlined visual credit cards, debit cards, checking and savings ledger targets.</p>
      </div>

      <div>
        <button
          @click="triggerCreateAccount"
          class="px-6 py-4 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 hover:opacity-90 rounded-2xl font-bold text-xs transition-all flex items-center gap-2 cursor-pointer border-none shadow-lg shadow-zinc-950/10 dark:shadow-white/5 active:scale-98"
        >
          <Plus class="w-4 h-4" /> Setup Account or Card
        </button>
      </div>
    </div>

    <!-- KPI Bento List -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      
      <!-- Net Worth -->
      <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-3xl p-6 shadow-sm relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-indigo-500/5 rounded-full blur-2xl transform translate-x-8 -translate-y-8 pointer-events-none" />
        <div class="flex items-center justify-between mb-4">
          <span class="text-[10px] font-bold uppercase text-zinc-400 dark:text-zinc-500 tracking-widest font-display">Combined Assets</span>
          <div class="p-2.5 bg-indigo-50 dark:bg-indigo-500/10 rounded-xl text-indigo-600 dark:text-indigo-400">
            <Wallet class="w-4 h-4" />
          </div>
        </div>
        <p class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-mono mb-1.5">
          {{ formatCurrency(totalBalance, user?.defaultCurrency || 'USD') }}
        </p>
        <span class="text-xs font-bold" :class="totalBalance >= 0 ? 'text-emerald-500' : 'text-rose-500'">
          {{ totalBalance >= 0 ? 'Positive Ledger Worth' : 'Net Liable Deficit' }}
        </span>
      </div>

      <!-- Liquid Cash Reserves -->
      <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-3xl p-6 shadow-sm relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-2xl transform translate-x-8 -translate-y-8 pointer-events-none" />
        <div class="flex items-center justify-between mb-4">
          <span class="text-[10px] font-bold uppercase text-zinc-400 dark:text-zinc-500 tracking-widest font-display">Cash / Bank Reserves</span>
          <div class="p-2.5 bg-emerald-50 dark:bg-emerald-500/10 rounded-xl text-emerald-600 dark:text-emerald-400">
            <PiggyBank class="w-4 h-4" />
          </div>
        </div>
        <p class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-mono mb-1.5">
          {{ formatCurrency(totalAssetBalance, user?.defaultCurrency || 'USD') }}
        </p>
        <span class="text-xs text-zinc-400 dark:text-zinc-500 font-medium">Liquid checking & savings</span>
      </div>

      <!-- Outstanding Credit Balance -->
      <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-3xl p-6 shadow-sm relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-rose-500/5 rounded-full blur-2xl transform translate-x-8 -translate-y-8 pointer-events-none" />
        <div class="flex items-center justify-between mb-4">
          <span class="text-[10px] font-bold uppercase text-zinc-400 dark:text-zinc-500 tracking-widest font-display">Credit Outstanding</span>
          <div class="p-2.5 bg-rose-50 dark:bg-rose-500/10 rounded-xl text-rose-600 dark:text-rose-400">
            <CreditCard class="w-4 h-4" />
          </div>
        </div>
        <p class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-mono mb-1.5">
          {{ formatCurrency(totalCreditBalance, user?.defaultCurrency || 'USD') }}
        </p>
        <span class="text-xs text-zinc-400 dark:text-zinc-500 font-medium">Total outstanding charges</span>
      </div>

      <!-- Credit utilization -->
      <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-3xl p-6 shadow-sm relative overflow-hidden">
        <div class="absolute top-0 right-0 w-32 h-32 bg-amber-500/5 rounded-full blur-2xl transform translate-x-8 -translate-y-8 pointer-events-none" />
        <div class="flex items-center justify-between mb-4">
          <span class="text-[10px] font-bold uppercase text-zinc-400 dark:text-zinc-500 tracking-widest font-display">Credit Util. Rate</span>
          <div class="p-2.5 bg-amber-50 dark:bg-amber-500/10 rounded-xl text-amber-600 dark:text-amber-400">
            <Building2 class="w-4 h-4" />
          </div>
        </div>
        <p class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-mono mb-1.5">
          {{ creditUtilization.toFixed(1) }}%
        </p>
        <div class="w-full bg-zinc-100 dark:bg-white/5 h-1.5 rounded-full overflow-hidden">
          <div 
            class="h-full transition-all duration-300"
            :class="creditUtilization > 30 ? 'bg-rose-500' : 'bg-emerald-500'"
            :style="`width: ${creditUtilization}%`"
          />
        </div>
      </div>

    </div>

    <!-- Cards visual gallery -->
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-bold text-zinc-900 dark:text-white font-display">My Digital Wallet</h2>
          <p class="text-xs text-zinc-400 dark:text-zinc-500">Click arrow on any account or card to open its transaction ledger.</p>
        </div>
        <span class="text-xs font-mono px-3 py-1 bg-zinc-100 dark:bg-white/5 text-zinc-500 dark:text-zinc-400 rounded-full font-bold">
          {{ accountGroups.length }} Active accounts
        </span>
      </div>

      <!-- Empty state -->
      <div v-if="accountGroups.length === 0" class="flex flex-col items-center justify-center p-16 bg-white dark:bg-[#0d151a] border border-dashed border-zinc-200 dark:border-white/5 rounded-[40px] text-center">
        <div class="w-16 h-16 bg-zinc-50 dark:bg-white/5 rounded-3xl flex items-center justify-center mb-6 border border-zinc-100 dark:border-white/10 shrink-0">
          <CreditCard class="w-8 h-8 text-zinc-400 dark:text-zinc-500" />
        </div>
        <h3 class="text-lg font-bold text-zinc-900 dark:text-white mb-2 font-display">No Accounts Configured Yet</h3>
        <p class="text-zinc-500 dark:text-zinc-500 max-w-sm mb-6 text-sm font-sans leading-relaxed">Avoid complex groupings! Set up individual Checking, Savings, Debit or Credit cards directly connected with secure local ledgers.</p>
        <button
          @click="triggerCreateAccount"
          class="px-6 py-4 bg-zinc-900 dark:bg-white text-white dark:text-zinc-900 rounded-2xl text-xs font-bold font-display hover:opacity-90 active:scale-95 transition-all outline-none border-none cursor-pointer"
        >
          Setup First Account
        </button>
      </div>

      <!-- Card List -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div 
          v-for="account in accountGroups" 
          :key="account.id"
          @click="emit('selectGroup', account.id)"
          class="p-7 rounded-[32px] overflow-hidden shadow-xl min-h-[220px] flex flex-col justify-between transition-all duration-300 hover:scale-[1.02] hover:-translate-y-1 cursor-pointer group relative border-none"
          :class="getCardStyle(account.color)"
        >
          <!-- Shiny holographic glaze -->
          <div class="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:animate-shimmer pointer-events-none" />

          <!-- Header -->
          <div class="flex items-start justify-between">
            <div>
              <p class="text-[9px] font-bold tracking-widest uppercase opacity-60 font-mono mb-1 leading-none">
                {{ account.bankName || 'Direct Asset' }}
              </p>
              <h3 class="text-xl font-bold leading-tight font-sans tracking-tight">{{ account.name }}</h3>
            </div>
            <div class="px-3 py-1.5 bg-black/15 dark:bg-black/30 rounded-xl text-[10px] font-bold font-mono tracking-wider opacity-90">
              <span v-if="account.accountType === 'checking'">CHECKING</span>
              <span v-else-if="account.accountType === 'savings'">SAVINGS</span>
              <span v-else-if="account.accountType === 'credit_card'">CREDIT</span>
              <span v-else-if="account.accountType === 'debit_card'">DEBIT</span>
              <span v-else class="uppercase">{{ account.accountType || 'CASH' }}</span>
            </div>
          </div>

          <!-- Microchip & Account Number -->
          <div class="flex items-center gap-4 py-4">
            <div class="w-9 h-7 bg-amber-400/35 border border-amber-300/30 rounded-md relative shadow-inner overflow-hidden shrink-0">
              <div class="absolute left-1.5 top-0 h-full w-[1px] bg-white/20" />
              <div class="absolute left-3 top-0 h-full w-[1px] bg-white/20" />
              <div class="absolute left-4.5 top-0 h-full w-[1px] bg-white/20" />
              <div class="absolute top-1.5 left-0 w-full h-[1px] bg-white/20" />
              <div class="absolute top-3.5 left-0 w-full h-[1px] bg-white/20" />
              <div class="absolute top-5 left-0 w-full h-[1px] bg-white/20" />
            </div>
            <p class="font-mono text-sm tracking-widest opacity-80">{{ account.cardNumber || '•••• •••• •••• 8888' }}</p>
          </div>

          <!-- Footer -->
          <div class="pt-4 border-t border-white/10 flex items-end justify-between">
            <div>
              <p class="text-[8px] font-bold uppercase tracking-wider opacity-60 leading-none mb-1.5 font-mono">
                {{ account.accountType === 'credit_card' ? 'Outstanding Charges' : 'Asset Balance' }}
              </p>
              <p class="text-2xl font-bold font-mono tracking-tight leading-none">
                {{ formatCurrency(account.balance || 0, account.currencyCode || user?.defaultCurrency || 'USD') }}
              </p>
            </div>

            <!-- Controls -->
            <div class="flex items-center gap-1">
              <button 
                @click.stop="editingAccount = account"
                class="p-2 rounded-xl text-white/50 hover:text-indigo-300 hover:bg-white/10 transition-all border-none bg-transparent cursor-pointer"
                title="Configure Account"
              >
                <Pencil class="w-4 h-4" />
              </button>
              <button 
                @click.stop="handleDeleteAccount(account.id, account.name)"
                class="p-2 rounded-xl text-white/50 hover:text-rose-400 hover:bg-white/10 transition-all border-none bg-transparent cursor-pointer"
                title="Deconstruct Account"
              >
                <Trash2 class="w-4 h-4" />
              </button>
              <div 
                class="p-2.5 bg-white/10 hover:bg-white/20 text-white rounded-xl transition-all flex items-center justify-center border-none"
              >
                <ChevronRight class="w-4 h-4" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Ledger overview recent transactions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <!-- Recent transactions feed -->
      <div class="lg:col-span-2 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold text-zinc-900 dark:text-white font-display">Recent Global Transactions</h2>
          <div class="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500 font-mono">
            <History class="w-3.5 h-3.5" />
            <span>Unified transaction log</span>
          </div>
        </div>

        <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[32px] p-6 shadow-sm">
          <div v-if="recentTransactions.length === 0" class="py-12 text-center text-zinc-400 dark:text-zinc-500 italic text-sm">
            No transactions posted yet in your accounts.
          </div>
          <div v-else class="divide-y divide-zinc-100 dark:divide-white/5">
            <div 
              v-for="tx in recentTransactions" 
              :key="tx.id"
              class="flex items-center justify-between py-4 hover:bg-zinc-50/50 dark:hover:bg-white/5 -mx-4 px-4 rounded-2xl transition-all"
            >
              <div class="flex items-center gap-4 min-w-0">
                <div class="p-3 rounded-2xl text-xs shrink-0 font-bold" :class="tx.amount >= 0 ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400'">
                  <TrendingUp v-if="tx.amount >= 0" class="w-4 h-4" />
                  <TrendingDown v-else class="w-4 h-4" />
                </div>
                <div class="min-w-0">
                  <p class="font-bold text-zinc-900 dark:text-white text-sm truncate">{{ tx.description }}</p>
                  <p class="text-xs text-zinc-400 dark:text-zinc-500 font-bold font-mono mt-0.5 truncate uppercase">
                    {{ tx.accountName }} &bull; {{ tx.category }}
                  </p>
                </div>
              </div>

              <div class="text-right shrink-0">
                <p class="font-bold font-mono text-sm" :class="tx.amount >= 0 ? 'text-emerald-500' : 'text-zinc-900 dark:text-white'">
                  {{ tx.amount >= 0 ? '+' : '' }}{{ formatCurrency(tx.amount, user?.defaultCurrency || 'USD') }}
                </p>
                <span class="text-[9px] text-zinc-400 dark:text-zinc-500 font-mono tracking-wider mt-0.5 block uppercase">
                  {{ tx.type }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Credit Guidance panel -->
      <div class="space-y-6">
        <h2 class="text-xl font-bold text-zinc-900 dark:text-white font-display">Credit Util. Strategy</h2>
        <div class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[32px] p-6 shadow-sm space-y-6">
          <div class="flex items-start gap-4">
            <div class="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-2xl shrink-0 mt-0.5">
              <ShieldCheck class="w-5 h-5" />
            </div>
            <div>
              <h4 class="font-bold text-sm text-zinc-900 dark:text-white font-display">Keep utilization &lt; 30%</h4>
              <p class="text-xs text-zinc-500 dark:text-zinc-400 mt-1 font-sans leading-relaxed">
                Using less than 30% of your limit maintains a strong debt-to-credit ratio. Keep your credit card balances below limit targets.
              </p>
            </div>
          </div>

          <div class="pt-4 border-t border-zinc-100 dark:border-white/5 space-y-4">
            <div class="flex justify-between items-center text-xs">
              <span class="font-bold text-zinc-500 dark:text-zinc-400 font-display">Utilization Cap (30%)</span>
              <span class="font-semibold text-zinc-900 dark:text-white font-mono">
                {{ formatCurrency(totalCreditLimit * 0.3, user?.defaultCurrency || 'USD') }}
              </span>
            </div>
            <div class="flex justify-between items-center text-xs">
              <span class="font-bold text-zinc-500 dark:text-zinc-400 font-display">Current Utilization</span>
              <span class="font-bold text-zinc-900 dark:text-white font-mono" :class="creditUtilization > 30 ? 'text-rose-500' : 'text-emerald-500'">
                {{ formatCurrency(totalCreditBalance, user?.defaultCurrency || 'USD') }}
              </span>
            </div>
          </div>

          <!-- Quick alert advice status block -->
          <div 
            class="p-4 rounded-2xl text-xs font-medium font-sans flex items-center gap-2.5 leading-snug"
            :class="creditUtilization > 30 ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-700 dark:text-rose-400' : 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'"
          >
            <AlertTriangle v-if="creditUtilization > 30" class="w-4 h-4 shrink-0" />
            <ShieldCheck v-else class="w-4 h-4 shrink-0" />
            <span>
              {{ creditUtilization > 30 ? 'Caution: Credit utilization rate exceeds guidelines. Make payments to lower usage.' : 'Safe: Outstanding credit charges operate within healthy margins.' }}
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Edit Account Modal (Settings) -->
    <transition name="fade">
      <div v-if="editingAccount" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="editingAccount = null" class="absolute inset-0 bg-zinc-950/65 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg bg-white dark:bg-[#0c1216] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 text-left">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display flex items-center gap-2">
              <Pencil class="w-6 h-6 text-indigo-500" />
              Configure Account
            </h3>
            <button @click="editingAccount = null" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer text-zinc-500 border-none bg-transparent">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateAccount" class="space-y-6">
            <div>
              <label for="hub-edit-account-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Account Name</label>
              <input
                id="hub-edit-account-name"
                v-model="editName"
                type="text"
                placeholder="e.g. Primary Checkings"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold text-zinc-900 dark:text-white"
                required
              />
            </div>

            <div>
              <label for="hub-edit-bank-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Bank Name</label>
              <input
                id="hub-edit-bank-name"
                v-model="editBankName"
                type="text"
                placeholder="e.g. Chase Bank, Fidelity"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold text-zinc-900 dark:text-white"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label for="hub-edit-acct-type" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Account Type</label>
                <select
                  id="hub-edit-acct-type"
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
                <label for="hub-edit-currency" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Currency</label>
                <select
                  id="hub-edit-currency"
                  v-model="editCurrencyCode"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-905 dark:text-white appearance-none cursor-pointer"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }} ({{ c.symbol }})</option>
                </select>
              </div>
            </div>

            <div v-if="editAccountType === 'credit_card'">
              <label for="hub-edit-limit" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Credit Limit</label>
              <div class="relative">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                  {{ getCurrencySymbol(editCurrencyCode) }}
                </span>
                <input
                  id="hub-edit-limit"
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

            <div class="flex items-center gap-4 pt-4">
              <button
                @click="editingAccount = null"
                type="button"
                class="flex-1 py-4.5 bg-zinc-100 dark:bg-white/5 text-zinc-700 dark:text-zinc-300 font-bold rounded-2xl border-none hover:bg-zinc-200 dark:hover:bg-white/10 transition-all active:scale-95 cursor-pointer text-xs uppercase"
              >
                Cancel
              </button>
              <button
                type="submit"
                class="flex-1 py-4.5 bg-gradient-to-br from-indigo-500 to-violet-600 text-white font-bold rounded-2xl border-none hover:opacity-90 transition-all active:scale-95 cursor-pointer shadow-lg shadow-indigo-500/20 text-xs uppercase"
              >
                Apply Changes
              </button>
            </div>
          </form>
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
