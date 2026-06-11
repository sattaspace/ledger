"""
DEALERCORE v3.0 — DSR Invitation API
-------------------------------------
API endpoints for managing DSR/Collector invitations.

All endpoints require authentication via JWT.
"""

from typing import List, Optional
from ninja_extra import api_controller, http_post, http_get, http_patch, http_delete
from ninja_extra.permissions import IsAuthenticated
from ninja import Schema, Field
from django.shortcuts import get_object_or_404
from django.db import transaction

from dsr.invitation_models import DsrInvitation, DsrDealerAssignment
from dsr.models import DSR
from dealer.models import DealerConfig


# ─── Schemas ───────────────────────────────────────────────────────────────

class CreateInvitationInput(Schema):
    email: str = Field(..., description="Email address of the invited DSR/Collector")
    role: str = Field(default="DSR", description="Role: DSR or Collector")
    parent_dsr_id: Optional[str] = Field(None, description="Parent DSR ID (required for Collectors)")
    message: str = Field(default="", description="Optional message to the invitee")


class InvitationOutput(Schema):
    id: str
    email: str
    role: str
    status: str
    expires_at: str
    created_at: str
    message: str = ""
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: Optional[str] = None


class InvitationDetailOutput(InvitationOutput):
    invite_url: str = ""


class AcceptInvitationInput(Schema):
    token: str = Field(..., description="Invitation token from the email link")


class DsrAssignmentOutput(Schema):
    id: str
    dsr_id: str
    dsr_name: str
    dealer_username: str
    dealer_name: str
    role: str
    is_active: bool
    assigned_at: str
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: Optional[str] = None


# ─── Controller ────────────────────────────────────────────────────────────

