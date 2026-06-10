<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { 
  Users, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  X, 
  Phone, 
  AlertTriangle, 
  Check 
} from 'lucide-vue-next';
import type { Supplier, Category } from '../types';

const props = withDefaults(defineProps<{
  suppliers: Supplier[];
  categories?: Category[];
  formatCurrency?: (amt: number) => string;
  onAddSupplier?: (data: any) => Promise<any>;
  onEditSupplier?: (supplierId: string, data: any) => Promise<any>;
  onDeleteSupplier?: (supplierId: string) => Promise<void>;
}>(), {
  categories: () => [],
});

const emit = defineEmits<{
  (e: 'refreshData'): void;
}>();

// Search & filter
const searchQuery = ref('');
const activeCategory = ref('All');

// Pagination
const currentPage = ref(1);
const itemsPerPage = 10;

// Form visibility states
const showAddForm = ref(false);
const showEditForm = ref(false);

// Form fields - Add
const newSupplierFields = ref({ name: '', phone: '', category: 'Parts' });

// Form fields - Edit
const editingSupplier = ref<Supplier | null>(null);
const editSupplierFields = ref({ name: '', phone: '', category: 'Parts' });

// Form states
const formError = ref('');
const formSuccess = ref('');
const isSubmitting = ref(false);

// Delete confirmation
const deleteConfirmSupplier = ref<Supplier | null>(null);

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

// Reset page on filter change
watch([searchQuery, activeCategory], () => {
  currentPage.value = 1;
});

// Filtered suppliers
const filteredSuppliers = computed(() => {
  return props.suppliers.filter(s => {
    const q = searchQuery.value.toLowerCase().trim();
    const matchesSearch = !q || 
      s.name.toLowerCase().includes(q) ||
      s.phone.toLowerCase().includes(q) ||
      s.category.toLowerCase().includes(q);
    const matchesCategory = activeCategory.value === 'All' || s.category === activeCategory.value;
    return matchesSearch && matchesCategory;
  });
});

// Paginated suppliers
const currentSuppliers = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage;
  return filteredSuppliers.value.slice(start, start + itemsPerPage);
});

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(filteredSuppliers.value.length / itemsPerPage));
});

// Category counts
const categoryCounts = computed(() => {
  const counts: Record<string, number> = {};
  allCategories.value.forEach(cat => {
    if (cat === 'All') {
      counts[cat] = props.suppliers.length;
    } else {
      counts[cat] = props.suppliers.filter(s => s.category === cat).length;
    }
  });
  return counts;
});

// ─── Add Supplier ──────────────────────────────────────────────────────
const handleAddSupplierSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';
  const { name, phone, category } = newSupplierFields.value;
  if (!name) {
    formError.value = 'Supplier name is required!';
    return;
  }
  isSubmitting.value = true;
  try {
    await props.onAddSupplier!({ name, phone: phone || '', category: category || 'General' });
    newSupplierFields.value = { name: '', phone: '', category: 'Parts' };
    showAddForm.value = false;
    formSuccess.value = 'Supplier added successfully!';
    setTimeout(() => { formSuccess.value = ''; }, 3000);
    emit('refreshData');
  } catch (err: any) {
    formError.value = err.message || 'Failed to add supplier';
  } finally {
    isSubmitting.value = false;
  }
};

// ─── Edit Supplier ─────────────────────────────────────────────────────
const handleStartEditSupplier = (s: Supplier) => {
  editingSupplier.value = s;
  editSupplierFields.value = { name: s.name, phone: s.phone || '', category: s.category || 'General' };
  showEditForm.value = true;
  showAddForm.value = false;
  formError.value = '';
  formSuccess.value = '';
  window.scrollTo({ top: 0, behavior: 'smooth' });
};

const handleEditSupplierSubmit = async () => {
  formError.value = '';
  formSuccess.value = '';
  if (!editingSupplier.value) return;
  const { name, phone, category } = editSupplierFields.value;
  if (!name) {
    formError.value = 'Supplier name is required!';
    return;
  }
  isSubmitting.value = true;
  try {
    await props.onEditSupplier!(editingSupplier.value.id, { name, phone, category });
    editingSupplier.value = null;
    showEditForm.value = false;
    formSuccess.value = 'Supplier updated!';
    setTimeout(() => { formSuccess.value = ''; }, 3000);
    emit('refreshData');
  } catch (err: any) {
    formError.value = err.message || 'Failed to update supplier';
  } finally {
    isSubmitting.value = false;
  }
};

