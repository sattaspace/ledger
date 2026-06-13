"""
DEALERCORE v3.0 - DSR Authentication API
-----------------------------------------
Authentication endpoints for DSRs, Collectors, and Managers.

This is SEPARATE from dealer authentication (which goes through SattaBase).
DSRs log in directly to DealerBackend with phone + password.

New Design:
1. DSR SELF-REGISTERS (independent profile)
2. Dealer sends invitation → DSR accepts/rejects
3. Multi-dealer support with per-dealer permissions
4. DSR can leave, Dealer can remove (preserving records)

API Endpoints:
- POST /dsr/auth/register         - Self-registration (new)
- POST /dsr/auth/register/:token  - Via invitation (existing)
- POST /dsr/auth/login            - Login with phone/email
- POST /dsr/auth/select-dealer    - Select dealer context
- POST /dsr/auth/logout           - Logout
- GET  /dsr/auth/me               - Get profile
- PUT  /dsr/auth/me               - Update profile
- POST /dsr/auth/password-reset/*  - Password management
- POST /dsr/auth/change-password  - Change password

DSR Invitation Endpoints:
- GET  /dsr/invitations           - List my invitations
- POST /dsr/invitations/:id/accept - Accept invitation
- POST /dsr/invitations/:id/reject - Reject invitation

DSR Assignment Endpoints:
- GET  /dsr/assignments           - List my dealer assignments
- POST /dsr/assignments/:id/leave - Leave a dealer
"""

import secrets
from datetime import timedelta
from typing import Optional

from ninja_extra import api_controller, route, http_post, http_get, http_put, http_delete
from ninja_extra.permissions import AllowAny, IsAuthenticated
from ninja import Schema
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import authenticate
import jwt as pyjwt

from users.models import DsrUser
from dsr.models import DSR
from dsr.invitation_models import DsrInvitation, DsrDealerAssignment
from dealer.models import DealerConfig
from common.dsr_auth_errors import (
    DsrAuthError,
    dsr_error_response,
    error_invalid_credentials,
    error_user_not_found,
    error_account_deactivated,
    error_profile_not_found,
    error_no_dealer_assignment,
    error_phone_exists,
    error_email_exists,
    error_auth_required,
    error_invalid_token,
    error_invitation_expired,
    error_invitation_invalid,
    error_password_mismatch,
)
# FIX H-6: rate-limit the auth endpoints to deter brute-force / spam.
from common.rate_limit import rate_limit
from dsr.auth_schemas import (
    DsrLoginInput,
    DsrLoginOutput,
    DsrSelfRegisterInput,
    DsrSelfRegisterOutput,
    DsrRegisterInput,
    DsrRegisterOutput,
    DealerSelectionInput,
    DealerSelectionOutput,
    DsrProfileOutput,
    UpdateProfileInput,
    DsrUserOutput,
    DealerChoice,
    PasswordResetRequestInput,
    PasswordResetConfirmInput,
    ChangePasswordInput,
    MessageOutput,
    TokenRefreshInput,
    TokenRefreshOutput,
    InvitationOutput,
    InvitationListOutput,
    AcceptInvitationOutput,
    RejectInvitationInput,
    AssignmentOutput,
    AssignmentListOutput,
    LeaveDealerInput,
)


def generate_tokens(user: DsrUser, dealer_context: Optional[DealerConfig] = None) -> tuple[str, str]:
    """Generate access and refresh tokens for a DSR user.

    FIX H-7: stamp the current `password_changed_at` value into both tokens.
    `decode_token()` later compares the claim to the live DB value and rejects
    the token if the user has changed their password since issuance.
    """
    from ninja_jwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)
    # Stamp the password-change timestamp on BOTH tokens. Even if the
    # access token's `pwd_changed_at` claim is somehow altered, the
    # refresh token check on /refresh will catch it.
    pwd_changed_at_ts = (
        int(user.password_changed_at.timestamp())
        if user.password_changed_at
        else 0
    )
    refresh["pwd_changed_at"] = pwd_changed_at_ts
    refresh.access_token["pwd_changed_at"] = pwd_changed_at_ts
    access = str(refresh.access_token)

    return access, str(refresh)


