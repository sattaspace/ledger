<script setup lang="ts">
/**
 * ReportsPage — wrapper for Reports.vue.
 */
import { onMounted, ref } from "vue";
import Reports from "../Reports.vue";
import { useAppData } from "../../composables/useAppData";
import { useToasts } from "../../composables/useToasts";
import { dsrService, reportsService } from "../../services/api";

const { summary, dsrs, sales, products, formatCurrency, ensureLoaded, refreshAll } =
  useAppData();
const { triggerToast, triggerErrorToast } = useToasts();

const aiResponse = ref("");
const isAiLoading = ref(false);

onMounted(async () => {
  await ensureLoaded();
});

async function handleAskGemini() {
  isAiLoading.value = true;
  aiResponse.value = "";
  try {
    const res = await reportsService.getAiReconciliation();
    aiResponse.value = res.data.text || "Unable to generate analysis.";
  } catch (err: any) {
    console.error(err);
    aiResponse.value =
      "### ⚠️ AI Assistant offline\nFailed to receive analysis response from Gemini. Check that GEMINI_API_KEY is configured correctly.";
  } finally {
    isAiLoading.value = false;
  }
}

async function handleEditDsr(dsrId: string, dData: any) {
  try {
    const res = await dsrService.updateDsr(dsrId, dData);
    await refreshAll();
    triggerToast("DSR Representative updated!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to update representative. Please try again.");
    throw err;
  }
}

async function handleDeleteDsr(dsrId: string) {
  try {
    await dsrService.deleteDsr(dsrId);
    await refreshAll();
    triggerToast("DSR Representative removed!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to delete representative. Please try again.");
    throw err;
  }
}
</script>

<template>
  <Reports
    :summary="summary"
    :dsrs="dsrs"
    :sales="sales"
    :products="products"
    :aiResponse="aiResponse"
    :isAiLoading="isAiLoading"
    :formatCurrency="formatCurrency"
    :onEditDsr="handleEditDsr"
    :onDeleteDsr="handleDeleteDsr"
    @askGemini="handleAskGemini"
    @refreshData="refreshAll"
  />
</template>
