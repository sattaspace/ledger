<script setup lang="ts">
/**
 * AddRepModal — Unified modal for inviting/adding sales representatives.
 *
 * Email-First Flow (Updated):
 * 1. Enter email address to search for existing DSR
 * 2. If DSR registered: Send in-app notification (they'll see it in their dashboard)
 * 3. If DSR not registered: Send invitation email with registration link
 * 4. Dealer sets role and permissions
 * 5. Phone number is optional for contact purposes
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

// useAccess is used in the Computed section below

// ─── State ─────────────────────────────────────────────────────────────────────

// Step in search flow: 'input' | 'searching' | 'found' | 'not_found' | 'inviting' | 'success'
const searchStep = ref<'input' | 'searching' | 'found' | 'not_found' | 'inviting' | 'success'>('input');

// Shared fields
const role = ref<'DSR' | 'Senior_DSR' | 'Manager' | 'Order Collector'>('DSR');
const parentDsrId = ref('');

// Search mode fields - EMAIL IS NOW PRIMARY
const dsrEmail = ref('');
const dsrPhone = ref('');  // Optional
const dsrMessage = ref('');

// Search results
const searchResult = ref<{
  exists: boolean;
  registered: boolean;
  dsrId?: string;
  dsrName?: string;
  dsrEmail?: string;
  dsrPhone?: string;
  alreadyAssigned?: boolean;
  hasPendingInvitation?: boolean;
  invitationId?: string;
} | null>(null);

// Registration link (for non-registered DSRs)
const registrationUrl = ref('');
const invitationToken = ref('');

// UI state
const successMessage = ref('');
const errorMessage = ref('');
const isLoading = ref(false);
const copiedLink = ref(false);

// ─── Computed ──────────────────────────────────────────────────────────────────

const { access, getLimit } = useAccess();
const maxDsrs = getLimit('max_dsrs', 5);  // Default 5 if not set
const currentDsrCount = computed(() => props.dsrs?.length || 0);
const canAddMore = computed(() => {
  const limit = maxDsrs.value;
  console.log('[AddRepModal] canAddMore check:', {
    limit,
    currentDsrCount: currentDsrCount.value,
    accessMap: access.value
  });
  // 0 or negative = unlimited
  if (limit === 0 || limit < 0) return true;
  // Very high number = effectively unlimited
  if (limit >= 999999) return true;
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

// Validation - EMAIL IS REQUIRED
const canSearch = computed(() => {
  const email = dsrEmail.value.trim();
  return email.length > 0 && email.includes('@');
});

const canInvite = computed(() => {
  if (!dsrEmail.value.trim()) return false;
  if (role.value === 'Order Collector' && !parentDsrId.value) return false;
  return true;
});

// ─── Methods ───────────────────────────────────────────────────────────────────

function resetForm() {
  searchStep.value = 'input';
  dsrEmail.value = '';
  dsrPhone.value = '';
  dsrMessage.value = '';
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

// Search for existing DSR by EMAIL
async function handleSearch() {
  if (!canSearch.value || !canAddMore.value) return;

  searchStep.value = 'searching';
  errorMessage.value = '';
  searchResult.value = null;

  try {
    // Construct URL with query params (apiClient doesn't support params option)
    const searchEmail = encodeURIComponent(dsrEmail.value.trim());
    const apiResponse = await apiClient.get<{
      exists: boolean;
      registered: boolean;
      dsrId?: string;
      dsrName?: string;
      dsrEmail?: string;
      dsrPhone?: string;
      alreadyAssigned?: boolean;
      hasPendingInvitation?: boolean;
      invitationId?: string;
    }>(`/dealer/dsr/search?email=${searchEmail}`);

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data || apiResponse;
    searchResult.value = response;
    
    if (response.alreadyAssigned) {
      searchStep.value = 'input';
      errorMessage.value = 'This DSR is already assigned to your team.';
    } else if (response.hasPendingInvitation) {
      // Don't block — the invite endpoint auto-revokes stale pending
      // invitations. Let the user proceed; show a note about re-invite.
      searchStep.value = response.registered ? 'found' : 'not_found';
      if (response.dsrPhone) {
        dsrPhone.value = response.dsrPhone;
      }
    } else if (response.registered) {
      searchStep.value = 'found';
      // Pre-fill phone if found
      if (response.dsrPhone) {
        dsrPhone.value = response.dsrPhone;
      }
    } else {
      searchStep.value = 'not_found';
    }
  } catch (err: any) {
    searchStep.value = 'input';
    errorMessage.value = err.data?.detail || err.message || 'Failed to search for DSR';
  }
}

// Send invitation - EMAIL IS REQUIRED, PHONE IS OPTIONAL
async function handleSendInvitation() {
  if (!canInvite.value || !canAddMore.value) return;

  searchStep.value = 'inviting';
  errorMessage.value = '';
  successMessage.value = '';

  try {
    const apiResponse = await apiClient.post<{
      id: string;
      dsrEmail: string;
      dsrPhone: string;
      role: string;
      status: string;
      token: string;
      expiresAt: string;
      registrationUrl?: string;
      message: string;
    }>('/dealer/dsr/invite', {
      dsrEmail: dsrEmail.value.trim(),  // REQUIRED (apiClient transforms to dsr_email)
      dsrPhone: dsrPhone.value.trim() || undefined,  // OPTIONAL
      role: role.value,
      parentDsrId: role.value === 'Order Collector' ? parentDsrId.value : undefined,  // apiClient transforms to parent_dsr_id
      message: dsrMessage.value.trim() || undefined,
    });

    // apiClient returns { ok, status, data } - access actual data via .data
    const response = apiResponse.data || apiResponse;
    invitationToken.value = response.token;
    
    // If registration URL is returned, DSR is not registered
    if (response.registrationUrl) {
      registrationUrl.value = response.registrationUrl;
    }

    searchStep.value = 'success';
    successMessage.value = response.message;
    emit('added');

  } catch (err: any) {
    searchStep.value = searchResult.value?.registered ? 'found' : 'not_found';
    errorMessage.value = err.data?.detail || err.message || 'Failed to send invitation';
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

// Reset search to start over
function resetSearch() {
  searchStep.value = 'input';
  searchResult.value = null;
  registrationUrl.value = '';
  invitationToken.value = '';
  errorMessage.value = '';
}

// Watch for errors reset
watch([dsrEmail, dsrPhone, role, parentDsrId], () => {
  if (errorMessage.value) errorMessage.value = '';
});
</script>

<template>
  <!-- Backdrop -->
  <!-- Hydration fix H-1: move v-if from inside <Transition> to the
       <Teleport> itself. When the modal is closed (isOpen is false),
       the entire <Teleport> block is skipped during SSR — no
       placeholder, no hydration mismatch. The `appear` attribute on
       <Transition> ensures the fade-in animation plays when the modal
       is opened client-side. The inner <Transition name="scale"> no
       longer needs its own v-if (the parent Teleport gates it). -->
  <Teleport v-if="isOpen" to="body">
    <Transition name="fade" appear>
      <div
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
        @click.self="handleClose"
      >
        <!-- Modal -->
        <Transition name="scale" appear>
          <div
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
                    You have {{ currentDsrCount }} of {{ maxDsrs }} sales representatives.
                    <span v-if="currentDsrCount > 0">Delete an existing DSR or u</span>
                    <span v-else>U</span>pgrade your plan to add more team members.
                  </p>
                  <!-- Debug info for development -->
                  <p class="text-xs text-amber-400 mt-2 font-mono">
                    [Debug] Limit: {{ maxDsrs }}, Current: {{ currentDsrCount }}, Access: {{ access?.max_dsrs ?? 'not set' }}
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

              <!-- Invitation Flow (email-first) -->
                <!-- Step: Input - Enter email to search -->
                <template v-if="searchStep === 'input'">
                  <div class="text-center py-4">
                    <div class="bg-emerald-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                      <Mail class="h-8 w-8 text-emerald-600" />
                    </div>
                    <h3 class="text-lg font-semibold text-slate-800 mb-2">Enter DSR Email Address</h3>
                    <p class="text-sm text-slate-500">
                      We'll check if they're already registered in the system
                    </p>
                  </div>

                  <div class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Mail class="h-4 w-4 text-emerald-500" />
                        Email Address *
                      </label>
                      <input
                        v-model="dsrEmail"
                        type="email"
                        placeholder="dsr@example.com"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                        @keyup.enter="handleSearch"
                      />
                    </div>

                    <button
                      @click="handleSearch"
                      :disabled="!canSearch || !canAddMore"
                      class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                    >
                      <Search class="h-5 w-5" />
                      Search
                    </button>
                  </div>
                </template>

                <!-- Step: Searching -->
                <template v-else-if="searchStep === 'searching'">
                  <div class="text-center py-12">
                    <Loader2 class="h-12 w-12 text-emerald-600 animate-spin mx-auto mb-4" />
                    <p class="text-slate-600">Searching for DSR...</p>
                  </div>
                </template>

                <!-- Step: Found - DSR is registered -->
                <template v-else-if="searchStep === 'found'">
                  <div class="text-center py-4">
                    <div class="bg-emerald-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                      <CheckCircle class="h-8 w-8 text-emerald-600" />
                    </div>
                    <h3 class="text-lg font-semibold text-slate-800 mb-2">DSR Found!</h3>
                    <p class="text-sm text-slate-500">
                      {{ searchResult?.dsrName || 'A DSR' }} is already registered
                    </p>
                  </div>

                  <div class="bg-emerald-50 border border-emerald-200 rounded-xl p-4 mb-4">
                    <div class="flex items-center gap-3">
                      <div class="w-10 h-10 rounded-full bg-emerald-600 flex items-center justify-center text-white font-semibold">
                        {{ (searchResult?.dsrName || 'DSR').split(' ').map(n => n[0] || '').join('').slice(0, 2).toUpperCase() }}
                      </div>
                      <div>
                        <p class="font-semibold text-slate-800">{{ searchResult?.dsrName || 'DSR' }}</p>
                        <p class="text-sm text-slate-500">{{ searchResult?.dsrEmail }}</p>
                      </div>
                    </div>
                  </div>

                  <!-- Role Selection -->
                  <div class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Role</label>
                      <select
                        v-model="role"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                      >
                        <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                          {{ opt.label }} - {{ opt.description }}
                        </option>
                      </select>
                    </div>

                    <!-- Parent DSR (for Order Collector) -->
                    <div v-if="role === 'Order Collector'" class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Parent DSR *</label>
                      <select
                        v-model="parentDsrId"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                      >
                        <option value="">Select parent DSR...</option>
                        <option v-for="dsr in availableParentDsrs" :key="dsr.id" :value="dsr.id">
                          {{ dsr.name }}
                        </option>
                      </select>
                    </div>

                    <!-- Optional Message -->
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Message (optional)</label>
                      <textarea
                        v-model="dsrMessage"
                        placeholder="Add a personal message to the invitation..."
                        rows="2"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none resize-none"
                      />
                    </div>

                    <div class="flex gap-3">
                      <button
                        @click="resetSearch"
                        class="flex-1 py-3 border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold rounded-xl transition-colors"
                      >
                        Back
                      </button>
                      <button
                        @click="handleSendInvitation"
                        :disabled="!canInvite"
                        class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                      >
                        <Send class="h-5 w-5" />
                        Send Invitation
                      </button>
                    </div>
                  </div>
                </template>

                <!-- Step: Not Found - DSR is not registered -->
                <template v-else-if="searchStep === 'not_found'">
                  <div class="text-center py-4">
                    <div class="bg-amber-100 p-4 rounded-full w-16 h-16 mx-auto mb-4 flex items-center justify-center">
                      <Mail class="h-8 w-8 text-amber-600" />
                    </div>
                    <h3 class="text-lg font-semibold text-slate-800 mb-2">DSR Not Registered</h3>
                    <p class="text-sm text-slate-500">
                      We'll send an email invitation with a registration link
                    </p>
                  </div>

                  <div class="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-4">
                    <p class="text-sm text-amber-800">
                      <strong>{{ dsrEmail }}</strong> is not registered yet.
                      An invitation email will be sent with a link to create their account.
                    </p>
                  </div>

                  <!-- Role and Details -->
                  <div class="space-y-4">
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Mail class="h-4 w-4 text-emerald-500" />
                        Email Address *
                      </label>
                      <input
                        v-model="dsrEmail"
                        type="email"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl bg-slate-50 text-slate-600"
                        disabled
                      />
                    </div>

                    <!-- Phone (Optional) -->
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700 flex items-center gap-2">
                        <Phone class="h-4 w-4 text-slate-400" />
                        Phone Number (optional)
                      </label>
                      <input
                        v-model="dsrPhone"
                        type="tel"
                        placeholder="+91 98765 43210"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-all"
                      />
                    </div>

                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Role</label>
                      <select
                        v-model="role"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                      >
                        <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
                          {{ opt.label }} - {{ opt.description }}
                        </option>
                      </select>
                    </div>

                    <!-- Parent DSR (for Order Collector) -->
                    <div v-if="role === 'Order Collector'" class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Parent DSR *</label>
                      <select
                        v-model="parentDsrId"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
                      >
                        <option value="">Select parent DSR...</option>
                        <option v-for="dsr in availableParentDsrs" :key="dsr.id" :value="dsr.id">
                          {{ dsr.name }}
                        </option>
                      </select>
                    </div>

                    <!-- Optional Message -->
                    <div class="space-y-2">
                      <label class="text-sm font-semibold text-slate-700">Message (optional)</label>
                      <textarea
                        v-model="dsrMessage"
                        placeholder="Add a personal message to the invitation..."
                        rows="2"
                        class="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none resize-none"
                      />
                    </div>

                    <div class="flex gap-3">
                      <button
                        @click="resetSearch"
                        class="flex-1 py-3 border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold rounded-xl transition-colors"
                      >
                        Back
                      </button>
                      <button
                        @click="handleSendInvitation"
                        :disabled="!canInvite"
                        class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                      >
                        <Send class="h-5 w-5" />
                        Send Invitation
                      </button>
                    </div>
                  </div>
                </template>

                <!-- Step: Inviting -->
                <template v-else-if="searchStep === 'inviting'">
                  <div class="text-center py-12">
                    <Loader2 class="h-12 w-12 text-emerald-600 animate-spin mx-auto mb-4" />
                    <p class="text-slate-600">Sending invitation...</p>
                  </div>
                </template>

                <!-- Step: Success -->
                <template v-else-if="searchStep === 'success'">
                  <div class="text-center py-8">
                    <div class="bg-emerald-100 p-4 rounded-full w-20 h-20 mx-auto mb-4 flex items-center justify-center">
                      <CheckCircle class="h-10 w-10 text-emerald-600" />
                    </div>
                    <h3 class="text-xl font-semibold text-slate-800 mb-2">Invitation Sent!</h3>
                    <p class="text-slate-500 mb-6">
                      {{ searchResult?.registered 
                        ? 'The DSR will see the invitation in their dashboard.' 
                        : 'An email has been sent with registration instructions.' 
                      }}
                    </p>

                    <!-- Show registration link if DSR not registered -->
                    <div v-if="registrationUrl" class="bg-slate-50 rounded-xl p-4 mb-4">
                      <p class="text-xs text-slate-500 mb-2">Or share this registration link directly:</p>
                      <div class="flex items-center gap-2">
                        <input
                          :value="registrationUrl"
                          readonly
                          class="flex-1 px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg truncate"
                        />
                        <button
                          @click="copyRegistrationLink"
                          class="px-3 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors"
                        >
                          <Copy v-if="!copiedLink" class="h-4 w-4" />
                          <CheckCircle v-else class="h-4 w-4" />
                        </button>
                      </div>
                    </div>

                    <div class="flex gap-3">
                      <button
                        @click="resetForm"
                        class="flex-1 py-3 border border-slate-300 hover:bg-slate-50 text-slate-700 font-semibold rounded-xl transition-colors"
                      >
                        Invite Another
                      </button>
                      <button
                        @click="handleClose"
                        class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl transition-colors"
                      >
                        Done
                      </button>
                    </div>
                  </div>
                </template>
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
