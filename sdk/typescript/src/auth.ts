/**
 * Auth module — user authentication against Sattabase.
 *
 * Maps 1:1 to the backend `AuthController` endpoints.
 * All requests automatically include `X-API-Key` and `X-Service-Domain` headers.
 */

import type { SattabaseClient } from "./client.js";
import type { TokenPair, MessageResponse } from "./models.js";
import { AuthMeResponse } from "./models.js";

export class AuthModule {
  private client: SattabaseClient;

  constructor(client: SattabaseClient) {
    this.client = client;
  }

  /**
   * Authenticate a user and obtain JWT tokens.
   *
   * @param email - User email address
   * @param password - User password
   * @returns TokenPair with access and refresh tokens
   * @throws {AuthenticationError} Invalid credentials
   */
  async login(email: string, password: string): Promise<TokenPair> {
    const data = await this.client.request<TokenPair>("POST", "/auth/login", {
      json: { email, password },
    });
    return data;
  }

  /**
   * Register a new user account.
   *
   * @param email - User email address
   * @param password - Password (min 8 chars, must include upper, lower, digit, special)
   * @param firstName - User first name
   * @param lastName - User last name
   * @param options - Optional fields: timezone (IANA), currency (ISO 4217), language (ISO 639-1)
   * @returns MessageResponse with success status
   */
  async register(
    email: string,
    password: string,
    firstName: string,
    lastName: string,
    options?: { timezone?: string; currency?: string; language?: string },
  ): Promise<MessageResponse> {
    const body: Record<string, unknown> = {
      email,
      password,
      first_name: firstName,
      last_name: lastName,
    };
    if (options?.timezone) body["timezone"] = options.timezone;
    if (options?.currency) body["currency"] = options.currency;
    if (options?.language) body["language"] = options.language;

    return this.client.request<MessageResponse>("POST", "/auth/register", { json: body });
  }

  /**
   * Get domain-scoped user info, subscription, and access map.
   *
   * This is the **core method** for service domain integration.
   * The backend resolves the domain via `X-API-Key` (priority) or `X-Service-Domain`
   * header (fallback) and returns user data scoped to that domain's product.
   *
   * @param token - JWT access token. If null, tries token store.
   * @returns AuthMeResponse with user, subscription, and access data
   * @throws {AccountInactiveError} User account deactivated (code: `account_inactive`)
   * @throws {AccountDeletedError} User account deleted (code: `account_deleted`)
   * @throws {AuthenticationError} Invalid or expired token
   */
  async me(token?: string | null): Promise<AuthMeResponse> {
    const resolvedToken = token ?? this.resolveTokenFromStore();
    const data = await this.client.request<{
      user: import("./models.js").User;
      account_status?: string;
      subscription?: import("./models.js").SubscriptionInfo | null;
      access?: Record<string, boolean | number | string>;
    }>("GET", "/billing/auth/me", { token: resolvedToken });
    return new AuthMeResponse(data);
  }

  /**
   * Refresh an expired access token.
   *
   * @param refreshToken - The long-lived refresh token
   * @returns New TokenPair
   * @throws {AuthenticationError} Invalid or expired refresh token
   */
  async refresh(refreshToken: string): Promise<TokenPair> {
    return this.client.request<TokenPair>("POST", "/auth/token/refresh", {
      json: { refresh: refreshToken },
    });
  }

  /**
   * Verify an access token is still valid.
   *
   * @param token - The access token to verify
   * @returns MessageResponse if token is valid
   * @throws {AuthenticationError} Token is invalid or expired
   */
  async verify(token: string): Promise<MessageResponse> {
    return this.client.request<MessageResponse>("POST", "/auth/token/verify", {
      json: { token },
    });
  }

  /**
   * Blacklist a refresh token (invalidate it).
   *
   * Used for explicit logout — the access token will still work until
   * it expires (short TTL), but the user cannot get new tokens.
   *
   * @param refreshToken - The refresh token to invalidate
   */
  async blacklist(refreshToken: string): Promise<MessageResponse> {
    return this.client.request<MessageResponse>("POST", "/auth/token/blacklist", {
      json: { refresh: refreshToken },
    });
  }

  /**
   * Logout a user — blacklist refresh token and clear token store.
   *
   * @param token - The access token (currently unused, kept for API completeness)
   * @param refreshToken - The refresh token to invalidate
   */
  async logout(_token: string, refreshToken: string): Promise<void> {
    await this.blacklist(refreshToken);

    // Clear token store if configured
    if (this.client.tokenStore) {
      const userId = this.client.findUserIdByRefresh(refreshToken);
      if (userId) {
        this.client.tokenStore.deleteTokens(userId);
      }
    }
  }

  /**
   * Request a password reset OTP via email.
   *
   * @param email - The account email address
   */
  async requestPasswordReset(email: string): Promise<MessageResponse> {
    return this.client.request<MessageResponse>("POST", "/auth/password-reset/request", {
      json: { email },
    });
  }

  /**
   * Confirm a password reset with the OTP received via email.
   *
   * @param email - The account email address
   * @param otp - 6-digit OTP code
   * @param newPassword - The new password
   * @param confirmPassword - Must match newPassword
   */
  async confirmPasswordReset(
    email: string,
    otp: string,
    newPassword: string,
    confirmPassword: string,
  ): Promise<MessageResponse> {
    return this.client.request<MessageResponse>("POST", "/auth/password-reset/confirm", {
      json: {
        email,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword,
      },
    });
  }

  /**
   * Request an email verification OTP.
   *
   * @param email - The account email address
   */
  async requestEmailVerification(email: string): Promise<MessageResponse> {
    return this.client.request<MessageResponse>("POST", "/auth/verify-email/request", {
      json: { email },
    });
  }

  /**
   * Confirm email verification with OTP.
   *
   * @param email - The account email address
   * @param otp - 6-digit OTP code
   */
  async confirmEmailVerification(email: string, otp: string): Promise<MessageResponse> {
    return this.client.request<MessageResponse>("POST", "/auth/verify-email/confirm", {
      json: { email, otp },
    });
  }

  /** Try to resolve a token from the configured token store. */
  private resolveTokenFromStore(): string | null {
    const store = this.client.tokenStore;
    if (!store) return null;

    if (store && typeof (store as TokenStoreWithLookup).getFirstTokenPair === "function") {
      const first = (store as TokenStoreWithLookup).getFirstTokenPair();
      return first?.access ?? null;
    }

    return null;
  }
}

// Inline import to avoid circular dependency — we only need the type
import type { TokenStoreWithLookup } from "./token-store.js";
