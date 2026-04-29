"""GDPR: Delete, anonymize, and export a Stripe Customer's billing data.

Called when a user account is deleted or data must be erased per GDPR.
Also provides data export for GDPR Article 20 (Right to Data Portability).
"""

import logging

from django.utils import timezone

from ..models import Subscription, SubscriptionStatus, Refund, Invoice
from .customer import find_customer_id
from .client import (
    modify_customer,
    delete_customer,
    retrieve_customer,
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

        subs.update(stripe_customer_id="", stripe_subscription_id="")
        return True

    except Exception as e:
        if "No such customer" in str(e):
            subs.update(stripe_customer_id="", stripe_subscription_id="")
            return True
        raise


def export_user_billing_data(user) -> dict:
    """Export all billing data for a user (GDPR Article 20 — Right to Data Portability).

    Returns a structured dictionary containing:
      - User identity info
      - Stripe customer metadata
      - Full subscription history with plan/product details
      - All refund records
      - All invoice records

    This endpoint is callable from the GDPR export controller and returns
    machine-readable data suitable for JSON/CSV export.
    """
    subscriptions = (
        Subscription.objects.filter(user=user)
        .select_related("plan", "product")
    )
    refunds = Refund.objects.filter(subscription__user=user).select_related("subscription")
    invoices = Invoice.objects.filter(subscription__user=user).select_related("subscription")

    # Pull Stripe customer data
    customer_id = find_customer_id(user)
    stripe_customer_data = {}
    if customer_id:
        try:
            stripe_customer_data = retrieve_customer(customer_id)
        except Exception as e:
            logger.warning(
                f"GDPR export: Could not retrieve Stripe customer "
                f"{customer_id}: {e}"
            )

    return {
        "user": {
            "email": user.email,
            "name": user.get_full_name(),
            "user_id": user.id,
        },
        "stripe_customer": {
            "id": customer_id,
            "created": stripe_customer_data.get("created"),
            "currency": stripe_customer_data.get("metadata", {}).get(
                "preferred_currency"
            ),
            "default_payment_method": stripe_customer_data.get(
                "default_payment_method"
            ),
        },
        "subscriptions": [
            {
                "product": s.product.name,
                "product_slug": s.product.slug,
                "plan": s.plan.name,
                "plan_slug": s.plan.slug,
                "status": s.status,
                "currency": s.currency or s.plan.currency,
                "stripe_subscription_id": s.stripe_subscription_id,
                "stripe_customer_id": s.stripe_customer_id,
                "current_period_start": (
                    s.current_period_start.isoformat()
                    if s.current_period_start
                    else None
                ),
                "current_period_end": (
                    s.current_period_end.isoformat()
                    if s.current_period_end
                    else None
                ),
                "trial_start": (
                    s.trial_start.isoformat() if s.trial_start else None
                ),
                "trial_end": s.trial_end.isoformat() if s.trial_end else None,
                "canceled_at": (
                    s.canceled_at.isoformat() if s.canceled_at else None
                ),
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in subscriptions
        ],
        "refunds": [
            {
                "refund_id": r.id,
                "amount_cents": r.amount_cents,
                "currency": r.currency,
                "status": r.status,
                "reason": r.reason,
                "stripe_refund_id": r.stripe_refund_id,
                "initiated_by": (
                    {
                        "id": r.initiated_by_id,
                        "email": (
                            r.initiated_by.email if r.initiated_by else None
                        ),
                    }
                    if r.initiated_by_id
                    else None
                ),
                "created_at": r.created_at.isoformat(),
            }
            for r in refunds
        ],
        "invoices": [
            {
                "stripe_invoice_id": inv.stripe_invoice_id,
                "number": inv.number,
                "status": inv.status,
                "amount_paid_cents": inv.amount_paid_cents,
                "amount_due_cents": inv.amount_due_cents,
                "tax_cents": inv.tax_cents,
                "discount_cents": inv.discount_cents,
                "currency": inv.currency,
                "description": inv.description,
                "period_start": (
                    inv.period_start.isoformat() if inv.period_start else None
                ),
                "period_end": (
                    inv.period_end.isoformat() if inv.period_end else None
                ),
                "hosted_url": inv.hosted_url,
                "pdf_url": inv.pdf_url,
                "attempt_count": inv.attempt_count,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invoices
        ],
        "exported_at": timezone.now().isoformat(),
    }
