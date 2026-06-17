<script setup lang="ts">
/**
 * SuppliersPage — wrapper for Suppliers.vue.
 */
import { onMounted } from "vue";
import Suppliers from "../Suppliers.vue";
import { useAppData } from "../../composables/useAppData";
import { useToasts } from "../../composables/useToasts";
import { supplierService } from "../../services/api";

const { suppliers, categories, formatCurrency, maxSuppliers, ensureLoaded, refreshAll } =
  useAppData();
const { triggerToast, triggerErrorToast } = useToasts();

onMounted(async () => {
  await ensureLoaded();
});

async function handleAddSupplier(sData: any) {
  if (maxSuppliers.value > 0 && suppliers.value.length >= maxSuppliers.value) {
    triggerErrorToast(
      `Supplier limit reached (${maxSuppliers.value} suppliers). Upgrade your plan to add more.`,
    );
    throw new Error(`Supplier limit reached (${maxSuppliers.value} suppliers)`);
  }
  try {
    const res = await supplierService.createSupplier(sData);
    await refreshAll();
    triggerToast("Supplier added successfully!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to add supplier. Please try again.");
    throw err;
  }
}

async function handleEditSupplier(supplierId: string, sData: any) {
  try {
    const res = await supplierService.updateSupplier(supplierId, sData);
    await refreshAll();
    triggerToast("Supplier updated!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to update supplier. Please try again.");
    throw err;
  }
}

async function handleDeleteSupplier(supplierId: string) {
  try {
    await supplierService.deleteSupplier(supplierId);
    await refreshAll();
    triggerToast("Supplier removed!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to delete supplier. Please try again.");
    throw err;
  }
}
</script>

<template>
  <Suppliers
    :suppliers="suppliers"
    :categories="categories"
    :formatCurrency="formatCurrency"
    :onAddSupplier="handleAddSupplier"
    :onEditSupplier="handleEditSupplier"
    :onDeleteSupplier="handleDeleteSupplier"
    @refreshData="refreshAll"
  />
</template>
