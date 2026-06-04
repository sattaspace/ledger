<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { 
  FileText, 
  UserPlus, 
  TrendingUp, 
  Sparkles, 
  CheckCircle,
  Truck, 
  Coins, 
  User, 
  AlertTriangle,
  BrainCircuit,
  Phone,
  BarChart2,
  Lock,
  ChevronDown,
  ChevronUp,
  Search,
  Calendar,
  X,
  Plus,
  Printer,
  Download
} from 'lucide-vue-next';
import type { DSR, Product, SaleRecord } from '../types';

interface SummaryData {
  revenue: number;
  cogs: number;
  grossProfit: number;
  creditPending: number;
  creditCollected: number;
  lowStockCount: number;
  lowStockItems: Product[];
  dsrPerformance: {
    id?: string;
    name: string;
    role?: 'DSR' | 'Order Collector';
    parentDsrId?: string;
    parentDsrName?: string;
    totalSales: number;
    collected: number;
    pending: number;
    count: number;
  }[];
  productPerformance: {
    name: string;
    quantity: number;
    total: number;
  }[];
  totalSalesCount: number;
}

const props = withDefaults(defineProps<{
  summary: SummaryData | null;
  dsrs: DSR[];
  sales: SaleRecord[];
  products: Product[];
  aiResponse: string;
  isAiLoading: boolean;
  formatCurrency?: (amt: number) => string;
}>(), {});

const emit = defineEmits<{
  (e: 'addDSR', dsrData: any): void;
  (e: 'askGemini'): void;
  (e: 'refreshData'): void;
}>();

// Form toggles & attributes
const showDsrForm = ref(false);
const dsrName = ref('');
const dsrPhone = ref('');
const repRole = ref<'DSR' | 'Order Collector'>('DSR');
const parentDsrId = ref('');
const dsrError = ref('');
const dsrSuccess = ref('');
const dsrSubmitting = ref(false);

const printData = ref<{
  type: 'EXECUTIVE' | 'DSR_STATEMENT' | 'VEHICLE_TRIP';
  period: string;
  payload: any;
} | null>(null);

const selectedPeriod = ref<'ALL' | 'TODAY' | 'WEEK' | 'MONTH' | 'QUARTER' | 'YEAR'>('ALL');
const expandedVehicle = ref<string | null>(null);
const expandedRep = ref<string | null>(null);

const vehicleQuery = ref('');
const repSearchQuery = ref('');

const repPage = ref(1);
const vehiclePage = ref(1);
const repRecordPage = ref(1);
const vRecordPage = ref(1);

const repsPerPage = 5;
const vehiclesPerPage = 6;
const subSalesPerPage = 5;

// Reset inner sub-pagination counters on collapse/expand triggers
watch(expandedRep, () => { repRecordPage.value = 1; });
watch(expandedVehicle, () => { vRecordPage.value = 1; });

// Reset outer pages when queries / period indices shift
watch([repSearchQuery, selectedPeriod], () => { repPage.value = 1; });
watch([vehicleQuery, selectedPeriod], () => { vehiclePage.value = 1; });

const formatCurrency = computed(() => {
  return props.formatCurrency || ((amt: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  });
});

