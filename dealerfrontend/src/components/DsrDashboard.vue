<script setup lang="ts">
/**
 * DSR Dashboard
 * -------------
 * Main dashboard for logged-in DSRs.
 * Shows invitations, assignments, and provides access to dealer tools.
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
import dsrAuthService, { type DealerChoice, type DsrUser } from '../services/api/dsrAuth.service';

const emit = defineEmits<{
  (e: 'logout'): void;
  (e: 'enterDealerPortal'): void;
}>();

// State
const user = ref<DsrUser | null>(null);
const selectedDealer = ref<DealerChoice | null>(null);
const dealers = ref<DealerChoice[]>([]);
const invitations = ref<any[]>([]);
const assignments = ref<any[]>([]);
const isLoading = ref(true);
const error = ref('');
const activeTab = ref<'overview' | 'invitations' | 'assignments'>('overview');

// Computed
const pendingInvitations = computed(() => 
  invitations.value.filter(inv => inv.status === 'pending')
);

const activeAssignments = computed(() => 
  assignments.value.filter(a => a.status === 'active')
);

// Methods
async function loadDashboard() {
  isLoading.value = true;
  error.value = '';
  
  try {
    // Get stored user and dealer
    user.value = dsrAuthService.getUser();
    selectedDealer.value = dsrAuthService.getSelectedDealer();
    
    // Fetch profile from API
    const profile = await dsrAuthService.getProfile();
    user.value = profile.user;
    dealers.value = profile.dealers;
    if (profile.selected_dealer) {
      selectedDealer.value = profile.selected_dealer;
    }
    
    // Fetch invitations
    await fetchInvitations();
    
    // Fetch assignments
    await fetchAssignments();
  } catch (err: any) {
    console.error('Failed to load dashboard:', err);
    error.value = 'Failed to load dashboard. Please try again.';
  } finally {
    isLoading.value = false;
  }
}

async function fetchInvitations() {
  try {
    const response = await fetch('/api/dsr/invitations', {
      headers: {
        'Authorization': `Bearer ${dsrAuthService.getAccessToken()}`
      }
    });
    if (response.ok) {
      invitations.value = await response.json();
    }
  } catch (err) {
    console.error('Failed to fetch invitations:', err);
  }
}

async function fetchAssignments() {
  try {
    const response = await fetch('/api/dsr/assignments', {
      headers: {
        'Authorization': `Bearer ${dsrAuthService.getAccessToken()}`
      }
    });
    if (response.ok) {
      assignments.value = await response.json();
    }
  } catch (err) {
    console.error('Failed to fetch assignments:', err);
  }
}

async function acceptInvitation(invitationId: string) {
  try {
    const response = await fetch(`/api/dsr/invitations/${invitationId}/accept`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${dsrAuthService.getAccessToken()}`
      }
    });
    
    if (response.ok) {
      await loadDashboard();
    } else {
      const data = await response.json();
      error.value = data.detail || 'Failed to accept invitation';
    }
  } catch (err) {
    error.value = 'Failed to accept invitation';
  }
}

async function rejectInvitation(invitationId: string) {
  if (!confirm('Are you sure you want to reject this invitation?')) return;
  
  try {
    const response = await fetch(`/api/dsr/invitations/${invitationId}/reject`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${dsrAuthService.getAccessToken()}`
      }
    });
    
    if (response.ok) {
      await loadDashboard();
    } else {
      const data = await response.json();
      error.value = data.detail || 'Failed to reject invitation';
    }
  } catch (err) {
    error.value = 'Failed to reject invitation';
  }
}

async function leaveDealer(assignmentId: string) {
  if (!confirm('Are you sure you want to leave this dealer? Your transaction records will be preserved.')) return;
  
  try {
    const response = await fetch(`/api/dsr/assignments/${assignmentId}/leave`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${dsrAuthService.getAccessToken()}`
      }
    });
    
    if (response.ok) {
      await loadDashboard();
    } else {
      const data = await response.json();
      error.value = data.detail || 'Failed to leave dealer';
    }
  } catch (err) {
    error.value = 'Failed to leave dealer';
  }
}

async function selectDealerAndEnter(dealer: DealerChoice) {
  try {
    await dsrAuthService.selectDealer(dealer.username);
    selectedDealer.value = dealer;
    emit('enterDealerPortal');
  } catch (err: any) {
    error.value = err?.response?.data?.detail || 'Failed to select dealer';
  }
}

function handleLogout() {
  dsrAuthService.clearAuth();
  emit('logout');
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

// Lifecycle
onMounted(() => {
  loadDashboard();
});
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center gap-3">
            <div class="bg-emerald-100 p-2 rounded-lg">
              <Store class="h-6 w-6 text-emerald-600" />
            </div>
            <div>
              <h1 class="text-lg font-bold text-slate-800">DSR Portal</h1>
              <p class="text-xs text-slate-500">{{ user?.full_name || 'Loading...' }}</p>
            </div>
          </div>
          
          <div class="flex items-center gap-3">
            <button 
              @click="loadDashboard"
              :disabled="isLoading"
              class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition"
            >
              <RefreshCw :class="['h-5 w-5', { 'animate-spin': isLoading }]" />
            </button>
            <button 
              @click="handleLogout"
              class="flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition"
            >
              <LogOut class="h-4 w-4" />
              <span class="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Error Alert -->
      <div v-if="error" class="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
        <AlertCircle class="h-5 w-5 text-red-600 shrink-0" />
        <p class="text-red-700">{{ error }}</p>
        <button @click="error = ''" class="ml-auto text-red-600 hover:text-red-700">
          <XCircle class="h-4 w-4" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="animate-spin h-10 w-10 border-4 border-emerald-500 border-t-transparent rounded-full"></div>
      </div>

      <!-- Dashboard Content -->
      <template v-else>
        <!-- Quick Stats -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center gap-3">
              <div class="bg-blue-100 p-3 rounded-lg">
                <Building2 class="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p class="text-sm text-slate-500">Active Dealers</p>
                <p class="text-2xl font-bold text-slate-800">{{ activeAssignments.length }}</p>
              </div>
            </div>
          </div>
          
          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center gap-3">
              <div class="bg-amber-100 p-3 rounded-lg">
                <Mail class="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <p class="text-sm text-slate-500">Pending Invitations</p>
                <p class="text-2xl font-bold text-slate-800">{{ pendingInvitations.length }}</p>
              </div>
            </div>
          </div>
          
          <div class="bg-white rounded-xl border border-slate-200 p-5">
            <div class="flex items-center gap-3">
              <div class="bg-emerald-100 p-3 rounded-lg">
                <User class="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <p class="text-sm text-slate-500">Profile Status</p>
                <p class="text-lg font-semibold text-emerald-600">Active</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Two Column Layout -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Pending Invitations -->
          <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Mail class="h-5 w-5 text-amber-600" />
                <h2 class="font-semibold text-slate-800">Pending Invitations</h2>
              </div>
              <span v-if="pendingInvitations.length > 0" class="px-2 py-1 bg-amber-100 text-amber-700 text-xs font-semibold rounded-full">
                {{ pendingInvitations.length }} new
              </span>
            </div>
            
            <div v-if="pendingInvitations.length === 0" class="p-8 text-center">
              <Mail class="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <p class="text-slate-500">No pending invitations</p>
              <p class="text-sm text-slate-400 mt-1">Dealers can invite you using your phone number</p>
            </div>
            
            <div v-else class="divide-y divide-slate-100">
              <div 
                v-for="inv in pendingInvitations" 
                :key="inv.id"
                class="p-4 hover:bg-slate-50 transition"
              >
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="font-semibold text-slate-800">{{ inv.dealer_name || inv.dealer?.full_name }}</p>
                    <p class="text-sm text-slate-500">Role: {{ inv.role }}</p>
                    <p class="text-xs text-slate-400 mt-1">Invited: {{ formatDate(inv.created_at) }}</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button 
                      @click="acceptInvitation(inv.id)"
                      class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg transition flex items-center gap-1"
                    >
                      <CheckCircle class="h-4 w-4" />
                      Accept
                    </button>
                    <button 
                      @click="rejectInvitation(inv.id)"
                      class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium rounded-lg transition flex items-center gap-1"
                    >
                      <XCircle class="h-4 w-4" />
                      Reject
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Active Assignments -->
          <div class="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Building2 class="h-5 w-5 text-blue-600" />
                <h2 class="font-semibold text-slate-800">Your Dealers</h2>
              </div>
            </div>
            
            <div v-if="activeAssignments.length === 0" class="p-8 text-center">
              <Building2 class="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <p class="text-slate-500">No dealer assignments</p>
              <p class="text-sm text-slate-400 mt-1">Accept invitations from dealers to get started</p>
            </div>
            
            <div v-else class="divide-y divide-slate-100">
              <div 
                v-for="assignment in activeAssignments" 
                :key="assignment.id"
                class="p-4 hover:bg-slate-50 transition"
              >
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <p class="font-semibold text-slate-800">{{ assignment.dealer_name || assignment.dealer?.full_name }}</p>
                    <div class="flex items-center gap-2 mt-1">
                      <span class="px-2 py-0.5 bg-emerald-100 text-emerald-700 text-xs font-medium rounded">{{ assignment.role }}</span>
                      <span v-if="assignment.dealer?.business_name" class="text-sm text-slate-500">{{ assignment.dealer.business_name }}</span>
                    </div>
                    <p class="text-xs text-slate-400 mt-1">Since: {{ formatDate(assignment.assigned_at) }}</p>
                  </div>
                  <div class="flex items-center gap-2">
                    <button 
                      @click="selectDealerAndEnter(assignment.dealer)"
                      class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition flex items-center gap-1"
                    >
                      Enter Portal
                      <ChevronRight class="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="mt-8 bg-white rounded-xl border border-slate-200 p-6">
          <h3 class="font-semibold text-slate-800 mb-4">Quick Actions</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div class="p-4 bg-slate-50 rounded-lg text-center cursor-pointer hover:bg-slate-100 transition" @click="$emit('enterDealerPortal')">
              <ShoppingBag class="h-8 w-8 text-blue-600 mx-auto mb-2" />
              <p class="text-sm font-medium text-slate-700">Record Sale</p>
            </div>
            <div class="p-4 bg-slate-50 rounded-lg text-center cursor-pointer hover:bg-slate-100 transition">
              <Package class="h-8 w-8 text-amber-600 mx-auto mb-2" />
              <p class="text-sm font-medium text-slate-700">View Inventory</p>
            </div>
            <div class="p-4 bg-slate-50 rounded-lg text-center cursor-pointer hover:bg-slate-100 transition">
              <Coins class="h-8 w-8 text-emerald-600 mx-auto mb-2" />
              <p class="text-sm font-medium text-slate-700">Collections</p>
            </div>
            <div class="p-4 bg-slate-50 rounded-lg text-center cursor-pointer hover:bg-slate-100 transition">
              <FileText class="h-8 w-8 text-purple-600 mx-auto mb-2" />
              <p class="text-sm font-medium text-slate-700">Reports</p>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>
