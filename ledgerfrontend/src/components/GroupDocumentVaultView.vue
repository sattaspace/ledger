<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { db } from '../firebase';
import { 
  collection, 
  doc, 
  setDoc,
  deleteDoc, 
  onSnapshot, 
  query, 
  orderBy, 
  Timestamp, 
  getDoc
} from 'firebase/firestore';
import { 
  ArrowLeft, 
  Plus, 
  Trash2, 
  CheckCircle, 
  Calendar, 
  User, 
  Link2, 
  Upload, 
  FileText, 
  File, 
  Eye, 
  Download, 
  AlertCircle,
  HelpCircle,
  FolderOpen,
  Check,
  Briefcase,
  ExternalLink,
  ShieldCheck,
  Building,
  KeyRound,
  PiggyBank
} from 'lucide-vue-next';
import { type Group, type VaultDocument } from '../types';

const props = defineProps<{
  groupId: string;
  user: any;
}>();

const emit = defineEmits<{
  (e: 'back'): void;
}>();

const loading = ref(true);
const group = ref<Group | null>(null);
const documents = ref<VaultDocument[]>([]);

// Reference collections for cross-linking
const accountsList = ref<any[]>([]);
const loansList = ref<any[]>([]);
const mortgagesList = ref<any[]>([]);
const rentsList = ref<any[]>([]);
const savingsList = ref<any[]>([]);

// Upload Form State
const isUploadOpen = ref(false);
const selectedFile = ref<File | null>(null);
const fileBase64 = ref<string>('');
const uploadProgress = ref(0);
const docName = ref('');
const docDesc = ref('');

// Linkage dropdown selections
const linkService = ref<'accounts' | 'loans_debts' | 'mortgages' | 'rent' | 'savings' | null>(null);
const linkEntityId = ref('');

// Detail Modal State
const activeDocPreview = ref<VaultDocument | null>(null);

// Drag & Drop State
const isDragging = ref(false);

const allowedFileTypes = [
  'image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml',
  'text/plain', 'text/html', 'text/css', 'application/json', 'application/pdf'
];

onMounted(async () => {
  try {
    // 1. Fetch Cabinet Metadata
    const gDoc = await getDoc(doc(db, 'groups', props.groupId));
    if (gDoc.exists()) {
      group.value = { id: gDoc.id, ...gDoc.data() } as Group;
    }

    // 2. Fetch Reference Entities for the linkages
    onSnapshot(collection(db, 'groups'), async (snap) => {
      const allGroups = snap.docs.map(d => ({ id: d.id, ...d.data() } as Group));
      
      // Filter Accounts
      accountsList.value = allGroups.filter(g => g.service === 'accounts');

      // Async fetch list for Rent leases, Loans, Mortgages, Savings goals across all corresponding groups
      const rentAccumulator: any[] = [];
      const loansAccumulator: any[] = [];
      const mortgagesAccumulator: any[] = [];
      const savingsAccumulator: any[] = [];

      for (const g of allGroups) {
        if (g.service === 'rent') {
          const rq = query(collection(db, 'groups', g.id, 'rents'));
          const rSnap = await getDocsDirect(rq);
          rentAccumulator.push(...rSnap.map(item => ({ ...item, groupName: g.name })));
        }
        if (g.service === 'loans_debts') {
          const lq = query(collection(db, 'groups', g.id, 'loans_debts'));
          const lSnap = await getDocsDirect(lq);
          loansAccumulator.push(...lSnap.map(item => ({ ...item, groupName: g.name })));
        }
        if (g.service === 'mortgages') {
          const mq = query(collection(db, 'groups', g.id, 'mortgages'));
          const mSnap = await getDocsDirect(mq);
          mortgagesAccumulator.push(...mSnap.map(item => ({ ...item, groupName: g.name })));
        }
        if (g.service === 'savings') {
          const sq = query(collection(db, 'groups', g.id, 'saving_goals'));
          const sSnap = await getDocsDirect(sq);
          savingsAccumulator.push(...sSnap.map(item => ({ ...item, groupName: g.name })));
        }
      }

      rentsList.value = rentAccumulator;
      loansList.value = loansAccumulator;
      mortgagesList.value = mortgagesAccumulator;
      savingsList.value = savingsAccumulator;
    });

    // 3. Listen to Documents subcollection
    const docQuery = query(collection(db, 'groups', props.groupId, 'documents'), orderBy('createdAt', 'desc'));
    onSnapshot(docQuery, (snapshot) => {
      documents.value = snapshot.docs.map(d => ({
        id: d.id,
        ... d.data()
      } as VaultDocument));
      loading.value = false;
    });

  } catch (error) {
    console.error("Error starting Document Cabinet listener:", error);
    loading.value = false;
  }
});

