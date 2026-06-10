<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { db } from '../firebase';
import { collection, getDocs, query } from 'firebase/firestore';
import { 
  Building, 
  Plus, 
  ArrowUpRight, 
  ArrowDownLeft, 
  Coins, 
  Scale, 
  ChevronRight,
  ShieldCheck,
  Home,
  Percent
} from 'lucide-vue-next';
import { type Group, type Mortgage } from '../types';
import { formatCurrency } from '../utils/format';

const props = defineProps<{
  user: any;
  groups: Group[];
}>();

const emit = defineEmits<{
  (e: 'selectGroup', id: string): void;
}>();

const loading = ref(true);
const allMortgages = ref<Mortgage[]>([]);
const mortgagesGroupMap = ref<Map<string, Mortgage[]>>(new Map());

// Fetch mortgages for all groups belonging to the mortgages service
onMounted(async () => {
  try {
    const mortgageList: Mortgage[] = [];
    const groupMap = new Map<string, Mortgage[]>();

    for (const group of props.groups) {
      const q = query(collection(db, 'groups', group.id, 'mortgages'));
      const snapshot = await getDocs(q);
      const list = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      } as Mortgage));
      
      mortgageList.push(...list);
      groupMap.set(group.id, list);
    }

    allMortgages.value = mortgageList;
    mortgagesGroupMap.value = groupMap;
  } catch (error) {
    console.error("Error loading mortgage overview data:", error);
  } finally {
    loading.value = false;
  }
});

// Calculate metrics
const totalLentClaim = computed(() => {
  // Mortgages where we are the lender (giving the mortgage property)
  return allMortgages.value
    .filter(m => m.type === 'given' && m.status !== 'settled')
    .reduce((sum, m) => sum + m.amount, 0);
});

const totalBorrowedDebt = computed(() => {
  // Mortgages where we are the borrower (taking the property debt)
  return allMortgages.value
    .filter(m => m.type === 'taken' && m.status !== 'settled')
    .reduce((sum, m) => sum + m.amount, 0);
});

const netDebtPosition = computed(() => {
  return totalLentClaim.value - totalBorrowedDebt.value;
});

const activeClaimsCount = computed(() => {
  return allMortgages.value.filter(m => m.type === 'given' && m.status !== 'settled').length;
});

const activeDebtsCount = computed(() => {
  return allMortgages.value.filter(m => m.type === 'taken' && m.status !== 'settled').length;
});

const openCreateModal = () => {
  if ((window as any).openCreateGroupModal) {
    (window as any).openCreateGroupModal();
  }
};
</script>

