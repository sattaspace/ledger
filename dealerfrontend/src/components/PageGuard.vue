<script setup lang="ts">
/**
 * PageGuard — page-level guard wrapper for authenticated app pages.
 *
 * Wraps each tab page's content with:
 *   1. SessionGuard — ensures auth state is restored before rendering
 *   2. PermissionGuard — gates content by plan-level access
 *   3. Triggers bootstrapAppData() on mount
 *
 * Usage in an Astro page:
 *   <PageGuard feature="inventory">
 *     <Inventory ... />
 *   </PageGuard>
 */
import { onMounted, ref } from "vue";
import SessionGuard from "./SessionGuard.vue";
import PermissionGuard from "./PermissionGuard.vue";
import { useAppData } from "../composables/useAppData";
import { ensureAuthenticated, bootstrapAppData } from "../composables/useBootstrap";

interface Props {
  feature?: string;
  module?: string;
  action?: string;
  any?: string[];
  all?: string[];
  fallback?: string;
}

const props = defineProps<Props>();

const isReady = ref(false);

onMounted(async () => {
  // Ensure auth state is resolved. If not authenticated, this redirects
  // to /login (or /dsr/login for DSR portal mode).
  const ok = await ensureAuthenticated();
  if (!ok) return;

  // Trigger bootstrap to load auth + access + dealer context + app data
  // (idempotent — first call wins, subsequent calls return cached)
  bootstrapAppData().then(() => {
    isReady.value = true;
  });
});
</script>

<template>
  <SessionGuard require-auth>
    <PermissionGuard
      :feature="props.feature"
      :module="props.module"
      :action="props.action"
      :any="props.any"
      :all="props.all"
      :fallback="props.fallback"
    >
      <slot v-if="isReady" />
      <div v-else class="p-6 text-center text-slate-500 text-sm">
        <div class="animate-spin h-6 w-6 border-2 border-amber-200 border-t-amber-500 rounded-full mx-auto mb-3"></div>
        Loading...
      </div>
    </PermissionGuard>
  </SessionGuard>
</template>
