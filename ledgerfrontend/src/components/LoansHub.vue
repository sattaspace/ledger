<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue';
import { 
  Scale, 
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
  Home,
  Landmark,
  Info
} from 'lucide-vue-next';
import { type Group, type Loan, type LoanPayment } from '../types';
import { db } from '../firebase';
import { collection, query, onSnapshot, orderBy, doc, deleteDoc, setDoc, updateDoc, Timestamp, addDoc } from 'firebase/firestore';
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

const loans = ref<Loan[]>([]);
const paymentsMap = ref<Map<string, LoanPayment[]>>(new Map());
const accountsList = ref<Group[]>([]);
const loading = ref(true);
const activeTab = ref<'all' | 'given' | 'taken' | 'settled'>('all');
const searchQuery = ref('');

// Modals
const isCreateLoanOpen = ref(false);
const isAddPaymentOpen = ref(false);
const activeSelectedLoan = ref<Loan | null>(null);

// Forms State
const newLoanGroupId = ref('');
const newLoanType = ref<'given' | 'taken'>('given');
const newLoanPerson = ref('');
const newLoanAmount = ref('');
const newLoanInterest = ref('0');
const newLoanCurrency = ref('USD');
const newLoanDate = ref(new Date().toISOString().split('T')[0]);
const newLoanDueDate = ref('');
const newLoanDesc = ref('');

const payAmount = ref('');
const payDate = ref(new Date().toISOString().split('T')[0]);
const payNote = ref('');
const payLinkedAccountId = ref('');

const unsubscribes = ref<(() => void)[]>([]);

// Filter and map only loans_debts groups
const loansGroups = computed(() => {
  return props.groups.filter(g => g.service === 'loans_debts');
});

