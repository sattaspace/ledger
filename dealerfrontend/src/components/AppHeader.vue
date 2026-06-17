<script setup lang="ts">
/**
 * AppHeader — persistent mobile topbar + metrics header.
 *
 * Mounted once per page (client-only). Renders:
 *   - Mobile top bar (brand + settings + logout)
 *   - Metrics header (3 gradient cards + New Sale button)
 */
import { computed, onMounted } from "vue";
import {
  Sparkles,
  Settings,
  LogOut,
  AlertCircle,
  Coins,
  ShoppingCart,
} from "lucide-vue-next";
import { useAppData } from "../composables/useAppData";
import { useAuth } from "../composables/useAuth";
import { useSettingsModal } from "../composables/useSettingsModal";
import { useToasts } from "../composables/useToasts";
import { useDsrPortal } from "../composables/useDsrPortal";
import { resetBootstrap } from "../composables/useBootstrap";
import dsrAuthService from "../services/api/dsrAuth.service";

const { summary, formatCurrency, refreshAll } = useAppData();
const { logout } = useAuth();
const { openSettings } = useSettingsModal();
const { triggerToast } = useToasts();
const { dsrInPortalMode, exitPortalMode } = useDsrPortal();

async function handleLogout() {
  if (dsrInPortalMode.value) {
    exitPortalMode();
    window.location.href = "/dsr/dashboard";
    return;
  }
  await logout();
  dsrAuthService.clearAuth();
  resetBootstrap();
}

onMounted(() => {
  // Refresh auth state on mount (idempotent)
});
</script>

<template>
  <div>
    <!-- Mobile Top Bar -->
    <div class="mobile-topbar">
      <div class="mobile-topbar-brand">
        <Sparkles class="mobile-brand-icon" />
        <span class="mobile-brand-name">DEALERCORE</span>
        <span class="mobile-brand-version">v3.0</span>
      </div>
      <div class="mobile-topbar-actions">
        <button
          @click="openSettings"
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

    <!-- Header Metrics — Gradient Cards -->
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
              {{ summary && summary.lowStockCount > 0 ? `${summary.lowStockCount} Items` : "0 Items" }}
            </span>
          </div>
        </div>

        <!-- Pending Credit Card -->
        <a
          href="/collections"
          class="metric-card metric-card--warning"
          style="cursor: pointer; text-decoration: none; color: inherit;"
        >
          <div class="metric-card-icon-wrap metric-card-icon-wrap--warning">
            <Coins class="metric-card-icon" />
          </div>
          <div class="metric-card-content">
            <span class="metric-card-label">Pending Credit</span>
            <span class="metric-card-value metric-card-value--warning">
              {{ summary ? formatCurrency(summary.creditPending) : "₹0" }}
            </span>
          </div>
        </a>

        <!-- Today's Transactions Card -->
        <div class="metric-card metric-card--success">
          <div class="metric-card-icon-wrap metric-card-icon-wrap--success">
            <ShoppingCart class="metric-card-icon" />
          </div>
          <div class="metric-card-content">
            <span class="metric-card-label">Today's Sales</span>
            <span class="metric-card-value metric-card-value--success">
              {{ summary ? `${summary.totalSalesCount} Bills` : "0 Bills" }}
            </span>
          </div>
        </div>
      </div>

      <!-- Quick Action CTA -->
      <a
        id="sys-btn-quick-sale"
        href="/sales"
        class="header-cta-btn"
        style="text-decoration: none;"
      >
        <ShoppingCart class="header-cta-icon" />
        <span>New Sale</span>
      </a>
    </header>
  </div>
</template>
