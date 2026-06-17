<script setup lang="ts">
/**
 * AppFooter — persistent footer + mobile bottom nav + toasts + modals.
 *
 * Mounted once per page (client-only). Renders:
 *   - Status bar footer
 *   - Mobile bottom nav (with <a href> links)
 *   - Success / error toast notifications
 *   - Settings modal (dealer configuration)
 *   - Add rep modal
 */
import { computed, onMounted, onUnmounted, ref } from "vue";
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
  Settings,
  X,
  RefreshCw,
} from "lucide-vue-next";
import { useAppData } from "../composables/useAppData";
import { useAuth } from "../composables/useAuth";
import { useAccess } from "../composables/useAccess";
import { useDealerContext } from "../composables/useDealerContext";
import { useSettingsModal } from "../composables/useSettingsModal";
import { useToasts } from "../composables/useToasts";
import { useDsrPortal } from "../composables/useDsrPortal";
import { useBillingRedirect } from "../composables/useBillingRedirect";
import AddRepModal from "./AddRepModal.vue";

const { dsrs } = useAppData();
const { refreshAll } = useAppData();
const { user, access, isAuthenticated, refreshUser } = useAuth();
const { hasAccess } = useAccess();
const { selectedDealer: activeDealer } = useDealerContext();
const {
  showSettingsModal,
  closeSettings,
  settingsSelectedCurrency,
  settingsSelectedLocale,
  settingsBusinessName,
  settingsGstNumber,
  settingsPhoneNumber,
  settingsEmail,
  settingsCommunicationNumber,
  settingsGoogleMapUrl,
  settingsAddress,
  CURRENCY_LOCALES,
  dealers,
  selectedDealer,
  handleSelectDealer,
  handleUpdateDealerSettings,
} = useSettingsModal();
const {
  successToast,
  errorToast,
  clearSuccessToast,
  clearErrorToast,
  triggerToast,
  triggerErrorToast,
} = useToasts();
const { dsrInPortalMode, dsrPortalDealer } = useDsrPortal();

// AddRepModal state
const showAddRepModal = ref(false);
const dsrRosterRef = ref<{ fetchData: () => Promise<void> } | null>(null);

// ─── Billing redirect detection ────────────────────────────────────────────
// On mount and after every Astro page swap, check for ?billing_updated=
async function checkBillingReturn() {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  const updated = params.get("billing_updated");
  if (updated === null) return;

  // Strip the param
  params.delete("billing_updated");
  const newSearch = params.toString();
  const cleanUrl =
    window.location.pathname +
    (newSearch ? `?${newSearch}` : "") +
    window.location.hash;
  window.history.replaceState({}, "", cleanUrl);

  // Refresh auth state (invalidates + refetches)
  await refreshUser();
  await refreshAll();

  if (updated === "1") {
    triggerToast("Billing updated successfully. Your plan changes are now active.");
  } else {
    triggerErrorToast("Billing update failed or was cancelled. Your plan is unchanged.");
  }
}

function openAddRepModal() {
  showAddRepModal.value = true;
}

onMounted(() => {
  checkBillingReturn();
  document.addEventListener("astro:after-swap", checkBillingReturn);
  // Listen for "open add rep" requests from any page
  window.addEventListener("dealercore:open-add-rep", openAddRepModal);
});

onUnmounted(() => {
  document.removeEventListener("astro:after-swap", checkBillingReturn);
  window.removeEventListener("dealercore:open-add-rep", openAddRepModal);
});

// ─── Mobile bottom nav items ───────────────────────────────────────────────
const allNavItems = [
  { id: "dashboard", label: "Home", href: "/dashboard", accessKey: "dashboard" },
  { id: "team", label: "Team", href: "/team", accessKey: "manage_dsrs" },
  { id: "inventory", label: "Inventory", href: "/inventory", accessKey: "inventory" },
  { id: "suppliers", label: "Suppliers", href: "/suppliers", accessKey: "suppliers" },
  { id: "sales", label: "Sales", href: "/sales", accessKey: "sales" },
  { id: "collections", label: "Dues", href: "/collections", accessKey: "collections" },
  { id: "reports", label: "Reports", href: "/reports", accessKey: "reports" },
];

const navItems = computed(() => {
  return allNavItems.filter((item) => {
    if (item.accessKey === "manage_dsrs" && !dsrInPortalMode.value) {
      return true;
    }
    return hasAccess(item.accessKey).value;
  });
});

const currentPath = ref(
  typeof window !== "undefined" ? window.location.pathname : "/",
);

function updateCurrentPath() {
  currentPath.value = window.location.pathname;
}

onMounted(() => {
  document.addEventListener("astro:after-swap", updateCurrentPath);
});

onUnmounted(() => {
  document.removeEventListener("astro:after-swap", updateCurrentPath);
});

function isActive(href: string): boolean {
  if (href === "/dashboard") {
    return currentPath.value === "/" || currentPath.value === "/dashboard";
  }
  return currentPath.value === href || currentPath.value.startsWith(href + "/");
}

