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
 * user logs in via the browser. Implements `TokenStoreWithLookup` for
 * full auto-refresh support.
 *
 * @example
 * ```ts
 * const store = new LocalStorageTokenStore();
 * const client = new SattabaseClient(config, store);
 *
 * await client.auth.login("user@example.com", "password");
 * // tokens are auto-stored; auto-refresh works automatically
 * ```
 */
export class LocalStorageTokenStore implements TokenStoreWithLookup {
  private readonly keyPrefix: string;
  private _currentUserId: string | null = null;

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
    this._currentUserId = userId;
    localStorage.setItem(this.storageKey(userId), JSON.stringify(tokens));
  }

  deleteTokens(userId: string): void {
    if (typeof localStorage === "undefined") return;
    localStorage.removeItem(this.storageKey(userId));
    if (this._currentUserId === userId) {
      this._currentUserId = null;
    }
  }

  /** Get the first (or current) available token pair from localStorage. */
  getFirstTokenPair(): TokenPair | null {
    if (typeof localStorage === "undefined") return null;
    // Prefer the last userId used in setTokens
    if (this._currentUserId) {
      const tokens = this.getTokens(this._currentUserId);
      if (tokens) return tokens;
    }
    // Fallback: scan localStorage for keys matching the prefix
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.keyPrefix)) {
        try {
          const raw = localStorage.getItem(key);
          if (raw) return JSON.parse(raw) as TokenPair;
        } catch {
          continue;
        }
      }
    }
    return null;
  }

  /** Find a userId by matching refresh token value. */
  getUserIdByRefresh(refreshToken: string): string | null {
    if (typeof localStorage === "undefined") return null;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.keyPrefix)) {
        try {
          const raw = localStorage.getItem(key);
          if (!raw) continue;
          const tokens = JSON.parse(raw) as TokenPair;
          if (tokens.refresh === refreshToken) {
            return key.slice(this.keyPrefix.length);
          }
        } catch {
          continue;
        }
      }
    }
    return null;
  }
}
