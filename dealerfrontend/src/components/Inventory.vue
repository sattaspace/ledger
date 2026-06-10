<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { 
  Plus, 
  Search, 
  Package, 
  ArrowDownCircle, 
  Tag, 
  DollarSign, 
  MapPin, 
  AlertTriangle,
  X,
  History,
  Check,
  Edit,
  Trash2,
  Settings,
  Download
} from 'lucide-vue-next';
import VirtualList from './VirtualList.vue';
import BulkActionsBar from './BulkActionsBar.vue';
import type { Product, RestockRecord, Supplier, DSR, Brand, Category } from '../types';
import { BaseChart, ChartCard } from './charts';
import type { ChartData, ChartOptions } from 'chart.js';

const props = withDefaults(defineProps<{
  products: Product[];
  suppliers: Supplier[];
  restocks: RestockRecord[];
  dsrs?: DSR[];
  brands?: Brand[];
  categories?: Category[];
  quickActionProduct?: Product | null;
  formatCurrency?: (amt: number) => string;
  onAddProduct?: (data: any) => Promise<any>;
  onRestock?: (data: any) => Promise<any>;
  onEditProduct?: (productId: string, data: any) => Promise<any>;
  onDeleteProduct?: (productId: string) => Promise<void>;
  onAddBrand?: (name: string) => Promise<any>;
  onDeleteBrand?: (id: string) => Promise<void>;
  onAddCategory?: (name: string) => Promise<any>;
  onDeleteCategory?: (id: string) => Promise<void>;
}>(), {
  dsrs: () => [],
  brands: () => [],
  categories: () => [],
  quickActionProduct: null
});

const emit = defineEmits<{
  (e: 'refreshData'): void;
  (e: 'clearQuickActionProduct'): void;
}>();

const searchQuery = ref('');
const activeCategory = ref('All');

// Window helpers for template access
const scrollToTop = () => window.scrollTo({ top: 0, behavior: 'smooth' });

// Form visibility states
const showAddForm = ref(false);
const showEditForm = ref(false);
const showRestockForm = ref(false);
const showHistory = ref(false);

const selectedProduct = ref<Product | null>(null);
const editingProduct = ref<Product | null>(null);

// Form Fields - New Product
const newProdFields = ref({
  name: '',
  sku: '',
  brand: '',
  category: 'Parts',
  minStockAlert: '10',
  unitPrice: '',
  sellingPrice: '',
  location: ''
});

// Form Fields - Edit Product
const editProdFields = ref({
  name: '',
  sku: '',
  brand: '',
  category: 'Parts',
  minStockAlert: '10',
  unitPrice: '',
  sellingPrice: '',
  location: ''
});

// Form Fields - Restock In
const restockFields = ref({
  quantity: '',
  supplierName: '',
  costPrice: '',
  receivedBy: ''
});

const formError = ref('');
const formSuccess = ref('');
const isSubmitting = ref(false);

// Delete confirmation state
const showDeleteConfirm = ref(false);
const deletingProduct = ref<Product | null>(null);

// Pagination State
const currentPage = ref(1);
const itemsPerPage = 20;

// Auto-save state
const AUTO_SAVE_KEY = 'dealercore_product_draft';
const lastSaved = ref<Date | null>(null);
const hasUnsavedChanges = ref(false);

// Export loading state
const isExporting = ref(false);

// Compact view toggle
const viewMode = ref<'card' | 'table'>('card');
const compactView = computed(() => viewMode.value === 'table');
const selectAll = ref(false);

// Brand & Category management panels
const showBrandPanel = ref(false);
const showCategoryPanel = ref(false);
const newBrandName = ref('');
const newCategoryName = ref('');
const brandSubmitting = ref(false);
const categorySubmitting = ref(false);
const brandError = ref('');
const categoryError = ref('');
const newCategoryInlineName = ref('');

// Computed category list: combine hardcoded + API categories
const allCategories = computed(() => {
  const hardcoded = ['All', 'Tyres', 'Fluids', 'Batteries', 'Parts', 'General'];
  const apiNames = (props.categories || []).map(c => c.name);
  const merged = [...hardcoded];
  apiNames.forEach(name => {
    if (!merged.includes(name)) merged.push(name);
  });
  return merged;
});

watch([searchQuery, activeCategory], () => {
  currentPage.value = 1;
});

const categories = allCategories;

// React to quick actions passed from parent
watch(() => props.quickActionProduct, (newVal) => {
  if (newVal) {
    selectedProduct.value = newVal;
    restockFields.value = {
      quantity: '',
      supplierName: '',
      costPrice: newVal.unitPrice.toString(),
      receivedBy: ''
    };
    showRestockForm.value = true;
    showAddForm.value = false;
    showEditForm.value = false;
    showHistory.value = false;
  }
}, { immediate: true });

// Auto-save form data
watch(newProdFields, () => {
  hasUnsavedChanges.value = true;
  localStorage.setItem(AUTO_SAVE_KEY, JSON.stringify(newProdFields.value));
  lastSaved.value = new Date();
}, { deep: true });

// Restore draft on mount
onMounted(() => {
  const saved = localStorage.getItem(AUTO_SAVE_KEY);
  if (saved) {
    try {
      const draft = JSON.parse(saved);
      if (draft.name || draft.sku) {
        newProdFields.value = draft;
        // Show toast notification about restored draft
        setTimeout(() => {
          formSuccess.value = '📝 Restored unsaved draft';
          setTimeout(() => formSuccess.value = '', 3000);
        }, 500);
      }
    } catch {}
  }
});

// Filter products based on search and selected category
const filteredProducts = computed(() => {
  return props.products.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) || 
                          p.brand.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
                          p.sku.toLowerCase().includes(searchQuery.value.toLowerCase());
    const matchesCategory = activeCategory.value === 'All' || p.category === activeCategory.value;
    return matchesSearch && matchesCategory;
  });
});

const currentProducts = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return filteredProducts.value.slice(start, start + itemsPerPage);
});

const totalPages = computed(() => {
  return Math.ceil(filteredProducts.value.length / itemsPerPage);
});

const indexOfFirstItem = computed(() => {
  return (currentPage.value - 1) * itemsPerPage;
});

const indexOfLastItem = computed(() => {
  return currentPage.value * itemsPerPage;
});

const formatCurrency = computed(() => {
  return props.formatCurrency || ((amt: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  });
});

// Category counts for pill badges
const categoryCounts = computed(() => {
  const counts: Record<string, number> = {};
  allCategories.value.forEach(cat => {
    if (cat === 'All') {
      counts[cat] = props.products.length;
    } else {
      counts[cat] = props.products.filter(p => p.category === cat).length;
    }
  });
  return counts;
});

// Stock level helper
const getStockLevel = (p: Product) => {
  if (p.stock === 0) return 'critical';
  if (p.stock <= p.minStockAlert) return 'low';
  return 'healthy';
};

const getStockPercent = (p: Product) => {
  const max = Math.max(p.minStockAlert * 3, p.stock, 1);
  return Math.min((p.stock / max) * 100, 100);
};

