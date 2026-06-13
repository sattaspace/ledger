"""
DEALERCORE v3.0 — Dealer DSR Management API
--------------------------------------------
Endpoints for dealers to manage DSRs (invite, remove, update permissions).

Dealer-side operations:
- Invite DSR by phone/email
- List DSRs (active, pending, removed)
- Update DSR permissions
- Remove DSR from team
- Revoke pending invitations
"""

import secrets
from datetime import timedelta
from typing import Optional

from ninja_extra import api_controller, route, http_post, http_get, http_put, http_delete
from ninja_extra.permissions import AllowAny
from ninja import Schema
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.conf import settings

from users.models import DsrUser
from dsr.models import DSR
from dsr.invitation_models import DsrInvitation, DsrDealerAssignment, DEFAULT_PERMISSIONS
from dealer.models import DealerConfig
from dsr.auth_schemas import (
    DealerInviteDsrInput,
    DealerInviteOutput,
    DealerDsrListOutput,
    RemoveDsrInput,
    UpdateDsrPermissionsInput,
    MessageOutput,
)
from common.dealer_context import get_dealer_context


def get_dealer_from_request(request: HttpRequest) -> Optional[DealerConfig]:
    """Get dealer from request context."""
    dealer_username = request.headers.get("X-Dealer-Username")
    if not dealer_username:
        return None
    
    try:
        return DealerConfig.objects.get(username=dealer_username)
    except DealerConfig.DoesNotExist:
        return None


async def aget_dealer_from_request(request: HttpRequest) -> Optional[DealerConfig]:
    """Async version of get_dealer_from_request."""
    dealer_username = request.headers.get("X-Dealer-Username")
    if not dealer_username:
        return None
    
    try:
        return await DealerConfig.objects.aget(username=dealer_username)
    except DealerConfig.DoesNotExist:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# DEALER DSR MANAGEMENT CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

