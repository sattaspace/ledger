<script setup lang="ts">
/**
 * SalesPage — wrapper for Sales.vue.
 */
import { onMounted } from "vue";
import Sales from "../Sales.vue";
import { useAppData } from "../../composables/useAppData";
import { useToasts } from "../../composables/useToasts";
import { salesService } from "../../services/api";

const { products, sales, dsrs, formatCurrency, ensureLoaded, refreshAll } = useAppData();
const { triggerToast, triggerErrorToast } = useToasts();

onMounted(async () => {
  await ensureLoaded();
});

async function handleAddSale(sData: any) {
  try {
    const res = await salesService.createSale(sData);
    await refreshAll();
    triggerToast("Billing Sale logged successfully!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to create sale. Please try again.");
    throw err;
  }
}

async function handleAddBulkSales(bulkData: any) {
  try {
    const res = await salesService.createBulkSales(bulkData);
    await refreshAll();
    triggerToast("Bulk dispatch roster logged successfully!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to create bulk sales. Please try again.");
    throw err;
  }
}

async function handleVoidSale(saleId: string, force = false) {
  try {
    await salesService.voidSale(saleId, force);
    await refreshAll();
    triggerToast("Sale voided — stock restored.");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to void sale.");
    throw err;
  }
}

async function handleEditSale(saleId: string, data: any) {
  try {
    await salesService.editSale(saleId, data);
    await refreshAll();
    triggerToast("Sale updated!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to update sale.");
    throw err;
  }
}

async function handleReturnSaleItem(saleId: string, data: any) {
  try {
    await salesService.returnSaleItem(saleId, data);
    await refreshAll();
    triggerToast("Product returned — stock restored!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to process return.");
    throw err;
  }
}
</script>

<template>
  <Sales
    :products="products"
    :sales="sales"
    :dsrs="dsrs"
    :formatCurrency="formatCurrency"
    :onAddSale="handleAddSale"
    :onAddBulkSales="handleAddBulkSales"
    :onVoidSale="handleVoidSale"
    :onEditSale="handleEditSale"
    :onReturnItem="handleReturnSaleItem"
    @refreshData="refreshAll"
  />
</template>
