/**
 * useCrudForm — create/edit form lifecycle management.
 *
 * Handles the complete lifecycle of a CRUD form: loading existing data
 * (for edit mode), tracking form state, validating, submitting (create
 * or update), and handling API errors including field-level validation.
 *
 * Designed to work with Pinia CRUD stores built on the base.ts factory.
 * Integrates with FormErrors, Modal, and ConfirmDialog components.
 *
 * Usage (create):
 *   const form = useCrudForm({
 *     store: useInstitutionStore(),
 *     mode: 'create',
 *     onSuccess: (item) => router.push(`/institutions/${item.id}`),
 *   });
 *
 * Usage (edit):
 *   const form = useCrudForm({
 *     store: useInstitutionStore(),
 *     mode: 'edit',
 *     itemId: props.id,
 *     onSuccess: (item) => emit('saved', item),
 *   });
 *
 *   // In onMounted:
 *   await form.load();
 *
 *   // In template:
 *   <form @submit.prevent="form.submit()">
 *     <input v-model="form.data.name" />
 *     <FormErrors :errors="form.error" :field-errors="form.fieldErrors" />
 *     <button :disabled="form.loading" type="submit">
 *       {{ form.isEdit ? 'Update' : 'Create' }}
 *     </button>
 *   </form>
 */

import {
  ref,
  reactive,
  computed,
  watch,
  onUnmounted,
  toRaw,
  type Ref,
  type ComputedRef,
} from "vue";
import { extractErrorMessage } from "@/stores/base";

// =============================================================================
// Types
// =============================================================================

/** Form mode: creating a new entity or editing an existing one. */
export type FormMode = "create" | "edit";

/**
 * Configuration for useCrudForm.
 *
 * @template T - Full entity type (e.g. InstitutionOut)
 * @template TCreate - Create request body type
 * @template TUpdate - Update request body type (all fields optional)
 */
export interface UseCrudFormConfig<T extends { id: number }, TCreate, TUpdate> {
  /** The Pinia CRUD store instance. */
  store: {
    current: T | null;
    loading: boolean;
    loadingAction: string;
    error: string | null;
    fieldErrors: Record<string, string[]>;
    fetchOne: (id: number) => Promise<T>;
    create: (data: TCreate) => Promise<T>;
    update: (id: number, data: TUpdate) => Promise<T>;
    clearError: () => void;
    clearCurrent: () => void;
  };

  /** Form mode: 'create' for new entity, 'edit' for existing. */
  mode: FormMode;

  /**
   * Entity ID to load (required for edit mode).
   * Can be a ref for reactive route param changes.
   */
  itemId?: number | (() => number);

  /**
   * Transform form data before submitting.
   * Useful for type coercion, trimming, or adding computed fields.
   *
   * @param data - The raw form data
   * @returns Transformed data ready for the API
   */
  beforeSubmit?: (data: Record<string, unknown>) => Record<string, unknown>;

  /**
   * Callback after successful create or update.
   * Receives the created/updated entity.
   *
   * @param item - The created or updated entity
   */
  onSuccess?: (item: T) => void;

  /**
   * Callback after a failed create or update.
   * Receives the error.
   *
   * @param err - The error that occurred
   */
  onError?: (err: unknown) => void;

  /**
   * Map entity data to initial form values (for edit mode).
   * If not provided, the entity is spread directly into the form.
   * Use this to transform API response fields to form field names/values.
   *
   * @param entity - The fetched entity
   * @returns Initial form data
   */
  mapEntityToForm?: (entity: T) => Record<string, unknown>;

  /**
   * Build the create request body from form data.
   * If not provided, form data is cast directly to TCreate.
   *
   * @param formData - The form data
   * @returns The create request body
   */
  buildCreatePayload?: (formData: Record<string, unknown>) => TCreate;

  /**
   * Build the update request body from form data.
   * If not provided, a diff against the original data is computed
   * and only changed fields are sent (PATCH semantics).
   *
   * @param formData - The current form data
   * @param original - The original entity data (before edits)
   * @returns The update request body
   */
  buildUpdatePayload?: (
    formData: Record<string, unknown>,
    original: Record<string, unknown>,
  ) => TUpdate;

  /**
   * Whether to track dirty state.
   * Default: true.
   */
  trackDirty?: boolean;

  /**
   * Confirmation message before navigating away with unsaved changes.
   * Set to false to disable the beforeunload warning.
   * Default: "You have unsaved changes. Are you sure you want to leave?"
   */
  unsavedChangesMessage?: string | false;
}