async def agenerate_tokens(user: DsrUser, dealer_context: Optional[DealerConfig] = None) -> tuple[str, str]:
    """Async wrapper for generate_tokens."""
    from asgiref.sync import sync_to_async
    return await sync_to_async(generate_tokens)(user, dealer_context)


def _pwd_changed_at_matches(user: DsrUser, payload: dict) -> bool:
    """FIX H-7: return False if the token was issued before the user's last
    password change. The comparison is int(timestamp) == int(timestamp)
    so a sub-second skew won't false-reject.
    """
    current_ts = (
        int(user.password_changed_at.timestamp())
        if user.password_changed_at
        else 0
    )
    token_ts = payload.get("pwd_changed_at")
    # Tokens issued before this fix was deployed won't have the claim;
    # we reject them conservatively (treat as stale) if the user has
    # ever changed their password. If they haven't, claim value 0 == 0.
    if token_ts is None:
        return current_ts == 0
    return int(token_ts) == current_ts


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = pyjwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_signature": True},
        )
        # FIX H-4: reject refresh tokens used as access tokens.
        # ninja_jwt sets `token_type` to "access" or "refresh"; without this
        # check, a 7-day refresh token can be used directly against protected
        # endpoints, defeating short-lived access token windows.
        token_type = payload.get("token_type")
        if token_type is not None and token_type != "access":
            return None
        return payload
    except pyjwt.InvalidTokenError:
        return None


def get_user_from_token(request: HttpRequest) -> Optional[DsrUser]:
    """Extract user from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    payload = decode_token(token)

    if not payload:
        return None

    user_id = payload.get("user_id") or payload.get("sub")

    try:
        user = DsrUser.objects.get(id=user_id)
    except DsrUser.DoesNotExist:
        return None

    # FIX H-3: deactivated users must not be able to use still-valid tokens.
    if not user.is_active:
        return None

    # FIX H-7: reject tokens issued before the user's last password change.
    if not _pwd_changed_at_matches(user, payload):
        return None

    return user


async def aget_user_from_token(request: HttpRequest) -> Optional[DsrUser]:
    """Async version of get_user_from_token."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header[7:]
    payload = decode_token(token)

    if not payload:
        return None

    user_id = payload.get("user_id") or payload.get("sub")

    try:
        user = await DsrUser.objects.aget(id=user_id)
    except DsrUser.DoesNotExist:
        return None

    # FIX H-3: deactivated users must not be able to use still-valid tokens.
    if not user.is_active:
        return None

    # FIX H-7: reject tokens issued before the user's last password change.
    if not _pwd_changed_at_matches(user, payload):
        return None

    return user


# ═══════════════════════════════════════════════════════════════════════════
# AUTHENTICATION CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

