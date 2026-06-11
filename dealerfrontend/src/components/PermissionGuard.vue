<script setup lang="ts">
import { Permission, usePermissions } from '../composables/usePermissions';

const props = defineProps<{
  permission: Permission;
  any?: Permission[];
  all?: Permission[];
  fallback?: string;
}>();

const { can, canAny, canAll } = usePermissions();

const hasAccess = computed(() => {
  if (props.permission) {
    return can(props.permission);
  }
  if (props.any && props.any.length > 0) {
    return canAny(props.any);
  }
  if (props.all && props.all.length > 0) {
    return canAll(props.all);
  }
  return false;
});
</script>

<template>
  <div v-if="hasAccess">
    <slot />
  </div>
  <div v-else-if="fallback" class="text-slate-400 text-sm">
    {{ fallback }}
  </div>
</template>
