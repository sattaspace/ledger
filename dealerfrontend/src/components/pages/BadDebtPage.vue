<script setup lang="ts">
/**
 * BadDebtPage — wrapper for BadDebt.vue.
 */
import { onMounted } from "vue";
import BadDebt from "../BadDebt.vue";
import { useAppData } from "../../composables/useAppData";

const { sales, formatCurrency, ensureLoaded, refreshAll } = useAppData();

onMounted(async () => {
  await ensureLoaded();
});
</script>

<template>
  <BadDebt :sales="sales" :formatCurrency="formatCurrency" @refreshData="refreshAll" />
</template>
