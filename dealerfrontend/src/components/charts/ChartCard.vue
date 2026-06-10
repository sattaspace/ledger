<script setup lang="ts">
defineProps<{
  title: string;
  subtitle?: string;
  noPadding?: boolean;
}>();
</script>

<template>
  <div class="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
    <div v-if="title" class="px-5 pt-5 pb-2">
      <h3 class="font-display font-bold text-slate-800 text-sm">{{ title }}</h3>
      <p v-if="subtitle" class="text-xs text-slate-400 mt-0.5">{{ subtitle }}</p>
    </div>
    <div :class="noPadding ? '' : 'px-4 pb-4'" class="chart-wrapper">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.chart-wrapper {
  position: relative;
  min-height: 200px;
}
</style>
