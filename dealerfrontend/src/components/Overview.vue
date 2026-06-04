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
import type { Product, SaleRecord } from '../types';

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
  sales?: SaleRecord[];
  formatCurrency?: (amt: number) => string;
}>(), {
  sales: () => []
});

const emit = defineEmits<{
  (e: 'navigate', tab: string): void;
  (e: 'quickAction', actionType: string): void;
}>();

// Default currency formatter
const formatCurrency = computed(() => {
  return props.formatCurrency || ((amt: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  });
});

// Group pending/total sales by vehicle dynamically for dashboard KPIs
const dashboardVehicles = computed(() => {
  const vehicleGroups: Record<string, { total: number; pending: number; count: number }> = {};
  props.sales.forEach(sale => {
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

// Safe division for rates
const collectionRate = computed(() => {
  if (!props.summary || props.summary.revenue === 0) return 100;
  return Math.round((props.summary.creditCollected / props.summary.revenue) * 100);
});

// Max value for scale calculation in our custom financial flow visualizer
const maxFlowValue = computed(() => {
  if (!props.summary) return 1;
  return Math.max(props.summary.revenue, props.summary.creditCollected, props.summary.creditPending, 1);
});
</script>

<template>
  <div v-if="!summary" class="flex justify-center items-center h-64">
    <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
  </div>

  <div v-else class="space-y-4 font-sans animate-fadeIn">
    <!-- CRITICAL LOW STOCK BANNER ALERT -->
    <div v-if="summary.lowStockCount > 0" class="bg-amber-50 border-l-4 border-amber-500 p-3 rounded shadow-sm animate-pulse flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <AlertTriangle class="h-5 w-5 text-amber-600 shrink-0" />
        <div class="text-left">
          <p class="font-display font-semibold text-amber-900 text-xs md:text-sm">
            {{ summary.lowStockCount }} Products are running very low!
          </p>
          <p class="text-[11px] text-amber-700 font-sans mt-0.5">
            Brands & products like 
            <span class="font-semibold">{{ summary.lowStockItems.slice(0, 3).map(p => p.name).join(', ') }}</span> 
            are below safety thresholds. Restock immediately to avoid losing customers.
          </p>
        </div>
      </div>
      <button 
        id="overview-btn-quick-restock"
        @click="emit('navigate', 'inventory')"
        class="bg-amber-600 text-white font-display text-[11px] font-bold px-3 py-1.5 rounded hover:bg-amber-700 transition shrink-0 ml-3 cursor-pointer"
      >
        Restock Now
      </button>
    </div>

    <!-- 4 BENTO QUICK METRICS -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- REVENUE -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm flex items-center justify-between">
        <div class="space-y-1 text-left">
          <span class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Total Sales done</span>
          <h3 class="text-xl md:text-2xl font-display font-semibold text-slate-900 tracking-tight">
            {{ formatCurrency(summary.revenue) }}
          </h3>
          <span class="text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded inline-flex items-center font-semibold">
            <TrendingUp class="h-3 w-3 mr-1" />
            {{ summary.totalSalesCount }} bills
          </span>
        </div>
        <div class="bg-blue-50 p-2.5 rounded text-blue-600 shrink-0">
          <ShoppingBag class="h-5 w-5" />
        </div>
      </div>

      <!-- CASH COLLECTED -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm flex items-center justify-between">
        <div class="space-y-1 text-left">
          <span class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Collected Cash</span>
          <h3 class="text-xl md:text-2xl font-display font-semibold text-emerald-700 tracking-tight">
            {{ formatCurrency(summary.creditCollected) }}
          </h3>
          <span class="text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded inline-flex items-center font-semibold">
            <CheckCircle class="h-3 w-3 mr-1" />
            {{ collectionRate }}% Cash Speed
          </span>
        </div>
        <div class="bg-emerald-50 p-2.5 rounded text-emerald-600 shrink-0">
          <DollarSign class="h-5 w-5" />
        </div>
      </div>

      <!-- OUTSTANDING CREDIT -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm flex items-center justify-between">
        <div class="space-y-1 text-left">
          <span class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Credit given (To Collect)</span>
          <h3 class="text-xl md:text-2xl font-display font-semibold text-rose-600 tracking-tight">
            {{ formatCurrency(summary.creditPending) }}
          </h3>
          <span class="text-[11px] text-rose-700 bg-rose-50 px-2 py-0.5 rounded inline-flex items-center font-semibold">
            <Clock class="h-3 w-3 mr-1" />
            Outstanding
          </span>
        </div>
        <div class="bg-rose-50 p-2.5 rounded text-rose-600 shrink-0">
          <PhoneCall class="h-5 w-5" />
        </div>
      </div>

      <!-- LOW STOCK ALERT COUNT -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm flex items-center justify-between">
        <div class="space-y-1 text-left">
          <span class="text-slate-400 text-[10px] uppercase font-bold tracking-wider">Low Stock Products</span>
          <h3 class="text-xl md:text-2xl font-display font-semibold text-amber-600 tracking-tight">
            {{ summary.lowStockCount }} items
          </h3>
          <span class="text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded inline-flex items-center">
            Threshold alert
          </span>
        </div>
        <div class="bg-amber-50 p-2.5 rounded text-amber-500 shrink-0">
          <Package class="h-5 w-5" />
        </div>
      </div>
    </div>

    <!-- QUICK EASY ACTIONS -->
    <div class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-2">
      <h3 class="font-display font-semibold text-slate-900 text-sm text-left">⚡ Quick Staff Operations Desk</h3>
      <p class="text-[11px] text-slate-500 font-sans mt-0.5 text-left">Click any option below to immediately manage the outward restocks, sales bills, or payments ledger.</p>
      
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3 pt-1">
        <!-- Quick stock in -->
        <button 
          id="quick-act-restock"
          @click="emit('quickAction', 'restock')"
          class="flex flex-col items-center justify-center p-3 bg-emerald-50 rounded border border-emerald-100 text-emerald-800 hover:bg-emerald-100/80 transition group cursor-pointer"
        >
          <div class="bg-emerald-500 text-white p-2 rounded group-hover:scale-105 transition shadow-sm">
            <Package class="h-4 w-4" />
          </div>
          <span class="font-display text-xs font-bold mt-2">Stock Restock In</span>
          <span class="font-sans text-[9px] text-emerald-600 mt-0.5">Log Brand Supply</span>
        </button>

        <!-- Quick vehicle sale -->
        <button 
          id="quick-act-sale-vehicle"
          @click="emit('quickAction', 'vehicle-sale')"
          class="flex flex-col items-center justify-center p-3 bg-blue-50 rounded border border-blue-100 text-blue-900 hover:bg-blue-100/80 transition group cursor-pointer"
        >
          <div class="bg-blue-600 text-white p-2 rounded group-hover:scale-105 transition shadow-sm">
            <Truck class="h-4 w-4" />
          </div>
          <span class="font-display text-xs font-bold mt-2">Vehicle Sales Out</span>
          <span class="font-sans text-[9px] text-blue-600 mt-0.5">By License Plate</span>
        </button>

        <!-- Quick DSR sale -->
        <button 
          id="quick-act-sale-dsr"
          @click="emit('quickAction', 'dsr-sale')"
          class="flex flex-col items-center justify-center p-3 bg-cyan-50 rounded border border-cyan-100 text-cyan-800 hover:bg-cyan-100/80 transition group cursor-pointer"
        >
          <div class="bg-cyan-500 text-white p-2 rounded group-hover:scale-105 transition shadow-sm">
            <User class="h-4 w-4" />
          </div>
          <span class="font-display text-xs font-bold mt-2">DSR Sales Out</span>
          <span class="font-sans text-[9px] text-cyan-600 mt-0.5">Representative Outward</span>
        </button>

        <!-- Quick collection payment -->
        <button 
          id="quick-act-collect"
          @click="emit('navigate', 'collections')"
          class="flex flex-col items-center justify-center p-3 bg-rose-50 rounded border border-rose-100 text-rose-800 hover:bg-rose-100/80 transition group cursor-pointer"
        >
          <div class="bg-rose-500 text-white p-2 rounded group-hover:scale-105 transition shadow-sm">
            <DollarSign class="h-4 w-4" />
          </div>
          <span class="font-display text-xs font-bold mt-2">Collect Outstanding</span>
          <span class="font-sans text-[9px] text-rose-600 mt-0.5">Credit Reconciliation</span>
        </button>
      </div>
    </div>

    <!-- MID SECTION - Charts and Staff Representatives Collections -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <!-- CHART SECTION (LUXURY CORRUPT-FREE NATIVE SVG/CSS CHANNELS) -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm lg:col-span-7 space-y-4">
        <div class="text-left">
          <h3 class="font-display font-semibold text-slate-900 text-sm">📊 Financial Cash Flow Split</h3>
          <p class="text-[11px] text-slate-500 font-sans">Visual proportion of total transactions this month</p>
        </div>
        
        <div class="h-56 mt-2 flex flex-col justify-end">
          <div v-if="summary.revenue === 0" class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
            <TrendingUp class="h-6 w-6" />
            <span class="text-[11px] font-sans">No sales recorded yet to plot dashboard charts.</span>
          </div>

          <!-- Pristine, responsive reactive dashboard chart bar channels -->
          <div v-else class="h-full w-full flex flex-col justify-between pt-4">
            <div class="flex-1 flex items-end justify-around gap-8 px-4 pb-3">
              <!-- Column 1: Total Sales -->
              <div class="flex flex-col items-center w-24 group">
                <div class="text-[10px] font-bold text-slate-500 mb-1 font-mono">
                  {{ formatCurrency(summary.revenue) }}
                </div>
                <div 
                  class="w-8 bg-blue-600 rounded-t transition-all duration-500 shadow-sm group-hover:opacity-90 cursor-default"
                  :style="{ height: `${(summary.revenue / maxFlowValue) * 120}px` }"
                ></div>
                <div class="text-[11px] font-semibold text-slate-600 mt-2 font-display">Total Sales</div>
              </div>

              <!-- Column 2: Cash Collected -->
              <div class="flex flex-col items-center w-24 group">
                <div class="text-[10px] font-bold text-emerald-600 mb-1 font-mono">
                  {{ formatCurrency(summary.creditCollected) }}
                </div>
                <div 
                  class="w-8 bg-emerald-500 rounded-t transition-all duration-500 shadow-sm group-hover:opacity-90 cursor-default"
                  :style="{ height: `${(summary.creditCollected / maxFlowValue) * 120}px` }"
                ></div>
                <div class="text-[11px] font-semibold text-slate-600 mt-2 font-display">Collected Cash</div>
              </div>

              <!-- Column 3: Outstanding Credit -->
              <div class="flex flex-col items-center w-24 group">
                <div class="text-[10px] font-bold text-rose-600 mb-1 font-mono">
                  {{ formatCurrency(summary.creditPending) }}
                </div>
                <div 
                  class="w-8 bg-rose-500 rounded-t transition-all duration-500 shadow-sm group-hover:opacity-90 cursor-default"
                  :style="{ height: `${(summary.creditPending / maxFlowValue) * 120}px` }"
                ></div>
                <div class="text-[11px] font-semibold text-slate-600 mt-2 font-display">Credit Pending</div>
              </div>
            </div>
            
            <!-- Axis guideline divider -->
            <div class="h-[1px] bg-slate-200 w-full mb-1"></div>
            <div class="text-[9px] text-slate-400 font-sans text-center">Interactive dashboard reporting scales up dynamically based on invoice volume</div>
          </div>
        </div>
      </div>

      <!-- STAFF/DSR COLLECTIONS REPORT -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm lg:col-span-5 space-y-4">
        <div class="flex justify-between items-center">
          <div class="text-left">
            <h3 class="font-display font-semibold text-slate-900 text-sm">👥 Sales Rep Ledger (DSR)</h3>
            <p class="text-[11px] text-slate-500 font-sans">Sales, collections, & credit tracking per DSR</p>
          </div>
          <button 
            id="overview-btn-dsr-view"
            @click="emit('navigate', 'reports')"
            class="text-blue-500 text-xs font-display hover:underline font-bold inline-flex items-center cursor-pointer"
          >
            All Reps <ArrowUpRight class="h-3.5 w-3.5 ml-0.5" />
          </button>
        </div>

        <div class="space-y-2 max-h-56 overflow-y-auto pr-1 scrollbar-thin">
          <div v-for="(rep, idx) in summary.dsrPerformance.slice(0, 5)" :key="idx" class="p-2.5 bg-slate-50 rounded space-y-1 border border-slate-100 col-span-1">
            <div class="flex justify-between items-start gap-1">
              <div class="text-left">
                <span class="font-display font-semibold text-slate-800 text-xs block leading-tight">{{ rep.name }}</span>
                <span class="text-[8px] text-slate-500 font-sans mt-0.5 inline-block bg-slate-100 border border-slate-200 px-1.5 py-0.2 rounded font-bold uppercase">
                  {{ rep.role === 'Order Collector' ? `Collector: under ${rep.parentDsrName || 'Dealer'}` : 'DSR Representative' }}
                </span>
              </div>
              <span class="text-[10px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded font-black font-sans shrink-0 uppercase">
                {{ rep.count }} bills
              </span>
            </div>
            
            <div class="grid grid-cols-3 gap-1.5 text-center pt-1.5 border-t border-slate-200 font-sans">
              <div>
                <p class="text-[8px] text-slate-400 uppercase font-bold tracking-wider">Sales</p>
                <p class="text-[10px] font-bold text-slate-700">{{ formatCurrency(rep.totalSales) }}</p>
              </div>
              <div>
                <p class="text-[8px] text-slate-400 uppercase font-bold tracking-wider">Collected</p>
                <p class="text-[10px] font-bold text-emerald-600">{{ formatCurrency(rep.collected) }}</p>
              </div>
              <div>
                <p class="text-[8px] text-slate-400 uppercase font-bold tracking-wider text-rose-600">Pending</p>
                <p class="text-[10px] font-black font-mono :class=&quot;rep.pending > 0 ? 'text-rose-600' : 'text-slate-400'&quot;">
                  {{ formatCurrency(rep.pending) }}
                </p>
              </div>
            </div>
          </div>

          <p v-if="summary.dsrPerformance.length === 0" class="text-center text-[11px] text-slate-400 py-6 font-sans">No representatives registered yet.</p>
        </div>
      </div>
    </div>

    <!-- VEHICLES AND POPULAR PRODUCTS GRID -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <!-- VEHICLE OUTSTANDING TRACKER -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm lg:col-span-5 space-y-4">
        <div class="flex justify-between items-center">
          <div class="text-left">
            <h3 class="font-display font-semibold text-slate-900 text-sm">🚚 Shipping Vehicles Tracker</h3>
            <p class="text-[11px] text-slate-500 font-sans">Active deliveries to multiple retail grocery stores</p>
          </div>
          <button 
            @click="emit('navigate', 'collections')"
            class="text-blue-500 text-xs font-display hover:underline font-bold inline-flex items-center cursor-pointer"
          >
            Reconcile <ArrowUpRight class="h-3.5 w-3.5 ml-0.5" />
          </button>
        </div>

        <div class="space-y-2 max-h-56 overflow-y-auto pr-1 scrollbar-thin">
          <div v-for="(v, idx) in dashboardVehicles.slice(0, 5)" :key="idx" class="p-2.5 bg-slate-50 rounded border border-slate-100 flex items-center justify-between">
            <div class="space-y-1 text-left">
              <span class="inline-flex items-center space-x-1 text-blue-800 bg-blue-50 border border-blue-200 px-1.5 py-0.5 rounded text-[9px] font-mono tracking-wider font-extrabold uppercase">
                <Truck class="h-2.5 w-2.5 text-blue-700" />
                <span>{{ v.vehicle }}</span>
              </span>
              <p class="text-[9px] text-slate-400 font-sans">Carried drops for {{ v.count }} stores</p>
            </div>
            <div class="text-right font-sans">
              <p class="text-[8px] text-slate-400 font-bold uppercase">Pending</p>
              <p :class="['text-xs font-black', v.pending > 0 ? 'text-rose-600' : 'text-slate-400']">
                {{ v.pending > 0 ? formatCurrency(v.pending) : 'Fully Paid' }}
              </p>
              <p class="text-[8.5px] text-slate-450 font-mono">Cargo: {{ formatCurrency(v.total) }}</p>
            </div>
          </div>

          <p v-if="dashboardVehicles.length === 0" class="text-center text-[10px] text-slate-400 py-6 font-sans">No transport vehicles carrying active credit balances.</p>
        </div>
      </div>

      <!-- POPULAR PRODUCTS HOT LIST -->
      <div class="bg-white p-4 rounded border border-slate-200 shadow-sm lg:col-span-7 space-y-4">
        <div class="text-left">
          <h3 class="font-display font-semibold text-slate-900 text-sm">🔥 Top-Selling Brands & Products</h3>
          <p class="text-[11px] text-slate-500 font-sans">Items with the highest sales frequency this month</p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div v-for="(perf, idx) in summary.productPerformance.slice(0, 6)" :key="idx" class="flex items-center justify-between p-2.5 bg-slate-50 rounded border border-slate-100 font-sans">
            <div class="flex items-center space-x-3 text-left">
              <div class="bg-blue-600 text-white rounded h-7 w-7 flex items-center justify-center font-display font-bold text-xs shadow-sm">
                #{{ idx + 1 }}
              </div>
              <div>
                <h4 class="font-sans font-medium text-slate-850 text-xs line-clamp-1">{{ perf.name }}</h4>
                <p class="text-[10px] text-slate-400">Sold: {{ perf.quantity }} units</p>
              </div>
            </div>
            <div class="text-right">
              <span class="font-display font-semibold text-slate-800 text-xs font-mono">
                {{ formatCurrency(perf.total) }}
              </span>
            </div>
          </div>

          <p v-if="summary.productPerformance.length === 0" class="col-span-2 text-center text-[11px] text-slate-400 py-6 font-sans">No active sales logged to compile performance lists.</p>
        </div>
      </div>
    </div>
  </div>
</template>
