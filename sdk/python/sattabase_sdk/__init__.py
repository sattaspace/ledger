"""
sattabase-sdk — Python SDK for Sattabase.

Central auth, subscription, and access control for multi-tenant service domains.

Usage::

    from sattabase_sdk import SattabaseClient, SattabaseConfig

    config = SattabaseConfig(
        base_url="https://sattabase.tld/api/v1",
        service_domain="finance.sattabase.tld",
        api_key="sb_live_...",
    )

    async with SattabaseClient(config) as client:
        tokens = await client.auth.login("user@example.com", "password")
        auth_me = await client.auth.me(tokens.access)
        if auth_me.has_access("reports"):
            print("User has reports access")
"""

__version__ = "0.1.0"

from .client import SattabaseClient
from .config import SattabaseConfig
from .models import (
    AuthMeResponse,
    MessageResponse,
    SubscriptionInfo,
    TokenPair,
    User,
)

# Lazy imports for token store classes (avoids potential circular deps)
from .token_store import InMemoryTokenStore, TokenStore, TokenStoreWithLookup

# Lazy imports for exceptions
from .exceptions import (
    AccountDeletedError,
    AccountInactiveError,
    AccountNotActiveError,
    ApiServerError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    SattabaseError,
    ValidationError,
)

# Lazy import for middleware (Django is an optional dependency)
from .middleware import SattabaseAuthMiddleware

__all__ = [
    # Client
    "SattabaseClient",
    "SattabaseConfig",
    # Models
    "AuthMeResponse",
    "MessageResponse",
    "SubscriptionInfo",
    "TokenPair",
    "User",
    # Token stores
    "TokenStore",
    "TokenStoreWithLookup",
    "InMemoryTokenStore",
    # Exceptions
    "SattabaseError",
    "AuthenticationError",
    "AccountInactiveError",
    "AccountDeletedError",
    "ForbiddenError",
    "AccountNotActiveError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
    "ValidationError",
    "BadRequestError",
    "ApiServerError",
    # Middleware
    "SattabaseAuthMiddleware",
    # Meta
    "__version__",
]
