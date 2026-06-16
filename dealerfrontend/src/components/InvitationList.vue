<script setup lang="ts">
/**
 * InvitationList — Dealer-side invitation management.
 *
 * FIX: previously used `useInvitations` composable which called
 * `/invitations/list` on the LEGACY `DsrInvitationController`. That
 * controller used `IsAuthenticated` (Django session auth) which never
 * runs in this JWT-only system, so the endpoint always returned 403.
 * As a result the Reports → Invitations toggle showed nothing.
 *
 * This rewrite uses the WORKING endpoint `/dealer/dsr` which returns:
 *   { active, pendingInvitations, removed }
 * mapped to the same UI. Invite-URL copy is disabled because tokens
 * are not exposed by this endpoint (would require a backend enhancement
 * to expose `/dealer/dsr/invitations` with full token data).
 */

import { ref, onMounted, computed } from 'vue';
import {
  Mail,
  Clock,
  CheckCircle,
  XCircle,
  Trash2,
  Copy,
  RefreshCw,
  AlertCircle,
  Filter,
  UserCheck,
  UserX,
} from 'lucide-vue-next';
import apiClient from '../services/apiClient';

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

// ─── State ───────────────────────────────────────────────────────────────────

interface ActiveRow {
  id: string;
  dsrId: string;
  dsrName: string;
  dsrPhone: string;
  dsrEmail: string;
  role: string;
  assignedAt: string;
  hasAccount: boolean;
}

interface PendingRow {
  id: string;
  dsrEmail: string;
  dsrPhone: string;
  role: string;
  createdAt: string;
  expiresAt: string;
}

interface RemovedRow {
  id: string;
  dsrId: string;
  dsrName: string;
  role: string;
  removedAt: string;
  removalReason: string;
}

type StatusFilter = 'all' | 'pending' | 'accepted' | 'expired' | 'revoked';

const activeDsrs = ref<ActiveRow[]>([]);
const pendingInvitations = ref<PendingRow[]>([]);
const removedDsrs = ref<RemovedRow[]>([]);
const isLoading = ref(false);
const error = ref<string | null>(null);
const selectedStatus = ref<StatusFilter>('all');
const showFilters = ref(false);

// ─── Computed ──────────────────────────────────────────────────────────────────

// Combine all rows into a single tagged list for the UI. The backend
// returns 3 buckets; we present them in a single table with a status
// column. `active` rows are tagged "accepted" (they joined), `pending`
// rows are "pending", `removed` are "revoked" (dealer removed them).
const allRows = computed(() => {
  const out: Array<{
    id: string;
    email: string;
    phone: string;
    role: string;
    status: StatusFilter;
    createdAt: string;
    extra?: string;
  }> = [];

  for (const a of activeDsrs.value) {
    out.push({
      id: `accepted-${a.dsrId}`,
      email: a.dsrEmail,
      phone: a.dsrPhone,
      role: a.role,
      status: 'accepted',
      createdAt: a.assignedAt,
    });
  }
  for (const p of pendingInvitations.value) {
    out.push({
      id: `pending-${p.id}`,
      email: p.dsrEmail,
      phone: p.dsrPhone,
      role: p.role,
      status: 'pending',
      createdAt: p.createdAt,
      extra: p.expiresAt,
    });
  }
  for (const r of removedDsrs.value) {
    out.push({
      id: `removed-${r.id}`,
      email: '',
      phone: '',
      role: r.role,
      status: 'revoked',
      createdAt: r.removedAt,
      extra: r.removalReason,
    });
  }

  return out.sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
});

const statusCounts = computed(() => {
  const counts: Record<StatusFilter, number> = {
    all: allRows.value.length,
    pending: 0,
    accepted: 0,
    expired: 0,
    revoked: 0,
  };
  for (const r of allRows.value) {
    counts[r.status]++;
  }
  return counts;
});

