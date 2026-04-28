"""Single source-of-truth subscription sync from Stripe.

Every webhook handler and the confirm_checkout flow call this one
function to update the local Subscription from the live Stripe
subscription.  This prevents status drift.
"""

import logging
from typing import Optional
from django.db import transaction

from ...models import (
    Subscription,
    SubscriptionStatus,
    Plan,
    Product,
)
from ..client import (
    retrieve_subscription,
    get_subscription_items,
    ts_to_dt,
    get_api_key,
)

logger = logging.getLogger(__name__)


# Stripe status -> local status mapping
_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.TRIALING,
    "past_due": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "paused": SubscriptionStatus.PAUSED,
    "unpaid": SubscriptionStatus.PAST_DUE,
}


def sync_subscription_from_stripe(
    stripe_sub_id: str,
    subscription: Optional[Subscription] = None,
) -> Subscription:
    """Fetch the live Stripe subscription and overwrite local state.

    This is the ONLY function that writes subscription state from Stripe
    to the local DB.  All webhook handlers and the confirm_checkout flow
    delegate to this.

    Args:
        stripe_sub_id: The Stripe subscription ID.
        subscription: Optional pre-fetched Subscription (for atomic blocks).

    Returns:
        The updated Subscription model instance.

    Raises:
        Subscription.DoesNotExist: If not found and not auto-created.
    """
    stripe_sub = retrieve_subscription(stripe_sub_id)
    stripe_status = stripe_sub.get("status", "")
    metadata = stripe_sub.get("metadata") or {}

    # --- Find or look up local subscription ----------------------------------
    if subscription is None:
        try:
            subscription = Subscription.objects.select_for_update().get(
                stripe_subscription_id=stripe_sub_id
            )
        except Subscription.DoesNotExist:
            # Try to find by user_id + product from metadata
            user_id = metadata.get("user_id")
            product_slug = metadata.get("product_slug")
            if user_id and product_slug:
                from ...services import BillingService
                from django.contrib.auth import get_user_model

                User = get_user_model()
                try:
                    user = User.objects.get(id=int(user_id))
                    product = BillingService.get_product_by_slug(product_slug)
                    if product:
                        subscription = (
                            Subscription.objects.select_for_update()
                            .filter(user=user, product=product)
                            .first()
                        )
                        if not subscription:
                            subscription = (
                                BillingService.get_or_create_free_subscription(
                                    user, product
                                )
                            )
                except (User.DoesNotExist, ValueError):
                    pass

    if subscription is None:
        logger.warning(
            f"sync_subscription: no local record for stripe_sub={stripe_sub_id}"
        )
        raise Subscription.DoesNotExist(f"No local subscription for {stripe_sub_id}")

    # --- Detect plan change via price ID or metadata -------------------------
    items = get_subscription_items(stripe_sub)
    metadata = stripe_sub.get("metadata") or {}
    plan_changed = False

    if items:
        price_obj = items[0].get("price") or {}
        stripe_price_id = price_obj.get("id") if isinstance(price_obj, dict) else None
        if stripe_price_id and stripe_price_id != subscription.plan.stripe_price_id:
            # Try matching by price ID first (exact match — same currency)
            new_plan = (
                Plan.objects.filter(stripe_price_id=stripe_price_id)
                .select_related("product")
                .first()
            )
            if new_plan:
                subscription.plan = new_plan
                plan_changed = True
                logger.info(f"Plan change detected via price ID: -> {new_plan.slug}")

    # Fallback: use metadata plan_slug when price ID doesn't match
    # (happens when checkout used a converted-currency price)
    if not plan_changed and metadata.get("plan_slug"):
        target_slug = metadata["plan_slug"]
        product_slug = metadata.get("product_slug", "")
        if subscription.plan.slug != target_slug:
            qs = Plan.objects.filter(slug=target_slug)
            if product_slug:
                qs = qs.filter(product__slug=product_slug)
            new_plan = qs.select_related("product").first()
            if new_plan:
                subscription.plan = new_plan
                logger.info(f"Plan change detected via metadata: -> {new_plan.slug}")

    # --- Overwrite all fields from Stripe ------------------------------------
    subscription.status = _STATUS_MAP.get(stripe_status, subscription.status)
    subscription.stripe_subscription_id = stripe_sub_id
    subscription.stripe_customer_id = (
        stripe_sub.get("customer") or subscription.stripe_customer_id
    )

    # Period dates
    subscription.current_period_start = ts_to_dt(stripe_sub.get("current_period_start"))
    subscription.current_period_end = ts_to_dt(stripe_sub.get("current_period_end"))

    # Trial
    trial_start = ts_to_dt(stripe_sub.get("trial_start"))
    trial_end = ts_to_dt(stripe_sub.get("trial_end"))
    if trial_start and trial_end:
        subscription.trial_start = trial_start
        subscription.trial_end = trial_end
        subscription.status = SubscriptionStatus.TRIALING
        subscription.has_used_trial = True

    # Cancellation
    canceled_at = ts_to_dt(stripe_sub.get("canceled_at"))
    if canceled_at:
        subscription.canceled_at = canceled_at

    # Currency — set once from Stripe, never overwrite
    sub_currency = getattr(subscription, "currency", None)
    if not sub_currency:
        subscription.currency = stripe_sub.get("currency", "usd")

    subscription.save()

    logger.info(
        f"Synced subscription {subscription.id} from Stripe: "
        f"status={subscription.status}, plan={subscription.plan.slug}, "
        f"stripe_sub={stripe_sub_id}"
    )
    return subscription
