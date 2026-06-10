<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue';
import { db } from '../firebase';
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
  User, 
  Scale, 
  Sparkles,
  Info,
  Clock,
  Briefcase,
  DollarSign
} from 'lucide-vue-next';
import { type Group, type Rent, type RentPayment } from '../types';
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
const rents = ref<Rent[]>([]);
const paymentsMap = ref<Map<string, RentPayment[]>>(new Map());
const accountsList = ref<Group[]>([]);

const activeSelectedRent = ref<Rent | null>(null);

// Forms state
const isCreateRentOpen = ref(false);
const isAddPaymentOpen = ref(false);

// New Rent contract form
const newRentProperty = ref('');
const newRentPerson = ref('');
const newRentType = ref<'given' | 'taken'>('taken');
const newRentAmount = ref('');
const newRentFrequency = ref<'monthly' | 'weekly' | 'yearly' | 'other'>('monthly');
const newRentDeposit = ref('');
const newRentStartDate = ref(new Date().toISOString().split('T')[0]);
const newRentEndDate = ref('');
const newRentDesc = ref('');

// Payment form
const payAmount = ref('');
const payDate = ref(new Date().toISOString().split('T')[0]);
const payNote = ref('');
const payLinkedAccountId = ref('');

// Filter state
const activeFilter = ref<'all' | 'given' | 'taken'>('all');

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

    // 3. Listen to Rent subcollection
    const rQuery = query(collection(db, 'groups', props.groupId, 'rents'), orderBy('createdAt', 'desc'));
    onSnapshot(rQuery, (snapshot) => {
      rents.value = snapshot.docs.map(d => ({
        id: d.id,
        ...d.data()
      } as Rent));

      // Fetch payment lists for all rents
      rents.value.forEach(r => {
        const pQuery = query(
          collection(db, 'groups', props.groupId, 'rents', r.id, 'rent_payments'), 
          orderBy('date', 'desc')
        );
        onSnapshot(pQuery, (pSnap) => {
          const list = pSnap.docs.map(pd => ({
            id: pd.id,
            ...pd.data()
          } as RentPayment));
          paymentsMap.value.set(r.id, list);
        });
      });

      loading.value = false;
    });

  } catch (error) {
    console.error("Error setting up rent stream listener:", error);
    loading.value = false;
  }
});

// Calculations helper
const getRentPaidTotal = (r: Rent) => {
  const ps = paymentsMap.value.get(r.id) || [];
  return ps.reduce((sum, p) => sum + p.amount, 0);
};

const getRentPaymentsCount = (r: Rent) => {
  const ps = paymentsMap.value.get(r.id) || [];
  return ps.length;
};

// Computed Stats of the current ledger group
const totalRentInflow = computed(() => {
  return rents.value
    .filter(r => r.type === 'given' && r.status !== 'settled')
    .reduce((s, r) => s + r.amount, 0);
});

const totalRentOutflow = computed(() => {
  return rents.value
    .filter(r => r.type === 'taken' && r.status !== 'settled')
    .reduce((s, r) => s + r.amount, 0);
});

const netRentIndexValue = computed(() => {
  return totalRentInflow.value - totalRentOutflow.value;
});

const filteredRents = computed(() => {
  if (activeFilter.value === 'given') {
    return rents.value.filter(r => r.type === 'given');
  }
  if (activeFilter.value === 'taken') {
    return rents.value.filter(r => r.type === 'taken');
  }
  return rents.value;
});

