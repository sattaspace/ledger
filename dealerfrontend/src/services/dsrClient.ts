/**
 * DSR API Client — Isolated client for DSR authentication
 *
 * This is a SEPARATE client from the dealer apiClient.
 * It does NOT use SattaBase tokens or any dealer auth logic.
 *
 * DSRs have their own JWT tokens stored in localStorage under:
 * - dsr_access_token
 * - dsr_refresh_token
 */

// Storage keys - separate from dealer auth
const DSR_ACCESS_KEY = "dsr_access_token";
const DSR_REFRESH_KEY = "dsr_refresh_token";
const DSR_USER_KEY = "dsr_user";
const DSR_SELECTED_DEALER_KEY = "dsr_selected_dealer";

// Base URL for DSR API — resolved from environment variables (same source
// as the dealer apiClient). Previously hardcoded to localhost which broke
// every non-local deployment.
function resolveDsrApiBase(): string {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const env =
    typeof import.meta !== "undefined" && (import.meta as any).env
      ? (import.meta as any).env
      : {};
  return (
    env.PUBLIC_DEALER_API_URL ||
    env.VITE_API_BASE_URL ||
    "http://localhost:8088/api"
  );
}
const DSR_API_BASE = resolveDsrApiBase();

// ─── Types ───────────────────────────────────────────────────────────────────

export interface DsrApiError {
  status: number;
  message: string;
  data?: any;
}

