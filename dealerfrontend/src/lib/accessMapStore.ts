/**
 * accessMapStore — single source of truth for the dealer-side access map.
 *
 * Extracted to break the circular import (audit fix H2):
 *
 *   useAccess.ts  →  (require useAuth)  →  lib/api.ts  →  useAccess.ts
 *
 * Previously, lib/api.ts's buildHeaders() used `require("../composables/useAccess")`
 * to read the access map for the X-Plan-Limits header. In ESM (Astro/Vite),
 * `require()` is undefined and the catch block silently skipped the header
 * injection — so the dealerbackend never received the access map from this
 * code path, weakening server-side plan-limit enforcement.
 *
 * Now useAccess writes the sanitized map to this leaf module, and
 * lib/api.ts reads it from here. No cycle, no require().
 */

import { ref, type Ref } from "vue";

export type AccessMapValue = boolean | number | string;
export type AccessMap = Record<string, AccessMapValue>;

const _accessMap: Ref<AccessMap> = ref({});

/** Set the access map (called by useAccess.setAccessMap). */
export function setAccessMapValue(map: AccessMap): void {
  _accessMap.value = map;
}

/** Clear the access map (called on logout). */
export function clearAccessMapValue(): void {
  _accessMap.value = {};
}

/**
 * Read the current access map. Returns a plain object (not a ref) —
 * callers that need reactivity should use useAccess().access instead.
 */
export function getAccessMap(): AccessMap {
  return _accessMap.value;
}

/** Reactive ref to the access map (for composables that need reactivity). */
export function getAccessMapRef(): Ref<AccessMap> {
  return _accessMap;
}
