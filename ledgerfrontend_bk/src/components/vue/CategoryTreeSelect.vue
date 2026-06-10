<script setup lang="ts">
/**
 * CategoryTreeSelect — Hierarchical category picker with expand/collapse.
 *
 * Renders a tree of categories with expand/collapse for subcategories,
 * search filtering, and selection. Designed for the CategoryTreeOut type.
 *
 * Usage:
 *   <CategoryTreeSelect
 *     :categories="tree"
 *     :model-value="selectedCategoryId"
 *     @select="handleSelect"
 *   />
 */
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
export interface TreeNode {
  id: number;
  name: string;
  icon?: string;
  color?: string;
  is_income?: boolean;
  sort_order?: number;
  subcategories?: TreeNode[];
}

const props = withDefaults(
  defineProps<{
    /** Tree structure data from API. */
    categories: TreeNode[];
    /** Currently selected category ID. */
    modelValue?: number | null;
    /** Placeholder text when nothing is selected. */
    placeholder?: string;
    /** Disable the select. */
    disabled?: boolean;
    /** Show income/expense indicator. */
    showTypeIndicator?: boolean;
    /** Show search filter. */
    searchable?: boolean;
  }>(),
  {
    modelValue: null,
    placeholder: "Select category...",
    disabled: false,
    showTypeIndicator: true,
    searchable: true,
  },
);

const emit = defineEmits<{
  "update:modelValue": [id: number | null];
  select: [node: TreeNode];
}>();

// ─── State ────────────────────────────────────────────────────────────────────

const isOpen = ref(false);
const searchQuery = ref("");
const expandedIds = ref<Set<number>>(new Set());
const containerRef = ref<HTMLElement | null>(null);

// ─── Computed ─────────────────────────────────────────────────────────────────

/** Find the selected node's label for display. */
const selectedLabel = computed(() => {
  if (!props.modelValue) return "";
  const found = findNodeById(props.categories, props.modelValue);
  return found ? getNodePath(props.categories, found) : "";
});

/** Filter tree by search query. */
const filteredTree = computed(() => {
  if (!searchQuery.value) return props.categories;
  return filterTree(props.categories, searchQuery.value.toLowerCase());
});

// ─── Tree Utilities ───────────────────────────────────────────────────────────

function findNodeById(nodes: TreeNode[], id: number): TreeNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.subcategories?.length) {
      const found = findNodeById(node.subcategories, id);
      if (found) return found;
    }
  }
  return null;
}

function getNodePath(nodes: TreeNode[], target: TreeNode, prefix = ""): string {
  for (const node of nodes) {
    const label = prefix ? `${prefix} > ${node.name}` : node.name;
    if (node.id === target.id) return label;
    if (node.subcategories?.length) {
      const found = getNodePath(node.subcategories, target, label);
      if (found) return found;
    }
  }
  return target.name;
}

function filterTree(nodes: TreeNode[], query: string): TreeNode[] {
  const result: TreeNode[] = [];
  for (const node of nodes) {
    const nameMatch = node.name.toLowerCase().includes(query);
    const filteredChildren = node.subcategories
      ? filterTree(node.subcategories, query)
      : [];
    if (nameMatch || filteredChildren.length > 0) {
      result.push({
        ...node,
        subcategories: filteredChildren.length > 0 ? filteredChildren : node.subcategories,
      });
    }
  }
  return result;
}

function toggleExpand(id: number) {
  if (expandedIds.value.has(id)) {
    expandedIds.value.delete(id);
  } else {
    expandedIds.value.add(id);
  }
}

function isExpanded(id: number): boolean {
  return expandedIds.value.has(id) || !!searchQuery.value;
}

function hasChildren(node: TreeNode): boolean {
  return !!(node.subcategories && node.subcategories.length > 0);
}

// ─── Selection ────────────────────────────────────────────────────────────────

function selectNode(node: TreeNode) {
  emit("update:modelValue", node.id);
  emit("select", node);
  isOpen.value = false;
  searchQuery.value = "";
}

function clearSelection() {
  emit("update:modelValue", null);
  isOpen.value = false;
}

function toggleDropdown() {
  if (props.disabled) return;
  isOpen.value = !isOpen.value;
}

// ─── Click Outside ────────────────────────────────────────────────────────────

function handleClickOutside(event: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(event.target as Node)) {
    isOpen.value = false;
    searchQuery.value = "";
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside);
});
</script>

