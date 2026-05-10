<script setup lang="ts">
/**
 * ProductDetailAdmin — Product detail page for /admin/products/:id.
 *
 * Features:
 *   - Product info card with edit/toggle/delete actions
 *   - Tab navigation: Plans | Domains | Access Matrix
 *   - Plans tab: data table of plans with actions (view, edit, toggle, duplicate, delete)
 *   - Domains tab: list of service domains with add/edit/remove
 *   - Access Matrix tab: feature comparison across all plans
 *   - Create plan modal
 *   - Add domain modal
 *
 * Uses 10.2 components: AdminPageHeader, AdminDataTable, AdminFilterBar,
 * AdminConfirmDialog, AdminStatusBadge, AdminFeatureMatrix.
 */

import { ref, computed, onMounted, watch, onUnmounted } from "vue";
import { requireAuth, getErrorMessage } from "@/lib/auth";
import { showToast } from "@/lib/toast";
import { adminApi, formatDateTime } from "@/lib/admin";
import type {
  ProductDetail,
  ProductUpdatePayload,
  PlanItem,
  PlanCreatePayload,
  PlanUpdatePayload,
  ServiceDomainDetail,
  ServiceDomainCreatePayload,
  ServiceDomainUpdatePayload,
  PaginationMeta,
  AccessMatrixResponse,
  AccessMatrixRow,
  AccessEntryCreatePayload,
  AccessEntryUpdatePayload,
} from "@/lib/admin";

import AdminPageHeader from "@/components/admin/AdminPageHeader.vue";
import AdminDataTable from "@/components/admin/AdminDataTable.vue";
import type { ColumnDef } from "@/components/admin/AdminDataTable.vue";
import AdminConfirmDialog from "@/components/admin/AdminConfirmDialog.vue";
import AdminStatusBadge from "@/components/admin/AdminStatusBadge.vue";
import AdminFeatureMatrix from "@/components/admin/AdminFeatureMatrix.vue";

// ─── Props & Route ID ────────────────────────────────────────────────────────
//
// With Astro ClientRouter (View Transitions) + client:only="vue", the Astro
// prop can become undefined during client-side page swaps.  We therefore read
// the product ID from the URL path as the primary source, with the Astro prop
// as a fallback for direct (full-page) loads.

const props = defineProps<{
  productId?: number;
}>();

/** Extract product ID from /admin/products/:id URL path. */
function getProductIdFromUrl(): number | undefined {
  const match = window.location.pathname.match(/\/admin\/products\/(\d+)/);
  return match ? Number(match[1]) : undefined;
}

const productId = computed(() => {
  // URL is the most reliable source during View Transition navigations
  const fromUrl = getProductIdFromUrl();
  if (fromUrl) return fromUrl;
  // Fallback to Astro prop (works on direct full-page loads)
  return props.productId;
});

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true);
const loadError = ref<string | null>(null);
const actionLoading = ref<string | null>(null);

const product = ref<ProductDetail | null>(null);
const activeTab = ref<"plans" | "domains" | "matrix">("plans");

// Plans state
const plansMeta = ref<PaginationMeta>({
  total_items: 0,
  total_pages: 1,
  current_page: 1,
  page_size: 20,
  has_next: false,
  has_previous: false,
});
const plansCurrentPage = ref(1);

// Access matrix
const matrixData = ref<AccessMatrixResponse | null>(null);
const matrixLoading = ref(false);

// Edit product modal
const showEditModal = ref(false);
const editLoading = ref(false);
const editError = ref<string | null>(null);
const editForm = ref({
  name: "",
  slug: "",
  description: "",
  home_url: "",
});

// Create plan modal
const showCreatePlanModal = ref(false);
const createPlanLoading = ref(false);
const createPlanError = ref<string | null>(null);
const createPlanForm = ref({
  name: "",
  slug: "",
  priceDollars: 0,
  currency: "usd",
  billing_cycle: "monthly" as "monthly" | "yearly",
  trial_days: 0,
  is_featured: false,
  sort_order: 0,
});

// Edit plan modal
const showEditPlanModal = ref(false);
const editPlanLoading = ref(false);
const editPlanError = ref<string | null>(null);
const editingPlan = ref<PlanItem | null>(null);
const editPlanForm = ref({
  name: "",
  slug: "",
  priceDollars: 0,
  currency: "usd",
  billing_cycle: "monthly" as "monthly" | "yearly",
  trial_days: 0,
  is_featured: false,
  sort_order: 0,
});

// Add domain modal
const showAddDomainModal = ref(false);
const addDomainLoading = ref(false);
const addDomainError = ref<string | null>(null);
const addDomainForm = ref({
  domain: "",
  is_primary: false,
});

// Edit domain modal
const showEditDomainModal = ref(false);
const editDomainLoading = ref(false);
const editDomainError = ref<string | null>(null);
const editingDomain = ref<ServiceDomainDetail | null>(null);
const editDomainForm = ref({
  domain: "",
  is_primary: false,
  is_active: true,
});

// Confirmation dialogs
const showDeleteProductDialog = ref(false);
const showDeletePlanDialog = ref(false);
const deletingPlan = ref<PlanItem | null>(null);
const showDeleteDomainDialog = ref(false);
const deletingDomain = ref<ServiceDomainDetail | null>(null);

// ─── Access Entry CRUD ────────────────────────────────────────────────────────

// Add access entry modal
const showAddEntryModal = ref(false);
const addEntryLoading = ref(false);
const addEntryError = ref<string | null>(null);
const addEntryForm = ref<{
  planId: number | null;
  key: string;
  value: string;
  value_type: "boolean" | "integer" | "string";
  description: string;
}>({
  planId: null,
  key: "",
  value: "true",
  value_type: "boolean",
  description: "",
});

