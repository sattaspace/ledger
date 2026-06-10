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
  Trash2,
  Edit,
  ArrowDownCircle,
  XCircle,
  RotateCcw
} from 'lucide-vue-next';
import type { Product, SaleRecord, DSR } from '../types';
import { BaseChart, ChartCard } from './charts';
import type { ChartData, ChartOptions } from 'chart.js';

const props = withDefaults(defineProps<{
  products: Product[];
  sales: SaleRecord[];
  dsrs: DSR[];
  quickActionType?: string | null;
  formatCurrency?: (amt: number) => string;
  onAddSale?: (data: any) => Promise<any>;
  onAddBulkSales?: (data: any) => Promise<any>;
  onVoidSale?: (saleId: string, force?: boolean) => Promise<any>;
  onEditSale?: (saleId: string, data: any) => Promise<any>;
  onReturnItem?: (saleId: string, data: any) => Promise<any>;
}>(), {
  quickActionType: null
});

const emit = defineEmits<{
  (e: 'refreshData'): void;
  (e: 'clearQuickActionType'): void;
}>();

const searchQuery = ref('');
const showLogForm = ref(false);
const isSubmitting = ref(false);
const formError = ref('');
const formSuccess = ref('');

// Sale action states
const editingSale = ref<SaleRecord | null>(null);
const editSaleFields = ref({ customerName: '', customerPhone: '', dueDate: '', vehicleNumber: '' });
const editSaleSubmitting = ref(false);
const editSaleError = ref('');

const voidingSale = ref<SaleRecord | null>(null);
const voidSaleSubmitting = ref(false);
const voidSaleError = ref('');

const returningSale = ref<SaleRecord | null>(null);
const returnSaleFields = ref({ quantity: '1', reason: 'Damaged', processedBy: '' });
const returnSaleSubmitting = ref(false);
const returnSaleError = ref('');

