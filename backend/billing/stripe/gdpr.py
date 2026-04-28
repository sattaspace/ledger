"""GDPR: Delete or anonymize a Stripe Customer.

Called when a user account is deleted or data must be erased per GDPR.
"""

import logging

from ..models import Subscription, SubscriptionStatus
from .client import (
    modify_customer,
    delete_customer,
    get_api_key,
)

logger = logging.getLogger(__name__)


def delete_or_anonymize_customer(user) -> bool:
    """Delete or anonymize the user's Stripe Customer.

    If any subscription is active/trialing, anonymizes instead of deleting.
    Returns True if action was taken, False if no customer found.
    """
    subs = (
        Subscription.objects.filter(user=user)
        .exclude(stripe_customer_id="")
        .exclude(stripe_customer_id__isnull=True)
    )
    if not subs.exists():
        return False

    customer_id = subs.first().stripe_customer_id
    has_active = subs.filter(
        status__in=(SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
    ).exists()

    try:
        if has_active:
            modify_customer(
                customer_id,
                email=f"deleted_{user.id}@redacted.com",
                name="Deleted User",
                metadata={
                    "gdpr_anonymized": "true",
                    "original_user_id": str(user.id),
                },
            )
            logger.info(f"Anonymized Stripe customer {customer_id}")
        else:
            delete_customer(customer_id)
            logger.info(f"Deleted Stripe customer {customer_id}")

        subs.update(stripe_customer_id="")
        return True

    except Exception as e:
        if "No such customer" in str(e):
            subs.update(stripe_customer_id="")
            return True
        raise