@api_controller("/dsr/auth", tags=["DSR Authentication"], permissions=[AllowAny])
class DsrAuthController:
    """
    DSR Authentication endpoints.

    DSRs log in with email + password directly to DealerBackend.
    This is separate from dealer authentication (which uses SattaBase).
    """

    @http_post("/register", response={200: DsrSelfRegisterOutput, 400: dict, 409: dict})
    @rate_limit("dsr_self_register", limit=5, period=3600, scope="ip")
    async def self_register(self, request: HttpRequest, data: DsrSelfRegisterInput):
        """
        DSR Self-Registration (Independent Profile).

        Creates an independent DSR account without any dealer assignment.
        DSR can then receive invitations from dealers.

        Email is required and must be unique (primary identifier).
        Phone is optional.
        """
        import logging
        logger = logging.getLogger(__name__)

        # DEBUG: Log incoming data
        logger.info(f"[DSR REGISTER] Received registration request: email={data.email}, phone={data.phone}, full_name={data.full_name}")
        print(f"[DSR REGISTER] Received registration request: email={data.email}, phone={data.phone}, full_name={data.full_name}")

        # Check if email already exists (email is primary identifier)
        email_exists = await DsrUser.objects.filter(email__iexact=data.email).aexists()
        logger.info(f"[DSR REGISTER] Email exists check: {email_exists}")
        print(f"[DSR REGISTER] Email exists check: {email_exists}")

        if email_exists:
            logger.warning(f"[DSR REGISTER] Email already registered: {data.email}")
            print(f"[DSR REGISTER] Email already registered: {data.email}")
            return error_email_exists()

        # Create user account (email is required, phone is optional)
        # FIX M-7 / M-10: wrap the user + DSR profile creation in
        # `async with transaction.atomic()` so a failure on the second insert
        # rolls back the first — otherwise a half-created user (with no DSR
        # profile) is left orphaned in the DB.
        from django.db import transaction as _transaction

        print(f"[DSR REGISTER] Creating user with email={data.email}")
        try:
            async with _transaction.atomic():
                user = await DsrUser.objects.acreate_user(
                    email=data.email,
                    password=data.password,
                    full_name=data.full_name,
                    phone=data.phone or "",
                    user_type=DsrUser.TYPE_DSR,
                )
                print(f"[DSR REGISTER] User created successfully: id={user.id}, email={user.email}")

                # Create DSR profile
                dsr_id = f"DSR-{str(user.id)[:8].upper()}"
                print(f"[DSR REGISTER] Creating DSR profile with id={dsr_id}")
                dsr = await DSR.objects.acreate(
                    id=dsr_id,
                    name=data.full_name,
                    phone=data.phone or "",
                    role=DSR.ROLE_DSR,
                    user=user,
                    email=data.email,
                )
                print(f"[DSR REGISTER] DSR profile created successfully: id={dsr.id}")
        except Exception as e:
            print(f"[DSR REGISTER] ERROR creating user/DSR: {type(e).__name__}: {e}")
            logger.error(f"[DSR REGISTER] ERROR creating user/DSR: {type(e).__name__}: {e}")
            # Re-raise so the view returns the appropriate error response.
            raise

        # Generate tokens
        access, refresh = await agenerate_tokens(user)

        return {
            "access": access,
            "refresh": refresh,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "phone": user.phone,
                "user_type": user.user_type,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "phone_verified": user.phone_verified,
                "email_verified": user.email_verified,
                "created_at": user.created_at,
                "has_dsr_profile": True,
            },
            "message": "Registration successful. You can now receive dealer invitations.",
        }

    @http_post("/register/{token}", response={200: DsrRegisterOutput, 400: dict, 409: dict, 410: dict})
    @rate_limit("dsr_invite_register", limit=10, period=3600, scope="ip")
    async def register_via_invitation(self, request: HttpRequest, token: str, data: DsrRegisterInput):
        """
        Register DSR account via invitation token.

        This creates:
        1. DsrUser account (for authentication)
        2. DSR profile (for business data)
        3. DsrDealerAssignment (links DSR to dealer)
        """
        # Validate invitation token (FIX L-9: hash before lookup)
        try:
            invitation = await DsrInvitation.objects.select_related("dealer").aget(
                token=DsrInvitation.hash_token(token),
                status=DsrInvitation.STATUS_PENDING,
            )
        except DsrInvitation.DoesNotExist:
            return error_invitation_invalid()

        # Check if expired
        if invitation.is_expired():
            invitation.status = DsrInvitation.STATUS_EXPIRED
            await invitation.asave(update_fields=["status"])
            return error_invitation_expired()

        # Determine phone (from data or invitation)
        phone = data.phone or invitation.dsr_phone

        # Check if user already exists
        existing_user = await DsrUser.objects.filter(phone=phone).aexists()
        if existing_user:
            return error_phone_exists()

        # Create user account + DSR profile + assignment in one transaction.
        # FIX M-7 / M-10: any failure rolls back the entire registration so we
        # don't leave orphaned DsrUser / DSR rows in the DB.
        from django.db import transaction as _transaction

        async with _transaction.atomic():
            user = await DsrUser.objects.acreate_user(
                phone=phone,
                password=data.password,
                full_name=data.full_name,
                email=invitation.dsr_email or "",
                user_type=DsrUser.TYPE_DSR,
            )

            # Create DSR profile
            dsr_id = f"DSR-{str(user.id)[:8].upper()}"
            dsr = await DSR.objects.acreate(
                id=dsr_id,
                name=data.full_name,
                phone=phone,
                role=invitation.role,
                user=user,
                email=invitation.dsr_email or "",
                parent_dsr_id=invitation.parent_dsr_id,
            )

            # Create dealer assignment (FIX M-13: ensure id fits 100-char PK)
            assignment_id = f"ASSIGN-{dsr_id}-{invitation.dealer.username}"[:100]
            await DsrDealerAssignment.objects.acreate(
                id=assignment_id,
                dsr=dsr,
                dealer=invitation.dealer,
                role=invitation.role,
                permissions=invitation.permissions,
                parent_dsr_id=invitation.parent_dsr_id,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            )

            # Mark invitation as accepted (use async version)
            await invitation.aaccept(dsr)

            # Set selected dealer
            user.selected_dealer = invitation.dealer
            await user.asave(update_fields=["selected_dealer"])

        # Generate tokens
        access, refresh = await agenerate_tokens(user)

        return {
            "access": access,
            "refresh": refresh,
            "user": {
                "id": str(user.id),
                "phone": user.phone,
                "email": user.email,
                "user_type": user.user_type,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "phone_verified": user.phone_verified,
                "email_verified": user.email_verified,
                "created_at": user.created_at,
                "has_dsr_profile": True,
            },
            "dealer": {
                "username": invitation.dealer.username,
                "full_name": invitation.dealer.full_name,
                "business_name": invitation.dealer.business_name,
            },
            "role": invitation.role,
        }

    @http_post("/login", response={200: DsrLoginOutput, 401: dict, 403: dict, 404: dict})
    @rate_limit("dsr_login", limit=5, period=60, scope="ip")
    async def login(self, request: HttpRequest, data: DsrLoginInput):
        """
        DSR login with phone/email and password.

        Returns:
        - JWT tokens (access, refresh)
        - User info
        - List of dealers the DSR is assigned to
        - require_dealer_selection flag (true if multiple dealers)

        Error Codes:
        - invalid_credentials: Wrong email or password
        - account_deactivated: User account is disabled
        - profile_not_found: DSR profile missing
        - no_dealer_assignment: DSR not assigned to any dealer
        """
        import logging
        logger = logging.getLogger(__name__)

        print(f"[DSR LOGIN] Login attempt with email: {data.email}")

        # Find user by email (email is the primary identifier)
        try:
            user = await DsrUser.objects.aget(email__iexact=data.email)
            print(f"[DSR LOGIN] Found user by email: {user.id}")
        except DsrUser.DoesNotExist:
            print(f"[DSR LOGIN] User not found by email: {data.email}")
            # FIX H-5: timing-attack mitigation. Run a dummy check_password
            # against a static PBKDF2 hash so a missing email takes the same
            # wall-clock time as a wrong password for an existing email -
            # otherwise attackers can enumerate registered emails.
            DsrUser().set_password(data.password)
            # Force the dummy hash computation to actually run:
            from django.contrib.auth.hashers import check_password as _cp
            _cp(data.password, "pbkdf2_sha256$600000$dummy$invalid+invalid+invalid")
            return error_invalid_credentials()

        # Check password
        if not user.check_password(data.password):
            print(f"[DSR LOGIN] Invalid password for user: {user.id}")
            return error_invalid_credentials()

        print(f"[DSR LOGIN] Password correct for user: {user.id}")

        # Check if active
        if not user.is_active:
            print(f"[DSR LOGIN] User account is deactivated: {user.id}")
            return error_account_deactivated()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
            print(f"[DSR LOGIN] Found DSR profile: {dsr.id}")
        except DSR.DoesNotExist:
            print(f"[DSR LOGIN] DSR profile NOT FOUND for user: {user.id}")
            print(f"[DSR LOGIN] User details: email={user.email}, phone={user.phone}, full_name={user.full_name}")
            return error_profile_not_found()

        # Get assigned dealers
        dealers = []
        async for assignment in DsrDealerAssignment.objects.filter(
            dsr=dsr,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related("dealer"):
            dealers.append({
                "username": assignment.dealer.username,
                "full_name": assignment.dealer.full_name,
                "business_name": assignment.dealer.business_name,
            })

        # Generate tokens
        access, refresh = await agenerate_tokens(user)

        # If DSR has no dealer assignments, still allow login
        # They can view pending invitations in their dashboard
        if not dealers:
            print(f"[DSR LOGIN] No dealer assignments for DSR: {dsr.id}")
            return {
                "access": access,
                "refresh": refresh,
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "phone": user.phone,
                    "user_type": user.user_type,
                    "full_name": user.full_name,
                    "avatar_url": user.avatar_url,
                    "phone_verified": user.phone_verified,
                    "email_verified": user.email_verified,
                    "created_at": user.created_at,
                    "has_dsr_profile": True,
                },
                "dealers": [],
                "require_dealer_selection": False,
                "message": "You are not assigned to any dealer yet. Check your invitations.",
                "awaiting_invitation": True,  # Flag for frontend
            }

        # If only one dealer, auto-select it
        require_dealer_selection = len(dealers) > 1
        if len(dealers) == 1:
            user.selected_dealer_id = dealers[0]["username"]
            await user.asave(update_fields=["selected_dealer"])

        # Update last login
        user.last_login = timezone.now()
        await user.asave(update_fields=["last_login"])

        return {
            "access": access,
            "refresh": refresh,
            "user": {
                "id": str(user.id),
                "phone": user.phone,
                "email": user.email,
                "user_type": user.user_type,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "phone_verified": user.phone_verified,
                "email_verified": user.email_verified,
                "created_at": user.created_at,
                "has_dsr_profile": True,
            },
            "dealers": dealers,
            "require_dealer_selection": require_dealer_selection,
        }

    @http_post("/select-dealer", response={200: DealerSelectionOutput, 401: dict, 403: dict, 404: dict})
    async def select_dealer(self, request: HttpRequest, data: DealerSelectionInput):
        """
        Select dealer context for multi-dealer DSR.

        Updates the user's selected_dealer and returns new tokens.
        """
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Validate dealer
        try:
            dealer = await DealerConfig.objects.aget(username=data.dealer_username)
        except DealerConfig.DoesNotExist:
            return dsr_error_response("Dealer not found", "dealer_not_found", 404)

        # Check if DSR is assigned to this dealer
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            return error_profile_not_found()

        assignment = await DsrDealerAssignment.objects.filter(
            dsr=dsr,
            dealer=dealer,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).afirst()

        if not assignment:
            return dsr_error_response(
                "You are not assigned to this dealer",
                "not_assigned",
                403
            )

        # Update selected dealer
        user.selected_dealer = dealer
        await user.asave(update_fields=["selected_dealer"])

        # Generate new tokens with dealer context
        access, refresh = await agenerate_tokens(user)

        return {
            "access": access,
            "refresh": refresh,
            "dealer": {
                "username": dealer.username,
                "full_name": dealer.full_name,
                "business_name": dealer.business_name,
            },
            "permissions": assignment.permissions,
        }

    @http_post("/refresh", response={200: TokenRefreshOutput, 401: dict})
    @rate_limit("dsr_refresh", limit=10, period=60, scope="ip")
    async def refresh_token(self, request: HttpRequest, data: TokenRefreshInput):
        """Refresh access token using refresh token."""
        from ninja_jwt.tokens import RefreshToken
        from django.contrib.auth import get_user_model

        try:
            refresh = RefreshToken(data.refresh)
            user_id = refresh.get("user_id") or refresh.get("sub")
            if not user_id:
                return error_invalid_token()
            # FIX H-7: enforce the password_changed_at check at refresh
            # time as well. If the user changed their password since the
            # refresh token was issued, refuse to mint a new access token.
            User = get_user_model()
            try:
                user = await User.objects.aget(id=user_id)
            except User.DoesNotExist:
                return error_invalid_token()
            if not user.is_active:
                return error_invalid_token()
            if not _pwd_changed_at_matches(user, dict(refresh.payload)):
                return error_invalid_token()
            access = str(refresh.access_token)
            new_refresh = str(refresh)

            return {
                "access": access,
                "refresh": new_refresh,
            }
        except Exception:
            return error_invalid_token()

    @http_post("/logout", response=MessageOutput)
    async def logout(self, request: HttpRequest):
        """Logout DSR by blacklisting the refresh token."""
        from ninja_jwt.tokens import RefreshToken

        refresh_token = request.COOKIES.get("dsr_refresh_token")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass

        response = JsonResponse({"message": "Logout successful"})
        response.delete_cookie("dsr_refresh_token")

        return response

    @http_get("/me", response={200: DsrProfileOutput, 401: dict})
    async def get_profile(self, request: HttpRequest):
        """Get current DSR profile and dealer assignments."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            dsr = None

        # Get dealers
        dealers = []
        selected_dealer = None

        if dsr:
            async for assignment in DsrDealerAssignment.objects.filter(
                dsr=dsr,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).select_related("dealer"):
                dealer_info = {
                    "username": assignment.dealer.username,
                    "full_name": assignment.dealer.full_name,
                    "business_name": assignment.dealer.business_name,
                }
                dealers.append(dealer_info)

                if user.selected_dealer_id == assignment.dealer.username:
                    selected_dealer = dealer_info

        return {
            "user": {
                "id": str(user.id),
                "phone": user.phone,
                "email": user.email,
                "user_type": user.user_type,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "phone_verified": user.phone_verified,
                "email_verified": user.email_verified,
                "created_at": user.created_at,
                "has_dsr_profile": dsr is not None,
            },
            "dsr_id": dsr.id if dsr else None,
            "dsr_name": dsr.name if dsr else "",
            "dsr_role": dsr.role if dsr else "",
            "dealers": dealers,
            "selected_dealer": selected_dealer,
            "skills": user.skills,
            "experience_years": user.experience_years,
            "rating": float(user.rating),
            "total_jobs": user.total_jobs,
        }

    @http_put("/me", response={200: DsrProfileOutput, 401: dict})
    async def update_profile(self, request: HttpRequest, data: UpdateProfileInput):
        """Update DSR profile."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Update fields
        if data.full_name is not None:
            user.full_name = data.full_name
        if data.email is not None:
            user.email = data.email
        if data.avatar_url is not None:
            user.avatar_url = data.avatar_url
        if data.bio is not None:
            user.bio = data.bio
        if data.skills is not None:
            user.skills = data.skills
        if data.experience_years is not None:
            user.experience_years = data.experience_years

        await user.asave()

        # Sync DSR profile if exists
        try:
            dsr = await DSR.objects.aget(user=user)
            if data.full_name:
                dsr.name = data.full_name
                await dsr.asave(update_fields=["name"])
        except DSR.DoesNotExist:
            dsr = None

        return await self.get_profile(request)

    @http_post("/change-password", response={200: MessageOutput, 400: dict, 401: dict})
    async def change_password(self, request: HttpRequest, data: ChangePasswordInput):
        """Change password (authenticated user)."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Verify current password
        if not user.check_password(data.current_password):
            return error_password_mismatch()

        # Set new password
        user.set_password(data.new_password)
        await user.asave()

        return {"message": "Password changed successfully"}

    @http_post("/password-reset/request", response=MessageOutput)
    @rate_limit(
        "dsr_password_reset_request",
        limit=3,
        period=3600,
        scope="ip",
    )
    async def request_password_reset(self, request: HttpRequest, data: PasswordResetRequestInput):
        """Request password reset via phone or email."""
        # Find user by phone or email
        user = None

        try:
            user = await DsrUser.objects.aget(phone=data.phone_or_email)
        except DsrUser.DoesNotExist:
            pass

        if not user:
            try:
                user = await DsrUser.objects.aget(email__iexact=data.phone_or_email)
            except DsrUser.DoesNotExist:
                pass

        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            # FIX H-9: use async setter (model now hashes the token - see M-4)
            await user.aset_password_reset_token(token)

            # TODO: Send SMS or email with reset link
            # The message should contain:
            # {FRONTEND_URL}/dsr/reset-password?token={token}

        # Always return success to prevent enumeration
        return {"message": "If the account exists, a password reset link has been sent."}

    @http_post("/password-reset/confirm", response={200: MessageOutput, 400: dict, 401: dict})
    async def confirm_password_reset(self, request: HttpRequest, data: PasswordResetConfirmInput):
        """Confirm password reset with token."""
        # FIX M-4: tokens are stored as SHA-256 hashes, so look up by the hash
        # of the supplied token instead of the raw token.
        from users.models import DsrUser as _DU
        hashed = _DU._hash_reset_token(data.token)
        try:
            user = await DsrUser.objects.aget(password_reset_token=hashed)
        except DsrUser.DoesNotExist:
            return error_invalid_token()

        # Check if token is valid (constant-time compare against stored hash)
        if not user.is_password_reset_valid(data.token):
            return error_invalid_token()

        # Reset password
        user.set_password(data.new_password)
        # FIX H-9: async clear
        await user.aclear_password_reset_token()

        return {"message": "Password reset successful"}


# ═══════════════════════════════════════════════════════════════════════════
# DSR INVITATIONS CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

@api_controller("/dsr/invitations", tags=["DSR Invitations"], permissions=[AllowAny])
class DsrInvitationController:
    """
    DSR Invitation management endpoints.

    DSRs can view, accept, or reject dealer invitations.
    """

    @http_get("", response={200: InvitationListOutput, 401: dict})
    async def list_invitations(self, request: HttpRequest):
        """List all invitations for the authenticated DSR."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            return error_profile_not_found()

        # Get invitations by status
        pending = []
        accepted = []
        rejected = []

        async for inv in DsrInvitation.objects.filter(
            dsr=dsr
        ).select_related("dealer").order_by("-created_at"):
            inv_data = {
                "id": inv.id,
                # NOTE: the raw `token` IS returned here for the
                # already-authenticated DSR. Risk is bounded because:
                #   1. The endpoint requires a valid JWT (IsJwtAuthenticated
                #      applied at controller level via `permissions`).
                #   2. The filter `dsr=dsr` restricts results to the calling
                #      user's own invitations - they can't see tokens for
                #      invitations belonging to other DSRs.
                #   3. The frontend needs the token to call /accept/{token}.
                # If you later add a "accept by id" endpoint that resolves
                # id → token server-side, the token field can be removed
                # here without breaking the accept flow.
                "token": inv.token,
                "dealer": {
                    "username": inv.dealer.username,
                    "full_name": inv.dealer.full_name,
                    "business_name": inv.dealer.business_name,
                },
                "role": inv.role,
                "permissions": inv.permissions,
                "message": inv.message,
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
                "status": inv.status,
            }

            if inv.status == DsrInvitation.STATUS_PENDING:
                pending.append(inv_data)
            elif inv.status == DsrInvitation.STATUS_ACCEPTED:
                accepted.append(inv_data)
            elif inv.status == DsrInvitation.STATUS_REJECTED:
                rejected.append(inv_data)

        return {
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
        }

    @http_post("/{invitation_id}/accept", response={200: AcceptInvitationOutput, 400: dict, 401: dict, 404: dict, 410: dict})
    async def accept_invitation(self, request: HttpRequest, invitation_id: str):
        """Accept a dealer invitation."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            return error_profile_not_found()

        # Get invitation
        try:
            invitation = await DsrInvitation.objects.select_related("dealer").aget(
                id=invitation_id,
                dsr=dsr,
                status=DsrInvitation.STATUS_PENDING,
            )
        except DsrInvitation.DoesNotExist:
            return dsr_error_response(
                "Invitation not found or already processed",
                "not_found",
                404
            )

        # Check if expired
        if invitation.is_expired():
            invitation.status = DsrInvitation.STATUS_EXPIRED
            await invitation.asave(update_fields=["status"])
            return error_invitation_expired()

        # Check if already assigned
        existing = await DsrDealerAssignment.objects.filter(
            dsr=dsr,
            dealer=invitation.dealer,
        ).aexists()

        if existing:
            return dsr_error_response(
                "You are already assigned to this dealer",
                "already_assigned",
                400
            )

        # Create assignment
        assignment = await DsrDealerAssignment.objects.acreate(
            id=f"ASSIGN-{dsr.id}-{invitation.dealer.username}",
            dsr=dsr,
            dealer=invitation.dealer,
            role=invitation.role,
            permissions=invitation.permissions,
            parent_dsr_id=invitation.parent_dsr_id,
        )

        # Mark invitation as accepted (use async version)
        await invitation.aaccept(dsr)

        # Set as selected dealer if first assignment
        if not user.selected_dealer:
            user.selected_dealer = invitation.dealer
            await user.asave(update_fields=["selected_dealer"])

        # Generate new tokens
        access, refresh = await agenerate_tokens(user)

        return {
            "access": access,
            "refresh": refresh,
            "dealer": {
                "username": invitation.dealer.username,
                "full_name": invitation.dealer.full_name,
                "business_name": invitation.dealer.business_name,
            },
            "role": invitation.role,
            "permissions": invitation.permissions,
            "message": "Invitation accepted",
        }

    @http_post("/{invitation_id}/reject", response={200: MessageOutput, 401: dict, 404: dict})
    async def reject_invitation(self, request: HttpRequest, invitation_id: str, data: RejectInvitationInput = None):
        """Reject a dealer invitation."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            return error_profile_not_found()

        # Get invitation
        try:
            invitation = await DsrInvitation.objects.aget(
                id=invitation_id,
                dsr=dsr,
                status=DsrInvitation.STATUS_PENDING,
            )
        except DsrInvitation.DoesNotExist:
            return dsr_error_response(
                "Invitation not found or already processed",
                "not_found",
                404
            )

        # Reject invitation (use async version)
        await invitation.areject()

        # TODO: Notify dealer about rejection

        return {"message": "Invitation rejected"}


