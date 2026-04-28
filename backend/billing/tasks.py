"""Celery tasks for the billing app.

Periodic tasks run by Celery Beat:
  - reconcile_webhooks: Retry failed webhook events (every 6 hours)
  - sync_customer_data: Sync Stripe customer data to local profiles (daily)
  - dunning_retry: Process past_due subscriptions needing payment retry (daily)
  - update_exchange_rates: Fetch latest currency exchange rates (daily)
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,  # 5 min between retries
)
def reconcile_webhooks(self, max_age_hours: int = 24):
    """Periodic task to retry failed webhook events.

    Called every 6 hours by Celery Beat. Finds webhook events that were
    recorded but failed during processing, and retries them.

    Args:
        max_age_hours: Only retry events within this time window.
    """
    from .stripe import reconcile_unprocessed_webhooks

    try:
        result = reconcile_unprocessed_webhooks(max_age_hours=max_age_hours)
        logger.info(f"Webhook reconciliation task completed: {result}")
        return result
    except Exception as exc:
        logger.error(f"Webhook reconciliation task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 min between retries
)
def sync_customer_data(self):
    """Periodic task to sync Stripe customer data to local user profiles.

    Called daily by Celery Beat. Iterates over all subscriptions with
    a Stripe customer ID and pulls the latest data from Stripe to
    keep email, name, and currency in sync. This is critical for
    data integrity when users update their profile via Stripe Customer Portal.

    F8: Ensures Stripe Portal changes propagate to the local database
    even if the customer.updated webhook was missed.
    """
    from django.contrib.auth import get_user_model
    from .models import Subscription
    from .stripe import sync_stripe_customer_data

    User = get_user_model()

    try:
        # Get all unique users with a Stripe customer ID
        subs = (
            Subscription.objects.exclude(stripe_customer_id="")
            .exclude(stripe_customer_id__isnull=True)
            .select_related("user")
            .only("user", "stripe_customer_id")
            .distinct("user_id")
        )

        synced_count = 0
        failed_count = 0
        total = subs.count()

        for sub in subs:
            try:
                result = sync_stripe_customer_data(sub.user)
                if result.get("synced"):
                    synced_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"Customer sync failed for user {sub.user_id}: {e}")

        logger.info(
            f"Customer sync task completed: "
            f"{synced_count}/{total} synced, {failed_count} failed"
        )
        return {"synced": synced_count, "failed": failed_count, "total": total}

    except Exception as exc:
        logger.error(f"Customer sync task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 min between retries
)
def dunning_retry(self):
    """Periodic task to process past_due subscriptions for dunning.

    Called daily by Celery Beat. Finds subscriptions that are past_due
    and have been in that state for more than 7 days. Logs a warning
    for manual review — cancellation should be handled by Stripe's
    automatic subscription cancellation after the configured retry
    window.

    Future enhancement: Send dunning emails to users whose payment
    method needs updating, with a link to the Stripe Customer Portal.
    """
    from django.utils import timezone
    from .models import Subscription, SubscriptionStatus

    try:
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)

        past_due_subs = Subscription.objects.filter(
            status=SubscriptionStatus.PAST_DUE,
            updated_at__lte=seven_days_ago,
        ).select_related("user", "plan", "product")

        count = 0
        for sub in past_due_subs:
            count += 1
            logger.warning(
                f"DUNNING: Subscription sub={sub.id} for user={sub.user.email} "
                f"has been past_due since {sub.updated_at}. "
                f"Plan: {sub.plan.name} ({sub.product.name}). "
                f"User should update payment method via Portal."
            )
            # Future: Send dunning email here
            # send_dunning_email(sub.user, sub)

        logger.info(
            f"Dunning retry task completed: {count} past_due subscriptions "
            f"older than 7 days found."
        )
        return {"past_due_count": count}

    except Exception as exc:
        logger.error(f"Dunning retry task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min between retries
)
def update_exchange_rates(self):
    """Periodic task to fetch and store exchange rates.

    Called daily by Celery Beat. Fetches rates from the free open.er-api.com
    API and upserts them into the ExchangeRate table. These rates are used
    by the currency conversion service to display plan prices in the user's
    preferred currency.
    """
    from .currency_service import update_exchange_rates as _update_rates

    try:
        result = _update_rates()
        logger.info(
            f"Exchange rates updated: {result['updated']} rates "
            f"(base={result['base']}, {result['skipped']} skipped)"
        )
        return result
    except Exception as exc:
        logger.error(f"Exchange rate update task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
