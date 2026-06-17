"""
DEALERCORE v3.0 — DSR Permissions API
---------------------------------------
Endpoint for DSRs to fetch their per-dealer module permissions.

This is called by the frontend `useDsrPermissions` composable to
determine which modules and actions a DSR can access for the currently
selected dealer.

Architecture
------------
  Frontend (useDsrPermissions.ts)
      │
      ▼
  GET /dsr/permissions
      │
      ▼
  DsrPermissionsController
      │  reads request.dsr_user_id / request.user_email
      │  + request.dealer_username
      ▼
  DsrDealerAssignment.permissions JSON
      │
      ▼
  { is_dealer, role, permissions: { sales: {view: True, edit: True}, ... } }

For dealers: returns is_dealer=True with empty permissions (dealers bypass
all module-level checks on the frontend).

For DSRs/Collectors: returns the permissions from their active
DsrDealerAssignment for the current dealer context.
"""

import logging
from typing import Optional

from ninja_extra import api_controller, route
from ninja import Schema
from django.http import HttpRequest

from common.permissions import IsJwtAuthenticated

logger = logging.getLogger(__name__)


# ─── Schemas ─────────────────────────────────────────────────────────────────


class DsrPermissionsResponse(Schema):
    """Response schema for GET /dsr/permissions."""
    is_dealer: bool = False
    dsr_user_id: Optional[str] = None
    dealer_username: Optional[str] = None
    role: Optional[str] = None
    permissions: dict = {}


# ─── Controller ──────────────────────────────────────────────────────────────


@api_controller("/dsr", tags=["DSR Permissions"], permissions=[IsJwtAuthenticated])
class DsrPermissionsController:
    """Provides DSR module permissions for the current dealer context.

    Called by the frontend useDsrPermissions composable to determine
    which modules and actions a DSR can access.
    """

    @route.get("/permissions", response=DsrPermissionsResponse,
               summary="Get DSR module permissions")
    async def get_permissions(self, request: HttpRequest) -> DsrPermissionsResponse:
        """Return the DSR's module permissions for the current dealer context.

        For dealers: is_dealer=True, empty permissions (dealers bypass checks).
        For DSRs/Collectors: their DsrDealerAssignment.permissions.
        """
        is_dealer = getattr(request, "is_dealer", False)
        dealer_username = getattr(request, "dealer_username", None)

        # For dealers, return immediately with empty permissions
        if is_dealer:
            return DsrPermissionsResponse(
                is_dealer=True,
                dsr_user_id=None,
                dealer_username=dealer_username,
                role="dealer",
                permissions={},
            )

        # For DSRs/Collectors, look up their assignment
        from dsr.invitation_models import DsrDealerAssignment
        from common.dsr_permissions import get_dsr_assignment

        assignment = await get_dsr_assignment(request)

        if assignment is None:
            # No active assignment — return empty (most restrictive)
            logger.info(
                "[DSR_PERM_API] No active assignment for request to %s %s",
                request.method, request.path,
            )
            return DsrPermissionsResponse(
                is_dealer=False,
                dsr_user_id=getattr(request, "dsr_user_id", None),
                dealer_username=dealer_username,
                role=None,
                permissions={},
            )

        return DsrPermissionsResponse(
            is_dealer=False,
            dsr_user_id=str(assignment.dsr_id) if assignment.dsr_id else None,
            dealer_username=str(assignment.dealer_id) if assignment.dealer_id else None,
            role=assignment.role,
            permissions=assignment.get_permissions(),
        )
