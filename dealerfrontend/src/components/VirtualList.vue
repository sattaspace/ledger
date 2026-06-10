<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

const props = defineProps<{
  items: any[];
  itemHeight: number;
  overscan?: number;
}>();

const containerRef = ref<HTMLElement | null>(null);
const scrollTop = ref(0);
const containerHeight = ref(0);

const overscan = computed(() => props.overscan || 5);
const totalHeight = computed(() => props.items.length * props.itemHeight);

const visibleItems = computed(() => {
  if (!containerHeight.value) return [];
  
  const startIdx = Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - overscan.value);
  const visibleCount = Math.ceil(containerHeight.value / props.itemHeight) + (overscan.value * 2);
  const endIdx = Math.min(props.items.length, startIdx + visibleCount);
  
  return props.items.slice(startIdx, endIdx).map((item, idx) => ({
    item,
    index: startIdx + idx,
    style: {
      position: 'absolute' as const,
      top: `${(startIdx + idx) * props.itemHeight}px`,
      left: 0,
      right: 0,
      height: `${props.itemHeight}px`,
    }
  }));
});

const onScroll = (e: Event) => {
  scrollTop.value = (e.target as HTMLElement).scrollTop;
};

onMounted(() => {
  if (containerRef.value) {
    containerHeight.value = containerRef.value.clientHeight;
    const resizeObserver = new ResizeObserver((entries) => {
      containerHeight.value = entries[0].contentRect.height;
    });
    resizeObserver.observe(containerRef.value);
  }
});
</script>

<template>
  <div 
    ref="containerRef"
    class="virtual-container"
    @scroll="onScroll"
  >
    <div class="virtual-content" :style="{ height: `${totalHeight}px` }">
      <div
        v-for="{ item, index, style } in visibleItems"
        :key="index"
        class="virtual-item"
        :style="style"
      >
        <slot :item="item" :index="index" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.virtual-container {
  height: 100%;
  max-height: 600px;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}

.virtual-content {
  position: relative;
}

.virtual-item {
  width: 100%;
}
</style>
