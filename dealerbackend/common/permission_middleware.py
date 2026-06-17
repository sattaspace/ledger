"""
DEALERCORE v3.0 — Permission Middleware
----------------------------------------
Extracts user role from JWT and injects permission context.

FIX DSR-001: This middleware now handles TWO types of JWT tokens:
1. SattaBase JWT (RS256) — for dealers logging in via SattaBase
2. Local DSR JWT (HS256 with SECRET_KEY) — for DSRs logging in directly

When a SattaBase JWT fails verification, the middleware falls back to
trying the local DSR JWT verification. If a DSR JWT is detected, it
extracts the DSR's user_id and email from the token claims and sets
the appropriate request attributes for downstream controllers.

Audit A1: Removed SATTABASE_JWT_SHARED_SECRET (HS256 fallback).
SattaBase JWTs are now verified ONLY with RS256 + the public key.
If no public key is configured AND DEBUG=False, SattaBase JWT
verification is skipped entirely (fails closed).
In DEBUG=True mode, the JWT is decoded without signature verification
so user identity can still be extracted — this is insecure but
acceptable for local development.

Dealer Detection (IMPORTANT):
1. Extracts user ID from JWT (dealer_id, user_id, username, or sub claim)
2. First checks JWT's is_dealer claim
3. If not set, checks DealerConfig table synchronously using the user ID
4. This happens in middleware so IsDealerOnly permission works correctly

JWT User ID Priority:
  dealer_id > user_id > username > sub

The DealerConfig check is required because SattaBase JWT may not include
the is_dealer claim, but the IsDealerOnly permission check runs BEFORE
any controller code (including async DealerConfig lookups).
"""

from typing import Optional, Callable
import time
import jwt
from django.http import HttpRequest
from django.conf import settings

from common.permissions import Role


