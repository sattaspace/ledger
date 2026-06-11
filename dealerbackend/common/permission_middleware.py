"""
DEALERCORE v3.0 — Permission Middleware
----------------------------------------
Extracts user role from JWT and injects permission context.
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
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        # Extract role from JWT
        role, is_dealer = self._extract_user_info(request)
        
        # Attach to request
        request.user_role = role
        request.is_dealer = is_dealer
        request.permissions = get_role_permissions(role) if role else []
        request.permission_checker = PermissionChecker(role=role, is_dealer=is_dealer)
        
        response = self.get_response(request)
        return response
    
    def _extract_user_info(self, request: HttpRequest) -> tuple[Optional[Role], bool]:
        """
        Extract user role from JWT token.
        
        Returns: (role, is_dealer)
        """
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None, False
        
        token = auth_header[7:]  # Remove "Bearer "
        
        try:
            # Decode JWT without verification (SattaBase verifies it)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            # Extract role from JWT claims
            # SattaBase might store this in different ways
            role_str = payload.get('role', '').lower()
            is_dealer = payload.get('is_dealer', False)
            
            # Map to Role enum
            role_map = {
                'dealer': Role.DEALER,
                'dsr': Role.DSR,
                'collector': Role.COLLECTOR,
                'admin': Role.ADMIN,
            }
            
            role = role_map.get(role_str)
            
            # If no explicit role but is_dealer flag, assume DEALER
            if not role and is_dealer:
                role = Role.DEALER
            
            return role, is_dealer
            
        except jwt.InvalidTokenError:
            return None, False
        except Exception:
            return None, False


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
        role, is_dealer = self._extract_user_info(request)
        
        request.user_role = role
        request.is_dealer = is_dealer
        request.permissions = get_role_permissions(role) if role else []
        request.permission_checker = PermissionChecker(role=role, is_dealer=is_dealer)
        
        response = await call_next(request)
        return response
    
    def _extract_user_info(self, request: HttpRequest) -> tuple[Optional[Role], bool]:
        """Extract user role from JWT"""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None, False
        
        token = auth_header[7:]
        
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            role_str = payload.get('role', '').lower()
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
            
            return role, is_dealer
            
        except Exception:
            return None, False


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
