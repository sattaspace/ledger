"""
DEALERCORE v3.0 — DSR ID Generator
------------------------------------
Shared utility for generating consistent DSR IDs across the system.

FIX DSR-015: Previously, DSR IDs were generated inconsistently:
- self_register used: DSR-{uuid_prefix} (e.g., DSR-A1B2C3D4)
- api.py used: dsr-{incremental_number} (e.g., dsr-5)

This made it hard to identify DSR records by their ID format and
created the impression of two separate DSR "species" in the system.

The standardized format is: DSR-{UUID_PREFIX} (uppercase, 8 chars)
This format is unique, collision-resistant, and consistent.
"""

import uuid


def generate_dsr_id() -> str:
    """
    Generate a standardized DSR ID.

    Format: DSR-{8-char uppercase hex from UUID4}

    Example: DSR-A1B2C3D4

    The UUID4 prefix provides:
    - Uniqueness without DB sequence dependency
    - No race conditions (unlike incremental IDs)
    - Consistent format regardless of creation path
    - Easy to identify as a DSR record

    Returns:
        str: A unique DSR ID in the format DSR-XXXXXXXX
    """
    return f"DSR-{uuid.uuid4().hex[:8].upper()}"
