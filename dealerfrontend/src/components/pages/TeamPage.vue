<script setup lang="ts">
/**
 * TeamPage — Team management page.
 *
 * Wraps DsrManagementPanel.vue with the page header and "Add Sales Rep" button
 * that opens the AddRepModal (rendered globally by AppFooter).
 */
import { onMounted, ref } from "vue";
import { UserCircle } from "lucide-vue-next";
import DsrManagementPanel from "../DsrManagementPanel.vue";
import PageHeader from "../PageHeader.vue";
import { useAppData } from "../../composables/useAppData";

const { refreshAll, ensureLoaded } = useAppData();
const dsrRosterRef = ref<{ fetchData: () => Promise<void> } | null>(null);

onMounted(async () => {
  await ensureLoaded();
});

function openAddRep() {
  // Dispatch a global event that AppFooter listens for
  window.dispatchEvent(new CustomEvent("dealercore:open-add-rep"));
}

function onAdded() {
  refreshAll();
  dsrRosterRef.value?.fetchData?.();
}
</script>

<template>
  <div class="p-4 md:p-6 space-y-6">
    <PageHeader
      title="Team Management"
      subtitle="Manage your sales representatives"
      :show-add-rep="true"
    />
    <DsrManagementPanel ref="dsrRosterRef" @refresh="refreshAll" />
  </div>
</template>
