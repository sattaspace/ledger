/**
 * DSR Authentication Service
 * --------------------------
 * Handles DSR-specific authentication (separate from SattaBase dealer auth).
 *
 * DSRs log in directly to DealerBackend with email/password.
 * Dealers continue to use SattaBase authentication.
 */

import { apiClient } from "../apiClient";

// Types
export interface DsrUser {
  id: string;
  email: string;
  user_type: "DSR" | "Collector" | "ADMIN";
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
}

export interface DealerChoice {
  username: string;
  full_name: string;
  business_name: string;
}

export interface DsrLoginResponse {
  access: string;
  refresh: string;
  user: DsrUser;
  dealers: DealerChoice[];
  // FIX B-2: previously snake_case. The apiClient auto-converts
  // response keys to camelCase, so the runtime shape is camelCase.
  // Declaring snake_case here caused `response.requireDealerSelection`
  // / `response.awaitingInvitation` to always be undefined.
  requireDealerSelection: boolean;
  awaitingInvitation?: boolean; // True if DSR has no dealer assignments
  message?: string;
}

export interface DsrRegisterResponse {
  access: string;
  refresh: string;
  user: DsrUser;
  dealer: DealerChoice;
  message?: string;
}

export interface DsrProfileResponse {
  user: DsrUser;
  dsr_id: string | null;
  dsr_name: string;
  dsr_role: string;
  dealers: DealerChoice[];
  selected_dealer: DealerChoice | null;
}

// Storage keys
const DSR_ACCESS_KEY = "dsr_access_token";
const DSR_REFRESH_KEY = "dsr_refresh_token";
const DSR_USER_KEY = "dsr_user";
const DSR_SELECTED_DEALER_KEY = "dsr_selected_dealer";

/**
 * DSR Authentication API
 */