const setupSubscriptions = () => {
  unsubscribes.value.forEach(unsub => unsub());
  unsubscribes.value = [];
  loading.value = true;

  if (loansGroups.value.length === 0) {
    loans.value = [];
    paymentsMap.value.clear();
    loading.value = false;
    return;
  }

  const loansListTempRef = ref<Loan[]>([]);
  const resolvedCountMap = ref(new Map<string, boolean>());

  // Fetch accounts for linkage
  const unsubAccounts = onSnapshot(collection(db, 'groups'), (snap) => {
    accountsList.value = snap.docs
      .map(doc => ({ id: doc.id, ...doc.data() } as Group))
      .filter(g => g.service === 'accounts');
  });
  unsubscribes.value.push(unsubAccounts);

  loansGroups.value.forEach(g => {
    const qLoans = query(
      collection(db, 'groups', g.id, 'loans_debts'),
      orderBy('createdAt', 'desc')
    );

    const unsubL = onSnapshot(qLoans, (snap) => {
      // Remove previous loans of this group
      loansListTempRef.value = loansListTempRef.value.filter(l => l.groupId !== g.id);

      const list = snap.docs.map(doc => {
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

      loansListTempRef.value.push(...list);
      loans.value = [...loansListTempRef.value];

      // Setup subcollection listener for payments under each loan
      list.forEach(loan => {
        const qPayments = query(
          collection(db, 'groups', g.id, 'loans_debts', loan.id, 'loan_payments'),
          orderBy('date', 'desc')
        );

        const unsubP = onSnapshot(qPayments, (pSnap) => {
          const payments = pSnap.docs.map(pDoc => {
            const pData = pDoc.data();
            let pDate = pData.date;
            if (typeof pDate === 'string') {
              pDate = { toMillis: () => Date.parse(pDate), toDate: () => new Date(pDate) };
            }
            return {
              id: pDoc.id,
              ...pData,
              date: pDate
            } as LoanPayment;
          });
          paymentsMap.value.set(loan.id, payments);
        });
        unsubscribes.value.push(unsubP);
      });

      loading.value = false;
    });
    unsubscribes.value.push(unsubL);
  });
};

onMounted(() => {
  setupSubscriptions();
});

const loansGroupsIds = computed(() => {
  return loansGroups.value.map(g => g.id).join(',');
});

watch(loansGroupsIds, (newVal, oldVal) => {
  if (newVal !== oldVal) {
    setupSubscriptions();
  }
});

onUnmounted(() => {
  unsubscribes.value.forEach(unsub => unsub());
});

// Dynamic calculations (converted to local user currency)
const loanStats = computed(() => {
  const dCurrency = props.user?.defaultCurrency || 'USD';
  let totalGivenPrincipal = 0;
  let totalGivenRepaid = 0;
  let totalTakenPrincipal = 0;
  let totalTakenRepaid = 0;
  let totalReceivables = 0;
  let totalPayables = 0;

  loans.value.forEach(loan => {
    const principalConverted = convertCurrency(loan.amount, loan.currencyCode || 'USD', dCurrency);
    const payments = paymentsMap.value.get(loan.id) || [];
    let repaidLocal = 0;
    
    payments.forEach(p => {
      repaidLocal += p.amount; // repayment amount matches loan currency code
    });

    const repaidConverted = convertCurrency(repaidLocal, loan.currencyCode || 'USD', dCurrency);

    if (loan.type === 'given') {
      totalGivenPrincipal += principalConverted;
      totalGivenRepaid += repaidConverted;
      if (loan.status !== 'settled') {
        totalReceivables += Math.max(principalConverted - repaidConverted, 0);
      }
    } else {
      totalTakenPrincipal += principalConverted;
      totalTakenRepaid += repaidConverted;
      if (loan.status !== 'settled') {
        totalPayables += Math.max(principalConverted - repaidConverted, 0);
      }
    }
  });

  const netBalance = totalReceivables - totalPayables;

  return {
    receivables: totalReceivables,
    payables: totalPayables,
    net: netBalance,
    givenPrincipal: totalGivenPrincipal,
    givenRepaid: totalGivenRepaid,
    takenPrincipal: totalTakenPrincipal,
    takenRepaid: totalTakenRepaid
  };
});

// Individual Loan Statistics Helpers
const getLoanRepaidPercentage = (loan: Loan) => {
  if (loan.status === 'settled') return 100;
  const payments = paymentsMap.value.get(loan.id) || [];
  const repaid = payments.reduce((sum, p) => sum + p.amount, 0);
  if (loan.amount <= 0) return 100;
  return Math.min(Math.round((repaid / loan.amount) * 100), 100);
};

const getLoanOutstanding = (loan: Loan) => {
  if (loan.status === 'settled') return 0;
  const payments = paymentsMap.value.get(loan.id) || [];
  const repaid = payments.reduce((sum, p) => sum + p.amount, 0);
  return Math.max(loan.amount - repaid, 0);
};

// Filtered Loans
const filteredLoans = computed(() => {
  let list = loans.value;

  if (activeTab.value === 'given') {
    list = list.filter(l => l.type === 'given' && l.status === 'active');
  } else if (activeTab.value === 'taken') {
    list = list.filter(l => l.type === 'taken' && l.status === 'active');
  } else if (activeTab.value === 'settled') {
    list = list.filter(l => l.status === 'settled');
  } else {
    // Show all active loans by default
    list = list.filter(l => l.status === 'active');
  }

  if (searchQuery.value.trim() !== '') {
    const q = searchQuery.value.toLowerCase().trim();
    list = list.filter(l => 
      l.personName.toLowerCase().includes(q) || 
      (l.description && l.description.toLowerCase().includes(q))
    );
  }

  return list;
});

// Form Handlers
const openNewLoanForm = () => {
  if (loansGroups.value.length === 0) {
    alert("Please create a Loan Tracker Group first using the '+' button in the sidebar!");
    return;
  }
  newLoanGroupId.value = loansGroups.value[0].id;
  newLoanCurrency.value = props.user?.defaultCurrency || 'USD';
  newLoanPerson.value = '';
  newLoanAmount.value = '';
  newLoanInterest.value = '0';
  newLoanDate.value = new Date().toISOString().split('T')[0];
  newLoanDueDate.value = '';
  newLoanDesc.value = '';
  isCreateLoanOpen.value = true;
};

const handleCreateLoan = async () => {
  if (!newLoanGroupId.value || !newLoanPerson.value.trim() || !newLoanAmount.value) return;

  try {
    const amt = parseFloat(newLoanAmount.value) || 0;
    if (amt <= 0) return;

    const loanId = crypto.randomUUID();
    const loanData: Loan = {
      id: loanId,
      groupId: newLoanGroupId.value,
      type: newLoanType.value,
      personName: newLoanPerson.value.trim(),
      amount: amt,
      interestRate: parseFloat(newLoanInterest.value) || 0,
      currencyCode: newLoanCurrency.value,
      date: Timestamp.fromDate(new Date(newLoanDate.value)),
      status: 'active',
      description: newLoanDesc.value.trim() || undefined,
      createdAt: Timestamp.now(),
      createdBy: props.user.uid
    };

    if (newLoanDueDate.value) {
      loanData.dueDate = Timestamp.fromDate(new Date(newLoanDueDate.value));
    }

    await setDoc(doc(db, 'groups', newLoanGroupId.value, 'loans_debts', loanId), loanData);
    isCreateLoanOpen.value = false;
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

    // 1. If linked account selected, debit or credit bank card balance
    if (payLinkedAccountId.value) {
      const bankAccount = accountsList.value.find(acc => acc.id === payLinkedAccountId.value);
      if (bankAccount) {
        txnId = crypto.randomUUID();
        
        // Define transaction direction:
        // Case A: Loan Taken repaid => We pay money out => Expense (-amt) in our bank balance
        // Case B: Loan Given repaid => We receive money back => Deposit (+amt) in our bank balance
        const isExpense = loan.type === 'taken'; 
        const linkAmt = isExpense ? -amt : amt;

        // Save ledger transaction under bank card
        const txPayload = {
          id: txnId,
          groupId: bankAccount.id,
          accountId: bankAccount.id,
          amount: linkAmt,
          description: isExpense ? `Loan Repay payload: To ${loan.personName}` : `Loan Recovery: From ${loan.personName}`,
          category: isExpense ? 'Card Payment' : 'Salary & Deposit',
          date: Timestamp.fromDate(new Date(payDate.value)),
          createdAt: Timestamp.now(),
          note: `Auto-linked from Loan Tracker repayment: ${payNote.value.trim() || 'No notes'}`.substring(0, 100),
          type: isExpense ? 'expense' : 'deposit'
        };

        await setDoc(doc(db, 'groups', bankAccount.id, 'account_transactions', txnId), txPayload);

        // Update target account's physical balance in groups table immediately
        let newBal = parseFloat(bankAccount.balance as any || 0);
        if (bankAccount.accountType === 'credit_card') {
          newBal = newBal - linkAmt; // paying card reduces liabilities, debiting links charges
        } else {
          newBal = newBal + linkAmt; // regular adjustment
        }
        await updateDoc(doc(db, 'groups', bankAccount.id), { balance: newBal });
      }
    }

    // 2. Commit loan installment payment record
    const payPayload = {
      id: paymentId,
      groupId: loan.groupId,
      loanId: loan.id,
      amount: amt,
      date: Timestamp.fromDate(new Date(payDate.value)),
      createdAt: Timestamp.now(),
      note: payNote.value.trim() || undefined,
      linkedAccountId: payLinkedAccountId.value || undefined,
      linkedTransactionId: txnId || undefined
    };

    await setDoc(doc(db, 'groups', loan.groupId, 'loans_debts', loan.id, 'loan_payments', paymentId), payPayload);

    // 3. Mark the loan as settled if it's fully paid
    const outstanding = getLoanOutstanding(loan) - amt;
    if (outstanding <= 0.01) {
      await updateDoc(doc(db, 'groups', loan.groupId, 'loans_debts', loan.id), { status: 'settled' });
    }

    isAddPaymentOpen.value = false;
    activeSelectedLoan.value = null;
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'loan_payments');
  }
};

const handleDeleteLoan = async (loan: Loan) => {
  if (!confirm(`Are you sure you want to delete this loan record with "${loan.personName}"? This will clear all repayments record too.`)) return;

  try {
    // Delete payments first
    const payments = paymentsMap.value.get(loan.id) || [];
    for (const p of payments) {
      await deleteDoc(doc(db, 'groups', loan.groupId, 'loans_debts', loan.id, 'loan_payments', p.id));
    }
    // Delete main loan
    await deleteDoc(doc(db, 'groups', loan.groupId, 'loans_debts', loan.id));
  } catch (error) {
    handleFirestoreError(error, OperationType.DELETE, 'loans_debts');
  }
};

const handleSettleMutually = async (loan: Loan) => {
  const remaining = getLoanOutstanding(loan);
  if (!confirm(`Are you sure you want to mutually settle this loan with "${loan.personName}"? Outstanding balance of ${formatCurrency(remaining, loan.currencyCode)} will be forgiven/waived and excluded from statistics.`)) return;

  try {
    await updateDoc(doc(db, 'groups', loan.groupId, 'loans_debts', loan.id), {
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
    await updateDoc(doc(db, 'groups', loan.groupId, 'loans_debts', loan.id), {
      status: 'active',
      mutuallySettled: false
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, 'loans_debts');
  }
};

const triggerCreateLedger = () => {
  if (typeof window !== 'undefined' && (window as any).openCreateGroupModal) {
    (window as any).openCreateGroupModal();
  }
};
</script>

<template>
  <div class="loans-hub" id="loans-hub-root">
    
    <!-- Top Display Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-10" id="loans-header-panel">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-zinc-950 dark:text-white font-display mb-2">
          Loans & Debts Hub
        </h1>
        <p class="text-zinc-500 dark:text-zinc-400 text-sm max-w-xl">
          Polished tracker for borrowed and lent assets. Oversee receivables, repayments, card allocations, and credit liabilities.
        </p>
      </div>

      <div class="flex items-center gap-3 shrink-0">
        <button 
          @click="openNewLoanForm" 
          class="flex items-center gap-2 px-6 py-3.5 bg-indigo-600 hover:bg-indigo-700 dark:bg-teal-500 dark:hover:bg-teal-600 text-white dark:text-zinc-900 rounded-xl font-bold tracking-tight shadow-lg shadow-indigo-500/10 cursor-pointer active:scale-95 transition-all text-sm"
        >
          <Plus class="w-4 h-4" />
          Initialize Loan / Debt
        </button>
      </div>
    </div>

    <!-- Quick Setup Widget if no loan trackers configured yet -->
    <div v-if="loansGroups.length === 0" class="p-8 border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-[#0d141e]/50 rounded-[32px] text-center mb-10 max-w-xl mx-auto shadow-sm">
      <div class="w-14 h-14 bg-amber-50 dark:bg-amber-500/15 text-amber-600 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-amber-100 dark:border-amber-500/20">
        <AlertCircle class="w-7 h-7" />
      </div>
      <h2 class="text-lg font-bold tracking-tight text-zinc-900 dark:text-white mb-2 font-display">Create a Loan Ledger</h2>
      <p class="text-zinc-500 dark:text-zinc-400 text-xs mb-8 leading-relaxed">
        Let's create a Loan Ledger group first! Press the <span class="font-bold text-zinc-850 dark:text-zinc-150 font-display">+</span> button in the sidebar under "Finance Services" to launch your loan ledger setup.
      </p>
      <button 
        @click="triggerCreateLedger" 
        class="inline-flex py-3.5 px-6 bg-zinc-900 dark:bg-white text-white dark:text-zinc-950 rounded-xl text-xs font-bold font-display cursor-pointer"
      >
        Open Creation Modal
      </button>
    </div>

    <template v-else>
      <!-- Highlights Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10" id="loans-stats-grid">
        
        <!-- Receivables Block -->
        <div class="p-6 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[28px] relative overflow-hidden group shadow-sm">
          <div class="absolute -right-6 -bottom-6 w-24 h-24 bg-emerald-500/5 rounded-full blur-xl group-hover:bg-emerald-500/10 transition-all duration-500" />
          <div class="flex items-center gap-4 mb-4">
            <div class="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-500/10 flex items-center justify-center text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-500/20">
              <TrendingUp class="w-6 h-6" />
            </div>
            <div>
              <p class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.150em]">Lent by Me (Receivables)</p>
              <h4 class="text-2xl font-black font-mono tracking-tight text-zinc-900 dark:text-zinc-100 mt-0.5">
                {{ formatCurrency(loanStats.receivables, user?.defaultCurrency || 'USD') }}
              </h4>
            </div>
          </div>
          <div class="pt-3 border-t border-zinc-100 dark:border-white/5 flex items-center justify-between text-[11px] text-zinc-400">
            <span>Principal: {{ formatCurrency(loanStats.givenPrincipal, user?.defaultCurrency || 'USD') }}</span>
            <span>Repaid: {{ loanStats.givenPrincipal > 0 ? Math.min(Math.round((loanStats.givenRepaid / loanStats.givenPrincipal) * 100), 100) : 100 }}%</span>
          </div>
        </div>

        <!-- Payables Block -->
        <div class="p-6 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[28px] relative overflow-hidden group shadow-sm">
          <div class="absolute -right-6 -bottom-6 w-24 h-24 bg-rose-500/5 rounded-full blur-xl group-hover:bg-rose-500/10 transition-all duration-500" />
          <div class="flex items-center gap-4 mb-4">
            <div class="w-12 h-12 rounded-xl bg-rose-50 dark:bg-rose-500/10 flex items-center justify-center text-rose-600 dark:text-rose-400 border border-rose-100 dark:border-rose-500/20">
              <TrendingDown class="w-6 h-6" />
            </div>
            <div>
              <p class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.150em]">Borrowed by Me (Payables)</p>
              <h4 class="text-2xl font-black font-mono tracking-tight text-zinc-900 dark:text-zinc-100 mt-0.5">
                {{ formatCurrency(loanStats.payables, user?.defaultCurrency || 'USD') }}
              </h4>
            </div>
          </div>
          <div class="pt-3 border-t border-zinc-100 dark:border-white/5 flex items-center justify-between text-[11px] text-zinc-400">
            <span>Principal: {{ formatCurrency(loanStats.takenPrincipal, user?.defaultCurrency || 'USD') }}</span>
            <span>Repaid: {{ loanStats.takenPrincipal > 0 ? Math.min(Math.round((loanStats.takenRepaid / loanStats.takenPrincipal) * 100), 100) : 100 }}%</span>
          </div>
        </div>

        <!-- Net Position Block -->
        <div class="p-6 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[28px] relative overflow-hidden group shadow-sm">
          <div class="absolute -right-6 -bottom-6 w-24 h-24 bg-indigo-500/5 rounded-full blur-xl group-hover:bg-indigo-500/10 transition-all duration-500" />
          <div class="flex items-center gap-4 mb-4">
            <div class="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-500/20">
              <Scale class="w-6 h-6" />
            </div>
            <div>
              <p class="text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-[0.150em]">Net Debt balance</p>
              <h4 class="text-2xl font-black font-mono tracking-tight mt-0.5" :class="loanStats.net >= 0 ? 'text-emerald-500' : 'text-rose-500'">
                {{ loanStats.net >= 0 ? '+' : '' }}{{ formatCurrency(loanStats.net, user?.defaultCurrency || 'USD') }}
              </h4>
            </div>
          </div>
          <div class="pt-3 border-t border-zinc-100 dark:border-white/5 flex items-center justify-between text-[11px] text-zinc-400">
            <span>Aggregated Outstanding Risk</span>
            <span class="font-bold" :class="loanStats.net >= 0 ? 'text-emerald-600' : 'text-rose-600'">
              {{ loanStats.net >= 0 ? 'Surplus' : 'Deficit' }}
            </span>
          </div>
        </div>

      </div>

      <!-- Controls Tab Panel -->
      <div class="bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-3xl p-6 shadow-sm mb-8">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div class="flex items-center gap-1.5 bg-zinc-50 dark:bg-white/5 p-1 rounded-xl">
            <button 
              @click="activeTab = 'all'" 
              :class="`px-5 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${activeTab === 'all' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'}`"
            >
              All Active
            </button>
            <button 
              @click="activeTab = 'given'" 
              :class="`px-5 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${activeTab === 'given' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'}`"
            >
              Lent by Me
            </button>
            <button 
              @click="activeTab = 'taken'" 
              :class="`px-5 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${activeTab === 'taken' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'}`"
            >
              Borrowed by Me
            </button>
            <button 
              @click="activeTab = 'settled'" 
              :class="`px-5 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${activeTab === 'settled' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-white'}`"
            >
              Settled / Paid
            </button>
          </div>

          <!-- Dynamic Search Input -->
          <div class="relative w-full sm:w-64">
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="Search debtor / creditor..." 
              class="w-full px-4 py-2.5 pl-9 bg-zinc-50 dark:bg-white/5 border border-zinc-200 dark:border-white/10 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 text-xs font-medium text-zinc-800 dark:text-zinc-200 placeholder:text-zinc-400"
            />
            <div class="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400">
              <Scale class="w-4 h-4" />
            </div>
          </div>
        </div>
      </div>

      <!-- Main Ledger List Grid -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
      </div>

      <div v-else-if="filteredLoans.length === 0" class="py-20 text-center text-zinc-400 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[32px] shadow-sm">
        <Scale class="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-650 mb-4 animate-bounce-slow" />
        <h3 class="font-bold text-zinc-950 dark:text-white tracking-tight mb-1 mb-2 font-display">No active loans found</h3>
        <p class="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
          Nothing matches this selection criteria. Introduce a loan or record a debt transaction above.
        </p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6" id="loans-ledger-grid">
        <div 
          v-for="loan in filteredLoans" 
          :key="loan.id" 
          class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative flex flex-col justify-between group hover:border-[#005a5b] dark:hover:border-teal-500/40 transition-all duration-300 shadow-sm"
        >
          <div>
            <!-- Heading -->
            <div class="flex items-start justify-between gap-4 mb-4">
              <div class="flex items-center gap-3">
                <div :class="`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border ${
                  loan.type === 'given' 
                    ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-100 dark:border-emerald-500/20 text-emerald-600' 
                    : 'bg-rose-50 dark:bg-rose-500/10 border-rose-100 dark:border-rose-500/20 text-rose-600'
                }`">
                  <User class="w-5 h-5" />
                </div>
                <div>
                  <h4 class="font-extrabold text-zinc-950 dark:text-white tracking-tight text-sm leading-tight leading-none mb-1">
                    {{ loan.personName }}
                  </h4>
                  <span :class="`px-2.5 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wider leading-none select-none ${
                    loan.type === 'given' 
                      ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600' 
                      : 'bg-rose-50 dark:bg-rose-500/10 text-rose-600'
                  }`">
                    {{ loan.type === 'given' ? 'Lent out (Receivable)' : 'Borrowed (Payable)' }}
                  </span>
                </div>
              </div>

              <div class="text-right">
                <p class="text-xs text-zinc-400 font-medium">Principal</p>
                <p class="text-base font-black font-mono tracking-tight text-zinc-900 dark:text-zinc-200">
                  {{ formatCurrency(loan.amount, loan.currencyCode) }}
                </p>
              </div>
            </div>

            <!-- Description -->
            <p v-if="loan.description" class="text-xs text-zinc-500 dark:text-zinc-400 italic bg-zinc-50 dark:bg-white/5 p-3 rounded-xl mb-4 leading-relaxed line-clamp-2">
              "{{ loan.description }}"
            </p>

            <!-- Remaining repays progress scale -->
            <div class="mb-5 bg-zinc-50 dark:bg-[#121c27] p-4 rounded-2xl border border-zinc-100 dark:border-white/5">
              <div class="flex items-center justify-between text-xs mb-2">
                <span class="text-zinc-400 font-medium">Outstanding Balance</span>
                <span class="font-bold tracking-tight text-zinc-900 dark:text-zinc-200">
                  {{ formatCurrency(getLoanOutstanding(loan), loan.currencyCode) }}
                </span>
              </div>
              <div class="w-full h-2 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                <div 
                  :class="`h-full transition-all duration-500 rounded-full ${
                    loan.type === 'given' ? 'bg-emerald-500' : 'bg-indigo-500'
                  }`" 
                  :style="`width: ${getLoanRepaidPercentage(loan)}%`"
                />
              </div>
              <div class="flex items-center justify-between text-[10px] text-zinc-400 mt-2 font-mono">
                <span>{{ getLoanRepaidPercentage(loan) }}% Repaid</span>
                <span v-if="loan.dueDate" class="flex items-center gap-1">
                  <Calendar class="w-3" />
                  Due: {{ loan.dueDate.toDate().toLocaleDateString() }}
                </span>
                <span v-else>No due date</span>
              </div>
            </div>
          </div>

          <!-- Actions Footer -->
          <div class="flex items-center justify-between pt-4 border-t border-zinc-100 dark:border-white/5 mt-2">
            <span class="text-[10px] text-zinc-400 font-mono">
              Launched: {{ loan.date.toDate().toLocaleDateString() }}
            </span>

            <div class="flex items-center gap-2">
              <button 
                @click.stop="handleDeleteLoan(loan)" 
                class="p-2 rounded-lg text-zinc-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors border-none bg-transparent cursor-pointer"
                title="Deconstruct Record"
              >
                <Trash2 class="w-4 h-4" />
              </button>
              <button 
                v-if="loan.status !== 'settled'"
                @click.stop="openPaymentForm(loan)" 
                class="px-4 py-2 bg-zinc-100 hover:bg-zinc-200 dark:bg-white/5 dark:hover:bg-white/10 text-zinc-900 dark:text-white rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <ArrowRightLeft class="w-3.5 h-3.5 text-teal-500" />
                Repay Installment
              </button>
              <button 
                v-if="loan.status !== 'settled'"
                @click.stop="handleSettleMutually(loan)" 
                class="px-3 py-2 bg-amber-500 hover:bg-amber-600 text-zinc-950 rounded-lg text-xs font-bold transition-colors cursor-pointer"
              >
                Settle Mutually
              </button>
              <div v-else class="flex items-center gap-2">
                <span 
                  class="text-emerald-500 text-xs font-extrabold uppercase tracking-wider flex items-center gap-1.5"
                >
                  <CheckCircle2 class="w-4 h-4 text-emerald-500" />
                  Fully Settled
                </span>
                <button 
                  @click.stop="handleReactivateLoan(loan)"
                  class="px-2 py-1 border border-zinc-200 dark:border-white/10 text-zinc-500 dark:text-zinc-400 font-bold text-[10px] rounded hover:bg-zinc-100 dark:hover:bg-zinc-900 transition-colors cursor-pointer"
                >
                  Undo
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Create Loan Modal Overlay -->
    <transition name="fade">
      <div v-if="isCreateLoanOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isCreateLoanOpen = false" class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm" />
        <div class="relative w-full max-w-lg bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-[32px] p-8 shadow-2xl z-10 animate-in overflow-y-auto max-h-[90vh]">
          
          <div class="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-white/5 mb-6">
            <h3 class="text-xl font-bold tracking-tight text-zinc-950 dark:text-white font-display">Initialize Loan / Debt</h3>
            <button @click="isCreateLoanOpen = false" class="p-2 text-zinc-400 hover:text-zinc-900 dark:hover:text-white cursor-pointer rounded-lg bg-transparent border-none">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleCreateLoan" class="space-y-5 text-left">
            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Select Tracker Ledger</label>
              <select 
                v-model="newLoanGroupId"
                class="w-full px-4 py-3.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-xl block focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold text-zinc-850 dark:text-zinc-150"
              >
                <option v-for="g in loansGroups" :key="g.id" :value="g.id">{{ g.name }}</option>
              </select>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Record Classification</label>
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
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Debtor / Creditor Person</label>
                <input 
                  v-model="newLoanPerson" 
                  type="text" 
                  placeholder="e.g. Rachel, Bank, Family" 
                  required
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold text-zinc-850"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Amount</label>
                <input 
                  v-model="newLoanAmount" 
                  type="number" 
                  step="any" 
                  placeholder="0.00" 
                  required
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold text-zinc-850"
                />
              </div>
            </div>

            <div class="grid grid-cols-3 gap-4">
              <div class="col-span-2">
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Simple Flat Interest Rate %</label>
                <input 
                  v-model="newLoanInterest" 
                  type="number" 
                  step="0.1" 
                  placeholder="0" 
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold text-zinc-850"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Currency</label>
                <select 
                  v-model="newLoanCurrency"
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold text-zinc-850"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Date Logged</label>
                <input 
                  v-model="newLoanDate" 
                  type="date" 
                  required
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none text-xs font-semibold"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Repayment Due Date (Optional)</label>
                <input 
                  v-model="newLoanDueDate" 
                  type="date" 
                  class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none text-xs font-semibold"
                />
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Description / Notes</label>
              <textarea 
                v-model="newLoanDesc" 
                placeholder="Details of context, simple payment schedule, or agreement note..." 
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none h-20 text-xs font-medium resize-none"
              />
            </div>

            <button 
              type="submit" 
              class="w-full py-4 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 text-xs font-bold rounded-xl mt-4 hover:bg-zinc-900 dark:hover:bg-zinc-100 transition-colors shadow-lg cursor-pointer"
            >
              Verify & Save Loan
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Record Payment Modal Overlay -->
    <transition name="fade">
      <div v-if="isAddPaymentOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div @click="isAddPaymentOpen = false" class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm" />
        <div class="relative w-full max-w-md bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-[32px] p-8 shadow-2xl z-10 animate-in">
          
          <div class="flex items-center justify-between pb-4 border-b border-zinc-100 dark:border-white/5 mb-6">
            <h3 class="text-xl font-bold tracking-tight text-zinc-950 dark:text-white font-display">Installment Repayment</h3>
            <button @click="isAddPaymentOpen = false" class="p-2 text-zinc-400 hover:text-zinc-900 dark:hover:text-white cursor-pointer rounded-lg bg-transparent border-none">
              <X class="w-5 h-5" />
            </button>
          </div>

          <form @submit.prevent="handleRecordPayment" class="space-y-4 text-left">
            <div>
              <p class="text-xs text-zinc-500 mb-2 font-semibold">Active Loan Account: <span class="text-zinc-900 dark:text-zinc-300 font-bold">{{ activeSelectedLoan?.personName }}</span></p>
              <p class="text-xs text-zinc-500 font-semibold">Outstanding Remaining: <span class="text-[#005a5b] dark:text-teal-400 font-bold font-mono">{{ formatCurrency(getLoanOutstanding(activeSelectedLoan!), activeSelectedLoan?.currencyCode) }}</span></p>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Payment Amount ({{ activeSelectedLoan?.currencyCode }})</label>
              <input 
                v-model="payAmount" 
                type="number" 
                step="any" 
                required
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 text-xs font-semibold"
              />
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Repayment Date</label>
              <input 
                v-model="payDate" 
                type="date" 
                required
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none text-xs font-semibold"
              />
            </div>

            <div>
              <div class="flex items-center justify-between mb-3 leading-none">
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] font-display">Link Bank Account/Card (Auto-Deduct)</label>
                <span class="text-[9px] text-[#005253] dark:text-teal-400 font-bold font-mono">Optional</span>
              </div>
              <select 
                v-model="payLinkedAccountId"
                class="w-full px-4 py-3.5 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-805 rounded-block focus:outline-none rounded-xl text-xs font-semibold"
              >
                <option value="">-- No Account Deduction (Manual Entry) --</option>
                <option v-for="acc in accountsList" :key="acc.id" :value="acc.id">
                  {{ acc.name }} ({{ formatCurrency(acc.balance || 0, acc.currencyCode) }})
                </option>
              </select>
              <p class="text-[10px] text-zinc-400 mt-2 leading-tight">
                Highly Recommended: When linked, this repayment automatically records a deposit/payment transaction on that card/account, decrementing checking when paying off a borrowing, or incrementing when recovering loans!
              </p>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Notes</label>
              <input 
                v-model="payNote" 
                type="text" 
                placeholder="e.g. Third installment, partial payload, settlement" 
                class="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none text-xs"
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

  </div>
</template>

<style scoped>
.bounce-slow {
  animation: bounce 3s infinite;
}
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
</style>
