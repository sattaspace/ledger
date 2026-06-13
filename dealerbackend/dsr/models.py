"""
DEALERCORE v3.0 — DSR App Models
-----------------------------------
Daily Sales Representatives and Order Collectors.

Relationships:
  DSR → DSR (self-referencing: parent_dsr for OC hierarchy)
  DSR ←── SaleRecord (FK: dsr, defined in sales app)
  DSR ←→ Dealer (many-to-many via DsrDealerAssignment)
  DSR ←── DsrInvitation

Exports:
  DSR, DsrInvitation, DsrDealerAssignment
"""

# Re-export invitation models
from .invitation_models import DsrInvitation, DsrDealerAssignment

from django.db import models


class DSR(models.Model):
    """DSR (Daily Sales Representative) or Order Collector.
    Self-referential FK for OC → parent DSR hierarchy.
    
    The DSR model stores the profile/record data.
    Authentication is handled by the related DsrUser.
    """

    ROLE_DSR = "DSR"
    ROLE_OC = "Order Collector"
    ROLE_CHOICES = [
        (ROLE_DSR, "DSR"),
        (ROLE_OC, "Order Collector"),
    ]

    id = models.CharField(max_length=100, primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_DSR)

    # Link to user account for authentication
    # One DSR has one user account (optional - legacy DSRs may not have one)
    user = models.OneToOneField(
        "users.DsrUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dsr_profile",
        help_text="User account for login (null for legacy DSRs)",
    )
    
    # Email stored for reference (synced from user account if linked)
    email = models.EmailField(blank=True, default="")

    # Self-referential FK for hierarchy (OC reports to a parent DSR)
    parent_dsr = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subordinates",
        db_column="parent_dsr_id",
    )
    parent_dsr_name = models.CharField(max_length=255, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "DSR"
        verbose_name_plural = "DSRs"
        indexes = [
            # For hierarchy lookups
            models.Index(fields=["parent_dsr", "role"]),
            # For role-based filtering
            models.Index(fields=["role"]),
            # For user lookup
            models.Index(fields=["user"]),
            # For email lookup
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.role})"
    
    def sync_from_user(self):
        """Sync profile data from linked user account."""
        if self.user:
            self.email = self.user.email
            self.name = self.user.full_name or self.name
            self.phone = self.user.phone or self.phone
            self.save(update_fields=["email", "name", "phone"])
    
    @property
    def has_account(self) -> bool:
        """Check if this DSR has a user account (can log in)."""
        return self.user is not None
