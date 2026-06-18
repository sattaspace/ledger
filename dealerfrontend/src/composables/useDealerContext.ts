/**
 * useDealerContext — Dealer selection state for multi-tenancy.
 *
 * Manages the active dealer context for DSRs/Collectors who may work
 * for multiple dealers. Dealers always work with their own data,
 * while DSRs need to select which dealer's data they're working with.
 *
 * The selected dealer is:
 * 1. Stored in localStorage for persistence across sessions
 * 2. Sent as X-Dealer-Username header in API requests
 * 3. Validated against the user's dealer assignments
 *
 * IMPORTANT: The dealer's username is the user_id from SattaBase JWT.
 * SattaBase does NOT have usernames - it uses user_id (e.g., "1").
 * The DealerConfig.username field stores this user_id as the primary key.
 *
 * Usage:
 *   const { selectedDealer, dealers, selectDealer, isMultiDealer } = useDealerContext();
 */

// Audit fix TS-11: removed unused `watch` import (no watch() calls in this file).
import { ref, computed } from "vue";
import { dealerService } from "../services/api";
import type { DealerConfig, User } from "../lib/types";

// ─── Storage Key ─────────────────────────────────────────────────────────────

const DEALER_CONTEXT_KEY = "dealercore:selected_dealer";

// ─── Module-level shared state (singleton) ────────────────────────────────────

const sharedDealers = ref<DealerConfig[]>([]);
const sharedSelectedDealer = ref<DealerConfig | null>(null);
const sharedLoading = ref(false);
const sharedError = ref<Error | null>(null);
const sharedInitialized = ref(false);
let fetchPromise: Promise<DealerConfig[] | null> | null = null;

// ─── Initialize from localStorage ─────────────────────────────────────────────

function initFromStorage(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(DEALER_CONTEXT_KEY);
  } catch {
    return null;
  }
}

// ─── Internal fetch ───────────────────────────────────────────────────────────

async function fetchDealers(): Promise<DealerConfig[] | null> {
  sharedLoading.value = true;
  sharedError.value = null;

  console.log(
    "%c[DEALER CONTEXT] Fetching dealers...",
    "color: #8b5cf6; font-weight: bold",
  );

  try {
    // Use dealerService which handles snake_case → camelCase transformation
    const response = await dealerService.getAllDealers();

    console.log(
      "%c[DEALER CONTEXT] Dealer fetch response",
      "color: #8b5cf6; font-weight: bold",
      {
        ok: response.ok,
        dealerCount: Array.isArray(response.data) ? response.data.length : 0,
        dealers: response.data,
      },
    );

    if (response.ok && Array.isArray(response.data)) {
      sharedDealers.value = response.data;
      sharedInitialized.value = true;
      return response.data;
    }
    return [];
  } catch (err) {
    console.error(
      "%c[DEALER CONTEXT] Fetch error",
      "color: #ef4444; font-weight: bold",
      err,
    );

    sharedError.value =
      err instanceof Error ? err : new Error("Failed to fetch dealers");
    return null;
  } finally {
    sharedLoading.value = false;
    fetchPromise = null;
  }
}

// ─── Public composable ────────────────────────────────────────────────────────

