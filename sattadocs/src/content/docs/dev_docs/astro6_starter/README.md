---
title: Sister Domain Starter 
description: Copy-paste starter files for any AstroJS sister domain frontend in the SattaSpace ecosystem.
---

# Sattabase Sister Domain Starter Kit

> Copy-paste starter files for any AstroJS sister domain frontend in the SattaSpace ecosystem.

## What This Is

This directory contains all the files that any AstroJS sister domain frontend needs to integrate with the Sattabase cross-domain SSO architecture. Sister domains only have **LOGIN** and **LOGOUT** screens — everything else (register, forgot password, reset, verify, profile, billing) redirects to the Sattabase base domain.

The **Token Pass-Through (authorization code) flow** enables seamless SSO: a sister domain generates a one-time auth code from its JWT and redirects to the base domain, which exchanges the code for its own tokens.

---

## Quick Start

### 1. Create a New Astro Project

```bash
npm create astro@latest my-sister-domain
cd my-sister-domain
```

When prompted:
- Template: **Empty**
- TypeScript: **Strict**
- Install dependencies: **Yes**

### 2. Install Dependencies

```bash
npm install vue @astrojs/vue
npm install tailwindcss @tailwindcss/vite
```

### 3. Configure Astro

Update `astro.config.mjs`:

```javascript
import { defineConfig } from 'astro/config';
import vue from '@astrojs/vue';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  integrations: [vue()],
  vite: {
    plugins: [tailwindcss()],
  },
});
```

### 4. Copy Starter Files

Copy all files from this `sister-domain-starter/` directory into your new Astro project:

```bash
# From the sister-domain-starter directory
cp -r src/ /path/to/my-sister-domain/src/
cp sattabase.config.ts /path/to/my-sister-domain/
cp .env.example /path/to/my-sister-domain/.env
```

### 5. Configure Environment Variables

Edit `.env` and fill in your domain-specific values:

```env
PUBLIC_API_BASE_URL_SB=https://api.sattaspace.com/api/v1
PUBLIC_BASE_DOMAIN_URL=https://sattabase.sattaspace.com
PUBLIC_THIS_DOMAIN_URL=https://finance.sattaspace.com
PUBLIC_SERVICE_DOMAIN=finance.sattaspace.com
PUBLIC_SESSION_COOKIE_NAME=sattabase_session_cookie
PUBLIC_TOKEN_KEY_PREFIX=sattabase:
```

### 6. Configure `sattabase.config.ts`

The config file reads from environment variables with sensible defaults. You typically don't need to edit it directly — just set the `.env` values above.

### 7. Add Your Business Pages

Add your own pages under `src/pages/dashboard/`. Use the `DashboardLayout` for authenticated pages and the feature gating composables to control access.

---

## SSO Flow

### How Login Works

```
1. User visits sister domain → /auth/login
2. User enters email + password
3. POST /auth/login → receives JWT tokens
4. Tokens stored in sessionStorage (or localStorage with "Remember me")
5. Redirect to /dashboard
6. GET /billing/auth/me (with X-Service-Domain header) → user + subscription + access map
```

### How Cross-Domain SSO Works

When a sister domain user needs to access the base domain (e.g., to manage billing):

```
1. User clicks "Manage Subscription" on sister domain
2. Sister domain calls POST /auth/authorize → receives one-time auth code
3. Sister domain redirects to: sattabase.tld/auth/callback?code=XXX&return_to=/dashboard/billing
4. Base domain exchanges code via POST /auth/token/exchange → receives its own JWT tokens
5. Base domain stores tokens, redirects to return_to
6. User is now authenticated on the base domain — seamless!
```

### How Billing Return Works

After a billing action on the base domain:

```
1. Base domain redirects to: finance.sattaspace.com/dashboard?billing_updated=1
2. useBillingRedirect detects the param
3. Cleans the URL (no re-trigger on refresh)
4. Dispatches "sattabase:billing-updated" CustomEvent
5. useAuth auto-refetches user/subscription/access
```

---

## File Reference

### Configuration

| File | Purpose |
|------|---------|
| `sattabase.config.ts` | Central configuration — API URL, base domain URL, service domain, token storage prefix |
| `.env.example` | Environment variables template — copy to `.env` and fill in |

### Library (`src/lib/`)

| File | Purpose |
|------|---------|
| `api.ts` | Centralized fetch client with JWT Bearer injection, auto-refresh on 401, token storage |
| `auth.ts` | Auth functions — login, logout, getAuthMe, generateAuthCode, redirectToBase, redirectToBaseWithAuthCode |
| `billing.ts` | Billing redirect URL constructors — upgrade, manageSubscription, portal, detectBillingUpdate |
| `types.ts` | TypeScript interfaces — User, SubscriptionInfo, AuthMeResponse, TokenPair, etc. |

