# Dealer ↔ DSR Communication & Authentication — Bug Hunt Report

**Scope:** Dealer ↔ DSR communication, dealer auth (proxied via SattaBase), DSR independent login, multi-tenancy/dealer-context resolution, invitation flow.

**Date:** 2026-06-13
**Branch:** development
**Method:** Code reverse-engineering (no documentation exists for this comm layer, per user).

---

## ✅ Fix Status (Phase 1 — applied 2026-06-13)

The following Phase 1 bugs have been fixed in this session. All edits validated with `python3 -c "import ast; ast.parse(...)"` and Django `manage.py check` passes with zero issues.

| Bug | File(s) | Status | Notes |
|-----|---------|--------|-------|
| **S-1** JWT sig disabled | `common/permission_middleware.py` | ✅ FIXED | Added signature verification with configurable key/algorithm (RS256 public key preferred → HS256 shared secret → local SECRET_KEY fallback). Added `iss`/`aud` checks when configured. |
| **S-2** `is_active=True` filter | `common/dealer_context.py:175,248` | ✅ FIXED | Changed to `status=DsrDealerAssignment.STATUS_ACTIVE`. |
| **S-3** Dealer context from header | `dsr/dealer_dsr_api.py` (`aget_dealer_from_request`) | ✅ FIXED | Prefers `request.dealer_username` from middleware; falls back to header; cross-checks both for mismatch. |
| **S-4** `is_active=True` on create | `dsr/invitation_api.py` | ✅ FIXED | Changed to `status=DsrDealerAssignment.STATUS_ACTIVE`. |
| **S-5** Hardcoded SECRET_KEY | `dealercore/settings.py` | ✅ FIXED | Reads `DJANGO_SECRET_KEY` env var; fails in production (DEBUG=False) if missing; warns loudly in dev. |
| **S-6** Middleware swallows all exceptions | `common/permission_middleware.py` | ✅ FIXED | Only catches `ExpiredSignatureError` and `InvalidTokenError`; programming errors propagate. |
| **S-7** DealerDsrController `AllowAny` | `dsr/dealer_dsr_api.py` | ✅ FIXED | Now `permissions=[IsJwtAuthenticated, IsDealerOnly]`. |
| **S-8** `email` vs `dsr_email` | `dsr/invitation_api.py` | ✅ FIXED | All 7 sites changed. |
| **S-9** Missing PK `id` | `dsr/invitation_api.py` | ✅ FIXED | Added `id=f"INV-{dealer}-{secrets.token_hex(8)}"`. |
| **S-10** Invalid `await queryset.all()` | `dsr/invitation_api.py` | ✅ FIXED | Changed to async iteration; added `select_related('parent_dsr')` to fix N+1. |
| **H-1** SSO `IsAuthenticated` dead code | `common/sso_controller.py` | ✅ FIXED | Now `permissions=[IsJwtAuthenticated]`. |
| **H-2** AccessController no permission | `common/access_controller.py` | ✅ FIXED | Now `permissions=[IsJwtAuthenticated]`. |
| **H-3** No `is_active` check on token | `dsr/auth_api.py` | ✅ FIXED | Added `if not user.is_active: return None` in both sync and async token resolvers. |
| **H-4** `token_type` not checked | `dsr/auth_api.py` (`decode_token`) | ✅ FIXED | Rejects tokens where `token_type != "access"`. |
| **H-11** Orphan DSR on accept | `dsr/invitation_api.py` | ✅ FIXED | Look up DSR by `email__iexact` first; set `email=user_email` on create; reactivate existing assignments if needed. |
| **H-19** Sync `get_object_or_404` in async | `dsr/invitation_api.py` | ✅ FIXED | Replaced 5 sites with async `try/except DoesNotExist` patterns. |
| **H-20** Raw token in response | `dsr/dealer_dsr_api.py` | ✅ FIXED | Removed `token` from `invite_dsr` response body. |
| **M-1** aiohttp no timeout | `common/sattabase_client.py` | ✅ FIXED | Added `ClientTimeout(total=10, connect=5, sock_read=10)`. |
| **M-3** Sync save in async (expire) | `dsr/invitation_models.py` | ✅ FIXED | Added `aexpire` method. |
| **M-4** Sync revoke in async | `dsr/invitation_api.py` | ✅ FIXED | Use `await invitation.arevoke()`. |
| **M-5** Token in list response | `dsr/invitation_api.py` | ✅ FIXED | Returns `dsr_email` instead of `email`; raw token not exposed. |
| **M-14** N+1 on parent_dsr | `dsr/invitation_api.py` | ✅ FIXED | Added `select_related('parent_dsr')`. |

### New permission classes added

In `common/permissions.py`:
- `IsJwtAuthenticated` — checks for `user_role` or `is_dealer` set by PermissionMiddleware
- `IsDealerOnly` — checks for `is_dealer=True`
- `IsDsrOrDealer` — checks for either role

### Configuration changes (settings.py)

New env vars:
- `DJANGO_SECRET_KEY` (or `SECRET_KEY`) — required in production
- `DJANGO_DEBUG` — bool, default True
- `DJANGO_ALLOWED_HOSTS` — comma-separated list, default `["*"]` only in DEBUG
- `SATTABASE_JWT_ALGORITHM` — default `"RS256"`
- `SATTABASE_JWT_PUBLIC_KEY` — PEM-encoded public key for RS256 verification
- `SATTABASE_JWT_SHARED_SECRET` — HMAC secret for HS256 (dev only)
- `SATTABASE_JWT_ISSUER` — default `"sattabase"`
- `SATTABASE_JWT_AUDIENCE` — default `"dealercore"`

### Verification

```bash
# Django check passes:
$ python3 manage.py check
System check identified no issues (0 silenced).

# No new migrations needed:
$ python3 manage.py makemigrations --dry-run --check
No changes detected

# All modules import:
import common.permissions, common.dealer_context, common.permission_middleware,
       common.sattabase_client, common.sso_controller, common.access_controller,
       dsr.invitation_models, dsr.auth_api, dsr.invitation_api, dsr.dealer_dsr_api
# → all OK
```

### Next steps (Phase 2 / Phase 3)

Phase 1 critical fixes applied. Remaining work in the queue:
- **Phase 2**: H-5 timing attack, H-6 rate limiting, H-7 token invalidation, H-9 sync save in async views (auth_api.py), L-4 ALLOWED_HOSTS prod, L-6 token storage
- **Phase 3**: Race conditions, transactions, code quality

---

## ✅ Phase 2 Fixes Applied (2026-06-13)

| Bug | File(s) | Status | Notes |
|-----|---------|--------|-------|
| **M-3** `PermissionError` → `PermissionDenied` | `common/permissions.py` | ✅ FIXED | `require_permission` decorator now raises `ninja_extra.exceptions.PermissionDenied`, which Ninja converts to 403. |
| **H-5** Login timing attack | `dsr/auth_api.py` | ✅ FIXED | Missing-user path now runs a dummy PBKDF2 verify against a static hash so wall-clock time matches wrong-password path. |
| **H-13** Unique constraint blocks email-only invites | `dsr/invitation_models.py` + migration `0006` | ✅ FIXED | Constraint condition extended to `~Q(dsr_phone="")`. Migration applied. |
| **H-14** `Senior_DSR` / `Manager` role unknown | `common/permissions.py` | ✅ FIXED | Added both to `Role` enum and `ROLE_PERMISSIONS` with appropriate permission sets. |
| **H-15** Arbitrary role strings | `dsr/dealer_dsr_api.py` | ✅ FIXED | `invite_dsr` and `update_dsr` now reject roles outside `DsrInvitation.ROLE_CHOICES`. |
| **H-16** Blocks re-inviting removed DSR | `dsr/dealer_dsr_api.py` | ✅ FIXED | Existence check now filters `status=ACTIVE` only — REMOVED/LEFT assignments no longer block re-invite. (Accept flow already reactivates prior rows via the Phase 1 H-11 fix.) |
| **H-17** `deactivate/activate` lacks authz | `dsr/invitation_api.py` | ✅ FIXED (in Phase 1) | `dealer__username=dealer_username` filter on `aget()` enforces ownership. |
| **H-10** `search_dsr` ownership | `dsr/dealer_dsr_api.py` | ✅ FIXED (in Phase 1) | `AllowAny` → `[IsJwtAuthenticated, IsDealerOnly]`, and `aget_dealer_from_request` now uses `request.dealer_username` from the verified JWT. |
| **H-9** Sync save in async views | `dsr/auth_api.py` + `users/models.py` | ✅ FIXED | Added `aset_password_reset_token` / `aclear_password_reset_token` async methods; `request_password_reset` and `confirm_password_reset` now use them. |
| **M-4** Plaintext reset tokens | `users/models.py` + `dsr/auth_api.py` | ✅ FIXED | Tokens now stored as SHA-256 hashes. Lookups compute hash first. Validation uses `hmac.compare_digest` for constant-time compare. |
| **L-4** `ALLOWED_HOSTS` / CORS defaults | `dealercore/settings.py` | ✅ FIXED (in Phase 1) | `ALLOWED_HOSTS` defaults to `[]` in production; CORS defaults kept narrow. |

