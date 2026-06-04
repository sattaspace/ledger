<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { 
  DollarSign, 
  Search, 
  Phone, 
  Calendar, 
  Truck, 
  User, 
  ChevronRight, 
  CheckCircle, 
  Coins, 
  Clock,
  UserCheck,
  X,
  ChevronDown,
  ChevronUp
} from 'lucide-vue-next';
import type { SaleRecord } from '../types';

const props = withDefaults(defineProps<{
  sales: SaleRecord[];
  formatCurrency?: (amt: number) => string;
}>(), {});

const emit = defineEmits<{
  (e: 'collectPayment', saleId: string, amount: number, receivedBy: string): void;
  (e: 'closeWithDue', saleId: string): void;
  (e: 'refreshData'): void;
}>();

const searchQuery = ref('');
const selectedSale = ref<SaleRecord | null>(null);

// Collect Form fields
const amount = ref('');
const receivedBy = ref('');
const formError = ref('');
const formSuccess = ref('');
const isSubmitting = ref(false);

// Pagination states for all 3 sub-tabs
const individualPage = ref(1);
const vehiclesPage = ref(1);
const repsPage = ref(1);
const itemsPerPage = 8;

// Track expanded row details
const expandedInvoiceId = ref<string | null>(null);
const expandedVehicleNumber = ref<string | null>(null);
const expandedRepName = ref<string | null>(null);

const closingInvoiceSale = ref<SaleRecord | null>(null);
const isClosingSubmitting = ref(false);
const errorClosing = ref('');

// Reset pages whenever search query shifts
watch(searchQuery, () => {
  individualPage.value = 1;
  vehiclesPage.value = 1;
  repsPage.value = 1;
});

const handleCloseWithDue = (sale: SaleRecord) => {
  const balanceDue = sale.totalAmount - sale.amountPaid;
  if (balanceDue <= 0) return;
  closingInvoiceSale.value = sale;
  errorClosing.value = '';
};

const handleConfirmClose = async () => {
  if (!closingInvoiceSale.value) return;
  isClosingSubmitting.value = true;
  errorClosing.value = '';
  try {
    // Notify parent to trigger standard closeWithDue endpoint flow
    emit('closeWithDue', closingInvoiceSale.value.id);
    
    // Auto-timeout success
    setTimeout(() => {
      closingInvoiceSale.value = null;
      emit('refreshData');
    }, 1000);
  } catch (err: any) {
    errorClosing.value = err.message || 'Error writing off dues.';
  } finally {
    isClosingSubmitting.value = false;
  }
};

const formatCurrency = computed(() => {
  return props.formatCurrency || ((amt: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  });
});

// Filter credits
const pendingCreditSales = computed(() => {
  return (props.sales || []).filter(s => 
    s.paymentType === 'Credit' && s.collectionStatus !== 'Fully Paid' && !s.isClosedWithDue
  );
});

const filteredPending = computed(() => {
  const q = searchQuery.value.toLowerCase().trim();
  if (!q) return pendingCreditSales.value;

  return pendingCreditSales.value.filter(s => {
    return s.customerName.toLowerCase().includes(q) || 
           s.productName.toLowerCase().includes(q) || 
           (s.vehicleNumber || '').toLowerCase().includes(q) || 
           (s.dsrName || '').toLowerCase().includes(q);
  });
});

const handleCollectSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';

  if (!selectedSale.value) return;

  const amt = Number(amount.value);
  const balanceDue = selectedSale.value.totalAmount - selectedSale.value.amountPaid;

  if (!amount.value || isNaN(amt) || amt <= 0) {
    formError.value = 'Please enter a valid amount greater than ₹0!';
    return;
  }

  if (amt > balanceDue) {
    formError.value = `Cannot collect more than balance due. Max Collectible: ${formatCurrency.value(balanceDue)}`;
    return;
  }

  if (!receivedBy.value) {
    formError.value = 'Please input who is receiving or registering this cash collection!';
    return;
  }

  isSubmitting.value = true;
  try {
    emit('collectPayment', selectedSale.value.id, amt, receivedBy.value);
    
    formSuccess.value = `Outstanding Payment of ${formatCurrency.value(amt)} successfully credited!`;
    amount.value = '';
    receivedBy.value = '';
    
    setTimeout(() => {
      selectedSale.value = null;
      formSuccess.value = '';
      emit('refreshData');
    }, 1800);
  } catch (err: any) {
    formError.value = err.message || 'Error processing ledger.';
  } finally {
    isSubmitting.value = false;
  }
};

const activeSubTab = ref<'individual' | 'vehicles' | 'reps'>('individual');

// Group vehicle stats dynamically
const vehicleGroups = computed(() => {
  const groups: { [key: string]: { total: number; pending: number; count: number } } = {};
  (props.sales || []).forEach(sale => {
    if (sale.isVehicle && sale.vehicleNumber) {
      const v = sale.vehicleNumber.trim().toUpperCase();
      if (!groups[v]) {
        groups[v] = { total: 0, pending: 0, count: 0 };
      }
      groups[v].total += sale.totalAmount;
      if (!sale.isClosedWithDue) {
        groups[v].pending += (sale.totalAmount - sale.amountPaid);
      }
      groups[v].count += 1;
    }
  });

  return Object.entries(groups).map(([vehicle, stats]) => ({
    vehicle,
    ...stats
  })).sort((a, b) => b.pending - a.pending);
});

// Group representative stats dynamically
const repGroups = computed(() => {
  const groups: { [key: string]: { name: string; total: number; pending: number; count: number } } = {};
  (props.sales || []).forEach(sale => {
    const repId = sale.dsrId || 'counter';
    const repName = sale.dsrName || 'Direct Dealer Counter';
    if (!groups[repId]) {
      groups[repId] = { name: repName, total: 0, pending: 0, count: 0 };
    }
    groups[repId].total += sale.totalAmount;
    if (!sale.isClosedWithDue) {
      groups[repId].pending += (sale.totalAmount - sale.amountPaid);
    }
    groups[repId].count += 1;
  });

  return Object.values(groups).sort((a, b) => b.pending - a.pending);
});

