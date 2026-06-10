import type { App } from "vue";
import { createPinia } from "pinia";

// ── Page Components (registered as ldgr-* custom elements) ────────────────────
import InstitutionsPage from "@/components/vue/institutions/InstitutionsPage.vue";
import TagsPage from "@/components/vue/tags/TagsPage.vue";
import AccountsPage from "@/components/vue/accounts/AccountsPage.vue";
import AccountDetail from "@/components/vue/accounts/AccountDetail.vue";
import CategoriesPage from "@/components/vue/categories/CategoriesPage.vue";
import TransactionsPage from "@/components/vue/transactions/TransactionsPage.vue";
import TransactionDetail from "@/components/vue/transactions/TransactionDetail.vue";

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

  // ── Register ldgr-* Custom Element Page Components ──────────────────
  // These map to <ldgr-*> tags used with client:only="vue" in Astro pages.
  app.component("ldgr-institutions-page", InstitutionsPage);
  app.component("ldgr-tags-page", TagsPage);
  app.component("ldgr-accounts-page", AccountsPage);
  app.component("ldgr-account-detail", AccountDetail);
  app.component("ldgr-categories-page", CategoriesPage);
  app.component("ldgr-transactions-page", TransactionsPage);
  app.component("ldgr-transaction-detail", TransactionDetail);

  // ── Global Properties ───────────────────────────────────────────────
  // app.config.globalProperties.$formatCurrency = formatCurrency;
};
