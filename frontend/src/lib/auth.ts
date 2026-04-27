/**
 * Auth utilities — provides helper functions for authentication state
 * management across Vue components (client-side only).
 *
 * Uses localStorage for JWT tokens.
 */

import { authHelpers, apiClient } from "./api";
import type { ApiError } from "./api";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  timezone: string;
  currency: string;
  language: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface UserProfile {
  id: number;
  slug: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  timezone: string;
  currency: string;
  language: string;
  is_email_verified: boolean;
  role: string;
  avatar: string | null;
  created_at: string;
  full_name: string;
  display_name: string;
}

// // ─── Choice Options (synced with backend) ────────────────────────────────────

// export const TIMEZONE_OPTIONS = [
//   { value: "UTC", label: "UTC" },
//   // Americas
//   { value: "America/New_York", label: "Eastern Time (US & Canada)" },
//   { value: "America/Chicago", label: "Central Time (US & Canada)" },
//   { value: "America/Denver", label: "Mountain Time (US & Canada)" },
//   { value: "America/Los_Angeles", label: "Pacific Time (US & Canada)" },
//   { value: "America/Anchorage", label: "Alaska" },
//   { value: "Pacific/Honolulu", label: "Hawaii" },
//   { value: "America/Toronto", label: "Eastern Time (Canada)" },
//   { value: "America/Vancouver", label: "Pacific Time (Canada)" },
//   { value: "America/Mexico_City", label: "Mexico City" },
//   { value: "America/Sao_Paulo", label: "Sao Paulo" },
//   { value: "America/Argentina/Buenos_Aires", label: "Buenos Aires" },
//   { value: "America/Bogota", label: "Bogota" },
//   { value: "America/Lima", label: "Lima" },
//   { value: "America/Santiago", label: "Santiago" },
//   // Europe
//   { value: "Europe/London", label: "London" },
//   { value: "Europe/Dublin", label: "Dublin" },
//   { value: "Europe/Paris", label: "Paris" },
//   { value: "Europe/Berlin", label: "Berlin" },
//   { value: "Europe/Madrid", label: "Madrid" },
//   { value: "Europe/Rome", label: "Rome" },
//   { value: "Europe/Amsterdam", label: "Amsterdam" },
//   { value: "Europe/Brussels", label: "Brussels" },
//   { value: "Europe/Vienna", label: "Vienna" },
//   { value: "Europe/Stockholm", label: "Stockholm" },
//   { value: "Europe/Oslo", label: "Oslo" },
//   { value: "Europe/Copenhagen", label: "Copenhagen" },
//   { value: "Europe/Helsinki", label: "Helsinki" },
//   { value: "Europe/Warsaw", label: "Warsaw" },
//   { value: "Europe/Lisbon", label: "Lisbon" },
//   { value: "Europe/Athens", label: "Athens" },
//   { value: "Europe/Prague", label: "Prague" },
//   { value: "Europe/Budapest", label: "Budapest" },
//   { value: "Europe/Bucharest", label: "Bucharest" },
//   // Asia
//   { value: "Asia/Dubai", label: "Dubai" },
//   { value: "Asia/Riyadh", label: "Riyadh" },
//   { value: "Asia/Kolkata", label: "India (IST)" },
//   { value: "Asia/Karachi", label: "Pakistan" },
//   { value: "Asia/Dhaka", label: "Bangladesh (BST)" },
//   { value: "Asia/Colombo", label: "Sri Lanka" },
//   { value: "Asia/Kathmandu", label: "Nepal" },
//   { value: "Asia/Bangkok", label: "Bangkok" },
//   { value: "Asia/Ho_Chi_Minh", label: "Ho Chi Minh City" },
//   { value: "Asia/Jakarta", label: "Jakarta" },
//   { value: "Asia/Kuala_Lumpur", label: "Kuala Lumpur" },
//   { value: "Asia/Singapore", label: "Singapore" },
//   { value: "Asia/Manila", label: "Manila" },
//   { value: "Asia/Shanghai", label: "Shanghai" },
//   { value: "Asia/Hong_Kong", label: "Hong Kong" },
//   { value: "Asia/Taipei", label: "Taipei" },
//   { value: "Asia/Seoul", label: "Seoul" },
//   { value: "Asia/Tokyo", label: "Tokyo" },
//   // Oceania
//   { value: "Australia/Sydney", label: "Sydney" },
//   { value: "Australia/Melbourne", label: "Melbourne" },
//   { value: "Australia/Perth", label: "Perth" },
//   { value: "Pacific/Auckland", label: "Auckland" },
//   // Africa
//   { value: "Africa/Johannesburg", label: "Johannesburg" },
//   { value: "Africa/Nairobi", label: "Nairobi" },
//   { value: "Africa/Cairo", label: "Cairo" },
//   { value: "Africa/Lagos", label: "Lagos" },
//   { value: "Africa/Casablanca", label: "Casablanca" },
// ] as const;

