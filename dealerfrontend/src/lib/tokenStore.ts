/**
 * tokenStore — single source of truth for the dealer-side access token.
 *
 * Extracted from lib/api.ts to break a circular import (audit fix H2):
 *
 *   useAuth.ts  →  lib/api.ts  →  useAccess.ts  →  useAuth.ts  (cycle!)
 *
 * The cycle existed because `useAccess` needed `getAccessToken` from
 * `lib/api.ts`, while `lib/api.ts` needed `setAccessMap` from `useAccess`
 * to inject the `X-Plan-Limits` header. The old workaround was to use
 * CommonJS `require()` inside a try/catch — which throws in ESM bundles
 * (Astro/Vite), silently returning `false` from `isDealer` and friends.
 *
 * Solution: move the token state into this leaf module with no imports.
 * Both `lib/api.ts` and `useAuth.ts` import it directly. The cycle is
 * broken because `useAccess` no longer needs `lib/api.ts` for the token.
 *
 * The token is still IN MEMORY ONLY — never written to localStorage or
 * sessionStorage. Hydrated synchronously from `window.__INITIAL_AUTH_TOKEN__`
 * (set by BaseLayout) on module load.
 */

declare global {
  interface Window {
    /** Short-lived JWT access token minted by the Astro middleware. */
    __INITIAL_AUTH_TOKEN__?: string;
  }
}

let _accessToken: string | null = null;

// Hydrate from server-injected token (set by BaseLayout before this
// module evaluates). Synchronous, runs once per page load.
if (typeof window !== "undefined") {
  const initial = window.__INITIAL_AUTH_TOKEN__;
  if (initial) {
    _accessToken = initial;
  }
}

/** Get the current access token from memory. */
export function getAccessToken(): string | null {
  return _accessToken;
}

/** Store the access token in memory. */
export function setAccessToken(token: string): void {
  _accessToken = token;
}

/** Clear the access token from memory. */
export function clearAccessToken(): void {
  _accessToken = null;
}

/** Check if there's a non-null access token in memory. */
export function hasAccessToken(): boolean {
  return _accessToken !== null;
}
