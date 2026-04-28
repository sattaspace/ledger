"""Webhook handler for checkout.session.completed."""

import logging

from ....models import Plan
from ...client import ts_to_dt
from ..sync import sync_subscription_from_stripe

logger = logging.getLogger(__name__)


def handle_checkout_completed(event: dict) -> None:
    """Activate local subscription after Stripe checkout payment."""
    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    product_slug = metadata.get("product_slug")
    plan_slug = metadata.get("plan_slug")

    if not all([user_id, product_slug, plan_slug]):
        logger.warning(
            f"checkout.session.completed missing metadata: {session.get('id')}"
        )
        return

    stripe_sub_id = session.get("subscription")
    if not stripe_sub_id:
        logger.warning(f"checkout.session.completed no sub ID: {session.get('id')}")
        return

    # Sync from Stripe — the single source of truth
    try:
        sync_subscription_from_stripe(stripe_sub_id)
    except Exception as e:
        logger.error(f"Failed to sync subscription after checkout: {e}")
