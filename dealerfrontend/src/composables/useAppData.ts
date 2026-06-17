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
  dealerService,
  reportsService,
} from "../services/api";
import type { SummaryData } from "../services/api/reports.service";
import { useAuth } from "./useAuth";
import { useDealerContext } from "./useDealerContext";
import { useAccess } from "./useAccess";
import { useToasts } from "./useToasts";

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

  // Wait for auth to settle before any dealer-backend call
  if (!authInitialized.value) {
    // Trigger a fetch (idempotent — returns cached if already loaded)
    await useAuth().fetchProfile();
  }

  if (!isAuthenticated.value && !useDsrPortalSafe()) {
    // Not authenticated and not in DSR portal mode — bail out
    return;
  }

  loading.value = true;
  try {
    // Initialize dealer context first (auto-selects dealer based on user_id)
    await initDealerContext(user.value, isDealerUser());

    const [
      pRes,
      sRes,
      dRes,
      supRes,
      sumRes,
      restRes,
      brandRes,
      catRes,
    ] = await Promise.all([
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
function useDsrPortalSafe(): boolean {
  try {
    // Lazy require to avoid module-load cycle
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const m = require("./useDsrPortal");
    return !!m?.useDsrPortal?.().dsrInPortalMode?.value;
  } catch {
    return false;
  }
}

function isDealerUser(): boolean {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const auth = require("./useAuth");
    const user = auth?.user?.value ?? auth?.useAuth?.()?.user?.value;
    return user?.is_dealer === true || user?.role === "dealer";
  } catch {
    return false;
  }
}

// ─── Public composable ───────────────────────────────────────────────────────

export function useAppData() {
  const { user, isAuthenticated } = useAuth();
  const { selectedDealer: activeDealer } = useDealerContext();
  const { hasAccess, getLimit } = useAccess();

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
      const [
        sumRes,
        pRes,
        sRes,
        dRes,
        restRes,
        brandRes,
        catRes,
        supRes,
      ] = await Promise.all([
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

// Re-export useSettingsModal for the loadDatabase() call above
import { useSettingsModal } from "./useSettingsModal";
