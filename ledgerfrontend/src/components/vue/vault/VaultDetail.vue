<script setup lang="ts">
/**
 * VaultDetail — Full detail view for a single DocumentVault entry.
 *
 * Features:
 *   - Loads document by ID from route (props: id as string)
 *   - Document preview section: file type icon (large), title, file_type badge,
 *     file_size, upload date, expiry_date (with color coding)
 *   - Metadata card: title, expiry_date, reminder settings
 *   - Actions: Edit metadata (inline toggle to edit mode), Download, Delete/Restore
 *   - Edit mode: title (text), expiry_date (date), remind_before_expiry (checkbox),
 *     days_before_expiry_reminder (number)
 *   - Back button to /dashboard/vault
 *
 * Registers as `ldgr-vault-detail` custom element.
 */

import {
  ConfirmDialog,
  TypeBadge,
  LoadingSkeleton,
  FormErrors,
} from "@/components/vue";
import {
  useSoftDelete,
  useActivator,
} from "@/composables";
import { useVaultStore } from "@/stores/vault";
import type {
  DocumentVaultOut,
  DocumentVaultUpdate,
  VaultFileType,
} from "@/lib/ledgerTypes";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrVaultDetail",
});

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  /** Document ID from Astro route param. */
  id: string;
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const vaultStore = useVaultStore();

// ─── State ───────────────────────────────────────────────────────────────────

const docId = computed(() => parseInt(props.id, 10));
const isEditing = ref(false);
const editTitle = ref("");
const editExpiryDate = ref("");
const editRemindBeforeExpiry = ref(false);
const editDaysBeforeExpiryReminder = ref(30);
const editLoading = ref(false);
const editError = ref<string | null>(null);
const editFieldErrors = ref<Record<string, string[]>>({});

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = bytes / Math.pow(k, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString();
}

function getExpiryDateClass(date: string | null): string {
  if (!date) return "text-green-600 dark:text-green-400";
  const now = new Date();
  const expiry = new Date(date);
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return "text-red-600 dark:text-red-400";
  if (diffDays <= 30) return "text-orange-600 dark:text-orange-400";
  return "text-green-600 dark:text-green-400";
}