// export const CURRENCY_OPTIONS = [
//   { value: "USD", label: "USD — US Dollar" },
//   { value: "EUR", label: "EUR — Euro" },
//   { value: "GBP", label: "GBP — British Pound" },
//   { value: "JPY", label: "JPY — Japanese Yen" },
//   { value: "CAD", label: "CAD — Canadian Dollar" },
//   { value: "AUD", label: "AUD — Australian Dollar" },
//   { value: "CHF", label: "CHF — Swiss Franc" },
//   { value: "CNY", label: "CNY — Chinese Yuan" },
//   { value: "HKD", label: "HKD — Hong Kong Dollar" },
//   { value: "NZD", label: "NZD — New Zealand Dollar" },
//   { value: "SEK", label: "SEK — Swedish Krona" },
//   { value: "KRW", label: "KRW — South Korean Won" },
//   { value: "SGD", label: "SGD — Singapore Dollar" },
//   { value: "INR", label: "INR — Indian Rupee" },
//   { value: "MXN", label: "MXN — Mexican Peso" },
//   { value: "BRL", label: "BRL — Brazilian Real" },
//   { value: "ZAR", label: "ZAR — South African Rand" },
//   { value: "RUB", label: "RUB — Russian Ruble" },
//   { value: "TRY", label: "TRY — Turkish Lira" },
//   { value: "AED", label: "AED — UAE Dirham" },
//   { value: "SAR", label: "SAR — Saudi Riyal" },
//   { value: "BDT", label: "BDT — Bangladeshi Taka" },
//   { value: "PKR", label: "PKR — Pakistani Rupee" },
//   { value: "PHP", label: "PHP — Philippine Peso" },
//   { value: "THB", label: "THB — Thai Baht" },
//   { value: "MYR", label: "MYR — Malaysian Ringgit" },
//   { value: "IDR", label: "IDR — Indonesian Rupiah" },
//   { value: "VND", label: "VND — Vietnamese Dong" },
//   { value: "NOK", label: "NOK — Norwegian Krone" },
//   { value: "DKK", label: "DKK — Danish Krone" },
//   { value: "PLN", label: "PLN — Polish Zloty" },
//   { value: "TWD", label: "TWD — Taiwan Dollar" },
//   { value: "NGN", label: "NGN — Nigerian Naira" },
//   { value: "EGP", label: "EGP — Egyptian Pound" },
//   { value: "KES", label: "KES — Kenyan Shilling" },
//   { value: "COP", label: "COP — Colombian Peso" },
//   { value: "CLP", label: "CLP — Chilean Peso" },
//   { value: "PEN", label: "PEN — Peruvian Sol" },
//   { value: "ARS", label: "ARS — Argentine Peso" },
// ] as const;

// export const LANGUAGE_OPTIONS = [
//   { value: "en", label: "English" },
//   { value: "es", label: "Spanish" },
//   { value: "fr", label: "French" },
//   { value: "de", label: "German" },
//   { value: "pt", label: "Portuguese" },
//   { value: "it", label: "Italian" },
//   { value: "nl", label: "Dutch" },
//   { value: "ru", label: "Russian" },
//   { value: "ja", label: "Japanese" },
//   { value: "ko", label: "Korean" },
//   { value: "zh", label: "Chinese" },
//   { value: "ar", label: "Arabic" },
//   { value: "hi", label: "Hindi" },
//   { value: "bn", label: "Bengali" },
//   { value: "tr", label: "Turkish" },
//   { value: "pl", label: "Polish" },
//   { value: "sv", label: "Swedish" },
//   { value: "da", label: "Danish" },
//   { value: "no", label: "Norwegian" },
//   { value: "fi", label: "Finnish" },
//   { value: "th", label: "Thai" },
//   { value: "vi", label: "Vietnamese" },
//   { value: "id", label: "Indonesian" },
//   { value: "ms", label: "Malay" },
//   { value: "tl", label: "Filipino" },
//   { value: "uk", label: "Ukrainian" },
//   { value: "cs", label: "Czech" },
//   { value: "hu", label: "Hungarian" },
//   { value: "ro", label: "Romanian" },
//   { value: "el", label: "Greek" },
// ] as const;

