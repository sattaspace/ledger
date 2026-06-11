"""
DEALERCORE v3.0 — DSR Invitation Models
-----------------------------------------
Invitation system for DSRs and Collectors to join dealers.
Enables multi-dealer support where DSRs can work for multiple dealers.
"""

import secrets
from datetime import timedelta
from django.db import models
from django.utils import timezone

from dealer.models import DealerConfig
# from dsr.models import DSR


class DsrInvitation(models.Model):
    """
    Invitation sent by a dealer to a DSR or Collector.
    
    Flow:
    1. Dealer creates invitation with email and role
    2. Invitation email sent to DSR with secure token link
    3. DSR clicks link → redirected to accept page
    4. If new user: redirected to SattaBase registration
    5. If existing user: invitation linked immediately
    6. DsrDealerAssignment created upon acceptance
    """
    
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_EXPIRED = "expired"
    STATUS_REVOKED = "revoked"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_REVOKED, "Revoked"),
    ]
    
    ROLE_DSR = "DSR"
    ROLE_COLLECTOR = "Collector"
    ROLE_CHOICES = [
        (ROLE_DSR, "DSR"),
        (ROLE_COLLECTOR, "Order Collector"),
    ]
    
    id = models.CharField(max_length=100, primary_key=True)
    dealer = models.ForeignKey(
        DealerConfig,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        db_column="dealer_username",
    )
    
    # Recipient info
    email = models.EmailField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_DSR)
    
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
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        "dsr.DSR",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
        db_column="accepted_by_dsr_id",
    )
    
    # Optional message from dealer
    message = models.TextField(blank=True, default="")
    
    class Meta:
        ordering = ["-created_at"]
        verbose_name = "DSR Invitation"
        verbose_name_plural = "DSR Invitations"
        indexes = [
            models.Index(fields=["dealer", "status"]),
            models.Index(fields=["email", "status"]),
            models.Index(fields=["token"]),
            models.Index(fields=["expires_at"]),
        ]
        constraints = [
            # One pending invitation per email per dealer
            models.UniqueConstraint(
                fields=["dealer", "email"],
                condition=models.Q(status="pending"),
                name="unique_pending_invitation_per_dealer_email",
            ),
        ]
    
    def __str__(self):
        return f"Invitation to {self.email} from {self.dealer.full_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        # Generate token and expiry on first save
        if not self.token:
            self.token = self._generate_token()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)  # 7 days expiry
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
        """Mark invitation as accepted"""
        self.status = self.STATUS_ACCEPTED
        self.accepted_at = timezone.now()
        self.accepted_by = dsr
        self.save(update_fields=["status", "accepted_at", "accepted_by"])
    
    def revoke(self):
        """Revoke pending invitation"""
        if self.status == self.STATUS_PENDING:
            self.status = self.STATUS_REVOKED
            self.save(update_fields=["status"])


class DsrDealerAssignment(models.Model):
    """
    Junction table linking DSRs to Dealers.
    
    This enables the multi-dealer architecture where:
    - A DSR can work for multiple dealers
    - Each dealer has their own DSR list
    - Sales are attributed to the dealer-dealer pair
    
    This replaces the direct FK from DSR to Dealer.
    """
    
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
    
    # Role-specific info
    role = models.CharField(
        max_length=20,
        choices=DsrInvitation.ROLE_CHOICES,
        default=DsrInvitation.ROLE_DSR,
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
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
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
            models.Index(fields=["dealer", "is_active", "role"]),
            models.Index(fields=["dsr", "is_active"]),
            models.Index(fields=["parent_dsr", "is_active"]),
        ]
    
    def __str__(self):
        return f"{self.dsr.name} → {self.dealer.full_name} ({self.role})"
    
    def deactivate(self):
        """Deactivate this assignment"""
        self.is_active = False
        self.save(update_fields=["is_active"])
    
    def activate(self):
        """Reactivate this assignment"""
        self.is_active = True
        self.save(update_fields=["is_active"])