/** Return type of useCrudForm. */
export interface CrudForm<T extends { id: number }> {
  /** Reactive form data object. Mutate directly for two-way binding. */
  data: Record<string, unknown>;

  /** Current form mode. */
  mode: FormMode;

  /** Whether the form is in edit mode. */
  isEdit: boolean;

  /** Whether the form is in create mode. */
  isCreate: boolean;

  /** Whether a load or submit operation is in progress. */
  loading: ComputedRef<boolean>;

  /** Which specific action is loading ('load' | 'create' | 'update'). */
  loadingAction: Ref<string>;

  /** General error message from the last failed operation. */
  error: ComputedRef<string | null>;

  /** Field-level validation errors from the API. */
  fieldErrors: ComputedRef<Record<string, string[]>>;

  /** Whether there are unsaved changes (only when trackDirty is enabled). */
  isDirty: Ref<boolean>;

  /** Whether the form has been submitted at least once. */
  isSubmitted: Ref<boolean>;

  /**
   * Load entity data for edit mode.
   * Called automatically if itemId is provided in config.
   * Can be called manually for lazy loading.
   *
   * @returns The loaded entity
   */
  load: () => Promise<T | null>;

  /**
   * Submit the form. Calls create or update based on mode.
   * Transforms data through beforeSubmit if configured.
   *
   * @returns The created/updated entity, or null on error
   */
  submit: () => Promise<T | null>;

  /**
   * Reset the form to its initial state.
   * For edit mode, reloads from the store's current entity.
   * For create mode, clears all fields.
   */
  reset: () => void;

  /**
   * Set a single form field value.
   *
   * @param key - Field name
   * @param value - New value
   */
  setFieldValue: (key: string, value: unknown) => void;

  /**
   * Get a form field value.
   *
   * @param key - Field name
   * @returns The current value
   */
  getFieldValue: (key: string) => unknown;

  /** Clear all errors (general + field-level). */
  clearErrors: () => void;

  /**
   * Manually set a field error (e.g. from client-side validation).
   *
   * @param field - Field name
   * @param message - Error message
   */
  setFieldError: (field: string, message: string) => void;

  /**
   * Manually set the general error message.
   *
   * @param message - Error message
   */
  setError: (message: string) => void;
}

// =============================================================================
// Composable
// =============================================================================

/**
 * Create a CRUD form with lifecycle management.
 *
 * @template T - Full entity type
 * @template TCreate - Create request body type
 * @template TUpdate - Update request body type
 * @param config - Configuration object
 */
