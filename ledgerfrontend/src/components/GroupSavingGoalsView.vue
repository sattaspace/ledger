<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  ArrowLeft,
  Target, 
  PiggyBank, 
  Coins, 
  Users, 
  Plus, 
  Calendar,
  Pencil,
  Trash2,
  Loader2,
  X,
  TrendingDown,
  ChevronRight,
  TrendingUp,
  Tag,
  DollarSign,
  Printer,
  Sparkles,
  AlertCircle,
  MoreVertical,
  Briefcase
} from 'lucide-vue-next';
import { type Group, type SavingGoal, type Deposit, type GroupMember } from '../types';
import { savingCategories } from '../utils/categories';
import { formatCurrency } from '../utils/format';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { convertCurrency, getCurrencySymbol, CURRENCIES } from '../utils/currency';
import { Timestamp, collection, query, onSnapshot, doc, getDoc, updateDoc, setDoc, deleteDoc } from 'firebase/firestore';
import { db } from '../firebase';

// Import our Central Data Management service functions
import {
  subscribeGroupDetail,
  subscribeGroupMembers,
  subscribeGroupGoals,
  subscribeGoalDeposits,
  createGoal,
  updateGoal,
  deleteGoal,
  createDeposit,
  deleteDeposit,
  updateGroupSettings,
  deleteGroup
} from '../services/dataService';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

const group = ref<Group | null>(null);
const goals = ref<SavingGoal[]>([]);
const deposits = ref<Record<string, Deposit[]>>({}); // goalId -> Deposit[]
const members = ref<GroupMember[]>([]);
const loading = ref(true);

// Settings Modals States inside saving goals detail view (Development Pattern Consistency!)
const isSettingsOpen = ref(false);
const isDeleteGroupConfirmOpen = ref(false);
const editName = ref('');
const editDescription = ref('');
const editGroupCurrency = ref('USD');
const editGroupType = ref('personal');

// AI Inside / Savings Insights
const isAnalyzing = ref(false);
const isAnalysisModalOpen = ref(false);
const analysisResult = ref<string | null>(null);

// Forms toggles & states
const isAddGoalOpen = ref(false);
const isEditGoalOpen = ref(false);
const isAddDepositOpen = ref(false);

const activeGoalForDeposit = ref<SavingGoal | null>(null);
const goalToEdit = ref<SavingGoal | null>(null);
const goalToDelete = ref<SavingGoal | null>(null);
const depositToDelete = ref<{ deposit: Deposit; goalId: string } | null>(null);

// Create Goal form state
const goalName = ref('');
const goalTarget = ref('');
const goalCurrencyCode = ref('USD');
const goalCategory = ref(savingCategories.value[0] || 'Other');
const isCreatingGoal = ref(false);

// Edit Goal form state
const editGoalName = ref('');
const editGoalTarget = ref('');
const editGoalCurrencyCode = ref('USD');
const editGoalCategory = ref('');
const isSavingGoal = ref(false);

// Add Deposit form state
const depositAmount = ref('');
const depositCurrencyCode = ref('USD');
const depositNote = ref('');
const depositDate = ref(new Date().toISOString().split('T')[0]);
const isCreatingDeposit = ref(false);

const accountGroups = ref<Group[]>([]);
const chosenAccountId = ref('');

// Subscriptions
let unsubscribeGroup: (() => void) | null = null;
let unsubscribeGoals: (() => void) | null = null;
let unsubscribeMembers: (() => void) | null = null;
let unsubscribeAccounts: (() => void) | null = null;
const depositUnsubscribes = ref<(() => void)[]>([]);

onMounted(() => {
  // Load accounts lists for linking deposits
  const accountsQuery = query(collection(db, 'groups'));
  unsubscribeAccounts = onSnapshot(accountsQuery, (snapshot) => {
    accountGroups.value = snapshot.docs
      .map(docSnap => ({ id: docSnap.id, ...docSnap.data() } as Group))
      .filter(g => g.service === 'accounts');
  }, (error) => {
    console.error("Error loading accounts in savings:", error);
  });
  // 1. Fetch Group detail via Central Services
  unsubscribeGroup = subscribeGroupDetail(props.groupId, (data) => {
    group.value = data;
    if (data && !editName.value) {
      editName.value = data.name || '';
      editDescription.value = data.description || '';
      editGroupCurrency.value = data.currencyCode || 'USD';
      editGroupType.value = data.type || 'personal';
    }
  });

  // 2. Fetch Group members via Central Services
  unsubscribeMembers = subscribeGroupMembers(props.groupId, (data) => {
    members.value = data;
  });

  // 3. Fetch Saving Goals via Central Services
  unsubscribeGoals = subscribeGroupGoals(props.groupId, (data) => {
    goals.value = data;

    // Clear previous deposit listeners
    depositUnsubscribes.value.forEach(unsub => unsub());
    depositUnsubscribes.value = [];

    // Subscribe to deposits for each goal via Central Services
    goals.value.forEach(g => {
      const unsubDep = subscribeGoalDeposits(props.groupId, g.id, (depSnap) => {
        deposits.value[g.id] = depSnap;
      });
      depositUnsubscribes.value.push(unsubDep);
    });

    loading.value = false;
  });
});

onUnmounted(() => {
  if (unsubscribeGroup) unsubscribeGroup();
  if (unsubscribeGoals) unsubscribeGoals();
  if (unsubscribeMembers) unsubscribeMembers();
  if (unsubscribeAccounts) unsubscribeAccounts();
  depositUnsubscribes.value.forEach(unsub => unsub());
});

watch(() => props.user, (u) => {
  if (u) {
    goalCurrencyCode.value = u.defaultCurrency || 'USD';
    depositCurrencyCode.value = u.defaultCurrency || 'USD';
  }
}, { immediate: true });

// Form logic
const openAddGoalModal = () => {
  goalName.value = '';
  goalTarget.value = '';
  goalCurrencyCode.value = props.user?.defaultCurrency || 'USD';
  goalCategory.value = savingCategories.value[0] || 'Other';
  isAddGoalOpen.value = true;
};

const openEditGoalModal = (g: SavingGoal) => {
  goalToEdit.value = g;
  editGoalName.value = g.name;
  editGoalTarget.value = g.targetAmount.toString();
  editGoalCurrencyCode.value = g.currencyCode || 'USD';
  editGoalCategory.value = g.category || savingCategories.value[0] || 'Other';
  isEditGoalOpen.value = true;
};

const openAddDepositModal = (g: SavingGoal) => {
  activeGoalForDeposit.value = g;
  depositAmount.value = '';
  depositCurrencyCode.value = props.user?.defaultCurrency || 'USD';
  depositNote.value = '';
  depositDate.value = new Date().toISOString().split('T')[0];
  isAddDepositOpen.value = true;
};

// Actions
const handleCreateGoal = async () => {
  if (!goalName.value.trim() || !goalTarget.value) return;

  isCreatingGoal.value = true;
  try {
    const targetVal = parseFloat(goalTarget.value);
    await createGoal(props.groupId, {
      name: goalName.value.trim(),
      targetAmount: targetVal,
      currencyCode: goalCurrencyCode.value,
      category: goalCategory.value,
      createdBy: props.user.uid,
    });
    isAddGoalOpen.value = false;
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, `groups/${props.groupId}/saving_goals`);
  } finally {
    isCreatingGoal.value = false;
  }
};

