<script setup lang="ts">
/**
 * VaultUploadForm — File upload form for DocumentVault entities.
 *
 * Features:
 *   - File upload zone with drag-and-drop support (accept PDF/PNG/JPG/XLSX/CSV)
 *   - Auto-detect file_type from extension
 *   - Show file name and file_size after selection
 *   - Fields: title (auto-filled from filename), expiry_date, remind_before_expiry,
 *     days_before_expiry_reminder (shown only if remind_before_expiry)
 *   - On submit: build FormData with file + metadata, call store.uploadFile(formData)
 *   - FormErrors display
 *
 * Registers as `ldgr-vault-upload-form` custom element.
 */

import { FormErrors } from "@/components/vue";
import { useVaultStore } from "@/stores/vault";
import type { DocumentVaultOut, VaultFileType } from "@/lib/ledgerTypes";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({ name: "LdgrVaultUploadForm" });

// ─── Props & Emits ───────────────────────────────────────────────────────────

const props = withDefaults(
  defineProps<{
    /** Whether the form is visible (parent controls visibility via Modal). */
    open?: boolean;
  }>(),
  {
    open: false,
  },
);

const emit = defineEmits<{
  saved: [item: DocumentVaultOut];
  cancel: [];
}>();

// ─── Store ───────────────────────────────────────────────────────────────────

