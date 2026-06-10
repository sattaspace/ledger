<script setup lang="ts">
import { Trash2, Download, Users } from 'lucide-vue-next';

defineProps<{
  selectedCount: number;
}>();

defineEmits<{
  (e: 'delete'): void;
  (e: 'export'): void;
  (e: 'reassign'): void;
}>();
</script>

<template>
  <div v-if="selectedCount > 0" class="bulk-actions-bar">
    <div class="bulk-info">
      <span class="bulk-count">{{ selectedCount }}</span>
      <span class="bulk-label">items selected</span>
    </div>
    <div class="bulk-buttons">
      <button @click="$emit('export')" class="bulk-btn export">
        <Download class="w-4 h-4" />
        Export
      </button>
      <button @click="$emit('reassign')" class="bulk-btn reassign">
        <Users class="w-4 h-4" />
        Reassign
      </button>
      <button @click="$emit('delete')" class="bulk-btn delete">
        <Trash2 class="w-4 h-4" />
        Delete
      </button>
    </div>
  </div>
</template>

<style scoped>
.bulk-actions-bar {
  position: sticky;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(135deg, #1e3a8a, #3b82f6);
  padding: 1rem 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 -4px 20px rgba(0,0,0,0.15);
  z-index: 100;
  border-radius: 12px 12px 0 0;
}

.bulk-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: white;
}

.bulk-count {
  background: white;
  color: #1e3a8a;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
}

.bulk-label {
  font-weight: 500;
  font-size: 14px;
}

.bulk-buttons {
  display: flex;
  gap: 0.75rem;
}

.bulk-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s;
  cursor: pointer;
  border: none;
}

.bulk-btn.export {
  background: rgba(255,255,255,0.2);
  color: white;
}

.bulk-btn.export:hover {
  background: rgba(255,255,255,0.3);
}

.bulk-btn.reassign {
  background: rgba(255,255,255,0.2);
  color: white;
}

.bulk-btn.reassign:hover {
  background: rgba(255,255,255,0.3);
}

.bulk-btn.delete {
  background: #fee2e2;
  color: #dc2626;
}

.bulk-btn.delete:hover {
  background: #fecaca;
}
</style>