const stockDistributionData = computed(() => {
  const categoryStocks: Record<string, number> = {};
  allCategories.value.filter(c => c !== 'All').forEach(cat => {
    categoryStocks[cat] = props.products
      .filter(p => p.category === cat)
      .reduce((sum, p) => sum + p.stock, 0);
  });
  
  const labels = Object.keys(categoryStocks).filter(k => categoryStocks[k] > 0);
  const values = labels.map(k => categoryStocks[k]);
  
  const colors = [
    'rgba(226, 82, 18, 0.8)',   // orange
    'rgba(16, 185, 129, 0.8)',  // emerald
    'rgba(59, 130, 246, 0.8)',  // blue
    'rgba(139, 92, 246, 0.8)',  // violet
    'rgba(245, 158, 11, 0.8)',  // amber
  ];
  
  return {
    labels,
    datasets: [{
      data: values,
      backgroundColor: colors.slice(0, labels.length),
      borderColor: colors.slice(0, labels.length).map(c => c.replace('0.8)', '1)')),
      borderWidth: 2,
      hoverOffset: 6,
    }]
  };
});

const stockDistributionOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        usePointStyle: true,
        pointStyle: 'circle',
        padding: 12,
        font: { family: 'Inter', size: 11 },
      }
    },
    tooltip: {
      callbacks: {
        label: (ctx: any) => {
          const total = (ctx.dataset.data as number[]).reduce((a, b) => a + b, 0);
          const pct = total > 0 ? ((ctx.raw as number) / total * 100).toFixed(1) : 0;
          return `${ctx.label}: ${ctx.raw} units (${pct}%)`;
        }
      }
    }
  }
}));

const stockHealthSummary = computed(() => {
  const healthy = props.products.filter(p => p.stock > p.minStockAlert).length;
  const low = props.products.filter(p => p.stock > 0 && p.stock <= p.minStockAlert).length;
  const critical = props.products.filter(p => p.stock === 0).length;
  return { healthy, low, critical, total: props.products.length };
});

// Stock value by category bar chart (selling price × stock)
const stockValueData = computed(() => {
  const categoryValues: Record<string, number> = {};
  const categoryCostValues: Record<string, number> = {};
  allCategories.value.filter(c => c !== 'All').forEach(cat => {
    const prods = props.products.filter(p => p.category === cat);
    categoryValues[cat] = prods.reduce((sum, p) => sum + (p.sellingPrice * p.stock), 0);
    categoryCostValues[cat] = prods.reduce((sum, p) => sum + (p.unitPrice * p.stock), 0);
  });
  
  const labels = Object.keys(categoryValues).filter(k => categoryValues[k] > 0 || categoryCostValues[k] > 0);
  
  return {
    labels,
    datasets: [
      {
        label: 'Retail Value',
        data: labels.map(k => categoryValues[k]),
        backgroundColor: 'rgba(59, 130, 246, 0.75)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1,
        borderRadius: 6,
      },
      {
        label: 'Cost Value',
        data: labels.map(k => categoryCostValues[k]),
        backgroundColor: 'rgba(139, 92, 246, 0.75)',
        borderColor: 'rgb(139, 92, 246)',
        borderWidth: 1,
        borderRadius: 6,
      }
    ]
  };
});

