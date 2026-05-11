---
title: Satta Ledger Integration Guide
description: This guide walks you through integrating the Python SDK 
---

# Satta Ledger — Localhost Integration Guide

This guide walks you through integrating the Python SDK in `ledgerbackend` and the sister-domain-starter in `ledgerfrontend`, then verifying the full chain works on localhost.

---

## Architecture

```
┌─────────────────────────────────┐
│    SATTABASE CORE               │
│    backend (port 8086)          │
│    frontend (port 4321)         │
│    — User accounts             │
│    — Auth (JWT)                │
│    — Billing (Stripe)          │
│    — Access maps               │
└────────────┬────────────────────┘
             │
    ┌────────┴─────────┐
    │                  │
    ▼                  ▼
┌───────────────┐  ┌──────────────────┐
│ ledgerfrontend │  │ ledgerbackend     │
│ (port 4322)   │  │ (port 8087)       │
│               │  │                   │
│ Astro 6 + Vue │  │ Django Ninja      │
│               │  │ + sattabase-sdk   │
│ - Login page  │  │ + SattabaseAuth   │
│ - Dashboard   │  │   Middleware      │
│ - Billing     │  │                   │
│   redirects   │  │ request.          │
│               │  │   sattabase_user  │
│               │  │   sattabase_access│
│               │  │   sattabase_subs  │
└───────┬───────┘  └──────────────────┘
        │                    │
        │  JWT Bearer +      │  X-API-Key +
        │  X-Service-Domain  │  X-Service-Domain +
        │                    │  Authorization
        └────────┬───────────┘
                 │
                 ▼
        Sattabase API
        /billing/auth/me
```

---

## Part 1: Backend Setup (ledgerbackend)

### 1.1 Install the Python SDK

```bash
cd /path/to/sattabase/sdk/python

# Install in development mode (editable) so changes reflect immediately
pip install -e .

# Or if you prefer a regular install:
# pip install .
```

Verify:
```bash
python -c "from sattabase_sdk import SattabaseClient, SattabaseAuthMiddleware; print('SDK OK')"
```

### 1.2 Add SATTABASE settings to your .env

The ledgerbackend reads `.env` from the **parent directory** (`sattabase/.env`). Add these lines:

```env
# ── Sattabase SDK (Ledger Backend) ──────────────────────────────────────
# The Sattabase backend API URL (same server, different port)
SL_SATTABASE_BASE_URL=http://localhost:8000/api/v1

# Service domain identifier for Ledger (must match ServiceDomain.domain in Sattabase admin)
SL_SATTABASE_SERVICE_DOMAIN=ledger.sattaspace.com

# API key for Ledger service (generate one in Sattabase admin: Settings → API Keys)
# MUST start with "sb_live_"
SL_SATTABASE_API_KEY=sb_live_your_actual_api_key_here

# How long to wait for Sattabase auth/me response (seconds)
SL_SATTABASE_AUTH_TIMEOUT=5

# How long to cache auth/me results (seconds) — avoids hitting Sattabase on every request
SL_SATTABASE_AUTH_CACHE_TTL=60
```

### 1.3 Create a ServiceDomain in Sattabase Admin

Before the SDK will work, you need to register the Ledger service domain in the Sattabase admin panel:

1. Start Sattabase backend + frontend
2. Go to **Admin → Service Domains**
3. Create a new ServiceDomain:
   - **Domain**: `ledger.sattaspace.com`
   - **Product**: Select the "Ledger" product (create one if needed)
4. Go to **Admin → API Keys**
5. Create an API key credential — copy the raw key (starts with `sb_live_`)
6. Set `SL_SATTABASE_API_KEY` in your `.env` to that key

### 1.4 Run migrations

```bash
cd /path/to/sattabase/ledgerbackend

# The TestNote model needs a migration
python manage.py makemigrations api
python manage.py migrate
```

### 1.5 Start the backend

```bash
python manage.py runserver 8087
```

### 1.6 Verify the backend is running

```bash
# Should return the OpenAPI schema
curl http://localhost:8087/api/v1/docs

# Test the /me endpoint WITHOUT auth — should return 401
curl http://localhost:8087/api/v1/test-notes/me

# Test with a valid JWT from Sattabase
curl -H "Authorization: Bearer <your_jwt_access_token>" \
     http://localhost:8087/api/v1/test-notes/me
```

---

## Part 2: Frontend Setup (ledgerfrontend)

### 2.1 Install npm dependencies

```bash
cd /path/to/sattabase/ledgerfrontend

# Dependencies should already be in package.json
npm install
```

### 2.2 Create `.env` file

```bash
cp .env.example .env
```

The defaults should work for localhost. Verify these values:

```env
# API base URL of the Sattabase backend (Django Ninja)
PUBLIC_API_BASE_URL_SB=http://localhost:8000/api/v1

# Sattabase base domain frontend URL (for redirects to register, billing, etc.)
PUBLIC_BASE_DOMAIN_URL=http://localhost:4321

# This sister domain's own URL (for return redirects after billing)
PUBLIC_THIS_DOMAIN_URL=http://localhost:4322

# Service domain identifier (must match ServiceDomain in Sattabase admin)
PUBLIC_SERVICE_DOMAIN=ledger.sattaspace.com

# Session cookie name
PUBLIC_SESSION_COOKIE_NAME=sattabase_session_cookie

# Token storage key prefix (domain-specific)
PUBLIC_TOKEN_KEY_PREFIX=sattabase-ledger:
```

### 2.3 Start the frontend

```bash
npm run dev
```

This starts the dev server on **http://localhost:4322**.

---

## Part 3: End-to-End Integration Test