export function useCrudForm<T extends { id: number }, TCreate, TUpdate>(
  config: UseCrudFormConfig<T, TCreate, TUpdate>,
): CrudForm<T> {
  const {
    store,
    mode,
    itemId,
    beforeSubmit,
    onSuccess,
    onError,
    mapEntityToForm,
    buildCreatePayload,
    buildUpdatePayload,
    trackDirty = true,
    unsavedChangesMessage = "You have unsaved changes. Are you sure you want to leave?",
  } = config;

  // ─── State ──────────────────────────────────────────────────────────────

  const data = reactive<Record<string, unknown>>({});
  const originalData = ref<Record<string, unknown>>({});
  const isDirty = ref(false);
  const isSubmitted = ref(false);
  const loadingAction = ref<string>("");

  // Proxy loading and error from the store
  const loading = computed(() => store.loading);
  const error = computed(() => store.error);
  const fieldErrors = computed(() => store.fieldErrors);

  const isEdit = mode === "edit";
  const isCreate = mode === "create";

  // ─── Resolve itemId ────────────────────────────────────────────────────

  function resolveItemId(): number | undefined {
    if (itemId === undefined) return undefined;
    if (typeof itemId === "function") return itemId();
    return itemId;
  }

  // ─── Dirty tracking ────────────────────────────────────────────────────

  if (trackDirty) {
    watch(
      data,
      () => {
        const currentJson = JSON.stringify(toRaw(data));
        const originalJson = JSON.stringify(originalData.value);
        isDirty.value = currentJson !== originalJson;
      },
      { deep: true },
    );
  }

  // ─── Browser beforeunload warning ──────────────────────────────────────

  function handleBeforeUnload(event: BeforeUnloadEvent): void {
    if (isDirty.value && unsavedChangesMessage !== false) {
      event.preventDefault();
      // Modern browsers ignore custom messages but require returnValue to be set
      event.returnValue = unsavedChangesMessage as string;
    }
  }

  if (typeof window !== "undefined" && unsavedChangesMessage !== false) {
    window.addEventListener("beforeunload", handleBeforeUnload);
  }

  onUnmounted(() => {
    if (typeof window !== "undefined") {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    }
    // Clear the store's current entity to avoid stale data
    store.clearCurrent();
  });

  // ─── Load entity (edit mode) ────────────────────────────────────────────

  async function load(): Promise<T | null> {
    const id = resolveItemId();
    if (isCreate || !id) return null;

    loadingAction.value = "load";

    try {
      const entity = await store.fetchOne(id);

      // Map entity to form data
      const formData = mapEntityToForm ? mapEntityToForm(entity) : { ...entity };

      // Reset form data
      for (const key of Object.keys(data)) {
        delete data[key];
      }
      Object.assign(data, formData);

      // Store original for dirty tracking
      originalData.value = { ...toRaw(data) };
      isDirty.value = false;

      return entity;
    } catch (err) {
      onError?.(err);
      return null;
    } finally {
      loadingAction.value = "";
    }
  }

  // ─── Submit ─────────────────────────────────────────────────────────────

  async function submit(): Promise<T | null> {
    isSubmitted.value = true;
    store.clearError();

    // Transform data through beforeSubmit hook
    let submitData = { ...toRaw(data) };
    if (beforeSubmit) {
      submitData = beforeSubmit(submitData);
    }

    try {
      let result: T;

      if (isEdit) {
        const id = resolveItemId();
        if (!id) {
          throw new Error("Cannot update: no itemId provided for edit mode");
        }

        // Build update payload
        const updatePayload = buildUpdatePayload
          ? buildUpdatePayload(submitData, originalData.value)
          : (computeDiff(submitData, originalData.value) as TUpdate);

        loadingAction.value = "update";
        result = await store.update(id, updatePayload);
      } else {
        // Build create payload
        const createPayload = buildCreatePayload
          ? buildCreatePayload(submitData)
          : (submitData as TCreate);

        loadingAction.value = "create";
        result = await store.create(createPayload);
      }

      // Update original data after successful save
      originalData.value = { ...submitData };
      isDirty.value = false;

      onSuccess?.(result);
      return result;
    } catch (err) {
      onError?.(err);
      return null;
    } finally {
      loadingAction.value = "";
    }
  }

  // ─── Reset ──────────────────────────────────────────────────────────────

  function reset(): void {
    store.clearError();
    isSubmitted.value = false;
    loadingAction.value = "";

    if (isEdit && store.current) {
      // Reset to the original entity data
      const formData = mapEntityToForm ? mapEntityToForm(store.current) : { ...store.current };

      for (const key of Object.keys(data)) {
        delete data[key];
      }
      Object.assign(data, formData);
      originalData.value = { ...toRaw(data) };
    } else {
      // Clear all form fields
      for (const key of Object.keys(data)) {
        delete data[key];
      }
      originalData.value = {};
    }

    isDirty.value = false;
  }

  // ─── Field helpers ──────────────────────────────────────────────────────

  function setFieldValue(key: string, value: unknown): void {
    data[key] = value;
  }

  function getFieldValue(key: string): unknown {
    return data[key];
  }

  function clearErrors(): void {
    store.clearError();
  }

  function setFieldError(field: string, message: string): void {
    // For client-side validation, we set errors directly on the store
    store.fieldErrors = { ...store.fieldErrors, [field]: [message] };
  }

  function setError(message: string): void {
    (store as unknown as { error: string | null }).error = message;
  }

  // ─── Auto-load for edit mode ────────────────────────────────────────────

  if (isEdit && resolveItemId()) {
    // Will be called by the component in onMounted typically,
    // but we make it available for manual invocation too.
  }

  return {
    data,
    mode,
    isEdit,
    isCreate,
    loading,
    loadingAction,
    error,
    fieldErrors,
    isDirty,
    isSubmitted,

    load,
    submit,
    reset,
    setFieldValue,
    getFieldValue,
    clearErrors,
    setFieldError,
    setError,
  };
}

// =============================================================================
// Internal helpers
// =============================================================================

/**
 * Compute the diff between current form data and original data.
 * Only includes fields that have changed — implements PATCH semantics.
 */
function computeDiff(
  current: Record<string, unknown>,
  original: Record<string, unknown>,
): Record<string, unknown> {
  const diff: Record<string, unknown> = {};

  for (const key of Object.keys(current)) {
    const currVal = current[key];
    const origVal = original[key];

    // Compare by JSON stringification to handle objects/arrays
    if (JSON.stringify(currVal) !== JSON.stringify(origVal)) {
      diff[key] = currVal;
    }
  }

  return diff;
}