export interface DsrUser {
  id: string;
  email: string;
  phone?: string;
  user_type: string;
  full_name: string;
  avatar_url?: string;
  email_verified?: boolean; // FIX DSR-INV-005: Needed for verification banner
  phone_verified?: boolean;
  has_dsr_profile?: boolean;
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
  awaiting_invitation?: boolean;
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

export interface DsrRegisterViaInviteResponse {
  access: string;
  refresh: string;
  user: DsrUser;
  dealer: DealerChoice;
  message?: string;
}

// ─── Token Management ────────────────────────────────────────────────────────

export function getDsrAccessToken(): string | null {
  return localStorage.getItem(DSR_ACCESS_KEY);
}

export function getDsrRefreshToken(): string | null {
  return localStorage.getItem(DSR_REFRESH_KEY);
}

export function setDsrTokens(access: string, refresh: string): void {
  localStorage.setItem(DSR_ACCESS_KEY, access);
  localStorage.setItem(DSR_REFRESH_KEY, refresh);
}

export function getDsrUser(): DsrUser | null {
  const userStr = localStorage.getItem(DSR_USER_KEY);
  return userStr ? JSON.parse(userStr) : null;
}

export function setDsrUser(user: DsrUser): void {
  localStorage.setItem(DSR_USER_KEY, JSON.stringify(user));
}

export function getDsrSelectedDealer(): DealerChoice | null {
  const dealerStr = localStorage.getItem(DSR_SELECTED_DEALER_KEY);
  return dealerStr ? JSON.parse(dealerStr) : null;
}

export function setDsrSelectedDealer(dealer: DealerChoice): void {
  localStorage.setItem(DSR_SELECTED_DEALER_KEY, JSON.stringify(dealer));
}

export function clearDsrAuth(): void {
  localStorage.removeItem(DSR_ACCESS_KEY);
  localStorage.removeItem(DSR_REFRESH_KEY);
  localStorage.removeItem(DSR_USER_KEY);
  localStorage.removeItem(DSR_SELECTED_DEALER_KEY);
}

// ─── API Request Helper ──────────────────────────────────────────────────────

async function dsrRequest<T>(
  method: string,
  endpoint: string,
  body?: any,
  useAuth: boolean = false,
): Promise<T> {
  const url = `${DSR_API_BASE}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };

  // Add DSR token if authenticated request
  if (useAuth) {
    const token = getDsrAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // FIX M-5: removed `credentials: "include"`. The DSR API uses Bearer-token
  // auth in the Authorization header; sending ambient cookies widens the
  // CORS attack surface for no benefit and can cause subtle CSRF/CSWSH
  // issues when the backend is later configured with cookie sessions.
  const config: RequestInit = {
    method,
    headers,
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  // FIX: gate request diagnostics behind DEV mode to avoid leaking
  // API call details in production console.
  if (import.meta.env.DEV) {
    console.log(`[DSR CLIENT] ${method} ${endpoint}`, {
      useAuth,
      hasBody: !!body,
    });
  }

  const response = await fetch(url, config);

  // Parse response
  let data: any = null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    data = await response.json();
  } else {
    const text = await response.text();
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (import.meta.env.DEV) {
    console.log(`[DSR CLIENT] ${method} ${endpoint} response:`, {
      status: response.status,
      ok: response.ok,
    });
  }

  if (!response.ok) {
    const error: DsrApiError = {
      status: response.status,
      message: data?.detail || data?.message || data?.error || "Request failed",
      data,
    };
    throw error;
  }

  return data;
}

// ─── DSR Auth API ─────────────────────────────────────────────────────────────

export const dsrApi = {
  /**
   * Login as DSR with email and password
   */
  async login(email: string, password: string): Promise<DsrLoginResponse> {
    const data = await dsrRequest<DsrLoginResponse>("POST", "/dsr/auth/login", {
      email,
      password,
    });

    // Store tokens and user
    if (data.access && data.refresh) {
      setDsrTokens(data.access, data.refresh);
    }
    if (data.user) {
      setDsrUser(data.user);
    }

    // Store dealer if only one
    if (!data.require_dealer_selection && data.dealers?.length === 1) {
      setDsrSelectedDealer(data.dealers[0]);
    }

    if (import.meta.env.DEV) {
      console.log("[DSR API] Login successful:", {
        hasToken: !!getDsrAccessToken(),
        awaitingInvitation: data.awaiting_invitation,
      });
    }

    return data;
  },

  /**
   * Self-register as DSR
   */
  async register(
    email: string,
    fullName: string,
    password: string,
    phone?: string,
  ): Promise<DsrLoginResponse> {
    const data = await dsrRequest<DsrLoginResponse>(
      "POST",
      "/dsr/auth/register",
      {
        email,
        full_name: fullName,
        password,
        phone: phone || "",
      },
    );

    if (data.access && data.refresh) {
      setDsrTokens(data.access, data.refresh);
    }
    if (data.user) {
      setDsrUser(data.user);
    }

    return data;
  },

  /**
   * Get DSR profile
   */
  async getProfile(): Promise<DsrProfileResponse> {
    return dsrRequest<DsrProfileResponse>(
      "GET",
      "/dsr/auth/me",
      undefined,
      true,
    );
  },

  /**
   * Select dealer for multi-dealer DSR
   *
   * The backend returns `effective_access` — the SINGLE SOURCE OF TRUTH
   * for the DSR's portal session. It's already the intersection of:
   *   - dealer's plan-level access (from SattaBase)
   *   - DSR's per-dealer assignment permissions
   *
   * The frontend should just `setAccessMap(result.effective_access)`.
   * No intersection logic, no hardcoded defaults.
   */
  async selectDealer(dealerUsername: string): Promise<{
    access: string;
    refresh: string;
    dealer: DealerChoice;
    permissions: Record<string, any>;
    dealer_access?: Record<string, any>;
    effective_access?: Record<string, any>;
    message?: string;
  }> {
    const data = await dsrRequest<{
      access: string;
      refresh: string;
      dealer: DealerChoice;
      permissions: Record<string, any>;
      dealer_access?: Record<string, any>;
      effective_access?: Record<string, any>;
      message?: string;
    }>(
      "POST",
      "/dsr/auth/select-dealer",
      { dealer_username: dealerUsername },
      true,
    );

    if (data.access && data.refresh) {
      setDsrTokens(data.access, data.refresh);
    }
    if (data.dealer) {
      setDsrSelectedDealer(data.dealer);
    }

    return data;
  },

  /**
   * Refresh the DSR's effective_access map from SattaBase.
   *
   * WHY THIS EXISTS
   * ---------------
   * The backend caches SattaBase access responses for
   * SATTABASE_ACCESS_CACHE_TTL seconds (default 300 = 5 min). The
   * frontend also caches the effective_access map in a Vue ref after
   * select-dealer. When the dealer's plan is changed live in SattaBase
   * admin, NEITHER cache knows about it — the DSR keeps seeing the
   * stale menu until the cache TTL expires AND the DSR re-logs in.
   *
   * This endpoint breaks the staleness in one shot:
   *   1. Backend invalidates its in-memory cache for the current dealer.
   *   2. Backend re-fetches fresh access from SattaBase (and re-caches it
   *      so subsequent API calls also see the new matrix).
   *   3. Backend recomputes effective_access and returns it.
   *
   * WHEN TO CALL
   * ------------
   * - When the DSR returns from a billing-redirect flow
   *   (useBillingRedirect detects ?billing_updated=1)
   * - On an explicit "Refresh permissions" action in the UI
   * - Optionally: periodically (every 5 min) while the DSR portal
   *   session is active
   *
   * After calling this, the caller MUST do `setAccessMap(result.effective_access)`
   * to update the in-memory Vue ref so menu visibility re-renders.
   *
   * Note: this does NOT re-issue JWT tokens. The DSR's existing tokens
   * remain valid. Only the access map is refreshed.
   */
  async refreshAccess(): Promise<{
    effective_access: Record<string, any>;
    dealer_access?: Record<string, any>;
    permissions?: Record<string, any>;
    cache_invalidated: boolean;
    message?: string;
  }> {
    return dsrRequest<{
      effective_access: Record<string, any>;
      dealer_access?: Record<string, any>;
      permissions?: Record<string, any>;
      cache_invalidated: boolean;
      message?: string;
    }>("POST", "/dsr/auth/refresh-access", undefined, true);
  },

  /**
   * Logout DSR
   */
  async logout(): Promise<void> {
    try {
      await dsrRequest("POST", "/dsr/auth/logout", undefined, true);
    } catch (err) {
      console.error("[DSR API] Logout API error:", err);
    } finally {
      clearDsrAuth();
    }
  },

  /**
   * Refresh DSR token
   */
  async refreshToken(): Promise<{ access: string; refresh?: string }> {
    const refreshToken = getDsrRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const data = await dsrRequest<{ access: string; refresh?: string }>(
      "POST",
      "/dsr/auth/refresh",
      { refresh: refreshToken },
    );

    if (data.access) {
      setDsrTokens(data.access, data.refresh || refreshToken);
    }

    return data;
  },

  /**
   * Get DSR invitations
   * Backend returns: { pending: [...], accepted: [...], rejected: [...] }
   */
  async getInvitations(): Promise<{
    pending: any[];
    accepted: any[];
    rejected: any[];
  }> {
    const data = await dsrRequest<{
      pending: any[];
      accepted: any[];
      rejected: any[];
    }>("GET", "/dsr/invitations", undefined, true);
    // Handle both old and new format
    if (data.pending !== undefined) {
      return data;
    }
    // Fallback for other formats
    return { pending: [], accepted: [], rejected: [] };
  },

  /**
   * Accept invitation
   */
  async acceptInvitation(invitationId: string): Promise<any> {
    return dsrRequest(
      "POST",
      `/dsr/invitations/${invitationId}/accept`,
      undefined,
      true,
    );
  },

  /**
   * Reject invitation
   */
  async rejectInvitation(invitationId: string): Promise<any> {
    return dsrRequest(
      "POST",
      `/dsr/invitations/${invitationId}/reject`,
      undefined,
      true,
    );
  },

  /**
   * Get DSR assignments
   * Backend returns: { active: [...], removed: [...], left: [...] }
   */
  async getAssignments(): Promise<{
    active: any[];
    removed: any[];
    left: any[];
  }> {
    const data = await dsrRequest<{
      active: any[];
      removed: any[];
      left: any[];
    }>("GET", "/dsr/assignments", undefined, true);
    // Handle both old and new format
    if (data.active !== undefined) {
      return data;
    }
    // Fallback for other formats
    return { active: [], removed: [], left: [] };
  },

  /**
   * Register DSR via invitation token.
   *
   * FIX: Previously this method lived in dsrAuth.service.ts and went through
   * the dealer apiClient (wrong auth context). Now consolidated into the
   * isolated DSR client.
   */
  async registerViaInvitation(
    token: string,
    fullName: string,
    phone: string,
    password: string,
  ): Promise<DsrRegisterViaInviteResponse> {
    const data = await dsrRequest<DsrRegisterViaInviteResponse>(
      "POST",
      `/dsr/auth/register/${token}`,
      {
        full_name: fullName,
        phone,
        password,
      },
    );

    if (data.access && data.refresh) {
      setDsrTokens(data.access, data.refresh);
    }
    if (data.user) {
      setDsrUser(data.user);
    }
    if (data.dealer) {
      setDsrSelectedDealer(data.dealer);
    }

    return data;
  },

  /**
   * Update DSR profile
   */
  async updateProfile(updates: {
    full_name?: string;
    email?: string;
    phone?: string;
    avatar_url?: string;
    bio?: string;
  }): Promise<DsrProfileResponse> {
    return dsrRequest<DsrProfileResponse>("PUT", "/dsr/auth/me", updates, true);
  },

  /**
   * Change password
   */
  async changePassword(
    currentPassword: string,
    newPassword: string,
  ): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      "/dsr/auth/change-password",
      {
        current_password: currentPassword,
        new_password: newPassword,
      },
      true,
    );
  },

  /**
   * Request password reset
   */
  async requestPasswordReset(
    phoneOrEmail: string,
  ): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      "/dsr/auth/password-reset/request",
      { phone_or_email: phoneOrEmail },
    );
  },

  /**
   * Confirm password reset
   */
  async confirmPasswordReset(
    token: string,
    newPassword: string,
  ): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      "/dsr/auth/password-reset/confirm",
      { token, new_password: newPassword },
    );
  },

  /**
   * Verify email address
   */
  async verifyEmail(token: string): Promise<{ message: string }> {
    // Backend expects `token` as a query parameter (?token=xxx), not in the body.
    return dsrRequest<{ message: string }>(
      "POST",
      `/dsr/auth/verify-email?token=${encodeURIComponent(token)}`,
    );
  },

  /**
   * Resend email verification
   * FIX DSR-INV-005: Now requires auth (backend validates via JWT token).
   */
  async resendVerification(email?: string): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      "/dsr/auth/resend-verification",
      email ? { email } : {},
      true, // FIX: requires auth — backend gets user from JWT
    );
  },

  /**
   * Set phone number (required after first invitation acceptance)
   */
  async setPhone(phone: string): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      "/dsr/auth/set-phone",
      { phone },
      true,
    );
  },

  /**
   * Leave a dealer assignment
   */
  async leaveDealer(
    assignmentId: string,
    reason?: string,
  ): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      `/dsr/assignments/${assignmentId}/leave`,
      { reason },
      true,
    );
  },
};

// ─── Auth State Check ────────────────────────────────────────────────────────

export function isDsrAuthenticated(): boolean {
  return !!getDsrAccessToken();
}

export default dsrApi;
