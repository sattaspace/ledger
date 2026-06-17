"""
DEALERCORE v3.0 — DSR Authentication Schemas
----------------------------------------------
Request/Response schemas for DSR authentication endpoints.

Supports:
- Email-based authentication (primary)
- Phone for contact (optional)
- Self-registration (independent profile)
- Invitation accept/reject
- Dealer assignment management
"""

from ninja import Schema
from typing import Optional, List, Dict, Any
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# LOGIN SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class DsrLoginInput(Schema):
    """DSR login credentials - email + password."""
    email: str
    password: str


class DealerChoice(Schema):
    """Dealer info for selection UI."""
    username: str
    full_name: str
    business_name: str = ""


class DsrUserOutput(Schema):
    """DSR user profile."""
    id: str
    email: str
    phone: str = ""
    user_type: str
    full_name: str
    avatar_url: str = ""
    phone_verified: bool = False
    email_verified: bool = False
    created_at: datetime
    # has_dsr_profile removed after DSR→DsrUser merge: every DsrUser IS a DSR,
    # so the field would always be True and is meaningless.


class DsrLoginOutput(Schema):
    """DSR login response with tokens and dealer choices."""
    access: str
    refresh: str
    user: DsrUserOutput
    dealers: List[DealerChoice] = []
    require_dealer_selection: bool = False
    awaiting_invitation: bool = False  # True if DSR has no dealer assignments
    message: str = "Login successful"


# ═══════════════════════════════════════════════════════════════════════════
# SELF-REGISTRATION SCHEMAS (New - Independent Profile)
# ═══════════════════════════════════════════════════════════════════════════

class DsrSelfRegisterInput(Schema):
    """DSR self-registration (no invitation required)."""
    email: str  # Required - primary identifier
    password: str
    full_name: str
    phone: Optional[str] = None  # Optional - for contact


class DsrSelfRegisterOutput(Schema):
    """DSR self-registration response."""
    access: str
    refresh: str
    user: DsrUserOutput
    message: str = "Registration successful. You can now receive dealer invitations."


# ═══════════════════════════════════════════════════════════════════════════
# INVITATION REGISTRATION SCHEMAS (Existing - Via Invitation Token)
# ═══════════════════════════════════════════════════════════════════════════

class DsrRegisterInput(Schema):
    """DSR registration via invitation token."""
    token: str
    full_name: str
    password: str
    phone: Optional[str] = None  # Override phone from invitation


class DsrRegisterOutput(Schema):
    """DSR registration response."""
    access: str
    refresh: str
    user: DsrUserOutput
    dealer: DealerChoice
    role: str
    message: str = "Registration successful"


# ═══════════════════════════════════════════════════════════════════════════
# INVITATION MANAGEMENT SCHEMAS (New)
# ═══════════════════════════════════════════════════════════════════════════

class InvitationOutput(Schema):
    """Invitation details for DSR to view.
    
    FIX DSR-INV-004: token field was required but never returned by the
    list_invitations endpoint (removed in FIX DSR-009). This schema
    mismatch caused Django Ninja to throw a validation error on every
    GET /dsr/invitations call, which the frontend silently caught as
    an empty invitation list — making invitations invisible in the DSR panel.
    """
    id: str
    token: Optional[str] = None  # FIX DSR-INV-004: Made optional (never returned)
    dealer: DealerChoice
    role: str
    permissions: Dict[str, Any] = {}
    message: str = ""
    created_at: datetime
    expires_at: datetime
    status: str


class InvitationListOutput(Schema):
    """List of invitations for DSR."""
    pending: List[InvitationOutput]
    accepted: List[InvitationOutput]
    rejected: List[InvitationOutput]


class AcceptInvitationOutput(Schema):
    """Accept invitation response."""
    access: str
    refresh: str
    dealer: DealerChoice
    role: str
    permissions: Dict[str, Any]
    message: str = "Invitation accepted"
    # FIX DSR-017: Flag indicating phone number is required
    phone_required: bool = False