// Pagination calculations
// 1. Individual
const individualTotalPages = computed(() => Math.ceil(filteredPending.value.length / itemsPerPage));
const currentIndividualSales = computed(() => {
  const start = (individualPage.value - 1) * itemsPerPage;
  return filteredPending.value.slice(start, start + itemsPerPage);
});
const individualFirst = computed(() => (individualPage.value - 1) * itemsPerPage);

// 2. Vehicles
const activePendingVehicles = computed(() => vehicleGroups.value.filter(v => v.pending > 0));
const vehiclesTotalPages = computed(() => Math.ceil(activePendingVehicles.value.length / itemsPerPage));
const currentVehicles = computed(() => {
  const start = (vehiclesPage.value - 1) * itemsPerPage;
  return activePendingVehicles.value.slice(start, start + itemsPerPage);
});
const vehiclesFirst = computed(() => (vehiclesPage.value - 1) * itemsPerPage);

// 3. Reps
const repsTotalPages = computed(() => Math.ceil(repGroups.value.length / itemsPerPage));
const currentReps = computed(() => {
  const start = (repsPage.value - 1) * itemsPerPage;
  return repGroups.value.slice(start, start + itemsPerPage);
});
const repsFirst = computed(() => (repsPage.value - 1) * itemsPerPage);

// Outstanding total
const totalOutstandingSum = computed(() => {
  return pendingCreditSales.value.reduce((acc, curr) => acc + (curr.totalAmount - curr.amountPaid), 0);
});
</script>

