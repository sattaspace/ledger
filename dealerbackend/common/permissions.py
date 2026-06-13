"""
DEALERCORE v3.0 — Permission System
------------------------------------
Role-based access control for dealer, DSR, and collector roles.
"""

from enum import Enum
from typing import List, Optional
from functools import wraps


class Role(str, Enum):
    """User roles in the system"""
    DEALER = "dealer"
    DSR = "dsr"
    # FIX H-14: invitation_models.py supports Senior_DSR and Manager roles
    # but the permission checker didn't know them — invitation-accepted users
    # with those roles were silently locked out of every permission check.
    SENIOR_DSR = "senior_dsr"
    MANAGER = "manager"
    COLLECTOR = "collector"
    ADMIN = "admin"


class Permission(str, Enum):
    """Available permissions"""
    # Dealer permissions
    DEALER_FULL_ACCESS = "dealer.full_access"
    DEALER_SETTINGS = "dealer.settings"
    DEALER_BILLING = "dealer.billing"
    DEALER_REPORTS = "dealer.reports"
    DEALER_INVITE_DSR = "dealer.invite_dsr"
    
    # DSR permissions
    DSR_SALES_CREATE = "dsr.sales_create"
    DSR_SALES_VIEW = "dsr.sales_view"
    DSR_INVENTORY_VIEW = "dsr.inventory_view"
    DSR_CUSTOMERS_VIEW = "dsr.customers_view"
    DSR_COLLECTIONS_VIEW = "dsr.collections_view"
    
    # Collector permissions
    COLLECTOR_ORDER_ENTRY = "collector.order_entry"
    COLLECTOR_SALES_CREATE = "collector.sales_create"
    COLLECTOR_CUSTOMERS_VIEW = "collector.customers_view"
    
    # Shared permissions
    VIEW_DASHBOARD = "view.dashboard"
    VIEW_INVENTORY = "view.inventory"
    VIEW_SALES = "view.sales"
    VIEW_REPORTS = "view.reports"
    VIEW_COLLECTIONS = "view.collections"


# Role-to-permissions mapping
ROLE_PERMISSIONS = {
    Role.DEALER: [
        Permission.DEALER_FULL_ACCESS,
        Permission.DEALER_SETTINGS,
        Permission.DEALER_BILLING,
        Permission.DEALER_REPORTS,
        Permission.DEALER_INVITE_DSR,
        Permission.DSR_SALES_CREATE,
        Permission.DSR_SALES_VIEW,
        Permission.DSR_INVENTORY_VIEW,
        Permission.DSR_CUSTOMERS_VIEW,
        Permission.DSR_COLLECTIONS_VIEW,
        Permission.COLLECTOR_ORDER_ENTRY,
        Permission.COLLECTOR_SALES_CREATE,
        Permission.COLLECTOR_CUSTOMERS_VIEW,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_INVENTORY,
        Permission.VIEW_SALES,
        Permission.VIEW_REPORTS,
        Permission.VIEW_COLLECTIONS,
    ],
    Role.DSR: [
        Permission.DSR_SALES_CREATE,
        Permission.DSR_SALES_VIEW,
        Permission.DSR_INVENTORY_VIEW,
        Permission.DSR_CUSTOMERS_VIEW,
        Permission.DSR_COLLECTIONS_VIEW,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_INVENTORY,
        Permission.VIEW_SALES,
        Permission.VIEW_COLLECTIONS,
    ],
    Role.COLLECTOR: [
        Permission.COLLECTOR_ORDER_ENTRY,
        Permission.COLLECTOR_SALES_CREATE,
        Permission.COLLECTOR_CUSTOMERS_VIEW,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_SALES,
    ],
    # FIX H-14: grant broader permission sets to Senior_DSR and Manager
    # so users invited with these roles actually get the powers the dealer
    # intended (instead of silently being denied everything).
    Role.SENIOR_DSR: [
        Permission.DSR_SALES_CREATE,
        Permission.DSR_SALES_VIEW,
        Permission.DSR_INVENTORY_VIEW,
        Permission.DSR_CUSTOMERS_VIEW,
        Permission.DSR_COLLECTIONS_VIEW,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_INVENTORY,
        Permission.VIEW_SALES,
        Permission.VIEW_REPORTS,
        Permission.VIEW_COLLECTIONS,
    ],
    Role.MANAGER: [
        # Manager gets everything DSR has, plus inventory/suppliers edit
        # and reports export — these are the permissions the DEFAULT_PERMISSIONS
        # in invitation_models.py grant to the Manager role.
        Permission.DSR_SALES_CREATE,
        Permission.DSR_SALES_VIEW,
        Permission.DSR_INVENTORY_VIEW,
        Permission.DSR_CUSTOMERS_VIEW,
        Permission.DSR_COLLECTIONS_VIEW,
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_INVENTORY,
        Permission.VIEW_SALES,
        Permission.VIEW_REPORTS,
        Permission.VIEW_COLLECTIONS,
    ],
    Role.ADMIN: [
        Permission.DEALER_FULL_ACCESS,
    ],
}


