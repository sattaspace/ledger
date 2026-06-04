<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { 
  ShoppingBag, 
  Search, 
  Truck, 
  User, 
  DollarSign, 
  Calendar, 
  Coins,
  FileText,
  UserCheck,
  Tag,
  AlertCircle,
  Plus,
  X,
  Trash2
} from 'lucide-vue-next';
import type { Product, SaleRecord, DSR } from '../types';

const props = withDefaults(defineProps<{
  products: Product[];
  sales: SaleRecord[];
  dsrs: DSR[];
  quickActionType?: string | null;
  formatCurrency?: (amt: number) => string;
}>(), {
  quickActionType: null
});

const emit = defineEmits<{
  (e: 'addSale', saleData: any): void;
  (e: 'addBulkSales', bulkData: any): void;
  (e: 'refreshData'): void;
  (e: 'clearQuickActionType'): void;
}>();

const searchQuery = ref('');
const showLogForm = ref(false);
const isSubmitting = ref(false);
const formError = ref('');
const formSuccess = ref('');

const selectedPeriod = ref<'ALL' | 'TODAY' | 'WEEK' | 'MONTH' | 'QUARTER' | 'YEAR'>('ALL');
const sortBy = ref<'DATE_DESC' | 'DATE_ASC' | 'AMOUNT_DESC' | 'AMOUNT_ASC'>('DATE_DESC');
const currentPage = ref(1);
const itemsPerPage = 10;

// Watch details to reset page boundaries
watch([searchQuery, selectedPeriod, sortBy], () => {
  currentPage.value = 1;
});

const EXISTING_CUSTOMERS = [
  { name: 'Krishna Grocery Store', address: 'G Block, Pocket 2, Rohini', phone: '9911223344' },
  { name: 'Reliance Fresh', address: 'Metro Pillar 240, Sector 12, Dwarka', phone: '8822334455' },
  { name: 'Apna Mart', address: 'Apex Plaza, Sector 4, Malviya Nagar', phone: '9012345678' },
  { name: 'Shree Sai Traders', address: 'Gandhi Market, G.T. Road, Shahdara', phone: '9540011223' },
  { name: 'Ganpati Provision Store', address: 'Chowk Bazar, Near Shiv Temple, Sadar', phone: '9711055443' },
  { name: 'Super Value Supermarket', address: 'Lajpat Nagar II, Ring Road, Market', phone: '9650088776' },
  { name: 'Star Bazaar Express', address: 'Plot 4, Main High Road, Sector 55', phone: '9876543210' },
  { name: 'New Rajan Provision', address: 'Shop 4, Gali No. 2, Vikas Marg', phone: '9311022334' },
  { name: 'Balaji Grocery Mart', address: 'Sector 15, Near Central Park', phone: '9212033445' },
  { name: 'Golden Bakery & Retail', address: 'Shop 9, Model Town metro area', phone: '9810055443' }
];

// Dynamically aggregate sales history customers to suggestion pool
const allSuggestedCustomers = computed(() => {
  const list = [...EXISTING_CUSTOMERS];
  // Gather unique customer names from existing sales history
  const uniqueSalesCustomers = Array.from(new Set((props.sales || []).map(s => s.customerName))).map(name => {
    const matchingSale = props.sales.find(s => s.customerName === name);
    return {
      name,
      phone: matchingSale?.customerPhone || '',
      address: 'Active Local Customer'
    };
  });
  
  uniqueSalesCustomers.forEach(uc => {
    if (!list.some(item => item.name.toLowerCase() === uc.name.toLowerCase() || `${item.name} (${item.address})`.toLowerCase() === uc.name.toLowerCase())) {
      list.push(uc);
    }
  });
  return list;
});

// Form Fields - New Sale
const productId = ref('');
const quantity = ref('1');
const customerName = ref('');
const customerPhone = ref('');
const isVehicle = ref(true);
const vehicleNumber = ref('');
const dsrId = ref('');
const paymentType = ref<'Cash' | 'Credit'>('Cash');
const amountPaid = ref('');
const dueDate = ref('');

// Bulk Entry Mode Settings
const activeEntryMode = ref<'single' | 'bulk'>('single');

interface BulkRow {
  id: string;
  productId: string;
  quantity: string;
  customerName: string;
  customerPhone: string;
  paymentType: 'Cash' | 'Credit';
  amountPaid: string;
  dueDate: string;
}

const getDefaultDueDate = () => {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().split('T')[0];
};

const createEmptyRow = (): BulkRow => ({
  id: Math.random().toString(36).substring(2, 9),
  productId: '',
  quantity: '1',
  customerName: '',
  customerPhone: '',
  paymentType: 'Credit', // Most retail shops buy small products on credit from delivery vans
  amountPaid: '',
  dueDate: getDefaultDueDate()
});

const bulkRows = ref<BulkRow[]>([
  createEmptyRow(),
  createEmptyRow(),
  createEmptyRow(),
]);

const bulkVehicleNumber = ref('');
const bulkDsrId = ref('');

interface BulkDraft {
  id: string;
  vehicleNumber: string;
  dsrId: string;
  rows: BulkRow[];
  timestamp: string;
  name: string;
}

const drafts = ref<BulkDraft[]>([]);

onMounted(() => {
  try {
    const stored = localStorage.getItem('unique_vehicle_route_drafts');
    drafts.value = stored ? JSON.parse(stored) : [];
  } catch (_) {
    drafts.value = [];
  }
});

