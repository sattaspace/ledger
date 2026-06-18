<script setup lang="ts">
/**
 * DsrManagementPanel — Component for dealers to manage their DSRs.
 *
 * Features:
 * - View active DSRs with roles and permissions
 * - View pending invitations
 * - View removed/left DSRs
 * - Update DSR permissions (FIX DSR-012: full permission editor)
 * - Update DSR role and commission rate
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
  ChevronDown,
  RotateCcw
} from 'lucide-vue-next';
import apiClient from '../services/apiClient';

// Types
interface DsrAssignment {
  id: string;
  dsrId: string;
  dsrName: string;
  dsrPhone: string;
  dsrEmail: string;
  role: string;
  permissions: Record<string, any>;
  assignedAt: string;
  commissionRate: number | null;
  hasAccount: boolean;
}

interface PendingInvitation {
  id: string;
  dsrPhone: string;
  dsrEmail: string;
  role: string;
  createdAt: string;
  expiresAt: string;
}

interface RemovedDsr {
  id: string;
  dsrId: string;
  dsrName: string;
  role: string;
  removedAt: string;
  removalReason: string;
}

// ─── Permission Editor Configuration ────────────────────────────────────
// FIX DSR-012: Full permission editor replacing "coming soon" placeholder.
// The backend permissions JSON has this structure:
//   { "dashboard": {"view": true}, "inventory": {"view": true, "edit": false, "delete": false}, ... }

interface PermissionModule {
  key: string;
  label: string;
  icon: string;
  actions: { key: string; label: string }[];
}

const PERMISSION_MODULES: PermissionModule[] = [
  {
    key: 'dashboard',
    label: 'Dashboard',
    icon: '📊',
    actions: [{ key: 'view', label: 'View' }],
  },
  {
    key: 'inventory',
    label: 'Inventory',
    icon: '📦',
    actions: [
      { key: 'view', label: 'View' },
      { key: 'edit', label: 'Edit' },
      { key: 'delete', label: 'Delete' },
    ],
  },
  {
    key: 'sales',
    label: 'Sales',
    icon: '🧾',
    actions: [
      { key: 'view', label: 'View' },
      { key: 'edit', label: 'Create/Edit' },
      { key: 'delete', label: 'Void/Delete' },
    ],
  },
  {
    key: 'collections',
    label: 'Collections',
    icon: '💰',
    actions: [
      { key: 'view', label: 'View' },
      { key: 'edit', label: 'Record Payments' },
    ],
  },
  {
    key: 'suppliers',
    label: 'Suppliers',
    icon: '🏪',
    actions: [
      { key: 'view', label: 'View' },
      { key: 'edit', label: 'Edit' },
    ],
  },
  {
    key: 'reports',
    label: 'Reports',
    icon: '📈',
    actions: [
      { key: 'view', label: 'View' },
      { key: 'export', label: 'Export' },
    ],
  },
];

const SIMPLE_PERMISSIONS = [
  { key: 'print', label: 'Print Receipts/Invoices', icon: '🖨️' },
  { key: 'manage_dsrs', label: 'Manage Team Members', icon: '👥' },
];

const ROLE_OPTIONS = [
  { value: 'DSR', label: 'DSR' },
  { value: 'Senior_DSR', label: 'Senior DSR' },
  { value: 'Manager', label: 'Manager' },
  { value: 'Collector', label: 'Order Collector' },
];

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
const editedPermissions = ref<Record<string, any>>({});
const editedRole = ref('');
const editedCommissionRate = ref<number | null>(null);

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
    const response = await apiClient.get<{
      active: DsrAssignment[];
      pendingInvitations: PendingInvitation[];
      removed: RemovedDsr[];
    }>('/dealer/dsr');

    activeDsrs.value = response.data.active || [];
    pendingInvitations.value = response.data.pendingInvitations || [];
    removedDsrs.value = response.data.removed || [];
  } catch (err: any) {
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
    case 'Collector':
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

// ─── Permission Editing ───────────────────────────────────────────────

function openPermissionEditor(dsr: DsrAssignment) {
  editingDsr.value = { ...dsr };
  // Deep-clone the permissions so edits don't mutate the source
  editedPermissions.value = JSON.parse(JSON.stringify(dsr.permissions || {}));
  editedRole.value = dsr.role;
  editedCommissionRate.value = dsr.commissionRate;
  showPermissionModal.value = true;
}

function getPermAction(moduleKey: string, actionKey: string): boolean {
  const mod = editedPermissions.value[moduleKey];
  if (mod === undefined || mod === null) return false;
  if (typeof mod === 'boolean') return mod;
  return !!mod[actionKey];
}

function setPermAction(moduleKey: string, actionKey: string, value: boolean) {
  if (!editedPermissions.value[moduleKey] || typeof editedPermissions.value[moduleKey] === 'boolean') {
    editedPermissions.value[moduleKey] = {};
  }
  editedPermissions.value[moduleKey][actionKey] = value;
}

function getSimplePerm(key: string): boolean {
  return !!editedPermissions.value[key];
}

function setSimplePerm(key: string, value: boolean) {
  editedPermissions.value[key] = value;
}

function resetToRoleDefaults() {
  // Clear edited permissions; sending `permissions: null` tells the backend
  // to regenerate from DEFAULT_PERMISSIONS for the current role
  editedPermissions.value = {};
}

async function savePermissions() {
  if (!editingDsr.value) return;
  
  permissionLoading.value = true;
  
  try {
    const payload: Record<string, any> = {
      permissions: Object.keys(editedPermissions.value).length > 0
        ? editedPermissions.value
        : null,
    };
    
    // Include role and commission if changed
    if (editedRole.value !== editingDsr.value.role) {
      payload.role = editedRole.value;
    }
    if (editedCommissionRate.value !== editingDsr.value.commissionRate) {
      payload.commissionRate = editedCommissionRate.value;
    }
    
    await apiClient.put(`/dealer/dsr/assignments/${editingDsr.value.id}`, payload);
    
    // Update local data
    const index = activeDsrs.value.findIndex(d => d.id === editingDsr.value!.id);
    if (index >= 0) {
      activeDsrs.value[index] = {
        ...editingDsr.value,
        permissions: Object.keys(editedPermissions.value).length > 0
          ? { ...editedPermissions.value }
          : editingDsr.value.permissions,
        role: editedRole.value,
        commissionRate: editedCommissionRate.value,
      };
    }
    
    showPermissionModal.value = false;
    editingDsr.value = null;
    emit('refresh');
  } catch (err: any) {
    const detail = err?.data?.detail || err?.message;
    error.value = detail || 'Failed to update permissions';
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
    const detail = err?.data?.detail || err?.message;
    error.value = detail || 'Failed to remove DSR';
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
    const detail = err?.data?.detail || err?.message;
    error.value = detail || 'Failed to revoke invitation';
  }
}

// Lifecycle
onMounted(() => {
  fetchData();
});

// expose fetchData so the parent (App.vue) can call it directly
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
              {{ (dsr.dsrName || '?').split(' ').map((n: string) => n[0] || '').join('').slice(0, 2).toUpperCase() }}
            </div>
            <div>
              <p class="font-semibold text-slate-800">{{ dsr.dsrName || 'Unnamed' }}</p>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['px-2 py-0.5 text-xs font-medium rounded-full', getRoleBadgeClass(dsr.role)]">
                  {{ formatRole(dsr.role) }}
                </span>
                <span v-if="dsr.hasAccount" class="text-xs text-emerald-600 flex items-center gap-1">
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
              title="Edit permissions & role"
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
          <span>{{ dsr.dsrPhone }}</span>
          <span v-if="dsr.dsrEmail">{{ dsr.dsrEmail }}</span>
          <span>Since {{ formatDate(dsr.assignedAt) }}</span>
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
              <p class="font-semibold text-slate-800">{{ inv.dsrEmail || inv.dsrPhone || 'Unknown' }}</p>
              <div class="flex items-center gap-2 mt-1">
                <span :class="['px-2 py-0.5 text-xs font-medium rounded-full', getRoleBadgeClass(inv.role)]">
                  {{ formatRole(inv.role) }}
                </span>
                <span class="text-xs text-amber-600">
                  Expires {{ formatDate(inv.expiresAt) }}
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
              {{ dsr.dsrName || 'Unnamed' }}
              <span class="text-xs text-slate-400 font-normal">(No longer active)</span>
            </p>
            <div class="flex items-center gap-2 mt-1">
              <span :class="['px-2 py-0.5 text-xs font-medium rounded-full', getRoleBadgeClass(dsr.role)]">
                {{ formatRole(dsr.role) }}
              </span>
              <span class="text-xs text-slate-500">
                Removed {{ formatDate(dsr.removedAt) }}
              </span>
            </div>
            <p v-if="dsr.removalReason" class="text-xs text-slate-400 mt-1">
              Reason: {{ dsr.removalReason }}
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

    <!-- ═══════════════════════════════════════════════════════════════════
         FIX DSR-012: PERMISSION EDITOR MODAL
         Full permission editor with:
         - Role selector
         - Per-module, per-action toggle switches
         - Simple boolean permission toggles
         - Commission rate input
         - "Reset to role defaults" button
    ═══════════════════════════════════════════════════════════════════ -->
    <!-- Hydration fix H-1: move v-if from inside <Transition> to the
         <Teleport> itself. When the modal is closed (showPermissionModal
         is false), the entire <Teleport> block is skipped during SSR —
         no placeholder, no hydration mismatch. The `appear` attribute
         on <Transition> ensures the fade-in animation plays when the
         modal is opened client-side. -->
    <Teleport v-if="showPermissionModal" to="body">
      <Transition name="fade" appear>
        <div
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          @click.self="showPermissionModal = false"
        >
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col" @click.stop>
            <!-- Header -->
            <div class="px-6 py-4 bg-slate-50 border-b border-slate-100 shrink-0">
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="font-bold text-slate-800">Edit Permissions & Role</h3>
                  <p class="text-sm text-slate-500">{{ editingDsr?.dsrName || 'Unnamed' }}</p>
                </div>
                <button
                  @click="showPermissionModal = false"
                  class="p-1 text-slate-400 hover:text-slate-600 rounded"
                >
                  <XCircle class="h-5 w-5" />
                </button>
              </div>
            </div>

            <!-- Scrollable content -->
            <div class="overflow-y-auto flex-1 p-6 space-y-6">
              <!-- Role Selector -->
              <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Role</label>
                <select
                  v-model="editedRole"
                  class="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
                >
                  <option v-for="opt in ROLE_OPTIONS" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
                <p class="text-xs text-slate-400 mt-1">
                  Changing role will update the default permissions on save.
                </p>
              </div>

              <!-- Commission Rate -->
              <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Commission Rate (%)</label>
                <input
                  v-model.number="editedCommissionRate"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  placeholder="e.g. 5.0"
                  class="w-full px-3 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <!-- Reset to defaults -->
              <div class="flex items-center justify-between">
                <span class="text-sm font-semibold text-slate-700">Module Permissions</span>
                <button
                  @click="resetToRoleDefaults"
                  class="flex items-center gap-1.5 text-xs text-purple-600 hover:text-purple-700 font-medium"
                  title="Reset all permissions to the defaults for this role"
                >
                  <RotateCcw class="h-3.5 w-3.5" />
                  Reset to role defaults
                </button>
              </div>

              <!-- Module permission grids -->
              <div class="space-y-3">
                <div
                  v-for="module in PERMISSION_MODULES"
                  :key="module.key"
                  class="border border-slate-100 rounded-lg overflow-hidden"
                >
                  <!-- Module header -->
                  <div class="px-4 py-2.5 bg-slate-50 flex items-center gap-2">
                    <span class="text-base">{{ module.icon }}</span>
                    <span class="text-sm font-medium text-slate-700">{{ module.label }}</span>
                  </div>
                  <!-- Action toggles -->
                  <div class="px-4 py-3 flex flex-wrap gap-3">
                    <label
                      v-for="action in module.actions"
                      :key="action.key"
                      class="flex items-center gap-2 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        :checked="getPermAction(module.key, action.key)"
                        @change="setPermAction(module.key, action.key, ($event.target as HTMLInputElement).checked)"
                        class="w-4 h-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                      />
                      <span class="text-sm text-slate-600">{{ action.label }}</span>
                    </label>
                  </div>
                </div>
              </div>

              <!-- Simple boolean permissions -->
              <div class="space-y-2">
                <label
                  v-for="perm in SIMPLE_PERMISSIONS"
                  :key="perm.key"
                  class="flex items-center gap-3 p-3 border border-slate-100 rounded-lg cursor-pointer hover:bg-slate-50 transition"
                >
                  <input
                    type="checkbox"
                    :checked="getSimplePerm(perm.key)"
                    @change="setSimplePerm(perm.key, ($event.target as HTMLInputElement).checked)"
                    class="w-4 h-4 rounded border-slate-300 text-purple-600 focus:ring-purple-500"
                  />
                  <span class="text-base">{{ perm.icon }}</span>
                  <span class="text-sm text-slate-700">{{ perm.label }}</span>
                </label>
              </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 border-t border-slate-100 flex justify-end gap-3 shrink-0">
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
                {{ permissionLoading ? 'Saving...' : 'Save Changes' }}
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Remove Confirmation Modal -->
    <!-- Hydration fix H-1: same pattern as above — v-if on <Teleport>. -->
    <Teleport v-if="showRemoveModal" to="body">
      <Transition name="fade" appear>
        <div
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
          @click.self="showRemoveModal = false"
        >
          <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden" @click.stop>
            <div class="px-6 py-4 bg-rose-50 border-b border-rose-100">
              <h3 class="font-bold text-rose-800">Remove DSR</h3>
              <p class="text-sm text-rose-600">Are you sure you want to remove {{ removingDsr?.dsrName || 'Unnamed' }}?</p>
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
