<script setup lang="ts">
/**
 * DSR Dashboard
 * -------------
 * Main dashboard for logged-in DSRs.
 * Shows invitations, assignments, and provides access to dealer tools.
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
  FileText
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

const emit = defineEmits<{
  (e: 'logout'): void;
  (e: 'enterDealerPortal', dealer: any): void;
}>();

// State
const user = ref<DsrUser | null>(null);
const selectedDealer = ref<DealerChoice | null>(null);
const dealers = ref<DealerChoice[]>([]);
// Invitations grouped by status: { pending: [], accepted: [], rejected: [] }
const invitations = ref<{ pending: any[]; accepted: any[]; rejected: any[] }>({ pending: [], accepted: [], rejected: [] });
// Assignments grouped by status: { active: [], removed: [], left: [] }
const assignments = ref<{ active: any[]; removed: any[]; left: any[] }>({ active: [], removed: [], left: [] });
const isLoading = ref(true);
const error = ref('');
const activeTab = ref<'overview' | 'invitations' | 'assignments'>('overview');

// Computed - use the pending/active arrays directly from the backend response
const pendingInvitations = computed(() => invitations.value.pending || []);
const activeAssignments = computed(() => assignments.value.active || []);
// All invitations (for the invitations tab)
const allInvitations = computed(() => [
  ...(invitations.value.pending || []),
  ...(invitations.value.accepted || []),
  ...(invitations.value.rejected || [])
]);

// Methods
async function loadDashboard() {
  isLoading.value = true;
  error.value = '';
  
  console.log('[DSR DASHBOARD] Loading dashboard...');
  
  try {
    // Get stored user and dealer
    user.value = getDsrUser();
    selectedDealer.value = getDsrSelectedDealer();
    
    console.log('[DSR DASHBOARD] Stored user:', user.value?.email);
    console.log('[DSR DASHBOARD] Has token:', !!getDsrAccessToken());
    
    // Fetch profile from API
    const profile = await dsrApi.getProfile();
    console.log('[DSR DASHBOARD] Profile loaded:', profile);
    
    user.value = profile.user as DsrUser;
    dealers.value = profile.dealers || [];
    if (profile.selected_dealer) {
      selectedDealer.value = profile.selected_dealer;
    }
    
    // Fetch invitations
    await fetchInvitations();
    
    // Fetch assignments
    await fetchAssignments();
  } catch (err: any) {
    console.error('[DSR DASHBOARD] Failed to load:', err);
    error.value = err?.message || 'Failed to load dashboard. Please try again.';
    
    // If unauthorized, clear auth and redirect to login
    if (err?.status === 401) {
      console.log('[DSR DASHBOARD] Unauthorized - clearing auth');
      clearDsrAuth();
      emit('logout');
    }
  } finally {
    isLoading.value = false;
  }
}

async function fetchInvitations() {
  try {
    invitations.value = await dsrApi.getInvitations();
    const total = (invitations.value.pending?.length || 0) + 
                  (invitations.value.accepted?.length || 0) + 
                  (invitations.value.rejected?.length || 0);
    console.log('[DSR DASHBOARD] Invitations loaded:', total, invitations.value);
  } catch (err) {
    console.error('[DSR DASHBOARD] Failed to fetch invitations:', err);
    invitations.value = { pending: [], accepted: [], rejected: [] };
  }
}

async function fetchAssignments() {
  try {
    assignments.value = await dsrApi.getAssignments();
    console.log('[DSR DASHBOARD] Assignments loaded:', assignments.value);
  } catch (err) {
    console.error('[DSR DASHBOARD] Failed to fetch assignments:', err);
    assignments.value = { active: [], removed: [], left: [] };
  }
}

async function acceptInvitation(invitationId: string) {
  try {
    await dsrApi.acceptInvitation(invitationId);
    await loadDashboard();
  } catch (err: any) {
    error.value = err?.message || 'Failed to accept invitation';
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
  await dsrApi.logout();
  emit('logout');
}

function handleEnterPortal(assignment: any) {
  console.log('[DSR DASHBOARD] Entering dealer portal for:', assignment);
  const dealer = assignment.dealer;
  if (dealer) {
    selectedDealer.value = dealer;
    emit('enterDealerPortal', { ...assignment, dealer });
  } else {
    console.error('[DSR DASHBOARD] No dealer info in assignment');
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
                    <p class="text-sm text-slate-500">{{ inv.role || 'DSR' }} • {{ inv.status }}</p>
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
      </template>
    </main>
  </div>
</template>
