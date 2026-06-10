<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { db } from '../firebase';
import { calculateAmortizationSchedule } from '../services/dataService';
import { 
  collection, 
  doc, 
  setDoc,
  deleteDoc, 
  onSnapshot, 
  query, 
  orderBy, 
  Timestamp, 
  getDoc,
  serverTimestamp,
  updateDoc
} from 'firebase/firestore';
import { 
  ArrowLeft, 
  Plus, 
  Home, 
  Trash, 
  CheckCircle, 
  Calendar, 
  Percent, 
  ShieldCheck, 
  Scale, 
  User, 
  Sparkles,
  Info
} from 'lucide-vue-next';
import { type Group, type Mortgage, type MortgagePayment } from '../types';
import { formatCurrency } from '../utils/format';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

const loading = ref(true);
const group = ref<Group | null>(null);
const mortgages = ref<Mortgage[]>([]);
const paymentsMap = ref<Map<string, MortgagePayment[]>>(new Map());
const accountsList = ref<Group[]>([]);

const activeSelectedMortgage = ref<Mortgage | null>(null);

// Forms state
const isCreateMortgageOpen = ref(false);
const isAddPaymentOpen = ref(false);

// New Mortgage form
const newMortgageProperty = ref('');
const newMortgagePerson = ref('');
const newMortgageType = ref<'given' | 'taken'>('taken');
const newMortgageAmount = ref('');
const newCollateralValue = ref('');
const newDownPayment = ref('');
const newAmortizationYears = ref('30');
const newMortgageInterest = ref('4.5');
const newMortgageDate = ref(new Date().toISOString().split('T')[0]);
const newMortgageDueDate = ref('');
const newMortgageDesc = ref('');

// Payment form
const payAmount = ref('');
const payDate = ref(new Date().toISOString().split('T')[0]);
const payNote = ref('');
const payLinkedAccountId = ref('');

// Filter state
const activeFilter = ref<'all' | 'given' | 'taken'>('all');
const expandedAmortizationId = ref<string | null>(null);

onMounted(async () => {
  try {
    // 1. Fetch group metadata
    const gDoc = await getDoc(doc(db, 'groups', props.groupId));
    if (gDoc.exists()) {
      group.value = { id: gDoc.id, ...gDoc.data() } as Group;
    }

    // 2. Fetch Accounts
    onSnapshot(collection(db, 'groups'), (snap) => {
      accountsList.value = snap.docs
        .map(doc => ({ id: doc.id, ...doc.data() } as Group))
        .filter(g => g.service === 'accounts');
    });

    // 3. Listen to Mortgages subcollection
    const mQuery = query(collection(db, 'groups', props.groupId, 'mortgages'), orderBy('createdAt', 'desc'));
    onSnapshot(mQuery, (snapshot) => {
      mortgages.value = snapshot.docs.map(d => ({
        id: d.id,
        ...d.data()
      } as Mortgage));

      // Fetch payment lists for all mortgages
      mortgages.value.forEach(m => {
        const pQuery = query(
          collection(db, 'groups', props.groupId, 'mortgages', m.id, 'mortgage_payments'), 
          orderBy('date', 'desc')
        );
        onSnapshot(pQuery, (pSnap) => {
          const list = pSnap.docs.map(pd => ({
            id: pd.id,
            ...pd.data()
          } as MortgagePayment));
          paymentsMap.value.set(m.id, list);
        });
      });

      loading.value = false;
    });

  } catch (error) {
    console.error("Error setting up mortgages stream listener:", error);
    loading.value = false;
  }
});

// Calculations helper
const getMortgageRepaidAmount = (m: Mortgage) => {
  const ps = paymentsMap.value.get(m.id) || [];
  return ps.reduce((sum, p) => sum + p.amount, 0);
};

// Outstanding counts & pending during settle shouldn't be used in calculation
const getMortgageOutstanding = (m: Mortgage) => {
  if (m.status === 'settled') return 0;
  const repaid = getMortgageRepaidAmount(m);
  return Math.max(m.amount - repaid, 0);
};

// Computed Stats of the current ledger group
const totalLentClaim = computed(() => {
  return mortgages.value
    .filter(m => m.type === 'given' && m.status !== 'settled')
    .reduce((s, m) => s + m.amount, 0);
});

const totalBorrowedDebt = computed(() => {
  return mortgages.value
    .filter(m => m.type === 'taken' && m.status !== 'settled')
    .reduce((s, m) => s + m.amount, 0);
});

