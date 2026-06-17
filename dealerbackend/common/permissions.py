"""
DEALERCORE v3.0 — Permission System
------------------------------------
Role enum and Django Ninja permission classes for JWT-based auth.

Audit A3: Removed dead code that was superseded by dsr_permissions.py's
module+action system (enforce_dsr_permission). The removed items were:
  - Permission enum (18 values) — never used outside this file
  - ROLE_PERMISSIONS dict — only read by PermissionChecker
  - PermissionChecker class — set on request.permission_checker but never
    called by any business API
  - PERMISSION_GROUPS dict — never imported
  - require_permission() decorator — never applied to any endpoint
  - get_role_permissions(), has_permission(), has_any_permissions(),
    has_all_permissions() — only called by the dead PermissionChecker

What remains (alive code):
  - Role enum — used by PermissionMiddleware and dsr_permissions.py
  - IsJwtAuthenticated — used by dealer_dsr_api.py, permissions_api.py
  - IsDealerOnly — used by dealer_dsr_api.py
  - IsDsrOrDealer — used by dealer_dsr_api.py

The actual DSR permission enforcement is in common/dsr_permissions.py,
which checks DsrDealerAssignment.has_permission() + dealer subscription.
"""

from enum import Enum
from typing import Optional

from ninja_extra.permissions import BasePermission


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


# ═══════════════════════════════════════════════════════════════════════════
# Django Ninja Permission Classes
# ═══════════════════════════════════════════════════════════════════════════
# The built-in `IsAuthenticated` permission from ninja_extra checks
# `request.user.is_authenticated`, which always fails in this JWT-only
# system (Django's session auth never runs). Use `IsJwtAuthenticated`
# instead on any controller that requires a valid JWT.


class IsJwtAuthenticated(BasePermission):
    """
    Allow the request only if a valid JWT was processed by PermissionMiddleware.

    PermissionMiddleware sets `request.user_role` (a Role enum) and
    `request.is_dealer` (bool) for any request that carried a parseable JWT.
    If either is present, the user is considered authenticated.
    """

    def has_permission(self, request, controller) -> bool:
        import logging
        logger = logging.getLogger(__name__)
        
        user_role = getattr(request, "user_role", None)
        is_dealer = getattr(request, "is_dealer", False)
        
        logger.info(
            f"[IsJwtAuthenticated] Permission check: "
            f"user_role={user_role}, is_dealer={is_dealer}, "
            f"path={request.path}, method={request.method}"
        )
        
        result = (
            user_role is not None
            or is_dealer
        )
        logger.info(f"[IsJwtAuthenticated] Permission result: {'ALLOWED' if result else 'DENIED'}")
        
        return result


class IsDealerOnly(BasePermission):
    """
    Allow the request only if the JWT subject is a dealer (is_dealer=True).

    Used on dealer-scoped endpoints to prevent DSRs/Collectors from calling
    dealer-only operations (invite DSR, configure dealer settings, etc.).
    """

    def has_permission(self, request, controller) -> bool:
        import logging
        logger = logging.getLogger(__name__)
        
        is_dealer = getattr(request, "is_dealer", False)
        user_role = getattr(request, "user_role", None)
        dealer_username = getattr(request, "dealer_username", None)
        
        logger.info(
            f"[IsDealerOnly] Permission check: "
            f"is_dealer={is_dealer}, user_role={user_role}, dealer_username={dealer_username}, "
            f"path={request.path}, method={request.method}"
        )
        
        result = bool(is_dealer)
        logger.info(f"[IsDealerOnly] Permission result: {'ALLOWED' if result else 'DENIED'}")
        
        return result


class IsDsrOrDealer(BasePermission):
    """
    Allow the request if the JWT subject is either a DSR/Collector (has a
    user_role) or a Dealer. Used on shared endpoints that both roles hit.
    """

    def has_permission(self, request, controller) -> bool:
        if getattr(request, "is_dealer", False):
            return True
        return getattr(request, "user_role", None) is not None
