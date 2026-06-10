<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { 
  TrendingUp, 
  Banknote, 
  Coins, 
  Users, 
  ArrowRight,
  Plus,
  Calendar,
  Pencil,
  Trash2,
  Loader2,
  X,
  TrendingDown,
  CheckCircle2,
  ArrowUpRight
} from 'lucide-vue-next';
import { type Group, type IncomeTarget, type IncomeRecord } from '../types';
import { incomeCategories } from '../utils/categories';
import { db } from '../firebase';
import { collection, query, onSnapshot, orderBy, doc, updateDoc, deleteDoc, Timestamp } from 'firebase/firestore';
import { formatCurrency } from '../utils/format';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { convertCurrency, getCurrencySymbol, CURRENCIES } from '../utils/currency';

const props = defineProps<{
  user: any;
  groups: Group[];
}>();

const emit = defineEmits<{
  (e: 'selectGroup', id: string): void;
}>();

// Helper to convert rate
const getConvertedAmount = (amount: number, fromCurrency: string) => {
  return convertCurrency(amount, fromCurrency, props.user?.defaultCurrency || 'USD');
};

interface GroupIncomeData {
  groupId: string;
  groupName: string;
  groupType: string;
  targetsCount: number;
  totalTarget: number; // in default currency
  totalEarned: number;  // in default currency
}

interface DashboardInflow extends IncomeRecord {
  groupId: string;
  targetId: string;
  groupName: string;
  targetName: string;
}

const groupsIncome = ref<GroupIncomeData[]>([]);
const recentInflows = ref<DashboardInflow[]>([]);
const isGroupsListOpen = ref(false);

const groupTargetsMap = ref(new Map<string, IncomeTarget[]>());
const groupInflowsMap = ref(new Map<string, Map<string, IncomeRecord[]>>());
const categorySummaries = ref<{ category: string; target: number; earned: number; percent: number }[]>([]);

// Edit/Delete state for inflows
const editingInflow = ref<DashboardInflow | null>(null);
const inflowToDelete = ref<DashboardInflow | null>(null);
const isSaving = ref(false);
const isDeleting = ref(false);

// Edit form state
const editAmount = ref('');
const editInflowCurrency = ref('USD');
const editNote = ref('');
const editSourceType = ref('Bank Transfer');
const editDate = ref(new Date().toISOString().split('T')[0]);

watch(editingInflow, (newVal) => {
  if (newVal) {
    editAmount.value = (newVal.originalAmount ?? newVal.amount).toString();
    editInflowCurrency.value = newVal.currencyCode ?? 'USD';
    editNote.value = newVal.note ?? '';
    editSourceType.value = newVal.sourceType ?? 'Bank Transfer';
    editDate.value = newVal.date.toDate().toISOString().split('T')[0];
  }
});

// ESC key handler
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    editingInflow.value = null;
    inflowToDelete.value = null;
    isGroupsListOpen.value = false;
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

// Setup active listeners
const unsubscribes = ref<(() => void)[]>([]);

