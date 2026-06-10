<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  ArrowLeft,
  Calendar,
  MoreVertical,
  Plus,
  Sparkles,
  UserPlus,
  Receipt,
  Trash2,
  Pencil,
  X,
  Loader2,
  TrendingUp,
  PieChart as PieChartIcon,
  Check,
  AlertCircle,
  Printer,
  Users
} from 'lucide-vue-next';
import { db } from '../firebase';
import { 
  doc, 
  onSnapshot, 
  collection, 
  query, 
  orderBy, 
  addDoc,
  setDoc,
  getDoc,
  updateDoc,
  deleteDoc,
  serverTimestamp,
  Timestamp 
} from 'firebase/firestore';
import { type Group, type Expense, type GroupMember, type BudgetType } from '../types';
import { expenseCategories } from '../utils/categories';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { formatCurrency } from '../utils/format';
import { convertCurrency, getCurrencySymbol, CURRENCIES } from '../utils/currency';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

// Firestore real-time bindings
const group = ref<Group | null>(null);
const expenses = ref<Expense[]>([]);
const members = ref<GroupMember[]>([]);
const accountGroups = ref<Group[]>([]);
const chosenAccountId = ref('');

// Modals / Dropdowns
const isAddExpenseOpen = ref(false);
const isAddMemberOpen = ref(false);
const isSettingsOpen = ref(false);
const isDeleteGroupConfirmOpen = ref(false);
const isAnalysisModalOpen = ref(false);
const selectedStatDetails = ref<{ title: string; amount: number; subtitle?: string } | null>(null);

// Forms inputs
const amount = ref('');
const expenseCurrency = ref('USD');
const description = ref('');
const category = ref(expenseCategories.value[0] || 'Other');
const date = ref(new Date().toISOString().split('T')[0]);

// Editing states
const editingExpense = ref<Expense | null>(null);
const expenseToDelete = ref<string | null>(null);

// Invite state
const newMemberEmail = ref('');
const inviteLoading = ref(false);
const inviteError = ref<string | null>(null);
const inviteSuccess = ref(false);

// Edit settings state
const editName = ref('');
const editDescription = ref('');
const editMaxBudget = ref('');
const editBudgetType = ref<BudgetType>('monthly');
const editGroupCurrency = ref('USD');

// AI state
const isAnalyzing = ref(false);
const analysisResult = ref<string | null>(null);

// Themes
const theme = ref<'light' | 'dark'>('dark');

// Fetch the theme of documentElement
onMounted(() => {
  theme.value = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  
  const observer = new MutationObserver(() => {
    theme.value = document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
});

// Setup Firestore Listeners
let unsubscribes: (() => void)[] = [];

onMounted(() => {
  // Group details listener
  const unsubscribeGroup = onSnapshot(doc(db, 'groups', props.groupId), (snapshot) => {
    if (snapshot.exists()) {
      const data = snapshot.data();
      group.value = { id: snapshot.id, ...data } as Group;
      editName.value = data.name;
      editDescription.value = data.description || '';
      editMaxBudget.value = data.maxBudget?.toString() || '';
      editBudgetType.value = data.budgetType || 'monthly';
      editGroupCurrency.value = data.currencyCode || 'USD';
    }
  }, (error) => {
    if (!error.message.includes('Missing or insufficient permissions')) {
      console.error("Error loading group:", error);
    }
  });

  // Expenses listener
  const expensesQuery = query(collection(db, 'groups', props.groupId, 'expenses'), orderBy('date', 'desc'));
  const unsubscribeExpenses = onSnapshot(expensesQuery, (snapshot) => {
    expenses.value = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() } as Expense));
  }, (error) => {
    if (!error.message.includes('Missing or insufficient permissions')) {
      console.error("Error loading expenses:", error);
    }
  });

  // Members listener
  const membersQuery = collection(db, 'groups', props.groupId, 'members');
  const unsubscribeMembers = onSnapshot(membersQuery, (snapshot) => {
    members.value = snapshot.docs.map(doc => ({ uid: doc.id, ...doc.data() } as GroupMember));
  }, (error) => {
    if (!error.message.includes('Missing or insufficient permissions')) {
      console.error("Error loading members:", error);
    }
  });

  // Accounts list query for linked dropdowns
  const accountsQuery = query(collection(db, 'groups'));
  const unsubscribeAccounts = onSnapshot(accountsQuery, (snapshot) => {
    accountGroups.value = snapshot.docs
      .map(docSnap => ({ id: docSnap.id, ...docSnap.data() } as Group))
      .filter(g => g.service === 'accounts');
  }, (error) => {
    console.error("Error loading accounts in budget:", error);
  });

  unsubscribes = [unsubscribeGroup, unsubscribeExpenses, unsubscribeMembers, unsubscribeAccounts];
});

onUnmounted(() => {
  unsubscribes.forEach(unsub => unsub());
});

// Helper to dynamically calculate any expense amount converted to user's currently active default currency
const getConvertedExpenseAmount = (expense: Expense) => {
  const origAmount = expense.originalAmount ?? expense.amount;
  const origCurrency = expense.currencyCode ?? 'USD';
  return convertCurrency(origAmount, origCurrency, props.user.defaultCurrency || 'USD');
};

// Original entered currencies signature ledger tracker
const originalCurrenciesBreakdown = computed(() => {
  const breakdown: Record<string, number> = {};
  expenses.value.forEach(e => {
    const code = e.currencyCode || 'USD';
    const amountVal = e.originalAmount ?? e.amount;
    breakdown[code] = (breakdown[code] || 0) + amountVal;
  });
  return Object.entries(breakdown).map(([code, total]) => ({ code, total }));
});

// Watch edit expense triggering
watch(editingExpense, (val) => {
  if (val) {
    amount.value = (val.originalAmount ?? val.amount).toString();
    expenseCurrency.value = val.currencyCode || 'USD';
    description.value = val.description;
    category.value = val.category;
    date.value = val.date.toDate().toISOString().split('T')[0];
    chosenAccountId.value = val.linkedAccountId || '';
    isAddExpenseOpen.value = true;
  } else {
    amount.value = '';
    expenseCurrency.value = props.user.defaultCurrency || 'USD';
    description.value = '';
    category.value = expenseCategories.value[0] || 'Other';
    date.value = new Date().toISOString().split('T')[0];
    chosenAccountId.value = '';
  }
});

// Check if a date lies in current week/month
const isDateInCurrentPeriod = (d: Date, type: BudgetType) => {
  const now = new Date();
  if (type === 'total') return true;
  
  if (type === 'monthly') {
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  }
  
  if (type === 'weekly') {
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    startOfWeek.setHours(0,0,0,0);
    
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 7);
    
    return d >= startOfWeek && d < endOfWeek;
  }
  return true;
};

// Computed Stats
const currentPeriodExpenses = computed(() => {
  return expenses.value.filter(e => 
    isDateInCurrentPeriod(e.date.toDate(), group.value?.budgetType || 'total')
  );
});

const totalSpent = computed(() => {
  return currentPeriodExpenses.value.reduce((sum, e) => sum + getConvertedExpenseAmount(e), 0);
});

const userSpent = computed(() => {
  return currentPeriodExpenses.value
    .filter(e => e.paidBy === props.user.uid)
    .reduce((sum, e) => sum + getConvertedExpenseAmount(e), 0);
});

