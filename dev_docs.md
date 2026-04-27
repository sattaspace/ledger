# Satta Ledger — Development Documentation

> Personal Accounting & Notifications SaaS
> Version: 1.0.0 | Last Updated: April 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Project Structure](#4-project-structure)
5. [Environment Setup](#5-environment-setup)
6. [Backend — Data Models](#6-backend--data-models)
7. [Backend — Pydantic Schemas](#7-backend--pydantic-schemas)
8. [Backend — Service Layer](#8-backend--service-layer)
9. [Backend — API Endpoints](#9-backend--api-endpoints)
10. [Authentication System](#10-authentication-system)
11. [Frontend — Library Layer](#11-frontend--library-layer)
12. [Frontend — Components & Pages](#12-frontend--components--pages)
13. [Security](#13-security)
14. [Infrastructure](#14-infrastructure)
15. [Conventions & Patterns](#15-conventions--patterns)

---

## 1. Project Overview

Satta Ledger is a full-stack SaaS application for personal accounting and financial notifications. The system is built with a decoupled architecture: a Django Ninja backend serves a RESTful JSON API, while an Astro.js frontend consumes it via a centralized API client. Authentication is JWT-based with OTP-verified flows for email verification, password reset, and email changes. The project is designed for multi-tenant SaaS use with role-based access, soft-delete patterns, and comprehensive rate limiting.

### Key Design Decisions

- **Email as primary identifier** — the `username` field exists only for Django compatibility; all authentication uses `email` as `USERNAME_FIELD`.
- **OTP-based verification** — no token-bearing URLs; all verification flows use 6-digit OTPs sent via email and validated against Redis cache.
- **Soft delete pattern** — user accounts are never hard-deleted; `is_deleted` and `deleted_at` fields enable data retention and potential account recovery.
- **Async-first services** — every service method has both sync and async variants (`register_user` / `aregister_user`) for compatibility with Django 5.2's async ORM under Daphne/uvicorn.
- **Separate upload endpoint for avatars** — avatar uploads use `PUT /users/me/avatar` with `multipart/form-data` (via `ninja.UploadedFile`), separate from the JSON-based profile update endpoint.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT BROWSER                           │
│                                                                 │
│   Astro.js 6 + Vue 3 Islands + Tailwind CSS 4                  │
│   (Port 4321)                                                   │
└──────────────────────────┬──────────────────────────────────────┘
                           │  JSON / multipart
                           │  JWT Bearer Auth
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DJANGO NINJA API                           │
│                      (Port 8000)                                │
│                                                                 │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐            │
│  │Controller │→ │   Service    │→ │  ORM / Cache   │            │
│  │  (HTTP)   │  │  (Business)  │  │  (PostgreSQL)  │            │
│  └──────────┘  └──────────────┘  └───────┬───────┘            │
│                                               │                 │
│                                        ┌──────▼──────┐         │
│                                        │   Redis     │         │
│                                        │ OTP / Rate   │         │
│                                        │ Limit / Celery│        │
│                                        └─────────────┘         │
│                                                                 │
│  Apps: users | api | common                                      │
│  Auth: ninja_jwt (access + refresh + blacklist)                  │
└─────────────────────────────────────────────────────────────────┘
```

### Request Lifecycle

1. **Frontend** — Vue component calls a function from `src/lib/auth.ts`
2. **API Client** — `src/lib/api.ts` wraps the call with JWT headers and error handling
3. **Backend Router** — Ninja Extra auto-discovers controllers, routes to handler
4. **Controller** — validates rate limit, parses payload via Pydantic schema
5. **Service** — executes business logic (OTP generation, cache checks, DB writes)
6. **Response** — serialized via `ModelSchema` / `Schema`, returned as JSON

### Authentication Flow

```
Register ──→ Auto-send email verify OTP
    │
    ▼
Login ──→ Validate credentials ──→ Issue JWT pair ──→ Record login history
    │
    ├─ Access Token (60 min) — used in Authorization: Bearer header
    └─ Refresh Token (7 days) — used to obtain new token pair
         │
         └─ 401 response → auto-refresh via api.ts → retry original request
```

---

## 3. Tech Stack

### Backend

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.10+ |
| Framework | Django + Django Ninja | 5.2 / latest |
| ASGI Server | Daphne | latest |
| Database | PostgreSQL | latest |
| Cache / Broker | Redis | latest |
| Task Queue | Celery + django-celery-beat | latest |
| JWT | ninja_jwt | latest |
| API Framework | ninja_extra | latest |
| Email | Django SMTP (Gmail) | — |
| File Storage | Django FileSystemStorage (Pillow) | — |

### Frontend

| Component | Technology | Version |
|---|---|---|
| Framework | Astro.js | 6.x |
| UI Islands | Vue 3 | 3.5+ |
| Styling | Tailwind CSS | 4.x |
| Language | TypeScript | 5.9+ |
| Runtime | Node.js | 22.12+ |
| Build | Vite (via Astro) | — |

### Infrastructure

| Component | Technology |
|---|---|
| Containers | Docker Compose (PostgreSQL, Redis) |
| Tunneling | ngrok (for local development) |
| Version Control | Git + GitHub |

---

## 4. Project Structure

```
sattaledger/
├── backend/
│   ├── api/                          # API configuration
│   │   ├── views.py                  # NinjaExtraAPI instance, exception handlers
│   │   └── ...
│   ├── common/                       # Shared utilities
│   │   ├── models.py                 # TimeStampedModel, SoftDeleteModel, ActivatorModel
│   │   ├── permissions.py            # IsAuthenticated, IsAdmin, IsVerified, IsSelfOrAdmin
│   │   ├── rate_limit.py             # check_rate_limit(), get_client_ip()
│   │   ├── exceptions.py             # Custom APIException classes
│   │   └── ...
│   ├── users/                        # User authentication & profile app
│   │   ├── models.py                 # User, UserLoginHistory, Choice constants
│   │   ├── managers.py               # CustomUserManager (sync + async)
│   │   ├── schemas.py                # Pydantic request/response schemas
│   │   ├── services.py               # AuthService, UserService (business logic)
│   │   ├── controllers.py            # AuthController, UserController (HTTP routing)
│   │   ├── admin.py                  # Django admin registration
│   │   ├── signals.py                # Model signals
│   │   └── migrations/               # Database migrations
│   ├── sattaledger/                  # Django project settings
│   │   ├── settings.py               # All configuration
│   │   ├── urls.py                   # Root URL configuration
│   │   ├── asgi.py                   # ASGI entry (Daphne)
│   │   └── ...
│   ├── manage.py
│   └── media/                        # Uploaded files (avatars)
│       └── avatars/YYYY/MM/
│
├── frontend/
│   ├── src/
│   │   ├── lib/                      # Shared utilities
│   │   │   ├── api.ts                # Centralized API client (fetch wrapper)
│   │   │   ├── auth.ts               # Auth functions + types + choice options
│   │   │   └── toast.ts              # Toast notification system
│   │   ├── components/
│   │   │   ├── astro/                # Astro static components
│   │   │   │   ├── Navbar.astro      # Top navigation bar
│   │   │   │   ├── Sidebar.astro     # Dashboard sidebar
│   │   │   │   ├── EmptyState.astro  # Empty state display
│   │   │   │   └── LoadingSpinner.astro
│   │   │   └── vue/                  # Vue interactive islands
│   │   │       ├── LoginForm.vue
│   │   │       ├── RegisterForm.vue
│   │   │       ├── ForgotPasswordForm.vue
│   │   │       ├── ResetPasswordForm.vue
│   │   │       ├── VerifyEmailForm.vue
│   │   │       ├── ProfileCard.vue   # Profile view/edit + avatar upload
│   │   │       ├── SettingsPanel.vue # Account settings (password, email, delete)
│   │   │       ├── SearchableSelect.vue  # Reusable dropdown with search
│   │   │       └── DashboardHome.vue
│   │   ├── layouts/
│   │   │   ├── BaseLayout.astro      # Root layout
│   │   │   ├── AuthLayout.astro      # Unauthenticated layout
│   │   │   └── DashboardLayout.astro # Authenticated layout (navbar + sidebar)
│   │   ├── pages/
│   │   │   ├── index.astro           # Landing / redirect
│   │   │   ├── auth/
│   │   │   │   ├── login.astro
│   │   │   │   ├── register.astro
│   │   │   │   ├── forgot-password.astro
│   │   │   │   ├── reset-password.astro
│   │   │   │   └── verify-email.astro
│   │   │   └── dashboard/
│   │   │       ├── index.astro
│   │   │       ├── profile.astro     # Profile management
│   │   │       └── settings.astro    # Account settings
│   │   └── env.d.ts
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml                # PostgreSQL + Redis
├── .env                              # Environment variables (not in repo)
└── dev_docs.md                       # This file
```

---

## 5. Environment Setup

### Prerequisites

- Python 3.10+
- Node.js 22.12+
- Docker & Docker Compose
- Git

### Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services
docker ps
# → local-postgres on port 5432
# → local-redis on port 6379
```

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install django daphne ninja-extra ninja_jwt django-ninja-jwt-token-blacklist \
    django-cors-headers django-redis channels django-celery-results \
    django-celery-beat django-environ Pillow

# Create .env file (see Environment Variables section below)

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver 0.0.0.0:8000
# Or with Daphne (ASGI):
daphne -b 0.0.0.0 -p 8000 sattaledger.asgi:application
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Development server (port 4321)
npm run dev

# Type checking
npm run check

# Production build
npm run build
```

### Environment Variables

| Variable | Description | Example |
|---|---|---|
| `SF_DEBUG` | Debug mode | `True` |
| `SF_SECRET_KEY` | Django secret key | `django-insecure-...` |
| `SF_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `SFDB_NAME` | PostgreSQL database name | `django_db` |
| `SFDB_USER` | PostgreSQL username | `django_user` |
| `SFDB_PASSWORD` | PostgreSQL password | `django_password` |
| `SFDB_HOST` | PostgreSQL host | `localhost` |
| `SFDB_PORT` | PostgreSQL port | `5432` |
| `SF_REDIS_HOST` | Redis host | `localhost` |
| `SF_REDIS_PORT` | Redis port | `6379` |
| `SF_EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `SF_EMAIL_PORT` | SMTP port | `587` |
| `SF_EMAIL_HOST_USER` | SMTP username | `ledger@gmail.com` |
| `SF_EMAIL_HOST_PASSWORD` | SMTP password (app password) | `app-specific-pass` |
| `SF_DEFAULT_FROM_EMAIL` | Sender email | `ledger@gmail.com` |
| `JWT_SIGNING_KEY` | JWT signing key (prod) | `your-random-key` |
| `JWT_ACCESS_TOKEN_MINUTES` | Access token lifetime | `60` |
| `JWT_REFRESH_TOKEN_DAYS` | Refresh token lifetime | `7` |
| `VITE_API_BASE_URL` | Frontend API URL | `http://localhost:8000/api/v1` |

> **Note**: In production, `JWT_SIGNING_KEY` must be explicitly set and must differ from `SF_SECRET_KEY`. The server will refuse to start without it.

---

## 6. Backend — Data Models

### Abstract Base Models (`common/models.py`)

#### TimeStampedModel

Automatically tracks creation and modification timestamps on every model that inherits it.

| Field | Type | Description |
|---|---|---|
| `created_at` | DateTimeField | Auto-set on creation (`auto_now_add=True`) |
| `updated_at` | DateTimeField | Auto-updated on every save (`auto_now=True`) |

#### SoftDeleteModel

Provides soft-delete functionality. Instead of permanently deleting records, marks them as deleted with a timestamp.

| Field | Type | Default | Description |
|---|---|---|---|
| `is_deleted` | BooleanField | `False` | Whether the record has been soft-deleted |
| `deleted_at` | DateTimeField | `null` | Timestamp of deletion |

**Methods:**
- `soft_delete()` — sets `is_deleted=True` and `deleted_at=now()`
- `restore()` — sets `is_deleted=False` and `deleted_at=None`

#### ActivatorModel

Tracks activation status of records.

| Field | Type | Default | Description |
|---|---|---|---|
| `is_active` | BooleanField | `True` | Whether the record is active |
| `activated_at` | DateTimeField | `null` | Timestamp of activation |

**Methods:**
- `activate()` — sets `is_active=True` and `activated_at=now()`
- `deactivate()` — sets `is_active=False`

### User Model (`users/models.py`)

Inherits from `AbstractUser`, `TimeStampedModel`, and `SoftDeleteModel`.

| Field | Type | Constraints | Description |
|---|---|---|---|
| `username` | CharField(150) | nullable, not unique | Legacy field (not used for auth) |
| `slug` | UUIDField | unique, db_index, auto-generated | Public identifier for URLs |
| `email` | EmailField(255) | unique, db_index, `USERNAME_FIELD` | Primary identifier |
| `first_name` | CharField(150) | blank | First name |
| `last_name` | CharField(150) | blank | Last name |
| `phone` | CharField(30) | blank, default `""` | Phone number |
| `avatar` | ImageField | blank, null, upload `avatars/%Y/%m/` | Profile picture |
| `timezone` | CharField(50) | ChoiceField, default `UTC` | IANA timezone |
| `currency` | CharField(3) | ChoiceField, default `USD` | ISO 4217 currency code |
| `language` | CharField(10) | ChoiceField, default `en` | ISO 639-1 language code |
| `is_email_verified` | BooleanField | default `False` | Email verification status |
| `last_login_ip` | GenericIPAddressField | nullable | IP of last login |
| `role` | CharField(20) | ChoiceField, default `member` | User role (owner/admin/member) |
| `is_active` | BooleanField | from AbstractUser | Account active status |
| `is_deleted` | BooleanField | from SoftDeleteModel | Soft-delete flag |
| `deleted_at` | DateTimeField | from SoftDeleteModel | Deletion timestamp |
| `created_at` | DateTimeField | from TimeStampedModel | Creation timestamp |
| `updated_at` | DateTimeField | from TimeStampedModel | Last modification |

**Database table:** `users_user`

**Properties:**
- `full_name` → `"First Last"` or falls back to email
- `display_name` → first name or email prefix (before `@`)

**Choice Fields:**

| Field | Choices | Count |
|---|---|---|
| Role | owner, admin, member | 3 |
| Timezone | UTC + 54 IANA timezones | 55 |
| Currency | USD, EUR, GBP, JPY, ... | 40 |
| Language | en, es, fr, de, ... | 30 |

### UserLoginHistory Model (`users/models.py`)

Tracks every successful login event for security auditing.

| Field | Type | Description |
|---|---|---|
| `id` | BigAutoField | Primary key |
| `user` | ForeignKey(User) | Related user (CASCADE delete) |
| `ip_address` | GenericIPAddressField | Login origin IP |
| `user_agent` | TextField | Browser/client UA string (truncated to 500 chars) |
| `created_at` | DateTimeField | Login timestamp (auto) |

**Database table:** `users_login_history`

---

## 7. Backend — Pydantic Schemas

All schemas are defined in `users/schemas.py`. They serve as both request validation contracts and automatic OpenAPI documentation.

### Type Aliases for Choice Fields

```python
RoleType = Literal["owner", "admin", "member"]
TimezoneType = Literal["UTC", "America/New_York", ...]  # 55 values
CurrencyType = Literal["USD", "EUR", "GBP", ...]         # 40 values
LanguageType = Literal["en", "es", "fr", ...]            # 30 values
```

### Request Schemas

| Schema | Fields | Used By |
|---|---|---|
| `RegisterInputSchema` | email, password, first_name, last_name?, timezone, currency, language | `POST /auth/register` |
| `LoginInputSchema` | email, password | `POST /auth/login` |
| `TokenRefreshInputSchema` | refresh | `POST /auth/token/refresh` |
| `TokenVerifyInputSchema` | token | `POST /auth/token/verify` |
| `TokenBlacklistInputSchema` | refresh | `POST /auth/token/blacklist` |
| `PasswordResetRequestSchema` | email | `POST /auth/password-reset/request` |
| `PasswordResetConfirmSchema` | email, otp, new_password, confirm_password | `POST /auth/password-reset/confirm` |
| `EmailVerifyRequestSchema` | email | `POST /auth/verify-email/request` |
| `EmailVerifyConfirmSchema` | email, otp | `POST /auth/verify-email/confirm` |
| `ChangeEmailRequestSchema` | current_password, new_email | `POST /users/me/change-email` |
| `ChangeEmailConfirmOTPSchema` | otp | `POST /users/me/change-email/confirm` |
| `ChangePasswordInputSchema` | current_password, new_password, confirm_password | `POST /users/me/change-password` |
| `PasswordConfirmSchema` | current_password | `POST /users/me/confirm-identity` |
| `DeleteAccountRequestSchema` | current_password | `POST /users/me/delete-account` |
| `UserProfileUpdateInputSchema` | first_name?, last_name?, phone?, timezone?, currency?, language? | `PUT /users/me` |

### Response Schemas

| Schema | Fields | Used By |
|---|---|---|
| `TokenOutputSchema` | access, refresh | Login, token refresh |
| `UserOutputSchema` | id, slug, email, first_name, last_name, phone, avatar, timezone, currency, language, is_email_verified, is_active, role, created_at, full_name, display_name | All user profile endpoints |
| `ChoicesSchema` | timezones: ChoiceItemSchema[], currencies: ChoiceItemSchema[], languages: ChoiceItemSchema[] | `GET /auth/choices` |
| `ChoiceItemSchema` | value: str, label: str | Used inside ChoicesSchema |
| `MessageSchema` | message, success | All action endpoints |

### Password Validation

All password fields are validated by `_validate_password_strength()`:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (`!@#$%^&*(),.?":{}|<>_\-+=[]\/~`;'`)

### OTP Validation

All OTP fields are validated to be exactly 6 digits (numeric string).

---

## 8. Backend — Service Layer

Services encapsulate all business logic, keeping controllers thin. Located in `users/services.py`.

### AuthService

Handles all authentication-related operations.

| Method | Description | Async Variant |
|---|---|---|
| `register_user()` | Create new user account | `aregister_user()` |
| `authenticate_user()` | Validate email/password | `aauthenticate_user()` |
| `record_login()` | Update `last_login`, create login history entry | `arecord_login()` |
| `change_password()` | Verify current password, set new | `achange_password()` |
| `confirm_identity()` | Verify current password (gate for sensitive ops) | `aconfirm_identity()` |
| `request_password_reset()` | Generate OTP, cache it, send email | `arequest_password_reset()` |
| `confirm_password_reset()` | Validate OTP, set new password | `aconfirm_password_reset()` |
| `request_email_verification()` | Generate OTP, cache, send email | `arequest_email_verification()` |
| `confirm_email_verification()` | Validate OTP, mark email as verified | `aconfirm_email_verification()` |
| `request_email_change()` | Verify password, validate new email, generate OTP | `arequest_email_change()` |
| `confirm_email_change_otp()` | Validate OTP, apply email change | `aconfirm_email_change_otp()` |
| `delete_account()` | Verify password, soft_delete user, deactivate | `adelete_account()` |

### UserService

Handles user profile operations.

| Method | Description | Async Variant |
|---|---|---|
| `get_user_by_id()` | Get user by primary key | `aget_user_by_id()` |
| `get_user_by_email()` | Get user by email (returns None if not found) | `aget_user_by_email()` |
| `get_active_user_by_email()` | Get active, non-deleted user by email | `aget_active_user_by_email()` |
| `get_user_by_slug()` | Get user by public UUID slug | `aget_user_by_slug()` |
| `update_profile()` | Update whitelisted profile fields | `aupdate_profile()` |

### OTP Management

All OTP flows follow the same pattern:

1. **Generate** — cryptographically random 6-digit string via `secrets.randbelow(1_000_000).zfill(6)`
2. **Store** — in Redis cache with 10-minute TTL
3. **Send** — via Django's `send_mail()` to the appropriate email address
4. **Validate** — compare against cached OTP, track failed attempts (max 5), invalidate after too many failures
5. **Cleanup** — delete OTP and attempt counter from cache after success or max failures

Cache key patterns:
- Password reset: `pwreset_otp:{email}`, `pwreset_attempts:{email}`
- Email verification: `email_verify_otp:{email}`, `email_verify_attempts:{email}`
- Email change: `email_change_data:{user_id}`, `email_change_attempts:{user_id}`

### Custom User Manager (`users/managers.py`)

The `CustomUserManager` extends `BaseUserManager` with:
- `create_user()` / `acreate_user()` — always sets `is_active=False`, `is_email_verified=False`
- `create_superuser()` / `acreate_superuser()` — sets `is_staff=True`, `is_superuser=True`
- `get_by_natural_key()` / `aget_by_natural_key()` — excludes soft-deleted users
- `email_exists()` / `aemail_exists()` — checks for email uniqueness
- `active()` — returns queryset of active, non-deleted users

---

## 9. Backend — API Endpoints

All endpoints are documented in the auto-generated OpenAPI spec at `/api/v1/docs`.

### Public Endpoints (no auth required)

#### Authentication (`/api/v1/auth/`)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| GET | `/auth/choices` | Get timezone/currency/language choices | — | 200: `ChoicesSchema` |
| POST | `/auth/register` | Register new account | `RegisterInputSchema` | 201: `MessageSchema` |
| POST | `/auth/login` | Login with credentials | `LoginInputSchema` | 200: `TokenOutputSchema` |
| POST | `/auth/token/refresh` | Refresh access token | `TokenRefreshInputSchema` | 200: `TokenOutputSchema` |
| POST | `/auth/token/verify` | Verify access token validity | `TokenVerifyInputSchema` | 200: `MessageSchema` |
| POST | `/auth/token/blacklist` | Blacklist a refresh token | `TokenBlacklistInputSchema` | 200: `MessageSchema` |

#### Password Reset (OTP-based)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/auth/password-reset/request` | Request password reset OTP | `PasswordResetRequestSchema` | 200: `MessageSchema` |
| POST | `/auth/password-reset/confirm` | Reset password with OTP | `PasswordResetConfirmSchema` | 200: `MessageSchema` |

#### Email Verification (OTP-based)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/auth/verify-email/request` | Request verification OTP | `EmailVerifyRequestSchema` | 200: `MessageSchema` |
| POST | `/auth/verify-email/confirm` | Verify email with OTP | `EmailVerifyConfirmSchema` | 200: `MessageSchema` |

### Protected Endpoints (JWT Bearer token required)

#### Profile (`/api/v1/users/`)

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| GET | `/users/me` | Get current user profile | — | 200: `UserOutputSchema` |
| GET | `/users/{slug}` | Get user by slug | — | 200: `UserOutputSchema` |
| PUT | `/users/me` | Update profile fields | `UserProfileUpdateInputSchema` | 200: `UserOutputSchema` |
| PUT | `/users/me/avatar` | Upload/update avatar | `multipart/form-data` (file field: `avatar`) | 200: `UserOutputSchema` |
| DELETE | `/users/me/avatar` | Remove avatar | — | 200: `UserOutputSchema` |

#### Account Security

| Method | Path | Description | Request Body | Response |
|---|---|---|---|---|
| POST | `/users/me/change-password` | Change password | `ChangePasswordInputSchema` | 200: `MessageSchema` |
| POST | `/users/me/confirm-identity` | Verify identity (password gate) | `PasswordConfirmSchema` | 200: `MessageSchema` |
| POST | `/users/me/change-email` | Request email change OTP | `ChangeEmailRequestSchema` | 200: `MessageSchema` |
| POST | `/users/me/change-email/confirm` | Confirm email change with OTP | `ChangeEmailConfirmOTPSchema` | 200: `MessageSchema` |
| POST | `/users/me/delete-account` | Soft-delete account | `DeleteAccountRequestSchema` | 200: `MessageSchema` |
| POST | `/users/me/logout` | Logout notification | — | 200: `MessageSchema` |

### Error Response Format

All endpoints return errors in this format:

```json
{
  "detail": "Validation error",
  "errors": [
    { "field": "email", "message": "A user with this email address already exists." }
  ],
  "code": "validation_error"
}
```

For simple errors:
```json
{
  "message": "Invalid email or password.",
  "success": false
}
```

---

## 10. Authentication System

### JWT Configuration

| Setting | Default | Description |
|---|---|---|
| `ACCESS_TOKEN_LIFETIME` | 60 minutes | Short-lived token for API access |
| `REFRESH_TOKEN_LIFETIME` | 7 days | Long-lived token for obtaining new access tokens |
| `ROTATE_REFRESH_TOKENS` | `True` | New refresh token issued on each refresh |
| `BLACKLIST_AFTER_ROTATION` | `True` | Old refresh token blacklisted after rotation |
| `ALGORITHM` | HS256 | JWT signing algorithm |
| `SIGNING_KEY` | `SECRET_KEY` (dev) / `JWT_SIGNING_KEY` (prod) | Signing key |
| `USER_ID_FIELD` | `id` | User model field stored in JWT |
| `USER_ID_CLAIM` | `user_id` | JWT claim name for user ID |

### Token Storage

Tokens are stored in `localStorage` on the client:
- `access_token` — used in `Authorization: Bearer` header
- `refresh_token` — used for token refresh

### Token Refresh Flow (Automatic)

The `api.ts` client handles 401 responses automatically:

1. Original request fails with 401
2. If a refresh token exists, call `POST /auth/token/refresh`
3. On success: store new tokens, retry original request with new access token
4. On failure: clear tokens, redirect to `/auth/login`

This is transparent to all Vue components — they simply call `apiClient.get()`, `.post()`, etc. and never handle token refresh manually.

### OTP Security

| Property | Value |
|---|---|
| OTP Length | 6 digits |
| OTP Generation | `secrets.randbelow(1_000_000).zfill(6)` (cryptographically random) |
| OTP Expiry | 10 minutes (600 seconds) |
| Max Attempts | 5 per OTP |
| After Max Failures | OTP invalidated, user must request a new one |
| Storage | Redis cache (not database) |

### Rate Limiting

Rate limiting is implemented via Redis-based sliding window. Configured per endpoint:

| Endpoint | Key Pattern | Max Attempts | Window |
|---|---|---|---|
| Register | `register:{client_ip}` | 5 | 1 hour |
| Login | `login:{client_ip}` | 10 | 15 minutes |
| Password reset request | `pwreset_req:{client_ip}` | 5 | 1 hour |
| Password reset confirm | `pwreset_confirm:{client_ip}` | 5 | 1 hour |
| Email verify request | `email_verify_req:{client_ip}` | 5 | 5 minutes |
| Email verify confirm | `email_verify_confirm:{client_ip}` | 10 | 5 minutes |
| Identity confirmation | `confirm_identity:{user_id}:{client_ip}` | 10 | 1 hour |
| Email change | `email_change:{user_id}:{client_ip}` | 5 | 1 hour |
| Email change confirm | `email_change_confirm:{user_id}:{client_ip}` | 10 | 1 hour |
| Account deletion | `delete_account:{user_id}:{client_ip}` | 3 | 1 hour |

Client IP is extracted from `X-Forwarded-For` header (supports ngrok/reverse proxy).

---

## 11. Frontend — Library Layer

### API Client (`src/lib/api.ts`)

Centralized fetch wrapper that handles authentication, error handling, and token refresh.

**Key features:**
- Auto-attaches `Authorization: Bearer` header from localStorage
- Auto-refreshes expired access tokens (transparent 401 handling)
- Standardized error format with field-level error extraction
- Configurable base URL via `VITE_API_BASE_URL` env variable
- FormData upload support via `upload()` and `uploadPut()` methods
- `getMediaUrl()` helper to resolve relative media paths against the backend origin

**Exported API:**

```typescript
apiClient.get<T>(path, options?)
apiClient.post<T>(path, body?, options?)
apiClient.put<T>(path, body?, options?)
apiClient.patch<T>(path, body?, options?)
apiClient.delete<T>(path, options?)
apiClient.upload<T>(path, formData)       // POST with multipart/form-data
apiClient.uploadPut<T>(path, formData)    // PUT with multipart/form-data

authHelpers.setTokens(access, refresh)
authHelpers.clearTokens()
authHelpers.isAuthenticated()

getMediaUrl(path)  // "/media/avatars/..." → full backend URL
```

### Auth Library (`src/lib/auth.ts`)

Authentication functions and shared types.

**Exported types:**

```typescript
interface LoginPayload { email: string; password: string; }
interface RegisterPayload { email, password, first_name, last_name, timezone, currency, language }
interface AuthTokens { access: string; refresh: string; }
interface UserProfile { id, slug, email, first_name, last_name, phone, avatar,
                        timezone, currency, language, is_email_verified, role,
                        created_at, full_name, display_name }
```

**Choice options (served from backend via API):**

Timezone, currency, and language choices are **not hardcoded** in the frontend. They are fetched from the backend `GET /auth/choices` endpoint, which reads directly from Django model enums (`TimezoneChoices`, `CurrencyChoices`, `LanguageChoices`). This ensures the frontend and backend always stay in sync — the same pattern used for user roles.

```typescript
interface ChoiceOption { value: string; label: string; }
interface Choices {
  timezones: ChoiceOption[];
  currencies: ChoiceOption[];
  languages: ChoiceOption[];
}
```

```typescript
fetchChoices(): Promise<Choices>        // Fetches from GET /auth/choices, caches in-memory
getCachedChoices(): Choices | null       // Returns cached data without API call
```

**Exported functions:**

| Function | Endpoint | Description |
|---|---|---|
| `login(payload)` | POST /auth/login | Login and store tokens |
| `register(payload)` | POST /auth/register | Register new account |
| `logout()` | POST /users/me/logout | Clear tokens, redirect |
| `requestPasswordReset(email)` | POST /auth/password-reset/request | Request password reset OTP |
| `confirmPasswordReset(...)` | POST /auth/password-reset/confirm | Reset password with OTP |
| `changePassword(...)` | POST /users/me/change-password | Change password (authenticated) |
| `requestEmailChange(...)` | POST /users/me/change-email | Request email change OTP |
| `confirmEmailChangeOTP(otp)` | POST /users/me/change-email/confirm | Confirm email change |
| `requestEmailVerification(email)` | POST /auth/verify-email/request | Request email verify OTP |
| `verifyEmail(email, otp)` | POST /auth/verify-email/confirm | Verify email with OTP |
| `getCurrentUser()` | GET /users/me | Get current user profile |
| `updateProfile(data)` | PUT /users/me | Update profile fields |
| `updateAvatar(file)` | PUT /users/me/avatar | Upload avatar (multipart) |
| `deleteAvatar()` | DELETE /users/me/avatar | Remove avatar |
| `deleteAccount(password)` | POST /users/me/delete-account | Soft-delete account |
| `isAuthenticated()` | — | Check localStorage for token |
| `requireAuth()` | — | Redirect to login if unauthenticated |
| `getErrorMessage(error)` | — | Extract user-friendly error string |
| `fetchChoices()` | GET /auth/choices | Fetch timezone/currency/language choices (cached) |
| `getCachedChoices()` | — | Return cached choices if already fetched |
| `detectUserTimezone(choices?)` | — | Auto-detect browser timezone, validate against choices |
| `detectUserLanguage(choices?)` | — | Auto-detect browser language, validate against choices |

### Toast System (`src/lib/toast.ts`)

Lightweight DOM-based toast notification system with zero external dependencies.

```typescript
showToast(message, type?, options?)
// type: "success" | "error" | "info" | "warning"
// options: { duration?: number, action?: { label, onClick } }
```

---

## 12. Frontend — Components & Pages

### Auth Pages (unauthenticated)

| Page | Path | Component | Description |
|---|---|---|---|
| Login | `/auth/login` | `LoginForm.vue` | Email/password login form |
| Register | `/auth/register` | `RegisterForm.vue` | Registration with timezone/currency/language selection |
| Forgot Password | `/auth/forgot-password` | `ForgotPasswordForm.vue` | Enter email to request reset OTP |
| Reset Password | `/auth/reset-password` | `ResetPasswordForm.vue` | Enter OTP + new password |
| Verify Email | `/auth/verify-email` | `VerifyEmailForm.vue` | Enter OTP to verify email |

All auth pages use `AuthLayout.astro` which provides a centered, minimal layout.

### Dashboard Pages (authenticated)

| Page | Path | Component | Description |
|---|---|---|---|
| Dashboard | `/dashboard/` | `DashboardHome.vue` | Overview / landing after login |
| Profile | `/dashboard/profile` | `ProfileCard.vue` | View/edit profile, avatar upload |
| Settings | `/dashboard/settings` | `SettingsPanel.vue` | Password change, email change, account deletion |

All dashboard pages use `DashboardLayout.astro` which includes `Navbar.astro` and `Sidebar.astro`.

### Reusable Components

| Component | Type | Description |
|---|---|---|
| `SearchableSelect.vue` | Vue island | Dropdown with search, grouped options, keyboard nav |
| `EmptyState.astro` | Astro component | Centered empty state with icon and message |
| `LoadingSpinner.astro` | Astro component | CSS-only loading spinner |

### Avatar Upload Implementation

The avatar system spans multiple layers:

1. **UI** (`ProfileCard.vue`) — Hidden `<input type="file">` triggered by a camera icon button. Supports upload (blue circle, bottom-right) and remove (red X, top-right). Shows spinner during upload. Client-side validation: JPEG/PNG/GIF/WebP, max 2 MB.

2. **Auth library** (`auth.ts`) — `updateAvatar(file)` validates client-side, constructs `FormData`, calls `apiClient.uploadPut()`. `deleteAvatar()` calls `apiClient.delete()`.

3. **API client** (`api.ts`) — `uploadPut()` sends FormData with `Content-Type` omitted (browser auto-sets `multipart/form-data` boundary). `getMediaUrl()` converts relative `/media/...` paths to full backend URLs.

4. **Backend** (`controllers.py`) — `PUT /users/me/avatar` uses `ninja.UploadedFile = File(..., alias="avatar")` to parse multipart uploads. Validates file type and size server-side. Deletes old avatar file before saving new one.

---

## 13. Security

### Middleware Stack

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",           # CORS handling
    "django.middleware.common.CommonMiddleware",
    "ninja.compatibility.files.fix_request_files_middleware",  # File upload support
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

### JWT Authentication Flow

1. Client sends `Authorization: Bearer <access_token>` header
2. `JWTAuth.authenticate()` decodes the token, extracts `user_id`
3. User is fetched from DB with `is_active=True, is_deleted=False` filter
4. If valid, `request.user` is set; otherwise returns `None` (401)

### Password Security

- Passwords hashed by Django's PBKDF2 (configurable via `AUTH_PASSWORD_VALIDATORS`)
- Custom validator enforces: min 8 chars, uppercase, lowercase, digit, special character
- `check_password()` used for all password verification (never raw comparison)
- Current password required for all sensitive operations (email change, account deletion)

### OTP Security

- Cryptographically random generation (`secrets` module, not `random`)
- 10-minute expiry in Redis (volatile storage)
- Max 5 attempts per OTP; automatic invalidation after limit
- Separate cache keys for OTP value and attempt counter

### Soft Delete

- Accounts are never hard-deleted from the database
- `soft_delete()` sets `is_deleted=True`, `deleted_at=now()`, and `is_active=False`
- All queries filter out soft-deleted users (`is_deleted=False`)
- `get_by_natural_key()` (used by Django auth backend) excludes deleted users
- JWT auth explicitly checks `is_deleted=False`

### Production Security Headers

In production (`DEBUG=False`):
- `CSRF_COOKIE_SECURE = True`
- `SESSION_COOKIE_SECURE = True`
- `SESSION_COOKIE_SAMESITE = "lax"`
- `SESSION_COOKIE_HTTPONLY = True`
- `SECURE_HSTS_SECONDS = 31536000` (1 year)
- `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SECURE_HSTS_PRELOAD = True`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
- `JWT_SIGNING_KEY` required (must not fall back to `SECRET_KEY`)

### Custom Permissions (`common/permissions.py`)

| Permission | Description |
|---|---|
| `IsAuthenticated` | User must be logged in |
| `IsAdmin` | User must be staff |
| `IsVerified` | User must have verified email |
| `IsSelfOrAdmin` | User must be the object owner or staff |

---

## 14. Infrastructure

### Docker Compose

```yaml
services:
  redis:      # Port 6379 — OTP cache, rate limiting, Celery broker, Channels
  db:         # Port 5432 — PostgreSQL database
```

### Redis Usage

| Purpose | DB | TTL |
|---|---|---|
| OTP storage (all flows) | DB 0 (via default cache) | 10 minutes |
| Rate limiting | DB 0 (via default cache) | Variable (5 min to 1 hour) |
| Celery broker | DB 1 | — |
| Django Channels | DB 0 (configured separately) | — |

### Email Configuration

| Setting | Development | Production |
|---|---|---|
| Backend | `console.EmailBackend` (prints to terminal) | SMTP (Gmail) |
| Host | — | `smtp.gmail.com` |
| Port | — | 587 |
| TLS/SSL | — | SSL enabled |

### File Storage

| Setting | Value |
|---|---|
| `MEDIA_URL` | `/media/` |
| `MEDIA_ROOT` | `backend/media/` |
| Avatar upload path | `media/avatars/YYYY/MM/` |
| Allowed types | JPEG, PNG, GIF, WebP |
| Max size | 2 MB |
| Storage backend | `FileSystemStorage` (local disk) |
| Production serving | Reverse proxy (nginx) required |

---

## 15. Conventions & Patterns

### Backend Patterns

**Controller → Service → ORM**

Controllers are thin HTTP handlers. All business logic lives in services. Controllers handle:
- Rate limiting checks
- Payload parsing (via Pydantic schemas)
- Calling service methods
- Formatting responses

**Sync + Async Methods**

Every service and manager method has both sync and async variants. Async variants are prefixed with `a` (e.g., `register_user` / `aregister_user`). Async methods use Django 5.2's async ORM (`aget`, `afirst`, `asave`, `aexists`) and `sync_to_async` wrappers for cache operations.

**Whitelisted Field Updates**

The `update_profile()` service only updates fields in an explicit `allowed_fields` list. This prevents mass-assignment vulnerabilities. To add a new updatable field, add it to the whitelist in both `update_profile()` and `aupdate_profile()`.

**Email Normalization**

All email fields are normalized to lowercase and stripped of whitespace via Pydantic `@field_validator` and Django's `normalize_email()`.

**Error Handling in Controllers**

Controllers catch `ValueError` from services and return appropriate HTTP status codes:
- 200: Success
- 400: Validation/business logic error
- 401: Authentication failure
- 403: Forbidden
- 404: Not found
- 409: Conflict (duplicate)
- 429: Rate limit exceeded

### Frontend Patterns

**Vue 3 Composition API**

All Vue components use `<script setup lang="ts">` with Composition API (`ref`, `reactive`, `onMounted`).

**Astro Islands Architecture**

Static parts (layout, navigation) are Astro components (`.astro`). Interactive parts (forms, profile editing) are Vue components (`.vue`) loaded as client-side islands via `client:load` or `client:idle`.

**Centralized API Calls**

All API communication goes through `src/lib/api.ts`. Vue components never use raw `fetch()` — they import functions from `src/lib/auth.ts` which internally use `apiClient`.

**Error Display**

API errors are displayed via:
1. Field-level errors below individual inputs
2. Form-level error banners above forms
3. Toast notifications for action feedback (`showToast()`)
4. The `getErrorMessage()` utility extracts human-readable messages from error objects

**Backend-Served Choices (Single Source of Truth)**

Timezone, currency, and language options are defined exclusively in the Django model enums (`users/models.py`) and exposed to the frontend via `GET /auth/choices`. The frontend calls `fetchChoices()` from `auth.ts` — results are cached in-memory for the page lifetime. Both `RegisterForm.vue` and `ProfileCard.vue` consume these choices. This eliminates option duplication between frontend and backend and guarantees they are always in sync.

**Django TextChoices Serialization**

Django's `models.TextChoices` stores labels as lazy translation proxies (`gettext_lazy`). When returning choices in API responses consumed by Pydantic schemas, labels must be explicitly cast with `str()` to resolve the proxy into a plain string. Without this, Pydantic validation rejects the lazy proxy as non-string input.

```python
# Correct: str(l) resolves the lazy proxy
{"value": v, "label": str(l)} for v, l in TimezoneChoices.choices

# Incorrect: l is a lazy.__proxy__, Pydantic rejects it
{"value": v, "label": l} for v, l in TimezoneChoices.choices
```

**Tailwind CSS v4**

Styling uses Tailwind CSS v4 with CSS custom properties for theming (`--color-foreground`, `--color-muted`, etc.). Brand colors use `brand-*` prefix. Utility classes include `btn-primary`, `btn-secondary`, `btn-ghost`, `input-field`, `label-text`, `card`.
