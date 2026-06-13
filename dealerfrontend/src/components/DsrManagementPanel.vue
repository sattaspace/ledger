<script setup lang="ts">
/**
 * DsrManagementPanel — Component for dealers to manage their DSRs.
 *
 * Features:
 * - View active DSRs with roles and permissions
 * - View pending invitations
 * - View removed/left DSRs
 * - Update DSR permissions
 * - Remove DSR from team
 * - Revoke pending invitations
 */
import { ref, computed, onMounted } from 'vue';
import {
  Users,
  Mail,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  MoreVertical,
  Edit,
  Trash2,
  RefreshCw,
  Shield,
  UserX,
  UserCheck,
  ChevronDown
} from 'lucide-vue-next';
import apiClient from '../services/apiClient';

// Types
interface DsrAssignment {
  id: string;
  dsr_id: string;
  dsr_name: string;
  dsr_phone: string;
  dsr_email: string;
  role: string;
  permissions: Record<string, any>;
  assigned_at: string;
  commission_rate: number | null;
  has_account: boolean;
}

interface PendingInvitation {
  id: string;
  dsr_phone: string;
  dsr_email: string;
  role: string;
  created_at: string;
  expires_at: string;
}

interface RemovedDsr {
  id: string;
  dsr_id: string;
  dsr_name: string;
  role: string;
  removed_at: string;
  removal_reason: string;
}

// State
const activeDsrs = ref<DsrAssignment[]>([]);
const pendingInvitations = ref<PendingInvitation[]>([]);
const removedDsrs = ref<RemovedDsr[]>([]);
const isLoading = ref(true);
const error = ref('');
const activeTab = ref<'active' | 'pending' | 'removed'>('active');

// Permission editor state
const editingDsr = ref<DsrAssignment | null>(null);
const showPermissionModal = ref(false);
const permissionLoading = ref(false);

// Remove confirmation state
const removingDsr = ref<DsrAssignment | null>(null);
const showRemoveModal = ref(false);
const removeReason = ref('');
const removeLoading = ref(false);

// Emits
const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

// Computed
const hasData = computed(() => 
  activeDsrs.value.length > 0 || 
  pendingInvitations.value.length > 0 || 
  removedDsrs.value.length > 0
);

// Methods
async function fetchData() {
  isLoading.value = true;
  error.value = '';

  try {
    // FIX snake/camel: apiClient auto-converts backend snake_case keys to
    // camelCase. Previously read `response.pending_invitations` which was
    // always undefined after conversion → Pending tab showed 0 even with
    // real pending invitations.
    const response = await apiClient.get<{
      active: DsrAssignment[];
      pendingInvitations: PendingInvitation[];
      removed: RemovedDsr[];
    }>('/dealer/dsr');

    activeDsrs.value = response.active || [];
    pendingInvitations.value = response.pendingInvitations || [];
    removedDsrs.value = response.removed || [];
  } catch (err: any) {
    // FIX error reporting: apiClient throws `ApiError` with shape
    // `{ status, message, data }`, NOT Axios's `{ response: { data } }`.
    // The previous code always fell through to the generic fallback.
    console.error('Failed to fetch DSR data:', err);
    const status = err?.status ?? err?.response?.status;
    const detail = err?.data?.detail ?? err?.response?.data?.detail;
    const msg = err?.message;
    error.value =
      detail ||
      msg ||
      (status ? `Failed to load DSR data (HTTP ${status})` : 'Failed to load DSR data');
  } finally {
    isLoading.value = false;
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric'
  });
}

function getRoleBadgeClass(role: string): string {
  switch (role) {
    case 'Manager':
      return 'bg-purple-100 text-purple-700';
    case 'Senior_DSR':
      return 'bg-blue-100 text-blue-700';
    case 'Order Collector':
      return 'bg-amber-100 text-amber-700';
    default:
      return 'bg-emerald-100 text-emerald-700';
  }
}

function formatRole(role: string): string {
  switch (role) {
    case 'Senior_DSR':
      return 'Senior DSR';
    case 'Order Collector':
      return 'Collector';
    default:
      return role;
  }
}

// Permission editing
function openPermissionEditor(dsr: DsrAssignment) {
  editingDsr.value = { ...dsr };
  showPermissionModal.value = true;
}

async function savePermissions() {
  if (!editingDsr.value) return;
  
  permissionLoading.value = true;
  
  try {
    await apiClient.put(`/dealer/dsr/assignments/${editingDsr.value.id}`, {
      permissions: editingDsr.value.permissions
    });
    
    // Update local data
    const index = activeDsrs.value.findIndex(d => d.id === editingDsr.value!.id);
    if (index >= 0) {
      activeDsrs.value[index] = { ...editingDsr.value };
    }
    
    showPermissionModal.value = false;
    editingDsr.value = null;
    emit('refresh');
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to update permissions';
  } finally {
    permissionLoading.value = false;
  }
}

// Remove DSR
function openRemoveModal(dsr: DsrAssignment) {
  removingDsr.value = dsr;
  removeReason.value = '';
  showRemoveModal.value = true;
}

