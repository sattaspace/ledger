"""billing.stripe — Clean public API for Stripe integration.

Controllers and tasks should ONLY import from this package.
Never import from submodules directly — this is the stable interface.

Usage in controllers::

    from billing.stripe import (
        create_checkout,
        confirm_checkout,
        create_portal,
        get_or_create_customer_id,
        sync_customer_to_local,
        cancel_subscription_on_stripe,
        update_subscription_plan_on_stripe,
        reactivate_subscription_on_stripe,
        get_proration_preview,
        create_stripe_refund,
        get_transaction_history,
        delete_or_anonymize_customer,
        verify_and_parse_webhook,
        record_webhook_event,
        process_webhook_event,
        reconcile_unprocessed_webhooks,
    )
"""

import logging
from typing import Optional

from ..models import Plan, Subscription
from .client import (
    retrieve_subscription,
    modify_subscription,
    retrieve_invoice,
    list_invoices,
    retrieve_upcoming_invoice,
    get_first_item_id,
    get_subscription_currency,
    create_refund,
    get_api_key,
    ts_to_dt,
    get_subscription_items,
)
from .prices import resolve_price_id
from .customer import (
    get_or_create_customer_id,
    sync_customer_to_local,
    find_customer_id,
)
from .checkout import create_checkout, confirm_checkout
from .portal import create_portal
from .gdpr import delete_or_anonymize_customer
from .webhooks.router import (
    verify_and_parse as verify_and_parse_webhook,
    record_event as record_webhook_event,
    process_event as process_webhook_event,
    reconcile_unprocessed as reconcile_unprocessed_webhooks,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Subscription management (thin wrappers over client + prices)
# ---------------------------------------------------------------------------


def cancel_subscription_on_stripe(subscription: Subscription) -> None:
    """Set cancel_at_period_end=True on Stripe."""
    if not subscription.stripe_subscription_id:
        return
    modify_subscription(
        subscription.stripe_subscription_id,
        cancel_at_period_end=True,
    )
    logger.info(
        f"Cancelled Stripe sub {subscription.stripe_subscription_id} at period end"
    )


def update_subscription_plan_on_stripe(
    subscription: Subscription,
    new_plan: Plan,
    proration_behavior: str = "create_prorations",
) -> None:
    """Swap the plan price on an existing Stripe subscription.

    Uses the existing subscription's currency for the new price.
    """
    if not subscription.stripe_subscription_id:
        return

    sub_dict = retrieve_subscription(subscription.stripe_subscription_id)
    currency = get_subscription_currency(sub_dict)
    item_id = get_first_item_id(sub_dict)

    if not item_id:
        logger.warning(f"Stripe sub {subscription.stripe_subscription_id} has no items")
        return

    price_id = resolve_price_id(new_plan, currency)

    modify_subscription(
        subscription.stripe_subscription_id,
        cancel_at_period_end=False,
        items=[{"id": item_id, "price": price_id}],
        metadata={
            "plan_slug": new_plan.slug,
            "product_slug": new_plan.product.slug,
        },
        proration_behavior=proration_behavior,
    )
    logger.info(
        f"Updated Stripe sub {subscription.stripe_subscription_id} "
        f"-> {new_plan.slug} (currency={currency})"
    )


def reactivate_subscription_on_stripe(
    subscription: Subscription,
    new_plan: Plan,
) -> None:
    """Remove cancel_at_period_end and swap plan price on Stripe.

    Uses the existing subscription's currency for the new price.
    """
    if not subscription.stripe_subscription_id:
        raise ValueError("No Stripe subscription to reactivate.")

    sub_dict = retrieve_subscription(subscription.stripe_subscription_id)
    currency = get_subscription_currency(sub_dict)
    item_id = get_first_item_id(sub_dict)

    if not item_id:
        raise ValueError("Stripe subscription has no items.")

    price_id = resolve_price_id(new_plan, currency)

    modify_subscription(
        subscription.stripe_subscription_id,
        cancel_at_period_end=False,
        items=[{"id": item_id, "price": price_id}],
        metadata={
            "plan_slug": new_plan.slug,
            "product_slug": new_plan.product.slug,
            "user_id": str(subscription.user.id),
        },
        proration_behavior="create_prorations",
    )
    logger.info(
        f"Reactivated Stripe sub {subscription.stripe_subscription_id} "
        f"-> {new_plan.slug} (currency={currency})"
    )


# ---------------------------------------------------------------------------
# Proration preview
# ---------------------------------------------------------------------------


def get_proration_preview(subscription: Subscription, new_plan: Plan) -> dict:
    """Preview proration for a plan change."""
    if not subscription.stripe_subscription_id:
        raise ValueError("No Stripe subscription — cannot preview.")

    sub_dict = retrieve_subscription(subscription.stripe_subscription_id)
    currency = get_subscription_currency(sub_dict)
    item_id = get_first_item_id(sub_dict)

    if not item_id:
        raise ValueError("Stripe subscription has no items.")

    price_id = resolve_price_id(new_plan, currency)

    preview = retrieve_upcoming_invoice(
        customer=subscription.stripe_customer_id,
        subscription=subscription.stripe_subscription_id,
        subscription_items=[{"id": item_id, "price": price_id}],
    )

    preview_currency = preview.get("currency", currency) or currency
    return {
        "subtotal": (preview.get("subtotal_excluding_tax") or 0) / 100,
        "tax": (preview.get("tax") or 0) / 100,
        "total": (preview.get("total") or 0) / 100,
        "next_billing": (preview.get("amount_due") or 0) / 100,
        "currency": preview_currency.upper(),
    }


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


def create_stripe_refund(subscription, amount_cents=None, reason="", initiated_by=None):
    """Create a Stripe refund for the latest payment on a subscription."""
    from ..models import Refund, RefundStatus
    import time as _time

    if not subscription.stripe_subscription_id:
        raise ValueError("No Stripe subscription ID.")

    sub_dict = retrieve_subscription(subscription.stripe_subscription_id)
    latest_invoice_id = sub_dict.get("latest_invoice")
    if not latest_invoice_id:
        raise ValueError("No invoices for this subscription.")

    invoice = retrieve_invoice(latest_invoice_id)
    payment_intent_id = invoice.get("payment_intent")
    if not payment_intent_id:
        raise ValueError("No payment on latest invoice.")

    currency = invoice.get("currency", subscription.plan.currency)

    idempotency_key = (
        f"refund-{subscription.id}-{payment_intent_id}-{int(_time.time())}"
    )

    refund = create_refund(
        payment_intent=payment_intent_id,
        amount=amount_cents,
        reason=reason,
        metadata={
            "subscription_id": str(subscription.id),
            "reason": reason,
            "initiated_by": str(initiated_by.id) if initiated_by else "system",
        },
        idempotency_key=idempotency_key,
    )

    record = Refund.objects.create(
        subscription=subscription,
        stripe_refund_id=refund["id"],
        stripe_charge_id=payment_intent_id,
        amount_cents=amount_cents or refund.get("amount", 0),
        currency=currency,
        reason=reason,
        status=(
            RefundStatus.COMPLETED
            if refund.get("status") == "succeeded"
            else RefundStatus.PENDING
        ),
        initiated_by=initiated_by,
        stripe_response=refund,
    )
    logger.info(f"Refund created: {refund['id']}")
    return record


# ---------------------------------------------------------------------------
# Transaction history
# ---------------------------------------------------------------------------


def get_transaction_history(user, limit=25, starting_after=None) -> dict:
    """Pull invoice/charge history from Stripe."""
    customer_id = find_customer_id(user)
    if not customer_id:
        return {"transactions": [], "has_more": False, "currency": "USD"}

    default_currency = getattr(user, "currency", "USD")

    result = list_invoices(
        customer_id=customer_id,
        limit=min(limit, 100),
        starting_after=starting_after,
        expand=["data.charge"],
    )

    transactions = []
    for inv in result["data"]:
        transactions.append(
            {
                "id": inv.get("id"),
                "number": inv.get("number"),
                "amount": (inv.get("amount_paid") or 0) / 100,
                "currency": (inv.get("currency") or "usd").upper(),
                "status": inv.get("status"),
                "hosted_url": inv.get("hosted_invoice_url"),
                "created": inv.get("created"),
            }
        )

    return {
        "transactions": transactions,
        "has_more": result["has_more"],
        "currency": default_currency,
    }


# ---------------------------------------------------------------------------
# Backward-compatible aliases (for tasks.py)
# ---------------------------------------------------------------------------

sync_stripe_customer_data = sync_customer_to_local
