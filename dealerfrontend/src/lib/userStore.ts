/**
 * userStore — single source of truth for the dealer-side user object.
 *
 * Extracted to break the circular import (audit fix H2):
 *
 *   useAccess.ts  →  (require useAuth)  →  lib/api.ts  →  useAccess.ts
 *
 * The `require()` call throws in ESM bundles (Astro/Vite), so the old
 * `useAccess.isDealer` always returned false. By hoisting the user ref
 * here, `useAccess` can import it directly with no cycle.
 *
 * `useAuth` still owns the public `user` ref it returns from `useAuth()`,
 * but it reads/writes through this singleton so other modules can observe
 * the same state.
 */

import { ref, type Ref } from "vue";
import type { User } from "./types";

export const sharedUser: Ref<User | null> = ref(null);

/** Set the shared user (called by useAuth after /billing/auth/me). */
export function setSharedUser(user: User | null): void {
  sharedUser.value = user;
}

/** Get the shared user ref (read-only for consumers). */
export function getSharedUser(): Ref<User | null> {
  return sharedUser;
}

/**
 * Check if the current user is a dealer (vs. a DSR in portal mode).
 *
 * SattaBase user roles are "owner", "admin", "member" — there is NO
 * "dealer" role. A "dealer" is any SattaBase user with a DealerCore
 * subscription.
 *
 * DSR users (from dealerbackend) have a `user_type` field (e.g. "dsr").
 * SattaBase users do NOT have `user_type`.
 *
 * So the check is:
 *   - If user has `user_type` → it's a DSR → return false
 *   - If user has no `user_type` → it's a SattaBase user (dealer) → return true
 */
export function isDealerUser(): boolean {
  const user = sharedUser.value;
  if (!user) return false;
  // DSR users have user_type set (e.g. "dsr", "Senior_DSR", etc.)
  // SattaBase users do NOT have this field.
  const userType = (user as unknown as { user_type?: string }).user_type;
  if (userType) {
    return false; // DSR
  }
  return true; // SattaBase user = dealer
}
