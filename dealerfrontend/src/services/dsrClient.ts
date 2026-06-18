/**
 * DSR API Client — Isolated client for DSR authentication.
 *
 * This is a SEPARATE client from the dealer apiClient. It does NOT use
 * SattaBase tokens or any dealer auth logic.
 *
 * ─── AUDIT FIX C1 (localStorage tokens → httpOnly cookie) ──────────────
 * The DSR refresh token is NO LONGER stored in localStorage. It lives in
 * an httpOnly, Secure, SameSite=Lax cookie set by the Astro proxy at
 * /api/dsr/auth/login (and rotated by /api/dsr/auth/refresh-cookie). The
 * browser sends the cookie automatically on every /api/dsr/auth/* call
 * (credentials: 'include'). JavaScript cannot read it, so XSS cannot
 * exfiltrate it.
 *
 * The short-lived DSR access token (~5 min default) lives in JavaScript
 * memory only (`_dsrAccessToken`), mirroring the dealer-side pattern in
 * lib/api.ts. It is hydrated from the proxy response body and discarded
 * on logout.
 *
 * ─── AUDIT FIX C2 (logout never blacklisted) ───────────────────────────
 * Logout now POSTs to /api/dsr/auth/logout (Astro proxy). The proxy
 * forwards the httpOnly cookie to the dealerbackend, which reads it and
 * blacklists the token via RefreshToken.blacklist(). The proxy then
 * clears the cookie on the browser.
 *
 * ─── AUDIT FIX C3 (no token refresh) ───────────────────────────────────
 * dsrRequest now has a 401 → refresh-cookie → retry interceptor, mirroring
 * the dealer-side refreshAccessToken() in lib/api.ts. Concurrent 401s are
 * deduplicated via a shared `dsrRefreshPromise`. On refresh failure, the
 * in-memory token is cleared and the user is redirected to /dsr/login.
 *
 * ─── AUDIT FIX H6 (PII in console) ─────────────────────────────────────
 * All diagnostic console.log calls are gated behind import.meta.env.DEV.
 */

// Storage keys — only the access token's USER PROFILE and selected dealer
// are kept in localStorage. The refresh token is in an httpOnly cookie.
const DSR_USER_KEY = "dsr_user";
const DSR_SELECTED_DEALER_KEY = "dsr_selected_dealer";

// In-memory access token. NEVER written to localStorage. Mirrors the
// dealer-side _accessToken in lib/api.ts.
let _dsrAccessToken: string | null = null;

// Base URL for the Astro DSR auth proxy endpoints (same-origin).
const DSR_AUTH_PROXY_BASE = "/api/dsr/auth";

// Base URL for DSR business API endpoints — resolved from environment
// variables (same source as the dealer apiClient). Previously hardcoded
// to localhost which broke every non-local deployment.
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
  email_verified?: boolean;
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
  // refresh is now always "" — the real refresh token lives in an
  // httpOnly cookie set by the /api/dsr/auth/login proxy.
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
  refresh: string; // "" — httpOnly cookie only
  user: DsrUser;
  dealer: DealerChoice;
  message?: string;
}

// ─── Token Management ────────────────────────────────────────────────────────

/**
 * Get the in-memory DSR access token. Returns null if not set.
 *
 * Note: the access token is hydrated by login() / selectDealer() /
 * refreshToken() — never from localStorage. On a fresh page load, it is
 * null until the bootstrap code calls /api/dsr/auth/refresh-cookie to
 * mint a fresh one from the httpOnly refresh cookie.
 */
export function getDsrAccessToken(): string | null {
  return _dsrAccessToken;
}

/**
 * Set the in-memory DSR access token. Called by login, select-dealer, and
 * refresh after a successful response.
 */
export function setDsrAccessToken(access: string): void {
  _dsrAccessToken = access;
}

/**
 * Clear the in-memory DSR access token. Called by logout() and on refresh
 * failure. The httpOnly refresh cookie is cleared by the proxy endpoint.
 */
export function clearDsrAccessToken(): void {
  _dsrAccessToken = null;
}

