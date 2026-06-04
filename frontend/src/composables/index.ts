/**
 * Vue Composables — barrel export for all shared composables.
 *
 * Composables extract duplicated patterns from Vue components into
 * reusable, reactive functions. This reduces code duplication,
 * improves maintainability, and provides shared state across components.
 *
 * Available composables:
 *   useAuth()             — Shared auth + billing state (user, subscription, access, error, refetch)
 *   useSubscription()     — Shared subscription list state (deduplicates concurrent fetches)
 *   useProducts()         — Shared product catalog state (deduplicates concurrent fetches, caches details + matrices)
 *   useAccess()           — Reactive feature-access checking (hasAccess, getAccess, accessKeys)
 *   useBillingRedirect()  — Detect billing return from Sattabase (triggers useAuth refetch)
 *   usePasswordStrength() — Password validation + strength indicator
 *   useCooldownTimer()    — Countdown timer for OTP resend
 *   useOtpInput()         — Multi-digit OTP input handling
 *   useFormErrors()       — Field-level + general error management
 *   useAsyncAction()      — Loading/error state for async operations
 *   useMediaQuery()       — Reactive CSS media query matching
 *   useAdminGuard()       — Client-side admin route protection (is_staff check)
 */

export { useAuth } from "./useAuth";
export { useSubscription } from "./useSubscription";
export { useProducts } from "./useProducts";
export { useAccess } from "./useAccess";
export { useBillingRedirect } from "./useBillingRedirect";
export { usePasswordStrength } from "./usePasswordStrength";
export type {
  PasswordChecks,
  PasswordStrengthResult,
} from "./usePasswordStrength";
export { useCooldownTimer } from "./useCooldownTimer";
export { useOtpInput } from "./useOtpInput";
export { useFormErrors } from "./useFormErrors";
export { useAsyncAction } from "./useAsyncAction";
export type { AsyncActionOptions } from "./useAsyncAction";
export { useMediaQuery } from "./useMediaQuery";
export { useAdminGuard } from "./useAdminGuard";
export { useTransactions } from "./useTransactions";
export { useAdminData } from "./useAdminData";
