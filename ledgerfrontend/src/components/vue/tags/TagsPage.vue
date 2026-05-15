<script setup lang="ts">
/**
 * TagsPage — Grid-based tag management page.
 *
 * Displays tags as colored cards in a responsive grid with:
 *   - Inline create at the top of the grid (text input + color picker + Add button)
 *   - SearchInput for name filtering
 *   - Edit modal (TagForm) when clicking a tag card
 *   - ConfirmDialog for soft-delete confirmation
 *   - EmptyState when no tags exist
 *   - LoadingSkeleton during data fetch
 *
 * Registered as `ldgr-tags-page` for Astro integration.
 */

import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import {
  Modal,
  ConfirmDialog,
  SearchInput,
  EmptyState,
  LoadingSkeleton,
  FeatureGate,
  UpgradePrompt,
} from "@/components/vue";
import {
  useLedgerFilters,
  useSoftDelete,
} from "@/composables";
import { useTagStore } from "@/stores/tag";
import TagForm from "./TagForm.vue";
import type { TagOut, TagCreate } from "@/lib/ledgerTypes";

// ─── Custom Element Registration ─────────────────────────────────────────────

defineOptions({
  name: "LdgrTagsPage",
});

// ─── Store & Composables ─────────────────────────────────────────────────────

const store = useTagStore();

const { filters, applyFilters, setFilter } = useLedgerFilters({
  store,
  defaultFilters: { limit: 100, offset: 0 },
  syncKeys: ["search"],
});

const deleter = useSoftDelete<TagOut>({
  store,
  entityName: "Tag",
  onDeleted: () => {
    // List is auto-refreshed by useSoftDelete
  },
});

// ─── Inline Create State ─────────────────────────────────────────────────────

const inlineName = ref("");
const inlineColor = ref("#6B7280");
const inlineError = ref<string | null>(null);
const inlineCreating = ref(false);

// ─── Edit Modal State ────────────────────────────────────────────────────────

const showEditModal = ref(false);
const editingTagId = ref<number | undefined>(undefined);

// ─── Computed ────────────────────────────────────────────────────────────────

const tagCount = computed(() => store.total);

const isLoading = computed(() => store.loading && !store.listLoaded);

const hasNoTags = computed(
  () => !store.loading && store.listLoaded && store.items.length === 0,
);

// Check if inline name already exists
const nameExists = computed(() => {
  if (!inlineName.value.trim()) return false;
  const trimmed = inlineName.value.trim().toLowerCase();
  return store.items.some(
    (tag) => tag.name.toLowerCase() === trimmed,
  );
});

// ─── Handlers ────────────────────────────────────────────────────────────────

/** Handle search input changes */
function handleSearch(query: string) {
  setFilter("search", query || null);
  applyFilters();
}

/** Create tag inline from the top-of-grid input */
async function handleInlineCreate() {
  const name = inlineName.value.trim();
  if (!name) return;

  if (nameExists.value) {
    inlineError.value = `A tag named "${name}" already exists.`;
    return;
  }

  inlineError.value = null;
  inlineCreating.value = true;

  try {
    const payload: TagCreate = {
      name,
      color: inlineColor.value || null,
    };
    await store.create(payload);
    // Reset inline form
    inlineName.value = "";
    inlineColor.value = randomColor();
  } catch (err: unknown) {
    // Extract error message
    if (typeof err === "object" && err !== null && "message" in err) {
      inlineError.value = String((err as Record<string, unknown>).message);
    } else {
      inlineError.value = "Failed to create tag";
    }
  } finally {
    inlineCreating.value = false;
  }
}

/** Handle Enter key in inline create input */
function handleInlineKeydown(e: KeyboardEvent) {
  inlineError.value = null;
  if (e.key === "Enter") {
    e.preventDefault();
    handleInlineCreate();
  }
}

/** Open edit modal for a tag */
function editTag(tag: TagOut) {
  editingTagId.value = tag.id;
  showEditModal.value = true;
}

/** Handle tag saved from the edit modal */
function handleTagSaved() {
  showEditModal.value = false;
  editingTagId.value = undefined;
}

/** Initiate delete for a tag */
function deleteTag(tag: TagOut) {
  deleter.confirmDelete(tag);
}

/** Generate a random pleasant color */
function randomColor(): string {
  const palette = [
    "#EF4444", "#F97316", "#F59E0B", "#84CC16",
    "#22C55E", "#14B8A6", "#06B6D4", "#3B82F6",
    "#6366F1", "#8B5CF6", "#A855F7", "#D946EF",
    "#EC4899", "#6B7280", "#78716C", "#0EA5E9",
  ];
  return palette[Math.floor(Math.random() * palette.length)];
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  if (!store.listLoaded) {
    store.fetchList();
  }
  // Set initial random color for inline create
  inlineColor.value = randomColor();
});
</script>

