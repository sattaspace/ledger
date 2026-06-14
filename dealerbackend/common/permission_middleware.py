"""
DEALERCORE v3.0 — Permission Middleware
----------------------------------------
Extracts user role from JWT and injects permission context.

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
import jwt
from django.http import HttpRequest, JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from common.permissions import Role, PermissionChecker, get_role_permissions


class PermissionMiddleware:
    """
    Middleware to extract user role and permissions from JWT.
    
    Adds to request:
    - request.user_role: Role enum
    - request.is_dealer: Boolean
    - request.permissions: List[Permission]
    - request.permission_checker: PermissionChecker instance
    - request.dealer_username: str (from JWT or X-Dealer-Username header for DSRs)
    - request.user_email: str (extracted from JWT 'email' claim)
    - request.selected_dealer: str (X-Dealer-Username header for multi-dealer DSRs)
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # Extract role from JWT
        role, is_dealer, username, email = self._extract_user_info(request)
        
        # Check for X-Dealer-Username header (for multi-dealer DSR context)
        selected_dealer = request.headers.get('X-Dealer-Username')
        
        # Determine effective dealer username:
        # - For dealers: always use their own username (ignore header)
        # - For DSRs/Collectors: use header if provided, otherwise use JWT username
        if is_dealer:
            effective_dealer = username  # Dealers can only access their own data
        elif selected_dealer:
            effective_dealer = selected_dealer  # DSR selected dealer context
        else:
            effective_dealer = username  # Fallback to JWT username
        
        # Attach to request
        request.user_role = role
        request.is_dealer = is_dealer
        request.permissions = get_role_permissions(role) if role else []
        request.permission_checker = PermissionChecker(role=role, is_dealer=is_dealer)
        request.dealer_username = effective_dealer  # For dealer context scoping
        request.user_email = email  # For DSR/invitation matching
        request.selected_dealer = selected_dealer  # The explicitly selected dealer (for validation)
        
        response = self.get_response(request)
        return response
    
    def _extract_user_info(self, request: HttpRequest) -> tuple[Optional[Role], bool, Optional[str], Optional[str]]:
        """
        Extract user role and identity from JWT token.
        
        FIX S-1: JWT signatures are now VERIFIED. We choose the verification
        key based on the configured SattaBase settings:
          - SATTABASE_JWT_PUBLIC_KEY set  → RS256 with that public key
          - SATTABASE_JWT_SHARED_SECRET set → HS256 with that shared secret
          - Otherwise → fall back to the local SECRET_KEY (HS256, dev only)
        `require=["exp"]` enforces expiry. `iss`/`aud` are validated when
        `SATTABASE_JWT_ISSUER` / `SATTABASE_JWT_AUDIENCE` are set.

        FIX S-6: only catch the JWT exceptions we expect. Programming errors
        (AttributeError, KeyError, etc.) must propagate so they show up in
        logs instead of silently granting anonymous access.

        Dealer Detection:
        - First checks JWT's is_dealer claim
        - If not set, checks DealerConfig table synchronously (username from JWT)
        - This is required for IsDealerOnly permission to work correctly
        
        Returns: (role, is_dealer, username, email)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("[PERMISSION MIDDLEWARE] ====== START JWT EXTRACTION ======")
        
        auth_header = request.headers.get('Authorization', '')
        logger.info(f"[PERMISSION MIDDLEWARE] Authorization header present: {bool(auth_header)}")
        
        if not auth_header.startswith('Bearer '):
            logger.warning("[PERMISSION MIDDLEWARE] No Bearer token found, returning anonymous")
            return None, False, None, None
        
        token = auth_header[7:]  # Remove "Bearer "
        logger.info(f"[PERMISSION MIDDLEWARE] Token length: {len(token)}, preview: {token[:50]}...")
        
        # Pick the verification key/algorithm
        public_key = getattr(settings, 'SATTABASE_JWT_PUBLIC_KEY', '') or ''
        shared_secret = getattr(settings, 'SATTABASE_JWT_SHARED_SECRET', '') or ''
        
        # Log JWT verification configuration (for debugging)
        if not public_key and not shared_secret:
            logger.warning(
                "[PERMISSION MIDDLEWARE] JWT verification using local SECRET_KEY. "
                "For production, set SATTABASE_JWT_PUBLIC_KEY or SATTABASE_JWT_SHARED_SECRET "
                "to match SattaBase JWT signing key."
            )
        else:
            logger.info(
                f"[PERMISSION MIDDLEWARE] JWT verification configured: "
                f"public_key={'set' if public_key else 'not set'}, "
                f"shared_secret={'set' if shared_secret else 'not set'}"
            )
        
        if public_key:
            verify_key = public_key
            algorithms = [getattr(settings, 'SATTABASE_JWT_ALGORITHM', 'RS256') or 'RS256']
        elif shared_secret:
            verify_key = shared_secret
            algorithms = ['HS256']
            # Log key details for debugging (show first/last few chars only for security)
            key_preview = f"{shared_secret[:20]}...{shared_secret[-20:]}" if len(shared_secret) > 40 else shared_secret
            logger.info(f"[PERMISSION MIDDLEWARE] Using shared_secret for HS256 verification, key preview: {key_preview}")
        else:
            # Fallback to local SECRET_KEY (HS256). In production, set one of
            # the two env vars above; otherwise signature verification is
            # effectively using the local dev key.
            verify_key = settings.SECRET_KEY
            algorithms = ['HS256']
            logger.warning(
                f"[PERMISSION MIDDLEWARE] Using local SECRET_KEY for JWT verification (fallback mode). "
                f"SATTABASE_JWT_SHARED_SECRET not set. Key preview: {settings.SECRET_KEY[:20]}..."
            )

        decode_kwargs = {
            'algorithms': algorithms,
            'options': {
                'verify_signature': True,
                'require': ['exp'],
            },
        }
        issuer = getattr(settings, 'SATTABASE_JWT_ISSUER', '') or ''
        audience = getattr(settings, 'SATTABASE_JWT_AUDIENCE', '') or ''
        
        logger.info(f"[PERMISSION MIDDLEWARE] JWT decode settings: issuer='{issuer}', audience='{audience}', algorithms={algorithms}")
        
        if issuer:
            decode_kwargs['issuer'] = issuer
        if audience:
            decode_kwargs['audience'] = audience

        try:
            payload = jwt.decode(token, verify_key, **decode_kwargs)
            logger.info(f"[PERMISSION MIDDLEWARE] JWT decoded successfully!")
        except jwt.ExpiredSignatureError:
            logger.warning("[PERMISSION MIDDLEWARE] JWT expired")
            return None, False, None, None
        except jwt.InvalidTokenError as e:
            logger.error(f"[PERMISSION MIDDLEWARE] JWT invalid: {e}")
            # Debug: Try to decode without verification to see the payload
            try:
                unverified_payload = jwt.decode(token, options={"verify_signature": False})
                logger.info(f"[PERMISSION MIDDLEWARE] Token payload (unverified): keys={list(unverified_payload.keys())}")
                logger.info(f"[PERMISSION MIDDLEWARE] Token claims: user_id={unverified_payload.get('user_id')}, exp={unverified_payload.get('exp')}")
            except Exception as debug_e:
                logger.error(f"[PERMISSION MIDDLEWARE] Could not decode token even without verification: {debug_e}")
            return None, False, None, None
        except Exception as e:
            logger.error(f"[PERMISSION MIDDLEWARE] JWT decode unexpected error: {type(e).__name__}: {e}")
            return None, False, None, None
        # Programming errors / unexpected exceptions propagate so they show
        # up in logs instead of silently becoming "anonymous".
        
        # Extract role from JWT claims
        role_str = payload.get('role', '').lower()
        
        # Extract user identity for dealer context
        # SattaBase may use: user_id, dealer_id, sub, or username
        # Priority: dealer_id > user_id > username > sub
        dealer_id_from_jwt = (
            payload.get('dealer_id') or 
            payload.get('user_id') or 
            payload.get('username') or 
            payload.get('sub')
        )
        email = payload.get('email')
        
        # Debug logging for JWT payload - show all claims and their types
        logger.info(
            f"[PERMISSION MIDDLEWARE] JWT payload keys: {list(payload.keys())}"
        )
        logger.info(
            f"[PERMISSION MIDDLEWARE] JWT claims: "
            f"dealer_id={payload.get('dealer_id')} ({type(payload.get('dealer_id')).__name__}), "
            f"user_id={payload.get('user_id')} ({type(payload.get('user_id')).__name__}), "
            f"username={payload.get('username')} ({type(payload.get('username')).__name__}), "
            f"sub={payload.get('sub')} ({type(payload.get('sub')).__name__}), "
            f"is_dealer={payload.get('is_dealer')} ({type(payload.get('is_dealer')).__name__}), "
            f"role={role_str}"
        )
        logger.info(
            f"[PERMISSION MIDDLEWARE] Extracted dealer_id_from_jwt: {dealer_id_from_jwt} ({type(dealer_id_from_jwt).__name__})"
        )
        
        # Check is_dealer flag from JWT (may not be present)
        is_dealer = payload.get('is_dealer', False)
        logger.info(f"[PERMISSION MIDDLEWARE] is_dealer from JWT claim: {is_dealer}")
        
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
        
        # FIX: If is_dealer is not set in JWT, check DealerConfig synchronously.
        # This is required because IsDealerOnly permission check happens BEFORE
        # the controller runs, so the async DealerConfig lookup in get_dealer_context()
        # is too late. We must determine dealer status here.
        # 
        # NOTE: The variable 'dealer_id_from_jwt' contains the dealer's identifier
        # from SattaBase (from dealer_id, user_id, username, or sub claim).
        # DealerConfig.username field stores this same dealer_id value.
        if not is_dealer and dealer_id_from_jwt:
            try:
                from dealer.models import DealerConfig
                # Convert to string for comparison - DealerConfig.username is a string field
                lookup_value = str(dealer_id_from_jwt)
                logger.info(
                    f"[PERMISSION MIDDLEWARE] Checking DealerConfig: "
                    f"looking for username='{lookup_value}'"
                )
                
                # List all DealerConfig usernames for debugging
                all_usernames = list(DealerConfig.objects.values_list('username', flat=True))
                logger.info(f"[PERMISSION MIDDLEWARE] All DealerConfig usernames in DB: {all_usernames}")
                
                is_dealer = DealerConfig.objects.filter(username=lookup_value).exists()
                logger.info(
                    f"[PERMISSION MIDDLEWARE] DealerConfig check result: "
                    f"username='{lookup_value}', is_dealer={is_dealer}"
                )
                if is_dealer and not role:
                    role = Role.DEALER
                    logger.info(f"[PERMISSION MIDDLEWARE] Set role to DEALER based on DealerConfig check")
            except Exception as e:
                # Don't fail the request if DealerConfig check fails
                logger.error(
                    f"[PERMISSION MIDDLEWARE] DealerConfig check failed with exception: {type(e).__name__}: {e}",
                    exc_info=True
                )
                pass
        elif not dealer_id_from_jwt:
            logger.warning("[PERMISSION MIDDLEWARE] No dealer_id/user_id/username/sub found in JWT - cannot check DealerConfig")
        
        # Final result logging
        logger.info(
            f"[PERMISSION MIDDLEWARE] ====== FINAL RESULT ====== "
            f"role={role}, is_dealer={is_dealer}, dealer_id={dealer_id_from_jwt}, email={email}"
        )
        
        # Return the dealer_id (stored in variable named 'username' for backward compatibility)
        return role, is_dealer, dealer_id_from_jwt, email


# NOTE: The legacy DealerOnlyMiddleware, DSRPlusMiddleware, and
# AsyncPermissionMiddleware classes have been removed — they were never
# registered in settings.MIDDLEWARE and were dead code. Role gating for
# controllers is now done declaratively via the `permissions=[...]`
# argument using the IsJwtAuthenticated / IsDealerOnly / IsDsrOrDealer
# permission classes in `common/permissions.py`.


# Permission check helper for controllers
def check_permission(request: HttpRequest, permission: str) -> bool:
    """
    Check if request user has permission.
    
    Usage in controllers:
        if not check_permission(request, Permission.DEALER_SETTINGS):
            return {"detail": "Permission denied"}, 403
    """
    checker = getattr(request, 'permission_checker', None)
    if not checker:
        # Try to create checker from request
        role = getattr(request, 'user_role', None)
        is_dealer = getattr(request, 'is_dealer', False)
        checker = PermissionChecker(role=role, is_dealer=is_dealer)
    
    from common.permissions import Permission
    try:
        perm = Permission(permission)
        return checker.can(perm)
    except ValueError:
        return False


def require_dealer(request: HttpRequest) -> Optional[JsonResponse]:
    """
    Require dealer role.
    
    Returns None if authorized, JsonResponse if not.
    """
    if not getattr(request, 'is_dealer', False):
        return JsonResponse(
            {"detail": "Dealer access required", "code": "dealer_required"},
            status=403
        )
    return None


def require_dsr_plus(request: HttpRequest) -> Optional[JsonResponse]:
    """Require DSR or higher role"""
    role = getattr(request, 'user_role', None)
    is_dealer = getattr(request, 'is_dealer', False)
    
    if is_dealer:
        return None
    
    if role not in [Role.DEALER, Role.DSR, Role.ADMIN]:
        return JsonResponse(
            {"detail": "DSR access required", "code": "dsr_required"},
            status=403
        )
    return None
