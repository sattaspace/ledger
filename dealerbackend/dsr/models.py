"""
DEALERCORE v3.0 — DSR App Models
-----------------------------------
Daily Sales Representatives and Order Collectors.

DSR Model Merge (DSR → DsrUser):
  The separate DSR model has been merged into DsrUser. This eliminates
  the redundant one-to-one relationship where DSR stored profile data
  (name, phone, email) that duplicated DsrUser fields.

  Before: DsrUser (auth) ←1:1→ DSR (profile) ←→ Dealer (via DsrDealerAssignment)
  After:  DsrUser (auth + profile) ←→ Dealer (via DsrDealerAssignment)

  All FK references that previously pointed to "dsr.DSR" now point to
  "users.DsrUser". Hierarchy (parent_dsr) and role are per-dealer,
  stored on DsrDealerAssignment.

Exports:
  DsrInvitation, DsrDealerAssignment (re-exported from invitation_models)
"""

# Re-export invitation models — these are the only models in the DSR app now.
# The DSR model class has been removed; DsrUser replaces it.
from .invitation_models import DsrInvitation, DsrDealerAssignment

__all__ = ["DsrInvitation", "DsrDealerAssignment"]