### Composables (`src/composables/`)

| File | Purpose |
|------|---------|
| `useAuth.ts` | Singleton shared auth state — user, subscription, access, login, logout, redirectWithAuthCode |
| `useAccess.ts` | Feature gating — hasAccess(), getAccess(), getLimit() |
| `useSubscription.ts` | Subscription state — fetchSubscriptions(), hasActiveSubscription() |
| `useBillingRedirect.ts` | Billing redirect detection — checkBillingRedirect(), auto-dispatch event |

### Components

| File | Purpose |
|------|---------|
| `src/components/vue/LoginForm.vue` | Login form with email/password, "Remember me", base domain redirect links |
| `src/components/astro/LoadingSpinner.astro` | Simple loading spinner with brand/muted variants |

### Pages

| File | Purpose |
|------|---------|
| `src/pages/auth/login.astro` | Login page — wraps LoginForm in BaseLayout |

### Layouts

| File | Purpose |
|------|---------|
| `src/layouts/BaseLayout.astro` | Base HTML shell — meta tags, fonts, dark mode, CSS |
| `src/layouts/DashboardLayout.astro` | Authenticated layout — sidebar, top bar, user info, sign out |

### Other

| File | Purpose |
|------|---------|
| `src/middleware.ts` | Astro middleware — auth guard for /dashboard routes |
| `src/styles/global.css` | Tailwind CSS 4 setup — brand colors, dark mode, utility classes |

---

## Adding Your Own Business Pages

### 1. Create a New Page

```astro
---
// src/pages/dashboard/reports.astro
import DashboardLayout from "@/layouts/DashboardLayout.astro";
---

<DashboardLayout title="Reports — SattaBase">
  <div id="reports-content" style="display:none">
    <h2 class="text-2xl font-bold">Reports</h2>
    <p class="mt-2 text-muted-foreground">Your business-specific reports go here.</p>
    
    <!-- Access-gated section -->
    <div id="reports-locked" class="mt-6 card p-6">
      <p class="text-muted-foreground">Upgrade to access reports.</p>
      <button class="btn-primary mt-3" id="upgrade-btn">Upgrade Plan</button>
    </div>
  </div>
</DashboardLayout>

<script>
  import { isAuthenticated } from "@/lib/api";

  async function initReports() {
    if (!isAuthenticated()) {
      window.location.href = "/auth/login";
      return;
    }
    
    const content = document.getElementById("reports-content")!;
    content.style.display = "block";
    
    // Check feature access
    const { apiClient } = await import("@/lib/api");
    const data = await apiClient.get<{ access: Record<string, any> }>("/billing/auth/me");
    const hasReports = data.access?.reports === true || data.access?.reports === "true";
    
    const locked = document.getElementById("reports-locked")!;
    if (hasReports) {
      locked.innerHTML = "<p>📊 Your reports content here...</p>";
    }
    
    // Upgrade button redirect
    document.getElementById("upgrade-btn")?.addEventListener("click", async () => {
      const { redirectToBaseWithAuthCode } = await import("@/lib/auth");
      await redirectToBaseWithAuthCode("/dashboard/billing/plans/finance");
    });
  }
  
  initReports();
  document.addEventListener("astro:page-load", initReports);
</script>
```

### 2. Use Vue Components for Interactive Pages

For more interactive pages, create Vue components and mount them with `client:only="vue"`:

```astro
---
// src/pages/dashboard/analytics.astro
import DashboardLayout from "@/layouts/DashboardLayout.astro";
import AnalyticsDashboard from "@/components/vue/AnalyticsDashboard.vue";
---

<DashboardLayout title="Analytics — SattaBase">
  <AnalyticsDashboard client:only="vue" />
</DashboardLayout>
```

### 3. Use Composables in Vue Components

```typescript
// src/components/vue/AnalyticsDashboard.vue
import { useAuth } from "@/composables/useAuth";
import { useAccess } from "@/composables/useAccess";
import { useSubscription } from "@/composables/useSubscription";
import { useBillingRedirect } from "@/composables/useBillingRedirect";

const { user, isAuthenticated, redirectWithAuthCode } = useAuth();
const { hasAccess, getLimit } = useAccess();
const { fetchSubscriptions, hasActiveSubscription } = useSubscription();
const { checkBillingRedirect, isBillingReturn, billingSuccess } = useBillingRedirect();

// Check feature access
const canExport = hasAccess("export_data");
const maxProjects = getLimit("max_projects", 3);

// Redirect to billing
async function goToBilling() {
  await redirectWithAuthCode("/dashboard/billing");
}
```

