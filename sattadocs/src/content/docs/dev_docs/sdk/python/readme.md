---
title: Python sdk
description: the central authentication, subscription, and access-control platform for multi-tenant service domains.
---

# sattabase-sdk

Python SDK for **Sattabase** — the central authentication, subscription, and access-control platform for multi-tenant service domains.

> **Scope:** Auth + Permissions only. Billing, payments, and subscription management are handled entirely by the Sattabase frontend via Stripe. Sister domains never touch payment flows directly — the SDK provides redirect URLs for billing instead.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Modules](#modules)
  - [Auth (`client.auth`)](#auth-clientauth)
  - [Access (`client.access`)](#access-clientaccess)
  - [Billing Redirects (`client.billing`)](#billing-redirects-clientbilling)
- [Token Store](#token-store)
- [Django Middleware](#django-middleware)
- [Models](#models)
- [Exceptions](#exceptions)
- [Running Tests](#running-tests)
- [Development](#development)
- [Architecture Overview](#architecture-overview)

---

## Installation

```bash
pip install sattabase-sdk
```

With optional Redis token store:

```bash
pip install "sattabase-sdk[redis]"
```

For development:

```bash
pip install "sattabase-sdk[dev]"
```

**Requirements:** Python 3.10+, `httpx>=0.25`, `pydantic>=2.0`.

---

## Quick Start

```python
import asyncio
from sattabase_sdk import SattabaseClient, SattabaseConfig

config = SattabaseConfig(
    base_url="https://sattabase.tld/api/v1",
    service_domain="finance.sattabase.tld",
    api_key="sb_live_...",
)

async def main():
    async with SattabaseClient(config) as client:
        # Login
        tokens = await client.auth.login("user@example.com", "password")

        # Get domain-scoped user info + access map
        auth_me = await client.auth.me(tokens.access)
        print(f"User: {auth_me.user.display}")
        print(f"Plan: {auth_me.subscription.plan_name if auth_me.subscription else 'Free'}")

        # Feature gating
        if auth_me.has_access("reports"):
            print("User has reports access")

        # Get numeric limits
        max_accounts = auth_me.get_access("max_bank_accounts", default=1)
        print(f"Max bank accounts: {max_accounts}")

asyncio.run(main())
```

---

## Configuration

`SattabaseConfig` is a frozen dataclass that validates configuration at construction time.

| Field | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | *required* | Sattabase API base URL (e.g. `https://sattabase.tld/api/v1`) |
| `service_domain` | `str` | *required* | Identifies this service domain (e.g. `finance.sattabase.tld`) |
| `api_key` | `str` | *required* | Service credential raw key (format: `sb_live_{token_urlsafe(32)}`) |
| `timeout` | `float` | `10.0` | HTTP request timeout in seconds |
| `auto_refresh` | `bool` | `True` | Automatically refresh tokens on 401 responses |
| `max_retries` | `int` | `1` | Max retries after token refresh (total attempts = 1 + max_retries) |
| `debug` | `bool` | `False` | Allow `http://` base URLs and relax validation |

**Validation rules:**
- API key **must** start with `sb_live_`
- Base URL **must** use HTTPS unless `debug=True`
- Config is immutable after creation (frozen dataclass)

```python
config = SattabaseConfig(
    base_url="https://sattabase.tld/api/v1",
    service_domain="finance.sattabase.tld",
    api_key="sb_live_abcd1234efgh5678ijkl9012mnop3456",
    timeout=15.0,
    debug=False,  # Set True for local development with http://
)
```

The config exposes `app_base_url` (read-only property) which derives the frontend root by stripping `/api/v1`:

```python
config.app_base_url  # "https://sattabase.tld" (used by billing redirects)
```

---

## Modules

The `SattabaseClient` exposes three namespaced modules:

```python
client.auth      # Authentication methods
client.access    # Feature gating helpers (cached)
client.billing   # Billing redirect URL constructors
```

### Auth (`client.auth`)

All auth methods automatically include `X-API-Key` and `X-Service-Domain` headers. They map 1:1 to the backend `AuthController` endpoints.

#### `login(email, password) -> TokenPair`

Authenticate a user and obtain JWT tokens.

```python
tokens = await client.auth.login("user@example.com", "password")
print(tokens.access)   # Short-lived access token
print(tokens.refresh)  # Long-lived refresh token
```

#### `register(email, password, first_name, last_name, ...) -> MessageResponse`

Register a new user account. Optional fields: `timezone` (IANA), `currency` (ISO 4217), `language` (ISO 639-1).

```python
result = await client.auth.register(
    email="newuser@example.com",
    password="SecurePass1!",
    first_name="Rahim",
    last_name="Uddin",
    timezone="Asia/Dhaka",
    currency="BDT",
)
print(result.success)  # True
```

#### `me(token=None) -> AuthMeResponse`

Get domain-scoped user info, subscription, and access map. This is the **core method** for service domain integration. The backend resolves the domain via `X-API-Key` (priority) or `X-Service-Domain` header (fallback) and returns user data scoped to that domain's product.

```python
auth_me = await client.auth.me(tokens.access)

# User profile
print(auth_me.user.email)           # "user@example.com"
print(auth_me.user.display)         # "Rahim"
print(auth_me.user.is_email_verified)  # True

# Account status
print(auth_me.account_status)       # "active" | "inactive" | "deleted"

# Subscription info
if auth_me.subscription:
    print(auth_me.subscription.plan_name)       # "Standard"
    print(auth_me.subscription.status)          # "active"
    print(auth_me.subscription.is_active)       # True
    print(auth_me.subscription.current_period_end)  # datetime

# Feature access
print(auth_me.has_access("reports"))            # True
print(auth_me.get_access("max_bank_accounts"))  # 5
print(auth_me.access_keys)                      # ["dashboard", "reports", ...]
```

#### `refresh(refresh_token) -> TokenPair`

Refresh an expired access token.

```python
new_tokens = await client.auth.refresh(tokens.refresh)
```

#### `verify(token) -> MessageResponse`

Verify an access token is still valid.

```python
result = await client.auth.verify(tokens.access)
print(result.success)  # True
```

#### `blacklist(refresh_token) -> MessageResponse`

Invalidate a refresh token (used for logout). The access token continues working until its short TTL expires.

```python
await client.auth.blacklist(tokens.refresh)
```

#### `logout(token, refresh_token) -> None`

Convenience method — blacklists the refresh token and clears the token store if configured.

```python
await client.auth.logout(tokens.access, tokens.refresh)
```

#### Password Reset

```python
# Request OTP via email
await client.auth.request_password_reset("user@example.com")

# Confirm with OTP
await client.auth.confirm_password_reset(
    email="user@example.com",
    otp="123456",
    new_password="NewSecurePass1!",
    confirm_password="NewSecurePass1!",
)
```

#### Email Verification

```python
# Request OTP
await client.auth.request_email_verification("user@example.com")

# Confirm with OTP
await client.auth.confirm_email_verification(
    email="user@example.com",
    otp="123456",
)
```

### Access (`client.access`)

Feature access checking with client-side caching. Wraps `auth.me()` with a configurable TTL to avoid repeated API calls within a short window.

```python
# Check if user has access to a feature
can_export = await client.access.has_access("export_pdf", token=tokens.access)

# Get raw value (numeric limits, etc.)
max_accounts = await client.access.get_access("max_bank_accounts", default=1, token=tokens.access)

# Get all available access keys
keys = await client.access.keys(token=tokens.access)

# Force re-fetch (e.g., after returning from billing redirect)
client.access.invalidate_cache()
```

**Cache behavior:**
- Default TTL: 60 seconds (configurable via `cache_ttl` parameter)
- All `access.*` methods share the same cache
- Call `invalidate_cache()` when you know access has changed (e.g., after billing redirect with `billing_updated=1`)

### Billing Redirects (`client.billing`)

Zero API calls — these methods only construct URL strings for redirecting users to Sattabase's billing pages. The actual `return_url` validation happens server-side in the Sattabase backend.

```python
# Redirect to subscription management
url = client.billing.manage_subscription(
    product_slug="finance",
    return_url="https://finance.sattabase.tld/settings",
)
# -> "https://sattabase.tld/dashboard/billing/plans/finance?return_url=..."

# Redirect to upgrade page
url = client.billing.upgrade(
    product_slug="finance",
    return_url="https://finance.sattabase.tld/billing",
)

# Redirect to Stripe Customer Portal
url = client.billing.portal(return_url="https://finance.sattabase.tld/dashboard")
```

#### Detecting Billing Updates

After a user returns from a billing redirect, check for the `billing_updated` query parameter to refresh their access data:

```python
from sattabase_sdk.redirect import BillingRedirectModule

detected, value = BillingRedirectModule.detect_billing_update(request_url)
if detected and value == 1:
    # Billing was updated — refresh access
    client.access.invalidate_cache()
    auth_me = await client.auth.me(tokens.access)
elif detected and value == 0:
    # User cancelled or payment failed
    pass
```

Returns:
- `(True, 1)` — billing action succeeded
- `(True, 0)` — billing action cancelled or failed
- `(False, None)` — no `billing_updated` parameter present

---

## Token Store

The SDK uses a `TokenStore` protocol for persisting tokens across requests (required for auto-refresh). Implement the protocol or use one of the built-in stores.

### Protocol

```python
from sattabase_sdk.token_store import TokenStore
from sattabase_sdk.models import TokenPair

class MyTokenStore(TokenStore):
    async def get_tokens(self, user_id: str) -> TokenPair | None: ...
    async def set_tokens(self, user_id: str, tokens: TokenPair) -> None: ...
    async def delete_tokens(self, user_id: str) -> None: ...
```

### Extended Protocol (`TokenStoreWithLookup`)

For full auto-refresh support (including token resolution when `user_id` is unknown), implement the extended protocol. Both `InMemoryTokenStore` and `RedisTokenStore` implement this automatically.

```python
from sattabase_sdk.token_store import TokenStoreWithLookup
from sattabase_sdk.models import TokenPair

class MyStore(TokenStoreWithLookup):
    # ... TokenStore methods ...

    async def get_first_token_pair(self) -> TokenPair | None:
        """Return the first available token pair (for auto-refresh)."""
        ...

    async def get_user_id_by_refresh(self, refresh_token: str) -> str | None:
        """Find user_id by matching refresh token value."""
        ...
```

### In-Memory Store (development only)

```python
from sattabase_sdk.token_store import InMemoryTokenStore

store = InMemoryTokenStore()
client = SattabaseClient(config, token_store=store)

# After login, store tokens
await store.set_tokens("user_42", tokens)

# Auto-refresh will use the store to find refresh tokens
# InMemoryTokenStore implements TokenStoreWithLookup for full auto-refresh support
```

### Redis Store

```python
from sattabase_sdk.token_store import RedisTokenStore
import redis.asyncio as redis

redis_client = redis.from_url("redis://localhost:6379")
store = RedisTokenStore(redis_client)  # key_prefix defaults to "sb:tokens:"
client = SattabaseClient(config, token_store=store)
```

The optional `key_prefix` parameter controls the Redis key namespace (default: `"sb:tokens:"`). Keys in Redis follow the pattern `sb:tokens:<user_id>` → `JSON(TokenPair)`.

### Auto-Refresh

When `auto_refresh=True` (default), the client automatically refreshes expired tokens on 401 responses. It uses an async lock to prevent concurrent refresh calls. The flow:

1. Request returns 401
2. Client acquires refresh lock
3. Finds refresh token from the `TokenStore`
4. Calls `POST /auth/token/refresh`
5. Stores new tokens in the `TokenStore`
6. Retries the original request with the new access token

---

## Django Middleware

For sister domains running Django backends (Pattern A — backend proxy), the SDK provides a middleware that automatically attaches Sattabase user data to every request.

### Setup

Add to your Django `settings.py`:

```python
MIDDLEWARE = [
    # ... existing middleware
    "sattabase_sdk.middleware.SattabaseAuthMiddleware",
]

# Sattabase configuration
SATTABASE_BASE_URL = "https://sattabase.tld/api/v1"
SATTABASE_SERVICE_DOMAIN = "finance.sattabase.tld"
SATTABASE_API_KEY = "sb_live_..."
SATTABASE_AUTH_TIMEOUT = 5       # seconds (default: 5)
SATTABASE_AUTH_CACHE_TTL = 60    # seconds (default: 60)
```

### What it does

On every request, the middleware extracts the JWT access token from:

1. `Authorization: Bearer {token}` header
2. `access_token` cookie
3. `session["access_token"]`

Then it calls `auth/me` and attaches the results to the request:

```python
def my_view(request):
    # These are always available (None if not authenticated)
    user = request.sattabase_user          # User | None
    access = request.sattabase_access      # dict[str, Any]
    subscription = request.sattabase_subscription  # SubscriptionInfo | None

    if user is None:
        return redirect("login")

    if "reports" in access:
        # Show reports
        pass

    if subscription and subscription.is_active:
        # Show premium features
        pass
```

**Graceful degradation:** If the Sattabase API call fails (network error, 401, etc.), all three attributes are set to `None` — your views should always check. The middleware supports both sync and async Django views.

---

## Models

All models use Pydantic v2 and mirror the backend schemas exactly.

### `TokenPair`

```python
class TokenPair(BaseModel):
    access: str    # Short-lived JWT access token
    refresh: str   # Long-lived JWT refresh token
```

### `User`

```python
class User(BaseModel):
    id: int
    slug: str
    email: str
    first_name: str = ""
    last_name: str = ""
    phone: str | None = None
    avatar: str | None = None
    timezone: str | None = None
    currency: str | None = None
    language: str | None = None
    is_email_verified: bool = False
    is_active: bool = True
    role: str = "member"
    created_at: datetime | None = None
    full_name: str = ""
    display_name: str = ""

    @property
    def display(self) -> str:
        """Best display name: display_name > full_name > email prefix."""
```

### `SubscriptionInfo`

```python
class SubscriptionInfo(BaseModel):
    plan_name: str
    plan_slug: str
    status: str                   # "active", "trialing", "canceled", "past_due", etc.
    current_period_end: datetime | None = None
    trial_end: datetime | None = None
    is_active: bool = True
```

### `AuthMeResponse`

The core response from `auth/me`. Contains user, subscription, and the access map.

```python
class AuthMeResponse(BaseModel):
    user: User
    account_status: str = "active"              # "active" | "inactive" | "deleted"
    subscription: SubscriptionInfo | None = None
    access: dict[str, Any] = {}                 # Feature flags and limits

    def has_access(self, key: str) -> bool: ...      # Coerces strings/ints to bool
    def get_access(self, key: str, default=None): ...  # Raw value lookup
    @property
    def access_keys(self) -> list[str]: ...            # All available keys
```

### `MessageResponse`

Generic API response for status messages.

```python
class MessageResponse(BaseModel):
    message: str
    success: bool = True
```

---

## Exceptions

All SDK errors inherit from `SattabaseError`. The hierarchy:

```
SattabaseError                     # Base (all errors)
  AuthenticationError               # 401 — Invalid/expired token or API key
    AccountInactiveError            # 401 — User account deactivated (code: account_inactive)
    AccountDeletedError             # 401 — User account soft-deleted (code: account_deleted)
  ForbiddenError                    # 403 — Insufficient permissions
    AccountNotActiveError           # 403 — Email not verified (code: account_not_active)
  NotFoundError                     # 404 — Resource not found
  ConflictError                     # 409 — State conflict (duplicate, etc.)
  ValidationError                   # 422 — Invalid request body/parameters
  BadRequestError                   # 400 — Malformed request
  RateLimitError                    # 429 — Too many requests
    .retry_after                    # Seconds to wait (from response)
  ApiServerError                    # 5xx — Server error or network failure
```

**Error mapping priority:**
1. Match by `code` field from the response body (e.g., `account_deleted`)
2. Fall back to HTTP status code
3. Final fallback: `ApiServerError`

```python
from sattabase_sdk.exceptions import (
    SattabaseError,
    AuthenticationError,
    AccountInactiveError,
    AccountDeletedError,
    RateLimitError,
)

try:
    auth_me = await client.auth.me(token)
except AccountDeletedError:
    # User deleted their account — force logout, clear local data
    force_logout()
except AccountInactiveError:
    # Account deactivated by admin — force logout
    force_logout()
except RateLimitError as exc:
    # Wait and retry
    await asyncio.sleep(exc.retry_after or 60)
except AuthenticationError:
    # Token expired — redirect to login
    redirect_to_login()
except SattabaseError as exc:
    # Generic handler
    logger.error("Sattabase error: %s (status=%d)", exc.message, exc.status)
```

---

## Running Tests

```bash
cd sdk/python

# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test module
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=sattabase_sdk --cov-report=term-missing
```

```bash
# Run unit tests only (skip integration)
pytest -m "not integration"

# Run integration tests only (requires a running backend)
pytest -m integration
```

Tests use `respx` for HTTP mocking and `pytest-asyncio` for async test support. Integration tests are marked with the `integration` marker and require a running Sattabase backend.

---

## Development

### Project Structure

```
sdk/python/
  pyproject.toml              # Build config (hatch), dependencies, tool settings
  sattabase_sdk/
    __init__.py               # Public API exports + version
    config.py                 # SattabaseConfig frozen dataclass
    client.py                 # SattabaseClient — async HTTP client + auto-refresh
    auth.py                   # AuthModule — login, register, me, refresh, verify, etc.
    access.py                 # AccessModule — cached feature gating helpers
    redirect.py               # BillingRedirectModule — URL constructors
    middleware.py             # Django middleware (sync + async support)
    token_store.py            # TokenStore + TokenStoreWithLookup protocols + stores
    models.py                 # Pydantic v2 models (TokenPair, User, SubscriptionInfo, etc.)
    exceptions.py             # Typed exception hierarchy + build_error mapper
    py.typed                  # PEP 561 marker
  tests/
    __init__.py               # Package marker
    conftest.py               # Shared fixtures
    test_auth.py              # Auth module tests
    test_access.py            # Access module tests
    test_client.py            # Client request + error mapping tests
    test_config.py            # Config validation + error builder tests
    test_models.py            # Model helper method tests
    test_redirect.py          # Billing URL constructor tests
    test_middleware.py        # Django middleware tests
    test_token_store.py       # Token store protocol + implementation tests
    test_integration.py       # Integration tests (marked with `integration` marker)
```

### Toolchain

| Tool | Purpose |
|---|---|
| [hatch](https://hatch.pypa.io/) | Build backend |
| [ruff](https://docs.astral.sh/ruff/) | Linting + formatting (E, F, I, N, W, UP rules) |
| [mypy](https://mypy.readthedocs.io/) | Strict type checking |
| [pytest](https://docs.pytest.org/) + [pytest-asyncio](https://pytest-asyncio.readthedocs.io/) | Testing |
| [respx](https://lundberg.github.io/respx/) | HTTP mocking for httpx |
| [httpx](https://www.python-httpx.org/) | Async HTTP client |
| [pydantic](https://docs.pydantic.dev/) | Data validation and serialization |

```bash
# Lint
ruff check sattabase_sdk/

# Type check
mypy sattabase_sdk/
```

---

## Architecture Overview

```
+-------------------+         SDK Scope          +-------------------+
|                   |  (Auth + Permissions)      |                   |
|  Sister Domain    | <========================> |    Sattabase      |
|  (finance app)    |                            |   (this platform) |
|                   |                            |                   |
|  - Django/FastAPI |   X-API-Key               |  - Django Ninja   |
|  - Own database   |   X-Service-Domain        |  - Stripe         |
|  - Uses user.id   |   Authorization: Bearer    |  - User records   |
|    as foreign key |                            |  - Subscriptions  |
+-------------------+                            +-------------------+
        |                                                |
        |  billing_updated=1                              |  Stripe
        |  (redirect back)                                |  (payments)
        +<-----------------------------------------------+
```

**Key principles:**

- **SDK surface is small and stable** — auth schemas rarely change, while billing schemas change often. This keeps the SDK version-pinned and reliable.
- **Each sister domain has its own database** — the SDK provides only the identity layer (who is this user?) and permission layer (what can they do?). The sister domain uses `user.id` as a foreign key for its own data models.
- **Billing is never proxied** — for subscription management, plan changes, and cancellations, the SDK generates redirect URLs to Sattabase. Stripe is the single source of truth for all payment state.
- **Auto-refresh is built-in** — when enabled, the SDK automatically handles token refresh on 401 responses using an async lock to prevent race conditions.
- **Graceful degradation** — the middleware never crashes your app. On Sattabase failures, it sets all request attributes to `None`.

## License

MIT