<template>
  <FeatureGate feature="tags" show-fallback>
  <div class="space-y-6">
    <!-- ── Page Header ──────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold text-navy-900 dark:text-navy-100">
          Tags
        </h1>
        <span
          v-if="tagCount > 0"
          class="inline-flex items-center rounded-full bg-cyan-100 dark:bg-cyan-950/50 px-2.5 py-0.5 text-xs font-medium text-cyan-700 dark:text-cyan-400"
        >
          {{ tagCount }}
        </span>
      </div>
    </div>

    <!-- ── Search ───────────────────────────────────────────────────────────── -->
    <div class="max-w-sm">
      <SearchInput
        :model-value="filters.search ?? ''"
        placeholder="Search tags..."
        @search="handleSearch"
      />
    </div>

    <!-- ── Loading State ────────────────────────────────────────────────────── -->
    <LoadingSkeleton v-if="isLoading" type="card" :rows="6" />

    <!-- ── Content ──────────────────────────────────────────────────────────── -->
    <div v-else>
      <!-- Tag Grid -->
      <div
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3"
      >
        <!-- ── Inline Create Card (always visible) ─────────────────────────── -->
        <div
          class="card p-4 flex flex-col gap-3 border-dashed border-2 border-cyan-300 dark:border-cyan-800 bg-cyan-50/50 dark:bg-cyan-950/20"
        >
          <div class="text-xs font-medium text-cyan-700 dark:text-cyan-400 uppercase tracking-wide">
            New Tag
          </div>

          <!-- Name input -->
          <input
            v-model="inlineName"
            type="text"
            class="input-field h-8 text-sm"
            placeholder="Tag name..."
            autocomplete="off"
            @keydown="handleInlineKeydown"
            @input="inlineError = null"
          />

          <!-- Color picker row -->
          <div class="flex items-center gap-2">
            <input
              v-model="inlineColor"
              type="color"
              class="h-7 w-8 cursor-pointer rounded border border-navy-200 dark:border-navy-700 bg-transparent p-0.5"
            />
            <span
              class="h-5 w-5 rounded-full shrink-0 border border-navy-200 dark:border-navy-700"
              :style="{ backgroundColor: inlineColor }"
            />
          </div>

          <!-- Add button -->
          <button
            class="btn-primary text-xs h-8 px-3 w-full"
            :disabled="!inlineName.trim() || inlineCreating || nameExists"
            @click="handleInlineCreate"
          >
            <svg
              v-if="inlineCreating"
              class="h-3.5 w-3.5 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
            >
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            <svg
              v-else
              class="h-3.5 w-3.5"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
            </svg>
            Add
          </button>

          <!-- Inline error for duplicate name / API error -->
          <p
            v-if="nameExists && inlineName.trim()"
            class="text-xs text-amber-600 dark:text-amber-400"
          >
            A tag with this name already exists.
          </p>
          <p
            v-else-if="inlineError"
            class="text-xs text-debit"
          >
            {{ inlineError }}
          </p>
        </div>

        <!-- ── Empty State (when no existing tags) ──────────────────────────── -->
        <div
          v-if="hasNoTags"
          class="col-span-1 sm:col-span-2 md:col-span-3 lg:col-span-4 flex items-center justify-center"
        >
          <EmptyState
            title="No tags yet"
            description="Create your first tag using the form above. Tags help you categorize and filter transactions."
            icon="folder"
          />
        </div>

        <!-- ── Tag Cards ────────────────────────────────────────────────────── -->
        <div
          v-for="tag in store.items"
          :key="tag.id"
          class="card p-4 flex items-center justify-between group hover:shadow-md transition-shadow cursor-pointer"
          @click="editTag(tag)"
        >
          <div class="flex items-center gap-2">
            <span
              class="h-4 w-4 rounded-full shrink-0"
              :style="{ backgroundColor: tag.color || '#6B7280' }"
            />
            <span class="font-medium text-navy-900 dark:text-navy-100">
              {{ tag.name }}
            </span>
          </div>
          <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              class="btn-ghost text-xs p-1"
              @click.stop="editTag(tag)"
            >
              Edit
            </button>
            <button
              class="btn-ghost text-xs p-1 text-debit"
              @click.stop="deleteTag(tag)"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Edit Modal ───────────────────────────────────────────────────────── -->
    <Modal
      :open="showEditModal"
      title="Edit Tag"
      size="sm"
      @close="showEditModal = false"
    >
      <template #body>
        <TagForm
          mode="edit"
          :item-id="editingTagId"
          @saved="handleTagSaved"
          @cancel="showEditModal = false"
        />
      </template>
    </Modal>

    <!-- ── Delete Confirm Dialog ────────────────────────────────────────────── -->
    <ConfirmDialog
      :open="deleter.showConfirm.value"
      :title="deleter.dialogTitle.value"
      :message="deleter.dialogMessage.value"
      :confirm-text="deleter.confirmText.value"
      :variant="deleter.dialogVariant.value"
      :loading="deleter.loading.value"
      @confirm="deleter.execute()"
      @cancel="deleter.cancel()"
    />
  </div>
  <template #no-access>
    <UpgradePrompt feature="tags" />
  </template>
  </FeatureGate>
</template>