const saveCurrentAsDraft = () => {
  if (!bulkVehicleNumber.value) {
    formError.value = 'Please input a Vehicle Licence Number first before saving draft!';
    return;
  }
  const matchingDsrName = props.dsrs.find(d => d.id === bulkDsrId.value)?.name || 'No Rep Assigned';
  const activeRouteDrops = bulkRows.value.filter(r => r.productId || r.customerName).length;
  const description = `${bulkVehicleNumber.value || 'Draft-No-Plate'} [${matchingDsrName}] - ${activeRouteDrops} Drop Items`;

  const newDraft: BulkDraft = {
    id: Math.random().toString(36).substring(2, 9),
    vehicleNumber: bulkVehicleNumber.value,
    dsrId: bulkDsrId.value,
    rows: JSON.parse(JSON.stringify(bulkRows.value)),
    timestamp: new Date().toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' }),
    name: description
  };

  drafts.value = [newDraft, ...drafts.value];
  localStorage.setItem('unique_vehicle_route_drafts', JSON.stringify(drafts.value));
  formSuccess.value = `Saved vehicle route draft successfully!`;
  setTimeout(() => formSuccess.value = '', 3000);
};

const handleLoadDraft = (draft: BulkDraft) => {
  bulkVehicleNumber.value = draft.vehicleNumber;
  bulkDsrId.value = draft.dsrId;
  bulkRows.value = JSON.parse(JSON.stringify(draft.rows));
  formSuccess.value = `Restored route draft for vehicle ${draft.vehicleNumber}!`;
  setTimeout(() => formSuccess.value = '', 3500);
};

const handleDeleteDraft = (id: string, e: Event) => {
  e.stopPropagation();
  drafts.value = drafts.value.filter(d => d.id !== id);
  localStorage.setItem('unique_vehicle_route_drafts', JSON.stringify(drafts.value));
  formSuccess.value = 'Draft route deleted successfully.';
  setTimeout(() => formSuccess.value = '', 3000);
};

const handleAddBulkRow = () => {
  bulkRows.value.push(createEmptyRow());
};

const handleRemoveBulkRow = (id: string) => {
  if (bulkRows.value.length <= 1) {
    bulkRows.value = [createEmptyRow()];
    return;
  }
  bulkRows.value = bulkRows.value.filter(r => r.id !== id);
};

const handleUpdateBulkRow = (id: string, field: keyof BulkRow, value: any) => {
  bulkRows.value = bulkRows.value.map(row => {
    if (row.id === id) {
      return { ...row, [field]: value };
    }
    return row;
  });
};

const handleBulkSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';

  if (!bulkVehicleNumber.value) {
    formError.value = 'Delivery vehicle license number is required for bulk parcel drops!';
    return;
  }

  if (!bulkDsrId.value) {
    formError.value = 'Please select the assigned Representative in charge of this delivery vehicle route!';
    return;
  }

  // Filter out rows that are entirely blank/empty
  const validRows = bulkRows.value.filter(row => row.productId || row.customerName || row.customerPhone);
  if (validRows.length === 0) {
    formError.value = 'Please complete at least one store/customer drop row item.';
    return;
  }

  // Validation checks
  for (let i = 0; i < validRows.length; i++) {
    const row = validRows[i];
    const rowNum = i + 1;
    if (!row.productId) {
      formError.value = `Invoice row #${rowNum}: Please select a product item.`;
      return;
    }
    if (!row.customerName) {
      formError.value = `Invoice row #${rowNum}: Customer Retail Grocery Store name is required.`;
      return;
    }
    const qty = Number(row.quantity);
    if (isNaN(qty) || qty <= 0) {
      formError.value = `Invoice row #${rowNum}: Quantity must be a valid positive number.`;
      return;
    }
    const p = props.products.find(prod => prod.id === row.productId);
    if (!p) {
      formError.value = `Invoice row #${rowNum}: Selected product does not exist.`;
      return;
    }
    if (p.stock < qty) {
      formError.value = `Invoice row #${rowNum}: Insufficient stock alert for "${p.name}". Wanted ${qty} but database has only ${p.stock} units.`;
      return;
    }
    if (row.paymentType === 'Credit' && !row.dueDate) {
      formError.value = `Invoice row #${rowNum}: Credit transactions require a payment due date.`;
      return;
    }
  }

  isSubmitting.value = true;
  try {
    emit('addBulkSales', {
      isVehicle: true,
      vehicleNumber: bulkVehicleNumber.value,
      dsrId: bulkDsrId.value,
      entries: validRows.map(row => {
        const prod = props.products.find(p => p.id === row.productId)!;
        const parsedAmountPaid = row.paymentType === 'Cash'
          ? Number(row.quantity) * prod.sellingPrice
          : Number(row.amountPaid) || 0;

        return {
          productId: row.productId,
          quantity: Number(row.quantity),
          customerName: row.customerName,
          customerPhone: row.customerPhone,
          paymentType: row.paymentType,
          amountPaid: parsedAmountPaid,
          dueDate: row.paymentType === 'Credit' ? row.dueDate : undefined
        };
      })
    });

    formSuccess.value = `Successfully dispatched vehicle cargo with ${validRows.length} wholesale customer invoices logged!`;
    
    // Reset bulk forms
    bulkRows.value = [createEmptyRow(), createEmptyRow(), createEmptyRow()];
    bulkVehicleNumber.value = '';
    bulkDsrId.value = '';

    setTimeout(() => {
      showLogForm.value = false;
      formSuccess.value = '';
    }, 2200);
  } catch (err: any) {
    formError.value = err.message || 'Trouble submitting bulk sales ledger.';
  } finally {
    isSubmitting.value = false;
  }
};

