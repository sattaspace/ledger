"""Webhook handlers for invoice.* events."""

import logging

from ....models import Subscription, SubscriptionStatus
from ...client import ts_to_dt

logger = logging.getLogger(__name__)


def handle_invoice_payment_succeeded(event: dict) -> None:
    """Mark past_due subscriptions as active on successful payment."""
    invoice = event["data"]["object"]
    stripe_sub_id = invoice.get("subscription")
    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.select_for_update().get(
            stripe_subscription_id=stripe_sub_id
        )
    except Subscription.DoesNotExist:
        return

    if sub.status == SubscriptionStatus.PAST_DUE:
        sub.status = SubscriptionStatus.ACTIVE

    sub.current_period_start = ts_to_dt(invoice.get("period_start"))
    sub.current_period_end = ts_to_dt(invoice.get("period_end"))
    sub.save()

    logger.info(f"Payment succeeded: sub={sub.id}")


def handle_invoice_payment_failed(event: dict) -> None:
    """Mark subscription as past_due."""
    invoice = event["data"]["object"]
    stripe_sub_id = invoice.get("subscription")
    if not stripe_sub_id:
        return

    try:
        sub = Subscription.objects.select_for_update().get(
            stripe_subscription_id=stripe_sub_id
        )
    except Subscription.DoesNotExist:
        return

    sub.status = SubscriptionStatus.PAST_DUE
    sub.save()

    next_retry = ts_to_dt(invoice.get("next_payment_attempt"))
    logger.warning(
        f"Payment failed: sub={sub.id}, attempt={invoice.get('attempt_count', 1)}, "
        f"next_retry={next_retry}"
    )


def handle_invoice_created(event: dict) -> None:
    """Log invoice creation for audit trail."""
    invoice = event["data"]["object"]
    logger.info(
        f"Invoice created: {invoice.get('number')} ({invoice.get('id')}), "
        f"amount_due={invoice.get('amount_due', 0) / 100:.2f} "
        f"{invoice.get('currency', 'USD').upper()}"
    )
