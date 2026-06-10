<script setup lang="ts">
/**
 * LoadingSkeleton — Content placeholder with shimmer animation.
 *
 * Provides skeleton loading states matching common page layouts:
 * table rows, card grids, and detail views.
 *
 * Usage:
 *   <LoadingSkeleton type="table" :rows="5" />
 *   <LoadingSkeleton type="card" :rows="3" />
 *   <LoadingSkeleton type="detail" />
 */

const props = withDefaults(
  defineProps<{
    /** Number of skeleton rows/items. */
    rows?: number;
    /** Layout type: 'table' | 'card' | 'detail'. */
    type?: "table" | "card" | "detail";
  }>(),
  {
    rows: 5,
    type: "table",
  },
);
</script>

<template>
  <!-- Table Skeleton -->
  <div v-if="type === 'table'" class="w-full">
    <!-- Header -->
    <div class="flex gap-4 px-4 py-3 bg-navy-50 dark:bg-navy-900">
      <div v-for="i in 4" :key="i" class="skeleton h-4 rounded flex-1" />
    </div>
    <!-- Rows -->
    <div v-for="row in rows" :key="row" class="flex gap-4 px-4 py-3 border-t border-navy-100 dark:border-navy-800">
      <div v-for="col in 4" :key="col" class="skeleton h-4 rounded flex-1" :style="{ width: `${50 + Math.random() * 40}%` }" />
    </div>
  </div>

  <!-- Card Grid Skeleton -->
  <div v-else-if="type === 'card'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
    <div v-for="i in rows" :key="i" class="card p-6 space-y-3">
      <div class="skeleton h-5 w-3/4 rounded" />
      <div class="skeleton h-4 w-1/2 rounded" />
      <div class="skeleton h-8 w-1/3 rounded" />
      <div class="flex gap-2 pt-2">
        <div class="skeleton h-6 w-16 rounded-full" />
        <div class="skeleton h-6 w-12 rounded-full" />
      </div>
    </div>
  </div>

  <!-- Detail View Skeleton -->
  <div v-else class="space-y-6">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <div class="skeleton h-12 w-12 rounded-xl" />
      <div class="flex-1 space-y-2">
        <div class="skeleton h-6 w-1/3 rounded" />
        <div class="skeleton h-4 w-1/4 rounded" />
      </div>
    </div>
    <!-- Stats Row -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div v-for="i in 4" :key="i" class="card p-4">
        <div class="skeleton h-3 w-1/2 rounded mb-2" />
        <div class="skeleton h-6 w-2/3 rounded" />
      </div>
    </div>
    <!-- Content Area -->
    <div class="card p-6">
      <div class="skeleton h-5 w-1/4 rounded mb-4" />
      <div class="space-y-3">
        <div v-for="i in 5" :key="i" class="flex gap-4">
          <div class="skeleton h-4 rounded flex-1" :style="{ width: `${40 + Math.random() * 50}%` }" />
          <div class="skeleton h-4 w-20 rounded" />
        </div>
      </div>
    </div>
  </div>
</template>
