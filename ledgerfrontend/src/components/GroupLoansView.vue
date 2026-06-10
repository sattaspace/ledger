<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  ArrowLeft, 
  Plus, 
  Trash2, 
  ChevronRight, 
  CheckCircle2, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Calendar,
  User,
  ArrowRightLeft,
  X,
  CreditCard,
  History,
  Pencil,
  AlertCircle,
  HelpCircle,
  Info,
  Settings,
  ShieldAlert,
  Landmark
} from 'lucide-vue-next';
import { type Group, type Loan, type LoanPayment } from '../types';
import { db } from '../firebase';
import { collection, query, onSnapshot, orderBy, doc, deleteDoc, setDoc, updateDoc, Timestamp, addDoc } from 'firebase/firestore';
import { formatCurrency } from '../utils/format';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { convertCurrency, getCurrencySymbol, CURRENCIES } from '../utils/currency';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

const group = ref<Group | null>(null);
const loans = ref<Loan[]>([]);
const paymentsMap = ref<Map<string, LoanPayment[]>>(new Map());
const accountsList = ref<Group[]>([]);
const loading = ref(true);

// Modals / Overlays
const isCreateLoanOpen = ref(false);
const isAddPaymentOpen = ref(false);
const isSettingsOpen = ref(false);
const isDeleteConfirmOpen = ref(false);
const activeSelectedLoan = ref<Loan | null>(null);
const expandedLoanId = ref<string | null>(null);

// Settings Form Fields
const editName = ref('');
const editDescription = ref('');
const editCurrencyCode = ref('USD');

// Form Fields
const newLoanType = ref<'given' | 'taken'>('given');
const newLoanPerson = ref('');
const newLoanAmount = ref('');
const newLoanInterest = ref('0');
const newLoanDate = ref(new Date().toISOString().split('T')[0]);
const newLoanDueDate = ref('');
const newLoanDesc = ref('');

// Filter state
const activeFilter = ref<'all' | 'given' | 'taken'>('all');

const payAmount = ref('');
const payDate = ref(new Date().toISOString().split('T')[0]);
const payNote = ref('');
const payLinkedAccountId = ref('');

const unsubscribes = ref<(() => void)[]>([]);

const initDataStreams = () => {
  unsubscribes.value.forEach(unsub => unsub());
  unsubscribes.value = [];
  loading.value = true;

  // 1. Fetch Group Metadata
  const unsubGroup = onSnapshot(doc(db, 'groups', props.groupId), (snap) => {
    if (snap.exists()) {
      group.value = { id: snap.id, ...snap.data() } as Group;
    } else {
      emit('back');
    }
  });
  unsubscribes.value.push(unsubGroup);

  // 2. Fetch Accounts
  const unsubAccounts = onSnapshot(collection(db, 'groups'), (snap) => {
    accountsList.value = snap.docs
      .map(doc => ({ id: doc.id, ...doc.data() } as Group))
      .filter(g => g.service === 'accounts');
  });
  unsubscribes.value.push(unsubAccounts);

  // 3. Fetch Loans unique to this group
  const loansQuery = query(
    collection(db, 'groups', props.groupId, 'loans_debts'),
    orderBy('createdAt', 'desc')
  );

  const unsubLoans = onSnapshot(loansQuery, (snap) => {
    loans.value = snap.docs.map(doc => {
      const data = doc.data();
      let dDate = data.date;
      if (typeof dDate === 'string') {
        dDate = { toMillis: () => Date.parse(dDate), toDate: () => new Date(dDate) };
      }
      let duDate = data.dueDate;
      if (typeof duDate === 'string') {
        duDate = { toMillis: () => Date.parse(duDate), toDate: () => new Date(duDate) };
      }

      return {
        id: doc.id,
        ...data,
        date: dDate,
        dueDate: duDate
      } as Loan;
    });

    // Subscribe to each loan's payments/installments list
    loans.value.forEach(loan => {
      const paymentsQuery = query(
        collection(db, 'groups', props.groupId, 'loans_debts', loan.id, 'loan_payments'),
        orderBy('date', 'desc')
      );

      const unsubPayments = onSnapshot(paymentsQuery, (psnap) => {
        const payments = psnap.docs.map(pdoc => {
          const pdata = pdoc.data();
          let pdate = pdata.date;
          if (typeof pdate === 'string') {
            pdate = { toMillis: () => Date.parse(pdate), toDate: () => new Date(pdate) };
          }
          return {
            id: pdoc.id,
            ...pdata,
            date: pdate
          } as LoanPayment;
        });

        paymentsMap.value.set(loan.id, payments);
      });
      unsubscribes.value.push(unsubPayments);
    });

    loading.value = false;
  }, (err) => {
    console.error("Loans subscription error:", err);
  });
  unsubscribes.value.push(unsubLoans);
};

onMounted(() => {
  initDataStreams();
});

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

