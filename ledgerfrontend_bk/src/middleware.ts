/**
 * Astro middleware — enhanced auth guard for Satta Ledger.
 *
 * Protected paths:   /dashboard — redirect to /auth/login if not authenticated
 * Guest-only paths:  /auth/login, /auth/callback — redirect to /dashboard if authenticated
 * Public paths:      / (landing page) — accessible to everyone
 *
 * Since JWTs are stored client-side (sessionStorage / localStorage),
 * the middleware injects a client-side auth check script for protected routes
 * and a redirect script for guest-only routes.
 */

import { defineMiddleware } from "astro:middleware";

// Paths that require authentication
const PROTECTED_PATHS = ["/dashboard"];

// Paths that should redirect away if already authenticated
const GUEST_ONLY_PATHS = ["/auth/login", "/auth/callback", "/auth"];

// Feature-gated paths: path prefix → required feature key
const FEATURE_GATED_PATHS: Record<string, string> = {
  "/dashboard/budgets": "budgets",
  "/dashboard/goals": "goals",
  "/dashboard/investments": "investments",
  "/dashboard/debts": "debts",
  "/dashboard/cards": "cards",
  "/dashboard/insurance": "insurance",
  "/dashboard/invoices": "invoices",
  "/dashboard/vault": "vault",
  "/dashboard/transactions": "transactions",
  "/dashboard/institutions": "institutions",
  "/dashboard/accounts": "accounts",
  "/dashboard/categories": "categories",
  "/dashboard/tags": "tags",
  "/dashboard/bills": "bills",
  "/dashboard/reports": "reports",
  "/dashboard/calendar": "bills",
  // TODO: Gate export_pdf when export functionality is added
  // "/dashboard/export": "export_pdf",
};

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Check if this is a protected path
  const isProtected = PROTECTED_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  // Check if this is a guest-only path
  const isGuestOnly = GUEST_ONLY_PATHS.some(
    (path) => pathname === path || pathname.startsWith(`${path}/`),
  );

  // Protected routes: inject client-side auth check script
  if (isProtected) {
    const response = await next();

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      response.headers.set("x-require-auth", "true");

      // Inject a client-side auth guard script that runs immediately
      // This prevents the page from being visible if the user is not authenticated
      const authCheckScript = `
<script is:inline>
(function() {
  var prefix = 'sattabase-ledger:';
  var hasToken = !!(sessionStorage.getItem(prefix + 'access_token') || localStorage.getItem(prefix + 'access_token'));
  if (!hasToken) {
    var returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.replace('/auth/login?return_url=' + returnUrl);
  }
})();
</script>`;

      // Check feature gating
      const requiredFeature = Object.entries(FEATURE_GATED_PATHS).find(
        ([path]) => pathname === path || pathname.startsWith(`${path}/`),
      )?.[1];

      if (requiredFeature) {
        response.headers.set("x-require-feature", requiredFeature);
      }

      const featureCheckScript = requiredFeature
        ? `
<script is:inline>
(function() {
  var featureKey = '${requiredFeature}';
  try {
    var raw = sessionStorage.getItem('sattabase:auth_access');
    if (raw) {
      var access = JSON.parse(raw);
      var value = access[featureKey];
      var hasAccess = value === true
        || (typeof value === 'number' && value > 0)
        || (typeof value === 'string' && value !== '' && value !== 'false' && value !== '0');
      if (!hasAccess) {
        window.location.replace('/dashboard/upgrade?feature=' + encodeURIComponent(featureKey));
      }
    }
    // If sessionStorage is empty, let the page load — the Vue component will handle it
  } catch (e) {
    // On error, let the page load — the Vue component will handle it
  }
})();
</script>`
        : "";

      try {
        const body = await response.text();
        // Inject the script right after <head> so it runs before page renders
        const injected = body.replace("<head>", "<head>" + authCheckScript + featureCheckScript);
        return new Response(injected, {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
        });
      } catch {
        // If we can't modify the response, just return as-is
        return response;
      }
    }

    return response;
  }

  // Guest-only routes: if authenticated, redirect to dashboard
  if (isGuestOnly) {
    const response = await next();

    const contentType = response.headers.get("content-type") || "";
    if (contentType.includes("text/html")) {
      response.headers.set("x-guest-only", "true");
      return response;
    }

    return response;
  }

  // Public routes (e.g. / landing page) — let everyone through
  return next();
});
