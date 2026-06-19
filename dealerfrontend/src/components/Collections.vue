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
  ChevronUp,
  RotateCcw
} from 'lucide-vue-next';
import type { SaleRecord } from '../types';
import { BaseChart, ChartCard } from './charts';
import type { ChartData, ChartOptions } from 'chart.js';
// Audit fix GAP C-1: import usePermissions for operation-level enforcement.
import { usePermissions } from "../composables/usePermissions";

const { canEdit, can } = usePermissions();

const props = withDefaults(defineProps<{
  sales: SaleRecord[];
  formatCurrency?: (amt: number) => string;
  onCollectPayment?: (saleId: string, amount: number, receivedBy: string) => Promise<any>;
  onCloseWithDue?: (saleId: string) => Promise<any>;
}>(), {});

const emit = defineEmits<{
  (e: 'refreshData'): void;
}>();

const searchQuery = ref('');
const selectedSale = ref<SaleRecord | null>(null);

// Window helpers for template access
const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' });

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
  const balanceDue = sale.balanceDue || (sale.netAmount - sale.amountPaid) || (sale.totalAmount - sale.amountPaid);
  if (balanceDue <= 0) return;
  closingInvoiceSale.value = sale;
  errorClosing.value = '';
};

const handleConfirmClose = async () => {
  if (!closingInvoiceSale.value) return;
  isClosingSubmitting.value = true;
  errorClosing.value = '';
  try {
    await props.onCloseWithDue!(closingInvoiceSale.value.id);
    closingInvoiceSale.value = null;
    emit('refreshData');
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
    s.paymentType === 'Credit' && s.collectionStatus !== 'Fully Paid' && !s.isClosedWithDue && !s.isVoided
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
  const balanceDue = selectedSale.value.balanceDue || (selectedSale.value.netAmount - selectedSale.value.amountPaid) || (selectedSale.value.totalAmount - selectedSale.value.amountPaid);

  if (!amount.value || isNaN(amt) || amt <= 0) {
    formError.value = 'Please enter a valid amount greater than ₹0!';
    return;
  }

  if (amt > balanceDue) {
    formError.value = `Cannot collect more than balance due. Max: ${formatCurrency.value(balanceDue)}`;
    return;
  }

  if (!receivedBy.value) {
    formError.value = 'Please enter who is receiving this payment!';
    return;
  }

  isSubmitting.value = true;
  try {
    await props.onCollectPayment!(selectedSale.value.id, amt, receivedBy.value);
    
    amount.value = '';
    receivedBy.value = '';
    selectedSale.value = null;
    emit('refreshData');
  } catch (err: any) {
    formError.value = err.message || 'Error processing payment.';
  } finally {
    isSubmitting.value = false;
  }
};

const activeSubTab = ref<'individual' | 'vehicles' | 'reps'>('individual');

// Group vehicle stats dynamically
const vehicleGroups = computed(() => {
  const groups: { [key: string]: { total: number; pending: number; collected: number; count: number } } = {};
  (props.sales || []).forEach(sale => {
    // Exclude voided and written-off sales from vehicle tracking
    if (sale.isVoided || sale.isClosedWithDue) return;
    if (sale.isVehicle && sale.vehicleNumber) {
      const v = sale.vehicleNumber.trim().toUpperCase();
      if (!groups[v]) {
        groups[v] = { total: 0, pending: 0, collected: 0, count: 0 };
      }
      const netAmt = sale.netAmount || (sale.totalAmount - (sale.returnTotalAmount || 0));
      const dueAmt = sale.balanceDue || (netAmt - sale.amountPaid);
      groups[v].total += netAmt;
      if (dueAmt > 0) {
        groups[v].pending += dueAmt;
      }
      groups[v].collected = groups[v].total - groups[v].pending;
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
    // Exclude voided and written-off sales from rep tracking
    if (sale.isVoided || sale.isClosedWithDue) return;
    const repId = sale.dsrId || 'counter';
    const repName = sale.dsrName || 'Direct Dealer Counter';
    if (!groups[repId]) {
      groups[repId] = { name: repName, total: 0, pending: 0, count: 0 };
    }
    const netAmt = sale.netAmount || (sale.totalAmount - (sale.returnTotalAmount || 0));
    const dueAmt = sale.balanceDue || (netAmt - sale.amountPaid);
    groups[repId].total += netAmt;
    if (dueAmt > 0) {
      groups[repId].pending += dueAmt;
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
  return pendingCreditSales.value.reduce((acc, curr) => {
    const due = curr.balanceDue || (curr.netAmount - curr.amountPaid) || (curr.totalAmount - curr.amountPaid);
    return acc + due;
  }, 0);
});

// Outstanding by vehicle bar chart
const vehicleOutstandingData = computed(() => {
  const top5 = vehicleGroups.value.slice(0, 5);
  return {
    labels: top5.map(v => v.vehicle),
    datasets: [{
      label: 'Outstanding',
      data: top5.map(v => v.pending),
      backgroundColor: 'rgba(244, 63, 94, 0.75)',
      borderColor: 'rgb(244, 63, 94)',
      borderWidth: 1,
      borderRadius: 6,
    }, {
      label: 'Collected',
      data: top5.map(v => v.collected),
      backgroundColor: 'rgba(16, 185, 129, 0.75)',
      borderColor: 'rgb(16, 185, 129)',
      borderWidth: 1,
      borderRadius: 6,
    }]
  };
});

const vehicleOutstandingOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: { usePointStyle: true, pointStyle: 'rectRounded', padding: 12, font: { family: 'Inter', size: 11 } }
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => `${ctx.dataset.label}: ${formatCurrency.value(ctx.raw as number)}`
      }
    }
  },
  scales: {
    x: { grid: { display: false } },
    y: { 
      grid: { color: '#EAE4DC' },
      ticks: {
        callback: (value: any) => {
          const val = value as number;
          if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
          if (val >= 1000) return `₹${(val / 1000).toFixed(1)}K`;
          return `₹${val}`;
        }
      }
    }
  }
}));

