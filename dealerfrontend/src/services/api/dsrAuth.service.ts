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
  require_dealer_selection: boolean;
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
  async login(
    emailOrPhone: string,
    password: string,
  ): Promise<DsrLoginResponse> {
    const response = await apiClient.post<DsrLoginResponse>("/dsr/auth/login", {
      phone_or_email: emailOrPhone,
      password,
    });

    // Store tokens and user
    this.setTokens(response.access, response.refresh);
    this.setUser(response.user);

    // If only one dealer, store it
    if (!response.require_dealer_selection && response.dealers.length === 1) {
      this.setSelectedDealer(response.dealers[0]);
    }

    return response;
  },

  /**
   * Self-register as DSR (independent profile)
   */
  async selfRegister(
    phone: string,
    fullName: string,
    password: string,
    email?: string,
  ): Promise<DsrLoginResponse> {
    const response = await apiClient.post<DsrLoginResponse>(
      "/dsr/auth/register",
      {
        phone,
        full_name: fullName,
        password,
        email: email || "",
      },
    );

    // Store tokens and user
    this.setTokens(response.access, response.refresh);
    this.setUser(response.user);

    return response;
  },

  /**
   * Register DSR via invitation token
   */
  async register(
    token: string,
    name: string,
    phone: string,
    password: string,
  ): Promise<DsrRegisterResponse> {
    const response = await apiClient.post<DsrRegisterResponse>(
      "/dsr/auth/register",
      {
        token,
        name,
        phone,
        password,
      },
    );

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

    const response = await apiClient.post<{
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

    const response = await apiClient.get<DsrProfileResponse>("/dsr/auth/me", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    });

    return response;
  },

  /**
   * Refresh access token
   */
  async refreshToken(): Promise<{ access: string; refresh?: string }> {
    const refreshToken = this.getRefreshToken();

    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await apiClient.post<{ access: string; refresh?: string }>(
      "/dsr/auth/refresh",
      { refresh: refreshToken },
    );

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
    return apiClient.post<{ message: string }>(
      "/dsr/auth/password-reset/request",
      {
        email,
      },
    );
  },

  /**
   * Confirm password reset
   */
  async confirmPasswordReset(
    token: string,
    newPassword: string,
  ): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>(
      "/dsr/auth/password-reset/confirm",
      {
        token,
        new_password: newPassword,
      },
    );
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
