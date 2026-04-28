"""Webhook handlers for charge.refunded and customer.updated."""

import logging

from ....models import Subscription, Refund, RefundStatus
from ...client import ts_to_dt

logger = logging.getLogger(__name__)


def handle_charge_refunded(event: dict) -> None:
    """Create local Refund record from Stripe-initiated refund."""
    charge = event["data"]["object"]
    charge_id = charge.get("id")
    refunds = charge.get("refunds") or {}
    refund_data = (refunds.get("data") or [None])[0] if refunds else None

    if not refund_data or not refund_data.get("id"):
        logger.info(f"charge.refunded {charge_id}: no refund object")
        return

    refund_id = refund_data["id"]
    payment_intent_id = charge.get("payment_intent")
    if not payment_intent_id:
        return

    # Avoid duplicate
    if Refund.objects.filter(stripe_refund_id=refund_id).exists():
        return

    # Find subscription (best effort — link via user)
    sub = Subscription.objects.filter(stripe_subscription_id__isnull=False).first()
    if not sub:
        return

    Refund.objects.create(
        subscription=sub,
        stripe_refund_id=refund_id,
        stripe_charge_id=payment_intent_id,
        amount_cents=refund_data.get("amount", 0),
        currency=charge.get("currency", "USD"),
        reason=f"Refund via Stripe Dashboard (charge {charge_id})",
        status=(
            RefundStatus.COMPLETED
            if refund_data.get("status") == "succeeded"
            else RefundStatus.PENDING
        ),
        initiated_by=None,
        stripe_response=refund_data,
    )
    logger.info(f"Refund record created: {refund_id}")


def handle_customer_updated(event: dict) -> None:
    """Sync Stripe customer data changes to local user."""
    customer = event["data"]["object"]
    customer_id = customer.get("id")
    if not customer_id:
        return

    try:
        sub = (
            Subscription.objects.select_for_update()
            .filter(stripe_customer_id=customer_id)
            .first()
        )
        if not sub:
            return

        user = sub.user
        updated = False

        email = customer.get("email")
        if email and email != user.email:
            user.email = email
            updated = True

        name = customer.get("name")
        if name:
            parts = name.strip().split(" ", 1)
            if parts[0] and parts[0] != user.first_name:
                user.first_name = parts[0]
                updated = True
            if len(parts) > 1 and parts[1] != user.last_name:
                user.last_name = parts[1]
                updated = True

        metadata = customer.get("metadata") or {}
        currency = (
            metadata.get("preferred_currency") if isinstance(metadata, dict) else None
        )
        if currency and hasattr(user, "currency"):
            choices = [
                c[0]
                for c in getattr(
                    user.__class__, "CurrencyChoices", type("C", (), {"choices": ()})
                )
            ]
            if currency in choices and currency != user.currency:
                user.currency = currency
                updated = True

        if updated:
            user.save()
            logger.info(f"Customer synced from webhook for user {user.id}")

    except Exception as e:
        logger.error(f"customer.updated sync failed for {customer_id}: {e}")
