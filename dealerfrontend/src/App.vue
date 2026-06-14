<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { 
  Package, 
  ShoppingCart, 
  Coins, 
  FilePieChart, 
  LayoutDashboard, 
  Menu, 
  X, 
  AlertCircle,
  AlertTriangle,
  Smartphone,
  RefreshCw,
  LogOut,
  Settings,
  Sparkles,
  Award,
  Users,
  User,
  UserCircle,
  CreditCard
} from 'lucide-vue-next';
import { sattabaseUrls } from './lib/constants';
import type { DatabaseSchema, Product, SaleRecord, RestockRecord, DSR, Supplier, DealerConfig, Brand, Category } from './types';
// ─── Shared Utilities ──────────────────────────────────────────────────────
import { useFormatters } from './composables/useFormatters';
import { useAuth } from './composables/useAuth';
import { useAccess } from './composables/useAccess';
import { useDealerContext } from './composables/useDealerContext';
import './styles/utilities.css';

// ─── Authentication (must be before onMounted) ──────────────────────────────
const { isAuthenticated, logout, user, access, initialized: authInitialized, refreshUser } = useAuth();

// ─── Dealer Context (multi-tenancy) ──────────────────────────────────────────────
const { 
  selectedDealer: activeDealer, 
  dealers, 
  selectDealer: setDealerContext,
  initDealerContext 
} = useDealerContext();

// Check if user is a dealer (from auth response).
// FIX B-7: previously used `access.value?.is_dealer` / `access.value?.role`.
// During initial login `access.value` is still {} while /billing/auth/me
// is in flight, so `isDealerUser` evaluated to false and the wrong dealer
// was auto-selected. We now read the canonical `user.role` /
// `user.is_dealer` fields from the auth profile (set by useAuth).
const isDealerUser = computed(() => {
  return user.value?.is_dealer === true || user.value?.role === 'dealer';
});

import Overview from './components/Overview.vue';
import Inventory from './components/Inventory.vue';
import Sales from './components/Sales.vue';
import Collections from './components/Collections.vue';
import Reports from './components/Reports.vue';
import Suppliers from './components/Suppliers.vue';
import BadDebt from './components/BadDebt.vue';
import LoginPage from './components/LoginPage.vue';
import SessionGuard from './components/SessionGuard.vue';
import ManageBillingButton from './components/ManageBillingButton.vue';
import PermissionGuard from './components/PermissionGuard.vue';
import DealerSelector from './components/DealerSelector.vue';

// ─── DSR Authentication Components ──────────────────────────────────────
import DsrLoginPage from './components/DsrLoginPage.vue';
import DsrSelfRegisterPage from './components/DsrSelfRegisterPage.vue';
import DsrRegisterPage from './components/DsrRegisterPage.vue';
import DsrDashboard from './components/DsrDashboard.vue';
import DsrManagementPanel from './components/DsrManagementPanel.vue';
import AddRepModal from './components/AddRepModal.vue';
import dsrAuthService from './services/api/dsrAuth.service';

// ─── Centralized API Services ──────────────────────────────────────────
// All API communication flows through these service singletons.
// Backend: Django Ninja (async) — configured via VITE_API_BASE_URL in .env
import {
  inventoryService,
  salesService,
  dsrService,
  supplierService,
  dealerService,
  reportsService,
} from './services/api';
import type { SummaryData } from './services/api/reports.service';
import { ApiError } from './services/apiClient';
import { authHelpers } from './lib/api';

const CURRENCY_LOCALES: Record<string, string> = {
  INR: 'en-IN',
  USD: 'en-US',
  EUR: 'en-IE',
  GBP: 'en-GB',
  AED: 'en-AE',
  JPY: 'ja-JP',
  CAD: 'en-CA',
  AUD: 'en-AU',
  SGD: 'en-SG'
};

const activeTab = ref('overview');
const menuOpen = ref(false);

// ─── DSR Authentication State ───────────────────────────────────────────────
// View mode: 'dealer' (default dealer login) | 'dsr-login' | 'dsr-register' | 'dsr-dashboard' | 'dsr-register-invite'
const authView = ref<'dealer' | 'dsr-login' | 'dsr-register' | 'dsr-dashboard' | 'dsr-register-invite'>('dealer');
const dsrInviteToken = ref<string | null>(null);

// Use a reactive ref for DSR auth state that can be updated on login/logout
// Initialize from localStorage but make it reactive
const dsrAuthState = ref(!!localStorage.getItem('dsr_access_token'));

// Check DSR auth on mount (in case page was refreshed after DSR login)
const isDsrAuthenticated = computed(() => dsrAuthState.value);

// Database Core States
const products = ref<Product[]>([]);
const sales = ref<SaleRecord[]>([]);
const dsrs = ref<DSR[]>([]);
const suppliers = ref<Supplier[]>([]);
const restocksList = ref<RestockRecord[]>([]);
const summary = ref<SummaryData | null>(null);

// Brands & Categories State
const brands = ref<Brand[]>([]);
const categories = ref<Category[]>([]);

// Dealer / Settings State (settings modal fields)
const showSettingsModal = ref(false);
const showAddRepModal = ref(false);
// FIX B-5: ref to DsrManagementPanel so we can call fetchData() directly
// after a new invite is added. See @added handler below.
const dsrRosterRef = ref<{ fetchData: () => Promise<void> } | null>(null);
const settingsSelectedCurrency = ref('INR');
const settingsSelectedLocale = ref('en-IN');
const settingsBusinessName = ref('');
const settingsGstNumber = ref('');
const settingsPhoneNumber = ref('');
const settingsEmail = ref('');
const settingsCommunicationNumber = ref('');
const settingsGoogleMapUrl = ref('');
const settingsAddress = ref('');

// Dynamic notifications / banners loaders
const loading = ref(true);

// Centralized toast notification state
// successToast: green toast for successful CRUD operations
// errorToast: red toast for API errors (500, 400, network failures)
const successToast = ref('');
const errorToast = ref('');

// Context Transfer channels (Shortcut quick links routes)
const quickActionProduct = ref<Product | null>(null);
const quickActionType = ref<string | null>(null);

// Gemini intelligence states
const aiResponse = ref('');
const isAiLoading = ref(false);

const loadDatabase = async () => {
  console.log('%c[APP] loadDatabase START', 'color: #3b82f6; font-weight: bold; font-size: 14px;', {
    isAuthenticated: isAuthenticated.value,
    user: user.value,
    isDealerUser: isDealerUser.value
  });

  try {
    // Initialize dealer context first (auto-selects dealer based on user_id)
    console.log('%c[APP] Initializing dealer context...', 'color: #3b82f6;');
    await initDealerContext(user.value, isDealerUser.value);
    console.log('%c[APP] Dealer context initialized', 'color: #3b82f6;', {
      activeDealer: activeDealer.value,
      dealersCount: dealers.value.length
    });
    
    // All API calls go through centralized services — NOT raw fetch()
    console.log('%c[APP] Starting parallel API calls...', 'color: #3b82f6;');
    const [pRes, sRes, dRes, supRes, sumRes, restRes, brandRes, catRes] = await Promise.all([
      inventoryService.getAllProducts(),
      salesService.getAllSales(),
      dsrService.getAllDsrs(),
      supplierService.getAllSuppliers(),
      reportsService.getSummary(),
      inventoryService.getAllRestocks(),
      inventoryService.getBrands(),
      inventoryService.getCategories(),
    ]);

    console.log('%c[APP] API responses received', 'color: #3b82f6; font-weight: bold', {
      products: { ok: pRes.ok, count: pRes.data?.length || 0 },
      sales: { ok: sRes.ok, count: sRes.data?.length || 0 },
      dsrs: { ok: dRes.ok, count: dRes.data?.length || 0 },
      suppliers: { ok: supRes.ok, count: supRes.data?.length || 0 },
      summary: { ok: sumRes.ok, data: sumRes.data },
      restocks: { ok: restRes.ok, count: restRes.data?.length || 0 },
      brands: { ok: brandRes.ok, count: brandRes.data?.length || 0 },
      categories: { ok: catRes.ok, count: catRes.data?.length || 0 }
    });

    if (!pRes.ok || !sRes.ok || !dRes.ok || !supRes.ok || !sumRes.ok) {
      console.error('%c[APP] Some API resources failed to load!', 'color: #ef4444; font-weight: bold', {
        products: pRes.ok,
        sales: sRes.ok,
        dsrs: dRes.ok,
        suppliers: supRes.ok,
        summary: sumRes.ok
      });
      throw new Error('Some API resources failed to load.');
    }

    products.value = pRes.data;
    sales.value = sRes.data;
    dsrs.value = dRes.data;
    suppliers.value = supRes.data;
    summary.value = sumRes.data;

    console.log('%c[APP] State updated', 'color: #10b981; font-weight: bold', {
      products: products.value.length,
      sales: sales.value.length,
      dsrs: dsrs.value.length,
      suppliers: suppliers.value.length,
      summary: summary.value
    });

    if (restRes.ok) {
      restocksList.value = restRes.data;
    }

    if (brandRes.ok) brands.value = brandRes.data;
    if (catRes.ok) categories.value = catRes.data;

    // Update settings from the selected dealer (from useDealerContext)
    if (activeDealer.value) {
      settingsSelectedCurrency.value = activeDealer.value.defaultCurrency;
      settingsSelectedLocale.value = activeDealer.value.defaultLocale;
      settingsBusinessName.value = activeDealer.value.businessName || '';
      settingsGstNumber.value = activeDealer.value.gstNumber || '';
      settingsPhoneNumber.value = activeDealer.value.phoneNumber || '';
      settingsEmail.value = activeDealer.value.email || '';
      settingsCommunicationNumber.value = activeDealer.value.communicationNumber || '';
      settingsGoogleMapUrl.value = activeDealer.value.googleMapUrl || '';
      settingsAddress.value = activeDealer.value.address || '';
    }
  } catch (err: any) {
    console.error('%c[APP] loadDatabase ERROR', 'color: #ef4444; font-weight: bold; font-size: 14px;', err);
    triggerErrorToast('Trouble loading system database. Please refresh the page.');
  } finally {
    loading.value = false;
    console.log('%c[APP] loadDatabase COMPLETE - loading set to false', 'color: #10b981; font-weight: bold;', {
      loading: loading.value,
      hasData: products.value.length > 0 || sales.value.length > 0 || dsrs.value.length > 0
    });
  }
};