/**
 * Backwards-compatible alias. Old callers stored both tokens via
 * setDsrTokens(access, refresh). The refresh arg is now silently
 * ignored — the refresh token is set by the proxy via httpOnly cookie.
 *
 * @deprecated Use setDsrAccessToken(access) instead.
 */
export function setDsrTokens(access: string, _refresh?: string): void {
  _dsrAccessToken = access;
}

/**
 * Backwards-compatible alias. Always returns null — the refresh token is
 * in an httpOnly cookie and is not readable from JavaScript.
 *
 * @deprecated Use hasDsrSession() to check if the cookie is plausibly set.
 */
export function getDsrRefreshToken(): string | null {
  return null;
}

// ─── User / Dealer Profile in localStorage ───────────────────────────────────
//
// The user object and selected dealer are NOT security-sensitive (they're
// already in the JWT, just base64-encoded), so localStorage is fine for
// them. Only the refresh token needed to leave localStorage.

export function getDsrUser(): DsrUser | null {
  if (typeof localStorage === "undefined") return null;
  const userStr = localStorage.getItem(DSR_USER_KEY);
  return userStr ? JSON.parse(userStr) : null;
}

export function setDsrUser(user: DsrUser): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(DSR_USER_KEY, JSON.stringify(user));
}

export function getDsrSelectedDealer(): DealerChoice | null {
  if (typeof localStorage === "undefined") return null;
  const dealerStr = localStorage.getItem(DSR_SELECTED_DEALER_KEY);
  return dealerStr ? JSON.parse(dealerStr) : null;
}

export function setDsrSelectedDealer(dealer: DealerChoice): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(DSR_SELECTED_DEALER_KEY, JSON.stringify(dealer));
}

/**
 * Clear ALL DSR auth state from the browser.
 *
 * - In-memory access token → cleared
 * - localStorage user + selected dealer → cleared
 * - dealercore:dsr_portal_mode flag → cleared (audit fix M4)
 * - The httpOnly refresh cookie is cleared separately by the logout proxy.
 */
export function clearDsrAuth(): void {
  _dsrAccessToken = null;
  if (typeof localStorage === "undefined") return;
  localStorage.removeItem(DSR_USER_KEY);
  localStorage.removeItem(DSR_SELECTED_DEALER_KEY);
  // Audit fix M4: also clear portal mode so the banner doesn't persist
  // into a new DSR session.
  localStorage.removeItem("dealercore:dsr_portal_mode");
}

// ─── Refresh Token (via httpOnly cookie) ─────────────────────────────────────

let dsrRefreshPromise: Promise<string | null> | null = null;

/**
 * Refresh the DSR access token using the httpOnly refresh cookie.
 *
 * Calls the Astro proxy /api/dsr/auth/refresh-cookie with
 * credentials: 'include' so the browser automatically sends the
 * dsr_refresh_token cookie. The proxy reads the cookie, calls the
 * dealerbackend's /dsr/auth/refresh, and returns { access } in the body.
 * The rotated refresh cookie (if any) arrives in Set-Cookie and is
 * stored by the browser automatically.
 *
 * Returns the new access token on success, null on failure.
 * Deduplicates concurrent calls so only one refresh request flies.
 *
 * This mirrors the dealer-side refreshAccessToken() in lib/api.ts.
 */
