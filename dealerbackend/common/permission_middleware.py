"""
DEALERCORE v3.0 — Permission Middleware
----------------------------------------
Extracts user role from JWT and injects permission context.

FIX DSR-001: This middleware now handles TWO types of JWT tokens:
1. SattaBase JWT (RS256/HS256) — for dealers logging in via SattaBase
2. Local DSR JWT (HS256 with SECRET_KEY) — for DSRs logging in directly

When a SattaBase JWT fails verification, the middleware falls back to
trying the local DSR JWT verification. If a DSR JWT is detected, it
extracts the DSR's user_id and email from the token claims and sets
the appropriate request attributes for downstream controllers.

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
    
    FIX DSR-001: Now handles both SattaBase JWTs and local DSR JWTs.
    
    Adds to request:
    - request.user_role: Role enum
    - request.is_dealer: Boolean
    - request.permissions: List[Permission]
    - request.permission_checker: PermissionChecker instance
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
        request.permissions = get_role_permissions(role) if role else []
        request.permission_checker = PermissionChecker(role=role, is_dealer=is_dealer)
        request.dealer_username = effective_dealer  # For dealer context scoping
        request.user_email = email  # For DSR/invitation matching
        request.selected_dealer = selected_dealer  # The explicitly selected dealer (for validation)
        
        response = self.get_response(request)
        return response
    
    def _extract_user_info(self, request: HttpRequest) -> tuple[Optional[Role], bool, Optional[str], Optional[str], bool, Optional[str]]:
        """
        Extract user role and identity from JWT token.
        
        FIX DSR-001: Attempts SattaBase JWT verification first, then falls
        back to local DSR JWT verification. This unifies the two auth paths
        at the middleware level.
        
        Returns: (role, is_dealer, username, email, is_dsr, dsr_user_id)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return None, False, None, None, False, None
        
        token = auth_header[7:]  # Remove "Bearer "
        
        # ── Step 1: Try SattaBase JWT verification ──────────────────────
        result = self._verify_sattabase_jwt(token, logger)
        if result is not None:
            return result
        
        # ── Step 2: Try local DSR JWT verification ──────────────────────
        result = self._verify_dsr_jwt(token, logger)
        if result is not None:
            return result
        
        # Neither verification succeeded
        return None, False, None, None, False, None

    def _verify_sattabase_jwt(self, token: str, logger) -> Optional[tuple]:
        """
        Verify a SattaBase-issued JWT (RS256 or HS256).
        
        Returns (role, is_dealer, username, email, is_dsr=False, dsr_user_id=None)
        or None if verification fails.
        """
        public_key = getattr(settings, 'SATTABASE_JWT_PUBLIC_KEY', '') or ''
        shared_secret = getattr(settings, 'SATTABASE_JWT_SHARED_SECRET', '') or ''
        
        if public_key:
            verify_key = public_key
            algorithms = [getattr(settings, 'SATTABASE_JWT_ALGORITHM', 'RS256') or 'RS256']
        elif shared_secret:
            verify_key = shared_secret
            algorithms = ['HS256']
        else:
            verify_key = settings.SECRET_KEY
            algorithms = ['HS256']

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
            logger.error(f"[PERMISSION MIDDLEWARE] SattaBase JWT decode unexpected error: {type(e).__name__}: {e}")
            return None
        
        # Extract role from JWT claims
        role_str = payload.get('role', '').lower()
        
        # Extract user identity for dealer context
        dealer_id_from_jwt = (
            payload.get('dealer_id') or 
            payload.get('user_id') or 
            payload.get('username') or 
            payload.get('sub')
        )
        email = payload.get('email')
        
        # Check is_dealer flag from JWT (may not be present)
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
        
        # If is_dealer is not set in JWT, check DealerConfig synchronously.
        if not is_dealer and dealer_id_from_jwt:
            try:
                from dealer.models import DealerConfig
                lookup_value = str(dealer_id_from_jwt)
                is_dealer = DealerConfig.objects.filter(username=lookup_value).exists()
                if is_dealer and not role:
                    role = Role.DEALER
            except Exception:
                pass
        
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
            logger.error(f"[PERMISSION MIDDLEWARE] DSR JWT user lookup failed: {type(e).__name__}: {e}")
            return None


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
