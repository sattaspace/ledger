<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { 
  Package, 
  ShoppingCart, 
  Coins, 
  FilePieChart, 
  LayoutDashboard, 
  Menu, 
  X, 
  AlertCircle,
  Smartphone,
  RefreshCw,
  LogOut,
  Settings,
  Sparkles,
  Award
} from 'lucide-vue-next';
import type { DatabaseSchema, Product, SaleRecord, RestockRecord, DSR, Supplier, DealerConfig } from './types';
import Overview from './components/Overview.vue';
import Inventory from './components/Inventory.vue';
import Sales from './components/Sales.vue';
import Collections from './components/Collections.vue';
import Reports from './components/Reports.vue';

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
import { ApiError } from './services/apiClient';

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

// Database Core States
const products = ref<Product[]>([]);
const sales = ref<SaleRecord[]>([]);
const dsrs = ref<DSR[]>([]);
const suppliers = ref<Supplier[]>([]);
const restocksList = ref<RestockRecord[]>([]);
const summary = ref<any>(null);

// Dealer / Settings State
const dealers = ref<DealerConfig[]>([]);
const activeDealer = ref<DealerConfig | null>(null);
const showSettingsModal = ref(false);
const settingsSelectedCurrency = ref('INR');
const settingsSelectedLocale = ref('en-IN');

// Dynamic notifications / banners loaders
const loading = ref(true);
const errorBanner = ref('');
const successBanner = ref('');

// Context Transfer channels (Shortcut quick links routes)
const quickActionProduct = ref<Product | null>(null);
const quickActionType = ref<string | null>(null);

// Gemini intelligence states
const aiResponse = ref('');
const isAiLoading = ref(false);

const loadDatabase = async () => {
  try {
    // All API calls go through centralized services — NOT raw fetch()
    const [pRes, sRes, dRes, supRes, sumRes, dealRes] = await Promise.all([
      inventoryService.getAllProducts(),
      salesService.getAllSales(),
      dsrService.getAllDsrs(),
      supplierService.getAllSuppliers(),
      reportsService.getSummary(),
      dealerService.getAllDealers(),
    ]);

    if (!pRes.ok || !sRes.ok || !dRes.ok || !supRes.ok || !sumRes.ok) {
      throw new Error('Some API resources failed to load.');
    }

    products.value = pRes.data;
    sales.value = sRes.data;
    dsrs.value = dRes.data;
    suppliers.value = supRes.data;
    summary.value = sumRes.data;

    if (dealRes.ok) {
      const dealersData = dealRes.data;
      dealers.value = dealersData;
      const storedUser = localStorage.getItem('dealercore_active_username') || 'sanjay';
      const active = dealersData.find((d: any) => d.username === storedUser) || dealersData[0];
      if (active) {
        activeDealer.value = active;
        settingsSelectedCurrency.value = active.defaultCurrency;
        settingsSelectedLocale.value = active.defaultLocale;
      }
    }
  } catch (err: any) {
    console.error(err);
    errorBanner.value = 'Trouble loading system database templates. Retrying in 5s.';
  } finally {
    loading.value = false;
  }
};

const loadAll = async () => {
  loading.value = true;
  await loadDatabase();
};

onMounted(async () => {
  await loadAll();

  // Populate seeding lists matching exact items specs
  if (restocksList.value.length === 0) {
    restocksList.value = [
      {
        id: 'restock-1',
        productId: 'prod-1',
        productName: "Michelin Primacy 4 SUV Tyre",
        quantity: 20,
        supplierName: "Michelin Distributors",
        costPrice: 120,
        totalCost: 2400,
        date: "2026-05-10T10:00:00.000Z",
        receivedBy: "Sanjay Sharma (Manager)"
      },
      {
        id: 'restock-2',
        productId: 'prod-2',
        productName: "Castrol EDGE 5W-40 Engine Oil Full Synthetic",
        quantity: 10,
        supplierName: "Castrol India",
        costPrice: 25,
        totalCost: 250,
        date: "2026-05-12T14:30:00.000Z",
        receivedBy: "Rajesh Kumar (DSR)"
      }
    ];
  }
});

