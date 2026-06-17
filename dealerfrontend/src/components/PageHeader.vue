<script setup lang="ts">
/**
 * PageHeader — page-specific header with title, subtitle, and optional actions.
 *
 * Used by every tab page (inventory, sales, etc.) for consistent layout.
 * The "Add Sales Rep" button emits an event that opens the AddRepModal
 * (which lives in AppFooter.vue). We use a custom event on window to
 * communicate between the page component and the persistent AppFooter.
 */
import { onMounted, onUnmounted, ref } from "vue";

interface Props {
  title: string;
  subtitle?: string;
  showAddRep?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  subtitle: "",
  showAddRep: false,
});

const showAddRepBtn = ref(props.showAddRep);

function openAddRep() {
  // Dispatch a global event that AppFooter.vue listens for
  window.dispatchEvent(new CustomEvent("dealercore:open-add-rep"));
}

onMounted(() => {
  // Listen for the "open add rep" event so external buttons (e.g. in tabs) can trigger it
  window.addEventListener("dealercore:open-add-rep", () => {
    /* no-op — AppFooter listens and opens the modal */
  });
});
</script>

<template>
  <div class="flex items-center justify-between mb-4">
    <div>
      <h2 class="text-2xl font-bold text-slate-800">{{ title }}</h2>
      <p v-if="subtitle" class="text-sm text-slate-500">{{ subtitle }}</p>
    </div>
    <button
      v-if="showAddRepBtn"
      @click="openAddRep"
      class="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium transition"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
      </svg>
      Add Sales Rep
    </button>
  </div>
</template>