def get_role_permissions(role: Role) -> List[Permission]:
    """Get all permissions for a role"""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(role: Role, permission: Permission) -> bool:
    """Check if role has a specific permission"""
    return permission in get_role_permissions(role)


def has_any_permission(role: Role, permissions: List[Permission]) -> bool:
    """Check if role has any of the permissions"""
    role_perms = get_role_permissions(role)
    return any(p in role_perms for p in permissions)


def has_all_permissions(role: Role, permissions: List[Permission]) -> bool:
    """Check if role has all permissions"""
    role_perms = get_role_permissions(role)
    return all(p in role_perms for p in permissions)


class PermissionChecker:
    """Permission checker for request context"""
    
    def __init__(self, role: Optional[Role] = None, is_dealer: bool = False):
        self.role = role
        self.is_dealer = is_dealer
    
    def can(self, permission: Permission) -> bool:
        """Check if user has permission"""
        if self.is_dealer:
            return True  # Dealer has all permissions
        if not self.role:
            return False
        return has_permission(self.role, permission)
    
    def can_any(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the permissions"""
        if self.is_dealer:
            return True
        if not self.role:
            return False
        return has_any_permission(self.role, permissions)
    
    def can_all(self, permissions: List[Permission]) -> bool:
        """Check if user has all permissions"""
        if self.is_dealer:
            return True
        if not self.role:
            return False
        return has_all_permissions(self.role, permissions)


def require_permission(permission: Permission):
    """Decorator to require a specific permission.

    FIX M-3: raise `ninja_extra.exceptions.PermissionDenied` (which the
    Ninja framework converts into a 403 response) instead of the built-in
    `PermissionError`, which the framework treats as an unhandled exception
    and returns as 500.
    """
    # Imported lazily so this module stays importable in non-Ninja contexts.
    from ninja_extra.exceptions import PermissionDenied

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request from args (first arg after self)
            request = args[1] if len(args) > 1 else kwargs.get('request')

            if not request:
                raise PermissionDenied("No request context")

            # Get user role from request
            role = getattr(request, 'user_role', None)
            is_dealer = getattr(request, 'is_dealer', False)

            checker = PermissionChecker(role=role, is_dealer=is_dealer)

            if not checker.can(permission):
                raise PermissionDenied(f"Permission denied: {permission}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# Django Ninja Permission Classes
# ═══════════════════════════════════════════════════════════════════════════
# The built-in `IsAuthenticated` permission from ninja_extra checks
# `request.user.is_authenticated`, which always fails in this JWT-only
# system (Django's session auth never runs). Use `IsJwtAuthenticated`
# instead on any controller that requires a valid JWT.

from ninja_extra.permissions import BasePermission


class IsJwtAuthenticated(BasePermission):
    """
    Allow the request only if a valid JWT was processed by PermissionMiddleware.

    PermissionMiddleware sets `request.user_role` (a Role enum) and
    `request.is_dealer` (bool) for any request that carried a parseable JWT.
    If either is present, the user is considered authenticated.
    """

    def has_permission(self, request, controller) -> bool:
        return (
            getattr(request, "user_role", None) is not None
            or getattr(request, "is_dealer", False)
        )


class IsDealerOnly(BasePermission):
    """
    Allow the request only if the JWT subject is a dealer (is_dealer=True).

    Used on dealer-scoped endpoints to prevent DSRs/Collectors from calling
    dealer-only operations (invite DSR, configure dealer settings, etc.).
    """

    def has_permission(self, request, controller) -> bool:
        return bool(getattr(request, "is_dealer", False))


class IsDsrOrDealer(BasePermission):
    """
    Allow the request if the JWT subject is either a DSR/Collector (has a
    user_role) or a Dealer. Used on shared endpoints that both roles hit.
    """

    def has_permission(self, request, controller) -> bool:
        if getattr(request, "is_dealer", False):
            return True
        return getattr(request, "user_role", None) is not None


# Permission groups for common use cases
PERMISSION_GROUPS = {
    "sales": [
        Permission.DSR_SALES_CREATE,
        Permission.COLLECTOR_SALES_CREATE,
        Permission.VIEW_SALES,
    ],
    "inventory": [
        Permission.DSR_INVENTORY_VIEW,
        Permission.VIEW_INVENTORY,
    ],
    "reports": [
        Permission.DEALER_REPORTS,
        Permission.VIEW_REPORTS,
    ],
    "settings": [
        Permission.DEALER_SETTINGS,
    ],
    "billing": [
        Permission.DEALER_BILLING,
    ],
}
