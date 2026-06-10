<script setup lang="ts">
import { ref, watch } from 'vue';
import { X, Plus, Trash2, Tag, Target, TrendingUp } from 'lucide-vue-next';
import { 
  expenseCategories, 
  savingCategories,
  incomeCategories,
  saveCustomCategories, 
  DEFAULT_EXPENSE_CATEGORIES, 
  DEFAULT_SAVING_CATEGORIES,
  DEFAULT_INCOME_CATEGORIES
} from '../utils/categories';

const props = defineProps<{
  isOpen: boolean;
  userId: string;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const activeTab = ref<'expenses' | 'savings' | 'income'>('expenses');
const localExpenseCategories = ref<string[]>([]);
const localSavingCategories = ref<string[]>([]);
const localIncomeCategories = ref<string[]>([]);
const newCategoryName = ref('');
const isSaving = ref(false);

watch(() => props.isOpen, (open) => {
  if (open) {
    localExpenseCategories.value = [...expenseCategories.value];
    localSavingCategories.value = [...savingCategories.value];
    localIncomeCategories.value = [...incomeCategories.value];
    newCategoryName.value = '';
  }
}, { immediate: true });

const handleAddCategory = () => {
  const name = newCategoryName.value.trim();
  if (!name) return;
  
  if (activeTab.value === 'expenses') {
    if (!localExpenseCategories.value.includes(name)) {
      localExpenseCategories.value.push(name);
    }
  } else if (activeTab.value === 'savings') {
    if (!localSavingCategories.value.includes(name)) {
      localSavingCategories.value.push(name);
    }
  } else {
    if (!localIncomeCategories.value.includes(name)) {
      localIncomeCategories.value.push(name);
    }
  }
  newCategoryName.value = '';
};

const handleRemoveCategory = (cat: string) => {
  if (cat.toLowerCase() === 'other') return; // protect standard fallback
  
  if (activeTab.value === 'expenses') {
    localExpenseCategories.value = localExpenseCategories.value.filter(c => c !== cat);
  } else if (activeTab.value === 'savings') {
    localSavingCategories.value = localSavingCategories.value.filter(c => c !== cat);
  } else {
    localIncomeCategories.value = localIncomeCategories.value.filter(c => c !== cat);
  }
};

const handleResetToDefaults = () => {
  if (activeTab.value === 'expenses') {
    localExpenseCategories.value = [...DEFAULT_EXPENSE_CATEGORIES];
  } else if (activeTab.value === 'savings') {
    localSavingCategories.value = [...DEFAULT_SAVING_CATEGORIES];
  } else {
    localIncomeCategories.value = [...DEFAULT_INCOME_CATEGORIES];
  }
};

const handleSave = async () => {
  if (!props.userId) return;
  isSaving.value = true;
  try {
    // Ensure "Other" remains in the lists if not present
    if (!localExpenseCategories.value.includes('Other')) {
      localExpenseCategories.value.push('Other');
    }
    if (!localSavingCategories.value.includes('Other')) {
      localSavingCategories.value.push('Other');
    }
    if (!localIncomeCategories.value.includes('Other')) {
      localIncomeCategories.value.push('Other');
    }
    
    await saveCustomCategories(props.userId, localExpenseCategories.value, localSavingCategories.value, localIncomeCategories.value);
    emit('close');
  } catch (error) {
    console.error('Failed to save custom categories:', error);
  } finally {
    isSaving.value = false;
  }
};
</script>

<template>
  <transition name="fade">
    <div v-if="isOpen" class="fixed inset-0 z-[80] flex items-center justify-center p-4">
      <div @click="$emit('close')" class="absolute inset-0 bg-zinc-950/60 backdrop-blur-sm" />
      
      <div class="relative w-full max-w-lg bg-white dark:bg-[#0d151a] border border-zinc-200 dark:border-zinc-800 rounded-[32px] shadow-2xl overflow-hidden outline-none z-10 transition-all flex flex-col max-h-[85vh]">
        
        <!-- Header -->
        <div class="p-8 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between shrink-0">
          <div>
            <h3 class="text-2xl font-bold tracking-tight text-zinc-900 dark:text-white font-display">Category Manager</h3>
            <p class="text-xs text-zinc-500 mt-1">Configure custom categories selected across the system</p>
          </div>
          <button @click="$emit('close')" class="p-2 hover:bg-zinc-100 dark:hover:bg-white/10 rounded-xl transition-colors cursor-pointer outline-none">
            <X class="w-5 h-5 text-zinc-500" />
          </button>
        </div>

        <!-- Tabs -->
        <div class="px-8 pt-4 pb-2 bg-zinc-50/50 dark:bg-zinc-950/20 flex gap-2 border-b border-zinc-100 dark:border-zinc-805 shrink-0 overflow-x-auto custom-scrollbar">
          <button
            @click="activeTab = 'expenses'"
            :class="`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold font-display transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'expenses'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/10'
                : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'
            }`"
          >
            <Tag class="w-3.5 h-3.5" />
            Budget Expenses
          </button>
          <button
            @click="activeTab = 'savings'"
            :class="`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold font-display transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'savings'
                ? 'bg-teal-600 text-white shadow-md shadow-teal-600/10'
                : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'
            }`"
          >
            <Target class="w-3.5 h-3.5" />
            Savings Goals
          </button>
          <button
            @click="activeTab = 'income'"
            :class="`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold font-display transition-all cursor-pointer whitespace-nowrap ${
              activeTab === 'income'
                ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/10'
                : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-white/5 hover:text-zinc-900 dark:hover:text-white'
            }`"
          >
            <TrendingUp class="w-3.5 h-3.5" />
            Income Sources
          </button>
        </div>

        <!-- Tab Content -->
        <div class="flex-1 overflow-y-auto p-8 custom-scrollbar">
          <!-- Add Category Form -->
          <div class="mb-6">
            <label class="block text-[10px] font-bold text-zinc-500 dark:text-zinc-400 uppercase tracking-widest mb-2 font-display">
              Add New {{ activeTab === 'expenses' ? 'Budget' : activeTab === 'savings' ? 'Savings' : 'Income' }} Category
            </label>
            <div class="flex gap-2">
              <input
                type="text"
                v-model="newCategoryName"
                @keydown.enter.prevent="handleAddCategory"
                placeholder="e.g., Subscriptions, Kids, Freelance, Side Hustle"
                class="flex-1 px-4 py-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 dark:focus:border-teal-500/50 transition-all font-medium text-zinc-900 dark:text-white placeholder:text-zinc-400 dark:placeholder:text-zinc-600 text-sm"
              />
              <button
                @click="handleAddCategory"
                :class="`px-5 py-3 rounded-xl font-bold text-sm text-white transition-all active:scale-95 cursor-pointer flex items-center justify-center gap-1.5 ${
                  activeTab === 'expenses' ? 'bg-indigo-600 hover:bg-indigo-700' : activeTab === 'savings' ? 'bg-teal-600 hover:bg-teal-700' : 'bg-emerald-600 hover:bg-emerald-700'
                }`"
              >
                <Plus class="w-4 h-4" />
                Add
              </button>
            </div>
          </div>

          <!-- Category list -->
          <div>
            <div class="flex items-center justify-between mb-3 text-[10px] font-bold text-zinc-400 dark:text-zinc-500 uppercase tracking-widest">
              <span>Active Categories</span>
              <button 
                @click="handleResetToDefaults"
                class="text-[10px] lowercase font-semibold text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 underline cursor-pointer"
              >
                Reset to defaults
              </button>
            </div>
            
            <div class="space-y-1.5">
              <div 
                v-for="cat in (activeTab === 'expenses' ? localExpenseCategories : activeTab === 'savings' ? localSavingCategories : localIncomeCategories)" 
                :key="cat"
                class="flex items-center justify-between px-4 py-3 bg-zinc-50 dark:bg-white/5 border border-zinc-150/50 dark:border-white/5 rounded-xl text-sm font-medium text-zinc-950 dark:text-zinc-200"
              >
                <span>{{ cat }}</span>
                <button
                  v-if="cat.toLowerCase() !== 'other'"
                  @click="handleRemoveCategory(cat)"
                  class="p-1.5 hover:bg-red-50 dark:hover:bg-red-500/10 hover:text-red-500 rounded-lg text-zinc-400 transition-colors cursor-pointer focus:outline-none"
                  title="Remove category"
                >
                  <Trash2 class="w-4 h-4" />
                </button>
                <span v-else class="text-[10px] font-bold uppercase tracking-wider text-zinc-400 font-mono px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 rounded-md">
                  Fallback
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Footer actions -->
        <div class="p-8 border-t border-zinc-100 dark:border-zinc-800 flex gap-4 bg-zinc-50/50 dark:bg-zinc-950/20 shrink-0">
          <button
            @click="$emit('close')"
            class="flex-1 py-3.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 rounded-2xl font-bold hover:bg-zinc-200 dark:hover:bg-zinc-750 transition-all active:scale-[0.98] cursor-pointer"
          >
            Cancel
          </button>
          <button
            @click="handleSave"
            :disabled="isSaving"
            :class="`flex-1 py-3.5 rounded-2xl font-bold text-white transition-all active:scale-[0.98] cursor-pointer shadow-lg ${
              activeTab === 'expenses' 
                ? 'bg-indigo-600 hover:bg-indigo-700 shadow-indigo-600/10' 
                : activeTab === 'savings'
                ? 'bg-teal-600 hover:bg-teal-700 shadow-teal-600/10'
                : 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-500/10'
            }`"
          >
            {{ isSaving ? 'Saving Changes...' : 'Save Category Matrix' }}
          </button>
        </div>

      </div>
    </div>
  </transition>
</template>