const loadAll = async () => {
  loading.value = true;
  await loadDatabase();
};

onMounted(async () => {
  console.log('%c[APP] onMounted triggered', 'color: #6366f1; font-weight: bold; font-size: 14px;', {
    isAuthenticated: isAuthenticated.value,
    user: user.value,
    access: access.value,
    dsrAuthState: dsrAuthState.value
  });

  // FIX A-4 (Phase A — CRIT-4): wait for useAuth() to finish its async
  // /billing/auth/me fetch before deciding which session to restore.
  // Without this, a dealer with a stale DSR token in localStorage briefly
  // sees the DSR dashboard (because isAuthenticated is still false at the
  // moment onMounted runs) and then gets a flash redirect when /me resolves.
  const waitForAuthInit = async () => {
    if (authInitialized.value) return;
    const deadline = Date.now() + 3000;
    while (!authInitialized.value && Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 50));
    }
  };

  // FIX B-9: previously the access token was memory-only but no code
  // ever re-bootstrapped the session from the stored refresh token, so
  // every page reload showed the login screen even with a valid refresh
  // token in sessionStorage. If we have a refresh token but no in-memory
  // user, call refreshUser() to exchange it for an access token + profile.
  // authInitialized stays false until this completes.
  if (!isAuthenticated.value && authHelpers.getRefreshToken()) {
    try {
      await refreshUser();
    } catch {
      // refreshUser swallows errors internally and returns null; this
      // catch is just defensive.
    }
  }

  await waitForAuthInit();

  // FIX A-3 (Phase A — CRIT-3): parse ?token=... URL to enable invitation
  // acceptance. Before this fix the invitation link was dead code: the URL
  // was generated by the dealer but clicking it did nothing because nothing
  // read window.location.search. We now:
  //   1. Strip the token from the URL bar via history.replaceState so it
  //      does not leak via browser history, bookmarks, or referrer.
  //   2. Route to the dsr-register-invite view with the token captured.
  //   3. Only apply this if the user is not already authenticated as a dealer
  //      (dealers should not be redirected into a DSR flow mid-session).
  const params = new URLSearchParams(window.location.search);
  const inviteToken = params.get('token');
  if (inviteToken && !isAuthenticated.value) {
    dsrInviteToken.value = inviteToken;
    authView.value = 'dsr-register-invite';
    // Strip the token from the URL so it doesn't linger in history/referrer.
    const cleanedUrl = window.location.pathname + window.location.hash;
    window.history.replaceState({}, document.title, cleanedUrl);
    return;
  }

  // Check for existing DSR session (page refresh after DSR login)
  // Only do this if the dealer-auth check has settled AND the user really
  // has no dealer session. Prevents the race where isAuthenticated is
  // briefly false during the /billing/auth/me fetch and we wrongly show
  // the DSR dashboard.
  const hasDsrToken = !!localStorage.getItem('dsr_access_token');
  if (hasDsrToken && !isAuthenticated.value && authInitialized.value) {
    console.log('%c[APP] Found existing DSR session - restoring DSR dashboard', 'color: #10b981;');
    dsrAuthState.value = true;
    authView.value = 'dsr-dashboard';
    return; // Don't load dealer data
  }

  // Only load data if authenticated - prevents API calls before login
  if (isAuthenticated.value) {
    console.log('%c[APP] User authenticated - calling loadAll()', 'color: #10b981;');
    await loadAll();
  } else {
    console.log('%c[APP] User NOT authenticated - skipping loadAll()', 'color: #f59e0b;');
  }
});

// Watch for authentication state changes - load data when user becomes authenticated
// This handles the case where onMounted runs before auth fetch completes
watch(isAuthenticated, async (newValue, oldValue) => {
  console.log('%c[APP] isAuthenticated changed', 'color: #8b5cf6; font-weight: bold;', {
    oldValue,
    newValue,
    hasLoadedData: products.value.length > 0 || sales.value.length > 0
  });
  
  // Only load if:
  // 1. Just became authenticated (oldValue was false, newValue is true)
  // 2. Haven't loaded data yet
  if (newValue && !oldValue && products.value.length === 0) {
    console.log('%c[APP] Auth state changed to authenticated - calling loadAll()', 'color: #10b981; font-weight: bold;');
    await loadAll();
  }
});