// Collection status doughnut
const collectionStatusData = computed(() => {
  const fullyPaid = (props.sales || []).filter(s => s.paymentType === 'Credit' && s.collectionStatus === 'Fully Paid' && !s.isClosedWithDue).length;
  const partial = (props.sales || []).filter(s => s.paymentType === 'Credit' && s.collectionStatus === 'Partial' && !s.isClosedWithDue).length;
  const pending = (props.sales || []).filter(s => s.paymentType === 'Credit' && s.collectionStatus === 'Pending' && !s.isClosedWithDue).length;
  const writtenOff = (props.sales || []).filter(s => s.isClosedWithDue || s.collectionStatus === 'Written Off').length;
  
  return {
    labels: ['Fully Paid', 'Partial', 'Pending', 'Written Off'],
    datasets: [{
      data: [fullyPaid, partial, pending, writtenOff],
      backgroundColor: [
        'rgba(16, 185, 129, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(244, 63, 94, 0.8)',
        'rgba(139, 92, 246, 0.8)',
      ],
      borderColor: [
        'rgb(16, 185, 129)',
        'rgb(245, 158, 11)',
        'rgb(244, 63, 94)',
        'rgb(139, 92, 246)',
      ],
      borderWidth: 2,
      hoverOffset: 6,
    }]
  };
});

const collectionStatusOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '62%',
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: { usePointStyle: true, pointStyle: 'circle', padding: 12, font: { family: 'Inter', size: 11 } }
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const total = (ctx.dataset.data as number[]).reduce((a, b) => a + b, 0);
          const pct = total > 0 ? ((ctx.raw as number) / total * 100).toFixed(1) : 0;
          return `${ctx.label}: ${ctx.raw} invoices (${pct}%)`;
        }
      }
    }
  }
}));
</script>