const saleFilter = ref<'ALL' | 'VOIDED' | 'ACTIVE'>('ALL');

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
      formError.value = `Invoice row #${rowNum}: Customer name is required.`;
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
      formError.value = `Invoice row #${rowNum}: Insufficient stock for "${p.name}". Wanted ${qty} but only ${p.stock} units available.`;
      return;
    }
    if (row.paymentType === 'Credit' && !row.dueDate) {
      formError.value = `Invoice row #${rowNum}: Credit transactions require a payment due date.`;
      return;
    }
  }

  isSubmitting.value = true;
  try {
    await props.onAddBulkSales!({
      vehicleNumber: bulkVehicleNumber.value,
      dsrId: bulkDsrId.value,
      rows: validRows.map(row => {
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

    // Reset bulk forms
    bulkRows.value = [createEmptyRow(), createEmptyRow(), createEmptyRow()];
    bulkVehicleNumber.value = '';
    bulkDsrId.value = '';
    showLogForm.value = false;
  } catch (err: any) {
    formError.value = err.message || 'Trouble submitting bulk sales.';
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
    formError.value = 'Please select a product!';
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
    formError.value = `Out of Stock! You want ${qty}, but only have ${selectedProduct.stock} left.`;
    return;
  }

  if (!customerName.value) {
    formError.value = 'Customer name is required!';
    return;
  }

  if (isVehicle.value && !vehicleNumber.value) {
    formError.value = 'Please provide a vehicle plate number!';
    return;
  }

  if (!dsrId.value) {
    formError.value = 'Please assign a sales representative!';
    return;
  }

  if (paymentType.value === 'Credit' && !dueDate.value) {
    formError.value = 'Please select a due date!';
    return;
  }

  isSubmitting.value = true;
  try {
    const parsedAmountPaid = paymentType.value === 'Cash' 
      ? qty * selectedProduct.sellingPrice 
      : Number(amountPaid.value) || 0;

    await props.onAddSale!({
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
    showLogForm.value = false;
  } catch (err: any) {
    formError.value = err.message || 'Trouble submitting sale.';
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
  let filtered = periodFilteredSales.value;
  
  // Apply voided/active filter
  if (saleFilter.value === 'VOIDED') {
    filtered = filtered.filter(s => s.isVoided);
  } else if (saleFilter.value === 'ACTIVE') {
    filtered = filtered.filter(s => !s.isVoided);
  }
  
  if (!q) return filtered;

  return filtered.filter(s => {
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

// Payment type distribution for current sales
const salesPaymentData = computed(() => {
  const allSales = props.sales || [];
  const cashTotal = allSales.filter(s => s.paymentType === 'Cash').reduce((sum, s) => sum + s.totalAmount, 0);
  const creditTotal = allSales.filter(s => s.paymentType === 'Credit').reduce((sum, s) => sum + s.totalAmount, 0);
  return {
    labels: ['Cash Sales', 'Credit Sales'],
    datasets: [{
      data: [cashTotal, creditTotal],
      backgroundColor: ['rgba(16, 185, 129, 0.8)', 'rgba(244, 63, 94, 0.8)'],
      borderColor: ['rgb(16, 185, 129)', 'rgb(244, 63, 94)'],
      borderWidth: 2,
      hoverOffset: 6,
    }]
  };
});

const salesPaymentOptions = computed(() => ({
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
        label: (ctx: any) => `${ctx.label}: ${formatCurrency.value(ctx.raw as number)}`
      }
    }
  }
}));

// Sales by product bar chart (top 6 products)
const salesByProductData = computed(() => {
  const productSales: Record<string, number> = {};
  (props.sales || []).forEach(s => {
    productSales[s.productName] = (productSales[s.productName] || 0) + s.totalAmount;
  });
  const sorted = Object.entries(productSales).sort((a, b) => b[1] - a[1]).slice(0, 6);
  return {
    labels: sorted.map(([name]) => name.length > 12 ? name.slice(0, 12) + '...' : name),
    datasets: [{
      label: 'Revenue',
      data: sorted.map(([, val]) => val),
      backgroundColor: [
        'rgba(226, 82, 18, 0.75)',
        'rgba(16, 185, 129, 0.75)',
        'rgba(59, 130, 246, 0.75)',
        'rgba(139, 92, 246, 0.75)',
        'rgba(245, 158, 11, 0.75)',
        'rgba(236, 72, 153, 0.75)',
      ],
      borderRadius: 6,
      borderWidth: 1,
    }]
  };
});

const salesByProductOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => `Revenue: ${formatCurrency.value(ctx.raw as number)}`
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

// Daily sales trend line chart (last 7 days)
const dailySalesTrendData = computed(() => {
  const labels: string[] = [];
  const amounts: number[] = [];
  
  for (let i = 6; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    labels.push(d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));
    
    const daySales = (props.sales || []).filter(s => {
      const sd = new Date(s.date);
      return sd.getFullYear() === d.getFullYear() && sd.getMonth() === d.getMonth() && sd.getDate() === d.getDate();
    });
    amounts.push(daySales.reduce((sum, s) => sum + (s.totalAmount || 0), 0));
  }
  
  return {
    labels,
    datasets: [{
      label: 'Daily Revenue',
      data: amounts,
      borderColor: 'rgb(16, 185, 129)',
      backgroundColor: 'rgba(16, 185, 129, 0.1)',
      fill: true,
      tension: 0.4,
      pointBackgroundColor: 'rgb(16, 185, 129)',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
    }]
  };
});

const dailySalesTrendOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      callbacks: {
        label: (ctx: any) => `Revenue: ${formatCurrency.value(ctx.raw as number)}`
      }
    }
  },
  scales: {
    x: { 
      grid: { display: false },
      ticks: { color: '#64748B', font: { family: 'Inter', size: 10 } }
    },
    y: { 
      grid: { color: '#F1F5F9' },
      ticks: {
        color: '#94A3B8',
        font: { family: 'JetBrains Mono', size: 10 },
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

// ─── Edit Sale Handler ────────────────────────────────────────────────────
const openEditSale = (sale: SaleRecord) => {
  editingSale.value = sale;
  editSaleFields.value = {
    customerName: sale.customerName,
    customerPhone: sale.customerPhone || '',
    dueDate: sale.dueDate || '',
    vehicleNumber: sale.vehicleNumber || ''
  };
  editSaleError.value = '';
};

const handleEditSaleSubmit = async () => {
  if (!editingSale.value) return;
  editSaleSubmitting.value = true;
  editSaleError.value = '';
  try {
    await props.onEditSale!(editingSale.value.id, editSaleFields.value);
    editingSale.value = null;
    emit('refreshData');
  } catch (err: any) {
    editSaleError.value = err.message || 'Failed to update sale.';
  } finally {
    editSaleSubmitting.value = false;
  }
};

const voidForceMode = ref(false);

// ─── Void Sale Handler ──────────────────────────────────────────────────
const openVoidSale = (sale: SaleRecord) => {
  voidingSale.value = sale;
  voidSaleError.value = '';
  // If sale has payments, show warning and require force
  voidForceMode.value = !!(sale.amountPaid && sale.amountPaid > 0);
};

const handleVoidSaleConfirm = async (force: boolean = false) => {
  if (!voidingSale.value) return;
  voidSaleSubmitting.value = true;
  voidSaleError.value = '';
  try {
    await props.onVoidSale!(voidingSale.value.id, force);
    voidingSale.value = null;
    voidForceMode.value = false;
    emit('refreshData');
  } catch (err: any) {
    // If error indicates transactions exist, switch to force mode
    if (err.message && err.message.includes('payment')) {
      voidForceMode.value = true;
      voidSaleError.value = err.message;
    } else {
      voidSaleError.value = err.message || 'Failed to void sale.';
    }
  } finally {
    voidSaleSubmitting.value = false;
  }
};

// ─── Return Item Handler ────────────────────────────────────────────────
const openReturnForm = (sale: SaleRecord) => {
  returningSale.value = sale;
  returnSaleFields.value = { quantity: '1', reason: 'Customer Return', processedBy: '' };
  returnSaleError.value = '';
};

const handleReturnSubmit = async () => {
  if (!returningSale.value) return;
  returnSaleSubmitting.value = true;
  returnSaleError.value = '';
  try {
    await props.onReturnItem!(returningSale.value.id, {
      quantity: Number(returnSaleFields.value.quantity),
      reason: returnSaleFields.value.reason,
      processedBy: returnSaleFields.value.processedBy
    });
    returningSale.value = null;
    emit('refreshData');
  } catch (err: any) {
    returnSaleError.value = err.message || 'Failed to process return.';
  } finally {
    returnSaleSubmitting.value = false;
  }
  };
</script>

<template>
  <div class="dashboard-layout font-sans animate-fadeIn">
    <div class="dashboard-middle space-y-6">
    <!-- HEADER -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="text-left">
        <h2 class="text-xl md:text-2xl font-bold text-slate-800 flex items-center gap-2">
          <ShoppingBag class="h-6 w-6 text-emerald-600" />
          Record a Sale
        </h2>
        <p class="text-sm text-slate-500 mt-1">Sell products via vehicle delivery or sales rep</p>
      </div>

      <button 
        id="sales-btn-toggle-log"
        @click="showLogForm = !showLogForm"
        :class="['py-2.5 px-5 rounded-lg flex items-center gap-2 transition font-semibold text-sm cursor-pointer',
          showLogForm 
            ? 'bg-rose-600 text-white shadow-sm hover:bg-rose-700' 
            : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm'
        ]"
      >
        <component :is="showLogForm ? X : Plus" class="h-4 w-4" />
        <span>{{ showLogForm ? 'Close Form' : 'New Sale' }}</span>
      </button>
    </div>

    <!-- SALE FORM -->
    <div v-if="showLogForm" class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-3 border-b border-slate-100">
        <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
          <ShoppingBag class="h-5 w-5 text-emerald-600" />
          <span>Record a Sale</span>
        </h3>
        <button id="sales-btn-close-form" @click="showLogForm = false" class="text-slate-400 hover:text-slate-600 cursor-pointer p-1 rounded-lg hover:bg-slate-100 transition">
          <X class="h-5 w-5" />
        </button>
      </div>

      <!-- MODE TAB SWITCH (Pill Style) -->
      <div class="inline-flex bg-slate-100 p-1 rounded-lg">
        <button
          id="mode-choice-single"
          type="button"
          @click="activeEntryMode = 'single'; formError = ''; formSuccess = '';"
          :class="['py-2.5 px-5 text-sm font-semibold rounded-lg transition-all cursor-pointer flex items-center gap-2',
            activeEntryMode === 'single'
              ? 'bg-white text-slate-900 shadow-sm font-bold'
              : 'text-slate-500 hover:text-slate-700'
          ]"
        >
          <User class="h-4 w-4" />
          <span>Single Sale</span>
        </button>
        <button
          id="mode-choice-bulk"
          type="button"
          @click="activeEntryMode = 'bulk'; formError = ''; formSuccess = '';"
          :class="['py-2.5 px-5 text-sm font-semibold rounded-lg transition-all cursor-pointer flex items-center gap-2',
            activeEntryMode === 'bulk'
              ? 'bg-white text-slate-900 shadow-sm font-bold'
              : 'text-slate-500 hover:text-slate-700'
          ]"
        >
          <Truck class="h-4 w-4" />
          <span>Bulk Route</span>
        </button>
      </div>

      <!-- ========== BULK ENTRY PANEL ========== -->
      <div v-if="activeEntryMode === 'bulk'" class="space-y-5 font-sans">
        <!-- Drafts Panel -->
        <div v-if="drafts.length > 0" class="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
          <div class="flex items-center justify-between">
            <span class="font-bold text-amber-800 flex items-center gap-2 text-sm">
              <FileText class="h-4 w-4" />
              Saved Drafts ({{ drafts.length }})
            </span>
            <span class="text-xs text-amber-600">Click to load a draft</span>
          </div>
          <div class="flex flex-wrap gap-2 max-h-28 overflow-y-auto">
            <div 
              v-for="d in drafts" 
              :key="d.id"
              @click="handleLoadDraft(d)"
              class="bg-white hover:bg-amber-50 border border-amber-200 hover:border-amber-400 rounded-lg px-3 py-2 flex items-center gap-3 cursor-pointer transition shadow-sm text-sm"
            >
              <Truck class="h-4 w-4 text-amber-600 shrink-0" />
              <span class="font-semibold text-slate-800">{{ d.vehicleNumber }}</span>
              <span class="text-xs text-slate-400 hidden sm:inline truncate max-w-[150px]">
                {{ d.name.split(' - ')[1] || d.name }}
              </span>
              <span class="text-xs text-slate-400 font-mono shrink-0">{{ d.timestamp }}</span>
              <button
                type="button"
                @click="handleDeleteDraft(d.id, $event)"
                class="text-slate-400 hover:text-rose-600 ml-1 hover:bg-rose-50 rounded-lg p-1 transition cursor-pointer"
              >
                <Trash2 class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Vehicle & Rep Fields -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-5 rounded-xl border border-slate-200">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
              <Truck class="h-4 w-4 text-slate-500" />
              Vehicle Plate Number *
            </label>
            <input
              type="text"
              placeholder="e.g. GJ-01-AB-1234"
              v-model="bulkVehicleNumber"
              @input="bulkVehicleNumber = bulkVehicleNumber.toUpperCase()"
              class="w-full text-sm py-3 px-4 border border-slate-300 bg-white rounded-lg uppercase font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 font-semibold"
            />
            <p class="text-xs text-slate-400">All items below will be grouped under this vehicle</p>
          </div>

          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
              <UserCheck class="h-4 w-4 text-slate-500" />
              Sales Representative *
            </label>
            <select
              v-model="bulkDsrId"
              class="w-full text-sm py-3 px-4 border border-slate-300 rounded-lg bg-white text-slate-700 font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
            >
              <option value="">-- Choose Representative --</option>
              <option v-for="d in dsrs" :key="d.id" :value="d.id">
                {{ d.name }} [{{ d.role === 'Order Collector' ? 'Collector' : 'Rep' }}] ({{ d.phone }})
              </option>
            </select>
            <p class="text-xs text-slate-400">This rep is responsible for collecting payments</p>
          </div>
        </div>

        <!-- Bulk Entries Table -->
        <div class="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm table-fixed min-w-[800px]">
              <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-xs font-bold tracking-wider">
                  <th class="py-3 px-4 w-[25%] text-left">Product *</th>
                  <th class="py-3 px-4 w-[10%]">Qty *</th>
                  <th class="py-3 px-4 w-[26%] text-left">Customer *</th>
                  <th class="py-3 px-4 w-[15%] text-center">Payment</th>
                  <th class="py-3 px-4 w-[16%]">Details</th>
                  <th class="py-3 px-3 text-center w-[8%]"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="(row, idx) in bulkRows" :key="row.id" class="hover:bg-slate-50/50 transition align-top">
                  <td class="py-3 px-4">
                    <select
                      v-model="row.productId"
                      class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="">-- Choose Item --</option>
                      <option v-for="p in products" :key="p.id" :value="p.id" :disabled="p.stock <= 0">
                        {{ p.name }} ({{ p.brand }}) [Stock: {{ p.stock }}]
                      </option>
                    </select>
                    <p v-if="products.find(p => p.id === row.productId)" class="text-xs text-slate-400 mt-1 font-medium">
                      Price: {{ formatCurrency(products.find(p => p.id === row.productId)!.sellingPrice) }}
                    </p>
                  </td>

                  <td class="py-3 px-3">
                    <input
                      type="number"
                      min="1"
                      v-model="row.quantity"
                      class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    />
                    <p v-if="products.find(p => p.id === row.productId) && products.find(p => p.id === row.productId)!.stock < (Number(row.quantity) || 0)" class="text-xs text-rose-600 font-bold mt-1">Low Stock!</p>
                  </td>

                  <td class="py-3 px-3">
                    <div class="space-y-2">
                      <input
                        type="text"
                        placeholder="Customer name"
                        v-model="row.customerName"
                        @input="(e: any) => {
                          const val = e.target.value;
                          const selected = allSuggestedCustomers.find(c => val === `${c.name} (${c.address})` || val === c.name);
                          if (selected && selected.phone) {
                            row.customerPhone = selected.phone;
                          }
                        }"
                        :list="`bulk-customer-list-${row.id}`"
                        class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg font-semibold bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                      <datalist :id="`bulk-customer-list-${row.id}`">
                        <option v-for="(c, cIdx) in allSuggestedCustomers" :key="cIdx" :value="`${c.name} (${c.address})`" />
                      </datalist>
                      <input
                        type="text"
                        placeholder="Phone (optional)"
                        v-model="row.customerPhone"
                        class="w-full text-sm py-2 px-3 border border-slate-200 bg-slate-50 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  </td>

                  <td class="py-3 px-3 text-center">
                    <div class="inline-flex rounded-lg border border-slate-200 p-0.5 bg-slate-100">
                      <button
                        type="button"
                        @click="row.paymentType = 'Cash'"
                        :class="['px-3 py-1.5 text-xs font-bold rounded-md cursor-pointer transition',
                          row.paymentType === 'Cash' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-200/50'
                        ]"
                      >
                        Cash
                      </button>
                      <button
                        type="button"
                        @click="row.paymentType = 'Credit'"
                        :class="['px-3 py-1.5 text-xs font-bold rounded-md cursor-pointer transition',
                          row.paymentType === 'Credit' ? 'bg-rose-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-200/50'
                        ]"
                      >
                        Credit
                      </button>
                    </div>
                    <p class="text-xs text-slate-700 font-semibold font-mono mt-2">
                      {{ formatCurrency(products.find(p => p.id === row.productId) ? products.find(p => p.id === row.productId)!.sellingPrice * (Number(row.quantity) || 0) : 0) }}
                    </p>
                  </td>

                  <td class="py-3 px-3 text-left">
                    <div v-if="row.paymentType === 'Credit'" class="space-y-2">
                      <input
                        type="number"
                        placeholder="Down payment"
                        v-model="row.amountPaid"
                        class="w-full text-sm py-2 px-3 border border-rose-200 bg-rose-50/30 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-400 font-mono"
                      />
                      <div class="flex items-center gap-2">
                        <span class="text-xs text-slate-500 font-semibold shrink-0">Due:</span>
                        <input
                          type="date"
                          v-model="row.dueDate"
                          class="w-full text-sm py-1.5 px-2 border border-slate-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        />
                      </div>
                    </div>
                    <div v-else class="text-xs text-emerald-700 font-semibold py-3 bg-emerald-50 border border-emerald-100 rounded-lg text-center">
                      Cash Payment
                    </div>
                  </td>

                  <td class="py-3 px-2 text-center align-middle">
                    <button
                      type="button"
                      @click="handleRemoveBulkRow(row.id)"
                      class="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                    >
                      <Trash2 class="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Add Row & Total -->
        <div class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-left">
          <button
            type="button"
            @click="handleAddBulkRow"
            class="bg-white hover:bg-slate-100 text-slate-700 text-sm font-semibold py-2.5 px-4 rounded-lg border border-slate-300 inline-flex items-center gap-2 cursor-pointer transition shadow-sm"
          >
            <Plus class="h-4 w-4" />
            <span>Add Row</span>
          </button>

          <div class="text-right font-sans">
            <span class="text-xs text-slate-400 uppercase tracking-wider font-semibold">Total Value</span>
            <span class="text-lg font-bold text-emerald-600 block font-mono">
              {{ formatCurrency(
                bulkRows.reduce((sum, r) => {
                  const p = products.find(prod => prod.id === r.productId);
                  return sum + (p ? p.sellingPrice * (Number(r.quantity) || 0) : 0);
                }, 0)
              ) }}
            </span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex flex-col sm:flex-row justify-end gap-3 pt-4 border-t border-slate-200 items-center">
          <p v-if="formError" class="text-sm text-rose-600 mr-auto font-semibold flex items-center gap-1"><AlertCircle class="h-4 w-4" /> {{ formError }}</p>
          <p v-if="formSuccess" class="text-sm text-emerald-600 mr-auto font-semibold">✓ {{ formSuccess }}</p>
          
          <button 
            type="button" 
            @click="saveCurrentAsDraft"
            class="py-2.5 px-4 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-semibold shadow-sm cursor-pointer flex items-center gap-2"
          >
            <FileText class="h-4 w-4" />
            <span>Save Draft</span>
          </button>

          <button 
            type="button" 
            @click="showLogForm = false" 
            class="py-2.5 px-4 border border-slate-300 rounded-lg text-sm cursor-pointer hover:bg-slate-50 font-semibold"
          >
            Cancel
          </button>
          
          <button 
            type="button"
            @click="handleBulkSubmit"
            :disabled="isSubmitting"
            class="py-2.5 px-5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold shadow-sm cursor-pointer disabled:opacity-50 flex items-center gap-2"
          >
            <Truck class="h-4 w-4" />
            {{ isSubmitting ? 'Submitting...' : 'Dispatch Route' }}
          </button>
        </div>
      </div>

      <!-- ========== SINGLE ENTRY PANEL ========== -->
      <form v-else @submit.prevent="handleSaleSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-4 font-sans pt-2">
        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Select Product *</label>
          <select 
            v-model="productId"
            class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          >
            <option value="">-- Choose from stock --</option>
            <option v-for="p in products" :key="p.id" :value="p.id" :disabled="p.stock <= 0">
              {{ p.name }} ({{ p.brand }}) [{{ p.stock }} available]
            </option>
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Quantity *</label>
          <input 
            type="number" 
            min="1"
            v-model="quantity"
            class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Price Per Unit</label>
          <div class="py-3 px-4 w-full bg-slate-50 border border-slate-200 rounded-lg text-sm font-semibold text-slate-700 flex items-center font-mono">
            {{ productId 
              ? formatCurrency(products.find(p => p.id === productId)?.sellingPrice || 0) 
              : 'Select product first'
            }}
          </div>
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Customer *</label>
          <input 
            type="text" 
            placeholder="e.g. Reliance Fresh" 
            v-model="customerName"
            @input="(e: any) => {
              const val = e.target.value;
              const selected = allSuggestedCustomers.find(c => val === `${c.name} (${c.address})` || val === c.name);
              if (selected && selected.phone) {
                customerPhone = selected.phone;
              }
            }"
            list="single-customer-list"
            class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 font-semibold bg-white text-slate-800"
          />
          <datalist id="single-customer-list">
            <option v-for="(c, idx) in allSuggestedCustomers" :key="idx" :value="`${c.name} (${c.address})`" />
          </datalist>
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Phone Number</label>
          <input 
            type="text" 
            placeholder="e.g. +91 99887 76655" 
            v-model="customerPhone"
            class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Delivery Method</label>
          <div class="flex rounded-lg border border-slate-200 p-1 bg-slate-100">
            <button
              type="button"
              @click="isVehicle = true"
              :class="['flex-1 text-sm font-semibold rounded-md cursor-pointer py-2.5 flex items-center justify-center gap-2 transition',
                isVehicle ? 'bg-white text-slate-800 shadow-sm font-bold' : 'text-slate-500 hover:text-slate-700'
              ]"
            >
              <Truck class="h-4 w-4" />
              Vehicle
            </button>
            <button
              type="button"
              @click="isVehicle = false"
              :class="['flex-1 text-sm font-semibold rounded-md cursor-pointer py-2.5 flex items-center justify-center gap-2 transition',
                !isVehicle ? 'bg-white text-slate-800 shadow-sm font-bold' : 'text-slate-500 hover:text-slate-700'
              ]"
            >
              <User class="h-4 w-4" />
              Sales Rep
            </button>
          </div>
        </div>

        <div v-if="isVehicle" class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block flex items-center gap-1.5 font-mono">
            <Truck class="h-4 w-4 text-slate-500" />
            Vehicle Plate *
          </label>
          <input 
            type="text" 
            placeholder="e.g. DL-3C-AS-9999" 
            v-model="vehicleNumber"
            @input="vehicleNumber = vehicleNumber.toUpperCase()"
            class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg uppercase font-mono font-semibold focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Assigned Rep *</label>
          <select 
            v-model="dsrId"
            class="w-full text-sm py-3 px-4 border border-slate-200 rounded-lg bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          >
            <option value="">-- Choose Rep --</option>
            <option v-for="d in dsrs" :key="d.id" :value="d.id">
              {{ d.name }} ({{ d.phone }})
            </option>
          </select>
        </div>

        <div class="space-y-2">
          <label class="text-sm font-semibold text-slate-700 block">Payment Method</label>
          <div class="flex rounded-lg border border-slate-200 p-1 bg-slate-100">
            <button
              type="button"
              @click="paymentType = 'Cash'"
              :class="['flex-1 text-sm font-semibold rounded-md cursor-pointer py-2.5 flex items-center justify-center gap-2 transition',
                paymentType === 'Cash' ? 'bg-emerald-600 text-white shadow-sm font-bold' : 'text-slate-500 hover:text-slate-700'
              ]"
            >
              Cash
            </button>
            <button
              type="button"
              @click="paymentType = 'Credit'"
              :class="['flex-1 text-sm font-semibold rounded-md cursor-pointer py-2.5 flex items-center justify-center gap-2 transition',
                paymentType === 'Credit' ? 'bg-rose-600 text-white shadow-sm font-bold' : 'text-slate-500 hover:text-slate-700'
              ]"
            >
              Credit
            </button>
          </div>
        </div>

        <div v-if="paymentType === 'Credit'" class="space-y-2">
          <label class="text-sm font-semibold text-rose-600 block">Down Payment (₹)</label>
          <input 
            type="number" 
            placeholder="Amount paid now" 
            v-model="amountPaid"
            class="w-full text-sm py-3 px-4 border border-rose-200 rounded-lg bg-rose-50/30 focus:outline-none focus:ring-2 focus:ring-rose-400 font-mono"
          />
        </div>

        <div v-if="paymentType === 'Credit'" class="space-y-2">
          <label class="text-sm font-semibold text-rose-600 block">Due Date *</label>
          <input 
            type="date" 
            v-model="dueDate"
            class="w-full text-sm py-3 px-4 border border-rose-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-400"
          />
        </div>

        <div class="md:col-span-3 flex flex-col sm:flex-row justify-end gap-3 pt-4 border-t border-slate-100 items-center">
          <p v-if="formError" class="text-sm text-rose-600 mr-auto font-semibold flex items-center gap-1"><AlertCircle class="h-4 w-4" /> {{ formError }}</p>
          <p v-if="formSuccess" class="text-sm text-emerald-600 mr-auto font-semibold">✓ {{ formSuccess }}</p>
          
          <div class="text-right mr-4 font-sans" v-if="productId">
            <span class="text-xs text-slate-400 uppercase tracking-wider block font-semibold">Estimated Total</span>
            <span class="text-lg font-bold text-slate-800 font-mono">
              {{ formatCurrency((Number(quantity) || 0) * (products.find(p => p.id === productId)?.sellingPrice || 0)) }}
            </span>
          </div>

          <button id="sales-btn-cancel" type="button" @click="showLogForm = false" class="py-2.5 px-4 border border-slate-300 rounded-lg text-sm cursor-pointer hover:bg-slate-50 font-semibold">
            Cancel
          </button>
          <button id="sales-btn-submit" type="submit" :disabled="isSubmitting" class="py-2.5 px-5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-sm font-semibold shadow-sm cursor-pointer disabled:opacity-50 flex items-center gap-2">
            <ShoppingBag class="h-4 w-4" />
            {{ isSubmitting ? 'Saving...' : 'Record Sale' }}
          </button>
        </div>
      </form>
    </div>

    <!-- ========== SALES HISTORY LIST ========== -->
    <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-5 text-left">
      <div class="flex flex-col md:flex-row gap-4 items-center justify-between">
        <!-- Search -->
        <div class="relative w-full md:w-80">
          <Search class="absolute left-3 top-3 h-5 w-5 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search customer, product, vehicle..." 
            v-model="searchQuery"
            class="w-full text-sm pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
          />
        </div>

        <!-- Filters -->
        <div class="flex flex-wrap gap-2 w-full md:w-auto md:justify-end">
          <select 
            v-model="selectedPeriod"
            class="text-sm px-3 py-2 rounded-lg border border-slate-200 bg-white font-semibold text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="ALL">All Dates</option>
            <option value="TODAY">Today</option>
            <option value="WEEK">Last 7 Days</option>
            <option value="MONTH">This Month</option>
            <option value="QUARTER">This Quarter</option>
            <option value="YEAR">This Year</option>
          </select>

          <select 
            v-model="saleFilter"
            class="text-sm px-3 py-2 rounded-lg border border-slate-200 bg-white font-semibold text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="ALL">All Sales</option>
            <option value="ACTIVE">Active Only</option>
            <option value="VOIDED">Voided</option>
          </select>

          <select 
            v-model="sortBy"
            class="text-sm px-3 py-2 rounded-lg border border-slate-200 bg-white font-semibold text-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="DATE_DESC">Date (Latest)</option>
            <option value="DATE_ASC">Date (Oldest)</option>
            <option value="AMOUNT_DESC">Amount (High→Low)</option>
            <option value="AMOUNT_ASC">Amount (Low→High)</option>
          </select>
        </div>
      </div>

      <!-- Sales Table -->
      <div class="border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm font-sans">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase text-xs font-bold tracking-wider">
                <th class="py-3.5 px-4">Invoice</th>
                <th class="py-3.5 px-4">Customer</th>
                <th class="py-3.5 px-4">Product</th>
                <th class="py-3.5 px-4">Route</th>
                <th class="py-3.5 px-4 text-center">Status</th>
                <th class="py-3.5 px-4 text-right">Total</th>
                <th class="py-3.5 px-3 text-center">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="sale in currentSalesList" :key="sale.id" :class="['hover:bg-slate-50/50 transition', sale.isVoided ? 'bg-slate-100 opacity-60' : '']">
                <td class="py-4 px-4">
                  <div>
                    <span class="font-mono text-sm font-bold text-slate-900">#{{ sale.id.substring(sale.id.length - 6).toUpperCase() }}</span>
                    <span class="block text-xs text-slate-400 mt-1 font-mono">
                      {{ new Date(sale.date).toLocaleDateString() }} {{ new Date(sale.date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}
                    </span>
                    <span v-if="sale.isVoided" class="inline-flex items-center gap-1 mt-1 px-2 py-0.5 bg-rose-100 text-rose-700 text-[10px] font-bold rounded border border-rose-200">VOIDED</span>
                  </div>
                </td>

                <td class="py-4 px-4">
                  <div>
                    <span class="font-bold text-slate-800 block leading-snug">{{ sale.customerName }}</span>
                    <span class="text-xs text-slate-400 font-mono" v-if="sale.customerPhone">{{ sale.customerPhone }}</span>
                  </div>
                </td>

                <td class="py-4 px-4">
                  <div>
                    <span class="font-semibold text-slate-700 block">{{ sale.productName }}</span>
                    <span class="text-xs text-slate-400 mt-0.5 block">Qty: <span class="font-semibold text-slate-600">{{ sale.quantity }}</span></span>
                  </div>
                </td>

                <td class="py-4 px-4">
                  <div class="flex flex-col gap-1">
                    <span v-if="sale.isVehicle" class="inline-flex items-center gap-1.5 text-blue-700 bg-blue-50 border border-blue-100 w-fit px-2.5 py-1 rounded-md text-xs font-mono font-semibold">
                      <Truck class="h-3.5 w-3.5" />
                      {{ sale.vehicleNumber }}
                    </span>
                    <span v-else class="inline-flex items-center gap-1.5 text-slate-600 bg-slate-100 border border-slate-200 w-fit px-2.5 py-1 rounded-md text-xs font-semibold">
                      <User class="h-3.5 w-3.5" />
                      Counter
                    </span>
                    <span class="text-xs text-slate-400">Rep: {{ sale.dsrName || 'Self' }}</span>
                  </div>
                </td>

                <td class="py-4 px-4 text-center">
                  <!-- Voided -->
                  <span v-if="sale.isVoided" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">Voided</span>
                  <!-- Status Pills -->
                  <span v-else-if="sale.paymentType === 'Cash'" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                    Paid
                  </span>
                  <div v-else class="flex flex-col items-center gap-1">
                    <span v-if="sale.amountPaid >= sale.totalAmount" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">
                      Paid
                    </span>
                    <span v-else-if="sale.amountPaid > 0" class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                      Partial
                    </span>
                    <span v-else class="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-200">
                      Pending
                    </span>
                    
                    <span class="text-xs text-slate-400" v-if="sale.amountPaid < sale.totalAmount">
                      Paid: <span class="font-mono font-semibold">{{ formatCurrency(sale.amountPaid) }}</span>
                    </span>
                    <span class="text-xs text-rose-500 font-semibold bg-rose-50 px-2 py-0.5 rounded font-mono" v-if="sale.amountPaid < sale.totalAmount && sale.dueDate">
                      Due: {{ new Date(sale.dueDate).toLocaleDateString() }}
                    </span>
                  </div>
                </td>

                <td class="py-4 px-4 text-right font-bold text-slate-800 text-sm font-mono">
                  <div>{{ formatCurrency(sale.netAmount || sale.totalAmount) }}</div>
                  <div v-if="sale.returnTotalAmount && sale.returnTotalAmount > 0" class="text-xs text-amber-600 font-normal mt-0.5">
                    net of {{ formatCurrency(sale.returnTotalAmount) }} returns
                  </div>
                </td>
                
                <!-- Actions column -->
                <td class="py-4 px-3 text-center">
                  <div class="flex items-center justify-center gap-1">
                    <!-- Edit button -->
                    <button 
                      @click="openEditSale(sale)"
                      :disabled="sale.isVoided"
                      class="p-1.5 rounded-lg cursor-pointer transition text-slate-400 hover:text-blue-600 hover:bg-blue-50 disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Edit sale"
                    >
                      <Edit class="h-3.5 w-3.5" />
                    </button>
                    <!-- Void button -->
                    <button 
                      v-if="!sale.isVoided"
                      @click="openVoidSale(sale)"
                      class="p-1.5 rounded-lg cursor-pointer transition text-slate-400 hover:text-rose-600 hover:bg-rose-50"
                      title="Void sale"
                    >
                      <XCircle class="h-3.5 w-3.5" />
                    </button>
                    <!-- Return button -->
                    <button 
                      v-if="!sale.isVoided && !sale.isClosedWithDue"
                      @click="openReturnForm(sale)"
                      class="p-1.5 rounded-lg cursor-pointer transition text-slate-400 hover:text-amber-600 hover:bg-amber-50"
                      title="Return items"
                    >
                      <RotateCcw class="h-3.5 w-3.5" />
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Empty State -->
              <tr v-if="sortedSales.length === 0">
                <td colSpan="7" class="text-center py-12 bg-white">
                  <ShoppingBag class="h-10 w-10 text-slate-300 mx-auto mb-3" />
                  <p class="font-semibold text-slate-600 text-sm">No sales recorded yet</p>
                  <p class="text-sm text-slate-400 mt-1">Click "New Sale" above to record your first sale</p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="bg-slate-50 border-t border-slate-200 px-6 py-3 flex items-center justify-between font-sans">
          <p class="text-sm text-slate-500 text-left">
            Showing <span class="font-semibold">{{ indexOfFirstItem + 1 }}</span> –
            <span class="font-semibold">{{ Math.min(indexOfFirstItem + itemsPerPage, sortedSales.length) }}</span> of
            <span class="font-semibold">{{ sortedSales.length }}</span>
          </p>

          <div class="flex gap-1">
            <button
              @click="currentPage = Math.max(currentPage - 1, 1)"
              :disabled="currentPage === 1"
              class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition"
            >
              Prev
            </button>
            
            <button
              v-for="no in totalPages"
              :key="no"
              @click="currentPage = no"
              :class="['px-3 py-1.5 text-sm border rounded-lg cursor-pointer font-semibold transition',
                currentPage === no
                  ? 'bg-emerald-600 border-emerald-600 text-white'
                  : 'bg-white border-slate-300 text-slate-600 hover:bg-slate-100'
              ]"
            >
              {{ no }}
            </button>

            <button
              @click="currentPage = Math.min(currentPage + 1, totalPages)"
              :disabled="currentPage === totalPages"
              class="px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white font-medium hover:bg-slate-100 disabled:opacity-40 cursor-pointer transition"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    </div><!-- /dashboard-middle -->

    <!-- EDIT SALE MODAL -->
    <div v-if="editingSale" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-fadeIn" @click.self="editingSale = null">
      <div class="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-md mx-4 p-6 space-y-5 text-left">
        <div class="flex justify-between items-center pb-3 border-b border-slate-100">
          <h3 class="font-bold text-slate-800 text-base">Edit Sale #{{ editingSale.id.substring(editingSale.id.length - 6).toUpperCase() }}</h3>
          <button @click="editingSale = null" class="text-slate-400 hover:text-slate-600 cursor-pointer"><X class="h-5 w-5" /></button>
        </div>
        <form @submit.prevent="async () => { editSaleSubmitting = true; editSaleError = ''; try { await props.onEditSale!(editingSale!.id, editSaleFields); editingSale = null; emit('refreshData'); } catch(e: any) { editSaleError = e.message || 'Failed'; } finally { editSaleSubmitting = false; } }" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Customer Name</label>
            <input type="text" v-model="editSaleFields.customerName" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Phone</label>
            <input type="text" v-model="editSaleFields.customerPhone" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Due Date</label>
            <input type="date" v-model="editSaleFields.dueDate" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Vehicle Number</label>
            <input type="text" v-model="editSaleFields.vehicleNumber" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg font-mono uppercase focus:outline-none focus:ring-2 focus:ring-blue-400" />
          </div>
          <p v-if="editSaleError" class="text-sm text-rose-600">{{ editSaleError }}</p>
          <div class="flex gap-3 pt-2">
            <button type="button" @click="editingSale = null" class="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm font-semibold cursor-pointer hover:bg-slate-50 transition">Cancel</button>
            <button type="submit" :disabled="editSaleSubmitting" class="flex-1 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-blue-700 disabled:opacity-50 transition">{{ editSaleSubmitting ? 'Saving...' : 'Save' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- VOID SALE CONFIRMATION -->
    <div v-if="voidingSale" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-fadeIn" @click.self="voidingSale = null; voidForceMode = false">
      <div class="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-sm mx-4 p-6 space-y-5 text-left">
        <div class="flex items-start gap-3">
          <div class="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center shrink-0"><AlertCircle class="h-5 w-5 text-rose-600" /></div>
          <div>
            <h3 class="font-bold text-slate-800 text-base">Void Sale?</h3>
            <p v-if="voidForceMode" class="text-sm text-amber-700 mt-1">
              This sale has payments recorded ({{ formatCurrency(voidingSale.amountPaid) }}). Voiding will reverse the entire transaction including financial history.
              Consider using <strong>Return</strong> instead for partial reversal. Force void only for mistake entries.
            </p>
            <p v-else class="text-sm text-slate-600 mt-1">Void this sale? Stock will be restored. This cannot be undone.</p>
          </div>
        </div>
        <p v-if="voidSaleError" class="text-sm text-rose-600 font-semibold">{{ voidSaleError }}</p>
        <div class="flex gap-3">
          <button @click="voidingSale = null; voidForceMode = false" class="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm font-semibold cursor-pointer hover:bg-slate-50 transition">Cancel</button>
          <button v-if="voidForceMode" @click="handleVoidSaleConfirm(true)" :disabled="voidSaleSubmitting" class="flex-1 py-2.5 bg-amber-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-amber-700 disabled:opacity-50 transition">{{ voidSaleSubmitting ? 'Force Voiding...' : 'Force Void' }}</button>
          <button v-else @click="handleVoidSaleConfirm(false)" :disabled="voidSaleSubmitting" class="flex-1 py-2.5 bg-rose-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-rose-700 disabled:opacity-50 transition">{{ voidSaleSubmitting ? 'Voiding...' : 'Void Sale' }}</button>
        </div>
      </div>
    </div>

    <!-- RETURN SALE ITEM MODAL -->
    <div v-if="returningSale" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 animate-fadeIn" @click.self="returningSale = null">
      <div class="bg-white rounded-2xl shadow-xl border border-slate-200 w-full max-w-sm mx-4 p-6 space-y-5 text-left">
        <div class="flex justify-between items-center pb-3 border-b border-slate-100">
          <h3 class="font-bold text-slate-800 text-base">Return Items</h3>
          <button @click="returningSale = null" class="text-slate-400 hover:text-slate-600 cursor-pointer"><X class="h-5 w-5" /></button>
        </div>
        <p class="text-sm text-slate-600">Return items from: <strong>{{ returningSale.productName }}</strong>
          <span class="text-slate-500">(original: ×{{ returningSale.quantity }}<template v-if="returningSale.returns && returningSale.returns.length > 0">, already returned: ×{{ returningSale.returns.reduce((a: number, r: any) => a + r.quantity, 0) }}</template>)</span>
        </p>
        <form @submit.prevent="async () => { returnSaleSubmitting = true; returnSaleError = ''; try { await props.onReturnItem!(returningSale!.id, { quantity: Number(returnSaleFields.quantity), reason: returnSaleFields.reason, processedBy: returnSaleFields.processedBy }); returningSale = null; emit('refreshData'); } catch(e: any) { returnSaleError = e.message || 'Failed'; } finally { returnSaleSubmitting = false; } }" class="space-y-4">
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Quantity to Return</label>
            <input type="number" min="1" :max="returningSale.quantity" v-model="returnSaleFields.quantity" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Reason</label>
            <select v-model="returnSaleFields.reason" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400">
              <option value="Damaged">Damaged</option>
              <option value="Expired">Expired</option>
              <option value="Wrong Item">Wrong Item</option>
              <option value="Customer Return">Customer Return</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div class="space-y-2">
            <label class="text-sm font-semibold text-slate-700">Processed By</label>
            <input type="text" v-model="returnSaleFields.processedBy" placeholder="e.g. Sanjay" class="w-full text-sm py-2.5 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400" />
          </div>
          <p v-if="returnSaleError" class="text-sm text-rose-600">{{ returnSaleError }}</p>
          <div class="flex gap-3 pt-2">
            <button type="button" @click="returningSale = null" class="flex-1 py-2.5 border border-slate-200 rounded-xl text-sm font-semibold cursor-pointer hover:bg-slate-50 transition">Cancel</button>
            <button type="submit" :disabled="returnSaleSubmitting" class="flex-1 py-2.5 bg-amber-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-amber-700 disabled:opacity-50 transition">{{ returnSaleSubmitting ? 'Processing...' : 'Return' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- CHARTS SIDEBAR -->
    <aside class="dashboard-charts">
      <ChartCard v-if="(sales || []).length > 0" title="Daily Revenue Trend" subtitle="Last 7 days sales performance">
        <div style="height: 210px">
          <BaseChart chartType="line" :chartData="dailySalesTrendData" :chartOptions="dailySalesTrendOptions" />
        </div>
      </ChartCard>

      <ChartCard title="Revenue by Product" subtitle="Top selling products by revenue">
        <div style="height: 210px">
          <BaseChart 
            v-if="(sales || []).length > 0"
            chartType="bar" 
            :chartData="salesByProductData" 
            :chartOptions="salesByProductOptions" 
          />
          <div v-else class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
            <ShoppingBag class="h-8 w-8" />
            <span class="text-sm">No sales data yet</span>
          </div>
        </div>
      </ChartCard>

      <ChartCard title="Payment Mix" subtitle="Cash vs Credit revenue distribution">
        <div style="height: 210px">
          <BaseChart 
            v-if="(sales || []).length > 0"
            chartType="doughnut" 
            :chartData="salesPaymentData" 
            :chartOptions="salesPaymentOptions" 
          />
          <div v-else class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
            <Coins class="h-8 w-8" />
            <span class="text-sm">No payment data yet</span>
          </div>
        </div>
      </ChartCard>
    </aside>
  </div><!-- /dashboard-layout -->
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