// ─── Choice options (synced with backend via API) ────────────────────────────

export interface ChoiceOption {
  value: string;
  label: string;
}

export interface Choices {
  timezones: ChoiceOption[];
  currencies: ChoiceOption[];
  languages: ChoiceOption[];
}

let _choicesCache: Choices | null = null;
let _choicesPromise: Promise<Choices> | null = null;

/**
 * Fetch timezone, currency, language choices from the backend.
 *
 * Reads from Django model enums (TimezoneChoices, CurrencyChoices, LanguageChoices)
 * via `GET /api/v1/auth/choices`. Results are cached in memory for the page
 * lifetime — subsequent calls return the cached data instantly.
 *
 * Usage in a Vue component:
 * ```ts
 * const choices = ref<Choices>({ timezones: [], currencies: [], languages: [] });
 * onMounted(async () => { choices.value = await fetchChoices(); });
 * ```
 */
export async function fetchChoices(): Promise<Choices> {
  if (_choicesCache) return _choicesCache;
  if (_choicesPromise) return _choicesPromise;

  _choicesPromise = apiClient
    .get<Choices>("/auth/choices")
    .then((data) => {
      _choicesCache = data;
      _choicesPromise = null;
      return data;
    })
    .catch((err) => {
      _choicesPromise = null;
      console.error("Failed to fetch choices:", err);
      return { timezones: [], currencies: [], languages: [] };
    });

  return _choicesPromise;
}

/**
 * Return cached choices if already fetched, otherwise null.
 */
export function getCachedChoices(): Choices | null {
  return _choicesCache;
}

// ─── Auth functions ─────────────────────────────────────────────────────────

/**
 * Login — POST /auth/login → store tokens
 */
export async function login(payload: LoginPayload): Promise<AuthTokens> {
  const data = await apiClient.post<AuthTokens>("/auth/login", payload);
  authHelpers.setTokens(data.access, data.refresh);
  return data;
}

/**
 * Register — POST /auth/register
 */
export async function register(payload: RegisterPayload): Promise<void> {
  await apiClient.post("/auth/register", payload);
}

/**
 * Logout — clear tokens and redirect
 */
export async function logout(): Promise<void> {
  try {
    await apiClient.post("/users/me/logout");
  } catch {
    // Even if the API call fails, clear local tokens
  }
  authHelpers.clearTokens();
  if (typeof window !== "undefined") {
    window.location.href = "/auth/login";
  }
}

/**
 * Request password reset email — POST /auth/password-reset/request
 */
export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post("/auth/password-reset/request", { email });
}

/**
 * Confirm password reset — POST /auth/password-reset/confirm (OTP-based)
 */
export async function confirmPasswordReset(
  email: string,
  otp: string,
  new_password: string,
  confirm_password: string,
): Promise<void> {
  await apiClient.post("/auth/password-reset/confirm", {
    email,
    otp,
    new_password,
    confirm_password,
  });
}

/**
 * Change password (requires current password) — POST /users/me/change-password
 */
export async function changePassword(
  current_password: string,
  new_password: string,
  confirm_password: string,
): Promise<void> {
  await apiClient.post("/users/me/change-password", {
    current_password,
    new_password,
    confirm_password,
  });
}

/**
 * Request email change — POST /users/me/change-email
 * Sends a 6-digit OTP to the current email.
 */
export async function requestEmailChange(
  current_password: string,
  new_email: string,
): Promise<void> {
  await apiClient.post("/users/me/change-email", {
    current_password,
    new_email,
  });
}

/**
 * Confirm email change with OTP (authenticated) — POST /users/me/change-email/confirm
 */
export async function confirmEmailChangeOTP(otp: string): Promise<string> {
  const res = await apiClient.post<{ message: string; success: boolean }>(
    "/users/me/change-email/confirm",
    { otp },
  );
  return res.message;
}

/**
 * Request email verification — POST /auth/verify-email/request
 */
export async function requestEmailVerification(email: string): Promise<void> {
  await apiClient.post("/auth/verify-email/request", { email });
}

/**
 * Verify email with OTP — POST /auth/verify-email/confirm
 */
export async function verifyEmail(email: string, otp: string): Promise<void> {
  await apiClient.post("/auth/verify-email/confirm", { email, otp });
}

/**
 * Delete account — POST /users/me/delete-account
 */
export async function deleteAccount(current_password: string): Promise<void> {
  await apiClient.post("/users/me/delete-account", { current_password });
}

/**
 * Get current user profile — GET /users/me
 */