export async function refreshDsrAccessToken(): Promise<string | null> {
  if (dsrRefreshPromise) return dsrRefreshPromise;

  dsrRefreshPromise = (async () => {
    try {
      const response = await fetch(`${DSR_AUTH_PROXY_BASE}/refresh-cookie`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include", // browser sends dsr_refresh_token cookie
        body: "{}",
      });

      if (!response.ok) {
        // Diagnostic: log the failure status + body so the user can see
        // WHY the refresh failed (CSRF 403? cookie missing 401? backend 502?)
        if (import.meta.env.DEV) {
          let detail = "";
          try {
            const errBody = await response.clone().json();
            detail =
              errBody?.detail || errBody?.message || JSON.stringify(errBody);
          } catch {
            try {
              detail = await response.clone().text();
            } catch {
              detail = "(unreadable body)";
            }
          }
          console.warn("[DSR REFRESH] refresh-cookie failed", {
            status: response.status,
            statusText: response.statusText,
            detail,
            hint:
              response.status === 401
                ? "No dsr_refresh_token cookie was sent (cookie not stored, or expired, or credentials:'include' not set)"
                : response.status === 403
                  ? "CSRF guard rejected the request (Origin/Referer header mismatch)"
                  : response.status === 502
                    ? "Dealerbackend unreachable or returned an error"
                    : "Unknown error",
          });
        }
        clearDsrAccessToken();
        return null;
      }

      const data = await response.json();
      if (data.access) {
        _dsrAccessToken = data.access;
        return data.access;
      }

      if (import.meta.env.DEV) {
        console.warn(
          "[DSR REFRESH] refresh-cookie returned 200 but no access token in body",
          data,
        );
      }
      return null;
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("[DSR REFRESH] refresh-cookie network error:", err);
      }
      clearDsrAccessToken();
      return null;
    } finally {
      dsrRefreshPromise = null;
    }
  })();

  return dsrRefreshPromise;
}

// ─── API Request Helper ──────────────────────────────────────────────────────

//
// Auth endpoints (login, logout, refresh-cookie, select-dealer) are
// proxied via /api/dsr/auth/* so we can manage the httpOnly cookie.
// All other /dsr/* endpoints (profile, invitations, assignments, etc.)
// go directly to the dealerbackend with Bearer auth.
//
// The individual `dsrApi` methods below explicitly pass `useProxy: true`
// when calling dsrRequest for the four auth endpoints — no central
// routing decision is needed.

interface DsrRequestOptions {
  /** Send the in-memory DSR access token as Bearer. */
  useAuth?: boolean;
  /** Route through the same-origin /api/dsr/auth proxy instead of the
   *  cross-origin dealerbackend. Used by login/logout/refresh/select-dealer
   *  so the httpOnly cookie can be set/read. */
  useProxy?: boolean;
  /**
   * Internal: skip the 401-refresh-retry logic to avoid infinite loops
   * when the request itself IS the refresh call.
   */
  _skipRefreshRetry?: boolean;
}

async function dsrRequest<T>(
  method: string,
  endpoint: string,
  body?: any,
  options: DsrRequestOptions = {},
): Promise<T> {
  const {
    useAuth = false,
    useProxy = false,
    _skipRefreshRetry = false,
  } = options;

  const baseUrl = useProxy ? "" : DSR_API_BASE;
  const url = useProxy ? endpoint : `${baseUrl}${endpoint}`;

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

  const config: RequestInit = {
    method,
    headers,
    // Always include credentials so the browser sends the httpOnly
    // dsr_refresh_token cookie to the same-origin proxy. For cross-origin
    // dealerbackend calls, the cookie isn't sent (different origin), which
    // is fine — those endpoints use Bearer auth, not cookies.
    credentials: useProxy ? "include" : "same-origin",
  };

  if (body !== undefined && body !== null) {
    config.body = JSON.stringify(body);
  }

  if (import.meta.env.DEV) {
    console.log(`[DSR CLIENT] ${method} ${endpoint}`, {
      useAuth,
      useProxy,
      hasBody: !!body,
    });
  }

  let response = await fetch(url, config);

  // ── 401 → try token refresh → retry once ─────────────────────────────
  // Audit fix C3: previously the DSR client had no refresh interceptor,
  // so DSRs were silently logged out every ~5 min when their access
  // token expired. We now mirror the dealer-side refresh pattern.
  if (response.status === 401 && useAuth && !_skipRefreshRetry) {
    const newToken = await refreshDsrAccessToken();
    if (newToken) {
      // Retry the original request with the fresh token.
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(url, { ...config, headers });
    } else {
      // Refresh failed — clear local state and redirect to /dsr/login.
      clearDsrAuth();
      if (typeof window !== "undefined") {
        window.location.href = "/dsr/login";
      }
      const err: DsrApiError = {
        status: 401,
        message: "DSR session expired. Please sign in again.",
      };
      throw err;
    }
  }

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

  // 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return data;
}

// ─── DSR Auth API ─────────────────────────────────────────────────────────────

