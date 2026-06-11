# DEALERCORE v3.0 — Developer Documentation

> **Comprehensive Guide for Developers**  
> **Version**: 3.0.0  
> **Last Updated**: June 10, 2026  
> **Status**: Production Ready

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Directory Structure](#3-directory-structure)
4. [Authentication System](#4-authentication-system)
5. [Backend Deep Dive](#5-backend-deep-dive)
6. [Frontend Deep Dive](#6-frontend-deep-dive)
7. [API Reference](#7-api-reference)
8. [Data Models](#8-data-models)
9. [Development Setup](#9-development-setup)
10. [Deployment Guide](#10-deployment-guide)
11. [Architecture Decisions](#11-architecture-decisions)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. System Overview

### 1.1 Purpose

DEALERCORE is a comprehensive dealer management system for automotive dealerships. It provides:

- **Inventory Management**: Track stock, restock products, manage suppliers
- **Sales Management**: Record sales, handle credit, manage DSRs (Daily Sales Representatives)
- **Financial Reports**: Revenue tracking, collections, bad debt management
- **User Management**: Dealer owners, DSRs, and Order Collectors with role-based access
- **Multi-Dealer Support**: DSRs can work for multiple dealers simultaneously

### 1.2 Key Features

| Feature | Description |
|---------|-------------|
| JWT Authentication | Secure token-based auth integrated with SattaBase |
| Role-Based Access | Dealer, DSR, Collector, Admin roles |
| DSR Invitation System | Invite-based onboarding for DSRs |
| Multi-Dealer Support | DSRs can work for multiple dealers |
| Cross-Domain SSO | Seamless billing management via SattaBase |
| Real-time Updates | Auto-refresh sales and inventory data |
| CSV Export | Export inventory, sales, suppliers |
| Responsive Design | Mobile-first responsive UI |

### 1.3 Technology Stack

**Backend (dealerbackend)**
- Django 5.2.13
- Django Ninja Extra (API framework)
- Django Channels (WebSocket support)
- PostgreSQL (database)
- Redis (cache & message broker)
- Celery (background tasks)

**Frontend (dealerfrontend)**
- Astro 5.x (meta-framework)
- Vue 3.5 (UI framework)
- TypeScript (type safety)
- Tailwind CSS (styling)
- Chart.js (charts)

**Integration**
- SattaBase (central auth & billing)
- JWT tokens
- httpOnly cookies
- API key authentication

---

## 2. Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Browser                         │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTPS
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  dealerfrontend (Port 4323)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Login      │  │  Dashboard   │  │  Components      │  │
│  │   Page       │  │  (Overview)  │  │  (Vue 3)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────┬───────────────────────────────────────┘
                      │ API Calls (Axios/Fetch)
                      │ Authorization: Bearer <JWT>
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  dealerbackend (Port 8088)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Auth Ctrl   │  │  API Ctrl    │  │  Models          │  │
│  │  (Ninja)     │  │  (Ninja)     │  │  (Django ORM)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │         SattaBase Integration (Port 8086)            │  │
│  │  - Login proxy      - Token refresh                  │  │
│  │  - User profile     - SSO authorization              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│   PostgreSQL     │          │      Redis       │
│   (Main DB)      │          │  (Cache/Celery)  │
└──────────────────┘          └──────────────────┘
```

### 2.2 Authentication Flow

```
1. User enters credentials on LoginPage.vue
2. credentials → POST /auth/login
3. dealerbackend proxies to SattaBase
4. SattaBase validates and returns JWT
5. dealerbackend sets httpOnly refresh cookie
6. Frontend stores access token in memory
7. Auto-refresh every 5 minutes
8. On expiry, refresh token used to get new access token
```

### 2.3 Multi-Dealer Architecture

```
                    ┌──────────────────┐
                    │     DSR (User)   │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Dealer A    │   │   Dealer B    │   │   Dealer C    │
│  (Assignment) │   │  (Assignment) │   │  (Assignment) │
└───────────────┘   └───────────────┘   └───────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Sales A       │   │ Sales B       │   │ Sales C       │
│ Inventory A   │   │ Inventory B   │   │ Inventory C   │
└───────────────┘   └───────────────┘   └───────────────┘

DSR sees combined dashboard but dealer-specific sales/inventory
```

---

## 3. Directory Structure

### 3.1 Backend (dealerbackend)

```
dealerbackend/
├── common/                     # Shared utilities
│   ├── __init__.py
│   ├── sattabase_client.py    # SattaBase API client
│   ├── auth_controller.py     # Auth endpoints
│   ├── sso_controller.py      # SSO endpoints
│   ├── permissions.py         # Permission definitions
│   └── permission_middleware.py # Permission middleware
├── dealer/                     # Dealer management
│   ├── __init__.py
│   ├── models.py              # DealerConfig model
│   ├── api.py                 # Dealer API
│   └── schemas.py             # Pydantic schemas
├── dsr/                        # DSR management
│   ├── __init__.py
│   ├── models.py              # DSR model + re-exports
│   ├── invitation_models.py   # Invitation & Assignment models
│   ├── invitation_api.py      # Invitation endpoints
│   ├── api.py                 # DSR endpoints
│   └── schemas.py             # DSR schemas
├── inventory/                  # Inventory management
│   ├── __init__.py
│   ├── models.py              # Product, RestockRecord
│   ├── api.py                 # Inventory endpoints
│   └── schemas.py
├── sales/                      # Sales management
│   ├── __init__.py
│   ├── models.py              # SaleRecord
│   ├── api.py                 # Sales endpoints
│   └── schemas.py
├── supplier/                   # Supplier management
│   ├── __init__.py
│   ├── models.py              # Supplier
│   ├── api.py                 # Supplier endpoints
│   └── schemas.py
├── reports/                    # Financial reports
│   ├── __init__.py
│   ├── api.py                 # Reports endpoints
│   ├── schemas.py
│   └── service.py             # Report calculation logic
├── dealercore/                 # Core configuration
│   ├── __init__.py
│   ├── settings.py            # Django settings
│   ├── urls.py                # URL routing
│   ├── api.py                 # API registration
│   ├── asgi.py                # ASGI config
│   └── wsgi.py                # WSGI config
├── manage.py                   # Django CLI
├── requirements.txt            # Dependencies
└── .env                        # Environment variables
```

### 3.2 Frontend (dealerfrontend)

```
dealerfrontend/
├── src/
│   ├── components/              # Vue components
│   │   ├── LoginForm.vue       # Login form
│   │   ├── LoginPage.vue       # Full login page
│   │   ├── SessionGuard.vue    # Auth guard
│   │   ├── ManageBillingButton.vue  # SSO button
│   │   ├── PermissionGuard.vue      # Permission wrapper
│   │   ├── App.vue             # Main app shell
│   │   ├── Overview.vue        # Dashboard
│   │   ├── Inventory.vue       # Inventory management
│   │   ├── Sales.vue           # Sales entry
│   │   ├── Collections.vue     # Pending collections
│   │   ├── Reports.vue         # Financial reports
│   │   ├── Suppliers.vue       # Supplier management
│   │   ├── BadDebt.vue         # Bad debt tracking
│   │   ├── VirtualList.vue     # Virtual scroll list
│   │   ├── BulkActionsBar.vue  # Bulk actions
│   │   └── charts/             # Chart components
│   │       ├── BaseChart.vue
│   │       └── ChartCard.vue
│   ├── composables/            # Vue composables
│   │   ├── useAuth.ts          # Auth state
│   │   ├── useSSO.ts           # SSO functionality
│   │   ├── usePermissions.ts   # Permission checking
│   │   └── useFormatters.ts    # Format utilities
│   ├── lib/                    # Utilities
│   │   └── auth.ts             # Auth library
│   ├── services/               # API services
│   │   ├── apiClient.ts        # HTTP client
│   │   └── api/                # Service modules
│   │       ├── index.ts
│   │       ├── dealer.service.ts
│   │       ├── inventory.service.ts
│   │       ├── sales.service.ts
│   │       ├── dsr.service.ts
│   │       ├── supplier.service.ts
│   │       └── reports.service.ts
│   ├── styles/                 # Shared CSS
│   │   └── utilities.css       # Animation utilities
│   ├── types.ts                # TypeScript types
│   └── env.d.ts                # Type declarations
├── astro.config.mjs            # Astro config
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
└── .env                        # Environment variables
```

---

## 4. Authentication System

### 4.1 Overview

The authentication system uses **JWT (JSON Web Tokens)** with **httpOnly cookies** for refresh tokens. It's integrated with **SattaBase** for centralized user management.

### 4.2 Token Types

| Token | Storage | Lifetime | Purpose |
|-------|---------|----------|---------|
| Access Token | Memory + sessionStorage | 60 minutes | API authentication |
| Refresh Token | httpOnly cookie | 7 days | Get new access token |
| SSO Auth Code | Server-side (Redis) | 30 seconds | Cross-domain auth |

### 4.3 Authentication Flow

#### Login
```
User Credentials
    ↓
POST /auth/login
    ↓
dealerbackend (sattabase_client.py)
    ↓
POST SattaBase /auth/login
    ↓
SattaBase validates credentials
    ↓
Returns: { access, refresh, user }
    ↓
dealerbackend sets httpOnly cookie (refresh)
    ↓
Returns: { access, user }
    ↓
Frontend stores access token
```

#### Auto-Refresh
```
Every 5 minutes OR when 401 received
    ↓
POST /auth/refresh
    ↓
Cookie sent automatically (httpOnly)
    ↓
dealerbackend verifies refresh token
    ↓
POST SattaBase /auth/token/refresh
    ↓
Returns new access token
    ↓
New cookie set (if rotation enabled)
    ↓
Frontend updates access token
```

### 4.4 Role-Based Access Control (RBAC)

#### Roles

| Role | Description | Use Case |
|------|-------------|----------|
| `dealer` | Full system access | Business owner |
| `dsr` | Sales representative | Makes sales, views inventory |
| `collector` | Order taker | Records orders under a DSR |
| `admin` | System admin | Full administrative access |

#### Permissions

**Dealer Permissions**
- `dealer.full_access` - Everything
- `dealer.settings` - Configure dealer settings
- `dealer.billing` - Access billing (via SSO)
- `dealer.reports` - Financial reports
- `dealer.invite_dsr` - Invite DSRs/Collectors

**DSR Permissions**
- `dsr.sales_create` - Create sales
- `dsr.sales_view` - View sales history
- `dsr.inventory_view` - View inventory
- `dsr.customers_view` - View customers
- `dsr.collections_view` - View pending collections

**Collector Permissions**
- `collector.order_entry` - Create orders
- `collector.sales_create` - Record sales
- `collector.customers_view` - View customers

**Shared Permissions**
- `view.dashboard` - View dashboard
- `view.inventory` - Access inventory
- `view.sales` - Access sales
- `view.reports` - Access reports
- `view.collections` - Access collections

### 4.5 Permission Checking

**Backend Example**
```python
# In controller
from common.permissions import Permission
from common.permission_middleware import check_permission

@http_post("/sales")
async def create_sale(self, request, data):
    # Check permission
    if not check_permission(request, Permission.DSR_SALES_CREATE):
        return {"detail": "Permission denied"}, 403
    
    # Create sale...
```

**Frontend Example**
```typescript
// In component
import { Permission, usePermissions } from '../composables/usePermissions';

const { can, visibleTabs } = usePermissions();

// Check single permission
if (can(Permission.DEALER_SETTINGS)) {
    showSettingsButton.value = true;
}

// Permission-based navigation
const tabs = visibleTabs.value;  // Automatically filtered
```

---

## 5. Backend Deep Dive

### 5.1 Common Package

#### sattabase_client.py

**Purpose**: Async client for SattaBase API communication

**Key Class**: `SattaBaseClient`

**Methods**:
- `async login(email, password)` → `{ access, refresh, user }`
- `async refresh_token(refresh_token)` → `{ access, refresh }`
- `async logout(refresh_token)` → None
- `async get_me(access_token)` → User profile
- `async generate_auth_code(access_token)` → SSO code

**Configuration** (via env):
- `SB_API_BASE_URL`
- `SB_SERVICE_DOMAIN`
- `SB_API_KEY`

**Error Handling**: `SattaBaseAuthError` with message, code, status_code

#### auth_controller.py

**Endpoints**:

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/login` | Public | Login with credentials |
| POST | `/auth/refresh` | Cookie | Refresh access token |
| POST | `/auth/logout` | Cookie | Logout user |
| GET | `/auth/me` | JWT | Get user info |
| GET | `/auth/sso/authorize` | JWT | Generate SSO code |

**Cookies**:
- `dealer_refresh_token` - httpOnly, Secure, SameSite=Lax

#### sso_controller.py

**Purpose**: Cross-domain SSO to SattaBase

**Endpoints**:
- `GET /sso/sattabase` → Returns `{ redirectUrl }`
- `GET /sso/sattabase/redirect` → HTTP 302 redirect

**Flow**:
1. Authenticated user clicks "Manage Billing"
2. Frontend calls `/sso/sattabase`
3. Backend calls SattaBase `/auth/authorize`
4. Returns redirect URL with one-time code
5. Frontend redirects to SattaBase
6. User is logged in on SattaBase automatically

#### permissions.py

**Enums**:
- `Role` - DEALER, DSR, COLLECTOR, ADMIN
- `Permission` - 20 permission constants

**Mapping**: `ROLE_PERMISSIONS` - role → permission list

**Functions**:
- `has_permission(role, permission)` → boolean
- `has_any_permission(role, permissions)` → boolean
- `has_all_permissions(role, permissions)` → boolean

**Class**: `PermissionChecker`
- `.can(permission)` - check single
- `.can_any(permissions)` - check any
- `.can_all(permissions)` - check all

#### permission_middleware.py

**Middleware**: `PermissionMiddleware`

**Attaches to request**:
- `request.user_role` - Role enum
- `request.is_dealer` - Boolean
- `request.permissions` - List[Permission]
- `request.permission_checker` - PermissionChecker instance

**Extraction**: Decodes JWT without verification (just for role info)

### 5.2 DSR Package

#### invitation_models.py

**DsrInvitation Model**

| Field | Type | Description |
|-------|------|-------------|
| id | CharField(PK) | UUID string |
| dealer | FK(DealerConfig) | Sending dealer |
| email | EmailField | Invitee email |
| role | ChoiceField | DSR or Collector |
| parent_dsr | FK(DSR, null) | Parent for collectors |
| token | CharField(64, unique) | Secure invite token |
| expires_at | DateTimeField | Expiration (7 days) |
| status | ChoiceField | pending/accepted/expired/revoked |
| message | TextField | Optional message |
| created_at | DateTimeField | Auto |
| accepted_at | DateTimeField | On acceptance |
| accepted_by | FK(DSR) | DSR who accepted |

**Methods**:
- `is_expired()` → boolean
- `is_valid()` → boolean
- `accept(dsr)` - Mark accepted
- `revoke()` - Mark revoked
- `expire()` - Mark expired

**Token Generation**: `secrets.token_urlsafe(32)`

**DsrDealerAssignment Model**

| Field | Type | Description |
|-------|------|-------------|
| id | CharField(PK) | UUID string |
| dsr | FK(DSR) | The DSR |
| dealer | FK(DealerConfig) | The dealer |
| role | ChoiceField | DSR or Collector |
| parent_dsr | FK(DSR, null) | Parent for collectors |
| is_active | BooleanField | Soft delete flag |
| assigned_at | DateTimeField | Auto |
| commission_rate | DecimalField(5,2) | Optional commission % |

**Methods**:
- `deactivate()` - Soft delete
- `activate()` - Re-enable

**Constraints**:
- Unique: (dsr, dealer) - One assignment per pair

#### invitation_api.py

**Controller**: `DsrInvitationController`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/invitations/create` | JWT | Create invitation |
| GET | `/invitations/list` | JWT | List dealer's invitations |
| GET | `/invitations/{token}` | Public | Validate token |
| POST | `/invitations/{token}/accept` | JWT | Accept invitation |
| PATCH | `/invitations/{id}/revoke` | JWT | Revoke invitation |
| DELETE | `/invitations/{id}` | JWT | Delete invitation |
| GET | `/invitations/assignments/list` | JWT | List assignments |
| PATCH | `/assignments/{id}/deactivate` | JWT | Deactivate assignment |
| PATCH | `/assignments/{id}/activate` | JWT | Reactivate assignment |

**Invitation Flow**:
1. Dealer: `POST /invitations/create` (email, role, parent_dsr)
2. System: Send email with token
3. DSR: Click link → `GET /invitations/{token}` (validate)
4. DSR: Accept → `POST /invitations/{token}/accept`
5. System: Create DsrDealerAssignment
6. DSR: Can now access dealer's system

### 5.3 Database Models

#### DealerConfig (dealer/models.py)

**Purpose**: Dealer configuration and settings

| Field | Type | Notes |
|-------|------|-------|
| username | CharField(PK) | Natural key (from SattaBase) |
| full_name | CharField | Display name |
| role | CharField | Usually "Dealer" |
| business_name | CharField | Company name |
| address | TextField | Business address |
| phone_number | CharField | Contact |
| email | EmailField | Contact |
| gst_number | CharField | Tax ID |
| google_map_url | URLField | Location |
| communication_number | CharField | Alt contact |
| default_currency | CharField(3) | INR, USD, EUR, etc. |
| default_locale | CharField(10) | en-IN, en-US, etc. |

#### DSR (dsr/models.py)

**Purpose**: Daily Sales Representative / Order Collector

| Field | Type | Notes |
|-------|------|-------|
| id | CharField(PK) | UUID or custom ID |
| name | CharField | Full name |
| phone | CharField | Contact |
| role | ChoiceField | DSR or Order Collector |
| parent_dsr | FK(DSR) | Hierarchy for collectors |
| parent_dsr_name | CharField | Cached parent name |

 **Note**: The dealer relationship is through `DsrDealerAssignment`, not a direct FK.

#### SaleRecord (sales/models.py)

**Purpose**: Sales transaction record

| Field | Type | Notes |
|-------|------|-------|
| id | CharField(PK) | UUID |
| date | DateField | Sale date |
| customer_name | CharField | Customer |
| customer_phone | CharField | Contact |
| product_id | CharField | FK to Product |
| product_name | CharField | Cached |
| quantity | IntegerField | Units sold |
| unit_price | DecimalField | Price per unit |
| total_amount | DecimalField | Total |
| net_amount | DecimalField | After returns |
| amount_paid | DecimalField | Cash collected |
| balance_due | DecimalField | Outstanding |
| payment_type | ChoiceField | Cash or Credit |
| is_voided | BooleanField | Refunded |
| is_closed_with_due | BooleanField | Written off |
| dsr_id | CharField | FK to DSR |
| dsr_name | CharField | Cached |
| vehicle_number | CharField | Delivery vehicle |

#### Product (inventory/models.py)

**Purpose**: Product catalog

| Field | Type | Notes |
|-------|------|-------|
| id | CharField(PK) | UUID |
| name | CharField | Product name |
| sku | CharField(unique) | Stock code |
| category | CharField | Product category |
| brand | CharField | Brand name |
| unit_price | DecimalField | Cost price |
| selling_price | DecimalField | Retail price |
| stock | IntegerField | Current stock |
| min_stock_alert | IntegerField | Low stock threshold |
| supplier_ids | ArrayField | FKs to suppliers |

### 5.4 API Response Format

**Success Response**:
```json
{
  "data": { ... },
  "message": "Operation successful"
}
```

**Error Response**:
```json
{
  "detail": "Error message",
  "code": "error_code"
}
```

**Paginated Response**:
```json
{
  "meta": {
    "total_items": 100,
    "total_pages": 10,
    "current_page": 1,
    "page_size": 10,
    "has_next": true,
    "has_previous": false
  },
  "results": [ ... ]
}
```

---

## 6. Frontend Deep Dive

### 6.1 Authentication Library (auth.ts)

**Purpose**: Core authentication functionality

**Key Functions**:

```typescript
// Token Management
getAccessToken(): string | null
setAccessToken(token: string): void
clearAccessToken(): void

// Auth Operations
login(credentials: LoginCredentials): Promise<LoginResponse>
logout(): Promise<void>
refreshToken(): Promise<boolean>
getMe(): Promise<User>

// Helpers
isAuthenticated(): boolean
initAuth(): void
startAutoRefresh(): void
stopAutoRefresh(): void
```

**Token Storage Strategy**:
- **Access Token**: 
  1. Window object (`window.__dealercore_auth.accessToken`) for view transitions
  2. sessionStorage backup for persistence
- **Refresh Token**: httpOnly cookie (set by backend)

**Auto-Refresh**: Starts on mount, runs every 5 minutes

### 6.2 Composables

#### useAuth.ts

**Returns**:
```typescript
{
  user: ComputedRef<User | null>
  isAuthenticated: ComputedRef<boolean>
  isLoading: Ref<boolean>
  error: Ref<string | null>
  login: (credentials) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
  clearError: () => void
}
```

**Usage**:
```vue
<script setup>
const { user, isAuthenticated, login } = useAuth();

async function onLogin() {
  await login({ email: '...', password: '...' });
}
</script>
```

#### usePermissions.ts

**Returns**:
```typescript
{
  role: ComputedRef<Role | null>
  isDealer: ComputedRef<boolean>
  isDSR: ComputedRef<boolean>
  isCollector: ComputedRef<boolean>
  permissions: ComputedRef<Permission[]>
  can: (permission) => boolean
  canAny: (permissions) => boolean
  canAll: (permissions) => boolean
  visibleTabs: ComputedRef<NavItem[]>
  visibleQuickActions: ComputedRef<string[]>
}
```

**Usage**:
```vue
<script setup>
const { can, Permission, visibleTabs } = usePermissions();

// Check single permission
const canEditSettings = computed(() => can(Permission.DEALER_SETTINGS));

// Permission-based navigation
const navItems = computed(() => visibleTabs.value);
</script>
```

**Visible Tabs by Role**:

| Role | Visible Tabs |
|------|--------------|
| Dealer | All (overview, inventory, suppliers, sales, collections, bad-debt, reports) |
| DSR | overview, inventory, sales, collections |
| Collector | overview, sales |

#### useSSO.ts

**Returns**:
```typescript
{
  isLoading: Ref<boolean>
  error: Ref<string | null>
  redirectToSattaBase: () => Promise<void>
  openSattaBaseInNewTab: () => Promise<void>
  clearError: () => void
}
```

**Usage**:
```vue
<script setup>
const { redirectToSattaBase } = useSSO();

async function manageBilling() {
  await redirectToSattaBase();  // Redirects to SattaBase
}
</script>
```

### 6.3 Key Components

#### LoginPage.vue

**Features**:
- Split-screen layout (branding left, form right)
- Amber gradient branding
- Responsive (stacks on mobile)
- Loading states
- Error display
- "Forgot password" placeholder

**Props**: None  
**Emits**: `@login`

#### SessionGuard.vue

**Purpose**: Protect routes requiring authentication

**Props**:
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| requireAuth | boolean | true | Whether auth is required |

**Emits**:
- `@auth-required` - When session lost
- `@session-restored` - When session recovered

**Usage**:
```vue
<SessionGuard require-auth @auth-required="redirectToLogin">
  <RouterView />
</SessionGuard>
```

#### ManageBillingButton.vue

**Variants**: button, link, menu-item

**Props**:
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | 'button' \| 'link' \| 'menu-item' | 'button' | Button style |
| openInNewTab | boolean | false | Open in new tab |

**Usage**:
```vue
<ManageBillingButton variant="button" />
<ManageBillingButton variant="link" />
<ManageBillingButton variant="menu-item" />
```

#### PermissionGuard.vue

**Purpose**: Conditional rendering based on permissions

**Props**:
| Prop | Type | Required | Description |
|------|------|----------|-------------|
| permission | Permission | No | Single permission to check |
| any | Permission[] | No | Any of these permissions |
| all | Permission[] | No | All of these permissions |
| fallback | string | No | Message to show if no access |

**Usage**:
```vue
<PermissionGuard :permission="Permission.DEALER_SETTINGS">
  <SettingsPanel />
</PermissionGuard>

<PermissionGuard :any="[Permission.DSR_SALES_CREATE, Permission.COLLECTOR_SALES_CREATE]">
  <SalesButton />
</PermissionGuard>
```

### 6.4 App Shell (App.vue)

**Features**:
- Conditional rendering: LoginPage vs Main App
- SessionGuard wrapper for auth checking
- Permission-based navigation
- Responsive sidebar + mobile bottom nav
- Loading skeletons
- Toast notifications
- Settings modal

**Reactive State**:
- `isAuthenticated` - From useAuth
- `user` - Current user
- `activeTab` - Current navigation tab
- `loading` - Global loading state

**Key Methods**:
- `handleLoginSuccess()` - On successful login
- `handleLogout()` - On logout (clears all data)
- `handleSessionRestored()` - On session recovery

---

## 7. API Reference

### Authentication Endpoints

#### POST /auth/login

**Request**:
```json
{
  "email": "dealer@example.com",
  "password": "securepassword"
}
```

**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 123,
    "email": "dealer@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true
  },
  "message": "Login successful"
}
```

**Cookies**: Sets `dealer_refresh_token` (httpOnly)

---

#### POST /auth/refresh

**Request**: None (uses cookie)

**Response**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIs...",
  "message": "Token refreshed"
}
```

---

#### POST /auth/logout

**Request**: None (uses cookie)

**Response**:
```json
{
  "message": "Logout successful"
}
```

**Cookies**: Deletes `dealer_refresh_token`

---

#### GET /auth/me

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "id": 123,
  "email": "dealer@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "subscription": {
    "status": "active",
    "plan_name": "Standard"
  },
  "access_map": {
    "max_products": 1000,
    "max_dsrs": 10
  }
}
```

---

### Invitation Endpoints

#### POST /invitations/create

**Headers**: `Authorization: Bearer <token>`

**Request**:
```json
{
  "email": "dsr@example.com",
  "role": "DSR",
  "parent_dsr_id": null,
  "message": "Join my dealership!"
}
```

**Response**:
```json
{
  "id": "inv_abc123",
  "email": "dsr@example.com",
  "role": "DSR",
  "status": "pending",
  "expires_at": "2026-06-17T10:00:00Z",
  "created_at": "2026-06-10T10:00:00Z",
  "message": "Join my dealership!",
  "invite_url": "/invitation/abc123..."
}
```

---

#### GET /invitations/list

**Query Params**:
- `status` (optional): pending, accepted, expired, revoked
- `limit` (optional): default 50

**Response**:
```json
[
  {
    "id": "inv_abc123",
    "email": "dsr@example.com",
    "role": "DSR",
    "status": "pending",
    ...
  }
]
```

---

#### GET /invitations/{token}

**Auth**: None (public endpoint)

**Response** (valid):
```json
{
  "id": "inv_abc123",
  "email": "dsr@example.com",
  "role": "DSR",
  "status": "pending",
  "expires_at": "2026-06-17T10:00:00Z",
  ...
}
```

**Error** (expired):
```json
{
  "detail": "Invitation has expired",
  "code": "invitation_expired"
}
```
(status: 410)

---

#### POST /invitations/{token}/accept

**Headers**: `Authorization: Bearer <token>`

**Response** (success):
```json
{
  "message": "Invitation accepted successfully",
  "assignment": {
    "id": "assign_xyz789",
    "dsr_id": "dsr_123",
    "dealer_username": "dealer1",
    "role": "DSR"
  }
}
```

---

#### PATCH /invitations/{invitation_id}/revoke

**Response**:
```json
{
  "message": "Invitation revoked successfully"
}
```

---

#### GET /invitations/assignments/list

**Query Params**:
- `is_active` (optional): true/false
- `role` (optional): DSR, Collector

**Response**:
```json
[
  {
    "id": "assign_xyz789",
    "dsr_id": "dsr_123",
    "dsr_name": "Ramesh Kumar",
    "dealer_username": "dealer1",
    "dealer_name": "Sharma Autos",
    "role": "DSR",
    "is_active": true,
    "assigned_at": "2026-06-10T10:30:00Z"
  }
]
```

---

### SSO Endpoints

#### GET /sso/sattabase

**Headers**: `Authorization: Bearer <token>`

**Response**:
```json
{
  "redirectUrl": "http://localhost:4321/auth/callback?code=abc123..."
}
```

---

## 8. Data Models

### Entity Relationship Diagram (Simplified)

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│  DealerConfig    │     │  DsrDealerAssignment │     │      DSR         │
├──────────────────┤     ├─────────────────────┤     ├──────────────────┤
│ PK: username     │◄────┤ FK: dealer          │────►│ PK: id           │
│    full_name     │     │ FK: dsr             │     │    name          │
│    business_name │     │    role             │     │    phone         │
│    email         │     │    is_active        │     │    role          │
└──────────────────┘     │    commission_rate  │     │ FK: parent_dsr   │
                         └─────────────────────┘     └──────────────────┘
                                   │
                                   │
                         ┌─────────────────────┐
                         │   DsrInvitation     │
                         ├─────────────────────┤
                         │ PK: id              │
                         │ FK: dealer          │
                         │    email            │
                         │    role             │
                         │    token (unique)   │
                         │    expires_at       │
                         │    status           │
                         └─────────────────────┘
```

### Model Relationships

**DealerConfig**:
- Has many: `sent_invitations` (DsrInvitation)
- Has many: `dsr_assignments` (DsrDealerAssignment)

**DSR**:
- Has many: `dealer_assignments` (DsrDealerAssignment)
- Self-referential: `parent_dsr` / `subordinates`
- Has many: `collector_invitations` (as parent)

**DsrInvitation**:
- Belongs to: `dealer` (DealerConfig)
- Belongs to: `parent_dsr` (DSR) - for collectors
- Belongs to: `accepted_by` (DSR)

**DsrDealerAssignment**:
- Belongs to: `dsr` (DSR)
- Belongs to: `dealer` (DealerConfig)
- Belongs to: `parent_dsr` (DSR) - for collectors

---

## 9. Development Setup

### 9.1 Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Redis 7+
- Git

### 9.2 Backend Setup

```bash
# 1. Clone repo (if not already)
cd dealerbackend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cat > .env << 'EOF'
# Database
DB_NAME=dealercore
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# SattaBase Integration
SB_API_BASE_URL=http://localhost:8086/api/v1
SB_SERVICE_DOMAIN=dealer.sattaspace.com
SB_API_KEY=sb_live_xxxxxxxxxxxx

# Security
SECRET_KEY=your_secret_key_here
DEBUG=True

# CORS
SL_CORS_ALLOWED_ORIGINS=http://localhost:4323,http://127.0.0.1:4323
EOF

# 5. Run migrations
python manage.py migrate

# 6. Create superuser (optional)
python manage.py createsuperuser

# 7. Start development server
uvicorn dealercore.asgi:application --port 8088 --reload

# API docs: http://localhost:8088/api/docs
```

### 9.3 Frontend Setup

```bash
# 1. Navigate to frontend
cd dealerfrontend

# 2. Install dependencies
npm install

# 3. Create .env file
cat > .env << 'EOF'
VITE_API_BASE_URL=http://localhost:8088/api
PUBLIC_API_BASE_URL=http://localhost:8088/api/v1

# For SSO to SattaBase
PUBLIC_BASE_DOMAIN_URL=http://localhost:4321
PUBLIC_SERVICE_DOMAIN=dealer.sattaspace.com
EOF

# 4. Start development server
npm run dev

# App: http://localhost:4323
```

### 9.4 Testing Your Setup

**Backend Test**:
```bash
# Check API is running
curl http://localhost:8088/api/docs

# Test auth endpoint
curl -X POST http://localhost:8088/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass"}'
```

**Frontend Test**:
- Visit http://localhost:4323
- Should see login page
- Login (requires SattaBase with test user)
- Should redirect to dashboard

---

## 10. Deployment Guide

### 10.1 Backend Deployment

**Docker (Recommended)**:

```dockerfile
# Dockerfile\FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8088

CMD ["gunicorn", "--bind", "0.0.0.0:8088", "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "dealercore.asgi:application"]
```

**Environment Variables (Production)**:
```env
DEBUG=False
SECRET_KEY=<generate_random_50_chars>
ALLOWED_HOSTS=api.dealercore.com

# Database (use managed service)
DB_HOST=your-db-host
DB_NAME=dealercore_prod
DB_USER=dealercore
DB_PASSWORD=<secure_password>

# SattaBase
SB_API_BASE_URL=https://api.sattaspace.com/api/v1
SB_SERVICE_DOMAIN=dealer.sattaspace.com
SB_API_KEY=sb_live_xxxxxxxxxxxx

# Redis
REDIS_URL=redis://your-redis-host:6379/0

# CORS
SL_CORS_ALLOWED_ORIGINS=https://app.dealercore.com
```

**Health Check**:
```bash
curl https://api.dealercore.com/api/v1/auth/choices
# Should return 200
```

### 10.2 Frontend Deployment

**Build Configuration**:
```bash
# Update astro.config.mjs
export default defineConfig({
  output: "server",
  adapter: node({
    mode: "standalone",
  }),
  server: {
    port: process.env.PORT || 4323,
    host: '0.0.0.0',
  },
  // ...
});
```

**Environment Variables (Production)**:
```env
VITE_API_BASE_URL=https://api.dealercore.com/api
PUBLIC_API_BASE_URL=https://api.dealercore.com/api/v1
PUBLIC_BASE_DOMAIN_URL=https://sattaspace.com
PUBLIC_SERVICE_DOMAIN=dealer.sattaspace.com
```

**Build & Deploy**:
```bash
# Build
npm run build

# Output in dist/
# Deploy dist/ to your hosting provider
```

### 10.3 Database Migrations

**On Each Deploy**:
```bash
# Always run migrations before starting server
python manage.py migrate

# Zero-downtime deployment:
# 1. Run migrations
# 2. Verify migrations successful
# 3. Deploy new code
# 4. Restart servers
```

---

## 11. Architecture Decisions

### 11.1 Why JWT + httpOnly Cookies?

**Decision**: Use JWT access tokens in memory + httpOnly refresh cookies

**Rationale**:
- **JWT**: Stateless, easy to scale
- **httpOnly cookies**: XSS protection (not accessible via JavaScript)
- **Refresh tokens**: Enable sliding sessions without re-login
- **Local/Fallback**: Memory for performance, sessionStorage for persistence

**Alternatives Considered**:
- Server-side sessions: Stateful, harder to scale
- Pure localStorage: XSS vulnerable
- Service workers: More complex

### 11.2 Why Junction Table for Multi-Dealer?

**Decision**: Use DsrDealerAssignment junction table instead of direct FK

**Rationale**:
- Keeps DSR model clean
- Enables metadata per dealer-dsr pair (commission, dates)
- Supports soft delete (is_active flag)
- Easy to query: dealer's DSRs, DSR's dealers

**Alternatives Considered**:
- Array field: Hard to query, no referential integrity
- Direct FK: Doesn't support multiple dealers

### 11.3 Why Async Django?

**Decision**: Use async views (Django Ninja Extra) with ASGI

**Rationale**:
- Better performance for I/O-bound operations (API calls)
- SattaBase integration is I/O heavy
- Future-proof for WebSocket support

**Trade-offs**:
- More complex than sync
- Need to use async ORM methods

### 11.4 Why Astro + Vue?

**Decision**: Use Astro as meta-framework with Vue components

**Rationale**:
- **Astro**: Fast initial load (zero JS by default)
- **Vue**: Reactive, component-based UI
- **TypeScript**: Type safety across full stack
- **Tailwind**: Utility-first CSS, rapid development

**Alternatives Considered**:
- Next.js: Good but heavier
- Pure Vue: No SSR benefits
- Nuxt: Overkill for our needs

---

## 12. Troubleshooting

### 12.1 Authentication Issues

**Problem**: Login fails with "Connection error"

**Solution**:
```bash
# 1. Check SattaBase is running
curl http://localhost:8086/api/v1/auth/choices

# 2. Check dealerbackend can reach SattaBase
# Look at logs for "Connection error"

# 3. Verify environment variables
echo $SB_API_BASE_URL

# 4. Check network connectivity
ping localhost:8086
```

**Problem**: Token refresh fails

**Solution**:
```bash
# 1. Check cookie is being set
# In browser DevTools → Application → Cookies

# 2. Verify cookie settings in response headers
# Set-Cookie: dealer_refresh_token=...; HttpOnly; SameSite=Lax

# 3. Check credentials are included in fetch
fetch(url, { credentials: 'include' })

# 4. Clear cookies and re-login
```

### 12.2 CORS Issues

**Problem**: "CORS error" in browser console

**Solution**:
```python
# In dealerbackend/settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4323",
    "http://127.0.0.1:4323",
    # Add your frontend URL
]

# Also check:
CORS_ALLOW_CREDENTIALS = True
```

### 12.3 Database Issues

**Problem**: "relation does not exist" error

**Solution**:
```bash
# Run migrations
python manage.py migrate

# If migration fails, check:
python manage.py showmigrations

# Reset (development only!)
python manage.py migrate dsr zero
python manage.py makemigrations dsr
python manage.py migrate
```

**Problem**: Slow queries

**Solution**:
```python
# Use select_related for FKs
await DsrInvitation.objects.select_related('dealer').all()

# Use prefetch_related for reverse FKs
await DSR.objects.prefetch_related('dealer_assignments').all()

# Add indexes (already in models)
# Check with EXPLAIN ANALYZE in psql
```

### 12.4 Frontend Build Issues

**Problem**: "Cannot find module"

**Solution**:
```bash
# 1. Clear node_modules
rm -rf node_modules package-lock.json
npm install

# 2. Check TypeScript config
npx tsc --noEmit

# 3. Clear Astro cache
rm -rf .astro dist
npm run build
```

**Problem**: "Chunk size warning"

**Solution**:
```javascript
// astro.config.mjs - dynamic import
const MyComponent = defineAsyncComponent(() => 
  import('./components/MyHeavyComponent.vue')
);
```

### 12.5 Permission Issues

**Problem**: User has no permissions

**Solution**:
```python
# Check middleware is loaded
MIDDLEWARE = [
    # ...
    'common.permission_middleware.PermissionMiddleware',
    # ...
]

# Debug permissions
print(request.user_role)
print(request.permissions)
print(request.permission_checker.can(Permission.VIEW_DASHBOARD))
```

### 12.6 SSO Issues

**Problem**: SSO redirect fails

**Solution**:
```bash
# 1. Check SattaBase has auth callback page
# /auth/callback?code=xxx

# 2. Verify SSO endpoint is called
# Look at Network tab in DevTools

# 3. Check token is valid
# JWT should not be expired

# 4. Verify environment
SB_FRONTEND_URL=http://localhost:4321  # SattaBase URL
```

---

## Appendix A: Environment Variable Reference

### Backend (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| SECRET_KEY | Yes | - | Django secret key |
| DEBUG | No | False | Debug mode |
| DB_NAME | Yes | dealercore | Database name |
| DB_USER | Yes | postgres | Database user |
| DB_PASSWORD | Yes | - | Database password |
| DB_HOST | Yes | localhost | Database host |
| DB_PORT | No | 5432 | Database port |
| SB_API_BASE_URL | Yes | - | SattaBase API URL |
| SB_SERVICE_DOMAIN | Yes | - | Service domain |
| SB_API_KEY | Yes | - | API key |
| REDIS_URL | No | - | Redis connection |
| SL_CORS_ALLOWED_ORIGINS | Yes | - | Allowed origins |

### Frontend (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| VITE_API_BASE_URL | Yes | http://localhost:8088/api | API base URL |
| PUBLIC_API_BASE_URL | Yes | http://localhost:8088/api/v1 | Public API URL |
| PUBLIC_BASE_DOMAIN_URL | Yes | - | SattaBase frontend URL |
| PUBLIC_SERVICE_DOMAIN | Yes | - | Service domain |

---

## Appendix B: Common Commands

### Backend

```bash
# Run server
uvicorn dealercore.asgi:application --port 8088 --reload

# Migrations
python manage.py makemigrations
python manage.py migrate
python manage.py showmigrations

# Shell
python manage.py shell

# Tests
python manage.py test

# Create superuser
python manage.py createsuperuser

# Collect static
python manage.py collectstatic
```

### Frontend

```bash
# Development
npm run dev

# Production build
npm run build

# Preview build
npm run preview

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Format
npm run format
```

---

**Document Version**: 1.0  
**Last Updated**: June 10, 2026  
**Maintainer**: DealerCore Development Team
