<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import { db } from '../firebase';
import { collection, addDoc, serverTimestamp, doc, setDoc, Timestamp } from 'firebase/firestore';
import { X, Home, Plane, Users, Briefcase, DollarSign, Laptop, Store, TrendingUp, Sparkles, Scale } from 'lucide-vue-next';
import { type GroupType, type BudgetType } from '../types';
import { handleFirestoreError, OperationType } from '../utils/errorHandling';
import { getCurrencySymbol, CURRENCIES } from '../utils/currency';

const props = defineProps<{
  isOpen: boolean;
  user: any;
  activeService?: 'budget' | 'savings' | 'income' | 'accounts' | 'loans_debts' | 'mortgages' | 'rent' | 'document_vault' | 'db-inspector';
  'active-service'?: 'budget' | 'savings' | 'income' | 'accounts' | 'loans_debts' | 'mortgages' | 'rent' | 'document_vault' | 'db-inspector';
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const name = ref('');
const description = ref('');
const type = ref<GroupType>('household');
const maxBudget = ref('');
const budgetType = ref<BudgetType>('monthly');
const currencyCode = ref('USD');
const service = ref<'budget' | 'savings' | 'income' | 'accounts' | 'loans_debts' | 'mortgages' | 'rent' | 'document_vault'>('budget');
const isSubmitting = ref(false);

const accountType = ref<'checking' | 'savings' | 'credit_card' | 'debit_card'>('checking');
const bankName = ref('');
const initialBalance = ref('');
const creditLimit = ref('');
const selectedCardColor = ref('slate');

const cardColors = [
  { id: 'slate', bg: 'bg-gradient-to-br from-zinc-800 via-zinc-900 to-black', text: 'text-zinc-100', accent: 'border-zinc-700' },
  { id: 'indigo', bg: 'bg-gradient-to-br from-indigo-600 via-violet-700 to-indigo-950', text: 'text-white', accent: 'border-indigo-500/30' },
  { id: 'emerald', bg: 'bg-gradient-to-br from-teal-600 via-emerald-700 to-teal-950', text: 'text-emerald-50', accent: 'border-emerald-500/30' },
  { id: 'rose', bg: 'bg-gradient-to-br from-rose-600 via-pink-700 to-red-950', text: 'text-white', accent: 'border-rose-500/30' },
  { id: 'amber', bg: 'bg-gradient-to-br from-amber-500 via-orange-600 to-yellow-950', text: 'text-amber-50', accent: 'border-amber-500/30' }
];

const generateMaskedCardNumber = (type: string) => {
  const digits = Math.floor(1000 + Math.random() * 9000);
  if (type === 'checking' || type === 'savings') {
    return `Acc: •••• ${digits}`;
  }
  return `•••• •••• •••• ${digits}`;
};

const showPurposeSelection = computed(() => {
  const currentService = props.activeService || (props as any)['active-service'];
  return currentService !== 'budget' && currentService !== 'savings' && currentService !== 'income' && currentService !== 'accounts' && currentService !== 'loans_debts' && currentService !== 'mortgages' && currentService !== 'rent' && currentService !== 'document_vault';
});

watch(service, (newService) => {
  if (newService === 'income') {
    type.value = 'employment';
  } else if (newService === 'savings' || newService === 'accounts' || newService === 'loans_debts' || newService === 'mortgages' || newService === 'rent' || newService === 'document_vault') {
    type.value = 'personal';
  } else {
    type.value = 'household';
  }
});

watch(() => props.isOpen, (open) => {
  if (open) {
    currencyCode.value = props.user?.defaultCurrency || 'USD';
    const currentService = props.activeService || (props as any)['active-service'];
    if (currentService === 'savings') {
      service.value = 'savings';
    } else if (currentService === 'income') {
      service.value = 'income';
    } else if (currentService === 'accounts') {
      service.value = 'accounts';
    } else if (currentService === 'loans_debts') {
      service.value = 'loans_debts';
    } else if (currentService === 'mortgages') {
      service.value = 'mortgages';
    } else if (currentService === 'rent') {
      service.value = 'rent';
    } else if (currentService === 'document_vault') {
      service.value = 'document_vault';
    } else {
      service.value = 'budget';
    }
  }
}, { immediate: true });

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.isOpen) {
    emit('close');
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
});