// Edit access entry modal (cell-level edit)
const showEditEntryModal = ref(false);
const editEntryLoading = ref(false);
const editEntryError = ref<string | null>(null);
const editingEntryId = ref<number | null>(null); // existing entry ID if updating
const editingEntryPlanSlug = ref<string>("");
const editingEntryRow = ref<AccessMatrixRow | null>(null);
const editEntryForm = ref<{
  planId: number | null;
  key: string;
  value: string;
  value_type: "boolean" | "integer" | "string";
  description: string;
}>({
  planId: null,
  key: "",
  value: "true",
  value_type: "boolean",
  description: "",
});

// Delete access entry dialog
const showDeleteEntryDialog = ref(false);
const deletingEntryRow = ref<AccessMatrixRow | null>(null);
const deletingEntryIds = ref<number[]>([]); // entry IDs for this key across plans

// Helper: look up plan ID from slug using product data
function planSlugToId(slug: string): number | null {
  if (!product.value) return null;
  const plan = product.value.plans.find((p) => p.slug === slug);
  return plan?.id ?? null;
}

// Helper: look up plan name from slug
function planSlugToName(slug: string): string {
  if (!matrixData.value) return slug;
  const plan = matrixData.value.plans.find((p) => p.slug === slug);
  return plan?.name ?? slug;
}

// ─── Column definitions: Plans ───────────────────────────────────────────────

const planColumns = computed<ColumnDef[]>(() => [
  { key: "name", label: "Plan", sortable: true },
  { key: "price_cents", label: "Price", align: "right", width: "100px" },
  { key: "billing_cycle", label: "Cycle", width: "80px", hideOnMobile: true },
  { key: "subscriber_count", label: "Subs", align: "center", width: "70px" },
  { key: "is_active", label: "Status", align: "center", width: "90px" },
  { key: "actions", label: "", align: "right", width: "180px" },
]);

// ─── Data fetching ───────────────────────────────────────────────────────────

async function fetchProduct() {
  const id = productId.value;
  if (!id) {
    loadError.value = "Invalid product ID.";
    loading.value = false;
    return;
  }
  loading.value = true;
  loadError.value = null;
  try {
    product.value = await adminApi.getProduct(id);
  } catch (err) {
    loadError.value = getErrorMessage(err);
  } finally {
    loading.value = false;
  }
}

async function fetchMatrix() {
  const id = productId.value;
  if (!id) return;
  matrixLoading.value = true;
  try {
    matrixData.value = await adminApi.getAccessMatrix(id);
  } catch (err) {
    console.warn("Failed to load access matrix:", err);
  } finally {
    matrixLoading.value = false;
  }
}

onMounted(async () => {
  if (!requireAuth()) return;
  await fetchProduct();
});

// Re-fetch when navigating between product detail pages via View Transitions.
// astro:page-load fires on every navigation (initial + client-side swaps).
function handlePageLoad() {
  const newId = getProductIdFromUrl();
  if (newId && newId !== product.value?.id) {
    // Reset state for the new product
    activeTab.value = "plans";
    matrixData.value = null;
    fetchProduct();
  }
}
document.addEventListener("astro:page-load", handlePageLoad);
onUnmounted(() => {
  document.removeEventListener("astro:page-load", handlePageLoad);
});

// Fetch matrix when tab is selected
watch(activeTab, (tab) => {
  if (tab === "matrix" && !matrixData.value) {
    fetchMatrix();
  }
});

// ─── Plan navigation ─────────────────────────────────────────────────────────

function handlePlanRowClick(row: Record<string, unknown>) {
  const plan = row as PlanItem;
  window.location.href = `/admin/plans/${plan.id}`;
}

// ─── Format price ────────────────────────────────────────────────────────────

