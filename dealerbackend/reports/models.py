"""
DEALERCORE v3.0 — Reports App Models
--------------------------------------
Reports are computed views — no dedicated database models needed.
All data is aggregated from inventory, sales, dsr, and dealer apps.

This module intentionally has no models.
The schemas.py contains Pydantic response models for the computed data.
The api.py contains the view logic using Django ORM annotations/aggregations.
"""
