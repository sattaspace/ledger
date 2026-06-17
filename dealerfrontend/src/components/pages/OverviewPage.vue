<script setup lang="ts">
/**
 * OverviewPage — wrapper that pulls shared data from useAppData and
 * passes it to the Overview.vue presentation component.
 *
 * Handles navigation via window.location.href (MPA pattern).
 */
import { onMounted } from "vue";
import Overview from "../Overview.vue";
import { useAppData } from "../../composables/useAppData";
import { useToasts } from "../../composables/useToasts";

const { summary, sales, formatCurrency, ensureLoaded, refreshAll } = useAppData();
const { triggerToast, triggerErrorToast } = useToasts();

onMounted(async () => {
  await ensureLoaded();
});

function handleNavigate(tab: string) {
  // Map old tab ids to new routes
  const routeMap: Record<string, string> = {
    overview: "/dashboard",
    team: "/team",
    inventory: "/inventory",
    suppliers: "/suppliers",
    sales: "/sales",
    collections: "/collections",
    "bad-debt": "/bad-debt",
    reports: "/reports",
  };
  const route = routeMap[tab] || "/dashboard";
  window.location.href = route;
}

function handleQuickAction(actionType: string) {
  if (actionType === "restock") {
    window.location.href = "/inventory";
  } else if (actionType === "vehicle-sale" || actionType === "dsr-sale") {
    window.location.href = "/sales";
  }
}

// Silence unused warnings — toasts available for future use
void triggerToast;
void triggerErrorToast;
void refreshAll;
</script>

<template>
  <Overview
    :summary="summary"
    :sales="sales"
    :formatCurrency="formatCurrency"
    @navigate="handleNavigate"
    @quickAction="handleQuickAction"
  />
</template>
