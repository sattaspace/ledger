<script setup lang="ts">
/**
 * PlanDetailAdmin — Plan detail page for /admin/plans/:planId.
 *
 * Features:
 *   - Plan info card with edit/toggle/feature/duplicate/delete actions
 *   - Access entries data table with add/edit/delete
 *   - Add access entry modal
 *   - Edit access entry modal
 *   - Bulk update button
 *
 * Uses 10.2 components: AdminPageHeader, AdminDataTable, AdminConfirmDialog,
 * AdminStatusBadge, AdminEmptyState.
 */

import { ref, computed, onMounted } from "vue";
import { requireAuth, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import { adminApi, formatDateTime } from "@/lib/admin";
import type {
  PlanDetail,
  PlanUpdatePayload,
  AccessEntryItem,
  AccessEntryCreatePayload,
  AccessEntryUpdatePayload,
} from "@/lib/admin";

import AdminPageHeader from "@/components/admin/AdminPageHeader.vue";
import AdminDataTable from "@/components/admin/AdminDataTable.vue";
import type { ColumnDef } from "@/components/admin/AdminDataTable.vue";
import AdminConfirmDialog from "@/components/admin/AdminConfirmDialog.vue";
import AdminStatusBadge from "@/components/admin/AdminStatusBadge.vue";

// ─── Props ───────────────────────────────────────────────────────────────────

const props = defineProps<{
  planId: number;
}>();

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true);
const loadError = ref<string | null>(null);
const actionLoading = ref<string | null>(null);

const plan = ref<PlanDetail | null>(null);

// Edit plan modal
const showEditModal = ref(false);
const editLoading = ref(false);
const editError = ref<string | null>(null);
const editForm = ref({
  name: "",
  slug: "",
  priceDollars: 0,
  currency: "usd",
  billing_cycle: "monthly" as "monthly" | "yearly",
  trial_days: 0,
  is_featured: false,
  sort_order: 0,
});

// Add access entry modal
const showAddEntryModal = ref(false);
const addEntryLoading = ref(false);
const addEntryError = ref<string | null>(null);
const addEntryForm = ref({
  key: "",
  value: "",
  value_type: "boolean" as "boolean" | "integer" | "string",
  description: "",
});

// Edit access entry modal
const showEditEntryModal = ref(false);
const editEntryLoading = ref(false);
const editEntryError = ref<string | null>(null);
const editingEntry = ref<AccessEntryItem | null>(null);
const editEntryForm = ref({
  key: "",
  value: "",
  value_type: "boolean" as "boolean" | "integer" | "string",
  description: "",
});

// Delete confirmation
const showDeletePlanDialog = ref(false);
const showDeleteEntryDialog = ref(false);
const deletingEntry = ref<AccessEntryItem | null>(null);

// ─── Column definitions: Access Entries ──────────────────────────────────────

const entryColumns = computed<ColumnDef[]>(() => [
  { key: "key", label: "Key", sortable: true, defaultSort: "asc" },
  { key: "value", label: "Value", width: "120px" },
  { key: "value_type", label: "Type", align: "center", width: "90px", hideOnMobile: true },
  { key: "description", label: "Description", hideOnMobile: true },
  { key: "actions", label: "", align: "right", width: "90px" },
]);

// ─── Data fetching ───────────────────────────────────────────────────────────

async function fetchPlan() {
  loading.value = true;
  loadError.value = null;
  try {
    plan.value = await adminApi.getPlan(props.planId);
  } catch (err) {
    loadError.value = getErrorMessage(err);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  if (!requireAuth()) return;
  await fetchPlan();
});

// ─── Format price ────────────────────────────────────────────────────────────

