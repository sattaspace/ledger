"""
DEALERCORE v3.0 — Permission Middleware
----------------------------------------
Extracts user role from JWT and injects permission context.

IMPORTANT: Dealer detection happens in two stages:
1. Middleware extracts user_id from JWT (fast, no DB call)
2. get_dealer_context() checks if user_id matches DealerConfig (async DB)

This separation allows the async DB check to work properly in Django async views.
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
        
        Note: Dealer detection via DealerConfig is handled asynchronously
        in get_dealer_context() to work properly with Django async views.
        
        Returns: (role, is_dealer, username, email)
        """
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None, False, None, None
        
        token = auth_header[7:]  # Remove "Bearer "
        
        try:
            # Decode JWT without verification (SattaBase verifies it)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Extract role from JWT claims
            role_str = payload.get('role', '').lower()
            
            # Extract user identity for dealer context
            # SattaBase uses user_id (not username)
            username = payload.get('username') or payload.get('sub') or payload.get('user_id')
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
            
            return role, is_dealer, username, email
            
        except jwt.InvalidTokenError:
            return None, False, None, None
        except Exception:
            return None, False, None, None


class DealerOnlyMiddleware:
    """Middleware to restrict endpoints to dealers only"""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        if not getattr(request, 'is_dealer', False):
            return JsonResponse(
                {"detail": "Dealer access required", "code": "dealer_required"},
                status=403
            )
        return self.get_response(request)


class DSRPlusMiddleware:
    """Middleware to restrict endpoints to DSRs and above"""
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        role = getattr(request, 'user_role', None)
        is_dealer = getattr(request, 'is_dealer', False)
        
        if not (is_dealer or role in [Role.DEALER, Role.DSR, Role.ADMIN]):
            return JsonResponse(
                {"detail": "DSR access required", "code": "dsr_required"},
                status=403
            )
        return self.get_response(request)


# Async versions for Django Ninja
class AsyncPermissionMiddleware:
    """Async middleware for permission checking"""
    
    async def __call__(self, request: HttpRequest, call_next):
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
        
        request.user_role = role
        request.is_dealer = is_dealer
        request.permissions = get_role_permissions(role) if role else []
        request.permission_checker = PermissionChecker(role=role, is_dealer=is_dealer)
        request.dealer_username = effective_dealer  # For dealer context scoping
        request.user_email = email  # For DSR/invitation matching
        request.selected_dealer = selected_dealer  # The explicitly selected dealer (for validation)
        
        response = await call_next(request)
        return response
    
    def _extract_user_info(self, request: HttpRequest) -> tuple[Optional[Role], bool, Optional[str], Optional[str]]:
        """Extract user role and identity from JWT.
        
        Note: Dealer detection via DealerConfig is handled asynchronously
        in get_dealer_context() to work properly with Django async views.
        """
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None, False, None, None
        
        token = auth_header[7:]
        
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            role_str = payload.get('role', '').lower()
            
            # Extract user identity (SattaBase uses user_id)
            username = payload.get('username') or payload.get('sub') or payload.get('user_id')
            email = payload.get('email')
            
            # Check is_dealer flag from JWT (may not be present)
            is_dealer = payload.get('is_dealer', False)
            
            role_map = {
                'dealer': Role.DEALER,
                'dsr': Role.DSR,
                'collector': Role.COLLECTOR,
                'admin': Role.ADMIN,
            }
            
            role = role_map.get(role_str)
            if not role and is_dealer:
                role = Role.DEALER
            
            return role, is_dealer, username, email
            
        except Exception:
            return None, False, None, None


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