const handleUpdateGoal = async () => {
  if (!goalToEdit.value || !editGoalName.value.trim() || !editGoalTarget.value) return;

  isSavingGoal.value = true;
  try {
    const targetVal = parseFloat(editGoalTarget.value);
    await updateGoal(props.groupId, goalToEdit.value.id, {
      name: editGoalName.value.trim(),
      targetAmount: targetVal,
      currencyCode: editGoalCurrencyCode.value,
      category: editGoalCategory.value,
    });
    isEditGoalOpen.value = false;
    goalToEdit.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/${props.groupId}/saving_goals/${goalToEdit.value.id}`);
  } finally {
    isSavingGoal.value = false;
  }
};

const handleDeleteGoal = async () => {
  if (!goalToDelete.value) return;

  try {
    await deleteGoal(props.groupId, goalToDelete.value.id);
    goalToDelete.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/${props.groupId}/saving_goals/${goalToDelete.value.id}`);
  }
};

const handleCreateDeposit = async () => {
  if (!activeGoalForDeposit.value || !depositAmount.value) return;

  isCreatingDeposit.value = true;
  try {
    const origAmount = parseFloat(depositAmount.value);
    const entryCurrency = depositCurrencyCode.value;
    const userDefault = props.user?.defaultCurrency || 'USD';
    const convertedAmount = convertCurrency(origAmount, entryCurrency, userDefault);

    const depositId = crypto.randomUUID();
    let linkedAccId = '';
    let linkedTxId = '';

    if (chosenAccountId.value) {
      linkedAccId = chosenAccountId.value;
      linkedTxId = crypto.randomUUID();

      const accToDebit = accountGroups.value.find(g => g.id === chosenAccountId.value);
      if (accToDebit) {
        const isCC = accToDebit.accountType === 'credit_card';
        const accCurrency = accToDebit.currencyCode || 'USD';
        const accAmt = convertCurrency(origAmount, entryCurrency, accCurrency);

        const txData = {
          id: linkedTxId,
          groupId: chosenAccountId.value,
          accountId: chosenAccountId.value,
          amount: -accAmt,
          description: `Savings Goal Contribution: ${activeGoalForDeposit.value.name}`,
          category: 'Savings',
          date: Timestamp.fromDate(new Date(depositDate.value)),
          createdAt: Timestamp.now(),
          type: 'expense',
          note: `Auto-linked from Savings Goal: ${activeGoalForDeposit.value.name}`
        };

        await setDoc(doc(db, 'groups', chosenAccountId.value, 'account_transactions', linkedTxId), txData);

        let activeBal = parseFloat(accToDebit.balance as any || 0);
        if (isCC) {
          activeBal = activeBal + accAmt;
        } else {
          activeBal = activeBal - accAmt;
        }
        await updateDoc(doc(db, 'groups', chosenAccountId.value), { balance: activeBal });
      }
    }

    const depData: any = {
      amount: convertedAmount,
      originalAmount: origAmount,
      currencyCode: entryCurrency,
      depositedBy: props.user.uid,
      note: depositNote.value.trim(),
      date: Timestamp.fromDate(new Date(depositDate.value)),
    };

    if (linkedAccId && linkedTxId) {
      depData.linkedAccountId = linkedAccId;
      depData.linkedTransactionId = linkedTxId;
    }

    await setDoc(doc(db, 'groups', props.groupId, 'saving_goals', activeGoalForDeposit.value.id, 'deposits', depositId), depData);
    
    isAddDepositOpen.value = false;
    activeGoalForDeposit.value = null;
    depositAmount.value = '';
    depositNote.value = '';
    chosenAccountId.value = '';
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, `groups/${props.groupId}/saving_goals/deposits`);
  } finally {
    isCreatingDeposit.value = false;
  }
};

const handleDeleteDeposit = async () => {
  if (!depositToDelete.value) return;

  try {
    const dep = depositToDelete.value.deposit;
    if (dep.linkedAccountId && dep.linkedTransactionId) {
      const oldAccId = dep.linkedAccountId;
      const oldTxId = dep.linkedTransactionId;
      const oldOrigAmt = dep.originalAmount ?? dep.amount;

      const accDocObj = await getDoc(doc(db, 'groups', oldAccId));
      if (accDocObj.exists()) {
        const accData = accDocObj.data() as Group;
        let oldBal = parseFloat(accData.balance as any || 0);
        if (accData.accountType === 'credit_card') {
          oldBal = oldBal - oldOrigAmt;
        } else {
          oldBal = oldBal + oldOrigAmt;
        }
        await updateDoc(doc(db, 'groups', oldAccId), { balance: oldBal });
      }
      await deleteDoc(doc(db, 'groups', oldAccId, 'account_transactions', oldTxId));
    }

    await deleteDeposit(props.groupId, depositToDelete.value.goalId, dep.id);
    depositToDelete.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/deposits/${depositToDelete.value.deposit.id}`);
  }
};

// Group Settings Editor logic
const handleUpdateSettings = async () => {
  if (!editName.value.trim()) return;
  try {
    await updateGroupSettings(props.groupId, {
      name: editName.value.trim(),
      description: editDescription.value.trim(),
      currencyCode: editGroupCurrency.value,
      type: editGroupType.value as any
    });
    isSettingsOpen.value = false;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/${props.groupId}`);
  }
};

