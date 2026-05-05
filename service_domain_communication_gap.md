# Service Domain Communication Gap Analysis

> SDK (TypeScript) vs Backend (Django Ninja) — security & feature alignment audit
>
> Generated: 2026-05-05 | Branch: development

---

## 1. Overview

The `@sattabase/sdk` (TypeScript) is designed to be consumed by **sister domains** — external applications that authenticate users against Sattabase and receive domain-specific access maps. The SDK sends every request with two identifying headers:

```
X-API-Key: sb_live_...
X-Service-Domain: finance.sattabase.tld
```

This document identifies every gap between what the SDK sends/expects and what the backend actually validates/processes.

---

## 2. Gap Summary

| # | Gap | Severity | SDK expects | Backend does | Fix |
|---|-----|----------|-------------|-------------|-----|
| G1 | No `ServiceCredential` model | **CRITICAL** | API key validated against stored credential | Header ignored entirely | New model + middleware |
| G2 | No API key validation middleware | **CRITICAL** | 403 for invalid/missing API key | Request passes through | New middleware |
| G3 | No `POST /admin/api-keys` endpoint | **HIGH** | Admin creates credentials via API | No creation endpoint exists | New admin controller endpoint |
| G4 | No API key creation in Django admin | **HIGH** | Read-only admin view for auditing | No admin model at all | New admin + migration |
| G5 | No API key revocation/rotation | **MEDIUM** | Revoked keys return 403 | N/A — no keys to revoke | Part of G1 model |
| G6 | SDK sends `X-API-Key` on all endpoints | **MEDIUM** | Backend should validate on protected endpoints | Only `X-Service-Domain` is read on `GET /billing/auth/me` | Middleware (G2) |
| G7 | No CORS origin validation via API key | **LOW** | API key ties domain to a registered service | CORS is separate from API key | Future enhancement |
| G8 | SDK config requires `apiKey` prefix `sb_live_` | **LOW** | Backend should reject keys not matching format | N/A — no validation | Part of G2 |
| G9 | No `ServiceCredential` migration | **HIGH** | DB table must exist | No migration file | New migration |
| G10 | SDK `AuthenticationError` maps to API key failure | **LOW** | SDK throws `AuthenticationError` on 401/403 for bad key | Backend never returns 403 for bad key | Part of G2 |

---

## 3. Detailed Gap Analysis

### G1: No `ServiceCredential` Model

**What the SDK expects:**
The SDK README (line 54) specifies the API key format: `sb_live_{token_urlsafe(32)}`. The SDK `config.ts` validates at construction that the key starts with `sb_live_`. This implies a secure credential model on the backend that:
- Stores API keys (hashed, never plaintext after creation)
- Associates each key with a `ServiceDomain`
- Allows activation/deactivation without deletion
- Tracks creation and last-used timestamps

**What the backend has:**
Only `ServiceDomain` model exists (in `billing/models.py`, line 55-110). It stores domain name, product FK, is_primary, is_active. There is **no credential/key storage**.

**Impact:**
- Anyone who knows a valid `X-Service-Domain` value can impersonate that service
- No audit trail of which service domains have active credentials
- No way to rotate or revoke individual keys
- The `ServiceDomain.is_active` flag is the only "gate" — but it controls the domain, not the credential

**Proposed model:**

```
ServiceCredential
├── id              BigAutoField (PK)
├── service_domain  FK → billing.ServiceDomain (CASCADE)
├── key_prefix      CharField(12)       — "sb_live_abcd..." (first 12 chars, for identification)
├── key_hash        CharField(128)      — SHA-256 of the full raw key
├── name            CharField(100)      — human-readable label, e.g. "Finance App Production"
├── is_active       BooleanField        — default True; soft disable without deletion
├── last_used_at    DateTimeField       — updated on each validated request
├── created_by      FK → User (SET_NULL)— admin who created this credential
├── created_at      DateTimeField (auto_now_add)
├── updated_at      DateTimeField (auto_now)
│
├── Meta
│   ├── db_table = "billing_service_credential"
│   └── unique_together = [("service_domain", "key_hash")]
│
├── Methods
│   ├── verify_raw_key(raw_key) → bool    — class method, constant-time compare
│   └── generate_key() → (raw_key, prefix) — class method, creates sb_live_ + urlsafe(32)
```

