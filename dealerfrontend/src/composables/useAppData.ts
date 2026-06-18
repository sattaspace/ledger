/**
 * useAppData — shared dealer business data (products, sales, dsrs, etc.).
 *
 * Extracted from App.vue so all tab pages (inventory, sales, reports, etc.)
 * share the same cached state across Astro MPA navigations.
 *
 * Module-level singletons persist as long as the JS module graph is loaded
 * (one tab session). On a fresh tab, ensureLoaded() re-fetches everything.
 *
 * The ensureLoaded() chain waits for useAuth.fetchProfile() to complete
 * before fetching dealer data — this fixes the X-Plan-Limits header race
 * (the access map must be populated before dealer-backend calls so the
 * backend can enforce plan limits correctly).
 */

import { ref } from "vue";
import type {
  Product,
  SaleRecord,
  DSR,
  Supplier,
  RestockRecord,
  Brand,
  Category,
} from "../types";
import {
  inventoryService,
  salesService,
  dsrService,
  supplierService,
  reportsService,
} from "../services/api";
import type { SummaryData } from "../services/api/reports.service";
import { useAuth } from "./useAuth";
import { useDealerContext } from "./useDealerContext";
import { useAccess } from "./useAccess";
import { useToasts } from "./useToasts";
// Audit fix H2: read the user role + portal flag from leaf stores instead
// of using require() (which is undefined in ESM and always threw).
import { isDealerUser } from "../lib/userStore";
import { setSharedUser } from "../lib/userStore";
// DSR portal mode: fetch effective_access from the DSR backend instead
// of /billing/auth/me on SattaBase (which rejects DSR JWTs).
import { getDsrUser } from "../services/dsrClient";
import { useDsrAccessRefresh } from "./useDsrAccessRefresh";
// Re-export useSettingsModal for the loadDatabase() call below
import { useSettingsModal } from "./useSettingsModal";

// ─── Module-level shared state ───────────────────────────────────────────────

const products = ref<Product[]>([]);
const sales = ref<SaleRecord[]>([]);
const dsrs = ref<DSR[]>([]);
const suppliers = ref<Supplier[]>([]);
const restocksList = ref<RestockRecord[]>([]);
const summary = ref<SummaryData | null>(null);
const brands = ref<Brand[]>([]);
const categories = ref<Category[]>([]);

const loading = ref(false);
const initialized = ref(false);
let loadPromise: Promise<void> | null = null;

// ─── Internal loader ─────────────────────────────────────────────────────────

async function loadDatabase(): Promise<void> {
  const { user, isAuthenticated, initialized: authInitialized } = useAuth();
  const { initDealerContext, selectedDealer } = useDealerContext();
  const { triggerErrorToast } = useToasts();

  // ── DSR PORTAL MODE: skip /billing/auth/me entirely ──────────────
  //
  // When a DSR enters portal mode, the middleware sets the DSR access
  // token as locals.accessToken. BaseLayout puts it in
  // window.__INITIAL_AUTH_TOKEN__, and tokenStore hydrates it.
  //
  // BUT that token is a DSR JWT (issued by dealerbackend 8088), NOT a
  // SattaBase dealer JWT. If we call /billing/auth/me on SattaBase
  // (8086), SattaBase rejects the DSR JWT → 401 → the 401 handler
  // tries to refresh the dealer token (no sb_refresh_token cookie) →
  // fails → redirects to /login. That's the bug.
  //
  // Fix: in DSR portal mode, skip /billing/auth/me. Instead:
  //   1. Set the user from localStorage (dsr_user)
  //   2. Fetch the access map from the DSR backend's refresh-access
  //      endpoint (which returns effective_access — the intersection
  //      of the dealer's plan-level access and the DSR's per-dealer
  //      permissions)
  if (useDsrPortalSafe()) {
    try {
      // Fetch the effective_access map from the DSR backend.
      // This is the SAME call that handleEnterPortal made before
      // navigating — but after a full page reload, the in-memory
      // access map is gone, so we need to re-fetch it.
      const { refreshDsrAccess } = useDsrAccessRefresh();
      await refreshDsrAccess(true);
    } catch {
      // If refreshAccess fails, continue with whatever access map is
      // available (possibly empty). The backend will still enforce
      // permissions server-side.
    }

    // Set the user from localStorage so useAuth().user is populated
    // for components that read it (e.g., AppHeader, dealer context init).
    const dsrUser = getDsrUser();
    if (dsrUser) {
      setSharedUser(dsrUser as any);
    }

    // Skip the /billing/auth/me call — proceed directly to loading
    // dealer business data (which uses the DSR JWT via the
    // services/apiClient.ts, not the SattaBase apiClient).
  } else {
    // ── STANDARD DEALER AUTH PATH ──────────────────────────────────
    // Wait for auth to settle before any dealer-backend call
    if (!authInitialized.value) {
      await useAuth().fetchProfile();
    }

    if (!isAuthenticated.value) {
      // Not authenticated — bail out
      return;
    }
  }

  loading.value = true;
  try {
    // Initialize dealer context first (auto-selects dealer based on user_id)
    await initDealerContext(user.value, isDealerUser());

    const [pRes, sRes, dRes, supRes, sumRes, restRes, brandRes, catRes] =
      await Promise.all([
        inventoryService.getAllProducts(),
        salesService.getAllSales(),
        dsrService.getAllDsrs(),
        supplierService.getAllSuppliers(),
        reportsService.getSummary(),
        inventoryService.getAllRestocks(),
        inventoryService.getBrands(),
        inventoryService.getCategories(),
      ]);

    if (!pRes.ok || !sRes.ok || !dRes.ok || !supRes.ok || !sumRes.ok) {
      throw new Error("Some API resources failed to load.");
    }

    products.value = pRes.data;
    sales.value = sRes.data;
    dsrs.value = dRes.data;
    suppliers.value = supRes.data;
    summary.value = sumRes.data;
    if (restRes.ok) restocksList.value = restRes.data;
    if (brandRes.ok) brands.value = brandRes.data;
    if (catRes.ok) categories.value = catRes.data;

    // Sync settings modal with selected dealer
    const { syncFromDealer } = useSettingsModal();
    syncFromDealer(selectedDealer.value as any);

    initialized.value = true;
  } catch (err: any) {
    console.error("[APP DATA] loadDatabase ERROR:", err);
    triggerErrorToast(
      "Trouble loading system database. Please refresh the page.",
    );
  } finally {
    loading.value = false;
  }
}

