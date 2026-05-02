/**
 * Token store interface for persisting user tokens across requests.
 *
 * The SDK uses this for auto-refresh. Implement this interface to integrate
 * with your preferred storage backend (localStorage, sessionStorage, cookies,
 * Redis, database, etc.).
 */

import type { TokenPair } from "./models.js";

/**
 * Token storage interface.
 *
 * Implement this to persist tokens across requests or page reloads.
 */
export interface TokenStore {
  /** Retrieve stored tokens for a user. */
  getTokens(userId: string): TokenPair | null | Promise<TokenPair | null>;
  /** Store tokens for a user. */
  setTokens(userId: string, tokens: TokenPair): void | Promise<void>;
  /** Delete stored tokens for a user. */
  deleteTokens(userId: string): void | Promise<void>;
}

/**
 * Extended token store interface with internal helper methods.
 * The `InMemoryTokenStore` implements this automatically.
 *
 * @internal
 */
export interface TokenStoreWithLookup extends TokenStore {
  /** Get the first available token pair (for auto-refresh when userId context is unavailable). */
  getFirstTokenPair(): TokenPair | null;
  /** Find a userId by matching the refresh token value. */
  getUserIdByRefresh(refreshToken: string): string | null;
}

/**
 * In-memory token store for development and testing.
 *
 * Not suitable for production — tokens are lost on page refresh.
 * Implements `TokenStoreWithLookup` for auto-refresh support.
 *
 * @example
 * ```ts
 * const store = new InMemoryTokenStore();
 * const client = new SattabaseClient(config, store);
 *
 * await client.auth.login("user@example.com", "password");
 * // tokens are auto-stored by the client
 * ```
 */
export class InMemoryTokenStore implements TokenStoreWithLookup {
  private store = new Map<string, TokenPair>();

  getTokens(userId: string): TokenPair | null {
    return this.store.get(userId) ?? null;
  }

  setTokens(userId: string, tokens: TokenPair): void {
    this.store.set(userId, tokens);
  }

  deleteTokens(userId: string): void {
    this.store.delete(userId);
  }

  /** Get the first available token pair from the store. */
  getFirstTokenPair(): TokenPair | null {
    const first = this.store.values().next();
    return first.done ? null : first.value;
  }

  /** Find a userId by matching refresh token value. */
  getUserIdByRefresh(refreshToken: string): string | null {
    for (const [userId, tokens] of this.store) {
      if (tokens.refresh === refreshToken) return userId;
    }
    return null;
  }
}

/**
 * Browser localStorage token store.
 *
 * Persists tokens across page refreshes. Suitable for SPAs where the
 * user logs in via the browser.
 *
 * Note: Does NOT implement `TokenStoreWithLookup` — localStorage stores
 * are keyed by userId, and auto-refresh requires the userId to be passed
 * explicitly. For full auto-refresh support with localStorage, use the
 * InMemoryTokenStore wrapper or implement TokenStoreWithLookup yourself.
 *
 * @example
 * ```ts
 * const store = new LocalStorageTokenStore();
 * const client = new SattabaseClient(config, store);
 * ```
 */
export class LocalStorageTokenStore implements TokenStore {
  private readonly keyPrefix: string;

  constructor(keyPrefix = "sb:") {
    this.keyPrefix = keyPrefix;
  }

  private storageKey(userId: string): string {
    return `${this.keyPrefix}${userId}`;
  }

  getTokens(userId: string): TokenPair | null {
    if (typeof localStorage === "undefined") return null;
    try {
      const raw = localStorage.getItem(this.storageKey(userId));
      if (!raw) return null;
      return JSON.parse(raw) as TokenPair;
    } catch {
      return null;
    }
  }

  setTokens(userId: string, tokens: TokenPair): void {
    if (typeof localStorage === "undefined") return;
    localStorage.setItem(this.storageKey(userId), JSON.stringify(tokens));
  }

  deleteTokens(userId: string): void {
    if (typeof localStorage === "undefined") return;
    localStorage.removeItem(this.storageKey(userId));
  }
}