const activeLTV = computed(() => {
  const activeWithCollateral = mortgages.value.filter(m => m.status !== 'settled' && m.collateralValue);
  if (activeWithCollateral.length === 0) return 0;
  const sumOutstanding = activeWithCollateral.reduce((s, m) => s + getMortgageOutstanding(m), 0);
  const sumCollateral = activeWithCollateral.reduce((s, m) => s + (m.collateralValue || 0), 0);
  return sumCollateral > 0 ? Math.round((sumOutstanding / sumCollateral) * 100) : 0;
});

const activeFilterLabel = computed(() => {
  if (activeFilter.value === 'given') return 'Lent Out collateral claims';
  if (activeFilter.value === 'taken') return 'Borrowed property mortgages';
  return 'All active mortgages';
});

const filteredMortgages = computed(() => {
  if (activeFilter.value === 'given') {
    return mortgages.value.filter(m => m.type === 'given');
  }
  if (activeFilter.value === 'taken') {
    return mortgages.value.filter(m => m.type === 'taken');
  }
  return mortgages.value;
});

// Actions handlers
const handleCreateMortgage = async () => {
  if (!newMortgageProperty.value.trim() || !newMortgageAmount.value) return;

  try {
    const mortgageId = crypto.randomUUID();
    const amt = parseFloat(newMortgageAmount.value) || 0;
    const cValue = parseFloat(newCollateralValue.value) || amt; // fallback to loan amount if empty
    const dPay = parseFloat(newDownPayment.value) || 0;

    const payload: Mortgage = {
      id: mortgageId,
      groupId: props.groupId,
      type: newMortgageType.value,
      personName: newMortgagePerson.value.trim() || (newMortgageType.value === 'taken' ? 'Lender / Institution' : 'Borrower Partner'),
      propertyCollateralName: newMortgageProperty.value.trim(),
      amount: amt,
      collateralValue: cValue,
      downPayment: dPay,
      interestRate: parseFloat(newMortgageInterest.value) || 0,
      amortizationYears: parseInt(newAmortizationYears.value) || 30,
      currencyCode: group.value?.currencyCode || 'USD',
      date: Timestamp.fromDate(new Date(newMortgageDate.value)),
      status: 'active',
      description: newMortgageDesc.value.trim() || undefined,
      createdAt: Timestamp.now(),
      createdBy: props.user.uid
    };

    if (newMortgageDueDate.value) {
      payload.dueDate = Timestamp.fromDate(new Date(newMortgageDueDate.value));
    }

    await setDoc(doc(db, 'groups', props.groupId, 'mortgages', mortgageId), payload);
    isCreateMortgageOpen.value = false;

    // Reset fields
    newMortgageProperty.value = '';
    newMortgagePerson.value = '';
    newMortgageAmount.value = '';
    newCollateralValue.value = '';
    newDownPayment.value = '';
    newAmortizationYears.value = '30';
    newMortgageInterest.value = '4.5';
    newMortgageDate.value = new Date().toISOString().split('T')[0];
    newMortgageDueDate.value = '';
    newMortgageDesc.value = '';

  } catch (error) {
    console.error("Error creating property mortgage asset entry:", error);
  }
};