// Stats calculated in the Active Group's Currency
const groupStats = computed(() => {
  let lentPrincipal = 0;
  let lentRepaid = 0;
  let borrowedPrincipal = 0;
  let borrowedRepaid = 0;
  let lentOutstanding = 0;
  let borrowedOutstanding = 0;

  loans.value.forEach(loan => {
    const list = paymentsMap.value.get(loan.id) || [];
    const repaid = list.reduce((sum, p) => sum + p.amount, 0);

    if (loan.type === 'given') {
      lentPrincipal += loan.amount;
      lentRepaid += repaid;
      if (loan.status !== 'settled') {
        lentOutstanding += Math.max(loan.amount - repaid, 0);
      }
    } else {
      borrowedPrincipal += loan.amount;
      borrowedRepaid += repaid;
      if (loan.status !== 'settled') {
        borrowedOutstanding += Math.max(loan.amount - repaid, 0);
      }
    }
  });

  const netPosition = lentOutstanding - borrowedOutstanding;

  return {
    lentPrincipal,
    lentRepaid,
    borrowedPrincipal,
    borrowedRepaid,
    lentOutstanding,
    borrowedOutstanding,
    net: netPosition
  };
});

const getLoanRepaidPercentage = (loan: Loan) => {
  if (loan.status === 'settled') return 100;
  const ps = paymentsMap.value.get(loan.id) || [];
  const repaid = ps.reduce((s, p) => s + p.amount, 0);
  if (loan.amount <= 0) return 100;
  return Math.min(Math.round((repaid / loan.amount) * 100), 100);
};

const getLoanOutstanding = (loan: Loan) => {
  if (loan.status === 'settled') return 0;
  const ps = paymentsMap.value.get(loan.id) || [];
  const repaid = ps.reduce((s, p) => s + p.amount, 0);
  return Math.max(loan.amount - repaid, 0);
};

// Filtered Loans based on current tab selection
const filteredLoans = computed(() => {
  if (activeFilter.value === 'given') {
    return loans.value.filter(l => l.type === 'given');
  }
  if (activeFilter.value === 'taken') {
    return loans.value.filter(l => l.type === 'taken');
  }
  return loans.value;
});

// Actions
const handleCreateLoan = async () => {
  if (!newLoanPerson.value.trim() || !newLoanAmount.value) return;

  try {
    const amt = parseFloat(newLoanAmount.value) || 0;
    if (amt <= 0) return;

    const loanId = crypto.randomUUID();
    const loanPayload: Loan = {
      id: loanId,
      groupId: props.groupId,
      type: newLoanType.value,
      personName: newLoanPerson.value.trim(),
      amount: amt,
      interestRate: parseFloat(newLoanInterest.value) || 0,
      currencyCode: group.value?.currencyCode || 'USD',
      date: Timestamp.fromDate(new Date(newLoanDate.value)),
      status: 'active',
      description: newLoanDesc.value.trim() || undefined,
      createdAt: Timestamp.now(),
      createdBy: props.user.uid
    };

    if (newLoanDueDate.value) {
      loanPayload.dueDate = Timestamp.fromDate(new Date(newLoanDueDate.value));
    }

    await setDoc(doc(db, 'groups', props.groupId, 'loans_debts', loanId), loanPayload);
    isCreateLoanOpen.value = false;

    // Reset Form Fields
    newLoanPerson.value = '';
    newLoanAmount.value = '';
    newLoanInterest.value = '0';
    newLoanDate.value = new Date().toISOString().split('T')[0];
    newLoanDueDate.value = '';
    newLoanDesc.value = '';
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'loans_debts');
  }
};

const openPaymentForm = (loan: Loan) => {
  activeSelectedLoan.value = loan;
  payAmount.value = getLoanOutstanding(loan).toString();
  payDate.value = new Date().toISOString().split('T')[0];
  payNote.value = '';
  payLinkedAccountId.value = '';
  isAddPaymentOpen.value = true;
};

