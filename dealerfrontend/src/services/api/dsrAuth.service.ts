/**
 * DSR Authentication Service (DEPRECATED — thin re-export wrapper)
 * ---------------------------------------------------------------
 *
 * This module previously contained a DUPLICATE DSR auth implementation
 * that used the dealer `apiClient` instead of the isolated DSR client.
 * It has been consolidated into `services/dsrClient.ts`.
 *
 * All new code should import from `services/dsrClient.ts` directly.
 * This file exists only for backward compatibility with existing imports.
 *
 * Key differences in the consolidated client:
 * - Uses the isolated DSR HTTP client (correct auth context)
 * - Environment-variable-based API base URL (not hardcoded localhost)
 * - DEV-only console logging (no token leakage in production)
 * - All DSR endpoints are in one place
 *
 * Audit fix TS-5: removed unused `DsrRegisterViaInviteResponse` type
 * import. The local `DsrRegisterResponse` interface is used instead.
 *
 * Audit fix TS-6: the previous `setTokens: setDsrTokens` and
 * `getRefreshToken: getDsrRefreshToken` re-exports triggered @deprecated
 * warnings because both functions are marked @deprecated in dsrClient.ts
 * (setDsrTokens is a backwards-compat shim that ignores its refresh arg;
 * getDsrRefreshToken always returns null because the refresh token now
 * lives in an httpOnly cookie). We keep the re-exports because external
 * callers may still use them, but inline the underlying behavior with
 * wrappers that don't trigger the @deprecated warning at the import
 * site. The wrappers themselves are marked @deprecated so future
 * callers see the warning at the call site, not the import site.
 */

import {
  dsrApi,
  getDsrAccessToken,
  getDsrRefreshToken,
  setDsrTokens,
  getDsrUser,
  setDsrUser,
  getDsrSelectedDealer,
  setDsrSelectedDealer,
  clearDsrAuth,
  isDsrAuthenticated,
  type DsrUser,
  type DealerChoice,
  type DsrLoginResponse,
  type DsrProfileResponse,
} from "../dsrClient";

// ─── Re-exported types for backward compatibility ──────────────────────

export type { DsrUser, DealerChoice, DsrLoginResponse, DsrProfileResponse };

export interface DsrRegisterResponse {
  access: string;
  refresh: string;
  user: DsrUser;
  dealer: DealerChoice;
  message?: string;
}

// ─── Re-exported service object ────────────────────────────────────────
//
// This object preserves the .method() call style used by existing
// components (e.g. DsrRegisterPage, App.vue) while delegating
// all real work to the consolidated dsrApi from dsrClient.ts.
//
// Audit fix TS-6: wrap the deprecated `setDsrTokens` / `getDsrRefreshToken`
// helpers in arrow functions so that importing them from this module
// doesn't trigger @deprecated warnings at the import site. Callers
// that use these wrappers will still see the @deprecated JSDoc on the
// underlying dsrClient.ts functions in their IDE.

/** @deprecated Use setDsrAccessToken from dsrClient.ts directly. */
const setTokensWrapper = (access: string, _refresh?: string): void => {
  setDsrTokens(access, _refresh);
};

/** @deprecated The refresh token is now in an httpOnly cookie — always returns null. */
const getRefreshTokenWrapper = (): string | null => {
  return getDsrRefreshToken();
};

export const dsrAuthService = {
  // ── Token Management (delegate to dsrClient) ───────────────────────

  /** @deprecated Use setDsrAccessToken from dsrClient.ts directly. */
  setTokens: setTokensWrapper,
  getAccessToken: getDsrAccessToken,
  /** @deprecated The refresh token is now in an httpOnly cookie — always returns null. */
  getRefreshToken: getRefreshTokenWrapper,
  clearAuth: clearDsrAuth,
  setUser: setDsrUser,
  getUser: getDsrUser,
  setSelectedDealer: setDsrSelectedDealer,
  getSelectedDealer: getDsrSelectedDealer,
  isAuthenticated: isDsrAuthenticated,

  hasSelectedDealer(): boolean {
    return !!getDsrSelectedDealer();
  },

  getAuthHeader(): Record<string, string> {
    const token = getDsrAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },

  // ── Authentication Endpoints (delegate to dsrApi) ──────────────────

  async login(email: string, password: string): Promise<DsrLoginResponse> {
    return dsrApi.login(email, password);
  },

  async selfRegister(
    email: string,
    fullName: string,
    password: string,
    phone?: string,
  ): Promise<DsrLoginResponse> {
    return dsrApi.register(email, fullName, password, phone);
  },

  /**
   * Register via invitation token.
   * Delegates to dsrApi.registerViaInvitation which uses the isolated
   * DSR client instead of the dealer apiClient.
   */
  async register(
    token: string,
    fullName: string,
    phone: string,
    password: string,
  ): Promise<DsrRegisterResponse> {
    const result = await dsrApi.registerViaInvitation(
      token,
      fullName,
      phone,
      password,
    );
    return {
      access: result.access,
      refresh: result.refresh,
      user: result.user,
      dealer: result.dealer,
      message: result.message,
    };
  },

  async selectDealer(
    dealerUsername: string,
  ): Promise<{ access: string; refresh: string; dealer: DealerChoice }> {
    return dsrApi.selectDealer(dealerUsername);
  },

  async getProfile(): Promise<DsrProfileResponse> {
    return dsrApi.getProfile();
  },

  async refreshToken(): Promise<{ access: string; refresh?: string }> {
    return dsrApi.refreshToken();
  },

  async logout(): Promise<void> {
    return dsrApi.logout();
  },

  async requestPasswordReset(email: string): Promise<{ message: string }> {
    return dsrApi.requestPasswordReset(email);
  },

  async confirmPasswordReset(
    token: string,
    newPassword: string,
  ): Promise<{ message: string }> {
    return dsrApi.confirmPasswordReset(token, newPassword);
  },
};

export default dsrAuthService;