class PermissionMiddleware:
    """
    Middleware to extract user role and permissions from JWT.
    
    FIX DSR-001: Now handles both SattaBase JWTs and local DSR JWTs.
    
    Adds to request:
    - request.user_role: Role enum
    - request.is_dealer: Boolean
    - request.dealer_username: str (from JWT or X-Dealer-Username header for DSRs)
    - request.user_email: str (extracted from JWT 'email' claim)
    - request.selected_dealer: str (X-Dealer-Username header for multi-dealer DSRs)
    - request.is_dsr: Boolean (True if authenticated via local DSR JWT)
    - request.dsr_user_id: str (DsrUser PK from local DSR JWT, if applicable)
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # Extract role from JWT
        role, is_dealer, username, email, is_dsr, dsr_user_id = self._extract_user_info(request)
        
        # Check for X-Dealer-Username header (for multi-dealer DSR context)
        selected_dealer = request.headers.get('X-Dealer-Username')
        
        # Determine effective dealer username:
        # - For dealers: always use their own username (ignore header)
        # - For DSRs/Collectors: use header if provided, otherwise use JWT username
        # FIX: Normalize username to string — JWT user_id may be int (e.g. 1)
        # while X-Dealer-Username is always str (e.g. "1"). Without this,
        # the aget_dealer_from_request anti-spoofing check fails because
        # 1 != "1" in Python.
        if is_dealer:
            effective_dealer = str(username) if username else None
        elif selected_dealer:
            effective_dealer = selected_dealer  # Already a string from HTTP header
        else:
            effective_dealer = str(username) if username else None
        
        # Attach to request
        request.user_role = role
        request.is_dealer = is_dealer
        request.is_dsr = is_dsr  # FIX DSR-001: flag for local DSR JWT
        request.dsr_user_id = dsr_user_id  # FIX DSR-001: DsrUser PK
        request.dealer_username = effective_dealer  # For dealer context scoping
        request.user_email = email  # For DSR/invitation matching
        request.selected_dealer = selected_dealer  # The explicitly selected dealer (for validation)
        
        response = self.get_response(request)
        return response
    
    def _extract_user_info(self, request: HttpRequest) -> tuple[Optional[Role], bool, Optional[str], Optional[str], bool, Optional[str]]:
        """
        Extract user role and identity from JWT token.

        CRITICAL FIX: Try local DSR JWT verification FIRST, then fall back
        to SattaBase JWT verification. This is the correct order because:

        - DSR JWTs are HS256-signed with Django's SECRET_KEY. Verification
          is deterministic — it either succeeds (valid DSR JWT) or fails
          (not a DSR JWT).
        - SattaBase JWTs are RS256-signed. In dev mode without the public
          key, they're decoded WITHOUT signature verification, which means
          ANY JWT (including DSR JWTs) can be decoded here. If we try
          SattaBase first in dev mode, DSR JWTs would be misidentified as
          SattaBase JWTs, bypassing DSR permission checks.

        The previous code tried SattaBase first and used a `token_type`
        claim heuristic to distinguish the two. This was BROKEN because
        SattaBase JWTs (issued via ninja_jwt.tokens.AccessToken.for_user)
        ALSO contain `token_type: "access"` — the same as DSR JWTs. The
        heuristic caused SattaBase JWTs to be bounced to _verify_dsr_jwt,
        which failed HS256 verification, leaving is_dealer=False and
        causing 403 on every dealer-only endpoint (e.g. /api/dealer/dsr).

        Returns: (role, is_dealer, username, email, is_dsr, dsr_user_id)
        """
        import logging
        logger = logging.getLogger(__name__)

        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return None, False, None, None, False, None

        token = auth_header[7:]  # Remove "Bearer "

        # ── Step 1: Try local DSR JWT verification (HS256 with SECRET_KEY) ─
        # This is the strict, deterministic check. If it succeeds, the
        # token is definitely a DSR JWT. If it fails, the token is either
        # a SattaBase JWT or an invalid token.
        result = self._verify_dsr_jwt(token, logger)
        if result is not None:
            logger.debug(
                "[PERMISSION MIDDLEWARE] JWT verified as DSR token "
                "(HS256 with SECRET_KEY succeeded)"
            )
            return result

        # ── Step 2: Try SattaBase JWT verification (RS256 or dev-mode decode) ─
        # If HS256 verification failed, this is either a SattaBase JWT
        # (RS256-signed) or an invalid token. In dev mode without the
        # public key, we decode without verification and rely on the
        # DealerConfig DB lookup to validate the user's identity.
        result = self._verify_sattabase_jwt(token, logger)
        if result is not None:
            logger.debug(
                "[PERMISSION MIDDLEWARE] JWT verified as SattaBase token "
                "(is_dealer=%s, user_id=%s)",
                result[1], result[2],
            )
            return result

        # Neither verification succeeded
        logger.warning(
            "[PERMISSION MIDDLEWARE] JWT verification FAILED for both "
            "DSR (HS256) and SattaBase (RS256/dev-decode) paths. "
            "is_dealer will be False → 403 on permission-checked endpoints."
        )
        return None, False, None, None, False, None

    def _verify_sattabase_jwt(self, token: str, logger) -> Optional[tuple]:
        """
        Verify a SattaBase-issued JWT using RS256 with the public key.
        
        Audit A1: Removed HS256 shared-secret fallback. SattaBase JWTs are
        now verified ONLY with the RS256 public key.
        
        DEVELOPMENT MODE: When SATTABASE_JWT_PUBLIC_KEY is not configured
        AND DEBUG=True, the JWT is decoded WITHOUT signature verification
        so that user identity (user_id, is_dealer) can still be extracted.
        The DealerConfig DB check provides an additional identity validation
        layer. A loud warning is logged every time this path is taken.
        
        In production (DEBUG=False), missing public key → fail closed.
        
        Returns (role, is_dealer, username, email, is_dsr=False, dsr_user_id=None)
        or None if verification fails.
        """
        public_key = getattr(settings, 'SATTABASE_JWT_PUBLIC_KEY', '') or ''
        
        if not public_key:
            # Production: fail closed — no verification possible without public key
            if not getattr(settings, 'DEBUG', False):
                logger.debug(
                    "[PERMISSION MIDDLEWARE] SATTABASE_JWT_PUBLIC_KEY not "
                    "configured and DEBUG=False — skipping SattaBase JWT "
                    "verification. Only local DSR JWTs will be accepted."
                )
                return None
            
            # Development: decode without verification so we can still
            # extract user identity (user_id, email, is_dealer claim).
            # The DealerConfig DB check validates the user is a real
            # dealer. This is NOT secure for production — anyone could
            # forge a JWT with an arbitrary user_id.
            logger.warning(
                "[PERMISSION MIDDLEWARE] SATTABASE_JWT_PUBLIC_KEY not "
                "configured — decoding SattaBase JWT WITHOUT signature "
                "verification (DEBUG=True). THIS IS INSECURE — set "
                "SATTABASE_JWT_PUBLIC_KEY in production!"
            )
            try:
                payload = jwt.decode(
                    token,
                    options={"verify_signature": False},
                    algorithms=["RS256", "HS256"],
                )
            except Exception as e:
                logger.debug(
                    "[PERMISSION MIDDLEWARE] SattaBase JWT decode (no-verify) "
                    "failed: %s: %s", type(e).__name__, e,
                )
                return None
            
            # FIX: The previous code used a `token_type` claim heuristic
            # to distinguish SattaBase JWTs from DSR JWTs. This was BROKEN
            # because BOTH types of JWTs are issued via ninja_jwt and BOTH
            # contain `token_type: "access"`. The heuristic caused SattaBase
            # JWTs to be bounced to _verify_dsr_jwt (which failed HS256
            # verification), leaving is_dealer=False and causing 403 on
            # every dealer-only endpoint (e.g. /api/dealer/dsr — the Team
            # menu).
            #
            # The correct fix is in _extract_user_info: try _verify_dsr_jwt
            # FIRST. If HS256 verification succeeds, it's a DSR JWT. If it
            # fails, the token falls through to here (SattaBase path).
            # By the time we reach this point, we KNOW the token is not a
            # valid DSR JWT, so we can safely treat it as a SattaBase JWT
            # and proceed with claim extraction + DealerConfig lookup.
            
            # Reject expired tokens even in dev mode
            exp = payload.get("exp")
            if exp and exp < time.time():
                logger.debug("[PERMISSION MIDDLEWARE] SattaBase JWT expired")
                return None
            
            return self._extract_sattabase_claims(payload, logger)

        # Production path: verify signature with RS256 public key
        verify_key = public_key
        algorithms = [getattr(settings, 'SATTABASE_JWT_ALGORITHM', 'RS256') or 'RS256']

        decode_kwargs = {
            'algorithms': algorithms,
            'options': {
                'verify_signature': True,
                'require': ['exp'],
            },
        }
        issuer = getattr(settings, 'SATTABASE_JWT_ISSUER', '') or ''
        audience = getattr(settings, 'SATTABASE_JWT_AUDIENCE', '') or ''
        
        if issuer:
            decode_kwargs['issuer'] = issuer
        if audience:
            decode_kwargs['audience'] = audience

        try:
            payload = jwt.decode(token, verify_key, **decode_kwargs)
        except jwt.ExpiredSignatureError:
            logger.debug("[PERMISSION MIDDLEWARE] SattaBase JWT expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.debug(f"[PERMISSION MIDDLEWARE] SattaBase JWT invalid: {e}")
            return None
        except Exception as e:
            logger.error(f"[PERMISSION MIDDLEWARE] SattaBase JWT decode unexpected error: {type(e).__name__}:{e}")
            return None
        
        return self._extract_sattabase_claims(payload, logger)

    def _extract_sattabase_claims(self, payload: dict, logger) -> tuple:
        """Extract role, identity and dealer status from a decoded SattaBase JWT payload.

        Shared between the verified (RS256) and dev-mode (no-verify) decode
        paths so the claim extraction logic stays DRY.

        IMPORTANT — SattaBase JWT architecture:
        SattaBase is a platform-agnostic identity + billing provider. It does
        NOT know about dealer-ness, supplier-ness, or any sister-domain role.
        Standard ninja_jwt AccessTokens contain ONLY:
            - token_type: "access"
            - exp, iat, jti
            - user_id: <SattaBase.User.pk>
        They do NOT contain `is_dealer`, `role`, or `email` claims.

        Therefore, the ONLY way to determine "is this user a dealer in THIS
        sister domain" is to look up our own DealerConfig table using the
        JWT's user_id. The DealerConfig row should have been created by the
        SattaBase→DealerBackend onboarding flow (webhook or signal) when the
        user subscribed to the dealer service plan.

        Convention: DealerConfig.username stores str(SattaBase.User.pk)
        (the column was originally designed for usernames but pivoted to
        user_id without renaming — see worklog "single-source-of-truth-access").
        """
        # Extract role from JWT claims (almost always empty for SattaBase JWTs)
        role_str = payload.get('role', '').lower()

        # Extract user identity for dealer context.
        # Priority: dealer_id > user_id > username > sub
        # For SattaBase JWTs, only `user_id` is present.
        dealer_id_from_jwt = (
            payload.get('dealer_id') or
            payload.get('user_id') or
            payload.get('username') or
            payload.get('sub')
        )
        email = payload.get('email')

        # Check is_dealer flag from JWT (almost always False for SattaBase JWTs)
        is_dealer = payload.get('is_dealer', False)

        # Map to Role enum
        role_map = {
            'dealer': Role.DEALER,
            'dsr': Role.DSR,
            'collector': Role.COLLECTOR,
            'admin': Role.ADMIN,
        }

        role = role_map.get(role_str)

        # If no explicit role but is_dealer, assume DEALER role
        if not role and is_dealer:
            role = Role.DEALER

        # ── CRITICAL: DealerConfig DB lookup ──────────────────────────────
        # This is the ONLY way to establish is_dealer=True for a real
        # SattaBase JWT (which has no is_dealer claim). If this lookup
        # fails silently, the user gets 403 on every dealer-only endpoint
        # (e.g. /api/dealer/dsr — the Team menu) even though they're a
        # legitimate dealer. Endpoints without permission checks (e.g.
        # /api/dsrs — the dashboard) still work, creating the confusing
        # "dashboard works but Team menu 403s" symptom.
        #
        # FIX: previously this had `except: pass` which swallowed ALL
        # errors silently. Now we log every failure path so the root
        # cause is visible in the server logs on the next request.
        if not is_dealer and dealer_id_from_jwt:
            lookup_value = str(dealer_id_from_jwt).strip()
            try:
                from dealer.models import DealerConfig
                is_dealer = DealerConfig.objects.filter(
                    username=lookup_value
                ).exists()
                if is_dealer:
                    if not role:
                        role = Role.DEALER
                    logger.info(
                        "[PERMISSION MIDDLEWARE] DealerConfig lookup "
                        "SUCCEEDED for user_id=%s (lookup_value=%r) — "
                        "is_dealer=True, role=DEALER",
                        dealer_id_from_jwt, lookup_value,
                    )
                else:
                    # This is the smoking gun for the Team-menu-403 bug.
                    # Log loudly so the operator can see exactly what's
                    # happening and fix the onboarding gap.
                    logger.warning(
                        "[PERMISSION MIDDLEWARE] DealerConfig lookup "
                        "returned EMPTY for user_id=%s "
                        "(lookup_value=%r, type=%s). The SattaBase user "
                        "is authenticated but has NO DealerConfig row "
                        "with username=%r. This causes 403 on every "
                        "dealer-only endpoint (e.g. /api/dealer/dsr — "
                        "the Team menu). FIX: either (1) create the "
                        "DealerConfig row manually, or (2) verify the "
                        "SattaBase→DealerBackend onboarding webhook "
                        "fired when this user subscribed to the dealer "
                        "plan. JWT claims present: %s",
                        dealer_id_from_jwt,
                        lookup_value,
                        type(dealer_id_from_jwt).__name__,
                        lookup_value,
                        sorted(payload.keys()),
                    )
            except Exception as e:
                # Database error, ImportError, or anything else — log it
                # loudly instead of swallowing. A silent failure here
                # causes mysterious 403s that are nearly impossible to
                # diagnose.
                logger.error(
                    "[PERMISSION MIDDLEWARE] DealerConfig lookup "
                    "RAISED EXCEPTION for user_id=%s "
                    "(lookup_value=%r): %s: %s. This causes 403 on "
                    "every dealer-only endpoint. The exception was "
                    "previously swallowed by `except: pass` which made "
                    "this bug invisible. JWT claims present: %s",
                    dealer_id_from_jwt,
                    lookup_value,
                    type(e).__name__,
                    e,
                    sorted(payload.keys()),
                    exc_info=True,
                )
        elif not is_dealer and not dealer_id_from_jwt:
            # The JWT has NO user identity claim at all. This means
            # either SattaBase changed its claim names, or someone is
            # sending a malformed token.
            logger.warning(
                "[PERMISSION MIDDLEWARE] SattaBase JWT has NO user "
                "identity claim (checked dealer_id, user_id, username, "
                "sub — all empty). Cannot determine dealer identity. "
                "JWT claims present: %s",
                sorted(payload.keys()),
            )

        return role, is_dealer, dealer_id_from_jwt, email, False, None

    def _verify_dsr_jwt(self, token: str, logger) -> Optional[tuple]:
        """
        Verify a local DSR JWT (HS256 with SECRET_KEY).
        
        FIX DSR-001: This allows DSR tokens issued by auth_api.py to be
        recognized by PermissionMiddleware, unifying the two auth paths.
        
        Returns (role, is_dealer=False, username, email, is_dsr=True, dsr_user_id)
        or None if verification fails.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_signature": True, "require": ["exp"]},
            )
        except jwt.ExpiredSignatureError:
            logger.debug("[PERMISSION MIDDLEWARE] DSR JWT expired")
            return None
        except jwt.InvalidTokenError:
            # Not a valid local JWT either — skip silently
            return None
        
        # Check if this looks like a DSR token (has user_id and token_type=access)
        token_type = payload.get("token_type")
        if token_type is not None and token_type != "access":
            return None  # Refresh tokens must not be used as access tokens
        
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            return None  # Not a DSR token
        
        # Verify the DSR user exists and is active
        try:
            from users.models import DsrUser
            try:
                user = DsrUser.objects.get(id=user_id)
            except DsrUser.DoesNotExist:
                return None
            
            if not user.is_active:
                return None
            
            # FIX H-7: reject tokens issued before last password change
            pwd_changed_at_ts = (
                int(user.password_changed_at.timestamp())
                if user.password_changed_at
                else 0
            )
            token_pwd_ts = payload.get("pwd_changed_at")
            if token_pwd_ts is not None and int(token_pwd_ts) != pwd_changed_at_ts:
                return None
            
            # Determine DSR role from user_type
            role_map = {
                'DSR': Role.DSR,
                'Collector': Role.COLLECTOR,
                'Manager': Role.MANAGER,
                'ADMIN': Role.ADMIN,
            }
            role = role_map.get(user.user_type, Role.DSR)
            
            return role, False, None, user.email, True, str(user.id)
            
        except Exception as e:
            logger.error(f"[PERMISSION MIDDLEWARE] DSR JWT user lookup failed: {type(e).__name__}:{e}")
            return None


# NOTE: The legacy DealerOnlyMiddleware, DSRPlusMiddleware, and
# AsyncPermissionMiddleware classes have been removed — they were never
# registered in settings.MIDDLEWARE and were dead code. Role gating for
# controllers is now done declaratively via the `permissions=[...]`
# argument using the IsJwtAuthenticated / IsDealerOnly / IsDsrOrDealer
# permission classes in `common/permissions.py`.
#
# Audit A2: The dead helper functions check_permission(), require_dealer(),
# and require_dsr_plus() have been removed. They were never imported by any
# controller and were superseded by:
#   - dsr_permissions.enforce_dsr_permission() for module+action checks
#   - IsDealerOnly permission class for dealer-only endpoints
#   - IsDsrOrDealer permission class for shared endpoints