export const dsrAuthService = {
  // ─── Token Management ────────────────────────────────────────────────────

  /**
   * Store DSR tokens in localStorage
   */
  setTokens(access: string, refresh: string): void {
    localStorage.setItem(DSR_ACCESS_KEY, access);
    localStorage.setItem(DSR_REFRESH_KEY, refresh);
  },

  /**
   * Get DSR access token
   */
  getAccessToken(): string | null {
    return localStorage.getItem(DSR_ACCESS_KEY);
  },

  /**
   * Get DSR refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem(DSR_REFRESH_KEY);
  },

  /**
   * Clear all DSR auth data
   */
  clearAuth(): void {
    localStorage.removeItem(DSR_ACCESS_KEY);
    localStorage.removeItem(DSR_REFRESH_KEY);
    localStorage.removeItem(DSR_USER_KEY);
    localStorage.removeItem(DSR_SELECTED_DEALER_KEY);
  },

  /**
   * Store DSR user data
   */
  setUser(user: DsrUser): void {
    localStorage.setItem(DSR_USER_KEY, JSON.stringify(user));
  },

  /**
   * Get stored DSR user data
   */
  getUser(): DsrUser | null {
    const userStr = localStorage.getItem(DSR_USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  },

  /**
   * Store selected dealer
   */
  setSelectedDealer(dealer: DealerChoice): void {
    localStorage.setItem(DSR_SELECTED_DEALER_KEY, JSON.stringify(dealer));
  },

  /**
   * Get selected dealer
   */
  getSelectedDealer(): DealerChoice | null {
    const dealerStr = localStorage.getItem(DSR_SELECTED_DEALER_KEY);
    return dealerStr ? JSON.parse(dealerStr) : null;
  },

  // ─── Authentication Endpoints ────────────────────────────────────────────

  /**
   * Login as DSR
   */
  async login(email: string, password: string): Promise<DsrLoginResponse> {
    const apiResponse = await apiClient.post<DsrLoginResponse>(
      "/dsr/auth/login",
      {
        email,
        password,
      },
    );

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data;

    console.log("[DSR AUTH] Login response:", {
      hasAccess: !!response.access,
      hasRefresh: !!response.refresh,
      hasUser: !!response.user,
      awaitingInvitation: response.awaitingInvitation,
    });

    // Store tokens and user
    this.setTokens(response.access, response.refresh);
    this.setUser(response.user);

    // Verify tokens were stored
    console.log("[DSR AUTH] Tokens stored:", {
      storedAccess: !!this.getAccessToken(),
      storedRefresh: !!this.getRefreshToken(),
    });

    // If only one dealer, store it (check dealers array exists first)
    if (
      !response.requireDealerSelection &&
      response.dealers &&
      response.dealers.length === 1
    ) {
      this.setSelectedDealer(response.dealers[0]);
    }

    return response;
  },

  /**
   * Self-register as DSR (independent profile)
   * Email is required, phone is optional
   */
  async selfRegister(
    email: string,
    fullName: string,
    password: string,
    phone?: string,
  ): Promise<DsrLoginResponse> {
    const apiResponse = await apiClient.post<DsrLoginResponse>(
      "/dsr/auth/register",
      {
        email,
        full_name: fullName,
        password,
        phone: phone || "",
      },
    );

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data;

    // Store tokens and user
    this.setTokens(response.access, response.refresh);
    this.setUser(response.user);

    return response;
  },

  /**
   * Register DSR via invitation token.
   *
   * FIX B-2: payload now sends `full_name` (matches the backend's
   * `DsrRegisterInput.full_name` field and the self-register flow's
   * shape). Previously sent `name`, which the backend stored as `""`,
   * producing DSR records with blank names.
   */
  async register(
    token: string,
    fullName: string,
    phone: string,
    password: string,
  ): Promise<DsrRegisterResponse> {
    const apiResponse = await apiClient.post<DsrRegisterResponse>(
      "/dsr/auth/register",
      {
        token,
        full_name: fullName,
        phone,
        password,
      },
    );

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data;

    // Store tokens and user
    this.setTokens(response.access, response.refresh);
    this.setUser(response.user);
    this.setSelectedDealer(response.dealer);

    return response;
  },

  /**
   * Select dealer context (for multi-dealer DSRs)
   */
  async selectDealer(
    dealerUsername: string,
  ): Promise<{ access: string; refresh: string; dealer: DealerChoice }> {
    const accessToken = this.getAccessToken();

    if (!accessToken) {
      throw new Error("No access token available. Please login again.");
    }

    const apiResponse = await apiClient.post<{
      access: string;
      refresh: string;
      dealer: DealerChoice;
    }>(
      "/dsr/auth/select-dealer",
      { dealer_username: dealerUsername },
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      },
    );

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data;

    // Update tokens and selected dealer
    this.setTokens(response.access, response.refresh);
    this.setSelectedDealer(response.dealer);

    return response;
  },

  /**
   * Get DSR profile
   */
  async getProfile(): Promise<DsrProfileResponse> {
    const accessToken = this.getAccessToken();

    // FIX M-8: gate token diagnostics behind DEV. Even a 20-char token
    // prefix aids attackers using XSS or physical access to devtools.
    if (import.meta.env.DEV) {
      console.log("[DSR AUTH] getProfile - token check:", {
        hasToken: !!accessToken,
        tokenPreview: accessToken ? `${accessToken.substring(0, 20)}...` : "null",
      });
    }

    if (!accessToken) {
      throw new Error("No access token available. Please login again.");
    }

    const apiResponse = await apiClient.get<DsrProfileResponse>(
      "/dsr/auth/me",
      {
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
      },
    );

    // apiClient returns { ok, status, data } - access actual data via .data
    return apiResponse.data;
  },

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<{ access: string; refresh?: string }> {
    const refreshToken = this.getRefreshToken();

    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const apiResponse = await apiClient.post<{
      access: string;
      refresh?: string;
    }>("/dsr/auth/refresh", { refresh: refreshToken });

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data;

    // Update tokens
    this.setTokens(response.access, response.refresh || refreshToken);

    return response;
  },

  /**
   * Logout DSR
   */
  async logout(): Promise<void> {
    try {
      const accessToken = this.getAccessToken();
      await apiClient.post(
        "/dsr/auth/logout",
        {},
        {
          headers: {
            Authorization: `Bearer ${accessToken}`,
          },
        },
      );
    } catch (error) {
      // Continue with logout even if API call fails
      console.error("Logout API call failed:", error);
    } finally {
      this.clearAuth();
    }
  },

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<{ message: string }> {
    const apiResponse = await apiClient.post<{ message: string }>(
      "/dsr/auth/password-reset/request",
      {
        email,
      },
    );
    return apiResponse.data;
  },

  /**
   * Confirm password reset
   */
  async confirmPasswordReset(
    token: string,
    newPassword: string,
  ): Promise<{ message: string }> {
    const apiResponse = await apiClient.post<{ message: string }>(
      "/dsr/auth/password-reset/confirm",
      {
        token,
        new_password: newPassword,
      },
    );
    return apiResponse.data;
  },

  // ─── Auth State Helpers ───────────────────────────────────────────────────

  /**
   * Check if DSR is authenticated (has valid tokens)
   */
  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  },

  /**
   * Check if DSR has selected a dealer
   */
  hasSelectedDealer(): boolean {
    return !!this.getSelectedDealer();
  },

  /**
   * Get the authorization header for API requests
   */
  getAuthHeader(): Record<string, string> {
    const token = this.getAccessToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  },
};

export default dsrAuthService;
