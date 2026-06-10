<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  ArrowLeft, 
  Plus, 
  Trash2, 
  Pencil, 
  Calendar, 
  MoreVertical, 
  Sparkles, 
  Loader2, 
  X, 
  TrendingUp, 
  PiggyBank, 
  Target, 
  Coins, 
  Users, 
  ArrowRight,
  TrendingDown,
  Printer,
  MoreHorizontal,
  Banknote,
  ArrowUpRight,
  HelpCircle,
  FileSpreadsheet
} from 'lucide-vue-next';
import { type Group, type GroupMember, type IncomeTarget, type IncomeRecord } from '../types';
import { incomeCategories } from '../utils/categories';
import { db } from '../firebase';
import { 
  doc, 
  collection, 
  query, 
  onSnapshot, 
  addDoc, 
  updateDoc, 
  deleteDoc, 
  serverTimestamp, 
  orderBy, 
  Timestamp,
  getDoc,
  setDoc
} from 'firebase/firestore';
import { formatCurrency } from '../utils/format';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { convertCurrency, getCurrencySymbol, CURRENCIES } from '../utils/currency';
import { deleteGroup } from '../services/dataService';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

// Main states
const group = ref<Group | null>(null);
const members = ref<GroupMember[]>([]);
const targets = ref<IncomeTarget[]>([]);
// Map of targetId to list of inflows
const inflows = ref<Record<string, IncomeRecord[]>>({});
const reportsExpanded = ref(false);

// Modals
const isAddTargetOpen = ref(false);
const isEditTargetOpen = ref(false);
const isAddInflowOpen = ref(false);
const isEditInflowOpen = ref(false);
const isSettingsOpen = ref(false);
const isAnalysisModalOpen = ref(false);

// Deletions
const targetToDelete = ref<IncomeTarget | null>(null);
const inflowToDelete = ref<IncomeRecord | null>(null);
const inflowToDeleteTargetId = ref<string>('');

// Submitting state indicators
const isSubmitting = ref(false);
const isAnalyzing = ref(false);
const analysisResult = ref<string | null>(null);

// Forms
// 1. Add Target
const targetName = ref('');
const targetAmount = ref('');
const targetCurrencyCode = ref('USD');
const targetCategory = ref('Salary & Wages');

// 2. Edit Target
const editTargetId = ref('');
const editTargetName = ref('');
const editTargetAmount = ref('');
const editTargetCurrencyCode = ref('USD');
const editTargetCategory = ref('Salary & Wages');

// 3. Add Inflow
const selectedTargetForInflow = ref<IncomeTarget | null>(null);
const inflowAmount = ref('');
const inflowCurrencyCode = ref('USD');
const sourceType = ref('Direct Deposit');
const inflowNote = ref('');
const inflowDate = ref(new Date().toISOString().split('T')[0]);

const accountGroups = ref<Group[]>([]);
const chosenAccountId = ref('');

// 4. Edit Inflow
const editingInflow = ref<IncomeRecord | null>(null);
const editingInflowTargetId = ref('');
const editInflowAmount = ref('');
const editInflowCurrencyCode = ref('USD');
const editSourceType = ref('Direct Deposit');
const editInflowNote = ref('');
const editInflowDate = ref(new Date().toISOString().split('T')[0]);

// 5. Settings / Rename group
const editName = ref('');
const editDescription = ref('');

// Listeners
const unsubscribes = ref<(() => void)[]>([]);

onMounted(() => {
  // Esc closing helpers
  window.addEventListener('keydown', handleKeyDown);

  // Group snapshot
  const groupRef = doc(db, 'groups', props.groupId);
  const unsubGroup = onSnapshot(groupRef, (snap) => {
    if (snap.exists()) {
      group.value = { id: snap.id, ...snap.data() } as Group;
      editName.value = group._value?.name || '';
      editDescription.value = group._value?.description || '';
    } else {
      emit('back');
    }
  });
  unsubscribes.value.push(unsubGroup);

  // Members
  const membersQuery = collection(db, 'groups', props.groupId, 'members');
  const unsubMembers = onSnapshot(membersQuery, (snap) => {
    members.value = snap.docs.map(d => ({ uid: d.id, ...d.data() } as GroupMember));
  });
  unsubscribes.value.push(unsubMembers);

  // Load Accounts groups listener for linking inflow deposits
  const accountsQuery = query(collection(db, 'groups'));
  const unsubAccounts = onSnapshot(accountsQuery, (snapshot) => {
    accountGroups.value = snapshot.docs
      .map(docSnap => ({ id: docSnap.id, ...docSnap.data() } as Group))
      .filter(g => g.service === 'accounts');
  }, (error) => {
    console.error("Error loading accounts in income:", error);
  });
  unsubscribes.value.push(unsubAccounts);

  // Targets
  const targetsQuery = query(collection(db, 'groups', props.groupId, 'income_targets'), orderBy('createdAt', 'desc'));
  const unsubTargets = onSnapshot(targetsQuery, (snap) => {
    targets.value = snap.docs.map(d => ({ id: d.id, ...d.data() } as IncomeTarget));

    // For each target, setup inflows subscription
    snap.docs.forEach(docSnap => {
      const targetId = docSnap.id;
      const inflowsQuery = query(
        collection(db, 'groups', props.groupId, 'income_targets', targetId, 'inflows'),
        orderBy('date', 'desc')
      );

      const unsubInflows = onSnapshot(inflowsQuery, (inflSnap) => {
        inflows.value[targetId] = inflSnap.docs.map(d => ({ id: d.id, ...d.data() } as IncomeRecord));
      }, (err) => {
        if (!err.message.includes('Missing or insufficient permissions')) {
          console.error("Firestore inflow snapshot subscription failed:", err);
        }
      });
      unsubscribes.value.push(unsubInflows);
    });
  }, (err) => {
    if (!err.message.includes('Missing or insufficient permissions')) {
      console.error("Firestore targets snapshot subscription failed:", err);
    }
  });
  unsubscribes.value.push(unsubTargets);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
  unsubscribes.value.forEach(unsub => unsub());
});

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape') {
    isAddTargetOpen.value = false;
    isEditTargetOpen.value = false;
    isAddInflowOpen.value = false;
    isEditInflowOpen.value = false;
    isSettingsOpen.value = false;
    isAnalysisModalOpen.value = false;
    targetToDelete.value = null;
    inflowToDelete.value = null;
  }
};