<template>
  <div ref="containerRef" class="relative">
    <!-- Trigger Button -->
    <button
      type="button"
      :disabled="disabled"
      :class="[
        'input-field w-full flex items-center justify-between gap-2 text-left',
        disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
        isOpen ? 'ring-2 ring-cyan-500 border-cyan-500' : '',
      ]"
      @click="toggleDropdown"
    >
      <span
        :class="[
          selectedLabel ? 'text-navy-900 dark:text-navy-100' : 'text-slate-custom-400',
        ]"
      >
        {{ selectedLabel || placeholder }}
      </span>
      <svg
        :class="['h-4 w-4 text-slate-custom-400 transition-transform', isOpen ? 'rotate-180' : '']"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
    </button>

    <!-- Dropdown Panel -->
    <Transition
      enter-active-class="transition duration-150 ease-out"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-100 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div
        v-if="isOpen"
        class="absolute z-50 mt-1 w-full rounded-xl border border-navy-200 dark:border-navy-700 bg-white dark:bg-navy-900 shadow-lg max-h-80 overflow-y-auto"
      >
        <!-- Search -->
        <div v-if="searchable" class="p-2 border-b border-navy-100 dark:border-navy-800">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Filter categories..."
            class="input-field h-8 text-sm w-full"
          />
        </div>

        <!-- Clear Selection -->
        <button
          v-if="modelValue"
          class="w-full text-left px-4 py-2 text-sm text-cyan-600 dark:text-cyan-400 hover:bg-cyan-50 dark:hover:bg-navy-800 transition-colors"
          @click="clearSelection"
        >
          Clear selection
        </button>

        <!-- Tree Nodes -->
        <div class="py-1">
          <template v-for="node in filteredTree" :key="node.id">
            <!-- Node Row -->
            <div
              :class="[
                'flex items-center gap-1 px-4 py-2 text-sm cursor-pointer transition-colors',
                node.id === modelValue
                  ? 'bg-cyan-50 dark:bg-cyan-950/30 text-cyan-700 dark:text-cyan-300'
                  : 'text-navy-900 dark:text-navy-100 hover:bg-cyan-50/50 dark:hover:bg-navy-800/50',
              ]"
              @click="selectNode(node)"
            >
              <!-- Expand/Collapse -->
              <button
                v-if="hasChildren(node)"
                class="p-0.5 rounded hover:bg-navy-100 dark:hover:bg-navy-700 transition-colors"
                @click.stop="toggleExpand(node.id)"
              >
                <svg
                  :class="['h-3.5 w-3.5 text-slate-custom-400 transition-transform', isExpanded(node.id) ? 'rotate-90' : '']"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                </svg>
              </button>
              <span v-else class="w-5" />

              <!-- Color Dot -->
              <span
                v-if="node.color"
                class="h-2.5 w-2.5 rounded-full flex-shrink-0"
                :style="{ backgroundColor: node.color }"
              />

              <!-- Income/Expense Badge -->
              <span
                v-if="showTypeIndicator"
                :class="[
                  'text-[10px] font-bold rounded px-1',
                  node.is_income
                    ? 'text-credit bg-green-50 dark:bg-green-950/30'
                    : 'text-debit bg-red-50 dark:bg-red-950/30',
                ]"
              >
                {{ node.is_income ? "+" : "-" }}
              </span>

              <!-- Name -->
              <span class="truncate">{{ node.name }}</span>
            </div>

            <!-- Subcategories -->
            <div v-if="hasChildren(node) && isExpanded(node.id)" class="ml-6">
              <div
                v-for="child in node.subcategories"
                :key="child.id"
                :class="[
                  'flex items-center gap-1 px-4 py-1.5 text-sm cursor-pointer transition-colors',
                  child.id === modelValue
                    ? 'bg-cyan-50 dark:bg-cyan-950/30 text-cyan-700 dark:text-cyan-300'
                    : 'text-navy-900 dark:text-navy-100 hover:bg-cyan-50/50 dark:hover:bg-navy-800/50',
                ]"
                @click="selectNode(child)"
              >
                <span
                  v-if="child.color"
                  class="h-2 w-2 rounded-full flex-shrink-0"
                  :style="{ backgroundColor: child.color }"
                />
                <span
                  v-if="showTypeIndicator"
                  :class="[
                    'text-[10px] font-bold rounded px-1',
                    child.is_income
                      ? 'text-credit bg-green-50 dark:bg-green-950/30'
                      : 'text-debit bg-red-50 dark:bg-red-950/30',
                  ]"
                >
                  {{ child.is_income ? "+" : "-" }}
                </span>
                <span class="truncate">{{ child.name }}</span>
              </div>
            </div>
          </template>

          <!-- No Results -->
          <div
            v-if="filteredTree.length === 0"
            class="px-4 py-6 text-center text-sm text-slate-custom-500"
          >
            No categories found
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>
