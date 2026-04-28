"""Stripe Customer Portal session creation."""

import logging

from django.conf import settings

from .customer import find_customer_id
from .client import create_portal_session as _create_portal

logger = logging.getLogger(__name__)


def create_portal(user, return_url: str = None) -> str:
    """Create a Stripe Customer Portal session.  Returns the portal URL.

    Raises:
        ValueError: If user has no Stripe customer.
    """
    customer_id = find_customer_id(user)
    if not customer_id:
        raise ValueError("No Stripe customer found.  Complete a checkout first.")

    _return_url = return_url or getattr(settings, "STRIPE_PORTAL_RETURN_URL", "")

    session = _create_portal(
        customer_id=customer_id,
        return_url=_return_url,
    )

    logger.info(f"Portal session {session['id']} for {user.email}")
    return session["url"]