// Math helpers
const getTargetSavedAmount = (targetId: string, currency: string) => {
  const list = inflows.value[targetId] || [];
  return list.reduce((acc, curr) => {
    return acc + convertCurrency(curr.originalAmount ?? curr.amount, curr.currencyCode ?? 'USD', currency);
  }, 0);
};

const totalTargetValue = computed(() => {
  const targetCurrency = group.value?.currencyCode || props.user?.defaultCurrency || 'USD';
  return targets.value.reduce((acc, curr) => {
    return acc + convertCurrency(curr.targetAmount, curr.currencyCode, targetCurrency);
  }, 0);
});

const totalSavedValue = computed(() => {
  const targetCurrency = group.value?.currencyCode || props.user?.defaultCurrency || 'USD';
  return targets.value.reduce((acc, t) => {
    return acc + convertCurrency(getTargetSavedAmount(t.id, t.currencyCode), t.currencyCode, targetCurrency);
  }, 0);
});

const aggregatedReceipts = computed(() => {
  const list: { r: IncomeRecord; targetName: string; targetId: string }[] = [];
  targets.value.forEach(t => {
    const records = inflows.value[t.id] || [];
    records.forEach(r => {
      list.push({ r, targetName: t.name, targetId: t.id });
    });
  });
  list.sort((a, b) => b.r.date.toMillis() - a.r.date.toMillis());
  return list;
});

const defaultCurrencySymbol = computed(() => {
  return getCurrencySymbol(group.value?.currencyCode || props.user?.defaultCurrency || 'USD');
});

// Category Styling Mapper
const getTargetCategoryColor = (category: string) => {
  switch (category) {
    case 'Salary & Wages': return 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-500/20';
    case 'Freelance & Consulting': return 'bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-100 dark:border-indigo-500/20';
    case 'Investments & Dividends': return 'bg-purple-50 dark:bg-purple-500/10 text-purple-600 dark:text-purple-405 border-purple-100 dark:border-purple-500/20';
    case 'Rental Income': return 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-100 dark:border-amber-500/20';
    case 'Sales & E-Commerce': return 'bg-sky-50 dark:bg-sky-500/10 text-sky-600 dark:text-sky-455 border-sky-100 dark:border-sky-500/20';
    case 'Gifts & Grants': return 'bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-455 border-rose-100 dark:border-rose-500/20';
    case 'Side Hustle': return 'bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 border-teal-100 dark:border-teal-500/20';
    default: return 'bg-zinc-50 dark:bg-zinc-500/10 text-zinc-650 dark:text-zinc-400 border-zinc-100 dark:border-zinc-500/20';
  }
};

// CRUD Operations
const handleAddTarget = async () => {
  if (!targetName.value.trim() || !targetAmount.value || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    await addDoc(collection(db, 'groups', props.groupId, 'income_targets'), {
      name: targetName.value.trim(),
      targetAmount: parseFloat(targetAmount.value),
      currencyCode: targetCurrencyCode.value,
      category: targetCategory.value,
      createdBy: props.user.uid,
      createdAt: serverTimestamp()
    });

    isAddTargetOpen.value = false;
    targetName.value = '';
    targetAmount.value = '';
    targetCurrencyCode.value = group.value?.currencyCode || props.user?.defaultCurrency || 'USD';
  } catch (err) {
    handleFirestoreError(err, OperationType.CREATE, `groups/${props.groupId}/income_targets`);
  } finally {
    isSubmitting.value = false;
  }
};

const handleEditTargetClick = (t: IncomeTarget) => {
  editTargetId.value = t.id;
  editTargetName.value = t.name;
  editTargetAmount.value = t.targetAmount.toString();
  editTargetCurrencyCode.value = t.currencyCode;
  editTargetCategory.value = t.category;
  isEditTargetOpen.value = true;
};

const handleUpdateTarget = async () => {
  if (!editTargetName.value.trim() || !editTargetAmount.value || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    const docRef = doc(db, 'groups', props.groupId, 'income_targets', editTargetId.value);
    await updateDoc(docRef, {
      name: editTargetName.value.trim(),
      targetAmount: parseFloat(editTargetAmount.value),
      currencyCode: editTargetCurrencyCode.value,
      category: editTargetCategory.value
    });
    isEditTargetOpen.value = false;
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, `groups/income_targets/${editTargetId.value}`);
  } finally {
    isSubmitting.value = false;
  }
};

const handleDeleteTarget = async () => {
  if (!targetToDelete.value || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    // Delete inflows first
    // Note: in high scale you'd do query/delete, in client demo we delete the parent directly. Firestore leaves orphaned children but it's hidden under targets anyway. For precision:
    const inflowsRef = collection(db, 'groups', props.groupId, 'income_targets', targetToDelete.value.id, 'inflows');
    // We just delete the target itself
    const docRef = doc(db, 'groups', props.groupId, 'income_targets', targetToDelete.value.id);
    await deleteDoc(docRef);

    targetToDelete.value = null;
  } catch (err) {
    handleFirestoreError(err, OperationType.DELETE, `groups/income_targets`);
  } finally {
    isSubmitting.value = false;
  }
};

// Inflow logic
const handleOpenAddInflow = (t: IncomeTarget) => {
  selectedTargetForInflow.value = t;
  inflowAmount.value = '';
  inflowCurrencyCode.value = t.currencyCode;
  sourceType.value = 'Direct Deposit';
  inflowNote.value = '';
  inflowDate.value = new Date().toISOString().split('T')[0];
  chosenAccountId.value = '';
  isAddInflowOpen.value = true;
};

