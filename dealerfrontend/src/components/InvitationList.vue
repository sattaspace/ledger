<script setup lang="ts">
/**
 * InvitationList — Component to display and manage pending/accepted invitations.
 *
 * Features:
 * - List all invitations with status indicators
 * - Filter by status
 * - Revoke pending invitations
 * - Delete invitations
 * - Show invite URL for sharing
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
  ChevronDown,
  Filter,
  UserCheck,
  UserX
} from 'lucide-vue-next';
import { useInvitations } from '../composables/useInvitations';
import type { DsrInvitation } from '../types';

// ─── Props & Emits ─────────────────────────────────────────────────────────────

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();

// ─── Composables ───────────────────────────────────────────────────────────────

const {
  invitations,
  pendingInvitations,
  acceptedInvitations,
  isLoading,
  error,
  fetchInvitations,
  revokeInvitation,
  deleteInvitation,
} = useInvitations();

// ─── State ─────────────────────────────────────────────────────────────────────

const selectedStatus = ref<'all' | 'pending' | 'accepted' | 'expired' | 'revoked'>('all');
const showFilters = ref(false);
const copiedId = ref<string | null>(null);

// ─── Computed ──────────────────────────────────────────────────────────────────

const filteredInvitations = computed(() => {
  if (selectedStatus.value === 'all') return invitations.value;
  return invitations.value.filter((inv) => inv.status === selectedStatus.value);
});

const statusCounts = computed(() => ({
  all: invitations.value.length,
  pending: pendingInvitations.value.length,
  accepted: acceptedInvitations.value.length,
  expired: invitations.value.filter((inv) => inv.status === 'expired').length,
  revoked: invitations.value.filter((inv) => inv.status === 'revoked').length,
}));

// ─── Methods ───────────────────────────────────────────────────────────────────

onMounted(() => {
  fetchInvitations();
});

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getStatusColor(status: string): string {
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

function getStatusIcon(status: string) {
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

async function handleRevoke(invitation: DsrInvitation) {
  if (!confirm(`Revoke invitation to ${invitation.email}?`)) return;
  await revokeInvitation(invitation.id);
  emit('refresh');
}

async function handleDelete(invitation: DsrInvitation) {
  if (!confirm(`Delete invitation to ${invitation.email}?`)) return;
  await deleteInvitation(invitation.id);
  emit('refresh');
}

async function copyInviteUrl(invitation: DsrInvitation) {
  if (!invitation.inviteUrl) return;
  
  try {
    await navigator.clipboard.writeText(invitation.inviteUrl);
    copiedId.value = invitation.id;
    setTimeout(() => {
      copiedId.value = null;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}

function handleRefresh() {
  fetchInvitations();
  emit('refresh');
}
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
            {{ pendingInvitations.length }} pending · {{ acceptedInvitations.length }} accepted
          </p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="showFilters = !showFilters"
          :class="[
            'p-2 rounded-lg transition cursor-pointer',
            showFilters ? 'bg-violet-100 text-violet-600' : 'text-slate-400 hover:text-slate-600 hover:bg-slate-50'
          ]"
        >
          <Filter class="h-4 w-4" />
        </button>
        <button
          @click="handleRefresh"
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
          @click="selectedStatus = status as any"
          :class="[
            'px-3 py-1.5 text-xs font-semibold rounded-lg transition cursor-pointer',
            selectedStatus === status
              ? 'bg-violet-600 text-white'
              : 'bg-white text-slate-600 border border-slate-200 hover:border-violet-300'
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
      v-if="!isLoading && filteredInvitations.length === 0"
      class="px-5 py-12 text-center"
    >
      <Mail class="h-12 w-12 text-slate-300 mx-auto mb-3" />
      <p class="text-slate-500 font-medium">No invitations found</p>
      <p class="text-xs text-slate-400 mt-1">
        {{ selectedStatus === 'all' ? 'Invite team members to get started' : `No ${selectedStatus} invitations` }}
      </p>
    </div>

    <!-- List -->
    <div v-else class="divide-y divide-slate-100">
      <div
        v-for="invitation in filteredInvitations"
        :key="invitation.id"
        class="px-5 py-4 hover:bg-slate-50 transition"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-start gap-3 min-w-0">
            <!-- Status Icon -->
            <div :class="['p-2 rounded-lg shrink-0', getStatusColor(invitation.status)]">
              <component :is="getStatusIcon(invitation.status)" class="h-4 w-4" />
            </div>

            <!-- Details -->
            <div class="min-w-0">
              <p class="text-sm font-semibold text-slate-800 truncate">
                {{ invitation.email }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-xs text-slate-500">
                  {{ invitation.role === 'DSR' ? 'DSR Rep' : 'Order Collector' }}
                </span>
                <span class="text-slate-300">·</span>
                <span class="text-xs text-slate-500">
                  {{ formatDate(invitation.createdAt) }}
                </span>
              </div>
              <p v-if="invitation.parentDsrName" class="text-xs text-slate-500 mt-1">
                Reports to: {{ invitation.parentDsrName }}
              </p>
            </div>
          </div>

          <!-- Status & Actions -->
          <div class="flex items-center gap-2 shrink-0">
            <!-- Status Badge -->
            <span
              :class="[
                'px-2.5 py-1 text-xs font-semibold rounded-full border',
                getStatusColor(invitation.status)
              ]"
            >
              {{ invitation.status }}
            </span>

            <!-- Actions -->
            <div class="flex items-center gap-1">
              <!-- Copy Invite URL -->
              <button
                v-if="invitation.status === 'pending' && invitation.inviteUrl"
                @click="copyInviteUrl(invitation)"
                class="p-1.5 text-slate-400 hover:text-violet-600 hover:bg-violet-50 rounded-lg transition cursor-pointer"
                title="Copy invite link"
              >
                <Copy :class="['h-4 w-4', { 'text-emerald-600': copiedId === invitation.id }]" />
              </button>

              <!-- Revoke -->
              <button
                v-if="invitation.status === 'pending'"
                @click="handleRevoke(invitation)"
                class="p-1.5 text-slate-400 hover:text-amber-600 hover:bg-amber-50 rounded-lg transition cursor-pointer"
                title="Revoke invitation"
              >
                <UserX class="h-4 w-4" />
              </button>

              <!-- Delete -->
              <button
                @click="handleDelete(invitation)"
                class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                title="Delete invitation"
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
  </div>
</template>