const handleDeleteGroup = async () => {
  try {
    await deleteGroup(props.groupId);
    emit('back');
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/${props.groupId}`);
  }
};

// AI Savings Insights (Communication Symmetry!)
const handleAnalyzeSavings = async () => {
  isAnalyzing.value = true;
  isAnalysisModalOpen.value = true;
  analysisResult.value = null;

  try {
    const goalsSummary = goals.value.map(g => {
      const saved = getGoalSavedAmount(g.id, g.currencyCode);
      const recentDeps = (deposits.value[g.id] || []).slice(0, 3).map(d => ({
        amount: d.originalAmount || d.amount,
        currency: d.currencyCode,
        note: d.note,
        date: d.date?.toDate ? d.date.toDate().toLocaleDateString() : String(d.date)
      }));
      return {
        name: g.name,
        category: g.category,
        targetAmount: g.targetAmount,
        currency: g.currencyCode,
        currentSaved: saved,
        percentComplete: g.targetAmount > 0 ? ((saved / g.targetAmount) * 100).toFixed(1) + '%' : '0%',
        recentDeposits: recentDeps
      };
    });

    const response = await fetch('/api/analyze-savings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        groupName: group.value?.name,
        groupType: group.value?.type,
        totalTarget: totalTargetValue.value,
        totalSaved: totalSavedValue.value,
        goalsSummary
      })
    });

    const output = await response.json();
    analysisResult.value = output.text || "No insights could be generated.";
  } catch (error: any) {
    console.error("AI Analysis Error:", error);
    analysisResult.value = "Sorry, I encountered an error while communicating with the analysis backend. Please make sure the app was fully restarted and build complete.";
  } finally {
    isAnalyzing.value = false;
  }
};

const parsedAnalysisResult = computed(() => {
  if (!analysisResult.value) return '';
  let html = analysisResult.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  
  // Headers
  html = html.replace(/^### (.*$)/gm, '<h3 class="text-base font-bold text-zinc-900 dark:text-white mt-4 mb-2">$1</h3>');
  html = html.replace(/^## (.*$)/gm, '<h2 class="text-lg font-bold text-zinc-900 dark:text-white mt-5 mb-2">$1</h2>');
  html = html.replace(/^# (.*$)/gm, '<h1 class="text-xl font-bold text-zinc-900 dark:text-white mt-6 mb-3">$1</h1>');
  
  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-zinc-900 dark:text-white">$1</strong>');
  
  // Bullet points
  html = html.replace(/^\s*[\-\*]\s+(.*$)/gm, '<li class="ml-4 list-disc text-sm text-zinc-600 dark:text-zinc-300 my-1">$1</li>');
  
  // Paragraphs
  html = html.replace(/^\s*$/gm, '<br/>');
  
  return html;
});

// Trigger Native Print Previews
const handlePrintReport = () => {
  window.print();
};

// Computed Stats & Aggregations
const totalTargetValue = computed(() => {
  const userCurrency = props.user?.defaultCurrency || 'USD';
  return goals.value.reduce((sum, g) => {
    return sum + convertCurrency(g.targetAmount, g.currencyCode || 'USD', userCurrency);
  }, 0);
});

const totalSavedValue = computed(() => {
  const userCurrency = props.user?.defaultCurrency || 'USD';
  let totalSaved = 0;
  goals.value.forEach(goal => {
    const goalDeposits = deposits.value[goal.id] || [];
    goalDeposits.forEach(dep => {
      totalSaved += convertCurrency(dep.originalAmount ?? dep.amount, dep.currencyCode ?? 'USD', userCurrency);
    });
  });
  return totalSaved;
});

// Calculate particular progress for a specific goal
const getGoalSavedAmount = (goalId: string, currency: string) => {
  const goalDeposits = deposits.value[goalId] || [];
  let sum = 0;
  goalDeposits.forEach(dep => {
    sum += convertCurrency(dep.originalAmount ?? dep.amount, dep.currencyCode ?? 'USD', currency);
  });
  return sum;
};

const getConvertedExpenseAmount = (amount: number, fromCurrency: string) => {
  return convertCurrency(amount, fromCurrency, props.user?.defaultCurrency || 'USD');
};

const getGoalCategoryColor = (category: string) => {
  switch (category) {
    case 'Vacation & Travel':
      return 'bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-100 dark:border-sky-500/20';
    case 'Home & Property':
      return 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-100 dark:border-amber-500/20';
    case 'Vehicle & Transport':
      return 'bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-100 dark:border-purple-500/20';
    case 'Emergency Fund':
      return 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-100 dark:border-rose-500/20';
    case 'Gadget & Appliance':
      return 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-100 dark:border-indigo-500/20';
    case 'Education':
      return 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-500/20';
    case 'Investment':
      return 'bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-100 dark:border-teal-500/20';
    default:
      return 'bg-zinc-50 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 border-zinc-200 dark:border-zinc-700';
  }
};

// 1. Aggressively compile deposits across the entire group (Recent Deposits feature request!)
const allGroupDeposits = computed(() => {
  const list: { id: string; deposit: Deposit; goalId: string; goalName: string; category: string }[] = [];
  goals.value.forEach(goal => {
    const goalDeps = deposits.value[goal.id] || [];
    goalDeps.forEach(dep => {
      list.push({
        id: dep.id,
        deposit: dep,
        goalId: goal.id,
        goalName: goal.name,
        category: goal.category
      });
    });
  });
  // Sort descending by date
  return list.sort((a,b) => {
    const timeA = a.deposit.date?.toMillis ? a.deposit.date.toMillis() : new Date(a.deposit.date as any).getTime();
    const timeB = b.deposit.date?.toMillis ? b.deposit.date.toMillis() : new Date(b.deposit.date as any).getTime();
    return timeB - timeA;
  });
});

// 2. Alert engine for Savings goals (Alert feature request!)
const goalsAlerts = computed(() => {
  const alertsList: { type: 'success' | 'encouragement' | 'info'; title: string; message: string; dateLabel?: string }[] = [];
  
  if (goals.value.length === 0) return alertsList;

  goals.value.forEach(g => {
    const saved = getGoalSavedAmount(g.id, g.currencyCode);
    const target = g.targetAmount;
    if (target <= 0) return;

    const percent = (saved / target) * 100;
    if (percent >= 100) {
      alertsList.push({
        type: 'success',
        title: 'Goal Fully Achieved! 🏆',
        message: `Congratulations! You have successfully reached 100% of your target for "${g.name}" by accumulating ${getCurrencySymbol(g.currencyCode)}${formatCurrency(saved)}.`
      });
    } else if (percent >= 80) {
      alertsList.push({
        type: 'encouragement',
        title: 'Just Moments Away! 🌟',
        message: `You are incredibly close to finishing the "${g.name}" milestone! You've funded ${percent.toFixed(0)}%. Just ${getCurrencySymbol(g.currencyCode)}${formatCurrency(target - saved)} left to go.`
      });
    }
  });

  // If no specific single alert is available, give a nice general status indicator alert
  if (alertsList.length === 0 && totalTargetValue.value > 0) {
    const combinedPercent = (totalSavedValue.value / totalTargetValue.value) * 100;
    if (combinedPercent > 0) {
      alertsList.push({
        type: 'info',
        title: 'Savings Pace Tracker ⚡',
        message: `Your collective goals are ${combinedPercent.toFixed(0)}% funded! You have saved a total of ${getCurrencySymbol(props.user.defaultCurrency)}${formatCurrency(totalSavedValue.value)} so far. Consistent habits build secure futures!`
      });
    }
  }

  return alertsList;
});

// Computes category-wise saving targets & aggregates for print report
const categoryPrintedSummary = computed(() => {
  const summary: Record<string, { target: number; saved: number; count: number }> = {};
  
  savingCategories.value.forEach(cat => {
    summary[cat] = { target: 0, saved: 0, count: 0 };
  });

  const userDefault = props.user?.defaultCurrency || 'USD';

  goals.value.forEach(goal => {
    const cat = goal.category || 'Other';
    if (!summary[cat]) {
      summary[cat] = { target: 0, saved: 0, count: 0 };
    }
    const convertedTarget = convertCurrency(goal.targetAmount, goal.currencyCode, userDefault);
    const convertedSaved = convertCurrency(getGoalSavedAmount(goal.id, goal.currencyCode), goal.currencyCode, userDefault);
    
    summary[cat].target += convertedTarget;
    summary[cat].saved += convertedSaved;
    summary[cat].count += 1;
  });

  return Object.entries(summary)
    .filter(([_, data]) => data.count > 0 || data.saved > 0)
    .map(([category, data]) => ({
      name: category,
      target: data.target,
      saved: data.saved,
      count: data.count,
      progress: data.target > 0 ? (data.saved / data.target) * 100 : 0
    }));
});
</script>