const perPerson = computed(() => {
  return totalSpent.value;
});

const balance = computed(() => {
  return 0;
});

const currentBudgetSpent = computed(() => totalSpent.value);

const convertedMaxBudget = computed(() => {
  if (!group.value || !group.value.maxBudget) return 0;
  return convertCurrency(group.value.maxBudget, group.value.currencyCode || 'USD', props.user?.defaultCurrency || 'USD');
});

// Line Chart (Trend Data)
const lineData = computed(() => {
  if (!group.value || group.value.budgetType === 'total') return [];
  
  const now = new Date();
  const currentYear = now.getFullYear();
  const data = [];
  
  if (group.value.budgetType === 'weekly') {
    // 52 weeks
    const firstDayOfYear = new Date(currentYear, 0, 1);
    const startOfFirstWeek = new Date(firstDayOfYear);
    startOfFirstWeek.setDate(firstDayOfYear.getDate() - firstDayOfYear.getDay());
    startOfFirstWeek.setHours(0, 0, 0, 0);

    for (let i = 0; i < 52; i++) {
      const weekStart = new Date(startOfFirstWeek);
      weekStart.setDate(startOfFirstWeek.getDate() + (i * 7));
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 7);

      const weekSpent = expenses.value
        .filter(e => {
          const ed = e.date.toDate();
          return ed >= weekStart && ed < weekEnd && ed.getFullYear() === currentYear;
        })
        .reduce((sum, e) => sum + getConvertedExpenseAmount(e), 0);
      
      data.push({ 
        name: `W${i + 1}`, 
        amount: weekSpent 
      });
    }
  } else if (group.value.budgetType === 'monthly') {
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    for (let i = 0; i < 12; i++) {
      const monthSpent = expenses.value
        .filter(e => {
          const ed = e.date.toDate();
          return ed.getMonth() === i && ed.getFullYear() === currentYear;
        })
        .reduce((sum, e) => sum + getConvertedExpenseAmount(e), 0);
      data.push({ name: monthNames[i], amount: monthSpent });
    }
  }
  return data;
});

// Pie Chart (category distribution)
const pieData = computed(() => {
  const categoryMap = new Map<string, number>();
  currentPeriodExpenses.value.forEach(e => {
    categoryMap.set(e.category, (categoryMap.get(e.category) || 0) + getConvertedExpenseAmount(e));
  });
  return Array.from(categoryMap.entries()).map(([name, value]) => ({ name, value }));
});

const getPeriodLabel = () => {
  const now = new Date();
  const type = group.value?.budgetType || 'total';
  
  if (type === 'monthly') {
    return now.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  }
  
  if (type === 'weekly') {
    const startOfWeek = new Date(now);
    startOfWeek.setDate(now.getDate() - now.getDay());
    const endOfWeek = new Date(startOfWeek);
    endOfWeek.setDate(startOfWeek.getDate() + 6);
    
    const startMonth = startOfWeek.toLocaleDateString('en-US', { month: 'short' });
    const endMonth = endOfWeek.toLocaleDateString('en-US', { month: 'short' });
    
    if (startMonth === endMonth) {
      return `${startMonth} ${startOfWeek.getDate()} - ${endOfWeek.getDate()}, ${now.getFullYear()}`;
    }
    return `${startMonth} ${startOfWeek.getDate()} - ${endMonth} ${endOfWeek.getDate()}, ${now.getFullYear()}`;
  }
  return 'All Time';
};