// Full state synchronization fetcher — uses centralized API services
const fetchFullDetails = async () => {
  try {
    const [sumRes, pRes, sRes, dRes, restRes, brandRes, catRes, supRes] = await Promise.all([
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

    // Update settings from the selected dealer (from useDealerContext)
    if (activeDealer.value) {
      settingsSelectedCurrency.value = activeDealer.value.defaultCurrency;
      settingsSelectedLocale.value = activeDealer.value.defaultLocale;
      settingsBusinessName.value = activeDealer.value.businessName || '';
      settingsGstNumber.value = activeDealer.value.gstNumber || '';
      settingsPhoneNumber.value = activeDealer.value.phoneNumber || '';
      settingsEmail.value = activeDealer.value.email || '';
      settingsCommunicationNumber.value = activeDealer.value.communicationNumber || '';
      settingsGoogleMapUrl.value = activeDealer.value.googleMapUrl || '';
      settingsAddress.value = activeDealer.value.address || '';
    }
  } catch (err) {
    console.error(err);
    triggerErrorToast('Sync failed. Please try again.');
  }
};

const handleAddProduct = async (pData: any) => {
  // Enforce max_products limit
  if (maxProducts.value > 0 && products.value.length >= maxProducts.value) {
    triggerErrorToast(`Product limit reached (${maxProducts.value} items). Upgrade your plan to add more products.`);
    throw new Error(`Product limit reached (${maxProducts.value} items)`);
  }
  
  try {
    const res = await inventoryService.addProduct(pData);
    await fetchFullDetails();
    triggerToast('Product added successfully!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to add product. Please try again.');
    throw err; // Re-throw so the component's catch block also handles it
  }
};

const handleRestockLogged = async (data: any) => {
  try {
    const res = await inventoryService.restockProduct(data);
    await fetchFullDetails();
    triggerToast('Stock Restocked successfully!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to restock. Please try again.');
    throw err;
  }
};

const handleEditProduct = async (productId: string, pData: any) => {
  try {
    const res = await inventoryService.editProduct(productId, pData);
    await fetchFullDetails();
    triggerToast('Product updated successfully!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to update product. Please try again.');
    throw err;
  }
};

const handleAddSale = async (sData: any) => {
  try {
    const res = await salesService.createSale(sData);
    await fetchFullDetails();
    triggerToast('Billing Sale logged successfully!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to create sale. Please try again.');
    throw err;
  }
};

const handleAddBulkSales = async (bulkData: any) => {
  try {
    const res = await salesService.createBulkSales(bulkData);
    await fetchFullDetails();
    triggerToast('Bulk dispatch roster logged successfully!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to create bulk sales. Please try again.');
    throw err;
  }
};

const handleCollectPayment = async (saleId: string, amount: number, receivedBy: string) => {
  try {
    const res = await salesService.collectPayment(saleId, { amount, receivedBy });
    await fetchFullDetails();
    triggerToast('Ledger payment collection recorded!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to record payment. Please try again.');
    throw err;
  }
};

const handleCloseWithDue = async (saleId: string) => {
  try {
    const res = await salesService.closeSaleWithDue(saleId);
    await fetchFullDetails();
    triggerToast('Invoice closed with remaining balance written off.');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to close invoice. Please try again.');
    throw err;
  }
};

const handleEditDsr = async (dsrId: string, dData: any) => {
  try {
    const res = await dsrService.updateDsr(dsrId, dData);
    await fetchFullDetails();
    triggerToast('DSR Representative updated!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to update representative. Please try again.');
    throw err;
  }
};

const handleDeleteDsr = async (dsrId: string) => {
  try {
    const res = await dsrService.deleteDsr(dsrId);
    await fetchFullDetails();
    triggerToast('DSR Representative removed!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to delete representative. Please try again.');
    throw err;
  }
};

const handleDeleteProduct = async (productId: string) => {
  try {
    const res = await inventoryService.deleteProduct(productId);
    await fetchFullDetails();
    triggerToast('Product deleted successfully!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to delete product. It may have existing sales.');
    throw err;
  }
};

const handleAddSupplier = async (sData: any) => {
  // Enforce max_suppliers limit
  if (maxSuppliers.value > 0 && suppliers.value.length >= maxSuppliers.value) {
    triggerErrorToast(`Supplier limit reached (${maxSuppliers.value} suppliers). Upgrade your plan to add more.`);
    throw new Error(`Supplier limit reached (${maxSuppliers.value} suppliers)`);
  }
  
  try {
    const res = await supplierService.createSupplier(sData);
    await fetchFullDetails();
    triggerToast('Supplier added successfully!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to add supplier. Please try again.');
    throw err;
  }
};

const handleEditSupplier = async (supplierId: string, sData: any) => {
  try {
    const res = await supplierService.updateSupplier(supplierId, sData);
    await fetchFullDetails();
    triggerToast('Supplier updated!');
    return res.data;
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to update supplier. Please try again.');
    throw err;
  }
};

const handleDeleteSupplier = async (supplierId: string) => {
  try {
    const res = await supplierService.deleteSupplier(supplierId);
    await fetchFullDetails();
    triggerToast('Supplier removed!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to delete supplier. Please try again.');
    throw err;
  }
};

const handleAskGemini = async () => {
  isAiLoading.value = true;
  aiResponse.value = '';
  try {
    const res = await reportsService.getAiReconciliation();
    aiResponse.value = res.data.text || 'Unable to generate analysis.';
  } catch (err: any) {
    console.error(err);
    aiResponse.value = `### ⚠️ AI Assistant offline\nFailed to receive analysis response from Gemini. Check that process.env.GEMINI_API_KEY is configured correctly inside AI Studio secrets.`;
  } finally {
    isAiLoading.value = false;
  }
};

const handleSelectDealer = async (dealer: DealerConfig) => {
  // Use the composable's selectDealer function which handles localStorage
  setDealerContext(dealer);
  settingsSelectedCurrency.value = dealer.defaultCurrency;
  settingsSelectedLocale.value = dealer.defaultLocale;
  settingsBusinessName.value = dealer.businessName || '';
  settingsGstNumber.value = dealer.gstNumber || '';
  settingsPhoneNumber.value = dealer.phoneNumber || '';
  settingsEmail.value = dealer.email || '';
  settingsCommunicationNumber.value = dealer.communicationNumber || '';
  settingsGoogleMapUrl.value = dealer.googleMapUrl || '';
  settingsAddress.value = dealer.address || '';
  triggerToast(`Active profile switched to ${dealer.fullName}`);
};

const handleUpdateDealerSettings = async ({ username, defaultCurrency }: { username: string, defaultCurrency: string }) => {
  try {
    await dealerService.updateDealerSettings({
      username,
      defaultCurrency,
      defaultLocale: CURRENCY_LOCALES[defaultCurrency] || 'en-US',
      businessName: settingsBusinessName.value,
      gstNumber: settingsGstNumber.value,
      phoneNumber: settingsPhoneNumber.value,
      email: settingsEmail.value,
      communicationNumber: settingsCommunicationNumber.value,
      googleMapUrl: settingsGoogleMapUrl.value,
      address: settingsAddress.value,
    });

    await fetchFullDetails();
    triggerToast(`Settings updated successfully!`);
    showSettingsModal.value = false;
  } catch (err: any) {
    console.error(err);
    triggerErrorToast(err.message || 'Error updating settings');
  }
};

const triggerToast = (msg: string) => {
  successToast.value = msg;
  errorToast.value = ''; // Clear any previous error toast
  setTimeout(() => {
    if (successToast.value === msg) {
      successToast.value = '';
    }
  }, 4000);
};

const triggerErrorToast = (msg: string) => {
  errorToast.value = msg;
  successToast.value = ''; // Clear any previous success toast
  setTimeout(() => {
    if (errorToast.value === msg) {
      errorToast.value = '';
    }
  }, 6000); // Error toasts stay longer (6s) since they need attention
};

const handleVoidSale = async (saleId: string, force: boolean = false) => {
  try {
    await salesService.voidSale(saleId, force);
    await fetchFullDetails();
    triggerToast('Sale voided — stock restored.');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to void sale.');
    throw err;
  }
};

const handleEditSale = async (saleId: string, data: any) => {
  try {
    await salesService.editSale(saleId, data);
    await fetchFullDetails();
    triggerToast('Sale updated!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to update sale.');
    throw err;
  }
};

const handleReturnSaleItem = async (saleId: string, data: any) => {
  try {
    await salesService.returnSaleItem(saleId, data);
    await fetchFullDetails();
    triggerToast('Product returned — stock restored!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to process return.');
    throw err;
  }
};

const handleAddBrand = async (name: string) => {
  try {
    await inventoryService.createBrand({ name });
    const res = await inventoryService.getBrands();
    if (res.ok) brands.value = res.data;
    triggerToast('Brand added!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to add brand.');
    throw err;
  }
};

const handleDeleteBrand = async (id: string) => {
  try {
    await inventoryService.deleteBrand(id);
    const res = await inventoryService.getBrands();
    if (res.ok) brands.value = res.data;
    triggerToast('Brand removed.');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to delete brand.');
    throw err;
  }
};

const handleAddCategory = async (name: string) => {
  try {
    await inventoryService.createCategory({ name });
    const res = await inventoryService.getCategories();
    if (res.ok) categories.value = res.data;
    triggerToast('Category added!');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to add category.');
    throw err;
  }
};

const handleDeleteCategory = async (id: string) => {
  try {
    await inventoryService.deleteCategory(id);
    const res = await inventoryService.getCategories();
    if (res.ok) categories.value = res.data;
    triggerToast('Category removed.');
  } catch (err: any) {
    triggerErrorToast(err.message || 'Failed to delete category.');
    throw err;
  }
};

const handleQuickAction = (actionType: string) => {
  if (actionType === 'restock') {
    activeTab.value = 'inventory';
    quickActionProduct.value = null;
  } else if (actionType === 'vehicle-sale') {
    activeTab.value = 'sales';
    quickActionType.value = 'vehicle-sale';
  } else if (actionType === 'dsr-sale') {
    activeTab.value = 'sales';
    quickActionType.value = 'dsr-sale';
  }
};

const handleNavigate = (tabId: string) => {
  activeTab.value = tabId;
  menuOpen.value = false;
  fetchFullDetails();
};

// ─── Authentication Handlers ──────────────────────────────────────────────

const handleLoginSuccess = async () => {
  // Load data after successful login
  await loadAll();
};

const handleLogout = async () => {
  await logout();
  // FIX M-4 (cross-session bleed): if a DSR session is also active in
  // this browser (e.g. on a shared workstation), scrub it too. The DSR's
  // refresh token would otherwise remain valid server-side until expiry.
  dsrAuthService.clearAuth();
  dsrAuthState.value = false;
  // Clear any sensitive data
  products.value = [];
  sales.value = [];
  dsrs.value = [];
  suppliers.value = [];
  summary.value = null;
};

// ─── DSR Authentication Handlers ──────────────────────────────────────────────
const handleDsrLoginSuccess = async () => {
  // DSR logged in successfully, update auth state and show dashboard
  dsrAuthState.value = true;
  authView.value = 'dsr-dashboard';
};

const handleDsrLogout = async () => {
  // FIX B-1: previously called only `dsrAuthService.clearAuth()` which is
  // client-only. The refresh token remained valid server-side and could
  // be reused by an attacker. Now call `logout()` first, which hits the
  // backend logout endpoint (blacklists the refresh token on the server)
  // and falls back to local cleanup if the request fails.
  try {
    await dsrAuthService.logout();
  } catch (e) {
    // Logout failures must not block the user from logging out locally.
    console.warn('[APP] DSR server logout failed, clearing local state anyway:', e);
    dsrAuthService.clearAuth();
  }
  // Update reactive state
  dsrAuthState.value = false;
  // Reset to dealer login view
  authView.value = 'dealer';
};

const handleDsrEnterPortal = async (assignment: any) => {
  console.log('[APP] DSR entering dealer portal:', assignment);

  if (!assignment?.dealer?.username) {
    console.error('[APP] No dealer username in assignment');
    return;
  }

  try {
    // Import dsrApi dynamically to avoid circular deps
    const { dsrApi, setDsrSelectedDealer } = await import('./services/dsrClient');

    // Select the dealer context - this updates tokens and selected dealer
    const result = await dsrApi.selectDealer(assignment.dealer.username);
    console.log('[APP] Dealer selected:', result);

    // Set the dealer in our local state
    setDsrSelectedDealer(result.dealer);

    // FIX L-18: replaced native alert() (which blocks the main thread)
    // with the existing triggerToast / triggerErrorToast system.
    const dealerLabel = result.dealer.full_name || result.dealer.business_name || 'dealer';
    triggerToast(
      `Connected to ${dealerLabel}. DSR dealer portal features are being developed — you'll soon be able to view inventory, record sales, and collect payments here.`,
    );
  } catch (error: any) {
    console.error('[APP] Failed to enter dealer portal:', error);
    triggerErrorToast('Failed to connect to dealer portal. Please try again.');
  }
};

const handleSessionRestored = async () => {
  await loadAll();
};

// FIX L-17: surface billing return result to the user. Called by
// <SessionGuard> when useBillingRedirect detects a return from the
// SattaBase billing flow. We always run loadAll() first so the new
// subscription is reflected in the UI before the toast appears.
const handleBillingReturned = async (success: boolean | null) => {
  if (success === null) return; // not a billing return
  await loadAll();
  if (success) {
    triggerToast('Billing updated successfully. Your plan changes are now active.');
  } else {
    triggerErrorToast('Billing update failed or was cancelled. Your plan is unchanged.');
  }
};

const formatCurrency = (amt: number) => {
  const cur = activeDealer.value?.defaultCurrency || 'INR';
  const loc = activeDealer.value?.defaultLocale || 'en-IN';
  return new Intl.NumberFormat(loc, {
    style: 'currency',
    currency: cur,
    maximumFractionDigits: 0
  }).format(amt);
};

// ─── Access Control ──────────────────────────────────────────────────────
const { hasAccess, getLimit } = useAccess();

// Navigation items with access keys for permission filtering
const allNavItems = [
  { id: 'overview', name: 'Dashboard', icon: '📦', accessKey: 'dashboard' },
  { id: 'team', name: 'Team', icon: '👥', accessKey: 'dashboard' },
  { id: 'inventory', name: 'Inventory/Restock', icon: '🏢', accessKey: 'inventory' },
  { id: 'suppliers', name: 'Suppliers', icon: '🏪', accessKey: 'suppliers' },
  { id: 'sales', name: 'Sales Entry', icon: '🧾', accessKey: 'sales' },
  { id: 'collections', name: 'Pending Collections', icon: '⏳', accessKey: 'collections' },
  { id: 'bad-debt', name: 'Bad Debt', icon: '⚠️', accessKey: 'bad_debt' },
  { id: 'reports', name: 'Financial Reports', icon: '📊', accessKey: 'reports' }
];

// Filter nav items based on user's access permissions
const navItems = computed(() => {
  return allNavItems.filter(item => hasAccess(item.accessKey).value);
});

// Access limits for enforcement
const maxProducts = getLimit('max_products', 0); // 0 = unlimited
const maxDsrs = getLimit('max_dsrs', 0);
const maxSuppliers = getLimit('max_suppliers', 0);
</script>

<template>
  <!-- ═══════════════════════════════════════════════════════════════════════
       DSR AUTHENTICATION VIEWS
       ═══════════════════════════════════════════════════════════════════════ -->
  
  <!-- DSR Dashboard - shown when DSR is authenticated -->
  <DsrDashboard 
    v-if="!isAuthenticated && isDsrAuthenticated && authView === 'dsr-dashboard'"
    @logout="handleDsrLogout"
    @enterDealerPortal="handleDsrEnterPortal"
  />
  
  <!-- DSR Login Page -->
  <DsrLoginPage 
    v-else-if="!isAuthenticated && authView === 'dsr-login'"
    @login="handleDsrLoginSuccess"
    @showDealerLogin="authView = 'dealer'"
    @showDsrRegister="authView = 'dsr-register'"
  />
  
  <!-- DSR Self-Registration Page -->
  <DsrSelfRegisterPage 
    v-else-if="!isAuthenticated && authView === 'dsr-register'"
    @registered="handleDsrLoginSuccess"
    @showDsrLogin="authView = 'dsr-login'"
  />
  
  <!-- DSR Registration via Invitation Token -->
  <DsrRegisterPage
    v-else-if="!isAuthenticated && authView === 'dsr-register-invite' && dsrInviteToken"
    :token="dsrInviteToken"
    @registered="handleDsrLoginSuccess"
    @showLogin="authView = 'dsr-login'"
  />
  
  <!-- Dealer Login Page - shown when not authenticated -->
  <LoginPage 
    v-else-if="!isAuthenticated" 
    @login="handleLoginSuccess"
    @showDsrLogin="authView = 'dsr-login'"
  />
  
  <!-- Main App - shown when authenticated -->
  <SessionGuard
    v-else
    require-auth
    @auth-required="handleLogout"
    @session-restored="handleSessionRestored"
    @billing-returned="handleBillingReturned"
  >
  <div class="app-shell">
    
    <!-- ═══════════════════════════════════════════════════════════════════
         DESKTOP SIDEBAR — Warm Espresso gradient with orange glow indicators
         ═══════════════════════════════════════════════════════════════════ -->
    <aside class="sidebar-desktop">
      <!-- Brand Header -->
      <div class="sidebar-brand">
        <div class="brand-logo">
          <Sparkles class="brand-logo-icon" />
        </div>
        <div class="brand-text">
          <h1 class="brand-name">DEALERCORE</h1>
          <span class="brand-version">v3.0</span>
        </div>
      </div>

      <!-- Dealer Context Selector (for multi-dealer DSRs) -->
      <div class="sidebar-dealer-selector">
        <DealerSelector @dealer-changed="fetchFullDetails" />
      </div>

      <!-- Navigation -->
      <nav class="sidebar-nav">
        <button
          v-for="item in navItems"
          :key="item.id"
          :id="`sidebar-nav-${item.id}`"
          @click="handleNavigate(item.id)"
          :class="['sidebar-nav-item', { 'sidebar-nav-item--active': activeTab === item.id }]"
        >
          <!-- Active glow pill -->
          <div v-if="activeTab === item.id" class="nav-glow-pill"></div>
          
          <LayoutDashboard v-if="item.id === 'overview'" class="nav-icon" />
          <UserCircle v-else-if="item.id === 'team'" class="nav-icon" />
          <Package v-else-if="item.id === 'inventory'" class="nav-icon" />
          <Users v-else-if="item.id === 'suppliers'" class="nav-icon" />
          <ShoppingCart v-else-if="item.id === 'sales'" class="nav-icon" />
          <Coins v-else-if="item.id === 'collections'" class="nav-icon" />
          <AlertTriangle v-else-if="item.id === 'bad-debt'" class="nav-icon" />
          <FilePieChart v-else-if="item.id === 'reports'" class="nav-icon" />
          
          <span class="nav-label">{{ item.name }}</span>
          <!-- Notification badge for specific items -->
          <span v-if="item.id === 'inventory' && summary && summary.lowStockCount > 0" class="nav-badge nav-badge--warning">
            {{ summary.lowStockCount }}
          </span>
          <span v-if="item.id === 'collections' && summary && summary.creditPendingCount > 0" class="nav-badge nav-badge--danger">
            {{ summary.creditPendingCount }}
          </span>
        </button>
      </nav>

      <!-- User Card with Gradient Ring Avatar -->
      <div class="sidebar-user">
        <button 
          @click="showSettingsModal = true"
          class="sidebar-user-btn"
          title="Dealer Settings Setup"
        >
          <div class="avatar-ring">
            <div class="avatar-inner">
              {{ activeDealer?.fullName ? activeDealer.fullName.split(' ').map((n: string) => n[0] || '').join('') : 'SS' }}
            </div>
          </div>
          <div class="sidebar-user-info">
            <p class="sidebar-user-name">
              {{ activeDealer?.fullName || 'Loading...' }}
            </p>
            <p class="sidebar-user-role">
              {{ activeDealer?.role || 'Dealer' }}
            </p>
          </div>
        </button>
        <div class="sidebar-user-actions">
          <!-- Billing in SattaBase -->
          <a 
            :href="sattabaseUrls.billing"
            target="_blank"
            class="sidebar-action-btn sidebar-action-btn--billing"
            title="Manage Billing in SattaBase"
          >
            <CreditCard class="sidebar-action-icon" />
          </a>
          <!-- Account Profile in SattaBase -->
          <a 
            :href="sattabaseUrls.accountProfile"
            target="_blank"
            class="sidebar-action-btn"
            title="Account Profile"
          >
            <User class="sidebar-action-icon" />
          </a>
          <button 
            @click="showSettingsModal = true"
            class="sidebar-action-btn"
            title="System Settings"
          >
            <Settings class="sidebar-action-icon" />
          </button>
          <button 
            @click="fetchFullDetails"
            class="sidebar-action-btn sidebar-action-btn--sync"
            title="Sync Database"
          >
            <RefreshCw class="sidebar-action-icon" />
          </button>
          <button 
            @click="handleLogout"
            class="sidebar-action-btn sidebar-action-btn--logout"
            title="Logout"
          >
            <LogOut class="sidebar-action-icon" />
          </button>
        </div>
      </div>
    </aside>

    <!-- ═══════════════════════════════════════════════════════════════════
         MAIN CONTENT AREA
         ═══════════════════════════════════════════════════════════════════ -->
    <div class="main-wrapper">
      
      <!-- ─── MOBILE TOP BAR ─────────────────────────────────────────── -->
      <div class="mobile-topbar">
        <div class="mobile-topbar-brand">
          <Sparkles class="mobile-brand-icon" />
          <span class="mobile-brand-name">DEALERCORE</span>
          <span class="mobile-brand-version">v3.0</span>
        </div>
        <div class="mobile-topbar-actions">
          <button 
            @click="showSettingsModal = true"
            class="mobile-action-btn"
            title="System Settings"
          >
            <Settings class="mobile-action-icon" />
          </button>
          <button 
            @click="handleLogout"
            class="mobile-action-btn mobile-action-btn--logout"
            title="Logout"
          >
            <LogOut class="mobile-action-icon" />
          </button>
        </div>
      </div>

      <!-- ─── HEADER METRICS — Gradient Cards ────────────────────────── -->
      <header class="metrics-header">
        <div class="metrics-cards">
          <!-- Low Inventory Alert Card -->
          <div class="metric-card metric-card--danger">
            <div class="metric-card-icon-wrap metric-card-icon-wrap--danger">
              <AlertCircle class="metric-card-icon" />
            </div>
            <div class="metric-card-content">
              <span class="metric-card-label">Low Inventory</span>
              <span class="metric-card-value metric-card-value--danger">
                {{ summary && summary.lowStockCount > 0 ? `${summary.lowStockCount} Items` : '0 Items' }}
              </span>
            </div>
          </div>

          <!-- Pending Credit Card -->
          <div 
            class="metric-card metric-card--warning"
            @click="handleNavigate('collections')"
            role="button"
            tabindex="0"
          >
            <div class="metric-card-icon-wrap metric-card-icon-wrap--warning">
              <Coins class="metric-card-icon" />
            </div>
            <div class="metric-card-content">
              <span class="metric-card-label">Pending Credit</span>
              <span class="metric-card-value metric-card-value--warning">
                {{ summary ? formatCurrency(summary.creditPending) : '₹0' }}
              </span>
            </div>
          </div>

          <!-- Today's Transactions Card -->
          <div class="metric-card metric-card--success">
            <div class="metric-card-icon-wrap metric-card-icon-wrap--success">
              <ShoppingCart class="metric-card-icon" />
            </div>
            <div class="metric-card-content">
              <span class="metric-card-label">Today's Sales</span>
              <span class="metric-card-value metric-card-value--success">
                {{ summary ? `${summary.totalSalesCount} Bills` : '0 Bills' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Quick Action CTA -->
        <button 
          id="sys-btn-quick-sale"
          @click="handleNavigate('sales')"
          class="header-cta-btn"
        >
          <ShoppingCart class="header-cta-icon" />
          <span>New Sale</span>
        </button>
      </header>

      <!-- ─── MAIN BODY ──────────────────────────────────────────────── -->
      <div class="main-body">
        
        <!-- Success Toast Notification — slides from top-right -->
        <Transition name="toast">
          <div 
            v-if="successToast" 
            class="toast-notification"
          >
            <div class="toast-dot"></div>
            <span class="toast-message">{{ successToast }}</span>
            <button @click="successToast = ''" class="toast-close">
              <X class="toast-close-icon" />
            </button>
          </div>
        </Transition>

        <!-- Error Toast Notification — for API/CRUD failures -->
        <Transition name="toast">
          <div 
            v-if="errorToast" 
            class="toast-notification toast-notification--error"
          >
            <div class="toast-dot toast-dot--error"></div>
            <span class="toast-message">{{ errorToast }}</span>
            <button @click="errorToast = ''" class="toast-close">
              <X class="toast-close-icon" />
            </button>
          </div>
        </Transition>

        <!-- Loading State — Professional Skeleton Screen -->
        <div v-if="loading" class="skeleton-screen">
          <div class="skeleton-header">
            <div class="skeleton-card skeleton-shimmer"></div>
            <div class="skeleton-card skeleton-shimmer"></div>
            <div class="skeleton-card skeleton-shimmer"></div>
          </div>
          <div class="skeleton-body">
            <div class="skeleton-row skeleton-shimmer" style="width: 60%"></div>
            <div class="skeleton-row skeleton-shimmer" style="width: 90%"></div>
            <div class="skeleton-row skeleton-shimmer" style="width: 75%"></div>
            <div class="skeleton-row skeleton-shimmer" style="width: 85%"></div>
            <div class="skeleton-grid">
              <div class="skeleton-block skeleton-shimmer"></div>
              <div class="skeleton-block skeleton-shimmer"></div>
              <div class="skeleton-block skeleton-shimmer"></div>
            </div>
            <div class="skeleton-row skeleton-shimmer" style="width: 50%"></div>
            <div class="skeleton-row skeleton-shimmer" style="width: 95%"></div>
            <div class="skeleton-row skeleton-shimmer" style="width: 70%"></div>
          </div>
          <div class="skeleton-footer">
            <div class="skeleton-dot"></div>
            <div class="skeleton-row skeleton-shimmer" style="width: 30%"></div>
          </div>
        </div>

        <!-- Content Area -->
        <div v-else class="content-area">
          <PermissionGuard feature="dashboard">
            <Overview 
              v-if="activeTab === 'overview'" 
              :summary="summary"
              :sales="sales"
              :formatCurrency="formatCurrency"
              @navigate="handleNavigate"
              @quickAction="handleQuickAction"
            />
          </PermissionGuard>

          <!-- Team Management Tab -->
          <PermissionGuard feature="dashboard">
            <div v-if="activeTab === 'team'" class="p-4 md:p-6 space-y-6">
              <div class="flex items-center justify-between mb-4">
                <div>
                  <h2 class="text-2xl font-bold text-slate-800">Team Management</h2>
                  <p class="text-sm text-slate-500">Manage your sales representatives</p>
                </div>
                <button
                  @click="showAddRepModal = true"
                  class="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium transition"
                >
                  <UserCircle class="h-5 w-5" />
                  Add Sales Rep
                </button>
              </div>
              <DsrManagementPanel ref="dsrRosterRef" @refresh="fetchFullDetails" />
            </div>
          </PermissionGuard>

          <PermissionGuard feature="inventory">
            <Inventory 
              v-if="activeTab === 'inventory'" 
              :products="products"
              :suppliers="suppliers"
              :restocks="restocksList"
              :dsrs="dsrs"
              :quickActionProduct="quickActionProduct"
              :formatCurrency="formatCurrency"
              :onAddProduct="handleAddProduct"
              :onRestock="handleRestockLogged"
              :onEditProduct="handleEditProduct"
              :onDeleteProduct="handleDeleteProduct"
              :brands="brands"
              :categories="categories"
              :onAddBrand="handleAddBrand"
              :onDeleteBrand="handleDeleteBrand"
              :onAddCategory="handleAddCategory"
              :onDeleteCategory="handleDeleteCategory"
              @refreshData="fetchFullDetails"
              @clearQuickActionProduct="quickActionProduct = null"
            />
          </PermissionGuard>

          <PermissionGuard feature="suppliers">
            <Suppliers 
              v-if="activeTab === 'suppliers'" 
              :suppliers="suppliers"
              :categories="categories"
              :formatCurrency="formatCurrency"
              :onAddSupplier="handleAddSupplier"
              :onEditSupplier="handleEditSupplier"
              :onDeleteSupplier="handleDeleteSupplier"
              @refreshData="fetchFullDetails"
            />
          </PermissionGuard>

          <PermissionGuard feature="sales">
            <Sales 
              v-if="activeTab === 'sales'" 
              :products="products"
              :sales="sales"
              :dsrs="dsrs"
              :quickActionType="quickActionType"
              :formatCurrency="formatCurrency"
              :onAddSale="handleAddSale"
              :onAddBulkSales="handleAddBulkSales"
              :onVoidSale="handleVoidSale"
              :onEditSale="handleEditSale"
              :onReturnItem="handleReturnSaleItem"
              @refreshData="fetchFullDetails"
              @clearQuickActionType="quickActionType = null"
            />
          </PermissionGuard>

          <PermissionGuard feature="collections">
            <Collections 
              v-if="activeTab === 'collections'" 
              :sales="sales"
              :formatCurrency="formatCurrency"
              :onCollectPayment="handleCollectPayment"
              :onCloseWithDue="handleCloseWithDue"
              @refreshData="fetchFullDetails"
            />
          </PermissionGuard>

          <PermissionGuard feature="bad_debt">
            <BadDebt 
              v-if="activeTab === 'bad-debt'" 
              :sales="sales"
              :formatCurrency="formatCurrency"
              @refreshData="fetchFullDetails"
            />
          </PermissionGuard>

          <PermissionGuard feature="reports">
            <Reports 
              v-if="activeTab === 'reports'" 
              :summary="summary"
              :dsrs="dsrs"
              :sales="sales"
              :products="products"
              :aiResponse="aiResponse"
              :isAiLoading="isAiLoading"
              :formatCurrency="formatCurrency"
              :onEditDsr="handleEditDsr"
              :onDeleteDsr="handleDeleteDsr"
              @askGemini="handleAskGemini"
              @refreshData="fetchFullDetails"
            />
          </PermissionGuard>
        </div>
      </div>

      <!-- ─── FOOTER — Minimal Status Bar ────────────────────────────── -->
      <footer class="status-bar">
        <div class="status-bar-left">
          <div class="status-dot"></div>
          <span class="status-text">
            <strong>{{ activeDealer ? activeDealer.fullName : 'Sanjay Sharma' }}</strong> — Synced
          </span>
        </div>
        <div class="status-bar-right">
          <span class="status-terminal">DEALERCORE v3.0</span>
        </div>
      </footer>

      <!-- ─── MOBILE BOTTOM NAVIGATION BAR ───────────────────────────── -->
      <nav class="mobile-bottomnav">
        <button
          v-for="item in navItems"
          :key="item.id"
          :id="`mobile-nav-${item.id}`"
          @click="handleNavigate(item.id)"
          :class="['mobile-bottomnav-item', { 'mobile-bottomnav-item--active': activeTab === item.id }]"
        >
          <LayoutDashboard v-if="item.id === 'overview'" class="mobile-bottomnav-icon" />
          <UserCircle v-else-if="item.id === 'team'" class="mobile-bottomnav-icon" />
          <Package v-else-if="item.id === 'inventory'" class="mobile-bottomnav-icon" />
          <Users v-else-if="item.id === 'suppliers'" class="mobile-bottomnav-icon" />
          <ShoppingCart v-else-if="item.id === 'sales'" class="mobile-bottomnav-icon" />
          <Coins v-else-if="item.id === 'collections'" class="mobile-bottomnav-icon" />
          <AlertTriangle v-else-if="item.id === 'bad-debt'" class="mobile-bottomnav-icon" />
          <FilePieChart v-else-if="item.id === 'reports'" class="mobile-bottomnav-icon" />
          <span class="mobile-bottomnav-label">{{ item.id === 'overview' ? 'Home' : item.id === 'team' ? 'Team' : item.id === 'inventory' ? 'Inventory' : item.id === 'suppliers' ? 'Suppliers' : item.id === 'sales' ? 'Sales' : item.id === 'collections' ? 'Dues' : 'Reports' }}</span>
        </button>
      </nav>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════════
         SETTINGS MODAL — Glass-morphism with backdrop blur
         ═══════════════════════════════════════════════════════════════════ -->
    <Transition name="modal">
      <div v-if="showSettingsModal" class="modal-overlay">
        <div @click="showSettingsModal = false" class="modal-backdrop" />
        
        <div class="modal-container">
          <!-- Modal Header -->
          <div class="modal-header">
            <div class="modal-header-left">
              <div class="modal-header-icon">
                <Settings class="modal-header-icon-svg" />
              </div>
              <div>
                <h3 class="modal-title">Dealer Configuration</h3>
                <p class="modal-subtitle">Manage currency and active profile</p>
              </div>
            </div>
            <button @click="showSettingsModal = false" class="modal-close-btn">
              <X class="modal-close-icon" />
            </button>
          </div>

          <!-- Modal Body -->
          <div class="modal-body">
            <!-- Active Profile Selection -->
            <div>
              <label class="modal-field-label">Active Dealer Profile</label>
              <div class="modal-dealer-grid">
                <button
                  v-for="d in dealers"
                  :key="d.username"
                  type="button"
                  @click="handleSelectDealer(d)"
                  :class="['modal-dealer-card', { 'modal-dealer-card--active': activeDealer?.username === d.username }]"
                >
                  <div class="modal-dealer-avatar-wrap">
                    <div :class="['modal-dealer-avatar', activeDealer?.username === d.username ? 'modal-dealer-avatar--active' : '']">
                      {{ d.fullName ? d.fullName.split(' ').map((n: string) => n[0] || '').join('') : '?' }}
                    </div>
                  </div>
                  <span class="modal-dealer-name">{{ d.fullName }}</span>
                  <span class="modal-dealer-role">{{ d.role }}</span>
                </button>
              </div>
            </div>

            <!-- Dealer Business Info -->
            <div>
              <label class="modal-field-label">Business Information</label>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <input type="text" v-model="settingsBusinessName" placeholder="Business Name" class="modal-input" />
                <input type="text" v-model="settingsGstNumber" placeholder="GST Number" class="modal-input" />
                <input type="text" v-model="settingsPhoneNumber" placeholder="Phone Number" class="modal-input" />
                <input type="email" v-model="settingsEmail" placeholder="Email" class="modal-input" />
                <input type="text" v-model="settingsCommunicationNumber" placeholder="WhatsApp / Landline" class="modal-input" />
                <input type="url" v-model="settingsGoogleMapUrl" placeholder="Google Map URL" class="modal-input" />
                <textarea v-model="settingsAddress" placeholder="Business Address" rows="2" class="modal-input md:col-span-2"></textarea>
              </div>
            </div>

            <!-- Currency Selection -->
            <div v-if="activeDealer" class="modal-currency-section">
              <div class="modal-currency-header">
                <span class="modal-currency-emoji">💰</span>
                <label class="modal-currency-label">Default Currency ({{ activeDealer.fullName }})</label>
              </div>
              <p class="modal-currency-desc">
                Sets the formatting for all invoices, COGS values, credit ledgers, and reports.
              </p>

              <select 
                v-model="settingsSelectedCurrency" 
                class="modal-currency-select"
              >
                <option value="INR">INR (₹) — Indian Rupee</option>
                <option value="USD">USD ($) — US Dollar</option>
                <option value="EUR">EUR (€) — Eurozone Euro</option>
                <option value="GBP">GBP (£) — British Pound</option>
                <option value="AED">AED (د.إ) — UAE Dirham</option>
                <option value="JPY">JPY (¥) — Japanese Yen</option>
                <option value="CAD">CAD (C$) — Canadian Dollar</option>
                <option value="AUD">AUD (A$) — Australian Dollar</option>
                <option value="SGD">SGD (S$) — Singapore Dollar</option>
              </select>

              <div class="modal-currency-preview">
                <span class="modal-currency-preview-label">Preview:</span>
                <span class="modal-currency-preview-value">
                  {{
                    new Intl.NumberFormat(CURRENCY_LOCALES[settingsSelectedCurrency] || 'en-US', {
                      style: 'currency',
                      currency: settingsSelectedCurrency,
                      maximumFractionDigits: 0
                    }).format(1248500)
                  }}
                </span>
              </div>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="modal-footer">
            <button 
              type="button" 
              @click="showSettingsModal = false" 
              class="modal-btn modal-btn--secondary"
            >
              Cancel
            </button>
            <button
              type="button"
              :disabled="!activeDealer?.username"
              @click="activeDealer?.username && handleUpdateDealerSettings({ username: activeDealer.username, defaultCurrency: settingsSelectedCurrency })"
              class="modal-btn modal-btn--primary"
            >
              Apply Settings
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Add Rep Modal -->
    <AddRepModal
      :isOpen="showAddRepModal"
      :dsrs="dsrs"
      @close="showAddRepModal = false"
      @added="showAddRepModal = false; fetchFullDetails(); dsrRosterRef?.fetchData?.();"
    />
  </div>
  </SessionGuard>
</template>

<style>
/* ═══════════════════════════════════════════════════════════════════════
   DEALERCORE v3.0 — Modern SaaS Dashboard Shell
   Color System: Primary Hermès Orange, Success emerald-500, Warning amber-500, Danger rose-500
   ═══════════════════════════════════════════════════════════════════════ */

/* ─── CSS Custom Properties ──────────────────────────────────────────── */
:root {
  --dc-primary: #E25212;
  --dc-primary-light: #E46327;
  --dc-primary-dark: #C2410B;
  --dc-success: #10b981;
  --dc-warning: #f59e0b;
  --dc-danger: #f43f5e;
  --dc-sidebar-w: 260px;
  --dc-header-h: 88px;
  --dc-footer-h: 36px;
  --dc-bottomnav-h: 64px;
  --dc-topbar-h: 56px;
  --dc-radius: 12px;
  --dc-radius-sm: 8px;
  --dc-radius-lg: 16px;
  --dc-font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.modal-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  font-family: var(--dc-font);
  color: #1e293b;
  background: #fff;
  transition: border-color 0.2s;
}
.modal-input:focus {
  outline: none;
  border-color: #E25212;
  box-shadow: 0 0 0 3px rgba(226, 82, 18, 0.1);
}

/* ─── App Shell ──────────────────────────────────────────────────────── */
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
  background: #f8fafc;
  font-family: var(--dc-font);
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  user-select: none;
  text-align: left;
}

@media (min-width: 1024px) {
  .app-shell {
    flex-direction: row;
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   SIDEBAR — Desktop Only (Warm Espresso gradient)
   ═══════════════════════════════════════════════════════════════════════ */
.sidebar-desktop {
  display: none;
  width: var(--dc-sidebar-w);
  min-width: var(--dc-sidebar-w);
  flex-direction: column;
  flex-shrink: 0;
  background: linear-gradient(180deg, #1D1915 0%, #29241E 40%, #3E372F 100%);
  color: #fff;
  text-align: left;
  overflow: hidden;
  position: relative;
}

/* Subtle noise texture overlay */
.sidebar-desktop::before {
  content: '';
  position: absolute;
  inset: 0;
  background: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none;
  z-index: 0;
}

.sidebar-desktop > * {
  position: relative;
  z-index: 1;
}

@media (min-width: 1024px) {
  .sidebar-desktop {
    display: flex;
  }
}

/* Brand Header */
.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: rgba(255,255,255,0.12);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.brand-logo-icon {
  width: 18px;
  height: 18px;
  color: #F59E0B;
}

.brand-text {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.brand-name {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #fff;
}

.brand-version {
  font-size: 10px;
  font-weight: 700;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: rgba(245, 158, 11, 0.7);
  background: rgba(255,255,255,0.08);
  padding: 2px 6px;
}

/* Dealer Selector in Sidebar */
.sidebar-dealer-selector {
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

/* Sidebar Navigation */
.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.sidebar-nav::-webkit-scrollbar {
  width: 0;
}

.sidebar-nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  border-radius: var(--dc-radius-sm);
  border: none;
  background: transparent;
  color: rgba(255,255,255,0.55);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  min-height: 44px;
  font-family: var(--dc-font);
  text-align: left;
}

.sidebar-nav-item:hover {
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.9);
}

.sidebar-nav-item--active {
  background: rgba(255,255,255,0.12);
  color: #fff;
}

/* Glow Pill Indicator */
.nav-glow-pill {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  border-radius: 0 3px 3px 0;
  background: #E25212;
  box-shadow: 0 0 12px rgba(226, 82, 18, 0.5), 0 0 24px rgba(226, 82, 18, 0.3);
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-label {
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Sidebar User Card */
.sidebar-user {
  padding: 16px;
  border-top: 1px solid rgba(255,255,255,0.08);
  background: rgba(0,0,0,0.1);
  flex-shrink: 0;
}

.sidebar-user-btn {
  display: flex;
  align-items: center;
  gap: 12px;
  background: none;
  border: none;
  color: #fff;
  cursor: pointer;
  padding: 0;
  flex: 1;
  min-width: 0;
  text-align: left;
  font-family: var(--dc-font);
  transition: opacity 0.15s;
}

.sidebar-user-btn:hover {
  opacity: 0.85;
}

/* Avatar with Gradient Ring */
.avatar-ring {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #E25212, #E46327, #F59E0B);
  padding: 2.5px;
  flex-shrink: 0;
}

.avatar-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: #C2410B;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 800;
  color: #fff;
  text-transform: uppercase;
  line-height: 1;
  letter-spacing: 0.02em;
}

.sidebar-user-info {
  min-width: 0;
  flex: 1;
}

.sidebar-user-name {
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-user-role {
  font-size: 11px;
  color: rgba(255,255,255,0.45);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-user-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 12px;
}

.sidebar-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.45);
  cursor: pointer;
  transition: all 0.15s;
}

.sidebar-action-btn:hover {
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.9);
}

.sidebar-action-btn--sync:hover .sidebar-action-icon {
  transform: rotate(180deg);
}

.sidebar-action-btn--logout {
  color: rgba(255,255,255,0.6);
}

.sidebar-action-btn--logout:hover {
  background: rgba(244,63,94,0.2);
  color: #f43f5e;
}

.sidebar-action-btn--billing {
  color: rgba(255,255,255,0.6);
}

.sidebar-action-btn--billing:hover {
  background: rgba(59,130,246,0.2);
  color: #3b82f6;
}

.sidebar-action-icon {
  width: 15px;
  height: 15px;
  transition: transform 0.3s ease;
}

/* ═══════════════════════════════════════════════════════════════════════
   MOBILE TOP BAR
   ═══════════════════════════════════════════════════════════════════════ */
.mobile-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: var(--dc-topbar-h);
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

@media (min-width: 1024px) {
  .mobile-topbar {
    display: none;
  }
}

.mobile-topbar-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-brand-icon {
  width: 20px;
  height: 20px;
  color: var(--dc-primary);
}

.mobile-brand-name {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.06em;
  color: #1e293b;
}

.mobile-brand-version {
  font-size: 10px;
  font-weight: 700;
  color: var(--dc-primary);
  font-family: 'SF Mono', 'Fira Code', monospace;
}

.mobile-topbar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.mobile-action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s;
}

.mobile-action-btn:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.mobile-action-btn--logout:hover {
  background: #fef2f2;
  color: #f43f5e;
}

.mobile-action-icon {
  width: 20px;
  height: 20px;
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN WRAPPER
   ═══════════════════════════════════════════════════════════════════════ */
.main-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
  /* Account for mobile topbar + bottom nav on small screens */
  padding-bottom: var(--dc-bottomnav-h);
}

@media (min-width: 1024px) {
  .main-wrapper {
    padding-bottom: 0;
  }
}

/* ═══════════════════════════════════════════════════════════════════════
   HEADER METRICS — Rounded Gradient Cards
   ═══════════════════════════════════════════════════════════════════════ */
.metrics-header {
  display: none;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  overflow-x: auto;
}

.metrics-header::-webkit-scrollbar {
  height: 0;
}

@media (min-width: 1024px) {
  .metrics-header {
    display: flex;
  }
}

.metrics-cards {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.metric-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--dc-radius);
  min-width: 180px;
  transition: transform 0.15s, box-shadow 0.15s;
}

.metric-card--danger {
  background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
  border: 1px solid #fecdd3;
}

.metric-card--warning {
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
  border: 1px solid #fde68a;
  cursor: pointer;
}

.metric-card--warning:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.15);
}

.metric-card--success {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 1px solid #a7f3d0;
}

.metric-card-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.metric-card-icon-wrap--danger {
  background: linear-gradient(135deg, #f43f5e, #fb7185);
  box-shadow: 0 2px 8px rgba(244, 63, 94, 0.3);
}

.metric-card-icon-wrap--warning {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.3);
}

.metric-card-icon-wrap--success {
  background: linear-gradient(135deg, #10b981, #34d399);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.metric-card-icon {
  width: 18px;
  height: 18px;
  color: #fff;
}

.metric-card-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-card-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
  letter-spacing: 0.01em;
}

.metric-card-value {
  font-size: 18px;
  font-weight: 800;
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', monospace;
  line-height: 1.1;
}

.metric-card-value--danger {
  color: #e11d48;
}

.metric-card-value--warning {
  color: #d97706;
}

.metric-card-value--success {
  color: #059669;
}

/* Header CTA Button */
.header-cta-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #E25212 0%, #C2410B 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  font-family: var(--dc-font);
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(226, 82, 18, 0.3);
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: auto;
}

