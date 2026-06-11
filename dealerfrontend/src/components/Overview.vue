<script setup lang="ts">
import { computed } from 'vue';
import { 
  DollarSign, 
  Package, 
  TrendingUp, 
  AlertTriangle, 
  ShoppingBag, 
  ArrowUpRight, 
  PhoneCall, 
  User, 
  Truck, 
  CheckCircle,
  Clock
} from 'lucide-vue-next';
import { useFormatters } from '../composables/useFormatters';
import { BaseChart, ChartCard } from './charts';
import type { SaleRecord } from '../types';
import type { SummaryData } from '../services/api/reports.service';



const props = withDefaults(defineProps<{
  summary: SummaryData | null;
  sales?: SaleRecord[];
  formatCurrency?: (amt: number) => string;
}>(), {
  sales: () => []
});

const emit = defineEmits<{
  (e: 'navigate', tab: string): void;
  (e: 'quickAction', actionType: string): void;
}>();

// Use shared formatter
const { formatCurrency } = useFormatters({ formatCurrency: props.formatCurrency });

// ═══════════════════════════════════════════════════════════
// CHART DATA COMPUTEDS
// ═══════════════════════════════════════════════════════════

// 1. Financial Bar Chart Data
const revenueBarData = computed(() => ({
  labels: ['Total Sales', 'Cash Collected', 'Money to Collect'],
  datasets: [{
    data: [
      props.summary?.revenue || 0,
      props.summary?.creditCollected || 0,
      props.summary?.creditPending || 0
    ],
    backgroundColor: [
      'rgba(59, 130, 246, 0.85)',
      'rgba(16, 185, 129, 0.85)',
      'rgba(244, 63, 94, 0.85)',
    ],
    borderColor: [
      'rgb(59, 130, 246)',
      'rgb(16, 185, 129)',
      'rgb(244, 63, 94)',
    ],
    borderWidth: 2,
    borderRadius: 8,
    barThickness: 40,
  }]
}));

// 2. Financial Bar Chart Options
const revenueBarOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#29241E',
      titleColor: '#F4F0EA',
      bodyColor: '#F4F0EA',
      borderColor: '#DBD3C7',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      titleFont: { family: 'Inter', size: 13, weight: '600' as const },
      bodyFont: { family: 'JetBrains Mono', size: 12 },
      callbacks: {
        label: (ctx: any) => formatCurrency.value(ctx.parsed?.y ?? ctx.raw ?? 0)
      }
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#64748B', font: { family: 'Inter', size: 10, weight: '500' as const } },
      border: { display: false },
    },
    y: {
      grid: { color: '#F1F5F9', drawBorder: false },
      ticks: {
        color: '#94A3B8',
        font: { family: 'JetBrains Mono', size: 9 },
        callback: (value: any) => {
          const v = Number(value);
          if (v >= 100000) return '₹' + (v / 100000).toFixed(1) + 'L';
          if (v >= 1000) return '₹' + (v / 1000).toFixed(1) + 'K';
          return formatCurrency.value(v);
        }
      },
      border: { display: false },
    },
  },
}));

// Exclude voided sales from chart data
const activeSales = computed(() => (props.sales || []).filter(s => !s.isVoided));

// 3. Payment Mix Doughnut Chart Data
const paymentDoughnutData = computed(() => {
  const cashSales = activeSales.value.filter(s => s.paymentType === 'Cash');
  const creditSales = activeSales.value.filter(s => s.paymentType === 'Credit');
  return {
    labels: ['Cash Payments', 'Credit Payments'],
    datasets: [{
      data: [cashSales.length, creditSales.length],
      backgroundColor: ['rgba(16, 185, 129, 0.8)', 'rgba(244, 63, 94, 0.8)'],
      borderColor: ['rgb(16, 185, 129)', 'rgb(244, 63, 94)'],
      borderWidth: 2,
      hoverOffset: 8,
    }]
  };
});