export async function getCurrentUser(): Promise<UserProfile> {
  return apiClient.get<UserProfile>("/users/me");
}

/**
 * Update user profile — PUT /users/me
 */
export async function updateProfile(
  data: Partial<Pick<UserProfile, "first_name" | "last_name" | "phone" | "timezone" | "currency" | "language">>,
): Promise<UserProfile> {
  return apiClient.put<UserProfile>("/users/me", data);
}

/**
 * Update avatar — PUT /users/me/avatar (multipart/form-data)
 *
 * Accepts a File object (from <input type="file">), validates type/size client-side,
 * then uploads via multipart/form-data. Returns the updated user profile with new avatar URL.
 *
 * @param file - The image file to upload
 * @throws Error if file type is invalid or file is too large
 */
export async function updateAvatar(file: File): Promise<UserProfile> {
  // Client-side validation
  const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];
  const MAX_SIZE = 2 * 1024 * 1024; // 2 MB

  if (!ALLOWED_TYPES.includes(file.type)) {
    throw {
      status: 400,
      message: "Invalid file type. Please upload a JPEG, PNG, GIF, or WebP image.",
    } as ApiError;
  }

  if (file.size > MAX_SIZE) {
    throw {
      status: 400,
      message: "File is too large. Maximum size is 2 MB.",
    } as ApiError;
  }

  const formData = new FormData();
  formData.append("avatar", file);

  return apiClient.uploadPut<UserProfile>("/users/me/avatar", formData);
}

/**
 * Delete avatar — DELETE /users/me/avatar
 * Removes the user's avatar and returns the updated profile.
 */
export async function deleteAvatar(): Promise<UserProfile> {
  return apiClient.delete<UserProfile>("/users/me/avatar");
}


// ─── Convenience ────────────────────────────────────────────────────────────

/**
 * Check if user is authenticated (has a non-expired access token).
 * Note: This only checks localStorage — it doesn't validate the token with the server.
 */
export function isAuthenticated(): boolean {
  return authHelpers.isAuthenticated();
}

/**
 * Redirect to login if not authenticated.
 */
export function requireAuth(): boolean {
  if (!isAuthenticated()) {
    if (typeof window !== "undefined") {
      window.location.href = "/auth/login";
    }
    return false;
  }
  return true;
}

/**
 * Format API error message for display.
 */
export function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    return (error as ApiError).message || "An unexpected error occurred.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "An unexpected error occurred. Please try again.";
}

// ─── Helper: Detect user timezone ──────────────────────────────────────────

// /**
//  * Try to detect the user's timezone from the browser.
//  * Falls back to "UTC" if detection fails or if the timezone isn't in our options.
//  */
// export function detectUserTimezone(): string {
//   if (typeof window === "undefined") return "UTC";
//   try {
//     const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
//     // Check if it's in our options
//     const known = TIMEZONE_OPTIONS.some((opt) => opt.value === detected);
//     return known ? detected : "UTC";
//   } catch {
//     return "UTC";
//   }
// }

// /**
//  * Try to detect the user's preferred language from the browser.
//  * Falls back to "en" if detection fails or if the language isn't in our options.
//  */
// export function detectUserLanguage(): string {
//   if (typeof window === "undefined") return "en";
//   try {
//     const browserLang = (navigator.language || "en").split("-")[0].toLowerCase();
//     const known = LANGUAGE_OPTIONS.some((opt) => opt.value === browserLang);
//     return known ? browserLang : "en";
//   } catch {
//     return "en";
//   }
// }
// ─── Helper: Detect user preferences ────────────────────────────────────────

/**
 * Try to detect the user's timezone from the browser.
 * Falls back to "UTC" if detection fails or if the timezone isn't in our options.
 */
export function detectUserTimezone(choices?: ChoiceOption[]): string {
  if (typeof window === "undefined") return "UTC";
  try {
    const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (choices) {
      const known = choices.some((opt) => opt.value === detected);
      return known ? detected : "UTC";
    }
    return detected || "UTC";
  } catch {
    return "UTC";
  }
}

/**
 * Try to detect the user's preferred language from the browser.
 * Falls back to "en" if detection fails or if the language isn't in our options.
 */
export function detectUserLanguage(choices?: ChoiceOption[]): string {
  if (typeof window === "undefined") return "en";
  try {
    const browserLang = (navigator.language || "en").split("-")[0].toLowerCase();
    if (choices) {
      const known = choices.some((opt) => opt.value === browserLang);
      return known ? browserLang : "en";
    }
    return browserLang || "en";
  } catch {
    return "en";
  }
}