.header-cta-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(226, 82, 18, 0.4);
  background: linear-gradient(135deg, #C2410B 0%, #E25212 100%);
}

.header-cta-icon {
  width: 16px;
  height: 16px;
}

/* ═══════════════════════════════════════════════════════════════════════
   MAIN BODY
   ═══════════════════════════════════════════════════════════════════════ */
.main-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: #f8fafc;
  position: relative;
}

@media (min-width: 1280px) {
  .main-body {
    overflow-y: auto;
  }
}

@media (max-width: 1023px) {
  .main-body {
    padding: 16px;
  }
}

/* Custom scrollbar */
.main-body::-webkit-scrollbar {
  width: 6px;
}

.main-body::-webkit-scrollbar-track {
  background: transparent;
}

.main-body::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.main-body::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

/* ═══════════════════════════════════════════════════════════════════════
   TOAST NOTIFICATION — Modern slide-in from top-right
   ═══════════════════════════════════════════════════════════════════════ */
.toast-notification {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-radius: var(--dc-radius);
  background: rgba(15, 23, 42, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  color: #fff;
  box-shadow: 0 8px 32px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.05);
  font-family: var(--dc-font);
  max-width: 380px;
}

.toast-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--dc-success);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  animation: toast-pulse 2s ease-in-out infinite;
  flex-shrink: 0;
}