const handleRecordPayment = async () => {
  if (!activeSelectedLoan.value || !payAmount.value) return;

  try {
    const amt = parseFloat(payAmount.value) || 0;
    if (amt <= 0) return;

    const loan = activeSelectedLoan.value;
    const paymentId = crypto.randomUUID();
    let txnId: string | undefined;

    // Link Bank Account
    if (payLinkedAccountId.value) {
      const bank = accountsList.value.find(acc => acc.id === payLinkedAccountId.value);
      if (bank) {
        txnId = crypto.randomUUID();
        const isExpense = loan.type === 'taken';
        const linkAmt = isExpense ? -amt : amt;

        const txPayload = {
          id: txnId,
          groupId: bank.id,
          accountId: bank.id,
          amount: linkAmt,
          description: isExpense ? `Loan Repay: ${loan.personName}` : `Loan Recov: ${loan.personName}`,
          category: isExpense ? 'Card Payment' : 'Salary & Deposit',
          date: Timestamp.fromDate(new Date(payDate.value)),
          createdAt: Timestamp.now(),
          note: `Auto-linked payment of loan: ${loan.personName}`,
          type: isExpense ? 'expense' : 'deposit'
        };

        await setDoc(doc(db, 'groups', bank.id, 'account_transactions', txnId), txPayload);

        // Update physical balance
        let newBal = parseFloat(bank.balance as any || 0);
        if (bank.accountType === 'credit_card') {
          newBal = newBal - linkAmt;
        } else {
          newBal = newBal + linkAmt;
        }
        await updateDoc(doc(db, 'groups', bank.id), { balance: newBal });
      }
    }

    const payPayload = {
      id: paymentId,
      groupId: props.groupId,
      loanId: loan.id,
      amount: amt,
      date: Timestamp.fromDate(new Date(payDate.value)),
      createdAt: Timestamp.now(),
      note: payNote.value.trim() || undefined,
      linkedAccountId: payLinkedAccountId.value || undefined,
      linkedTransactionId: txnId || undefined
    };

    await setDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id, 'loan_payments', paymentId), payPayload);

    // If fully settled, mark active loan as settled
    const outstanding = getLoanOutstanding(loan) - amt;
    if (outstanding <= 0.01) {
      await updateDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id), { status: 'settled' });
    }

    isAddPaymentOpen.value = false;
    activeSelectedLoan.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'loan_payments');
  }
};

const handleDeleteLoan = async (loan: Loan) => {
  if (!confirm(`Are you sure you want to permanently delete loan with "${loan.personName}"? This is irreversible.`)) return;

  try {
    const list = paymentsMap.value.get(loan.id) || [];
    for (const p of list) {
      await handleDeletePayment(loan, p, false);
    }
    await deleteDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id));
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, 'loans_debts');
  }
};

const handleDeletePayment = async (loan: Loan, payment: LoanPayment, prompt = true) => {
  if (prompt && !confirm("Are you sure you want to delete this payment record? This will adjust outstanding balance & recover bank funds.")) return;

  try {
    // 1. Roll back linked bank card transactions
    if (payment.linkedAccountId && payment.linkedTransactionId) {
      const bank = accountsList.value.find(acc => acc.id === payment.linkedAccountId);
      if (bank) {
        // Reverse bank balance modification
        const amt = payment.amount;
        const isExpense = loan.type === 'taken'; // case taken: we paid (+amount rollback), case given: we received (-amount rollback)
        const rollbackAmt = isExpense ? amt : -amt;

        let newBal = parseFloat(bank.balance as any || 0);
        if (bank.accountType === 'credit_card') {
          newBal = newBal - rollbackAmt;
        } else {
          newBal = newBal + rollbackAmt;
        }
        
        await updateDoc(doc(db, 'groups', bank.id), { balance: newBal });
        // Delete ledger entry
        await deleteDoc(doc(db, 'groups', bank.id, 'account_transactions', payment.linkedTransactionId));
      }
    }

    // 2. Delete payment document
    await deleteDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id, 'loan_payments', payment.id));
    
    // 3. Set loan active status back to active if it was settled
    if (loan.status === 'settled') {
      await updateDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id), { status: 'active' });
    }
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, 'loan_payments');
  }
};

const toggleExpandLoan = (id: string) => {
  expandedLoanId.value = expandedLoanId.value === id ? null : id;
};

const getBankName = (id: string) => {
  const b = accountsList.value.find(acc => acc.id === id);
  return b ? b.name : 'Unknown Card';
};

const openSettings = () => {
  if (group.value) {
    editName.value = group.value.name || '';
    editDescription.value = group.value.description || '';
    editCurrencyCode.value = group.value.currencyCode || 'USD';
    isSettingsOpen.value = true;
  }
};

const handleUpdateSettings = async () => {
  if (!editName.value.trim() || !group.value) return;
  try {
    const groupRef = doc(db, 'groups', props.groupId);
    await updateDoc(groupRef, {
      name: editName.value.trim(),
      description: editDescription.value.trim(),
      currencyCode: editCurrencyCode.value
    });
    isSettingsOpen.value = false;
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, 'groups');
  }
};

const handleDeleteGroup = async () => {
  if (!group.value) return;
  try {
    await deleteDoc(doc(db, 'groups', props.groupId));
    isDeleteConfirmOpen.value = false;
    emit('back');
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, 'groups');
  }
};

const handleSettleMutually = async (loan: Loan) => {
  const remaining = getLoanOutstanding(loan);
  if (!confirm(`Are you sure you want to mutually settle this loan with "${loan.personName}"? Outstanding balance of ${formatCurrency(remaining, loan.currencyCode)} will be forgiven/waived and excluded from statistics.`)) return;

  try {
    await updateDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id), {
      status: 'settled',
      mutuallySettled: true,
      settledAt: Timestamp.now()
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, 'loans_debts');
  }
};