class SetPhoneInput(Schema):
    """FIX DSR-017: Set phone number (required after first invitation acceptance)."""
    phone: str


class RejectInvitationInput(Schema):
    """Reject invitation input."""
    reason: Optional[str] = None


class MessageOutput(Schema):
    """Generic message response."""
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# DEALER SELECTION SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class DealerSelectionInput(Schema):
    """Select dealer context for multi-dealer DSR."""
    dealer_username: str


class DealerSelectionOutput(Schema):
    """Dealer selection response with updated tokens.

    The ``effective_access`` field is the SINGLE SOURCE OF TRUTH for the
    DSR's portal session — it's the backend-computed intersection of:

    1. The dealer's plan-level access (from SattaBase's AccessEntry table)
    2. The DSR's per-dealer assignment permissions (from DsrDealerAssignment)

    The frontend should call ``setAccessMap(result.effective_access)``
    and STOP doing any intersection logic client-side.

    ``dealer_access`` (raw SattaBase access map) and ``permissions`` (raw
    DSR assignment permissions) are kept for debugging/inspection only —
    do NOT use them for UI gating. Use ``effective_access`` instead.
    """
    access: str
    refresh: str
    dealer: DealerChoice
    permissions: Dict[str, Any] = {}
    dealer_access: Dict[str, Any] = {}
    effective_access: Dict[str, Any] = {}
    message: str = "Dealer context updated"


# ═══════════════════════════════════════════════════════════════════════════
# PROFILE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class DsrProfileOutput(Schema):
    """DSR profile with user info and assignments.
    
    After DSR→DsrUser merge:
      dsr_id   → str(user.id) (UUID)
      dsr_name → user.full_name
      dsr_role → from DsrDealerAssignment.role (per-dealer)
    """
    user: DsrUserOutput
    dsr_id: Optional[str] = None  # str(user.id) — UUID from DsrUser
    dsr_name: str = ""            # user.full_name from DsrUser
    dsr_role: str = ""           # from DsrDealerAssignment.role
    dealers: List[DealerChoice] = []
    # FIX DSR-007: selected_dealer is now None (legacy field kept for API compat).
    # Frontend determines selected dealer from localStorage.
    selected_dealer: Optional[DealerChoice] = None
    skills: List[str] = []
    experience_years: int = 0
    rating: float = 0.0
    total_jobs: int = 0


