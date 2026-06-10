/**
 * useToast — Global toast notification composable.
 *
 * Provides a reactive toast queue that persists across navigation.
 * Built on a Pinia store so any component or store action can
 * call `toast.success()`, `toast.error()`, etc.
 *
 * Usage:
 *   import { useToast } from '@/composables'
 *   const toast = useToast()
 *   toast.success('Account created!')
 *   toast.error('Failed to save', { duration: 6000 })
 *   toast.warning('Budget is 90% used')
 *   toast.info('Tip: Press Ctrl+K to search')
 *
 * ToastContainer.vue must be mounted once in the app shell
 * (DashboardLayout.astro) to render the toasts.
 */

import { defineStore } from "pinia";

// ─── Types ──────────────────────────────────────────────────────────────────

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  /** Unique ID for this toast instance. */
  id: number;
  /** Variant controls color and icon. */
  variant: ToastVariant;
  /** Main message text. */
  message: string;
  /** Optional title (bold). */
  title?: string;
  /** Optional action button (e.g. "Retry"). */
  action?: {
    /** Button label text. */
    label: string;
    /** Click handler. */
    onClick: () => void;
  };
  /** Auto-dismiss duration in ms. 0 = manual dismiss only. */
  duration: number;
  /** Timestamp when the toast was created. */
  createdAt: number;
}

export interface ToastOptions {
  /** Optional title shown in bold above the message. */
  title?: string;
  /** Auto-dismiss duration in ms. Default: 4000 for success/info, 6000 for error/warning. */
  duration?: number;
  /** Optional action button (e.g. "Retry"). */
  action?: {
    label: string;
    onClick: () => void;
  };
}

// ─── Store ──────────────────────────────────────────────────────────────────

let nextId = 0;

const useToastStore = defineStore("toast", {
  state: () => ({
    toasts: [] as Toast[],
  }),

  actions: {
    /** Add a toast to the queue. */
    add(variant: ToastVariant, message: string, options?: ToastOptions) {
      const defaultDuration = variant === "error" || variant === "warning" ? 6000 : 4000;
      const toast: Toast = {
        id: ++nextId,
        variant,
        message,
        title: options?.title,
        action: options?.action,
        duration: options?.duration ?? defaultDuration,
        createdAt: Date.now(),
      };
      this.toasts.push(toast);

      // Auto-dismiss after duration
      if (toast.duration > 0) {
        setTimeout(() => this.dismiss(toast.id), toast.duration);
      }

      return toast.id;
    },

    /** Remove a toast by ID. */
    dismiss(id: number) {
      const idx = this.toasts.findIndex((t) => t.id === id);
      if (idx !== -1) {
        this.toasts.splice(idx, 1);
      }
    },

    /** Clear all active toasts. */
    clearAll() {
      this.toasts = [];
    },
  },
});

// ─── Composable ─────────────────────────────────────────────────────────────

export interface ToastComposable {
  /** Show a success toast (green). */
  success: (message: string, options?: ToastOptions) => number;
  /** Show an error toast (red). */
  error: (message: string, options?: ToastOptions) => number;
  /** Show a warning toast (amber). */
  warning: (message: string, options?: ToastOptions) => number;
  /** Show an info toast (cyan). */
  info: (message: string, options?: ToastOptions) => number;
  /** Dismiss a specific toast by ID. */
  dismiss: (id: number) => void;
  /** Clear all active toasts. */
  clearAll: () => void;
  /** Reactive array of active toasts. */
  toasts: Toast[];
}

/**
 * Composable that provides toast notification methods.
 *
 * Uses a shared Pinia store internally so all components
 * share the same toast queue.
 */
export function useToast(): ToastComposable {
  const store = useToastStore();

  return {
    success: (msg, opts) => store.add("success", msg, opts),
    error: (msg, opts) => store.add("error", msg, opts),
    warning: (msg, opts) => store.add("warning", msg, opts),
    info: (msg, opts) => store.add("info", msg, opts),
    dismiss: (id) => store.dismiss(id),
    clearAll: () => store.clearAll(),
    toasts: store.toasts,
  };
}
