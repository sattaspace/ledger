<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { 
  TrendingUp, 
  TrendingDown, 
  Users, 
  Receipt, 
  ArrowRight,
  Plus,
  Calendar,
  Pencil,
  Trash2,
  Loader2,
  X
} from 'lucide-vue-next';
import { type Group, type Expense, type BudgetType } from '../types';
import { expenseCategories } from '../utils/categories';
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

// Helper to dynamically calculate any expense amount converted to user's currently active default currency
const getConvertedExpenseAmount = (expense: Expense) => {
  const origAmount = expense.originalAmount ?? expense.amount;
  const origCurrency = expense.currencyCode ?? 'USD';
  return convertCurrency(origAmount, origCurrency, props.user?.defaultCurrency || 'USD');
};

interface DashboardExpense extends Expense {
  groupId: string;
}

interface Alert {
  id: string;
  message: string;
  type: 'warning' | 'info';
  groupId: string;
}

const recentExpenses = ref<DashboardExpense[]>([]);
const alerts = ref<Alert[]>([]);
const isGroupsListOpen = ref(false);

// Edit/Delete states
const editingExpense = ref<DashboardExpense | null>(null);
const expenseToDelete = ref<DashboardExpense | null>(null);
const isSaving = ref(false);
const isDeleting = ref(false);

// Focus Refs
const groupsListModalRef = ref<HTMLDivElement | null>(null);
const deleteExpenseModalRef = ref<HTMLDivElement | null>(null);

// Form states for editing
const editAmount = ref('');
const editDescription = ref('');
const editCategory = ref(expenseCategories.value[0] || 'Other');
const editDate = ref(new Date().toISOString().split('T')[0]);
const editExpenseCurrency = ref('USD');

watch(editingExpense, (newVal) => {
  if (newVal) {
    editAmount.value = (newVal.originalAmount ?? newVal.amount).toString();
    editDescription.value = newVal.description;
    editCategory.value = newVal.category;
    editDate.value = newVal.date.toDate().toISOString().split('T')[0];
    editExpenseCurrency.value = newVal.currencyCode ?? 'USD';
  }
});

// ESC key handler to close modals
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    editingExpense.value = null;
    expenseToDelete.value = null;
    isGroupsListOpen.value = false;
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

// Subscriptions
const unsubscribes = ref<(() => void)[]>([]);

const isDateInCurrentPeriod = (date: Date, type: BudgetType) => {
  const now = new Date();
  if (type === 'total') return true;
  
  if (type === 'monthly') {
    return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
  }
  
  if (type === 'weekly') {
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0, 0, 0, 0);
    
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 7);
    
    return date >= startOfWeek && date < endOfWeek;
  }
  
  return true;
};

const setupExpensesListeners = () => {
  // Clear any existing subscriptions
  unsubscribes.value.forEach(unsub => unsub());
  unsubscribes.value = [];

  if (props.groups.length === 0) {
    recentExpenses.value = [];
    alerts.value = [];
    return;
  }

  const expensesMap = new Map<string, DashboardExpense[]>();

  props.groups.forEach(group => {
    const expensesQuery = query(
      collection(db, 'groups', group.id, 'expenses'),
      orderBy('date', 'desc')
    );

    const unsub = onSnapshot(expensesQuery, (snapshot) => {
      const fetchedExpenses = snapshot.docs.map(doc => ({ 
        id: doc.id, 
        groupId: group.id,
        ...doc.data() 
      } as DashboardExpense));
      
      expensesMap.set(group.id, fetchedExpenses);
      
      // Combine all expenses from all groups
      const allExpenses = Array.from(expensesMap.values()).flat();
      
      // Sort by date descending
      allExpenses.sort((a, b) => b.date.toMillis() - a.date.toMillis());
      
      // Take top 10
      recentExpenses.value = allExpenses.slice(0, 10);
      
      // Generate alerts based on budgets
      const newAlerts: Alert[] = [];
      
      props.groups.forEach(g => {
        if (!g.maxBudget) return;
        
        const gExpenses = expensesMap.get(g.id) || [];
        const currentPeriodExpenses = gExpenses.filter(e => 
          isDateInCurrentPeriod(e.date.toDate(), g.budgetType || 'total')
        );
        
        const totalSpent = currentPeriodExpenses.reduce((sum, e) => sum + getConvertedExpenseAmount(e), 0);
        const symbol = getCurrencySymbol(props.user?.defaultCurrency || 'USD');
        
        const convertedMaxBudget = convertCurrency(g.maxBudget, g.currencyCode || 'USD', props.user?.defaultCurrency || 'USD');
        
        if (totalSpent > convertedMaxBudget) {
          newAlerts.push({
            id: `over-budget-${g.id}`,
            message: `Budget "${g.name}" is over its ${g.budgetType || 'total'} limit (${symbol}${formatCurrency(totalSpent)} / ${symbol}${formatCurrency(convertedMaxBudget)})`,
            type: 'warning',
            groupId: g.id
          });
        }
      });
      
      alerts.value = newAlerts;
      
    }, (error) => {
      if (error.message.includes('Missing or insufficient permissions')) {
        return;
      }
      console.error("Error fetching expenses for group", group.id, error);
    });

    unsubscribes.value.push(unsub);
  });
};