// React to quick actions passed from parent
watch(() => props.quickActionType, (newVal) => {
  if (newVal) {
    if (newVal === 'vehicle-sale') {
      isVehicle.value = true;
    } else if (newVal === 'dsr-sale') {
      isVehicle.value = false;
    }
    showLogForm.value = true;
    emit('clearQuickActionType');
  }
}, { immediate: true });

const handleSaleSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';

  if (!productId.value) {
    formError.value = 'Please select a product from stock!';
    return;
  }
  
  const qty = Number(quantity.value);
  if (isNaN(qty) || qty <= 0) {
    formError.value = 'Quantity must be 1 or higher!';
    return;
  }

  const selectedProduct = props.products.find(p => p.id === productId.value);
  if (!selectedProduct) {
    formError.value = 'Invalid product selection!';
    return;
  }

  if (selectedProduct.stock < qty) {
    formError.value = `Out of Stock! You want ${qty}, but only have {{ selectedProduct.stock }} left in database.`;
    return;
  }

  if (!customerName.value) {
    formError.value = 'Retail Grocery Store / Customer name is required!';
    return;
  }

  if (isVehicle.value && !vehicleNumber.value) {
    formError.value = 'Please provide a delivery vehicle plate number!';
    return;
  }

  if (!dsrId.value) {
    formError.value = 'Please assign a sales representative or order collector to manage collection!';
    return;
  }

  if (paymentType.value === 'Credit' && !dueDate.value) {
    formError.value = 'Please select a repayment due date!';
    return;
  }

  isSubmitting.value = true;
  try {
    const parsedAmountPaid = paymentType.value === 'Cash' 
      ? qty * selectedProduct.sellingPrice 
      : Number(amountPaid.value) || 0;

    emit('addSale', {
      productId: productId.value,
      quantity: qty,
      customerName: customerName.value,
      customerPhone: customerPhone.value,
      isVehicle: isVehicle.value,
      vehicleNumber: isVehicle.value ? vehicleNumber.value : undefined,
      dsrId: dsrId.value || undefined,
      paymentType: paymentType.value,
      amountPaid: parsedAmountPaid,
      dueDate: paymentType.value === 'Credit' ? dueDate.value : undefined
    });

    formSuccess.value = `Direct sale registered successfully! Decremented inventory stock by ${qty}.`;
    
    // Reset forms
    productId.value = '';
    quantity.value = '1';
    customerName.value = '';
    customerPhone.value = '';
    vehicleNumber.value = '';
    dsrId.value = '';
    paymentType.value = 'Cash';
    amountPaid.value = '';
    dueDate.value = '';
    
    setTimeout(() => {
      showLogForm.value = false;
      formSuccess.value = '';
    }, 2500);
  } catch (err: any) {
    formError.value = err.message || 'Trouble submitting bills.';
  } finally {
    isSubmitting.value = false;
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

// Filter Sales lists
const periodFilteredSales = computed(() => {
  return (props.sales || []).filter(s => {
    if (selectedPeriod.value === 'ALL') return true;
    const d = new Date(s.date);
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    const day = now.getDate();
    
    if (selectedPeriod.value === 'TODAY') {
      return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
    }
    if (selectedPeriod.value === 'WEEK') {
      const diffTime = Math.abs(now.getTime() - d.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      return diffDays <= 7;
    }
    if (selectedPeriod.value === 'MONTH') {
      return d.getFullYear() === year && d.getMonth() === month;
    }
    if (selectedPeriod.value === 'QUARTER') {
      const curQuarter = Math.floor(month / 3);
      const dQuarter = Math.floor(d.getMonth() / 3);
      return d.getFullYear() === year && curQuarter === dQuarter;
    }
    if (selectedPeriod.value === 'YEAR') {
      return d.getFullYear() === year;
    }
    return true;
  });
});

const searchFilteredSales = computed(() => {
  const q = searchQuery.value.toLowerCase().trim();
  if (!q) return periodFilteredSales.value;

  return periodFilteredSales.value.filter(s => {
    const matchCustName = s.customerName.toLowerCase().includes(q);
    const matchProdName = s.productName.toLowerCase().includes(q);
    const matchVehicle = s.vehicleNumber && s.vehicleNumber.toLowerCase().includes(q);
    const matchDsr = s.dsrName && s.dsrName.toLowerCase().includes(q);
    return matchCustName || matchProdName || !!matchVehicle || !!matchDsr;
  });
});

const sortedSales = computed(() => {
  const copied = [...searchFilteredSales.value];
  if (sortBy.value === 'DATE_DESC') {
    copied.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  } else if (sortBy.value === 'DATE_ASC') {
    copied.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  } else if (sortBy.value === 'AMOUNT_DESC') {
    copied.sort((a, b) => (b.totalAmount || 0) - (a.totalAmount || 0));
  } else if (sortBy.value === 'AMOUNT_ASC') {
    copied.sort((a, b) => (a.totalAmount || 0) - (b.totalAmount || 0));
  }
  return copied;
});

const totalPages = computed(() => {
  return Math.ceil(sortedSales.value.length / itemsPerPage);
});

const currentSalesList = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return sortedSales.value.slice(start, start + itemsPerPage);
});

const indexOfFirstItem = computed(() => {
  return (currentPage.value - 1) * itemsPerPage;
});
</script>

