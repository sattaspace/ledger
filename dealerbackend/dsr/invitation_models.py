"""
DEALERCORE v3.0 — DSR Invitation Models
-----------------------------------------
Invitation system for DSRs and Collectors to join dealers.

Supports:
- DSR self-registration (independent profiles)
- Dealer invitation with accept/reject
- Multi-dealer assignments with per-dealer permissions
- Removal with transaction record preservation
"""

import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone
from django.conf import settings

from dealer.models import DealerConfig


# Default permissions by role
DEFAULT_PERMISSIONS = {
    "DSR": {
        "dashboard": {"view": True},
        "inventory": {"view": True, "edit": False, "delete": False},
        "sales": {"view": True, "edit": True, "delete": False},
        "collections": {"view": True, "edit": False},
        "suppliers": {"view": False},
        "reports": {"view": True, "export": False},
        "print": False,
    },
    "Senior_DSR": {
        "dashboard": {"view": True},
        "inventory": {"view": True, "edit": True, "delete": False},
        "sales": {"view": True, "edit": True, "delete": True},
        "collections": {"view": True, "edit": True},
        "suppliers": {"view": True, "edit": False},
        "reports": {"view": True, "export": True},
        "print": True,
    },
    "Manager": {
        "dashboard": {"view": True},
        "inventory": {"view": True, "edit": True, "delete": True},
        "sales": {"view": True, "edit": True, "delete": True},
        "collections": {"view": True, "edit": True, "delete": True},
        "suppliers": {"view": True, "edit": True, "delete": False},
        "reports": {"view": True, "export": True},
        "print": True,
        "manage_dsrs": True,
    },
    "Collector": {
        "dashboard": {"view": True},
        "inventory": {"view": True, "edit": False, "delete": False},
        "sales": {"view": True, "edit": True, "delete": False},
        "collections": {"view": True, "edit": False},
        "suppliers": {"view": False},
        "reports": {"view": False},
        "print": False,
    },
}


