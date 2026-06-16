"""
DEALERCORE v3.0 — DSR Schemas (Pydantic)
------------------------------------------
All schemas use camelCase alias for frontend compatibility.
Custom schema needed for DSROut because of computed active_sales_count.

After DSR→DsrUser merge, these schemas are populated from DsrUser fields:
  id   → str(user.id)    (UUID)
  name → user.full_name
  phone → user.phone
  role → from DsrDealerAssignment (per-dealer)
  parent_dsr_id / parent_dsr_name → from DsrDealerAssignment.parent_dsr
"""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


# ─── Extended schema with computed field ─────────────────────

class DSROut(Schema):
    """DSR response with computed active_sales_count annotation.
    
    Populated from DsrUser (after DSR model merge):
      id   → str(user.id) (UUID)
      name → user.full_name
      phone → user.phone
    
    FIX DSR-004: `role` field is now deprecated. The role shown here comes
    from the DsrDealerAssignment (per-dealer). If no assignment context is
    available, defaults to "DSR".
    """

    model_config = _CAMEL_CONFIG

    id: str
    name: str
    phone: str
    active_sales_count: int = 0
    role: str = "DSR"  # FIX DSR-004: populated from assignment, not DsrUser.user_type
    parent_dsr_id: Optional[str] = None
    parent_dsr_name: str = ""


# ─── Custom Input Schema ────────────────────────────────────

class CreateDSRIn(Schema):
    """Create a new DSR or Order Collector."""

    model_config = _CAMEL_CONFIG

    name: str
    phone: str
    role: Optional[str] = "DSR"
    parent_dsr_id: Optional[str] = None


class UpdateDSRIn(Schema):
    """Partial update on a DSR — all fields optional (PATCH semantics).
    
    FIX DSR-004: `role` field removed from DSR model update. Role changes
    should be done via DsrDealerAssignment update (PUT /dealer/dsr/assignments/{id}).
    """

    model_config = _CAMEL_CONFIG

    name: Optional[str] = None
    phone: Optional[str] = None
    parent_dsr_id: Optional[str] = None
