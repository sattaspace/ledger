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
  type DsrRegisterViaInviteResponse,
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

export const dsrAuthService = {
  // ── Token Management (delegate to dsrClient) ───────────────────────

  setTokens: setDsrTokens,
  getAccessToken: getDsrAccessToken,
  getRefreshToken: getDsrRefreshToken,
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