class DsrInvitation(models.Model):
    """
    Invitation sent by a dealer to a DSR or Collector.
    
    Flow (New Design):
    ─────────────────────────────────────────────────────────────────
    1. DSR SELF-REGISTERS (independent profile)
       - DSR creates account at /dsr/register
       - Account created with no dealer assignments
       - DSR waits for dealer invitations
    
    2. DEALER SENDS INVITATION
       - Dealer searches by phone/email
       - IF DSR NOT REGISTERED: Send registration link with token
       - IF DSR REGISTERED: Send in-app notification
       - Create DsrInvitation record with offered permissions
    
    3. DSR RESPONDS
       - DSR can ACCEPT → Creates DsrDealerAssignment (status=active)
       - DSR can REJECT → Marks invitation as rejected
       - Notification sent to dealer about response
    
    4. DEALER CAN REVOKE pending invitations
    ─────────────────────────────────────────────────────────────────
    """
    
    # Status choices
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"  # NEW: DSR rejected invitation
    STATUS_EXPIRED = "expired"
    STATUS_REVOKED = "revoked"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),  # NEW
        (STATUS_EXPIRED, "Expired"),
        (STATUS_REVOKED, "Revoked"),
    ]
    
    # Role choices
    ROLE_DSR = "DSR"
    ROLE_SENIOR_DSR = "Senior_DSR"  # NEW
    ROLE_MANAGER = "Manager"  # NEW
    ROLE_COLLECTOR = "Collector"
    ROLE_CHOICES = [
        (ROLE_DSR, "DSR"),
        (ROLE_SENIOR_DSR, "Senior DSR"),  # NEW
        (ROLE_MANAGER, "Manager"),  # NEW
        (ROLE_COLLECTOR, "Order Collector"),
    ]
    
    id = models.CharField(max_length=100, primary_key=True)
    
    # From Dealer
    dealer = models.ForeignKey(
        DealerConfig,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        db_column="dealer_username",
    )
    
    # To DSR - identified by phone (primary) or email
    dsr_phone = models.CharField(
        max_length=20,
        db_index=True,
        default="",
        help_text="DSR phone number (primary identifier)",
    )
    dsr_email = models.EmailField(
        blank=True,
        default="",
        help_text="DSR email (optional, for notifications)",
    )
    
    # Link to existing DSR (if already registered)
    dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_invitations",
        db_column="dsr_id",
        help_text="Link to DSR if already registered",
    )
    
    # Role and permissions being offered
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_DSR,
    )
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Permissions being offered to this DSR",
    )
    
    # For collectors - parent DSR they report to
    parent_dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collector_invitations",
        db_column="parent_dsr_id",
    )
    
    # Invitation token (secure random string)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Expiry and status
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    
    # Tracking timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When DSR accepted/rejected",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    # Who accepted (links to DSR profile)
    accepted_by = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
        db_column="accepted_by_dsr_id",
    )
    
    # Optional message from dealer
    message = models.TextField(
        blank=True,
        default="",
        help_text="Personal message from dealer to DSR",
    )
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "DSR Invitation"
        verbose_name_plural = "DSR Invitations"
        indexes = [
            models.Index(fields=["dealer", "status"]),
            models.Index(fields=["dsr_phone", "status"]),
            models.Index(fields=["dsr_email", "status"]),
            models.Index(fields=["token"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["dsr", "status"]),
        ]
        constraints = [
            # One pending invitation per phone per dealer
            models.UniqueConstraint(
                fields=["dealer", "dsr_phone"],
                condition=models.Q(status="pending"),
                name="unique_pending_invitation_per_dealer_phone",
            ),
        ]
    
    def __str__(self):
        return f"Invitation to {self.dsr_phone} from {self.dealer.full_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Generate token and expiry on first save
        if not self.token:
            self.token = self._generate_token()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)  # 7 days expiry
        
        # Set default permissions based on role if not provided
        if not self.permissions and self.role in DEFAULT_PERMISSIONS:
            self.permissions = DEFAULT_PERMISSIONS[self.role].copy()
        
        super().save(*args, **kwargs)
    
    def _generate_token(self) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if invitation is valid (pending and not expired)"""
        return self.status == self.STATUS_PENDING and not self.is_expired()
    
    def expire(self):
        """Mark invitation as expired"""
        if self.status == self.STATUS_PENDING and self.is_expired():
            self.status = self.STATUS_EXPIRED
            self.save(update_fields=["status"])
    
    def accept(self, dsr):
        """Mark invitation as accepted by DSR"""
        self.status = self.STATUS_ACCEPTED
        self.accepted_at = timezone.now()
        self.responded_at = timezone.now()
        self.accepted_by = dsr
        self.dsr = dsr
        self.save(update_fields=["status", "accepted_at", "responded_at", "accepted_by", "dsr"])
    
    def reject(self):
        """Mark invitation as rejected by DSR"""
        self.status = self.STATUS_REJECTED
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "responded_at"])
    
    def revoke(self):
        """Revoke pending invitation by dealer"""
        if self.status == self.STATUS_PENDING:
            self.status = self.STATUS_REVOKED
            self.save(update_fields=["status"])


class DsrDealerAssignment(models.Model):
    """
    Junction table linking DSRs to Dealers with per-dealer permissions.
    
    This enables the multi-dealer architecture where:
    - A DSR can work for multiple dealers
    - Each dealer sets different permissions
    - DSR can accept/reject invitations
    - Removal preserves transaction records
    
    Status Flow:
    ─────────────────────────────────────────────────────────────────
    pending → active → removed (by dealer) OR left (by DSR)
    
    Records are never deleted - status changes preserve history.
    ─────────────────────────────────────────────────────────────────
    """
    
    # Status choices
    STATUS_PENDING = "pending"  # Invitation accepted, awaiting first login
    STATUS_ACTIVE = "active"    # Currently working
    STATUS_REMOVED = "removed"  # Dealer removed DSR
    STATUS_LEFT = "left"        # DSR left dealer
    
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_REMOVED, "Removed by Dealer"),
        (STATUS_LEFT, "Left by DSR"),
    ]
    
    id = models.CharField(max_length=100, primary_key=True)
    
    dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.CASCADE,
        related_name="dealer_assignments",
        db_column="dsr_id",
    )
    
    dealer = models.ForeignKey(
        DealerConfig,
        on_delete=models.CASCADE,
        related_name="dsr_assignments",
        db_column="dealer_username",
    )
    
    # Role and permissions (set by dealer)
    role = models.CharField(
        max_length=20,
        choices=DsrInvitation.ROLE_CHOICES,
        default=DsrInvitation.ROLE_DSR,
    )
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-dealer permissions for this DSR",
    )
    
    # For collectors - parent DSR
    parent_dsr = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinate_assignments",
        db_column="parent_dsr_id",
    )
    
    # Assignment status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Removal tracking
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Who initiated removal: 'dealer' or 'dsr'",
    )
    removal_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for removal/leaving",
    )
    
    # Commission/rate (optional)
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Commission percentage for this DSR with this dealer",
    )
    
    class Meta:
        ordering = ["-assigned_at"]
        verbose_name = "DSR Dealer Assignment"
        verbose_name_plural = "DSR Dealer Assignments"
        
        # Critical: One assignment per DSR-Dealer pair
        constraints = [
            models.UniqueConstraint(
                fields=["dsr", "dealer"],
                name="unique_dsr_dealer_assignment",
            ),
        ]
        
        indexes = [
            models.Index(fields=["dealer", "status", "role"]),
            models.Index(fields=["dsr", "status"]),
            models.Index(fields=["parent_dsr", "status"]),
        ]
    
    def __str__(self):
        status_display = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return f"{self.dsr.name} → {self.dealer.full_name} ({status_display})"
    
    def save(self, *args, **kwargs):
        # Set default permissions based on role if not provided
        if not self.permissions and self.role in DEFAULT_PERMISSIONS:
            self.permissions = DEFAULT_PERMISSIONS[self.role].copy()
        super().save(*args, **kwargs)
    
    @property
    def is_active(self) -> bool:
        """Check if assignment is currently active."""
        return self.status == self.STATUS_ACTIVE
    
    def activate(self):
        """Activate this assignment."""
        self.status = self.STATUS_ACTIVE
        self.activated_at = timezone.now()
        self.save(update_fields=["status", "activated_at"])
    
    def deactivate_by_dealer(self, reason: str = ""):
        """
        Deactivate by dealer (removal).
        Transaction records will be preserved with DSR name snapshot.
        """
        self.status = self.STATUS_REMOVED
        self.removed_at = timezone.now()
        self.removed_by = "dealer"
        self.removal_reason = reason
        self.save(update_fields=["status", "removed_at", "removed_by", "removal_reason"])
    
    def deactivate_by_dsr(self, reason: str = ""):
        """
        Deactivate by DSR (leaving).
        Transaction records will be preserved with DSR name snapshot.
        """
        self.status = self.STATUS_LEFT
        self.removed_at = timezone.now()
        self.removed_by = "dsr"
        self.removal_reason = reason
        self.save(update_fields=["status", "removed_at", "removed_by", "removal_reason"])
    
    def get_permissions(self) -> dict:
        """Get permissions for this assignment."""
        return self.permissions or DEFAULT_PERMISSIONS.get(self.role, {})
    
    def has_permission(self, module: str, action: str = "view") -> bool:
        """Check if DSR has specific permission."""
        perms = self.get_permissions()
        module_perms = perms.get(module, {})
        
        # Handle simple boolean permissions (like 'print')
        if isinstance(module_perms, bool):
            return module_perms
        
        # Handle nested permissions (like 'sales': {'view': True, 'edit': True})
        return module_perms.get(action, False)
