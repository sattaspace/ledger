<script setup lang="ts">
/**
 * InventoryPage — wrapper for Inventory.vue.
 *
 * Pulls shared data from useAppData and provides action handlers that
 * call the centralized services and refresh the shared cache.
 */
import { onMounted } from "vue";
import Inventory from "../Inventory.vue";
import { useAppData } from "../../composables/useAppData";
import { useToasts } from "../../composables/useToasts";
import {
  inventoryService,
} from "../../services/api";

const {
  products,
  suppliers,
  restocksList,
  dsrs,
  brands,
  categories,
  formatCurrency,
  maxProducts,
  ensureLoaded,
  refreshAll,
} = useAppData();

const { triggerToast, triggerErrorToast } = useToasts();

onMounted(async () => {
  await ensureLoaded();
});

async function handleAddProduct(pData: any) {
  if (maxProducts.value > 0 && products.value.length >= maxProducts.value) {
    triggerErrorToast(
      `Product limit reached (${maxProducts.value} items). Upgrade your plan to add more products.`,
    );
    throw new Error(`Product limit reached (${maxProducts.value} items)`);
  }
  try {
    const res = await inventoryService.addProduct(pData);
    await refreshAll();
    triggerToast("Product added successfully!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to add product. Please try again.");
    throw err;
  }
}

async function handleRestockLogged(data: any) {
  try {
    const res = await inventoryService.restockProduct(data);
    await refreshAll();
    triggerToast("Stock Restocked successfully!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to restock. Please try again.");
    throw err;
  }
}

async function handleEditProduct(productId: string, pData: any) {
  try {
    const res = await inventoryService.editProduct(productId, pData);
    await refreshAll();
    triggerToast("Product updated successfully!");
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to update product. Please try again.");
    throw err;
  }
}

async function handleDeleteProduct(productId: string) {
  try {
    await inventoryService.deleteProduct(productId);
    await refreshAll();
    triggerToast("Product deleted successfully!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to delete product. It may have existing sales.");
    throw err;
  }
}

async function handleAddBrand(name: string) {
  try {
    await inventoryService.createBrand({ name });
    await refreshAll();
    triggerToast("Brand added!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to add brand.");
    throw err;
  }
}

async function handleDeleteBrand(id: string) {
  try {
    await inventoryService.deleteBrand(id);
    await refreshAll();
    triggerToast("Brand removed.");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to delete brand.");
    throw err;
  }
}

async function handleAddCategory(name: string) {
  try {
    await inventoryService.createCategory({ name });
    await refreshAll();
    triggerToast("Category added!");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to add category.");
    throw err;
  }
}

async function handleDeleteCategory(id: string) {
  try {
    await inventoryService.deleteCategory(id);
    await refreshAll();
    triggerToast("Category removed.");
  } catch (err: any) {
    triggerErrorToast(err.message || "Failed to delete category.");
    throw err;
  }
}
</script>

<template>
  <Inventory
    :products="products"
    :suppliers="suppliers"
    :restocks="restocksList"
    :dsrs="dsrs"
    :brands="brands"
    :categories="categories"
    :formatCurrency="formatCurrency"
    :onAddProduct="handleAddProduct"
    :onRestock="handleRestockLogged"
    :onEditProduct="handleEditProduct"
    :onDeleteProduct="handleDeleteProduct"
    :onAddBrand="handleAddBrand"
    :onDeleteBrand="handleDeleteBrand"
    :onAddCategory="handleAddCategory"
    :onDeleteCategory="handleDeleteCategory"
    @refreshData="refreshAll"
  />
</template>
