<script setup lang="ts">
/**
 * EmptyState — No-data illustration with optional CTA button.
 *
 * Usage:
 *   <EmptyState
 *     title="No transactions yet"
 *     description="Record your first transaction to get started."
 *     action-label="Add Transaction"
 *     @action="showCreateForm = true"
 *   />
 */

const props = withDefaults(
  defineProps<{
    /** Main heading text. */
    title: string;
    /** Supporting description. */
    description?: string;
    /** Icon name: 'inbox' | 'search' | 'folder' | 'credit-card' | 'chart'. */
    icon?: "inbox" | "search" | "folder" | "credit-card" | "chart";
    /** CTA button label. Hides button if empty. */
    actionLabel?: string;
  }>(),
  {
    description: "",
    icon: "inbox",
    actionLabel: "",
  },
);

const emit = defineEmits<{
  action: [];
}>();
</script>

<template>
  <div class="flex flex-col items-center justify-center py-12 px-4 text-center">
    <!-- Icon -->
    <div class="mb-4 rounded-full bg-navy-100 dark:bg-navy-800 p-4">
      <!-- Inbox -->
      <svg v-if="icon === 'inbox'" class="h-8 w-8 text-slate-custom-500 dark:text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M5 3a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 2h10v7h-2l-1 2H8l-1-2H5V5z" clip-rule="evenodd" />
      </svg>
      <!-- Search -->
      <svg v-else-if="icon === 'search'" class="h-8 w-8 text-slate-custom-500 dark:text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
      </svg>
      <!-- Folder -->
      <svg v-else-if="icon === 'folder'" class="h-8 w-8 text-slate-custom-500 dark:text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
      </svg>
      <!-- Credit Card -->
      <svg v-else-if="icon === 'credit-card'" class="h-8 w-8 text-slate-custom-500 dark:text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
        <path d="M4 4a2 2 0 00-2 2v1h16V6a2 2 0 00-2-2H4zM2 10v4a2 2 0 002 2h12a2 2 0 002-2v-4H2zm4 2h2a1 1 0 100-2H6a1 1 0 100 2z" />
      </svg>
      <!-- Chart -->
      <svg v-else class="h-8 w-8 text-slate-custom-500 dark:text-slate-custom-400" viewBox="0 0 20 20" fill="currentColor">
        <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
      </svg>
    </div>

    <!-- Title -->
    <h3 class="text-lg font-semibold text-navy-900 dark:text-navy-100 mb-1">
      {{ title }}
    </h3>

    <!-- Description -->
    <p
      v-if="description"
      class="text-sm text-slate-custom-600 dark:text-slate-custom-400 max-w-sm mb-4"
    >
      {{ description }}
    </p>

    <!-- CTA Button -->
    <button
      v-if="actionLabel"
      class="btn-primary"
      @click="emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>