const store = useVaultStore();

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  const size = bytes / Math.pow(k, i);
  return `${size.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

/** Map file extension to VaultFileType */
function detectFileType(filename: string): VaultFileType {
  const ext = filename.split(".").pop()?.toUpperCase() ?? "";
  const typeMap: Record<string, VaultFileType> = {
    PDF: "PDF",
    PNG: "PNG",
    JPG: "JPG",
    JPEG: "JPG",
    XLSX: "XLSX",
    XLS: "XLSX",
    CSV: "CSV",
  };
  return typeMap[ext] ?? "OTHER";
}

// ─── State ───────────────────────────────────────────────────────────────────

const selectedFile = ref<File | null>(null);
const title = ref("");
const expiryDate = ref("");
const remindBeforeExpiry = ref(false);
const daysBeforeExpiryReminder = ref(30);
const isDragOver = ref(false);
const loading = ref(false);
const error = ref<string | null>(null);
const fieldErrors = ref<Record<string, string[]>>({});

// ─── File Input Ref ──────────────────────────────────────────────────────────

const fileInput = ref<HTMLInputElement | null>(null);

// ─── File Selection ──────────────────────────────────────────────────────────

function handleFileSelect(event: Event) {
  const input = event.target as HTMLInputElement;
  if (input.files && input.files.length > 0) {
    processFile(input.files[0]);
  }
}

function processFile(file: File) {
  selectedFile.value = file;
  // Auto-fill title from filename (without extension)
  if (!title.value) {
    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
    title.value = nameWithoutExt;
  }
}

function removeFile() {
  selectedFile.value = null;
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

// ─── Drag and Drop ───────────────────────────────────────────────────────────

function onDragOver(event: DragEvent) {
  event.preventDefault();
  isDragOver.value = true;
}

function onDragLeave(event: DragEvent) {
  event.preventDefault();
  isDragOver.value = false;
}

function onDrop(event: DragEvent) {
  event.preventDefault();
  isDragOver.value = false;
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    processFile(event.dataTransfer.files[0]);
  }
}

function openFilePicker() {
  fileInput.value?.click();
}

// ─── Computed ────────────────────────────────────────────────────────────────

const detectedFileType = computed<VaultFileType>(() => {
  if (!selectedFile.value) return "OTHER";
  return detectFileType(selectedFile.value.name);
});

// ─── Submit ──────────────────────────────────────────────────────────────────

async function handleSubmit() {
  if (!selectedFile.value) {
    fieldErrors.value = { file: ["Please select a file to upload."] };
    return;
  }

  if (!title.value.trim()) {
    fieldErrors.value = { title: ["Title is required."] };
    return;
  }

  loading.value = true;
  error.value = null;
  fieldErrors.value = {};

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    formData.append("title", title.value.trim());
    formData.append("file_type", detectedFileType.value);
    formData.append("file_size", String(selectedFile.value.size));
    formData.append("content_type_id", "0");
    formData.append("object_id", "0");

    if (expiryDate.value) {
      formData.append("expiry_date", expiryDate.value);
    }

    if (remindBeforeExpiry.value) {
      formData.append("remind_before_expiry", "true");
      formData.append("days_before_expiry_reminder", String(daysBeforeExpiryReminder.value));
    }

    const result = await store.uploadFile(formData);
    if (result) {
      emit("saved", result);
      resetForm();
    }
  } catch (err: unknown) {
    if (err instanceof Error) {
      error.value = err.message;
    } else {
      error.value = "Failed to upload document. Please try again.";
    }
    // Check if store has field errors
    if (store.fieldErrors && Object.keys(store.fieldErrors).length > 0) {
      fieldErrors.value = store.fieldErrors;
    }
  } finally {
    loading.value = false;
  }
}

function resetForm() {
  selectedFile.value = null;
  title.value = "";
  expiryDate.value = "";
  remindBeforeExpiry.value = false;
  daysBeforeExpiryReminder.value = 30;
  error.value = null;
  fieldErrors.value = {};
  if (fileInput.value) {
    fileInput.value.value = "";
  }
}

function handleCancel() {
  resetForm();
  emit("cancel");
}
</script>

<template>
  <form @submit.prevent="handleSubmit" class="space-y-5">
    <!-- Form Errors -->
    <FormErrors :errors="error" :field-errors="fieldErrors" />

    <!-- File Upload Zone -->
    <div class="space-y-1.5">
      <label class="label-text">
        File <span class="text-debit">*</span>
      </label>
      <div
        :class="[
          'relative border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer',
          isDragOver
            ? 'border-cyan-500 bg-cyan-50 dark:bg-cyan-950/20'
            : selectedFile
              ? 'border-green-400 dark:border-green-600 bg-green-50/50 dark:bg-green-950/10'
              : 'border-navy-300 dark:border-navy-600 hover:border-cyan-400 dark:hover:border-cyan-600 hover:bg-cyan-50/30 dark:hover:bg-cyan-950/10',
          fieldErrors.file ? 'border-red-400 dark:border-red-600' : '',
        ]"
        @dragover="onDragOver"
        @dragleave="onDragLeave"
        @drop="onDrop"
        @click="openFilePicker"
      >
        <input
          ref="fileInput"
          type="file"
          class="hidden"
          accept=".pdf,.png,.jpg,.jpeg,.xlsx,.xls,.csv"
          @change="handleFileSelect"
        />

        <!-- No file selected -->
        <template v-if="!selectedFile">
          <svg class="h-10 w-10 mx-auto text-slate-custom-400 mb-3" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm text-slate-custom-600 dark:text-slate-custom-400">
            <span class="font-medium text-cyan-700 dark:text-cyan-400">Click to upload</span>
            or drag and drop
          </p>
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mt-1">
            PDF, PNG, JPG, XLSX, CSV
          </p>
        </template>

        <!-- File selected -->
        <template v-else>
          <svg class="h-8 w-8 mx-auto text-green-500 mb-2" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
          </svg>
          <p class="text-sm font-medium text-navy-900 dark:text-navy-100">
            {{ selectedFile.name }}
          </p>
          <p class="text-xs text-slate-custom-500 dark:text-slate-custom-400 mt-0.5">
            {{ formatFileSize(selectedFile.size) }} &middot; {{ detectedFileType }}
          </p>
          <button
            type="button"
            class="mt-2 text-xs text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
            @click.stop="removeFile"
          >
            Remove file
          </button>
        </template>
      </div>
      <p v-if="fieldErrors.file" class="text-xs text-debit mt-1">
        {{ fieldErrors.file[0] }}
      </p>
    </div>

    <!-- Title -->
    <div class="space-y-1.5">
      <label for="vault-title" class="label-text">
        Title <span class="text-debit">*</span>
      </label>
      <input
        id="vault-title"
        v-model="title"
        type="text"
        class="input-field"
        placeholder="Document title"
        required
      />
      <p v-if="fieldErrors.title" class="text-xs text-debit mt-1">
        {{ fieldErrors.title[0] }}
      </p>
    </div>

    <!-- Expiry Date -->
    <div class="space-y-1.5">
      <label for="vault-expiry" class="label-text">Expiry Date</label>
      <input
        id="vault-expiry"
        v-model="expiryDate"
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
          id="vault-remind"
          v-model="remindBeforeExpiry"
          type="checkbox"
          class="h-4 w-4 rounded border-navy-300 dark:border-navy-600 text-cyan-600 focus:ring-cyan-500"
        />
        <label for="vault-remind" class="text-sm text-navy-900 dark:text-navy-100">
          Remind me before expiry
        </label>
      </div>

      <!-- Days Before Expiry Reminder (shown only if remind_before_expiry) -->
      <div v-if="remindBeforeExpiry" class="ml-6 space-y-1.5">
        <label for="vault-reminder-days" class="label-text">
          Days before expiry to remind
        </label>
        <input
          id="vault-reminder-days"
          v-model.number="daysBeforeExpiryReminder"
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

    <!-- Action Buttons -->
    <div class="flex items-center justify-end gap-3 pt-4 border-t border-navy-100 dark:border-navy-800">
      <button
        type="button"
        class="btn-secondary"
        :disabled="loading"
        @click="handleCancel"
      >
        Cancel
      </button>
      <button
        type="submit"
        class="btn-primary"
        :disabled="loading || !selectedFile"
      >
        <svg
          v-if="loading"
          class="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
        >
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        Upload Document
      </button>
    </div>
  </form>
</template>