const isWithinPeriod = (dateStr: string, periodStr: string) => {
  if (periodStr === 'ALL') return true;
  const d = new Date(dateStr);
  const now = new Date();
  
  const year = now.getFullYear();
  const month = now.getMonth();
  const day = now.getDate();
  
  if (periodStr === 'TODAY') {
    return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
  }
  if (periodStr === 'WEEK') {
    const diffTime = Math.abs(now.getTime() - d.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays <= 7;
  }
  if (periodStr === 'MONTH') {
    return d.getFullYear() === year && d.getMonth() === month;
  }
  if (periodStr === 'QUARTER') {
    const curQuarter = Math.floor(month / 3);
    const dQuarter = Math.floor(d.getMonth() / 3);
    return d.getFullYear() === year && curQuarter === dQuarter;
  }
  if (periodStr === 'YEAR') {
    return d.getFullYear() === year;
  }
  return true;
};

// Period-filtered sales records
const periodFilteredSales = computed(() => {
  return (props.sales || []).filter(s => isWithinPeriod(s.date, selectedPeriod.value));
});

// Period totals sum
const periodTotals = computed(() => {
  let revenueSum = 0;
  let cogsSum = 0;
  let creditPendingAmt = 0;
  
  periodFilteredSales.value.forEach(sale => {
    revenueSum += sale.totalAmount || 0;
    
    const prod = (props.products || []).find(p => p.id === sale.productId);
    const costPerUnit = prod ? prod.unitPrice : 0;
    cogsSum += (costPerUnit * sale.quantity);

    if (sale.paymentType === 'Credit' && !sale.isClosedWithDue) {
      creditPendingAmt += (sale.totalAmount - sale.amountPaid);
    }
  });
  
  return {
    revenue: revenueSum,
    cogs: cogsSum,
    grossProfit: revenueSum - cogsSum,
    pending: creditPendingAmt
  };
});

// Calculate representative stats dynamically
const periodDsrPerformance = computed(() => {
  return (props.dsrs || []).map(dsr => {
    const dsrSales = periodFilteredSales.value.filter(s => 
      s.dsrId === dsr.id || (s.dsrName && s.dsrName.toLowerCase().trim() === dsr.name.toLowerCase().trim())
    );
    const salesTotal = dsrSales.reduce((acc, curr) => acc + (curr.totalAmount || 0), 0);
    const collected = dsrSales.reduce((acc, curr) => acc + (curr.amountPaid || 0), 0);
    const pending = dsrSales.reduce((acc, curr) => {
      if (curr.paymentType === 'Credit' && !curr.isClosedWithDue) {
        return acc + ((curr.totalAmount || 0) - (curr.amountPaid || 0));
      }
      return acc;
    }, 0);
    return {
      id: dsr.id,
      name: dsr.name,
      role: dsr.role || 'DSR',
      parentDsrId: dsr.parentDsrId,
      parentDsrName: dsr.parentDsrName,
      totalSales: salesTotal,
      collected,
      pending,
      count: dsrSales.length,
    };
  });
});

const filteredDsrPerformance = computed(() => {
  const query = repSearchQuery.value.toLowerCase().trim();
  return periodDsrPerformance.value.filter(rep => 
    rep.name.toLowerCase().includes(query)
  );
});

const currentRepsList = computed(() => {
  const start = (repPage.value - 1) * repsPerPage;
  return filteredDsrPerformance.value.slice(start, start + repsPerPage);
});

const totalRepPages = computed(() => Math.ceil(filteredDsrPerformance.value.length / repsPerPage));

// Calculate logistics vehicles performance dynamically
const vehiclePerformance = computed(() => {
  const vehicles: { [vehicleNumber: string]: {
    vehicleNumber: string;
    totalSales: number;
    collected: number;
    pending: number;
    writtenOff: number;
    count: number;
    reps: string[];
    records: SaleRecord[];
  } } = {};

  periodFilteredSales.value.forEach(s => {
    if (s.isVehicle && s.vehicleNumber) {
      const vNum = s.vehicleNumber.toUpperCase().trim();
      if (!vehicles[vNum]) {
        vehicles[vNum] = {
          vehicleNumber: vNum,
          totalSales: 0,
          collected: 0,
          pending: 0,
          writtenOff: 0,
          count: 0,
          reps: [],
          records: []
        };
      }

      const v = vehicles[vNum];
      v.totalSales += s.totalAmount || 0;
      v.collected += s.amountPaid || 0;
      v.count += 1;
      
      if (s.isClosedWithDue) {
        const writtenOffAmt = Math.max(0, (s.totalAmount || 0) - (s.amountPaid || 0));
        v.writtenOff += writtenOffAmt;
      } else {
        const unpaid = Math.max(0, (s.totalAmount || 0) - (s.amountPaid || 0));
        v.pending += unpaid;
      }

      if (s.dsrName && !v.reps.includes(s.dsrName)) {
        v.reps.push(s.dsrName);
      }

      v.records.push(s);
    }
  });

  return Object.values(vehicles);
});

const filteredVehicles = computed(() => {
  const query = vehicleQuery.value.toLowerCase().trim();
  return vehiclePerformance.value.filter(v => {
    return v.vehicleNumber.toLowerCase().includes(query) || v.reps.some(r => r.toLowerCase().includes(query));
  });
});

const currentVehiclesList = computed(() => {
  const start = (vehiclePage.value - 1) * vehiclesPerPage;
  return filteredVehicles.value.slice(start, start + vehiclesPerPage);
});

const totalVehiclePages = computed(() => Math.ceil(filteredVehicles.value.length / vehiclesPerPage));

// Add DSR submission logic
const handleAddDsrSubmit = async () => {
  dsrError.value = '';
  dsrSuccess.value = '';

  if (!dsrName.value || !dsrPhone.value) {
    dsrError.value = 'Both Representative Name and Phone of communication are required fields!';
    return;
  }

  dsrSubmitting.value = true;
  try {
    emit('addDSR', {
      name: dsrName.value,
      phone: dsrPhone.value,
      role: repRole.value,
      parentDsrId: repRole.value === 'Order Collector' ? parentDsrId.value : undefined
    });
    
    dsrSuccess.value = `Representative "${dsrName.value}" registered successfully!`;
    dsrName.value = '';
    dsrPhone.value = '';
    repRole.value = 'DSR';
    parentDsrId.value = '';
    
    setTimeout(() => {
      showDsrForm.value = false;
      dsrSuccess.value = '';
      emit('refreshData');
    }, 2000);
  } catch (err: any) {
    dsrError.value = err.message || 'Error occurred during staff registration.';
  } finally {
    dsrSubmitting.value = false;
  }
};

// CSV Export Utilities
const handleExportCSV = () => {
  if (!printData.value) return;
  let headers: string[] = [];
  let rows: any[] = [];
  let filename = `dms_report_${printData.value.type.toLowerCase()}_${selectedPeriod.value.toLowerCase()}.csv`;

  if (printData.value.type === 'EXECUTIVE') {
    headers = ['Metric/Item', 'Detail/Value', 'Summary Info'];
    rows = [
      ['Enterprise Name', 'Sri Balaji Enterprises', 'Authorized FMCG Wholesale'],
      ['Account Period', selectedPeriod.value, 'Date selection scope'],
      ['Period Revenue', formatCurrency.value(periodTotals.value.revenue), `${periodFilteredSales.value.length} bills total`],
      ['Cost of Goods Sold', formatCurrency.value(periodTotals.value.cogs), 'FMCG unit prices sum'],
      ['Gross Profit Margin', formatCurrency.value(periodTotals.value.grossProfit), 'Spread before logistics'],
      ['Outstanding Credits', formatCurrency.value(periodTotals.value.pending), 'Active ledger dues'],
    ];
    rows.push([]);
    rows.push(['REPRESENTATIVES LEDGER SUMMARY']);
    rows.push(['Representative Name', 'Role', 'Total Sales Volume', 'Outstanding Pending']);
    filteredDsrPerformance.value.forEach(rep => {
      rows.push([rep.name, rep.role || 'DSR', formatCurrency.value(rep.totalSales), formatCurrency.value(rep.pending)]);
    });
  } else if (printData.value.type === 'DSR_STATEMENT') {
    const rep = printData.value.payload.rep;
    const rSales = printData.value.payload.sales;
    filename = `dms_dsr_statement_${rep.name.replace(/\s+/g, '_').toLowerCase()}.csv`;
    headers = ['Date', 'Invoice ID/Reference', 'Customer Store', 'Product Item', 'Qty', 'Selling Price', 'Invoiced Value', 'Collected Paid', 'Balance Out'];
    rSales.forEach((s: any) => {
      const balance = s.isClosedWithDue ? 0 : Math.max(0, s.totalAmount - s.amountPaid);
      rows.push([
        new Date(s.date).toLocaleDateString(),
        s.id || '--',
        s.customerName,
        s.productName,
        s.quantity,
        s.sellingPrice,
        s.totalAmount,
        s.amountPaid,
        s.isClosedWithDue ? 'WRITTEN_OFF' : balance
      ]);
    });
  } else if (printData.value.type === 'VEHICLE_TRIP') {
    const v = printData.value.payload.vehicle;
    filename = `dms_vehicle_trip_${v.vehicleNumber.toLowerCase()}.csv`;
    headers = ['Trip Date', 'Outlet Store', 'Contact Phone', 'Loaded Product Name', 'Quantity Dispatched', 'Invoiced Value', 'Paid On Route', 'Pending Deficit'];
    v.records.forEach((r: any) => {
      const balance = r.isClosedWithDue ? 0 : Math.max(0, r.totalAmount - r.amountPaid);
      rows.push([
        new Date(r.date).toLocaleDateString(),
        r.customerName,
        r.customerPhone || 'N/A',
        r.productName,
        r.quantity,
        r.totalAmount,
        r.amountPaid,
        r.isClosedWithDue ? 'WRITTEN_OFF' : balance
      ]);
    });
  }

  const csvContent = [
    headers.join(','),
    ...rows.map(e => e.map((val: any) => {
      const str = String(val === undefined ? '' : val).replace(/"/g, '""');
      return str.includes(',') || str.includes('\n') ? `"${str}"` : str;
    }).join(','))
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};
</script>

<template>
  <div class="space-y-4 font-sans text-left animate-fadeIn">
    <!-- HEADER SECTION -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-lg md:text-xl font-display font-bold text-slate-805">📊 Automated Reconciliation Reports</h2>
        <p class="text-[11px] text-slate-550 font-sans mt-0.5">Automated accounting metrics, representative registration, and Gemini AI insights</p>
      </div>

      <div class="flex flex-wrap gap-2">
        <button 
          id="rep-btn-toggle-rep"
          @click="showDsrForm = !showDsrForm"
          class="font-display text-xs px-3 py-2 bg-white text-slate-700 border border-slate-200 rounded flex items-center space-x-1.5 hover:bg-slate-50 transition cursor-pointer font-bold leading-none shadow-xs"
        >
          <UserPlus class="h-3.5 w-3.5 text-blue-600" />
          <span>Appoint DSR Rep</span>
        </button>

        <button 
          id="btn-print-executive-report"
          @click="printData = {
            type: 'EXECUTIVE',
            period: selectedPeriod,
            payload: {
              totals: periodTotals,
              reps: filteredDsrPerformance,
              vehicles: vehiclePerformance,
              lowStock: products.filter(p => p.stock <= (p.minStockAlert || 10))
            }
          }"
          class="font-display text-xs px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded flex items-center space-x-1.5 transition cursor-pointer font-bold leading-none shadow-sm"
        >
          <Printer class="h-3.5 w-3.5 font-bold" />
          <span>Print Executive Statement (PDF)</span>
        </button>
      </div>
    </div>

    <!-- ACCOUNTING RANGE SELECTOR -->
    <div class="bg-white p-2.5 rounded border border-slate-200 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-left">
      <span class="text-[11px] font-bold text-slate-705 uppercase tracking-wider flex items-center gap-1.5 ml-1">
        <Calendar class="h-4 w-4 text-blue-600 font-bold" />
        <span>Accounting Period Range</span>
      </span>
      <div class="flex flex-wrap gap-1">
        <button
          v-for="period in (['ALL', 'TODAY', 'WEEK', 'MONTH', 'QUARTER', 'YEAR'] as const)"
          :key="period"
          :id="`period-filter-${period}`"
          @click="selectedPeriod = period"
          :class="['px-3 py-1 text-[10px] font-display font-extrabold uppercase rounded cursor-pointer transition',
            selectedPeriod === period
              ? 'bg-blue-600 text-white shadow-xs font-black'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          ]"
        >
          {{ period === 'ALL' ? 'All Time' : period }}
        </button>
      </div>
    </div>

    <!-- HIRE DSR REPRESENTATIVE FORM -->
    <form v-if="showDsrForm" @submit.prevent="handleAddDsrSubmit" class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-3 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-1.5 border-b border-slate-100">
        <h3 class="font-display font-bold text-slate-900 text-xs md:text-sm flex items-center space-x-2">
          <User class="h-4.5 w-4.5 text-blue-600" />
          <span>Hire & Appoint Sales Representative or Order Collector</span>
        </h3>
        <button 
          type="button" 
          @click="showDsrForm = false" 
          class="text-slate-405 hover:text-slate-650 cursor-pointer"
        >
          <X class="h-4.5 w-4.5" />
        </button>
      </div>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <!-- Name -->
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Representative Name *</label>
          <input 
            type="text" 
            placeholder="e.g. Rajesh Kumar" 
            v-model="dsrName"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white text-slate-800"
          />
        </div>

        <!-- Phone -->
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block font-mono">Phone Number *</label>
          <input 
            type="text" 
            placeholder="e.g. +91 91122 33445" 
            v-model="dsrPhone"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none font-mono"
          />
        </div>

        <!-- Appointed role selection -->
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Appointed Position Type *</label>
          <div class="grid grid-cols-2 gap-2 h-[34px]">
            <button
              type="button"
              @click="repRole = 'DSR'"
              :class="['text-[10px] font-display font-black rounded flex items-center justify-center border cursor-pointer leading-tight',
                repRole === 'DSR' 
                  ? 'bg-slate-850 border-slate-850 text-white shadow-xs font-black' 
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100'
              ]"
            >
              <span>DSR Representative</span>
            </button>
            <button
              type="button"
              @click="repRole = 'Order Collector'"
              :class="['text-[10px] font-display font-black rounded flex items-center justify-center border cursor-pointer leading-tight',
                repRole === 'Order Collector' 
                  ? 'bg-slate-850 border-slate-850 text-white shadow-xs font-black' 
                  : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-100'
              ]"
            >
              <span>Order Collector</span>
            </button>
          </div>
        </div>

        <!-- Parent supervisor selection -->
        <div class="space-y-1" v-if="repRole === 'Order Collector'">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Appoint under Supervisor DSR *</label>
          <select 
            v-model="parentDsrId"
            class="w-full text-xs p-2 border border-slate-205 rounded bg-white text-slate-700 focus:outline-none"
          >
            <option value="">-- Directly Under Dealer Counter --</option>
            <option v-for="d in dsrs.filter(d => !d.role || d.role === 'DSR')" :key="d.id" :value="d.id">
              {{ d.name }} (DSR Supervisor)
            </option>
          </select>
        </div>
        <div v-else class="p-3 bg-slate-50 border border-slate-100 rounded text-[9px] text-slate-400 mt-auto leading-normal">
          DSRs report directly to Dealer Administration (Sanjay Sharma). They manage their own assigned area collector nodes.
        </div>
      </div>

      <div class="flex justify-end space-x-2 pt-2 border-t border-slate-100 items-center">
        <p v-if="dsrError" class="text-[11px] text-rose-650 mr-auto font-sans font-bold leading-none">⚠️ {{ dsrError }}</p>
        <p v-if="dsrSuccess" class="text-[11px] text-emerald-650 mr-auto font-sans font-bold leading-none">✨ {{ dsrSuccess }}</p>
        
        <button 
          type="button" 
          @click="showDsrForm = false" 
          class="px-3 py-1.5 border border-slate-220 rounded text-xs cursor-pointer hover:bg-slate-50 font-bold"
        >
          Cancel
        </button>
        <button 
          type="submit" 
          :disabled="dsrSubmitting"
          class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold cursor-pointer disabled:opacity-40"
        >
          {{ dsrSubmitting ? 'Registering...' : 'Save Appointed Rep' }}
        </button>
      </div>
    </form>

    <!-- METRIC CARDS GRID -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-left">
      <!-- Revenue -->
      <div class="bg-white p-3.5 rounded border border-slate-200 shadow-xs space-y-1">
        <span class="text-[9px] uppercase text-slate-400 font-sans tracking-wide font-black block">Period Revenue</span>
        <h3 class="text-xl font-display font-black text-blue-800 font-mono">{{ formatCurrency(periodTotals.revenue) }}</h3>
        <p class="text-[9px] text-slate-500 font-sans mt-1">Sum value of {{ periodFilteredSales.length }} bills in this period</p>
      </div>

      <!-- COGS -->
      <div class="bg-white p-3.5 rounded border border-slate-200 shadow-xs space-y-1">
        <span class="text-[9px] uppercase text-slate-400 font-sans tracking-wide font-black block">Cost of Products (COGS)</span>
        <h3 class="text-xl font-display font-black text-slate-805 font-mono">{{ formatCurrency(periodTotals.cogs) }}</h3>
        <p class="text-[9px] text-slate-505 font-sans mt-1">Purchasing and stocking expense estimate</p>
      </div>

      <!-- Profit -->
      <div class="bg-white p-3.5 rounded border border-slate-200 shadow-xs space-y-1">
        <span class="text-[9px] uppercase text-slate-400 font-sans tracking-wide font-black block">Gross Margin Profit</span>
        <h3 :class="['text-xl font-display font-black font-mono', periodTotals.grossProfit >= 0 ? 'text-emerald-700' : 'text-rose-600']">
          {{ formatCurrency(periodTotals.grossProfit) }}
        </h3>
        <p class="text-[9px] text-slate-500 font-sans mt-1">Gross profit spread before operations</p>
      </div>

      <!-- Debts -->
      <div class="bg-white p-3.5 rounded border border-slate-200 shadow-xs space-y-1">
        <span class="text-[9px] uppercase text-rose-500 font-sans tracking-wide font-black block">Credit Issued</span>
        <h3 class="text-xl font-display font-black text-rose-600 font-mono">{{ formatCurrency(periodTotals.pending) }}</h3>
        <p class="text-[9px] text-rose-700 font-sans mt-1 leading-normal">Credits waiting callback collections</p>
      </div>
    </div>

    <!-- DSR REPRESENTATIVE STAFF TABLE -->
    <div class="bg-white p-4 rounded border border-slate-200 shadow-xs space-y-3 font-sans text-left">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-2">
        <div>
          <h3 class="font-display font-black text-slate-800 text-xs uppercase tracking-wider flex items-center gap-1.5">
            <User class="h-4 w-4 text-blue-600" />
            <span>👤 Sales Representative Performance Ledger Matrix</span>
          </h3>
          <p class="text-[11px] text-slate-500 font-sans mt-0.5">Performance metrics and liabilities follow-up grouped by staff</p>
        </div>
        <div class="relative w-full max-w-xs text-left">
          <Search class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search representative name..."
            v-model="repSearchQuery"
            class="w-full text-xs pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-205 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 text-slate-800"
          />
        </div>
      </div>

      <div class="overflow-x-auto border border-slate-200 rounded shadow-xs">
        <table class="w-full text-left font-sans text-xs">
          <thead>
            <tr class="bg-slate-50 border-b border-slate-200 text-slate-450 uppercase text-[9px] font-extrabold tracking-wider">
              <th class="py-2.5 px-3">Representative</th>
              <th class="py-2.5 px-3 font-mono text-[9px]">Mobile Phone</th>
              <th class="py-2.5 px-3">Total Sales Volume</th>
              <th class="py-2.5 px-3 text-emerald-800 font-extrabold">Cash Recovered</th>
              <th class="py-2.5 px-3 text-rose-650 font-extrabold">Outstanding Pending</th>
              <th class="py-2.5 px-3 text-center">Invoiced Bills</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <template v-for="(rep, idx) in currentRepsList" :key="idx">
              <!-- Row Trigger detailed expanding sheets -->
              <tr 
                @click="expandedRep = expandedRep === (rep.id || rep.name) ? null : (rep.id || rep.name)"
                :class="['hover:bg-slate-50 transition cursor-pointer border-b border-slate-100 font-medium', expandedRep === (rep.id || rep.name) ? 'bg-blue-50/10' : '']"
              >
                <td class="py-3 px-3">
                  <div>
                    <p class="font-bold text-slate-850 text-xs leading-none flex items-center space-x-1.5">{{ rep.name }}</p>
                    <div class="text-[9px] text-slate-400 mt-1 flex flex-wrap gap-1 items-center">
                      <span v-if="rep.role === 'DSR'" class="text-blue-700 bg-blue-50 px-1.5 py-0.2 rounded font-black text-[8px] uppercase">DSR Rep</span>
                      <span v-else class="text-cyan-800 bg-cyan-50 px-1.5 py-0.2 rounded font-black text-[8px] uppercase">Collector</span>
                      <span v-if="rep.role === 'Order Collector'" class="text-slate-450 text-[9px]">under {{ rep.parentDsrName || 'Dealer' }}</span>
                    </div>
                  </div>
                </td>
                <td class="py-3 px-3 font-mono text-[10px] text-slate-500 leading-none">{{ dsrs.find(d => d.id === rep.id || d.name === rep.name)?.phone || '--' }}</td>
                <td class="py-3 px-3 font-bold text-slate-800 font-mono">{{ formatCurrency(rep.totalSales) }}</td>
                <td class="py-3 px-3 text-emerald-700 font-bold font-mono">{{ formatCurrency(rep.collected) }}</td>
                <td :class="['py-3 px-3 font-black font-mono', rep.pending > 0 ? 'text-rose-650' : 'text-slate-400']">
                  <span class="leading-none block font-black">{{ formatCurrency(rep.pending) }}</span>
                  <span v-if="rep.pending > 0" class="text-[8px] text-rose-500 uppercase tracking-widest mt-1 block font-extrabold leading-none">Collect urgent</span>
                </td>
                <td class="py-3 px-3 text-center align-middle">
                  <button
                    type="button"
                    class="bg-blue-50 hover:bg-blue-100 border border-blue-100 hover:border-blue-300 text-blue-800 px-2.5 py-1 rounded text-[10px] font-black inline-flex items-center space-x-1 cursor-pointer transition leading-none uppercase shrink-0"
                  >
                    <span>{{ rep.count }} bills</span>
                    <ChevronUp v-if="expandedRep === (rep.id || rep.name)" class="h-3 w-3 text-blue-600 shrink-0 ml-0.5" />
                    <ChevronDown v-else class="h-3 w-3 text-blue-600 shrink-0 ml-0.5" />
                  </button>
                </td>
              </tr>

              <!-- Expanding Invoices Listing for This Representative -->
              <tr v-if="expandedRep === (rep.id || rep.name)">
                <td colSpan="6" class="bg-slate-50/85 p-3 border-t border-b border-slate-200">
                  <div class="space-y-2.5 animate-fadeIn font-sans text-left">
                    <div class="flex items-center justify-between border-b border-slate-205 pb-1.5 font-sans">
                      <span class="font-display font-black text-slate-700 text-[10px] uppercase tracking-wider">
                        <span>🧾 Invoices ledger for <strong class="text-blue-700 uppercase font-black font-display font-bold">{{ rep.name }}</strong></span>
                      </span>

                      <div class="flex items-center gap-2">
                        <button
                          type="button"
                          @click="printData = {
                            type: 'DSR_STATEMENT',
                            period: selectedPeriod,
                            payload: {
                              rep: rep,
                              sales: periodFilteredSales.filter(s => s.dsrId === rep.id || (s.dsrName && s.dsrName.toLowerCase().trim() === rep.name.toLowerCase().trim()))
                            }
                          }"
                          class="px-2.5 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded font-display font-bold text-[9px] flex items-center gap-1 cursor-pointer transition leading-none shadow-xs"
                        >
                          <Printer class="h-2.5 w-2.5 text-blue-600" />
                          <span>Print Outstanding Statement</span>
                        </button>
                      </div>
                    </div>

                    <!-- Inner sales bills iteration -->
                    <div v-if="repSales = periodFilteredSales.filter(s => s.dsrId === rep.id || (s.dsrName && s.dsrName.toLowerCase().trim() === rep.name.toLowerCase().trim())), repSales.length > 0" class="space-y-2">
                      <div class="overflow-x-auto border border-slate-200 rounded shadow-xs">
                        <table class="w-full text-left text-xs bg-white">
                          <thead>
                            <tr class="bg-slate-100 border-b border-slate-200 text-slate-500 uppercase text-[8px] font-mono tracking-wider font-extrabold">
                              <th class="py-2.5 px-2.5">Date / Time</th>
                              <th class="py-2.5 px-2.5">Customer / Store</th>
                              <th class="py-2.5 px-2.5">Dispatched Items</th>
                              <th class="py-2.5 px-2.5 text-center">Invoiced Value</th>
                              <th class="py-2.5 px-2.5 text-center text-emerald-800">Recd. Payment</th>
                              <th class="py-2.5 px-2.5 text-center text-rose-600">Balance Due</th>
                              <th class="py-2.5 px-2.5 text-center">Terms</th>
                              <th class="py-2.5 px-2.5 text-center">Settle Status</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-slate-100 text-[11px] font-semibold text-slate-650">
                            <tr v-for="sale in repSales.slice((repRecordPage - 1) * subSalesPerPage, repRecordPage * subSalesPerPage)" :key="sale.id" class="hover:bg-slate-50 transition align-middle">
                              <td class="py-2.5 px-2.5 text-[10px] text-slate-400 font-mono tracking-tighter">{{ new Date(sale.date).toLocaleDateString() }}</td>
                              <td class="py-2.5 px-2.5 font-bold text-slate-800 leading-tight">
                                {{ sale.customerName }}
                                <span v-if="sale.isVehicle && sale.vehicleNumber" class="ml-1 px-1 bg-slate-900 text-white rounded font-mono text-[8px] uppercase tracking-wide font-black">{{ sale.vehicleNumber }}</span>
                              </td>
                              <td>
                                <p class="font-bold text-slate-700 font-sans leading-none">{{ sale.productName }}</p>
                                <p class="text-[9px] text-slate-400 font-mono mt-0.5 font-normal">Qty: {{ sale.quantity }} @ {{ formatCurrency(sale.sellingPrice) }}</p>
                              </td>
                              <td class="py-2.5 px-2 text-center font-bold font-mono">{{ formatCurrency(sale.totalAmount) }}</td>
                              <td class="py-2.5 px-2 text-center font-bold font-mono text-emerald-755">{{ formatCurrency(sale.amountPaid) }}</td>
                              <td class="py-2.5 px-2 text-center font-black font-mono">
                                <span v-if="sale.isClosedWithDue" class="text-amber-700 bg-amber-50 px-1 border border-amber-100 rounded text-[9px] uppercase font-bold">Written Off</span>
                                <span v-else-if="sale.totalAmount - sale.amountPaid > 0" class="text-rose-650 font-black">{{ formatCurrency(sale.totalAmount - sale.amountPaid) }}</span>
                                <span v-else class="text-emerald-700 font-bold">₹0</span>
                              </td>
                              <td class="py-2.5 px-2.5 text-center font-semibold text-slate-500 font-mono text-[10px]">{{ sale.paymentType }}</td>
                              <td class="py-2.5 px-2.5 text-center">
                                <span v-if="sale.isClosedWithDue" class="bg-amber-100 text-amber-950 border border-amber-200 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Loss writeoff</span>
                                <span v-else-if="sale.totalAmount - sale.amountPaid === 0" class="bg-emerald-50 border border-emerald-100 text-emerald-805 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Settle OK</span>
                                <span v-else class="bg-rose-50 border border-rose-100 text-rose-850 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Outstanding</span>
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>

                      <!-- Sub pagination controls nested inside reps expanding statement list -->
                      <div v-if="totalRepSalesPages = Math.ceil(repSales.length / subSalesPerPage), totalRepSalesPages > 1" class="flex items-center justify-between bg-white border border-slate-205 rounded px-3 py-1.5 shadow-xs font-sans">
                        <span class="text-[10px] text-slate-500">
                          Bills Page <span class="font-bold">{{ repRecordPage }}</span> of <span class="font-bold">{{ totalRepSalesPages }}</span>
                        </span>
                        <div class="flex space-x-1">
                          <button
                            type="button"
                            :disabled="repRecordPage === 1"
                            @click="repRecordPage = Math.max(repRecordPage - 1, 1)"
                            class="px-2 py-0.5 text-[10px] border border-slate-300 rounded bg-slate-100 hover:bg-slate-200 disabled:opacity-40 cursor-pointer"
                          >
                            Prev
                          </button>
                          <button
                            type="button"
                            :disabled="repRecordPage === totalRepSalesPages"
                            @click="repRecordPage = Math.min(repRecordPage + 1, totalRepSalesPages)"
                            class="px-2 py-0.5 text-[10px] border border-slate-300 rounded bg-slate-100 hover:bg-slate-200 disabled:opacity-40 cursor-pointer"
                          >
                            Next
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </template>

            <tr v-if="filteredDsrPerformance.length === 0">
              <td colSpan="6" class="text-center py-8 text-slate-450 italic font-bold">There are no sales representatives matching search queries!</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Outermost page indices footer for representative matrix structure -->
      <div v-if="totalRepPages > 1" class="bg-slate-50 border-t border-slate-200 pt-3 flex items-center justify-between px-1">
        <span class="text-xs text-slate-500">
          Showing representatives <span class="font-semibold">{{ (repPage - 1) * repsPerPage + 1 }}</span> to <span class="font-semibold">{{ Math.min(repPage * repsPerPage, filteredDsrPerformance.length) }}</span> of <span class="font-semibold">{{ filteredDsrPerformance.length }}</span> total
        </span>

        <div class="flex space-x-1">
          <button
            type="button"
            :disabled="repPage === 1"
            @click="repPage = Math.max(repPage - 1, 1)"
            class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-45 cursor-pointer animate-fadeIn"
          >
            Prev
          </button>
          <button
            v-for="no in totalRepPages"
            :key="no"
            type="button"
            @click="repPage = no"
            :class="['px-2.5 py-1 text-xs border rounded cursor-pointer font-bold',
              repPage === no
                ? 'bg-blue-600 border-blue-600 text-white font-black'
                : 'bg-white border-slate-300 text-slate-650 hover:bg-slate-150'
            ]"
          >
            {{ no }}
          </button>
          <button
            type="button"
            :disabled="repPage === totalRepPages"
            @click="repPage = Math.min(repPage + 1, totalRepPages)"
            class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-45 cursor-pointer animate-fadeIn"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- VEHICLES REPORTS BLOCK (BLOCK GRID SCHEMES) -->
    <div class="bg-white p-4 rounded border border-slate-200 shadow-xs space-y-4 font-sans text-left">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-105 pb-3">
        <div>
          <h3 class="font-display font-bold text-slate-805 text-xs uppercase tracking-wider flex items-center space-x-2">
            <Truck class="h-4.5 w-4.5 text-blue-650 font-bold" />
            <span>🚚 Delivery Vehicles Financial Report & Details</span>
          </h3>
          <p class="text-[11px] text-slate-505 font-sans mt-0.5">Track dispatched load values, cash collections, active transit credits, and write-offs by vehicle plate</p>
        </div>

        <div class="relative w-full max-w-xs text-left">
          <Search class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input 
            type="text"
            placeholder="Search vehicle plates or reps name..."
            v-model="vehicleQuery"
            class="w-full text-xs pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      <!-- Aggregate blocks -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <div 
          v-for="v in currentVehiclesList" 
          :key="v.vehicleNumber"
          :class="['border rounded p-3.5 transition flex flex-col justify-between text-left',
            expandedVehicle === v.vehicleNumber 
              ? 'border-blue-500 bg-blue-50/10 shadow-xs ring-1 ring-blue-500/10' 
              : 'border-slate-200 hover:border-slate-350 hover:bg-slate-50/40'
          ]"
        >
          <div class="space-y-2">
            <div class="flex justify-between items-start">
              <div>
                <span class="bg-slate-900 text-white font-mono font-black text-[10px] tracking-wider px-2 py-1 rounded shadow-xs uppercase leading-none">
                  {{ v.vehicleNumber }}
                </span>
                <p class="text-[10px] text-slate-450 mt-2 font-bold font-sans">
                  👤 Reps: {{ v.reps.join(', ') || 'Direct / Counter' }}
                </p>
              </div>
              <span class="text-[9px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-600 font-extrabold font-mono uppercase">
                {{ v.count }} drops
              </span>
            </div>

            <div class="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 font-sans text-left">
              <div>
                <p class="text-[8px] text-slate-400 uppercase font-bold tracking-wider leading-none">Dispatched load</p>
                <p class="text-xs font-semibold text-slate-800 font-mono mt-1 font-bold">{{ formatCurrency(v.totalSales) }}</p>
              </div>
              <div>
                <p class="text-[8px] text-emerald-600 uppercase font-bold tracking-wider leading-none">Cash settling</p>
                <p class="text-xs font-semibold text-emerald-755 font-mono mt-1 font-bold">{{ formatCurrency(v.collected) }}</p>
              </div>
              <div>
                <p class="text-[8px] text-rose-500 uppercase font-bold tracking-wider leading-none">Active credits</p>
                <p class="text-xs font-semibold text-rose-650 font-mono mt-1 font-bold">{{ formatCurrency(v.pending) }}</p>
              </div>
              <div>
                <p class="text-[8px] text-slate-400 uppercase font-bold tracking-wider leading-none">Settled/Loss</p>
                <p class="text-xs font-semibold text-slate-500 font-mono mt-1 font-bold">{{ formatCurrency(v.writtenOff) }}</p>
              </div>
            </div>
          </div>

          <button
            type="button"
            @click="expandedVehicle = expandedVehicle === v.vehicleNumber ? null : v.vehicleNumber"
            class="w-full text-center mt-3 py-1 bg-white hover:bg-slate-100 border border-slate-200 hover:border-slate-350 rounded text-[10px] font-bold text-slate-700 cursor-pointer transition shadow-xs flex items-center justify-center space-x-1"
          >
            <span>{{ expandedVehicle === v.vehicleNumber ? '🔼 Hide Block Details' : '🔍 View Outlets Drops Details' }}</span>
          </button>
        </div>

        <div v-if="currentVehiclesList.length === 0" class="col-span-full text-center py-6 border border-dashed border-slate-200 rounded text-slate-450 text-xs font-bold font-sans">
          No delivery transport vehicles recorded matching filter configurations!
        </div>
      </div>

      <!-- Pagination for blocks -->
      <div v-if="totalVehiclePages > 1" class="bg-slate-50 border-t border-slate-200 pt-3.5 flex items-center justify-between px-1">
        <span class="text-xs text-slate-500">
          Showing vehicles <span class="font-semibold">{{ (vehiclePage - 1) * vehiclesPerPage + 1 }}</span> to <span class="font-semibold">{{ Math.min(vehiclePage * vehiclesPerPage, filteredVehicles.length) }}</span> of <span class="font-semibold">{{ filteredVehicles.length }}</span> total
        </span>
        <div class="flex space-x-1">
          <button
            type="button"
            :disabled="vehiclePage === 1"
            @click="vehiclePage = Math.max(vehiclePage - 1, 1)"
            class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            Prev
          </button>
          <button
            v-for="no in totalVehiclePages"
            :key="no"
            type="button"
            @click="vehiclePage = no"
            :class="['px-2.5 py-1 text-xs border rounded cursor-pointer font-bold',
              vehiclePage === no
                ? 'bg-blue-600 border-blue-600 text-white font-black'
                : 'bg-white border-slate-300 text-slate-650 hover:bg-slate-150'
            ]"
          >
            {{ no }}
          </button>
          <button
            type="button"
            :disabled="vehiclePage === totalVehiclePages"
            @click="vehiclePage = Math.min(vehiclePage + 1, totalVehiclePages)"
            class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer"
          >
            Next
          </button>
        </div>
      </div>

      <!-- Itemized Expand content table for single vehicle -->
      <div v-if="expandedVehicle" class="bg-slate-50 p-3 rounded border border-slate-200 space-y-3 mt-4 animate-fadeIn text-left">
        <div class="flex justify-between items-center border-b border-slate-200 pb-2">
          <h4 class="font-display font-black text-slate-800 text-[11px] uppercase tracking-wider flex items-center space-x-1.5 text-left">
            <span>📋 Dispatched Outward Outlet Drops for Vehicle: <span class="font-mono text-blue-700 font-bold uppercase">{{ expandedVehicle }}</span></span>
          </h4>
          <div class="flex items-center gap-2">
            <button
              type="button"
              @click="printData = {
                type: 'VEHICLE_TRIP',
                period: selectedPeriod,
                payload: {
                  vehicle: vehiclePerformance.find(v => v.vehicleNumber === expandedVehicle)
                }
              }"
              class="px-2.5 py-1 bg-white hover:bg-slate-100 text-slate-700 border border-slate-305 rounded font-display font-bold text-[9px] flex items-center gap-1 cursor-pointer transition leading-none shadow-xs"
            >
              <Printer class="h-2.5 w-2.5 text-blue-605" />
              <span>Print Route Trip Sheet</span>
            </button>
            <button 
              @click="expandedVehicle = null"
              class="text-slate-550 hover:text-rose-650 font-bold text-[10px] cursor-pointer flex items-center gap-0.5 leading-none"
            >
              <span>Close</span>
              <X class="h-3 w-3 shrink-0" />
            </button>
          </div>
        </div>

        <div v-if="currVehicleRecords = (vehiclePerformance.find(v => v.vehicleNumber === expandedVehicle)?.records || []), currVehicleRecords.length > 0" class="overflow-x-auto border border-slate-200 rounded shadow-xs bg-white">
          <table class="w-full text-left text-xs">
            <thead>
              <tr class="bg-slate-105 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-mono tracking-wider font-extrabold">
                <th class="py-2.5 px-3">Date / Time</th>
                <th class="py-2.5 px-3">Retailer Store</th>
                <th class="py-2.5 px-3">Stock Items Drop</th>
                <th class="py-2.5 px-3 text-center">Invoice Value</th>
                <th class="py-2.5 px-3 text-center">Down-Payment Paid</th>
                <th class="py-2.5 px-3 text-center text-rose-600">Balance Due</th>
                <th class="py-2.5 px-3 text-center">Assigned Collector</th>
                <th class="py-2.5 px-3 text-center">Settlement Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150 text-[11px] font-semibold text-slate-650">
              <tr v-for="r in currVehicleRecords.slice((vRecordPage - 1) * subSalesPerPage, vRecordPage * subSalesPerPage)" :key="r.id" class="hover:bg-slate-50 transition align-top">
                <td class="py-2.5 px-3 text-[10px] text-slate-400 font-mono tracking-tighter">{{ new Date(r.date).toLocaleDateString() }}</td>
                <td class="py-2.5 px-3 text-left">
                  <p class="font-bold text-slate-800 leading-tight">{{ r.customerName }}</p>
                  <p class="text-[9.5px] text-slate-400 mt-0.5">📞 {{ r.customerPhone || 'N/A' }}</p>
                </td>
                <td class="py-2.5 px-3 text-left">
                  <p class="font-bold text-slate-750 leading-none">{{ r.productName }}</p>
                  <p class="text-[9.5px] text-slate-400 font-mono mt-0.5 font-normal">Qty: {{ r.quantity }} @ {{ formatCurrency(r.sellingPrice) }}</p>
                </td>
                <td class="py-2.5 px-3 text-center font-bold font-mono">{{ formatCurrency(r.totalAmount) }}</td>
                <td class="py-2.5 px-3 text-center font-bold font-mono text-emerald-700">{{ formatCurrency(r.amountPaid) }}</td>
                <td class="py-2.5 px-3 text-center font-black font-mono">
                  <span v-if="r.isClosedWithDue" class="text-amber-755 bg-amber-50 px-1 border border-amber-200 text-[10px] rounded uppercase font-bold">Written Off</span>
                  <span v-else-if="r.totalAmount - r.amountPaid > 0" class="text-rose-600 font-black">{{ formatCurrency(r.totalAmount - r.amountPaid) }}</span>
                  <span v-else class="text-emerald-700 font-bold">₹0</span>
                </td>
                <td class="py-2.5 px-3 text-slate-600 text-center font-medium">{{ r.dsrName || 'Counter Sales' }}</td>
                <td class="py-2.5 px-3 text-center">
                  <span v-if="r.isClosedWithDue" class="bg-amber-100 text-amber-900 border border-amber-250 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Loss writeoff</span>
                  <span v-else-if="r.totalAmount - r.amountPaid === 0" class="bg-emerald-50 border border-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Paid Full</span>
                  <span v-else-if="r.paymentType === 'Credit'" class="bg-rose-50 border border-rose-100 text-rose-800 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Credit Due</span>
                  <span v-else class="bg-blue-50 border border-blue-105 text-blue-805 px-1.5 py-0.5 rounded text-[8px] font-black uppercase tracking-wider leading-none">Cash terms</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- inner pagination panels for single vehicle drops list -->
        <div v-if="totalVRecordPages = Math.ceil(currVehicleRecords.length / subSalesPerPage), totalVRecordPages > 1" class="flex items-center justify-between bg-white border border-slate-200 rounded px-3 py-1.5 shadow-xs font-sans">
          <span class="text-[10px] text-slate-500">
            Drops Invoice Page <span class="font-bold">{{ vRecordPage }}</span> of <span class="font-bold">{{ totalVRecordPages }}</span>
          </span>
          <div class="flex space-x-1">
            <button
              type="button"
              :disabled="vRecordPage === 1"
              @click="vRecordPage = Math.max(vRecordPage - 1, 1)"
              class="px-2 py-0.5 text-[10px] border border-slate-300 rounded bg-slate-100 hover:bg-slate-205 disabled:opacity-40 cursor-pointer font-bold"
            >
              Prev
            </button>
            <button
              type="button"
              :disabled="vRecordPage === totalVRecordPages"
              @click="vRecordPage = Math.min(vRecordPage + 1, totalVRecordPages)"
              class="px-2 py-0.5 text-[10px] border border-slate-300 rounded bg-slate-105 hover:bg-slate-205 disabled:opacity-40 cursor-pointer font-bold"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- RESTOCK AND LOWER INVENTORY ALARMS -->
    <div v-if="products.filter(p => p.stock <= (p.minStockAlert || 10)).length > 0" class="bg-white p-4 rounded border border-slate-200 flex flex-col shadow-xs text-left gap-3 font-sans">
      <div class="flex items-center space-x-2 border-b border-slate-100 pb-1.5">
        <AlertTriangle class="h-4.5 w-4.5 text-rose-600 animate-pulse" />
        <span class="text-slate-800 font-display font-black text-xs uppercase tracking-wide">⚠️ restock alerts (low warehouse stock items)</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pb-1">
        <div 
          v-for="p in products.filter(p => p.stock <= (p.minStockAlert || 10))" 
          :key="p.id"
          class="p-2.5 border border-dashed border-rose-250 bg-rose-50/5 hover:bg-rose-50/20 rounded-md text-left transition"
        >
          <p class="font-bold text-slate-800 text-[11.5px] truncate">{{ p.name }}</p>
          <div class="flex items-center justify-between text-[10px] text-slate-500 mt-1.5 font-sans leading-none">
            <span>Warehouse Stock: <strong class="text-rose-600 font-extrabold">{{ p.stock }} units</strong></span>
            <span>Alert Point: {{ p.minStockAlert || 10 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- GEMINI RECONCILIATION INSTRUCTIONS -->
    <div class="bg-slate-900 text-slate-100 p-4 rounded border border-slate-800 shadow-sm space-y-4 text-left">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-3 border-b border-slate-800">
        <div class="flex items-center space-x-2.5 text-left">
          <div class="bg-blue-600 text-white p-2 rounded">
            <BrainCircuit class="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <h3 class="font-display font-semibold text-sm text-white">🤖 Run DMS Smart AI Assistant</h3>
            <p class="text-[10px] text-slate-400 font-sans mt-0.5">Runs automated financial reconciliation & suggests actionable steps for busy dealers</p>
          </div>
        </div>

        <button 
          id="rep-btn-run-ai"
          @click="emit('askGemini')"
          :disabled="isAiLoading"
          class="bg-blue-600 hover:bg-blue-500 text-white font-display text-[11px] px-3.5 py-1.5 rounded font-bold shadow-md flex items-center justify-center space-x-1.5 transition disabled:opacity-50 cursor-pointer"
        >
          <!-- spinner -->
          <svg v-if="isAiLoading" class="animate-spin h-3.5 w-3.5 text-white" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <Sparkles v-else class="h-3 w-3 text-white" />
          <span>{{ isAiLoading ? 'Analyzing ledger reports...' : 'Generate AI Reconciliation' }}</span>
        </button>
      </div>

      <div class="bg-slate-950 p-4 rounded border border-slate-800 relative">
        <div v-if="isAiLoading" class="flex flex-col items-center justify-center py-6 space-y-2 text-center">
          <div class="animate-bounce bg-blue-600 text-white p-2 rounded shadow-xs">
            <Sparkles class="h-4 w-4 text-white" />
          </div>
          <p class="text-[11px] text-slate-400 font-sans">Gemini is checking available products, credit collections sheets, and calculating totals...</p>
        </div>

        <div v-else-if="aiResponse" class="space-y-3 max-h-min text-slate-100 text-xs text-left leading-relaxed select-text select-all-none">
          <!-- Raw markdown converter logic inside reactive templates -->
          <div v-for="(line, idx) in aiResponse.split('\n')" :key="idx">
            <h4 v-if="line.startsWith('###') || (line.startsWith('**') && line.endsWith('**') && line.length < 50)" class="font-display font-black text-white text-xs md:text-sm mt-4 mb-2 border-b border-slate-800 pb-1 flex items-center gap-1.5 uppercase tracking-wide">
              <Sparkles class="h-3 w-3 text-amber-450 mt-0.5" />
              <span>{{ line.replace(/[#*]/g, '').trim() }}</span>
            </h4>
            <li v-else-if="line.startsWith('**') || line.startsWith('* **')" class="ml-4 list-disc text-xs text-slate-300 font-medium my-1.5 text-left font-sans">
              <!-- Inline Bold -->
              <span class="font-extrabold text-blue-400">{{ line.replace(/^\*\s+\*\*/, '').replace(/^\*\*/, '').split('**')[0] }}</span>
              <span>{{ line.replace(/^\*\s+\*\*/, '').replace(/^\*\*/, '').split('**').slice(1).join('') }}</span>
            </li>
            <li v-else-if="line.trim().startsWith('*') || line.trim().startsWith('-')" class="ml-4 list-disc text-xs text-slate-300 font-medium my-1.5 text-left font-sans">
              {{ line.trim().substring(1).trim() }}
            </li>
            <div v-else-if="line.trim().length === 0" class="h-1.5" />
            <p v-else class="text-slate-350 text-xs font-sans leading-relaxed text-left font-medium">
              {{ line }}
            </p>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-8 text-center text-slate-400 space-y-1.5 select-none font-sans">
          <Sparkles class="h-6 w-6 text-slate-650 animate-pulse" />
          <p class="font-display font-black text-slate-300 text-xs">No active balance analysis generated yet.</p>
          <p class="text-[10px] text-slate-500 font-sans max-w-xs leading-normal">Tap the top automated reconciler button to let the AI process outstanding dues and recommend ordering limits.</p>
        </div>
      </div>
    </div>

    <!-- PRINT STYLES PREVIEW OVERLAY (Triggered when printData occurs) -->
    <div v-if="printData" class="fixed inset-0 bg-white z-[999] overflow-y-auto p-4 sm:p-8 font-sans text-slate-900 leading-normal text-left uppercase-none select-text print-ready-overlay">
      <!-- absolute printing styles for iframe security layers -->
      <component :is="'style'">{`
        @media print {
          body * {
            visibility: hidden !important;
          }
          .print-ready-overlay, .print-ready-overlay * {
            visibility: visible !important;
          }
          .print-ready-overlay {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            height: auto !important;
            background: white !important;
            color: black !important;
            padding: 0 !important;
            margin: 0 !important;
          }
          .no-print {
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
          }
          .paper-sheet {
            border: none !important;
            box-shadow: none !important;
            margin: 0 !important;
            padding: 0 !important;
            max-width: 100% !important;
          }
        }
      `}</component>

      <div class="max-w-4xl mx-auto mb-6 flex flex-col sm:flex-row gap-3 justify-between items-center bg-slate-100 p-4 border border-slate-205 rounded no-print">
        <div class="space-y-0.5 text-left font-sans">
          <span class="text-xs font-black text-slate-800 uppercase tracking-wider flex items-center gap-1.5 leading-none">
            <Printer class="h-4 w-4 text-blue-600 font-bold" />
            <span>Distribution Documents Hub</span>
          </span>
          <p class="text-[10px] text-slate-500 mt-1 font-sans">Ready for letter-sized / A4 high-contrast print output & persistent storage backup</p>
        </div>
        <div class="flex flex-wrap gap-1.5">
          <button 
            @click="(() => window.print())"
            class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded flex items-center space-x-1.5 cursor-pointer leading-none shadow-xs"
          >
            <Printer class="h-3.5 w-3.5 font-bold" />
            <span>Trigger System Print</span>
          </button>
          <button 
            @click="handleExportCSV"
            class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-900 text-white text-xs font-bold rounded flex items-center space-x-1.5 cursor-pointer leading-none shadow-xs"
          >
            <Download class="h-3.5 w-3.5 text-blue-100 font-bold" />
            <span>Export CSV Data</span>
          </button>
          <button 
            @click="printData = null"
            class="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-bold border border-slate-300 rounded cursor-pointer leading-none"
          >
            Exit Preview
          </button>
        </div>
      </div>

      <!-- Core printable sheets -->
      <div class="max-w-4xl mx-auto border border-slate-300 bg-white p-6 sm:p-10 shadow-xl rounded font-sans text-slate-900 paper-sheet text-left">
        <!-- Luxury Letterhead -->
        <div class="border-b-2 border-slate-950 pb-5 text-left space-y-2 font-sans">
          <div class="flex flex-col sm:flex-row justify-between items-start gap-4">
            <div>
              <h1 class="text-xl sm:text-2xl font-display font-black text-slate-900 uppercase tracking-widest leading-none">
                SRI BALAJI ENTERPRISES
              </h1>
              <p class="text-[10px] font-bold text-slate-405 font-sans tracking-widest uppercase mt-1">
                AUTHORIZED WHOLESALE FMCG DISTRIBUTOR & LOGISTICS PARTNER
              </p>
              <p class="text-[10px] text-slate-500 font-sans mt-0.5 leading-relaxed">
                Main G.T. Road, Industrial Sector-3, Delhi - 110036 | Tel: +91 98112 00344 | GSTIN: 07AAAES1022H1ZN
              </p>
            </div>
            <div class="text-left sm:text-right text-[10px] text-slate-505 space-y-0.5">
              <p class="font-bold text-slate-940 font-mono tracking-wide leading-none">DOCKET ID: DMS-{{ Math.floor(100000 + Math.random() * 900000) }}</p>
              <p>Processed On: {{ new Date().toLocaleDateString() }}</p>
              <p>Authorized Officer: Sanjay Sharma (Manager)</p>
            </div>
          </div>
        </div>

        <!-- 1. Executive printable details sheet -->
        <div v-if="printData.type === 'EXECUTIVE'" class="mt-6 space-y-6 animate-fadeIn font-sans text-left">
          <div class="bg-slate-50 p-3 border border-slate-200 rounded flex justify-between items-center text-left">
            <span class="text-xs font-black text-slate-800 uppercase tracking-wider">📋 Executive Reconciliation Summary Statement</span>
            <span class="text-[10px] font-bold text-slate-600 bg-slate-200 px-2.5 py-0.5 rounded font-mono uppercase leading-none">Range Frame: {{ printData.period }}</span>
          </div>

          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-left">
            <div class="p-3 border border-slate-200 rounded">
              <span class="text-[8px] uppercase font-black text-slate-400">Total Revenue</span>
              <p class="text-sm font-bold text-slate-900 font-mono mt-0.5 font-bold leading-none">{{ formatCurrency(printData.payload.totals.revenue) }}</p>
            </div>
            <div class="p-3 border border-slate-205 rounded">
              <span class="text-[8px] uppercase font-black text-slate-400">Cost of stock</span>
              <p class="text-sm font-bold text-slate-800 font-mono mt-0.5 font-bold leading-none">{{ formatCurrency(printData.payload.totals.cogs) }}</p>
            </div>
            <div class="p-3 border border-slate-205 rounded">
              <span class="text-[8px] uppercase font-black text-slate-400">calculated gross margin</span>
              <p class="text-sm font-bold text-emerald-800 font-mono mt-0.5 font-bold leading-none">{{ formatCurrency(printData.payload.totals.grossProfit) }}</p>
            </div>
            <div class="p-3 border border-slate-205 bg-rose-50/5 rounded">
              <span class="text-[8px] uppercase font-black text-rose-600">Pending Credit Recovery</span>
              <p class="text-sm font-bold text-rose-650 font-mono mt-0.5 font-bold leading-none">{{ formatCurrency(printData.payload.totals.pending) }}</p>
            </div>
          </div>

          <!-- represent map -->
          <div class="space-y-2 text-left">
            <h3 class="text-[10px] font-black uppercase text-slate-850 tracking-wider">👤 Sales Staff Representative Ledger</h3>
            <table class="w-full text-left text-[11px] border border-slate-300 rounded overflow-hidden">
              <thead>
                <tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-[9px] uppercase text-slate-500">
                  <th class="py-2 px-3">Rep Name</th>
                  <th class="py-2 px-3 text-center">Appointed Authority</th>
                  <th class="py-2.5 px-3 text-right">Invoiced Sales Volume</th>
                  <th class="py-2.5 px-3 text-right">Cash Received</th>
                  <th class="py-2.5 px-3 text-right text-rose-700">Dues Outstanding</th>
                  <th class="py-2 px-3 text-center">Bills Count</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 font-medium">
                <tr v-for="(rep, rIdx) in printData.payload.reps" :key="rIdx">
                  <td class="py-2 px-3 font-semibold text-slate-800">{{ rep.name }}</td>
                  <td class="py-2 px-3 text-center text-slate-500 font-mono text-[9px]">{{ rep.role || 'DSR' }}</td>
                  <td class="py-2.5 px-3 text-right font-mono">{{ formatCurrency(rep.totalSales) }}</td>
                  <td class="py-2.5 px-3 text-right font-mono text-emerald-700">{{ formatCurrency(rep.collected) }}</td>
                  <td :class="['py-2.5 px-3 text-right font-mono font-bold', rep.pending > 0 ? 'text-rose-650' : 'text-slate-400']">{{ formatCurrency(rep.pending) }}</td>
                  <td class="py-2 px-3 text-center font-mono">{{ rep.count }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- fleet mapping -->
          <div class="space-y-2 text-left">
            <h3 class="text-[10px] font-black uppercase text-slate-850 tracking-wider">🚚 Logistics Fleet Transit Ledger</h3>
            <table class="w-full text-left text-[11px] border border-slate-300 rounded overflow-hidden">
              <thead>
                <tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-[9px] uppercase text-slate-500">
                  <th class="py-2 px-3">Vehicle Plate</th>
                  <th class="py-2 px-3">Representatives</th>
                  <th class="py-2 px-3 text-center">Trip Drops</th>
                  <th class="py-2 px-3 text-right">Dispatch Load value</th>
                  <th class="py-2 px-3 text-right">Recovered Settled</th>
                  <th class="py-2 px-3 text-right text-rose-700">Out Credit Active</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 font-medium">
                <tr v-for="vNode in printData.payload.vehicles" :key="vNode.vehicleNumber">
                  <td class="py-2 px-3 font-mono font-bold">{{ vNode.vehicleNumber }}</td>
                  <td class="py-2 px-3 text-[9.5px] text-slate-500">{{ vNode.reps.join(', ') || 'Direct counter' }}</td>
                  <td class="py-2 px-3 text-center font-mono">{{ vNode.count }} active drops</td>
                  <td class="py-2 px-3 text-right font-mono">{{ formatCurrency(vNode.totalSales) }}</td>
                  <td class="py-2 px-3 text-right font-mono text-emerald-700">{{ formatCurrency(vNode.collected) }}</td>
                  <td class="py-2 px-3 text-right font-mono font-bold text-rose-650">{{ formatCurrency(vNode.pending) }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- alarms -->
          <div v-if="printData.payload.lowStock.length > 0" class="space-y-2 text-left">
            <h3 class="text-[10px] font-black uppercase text-rose-600 tracking-wider">⚠️ Restock Alerts (Low Warehouse Inventory)</h3>
            <div class="grid grid-cols-2 md:grid-cols-3 gap-2">
              <div v-for="lowProd in printData.payload.lowStock" :key="lowProd.id" class="p-2 border border-dashed border-rose-300 rounded text-left bg-rose-50/5 font-sans">
                <p class="font-bold text-slate-900 text-[11px] truncate leading-none">{{ lowProd.name }}</p>
                <div class="flex justify-between items-center text-[10px] text-slate-500 mt-2 font-sans">
                  <span>Warehouse: <strong class="text-rose-600">{{ lowProd.stock }} units</strong></span>
                  <span>Min: {{ lowProd.minStockAlert || 10 }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 2. DSR STATEMENT PRINT LAYOUT -->
        <div v-if="printData.type === 'DSR_STATEMENT'" class="mt-6 space-y-6 animate-fadeIn text-left font-sans">
          <div class="border border-slate-200 rounded p-4 bg-slate-50 grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
            <div>
              <span class="text-[8px] uppercase font-black text-slate-400">Sales Representative Profile</span>
              <h4 class="text-sm font-bold text-slate-900 mt-0.5 leading-none">{{ printData.payload.rep.name }}</h4>
              <p class="text-[9.5px] text-slate-500 mt-1 font-mono">Mobile Contact: {{ printData.payload.rep.phone || '--' }}</p>
            </div>
            <div>
              <span class="text-[8px] uppercase font-black text-slate-400">Position & DSR Authority</span>
              <h4 class="text-sm font-bold m-0 text-slate-800 leading-none">{{ printData.payload.rep.role || 'DSR' }}</h4>
              <p v-if="printData.payload.rep.role === 'Order Collector'" class="text-[9px] text-slate-500 mt-1 font-sans">Supervisor: {{ printData.payload.rep.parentDsrName || 'Dealer Desk' }}</p>
            </div>
            <div class="space-y-1">
              <span class="text-[8px] uppercase font-bold text-rose-600 block">Pending recovery collections</span>
              <h4 class="text-base font-black text-rose-650 font-mono leading-none">{{ formatCurrency(printData.payload.rep.pending) }}</h4>
              <p class="text-[9px] text-slate-450">Out of {{ formatCurrency(printData.payload.rep.totalSales) }} dispatched value</p>
            </div>
          </div>

          <!-- Customer listing -->
          <div class="space-y-2 text-left">
            <h3 class="text-[10px] font-black uppercase text-slate-800 tracking-wider">🧾 Dynamic Client Outlets Statement Invoices</h3>
            <table class="w-full text-left text-[11px] border border-slate-300 rounded overflow-hidden">
              <thead>
                <tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-[9px] uppercase text-slate-500">
                  <th class="py-2.5 px-3">Invoice Date</th>
                  <th class="py-2.5 px-3">Client Outlet Store</th>
                  <th class="py-2.5 px-3">Dispatched items drop</th>
                  <th class="py-2.5 px-2 text-right">Invoiced Sum</th>
                  <th class="py-2.5 px-2 text-right">Down PMT Recd.</th>
                  <th class="py-2.5 px-2 text-right text-rose-700">DSR Due Outstanding</th>
                  <th class="py-2.5 px-3 text-center">Receiver Signature</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 font-semibold leading-relaxed">
                <tr v-for="sale in printData.payload.sales" :key="sale.id" class="align-top hover:bg-slate-50">
                  <td class="py-2.5 px-3 text-[10px] font-mono text-slate-400">{{ new Date(sale.date).toLocaleDateString() }}</td>
                  <td class="py-2.5 px-3 font-sans">
                    <p class="font-bold text-slate-805 leading-tight">{{ sale.customerName }}</p>
                    <p v-if="sale.customerPhone" class="text-[9px] text-slate-500 font-mono mt-0.5">📞 {{ sale.customerPhone }}</p>
                  </td>
                  <td class="py-2.5 px-3">
                    <p class="font-medium text-slate-700">{{ sale.productName }}</p>
                    <p class="text-[9.5px] text-slate-400 font-mono mt-0.5 font-normal font-sans">Qty: {{ sale.quantity }} @ {{ formatCurrency(sale.sellingPrice) }}</p>
                  </td>
                  <td class="py-2.5 px-2 text-right font-mono">{{ formatCurrency(sale.totalAmount) }}</td>
                  <td class="py-2.5 px-2 text-right font-mono text-emerald-700">{{ formatCurrency(sale.amountPaid) }}</td>
                  <td class="py-2.5 px-2 text-right font-mono font-bold text-rose-650">
                    {{ sale.isClosedWithDue ? 'WRITTEN_OFF' : formatCurrency(sale.totalAmount - sale.amountPaid) }}
                  </td>
                  <td class="py-2.5 px-3 border-l border-slate-205">
                    <div class="w-[100px] h-7 border border-dashed border-slate-300 rounded bg-slate-50/50" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 3. VEHICLE DISPATCH ROUTE SHEET PRINT -->
        <div v-if="printData.type === 'VEHICLE_TRIP'" class="mt-6 space-y-6 animate-fadeIn font-sans text-left">
          <div class="border border-slate-200 rounded p-4 bg-slate-50 grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
            <div>
              <span class="text-[8px] uppercase font-black text-slate-400 font-sans block">Logistics Vehicle Registration</span>
              <h4 class="text-sm font-black text-slate-900 mt-0.5 font-mono uppercase leading-none">{{ printData.payload.vehicle.vehicleNumber }}</h4>
              <p class="text-[9.5px] text-slate-550 mt-1 uppercase font-bold tracking-wider leading-none">Driver Route Trip Dispatch</p>
            </div>
            <div>
              <span class="text-[8px] uppercase font-black text-slate-400 font-sans block">Assigned Delivery DSRs</span>
              <h4 class="text-sm font-bold text-slate-800 mt-0.5 leading-none">
                {{ printData.payload.vehicle.reps.join(', ') || 'Counter / Direct Hands' }}
              </h4>
              <p class="text-[10px] text-slate-500 mt-1">Active drops: {{ printData.payload.vehicle.count }} locations</p>
            </div>
            <div>
              <span class="text-[8px] uppercase font-black text-slate-400 font-sans block">Vehicle Loads Valuation</span>
              <h4 class="text-sm font-black text-slate-900 mt-0.5 font-mono leading-none">
                LOAD: {{ formatCurrency(printData.payload.vehicle.totalSales) }}
              </h4>
              <p class="text-[10px] text-emerald-700 mt-1 font-extrabold leading-none">RECOV: {{ formatCurrency(printData.payload.vehicle.collected) }}</p>
            </div>
          </div>

          <!-- item table -->
          <div class="space-y-2 text-left">
            <h3 class="text-[10px] font-black uppercase text-slate-800 tracking-wider">🚚 Sequence Route Delivery & Outward Drops</h3>
            <table class="w-full text-left text-[11px] border border-slate-300 rounded overflow-hidden">
              <thead>
                <tr class="bg-slate-100 border-b border-slate-300 font-mono font-bold text-[9px] uppercase text-slate-500">
                  <th class="py-2.5 px-2 text-center">Stop</th>
                  <th class="py-2.5 px-3">Retailer Outlet Address</th>
                  <th class="py-2.5 px-3">Stock Items Dispatched</th>
                  <th class="py-2.5 px-2.5 text-center">Invoice Value</th>
                  <th class="py-2.5 px-2.5 text-center">Paid onroute</th>
                  <th class="py-2.5 px-2.5 text-center text-rose-600">Balance Target</th>
                  <th class="py-2.5 px-3 text-center">Actual Collected Cash</th>
                  <th class="py-2.5 px-3 text-center">Store sign stamp</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-150 font-semibold leading-relaxed">
                <tr v-for="(rec, rIdx) in printData.payload.vehicle.records" :key="rec.id" class="align-top hover:bg-slate-50">
                  <td class="py-3 px-2 text-center font-mono text-slate-450 select-none">{{ rIdx + 1 }}</td>
                  <td class="py-3 px-3">
                    <p class="font-bold text-slate-800 leading-tight">{{ rec.customerName }}</p>
                    <p v-if="rec.customerPhone" class="text-[9px] text-slate-400 font-mono mt-0.5">📞 {{ rec.customerPhone }}</p>
                  </td>
                  <td class="py-3 px-3">
                    <p class="font-bold text-slate-705">{{ rec.productName }}</p>
                    <p class="text-[9.5px] text-slate-400 font-mono font-normal">Qty: {{ rec.quantity }} @ {{ formatCurrency(rec.sellingPrice) }}</p>
                  </td>
                  <td class="py-3 px-2.5 text-center font-mono">{{ formatCurrency(rec.totalAmount) }}</td>
                  <td class="py-3 px-2.5 text-center font-mono text-emerald-700">{{ formatCurrency(rec.amountPaid) }}</td>
                  <td class="py-3 px-2.5 text-center font-mono font-bold text-rose-650">
                    {{ rec.isClosedWithDue ? 'WRITTEN_OFF' : formatCurrency(rec.totalAmount - rec.amountPaid) }}
                  </td>
                  <td class="py-3 px-3 border-l border-r border-slate-200">
                    <div class="w-[95px] h-7 border border-dashed border-slate-300 rounded bg-slate-50/20 flex items-center justify-center text-slate-350 font-mono">₹</div>
                  </td>
                  <td class="py-3 px-3">
                    <div class="w-[85px] h-7 border border-dashed border-slate-305 rounded" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="mt-8 pt-8 border-t border-slate-450 grid grid-cols-2 md:grid-cols-3 gap-6 text-[10px] text-slate-600 font-sans text-left uppercase-none">
          <div class="space-y-4">
            <p class="font-bold text-slate-800 block">DMS Handover desk audit lines:</p>
            <div class="h-10 border-b border-dashed border-slate-300 w-full" />
            <p class="text-[9px] text-slate-400 font-mono">DSR Representative Signature / Initials</p>
          </div>
          <div class="space-y-4">
            <p class="font-bold text-slate-800 block">System Verification Desk:</p>
            <div class="h-10 border-b border-dashed border-slate-300 w-full" />
            <p class="text-[9px] text-slate-400 font-mono">Operations Supervisor Signoff Line</p>
          </div>
          <div class="space-y-4 col-span-2 md:col-span-1">
            <p class="font-bold text-slate-850 block">For Sri Balaji Enterprises:</p>
            <div class="h-10 border-b border-dashed border-slate-300 w-full" />
            <p class="text-[9px] text-slate-450 font-bold tracking-wider uppercase font-mono">Manager (Sanjay Sharma)</p>
          </div>
        </div>

        <!-- Footnote -->
        <div class="mt-10 border-t border-slate-200 pt-4 flex flex-col sm:flex-row justify-between items-center text-[9px] text-slate-400 font-mono text-center sm:text-left gap-2 leading-none">
          <span>This distribution reconciliation document is an automated DMS database generation and is legally verified by regional management.</span>
          <span>Doc Hash: {{ Math.random().toString(36).substr(2, 9).toUpperCase() }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
