<script setup lang="ts">
/**
 * CollectionsPage — wrapper for Collections.vue.
 */
import { onMounted } from "vue";
import Collections from "../Collections.vue";
import { useAppData } from "../../composables/useAppData";
import { useToasts } from "../../composables/useToasts";
import { salesService } from "../../services/api";

const { sales, formatCurrency, ensureLoaded, refreshAll } = useAppData();
const { triggerToast, triggerErrorToast } = useToasts();

onMounted(async () => {
  await ensureLoaded();
});

async function handleCollectPayment(saleId: string, amount: number, receivedBy: string) {
  try {
    const res = await salesService.collectPayment(saleId, { amount, receivedBy });
    await refreshAll();
    triggerToast("Ledger payment collection recorded!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to record payment. Please try again.");
    throw err;
  }
}

async function handleCloseWithDue(saleId: string) {
  try {
    const res = await salesService.closeSaleWithDue(saleId);
    await refreshAll();
    triggerToast("Invoice closed with remaining balance written off.");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to close invoice. Please try again.");
    throw err;
  }
}
</script>

<template>
  <Collections
    :sales="sales"
    :formatCurrency="formatCurrency"
    :onCollectPayment="handleCollectPayment"
    :onCloseWithDue="handleCloseWithDue"
    @refreshData="refreshAll"
  />
</template>
