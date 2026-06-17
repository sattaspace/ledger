<script setup lang="ts">
/**
 * AppSidebar — persistent desktop sidebar.
 *
 * Mounted once per page (client-only). Reads the current route from
 * `window.location.pathname`
 * to highlight the active nav item.
 *
 * Also renders:
 *   - DSR Portal Mode banner (when in portal mode)
 *   - Brand header
 *   - Dealer selector
 *   - Navigation links (real <a href> links — MPA navigation)
 *   - User card with action buttons (billing, profile, settings, sync, logout)
 */
import { computed, onMounted, ref } from "vue";
import {
  Sparkles,
  LayoutDashboard,
  UserCircle,
  Package,
  Users,
  ShoppingCart,
  Coins,
  AlertTriangle,
  FilePieChart,
  CreditCard,
  User,
  Settings,
  RefreshCw,
  LogOut,
} from "lucide-vue-next";
import { sattabaseUrls } from "../lib/constants";
import { useAuth } from "../composables/useAuth";
import { useAccess } from "../composables/useAccess";
import { useDealerContext } from "../composables/useDealerContext";
import { useAppData } from "../composables/useAppData";
import { useSettingsModal } from "../composables/useSettingsModal";
import { useToasts } from "../composables/useToasts";
import { useDsrPortal } from "../composables/useDsrPortal";
import { resetBootstrap } from "../composables/useBootstrap";
import dsrAuthService from "../services/api/dsrAuth.service";
import DealerSelector from "./DealerSelector.vue";

const {
  user,
  access,
  isAuthenticated,
  logout,
  fetchProfile,
  refreshUser,
  initialized: authInitialized,
} = useAuth();
const { hasAccess } = useAccess();
const { selectedDealer: activeDealer } = useDealerContext();
const { summary, refreshAll } = useAppData();
const { openSettings } = useSettingsModal();
const { triggerToast } = useToasts();
const { dsrInPortalMode, dsrPortalDealer, exitPortalMode } = useDsrPortal();

// ─── Current route tracking ────────────────────────────────────────────────
const currentPath = ref(
  typeof window !== "undefined" ? window.location.pathname : "/",
);

function updateCurrentPath() {
  currentPath.value = window.location.pathname;
}

onMounted(() => {
  // Listen for Astro page transitions
  document.addEventListener("astro:after-swap", updateCurrentPath);
  // Also refresh auth state on mount (idempotent)
  if (!authInitialized.value && isAuthenticated.value === false) {
    refreshUser().catch(() => {});
  }
});

// ─── Navigation items ──────────────────────────────────────────────────────
const allNavItems = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard", accessKey: "dashboard", href: "/dashboard" },
  { id: "team", label: "Team", icon: "team", accessKey: "manage_dsrs", href: "/team" },
  { id: "inventory", label: "Inventory/Restock", icon: "inventory", accessKey: "inventory", href: "/inventory" },
  { id: "suppliers", label: "Suppliers", icon: "suppliers", href: "/suppliers", accessKey: "suppliers" },
  { id: "sales", label: "Sales Entry", icon: "sales", href: "/sales", accessKey: "sales" },
  { id: "collections", label: "Pending Collections", icon: "collections", href: "/collections", accessKey: "collections" },
  { id: "bad-debt", label: "Bad Debt", icon: "bad-debt", href: "/bad-debt", accessKey: "bad_debt" },
  { id: "reports", label: "Financial Reports", icon: "reports", href: "/reports", accessKey: "reports" },
];

const navItems = computed(() => {
  return allNavItems.filter((item) => {
    if (item.accessKey === "manage_dsrs" && !dsrInPortalMode.value) {
      return true; // Dealers always see Team
    }
    return hasAccess(item.accessKey).value;
  });
});

function isActive(href: string): boolean {
  if (href === "/dashboard") {
    return currentPath.value === "/" || currentPath.value === "/dashboard";
  }
  return currentPath.value === href || currentPath.value.startsWith(href + "/");
}

const isDealerUser = computed(
  () =>
    user.value?.is_dealer === true || user.value?.role === "dealer" || access.value?.is_dealer === true,
);

// ─── Actions ───────────────────────────────────────────────────────────────
async function handleSync() {
  await refreshAll();
  triggerToast("Data synced.");
}

async function handleLogout() {
  // If in DSR portal mode, exit portal (don't logout entirely)
  if (dsrInPortalMode.value) {
    exitPortalMode();
    window.location.href = "/dsr/dashboard";
    return;
  }

  await logout();
  // FIX M-4: scrub DSR session if active
  dsrAuthService.clearAuth();
  resetBootstrap();
  // logout() already redirects to /login
}
</script>