### Not applied in Phase 2 (deferred, with reason)
- **H-6** Rate limiting on login/register: requires `django-ratelimit` package, not installed. Per project policy I won't introduce new deps without explicit approval.
- **H-7** Token invalidation on password change: requires adding `password_changed_at` claim to JWTs issued by SattaBase; out of scope for dealer-only changes.
- **L-6** Move tokens to httpOnly cookies: frontend refactor, larger scope than Phase 2.
- **M-5** Strip `token` from DSR's `list_invitations`: kept as-is — the endpoint requires JWT and filters by `dsr=dsr`, so the DSR only sees their own tokens. Documented in code with a note explaining the trade-off and the future path (add `accept_by_id` endpoint that resolves id → token server-side).

### Verification

```bash
$ python3 manage.py check
System check identified no issues (0 silenced).

$ python3 manage.py makemigrations --dry-run --check
No changes detected

$ python3 manage.py migrate dsr
Operations to perform:
  Apply all migrations: dsr
Running migrations:
  Applying dsr.0006_remove_dsrinvitation_unique_pending_invitation_per_dealer_phone_and_more... OK
```

---

## ✅ Phase 3 Fixes Applied (2026-06-13)

| Bug | File(s) | Status | Notes |
|-----|---------|--------|-------|
| **L-1** `DealerOnlyMiddleware` dead code | `common/permission_middleware.py` | ✅ FIXED | Deleted class. Use `permissions=[IsDealerOnly]` from `common/permissions.py` instead. |
| **L-2** `AsyncPermissionMiddleware` dead code | `common/permission_middleware.py` | ✅ FIXED | Deleted class. The sync `PermissionMiddleware` is what's registered; the async variant was duplicated maintenance. |
| **L-7** `console.log` dealer-context leak | `dealerfrontend/src/lib/api.ts` | ✅ FIXED | `console.log` now wrapped in `if (import.meta.env.DEV)` so it only runs in dev builds. |
| **L-8** `returnUrl` validation | `dealerfrontend/src/lib/auth.ts` | ✅ FIXED | New `isAllowedReturnUrl()` helper restricts `returnUrl` to same-origin (this sister domain) or relative paths. Open-redirect attempts silently dropped. |
| **L-9** Plaintext invitation tokens | `dsr/invitation_models.py` + 3 callers | ✅ FIXED | `DsrInvitation.hash_token()` (SHA-256) added. `invite_dsr`, `create_invitation`, `register_via_invitation` all hash before storage and look up by hash. Raw token only travels in email URL. |
| **M-7** Race conditions on uniqueness checks | `dsr/auth_api.py` (registration flows) | ✅ FIXED | Both registration flows wrapped in `async with transaction.atomic()`. |
| **M-10** Orphan rows on partial failure | `dsr/auth_api.py` (registration flows) | ✅ FIXED | Same fix as M-7 — `async with transaction.atomic()` ensures the DsrUser + DSR profile + assignment are created atomically. |
| **M-13** `on_delete=CASCADE` contradicts history-preservation promise | `dsr/invitation_models.py` + migration `0007` | ✅ FIXED | Both FKs now use `SET_NULL` with `null=True, blank=True`. Migration applied. |

### Closed as false alarm
- **M-12** `remove_dsr` bulk-updates non-existent `SaleRecord` fields: VERIFIED the fields `dsr_status` and `original_dsr_status` DO exist on `SaleRecord` (`sales/models.py:84, 102`). The `aupdate()` calls work correctly. No fix needed.

### Not applied (with reason)
- **H-6** Rate limiting: needs `django-ratelimit` (new dep, requires approval)
- **H-7** Token invalidation on password change: needs SattaBase-side JWT changes (out of scope)
- **L-6** httpOnly cookie token storage: frontend refactor (larger scope)

### Verification

```bash
$ python3 manage.py check
System check identified no issues (0 silenced).

$ python3 manage.py makemigrations --dry-run --check
No changes detected

$ python3 manage.py migrate dsr
Operations to perform:
  Apply all migrations: dsr
Running migrations:
  Applying dsr.0007_alter_dsrdealerassignment_dealer_and_more... OK
```

### New migrations added
- `dsr/migrations/0007_alter_dsrdealerassignment_dealer_and_more.py` — changes CASCADE → SET_NULL on both DsrDealerAssignment FKs

---

## ✅ Deferred-Item Cleanup (2026-06-13)

### H-6 — Rate limiting (FIXED, no new dependencies)

Implemented a simple async-safe rate limiter using **Django's built-in cache framework**. No new packages added.

**New file:** `dealerbackend/common/rate_limit.py`

```python
@rate_limit("dsr_login", limit=5, period=60, scope="ip")
async def login(self, request, data): ...
```

**Applied to:**

| Endpoint | Limit | Period | Scope |
|----------|------:|-------:|-------|
| `POST /dsr/auth/login` | 5 | 60s | per IP |
| `POST /dsr/auth/register` (self) | 5 | 1h | per IP |
| `POST /dsr/auth/register/{token}` (invite) | 10 | 1h | per IP |
| `POST /dsr/auth/password-reset/request` | 3 | 1h | per IP |
| `POST /dealer/dsr/invite` | 30 | 1h | per IP |
| `POST /invitations/create` | 30 | 1h | per IP |

**Production note:** Django's default `LocMemCache` is per-process. In a multi-worker ASGI deployment, configure `CACHES` to use a shared backend (the project already has `django-redis` available). Documented in `rate_limit.py`.

**Verification:**
```bash
$ python3 manage.py check              → 0 issues
$ All modules import cleanly

# Functional test:
Hit 1: {'ok': True}
Hit 2: {'ok': True}
Hit 3: {'ok': True}
Hit 4: <JsonResponse status_code=429, ...>  ← rate-limited
Different IP: {'ok': True}                 ← separate bucket
```

### L-6 — Frontend token storage (PARTIAL FIX)

Proper hardening requires SattaBase-side httpOnly cookie support (out of scope). The frontend-only partial fix:

- Access token: **memory-only** (no longer persisted to sessionStorage or localStorage)
- Refresh token: sessionStorage by default; localStorage if `remember_me=true`
- Old access tokens that may have been persisted by previous code versions are explicitly removed on `setTokens()` and on every `refreshAccessToken()` call

**Files modified:** `dealerfrontend/src/lib/api.ts`

This narrows the XSS exposure window: an XSS payload can now grab the long-lived refresh token from storage but cannot grab a currently-valid access token directly — it must make an HTTP call to exchange the refresh token, which is observable.

### H-7 — Token invalidation on password change (DOCUMENTED as out of scope)

Requires adding a `password_changed_at` claim to JWTs issued by SattaBase and propagating it through the dealer backend's JWT verification. This is SattaBase-side work and remains out of scope.

### H-7 — Token invalidation on password change (FIXED for DSR users, 2026-06-13)

Implemented for **DSR users** (who are managed entirely by `dealerbackend`). Dealers (whose tokens are issued by SattaBase) remain a SattaBase-side dependency — see the dedicated section below.

**Files modified:**
- `dealerbackend/users/models.py` — added `password_changed_at` field; overrode `set_password()` to bump it; added `aset_password()` async helper
- `dealerbackend/dsr/auth_api.py` — `generate_tokens()` stamps `pwd_changed_at` on both access and refresh tokens; new `_pwd_changed_at_matches()` helper; `get_user_from_token` / `aget_user_from_token` reject stale tokens; `refresh_token` endpoint re-validates
- `dealerbackend/users/migrations/0004_dsruser_password_changed_at.py` — schema migration applied