const setupListeners = () => {
  unsubscribes.value.forEach(unsub => unsub());
  unsubscribes.value = [];

  if (props.groups.length === 0) {
    groupsIncome.value = [];
    recentInflows.value = [];
    categorySummaries.value = [];
    return;
  }

  groupTargetsMap.value.clear();
  groupInflowsMap.value.clear();

  props.groups.forEach(group => {
    // 1. Subscribe to income targets for this group
    const targetsQuery = query(
      collection(db, 'groups', group.id, 'income_targets'),
      orderBy('createdAt', 'desc')
    );

    const unsubTargets = onSnapshot(targetsQuery, (targetsSnapshot) => {
      const fetchedTargets = targetsSnapshot.docs.map(tDoc => ({
        id: tDoc.id,
        ...tDoc.data()
      } as IncomeTarget));

      groupTargetsMap.value.set(group.id, fetchedTargets);
      
      // Setup subcollection listeners for inflows
      fetchedTargets.forEach(target => {
        const inflowsQuery = query(
          collection(db, 'groups', group.id, 'income_targets', target.id, 'inflows'),
          orderBy('date', 'desc')
        );

        const unsubInflows = onSnapshot(inflowsQuery, (inflSnapshot) => {
          const fetchedInflows = inflSnapshot.docs.map(iDoc => ({
            id: iDoc.id,
            ...iDoc.data()
          } as IncomeRecord));

          if (!groupInflowsMap.value.has(group.id)) {
            groupInflowsMap.value.set(group.id, new Map());
          }
          groupInflowsMap.value.get(group.id)!.set(target.id, fetchedInflows);

          // Force recalculation
          recalculateAll();
        }, (err) => {
          if (!err.message.includes('Missing or insufficient permissions')) {
            console.error("Inflows listener error:", err);
          }
        });

        unsubscribes.value.push(unsubInflows);
      });

      recalculateAll();
    }, (err) => {
      if (!err.message.includes('Missing or insufficient permissions')) {
        console.error("Targets listener error:", err);
      }
    });

    unsubscribes.value.push(unsubTargets);
  });

  const recalculateAll = () => {
    const userCurrency = props.user?.defaultCurrency || 'USD';
    
    // 1. Scale group income metrics
    const newGroupIncome: GroupIncomeData[] = props.groups.map(g => {
      const gTargets = groupTargetsMap.value.get(g.id) || [];
      const gInflMap = groupInflowsMap.value.get(g.id);

      let totalTargetInDefault = 0;
      let totalEarnedInDefault = 0;

      gTargets.forEach(target => {
        totalTargetInDefault += convertCurrency(target.targetAmount, target.currencyCode, userCurrency);

        const targetInflows = gInflMap?.get(target.id) || [];
        targetInflows.forEach(infl => {
          totalEarnedInDefault += convertCurrency(infl.originalAmount ?? infl.amount, infl.currencyCode ?? 'USD', userCurrency);
        });
      });

      return {
        groupId: g.id,
        groupName: g.name,
        groupType: g.type,
        targetsCount: gTargets.length,
        totalTarget: totalTargetInDefault,
        totalEarned: totalEarnedInDefault
      };
    });

    groupsIncome.value = newGroupIncome;

    // 2. Aggregate category allocation & recent dynamic inflows
    const allInflows: DashboardInflow[] = [];
    const catMap = new Map<string, { target: number; earned: number }>();
    incomeCategories.value.forEach(cat => {
      catMap.set(cat, { target: 0, earned: 0 });
    });

    props.groups.forEach(g => {
      const gTargets = groupTargetsMap.value.get(g.id) || [];
      const gInflMap = groupInflowsMap.value.get(g.id);

      gTargets.forEach(target => {
        const targetInflows = gInflMap?.get(target.id) || [];
        
        const cat = target.category || 'Other';
        const currentCatVals = catMap.get(cat) || { target: 0, earned: 0 };
        const targetInDefault = convertCurrency(target.targetAmount, target.currencyCode, userCurrency);
        let targetEarnedInDefault = 0;

        targetInflows.forEach(infl => {
          const inflInDefault = convertCurrency(infl.originalAmount ?? infl.amount, infl.currencyCode ?? 'USD', userCurrency);
          targetEarnedInDefault += inflInDefault;

          allInflows.push({
            ...infl,
            groupId: g.id,
            targetId: target.id,
            groupName: g.name,
            targetName: target.name
          });
        });

        catMap.set(cat, {
          target: currentCatVals.target + targetInDefault,
          earned: currentCatVals.earned + targetEarnedInDefault
        });
      });
    });

    // Save summaries
    categorySummaries.value = Array.from(catMap.entries())
      .map(([cat, vals]) => ({
        category: cat,
        target: vals.target,
        earned: vals.earned,
        percent: vals.target > 0 ? Math.min(100, Math.round((vals.earned / vals.target) * 100)) : 0
      }))
      .filter(item => item.target > 0);

    allInflows.sort((a, b) => b.date.toMillis() - a.date.toMillis());
    recentInflows.value = allInflows.slice(0, 10);
  };
};

watch(() => props.groups, () => {
  setupListeners();
}, { immediate: true, deep: true });

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

