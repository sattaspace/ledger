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
    Self-referential FK for OC → parent DSR hierarchy."""

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
        ]

    def __str__(self):
        return f"{self.name} ({self.role})"