const stockValueOptions = computed(() => ({
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

const handleAddProductSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';
  
  const { name, sku, brand, category, minStockAlert, unitPrice, sellingPrice, location } = newProdFields.value;
  
  if (!name || !sku || !brand || !unitPrice || !sellingPrice) {
    formError.value = 'Please fill out all asterisked (*) fields!';
    return;
  }

  // Handle "Add New Category" selection
  let finalCategory = category;
  if (category === '__new__') {
    if (!newCategoryInlineName.value.trim()) {
      formError.value = 'Please enter the new category name!';
      return;
    }
    try {
      await props.onAddCategory!(newCategoryInlineName.value.trim());
      finalCategory = newCategoryInlineName.value.trim();
      newCategoryInlineName.value = '';
    } catch (err: any) {
      formError.value = err.message || 'Failed to create category.';
      return;
    }
  }

  isSubmitting.value = true;
  try {
    await props.onAddProduct!({
      name,
      sku,
      brand,
      category: finalCategory,
      minStockAlert: Number(minStockAlert),
      unitPrice: Number(unitPrice),
      sellingPrice: Number(sellingPrice),
      location: location || 'Main Rack'
    });
    clearDraft();
    newProdFields.value = {
      name: '',
      sku: '',
      brand: '',
      category: 'Parts',
      minStockAlert: '10',
      unitPrice: '',
      sellingPrice: '',
      location: ''
    };
    showAddForm.value = false;
  } catch (err: any) {
    formError.value = err.message || 'Failed to submit.';
  } finally {
    isSubmitting.value = false;
  }
};

// Export to CSV
const handleExportInventory = async () => {
  isExporting.value = true;
  try {
    const headers = ['ID', 'Name', 'SKU', 'Brand', 'Category', 'Stock', 'Min Stock', 'Cost Price', 'Selling Price', 'Location'];
    const rows = filteredProducts.value.map(p => [
      p.id, p.name, p.sku, p.brand, p.category, p.stock, p.minStockAlert, p.unitPrice, p.sellingPrice, p.location
    ]);
    
    const csv = [headers.join(','), ...rows.map((r: any[]) => r.map((field: any) => `"${field}"`).join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `inventory_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    formSuccess.value = `✓ Exported ${rows.length} products to CSV`;
    setTimeout(() => formSuccess.value = '', 3000);
  } catch (err: any) {
    formError.value = 'Export failed: ' + (err.message || 'Unknown error');
  } finally {
    isExporting.value = false;
  }
};

const clearDraft = () => {
  localStorage.removeItem(AUTO_SAVE_KEY);
  hasUnsavedChanges.value = false;
};

const handleRestockSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';

  if (!selectedProduct.value) {
    formError.value = 'Please select a product to restock!';
    return;
  }

  const { quantity, supplierName, costPrice, receivedBy } = restockFields.value;

  if (!quantity || !supplierName) {
    formError.value = 'Quantity and Supplier are required details!';
    return;
  }

  isSubmitting.value = true;
  try {
    await props.onRestock!({
      productId: selectedProduct.value.id,
      quantity: Number(quantity),
      supplierName,
      costPrice: costPrice ? Number(costPrice) : selectedProduct.value.unitPrice,
      receivedBy: receivedBy || 'Staff Member',
    });
    restockFields.value = {
      quantity: '',
      supplierName: '',
      costPrice: '',
      receivedBy: ''
    };
    selectedProduct.value = null;
    emit('clearQuickActionProduct');
    showRestockForm.value = false;
  } catch (err: any) {
    formError.value = err.message || 'Connection error.';
  } finally {
    isSubmitting.value = false;
  }
};

const handleStartEdit = (p: Product) => {
  editingProduct.value = p;
  editProdFields.value = {
    name: p.name,
    sku: p.sku,
    brand: p.brand,
    category: p.category || 'Parts',
    minStockAlert: p.minStockAlert.toString(),
    unitPrice: p.unitPrice.toString(),
    sellingPrice: p.sellingPrice.toString(),
    location: p.location || ''
  };
  formError.value = '';
  formSuccess.value = '';
  showEditForm.value = true;
  showAddForm.value = false;
  showRestockForm.value = false;
  showHistory.value = false;
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const handleEditProductSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';

  if (!editingProduct.value) return;

  const { name, sku, brand, category, minStockAlert, unitPrice, sellingPrice, location } = editProdFields.value;

  if (!name || !sku || !brand || !unitPrice || !sellingPrice) {
    formError.value = 'Please fill out all asterisked (*) fields!';
    return;
  }

  isSubmitting.value = true;
  try {
    await props.onEditProduct!(editingProduct.value.id, {
      name,
      sku,
      brand,
      category,
      minStockAlert: Number(minStockAlert),
      unitPrice: Number(unitPrice),
      sellingPrice: Number(sellingPrice),
      location: location || 'Main Rack'
    });
    editingProduct.value = null;
    emit('refreshData');
    showEditForm.value = false;
  } catch (err: any) {
    formError.value = err.message || 'Failed to update template';
  } finally {
    isSubmitting.value = false;
  }
};

// ─── Delete Product ────────────────────────────────────────────────────
const handleDeleteProduct = (product: Product) => {
  deletingProduct.value = product;
  showDeleteConfirm.value = true;
};

const handleConfirmDeleteProduct = async () => {
  if (!deletingProduct.value) return;
  try {
    await props.onDeleteProduct!(deletingProduct.value.id);
    deletingProduct.value = null;
    showDeleteConfirm.value = false;
    emit('refreshData');
  } catch (err: any) {
    formError.value = err.message || 'Failed to delete product. It may have existing sales.';
    showDeleteConfirm.value = false;
  }
};


</script>

<template>
  <div class="dashboard-layout font-sans animate-fadeIn">
    <div class="dashboard-middle">
    <!-- HEADER -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="text-left">
        <h2 class="text-xl md:text-2xl font-display font-bold text-slate-800 flex items-center gap-2">
          <Package class="h-6 w-6 text-slate-700" />
          Inventory
        </h2>
        <p class="text-sm text-slate-500 mt-1">Manage your products, stock levels, and restocking</p>
      </div>

      <!-- ACTION BUTTONS -->
      <div class="flex flex-wrap gap-3">
        <button 
          id="inv-btn-add-prod"
          @click="showAddForm = true; showRestockForm = false; showHistory = false; emit('clearQuickActionProduct')"
          :class="['min-h-[40px] px-5 py-2.5 rounded-xl flex items-center gap-2 transition font-semibold text-sm cursor-pointer border',
            showAddForm 
              ? 'bg-slate-800 border-slate-800 text-white shadow-lg' 
              : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50 hover:border-slate-300 shadow-sm'
          ]"
        >
          <Plus class="h-4 w-4" />
          <span>As Product Template</span>
        </button>

        <button 
          id="inv-btn-restock"
          @click="showRestockForm = true; showAddForm = false; showHistory = false;"
          :class="['min-h-[40px] px-5 py-2.5 rounded-xl flex items-center gap-2 transition font-semibold text-sm cursor-pointer border',
            showRestockForm 
              ? 'bg-emerald-600 border-emerald-600 text-white shadow-lg' 
              : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50 hover:border-emerald-300 shadow-sm'
          ]"
        >
          <ArrowDownCircle class="h-4 w-4" />
          <span>Restock Items</span>
        </button>

        <button 
          id="inv-btn-history"
          @click="showHistory = !showHistory; showAddForm = false; showRestockForm = false; emit('clearQuickActionProduct')"
          :class="['min-h-[40px] px-5 py-2.5 rounded-xl flex items-center gap-2 transition font-semibold text-sm cursor-pointer border',
            showHistory 
              ? 'bg-amber-600 border-amber-600 text-white shadow-lg' 
              : 'bg-white text-amber-700 border-amber-200 hover:bg-amber-50 hover:border-amber-300 shadow-sm'
          ]"
        >
          <History class="h-4 w-4" />
          <span>Restock History ({{ restocks.length }})</span>
        </button>

        <!-- Export to CSV -->
        <button 
          id="inv-btn-export"
          @click="handleExportInventory"
          :disabled="isExporting"
          :class="['min-h-[40px] px-5 py-2.5 rounded-xl flex items-center gap-2 transition font-semibold text-sm cursor-pointer border',
            isExporting 
              ? 'bg-slate-100 text-slate-400 border-slate-200' 
              : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50 hover:border-emerald-300 shadow-sm'
          ]"
        >
          <Download v-if="!isExporting" class="h-4 w-4" />
          <span v-else class="animate-spin">⟳</span>
          <span>{{ isExporting ? 'Exporting...' : 'Export CSV' }}</span>
        </button>

      </div>
    </div>

    <!-- DELETE PRODUCT CONFIRMATION MODAL -->
    <div v-if="showDeleteConfirm && deletingProduct" class="bg-rose-50 p-6 rounded-2xl border border-rose-200 shadow-sm space-y-5 animate-fadeIn text-left">
      <div class="flex items-start gap-4">
        <div class="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center shrink-0">
          <AlertTriangle class="h-5 w-5 text-rose-600" />
        </div>
        <div class="flex-1">
          <h3 class="font-bold text-slate-800 text-base">Delete Product</h3>
          <p class="text-sm text-slate-600 mt-1">
            Are you sure you want to permanently delete <strong class="text-rose-600">{{ deletingProduct.name }}</strong>? 
            This action cannot be undone. Products with existing sales cannot be deleted.
          </p>
        </div>
      </div>
      <div class="flex justify-end gap-3 pt-2">
        <button 
          type="button" 
          @click="showDeleteConfirm = false; deletingProduct = null" 
          class="min-h-[40px] px-5 py-2.5 border border-slate-200 rounded-xl text-sm cursor-pointer hover:bg-slate-50 font-semibold transition"
        >
          Cancel
        </button>
        <button 
          type="button"
          @click="handleConfirmDeleteProduct"
          class="min-h-[40px] px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-sm font-semibold shadow-sm cursor-pointer transition flex items-center gap-2"
        >
          <Trash2 class="h-4 w-4" />
          Delete Product
        </button>
      </div>
    </div>

    <!-- ADD NEW PRODUCT FORM -->
    <div v-if="showAddForm" class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-4 border-b border-slate-100">
        <div>
          <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
              <Plus class="h-4 w-4 text-slate-600" />
            </div>
            Add New Product
          </h3>
          <p class="text-sm text-slate-500 mt-1 ml-10">Starts with 0 stock — you can restock after adding</p>
        </div>
        <button id="inv-btn-close-add" @click="showAddForm = false" class="text-slate-400 hover:text-slate-600 cursor-pointer p-2 rounded-lg hover:bg-slate-100 transition">
          <X class="h-5 w-5" />
        </button>
      </div>

      <form @submit.prevent="handleAddProductSubmit" class="space-y-6">
        <!-- Section: Product Identity -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-slate-800 text-white text-xs flex items-center justify-center font-bold">1</span>
            Product Identity
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Product Name</label>
              <input 
                type="text" 
                placeholder="e.g. Michelin SUV Tyre 16'" 
                v-model="newProdFields.name"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white placeholder:text-slate-400"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">SKU / Code</label>
              <input 
                type="text" 
                placeholder="e.g. MICH-SUV16" 
                v-model="newProdFields.sku"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono placeholder:text-slate-400"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Brand</label>
              <input 
                type="text" 
                placeholder="e.g. Michelin, Bosch, Castrol" 
                v-model="newProdFields.brand"
                list="brand-datalist"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white placeholder:text-slate-400"
              />
              <datalist id="brand-datalist">
                <option v-for="b in brands" :key="b.id" :value="b.name" />
              </datalist>
            </div>
          </div>
        </div>

        <!-- Section: Classification -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-slate-800 text-white text-xs flex items-center justify-center font-bold">2</span>
            Classification & Location
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Category</label>
              <select 
                v-model="newProdFields.category"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white"
              >
                <option v-for="cat in allCategories.filter(c => c !== 'All')" :key="cat" :value="cat">{{ cat }}</option>
                <option value="__new__">+ Add New Category...</option>
              </select>
              <input v-if="newProdFields.category === '__new__'" type="text" v-model="newCategoryInlineName" placeholder="Enter new category name" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white mt-2 placeholder:text-slate-400" />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Low Stock Alert Level</label>
              <input 
                type="number" 
                placeholder="Alert when stock drops below"
                v-model="newProdFields.minStockAlert"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono placeholder:text-slate-400"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Shelf / Rack Location</label>
              <input 
                type="text" 
                placeholder="e.g. Rack B-4"
                v-model="newProdFields.location"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white placeholder:text-slate-400"
              />
            </div>
          </div>
        </div>

        <!-- Section: Pricing -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-slate-800 text-white text-xs flex items-center justify-center font-bold">3</span>
            Pricing
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Cost Price (what you pay)</label>
              <input 
                type="number" 
                placeholder="Dealer cost per unit"
                v-model="newProdFields.unitPrice"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono placeholder:text-slate-400"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Selling Price (what you charge)</label>
              <input 
                type="number" 
                placeholder="Retail selling rate"
                v-model="newProdFields.sellingPrice"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono placeholder:text-slate-400"
              />
            </div>
          </div>
        </div>

        <!-- Form actions -->
        <div class="flex flex-col sm:flex-row justify-between items-center gap-3 pt-4 border-t border-slate-100">
          <div class="w-full sm:w-auto">
            <p v-if="formError" class="text-sm text-rose-600 font-medium flex items-center gap-1.5">
              <AlertTriangle class="h-4 w-4" /> {{ formError }}
            </p>
            <p v-if="formSuccess" class="text-sm text-emerald-600 font-medium flex items-center gap-1.5">
              <Check class="h-4 w-4" /> {{ formSuccess }}
            </p>
          </div>
          
          <div class="flex gap-3 w-full sm:w-auto">
            <button id="inv-btn-add-cancel" type="button" @click="showAddForm = false" class="min-h-[40px] flex-1 sm:flex-none px-6 py-2.5 border border-slate-200 rounded-xl text-sm cursor-pointer hover:bg-slate-50 font-semibold transition">
              Cancel
            </button>
            <button id="inv-btn-add-submit" type="submit" :disabled="isSubmitting" class="min-h-[40px] flex-1 sm:flex-none px-6 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-sm font-semibold shadow-sm cursor-pointer disabled:opacity-50 transition flex items-center justify-center gap-2">
              <Plus class="h-4 w-4" />
              {{ isSubmitting ? 'Adding...' : 'Add Product' }}
            </button>
          </div>
        </div>
      </form>
    </div>

    <!-- EDIT PRODUCT FORM -->
    <div v-if="showEditForm && editingProduct" class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-4 border-b border-slate-100">
        <div>
          <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
              <Edit class="h-4 w-4 text-slate-600" />
            </div>
            Edit Product: {{ editingProduct.name }}
          </h3>
          <p class="text-sm text-slate-500 mt-1 ml-10">Update product details below</p>
        </div>
        <button id="inv-btn-close-edit" @click="showEditForm = false; editingProduct = null;" class="text-slate-400 hover:text-slate-600 cursor-pointer p-2 rounded-lg hover:bg-slate-100 transition">
          <X class="h-5 w-5" />
        </button>
      </div>

      <form @submit.prevent="handleEditProductSubmit" class="space-y-6">
        <!-- Section: Product Identity -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-slate-800 text-white text-xs flex items-center justify-center font-bold">1</span>
            Product Identity
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Product Name</label>
              <input 
                type="text" 
                v-model="editProdFields.name"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">SKU / Code</label>
              <input 
                type="text" 
                v-model="editProdFields.sku"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Brand</label>
              <input 
                type="text" 
                v-model="editProdFields.brand"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white"
              />
            </div>
          </div>
        </div>

        <!-- Section: Classification -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-slate-800 text-white text-xs flex items-center justify-center font-bold">2</span>
            Classification & Location
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Category</label>
              <select 
                v-model="editProdFields.category"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white"
              >
                <option v-for="cat in allCategories.filter(c => c !== 'All')" :key="cat" :value="cat">{{ cat }}</option>
              </select>
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Low Stock Alert Level</label>
              <input 
                type="number" 
                v-model="editProdFields.minStockAlert"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Shelf / Rack Location</label>
              <input 
                type="text" 
                v-model="editProdFields.location"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white"
              />
            </div>
          </div>
        </div>

        <!-- Section: Pricing -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-slate-800 text-white text-xs flex items-center justify-center font-bold">3</span>
            Pricing
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Cost Price (what you pay)</label>
              <input 
                type="number" 
                v-model="editProdFields.unitPrice"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Selling Price (what you charge)</label>
              <input 
                type="number" 
                v-model="editProdFields.sellingPrice"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 bg-white font-mono"
              />
            </div>
          </div>
        </div>

        <!-- Form actions -->
        <div class="flex flex-col sm:flex-row justify-between items-center gap-3 pt-4 border-t border-slate-100">
          <div class="w-full sm:w-auto">
            <p v-if="formError" class="text-sm text-rose-600 font-medium flex items-center gap-1.5">
              <AlertTriangle class="h-4 w-4" /> {{ formError }}
            </p>
            <p v-if="formSuccess" class="text-sm text-emerald-600 font-medium flex items-center gap-1.5">
              <Check class="h-4 w-4" /> {{ formSuccess }}
            </p>
          </div>
          
          <div class="flex gap-3 w-full sm:w-auto">
            <button id="inv-btn-edit-cancel" type="button" @click="showEditForm = false; editingProduct = null;" class="min-h-[40px] flex-1 sm:flex-none px-6 py-2.5 border border-slate-200 rounded-xl text-sm cursor-pointer hover:bg-slate-50 font-semibold transition">
              Cancel
            </button>
            <button id="inv-btn-edit-submit" type="submit" :disabled="isSubmitting" class="min-h-[40px] flex-1 sm:flex-none px-6 py-2.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-sm font-semibold shadow-sm cursor-pointer disabled:opacity-50 transition flex items-center justify-center gap-2">
              <Check class="h-4 w-4" />
              {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
            </button>
          </div>
        </div>
      </form>
    </div>

    <!-- RESTOCK FORM -->
    <div v-if="showRestockForm" class="bg-white p-6 rounded-2xl border border-emerald-100 shadow-sm space-y-6 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-4 border-b border-emerald-50">
        <div>
          <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
              <ArrowDownCircle class="h-4 w-4 text-emerald-600" />
            </div>
            Restock Items
          </h3>
          <p class="text-sm text-slate-500 mt-1 ml-10">Log incoming stock from your supplier</p>
        </div>
        <button id="inv-btn-close-restock" @click="showRestockForm = false; selectedProduct = null; emit('clearQuickActionProduct')" class="text-slate-400 hover:text-slate-600 cursor-pointer p-2 rounded-lg hover:bg-slate-100 transition">
          <X class="h-5 w-5" />
        </button>
      </div>

      <form @submit.prevent="handleRestockSubmit" class="space-y-6">
        <!-- Section: Which Product -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-emerald-600 text-white text-xs flex items-center justify-center font-bold">1</span>
            Which product are you restocking?
          </h4>
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Select Product</label>
            <select 
              :value="selectedProduct?.id || ''"
              @change="(e: any) => {
                const prod = products.find(p => p.id === e.target.value);
                selectedProduct = prod || null;
                if (prod) {
                  restockFields = {
                    quantity: '',
                    supplierName: restockFields.supplierName,
                    costPrice: prod.unitPrice.toString(),
                    receivedBy: restockFields.receivedBy
                  }
                } else {
                  restockFields = {
                    quantity: '',
                    supplierName: restockFields.supplierName,
                    costPrice: '',
                    receivedBy: restockFields.receivedBy
                  }
                }
              }"
              class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 bg-white"
            >
              <option value="">Choose a product...</option>
              <option v-for="p in products" :key="p.id" :value="p.id">
                {{ p.name }} ({{ p.brand }}) — Stock: {{ p.stock }} units
              </option>
            </select>
          </div>
        </div>

        <!-- Section: Shipment Details -->
        <div>
          <h4 class="text-sm font-semibold text-slate-600 mb-3 flex items-center gap-2">
            <span class="w-6 h-6 rounded-full bg-emerald-600 text-white text-xs flex items-center justify-center font-bold">2</span>
            Shipment Details
          </h4>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Supplier / Provider</label>
              <input 
                type="text" 
                placeholder="e.g. Michelin Distributors"
                list="suppliers-list"
                v-model="restockFields.supplierName"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 bg-white placeholder:text-slate-400"
              />
              <datalist id="suppliers-list">
                <option v-for="s in suppliers" :key="s.id" :value="s.name" />
              </datalist>
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">How many units?</label>
              <input 
                type="number" 
                placeholder="Number of units received" 
                v-model="restockFields.quantity"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 bg-white font-mono placeholder:text-slate-400"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">
                Cost Price per Unit
                <span class="text-slate-400 font-normal" v-if="selectedProduct">(current: {{ formatCurrency(selectedProduct.unitPrice) }})</span>
              </label>
              <input 
                type="number" 
                placeholder="Leave blank to use current cost price" 
                v-model="restockFields.costPrice"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 bg-white font-mono placeholder:text-slate-400"
              />
            </div>

            <div class="space-y-2">
              <label class="text-sm font-medium text-slate-700 block">Received By (Staff)</label>
              <input 
                type="text" 
                placeholder="Staff name who received stock" 
                list="received-by-staff-datalist"
                v-model="restockFields.receivedBy"
                class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-400 focus:border-emerald-400 bg-white placeholder:text-slate-400"
              />
              <datalist id="received-by-staff-datalist">
                <option value="Dealer Counter Desk" />
                <option value="Warehouse Admin Staff" />
                <option value="Finance Cashier" />
                <option v-for="d in dsrs" :key="d.id" :value="d.name" />
              </datalist>
            </div>
          </div>
        </div>

        <!-- Form actions -->
        <div class="flex flex-col sm:flex-row justify-between items-center gap-3 pt-4 border-t border-emerald-50">
          <div class="w-full sm:w-auto">
            <p v-if="formError" class="text-sm text-rose-600 font-medium flex items-center gap-1.5">
              <AlertTriangle class="h-4 w-4" /> {{ formError }}
            </p>
            <p v-if="formSuccess" class="text-sm text-emerald-600 font-medium flex items-center gap-1.5">
              <Check class="h-4 w-4" /> {{ formSuccess }}
            </p>
          </div>
          
          <div class="flex gap-3 w-full sm:w-auto">
            <button id="inv-btn-restock-cancel" type="button" @click="showRestockForm = false; selectedProduct = null; emit('clearQuickActionProduct')" class="min-h-[40px] flex-1 sm:flex-none px-6 py-2.5 border border-slate-200 rounded-xl text-sm hover:bg-slate-50 font-semibold cursor-pointer transition">
              Cancel
            </button>
            <button id="inv-btn-restock-submit" type="submit" :disabled="isSubmitting || !selectedProduct" class="min-h-[40px] flex-1 sm:flex-none px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold shadow-sm disabled:opacity-50 cursor-pointer transition flex items-center justify-center gap-2">
              <ArrowDownCircle class="h-4 w-4" />
              {{ isSubmitting ? 'Restocking...' : 'Receive Stock' }}
            </button>
          </div>
        </div>
      </form>
    </div>

    <!-- RESTOCK HISTORY — TIMELINE STYLE -->
    <div v-if="showHistory" class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-6 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-4 border-b border-slate-100">
        <div>
          <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
            <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
              <History class="h-4 w-4 text-amber-600" />
            </div>
            Restock History
          </h3>
          <p class="text-sm text-slate-500 mt-1 ml-10">{{ restocks.length }} shipment{{ restocks.length !== 1 ? 's' : '' }} received</p>
        </div>
        <button id="inv-btn-close-history" @click="showHistory = false" class="text-slate-400 hover:text-slate-600 cursor-pointer p-2 rounded-lg hover:bg-slate-100 transition">
          <X class="h-5 w-5" />
        </button>
      </div>

      <!-- Empty state -->
      <div v-if="restocks.length === 0" class="py-12 text-center">
        <Package class="h-12 w-12 text-slate-300 mx-auto mb-3" />
        <p class="text-sm font-semibold text-slate-500">No restock history yet</p>
        <p class="text-sm text-slate-400 mt-1">Your incoming stock shipments will appear here</p>
      </div>

      <!-- Timeline list -->
      <div v-else class="space-y-0">
        <div 
          v-for="(restock, index) in restocks.slice().reverse()" 
          :key="index"
          class="relative flex gap-4 pb-6"
        >
          <!-- Timeline line -->
          <div class="flex flex-col items-center">
            <div class="w-3 h-3 rounded-full bg-emerald-500 border-2 border-white shadow-sm mt-1.5 shrink-0"></div>
            <div v-if="index < restocks.length - 1" class="w-0.5 flex-1 bg-slate-200 mt-1"></div>
          </div>

          <!-- Timeline card -->
          <div class="flex-1 bg-slate-50 rounded-xl p-4 border border-slate-100 hover:border-slate-200 transition">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div class="flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-semibold text-sm text-slate-800">{{ restock.productName }}</span>
                  <span class="text-sm font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-lg">+{{ restock.quantity }} units</span>
                </div>
                <div class="flex items-center gap-3 mt-2 text-sm text-slate-500 flex-wrap">
                  <span class="flex items-center gap-1">
                    <MapPin class="h-3.5 w-3.5" />
                    {{ restock.supplierName }}
                  </span>
                  <span class="flex items-center gap-1">
                    <DollarSign class="h-3.5 w-3.5" />
                    {{ formatCurrency(restock.costPrice) }}/unit
                  </span>
                  <span class="font-semibold text-slate-700">{{ formatCurrency(restock.totalCost) }} total</span>
                </div>
              </div>
              <div class="text-right shrink-0">
                <p class="text-sm text-slate-500">{{ new Date(restock.date).toLocaleDateString() }}</p>
                <p class="text-xs text-slate-400 mt-0.5">by {{ restock.receivedBy }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- SEARCH & CATEGORY FILTERS -->
    <div class="space-y-4">
      <!-- Search bar -->
      <div class="relative">
        <Search class="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-slate-400" />
        <input 
          type="text" 
          placeholder="Search products..." 
          v-model="searchQuery"
          class="w-full text-sm pl-12 pr-4 py-3.5 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-slate-400 focus:border-slate-400 font-sans shadow-sm placeholder:text-slate-400"
        />
      </div>

      <!-- Category pills with counts -->
      <div class="flex overflow-x-auto gap-2 pb-1 scrollbar-none">
        <button 
          v-for="cat in categories" 
          :key="cat"
          @click="activeCategory = cat"
          :class="['min-h-[36px] px-4 py-2 rounded-xl shrink-0 transition font-semibold text-sm cursor-pointer border flex items-center gap-2',
            activeCategory === cat 
              ? 'bg-slate-800 text-white border-slate-800 shadow-md' 
              : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:border-slate-300 shadow-sm'
          ]"
        >
          <span>{{ cat }}</span>
          <span :class="['text-xs px-1.5 py-0.5 rounded-md font-bold',
            activeCategory === cat 
              ? 'bg-white/20 text-white' 
              : 'bg-slate-100 text-slate-500'
          ]">
            {{ categoryCounts[cat] || 0 }}
          </span>
        </button>
      </div>
    </div>

    <!-- BRAND & CATEGORY MANAGEMENT PANELS -->
    <div class="flex flex-wrap gap-2">
      <button 
        @click="showBrandPanel = !showBrandPanel; showCategoryPanel = false"
        :class="['px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition border',
          showBrandPanel ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
        ]"
      >
        <Settings class="h-3 w-3" /> Brands ({{ brands.length }})
      </button>
      <button 
        @click="showCategoryPanel = !showCategoryPanel; showBrandPanel = false"
        :class="['px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-1.5 cursor-pointer transition border',
          showCategoryPanel ? 'bg-slate-800 text-white border-slate-800' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
        ]"
      >
        <Settings class="h-3 w-3" /> Categories ({{ categories.length }})
      </button>
    </div>

    <!-- Brand Management Panel -->
    <div v-if="showBrandPanel" class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4 animate-fadeIn text-left">
      <div class="flex justify-between items-center">
        <h4 class="font-bold text-slate-800 text-sm">Manage Brands</h4>
        <button @click="showBrandPanel = false" class="text-slate-400 hover:text-slate-600 cursor-pointer"><X class="h-4 w-4" /></button>
      </div>
      <div class="flex gap-2">
        <input type="text" v-model="newBrandName" placeholder="New brand name" class="flex-1 text-sm py-2 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400" />
        <button 
          @click="async () => { if (!newBrandName.trim()) { brandError = 'Name required'; return; } brandSubmitting = true; brandError = ''; try { await props.onAddBrand!(newBrandName.trim()); newBrandName = ''; } catch(e: any) { brandError = e.message || 'Failed'; } finally { brandSubmitting = false; } }"
          :disabled="brandSubmitting"
          class="px-4 py-2 bg-slate-800 text-white text-xs font-semibold rounded-lg cursor-pointer hover:bg-slate-900 disabled:opacity-50 transition"
        >
          {{ brandSubmitting ? 'Adding...' : 'Add' }}
        </button>
      </div>
      <p v-if="brandError" class="text-xs text-rose-600">{{ brandError }}</p>
      <div v-if="brands.length > 0" class="flex flex-wrap gap-2">
        <span v-for="b in brands" :key="b.id" class="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-xs font-medium px-3 py-1.5 rounded-lg">
          {{ b.name }}
          <button @click="async () => { try { await props.onDeleteBrand!(b.id); } catch(e: any) { brandError = e.message || 'Failed'; } }" class="text-slate-400 hover:text-rose-600 cursor-pointer"><X class="h-3 w-3" /></button>
        </span>
      </div>
      <p v-else class="text-xs text-slate-400">No brands configured yet.</p>
    </div>

    <!-- Category Management Panel -->
    <div v-if="showCategoryPanel" class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4 animate-fadeIn text-left">
      <div class="flex justify-between items-center">
        <h4 class="font-bold text-slate-800 text-sm">Manage Categories</h4>
        <button @click="showCategoryPanel = false" class="text-slate-400 hover:text-slate-600 cursor-pointer"><X class="h-4 w-4" /></button>
      </div>
      <div class="flex gap-2">
        <input type="text" v-model="newCategoryName" placeholder="New category name" class="flex-1 text-sm py-2 px-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-400" />
        <button 
          @click="async () => { if (!newCategoryName.trim()) { categoryError = 'Name required'; return; } categorySubmitting = true; categoryError = ''; try { await props.onAddCategory!(newCategoryName.trim()); newCategoryName = ''; } catch(e: any) { categoryError = e.message || 'Failed'; } finally { categorySubmitting = false; } }"
          :disabled="categorySubmitting"
          class="px-4 py-2 bg-slate-800 text-white text-xs font-semibold rounded-lg cursor-pointer hover:bg-slate-900 disabled:opacity-50 transition"
        >
          {{ categorySubmitting ? 'Adding...' : 'Add' }}
        </button>
      </div>
      <p v-if="categoryError" class="text-xs text-rose-600">{{ categoryError }}</p>
      <div v-if="categories.length > 0" class="flex flex-wrap gap-2">
        <span v-for="c in categories" :key="c.id" class="inline-flex items-center gap-1.5 bg-slate-100 text-slate-700 text-xs font-medium px-3 py-1.5 rounded-lg">
          {{ c.name }}
          <button @click="async () => { try { await props.onDeleteCategory!(c.id); } catch(e: any) { categoryError = e.message || 'Failed'; } }" class="text-slate-400 hover:text-rose-600 cursor-pointer"><X class="h-3 w-3" /></button>
        </span>
      </div>
      <p v-else class="text-xs text-slate-400">No categories configured yet.</p>
    </div>

    <!-- VIEW MODE TOGGLE -->
    <div class="flex gap-1 bg-slate-100 p-1 rounded-lg">
      <button @click="viewMode = 'card'" :class="[viewMode === 'card' ? 'bg-white shadow-sm' : 'text-slate-500', 'px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer']">Cards</button>
      <button @click="viewMode = 'table'" :class="[viewMode === 'table' ? 'bg-white shadow-sm' : 'text-slate-500', 'px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer']">Table</button>
    </div>

    <!-- PRODUCT CARDS GRID (Card View) -->
    <div v-if="viewMode === 'card' && filteredProducts.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div 
        v-for="p in currentProducts" 
        :key="p.id"
        :class="['bg-white rounded-2xl border p-5 transition hover:shadow-md group',
          getStockLevel(p) === 'critical' 
            ? 'border-red-300 bg-red-50/30' 
            : getStockLevel(p) === 'low' 
              ? 'border-amber-300 bg-amber-50/30' 
              : 'border-slate-200 hover:border-slate-300'
        ]"
      >
        <!-- Card header: name + low stock badge -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="flex-1 min-w-0">
            <h3 class="font-bold text-sm text-slate-800 truncate">{{ p.name }}</h3>
            <div class="flex items-center gap-2 mt-1.5 flex-wrap">
              <span class="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-0.5 rounded-lg">{{ p.brand }}</span>
              <span class="text-xs font-semibold text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded-lg">{{ p.category }}</span>
            </div>
          </div>
          <div v-if="getStockLevel(p) !== 'healthy'" class="shrink-0">
            <div :class="['flex items-center gap-1 text-xs font-bold px-2 py-1 rounded-lg',
              getStockLevel(p) === 'critical' 
                ? 'text-red-700 bg-red-100' 
                : 'text-amber-700 bg-amber-100'
            ]">
              <AlertTriangle :class="['h-3.5 w-3.5', getStockLevel(p) === 'critical' ? 'animate-pulse' : '']" />
              {{ getStockLevel(p) === 'critical' ? 'Out of Stock' : 'Low Stock' }}
            </div>
          </div>
        </div>

        <!-- Stock level bar -->
        <div class="mb-4">
          <div class="flex items-center justify-between mb-1.5">
            <span class="text-xs text-slate-600">Stock Level</span>
            <span :class="['text-xs font-bold tabular-nums',
              getStockLevel(p) === 'critical' ? 'text-red-600' : 
              getStockLevel(p) === 'low' ? 'text-amber-600' : 'text-emerald-600'
            ]">
              {{ p.stock }} / {{ p.minStockAlert }} min
            </span>
          </div>
          <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
            <div 
              :class="['h-full rounded-full transition-all duration-500',
                getStockLevel(p) === 'critical' ? 'bg-red-500' : 
                getStockLevel(p) === 'low' ? 'bg-amber-500' : 'bg-emerald-500'
              ]"
              :style="{ width: getStockPercent(p) + '%' }"
            ></div>
          </div>
        </div>

        <!-- Price -->
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-1.5 text-slate-500">
            <Tag class="h-3.5 w-3.5" />
            <span class="text-xs">SKU: {{ p.sku }}</span>
          </div>
          <div class="text-right">
            <span class="text-sm font-bold text-slate-800">{{ formatCurrency(p.sellingPrice) }}</span>
          </div>
        </div>

        <!-- Location -->
        <div v-if="p.location" class="flex items-center gap-1.5 text-slate-400 mb-4">
          <MapPin class="h-3.5 w-3.5" />
          <span class="text-xs">{{ p.location }}</span>
        </div>

        <!-- Action buttons -->
        <div class="flex gap-2 pt-3 border-t border-slate-100">
          <button
            :id="`inv-btn-restock-shortcut-${p.id}`"
            @click="() => {
              selectedProduct = p;
              restockFields = {
                quantity: '',
                supplierName: '',
                costPrice: p.unitPrice.toString(),
                receivedBy: ''
              };
              showRestockForm = true;
              showAddForm = false;
              showEditForm = false;
              showHistory = false;
              scrollToTop();
            }"
            class="min-h-[36px] flex-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold px-3 py-2 rounded-xl border border-emerald-200 flex items-center justify-center gap-1 cursor-pointer transition"
          >
            <ArrowDownCircle class="h-3.5 w-3.5" />
            <span>Restock</span>
          </button>

          <button
            :id="`inv-btn-edit-shortcut-${p.id}`"
            @click="handleStartEdit(p)"
            class="min-h-[36px] flex-1 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold px-3 py-2 rounded-xl border border-slate-200 flex items-center justify-center gap-1 cursor-pointer transition"
          >
            <Edit class="h-3.5 w-3.5" />
            <span>Edit</span>
          </button>

          <button
            :id="`inv-btn-delete-shortcut-${p.id}`"
            @click="handleDeleteProduct(p)"
            class="min-h-[36px] flex-1 bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold px-3 py-2 rounded-xl border border-rose-200 flex items-center justify-center gap-1 cursor-pointer transition"
          >
            <Trash2 class="h-3.5 w-3.5" />
            <span>Delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- TABLE VIEW -->
    <div v-if="viewMode === 'table' && filteredProducts.length > 0" class="overflow-x-auto border rounded-xl">
      <table class="w-full text-xs">
        <thead class="bg-slate-50 border-b">
          <tr>
            <th class="py-2 px-3 text-left font-semibold text-slate-500">Product</th>
            <th class="py-2 px-3 text-left font-semibold text-slate-500">SKU</th>
            <th class="py-2 px-3 text-left font-semibold text-slate-500">Brand</th>
            <th class="py-2 px-3 text-left font-semibold text-slate-500">Category</th>
            <th class="py-2 px-3 text-right font-semibold text-slate-500">Stock</th>
            <th class="py-2 px-3 text-right font-semibold text-slate-500">Cost</th>
            <th class="py-2 px-3 text-right font-semibold text-slate-500">Sell</th>
            <th class="py-2 px-3 text-center font-semibold text-slate-500">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="product in currentProducts" :key="product.id" class="hover:bg-slate-50">
            <td class="py-2 px-3 font-medium text-slate-800">{{ product.name }}</td>
            <td class="py-2 px-3 font-mono text-slate-500">{{ product.sku }}</td>
            <td class="py-2 px-3 text-slate-600">{{ product.brand }}</td>
            <td class="py-2 px-3"><span class="bg-slate-100 px-2 py-0.5 rounded text-slate-600">{{ product.category }}</span></td>
            <td class="py-2 px-3 text-right font-bold" :class="product.stock <= product.minStockAlert ? 'text-rose-600' : 'text-slate-800'">{{ product.stock }}</td>
            <td class="py-2 px-3 text-right text-slate-500">{{ formatCurrency(product.unitPrice) }}</td>
            <td class="py-2 px-3 text-right font-semibold text-slate-800">{{ formatCurrency(product.sellingPrice) }}</td>
            <td class="py-2 px-3 text-center">
              <div class="flex justify-center gap-1">
                <button @click="() => { selectedProduct = product; restockFields = { quantity: '', supplierName: '', costPrice: product.unitPrice.toString(), receivedBy: '' }; showRestockForm = true; showAddForm = false; showEditForm = false; showHistory = false; scrollToTop(); }" class="p-1 hover:bg-emerald-50 rounded text-emerald-600" title="Restock"><Package class="h-3.5 w-3.5" /></button>
                <button @click="handleStartEdit(product)" class="p-1 hover:bg-blue-50 rounded text-blue-600" title="Edit"><Edit class="h-3.5 w-3.5" /></button>
                <button @click="handleDeleteProduct(product)" class="p-1 hover:bg-rose-50 rounded text-rose-600" title="Delete"><Trash2 class="h-3.5 w-3.5" /></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div v-if="filteredProducts.length === 0" class="bg-white rounded-2xl border border-slate-200 p-12 text-center">
      <Package class="h-16 w-16 text-slate-300 mx-auto mb-4" />
      <p class="text-base font-semibold text-slate-600">No products found</p>
      <p class="text-sm text-slate-400 mt-1">Try adjusting your search or add a new product</p>
    </div>

    <!-- PAGINATION -->
    <div v-if="totalPages > 1" class="bg-white rounded-2xl border border-slate-200 px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
      <p class="text-sm text-slate-500">
        Showing <span class="font-semibold text-slate-700">{{ indexOfFirstItem + 1 }}</span>–<span class="font-semibold text-slate-700">{{ Math.min(indexOfLastItem, filteredProducts.length) }}</span> of
        <span class="font-semibold text-slate-700">{{ filteredProducts.length }}</span> products
      </p>

      <div class="flex gap-1.5">
        <button
          @click="currentPage = Math.max(currentPage - 1, 1)"
          :disabled="currentPage === 1"
          class="min-h-[36px] px-4 py-2 text-sm border border-slate-200 rounded-xl bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition"
        >
          Prev
        </button>
        
        <button
          v-for="no in totalPages"
          :key="no"
          @click="currentPage = no"
          :class="['min-h-[36px] px-4 py-2 text-sm border rounded-xl cursor-pointer font-semibold transition',
            currentPage === no
              ? 'bg-slate-800 border-slate-800 text-white'
              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
          ]"
        >
          {{ no }}
        </button>

        <button
          @click="currentPage = Math.min(currentPage + 1, totalPages)"
          :disabled="currentPage === totalPages"
          class="min-h-[36px] px-4 py-2 text-sm border border-slate-200 rounded-xl bg-white font-medium hover:bg-slate-50 disabled:opacity-40 cursor-pointer transition"
        >
          Next
        </button>
      </div>

    </div>
    </div>
    <aside class="dashboard-charts">
      <!-- Stock Distribution Doughnut -->
      <ChartCard title="Stock by Category" subtitle="Units per product category">
          <div style="height: 220px">
            <BaseChart 
              v-if="products.length > 0"
              chartType="doughnut" 
              :chartData="stockDistributionData" 
              :chartOptions="stockDistributionOptions" 
            />
            <div v-else class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
              <Package class="h-8 w-8" />
              <span class="text-sm">No products yet</span>
            </div>
          </div>
        </ChartCard>
      <!-- Stock Value Bar Chart -->
      <ChartCard title="Inventory Value" subtitle="Retail vs Cost value by category">
          <div style="height: 220px">
            <BaseChart 
              v-if="products.length > 0"
              chartType="bar" 
              :chartData="stockValueData" 
              :chartOptions="stockValueOptions" 
            />
            <div v-else class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
              <DollarSign class="h-8 w-8" />
              <span class="text-sm">No inventory data yet</span>
            </div>
          </div>
        </ChartCard>
      <!-- Stock Health Summary -->
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5">
          <h3 class="font-display font-bold text-slate-800 text-sm mb-4">Stock Health Overview</h3>
          <div class="grid grid-cols-3 gap-3 mb-4">
            <!-- Healthy -->
            <div class="bg-emerald-50 border border-emerald-100 rounded-xl p-3 text-center">
              <div class="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-2">
                <Check class="h-4 w-4 text-white" />
              </div>
              <p class="text-xl font-bold text-emerald-700 font-mono">{{ stockHealthSummary.healthy }}</p>
              <p class="text-[10px] text-emerald-600 font-semibold mt-1">Healthy</p>
            </div>
            <!-- Low -->
            <div class="bg-amber-50 border border-amber-100 rounded-xl p-3 text-center">
              <div class="w-8 h-8 bg-amber-500 rounded-full flex items-center justify-center mx-auto mb-2">
                <AlertTriangle class="h-4 w-4 text-white" />
              </div>
              <p class="text-xl font-bold text-amber-700 font-mono">{{ stockHealthSummary.low }}</p>
              <p class="text-[10px] text-amber-600 font-semibold mt-1">Low Stock</p>
            </div>
            <!-- Critical -->
            <div class="bg-rose-50 border border-rose-100 rounded-xl p-3 text-center">
              <div class="w-8 h-8 bg-rose-500 rounded-full flex items-center justify-center mx-auto mb-2">
                <X class="h-4 w-4 text-white" />
              </div>
              <p class="text-xl font-bold text-rose-700 font-mono">{{ stockHealthSummary.critical }}</p>
              <p class="text-[10px] text-rose-600 font-semibold mt-1">Out of Stock</p>
            </div>
          </div>
          <!-- Stock progress bar -->
          <div v-if="stockHealthSummary.total > 0" class="space-y-1">
            <div class="flex rounded-full overflow-hidden h-3 bg-slate-100">
              <div 
                class="bg-emerald-500 transition-all duration-500" 
                :style="{ width: `${(stockHealthSummary.healthy / stockHealthSummary.total) * 100}%` }"
              ></div>
              <div 
                class="bg-amber-400 transition-all duration-500" 
                :style="{ width: `${(stockHealthSummary.low / stockHealthSummary.total) * 100}%` }"
              ></div>
              <div 
                class="bg-rose-500 transition-all duration-500" 
                :style="{ width: `${(stockHealthSummary.critical / stockHealthSummary.total) * 100}%` }"
              ></div>
            </div>
            <div class="flex justify-between text-xs text-slate-400">
              <span>{{ Math.round((stockHealthSummary.healthy / stockHealthSummary.total) * 100) }}% healthy</span>
              <span>{{ stockHealthSummary.total }} total products</span>
            </div>
          </div>
          <!-- Total inventory value -->
          <div class="mt-4 pt-3 border-t border-slate-100">
            <p class="text-xs text-slate-400 font-semibold uppercase">Total Inventory Value</p>
            <p class="text-lg font-bold text-slate-800 font-mono mt-1">
              {{ formatCurrency(products.reduce((sum, p) => sum + (p.sellingPrice * p.stock), 0)) }}
            </p>
          </div>
        </div>
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
