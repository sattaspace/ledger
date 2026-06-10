"""
DEALERCORE v3.0 — Dealer Schemas (Pydantic)
---------------------------------------------
Uses ninja.ModelSchema for output.
Custom input schema for settings update.
All schemas use camelCase alias for frontend compatibility.
"""

from typing import Optional

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel

from ninja import Schema, ModelSchema

from dealer.models import DealerConfig

# ─── Shared Config ──────────────────────────────────────────
_CAMEL_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
)


# ─── Model-based Output Schema ──────────────────────────────

class DealerConfigOut(ModelSchema):
    """Dealer configuration — fully auto-generated from DealerConfig model."""

    model_config = _CAMEL_CONFIG

    class Meta:
        model = DealerConfig
        fields = [
            "username", "full_name", "role",
            "business_name", "address", "phone_number", "email",
            "gst_number", "google_map_url", "communication_number",
            "default_currency", "default_locale",
        ]


# ─── Custom Input Schema ────────────────────────────────────

class UpdateDealerIn(Schema):
    """Update dealer settings. `username` is the lookup key."""

    model_config = _CAMEL_CONFIG

    username: str
    full_name: Optional[str] = None
    role: Optional[str] = None
    business_name: Optional[str] = None
    address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    gst_number: Optional[str] = None
    google_map_url: Optional[str] = None
    communication_number: Optional[str] = None
    default_currency: str = "INR"
    default_locale: str = "en-IN"


class CreateDealerIn(Schema):
    """Create a new dealer config."""

    model_config = _CAMEL_CONFIG

    username: str
    full_name: str
    role: str = "Dealer"
    business_name: str = ""
    address: str = ""
    phone_number: str = ""
    email: str = ""
    gst_number: str = ""
    google_map_url: str = ""
    communication_number: str = ""
    default_currency: str = "INR"
    default_locale: str = "en-IN"
