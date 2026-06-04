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
  Edit
} from 'lucide-vue-next';
import type { Product, RestockRecord, Supplier, DSR } from '../types';
import { inventoryService } from '../services/api';

const props = withDefaults(defineProps<{
  products: Product[];
  suppliers: Supplier[];
  restocks: RestockRecord[];
  dsrs?: DSR[];
  quickActionProduct?: Product | null;
  formatCurrency?: (amt: number) => string;
}>(), {
  dsrs: () => [],
  quickActionProduct: null
});

const emit = defineEmits<{
  (e: 'addProduct', productData: any): void;
  (e: 'restock', restockData: any): void;
  (e: 'refreshData'): void;
  (e: 'clearQuickActionProduct'): void;
}>();

const searchQuery = ref('');
const activeCategory = ref('All');

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
  receivedBy: '',
  sellingPrice: '',
  location: ''
});

const formError = ref('');
const formSuccess = ref('');
const isSubmitting = ref(false);

// Pagination State
const currentPage = ref(1);
const itemsPerPage = 8;

watch([searchQuery, activeCategory], () => {
  currentPage.value = 1;
});

const categories = ['All', 'Tyres', 'Fluids', 'Batteries', 'Parts', 'General'];

// React to quick actions passed from parent
watch(() => props.quickActionProduct, (newVal) => {
  if (newVal) {
    selectedProduct.value = newVal;
    restockFields.value = {
      quantity: '',
      supplierName: '',
      costPrice: newVal.unitPrice.toString(),
      receivedBy: '',
      sellingPrice: newVal.sellingPrice.toString(),
      location: newVal.location || ''
    };
    showRestockForm.value = true;
    showAddForm.value = false;
    showEditForm.value = false;
    showHistory.value = false;
  }
}, { immediate: true });

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

const formatCurrency = computed(() => {
  return props.formatCurrency || ((amt: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(amt);
  });
});

const handleAddProductSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';
  
  const { name, sku, brand, category, minStockAlert, unitPrice, sellingPrice, location } = newProdFields.value;
  
  if (!name || !sku || !brand || !unitPrice || !sellingPrice) {
    formError.value = 'Please fill out all asterisked (*) fields!';
    return;
  }

  isSubmitting.value = true;
  try {
    emit('addProduct', {
      name,
      sku,
      brand,
      category,
      minStockAlert: Number(minStockAlert),
      unitPrice: Number(unitPrice),
      sellingPrice: Number(sellingPrice),
      location: location || 'Main Rack'
    });
    formSuccess.value = `Successfully added product "${name}"! It starts with 0 stock. Please Restock now.`;
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
    setTimeout(() => {
      showAddForm.value = false;
      formSuccess.value = '';
    }, 2500);
  } catch (err: any) {
    formError.value = err.message || 'Failed to submit.';
  } finally {
    isSubmitting.value = false;
  }
};

const handleRestockSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';

  if (!selectedProduct.value) {
    formError.value = 'Please select a product to restock!';
    return;
  }

  const { quantity, supplierName, costPrice, receivedBy, sellingPrice, location } = restockFields.value;

  if (!quantity || !supplierName) {
    formError.value = 'Quantity and Supplier are required details!';
    return;
  }

  isSubmitting.value = true;
  try {
    emit('restock', {
      productId: selectedProduct.value.id,
      quantity: Number(quantity),
      supplierName,
      costPrice: costPrice ? Number(costPrice) : selectedProduct.value.unitPrice,
      receivedBy: receivedBy || 'Staff Member',
      sellingPrice: sellingPrice ? Number(sellingPrice) : selectedProduct.value.sellingPrice,
      location: location || selectedProduct.value.location
    });
    formSuccess.value = `Direct stock of ${quantity} units logged in for ${selectedProduct.value.name}!`;
    restockFields.value = {
      quantity: '',
      supplierName: '',
      costPrice: '',
      receivedBy: '',
      sellingPrice: '',
      location: ''
    };
    selectedProduct.value = null;
    emit('clearQuickActionProduct');
    setTimeout(() => {
      showRestockForm.value = false;
      formSuccess.value = '';
    }, 2500);
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
    const res = await inventoryService.editProduct(editingProduct.value.id, {
      name,
      sku,
      brand,
      category,
      minStockAlert: Number(minStockAlert),
      unitPrice: Number(unitPrice),
      sellingPrice: Number(sellingPrice),
      location: location || 'Main Rack'
    });

    if (!res.ok) {
      throw new Error(res.data?.error || 'Failed to update template');
    }

    formSuccess.value = `Successfully updated template for "${name}"!`;
    editingProduct.value = null;
    emit('refreshData');
    setTimeout(() => {
      showEditForm.value = false;
      formSuccess.value = '';
    }, 2000);
  } catch (err: any) {
    formError.value = err.message || 'Failed to update template';
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<template>
  <div class="space-y-4 font-sans animate-fadeIn">
    <!-- HEADER CONTROLS -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="text-left">
        <h2 class="text-lg md:text-xl font-display font-bold text-slate-800">📦 Inventory Control</h2>
        <p class="text-[11px] text-slate-500 font-sans mt-0.5">Manage brand parts, add new products, and log provider stock restocks</p>
      </div>

      <!-- CONTROLLER SWITCHES -->
      <div class="flex flex-wrap gap-2">
        <button 
          id="inv-btn-add-prod"
          @click="showAddForm = true; showRestockForm = false; showHistory = false; emit('clearQuickActionProduct')"
          :class="['font-display text-xs px-3 py-2 rounded flex items-center space-x-1.5 transition font-bold leading-none cursor-pointer border',
            showAddForm 
              ? 'bg-blue-600 border-blue-600 text-white shadow-sm' 
              : 'bg-white text-blue-600 border-slate-200 hover:bg-slate-50'
          ]"
        >
          <Plus class="h-3.5 w-3.5" />
          <span>New Product Template</span>
        </button>

        <button 
          id="inv-btn-restock"
          @click="showRestockForm = true; showAddForm = false; showHistory = false;"
          :class="['font-display text-xs px-3 py-2 rounded flex items-center space-x-1.5 transition font-bold leading-none cursor-pointer border',
            showRestockForm 
              ? 'bg-emerald-600 border-emerald-600 text-white shadow-sm' 
              : 'bg-white text-emerald-600 border-slate-200 hover:bg-slate-50'
          ]"
        >
          <ArrowDownCircle class="h-3.5 w-3.5" />
          <span>Stock In / Restock</span>
        </button>

        <button 
          id="inv-btn-history"
          @click="showHistory = !showHistory; showAddForm = false; showRestockForm = false; emit('clearQuickActionProduct')"
          :class="['font-display text-xs px-3 py-2 rounded flex items-center space-x-1.5 transition font-bold leading-none cursor-pointer border',
            showHistory 
              ? 'bg-amber-600 border-amber-600 text-white shadow-sm' 
              : 'bg-white text-amber-600 border-slate-200 hover:bg-slate-50'
          ]"
        >
          <History class="h-3.5 w-3.5" />
          <span>Restock ledger ({{ restocks.length }})</span>
        </button>
      </div>
    </div>

    <!-- ADD PRODUCT TEMPLATE FORM -->
    <div v-if="showAddForm" class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-3 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-2 border-b border-slate-100">
        <h3 class="font-display font-bold text-slate-800 text-sm flex items-center space-x-2">
          <Plus class="h-4 w-4 text-blue-600" />
          <span>Create Product Template (Initial Stock starts at 0)</span>
        </h3>
        <button id="inv-btn-close-add" @click="showAddForm = false" class="text-slate-400 hover:text-slate-605 cursor-pointer">
          <X class="h-4.5 w-4.5" />
        </button>
      </div>

      <form @submit.prevent="handleAddProductSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Product Name *</label>
          <input 
            type="text" 
            placeholder="e.g. Michelin SUV Tyre 16' " 
            v-model="newProdFields.name"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">SKU / Code *</label>
          <input 
            type="text" 
            placeholder="e.g. MICH-SUV16" 
            v-model="newProdFields.sku"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono bg-white"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Brand *</label>
          <input 
            type="text" 
            placeholder="e.g. Michelin / Bosch / Castrol" 
            v-model="newProdFields.brand"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Category</label>
          <select 
            v-model="newProdFields.category"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option v-for="cat in categories.filter(c => c !== 'All')" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Min Stock Alert Level</label>
          <input 
            type="number" 
            v-model="newProdFields.minStockAlert"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Cost Price / Unit Price (₹) *</label>
          <input 
            type="number" 
            placeholder="₹ Dealer cost"
            v-model="newProdFields.unitPrice"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Retail selling Price (₹) *</label>
          <input 
            type="number" 
            placeholder="₹ Selling rate"
            v-model="newProdFields.sellingPrice"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Shelf Rack location</label>
          <input 
            type="text" 
            placeholder="e.g. Rack B-4"
            v-model="newProdFields.location"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white"
          />
        </div>

        <div class="md:col-span-3 flex justify-end space-x-2 pt-2 border-t border-slate-100 items-center">
          <p v-if="formError" class="text-[11px] text-rose-600 mr-auto font-sans font-medium">⚠️ {{ formError }}</p>
          <p v-if="formSuccess" class="text-[11px] text-emerald-600 mr-auto font-sans font-medium">✨ {{ formSuccess }}</p>
          
          <button id="inv-btn-add-cancel" type="button" @click="showAddForm = false" class="px-3 py-1.5 border border-slate-200 rounded text-xs cursor-pointer hover:bg-slate-50 font-bold">
            Cancel
          </button>
          <button id="inv-btn-add-submit" type="submit" :disabled="isSubmitting" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold shadow-sm cursor-pointer disabled:opacity-50">
            {{ isSubmitting ? 'Saving...' : 'Create Template' }}
          </button>
        </div>
      </form>
    </div>

    <!-- EDIT PRODUCT TEMPLATE FORM -->
    <div v-if="showEditForm && editingProduct" class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-3 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-2 border-b border-slate-100">
        <h3 class="font-display font-bold text-slate-800 text-sm flex items-center space-x-2">
          <Plus class="h-4 w-4 text-blue-600" />
          <span>Edit Product Template: {{ editingProduct.name }}</span>
        </h3>
        <button id="inv-btn-close-edit" @click="showEditForm = false; editingProduct = null;" class="text-slate-400 hover:text-slate-600 cursor-pointer">
          <X class="h-4.5 w-4.5" />
        </button>
      </div>

      <form @submit.prevent="handleEditProductSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Product Name *</label>
          <input 
            type="text" 
            v-model="editProdFields.name"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">SKU / Code *</label>
          <input 
            type="text" 
            v-model="editProdFields.sku"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono bg-white"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Brand *</label>
          <input 
            type="text" 
            v-model="editProdFields.brand"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Category</label>
          <select 
            v-model="editProdFields.category"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option v-for="cat in categories.filter(c => c !== 'All')" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Min Stock Alert Level</label>
          <input 
            type="number" 
            v-model="editProdFields.minStockAlert"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Cost Price / Unit Price (₹) *</label>
          <input 
            type="number" 
            v-model="editProdFields.unitPrice"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Retail selling Price (₹) *</label>
          <input 
            type="number" 
            v-model="editProdFields.sellingPrice"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">Shelf Rack location</label>
          <input 
            type="text" 
            v-model="editProdFields.location"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white"
          />
        </div>

        <div class="md:col-span-3 flex justify-end space-x-2 pt-2 border-t border-slate-100 items-center">
          <p v-if="formError" class="text-[11px] text-rose-600 mr-auto font-sans font-medium">⚠️ {{ formError }}</p>
          <p v-if="formSuccess" class="text-[11px] text-emerald-600 mr-auto font-sans font-medium">✨ {{ formSuccess }}</p>
          
          <button id="inv-btn-edit-cancel" type="button" @click="showEditForm = false; editingProduct = null;" class="px-3 py-1.5 border border-slate-200 rounded text-xs cursor-pointer hover:bg-slate-50 font-bold">
            Cancel
          </button>
          <button id="inv-btn-edit-submit" type="submit" :disabled="isSubmitting" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold shadow-sm cursor-pointer disabled:opacity-50">
            {{ isSubmitting ? 'Updating...' : 'Save Template Changes' }}
          </button>
        </div>
      </form>
    </div>

    <!-- RESTOCK / STOCK IN FORM -->
    <div v-if="showRestockForm" class="bg-white p-4 rounded border border-slate-200 shadow-sm space-y-3 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-2 border-b border-slate-100">
        <h3 class="font-display font-semibold text-slate-805 text-sm flex items-center space-x-2">
          <ArrowDownCircle class="h-4.5 w-4.5 text-emerald-605" />
          <span>Log Provider Inventory Restock (Stock In)</span>
        </h3>
        <button id="inv-btn-close-restock" @click="showRestockForm = false; selectedProduct = null; emit('clearQuickActionProduct')" class="text-slate-400 hover:text-slate-600 cursor-pointer">
          <X class="h-4.5 w-4.5" />
        </button>
      </div>

      <form @submit.prevent="handleRestockSubmit" class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">1. Select Product *</label>
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
                  sellingPrice: prod.sellingPrice.toString(),
                  location: prod.location || '',
                  receivedBy: restockFields.receivedBy
                }
              } else {
                restockFields = {
                  quantity: '',
                  supplierName: restockFields.supplierName,
                  costPrice: '',
                  sellingPrice: '',
                  location: '',
                  receivedBy: restockFields.receivedBy
                }
              }
            }"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans bg-white text-slate-800"
          >
            <option value="">-- Choose Brand Product --</option>
            <option v-for="p in products" :key="p.id" :value="p.id">
              {{ p.name }} ({{ p.brand }}) [Stock: {{ p.stock }} units]
            </option>
          </select>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">2. Provider / Brand Supplier *</label>
          <input 
            type="text" 
            placeholder="e.g. Michelin Distributors, Bosch Parts India"
            list="suppliers-list"
            v-model="restockFields.supplierName"
            class="w-full text-xs p-2 border border-slate-200 rounded focus:outline-none bg-white font-sans"
          />
          <datalist id="suppliers-list">
            <option v-for="s in suppliers" :key="s.id" :value="s.name" />
          </datalist>
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">3. Quantity Restocked *</label>
          <input 
            type="number" 
            placeholder="How many boxes/units?" 
            v-model="restockFields.quantity"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">
            4. Cost Price per unit (Default: {{ selectedProduct ? formatCurrency(selectedProduct.unitPrice) : 'None' }})
          </label>
          <input 
            type="number" 
            placeholder="Leave blank to use current cost price" 
            v-model="restockFields.costPrice"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">
            5. Retail selling Price (₹) (Current: {{ selectedProduct ? formatCurrency(selectedProduct.sellingPrice) : 'None' }})
          </label>
          <input 
            type="number" 
            placeholder="Updated retail price"
            v-model="restockFields.sellingPrice"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans bg-white font-mono"
          />
        </div>

        <div class="space-y-1">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">
            6. Shelf rack location (Current: {{ selectedProduct ? selectedProduct.location : 'None' }})
          </label>
          <input 
            type="text" 
            placeholder="Updated location" 
            v-model="restockFields.location"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans bg-white"
          />
        </div>

        <div class="space-y-1 md:col-span-2">
          <label class="text-[10px] font-bold text-slate-650 uppercase tracking-wider block">Received By / Handled by Staff Member *</label>
          <input 
            type="text" 
            placeholder="Staff name handles receipt" 
            list="received-by-staff-datalist"
            v-model="restockFields.receivedBy"
            class="w-full text-xs p-2 border border-slate-200 rounded font-sans bg-white font-bold"
          />
          <datalist id="received-by-staff-datalist">
            <option value="Dealer Counter Desk" />
            <option value="Warehouse Admin Staff" />
            <option value="Finance Cashier" />
            <option v-for="d in dsrs" :key="d.id" :value="d.name" />
          </datalist>
        </div>

        <div class="md:col-span-2 flex justify-end space-x-2 pt-2 border-t border-slate-100 items-center">
          <p v-if="formError" class="text-[11px] text-rose-600 mr-auto font-sans font-medium">⚠️ {{ formError }}</p>
          <p v-if="formSuccess" class="text-[11px] text-emerald-600 mr-auto font-sans font-medium">✨ {{ formSuccess }}</p>
          
          <button id="inv-btn-restock-cancel" type="button" @click="showRestockForm = false; selectedProduct = null; emit('clearQuickActionProduct')" class="px-3 py-1.5 border border-slate-200 rounded text-xs hover:bg-slate-50 font-bold cursor-pointer">
            Cancel
          </button>
          <button id="inv-btn-restock-submit" type="submit" :disabled="isSubmitting || !selectedProduct" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-xs font-bold shadow-sm disabled:opacity-50 cursor-pointer">
            {{ isSubmitting ? 'Logging restock...' : 'Receive Stock' }}
          </button>
        </div>
      </form>
    </div>

    <!-- RESTOCK LEDGER HISTORY LIST -->
    <div v-if="showHistory" class="bg-slate-50 p-4 rounded border border-slate-200 space-y-3 animate-fadeIn text-left">
      <div class="flex justify-between items-center pb-2 border-b border-slate-200">
        <h3 class="font-display font-semibold text-slate-700 text-xs md:text-sm flex items-center space-x-2">
          <History class="h-4 w-4 text-amber-600" />
          <span>Restock Log Books / Supply Transactions</span>
        </h3>
        <button id="inv-btn-close-history" @click="showHistory = false" class="text-slate-400 hover:text-slate-655 cursor-pointer">
          <X class="h-4 w-4" />
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-sans">
          <thead>
            <tr class="border-b border-slate-200 text-slate-400 font-bold uppercase text-[9px] tracking-wider">
              <th class="py-2">Date</th>
              <th className="py-2">Product / Item Name</th>
              <th class="py-2">Supplier Provider</th>
              <th class="py-2">Qty Received</th>
              <th class="py-2">Cost / Unit</th>
              <th class="py-2">Total Amount</th>
              <th class="py-2">Staff</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(restock, index) in restocks.slice().reverse()" :key="index" class="border-b border-slate-150 hover:bg-slate-100/50 transition">
              <td class="py-2 font-mono text-[11px] text-slate-450 text-left">
                {{ new Date(restock.date).toLocaleDateString() }}
              </td>
              <td class="py-2 font-sans font-semibold text-slate-800 text-left">
                {{ restock.productName }}
              </td>
              <td class="py-2 text-slate-500 text-left">{{ restock.supplierName }}</td>
              <td class="py-2 font-bold text-emerald-600 text-left">+{{ restock.quantity }} units</td>
              <td class="py-2 text-slate-500 font-mono text-left">{{ formatCurrency(restock.costPrice) }}</td>
              <td class="py-2 font-bold text-slate-800 font-mono text-left">{{ formatCurrency(restock.totalCost) }}</td>
              <td class="py-2 text-slate-400 text-[11px] text-left">{{ restock.receivedBy }}</td>
            </tr>

            <tr v-if="restocks.length === 0">
              <td colSpan="7" class="text-center py-6 text-slate-400 font-sans">No Restock transaction history registered in database files.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- FILTERS AND CATEGORIES -->
    <div class="bg-white p-3 rounded border border-slate-200 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-3 text-left">
      <div class="relative w-full sm:w-80">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="Search name, brand, SKU..." 
          v-model="searchQuery"
          class="w-full text-xs pl-8 pr-3 py-2 bg-slate-50 border border-slate-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans"
        />
      </div>

      <div class="flex overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0 gap-1 scrollbar-none">
        <button 
          v-for="cat in categories" 
          :key="cat"
          @click="activeCategory = cat"
          :class="['text-[11px] font-sans px-2.5 py-1.5 rounded shrink-0 transition font-bold leading-none cursor-pointer border',
            activeCategory === cat 
              ? 'bg-slate-800 text-white border-slate-800' 
              : 'bg-slate-50 text-slate-600 border-slate-250 hover:bg-slate-100'
          ]"
        >
          {{ cat }}
        </button>
      </div>
    </div>

    <!-- INVENTORY LIST TABLE -->
    <div class="bg-white rounded border border-slate-200 overflow-hidden shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-sans border-collapse">
          <thead>
            <tr class="bg-slate-100 border-b border-slate-200 text-slate-500 uppercase text-[9px] font-extrabold tracking-wider">
              <th class="py-3 px-4 text-left">Product Details</th>
              <th class="py-3 px-4">SKU / Brand</th>
              <th class="py-3 px-4">Category</th>
              <th class="py-3 px-4">Location</th>
              <th class="py-3 px-4 text-center">Current Stock</th>
              <th class="py-3 px-4 text-center">Alert Stock</th>
              <th class="py-3 px-4 text-right">Selling Price</th>
              <th class="py-3 px-4 text-center">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-150">
            <tr v-for="p in currentProducts" :key="p.id" :class="['hover:bg-slate-50 transition', p.stock <= p.minStockAlert ? 'bg-amber-50/10' : '']">
              <td class="py-3 px-4 text-left">
                <div>
                  <span class="font-display font-black text-slate-800 text-sm block">{{ p.name }}</span>
                  <span v-if="p.stock <= p.minStockAlert" class="text-[10px] font-bold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded inline-flex items-center mt-1 leading-none">
                    <AlertTriangle class="h-3 w-3 mr-0.5 animate-pulse text-amber-500" />
                    Low stock alert
                  </span>
                  <span v-else class="text-[10px] font-medium text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded inline-flex items-center mt-1 leading-none">
                    <Check class="h-3 w-3 mr-0.5 text-emerald-600" />
                    Healthy
                  </span>
                </div>
              </td>

              <td class="py-3 px-4 text-left">
                <div>
                  <span class="font-mono text-xs font-bold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded uppercase tracking-wider block w-fit">
                    {{ p.sku }}
                  </span>
                  <span class="block text-[10px] text-slate-450 mt-1 font-semibold">
                    Brand: {{ p.brand }}
                  </span>
                </div>
              </td>

              <td class="py-3 px-4 text-left">
                <span class="px-2 py-0.5 bg-blue-50 text-blue-800 border border-blue-100 font-bold rounded text-[10px] uppercase">
                  {{ p.category }}
                </span>
              </td>

              <td class="py-3 px-4 text-left">
                <span class="text-slate-605 font-mono text-xs font-medium">{{ p.location || 'Main Rack' }}</span>
              </td>

              <td class="py-3 px-4 text-center">
                <span :class="['text-xs font-display font-black font-mono px-2.5 py-1 rounded inline-block',
                  p.stock <= p.minStockAlert 
                    ? 'bg-amber-100 text-amber-800 font-black' 
                    : 'bg-emerald-50 text-emerald-800 font-extrabold'
                ]">
                  {{ p.stock }} units
                </span>
              </td>

              <td class="py-3 px-4 text-center text-slate-500 font-mono text-xs">{{ p.minStockAlert }}</td>

              <td class="py-3 px-4 text-right font-bold text-slate-805 text-xs font-mono">{{ formatCurrency(p.sellingPrice) }}</td>

              <td class="py-3 px-4 text-center">
                <div class="flex items-center justify-center gap-1.5">
                  <button
                    :id="`inv-btn-restock-shortcut-${p.id}`"
                    @click="() => {
                      selectedProduct = p;
                      restockFields = {
                        quantity: '',
                        supplierName: '',
                        costPrice: p.unitPrice.toString(),
                        receivedBy: '',
                        sellingPrice: p.sellingPrice.toString(),
                        location: p.location || ''
                      };
                      showRestockForm = true;
                      showAddForm = false;
                      showEditForm = false;
                      showHistory = false;
                      window.scrollTo({ top: 0, behavior: 'smooth' });
                    }"
                    class="bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[10px] font-display font-medium px-2 py-1 rounded border border-emerald-150 flex items-center space-x-1 cursor-pointer transition shadow-xs"
                  >
                    <ArrowDownCircle class="h-3.5 w-3.5" />
                    <span>Restock</span>
                  </button>

                  <button
                    :id="`inv-btn-edit-shortcut-${p.id}`"
                    @click="handleStartEdit(p)"
                    class="bg-slate-50 hover:bg-slate-100 text-slate-700 text-[10px] font-display font-medium px-2 py-1 rounded border border-slate-150 flex items-center space-x-1 cursor-pointer transition shadow-xs"
                  >
                    <Edit class="h-3 w-3" />
                    <span>Edit</span>
                  </button>
                </div>
              </td>
            </tr>

            <tr v-if="filteredProducts.length === 0">
              <td colSpan="8" class="text-center py-10 bg-white">
                <p class="font-display font-semibold text-slate-700 text-sm font-bold">No matching products found!</p>
                <p class="text-[11px] text-slate-400 font-sans mt-0.5">Refine SKU description or create a new template above.</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Footer -->
      <div v-if="totalPages > 1" class="bg-slate-50 border-t border-slate-200 px-4 py-2.5 flex items-center justify-between font-sans">
        <p class="text-xs text-slate-500">
          Showing <span class="font-semibold">{{ indexOfFirstItem + 1 }}</span> to
          <span class="font-semibold">{{ Math.min(indexOfLastItem, filteredProducts.length) }}</span> of
          <span class="font-semibold">{{ filteredProducts.length }}</span> products
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
                ? 'bg-blue-650 border-blue-650 text-white font-black'
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
</template>