const handleReactivateLoan = async (loan: Loan) => {
  if (!confirm(`Are you sure you want to re-activate this loan agreement with "${loan.personName}"?`)) return;

  try {
    await updateDoc(doc(db, 'groups', props.groupId, 'loans_debts', loan.id), {
      status: 'active',
      mutuallySettled: false
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, 'loans_debts');
  }
};
</script>

<template>
  <div class="group-loans-view text-left" id="group-loans-wrapper">
    
    <!-- Navigation back -->
    <button 
      @click="emit('back')" 
      class="flex items-center gap-2 text-zinc-500 hover:text-zinc-950 dark:hover:text-white mb-6 font-semibold cursor-pointer border-none bg-transparent select-none"
    >
      <ArrowLeft class="w-4 h-4" />
      Back to Finance Services
    </button>

    <!-- Header Metadata -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-10 pb-8 border-b border-zinc-200 dark:border-white/5">
      <div>
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 rounded-xl flex items-center justify-center">
            <User class="w-6 h-6" />
          </div>
          <h1 class="text-3xl font-black tracking-tight text-zinc-950 dark:text-white font-display">
            {{ group?.name }}
          </h1>
        </div>
        <p class="text-zinc-500 dark:text-zinc-400 text-xs pl-13 max-w-xl italic">
          {{ group?.description || 'Active ledger of peer-to-peer loan channels.' }}
        </p>
      </div>

      <div class="flex items-center gap-3 shrink-0">
        <button 
          @click="openSettings" 
          class="p-4 bg-zinc-100 hover:bg-zinc-200 dark:bg-white/5 dark:hover:bg-white/10 text-zinc-700 dark:text-zinc-300 rounded-xl cursor-pointer transition-all"
          title="Ledger Settings"
        >
          <Settings class="w-5 h-5" />
        </button>
        <button 
          @click="isCreateLoanOpen = true" 
          class="flex items-center gap-2 px-6 py-3.5 bg-zinc-950 hover:bg-zinc-900 dark:bg-white dark:hover:bg-zinc-100 text-white dark:text-zinc-950 text-xs font-bold font-display rounded-xl tracking-tight shadow-md cursor-pointer transition-all"
        >
          <Plus class="w-4 h-4" />
          Configure New Loan
        </button>
      </div>
    </div>

    <!-- Stats Panel -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10" id="group-loans-stats">
      
      <!-- Lent out outstanding -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/5 rounded-3xl relative overflow-hidden shadow-sm">
        <p class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">Active Claims (Receivables)</p>
        <h4 class="text-2xl font-black font-mono mt-1 text-zinc-950 dark:text-white">
          {{ formatCurrency(groupStats.lentOutstanding, group?.currencyCode || 'USD') }}
        </h4>
        <div class="pt-3 border-t border-zinc-100 dark:border-white/5 mt-3 flex items-center justify-between text-[11px] text-zinc-500">
          <span>Principal amount: {{ formatCurrency(groupStats.lentPrincipal, group?.currencyCode) }}</span>
          <span>Repaid: {{ formatCurrency(groupStats.lentRepaid, group?.currencyCode) }}</span>
        </div>
      </div>

      <!-- Borrowed outstanding -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/5 rounded-3xl relative overflow-hidden shadow-sm">
        <p class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">Outstanding Debts (Payables)</p>
        <h4 class="text-2xl font-black font-mono mt-1 text-zinc-950 dark:text-white">
          {{ formatCurrency(groupStats.borrowedOutstanding, group?.currencyCode || 'USD') }}
        </h4>
        <div class="pt-3 border-t border-zinc-100 dark:border-white/5 mt-3 flex items-center justify-between text-[11px] text-zinc-500">
          <span>Principal amount: {{ formatCurrency(groupStats.borrowedPrincipal, group?.currencyCode) }}</span>
          <span>Repaid: {{ formatCurrency(groupStats.borrowedRepaid, group?.currencyCode) }}</span>
        </div>
      </div>

      <!-- Net leverage -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/5 rounded-3xl relative overflow-hidden shadow-sm">
        <p class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">Ledger Balance Position</p>
        <h4 class="text-2xl font-black font-mono mt-1" :class="groupStats.net >= 0 ? 'text-emerald-500' : 'text-rose-500'">
          {{ groupStats.net >= 0 ? '+' : '' }}{{ formatCurrency(groupStats.net, group?.currencyCode || 'USD') }}
        </h4>
        <div class="pt-3 border-t border-zinc-100 dark:border-white/5 mt-3 flex items-center justify-between text-[11px] text-zinc-500">
          <span>Difference Claim position</span>
          <span class="font-bold" :class="groupStats.net >= 0 ? 'text-emerald-600' : 'text-rose-600'">
            {{ groupStats.net >= 0 ? 'Lender Position' : 'Debtor Position' }}
          </span>
        </div>
      </div>

    </div>

    <!-- Active List -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <div class="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
    </div>

    <div v-else-if="loans.length === 0" class="py-20 text-center text-zinc-500 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[32px] shadow-sm">
      <Landmark class="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-750 mb-4 animate-bounce-slow" />
      <h3 class="font-bold text-zinc-950 dark:text-white tracking-tight mb-2 font-display">No logs inside this ledger</h3>
      <p class="text-xs text-zinc-500 max-w-sm mx-auto mb-6 leading-relaxed">
        Let's configure your first loan agreement! Claim payments, log borrowings or peer repayments easily.
      </p>
      <button 
        @click="isCreateLoanOpen = true" 
        class="py-3 px-5 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 rounded-xl text-xs font-bold cursor-pointer"
      >
        Configure Agreement
      </button>
    </div>

    <div v-else class="space-y-4">
      <!-- Tab Filters -->
      <div class="flex gap-2 p-1.5 bg-zinc-100 dark:bg-white/5 rounded-2xl w-fit mb-6 select-none border border-zinc-200/50 dark:border-white/5">
        <button 
          @click="activeFilter = 'all'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'all' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          All Agreements ({{ loans.length }})
        </button>
        <button 
          @click="activeFilter = 'given'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'given' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          Lent / Receivables ({{ loans.filter(l => l.type === 'given').length }})
        </button>
        <button 
          @click="activeFilter = 'taken'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'taken' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          Borrowed / Payables ({{ loans.filter(l => l.type === 'taken').length }})
        </button>
      </div>

      <!-- No items matching current filter -->
      <div v-if="filteredLoans.length === 0" class="py-20 text-center text-zinc-500 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[32px] shadow-sm">
        <Landmark class="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-750 mb-4 animate-pulse-slow" />
        <h3 class="font-bold text-zinc-950 dark:text-white tracking-tight mb-2 font-display">No matches found</h3>
        <p class="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
          No active agreements are logged under the "{{ activeFilter }}" classification in this ledger.
        </p>
      </div>

      <div v-else class="space-y-4" id="group-loans-list">
        <div 
          v-for="loan in filteredLoans" 
          :key="loan.id" 
          class="bg-white dark:bg-[#0c141d]/85 border border-zinc-205 dark:border-white/5 rounded-[24px] overflow-hidden shadow-sm hover:scale-[1.005] hover:shadow-md transition-all duration-300"
        >
          <!-- Row Header Grid -->
          <div 
            @click="toggleExpandLoan(loan.id)"
            class="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-zinc-50/50 dark:hover:bg-white/5 transition-colors select-none"
          >
            <div class="flex items-center gap-4">
              <div :class="`w-10 h-10 rounded-xl flex items-center justify-center border ${
                loan.type === 'given' 
                  ? 'bg-emerald-50 dark:bg-emerald-500/15 border-emerald-100 dark:border-emerald-500/20 text-emerald-600' 
                  : 'bg-rose-50 dark:bg-rose-500/15 border-rose-100 dark:border-rose-500/20 text-rose-600'
              }`">
                <User class="w-5 h-5 animate-pulse-slow" />
              </div>
              
              <div>
                <h4 class="font-extrabold text-sm text-zinc-950 dark:text-white tracking-tight flex items-center gap-2">
                  {{ loan.personName }}
                  <span v-if="loan.status === 'settled'" class="px-2 py-0.5 rounded-full text-[8.5px] font-black bg-emerald-50 dark:bg-emerald-500/20 text-emerald-600">Settled</span>
                </h4>
                <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mt-1">
                  {{ loan.type === 'given' ? 'Lent out Receivable' : 'Borrowed Payable' }}
                </p>
              </div>
            </div>

          <!-- Progress -->
          <div class="flex-1 max-w-sm sm:mx-10">
            <div class="flex items-center justify-between text-xs mb-1.5 font-medium">
              <span class="text-zinc-400">Repaid ({{ getLoanRepaidPercentage(loan) }}%)</span>
              <span class="font-extrabold text-[#005a5b] dark:text-teal-400 font-mono">{{ formatCurrency(getLoanOutstanding(loan), loan.currencyCode) }} Outstanding</span>
            </div>
            <div class="w-full h-1.5 bg-zinc-100 dark:bg-[#121c27] rounded-full overflow-hidden border border-zinc-200/20">
              <div 
                :class="`h-full rounded-full transition-all duration-300 ${loan.type === 'given' ? 'bg-emerald-500' : 'bg-indigo-500'}`"
                :style="`width: ${getLoanRepaidPercentage(loan)}%`"
              />
            </div>
          </div>

          <div class="flex items-center gap-6 shrink-0">
            <div class="text-right">
              <p class="text-[9px] font-bold text-zinc-400 uppercase tracking-wider">Principal</p>
              <h4 class="text-base font-extrabold font-mono tracking-tight text-zinc-900 dark:text-zinc-200">
                {{ formatCurrency(loan.amount, loan.currencyCode) }}
              </h4>
            </div>

            <ChevronRight 
              class="w-5 h-5 text-zinc-400 transition-transform duration-300" 
              :class="expandedLoanId === loan.id ? 'rotate-90' : ''" 
            />
          </div>
        </div>

        <!-- Expanded Details (Log Installments table & metadata) -->
        <div v-show="expandedLoanId === loan.id" class="px-6 pb-6 bg-zinc-50/50 dark:bg-[#070b0f] border-t border-zinc-100 dark:border-white/5 animate-in">
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-6 pt-6">
            
            <!-- Metadata details -->
            <div class="space-y-4">
              <h5 class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest flex items-center gap-1">
                <Info class="w-3.5" />
                Agreement Metadata
              </h5>
              <div class="bg-white dark:bg-[#0d141d] p-4 border border-zinc-105 dark:border-white/5 rounded-2xl text-xs space-y-2.5">
                <div class="flex items-center justify-between">
                  <span class="text-zinc-400 font-medium">Initiated date:</span>
                  <span class="font-bold text-zinc-900 dark:text-zinc-300">{{ loan.date.toDate().toLocaleDateString() }}</span>
                </div>
                <div v-if="loan.dueDate" class="flex items-center justify-between">
                  <span class="text-zinc-400 font-medium">Due deadline:</span>
                  <span class="font-bold text-zinc-900 dark:text-zinc-300 text-rose-500">{{ loan.dueDate.toDate().toLocaleDateString() }}</span>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-zinc-400 font-medium">Interest charge:</span>
                  <span class="font-bold text-zinc-900 dark:text-zinc-300">{{ loan.interestRate || '0' }}% Flat</span>
                </div>
                <div v-if="loan.description" class="pt-2 border-t border-zinc-100 dark:border-white/5">
                  <span class="text-zinc-400 font-medium">Description note:</span>
                  <p class="mt-1 leading-relaxed text-[11px] text-zinc-500 italic">"{{ loan.description }}"</p>
                </div>
              </div>

              <div class="flex flex-col gap-2">
                <div class="flex items-center gap-2">
                  <button 
                    @click="handleDeleteLoan(loan)"
                    class="flex-1 py-3 border border-rose-500/20 hover:bg-rose-500/10 text-rose-600 dark:text-rose-450 font-bold text-xs rounded-xl transition-colors cursor-pointer"
                  >
                    Delete Agreement
                  </button>
                  <button 
                    v-if="loan.status !== 'settled'"
                    @click="openPaymentForm(loan)"
                    class="flex-1 py-3 bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 font-bold text-xs rounded-xl transition-colors cursor-pointer"
                  >
                    Record Payment
                  </button>
                </div>
                <button 
                  v-if="loan.status !== 'settled'"
                  @click="handleSettleMutually(loan)"
                  class="w-full py-3 bg-amber-500 hover:bg-amber-600 text-zinc-950 font-bold text-xs rounded-xl transition-colors cursor-pointer"
                >
                  Mutually Settle Loan
                </button>
                <button 
                  v-else
                  @click="handleReactivateLoan(loan)"
                  class="w-full py-3 border border-zinc-200 dark:border-white/10 text-zinc-700 dark:text-zinc-300 font-bold text-xs rounded-xl transition-colors cursor-pointer"
                >
                  Re-active Agreement
                </button>
              </div>

            </div>

            <!-- Installment historical payments list -->
            <div class="md:col-span-2 space-y-4">
              <h5 class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest flex items-center gap-1.5 leading-none">
                <History class="w-3.5" />
                Repayment installments History Log
              </h5>

              <div class="bg-white dark:bg-[#0d141d] border border-zinc-100 dark:border-white/5 rounded-2xl overflow-hidden">
                <div v-if="!paymentsMap.get(loan.id) || paymentsMap.get(loan.id)!.length === 0" class="p-10 text-center text-zinc-500 italic text-xs">
                  No installment repayment has been recorded as of yet for this loan.
                </div>

                <table v-else class="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr class="bg-zinc-50 dark:bg-zinc-900/40 text-zinc-400 text-[10px] uppercase font-bold tracking-wider border-b border-zinc-102 dark:border-white/5">
                      <th class="p-4">Paid Date</th>
                      <th class="p-4">Linked Ledger Option</th>
                      <th class="p-4">Note / Reason</th>
                      <th class="p-4 text-right">Sum paid</th>
                      <th class="p-4 text-center">Deconstruct</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-zinc-50 dark:divide-white/5">
                    <tr 
                      v-for="pay in paymentsMap.get(loan.id)" 
                      :key="pay.id"
                      class="hover:bg-zinc-50/20 dark:hover:bg-white/5 transition-colors"
                    >
                      <td class="p-4 font-medium">{{ pay.date.toDate().toLocaleDateString() }}</td>
                      <td class="p-4 font-bold text-indigo-600 dark:text-teal-400">
                        {{ pay.linkedAccountId ? getBankName(pay.linkedAccountId) : 'Cash Payment (Manual)' }}
                      </td>
                      <td class="p-4 italic text-zinc-500">{{ pay.note || '--' }}</td>
                      <td class="p-4 text-right font-bold font-mono text-zinc-900 dark:text-zinc-200">
                        {{ formatCurrency(pay.amount, loan.currencyCode) }}
                      </td>
                      <td class="p-4 text-center">
                        <button 
                          @click="handleDeletePayment(loan, pay)"
                          class="p-2 text-zinc-400 hover:text-rose-500 hover:bg-[#fff5f5] dark:hover:bg-zinc-900 rounded-lg transition-all border-none bg-transparent cursor-pointer"
                        >
                          <Trash2 class="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

          </div>

        </div>
      </div>
    </div>
  </div>

    <!-- Create Loan Modal Overlay -->
    <transition name="fade">
      <div v-if="isCreateLoanOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isCreateLoanOpen = false" class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg bg-white dark:bg-zinc-955 border border-zinc-200 dark:border-zinc-800 rounded-[32px] p-8 shadow-2xl z-10 animate-in overflow-y-auto max-h-[90vh]">
          
          <div class="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-white/5 mb-6">
            <h3 class="text-xl font-bold tracking-tight text-zinc-950 dark:text-white font-display">Log Peer Loan Proposal</h3>
            <button @click="isCreateLoanOpen = false" class="p-2 text-zinc-400 hover:text-zinc-900 dark:hover:text-white cursor-pointer rounded-lg bg-transparent border-none">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleCreateLoan" class="space-y-4 text-left">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Classification Type</label>
              <div class="grid grid-cols-2 gap-4">
                <button 
                  type="button" 
                  @click="newLoanType = 'given'" 
                  :class="`py-4 rounded-xl font-bold max-h-[50px] border flex items-center justify-center gap-2 text-xs cursor-pointer transition-all ${
                    newLoanType === 'given' 
                      ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 text-emerald-600' 
                      : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-400'
                  }`"
                >
                  <TrendingUp class="w-4 h-4" />
                  Given (Lent by me)
                </button>
                <button 
                  type="button" 
                  @click="newLoanType = 'taken'" 
                  :class="`py-4 rounded-xl font-bold max-h-[50px] border flex items-center justify-center gap-2 text-xs cursor-pointer transition-all ${
                    newLoanType === 'taken' 
                      ? 'bg-rose-50 dark:bg-rose-500/10 border-rose-500 text-rose-600' 
                      : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-800 text-zinc-400'
                  }`"
                >
                  <TrendingDown class="w-4 h-4" />
                  Taken (Borrowed)
                </button>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Person involved</label>
                <input 
                  v-model="newLoanPerson" 
                  type="text" 
                  placeholder="e.g. Rachel, Bank, Family" 
                  required
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Principal Sum ({{ group?.currencyCode }})</label>
                <input 
                  v-model="newLoanAmount" 
                  type="number" 
                  step="any" 
                  placeholder="0.00" 
                  required
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold"
                />
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Initiated Date</label>
                <input 
                  v-model="newLoanDate" 
                  type="date" 
                  required
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-xl focus:outline-none text-xs font-semibold"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Due Deadline Date (Optional)</label>
                <input 
                  v-model="newLoanDueDate" 
                  type="date" 
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-xl focus:outline-none text-xs font-semibold"
                />
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Flat Simple Annual interest rate %</label>
              <input 
                v-model="newLoanInterest" 
                type="number" 
                step="0.1" 
                placeholder="0" 
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-xl focus:outline-none text-xs font-semibold"
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Notes & Description memo</label>
              <textarea 
                v-model="newLoanDesc" 
                placeholder="Details of agreement context..." 
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-205 dark:border-zinc-805 rounded-xl h-20 text-xs font-semibold resize-none focus:outline-none"
              />
            </div>

            <button 
              type="submit" 
              class="w-full py-4 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 text-xs font-bold rounded-xl mt-4 hover:bg-zinc-920 dark:hover:bg-zinc-100 transition-colors shadow-lg cursor-pointer"
            >
              Verify & Save Loan Setup
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Record Payment Modal Overlay -->
    <transition name="fade">
      <div v-if="isAddPaymentOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddPaymentOpen = false" class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-955 border border-zinc-200 dark:border-zinc-800 rounded-[32px] p-8 shadow-2xl z-10 animate-in">
          
          <div class="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-white/5 mb-6">
            <h3 class="text-xl font-bold tracking-tight text-zinc-950 dark:text-white font-display">Record installment Repayment</h3>
            <button @click="isAddPaymentOpen = false" class="p-2 text-zinc-400 hover:text-zinc-950 dark:hover:text-white cursor-pointer rounded-lg bg-transparent border-none">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleRecordPayment" class="space-y-4 text-left">
            <div>
              <p class="text-xs text-zinc-500 mb-1 font-semibold">Active Loan Record: <span class="text-zinc-950 dark:text-white font-bold">{{ activeSelectedLoan?.personName }}</span></p>
              <p class="text-xs text-zinc-500 font-semibold">Outstanding Remaining: <span class="text-[#005a5b] dark:text-teal-400 font-bold font-mono">{{ formatCurrency(getLoanOutstanding(activeSelectedLoan!), activeSelectedLoan?.currencyCode) }}</span></p>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Payment Amount ({{ activeSelectedLoan?.currencyCode }})</label>
              <input 
                v-model="payAmount" 
                type="number" 
                step="any" 
                required
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-202 dark:border-zinc-805 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold"
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Payment Date</label>
              <input 
                v-model="payDate" 
                type="date" 
                required
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-202 dark:border-zinc-805 rounded-xl focus:outline-none text-xs font-semibold"
              />
            </div>

            <div>
              <div class="flex items-center justify-between mb-3 leading-none">
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] font-display">Link Bank Account/Card (Auto-Deduct)</label>
                <span class="text-[9px] text-[#005253] dark:text-teal-400 font-bold font-mono">Optional</span>
              </div>
              <select 
                v-model="payLinkedAccountId"
                class="w-full px-4 py-3.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-202 dark:border-zinc-805 rounded-xl block focus:outline-none text-xs font-semibold"
              >
                <option value="">-- No Account Deduction (Manual Entry) --</option>
                <option v-for="acc in accountsList" :key="acc.id" :value="acc.id">
                  {{ acc.name }} ({{ formatCurrency(acc.balance || 0, acc.currencyCode) }})
                </option>
              </select>
              <p class="text-[10px] text-zinc-500 mt-2 leading-tight font-medium">
                When linked, this repayment will automatically record a bank ledger transaction and adjust their balance.
              </p>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Notes / Memo</label>
              <input 
                v-model="payNote" 
                type="text" 
                placeholder="e.g. third installment, direct check payer" 
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-202 dark:border-zinc-805 rounded-xl focus:outline-none text-xs text-zinc-850"
              />
            </div>

            <button 
              type="submit" 
              class="w-full py-4 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 text-xs font-bold rounded-xl mt-4 hover:bg-zinc-900 dark:hover:bg-zinc-100 transition-colors shadow-lg cursor-pointer"
            >
              Verify & Record Repayment
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Ledger Configuration Modal (Settings) -->
    <transition name="fade">
      <div v-if="isSettingsOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isSettingsOpen = false" class="absolute inset-0 bg-zinc-950/65 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg bg-white dark:bg-[#0c1216] border border-zinc-200 dark:border-white/5 rounded-[40px] shadow-2xl p-10 outline-none z-10 text-left">
          <div class="flex items-center justify-between mb-8">
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display flex items-center gap-2">
              <Settings class="w-6 h-6 text-indigo-500" />
              Ledger Configuration
            </h3>
            <button @click="isSettingsOpen = false" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-full cursor-pointer text-zinc-500 border-none bg-transparent">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleUpdateSettings" class="space-y-6">
            <div>
              <label for="edit-ledger-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Ledger Name</label>
              <input
                id="edit-ledger-name"
                v-model="editName"
                type="text"
                placeholder="e.g. Rachel / peer loans"
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold text-zinc-900 dark:text-white"
                required
              />
            </div>

            <div>
              <label for="edit-ledger-desc" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Description</label>
              <textarea
                id="edit-ledger-desc"
                v-model="editDescription"
                placeholder="Details of peer-to-peer loan channels..."
                class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-semibold text-zinc-900 dark:text-white resize-none h-24"
              />
            </div>

            <div>
              <label for="edit-ledger-currency" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-1.5 font-display">Ledger Default Currency</label>
              <select
                id="edit-ledger-currency"
                v-model="editCurrencyCode"
                class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-white/5 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
              >
                <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }} ({{ c.symbol }})</option>
              </select>
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
                Deconstruct Ledger
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
          <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display mb-3">Deconstruct Ledger?</h3>
          <p class="text-zinc-500 dark:text-zinc-400 text-sm mb-8 leading-relaxed">
            This will permanently delete <span class="font-bold text-zinc-900 dark:text-white">"{{ group?.name }}"</span> and erase its transaction logs and historical peer loan-debt records. This operation is absolute and cannot be undone.
          </p>
          <div class="flex items-center gap-4">
            <button
              @click="isDeleteConfirmOpen = false"
              type="button"
              class="flex-1 py-4.5 bg-zinc-100 dark:bg-white/5 text-zinc-700 dark:text-zinc-300 font-bold rounded-2xl border-none hover:bg-zinc-200 dark:hover:bg-white/10 transition-all active:scale-[0.98] cursor-pointer text-xs uppercase"
            >
              Cancel
            </button>
            <button
              @click="handleDeleteGroup"
              type="button"
              class="flex-1 py-4.5 bg-red-600 text-white font-bold rounded-2xl border-none hover:bg-red-700 transition-all active:scale-[0.98] cursor-pointer shadow-lg shadow-red-500/20 text-xs uppercase"
            >
              Confirm Deconstruct
            </button>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>