const handleRecordPayment = async () => {
  if (!activeSelectedMortgage.value || !payAmount.value) return;

  try {
    const m = activeSelectedMortgage.value;
    const pAmt = parseFloat(payAmount.value) || 0;
    if (pAmt <= 0) return;

    const paymentId = crypto.randomUUID();
    let txnId: string | undefined;

    // Link Bank Account / Card deduction
    if (payLinkedAccountId.value) {
      const bank = accountsList.value.find(acc => acc.id === payLinkedAccountId.value);
      if (bank) {
        txnId = crypto.randomUUID();
        const isExpense = m.type === 'taken';
        const linkAmt = isExpense ? -pAmt : pAmt;

        const txPayload = {
          id: txnId,
          groupId: bank.id,
          accountId: bank.id,
          amount: linkAmt,
          description: isExpense ? `Mortgage Paymnt: ${m.propertyCollateralName}` : `Mortgage Recovery: ${m.propertyCollateralName}`,
          category: isExpense ? 'Card Payment' : 'Salary & Deposit',
          date: Timestamp.fromDate(new Date(payDate.value)),
          createdAt: Timestamp.now(),
          note: `Auto-linked payment of mortgage on: ${m.propertyCollateralName}`,
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

    const pPayload: MortgagePayment = {
      id: paymentId,
      mortgageId: m.id,
      groupId: props.groupId,
      amount: pAmt,
      date: Timestamp.fromDate(new Date(payDate.value)),
      note: payNote.value.trim() || undefined,
      linkedAccountId: payLinkedAccountId.value || undefined,
      linkedTransactionId: txnId || undefined,
      createdAt: Timestamp.now(),
      createdBy: props.user.uid
    };

    await setDoc(doc(db, 'groups', props.groupId, 'mortgages', m.id, 'mortgage_payments', paymentId), pPayload);
    
    // Check if fully paid off, auto update status if so
    const currentRepaid = getMortgageRepaidAmount(m) + pAmt;
    if (currentRepaid >= m.amount) {
      await setDoc(doc(db, 'groups', props.groupId, 'mortgages', m.id), { status: 'settled' }, { merge: true });
    }

    isAddPaymentOpen.value = false;
    payAmount.value = '';
    payNote.value = '';
    payLinkedAccountId.value = '';

  } catch (error) {
    console.error("Error writing payment info: ", error);
  }
};

// Settle manually or mutually feature
// This option satisfies: "loan and lent can be settle without full payment, i mean manually or mutually. SO this option should have, and pending amount during settle should not used in calculation."
const handleMutualSettle = async (m: Mortgage) => {
  const confirmSettle = confirm("Are you sure you want to mutually or manually settle this mortgage? This voids any remaining unpaid balance out of outstanding totals.");
  if (!confirmSettle) return;

  try {
    await setDoc(doc(db, 'groups', props.groupId, 'mortgages', m.id), { status: 'settled' }, { merge: true });
    alert("Mortgage marked as mutually settled successfully.");
  } catch (error) {
    console.error("Error settling mortgage mutually:", error);
  }
};

const handleDeleteMortgage = async (m: Mortgage) => {
  const confirmDel = confirm("Are you sure you want to completely delete this mortgage ledger agreement? This action is irreversible.");
  if (!confirmDel) return;

  try {
    await deleteDoc(doc(db, 'groups', props.groupId, 'mortgages', m.id));
    alert("Mortgage deleted successfully.");
  } catch (error) {
    console.error("Error deleting mortgage:", error);
  }
};
</script>

<template>
  <div class="space-y-8" id="group-mortgages-view-container">
    <!-- Breadcrumb back link -->
    <button 
      @click="emit('back')"
      class="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-950 dark:hover:text-white text-xs font-black select-none cursor-pointer group"
    >
      <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
      Back to Broker Hub
    </button>

    <!-- Header Section card -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-5 bg-white dark:bg-[#0c141d]/70 p-8 border border-zinc-200 dark:border-white/10 rounded-[32px] shadow-sm text-left">
      <div>
        <div class="flex items-center gap-3 mb-2.5">
          <span class="px-3 py-1 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 text-[10px] uppercase font-black tracking-widest rounded-full">
            REAL PROPERTY BROKER
          </span>
          <span class="text-zinc-400 font-mono text-[11px] font-bold">
            Group Identifier: {{ group?.id }}
          </span>
        </div>
        <h2 class="text-3xl font-black text-zinc-950 dark:text-white tracking-tight font-display mb-1">
          {{ group?.name }}
        </h2>
        <p class="text-xs text-zinc-500 leading-relaxed max-w-2xl">
          {{ group?.description || 'Active long-term mortgage loan management and debt settlement console' }}
        </p>
      </div>

      <button 
        @click="isCreateMortgageOpen = true"
        class="px-5 py-4 bg-gradient-to-br from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-2xl font-bold text-xs transition-colors shadow-lg shadow-indigo-500/15 flex items-center justify-center gap-2 shrink-0 cursor-pointer"
      >
        <Plus class="w-4 h-4 shrink-0" />
        Record Secured Property / Collateral
      </button>
    </div>

    <!-- Active Mortgage Ledger Statistics Bar -->
    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-4 gap-5" id="group-mortgage-stats-bar">
      <!-- 1st element: Collaterals Active Claims -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Lent Collateral Claims</span>
        <span class="block text-xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
          {{ formatCurrency(totalLentClaim, group?.currencyCode || 'USD') }}
        </span>
      </div>

      <!-- 2nd element: Mortgages Taken liabilities -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Mortgages / Liabilities</span>
        <span class="block text-xl font-black text-rose-600 dark:text-rose-450 font-mono">
          {{ formatCurrency(totalBorrowedDebt, group?.currencyCode || 'USD') }}
        </span>
      </div>

      <!-- 3rd element: Weighted average LTV -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Average LTV % position</span>
        <span class="block text-xl font-black text-indigo-600 dark:text-indigo-400 font-mono">
          {{ activeLTV }}%
        </span>
      </div>

      <!-- 4th element: Ledger balance position -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Brokers Settlement Index</span>
        <span :class="`block text-lg font-black font-mono truncate ${
          (totalLentClaim - totalBorrowedDebt) >= 0 ? 'text-indigo-600 dark:text-indigo-400' : 'text-rose-600'
        }`">
          {{ formatCurrency(totalLentClaim - totalBorrowedDebt, group?.currencyCode || 'USD') }}
        </span>
      </div>
    </div>

    <!-- Main List of Mortgages -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
    </div>

    <div v-else class="space-y-4">
      <!-- Grid header tabs -->
      <div class="flex gap-2 p-1.5 bg-zinc-100 dark:bg-white/5 rounded-2xl w-fit select-none border border-zinc-200/50 dark:border-white/5">
        <button 
          @click="activeFilter = 'all'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'all' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          All ({{ mortgages.length }})
        </button>
        <button 
          @click="activeFilter = 'given'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'given' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          Lent Claims ({{ mortgages.filter(m => m.type === 'given').length }})
        </button>
        <button 
          @click="activeFilter = 'taken'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'taken' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          Borrowed Debt ({{ mortgages.filter(m => m.type === 'taken').length }})
        </button>
      </div>

      <div v-if="filteredMortgages.length === 0" class="py-20 text-center text-zinc-550 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[32px] shadow-sm">
        <Home class="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-750 mb-4" />
        <h3 class="font-bold text-zinc-950 dark:text-white tracking-tight mb-2 font-display">No matches found</h3>
        <p class="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
          No property entries match the filter criteria under this ledger. Click "Record Secured Property" above to record one.
        </p>
      </div>

      <div v-else class="space-y-4" id="group-mortgages-list-view">
        <div 
          v-for="m in filteredMortgages" 
          :key="m.id" 
          class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-205 dark:border-white/10 rounded-[28px] overflow-hidden shadow-sm"
        >
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            <!-- col-span-5: Details of property collateral and partner names -->
            <div class="lg:col-span-5 text-left space-y-4">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-2xl flex items-center justify-center bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 shrink-0">
                  <Home class="w-6 h-6" />
                </div>
                <div>
                  <h4 class="font-black text-zinc-950 dark:text-white tracking-tight leading-snug">
                    {{ m.propertyCollateralName }}
                  </h4>
                  <p class="text-[11px] text-zinc-400 font-medium flex items-center gap-1 mt-0.5">
                    <User class="w-3" />
                    <span>Partner: <strong>{{ m.personName }}</strong></span>
                  </p>
                </div>
              </div>

              <!-- General specs pill indicators index -->
              <div class="flex flex-wrap gap-2">
                <span :class="`px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider ${
                  m.type === 'given' 
                    ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600' 
                    : 'bg-rose-50 dark:bg-rose-500/10 text-rose-600'
                }`">
                  {{ m.type === 'given' ? 'Lent Collateral Lien / Claimant' : 'Mortgage Liability / Debtor' }}
                </span>
                <span v-if="m.status === 'settled'" class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider bg-zinc-150 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 flex items-center gap-1">
                  <CheckCircle class="w-3 h-3 text-zinc-500 dark:text-zinc-450" />
                  Settled (Clear)
                </span>
                <span v-else class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider bg-orange-50 dark:bg-orange-500/10 text-orange-600">
                  Active Amortization
                </span>
              </div>

              <!-- Details note memo -->
              <p v-if="m.description" class="text-xs text-zinc-500 dark:text-zinc-400 italic bg-zinc-50 dark:bg-white/5 p-3 rounded-xl mt-3 leading-relaxed">
                "{{ m.description }}"
              </p>
            </div>

            <!-- col-span-3: Collateral value and principal terms details -->
            <div class="lg:col-span-3 text-left space-y-2.5">
              <h5 class="text-[9px] font-black text-indigo-500 uppercase tracking-widest block font-display">Secured Asset Value Index</h5>
              <div class="space-y-1.5 text-xs">
                <div class="flex justify-between items-center text-zinc-505">
                  <span>Collateral value:</span>
                  <span class="font-extrabold text-zinc-950 dark:text-white font-mono">
                    {{ formatCurrency(m.collateralValue || m.amount, m.currencyCode) }}
                  </span>
                </div>
                <div class="flex justify-between items-center text-zinc-505">
                  <span>Principal Loan sum:</span>
                  <span class="font-extrabold text-zinc-950 dark:text-white font-mono">
                    {{ formatCurrency(m.amount, m.currencyCode) }}
                  </span>
                </div>
                <div class="flex justify-between items-center text-zinc-505">
                  <span>Down Payment paid:</span>
                  <span class="font-bold text-teal-600 font-mono">
                    {{ formatCurrency(m.downPayment || 0, m.currencyCode) }}
                  </span>
                </div>
                <div v-if="m.interestRate" class="flex justify-between items-center text-zinc-505">
                  <span>Annual interest rate:</span>
                  <span class="font-bold text-indigo-600 font-mono flex items-center gap-0.5">
                    <Percent class="w-2.5 h-2.5" /> {{ m.interestRate }}%
                  </span>
                </div>
                <div v-if="m.amortizationYears" class="flex justify-between items-center text-zinc-505 pt-1.5 border-t border-zinc-100 dark:border-white/5">
                  <span>Amortization Term:</span>
                  <span class="font-bold text-zinc-800 dark:text-zinc-300">
                    {{ m.amortizationYears }} Years
                  </span>
                </div>
              </div>
            </div>

            <!-- col-span-4: Balance summary counters and Actions -->
            <div class="lg:col-span-4 text-left flex flex-col justify-between h-full space-y-4">
              <div class="bg-zinc-50 dark:bg-[#121c27] p-4 rounded-2xl border border-zinc-100 dark:border-white/5">
                <div class="flex justify-between items-center text-xs mb-1.5">
                  <span class="text-zinc-400 font-bold">Outstanding Balance:</span>
                  <span :class="`font-black font-mono text-sm ${m.status === 'settled' ? 'line-through text-zinc-400' : 'text-zinc-950 dark:text-white'}`">
                    {{ formatCurrency(getMortgageOutstanding(m), m.currencyCode) }}
                  </span>
                </div>

                <div class="w-full h-2 bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden mb-3">
                  <div 
                    class="h-full bg-indigo-500 rounded-full transition-all duration-300"
                    :style="{ width: `${m.status === 'settled' ? 100 : Math.min((getMortgageRepaidAmount(m) / m.amount) * 100, 100)}%` }"
                  />
                </div>

                <div class="flex items-center justify-between text-[11px] text-zinc-400">
                  <span>Paid Repaid total:</span>
                  <span class="font-black font-mono text-[#005a5b] dark:text-teal-400">
                    {{ formatCurrency(getMortgageRepaidAmount(m), m.currencyCode) }}
                  </span>
                </div>
              </div>

              <!-- Button Actions -->
              <div class="flex flex-wrap gap-2 pt-2">
                <button 
                  @click="handleDeleteMortgage(m)"
                  class="p-2 border border-rose-500/10 hover:bg-rose-500/15 text-rose-500 rounded-xl transition-all cursor-pointer"
                  title="Delete Agreement"
                >
                  <Trash class="w-4 h-4" />
                </button>

                <button 
                  v-if="m.status !== 'settled'"
                  @click="handleMutualSettle(m)"
                  class="px-3 py-2 bg-amber-50 dark:bg-amber-500/15 text-amber-700 dark:text-amber-400 hover:bg-amber-100 border border-amber-200/50 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer flex-1"
                  title="Void and resolve immediately with zero balance"
                >
                  <ShieldCheck class="w-4 h-4 shrink-0 font-extrabold" />
                  Settle Mutually
                </button>

                <button 
                  v-if="m.status !== 'settled'"
                  @click="activeSelectedMortgage = m; payAmount = getMortgageOutstanding(m).toString(); isAddPaymentOpen = true;"
                  class="px-4 py-2 bg-[#005a5b] hover:bg-[#007273] dark:bg-teal-500 dark:hover:bg-teal-450 dark:text-zinc-950 text-white rounded-xl text-xs font-extrabold transition-all flex items-center justify-center gap-1.5 cursor-pointer flex-1"
                >
                  Record Cash Pay
                </button>
              </div>
            </div>

          </div>

          <!-- List of pay histories collapsible/detailed box -->
          <div v-if="(paymentsMap.get(m.id) || []).length > 0" class="mt-5 pt-4 border-t border-dotted border-zinc-200 dark:border-white/5 text-left">
            <h6 class="text-[9px] font-black text-indigo-500 uppercase tracking-wider mb-2.5 flex items-center gap-1 font-display">
              <Calendar class="w-3 text-indigo-400" />
              Cash Repayment logs history
            </h6>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs font-medium">
                <thead>
                  <tr class="text-zinc-400 uppercase text-[9px] tracking-wider border-b border-zinc-100 dark:border-white/5">
                    <th class="py-2">Date recorded</th>
                    <th class="py-2 text-right">Amount pay</th>
                    <th class="py-2 pl-4">Audit Note memo</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-zinc-100 dark:divide-white/5 font-mono">
                  <tr v-for="p in paymentsMap.get(m.id)" :key="p.id" class="text-zinc-950 dark:text-zinc-200 text-[11px]">
                    <td class="py-2 font-sans">{{ new Date(p.date.seconds * 1000).toLocaleDateString() }}</td>
                    <td class="py-2 text-right text-emerald-600 dark:text-teal-400 font-extrabold">
                      {{ formatCurrency(p.amount, m.currencyCode) }}
                    </td>
                    <td class="py-2 pl-4 italic text-zinc-400 font-sans truncate max-w-xs">{{ p.note || 'Regular payout installment' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Amortization Projections Trigger -->
          <div class="flex gap-2.5 mt-4 pt-3 border-t border-zinc-100 dark:border-white/5">
            <button 
              @click="expandedAmortizationId = expandedAmortizationId === m.id ? null : m.id"
              class="text-[10px] uppercase font-black text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1.5 cursor-pointer outline-none select-none"
              type="button"
            >
              <Sparkles class="w-3.5 h-3.5 text-indigo-500" />
              {{ expandedAmortizationId === m.id ? 'Close Amortization projection' : 'Forecast planned amortization schedule (principal vs interest)' }}
            </button>
          </div>

          <!-- Amortization Forecast Area -->
          <div v-if="expandedAmortizationId === m.id" class="mt-4 p-4 rounded-2xl bg-indigo-50/20 dark:bg-indigo-950/25 border border-indigo-500/10 text-left">
            <div class="flex items-center gap-2 mb-3">
              <Sparkles class="w-4 h-4 text-indigo-500 animate-pulse" />
              <div>
                <h5 class="text-xs font-bold text-zinc-900 dark:text-white leading-tight">Amortization & Interest-Split Projections</h5>
                <p class="text-[9px] text-zinc-500">Compound interest schedule projection for the full duration of {{ m.amortizationYears || 30 }} years.</p>
              </div>
            </div>

            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4 text-xs">
              <div class="bg-white dark:bg-[#111922] p-3 rounded-xl border border-zinc-200/50 dark:border-white/5 shadow-sm">
                <span class="block text-[8.5px] font-bold text-zinc-400 uppercase tracking-wider mb-0.5">Estimated Installment</span>
                <span class="block font-mono font-black text-indigo-600 dark:text-indigo-400 text-sm">
                  {{ formatCurrency(calculateAmortizationSchedule(m.amount, m.interestRate || 0, m.amortizationYears || 30).monthlyPayment, m.currencyCode) }}/mo
                </span>
              </div>
              <div class="bg-white dark:bg-[#111922] p-3 rounded-xl border border-zinc-200/50 dark:border-white/5 shadow-sm">
                <span class="block text-[8.5px] font-bold text-zinc-400 uppercase tracking-wider mb-0.5">Total Interest Cost</span>
                <span class="block font-mono font-black text-rose-500 text-sm">
                  {{ formatCurrency(calculateAmortizationSchedule(m.amount, m.interestRate || 0, m.amortizationYears || 30).totalInterestPaid, m.currencyCode) }}
                </span>
              </div>
              <div class="bg-white dark:bg-[#111922] p-3 rounded-xl border border-zinc-200/50 dark:border-white/5 shadow-sm">
                <span class="block text-[8.5px] font-bold text-zinc-405 uppercase tracking-wider mb-0.5">Total Amortized Cost</span>
                <span class="block font-mono font-bold text-zinc-950 dark:text-white text-sm">
                  {{ formatCurrency(calculateAmortizationSchedule(m.amount, m.interestRate || 0, m.amortizationYears || 30).totalCostOfLoan, m.currencyCode) }}
                </span>
              </div>
              <div class="bg-white dark:bg-[#111922] p-3 rounded-xl border border-zinc-200/50 dark:border-white/5 shadow-sm">
                <span class="block text-[8.5px] font-bold text-zinc-405 uppercase tracking-wider mb-0.5">Repayment Period</span>
                <span class="block font-mono font-bold text-zinc-700 dark:text-zinc-300 text-sm">
                  {{ m.amortizationYears }} Years ({{ (m.amortizationYears || 30) * 12 }} terms)
                </span>
              </div>
            </div>

            <div class="overflow-x-auto max-h-[220px] custom-scrollbar overflow-y-auto rounded-xl border border-zinc-150 dark:border-white/5 bg-white dark:bg-[#080d13]">
              <table class="w-full text-left text-[11px] font-medium leading-none">
                <thead class="bg-zinc-50 dark:bg-zinc-900 sticky top-0 z-10">
                  <tr class="text-zinc-400 font-bold uppercase text-[8.5px] tracking-wider border-b border-zinc-200/60 dark:border-white/5">
                    <th class="py-2.5 px-3">Month</th>
                    <th class="py-2.5 px-3 text-right">Payment</th>
                    <th class="py-2.5 px-3 text-right text-emerald-600 dark:text-emerald-450">Principal Portion</th>
                    <th class="py-2.5 px-3 text-right text-purple-600 dark:text-purple-450">Interest Portion</th>
                    <th class="py-2.5 px-3 text-right pr-4">Remaining Principal</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-zinc-100 dark:divide-white/5 font-mono text-[10.5px]">
                  <tr 
                    v-for="p in calculateAmortizationSchedule(m.amount, m.interestRate || 0, m.amortizationYears || 30).schedule.slice(0, 12)" 
                    :key="p.periodIndex"
                    class="hover:bg-zinc-50 dark:hover:bg-white/5 text-zinc-900 dark:text-zinc-250"
                  >
                    <td class="py-2 px-3 font-semibold text-zinc-400">Month #{{ p.periodIndex }}</td>
                    <td class="py-2 px-3 text-right font-bold">
                      {{ formatCurrency(p.paymentAmount, m.currencyCode) }}
                    </td>
                    <td class="py-2 px-3 text-right text-emerald-600 dark:text-emerald-400 font-extrabold">
                      {{ formatCurrency(p.principalPaid, m.currencyCode) }}
                    </td>
                    <td class="py-2 px-3 text-right text-purple-600 dark:text-purple-400 font-bold">
                      {{ formatCurrency(p.interestPaid, m.currencyCode) }}
                    </td>
                    <td class="py-2 px-3 text-right pr-4 text-zinc-400 font-bold">
                      {{ formatCurrency(p.remainingPrincipal, m.currencyCode) }}
                    </td>
                  </tr>
                  <tr v-if="calculateAmortizationSchedule(m.amount, m.interestRate || 0, m.amortizationYears || 30).schedule.length > 12">
                    <td colspan="5" class="py-2.5 text-center italic text-[10px] text-zinc-400 font-sans">
                      ... Showing schedule projection of first 12 installments. Continuing up to Month #{{ calculateAmortizationSchedule(m.amount, m.interestRate || 0, m.amortizationYears || 30).schedule.length }} ...
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Asset Modal Overlay -->
    <transition name="fade">
      <div v-if="isCreateMortgageOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Overlay background shadow backdrop -->
        <div class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm cursor-pointer" @click="isCreateMortgageOpen = false" />
        
        <div class="bg-white dark:bg-[#0c141d] border border-zinc-200 dark:border-white/10 rounded-3xl overflow-hidden shadow-2xl relative w-full max-w-lg z-10 max-h-[90vh] flex flex-col">
          <div class="p-6 border-b border-zinc-100 dark:border-white/5 flex items-center justify-between text-left">
            <div>
              <h3 class="text-lg font-black text-zinc-950 dark:text-white leading-tight">Collateral Property Mortgage Form</h3>
              <p class="text-[10px] text-zinc-500 mt-1 leading-relaxed">Secured asset collateral valuations, term years & interest metrics</p>
            </div>
            <button @click="isCreateMortgageOpen = false" class="text-zinc-400 hover:text-white cursor-pointer select-none font-bold">×</button>
          </div>

          <form @submit.prevent="handleCreateMortgage" class="p-6 space-y-4 overflow-y-auto custom-scrollbar text-left flex-1">
            
            <div class="grid grid-cols-2 gap-4">
              <button 
                type="button" 
                @click="newMortgageType = 'taken'"
                :class="`py-3 rounded-xl text-xs font-bold transition-all border shrink-0 ${
                  newMortgageType === 'taken' 
                    ? 'bg-rose-50/50 dark:bg-rose-500/10 border-rose-500 text-rose-600 dark:text-rose-450' 
                    : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-805 text-zinc-500'
                }`"
              >
                Mortgage Liability (Borrowed)
              </button>
              <button 
                type="button" 
                @click="newMortgageType = 'given'"
                :class="`py-3 rounded-xl text-xs font-bold transition-all border shrink-0 ${
                  newMortgageType === 'given' 
                    ? 'bg-emerald-50/50 dark:bg-emerald-500/10 border-emerald-500 text-emerald-600 dark:text-emerald-450' 
                    : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-805 text-zinc-550'
                }`"
              >
                Collateral Claim (Lent Out)
              </button>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">Property Collateral Name</label>
              <input 
                v-model="newMortgageProperty" 
                type="text" 
                placeholder="e.g. 210 Baker Street (Unit B Apartment)" 
                required
                class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 w-full rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs font-semibold text-zinc-950 dark:text-white"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">Lend Partner/Institution Name</label>
                <input 
                  v-model="newMortgagePerson" 
                  type="text" 
                  placeholder="e.g. Chase Bank, Private Partner" 
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 w-full rounded-xl border border-zinc-200 text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">Principal Borrowed Amount ({{ group?.currencyCode }})</label>
                <input 
                  v-model="newMortgageAmount" 
                  type="number" 
                  step="any" 
                  placeholder="e.g. 250000" 
                  required
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-200 dark:border-zinc-805 rounded-xl text-xs font-semibold font-mono text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Collateral Market Value ({{ group?.currencyCode }})</label>
                <input 
                  v-model="newCollateralValue" 
                  type="number" 
                  step="any" 
                  placeholder="e.g. 320000" 
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-800 rounded-xl text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Down Payment Paid ({{ group?.currencyCode }})</label>
                <input 
                  v-model="newDownPayment" 
                  type="number" 
                  step="any" 
                  placeholder="e.g. 50000" 
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-800 rounded-xl text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Interest Rate (%)</label>
                <input 
                  v-model="newMortgageInterest" 
                  type="number" 
                  step="0.05" 
                  placeholder="4.5" 
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-800 rounded-xl text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Term Duration Period (Years)</label>
                <input 
                  v-model="newAmortizationYears" 
                  type="number" 
                  placeholder="30" 
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Initiated Date</label>
                <input 
                  v-model="newMortgageDate" 
                  type="date" 
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-805 rounded-xl text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Maturity / Due Date (Optional)</label>
                <input 
                  v-model="newMortgageDueDate" 
                  type="date" 
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Description / Settlement Notes</label>
              <textarea 
                v-model="newMortgageDesc" 
                placeholder="Attach any property details, title deeds storage context, or amortization structures..." 
                class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-805 rounded-xl text-xs font-semibold resize-none h-20"
              />
            </div>

            <button 
              type="submit" 
              class="w-full py-4 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 text-xs font-bold rounded-xl mt-4 hover:bg-zinc-900 transition-all cursor-pointer"
            >
              Verify & Instantiate Amortization
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Cash Payout Installment modal -->
    <transition name="fade">
      <div v-if="isAddPaymentOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Overlay dark backdrop -->
        <div class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm cursor-pointer" @click="isAddPaymentOpen = false" />

        <div class="bg-white dark:bg-[#0c141d] border border-zinc-220 dark:border-white/10 rounded-2xl p-6 w-full max-w-sm relative z-10 text-left">
          <div class="mb-4">
            <h3 class="text-sm font-black text-zinc-950 dark:text-white uppercase tracking-wider">Record Amortized Cash Payment</h3>
            <p class="text-[10px] text-zinc-500 mt-0.5">Increases repaid cumulative total & decreases outstanding liability value</p>
          </div>

          <form @submit.prevent="handleRecordPayment" class="space-y-4">
            <div>
              <label class="block text-[9px] font-bold text-zinc-405 uppercase tracking-wider mb-1.5">Installment paid amount ({{ group?.currencyCode }})</label>
              <input 
                v-model="payAmount" 
                type="number" 
                step="any" 
                required 
                class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border text-xs font-semibold font-mono"
              />
            </div>

            <div>
              <label class="block text-[9px] font-bold text-zinc-405 uppercase tracking-wider mb-1.5">Date transaction executed</label>
              <input 
                v-model="payDate" 
                type="date" 
                required 
                class="w-full px-4 py-3 bg-[#fafafa] d-full rounded-xl border text-xs font-semibold"
              />
            </div>

            <div>
              <div class="flex items-center justify-between mb-1.5 leading-none">
                <label class="block text-[9px] font-bold text-zinc-405 uppercase tracking-wider">Link Bank Account/Card (Auto-Deduct)</label>
                <span class="text-[8.5px] text-[#005a5b] dark:text-teal-400 font-bold font-mono">Optional</span>
              </div>
              <select 
                v-model="payLinkedAccountId"
                class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border text-xs font-semibold focus:outline-none"
              >
                <option value="">-- No Account Deduction (Manual Entry) --</option>
                <option v-for="acc in accountsList" :key="acc.id" :value="acc.id">
                  {{ acc.name }} ({{ formatCurrency(acc.balance || 0, acc.currencyCode) }})
                </option>
              </select>
              <p class="text-[9px] text-zinc-400 mt-1 leading-tight">
                Instantly records a backing transaction on the linked account and syncs balances.
              </p>
            </div>

            <div>
              <label class="block text-[9px] font-bold text-zinc-405 uppercase tracking-wider mb-1.5">Note description</label>
              <input 
                v-model="payNote" 
                type="text" 
                placeholder="e.g. May 2026 Monthly Payout installment" 
                class="w-full px-4 py-3 bg-[#fafafa] rounded-xl border text-xs font-medium"
              />
            </div>

            <div class="flex gap-2 pt-2">
              <button 
                type="button" 
                @click="isAddPaymentOpen = false" 
                class="flex-1 py-3 bg-zinc-100 hover:bg-zinc-200 text-zinc-700 rounded-xl text-xs font-bold cursor-pointer"
              >
                Dismiss Form
              </button>
              <button 
                type="submit" 
                class="flex-1 py-3 bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 rounded-xl text-xs font-extrabold cursor-pointer"
              >
                Log Payment
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>
  </div>
</template>
