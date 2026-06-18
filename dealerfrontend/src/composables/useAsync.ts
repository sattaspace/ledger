/**
 * DEALERCORE v3.0 — Async Operation Utilities
 *
 * Centralized async utilities for consistent error handling,
 * loading states, and request management.
 */

import { ref, shallowRef, type Ref } from "vue";

export interface UseAsyncOptions<T> {
  /** Callback on successful execution */
  onSuccess?: (data: T) => void;
  /** Callback on error */
  onError?: (error: Error) => void;
  /** Default error message if none provided */
  defaultErrorMessage?: string;
  /** Whether to show alert on error */
  showErrorAlert?: boolean;
}

export interface UseAsyncState<T> {
  /** Whether an operation is in progress */
  isLoading: Ref<boolean>;
  /** Error message if operation failed */
  error: Ref<string | null>;
  /**
   * Last successful result.
   *
   * Audit fix TS-8 (revised): uses `shallowRef` instead of `ref` for the
   * data field. `ref<T | null>(null)` returns `Ref<UnwrapRef<T | null>>`
   * which is a complex union type for generic T — TypeScript can't prove
   * it's assignable to `Ref<T | null>`. `shallowRef<T | null>(null)`
   * returns `ShallowRef<T | null>` which IS directly assignable to
   * `Ref<T | null>` (ShallowRef extends Ref).
   *
   * This is also more correct semantically: we always do
   * `data.value = result` (whole-value replacement), never deep mutation,
   * so shallow reactivity is sufficient and more efficient.
   */
  data: Ref<T | null>;
  /** Execute the async function */
  execute: (fn: () => Promise<T>) => Promise<T | null>;
  /** Reset state */
  reset: () => void;
}

/**
 * Composable for managing async operations with loading and error states
 *
 * @example
 * ```ts
 * const { isLoading, error, execute } = useAsync<Product[]>();
 *
 * async function loadProducts() {
 *   const products = await execute(async () => {
 *     const res = await api.getProducts();
 *     // Audit fix TS-13: updated JSDoc example — services/apiClient.ts
 *     // throws ApiError on non-2xx (no `res.error` field on ApiResponse).
 *     // The execute() catch block handles errors automatically.
 *     return res.data;
 *   });
 *
 *   if (products) {
 *     // Handle success
 *   }
 * }
 * ```
 */
export function useAsync<T = any>(
  options: UseAsyncOptions<T> = {},
): UseAsyncState<T> {
  const isLoading = ref(false);
  const error = ref<string | null>(null);
  // Audit fix TS-8 (revised): use shallowRef instead of ref. See the
  // interface docstring above for the full explanation.
  const data = shallowRef<T | null>(null);

  async function execute(fn: () => Promise<T>): Promise<T | null> {
    isLoading.value = true;
    error.value = null;

    try {
      const result = await fn();
      data.value = result;
      options.onSuccess?.(result);
      return result;
    } catch (err: any) {
      const errorMessage =
        err?.message ||
        options.defaultErrorMessage ||
        "An unexpected error occurred";
      error.value = errorMessage;

      console.error("Async operation failed:", err);

      if (options.showErrorAlert !== false) {
        alert(errorMessage);
      }

      options.onError?.(err);
      return null;
    } finally {
      isLoading.value = false;
    }
  }

  function reset() {
    isLoading.value = false;
    error.value = null;
    data.value = null;
  }

  return {
    isLoading,
    error,
    data,
    execute,
    reset,
  };
}

/**
 * Execute an async function with automatic error handling
 * Standalone version for one-off operations
 *
 * @example
 * ```ts
 * const products = await withErrorHandling(
 *   () => api.getProducts(),
 *   { onError: (err) => console.error(err) }
 * );
 * ```
 */
export async function withErrorHandling<T>(
  fn: () => Promise<T>,
  options: UseAsyncOptions<T> = {},
): Promise<T | null> {
  try {
    const result = await fn();
    options.onSuccess?.(result);
    return result;
  } catch (err: any) {
    const errorMessage =
      err?.message ||
      options.defaultErrorMessage ||
      "An unexpected error occurred";

    console.error("Operation failed:", err);

    if (options.showErrorAlert !== false) {
      alert(errorMessage);
    }

    options.onError?.(err);
    return null;
  }
}

/**
 * Debounce function for search inputs and similar
 */
export function useDebounce<T extends (...args: any[]) => void>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      fn(...args);
    }, delay);
  };
}

/**
 * Throttle function for scroll/resize handlers
 */
export function useThrottle<T extends (...args: any[]) => void>(
  fn: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}