const handleAddInflow = async () => {
  if (!selectedTargetForInflow.value || !inflowAmount.value || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    const origAmt = parseFloat(inflowAmount.value);
    const entryCurr = inflowCurrencyCode.value;
    const targetCurr = selectedTargetForInflow.value.currencyCode;
    const convertedAmount = convertCurrency(origAmt, entryCurr, targetCurr);

    const inflowId = crypto.randomUUID();
    let linkedAccId = '';
    let linkedTxId = '';

    // Register deposit to account if set
    if (chosenAccountId.value) {
      linkedAccId = chosenAccountId.value;
      linkedTxId = crypto.randomUUID();

      const accToCredit = accountGroups.value.find(g => g.id === chosenAccountId.value);
      if (accToCredit) {
        const isCC = accToCredit.accountType === 'credit_card';
        const accCurrency = accToCredit.currencyCode || 'USD';
        const accAmt = convertCurrency(origAmt, entryCurr, accCurrency);

        const txData = {
          id: linkedTxId,
          groupId: chosenAccountId.value,
          accountId: chosenAccountId.value,
          amount: accAmt,
          description: `Income Deposit: ${selectedTargetForInflow.value.name}`,
          category: 'Income',
          date: Timestamp.fromDate(new Date(inflowDate.value)),
          createdAt: Timestamp.now(),
          type: 'income',
          note: `Auto-linked from Income: ${selectedTargetForInflow.value.name}`
        };

        await setDoc(doc(db, 'groups', chosenAccountId.value, 'account_transactions', linkedTxId), txData);

        let activeBal = parseFloat(accToCredit.balance as any || 0);
        if (isCC) {
          activeBal = activeBal - accAmt;
        } else {
          activeBal = activeBal + accAmt;
        }
        await updateDoc(doc(db, 'groups', chosenAccountId.value), { balance: activeBal });
      }
    }

    const inflowDocRef = doc(
      db, 
      'groups', 
      props.groupId, 
      'income_targets', 
      selectedTargetForInflow.value.id, 
      'inflows',
      inflowId
    );

    const inflowData: any = {
      amount: convertedAmount,
      originalAmount: origAmt,
      currencyCode: entryCurr,
      exchangeRateUsed: convertCurrency(1, entryCurr, targetCurr),
      receivedBy: props.user.uid,
      sourceType: sourceType.value,
      note: inflowNote.value.trim(),
      date: Timestamp.fromDate(new Date(inflowDate.value)),
      createdAt: serverTimestamp()
    };

    if (linkedAccId && linkedTxId) {
      inflowData.linkedAccountId = linkedAccId;
      inflowData.linkedTransactionId = linkedTxId;
    }

    await setDoc(inflowDocRef, inflowData);

    isAddInflowOpen.value = false;
    chosenAccountId.value = '';
  } catch (err) {
    handleFirestoreError(err, OperationType.CREATE, 'inflows');
  } finally {
    isSubmitting.value = false;
  }
};

const handleOpenEditInflow = (item: IncomeRecord, targetId: string) => {
  editingInflow.value = item;
  editingInflowTargetId.value = targetId;

  editInflowAmount.value = (item.originalAmount ?? item.amount).toString();
  editInflowCurrencyCode.value = item.currencyCode ?? 'USD';
  editSourceType.value = item.sourceType ?? 'Direct Deposit';
  editInflowNote.value = item.note ?? '';
  editInflowDate.value = item.date.toDate().toISOString().split('T')[0];
  chosenAccountId.value = item.linkedAccountId || '';

  isEditInflowOpen.value = true;
};

const handleUpdateInflow = async () => {
  if (!editingInflow.value || !editInflowAmount.value || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    const origAmt = parseFloat(editInflowAmount.value);
    const entryCurr = editInflowCurrencyCode.value;
    
    // Find target currency
    const target = targets.value.find(t => t.id === editingInflowTargetId.value);
    const tCurr = target?.currencyCode || 'USD';
    const convertedAmount = convertCurrency(origAmt, entryCurr, tCurr);

    const oldInflow = editingInflow.value;

    // 1. Rollback old linked account balance
    if (oldInflow.linkedAccountId && oldInflow.linkedTransactionId) {
      const oldAccId = oldInflow.linkedAccountId;
      const oldTxId = oldInflow.linkedTransactionId;
      const oldOrigAmt = oldInflow.originalAmount ?? oldInflow.amount;

      const accDocObj = await getDoc(doc(db, 'groups', oldAccId));
      if (accDocObj.exists()) {
        const accData = accDocObj.data() as Group;
        let oldBal = parseFloat(accData.balance as any || 0);
        if (accData.accountType === 'credit_card') {
          oldBal = oldBal + oldOrigAmt;
        } else {
          oldBal = oldBal - oldOrigAmt;
        }
        await updateDoc(doc(db, 'groups', oldAccId), { balance: oldBal });
      }
      await deleteDoc(doc(db, 'groups', oldAccId, 'account_transactions', oldTxId));
    }

    let linkedAccId = '';
    let linkedTxId = '';

    // 2. Adjust new linked account balance if selected
    if (chosenAccountId.value) {
      linkedAccId = chosenAccountId.value;
      linkedTxId = crypto.randomUUID();

      const accToCredit = accountGroups.value.find(g => g.id === chosenAccountId.value);
      if (accToCredit) {
        const isCC = accToCredit.accountType === 'credit_card';
        const accCurrency = accToCredit.currencyCode || 'USD';
        const accAmt = convertCurrency(origAmt, entryCurr, accCurrency);

        const txData = {
          id: linkedTxId,
          groupId: chosenAccountId.value,
          accountId: chosenAccountId.value,
          amount: accAmt,
          description: `Income Deposit: ${target?.name || 'Income'}`,
          category: 'Income',
          date: Timestamp.fromDate(new Date(editInflowDate.value)),
          createdAt: Timestamp.now(),
          type: 'income',
          note: `Auto-linked from Income: ${target?.name || 'Income'}`
        };

        await setDoc(doc(db, 'groups', chosenAccountId.value, 'account_transactions', linkedTxId), txData);

        let activeBal = parseFloat(accToCredit.balance as any || 0);
        if (isCC) {
          activeBal = activeBal - accAmt;
        } else {
          activeBal = activeBal + accAmt;
        }
        await updateDoc(doc(db, 'groups', chosenAccountId.value), { balance: activeBal });
      }
    }

    const docRef = doc(
      db, 
      'groups', 
      props.groupId, 
      'income_targets', 
      editingInflowTargetId.value, 
      'inflows', 
      editingInflow.value.id
    );

    const inflowData: any = {
      amount: convertedAmount,
      originalAmount: origAmt,
      currencyCode: entryCurr,
      exchangeRateUsed: convertCurrency(1, entryCurr, tCurr),
      sourceType: editSourceType.value,
      note: editInflowNote.value.trim(),
      date: Timestamp.fromDate(new Date(editInflowDate.value))
    };

    if (linkedAccId && linkedTxId) {
      inflowData.linkedAccountId = linkedAccId;
      inflowData.linkedTransactionId = linkedTxId;
    } else {
      inflowData.linkedAccountId = null;
      inflowData.linkedTransactionId = null;
    }

    await updateDoc(docRef, inflowData);

    isEditInflowOpen.value = false;
    chosenAccountId.value = '';
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, 'inflow');
  } finally {
    isSubmitting.value = false;
  }
};

