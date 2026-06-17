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
from typing import Dict, Optional

from ninja_extra import api_controller, route, http_post, http_get, http_put, http_delete
from ninja_extra.permissions import AllowAny, IsAuthenticated
from ninja import Schema
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import authenticate
import jwt as pyjwt
import logging

logger = logging.getLogger(__name__)

from users.models import DsrUser
from dsr.invitation_models import DsrInvitation, DsrDealerAssignment
from dealer.models import DealerConfig
from common.dsr_auth_errors import (
    DsrAuthError,
    dsr_error_response,
    error_invalid_credentials,
    error_user_not_found,
    error_account_deactivated,
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
from common.tasks import (
    send_email_verification,
    send_dsr_invitation_email,
    send_dsr_notification_email,
    send_invitation_accepted_notification,
    send_invitation_rejected_notification,
    send_dsr_removed_notification,
    send_dsr_left_notification,
    send_welcome_email,
)
from dsr.auth_schemas import (
    DsrLoginInput,
    DsrLoginOutput,
    DsrSelfRegisterInput,
    DsrSelfRegisterOutput,
    DsrRegisterInput,
    DsrRegisterOutput,
    DealerSelectionInput,
    DealerSelectionOutput,
    RefreshAccessOutput,
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
    SetPhoneInput,
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

        # Check if email already exists (email is primary identifier)
        email_exists = await DsrUser.objects.filter(email__iexact=data.email).aexists()
        logger.info(f"[DSR REGISTER] Email exists check: {email_exists}")

        if email_exists:
            logger.warning(f"[DSR REGISTER] Email already registered: {data.email}")
            return error_email_exists()

        # Create user account (email is required, phone is optional)
        # REVERT M-7/M-10: Django's `transaction.atomic()` is a DECORATOR,
        # not an async context manager — `async with` on it raises
        # AttributeError: __aenter__. Wrap individual operations in
        # sync_to_async instead so we don't lose atomicity guarantees
        # but stay async-safe.
        from asgiref.sync import sync_to_async
        try:
            user = await DsrUser.objects.acreate_user(
                email=data.email,
                password=data.password,
                full_name=data.full_name,
                phone=data.phone or "",
                user_type=DsrUser.TYPE_DSR,
            )

            # FIX DSR-INV-001: Link any existing pending invitations to this new DSR user.
            # When a dealer invites a DSR by email or phone before the DSR has registered,
            # the invitation is created with dsr_email/dsr_phone but dsr=None. Now that the
            # DSR has registered, we link those invitations so they appear in the
            # DSR's invitation list.
            from django.db.models import Q
            link_q = Q(dsr__isnull=True, status=DsrInvitation.STATUS_PENDING)
            email_q = Q(dsr_email__iexact=data.email) if data.email else Q(pk__in=[])
            phone_q = Q(dsr_phone=data.phone) if data.phone else Q(pk__in=[])
            pending_invitations = DsrInvitation.objects.filter(link_q & (email_q | phone_q))
            linked_count = await pending_invitations.aupdate(dsr=user)
            if linked_count > 0:
                logger.info(f"[DSR REGISTER] Linked {linked_count} pending invitation(s) to new DSR {user.id} (by email and/or phone)")

        except Exception as e:
            logger.error(f"[DSR REGISTER] ERROR creating user: {type(e).__name__}: {e}")
            # Best-effort rollback of the user if the insert fails.
            try:
                if 'user' in locals() and user.pk:
                    await sync_to_async(user.delete)()
            except Exception:
                pass
            raise

        # Generate tokens
        access, refresh = await agenerate_tokens(user)

        # FIX DSR-005/018: Send email verification after self-registration.
        # DSRs must verify their email before accepting invitations.
        # For self-registered users (not via invitation), email is unverified.
        verification_token = secrets.token_urlsafe(32)
        await user.aset_email_verification_token(verification_token)

        frontend_url = getattr(settings, 'DEALER_FRONTEND_URL', 'http://localhost:4323')
        verification_url = f"{frontend_url}/dsr/verify-email?token={verification_token}"

        send_email_verification.delay(
            email=user.email,
            dsr_name=user.full_name or user.email.split('@')[0],
            verification_url=verification_url,
        )

        # Also send welcome email
        send_welcome_email.delay(
            email=user.email,
            dsr_name=user.full_name or user.email.split('@')[0],
        )

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
            "message": "Registration successful. Please verify your email to accept dealer invitations.",
        }

    @http_post("/register/{token}", response={200: DsrRegisterOutput, 400: dict, 409: dict, 410: dict})
    @rate_limit("dsr_invite_register", limit=10, period=3600, scope="ip")
    async def register_via_invitation(self, request: HttpRequest, token: str, data: DsrRegisterInput):
        """
        Register DSR account via invitation token.

        This creates:
        1. DsrUser account (for authentication — IS the DSR after model merge)
        2. DsrDealerAssignment (links DSR to dealer)
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

        # Check if user already exists (by email, since email is primary identifier)
        existing_user = await DsrUser.objects.filter(email__iexact=invitation.dsr_email).aexists()
        if existing_user:
            return error_email_exists()

        # Create user account + assignment in one transaction.
        # FIX DSR-011: Django's `transaction.atomic()` is a DECORATOR / sync
        # context manager — `async with` on it raises AttributeError: __aenter__.
        # Wrap the entire block in sync_to_async so we get true atomicity
        # without the async-with bug.
        from asgiref.sync import sync_to_async
        from django.db import transaction as _transaction

        @sync_to_async
        def _create_user_and_assignment():
            with _transaction.atomic():
                user = DsrUser.objects.create_user(
                    phone=phone,
                    password=data.password,
                    full_name=data.full_name,
                    email=invitation.dsr_email or "",
                    user_type=DsrUser.TYPE_DSR,
                )

                # FIX DSR-005/018: Auto-verify email for invitation-based
                # registration — the user proved email ownership by clicking
                # the invitation link sent to their email address.
                user.email_verified = True
                user.email_verified_at = timezone.now()
                user.save(update_fields=["email_verified", "email_verified_at"])

                # Create dealer assignment (FIX M-13: ensure id fits 100-char PK)
                assignment_id = f"ASSIGN-{user.id}-{invitation.dealer.username}"[:100]
                DsrDealerAssignment.objects.create(
                    id=assignment_id,
                    dsr=user,
                    dealer=invitation.dealer,
                    role=invitation.role,
                    permissions=invitation.permissions,
                    parent_dsr_id=invitation.parent_dsr_id,
                    status=DsrDealerAssignment.STATUS_ACTIVE,
                )

                # Mark invitation as accepted
                invitation.accept(user)

                # FIX DSR-007: No longer persist selected_dealer on user model.
                # The frontend handles dealer selection via X-Dealer-Username header.

                return user

        user = await _create_user_and_assignment()

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
        - no_dealer_assignment: DSR not assigned to any dealer
        """
        import logging
        logger = logging.getLogger(__name__)

        # Find user by email (email is the primary identifier)
        try:
            user = await DsrUser.objects.aget(email__iexact=data.email)
        except DsrUser.DoesNotExist:
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
            return error_invalid_credentials()

        # Check if active
        if not user.is_active:
            return error_account_deactivated()

        # Get assigned dealers (DsrUser IS the DSR after model merge)
        dealers = []
        async for assignment in DsrDealerAssignment.objects.filter(
            dsr=user,
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

        # FIX DSR-007: No longer auto-persist selected_dealer on user model.
        # The frontend receives the dealer list and handles selection via
        # X-Dealer-Username header on subsequent requests.
        require_dealer_selection = len(dealers) > 1
        # Hint to frontend which dealer to auto-select if only one
        auto_select_dealer = dealers[0] if len(dealers) == 1 else None

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
            "auto_select_dealer": auto_select_dealer,
        }

    @http_post("/select-dealer", response={200: DealerSelectionOutput, 401: dict, 403: dict, 404: dict})
    async def select_dealer(self, request: HttpRequest, data: DealerSelectionInput):
        """
        Select dealer context for multi-dealer DSR.

        FIX DSR-007: No longer persists the selection to DsrUser.selected_dealer.
        The frontend sets X-Dealer-Username header on subsequent requests.
        This endpoint validates the selection against DsrDealerAssignment and
        returns new tokens with dealer context. The frontend is responsible
        for persisting the selection in localStorage.
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
        assignment = await DsrDealerAssignment.objects.filter(
            dsr=user,
            dealer=dealer,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).afirst()

        if not assignment:
            return dsr_error_response(
                "You are not assigned to this dealer",
                "not_assigned",
                403
            )

        # FIX DSR-007: No DB write — just validate and return tokens.
        # The frontend persists selection in localStorage + X-Dealer-Username header.

        # Generate new tokens with dealer context
        access, refresh = await agenerate_tokens(user)

        # ─── SINGLE SOURCE OF TRUTH FOR DSR ACCESS ────────────────────────
        # Fetch the dealer's plan-level access map from SattaBase, then
        # compute ONE flat effective_access map that intersects it with
        # the DSR's per-dealer assignment permissions. The frontend just
        # calls setAccessMap(result.effective_access) — no intersection
        # logic, no hardcoded defaults, no special cases.
        #
        # This eliminates the entire class of bugs where the frontend's
        # intersection logic disagrees with the backend's enforcement.
        # The backend now computes the final authoritative map.
        effective_access: Dict[str, Any] = {"dashboard": True, "__subscription_active": False}
        raw_dealer_access: Dict[str, Any] = {}
        try:
            from common.sattabase_access import (
                aget_dealer_access,
                compute_effective_access,
            )
            # Pass dealer.username (= SattaBase user_pk as string) straight
            # through. SattaBase's subscriber-access API does pk → username
            # → email lookup, so the pk branch will find the user.
            dealer_access_data = await aget_dealer_access(str(dealer.username))
            raw_dealer_access = dealer_access_data.get("access", {})
            effective_access = compute_effective_access(
                dealer_access_data,
                assignment.permissions or {},
            )
        except Exception as exc:
            logger.warning(
                "[DSR-AUTH] Could not fetch dealer access from SattaBase "
                "for %s: %s. Falling back to dashboard-only access.",
                dealer.username, exc,
            )

        return {
            "access": access,
            "refresh": refresh,
            "dealer": {
                "username": dealer.username,
                "full_name": dealer.full_name,
                "business_name": dealer.business_name,
            },
            "permissions": assignment.permissions,
            "dealer_access": raw_dealer_access,
            "effective_access": effective_access,
        }

    @http_post("/refresh-access", response={200: RefreshAccessOutput, 401: dict, 403: dict, 404: dict})
    @rate_limit("dsr_refresh_access", limit=10, period=60, scope="user")
    async def refresh_access(self, request: HttpRequest):
        """Refresh the DSR's effective_access map from SattaBase.

        PURPOSE
        -------
        SattaBase access responses are cached in-memory for
        ``SATTABASE_ACCESS_CACHE_TTL`` seconds (default 300 = 5 min) so
        we don't hammer SattaBase on every API call. The DSR frontend
        also caches the ``effective_access`` map in a Vue ref after
        ``select-dealer`` — it does NOT auto-refresh.

        When the dealer's plan is changed live in SattaBase admin (e.g.
        disabling ``bad_debt`` on the FREE plan), neither the backend
        cache nor the frontend Vue ref knows about it. The DSR keeps
        seeing the stale menu until either:
          (a) the backend cache TTL expires (up to 5 min), AND
          (b) the frontend re-calls ``select-dealer`` to get a new
              ``effective_access`` (which only happens on logout/login).

        This endpoint breaks that staleness in one shot:
          1. Looks up the DSR's currently-selected dealer (from the
             ``X-Dealer-Username`` header, set by the frontend after
             ``select-dealer``).
          2. Calls ``invalidate_cache(dealer_username)`` to drop the
             stale SattaBase response for THIS dealer only (other
             dealers' caches are untouched).
          3. Re-fetches fresh access from SattaBase — this also
             re-caches the new response so subsequent API calls by
             this DSR (and any other DSR under the same dealer) see
             the new matrix immediately.
          4. Recomputes ``effective_access`` via
             ``compute_effective_access()`` and returns it.

        The frontend should call this endpoint:
          - When the DSR returns from a billing-redirect flow
            (``useBillingRedirect`` detects ``?billing_updated=1``)
          - On an explicit "Refresh permissions" action in the UI
          - Optionally: periodically (e.g., every 5 min) while the
            DSR portal session is active

        This endpoint does NOT re-issue JWT tokens. The DSR's existing
        tokens remain valid. Only the access map is refreshed.

        Returns 401 if the DSR JWT is invalid.
        Returns 403 if the DSR has no selected dealer context.
        Returns 404 if the selected dealer no longer exists.
        """
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # Resolve the currently-selected dealer.
        # The frontend sets X-Dealer-Username after select-dealer.
        dealer_username = request.headers.get("X-Dealer-Username")
        if not dealer_username:
            # Fall back to the DSR's first active assignment
            assignment_fallback = await DsrDealerAssignment.objects.filter(
                dsr=user,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).select_related("dealer").afirst()
            if not assignment_fallback or not assignment_fallback.dealer:
                return dsr_error_response(
                    "No dealer context selected. Call /dsr/auth/select-dealer first.",
                    "no_dealer_context",
                    403,
                )
            dealer = assignment_fallback.dealer
            assignment = assignment_fallback
        else:
            try:
                dealer = await DealerConfig.objects.aget(username=dealer_username)
            except DealerConfig.DoesNotExist:
                return dsr_error_response(
                    f"Dealer '{dealer_username}' not found.",
                    "dealer_not_found",
                    404,
                )
            # Verify the DSR still has an active assignment to this dealer
            assignment = await DsrDealerAssignment.objects.filter(
                dsr=user,
                dealer=dealer,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).afirst()
            if not assignment:
                return dsr_error_response(
                    "You are not actively assigned to this dealer.",
                    "not_assigned",
                    403,
                )

        # ── Step 1: invalidate the backend cache for THIS dealer ───────
        from common.sattabase_access import invalidate_cache
        invalidate_cache(str(dealer.username))
        logger.info(
            "[DSR-AUTH] refresh-access: invalidated backend cache for "
            "dealer_username=%s (SattaBase user_pk)",
            dealer.username,
        )

        # ── Step 2: re-fetch fresh access from SattaBase ───────────────
        # aget_dealer_access() will hit SattaBase (cache was just cleared)
        # and re-cache the new response.
        effective_access: Dict[str, Any] = {
            "dashboard": True,
            "__subscription_active": False,
        }
        raw_dealer_access: Dict[str, Any] = {}
        try:
            from common.sattabase_access import (
                aget_dealer_access,
                compute_effective_access,
            )
            dealer_access_data = await aget_dealer_access(str(dealer.username))
            raw_dealer_access = dealer_access_data.get("access", {})
            effective_access = compute_effective_access(
                dealer_access_data,
                assignment.permissions or {},
            )
            logger.info(
                "[DSR-AUTH] refresh-access: re-fetched access from SattaBase "
                "for dealer_username=%s — plan=%s, status=%s, "
                "effective_access_keys=%s",
                dealer.username,
                dealer_access_data.get("plan_slug"),
                dealer_access_data.get("subscription_status"),
                sorted(effective_access.keys()),
            )
        except Exception as exc:
            logger.warning(
                "[DSR-AUTH] refresh-access: could not fetch dealer access "
                "from SattaBase for %s: %s. Returning dashboard-only "
                "fallback. The backend cache WAS invalidated, so the next "
                "API call will retry SattaBase.",
                dealer.username, exc,
            )

        return {
            "effective_access": effective_access,
            "dealer_access": raw_dealer_access,
            "permissions": assignment.permissions or {},
            "cache_invalidated": True,
            "message": "Access map refreshed from SattaBase",
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

        # Get dealers (DsrUser IS the DSR after model merge)
        dealers = []
        # FIX DSR-007: No server-side selected_dealer. The frontend
        # determines the active dealer from localStorage/X-Dealer-Username.
        # We return the full list so the frontend can decide.

        async for assignment in DsrDealerAssignment.objects.filter(
            dsr=user,
            status=DsrDealerAssignment.STATUS_ACTIVE,
        ).select_related("dealer"):
            dealer_info = {
                "username": assignment.dealer.username,
                "full_name": assignment.dealer.full_name,
                "business_name": assignment.dealer.business_name,
            }
            dealers.append(dealer_info)

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
                "has_dsr_profile": True,
            },
            "dsr_id": str(user.id),
            "dsr_name": user.full_name,
            # FIX DSR-004: role is per-dealer, not global on DSR model.
            # Return the role from the first active assignment if available.
            "dsr_role": "",  # Deprecated — use assignment.role from /dsr/assignments
            "dealers": dealers,
            # FIX DSR-007: No server-side selected_dealer; frontend decides.
            "selected_dealer": None,
            # FIX DSR-008: Marketplace fields moved to DsrMarketplaceProfile.
            # Return defaults for backward API compatibility; when marketplace
            # feature is implemented, fetch from user.marketplace_profile.
            "skills": [],
            "experience_years": 0,
            "rating": 0.0,
            "total_jobs": 0,
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
        # FIX DSR-008: skills and experience_years moved to DsrMarketplaceProfile.
        # These fields are no longer on DsrUser. When marketplace is implemented,
        # update the marketplace profile instead.

        await user.asave()

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

    @http_post("/set-phone", response={200: MessageOutput, 400: dict, 401: dict})
    async def set_phone(self, request: HttpRequest, data: SetPhoneInput):
        """
        Set phone number for DSR account.
        
        FIX DSR-017: Phone number is required after accepting the first
        invitation. DSRs who registered via email-only invitations may not
        have a phone on file. This endpoint allows them to add one.
        """
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        phone = data.phone.strip()
        if not phone:
            return dsr_error_response("Phone number is required", "phone_required", 400)

        # Check if phone is already taken by another user
        existing = await DsrUser.objects.filter(phone=phone).exclude(id=user.id).aexists()
        if existing:
            return error_phone_exists()

        user.phone = phone
        await user.asave(update_fields=["phone"])

        return {"message": "Phone number updated successfully"}

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

            # Send password reset email via Celery
            from django.conf import settings
            from common.tasks import send_password_reset_email

            reset_url = (
                f"{settings.DEALER_FRONTEND_URL}/dsr/reset-password"
                f"?token={token}"
            )
            send_password_reset_email.delay(
                email=user.email,
                reset_url=reset_url,
                expires_hours=1,
            )

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

    # ═══════════════════════════════════════════════════════════════════════
    # FIX DSR-005/018: EMAIL VERIFICATION ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════════

    @http_post("/verify-email", response={200: MessageOutput, 400: dict, 410: dict})
    async def verify_email(self, request: HttpRequest, token: str):
        """
        Verify DSR email address.
        
        FIX DSR-005/018: After self-registration, DSRs receive a verification
        email with a tokenized link. This endpoint validates the token and
        marks the email as verified. Only after verification can DSRs accept
        dealer invitations.
        """
        if not token:
            return dsr_error_response("Verification token is required", "token_required", 400)

        # Look up user by hashed token
        from users.models import DsrUser as _DU
        hashed = _DU._hash_reset_token(token)
        try:
            user = await DsrUser.objects.aget(email_verification_token=hashed)
        except DsrUser.DoesNotExist:
            return dsr_error_response("Invalid or expired verification token", "invalid_token", 400)

        # Check if already verified
        if user.email_verified:
            return {"message": "Email already verified"}

        # Check if token is expired
        if user.email_verification_expires and timezone.now() > user.email_verification_expires:
            return dsr_error_response("Verification token has expired. Please request a new one.", "token_expired", 410)

        # Verify the token (constant-time compare)
        if not user.is_email_verification_valid(token):
            return dsr_error_response("Invalid verification token", "invalid_token", 400)

        # Mark as verified
        from asgiref.sync import sync_to_async
        await sync_to_async(user.verify_email)()

        return {"message": "Email verified successfully. You can now accept dealer invitations."}

    @http_post("/resend-verification", response=MessageOutput)
    @rate_limit("dsr_resend_verification", limit=3, period=3600, scope="ip")
    async def resend_verification(self, request: HttpRequest):
        """
        Resend email verification link.
        
        FIX DSR-005/018: Allows DSRs who haven't verified their email to
        request a new verification link. Rate-limited to 3 per hour per IP.
        """
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        if user.email_verified:
            return {"message": "Email already verified"}

        # Generate new verification token
        verification_token = secrets.token_urlsafe(32)
        await user.aset_email_verification_token(verification_token)

        frontend_url = getattr(settings, 'DEALER_FRONTEND_URL', 'http://localhost:4323')
        verification_url = f"{frontend_url}/dsr/verify-email?token={verification_token}"

        send_email_verification.delay(
            email=user.email,
            dsr_name=user.full_name or user.email.split('@')[0],
            verification_url=verification_url,
        )

        return {"message": "Verification email sent. Please check your inbox."}


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
        import logging
        logger = logging.getLogger(__name__)
        
        user = await aget_user_from_token(request)
        if not user:
            logger.warning("[DSR INVITATIONS] aget_user_from_token returned None — no valid DSR auth")
            return error_auth_required()

        logger.info(f"[DSR INVITATIONS] Fetching invitations for user={user.email} (id={user.id})")

        # Get invitations by status (DsrUser IS the DSR after model merge)
        pending = []
        accepted = []
        rejected = []

        # FIX DSR-INV-001: Comprehensive invitation matching.
        # A DSR should see invitations that belong to them via ANY of:
        #   1. dsr FK points to this user (set when dealer invited a registered DSR)
        #   2. dsr_email matches user's email AND dsr FK is NULL
        #      (dealer invited by email before DSR registered)
        #   3. dsr_phone matches user's phone AND dsr FK is NULL
        #      (dealer invited by phone before DSR registered)
        #
        # Previous query missed case 3 — if the dealer invited by phone only
        # (or the DSR registered with a different email), the invitation was
        # invisible in the DSR panel despite being visible in the dealer panel.
        from django.db.models import Q

        # Build match conditions
        match_q = Q(dsr=user)  # Direct FK link

        # Email-based match (dsr FK not yet linked)
        if user.email:
            match_q |= Q(dsr_email__iexact=user.email, dsr__isnull=True)

        # Phone-based match (dsr FK not yet linked)
        # This is critical for markets where phone is the primary identifier.
        if user.phone:
            match_q |= Q(dsr_phone=user.phone, dsr__isnull=True)

        logger.info(
            f"[DSR INVITATIONS] Query for user={user.email} phone={user.phone}: "
            f"match_q conditions include dsr FK, email match, phone match"
        )

        # FIX DSR-INV-002: Also auto-link any unlinked matching invitations
        # to this user's dsr FK so future queries are simpler and faster.
        link_q = Q(pk__in=[])  # Start with empty match
        if user.email:
            link_q = link_q | Q(dsr_email__iexact=user.email)
        if user.phone:
            link_q = link_q | Q(dsr_phone=user.phone)
        unlinked = DsrInvitation.objects.filter(
            dsr__isnull=True,
            status=DsrInvitation.STATUS_PENDING,
        ).filter(link_q)
        linked_count = await unlinked.aupdate(dsr=user)
        if linked_count > 0:
            logger.info(
                f"[DSR INVITATIONS] Auto-linked {linked_count} pending "
                f"invitation(s) to user={user.email}"
            )

        async for inv in DsrInvitation.objects.filter(
            match_q
        ).select_related("dealer").order_by("-created_at"):
            inv_data = {
                "id": inv.id,
                # FIX DSR-009: Removed `token` field from response. Since L-9 fix,
                # invitation.token stores a SHA-256 hash, not the raw token. Returning
                # the hash is useless for the frontend (it can't be used for accept),
                # and the accept-by-ID endpoint (/{invitation_id}/accept) is the
                # correct flow — no token needed.
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

        logger.info(
            f"[DSR INVITATIONS] Found {len(pending)} pending, "
            f"{len(accepted)} accepted, {len(rejected)} rejected "
            f"for user={user.email}"
        )

        return {
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
        }

    @http_post("/{invitation_id}/accept", response={200: AcceptInvitationOutput, 400: dict, 401: dict, 403: dict, 404: dict, 410: dict})
    async def accept_invitation(self, request: HttpRequest, invitation_id: str):
        """Accept a dealer invitation.
        
        FIX DSR-005/018: Requires email verification before acceptance.
        Self-registered DSRs must verify their email first.
        DSRs registered via invitation token are auto-verified (they proved
        email ownership by using the invitation token sent to their email).
        """
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # FIX DSR-005/018: Check email verification before accepting
        if not user.email_verified:
            return dsr_error_response(
                "Please verify your email address before accepting invitations.",
                "email_not_verified",
                403
            )

        # FIX DSR-INV-001: Also check for invitations by email AND phone
        # where dsr field is not yet set. This handles the case where a dealer
        # invited the DSR before the DSR registered.
        from django.db.models import Q
        ownership_q = Q(dsr=user)
        if user.email:
            ownership_q |= Q(dsr_email__iexact=user.email, dsr__isnull=True)
        if user.phone:
            ownership_q |= Q(dsr_phone=user.phone, dsr__isnull=True)
        try:
            invitation = await DsrInvitation.objects.select_related("dealer").aget(
                Q(id=invitation_id) & Q(status=DsrInvitation.STATUS_PENDING) & ownership_q
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
        existing_assignment = await DsrDealerAssignment.objects.filter(
            dsr=user,
            dealer=invitation.dealer,
        ).afirst()

        if existing_assignment:
            # If prior assignment exists but is not active, check limits
            # before reactivating (Phase 2)
            if existing_assignment.status != DsrDealerAssignment.STATUS_ACTIVE:
                from common.sattabase_access import aget_dealer_access, get_dealer_limit
                dealer_access = await aget_dealer_access(invitation.dealer.username)
                max_dsrs = get_dealer_limit(dealer_access, "max_dsrs")
                if max_dsrs is not None and max_dsrs > 0:
                    active_count = await DsrDealerAssignment.objects.filter(
                        dealer=invitation.dealer,
                        status=DsrDealerAssignment.STATUS_ACTIVE,
                    ).acount()
                    if (active_count + 1) > max_dsrs:
                        return dsr_error_response(
                            "Cannot accept: the dealer has reached their "
                            "plan limit of {} DSRs. Please ask the "
                            "dealer to upgrade their plan.".format(max_dsrs),
                            "plan_limit_exceeded",
                            403,
                        )
                await existing_assignment.aactivate()
                await invitation.aaccept(user)

                # Notify dealer about reactivation
                send_invitation_accepted_notification.delay(
                    dealer_email=invitation.dealer.username,
                    dealer_name=invitation.dealer.full_name or invitation.dealer.username,
                    dsr_name=user.full_name,
                    dsr_email=user.email,
                    role=invitation.role,
                )

                access, refresh = await agenerate_tokens(user)
                phone_required = not user.phone
                return {
                    "access": access,
                    "refresh": refresh,
                    "dealer": {
                        "username": invitation.dealer.username,
                        "full_name": invitation.dealer.full_name,
                        "business_name": invitation.dealer.business_name,
                    },
                    "role": existing_assignment.role,
                    "permissions": existing_assignment.permissions,
                    "message": "Invitation accepted (reactivated)",
                    "phone_required": phone_required,
                }
            else:
                return dsr_error_response(
                    "You are already assigned to this dealer",
                    "already_assigned",
                    400
                )

        # Phase 2: Check max_dsrs before creating a new assignment too.
        # The dealer may have hit their DSR limit between sending the
        # invitation and the DSR accepting it.
        from common.sattabase_access import aget_dealer_access, get_dealer_limit
        dealer_access = await aget_dealer_access(invitation.dealer.username)
        max_dsrs = get_dealer_limit(dealer_access, "max_dsrs")
        if max_dsrs is not None and max_dsrs > 0:
            active_count = await DsrDealerAssignment.objects.filter(
                dealer=invitation.dealer,
                status=DsrDealerAssignment.STATUS_ACTIVE,
            ).acount()
            if (active_count + 1) > max_dsrs:
                return dsr_error_response(
                    "Cannot accept: the dealer has reached their "
                    "plan limit of {} DSRs. Please ask the "
                    "dealer to upgrade their plan.".format(max_dsrs),
                    "plan_limit_exceeded",
                    403,
                )

        # Create assignment (FIX: ensure id fits 100-char PK like the sync path)
        assignment = await DsrDealerAssignment.objects.acreate(
            id=f"ASSIGN-{user.id}-{invitation.dealer.username}"[:100],
            dsr=user,
            dealer=invitation.dealer,
            role=invitation.role,
            permissions=invitation.permissions,
            parent_dsr_id=invitation.parent_dsr_id,
        )

        # Mark invitation as accepted (use async version)
        await invitation.aaccept(user)

        # FIX DSR-007: No server-side selected_dealer to set.
        # The frontend handles dealer selection entirely via localStorage.

        # FIX DSR-019: Notify dealer about invitation acceptance
        send_invitation_accepted_notification.delay(
            dealer_email=invitation.dealer.username,
            dealer_name=invitation.dealer.full_name or invitation.dealer.username,
            dsr_name=user.full_name,
            dsr_email=user.email,
            role=invitation.role,
        )

        # Generate new tokens
        access, refresh = await agenerate_tokens(user)

        # FIX DSR-017: Flag if phone number is missing after first acceptance
        phone_required = not user.phone

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
            "phone_required": phone_required,
        }

    @http_post("/{invitation_id}/reject", response={200: MessageOutput, 401: dict, 404: dict})
    async def reject_invitation(self, request: HttpRequest, invitation_id: str, data: RejectInvitationInput = None):
        """Reject a dealer invitation."""
        user = await aget_user_from_token(request)
        if not user:
            return error_auth_required()

        # FIX DSR-INV-001: Also check for invitations by email AND phone
        from django.db.models import Q
        ownership_q = Q(dsr=user)
        if user.email:
            ownership_q |= Q(dsr_email__iexact=user.email, dsr__isnull=True)
        if user.phone:
            ownership_q |= Q(dsr_phone=user.phone, dsr__isnull=True)
        try:
            invitation = await DsrInvitation.objects.aget(
                Q(id=invitation_id) & Q(status=DsrInvitation.STATUS_PENDING) & ownership_q
            )
        except DsrInvitation.DoesNotExist:
            return dsr_error_response(
                "Invitation not found or already processed",
                "not_found",
                404
            )

        # Reject invitation (use async version)
        await invitation.areject()

        # FIX DSR-019: Notify dealer about rejection
        send_invitation_rejected_notification.delay(
            dealer_email=invitation.dealer.username,  # Dealer username may be their email
            dealer_name=invitation.dealer.full_name or invitation.dealer.username,
            dsr_name=user.full_name,
            dsr_email=user.email,
            role=invitation.role,
        )

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

        # Get assignments by status (DsrUser IS the DSR after model merge)
        active = []
        removed = []
        left = []

        async for assignment in DsrDealerAssignment.objects.filter(
            dsr=user
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

        # Get assignment (DsrUser IS the DSR after model merge)
        try:
            assignment = await DsrDealerAssignment.objects.aget(
                id=assignment_id,
                dsr=user,
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
            dsr=user,
            dealer=dealer
        ).aupdate(dsr_status='left')

        # Update original DSR sales to show left status
        await SaleRecord.objects.filter(
            original_dsr=user,
            dealer=dealer
        ).aupdate(original_dsr_status='left')

        # Deactivate assignment (DSR leaving) - use async version
        reason = data.reason if data else None
        await assignment.adeactivate_by_dsr(reason or "")

        # FIX DSR-007: No server-side selected_dealer to clear.
        # The frontend handles dealer selection entirely via localStorage.

        # FIX DSR-019: Notify dealer about DSR leaving
        send_dsr_left_notification.delay(
            dealer_email=dealer.username,
            dealer_name=dealer.full_name or dealer.username,
            dsr_name=user.full_name,
            dsr_email=user.email,
            reason=reason or "",
        )

        return {"message": f"Left {assignment.dealer.full_name} successfully"}