**Key format:** `sb_live_` + `secrets.token_urlsafe(32)` = `sb_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ012345`
- Total length: 8 (prefix) + 43 (urlsafe base64 of 32 bytes) = **51 characters**
- `key_prefix` stores first 12 chars: `sb_live_aBcD` — for admin identification
- `key_hash` stores `SHA-256(raw_key)` — for lookup, never reversed

---

### G2: No API Key Validation Middleware

**What the SDK does:**
Every SDK request includes `X-API-Key` and `X-Service-Domain` headers (client.ts line 92-96):
```typescript
const headers: Record<string, string> = {
  "Content-Type": "application/json",
  "X-API-Key": this.config.apiKey,
  "X-Service-Domain": this.config.serviceDomain,
};
```

**What the backend does:**
Only `GET /billing/auth/me` reads `X-Service-Domain` (controllers.py line 321):
```python
domain = request.headers.get("X-Service-Domain", "").strip()
```

The `X-API-Key` header is **never read** anywhere in the codebase.

**Proposed implementation:**

Create a Django middleware that runs on every API request containing `X-API-Key`:

```python
class ServiceCredentialMiddleware:
    """Validate X-API-Key header against stored ServiceCredential.

    Only activates when X-API-Key is present (opt-in per request).
    Endpoints that require service authentication will check
    request.service_credential.

    Flow:
    1. Read X-API-Key from request headers
    2. Read X-Service-Domain from request headers
    3. If both present:
       a. Look up ServiceDomain by X-Service-Domain value
       b. Look up active ServiceCredential for that domain by key_hash
       c. If valid: attach to request.service_credential
       d. If invalid: return 403 Forbidden
    4. If X-API-Key present but X-Service-Domain missing: return 400
    5. If neither present: pass through (regular user auth)
    """

    async def __call__(self, request, get_response):
        api_key = request.headers.get("X-API-Key", "").strip()

        if not api_key:
            # No service credential — regular user auth path
            return await get_response(request)

        if not api_key.startswith("sb_live_"):
            return JsonResponse(
                {"detail": "Invalid API key format.", "code": "invalid_api_key"},
                status=403,
            )

        service_domain = request.headers.get("X-Service-Domain", "").strip()
        if not service_domain:
            return JsonResponse(
                {"detail": "X-Service-Domain header required with X-API-Key.",
                 "code": "missing_service_domain"},
                status=400,
            )

        # Look up domain → credential → validate key hash
        # Use constant-time comparison to prevent timing attacks
        try:
            domain = await ServiceDomain.objects.filter(
                domain=service_domain, is_active=True
            ).select_related("product").afirst()
            if not domain:
                raise PermissionDenied("Unknown service domain.")

            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            credential = await ServiceCredential.objects.filter(
                service_domain=domain,
                key_hash=key_hash,
                is_active=True,
            ).afirst()
            if not credential:
                raise PermissionDenied("Invalid API key.")

            # Attach to request for downstream use
            request.service_credential = credential
            request.service_domain = domain

            # Update last_used_at (fire-and-forget)
            await ServiceCredential.objects.filter(pk=credential.pk).aupdate(
                last_used_at=timezone.now()
            )

        except PermissionDenied as e:
            return JsonResponse(
                {"detail": str(e), "code": "api_key_forbidden"},
                status=403,
            )

        return await get_response(request)
```

**Middleware ordering in settings.py:**
```python
MIDDLEWARE = [
    # ... existing middleware ...
    "corsheaders.middleware.CorsMiddleware",
    # NEW: Service credential validation (before JWT auth)
    "billing.middleware.ServiceCredentialMiddleware",
    # ... rest of middleware ...
]
```

**Security considerations:**
- Constant-time comparison (`hmac.compare_digest`) to prevent timing attacks
- `last_used_at` updated asynchronously — no blocking DB write on every request
- Middleware is opt-in: only activates when `X-API-Key` is present
- Regular user JWT auth (Bearer token) still works independently
- Both auth methods can coexist on the same request (service key + user JWT)

---

### G3: No `POST /admin/api-keys` Endpoint

**What the SDK README implies:**
The admin creates credentials via an API endpoint (not Django admin). The raw key is returned **only once** at creation time. The docstring in the user's Django admin comment confirms: *"Credentials are created via the API endpoint (POST /admin/api-keys)"*

**What the backend has:**
No such endpoint exists. There's no admin controller for API key management at all.