const dealerLabel = computed(() => {
  if (dsrInPortalMode.value) {
    return dsrPortalDealer.value?.full_name || "DSR";
  }
  return activeDealer.value?.fullName || "—";
});

const syncLabel = computed(() => (dsrInPortalMode.value ? "DSR Portal Mode" : "Synced"));
</script>

<template>
  <div>
    <!-- Status Bar Footer -->
    <footer class="status-bar">
      <div class="status-bar-left">
        <div class="status-dot"></div>
        <span class="status-text">
          <strong>{{ dealerLabel }}</strong> — {{ syncLabel }}
        </span>
      </div>
      <div class="status-bar-right">
        <span class="status-terminal">DEALERCORE v3.0</span>
      </div>
    </footer>

    <!-- Mobile Bottom Navigation Bar -->
    <nav class="mobile-bottomnav">
      <a
        v-for="item in navItems"
        :key="item.id"
        :id="`mobile-nav-${item.id}`"
        :href="item.href"
        :class="['mobile-bottomnav-item', { 'mobile-bottomnav-item--active': isActive(item.href) }]"
      >
        <LayoutDashboard v-if="item.id === 'dashboard'" class="mobile-bottomnav-icon" />
        <UserCircle v-else-if="item.id === 'team'" class="mobile-bottomnav-icon" />
        <Package v-else-if="item.id === 'inventory'" class="mobile-bottomnav-icon" />
        <Users v-else-if="item.id === 'suppliers'" class="mobile-bottomnav-icon" />
        <ShoppingCart v-else-if="item.id === 'sales'" class="mobile-bottomnav-icon" />
        <Coins v-else-if="item.id === 'collections'" class="mobile-bottomnav-icon" />
        <AlertTriangle v-else-if="item.id === 'bad-debt'" class="mobile-bottomnav-icon" />
        <FilePieChart v-else-if="item.id === 'reports'" class="mobile-bottomnav-icon" />
        <span class="mobile-bottomnav-label">{{ item.label }}</span>
      </a>
    </nav>

    <!-- ─── Toast Notifications ─────────────────────────────────────────── -->
    <Transition name="toast">
      <div v-if="successToast" class="toast-notification toast-notification--floating">
        <div class="toast-dot"></div>
        <span class="toast-message">{{ successToast }}</span>
        <button @click="clearSuccessToast" class="toast-close">
          <X class="toast-close-icon" />
        </button>
      </div>
    </Transition>

    <Transition name="toast">
      <div
        v-if="errorToast"
        class="toast-notification toast-notification--error toast-notification--floating"
      >
        <div class="toast-dot toast-dot--error"></div>
        <span class="toast-message">{{ errorToast }}</span>
        <button @click="clearErrorToast" class="toast-close">
          <X class="toast-close-icon" />
        </button>
      </div>
    </Transition>

    <!-- ─── Settings Modal ──────────────────────────────────────────────── -->
    <Transition name="modal">
      <div v-if="showSettingsModal" class="modal-overlay">
        <div @click="closeSettings" class="modal-backdrop" />

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
            <button @click="closeSettings" class="modal-close-btn">
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
                  :class="[
                    'modal-dealer-card',
                    { 'modal-dealer-card--active': selectedDealer?.username === d.username },
                  ]"
                >
                  <div class="modal-dealer-avatar-wrap">
                    <div
                      :class="[
                        'modal-dealer-avatar',
                        selectedDealer?.username === d.username ? 'modal-dealer-avatar--active' : '',
                      ]"
                    >
                      {{
                        d.fullName
                          ? d.fullName
                              .split(" ")
                              .map((n: string) => n[0] || "")
                              .join("")
                          : "?"
                      }}
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
            <div v-if="selectedDealer" class="modal-currency-section">
              <div class="modal-currency-header">
                <span class="modal-currency-emoji">💰</span>
                <label class="modal-currency-label">Default Currency ({{ selectedDealer.fullName }})</label>
              </div>
              <p class="modal-currency-desc">
                Sets the formatting for all invoices, COGS values, credit ledgers, and reports.
              </p>

              <select v-model="settingsSelectedCurrency" class="modal-currency-select">
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
                    new Intl.NumberFormat(
                      CURRENCY_LOCALES[settingsSelectedCurrency] || "en-US",
                      {
                        style: "currency",
                        currency: settingsSelectedCurrency,
                        maximumFractionDigits: 0,
                      },
                    ).format(1248500)
                  }}
                </span>
              </div>
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="modal-footer">
            <button type="button" @click="closeSettings" class="modal-btn modal-btn--secondary">
              Cancel
            </button>
            <button
              type="button"
              :disabled="!selectedDealer?.username"
              @click="handleUpdateDealerSettings"
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
      @added="showAddRepModal = false; refreshAll();"
    />
  </div>
</template>

<style scoped>
/* Floating toasts position above all content but below modals */
.toast-notification--floating {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
  max-width: none;
}
</style>
