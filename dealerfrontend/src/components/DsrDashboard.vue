<script setup lang="ts">
/**
 * DSR Dashboard
 * -------------
 * Main dashboard for logged-in DSRs.
 * Shows invitations, assignments, profile editing, and provides access to dealer tools.
 * 
 * FIX DSR-014: Added "Profile" tab with profile editing and password change.
 * 
 * Uses the isolated dsrClient - NO dependency on dealer auth.
 */
import { ref, computed, onMounted } from 'vue';
import { 
  Store, 
  Mail, 
  Building2, 
  CheckCircle, 
  XCircle, 
  Clock, 
  LogOut,
  User,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  ShoppingBag,
  Package,
  Coins,
  FileText,
  Save,
  Key,
  Eye,
  EyeOff,
  ShieldCheck,
  Send
} from 'lucide-vue-next';
import { 
  dsrApi, 
  getDsrUser, 
  getDsrSelectedDealer, 
  getDsrAccessToken,
  clearDsrAuth,
  type DealerChoice, 
  type DsrUser 
} from '../services/dsrClient';
import { setAccessMap } from '../composables/useAccess';
import { useDsrPortal } from '../composables/useDsrPortal';
import { useDsrAccessRefresh } from '../composables/useDsrAccessRefresh';
import { useToasts } from '../composables/useToasts';

// No emits — navigation is via window.location.href (MPA pattern).

// State
const user = ref<DsrUser | null>(null);
const selectedDealer = ref<DealerChoice | null>(null);
const dealers = ref<DealerChoice[]>([]);
const invitations = ref<{ pending: any[]; accepted: any[]; rejected: any[] }>({ pending: [], accepted: [], rejected: [] });
const assignments = ref<{ active: any[]; removed: any[]; left: any[] }>({ active: [], removed: [], left: [] });
const isLoading = ref(true);
const error = ref('');
const activeTab = ref<'overview' | 'invitations' | 'assignments' | 'profile'>('overview');

// ─── FIX DSR-014: Profile editing state ────────────────────────────────
const profileForm = ref({
  full_name: '',
  phone: '',
  bio: '',
});
const profileSaving = ref(false);
const profileSaved = ref(false);
const profileError = ref('');

// Password change state
const passwordForm = ref({
  current_password: '',
  new_password: '',
  confirm_password: '',
});
const passwordSaving = ref(false);
const passwordSaved = ref(false);
const passwordError = ref('');
const showCurrentPassword = ref(false);
const showNewPassword = ref(false);

// ─── FIX DSR-INV-005: Email verification state ────────────────────────
const emailVerified = computed(() => (user.value as any)?.email_verified !== false);
const resendVerificationLoading = ref(false);
const resendVerificationSent = ref(false);
const resendVerificationError = ref('');

// Computed - use the pending/active arrays directly from the backend response
const pendingInvitations = computed(() => invitations.value.pending || []);
const activeAssignments = computed(() => assignments.value.active || []);
const allInvitations = computed(() => [
  ...(invitations.value.pending || []),
  ...(invitations.value.accepted || []),
  ...(invitations.value.rejected || [])
]);

// Methods
async function loadDashboard() {
  isLoading.value = true;
  error.value = '';
  
  try {
    user.value = getDsrUser();
    selectedDealer.value = getDsrSelectedDealer();
    
    // Audit fix C1+C3: bootstrap the DSR session by minting a fresh
    // access token from the httpOnly refresh cookie. Previously the
    // dashboard tried to call /dsr/auth/me directly with a localStorage
    // token — but that token is gone on a fresh page load (it lives in
    // memory only now). bootstrapDsrSession calls the refresh-cookie
    // proxy and populates the in-memory access token; if the cookie is
    // absent/expired, it redirects to /dsr/login.
    const { bootstrapDsrSession } = await import('../services/dsrClient');
    const token = await bootstrapDsrSession();
    if (!token) {
      // bootstrapDsrSession already redirected to /dsr/login
      return;
    }
    
    // Fetch profile from API
    const profile = await dsrApi.getProfile();
    
    user.value = profile.user as DsrUser;
    dealers.value = profile.dealers || [];
    if (profile.selected_dealer) {
      selectedDealer.value = profile.selected_dealer;
    }
    
    // Initialize profile form from user data
    profileForm.value = {
      full_name: profile.user.full_name || '',
      phone: profile.user.phone || '',
      bio: (profile.user as any).bio || '',
    };
    
    // Fetch invitations
    await fetchInvitations();
    
    // Fetch assignments
    await fetchAssignments();
  } catch (err: any) {
    error.value = err?.message || 'Failed to load dashboard. Please try again.';
    
    if (err?.status === 401) {
      // The refresh interceptor in dsrClient should have handled this,
      // but if we still get here, the session is truly expired.
      clearDsrAuth();
      window.location.href = '/dsr/login';
    }
  } finally {
    isLoading.value = false;
  }
}

