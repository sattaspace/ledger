/**
 * useHotkeys — Global keyboard shortcut composable.
 *
 * Registers keyboard shortcuts at the app level and provides
 * a simple API for components to add their own scoped shortcuts.
 *
 * Built-in global shortcuts:
 *   Ctrl+K / Cmd+K  → Open search focus
 *   Ctrl+N / Cmd+N  → Quick-add transaction
 *   Escape           → Close topmost modal/dropdown (handled by Modal.vue)
 *
 * Usage in components:
 *   import { useHotkeys } from '@/composables'
 *
 *   const { onSearch, onQuickAdd } = useHotkeys()
 *
 *   onSearch(() => {
 *     searchInputRef.value?.focus()
 *   })
 *
 *   onQuickAdd(() => {
 *     showTransactionForm.value = true
 *   })
 *
 * Architecture:
 *   - Singleton event listener on document.keydown
 *   - Callbacks registered via onSearch / onQuickAdd
 *   - Last registered callback wins (page-level overrides)
 *   - Input/textarea/contenteditable elements are skipped
 *     (shortcuts don't fire when typing)
 */

// ─── Types ──────────────────────────────────────────────────────────────────

type HotkeyCallback = () => void;

interface HotkeyRegistry {
  search: HotkeyCallback | null;
  quickAdd: HotkeyCallback | null;
}

// ─── Singleton State ────────────────────────────────────────────────────────

const registry: HotkeyRegistry = {
  search: null,
  quickAdd: null,
};

let listenerAttached = false;

// ─── Key Match Helpers ──────────────────────────────────────────────────────

function isSearchShortcut(e: KeyboardEvent): boolean {
  return (e.ctrlKey || e.metaKey) && e.key === "k";
}

function isQuickAddShortcut(e: KeyboardEvent): boolean {
  return (e.ctrlKey || e.metaKey) && e.key === "n";
}

/** Check if the event originated from an input element where shortcuts should be suppressed. */
function isEditableTarget(e: KeyboardEvent): boolean {
  const target = e.target as HTMLElement | null;
  if (!target) return false;
  const tag = target.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return true;
  if (target.isContentEditable) return true;
  return false;
}

// ─── Global Listener ────────────────────────────────────────────────────────

function handleKeydown(e: KeyboardEvent) {
  // Skip shortcuts when focused on editable elements
  if (isEditableTarget(e)) return;

  if (isSearchShortcut(e)) {
    e.preventDefault();
    registry.search?.();
    return;
  }

  if (isQuickAddShortcut(e)) {
    e.preventDefault();
    registry.quickAdd?.();
    return;
  }
}

function ensureListener() {
  if (listenerAttached) return;
  if (typeof document === "undefined") return;
  document.addEventListener("keydown", handleKeydown);
  listenerAttached = true;
}

// ─── Composable ─────────────────────────────────────────────────────────────

export interface HotkeysComposable {
  /** Register a callback for Ctrl+K (search). Replaces any previous callback. */
  onSearch: (cb: HotkeyCallback) => void;
  /** Register a callback for Ctrl+N (quick-add). Replaces any previous callback. */
  onQuickAdd: (cb: HotkeyCallback) => void;
  /** Clear the search shortcut callback. */
  clearSearch: () => void;
  /** Clear the quick-add shortcut callback. */
  clearQuickAdd: () => void;
}

/**
 * Composable for registering global keyboard shortcuts.
 *
 * Call `onSearch(cb)` or `onQuickAdd(cb)` to register handlers.
 * The last registered callback wins (page-level overrides global).
 * Cleanup is automatic when the component unmounts.
 */
export function useHotkeys(): HotkeysComposable {
  ensureListener();

  const cleanupFns: Array<() => void> = [];

  function onSearch(cb: HotkeyCallback) {
    registry.search = cb;
    const cleanup = () => {
      if (registry.search === cb) registry.search = null;
    };
    cleanupFns.push(cleanup);
    if (typeof onUnmounted !== "undefined") {
      onUnmounted(cleanup);
    }
  }

  function onQuickAdd(cb: HotkeyCallback) {
    registry.quickAdd = cb;
    const cleanup = () => {
      if (registry.quickAdd === cb) registry.quickAdd = null;
    };
    cleanupFns.push(cleanup);
    if (typeof onUnmounted !== "undefined") {
      onUnmounted(cleanup);
    }
  }

  function clearSearch() {
    registry.search = null;
  }

  function clearQuickAdd() {
    registry.quickAdd = null;
  }

  return { onSearch, onQuickAdd, clearSearch, clearQuickAdd };
}