// 4. Payment Mix Doughnut Chart Options
const paymentDoughnutOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '62%',
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        color: '#475569',
        font: { family: 'Inter', size: 10, weight: '500' as const },
        padding: 12,
        usePointStyle: true,
        pointStyle: 'circle',
      }
    },
    tooltip: {
      backgroundColor: '#29241E',
      titleColor: '#F4F0EA',
      bodyColor: '#F4F0EA',
      borderColor: '#DBD3C7',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      callbacks: {
        label: (ctx: any) => {
          const dataArr = (ctx.dataset.data as number[]) || [];
          const total = dataArr.reduce((s: number, v: any) => s + (typeof v === 'number' ? v : 0), 0);
          const value = typeof ctx.raw === 'number' ? ctx.raw : 0;
          const pct = total > 0 ? ((value / total) * 100).toFixed(1) : '0';
          return ` ${ctx.label}: ${value} bills (${pct}%)`;
        }
      }
    },
  },
}));

// 5. Sales Trend Line Chart Data
const salesTrendData = computed(() => {
  const last7Days: string[] = [];
  const amounts: number[] = [];
  
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const dateStr = d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
    last7Days.push(dateStr);
    
    const daySales = activeSales.value.filter(s => {
      const sd = new Date(s.date);
      return sd.getFullYear() === d.getFullYear() && sd.getMonth() === d.getMonth() && sd.getDate() === d.getDate();
    });
    
    amounts.push(daySales.reduce((sum, s) => sum + (s.isVoided ? 0 : (s.totalAmount || 0)), 0));
  }
  
  return {
    labels: last7Days,
    datasets: [{
      label: 'Revenue',
      data: amounts,
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: true,
      tension: 0.4,
      pointBackgroundColor: 'rgb(59, 130, 246)',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
    }]
  };
});

// 6. Sales Trend Line Chart Options
const salesTrendOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: '#29241E',
      titleColor: '#F4F0EA',
      bodyColor: '#F4F0EA',
      borderColor: '#DBD3C7',
      borderWidth: 1,
      padding: 12,
      cornerRadius: 8,
      callbacks: {
        label: (ctx: any) => formatCurrency.value(ctx.parsed?.y ?? ctx.raw ?? 0)
      }
    },
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { color: '#64748B', font: { family: 'Inter', size: 9 } },
      border: { display: false },
    },
    y: {
      grid: { color: '#F1F5F9', drawBorder: false },
      ticks: {
        color: '#94A3B8',
        font: { family: 'JetBrains Mono', size: 9 },
        callback: (value: any) => {
          const v = Number(value);
          if (v >= 100000) return '₹' + (v / 100000).toFixed(1) + 'L';
          if (v >= 1000) return '₹' + (v / 1000).toFixed(1) + 'K';
          return '₹' + v;
        }
      },
      border: { display: false },
    },
  },
}));

// ═══════════════════════════════════════════════════════════
// SAFE ACCESSORS & HELPERS
// ═══════════════════════════════════════════════════════════

const lowStockItems = computed(() => props.summary?.lowStockItems || []);
const dsrPerformance = computed(() => props.summary?.dsrPerformance || []);
const productPerformance = computed(() => props.summary?.productPerformance || []);

const dashboardVehicles = computed(() => {
  const vehicleGroups: Record<string, { total: number; pending: number; count: number }> = {};
  activeSales.value.forEach(sale => {
    if (sale.isVehicle && sale.vehicleNumber) {
      const v = sale.vehicleNumber.trim().toUpperCase();
      if (!vehicleGroups[v]) {
        vehicleGroups[v] = { total: 0, pending: 0, count: 0 };
      }
      vehicleGroups[v].total += sale.totalAmount;
      vehicleGroups[v].pending += (sale.totalAmount - sale.amountPaid);
      vehicleGroups[v].count += 1;
    }
  });
  return Object.entries(vehicleGroups).map(([vehicle, stats]) => ({
    vehicle,
    ...stats
  })).sort((a, b) => b.pending - a.pending);
});

const collectionRate = computed(() => {
  if (!props.summary || props.summary.revenue === 0) return 100;
  return Math.round((props.summary.creditCollected / props.summary.revenue) * 100);
});

const getInitials = (name: string) => {
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
};