async function fetchInvitations() {
  try {
    invitations.value = await dsrApi.getInvitations();
  } catch (err: any) {
    // FIX DSR-INV-003: Log the error instead of silently swallowing it.
    // A 401 here means the token is invalid (should not happen since
    // getProfile succeeded), but other errors (500, CORS, network)
    // should be visible for debugging.
    console.error('[DSR DASHBOARD] Failed to fetch invitations:', err?.message || err);
    invitations.value = { pending: [], accepted: [], rejected: [] };
  }
}

async function fetchAssignments() {
  try {
    assignments.value = await dsrApi.getAssignments();
  } catch (err: any) {
    console.error('[DSR DASHBOARD] Failed to fetch assignments:', err?.message || err);
    assignments.value = { active: [], removed: [], left: [] };
  }
}

async function acceptInvitation(invitationId: string) {
  try {
    await dsrApi.acceptInvitation(invitationId);
    await loadDashboard();
  } catch (err: any) {
    // FIX DSR-INV-005: Show specific message for email verification required
    const code = err?.data?.code;
    if (code === 'email_not_verified' || err?.status === 403) {
      error.value = 'Please verify your email address before accepting invitations. Check the verification banner above or go to your Profile to resend the verification email.';
    } else {
      error.value = err?.message || 'Failed to accept invitation';
    }
  }
}

async function rejectInvitation(invitationId: string) {
  if (!confirm('Are you sure you want to reject this invitation?')) return;
  
  try {
    await dsrApi.rejectInvitation(invitationId);
    await loadDashboard();
  } catch (err: any) {
    error.value = err?.message || 'Failed to reject invitation';
  }
}

async function handleLogout() {
  try {
    await dsrApi.logout();
  } catch (e) {
    console.warn('[DSR DASHBOARD] Server logout failed, clearing local state:', e);
    clearDsrAuth();
  }
  window.location.href = '/dsr/login';
}

// ─── FIX DSR-INV-005: Email verification handler ────────────────────────
async function handleResendVerification() {
  resendVerificationLoading.value = true;
  resendVerificationError.value = '';
  resendVerificationSent.value = false;
  
  try {
    await dsrApi.resendVerification();
    resendVerificationSent.value = true;
    setTimeout(() => { resendVerificationSent.value = false; }, 10000);
  } catch (err: any) {
    resendVerificationError.value = err?.message || 'Failed to send verification email. Please try again.';
  } finally {
    resendVerificationLoading.value = false;
  }
}

async function handleEnterPortal(assignment: any) {
  const dealer = assignment?.dealer;
  if (!dealer?.username) {
    console.error('[DSR DASHBOARD] No dealer username in assignment');
    return;
  }

  const { triggerToast, triggerErrorToast } = useToasts();
  const { enterPortalMode } = useDsrPortal();
  const { startDsrAccessRefreshTimer } = useDsrAccessRefresh();

  try {
    // Select the dealer context — backend returns DSR-scoped JWT tokens AND
    // the single-source-of-truth `effective_access` map.
    const { dsrApi: dsr, setDsrSelectedDealer } = await import('../services/dsrClient');
    const result = await dsr.selectDealer(dealer.username);

    // Store dealer selection
    setDsrSelectedDealer(result.dealer);
    selectedDealer.value = result.dealer;

    // Set the access map directly from the backend-computed intersection
    const effectiveAccess =
      result.effective_access || { dashboard: true, __subscription_active: false };
    setAccessMap(effectiveAccess);

    // Enter portal mode (persists to localStorage so it survives the navigation)
    enterPortalMode({
      username: result.dealer.username,
      full_name: result.dealer.full_name,
      business_name: result.dealer.business_name,
    });

    // Start the periodic access-refresh timer
    startDsrAccessRefreshTimer();

    const dealerLabel =
      result.dealer.full_name || result.dealer.business_name || 'dealer';
    triggerToast(`Connected to ${dealerLabel}. You're now in the dealer portal.`);

    // Navigate to /dashboard — AppShell will detect portal mode and show the banner
    window.location.href = '/dashboard';
  } catch (error: any) {
    console.error('[DSR DASHBOARD] Failed to enter portal:', error);
    triggerErrorToast('Failed to connect to dealer portal. Please try again.');
  }
}