// ─── Delete Supplier ───────────────────────────────────────────────────
const handleDeleteSupplier = (s: Supplier) => {
  deleteConfirmSupplier.value = s;
};

const handleConfirmDeleteSupplier = async () => {
  if (!deleteConfirmSupplier.value) return;
  try {
    await props.onDeleteSupplier!(deleteConfirmSupplier.value.id);
    deleteConfirmSupplier.value = null;
    formSuccess.value = 'Supplier removed!';
    setTimeout(() => { formSuccess.value = ''; }, 3000);
    emit('refreshData');
  } catch (err: any) {
    formError.value = err.message || 'Failed to delete supplier';
    deleteConfirmSupplier.value = null;
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
            <div class="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center">
              <Users class="h-5 w-5 text-violet-600" />
            </div>
            Suppliers
          </h2>
          <p class="text-sm text-slate-500 mt-1">{{ suppliers.length }} supplier{{ suppliers.length !== 1 ? 's' : '' }} in your directory</p>
        </div>

        <!-- ACTION BUTTONS -->
        <div class="flex flex-wrap gap-3">
          <button 
            id="sup-btn-add"
            @click="showAddForm = !showAddForm; showEditForm = false; editingSupplier = null; formError = ''; formSuccess = ''"
            :class="['min-h-[40px] px-5 py-2.5 rounded-xl flex items-center gap-2 transition font-semibold text-sm cursor-pointer border',
              showAddForm 
                ? 'bg-violet-600 border-violet-600 text-white shadow-lg' 
                : 'bg-white text-violet-700 border-violet-200 hover:bg-violet-50 hover:border-violet-300 shadow-sm'
            ]"
          >
            <Plus class="h-4 w-4" />
            <span>Add Supplier</span>
          </button>
        </div>
      </div>

      <!-- Success message -->
      <div v-if="formSuccess && !showAddForm && !showEditForm" class="bg-emerald-50 p-4 rounded-xl border border-emerald-200 flex items-center gap-3 animate-fadeIn">
        <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
          <Check class="h-4 w-4 text-emerald-600" />
        </div>
        <p class="text-sm text-emerald-700 font-medium">{{ formSuccess }}</p>
        <button @click="formSuccess = ''" class="ml-auto text-emerald-400 hover:text-emerald-600 p-1 transition cursor-pointer">
          <X class="h-4 w-4" />
        </button>
      </div>

      <!-- ADD SUPPLIER FORM -->
      <div v-if="showAddForm" class="bg-white p-6 rounded-2xl border border-violet-200 shadow-sm space-y-5 animate-fadeIn text-left">
        <div class="flex justify-between items-center pb-4 border-b border-slate-100">
          <div>
            <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-violet-100 flex items-center justify-center">
                <Plus class="h-4 w-4 text-violet-600" />
              </div>
              Add New Supplier
            </h3>
            <p class="text-sm text-slate-500 mt-1 ml-10">Register a new vendor or supplier</p>
          </div>
          <button @click="showAddForm = false; formError = ''; formSuccess = ''" class="text-slate-400 hover:text-slate-600 cursor-pointer p-2 rounded-lg hover:bg-slate-100 transition">
            <X class="h-5 w-5" />
          </button>
        </div>

        <form @submit.prevent="handleAddSupplierSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Name *</label>
            <input type="text" placeholder="e.g. Michelin Distributors" v-model="newSupplierFields.name" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-violet-400 bg-white placeholder:text-slate-400" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Phone</label>
            <input type="text" placeholder="e.g. +91 99887 76655" v-model="newSupplierFields.phone" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-violet-400 bg-white font-mono placeholder:text-slate-400" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Category</label>
            <select v-model="newSupplierFields.category" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-violet-400 bg-white">
              <option v-for="cat in allCategories.filter(c => c !== 'All')" :key="cat" :value="cat">{{ cat }}</option>
              <option value="General">General</option>
            </select>
          </div>
          <div class="md:col-span-3 flex items-center gap-3">
            <p v-if="formError" class="text-sm text-rose-600 font-medium flex items-center gap-1"><AlertTriangle class="h-4 w-4" /> {{ formError }}</p>
            <div class="ml-auto flex gap-2">
              <button type="button" @click="showAddForm = false; formError = ''; formSuccess = ''" class="min-h-[40px] px-5 py-2.5 border border-slate-200 rounded-xl text-sm cursor-pointer hover:bg-slate-50 font-semibold transition">Cancel</button>
              <button type="submit" :disabled="isSubmitting" class="min-h-[40px] px-5 py-2.5 bg-violet-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-violet-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">
                <Plus class="h-4 w-4" /> {{ isSubmitting ? 'Adding...' : 'Add Supplier' }}
              </button>
            </div>
          </div>
        </form>
      </div>

      <!-- EDIT SUPPLIER FORM -->
      <div v-if="showEditForm && editingSupplier" class="bg-white p-6 rounded-2xl border border-blue-200 shadow-sm space-y-5 animate-fadeIn text-left">
        <div class="flex justify-between items-center pb-4 border-b border-slate-100">
          <div>
            <h3 class="font-bold text-slate-800 text-base flex items-center gap-2">
              <div class="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center">
                <Edit class="h-4 w-4 text-blue-600" />
              </div>
              Edit Supplier: {{ editingSupplier.name }}
            </h3>
            <p class="text-sm text-slate-500 mt-1 ml-10">Update supplier details</p>
          </div>
          <button @click="showEditForm = false; editingSupplier = null; formError = ''; formSuccess = ''" class="text-slate-400 hover:text-slate-600 cursor-pointer p-2 rounded-lg hover:bg-slate-100 transition">
            <X class="h-5 w-5" />
          </button>
        </div>

        <form @submit.prevent="handleEditSupplierSubmit" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Name *</label>
            <input type="text" v-model="editSupplierFields.name" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 bg-white" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Phone</label>
            <input type="text" v-model="editSupplierFields.phone" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 bg-white font-mono" />
          </div>
          <div class="space-y-2">
            <label class="text-sm font-medium text-slate-700 block">Category</label>
            <select v-model="editSupplierFields.category" class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 bg-white">
              <option v-for="cat in allCategories.filter(c => c !== 'All')" :key="cat" :value="cat">{{ cat }}</option>
              <option value="General">General</option>
            </select>
          </div>
          <div class="md:col-span-3 flex items-center gap-3">
            <p v-if="formError" class="text-sm text-rose-600 font-medium flex items-center gap-1"><AlertTriangle class="h-4 w-4" /> {{ formError }}</p>
            <div class="ml-auto flex gap-2">
              <button type="button" @click="showEditForm = false; editingSupplier = null; formError = ''; formSuccess = ''" class="min-h-[40px] px-5 py-2.5 border border-slate-200 rounded-xl text-sm cursor-pointer hover:bg-slate-50 font-semibold transition">Cancel</button>
              <button type="submit" :disabled="isSubmitting" class="min-h-[40px] px-5 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-blue-700 disabled:opacity-50 transition flex items-center gap-2 shadow-sm">
                <Check class="h-4 w-4" /> {{ isSubmitting ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </div>
        </form>
      </div>

      <!-- DELETE SUPPLIER CONFIRMATION -->
      <div v-if="deleteConfirmSupplier" class="bg-rose-50 p-6 rounded-2xl border border-rose-200 shadow-sm space-y-5 animate-fadeIn text-left">
        <div class="flex items-start gap-4">
          <div class="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center shrink-0">
            <AlertTriangle class="h-5 w-5 text-rose-600" />
          </div>
          <div class="flex-1">
            <h3 class="font-bold text-slate-800 text-base">Delete Supplier</h3>
            <p class="text-sm text-slate-600 mt-1">
              Remove supplier <strong class="text-rose-600">{{ deleteConfirmSupplier.name }}</strong>? This will not affect existing restock records.
            </p>
          </div>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button 
            type="button" 
            @click="deleteConfirmSupplier = null" 
            class="min-h-[40px] px-5 py-2.5 border border-slate-200 rounded-xl text-sm cursor-pointer hover:bg-slate-50 font-semibold transition"
          >
            Cancel
          </button>
          <button 
            type="button"
            @click="handleConfirmDeleteSupplier"
            class="min-h-[40px] px-5 py-2.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-sm font-semibold shadow-sm cursor-pointer transition flex items-center gap-2"
          >
            <Trash2 class="h-4 w-4" />
            Delete Supplier
          </button>
        </div>
      </div>

      <!-- SEARCH & FILTER BAR -->
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-4">
        <div class="flex flex-col md:flex-row gap-3 items-start md:items-center justify-between">
          <!-- Search -->
          <div class="relative w-full md:w-80">
            <Search class="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search suppliers by name, phone, or category..." 
              v-model="searchQuery" 
              class="w-full text-sm pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-violet-400" 
            />
          </div>

          <!-- Category Filter Pills -->
          <div class="flex flex-wrap gap-1.5">
            <button 
              v-for="cat in allCategories" 
              :key="cat"
              @click="activeCategory = cat"
              :class="['px-3 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer border',
                activeCategory === cat 
                  ? 'bg-violet-600 text-white border-violet-600 shadow-sm' 
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:border-slate-300'
              ]"
            >
              {{ cat }}
              <span v-if="categoryCounts[cat]" class="ml-1 opacity-70">({{ categoryCounts[cat] }})</span>
            </button>
          </div>
        </div>

        <!-- Results count -->
        <div class="flex items-center justify-between text-xs text-slate-500 pt-1">
          <span>
            Showing {{ currentSuppliers.length }} of {{ filteredSuppliers.length }} supplier{{ filteredSuppliers.length !== 1 ? 's' : '' }}
            <span v-if="searchQuery"> matching "{{ searchQuery }}"</span>
          </span>
        </div>
      </div>

      <!-- SUPPLIER LIST -->
      <div v-if="currentSuppliers.length > 0" class="divide-y divide-slate-100 border border-slate-200 rounded-2xl overflow-hidden bg-white shadow-sm">
        <div 
          v-for="s in currentSuppliers" 
          :key="s.id" 
          class="flex items-center gap-4 px-5 py-4 hover:bg-slate-50/50 transition"
        >
          <div class="w-10 h-10 rounded-xl bg-violet-50 flex items-center justify-center shrink-0">
            <Users class="h-5 w-5 text-violet-600" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-slate-800 text-sm truncate">{{ s.name }}</p>
            <div class="flex items-center gap-3 mt-1">
              <span v-if="s.phone" class="text-xs text-slate-400 flex items-center gap-1">
                <Phone class="h-3 w-3" /> {{ s.phone }}
              </span>
              <span class="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-medium">{{ s.category || 'General' }}</span>
            </div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <button 
              @click="handleStartEditSupplier(s)" 
              class="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition cursor-pointer" 
              title="Edit supplier"
            >
              <Edit class="h-4 w-4" />
            </button>
            <button 
              @click="handleDeleteSupplier(s)" 
              class="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer" 
              title="Delete supplier"
            >
              <Trash2 class="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="py-16 text-center bg-white rounded-2xl border border-slate-200 shadow-sm">
        <Users class="h-12 w-12 text-slate-300 mx-auto mb-4" />
        <p class="text-base font-semibold text-slate-500">No suppliers found</p>
        <p class="text-sm text-slate-400 mt-1">
          {{ searchQuery ? 'Try adjusting your search or filters' : 'Add your first supplier to get started' }}
        </p>
        <button 
          v-if="!searchQuery"
          @click="showAddForm = true; formError = ''; formSuccess = ''"
          class="mt-4 min-h-[40px] px-5 py-2.5 bg-violet-600 text-white rounded-xl text-sm font-semibold cursor-pointer hover:bg-violet-700 transition flex items-center gap-2 shadow-sm mx-auto"
        >
          <Plus class="h-4 w-4" />
          Add Supplier
        </button>
      </div>

      <!-- PAGINATION -->
      <div v-if="totalPages > 1" class="flex items-center justify-between bg-white p-4 rounded-2xl border border-slate-200 shadow-sm">
        <button 
          @click="currentPage = Math.max(1, currentPage - 1)" 
          :disabled="currentPage === 1"
          class="min-h-[36px] px-4 py-2 text-sm font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition"
        >
          Previous
        </button>
        <div class="flex items-center gap-1.5">
          <template v-for="page in totalPages" :key="page">
            <button 
              v-if="totalPages <= 7 || page === 1 || page === totalPages || Math.abs(page - currentPage) <= 1"
              @click="currentPage = page"
              :class="['min-w-[36px] min-h-[36px] px-2 py-1 text-sm font-semibold rounded-lg transition cursor-pointer border',
                currentPage === page 
                  ? 'bg-violet-600 text-white border-violet-600 shadow-sm' 
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 hover:border-slate-300'
              ]"
            >
              {{ page }}
            </button>
            <span v-else-if="Math.abs(page - currentPage) === 2" class="text-slate-400 px-1">...</span>
          </template>
        </div>
        <button 
          @click="currentPage = Math.min(totalPages, currentPage + 1)" 
          :disabled="currentPage === totalPages"
          class="min-h-[36px] px-4 py-2 text-sm font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition"
        >
          Next
        </button>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* Animation for fade-in */
.animate-fadeIn {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Custom scrollbar for supplier list */
.divide-y::-webkit-scrollbar {
  width: 6px;
}
.divide-y::-webkit-scrollbar-track {
  background: transparent;
}
.divide-y::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.divide-y::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>