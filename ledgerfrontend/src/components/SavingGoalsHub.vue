<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { 
  Target, 
  PiggyBank, 
  Coins, 
  Users, 
  ArrowRight,
  Plus,
  Calendar,
  Pencil,
  Trash2,
  Loader2,
  X,
  TrendingUp,
  CheckCircle2
} from 'lucide-vue-next';
import { type Group, type SavingGoal, type Deposit } from '../types';
import { savingCategories } from '../utils/categories';
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

interface GroupSavingsData {
  groupId: string;
  groupName: string;
  groupType: string;
  goalsCount: number;
  totalTarget: number; // in default currency
  totalSaved: number;  // in default currency
}

interface DashboardDeposit extends Deposit {
  groupId: string;
  goalId: string;
  groupName: string;
  goalName: string;
}

const groupsSavings = ref<GroupSavingsData[]>([]);
const recentDeposits = ref<DashboardDeposit[]>([]);
const isGroupsListOpen = ref(false);

const groupGoalsMap = ref(new Map<string, SavingGoal[]>());
const groupDepositsMap = ref(new Map<string, Map<string, Deposit[]>>());
const categorySummaries = ref<{ category: string; target: number; saved: number; percent: number }[]>([]);

// Edit/Delete state for deposits
const editingDeposit = ref<DashboardDeposit | null>(null);
const depositToDelete = ref<DashboardDeposit | null>(null);
const isSaving = ref(false);
const isDeleting = ref(false);

// Edit form state
const editAmount = ref('');
const editDepositCurrency = ref('USD');
const editNote = ref('');
const editDate = ref(new Date().toISOString().split('T')[0]);

watch(editingDeposit, (newVal) => {
  if (newVal) {
    editAmount.value = (newVal.originalAmount ?? newVal.amount).toString();
    editDepositCurrency.value = newVal.currencyCode ?? 'USD';
    editNote.value = newVal.note ?? '';
    editDate.value = newVal.date.toDate().toISOString().split('T')[0];
  }
});