// Full state synchronization fetcher — uses centralized API services
const fetchFullDetails = async () => {
  try {
    const [sumRes, pRes, sRes, dRes, dealRes] = await Promise.all([
      reportsService.getSummary(),
      inventoryService.getAllProducts(),
      salesService.getAllSales(),
      dsrService.getAllDsrs(),
      dealerService.getAllDealers(),
    ]);

    if (sumRes.ok) summary.value = sumRes.data;
    if (pRes.ok) products.value = pRes.data;
    if (sRes.ok) sales.value = sRes.data;
    if (dRes.ok) dsrs.value = dRes.data;

    if (dealRes.ok) {
      const dealersData = dealRes.data;
      dealers.value = dealersData;
      const storedUser = localStorage.getItem('dealercore_active_username') || 'sanjay';
      const active = dealersData.find((d: any) => d.username === storedUser) || dealersData[0];
      if (active) {
        activeDealer.value = active;
      }
    }
  } catch (err) {
    console.error(err);
  }
};

const handleAddProduct = async (pData: any) => {
  const res = await inventoryService.addProduct(pData);
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to create product template');
  }
  await fetchFullDetails();
  return res.data;
};

const handleRestockLogged = async (data: any) => {
  const res = await inventoryService.restockProduct(data);
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to restock product');
  }
  await fetchFullDetails();
  
  // Add item history details client-side list
  const newRestockItem: RestockRecord = {
    id: `restock-${Date.now()}`,
    productId: data.productId,
    productName: products.value.find(p => p.id === data.productId)?.name || 'Direct Resource',
    quantity: data.quantity,
    supplierName: data.supplierName,
    costPrice: data.costPrice,
    totalCost: data.quantity * data.costPrice,
    date: new Date().toISOString(),
    receivedBy: data.receivedBy || 'Staff'
  };
  restocksList.value.push(newRestockItem);
  triggerToast('Stock Restocked successfully!');
  return res.data;
};

const handleAddSale = async (sData: any) => {
  const res = await salesService.createSale(sData);
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to complete sale transaction');
  }
  await fetchFullDetails();
  triggerToast('Billing Sale logged successfully!');
  return res.data;
};

const handleAddBulkSales = async (bulkData: any) => {
  const res = await salesService.createBulkSales(bulkData);
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to complete bulk sales transaction');
  }
  await fetchFullDetails();
  triggerToast('Bulk dispatch roster logged successfully!');
  return res.data;
};

const handleCollectPayment = async ({ saleId, amount, receivedBy }: { saleId: string, amount: number, receivedBy: string }) => {
  const res = await salesService.collectPayment(saleId, { amount, receivedBy });
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to record outstanding payment');
  }
  await fetchFullDetails();
  triggerToast('Ledger payment collection recorded!');
  return res.data;
};

const handleCloseWithDue = async (saleId: string) => {
  const res = await salesService.closeSaleWithDue(saleId);
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to close invoice with due');
  }
  await fetchFullDetails();
  triggerToast('Invoice closed with remaining balance written off.');
  return res.data;
};

const handleAddDsr = async (dData: any) => {
  const res = await dsrService.createDsr(dData);
  if (!res.ok) {
    throw new Error(res.data?.error || 'Failed to register representative');
  }
  await fetchFullDetails();
  triggerToast('DSR Representative registered!');
  return res.data;
};

const handleAskGemini = async () => {
  isAiLoading.value = true;
  aiResponse.value = '';
  try {
    const res = await reportsService.getAiReconciliation();
    if (!res.ok) {
      throw new Error('Gemini API query failed.');
    }
    aiResponse.value = res.data.text || 'Unable to generate analysis.';
  } catch (err: any) {
    console.error(err);
    aiResponse.value = `### ⚠️ AI Assistant offline\nFailed to receive analysis response from Gemini. Check that process.env.GEMINI_API_KEY is configured correctly inside AI Studio secrets.`;
  } finally {
    isAiLoading.value = false;
  }
};

const handleSelectDealer = async (dealer: DealerConfig) => {
  localStorage.setItem('dealercore_active_username', dealer.username);
  activeDealer.value = dealer;
  settingsSelectedCurrency.value = dealer.defaultCurrency;
  settingsSelectedLocale.value = dealer.defaultLocale;
  triggerToast(`Active profile switched to ${dealer.fullName}`);
};

