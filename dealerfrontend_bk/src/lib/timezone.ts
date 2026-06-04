/**
 * Timezone utilities for Satta Ledger frontend.
 *
 * All timestamps from the backend are in UTC (ISO 8601).
 * The frontend converts them to the user's selected timezone for display.
 * The user's timezone comes from /billing/auth/me → user.timezone.
 *
 * Architecture:
 *   - Store timestamps in UTC in the database
 *   - API returns UTC ISO strings ("2025-01-15T10:30:00Z")
 *   - Frontend converts to user.timezone for display
 *   - Frontend sends UTC when posting back to API
 */

// ─── Storage ────────────────────────────────────────────────────────────────

const TIMEZONE_KEY = "sattabase-ledger:user_timezone";

// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Store the user's timezone preference from auth/me.
 */
export function cacheUserTimezone(timezone: string | null | undefined): void {
  if (typeof window === "undefined" || !timezone) return;
  try {
    sessionStorage.setItem(TIMEZONE_KEY, timezone);
  } catch {
    // ignore
  }
}

/**
 * Get the cached user timezone.
 * Falls back to the browser's timezone, then "UTC".
 */
export function getUserTimezone(): string {
  if (typeof window === "undefined") return "UTC";

  const cached = sessionStorage.getItem(TIMEZONE_KEY);
  if (cached) return cached;

  // Try browser timezone
  try {
    const browserTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (browserTz) return browserTz;
  } catch {
    // fallback
  }

  return "UTC";
}

/**
 * Format a UTC ISO string in the user's timezone.
 *
 * @param utcDateString - ISO 8601 string from API (e.g. "2025-01-15T10:30:00Z")
 * @param options - Intl.DateTimeFormat options
 * @returns Formatted date/time string in user's timezone
 */
export function formatInUserTimezone(
  utcDateString: string | null | undefined,
  options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  },
): string {
  if (!utcDateString) return "—";

  try {
    const date = new Date(utcDateString);
    if (isNaN(date.getTime())) return "—";

    const timezone = getUserTimezone();

    return new Intl.DateTimeFormat("en-US", {
      ...options,
      timeZone: timezone,
    }).format(date);
  } catch {
    return "—";
  }
}

/**
 * Format a date as a short date in user's timezone.
 * Example: "Jan 15, 2025"
 */
export function formatDateShort(utcDateString: string | null | undefined): string {
  return formatInUserTimezone(utcDateString, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/**
 * Format a date with time in user's timezone.
 * Example: "Jan 15, 2025, 4:30 PM"
 */
export function formatDateTime(utcDateString: string | null | undefined): string {
  return formatInUserTimezone(utcDateString, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a time only in user's timezone.
 * Example: "4:30 PM"
 */
export function formatTimeOnly(utcDateString: string | null | undefined): string {
  return formatInUserTimezone(utcDateString, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format a relative time string (e.g. "2 hours ago", "3 days ago").
 */
export function formatRelativeTime(utcDateString: string | null | undefined): string {
  if (!utcDateString) return "—";

  try {
    const date = new Date(utcDateString);
    if (isNaN(date.getTime())) return "—";

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return "just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    if (diffDay < 30) return `${Math.floor(diffDay / 7)}w ago`;

    return formatDateShort(utcDateString);
  } catch {
    return "—";
  }
}

/**
 * Get the current timezone offset display string.
 * Example: "GMT+6" for Asia/Dhaka
 */
export function getTimezoneOffsetDisplay(): string {
  const timezone = getUserTimezone();
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      timeZoneName: "shortOffset",
    });
    const parts = formatter.formatToParts(new Date());
    const tzPart = parts.find((p) => p.type === "timeZoneName");
    return tzPart?.value ?? timezone;
  } catch {
    return timezone;
  }
}

/**
 * Clear cached timezone (on logout).
 */
export function clearUserTimezone(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(TIMEZONE_KEY);
  } catch {
    // ignore
  }
}