<template>
  <div class="dashboard-layout font-sans text-left animate-fadeIn">
    <div class="dashboard-middle space-y-6">
    <!-- HEADER -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-xl md:text-2xl font-bold text-slate-800 flex items-center gap-2">
          <DollarSign class="h-6 w-6 text-rose-600" />
          Money to Collect
        </h2>
        <p class="text-sm text-slate-500 mt-1">Track and collect outstanding credit payments</p>
      </div>

      <!-- Outstanding Balance -->
      <div class="bg-rose-50 border border-rose-200 rounded-xl px-5 py-3 flex flex-col justify-center text-right shadow-sm select-none">
        <p class="text-xs text-rose-600 font-semibold uppercase tracking-wider">Total Outstanding</p>
        <p class="text-xl font-bold text-rose-600 font-mono mt-0.5">{{ formatCurrency(totalOutstandingSum) }}</p>
      </div>
    </div>

    <!-- PILL TAB NAVIGATION -->
    <div class="inline-flex bg-slate-100 p-1 rounded-lg gap-1">
      <button
        id="tab-sub-individual"
        type="button"
        @click="activeSubTab = 'individual'"
        :class="['py-2.5 px-4 rounded-lg text-sm font-semibold transition flex items-center gap-2 cursor-pointer',
          activeSubTab === 'individual'
            ? 'bg-white text-slate-900 shadow-sm font-bold'
            : 'text-slate-500 hover:text-slate-700'
        ]"
      >
        <Coins class="h-4 w-4 text-rose-600" />
        <span>Invoices ({{ filteredPending.length }})</span>
      </button>

      <button
        id="tab-sub-vehicles"
        type="button"
        @click="activeSubTab = 'vehicles'"
        :class="['py-2.5 px-4 rounded-lg text-sm font-semibold transition flex items-center gap-2 cursor-pointer',
          activeSubTab === 'vehicles'
            ? 'bg-white text-slate-900 shadow-sm font-bold'
            : 'text-slate-500 hover:text-slate-700'
        ]"
      >
        <Truck class="h-4 w-4 text-blue-600 shrink-0" />
        <span>Vehicles ({{ activePendingVehicles.length }})</span>
      </button>

      <button
        id="tab-sub-reps"
        type="button"
        @click="activeSubTab = 'reps'"
        :class="['py-2.5 px-4 rounded-lg text-sm font-semibold transition flex items-center gap-2 cursor-pointer',
          activeSubTab === 'reps'
            ? 'bg-white text-slate-900 shadow-sm font-bold'
            : 'text-slate-500 hover:text-slate-700'
        ]"
      >
        <User class="h-4 w-4 text-cyan-600 shrink-0" />
        <span>Reps</span>
      </button>
    </div>

    <!-- SEARCH BAR (for Individual tab) -->
    <div v-if="activeSubTab === 'individual'" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <div class="relative w-full">
        <Search class="absolute left-3 top-3 h-5 w-5 text-slate-400" />
        <input 
          type="text" 
          placeholder="Search by customer name, vehicle, or rep..." 
          v-model="searchQuery"
          class="w-full text-sm pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500"
        />
      </div>
    </div>

    <!-- PAYMENT COLLECTION SLIDE-DOWN PANEL -->
    <div v-if="selectedSale" class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 animate-fadeIn font-sans">
      <div class="flex justify-between items-center pb-3 border-b border-slate-100">
        <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
          <DollarSign class="h-5 w-5 text-rose-600" />
          <span>Collect Payment</span>
        </h3>
        <button 
          id="col-btn-close-form"
          @click="selectedSale = null" 
          class="text-slate-400 hover:text-slate-600 cursor-pointer p-1 rounded-lg hover:bg-slate-100 transition"
        >
          <X class="h-5 w-5" />
        </button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        <!-- Sale Reference -->
        <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-sm text-slate-600">
          <h4 class="font-bold text-slate-800 text-sm uppercase tracking-wider">Sale Details</h4>
          <div class="space-y-2">
            <p class="flex justify-between">
              <span class="text-slate-400 font-semibold">Customer</span>
              <span class="font-bold text-slate-800">{{ selectedSale.customerName }}</span>
            </p>
            <p class="flex justify-between">
              <span class="text-slate-400 font-semibold">Phone</span>
              <span class="font-semibold">{{ selectedSale.customerPhone || 'N/A' }}</span>
            </p>
            <p class="flex justify-between">
              <span class="text-slate-400 font-semibold">Product</span>
              <span class="font-semibold">{{ selectedSale.productName }} (×{{ selectedSale.quantity }})</span>
            </p>
            <p class="flex justify-between">
              <span class="text-slate-400 font-semibold">Route</span>
              <span v-if="selectedSale.isVehicle" class="font-semibold text-blue-700">Vehicle {{ selectedSale.vehicleNumber }}</span>
              <span v-else class="font-semibold text-cyan-700">Rep {{ selectedSale.dsrName }}</span>
            </p>
          </div>
          <div class="pt-3 border-t border-slate-200 grid grid-cols-2 gap-4 text-center">
            <div>
              <p class="text-xs text-slate-400 font-semibold uppercase">Original Bill</p>
              <p class="font-bold text-slate-800 mt-1 font-mono">{{ formatCurrency(selectedSale.totalAmount) }}</p>
            </div>
            <div>
              <p class="text-xs text-rose-500 font-semibold uppercase">Amount Left</p>
              <p class="font-bold text-rose-600 mt-1 font-mono">
                {{ formatCurrency(selectedSale.balanceDue || (selectedSale.totalAmount - selectedSale.amountPaid)) }}
              </p>
            </div>
          </div>
        </div>

        <!-- Collect Form -->
        <form @submit.prevent="handleCollectSubmit" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 block">
              Amount to Collect (₹) *
            </label>
            <input
              type="number"
              :placeholder="`Max: ${formatCurrency(selectedSale.balanceDue || (selectedSale.totalAmount - selectedSale.amountPaid))}`"
              v-model="amount"
              class="w-full text-sm py-3 px-4 border border-rose-200 rounded-lg bg-rose-50/30 font-bold text-rose-800 font-mono focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 block">
              Collected By *
            </label>
            <input 
              type="text" 
              placeholder="e.g. Sanjay Sharma or Counter Desk" 
              v-model="receivedBy"
              class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500"
            />
          </div>

          <div class="flex justify-end gap-3 pt-3 border-t border-slate-100 items-center">
            <p v-if="formError" class="text-sm text-rose-600 font-semibold mr-auto">{{ formError }}</p>
            <p v-if="formSuccess" class="text-sm text-emerald-600 font-semibold mr-auto">{{ formSuccess }}</p>
            
            <button 
              id="col-btn-form-cancel"
              type="button" 
              @click="selectedSale = null" 
              class="py-2.5 px-4 border border-slate-300 rounded-lg text-sm cursor-pointer hover:bg-slate-50 font-semibold"
            >
              Cancel
            </button>
            <button 
              id="col-btn-form-save"
              type="submit" 
              :disabled="isSubmitting"
              class="py-2.5 px-5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-semibold cursor-pointer disabled:opacity-50 flex items-center gap-2 shadow-sm"
            >
              <DollarSign class="h-4 w-4" />
              {{ isSubmitting ? 'Saving...' : 'Record Payment' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- ========== INDIVIDUAL INVOICES TAB ========== -->
    <div v-if="activeSubTab === 'individual'" class="space-y-4">
      <div class="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm font-sans border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-xs font-bold tracking-wider">
                <th class="py-3.5 px-4 w-[5%] text-center"></th>
                <th class="py-3.5 px-4 w-[26%] text-left">Customer</th>
                <th class="py-3.5 px-4 w-[22%]">Product</th>
                <th class="py-3.5 px-4 w-[15%]">Route</th>
                <th class="py-3.5 px-4 w-[12%] text-right font-mono text-rose-600">Outstanding</th>
                <th class="py-3.5 px-4 w-[13%] text-center">Due Date</th>
                <th class="py-3.5 px-4 w-[20%] text-center">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <template v-for="sale in currentIndividualSales" :key="sale.id">
                <tr :class="['hover:bg-slate-50/50 transition', expandedInvoiceId === sale.id ? 'bg-slate-50/60' : '']">
                  <td class="py-3.5 px-4 text-center">
                    <button
                      :id="`col-btn-toggle-detail-${sale.id}`"
                      @click="expandedInvoiceId = expandedInvoiceId === sale.id ? null : sale.id"
                      class="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition cursor-pointer"
                    >
                      <ChevronUp v-if="expandedInvoiceId === sale.id" class="h-4 w-4 text-rose-600" />
                      <ChevronDown v-else class="h-4 w-4" />
                    </button>
                  </td>

                  <td class="py-3.5 px-4">
                    <div class="space-y-0.5">
                      <span class="font-bold text-slate-800 block">{{ sale.customerName }}</span>
                      <span class="text-xs text-slate-400 block">{{ sale.customerPhone || 'N/A' }}</span>
                    </div>
                  </td>

                  <td class="py-3.5 px-4 text-slate-700">
                    <div class="font-medium whitespace-normal">
                      {{ sale.productName }}
                      <span class="ml-1 bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md text-xs font-semibold">
                        ×{{ sale.quantity }}
                      </span>
                    </div>
                  </td>

                  <td class="py-3.5 px-4">
                    <span v-if="sale.isVehicle" class="bg-blue-50 border border-blue-100 text-blue-700 font-mono text-xs px-2.5 py-1 rounded-md font-semibold inline-flex items-center gap-1">
                      <Truck class="h-3 w-3" />
                      {{ sale.vehicleNumber }}
                    </span>
                    <span v-else class="bg-cyan-50 border border-cyan-100 text-cyan-700 text-xs px-2.5 py-1 rounded-md inline-flex items-center gap-1 font-semibold">
                      <UserCheck class="h-3 w-3" />
                      {{ sale.dsrName }}
                    </span>
                  </td>

                  <td class="py-3.5 px-4 text-right font-bold font-mono text-rose-600">
                    {{ formatCurrency(sale.balanceDue || (sale.totalAmount - sale.amountPaid)) }}
                  </td>

                  <td class="py-3.5 px-4 text-center">
                    <span class="bg-rose-50 text-rose-600 border border-rose-100 px-2.5 py-1 rounded-md text-xs font-semibold">
                      {{ sale.dueDate ? new Date(sale.dueDate).toLocaleDateString('en-IN') : 'No date' }}
                    </span>
                  </td>

                  <td class="py-3.5 px-4">
                    <div class="flex gap-2 justify-center">
                      <button
                        :id="`col-btn-trigger-${sale.id}`"
                        @click="() => {
                          selectedSale = sale;
                          amount = '';
                          receivedBy = sale.dsrName || 'Counter Staff';
                          scrollToTop();
                        }"
                        class="bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold px-3 py-1.5 rounded-lg border border-rose-200 flex items-center gap-1.5 cursor-pointer transition"
                      >
                        <Coins class="h-3.5 w-3.5" />
                        <span>Collect</span>
                      </button>

                      <button
                        :id="`col-btn-close-due-${sale.id}`"
                        @click="handleCloseWithDue(sale)"
                        class="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold px-3 py-1.5 rounded-lg border border-emerald-200 flex items-center gap-1 cursor-pointer transition"
                        title="Close invoice with remaining balance written off"
                      >
                        <span>Write Off</span>
                      </button>
                    </div>
                  </td>
                </tr>

                <!-- Expanded Details -->
                <tr v-if="expandedInvoiceId === sale.id" class="bg-slate-50/40">
                  <td colSpan="7" class="py-4 px-6 border-y border-slate-100 font-sans">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-5 bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
                      <div class="text-left">
                        <h4 class="font-bold text-slate-800 text-sm mb-3">Invoice Summary</h4>
                        <div class="space-y-2 text-sm text-slate-600">
                          <p class="flex justify-between"><span class="text-slate-400">Invoice ID</span> <span class="font-mono font-bold text-slate-700">{{ sale.id }}</span></p>
                          <p class="flex justify-between"><span class="text-slate-400">Date</span> <span>{{ new Date(sale.date).toLocaleString('en-IN') }}</span></p>
                          <p class="flex justify-between"><span class="text-slate-400">Original Total</span> <span class="font-mono">{{ formatCurrency(sale.totalAmount) }}</span></p>
                          <p v-if="sale.returnTotalAmount && sale.returnTotalAmount > 0" class="flex justify-between"><span class="text-amber-500 font-semibold">Returns Deducted</span> <span class="font-mono text-amber-600">-{{ formatCurrency(sale.returnTotalAmount) }}</span></p>
                          <p v-if="sale.returnTotalAmount && sale.returnTotalAmount > 0" class="flex justify-between"><span class="text-slate-400">Net Amount</span> <span class="font-mono font-bold">{{ formatCurrency(sale.netAmount || (sale.totalAmount - sale.returnTotalAmount)) }}</span></p>
                          <p class="flex justify-between"><span class="text-slate-400">Initial Payment</span> <span class="font-mono">{{ formatCurrency(sale.amountPaid - (sale.payments ? sale.payments.reduce((a, p) => a + p.amount, 0) : 0)) }}</span></p>
                          <p class="flex justify-between pt-2 border-t border-slate-100"><span class="text-rose-500 font-semibold">Amount Owed</span> <span class="text-rose-600 font-bold font-mono">{{ formatCurrency(sale.balanceDue || (sale.netAmount - sale.amountPaid) || (sale.totalAmount - sale.amountPaid)) }}</span></p>
                        </div>
                      </div>

                      <div class="text-left">
                        <h4 class="font-bold text-slate-800 text-sm mb-3">Payment History ({{ sale.payments?.length || 0 }})</h4>
                        <div v-if="sale.payments && sale.payments.length > 0" class="border border-slate-200 rounded-xl overflow-hidden max-h-40 overflow-y-auto">
                          <table class="w-full text-left text-sm font-sans">
                            <thead>
                              <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 font-bold uppercase text-xs">
                                <th class="py-2 px-3">Date</th>
                                <th class="py-2 px-3 text-right">Amount</th>
                                <th class="py-2 px-3">Received By</th>
                              </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 text-slate-600 font-medium">
                              <tr v-for="(pRecord, pIdx) in sale.payments" :key="pIdx">
                                <td class="py-2 px-3 text-slate-500">{{ new Date(pRecord.date).toLocaleDateString('en-IN') }}</td>
                                <td class="py-2 px-3 text-right font-mono text-emerald-600 font-bold">+{{ formatCurrency(pRecord.amount) }}</td>
                                <td class="py-2 px-3 text-slate-600">{{ pRecord.receivedBy }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                        <div v-else class="flex flex-col items-center justify-center p-6 border border-dashed border-slate-200 rounded-xl text-center text-slate-400 bg-slate-50/50">
                          <Coins class="h-6 w-6 text-slate-300 mb-2" />
                          <p class="font-medium text-sm">No payments recorded yet</p>
                          <p class="text-xs mt-1">Use "Collect" to record a payment</p>
                        </div>
                      </div>

                      <!-- Return History -->
                      <div v-if="sale.returns && sale.returns.length > 0" class="text-left mt-4">
                        <h4 class="font-bold text-slate-800 text-sm mb-3 flex items-center gap-1.5">
                          <RotateCcw class="h-4 w-4 text-amber-500" />
                          Returns ({{ sale.returns.length }})
                        </h4>
                        <div class="border border-amber-200 rounded-xl overflow-hidden max-h-40 overflow-y-auto">
                          <table class="w-full text-left text-sm font-sans">
                            <thead>
                              <tr class="bg-amber-50 border-b border-amber-200 text-amber-700 font-bold uppercase text-xs">
                                <th class="py-2 px-3">Date</th>
                                <th class="py-2 px-3 text-center">Qty</th>
                                <th class="py-2 px-3 text-right">Amount</th>
                                <th class="py-2 px-3">Reason</th>
                              </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100 text-slate-600 font-medium">
                              <tr v-for="(ret, rIdx) in sale.returns" :key="rIdx">
                                <td class="py-2 px-3 text-slate-500">{{ new Date(ret.date).toLocaleDateString('en-IN') }}</td>
                                <td class="py-2 px-3 text-center font-mono">-{{ ret.quantity }}</td>
                                <td class="py-2 px-3 text-right font-mono text-amber-600 font-bold">-{{ formatCurrency(ret.returnAmount) }}</td>
                                <td class="py-2 px-3">{{ ret.reason }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>

              <!-- Empty State -->
              <tr v-if="currentIndividualSales.length === 0">
                <td colSpan="7" class="text-center py-12 bg-white">
                  <CheckCircle class="h-10 w-10 text-emerald-400 mx-auto mb-3" />
                  <p class="font-semibold text-slate-600 text-sm">All caught up!</p>
                  <p class="text-sm text-slate-400 mt-1">No pending collections found</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="individualTotalPages > 1" class="bg-slate-50 border-t border-slate-200 px-6 py-3 flex items-center justify-between font-sans">
          <p class="text-sm text-slate-500">
            Showing <span class="font-semibold">{{ individualFirst + 1 }}</span> –
            <span class="font-semibold">{{ Math.min(individualFirst + itemsPerPage, filteredPending.length) }}</span> of
            <span class="font-semibold">{{ filteredPending.length }}</span>
          </p>

          <div class="flex gap-1">
            <button
              @click="individualPage = Math.max(individualPage - 1, 1)"
              :disabled="individualPage === 1"
              class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition"
            >
              Prev
            </button>
            <button
              v-for="no in individualTotalPages"
              :key="no"
              @click="individualPage = no"
              :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition',
                individualPage === no
                  ? 'bg-rose-600 border-rose-600 text-white'
                  : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100'
              ]"
            >
              {{ no }}
            </button>
            <button
              @click="individualPage = Math.min(individualPage + 1, individualTotalPages)"
              :disabled="individualPage === individualTotalPages"
              class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ========== VEHICLES TAB ========== -->
    <div v-if="activeSubTab === 'vehicles'" class="space-y-4 font-sans">
      <div class="bg-blue-50 p-4 rounded-xl border border-blue-200 flex items-center gap-3">
        <Truck class="h-6 w-6 text-blue-600 shrink-0" />
        <div class="text-left">
          <h4 class="font-bold text-blue-900 text-sm">Vehicle Collections</h4>
          <p class="text-xs text-blue-600 mt-0.5">Outstanding payments grouped by delivery vehicle</p>
        </div>
      </div>

      <!-- Vehicle Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div 
          v-for="vNode in currentVehicles" 
          :key="vNode.vehicle"
          class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition hover:shadow-md"
        >
          <div class="p-5">
            <div class="flex justify-between items-start mb-3">
              <div class="flex items-center gap-2">
                <div class="bg-blue-100 p-2 rounded-lg">
                  <Truck class="h-5 w-5 text-blue-600" />
                </div>
                <span class="font-mono font-bold text-slate-800 text-sm tracking-wider uppercase">{{ vNode.vehicle }}</span>
              </div>
              <span class="text-xs bg-slate-100 px-2.5 py-1 rounded-full text-slate-600 font-semibold">
                {{ vNode.count }} stops
              </span>
            </div>

            <div class="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100">
              <div>
                <p class="text-xs text-slate-400 font-semibold uppercase">Total Billed</p>
                <p class="text-sm font-bold text-slate-800 font-mono mt-0.5">{{ formatCurrency(vNode.total) }}</p>
              </div>
              <div>
                <p class="text-xs text-rose-500 font-semibold uppercase">Outstanding</p>
                <p class="text-sm font-bold text-rose-600 font-mono mt-0.5">{{ formatCurrency(vNode.pending) }}</p>
              </div>
            </div>
          </div>

          <div class="border-t border-slate-100 px-5 py-3 bg-slate-50 flex justify-between items-center">
            <button
              type="button"
              @click="expandedVehicleNumber = expandedVehicleNumber === vNode.vehicle ? null : vNode.vehicle"
              class="text-xs font-semibold text-blue-600 hover:text-blue-800 cursor-pointer flex items-center gap-1"
            >
              {{ expandedVehicleNumber === vNode.vehicle ? 'Hide Details' : 'View Details' }}
              <component :is="expandedVehicleNumber === vNode.vehicle ? ChevronUp : ChevronDown" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              @click="() => { searchQuery = vNode.vehicle; activeSubTab = 'individual'; }"
              class="text-xs font-semibold text-slate-500 hover:text-slate-700 cursor-pointer px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition"
            >
              Filter Invoices
            </button>
          </div>

          <!-- Expanded Details -->
          <div v-if="expandedVehicleNumber === vNode.vehicle" class="border-t border-slate-200 p-4 bg-slate-50/50 animate-fadeIn">
            <div class="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <table class="w-full text-left text-sm font-sans">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 font-bold uppercase text-xs">
                    <th class="py-2 px-3">Customer</th>
                    <th class="py-2 px-3">Product</th>
                    <th class="py-2 px-3 text-right">Billed</th>
                    <th class="py-2 px-3 text-right text-rose-600">Owed</th>
                    <th class="py-2 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-slate-600">
                  <tr v-for="assignedRec in pendingCreditSales.filter(s => s.isVehicle && s.vehicleNumber && s.vehicleNumber.trim().toUpperCase() === vNode.vehicle)" :key="assignedRec.id" class="hover:bg-slate-50/50">
                    <td class="py-2.5 px-3">
                      <div class="font-semibold text-slate-800">{{ assignedRec.customerName }}</div>
                      <div class="text-xs text-slate-400 mt-0.5">{{ assignedRec.customerPhone || 'N/A' }}</div>
                    </td>
                    <td class="py-2.5 px-3">{{ assignedRec.productName }} (×{{ assignedRec.quantity }})</td>
                    <td class="py-2.5 px-3 text-right font-mono text-slate-600">{{ formatCurrency(assignedRec.totalAmount) }}</td>
                    <td class="py-2.5 px-3 text-right font-bold font-mono text-rose-600">{{ formatCurrency(assignedRec.balanceDue || (assignedRec.totalAmount - assignedRec.amountPaid)) }}</td>
                    <td class="py-2.5 px-3 text-center">
                      <div class="flex gap-1.5 justify-center">
                        <button
                          @click="() => { selectedSale = assignedRec; amount = ''; receivedBy = assignedRec.dsrName || 'Counter Staff'; scrollToTop(); }"
                          class="bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs px-2.5 py-1 rounded-lg cursor-pointer border border-rose-200 font-semibold"
                        >
                          Collect
                        </button>
                        <button
                          @click="handleCloseWithDue(assignedRec)"
                          class="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs px-2.5 py-1 rounded-lg cursor-pointer border border-emerald-200 font-semibold"
                        >
                          Write Off
                        </button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="currentVehicles.length === 0" class="col-span-full text-center py-12 bg-white rounded-xl border border-slate-200">
          <CheckCircle class="h-10 w-10 text-emerald-400 mx-auto mb-3" />
          <p class="font-semibold text-slate-600 text-sm">No vehicle outstanding!</p>
          <p class="text-sm text-slate-400 mt-1">All vehicle deliveries are fully collected</p>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="vehiclesTotalPages > 1" class="bg-white border border-slate-200 rounded-xl px-6 py-3 flex items-center justify-between shadow-sm font-sans">
        <p class="text-sm text-slate-500">
          Showing <span class="font-semibold">{{ vehiclesFirst + 1 }}</span> –
          <span class="font-semibold">{{ Math.min(vehiclesFirst + itemsPerPage, activePendingVehicles.length) }}</span> of
          <span class="font-semibold">{{ activePendingVehicles.length }}</span> vehicles
        </p>
        <div class="flex gap-1">
          <button @click="vehiclesPage = Math.max(vehiclesPage - 1, 1)" :disabled="vehiclesPage === 1" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition">Prev</button>
          <button v-for="no in vehiclesTotalPages" :key="no" @click="vehiclesPage = no" :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition', vehiclesPage === no ? 'bg-rose-600 border-rose-600 text-white' : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100']">{{ no }}</button>
          <button @click="vehiclesPage = Math.min(vehiclesPage + 1, vehiclesTotalPages)" :disabled="vehiclesPage === vehiclesTotalPages" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition">Next</button>
        </div>
      </div>
    </div>

    <!-- ========== REPS TAB ========== -->
    <div v-if="activeSubTab === 'reps'" class="space-y-4 font-sans">
      <div class="bg-cyan-50 p-4 rounded-xl border border-cyan-200 flex items-center gap-3">
        <UserCheck class="h-6 w-6 text-cyan-600 shrink-0" />
        <div class="text-left">
          <h4 class="font-bold text-cyan-900 text-sm">Rep Collections</h4>
          <p class="text-xs text-cyan-600 mt-0.5">Outstanding payments grouped by sales representative</p>
        </div>
      </div>

      <!-- Rep Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div 
          v-for="repNode in currentReps" 
          :key="repNode.name"
          class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition hover:shadow-md"
        >
          <div class="p-5">
            <div class="flex justify-between items-start mb-3">
              <div class="flex items-center gap-2">
                <div class="bg-cyan-100 p-2 rounded-lg">
                  <UserCheck class="h-5 w-5 text-cyan-600" />
                </div>
                <span class="font-bold text-slate-800 text-sm">{{ repNode.name }}</span>
              </div>
              <span class="text-xs bg-slate-100 px-2.5 py-1 rounded-full text-slate-600 font-semibold">
                {{ repNode.count }} bills
              </span>
            </div>

            <div class="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100">
              <div>
                <p class="text-xs text-slate-400 font-semibold uppercase">Total Billed</p>
                <p class="text-sm font-bold text-slate-800 font-mono mt-0.5">{{ formatCurrency(repNode.total) }}</p>
              </div>
              <div>
                <p class="text-xs text-rose-500 font-semibold uppercase">Outstanding</p>
                <p class="text-sm font-bold text-rose-600 font-mono mt-0.5">{{ formatCurrency(repNode.pending) }}</p>
              </div>
            </div>
          </div>

          <div class="border-t border-slate-100 px-5 py-3 bg-slate-50 flex justify-between items-center">
            <button
              @click="expandedRepName = expandedRepName === repNode.name ? null : repNode.name"
              class="text-xs font-semibold text-cyan-600 hover:text-cyan-800 cursor-pointer flex items-center gap-1"
            >
              {{ expandedRepName === repNode.name ? 'Hide Details' : 'View Details' }}
              <component :is="expandedRepName === repNode.name ? ChevronUp : ChevronDown" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              @click="() => { searchQuery = repNode.name === 'Direct Dealer Counter' ? '' : repNode.name; activeSubTab = 'individual'; }"
              class="text-xs font-semibold text-slate-500 hover:text-slate-700 cursor-pointer px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition"
            >
              Filter Invoices
            </button>
          </div>

          <!-- Expanded Details -->
          <div v-if="expandedRepName === repNode.name" class="border-t border-slate-200 p-4 bg-slate-50/50 animate-fadeIn">
            <div class="bg-white rounded-lg border border-slate-200 overflow-hidden">
              <table class="w-full text-left text-sm font-sans">
                <thead>
                  <tr class="bg-slate-50 border-b border-slate-200 text-slate-400 font-bold uppercase text-xs">
                    <th class="py-2 px-3">Customer</th>
                    <th class="py-2 px-3">Product</th>
                    <th class="py-2 px-3 text-right">Billed</th>
                    <th class="py-2 px-3 text-right text-rose-600">Owed</th>
                    <th class="py-2 px-3 text-center">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 text-slate-600">
                  <tr v-for="saleRecord in pendingCreditSales.filter(s => {
                    const isDirect = !s.isVehicle && (!s.dsrId || s.dsrId === 'counter');
                    if (repNode.name === 'Direct Dealer Counter') {
                      return isDirect || s.dsrName === 'Direct Dealer Counter';
                    }
                    return s.dsrName && s.dsrName.toLowerCase().trim() === repNode.name.toLowerCase().trim();
                  })" :key="saleRecord.id" class="hover:bg-slate-50/50">
                    <td class="py-2.5 px-3">
                      <div class="font-semibold text-slate-800">{{ saleRecord.customerName }}</div>
                      <div class="text-xs text-slate-400 mt-0.5">{{ saleRecord.customerPhone || 'N/A' }}</div>
                    </td>
                    <td class="py-2.5 px-3">{{ saleRecord.productName }} (×{{ saleRecord.quantity }})</td>
                    <td class="py-2.5 px-3 text-right font-mono text-slate-600">{{ formatCurrency(saleRecord.totalAmount) }}</td>
                    <td class="py-2.5 px-3 text-right font-bold font-mono text-rose-600">{{ formatCurrency(saleRecord.balanceDue || (saleRecord.totalAmount - saleRecord.amountPaid)) }}</td>
                    <td class="py-2.5 px-3 text-center">
                      <div class="flex gap-1.5 justify-center">
                        <!-- Audit fix GAP C-1: gate Collect button by collections.edit permission -->
                        <button v-if="canEdit('collections').value" @click="() => { selectedSale = saleRecord; amount = ''; receivedBy = saleRecord.dsrName || 'Counter Staff'; scrollToTop(); }" class="bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs px-2.5 py-1 rounded-lg cursor-pointer border border-rose-200 font-semibold">Collect</button>
                        <!-- Audit fix GAP C-1: gate Write Off button by bad_debt feature + collections.edit permission -->
                        <button v-if="can('bad_debt').value && canEdit('collections').value" @click="handleCloseWithDue(saleRecord)" class="bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs px-2.5 py-1 rounded-lg cursor-pointer border border-emerald-200 font-semibold">Write Off</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-if="currentReps.length === 0" class="col-span-full text-center py-12 bg-white rounded-xl border border-slate-200">
          <CheckCircle class="h-10 w-10 text-emerald-400 mx-auto mb-3" />
          <p class="font-semibold text-slate-600 text-sm">All clear!</p>
          <p class="text-sm text-slate-400 mt-1">No outstanding rep collections</p>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="repsTotalPages > 1" class="bg-white border border-slate-200 rounded-xl px-6 py-3 flex items-center justify-between shadow-sm font-sans">
        <p class="text-sm text-slate-500">
          Showing <span class="font-semibold">{{ repsFirst + 1 }}</span> –
          <span class="font-semibold">{{ Math.min(repsFirst + itemsPerPage, repGroups.length) }}</span> of
          <span class="font-semibold">{{ repGroups.length }}</span> reps
        </p>
        <div class="flex gap-1">
          <button @click="repsPage = Math.max(repsPage - 1, 1)" :disabled="repsPage === 1" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition">Prev</button>
          <button v-for="no in repsTotalPages" :key="no" @click="repsPage = no" :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition', repsPage === no ? 'bg-rose-600 border-rose-600 text-white' : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100']">{{ no }}</button>
          <button @click="repsPage = Math.min(repsPage + 1, repsTotalPages)" :disabled="repsPage === repsTotalPages" class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition">Next</button>
        </div>
      </div>
    </div>

    <!-- WRITE-OFF CONFIRMATION MODAL -->
    <div v-if="closingInvoiceSale !== null" class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
      <div class="bg-white rounded-xl max-w-md w-full border border-slate-200 shadow-xl overflow-hidden animate-slideUp">
        <div class="bg-amber-50 px-5 py-4 border-b border-amber-200 flex items-center gap-3">
          <span class="text-amber-600 text-lg">⚠️</span>
          <h3 class="font-bold text-amber-900 text-sm uppercase tracking-wider">
            Confirm Write-Off
          </h3>
        </div>
        
        <div class="p-5 space-y-4 font-sans text-left">
          <p class="text-sm text-slate-600 leading-relaxed">
            Are you sure you want to write off the invoice for <span class="font-bold text-slate-900">"{{ closingInvoiceSale.customerName }}"</span>? This cannot be undone.
          </p>
          
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2 text-sm font-medium">
            <p class="text-slate-500">Invoice: <span class="font-mono text-slate-800 font-bold">{{ closingInvoiceSale.id }}</span></p>
            <p class="text-slate-500">Product: <span class="text-slate-800 font-bold">{{ closingInvoiceSale.productName }} (×{{ closingInvoiceSale.quantity }})</span></p>
            <p class="text-slate-500">Total: <span class="text-slate-800 font-bold font-mono">{{ formatCurrency(closingInvoiceSale.totalAmount) }}</span></p>
            <p class="flex justify-between pt-2 border-t border-slate-200 font-bold text-rose-600 text-sm">
              <span>UNCOLLECTED LOSS:</span>
              <span class="font-mono">{{ formatCurrency(closingInvoiceSale.balanceDue || (closingInvoiceSale.totalAmount - closingInvoiceSale.amountPaid)) }}</span>
            </p>
          </div>

          <p class="text-xs text-amber-700 font-medium">
            The remaining balance will be written off with no cash collected.
          </p>

          <p v-if="errorClosing" class="p-3 bg-rose-50 border border-rose-100 rounded-lg text-rose-700 text-sm font-semibold">
            {{ errorClosing }}
          </p>
        </div>

        <div class="bg-slate-50 px-5 py-3 border-t border-slate-100 flex justify-end gap-3">
          <button 
            type="button" 
            @click="closingInvoiceSale = null"
            class="py-2.5 px-4 bg-white border border-slate-300 rounded-lg text-sm font-semibold hover:bg-slate-100 text-slate-700 cursor-pointer transition"
          >
            Cancel
          </button>
          <button 
            type="button" 
            @click="handleConfirmClose"
            :disabled="isClosingSubmitting"
            class="py-2.5 px-5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-bold cursor-pointer shadow-sm disabled:opacity-50 transition"
          >
            {{ isClosingSubmitting ? 'Processing...' : 'Yes, Write Off' }}
          </button>
        </div>
      </div>
    </div>
    </div><!-- /dashboard-middle -->

    <!-- CHARTS SIDEBAR -->
    <aside class="dashboard-charts">
      <ChartCard title="Vehicle Collections" subtitle="Outstanding vs Collected by vehicle">
        <div style="height: 240px">
          <BaseChart 
            v-if="vehicleGroups.length > 0"
            chartType="bar" 
            :chartData="vehicleOutstandingData" 
            :chartOptions="vehicleOutstandingOptions" 
          />
          <div v-else class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
            <CheckCircle class="h-8 w-8" />
            <span class="text-sm">No vehicle outstanding</span>
          </div>
        </div>
      </ChartCard>
      <ChartCard title="Collection Status" subtitle="Invoice payment status breakdown">
        <div style="height: 240px">
          <BaseChart 
            v-if="(sales || []).some(s => s.paymentType === 'Credit')"
            chartType="doughnut" 
            :chartData="collectionStatusData" 
            :chartOptions="collectionStatusOptions" 
          />
          <div v-else class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
            <Coins class="h-8 w-8" />
            <span class="text-sm">No credit sales yet</span>
          </div>
        </div>
      </ChartCard>
    </aside>
  </div>
</template>

<style scoped>
.dashboard-layout {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 100%;
}

@media (min-width: 1280px) {
  .dashboard-layout {
    flex-direction: row;
    gap: 24px;
  }
}

.dashboard-middle {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dashboard-charts {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex-shrink: 0;
}

@media (min-width: 1280px) {
  .dashboard-charts {
    width: 380px;
    min-width: 380px;
    max-height: calc(100vh - var(--dc-header-h, 88px) - var(--dc-footer-h, 36px) - 48px);
    overflow-y: auto;
    position: sticky;
    top: 24px;
    align-self: flex-start;
  }

  .dashboard-charts::-webkit-scrollbar {
    width: 4px;
  }
  .dashboard-charts::-webkit-scrollbar-track {
    background: transparent;
  }
  .dashboard-charts::-webkit-scrollbar-thumb {
    background: #e2e8f0;
    border-radius: 999px;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn {
  animation: fadeIn 0.5s ease-out;
}
</style>