const rankBadgeClass = (idx: number) => {
  if (idx === 0) return 'bg-amber-400 text-amber-900 ring-2 ring-amber-300';
  if (idx === 1) return 'bg-slate-300 text-slate-700 ring-2 ring-slate-200';
  if (idx === 2) return 'bg-orange-400 text-orange-900 ring-2 ring-orange-300';
  return 'bg-slate-100 text-slate-600';
};
</script>

<template>
  <!-- Loading state -->
  <div v-if="!summary" class="flex justify-center items-center h-64">
    <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>

  <!-- ═══════════════════════════════════════════════════════════════
       3-COLUMN LAYOUT: [Left Nav] | [Middle Operational] | [Right Charts]
       Middle uses 2-column internal grid for DSR + Vehicles / Products
       ═══════════════════════════════════════════════════════════════ -->
  <div v-else class="dashboard-layout font-sans animate-fadeIn">

    <!-- ═══════════════════════════════════════════════════════════
         MIDDLE COLUMN — Operational Content
         ═══════════════════════════════════════════════════════════ -->
    <div class="dashboard-middle">

      <!-- LOW STOCK ALERT BANNER -->
      <div 
        v-if="summary.lowStockCount > 0" 
        class="relative overflow-hidden rounded-xl shadow-lg animate-pulse-slow"
      >
        <div class="bg-gradient-to-r from-red-500 via-rose-500 to-red-600 p-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <div class="bg-white/20 backdrop-blur-sm p-2.5 rounded-xl">
              <AlertTriangle class="h-5 w-5 text-white shrink-0" />
            </div>
            <div class="text-left">
              <p class="font-display font-bold text-white text-sm">
                {{ summary.lowStockCount }} Products Running Low!
              </p>
              <p class="text-xs text-white/80 font-sans mt-0.5">
                Items like 
                <span class="font-semibold text-white">{{ lowStockItems.slice(0, 3).map(p => p.name).join(', ') }}</span> 
                need restocking.
              </p>
            </div>
          </div>
          <button 
            id="overview-btn-quick-restock"
            @click="emit('navigate', 'inventory')"
            class="bg-white text-red-600 font-display text-xs font-bold px-4 py-2 rounded-xl hover:bg-red-50 transition shadow-md shrink-0 ml-3 cursor-pointer"
          >
            Restock Now
          </button>
        </div>
      </div>

      <!-- 4 GRADIENT METRIC CARDS (2x2 grid) -->
      <div class="grid grid-cols-2 gap-4">
        <!-- TOTAL SALES -->
        <div class="relative overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300">
          <div class="bg-gradient-to-br from-blue-500 to-blue-700 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-blue-100 text-xs font-semibold tracking-wide">Total Sales</span>
              <div class="bg-white/20 backdrop-blur-sm p-2 rounded-xl">
                <ShoppingBag class="h-4 w-4 text-white" />
              </div>
            </div>
            <h3 class="text-2xl font-display font-bold text-white tracking-tight mb-2">
              {{ formatCurrency(summary.revenue) }}
            </h3>
            <span class="inline-flex items-center gap-1 text-xs text-blue-100 bg-white/15 backdrop-blur-sm px-2.5 py-0.5 rounded-full font-medium">
              <TrendingUp class="h-3 w-3" />
              {{ summary.totalSalesCount }} bills
            </span>
            <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-white/5 rounded-full"></div>
          </div>
        </div>

        <!-- CASH COLLECTED -->
        <div class="relative overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300">
          <div class="bg-gradient-to-br from-emerald-500 to-emerald-700 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-emerald-100 text-xs font-semibold tracking-wide">Cash Collected</span>
              <div class="bg-white/20 backdrop-blur-sm p-2 rounded-xl">
                <CheckCircle class="h-4 w-4 text-white" />
              </div>
            </div>
            <h3 class="text-2xl font-display font-bold text-white tracking-tight mb-2">
              {{ formatCurrency(summary.creditCollected) }}
            </h3>
            <span class="inline-flex items-center gap-1 text-xs text-emerald-100 bg-white/15 backdrop-blur-sm px-2.5 py-0.5 rounded-full font-medium">
              <TrendingUp class="h-3 w-3" />
              {{ collectionRate }}% Rate
            </span>
            <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-white/5 rounded-full"></div>
          </div>
        </div>

        <!-- MONEY TO COLLECT -->
        <div class="relative overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300">
          <div class="bg-gradient-to-br from-rose-500 to-rose-700 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-rose-100 text-xs font-semibold tracking-wide">Money to Collect</span>
              <div class="bg-white/20 backdrop-blur-sm p-2 rounded-xl">
                <Clock class="h-4 w-4 text-white" />
              </div>
            </div>
            <h3 class="text-2xl font-display font-bold text-white tracking-tight mb-2">
              {{ formatCurrency(summary.creditPending) }}
            </h3>
            <span class="inline-flex items-center gap-1 text-xs text-rose-100 bg-white/15 backdrop-blur-sm px-2.5 py-0.5 rounded-full font-medium">
              <PhoneCall class="h-3 w-3" />
              Outstanding
            </span>
            <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-white/5 rounded-full"></div>
          </div>
        </div>

        <!-- PROFIT MARGIN -->
        <div class="relative overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300">
          <div class="bg-gradient-to-br from-teal-500 to-teal-700 p-5">
            <div class="flex items-center justify-between mb-3">
              <span class="text-teal-100 text-xs font-semibold tracking-wide">Profit Margin</span>
              <div class="bg-white/20 backdrop-blur-sm p-2 rounded-xl">
                <TrendingUp class="h-4 w-4 text-white" />
              </div>
            </div>
            <h3 class="text-2xl font-display font-bold text-white tracking-tight mb-1.5">
              {{ summary.revenue > 0 ? Math.round(((summary.revenue - summary.cogs) / summary.revenue) * 100) : 0 }}%
            </h3>
            <div class="w-full bg-white/20 rounded-full h-1.5 mb-1">
              <div 
                class="h-1.5 rounded-full bg-white/80 transition-all duration-700"
                :style="{ width: `${Math.min(summary.revenue > 0 ? ((summary.revenue - summary.cogs) / summary.revenue) * 100 : 0, 100)}%` }"
              ></div>
            </div>
            <span class="text-xs text-teal-100 font-medium">
              {{ formatCurrency(summary.revenue - summary.cogs) }} profit
            </span>
            <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-white/5 rounded-full"></div>
          </div>
        </div>

        <!-- WRITTEN-OFF BAD DEBT (only shown if > 0) -->
        <div 
          v-if="summary.writtenOffOutstanding > 0"
          class="col-span-2 relative overflow-hidden rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300"
        >
          <div class="bg-gradient-to-br from-amber-500 to-amber-700 p-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <div class="bg-white/20 backdrop-blur-sm p-2 rounded-xl">
                <AlertTriangle class="h-4 w-4 text-white" />
              </div>
              <div>
                <span class="text-amber-100 text-xs font-semibold tracking-wide block">Uncollected Bad Debt</span>
                <span class="text-lg font-display font-bold text-white">
                  {{ formatCurrency(summary.writtenOffOutstanding) }}
                </span>
              </div>
            </div>
            <span class="text-xs text-amber-100 bg-white/15 backdrop-blur-sm px-3 py-1 rounded-full font-medium">
              Written off, not collected
            </span>
            <div class="absolute -right-4 -bottom-4 w-20 h-20 bg-white/5 rounded-full"></div>
          </div>
        </div>
      </div>

      <!-- QUICK ACTIONS -->
      <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
        <h3 class="font-display font-bold text-slate-900 text-sm text-left mb-1">Quick Actions</h3>
        <p class="text-xs text-slate-500 font-sans text-left mb-4">Jump straight to common tasks</p>
        
        <div class="grid grid-cols-2 gap-3">
          <button 
            id="quick-act-restock"
            @click="emit('quickAction', 'restock')"
            class="flex items-center gap-3 p-3.5 bg-gradient-to-r from-emerald-50 to-emerald-100 rounded-xl border-2 border-emerald-200 text-emerald-800 hover:from-emerald-100 hover:to-emerald-200 hover:border-emerald-300 transition-all group cursor-pointer"
          >
            <div class="bg-emerald-500 text-white p-2.5 rounded-xl group-hover:scale-110 transition-transform shadow-md shrink-0">
              <Package class="h-5 w-5" />
            </div>
            <div class="text-left">
              <span class="font-display text-sm font-bold block">Restock</span>
              <span class="font-sans text-[10px] text-emerald-600">Log brand supply</span>
            </div>
          </button>

          <button 
            id="quick-act-sale-vehicle"
            @click="emit('quickAction', 'vehicle-sale')"
            class="flex items-center gap-3 p-3.5 bg-gradient-to-r from-blue-50 to-blue-100 rounded-xl border-2 border-blue-200 text-blue-900 hover:from-blue-100 hover:to-blue-200 hover:border-blue-300 transition-all group cursor-pointer"
          >
            <div class="bg-blue-600 text-white p-2.5 rounded-xl group-hover:scale-110 transition-transform shadow-md shrink-0">
              <Truck class="h-5 w-5" />
            </div>
            <div class="text-left">
              <span class="font-display text-sm font-bold block">Vehicle Sale</span>
              <span class="font-sans text-[10px] text-blue-600">By license plate</span>
            </div>
          </button>

          <button 
            id="quick-act-sale-dsr"
            @click="emit('quickAction', 'dsr-sale')"
            class="flex items-center gap-3 p-3.5 bg-gradient-to-r from-violet-50 to-violet-100 rounded-xl border-2 border-violet-200 text-violet-900 hover:from-violet-100 hover:to-violet-200 hover:border-violet-300 transition-all group cursor-pointer"
          >
            <div class="bg-violet-500 text-white p-2.5 rounded-xl group-hover:scale-110 transition-transform shadow-md shrink-0">
              <User class="h-5 w-5" />
            </div>
            <div class="text-left">
              <span class="font-display text-sm font-bold block">Rep Sale</span>
              <span class="font-sans text-[10px] text-violet-600">DSR outward</span>
            </div>
          </button>

          <button 
            id="quick-act-collect"
            @click="emit('navigate', 'collections')"
            class="flex items-center gap-3 p-3.5 bg-gradient-to-r from-rose-50 to-rose-100 rounded-xl border-2 border-rose-200 text-rose-800 hover:from-rose-100 hover:to-rose-200 hover:border-rose-300 transition-all group cursor-pointer"
          >
            <div class="bg-rose-500 text-white p-2.5 rounded-xl group-hover:scale-110 transition-transform shadow-md shrink-0">
              <DollarSign class="h-5 w-5" />
            </div>
            <div class="text-left">
              <span class="font-display text-sm font-bold block">Collect</span>
              <span class="font-sans text-[10px] text-rose-600">Record cash received</span>
            </div>
          </button>
        </div>
      </div>

      <!-- 2-COLUMN MIDDLE: DSR Performance + Vehicle/Products -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <!-- DSR PERFORMANCE -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
          <div class="flex justify-between items-center mb-4">
            <div class="text-left">
              <h3 class="font-display font-bold text-slate-900 text-sm">Sales Reps</h3>
              <p class="text-xs text-slate-500 font-sans mt-0.5">Performance overview</p>
            </div>
            <button 
              id="overview-btn-dsr-view"
              @click="emit('navigate', 'reports')"
              class="text-blue-600 text-xs font-display hover:underline font-bold inline-flex items-center gap-0.5 cursor-pointer"
            >
              All <ArrowUpRight class="h-3 w-3" />
            </button>
          </div>

          <div class="space-y-2.5 max-h-64 overflow-y-auto pr-1 scrollbar-thin">
            <div 
              v-for="(rep, idx) in dsrPerformance.slice(0, 5)" 
              :key="idx" 
              class="bg-slate-50 rounded-xl p-3 border border-slate-100 hover:border-slate-200 transition"
            >
              <div class="flex items-center gap-2.5 mb-2">
                <div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center text-white font-display font-bold text-xs shadow-sm shrink-0">
                  {{ getInitials(rep.name) }}
                </div>
                <div class="text-left min-w-0 flex-1">
                  <span class="font-display font-semibold text-slate-800 text-xs block truncate">{{ rep.name }}</span>
                  <span class="text-[10px] text-slate-500 font-sans block">
                    {{ rep.role === 'Order Collector' ? `Collector under ${rep.parentDsrName || 'Dealer'}` : 'DSR' }}
                  </span>
                </div>
                <span class="text-[10px] text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full font-bold shrink-0">
                  {{ rep.count }} bills
                </span>
              </div>
              <div class="flex gap-1.5">
                <div class="flex-1 bg-white rounded-lg px-2 py-1.5 text-center border border-slate-100">
                  <p class="text-[9px] text-slate-400 font-semibold uppercase">Sales</p>
                  <p class="text-xs font-bold text-slate-700">{{ formatCurrency(rep.totalSales) }}</p>
                </div>
                <div class="flex-1 bg-white rounded-lg px-2 py-1.5 text-center border border-slate-100">
                  <p class="text-[9px] text-emerald-500 font-semibold uppercase">Collected</p>
                  <p class="text-xs font-bold text-emerald-600">{{ formatCurrency(rep.collected) }}</p>
                </div>
                <div class="flex-1 bg-white rounded-lg px-2 py-1.5 text-center border border-slate-100">
                  <p class="text-[9px] text-rose-500 font-semibold uppercase">Pending</p>
                  <p :class="['text-xs font-bold', rep.pending > 0 ? 'text-rose-600' : 'text-slate-400']">
                    {{ formatCurrency(rep.pending) }}
                  </p>
                </div>
              </div>
            </div>
            <p v-if="dsrPerformance.length === 0" class="text-center text-xs text-slate-400 py-6 font-sans">No representatives yet.</p>
          </div>
        </div>

        <!-- VEHICLE TRACKER + TOP PRODUCTS (stacked) -->
        <div class="space-y-4">
          <!-- VEHICLE TRACKER -->
          <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div class="flex justify-between items-center mb-4">
              <div class="text-left">
                <h3 class="font-display font-bold text-slate-900 text-sm">Vehicle Tracker</h3>
                <p class="text-xs text-slate-500 font-sans mt-0.5">Active delivery vehicles</p>
              </div>
              <button 
                @click="emit('navigate', 'collections')"
                class="text-blue-600 text-xs font-display hover:underline font-bold inline-flex items-center gap-0.5 cursor-pointer"
              >
                Reconcile <ArrowUpRight class="h-3 w-3" />
              </button>
            </div>

            <div class="space-y-2 max-h-36 overflow-y-auto pr-1 scrollbar-thin">
              <div 
                v-for="(v, idx) in dashboardVehicles.slice(0, 4)" 
                :key="idx" 
                class="flex items-center justify-between bg-slate-50 rounded-xl p-3 border border-slate-100 hover:border-slate-200 transition"
              >
                <div class="flex items-center gap-2 text-left">
                  <div class="bg-gradient-to-br from-blue-500 to-blue-600 text-white px-2.5 py-1 rounded-lg font-mono text-[10px] font-extrabold tracking-wider shadow-sm flex items-center gap-1 shrink-0">
                    <Truck class="h-3 w-3" />
                    {{ v.vehicle }}
                  </div>
                  <div>
                    <p class="text-xs font-semibold text-slate-700">{{ v.count }} deliveries</p>
                    <p class="text-[10px] text-slate-400 font-sans">{{ formatCurrency(v.total) }}</p>
                  </div>
                </div>
                <div class="text-right shrink-0">
                  <p :class="['text-xs font-bold', v.pending > 0 ? 'text-rose-600' : 'text-emerald-600']">
                    {{ v.pending > 0 ? formatCurrency(v.pending) : 'Paid ✓' }}
                  </p>
                </div>
              </div>
              <p v-if="dashboardVehicles.length === 0" class="text-center text-xs text-slate-400 py-4 font-sans">No active vehicles.</p>
            </div>
          </div>

          <!-- TOP PRODUCTS -->
          <div class="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <div class="text-left mb-4">
              <h3 class="font-display font-bold text-slate-900 text-sm">Top Products</h3>
              <p class="text-xs text-slate-500 font-sans mt-0.5">Best sellers this month</p>
            </div>

            <div class="space-y-2 max-h-36 overflow-y-auto pr-1 scrollbar-thin">
              <div 
                v-for="(perf, idx) in productPerformance.slice(0, 5)" 
                :key="idx" 
                class="flex items-center justify-between bg-slate-50 rounded-xl p-2.5 border border-slate-100 hover:border-slate-200 transition"
              >
                <div class="flex items-center gap-2.5 text-left min-w-0">
                  <div 
                    :class="['w-7 h-7 rounded-full flex items-center justify-center font-display font-bold text-xs shadow-sm shrink-0', rankBadgeClass(idx)]"
                  >
                    {{ idx + 1 }}
                  </div>
                  <div class="min-w-0">
                    <h4 class="font-sans font-semibold text-slate-800 text-xs truncate">{{ perf.name }}</h4>
                    <p class="text-[10px] text-slate-400">{{ perf.quantity }} units</p>
                  </div>
                </div>
                <span class="font-display font-bold text-slate-800 text-xs shrink-0 ml-2">
                  {{ formatCurrency(perf.total) }}
                </span>
              </div>
              <p v-if="productPerformance.length === 0" class="text-center text-xs text-slate-400 py-4 font-sans">No sales data yet.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════════
         RIGHT COLUMN — Charts Sidebar
         ═══════════════════════════════════════════════════════════ -->
    <aside class="dashboard-charts">
      <!-- Financial Overview Bar Chart -->
      <ChartCard title="Financial Overview" subtitle="Revenue & collections">
        <div v-if="summary.revenue === 0" class="flex flex-col items-center justify-center text-slate-400 space-y-2" style="height: 200px">
          <TrendingUp class="h-8 w-8" />
          <span class="text-xs font-sans">No sales yet.</span>
        </div>
        <div v-else style="height: 200px">
          <BaseChart chartType="bar" :chartData="revenueBarData" :chartOptions="revenueBarOptions" />
        </div>
      </ChartCard>

      <!-- Sales Trend Line Chart -->
      <ChartCard title="Sales Trend" subtitle="Last 7 days revenue">
        <div v-if="!sales || sales.length === 0" class="flex flex-col items-center justify-center text-slate-400 space-y-2" style="height: 180px">
          <TrendingUp class="h-8 w-8" />
          <span class="text-xs font-sans">No data yet.</span>
        </div>
        <div v-else style="height: 180px">
          <BaseChart chartType="line" :chartData="salesTrendData" :chartOptions="salesTrendOptions" />
        </div>
      </ChartCard>

      <!-- Payment Mix Doughnut Chart -->
      <ChartCard title="Payment Mix" subtitle="Cash vs Credit">
        <div v-if="!sales || sales.length === 0" class="flex flex-col items-center justify-center text-slate-400 space-y-2" style="height: 180px">
          <DollarSign class="h-8 w-8" />
          <span class="text-xs font-sans">No payments yet.</span>
        </div>
        <div v-else style="height: 180px">
          <BaseChart chartType="doughnut" :chartData="paymentDoughnutData" :chartOptions="paymentDoughnutOptions" />
        </div>
      </ChartCard>
    </aside>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════════
   3-COLUMN DASHBOARD LAYOUT
   Desktop: Middle (flex-1) + Right Charts Sidebar (380px)
   Tablet/Mobile: Single column stack
   ═══════════════════════════════════════════════════════════════ */
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

/* Middle — operational content, natural flow */
.dashboard-middle {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Right — charts sidebar, sticky on desktop */
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

/* Animations */
@keyframes pulse-slow {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.92; }
}
.animate-pulse-slow {
  animation: pulse-slow 2.5s ease-in-out infinite;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fadeIn {
  animation: fadeIn 0.5s ease-out;
}

/* Scrollbar styling */
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 999px;
}
.scrollbar-thin::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