**Proposed endpoint:**

```
POST /api/v1/billing/admin/api-keys
Authorization: Bearer <staff_jwt>
Content-Type: application/json

Request:
{
  "service_domain": "docs.sattaspace.com",
  "name": "SattaDocs Production"
}

Response (201):
{
  "id": 1,
  "service_domain": "docs.sattaspace.com",
  "name": "SattaDocs Production",
  "key_prefix": "sb_live_aBcD",
  "raw_key": "sb_live_aBcDeFgHiJkLmNoPqRsTuVwXyZ012345",  // ONLY TIME SHOWN
  "is_active": true,
  "created_at": "2026-05-05T10:00:00Z"
}
```

**Important:** The `raw_key` is returned in the creation response **only**. After that, it's impossible to retrieve. If lost, the key must be revoked and a new one created.

---

### G4: No API Key Management in Django Admin

**What the user's admin docstring describes:**
```python
@admin.register(ServiceCredential)
class ServiceCredentialAdmin(admin.ModelAdmin):
    """Admin configuration for service credentials.

    Credentials are created via the API endpoint (POST /admin/api-keys),
    not through the Django admin. The admin provides a read-only list view
    for auditing and a revoke action. The raw API key is never shown here
    since it is only returned at creation time.
    """
```

**What the backend has:**
No `ServiceCredentialAdmin` class. No admin interface for viewing or revoking credentials.

**Proposed admin features:**
- **List view:** service domain, key prefix (first 12 chars), name, is_active, last_used_at, created_by, created_at
- **No add form:** creation is API-only (prevents accidental admin creation without secure storage)
- **Actions:** "Revoke selected" (sets is_active=False), "Reactivate selected"
- **Read-only fields:** key_hash (never shown), service_domain (FK display)
- **Filters:** is_active, service_domain, created_by

---

### G5: No API Key Revocation/Rotation

**What production needs:**
- Immediate revocation when a key is compromised
- Graceful rotation: create new key → deploy to service → revoke old key
- Audit trail of revocations

**Proposed model additions:**
- `revoked_at` DateTimeField — when the key was deactivated
- `revoked_by` FK → User — who revoked it
- `revocation_reason` CharField — "compromised", "rotated", "unused"

Or use the simpler `is_active` flag with a signal-based audit log.

---

### G6: SDK Sends `X-API-Key` on All Endpoints

**SDK behavior (client.ts line 92-96):**
The SDK attaches `X-API-Key` and `X-Service-Domain` to **every** request — auth endpoints included (`/auth/login`, `/auth/register`, `/auth/token/refresh`, etc.).

**Backend behavior:**
These headers are completely ignored. The auth endpoints (`/auth/login`, `/auth/register`) have no concept of service identity. This means:
- A sister domain's login request is indistinguishable from a direct Sattabase login
- The backend cannot audit which service domain initiated a registration or login
- There's no way to limit registrations to specific service domains

