<script setup lang="ts">
/**
 * TagChips — Display and edit a list of tags as colored chips.
 *
 * Shows tags as small colored pills with optional remove button.
 * In editable mode, includes an inline input for adding new tags.
 *
 * Usage:
 *   <TagChips :tags="selectedTags" editable @add="handleAdd" @remove="handleRemove" />
 */

export interface TagItem {
  id: number;
  name: string;
  color?: string;
}

const props = withDefaults(
  defineProps<{
    /** List of tags to display. */
    tags: TagItem[];
    /** Show edit controls (remove button + add input). */
    editable?: boolean;
    /** Available tags for the add autocomplete. */
    availableTags?: TagItem[];
    /** Size variant: 'sm' | 'md'. */
    size?: "sm" | "md";
  }>(),
  {
    editable: false,
    availableTags: () => [],
    size: "md",
  },
);

const emit = defineEmits<{
  add: [tag: TagItem];
  remove: [tagId: number];
}>();

// ─── State ────────────────────────────────────────────────────────────────────

const searchQuery = ref("");
const showSuggestions = ref(false);
const inputRef = ref<HTMLInputElement | null>(null);

// ─── Computed ─────────────────────────────────────────────────────────────────

const suggestions = computed(() => {
  if (!searchQuery.value) return [];
  const query = searchQuery.value.toLowerCase();
  const existingIds = new Set(props.tags.map((t) => t.id));
  return props.availableTags.filter(
    (t) => !existingIds.has(t.id) && t.name.toLowerCase().includes(query),
  );
});

const chipSize = computed(() =>
  props.size === "sm"
    ? "px-1.5 py-0.5 text-xs gap-1"
    : "px-2.5 py-1 text-sm gap-1.5",
);

// ─── Handlers ─────────────────────────────────────────────────────────────────

function handleAdd(tag: TagItem) {
  emit("add", tag);
  searchQuery.value = "";
  showSuggestions.value = false;
}

function focusInput() {
  inputRef.value?.focus();
  showSuggestions.value = true;
}

function handleInputBlur() {
  // Delay to allow click on suggestion
  setTimeout(() => {
    showSuggestions.value = false;
  }, 150);
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <!-- Existing Tags -->
    <span
      v-for="tag in tags"
      :key="tag.id"
      :class="[
        'inline-flex items-center rounded-full font-medium transition-colors',
        chipSize,
      ]"
      :style="{
        backgroundColor: tag.color ? `${tag.color}20` : undefined,
        color: tag.color,
        borderColor: tag.color,
        borderWidth: '1px',
      }"
    >
      <span>{{ tag.name }}</span>
      <!-- Remove Button -->
      <button
        v-if="editable"
        class="ml-0.5 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition-colors"
        aria-label="Remove tag"
        @click="emit('remove', tag.id)"
      >
        <svg class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
        </svg>
      </button>
    </span>

    <!-- Add Tag Input -->
    <div v-if="editable" class="relative">
      <input
        ref="inputRef"
        v-model="searchQuery"
        type="text"
        placeholder="+ Add"
        class="w-20 rounded-full border border-dashed border-navy-300 dark:border-navy-600 bg-transparent px-2 py-0.5 text-xs text-navy-900 dark:text-navy-100 placeholder:text-slate-custom-400 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
        @focus="showSuggestions = true"
        @blur="handleInputBlur"
      />
      <!-- Suggestions Dropdown -->
      <div
        v-if="showSuggestions && suggestions.length > 0"
        class="absolute z-20 mt-1 left-0 w-48 rounded-lg border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900 shadow-lg py-1"
      >
        <button
          v-for="tag in suggestions"
          :key="tag.id"
          class="w-full text-left px-3 py-1.5 text-sm text-navy-900 dark:text-navy-100 hover:bg-cyan-50 dark:hover:bg-navy-800 transition-colors flex items-center gap-2"
          @mousedown.prevent="handleAdd(tag)"
        >
          <span
            class="h-2.5 w-2.5 rounded-full flex-shrink-0"
            :style="{ backgroundColor: tag.color }"
          />
          {{ tag.name }}
        </button>
      </div>
    </div>
  </div>
</template>