function formatCents(cents: number, currency: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: currency?.toUpperCase() || "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

/** Convert dollars to cents for API submission. */
function dollarsToCents(dollars: number): number {
  return Math.round(dollars * 100);
}

/** Convert cents to dollars for form display. */
function centsToDollars(cents: number): number {
  return cents / 100;
}

// ─── Edit Product ────────────────────────────────────────────────────────────

function openEditModal() {
  if (!product.value) return;
  editForm.value = {
    name: product.value.name,
    slug: product.value.slug,
    description: product.value.description || "",
    home_url: product.value.home_url || "",
  };
  editError.value = null;
  showEditModal.value = true;
}

async function handleEditSubmit() {
  editLoading.value = true;
  editError.value = null;
  try {
    const payload: ProductUpdatePayload = {
      name: editForm.value.name,
      slug: editForm.value.slug,
      description: editForm.value.description || undefined,
      home_url: editForm.value.home_url || undefined,
    };
    await adminApi.updateProduct(productId.value!, payload);
    showToast("Product updated.", "success");
    showEditModal.value = false;
    await fetchProduct();
  } catch (err) {
    editError.value = getErrorMessage(err);
  } finally {
    editLoading.value = false;
  }
}

// ─── Toggle Product ──────────────────────────────────────────────────────────

async function handleToggleProduct() {
  if (!product.value) return;
  actionLoading.value = "toggle-product";
  try {
    await adminApi.toggleProduct(productId.value!);
    showToast(
      `Product ${product.value.is_active ? "deactivated" : "activated"}.`,
      "success"
    );
    await fetchProduct();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

// ─── Delete Product ──────────────────────────────────────────────────────────

async function confirmDeleteProduct() {
  actionLoading.value = "delete-product";
  try {
    await adminApi.deleteProduct(productId.value!);
    showToast("Product deleted.", "success");
    showDeleteProductDialog.value = false;
    window.location.href = "/admin/products";
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

// ─── Create Plan ─────────────────────────────────────────────────────────────

function openCreatePlanModal() {
  createPlanForm.value = {
    name: "",
    slug: "",
    priceDollars: 0,
    currency: "usd",
    billing_cycle: "monthly",
    trial_days: 0,
    is_featured: false,
    sort_order: 0,
  };
  createPlanError.value = null;
  showCreatePlanModal.value = true;
}

function handlePlanNameInput() {
  createPlanForm.value.slug = createPlanForm.value.name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

async function handleCreatePlan() {
  createPlanLoading.value = true;
  createPlanError.value = null;
  try {
    const payload: PlanCreatePayload = {
      name: createPlanForm.value.name,
      slug: createPlanForm.value.slug || undefined,
      price_cents: dollarsToCents(createPlanForm.value.priceDollars),
      currency: createPlanForm.value.currency || undefined,
      billing_cycle: createPlanForm.value.billing_cycle,
      trial_days: createPlanForm.value.trial_days || undefined,
      is_featured: createPlanForm.value.is_featured || undefined,
      sort_order: createPlanForm.value.sort_order || undefined,
    };
    await adminApi.createPlan(productId.value!, payload);
    showToast("Plan created.", "success");
    showCreatePlanModal.value = false;
    await fetchProduct();
  } catch (err) {
    createPlanError.value = getErrorMessage(err);
  } finally {
    createPlanLoading.value = false;
  }
}

// ─── Edit Plan ───────────────────────────────────────────────────────────────

function openEditPlanModal(plan: PlanItem) {
  editingPlan.value = plan;
  editPlanForm.value = {
    name: plan.name,
    slug: plan.slug,
    priceDollars: centsToDollars(plan.price_cents),
    currency: plan.currency,
    billing_cycle: plan.billing_cycle,
    trial_days: plan.trial_days,
    is_featured: plan.is_featured,
    sort_order: plan.sort_order,
  };
  editPlanError.value = null;
  showEditPlanModal.value = true;
}

async function handleEditPlanSubmit() {
  if (!editingPlan.value) return;
  editPlanLoading.value = true;
  editPlanError.value = null;
  try {
    const payload: PlanUpdatePayload = {
      name: editPlanForm.value.name,
      slug: editPlanForm.value.slug,
      price_cents: dollarsToCents(editPlanForm.value.priceDollars),
      currency: editPlanForm.value.currency,
      billing_cycle: editPlanForm.value.billing_cycle,
      trial_days: editPlanForm.value.trial_days,
      is_featured: editPlanForm.value.is_featured,
      sort_order: editPlanForm.value.sort_order,
    };
    await adminApi.updatePlan(editingPlan.value.id, payload);
    showToast("Plan updated.", "success");
    showEditPlanModal.value = false;
    await fetchProduct();
  } catch (err) {
    editPlanError.value = getErrorMessage(err);
  } finally {
    editPlanLoading.value = false;
  }
}

// ─── Plan actions ────────────────────────────────────────────────────────────

async function handleTogglePlan(plan: PlanItem) {
  actionLoading.value = `toggle-plan-${plan.id}`;
  try {
    await adminApi.togglePlan(plan.id);
    showToast(`Plan ${plan.is_active ? "deactivated" : "activated"}.`, "success");
    await fetchProduct();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function handleTogglePlanFeature(plan: PlanItem) {
  actionLoading.value = `feature-plan-${plan.id}`;
  try {
    await adminApi.togglePlanFeature(plan.id);
    showToast(`Plan ${plan.is_featured ? "unfeatured" : "featured"}.`, "success");
    await fetchProduct();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

async function handleDuplicatePlan(plan: PlanItem) {
  actionLoading.value = `dup-plan-${plan.id}`;
  try {
    await adminApi.duplicatePlan(plan.id);
    showToast("Plan duplicated.", "success");
    await fetchProduct();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

function openDeletePlanDialog(plan: PlanItem) {
  deletingPlan.value = plan;
  showDeletePlanDialog.value = true;
}

async function confirmDeletePlan() {
  if (!deletingPlan.value) return;
  actionLoading.value = `delete-plan-${deletingPlan.value.id}`;
  try {
    await adminApi.deletePlan(deletingPlan.value.id);
    showToast("Plan deleted.", "success");
    showDeletePlanDialog.value = false;
    deletingPlan.value = null;
    await fetchProduct();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

// ─── Domain actions ──────────────────────────────────────────────────────────

function openAddDomainModal() {
  addDomainForm.value = { domain: "", is_primary: false };
  addDomainError.value = null;
  showAddDomainModal.value = true;
}

async function handleAddDomain() {
  addDomainLoading.value = true;
  addDomainError.value = null;
  try {
    const payload: ServiceDomainCreatePayload = {
      domain: addDomainForm.value.domain,
      is_primary: addDomainForm.value.is_primary || undefined,
    };
    await adminApi.addServiceDomain(productId.value!, payload);
    showToast("Domain added.", "success");
    showAddDomainModal.value = false;
    await fetchProduct();
  } catch (err) {
    addDomainError.value = getErrorMessage(err);
  } finally {
    addDomainLoading.value = false;
  }
}

function openEditDomainModal(domain: ServiceDomainDetail) {
  editingDomain.value = domain;
  editDomainForm.value = {
    domain: domain.domain,
    is_primary: domain.is_primary,
    is_active: domain.is_active,
  };
  editDomainError.value = null;
  showEditDomainModal.value = true;
}

async function handleEditDomainSubmit() {
  if (!editingDomain.value) return;
  editDomainLoading.value = true;
  editDomainError.value = null;
  try {
    const payload: ServiceDomainUpdatePayload = {
      domain: editDomainForm.value.domain,
      is_primary: editDomainForm.value.is_primary,
      is_active: editDomainForm.value.is_active,
    };
    await adminApi.updateServiceDomain(editingDomain.value.id, payload);
    showToast("Domain updated.", "success");
    showEditDomainModal.value = false;
    await fetchProduct();
  } catch (err) {
    editDomainError.value = getErrorMessage(err);
  } finally {
    editDomainLoading.value = false;
  }
}

function openDeleteDomainDialog(domain: ServiceDomainDetail) {
  deletingDomain.value = domain;
  showDeleteDomainDialog.value = true;
}

async function confirmDeleteDomain() {
  if (!deletingDomain.value) return;
  actionLoading.value = `delete-domain-${deletingDomain.value.id}`;
  try {
    await adminApi.deleteServiceDomain(deletingDomain.value.id);
    showToast("Domain removed.", "success");
    showDeleteDomainDialog.value = false;
    deletingDomain.value = null;
    await fetchProduct();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

// ─── Plans sort ──────────────────────────────────────────────────────────────

function handlePlanSort({ key, direction }: { key: string; direction: "asc" | "desc" }) {
  if (!product.value) return;
  product.value.plans.sort((a, b) => {
    const aVal = (a as Record<string, unknown>)[key];
    const bVal = (b as Record<string, unknown>)[key];
    if (aVal == null || bVal == null) return 0;
    const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
    return direction === "asc" ? cmp : -cmp;
  });
}

// ─── Access Entry CRUD ──────────────────────────────────────────────────────

/** Open the "Add Feature" modal */
function openAddEntryModal() {
  if (!product.value?.plans.length) {
    showToast("Create a plan first before adding features.", "error");
    return;
  }
  addEntryForm.value = {
    planId: product.value.plans[0].id,
    key: "",
    value: "true",
    value_type: "boolean",
    description: "",
  };
  addEntryError.value = null;
  showAddEntryModal.value = true;
}

/** Handle add-entry form submit */
async function handleAddEntry() {
  if (!addEntryForm.value.planId) {
    addEntryError.value = "Select a plan.";
    return;
  }
  addEntryLoading.value = true;
  addEntryError.value = null;
  try {
    const payload: AccessEntryCreatePayload = {
      key: addEntryForm.value.key,
      value: addEntryForm.value.value,
      value_type: addEntryForm.value.value_type,
      description: addEntryForm.value.description || undefined,
    };
    await adminApi.addAccessEntry(addEntryForm.value.planId, payload);
    showToast("Feature added.", "success");
    showAddEntryModal.value = false;
    await fetchMatrix();
  } catch (err) {
    addEntryError.value = getErrorMessage(err);
  } finally {
    addEntryLoading.value = false;
  }
}

/** Handle cell click — edit the value for a specific plan+key */
function handleEditCell(row: AccessMatrixRow, planSlug: string) {
  const planId = planSlugToId(planSlug);
  if (!planId) {
    showToast("Could not resolve plan.", "error");
    return;
  }

  // Use entry_ids from the matrix row — no extra API call needed
  const entryId = row.entry_ids?.[planSlug] ?? null;
  const currentValue = row.values[planSlug] ?? null;

  editingEntryRow.value = row;
  editingEntryPlanSlug.value = planSlug;
  editingEntryId.value = entryId;

  if (entryId) {
    // ── Update existing entry ──
    // Infer value_type from the current value
    let inferredType: "boolean" | "integer" | "string" = "string";
    if (currentValue !== null) {
      const lower = String(currentValue).toLowerCase();
      if (lower === "true" || lower === "false" || lower === "0" || lower === "1") {
        inferredType = "boolean";
      } else if (/^-?\d+$/.test(String(currentValue))) {
        inferredType = "integer";
      }
    }
    editEntryForm.value = {
      planId,
      key: row.key,
      value: currentValue ?? "true",
      value_type: inferredType,
      description: row.description || "",
    };
  } else {
    // ── Create new entry for this plan+key ──
    editEntryForm.value = {
      planId,
      key: row.key,
      value: "true",
      value_type: "boolean",
      description: row.description || "",
    };
  }

  editEntryError.value = null;
  showEditEntryModal.value = true;
}

/** Handle "edit row" — edit the key/description for a feature row */
function handleEditRow(row: AccessMatrixRow) {
  if (!matrixData.value?.plans.length) return;

  // Pick the first plan that has an entry ID for this key
  let targetSlug = matrixData.value.plans[0].slug;

  for (const plan of matrixData.value.plans) {
    if (row.entry_ids?.[plan.slug]) {
      targetSlug = plan.slug;
      break;
    }
  }

  handleEditCell(row, targetSlug);
}

/** Handle edit-entry form submit */
async function handleEditEntrySubmit() {
  if (!editEntryForm.value.planId) {
    editEntryError.value = "Plan not resolved.";
    return;
  }
  editEntryLoading.value = true;
  editEntryError.value = null;
  try {
    if (editingEntryId.value) {
      // Update existing entry (PUT /admin/access-entries/{id})
      const payload: AccessEntryUpdatePayload = {
        key: editEntryForm.value.key,
        value: editEntryForm.value.value,
        value_type: editEntryForm.value.value_type,
        description: editEntryForm.value.description || undefined,
      };
      await adminApi.updateAccessEntry(editingEntryId.value, payload);
      showToast("Feature updated.", "success");
    } else {
      // Create new entry (POST /admin/plans/{id}/access-entries)
      const payload: AccessEntryCreatePayload = {
        key: editEntryForm.value.key,
        value: editEntryForm.value.value,
        value_type: editEntryForm.value.value_type,
        description: editEntryForm.value.description || undefined,
      };
      await adminApi.addAccessEntry(editEntryForm.value.planId, payload);
      showToast("Feature added.", "success");
    }
    showEditEntryModal.value = false;
    await fetchMatrix();
  } catch (err) {
    editEntryError.value = getErrorMessage(err);
  } finally {
    editEntryLoading.value = false;
  }
}

/** Handle "delete row" — delete the key from all plans */
function handleDeleteRow(row: AccessMatrixRow) {
  deletingEntryRow.value = row;

  // Collect entry IDs directly from the matrix row's entry_ids map
  const ids: number[] = [];
  if (row.entry_ids) {
    for (const [planSlug, entryId] of Object.entries(row.entry_ids)) {
      if (entryId !== null && entryId !== undefined) {
        ids.push(entryId);
      }
    }
  }
  deletingEntryIds.value = ids;
  showDeleteEntryDialog.value = true;
}

/** Confirm deletion of all entries for a key */
async function confirmDeleteEntries() {
  if (!deletingEntryIds.value.length) return;
  actionLoading.value = "delete-entries";
  try {
    for (const id of deletingEntryIds.value) {
      await adminApi.deleteAccessEntry(id);
    }
    showToast("Feature removed from all plans.", "success");
    showDeleteEntryDialog.value = false;
    deletingEntryRow.value = null;
    deletingEntryIds.value = [];
    await fetchMatrix();
  } catch (err) {
    showToast(getErrorMessage(err), "error");
  } finally {
    actionLoading.value = null;
  }
}

/** When value_type changes, auto-set a sensible default value */
function handleValueTypeChange(formRef: typeof addEntryForm | typeof editEntryForm) {
  switch (formRef.value.value_type) {
    case "boolean":
      formRef.value.value = "true";
      break;
    case "integer":
      formRef.value.value = "0";
      break;
    case "string":
      formRef.value.value = "";
      break;
  }
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
      <p class="font-medium text-foreground">Failed to load product</p>
      <p class="text-sm text-muted-foreground">{{ loadError }}</p>
      <button type="button" class="btn-secondary" @click="fetchProduct">Try again</button>
    </div>

    <!-- Product detail -->
    <template v-else-if="product">
      <!-- Page Header -->
      <AdminPageHeader
        :title="product.name"
        :description="product.description || 'Product management'"
        :breadcrumbs="[
          { label: 'Admin', href: '/admin' },
          { label: 'Products', href: '/admin/products' },
          { label: product.name },
        ]"
      >
        <template #secondary-action>
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
        </template>
        <template #primary-action>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2"
              :disabled="actionLoading === 'toggle-product'"
              @click="handleToggleProduct"
            >
              <svg v-if="actionLoading === 'toggle-product'" class="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              {{ product.is_active ? "Deactivate" : "Activate" }}
            </button>
            <button
              type="button"
              class="btn-secondary inline-flex items-center gap-2 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950"
              @click="showDeleteProductDialog = true"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </button>
          </div>
        </template>
      </AdminPageHeader>

      <!-- Info Card -->
      <div class="card p-5">
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Slug</p>
            <p class="mt-1 text-sm font-medium text-foreground">{{ product.slug }}</p>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Status</p>
            <div class="mt-1">
              <AdminStatusBadge :status="product.is_active ? 'active' : 'inactive'" type="active-inactive" />
            </div>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Home URL</p>
            <p class="mt-1 text-sm text-foreground">
              <a
                v-if="product.home_url"
                :href="product.home_url"
                class="text-brand-600 hover:underline dark:text-brand-400"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ product.home_url }}
              </a>
              <span v-else class="text-muted-foreground">—</span>
            </p>
          </div>
          <div>
            <p class="text-xs font-medium uppercase text-muted-foreground">Created</p>
            <p class="mt-1 text-sm text-foreground">{{ formatDateTime(product.created_at) }}</p>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════ -->
      <!--  Tab Navigation                                                        -->
      <!-- ═══════════════════════════════════════════════════════════════════════ -->

      <div class="border-b border-border">
        <nav class="flex gap-6" aria-label="Product tabs">
          <button
            v-for="tab in (['plans', 'domains', 'matrix'] as const)"
            :key="tab"
            class="border-b-2 pb-3 text-sm font-medium transition-colors"
            :class="
              activeTab === tab
                ? 'border-brand-600 text-brand-600 dark:border-brand-400 dark:text-brand-400'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            "
            @click="activeTab = tab"
          >
            {{ tab === 'plans' ? 'Plans' : tab === 'domains' ? 'Domains' : 'Access Matrix' }}
            <span
              v-if="tab === 'plans' && product.plans.length"
              class="ml-1.5 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-muted px-1.5 text-[10px] font-semibold text-foreground"
            >
              {{ product.plans.length }}
            </span>
            <span
              v-if="tab === 'domains' && product.service_domains.length"
              class="ml-1.5 inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-muted px-1.5 text-[10px] font-semibold text-foreground"
            >
              {{ product.service_domains.length }}
            </span>
          </button>
        </nav>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════ -->
      <!--  Plans Tab (10.4.4)                                                    -->
      <!-- ═══════════════════════════════════════════════════════════════════════ -->

      <div v-if="activeTab === 'plans'">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-foreground">Plans</h3>
          <button type="button" class="btn-primary inline-flex items-center gap-2 text-sm" @click="openCreatePlanModal">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            New Plan
          </button>
        </div>

        <AdminDataTable
          :columns="planColumns"
          :rows="product.plans"
          :meta="null"
          :loading="false"
          :clickable="true"
          row-key="id"
          empty-message="No plans yet"
          empty-description="Create your first plan for this product."
          @row-click="handlePlanRowClick"
          @sort="handlePlanSort"
        >
          <!-- Plan name cell -->
          <template #cell-name="{ row }">
            <div>
              <p class="font-medium text-foreground">{{ row.name }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span v-if="row.is_featured" class="inline-flex items-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-400">
                  Featured
                </span>
                <span class="text-xs text-muted-foreground">{{ row.slug }}</span>
              </div>
            </div>
          </template>

          <!-- Price cell -->
          <template #cell-price_cents="{ row }">
            <span class="font-medium text-foreground">{{ formatCents(row.price_cents, row.currency) }}</span>
          </template>

          <!-- Status cell -->
          <template #cell-is_active="{ row }">
            <AdminStatusBadge :status="row.is_active ? 'active' : 'inactive'" type="active-inactive" />
          </template>

          <!-- Actions cell -->
          <template #cell-actions="{ row }">
            <div class="flex items-center justify-end gap-1" @click.stop>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                title="Edit"
                @click="openEditPlanModal(row)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                :title="row.is_featured ? 'Unfeature' : 'Feature'"
                :disabled="actionLoading === `feature-plan-${row.id}`"
                @click="handleTogglePlanFeature(row)"
              >
                <svg class="h-3.5 w-3.5" :class="row.is_featured ? 'text-amber-500' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
              </button>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                title="Duplicate"
                :disabled="actionLoading === `dup-plan-${row.id}`"
                @click="handleDuplicatePlan(row)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </button>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                :title="row.is_active ? 'Deactivate' : 'Activate'"
                :disabled="actionLoading === `toggle-plan-${row.id}`"
                @click="handleTogglePlan(row)"
              >
                <svg v-if="row.is_active" class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                </svg>
                <svg v-else class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </button>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950 dark:hover:text-red-400"
                title="Delete"
                @click="openDeletePlanDialog(row)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </template>
        </AdminDataTable>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════ -->
      <!--  Domains Tab (10.4.5)                                                  -->
      <!-- ═══════════════════════════════════════════════════════════════════════ -->

      <div v-if="activeTab === 'domains'">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-foreground">Service Domains</h3>
          <button type="button" class="btn-primary inline-flex items-center gap-2 text-sm" @click="openAddDomainModal">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Domain
          </button>
        </div>

        <!-- Empty -->
        <div
          v-if="product.service_domains.length === 0"
          class="card flex flex-col items-center gap-3 p-8 text-center"
        >
          <svg class="h-8 w-8 text-muted-foreground/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
          </svg>
          <p class="text-sm text-muted-foreground">No service domains configured yet.</p>
        </div>

        <!-- Domain list -->
        <div v-else class="space-y-2">
          <div
            v-for="domain in product.service_domains"
            :key="domain.id"
            class="card flex items-center justify-between p-4"
          >
            <div class="flex items-center gap-3 min-w-0">
              <div
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                :class="
                  domain.is_active
                    ? 'bg-green-100 text-green-600 dark:bg-green-950 dark:text-green-400'
                    : 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
                "
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <div class="min-w-0">
                <p class="truncate font-medium text-foreground">{{ domain.domain }}</p>
                <div class="flex items-center gap-2 mt-0.5">
                  <span
                    v-if="domain.is_primary"
                    class="inline-flex items-center rounded-full bg-blue-100 px-1.5 py-0.5 text-[10px] font-semibold text-blue-700 dark:bg-blue-950 dark:text-blue-400"
                  >
                    Primary
                  </span>
                  <AdminStatusBadge :status="domain.is_active ? 'active' : 'inactive'" type="active-inactive" :dot="false" />
                </div>
              </div>
            </div>
            <div class="flex items-center gap-1 shrink-0" @click.stop>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                title="Edit"
                @click="openEditDomainModal(domain)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </button>
              <button
                type="button"
                class="inline-flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950 dark:hover:text-red-400"
                title="Remove"
                @click="openDeleteDomainDialog(domain)"
              >
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════════════════ -->
      <!--  Access Matrix Tab (10.4.8)                                            -->
      <!-- ═══════════════════════════════════════════════════════════════════════ -->

      <div v-if="activeTab === 'matrix'">
        <div class="mb-4 flex items-center justify-between">
          <div>
            <h3 class="text-sm font-semibold text-foreground">Feature Access Matrix</h3>
            <p class="text-xs text-muted-foreground">Click any cell to edit its value. Use row actions to modify or remove features.</p>
          </div>
          <button
            v-if="product.plans.length > 0"
            type="button"
            class="btn-primary inline-flex items-center gap-2 text-sm"
            @click="openAddEntryModal"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Feature
          </button>
        </div>

        <!-- Matrix loading -->
        <div v-if="matrixLoading" class="card animate-pulse p-6">
          <div class="space-y-4">
            <div class="h-4 w-40 rounded skeleton" />
            <div class="h-4 w-full rounded skeleton" />
            <div class="h-4 w-full rounded skeleton" />
          </div>
        </div>

        <AdminFeatureMatrix
          v-else-if="matrixData"
          :plans="matrixData.plans"
          :rows="matrixData.rows"
          :product-name="product.name"
          :loading="matrixLoading"
          :editable="true"
          @edit-cell="handleEditCell"
          @add-entry="openAddEntryModal"
          @edit-row="handleEditRow"
          @delete-row="handleDeleteRow"
        />

        <div
          v-else
          class="card flex flex-col items-center gap-3 p-8 text-center"
        >
          <svg class="h-8 w-8 text-muted-foreground/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
          <p class="text-sm text-muted-foreground">No access matrix data available.</p>
          <button
            v-if="product.plans.length > 0"
            type="button"
            class="btn-primary inline-flex items-center gap-2 text-sm mt-2"
            @click="openAddEntryModal"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add First Feature
          </button>
        </div>
      </div>
    </template>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Edit Product Modal                                                     -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showEditModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditModal = false" />
        <div class="relative w-full max-w-xl rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Edit Product</h2>
          <p class="mt-1 text-sm text-muted-foreground">Update product details below.</p>
          <form class="mt-5 space-y-4" @submit.prevent="handleEditSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Name <span class="text-destructive">*</span></label>
              <input v-model="editForm.name" type="text" class="input-field" required />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Slug</label>
              <input v-model="editForm.slug" type="text" class="input-field" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Description</label>
              <textarea v-model="editForm.description" class="input-field min-h-[80px]" rows="3" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Home URL</label>
              <input v-model="editForm.home_url" type="url" class="input-field" />
            </div>
            <div v-if="editError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ editError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="editLoading" @click="showEditModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="editLoading">
                <svg v-if="editLoading" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Update
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Create Plan Modal (10.4.6)                                             -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showCreatePlanModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showCreatePlanModal = false" />
        <div class="relative w-full max-w-xl rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">New Plan</h2>
          <p class="mt-1 text-sm text-muted-foreground">Create a new plan for {{ product?.name }}.</p>

          <form class="mt-5 space-y-4" @submit.prevent="handleCreatePlan">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Name <span class="text-destructive">*</span></label>
              <input v-model="createPlanForm.name" type="text" class="input-field" placeholder="e.g. Pro" required @input="handlePlanNameInput" />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Slug</label>
              <input v-model="createPlanForm.slug" type="text" class="input-field" placeholder="auto-generated from name" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Price <span class="text-destructive">*</span></label>
                <input v-model.number="createPlanForm.priceDollars" type="number" step="0.01" min="0" class="input-field" required />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Currency</label>
                <select v-model="createPlanForm.currency" class="input-field">
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
                <select v-model="createPlanForm.billing_cycle" class="input-field">
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Trial Days</label>
                <input v-model.number="createPlanForm.trial_days" type="number" min="0" class="input-field" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="flex items-center gap-2">
                <input v-model="createPlanForm.is_featured" type="checkbox" class="h-4 w-4 rounded border-border" />
                <label class="text-sm font-medium text-foreground">Featured</label>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Sort Order</label>
                <input v-model.number="createPlanForm.sort_order" type="number" min="0" class="input-field" />
              </div>
            </div>
            <div v-if="createPlanError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ createPlanError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="createPlanLoading" @click="showCreatePlanModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="createPlanLoading">
                <svg v-if="createPlanLoading" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Create Plan
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Edit Plan Modal                                                        -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showEditPlanModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditPlanModal = false" />
        <div class="relative w-full max-w-xl rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Edit Plan</h2>
          <p class="mt-1 text-sm text-muted-foreground">Update plan configuration for <span class="font-medium text-foreground">{{ editingPlan?.name }}</span>.</p>
          <form class="mt-5 space-y-4" @submit.prevent="handleEditPlanSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Name <span class="text-destructive">*</span></label>
              <input v-model="editPlanForm.name" type="text" class="input-field" required />
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Slug</label>
              <input v-model="editPlanForm.slug" type="text" class="input-field" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Price</label>
                <input v-model.number="editPlanForm.priceDollars" type="number" step="0.01" min="0" class="input-field" />
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Currency</label>
                <select v-model="editPlanForm.currency" class="input-field">
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
                <select v-model="editPlanForm.billing_cycle" class="input-field">
                  <option value="monthly">Monthly</option>
                  <option value="yearly">Yearly</option>
                </select>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Trial Days</label>
                <input v-model.number="editPlanForm.trial_days" type="number" min="0" class="input-field" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div class="flex items-center gap-2">
                <input v-model="editPlanForm.is_featured" type="checkbox" class="h-4 w-4 rounded border-border" />
                <label class="text-sm font-medium text-foreground">Featured</label>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Sort Order</label>
                <input v-model.number="editPlanForm.sort_order" type="number" min="0" class="input-field" />
              </div>
            </div>
            <div v-if="editPlanError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ editPlanError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="editPlanLoading" @click="showEditPlanModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="editPlanLoading">
                <svg v-if="editPlanLoading" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Update Plan
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Add Domain Modal                                                       -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showAddDomainModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showAddDomainModal = false" />
        <div class="relative w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Add Service Domain</h2>
          <p class="mt-1 text-sm text-muted-foreground">Register a domain that will authenticate against this product.</p>
          <form class="mt-5 space-y-4" @submit.prevent="handleAddDomain">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Domain <span class="text-destructive">*</span></label>
              <input v-model="addDomainForm.domain" type="text" class="input-field" placeholder="finance.sattabase.tld" required />
            </div>
            <div class="flex items-center gap-2">
              <input v-model="addDomainForm.is_primary" type="checkbox" class="h-4 w-4 rounded border-border" />
              <label class="text-sm font-medium text-foreground">Set as primary domain</label>
            </div>
            <div v-if="addDomainError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ addDomainError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="addDomainLoading" @click="showAddDomainModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="addDomainLoading">Add Domain</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Edit Domain Modal                                                      -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <Teleport to="body">
      <div
        v-if="showEditDomainModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditDomainModal = false" />
        <div class="relative w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl" role="dialog" aria-modal="true">
          <h2 class="text-lg font-semibold text-foreground">Edit Domain</h2>
          <form class="mt-5 space-y-4" @submit.prevent="handleEditDomainSubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Domain</label>
              <input v-model="editDomainForm.domain" type="text" class="input-field" />
            </div>
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2">
                <input v-model="editDomainForm.is_primary" type="checkbox" class="h-4 w-4 rounded border-border" />
                <label class="text-sm font-medium text-foreground">Primary</label>
              </div>
              <div class="flex items-center gap-2">
                <input v-model="editDomainForm.is_active" type="checkbox" class="h-4 w-4 rounded border-border" />
                <label class="text-sm font-medium text-foreground">Active</label>
              </div>
            </div>
            <div v-if="editDomainError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ editDomainError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="editDomainLoading" @click="showEditDomainModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="editDomainLoading">Update Domain</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Confirmation Dialogs                                                   -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <AdminConfirmDialog
      v-model:open="showDeleteProductDialog"
      title="Delete Product"
      :message="'Delete \'' + (product?.name ?? '') + '\'?'"
      detail="Only products with no active subscriptions can be deleted. This is a soft-delete operation."
      confirm-label="Delete"
      :destructive="true"
      :loading="actionLoading === 'delete-product'"
      @confirm="confirmDeleteProduct"
    />

    <AdminConfirmDialog
      v-model:open="showDeletePlanDialog"
      title="Delete Plan"
      :message="'Delete plan \'' + (deletingPlan?.name ?? '') + '\'?'"
      detail="Only plans with no active subscribers can be deleted."
      confirm-label="Delete"
      :destructive="true"
      :loading="actionLoading?.startsWith('delete-plan-')"
      @confirm="confirmDeletePlan"
    />

    <AdminConfirmDialog
      v-model:open="showDeleteDomainDialog"
      title="Remove Domain"
      :message="'Remove domain \'' + (deletingDomain?.domain ?? '') + '\'?'"
      detail="Services using this domain will lose access to auth/me endpoints."
      confirm-label="Remove"
      :destructive="true"
      :loading="actionLoading?.startsWith('delete-domain-')"
      @confirm="confirmDeleteDomain"
    />

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
          <h2 class="text-lg font-semibold text-foreground">Add Feature</h2>
          <p class="mt-1 text-sm text-muted-foreground">Add a new access entry to a plan. You can add the same key to other plans later.</p>
          <form class="mt-5 space-y-4" @submit.prevent="handleAddEntry">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Plan <span class="text-destructive">*</span></label>
              <select v-model="addEntryForm.planId" class="input-field" required>
                <option v-for="plan in product?.plans" :key="plan.id" :value="plan.id">
                  {{ plan.name }}
                </option>
              </select>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Key <span class="text-destructive">*</span></label>
              <input v-model="addEntryForm.key" type="text" class="input-field" placeholder="e.g. reports, max_accounts" required />
              <p class="mt-1 text-xs text-muted-foreground">A unique identifier for this feature within the plan.</p>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Value Type</label>
                <select v-model="addEntryForm.value_type" class="input-field" @change="handleValueTypeChange(addEntryForm)">
                  <option value="boolean">Boolean</option>
                  <option value="integer">Integer</option>
                  <option value="string">String</option>
                </select>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Value <span class="text-destructive">*</span></label>
                <!-- Boolean toggle -->
                <div v-if="addEntryForm.value_type === 'boolean'" class="flex items-center gap-3 h-[42px]">
                  <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors"
                    :class="
                      addEntryForm.value === 'true'
                        ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    "
                    @click="addEntryForm.value = 'true'"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    True
                  </button>
                  <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors"
                    :class="
                      addEntryForm.value === 'false'
                        ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    "
                    @click="addEntryForm.value = 'false'"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    False
                  </button>
                </div>
                <!-- Integer input -->
                <input v-else-if="addEntryForm.value_type === 'integer'" v-model="addEntryForm.value" type="number" class="input-field" placeholder="0" />
                <!-- String input -->
                <input v-else v-model="addEntryForm.value" type="text" class="input-field" placeholder="Feature value" />
              </div>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Description</label>
              <input v-model="addEntryForm.description" type="text" class="input-field" placeholder="Human-readable description of this feature" />
            </div>
            <div v-if="addEntryError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ addEntryError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="addEntryLoading" @click="showAddEntryModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="addEntryLoading">
                <svg v-if="addEntryLoading" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Add Feature
              </button>
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
          <h2 class="text-lg font-semibold text-foreground">
            {{ editingEntryId ? 'Edit Feature' : 'Add Feature to Plan' }}
          </h2>
          <p class="mt-1 text-sm text-muted-foreground">
            {{ editingEntryId
              ? `Editing '${editEntryForm.key}' for ${planSlugToName(editingEntryPlanSlug)}`
              : `Adding '${editEntryForm.key}' to ${planSlugToName(editingEntryPlanSlug)}`
            }}
          </p>
          <form class="mt-5 space-y-4" @submit.prevent="handleEditEntrySubmit">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Plan</label>
              <div class="input-field bg-muted/50 cursor-not-allowed opacity-70">
                {{ planSlugToName(editingEntryPlanSlug) }}
              </div>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Key <span class="text-destructive">*</span></label>
              <input v-model="editEntryForm.key" type="text" class="input-field" :disabled="!!editingEntryId" required />
              <p v-if="editingEntryId" class="mt-1 text-xs text-muted-foreground">Key cannot be changed for existing entries.</p>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Value Type</label>
                <select v-model="editEntryForm.value_type" class="input-field" @change="handleValueTypeChange(editEntryForm)">
                  <option value="boolean">Boolean</option>
                  <option value="integer">Integer</option>
                  <option value="string">String</option>
                </select>
              </div>
              <div>
                <label class="mb-1.5 block text-sm font-medium text-foreground">Value <span class="text-destructive">*</span></label>
                <!-- Boolean toggle -->
                <div v-if="editEntryForm.value_type === 'boolean'" class="flex items-center gap-3 h-[42px]">
                  <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors"
                    :class="
                      editEntryForm.value === 'true'
                        ? 'border-green-300 bg-green-50 text-green-700 dark:border-green-800 dark:bg-green-950 dark:text-green-400'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    "
                    @click="editEntryForm.value = 'true'"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    True
                  </button>
                  <button
                    type="button"
                    class="inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors"
                    :class="
                      editEntryForm.value === 'false'
                        ? 'border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-400'
                        : 'border-border text-muted-foreground hover:bg-muted'
                    "
                    @click="editEntryForm.value = 'false'"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                    False
                  </button>
                </div>
                <!-- Integer input -->
                <input v-else-if="editEntryForm.value_type === 'integer'" v-model="editEntryForm.value" type="number" class="input-field" />
                <!-- String input -->
                <input v-else v-model="editEntryForm.value" type="text" class="input-field" />
              </div>
            </div>
            <div>
              <label class="mb-1.5 block text-sm font-medium text-foreground">Description</label>
              <input v-model="editEntryForm.description" type="text" class="input-field" placeholder="Human-readable description" />
            </div>
            <div v-if="editEntryError" class="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950 dark:text-red-400">{{ editEntryError }}</div>
            <div class="flex items-center justify-end gap-3 pt-2">
              <button type="button" class="btn-secondary" :disabled="editEntryLoading" @click="showEditEntryModal = false">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="editEntryLoading">
                <svg v-if="editEntryLoading" class="mr-2 h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {{ editingEntryId ? 'Update' : 'Add' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- ═══════════════════════════════════════════════════════════════════════ -->
    <!--  Delete Access Entry Dialog                                             -->
    <!-- ═══════════════════════════════════════════════════════════════════════ -->

    <AdminConfirmDialog
      v-model:open="showDeleteEntryDialog"
      title="Delete Feature"
      :message="'Delete feature \'' + (deletingEntryRow?.key ?? '') + '\' from all plans?'"
      :detail="deletingEntryIds.length > 0
        ? 'This will remove ' + deletingEntryIds.length + ' access entr' + (deletingEntryIds.length === 1 ? 'y' : 'ies') + ' across all plans. This immediately affects the access map for subscribers.'
        : 'No entries found to delete.'"
      confirm-label="Delete"
      :destructive="true"
      :loading="actionLoading === 'delete-entries'"
      @confirm="confirmDeleteEntries"
    />
  </div>
</template>