---

## Important Notes

### Token Storage

Tokens are stored in `sessionStorage` by default (tab-only, cleared on close). When the user checks "Remember me", tokens move to `localStorage` (persists across tabs and browser restarts). The storage key includes a configurable prefix (default: `sattabase:`) to avoid collisions with other apps on the same domain.

### X-Service-Domain Header

The API client automatically injects the `X-Service-Domain` header on every request. This tells the Sattabase backend which product's subscription and access map to return. The value comes from `PUBLIC_SERVICE_DOMAIN` in your `.env`.

### CORS

The Sattabase backend automatically adds all active `ServiceDomain.domain` values to the CORS allowed origins. Make sure your sister domain's domain is registered as a `ServiceDomain` in Sattabase admin with `is_active=True`.

### Never Put Secrets in the Frontend

The `PUBLIC_` prefix on environment variables means they're exposed to the browser. **Never** put API keys (`sb_live_...`) or service credentials in `.env` files — those belong on the sister domain's backend only.

### Dark Mode

Dark mode is supported via CSS variables and a `dark` class on the `<html>` element. The user's preference is stored in `localStorage.theme`. The BaseLayout includes an inline script in `<head>` to prevent the flash of unstyled content.

---

## Architecture Diagram

```
┌──────────────────────────────┐       ┌──────────────────────────┐
│  Sister Domain Frontend       │       │     Sattabase Backend     │
│  (e.g., finance.sattaspace)   │       │  (Django Ninja API)      │
│                               │       │                          │
│  src/lib/api.ts ─────────────────────→│  /auth/login             │
│    JWT Bearer + X-Service-Domain     │  /auth/token/refresh     │
│                               │       │  /auth/authorize         │
│  src/lib/auth.ts ───────────────────→│  /auth/token/exchange    │
│    login, logout, redirectWithCode   │  /billing/auth/me        │
│                               │       │  /billing/subscriptions  │
│  src/lib/billing.ts           │       │                          │
│    URL constructors only      │       │  Returns:                │
│    (zero API calls)           │       │  - user profile          │
│                               │       │  - subscription status   │
│  src/composables/             │       │  - access map            │
│    useAuth, useAccess,        │       │    (scoped to product)   │
│    useSubscription,           │       └──────────────────────────┘
│    useBillingRedirect         │                  │
│                               │                  │ Stripe
└──────────────────────────────┘       ┌───────────┘
         │                              │
         │  Redirect for billing        ▼
         │  (authorization code)   ┌──────────────────────────┐
         └────────────────────────→│  Sattabase Frontend       │
                                   │  (sattabase.sattaspace)   │
                                   │                           │
                                   │  /auth/callback?code=XXX  │
                                   │  /auth/register           │
                                   │  /auth/forgot-password    │
                                   │  /dashboard/billing       │
                                   │  /dashboard/profile       │
                                   └──────────────────────────┘
```

---

## API Key & Authentication Modes

The Sattabase TypeScript SDK supports two authentication modes depending on where it runs:

| Mode | Where | API Key | Auth Method | Use Case |
|------|-------|---------|-------------|----------|
| **Server Mode** | Backend / SSR | **Required** | `X-API-Key` header | Server-to-server domain authentication |
| **Browser Mode** | Frontend / Client | **Optional** | JWT Bearer token | User-facing browser requests |

### Why API Key is Optional in the Browser

In a browser context, the user authenticates via JWT tokens (access + refresh). The JWT already proves *who* the user is and scopes all data to that user. Exposing an API key in frontend code is a security risk — it could be extracted from the browser and used to impersonate the domain.

The API key is still **required for server-to-server** communication because it proves *which domain* is making the request. The Sattabase backend cross-checks the API key against the `X-Service-Domain` header to prevent domain spoofing — a compromised sister domain cannot impersonate another domain.

### Sister Domain Frontend = Browser Mode

This starter kit runs entirely in the browser. It uses **JWT-only authentication** — no API key is needed or used anywhere in the starter files. The `X-Service-Domain` header is still sent so the backend knows which product's subscription data to return, but it is not trusted on its own (only API-key-backed domain claims are trusted by the backend).

If your sister domain also has a backend (e.g., for SSR or webhooks), that backend should use the **Python SDK** or the **TypeScript SDK in server mode** with an API key for any server-to-server calls to Sattabase.
