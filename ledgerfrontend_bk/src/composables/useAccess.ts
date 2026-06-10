/**
 * useAccess — reactive feature-access checking composable.
 */

import { computed, type ComputedRef } from "vue";
import { useAuth } from "./useAuth";

export function useAccess() {
  const { access, isLoading, refetch: refetchAuth } = useAuth();

  /**
   * Check whether a feature or access key is enabled.
   *
   * For boolean keys, returns the boolean value directly.
   * For numeric keys, returns `true` only when the value is > 0.
   * For string keys, returns `false` for empty strings, `"false"`, and `"0"`.
   *
   * **Note on `max_*` keys**: Calling `hasAccess("max_accounts")` returns `false` when the value is `0`,
   * because `0` for a numeric key means "unlimited quota", not "has access". To check whether a user
   * has quota for a feature, use `hasQuota("max_accounts", "accounts")` instead.
   *
   * @param key - The access key to check (e.g., "budgets", "max_accounts")
   */
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

  /**
   * Check whether a user has quota for a `max_*` limit key.
   *
   * Returns `true` when:
   * - The feature boolean key is enabled AND the max value is `0` (unlimited)
   * - The max value is a positive number (finite quota available)
   *
   * Returns `false` when:
   * - The feature boolean key is disabled (e.g., `investments: false` means `max_investments: 0` = disabled)
   * - The max key is not found in the access map
   *
   * @param maxKey - The `max_*` key to check (e.g., "max_accounts", "max_budgets")
   * @param featureKey - Optional boolean feature key (e.g., "accounts", "budgets"). When provided,
   *   returns `false` if the feature is disabled regardless of the max value.
   *
   * @example
   * // Correct way to check if user can create more accounts:
   * const canCreate = hasQuota("max_accounts", "accounts");
   * const maxAccounts = getLimit("max_accounts");
   * const atLimit = maxAccounts.value > 0 && currentCount >= maxAccounts.value;
   */
  function hasQuota(maxKey: string, featureKey?: string): ComputedRef<boolean> {
    return computed(() => {
      const limitValue = access.value[maxKey];
      // If a feature key is provided, check if the feature is enabled at all
      if (featureKey) {
        const featureValue = access.value[featureKey];
        if (featureValue === false || featureValue === 0) return false;
      }
      // 0 means unlimited (has quota), any positive number means finite quota
      if (typeof limitValue === "number") return limitValue >= 0;
      if (limitValue === undefined || limitValue === null) return false;
      return Boolean(limitValue);
    });
  }

  const accessKeys: ComputedRef<string[]> = computed(() => Object.keys(access.value));

  return {
    hasAccess,
    hasQuota,
    getAccess,
    getLimit,
    accessKeys,
    isLoading,
    refetch: refetchAuth,
  };
}
