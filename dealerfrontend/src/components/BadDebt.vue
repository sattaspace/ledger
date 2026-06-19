<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { 
  AlertTriangle, 
  Search, 
  User, 
  Calendar, 
  DollarSign,
  ChevronLeft,
  ChevronRight,
  FileText,
  Download,
  X
} from 'lucide-vue-next';
import { useFormatters } from '../composables/useFormatters';
import type { SaleRecord } from '../types';
// Audit fix GAP C-1: import usePermissions for operation-level enforcement.
import { usePermissions } from "../composables/usePermissions";

const { can, canEdit } = usePermissions();

const props = defineProps<{
  sales: SaleRecord[];
  formatCurrency?: (amt: number) => string;
}>();

const emit = defineEmits<{
  (e: 'refreshData'): void;
}>();

// Search & filters
const searchQuery = ref('');
const selectedPeriod = ref<'ALL' | 'TODAY' | 'WEEK' | 'MONTH' | 'QUARTER' | 'YEAR'>('ALL');

// Pagination
const currentPage = ref(1);
const itemsPerPage = 10;

// Reset page when filters change
watch([searchQuery, selectedPeriod], () => {
  currentPage.value = 1;
});

// Filter written-off sales
const writtenOffSales = computed(() => {
  return props.sales.filter(s => s.isClosedWithDue || s.collectionStatus === 'Written Off');
});

// Filter by search and period
const filteredSales = computed(() => {
  let filtered = writtenOffSales.value;
  
  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase();
    filtered = filtered.filter(s => 
      s.customerName.toLowerCase().includes(q) ||
      s.productName.toLowerCase().includes(q) ||
      s.dsrName?.toLowerCase().includes(q) ||
      s.vehicleNumber?.toLowerCase().includes(q)
    );
  }
  
  // Period filter
  const now = new Date();
  if (selectedPeriod.value !== 'ALL') {
    filtered = filtered.filter(s => {
      const saleDate = new Date(s.date);
      const diffDays = (now.getTime() - saleDate.getTime()) / (1000 * 60 * 60 * 24);
      
      switch (selectedPeriod.value) {
        case 'TODAY': return diffDays < 1;
        case 'WEEK': return diffDays <= 7;
        case 'MONTH': return diffDays <= 30;
        case 'QUARTER': return diffDays <= 90;
        case 'YEAR': return diffDays <= 365;
        default: return true;
      }
    });
  }
  
  return filtered.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
});

// Pagination
const totalPages = computed(() => Math.ceil(filteredSales.value.length / itemsPerPage));
const currentSales = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return filteredSales.value.slice(start, start + itemsPerPage);
});

// Totals - match calculation with Reports.vue
const totalWrittenOff = computed(() => 
  filteredSales.value.reduce((sum, s) => sum + Math.max(0, (s.totalAmount || 0) - (s.amountPaid || 0)), 0)
);
const totalCount = computed(() => filteredSales.value.length);
const totalQuantity = computed(() => 
  filteredSales.value.reduce((sum, s) => sum + s.quantity, 0)
);