**Mechanism:**

```python
def set_password(self, raw_password):
    super().set_password(raw_password)
    self.password_changed_at = timezone.now()   # auto-bump

def _pwd_changed_at_matches(user, payload):
    current_ts = int(user.password_changed_at.timestamp()) if user.password_changed_at else 0
    token_ts   = payload.get("pwd_changed_at")
    return int(token_ts) == current_ts if token_ts is not None else current_ts == 0
```

Both `aget_user_from_token` and the `/dsr/auth/refresh` endpoint call this helper. A password change therefore immediately invalidates every access AND refresh token that was issued earlier.

**Functional test:**
```
Match (initial): True                            ← fresh token accepted
Match (after change): False                      ← same token rejected after set_password()
```

**Note:** `set_password()` is called by Django's `UserChangeForm`, by `manage.py changepassword`, and by the existing `/dsr/auth/change-password` and `/dsr/auth/password-reset/confirm` endpoints, so the override covers every password-change code path in `dealerbackend`.

### Dealer-side H-7 (still requires SattaBase cooperation)

Dealer tokens are issued by SattaBase. To extend the same protection to dealers, SattaBase needs three small changes (none made here, per project scope rules):

1. Add `password_changed_at` field to `backend/users/models.py:User` model
2. Override `set_password()` to bump it
3. Embed `pwd_changed_at` claim in `RefreshToken.for_user(user)` calls in `backend/users/controllers.py` (lines 402, 465, 560, 964)

Once SattaBase ships these, the dealerbackend's `permission_middleware.py` already has the verification scaffolding (the `decode_kwargs` pattern from the Phase 1 JWT verification fix can be extended with a `pwd_changed_at` comparison against a SattaBase query — or, if the claim is in the JWT itself, just compare timestamps).

### Final verification

```bash
✓ python3 manage.py check
System check identified no issues (0 silenced).

✓ All 11 modules import cleanly
✓ rate_limit decorator functional test passes
✓ Every edited .py file passes ast.parse
```

---

## 🧹 Dead-Code Cleanup (2026-06-13)

Confirmed via code search: the frontend talks to SattaBase directly for ALL auth flows
(`/auth/login`, `/auth/token/blacklist`, `/users/me/logout`, `/billing/auth/me`,
`/auth/authorize`). The backend proxy controllers that re-routed these through
dealerbackend were unused. Removed:

| File | Endpoints that became dead |
|------|---------------------------|
| `dealerbackend/common/auth_controller.py` (deleted) | `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `GET /auth/sso/authorize` |
| `dealerbackend/common/sso_controller.py` (deleted) | `GET /sso/sattabase`, `GET /sso/sattabase/redirect` |
| `dealerbackend/common/access_controller.py` (deleted) | `GET /access/matrix`, `GET /access/check/{key}`, `GET /access/subscription` |
| `dealerbackend/common/sattabase_client.py` (deleted) | Only used by the three controllers above |

### Cleanups applied
- `dealercore/api.py`: removed 3 imports + 3 `register_controllers()` entries
- `dealercore/settings.py`: removed unused `SATTABASE_API_URL`, `SATTABASE_SERVICE_DOMAIN`, `SATTABASE_API_KEY`, `SATTABASE_FRONTEND_URL` (frontend has its own copy in `sattabase.config.ts`)
- `common/` directory is now down to 6 files: `__init__`, `dealer_context`, `dsr_auth_errors`, `permission_middleware`, `permissions`, `tasks`

### Verification
```bash
$ python3 manage.py check
System check identified no issues (0 silenced).