// ─── FIX DSR-014: Profile & Password handlers ─────────────────────────

async function saveProfile() {
  profileSaving.value = true;
  profileError.value = '';
  profileSaved.value = false;
  
  try {
    const updates: Record<string, string> = {};
    if (profileForm.value.full_name !== (user.value?.full_name || '')) {
      updates.full_name = profileForm.value.full_name;
    }
    if (profileForm.value.phone !== (user.value?.phone || '')) {
      updates.phone = profileForm.value.phone;
    }
    if (profileForm.value.bio !== ((user.value as any)?.bio || '')) {
      updates.bio = profileForm.value.bio;
    }
    
    if (Object.keys(updates).length > 0) {
      await dsrApi.updateProfile(updates);
      // Refresh user data
      const profile = await dsrApi.getProfile();
      user.value = profile.user as DsrUser;
    }
    
    profileSaved.value = true;
    setTimeout(() => { profileSaved.value = false; }, 3000);
  } catch (err: any) {
    profileError.value = err?.message || 'Failed to update profile';
  } finally {
    profileSaving.value = false;
  }
}

async function changePassword() {
  passwordSaving.value = true;
  passwordError.value = '';
  passwordSaved.value = false;
  
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordError.value = 'Passwords do not match';
    passwordSaving.value = false;
    return;
  }
  
  if (passwordForm.value.new_password.length < 8) {
    passwordError.value = 'Password must be at least 8 characters';
    passwordSaving.value = false;
    return;
  }
  
  try {
    await dsrApi.changePassword(
      passwordForm.value.current_password,
      passwordForm.value.new_password,
    );
    
    passwordSaved.value = true;
    passwordForm.value = {
      current_password: '',
      new_password: '',
      confirm_password: '',
    };
    setTimeout(() => { passwordSaved.value = false; }, 3000);
  } catch (err: any) {
    passwordError.value = err?.message || 'Failed to change password';
  } finally {
    passwordSaving.value = false;
  }
}

onMounted(() => {
  loadDashboard();
});
</script>