const filteredRows = computed(() => {
  if (selectedStatus.value === 'all') return allRows.value;
  return allRows.value.filter((r) => r.status === selectedStatus.value);
});

// ─── Methods ───────────────────────────────────────────────────────────────────

async function fetchData() {
  isLoading.value = true;
  error.value = null;

  try {
    // FIX: use /dealer/dsr (the working, dealer-scoped endpoint) instead
    // of /invitations/list (the legacy broken endpoint).
    const response = await apiClient.get<{
      active: ActiveRow[];
      pendingInvitations: PendingRow[];
      removed: RemovedRow[];
    }>('/dealer/dsr');

    activeDsrs.value = response.data.active || [];
    pendingInvitations.value = response.data.pendingInvitations || [];
    removedDsrs.value = response.data.removed || [];
  } catch (err: any) {
    console.error('Failed to fetch invitation data:', err);
    error.value = err?.data?.detail || err?.message || 'Failed to load invitations';
  } finally {
    isLoading.value = false;
  }
}

async function revokeInvitation(row: any) {
  if (!row.id.startsWith('pending-')) return;
  const invitationId = row.id.replace('pending-', '');
  if (!confirm(`Revoke invitation to ${row.email}?`)) return;

  try {
    await apiClient.delete(`/dealer/dsr/invitations/${invitationId}`);
    await fetchData();
    emit('refresh');
  } catch (err: any) {
    error.value = err?.data?.detail || 'Failed to revoke invitation';
  }
}

