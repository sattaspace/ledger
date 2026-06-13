<script setup lang="ts">
/**
 * AddRepModal — Unified modal for inviting/adding sales representatives.
 *
 * New Flow (Phase 4 Redesigned):
 * 1. Enter phone number to search for existing DSR
 * 2. If DSR registered: Send in-app invitation (they'll see it in their dashboard)
 * 3. If DSR not registered: Generate registration link to share
 * 4. Dealer sets role and permissions
 *
 * Legacy support: Direct add mode for backward compatibility
 */

import { ref, computed, watch } from 'vue';
import {
  X,
  Search,
  Send,
  UserPlus,
  AlertCircle,
  CheckCircle,
  Loader2,
  Users,
  User,
  Phone,
  Copy,
  ExternalLink,
  Mail,
  Shield
} from 'lucide-vue-next';
import { useAccess } from '../composables/useAccess';
import apiClient from '../services/apiClient';
import type { DSR } from '../types';

// ─── Props & Emits ─────────────────────────────────────────────────────────────

const props = defineProps<{
  isOpen: boolean;
  dsrs: DSR[];
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'added'): void;
}>();

// ─── Composables ───────────────────────────────────────────────────────────────

const { getLimit } = useAccess();

// ─── State ─────────────────────────────────────────────────────────────────────

// Mode: 'search' (new flow) or 'direct' (legacy)
const mode = ref<'search' | 'direct'>('search');

// Step in search flow: 'input' | 'searching' | 'found' | 'not_found' | 'inviting' | 'success'
const searchStep = ref<'input' | 'searching' | 'found' | 'not_found' | 'inviting' | 'success'>('input');

// Shared fields
const role = ref<'DSR' | 'Senior_DSR' | 'Manager' | 'Order Collector'>('DSR');
const parentDsrId = ref('');

// Search mode fields
const dsrPhone = ref('');
const dsrEmail = ref('');
const dsrMessage = ref('');

// Search results
const searchResult = ref<{
  exists: boolean;
  registered: boolean;
  dsr_id?: string;
  dsr_name?: string;
  dsr_phone?: string;
  already_assigned?: boolean;
  has_pending_invitation?: boolean;
  invitation_id?: string;
} | null>(null);

// Registration link (for non-registered DSRs)
const registrationUrl = ref('');
const invitationToken = ref('');

// Direct mode fields
const dsrName = ref('');

// UI state
const successMessage = ref('');
const errorMessage = ref('');
const isLoading = ref(false);
const copiedLink = ref(false);

// ─── Computed ──────────────────────────────────────────────────────────────────

const maxDsrs = getLimit('max_dsrs', 5);
const currentDsrCount = computed(() => props.dsrs.length);
const canAddMore = computed(() => {
  const limit = maxDsrs.value;
  if (limit < 0 || limit >= 999999) return true;
  return currentDsrCount.value < limit;
});

const availableParentDsrs = computed(() =>
  props.dsrs.filter((d) => !d.role || d.role === 'DSR'),
);

// Role options with descriptions
const roleOptions = [
  { value: 'DSR', label: 'DSR Rep', description: 'Basic sales access' },
  { value: 'Senior_DSR', label: 'Senior DSR', description: 'Extended permissions' },
  { value: 'Manager', label: 'Manager', description: 'Can manage team' },
  { value: 'Order Collector', label: 'Order Collector', description: 'Reports to DSR' },
];

// Validation
const canSearch = computed(() => dsrPhone.value.trim().length >= 10);
const canInvite = computed(() => {
  if (!dsrPhone.value.trim()) return false;
  if (role.value === 'Order Collector' && !parentDsrId.value) return false;
  return true;
});
const canDirectAdd = computed(() => {
  if (!dsrName.value.trim()) return false;
  if (!dsrPhone.value.trim()) return false;
  if (role.value === 'Order Collector' && !parentDsrId.value) return false;
  return true;
});

// ─── Methods ───────────────────────────────────────────────────────────────────

function resetForm() {
  mode.value = 'search';
  searchStep.value = 'input';
  dsrPhone.value = '';
  dsrEmail.value = '';
  dsrMessage.value = '';
  dsrName.value = '';
  role.value = 'DSR';
  parentDsrId.value = '';
  searchResult.value = null;
  registrationUrl.value = '';
  invitationToken.value = '';
  successMessage.value = '';
  errorMessage.value = '';
  copiedLink.value = false;
}

