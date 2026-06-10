<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { db } from '../firebase';
import { collection, getDocs, query } from 'firebase/firestore';
import { 
  FolderLock, 
  Plus, 
  FileText, 
  HardDrive, 
  Link2, 
  ChevronRight,
  ShieldCheck,
  FolderPlus
} from 'lucide-vue-next';
import { type Group, type VaultDocument } from '../types';

const props = defineProps<{
  user: any;
  groups: Group[];
}>();

const emit = defineEmits<{
  (e: 'selectGroup', id: string): void;
}>();

const loading = ref(true);
const allDocuments = ref<VaultDocument[]>([]);
const groupDocsMap = ref<Map<string, VaultDocument[]>>(new Map());

// Fetch documents for all cabinets belonging to the document_vault service
onMounted(async () => {
  try {
    const docList: VaultDocument[] = [];
    const tempMap = new Map<string, VaultDocument[]>();

    for (const group of props.groups) {
      const q = query(collection(db, 'groups', group.id, 'documents'));
      const snapshot = await getDocs(q);
      const list = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      } as VaultDocument));
      
      docList.push(...list);
      tempMap.set(group.id, list);
    }

    allDocuments.value = docList;
    groupDocsMap.value = tempMap;
  } catch (error) {
    console.error("Error loading document vault overview data:", error);
  } finally {
    loading.value = false;
  }
});

// Calculate metrics
const totalDocsCount = computed(() => {
  return allDocuments.value.length;
});

const totalStorageSize = computed(() => {
  const bytes = allDocuments.value.reduce((sum, d) => sum + (d.fileSize || 0), 0);
  if (bytes === 0) return '0 KB';
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
});

const linkedDocsCount = computed(() => {
  return allDocuments.value.filter(d => d.linkedService && d.linkedEntityId).length;
});

const standaloneDocsCount = computed(() => {
  return allDocuments.value.filter(d => !d.linkedService).length;
});

const openCreateModal = () => {
  if ((window as any).openCreateGroupModal) {
    (window as any).openCreateGroupModal();
  }
};
</script>

