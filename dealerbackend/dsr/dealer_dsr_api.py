"""
DEALERCORE v3.0 — Dealer DSR Management API
--------------------------------------------
Endpoints for dealers to manage DSRs (invite, remove, update permissions).

Dealer-side operations:
- Invite DSR by email (phone optional)
- List DSRs (active, pending, removed)
- Update DSR permissions
- Remove DSR from team
- Revoke pending invitations

Email is now the primary identifier for DSR invitations.
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
from common.permissions import IsJwtAuthenticated, IsDealerOnly
from common.tasks import send_dsr_invitation_email, send_dsr_notification_email
from common.rate_limit import rate_limit


def get_dealer_from_request(request: HttpRequest) -> Optional[DealerConfig]:
    """Get dealer from request context (sync version).

    FIX S-3: prefer the dealer_username that the PermissionMiddleware resolved
    from the verified JWT. Falls back to the X-Dealer-Username header ONLY if
    the middleware didn't set one. Cross-check the header against the JWT
    derived value to prevent header-spoofing dealer impersonation.
    """
    jwt_dealer = getattr(request, "dealer_username", None)
    header_dealer = request.headers.get("X-Dealer-Username")

    chosen = jwt_dealer or header_dealer
    if not chosen:
        return None

    # If both are set they must agree — otherwise someone is trying to spoof.
    if (
        jwt_dealer
        and header_dealer
        and jwt_dealer != header_dealer
    ):
        return None

    try:
        return DealerConfig.objects.get(username=chosen)
    except DealerConfig.DoesNotExist:
        return None


async def aget_dealer_from_request(request: HttpRequest) -> Optional[DealerConfig]:
    """Async version of get_dealer_from_request.

    FIX S-3: same change as the sync helper — derive dealer from the verified
    JWT (via the middleware), not from the raw X-Dealer-Username header.
    """
    jwt_dealer = getattr(request, "dealer_username", None)
    header_dealer = request.headers.get("X-Dealer-Username")

    chosen = jwt_dealer or header_dealer
    if not chosen:
        return None

    if (
        jwt_dealer
        and header_dealer
        and jwt_dealer != header_dealer
    ):
        return None

    try:
        return await DealerConfig.objects.aget(username=chosen)
    except DealerConfig.DoesNotExist:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# DEALER DSR MANAGEMENT CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

@api_controller(
    "/dealer/dsr",
    tags=["Dealer DSR Management"],
    # FIX S-7: was `permissions=[AllowAny]`. The controller manages dealer-only
    # data (DSR roster, invitations, assignments), so require both a valid JWT
    # (any role) AND a dealer identity. Per-endpoint ownership checks happen
    # inside each method via `aget_dealer_from_request`.
    permissions=[IsJwtAuthenticated, IsDealerOnly],
)
class DealerDsrController:
    """
    Dealer DSR Management endpoints.
    
    Dealers can:
    - Invite DSRs by email (primary identifier)
    - View all DSR assignments
    - Update DSR permissions
    - Remove DSRs from their team
    """
    
    @http_post("/invite", response={200: DealerInviteOutput, 400: dict})
    async def invite_dsr(self, request: HttpRequest, data: DealerInviteDsrInput):
        """
        Invite a DSR to join the dealer's team.
        
        Email is the primary identifier (required).
        Phone is optional for contact purposes.
        
        If DSR is not registered:
        - Creates pending invitation
        - Returns registration URL with token
        - Sends invitation email via Celery
        
        If DSR is registered:
        - Creates pending invitation linked to existing DSR
        - Sends notification email via Celery
        - DSR will see it in their invitation list
        """
        import logging
        logger = logging.getLogger(__name__)
        
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        # Normalize email
        email = data.dsr_email.lower().strip()
        phone = data.dsr_phone.strip() if data.dsr_phone else ""
        
        # Check for existing pending invitation by email
        existing = await DsrInvitation.objects.filter(
            dealer=dealer,
            dsr_email=email,
            status=DsrInvitation.STATUS_PENDING,
        ).aexists()
        
        if existing:
            return 400, {
                "detail": "Pending invitation already exists for this email",
                "code": "invitation_exists"
            }
        
        # Check if DSR already exists (registered) - search by email
        dsr_profile = None
        existing_user = None
        
        try:
            existing_user = await DsrUser.objects.aget(email__iexact=email)
            # Get DSR profile
            dsr_profile = await DSR.objects.aget(user=existing_user)
        except DsrUser.DoesNotExist:
            pass
        except DSR.DoesNotExist:
            pass
        
        # Check if already assigned to this dealer
        if dsr_profile:
            existing_assignment = await DsrDealerAssignment.objects.filter(
                dsr=dsr_profile,
                dealer=dealer,
                # FIX H-16: only treat ACTIVE assignments as "already assigned".
                # REMOVED / LEFT assignments are still in the table (history is
                # preserved) but the DSR is not currently on the team, so a
                # new invite + reactivation is the expected workflow.
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).afirst()
            
            if existing_assignment:
                return 400, {
                    "detail": "DSR is already assigned to your team",
                    "code": "already_assigned"
                }
        
        # Create invitation
        invitation_id = f"INV-{dealer.username}-{email.split('@')[0][:8]}-{secrets.token_hex(4)}"

        # FIX H-15: validate role against DsrInvitation.ROLE_CHOICES so the
        # dealer can't invite a DSR with an unknown role (e.g. "superadmin").
        valid_roles = {choice for choice, _ in DsrInvitation.ROLE_CHOICES}
        if data.role not in valid_roles:
            return 400, {
                "detail": f"Invalid role '{data.role}'. Must be one of: {sorted(valid_roles)}",
                "code": "invalid_role",
            }

        # Set permissions
        permissions = data.permissions
        if not permissions and data.role in DEFAULT_PERMISSIONS:
            permissions = DEFAULT_PERMISSIONS[data.role].copy()
        
        invitation = await DsrInvitation.objects.acreate(
            id=invitation_id,
            dealer=dealer,
            dsr_phone=phone,
            dsr_email=email,
            dsr=dsr_profile,
            role=data.role,
            permissions=permissions or {},
            parent_dsr_id=data.parent_dsr_id,
            message=data.message or "",
        )

        # FIX L-9: regenerate the token so we have the raw value for the
        # email URL, then store the hash in the DB. The raw token is NOT
        # persisted — only the hash lives in invitation.token.
        raw_token = invitation._generate_token()
        invitation.token = DsrInvitation.hash_token(raw_token)
        await invitation.asave(update_fields=["token", "updated_at"])

        # Generate registration URL if DSR not registered
        registration_url = None
        frontend_url = getattr(settings, 'DEALER_FRONTEND_URL', 'http://localhost:4323')

        if not existing_user:
            # DSR not registered - create registration link (uses RAW token)
            registration_url = f"{frontend_url}/dsr/register/{raw_token}"
            
            # Send invitation email via Celery
            send_dsr_invitation_email.delay(
                email=email,
                dealer_name=dealer.full_name or dealer.username,
                dealer_business=dealer.business_name or "",
                role=data.role,
                registration_url=registration_url,
                expires_at=invitation.expires_at.isoformat() if invitation.expires_at else None,
                message=data.message,
            )
            
            logger.info(f"[DSR INVITE] Invitation email queued for {email}")
        
        else:
            # DSR is registered - send notification email
            dsr_name = existing_user.full_name or email.split('@')[0]
            
            send_dsr_notification_email.delay(
                email=email,
                dsr_name=dsr_name,
                dealer_name=dealer.full_name or dealer.username,
                dealer_business=dealer.business_name or "",
                role=data.role,
                invitation_id=invitation.id,
                message=data.message,
            )
            
            logger.info(f"[DSR INVITE] Notification email queued for registered DSR {email}")
        
        # FIX H-20: do NOT return the raw token in the response body. With the
        # previous `AllowAny` controller this was a full impersonation vector:
        # any caller could grab the token and use it to register as the
        # invited DSR. The token lives in the registration URL (for the email
        # link); the dealer doesn't need it separately.
        return {
            "id": invitation.id,
            "dsr_email": invitation.dsr_email,
            "dsr_phone": invitation.dsr_phone,
            "role": invitation.role,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
            "registration_url": registration_url,
            "message": "Invitation email sent" if existing_user else "Registration link sent to email",
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
                "dsr_email": inv.dsr_email,
                "dsr_phone": inv.dsr_phone,
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
        ).select_related("dsr", "dsr__user"):
            # Check has_account by checking if user_id is set (avoids lazy loading)
            has_account = assignment.dsr.user_id is not None
            active.append({
                "id": assignment.id,
                "dsr_id": assignment.dsr.id,
                "dsr_name": assignment.dsr.name,
                "dsr_email": assignment.dsr.email,
                "dsr_phone": assignment.dsr.phone,
                "role": assignment.role,
                "permissions": assignment.permissions,
                "assigned_at": assignment.assigned_at,
                "commission_rate": float(assignment.commission_rate) if assignment.commission_rate else None,
                "has_account": has_account,
            })
        
        # Pending invitations
        pending_invitations = []
        async for inv in DsrInvitation.objects.filter(
            dealer=dealer,
            status=DsrInvitation.STATUS_PENDING,
        ):
            pending_invitations.append({
                "id": inv.id,
                "dsr_email": inv.dsr_email,
                "dsr_phone": inv.dsr_phone,
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
            # FIX H-15: validate against DsrInvitation.ROLE_CHOICES so a
            # caller can't smuggle in `role="superadmin"` (or any other
            # unknown string) to bypass downstream role-string checks.
            valid_roles = {choice for choice, _ in DsrInvitation.ROLE_CHOICES}
            if data.role not in valid_roles:
                return 400, {
                    "detail": f"Invalid role '{data.role}'. Must be one of: {sorted(valid_roles)}",
                    "code": "invalid_role",
                }
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
        
        # Deactivate assignment (dealer removing) - use async version
        reason = data.reason if data else None
        await assignment.adeactivate_by_dealer(reason or "")
        
        # TODO: Notify DSR about removal via email
        
        return {"message": f"DSR {assignment.dsr.name} removed from team"}
    
    @http_get("/search", response={200: dict})
    async def search_dsr(self, request: HttpRequest, email: str = ""):
        """
        Search for existing DSR by email.
        
        Used in AddRepModal to check if DSR already has an account.
        """
        if not email:
            return {"exists": False}
        
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}
        
        # Check if DSR user exists by email
        try:
            user = await DsrUser.objects.aget(email__iexact=email)
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
                "dsr_email": user.email,
                "dsr_phone": dsr.phone,
                "already_assigned": is_assigned,
            }
        except (DsrUser.DoesNotExist, DSR.DoesNotExist):
            pass
        
        # Check if there's a pending invitation
        pending_inv = await DsrInvitation.objects.filter(
            dsr_email__iexact=email,
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