// Actions handlers
const handleCreateRent = async () => {
  if (!newRentProperty.value.trim() || !newRentAmount.value || !newRentPerson.value.trim()) return;

  try {
    const rentId = crypto.randomUUID();
    const amt = parseFloat(newRentAmount.value) || 0;
    const dep = parseFloat(newRentDeposit.value) || 0;

    const payload: Rent = {
      id: rentId,
      groupId: props.groupId,
      type: newRentType.value,
      tenantOrLandlord: newRentPerson.value.trim(),
      propertyName: newRentProperty.value.trim(),
      amount: amt,
      frequency: newRentFrequency.value,
      currencyCode: group.value?.currencyCode || 'USD',
      startDate: Timestamp.fromDate(new Date(newRentStartDate.value)),
      status: 'active',
      description: newRentDesc.value.trim() || undefined,
      createdAt: Timestamp.now(),
      createdBy: props.user.uid
    };

    if (dep > 0) {
      payload.depositAmount = dep;
    }

    if (newRentEndDate.value) {
      payload.endDate = Timestamp.fromDate(new Date(newRentEndDate.value));
    }

    await setDoc(doc(db, 'groups', props.groupId, 'rents', rentId), payload);
    isCreateRentOpen.value = false;

    // Reset fields
    newRentProperty.value = '';
    newRentPerson.value = '';
    newRentAmount.value = '';
    newRentDeposit.value = '';
    newRentFrequency.value = 'monthly';
    newRentStartDate.value = new Date().toISOString().split('T')[0];
    newRentEndDate.value = '';
    newRentDesc.value = '';

  } catch (error) {
    console.error("Error creating rent property entry:", error);
  }
};