function handleClose() {
  resetForm();
  emit('close');
}

// Search for existing DSR by phone
async function handleSearch() {
  if (!canSearch.value || !canAddMore.value) return;

  searchStep.value = 'searching';
  errorMessage.value = '';
  searchResult.value = null;

  try {
    const response = await apiClient.get<{
      exists: boolean;
      registered: boolean;
      dsr_id?: string;
      dsr_name?: string;
      dsr_phone?: string;
      already_assigned?: boolean;
      has_pending_invitation?: boolean;
      invitation_id?: string;
    }>('/dealer/dsr/search', {
      params: { phone: dsrPhone.value.trim() }
    });

    searchResult.value = response;
    
    if (response.already_assigned) {
      searchStep.value = 'input';
      errorMessage.value = 'This DSR is already assigned to your team.';
    } else if (response.has_pending_invitation) {
      searchStep.value = 'input';
      errorMessage.value = 'A pending invitation already exists for this phone number.';
    } else if (response.registered) {
      searchStep.value = 'found';
      // Pre-fill name if found
      if (response.dsr_name) {
        dsrName.value = response.dsr_name;
      }
    } else {
      searchStep.value = 'not_found';
    }
  } catch (err: any) {
    searchStep.value = 'input';
    errorMessage.value = err.response?.data?.detail || 'Failed to search for DSR';
  }
}

// Send invitation
async function handleSendInvitation() {
  if (!canInvite.value || !canAddMore.value) return;

  searchStep.value = 'inviting';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const response = await apiClient.post<{
      id: string;
      dsr_phone: string;
      dsr_email: string;
      role: string;
      status: string;
      token: string;
      expires_at: string;
      registration_url?: string;
      message: string;
    }>('/dealer/dsr/invite', {
      dsr_phone: dsrPhone.value.trim(),
      dsr_email: dsrEmail.value.trim() || undefined,
      role: role.value,
      parent_dsr_id: role.value === 'Order Collector' ? parentDsrId.value : undefined,
      message: dsrMessage.value.trim() || undefined,
    });

    invitationToken.value = response.token;
    
    // If registration URL is returned, DSR is not registered
    if (response.registration_url) {
      registrationUrl.value = response.registration_url;
    }

    searchStep.value = 'success';
    successMessage.value = response.message;
    emit('added');

  } catch (err: any) {
    searchStep.value = searchResult.value?.registered ? 'found' : 'not_found';
    errorMessage.value = err.response?.data?.detail || 'Failed to send invitation';
  }
}

// Copy registration link
async function copyRegistrationLink() {
  if (!registrationUrl.value) return;
  
  try {
    await navigator.clipboard.writeText(registrationUrl.value);
    copiedLink.value = true;
    setTimeout(() => {
      copiedLink.value = false;
    }, 2000);
  } catch (err) {
    console.error('Failed to copy:', err);
  }
}

// Direct add (legacy)
async function handleDirectAdd() {
  if (!canDirectAdd.value || !canAddMore.value) return;

  isLoading.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const payload = {
      name: dsrName.value.trim(),
      phone: dsrPhone.value.trim(),
      role: role.value,
      parent_dsr_id: role.value === 'Order Collector' ? parentDsrId.value : null,
    };

    await apiClient.post('/dsr/dsrs/', payload);
    successMessage.value = `${dsrName.value} added successfully!`;
    emit('added');

    setTimeout(() => {
      resetForm();
      emit('close');
    }, 1500);
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || 'Failed to add representative';
  } finally {
    isLoading.value = false;
  }
}

// Reset search to start over
function resetSearch() {
  searchStep.value = 'input';
  searchResult.value = null;
  registrationUrl.value = '';
  invitationToken.value = '';
  errorMessage.value = '';
}

// Reset to search mode
function goToSearchMode() {
  resetForm();
  mode.value = 'search';
}

// Watch for errors reset
watch([dsrPhone, dsrName, role, parentDsrId, mode], () => {
  if (errorMessage.value) errorMessage.value = '';
});
</script>

