<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { db } from '../firebase';
import { collection, getDocs, query } from 'firebase/firestore';
import { 
  Building, 
  Plus, 
  ArrowUpRight, 
  ArrowDownLeft, 
  ChevronRight,
  ShieldCheck,
  Home,
  Scale,
  KeyRound,
  FileText
} from 'lucide-vue-next';
import { type Group, type Rent } from '../types';
import { formatCurrency } from '../utils/format';

const props = defineProps<{
  user: any;
  groups: Group[];
}>();

const emit = defineEmits<{
  (e: 'selectGroup', id: string): void;
}>();

const loading = ref(true);
const allRents = ref<Rent[]>([]);
const rentsGroupMap = ref<Map<string, Rent[]>>(new Map());

// Fetch rent contracts for all groups belonging to the rent service
onMounted(async () => {
  try {
    const rentList: Rent[] = [];
    const groupMap = new Map<string, Rent[]>();

    for (const group of props.groups) {
      const q = query(collection(db, 'groups', group.id, 'rents'));
      const snapshot = await getDocs(q);
      const list = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      } as Rent));
      
      rentList.push(...list);
      groupMap.set(group.id, list);
    }

    allRents.value = rentList;
    rentsGroupMap.value = groupMap;
  } catch (error) {
    console.error("Error loading rent overview data:", error);
  } finally {
    loading.value = false;
  }
});

// Calculate metrics
const totalRentIncome = computed(() => {
  // Rent contracts where we receive rent (given/leased out)
  return allRents.value
    .filter(r => r.type === 'given' && r.status !== 'settled')
    .reduce((sum, r) => sum + r.amount, 0);
});

const totalRentExpense = computed(() => {
  // Rent contracts where we pay rent (taken/leased)
  return allRents.value
    .filter(r => r.type === 'taken' && r.status !== 'settled')
    .reduce((sum, r) => sum + r.amount, 0);
});

const netRentPosition = computed(() => {
  return totalRentIncome.value - totalRentExpense.value;
});

const activeLeasesCount = computed(() => {
  return allRents.value.filter(r => r.type === 'given' && r.status !== 'settled').length;
});

const activeOccupationsCount = computed(() => {
  return allRents.value.filter(r => r.type === 'taken' && r.status !== 'settled').length;
});

const openCreateModal = () => {
  if ((window as any).openCreateGroupModal) {
    (window as any).openCreateGroupModal();
  }
};
</script>