// Helper wrapper to get docs synchronously/safely
async function getDocsDirect(q: any) {
  try {
    const s = await getDocs(q);
    return s.docs.map(d => ({ id: d.id, ...d.data() }));
  } catch (e) {
    return [];
  }
}

// Format size helper
const formatSize = (bytes: number) => {
  if (!bytes) return '0 Bytes';
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
};

// Target entities options list based on selected linkage type
const linkableEntities = computed(() => {
  if (!linkService.value) return [];
  if (linkService.value === 'accounts') return accountsList.value;
  if (linkService.value === 'rent') return rentsList.value;
  if (linkService.value === 'loans_debts') return loansList.value;
  if (linkService.value === 'mortgages') return mortgagesList.value;
  if (linkService.value === 'savings') return savingsList.value;
  return [];
});

const getEntityLabel = (entity: any) => {
  if (linkService.value === 'accounts') {
    return `${entity.name} (${entity.bankName || 'Card'})`;
  }
  if (linkService.value === 'rent') {
    return `${entity.propertyName} (Tenant/Landlord: ${entity.tenantOrLandlord})`;
  }
  if (linkService.value === 'loans_debts') {
    return `${entity.type === 'give' ? 'Leased to' : 'Owed to'}: ${entity.personName} (${entity.currencyCode} ${entity.amount})`;
  }
  if (linkService.value === 'mortgages') {
    return `Property: ${entity.collateralName} (Principal: ${entity.amount})`;
  }
  if (linkService.value === 'savings') {
    return `Saving Goal: ${entity.name} (Target: ${entity.targetAmount})`;
  }
  return entity.name || entity.id;
};

// Drag & Drop handlers
const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = true;
};

const handleDragLeave = () => {
  isDragging.value = false;
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = false;
  if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
    processFile(e.dataTransfer.files[0]);
  }
};

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    processFile(target.files[0]);
  }
};

const processFile = (file: File) => {
  if (file.size > 3 * 1024 * 1024) {
    alert("File is too large! Maximum limit is 3MB to preserve durable SQLite response speeds.");
    return;
  }

  selectedFile.value = file;
  docName.value = file.name;

  const reader = new FileReader();
  reader.onload = () => {
    fileBase64.value = reader.result as string;
  };
  reader.readAsDataURL(file);
};

// Reset Upload Modal Fields
const resetUploadForm = () => {
  selectedFile.value = null;
  fileBase64.value = '';
  docName.value = '';
  docDesc.value = '';
  linkService.value = null;
  linkEntityId.value = '';
  isUploadOpen.value = false;
};

// Create Document Entry
const handleUploadDocument = async () => {
  if (!docName.value.trim() || !fileBase64.value) {
    alert("Please drag or select a valid document first.");
    return;
  }

  try {
    const docId = crypto.randomUUID();
    const payload: VaultDocument = {
      id: docId,
      groupId: props.groupId,
      name: docName.value.trim(),
      fileSize: selectedFile.value?.size || 0,
      fileType: selectedFile.value?.type || 'application/octet-stream',
      description: docDesc.value.trim() || undefined,
      fileData: fileBase64.value,
      createdAt: Timestamp.now(),
      createdBy: props.user.uid
    };

    if (linkService.value && linkEntityId.value) {
      payload.linkedService = linkService.value;
      payload.linkedEntityId = linkEntityId.value;
    }

    await setDoc(doc(db, 'groups', props.groupId, 'documents', docId), payload);
    resetUploadForm();
  } catch (error) {
    console.error("Error creating Document entry:", error);
    alert("Could not append file records.");
  }
};