// Local helpers (avoid circular import with useDsrPortal)
// Audit fix H2: previously used require("./useDsrPortal") inside try/catch,
// but require() is undefined in ESM (Astro/Vite), so the catch always fired
// and useDsrPortalSafe() always returned false — breaking the data-load
// path for DSR portal mode.
//
// We now read the portal-mode flag directly from localStorage (the same
// source that useDsrPortal.ts hydrates from).
function useDsrPortalSafe(): boolean {
  if (typeof localStorage === "undefined") return false;
  try {
    return localStorage.getItem("dealercore:dsr_portal_mode") === "true";
  } catch {
    return false;
  }
}

// ─── Public composable ───────────────────────────────────────────────────────

export function useAppData() {
  // Audit fix TS-9: removed unused `user` and `isAuthenticated` from
  // useAuth() destructure. They were left over from an earlier design
  // where the public composable exposed them — but the current return
  // value doesn't include them, and no code in this function body
  // references them. (The loadDatabase() inner function calls useAuth()
  // separately on line 62 to get the values it needs.)
  const { selectedDealer: activeDealer } = useDealerContext();
  // Audit fix TS-9: removed unused `hasAccess` from the destructure.
  // Only `getLimit` is actually used (for maxProducts / maxDsrs / maxSuppliers).
  const { getLimit } = useAccess();

  /**
   * Idempotent loader — returns immediately if data is already loaded,
   * otherwise kicks off (or joins) the load promise.
   *
   * Safe to call from every page's onMounted().
   */
  async function ensureLoaded(): Promise<void> {
    if (initialized.value) return;
    if (loadPromise) return loadPromise;
    loadPromise = loadDatabase();
    return loadPromise;
  }

  /**
   * Force a fresh fetch — used after CRUD operations and dealer switches.
   */
  async function refreshAll(): Promise<void> {
    loading.value = true;
    try {
      const [sumRes, pRes, sRes, dRes, restRes, brandRes, catRes, supRes] =
        await Promise.all([
          reportsService.getSummary(),
          inventoryService.getAllProducts(),
          salesService.getAllSales(),
          dsrService.getAllDsrs(),
          inventoryService.getAllRestocks(),
          inventoryService.getBrands(),
          inventoryService.getCategories(),
          supplierService.getAllSuppliers(),
        ]);

      if (sumRes.ok) summary.value = sumRes.data;
      if (pRes.ok) products.value = pRes.data;
      if (sRes.ok) sales.value = sRes.data;
      if (dRes.ok) dsrs.value = dRes.data;
      if (restRes.ok) restocksList.value = restRes.data;
      if (brandRes.ok) brands.value = brandRes.data;
      if (catRes.ok) categories.value = catRes.data;
      if (supRes.ok) suppliers.value = supRes.data;

      const { syncFromDealer } = useSettingsModal();
      syncFromDealer(activeDealer.value as any);
    } catch (err) {
      console.error("[APP DATA] refreshAll error:", err);
    } finally {
      loading.value = false;
    }
  }

  /**
   * Invalidate the cache — next ensureLoaded() will re-fetch.
   */
  function invalidate(): void {
    initialized.value = false;
    loadPromise = null;
  }

  function clearAll(): void {
    products.value = [];
    sales.value = [];
    dsrs.value = [];
    suppliers.value = [];
    restocksList.value = [];
    summary.value = null;
    brands.value = [];
    categories.value = [];
    initialized.value = false;
    loadPromise = null;
  }

  const formatCurrency = (amt: number): string => {
    const cur = activeDealer.value?.defaultCurrency || "INR";
    const loc = activeDealer.value?.defaultLocale || "en-IN";
    return new Intl.NumberFormat(loc, {
      style: "currency",
      currency: cur,
      maximumFractionDigits: 0,
    }).format(amt);
  };

  // Plan limits for enforcement
  const maxProducts = getLimit("max_products", 0);
  const maxDsrs = getLimit("max_dsrs", 0);
  const maxSuppliers = getLimit("max_suppliers", 0);

  return {
    // State
    products,
    sales,
    dsrs,
    suppliers,
    restocksList,
    summary,
    brands,
    categories,
    loading,
    initialized,
    // Actions
    ensureLoaded,
    refreshAll,
    invalidate,
    clearAll,
    // Helpers
    formatCurrency,
    maxProducts,
    maxDsrs,
    maxSuppliers,
  };
}