<template>
  <!-- DSR Portal Mode Banner (fixed at top when in portal mode) -->
  <div
    v-if="dsrInPortalMode"
    class="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-2 flex items-center justify-between shadow-lg"
  >
    <div class="flex items-center gap-3">
      <div class="bg-white/20 p-1.5 rounded-lg">
        <Sparkles class="h-4 w-4" />
      </div>
      <div class="flex items-center gap-2">
        <span class="text-sm font-semibold">DSR Portal Mode</span>
        <span class="text-xs text-purple-200">•</span>
        <span class="text-xs text-purple-200">{{
          dsrPortalDealer?.full_name || dsrPortalDealer?.business_name || "Dealer"
        }}</span>
      </div>
    </div>
    <a
      href="/dsr/dashboard"
      class="flex items-center gap-1.5 px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm font-medium transition"
    >
      <LogOut class="h-3.5 w-3.5" />
      Back to Dashboard
    </a>
  </div>

  <!-- Desktop Sidebar -->
  <aside
    class="sidebar-desktop"
    :style="dsrInPortalMode ? 'margin-top: 40px;' : ''"
  >
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

    <!-- Dealer Context Selector -->
    <div class="sidebar-dealer-selector">
      <DealerSelector @dealer-changed="refreshAll" />
    </div>

    <!-- Navigation -->
    <nav class="sidebar-nav">
      <a
        v-for="item in navItems"
        :key="item.id"
        :id="`sidebar-nav-${item.id}`"
        :href="item.href"
        :class="['sidebar-nav-item', { 'sidebar-nav-item--active': isActive(item.href) }]"
      >
        <div v-if="isActive(item.href)" class="nav-glow-pill"></div>
        <LayoutDashboard v-if="item.icon === 'dashboard'" class="nav-icon" />
        <UserCircle v-else-if="item.icon === 'team'" class="nav-icon" />
        <Package v-else-if="item.icon === 'inventory'" class="nav-icon" />
        <Users v-else-if="item.icon === 'suppliers'" class="nav-icon" />
        <ShoppingCart v-else-if="item.icon === 'sales'" class="nav-icon" />
        <Coins v-else-if="item.icon === 'collections'" class="nav-icon" />
        <AlertTriangle v-else-if="item.icon === 'bad-debt'" class="nav-icon" />
        <FilePieChart v-else-if="item.icon === 'reports'" class="nav-icon" />
        <span class="nav-label">{{ item.label }}</span>

        <span
          v-if="item.id === 'inventory' && summary && summary.lowStockCount > 0"
          class="nav-badge nav-badge--warning"
        >{{ summary.lowStockCount }}</span>
        <span
          v-if="item.id === 'collections' && summary && summary.creditPendingCount > 0"
          class="nav-badge nav-badge--danger"
        >{{ summary.creditPendingCount }}</span>
      </a>
    </nav>

    <!-- User Card -->
    <div class="sidebar-user">
      <button
        @click="openSettings"
        class="sidebar-user-btn"
        title="Dealer Settings Setup"
      >
        <div class="avatar-ring">
          <div class="avatar-inner">
            {{
              activeDealer?.fullName
                ? activeDealer.fullName
                    .split(" ")
                    .map((n: string) => n[0] || "")
                    .join("")
                : dsrPortalDealer?.full_name?.charAt(0) || "SS"
            }}
          </div>
        </div>
        <div class="sidebar-user-info">
          <p class="sidebar-user-name">
            {{
              activeDealer?.fullName ||
              dsrPortalDealer?.full_name ||
              (isAuthenticated ? "Loading..." : "Guest")
            }}
          </p>
          <p class="sidebar-user-role">
            {{ activeDealer?.role || (dsrInPortalMode ? "DSR Portal" : "Dealer") }}
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
          @click="openSettings"
          class="sidebar-action-btn"
          title="System Settings"
        >
          <Settings class="sidebar-action-icon" />
        </button>
        <button
          @click="handleSync"
          class="sidebar-action-btn sidebar-action-btn--sync"
          title="Sync Database"
        >
          <RefreshCw class="sidebar-action-icon" />
        </button>
        <button
          @click="handleLogout"
          class="sidebar-action-btn sidebar-action-btn--logout"
          :title="dsrInPortalMode ? 'Back to DSR Dashboard' : 'Logout'"
        >
          <LogOut class="sidebar-action-icon" />
        </button>
      </div>
    </div>
  </aside>
</template>