<template>
  <div class="max-w-6xl mx-auto">
    <!-- Wrap all screen-only items in print:hidden so they are cleanly removed during browser print -->
    <div class="print:hidden">
      <!-- Back Navigation -->
      <button 
        id="back-to-hub-btn"
      @click="$emit('back')"
      class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:border-zinc-300 dark:hover:border-zinc-700 rounded-xl transition-all duration-200 mb-10 group shadow-sm cursor-pointer outline-none"
    >
      <ArrowLeft class="w-4 h-4 transition-transform group-hover:-translate-x-1" />
      <span class="text-sm font-bold">Back to Saving Goals Hub</span>
    </button>

    <!-- Header Section -->
    <header class="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-12" v-if="group">
      <div>
        <div class="flex items-center gap-3 mb-2">
          <span :class="`text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-lg border font-mono ${group.type === 'personal' ? 'bg-blue-50/55 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-500/20' : group.type === 'household' ? 'bg-emerald-50/55 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-500/20' : 'bg-orange-50/55 dark:bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-100 dark:border-orange-500/20'}`">
            {{ group.type }} saving group
          </span>
        </div>
        <h1 class="text-4xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">{{ group.name }} Goals</h1>
        <p class="text-zinc-500 dark:text-zinc-400 mt-1 max-w-xl">{{ group.description || 'Track your saving targets and mutual savings balances.' }}</p>
      </div>

      <!-- Action items: Print, Settings, AI Insights, Add Goal (Development Pattern Consistency!) -->
      <div class="flex flex-wrap items-center gap-2.5 w-full lg:w-auto">
        <!-- Print Button (Print report feature request!) -->
        <button 
          @click="handlePrintReport"
          class="p-3.5 bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 text-zinc-500 hover:text-zinc-950 dark:hover:text-white rounded-2xl transition-all hover:bg-zinc-50 dark:hover:bg-zinc-900 shadow-sm flex items-center justify-center cursor-pointer cursor-print pointer-events-auto shrink-0"
          title="Print Savings Goals Report"
        >
          <Printer class="w-5 h-5 text-zinc-500" />
          <span class="hidden sm:inline text-xs font-bold ml-2">Print</span>
        </button>

        <!-- Group Settings Button (Settings beside AI inside request!) -->
        <button 
          v-if="user.uid === group.createdBy"
          @click="isSettingsOpen = true"
          class="p-3.5 bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 text-zinc-500 hover:text-zinc-950 dark:hover:text-white rounded-2xl transition-all hover:bg-zinc-50 dark:hover:bg-zinc-900 shadow-sm flex items-center justify-center cursor-pointer pointer-events-auto shrink-0"
          title="Group Settings"
        >
          <MoreVertical class="w-5 h-5" />
        </button>

        <!-- AI Insights Button (AI Inside beside settings request!) -->
        <button 
          @click="handleAnalyzeSavings"
          :disabled="isAnalyzing"
          class="flex items-center justify-center gap-2 px-5 py-3.5 bg-gradient-to-br from-teal-600 to-emerald-600 text-white rounded-2xl text-sm font-bold hover:from-teal-700 hover:to-emerald-700 hover:shadow-xl hover:shadow-teal-500/40 transition-all disabled:opacity-50 shadow-lg shadow-teal-500/20 active:scale-95 cursor-pointer pointer-events-auto shrink-0"
        >
          <Loader2 v-if="isAnalyzing" class="w-4 h-4 animate-spin" />
          <Sparkles v-else class="w-4 h-4" />
          AI Insights
        </button>

        <!-- Create Savings Goal button -->
        <button 
          @click="openAddGoalModal"
          class="flex items-center justify-center gap-2 px-6 py-3.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl text-sm font-bold hover:shadow-xl hover:shadow-teal-600/30 transition-all shadow-md shadow-teal-600/10 active:scale-95 cursor-pointer outline-none shrink-0"
        >
          <Plus class="w-4.5 h-4.5" />
          Add Savings Goal
        </button>
      </div>
    </header>

    <!-- Loading screen -->
    <div v-if="loading" class="flex items-center justify-center p-20">
      <Loader2 class="w-8 h-8 text-teal-600 animate-spin" />
    </div>

    <template v-else>
      <!-- Savings Progress Alerts & Motivational system (Active alerts feature request!) -->
      <transition-group name="fade" tag="div" class="space-y-4 mb-10 print:hidden" v-if="goalsAlerts.length > 0">
        <div 
          v-for="(alert, index) in goalsAlerts" 
          :key="index"
          :class="[
            'p-5 rounded-[24px] border flex gap-4 items-start shadow-sm transition-all duration-300',
            alert.type === 'success' 
              ? 'bg-emerald-50/75 dark:bg-emerald-900/10 border-emerald-200 dark:border-emerald-800/30 text-emerald-900 dark:text-emerald-300' 
              : alert.type === 'encouragement'
              ? 'bg-amber-50/75 dark:bg-amber-900/10 border-amber-200 dark:border-amber-800/30 text-amber-900 dark:text-amber-300'
              : 'bg-teal-50/75 dark:bg-teal-900/10 border-teal-200 dark:border-teal-800/30 text-teal-900 dark:text-teal-300'
          ]"
        >
          <div :class="[
            'p-2.5 rounded-2xl shrink-0 mt-0.5',
            alert.type === 'success' ? 'bg-emerald-500/10' : alert.type === 'encouragement' ? 'bg-amber-500/10' : 'bg-teal-500/10'
          ]">
            <Sparkles v-if="alert.type === 'success'" class="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            <AlertCircle v-else-if="alert.type === 'encouragement'" class="w-5 h-5 text-amber-600 dark:text-amber-400" />
            <PiggyBank v-else class="w-5 h-5 text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <h4 class="font-bold text-sm tracking-tight">{{ alert.title }}</h4>
            <p class="text-xs mt-1 leading-relaxed opacity-90">{{ alert.message }}</p>
          </div>
        </div>
      </transition-group>

      <!-- Target & Progress summary card -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <div class="bg-white dark:bg-zinc-900 p-8 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">Combined Target</span>
            <p class="text-3xl font-bold font-mono text-zinc-900 dark:text-white mt-1">
              {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalTargetValue) }}
            </p>
          </div>
          <p class="text-xs text-zinc-500 dark:text-zinc-400 font-medium mt-4">Calculated in your default active currency</p>
        </div>

        <div class="bg-white dark:bg-zinc-900 p-8 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between">
          <div>
            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">Combined Saved</span>
            <p class="text-3xl font-bold font-mono text-teal-600 dark:text-teal-400 mt-1">
              {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalSavedValue) }}
            </p>
          </div>
          <p class="text-xs text-zinc-500 dark:text-zinc-400 font-medium mt-4">Progress: {{ totalTargetValue > 0 ? ((totalSavedValue / totalTargetValue) * 100).toFixed(0) : 0 }}% of goal reached</p>
        </div>

        <div class="bg-white dark:bg-zinc-900 p-8 rounded-[32px] border border-zinc-200 dark:border-zinc-800 shadow-sm flex flex-col justify-between md:col-span-1">
          <div>
            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-display">Goals Completion</span>
            <p class="text-3xl font-bold text-zinc-900 dark:text-white mt-1">
              {{ goals.filter(g => getGoalSavedAmount(g.id, g.currencyCode) >= g.targetAmount).length }}
              <span class="text-lg font-medium text-zinc-400 dark:text-zinc-500">/ {{ goals.length }} Completed</span>
            </p>
          </div>
          <div class="h-2 bg-zinc-200 dark:bg-white/10 rounded-full mt-4 overflow-hidden">
            <div 
              class="h-full bg-teal-500 rounded-full"
              :style="{ width: `${goals.length > 0 ? (goals.filter(g => getGoalSavedAmount(g.id, g.currencyCode) >= g.targetAmount).length / goals.length) * 100 : 0}%` }"
            />
          </div>
        </div>
      </div>

      <!-- Saving Goals Grid -->
      <section class="space-y-6">
        <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display mb-6">Goals in Progress</h2>
        
        <div v-if="goals.length === 0" class="p-20 bg-white dark:bg-zinc-900 rounded-[32px] border border-zinc-200 dark:border-zinc-800 text-center shadow-sm">
          <div class="w-16 h-16 bg-zinc-100 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
            <Target class="w-8 h-8 text-zinc-400 dark:text-zinc-600" />
          </div>
          <h3 class="text-lg font-bold text-zinc-900 dark:text-white mb-1">No saving goals defined</h3>
          <p class="text-zinc-500 dark:text-zinc-400 max-w-sm mx-auto text-sm leading-relaxed">Let's create your first saving goal for this group today. Perfect for vacations, emergency funds, or equipment purchases.</p>
        </div>
 
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div 
            v-for="goal in goals" 
            :key="goal.id"
            class="bg-white dark:bg-zinc-900 p-8 rounded-[40px] border border-zinc-200 dark:border-zinc-800 shadow-sm relative group flex flex-col justify-between gap-6"
          >
            <div>
            <div class="flex items-start justify-between gap-4">
              <div class="min-w-0 flex-1">
                <span :class="`inline-block text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg border font-mono ${getGoalCategoryColor(goal.category)}`">
                  {{ goal.category }}
                </span>
                <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-3 font-display break-words leading-tight">{{ goal.name }}</h3>
              </div>
              
              <!-- Quick tools for Goal -->
              <div class="flex items-center gap-1 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-all duration-200 shrink-0 ml-4">
                <button 
                  @click="openEditGoalModal(goal)"
                  class="p-2 text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded-xl active:scale-90 transition-all duration-150 cursor-pointer outline-none"
                  title="Edit savings goal"
                >
                  <Pencil class="w-4 h-4" />
                </button>
                <button 
                  @click="goalToDelete = goal"
                  class="p-2 text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-zinc-50 dark:hover:bg-zinc-800 rounded-xl active:scale-90 transition-all duration-150 cursor-pointer outline-none"
                  title="Delete goal"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
              </div>
            </div>

              <!-- Metrics -->
              <div class="mt-8 grid grid-cols-2 gap-4">
                <div>
                  <span class="text-[9px] font-bold uppercase tracking-wider text-zinc-400">Total Saved</span>
                  <p class="text-xl font-bold font-mono text-zinc-950 dark:text-white">
                    {{ getCurrencySymbol(goal.currencyCode) }}{{ formatCurrency(getGoalSavedAmount(goal.id, goal.currencyCode)) }}
                  </p>
                  <p v-if="goal.currencyCode !== user.defaultCurrency" class="text-[9px] text-zinc-400 font-mono">
                    ≈ {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(getConvertedExpenseAmount(getGoalSavedAmount(goal.id, goal.currencyCode), goal.currencyCode)) }}
                  </p>
                </div>
                <div>
                  <span class="text-[9px] font-bold uppercase tracking-wider text-zinc-400 font-display">Target Amount</span>
                  <p class="text-xl font-semibold font-mono text-zinc-500 dark:text-zinc-400">
                    {{ getCurrencySymbol(goal.currencyCode) }}{{ formatCurrency(goal.targetAmount) }}
                  </p>
                  <p v-if="goal.currencyCode !== user.defaultCurrency" class="text-[9px] text-zinc-500 font-mono">
                    ≈ {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(getConvertedExpenseAmount(goal.targetAmount, goal.currencyCode)) }}
                  </p>
                </div>
              </div>

              <!-- Visual progress bar -->
              <div class="mt-6 flex items-center justify-between gap-4">
                <div class="h-2 bg-zinc-100 dark:bg-white/10 rounded-full flex-1 overflow-hidden">
                  <div 
                    :class="`h-full rounded-full transition-all duration-700 ease-out ${getGoalSavedAmount(goal.id, goal.currencyCode) >= goal.targetAmount ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' : 'bg-teal-500'}`"
                    :style="{ width: `${Math.min(100, (getGoalSavedAmount(goal.id, goal.currencyCode) / goal.targetAmount) * 100)}%` }"
                  />
                </div>
                <span class="font-mono text-xs font-bold text-teal-600 dark:text-teal-400">
                  {{ ((getGoalSavedAmount(goal.id, goal.currencyCode) / goal.targetAmount) * 100).toFixed(0) }}%
                </span>
              </div>
            </div>

            <!-- List of Deposits inside this Goal -->
            <div class="border-t border-zinc-100 dark:border-zinc-800 pt-6">
              <div class="flex items-center justify-between mb-4">
                <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest font-display">Past Deposits</span>
                <button 
                  @click="openAddDepositModal(goal)"
                  class="flex items-center gap-1 text-[10px] font-bold text-teal-650 hover:text-teal-700 px-2.5 py-1 bg-teal-50 dark:bg-teal-500/10 rounded-lg transition-colors border border-teal-100 dark:border-teal-500/15 cursor-pointer"
                >
                  <Coins class="w-3.5 h-3.5" />
                  Commit Deposit
                </button>
              </div>

              <div v-if="!deposits[goal.id] || deposits[goal.id].length === 0" class="py-6 text-center">
                <p class="text-xs text-zinc-400 italic">No deposits saved for this goal.</p>
              </div>
              <div v-else class="space-y-2 max-h-[160px] overflow-y-auto pr-1 select-none custom-scrollbar">
                <div 
                  v-for="dep in deposits[goal.id]" 
                  :key="dep.id"
                  class="flex items-center justify-between p-3.5 rounded-xl bg-zinc-50 dark:bg-white/5 border border-zinc-200/50 dark:border-white/5 text-sm hover:bg-zinc-100/50 dark:hover:bg-white/10 group/item relative transition-all"
                >
                  <div class="min-w-0">
                    <p v-if="dep.note" class="font-bold text-zinc-800 dark:text-zinc-200 truncate">{{ dep.note }}</p>
                    <p v-else class="text-xs text-zinc-500 dark:text-zinc-400 italic">Anonymous savings contribution</p>
                    <p class="text-[10px] text-zinc-500 dark:text-zinc-400 font-mono mt-0.5">
                      {{ dep.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
                    </p>
                  </div>
                  <div class="text-right shrink-0">
                    <p class="font-mono font-bold text-teal-650 dark:text-teal-400">
                      +{{ getCurrencySymbol(dep.currencyCode) }}{{ formatCurrency(dep.originalAmount) }}
                    </p>
                    <button 
                      v-if="dep.depositedBy === user.uid"
                      @click="depositToDelete = { deposit: dep, goalId: goal.id }"
                      class="absolute right-2 bottom-1.5 p-1 bg-white dark:bg-zinc-800 text-zinc-400 hover:text-red-600 rounded shadow border border-zinc-100 dark:border-zinc-700 opacity-0 group-hover/item:opacity-100 transition-opacity"
                      title="Delete deposit entry"
                    >
                      <Trash2 class="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Recent Saving Deposits Table (Recent deposits request!) -->
      <section class="mt-14 print:hidden">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Recent Savings Deposits</h2>
            <p class="text-xs text-zinc-500 dark:text-zinc-450 mt-1">Sustained deposit ledger across all defined group goals</p>
          </div>
        </div>

        <div v-if="allGroupDeposits.length === 0" class="p-12 text-center bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[32px] shadow-sm">
          <p class="text-sm text-zinc-500 dark:text-zinc-400 italic">No deposits have been committed to any goals yet.</p>
        </div>

        <!-- Desktop Ledger View -->
        <div v-else class="hidden md:block bg-white dark:bg-[#091014] border border-zinc-200 dark:border-white/5 rounded-[32px] overflow-hidden shadow-sm">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="border-b border-zinc-100 dark:border-white/5 bg-zinc-50/50 dark:bg-white/[0.03]">
                <th class="p-5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono">Date</th>
                <th class="p-5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono">Member</th>
                <th class="p-5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono">Savings Goal & Category</th>
                <th class="p-5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono">Note / Memo</th>
                <th class="p-5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono text-right">Committed Amount</th>
                <th class="p-5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono text-right">Value ({{ user.defaultCurrency }})</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-zinc-50 dark:divide-white/5">
              <tr 
                v-for="{ deposit: dep, goalName, category, goalId } in allGroupDeposits" 
                :key="dep.id"
                class="hover:bg-zinc-50/50 dark:hover:bg-white/[0.01] transition-colors"
              >
                <!-- Date -->
                <td class="p-5 font-mono text-xs font-bold text-zinc-900 dark:text-zinc-100">
                  {{ dep.date?.toDate ? dep.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : String(dep.date) }}
                </td>
                
                <!-- Contributor -->
                <td class="p-5">
                  <div class="flex items-center gap-2">
                    <div class="w-7 h-7 bg-teal-50 dark:bg-teal-500/10 border border-teal-100 dark:border-teal-500/15 rounded-full flex items-center justify-center font-bold text-xs text-teal-600 dark:text-teal-400 font-display">
                      {{ (members.find(m => m.uid === dep.depositedBy)?.displayName || user.displayName || 'G')[0].toUpperCase() }}
                    </div>
                    <span class="text-sm font-bold text-zinc-800 dark:text-zinc-200">
                      {{ members.find(m => m.uid === dep.depositedBy)?.displayName || (dep.depositedBy === user.uid ? 'You' : 'Anonymous Member') }}
                    </span>
                  </div>
                </td>

                <!-- Goal Name & Category Badge -->
                <td class="p-5">
                  <div class="flex flex-col gap-1 items-start">
                    <span class="text-sm font-bold text-zinc-900 dark:text-white">{{ goalName }}</span>
                    <span :class="['text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border-none', getGoalCategoryColor(category)]">
                      {{ category }}
                    </span>
                  </div>
                </td>

                <!-- Note -->
                <td class="p-5 text-sm text-zinc-500 dark:text-zinc-400">
                  <span v-if="dep.note" class="italic">"{{ dep.note }}"</span>
                  <span v-else class="text-zinc-400 dark:text-zinc-500 italic block">None</span>
                </td>

                <!-- Original Amount -->
                <td class="p-5 text-right font-mono text-sm font-extrabold text-teal-650 dark:text-teal-400">
                  +{{ getCurrencySymbol(dep.currencyCode) }}{{ formatCurrency(dep.originalAmount) }}
                </td>

                <!-- Base Converted Value -->
                <td class="p-5 text-right font-mono text-xs font-bold text-zinc-400 dark:text-zinc-500">
                  {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertCurrency(dep.originalAmount, dep.currencyCode, user.defaultCurrency)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Mobile Layout Card list -->
        <div class="md:hidden space-y-4">
          <div 
            v-for="{ id, deposit: dep, goalName, category, goalId } in allGroupDeposits" 
            :key="id"
            class="bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 p-5 rounded-3xl"
          >
            <div class="flex justify-between items-start mb-3">
              <span class="text-[10px] font-mono font-bold text-zinc-500">
                {{ dep.date?.toDate ? dep.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : String(dep.date) }}
              </span>
              <span :class="['text-[8px] font-bold uppercase tracking-widest px-2 py-0.5 rounded border-none', getGoalCategoryColor(category)]">
                {{ category }}
              </span>
            </div>
            
            <h4 class="font-bold text-zinc-900 dark:text-white text-sm mb-1">{{ goalName }}</h4>
            <p v-if="dep.note" class="text-xs text-zinc-500 dark:text-zinc-400 italic mb-4">"{{ dep.note }}"</p>
            
            <div class="flex items-center justify-between border-t border-zinc-100 dark:border-white/5 pt-3">
              <div class="flex items-center gap-2">
                <div class="w-6 h-6 bg-teal-50 dark:bg-teal-500/10 border border-teal-100 dark:border-teal-500/20 rounded-full flex items-center justify-center font-bold text-[10px] text-teal-600 dark:text-teal-400">
                  {{ (members.find(m => m.uid === dep.depositedBy)?.displayName || user.displayName || 'G')[0].toUpperCase() }}
                </div>
                <span class="text-xs text-zinc-600 dark:text-zinc-300 font-bold">
                  {{ members.find(m => m.uid === dep.depositedBy)?.displayName || (dep.depositedBy === user.uid ? 'You' : 'Member') }}
                </span>
              </div>
              <p class="font-mono font-extrabold text-teal-600 dark:text-teal-400 text-sm">
                +{{ getCurrencySymbol(dep.currencyCode) }}{{ formatCurrency(dep.originalAmount) }}
              </p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <!-- Create Goal Modal -->
    <transition name="fade">
      <div v-if="isAddGoalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddGoalOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">New Saving Goal</h3>
            <button @click="isAddGoalOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer outline-none text-zinc-500">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleCreateGoal" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Goal Title</label>
              <input
                type="text"
                v-model="goalName"
                placeholder="e.g. Summer Cruise, Car Downpayment"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white shadow-inner"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Category</label>
                <select
                  v-model="goalCategory"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="cat in savingCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Currency</label>
                <select
                  v-model="goalCurrencyCode"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Goal Amount</label>
              <div class="relative">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                  {{ getCurrencySymbol(goalCurrencyCode) }}
                </span>
                <input
                  type="number"
                  step="0.01"
                  v-model="goalTarget"
                  placeholder="0.00"
                  class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              :disabled="isCreatingGoal"
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-teal-600/10"
            >
              <Loader2 v-if="isCreatingGoal" class="w-5 h-5 animate-spin" />
              <template v-else>Define Goal</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Edit Goal Modal -->
    <transition name="fade">
      <div v-if="isEditGoalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isEditGoalOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Saving Goal</h3>
            <button @click="isEditGoalOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer outline-none text-zinc-500">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateGoal" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Goal Title</label>
              <input
                type="text"
                v-model="editGoalName"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white shadow-inner"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Category</label>
                <select
                  v-model="editGoalCategory"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="cat in savingCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Currency</label>
                <select
                  v-model="editGoalCurrencyCode"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Goal Amount</label>
              <div class="relative">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                  {{ getCurrencySymbol(editGoalCurrencyCode) }}
                </span>
                <input
                  type="number"
                  step="0.01"
                  v-model="editGoalTarget"
                  class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              :disabled="isSavingGoal"
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-teal-600/10"
            >
              <Loader2 v-if="isSavingGoal" class="w-5 h-5 animate-spin" />
              <template v-else>Save Changes</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Goal Delete Modal -->
    <transition name="fade">
      <div v-if="goalToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="goalToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 border border-red-100 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Delete Savings Goal?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            Are you sure you want to delete this saving goal and all associated deposits? This action cannot be undone.
          </p>
          <div class="flex gap-4">
            <button
              @click="goalToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-950 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteGoal"
              class="flex-1 py-4 bg-red-600 text-white rounded-2xl font-bold hover:bg-red-700 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Commit Deposit Modal -->
    <transition name="fade">
      <div v-if="isAddDepositOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddDepositOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Commit Deposit</h3>
            <button @click="isAddDepositOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer outline-none text-zinc-500">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleCreateDeposit" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Amount & Currency Signature</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                    {{ getCurrencySymbol(depositCurrencyCode) }}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    v-model="depositAmount"
                    placeholder="0.00"
                    class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                    required
                  />
                </div>
                <div class="w-32 shrink-0">
                  <select
                    v-model="depositCurrencyCode"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
              <p v-if="depositCurrencyCode !== user.defaultCurrency" class="text-[10px] text-zinc-400 mt-2 font-medium font-mono">
                Converts to approx. {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertCurrency(parseFloat(depositAmount || '0'), depositCurrencyCode, user.defaultCurrency)) }}
              </p>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Deposit Memo</label>
              <input
                type="text"
                v-model="depositNote"
                placeholder="e.g. Saved from dinner, salary contribution"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white shadow-inner"
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Deposit Date</label>
              <input
                type="date"
                v-model="depositDate"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white shadow-inner"
                required
              />
            </div>

            <!-- Funding source Account / Card -->
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display font-semibold">Fund from Account / Card</label>
              <select
                v-model="chosenAccountId"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all text-sm font-semibold dark:text-white appearance-none cursor-pointer"
              >
                <option value="">-- Cash or External --</option>
                <option 
                  v-for="acc in accountGroups" 
                  :key="acc.id" 
                  :value="acc.id"
                >
                  {{ acc.name }} ({{ formatCurrency(acc.balance || 0, acc.currencyCode || 'USD') }})
                </option>
              </select>
            </div>

            <button
              type="submit"
              :disabled="isCreatingDeposit"
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-teal-600/15"
            >
              <Loader2 v-if="isCreatingDeposit" class="w-5 h-5 animate-spin" />
              <template v-else>Deposit Funds</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Delete Deposit Confirmation -->
    <transition name="fade">
      <div v-if="depositToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="depositToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 border border-red-100 dark:border-red-500/20 text-red-600">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-4 font-display">Delete Deposit entry?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 mb-10 leading-relaxed text-sm">
            Are you sure you want to delete this deposit entry? This will subtract the amount from the goal's overall savings progress.
          </p>
          <div class="flex gap-4">
            <button
              @click="depositToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-750 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteDeposit"
              class="flex-1 py-4 bg-red-600 text-white rounded-2xl font-bold hover:bg-red-700 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Group Settings Modal (Symmetrical with Budget and Expense settings editor!) -->
    <transition name="fade">
      <div v-if="isSettingsOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isSettingsOpen = false" class="absolute inset-0 bg-zinc-950/65 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg bg-white dark:bg-[#0c1216] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display flex items-center gap-2">
              <Briefcase class="w-6 h-6 text-teal-500" />
              Group Configuration
            </h3>
            <button @click="isSettingsOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer text-zinc-500">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateSettings" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Group Name</label>
              <input
                type="text"
                v-model="editName"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white"
                required
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Description</label>
              <textarea
                v-model="editDescription"
                rows="3"
                placeholder="Brief summary or savings guidelines..."
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white resize-none"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Group Type</label>
                <select
                  v-model="editGroupType"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option value="personal">Personal</option>
                  <option value="household">Household</option>
                  <option value="trip">Trip & Travel</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Default Currency</label>
                <select
                  v-model="editGroupCurrency"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.legend }} ({{ c.code }})</option>
                </select>
              </div>
            </div>

            <button
              type="submit"
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all mt-4 hover:shadow-xl hover:shadow-teal-600/25 cursor-pointer flex items-center justify-center shadow-lg"
            >
              Save Settings
            </button>

            <!-- Symmetrical Admin/Owner only Delete button -->
            <div class="pt-8 border-t border-zinc-200 dark:border-white/5">
              <button
                type="button"
                @click="isSettingsOpen = false; isDeleteGroupConfirmOpen = true"
                class="w-full py-4 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 rounded-2xl font-bold hover:bg-red-100 dark:hover:bg-red-500/20 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer border border-transparent dark:border-red-900/10"
              >
                <Trash2 class="w-5 h-5" />
                Delete Group
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- Symmetrical Delete Group Confirmation Modal -->
    <transition name="fade">
      <div v-if="isDeleteGroupConfirmOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div @click="isDeleteGroupConfirmOpen = false" class="absolute inset-0 bg-zinc-950/65 backdrop-blur-sm" />
        <div class="relative w-full max-w-sm bg-white dark:bg-[#0c1216] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 text-center outline-none z-10 transition-all">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 border border-red-105 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">Delete Savings Group?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-10 leading-relaxed">
            This will permanently delete the group <strong class="text-zinc-900 dark:text-zinc-100">{{ group ? group.name : '' }}</strong> and all its recorded saving goals and deposits. This action cannot be undone.
          </p>
          <div class="flex gap-4">
            <button
              @click="isDeleteGroupConfirmOpen = false"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteGroup"
              class="flex-1 py-4 bg-red-600 hover:bg-red-700 text-white rounded-2xl font-bold transition-all active:scale-95 cursor-pointer shadow-lg shadow-red-550/20 hover:shadow-xl hover:shadow-red-600/30"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- AI Insights Analysis Modal (Communication Symmetry!) -->
    <transition name="fade">
      <div v-if="isAnalysisModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAnalysisModalOpen = false" class="absolute inset-0 bg-[#060c10]/80 backdrop-blur-md" />
        <div class="relative w-full max-w-2xl bg-white dark:bg-[#0c1317] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 flex flex-col max-h-[85vh]">
          
          <div class="flex items-center justify-between mb-8 shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 bg-teal-50 dark:bg-teal-500/10 rounded-2xl flex items-center justify-center shadow-inner border border-teal-100 dark:border-teal-500/20 text-teal-600 dark:text-teal-400">
                <Sparkles class="w-6 h-6 text-teal-600 dark:text-teal-400" />
              </div>
              <div>
                <h3 class="text-2xl font-bold text-zinc-900 dark:text-white font-display leading-tight">AI Savings Insights</h3>
                <p class="text-xs text-zinc-400 mt-0.5">Gemini-powered contextual advice & forecasting</p>
              </div>
            </div>
            <button @click="isAnalysisModalOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer text-zinc-500">
              <X class="w-5 h-5" />
            </button>
          </div>

          <!-- Loading state -->
          <div v-if="isAnalyzing" class="flex-1 overflow-y-auto py-12 flex flex-col items-center justify-center gap-4 text-center">
            <div class="relative w-16 h-16">
              <div class="absolute inset-0 border-4 border-teal-500/20 rounded-full" />
              <div class="absolute inset-0 border-4 border-t-teal-500 rounded-full animate-spin" />
            </div>
            <div>
              <p class="font-bold text-zinc-800 dark:text-zinc-200 font-display text-sm">Consulting Financial Brain...</p>
              <p class="text-xs text-zinc-500 dark:text-zinc-450 mt-1 max-w-sm">Generating performance forecasting based on savings momentum and deposit tracking.</p>
            </div>
          </div>

          <!-- Analysis complete -->
          <div v-else class="flex-1 overflow-y-auto pr-2 custom-scrollbar space-y-6">
            <div 
              class="prose prose-zinc dark:prose-invert max-w-none text-zinc-600 dark:text-zinc-300 leading-relaxed text-sm bg-zinc-50 dark:bg-zinc-950 p-6 rounded-3xl border border-zinc-200 dark:border-white/5 space-y-4"
              v-html="parsedAnalysisResult"
            />
          </div>

          <div class="pt-6 border-t border-zinc-100 dark:border-white/5 shrink-0 flex justify-end gap-3 bg-white dark:bg-[#0c1317]">
            <button 
              @click="handlePrintReport" 
              class="px-5 py-3 border border-zinc-200 dark:border-white/5 text-zinc-700 dark:text-zinc-300 rounded-2xl text-xs font-bold hover:bg-zinc-50 dark:hover:bg-white/5 cursor-pointer flex items-center justify-center gap-2"
            >
              <Printer class="w-4 h-4" />
              Print Insights
            </button>
            <button 
              @click="isAnalysisModalOpen = false"
              class="px-6 py-3 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl text-xs font-bold hover:shadow-xl hover:shadow-teal-600/20 transition-all cursor-pointer"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </transition>

    </div> <!-- End screen-only wrapper -->

    <!-- PRINT ONLY TEMPLATE VIEW (Printer report feature request!) -->
    <div class="print-only-container text-black bg-white p-12 min-h-screen text-xs space-y-8 absolute inset-0 z-[1000] w-full font-sans">
      
      <!-- Printed Document Title Header -->
      <div class="flex items-start justify-between border-b pb-6">
        <div>
          <h1 class="text-2xl font-bold tracking-tight uppercase font-sans">{{ group ? group.name : 'Joint Savings Group' }}</h1>
          <p class="text-sm font-medium mt-1 text-zinc-605">Savings Goals Performance & Deposits Audit Report</p>
          <p class="text-[9px] text-zinc-550 mt-2 font-mono">Date Generated: {{ new Date().toLocaleString() }} | Target Currency Base: {{ user.defaultCurrency }}</p>
        </div>
        <div class="text-right">
          <p class="text-xl font-black text-emerald-800">SAVINGS PORTFOLIO AUDIT REPORT</p>
          <p class="text-[10px] font-bold text-zinc-500 mt-1">Certified Account Ledger</p>
        </div>
      </div>

      <!-- Financial Metrics Grid -->
      <div class="grid grid-cols-3 gap-6 bg-zinc-50 p-5 rounded-2xl">
        <div>
          <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest block">Combined Total Goals Target</span>
          <span class="text-base font-bold text-zinc-900 block font-mono mt-1">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalTargetValue) }}
          </span>
        </div>
        <div>
          <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest block">Aggregated Saved Value</span>
          <span class="text-base font-bold text-emerald-700 block font-mono mt-1">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalSavedValue) }}
          </span>
        </div>
        <div>
          <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest block">Total Progress Ratio</span>
          <span class="text-base font-bold text-zinc-900 block font-mono mt-1">
            {{ totalTargetValue > 0 ? ((totalSavedValue / totalTargetValue) * 100).toFixed(1) : 0 }}% Fully Funded
          </span>
        </div>
      </div>

      <!-- Section A: Performance by Category -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-550 bg-zinc-100 p-2 rounded mb-3">1. Performance & Allocations by Category</h3>
        <table class="w-full text-left border-collapse font-sans text-[10px]">
          <thead>
            <tr class="border-b text-zinc-505 font-bold bg-zinc-50/50">
              <th class="p-2.5">Category Title</th>
              <th class="p-2.5 text-right font-mono">Target Capacity ({{ user.defaultCurrency }})</th>
              <th class="p-2.5 text-right font-mono">Amount Contributed</th>
              <th class="p-2.5 text-right font-mono">Fulfillment Ratio</th>
            </tr>
          </thead>
          <tbody class="divide-y text-zinc-800">
            <tr v-for="cat in categoryPrintedSummary" :key="cat.name">
              <td class="p-2.5 font-bold">{{ cat.name }} <span class="text-[8px] text-zinc-400">({{ cat.count }} goals)</span></td>
              <td class="p-2.5 text-right font-mono">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(cat.target) }}</td>
              <td class="p-2.5 text-right font-mono font-bold text-emerald-750">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(cat.saved) }}</td>
              <td class="p-2.5 text-right font-mono font-extrabold text-emerald-700">{{ cat.progress.toFixed(0) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Section B: Individual Savings Goals Summary -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-555 bg-zinc-101 p-2 rounded mb-3">2. Detailed Progress Ledger by Goal</h3>
        <table class="w-full text-left border-collapse text-[10px]">
          <thead>
            <tr class="border-b font-bold bg-zinc-50/50 text-zinc-500">
              <th class="p-2.5">Goal Name</th>
              <th class="p-2.5">Category</th>
              <th class="p-2.5 text-right font-mono">Target Amount</th>
              <th class="p-2.5 text-right font-mono">Total Saved</th>
              <th class="p-2.5 text-right font-mono">Remaining Needed</th>
              <th class="p-2.5 text-right font-mono">Completion Ratio</th>
            </tr>
          </thead>
          <tbody class="divide-y text-zinc-800">
            <tr v-for="goal in goals" :key="goal.id">
              <td class="p-2.5 font-bold">{{ goal.name }}</td>
              <td class="p-2.5 font-sans">{{ goal.category }}</td>
              <td class="p-2.5 text-right font-mono">{{ getCurrencySymbol(goal.currencyCode) }}{{ formatCurrency(goal.targetAmount) }}</td>
              <td class="p-2.5 text-right font-mono font-bold">{{ getCurrencySymbol(goal.currencyCode) }}{{ formatCurrency(getGoalSavedAmount(goal.id, goal.currencyCode)) }}</td>
              <td class="p-2.5 text-right font-mono text-zinc-500">
                <span v-if="goal.targetAmount - getGoalSavedAmount(goal.id, goal.currencyCode) > 0">
                  {{ getCurrencySymbol(goal.currencyCode) }}{{ formatCurrency(goal.targetAmount - getGoalSavedAmount(goal.id, goal.currencyCode)) }}
                </span>
                <span v-else class="text-emerald-700 font-bold">REACHED ✅</span>
              </td>
              <td class="p-2.5 text-right font-mono font-bold">
                {{ goal.targetAmount > 0 ? ((getGoalSavedAmount(goal.id, goal.currencyCode) / goal.targetAmount) * 100).toFixed(0) + '%' : '0%' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Section C: Transaction Ledger -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-555 bg-zinc-101 p-2 rounded mb-3">3. Individual Deposit Contributions Log</h3>
        <table v-if="allGroupDeposits.length > 0" class="w-full text-left border-collapse text-[10px]">
          <thead>
            <tr class="border-b bg-zinc-50/50 font-bold text-zinc-500">
              <th class="p-2.5">Date</th>
              <th class="p-2.5">Depositor</th>
              <th class="p-2.5">Savings Goal Component</th>
              <th class="p-2.5">Memo / Description</th>
              <th class="p-2.5 text-right font-mono">Amount Committed</th>
              <th class="p-2.5 text-right font-mono">Converted Value ({{ user.defaultCurrency }})</th>
            </tr>
          </thead>
          <tbody class="divide-y text-zinc-800">
            <tr v-for="{ deposit: dep, goalName } in allGroupDeposits" :key="dep.id">
              <td class="p-2.5 font-mono">
                {{ dep.date?.toDate ? dep.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : String(dep.date) }}
              </td>
              <td class="p-2.5 font-bold">
                {{ members.find(m => m.uid === dep.depositedBy)?.displayName || (dep.depositedBy === user.uid ? 'You' : 'Anonymous Member') }}
              </td>
              <td class="p-2.5 font-sans font-bold">{{ goalName }}</td>
              <td class="p-2.5 italic text-zinc-600">"{{ dep.note || 'Regular Savings Deposit' }}"</td>
              <td class="p-2.5 text-right font-mono font-bold text-emerald-800">+{{ getCurrencySymbol(dep.currencyCode) }}{{ formatCurrency(dep.originalAmount) }}</td>
              <td class="p-2.5 text-right font-mono text-zinc-500">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertCurrency(dep.originalAmount, dep.currencyCode, user.defaultCurrency)) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-center italic text-zinc-400 text-xs mt-4">No logged deposits committed to date.</p>
      </div>

      <div class="pt-8 border-t border-dashed flex justify-between text-[8px] text-zinc-400">
        <span>End of Certified Joint Savings Goals Performance Report</span>
        <span>Generated via centralized Antigravity AI Co-Pilot Ledger Sync</span>
      </div>
    </div>

  </div>
</template>