.toast-notification--error {
  background: rgba(244, 63, 94, 0.92);
  box-shadow: 0 8px 32px rgba(244, 63, 94, 0.3), 0 0 0 1px rgba(255,255,255,0.05);
}

.toast-dot--error {
  background: #fff;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

.toast-message {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.4;
  flex: 1;
}

.toast-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.5);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.toast-close:hover {
  background: rgba(255,255,255,0.15);
  color: #fff;
}

.toast-close-icon {
  width: 14px;
  height: 14px;
}

@keyframes toast-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}

/* Toast transitions */
.toast-enter-active {
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 1, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(40px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(20px) scale(0.98);
}

/* ═══════════════════════════════════════════════════════════════════════
   LOADING STATE — Professional Skeleton Screen
   ═══════════════════════════════════════════════════════════════════════ */
.skeleton-screen {
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: skeletonFadeIn 0.4s ease-out;
}

@keyframes skeletonFadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.skeleton-header {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.skeleton-card {
  width: 200px;
  height: 64px;
  border-radius: var(--dc-radius);
  background: #e2e8f0;
}

.skeleton-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px 0;
}

.skeleton-row {
  height: 16px;
  border-radius: 8px;
  background: #e2e8f0;
}

.skeleton-grid {
  display: flex;
  gap: 16px;
  margin: 8px 0;
}

.skeleton-block {
  flex: 1;
  height: 180px;
  border-radius: var(--dc-radius-lg);
  background: #e2e8f0;
}

.skeleton-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.skeleton-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #e2e8f0;
}