// Document removal
const handleDeleteDocument = async (d: VaultDocument) => {
  const confirmDel = confirm(`Are you sure you want to permanently erase "${d.name}"? This deletes the archived file contents.`);
  if (!confirmDel) return;

  try {
    await deleteDoc(doc(db, 'groups', props.groupId, 'documents', d.id));
  } catch (error) {
    console.error("Error deleting document record:", error);
  }
};

// Download helper
const triggerFileDownload = (d: VaultDocument) => {
  if (!d.fileData) return;
  const link = document.createElement('a');
  link.href = d.fileData;
  link.download = d.name;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// Link resolution labels
const getLinkedLabelText = (d: VaultDocument) => {
  if (!d.linkedService || !d.linkedEntityId) return '';
  
  if (d.linkedService === 'accounts') {
    const acc = accountsList.value.find(a => a.id === d.linkedEntityId);
    return acc ? `Account: ${acc.name}` : 'Linked Account';
  }
  if (d.linkedService === 'rent') {
    const r = rentsList.value.find(item => item.id === d.linkedEntityId);
    return r ? `Rent Unit: ${r.propertyName}` : 'Linked Lease agreement';
  }
  if (d.linkedService === 'loans_debts') {
    const l = loansList.value.find(item => item.id === d.linkedEntityId);
    return l ? `Loan with: ${l.personName}` : 'Linked Loan tracker';
  }
  if (d.linkedService === 'mortgages') {
    const m = mortgagesList.value.find(item => item.id === d.linkedEntityId);
    return m ? `Mortgage: ${m.collateralName}` : 'Linked Mortgage';
  }
  if (d.linkedService === 'savings') {
    const s = savingsList.value.find(item => item.id === d.linkedEntityId);
    return s ? `Saving Goal: ${s.name}` : 'Linked Saving Goal';
  }
  return 'Linked attachment';
};

const getServiceIcon = (service: string) => {
  if (service === 'accounts') return CreditCard;
  if (service === 'rent') return KeyRound;
  if (service === 'loans_debts') return User;
  if (service === 'mortgages') return Building;
  if (service === 'savings') return PiggyBank;
  return Link2;
};
</script>

<template>
  <div class="space-y-8" id="group-document-view-container">
    <!-- Breadcrumb back link -->
    <button 
      @click="emit('back')"
      class="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-950 dark:hover:text-white text-xs font-black select-none cursor-pointer bg-transparent border-none"
    >
      <ArrowLeft class="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
      Back to Document Vault Hub
    </button>

    <!-- Header Section card -->
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-5 bg-white dark:bg-[#0c141d]/70 p-8 border border-zinc-200 dark:border-white/10 rounded-[32px] shadow-sm text-left">
      <div>
        <div class="flex items-center gap-3 mb-2.5">
          <span class="px-3 py-1 bg-indigo-50 dark:bg-indigo-500/10 text-indigo-650 dark:text-indigo-400 text-[10px] uppercase font-black tracking-widest rounded-full">
            DURABLE CLOUD ARCHIVES
          </span>
          <span class="text-zinc-400 font-mono text-[11px] font-bold">
            Cabinet ID: {{ group?.id }}
          </span>
        </div>
        <h2 class="text-3xl font-black text-zinc-950 dark:text-white tracking-tight font-display mb-1">
          Cabinet: {{ group?.name }}
        </h2>
        <p class="text-xs text-zinc-500 leading-relaxed max-w-2xl">
          {{ group?.description || 'A secure folder room containing PDF invoices, banking sheets, tax reports, and transaction attachments.' }}
        </p>
      </div>

      <button 
        @click="isUploadOpen = true"
        class="px-5 py-4 bg-gradient-to-br from-indigo-600 to-indigo-750 text-white rounded-2xl font-bold text-xs transition-colors shadow-lg shadow-indigo-500/15 flex items-center justify-center gap-2 shrink-0 cursor-pointer border-none"
      >
        <Upload class="w-4 h-4 shrink-0" />
        Archive Document
      </button>
    </div>

    <!-- Active Documents Grid -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
    </div>

    <div v-else class="space-y-4">
      <div v-if="documents.length === 0" class="py-20 text-center text-zinc-550 bg-white dark:bg-[#0b1219]/60 border border-zinc-200 dark:border-white/5 rounded-[32px] shadow-sm">
        <FolderOpen class="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-700 mb-4" />
        <h3 class="font-bold text-zinc-950 dark:text-white tracking-tight mb-2 font-display">This Cabinet is Empty</h3>
        <p class="text-xs text-zinc-500 max-w-sm mx-auto leading-relaxed mb-6">
          No files has been archived inside this folder room yet. Click "Archive Document" to upload your first bank statement or receipt file.
        </p>

        <button 
          @click="isUploadOpen = true"
          class="inline-flex items-center gap-2 px-5 py-3.5 bg-indigo-600 text-white rounded-xl font-bold text-xs transition-all shadow-md cursor-pointer border-none"
        >
          <Upload class="w-4 h-4" />
          Archive First Document
        </button>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="cabinet-documents-grid-view">
        <div 
          v-for="d in documents" 
          :key="d.id" 
          class="p-5 bg-white dark:bg-[#0c141d]/85 border border-zinc-200 dark:border-white/10 rounded-[28px] shadow-sm flex flex-col justify-between text-left group"
        >
          <!-- Document details -->
          <div>
            <div class="flex items-start justify-between gap-2 mb-3">
              <!-- Inline icon according to mime-type -->
              <div 
                v-if="d.fileType && d.fileType.startsWith('image/')"
                class="w-12 h-12 rounded-xl border border-zinc-200/50 bg-zinc-50 dark:bg-zinc-900 overflow-hidden flex items-center justify-center shrink-0 cursor-pointer"
                @click="activeDocPreview = d"
                title="View image thumbnail"
              >
                <img :src="d.fileData" class="w-full h-full object-cover" />
              </div>
              <div 
                v-else
                class="w-12 h-12 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center shrink-0"
              >
                <FileText class="w-5 h-5" />
              </div>

              <!-- Secondary delete action button -->
              <button 
                @click="handleDeleteDocument(d)"
                class="p-1.5 text-zinc-400 hover:text-rose-500 dark:hover:bg-rose-500/10 rounded-lg transition-colors cursor-pointer bg-transparent border-none"
                title="Erase Document record"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>

            <!-- Name of the document -->
            <h4 class="font-bold text-sm text-zinc-950 dark:text-white line-clamp-1 group-hover:text-indigo-500 dark:group-hover:text-indigo-400 transition-colors">
              {{ d.name }}
            </h4>
            
            <!-- Metadata line -->
            <p class="text-[10px] text-zinc-450 dark:text-zinc-500 font-mono mt-0.5">
              {{ formatSize(d.fileSize) }} • {{ d.fileType?.split('/')[1]?.toUpperCase() || 'DOCUMENT' }}
            </p>

            <p v-if="d.description" class="text-xs text-zinc-500 dark:text-zinc-400 mt-2 line-clamp-2">
              {{ d.description }}
            </p>

            <!-- Linked Indicators -->
            <div v-if="d.linkedService && d.linkedEntityId" class="mt-3.5 pt-3 border-t border-zinc-100 dark:border-white/5">
              <span class="inline-flex items-center gap-1.5 px-3 py-1 bg-pink-50 dark:bg-pink-500/10 text-pink-650 dark:text-pink-400 rounded-lg text-[9.5px] font-black tracking-wide shrink-0">
                <component :is="getServiceIcon(d.linkedService)" class="w-3" />
                {{ getLinkedLabelText(d) }}
              </span>
            </div>
            <div v-else class="mt-3.5 pt-3 border-t border-zinc-100 dark:border-white/5">
              <span class="text-[9.5px] font-medium text-zinc-400 bg-zinc-50 dark:bg-white/5 px-2.5 py-1 rounded-lg">
                Standalone Safe document
              </span>
            </div>
          </div>

          <!-- Bottom Action Controls -->
          <div class="mt-5 flex gap-2">
            <button 
              @click="activeDocPreview = d"
              class="flex-1 py-2.5 border border-zinc-200 dark:border-white/10 hover:bg-zinc-100 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-400 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer bg-transparent"
            >
              <Eye class="w-3.5 h-3.5" />
              View file
            </button>
            <button 
              @click="triggerFileDownload(d)"
              class="px-4 py-2.5 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-750 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer border-none"
              title="Download Original file"
            >
              <Download class="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Upload Attachment Modal Overlay -->
    <transition name="fade">
      <div v-if="isUploadOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Overlay background shadow backdrop -->
        <div class="absolute inset-0 bg-zinc-950/70 backdrop-blur-sm cursor-pointer" @click="resetUploadForm" />
        
        <div class="bg-white dark:bg-[#0c141d] border border-zinc-200 dark:border-white/10 rounded-3xl overflow-hidden shadow-2xl relative w-full max-w-lg z-10 max-h-[90vh] flex flex-col">
          <div class="p-6 border-b border-zinc-100 dark:border-white/5 flex items-center justify-between text-left">
            <div>
              <h3 class="text-lg font-black text-zinc-950 dark:text-white leading-tight">Archive Document</h3>
              <p class="text-[10px] text-zinc-500 mt-1 leading-relaxed">Secure transaction records, agreements, or identification credentials</p>
            </div>
            <button @click="resetUploadForm" class="text-zinc-400 hover:text-white cursor-pointer select-none font-bold bg-transparent border-none">×</button>
          </div>

          <div class="p-6 space-y-4 overflow-y-auto custom-scrollbar text-left flex-1">
            
            <!-- Drag & Drop container area -->
            <div 
              @dragover="handleDragOver"
              @dragleave="handleDragLeave"
              @drop="handleDrop"
              :class="`border-2 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer relative ${
                isDragging 
                  ? 'border-indigo-500 bg-indigo-50/20' 
                  : selectedFile 
                    ? 'border-emerald-500 bg-emerald-50/10' 
                    : 'border-zinc-300 hover:border-indigo-400 dark:border-zinc-800'
              }`"
            >
              <input 
                type="file" 
                id="doc-file-input" 
                @change="handleFileSelect" 
                class="hidden" 
                accept="image/*,application/pdf,text/*,application/json"
              />
              <label for="doc-file-input" class="cursor-pointer block space-y-2">
                <div v-if="selectedFile" class="space-y-1">
                  <CheckCircle class="w-10 h-10 mx-auto text-emerald-500 animate-bounce" />
                  <p class="text-xs font-bold text-emerald-600 dark:text-emerald-450">{{ selectedFile.name }}</p>
                  <p class="text-[10px] text-zinc-400">{{ formatSize(selectedFile.size) }}</p>
                </div>
                <div v-else class="space-y-2">
                  <Upload class="w-8 h-8 mx-auto text-zinc-400 dark:text-zinc-600" />
                  <p class="text-xs font-extrabold text-zinc-800 dark:text-zinc-300">Drag & Drop file here, or click to browse</p>
                  <p class="text-[9.5px] text-zinc-450 leading-relaxed uppercase tracking-wider">
                    Maximum Size: 3MB • PDF, HTML, TXT, JSON, PNG, JPG, GIF
                  </p>
                </div>
              </label>
            </div>

            <!-- Field Meta inputs -->
            <div class="space-y-3">
              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Display Name</label>
                <input 
                  v-model="docName" 
                  type="text" 
                  placeholder="e.g. May House Lease Contract" 
                  required
                  class="w-full px-4 py-3 bg-[#fafafa] dark:bg-zinc-90 rounded-xl border border-zinc-200 text-xs font-semibold"
                />
              </div>

              <div>
                <label class="block text-[10px] font-bold text-zinc-405 uppercase tracking-wider mb-2">Description / Notes</label>
                <textarea 
                  v-model="docDesc" 
                  placeholder="Append tags, remarks, scan date details, or billing codes..." 
                  class="w-full px-4 py-3 bg-white dark:bg-zinc-95 border border-zinc-205 dark:border-zinc-805 rounded-xl text-xs font-semibold resize-none h-16"
                />
              </div>

              <!-- Linkage selector triggers -->
              <div class="pt-3 border-t border-zinc-150 dark:border-white/5">
                <h4 class="text-[10px] font-black text-rose-500 uppercase tracking-widest mb-3">Service Link Connection (Optional)</h4>
                
                <div class="grid grid-cols-3 gap-2">
                  <button 
                    type="button"
                    @click="linkService = (linkService === 'accounts' ? null : 'accounts'); linkEntityId = '';"
                    :class="`py-2 rounded-xl text-[9.5px] font-black uppercase tracking-wider border bg-transparent flex flex-col items-center gap-1 ${
                      linkService === 'accounts' 
                        ? 'border-pink-500 bg-pink-50/30 text-pink-500' 
                        : 'border-zinc-200/50 dark:border-zinc-805 text-zinc-500'
                    }`"
                  >
                    <CreditCard class="w-3.5 h-3.5" />
                    Accounts
                  </button>

                  <button 
                    type="button"
                    @click="linkService = (linkService === 'rent' ? null : 'rent'); linkEntityId = '';"
                    :class="`py-2 rounded-xl text-[9.5px] font-black uppercase tracking-wider border bg-transparent flex flex-col items-center gap-1 ${
                      linkService === 'rent' 
                        ? 'border-pink-500 bg-pink-50/30 text-pink-500' 
                        : 'border-zinc-200/50 dark:border-zinc-805 text-zinc-500'
                    }`"
                  >
                    <KeyRound class="w-3.5 h-3.5" />
                    Rent
                  </button>

                  <button 
                    type="button"
                    @click="linkService = (linkService === 'loans_debts' ? null : 'loans_debts'); linkEntityId = '';"
                    :class="`py-2 rounded-xl text-[9.5px] font-black uppercase tracking-wider border bg-transparent flex flex-col items-center gap-1 ${
                      linkService === 'loans_debts' 
                        ? 'border-pink-500 bg-pink-50/30 text-pink-500' 
                        : 'border-zinc-200/50 dark:border-zinc-805 text-zinc-500'
                    }`"
                  >
                    <User class="w-3.5 h-3.5" />
                    Loans
                  </button>

                  <button 
                    type="button"
                    @click="linkService = (linkService === 'mortgages' ? null : 'mortgages'); linkEntityId = '';"
                    :class="`py-2 rounded-xl text-[9.5px] font-black uppercase tracking-wider border bg-transparent flex flex-col items-center gap-1 ${
                      linkService === 'mortgages' 
                        ? 'border-pink-500 bg-pink-50/30 text-pink-500' 
                        : 'border-zinc-200/50 dark:border-zinc-805 text-zinc-500'
                    }`"
                  >
                    <Building class="w-3.5 h-3.5" />
                    Mortgages
                  </button>

                  <button 
                    type="button"
                    @click="linkService = (linkService === 'savings' ? null : 'savings'); linkEntityId = '';"
                    :class="`py-2 rounded-xl text-[9.5px] font-black uppercase tracking-wider border bg-transparent flex flex-col items-center gap-1 ${
                      linkService === 'savings' 
                        ? 'border-pink-500 bg-pink-50/30 text-pink-500' 
                        : 'border-zinc-200/50 dark:border-zinc-805 text-zinc-500'
                    }`"
                  >
                    <PiggyBank class="w-3.5 h-3.5" />
                    Savings
                  </button>
                </div>

                <!-- Dropdown selector mapping to linkable selector options -->
                <div v-if="linkService" class="mt-3">
                  <label class="block text-[8.5px] font-bold text-zinc-450 uppercase mb-2">Select Active Target Record</label>
                  <select 
                    v-model="linkEntityId"
                    class="w-full px-4 py-3 bg-[#fafafa] rounded-xl border text-xs font-semibold focus:outline-none"
                  >
                    <option value="">-- Choose active items to sync --</option>
                    <option v-for="item in linkableEntities" :key="item.id" :value="item.id">
                      {{ getEntityLabel(item) }}
                    </option>
                  </select>
                </div>
              </div>
            </div>

            <button 
              @click="handleUploadDocument"
              class="w-full py-4 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-xl mt-4 cursor-pointer border-none"
            >
              Verify & Secure to Cabinet Vault
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- File Preview Popup detailed Modal Overlay -- Handles visual rendering -->
    <transition name="fade">
      <div v-if="activeDocPreview" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Overlay background shadow backdrop -->
        <div class="absolute inset-0 bg-zinc-950/80 backdrop-blur-sm cursor-pointer" @click="activeDocPreview = null" />

        <div class="bg-white dark:bg-[#0c141d] border border-zinc-200 dark:border-white/10 rounded-2xl w-full max-w-2xl relative z-10 text-left overflow-hidden flex flex-col max-h-[85vh]">
          <!-- header -->
          <div class="p-5 border-b border-zinc-150 dark:border-white/5 flex items-center justify-between">
            <div>
              <h3 class="text-sm font-black text-zinc-950 dark:text-white uppercase tracking-wider truncate max-w-sm">
                {{ activeDocPreview.name }}
              </h3>
              <p class="text-[10px] text-zinc-450 mt-0.5">
                {{ formatSize(activeDocPreview.fileSize) }} • {{ activeDocPreview.fileType }}
              </p>
            </div>
            <button @click="activeDocPreview = null" class="text-zinc-400 hover:text-white cursor-pointer select-none font-bold bg-transparent border-none">×</button>
          </div>

          <!-- render box block -->
          <div class="p-6 bg-zinc-50 dark:bg-zinc-950 flex-1 overflow-auto flex items-center justify-center min-h-[300px]">
            <!-- Picture visual presentation -->
            <div v-if="activeDocPreview.fileType?.startsWith('image/')" class="max-w-full max-h-[50vh] overflow-hidden rounded-xl">
              <img :src="activeDocPreview.fileData" class="max-w-full max-h-[50vh] object-contain" />
            </div>

            <!-- Plain textual content display -->
            <pre 
              v-else-if="activeDocPreview.fileType?.startsWith('text/') || activeDocPreview.fileType === 'application/json'"
              class="w-full text-left font-mono text-[11px] p-4 bg-white dark:bg-[#080d12] border dark:border-white/5 rounded-xl h-[45vh] overflow-auto whitespace-pre-wrap dark:text-zinc-200 text-zinc-900"
            >{{ activeDocPreview.fileData?.includes(';base64,') ? atob(activeDocPreview.fileData.split(',')[1]) : activeDocPreview.fileData }}</pre>

            <!-- Fallback container panel indicator -->
            <div v-else class="text-center py-20">
              <FileText class="w-20 h-20 text-zinc-300 dark:text-zinc-700 mx-auto mb-4" />
              <p class="text-xs font-bold text-zinc-600 dark:text-zinc-300 mb-1">Preview Unavailable for Type: {{ activeDocPreview.fileType }}</p>
              <p class="text-[10px] text-zinc-450">You can download the original file securely locally to view its data contents.</p>
            </div>
          </div>

          <!-- footer info block -->
          <div class="p-5 border-t border-zinc-150 dark:border-white/5 flex gap-3 items-center justify-between">
            <div class="text-xs text-zinc-500">
              <span v-if="activeDocPreview.description" class="italic text-zinc-400">"{{ activeDocPreview.description }}"</span>
              <span v-else class="text-[10px] text-zinc-450 uppercase font-bold tracking-wider">No notes text setup</span>
            </div>

            <div class="flex gap-2">
              <button 
                @click="activeDocPreview = null" 
                class="px-4 py-2 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700 rounded-xl text-xs font-bold cursor-pointer border-none"
              >
                Dismiss
              </button>
              <button 
                @click="triggerFileDownload(activeDocPreview)" 
                class="px-5 py-2 bg-indigo-600 hover:bg-indigo-750 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer border-none"
              >
                <Download class="w-4 h-4" />
                Download Original File
              </button>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>