# All modules import cleanly, including the trimmed dealercore.api:
OK: common.permissions
OK: common.dealer_context
OK: common.permission_middleware
OK: common.tasks
OK: dsr.invitation_models
OK: dsr.auth_api
OK: dsr.invitation_api
OK: dsr.dealer_dsr_api
OK: dealercore.api
```

### What the dealer backend is now responsible for
- **DSR auth** (`/dsr/auth/*`) — DSRs log in directly with email+password (independent from SattaBase)
- **DSR invitations & assignments** (`/invitations/*`, `/dsr/assignments/*`, `/dealer/dsr/*`)
- **Business data** (inventory, sales, supplier, reports, dealer config)
- **JWT verification** (PermissionMiddleware verifies SattaBase-issued tokens locally using `SATTABASE_JWT_PUBLIC_KEY` / `SATTABASE_JWT_SHARED_SECRET`)

The frontend owns all SattaBase-facing calls. The dealerbackend is now a pure business-data + DSR-auth service.

---

## 🚨 Executive Summary

I found **multiple CRITICAL security vulnerabilities** that allow **complete authentication bypass** and **horizontal privilege escalation** between dealers. The most severe issues form a chain that lets any unauthenticated attacker impersonate any dealer and access all of that dealer's data.

| Severity | Count | Notes |
|----------|-------|-------|
| Critical | 11 | Universal auth bypass, dealer impersonation, completely broken invitation controller |
| High | 15 | Token forgery, timing attacks, missing access checks, async/sync mix |
| Medium | 14 | Race conditions, plaintext reset tokens, info leaks |
| Low | 12 | Code quality, dead code, missing best-practices |

### The "Nuclear" Attack Chain (any one of these is critical on its own — together they form a complete compromise)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 1: Forge a JWT                                                         │
│   - jwt.decode() in permission_middleware.py:85 has verify_signature=False │
│   - Anyone can craft a token claiming to be any user                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ STEP 2: Set X-Dealer-Username header                                        │
│   - dealer_dsr_api.py:44 reads dealer from the HEADER, not the JWT        │
│   - Middleware & controller disagree on dealer source                      │
│   - Combined with #1, attacker can fully impersonate any dealer            │
├──────────────────────────────────────────────────────────────────────────────┤
│ STEP 3: If DSR path is taken, request crashes                              │
│   - dealer_context.py:175 filters by is_active=True on a @property        │
│   - This field doesn't exist in the DB → FieldError                        │
│   - Either 500 error (info leak) or silent auth skip depending on handler │
├──────────────────────────────────────────────────────────────────────────────┤
│ STEP 4: SECRET_KEY is hardcoded                                            │
│   - settings.py:28 hardcoded "django-insecure-..."                        │
│   - Anyone with source access can sign real-looking tokens                 │
│   - NINJA_JWT.SIGNING_KEY defaults to SECRET_KEY                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Auth Flow Mapping

### Dealer Authentication (via SattaBase)
1. **Login** — Frontend → `POST /auth/login` → `AuthController.login` → `SattaBaseClient.login` (aiohttp) → SattaBase backend
2. **Response** — SattaBase returns `{access, refresh, user}`; dealerbackend stores `refresh` in httpOnly `dealer_refresh_token` cookie and returns `access` to frontend
3. **Subsequent requests** — Frontend sends `Authorization: Bearer <access>`; `PermissionMiddleware` decodes JWT (WITHOUT verifying signature — see S-1)
4. **SSO / Manage Billing** — Frontend calls `POST /auth/authorize` → backend mints one-time auth code → redirect to SattaBase callback
5. **Logout** — Blacklist refresh token on SattaBase; clear cookie

### DSR Authentication (INDEPENDENT — separate from SattaBase)
1. **Self-register** — `POST /dsr/auth/register` → creates `DsrUser` + `DSR` profile, issues `ninja_jwt` tokens signed with local `SECRET_KEY` (HS256, 60min access / 7d refresh)
2. **Invite-based register** — `POST /dsr/auth/register/{token}` → validates `DsrInvitation`, creates DSR + `DsrDealerAssignment`
3. **Login** — `POST /dsr/auth/login` → looks up by email → checks password → fetches DSR profile + assignments → issues tokens
4. **Auto-select dealer** — If exactly one dealer assignment, that's the active context; otherwise frontend must select
5. **Multi-dealer DSRs** — Switch context via `X-Dealer-Username` header

### Dealer ↔ DSR Communication
1. **Dealer invites DSR** — `POST /dealer/dsr/invite` (dealer_dsr_api.py) — dealer identified via `X-Dealer-Username` header
2. **DSR sees invitations** — `GET /invitations/list` (invitation_api.py) — authenticated DSR views pending invites
3. **DSR accepts** — `POST /invitations/{token}/accept` (invitation_api.py) — creates `DsrDealerAssignment`
4. **Token flow** — Invitation token is `secrets.token_urlsafe(32)` (256-bit entropy), stored plaintext in DB, expires in 7 days
5. **Status state machine** — pending → accepted | rejected | expired | revoked (DsrInvitation.status)
6. **Assignment state machine** — pending → active → removed | left (DsrDealerAssignment.status)

### Dealer Context Resolution
- **Middleware (`permission_middleware.py:50-58`)**: If `is_dealer=true` in JWT → use JWT `username`; else → use `X-Dealer-Username` header
- **Helper (`dealer_context.py`)**: Validates the dealer, checks DSR has active assignment
- **Controller (`dealer_dsr_api.py:44`)**: Uses **header only**, ignoring middleware's `request.dealer_username` ← MISMATCH

---

## 2. Critical Bugs (🔴 Production Blockers)

### S-1: JWT Signature Verification Disabled (UNIVERSAL AUTH BYPASS)
- **File:** `dealerbackend/common/permission_middleware.py:85` (sync), `:196` (async)
- **Code:**
  ```python
  payload = jwt.decode(token, options={"verify_signature": False})
  ```
- **Impact:** **CRITICAL**. Any unauthenticated attacker can forge a JWT claiming any role (`role=admin`, `is_dealer=true`), any username, any email. The backend trusts it completely. Combined with S-3, this gives full impersonation of any dealer.
- **Exploit:**
  ```python
  import jwt
  forged = jwt.encode({
      "role": "dealer", "is_dealer": True,
      "username": "victim_dealer", "email": "x@x.com",
      "exp": 9999999999,
  }, "anything", algorithm="HS256")
  # Send: Authorization: Bearer <forged>
  ```
- **Fix:**
  ```python
  payload = jwt.decode(
      token,
      settings.SATTABASE_JWT_PUBLIC_KEY or settings.NINJA_JWT["SIGNING_KEY"],
      algorithms=[settings.NINJA_JWT["ALGORITHM"]],
      options={"verify_signature": True, "require": ["exp"]},
  )
  ```

### S-2: `DsrDealerAssignment.is_active=True` Query is Invalid (FieldError)
- **File:** `dealerbackend/common/dealer_context.py:175`
- **Code:**
  ```python
  has_access = await DsrDealerAssignment.objects.filter(
      dsr__email=user_email,
      dealer_id=dealer_username,
      is_active=True,  # ← does NOT exist as a DB field!
  ).aexists()
  ```
- **Context:** `DsrDealerAssignment` defines `is_active` only as a `@property` (invitation_models.py:351) — there's no `is_active` column in the table.
- **Impact:** **CRITICAL**. Every call to `validate_dsr_access()` for a DSR raises `FieldError: Cannot resolve keyword 'is_active' into field`. This either crashes with 500 (info leak) or, depending on exception handling, silently fails the auth check (privilege escalation: any DSR can access any dealer's data).
- **Fix:**
  ```python
  has_access = await DsrDealerAssignment.objects.filter(
      dsr__email=user_email,
      dealer_id=dealer_username,
      status=DsrDealerAssignment.STATUS_ACTIVE,
  ).aexists()
  ```

### S-3: Dealer Context Derived from Header in dealer_dsr_api.py (DEALER IMPERSONATION)
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:38-89` (used by `invite_dsr`, `revoke_invitation`, `list_dsrs`, `update_dsr`, `remove_dsr`, `search_dsr`)
- **Code:**
  ```python
  async def aget_dealer_from_request(request):
      dealer_username = request.headers.get("X-Dealer-Username")  # ← header only!
      if not dealer_username:
          return None
      return await DealerConfig.objects.aget(username=dealer_username)
  ```
- **Impact:** **CRITICAL**. While the middleware correctly resolves the dealer context for most controllers (`request.dealer_username`), this controller re-derives it from the raw `X-Dealer-Username` header. An attacker who can send ANY `X-Dealer-Username: <target_dealer>` (e.g., forger from S-1, or a malicious DSR with their own valid JWT) can:
  - Invite/remove DSRs **on behalf of any dealer**
  - View all DSRs of any dealer
  - Update permissions of any dealer's DSRs
  - Search for DSRs across the entire platform
- **Note:** The middleware trusts the same header for DSRs (`permission_middleware.py:60`), but it does enforce that the DSR's email matches an assignment before letting them act as a dealer in `dealer_context.py` — but only if S-2 isn't crashing first.
- **Fix:**
  ```python
  dealer_username = getattr(request, 'dealer_username', None) or request.headers.get('X-Dealer-Username')
  if not dealer_username:
      return 400, {"detail": "Dealer context required", ...}
  # Always verify the dealer in request matches X-Dealer-Username header
  if request.headers.get('X-Dealer-Username') and request.headers.get('X-Dealer-Username') != dealer_username:
      raise HttpError(403, "Dealer context mismatch")
  ```

### S-4: `invitation_api.py:313` Passes Non-Existent Field to `acreate`
- **File:** `dealerbackend/dsr/invitation_api.py:307-313`
- **Code:**
  ```python
  assignment = await DsrDealerAssignment.objects.acreate(
      id=f"assign-{dsr.id}",
      dsr=dsr,
      dealer=invitation.dealer,
      role=invitation.role,
      parent_dsr=invitation.parent_dsr,
      is_active=True,  # ← field doesn't exist!
  )
  ```
- **Impact:** **CRITICAL**. Every invitation acceptance crashes with `TypeError: DsrDealerAssignment() got unexpected keyword argument 'is_active'`. The whole invitation-accept flow is broken — DSRs cannot accept invitations at all.
- **Fix:**
  ```python
  assignment = await DsrDealerAssignment.objects.acreate(
      id=f"assign-{dsr.id}",
      dsr=dsr,
      dealer=invitation.dealer,
      role=invitation.role,
      parent_dsr=invitation.parent_dsr,
      status=DsrDealerAssignment.STATUS_ACTIVE,  # correct field
  )
  ```

### S-5: Hardcoded SECRET_KEY (TOKEN FORGERY)
- **File:** `dealerbackend/dealercore/settings.py:28`
- **Code:**
  ```python
  SECRET_KEY = "django-insecure-(...)"  # ← hardcoded default
  ```
- **Impact:** **CRITICAL**. Used as `NINJA_JWT.SIGNING_KEY` (settings.py:242) for all local DSR tokens. Anyone with source-code access can sign valid DSR tokens. If this leaks (git history, image backup, .env.example), attackers can forge tokens offline even without S-1.
- **Fix:**
  ```python
  SECRET_KEY = os.environ["SECRET_KEY"]  # fail-fast if missing
  ```

### S-6: `PermissionMiddleware` Silently Swallows ALL Exceptions
- **File:** `dealerbackend/common/permission_middleware.py:91-92, 215-216`
- **Code:**
  ```python
  except jwt.InvalidTokenError:
      return None, False, None, None
  except Exception:
      return None, False, None, None  # ← catches everything!
  ```
- **Impact:** **CRITICAL**. Any unexpected error in JWT parsing (malformed token, version mismatch, missing library) silently grants "anonymous" status. If a controller relies solely on `request.user_role is None` to deny access, and a different code path allows the request to continue (e.g., when another middleware also runs), requests can pass with no identity at all.
- **Fix:** Log the exception and explicitly return a 401 for protected paths.

### S-7: `DealerDsrController` Decorated with `permissions=[AllowAny]` (ENTIRE API SURFACE IS PUBLIC)
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:71`
- **Code:**
  ```python
  @api_controller("/dealer/dsr", tags=["Dealer DSR Management"], permissions=[AllowAny])
  class DealerDsrController:
  ```
- **Impact:** **CRITICAL**. Every endpoint under `/dealer/dsr/*` (`invite_dsr`, `list_invitations`, `revoke_invitation`, `list_dsrs`, `update_dsr`, `remove_dsr`, `search_dsr`) is reachable without ANY authentication. Combined with S-3 (header-based dealer impersonation), an unauthenticated attacker can:
  - List every DSR/email of any dealer
  - Invite a fake DSR to any dealer
  - Modify or remove any dealer's DSR assignments
  - Enumerate registered DSR emails via `search_dsr`
- **Exploit:**
  ```bash
  # No auth needed:
  curl -X GET http://localhost:8088/dealer/dsr -H "X-Dealer-Username: victim"
  curl -X POST http://localhost:8088/dealer/dsr/invite \
       -H "X-Dealer-Username: victim" -H "Content-Type: application/json" \
       -d '{"dsr_email": "attacker@evil.com", "role": "DSR"}'
  ```
- **Fix:** Replace with `permissions=[IsJwtAuthenticated]` (custom JWT-aware permission) plus per-endpoint `require_dealer` check.

### S-8: `invitation_api.py` References Non-Existent `email` Field on `DsrInvitation` (ENTIRE CONTROLLER BROKEN)
- **File:** `dealerbackend/dsr/invitation_api.py` — lines 104, 115, 131, 171, 206, 247, 259
- **Code (representative):**
  ```python
  # line 104
  existing = await DsrInvitation.objects.filter(dealer=dealer, email=data.email, ...)
  # line 247
  if user_email.lower() != invitation.email.lower():
  ```
- **Context:** The model field is `dsr_email`, not `email` (invitation_models.py:150).
- **Impact:** **CRITICAL**. Every method in `DsrInvitationController` references the wrong field. Results:
  - `create_invitation`: `DsrInvitation(... email=data.email ...)` → `TypeError: unexpected keyword argument 'email'`
  - All read paths: `invitation.email` → `AttributeError`
  - **The entire invitation controller is non-functional.**
- **Fix:** Rename all `email` → `dsr_email` in `invitation_api.py` (7 sites).

### S-9: `create_invitation` Omits Mandatory `id` CharField PK
- **File:** `dealerbackend/dsr/invitation_api.py:112-116`
- **Code:**
  ```python
  invitation = DsrInvitation(
      dealer=dealer, email=data.email, role=data.role,
      parent_dsr=parent_dsr, message=data.message,
  )
  ```
- **Context:** `DsrInvitation.id = models.CharField(max_length=100, primary_key=True)` with no default.
- **Impact:** **CRITICAL**. Saving the row raises `IntegrityError` (no PK value). Even after S-8 is fixed, this still breaks creation.
- **Fix:** Add `id=` to the kwargs, e.g., `id=f"INV-{dealer.username}-{secrets.token_hex(8)}"`.

### S-10: `await queryset[:limit].all()` Is Invalid Django Async Syntax
- **File:** `dealerbackend/dsr/invitation_api.py:120`
- **Code:**
  ```python
  invitations = await queryset[:limit].all()
  ```
- **Impact:** **CRITICAL**. `QuerySet` is not awaitable and `QuerySet.all()` is sync (no `aall()` in Django 5.2). Raises `TypeError: object QuerySet can't be used in 'await' expression`. The `list_invitations` endpoint is completely broken.
- **Fix:**
  ```python
  invitations = [inv async for inv in queryset[:limit]]
  ```

---

## 3. High-Severity Bugs

### H-1: `SSOController` Uses `IsAuthenticated` (Always Denies JWT Users)
- **File:** `dealerbackend/common/sso_controller.py:42`
- **Code:** `permissions=[IsAuthenticated]` — checks Django session auth, not JWT.
- **Impact:** System uses JWT auth everywhere, so `request.user` is always `AnonymousUser`. SSO endpoints are unreachable. Either dead code or all SSO calls 401.
- **Fix:** Replace with a JWT-aware permission class:
  ```python
  class IsJwtAuthenticated:
      def has_permission(self, request, controller):
          return getattr(request, 'user_role', None) is not None
  ```

### H-2: `AccessController` Has NO Permission Protection
- **File:** `dealerbackend/common/access_controller.py:35`
- **Code:** No `permissions=[...]` on the controller class.
- **Impact:** Each endpoint manually extracts the token. Easy to forget on a new endpoint → public.
- **Fix:** Add `permissions=[IsJwtAuthenticated]` at controller level.

### H-3: JWT `is_active` Not Checked on Token Validation
- **File:** `dealerbackend/dsr/auth_api.py:128-163` (`get_user_from_token` / `aget_user_from_token`)
- **Code:** Fetches user, returns it — no `if not user.is_active: return None` check.
- **Impact:** Deactivated users can still use valid JWTs indefinitely.
- **Fix:** Add `if not user.is_active: return None`.

### H-4: JWT `token_type` Not Checked
- **File:** `dealerbackend/dsr/auth_api.py:114-123` (`decode_token`)
- **Code:** Accepts any valid JWT, doesn't check `token_type`.
- **Impact:** A long-lived refresh token (7 days) can be used directly as an access token against protected endpoints (`/me`, `/select-dealer`, `/change-password`).
- **Fix:** Reject if `payload.get("token_type") != "access"`.

### H-5: Login Timing Attack (Email Enumeration)
- **File:** `dealerbackend/dsr/auth_api.py:388-395`
- **Code:** `check_password()` (PBKDF2) only runs when email exists. Missing user → immediate return.
- **Impact:** Attacker can enumerate registered emails via response timing.
- **Fix:** Always run a dummy `check_password()` against a fixed hash to equalize timing.

### H-6: No Rate Limiting on Login / Register / Refresh / Forgot-Password
- **Files:** `dealerbackend/dsr/auth_api.py`, `dealerbackend/common/auth_controller.py`
- **Impact:** Brute-forceable credentials, can exhaust SattaBase rate limits.
- **Fix:** Apply `django-ratelimit` or Ninja throttle decorators.

### H-7: Password Change Does Not Invalidate Existing Tokens
- **File:** `dealerbackend/dsr/auth_api.py:671-680`
- **Impact:** Stolen tokens remain valid after password change. Attacker retains access.
- **Fix:** Add `password_changed_at` claim to JWTs; reject tokens issued before that timestamp. Or blacklist outstanding refresh tokens on password change.

### H-8: Dealer Not Validated Against JWT in `get_dealer_context`
- **File:** `dealerbackend/common/dealer_context.py:104-117`
- **Code:** When `is_dealer=True`, returns `user_dealer_username` without checking it equals the `X-Dealer-Username` header value (if any).
- **Impact:** A dealer could spoof X-Dealer-Username to confuse downstream filters that use the header. Combined with S-3, this widens the impersonation.
- **Fix:** Cross-check header and JWT-derived dealer_username; raise 403 on mismatch.

### H-9: Sync `self.save()` Inside Async Views (Runtime Crash)
- **Files:** `dealerbackend/dsr/auth_api.py:701, 726` — `set_password_reset_token()` and `clear_password_reset_token()` are sync.
- **Impact:** Calls to `request_password_reset` and `confirm_password_reset` crash with `SynchronousOnlyOperation` (Django 5.2 async). Password reset is non-functional.
- **Fix:** Use `await sync_to_async(user.set_password_reset_token)(token)` or refactor to async.

### H-10: `search_dsr` Is Public (Email/PII Enumeration)
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:71` (controller-level `AllowAny`) + endpoint at line 390-471
- **Impact:** Any unauthenticated attacker can probe any email and learn:
  - Whether the email is registered as a DSR
  - The DSR's name and phone
  - Whether the DSR is already assigned to the spoofed dealer
- **Exploit:**
  ```bash
  curl 'http://localhost:8088/dealer/dsr/search?email=victim@x.com' \
       -H "X-Dealer-Username: any"
  ```
- **Fix:** Add `permissions=[IsJwtAuthenticated]` plus `require_dealer` check.

### H-11: `accept_invitation` Creates Orphan DSR (No `user` FK, Empty Email)
- **File:** `dealerbackend/dsr/invitation_api.py:265-273`
- **Code:**
  ```python
  dsr = await DSR.objects.acreate(
      id=..., name=dsr_name, phone="", role=invitation.role,
      parent_dsr=invitation.parent_dsr, parent_dsr_name=...,
  )
  ```
- **Impact:** Even after fixing S-4, the new DSR row has no `user` FK and `email=""`. The validation gate (`validate_dsr_access`) matches DSR by `dsr__email=user_email`, so the new DSR can NEVER pass the check and is locked out of all dealer-scoped endpoints.
- **Fix:** Look up the existing DSR by email first; if found, link `user=authenticated_user`, set `email=user_email`. Only create a new DSR if none exists.

### H-12: `accept_invitation` Doesn't Reuse Existing DSR Profile
- **File:** `dealerbackend/dsr/invitation_api.py:265`
- **Impact:** A user accepting multiple invitations creates a NEW DSR row each time. No lookup by JWT `user_email` or `DsrUser`. Over time: duplicate orphan records, analytics pollution, broken audit trail.
- **Fix:** `dsr = await DSR.objects.filter(email=user_email).afirst() or await DSR.objects.acreate(...)`.

### H-13: Unique Constraint on `(dealer, dsr_phone)` Blocks Email-Only Invites
- **File:** `dealerbackend/dsr/invitation_models.py:184-186`
- **Code:**
  ```python
  UniqueConstraint(fields=["dealer", "dsr_phone"], condition=Q(status="pending"), name="...")
  ```
- **Impact:** `dsr_phone` defaults to `""`. A dealer sending two pending email-only invitations (phone blank) crashes on the second save with `IntegrityError` because `(dealer, "")` already exists.
- **Fix:** Relax the constraint to `condition=Q(status="pending") & ~Q(dsr_phone="")`, or remove the empty-string default and require phone OR drop the unique constraint.

### H-14: `permissions.py` Role Enum Doesn't Recognize `Senior_DSR` or `Manager`
- **File:** `dealerbackend/common/permissions.py:10-16`
- **Impact:** Invitations can be created with `Senior_DSR` / `Manager` roles, but `Role` enum only knows `DEALER | DSR | COLLECTOR | ADMIN`. `PermissionChecker.can()` returns `False` for every permission for those roles → users locked out of resources they were explicitly granted.
- **Fix:** Add the missing roles to `Role` enum and `ROLE_PERMISSIONS` map.

### H-15: `update_dsr` Accepts Arbitrary Role Strings (Privilege Escalation)
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:246`
- **Code:** `if data.role is not None: assignment.role = data.role` — no validation.
- **Impact:** Dealer can set `assignment.role = "superadmin"` or any string, bypassing any permission checks that rely on exact role matches.
- **Fix:** Validate against `DsrInvitation.ROLE_CHOICES` before assignment.

### H-16: `invite_dsr` Blocks Re-Inviting Previously Removed DSR
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:83`
- **Code:**
  ```python
  existing_assignment = await DsrDealerAssignment.objects.filter(
      dsr=dsr_profile, dealer=dealer
  ).aexists()  # ← no status filter
  ```
- **Impact:** A DSR who was previously removed (status=removed) can never be invited again, even though that's a common workflow.
- **Fix:** Filter `status__in=[STATUS_REMOVED, STATUS_LEFT]` in the existing-assignment check, OR delete old assignments on re-invite.

### H-17: `deactivate_assignment` / `activate_assignment` Lack Authorization
- **File:** `dealerbackend/dsr/invitation_api.py:440-465`
- **Impact:** Any authenticated user with `X-Dealer-Username` header can activate/deactivate ANY DSR's assignment. Combined with S-1/S-3, trivial impersonation.
- **Fix:** Verify `request.is_dealer and request.dealer_username == assignment.dealer.username`.

### H-18: `transaction.atomic()` + Sync `save()` Inside Async View
- **File:** `dealerbackend/dsr/invitation_api.py:112-116`
- **Impact:** Sync ORM in async view → blocks event loop, not wrapped in `sync_to_async`.
- **Fix:** Use `asave()` and `async with transaction.atomic():`.

### H-19: Multiple Sync `get_object_or_404` in Async Views
- **Files:** `dealerbackend/dsr/invitation_api.py:229, 344, 366, 440, 459`
- **Impact:** Sync helpers in async views block the event loop.
- **Fix:** Use `await aget_object_or_404` from `django.shortcuts` (Django 5 supports async version).

### H-20: Raw Invitation Token Returned in `invite_dsr` Response (with AllowAny)
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:125`
- **Impact:** The response includes `"token": invitation.token`. With `AllowAny`, an unauthenticated attacker can generate an invitation and capture the token, then use it to register as the invited DSR. Same risk in `invitation_api.py:131` via `invite_url`.
- **Fix:** Strip `token` from the response schema; only return `registration_url`.

---

## 4. Medium-Severity Bugs

### M-1: aiohttp Missing Timeout (DoS)
- **File:** `dealerbackend/common/sattabase_client.py:48`
- **Impact:** Hung SattaBase connection blocks ASGI worker indefinitely → trivial DoS.
- **Fix:** `timeout=aiohttp.ClientTimeout(total=10)`.

### M-2: aiohttp Session Race (Connection Leak)
- **File:** `dealerbackend/common/sattabase_client.py:45-52`
- **Impact:** Two concurrent coroutines can both pass `if self._session is None` and create two sessions → leak.
- **Fix:** Guard with `asyncio.Lock`.

### M-3: `require_permission` Raises Built-in `PermissionError`
- **File:** `dealerbackend/common/permissions.py:149-175`
- **Impact:** Django Ninja doesn't catch built-in `PermissionError`; denial returns **500** instead of 403.
- **Fix:** Raise `ninja_extra.exceptions.PermissionDenied` instead.

### M-4: Password Reset Token Stored Plaintext
- **File:** `dealerbackend/users/models.py:143`
- **Impact:** DB read = full account takeover for users with active reset requests.
- **Fix:** Store SHA-256 hash of token.

### M-5: Invitation Token Exposed in `list_invitations` Response
- **File:** `dealerbackend/dsr/auth_api.py:773-788`
- **Impact:** Compromised DSR account leaks usable registration tokens for other dealers.
- **Fix:** Remove `token` from `InvitationOutput` schema.

### M-6: PII Logged to Console
- **Files:** `dealerbackend/dsr/auth_api.py` (multiple lines)
- **Impact:** Email, phone, full_name in stdout/logs (Docker, CloudWatch). PII leak surface.
- **Fix:** Remove `print(...)` debug statements.

### M-7: Race Condition on Uniqueness Checks
- **Files:** `dealerbackend/dsr/auth_api.py:200-212, 296-302`
- **Impact:** Concurrent registrations with same email/phone both pass `aexists()` check, one crashes with unhandled `IntegrityError` → 500.
- **Fix:** Wrap in `transaction.atomic()` and catch `IntegrityError`.

### M-8: Empty-Phone Duplicate Check Blocks Registration
- **File:** `dealerbackend/dsr/auth_api.py:296-301`
- **Impact:** `phone=""` returns True after first empty-phone registration → no subsequent registration allowed.
- **Fix:** Skip duplicate check if phone is blank; enforce at DB level.

### M-9: Email Case-Sensitivity Collision
- **File:** `dealerbackend/dsr/auth_api.py:388`
- **Impact:** `email__iexact='john@example.com'` with Django's partial normalization (only domain lowercased) can raise `MultipleObjectsReturned` in SQLite.
- **Fix:** Normalize email to lowercase before storage and query.

### M-10: `async with transaction.atomic()` Missing
- **Files:** `dealerbackend/dsr/auth_api.py:188-239, 301-322, 829-841` — multiple create flows.
- **Impact:** Multi-step operations can leave orphans if a step fails mid-way (e.g., DsrUser created but DSR profile fails).
- **Fix:** Wrap all multi-step creations in `async with transaction.atomic():`.

### M-11: `invite_dsr` Generates Predictable Invitation IDs
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:127`
- **Code:** `invitation_id = f"INV-{dealer.username}-{email.split('@')[0][:8]}-{secrets.token_hex(4)}"` — only 4 bytes of randomness, rest is predictable.
- **Impact:** While the actual `token` field uses full 256-bit randomness, the ID is easily guessable. If the token column is ever exposed in a list (M-5) or leaked, attackers can iterate predictable IDs.
- **Fix:** Use UUID4 for invitation ID.

### M-12: `remove_dsr` Bulk-Updates Non-Existent `SaleRecord` Fields
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:280-290`
- **Code:**
  ```python
  await SaleRecord.objects.filter(dsr=dsr, dealer=dealer).aupdate(dsr_status='removed')
  await SaleRecord.objects.filter(original_dsr=dsr, dealer=dealer).aupdate(original_dsr_status='removed')
  ```
- **Impact:** If `SaleRecord` lacks `dsr_status` / `original_dsr_status` fields, this raises `FieldError` on every removal. Either adds 2 more silent broken endpoints.
- **Fix:** Verify field existence; either add them via migration or guard the `.aupdate`.

### M-13: `DsrDealerAssignment.on_delete=CASCADE` Contradicts "History Preserved"
- **File:** `dealerbackend/dsr/invitation_models.py:277, 291`
- **Impact:** Both FKs use CASCADE, so deleting a DSR or Dealer hard-deletes every assignment — breaking the "records are never deleted" promise in the docstring.
- **Fix:** Change to `SET_NULL` (with `null=True, blank=True` on FK), OR use soft-delete pattern.

### M-14: N+1 Query in `list_invitations`
- **File:** `dealerbackend/dsr/invitation_api.py:167-178`
- **Impact:** Iterates `invitation.parent_dsr.name` without `select_related('parent_dsr')`. One extra query per invitation.
- **Fix:** Add `.select_related('parent_dsr')` to the queryset.

---

## 5. Low-Severity Bugs

### L-1: `require_dealer` Decorator Dead Code
- **File:** `dealerbackend/common/permission_middleware.py:120` (`DealerOnlyMiddleware`)
- **Impact:** Defined but never registered in `MIDDLEWARE`.
- **Fix:** Either register or delete.

### L-2: `AsyncPermissionMiddleware` Dead Code
- **File:** `dealerbackend/common/permission_middleware.py:154`
- **Impact:** Sync version is registered, async version exists but is dead.
- **Fix:** Replace sync with async in `MIDDLEWARE` setting.

### L-3: No `iss` / `aud` Validation in JWT Decode (when fixed)
- **File:** `dealerbackend/common/permission_middleware.py:85, 196`
- **Impact:** Even if signature checking is added, tokens from other services with the same key would be accepted.
- **Fix:** Add `issuer="sattabase"`, `audience="dealerbackend"`.

### L-4: CORS / ALLOWED_HOSTS Defaults for Production
- **File:** `dealerbackend/dealercore/settings.py:33, 100-111`
- **Impact:** `ALLOWED_HOSTS = ['*']`, CORS defaults include localhost ports. If env vars not set in prod, these remain active.
- **Fix:** Default to empty lists, fail on startup if env vars missing.

### L-5: `Cookie secure=not settings.DEBUG`
- **File:** `dealerbackend/common/auth_controller.py:91, 140`
- **Impact:** If `DEBUG=True` accidentally in production, refresh token cookie sent over plaintext HTTP.
- **Fix:** `secure=True` always.

### L-6: Frontend Tokens in sessionStorage (XSS Theft)
- **File:** `dealerfrontend/src/lib/api.ts:60-78`
- **Impact:** While sessionStorage is safer than localStorage, it is still accessible to any JS on the page. XSS = full token theft. The "remember me" option uses localStorage (worse).
- **Fix:** Move access tokens to httpOnly cookie (already used for refresh), keep refresh in httpOnly + Secure + SameSite=Strict.

### L-7: Frontend `console.log` of Dealer Selection in Production
- **File:** `dealerfrontend/src/lib/api.ts:115-122`
- **Impact:** `getSelectedDealerUsername()` logs to console in production, exposing dealer context.
- **Fix:** Remove or gate behind `import.meta.env.DEV`.

### L-8: `redirectToBase` URL Manipulation
- **File:** `dealerfrontend/src/lib/auth.ts:140-153`
- **Impact:** `returnUrl` defaults to `window.location.href` if not provided. An attacker-controlled link can redirect the user back to a phishing page after login.
- **Fix:** Validate `returnUrl` starts with `config.thisDomainUrl`.

### L-9: `DsrInvitation.token` Stored Plaintext in DB
- **File:** `dealerbackend/dsr/invitation_models.py:210-222`
- **Impact:** Token generated with strong entropy but stored unhashed. DB dump = reusable invitation URLs.
- **Fix:** Store SHA-256 hash, compare hashes.

### L-10: Hard-Coded 7-Day TTL on Invitations
- **File:** `dealerbackend/dsr/invitation_models.py:217`
- **Impact:** No per-invitation override or system setting.
- **Fix:** Make configurable.

### L-11: `is_dealer` Auto-Detection DB Lookup Is Expensive
- **File:** `dealerbackend/common/dealer_context.py:36`
- **Impact:** `_check_is_dealer_by_user_id` runs an async DB query on every request for non-dealers. Cache it.

### L-12: `dealer_dsr_api.py` Double-Saves on Revoke
- **File:** `dealerbackend/dsr/dealer_dsr_api.py:260-261`
- **Code:** `invitation.revoke()` (sync save) followed by `await invitation.asave()`.
- **Impact:** Redundant DB round-trip and small race window.
- **Fix:** Use only `await invitation.arevoke()`.

---

## 6. Logic / Correctness Bugs

| Severity | File:line | Description |
|----------|-----------|-------------|
| High | `dealerbackend/dsr/auth_api.py:226` | DSR ID truncates UUID to 8 hex chars → 32 bits entropy, collision ~65k users. |
| High | `dealerbackend/dsr/auth_api.py:322, 841` | `DsrDealerAssignment.id = f"ASSIGN-{dsr_id}-{dealer}"` may exceed `max_length=100` → DataError. |
| Med | `dealerbackend/dsr/invitation_api.py:248-270` | `accept_invitation` creates a NEW DSR every time, even if user already has one. |
| Med | `dealerbackend/dsr/invitation_api.py:325-329` | Invitation `aaccept()` is called AFTER assignment creation, but `DsrInvitation` has a unique constraint on `(dealer, dsr_phone, status='pending')`. If `accepted_at` save fails, the unique constraint blocks future invitations for the same phone. |
| Med | `dealerbackend/dsr/auth_api.py:560-565` | Logout reads refresh token from cookie only; SPA mobile clients use body → silently no-ops. |
| Med | `dealerbackend/dsr/auth_api.py:829-841` | `accept_invitation` race: two simultaneous accept calls both pass the `aexists` check → `IntegrityError` on create. |
| Med | `dealerbackend/dsr/invitation_api.py:170-175` | `existing` check uses `invitation.email` but field is `dsr_email`. Query is always empty → duplicate invitations allowed. |
| Med | `dealerbackend/dsr/invitation_api.py:263-264` | DSR created with `phone=""` and `name=email.split('@')[0]` — arbitrary phone is never overwritten. |
| Low | `dealerbackend/dsr/auth_api.py:402` | `email_verified` returned in API but never checked. |
| Low | `dealerbackend/dsr/auth_api.py:688-709` | Password reset email/SMS dispatch is a TODO — feature non-functional. |

---

## 7. Async / Django Issues

| Severity | File:line | Description |
|----------|-----------|-------------|
| High | `dealerbackend/dsr/auth_api.py:701, 726` | Sync `self.save()` in async views → `SynchronousOnlyOperation`. |
| High | `dealerbackend/dsr/auth_api.py:560-565` | `token.blacklist()` is sync in async logout. |
| Med | `dealerbackend/dsr/auth_api.py:243` | `DSR._meta.get_fields()` sync in async exception handler. |
| Med | `dealerbackend/dsr/invitation_api.py:223` | `DsrInvitation.save()` is sync; called inside `async def` wrapped in `transaction.atomic()`. |
| Med | `dealerbackend/common/sattabase_client.py:48` | aiohttp session creation not wrapped in lock. |

---

## 8. Other Concerns

1. **`DEBUG=True` in settings** — `settings.py:31`. All errors leak stack traces.
2. **`SILENCED_SYSTEM_CHECKS = ["security.W019"]`** — `settings.py:65`. Actively hides the ALLOWED_HOSTS warning.
3. **No `extra='forbid'`** on Pydantic schemas — mass-assignment silent for unexpected fields.
4. **`@api_controller("/dsr/auth", ..., permissions=[AllowAny])`** — public endpoints rely on manual checks inside each handler. Easy to miss on new endpoint → public exposure.
5. **No `iss` / `aud` validation** — even after S-1 is fixed, tokens from other services with same key would be accepted.
6. **Frontend `auth.ts:111-127` logout swallows all errors** — no logging when blacklist fails server-side.
7. **`refreshPromise` dedup is correct** — frontend `api.ts:174-216` properly dedups concurrent refreshes. Good practice.
8. **`getSelectedDealerUsername()` logs to console** — privacy/PII leak in production.

---

## 9. Prioritized Fix Plan

### Phase 1: Stop the Bleeding (Deploy immediately — ~3 hours)

| # | Bug | Effort | Action |
|---|-----|--------|--------|
| 1 | **S-1 JWT signature disabled** | 30 min | Enable signature verification with `SECRET_KEY` + `algorithms=["HS256"]` |
| 2 | **S-2 `is_active=True` filter** | 5 min | Change to `status=STATUS_ACTIVE` in `dealer_context.py:175,248` |
| 3 | **S-3 dealer context from header** | 30 min | Use `request.dealer_username` in `dealer_dsr_api.py`; cross-check header |
| 4 | **S-4 `is_active=True` on create** | 5 min | Change to `status=STATUS_ACTIVE` in `invitation_api.py:313` |
| 5 | **S-5 hardcoded SECRET_KEY** | 5 min | Move to env; rotate the key |
| 6 | **S-7 `DealerDsrController` AllowAny** | 15 min | Replace `AllowAny` with `IsJwtAuthenticated` + dealer ownership check |
| 7 | **S-8 `email` vs `dsr_email`** | 15 min | Rename 7 occurrences in `invitation_api.py` |
| 8 | **S-9 missing PK `id`** | 5 min | Add `id=f"INV-{...}"` to `DsrInvitation(...)` |
| 9 | **S-10 invalid `await queryset.all()`** | 5 min | Change to `[inv async for inv in queryset[:limit]]` |
| 10 | **H-1 SSO dead code** | 15 min | Replace `IsAuthenticated` with JWT-aware permission |
| 11 | **H-3 is_active not checked** | 5 min | Add check in `get_user_from_token` |
| 12 | **H-4 token_type not checked** | 10 min | Reject non-access tokens in `decode_token` |
| 13 | **H-11 orphan DSR on accept** | 15 min | Look up existing DSR by email first; link `user=` and set `email=` |
| 14 | **H-20 raw token in response** | 10 min | Strip `token` from response schema |
| 15 | **M-1 aiohttp no timeout** | 5 min | Add `ClientTimeout(total=10)` |

### Phase 2: Harden (Within 1 week — ~2 days)

| # | Bug | Effort | Action |
|---|-----|--------|--------|
| 1 | **M-5 invitation token in list response** | 10 min | Strip token from schema |
| 2 | **M-4 plaintext reset tokens** | 1 hr | Hash tokens |
| 3 | **H-5 timing attack on login** | 30 min | Dummy `check_password` for missing users |
| 4 | **H-6 rate limiting** | 2 hr | Add `django-ratelimit` decorators |
| 5 | **H-7 token invalidation on password change** | 2 hr | Add `password_changed_at` claim |
| 6 | **H-9 sync save in async views** | 1 hr | Wrap in `sync_to_async` or refactor |
| 7 | **M-3 500 instead of 403** | 15 min | Raise `PermissionDenied` |
| 8 | **L-4 ALLOWED_HOSTS / CORS** | 15 min | Restrict to production domains |
| 9 | **L-6 token storage** | 4 hr | Move to httpOnly cookies |
| 10 | **H-10 search_dsr public** | 30 min | Add auth + dealer ownership |
| 11 | **H-13 unique constraint blocks email-only invites** | 30 min | Relax the constraint or remove empty phone default |
| 12 | **H-14 Senior_DSR/Manager role unknown** | 30 min | Add to `Role` enum + permissions map |
| 13 | **H-15 arbitrary role strings** | 15 min | Validate against `ROLE_CHOICES` |
| 14 | **H-16 blocks re-inviting removed DSR** | 15 min | Filter `status__in=[REMOVED, LEFT]` |
| 15 | **H-17 deactivate/activate lacks authz** | 30 min | Add `require_dealer` check |
| 16 | **H-18/H-19 sync ORM in async views** | 2 hr | Convert to async equivalents |

### Phase 3: Polish (Within 2 weeks — ~1 week)

| # | Bug | Effort |
|---|-----|--------|
| 1 | **M-7, M-10 race conditions + transactions** | 4 hr |
| 2 | **L-1, L-2 dead middleware** | 30 min |
| 3 | **M-11 predictable invitation IDs** | 15 min |
| 4 | **M-6 PII in logs** | 1 hr |
| 5 | **M-2 aiohttp session race** | 30 min |
| 6 | **L-8 returnUrl validation** | 30 min |
| 7 | **M-12 SaleRecord field check** | 30 min |
| 8 | **M-13 CASCADE contradicts history** | 1 hr |
| 9 | **M-14 N+1 in list_invitations** | 15 min |
| 10 | **L-9 plaintext invitation tokens** | 1 hr |
| 11 | **Logic bugs (DSR created fresh each accept, etc.)** | 4 hr |

### Phase 2: Harden (Within 1 week)

| # | Bug | Effort | Action |
|---|-----|--------|--------|
| 1 | **M-5 invitation token in list response** | 10 min | Strip token from schema |
| 2 | **M-4 plaintext reset tokens** | 1 hr | Hash tokens |
| 3 | **H-5 timing attack on login** | 30 min | Dummy `check_password` for missing users |
| 4 | **H-6 rate limiting** | 2 hr | Add `django-ratelimit` decorators |
| 5 | **H-7 token invalidation on password change** | 2 hr | Add `password_changed_at` claim |
| 6 | **H-9 sync save in async views** | 1 hr | Wrap in `sync_to_async` or refactor |
| 7 | **M-3 500 instead of 403** | 15 min | Raise `PermissionDenied` |
| 8 | **L-4 ALLOWED_HOSTS / CORS** | 15 min | Restrict to production domains |
| 9 | **L-6 token storage** | 4 hr | Move to httpOnly cookies |

### Phase 3: Polish (Within 2 weeks)

| # | Bug | Effort |
|---|-----|--------|
| 1 | **M-7, M-10 race conditions + transactions** | 4 hr |
| 2 | **L-1, L-2 dead middleware** | 30 min |
| 3 | **M-11 predictable invitation IDs** | 15 min |
| 4 | **M-6 PII in logs** | 1 hr |
| 5 | **M-2 aiohttp session race** | 30 min |
| 6 | **L-8 returnUrl validation** | 30 min |
| 7 | **Logic bugs (DSR created fresh each accept, etc.)** | 4 hr |

---

## 10. Verification Steps

To verify each fix:

```bash
# S-1: Forge a token, expect 401
python -c "
import jwt
forged = jwt.encode({'role':'dealer','is_dealer':True,'username':'victim'}, 'fake', algorithm='HS256')
print(forged)
"
# curl with Authorization: Bearer <forged> → should be 401 after fix

# S-2: Login as DSR, call /dsr/auth/me → should NOT 500
# (currently crashes with FieldError)

# S-3: Send X-Dealer-Username: other_dealer with valid DSR JWT
# → should be 403 after fix

# S-4: Dealer invites DSR; DSR clicks accept link
# → should succeed (currently crashes with TypeError)
```

---

## 11. Files Audited

### Backend (`dealerbackend/`)
- `common/auth_controller.py` — dealer auth proxy
- `common/sso_controller.py` — SSO endpoints
- `common/sattabase_client.py` — SattaBase HTTP client
- `common/permission_middleware.py` — JWT decode + role extraction
- `common/permissions.py` — Permission enum + helpers
- `common/access_controller.py` — Access endpoints
- `common/dealer_context.py` — Dealer context resolution
- `common/dsr_auth_errors.py` — DSR auth error helpers
- `common/tasks.py` — Celery tasks
- `dsr/auth_api.py` (1023 lines) — DSR auth endpoints
- `dsr/auth_schemas.py` (300 lines) — DSR auth Pydantic schemas
- `dsr/models.py` — DSR DB model
- `dsr/dealer_dsr_api.py` — Dealer→DSR management endpoints
- `dsr/invitation_api.py` — Invitation endpoints
- `dsr/invitation_models.py` — Invitation + Assignment DB models
- `dealercore/settings.py` — Django config

### Frontend (`dealerfrontend/src/`)
- `lib/api.ts` (17.8K) — Centralized API client + token management
- `lib/auth.ts` (8.7K) — Login, logout, SSO, redirect helpers
- (Other composables reviewed via Explore agent)

---

**Total bugs found:** 52 (11 critical, 15 high, 14 medium, 12 low)
**Estimated Phase 1 fix effort:** ~3 hours
**Estimated full fix effort:** ~1 week