@keyframes shimmer {
  0% { background-position: -400px 0; }
  100% { background-position: 400px 0; }
}

.skeleton-shimmer {
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 37%, #e2e8f0 63%);
  background-size: 800px 100%;
  animation: shimmer 1.8s ease-in-out infinite;
}

/* ─── Notification Badges on Sidebar ─────────────────────────────────── */
.nav-badge {
  margin-left: auto;
  font-size: 10px;
  font-weight: 700;
  font-family: 'SF Mono', 'Fira Code', monospace;
  padding: 2px 7px;
  border-radius: 999px;
  line-height: 1.4;
  min-width: 20px;
  text-align: center;
  flex-shrink: 0;
}

.nav-badge--warning {
  background: rgba(245, 158, 11, 0.9);
  color: #fff;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.4);
}

.nav-badge--danger {
  background: rgba(244, 63, 94, 0.9);
  color: #fff;
  box-shadow: 0 0 8px rgba(244, 63, 94, 0.4);
}

/* ═══════════════════════════════════════════════════════════════════════
   CONTENT AREA
   ═══════════════════════════════════════════════════════════════════════ */
.content-area {
  min-height: 100%;
}

/* ═══════════════════════════════════════════════════════════════════════
   FOOTER — Minimal Status Bar
   ═══════════════════════════════════════════════════════════════════════ */