export function useDealerContext() {
  const dealers = sharedDealers;
  const selectedDealer = sharedSelectedDealer;
  const loading = sharedLoading;
  const error = sharedError;
  const initialized = sharedInitialized;

  /**
   * Whether the current user has access to multiple dealers.
   * Used to show/hide the dealer selector UI.
   */
  const isMultiDealer = computed(() => dealers.value.length > 1);

  /**
   * Whether a dealer context is required but not selected.
   * Used to show error states.
   */
  const requiresSelection = computed(() => {
    return dealers.value.length > 0 && !selectedDealer.value;
  });

  /**
   * Fetch available dealers for the current user.
   * This should be called after authentication.
   */
  async function fetchAvailableDealers(): Promise<DealerConfig[] | null> {
    // Return cached data if already loaded
    if (sharedInitialized.value && dealers.value.length > 0) {
      return dealers.value;
    }

    // Deduplicate concurrent fetches
    if (fetchPromise) return fetchPromise;

    fetchPromise = fetchDealers();
    return fetchPromise;
  }

  /**
   * Select a dealer as the active context.
   * Stores the selection in localStorage for persistence.
   */
  function selectDealer(dealer: DealerConfig): void {
    console.log(
      "%c[DEALER CONTEXT] Selecting dealer",
      "color: #10b981; font-weight: bold",
      {
        username: dealer.username,
        businessName: dealer.businessName,
        fullName: dealer.fullName,
      },
    );

    sharedSelectedDealer.value = dealer;

    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(DEALER_CONTEXT_KEY, dealer.username);
        console.log(
          "%c[DEALER CONTEXT] Saved to localStorage",
          "color: #10b981;",
          { key: DEALER_CONTEXT_KEY, value: dealer.username },
        );
      } catch {
        // Storage unavailable
      }
    }

    // Dispatch event so API client can update headers
    if (typeof window !== "undefined") {
      window.dispatchEvent(
        new CustomEvent("dealercore:dealer-changed", {
          detail: { dealer },
        }),
      );
    }
  }

  /**
   * Auto-select a dealer based on user type and stored preference.
   *
   * For Dealer users: Auto-select dealer matching their user_id
   * For DSR users: Use stored preference or first available
   *
   * @param user - The current user from auth (contains id for dealer matching)
   * @param isDealer - Whether the user is a dealer (not a DSR)
   */
  function autoSelectDealer(
    user?: User | null,
    isDealer?: boolean,
  ): DealerConfig | null {
    console.log(
      "%c[DEALER CONTEXT] Auto-selecting dealer",
      "color: #f59e0b; font-weight: bold",
      {
        dealerCount: dealers.value.length,
        isDealer,
        userId: user?.id,
        availableDealers: dealers.value.map((d) => ({
          username: d.username,
          businessName: d.businessName,
        })),
      },
    );

    if (dealers.value.length === 0) {
      console.warn(
        "%c[DEALER CONTEXT] No dealers available to select!",
        "color: #ef4444; font-weight: bold",
      );
      return null;
    }

    // Case 1: User is a Dealer - select dealer matching their user_id
    if (isDealer && user?.id) {
      const userIdString = String(user.id);
      console.log(
        `%c[DEALER CONTEXT] Looking for dealer with username=user_id="${userIdString}"`,
        "color: #f59e0b;",
      );
      const dealerByUserId = dealers.value.find(
        (d) => d.username === userIdString,
      );
      if (dealerByUserId) {
        console.log(
          "%c[DEALER CONTEXT] Found matching dealer by user_id",
          "color: #10b981;",
          dealerByUserId,
        );
        selectDealer(dealerByUserId);
        return dealerByUserId;
      }
      // If no matching dealer found, fall through to default selection
      console.warn(
        `%c[DEALER CONTEXT] No DealerConfig found for user_id: ${userIdString}`,
        "color: #ef4444; font-weight: bold",
      );
      console.warn(
        "Available dealer usernames:",
        dealers.value.map((d) => d.username),
      );
    }

    // Case 2: Single dealer - auto-select
    if (dealers.value.length === 1) {
      console.log(
        "%c[DEALER CONTEXT] Single dealer - auto-selecting",
        "color: #10b981;",
        dealers.value[0],
      );
      selectDealer(dealers.value[0]);
      return dealers.value[0];
    }

    // Case 3: Multiple dealers - check stored preference
    const storedUsername = initFromStorage();
    console.log(
      "%c[DEALER CONTEXT] Checking stored preference",
      "color: #f59e0b;",
      { storedUsername },
    );
    if (storedUsername) {
      const storedDealer = dealers.value.find(
        (d) => d.username === storedUsername,
      );
      if (storedDealer) {
        console.log(
          "%c[DEALER CONTEXT] Found stored dealer preference",
          "color: #10b981;",
          storedDealer,
        );
        selectDealer(storedDealer);
        return storedDealer;
      }
    }

    // Case 4: No valid stored preference - select first
    console.log(
      "%c[DEALER CONTEXT] No valid preference - selecting first dealer",
      "color: #f59e0b;",
      dealers.value[0],
    );
    selectDealer(dealers.value[0]);
    return dealers.value[0];
  }

  /**
   * Initialize dealer context - fetch dealers and auto-select.
   * Should be called after authentication is confirmed.
   *
   * @param user - The current user from auth (contains id for dealer matching)
   * @param isDealer - Whether the user is a dealer (not a DSR)
   */
  async function initDealerContext(
    user?: User | null,
    isDealer?: boolean,
  ): Promise<DealerConfig | null> {
    const fetchedDealers = await fetchAvailableDealers();
    if (fetchedDealers && fetchedDealers.length > 0) {
      return autoSelectDealer(user, isDealer);
    }
    return null;
  }

  /**
   * Clear the selected dealer context.
   * Used during logout.
   */
  function clearDealerContext(): void {
    sharedSelectedDealer.value = null;
    sharedDealers.value = [];
    sharedInitialized.value = false;
    fetchPromise = null;

    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem(DEALER_CONTEXT_KEY);
      } catch {
        // Storage unavailable
      }
    }
  }

  /**
   * Get the selected dealer username for API headers.
   * Returns null if no dealer is selected.
   */
  function getSelectedDealerUsername(): string | null {
    return selectedDealer.value?.username ?? null;
  }

  return {
    dealers,
    selectedDealer,
    loading,
    error,
    initialized,
    isMultiDealer,
    requiresSelection,
    fetchAvailableDealers,
    selectDealer,
    autoSelectDealer,
    initDealerContext,
    clearDealerContext,
    getSelectedDealerUsername,
  };
}
