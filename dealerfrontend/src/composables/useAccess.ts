/**
 * useAccess — reactive feature-access checking composable.
 */

import { computed, type ComputedRef } from "vue";
import { useAuth } from "./useAuth";

export function useAccess() {
  const { access, isLoading, refetch: refetchAuth } = useAuth();

  function hasAccess(key: string): ComputedRef<boolean> {
    return computed(() => {
      const value = access.value[key];
      if (value === undefined || value === null) return false;
      if (typeof value === "boolean") return value;
      if (typeof value === "number") return value > 0;
      if (typeof value === "string") {
        return value !== "" && value !== "false" && value !== "0";
      }
      return Boolean(value);
    });
  }

  function getAccess<T extends boolean | number | string>(
    key: string,
    defaultValue?: T,
  ): ComputedRef<T | undefined> {
    return computed(() => {
      const value = access.value[key];
      if (value === undefined || value === null) return defaultValue;
      return value as T;
    });
  }

  function getLimit(key: string, defaultValue = 0): ComputedRef<number> {
    return computed(() => {
      const value = access.value[key];
      if (value === undefined || value === null) return defaultValue;
      const num = Number(value);
      return isNaN(num) ? defaultValue : num;
    });
  }

  const accessKeys: ComputedRef<string[]> = computed(() => Object.keys(access.value));

  return {
    hasAccess,
    getAccess,
    getLimit,
    accessKeys,
    isLoading,
    refetch: refetchAuth,
  };
}
