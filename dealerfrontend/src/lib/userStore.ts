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
 * Used by useAccess.isDealer and useAppData.isDealerUser without needing
 * to import useAuth (which would re-introduce the cycle).
 */
export function isDealerUser(): boolean {
  const user = sharedUser.value;
  if (!user) return false;
  // Check both common shapes: explicit role field, or is_dealer flag.
  // The /billing/auth/me response includes both for backwards compat.
  return (
    (user as unknown as { role?: string }).role === "dealer" ||
    (user as unknown as { is_dealer?: boolean }).is_dealer === true
  );
}