<template>
  <div class="space-y-8" id="mortgages-hub-container">
    <!-- Header with title & Action Button -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-zinc-950 dark:text-white tracking-tight flex items-center gap-2.5 font-display">
          <Home class="w-8 h-8 text-indigo-500" />
          Property Mortgages
        </h1>
        <p class="text-xs text-zinc-500 dark:text-zinc-600 font-medium">
          Durable Cloud Ledger designed for collateral-backed properties, liens, and long-term amortizations.
        </p>
      </div>

      <button 
        @click="openCreateModal"
        class="inline-flex items-center gap-2 px-5 py-3.5 bg-gradient-to-br from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-2xl font-bold text-xs transition-all shadow-xl shadow-indigo-500/10 hover:shadow-indigo-500/20 cursor-pointer"
      >
        <Plus class="w-4 h-4" />
        Initialize Mortgage Broker
      </button>
    </div>

    <!-- Active Statistics Dashboard Grid -->
    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-3 gap-6" id="mortgages-stats-grid">
      <!-- Lent Claim / Receivables Card -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <ArrowUpRight class="w-24 h-24 text-emerald-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">LENT BY ME / COLLATERAL CLAIMS</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-2xl font-black tracking-tight text-emerald-600 dark:text-emerald-400 font-mono">
            {{ formatCurrency(totalLentClaim, 'USD') }}
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <ShieldCheck class="w-4 h-4 text-emerald-500" />
          <span>{{ activeClaimsCount }} Active Claim ledgers</span>
        </div>
      </div>

      <!-- Borrowed Debt / Payables Card -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <ArrowDownLeft class="w-24 h-24 text-rose-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">BORROWED BY ME / LIABILITIES</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-2xl font-black tracking-tight text-rose-600 dark:text-rose-400 font-mono">
            {{ formatCurrency(totalBorrowedDebt, 'USD') }}
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <Building class="w-4 h-4 text-[#005a5b] dark:text-teal-400" />
          <span>{{ activeDebtsCount }} Properties mortgaged</span>
        </div>
      </div>

      <!-- Net Debt balance position -->
      <div :class="`p-6 border rounded-[28px] relative overflow-hidden shadow-sm transition-all duration-300 ${
        netDebtPosition >= 0 
          ? 'bg-gradient-to-br from-indigo-50/50 to-emerald-50/20 dark:from-indigo-550/5 dark:to-zinc-950 border-indigo-150 dark:border-indigo-500/15'
          : 'bg-gradient-to-br from-rose-50/30 to-zinc-50 dark:from-rose-500/5 dark:to-zinc-950 border-rose-150 dark:border-rose-500/15'
      }`">
        <p class="text-[10px] font-bold text-indigo-500/80 dark:text-[#005a5b] uppercase tracking-wider mb-2 font-display">NET MORTGAGE PORTFOLIO</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span :class="`text-2xl font-black tracking-tight font-mono ${netDebtPosition >= 0 ? 'text-indigo-600 dark:text-indigo-400' : 'text-rose-600 dark:text-rose-400'}`">
            {{ formatCurrency(netDebtPosition, 'USD') }}
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-200/40 dark:border-white/5">
          <Scale class="w-4 h-4 text-indigo-500" />
          <span>Balanced ledger clearing position</span>
        </div>
      </div>
    </div>

    <!-- Loading Spin Grid -->
    <div v-if="loading" class="flex items-center justify-center py-24">
      <div class="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    </div>

    <!-- Active Brokers / Groups List Grid -->
    <template v-else>
      <div v-if="groups.length === 0" class="py-24 text-center text-zinc-500 bg-white dark:bg-[#0b1219]/60 border border-zinc-250 dark:border-white/5 rounded-[32px] shadow-sm">
        <Building class="w-16 h-16 mx-auto text-zinc-300 dark:text-zinc-700 mb-5 animate-pulse" />
        <h3 class="font-extrabold text-zinc-950 dark:text-white text-lg tracking-tight mb-2 font-display">Assemble Mortgage Brokers</h3>
        <p class="text-xs text-zinc-550 dark:text-zinc-400 max-w-sm mx-auto leading-relaxed mb-6">
          Set up a secured property mortgages group, claim list, or amortization account. Let's start with your first ledger.
        </p>
        <button 
          @click="openCreateModal"
          class="inline-flex items-center gap-2 px-5 py-3.5 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 hover:bg-zinc-900 dark:hover:bg-zinc-100 rounded-xl font-bold text-xs transition-all shadow-md cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          Initialize First Broker
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="mortgages-groups-list">
        <div 
          v-for="group in groups" 
          :key="group.id" 
          @click="emit('selectGroup', group.id)"
          class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] hover:border-indigo-500 dark:hover:border-indigo-500/40 transition-all duration-300 shadow-sm cursor-pointer group flex flex-col justify-between h-[190px]"
        >
          <div>
            <div class="flex items-center justify-between mb-4">
              <span class="text-[9px] font-black uppercase tracking-wider bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 px-3 py-1 rounded-full">
                {{ group.currencyCode || 'USD' }} Broker
              </span>
              <ChevronRight class="w-4 h-4 text-zinc-400 group-hover:text-indigo-500 transition-colors" />
            </div>

            <h3 class="text-base font-black text-zinc-950 dark:text-white group-hover:text-indigo-500 transition-colors tracking-tight line-clamp-1 text-left font-display">
              {{ group.name }}
            </h3>
            <p v-if="group.description" class="text-[11px] text-zinc-400 dark:text-zinc-500 line-clamp-2 mt-1 leading-relaxed text-left">
              {{ group.description }}
            </p>
            <p v-else class="text-[11px] text-zinc-400 dark:text-zinc-600 italic mt-1 text-left">
              No description/notes setup.
            </p>
          </div>

          <div class="pt-4 border-t border-zinc-100 dark:border-white/5 flex items-center justify-between text-xs text-zinc-400">
            <span class="font-medium">Total Collaterals</span>
            <span class="font-bold text-zinc-950 dark:text-white font-mono">
              {{ mortgagesGroupMap.get(group.id)?.length || 0 }} assets
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