const handleRecordPayment = async () => {
  if (!activeSelectedRent.value || !payAmount.value) return;

  try {
    const r = activeSelectedRent.value;
    const pAmt = parseFloat(payAmount.value) || 0;
    if (pAmt <= 0) return;

    const paymentId = crypto.randomUUID();
    let txnId: string | undefined;

    // Link Bank Account / Card deduction
    if (payLinkedAccountId.value) {
      const bank = accountsList.value.find(acc => acc.id === payLinkedAccountId.value);
      if (bank) {
        txnId = crypto.randomUUID();
        const isExpense = r.type === 'taken'; // taken = we pay rent (expense)
        const linkAmt = isExpense ? -pAmt : pAmt;

        const txPayload = {
          id: txnId,
          groupId: bank.id,
          accountId: bank.id,
          amount: linkAmt,
          description: isExpense ? `Rent Payment: ${r.propertyName}` : `Rent Received: ${r.propertyName}`,
          category: isExpense ? 'Card Payment' : 'Salary & Deposit',
          date: Timestamp.fromDate(new Date(payDate.value)),
          createdAt: Timestamp.now(),
          note: `Auto-linked lease installment of property: ${r.propertyName}`,
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

    const pPayload: RentPayment = {
      id: paymentId,
      rentId: r.id,
      groupId: props.groupId,
      amount: pAmt,
      date: Timestamp.fromDate(new Date(payDate.value)),
      note: payNote.value.trim() || undefined,
      linkedAccountId: payLinkedAccountId.value || undefined,
      linkedTransactionId: txnId || undefined,
      createdAt: Timestamp.now()
    };

    await setDoc(doc(db, 'groups', props.groupId, 'rents', r.id, 'rent_payments', paymentId), pPayload);

    isAddPaymentOpen.value = false;
    payAmount.value = '';
    payNote.value = '';
    payLinkedAccountId.value = '';

  } catch (error) {
    console.error("Error writing rent payment data: ", error);
  }
};

const handleTerminateContract = async (r: Rent) => {
  const confirmTerminate = confirm("Are you sure you want to mark this rent agreement / lease as Settled/Terminated? This locks future recurrence checks.");
  if (!confirmTerminate) return;

  try {
    await setDoc(doc(db, 'groups', props.groupId, 'rents', r.id), { status: 'settled' }, { merge: true });
    alert("Rent agreement flagged as settled/terminated.");
  } catch (error) {
    console.error("Error terminating rent lease:", error);
  }
};

const handleDeleteRent = async (r: Rent) => {
  const confirmDel = confirm("Are you sure you want to completely delete this Rent lease record? All historic logs in this contract will be erased permanently.");
  if (!confirmDel) return;

  try {
    await deleteDoc(doc(db, 'groups', props.groupId, 'rents', r.id));
    alert("Rent lease contract deleted.");
  } catch (error) {
    console.error("Error deleting rent agreement:", error);
  }
};
</script>

<template>
  <div class="space-y-8" id="group-rents-view-container">
    <!-- Breadcrumb back link -->
    <button 
      @click="emit('back')"
      class="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-950 dark:hover:text-white text-xs font-black select-none cursor-pointer group bg-transparent border-none"
    >
      <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
      Back to Rent Hub
    </button>

    <!-- Header Section card -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-5 bg-white dark:bg-[#0c141d]/70 p-8 border border-zinc-200 dark:border-white/10 rounded-[32px] shadow-sm text-left">
      <div>
        <div class="flex items-center gap-3 mb-2.5">
          <span class="px-3 py-1 bg-teal-50 dark:bg-teal-500/10 text-teal-650 dark:text-teal-400 text-[10px] uppercase font-black tracking-widest rounded-full">
            REAL ESTATE LEASE REGISTRIES
          </span>
          <span class="text-zinc-400 font-mono text-[11px] font-bold">
            Ledger Identifier: {{ group?.id }}
          </span>
        </div>
        <h2 class="text-3xl font-black text-zinc-950 dark:text-white tracking-tight font-display mb-1">
          {{ group?.name }}
        </h2>
        <p class="text-xs text-zinc-550 leading-relaxed max-w-2xl">
          {{ group?.description || 'Active long-term tenancy leases, rental cash installments, and centralized balance synchronization.' }}
        </p>
      </div>

      <button 
        @click="isCreateRentOpen = true"
        class="px-5 py-4 bg-gradient-to-br from-[#005a5b] to-teal-600 hover:from-[#004a4b] hover:to-teal-750 text-white rounded-2xl font-bold text-xs transition-colors shadow-lg shadow-teal-500/15 flex items-center justify-center gap-2 shrink-0 cursor-pointer"
      >
        <Plus class="w-4 h-4 shrink-0" />
        Record Lease Agreement
      </button>
    </div>

    <!-- Active Rent Ledger Statistics Bar -->
    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-4 gap-5" id="group-rent-stats-bar">
      <!-- 1st element: Receivables (Tenants pay us) -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Regular Rental Revenue</span>
        <span class="block text-xl font-black text-emerald-600 dark:text-emerald-400 font-mono">
          {{ formatCurrency(totalRentInflow, group?.currencyCode || 'USD') }}<span class="text-xs font-bold text-zinc-400">/mo</span>
        </span>
      </div>

      <!-- 2nd element: Rent We Pay (Outflows) -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Regular Tenancy Payables</span>
        <span class="block text-xl font-black text-rose-600 dark:text-rose-450 font-mono">
          {{ formatCurrency(totalRentOutflow, group?.currencyCode || 'USD') }}<span class="text-xs font-bold text-zinc-400">/mo</span>
        </span>
      </div>

      <!-- 3rd element: Overall Leases Count -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Active Property Leases</span>
        <span class="block text-xl font-black text-teal-600 dark:text-teal-450 font-mono">
          {{ rents.filter(r => r.status === 'active').length }}
        </span>
      </div>

      <!-- 4th element: Ledger balance index indicator -->
      <div class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-2xl text-left">
        <span class="block text-[9px] font-bold text-zinc-400 uppercase tracking-wider mb-1.5 font-display">Rent Clearing Portfolio Balance</span>
        <span :class="`block text-lg font-black font-mono truncate ${
          netRentIndexValue >= 0 ? 'text-teal-600 dark:text-teal-405' : 'text-rose-600'
        }`">
          {{ formatCurrency(netRentIndexValue, group?.currencyCode || 'USD') }}<span class="text-[10px] font-medium font-sans">/mo</span>
        </span>
      </div>
    </div>

    <!-- Main List of Rents -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="w-8 h-8 border-4 border-teal-500 border-t-transparent rounded-full animate-spin" />
    </div>

    <div v-else class="space-y-4">
      <!-- Grid header tabs -->
      <div class="flex gap-2 p-1.5 bg-zinc-100 dark:bg-white/5 rounded-2xl w-fit select-none border border-zinc-200/50 dark:border-white/5">
        <button 
          @click="activeFilter = 'all'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'all' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          All ({{ rents.length }})
        </button>
        <button 
          @click="activeFilter = 'given'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'given' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          Leased Out ({{ rents.filter(r => r.type === 'given').length }})
        </button>
        <button 
          @click="activeFilter = 'taken'"
          :class="`px-5 py-2.5 rounded-xl font-bold text-xs transition-all cursor-pointer ${activeFilter === 'taken' ? 'bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-white'}`"
        >
          Rented By Us ({{ rents.filter(r => r.type === 'taken').length }})
        </button>
      </div>

      <div v-if="filteredRents.length === 0" class="py-20 text-center text-zinc-550 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[32px] shadow-sm">
        <Home class="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-755 mb-4" />
        <h3 class="font-bold text-zinc-950 dark:text-white tracking-tight mb-2 font-display">No agreements registered</h3>
        <p class="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed">
          No property entries match the filter criteria under this ledger. Click "Record Lease Agreement" above to register a rent property.
        </p>
      </div>

      <div v-else class="space-y-4" id="group-rents-list-view">
        <div 
          v-for="r in filteredRents" 
          :key="r.id" 
          class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-205 dark:border-white/10 rounded-[28px] overflow-hidden shadow-sm"
        >
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            <!-- col-span-5: Details of property name and partner names -->
            <div class="lg:col-span-5 text-left space-y-4">
              <div class="flex items-center gap-3">
                <div class="w-12 h-12 rounded-2xl flex items-center justify-center bg-teal-50 dark:bg-teal-500/10 text-teal-600 dark:text-teal-400 shrink-0">
                  <Home class="w-6 h-6" />
                </div>
                <div>
                  <h4 class="font-black text-zinc-950 dark:text-white tracking-tight leading-snug">
                    {{ r.propertyName }}
                  </h4>
                  <p class="text-[11px] text-zinc-405 font-medium flex items-center gap-1 mt-0.5">
                    <User class="w-3" />
                    <span>{{ r.type === 'given' ? 'Tenant:' : 'Landlord:' }} <strong>{{ r.tenantOrLandlord }}</strong></span>
                  </p>
                </div>
              </div>

              <!-- General specs pill indicators index -->
              <div class="flex flex-wrap gap-2">
                <span :class="`px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider ${
                  r.type === 'given' 
                    ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600' 
                    : 'bg-rose-50 dark:bg-rose-500/10 text-rose-600'
                }`">
                  {{ r.type === 'given' ? 'Income-producing lease' : 'Expense tenancy list' }}
                </span>
                <span v-if="r.status === 'settled'" class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider bg-zinc-150 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-500 flex items-center gap-1">
                  <CheckCircle class="w-3 h-3 text-zinc-500" />
                  Terminated/Settled
                </span>
                <span v-else class="px-2.5 py-1 rounded-full text-[9px] font-black uppercase tracking-wider bg-teal-50 dark:bg-teal-500/10 text-teal-600">
                  Active Recurring
                </span>
              </div>

              <!-- Details note memo -->
              <p v-if="r.description" class="text-xs text-zinc-505 dark:text-zinc-420 italic bg-zinc-50 dark:bg-white/5 p-3 rounded-xl mt-3 leading-relaxed">
                "{{ r.description }}"
              </p>
            </div>

            <!-- col-span-3: Financial Details -->
            <div class="lg:col-span-3 text-left space-y-2.5">
              <h5 class="text-[9px] font-black text-teal-650 dark:text-teal-400 uppercase tracking-widest block font-display">Contract Schedule & Security</h5>
              <div class="space-y-1.5 text-xs">
                <div class="flex justify-between items-center text-zinc-500">
                  <span>Regular Rent Cost:</span>
                  <span class="font-extrabold text-zinc-950 dark:text-white font-mono">
                    {{ formatCurrency(r.amount, r.currencyCode) }} / {{ r.frequency }}
                  </span>
                </div>
                <div v-if="r.depositAmount" class="flex justify-between items-center text-zinc-500">
                  <span>Security Deposit:</span>
                  <span class="font-bold text-teal-600 dark:text-teal-400 font-mono">
                    {{ formatCurrency(r.depositAmount, r.currencyCode) }}
                  </span>
                </div>
                <div class="flex justify-between items-center text-[#005a5b] dark:text-teal-450 pt-2 border-t border-zinc-100 dark:border-white/5">
                  <span class="flex items-center gap-1"><Calendar class="w-3" /> Start Date:</span>
                  <span class="font-bold font-mono">
                    {{ new Date(r.startDate.seconds * 1000).toLocaleDateString() }}
                  </span>
                </div>
                <div v-if="r.endDate" class="flex justify-between items-center text-zinc-400">
                  <span class="flex items-center gap-1"><Clock class="w-3" /> Expiration Date:</span>
                  <span class="font-bold font-mono">
                    {{ new Date(r.endDate.seconds * 1000).toLocaleDateString() }}
                  </span>
                </div>
              </div>
            </div>

            <!-- col-span-4: Balance summary counters and Actions -->
            <div class="lg:col-span-4 text-left flex flex-col justify-between h-full space-y-4">
              <div class="bg-zinc-50 dark:bg-[#121c27] p-4 rounded-2xl border border-zinc-100 dark:border-white/5">
                <div class="flex justify-between items-center text-xs mb-1.5">
                  <span class="text-zinc-405 font-bold">Total Accumulated Pay:</span>
                  <span class="font-black font-mono text-zinc-950 dark:text-white">
                    {{ formatCurrency(getRentPaidTotal(r), r.currencyCode) }}
                  </span>
                </div>

                <div class="flex items-center justify-between text-[11px] text-zinc-400">
                  <span>Logged installments:</span>
                  <span class="font-black font-mono text-[#005a5b] dark:text-teal-405">
                    {{ getRentPaymentsCount(r) }} installments
                  </span>
                </div>
              </div>

              <!-- Button Actions -->
              <div class="flex flex-wrap gap-2 pt-2">
                <button 
                  @click="handleDeleteRent(r)"
                  class="p-2.5 border border-rose-500/15 hover:bg-rose-500/15 text-rose-500 rounded-xl transition-all cursor-pointer bg-transparent"
                  title="Delete Tenant Lease"
                >
                  <Trash class="w-4 h-4" />
                </button>

                <button 
                  v-if="r.status !== 'settled'"
                  @click="handleTerminateContract(r)"
                  class="px-3 py-2 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 border border-zinc-200/50 dark:border-white/5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer flex-1"
                  title="Mark Lease as Terminated/Settled"
                >
                  <CheckCircle class="w-4 h-4 shrink-0 font-extrabold" />
                  Terminate Lease
                </button>

                <button 
                  v-if="r.status !== 'settled'"
                  @click="activeSelectedRent = r; payAmount = r.amount.toString(); isAddPaymentOpen = true;"
                  class="px-4 py-2 bg-[#005a5b] hover:bg-[#007273] dark:bg-teal-500 dark:hover:bg-teal-450 dark:text-zinc-950 text-white rounded-xl text-xs font-extrabold transition-all flex items-center justify-center gap-1.5 cursor-pointer flex-1"
                >
                  Record Rent Pay
                </button>
              </div>
            </div>

          </div>

          <!-- List of rent payments collapsible/detailed box -->
          <div v-if="(paymentsMap.get(r.id) || []).length > 0" class="mt-5 pt-4 border-t border-dotted border-zinc-200 dark:border-white/5 text-left">
            <h6 class="text-[9px] font-black text-teal-650 dark:text-teal-400 uppercase tracking-wider mb-2.5 flex items-center gap-1 font-display">
              <Calendar class="w-3 text-teal-500" />
              Cash Installment payment records
            </h6>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs font-medium">
                <thead>
                  <tr class="text-zinc-400 uppercase text-[9px] tracking-wider border-b border-zinc-100 dark:border-white/5">
                    <th class="py-2">Date recorded</th>
                    <th class="py-2 text-right">Amount pay</th>
                    <th class="py-2 pl-4">Note / description</th>
                    <th class="py-2 pl-4">Deducted Card/Bank</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-zinc-100 dark:divide-white/5 font-mono">
                  <tr v-for="p in paymentsMap.get(r.id)" :key="p.id" class="text-zinc-950 dark:text-zinc-200 text-[11px]">
                    <td class="py-2 font-sans">{{ new Date(p.date.seconds * 1000).toLocaleDateString() }}</td>
                    <td class="py-2 text-right text-emerald-600 dark:text-teal-400 font-extrabold">
                      {{ formatCurrency(p.amount, r.currencyCode) }}
                    </td>
                    <td class="py-2 pl-4 italic text-zinc-405 font-sans truncate max-w-xs">{{ p.note || 'Monthly Lease Installment' }}</td>
                    <td class="py-2 pl-4 font-sans text-zinc-500">
                      {{ p.linkedAccountId ? (accountsList.find(a => a.id === p.linkedAccountId)?.name || 'Linked Account') : 'No linked auto-deduction' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Rent Contract Modal Overlay -->
    <transition name="fade">
      <div v-if="isCreateRentOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Overlay background shadow backdrop -->
        <div class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm cursor-pointer" @click="isCreateRentOpen = false" />
        
        <div class="bg-white dark:bg-[#0c141d] border border-zinc-200 dark:border-white/10 rounded-3xl overflow-hidden shadow-2xl relative w-full max-w-lg z-10 max-h-[90vh] flex flex-col">
          <div class="p-6 border-b border-zinc-100 dark:border-white/5 flex items-center justify-between text-left">
            <div>
              <h3 class="text-lg font-black text-zinc-950 dark:text-white leading-tight">Property Lease Agreement Form</h3>
              <p class="text-[10px] text-zinc-500 mt-1 leading-relaxed">Secured renter leases, frequency options & deposit allocations</p>
            </div>
            <button @click="isCreateRentOpen = false" class="text-zinc-400 hover:text-white cursor-pointer select-none font-bold bg-transparent border-none">×</button>
          </div>

          <form @submit.prevent="handleCreateRent" class="p-6 space-y-4 overflow-y-auto custom-scrollbar text-left flex-1">
            
            <div class="grid grid-cols-2 gap-4">
              <button 
                type="button" 
                @click="newRentType = 'taken'"
                :class="`py-3 rounded-xl text-xs font-bold transition-all border shrink-0 bg-transparent ${
                  newRentType === 'taken' 
                    ? 'bg-rose-50/50 dark:bg-rose-500/10 border-rose-500 text-rose-600 dark:text-rose-450' 
                    : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-805 text-zinc-500'
                }`"
              >
                Renting property (We Pay)
              </button>
              <button 
                type="button" 
                @click="newRentType = 'given'"
                :class="`py-3 rounded-xl text-xs font-bold transition-all border shrink-0 bg-transparent ${
                  newRentType === 'given' 
                    ? 'bg-emerald-50/50 dark:bg-emerald-500/10 border-emerald-500 text-emerald-600 dark:text-emerald-450' 
                    : 'bg-zinc-50 dark:bg-zinc-900 border-zinc-200 dark:border-zinc-805 text-zinc-550'
                }`"
              >
                Leasing property out (We Receive)
              </button>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">Property Unit or Address Name</label>
              <input 
                v-model="newRentProperty" 
                type="text" 
                placeholder="e.g. Apartment 404, Building A, Main Road" 
                required
                class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 dark:border-zinc-800 text-xs font-semibold text-zinc-950 dark:text-white"
              />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">{{ newRentType === 'given' ? 'Tenant Name' : 'Landlord Name' }}</label>
                <input 
                  v-model="newRentPerson" 
                  type="text" 
                  placeholder="e.g. Jane Smith, Avalon Properties" 
                  required
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">Rent Payable Amount ({{ group?.currencyCode }})</label>
                <input 
                  v-model="newRentAmount" 
                  type="number" 
                  step="any" 
                  placeholder="e.g. 1800" 
                  required
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-200 dark:border-zinc-805 rounded-xl text-xs font-semibold font-mono text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2 font-display">Rent Frequency Schedule</label>
                <select 
                  v-model="newRentFrequency" 
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 text-xs font-semibold text-zinc-950 dark:text-white"
                >
                  <option value="monthly">Monthly Cycle</option>
                  <option value="weekly">Weekly Cycle</option>
                  <option value="yearly">Yearly Cycle</option>
                  <option value="other">Flexible Period</option>
                </select>
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Security Deposit (Optional)</label>
                <input 
                  v-model="newRentDeposit" 
                  type="number" 
                  step="any" 
                  placeholder="e.g. 1000" 
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-800 rounded-xl text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Lease Start Date</label>
                <input 
                  v-model="newRentStartDate" 
                  type="date" 
                  required
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-805 rounded-xl text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Lease Expiration / End Date (Optional)</label>
                <input 
                  v-model="newRentEndDate" 
                  type="date" 
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 text-xs font-semibold text-zinc-950 dark:text-white"
                />
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Contract Memo Description / Terms</label>
              <textarea 
                v-model="newRentDesc" 
                placeholder="Attach any lease conditions, utilities inclusion terms, or check-out details..." 
                class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-805 rounded-xl text-xs font-semibold resize-none h-20"
              />
            </div>

            <button 
              type="submit" 
              class="w-full py-4 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 text-xs font-bold rounded-xl mt-4 hover:bg-zinc-900 transition-all cursor-pointer border-none"
            >
              Verify & Instantiate Lease Agreement
            </button>
          </form>
        </div>
      </div>
    </transition>

    <!-- Cash Rent Payout Installment modal -->
    <transition name="fade">
      <div v-if="isAddPaymentOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Overlay dark backdrop -->
        <div class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm cursor-pointer" @click="isAddPaymentOpen = false" />

        <div class="bg-white dark:bg-[#0c141d] border border-zinc-220 dark:border-white/10 rounded-2xl p-6 w-full max-w-sm relative z-10 text-left animate-in">
          <div class="mb-4">
            <h3 class="text-sm font-black text-zinc-950 dark:text-white uppercase tracking-wider">Record Rental Cash Payment</h3>
            <p class="text-[10px] text-zinc-500 mt-0.5">Records dynamic rent receipt transactions and links card deductibles centrally</p>
          </div>

          <form @submit.prevent="handleRecordPayment" class="space-y-4">
            <div>
              <label class="block text-[9px] font-bold text-[#005a5b] dark:text-teal-400 uppercase tracking-wider mb-1.5 font-display">Installment amount paid ({{ group?.currencyCode }})</label>
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
                class="w-full px-4 py-3 bg-[#fafafa] rounded-xl border text-xs font-semibold"
              />
            </div>

            <div>
              <div class="flex items-center justify-between mb-1.5 leading-none">
                <label class="block text-[9px] font-bold text-zinc-405 uppercase tracking-wider">Link Bank Account/Card (Auto-Deduct/Deposit)</label>
                <span class="text-[8.5px] text-[#005a5b] dark:text-teal-400 font-bold font-mono">Optional</span>
              </div>
              <select 
                v-model="payLinkedAccountId"
                class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border text-xs font-semibold focus:outline-none focus:border-teal-500"
              >
                <option value="">-- No Account Balance Sync (Manual Log) --</option>
                <option v-for="acc in accountsList" :key="acc.id" :value="acc.id">
                  {{ acc.name }} ({{ formatCurrency(acc.balance || 0, acc.currencyCode) }})
                </option>
              </select>
              <p class="text-[9px] text-zinc-400 mt-1 leading-tight">
                Instantly adds a ledger transaction to the linked account and syncs the cash balances.
              </p>
            </div>

            <div>
              <label class="block text-[9px] font-bold text-zinc-405 uppercase tracking-wider mb-1.5">Note description</label>
              <input 
                v-model="payNote" 
                type="text" 
                placeholder="e.g. Rent payment for May 2026" 
                class="w-full px-4 py-3 bg-[#fafafa] rounded-xl border text-xs font-medium"
              />
            </div>

            <div class="flex gap-2 pt-2">
              <button 
                type="button" 
                @click="isAddPaymentOpen = false" 
                class="flex-1 py-3 bg-zinc-100 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 rounded-xl text-xs font-bold cursor-pointer border-none"
              >
                Dismiss Form
              </button>
              <button 
                type="submit" 
                class="flex-1 py-3 bg-[#005a5b] dark:bg-teal-500 text-white dark:text-zinc-950 rounded-xl text-xs font-extrabold cursor-pointer border-none"
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