const handleSubmit = async () => {
  if (!name.value.trim() || isSubmitting.value) return;

  isSubmitting.value = true;
  try {
    // 1. Create the group
    const groupData: any = {
      name: name.value.trim(),
      description: description.value.trim(),
      type: type.value,
      createdBy: props.user.uid,
      createdAt: serverTimestamp(),
      memberIds: [props.user.uid],
      currencyCode: currencyCode.value,
      service: service.value,
    };

    if (service.value === 'accounts') {
      groupData.accountType = accountType.value;
      groupData.bankName = bankName.value.trim() || 'Generic Bank';
      groupData.cardNumber = generateMaskedCardNumber(accountType.value);
      groupData.balance = parseFloat(initialBalance.value) || 0;
      groupData.creditLimit = accountType.value === 'credit_card' ? (parseFloat(creditLimit.value) || 0) : 0;
      groupData.color = selectedCardColor.value;
    } else {
      if (maxBudget.value && !isNaN(parseFloat(maxBudget.value))) {
        groupData.maxBudget = parseFloat(maxBudget.value);
        groupData.budgetType = budgetType.value;
      }
    }

    const groupRef = await addDoc(collection(db, 'groups'), groupData);
    console.log(`Group created successfully with ID: ${groupRef.id}`);

    // If accounts, and initial balance !== 0, create seed transaction under account_transactions
    if (service.value === 'accounts' && parseFloat(initialBalance.value) !== 0) {
      const doubleInitialBalance = parseFloat(initialBalance.value) || 0;
      const initialTx = {
        id: crypto.randomUUID(),
        groupId: groupRef.id,
        accountId: groupRef.id, // group is the account itself now
        amount: accountType.value === 'credit_card' ? -doubleInitialBalance : doubleInitialBalance,
        description: 'Opening Balance Setup',
        category: 'Salary & Deposit',
        date: Timestamp.fromDate(new Date()),
        createdAt: Timestamp.now(),
        type: accountType.value === 'credit_card' ? 'expense' : 'deposit'
      };
      await setDoc(doc(db, 'groups', groupRef.id, 'account_transactions', initialTx.id), initialTx);
    }

    // 2. Add the creator as an admin member
    await setDoc(doc(db, 'groups', groupRef.id, 'members', props.user.uid), {
      uid: props.user.uid,
      role: 'admin',
      joinedAt: serverTimestamp(),
      displayName: props.user.displayName,
      email: props.user.email,
    });

    emit('close');
    name.value = '';
    description.value = '';
    type.value = 'household';
    maxBudget.value = '';
    budgetType.value = 'monthly';
    accountType.value = 'checking';
    bankName.value = '';
    initialBalance.value = '';
    creditLimit.value = '';
    selectedCardColor.value = 'slate';
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, 'groups');
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <transition name="fade">
    <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div @click="$emit('close')" class="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      
      <div class="relative w-full max-w-lg bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-[32px] shadow-2xl overflow-y-auto max-h-[90vh] outline-none z-10 transition-all">
        <div class="p-10">
          <div class="flex items-center justify-between mb-10">
            <h2 id="modal-title" class="text-3xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">
              {{ service === 'accounts' ? 'New Account / Card Setup' : service === 'loans_debts' ? 'New Loan & Debt Tracker Ledger' : service === 'mortgages' ? 'New Property Mortgage Tracker' : service === 'rent' ? 'New Rent Management Ledger' : service === 'document_vault' ? 'New Document Cabinet' : 'Create New Group' }}
            </h2>
            <button 
              @click="$emit('close')" 
              class="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl transition-colors text-zinc-400 dark:text-zinc-500 hover:text-zinc-900 dark:hover:text-white outline-none cursor-pointer border-none bg-transparent"
              aria-label="Close modal"
            >
              <X class="w-6 h-6" />
            </button>
          </div>

          <form @submit.prevent="handleSubmit" class="space-y-8">
            <!-- CARDS & ACCOUNTS SPECIALIZED FORM -->
            <template v-if="service === 'accounts'">
              <!-- Account Name -->
              <div>
                <label for="acc-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Account / Card Name</label>
                <input
                  id="acc-name"
                  type="text"
                  v-model="name"
                  placeholder="e.g. Sapphire Preferred, Active Checking"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                  required
                  autoFocus
                />
              </div>

              <!-- Asset/Liability Type -->
              <div>
                <label for="acc-type" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Asset/Liability Type</label>
                <select
                  id="acc-type"
                  v-model="accountType"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                  required
                >
                  <option value="checking">Checking / Current Account</option>
                  <option value="savings">Savings Account</option>
                  <option value="credit_card">Credit Card Account</option>
                  <option value="debit_card">Debit Card Account</option>
                </select>
              </div>

              <!-- Bank Name & Initial Balance -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label for="bank-name" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Bank Name</label>
                  <input
                    id="bank-name"
                    type="text"
                    v-model="bankName"
                    placeholder="e.g. Chase, HSBC, Wells Fargo"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold text-zinc-900 dark:text-white"
                  />
                </div>
                <div>
                  <label for="initial-balance" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Initial Balance</label>
                  <input
                    id="initial-balance"
                    type="number"
                    step="0.01"
                    v-model="initialBalance"
                    placeholder="0.00"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                  />
                </div>
              </div>

              <!-- Outstanding Credit Limit -->
              <div v-if="accountType === 'credit_card'">
                <label for="credit-limit" class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-3 font-display">Outstanding Credit Limit</label>
                <input
                  id="credit-limit"
                  type="number"
                  step="0.01"
                  v-model="creditLimit"
                  placeholder="5000.00"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-805 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 font-bold font-mono text-zinc-900 dark:text-white"
                  required
                />
              </div>

              <!-- Currency Code -->
              <div>
                <label class="block text-[10px] font-bold text-zinc-500 mb-3 uppercase tracking-wider font-display">Account Currency</label>
                <select
                  v-model="currencyCode"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-850 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
                >
                  <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }} ({{ c.symbol }})</option>
                </select>
              </div>

              <!-- Card Aesthetics -->
              <div>
                <label class="block text-[10px] font-bold text-zinc-400 uppercase tracking-[0.2em] mb-4 font-display">Card Aesthetics Theme</label>
                <div class="grid grid-cols-2 sm:grid-cols-5 gap-3">
                  <button 
                    v-for="color in cardColors" 
                    :key="color.id" 
                    type="button" 
                    @click="selectedCardColor = color.id"
                    class="p-4 rounded-2xl flex flex-col items-center justify-center border-2 transition-all cursor-pointer text-center bg-transparent"
                    :class="selectedCardColor === color.id ? 'border-teal-500 bg-zinc-50 dark:bg-zinc-950 shadow-md scale-102' : 'border-zinc-205 dark:border-zinc-850'"
                  >
                    <div class="w-6 h-6 rounded-full shrink-0" :class="color.bg" />
                    <span class="text-[9px] font-bold mt-2 text-zinc-500 dark:text-zinc-400 whitespace-nowrap">{{ color.id.toUpperCase() }}</span>
                  </button>
                </div>
              </div>
            </template>

            <!-- TRADITIONAL FINANCIAL GROUPS FORM -->
            <template v-else>
              <div>
                <label for="group-name" class="block text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-3 font-display">Group Name</label>
                <input
                  id="group-name"
                  type="text"
                  v-model="name"
                  placeholder="e.g., Summer Trip 24, Roommates"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-medium text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label for="group-desc" class="block text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-3 font-display">Description (Optional)</label>
                <textarea
                  id="group-desc"
                  v-model="description"
                  placeholder="What is this group for?"
                  class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all resize-none h-28 font-medium text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600"
                />
              </div>

              <div v-if="showPurposeSelection">
                <label class="block text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 font-display">Group Purpose</label>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <button
                    type="button"
                    @click="service = 'budget'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'budget'
                        ? 'bg-indigo-50/50 dark:bg-indigo-500/15 border-indigo-500 text-indigo-700 dark:text-indigo-400 shadow-md shadow-indigo-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Budget & Expenses</span>
                    <span class="text-[10px] opacity-75">Track bills & shared expenses</span>
                  </button>

                  <button
                    type="button"
                    @click="service = 'savings'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'savings'
                        ? 'bg-teal-50/50 dark:bg-teal-500/15 border-teal-500 text-teal-700 dark:text-teal-400 shadow-md shadow-teal-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Savings Goals Hub</span>
                    <span class="text-[10px] opacity-75">Aggregate saving campaigns</span>
                  </button>

                  <button
                    type="button"
                    @click="service = 'income'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'income'
                        ? 'bg-emerald-50/50 dark:bg-emerald-500/15 border-emerald-500 text-emerald-700 dark:text-emerald-400 shadow-md shadow-emerald-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Target & Income</span>
                    <span class="text-[10px] opacity-75">Track income streams & inflows</span>
                  </button>

                  <button
                    type="button"
                    @click="service = 'loans_debts'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'loans_debts'
                        ? 'bg-amber-50/50 dark:bg-amber-500/15 border-amber-500 text-amber-700 dark:text-amber-400 shadow-md shadow-amber-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Loans & Debts Ledger</span>
                    <span class="text-[10px] opacity-75">Track borrowed & lent assets</span>
                  </button>

                  <button
                    type="button"
                    @click="service = 'mortgages'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'mortgages'
                        ? 'bg-indigo-50/50 dark:bg-indigo-500/15 border-indigo-505 text-indigo-700 dark:text-indigo-400 shadow-md shadow-indigo-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Property Mortgages</span>
                    <span class="text-[10px] opacity-75">Track home & asset mortgages</span>
                  </button>

                  <button
                    type="button"
                    @click="service = 'rent'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'rent'
                        ? 'bg-teal-50/55 dark:bg-teal-500/15 border-teal-500 text-teal-700 dark:text-teal-450 shadow-md shadow-teal-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Rent Management</span>
                    <span class="text-[10px] opacity-75">Track property leases & rent schedules</span>
                  </button>

                  <button
                    type="button"
                    @click="service = 'document_vault'"
                    :class="`flex flex-col items-start gap-1 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer text-left ${
                      service === 'document_vault'
                        ? 'bg-indigo-50/55 dark:bg-indigo-500/15 border-indigo-500 text-indigo-700 dark:text-indigo-400 shadow-md shadow-indigo-500/5'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-805 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <span class="font-bold text-sm">Document Cabinets</span>
                    <span class="text-[10px] opacity-75">Secure PDFs, bank statements & text receipts</span>
                  </button>
                </div>
              </div>

              <div v-if="service !== 'loans_debts' && service !== 'mortgages' && service !== 'rent' && service !== 'document_vault'">
                <label class="block text-[10px] font-bold text-zinc-500 uppercase tracking-[0.2em] mb-4 font-display">Group Type</label>
                
                <!-- Income Specific Group Types -->
                <div v-if="service === 'income'" class="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    @click="type = 'employment'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'employment'
                        ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 shadow-lg shadow-emerald-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <DollarSign :class="`w-5 h-5 ${type === 'employment' ? 'text-emerald-600 dark:text-emerald-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Employment / Wages</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'freelance'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'freelance'
                        ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-500 text-blue-700 dark:text-blue-400 shadow-lg shadow-blue-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <Laptop :class="`w-5 h-5 ${type === 'freelance' ? 'text-blue-600 dark:text-blue-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Freelance / Gig</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'business'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'business'
                        ? 'bg-purple-50 dark:bg-purple-500/10 border-purple-500 text-purple-700 dark:text-purple-400 shadow-lg shadow-purple-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <Store :class="`w-5 h-5 ${type === 'business' ? 'text-purple-600 dark:text-purple-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Business / SaaS</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'investment'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'investment'
                        ? 'bg-orange-50 dark:bg-orange-500/10 border-orange-500 text-orange-700 dark:text-orange-400 shadow-lg shadow-orange-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <TrendingUp :class="`w-5 h-5 ${type === 'investment' ? 'text-orange-600 dark:text-orange-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-xs">Investments / rent</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'other'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer col-span-2 bg-transparent text-left ${
                      type === 'other'
                        ? 'bg-indigo-50 dark:bg-indigo-500/10 border-indigo-500 text-indigo-700 dark:text-indigo-400 shadow-lg shadow-indigo-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <Sparkles :class="`w-5 h-5 ${type === 'other' ? 'text-indigo-600 dark:text-indigo-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Other Inflow Sources</span>
                  </button>
                </div>

                <!-- Standard Budgeting / Savings Group Types -->
                <div v-else class="grid grid-cols-2 gap-4">
                  <button
                    type="button"
                    @click="type = 'household'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'household'
                        ? 'bg-emerald-50 dark:bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 shadow-lg shadow-emerald-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <Home :class="`w-5 h-5 ${type === 'household' ? 'text-emerald-600 dark:text-emerald-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Household</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'trip'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'trip'
                        ? 'bg-orange-50 dark:bg-orange-500/10 border-orange-500 text-orange-700 dark:text-orange-400 shadow-lg shadow-orange-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <Plane :class="`w-5 h-5 ${type === 'trip' ? 'text-orange-600 dark:text-orange-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Trip</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'personal'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'personal'
                        ? 'bg-blue-50 dark:bg-blue-500/10 border-blue-500 text-blue-700 dark:text-blue-400 shadow-lg shadow-blue-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-300 dark:hover:border-zinc-700'
                    }`"
                  >
                    <Users :class="`w-5 h-5 ${type === 'personal' ? 'text-blue-600 dark:text-blue-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Personal</span>
                  </button>

                  <button
                    type="button"
                    @click="type = 'other'"
                    :class="`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-300 outline-none cursor-pointer bg-transparent text-left ${
                      type === 'other'
                        ? 'bg-indigo-50 dark:bg-indigo-500/10 border-indigo-500 text-indigo-700 dark:text-indigo-400 shadow-lg shadow-indigo-500/10'
                        : 'bg-zinc-50 dark:bg-zinc-950 border-zinc-200 dark:border-zinc-800 text-zinc-500 hover:border-zinc-350 dark:hover:border-zinc-750'
                    }`"
                  >
                    <Briefcase :class="`w-5 h-5 ${type === 'other' ? 'text-indigo-600 dark:text-indigo-400' : 'text-zinc-400 dark:text-zinc-600'}`" />
                    <span class="font-bold text-sm">Other</span>
                  </button>
                </div>
              </div>

              <div v-if="service === 'loans_debts' || service === 'mortgages' || service === 'rent' || service === 'document_vault'" class="pt-8 border-t border-zinc-100 dark:border-zinc-800">
                <label class="block text-[10px] font-bold text-zinc-500 mb-3 uppercase tracking-wider font-display">Ledger Default Currency</label>
                <div class="relative">
                  <select
                    v-model="currencyCode"
                    class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
                  >
                    <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }} ({{ c.symbol }})</option>
                  </select>
                </div>
              </div>

              <div v-else class="pt-8 border-t border-zinc-100 dark:border-zinc-800">
                <h3 class="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-500 mb-6 font-display">Budget Settings (Optional)</h3>
                <div class="space-y-6">
                  <div>
                    <label class="block text-[10px] font-bold text-zinc-500 mb-3 uppercase tracking-wider font-display">Budget Currency & Limit</label>
                    <div class="flex gap-3">
                      <div class="relative flex-1">
                        <span class="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-400 dark:text-zinc-600 font-mono font-bold">
                          {{ getCurrencySymbol(currencyCode) }}
                        </span>
                        <input
                          id="max-budget"
                          type="number"
                          step="0.01"
                          v-model="maxBudget"
                          placeholder="No limit"
                          class="w-full pl-10 pr-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-mono font-bold text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 shadow-inner"
                        />
                      </div>
                      <div class="w-32 shrink-0">
                        <select
                          v-model="currencyCode"
                          class="w-full px-4 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all font-bold text-zinc-900 dark:text-white appearance-none cursor-pointer"
                        >
                          <option v-for="c in CURRENCIES" :key="c.code" :value="c.code">{{ c.code }}</option>
                        </select>
                      </div>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="budget-freq" class="block text-[10px] font-bold text-zinc-500 mb-3 uppercase tracking-wider font-display">Frequency</label>
                    <select
                      id="budget-freq"
                      v-model="budgetType"
                      class="w-full px-5 py-4 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all appearance-none font-bold text-zinc-900 dark:text-white cursor-pointer"
                    >
                      <option value="weekly">Per Week</option>
                      <option value="monthly">Per Month</option>
                      <option value="total">Total</option>
                    </select>
                  </div>
                </div>
              </div>
            </template>

            <button
              type="submit"
              :disabled="isSubmitting"
              class="w-full py-5 bg-gradient-to-br from-indigo-600 to-violet-600 text-white rounded-2xl font-bold hover:from-indigo-700 hover:to-violet-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-4 shadow-xl shadow-indigo-500/20 active:scale-[0.98] outline-none cursor-pointer focus:ring-4 focus:ring-indigo-500/40"
            >
              {{ isSubmitting ? 'Creating...' : service === 'accounts' ? 'Assemble Bank Account / Card' : service === 'loans_debts' ? 'Initialize Loan Ledger' : service === 'mortgages' ? 'Initialize Mortgage Broker' : service === 'rent' ? 'Initialize Rent Ledger' : service === 'document_vault' ? 'Initialize Cabinet Vault' : 'Create Group' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  </transition>
</template>