// Database operation Handlers
const handleAddExpense = async () => {
  if (!amount.value || !description.value) return;

  try {
    const origAmount = parseFloat(amount.value);
    const entryCurrency = expenseCurrency.value;
    const userDefault = props.user.defaultCurrency || 'USD';
    const convertedAmount = convertCurrency(origAmount, entryCurrency, userDefault);

    // 1. Reverse/adjust old linked account balance first if updated
    if (editingExpense.value && editingExpense.value.linkedAccountId && editingExpense.value.linkedTransactionId) {
      const oldAccId = editingExpense.value.linkedAccountId;
      const oldTxId = editingExpense.value.linkedTransactionId;
      const oldOrigAmt = editingExpense.value.originalAmount ?? editingExpense.value.amount;

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

    const expenseId = editingExpense.value ? editingExpense.value.id : crypto.randomUUID();
    let newLinkedAccId = '';
    let newLinkedTxId = '';

    // 2. Add / Charge new linked account if selected
    if (chosenAccountId.value) {
      newLinkedAccId = chosenAccountId.value;
      newLinkedTxId = crypto.randomUUID();

      const accToCharge = accountGroups.value.find(g => g.id === chosenAccountId.value);
      if (accToCharge) {
        const isCC = accToCharge.accountType === 'credit_card';
        const accCurrency = accToCharge.currencyCode || 'USD';
        const accAmt = convertCurrency(origAmount, entryCurrency, accCurrency);

        const txData = {
          id: newLinkedTxId,
          groupId: chosenAccountId.value,
          accountId: chosenAccountId.value,
          amount: -accAmt,
          description: `Budget Expense: ${description.value.trim()}`,
          category: category.value,
          date: Timestamp.fromDate(new Date(date.value)),
          createdAt: Timestamp.now(),
          type: 'expense',
          note: `Auto-linked from Budget & Expenses: ${description.value.trim()}`
        };

        await setDoc(doc(db, 'groups', chosenAccountId.value, 'account_transactions', newLinkedTxId), txData);

        let activeBal = parseFloat(accToCharge.balance as any || 0);
        if (isCC) {
          activeBal = activeBal + accAmt;
        } else {
          activeBal = activeBal - accAmt;
        }
        await updateDoc(doc(db, 'groups', chosenAccountId.value), { balance: activeBal });
      }
    }

    const expenseData: any = {
      amount: convertedAmount,
      originalAmount: origAmount,
      currencyCode: entryCurrency,
      exchangeRateUsed: convertCurrency(1, entryCurrency, userDefault),
      description: description.value.trim(),
      category: category.value,
      paidBy: editingExpense.value ? editingExpense.value.paidBy : props.user.uid,
      date: Timestamp.fromDate(new Date(date.value)),
      createdAt: editingExpense.value ? editingExpense.value.createdAt : serverTimestamp(),
      splitType: 'equal' as const
    };

    if (newLinkedAccId && newLinkedTxId) {
      expenseData.linkedAccountId = newLinkedAccId;
      expenseData.linkedTransactionId = newLinkedTxId;
    } else {
      expenseData.linkedAccountId = null;
      expenseData.linkedTransactionId = null;
    }

    if (editingExpense.value) {
      await updateDoc(doc(db, 'groups', props.groupId, 'expenses', editingExpense.value.id), expenseData);
    } else {
      await setDoc(doc(db, 'groups', props.groupId, 'expenses', expenseId), expenseData);
    }
    
    isAddExpenseOpen.value = false;
    editingExpense.value = null;
    amount.value = '';
    description.value = '';
    chosenAccountId.value = '';
  } catch (error) {
    handleFirestoreError(error, editingExpense.value ? OperationType.UPDATE : OperationType.CREATE, `groups/${props.groupId}/expenses`);
  }
};

const handleAddMember = async () => {
  inviteError.value = 'Email invites are disabled for this sandbox version. Please use the Remix button to deploy your own database to support sharing.';
};

const handleDeleteExpense = async (id: string) => {
  try {
    const expDocObj = await getDoc(doc(db, 'groups', props.groupId, 'expenses', id));
    if (expDocObj.exists()) {
      const expData = expDocObj.data() as Expense;
      if (expData.linkedAccountId && expData.linkedTransactionId) {
        const oldAccId = expData.linkedAccountId;
        const oldTxId = expData.linkedTransactionId;
        const oldOrigAmt = expData.originalAmount ?? expData.amount;

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
    }

    await deleteDoc(doc(db, 'groups', props.groupId, 'expenses', id));
    expenseToDelete.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/${props.groupId}/expenses/${id}`);
  }
};

const handleDeleteGroup = async () => {
  try {
    await deleteDoc(doc(db, 'groups', props.groupId));
    emit('back');
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, `groups/${props.groupId}`);
  }
};

const handleUpdateSettings = async () => {
  if (!editName.value.trim()) return;
  
  try {
    const updateData: any = {
      name: editName.value.trim(),
      description: editDescription.value.trim(),
      maxBudget: editMaxBudget.value ? parseFloat(editMaxBudget.value) : null,
      budgetType: editMaxBudget.value ? editBudgetType.value : 'total',
      currencyCode: editGroupCurrency.value
    };
    await updateDoc(doc(db, 'groups', props.groupId), updateData);
    isSettingsOpen.value = false;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `groups/${props.groupId}`);
  }
};

// AI Insights spending analysis using server proxy route
const handleAnalyzeSpending = async () => {
  isAnalyzing.value = true;
  isAnalysisModalOpen.value = true;
  analysisResult.value = null;

  try {
    const expenseSummary = expenses.value.map(e => ({
      amount: e.amount,
      description: e.description,
      category: e.category,
      date: e.date.toDate().toLocaleDateString()
    }));

    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        groupName: group.value?.name,
        groupType: group.value?.type,
        budgetType: group.value?.budgetType,
        maxBudget: group.value?.maxBudget,
        totalSpent: totalSpent.value,
        expenseSummary
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

// Custom Simple Markdown parser
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

const handlePrintReport = () => {
  window.print();
};

const categoryPrintedSummary = computed(() => {
  const summary: Record<string, { spent: number; count: number }> = {};
  
  expenseCategories.value.forEach(cat => {
    summary[cat] = { spent: 0, count: 0 };
  });

  const userDefault = props.user?.defaultCurrency || 'USD';

  expenses.value.forEach(exp => {
    const cat = exp.category || 'Other';
    if (!summary[cat]) {
      summary[cat] = { spent: 0, count: 0 };
    }
    const convertedSpent = convertCurrency(exp.amount, exp.currencyCode || 'USD', userDefault);
    summary[cat].spent += convertedSpent;
    summary[cat].count += 1;
  });

  return Object.entries(summary)
    .filter(([_, data]) => data.count > 0 || data.spent > 0)
    .map(([category, data]) => ({
      name: category,
      spent: data.spent,
      count: data.count,
    }));
});

// Category Styling Utilities
const getCategoryColor = (cat: string) => {
  switch (cat) {
    case 'Food': return 'bg-orange-500 text-white';
    case 'Rent': return 'bg-emerald-500 text-white';
    case 'Utilities': return 'bg-blue-500 text-white';
    case 'Transport': return 'bg-amber-500 text-white';
    case 'Entertainment': return 'bg-fuchsia-500 text-white';
    case 'Shopping': return 'bg-sky-500 text-white';
    case 'Health': return 'bg-red-500 text-white';
    case 'Travel': return 'bg-indigo-500 text-white';
    default: return 'bg-zinc-500 text-white';
  }
};

const getCategoryBadgeClass = (cat: string) => {
  switch (cat) {
    case 'Food': return 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-500/10 border-orange-100 dark:border-orange-500/20';
    case 'Rent': return 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-100 dark:border-emerald-500/20';
    case 'Utilities': return 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-500/10 border-blue-100 dark:border-blue-500/20';
    case 'Transport': return 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-100 dark:border-amber-500/20';
    case 'Entertainment': return 'text-fuchsia-600 dark:text-fuchsia-400 bg-fuchsia-50 dark:bg-fuchsia-500/10 border-fuchsia-100 dark:border-fuchsia-500/20';
    case 'Shopping': return 'text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-500/10 border-sky-100 dark:border-sky-500/20';
    case 'Health': return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-500/10 border-red-100 dark:border-red-500/20';
    case 'Travel': return 'text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 border-indigo-100 dark:border-indigo-500/20';
    default: return 'text-zinc-650 dark:text-zinc-400 bg-zinc-50 dark:bg-zinc-500/10 border-zinc-100 dark:border-zinc-500/20';
  }
};

// Settlement / Debts Engine
const settlements = computed(() => {
  if (members.value.length <= 1 || expenses.value.length === 0) return [];

  // 1. Calculate net balance for each member
  const memberBalances = members.value.map(member => {
    const spent = expenses.value
      .filter(e => e.paidBy === member.uid)
      .reduce((sum, e) => sum + e.amount, 0);
    const net = spent - (expenses.value.reduce((sum, e) => sum + e.amount, 0) / members.value.length);
    return {
      uid: member.uid,
      displayName: member.displayName || 'Unknown Member',
      balance: net
    };
  });

  // Split into debtors (who owe) and creditors (who are owed)
  const debtors = memberBalances.filter(m => m.balance < -0.01).sort((a,b) => a.balance - b.balance);
  const creditors = memberBalances.filter(m => m.balance > 0.01).sort((a,b) => b.balance - a.balance);

  const list: { from: string; to: string; amount: number }[] = [];

  let dIdx = 0;
  let cIdx = 0;

  // Clone debts to settle
  const debtorsCopy = debtors.map(d => ({ ...d }));
  const creditorsCopy = creditors.map(c => ({ ...c }));

  while (dIdx < debtorsCopy.length && cIdx < creditorsCopy.length) {
    const debtor = debtorsCopy[dIdx];
    const creditor = creditorsCopy[cIdx];

    const oweAmount = Math.abs(debtor.balance);
    const creditAmount = creditor.balance;

    const settled = Math.min(oweAmount, creditAmount);

    list.push({
      from: debtor.displayName,
      to: creditor.displayName,
      amount: parseFloat(settled.toFixed(2))
    });

    debtor.balance += settled;
    creditor.balance -= settled;

    if (Math.abs(debtor.balance) < 0.01) dIdx++;
    if (creditor.balance < 0.01) cIdx++;
  }

  return list;
});
</script>

<template>
  <div v-if="group" class="max-w-6xl mx-auto pb-20">
    <!-- Wrap all screen-only items in print:hidden so they are cleanly removed during browser print -->
    <div class="print:hidden">
      <!-- Back Button -->
      <button 
        @click="$emit('back')"
      class="flex items-center gap-2 px-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white hover:border-zinc-300 dark:hover:border-zinc-700 rounded-xl transition-all duration-200 mb-10 group shadow-sm cursor-pointer outline-none"
    >
      <ArrowLeft class="w-4 h-4 transition-transform group-hover:-translate-x-1" />
      <span class="text-sm font-bold">Back to Budget & Expenses</span>
    </button>

    <!-- Header Section -->
    <div class="flex flex-col md:flex-row md:items-start justify-between gap-8 mb-12">
      <div class="flex-1">
        <div class="flex items-center gap-3 mb-3">
          <span :class="`px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wider ${
            group.type === 'household' ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-500/20' :
            group.type === 'trip' ? 'bg-orange-50 dark:bg-orange-500/10 text-orange-700 dark:text-orange-400 border border-orange-100 dark:border-orange-500/20' :
            'bg-blue-50 dark:bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-100 dark:border-blue-500/20'
          }`">
            {{ group.type }}
          </span>
          <div class="flex items-center gap-1.5 text-zinc-400 dark:text-zinc-500">
            <Calendar class="w-3.5 h-3.5" />
            <span class="text-[10px] font-bold uppercase tracking-widest font-mono">{{ getPeriodLabel() }}</span>
          </div>
        </div>
        <h1 class="text-4xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">{{ group.name }}</h1>
        <p class="text-zinc-650 dark:text-zinc-300 max-w-2xl leading-relaxed font-medium">{{ group.description || 'No description provided.' }}</p>
      </div>

      <!-- Header CTAs -->
      <div class="flex flex-wrap items-stretch gap-2.3 sm:gap-3 w-full md:w-auto">
        <!-- Print Button (Print report feature request!) -->
        <button 
          @click="handlePrintReport"
          class="p-3.5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:text-zinc-950 dark:hover:text-white rounded-2xl transition-all hover:bg-zinc-50 dark:hover:bg-zinc-805 shadow-sm flex items-center justify-center cursor-pointer cursor-print pointer-events-auto shrink-0"
          title="Print Budget Report"
        >
          <Printer class="w-5 h-5" />
          <span class="hidden sm:inline text-xs font-bold ml-2">Print</span>
        </button>

        <button 
          v-if="user.uid === group.createdBy"
          @click="isSettingsOpen = true"
          class="w-12 sm:w-auto p-3.5 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 rounded-2xl text-zinc-500 hover:bg-zinc-50 dark:hover:bg-zinc-800 hover:text-zinc-900 dark:hover:text-white transition-all shadow-sm flex items-center justify-center shrink-0 cursor-pointer"
          title="Group Settings"
        >
          <MoreVertical class="w-5 h-5" />
        </button>
        <button 
          @click="handleAnalyzeSpending"
          :disabled="isAnalyzing"
          class="flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-3.5 bg-gradient-to-br from-teal-600 to-emerald-600 text-white rounded-2xl text-sm font-bold hover:from-teal-700 hover:to-emerald-700 hover:shadow-xl hover:shadow-teal-500/40 transition-all disabled:opacity-50 shadow-lg shadow-teal-500/20 active:scale-95 cursor-pointer font-sans"
        >
          <Loader2 v-if="isAnalyzing" class="w-4 h-4 animate-spin" />
          <Sparkles v-else class="w-4 h-4" />
          AI Insights
        </button>
        <button 
          @click="editingExpense = null; isAddExpenseOpen = true"
          class="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-3.5 border border-zinc-200 dark:border-white/5 bg-white dark:bg-[#0d151a] rounded-2xl text-sm font-bold text-zinc-900 dark:text-white hover:bg-teal-50 dark:hover:bg-teal-900/20 hover:border-teal-200 dark:hover:border-teal-850 hover:shadow-lg hover:shadow-teal-500/5 transition-all active:scale-95 cursor-pointer font-sans"
        >
          <Plus class="w-4 h-4" />
          Add Expense
        </button>
      </div>
    </div>

    <!-- Budget Alert Banner -->
    <transition name="fade">
      <div 
        v-if="group.maxBudget && currentBudgetSpent > convertedMaxBudget"
        class="mb-8 p-6 bg-red-50 dark:bg-red-950/80 border border-red-250 dark:border-red-900/50 rounded-[24px] text-red-905 dark:text-red-100 flex items-start gap-4 shadow-lg shadow-red-500/5 backdrop-blur-sm"
      >
        <div class="p-2 bg-red-100 dark:bg-red-500/20 rounded-xl text-red-600 dark:text-red-400 shrink-0">
          <AlertCircle class="w-5 h-5" />
        </div>
        <div class="flex-1">
          <h4 class="font-bold text-sm tracking-tight mb-1">Budget Threshold Exceeded</h4>
          <p class="text-xs text-red-750 dark:text-red-300 leading-relaxed">
            This budget group has exceeded its set threshold of 
            <span class="font-semibold">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertedMaxBudget) }}</span>. 
            Currently, total expenditures amount to 
            <span class="font-bold text-red-700 dark:text-red-400">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(currentBudgetSpent) }}</span> 
            ({{ convertedMaxBudget > 0 ? ((currentBudgetSpent / convertedMaxBudget) * 100).toFixed(0) : 0 }}% spent).
          </p>
        </div>
      </div>
    </transition>

    <!-- Budgets and Stats Bento Matrix -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
      <!-- Total spending card -->
      <div 
        class="text-left w-full bg-white dark:bg-[#0d151a] p-8 rounded-[32px] border border-zinc-200 dark:border-white/5 shadow-xl shadow-zinc-200/50 dark:shadow-black/20 relative overflow-hidden group"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-teal-500/5 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative">
          <p class="text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.2em] mb-4 font-display">Total Spend</p>
          <p class="text-4xl font-bold text-zinc-900 dark:text-white font-display tracking-tight truncate">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalSpent) }}
          </p>
          
          <!-- Optional budgets limits indicator bar -->
          <div v-if="group.maxBudget" class="mt-6">
            <div class="flex justify-between text-[10px] font-bold uppercase mb-2 font-display">
              <span class="text-zinc-400">Budget ({{ group.budgetType }})</span>
              <span :class="currentBudgetSpent > convertedMaxBudget ? 'text-red-600 dark:text-red-400' : 'text-teal-600 dark:text-teal-400'">
                {{ convertedMaxBudget > 0 ? ((currentBudgetSpent / convertedMaxBudget) * 100).toFixed(0) : 0 }}%
              </span>
            </div>
            <div class="h-2 bg-zinc-100 dark:bg-white/10 rounded-full overflow-hidden">
              <div 
                :class="`h-full transition-all duration-700 ease-out ${currentBudgetSpent > convertedMaxBudget ? 'bg-red-500 animate-pulse' : 'bg-teal-500'}`"
                :style="{ width: `${convertedMaxBudget > 0 ? Math.min(100, (currentBudgetSpent / convertedMaxBudget) * 100) : 0}%` }"
              />
            </div>
            <p class="text-[10px] text-zinc-500 dark:text-zinc-400 mt-2 font-medium">
              {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(currentBudgetSpent) }} of {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertedMaxBudget) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Live Exchange conversions checklist -->
      <div 
        class="text-left w-full bg-white dark:bg-[#0d151a] p-8 rounded-[32px] border border-zinc-200 dark:border-white/5 shadow-xl shadow-zinc-200/50 dark:shadow-black/20 relative overflow-hidden group"
      >
        <div class="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full -mr-16 -mt-16 transition-transform group-hover:scale-110" />
        <div class="relative h-full flex flex-col justify-between">
          <div>
            <p class="text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.2em] mb-4 font-display">Default Currency Preference</p>
            <div class="flex items-center gap-2">
              <span class="text-xs font-bold px-2 py-1 bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-100 dark:border-teal-500/20 rounded-lg">
                {{ user.defaultCurrency || 'USD' }}
              </span>
              <span class="text-xs font-medium text-zinc-500">Live dynamic recalculation active</span>
            </div>
          </div>
          <p class="text-xs text-zinc-400 dark:text-zinc-400 mt-4 leading-relaxed font-medium">
            Keep track of expenses globally. Changing your default currency from the sidebar instantly recalibrates all trends, trackers, layouts, and historic list totals.
          </p>
        </div>
      </div>
    </div>

    <!-- Visualizer Graphics Panels -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
      <!-- Category distribution -->
      <div class="bg-white dark:bg-[#0d151a] p-8 rounded-[40px] border border-zinc-200 dark:border-white/5 shadow-xl shadow-zinc-200/50 dark:shadow-black/20">
        <h3 class="text-xs font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-8 flex items-center gap-2 font-display">
          <PieChartIcon class="w-4 h-4 text-teal-600" />
          Category Distribution
        </h3>

        <div v-if="pieData.length === 0" class="h-64 flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-650">
          <PieChartIcon class="w-12 h-12 mb-3 stroke-[1.2] opacity-40" />
          <p class="italic text-sm">No expenses in this period</p>
        </div>
        <div v-else class="space-y-5">
          <!-- Visual representation using clean HTML5 dynamic bar metrics -->
          <div v-for="item in pieData" :key="item.name" class="space-y-1.5 font-sans">
            <div class="flex items-center justify-between text-xs font-bold">
              <span class="text-zinc-700 dark:text-zinc-300">{{ item.name }}</span>
              <div class="flex items-center gap-3">
                <span class="text-zinc-900 dark:text-white font-mono">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(item.value) }}</span>
                <span class="text-zinc-400 font-mono font-medium">{{ ((item.value / totalSpent) * 100).toFixed(0) }}%</span>
              </div>
            </div>
            <!-- Progress Tracker Bar -->
            <div class="h-2.5 bg-zinc-100 dark:bg-zinc-800/60 rounded-full overflow-hidden">
              <div 
                :class="`h-full rounded-full ${
                  item.name === 'Food' ? 'bg-orange-500' :
                  item.name === 'Rent' ? 'bg-emerald-500' :
                  item.name === 'Utilities' ? 'bg-blue-500' :
                  item.name === 'Transport' ? 'bg-amber-500' :
                  item.name === 'Entertainment' ? 'bg-fuchsia-500' :
                  item.name === 'Shopping' ? 'bg-sky-500' :
                  item.name === 'Health' ? 'bg-red-500' :
                  item.name === 'Travel' ? 'bg-indigo-500' : 'bg-zinc-500'
                }`" 
                :style="{ width: `${(item.value / totalSpent) * 100}%` }"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Entered currencies ledger tracker -->
      <div class="bg-white dark:bg-[#0d151a] p-8 rounded-[40px] border border-zinc-200 dark:border-white/5 shadow-xl shadow-zinc-200/50 dark:shadow-black/20">
        <h3 class="text-xs font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-[0.15em] mb-8 flex items-center gap-2 font-display">
          <Sparkles class="w-4 h-4 text-teal-600" />
          Entered Currencies Ledger
        </h3>

        <div v-if="originalCurrenciesBreakdown.length === 0" class="h-64 flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-650 text-center">
          <div class="w-12 h-12 rounded-full bg-teal-500/10 flex items-center justify-center text-teal-500 mb-3">
            <Check class="w-6 h-6" />
          </div>
          <p class="font-bold text-zinc-800 dark:text-white text-base">Ledger empty</p>
          <p class="text-xs text-zinc-400 max-w-[200px] mt-1">Start entering expenses in any major global currency to see them here.</p>
        </div>
        <div v-else class="space-y-4 max-h-[240px] overflow-y-auto pr-2 custom-scrollbar">
          <div v-for="(item, index) in originalCurrenciesBreakdown" :key="index" class="p-4 bg-[#faf8f5]/50 dark:bg-[#090e12]/30 rounded-2xl border border-zinc-150 dark:border-white/5 flex items-center justify-between gap-4 font-sans">
            <div class="flex items-center gap-3">
              <span class="w-10 h-10 rounded-xl bg-teal-500/10 text-teal-600 dark:text-teal-400 font-bold flex items-center justify-center text-sm font-mono">
                {{ item.code }}
              </span>
              <div>
                <p class="text-sm font-bold text-zinc-900 dark:text-white">{{ item.code }} Signature Ledger</p>
                <p class="text-[10px] text-zinc-500 dark:text-zinc-400 font-medium">Entered raw in {{ item.code }}</p>
              </div>
            </div>
            <span class="text-base font-bold text-teal-600 dark:text-teal-400 font-mono shrink-0">
              {{ getCurrencySymbol(item.code) }}{{ formatCurrency(item.total) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Content layout mapping list of transitions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-12">
      <!-- Transaction list -->
      <div class="lg:col-span-2">
        <div class="flex items-center justify-between mb-8">
          <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white flex items-center gap-3 font-display">
            <Receipt class="w-6 h-6 text-zinc-400 dark:text-zinc-500" />
            Transaction History
          </h2>
          <div class="text-xs font-bold text-zinc-550 dark:text-zinc-400 uppercase tracking-widest font-mono">{{ expenses.length }} Total</div>
        </div>
        
        <div class="bg-white dark:bg-zinc-900 rounded-[40px] border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-xl shadow-zinc-200/50 dark:shadow-black/20">
          <div v-if="expenses.length === 0" class="p-16 text-center">
            <div class="w-16 h-16 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-6 border border-zinc-100 dark:border-zinc-750">
              <Receipt class="w-8 h-8 text-zinc-300 dark:text-zinc-600" />
            </div>
            <h3 class="text-lg font-bold text-zinc-900 dark:text-white mb-2">No expenses added yet</h3>
            <p class="text-zinc-500 dark:text-zinc-400 text-sm max-w-xs mx-auto">Click "Add Expense" to start tracking transactions in this room.</p>
          </div>
          
          <div v-else class="divide-y divide-zinc-100 dark:divide-zinc-800/80">
            <div v-for="expense in expenses" :key="expense.id" class="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 group transition-all duration-200 hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
              <div class="flex items-center gap-4 sm:gap-5 min-w-0">
                <div class="w-12 h-12 sm:w-14 sm:h-14 bg-zinc-50 dark:bg-zinc-800 rounded-2xl flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-500 border border-zinc-100 dark:border-zinc-700 transition-colors shrink-0">
                  <span class="text-[9px] font-bold uppercase tracking-tighter text-zinc-500">{{ expense.date.toDate().toLocaleDateString('en-US', { month: 'short' }) }}</span>
                  <span class="text-lg sm:text-xl font-bold leading-none text-zinc-900 dark:text-white">{{ expense.date.toDate().getDate() }}</span>
                </div>
                <div class="min-w-0">
                  <p class="font-bold text-zinc-900 dark:text-white group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors truncate">{{ expense.description }}</p>
                  <div class="flex flex-wrap items-center gap-2 mt-1">
                    <span :class="`px-2.5 py-0.5 rounded-full text-[9px] font-semibold uppercase tracking-wider border shrink-0 ${getCategoryBadgeClass(expense.category)}`">
                      {{ expense.category }}
                    </span>
                    <span class="text-zinc-300 dark:text-zinc-700 hidden sm:inline">•</span>
                    <span class="text-[10px] sm:text-xs text-zinc-500 dark:text-zinc-400 font-medium truncate">
                      Paid by {{ members.find(m => m.uid === expense.paidBy)?.displayName || 'Unknown' }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Transaction edit metrics -->
              <div class="flex items-center justify-between sm:justify-end gap-4 shrink-0 sm:mt-0">
                <div class="text-left sm:text-right">
                  <p class="text-lg sm:text-xl font-bold text-zinc-900 dark:text-white font-mono">
                    {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(getConvertedExpenseAmount(expense)) }}
                  </p>
                  <p v-if="expense.currencyCode && expense.currencyCode !== user.defaultCurrency" class="text-[9px] text-zinc-400 dark:text-zinc-500 font-semibold font-mono text-right">
                    Original Signature: {{ getCurrencySymbol(expense.currencyCode) }}{{ formatCurrency(expense.originalAmount || expense.amount) }}
                  </p>
                  <p v-else class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest mt-0.5">Amount</p>
                </div>
                <div class="flex items-center gap-1">
                  <button 
                    @click="editingExpense = expense"
                    class="p-2 text-zinc-400 hover:text-teal-600 dark:hover:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-500/10 rounded-xl sm:opacity-0 group-hover:opacity-100 transition-all outline-none cursor-pointer"
                  >
                    <Pencil class="w-4 h-4" />
                  </button>
                  <button 
                    @click="expenseToDelete = expense.id"
                    class="p-2 text-zinc-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 rounded-xl sm:opacity-0 group-hover:opacity-100 transition-all outline-none cursor-pointer"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Members side drawer -->
      <div>
        <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white mb-8 flex items-center gap-3 font-display">
          <Users class="w-6 h-6 text-zinc-400 dark:text-zinc-500" />
          Budget Wallet Owner
        </h2>
        <div class="bg-white dark:bg-[#0d151a] p-8 rounded-[40px] border border-zinc-200 dark:border-white/5 shadow-xl shadow-zinc-200/50 dark:shadow-black/20">
          <div class="space-y-6">
            <div v-for="member in members" :key="member.uid" class="flex items-center justify-between">
              <div class="flex items-center gap-4 min-w-0">
                <div class="relative shrink-0">
                  <div class="w-11 h-11 bg-zinc-50 dark:bg-white/5 border border-zinc-200 dark:border-white/5 rounded-2xl flex items-center justify-center text-zinc-400 dark:text-zinc-400 font-bold">
                    {{ member.displayName?.charAt(0).toUpperCase() }}
                  </div>
                  <div v-if="member.uid === group.createdBy" class="absolute -top-1 -right-1 w-4 h-4 bg-teal-650 rounded-full border-2 border-white dark:border-zinc-900 flex items-center justify-center">
                    <Sparkles class="w-2.5 h-2.5 text-white" />
                  </div>
                </div>
                <div class="min-w-0">
                  <p class="text-sm font-bold text-zinc-900 dark:text-white truncate">{{ member.displayName }}</p>
                  <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest truncate">{{ member.role }}</p>
                </div>
              </div>
              <span v-if="member.uid === group.createdBy" class="text-[9px] font-bold text-teal-650 dark:text-teal-400 bg-teal-50 dark:bg-teal-500/10 px-2.5 py-0.5 rounded-full border border-teal-100 dark:border-teal-500/20">
                OWNER
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Expense modal -->
    <transition name="fade">
      <div v-if="isAddExpenseOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddExpenseOpen = false; editingExpense = null" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-150 dark:border-white/5 rounded-[36px] shadow-2xl p-10 outline-none z-10 transition-all">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">
              {{ editingExpense ? 'Edit Transaction' : 'Add Transaction' }}
            </h3>
            <button @click="isAddExpenseOpen = false; editingExpense = null" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <form @submit.prevent="handleAddExpense" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Amount & Currency Signature</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                    {{ getCurrencySymbol(expenseCurrency) }}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    v-model="amount"
                    class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-mono font-bold text-lg dark:text-white"
                    placeholder="0.00"
                    required
                    autoFocus
                  />
                </div>
                <div class="w-32 shrink-0">
                  <select
                    v-model="expenseCurrency"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-bold dark:text-white appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
              <p v-if="expenseCurrency !== user.defaultCurrency" class="text-[10px] text-zinc-400 mt-2 font-medium font-mono">
                Converts to approx. {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(convertCurrency(parseFloat(amount || '0'), expenseCurrency, user.defaultCurrency)) }}
              </p>
            </div>
            <div>
              <label class="block text-[10px] font-bold text-zinc-450 uppercase tracking-[0.15em] mb-2 font-display">Description</label>
              <input
                type="text"
                v-model="description"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-medium dark:text-white"
                placeholder="What was it for?"
                required
              />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-450 uppercase tracking-[0.15em] mb-2 font-display">Category</label>
                <select
                  v-model="category"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-semibold dark:text-white appearance-none"
                >
                  <option v-for="cat in expenseCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-450 uppercase tracking-[0.15em] mb-2 font-display">Date</label>
                <input
                  type="date"
                  v-model="date"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-teal-500/10 focus:border-teal-500 transition-all font-semibold dark:text-white"
                  required
                />
              </div>
            </div>

            <!-- Link with Account / Card -->
            <div>
              <label class="block text-[10px] font-bold text-zinc-450 uppercase tracking-[0.15em] mb-2 font-display font-semibold">Charge Account / Card</label>
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
              class="w-full py-4.5 bg-teal-600 hover:bg-teal-700 text-white rounded-2xl font-bold transition-all shadow-lg shadow-teal-600/15 active:scale-95 cursor-pointer font-sans"
            >
              {{ editingExpense ? 'Update Transaction' : 'Save Transaction' }}
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Invite members popup modal -->
    <transition name="fade">
      <div v-if="isAddMemberOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddMemberOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[36px] shadow-2xl p-10 outline-none z-10 transition-all">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Invite Member</h3>
            <button @click="isAddMemberOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-850 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-8 leading-relaxed">Enter the email address of the person you want to add.</p>

          <div v-if="inviteError" class="mb-6 p-4 bg-red-50 dark:bg-red-500/10 border border-red-100 dark:border-red-500/20 text-red-600 dark:text-red-400 text-xs font-bold leading-relaxed rounded-2xl">
            {{ inviteError }}
          </div>

          <form @submit.prevent="handleAddMember" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Email Address</label>
              <input
                type="email"
                v-model="newMemberEmail"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-medium dark:text-white"
                placeholder="friend@example.com"
                required
              />
            </div>
            <button
              type="submit"
              class="w-full py-4.5 bg-zinc-900 dark:bg-indigo-600 text-white rounded-2xl font-bold hover:bg-zinc-800 dark:hover:bg-indigo-700 transition-all active:scale-95 cursor-pointer"
            >
              Add to Group
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Settings editor group config -->
    <transition name="fade">
      <div v-if="isSettingsOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isSettingsOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[36px] shadow-2xl p-10 max-h-[90vh] overflow-y-auto outline-none z-10 transition-all custom-scrollbar">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Group Settings</h3>
            <button @click="isSettingsOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateSettings" class="space-y-8">
            <div>
              <h4 class="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 mb-6 font-display">General Info</h4>
              <div class="space-y-5">
                <div>
                  <label class="block text-[10px] font-bold text-zinc-400 tracking-wider mb-2 font-display">Group Name</label>
                  <input
                    type="text"
                    v-model="editName"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold dark:text-white"
                    required
                  />
                </div>
                <div>
                  <label class="block text-[10px] font-bold text-zinc-400 tracking-wider mb-2 font-display">Description</label>
                  <textarea
                    v-model="editDescription"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all resize-none h-24 font-normal dark:text-white"
                  />
                </div>
              </div>
            </div>

            <div>
              <h4 class="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 mb-6 font-display">Budget Limits & Currency</h4>
              <div class="space-y-5">
                <div>
                  <label class="block text-[10px] font-bold text-zinc-400 tracking-wider mb-2 font-display">Budget Currency & Limit</label>
                  <div class="flex gap-3">
                    <div class="relative flex-1">
                      <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 font-mono font-bold">
                        {{ getCurrencySymbol(editGroupCurrency) }}
                      </span>
                      <input
                        type="number"
                        step="0.01"
                        v-model="editMaxBudget"
                        placeholder="No limit"
                        class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                      />
                    </div>
                    <div class="w-32 shrink-0">
                      <select
                        v-model="editGroupCurrency"
                        class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
                      >
                        <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div>
                  <label class="block text-[10px] font-bold text-zinc-400 tracking-wider mb-2 font-display">Frequency</label>
                  <select
                    v-model="editBudgetType"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold dark:text-white appearance-none"
                  >
                    <option value="weekly">Per Week</option>
                    <option value="monthly">Per Month</option>
                    <option value="total">Total</option>
                  </select>
                </div>
              </div>
            </div>

            <button
              type="submit"
              class="w-full py-4.5 bg-zinc-900 dark:bg-indigo-600 text-white rounded-2xl font-bold hover:bg-zinc-800 dark:hover:bg-indigo-700 transition-all shadow-lg active:scale-95 cursor-pointer"
            >
              Save Settings
            </button>

            <!-- Admin or Owner only: delete option -->
            <div class="pt-8 border-t border-zinc-200 dark:border-zinc-800">
              <button
                type="button"
                @click="isSettingsOpen = false; isDeleteGroupConfirmOpen = true"
                class="w-full py-4 bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400 rounded-2xl font-bold hover:bg-red-100 dark:hover:bg-red-500/20 transition-all flex items-center justify-center gap-2 active:scale-95 cursor-pointer"
              >
                <Trash2 class="w-5 h-5" />
                Delete Group
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- AI spend analyze result -->
    <transition name="fade">
      <div v-if="isAnalysisModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAnalysisModalOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-2xl bg-white dark:bg-zinc-900 rounded-[36px] shadow-2xl p-10 max-h-[85vh] overflow-y-auto outline-none z-10 transition-all custom-scrollbar">
          <div class="flex items-center gap-4 mb-8">
            <div class="w-12 h-12 bg-indigo-50 dark:bg-indigo-500/10 rounded-2xl flex items-center justify-center text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
              <Sparkles class="w-6 h-6" />
            </div>
            <div>
              <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Spending Analysis</h3>
              <p class="text-zinc-500 dark:text-zinc-400 text-sm">AI-powered insights for {{ group.name }}</p>
            </div>
          </div>

          <!-- Processing load state -->
          <div v-if="isAnalyzing" class="py-16 flex flex-col items-center justify-center gap-6 text-zinc-400">
            <div class="relative">
              <Loader2 class="w-10 h-10 animate-spin text-indigo-600" />
              <div class="absolute inset-0 blur-lg bg-indigo-400/20 animate-pulse" />
            </div>
            <p class="font-bold text-xs uppercase tracking-widest animate-pulse font-mono">Analyzing your spending habits...</p>
          </div>

          <!-- Load complete state -->
          <div v-else class="max-w-none">
            <div class="bg-zinc-50 dark:bg-zinc-800/80 rounded-[28px] p-8 border border-zinc-200 dark:border-zinc-700 dark:text-zinc-300 leading-relaxed max-w-none">
              <div v-html="parsedAnalysisResult" class="space-y-3 prose dark:prose-invert" />
            </div>
            <button
              @click="isAnalysisModalOpen = false"
              class="w-full py-4.5 bg-zinc-900 dark:bg-indigo-600 text-white rounded-2xl font-bold hover:bg-zinc-820 dark:hover:bg-indigo-700 transition-all mt-8 active:scale-95 cursor-pointer"
            >
              Close Insights
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Delete Group Confirmation Modal -->
    <transition name="fade">
      <div v-if="isDeleteGroupConfirmOpen" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div @click="isDeleteGroupConfirmOpen = false" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-sm bg-white dark:bg-zinc-900 rounded-[36px] shadow-2xl p-10 text-center outline-none z-10 transition-all">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 border border-red-100 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">Delete Group?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-10 leading-relaxed">
            This will permanently delete the group <strong>{{ group.name }}</strong> and all its expenses. This action cannot be undone.
          </p>
          <div class="flex gap-4">
            <button
              @click="isDeleteGroupConfirmOpen = false"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-705 dark:text-zinc-300 rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteGroup"
              class="flex-1 py-4 bg-red-600 text-white rounded-2xl font-bold hover:bg-red-700 transition-all active:scale-95 cursor-pointer shadow-lg shadow-red-500/20"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Stat details modal popup -->
    <transition name="fade">
      <div v-if="selectedStatDetails" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="selectedStatDetails = null" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-900 rounded-[36px] shadow-2xl p-10 text-center outline-none z-10 transition-all">
          <p class="text-xs font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 font-display">{{ selectedStatDetails.title }}</p>
          <p class="text-5xl font-bold text-zinc-900 dark:text-white font-display tracking-tight mb-2 break-all">${{ formatCurrency(selectedStatDetails.amount) }}</p>
          <p v-if="selectedStatDetails.subtitle" class="text-sm font-medium text-zinc-500 mt-4 leading-relaxed">{{ selectedStatDetails.subtitle }}</p>
          <button
            @click="selectedStatDetails = null"
            class="w-full py-4 bg-zinc-900 dark:bg-indigo-600 text-white rounded-2xl font-bold hover:bg-zinc-800 dark:hover:bg-indigo-700 transition-all mt-8 active:scale-95 cursor-pointer"
          >
            Close Details
          </button>
        </div>
      </div>
    </transition>

    <!-- Expense deletion modal -->
    <transition name="fade">
      <div v-if="expenseToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="expenseToDelete = null" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
        <div class="relative w-full max-w-sm bg-white dark:bg-zinc-900 rounded-[36px] shadow-2xl p-10 text-center outline-none z-10 transition-all">
          <div class="w-20 h-20 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-8 text-red-600 border border-red-100 dark:border-red-500/20">
            <Trash2 class="w-10 h-10" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-3 font-display">Delete Expense?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-10 leading-relaxed">This action cannot be undone. Are you sure you want to remove this expense?</p>
          <div class="flex gap-4">
            <button
              @click="expenseToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-all active:scale-95 cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteExpense(expenseToDelete)"
              class="flex-1 py-4 bg-red-600 text-white rounded-2xl font-bold hover:bg-red-700 transition-all active:scale-95 cursor-pointer shadow-lg shadow-red-500/20"
            >
              Delete
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
          <h1 class="text-2xl font-bold tracking-tight uppercase font-sans">{{ group ? group.name : 'Budget Group' }}</h1>
          <p class="text-sm font-medium mt-1 text-zinc-650">Budget Performance & Expenses Audit Report</p>
          <p class="text-[9px] text-zinc-550 mt-2 font-mono">Date Generated: {{ new Date().toLocaleString() }} | Target Currency Base: {{ user.defaultCurrency }}</p>
        </div>
        <div class="text-right">
          <p class="text-xl font-black text-red-700 block">EXPENDITURE ANALYSIS REPORT</p>
          <p class="text-[10px] font-bold text-zinc-500 mt-1">Certified Account Ledger</p>
        </div>
      </div>

      <!-- Financial Metrics Grid -->
      <div class="grid grid-cols-3 gap-6 bg-zinc-50 p-5 rounded-2xl">
        <div>
          <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest block">Combined Total Group Budget Limit</span>
          <span class="text-base font-bold text-zinc-900 block font-mono mt-1">
            {{ group?.maxBudget ? getCurrencySymbol(user.defaultCurrency) + formatCurrency(convertedMaxBudget) : 'N/A' }}
          </span>
        </div>
        <div>
          <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest block">Aggregated Spent Value</span>
          <span class="text-base font-bold text-red-700 block font-mono mt-1">
            {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(totalSpent) }}
          </span>
        </div>
        <div>
          <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-widest block">Limit Status</span>
          <span class="text-base font-bold text-zinc-900 block font-mono mt-1">
            <span v-if="group?.maxBudget && totalSpent > convertedMaxBudget" class="text-red-700 font-bold">OVERSPENT ⚠️</span>
            <span v-else-if="group?.maxBudget" class="text-emerald-700 font-bold">UNDER LIMIT ✅</span>
            <span v-else class="text-zinc-500">Unrestricted</span>
          </span>
        </div>
      </div>

      <!-- Section A: Performance by Category -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-550 bg-zinc-100 p-2 rounded mb-3">1. Expenditure & Allocations by Category</h3>
        <table class="w-full text-left border-collapse font-sans text-[10px]">
          <thead>
            <tr class="border-b text-zinc-505 font-bold bg-zinc-50/50">
              <th class="p-2.5">Category Title</th>
              <th class="p-2.5 text-right font-mono">Transaction Count</th>
              <th class="p-2.5 text-right font-mono">Amount Spent</th>
              <th class="p-2.5 text-right font-mono">Allocations %</th>
            </tr>
          </thead>
          <tbody class="divide-y text-zinc-800">
            <tr v-for="cat in categoryPrintedSummary" :key="cat.name">
              <td class="p-2.5 font-bold">{{ cat.name }}</td>
              <td class="p-2.5 text-right font-mono">{{ cat.count }} transactions</td>
              <td class="p-2.5 text-right font-mono font-bold text-red-750">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(cat.spent) }}</td>
              <td class="p-2.5 text-right font-mono font-extrabold text-red-700">
                {{ totalSpent > 0 ? ((cat.spent / totalSpent) * 100).toFixed(0) : 0 }}%
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Section B: Transaction Ledger Log -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-555 bg-zinc-101 p-2 rounded mb-3">2. Detailed Expense Log Ledger</h3>
        <table v-if="expenses.length > 0" class="w-full text-left border-collapse text-[10px]">
          <thead>
            <tr class="border-b bg-zinc-50/50 font-bold text-zinc-500">
              <th class="p-2.5">Date</th>
              <th class="p-2.5">Paid By</th>
              <th class="p-2.5">Category</th>
              <th class="p-2.5">Memo / Description</th>
              <th class="p-2.5 text-right font-mono">Original Entry</th>
              <th class="p-2.5 text-right font-mono">Converted Value ({{ user.defaultCurrency }})</th>
            </tr>
          </thead>
          <tbody class="divide-y text-zinc-800">
            <tr v-for="exp in expenses" :key="exp.id">
              <td class="p-2.5 font-mono">
                {{ exp.date?.toDate ? exp.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : String(exp.date) }}
              </td>
              <td class="p-2.5 font-bold">
                {{ members.find(m => m.uid === exp.paidBy)?.displayName || (exp.paidBy === user.uid ? 'You' : 'Anonymous Member') }}
              </td>
              <td class="p-2.5 font-sans font-bold">{{ exp.category }}</td>
              <td class="p-2.5 italic text-zinc-600">"{{ exp.description || 'Generic Expense Entry' }}"</td>
              <td class="p-2.5 text-right font-mono font-bold text-red-800">
                {{ getCurrencySymbol(exp.currencyCode || 'USD') }}{{ formatCurrency(exp.originalAmount || exp.amount) }}
              </td>
              <td class="p-2.5 text-right font-mono text-zinc-500">{{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(exp.amount) }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-center italic text-zinc-400 text-xs mt-4">No logged expenses to date.</p>
      </div>

      <!-- Section C: Active Balances & Settlements -->
      <div>
        <h3 class="text-xs font-bold uppercase tracking-wider text-zinc-555 bg-zinc-101 p-2 rounded mb-3">3. Active Balances & Peer Settlement Summary</h3>
        <table v-if="settlements.length > 0" class="w-full text-left border-collapse text-[10px]">
          <thead>
            <tr class="border-b bg-zinc-50/50 font-bold text-zinc-505">
              <th class="p-2.5">Debtor (Owes)</th>
              <th class="p-2.5">Creditor (Gets Back)</th>
              <th class="p-2.5 text-right font-mono">Settlement Amount Needed ({{ user.defaultCurrency }})</th>
            </tr>
          </thead>
          <tbody class="divide-y text-zinc-800">
            <tr v-for="(settlement, i) in settlements" :key="i">
              <td class="p-2.5 font-bold text-red-700">
                {{ members.find(m => m.uid === settlement.from)?.displayName || 'Member' }}
              </td>
              <td class="p-2.5 font-bold text-emerald-700 font-display">
                {{ members.find(m => m.uid === settlement.to)?.displayName || 'Member' }}
              </td>
              <td class="p-2.5 text-right font-mono font-extrabold text-zinc-900">
                {{ getCurrencySymbol(user.defaultCurrency) }}{{ formatCurrency(settlement.amount) }}
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="text-center italic text-zinc-400 text-xs mt-4">Group is mathematically settled. No active debts pending.</p>
      </div>

      <div class="pt-8 border-t border-dashed flex justify-between text-[8px] text-zinc-400">
        <span>End of Certified Expenditures Audit Report</span>
        <span>Generated via centralized Antigravity AI Co-Pilot Ledger Sync</span>
      </div>
    </div>

  </div>
</template>
