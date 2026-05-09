import type { App } from "vue";
import { createPinia } from "pinia";

/**
 * Vue app entrypoint — registered via @astrojs/vue appEntrypoint.
 * This is called once when the Vue app is created.
 * Use it to register plugins, directives, and global configurations.
 */
export default (app: App) => {
  // ── State Management ────────────────────────────────────────────────
  const pinia = createPinia();
  app.use(pinia);

  // ── Global Error Handler ────────────────────────────────────────────
  app.config.errorHandler = (err, instance, info) => {
    console.error("[Vue Error]", err);
    console.error("Component:", instance?.$options?.name ?? "Anonymous");
    console.error("Info:", info);
  };

  // ── Custom Element Config ───────────────────────────────────────────
  // Elements starting with "ldgr-" are treated as custom elements
  // (already configured in astro.config.mjs via vue jsx.isCustomElement)

  // ── Global Properties ───────────────────────────────────────────────
  // app.config.globalProperties.$formatCurrency = formatCurrency;
};