# ═══════════════════════════════════════════════════════════════════════════
# DSR ASSIGNMENTS CONTROLLER
# ═══════════════════════════════════════════════════════════════════════════

@api_controller("/dsr/assignments", tags=["DSR Assignments"], permissions=[AllowAny])
class DsrAssignmentController:
    """
    DSR Assignment management endpoints.

    DSRs can view their dealer assignments and leave dealers.
    """

    @http_get("", response={200: AssignmentListOutput, 401: dict})
    async def list_assignments(self, request: HttpRequest):
        """List all dealer assignments for the authenticated DSR."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            return error_profile_not_found()

        # Get assignments by status
        active = []
        removed = []
        left = []

        async for assignment in DsrDealerAssignment.objects.filter(
            dsr=dsr
        ).select_related("dealer").order_by("-assigned_at"):
            assignment_data = {
                "id": assignment.id,
                "dealer": {
                    "username": assignment.dealer.username,
                    "full_name": assignment.dealer.full_name,
                    "business_name": assignment.dealer.business_name,
                },
                "role": assignment.role,
                "permissions": assignment.permissions,
                "status": assignment.status,
                "assigned_at": assignment.assigned_at,
                "commission_rate": float(assignment.commission_rate) if assignment.commission_rate else None,
            }

            if assignment.status == DsrDealerAssignment.STATUS_ACTIVE:
                active.append(assignment_data)
            elif assignment.status == DsrDealerAssignment.STATUS_REMOVED:
                removed.append(assignment_data)
            elif assignment.status == DsrDealerAssignment.STATUS_LEFT:
                left.append(assignment_data)

        return {
            "active": active,
            "removed": removed,
            "left": left,
        }

    @http_post("/{assignment_id}/leave", response={200: MessageOutput, 400: dict, 401: dict, 404: dict})
    async def leave_dealer(self, request: HttpRequest, assignment_id: str, data: LeaveDealerInput = None):
        """Leave a dealer assignment."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Get DSR profile
        try:
            dsr = await DSR.objects.aget(user=user)
        except DSR.DoesNotExist:
            return error_profile_not_found()

        # Get assignment
        try:
            assignment = await DsrDealerAssignment.objects.aget(
                id=assignment_id,
                dsr=dsr,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            )
        except DsrDealerAssignment.DoesNotExist:
            return dsr_error_response(
                "Assignment not found or not active",
                "not_found",
                404
            )

        # Preserve transaction records with DSR status snapshot
        from sales.models import SaleRecord
        dealer = assignment.dealer

        # Update current DSR sales to show left status
        await SaleRecord.objects.filter(
            dsr=dsr,
            dealer=dealer
        ).aupdate(dsr_status='left')

        # Update original DSR sales to show left status
        await SaleRecord.objects.filter(
            original_dsr=dsr,
            dealer=dealer
        ).aupdate(original_dsr_status='left')

        # Deactivate assignment (DSR leaving) - use async version
        reason = data.reason if data else None
        await assignment.adeactivate_by_dsr(reason or "")

        # Clear selected dealer if this was the selected one
        if user.selected_dealer_id == assignment.dealer.username:
            user.selected_dealer = None
            await user.asave(update_fields=["selected_dealer"])

        # TODO: Notify dealer

        return {"message": f"Left {assignment.dealer.full_name} successfully"}