<template>
  <div class="space-y-4 font-sans text-left animate-fadeIn">
    <!-- HEADER SECTION -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-2.5">
      <div>
        <h2 class="text-lg md:text-xl font-display font-bold text-slate-800">📞 Credit Collections & Follow-up Ledger</h2>
        <p class="text-[11px] text-slate-500 font-sans mt-0.5 font-medium">Reconcile vehicle drops, track outlet-specific pending collection amounts, and monitor DSR responsible followup cash</p>
      </div>

      <!-- Outstanding balance metrics -->
      <div class="bg-rose-50 border border-rose-150 rounded px-3 py-1.5 flex flex-col justify-center text-right shadow-xs select-none">
        <p class="text-[10px] text-rose-850 font-bold uppercase tracking-wider font-mono">Total Debts Outstanding</p>
        <p class="text-sm md:text-base font-display font-black text-rose-600 font-mono mt-0.5">{{ formatCurrency(totalOutstandingSum) }}</p>
      </div>
    </div>

    <!-- SUB TAB NAVIGATION CONTROLS -->
    <div class="grid grid-cols-3 gap-1 bg-slate-105 p-1 rounded border border-slate-200 shadow-xs max-w-2xl">
      <button
        id="tab-sub-individual"
        type="button"
        @click="activeSubTab = 'individual'"
        :class="['py-1.5 px-2 rounded text-[10px] font-display font-bold transition flex items-center justify-center space-x-1.5 cursor-pointer leading-none',
          activeSubTab === 'individual'
            ? 'bg-white text-slate-900 shadow-xs font-black'
            : 'text-slate-650 hover:bg-white/40'
        ]"
      >
        <Coins class="h-3.5 w-3.5 text-blue-600" />
        <span>Outlet Invoices ({{ filteredPending.length }})</span>
      </button>

      <button
        id="tab-sub-vehicles"
        type="button"
        @click="activeSubTab = 'vehicles'"
        :class="['py-1.5 px-2 rounded text-[10px] font-display font-bold transition flex items-center justify-center space-x-1.5 cursor-pointer leading-none',
          activeSubTab === 'vehicles'
            ? 'bg-white text-slate-900 shadow-xs font-black'
            : 'text-slate-650 hover:bg-white/40'
        ]"
      >
        <Truck class="h-3.5 w-3.5 text-amber-600 shrink-0" />
        <span>Vehicle-Wise Rollups ({{ pendingVehiclesCount = activePendingVehicles.length }})</span>
      </button>

      <button
        id="tab-sub-reps"
        type="button"
        @click="activeSubTab = 'reps'"
        :class="['py-1.5 px-2 rounded text-[10px] font-display font-bold transition flex items-center justify-center space-x-1.5 cursor-pointer leading-none',
          activeSubTab === 'reps'
            ? 'bg-white text-slate-900 shadow-xs font-black'
            : 'text-slate-650 hover:bg-white/40'
        ]"
      >
        <User class="h-3.5 w-3.5 text-cyan-600 shrink-0" />
        <span>Rep / DSR Liability</span>
      </button>
    </div>

    <!-- FILTER CARDS -->
    <div v-if="activeSubTab === 'individual'" class="bg-white p-3 rounded border border-slate-200 shadow-xs flex items-center">
      <div class="relative w-full">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="Search debtor store name, plate number, or representing salesperson..." 
          v-model="searchQuery"
          class="w-full text-xs pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-sans"
        />
      </div>
    </div>

    <!-- PAYMENT COLLECTION DIALOG PANEL -->
    <div v-if="selectedSale" class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-3 animate-fadeIn font-sans">
      <div class="flex justify-between items-center pb-2 border-b border-slate-100">
        <h3 class="font-display font-bold text-slate-800 text-xs md:text-sm flex items-center space-x-2">
          <DollarSign class="h-4.5 w-4.5 text-rose-600" />
          <span>Record Collections Cash Payment</span>
        </h3>
        <button 
          id="col-btn-close-form"
          @click="selectedSale = null" 
          class="text-slate-450 hover:text-slate-700 cursor-pointer"
        >
          <X class="h-4.5 w-4.5" />
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <!-- Details Reference Box -->
        <div class="p-3 bg-slate-50 border border-slate-200 rounded space-y-2 text-[11px] text-slate-650">
          <h4 class="font-display font-bold text-slate-800 text-xs uppercase tracking-wider">Sale Reference Details</h4>
          <p>📍 <span class="font-bold text-slate-500 font-mono text-[10px]">CUSTOMER:</span> <span class="font-black text-slate-850">{{ selectedSale.customerName }} ({{ selectedSale.customerPhone || 'N/A' }})</span></p>
          <p>📦 <span class="font-bold text-slate-500 font-mono text-[10px]">PRODUCT:</span> <span class="font-bold text-slate-850">{{ selectedSale.productName }} (Qty: {{ selectedSale.quantity }} units)</span></p>
          <p>🏷️ <span class="font-bold text-slate-500 font-mono text-[10px]">TRACK METHOD:</span>{' '}
            <span v-if="selectedSale.isVehicle" class="font-bold text-blue-700 uppercase">Vehicle Plate {{ selectedSale.vehicleNumber }}</span>
            <span v-else class="font-bold text-cyan-800 uppercase">Representative {{ selectedSale.dsrName }}</span>
          </p>
          <div class="pt-2 border-t border-slate-200 grid grid-cols-2 gap-2 text-center text-[10px]">
            <div>
              <p class="text-slate-400 font-bold uppercase tracking-wider">Original Bill</p>
              <p class="font-black text-slate-800 mt-1 font-mono">{{ formatCurrency(selectedSale.totalAmount) }}</p>
            </div>
            <div>
              <p class="text-rose-600 font-bold uppercase tracking-wider">Outstanding Left</p>
              <p class="font-black text-rose-600 mt-1 font-mono text-xs">
                {{ formatCurrency(selectedSale.totalAmount - selectedSale.amountPaid) }}
              </p>
            </div>
          </div>
        </div>

        <!-- Form fields -->
        <form @submit.prevent="handleCollectSubmit" class="space-y-3">
          <div class="space-y-1">
            <label class="text-[10px] font-bold text-rose-800 uppercase tracking-wider">
              Amount Cash Collected (₹) *
            </label>
            <input 
              type="number" 
              :placeholder="`Max outstanding balance to pay is ${selectedSale.totalAmount - selectedSale.amountPaid}`"
              v-model="amount"
              class="w-full text-xs p-2 border border-rose-250 rounded bg-rose-50/10 font-black text-rose-850 font-mono focus:outline-none"
            />
          </div>

          <div class="space-y-1">
            <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider">
              Collected By / Cash Receiver Staff *
            </label>
            <input 
              type="text" 
              placeholder="e.g. Sanjay Sharma, DSR name, or Counter Desk" 
              v-model="receivedBy"
              class="w-full text-xs p-2 border border-slate-200 rounded font-sans"
            />
          </div>

          <div class="flex justify-end space-x-2 pt-1.5 border-t border-slate-100 items-center">
            <p v-if="formError" class="text-[11px] text-rose-650 font-semibold font-mono mr-auto leading-none">⚠️ {{ formError }}</p>
            <p v-if="formSuccess" class="text-[11px] text-emerald-655 font-bold font-sans mr-auto leading-none animate-pulse">✨ {{ formSuccess }}</p>
            
            <button 
              id="col-btn-form-cancel"
              type="button" 
              @click="selectedSale = null" 
              class="px-3 py-1.5 border border-slate-200 rounded text-xs cursor-pointer hover:bg-slate-50 font-bold"
            >
              Cancel
            </button>
            <button 
              id="col-btn-form-save"
              type="submit" 
              :disabled="isSubmitting"
              class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-bold cursor-pointer disabled:opacity-50"
            >
              {{ isSubmitting ? 'Saving...' : 'Record Collected' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- INDIVIDUAL OUTLET DEBTS TAB -->
    <div v-if="activeSubTab === 'individual'" class="space-y-3">
      <div class="bg-white rounded border border-slate-200 overflow-hidden shadow-xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-sans border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-extrabold tracking-wider">
                <th class="py-3 px-4 w-[6%] text-center">Detail</th>
                <th class="py-3 px-4 w-[28%] text-left">Store Name</th>
                <th class="py-3 px-4 w-[24%]">Product Issued</th>
                <th class="py-3 px-4 w-[16%]">Billing Track</th>
                <th class="py-3 px-4 w-[12%] text-right font-mono text-rose-655">Outstanding</th>
                <th class="py-3 px-4 w-[14%] text-center">Due Date</th>
                <th class="py-3 px-4 w-[22%] text-center">Recovery Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150">
              <template v-for="sale in currentIndividualSales" :key="sale.id">
                <tr :class="['hover:bg-slate-50/50 transition border-b border-slate-100', expandedInvoiceId === sale.id ? 'bg-slate-50/60' : '']">
                  <!-- Toggle Expansion trigger -->
                  <td class="py-3 px-4 text-center">
                    <button
                      :id="`col-btn-toggle-detail-${sale.id}`"
                      @click="expandedInvoiceId = expandedInvoiceId === sale.id ? null : sale.id"
                      class="p-1 rounded text-slate-500 hover:bg-slate-100 transition cursor-pointer"
                    >
                      <ChevronUp v-if="expandedInvoiceId === sale.id" class="h-4.5 w-4.5 text-rose-600" />
                      <ChevronDown v-else class="h-4.5 w-4.5 text-slate-500 hover:text-blue-600" />
                    </button>
                  </td>

                  <!-- Customer / Store Identity -->
                  <td class="py-3 px-4 font-bold">
                    <div class="space-y-0.5 whitespace-normal">
                      <span class="font-display font-black text-slate-800 text-xs block" :title="sale.customerName">
                        {{ sale.customerName }}
                      </span>
                      <span class="text-[10px] text-slate-450 font-medium block">
                        📞 {{ sale.customerPhone || 'N/A' }}
                      </span>
                    </div>
                  </td>

                  <!-- Items load description -->
                  <td class="py-3 px-4 text-slate-700">
                    <div class="font-medium text-xs font-semibold whitespace-normal">
                      {{ sale.productName }}
                      <span class="ml-1 bg-slate-100 text-slate-700 px-1.5 py-0.2 rounded-sm text-[10px] font-bold">
                        x{{ sale.quantity }}
                      </span>
                    </div>
                  </td>

                  <!-- Transportation vehicle drop or representative -->
                  <td class="py-3 px-4">
                    <span v-if="sale.isVehicle" class="bg-blue-50 border border-blue-100 text-blue-800 font-mono text-[9px] px-1.5 py-0.5 rounded leading-none font-black inline-flex items-center uppercase tracking-wide">
                      <Truck class="h-2.5 w-2.5 mr-1" />
                      {{ sale.vehicleNumber }}
                    </span>
                    <span v-else class="bg-cyan-50 border border-cyan-100 text-cyan-850 text-[9px] px-1.5 py-0.5 rounded leading-none inline-flex items-center font-black uppercase tracking-wide">
                      <UserCheck class="h-2.5 w-2.5 mr-1" />
                      {{ sale.dsrName }}
                    </span>
                  </td>

                  <!-- Credit outstanding metrics -->
                  <td class="py-3 px-4 text-right font-black font-semibold font-mono text-xs text-rose-600">
                    {{ formatCurrency(sale.totalAmount - sale.amountPaid) }}
                  </td>

                  <!-- Date repayment limits -->
                  <td class="py-3 px-4 text-center text-[10px] font-bold">
                    <span class="bg-rose-50 text-rose-700 border border-rose-100 px-2 py-0.5 rounded leading-none">
                      {{ sale.dueDate ? new Date(sale.dueDate).toLocaleDateString() : 'No repayment date' }}
                    </span>
                  </td>

                  <!-- Trigger Payment forms button -->
                  <td class="py-3 px-4">
                    <div class="flex gap-1.5 justify-center">
                      <button
                        :id="`col-btn-trigger-${sale.id}`"
                        @click="() => {
                          selectedSale = sale;
                          amount = '';
                          receivedBy = sale.dsrName || 'Counter Staff';
                          window.scrollTo({ top: 0, behavior: 'smooth' });
                        }"
                        class="bg-rose-50 hover:bg-rose-100 text-rose-800 text-[10px] font-display font-medium px-2 py-1 rounded border border-rose-150 flex items-center space-x-1 cursor-pointer transition shadow-xs"
                      >
                        <Coins class="h-3 w-3" />
                        <span>Collect Cash</span>
                      </button>

                      <button
                        :id="`col-btn-close-due-${sale.id}`"
                        @click="handleCloseWithDue(sale)"
                        class="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[10px] font-display font-black px-2 py-1 rounded border border-emerald-250 flex items-center space-x-1 cursor-pointer transition shadow-xs animate-fadeIn"
                        title="Instantly close outstanding invoice with remaining balance written off"
                      >
                        <span>Close with Due</span>
                      </button>
                    </div>
                  </td>
                </tr>

                <!-- Accordion collapsible details panel -->
                <tr v-if="expandedInvoiceId === sale.id" class="bg-slate-50/40">
                  <td colSpan="7" class="py-3 px-6 border-y border-slate-100 font-sans">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-white rounded border border-slate-200 p-3.5 shadow-xs">
                      <div class="text-left">
                        <h4 class="font-display font-bold text-slate-800 text-xs mb-2">📄 Outlet Invoice Recovery Summary</h4>
                        <div class="space-y-1.5 text-[11px] text-slate-550 font-semibold">
                          <p>🛡️ <span class="text-slate-400 font-bold">Invoice Unique ID:</span> <span class="font-mono font-bold text-slate-700">{{ sale.id }}</span></p>
                          <p>📅 <span class="text-slate-400 font-bold">Billing Issuance Date:</span> <span class="text-slate-700">{{ new Date(sale.date).toLocaleString() }}</span></p>
                          <p>🛠️ <span class="text-slate-400 font-bold">Initial Cargo Invoice Total:</span> <span class="text-slate-700 font-mono">{{ formatCurrency(sale.totalAmount) }}</span></p>
                          <p>💵 <span class="text-slate-400 font-bold">Downpayment Paid Initially:</span> <span class="text-slate-700 font-mono">{{ formatCurrency(sale.amountPaid - (sale.payments ? sale.payments.reduce((a, p) => a + p.amount, 0) : 0)) }}</span></p>
                          <p>💸 <span class="text-rose-500 font-bold">Current Debts Owed:</span> <span class="text-rose-650 font-extrabold font-mono text-xs">{{ formatCurrency(sale.totalAmount - sale.amountPaid) }}</span></p>
                        </div>
                      </div>

                      <div class="text-left">
                        <h4 class="font-display font-bold text-slate-800 text-xs mb-2">📋 Ledger Payments Log ({{ sale.payments?.length || 0 }} Partial Collections)</h4>
                        <div v-if="sale.payments && sale.payments.length > 0" class="border border-slate-150 rounded overflow-hidden max-h-40 overflow-y-auto">
                          <table class="w-full text-left text-[11px] font-sans">
                            <thead>
                              <tr class="bg-slate-50 border-b border-slate-200 text-slate-450 font-bold uppercase text-[9px]">
                                <th class="py-1 px-2.5">Collected Date</th>
                                <th class="py-1 px-2.5 text-right">Amount Credited</th>
                                <th class="py-1 px-2.5">Received By</th>
                              </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 text-slate-755 font-semibold">
                              <tr v-for="(pRecord, pIdx) in sale.payments" :key="pIdx">
                                <td class="py-1 px-2.5 text-slate-500">{{ new Date(pRecord.date).toLocaleDateString() }}</td>
                                <td class="py-1 px-2.5 text-right font-mono text-emerald-650 font-bold">+{{ formatCurrency(pRecord.amount) }}</td>
                                <td class="py-1 px-2.5 text-slate-650">{{ pRecord.receivedBy }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <div v-else class="flex flex-col items-center justify-center p-4 border border-dashed border-slate-250 rounded text-center text-slate-400 bg-slate-50/50">
                          <Coins class="h-4 w-4 text-slate-300 mb-1" />
                          <p class="font-medium text-[10px]">No partial cash collections registered yet.</p>
                          <p class="text-[9px]">Use "Collect Cash" to log partial payments from this client store.</p>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>

              <tr v-if="currentIndividualSales.length === 0">
                <td colSpan="7" class="text-center py-10 bg-white">
                  <CheckCircle class="h-7 w-7 text-emerald-500 mx-auto mb-2 animate-bounce" />
                  <p class="font-display font-semibold text-slate-750 text-xs">No pending collections found!</p>
                  <p class="text-[11px] text-slate-400 font-sans">Everything has been recovered and reconciled.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- individual page indices footer -->
        <div v-if="individualTotalPages > 1" class="bg-slate-50 border-t border-slate-200 px-4 py-2.5 flex items-center justify-between sm:px-6 font-sans">
          <p class="text-xs text-slate-500">
            Showing <span class="font-semibold">{{ individualFirst + 1 }}</span> to{' '}
            <span class="font-semibold">
              {{ Math.min(individualFirst + itemsPerPage, filteredPending.length) }}
            </span>{' '}
            of <span class="font-semibold">{{ filteredPending.length }}</span> debts
          </p>

          <div class="flex space-x-1">
            <button
              @click="individualPage = Math.max(individualPage - 1, 1)"
              :disabled="individualPage === 1"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
            >
              Prev
            </button>
            <button
              v-for="no in individualTotalPages"
              :key="no"
              @click="individualPage = no"
              :class="['px-2.5 py-1 text-xs border rounded cursor-pointer font-bold',
                individualPage === no
                  ? 'bg-blue-650 border-blue-650 text-white font-black'
                  : 'bg-white border-slate-300 text-slate-650 hover:bg-slate-150'
              ]"
            >
              {{ no }}
            </button>
            <button
              @click="individualPage = Math.min(individualPage + 1, individualTotalPages)"
              :disabled="individualPage === individualTotalPages"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- VEHICLES SUMMARY TAB -->
    <div v-if="activeSubTab === 'vehicles'" class="space-y-3 font-sans">
      <div class="bg-blue-50/50 p-3 rounded border border-blue-150 flex items-center space-x-2.5">
        <Truck class="h-5 w-5 text-blue-600 animate-pulse shrink-0" />
        <div class="text-left font-sans">
          <h4 class="font-display font-bold text-blue-900 text-xs uppercase tracking-wider">🚚 Vehicle Shipping Accounts Follow-up</h4>
          <p class="text-[10px] text-blue-750">A delivery vehicle carries load for multiple retail stores. This rollup combines all pending store collections grouped by transport plate.</p>
        </div>
      </div>

      <div class="bg-white rounded border border-slate-200 overflow-hidden shadow-xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-sans border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-extrabold tracking-wider">
                <th class="py-3 px-4 w-[6%] text-center">Detail</th>
                <th class="py-3 px-4 w-[34%]">Vehicle Plate Number</th>
                <th class="py-3 px-4 w-[16%] text-center">Assigned Clients</th>
                <th class="py-3 px-4 w-[20%] text-right">Total Cargo Invoiced</th>
                <th class="py-3 px-4 w-[20%] text-right text-rose-650">Outstanding Due</th>
                <th class="py-3 px-4 w-[24%] text-center">Recovery Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150">
              <template v-for="vNode in currentVehicles" :key="vNode.vehicle">
                <tr :class="['hover:bg-slate-50 transition border-b border-slate-100', expandedVehicleNumber === vNode.vehicle ? 'bg-slate-50/50' : '']">
                  <!-- Toggle Expansion -->
                  <td class="py-3 px-4 text-center">
                    <button
                      @click="expandedVehicleNumber = expandedVehicleNumber === vNode.vehicle ? null : vNode.vehicle"
                      class="p-1 rounded text-slate-500 hover:bg-slate-100 transition cursor-pointer"
                    >
                      <ChevronUp v-if="expandedVehicleNumber === vNode.vehicle" class="h-4.5 w-4.5 text-rose-500" />
                      <ChevronDown v-else class="h-4.5 w-4.5 text-slate-505" />
                    </button>
                  </td>

                  <!-- Plate Name -->
                  <td class="py-3 px-4 text-left">
                    <span class="inline-flex items-center space-x-1.5 text-blue-800 bg-blue-50 border border-blue-150 px-2.5 py-1 rounded text-[11px] font-mono tracking-wider font-extrabold uppercase animate-fadeIn">
                      <Truck class="h-3.5 w-3.5 text-blue-600 font-bold" />
                      <span>{{ vNode.vehicle }}</span>
                    </span>
                  </td>

                  <!-- Assigned counts -->
                  <td class="py-3 px-4 text-center font-extrabold text-slate-700">
                    {{ vNode.count }} store locations
                  </td>

                  <td class="py-3 px-4 text-right font-bold font-mono text-slate-750">
                    {{ formatCurrency(vNode.total) }}
                  </td>

                  <td class="py-3 px-4 text-right font-black font-mono text-rose-600">
                    {{ formatCurrency(vNode.pending) }}
                  </td>

                  <!-- Active search filter jump -->
                  <td class="py-3 px-4 text-center">
                    <button
                      type="button"
                      @click="() => {
                        searchQuery = vNode.vehicle;
                        activeSubTab = 'individual';
                      }"
                      class="px-2.5 py-1 text-[9.5px] font-bold text-slate-750 bg-slate-100 hover:bg-slate-205 border border-slate-220 rounded cursor-pointer transition uppercase"
                    >
                      Filter Store Bills
                    </button>
                  </td>
                </tr>

                <!-- Expanded row contents detailing vehicle assignments -->
                <tr v-if="expandedVehicleNumber === vNode.vehicle" class="bg-slate-50/45 text-left">
                  <td colSpan="6" class="py-3 px-6 border-y border-slate-100 font-sans animate-fadeIn">
                    <div class="bg-white rounded border border-slate-250 p-3 shadow-xs">
                      <h4 class="font-display font-black text-slate-805 text-xs mb-2">🚚 Store-wise cargo breakdown under delivery vehicle plate {{ vNode.vehicle }}</h4>
                      <div class="border border-slate-150 rounded overflow-hidden">
                        <table class="w-full text-left text-[11px] font-sans">
                          <thead>
                            <tr class="bg-slate-50 border-b border-slate-200 text-slate-455 font-bold uppercase text-[9px]">
                              <th class="py-2 px-3">Client Store</th>
                              <th class="py-2 px-3">Item Issued</th>
                              <th class="py-2 px-3 text-right">Invoice Sum</th>
                              <th class="py-2 px-3 text-right text-rose-650">Credit Balance</th>
                              <th class="py-2 px-3 text-center">Collection Action</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-slate-100 font-semibold text-slate-750 text-xs text-left">
                            <tr v-for="assignedRec in pendingCreditSales.filter(s => s.isVehicle && s.vehicleNumber && s.vehicleNumber.trim().toUpperCase() === vNode.vehicle)" :key="assignedRec.id" class="hover:bg-slate-50/50">
                              <td class="py-2 px-3 text-left font-sans">
                                <div class="font-black text-slate-800">{{ assignedRec.customerName }}</div>
                                <div class="text-[9px] text-slate-400 font-normal leading-none mt-0.5">📞 {{ assignedRec.customerPhone || 'N/A' }}</div>
                              </td>
                              <td class="py-2 px-3 font-medium text-slate-650">{{ assignedRec.productName }} (x{{ assignedRec.quantity }})</td>
                              <td class="py-2 px-3 text-right font-mono text-slate-600">{{ formatCurrency(assignedRec.totalAmount) }}</td>
                              <td class="py-2 px-3 text-right font-black font-mono text-rose-650">{{ formatCurrency(assignedRec.totalAmount - assignedRec.amountPaid) }}</td>
                              <td class="py-2 px-3 text-center">
                                <div class="flex gap-1 justify-center">
                                  <button
                                    @click="() => {
                                      selectedSale = assignedRec;
                                      amount = '';
                                      receivedBy = assignedRec.dsrName || 'Counter Staff';
                                      window.scrollTo({ top: 0, behavior: 'smooth' });
                                    }"
                                    class="bg-rose-50 hover:bg-rose-100 text-rose-800 text-[9.5px] px-2 py-0.5 rounded cursor-pointer border border-rose-250 font-medium leading-none"
                                  >
                                    Collect
                                  </button>
                                  <button
                                    @click="handleCloseWithDue(assignedRec)"
                                    class="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[9.5px] px-2 py-0.5 rounded cursor-pointer border border-emerald-250 font-medium whitespace-nowrap leading-none"
                                  >
                                    Close with Due
                                  </button>
                                </div>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>

              <tr v-if="currentVehicles.length === 0">
                <td colSpan="6" class="text-center py-10 bg-white font-sans">
                  <CheckCircle class="h-7 w-7 text-emerald-500 mx-auto mb-2 animate-pulse" />
                  <p class="font-display font-semibold text-slate-750 text-xs">No active vehicle-level outstanding debts!</p>
                  <p class="text-[11px] text-slate-400 font-sans">All vehicle assignments are fully collected.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- vehicle rollups indices pagination layout -->
        <div v-if="vehiclesTotalPages > 1" class="bg-slate-50 border-t border-slate-200 px-4 py-2.5 flex items-center justify-between sm:px-6 font-sans">
          <p class="text-xs text-slate-500">
            Showing <span class="font-semibold">{{ vehiclesFirst + 1 }}</span> to{' '}
            <span class="font-semibold">
              {{ Math.min(vehiclesFirst + itemsPerPage, activePendingVehicles.length) }}
            </span>{' '}
            of <span class="font-semibold">{{ activePendingVehicles.length }}</span> active vehicles
          </p>

          <div class="flex space-x-1">
            <button
              @click="vehiclesPage = Math.max(vehiclesPage - 1, 1)"
              :disabled="vehiclesPage === 1"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
            >
              Prev
            </button>
            <button
              v-for="no in vehiclesTotalPages"
              :key="no"
              @click="vehiclesPage = no"
              :class="['px-2.5 py-1 text-xs border rounded cursor-pointer font-bold',
                vehiclesPage === no
                  ? 'bg-blue-650 border-blue-650 text-white font-black'
                  : 'bg-white border-slate-300 text-slate-650 hover:bg-slate-150'
              ]"
            >
              {{ no }}
            </button>
            <button
              @click="vehiclesPage = Math.min(vehiclesPage + 1, vehiclesTotalPages)"
              :disabled="vehiclesPage === vehiclesTotalPages"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- REPRESENTATIVES (DSR) TAB -->
    <div v-if="activeSubTab === 'reps'" class="space-y-3 font-sans">
      <div class="bg-cyan-50/50 p-3 rounded border border-cyan-150 flex items-center space-x-2.5">
        <UserCheck class="h-5 w-5 text-cyan-700 shrink-0" />
        <div class="text-left font-sans">
          <h4 class="font-display font-bold text-cyan-900 text-xs uppercase tracking-wider">👤 Sales Representative Liabilities follow-up</h4>
          <p class="text-[10px] text-cyan-750">Dealer sales representatives (DSR) and appointed order collectors are responsible for following up on credit given during store visits.</p>
        </div>
      </div>

      <div class="bg-white rounded border border-slate-200 overflow-hidden shadow-xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-sans border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-extrabold tracking-wider animate-fadeIn">
                <th class="py-3 px-4 w-[6%] text-center">Detail</th>
                <th class="py-3 px-4 w-[34%]">Sales Representative Name</th>
                <th class="py-3 px-4 w-[16%] text-center">Assigned Invoices</th>
                <th class="py-3 px-4 w-[20%] text-right">Invoiced Sales Volume</th>
                <th class="py-3 px-4 w-[20%] text-right text-rose-655">Liability Owed</th>
                <th class="py-3 px-4 w-[24%] text-center">Recovery Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150">
              <template v-for="repNode in currentReps" :key="repNode.name">
                <tr :class="['hover:bg-slate-50 transition border-b border-slate-100', expandedRepName === repNode.name ? 'bg-slate-50/50' : '']">
                  <!-- Toggle expansion -->
                  <td class="py-3 px-4 text-center">
                    <button
                      @click="expandedRepName = expandedRepName === repNode.name ? null : repNode.name"
                      class="p-1 rounded text-slate-500 hover:bg-slate-100 transition cursor-pointer"
                    >
                      <ChevronUp v-if="expandedRepName === repNode.name" class="h-4.5 w-4.5 text-rose-500" />
                      <ChevronDown v-else class="h-4.5 w-4.5 text-slate-505" />
                    </button>
                  </td>

                  <!-- Rep Identification -->
                  <td class="py-3 px-4">
                    <span class="inline-flex items-center space-x-1.5 text-cyan-850 bg-cyan-50 border border-cyan-150 px-2.5 py-1 rounded text-[11px] uppercase tracking-wider font-extrabold animate-fadeIn animate-fadeIn">
                      <UserCheck class="h-3.5 w-3.5 text-cyan-600 font-bold" />
                      <span>{{ repNode.name }}</span>
                    </span>
                  </td>

                  <td class="py-3 px-4 text-center font-bold text-slate-700">
                    {{ repNode.count }} bills
                  </td>

                  <td class="py-3 px-4 text-right font-semibold font-mono text-slate-700">
                    {{ formatCurrency(repNode.total) }}
                  </td>

                  <td class="py-3 px-4 text-right font-black font-mono text-rose-600">
                    {{ formatCurrency(repNode.pending) }}
                  </td>

                  <td class="py-3 px-4 text-center">
                    <button
                      type="button"
                      @click="() => {
                        searchQuery = repNode.name === 'Direct Dealer Counter' ? '' : repNode.name;
                        activeSubTab = 'individual';
                      }"
                      class="px-2.5 py-1 text-[10px] font-bold text-slate-755 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded cursor-pointer transition uppercase"
                    >
                      Filter Debts
                    </button>
                  </td>
                </tr>

                <!-- Expanded reps details table -->
                <tr v-if="expandedRepName === repNode.name" class="bg-slate-50/40 text-left">
                  <td colSpan="6" class="py-3 px-6 border-y border-slate-100 font-sans">
                    <div class="bg-white rounded border border-slate-250 p-3 shadow-xs">
                      <h4 class="font-display font-black text-slate-800 text-xs mb-2">👤 Store-wise collections responsibility assigned to representative "{{ repNode.name }}"</h4>
                      <div class="border border-slate-150 rounded overflow-hidden">
                        <table class="w-full text-left text-[11px] font-sans">
                          <thead>
                            <tr class="bg-slate-50 border-b border-slate-200 text-slate-455 font-bold uppercase text-[9px]">
                              <th class="py-2 px-3">Client Store</th>
                              <th class="py-2 px-3">Item Issued</th>
                              <th class="py-2 px-3 text-right">Invoice Sum</th>
                              <th class="py-2 px-3 text-right text-rose-650">Credit Balance</th>
                              <th class="py-2 px-3 text-center">Collection Action</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-slate-100 font-bold text-slate-750 text-xs text-left">
                            <tr v-for="saleRecord in pendingCreditSales.filter(s => {
                              const isDirect = !s.isVehicle && (!s.dsrId || s.dsrId === 'counter');
                              if (repNode.name === 'Direct Dealer Counter') {
                                return isDirect || s.dsrName === 'Direct Dealer Counter';
                              }
                              return s.dsrName && s.dsrName.toLowerCase().trim() === repNode.name.toLowerCase().trim();
                            })" :key="saleRecord.id" class="hover:bg-slate-50/50">
                              <td class="py-2 px-3 text-left">
                                <div class="font-black text-slate-800">{{ saleRecord.customerName }}</div>
                                <div class="text-[9px] text-slate-400 font-normal leading-none mt-0.5">📞 {{ saleRecord.customerPhone || 'N/A' }}</div>
                              </td>
                              <td class="py-2 px-3 font-medium text-slate-650">{{ saleRecord.productName }} (x{{ saleRecord.quantity }})</td>
                              <td class="py-2 px-3 text-right font-mono text-slate-600">{{ formatCurrency(saleRecord.totalAmount) }}</td>
                              <td class="py-2 px-3 text-right font-black font-mono text-rose-650">{{ formatCurrency(saleRecord.totalAmount - saleRecord.amountPaid) }}</td>
                              <td class="py-2 px-3 text-center">
                                <div class="flex gap-1 justify-center">
                                  <button
                                    @click="() => {
                                      selectedSale = saleRecord;
                                      amount = '';
                                      receivedBy = saleRecord.dsrName || 'Counter Staff';
                                      window.scrollTo({ top: 0, behavior: 'smooth' });
                                    }"
                                    class="bg-rose-50 hover:bg-rose-100 text-rose-800 text-[9.5px] px-2 py-0.5 rounded cursor-pointer border border-rose-250 font-medium leading-none"
                                  >
                                    Collect
                                  </button>
                                  <button
                                    @click="handleCloseWithDue(saleRecord)"
                                    class="bg-emerald-50 hover:bg-emerald-100 text-emerald-805 text-[9.5px] px-2 py-0.5 rounded cursor-pointer border border-emerald-250 font-medium whitespace-nowrap leading-none"
                                  >
                                    Close with Due
                                  </button>
                                </div>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>

              <tr v-if="currentReps.length === 0">
                <td colSpan="6" class="text-center py-10 bg-white font-sans">
                  <CheckCircle class="h-7 w-7 text-emerald-500 mx-auto mb-2 animate-pulse" />
                  <p class="font-display font-semibold text-slate-755 text-xs">No active collections responsibility under representatives!</p>
                  <p class="text-[11px] text-slate-400 font-sans">All outstanding representative collections are cleared.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- pagination footer for reps -->
        <div v-if="repsTotalPages > 1" class="bg-slate-50 border-t border-slate-200 px-4 py-2.5 flex items-center justify-between sm:px-6 font-sans">
          <p class="text-xs text-slate-500">
            Showing <span class="font-semibold">{{ repsFirst + 1 }}</span> to{' '}
            <span class="font-semibold">
              {{ Math.min(repsFirst + itemsPerPage, pendingReps.length) }}
            </span>{' '}
            of <span class="font-semibold">{{ pendingReps.length }}</span> representative accounts
          </p>

          <div class="flex space-x-1">
            <button
              @click="repsPage = Math.max(repsPage - 1, 1)"
              :disabled="repsPage === 1"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
            >
              Prev
            </button>
            <button
              v-for="no in repsTotalPages"
              :key="no"
              @click="repsPage = no"
              :class="['px-2.5 py-1 text-xs border rounded cursor-pointer font-bold',
                repsPage === no
                  ? 'bg-blue-650 border-blue-650 text-white font-black'
                  : 'bg-white border-slate-300 text-slate-650 hover:bg-slate-150'
              ]"
            >
              {{ no }}
            </button>
            <button
              @click="repsPage = Math.min(repsPage + 1, repsTotalPages)"
              :disabled="repsPage === repsTotalPages"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- WRITEOFF CONFIRMATION POPUP MODAL -->
    <div v-if="closingInvoiceSale !== null" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fadeIn h-full w-full">
      <div class="bg-white rounded-lg max-w-md w-full border border-slate-200 shadow-xl overflow-hidden animate-slideUp">
        <div class="bg-amber-50 px-4 py-3 border-b border-amber-200 flex items-center space-x-2">
          <span class="text-amber-700 font-bold text-lg leading-none">⚠️</span>
          <h3 class="font-display font-black text-amber-900 text-xs md:text-sm uppercase tracking-wider">
            Confirm Write-Off / Close Invoice
          </h3>
        </div>
        
        <div class="p-4 space-y-3.5 font-sans text-left">
          <p class="text-xs text-slate-600 leading-relaxed">
            Are you sure you want to write-off and close the outlet invoice for customer <span class="font-bold text-slate-900">"{{ closingInvoiceSale.customerName }}"</span>? This operation is irreversible and removes the entry from pending collection sheets.
          </p>
          
          <div class="bg-slate-50 p-3 rounded border border-slate-200 space-y-1.5 text-xs font-semibold">
            <p class="text-slate-500">Invoice ID: <span class="font-mono text-slate-850 font-bold">{{ closingInvoiceSale.id }}</span></p>
            <p class="text-slate-500">Product Item: <span class="text-slate-850 font-bold">{{ closingInvoiceSale.productName }} (Qty: {{ closingInvoiceSale.quantity }})</span></p>
            <p class="text-slate-500">Total Invoice Valuation: <span class="text-slate-850 font-bold font-mono">{{ formatCurrency(closingInvoiceSale.totalAmount) }}</span></p>
            <p class="text-slate-500 flex justify-between pt-1 border-t border-slate-200 font-bold text-rose-650 text-xs">
              <span>UNCOLLECTED BALANCE LOSS:</span>
              <span class="font-mono">{{ formatCurrency(closingInvoiceSale.totalAmount - closingInvoiceSale.amountPaid) }}</span>
            </p>
          </div>

          <p class="text-[10px] text-amber-800 font-medium">
            * Note: The remaining uncollected balance will be written off/removed from ledger with no cash collected.
          </p>

          <p v-if="errorClosing" class="p-2 bg-rose-50 border border-rose-100 rounded text-rose-800 text-[11px] font-bold">
            ⚠️ {{ errorClosing }}
          </p>
        </div>

        <div class="bg-slate-50 px-4 py-3 border-t border-slate-100 flex justify-end space-x-2">
          <button 
            type="button" 
            @click="closingInvoiceSale = null"
            class="px-3.5 py-1.5 bg-white border border-slate-250 rounded text-xs font-bold hover:bg-slate-100 text-slate-705 cursor-pointer"
          >
            Cancel
          </button>
          <button 
            type="button" 
            @click="handleConfirmClose"
            :disabled="isClosingSubmitting"
            class="px-4 py-1.5 bg-amber-600 hover:bg-amber-705 text-white rounded text-xs font-display font-black cursor-pointer shadow-xs disabled:opacity-50 flex items-center justify-center"
          >
            <span v-if="isClosingSubmitting">Writing off dues...</span>
            <span v-else>Yes, Close & Write-Off</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