<template>
  <div class="space-y-4 font-sans animate-fadeIn">
    <!-- HEADER ROW -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="text-left">
        <h2 class="text-lg md:text-xl font-display font-bold text-slate-800">🛒 Issue Products & Log Sales</h2>
        <p class="text-[11px] text-slate-500 font-sans mt-0.5">Issue custom stock under Vehicle Plates or Representative (DSR) ledger accounts</p>
      </div>

      <button 
        id="sales-btn-toggle-log"
        @click="showLogForm = !showLogForm"
        :class="['font-display text-xs px-3 py-2 rounded flex items-center space-x-1.5 transition font-bold leading-none cursor-pointer',
          showLogForm 
            ? 'bg-rose-600 text-white shadow-sm' 
            : 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
        ]"
      >
        <component :is="showLogForm ? X : Plus" class="h-3.5 w-3.5" />
        <span>{{ showLogForm ? 'Close Sale Desk' : 'Log Direct Sale / Outward' }}</span>
      </button>
    </div>

    <!-- REGISTER SALES BILL FORM -->
    <div v-if="showLogForm" class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-3 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-2 border-b border-slate-100">
        <h3 class="font-display font-bold text-slate-800 text-xs md:text-sm flex items-center space-x-2">
          <ShoppingBag class="h-4.5 w-4.5 text-blue-600" />
          <span>Log Deliveries & Issue Products Outward</span>
        </h3>
        <button id="sales-btn-close-form" @click="showLogForm = false" class="text-slate-400 hover:text-slate-600 cursor-pointer">
          <X class="h-4.5 w-4.5" />
        </button>
      </div>

      <!-- DUAL MODE SELECTOR BUTTONS -->
      <div class="flex border-b border-slate-200 pb-2">
        <button
          id="mode-choice-single"
          type="button"
          @click="activeEntryMode = 'single'; formError = ''; formSuccess = '';"
          :class="['pb-2 px-4 text-xs font-display font-bold transition-all border-b-2 cursor-pointer',
            activeEntryMode === 'single'
              ? 'border-blue-600 text-blue-600 font-extrabold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          ]"
        >
          👤 Single Outlet Drop / Counter Sale
        </button>
        <button
          id="mode-choice-bulk"
          type="button"
          @click="activeEntryMode = 'bulk'; formError = ''; formSuccess = '';"
          :class="['pb-2 px-4 text-xs font-display font-bold transition-all border-b-2 cursor-pointer flex items-center space-x-1.5',
            activeEntryMode === 'bulk'
              ? 'border-blue-600 text-blue-600 font-extrabold'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          ]"
        >
          <Truck class="h-3 w-3 shrink-0" />
          <span>🚚 Bulk Vehicle Route Dispatch Sheets</span>
          <span class="bg-blue-100 text-blue-800 px-1.5 py-0.2 rounded-full text-[9px] font-black uppercase ml-1">Instant</span>
        </button>
      </div>

      <!-- BULK ENTRY PANEL -->
      <div v-if="activeEntryMode === 'bulk'" class="space-y-4 pt-1 font-sans">
        <!-- Drafts Panel -->
        <div v-if="drafts.length > 0" class="bg-amber-50/50 border border-amber-200 rounded p-3 text-xs space-y-2">
          <div class="flex items-center justify-between">
            <span class="font-display font-black text-amber-800 flex items-center gap-1.5 uppercase text-[10px]">
              📂 Saved Vehicle Route Drafts ({{ drafts.length }})
            </span>
            <span class="text-[10px] text-amber-600 font-medium">Click a draft below to load/restore data on form</span>
          </div>
          <div class="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto">
            <div 
              v-for="d in drafts" 
              :key="d.id"
              @click="handleLoadDraft(d)"
              class="bg-white hover:bg-amber-105 border border-amber-200 hover:border-amber-400 rounded px-2.5 py-1.5 flex items-center gap-2 cursor-pointer transition shadow-xs text-[11px]"
            >
              <span class="font-bold text-amber-905 leading-none">🚚 {{ d.vehicleNumber }}</span>
              <span class="text-slate-500 text-[10px] hidden sm:inline whitespace-nowrap overflow-hidden text-ellipsis max-w-[200px] border-l border-slate-200 pl-1.5">
                {{ d.name.split(' - ')[1] || d.name }}
              </span>
              <span class="text-[9px] text-slate-400 font-mono tracking-tighter shrink-0">{{ d.timestamp }}</span>
              <button
                type="button"
                @click="handleDeleteDraft(d.id, $event)"
                class="text-slate-400 hover:text-rose-600 ml-1 hover:bg-rose-50 rounded p-0.5 transition cursor-pointer"
              >
                <Trash2 class="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 p-3.5 rounded border border-slate-200">
          <div class="space-y-1">
            <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider font-mono block">
              🚚 Shared Vehicle licence/Plate Number *
            </label>
            <input
              type="text"
              placeholder="e.g. GJ-01-AB-1234 or DL-3C-AS-9999"
              v-model="bulkVehicleNumber"
              @input="bulkVehicleNumber = bulkVehicleNumber.toUpperCase()"
              class="w-full text-xs p-2.5 border border-slate-300 bg-white rounded uppercase font-mono tracking-wider focus:outline-none focus:ring-1 focus:ring-blue-500 font-bold"
            />
            <p class="text-[9px] text-slate-400">All sales items below will be grouped under this route transport vehicle.</p>
          </div>

          <div class="space-y-1">
            <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">
              👤 Route Sales Representative / Visited Store Collector *
            </label>
            <select
              v-model="bulkDsrId"
              class="w-full text-xs p-2.5 border border-slate-300 rounded bg-white text-slate-700 font-bold focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">-- Choose Sales Representative in charge --</option>
              <option v-for="d in dsrs" :key="d.id" :value="d.id">
                {{ d.name }} [{{ d.role === 'Order Collector' ? 'Collector' : 'Rep' }}] ({{ d.phone }})
              </option>
            </select>
            <p class="text-[9px] text-slate-400">This representative is responsible for retrieving outstanding cash balances.</p>
          </div>
        </div>

        <!-- entries list -->
        <div class="border border-slate-200 rounded overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs table-fixed min-w-[800px]">
              <thead>
                <tr class="bg-slate-100 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-extrabold font-mono tracking-wider">
                  <th class="py-2.5 px-3 w-[25%] text-left">Stock Item Drop *</th>
                  <th class="py-2.5 px-3 w-[10%]">Qty *</th>
                  <th class="py-2.5 px-3 w-[26%] text-left">Retail Store / Customer *</th>
                  <th class="py-2.5 px-3 w-[15%] text-center">Payment Term</th>
                  <th class="py-2.5 px-3 w-[16%]">Downpay / Credit Terms</th>
                  <th class="py-2.5 px-2 text-center w-[8%]">Action</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200">
                <tr v-for="(row, idx) in bulkRows" :key="row.id" class="hover:bg-slate-50 transition align-top">
                  <td class="py-2 px-2.5">
                    <select
                      v-model="row.productId"
                      class="w-full text-xs p-1.5 border border-slate-200 rounded bg-white text-slate-800"
                    >
                      <option value="">-- Choose Item --</option>
                      <option v-for="p in products" :key="p.id" :value="p.id" :disabled="p.stock <= 0">
                        {{ p.name }} ({{ p.brand }}) [Stock: {{ p.stock }}]
                      </option>
                    </select>
                    <p v-if="products.find(p => p.id === row.productId)" class="text-[9px] text-slate-400 font-sans mt-0.5 ml-0.5 leading-none font-medium">
                      Price: {{ formatCurrency(products.find(p => p.id === row.productId)!.sellingPrice) }}
                    </p>
                  </td>

                  <td class="py-2 px-2">
                    <input
                      type="number"
                      min="1"
                      v-model="row.quantity"
                      class="w-full text-xs p-1.5 border border-slate-200 rounded font-sans"
                    />
                    <p v-if="products.find(p => p.id === row.productId) && products.find(p => p.id === row.productId)!.stock < (Number(row.quantity) || 0)" class="text-[8px] text-rose-600 font-bold mt-0.5 leading-none">Insuff. Stock!</p>
                  </td>

                  <td class="py-2 px-2">
                    <div class="space-y-1.5">
                      <input
                        type="text"
                        placeholder="Store Name & Address"
                        v-model="row.customerName"
                        @input="(e: any) => {
                          const val = e.target.value;
                          const selected = allSuggestedCustomers.find(c => val === `${c.name} (${c.address})` || val === c.name);
                          if (selected && selected.phone) {
                            row.customerPhone = selected.phone;
                          }
                        }"
                        :list="`bulk-customer-list-${row.id}`"
                        class="w-full text-xs p-1.5 border border-slate-250 rounded font-bold bg-white text-slate-800"
                      />
                      <datalist :id="`bulk-customer-list-${row.id}`">
                        <option v-for="(c, cIdx) in allSuggestedCustomers" :key="cIdx" :value="`${c.name} (${c.address})`" />
                      </datalist>
                      <input
                        type="text"
                        placeholder="Contact Phone (optional)"
                        v-model="row.customerPhone"
                        class="w-full text-[10px] p-1 border border-slate-200 bg-white/70 rounded h-[22px] font-mono leading-none font-bold"
                      />
                    </div>
                  </td>

                  <td class="py-2 px-2 text-center">
                    <div class="inline-flex rounded border border-slate-200 p-0.5 bg-slate-100">
                      <button
                        type="button"
                        @click="row.paymentType = 'Cash'"
                        :class="['px-2 py-0.5 text-[9px] font-bold rounded cursor-pointer leading-tight',
                          row.paymentType === 'Cash' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-200/50'
                        ]"
                      >
                        Cash
                      </button>
                      <button
                        type="button"
                        @click="row.paymentType = 'Credit'"
                        :class="['px-2 py-0.5 text-[9px] font-bold rounded cursor-pointer leading-tight',
                          row.paymentType === 'Credit' ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-600 hover:bg-slate-200/50'
                        ]"
                      >
                        Credit
                      </button>
                    </div>
                    <p class="text-[10px] text-slate-700 font-bold font-mono mt-1.5">
                      Subtotal: {{ formatCurrency(products.find(p => p.id === row.productId) ? products.find(p => p.id === row.productId)!.sellingPrice * (Number(row.quantity) || 0) : 0) }}
                    </p>
                  </td>

                  <td class="py-2 px-2 text-left">
                    <div v-if="row.paymentType === 'Credit'" class="space-y-1">
                      <input
                        type="number"
                        placeholder="Down payment (₹0)"
                        v-model="row.amountPaid"
                        class="w-full text-[10px] p-1 border border-rose-200 bg-rose-50/10 rounded font-sans focus:outline-none font-mono"
                      />
                      <div class="flex items-center space-x-1 justify-between">
                        <span class="text-[8px] text-slate-450 font-black shrink-0 uppercase tracking-widest leading-none font-mono">DUE:</span>
                        <input
                          type="date"
                          v-model="row.dueDate"
                          class="w-full text-[9px] p-0.5 border border-slate-250 rounded font-sans bg-white leading-none h-[18px]"
                        />
                      </div>
                    </div>
                    <div v-else class="text-[9px] text-emerald-800 font-bold py-2 bg-emerald-50 border border-emerald-100 rounded text-center uppercase tracking-wide">
                      💸 Cash terms
                    </div>
                  </td>

                  <td class="py-2.5 px-2 text-center align-middle">
                    <button
                      type="button"
                      @click="handleRemoveBulkRow(row.id)"
                      class="p-1 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded transition cursor-pointer border border-transparent hover:border-rose-100"
                    >
                      <Trash2 class="h-4.5 w-4.5" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 bg-slate-50 p-2.5 rounded border border-slate-200 text-left">
          <button
            type="button"
            @click="handleAddBulkRow"
            class="bg-white hover:bg-slate-100 text-slate-700 text-[10px] font-display font-black px-3 py-1.5 rounded border border-slate-300 inline-flex items-center space-x-1 cursor-pointer transition shadow-xs leading-none"
          >
            <Plus class="h-3.5 w-3.5" />
            <span>+ Add Outlet Invoice Drop</span>
          </button>

          <div class="text-right font-sans">
            <span class="text-[9px] text-slate-400 uppercase tracking-wider font-bold">Total Vehicle Cargo Load Value:</span>
            <span class="text-sm font-display font-black text-blue-600 block font-mono">
              {{ formatCurrency(
                bulkRows.reduce((sum, r) => {
                  const p = products.find(prod => prod.id === r.productId);
                  return sum + (p ? p.sellingPrice * (Number(r.quantity) || 0) : 0);
                }, 0)
              ) }}
            </span>
          </div>
        </div>

        <div class="flex justify-end space-x-2 pt-3 border-t border-slate-200 items-center">
          <p v-if="formError" class="text-[11px] text-rose-600 mr-auto font-bold font-sans">⚠️ {{ formError }}</p>
          <p v-if="formSuccess" class="text-[11px] text-emerald-600 mr-auto font-bold font-sans">✨ {{ formSuccess }}</p>
          
          <button 
            type="button" 
            @click="saveCurrentAsDraft"
            class="px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded text-xs font-bold shadow-xs cursor-pointer flex items-center space-x-1 border border-amber-500"
          >
            <span>💾 Save as Draft</span>
          </button>

          <button 
            type="button" 
            @click="showLogForm = false" 
            class="px-3 py-2 border border-slate-250 rounded text-xs cursor-pointer hover:bg-slate-50 font-bold"
          >
            Cancel
          </button>
          
          <button 
            type="button"
            @click="handleBulkSubmit"
            :disabled="isSubmitting"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold shadow-sm cursor-pointer disabled:opacity-50"
          >
            {{ isSubmitting ? 'Dispatching Cargo...' : 'Finalize & Dispatch Route Load' }}
          </button>
        </div>
      </div>

      <!-- SINGLE ENTRY PANEL -->
      <form v-else @submit.prevent="handleSaleSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-3 font-sans pt-2">
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">1. Select Product *</label>
          <select 
            v-model="productId"
            class="w-full text-xs p-2 border border-slate-200 rounded bg-white text-slate-800"
          >
            <option value="">-- Choose from available stock --</option>
            <option v-for="p in products" :key="p.id" :value="p.id" :disabled="p.stock <= 0">
              {{ p.name }} ({{ p.brand }}) [Available units: {{ p.stock }}]
            </option>
          </select>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Quantity *</label>
          <input 
            type="number" 
            min="1"
            v-model="quantity"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Price Per Unit</label>
          <div class="p-2 w-full bg-slate-50 border border-slate-200 rounded text-xs font-semibold text-slate-700 flex items-center h-[34px] font-mono">
            {{ productId 
              ? formatCurrency(products.find(p => p.id === productId)?.sellingPrice || 0) 
              : '₹ Select product first'
            }}
          </div>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Retail Grocery Store / Customer *</label>
          <input 
            type="text" 
            placeholder="e.g. Reliance Fresh, Big Bazaar" 
            v-model="customerName"
            @input="(e: any) => {
              const val = e.target.value;
              const selected = allSuggestedCustomers.find(c => val === `${c.name} (${c.address})` || val === c.name);
              if (selected && selected.phone) {
                customerPhone = selected.phone;
              }
            }"
            list="single-customer-list"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 font-bold bg-white text-slate-800"
          />
          <datalist id="single-customer-list">
            <option v-for="(c, idx) in allSuggestedCustomers" :key="idx" :value="`${c.name} (${c.address})`" />
          </datalist>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Store Contact Phone</label>
          <input 
            type="text" 
            placeholder="e.g. +91 99887 76655" 
            v-model="customerPhone"
            class="w-full text-xs p-2 border border-slate-200 rounded font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Route Transport Method</label>
          <div class="flex rounded border border-slate-200 p-0.5 bg-slate-100 h-[34px]">
            <button
              type="button"
              @click="isVehicle = true"
              :class="['w-1/2 text-xs font-bold font-display rounded cursor-pointer', isVehicle ? 'bg-white text-slate-800 shadow-xs' : 'text-slate-500 hover:bg-slate-200/50']"
            >
              🚚 Dispatch Van
            </button>
            <button
              type="button"
              @click="isVehicle = false"
              :class="['w-1/2 text-xs font-bold font-display rounded cursor-pointer', !isVehicle ? 'bg-white text-slate-800 shadow-xs' : 'text-slate-500 hover:bg-slate-200/50']"
            >
              👤 Representative DSR
            </button>
          </div>
        </div>

        <div v-if="isVehicle" class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block font-mono">🚚 Vehicle Plate Number *</label>
          <input 
            type="text" 
            placeholder="License Plate code" 
            v-model="vehicleNumber"
            @input="vehicleNumber = vehicleNumber.toUpperCase()"
            class="w-full text-xs p-2 border border-slate-200 rounded uppercase font-mono font-bold"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">👤 Assigned Representative (DSR) *</label>
          <select 
            v-model="dsrId"
            class="w-full text-xs p-2 border border-slate-200 rounded bg-white text-slate-800"
          >
            <option value="">-- Choose Rep --</option>
            <option v-for="d in dsrs" :key="d.id" :value="d.id">
              {{ d.name }} ({{ d.phone }})
            </option>
          </select>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Payment Term Choice</label>
          <div class="flex rounded border border-slate-200 p-0.5 bg-slate-100 h-[34px]">
            <button
              type="button"
              @click="paymentType = 'Cash'"
              :class="['w-1/2 text-xs font-bold font-display rounded cursor-pointer', paymentType === 'Cash' ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-500 hover:bg-slate-200/50']"
            >
              💸 Full Cash
            </button>
            <button
              type="button"
              @click="paymentType = 'Credit'"
              :class="['w-1/2 text-xs font-bold font-display rounded cursor-pointer', paymentType === 'Credit' ? 'bg-rose-600 text-white shadow-xs' : 'text-slate-500 hover:bg-slate-200/50']"
            >
              💳 Credit Terms
            </button>
          </div>
        </div>

        <div v-if="paymentType === 'Credit'" class="space-y-1">
          <label class="text-[10px] font-bold text-rose-600 uppercase tracking-wider block font-bold">Down Payment Received (₹)</label>
          <input 
            type="number" 
            placeholder="Rep paid cash (e.g. 5000)" 
            v-model="amountPaid"
            class="w-full text-xs p-2 border border-rose-200 rounded bg-rose-50/5 focus:outline-none font-mono"
          />
        </div>

        <div v-if="paymentType === 'Credit'" class="space-y-1">
          <label class="text-[10px] font-bold text-rose-600 uppercase tracking-wider block font-bold">Repayment Due Date *</label>
          <input 
            type="date" 
            v-model="dueDate"
            class="w-full text-xs p-2 border border-rose-200 rounded focus:outline-none"
          />
        </div>

        <div class="md:col-span-3 flex justify-end space-x-2 pt-3 border-t border-slate-100 items-center">
          <p v-if="formError" class="text-[11px] text-rose-600 mr-auto font-bold font-sans">⚠️ {{ formError }}</p>
          <p v-if="formSuccess" class="text-[11px] text-emerald-600 mr-auto font-bold font-sans">✨ {{ formSuccess }}</p>
          
          <div class="text-right mr-4 font-sans" v-if="productId">
            <span class="text-[9px] text-slate-400 uppercase tracking-widest block font-bold">Estimated Invoice Total:</span>
            <span class="text-sm font-display font-black text-slate-800 font-mono">
              {{ formatCurrency((Number(quantity) || 0) * (products.find(p => p.id === productId)?.sellingPrice || 0)) }}
            </span>
          </div>

          <button id="sales-btn-cancel" type="button" @click="showLogForm = false" class="px-3 py-1.5 border border-slate-200 rounded text-xs cursor-pointer hover:bg-slate-50 font-bold">
            Cancel
          </button>
          <button id="sales-btn-submit" type="submit" :disabled="isSubmitting" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold shadow-sm cursor-pointer disabled:opacity-50">
            {{ isSubmitting ? 'Registering Sale...' : 'Finalize & Draw Invoice' }}
          </button>
        </div>
      </form>
    </div>

    <!-- SALES LIST TABLE & SEARCH FILTERS -->
    <div class="bg-white p-3.5 rounded border border-slate-200 shadow-sm space-y-3.5 text-left">
      <div class="flex flex-col md:flex-row gap-3 items-center justify-between">
        <!-- Search bar -->
        <div class="relative w-full md:w-80">
          <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search customer, item, vehicle..." 
            v-model="searchQuery"
            class="w-full text-xs pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans"
          />
        </div>

        <!-- Filter selections -->
        <div class="flex flex-wrap gap-2 w-full md:w-auto md:justify-end">
          <select 
            v-model="selectedPeriod"
            class="text-[11px] font-sans px-2 py-1.5 rounded border border-slate-200 bg-white font-bold text-slate-600"
          >
            <option value="ALL">🗓️ All Dates</option>
            <option value="TODAY">Today</option>
            <option value="WEEK">Last 7 Days</option>
            <option value="MONTH">This Month</option>
            <option value="QUARTER">This Quarter</option>
            <option value="YEAR">This Year</option>
          </select>

          <select 
            v-model="sortBy"
            class="text-[11px] font-sans px-2 py-1.5 rounded border border-slate-200 bg-white font-bold text-slate-600"
          >
            <option value="DATE_DESC">⏱️ Date (Latest First)</option>
            <option value="DATE_ASC">⏱️ Date (Oldest First)</option>
            <option value="AMOUNT_DESC">💰 Amount (High → Low)</option>
            <option value="AMOUNT_ASC">💰 Amount (Low → High)</option>
          </select>
        </div>
      </div>

      <!-- sales data table listing -->
      <div class="border border-slate-200 rounded overflow-hidden shadow-xs">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs font-sans">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-extrabold tracking-wider">
                <th class="py-3 px-4">Invoice / Date</th>
                <th class="py-3 px-4">Retail Outlet Store</th>
                <th class="py-3 px-4">Product Details</th>
                <th class="py-3 px-4">Transport Route</th>
                <th class="py-3 px-4 text-center">Payment Status</th>
                <th class="py-3 px-4 text-right">Invoice Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-150">
              <tr v-for="sale in currentSalesList" :key="sale.id" class="hover:bg-slate-50/50 transition">
                <td class="py-3 px-4">
                  <div>
                    <span class="font-mono text-xs font-black text-slate-900">#{{ sale.id.substring(sale.id.length - 6).toUpperCase() }}</span>
                    <span class="block text-[10px] text-slate-400 mt-1 font-mono tracking-tighter">
                      {{ new Date(sale.date).toLocaleDateString() }} at {{ new Date(sale.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
                    </span>
                  </div>
                </td>

                <td class="py-3 px-4 h-full align-middle">
                  <div>
                    <span class="font-display font-black text-slate-800 text-sm block leading-snug">{{ sale.customerName }}</span>
                    <span class="text-[9.5px] text-slate-450 font-mono" v-if="sale.customerPhone">📞 {{ sale.customerPhone }}</span>
                  </div>
                </td>

                <td class="py-3 px-4">
                  <div>
                    <span class="font-sans font-semibold text-slate-700 block">{{ sale.productName }}</span>
                    <span class="text-[10px] text-slate-450 mt-1 block">Qty issued: <span class="font-bold text-slate-600">{{ sale.quantity }}</span> units</span>
                  </div>
                </td>

                <td class="py-3 px-4">
                  <div class="flex flex-col space-y-1">
                    <span v-if="sale.isVehicle" class="inline-flex items-center space-x-1 text-blue-800 bg-blue-50 border border-blue-10 w-fit px-1.5 py-0.5 rounded text-[9px] font-mono tracking-wider font-extrabold uppercase">
                      <Truck class="h-2.5 w-2.5" />
                      <span>{{ sale.vehicleNumber }}</span>
                    </span>
                    <span v-else class="inline-flex items-center space-x-1 text-slate-600 bg-slate-100 border border-slate-200 w-fit px-1.5 py-0.5 rounded text-[9px] font-mono font-extrabold uppercase">
                      <User class="h-2.5 w-2.5" />
                      <span>Store Counter</span>
                    </span>
                    <span class="text-[9.5px] text-slate-500 font-semibold mt-1">Rep: {{ sale.dsrName || 'Self / Counter' }}</span>
                  </div>
                </td>

                <td class="py-3 px-4 text-center">
                  <div v-if="sale.paymentType === 'Cash'" class="inline-flex items-center text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded font-bold uppercase text-[10px] tracking-wide border border-emerald-150">
                    Paid Full Cash
                  </div>
                  <div v-else class="flex flex-col items-center space-y-1">
                    <!-- Is fully solved or pending -->
                    <span v-if="sale.amountPaid >= sale.totalAmount" class="text-emerald-800 bg-emerald-50 border border-emerald-150 px-2 py-0.5 text-[9px] font-black uppercase rounded tracking-wider">
                      Credit Solved
                    </span>
                    <span v-else class="text-rose-700 bg-rose-50 border border-rose-150 px-2 py-0.5 text-[9px] font-black uppercase rounded tracking-wider">
                      Credit Pending
                    </span>
                    
                    <span class="text-[9px] text-slate-450 font-sans block" v-if="sale.amountPaid < sale.totalAmount">
                      Paid: <span class="font-mono font-bold">{{ formatCurrency(sale.amountPaid) }}</span>
                    </span>
                    <span class="text-[8px] text-rose-500 font-bold block bg-rose-50/50 border border-rose-200 px-1 py-0.2 rounded font-mono" v-if="sale.amountPaid < sale.totalAmount && sale.dueDate">
                      Due: {{ new Date(sale.dueDate).toLocaleDateString() }}
                    </span>
                  </div>
                </td>

                <td class="py-3 px-4 text-right font-display font-black text-slate-800 text-sm font-mono leading-none">
                  {{ formatCurrency(sale.totalAmount) }}
                </td>
              </tr>

              <tr v-if="sortedSales.length === 0">
                <td colSpan="6" class="text-center py-10 bg-white">
                  <p class="font-display font-semibold text-slate-700 text-sm font-bold">No registered sales invoices match your search preferences!</p>
                  <p class="text-[11px] text-slate-400 font-sans mt-0.5">Adjust chronological date range or refine customer name query parameters.</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- pagination controls footer -->
        <div v-if="totalPages > 1" class="bg-slate-50 border-t border-slate-200 px-4 py-2.5 flex items-center justify-between font-sans">
          <p class="text-xs text-slate-500 text-left">
            Showing <span class="font-semibold">{{ indexOfFirstItem + 1 }}</span> to
            <span class="font-semibold">{{ Math.min(indexOfFirstItem + itemsPerPage, sortedSales.length) }}</span> of
            <span class="font-semibold">{{ sortedSales.length }}</span> sales records
          </p>

          <div class="flex space-x-1">
            <button
              @click="currentPage = Math.max(currentPage - 1, 1)"
              :disabled="currentPage === 1"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer"
            >
              Prev
            </button>
            
            <button
              v-for="no in totalPages"
              :key="no"
              @click="currentPage = no"
              :class="['px-2.5 py-1 text-xs border rounded cursor-pointer font-bold',
                currentPage === no
                  ? 'bg-blue-600 border-blue-605 text-white font-black'
                  : 'bg-white border-slate-300 text-slate-650 hover:bg-slate-100'
              ]"
            >
              {{ no }}
            </button>

            <button
              @click="currentPage = Math.min(currentPage + 1, totalPages)"
              :disabled="currentPage === totalPages"
              class="px-2.5 py-1 text-xs border border-slate-300 rounded bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