<template>
  <!-- Backdrop -->
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="isOpen"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        @click.self="handleClose"
      >
        <!-- Modal -->
        <Transition name="scale">
          <div
            v-if="isOpen"
            class="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden max-h-[90vh] overflow-y-auto"
            @click.stop
          >
            <!-- Header -->
            <div class="bg-gradient-to-r from-emerald-600 to-emerald-700 px-6 py-4 sticky top-0 z-10">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="p-2 bg-white/20 rounded-lg">
                    <UserPlus class="h-5 w-5 text-white" />
                  </div>
                  <div>
                    <h2 class="text-lg font-bold text-white">Add Sales Representative</h2>
                    <p class="text-sm text-white/80">Invite DSR to join your team</p>
                  </div>
                </div>
                <button
                  @click="handleClose"
                  class="p-2 hover:bg-white/20 rounded-lg transition cursor-pointer"
                >
                  <X class="h-5 w-5 text-white" />
                </button>
              </div>
            </div>

            <!-- Body -->
            <div class="p-6 space-y-5">
              <!-- Limit Warning -->
              <div
                v-if="!canAddMore"
                class="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-xl"
              >
                <AlertCircle class="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                <div>
                  <p class="text-sm font-semibold text-amber-800">Team Limit Reached</p>
                  <p class="text-xs text-amber-600 mt-1">
                    You've reached the maximum of {{ maxDsrs }} sales representatives.
                    Upgrade your plan to add more team members.
                  </p>
                </div>
              </div>

              <!-- Success Message -->
              <div
                v-if="successMessage"
                class="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl"
              >
                <CheckCircle class="h-5 w-5 text-emerald-600 shrink-0" />
                <p class="text-sm font-semibold text-emerald-800">{{ successMessage }}</p>
              </div>

              <!-- Error Message -->
              <div
                v-if="errorMessage"
                class="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-xl"
              >
                <AlertCircle class="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
                <p class="text-sm text-rose-800">{{ errorMessage }}</p>
              </div>

              <!-- Search Mode -->
              <template v-if="mode === 'search'">
                <!-- Step: Input - Enter phone to search -->
                <template v-if="searchStep === 'input'">
                  <div class="text-center py-4">
                    <div class="bg-emerald-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                      <Phone class="h-8 w-8 text-emerald-600" />
                    </div>
                    <h3 class="text-lg font-semibold text-slate-800 mb-2">Enter DSR Phone Number</h3>
                    <p class="text-sm text-slate-500">
                      We'll check if they're already registered in the system
                    </p>
                  </div>

                  <div class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Phone class="h-4 w-4 text-emerald-500" />
                        Phone Number *
                      </label>
                      <input
                        type="tel"
                        v-model="dsrPhone"
                        placeholder="+91 91122 33445"
                        :disabled="!canAddMore"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800 disabled:opacity-50"
                        @keyup.enter="handleSearch"
                      />
                    </div>

                    <button
                      @click="handleSearch"
                      :disabled="!canSearch || !canAddMore"
                      class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-semibold transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Search class="h-5 w-5" />
                      Search for DSR
                    </button>
                  </div>
                </template>

                <!-- Step: Searching -->
                <template v-else-if="searchStep === 'searching'">
                  <div class="text-center py-8">
                    <Loader2 class="h-10 w-10 text-emerald-600 animate-spin mx-auto mb-4" />
                    <p class="text-slate-600">Searching for DSR...</p>
                  </div>
                </template>

                <!-- Step: Found - DSR is registered -->
                <template v-else-if="searchStep === 'found'">
                  <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-4">
                    <div class="flex items-center gap-3">
                      <div class="bg-emerald-100 p-2 rounded-full">
                        <CheckCircle class="h-5 w-5 text-emerald-600" />
                      </div>
                      <div>
                        <p class="font-semibold text-emerald-800">DSR Found!</p>
                        <p class="text-sm text-emerald-600">{{ searchResult?.dsr_name }} is registered in the system.</p>
                      </div>
                    </div>
                  </div>

                  <!-- Role Selection -->
                  <div class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Assign Role</label>
                      <div class="grid grid-cols-2 gap-2">
                        <button
                          v-for="opt in roleOptions"
                          :key="opt.value"
                          type="button"
                          @click="role = opt.value as any"
                          :class="[
                            'p-3 rounded-xl border-2 text-left transition',
                            role === opt.value
                              ? 'border-emerald-500 bg-emerald-50'
                              : 'border-slate-200 hover:border-slate-300'
                          ]"
                        >
                          <p class="font-semibold text-slate-800 text-sm">{{ opt.label }}</p>
                          <p class="text-xs text-slate-500">{{ opt.description }}</p>
                        </button>
                      </div>
                    </div>

                    <!-- Parent DSR for Collectors -->
                    <div v-if="role === 'Order Collector'" class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Users class="h-4 w-4 text-emerald-500" />
                        Supervisor DSR *
                      </label>
                      <select
                        v-model="parentDsrId"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        <option value="">Select a supervisor...</option>
                        <option v-for="d in availableParentDsrs" :key="d.id" :value="d.id">
                          {{ d.name }}
                        </option>
                      </select>
                    </div>

                    <!-- Optional Email -->
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Mail class="h-4 w-4 text-slate-400" />
                        Email (optional)
                      </label>
                      <input
                        type="email"
                        v-model="dsrEmail"
                        placeholder="dsr@example.com"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800"
                      />
                    </div>

                    <!-- Optional Message -->
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Message (optional)</label>
                      <textarea
                        v-model="dsrMessage"
                        placeholder="Welcome to our team..."
                        rows="2"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800 resize-none"
                      />
                    </div>
                  </div>

                  <div class="flex gap-3 pt-2">
                    <button
                      @click="resetSearch"
                      class="py-2.5 px-4 border border-slate-300 rounded-xl text-sm font-semibold hover:bg-slate-50 transition"
                    >
                      Back
                    </button>
                    <button
                      @click="handleSendInvitation"
                      :disabled="!canInvite"
                      class="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <Send class="h-4 w-4" />
                      Send Invitation
                    </button>
                  </div>
                </template>

                <!-- Step: Not Found - DSR not registered -->
                <template v-else-if="searchStep === 'not_found'">
                  <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
                    <div class="flex items-center gap-3">
                      <div class="bg-amber-100 p-2 rounded-full">
                        <UserPlus class="h-5 w-5 text-amber-600" />
                      </div>
                      <div>
                        <p class="font-semibold text-amber-800">DSR Not Registered</p>
                        <p class="text-sm text-amber-600">This phone number is not registered in our system.</p>
                      </div>
                    </div>
                  </div>

                  <p class="text-sm text-slate-600 mb-4">
                    You can invite them to register. Set their role and we'll generate a registration link for you to share.
                  </p>

                  <!-- Role Selection -->
                  <div class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Assign Role</label>
                      <select
                        v-model="role"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                          {{ opt.label }} - {{ opt.description }}
                        </option>
                      </select>
                    </div>

                    <!-- Parent DSR for Collectors -->
                    <div v-if="role === 'Order Collector'" class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Supervisor DSR *</label>
                      <select
                        v-model="parentDsrId"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      >
                        <option value="">Select a supervisor...</option>
                        <option v-for="d in availableParentDsrs" :key="d.id" :value="d.id">
                          {{ d.name }}
                        </option>
                      </select>
                    </div>

                    <!-- Optional Email -->
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Email (optional)</label>
                      <input
                        type="email"
                        v-model="dsrEmail"
                        placeholder="dsr@example.com"
                        class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800"
                      />
                      <p class="text-xs text-slate-500">If provided, we'll send the invitation via email</p>
                    </div>
                  </div>

                  <div class="flex gap-3 pt-2">
                    <button
                      @click="resetSearch"
                      class="py-2.5 px-4 border border-slate-300 rounded-xl text-sm font-semibold hover:bg-slate-50 transition"
                    >
                      Back
                    </button>
                    <button
                      @click="handleSendInvitation"
                      :disabled="!canInvite"
                      class="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold transition flex items-center justify-center gap-2 disabled:opacity-50"
                    >
                      <Send class="h-4 w-4" />
                      Generate Invitation
                    </button>
                  </div>
                </template>

                <!-- Step: Inviting -->
                <template v-else-if="searchStep === 'inviting'">
                  <div class="text-center py-8">
                    <Loader2 class="h-10 w-10 text-emerald-600 animate-spin mx-auto mb-4" />
                    <p class="text-slate-600">Sending invitation...</p>
                  </div>
                </template>

                <!-- Step: Success -->
                <template v-else-if="searchStep === 'success'">
                  <div class="text-center py-4">
                    <div class="bg-emerald-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                      <CheckCircle class="h-8 w-8 text-emerald-600" />
                    </div>
                    <h3 class="text-lg font-semibold text-slate-800 mb-2">Invitation Sent!</h3>
                    <p class="text-sm text-slate-500 mb-6">
                      {{ searchResult?.registered 
                        ? 'The DSR will see the invitation in their dashboard.' 
                        : 'Share the registration link with the DSR to complete signup.' 
                      }}
                    </p>

                    <!-- Show registration link if DSR not registered -->
                    <div v-if="registrationUrl" class="bg-slate-50 border border-slate-200 rounded-xl p-4 mb-4">
                      <label class="text-xs font-semibold text-slate-500 uppercase tracking-wide">Registration Link</label>
                      <div class="mt-2 flex items-center gap-2">
                        <input
                          type="text"
                          :value="registrationUrl"
                          readonly
                          class="flex-1 text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 truncate"
                        />
                        <button
                          @click="copyRegistrationLink"
                          :class="[
                            'p-2 rounded-lg transition',
                            copiedLink ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          ]"
                        >
                          <Copy class="h-4 w-4" />
                        </button>
                        <a
                          :href="registrationUrl"
                          target="_blank"
                          class="p-2 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded-lg transition"
                        >
                          <ExternalLink class="h-4 w-4" />
                        </a>
                      </div>
                      <p v-if="copiedLink" class="text-xs text-emerald-600 mt-2">Link copied to clipboard!</p>
                    </div>

                    <div class="flex gap-3">
                      <button
                        @click="handleClose"
                        class="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-sm font-semibold transition"
                      >
                        Done
                      </button>
                      <button
                        @click="resetForm"
                        class="flex-1 py-2.5 border border-emerald-300 text-emerald-700 rounded-xl text-sm font-semibold hover:bg-emerald-50 transition"
                      >
                        Add Another
                      </button>
                    </div>
                  </div>
                </template>
              </template>

              <!-- Direct Add Mode (Legacy) -->
              <template v-else-if="mode === 'direct'">
                <div class="space-y-4">
                  <div class="space-y-2">
                    <label class="text-sm font-semibold text-slate-700">Full Name *</label>
                    <input
                      type="text"
                      v-model="dsrName"
                      placeholder="e.g. Rajesh Kumar"
                      :disabled="isLoading"
                      class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800"
                    />
                  </div>

                  <div class="space-y-2">
                    <label class="text-sm font-semibold text-slate-700">Phone Number *</label>
                    <input
                      type="text"
                      v-model="dsrPhone"
                      placeholder="e.g. +91 91122 33445"
                      :disabled="isLoading"
                      class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white text-slate-800 font-mono"
                    />
                  </div>

                  <div class="space-y-2">
                    <label class="text-sm font-semibold text-slate-700">Role</label>
                    <select
                      v-model="role"
                      :disabled="isLoading"
                      class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                        {{ opt.label }}
                      </option>
                    </select>
                  </div>

                  <div v-if="role === 'Order Collector'" class="space-y-2">
                    <label class="text-sm font-semibold text-slate-700">Supervisor DSR *</label>
                    <select
                      v-model="parentDsrId"
                      :disabled="isLoading"
                      class="w-full text-sm py-3 px-4 border border-slate-200 rounded-xl bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <option value="">Select a supervisor...</option>
                      <option v-for="d in availableParentDsrs" :key="d.id" :value="d.id">
                        {{ d.name }}
                      </option>
                    </select>
                  </div>
                </div>

                <div class="flex justify-end gap-3 pt-4">
                  <button
                    type="button"
                    @click="goToSearchMode"
                    class="py-2.5 px-4 border border-slate-300 rounded-xl text-sm font-semibold hover:bg-slate-50 transition"
                  >
                    Back to Search
                  </button>
                  <button
                    @click="handleDirectAdd"
                    :disabled="!canDirectAdd || isLoading || !canAddMore"
                    class="py-2.5 px-5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-sm font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Loader2 v-if="isLoading" class="h-4 w-4 animate-spin" />
                    <UserPlus v-else class="h-4 w-4" />
                    Add Directly
                  </button>
                </div>
              </template>

              <!-- Mode Toggle (only show in input step) -->
              <div v-if="searchStep === 'input'" class="pt-4 border-t border-slate-100">
                <button
                  @click="mode = 'direct'"
                  class="w-full text-center text-sm text-slate-500 hover:text-slate-700"
                >
                  Or <span class="text-emerald-600 font-medium">add directly</span> without invitation
                </button>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
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

.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