// ESC key handler
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    editingDeposit.value = null;
    depositToDelete.value = null;
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
    groupsSavings.value = [];
    recentDeposits.value = [];
    categorySummaries.value = [];
    return;
  }

  groupGoalsMap.value.clear();
  groupDepositsMap.value.clear();

  props.groups.forEach(group => {
    // 1. Subscribe to goals for this group
    const goalsQuery = query(
      collection(db, 'groups', group.id, 'saving_goals'),
      orderBy('createdAt', 'desc')
    );

    const unsubGoals = onSnapshot(goalsQuery, (goalsSnapshot) => {
      const fetchedGoals = goalsSnapshot.docs.map(gDoc => ({
        id: gDoc.id,
        ...gDoc.data()
      } as SavingGoal));

      groupGoalsMap.value.set(group.id, fetchedGoals);
      
      // Cleanup previous subcollection listeners for deposits in this group if necessary
      // For simplicity, we create listeners for existing goals in this slice
      fetchedGoals.forEach(goal => {
        const depositsQuery = query(
          collection(db, 'groups', group.id, 'saving_goals', goal.id, 'deposits'),
          orderBy('date', 'desc')
        );

        const unsubDeposits = onSnapshot(depositsQuery, (depSnapshot) => {
          const fetchedDeposits = depSnapshot.docs.map(dDoc => ({
            id: dDoc.id,
            ...dDoc.data()
          } as Deposit));

          if (!groupDepositsMap.value.has(group.id)) {
            groupDepositsMap.value.set(group.id, new Map());
          }
          groupDepositsMap.value.get(group.id)!.set(goal.id, fetchedDeposits);

          // Trigger state recalculation whenever goals or deposits change
          recalculateAll();
        }, (err) => {
          if (!err.message.includes('Missing or insufficient permissions')) {
            console.error("Deposits listener error:", err);
          }
        });

        unsubscribes.value.push(unsubDeposits);
      });

      recalculateAll();
    }, (err) => {
      if (!err.message.includes('Missing or insufficient permissions')) {
        console.error("Goals listener error:", err);
      }
    });

    unsubscribes.value.push(unsubGoals);
  });

  const recalculateAll = () => {
    const userCurrency = props.user?.defaultCurrency || 'USD';
    
    // 1. Calculate aggregated savings data for each group
    const newGroupSavings: GroupSavingsData[] = props.groups.map(g => {
      const gGoals = groupGoalsMap.value.get(g.id) || [];
      const gDepMap = groupDepositsMap.value.get(g.id);

      let totalTargetInDefault = 0;
      let totalSavedInDefault = 0;

      gGoals.forEach(goal => {
        // Target in default currency
        totalTargetInDefault += convertCurrency(goal.targetAmount, goal.currencyCode, userCurrency);

        // Deposits under this goal
        const goalDeps = gDepMap?.get(goal.id) || [];
        goalDeps.forEach(dep => {
          totalSavedInDefault += convertCurrency(dep.originalAmount ?? dep.amount, dep.currencyCode ?? 'USD', userCurrency);
        });
      });

      return {
        groupId: g.id,
        groupName: g.name,
        groupType: g.type,
        goalsCount: gGoals.length,
        totalTarget: totalTargetInDefault,
        totalSaved: totalSavedInDefault
      };
    });

    groupsSavings.value = newGroupSavings;

    // 2. Compute recent deposits list AND category summaries globally across all groups and goals
    const allDeposits: DashboardDeposit[] = [];
    const catMap = new Map<string, { target: number; saved: number }>();
    savingCategories.value.forEach(cat => {
      catMap.set(cat, { target: 0, saved: 0 });
    });

    props.groups.forEach(g => {
      const gGoals = groupGoalsMap.value.get(g.id) || [];
      const gDepMap = groupDepositsMap.value.get(g.id);

      gGoals.forEach(goal => {
        const goalDeps = gDepMap?.get(goal.id) || [];
        
        // Calculate category target & saved amounts
        const cat = goal.category || 'Other';
        const currentCatVals = catMap.get(cat) || { target: 0, saved: 0 };
        const targetInDefault = convertCurrency(goal.targetAmount, goal.currencyCode, userCurrency);
        let goalSavedInDefault = 0;

        goalDeps.forEach(dep => {
          const depInDefault = convertCurrency(dep.originalAmount ?? dep.amount, dep.currencyCode ?? 'USD', userCurrency);
          goalSavedInDefault += depInDefault;

          allDeposits.push({
            ...dep,
            groupId: g.id,
            goalId: goal.id,
            groupName: g.name,
            goalName: goal.name
          });
        });

        catMap.set(cat, {
          target: currentCatVals.target + targetInDefault,
          saved: currentCatVals.saved + goalSavedInDefault
        });
      });
    });

    // Populate category summaries
    categorySummaries.value = Array.from(catMap.entries())
      .map(([cat, vals]) => ({
        category: cat,
        target: vals.target,
        saved: vals.saved,
        percent: vals.target > 0 ? Math.min(100, Math.round((vals.saved / vals.target) * 105)) : 0
      }))
      .filter(item => item.target > 0);

    // Limit percentage to max 100 correctly
    categorySummaries.value.forEach(item => {
      item.percent = Math.min(100, item.percent);
    });

    // Sort descending by date
    allDeposits.sort((a, b) => b.date.toMillis() - a.date.toMillis());
    recentDeposits.value = allDeposits.slice(0, 10);
  };
};

watch(() => props.groups, () => {
  setupListeners();
}, { immediate: true, deep: true });

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

const handleUpdateDeposit = async () => {
  if (!editingDeposit.value) return;

  isSaving.value = true;
  try {
    const origAmount = parseFloat(editAmount.value);
    const entryCurrency = editDepositCurrency.value;
    const userDefault = props.user?.defaultCurrency || 'USD';
    const convertedAmount = convertCurrency(origAmount, entryCurrency, userDefault);

    const depositRef = doc(
      db, 
      'groups', 
      editingDeposit.value.groupId, 
      'saving_goals', 
      editingDeposit.value.goalId, 
      'deposits', 
      editingDeposit.value.id
    );

    await updateDoc(depositRef, {
      amount: convertedAmount,
      originalAmount: origAmount,
      currencyCode: entryCurrency,
      exchangeRateUsed: convertCurrency(1, entryCurrency, userDefault),
      note: editNote.value.trim(),
      date: Timestamp.fromDate(new Date(editDate.value)),
    });
    editingDeposit.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/deposits/${editingDeposit.value.id}`);
  } finally {
    isSaving.value = false;
  }
};

const handleDeleteDeposit = async () => {
  if (!depositToDelete.value) return;

  isDeleting.value = true;
  try {
    const depositRef = doc(
      db, 
      'groups', 
      depositToDelete.value.groupId, 
      'saving_goals', 
      depositToDelete.value.goalId, 
      'deposits', 
      depositToDelete.value.id
    );
    await deleteDoc(depositRef);
    depositToDelete.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/deposits/${depositToDelete.value.id}`);
  } finally {
    isDeleting.value = false;
  }
};