const handleUpdateDealerSettings = async ({ username, defaultCurrency }: { username: string, defaultCurrency: string }) => {
  try {
    const res = await dealerService.updateDealerSettings({
      username,
      defaultCurrency,
      defaultLocale: CURRENCY_LOCALES[defaultCurrency] || 'en-US'
    });

    if (!res.ok) {
      throw new Error(res.data?.error || 'Failed to update dealer settings');
    }

    await fetchFullDetails();
    triggerToast(`Successfully set default currency to ${defaultCurrency}!`);
    showSettingsModal.value = false;
  } catch (err: any) {
    console.error(err);
    errorBanner.value = err.message || 'Error updating settings';
    setTimeout(() => errorBanner.value = '', 4005);
  }
};

const triggerToast = (msg: string) => {
  successBanner.value = msg;
  setTimeout(() => {
    if (successBanner.value === msg) {
      successBanner.value = '';
    }
  }, 4000);
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

const formatCurrency = (amt: number) => {
  const cur = activeDealer.value?.defaultCurrency || 'INR';
  const loc = activeDealer.value?.defaultLocale || 'en-IN';
  return new Intl.NumberFormat(loc, {
    style: 'currency',
    currency: cur,
    maximumFractionDigits: 0
  }).format(amt);
};

const navItems = [
  { id: 'overview', name: 'Dashboard', icon: '📦' },
  { id: 'inventory', name: 'Inventory/Restock', icon: '🏢' },
  { id: 'sales', name: 'Sales Entry', icon: '🧾' },
  { id: 'collections', name: 'Pending Collections', icon: '⏳' },
  { id: 'reports', name: 'Financial Reports', icon: '📊' }
];
</script>

<template>
  <div class="flex flex-col lg:flex-row h-screen w-full overflow-hidden bg-slate-50 font-sans text-slate-900 antialiased select-none text-left">
    
    <!-- DESKTOP SIDEBAR -->
    <aside class="hidden lg:flex w-64 bg-white border-r border-slate-200 flex-col shrink-0 text-left">
      <div class="p-6 border-b border-slate-100">
        <h1 class="text-slate-800 font-bold text-lg tracking-tight uppercase flex items-center space-x-2">
          <span>DEALERCORE</span>
          <span class="text-blue-600 text-xs font-mono font-bold">v3.0</span>
        </h1>
      </div>
      
      <nav class="flex-1 p-4 space-y-1 overflow-y-auto">
        <button
          v-for="item in navItems"
          :key="item.id"
          :id="`sidebar-nav-${item.id}`"
          @click="handleNavigate(item.id)"
          :class="['w-full flex items-center px-4 py-2.5 rounded text-xs font-bold cursor-pointer transition-all leading-none',
            activeTab === item.id 
              ? 'bg-blue-600 text-white shadow-sm font-black' 
              : 'text-slate-500 hover:text-slate-900 hover:bg-slate-100'
          ]"
        >
          <span class="mr-3 text-sm">{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </button>
      </nav>

      <!-- User card -->
      <div class="p-4 bg-slate-100/70 border-t border-slate-200 shrink-0 text-left">
        <div class="flex items-center justify-between">
          <button 
            @click="showSettingsModal = true"
            class="flex items-center space-x-3 text-left hover:opacity-85 transition cursor-pointer flex-1 min-w-0"
            title="Dealer Settings Setup"
          >
            <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-sans font-black text-white uppercase shrink-0 shadow-xs leading-none">
              {{ activeDealer ? activeDealer.fullName.split(' ').map(n => n[0]).join('') : 'JS' }}
            </div>
            <div class="min-w-0 flex-1">
              <p class="text-slate-800 text-xs font-bold leading-none truncate">
                {{ activeDealer ? activeDealer.fullName : 'Sanjay Sharma' }}
              </p>
              <p class="text-slate-400 text-[10px] mt-1.5 truncate leading-none">
                {{ activeDealer ? activeDealer.role : 'Senior Dealer Admin' }}
              </p>
            </div>
          </button>
          <div class="flex items-center space-x-1.5 ml-2">
            <button 
              @click="showSettingsModal = true"
              class="text-slate-450 hover:text-slate-800 p-1 rounded hover:bg-slate-200/50 cursor-pointer"
              title="System Switch Currency"
            >
              <Settings class="h-3.5 w-3.5" />
            </button>
            <button 
              @click="fetchFullDetails"
              class="text-slate-455 hover:text-slate-800 p-1 rounded hover:bg-slate-200/50 hover:rotate-180 transition-transform duration-300 cursor-pointer"
              title="Sync Database"
            >
              <RefreshCw class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- MOBILE HEADER BAR -->
    <div class="lg:hidden bg-white text-slate-800 shrink-0 px-4 py-3 flex items-center justify-between border-b border-slate-200 text-left shadow-xs">
      <h1 class="font-bold text-sm tracking-widest uppercase">
        DEALERCORE <span class="text-blue-600 text-xs">v3.0</span>
      </h1>
      <div class="flex items-center space-x-2">
        <button 
          @click="showSettingsModal = true"
          class="p-1.5 hover:bg-slate-100 rounded text-slate-450 hover:text-slate-800 cursor-pointer"
          title="System Settings"
        >
          <Settings class="h-4 w-4" />
        </button>
        <button 
          id="mobile-nav-toggle"
          @click="menuOpen = !menuOpen"
          class="p-1.5 hover:bg-slate-100 rounded text-slate-700 cursor-pointer"
        >
          <X v-if="menuOpen" class="h-5 w-5 animate-spin-once" />
          <Menu v-else class="h-5 w-5" />
        </button>
      </div>
    </div>

    <!-- MOBILE DRAWER MENU -->
    <Transition name="fade">
      <div 
        v-if="menuOpen" 
        class="lg:hidden absolute top-12 left-0 right-0 z-50 bg-white border-b border-slate-200 p-2 space-y-1 shadow-md font-sans text-left"
      >
        <button
          v-for="item in navItems"
          :key="item.id"
          :id="`mobile-nav-${item.id}`"
          @click="handleNavigate(item.id)"
          :class="['w-full flex items-center px-4 py-2.5 rounded text-xs font-bold transition-all leading-none border-b border-slate-50 last:border-b-0 cursor-pointer',
            activeTab === item.id 
              ? 'bg-blue-600 text-white shadow-xs font-black' 
              : 'text-slate-600 hover:bg-slate-100'
          ]"
        >
          <span class="mr-3">{{ item.icon }}</span>
          <span>{{ item.name }}</span>
        </button>
      </div>
    </Transition>

    <!-- MAIN WORKS FRAME CONTAINER -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- HEADER METRICS BOARD -->
      <header class="h-20 bg-white border-b border-slate-200 flex items-center px-4 md:px-6 space-x-6 shrink-0 overflow-x-auto scrollbar-none text-left">
        <div class="flex flex-col shrink-0 text-left">
          <span class="text-[9.5px] text-slate-455 uppercase font-bold tracking-wider">Low Inventory Alerts</span>
          <span class="text-xl md:text-2xl font-black text-red-650 font-mono">
            {{ summary && summary.lowStockCount > 0 ? `${summary.lowStockCount} Items` : '0 Items' }}
          </span>
        </div>
        <div class="h-10 w-px bg-slate-200 shrink-0"></div>
        <div class="flex flex-col shrink-0 text-left">
          <span class="text-[9.5px] text-slate-455 uppercase font-bold tracking-wider block">Pending Active Credit</span>
          <span 
            @click="handleNavigate('collections')"
            class="text-xl md:text-2xl font-black text-amber-600 underline cursor-pointer hover:text-amber-700 transition font-mono leading-tight"
          >
            {{ summary ? formatCurrency(summary.creditPending) : '₹0' }}
          </span>
        </div>
        <div class="h-10 w-px bg-slate-200 shrink-0"></div>
        <div class="flex flex-col shrink-0 text-left">
          <span class="text-[9.5px] text-slate-455 uppercase font-bold tracking-wider">Today's Transactions</span>
          <span class="text-xl md:text-2xl font-black text-emerald-650 font-mono">
            {{ summary ? `${summary.totalSalesCount} Bills` : '0 Bills' }}
          </span>
        </div>
        <div class="flex-1"></div>
        <button 
          id="sys-btn-quick-sale"
          @click="handleNavigate('sales')"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded font-black text-xs shadow-xs shrink-0 transition cursor-pointer"
        >
          + NEW SALES ENTRY
        </button>
      </header>

      <!-- ACTIVE BODY TRANSITION AREA -->
      <div class="flex-1 overflow-y-auto p-4 md:p-6 bg-slate-50 relative text-left">
        
        <!-- TOASTER BANNER NOTIFICATION -->
        <Transition name="toast">
          <div 
            v-if="successBanner" 
            class="fixed bottom-14 right-6 z-[999] bg-slate-900 text-white px-4 py-2.5 rounded shadow-lg text-xs font-bold border border-slate-800 flex items-center space-x-2.5 animate-fadeIn font-sans"
          >
            <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <span>{{ successBanner }}</span>
          </div>
        </Transition>

        <div v-if="loading" class="flex flex-col items-center justify-center h-full space-y-2 text-center select-none font-sans">
          <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-650"></div>
          <p class="text-xs text-slate-450 font-mono">Connecting regional database tables...</p>
        </div>

        <div v-else class="h-full">
          <!-- Multi router switches based on activeTab -->
          <Overview 
            v-if="activeTab === 'overview'" 
            :summary="summary"
            :sales="sales"
            :formatCurrency="formatCurrency"
            @navigate="handleNavigate"
            @quickAction="handleQuickAction"
          />

          <Inventory 
            v-else-if="activeTab === 'inventory'" 
            :products="products"
            :suppliers="suppliers"
            :restocks="restocksList"
            :dsrs="dsrs"
            :quickActionProduct="quickActionProduct"
            :formatCurrency="formatCurrency"
            @addProduct="handleAddProduct"
            @restock="handleRestockLogged"
            @refreshData="fetchFullDetails"
            @clearQuickActionProduct="quickActionProduct = null"
          />

          <Sales 
            v-else-if="activeTab === 'sales'" 
            :products="products"
            :sales="sales"
            :dsrs="dsrs"
            :quickActionType="quickActionType"
            :formatCurrency="formatCurrency"
            @addSale="handleAddSale"
            @addBulkSales="handleAddBulkSales"
            @refreshData="fetchFullDetails"
            @clearQuickActionType="quickActionType = null"
          />

          <Collections 
            v-else-if="activeTab === 'collections'" 
            :sales="sales"
            :formatCurrency="formatCurrency"
            @collectPayment="handleCollectPayment"
            @closeWithDue="handleCloseWithDue"
            @refreshData="fetchFullDetails"
          />

          <Reports 
            v-else-if="activeTab === 'reports'" 
            :summary="summary"
            :dsrs="dsrs"
            :sales="sales"
            :products="products"
            :aiResponse="aiResponse"
            :isAiLoading="isAiLoading"
            :formatCurrency="formatCurrency"
            @addDSR="handleAddDsr"
            @askGemini="handleAskGemini"
            @refreshData="fetchFullDetails"
          />
        </div>
      </div>

      <!-- FOOTER LIVE STATUS SIMULATOR BAR -->
      <footer class="h-12 bg-slate-100 border-t border-slate-300 flex items-center px-4 justify-between shrink-0 font-sans select-none">
        <div class="flex space-x-4 items-center overflow-hidden">
          <span class="text-[9.5px] font-extrabold text-slate-400 tracking-wider shrink-0 block">LIVE FEED STATUS</span>
          <div class="flex items-center space-x-2 overflow-hidden leading-none leading-normal">
            <div class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse shrink-0"></div>
            <p class="text-[11px] text-slate-605 truncate">
              <strong class="font-bold text-slate-900">{{ activeDealer ? activeDealer.fullName : 'Sanjay Sharma' }}</strong> updated regional stock records. Secure offline cached files sync complete.
            </p>
          </div>
        </div>
        <div class="hidden md:block text-[10px] text-slate-400 font-mono uppercase tracking-tighter">
          Terminal GJ-AHD-49 | Lat: 23.0225 | Lon: 72.5714 | Astro Node Powered
        </div>
      </footer>
    </div>

    <!-- DEALER SWITCH & SETTINGS MODAL -->
    <Transition name="fade">
      <div v-if="showSettingsModal" class="fixed inset-0 z-[1000] flex items-center justify-center p-4">
        <!-- Backdrop opacity exit triggers -->
        <div @click="showSettingsModal = false" class="absolute inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity" />
        
        <div class="bg-white rounded-xl shadow-xl w-full max-w-lg border border-slate-200 overflow-hidden font-sans z-10 relative flex flex-col animate-fadeIn font-sans text-left">
          <!-- header -->
          <div class="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <div class="flex items-center space-x-2.5">
              <span class="text-xl leading-none">⚙️</span>
              <div class="space-y-0.5">
                <h3 class="font-bold text-slate-900 text-sm tracking-tight font-sans">Dealer Configuration Setup</h3>
                <p class="text-[10px] text-slate-500 font-medium">Manage default system currency and active profile attributes</p>
              </div>
            </div>
            <button @click="showSettingsModal = false" class="p-1 hover:bg-slate-200 rounded text-slate-400 hover:text-slate-600 transition cursor-pointer">
              <X class="h-4 w-4" />
            </button>
          </div>

          <div class="p-5 space-y-4">
            <!-- Active Profile -->
            <div>
              <label class="block text-[9px] uppercase tracking-wider text-slate-400 font-black mb-2">Active Dealer Profile Context Account</label>
              <div class="grid grid-cols-2 gap-2.5">
                <button
                  v-for="d in dealers"
                  :key="d.username"
                  type="button"
                  @click="handleSelectDealer(d)"
                  :class="['p-3 rounded-lg border text-left transition flex flex-col justify-between h-20 cursor-pointer',
                    activeDealer?.username === d.username
                      ? 'border-blue-600 bg-blue-50/40 shadow-xs ring-1 ring-blue-500/10'
                      : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  ]"
                >
                  <div class="flex items-center space-x-2 overflow-hidden leading-none leading-normal">
                    <div :class="['w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-black text-white uppercase shrink-0', activeDealer?.username === d.username ? 'bg-blue-600' : 'bg-slate-450']">
                      {{ d.fullName.split(' ').map(n => n[0]).join('') }}
                    </div>
                    <span class="text-[11.5px] font-bold text-slate-800 truncate block max-w-[140px]">{{ d.fullName }}</span>
                  </div>
                  <span class="text-[9.5px] text-slate-400 block truncate font-sans">{{ d.role }}</span>
                </button>
              </div>
            </div>

            <!-- Currency Select -->
            <div v-if="activeDealer" class="bg-slate-50 p-4 rounded-lg border border-slate-200 text-left">
              <div class="flex items-center space-x-2 mb-2 font-bold text-slate-800 text-xs">
                <span>💰</span>
                <label>Default Currency Selector ({{ activeDealer.fullName }}):</label>
              </div>
              <p class="text-[10px] text-slate-500 mb-3 leading-relaxed font-sans font-medium">
                Switch default formatting for all invoiced sums, COGS values, credit ledgers, and outstanding debts in report tables:
              </p>

              <select 
                v-model="settingsSelectedCurrency" 
                class="w-full bg-white border border-slate-205 py-2 px-3 text-xs rounded-lg text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500 font-bold"
              >
                <option value="INR">INR (₹) - Indian Rupee (en-IN)</option>
                <option value="USD">USD ($) - US Dollar (en-US)</option>
                <option value="EUR">EUR (€) - Eurozone Euro (en-IE)</option>
                <option value="GBP">GBP (£) - British Pound Sterling (en-GB)</option>
                <option value="AED">AED (د.إ) - UAE Dirham (en-AE)</option>
                <option value="JPY">JPY (¥) - Japanese Yen (ja-JP)</option>
                <option value="CAD">CAD (C$) - Canadian Dollar (en-CA)</option>
                <option value="AUD">AUD (A$) - Australian Dollar (en-AU)</option>
                <option value="SGD">SGD (S$) - Singapore Dollar (en-SG)</option>
              </select>

              <div class="mt-3 flex items-center space-x-1 text-[10px] text-slate-400 uppercase tracking-tighter leading-none">
                <span>Value format preview:</span>
                <span class="font-bold text-blue-600 font-mono">
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

          <div class="px-5 py-3 border-t border-slate-200 bg-slate-50 flex justify-end space-x-2 items-center">
            <button 
              type="button" 
              @click="showSettingsModal = false" 
              class="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 rounded font-bold cursor-pointer"
            >
              Cancel
            </button>
            <button 
              type="button" 
              @click="handleUpdateDealerSettings({ username: activeDealer?.username || 'sanjay', defaultCurrency: settingsSelectedCurrency })"
              class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded text-xs font-bold cursor-pointer shadow-xs leading-none"
            >
              Apply Default Currency
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style>
/* Smooth Vue Transition animations */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.toast-enter-active, .toast-leave-active {
  transition: opacity 0.25s ease, transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}
.toast-enter-from, .toast-leave-to {
  opacity: 0;
  transform: translateY(15px) scale(0.95);
}
</style>
