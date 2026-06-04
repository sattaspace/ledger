"""
DEALERCORE v3.0 — Dealer Schemas (Pydantic)
---------------------------------------------
Request/Response schemas for Dealer configuration endpoints.
"""

from __future__ import annotations

from ninja import Schema


class DealerConfigOut(Schema):
    """Dealer configuration response."""

    username: str
    full_name: str
    role: str = "Dealer"
    default_currency: str = "INR"
    default_locale: str = "en-IN"

    class Config:
        from_attributes = True


class UpdateDealerIn(Schema):
    """Update dealer settings. `username` is the lookup key."""

    username: str
    default_currency: str = "INR"
    default_locale: str = "en-IN"