@api_controller("/dealer/dsr", tags=["Dealer DSR Management"], permissions=[AllowAny])
class DealerDsrController:
    """
    Dealer DSR Management endpoints.
    
    Dealers can:
    - Invite DSRs by phone/email
    - View all DSR assignments
    - Update DSR permissions
    - Remove DSRs from their team
    """
    
    @http_post("/invite", response={200: DealerInviteOutput, 400: dict})
    async def invite_dsr(self, request: HttpRequest, data: DealerInviteDsrInput):
        """
        Invite a DSR to join the dealer's team.
        
        If DSR is not registered:
        - Creates pending invitation
        - Returns registration URL with token
        
        If DSR is registered:
        - Creates pending invitation linked to existing DSR
        - DSR will see it in their invitation list
        """
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        # Check for existing pending invitation
        existing = await DsrInvitation.objects.filter(
            dealer=dealer,
            dsr_phone=data.dsr_phone,
            status=DsrInvitation.STATUS_PENDING,
        ).aexists()
        
        if existing:
            return 400, {
                "detail": "Pending invitation already exists for this phone number",
                "code": "invitation_exists"
            }
        
        # Check if DSR already exists (registered)
        existing_user = await DsrUser.objects.filter(phone=data.dsr_phone).aexists()
        dsr_profile = None
        
        if existing_user:
            # Get DSR profile
            try:
                dsr_profile = await DSR.objects.aget(user__phone=data.dsr_phone)
            except DSR.DoesNotExist:
                pass
        
        # Check if already assigned to this dealer
        if dsr_profile:
            existing_assignment = await DsrDealerAssignment.objects.filter(
                dsr=dsr_profile,
                dealer=dealer,
            ).aexists()
            
            if existing_assignment:
                return 400, {
                    "detail": "DSR is already assigned to your team",
                    "code": "already_assigned"
                }
        
        # Create invitation
        invitation_id = f"INV-{dealer.username}-{data.dsr_phone[-4:]}-{secrets.token_hex(4)}"
        
        # Set permissions
        permissions = data.permissions
        if not permissions and data.role in DEFAULT_PERMISSIONS:
            permissions = DEFAULT_PERMISSIONS[data.role].copy()
        
        invitation = await DsrInvitation.objects.acreate(
            id=invitation_id,
            dealer=dealer,
            dsr_phone=data.dsr_phone,
            dsr_email=data.dsr_email or "",
            dsr=dsr_profile,
            role=data.role,
            permissions=permissions or {},
            parent_dsr_id=data.parent_dsr_id,
            message=data.message or "",
        )
        
        # Generate registration URL if DSR not registered
        registration_url = None
        if not existing_user:
            # TODO: Use actual frontend URL from settings
            frontend_url = getattr(settings, 'DEALER_FRONTEND_URL', 'http://localhost:4323')
            registration_url = f"{frontend_url}/dsr/register/{invitation.token}"
            
            # TODO: Send SMS with registration link
            # send_sms(data.dsr_phone, f"You've been invited to join {dealer.full_name}...")
        
        else:
            # TODO: Send notification to existing DSR
            # They'll see it in their invitation list when they log in
            pass
        
        return {
            "id": invitation.id,
            "dsr_phone": invitation.dsr_phone,
            "dsr_email": invitation.dsr_email,
            "role": invitation.role,
            "status": invitation.status,
            "token": invitation.token,
            "expires_at": invitation.expires_at,
            "registration_url": registration_url,
            "message": "Invitation sent" if existing_user else "Registration link generated",
        }
    
    @http_get("/invitations", response={200: dict})
    async def list_invitations(self, request: HttpRequest):
        """List all invitations sent by the dealer."""
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        invitations = []
        async for inv in DsrInvitation.objects.filter(
            dealer=dealer
        ).order_by("-created_at"):
            invitations.append({
                "id": inv.id,
                "dsr_phone": inv.dsr_phone,
                "dsr_email": inv.dsr_email,
                "role": inv.role,
                "status": inv.status,
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
                "accepted_at": inv.accepted_at,
            })
        
        return {"invitations": invitations}
    
    @http_delete("/invitations/{invitation_id}", response={200: MessageOutput, 404: dict})
    async def revoke_invitation(self, request: HttpRequest, invitation_id: str):
        """Revoke a pending invitation."""
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        try:
            invitation = await DsrInvitation.objects.aget(
                id=invitation_id,
                dealer=dealer,
                status=DsrInvitation.STATUS_PENDING,
            )
        except DsrInvitation.DoesNotExist:
            return 404, {"detail": "Invitation not found", "code": "not_found"}
        
        invitation.revoke()
        await invitation.asave()
        
        return {"message": "Invitation revoked"}
    
    @http_get("", response={200: DealerDsrListOutput})
    async def list_dsrs(self, request: HttpRequest):
        """List all DSRs for the dealer (active, pending invitations, removed)."""
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        # Active DSRs
        active = []
        async for assignment in DsrDealerAssignment.objects.filter(
            dealer=dealer,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related("dsr"):
            active.append({
                "id": assignment.id,
                "dsr_id": assignment.dsr.id,
                "dsr_name": assignment.dsr.name,
                "dsr_phone": assignment.dsr.phone,
                "dsr_email": assignment.dsr.email,
                "role": assignment.role,
                "permissions": assignment.permissions,
                "assigned_at": assignment.assigned_at,
                "commission_rate": float(assignment.commission_rate) if assignment.commission_rate else None,
                "has_account": assignment.dsr.has_account,
            })
        
        # Pending invitations
        pending_invitations = []
        async for inv in DsrInvitation.objects.filter(
            dealer=dealer,
            status=DsrInvitation.STATUS_PENDING,
        ):
            pending_invitations.append({
                "id": inv.id,
                "dsr_phone": inv.dsr_phone,
                "dsr_email": inv.dsr_email,
                "role": inv.role,
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
            })
        
        # Removed DSRs
        removed = []
        async for assignment in DsrDealerAssignment.objects.filter(
            dealer=dealer,
            status=DsrDealerAssignment.STATUS_REMOVED,
        ).select_related("dsr"):
            removed.append({
                "id": assignment.id,
                "dsr_id": assignment.dsr.id,
                "dsr_name": assignment.dsr.name,
                "role": assignment.role,
                "removed_at": assignment.removed_at,
                "removal_reason": assignment.removal_reason,
            })
        
        return {
            "active": active,
            "pending_invitations": pending_invitations,
            "removed": removed,
        }
    
    @http_put("/assignments/{assignment_id}", response={200: dict, 404: dict})
    async def update_dsr(self, request: HttpRequest, assignment_id: str, data: UpdateDsrPermissionsInput):
        """Update DSR permissions/role."""
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        try:
            assignment = await DsrDealerAssignment.objects.aget(
                id=assignment_id,
                dealer=dealer,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            )
        except DsrDealerAssignment.DoesNotExist:
            return 404, {"detail": "Assignment not found", "code": "not_found"}
        
        # Update fields
        if data.role is not None:
            assignment.role = data.role
            # Update permissions based on new role if not explicitly provided
            if data.permissions is None and data.role in DEFAULT_PERMISSIONS:
                assignment.permissions = DEFAULT_PERMISSIONS[data.role].copy()
        
        if data.permissions is not None:
            assignment.permissions = data.permissions
        
        if data.commission_rate is not None:
            assignment.commission_rate = data.commission_rate
        
        await assignment.asave()
        
        return {
            "id": assignment.id,
            "role": assignment.role,
            "permissions": assignment.permissions,
            "commission_rate": float(assignment.commission_rate) if assignment.commission_rate else None,
            "message": "DSR updated successfully",
        }
    
    @http_delete("/assignments/{assignment_id}", response={200: MessageOutput, 404: dict})
    async def remove_dsr(self, request: HttpRequest, assignment_id: str, data: RemoveDsrInput = None):
        """
        Remove DSR from dealer's team.
        
        Transaction records are preserved with DSR name snapshot.
        DSR will be notified of removal.
        """
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        try:
            assignment = await DsrDealerAssignment.objects.aget(
                id=assignment_id,
                dealer=dealer,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            )
        except DsrDealerAssignment.DoesNotExist:
            return 404, {"detail": "Assignment not found or not active", "code": "not_found"}
        
        # Preserve transaction records with DSR name snapshot
        # Update SaleRecord to mark DSR status as 'removed'
        from sales.models import SaleRecord
        dsr = assignment.dsr
        
        # Update current DSR sales to show removed status
        await SaleRecord.objects.filter(
            dsr=dsr,
            dealer=dealer
        ).aupdate(dsr_status='removed')
        
        # Update original DSR sales to show removed status
        await SaleRecord.objects.filter(
            original_dsr=dsr,
            dealer=dealer
        ).aupdate(original_dsr_status='removed')
        
        # Deactivate assignment (dealer removing)
        reason = data.reason if data else None
        assignment.deactivate_by_dealer(reason or "")
        await assignment.asave()
        
        # TODO: Notify DSR about removal
        
        return {"message": f"DSR {assignment.dsr.name} removed from team"}
    
    @http_get("/search", response={200: dict})
    async def search_dsr(self, request: HttpRequest, phone: str = ""):
        """
        Search for existing DSR by phone number.
        
        Used in AddRepModal to check if DSR already has an account.
        """
        if not phone:
            return {"exists": False}
        
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        # Check if DSR user exists
        try:
            user = await DsrUser.objects.aget(phone=phone)
            dsr = await DSR.objects.aget(user=user)
            
            # Check if already assigned to this dealer
            is_assigned = await DsrDealerAssignment.objects.filter(
                dsr=dsr,
                dealer=dealer,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).aexists()
            
            return {
                "exists": True,
                "registered": True,
                "dsr_id": dsr.id,
                "dsr_name": dsr.name,
                "dsr_phone": dsr.phone,
                "already_assigned": is_assigned,
            }
        except (DsrUser.DoesNotExist, DSR.DoesNotExist):
            pass
        
        # Check if there's a pending invitation
        pending_inv = await DsrInvitation.objects.filter(
            dsr_phone=phone,
            dealer=dealer,
            status=DsrInvitation.STATUS_PENDING,
        ).afirst()
        
        if pending_inv:
            return {
                "exists": False,
                "registered": False,
                "has_pending_invitation": True,
                "invitation_id": pending_inv.id,
            }
        
        return {
            "exists": False,
            "registered": False,
            "has_pending_invitation": False,
        }