**This is actually by design** for the current architecture:
- The SDK represents a service domain calling Sattabase on behalf of its users
- The user's JWT token is the same regardless of which service domain initiated the login
- The `X-Service-Domain` header only matters for `auth/me` (to determine which product's access map to return)

**But the `X-API-Key` should still be validated** to prevent:
- Unauthorized services from calling Sattabase APIs
- Domain spoofing (sending fake `X-Service-Domain` values)

**Resolution:** The middleware (G2) should validate `X-API-Key` on all endpoints where it's present. If the key is invalid, return 403 — regardless of whether the endpoint uses service identity or not.

---

### G7: No CORS Origin Validation via API Key

**Current state:**
CORS is configured via `CORS_ALLOWED_ORIGINS` in settings.py (line 55-63):
```python
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:4321",
    "http://localhost:8086",
])
```

This is a static list. Adding a new service domain requires restarting the server.

**Future enhancement (not blocking):**
When a `ServiceCredential` is created or activated, automatically add the associated `ServiceDomain.domain` to the CORS allowed origins. When deactivated, remove it. This would be implemented via:
- A Django signal on `ServiceCredential` save/delete
- Updating a cached CORS whitelist (Redis)
- A custom CORS middleware that checks the whitelist

**Not needed for initial implementation** — static CORS config is fine for early adopters.

---

### G8: SDK Requires `sb_live_` Prefix

**SDK validation (config.ts):**
```typescript
if (!this.apiKey.startsWith("sb_live_")) {
  throw new Error("API key must start with 'sb_live_'");
}
```

**Backend validation:**
None. The backend never checks the format.

**Resolution:** The middleware (G2) should validate the prefix format as a first-pass rejection before doing the expensive DB lookup:
```python
if not api_key.startswith("sb_live_"):
    return 403  # Fast reject without DB query
```

---

### G9: No `ServiceCredential` Migration

**What needs to happen:**
After creating the `ServiceCredential` model in `billing/models.py`, a migration must be generated:
```bash
python manage.py makemigrations billing
python manage.py migrate
```

The migration should create the `billing_service_credential` table with:
- `service_domain` FK to `billing_service_domain`
- Unique constraint on `(service_domain, key_hash)`
- Index on `key_hash` (used for lookups on every validated request)
- Index on `is_active` (used for filtering)

---

### G10: SDK Exception Mapping for API Key Errors

**SDK exception hierarchy (exceptions.ts):**
```
SattabaseError
├── AuthenticationError (401)  ← "Invalid/expired token or API key"
├── ForbiddenError (403)        ← "Insufficient permissions"
```

**Current backend behavior:**
The middleware (G2) should return:
- `403` with `{"detail": "Invalid API key.", "code": "api_key_forbidden"}` for bad keys
- `400` with `{"detail": "Missing X-Service-Domain header.", "code": "missing_service_domain"}` for missing domain
- `403` with `{"detail": "Unknown service domain.", "code": "unknown_service_domain"}` for unregistered domains

**SDK mapping:**
The SDK's `buildError()` function (exceptions.ts) maps HTTP status codes to typed exceptions:
- `403` → `ForbiddenError` — SDK consumer catches this and knows the API key is invalid
- `401` → `AuthenticationError` — used for expired/invalid JWT tokens

This mapping is **already correct** in the SDK. The backend just needs to return the right status codes.

---

## 4. Existing Security Features (No Gaps)

These features are already properly implemented and have no gaps:

### 4.1 X-Service-Domain on `auth/me`

**Backend** (controllers.py line 321):
```python
domain = request.headers.get("X-Service-Domain", "").strip()
return await BillingService.aget_auth_me_data(request.user, domain or None)
```

**Service** (services.py): Looks up `ServiceDomain` by domain value → gets product → gets/creates free subscription → builds access map.

**SDK** (auth.ts): `me()` method includes `X-Service-Domain` on every request.

**Gap:** None. This works correctly. The `X-Service-Domain` header is properly consumed.

### 4.2 JWT Authentication

**Backend** (controllers.py line 93-117): `JWTAuth` class validates Bearer tokens, decodes user_id, looks up active user.

**SDK** (client.ts line 98-99): Automatically includes `Authorization: Bearer {token}` when token is provided.

**Gap:** None. JWT auth works correctly.

### 4.3 Auto-Refresh on 401

**SDK** (client.ts line 160-200): On 401 response, attempts token refresh via `POST /auth/token/refresh`, retries the original request.

**Backend** (controllers.py line 254-276): Token refresh endpoint validates refresh token and issues new token pair.

**Gap:** None. Auto-refresh works correctly.

### 4.4 Rate Limiting

**Backend** (rate_limit.py): Redis-based rate limiting on login, register, password reset, email verify, sensitive actions.

**Gap:** None. Rate limiting works correctly. Service domain requests are rate-limited per IP (same as regular requests).

### 4.5 Domain Validation on `auth/me`

**Backend** (services.py): When `X-Service-Domain` is provided:
1. Looks up `ServiceDomain` by domain value
2. Checks `is_active=True` on the domain
3. Checks `is_active=True` on the associated product
4. If domain is unknown or inactive → returns plain user profile (no subscription, no access)

**Security implication:** An attacker can send `X-Service-Domain: nonexistent.domain` and get the plain user profile. This is **by design** — the `auth/me` endpoint degrades gracefully for unknown domains. The API key validation (G2) will prevent unknown domains from making requests at all.

---

## 5. Implementation Checklist

### Phase A: Backend (must complete before SDK testing)

| # | Task | Files | Effort |
|---|------|-------|--------|
| A1 | Create `ServiceCredential` model | `billing/models.py` | 30 min |
| A2 | Generate migration | `billing/migrations/0014_*.py` | 5 min |
| A3 | Create `ServiceCredentialAdmin` (read-only) | `billing/admin.py` | 20 min |
| A4 | Create `ServiceCredentialMiddleware` | `billing/middleware.py` | 45 min |
| A5 | Register middleware in `settings.py` | `sattaledger/settings.py` | 5 min |
| A6 | Create `POST /billing/admin/api-keys` endpoint | `billing/controllers.py` | 30 min |
| A7 | Create `PATCH /billing/admin/api-keys/{id}` (revoke/activate) | `billing/controllers.py` | 15 min |
| A8 | Create `GET /billing/admin/api-keys` (list) | `billing/controllers.py` | 15 min |
| A9 | Create `ServiceCredential` schemas | `billing/schemas.py` | 15 min |
| A10 | Add `key_hash` index to migration | `billing/migrations/0014_*.py` | 5 min |
| A11 | Update `dev_docs.md` with new endpoints | `dev_docs.md` | 20 min |

**Total Phase A: ~3.5 hours**

### Phase B: Testing (after Phase A)

| # | Task | Effort |
|---|------|--------|
| B1 | Create a ServiceCredential for `docs.sattaspace.com` via admin API | 5 min |
| B2 | Use the raw key in SattaDocs `.env` | 2 min |
| B3 | Test SDK login → verify API key is validated | 10 min |
| B4 | Test SDK `me()` → verify domain-scoped access map | 10 min |
| B5 | Test with invalid API key → verify 403 | 5 min |
| B6 | Test with missing API key → verify request passes through (regular auth) | 5 min |
| B7 | Test API key revocation → verify 403 after revoke | 5 min |
| B8 | Test all remaining SDK methods (register, refresh, verify, password reset, etc.) | 20 min |

**Total Phase B: ~1 hour**

### Phase C: Future Enhancements (not blocking)

| # | Enhancement | Priority |
|---|------------|----------|
| C1 | CORS origin auto-management via ServiceCredential signals | Low |
| C2 | API key rotation endpoint (create new + auto-revoke old) | Medium |
| C3 | Per-service-domain rate limits (separate from per-IP) | Medium |
| C4 | Audit log for API key creation/revocation/login events | Medium |
| C5 | ServiceCredential Webhook for real-time key status propagation | Low |
| C6 | API key usage analytics (requests per key per day) | Low |

---

## 6. Request Flow (After Gap Fix)

### Current Flow (broken — no API key validation)

```
Sister Domain (SDK)
    │
    │  POST /api/v1/auth/login
    │  X-API-Key: sb_live_...     ← IGNORED by backend
    │  X-Service-Domain: finance   ← IGNORED on auth endpoints
    │  Authorization: (none)
    │
    ▼
Backend (Django)
    │  JWTAuth: not needed (public endpoint)
    │  Validates email/password → returns JWT tokens
    │
    ▼
Sister Domain (SDK)
    │
    │  GET /api/v1/billing/auth/me
    │  X-API-Key: sb_live_...     ← IGNORED by backend
    │  X-Service-Domain: finance   ← READ → looks up ServiceDomain
    │  Authorization: Bearer <jwt>
    │
    ▼
Backend (Django)
    │  JWTAuth: validates token → sets request.user
    │  Reads X-Service-Domain → looks up product → returns access map
    │  ⚠️ ANYONE can spoof X-Service-Domain header
```

### Fixed Flow (with ServiceCredential middleware)

```
Sister Domain (SDK)
    │
    │  POST /api/v1/auth/login
    │  X-API-Key: sb_live_...        ← VALIDATED by middleware
    │  X-Service-Domain: docs.sattaspace.com  ← VALIDATED by middleware
    │  Authorization: (none)
    │
    ▼
Backend (Django)
    │  ServiceCredentialMiddleware:
    │    1. Reads X-API-Key → validates sb_live_ prefix
    │    2. Looks up ServiceDomain by X-Service-Domain
    │    3. Looks up ServiceCredential by key_hash
    │    4. Sets request.service_credential ✓
    │    5. Updates last_used_at
    │  JWTAuth: not needed (public endpoint)
    │  Validates email/password → returns JWT tokens
    │
    ▼
Sister Domain (SDK)
    │
    │  GET /api/v1/billing/auth/me
    │  X-API-Key: sb_live_...        ← VALIDATED by middleware
    │  X-Service-Domain: docs.sattaspace.com  ← VALIDATED by middleware
    │  Authorization: Bearer <jwt>
    │
    ▼
Backend (Django)
    │  ServiceCredentialMiddleware: validates key ✓
    │  JWTAuth: validates token → sets request.user ✓
    │  Reads X-Service-Domain → looks up product → returns access map
    │  ✓ Domain cannot be spoofed — API key is tied to domain
```

### Invalid Key Flow

```
Attacker
    │
    │  GET /api/v1/billing/auth/me
    │  X-API-Key: sb_live_fakedata...    ← INVALID KEY
    │  X-Service-Domain: finance          ← SPOOFED DOMAIN
    │  Authorization: Bearer <stolen_jwt>
    │
    ▼
Backend (Django)
    │  ServiceCredentialMiddleware:
    │    1. Reads X-API-Key → validates sb_live_ prefix ✓
    │    2. Looks up ServiceDomain by "finance" ✓ (exists)
    │    3. Looks up ServiceCredential by key_hash → NOT FOUND ✗
    │    4. Returns 403 {"detail": "Invalid API key.", "code": "api_key_forbidden"}
    │
    ▼
Attacker blocked — cannot access any API endpoint
```

---

## 7. Files Changed Summary

| File | Action | Description |
|------|--------|-------------|
| `billing/models.py` | **MODIFY** | Add `ServiceCredential` model |
| `billing/admin.py` | **MODIFY** | Add `ServiceCredentialAdmin` |
| `billing/middleware.py` | **CREATE** | API key validation middleware |
| `billing/schemas.py` | **MODIFY** | Add `ServiceCredential` schemas |
| `billing/controllers.py` | **MODIFY** | Add admin API key endpoints |
| `sattaledger/settings.py` | **MODIFY** | Register middleware in MIDDLEWARE list |
| `billing/migrations/0014_servicecredential.py` | **CREATE** | Migration for new model |
| `dev_docs.md` | **MODIFY** | Document new endpoints |

---

## 8. SDK Testing Readiness

After all Phase A gaps are fixed, the SDK can be tested against the live backend:

| SDK Method | Requires API Key | Requires JWT | Expected Result |
|-----------|-----------------|-------------|-----------------|
| `client.auth.login()` | Yes (validated) | No | `TokenPair` |
| `client.auth.register()` | Yes (validated) | No | `MessageResponse` |
| `client.auth.me()` | Yes (validated) | Yes | `AuthMeResponse` with access map |
| `client.auth.refresh()` | No (SDK doesn't send key on refresh) | No | `TokenPair` |
| `client.auth.verify()` | Yes (validated) | No | `MessageResponse` |
| `client.auth.blacklist()` | Yes (validated) | No | `MessageResponse` |
| `client.auth.logout()` | Yes (validated) | Yes | void (clears store) |
| `client.auth.requestPasswordReset()` | Yes (validated) | No | `MessageResponse` |
| `client.auth.confirmPasswordReset()` | Yes (validated) | No | `MessageResponse` |
| `client.auth.requestEmailVerification()` | Yes (validated) | No | `MessageResponse` |
| `client.auth.confirmEmailVerification()` | Yes (validated) | No | `MessageResponse` |
| `client.access.hasAccess()` | Yes (validated) | Yes | boolean |
| `client.billing.manageSubscription()` | No (URL constructor only) | No | URL string |

**Note:** The SDK sends `X-API-Key` on all methods including `refresh()` (which doesn't include the key — see client.ts line 190-194, the refresh call uses plain `fetch` without the SDK's `request()` method). This is correct behavior — the refresh endpoint is a standalone JWT endpoint.

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| No API key validation before production | **High** (current state) | **Critical** — any domain can impersonate any service | Implement G1 + G2 before SDK testing |
| API key leaked in logs/error messages | Medium | High — credential exposure | Middleware should strip key from error responses |
| Brute-force API key guessing | Low | Medium — 43-char urlsafe key is 256-bit entropy | Rate limit on 403 responses per IP |
| ServiceCredential table becomes bottleneck | Low | Low — single row lookup by indexed hash | Index on `key_hash`, consider Redis cache |
| Middleware breaks existing user auth | Low | High — all endpoints fail | Only activates when `X-API-Key` header present |
| Migration breaks existing data | Very Low | High | Additive migration only — no field changes to existing models |