watch(() => props.groups, () => {
  setupExpensesListeners();
}, { immediate: true, deep: true });

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

const handleUpdateExpense = async () => {
  if (!editingExpense.value) return;

  isSaving.value = true;
  try {
    const origAmount = parseFloat(editAmount.value);
    const entryCurrency = editExpenseCurrency.value;
    const userDefault = props.user?.defaultCurrency || 'USD';
    const convertedAmount = convertCurrency(origAmount, entryCurrency, userDefault);

    const expenseRef = doc(db, 'groups', editingExpense.value.groupId, 'expenses', editingExpense.value.id);
    await updateDoc(expenseRef, {
      amount: convertedAmount,
      originalAmount: origAmount,
      currencyCode: entryCurrency,
      exchangeRateUsed: convertCurrency(1, entryCurrency, userDefault),
      description: editDescription.value,
      category: editCategory.value,
      date: Timestamp.fromDate(new Date(editDate.value)),
    });
    editingExpense.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/${editingExpense.value.groupId}/expenses/${editingExpense.value.id}`);
  } finally {
    isSaving.value = false;
  }
};

const handleDeleteExpense = async () => {
  if (!expenseToDelete.value) return;

  isDeleting.value = true;
  try {
    const expenseRef = doc(db, 'groups', expenseToDelete.value.groupId, 'expenses', expenseToDelete.value.id);
    await deleteDoc(expenseRef);
    expenseToDelete.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/${expenseToDelete.value.groupId}/expenses/${expenseToDelete.value.id}`);
  } finally {
    isDeleting.value = false;
  }
};

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
    <header class="mb-12 flex flex-col md:flex-row md:items-end justify-between gap-6">
      <div>
        <h1 class="text-4xl md:text-5xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">
          Welcome back, <span class="text-indigo-600 dark:text-indigo-400">{{ user.displayName?.split(' ')[0] }}</span>
        </h1>
        <p class="text-zinc-500 dark:text-zinc-400 font-medium text-lg">Here's what's happening with your shared budgets today.</p>
      </div>
      <button 
        @click="triggerCreateGroup"
        class="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-2xl text-sm font-bold hover:bg-indigo-700 hover:shadow-xl hover:shadow-indigo-500/40 transition-all shadow-lg shadow-indigo-500/20 active:scale-95 cursor-pointer"
      >
        <Plus class="w-4 h-4" />
        Create New Group
      </button>
    </header>

    <!-- Stat Grid -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <!-- Active Groups -->
      <button 
        @click="handleGroupsListClick"
        :class="`text-left bg-indigo-600 p-8 rounded-[32px] shadow-lg shadow-indigo-500/40 relative overflow-hidden group transition-all ${groups.length > 0 ? 'hover:scale-[1.02] active:scale-95 cursor-pointer' : 'cursor-default'}`"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <Users class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-indigo-100 uppercase tracking-[0.2em] mb-1">Active Groups</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight">{{ groups.length }}</p>
        </div>
      </button>

      <!-- Recent Expenses -->
      <button 
        @click="recentExpenses.length > 0 && $emit('selectGroup', recentExpenses[0].groupId)"
        :class="`text-left bg-emerald-600 p-8 rounded-[32px] shadow-lg shadow-emerald-500/40 relative overflow-hidden group transition-all ${recentExpenses.length > 0 ? 'hover:scale-[1.02] active:scale-95 cursor-pointer' : 'cursor-default'}`"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <Receipt class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-emerald-100 uppercase tracking-[0.2em] mb-1">Recent Expenses</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight">{{ recentExpenses.length }}</p>
        </div>
      </button>

      <!-- Active Alerts -->
      <button 
        @click="alerts.length > 0 && $emit('selectGroup', alerts[0].groupId)"
        :class="`text-left bg-fuchsia-600 p-8 rounded-[32px] shadow-lg shadow-fuchsia-500/40 relative overflow-hidden group transition-all ${alerts.length > 0 ? 'hover:scale-[1.02] active:scale-95 cursor-pointer' : 'cursor-default'}`"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-white/20 backdrop-blur-md rounded-2xl flex items-center justify-center mb-6">
            <TrendingUp class="w-6 h-6 text-white" />
          </div>
          <p class="text-xs font-bold text-fuchsia-100 uppercase tracking-[0.2em] mb-1">Active Alerts</p>
          <p class="text-4xl font-bold text-white font-display tracking-tight">{{ alerts.length }}</p>
        </div>
      </button>
    </div>

    <!-- Main Lists -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
      <!-- Recent activity -->
      <div class="lg:col-span-2 space-y-12">
        <section>
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Recent Activity</h2>
          </div>
          <div class="bg-white dark:bg-zinc-900 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-xl shadow-zinc-200/50 dark:shadow-black/20 overflow-hidden">
            <div v-if="recentExpenses.length === 0" class="p-16 text-center">
              <div class="w-16 h-16 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
                <Receipt class="w-8 h-8 text-zinc-300 dark:text-zinc-600" />
              </div>
              <p class="text-zinc-500 dark:text-zinc-400 font-medium">No recent expenses found.</p>
            </div>
            <div v-else class="divide-y divide-zinc-100 dark:divide-zinc-800">
              <div v-for="expense in recentExpenses" :key="expense.id" class="p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between transition-all group hover:bg-zinc-50 dark:hover:bg-zinc-800/50 gap-4">
                <div class="flex items-center gap-4 min-w-0">
                  <div class="w-12 h-12 sm:w-14 sm:h-14 bg-zinc-50 dark:bg-zinc-800 rounded-2xl flex items-center justify-center text-zinc-400 dark:text-zinc-500 transition-all border border-zinc-100 dark:border-transparent shrink-0">
                    <Receipt class="w-6 h-6 sm:w-7 sm:h-7" />
                  </div>
                  <div class="min-w-0">
                    <p class="font-bold text-zinc-900 dark:text-white text-base sm:text-lg truncate">{{ expense.description }}</p>
                    <div class="flex flex-wrap items-center gap-2 sm:gap-3 mt-1">
                      <span class="text-[9px] sm:text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider px-2 py-0.5 sm:px-2.5 sm:py-1 bg-indigo-50 dark:bg-indigo-500/10 rounded-lg border border-indigo-100 dark:border-indigo-500/20">{{ expense.category }}</span>
                      <span class="text-[9px] sm:text-[10px] text-zinc-500 font-mono font-bold">
                        {{ expense.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}
                      </span>
                      <span class="text-[9px] sm:text-[10px] text-zinc-400 font-medium italic truncate max-w-[100px] sm:max-w-none">
                        in {{ groups.find(g => g.id === expense.groupId)?.name }}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div class="flex items-center justify-between sm:justify-end gap-4 sm:gap-6 border-t border-zinc-100 dark:border-zinc-800 sm:border-0 pt-3 sm:pt-0 shrink-0">
                  <div class="text-left sm:text-right min-w-0">
                    <p 
                      :class="`text-lg sm:text-xl font-bold font-mono truncate ${expense.paidBy === user.uid ? 'text-teal-600 dark:text-teal-400' : 'text-zinc-900 dark:text-white'}`"
                      :title="`${getCurrencySymbol(user.defaultCurrency)}${formatCurrency(getConvertedExpenseAmount(expense))}`"
                    >
                      {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(getConvertedExpenseAmount(expense)) }}
                    </p>
                    <p v-if="expense.currencyCode && expense.currencyCode !== user.defaultCurrency" class="text-[9px] text-zinc-400 dark:text-zinc-500 font-semibold font-mono text-left sm:text-right">
                      Original Signature: {{ getCurrencySymbol(expense.currencyCode) }}{{ formatCurrency(expense.originalAmount || expense.amount) }}
                    </p>
                    <p v-else class="text-[9px] sm:text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-0.5">
                      {{ expense.paidBy === user.uid ? 'You paid' : 'Someone paid' }}
                    </p>
                  </div>
                  <div v-if="expense.paidBy === user.uid" class="flex items-center gap-1">
                    <button 
                      @click="editingExpense = expense"
                      class="p-2 text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-500/10 rounded-xl lg:opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all active:scale-90 outline-none cursor-pointer"
                      title="Edit Expense"
                    >
                      <Pencil class="w-4 h-4" />
                    </button>
                    <button 
                      @click="expenseToDelete = expense"
                      class="p-2 text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-xl lg:opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all active:scale-90 outline-none cursor-pointer"
                      title="Delete Expense"
                    >
                      <Trash2 class="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Sidebar section -->
      <div class="space-y-12">
        <section>
          <div class="flex items-center justify-between mb-6">
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Budget Alerts</h2>
          </div>
          <div class="space-y-4">
            <div v-if="alerts.length === 0" class="p-10 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[32px] text-center shadow-xl shadow-zinc-200/50 dark:shadow-black/20">
              <div class="w-12 h-12 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto mb-3">
                <TrendingDown class="w-6 h-6 text-emerald-500" />
              </div>
              <p class="text-zinc-500 text-sm font-medium">All budgets on track</p>
            </div>
            <div v-else v-for="alert in alerts" :key="alert.id" class="p-6 rounded-[32px] border shadow-md transition-all duration-300 bg-red-50 dark:bg-red-950/80 border-red-200 dark:border-red-900/50 text-red-900 dark:text-red-100 backdrop-blur-sm">
              <div class="flex gap-4">
                <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-red-500/10 dark:bg-red-500/20">
                  <TrendingUp class="w-5 h-5 text-red-600 dark:text-red-400" />
                </div>
                <p class="text-sm font-bold leading-relaxed">{{ alert.message }}</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- Select Group Modal -->
    <transition name="fade">
      <div v-if="isGroupsListOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div @click="isGroupsListOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[32px] shadow-2xl overflow-hidden outline-none z-10 p-8 list-none">
          <h3 class="text-xl font-bold text-zinc-900 dark:text-white mb-6 font-display">Select a Group</h3>
          <div class="space-y-2 max-h-[60vh] overflow-y-auto pr-2 custom-scrollbar">
            <button
              v-for="group in groups"
              :key="group.id"
              @click="$emit('selectGroup', group.id); isGroupsListOpen = false;"
              class="w-full flex items-center justify-between p-4 rounded-2xl bg-zinc-50 dark:bg-white/5 hover:bg-zinc-100 dark:hover:bg-white/10 border border-zinc-100 dark:border-white/5 transition-all text-left group cursor-pointer gap-2"
            >
              <div class="flex items-center gap-3 min-w-0 flex-1">
                <div :class="`w-2 h-2 rounded-full shrink-0 ${group.type === 'personal' ? 'bg-blue-400' : group.type === 'household' ? 'bg-emerald-400' : 'bg-orange-400'}`" />
                <span class="font-bold text-zinc-900 dark:text-white truncate">{{ group.name }}</span>
              </div>
              <ArrowRight class="w-4 h-4 text-zinc-400 dark:text-zinc-500 group-hover:translate-x-1 transition-transform shrink-0" />
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Expense Edit Modal -->
    <transition name="fade">
      <div v-if="editingExpense" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div @click="editingExpense = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Transaction</h3>
            <button @click="editingExpense = null" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>
          
          <form @submit.prevent="handleUpdateExpense" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Amount & Currency Signature</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                    {{ getCurrencySymbol(editExpenseCurrency) }}
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
                    v-model="editExpenseCurrency"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
              <p v-if="editExpenseCurrency !== user.defaultCurrency" class="text-[10px] text-zinc-400 mt-2 font-medium font-mono">
                Converts to approx. {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertCurrency(parseFloat(editAmount || '0'), editExpenseCurrency, user.defaultCurrency)) }}
              </p>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Description</label>
              <input
                type="text"
                v-model="editDescription"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white"
                placeholder="What was this for?"
                required
              />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Category</label>
                <select
                  v-model="editCategory"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white appearance-none"
                >
                  <option v-for="cat in expenseCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
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
            </div>
            <button
              type="submit"
              :disabled="isSaving"
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 shadow-lg shadow-teal-600/15 active:scale-95 cursor-pointer font-sans"
            >
              <Loader2 v-if="isSaving" class="w-5 h-5 animate-spin" />
              <template v-else>Save Changes</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Expense Delete Modal -->
    <transition name="fade">
      <div v-if="expenseToDelete" class="fixed inset-0 z-[70] flex items-center justify-center p-4">
        <div @click="expenseToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 border border-red-100 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Delete Expense?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            Are you sure you want to delete this expense? This action cannot be undone.
          </p>
          <div class="flex gap-4">
            <button
              @click="expenseToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteExpense"
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
