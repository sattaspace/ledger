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
    has_dsr_profile: bool = False


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
    """Invitation details for DSR to view."""
    id: str
    token: str
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
    """Dealer selection response with updated tokens."""
    access: str
    refresh: str
    dealer: DealerChoice
    permissions: Dict[str, Any] = {}
    message: str = "Dealer context updated"


# ═══════════════════════════════════════════════════════════════════════════
# PROFILE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════

class DsrProfileOutput(Schema):
    """DSR profile with user info and assignments."""
    user: DsrUserOutput
    dsr_id: Optional[str] = None
    dsr_name: str = ""
    dsr_role: str = ""
    dealers: List[DealerChoice] = []
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
    skills: Optional[List[str]] = None
    experience_years: Optional[int] = None


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
    """Dealer invitation response."""
    id: str
    dsr_email: str
    dsr_phone: str = ""
    role: str
    status: str
    token: str
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


class UpdateDsrPermissionsInput(Schema):
    """Dealer updating DSR permissions."""
    role: Optional[str] = None
    permissions: Optional[Dict[str, Any]] = None
    commission_rate: Optional[float] = None