const totalAggregatedGoals = ref(0);
const totalAggregatedSaved = ref(0);
const completedGoalsCount = ref(0);

watch([groupsSavings, recentDeposits], () => {
  let goals = 0;
  let saved = 0;
  groupsSavings.value.forEach(gs => {
    goals += gs.totalTarget;
    saved += gs.totalSaved;
  });
  
  totalAggregatedGoals.value = goals;
  totalAggregatedSaved.value = saved;
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
    <header id="saving-goals-header" class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">
          Welcome back, <span class="text-teal-600 dark:text-teal-400">{{ user.displayName?.split(' ')[0] }}</span>
        </h1>
        <p class="text-zinc-500 dark:text-zinc-400 font-medium text-lg">Here's how your shared saving goals and campaigns are progressing today.</p>
      </div>
      <button 
        id="create-group-btn"
        @click="triggerCreateGroup"
        class="flex items-center gap-2 px-6 py-3 bg-teal-600 text-white rounded-2xl text-sm font-bold hover:bg-teal-700 hover:shadow-xl hover:shadow-teal-500/40 transition-all shadow-lg shadow-teal-500/20 active:scale-95 cursor-pointer outline-none"
      >
        <Plus class="w-4 h-4" />
        Create Savings Group
      </button>
    </header>

    <!-- State Grid -->
    <div id="stats-grid" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <!-- Active Groups -->
      <button 
        id="stat-box-groups"
        @click="handleGroupsListClick"
        :class="`text-left bg-teal-600 p-8 rounded-[32px] shadow-lg shadow-teal-500/40 relative overflow-hidden group transition-all ${groups.length > 0 ? 'hover:scale-[1.02] active:scale-95 cursor-pointer' : 'cursor-default'}`"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <Users class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-teal-100 uppercase tracking-[0.2em] mb-1">Active Saving Groups</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight">{{ groups.length }}</p>
        </div>
      </button>

      <!-- Total Saved -->
      <div 
        id="stat-box-saved"
        class="text-left bg-emerald-600 p-8 rounded-[32px] shadow-lg shadow-emerald-500/40 relative overflow-hidden group"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <PiggyBank class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-emerald-100 uppercase tracking-[0.2em] mb-1">Combined Saved</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight truncate">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalAggregatedSaved) }}
          </p>
        </div>
      </div>

      <!-- Total Goals Target -->
      <div 
        id="stat-box-target"
        class="text-left bg-indigo-600 dark:bg-zinc-900 border border-transparent dark:border-zinc-800 p-8 rounded-[32px] shadow-lg shadow-indigo-500/20 dark:shadow-none relative overflow-hidden group"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <Target class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-indigo-100 uppercase tracking-[0.2em] mb-1">Aggregate Target</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight truncate">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalAggregatedGoals) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
      <!-- Group Goals list -->
      <div class="lg:col-span-2 space-y-12">
        <section id="groups-saving-campaigns">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Shared Savings Campaigns</h2>
          </div>
          <div class="space-y-6">
            <div v-if="groupsSavings.length === 0" class="p-16 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[32px] text-center shadow-md">
              <div class="w-16 h-16 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <Target class="w-8 h-8 text-zinc-300 dark:text-zinc-650" />
              </div>
              <p class="text-zinc-500 dark:text-zinc-400 font-medium">Create a group to start adding saving goals.</p>
            </div>
            
            <div 
              v-else 
              v-for="gSave in groupsSavings" 
              :key="gSave.groupId"
              @click="$emit('selectGroup', gSave.groupId)"
              class="bg-white dark:bg-zinc-900 p-6 sm:p-8 rounded-[32px] border border-zinc-200 dark:border-zinc-800 hover:border-teal-500 dark:hover:border-teal-500 shadow-sm hover:shadow-xl hover:scale-[1.01] transition-all duration-300 cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div class="flex items-center justify-between gap-4 mb-4">
                  <div class="flex items-center gap-3 min-w-0 flex-1">
                    <div :class="`w-2.5 h-2.5 rounded-full shrink-0 ${gSave.groupType === 'personal' ? 'bg-blue-400' : gSave.groupType === 'household' ? 'bg-emerald-400' : 'bg-orange-400'}`" />
                    <h3 class="font-bold text-lg text-zinc-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors truncate">{{ gSave.groupName }}</h3>
                  </div>
                  <span class="text-xs font-bold text-zinc-400 dark:text-zinc-500 font-mono shrink-0">
                    {{ gSave.goalsCount }} {{ gSave.goalsCount === 1 ? 'Goal' : 'Goals' }}
                  </span>
                </div>

                <div class="mt-4 flex items-end justify-between">
                  <div>
                    <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider block">Completed Milestone</span>
                    <p class="text-2xl font-bold text-zinc-900 dark:text-white font-mono mt-1">
                      {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(gSave.totalSaved) }}
                      <span class="text-zinc-400 dark:text-zinc-500 text-sm font-medium"> of {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(gSave.totalTarget) }}</span>
                    </p>
                  </div>
                  <span class="text-sm font-bold font-mono text-teal-600 dark:text-teal-400 bg-teal-50 dark:bg-teal-500/10 px-3 py-1.5 rounded-xl border border-teal-100 dark:border-teal-500/20">
                    {{ gSave.totalTarget > 0 ? ((gSave.totalSaved / gSave.totalTarget) * 100).toFixed(0) : 0 }}%
                  </span>
                </div>

                <!-- Progress Ring / Bar -->
                <div class="h-2.5 bg-zinc-100 dark:bg-white/10 rounded-full overflow-hidden mt-6">
                  <div 
                    class="h-full bg-gradient-to-r from-teal-500 to-emerald-500 rounded-full transition-all duration-700 ease-out"
                    :style="{ width: `${gSave.totalTarget > 0 ? Math.min(100, (gSave.totalSaved / gSave.totalTarget) * 100) : 0}%` }"
                  />
                </div>
              </div>

              <div class="mt-6 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex justify-end gap-2 items-center text-xs font-bold text-zinc-500 dark:text-zinc-400 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors">
                <span>Configure Goals & Deposits</span>
                <ArrowRight class="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Recent Deposits sidebar -->
      <div class="space-y-12">
        <!-- Goal Categories Allocation -->
        <section id="goal-categories-distribution" v-if="categorySummaries.length > 0">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Category Allocation</h2>
          </div>
          <div class="bg-white dark:bg-zinc-900 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm p-6 space-y-6">
            <div v-for="item in categorySummaries" :key="item.category" class="space-y-2">
              <div class="flex items-center justify-between text-xs font-bold">
                <span class="text-zinc-700 dark:text-zinc-300 font-medium">{{ item.category }}</span>
                <div class="flex items-center gap-1 text-right">
                  <span class="text-teal-600 dark:text-teal-400 font-mono">
                    {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(item.saved) }}
                  </span>
                  <span class="text-zinc-400 dark:text-zinc-500 font-mono text-[10px]">/ {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(item.target) }}</span>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <div class="flex-1 h-2 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                  <div 
                    :class="`h-full rounded-full ${
                      item.category === 'Vacation & Travel' ? 'bg-sky-500' :
                      item.category === 'Home & Property' ? 'bg-amber-500' :
                      item.category === 'Vehicle & Transport' ? 'bg-purple-500' :
                      item.category === 'Emergency Fund' ? 'bg-rose-500' :
                      item.category === 'Gadget & Appliance' ? 'bg-indigo-500' :
                      item.category === 'Education' ? 'bg-emerald-500' :
                      item.category === 'Investment' ? 'bg-teal-500' : 'bg-zinc-500'
                    }`"
                    :style="{ width: `${item.percent}%` }"
                  />
                </div>
                <span class="text-[10px] font-bold font-mono text-zinc-500 dark:text-zinc-400 shrink-0">{{ item.percent }}%</span>
              </div>
            </div>
          </div>
        </section>

        <section id="recent-saving-deposits">
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Recent Deposits</h2>
          </div>
          <div class="bg-white dark:bg-zinc-900 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm p-6 space-y-6">
            <div v-if="recentDeposits.length === 0" class="p-10 text-center">
              <div class="w-12 h-12 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-3">
                <Coins class="w-6 h-6 text-zinc-300 dark:text-zinc-600" />
              </div>
              <p class="text-zinc-500 text-sm font-medium">No deposits committed yet.</p>
            </div>
            
            <div v-else class="space-y-4 max-h-[500px] overflow-y-auto pr-1 custom-scrollbar">
              <div 
                v-for="dep in recentDeposits" 
                :key="dep.id" 
                class="p-4 rounded-2xl bg-zinc-50 dark:bg-white/5 border border-zinc-100 dark:border-white/5 relative group transition-all hover:bg-zinc-100/50 dark:hover:bg-white/10"
              >
                <div class="flex items-start justify-between gap-3 min-w-0">
                  <div class="min-w-0">
                    <p class="font-bold text-zinc-900 dark:text-white text-sm truncate">Goal: {{ dep.goalName }}</p>
                    <p class="text-[10px] text-zinc-400 dark:text-zinc-500 font-semibold font-mono mt-0.5">{{ dep.groupName }}</p>
                    <p v-if="dep.note" class="text-[11px] text-zinc-500 italic mt-1.5 truncate">"{{ dep.note }}"</p>
                    <div class="text-[10px] text-zinc-500 dark:text-zinc-400 mt-2 font-mono flex items-center gap-2">
                      <span class="font-bold uppercase bg-zinc-200 dark:bg-zinc-805 px-1.5 py-0.5 rounded-md text-zinc-650 dark:text-zinc-400 text-zinc-600 dark:text-zinc-450">Deposit</span>
                      <span>{{ dep.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}</span>
                    </div>
                  </div>
                  
                  <div class="text-right shrink-0">
                    <p class="font-mono font-bold text-teal-600 dark:text-teal-400 text-base">
                      +{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(getConvertedAmount(dep.originalAmount ?? dep.amount, dep.currencyCode ?? 'USD')) }}
                    </p>
                    <p v-if="dep.currencyCode && dep.currencyCode !== user.defaultCurrency" class="text-[9px] text-zinc-405 font-semibold font-mono">
                      Orig: {{ getCurrencySymbol(dep.currencyCode) }}{{ formatCurrency(dep.originalAmount) }}
                    </p>
                  </div>
                </div>

                <!-- Hover actions for deleting own deposits -->
                <div v-if="dep.depositedBy === user.uid" class="absolute right-2 bottom-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button 
                    @click="editingDeposit = dep"
                    class="p-1.5 bg-white dark:bg-zinc-800 text-zinc-500 hover:text-teal-600 rounded-lg shadow-sm border border-zinc-100 dark:border-zinc-700 hover:shadow active:scale-90 cursor-pointer"
                    title="Edit deposit"
                  >
                    <Pencil class="w-3.5 h-3.5" />
                  </button>
                  <button 
                    @click="depositToDelete = dep"
                    class="p-1.5 bg-white dark:bg-zinc-800 text-zinc-500 hover:text-red-600 rounded-lg shadow-sm border border-zinc-100 dark:border-zinc-700 hover:shadow active:scale-90 cursor-pointer"
                    title="Delete deposit"
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
          <h3 class="text-xl font-bold text-zinc-900 dark:text-white mb-6 font-display">Select a Group</h3>
          <div class="space-y-2 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
            <button
              v-for="group in groups"
              :key="group.id"
              @click="$emit('selectGroup', group.id); isGroupsListOpen = false;"
              class="w-full flex items-center justify-between p-4 rounded-2xl bg-zinc-50 dark:bg-white/5 hover:bg-zinc-100 dark:hover:bg-white/10 border border-zinc-100 dark:border-white/5 transition-all text-left group cursor-pointer"
            >
              <div class="flex items-center gap-3">
                <div :class="`w-2 h-2 rounded-full ${group.type === 'personal' ? 'bg-blue-400' : group.type === 'household' ? 'bg-emerald-500' : 'bg-orange-400'}`" />
                <span class="font-bold text-zinc-900 dark:text-white">{{ group.name }}</span>
              </div>
              <ArrowRight class="w-4 h-4 text-zinc-400 dark:text-zinc-400 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Deposit Edit Modal -->
    <transition name="fade">
      <div v-if="editingDeposit" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div @click="editingDeposit = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Deposit</h3>
            <button @click="editingDeposit = null" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>
          
          <form @submit.prevent="handleUpdateDeposit" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Amount & Currency</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                    {{ getCurrencySymbol(editDepositCurrency) }}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    v-model="editAmount"
                    class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                    required
                  />
                </div>
                <div class="w-32 shrink-0">
                  <select
                    v-model="editDepositCurrency"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
            </div>
            
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Notes/Memo</label>
              <input
                type="text"
                v-model="editNote"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white"
                placeholder="Details of deposit..."
              />
            </div>
            
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Date</label>
              <input
                type="date"
                v-model="editDate"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white"
                required
              />
            </div>
            
            <button
              type="submit"
              :disabled="isSaving"
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-teal-600/15 active:scale-95 cursor-pointer"
            >
              <Loader2 v-if="isSaving" class="w-5 h-5 animate-spin" />
              <template v-else>Save Changes</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Deposit Delete Modal -->
    <transition name="fade">
      <div v-if="depositToDelete" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div @click="depositToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 dark:text-red-400 border border-red-100 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Delete Deposit entry?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            Are you sure you want to delete this deposit entry? This will subtract the amount from the goal's overall savings progress.
          </p>
          <div class="flex gap-4">
            <button
              @click="depositToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteDeposit"
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