const handleUpdateInflow = async () => {
  if (!editingInflow.value) return;

  isSaving.value = true;
  try {
    const origAmount = parseFloat(editAmount.value);
    const entryCurrency = editInflowCurrency.value;
    const userDefault = props.user?.defaultCurrency || 'USD';
    const convertedAmount = convertCurrency(origAmount, entryCurrency, userDefault);

    const inflowRef = doc(
      db, 
      'groups', 
      editingInflow.value.groupId, 
      'income_targets', 
      editingInflow.value.targetId, 
      'inflows', 
      editingInflow.value.id
    );

    await updateDoc(inflowRef, {
      amount: convertedAmount,
      originalAmount: origAmount,
      currencyCode: entryCurrency,
      exchangeRateUsed: convertCurrency(1, entryCurrency, userDefault),
      note: editNote.value.trim(),
      sourceType: editSourceType.value,
      date: Timestamp.fromDate(new Date(editDate.value)),
    });
    editingInflow.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/inflows/${editingInflow.value.id}`);
  } finally {
    isSaving.value = false;
  }
};

const handleDeleteInflow = async () => {
  if (!inflowToDelete.value) return;

  isDeleting.value = true;
  try {
    const inflowRef = doc(
      db, 
      'groups', 
      inflowToDelete.value.groupId, 
      'income_targets', 
      inflowToDelete.value.targetId, 
      'inflows', 
      inflowToDelete.value.id
    );
    await deleteDoc(inflowRef);
    inflowToDelete.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/inflows/${inflowToDelete.value.id}`);
  } finally {
    isDeleting.value = false;
  }
};

const totalAggregatedTarget = ref(0);
const totalAggregatedEarned = ref(0);

watch([groupsIncome, recentInflows], () => {
  let targets = 0;
  let earned = 0;
  groupsIncome.value.forEach(gi => {
    targets += gi.totalTarget;
    earned += gi.totalEarned;
  });
  
  totalAggregatedTarget.value = targets;
  totalAggregatedEarned.value = earned;
}, { deep: true });

const triggerCreateGroup = () => {
  if ((window as any).openCreateGroupModal) {
    (window as any).openCreateGroupModal();
  }
};