const handleDeleteInflow = async () => {
  if (!inflowToDelete.value || !inflowToDeleteTargetId.value || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    const item = inflowToDelete.value;
    
    // Reverse/rollback balance
    if (item.linkedAccountId && item.linkedTransactionId) {
      const oldAccId = item.linkedAccountId;
      const oldTxId = item.linkedTransactionId;
      const oldOrigAmt = item.originalAmount ?? item.amount;

      const accDocObj = await getDoc(doc(db, 'groups', oldAccId));
      if (accDocObj.exists()) {
        const accData = accDocObj.data() as Group;
        let oldBal = parseFloat(accData.balance as any || 0);
        if (accData.accountType === 'credit_card') {
          oldBal = oldBal + oldOrigAmt;
        } else {
          oldBal = oldBal - oldOrigAmt;
        }
        await updateDoc(doc(db, 'groups', oldAccId), { balance: oldBal });
      }
      await deleteDoc(doc(db, 'groups', oldAccId, 'account_transactions', oldTxId));
    }

    const docRef = doc(
      db, 
      'groups', 
      props.groupId, 
      'income_targets', 
      inflowToDeleteTargetId.value, 
      'inflows', 
      inflowToDelete.value.id
    );
    await deleteDoc(docRef);
    inflowToDelete.value = null;
  } catch (err) {
    handleFirestoreError(err, OperationType.DELETE, 'inflow');
  } finally {
    isSubmitting.value = false;
  }
};

// Group Settings
const handleUpdateGroupSettings = async () => {
  if (!editName.value.trim()) return;
  try {
    const refDoc = doc(db, 'groups', props.groupId);
    await updateDoc(refDoc, {
      name: editName.value.trim(),
      description: editDescription.value.trim()
    });
    isSettingsOpen.value = false;
  } catch (err) {
    handleFirestoreError(err, OperationType.UPDATE, 'groups');
  }
};

const handleDeleteGroup = async () => {
  try {
    await deleteGroup(props.groupId);
    emit('back');
  } catch (err) {
    handleFirestoreError(err, OperationType.DELETE, `groups/${props.groupId}`);
  }
};

// Prints statement
const handlePrintStatement = () => {
  window.print();
};