// Export to CSV
const isExporting = ref(false);
const handleExport = async () => {
  isExporting.value = true;
  try {
    const headers = ['Date', 'Customer', 'Phone', 'Product', 'Qty', 'Total Amount', 'Balance Due', 'DSR', 'Vehicle'];
    const rows = filteredSales.value.map(s => [
      new Date(s.date).toLocaleDateString('en-IN'),
      s.customerName,
      s.customerPhone || 'N/A',
      s.productName,
      s.quantity,
      s.totalAmount,
      s.balanceDue,
      s.dsrName || 'N/A',
      s.vehicleNumber || 'N/A'
    ]);
    
    const csv = [headers.join(','), ...rows.map((r: any[]) => r.map((f: any) => `"${f}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bad_debt_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    alert(`✓ Exported ${rows.length} bad debt records`);
  } finally {
    isExporting.value = false;
  }
};

// Use shared formatter
const { formatCurrency } = useFormatters({ formatCurrency: props.formatCurrency });
</script>

<template>
  <div class="space-y-5 animate-fadeIn">
    <!-- HEADER -->
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 class="font-bold text-slate-800 text-lg flex items-center gap-2">
            <AlertTriangle class="h-6 w-6 text-amber-500" />
            Bad Debt / Written Off
          </h2>
          <p class="text-sm text-slate-400 mt-1">All written-off sales and unrecoverable debts</p>
        </div>
        <!-- Audit fix GAP C-1: gate Export button by bad_debt feature permission -->
        <button
          v-if="can('bad_debt').value"
          @click="handleExport"
          :disabled="isExporting"
          class="min-h-[40px] px-5 py-2.5 rounded-xl flex items-center gap-2 bg-amber-100 text-amber-700 border border-amber-200 hover:bg-amber-200 transition font-semibold text-sm disabled:opacity-50"
        >
          <Download v-if="!isExporting" class="h-4 w-4" />
          <span v-else class="animate-spin">⟳</span>
          <span>{{ isExporting ? 'Exporting...' : 'Export CSV' }}</span>
        </button>
      </div>

      <!-- SUMMARY CARDS -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="bg-gradient-to-br from-amber-50 to-amber-100 p-4 rounded-xl border border-amber-200">
          <p class="text-xs text-amber-600 font-semibold uppercase">Total Bad Debt</p>
          <p class="text-2xl font-bold text-amber-700 font-mono mt-1">{{ formatCurrency(totalWrittenOff) }}</p>
        </div>
        <div class="bg-white p-4 rounded-xl border border-slate-200">
          <p class="text-xs text-slate-400 font-semibold uppercase">Invoices Written Off</p>
          <p class="text-2xl font-bold text-slate-700 mt-1">{{ totalCount }}</p>
        </div>
        <div class="bg-white p-4 rounded-xl border border-slate-200">
          <p class="text-xs text-slate-400 font-semibold uppercase">Total Quantity</p>
          <p class="text-2xl font-bold text-slate-700 mt-1">{{ totalQuantity }} units</p>
        </div>
      </div>

      <!-- FILTERS -->
      <div class="flex flex-col sm:flex-row gap-3">
        <div class="relative flex-1 max-w-md">
          <Search class="absolute left-3 top-3 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            v-model="searchQuery"
            placeholder="Search by customer, product, DSR..."
            class="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          />
        </div>
        <select 
          v-model="selectedPeriod"
          class="px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm cursor-pointer"
        >
          <option value="ALL">All Time</option>
          <option value="TODAY">Today</option>
          <option value="WEEK">This Week</option>
          <option value="MONTH">This Month</option>
          <option value="QUARTER">This Quarter</option>
          <option value="YEAR">This Year</option>
        </select>
      </div>
    </div>

    <!-- DATA TABLE -->
    <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      <!-- Empty State -->
      <div v-if="filteredSales.length === 0" class="p-12 text-center">
        <div class="w-16 h-16 mx-auto mb-4 bg-slate-100 rounded-full flex items-center justify-center">
          <FileText class="h-8 w-8 text-slate-400" />
        </div>
        <h3 class="text-lg font-semibold text-slate-700 mb-2">No Bad Debt Records</h3>
        <p class="text-slate-400">No written-off sales found for the selected filters.</p>
      </div>

      <!-- Table -->
      <div v-else class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-4 py-3 font-semibold text-slate-600">Date</th>
              <th class="px-4 py-3 font-semibold text-slate-600">Customer</th>
              <th class="px-4 py-3 font-semibold text-slate-600">Product</th>
              <th class="px-4 py-3 font-semibold text-slate-600 text-right">Qty</th>
              <th class="px-4 py-3 font-semibold text-slate-600 text-right">Total</th>
              <th class="px-4 py-3 font-semibold text-slate-600 text-right">Balance Due</th>
              <th class="px-4 py-3 font-semibold text-slate-600">DSR</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="sale in currentSales" 
              :key="sale.id"
              class="border-b border-slate-100 hover:bg-slate-50 transition"
            >
              <td class="px-4 py-3 text-slate-600 whitespace-nowrap">
                {{ new Date(sale.date).toLocaleDateString('en-IN') }}
              </td>
              <td class="px-4 py-3">
                <div class="font-medium text-slate-800">{{ sale.customerName }}</div>
                <div v-if="sale.customerPhone" class="text-xs text-slate-400">{{ sale.customerPhone }}</div>
              </td>
              <td class="px-4 py-3 text-slate-700">{{ sale.productName }}</td>
              <td class="px-4 py-3 text-right text-slate-700">{{ sale.quantity }}</td>
              <td class="px-4 py-3 text-right font-mono text-slate-600">{{ formatCurrency(sale.totalAmount) }}</td>
              <td class="px-4 py-3 text-right font-mono font-semibold text-amber-600">{{ formatCurrency(sale.balanceDue) }}</td>
              <td class="px-4 py-3">
                <span v-if="sale.dsrName" class="inline-block px-2 py-1 bg-slate-100 rounded text-xs text-slate-600">
                  {{ sale.dsrName }}
                </span>
                <span v-else class="text-slate-400 text-xs">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-between px-4 py-3 bg-slate-50 border-t border-slate-200">
        <button 
          @click="currentPage = Math.max(1, currentPage - 1)"
          :disabled="currentPage === 1"
          class="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition"
        >
          <ChevronLeft class="h-4 w-4" />
          Previous
        </button>
        <span class="text-sm text-slate-600">
          Page <strong>{{ currentPage }}</strong> of {{ totalPages }}
          <span class="text-slate-400">({{ filteredSales.length }} records)</span>
        </span>
        <button 
          @click="currentPage = Math.min(currentPage + 1, totalPages)"
          :disabled="currentPage === totalPages"
          class="flex items-center gap-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition"
        >
          Next
          <ChevronRight class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>