class UpdateProfileInput(Schema):
    """Update DSR profile."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    # FIX DSR-008: skills and experience_years removed from UpdateProfileInput.
    # These fields now live on DsrMarketplaceProfile. When the marketplace
    # feature is implemented, add a separate marketplace profile update endpoint.


# ═══════════════════════════════════════════════════════════════════════════
# ASSIGNMENT MANAGEMENT SCHEMAS (New)
# ═══════════════════════════════════════════════════════════════════════════

class AssignmentOutput(Schema):
    """DSR-Dealer assignment details."""
    id: str
    dealer: DealerChoice
    role: str
    permissions: Dict[str, Any] = {}
    status: str
    assigned_at: datetime
    commission_rate: Optional[float] = None


class AssignmentListOutput(Schema):
    """List of assignments for DSR."""
    active: List[AssignmentOutput]
    removed: List[AssignmentOutput]
    left: List[AssignmentOutput]


class LeaveDealerInput(Schema):
    """DSR leaving dealer input."""
    reason: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════
# PASSWORD RESET SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class PasswordResetRequestInput(Schema):
    """Request password reset via phone or email."""
    phone_or_email: str


class PasswordResetConfirmInput(Schema):
    """Confirm password reset with OTP/token."""
    token: str
    new_password: str


class ChangePasswordInput(Schema):
    """Change password (authenticated)."""
    current_password: str
    new_password: str


# ═══════════════════════════════════════════════════════════════════════════
# TOKEN REFRESH SCHEMA
# ═══════════════════════════════════════════════════════════════════════════

class TokenRefreshInput(Schema):
    """Refresh token input."""
    refresh: str


class TokenRefreshOutput(Schema):
    """Token refresh response."""
    access: str
    refresh: Optional[str] = None
    message: str = "Token refreshed"


# ═══════════════════════════════════════════════════════════════════════════
# ACCESS MATRIX REFRESH SCHEMA
# ═══════════════════════════════════════════════════════════════════════════

class RefreshAccessOutput(Schema):
    """Response for POST /dsr/auth/refresh-access.

    Re-fetches the dealer's plan-level access map from SattaBase
    (bypassing the in-memory cache), recomputes the effective_access
    intersection with the DSR's per-dealer permissions, and returns
    the new effective_access map.

    IMPORTANT — why this endpoint exists:
    The backend caches SattaBase access responses for ``SATTABASE_ACCESS_CACHE_TTL``
    seconds (default 300 = 5 minutes) to avoid hammering SattaBase on every
    API call. When the dealer's plan is changed live in SattaBase admin
    (e.g., disabling ``bad_debt`` for the FREE plan), DealerBackend keeps
    serving the stale cached access map until the TTL expires.

    On the frontend, the DSR's ``effective_access`` is computed ONCE at
    ``select-dealer`` time and stored in a Vue ref (in-memory). It does
    NOT auto-refresh when SattaBase's access matrix changes.

    This endpoint breaks that staleness:
      1. Calls ``invalidate_cache(dealer_username)`` to drop the cached
         SattaBase response for this dealer.
      2. Calls ``aget_dealer_access()`` again — this hits SattaBase fresh
         and re-caches the new response.
      3. Recomputes ``effective_access`` via ``compute_effective_access()``.
      4. Returns the new map so the frontend can ``setAccessMap()``.

    The frontend should call this endpoint:
      - When the DSR returns from a billing-redirect flow
        (``useBillingRedirect`` detects ``?billing_updated=1``)
      - On an explicit "Refresh permissions" action
      - Optionally: periodically (e.g., every 5 minutes) while the
        DSR portal session is active

    Note: this endpoint does NOT re-issue JWT tokens. The DSR's existing
    tokens remain valid. Only the access map is refreshed.
    """
    effective_access: Dict[str, Any] = {}
    dealer_access: Dict[str, Any] = {}
    permissions: Dict[str, Any] = {}
    cache_invalidated: bool = True
    message: str = "Access map refreshed from SattaBase"


# ═══════════════════════════════════════════════════════════════════════════
# DEALER-SIDE SCHEMAS (For dealer to manage DSRs)
# ═══════════════════════════════════════════════════════════════════════════

class DealerInviteDsrInput(Schema):
    """Dealer inviting a DSR."""
    dsr_email: str  # Required - primary identifier
    dsr_phone: Optional[str] = None  # Optional - for contact
    role: str = "DSR"
    permissions: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    parent_dsr_id: Optional[str] = None  # For collectors


class DealerInviteOutput(Schema):
    """Dealer invitation response.
    
    FIX H-20: token field is no longer returned in the response body for
    security reasons. The raw token only lives in the registration URL
    (sent via email). Keeping the field as Optional for API backward compat.
    """
    id: str
    dsr_email: str
    dsr_phone: str = ""
    role: str
    status: str
    token: Optional[str] = None  # FIX H-20: no longer returned (was security risk)
    expires_at: datetime
    registration_url: Optional[str] = None
    message: str = "Invitation sent"


class DealerDsrListOutput(Schema):
    """List of DSRs for a dealer."""
    active: List[Dict[str, Any]]
    pending_invitations: List[Dict[str, Any]]
    removed: List[Dict[str, Any]]


class RemoveDsrInput(Schema):
    """Dealer removing DSR input."""
    reason: Optional[str] = None
    # FIX DSR-010: Optional DSR to reassign active sales to.
    # If not provided, sales are left with dsr_status='removed' and
    # the dealer must manually reassign them later.
    reassign_to_dsr_id: Optional[str] = None


class UpdateDsrPermissionsInput(Schema):
    """Dealer updating DSR permissions."""
    role: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    commission_rate: Optional[float] = None