// AI Inflows Insights
const handleAnalyzeIncomeInflows = async () => {
  isAnalyzing.value = true;
  isAnalysisModalOpen.value = true;
  analysisResult.value = null;

  try {
    const targetsSummary = targets.value.map(t => {
      const earned = getTargetSavedAmount(t.id, t.currencyCode);
      const recentInfls = (inflows.value[t.id] || []).slice(0, 3).map(i => ({
        amount: i.originalAmount || i.amount,
        currency: i.currencyCode,
        sourceType: i.sourceType,
        note: i.note,
        date: i.date?.toDate ? i.date.toDate().toLocaleDateString() : String(i.date)
      }));
      return {
        name: t.name,
        category: t.category,
        targetAmount: t.targetAmount,
        currency: t.currencyCode,
        currentEarned: earned,
        percentComplete: t.targetAmount > 0 ? ((earned / t.targetAmount) * 100).toFixed(1) + '%' : '0%',
        recentInflows: recentInfls
      };
    });

    const response = await fetch('/api/analyze-income', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        groupName: group.value?.name,
        groupType: group.value?.type,
        totalTarget: totalTargetValue.value,
        totalEarned: totalSavedValue.value,
        targetsSummary
      })
    });

    const output = await response.json();
    analysisResult.value = output.text || "Could not generate analysis.";
  } catch (err) {
    console.error("AI Analysis Error:", err);
    analysisResult.value = "Sorry, I encountered an error while communicating with the analysis service. Please verify your internet connection and verify that your Gemini API key is valid on the backend.";
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
  
  html = html.replace(/^### (.*$)/gm, '<h3 class="text-base font-bold text-zinc-900 dark:text-white mt-4 mb-2">$1</h3>');
  html = html.replace(/^## (.*$)/gm, '<h2 class="text-lg font-bold text-zinc-900 dark:text-white mt-5 mb-2">$1</h2>');
  html = html.replace(/^# (.*$)/gm, '<h1 class="text-xl font-bold text-zinc-900 dark:text-white mt-6 mb-3">$1</h1>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-zinc-900 dark:text-white">$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');
  html = html.replace(/`([^`]+)`/g, '<code class="bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded font-mono text-xs text-emerald-650 dark:text-emerald-400">$1</code>');
  html = html.replace(/^- +(.*$)/gm, '<li class="ml-4 list-disc text-sm text-zinc-650 dark:text-zinc-300">$1</li>');
  html = html.replace(/\n\n/g, '</p><p class="mt-3 text-sm text-zinc-650 dark:text-zinc-300 leading-relaxed">');
  
  return '<p class="text-sm text-zinc-650 dark:text-zinc-300 leading-relaxed">' + html + '</p>';
});

const progressPercent = computed(() => {
  if (totalTargetValue.value === 0) return 0;
  return Math.min(100, Math.round((totalSavedValue.value / totalTargetValue.value) * 100));
});

const progressFeedback = computed(() => {
  const pct = progressPercent.value;
  if (pct === 0) {
    return "Outstanding targets prepared. Awaiting initial cash receipts!";
  } else if (pct < 25) {
    return "Inflows registered! Early foundational momentum established.";
  } else if (pct < 60) {
    return "Great steady progress! Active streams are generating stable traction.";
  } else if (pct < 90) {
    return "Outstanding velocity! Your cumulative sources are approaching peak targets.";
  } else {
    return "Brilliant milestone accomplished! Target goals successfully covered!";
  }
});
</script>

<template>
  <div v-if="group" class="max-w-6xl mx-auto pb-16">
    
    <!-- Top Nav Action Bar -->
    <div id="income-top-nav" class="flex flex-wrap items-center justify-between gap-4 mb-8 print:hidden">
      <button 
        @click="$emit('back')" 
        class="flex items-center gap-2 text-sm font-bold text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white transition-colors cursor-pointer"
      >
        <ArrowLeft class="w-4 h-4" />
        Back to Dashboard
      </button>

      <div class="flex items-center gap-2">
        <!-- Print Button -->
        <button 
          @click="handlePrintStatement"
          class="p-3.5 bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 text-zinc-500 hover:text-zinc-950 dark:hover:text-white rounded-2xl transition-all hover:bg-zinc-50 dark:hover:bg-zinc-900 shadow-sm flex items-center justify-center cursor-pointer"
          title="Print Financial Statement"
        >
          <Printer class="w-5 h-5" />
          <span class="hidden sm:inline text-xs font-bold ml-2">Print</span>
        </button>

        <!-- Group Settings Button -->
        <button 
          v-if="user.uid === group.createdBy"
          @click="isSettingsOpen = true"
          class="p-3.5 bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 text-zinc-500 hover:text-zinc-950 dark:hover:text-white rounded-2xl transition-all hover:bg-zinc-50 dark:hover:bg-zinc-900 shadow-sm flex items-center justify-center cursor-pointer pointer-events-auto shrink-0"
          title="Group Settings"
        >
          <MoreVertical class="w-5 h-5" />
        </button>

        <!-- AI Insights Button -->
        <button 
          @click="handleAnalyzeIncomeInflows"
          :disabled="isAnalyzing"
          class="flex items-center justify-center gap-2 px-5 py-3.5 bg-gradient-to-br from-emerald-600 to-teal-600 text-white rounded-2xl text-sm font-bold hover:from-emerald-700 hover:to-teal-700 hover:shadow-xl hover:shadow-emerald-500/40 transition-all disabled:opacity-50 shadow-lg shadow-emerald-500/20 active:scale-95 cursor-pointer pointer-events-auto shrink-0"
        >
          <Loader2 v-if="isAnalyzing" class="w-4 h-4 animate-spin" />
          <Sparkles v-else class="w-4 h-4" />
          AI Insights
        </button>

        <!-- Add Income Target button -->
        <button 
          @click="isAddTargetOpen = true"
          class="flex items-center justify-center gap-2 px-6 py-3.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl text-sm font-bold hover:shadow-xl hover:shadow-emerald-600/30 transition-all shadow-md shadow-emerald-600/10 active:scale-95 cursor-pointer outline-none shrink-0"
        >
          <Plus class="w-4.5 h-4.5" />
          Add Income Target
        </button>
      </div>
    </div>

    <!-- Header Block -->
    <header id="group-statement-header" class="mb-10">
      <div class="flex items-start justify-between gap-6">
        <div>
          <div class="flex items-center gap-3">
            <span class="text-[10px] font-bold uppercase tracking-[0.2em] px-3 py-1 bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-500/15 rounded-lg font-mono">
              Target & Income
            </span>
            <span class="text-[10px] font-bold uppercase tracking-[0.2em] px-3 py-1 bg-zinc-50 dark:bg-white/5 text-zinc-500 dark:text-zinc-400 border border-zinc-100 dark:border-white/5 rounded-lg capitalize">
              {{ group.type }} Stream
            </span>
          </div>
          <h1 class="text-4xl md:text-5xl font-bold tracking-tight text-zinc-900 dark:text-white mt-4 font-display print:text-2xl">{{ group.name }}</h1>
          <p class="text-zinc-500 dark:text-zinc-400 font-medium text-lg mt-2">{{ group.description || 'No description designated.' }}</p>
        </div>
        
        <div class="text-right hidden sm:block">
          <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest font-mono">Currency Preference</p>
          <p class="text-2xl font-bold text-zinc-950 dark:text-white mt-1.5 font-display">{{ group.currencyCode || 'USD' }}</p>
        </div>
      </div>
    </header>

    <!-- Comprehensive Metrics Panel -->
    <section id="group-metrics-summary" class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
      <!-- Consolidated Target -->
      <div class="bg-white dark:bg-zinc-900 p-8 rounded-[36px] border border-zinc-200 dark:border-zinc-800 shadow-sm relative overflow-hidden group">
        <div class="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-100 dark:border-emerald-500/15 text-emerald-600 dark:text-emerald-400 rounded-2xl flex items-center justify-center mb-6">
            <ArrowUpRight class="w-6 h-6" />
          </div>
          <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] font-display">Combined Target Inflows</span>
          <p class="text-3xl font-extrabold text-zinc-900 dark:text-white mt-2 font-mono tracking-tight truncate">
            {{ defaultCurrencySymbol }}{{ formatCurrency(totalTargetValue) }}
          </p>
        </div>
      </div>

      <!-- Realized Earned -->
      <div class="bg-white dark:bg-zinc-900 p-8 rounded-[36px] border border-zinc-200 dark:border-zinc-800 shadow-sm relative overflow-hidden group">
        <div class="absolute top-0 right-0 w-32 h-32 bg-teal-500/5 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="w-12 h-12 bg-teal-50 dark:bg-teal-500/10 border border-teal-100 dark:border-teal-500/15 text-teal-600 dark:text-teal-400 rounded-2xl flex items-center justify-center mb-6">
            <TrendingUp class="w-6 h-6" />
          </div>
          <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] font-display">Realized Inflows</span>
          <p class="text-3xl font-extrabold text-zinc-900 dark:text-white mt-2 font-mono tracking-tight truncate">
            {{ defaultCurrencySymbol }}{{ formatCurrency(totalSavedValue) }}
          </p>
        </div>
      </div>

      <!-- Overall Achievements & Microfeedback -->
      <div class="bg-gradient-to-br from-emerald-600 to-teal-600 p-8 rounded-[36px] text-white shadow-lg shadow-emerald-500/10 relative overflow-hidden group col-span-1 md:col-span-1">
        <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16" />
        <div class="relative z-10">
          <div class="flex items-center justify-between mb-4">
            <span class="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-100">Milestone Reached</span>
            <span class="text-2xl font-bold font-mono">{{ progressPercent }}%</span>
          </div>
          
          <!-- Large progress bar -->
          <div class="h-2.5 bg-white/20 rounded-full overflow-hidden mb-6">
            <div class="h-full bg-white rounded-full transition-all duration-700 ease-out" :style="{ width: progressPercent + '%' }" />
          </div>
          
          <p class="text-xs font-semibold leading-relaxed text-emerald-50/90">{{ progressFeedback }}</p>
        </div>
      </div>
    </section>

    <!-- Targets Stream Listing -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
      
      <!-- Targets list -->
      <div class="lg:col-span-2 space-y-8">
        <div class="flex items-center justify-between">
          <h2 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Dynamic Target Inflow Paths</h2>
          <span class="text-xs font-bold text-zinc-400 font-mono">
            {{ targets.length }} active targets
          </span>
        </div>

        <div v-if="targets.length === 0" class="p-20 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-850 rounded-[44px] text-center shadow-sm">
          <div class="w-16 h-16 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-6">
            <Banknote class="w-8 h-8 text-zinc-300 dark:text-zinc-600" />
          </div>
          <h3 class="text-xl font-bold text-zinc-900 dark:text-white mb-2 font-display">No target channels defined</h3>
          <p class="text-zinc-500 dark:text-zinc-400 max-w-sm mx-auto mb-8 text-sm">Add custom income target streams (salary, projects, consulting) to start managing inflows.</p>
          <button 
            @click="isAddTargetOpen = true"
            class="px-6 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold text-xs hover:shadow-lg transition-all"
          >
            Add Target Inflow Path
          </button>
        </div>

        <!-- Loop targets -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <article 
            v-for="target in targets" 
            :key="target.id"
            class="bg-white dark:bg-zinc-900 p-8 rounded-[40px] border border-zinc-200 dark:border-zinc-800 shadow-sm relative group flex flex-col justify-between gap-6"
          >
            <div>
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0 flex-1">
                  <span :class="`inline-block text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-lg border font-mono ${getTargetCategoryColor(target.category)}`">
                    {{ target.category }}
                  </span>
                  <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mt-3 font-display break-words leading-tight">{{ target.name }}</h3>
                </div>
                
                <!-- Targets CRUD controls -->
                <div class="flex items-center gap-1 opacity-100 sm:opacity-0 group-hover:opacity-100 transition-all duration-205 shrink-0 ml-4">
                  <button 
                    @click="handleEditTargetClick(target)"
                    class="p-2 text-zinc-400 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-zinc-50 dark:hover:bg-zinc-850 rounded-xl active:scale-90 transition-all duration-150 cursor-pointer"
                    title="Edit target properties"
                  >
                    <Pencil class="w-4 h-4" />
                  </button>
                  <button 
                    @click="targetToDelete = target"
                    class="p-2 text-zinc-400 hover:text-red-650 hover:bg-zinc-50 dark:hover:bg-zinc-850 rounded-xl active:scale-90 transition-all duration-150 cursor-pointer"
                    title="Delete target stream"
                  >
                    <Trash2 class="w-4 h-4" />
                  </button>
                </div>
              </div>

              <!-- Metrics inside target -->
              <div class="mt-8 grid grid-cols-2 gap-4">
                <div class="p-4 bg-zinc-50 dark:bg-white/5 border border-zinc-100 dark:border-white/5 rounded-2xl">
                  <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-wider">Target goal</span>
                  <p class="font-mono font-bold text-zinc-900 dark:text-white text-base mt-0.5">
                    {{ getCurrencySymbol(target.currencyCode) }}{{ formatCurrency(target.targetAmount) }}
                  </p>
                </div>
                <div class="p-4 bg-zinc-50 dark:bg-white/5 border border-zinc-100 dark:border-white/5 rounded-2xl">
                  <span class="text-[9px] font-bold text-zinc-400 uppercase tracking-wider">Earned yet</span>
                  <p class="font-mono font-bold text-emerald-600 dark:text-emerald-400 text-base mt-0.5">
                    {{ getCurrencySymbol(target.currencyCode) }}{{ formatCurrency(getTargetSavedAmount(target.id, target.currencyCode)) }}
                  </p>
                </div>
              </div>
            </div>

            <!-- Inflows Target progress bar -->
            <div>
              <div class="flex items-center justify-between text-xs font-bold mb-2">
                <span class="text-zinc-400 uppercase tracking-widest text-[9px]">Accomplishment</span>
                <span class="font-mono text-emerald-650 dark:text-emerald-400">
                  {{ target.targetAmount > 0 ? ((getTargetSavedAmount(target.id, target.currencyCode) / target.targetAmount) * 100).toFixed(0) : 0 }}%
                </span>
              </div>
              <div class="h-2.5 bg-zinc-100 dark:bg-white/10 rounded-full overflow-hidden">
                <div 
                  :class="`h-full rounded-full transition-all duration-700 ease-out ${
                    getTargetSavedAmount(target.id, target.currencyCode) >= target.targetAmount 
                      ? 'bg-gradient-to-r from-emerald-500 to-emerald-400' 
                      : 'bg-emerald-500'
                  }`"
                  :style="{ width: `${target.targetAmount > 0 ? Math.min(100, (getTargetSavedAmount(target.id, target.currencyCode)/target.targetAmount)*100) : 0}%` }"
                />
              </div>
            </div>

            <div class="pt-4 border-t border-zinc-50 dark:border-zinc-800/80 flex items-center justify-between">
              <span class="text-[10px] text-zinc-400 font-bold font-mono">
                {{ (inflows[target.id] || []).length }} registered receipts
              </span>
              <button 
                @click="handleOpenAddInflow(target)"
                class="flex items-center gap-1.5 text-[10px] font-bold text-emerald-650 hover:text-emerald-700 dark:text-emerald-400 px-3 py-1.5 bg-emerald-50 dark:bg-emerald-500/10 rounded-xl transition-all border border-emerald-100 dark:border-emerald-500/15 cursor-pointer outline-none"
              >
                <Plus class="w-3.5 h-3.5" />
                Record Inflow
              </button>
            </div>
          </article>
        </div>
      </div>

      <!-- Live activity sidebar -->
      <div class="space-y-10">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Inflow receipts</h2>
        </div>

        <div class="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[36px] shadow-sm p-6 space-y-6">
          <div v-if="aggregatedReceipts.length === 0" class="p-10 text-center">
            <div class="w-12 h-12 bg-zinc-50 dark:bg-zinc-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <Coins class="w-6 h-6 text-zinc-300 dark:text-zinc-650" />
            </div>
            <p class="text-zinc-500 text-sm font-medium">Clear receipts ledger. Ready for dynamic cash injections!</p>
          </div>

          <div v-else class="space-y-4 max-h-[600px] overflow-y-auto pr-1 custom-scrollbar">
            <div 
              v-for="item in aggregatedReceipts" 
              :key="item.r.id"
              class="p-4 bg-zinc-50 dark:bg-white/5 border border-zinc-100 dark:border-white/5 rounded-2xl relative group transition-all hover:bg-zinc-100/50 dark:hover:bg-white/10"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0 flex-1">
                  <h4 class="font-bold text-zinc-900 dark:text-white text-sm truncate">{{ item.targetName }}</h4>
                  <p class="text-[10px] text-zinc-400 font-semibold font-mono mt-0.5 truncate">{{ item.r.sourceType }}</p>
                  <p v-if="item.r.note" class="text-[11px] text-zinc-500 italic mt-1.5 truncate">"{{ item.r.note }}"</p>
                  
                  <div class="text-[10px] text-zinc-400 mt-2 font-mono flex items-center gap-2">
                    <span class="font-bold uppercase px-1.5 py-0.5 bg-emerald-500/10 text-emerald-600 rounded">Inflow</span>
                    <span>{{ item.r.date.toDate().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }}</span>
                  </div>
                </div>

                <div class="text-right shrink-0">
                  <p class="font-mono font-bold text-emerald-500 dark:text-emerald-400 text-sm">
                    +{{ getCurrencySymbol(item.r.currencyCode) }}{{ formatCurrency(item.r.originalAmount || item.r.amount) }}
                  </p>
                </div>
              </div>

              <!-- Quick details edit actions -->
              <div v-if="item.r.receivedBy === props.user.uid" class="absolute right-2 bottom-2 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button 
                  @click="handleOpenEditInflow(item.r, item.targetId)"
                  class="p-1.5 bg-white dark:bg-zinc-800 text-zinc-500 hover:text-emerald-600 rounded-lg shadow-sm border border-zinc-100 dark:border-zinc-705 active:scale-90 cursor-pointer"
                  title="Modify inflow"
                >
                  <Pencil class="w-3 h-3" />
                </button>
                <button 
                  @click="inflowToDelete = item.r; inflowToDeleteTargetId = item.targetId"
                  class="p-1.5 bg-white dark:bg-zinc-800 text-zinc-500 hover:text-red-500 rounded-lg shadow-sm border border-zinc-100 dark:border-zinc-705 active:scale-90 cursor-pointer"
                  title="Delete inflow record"
                >
                  <Trash2 class="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Modals & dialog arrays -->

    <!-- Add Target Modal -->
    <transition name="fade">
      <div v-if="isAddTargetOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddTargetOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 max-h-[90vh] overflow-y-auto custom-scrollbar">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Add Target Inflow Path</h3>
            <button @click="isAddTargetOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <form @submit.prevent="handleAddTarget" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Name</label>
              <input
                type="text"
                v-model="targetName"
                placeholder="e.g. Freelance Consulting Contract, Salary Inflow"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-medium dark:text-white shadow-inner"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Category</label>
                <select
                  v-model="targetCategory"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="cat in incomeCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Currency</label>
                <select
                  v-model="targetCurrencyCode"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Expected Amount</label>
              <div class="relative">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-650 font-mono font-bold">
                  {{ getCurrencySymbol(targetCurrencyCode) }}
                </span>
                <input
                  type="number"
                  step="0.01"
                  v-model="targetAmount"
                  placeholder="0.00"
                  class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              :disabled="isSubmitting"
              class="w-full py-4.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-emerald-600/10"
            >
              <Loader2 v-if="isSubmitting" class="w-5 h-5 animate-spin" />
              <template v-else>Confirm and Add Target</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Edit Target Modal -->
    <transition name="fade">
      <div v-if="isEditTargetOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isEditTargetOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 max-h-[90vh] overflow-y-auto custom-scrollbar">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Target Inflow Properties</h3>
            <button @click="isEditTargetOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateTarget" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Name</label>
              <input
                type="text"
                v-model="editTargetName"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-medium dark:text-white shadow-inner"
                required
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Category</label>
                <select
                  v-model="editTargetCategory"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="cat in incomeCategories" :key="cat" :value="cat">{{ cat }}</option>
                </select>
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Currency</label>
                <select
                  v-model="editTargetCurrencyCode"
                  class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                </select>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-2 font-display">Target Expected Amount</label>
              <div class="relative">
                <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-650 font-mono font-bold">
                  {{ getCurrencySymbol(editTargetCurrencyCode) }}
                </span>
                <input
                  type="number"
                  step="0.01"
                  v-model="editTargetAmount"
                  class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              :disabled="isSubmitting"
              class="w-full py-4.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-emerald-600/10"
            >
              <Loader2 v-if="isSubmitting" class="w-5 h-5 animate-spin" />
              <template v-else>Confirm Changes</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Delete Target Modal -->
    <transition name="fade">
      <div v-if="targetToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="targetToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-sm bg-white dark:bg-[#0d151a] rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-16 h-16 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-6 text-red-650 dark:text-red-405 border border-red-100 dark:border-red-500/15">
            <Trash2 class="w-8 h-8" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-2 font-display">Delete target stream?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 leading-relaxed text-sm mb-8">
            Are you sure you want to delete <strong class="text-zinc-900 dark:text-white">"{{ targetToDelete.name }}"</strong>? This removes all associated recorded inflow receipts.
          </p>
          <div class="flex gap-3">
            <button
              @click="targetToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteTarget"
              class="flex-1 py-4 bg-red-650 text-white rounded-2xl font-bold hover:bg-red-700 transition-all cursor-pointer shadow-lg shadow-red-500/10"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Record Inflow Modal -->
    <transition name="fade">
      <div v-if="isAddInflowOpen && selectedTargetForInflow" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddInflowOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 max-h-[90vh] overflow-y-auto custom-scrollbar">
          <div class="flex items-center justify-between mb-8">
            <div>
              <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Record Cash Inflow</h3>
              <p class="text-[10px] text-zinc-405 font-bold font-mono mt-0.5">Stream: {{ selectedTargetForInflow.name }}</p>
            </div>
            <button @click="isAddInflowOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <form @submit.prevent="handleAddInflow" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Amount & Currency</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-450 font-mono font-bold">
                    {{ getCurrencySymbol(inflowCurrencyCode) }}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    v-model="inflowAmount"
                    placeholder="0.00"
                    class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                    required
                  />
                </div>
                <div class="w-32 shrink-0">
                  <select
                    v-model="inflowCurrencyCode"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Source Type</label>
              <select
                v-model="sourceType"
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
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Date Received</label>
              <input
                type="date"
                v-model="inflowDate"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-semibold dark:text-white"
                required
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Memo / Notes (Optional)</label>
              <input
                type="text"
                v-model="inflowNote"
                placeholder="e.g. Milestone completion bonus, Invoice #12"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-semibold dark:text-white"
              />
            </div>

            <!-- Deposit to Account / Card -->
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display font-semibold">Deposit to Account / Card</label>
              <select
                v-model="chosenAccountId"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all text-sm font-semibold dark:text-white appearance-none cursor-pointer"
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
              :disabled="isSubmitting"
              class="w-full py-4.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-emerald-500/20"
            >
              <Loader2 v-if="isSubmitting" class="w-5 h-5 animate-spin" />
              <template v-else>Register Cash Inflow</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Edit Inflow Modal -->
    <transition name="fade">
      <div v-if="isEditInflowOpen && editingInflow" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isEditInflowOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 max-h-[90vh] overflow-y-auto custom-scrollbar">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Edit Inflow Record</h3>
            <button @click="isEditInflowOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateInflow" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Amount & Currency</label>
              <div class="flex gap-3">
                <div class="relative flex-1">
                  <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-450 font-mono font-bold">
                    {{ getCurrencySymbol(editInflowCurrencyCode) }}
                  </span>
                  <input
                    type="number"
                    step="0.01"
                    v-model="editInflowAmount"
                    class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-mono font-bold dark:text-white shadow-inner"
                    required
                  />
                </div>
                <div class="w-32 shrink-0">
                  <select
                    v-model="editInflowCurrencyCode"
                    class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-bold dark:text-white cursor-pointer appearance-none"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                  </select>
                </div>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Source Type</label>
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
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Date Received</label>
              <input
                type="date"
                v-model="editInflowDate"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-semibold dark:text-white"
                required
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">Memo / Notes</label>
              <input
                type="text"
                v-model="editInflowNote"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-semibold dark:text-white"
              />
            </div>

            <!-- Deposit to Account / Card -->
            <div>
              <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display font-semibold">Deposit to Account / Card</label>
              <select
                v-model="chosenAccountId"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all text-sm font-semibold dark:text-white appearance-none cursor-pointer"
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
              :disabled="isSubmitting"
              class="w-full py-4.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer shadow-lg shadow-emerald-500/20"
            >
              <Loader2 v-if="isSubmitting" class="w-5 h-5 animate-spin" />
              <template v-else>Save Changes</template>
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Delete Inflow Modal -->
    <transition name="fade">
      <div v-if="inflowToDelete" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="inflowToDelete = null" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        <div class="relative w-full max-w-sm bg-white dark:bg-[#0d151a] rounded-[40px] shadow-2xl p-10 text-center outline-none z-10">
          <div class="w-16 h-16 bg-red-50 dark:bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-6 text-red-650 dark:text-red-405 border border-red-100 dark:border-red-500/15">
            <Trash2 class="w-8 h-8" />
          </div>
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white mb-2 font-display">Delete inflow record?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 leading-relaxed text-sm mb-8">
            Are you sure you want to delete this cash inflow of <strong class="text-zinc-900 dark:text-white">{{ getCurrencySymbol(inflowToDelete.currencyCode) }}{{ formatCurrency(inflowToDelete.originalAmount || inflowToDelete.amount) }}</strong>? This subtraction affects the target metrics.
          </p>
          <div class="flex gap-3">
            <button
              @click="inflowToDelete = null"
              class="flex-1 py-4 bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-white rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-all cursor-pointer"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteInflow"
              class="flex-1 py-4 bg-red-650 text-white rounded-2xl font-bold hover:bg-red-700 transition-all cursor-pointer shadow-lg shadow-red-500/10"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- AI Insights Modal -->
    <transition name="fade">
      <div v-if="isAnalysisModalOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAnalysisModalOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        
        <div class="relative w-full max-w-2xl bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[44px] shadow-2xl p-10 z-10 max-h-[85vh] overflow-y-auto custom-scrollbar flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-8">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-100 dark:border-emerald-500/15 rounded-2xl flex items-center justify-center text-emerald-600 dark:text-emerald-400">
                  <Sparkles class="w-6 h-6 animate-pulse" />
                </div>
                <div>
                  <h3 class="text-2xl font-bold text-zinc-900 dark:text-white font-display">Target & Inflows Agent Report</h3>
                  <p class="text-[9px] text-zinc-400 font-bold uppercase tracking-widest font-mono">{{ group.name }}</p>
                </div>
              </div>
              <button @click="isAnalysisModalOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer transition-colors outline-none">
                <X class="w-5 h-5 text-zinc-400" />
              </button>
            </div>

            <!-- Loader -->
            <div v-if="isAnalyzing" class="py-20 text-center flex flex-col items-center justify-center">
              <Loader2 class="w-10 h-10 animate-spin text-emerald-600 mb-4" />
              <p class="text-zinc-500 text-sm font-semibold animate-pulse">Consulting finance strategist AI agent...</p>
            </div>

            <!-- AI result content -->
            <div v-else class="prose dark:prose-invert max-w-none pt-2" v-html="parsedAnalysisResult" />
          </div>

          <div class="mt-10 pt-6 border-t border-zinc-100 dark:border-zinc-850 flex justify-end">
            <button 
              @click="isAnalysisModalOpen = false"
              class="px-8 py-3.5 bg-zinc-900 dark:bg-white text-white dark:text-zinc-950 font-bold rounded-2xl text-xs hover:shadow-lg transition-all cursor-pointer outline-none"
            >
              Close Strategic Review
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Group Settings / Delete Group Modal -->
    <transition name="fade">
      <div v-if="isSettingsOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isSettingsOpen = false" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
        
        <div class="relative w-full max-w-md bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 max-h-[90vh] overflow-y-auto custom-scrollbar">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Group Preferences</h3>
            <button @click="isSettingsOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full transition-colors cursor-pointer outline-none">
              <X class="w-5 h-5 text-zinc-500" />
            </button>
          </div>

          <!-- Edit group options -->
          <form @submit.prevent="handleUpdateGroupSettings" class="space-y-6">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Group Name</label>
              <input
                type="text"
                v-model="editName"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-medium dark:text-white"
                required
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.15em] mb-2 font-display">Description</label>
              <textarea
                v-model="editDescription"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500 transition-all font-medium dark:text-white resize-none h-24"
              />
            </div>

            <button
              type="submit"
              class="w-full py-4 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all shadow-md active:scale-95 cursor-pointer"
            >
              Save Changes
            </button>
          </form>

          <div class="pt-8 border-t border-zinc-100 dark:border-zinc-800 mt-8">
            <h4 class="text-[10px] font-bold uppercase tracking-[0.2em] text-red-500 mb-4 font-display">Dangerous zone</h4>
            <div class="p-4 bg-red-50 dark:bg-red-500/5 rounded-2xl border border-red-100 dark:border-red-500/10 flex flex-col gap-4">
              <p class="text-[11px] text-red-700 dark:text-red-400 font-medium leading-relaxed">
                Deleting this income tracking group dissolves all streams, logged inflows, and metrics irreversibly.
              </p>
              <button 
                @click="handleDeleteGroup"
                class="py-3 bg-red-600 hover:bg-red-700 text-white font-bold rounded-xl text-xs transition-all active:scale-95 cursor-pointer outline-none"
              >
                Permanently Dissolve Group
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>