### 3.1 Prerequisites — all services running

| Service | URL | Port |
|---------|-----|------|
| Sattabase Backend | http://localhost:8086 | 8086 |
| Sattabase API | http://localhost:8000/api/v1 | 8000 |
| Sattabase Frontend | http://localhost:4321 | 4321 |
| Ledger Frontend | http://localhost:4322 | 4322 |
| Ledger Backend | http://localhost:8087 | 8087 |

### 3.2 Test the full auth chain

**Step 1: Login on Ledger Frontend**

1. Open **http://localhost:4322/auth/login**
2. Enter your Sattabase credentials (email + password)
3. Click "Sign in"
4. You should be redirected to **http://localhost:4322/dashboard**

What happens behind the scenes:
```
Browser → POST /auth/login to Sattabase (port 8000)
Sattabase → returns JWT {access, refresh}
api.ts → stores tokens in sessionStorage (or localStorage if "Remember me")
Browser → redirects to /dashboard
dashboard.astro → GET /billing/auth/me with JWT + X-Service-Domain: ledger.sattaspace.com
Sattabase → returns {user, subscription, access} scoped to Ledger's product
Dashboard renders user info, plan, features
```

**Step 2: Verify the backend middleware**

In a separate terminal, get your JWT access token from the browser's DevTools:
1. Open DevTools → Application → Session Storage → `sattabase-ledger:access_token`
2. Copy the token value

Then test the backend:
```bash
# The /me endpoint shows what the middleware resolved
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://localhost:8087/api/v1/test-notes/me

# Expected response (if authenticated):
# {
#   "user_id": 1,
#   "email": "you@example.com",
#   "full_name": "Your Name",
#   "role": "owner",
#   "access": {"dashboard": true, "reports": true, ...},
#   "subscription": {"plan_name": "Pro", "status": "active", "is_active": true}
# }
```

**Step 3: Create a test note through the backend**

```bash
# Create a note
curl -X POST \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"title": "SDK Integration Test", "content": "It works!"}' \
     http://localhost:8087/api/v1/test-notes

# List notes
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     http://localhost:8087/api/v1/test-notes
```

### 3.3 Test the billing redirect flow

1. On the Ledger dashboard, click **"Manage on SattaBase"**
2. The browser redirects to `sattabase.tld/auth/callback?code=XXX&return_to=/dashboard/billing`
3. After managing billing on Sattabase, you're redirected back to:
   `http://localhost:4322/dashboard?billing_updated=1`
4. The dashboard detects `billing_updated=1`, cleans the URL, and refetches auth/me

### 3.4 Test the SSO cross-domain flow

1. From the Ledger dashboard, click "Manage on SattaBase"
2. Behind the scenes: `POST /auth/authorize` → one-time code → redirect with code
3. Sattabase exchanges the code for its own JWT tokens
4. User is now authenticated on BOTH domains seamlessly

---

## Part 4: What Was Implemented

### Backend (ledgerbackend)

| File | Purpose |
|------|---------|
| `ledger/settings.py` | Added `SattabaseAuthMiddleware` + `SATTABASE_*` config block |
| `ledger/asgi.py` | Fixed `DJANGO_SETTINGS_MODULE` → `"ledger.settings"` |
| `api/models.py` | `TestNote` model with `user_id` FK (integer, not Django FK) |
| `api/schemas.py` | Ninja schemas for TestNote CRUD |
| `api/controllers/test_note_controller.py` | Full CRUD + `/me` endpoint, all scoped by `request.sattabase_user` |
| `api/views.py` | Registered `TestNoteController` |

### Frontend (ledgerfrontend)

| File | Purpose |
|------|---------|
| `sattabase.config.ts` | Ledger-specific config (token prefix, service domain) |
| `.env.example` | PUBLIC_ env vars for Astro |
| `src/lib/api.ts` | Centralized fetch client with JWT + auto-refresh |
| `src/lib/auth.ts` | Login/logout/SSO authorization code flow |
| `src/lib/billing.ts` | Billing redirect URL constructors |
| `src/lib/types.ts` | TypeScript interfaces + `TestNote` type |
| `src/middleware.ts` | Astro auth guard for `/dashboard` paths |
| `src/composables/useAuth.ts` | Shared reactive auth state |
| `src/composables/useAccess.ts` | Feature gating helpers |
| `src/composables/useSubscription.ts` | Subscription state |
| `src/composables/useBillingRedirect.ts` | Billing return detection |
| `src/components/vue/LoginForm.vue` | Login form (Ledger-branded) |
| `src/components/astro/LoadingSpinner.astro` | Spinner component |
| `src/layouts/BaseLayout.astro` | HTML shell with dark mode |
| `src/layouts/DashboardLayout.astro` | Sidebar + user info + sign out |
| `src/pages/auth/login.astro` | Login page |
| `src/pages/dashboard/index.astro` | Dashboard with plan/access/billing cards |
| `src/styles/global.css` | Added component utilities (btn-primary, card, input-field, etc.) |

---

## Key Concepts

- **The single integer `user.id`** from Sattabase is the FK that ties all Ledger data to a user. No Django User model needed.
- **`request.sattabase_user`** is set by the middleware on every request. If `None`, the user is not authenticated.
- **`X-Service-Domain: ledger.sattaspace.com`** is sent by both frontend (api.ts) and backend (SDK middleware) so Sattabase returns domain-scoped data.
- **Browser mode (frontend)**: No API key — just JWT + X-Service-Domain header.
- **Server mode (backend)**: API key + JWT + X-Service-Domain header — the SDK middleware calls `GET /billing/auth/me` to verify the JWT.