export const dsrApi = {
  /**
   * Login as DSR with email and password.
   *
   * Posts to the Astro proxy /api/dsr/auth/login. The proxy:
   *   - forwards credentials to dealerbackend /dsr/auth/login
   *   - strips the refresh token from the response body
   *   - sets the refresh token as an httpOnly cookie on the dealerfrontend origin
   *
   * The returned DsrLoginResponse.refresh is always "" — the real token is
   * in the cookie.
   */
  async login(email: string, password: string): Promise<DsrLoginResponse> {
    const data = await dsrRequest<DsrLoginResponse>(
      "POST",
      `${DSR_AUTH_PROXY_BASE}/login`,
      { email, password },
      { useProxy: true },
    );

    // Store access token in memory only.
    if (data.access) {
      setDsrAccessToken(data.access);
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
        // Diagnostic: confirm the login proxy set the httpOnly cookie.
        // We can't read the httpOnly cookie from JS, but we CAN check if
        // document.cookie contains the non-httpOnly companion cookie (if
        // one existed). For now, just log that login returned successfully
        // and the refresh token should be in the httpOnly cookie.
        cookieHint:
          "The httpOnly dsr_refresh_token cookie should now be set on the dealerfrontend origin. " +
          "Check the Application > Cookies tab in DevTools to verify.",
      });
    }

    return data;
  },

  /**
   * Self-register as DSR.
   *
   * This endpoint doesn't return tokens in the new flow (the backend's
   * register flow requires email verification before login). The caller
   * should redirect to /dsr/login after success.
   */
  async register(
    email: string,
    fullName: string,
    password: string,
    phone?: string,
  ): Promise<DsrLoginResponse> {
    // Register goes directly to the dealerbackend (no token returned yet —
    // email verification is required first).
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

    // If the backend DID return tokens (some flows do), store them via
    // the login proxy pattern. But since we don't go through the proxy
    // here, we can't set the httpOnly cookie. The caller must redirect
    // to /dsr/login for the user to authenticate via the proxy.
    if (data.access) {
      setDsrAccessToken(data.access);
    }
    if (data.user) {
      setDsrUser(data.user);
    }

    return data;
  },

  /**
   * Get DSR profile. Requires Bearer access token.
   */
  async getProfile(): Promise<DsrProfileResponse> {
    return dsrRequest<DsrProfileResponse>("GET", "/dsr/auth/me", undefined, {
      useAuth: true,
    });
  },

  /**
   * Select dealer for multi-dealer DSR.
   *
   * Posts to the Astro proxy /api/dsr/auth/select-dealer. The proxy:
   *   - forwards the dealer_username + (optional) Bearer access token
   *     to dealerbackend /dsr/auth/select-dealer
   *   - strips the new refresh token from the response body
   *   - rotates the httpOnly cookie with the new refresh token
   *
   * The returned object's `refresh` is always "" — the real token is in
   * the cookie.
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
      `${DSR_AUTH_PROXY_BASE}/select-dealer`,
      {
        dealer_username: dealerUsername,
        access_token: getDsrAccessToken() || undefined,
      },
      { useProxy: true },
    );

    if (data.access) {
      setDsrAccessToken(data.access);
    }
    if (data.dealer) {
      setDsrSelectedDealer(data.dealer);
    }

    return data;
  },

  /**
   * Refresh the DSR's effective_access map from SattaBase.
   * (See the docstring in the previous version — this endpoint stays the
   * same; it's a business-data call that uses the in-memory access token.)
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
    }>("POST", "/dsr/auth/refresh-access", undefined, { useAuth: true });
  },

  /**
   * Logout DSR.
   *
   * Posts to the Astro proxy /api/dsr/auth/logout. The proxy:
   *   - forwards the httpOnly cookie to dealerbackend /dsr/auth/logout
   *   - the backend blacklists the refresh token (this previously NEVER
   *     happened because the frontend stored it in localStorage — audit C2)
   *   - clears the cookie on the browser
   *
   * We then clear all local DSR state (in-memory token, localStorage
   * user/dealer/portal-mode).
   */
  async logout(): Promise<void> {
    try {
      await dsrRequest("POST", `${DSR_AUTH_PROXY_BASE}/logout`, undefined, {
        useProxy: true,
      });
    } catch (err) {
      if (import.meta.env.DEV) {
        console.error("[DSR API] Logout API error:", err);
      }
    } finally {
      clearDsrAuth();
    }
  },

  /**
   * Refresh DSR access token via the httpOnly cookie.
   *
   * Exposed for callers that want to proactively refresh (e.g., before a
   * long-running operation). The 401 interceptor in dsrRequest calls this
   * automatically; most code should NOT call this directly.
   */
  async refreshToken(): Promise<{ access: string }> {
    const access = await refreshDsrAccessToken();
    if (!access) {
      throw {
        status: 401,
        message: "DSR session expired. Please sign in again.",
      } as DsrApiError;
    }
    return { access };
  },

  /**
   * Get DSR invitations.
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
    }>("GET", "/dsr/invitations", undefined, { useAuth: true });
    if (data.pending !== undefined) {
      return data;
    }
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
      { useAuth: true },
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
      { useAuth: true },
    );
  },

  /**
   * Get DSR assignments
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
    }>("GET", "/dsr/assignments", undefined, { useAuth: true });
    if (data.active !== undefined) {
      return data;
    }
    return { active: [], removed: [], left: [] };
  },

  /**
   * Register DSR via invitation token.
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

    // After invitation registration, the backend returns tokens. But we
    // didn't go through the proxy, so we can't set the httpOnly cookie
    // here. The caller should redirect the user to /dsr/login to
    // authenticate via the proxy and get the cookie set properly.
    // For backwards compatibility, we still store the access token
    // in memory (which will be lost on the next page load — fine).
    if (data.access) {
      setDsrAccessToken(data.access);
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
    return dsrRequest<DsrProfileResponse>("PUT", "/dsr/auth/me", updates, {
      useAuth: true,
    });
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
      { useAuth: true },
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
    return dsrRequest<{ message: string }>(
      "POST",
      `/dsr/auth/verify-email?token=${encodeURIComponent(token)}`,
    );
  },

  /**
   * Resend email verification (requires auth).
   */
  async resendVerification(email?: string): Promise<{ message: string }> {
    return dsrRequest<{ message: string }>(
      "POST",
      "/dsr/auth/resend-verification",
      email ? { email } : {},
      { useAuth: true },
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
      { useAuth: true },
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
      { useAuth: true },
    );
  },
};