function formatCents(cents: number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency?.toUpperCase() || "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

function dollarsToCents(dollars: number): number {
  return Math.round(dollars * 100);
}

function centsToDollars(cents: number): number {
  return cents / 100;
}

// ─── Edit Plan ───────────────────────────────────────────────────────────────

function openEditModal() {
  if (!plan.value) return;
  editForm.value = {
    name: plan.value.name,
    slug: plan.value.slug,
    priceDollars: centsToDollars(plan.value.price_cents),
    currency: plan.value.currency,
    billing_cycle: plan.value.billing_cycle,
    trial_days: plan.value.trial_days,
    is_featured: plan.value.is_featured,
    sort_order: plan.value.sort_order,
  };
  editError.value = null;
  showEditModal.value = true;
}

async function handleEditSubmit() {
  editLoading.value = true;
  editError.value = null;
  try {
    const payload: PlanUpdatePayload = {
      name: editForm.value.name,
      slug: editForm.value.slug,
      price_cents: dollarsToCents(editForm.value.priceDollars),
      currency: editForm.value.currency,
      billing_cycle: editForm.value.billing_cycle,
      trial_days: editForm.value.trial_days,
      is_featured: editForm.value.is_featured,
      sort_order: editForm.value.sort_order,
    };
    await adminApi.updatePlan(props.planId, payload);
    showToast("Plan updated.", "success");
    showEditModal.value = false;
    await fetchPlan();
  } catch (err) {
    editError.value = getErrorMessage(err);
  } finally {
    editLoading.value = false;
  }
}

// ─── Plan actions ────────────────────────────────────────────────────────────

async function handleToggle() {
  if (!plan.value) return;
  actionLoading.value = "toggle";
  try {
    await adminApi.togglePlan(props.planId);
    showToast(`Plan ${plan.value.is_active ? "deactivated" : "activated"}.`, "success");
    await fetchPlan();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function handleToggleFeature() {
  if (!plan.value) return;
  actionLoading.value = "feature";
  try {
    await adminApi.togglePlanFeature(props.planId);
    showToast(`Plan ${plan.value.is_featured ? "unfeatured" : "featured"}.`, "success");
    await fetchPlan();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function handleDuplicate() {
  actionLoading.value = "duplicate";
  try {
    await adminApi.duplicatePlan(props.planId);
    showToast("Plan duplicated.", "success");
    await fetchPlan();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function confirmDeletePlan() {
  actionLoading.value = "delete-plan";
  try {
    await adminApi.deletePlan(props.planId);
    showToast("Plan deleted.", "success");
    showDeletePlanDialog.value = false;
    // Navigate back to product detail
    if (plan.value) {
      window.location.href = `/admin/products/${plan.value.product_id}`;
    } else {
      window.location.href = "/admin/products";
    }
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

// ─── Add Access Entry ────────────────────────────────────────────────────────

function openAddEntryModal() {
  addEntryForm.value = { key: "", value: "true", value_type: "boolean", description: "" };
  addEntryError.value = null;
  showAddEntryModal.value = true;
}

async function handleAddEntry() {
  addEntryLoading.value = true;
  addEntryError.value = null;
  try {
    const payload: AccessEntryCreatePayload = {
      key: addEntryForm.value.key,
      value: addEntryForm.value.value,
      value_type: addEntryForm.value.value_type,
      description: addEntryForm.value.description || undefined,
    };
    await adminApi.addAccessEntry(props.planId, payload);
    showToast("Access entry added.", "success");
    showAddEntryModal.value = false;
    await fetchPlan();
  } catch (err) {
    addEntryError.value = getErrorMessage(err);
  } finally {
    addEntryLoading.value = false;
  }
}

// ─── Edit Access Entry ───────────────────────────────────────────────────────

function openEditEntryModal(entry: AccessEntryItem) {
  editingEntry.value = entry;
  editEntryForm.value = {
    key: entry.key,
    value: entry.value,
    value_type: entry.value_type,
    description: entry.description,
  };
  editEntryError.value = null;
  showEditEntryModal.value = true;
}

async function handleEditEntrySubmit() {
  if (!editingEntry.value) return;
  editEntryLoading.value = true;
  editEntryError.value = null;
  try {
    const payload: AccessEntryUpdatePayload = {
      key: editEntryForm.value.key,
      value: editEntryForm.value.value,
      value_type: editEntryForm.value.value_type,
      description: editEntryForm.value.description || undefined,
    };
    await adminApi.updateAccessEntry(editingEntry.value.id, payload);
    showToast("Access entry updated.", "success");
    showEditEntryModal.value = false;
    await fetchPlan();
  } catch (err) {
    editEntryError.value = getErrorMessage(err);
  } finally {
    editEntryLoading.value = false;
  }
}

// ─── Delete Access Entry ─────────────────────────────────────────────────────

function openDeleteEntryDialog(entry: AccessEntryItem) {
  deletingEntry.value = entry;
  showDeleteEntryDialog.value = true;
}

async function confirmDeleteEntry() {
  if (!deletingEntry.value) return;
  actionLoading.value = `delete-entry-${deletingEntry.value.id}`;
  try {
    await adminApi.deleteAccessEntry(deletingEntry.value.id);
    showToast("Access entry removed.", "success");
    showDeleteEntryDialog.value = false;
    deletingEntry.value = null;
    await fetchPlan();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

// ─── Sort entries ────────────────────────────────────────────────────────────

function handleEntrySort({ key, direction }: { key: string; direction: "asc" | "desc" }) {
  if (!plan.value) return;
  plan.value.access_entries.sort((a, b) => {
    const aVal = (a as Record<string, unknown>)[key];
    const bVal = (b as Record<string, unknown>)[key];
    if (aVal == null || bVal == null) return 0;
    const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
    return direction === "asc" ? cmp : -cmp;
  });
}
</script>

<template>
  <div class="space-y-6">
    <!-- Loading -->
    <div v-if="loading" class="space-y-6 animate-pulse">
      <div class="h-8 w-64 rounded skeleton" />
      <div class="h-48 rounded skeleton" />
    </div>

    <!-- Error -->
    <div
      v-else-if="loadError"
      class="card flex flex-col items-center gap-4 p-10 text-center"
    >
      <svg class="h-12 w-12 text-destructive/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <p class="font-medium text-foreground">Failed to load plan</p>
      <p class="text-sm text-muted-foreground">{{ loadError }}</p>
      <button type="button" class="btn-secondary" @click="fetchPlan">Try again</button>
    </div>

    <!-- Plan detail -->
    <template v-else-if="plan">
      <!-- Page Header -->
      <AdminPageHeader
        :title="plan.name"
        :description="`${plan.product_name} — ${formatCents(plan.price_cents, plan.currency)}/${plan.billing_cycle}`"
        :breadcrumbs="[
          { label: 'Admin', href: '/admin' },
          { label: 'Products', href: '/admin/products' },
          { label: plan.product_name, href: `/admin/products/${plan.product_id}` },
          { label: plan.name },
        ]"
      >
        <template #secondary-action>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2"
              @click="openEditModal"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit
            </button>
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2"
              :disabled="actionLoading === 'feature'"
              @click="handleToggleFeature"
            >
              <svg class="h-4 w-4" :class="plan.is_featured ? 'text-amber-500' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
              {{ plan.is_featured ? "Unfeature" : "Feature" }}
            </button>
          </div>
        </template>
        <template #primary-action>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2"
              :disabled="actionLoading === 'duplicate'"
              @click="handleDuplicate"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Duplicate
            </button>
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2"
              :disabled="actionLoading === 'toggle'"
              @click="handleToggle"
            >
              {{ plan.is_active ? "Deactivate" : "Activate" }}
            </button>
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
              @click="showDeletePlanDialog = true"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </template>
      </AdminPageHeader>

      <!-- Plan Info Card -->
      <div class="card p-5">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Price</p>
            <p class="mt-1 text-sm font-semibold text-foreground">
              {{ formatCents(plan.price_cents, plan.currency) }}
              <span class="font-normal text-muted-foreground">/ {{ plan.billing_cycle }}</span>
            </p>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Trial</p>
            <p class="mt-1 text-sm text-foreground">
              {{ plan.trial_days > 0 ? `${plan.trial_days} days` : "None" }}
            </p>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Subscribers</p>
            <p class="mt-1 text-sm font-medium text-foreground">{{ plan.subscriber_count }}</p>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Status</p>
            <div class="mt-1 flex items-center gap-2">
              <AdminStatusBadge :status="plan.is_active ? 'active' : 'inactive'" type="active-inactive" />
              <span
                v-if="plan.is_featured"
                class="inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-400"
              >
                Featured
              </span>
            </div>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Sort Order</p>
            <p class="mt-1 text-sm text-foreground">{{ plan.sort_order }}</p>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════ -->
      <!--  Access Entries (10.4.7)                                               -->
      <!-- ═══════════════════════════════════════════════════════════════════════ -->

      <div class="mb-4 flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold text-foreground">Access Entries</h3>
          <p class="text-xs text-muted-foreground">
            Define feature keys and values for this plan. {{ plan.access_entries.length }} entries.
          </p>
        </div>
        <button type="button" class="btn-primary inline-flex items-center gap-2 text-sm" @click="openAddEntryModal">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
          </svg>
          Add Entry
        </button>
      </div>

      <AdminDataTable
        :columns="entryColumns"
        :rows="plan.access_entries"
        :meta="null"
        :loading="false"
        :clickable="false"
        row-key="id"
        empty-message="No access entries"
        empty-description="Add access entries to define what features this plan provides."
        @sort="handleEntrySort"
      >
        <!-- Key cell -->
        <template #cell-key="{ row }">
          <code class="rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-foreground">{{ row.key }}</code>
        </template>

        <!-- Value cell -->
        <template #cell-value="{ row }">
          <span class="text-sm font-medium text-foreground">{{ row.value }}</span>
        </template>

        <!-- Value type cell -->
        <template #cell-value_type="{ row }">
          <span
            class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold"
            :class="
              row.value_type === 'boolean'
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-400'
                : row.value_type === 'integer'
                  ? 'bg-purple-100 text-purple-700 dark:bg-purple-950 dark:text-purple-400'
                  : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
            "
          >
            {{ row.value_type }}
          </span>
        </template>

        <!-- Description cell -->
        <template #cell-description="{ row }">
          <span class="text-sm text-muted-foreground">{{ row.description || "—" }}</span>
        </template>

        <!-- Actions cell -->
        <template #cell-actions="{ row }">
          <div class="flex items-center justify-end gap-1">
            <button
              type="button"
              class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              title="Edit"
              @click="openEditEntryModal(row)"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </button>
            <button
              type="button"
              class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950 dark:hover:text-red-400"
              title="Delete"
              @click="openDeleteEntryDialog(row)"
            >
              <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          </div>
        </template>
      </AdminDataTable>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Edit Plan Modal                                                        -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showEditModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditModal = false" />
        <div class="relative w-full max-w-xl rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Edit Plan</h2>
          <form class="mt-5 space-y-4" @submit.prevent="handleEditSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Name <span class="text-destructive">*</span></label>
              <input v-model="editForm.name" type="text" class="input-field" required />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Slug</label>
              <input v-model="editForm.slug" type="text" class="input-field" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Price</label>
                <input v-model.number="editForm.priceDollars" type="number" step="0.01" min="0" class="input-field" />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Currency</label>
                <select v-model="editForm.currency" class="input-field">
                  <option value="usd">USD</option>
                  <option value="eur">EUR</option>
                  <option value="gbp">GBP</option>
                  <option value="bdt">BDT</option>
                </select>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Billing Cycle</label>
                <select v-model="editForm.billing_cycle" class="input-field">
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Trial Days</label>
                <input v-model.number="editForm.trial_days" type="number" min="0" class="input-field" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="flex items-center gap-2">
                <input v-model="editForm.is_featured" type="checkbox" class="h-4 w-4 rounded border-border" />
                <label class="text-sm font-medium text-foreground">Featured</label>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Sort Order</label>
                <input v-model.number="editForm.sort_order" type="number" min="0" class="input-field" />
              </div>
            </div>
            <div v-if="editError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ editError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="editLoading" @click="showEditModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="editLoading">Update Plan</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Add Access Entry Modal                                                 -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showAddEntryModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showAddEntryModal = false" />
        <div class="relative w-full max-w-xl rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Add Access Entry</h2>
          <p class="mt-1 text-sm text-muted-foreground">Define a feature key and its value for this plan.</p>
          <form class="mt-5 space-y-4" @submit.prevent="handleAddEntry">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Key <span class="text-destructive">*</span></label>
              <input v-model="addEntryForm.key" type="text" class="input-field" placeholder="e.g. max_projects" required />
              <p class="mt-1 text-xs text-muted-foreground">Use snake_case for consistency (e.g. max_projects, reports_enabled).</p>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Value <span class="text-destructive">*</span></label>
              <input v-model="addEntryForm.value" type="text" class="input-field" placeholder="e.g. true, 10, unlimited" required />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Value Type</label>
              <select v-model="addEntryForm.value_type" class="input-field">
                <option value="boolean">Boolean</option>
                <option value="integer">Integer</option>
                <option value="string">String</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Description</label>
              <input v-model="addEntryForm.description" type="text" class="input-field" placeholder="What this access key controls" />
            </div>
            <div v-if="addEntryError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ addEntryError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="addEntryLoading" @click="showAddEntryModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="addEntryLoading">Add Entry</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Edit Access Entry Modal                                                -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showEditEntryModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditEntryModal = false" />
        <div class="relative w-full max-w-xl rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Edit Access Entry</h2>
          <form class="mt-5 space-y-4" @submit.prevent="handleEditEntrySubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Key</label>
              <input v-model="editEntryForm.key" type="text" class="input-field" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Value</label>
              <input v-model="editEntryForm.value" type="text" class="input-field" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Value Type</label>
              <select v-model="editEntryForm.value_type" class="input-field">
                <option value="boolean">Boolean</option>
                <option value="integer">Integer</option>
                <option value="string">String</option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Description</label>
              <input v-model="editEntryForm.description" type="text" class="input-field" />
            </div>
            <div v-if="editEntryError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ editEntryError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="editEntryLoading" @click="showEditEntryModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="editEntryLoading">Update Entry</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Confirmation Dialogs                                                   -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <AdminConfirmDialog
      v-model:open="showDeletePlanDialog"
      title="Delete Plan"
      :message="'Delete plan \'' + (plan?.name ?? '') + '\'?'"
      detail="Only plans with no active subscribers can be deleted."
      confirm-label="Delete"
      :destructive="true"
      :loading="actionLoading === 'delete-plan'"
      @confirm="confirmDeletePlan"
    />

    <AdminConfirmDialog
      v-model:open="showDeleteEntryDialog"
      title="Remove Access Entry"
      :message="'Remove access key \'' + (deletingEntry?.key ?? '') + '\'?'"
      detail="This will immediately affect the access map returned by auth/me for subscribers on this plan."
      confirm-label="Remove"
      :destructive="true"
      :loading="actionLoading?.startsWith('delete-entry-')"
      @confirm="confirmDeleteEntry"
    />
  </div>
</template>
