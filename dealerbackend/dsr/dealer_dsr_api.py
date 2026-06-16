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
from common.permissions import IsJwtAuthenticated, IsDealerOnly, IsDsrOrDealer
from common.tasks import (
    send_dsr_invitation_email,
    send_dsr_notification_email,
    send_dsr_removed_notification,
)
from common.rate_limit import rate_limit


def get_dealer_from_request(request: HttpRequest) -> Optional[DealerConfig]:
    """Get dealer from request context (sync version).

    FIX S-3: prefer the dealer_username that the PermissionMiddleware resolved
    from the verified JWT. Falls back to the X-Dealer-Username header ONLY if
    the middleware didn't set one. Cross-check the header against the JWT
    derived value to prevent header-spoofing dealer impersonation.
    
    For DSRs: Verify DSR is assigned to the dealer before returning.
    """
    jwt_dealer = getattr(request, "dealer_username", None)
    if jwt_dealer is not None:
        jwt_dealer = str(jwt_dealer)  # FIX: normalize int→str for comparison
    header_dealer = request.headers.get("X-Dealer-Username")
    is_dealer = getattr(request, "is_dealer", False)

    chosen = jwt_dealer or header_dealer
    if not chosen:
        return None

    # If both are set they must agree — otherwise someone is trying to spoof.
    # Only applies to dealers (DSRs use header for selected dealer context)
    if (
        is_dealer
        and jwt_dealer
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
    
    For DSRs: Verify DSR is assigned to the selected dealer before returning.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # FIX: Normalize to string — JWT user_id may be int (e.g. 1) while
    # X-Dealer-Username header is always str (e.g. "1"). Without str()
    # normalization, the anti-spoofing check jwt_dealer != header_dealer
    # incorrectly fails because 1 != "1" in Python.
    jwt_dealer = getattr(request, "dealer_username", None)
    if jwt_dealer is not None:
        jwt_dealer = str(jwt_dealer)
    header_dealer = request.headers.get("X-Dealer-Username")
    is_dealer = getattr(request, "is_dealer", False)
    user_email = getattr(request, "user_email", None)

    logger.info(
        f"[aget_dealer_from_request] jwt_dealer={jwt_dealer}, "
        f"header_dealer={header_dealer}, is_dealer={is_dealer}, user_email={user_email}"
    )

    # FIX: If middleware didn't set is_dealer=True, check via DealerConfig
    # lookup. SattaBase JWTs may not include is_dealer flag, but the user
    # might still be a dealer (has a DealerConfig record).
    if not is_dealer and jwt_dealer:
        try:
            is_dealer = await DealerConfig.objects.filter(username=str(jwt_dealer)).aexists()
            if is_dealer:
                logger.info(f"[aget_dealer_from_request] Dealer detected via DealerConfig fallback: {jwt_dealer}")
        except Exception as e:
            logger.warning(f"[aget_dealer_from_request] DealerConfig lookup failed: {e}")

    # Determine which dealer to use
    # For dealers: use their own dealer context (jwt_dealer)
    # For DSRs: use the header_dealer (selected dealer context)
    if is_dealer:
        chosen = jwt_dealer or header_dealer
        # If both are set, they must agree (prevent spoofing)
        if jwt_dealer and header_dealer and jwt_dealer != header_dealer:
            logger.warning(f"[aget_dealer_from_request] Dealer spoofing attempt: jwt={jwt_dealer} != header={header_dealer}")
            return None
    else:
        # DSR: Use the header dealer (their selected dealer context)
        chosen = header_dealer or jwt_dealer

    if not chosen:
        logger.warning("[aget_dealer_from_request] No dealer context found")
        return None

    logger.info(f"[aget_dealer_from_request] Looking up dealer with username={chosen}")

    try:
        dealer = await DealerConfig.objects.aget(username=chosen)
        logger.info(f"[aget_dealer_from_request] Found dealer: {dealer.username}")
        
        # For DSRs, verify assignment to this dealer
        if not is_dealer and user_email:
            # Check if this DSR is assigned to the dealer
            try:
                dsr_profile = await DsrUser.objects.aget(email__iexact=user_email)
                
                is_assigned = await DsrDealerAssignment.objects.filter(
                    dsr=dsr_profile,
                    dealer=dealer,
                    status=DsrDealerAssignment.STATUS_ACTIVE
                ).aexists()
                
                if not is_assigned:
                    logger.warning(
                        f"[aget_dealer_from_request] DSR {user_email} not assigned to dealer {chosen}"
                    )
                    return None
                    
                logger.info(f"[aget_dealer_from_request] DSR {user_email} is assigned to dealer {chosen}")
            except DsrUser.DoesNotExist:
                logger.warning(f"[aget_dealer_from_request] DSR user/profile not found for {user_email}")
                return None
        
        return dealer
    except DealerConfig.DoesNotExist:
        logger.warning(f"[aget_dealer_from_request] DealerConfig not found for username={chosen}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# DEALER DSR MANAGEMENT CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

@api_controller(
    "/dealer/dsr",
    tags=["Dealer DSR Management"],
    # Base permission: require valid JWT. Specific endpoints may override.
    # DSRs can view team members but only dealers can invite/remove/update.
    permissions=[IsJwtAuthenticated, IsDsrOrDealer],
)
class DealerDsrController:
    """
    Dealer DSR Management endpoints.
    
    Dealers can:
    - Invite DSRs by email (primary identifier)
    - View all DSR assignments
    - Update DSR permissions
    - Remove DSRs from their team
    
    DSRs can:
    - View DSR list (for forms, dropdowns)
    - Search for DSRs by email
    """
    
    @http_post("/invite", response={200: DealerInviteOutput, 400: dict, 403: dict})
    async def invite_dsr(self, request: HttpRequest, data: DealerInviteDsrInput):
        """
        Invite a DSR to join the dealer's team.
        
        DEALER ONLY: DSRs cannot invite other DSRs.
        
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
        # Dealer-only check
        if not getattr(request, 'is_dealer', False):
            return 403, {"detail": "Only dealers can invite DSRs", "code": "dealer_only"}
        
        import logging
        logger = logging.getLogger(__name__)
        
        dealer = await aget_dealer_from_request(request)
        if not dealer:
            return 400, {"detail": "Dealer context required", "code": "dealer_required"}

        # FIX A-1 (Phase A — CRIT-1): server-side enforcement of
        # `max_dsrs` plan limit. Counts active assignments for this dealer
        # and refuses to create more if the plan cap is reached.
        from common.plan_limits import check_plan_limit
        active_count = await DsrDealerAssignment.objects.filter(
            dealer=dealer,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).acount()
        check_plan_limit(request, "max_dsrs", active_count + 1)

        # Normalize email
        email = data.dsr_email.lower().strip()
        phone = data.dsr_phone.strip() if data.dsr_phone else ""
        
        # Check for existing pending invitation by email
        # FIX: Auto-revoke stale pending invitations instead of blocking.
        # This handles the common case where a previous invite attempt
        # created the DB record but the API response errored out (e.g. the
        # Pydantic token-field validation bug), leaving the dealer stuck
        # with an invisible pending invitation they can't re-send.
        existing_invitation = await DsrInvitation.objects.filter(
            dealer=dealer,
            dsr_email=email,
            status=DsrInvitation.STATUS_PENDING,
        ).afirst()
        
        if existing_invitation:
            # Check if it's expired — auto-revoke expired invitations
            if existing_invitation.expires_at and existing_invitation.expires_at < timezone.now():
                await existing_invitation.arevoke()
                logger.info(f"[DSR INVITE] Auto-revoked expired invitation {existing_invitation.id} for {email}")
            else:
                # Active pending invitation exists — revoke and re-invite
                # so the dealer gets a fresh token and email is re-sent.
                await existing_invitation.arevoke()
                logger.info(f"[DSR INVITE] Revoked existing pending invitation {existing_invitation.id} for re-invite")
        
        # Check if DSR already exists (registered) - search by email
        dsr_profile = None
        existing_user = None
        
        # After DSR merge, DsrUser IS the DSR — no separate lookup needed
        try:
            existing_user = await DsrUser.objects.aget(email__iexact=email)
            dsr_profile = existing_user  # After merge, DsrUser IS the DSR
        except DsrUser.DoesNotExist:
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
            
            # FIX: If DSR has an unusable password (e.g. migrated from old DSR
            # model with set_unusable_password()), they can't log into the DSR
            # portal to see/accept the invitation. Generate a password setup
            # token and include it in the notification email.
            password_setup_url = None
            if not existing_user.has_usable_password():
                import secrets as _secrets
                setup_token = _secrets.token_urlsafe(32)
                await existing_user.aset_password_reset_token(setup_token)
                password_setup_url = (
                    f"{getattr(settings, 'DEALER_FRONTEND_URL', 'http://localhost:4323')}"
                    f"/dsr/reset-password?token={setup_token}"
                )
                logger.info(f"[DSR INVITE] Generated password setup link for {email} (unusable password)")
            
            send_dsr_notification_email.delay(
                email=email,
                dsr_name=dsr_name,
                dealer_name=dealer.full_name or dealer.username,
                dealer_business=dealer.business_name or "",
                role=data.role,
                invitation_id=invitation.id,
                message=data.message,
                password_setup_url=password_setup_url,
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
    
    @http_get("/invitations", response={200: dict, 400: dict})
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
    
    @http_delete("/invitations/{invitation_id}", response={200: MessageOutput, 400: dict, 403: dict, 404: dict})
    async def revoke_invitation(self, request: HttpRequest, invitation_id: str):
        """Revoke a pending invitation. DEALER ONLY."""
        # Dealer-only check
        if not getattr(request, 'is_dealer', False):
            return 403, {"detail": "Only dealers can revoke invitations", "code": "dealer_only"}
        
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
        
        # FIX DSR-003: use async arevoke() instead of sync revoke() + asave()
        await invitation.arevoke()
        
        return {"message": "Invitation revoked"}
    
    @http_get("", response={200: DealerDsrListOutput, 400: dict})
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
            # After DSR merge, dsr FK points to DsrUser which IS the account
            has_account = assignment.dsr_id is not None
            active.append({
                "id": assignment.id,
                "dsr_id": str(assignment.dsr.id),
                "dsr_name": assignment.dsr.full_name or assignment.dsr.phone or assignment.dsr.email or "Unknown",
                "dsr_email": assignment.dsr.email or "",
                "dsr_phone": assignment.dsr.phone or "",
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
                "dsr_id": str(assignment.dsr.id),
                "dsr_name": assignment.dsr.full_name or assignment.dsr.phone or assignment.dsr.email or "Unknown",
                "role": assignment.role,
                "removed_at": assignment.removed_at,
                "removal_reason": assignment.removal_reason,
            })
        
        return {
            "active": active,
            "pending_invitations": pending_invitations,
            "removed": removed,
        }
    
    @http_put("/assignments/{assignment_id}", response={200: dict, 400: dict, 403: dict, 404: dict})
    async def update_dsr(self, request: HttpRequest, assignment_id: str, data: UpdateDsrPermissionsInput):
        """Update DSR permissions/role. DEALER ONLY."""
        # Dealer-only check
        if not getattr(request, 'is_dealer', False):
            return 403, {"detail": "Only dealers can update DSR permissions", "code": "dealer_only"}
        
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
    
    @http_delete("/assignments/{assignment_id}", response={200: MessageOutput, 400: dict, 403: dict, 404: dict})
    async def remove_dsr(self, request: HttpRequest, assignment_id: str, data: RemoveDsrInput = None):
        """
        Remove DSR from dealer's team. DEALER ONLY.
        
        Transaction records are preserved with DSR name snapshot.
        DSR will be notified of removal.
        """
        # Dealer-only check
        if not getattr(request, 'is_dealer', False):
            return 403, {"detail": "Only dealers can remove DSRs", "code": "dealer_only"}
        
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

        # FIX DSR-010: Optional sale reassignment on DSR removal.
        # If reassign_to_dsr_id is provided, active sales are transferred
        # to the new DSR. If not, sales are left with dsr_status='removed'.
        reassign_to = None
        if data and data.reassign_to_dsr_id:
            # Validate the target DSR is active in this dealer's team
            try:
                reassign_assignment = await DsrDealerAssignment.objects.aget(
                    dsr_id=data.reassign_to_dsr_id,
                    dealer=dealer,
                    status=DsrDealerAssignment.STATUS_ACTIVE,
                )
                reassign_to = await DsrUser.objects.aget(id=data.reassign_to_dsr_id)
            except (DsrDealerAssignment.DoesNotExist, DsrUser.DoesNotExist):
                return 400, {
                    "detail": f"DSR with id '{data.reassign_to_dsr_id}' not found or not active in your team",
                    "code": "invalid_reassign_target"
                }

        if reassign_to:
            # Reassign active sales to the new DSR
            await SaleRecord.objects.filter(
                dsr=dsr,
                dealer=dealer
            ).aupdate(dsr=reassign_to, dsr_status='reassigned')

            # Update original DSR sales to show removed status
            await SaleRecord.objects.filter(
                original_dsr=dsr,
                dealer=dealer
            ).aupdate(original_dsr_status='removed')
        else:
            # Just mark sales as removed (no reassignment)
            await SaleRecord.objects.filter(
                dsr=dsr,
                dealer=dealer
            ).aupdate(dsr_status='removed')

            await SaleRecord.objects.filter(
                original_dsr=dsr,
                dealer=dealer
            ).aupdate(original_dsr_status='removed')
        
        # Deactivate assignment (dealer removing) - use async version
        reason = data.reason if data else None
        await assignment.adeactivate_by_dealer(reason or "")
        
        # FIX DSR-019: Notify DSR about removal
        if dsr and dsr.email:
            send_dsr_removed_notification.delay(
                dsr_email=dsr.email,
                dsr_name=dsr.full_name,
                dealer_name=dealer.full_name or dealer.username,
                dealer_business=dealer.business_name or "",
                reason=reason or "",
            )
        
        return {"message": f"DSR {assignment.dsr.full_name} removed from team"}
    
    @http_get("/search", response={200: dict, 400: dict})
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
            dsr = user  # After merge, DsrUser IS the DSR
            
            # Check if already assigned to this dealer
            is_assigned = await DsrDealerAssignment.objects.filter(
                dsr=dsr,
                dealer=dealer,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).aexists()
            
            return {
                "exists": True,
                "registered": True,
                "dsr_id": str(dsr.id),
                "dsr_name": dsr.full_name,
                "dsr_email": user.email,
                "dsr_phone": dsr.phone,
                "already_assigned": is_assigned,
            }
        except DsrUser.DoesNotExist:
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
                # Note: invite endpoint auto-revokes pending invitations,
                # so the user can still proceed with inviting.
            }
        
        return {
            "exists": False,
            "registered": False,
            "has_pending_invitation": False,
        }
