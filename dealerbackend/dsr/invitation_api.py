"""
DEALERCORE v3.0 - DSR Invitation API
-------------------------------------
API endpoints for managing DSR/Collector invitations.

All endpoints require authentication via JWT.
"""

from typing import List, Optional
import secrets
from ninja_extra import api_controller, http_post, http_get, http_patch, http_delete
from ninja_extra.permissions import IsAuthenticated
from ninja import Schema, Field
from django.db import transaction

from dsr.invitation_models import DsrInvitation, DsrDealerAssignment
from common.rate_limit import rate_limit
from users.models import DsrUser
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
    @rate_limit("dsr_invitation_create", limit=30, period=3600, scope="ip")
    async def create_invitation(self, request, data: CreateInvitationInput):
        """
        Create a new invitation for a DSR or Collector.

        - Validates dealer authentication
        - Checks for existing pending invitation
        - Generates secure token
        - Returns invitation with invite URL
        """
        # Get authenticated dealer from request
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return {"detail": "Authentication required", "code": "auth_required"}, 401
        dealer = await DealerConfig.objects.aget(username=dealer_username)

        # Validate parent DSR if collector role
        parent_dsr = None
        if data.role == "Collector" and data.parent_dsr_id:
            try:
                parent_dsr = await DsrUser.objects.aget(id=data.parent_dsr_id)
            except DsrUser.DoesNotExist:
                return {"detail": "Parent DSR not found", "code": "parent_dsr_not_found"}, 400

        # Check for existing pending invitation
        # FIX S-8: model field is `dsr_email`, not `email`.
        existing = await DsrInvitation.objects.filter(
            dealer=dealer,
            dsr_email=data.email,
            status=DsrInvitation.STATUS_PENDING
        ).afirst()

        if existing:
            return {"detail": "Pending invitation already exists", "code": "invitation_exists"}, 409

        # Create invitation
        # FIX S-9: PK `id` is a CharField with no default - supply one.
        # FIX S-8: field is `dsr_email`.
        # FIX L-9: token stored as hash; raw token only in the email URL.
        invitation_id = f"INV-{dealer.username}-{secrets.token_hex(8)}"
        with transaction.atomic():
            invitation = DsrInvitation(
                id=invitation_id,
                dealer=dealer,
                dsr_email=data.email,
                role=data.role,
                parent_dsr=parent_dsr,
                message=data.message,
            )
            invitation.save()
            # Regenerate the token so we have the raw value for the URL,
            # then store the hash in the DB.
            raw_token = invitation._generate_token()
            invitation.token = DsrInvitation.hash_token(raw_token)
            invitation.save(update_fields=["token", "updated_at"])

        # Generate invite URL (uses the RAW token, not the hash)
        # TODO: Configure this based on frontend URL
        invite_url = f"/invitation/{raw_token}"

        # TODO: Send invitation email
        # await send_invitation_email(invitation)

        return {
            "id": invitation.id,
            "email": invitation.dsr_email,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at.isoformat(),
            "created_at": invitation.created_at.isoformat(),
            "message": invitation.message,
            "parent_dsr_id": str(invitation.parent_dsr_id) if invitation.parent_dsr_id else None,
            "parent_dsr_name": invitation.parent_dsr.full_name if invitation.parent_dsr else None,
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
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return [],  # Return empty list for unauthenticated requests
        dealer = await DealerConfig.objects.aget(username=dealer_username)

        queryset = (
            DsrInvitation.objects
            .filter(dealer=dealer)
            .select_related("parent_dsr")  # FIX M-14: avoid N+1 on parent_dsr lookup
            .order_by("-created_at")
        )

        if status:
            queryset = queryset.filter(status=status)

        # FIX S-10: Django QuerySet is not awaitable and has no `aall()`.
        # Use async iteration with a slice applied to the queryset.
        invitations = []
        async for inv in queryset[:limit]:
            invitations.append(inv)

        return [
            {
                "id": inv.id,
                "email": inv.dsr_email,
                "role": inv.role,
                "status": inv.status,
                "expires_at": inv.expires_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
                "message": inv.message,
                "parent_dsr_id": str(inv.parent_dsr_id) if inv.parent_dsr_id else None,
                "parent_dsr_name": inv.parent_dsr.full_name if inv.parent_dsr else None,
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
            # FIX L-9: look up by hash of the supplied token, not the raw token.
            invitation = await DsrInvitation.objects.select_related("dealer").aget(
                token=DsrInvitation.hash_token(token)
            )
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
            "email": invitation.dsr_email,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at.isoformat(),
            "created_at": invitation.created_at.isoformat(),
            "message": invitation.message,
            "parent_dsr_id": str(invitation.parent_dsr_id) if invitation.parent_dsr_id else None,
            "parent_dsr_name": invitation.parent_dsr.full_name if invitation.parent_dsr else None,
        }

    @http_post("/{token}/accept")
    async def accept_invitation(self, request, token: str):
        """
        Accept an invitation.

        - Requires authenticated user (DSR/Collector from SattaBase)
        - Validates that the authenticated user's email matches invitation email
        - Creates or retrieves DSR record linked to the user
        - Links DSR to dealer via DsrDealerAssignment
        - Returns the assignment details

        Security: Only the invited user (matching email) can accept the invitation.
        """
        # FIX H-19 / L-9: use async-aware lookup by hashed token
        try:
            invitation = await DsrInvitation.objects.select_related("dealer", "parent_dsr").aget(
                token=DsrInvitation.hash_token(token)
            )
        except DsrInvitation.DoesNotExist:
            return {"detail": "Invitation not found", "code": "invitation_not_found"}, 404

        # Check invitation status
        if invitation.is_expired():
            # FIX M-3/H-19: use async save in async view
            await invitation.aexpire()
            return {"detail": "Invitation has expired", "code": "invitation_expired"}, 410

        if invitation.status != DsrInvitation.STATUS_PENDING:
            return {"detail": f"Cannot accept {invitation.status} invitation", "code": "invalid_status"}, 400

        # Get authenticated user's info from JWT (extracted by PermissionMiddleware)
        user_email = getattr(request, 'user_email', None)
        user_username = getattr(request, 'dealer_username', None)  # This is the SattaBase username

        if not user_email:
            return {"detail": "Unable to verify user email. Please re-authenticate.", "code": "email_not_found"}, 401

        # Security: Verify the authenticated user's email matches the invitation email
        # FIX S-8: field is `dsr_email`, not `email`.
        if user_email.lower() != invitation.dsr_email.lower():
            return {
                "detail": f"This invitation was sent to {invitation.dsr_email}, but you are logged in as {user_email}. Please log in with the correct account.",
                "code": "email_mismatch"
            }, 403

        # After DSR→DsrUser merge: DsrUser IS the user now.
        # Look up by email; create only if no DsrUser exists yet.
        # parent_dsr is tracked on DsrDealerAssignment, not on DsrUser.
        dsr_name = invitation.dsr_email.split('@')[0]  # Default name from email

        # Try to find an existing DsrUser with this email
        dsr = await DsrUser.objects.filter(email__iexact=user_email).afirst()
        if dsr is None:
            # Determine user_type from invitation role
            user_type = (
                DsrUser.TYPE_COLLECTOR
                if invitation.role == DsrInvitation.ROLE_COLLECTOR
                else DsrUser.TYPE_DSR
            )
            dsr = await DsrUser.objects.acreate(
                email=user_email,
                full_name=dsr_name,
                phone="",  # Will be updated when user provides phone
                user_type=user_type,
            )

        # Check if assignment already exists
        existing = await DsrDealerAssignment.objects.filter(
            dsr=dsr,
            dealer=invitation.dealer
        ).afirst()

        if existing:
            # If a prior assignment exists but is not active, reactivate it
            if existing.status != DsrDealerAssignment.STATUS_ACTIVE:
                await existing.aactivate()
                await invitation.aaccept(dsr)
                return {
                    "message": "Invitation accepted (reactivated)",
                    "assignment": {
                        "id": existing.id,
                        "dsr_id": str(dsr.id),
                        "dsr_name": dsr.full_name,
                        "dealer_username": invitation.dealer.username,
                        "role": existing.role,
                    }
                }
            return {"detail": "Already assigned to this dealer", "code": "already_assigned"}, 409

        # FIX S-4: model has `status` (and a derived `is_active` property),
        # NOT a settable `is_active` field. Use `status=STATUS_ACTIVE`.
        # FIX M-13: ensure id fits the 100-char PK limit.
        assignment_id = f"assign-{dsr.id}-{invitation.dealer.username}"[:100]
        assignment = await DsrDealerAssignment.objects.acreate(
            id=assignment_id,
            dsr=dsr,
            dealer=invitation.dealer,
            role=invitation.role,
            parent_dsr=invitation.parent_dsr,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        )

        # Mark invitation as accepted (use async version)
        await invitation.aaccept(dsr)

        return {
            "message": "Invitation accepted successfully",
            "assignment": {
                "id": assignment.id,
                "dsr_id": str(dsr.id),
                "dsr_name": dsr.full_name,
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
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return {"detail": "Authentication required", "code": "auth_required"}, 401

        # FIX H-19: use async aget instead of sync get_object_or_404
        try:
            invitation = await DsrInvitation.objects.aget(
                id=invitation_id, dealer__username=dealer_username
            )
        except DsrInvitation.DoesNotExist:
            return {"detail": "Invitation not found", "code": "not_found"}, 404

        if invitation.status != DsrInvitation.STATUS_PENDING:
            return {"detail": f"Cannot revoke {invitation.status} invitation", "code": "invalid_status"}, 400

        # FIX M-4 / H-19: use async revoke
        await invitation.arevoke()

        return {"message": "Invitation revoked successfully"}

    @http_delete("/{invitation_id}")
    async def delete_invitation(self, request, invitation_id: str):
        """
        Delete an invitation (admin only, or own invitations).
        """
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return {"detail": "Authentication required", "code": "auth_required"}, 401

        # FIX H-19: async get
        try:
            invitation = await DsrInvitation.objects.aget(
                id=invitation_id, dealer__username=dealer_username
            )
        except DsrInvitation.DoesNotExist:
            return {"detail": "Invitation not found", "code": "not_found"}, 404

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
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return [],  # Return empty list for unauthenticated requests

        queryset = DsrDealerAssignment.objects.filter(
            dealer__username=dealer_username
        ).select_related("dsr", "parent_dsr").order_by("-assigned_at")

        if is_active is not None:
            # Map is_active to status field
            if is_active:
                queryset = queryset.filter(status=DsrDealerAssignment.STATUS_ACTIVE)
            else:
                queryset = queryset.filter(status__in=[
                    DsrDealerAssignment.STATUS_REMOVED,
                    DsrDealerAssignment.STATUS_LEFT
                ])

        if role:
            queryset = queryset.filter(role=role)

        # FIX: Use async iteration instead of `await queryset.all()` —
        # Django QuerySet doesn't support await on `.all()`.
        assignments = []
        async for a in queryset:
            assignments.append(a)

        return [
            {
                "id": a.id,
                "dsr_id": str(a.dsr.id),
                "dsr_name": a.dsr.full_name,
                "dealer_username": a.dealer.username,
                "dealer_name": a.dealer.full_name,
                "role": a.role,
                "is_active": a.is_active,
                "assigned_at": a.assigned_at.isoformat(),
                "parent_dsr_id": str(a.parent_dsr.id) if a.parent_dsr else None,
                "parent_dsr_name": a.parent_dsr.full_name if a.parent_dsr else None,
            }
            for a in assignments
        ]

    @http_patch("/assignments/{assignment_id}/deactivate")
    async def deactivate_assignment(self, request, assignment_id: str):
        """
        Deactivate a DSR assignment (soft remove from dealer's team).
        """
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return {"detail": "Authentication required", "code": "auth_required"}, 401

        # FIX H-17 / H-19: async get + ownership check
        try:
            assignment = await DsrDealerAssignment.objects.select_related("dsr", "dealer").aget(
                id=assignment_id, dealer__username=dealer_username
            )
        except DsrDealerAssignment.DoesNotExist:
            return {"detail": "Assignment not found", "code": "not_found"}, 404

        # FIX H-19: use async save
        await assignment.asave(update_fields=["status", "updated_at"])

        return {"message": "Assignment deactivated"}

    @http_patch("/assignments/{assignment_id}/activate")
    async def activate_assignment(self, request, assignment_id: str):
        """
        Reactivate a previously deactivated DSR assignment.
        """
        dealer_username = getattr(request, 'dealer_username', None)
        if not dealer_username:
            return {"detail": "Authentication required", "code": "auth_required"}, 401

        # FIX H-17 / H-19: async get + ownership check
        try:
            assignment = await DsrDealerAssignment.objects.select_related("dsr", "dealer").aget(
                id=assignment_id, dealer__username=dealer_username
            )
        except DsrDealerAssignment.DoesNotExist:
            return {"detail": "Assignment not found", "code": "not_found"}, 404

        await assignment.aactivate()

        return {"message": "Assignment activated"}