async function confirmRemove() {
  if (!removingDsr.value) return;
  
  removeLoading.value = true;
  
  try {
    await apiClient.delete(`/dealer/dsr/assignments/${removingDsr.value.id}`, {
      data: { reason: removeReason.value || undefined }
    });
    
    await fetchData();
    showRemoveModal.value = false;
    removingDsr.value = null;
    emit('refresh');
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to remove DSR';
  } finally {
    removeLoading.value = false;
  }
}

// Revoke invitation
async function revokeInvitation(invitationId: string) {
  if (!confirm('Are you sure you want to revoke this invitation?')) return;
  
  try {
    await apiClient.delete(`/dealer/dsr/invitations/${invitationId}`);
    await fetchData();
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to revoke invitation';
  }
}

// Lifecycle
onMounted(() => {
  fetchData();
});

// FIX B-5: expose fetchData so the parent (App.vue) can call it directly
// after an invite is created. Previously the parent relied on a `@refresh`
// event from DsrManagementPanel, but that event was emitted only from
// savePermissions() — adding a new invite via AddRepModal called
// fetchFullDetails() which refreshed everything EXCEPT the DSR roster.
defineExpose({ fetchData });
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
    <!-- Header -->
    <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-purple-100 rounded-lg">
          <Users class="h-5 w-5 text-purple-600" />
        </div>
        <div>
          <h3 class="font-bold text-slate-800">DSR Management</h3>
          <p class="text-xs text-slate-500">
            {{ activeDsrs.length }} active · {{ pendingInvitations.length }} pending · {{ removedDsrs.length }} removed
          </p>
        </div>
      </div>
      <button
        @click="fetchData"
        :disabled="isLoading"
        class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg transition disabled:opacity-50"
      >
        <RefreshCw :class="['h-4 w-4', { 'animate-spin': isLoading }]" />
      </button>
    </div>

    <!-- Tab Navigation -->
    <div class="flex border-b border-slate-100">
      <button
        @click="activeTab = 'active'"
        :class="[
          'flex-1 px-4 py-3 text-sm font-medium transition',
          activeTab === 'active'
            ? 'text-purple-600 border-b-2 border-purple-600'
            : 'text-slate-500 hover:text-slate-700'
        ]"
      >
        Active ({{ activeDsrs.length }})
      </button>
      <button
        @click="activeTab = 'pending'"
        :class="[
          'flex-1 px-4 py-3 text-sm font-medium transition',
          activeTab === 'pending'
            ? 'text-amber-600 border-b-2 border-amber-600'
            : 'text-slate-500 hover:text-slate-700'
        ]"
      >
        Pending ({{ pendingInvitations.length }})
      </button>
      <button
        @click="activeTab = 'removed'"
        :class="[
          'flex-1 px-4 py-3 text-sm font-medium transition',
          activeTab === 'removed'
            ? 'text-slate-600 border-b-2 border-slate-600'
            : 'text-slate-500 hover:text-slate-700'
        ]"
      >
        Removed ({{ removedDsrs.length }})
      </button>
    </div>

    <!-- Error -->
    <div
      v-if="error"
      class="px-5 py-4 bg-rose-50 border-b border-rose-100 flex items-center gap-3"
    >
      <AlertCircle class="h-5 w-5 text-rose-600 shrink-0" />
      <p class="text-sm text-rose-700">{{ error }}</p>
      <button @click="error = ''" class="ml-auto text-rose-600 hover:text-rose-700">
        <XCircle class="h-4 w-4" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="px-5 py-12 text-center">
      <RefreshCw class="h-8 w-8 text-purple-600 animate-spin mx-auto mb-3" />
      <p class="text-sm text-slate-500">Loading DSR data...</p>
    </div>

    <!-- Empty States -->
    <div
      v-else-if="!hasData"
      class="px-5 py-12 text-center"
    >
      <Users class="h-12 w-12 text-slate-300 mx-auto mb-3" />
      <p class="text-slate-500 font-medium">No DSRs found</p>
      <p class="text-xs text-slate-400 mt-1">
        Invite DSRs to join your team
      </p>
    </div>

    <!-- Active DSRs -->
    <div v-else-if="activeTab === 'active' && activeDsrs.length > 0" class="divide-y divide-slate-100">
      <div
        v-for="dsr in activeDsrs"
        :key="dsr.id"
        class="px-5 py-4 hover:bg-slate-50 transition"
      >
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center text-white font-semibold">
              {{ dsr.dsr_name.split(' ').map((n: string) => n[0]).join('').slice(0, 2) }}
            </div>
            <div>
              <p class="font-semibold text-slate-800">{{ dsr.dsr_name }}</p>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['px-2 py-0.5 text-xs font-medium rounded-full', getRoleBadgeClass(dsr.role)]">
                  {{ formatRole(dsr.role) }}
                </span>
                <span v-if="dsr.has_account" class="text-xs text-emerald-600 flex items-center gap-1">
                  <CheckCircle class="h-3 w-3" />
                  Registered
                </span>
                <span v-else class="text-xs text-slate-400">Not registered</span>
              </div>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              @click="openPermissionEditor(dsr)"
              class="p-2 text-slate-400 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition"
              title="Edit permissions"
            >
              <Shield class="h-4 w-4" />
            </button>
            <button
              @click="openRemoveModal(dsr)"
              class="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
              title="Remove DSR"
            >
              <UserX class="h-4 w-4" />
            </button>
          </div>
        </div>
        <div class="mt-2 text-xs text-slate-500 flex items-center gap-4">
          <span>{{ dsr.dsr_phone }}</span>
          <span v-if="dsr.dsr_email">{{ dsr.dsr_email }}</span>
          <span>Since {{ formatDate(dsr.assigned_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Pending Invitations -->
    <div v-else-if="activeTab === 'pending' && pendingInvitations.length > 0" class="divide-y divide-slate-100">
      <div
        v-for="inv in pendingInvitations"
        :key="inv.id"
        class="px-5 py-4 hover:bg-slate-50 transition"
      >
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
              <Clock class="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <!-- FIX M-12: render dsr_email as the primary label since
              dsr_phone is optional (the invitation flow allows email-only
              invites). Falls back to phone if email is somehow empty. -->
              <p class="font-semibold text-slate-800">{{ inv.dsr_email || inv.dsr_phone || 'Unknown' }}</p>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['px-2 py-0.5 text-xs font-medium rounded-full', getRoleBadgeClass(inv.role)]">
                  {{ formatRole(inv.role) }}
                </span>
                <span class="text-xs text-amber-600">
                  Expires {{ formatDate(inv.expires_at) }}
                </span>
              </div>
            </div>
          </div>
          <button
            @click="revokeInvitation(inv.id)"
            class="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
            title="Revoke invitation"
          >
            <XCircle class="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>

    <!-- Removed DSRs -->
    <div v-else-if="activeTab === 'removed' && removedDsrs.length > 0" class="divide-y divide-slate-100">
      <div
        v-for="dsr in removedDsrs"
        :key="dsr.id"
        class="px-5 py-4 bg-slate-50"
      >
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500">
            <UserX class="h-5 w-5" />
          </div>
          <div>
            <p class="font-semibold text-slate-600">
              {{ dsr.dsr_name }}
              <span class="text-xs text-slate-400 font-normal">(No longer active)</span>
            </p>
            <div class="flex items-center gap-2 mt-1">
              <span :class="['px-2 py-0.5 text-xs font-medium rounded-full', getRoleBadgeClass(dsr.role)]">
                {{ formatRole(dsr.role) }}
              </span>
              <span class="text-xs text-slate-500">
                Removed {{ formatDate(dsr.removed_at) }}
              </span>
            </div>
            <p v-if="dsr.removal_reason" class="text-xs text-slate-400 mt-1">
              Reason: {{ dsr.removal_reason }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty tab state -->
    <div
      v-else-if="!isLoading"
      class="px-5 py-12 text-center"
    >
      <Users class="h-10 w-10 text-slate-300 mx-auto mb-3" />
      <p class="text-slate-500 font-medium">
        No {{ activeTab }} DSRs
      </p>
    </div>

    <!-- Permission Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showPermissionModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          @click.self="showPermissionModal = false"
        >
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" @click.stop>
            <div class="px-6 py-4 bg-slate-50 border-b border-slate-100">
              <h3 class="font-bold text-slate-800">Edit Permissions</h3>
              <p class="text-sm text-slate-500">{{ editingDsr?.dsr_name }}</p>
            </div>
            <div class="p-6 space-y-4">
              <!-- Permission toggles would go here -->
              <p class="text-sm text-slate-500 text-center">
                Permission editor coming soon. Use role-based permissions for now.
              </p>
            </div>
            <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
              <button
                @click="showPermissionModal = false"
                class="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                @click="savePermissions"
                :disabled="permissionLoading"
                class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 disabled:opacity-50"
              >
                {{ permissionLoading ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Remove Confirmation Modal -->
    <Teleport to="body">
      <Transition name="fade">
        <div
          v-if="showRemoveModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          @click.self="showRemoveModal = false"
        >
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" @click.stop>
            <div class="px-6 py-4 bg-rose-50 border-b border-rose-100">
              <h3 class="font-bold text-rose-800">Remove DSR</h3>
              <p class="text-sm text-rose-600">Are you sure you want to remove {{ removingDsr?.dsr_name }}?</p>
            </div>
            <div class="p-6 space-y-4">
              <p class="text-sm text-slate-600">
                This will remove the DSR from your team. Their transaction records will be preserved with their name.
              </p>
              <div class="space-y-2">
                <label class="text-sm font-medium text-slate-700">Reason (optional)</label>
                <textarea
                  v-model="removeReason"
                  placeholder="Enter reason for removal..."
                  rows="2"
                  class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-rose-500 bg-white text-slate-800 resize-none"
                />
              </div>
            </div>
            <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
              <button
                @click="showRemoveModal = false"
                class="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                @click="confirmRemove"
                :disabled="removeLoading"
                class="px-4 py-2 bg-rose-600 text-white rounded-lg text-sm font-medium hover:bg-rose-700 disabled:opacity-50"
              >
                {{ removeLoading ? 'Removing...' : 'Remove DSR' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