.status-bar {
  display: none;
  align-items: center;
  justify-content: space-between;
  height: var(--dc-footer-h);
  padding: 0 20px;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
}

@media (min-width: 1024px) {
  .status-bar {
    display: flex;
  }
}

.status-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--dc-success);
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
  animation: toast-pulse 2.5s ease-in-out infinite;
}

.status-text {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
}

.status-text strong {
  color: #475569;
  font-weight: 700;
}

.status-bar-right {
  display: flex;
  align-items: center;
}

.status-terminal {
  font-size: 10px;
  color: #94a3b8;
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-weight: 600;
  letter-spacing: 0.04em;
}

/* ═══════════════════════════════════════════════════════════════════════
   MOBILE BOTTOM NAVIGATION BAR
   ═══════════════════════════════════════════════════════════════════════ */
.mobile-bottomnav {
  display: flex;
  align-items: stretch;
  justify-content: space-around;
  height: var(--dc-bottomnav-h);
  background: #fff;
  border-top: 1px solid #e2e8f0;
  flex-shrink: 0;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  box-shadow: 0 -2px 10px rgba(0,0,0,0.04);
}

@media (min-width: 1024px) {
  .mobile-bottomnav {
    display: none;
  }
}

.mobile-bottomnav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  flex: 1;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.2s;
  padding: 6px 4px;
  min-height: 44px;
  font-family: var(--dc-font);
  position: relative;
}