<template>
  <div class="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="bg-emerald-100 p-2 rounded-xl">
            <Store class="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <h1 class="text-xl font-bold text-slate-800">DSR Portal</h1>
            <p v-if="user" class="text-sm text-slate-500">{{ user.email }}</p>
          </div>
        </div>
        
        <button
          @click="handleLogout"
          class="flex items-center gap-2 px-4 py-2 text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
        >
          <LogOut class="h-5 w-5" />
          <span class="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 py-6">
      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center py-12">
        <RefreshCw class="h-8 w-8 text-emerald-600 animate-spin" />
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
        <div class="flex items-center gap-3">
          <AlertCircle class="h-5 w-5 text-red-600" />
          <p class="text-red-800">{{ error }}</p>
        </div>
        <button
          @click="loadDashboard"
          class="mt-3 text-sm text-red-600 hover:text-red-700 font-medium"
        >
          Try again
        </button>
      </div>

      <!-- Dashboard Content -->
      <template v-else>
        <!-- FIX DSR-INV-005: Email Verification Banner -->
        <div v-if="!emailVerified" class="mb-6 bg-amber-50 border border-amber-300 rounded-xl p-4 shadow-sm">
          <div class="flex items-start gap-4">
            <div class="bg-amber-100 p-3 rounded-xl shrink-0">
              <ShieldCheck class="h-6 w-6 text-amber-600" />
            </div>
            <div class="flex-1 min-w-0">
              <h3 class="text-base font-semibold text-amber-800 mb-1">Email Verification Required</h3>
              <p class="text-sm text-amber-700 mb-3">
                Your email <strong>{{ user?.email }}</strong> is not verified yet. You must verify your email before you can accept dealer invitations.
                Please check your inbox for the verification link, or resend it below.
              </p>
              <div class="flex flex-wrap items-center gap-3">
                <button
                  @click="handleResendVerification"
                  :disabled="resendVerificationLoading || resendVerificationSent"
                  class="inline-flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-300 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition"
                >
                  <svg v-if="resendVerificationLoading" class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                  </svg>
                  <Send v-else class="h-4 w-4" />
                  {{ resendVerificationSent ? 'Email Sent!' : resendVerificationLoading ? 'Sending...' : 'Resend Verification Email' }}
                </button>
                <span v-if="resendVerificationSent" class="text-sm text-emerald-600 font-medium">
                  Check your inbox!
                </span>
              </div>
              <p v-if="resendVerificationError" class="mt-2 text-sm text-red-600">{{ resendVerificationError }}</p>
            </div>
          </div>
        </div>

        <!-- Tabs -->
        <div class="flex gap-2 mb-6 overflow-x-auto pb-2">
          <button
            @click="activeTab = 'overview'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition whitespace-nowrap',
              activeTab === 'overview'
                ? 'bg-emerald-600 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-50'
            ]"
          >
            Overview
          </button>
          <button
            @click="activeTab = 'invitations'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition whitespace-nowrap relative',
              activeTab === 'invitations'
                ? 'bg-emerald-600 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-50'
            ]"
          >
            Invitations
            <span
              v-if="pendingInvitations.length > 0"
              :class="[
                'ml-2 px-2 py-0.5 rounded-full text-xs font-semibold',
                activeTab === 'invitations'
                  ? 'bg-white/20 text-white'
                  : 'bg-amber-100 text-amber-700'
              ]"
            >
              {{ pendingInvitations.length }}
            </span>
          </button>
          <button
            @click="activeTab = 'assignments'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition whitespace-nowrap',
              activeTab === 'assignments'
                ? 'bg-emerald-600 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-50'
            ]"
          >
            My Dealers
          </button>
          <!-- FIX DSR-014: Profile tab -->
          <button
            @click="activeTab = 'profile'"
            :class="[
              'px-4 py-2 rounded-lg font-medium transition whitespace-nowrap',
              activeTab === 'profile'
                ? 'bg-emerald-600 text-white'
                : 'bg-white text-slate-600 hover:bg-slate-50'
            ]"
          >
            Profile
          </button>
        </div>

        <!-- Overview Tab -->
        <div v-if="activeTab === 'overview'" class="space-y-6">
          <!-- Stats Cards -->
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-white rounded-xl p-6 shadow-sm border border-slate-100">
              <div class="flex items-center gap-3 mb-2">
                <div class="bg-emerald-100 p-2 rounded-lg">
                  <Building2 class="h-5 w-5 text-emerald-600" />
                </div>
                <span class="text-sm text-slate-500">Active Dealers</span>
              </div>
              <p class="text-2xl font-bold text-slate-800">{{ activeAssignments.length }}</p>
            </div>
            
            <div class="bg-white rounded-xl p-6 shadow-sm border border-slate-100">
              <div class="flex items-center gap-3 mb-2">
                <div class="bg-amber-100 p-2 rounded-lg">
                  <Mail class="h-5 w-5 text-amber-600" />
                </div>
                <span class="text-sm text-slate-500">Pending Invitations</span>
              </div>
              <p class="text-2xl font-bold text-slate-800">{{ pendingInvitations.length }}</p>
            </div>
          </div>

          <!-- Awaiting Invitation Notice -->
          <div
            v-if="activeAssignments.length === 0 && pendingInvitations.length === 0"
            class="bg-amber-50 border border-amber-200 rounded-xl p-6"
          >
            <div class="flex items-start gap-4">
              <div class="bg-amber-100 p-3 rounded-xl">
                <Mail class="h-6 w-6 text-amber-600" />
              </div>
              <div>
                <h3 class="text-lg font-semibold text-amber-800 mb-1">Awaiting Invitation</h3>
                <p class="text-amber-700">
                  You're not currently assigned to any dealer. Once a dealer sends you an invitation,
                  it will appear here. You can then accept or reject it.
                </p>
              </div>
            </div>
          </div>

          <!-- Pending Invitations Preview -->
          <div v-if="pendingInvitations.length > 0" class="bg-white rounded-xl shadow-sm border border-slate-100">
            <div class="p-4 border-b border-slate-100">
              <div class="flex items-center justify-between">
                <h3 class="font-semibold text-slate-800">Pending Invitations</h3>
                <span v-if="pendingInvitations.length > 0" class="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-semibold rounded-full">
                  {{ pendingInvitations.length }} new
                </span>
              </div>
            </div>
            
            <div v-if="pendingInvitations.length === 0" class="p-8 text-center">
              <Mail class="h-12 w-12 text-slate-300 mx-auto mb-3" />
              <p class="text-slate-500">No pending invitations</p>
            </div>
            
            <div v-else class="divide-y divide-slate-100">
              <div
                v-for="inv in pendingInvitations.slice(0, 3)"
                :key="inv.id"
                class="p-4 hover:bg-slate-50 transition"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                      <Building2 class="h-5 w-5 text-emerald-600" />
                    </div>
                    <div>
                      <p class="font-medium text-slate-800">{{ inv.dealer?.business_name || inv.dealer?.full_name || 'Unknown Dealer' }}</p>
                      <p class="text-sm text-slate-500">{{ inv.role || 'DSR' }}</p>
                    </div>
                  </div>
                  <div class="flex gap-2">
                    <button
                      @click="acceptInvitation(inv.id)"
                      class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition"
                    >
                      Accept
                    </button>
                    <button
                      @click="rejectInvitation(inv.id)"
                      class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Active Assignments -->
          <div v-if="activeAssignments.length > 0" class="bg-white rounded-xl shadow-sm border border-slate-100">
            <div class="p-4 border-b border-slate-100">
              <h3 class="font-semibold text-slate-800">My Dealers</h3>
            </div>
            
            <div v-if="activeAssignments.length === 0" class="p-8 text-center">
              <Building2 class="h-12 w-12 text-slate-300 mx-auto mb-3" />
              <p class="text-slate-500">No dealer assignments yet</p>
            </div>
            
            <div v-else class="divide-y divide-slate-100">
              <div
                v-for="assignment in activeAssignments"
                :key="assignment.id"
                class="p-4 hover:bg-slate-50 transition cursor-pointer"
                @click="handleEnterPortal(assignment)"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                      <Building2 class="h-5 w-5 text-emerald-600" />
                    </div>
                    <div>
                      <p class="font-medium text-slate-800">{{ assignment.dealer?.full_name || assignment.dealer_name || 'Unknown' }}</p>
                      <p class="text-sm text-slate-500">{{ assignment.role || 'DSR' }}</p>
                    </div>
                  </div>
                  <ChevronRight class="h-5 w-5 text-slate-400" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Invitations Tab -->
        <div v-if="activeTab === 'invitations'" class="bg-white rounded-xl shadow-sm border border-slate-100">
          <div class="p-4 border-b border-slate-100">
            <h3 class="font-semibold text-slate-800">All Invitations</h3>
          </div>
          
          <div v-if="allInvitations.length === 0" class="p-8 text-center">
            <Mail class="h-12 w-12 text-slate-300 mx-auto mb-3" />
            <p class="text-slate-500">No invitations yet</p>
          </div>
          
          <div v-else class="divide-y divide-slate-100">
            <div
              v-for="inv in allInvitations"
              :key="inv.id"
              class="p-4 hover:bg-slate-50 transition"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div 
                    :class="[
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      inv.status === 'pending' ? 'bg-amber-100' :
                      inv.status === 'accepted' ? 'bg-emerald-100' : 'bg-slate-100'
                    ]"
                  >
                    <Mail 
                      :class="[
                        'h-5 w-5',
                        inv.status === 'pending' ? 'text-amber-600' :
                        inv.status === 'accepted' ? 'text-emerald-600' : 'text-slate-400'
                      ]"
                    />
                  </div>
                  <div>
                    <p class="font-medium text-slate-800">{{ inv.dealer?.business_name || inv.dealer?.full_name || 'Unknown Dealer' }}</p>
                    <p class="text-sm text-slate-500">{{ inv.role || 'DSR' }} &bull; {{ inv.status }}</p>
                  </div>
                </div>
                <div v-if="inv.status === 'pending'" class="flex gap-2">
                  <button
                    @click="acceptInvitation(inv.id)"
                    class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition"
                  >
                    Accept
                  </button>
                  <button
                    @click="rejectInvitation(inv.id)"
                    class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition"
                  >
                    Reject
                  </button>
                </div>
                <div v-else>
                  <span 
                    :class="[
                      'px-2 py-1 rounded-full text-xs font-medium',
                      inv.status === 'accepted' ? 'bg-emerald-100 text-emerald-700' :
                      inv.status === 'rejected' ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-600'
                    ]"
                  >
                    {{ inv.status }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Assignments Tab -->
        <div v-if="activeTab === 'assignments'" class="bg-white rounded-xl shadow-sm border border-slate-100">
          <div class="p-4 border-b border-slate-100">
            <h3 class="font-semibold text-slate-800">My Dealer Assignments</h3>
          </div>
          
          <div v-if="activeAssignments.length === 0" class="p-8 text-center">
            <Building2 class="h-12 w-12 text-slate-300 mx-auto mb-3" />
            <p class="text-slate-500">No dealer assignments yet</p>
            <p class="text-sm text-slate-400 mt-1">Accept an invitation to get started</p>
          </div>
          
          <div v-else class="divide-y divide-slate-100">
            <div
              v-for="assignment in activeAssignments"
              :key="assignment.id"
              class="p-4 hover:bg-slate-50 transition cursor-pointer"
              @click="handleEnterPortal(assignment)"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                    <Building2 class="h-5 w-5 text-emerald-600" />
                  </div>
                  <div>
                    <p class="font-medium text-slate-800">{{ assignment.dealer?.full_name || assignment.dealer_name || 'Unknown' }}</p>
                    <p class="text-sm text-slate-500">{{ assignment.role || 'DSR' }}</p>
                  </div>
                </div>
                <ChevronRight class="h-5 w-5 text-slate-400" />
              </div>
            </div>
          </div>
        </div>

        <!-- ═══════════════════════════════════════════════════════════════
             FIX DSR-014: PROFILE TAB
             DSR profile editing and password change.
        ═══════════════════════════════════════════════════════════════ -->
        <div v-if="activeTab === 'profile'" class="space-y-6">
          <!-- Profile Info Card -->
          <div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
            <div class="p-6 border-b border-slate-100">
              <div class="flex items-center gap-4">
                <div class="w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center text-white text-2xl font-bold">
                  {{ user?.full_name?.charAt(0)?.toUpperCase() || '?' }}
                </div>
                <div>
                  <h3 class="text-lg font-bold text-slate-800">{{ user?.full_name || 'No name set' }}</h3>
                  <p class="text-sm text-slate-500">{{ user?.email }}</p>
                  <div class="flex items-center gap-2 mt-1">
                    <span v-if="user?.phone" class="text-xs text-slate-500">{{ user.phone }}</span>
                    <span v-if="user?.user_type" class="px-2 py-0.5 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700">
                      {{ user.user_type }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- FIX DSR-INV-005: Email verification status in Profile -->
            <div class="px-6 py-3 border-b border-slate-100">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <ShieldCheck v-if="emailVerified" class="h-4 w-4 text-emerald-500" />
                  <AlertCircle v-else class="h-4 w-4 text-amber-500" />
                  <span class="text-sm font-medium" :class="emailVerified ? 'text-emerald-700' : 'text-amber-700'">
                    Email: {{ emailVerified ? 'Verified' : 'Not Verified' }}
                  </span>
                </div>
                <button
                  v-if="!emailVerified"
                  @click="handleResendVerification"
                  :disabled="resendVerificationLoading || resendVerificationSent"
                  class="text-xs px-3 py-1.5 bg-amber-100 hover:bg-amber-200 disabled:bg-amber-50 disabled:text-amber-400 text-amber-700 font-medium rounded-lg transition"
                >
                  {{ resendVerificationSent ? 'Sent!' : resendVerificationLoading ? 'Sending...' : 'Resend Verification' }}
                </button>
              </div>
              <p v-if="!emailVerified" class="text-xs text-amber-600 mt-1">
                You must verify your email before accepting dealer invitations.
              </p>
              <p v-if="resendVerificationError" class="text-xs text-red-600 mt-1">{{ resendVerificationError }}</p>
            </div>

            <!-- Edit Profile Form -->
            <div class="p-6">
              <h4 class="text-sm font-semibold text-slate-700 mb-4">Edit Profile</h4>
              
              <div v-if="profileError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {{ profileError }}
              </div>
              <div v-if="profileSaved" class="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
                Profile updated successfully!
              </div>

              <form @submit.prevent="saveProfile" class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                  <input
                    v-model="profileForm.full_name"
                    type="text"
                    placeholder="Enter your full name"
                    class="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Phone</label>
                  <input
                    v-model="profileForm.phone"
                    type="tel"
                    placeholder="Enter your phone number"
                    class="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                  />
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Bio</label>
                  <textarea
                    v-model="profileForm.bio"
                    placeholder="Tell dealers about yourself..."
                    rows="3"
                    class="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 resize-none"
                  />
                </div>
                
                <button
                  type="submit"
                  :disabled="profileSaving"
                  class="flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                >
                  <Save v-if="!profileSaving" class="h-4 w-4" />
                  <RefreshCw v-else class="h-4 w-4 animate-spin" />
                  {{ profileSaving ? 'Saving...' : 'Save Changes' }}
                </button>
              </form>
            </div>
          </div>

          <!-- Change Password Card -->
          <div class="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
            <div class="p-6">
              <div class="flex items-center gap-2 mb-4">
                <Key class="h-5 w-5 text-slate-600" />
                <h4 class="text-sm font-semibold text-slate-700">Change Password</h4>
              </div>
              
              <div v-if="passwordError" class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                {{ passwordError }}
              </div>
              <div v-if="passwordSaved" class="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
                Password changed successfully!
              </div>

              <form @submit.prevent="changePassword" class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Current Password</label>
                  <div class="relative">
                    <input
                      v-model="passwordForm.current_password"
                      :type="showCurrentPassword ? 'text' : 'password'"
                      placeholder="Enter current password"
                      class="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 pr-10"
                      required
                    />
                    <button
                      type="button"
                      @click="showCurrentPassword = !showCurrentPassword"
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <Eye v-if="!showCurrentPassword" class="h-4 w-4" />
                      <EyeOff v-else class="h-4 w-4" />
                    </button>
                  </div>
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">New Password</label>
                  <div class="relative">
                    <input
                      v-model="passwordForm.new_password"
                      :type="showNewPassword ? 'text' : 'password'"
                      placeholder="Enter new password (min 8 characters)"
                      class="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 pr-10"
                      required
                    />
                    <button
                      type="button"
                      @click="showNewPassword = !showNewPassword"
                      class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      <Eye v-if="!showNewPassword" class="h-4 w-4" />
                      <EyeOff v-else class="h-4 w-4" />
                    </button>
                  </div>
                </div>
                
                <div>
                  <label class="block text-sm font-medium text-slate-700 mb-1">Confirm New Password</label>
                  <input
                    v-model="passwordForm.confirm_password"
                    type="password"
                    placeholder="Confirm new password"
                    class="w-full px-4 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                    required
                  />
                </div>
                
                <button
                  type="submit"
                  :disabled="passwordSaving"
                  class="flex items-center gap-2 px-4 py-2.5 bg-slate-700 hover:bg-slate-800 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
                >
                  <Key v-if="!passwordSaving" class="h-4 w-4" />
                  <RefreshCw v-else class="h-4 w-4 animate-spin" />
                  {{ passwordSaving ? 'Changing...' : 'Change Password' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