<template>
  <div class="space-y-8" id="document-vault-hub-container">
    <!-- Header with title & Action Button -->
    <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 text-left">
      <div>
        <h1 class="text-3xl font-black text-zinc-950 dark:text-white tracking-tight flex items-center gap-2.5 font-display">
          <FolderLock class="w-8 h-8 text-indigo-500" />
          Document Vault
        </h1>
        <p class="text-xs text-zinc-500 dark:text-zinc-400 font-medium mt-1">
          Secure offline-first repository for banking statement PDFs, lease deeds, invoices, and payment receipts.
        </p>
      </div>

      <button 
        @click="openCreateModal"
        class="inline-flex items-center gap-2 px-5 py-3.5 bg-gradient-to-br from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-2xl font-bold text-xs transition-all shadow-xl shadow-indigo-500/10 hover:shadow-indigo-500/20 cursor-pointer"
      >
        <FolderPlus class="w-4 h-4" />
        Create Cabinet Group
      </button>
    </div>

    <!-- Active Statistics Dashboard Grid -->
    <div v-if="!loading" class="grid grid-cols-1 md:grid-cols-3 gap-6" id="vault-stats-grid">
      <!-- Total files -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm text-left">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <FileText class="w-24 h-24 text-indigo-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">Archived Documents</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-3xl font-black tracking-tight text-indigo-600 dark:text-indigo-400 font-mono">
            {{ totalDocsCount }}
          </span>
          <span class="text-xs font-bold text-zinc-400">files</span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <ShieldCheck class="w-4 h-4 text-indigo-500" />
          <span>{{ standaloneDocsCount }} Standalone (unlinked) sheets</span>
        </div>
      </div>

      <!-- Allocated Storage space -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm text-left">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <HardDrive class="w-24 h-24 text-teal-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">Durable Storage Used</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-3xl font-black tracking-tight text-teal-600 dark:text-teal-400 font-mono">
            {{ totalStorageSize }}
          </span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <HardDrive class="w-4 h-4 text-teal-500" />
          <span>Secured directly in local SQLite Ledger</span>
        </div>
      </div>

      <!-- Linked Attachments count -->
      <div class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] relative overflow-hidden shadow-sm text-left">
        <div class="absolute right-4 top-4 opacity-5 pointer-events-none">
          <Link2 class="w-24 h-24 text-pink-500" />
        </div>
        <p class="text-[10px] font-bold text-zinc-400 uppercase tracking-wider mb-2 font-display">Linked Attachments</p>
        <div class="flex items-baseline gap-2 mb-4">
          <span class="text-3xl font-black tracking-tight text-pink-600 dark:text-pink-400 font-mono">
            {{ linkedDocsCount }}
          </span>
          <span class="text-xs font-bold text-zinc-400">attachments</span>
        </div>
        <div class="flex items-center gap-2 text-xs text-zinc-505 dark:text-zinc-300 font-medium pt-3 border-t border-zinc-100 dark:border-white/5">
          <Link2 class="w-4 h-4 text-pink-500" />
          <span>Synchronized with active services</span>
        </div>
      </div>
    </div>

    <!-- Loading Spin Grid -->
    <div v-if="loading" class="flex items-center justify-center py-24">
      <div class="w-10 h-10 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    </div>

    <!-- Active Cabinets List Grid -->
    <template v-else>
      <div v-if="groups.length === 0" class="py-24 text-center text-zinc-550 bg-white dark:bg-[#0b1219]/60 border border-zinc-250 dark:border-white/5 rounded-[32px] shadow-sm">
        <FolderLock class="w-16 h-16 mx-auto text-zinc-300 dark:text-zinc-705 mb-5 animate-pulse" />
        <h3 class="font-extrabold text-zinc-950 dark:text-white text-lg tracking-tight mb-2 font-display">Set Up Document Vault Cabinets</h3>
        <p class="text-xs text-zinc-500 dark:text-zinc-400 max-w-sm mx-auto leading-relaxed mb-6">
          Create structured Cabinets/Folders (e.g. "Real Estate Deeds", "Corporate Tax Receipts", "Active Invoices") to organize and secure documents.
        </p>
        <button 
          @click="openCreateModal"
          class="inline-flex items-center gap-2 px-5 py-3.5 bg-zinc-950 dark:bg-white text-white dark:text-zinc-950 hover:bg-zinc-900 dark:hover:bg-zinc-100 rounded-xl font-bold text-xs transition-all shadow-md cursor-pointer"
        >
          <Plus class="w-4 h-4" />
          Initialize First Cabinet
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="vault-cabinets-list">
        <div 
          v-for="group in groups" 
          :key="group.id" 
          @click="emit('selectGroup', group.id)"
          class="p-6 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] hover:border-indigo-500 dark:hover:border-indigo-500/40 transition-all duration-300 shadow-sm cursor-pointer group flex flex-col justify-between h-[190px]"
        >
          <div class="text-left">
            <div class="flex items-center justify-between mb-4">
              <span class="text-[9px] font-black uppercase tracking-wider bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 px-3 py-1 rounded-full">
                Vault Cabinet
              </span>
              <ChevronRight class="w-4 h-4 text-zinc-400 group-hover:text-indigo-500 transition-colors" />
            </div>

            <h3 class="text-base font-black text-zinc-950 dark:text-white group-hover:text-indigo-500 transition-colors tracking-tight line-clamp-1 font-display">
              {{ group.name }}
            </h3>
            <p v-if="group.description" class="text-[11px] text-zinc-400 dark:text-zinc-500 line-clamp-2 mt-1 leading-relaxed">
              {{ group.description }}
            </p>
            <p v-else class="text-[11px] text-zinc-400 dark:text-zinc-650 italic mt-1">
              General document archive.
            </p>
          </div>

          <div class="pt-4 border-t border-zinc-100 dark:border-white/5 flex items-center justify-between text-xs text-zinc-400">
            <span class="font-medium flex items-center gap-1">
              <FileText class="w-3.5 h-3.5" />
              Documents Count
            </span>
            <span class="font-bold text-zinc-950 dark:text-white font-mono">
              {{ groupDocsMap.get(group.id)?.length || 0 }} files
            </span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