const handleGroupsListClick = () => {
  if (props.groups.length === 0) return;
  if (props.groups.length === 1) {
    emit('selectGroup', props.groups[0].id);
  } else {
    isGroupsListOpen.value = true;
  }
};
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <!-- Welcome Header -->
    <header id="target-income-header" class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">
          Target & <span class="text-emerald-600 dark:text-emerald-400">Income Inflow</span>
        </h1>
        <p class="text-zinc-500 dark:text-zinc-400 font-medium text-lg">Define cash targets, record incoming resources, and analyze cash velocities instantly.</p>
      </div>
      <button 
        id="create-income-gt-btn"
        @click="triggerCreateGroup"
        class="flex items-center gap-2 px-6 py-3 bg-emerald-600 text-white rounded-2xl text-sm font-bold hover:bg-emerald-700 hover:shadow-xl hover:shadow-emerald-500/40 transition-all shadow-lg shadow-emerald-500/20 active:scale-95 cursor-pointer outline-none"
      >
        <Plus class="w-4 h-4" />
        Create Income Group
      </button>
    </header>

    <!-- State Grid -->
    <div id="income-stats-grid" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <!-- Active Inflows -->
      <button 
        id="income-stat-groups"
        @click="handleGroupsListClick"
        :class="`text-left bg-emerald-600 p-8 rounded-[32px] shadow-lg shadow-emerald-500/40 relative overflow-hidden group transition-all ${groups.length > 0 ? 'hover:scale-[1.02] active:scale-95 cursor-pointer' : 'cursor-default'}`"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <Users class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-emerald-100 uppercase tracking-[0.2em] mb-1">Active Income Groups</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight">{{ groups.length }}</p>
        </div>
      </button>

      <!-- Combined Income Reached -->
      <div 
        id="income-stat-earned"
        class="text-left bg-teal-600 p-8 rounded-[32px] shadow-lg shadow-teal-500/40 relative overflow-hidden group"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <TrendingUp class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-teal-100 uppercase tracking-[0.2em] mb-1">Total Cash Inflows</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight truncate">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalAggregatedEarned) }}
          </p>
        </div>
      </div>

      <!-- Cumulative Target Inflows -->
      <div 
        id="income-stat-target"
        class="text-left bg-indigo-600 dark:bg-zinc-900 border border-transparent dark:border-zinc-800 p-8 rounded-[32px] shadow-lg shadow-indigo-500/20 dark:shadow-none relative overflow-hidden group"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <ArrowUpRight class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-indigo-100 uppercase tracking-[0.2em] mb-1">Aggregated Goal Inflow</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight truncate">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalAggregatedTarget) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
      <!-- Income campaigns -->
      <div class="lg:col-span-2 space-y-12">
        <section id="groups-income-campaigns">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Shared Inflow Tracking Streams</h2>
          </div>
          <div class="space-y-6">
            <div v-if="groupsIncome.length === 0" class="p-16 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[32px] text-center shadow-md">
              <div class="w-16 h-16 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <Banknote class="w-8 h-8 text-zinc-300 dark:text-zinc-650" />
              </div>
              <p class="text-zinc-500 dark:text-zinc-400 font-medium">Create an income tracking group to start adding targets.</p>
            </div>
            
            <div 
              v-else 
              v-for="gInc in groupsIncome" 
              :key="gInc.groupId"
              @click="$emit('selectGroup', gInc.groupId)"
              class="bg-white dark:bg-zinc-900 p-6 sm:p-8 rounded-[32px] border border-zinc-200 dark:border-zinc-800 hover:border-emerald-500 dark:hover:border-emerald-500 shadow-sm hover:shadow-xl hover:scale-[1.01] transition-all duration-300 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div class="flex items-center justify-between gap-4 mb-4">
                  <div class="flex items-center gap-3 min-w-0 flex-1">
                    <div :class="`w-2.5 h-2.5 rounded-full shrink-0 ${gInc.groupType === 'personal' ? 'bg-blue-400' : gInc.groupType === 'household' ? 'bg-emerald-450' : 'bg-orange-450'}`" />
                    <h3 class="font-bold text-lg text-zinc-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors truncate">{{ gInc.groupName }}</h3>
                  </div>
                  <span class="text-xs font-bold text-zinc-400 dark:text-zinc-500 font-mono shrink-0">
                    {{ gInc.targetsCount }} {{ gInc.targetsCount === 1 ? 'Target stream' : 'Target streams' }}
                  </span>
                </div>

                <div class="mt-4 flex items-end justify-between">
                  <div>
                    <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">Inflow Tracked</span>
                    <p class="text-2xl font-bold text-zinc-900 dark:text-white font-mono mt-1">
                      {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(gInc.totalEarned) }}
                      <span class="text-zinc-400 dark:text-zinc-500 text-sm font-medium"> of {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(gInc.totalTarget) }}</span>
                    </p>
                  </div>
                  <span class="text-sm font-bold font-mono text-emerald-650 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 px-3 py-1.5 rounded-xl border border-emerald-100 dark:border-emerald-500/20">
                    {{ gInc.totalTarget > 0 ? ((gInc.totalEarned / gInc.totalTarget) * 100).toFixed(0) : 0 }}%
                  </span>
                </div>

                <!-- Progress Ring / Bar -->
                <div class="h-2.5 bg-zinc-100 dark:bg-white/10 rounded-full overflow-hidden mt-6">
                  <div 
                    class="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full transition-all duration-700 ease-out"
                    :style="{ width: `${gInc.totalTarget > 0 ? Math.min(100, (gInc.totalEarned / gInc.totalTarget) * 100) : 0}%` }"
                  />
                </div>
              </div>

              <div class="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex justify-end gap-2 items-center text-xs font-bold text-zinc-500 dark:text-zinc-400 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                <span>Configure Inflow Streams</span>
                <ArrowRight class="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Recent Inflows -->
      <div class="space-y-12">
        <!-- Target Categories Allocation -->
        <section id="income-categories-distribution" v-if="categorySummaries.length > 0">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Flow Contribution</h2>
          </div>
          <div class="bg-white dark:bg-zinc-900 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm p-6 space-y-6">
            <div v-for="item in categorySummaries" :key="item.category" class="space-y-2">
              <div class="flex items-center justify-between text-xs font-bold">
                <span class="text-zinc-700 dark:text-zinc-300 font-medium">{{ item.category }}</span>
                <div class="flex items-center gap-1 text-right">
                  <span class="text-emerald-600 dark:text-emerald-400 font-mono">
                    {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(item.earned) }}
                  </span>
                  <span class="text-zinc-400 dark:text-zinc-500 font-mono text-[10px]">/ {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(item.target) }}</span>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="flex-1 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div 
                    :class="`h-full rounded-full ${
                      item.category === 'Salary & Wages' ? 'bg-emerald-500' :
                      item.category === 'Freelance & Consulting' ? 'bg-indigo-500' :
                      item.category === 'Investments & Dividends' ? 'bg-purple-500' :
                      item.category === 'Rental Income' ? 'bg-amber-500' :
                      item.category === 'Sales & E-Commerce' ? 'bg-sky-500' :
                      item.category === 'Gifts & Grants' ? 'bg-rose-500' :
                      item.category === 'Side Hustle' ? 'bg-teal-500' : 'bg-zinc-500'
                    }`"
                    :style="{ width: `${item.percent}%` }"
                  />
                </div>
                <span class="text-[10px] font-bold font-mono text-zinc-500 dark:text-zinc-400 shrink-0">{{ item.percent }}%</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Recent Inflows stream -->
        <section id="recent-saving-deposits">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Recorded Receipts</h2>
          </div>
          <div class="bg-white dark:bg-zinc-900 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm p-6 space-y-6">
            <div v-if="recentInflows.length === 0" class="p-10 text-center">
              <div class="w-12 h-12 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-3">
                <Coins class="w-6 h-6 text-zinc-300 dark:text-zinc-600" />
              </div>
              <p class="text-zinc-500 text-sm font-medium">No inflow resources registered.</p>
            </div>
            
            <div v-else class="space-y-4 max-h-[500px] overflow-y-auto pr-1 custom-scrollbar">
              <div 
                v-for="dep in recentInflows" 
                :key="dep.id" 
                class="p-4 rounded-2xl bg-zinc-50 dark:bg-white/5 border border-zinc-100 dark:border-white/5 relative group transition-all hover:bg-zinc-100/50 dark:hover:bg-white/10"
              >
                <div class="flex items-start justify-between gap-3 min-w-0">
                  <div class="min-w-0">
                    <p class="font-bold text-zinc-900 dark:text-white text-sm truncate">Source: {{ dep.targetName }}</p>
                    <p class="text-[10px] text-zinc-400 dark:text-zinc-500 font-semibold font-mono mt-0.5">{{ dep.groupName }}</p>
                    <p v-if="dep.note" class="text-[11px] text-zinc-500 italic mt-1.5 truncate">"{{ dep.note }}"</p>
                    <div class="text-[10px] text-zinc-500 dark:text-zinc-400 mt-2 font-mono flex items-center gap-2">
                      <span class="font-bold uppercase bg-emerald-500/10 dark:bg-emerald-500/20 px-1.5 py-0.5 rounded-md text-emerald-600 dark:text-emerald-400">Inflow</span>
                      <span>{{ dep.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}</span>
                    </div>
                  </div>
                  
                  <div class="text-right shrink-0">
                    <p class="font-mono font-bold text-emerald-500 dark:text-emerald-400 text-base">
                      +{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(getConvertedAmount(dep.originalAmount ?? dep.amount, dep.currencyCode ?? 'USD')) }}
                    </p>
                    <p v-if="dep.currencyCode && dep.currencyCode !== user.defaultCurrency" class="text-[9px] text-zinc-405 font-semibold font-mono">
                      Orig: {{ getCurrencySymbol(dep.currencyCode) }}{{ formatCurrency(dep.originalAmount) }}
                    </p>
                  </div>
                </div>

                <!-- Actions for inflows -->
                <div v-if="dep.receivedBy === user.uid" class="absolute right-2 bottom-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    @click="editingInflow = dep"
                    class="p-1.5 bg-white dark:bg-zinc-800 text-zinc-500 hover:text-emerald-600 rounded-lg shadow-sm border border-zinc-100 dark:border-zinc-700 hover:shadow active:scale-90 cursor-pointer"
                    title="Edit inflow"
                  >
                    <Pencil class="w-3.5 h-3.5" />
                  </button>
                  <button 
                    @click="inflowToDelete = dep"
                    class="p-1.5 bg-white dark:bg-zinc-800 text-zinc-500 hover:text-red-600 rounded-lg shadow-sm border border-zinc-100 dark:border-zinc-700 hover:shadow active:scale-90 cursor-pointer"
                    title="Delete inflow"
                  >
                    <Trash2 class="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Group Selector Modal -->
    <transition name="fade">
      <div v-if="isGroupsListOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div @click="isGroupsListOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-zinc-800 rounded-[32px] shadow-2xl overflow-hidden z-10 p-8 list-none">
          <h3 class="text-xl font-bold text-zinc-900 dark:text-white mb-6 font-display">Select an Income Group</h3>
          <div class="space-y-2 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
            <button
              v-for="group in groups"
              :key="group.id"
              @click="$emit('selectGroup', group.id); isGroupsListOpen = false;"
              class="w-full flex items-center justify-between p-4 rounded-2xl bg-zinc-50 dark:bg-white/5 hover:bg-zinc-100 dark:hover:bg-white/10 border border-zinc-100 dark:border-white/5 transition-all text-left group cursor-pointer"
            >
              <div class="flex items-center gap-3">
                <div :class="`w-2 h-2 rounded-full ${
                  group.type === 'personal' ? 'bg-blue-400' :
                  group.type === 'household' ? 'bg-emerald-400' :
                  group.type === 'trip' ? 'bg-orange-400' :
                  group.type === 'employment' ? 'bg-emerald-500' :
                  group.type === 'freelance' ? 'bg-cyan-400' :
                  group.type === 'business' ? 'bg-purple-400' :
                  group.type === 'investment' ? 'bg-amber-400' :
                  'bg-indigo-400'
                }`" />
                <span class="font-bold text-zinc-900 dark:text-white">{{ group.name }}</span>
              </div>
              <ArrowRight class="w-4 h-4 text-zinc-400 dark:text-zinc-500 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Inflow Edit Modal -->
    <transition name="fade">
      <div v-if="editingInflow" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div @click="editingInflow = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Inflow Entry</h3>
            <button @click="editingInflow = null" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>
          
          <form @submit.prevent="handleUpdateInflow" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Amount & Currency</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                    {{ getCurrencySymbol(editInflowCurrency) }}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    v-model="editAmount"
                    class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                    required
                  />
                </div>
                <div class="w-32 shrink-0">
                  <select
                    v-model="editInflowCurrency"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Source Type</label>
              <select
                v-model="editSourceType"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer"
              >
                <option value="Direct Deposit">Direct Deposit</option>
                <option value="Bank Transfer">Bank/ACH Transfer</option>
                <option value="Cash Inflow">Cash</option>
                <option value="Stripe Payout">Stripe/Online Payout</option>
                <option value="Cheque">Check</option>
                <option value="Crypto Payout">Crypto</option>
              </select>
            </div>
            
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Memo / Notes</label>
              <input
                type="text"
                v-model="editNote"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-medium dark:text-white"
                placeholder="Details of receipt..."
              />
            </div>
            
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Date</label>
              <input
                type="date"
                v-model="editDate"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-medium dark:text-white"
                required
              />
            </div>
            
            <button
              type="submit"
              :disabled="isSaving"
              class="w-full py-4.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-emerald-600/15"
            >
              <Loader2 v-if="isSaving" class="w-5 h-5 animate-spin" />
              <template v-else>Save Changes</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Inflow Delete Modal -->
    <transition name="fade">
      <div v-if="inflowToDelete" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div @click="inflowToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Delete inflow?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            Are you sure you want to delete this recorded inflow? This action reduces the aggregated target accomplishments in real time.
          </p>
          <div class="flex gap-4">
            <button
              @click="inflowToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteInflow"
              :disabled="isDeleting"
              class="flex-1 py-4 bg-red-600 text-white rounded-2xl font-bold hover:bg-red-700 transition-all flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-red-500/20 active:scale-95 cursor-pointer"
            >
              <Loader2 v-if="isDeleting" class="w-5 h-5 animate-spin" />
              <template v-else>Delete</template>
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>