function getExpiryDateLabel(date: string | null): string {
  if (!date) return "No expiry";
  const now = new Date();
  const expiry = new Date(date);
  const diffDays = Math.ceil((expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) return `Expired ${Math.abs(diffDays)} day${Math.abs(diffDays) !== 1 ? "s" : ""} ago`;
  if (diffDays === 0) return "Expires today";
  if (diffDays === 1) return "Expires tomorrow";
  if (diffDays <= 30) return `Expires in ${diffDays} days`;
  return formatDate(date);
}

// ─── File Type Map ───────────────────────────────────────────────────────────

const fileTypeMap: Record<string, { bg: string; text: string }> = {
  pdf: { bg: "bg-red-100 dark:bg-red-950/50", text: "text-red-800 dark:text-red-300" },
  png: { bg: "bg-green-100 dark:bg-green-950/50", text: "text-green-800 dark:text-green-300" },
  jpg: { bg: "bg-amber-100 dark:bg-amber-950/50", text: "text-amber-800 dark:text-amber-300" },
  xlsx: { bg: "bg-emerald-100 dark:bg-emerald-950/50", text: "text-emerald-800 dark:text-emerald-300" },
  csv: { bg: "bg-cyan-100 dark:bg-cyan-950/50", text: "text-cyan-800 dark:text-cyan-300" },
  other: { bg: "bg-slate-100 dark:bg-slate-800/50", text: "text-slate-700 dark:text-slate-300" },
};

const fileTypeIconPath = "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z";

function getFileTypeKey(ft: string): string {
  const lower = ft?.toLowerCase?.();
  if (lower && fileTypeMap[lower]) return lower;
  return "other";
}

// ─── Load Data ───────────────────────────────────────────────────────────────

const isLoading = ref(true);
const loadError = ref<string | null>(null);

async function loadDocument() {
  if (isNaN(docId.value)) {
    loadError.value = "Invalid document ID";
    isLoading.value = false;
    return;
  }
  isLoading.value = true;
  loadError.value = null;
  try {
    await vaultStore.fetchOne(docId.value);
  } catch (err) {
    loadError.value = err instanceof Error ? err.message : "Failed to load document";
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  loadDocument();
});

watch(() => props.id, () => {
  loadDocument();
  isEditing.value = false;
});

// ─── Computed ────────────────────────────────────────────────────────────────

const doc = computed<DocumentVaultOut | null>(() => vaultStore.current);

// ─── Soft Delete ─────────────────────────────────────────────────────────────

const deleter = useSoftDelete<DocumentVaultOut>({
  store: vaultStore,
  entityName: "Document",
  getEntityLabel: (item) => item.title,
  onDeleted: () => {
    window.location.href = "/dashboard/vault";
  },
  onRestored: () => {
    loadDocument();
  },
});

// ─── Activator ───────────────────────────────────────────────────────────────

const activator = useActivator<DocumentVaultOut>({
  store: vaultStore,
  entityName: "Document",
  getEntityLabel: (item) => item.title,
  onActivated: () => {
    loadDocument();
  },
  onDeactivated: () => {
    loadDocument();
  },
});

// ─── Edit Mode ───────────────────────────────────────────────────────────────

function enterEditMode() {
  if (!doc.value) return;
  editTitle.value = doc.value.title;
  editExpiryDate.value = doc.value.expiry_date ? doc.value.expiry_date.split("T")[0] : "";
  editRemindBeforeExpiry.value = doc.value.remind_before_expiry;
  editDaysBeforeExpiryReminder.value = doc.value.days_before_expiry_reminder || 30;
  editError.value = null;
  editFieldErrors.value = {};
  isEditing.value = true;
}

function cancelEdit() {
  isEditing.value = false;
  editError.value = null;
  editFieldErrors.value = {};
}

async function saveEdit() {
  if (!doc.value) return;

  editLoading.value = true;
  editError.value = null;
  editFieldErrors.value = {};

  try {
    const updateData: DocumentVaultUpdate = {
      title: editTitle.value.trim() || null,
      expiry_date: editExpiryDate.value || null,
      remind_before_expiry: editRemindBeforeExpiry.value,
      days_before_expiry_reminder: editRemindBeforeExpiry.value
        ? editDaysBeforeExpiryReminder.value
        : null,
    };

    await vaultStore.update(doc.value.id, updateData);
    isEditing.value = false;
    await loadDocument();
  } catch (err: unknown) {
    if (err instanceof Error) {
      editError.value = err.message;
    } else {
      editError.value = "Failed to update document. Please try again.";
    }
    if (vaultStore.fieldErrors && Object.keys(vaultStore.fieldErrors).length > 0) {
      editFieldErrors.value = vaultStore.fieldErrors;
    }
  } finally {
    editLoading.value = false;
  }
}

// ─── Navigation ──────────────────────────────────────────────────────────────

function goBack() {
  window.location.href = "/dashboard/vault";
}

// ─── Download ────────────────────────────────────────────────────────────────

function downloadFile() {
  if (!doc.value) return;
  // The file URL is stored in doc.value.file
  // Open in a new tab for download
  const fileUrl = doc.value.file;
  if (fileUrl) {
    window.open(fileUrl, "_blank");
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading State -->
    <LoadingSkeleton v-if="isLoading" type="detail" />

    <!-- Error State -->
    <div v-else-if="loadError" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-debit" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
        </svg>
        <p class="text-debit font-medium">Failed to load document</p>
        <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">{{ loadError }}</p>
        <button class="btn-secondary" @click="loadDocument">Try Again</button>
      </div>
    </div>

    <!-- Not Found -->
    <div v-else-if="!doc" class="card p-6 text-center">
      <div class="flex flex-col items-center gap-3">
        <svg class="h-10 w-10 text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586l3.414 3.414A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" />
        </svg>
        <p class="text-navy-900 dark:text-navy-100 font-medium">Document not found</p>
        <button class="btn-secondary" @click="goBack">Back to Vault</button>
      </div>
    </div>

    <!-- Document Detail Content -->
    <template v-else>
      <!-- Back Button -->
      <button
        class="btn-ghost text-sm text-slate-custom-600 dark:text-slate-custom-400 hover:text-navy-900 dark:hover:text-navy-100 -ml-2"
        @click="goBack"
      >
        <svg class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clip-rule="evenodd" />
        </svg>
        Back to Vault
      </button>

      <!-- Header Card: Document Preview -->
      <div class="card p-6">
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <!-- Left: Document Info -->
          <div class="flex items-start gap-4 flex-1">
            <!-- Large File Type Icon -->
            <div
              :class="[
                'flex-shrink-0 w-16 h-16 rounded-xl flex items-center justify-center',
                fileTypeMap[getFileTypeKey(doc.file_type)]?.bg ?? fileTypeMap.other.bg,
              ]"
            >
              <svg
                :class="[
                  'h-8 w-8',
                  fileTypeMap[getFileTypeKey(doc.file_type)]?.text ?? fileTypeMap.other.text,
                ]"
                viewBox="0 0 20 20"
                fill="currentColor"
                aria-hidden="true"
              >
                <path :d="fileTypeIconPath" />
              </svg>
            </div>
            <div class="flex-1 min-w-0 space-y-2">
              <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100 break-words">
                {{ doc.title }}
              </h1>
              <div class="flex flex-wrap items-center gap-2">
                <TypeBadge
                  :type="getFileTypeKey(doc.file_type)"
                  :type-map="fileTypeMap"
                  :show-icon="false"
                  size="md"
                />
                <span
                  v-if="doc.is_deleted"
                  class="inline-flex items-center rounded-full bg-red-100 dark:bg-red-950/50 px-2.5 py-1 text-xs font-medium text-red-800 dark:text-red-300"
                >
                  Deleted
                </span>
                <span
                  v-else-if="!doc.is_active"
                  class="inline-flex items-center rounded-full bg-amber-100 dark:bg-amber-950/50 px-2.5 py-1 text-xs font-medium text-amber-800 dark:text-amber-300"
                >
                  Inactive
                </span>
                <span
                  v-else
                  class="inline-flex items-center rounded-full bg-green-100 dark:bg-green-950/50 px-2.5 py-1 text-xs font-medium text-green-800 dark:text-green-300"
                >
                  Active
                </span>
              </div>
            </div>
          </div>

          <!-- Right: Actions -->
          <div class="flex flex-col gap-2 md:items-end">
            <!-- Edit / Save / Cancel -->
            <button
              v-if="!isEditing"
              class="btn-primary"
              @click="enterEditMode"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
              </svg>
              Edit Metadata
            </button>
            <template v-else>
              <div class="flex items-center gap-2">
                <button
                  class="btn-secondary"
                  :disabled="editLoading"
                  @click="cancelEdit"
                >
                  Cancel
                </button>
                <button
                  class="btn-primary"
                  :disabled="editLoading"
                  @click="saveEdit"
                >
                  <svg
                    v-if="editLoading"
                    class="h-4 w-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                  >
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Save Changes
                </button>
              </div>
            </template>

            <!-- Download -->
            <button
              class="btn-ghost text-cyan-700 dark:text-cyan-400 hover:bg-cyan-50 dark:hover:bg-cyan-950/30"
              @click="downloadFile"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
              </svg>
              Download
            </button>

            <!-- Activate / Deactivate -->
            <button
              v-if="doc.is_active && !doc.is_deleted"
              class="btn-ghost text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-950/30"
              @click="activator.confirmDeactivate(doc)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 008.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clip-rule="evenodd" />
              </svg>
              Deactivate
            </button>
            <button
              v-else-if="!doc.is_deleted"
              class="btn-ghost text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="activator.confirmActivate(doc)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd" />
              </svg>
              Activate
            </button>

            <!-- Delete / Restore -->
            <button
              v-if="!doc.is_deleted"
              class="btn-ghost text-debit hover:bg-red-50 dark:hover:bg-red-950/30"
              @click="deleter.confirmDelete(doc)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
              </svg>
              Delete
            </button>
            <button
              v-else
              class="btn-ghost text-credit hover:bg-green-50 dark:hover:bg-green-950/30"
              @click="deleter.confirmRestore(doc)"
            >
              <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
              </svg>
              Restore
            </button>
          </div>
        </div>

        <!-- Summary Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-navy-100 dark:border-navy-800">
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">File Size</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatFileSize(doc.file_size) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">File Type</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ getFileTypeKey(doc.file_type).toUpperCase() }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Uploaded</p>
            <p class="text-lg font-bold text-navy-900 dark:text-navy-100">
              {{ formatDate(doc.created_at) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mb-1">Expiry</p>
            <p :class="['text-lg font-bold', getExpiryDateClass(doc.expiry_date)]">
              {{ getExpiryDateLabel(doc.expiry_date) }}
            </p>
          </div>
        </div>

        <!-- Store Error -->
        <FormErrors
          v-if="vaultStore.error"
          :errors="vaultStore.error"
          class="mt-4"
        />
      </div>

      <!-- Metadata Card -->
      <div class="card p-6">
        <h2 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-4">Document Metadata</h2>

        <!-- Edit Mode -->
        <template v-if="isEditing">
          <FormErrors :errors="editError" :field-errors="editFieldErrors" />

          <form @submit.prevent="saveEdit" class="space-y-5">
            <!-- Title -->
            <div class="space-y-1.5">
              <label for="edit-vault-title" class="label-text">
                Title <span class="text-debit">*</span>
              </label>
              <input
                id="edit-vault-title"
                v-model="editTitle"
                type="text"
                class="input-field"
                placeholder="Document title"
                required
              />
            </div>

            <!-- Expiry Date -->
            <div class="space-y-1.5">
              <label for="edit-vault-expiry" class="label-text">Expiry Date</label>
              <input
                id="edit-vault-expiry"
                v-model="editExpiryDate"
                type="date"
                class="input-field"
              />
              <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
                Optional — set a date when this document expires
              </p>
            </div>

            <!-- Remind Before Expiry -->
            <div class="space-y-3">
              <div class="flex items-center gap-2">
                <input
                  id="edit-vault-remind"
                  v-model="editRemindBeforeExpiry"
                  type="checkbox"
                  class="h-4 w-4 rounded border-navy-300 dark:border-navy-600 text-cyan-600 focus:ring-cyan-500"
                />
                <label for="edit-vault-remind" class="text-sm text-navy-900 dark:text-navy-100">
                  Remind me before expiry
                </label>
              </div>

              <!-- Days Before Expiry Reminder -->
              <div v-if="editRemindBeforeExpiry" class="ml-6 space-y-1.5">
                <label for="edit-vault-reminder-days" class="label-text">
                  Days before expiry to remind
                </label>
                <input
                  id="edit-vault-reminder-days"
                  v-model.number="editDaysBeforeExpiryReminder"
                  type="number"
                  min="1"
                  max="365"
                  class="input-field"
                  placeholder="30"
                />
                <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400">
                  You will be notified this many days before the document expires
                </p>
              </div>
            </div>
          </form>
        </template>

        <!-- View Mode -->
        <template v-else>
          <dl class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
            <!-- Title -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Title</dt>
              <dd class="text-sm font-medium text-navy-900 dark:text-navy-100 break-words">
                {{ doc.title }}
              </dd>
            </div>

            <!-- File Type -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">File Type</dt>
              <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
                <TypeBadge
                  :type="getFileTypeKey(doc.file_type)"
                  :type-map="fileTypeMap"
                  :show-icon="false"
                  size="sm"
                />
              </dd>
            </div>

            <!-- File Size -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">File Size</dt>
              <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
                {{ formatFileSize(doc.file_size) }}
              </dd>
            </div>

            <!-- Expiry Date -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Expiry Date</dt>
              <dd :class="['text-sm font-medium', getExpiryDateClass(doc.expiry_date)]">
                {{ doc.expiry_date ? formatDate(doc.expiry_date) : "No expiry" }}
              </dd>
            </div>

            <!-- Reminder Settings -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Expiry Reminder</dt>
              <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
                <template v-if="doc.remind_before_expiry">
                  <span class="inline-flex items-center gap-1 text-green-700 dark:text-green-400">
                    <svg class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clip-rule="evenodd" />
                    </svg>
                    {{ doc.days_before_expiry_reminder }} days before
                  </span>
                </template>
                <template v-else>
                  <span class="text-slate-custom-500 dark:text-slate-custom-400">Disabled</span>
                </template>
              </dd>
            </div>

            <!-- Upload Date -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Uploaded</dt>
              <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
                {{ formatDate(doc.created_at) }}
              </dd>
            </div>

            <!-- Last Updated -->
            <div class="flex flex-col">
              <dt class="text-sm text-slate-custom-500 dark:text-slate-custom-400 mb-0.5">Last Updated</dt>
              <dd class="text-sm font-medium text-navy-900 dark:text-navy-100">
                {{ formatDate(doc.updated_at) }}
              </dd>
            </div>
          </dl>
        </template>
      </div>

      <!-- Delete / Restore ConfirmDialog -->
      <ConfirmDialog
        :open="deleter.showConfirm.value"
        :title="deleter.dialogTitle.value"
        :message="deleter.dialogMessage.value"
        :variant="deleter.dialogVariant.value"
        :confirm-text="deleter.confirmText.value"
        :loading="deleter.loading.value"
        @confirm="deleter.execute()"
        @cancel="deleter.cancel()"
      />

      <!-- Activate / Deactivate ConfirmDialog -->
      <ConfirmDialog
        :open="activator.showConfirm.value"
        :title="activator.dialogTitle.value"
        :message="activator.dialogMessage.value"
        :variant="activator.dialogVariant.value"
        :confirm-text="activator.confirmText.value"
        :loading="activator.loading.value"
        @confirm="activator.execute()"
        @cancel="activator.cancel()"
      />
    </template>
  </div>
</template>