.mobile-bottomnav-item--active {
  color: var(--dc-primary);
}

.mobile-bottomnav-item--active::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  border-radius: 0 0 3px 3px;
  background: var(--dc-primary);
}

.mobile-bottomnav-icon {
  width: 20px;
  height: 20px;
}

.mobile-bottomnav-label {
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
}

/* ═══════════════════════════════════════════════════════════════════════
   SETTINGS MODAL — Glass-morphism with backdrop blur
   ═══════════════════════════════════════════════════════════════════════ */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.modal-container {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  border-radius: var(--dc-radius-lg);
  overflow: hidden;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 
    0 24px 80px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset,
    0 1px 0 rgba(255, 255, 255, 0.6) inset;
  font-family: var(--dc-font);
  color: #1e293b;
  text-align: left;
}

/* Modal Header */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(226, 232, 240, 0.6);
}

.modal-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.modal-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #E25212, #C2410B);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(226, 82, 18, 0.25);
}

.modal-header-icon-svg {
  width: 20px;
  height: 20px;
  color: #fff;
}

.modal-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.modal-subtitle {
  font-size: 12px;
  color: #64748b;
  margin: 2px 0 0;
  font-weight: 500;
}

.modal-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: rgba(15, 23, 42, 0.05);
  color: #94a3b8;
  cursor: pointer;
  transition: all 0.15s;
}

.modal-close-btn:hover {
  background: rgba(15, 23, 42, 0.1);
  color: #475569;
}

.modal-close-icon {
  width: 16px;
  height: 16px;
}

/* Modal Body */
.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.modal-field-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
  margin-bottom: 12px;
}

.modal-dealer-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.modal-dealer-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  padding: 14px;
  border-radius: var(--dc-radius);
  border: 1.5px solid #e2e8f0;
  background: rgba(255,255,255,0.6);
  cursor: pointer;
  transition: all 0.2s;
  min-height: 84px;
  text-align: left;
  font-family: var(--dc-font);
}

.modal-dealer-card:hover {
  border-color: #cbd5e1;
  background: rgba(255,255,255,0.8);
}

.modal-dealer-card--active {
  border-color: var(--dc-primary);
  background: rgba(226, 82, 18, 0.04);
  box-shadow: 0 0 0 3px rgba(226, 82, 18, 0.08);
}

.modal-dealer-avatar-wrap {
  margin-bottom: 8px;
}

.modal-dealer-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  color: #fff;
  text-transform: uppercase;
}

.modal-dealer-avatar--active {
  background: var(--dc-primary);
}

.modal-dealer-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

.modal-dealer-role {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 160px;
}

/* Currency Section */
.modal-currency-section {
  padding: 18px;
  border-radius: var(--dc-radius);
  background: rgba(248, 250, 252, 0.7);
  border: 1px solid #e2e8f0;
}

.modal-currency-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.modal-currency-emoji {
  font-size: 16px;
}

.modal-currency-label {
  font-size: 14px;
  font-weight: 700;
  color: #1e293b;
}

.modal-currency-desc {
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
  margin-bottom: 14px;
  font-weight: 400;
}

.modal-currency-select {
  width: 100%;
  padding: 10px 14px;
  border-radius: var(--dc-radius-sm);
  border: 1.5px solid #e2e8f0;
  background: rgba(255,255,255,0.9);
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  font-family: var(--dc-font);
  cursor: pointer;
  transition: border-color 0.15s;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}

.modal-currency-select:focus {
  outline: none;
  border-color: var(--dc-primary);
  box-shadow: 0 0 0 3px rgba(226, 82, 18, 0.08);
}

.modal-currency-preview {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  font-size: 11px;
}

.modal-currency-preview-label {
  color: #94a3b8;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.modal-currency-preview-value {
  color: var(--dc-primary);
  font-weight: 800;
  font-family: 'SF Mono', 'Fira Code', monospace;
}

/* Modal Footer */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid rgba(226, 232, 240, 0.6);
}

.modal-btn {
  padding: 9px 18px;
  border-radius: var(--dc-radius-sm);
  border: none;
  font-size: 13px;
  font-weight: 700;
  font-family: var(--dc-font);
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1;
}

.modal-btn--secondary {
  background: transparent;
  color: #64748b;
}

.modal-btn--secondary:hover {
  color: #1e293b;
  background: #f1f5f9;
}

.modal-btn--primary {
  background: linear-gradient(135deg, #E25212 0%, #C2410B 100%);
  color: #fff;
  box-shadow: 0 2px 8px rgba(226, 82, 18, 0.25);
}

.modal-btn--primary:hover {
  box-shadow: 0 4px 16px rgba(226, 82, 18, 0.35);
  transform: translateY(-1px);
}

/* Modal transition */
.modal-enter-active {
  transition: opacity 0.2s ease;
}
.modal-enter-active .modal-container {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.modal-leave-active {
  transition: opacity 0.15s ease;
}
.modal-leave-active .modal-container {
  transition: all 0.15s cubic-bezier(0.4, 0, 1, 1);
}
.modal-enter-from {
  opacity: 0;
}
.modal-enter-from .modal-container {
  opacity: 0;
  transform: scale(0.96) translateY(8px);
}
.modal-leave-to {
  opacity: 0;
}
.modal-leave-to .modal-container {
  opacity: 0;
  transform: scale(0.98) translateY(4px);
}

/* Fade transition (kept for compatibility) */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ═══════════════════════════════════════════════════════════════════════
   RESPONSIVE ADJUSTMENTS
   ═══════════════════════════════════════════════════════════════════════ */

/* Small mobile — compact metric display in main body */
@media (max-width: 640px) {
  .modal-dealer-grid {
    grid-template-columns: 1fr;
  }
  
  .toast-notification {
    left: 16px;
    right: 16px;
    max-width: none;
  }
}
</style>