<template>
  <div class="space-y-8" id="rents-hub-container">
    <!-- Header with title & Action Button -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-zinc-950 dark:text-white tracking-tight flex items-center gap-2.5 font-display">
          <KeyRound class="w-8 h-8 text-teal-500" />
          Rent Management
        </h1>
        <p class="text-xs text-zinc-505 dark:text-zinc-650 font-medium">
          Durable Cloud Ledger designed for rent tracking, leases, and tenant/landlord cash installments.
        </p>
      </div>

      <button 
        @click="openCreateModal"
        class="inline-flex items-center gap-2 px-5 py-3.5 bg-gradient-to-br from-[#005a5b] to-teal-600 hover:from-[#004a4b] hover:to-teal-700 text-white rounded-2xl font-bold text-xs transition-all shadow-xl shadow-teal-500/10 hover:shadow-teal-500/20 cursor-pointer"
      >
        <Plus class="w-4 h-4" />
        Initialize Rent Ledger
      </button>
    </div>

    <!-- Active Statistics Dashboard Grid -->
    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-3 gap-6" id="rents-stats-grid">
      <!-- Rent Inflow (We Lease Out) -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <ArrowUpRight class="w-24 h-24 text-emerald-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">ESTIMATED RENT INFLOW (RECEIVABLES)</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-2xl font-black tracking-tight text-emerald-600 dark:text-emerald-400 font-mono">
            {{ formatCurrency(totalRentIncome, 'USD') }}<span class="text-xs font-bold text-zinc-400">/mo</span>
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <ShieldCheck class="w-4 h-4 text-emerald-500" />
          <span>{{ activeLeasesCount }} Active Leased contracts</span>
        </div>
      </div>

      <!-- Rent Outflow (We Occupy) -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <ArrowDownLeft class="w-24 h-24 text-rose-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">ESTIMATED RENT OUTFLOW (PAYABLES)</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-2xl font-black tracking-tight text-rose-600 dark:text-rose-450 font-mono">
            {{ formatCurrency(totalRentExpense, 'USD') }}<span class="text-xs font-bold text-zinc-400">/mo</span>
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <Building class="w-4 h-4 text-[#005a5b] dark:text-teal-400" />
          <span>{{ activeOccupationsCount }} Occupied properties</span>
        </div>
      </div>

      <!-- Net balance position -->
      <div :class="`p-6 border rounded-[28px] relative overflow-hidden shadow-sm transition-all duration-300 ${
        netRentPosition >= 0 
          ? 'bg-gradient-to-br from-teal-50/50 to-emerald-50/20 dark:from-teal-950/20 dark:to-zinc-950 border-teal-150 dark:border-teal-900/40'
          : 'bg-gradient-to-br from-rose-50/30 to-zinc-50 dark:from-rose-950/20 dark:to-zinc-950 border-rose-150 dark:border-rose-900/40'
      }`">
        <p class="text-[10px] font-bold text-teal-600/80 dark:text-teal-400 uppercase tracking-wider mb-2 font-display">NET RENTAL INDEX POSITION</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span :class="`text-2xl font-black tracking-tight font-mono ${netRentPosition >= 0 ? 'text-teal-600 dark:text-teal-450' : 'text-rose-600 dark:text-rose-450'}`">
            {{ formatCurrency(netRentPosition, 'USD') }}<span class="text-[10px] font-bold opacity-60">/mo</span>
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-550 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-200/40 dark:border-white/5">
          <Scale class="w-4 h-4 text-teal-500" />
          <span>Balanced rent clearing position</span>
        </div>
      </div>
    </div>

    <!-- Loading Spin Grid -->
    <div v-if="loading" class="flex items-center justify-center py-24">
      <div class="w-10 h-10 border-4 border-[#005a5b] border-t-transparent rounded-full animate-spin" />
    </div>

    <!-- Active Brokers / Groups List Grid -->
    <template v-else>
      <div v-if="groups.length === 0" class="py-24 text-center text-zinc-500 bg-white dark:bg-[#0b1219]/60 border border-zinc-250 dark:border-white/5 rounded-[32px] shadow-sm">
        <Building class="w-16 h-16 mx-auto text-zinc-300 dark:text-zinc-700 mb-5 animate-pulse" />
        <h3 class="font-extrabold text-zinc-950 dark:text-white text-lg tracking-tight mb-2 font-display">Configure Rent Ledgers</h3>
        <p class="text-xs text-zinc-550 dark:text-zinc-400 max-w-sm mx-auto leading-relaxed mb-6">
          Set up a rent management group, tenant payment log, or lease coordinator ledger.
        </p>
        <button 
          @click="openCreateModal"
          class="inline-flex items-center gap-2 px-5 py-3.5 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 hover:bg-zinc-900 dark:hover:bg-zinc-100 rounded-xl font-bold text-xs transition-all shadow-md cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          Initialize First Rent Ledger
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="rents-groups-list">
        <div 
          v-for="group in groups" 
          :key="group.id" 
          @click="emit('selectGroup', group.id)"
          class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] hover:border-teal-500 dark:hover:border-teal-500/40 transition-all duration-300 shadow-sm cursor-pointer group flex flex-col justify-between h-[190px]"
        >
          <div>
            <div class="flex items-center justify-between mb-4">
              <span class="text-[9px] font-black uppercase tracking-wider bg-teal-50/50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 px-3 py-1 rounded-full">
                {{ group.currencyCode || 'USD' }} Lease Ledger
              </span>
              <ChevronRight class="w-4 h-4 text-zinc-400 group-hover:text-teal-500 transition-colors" />
            </div>

            <h3 class="text-base font-black text-zinc-950 dark:text-white group-hover:text-teal-500 transition-colors tracking-tight line-clamp-1 text-left font-display">
              {{ group.name }}
            </h3>
            <p v-if="group.description" class="text-[11px] text-zinc-400 dark:text-zinc-500 line-clamp-2 mt-1 leading-relaxed text-left">
              {{ group.description }}
            </p>
            <p v-else class="text-[11px] text-zinc-400 dark:text-zinc-650 italic mt-1 text-left">
              No description/notes setup.
            </p>
          </div>

          <div class="pt-4 border-t border-zinc-100 dark:border-white/5 flex items-center justify-between text-xs text-zinc-400">
            <span class="font-medium flex items-center gap-1">
              <FileText class="w-3.5 h-3.5" />
              Leases
            </span>
            <span class="font-bold text-zinc-950 dark:text-white font-mono">
              {{ rentsGroupMap.get(group.id)?.length || 0 }} property agreements
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