@api_controller("/invitations", tags=["DSR Invitations"], permissions=[IsAuthenticated])
class DsrInvitationController:
    """
    Manage DSR/Collector invitations.
    
    Dealers can:
    - Create invitations for DSRs and Collectors
    - View pending invitations
    - Revoke invitations
    - View accepted DSR assignments
    """
    
    @http_post("/create", response=InvitationDetailOutput)
    async def create_invitation(self, request, data: CreateInvitationInput):
        """
        Create a new invitation for a DSR or Collector.
        
        - Validates dealer authentication
        - Checks for existing pending invitation
        - Generates secure token
        - Returns invitation with invite URL
        """
        # Get authenticated dealer from request
        dealer_username = request.user.username
        dealer = await DealerConfig.objects.aget(username=dealer_username)
        
        # Validate parent DSR if collector role
        parent_dsr = None
        if data.role == "Collector" and data.parent_dsr_id:
            try:
                parent_dsr = await DSR.objects.aget(id=data.parent_dsr_id)
            except DSR.DoesNotExist:
                return {"detail": "Parent DSR not found", "code": "parent_dsr_not_found"}, 400
        
        # Check for existing pending invitation
        existing = await DsrInvitation.objects.filter(
            dealer=dealer,
            email=data.email,
            status=DsrInvitation.STATUS_PENDING
        ).afirst()
        
        if existing:
            return {"detail": "Pending invitation already exists", "code": "invitation_exists"}, 409
        
        # Create invitation
        with transaction.atomic():
            invitation = DsrInvitation(
                dealer=dealer,
                email=data.email,
                role=data.role,
                parent_dsr=parent_dsr,
                message=data.message,
            )
            invitation.save()
        
        # Generate invite URL
        # TODO: Configure this based on frontend URL
        invite_url = f"/invitation/{invitation.token}"
        
        # TODO: Send invitation email
        # await send_invitation_email(invitation)
        
        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at.isoformat(),
            "created_at": invitation.created_at.isoformat(),
            "message": invitation.message,
            "parent_dsr_id": invitation.parent_dsr_id if invitation.parent_dsr else None,
            "parent_dsr_name": invitation.parent_dsr.name if invitation.parent_dsr else None,
            "invite_url": invite_url,
        }
    
    @http_get("/list", response=List[InvitationOutput])
    async def list_invitations(
        self,
        request,
        status: Optional[str] = None,
        limit: int = 50
    ):
        """
        List invitations sent by the authenticated dealer.
        
        Query params:
        - status: Filter by status (pending, accepted, expired, revoked)
        - limit: Max results (default 50)
        """
        dealer_username = request.user.username
        dealer = await DealerConfig.objects.aget(username=dealer_username)
        
        queryset = DsrInvitation.objects.filter(dealer=dealer).order_by("-created_at")
        
        if status:
            queryset = queryset.filter(status=status)
        
        invitations = await queryset[:limit].all()
        
        return [
            {
                "id": inv.id,
                "email": inv.email,
                "role": inv.role,
                "status": inv.status,
                "expires_at": inv.expires_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
                "message": inv.message,
                "parent_dsr_id": inv.parent_dsr_id if inv.parent_dsr else None,
                "parent_dsr_name": inv.parent_dsr.name if inv.parent_dsr else None,
            }
            for inv in invitations
        ]
    
    @http_get("/{token}", response=InvitationOutput)
    async def get_invitation(self, request, token: str):
        """
        Public endpoint to validate and view an invitation.
        
        Used by the invitation acceptance page.
        Does not require authentication.
        """
        try:
            invitation = await DsrInvitation.objects.select_related("dealer").aget(token=token)
        except DsrInvitation.DoesNotExist:
            return {"detail": "Invitation not found", "code": "invitation_not_found"}, 404
        
        # Check if expired
        if invitation.is_expired():
            invitation.expire()
            return {"detail": "Invitation has expired", "code": "invitation_expired"}, 410
        
        if invitation.status != DsrInvitation.STATUS_PENDING:
            return {"detail": f"Invitation is {invitation.status}", "code": f"invitation_{invitation.status}"}, 400
        
        return {
            "id": invitation.id,
            "email": invitation.email,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at.isoformat(),
            "created_at": invitation.created_at.isoformat(),
            "message": invitation.message,
            "parent_dsr_id": invitation.parent_dsr_id if invitation.parent_dsr else None,
            "parent_dsr_name": invitation.parent_dsr.name if invitation.parent_dsr else None,
        }
    
    @http_post("/{token}/accept")
    async def accept_invitation(self, request, token: str):
        """
        Accept an invitation.
        
        - Requires authenticated user
        - Links DSR to dealer via DsrDealerAssignment
        - Returns the assignment details
        """
        invitation = await get_object_or_404(DsrInvitation, token=token)
        
        # Check invitation status
        if invitation.is_expired():
            invitation.expire()
            return {"detail": "Invitation has expired", "code": "invitation_expired"}, 410
        
        if invitation.status != DsrInvitation.STATUS_PENDING:
            return {"detail": f"Cannot accept {invitation.status} invitation", "code": "invalid_status"}, 400
        
        # Get or create DSR for the authenticated user
        # NOTE: In Phase 3, we're linking to existing DSR
        # In later phases, we'll create DSR on first invitation
        dealer_username = request.user.username
        
        # TODO: This should be linked to the actual user from SattaBase
        # For now, we'll need to handle this differently
        # We might need to look up DSR by phone/email or create from user profile
        
        try:
            # Try to find existing DSR by email
            dsr = await DSR.objects.aget(phone=invitation.email)  # Using phone as email lookup for now
        except DSR.DoesNotExist:
            # Create new DSR
            # In real implementation, get from SattaBase user profile
            return {"detail": "DSR not found. Please register first.", "code": "dsr_not_found"}, 404
        
        # Check if assignment already exists
        existing = await DsrDealerAssignment.objects.filter(
            dsr=dsr,
            dealer=invitation.dealer
        ).afirst()
        
        if existing:
            return {"detail": "Already assigned to this dealer", "code": "already_assigned"}, 409
        
        # Create the assignment
        with transaction.atomic():
            assignment = DsrDealerAssignment(
                dsr=dsr,
                dealer=invitation.dealer,
                role=invitation.role,
                parent_dsr=invitation.parent_dsr,
                is_active=True,
            )
            assignment.save()
            
            # Mark invitation as accepted
            invitation.accept(dsr)
        
        return {
            "message": "Invitation accepted successfully",
            "assignment": {
                "id": assignment.id,
                "dsr_id": dsr.id,
                "dealer_username": invitation.dealer.username,
                "role": assignment.role,
            }
        }
    
    @http_patch("/{invitation_id}/revoke")
    async def revoke_invitation(self, request, invitation_id: str):
        """
        Revoke a pending invitation.
        
        Only the dealer who sent the invitation can revoke it.
        """
        dealer_username = request.user.username
        
        invitation = await get_object_or_404(
            DsrInvitation,
            id=invitation_id,
            dealer__username=dealer_username
        )
        
        if invitation.status != DsrInvitation.STATUS_PENDING:
            return {"detail": f"Cannot revoke {invitation.status} invitation", "code": "invalid_status"}, 400
        
        invitation.revoke()
        
        return {"message": "Invitation revoked successfully"}
    
    @http_delete("/{invitation_id}")
    async def delete_invitation(self, request, invitation_id: str):
        """
        Delete an invitation (admin only, or own invitations).
        """
        dealer_username = request.user.username
        
        invitation = await get_object_or_404(
            DsrInvitation,
            id=invitation_id,
            dealer__username=dealer_username
        )
        
        await invitation.adelete()
        
        return {"message": "Invitation deleted"}
    
    # ─── DSR Assignments ───────────────────────────────────────────────────
    
    @http_get("/assignments/list", response=List[DsrAssignmentOutput])
    async def list_assignments(
        self,
        request,
        is_active: Optional[bool] = None,
        role: Optional[str] = None
    ):
        """
        List DSR assignments for the authenticated dealer.
        
        Query params:
        - is_active: Filter by active status
        - role: Filter by role (DSR/Collector)
        """
        dealer_username = request.user.username
        
        queryset = DsrDealerAssignment.objects.filter(
            dealer__username=dealer_username
        ).select_related("dsr", "parent_dsr").order_by("-assigned_at")
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        if role:
            queryset = queryset.filter(role=role)
        
        assignments = await queryset.all()
        
        return [
            {
                "id": a.id,
                "dsr_id": a.dsr.id,
                "dsr_name": a.dsr.name,
                "dealer_username": a.dealer.username,
                "dealer_name": a.dealer.full_name,
                "role": a.role,
                "is_active": a.is_active,
                "assigned_at": a.assigned_at.isoformat(),
                "parent_dsr_id": a.parent_dsr_id if a.parent_dsr else None,
                "parent_dsr_name": a.parent_dsr.name if a.parent_dsr else None,
            }
            for a in assignments
        ]
    
    @http_patch("/assignments/{assignment_id}/deactivate")
    async def deactivate_assignment(self, request, assignment_id: str):
        """
        Deactivate a DSR assignment (soft remove from dealer's team).
        """
        dealer_username = request.user.username
        
        assignment = await get_object_or_404(
            DsrDealerAssignment,
            id=assignment_id,
            dealer__username=dealer_username
        )
        
        assignment.deactivate()
        
        return {"message": "Assignment deactivated"}
    
    @http_patch("/assignments/{assignment_id}/activate")
    async def activate_assignment(self, request, assignment_id: str):
        """
        Reactivate a previously deactivated DSR assignment.
        """
        dealer_username = request.user.username
        
        assignment = await get_object_or_404(
            DsrDealerAssignment,
            id=assignment_id,
            dealer__username=dealer_username
        )
        
        assignment.activate()
        
        return {"message": "Assignment activated"}