// ─── Auth State Check ────────────────────────────────────────────────────────

/**
 * Check if the DSR has an in-memory access token.
 *
 * Note: this returns false on a fresh page load even if the httpOnly cookie
 * is still valid, because the access token is hydrated asynchronously by
 * the bootstrap code (which calls /api/dsr/auth/refresh-cookie).
 *
 * For a "is the user plausibly logged in" check that survives page loads,
 * use hasDsrSession() instead.
 */
export function isDsrAuthenticated(): boolean {
  return !!_dsrAccessToken;
}

/**
 * Check if the DSR has a non-empty user object in localStorage.
 *
 * This is a hint that the user *was* logged in on this tab. The actual
 * session validity is determined server-side by the httpOnly cookie.
 */
export function hasDsrSession(): boolean {
  if (typeof localStorage === "undefined") return false;
  return !!localStorage.getItem(DSR_USER_KEY);
}

/**
 * Bootstrap the DSR session on page load.
 *
 * Call this from the DSR dashboard's onMounted() to silently refresh the
 * access token from the httpOnly cookie. If the cookie is absent or
 * expired, the user is redirected to /dsr/login.
 *
 * Returns the new access token on success, or null (and redirects) on
 * failure.
 */
export async function bootstrapDsrSession(): Promise<string | null> {
  // If we already have an in-memory token (e.g., user just logged in),
  // no need to refresh.
  if (_dsrAccessToken) return _dsrAccessToken;

  const token = await refreshDsrAccessToken();
  if (!token) {
    if (typeof window !== "undefined") {
      window.location.href = "/dsr/login";
    }
    return null;
  }
  return token;
}

export default dsrApi;