async function removeDsr(row: any) {
  if (!row.id.startsWith('accepted-')) return;
  const dsrId = row.id.replace('accepted-', '');
  if (!confirm(`Remove ${row.email || row.phone} from your team?`)) return;

  try {
    await apiClient.delete(`/dealer/dsr/assignments/${dsrId}`, {
      data: { reason: 'Removed via Reports → Invitations' },
    });
    await fetchData();
    emit('refresh');
  } catch (err: any) {
    error.value = err?.data?.detail || 'Failed to remove DSR';
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function getStatusColor(status: StatusFilter): string {
  switch (status) {
    case 'pending':
      return 'bg-amber-100 text-amber-700 border-amber-200';
    case 'accepted':
      return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    case 'expired':
      return 'bg-slate-100 text-slate-600 border-slate-200';
    case 'revoked':
      return 'bg-rose-100 text-rose-700 border-rose-200';
    default:
      return 'bg-slate-100 text-slate-600 border-slate-200';
  }
}

function getStatusIcon(status: StatusFilter) {
  switch (status) {
    case 'pending':
      return Clock;
    case 'accepted':
      return CheckCircle;
    case 'expired':
      return AlertCircle;
    case 'revoked':
      return XCircle;
    default:
      return Clock;
  }
}

function formatRole(role: string): string {
  switch (role) {
    case 'Senior_DSR':
      return 'Senior DSR';
    case 'Order Collector':
      return 'Order Collector';
    default:
      return role || 'DSR';
  }
}

onMounted(fetchData);
</script>

<template>
  <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
    <!-- Header -->
    <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="p-2 bg-violet-100 rounded-lg">
          <Mail class="h-5 w-5 text-violet-600" />
        </div>
        <div>
          <h3 class="font-bold text-slate-800">Team Invitations</h3>
          <p class="text-xs text-slate-500">
            {{ pendingInvitations.length }} pending · {{ activeDsrs.length }} accepted
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="showFilters = !showFilters"
          :class="[
            'p-2 rounded-lg transition cursor-pointer',
            showFilters ? 'bg-violet-100 text-violet-600' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50',
          ]"
        >
          <Filter class="h-4 w-4" />
        </button>
        <button
          @click="fetchData"
          :disabled="isLoading"
          class="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-lg transition cursor-pointer disabled:opacity-50"
        >
          <RefreshCw :class="['h-4 w-4', { 'animate-spin': isLoading }]" />
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div v-if="showFilters" class="px-5 py-3 bg-slate-50 border-b border-slate-100">
      <div class="flex flex-wrap gap-2">
        <button
          v-for="(count, status) in statusCounts"
          :key="status"
          @click="selectedStatus = status as StatusFilter"
          :class="[
            'px-3 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer',
            selectedStatus === status
              ? 'bg-violet-600 text-white'
              : 'bg-white text-slate-600 border border-slate-200 hover:border-violet-300',
          ]"
        >
          {{ status.charAt(0).toUpperCase() + status.slice(1) }} ({{ count }})
        </button>
      </div>
    </div>

    <!-- Error -->
    <div
      v-if="error"
      class="px-5 py-4 bg-rose-50 border-b border-rose-100 flex items-center gap-3"
    >
      <AlertCircle class="h-5 w-5 text-rose-600 shrink-0" />
      <p class="text-sm text-rose-700">{{ error }}</p>
    </div>

    <!-- Empty State -->
    <div
      v-if="!isLoading && filteredRows.length === 0"
      class="px-5 py-12 text-center"
    >
      <Mail class="h-12 w-12 text-slate-300 mx-auto mb-3" />
      <p class="text-slate-500 font-medium">No invitations found</p>
      <p class="text-xs text-slate-400 mt-1">
        {{ selectedStatus === 'all' ? 'Invite team members from the Team tab to get started' : `No ${selectedStatus} invitations` }}
      </p>
    </div>

    <!-- List -->
    <div v-else class="divide-y divide-slate-100">
      <div
        v-for="row in filteredRows"
        :key="row.id"
        class="px-5 py-4 hover:bg-slate-50 transition"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-start gap-3 min-w-0">
            <div :class="['p-2 rounded-lg shrink-0', getStatusColor(row.status)]">
              <component :is="getStatusIcon(row.status)" class="h-4 w-4" />
            </div>

            <div class="min-w-0">
              <p class="text-sm font-semibold text-slate-800 truncate">
                {{ row.email || row.phone || 'Unknown recipient' }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-xs text-slate-500">
                  {{ formatRole(row.role) }}
                </span>
                <span class="text-slate-300">·</span>
                <span class="text-xs text-slate-500">
                  {{ formatDate(row.createdAt) }}
                </span>
              </div>
              <p v-if="row.extra" class="text-xs text-slate-500 mt-1">
                <span v-if="row.status === 'pending'">Expires: {{ formatDate(row.extra) }}</span>
                <span v-else>Reason: {{ row.extra }}</span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-2 shrink-0">
            <span
              :class="[
                'px-2.5 py-1 text-xs font-semibold rounded-full border',
                getStatusColor(row.status),
              ]"
            >
              {{ row.status }}
            </span>

            <div class="flex items-center gap-1">
              <!-- Revoke (pending only) -->
              <button
                v-if="row.status === 'pending'"
                @click="revokeInvitation(row)"
                class="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition cursor-pointer"
                title="Revoke invitation"
              >
                <UserX class="h-4 w-4" />
              </button>

              <!-- Remove (accepted only) -->
              <button
                v-if="row.status === 'accepted'"
                @click="removeDsr(row)"
                class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                title="Remove from team"
              >
                <Trash2 class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="isLoading" class="px-5 py-8 text-center">
      <RefreshCw class="h-6 w-6 text-violet-600 animate-spin mx-auto" />
      <p class="text-sm text-slate-500 mt-2">Loading invitations...</p>
    </div>

    <!-- Info banner about copy-link limitation -->
    <div class="px-5 py-3 bg-slate-50 border-t border-slate-100 text-xs text-slate-500">
      <strong>Note:</strong> Pending invitations cannot be copy-shared from
      this view — the backend does not currently expose invitation tokens
      in the list endpoint. The original invite URL is delivered by email
      when the invitation is created. Re-create the invitation if it was lost.
    </div>
  </div>
</template>
