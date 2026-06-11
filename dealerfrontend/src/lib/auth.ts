/**
 * DEALERCORE v3.0 — Authentication Library
 *
 * Handles all authentication operations with dealerbackend.
 * Manages JWT tokens, session persistence, and auto-refresh.
 */

import { ref, computed, readonly } from 'vue';

// ─── Configuration ─────────────────────────────────────────────────────────

const API_BASE_URL = import.meta.env.PUBLIC_API_BASE_URL || 'http://localhost:8088/api';
const ACCESS_TOKEN_KEY = 'dealercore_access_token';
const USER_KEY = 'dealercore_user';

// ─── Types ─────────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  subscription?: {
    status: string;
    plan_name: string;
    current_period_end?: string;
  };
  access_map?: Record<string, any>;
}

export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  error: string | null;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  user: User;
  message: string;
}

// ─── Reactive State ────────────────────────────────────────────────────────

const isLoading = ref(false);
const user = ref<User | null>(null);
const error = ref<string | null>(null);

export const authState = readonly({
  isAuthenticated: computed(() => !!user.value),
  isLoading: readonly(isLoading),
  user: readonly(user),
  error: readonly(error),
});

// ─── Token Management ──────────────────────────────────────────────────────

/**
 * Get access token from memory/storage
 */
export function getAccessToken(): string | null {
  // Try memory first (window level for view transitions)
  if (typeof window !== 'undefined' && (window as any).__dealercore_auth?.accessToken) {
    return (window as any).__dealercore_auth.accessToken;
  }
  
  // Fall back to sessionStorage
  try {
    return sessionStorage.getItem(ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Store access token in memory and sessionStorage
 */
export function setAccessToken(token: string): void {
  // Store in window for view transitions
  if (typeof window !== 'undefined') {
    if (!(window as any).__dealercore_auth) {
      (window as any).__dealercore_auth = {};
    }
    (window as any).__dealercore_auth.accessToken = token;
    
    // Also store in sessionStorage
    try {
      sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
    } catch {
      // Ignore storage errors
    }
  }
}

/**
 * Clear access token from memory and storage
 */
export function clearAccessToken(): void {
  if (typeof window !== 'undefined') {
    if ((window as any).__dealercore_auth) {
      delete (window as any).__dealercore_auth.accessToken;
    }
    
    try {
      sessionStorage.removeItem(ACCESS_TOKEN_KEY);
      sessionStorage.removeItem(USER_KEY);
    } catch {
      // Ignore storage errors
    }
  }
}

/**
 * Store user data
 */
export function setUser(userData: User): void {
  user.value = userData;
  
  try {
    sessionStorage.setItem(USER_KEY, JSON.stringify(userData));
  } catch {
    // Ignore storage errors
  }
}

/**
 * Clear user data
 */
export function clearUser(): void {
  user.value = null;
  clearAccessToken();
}

// ─── API Client ────────────────────────────────────────────────────────────

/**
 * Make authenticated API request
 */
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  
  // Add auth header if we have a token
  const token = getAccessToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include', // Include cookies for refresh token
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    // Handle 401 - try refresh if we have a token
    if (response.status === 401 && token) {
      const refreshed = await refreshToken();
      if (refreshed) {
        // Retry the request
        return apiRequest(endpoint, options);
      }
    }
    
    throw new Error(data.detail || data.message || 'Request failed');
  }
  
  return data;
}

// ─── Authentication Functions ──────────────────────────────────────────────

/**
 * Login with email and password
 */
export async function login(credentials: LoginCredentials): Promise<LoginResponse> {
  isLoading.value = true;
  error.value = null;
  
  try {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include', // Accept httpOnly cookie
      body: JSON.stringify(credentials),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }
    
    // Store access token
    setAccessToken(data.access);
    
    // Store user
    setUser(data.user);
    
    return data;
  } catch (err: any) {
    error.value = err.message || 'Login failed';
    throw err;
  } finally {
    isLoading.value = false;
  }
}

/**
 * Logout user
 */
export async function logout(): Promise<void> {
  isLoading.value = true;
  
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } catch {
    // Ignore errors, we want to clear local state anyway
  } finally {
    clearUser();
    isLoading.value = false;
  }
}

/**
 * Refresh access token using refresh cookie
 */
export async function refreshToken(): Promise<boolean> {
  const currentToken = getAccessToken();
  if (!currentToken) return false;
  
  try {
    const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include', // Send httpOnly cookie
    });
    
    if (!response.ok) {
      // Refresh failed - clear auth
      clearUser();
      return false;
    }
    
    const data = await response.json();
    setAccessToken(data.access);
    
    return true;
  } catch {
    return false;
  }
}

/**
 * Get current user info
 */
export async function getMe(): Promise<User> {
  const data = await apiRequest<User>('/auth/me');
  setUser(data);
  return data;
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/**
 * Initialize auth state from storage
 */
export function initAuth(): void {
  try {
    const token = sessionStorage.getItem(ACCESS_TOKEN_KEY);
    const userData = sessionStorage.getItem(USER_KEY);
    
    if (token && userData) {
      setAccessToken(token);
      user.value = JSON.parse(userData);
    }
  } catch {
    // Ignore storage errors
  }
}

/**
 * Generate SSO authorization code for SattaBase
 */
export async function generateAuthCode(): Promise<string> {
  const data = await apiRequest<{ code: string; expires_in: number }>('/auth/sso/authorize');
  return data.code;
}

// ─── Auto-refresh Setup ─────────────────────────────────────────────────────

let refreshInterval: ReturnType<typeof setInterval> | null = null;

/**
 * Start auto-refresh timer (call every 5 minutes)
 */
export function startAutoRefresh(): void {
  if (refreshInterval) return;
  
  refreshInterval = setInterval(() => {
    if (isAuthenticated()) {
      refreshToken().catch(() => {
        // Ignore errors, handled by interceptor
      });
    }
  }, 5 * 60 * 1000); // 5 minutes
}

/**
 * Stop auto-refresh timer
 */
export function stopAutoRefresh(): void {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

// ─── Session Expiry Detection ───────────────────────────────────────────────

/**
 * Handle session expired
 */
export function handleSessionExpired(): void {
  clearUser();
  
  // Emit event for UI to handle
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('auth:session-expired'));
  }
}

// Initialize on module load
initAuth();
