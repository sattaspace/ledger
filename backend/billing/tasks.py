"""Celery tasks for the billing app.

Periodic tasks run by Celery Beat:
  - reconcile_webhooks: Retry failed webhook events (every 6 hours)
  - sync_customer_data: Sync Stripe customer data to local profiles (daily)
  - dunning_retry: Process past_due subscriptions with staged email + action workflow (daily)
  - update_exchange_rates: Fetch latest currency exchange rates (daily)
  - recognize_revenue: Daily revenue recognition for active subscriptions (daily)
"""

import logging
from celery import shared_task

logger = logging.getLogger(__name__)


# =============================================================================
# Dunning Configuration
# =============================================================================

# Staged dunning workflow: each step triggers at the given day threshold.
# Steps are cumulative — if a subscription reaches day 5, both step 1 and
# step 2 actions will fire (unless already sent).
DUNNING_STEPS = [
    {
        "step": 1,
        "days": 3,
        "action": "email_reminder",
        "subject": "Payment Issue: Update Your Payment Method",
        "body_template": (
            "Hi {first_name},\n\n"
            "We were unable to process the payment for your {plan_name} "
            "subscription ({product_name}). This may be due to an expired "
            "or changed payment method.\n\n"
            "Please update your payment method as soon as possible to avoid "
            "service interruption:\n\n"
            "{portal_link}\n\n"
            "If you believe this is an error, please contact our support team.\n\n"
            "Thank you for being a valued customer."
        ),
    },
    {
        "step": 2,
        "days": 5,
        "action": "email_urgent",
        "subject": "URGENT: Payment Still Required — Action Needed",
        "body_template": (
            "Hi {first_name},\n\n"
            "This is a reminder that your {plan_name} subscription "
            "({product_name}) payment has still not been processed.\n\n"
            "Your access will be suspended in 2 days if payment is not updated.\n\n"
            "Update your payment method now:\n\n"
            "{portal_link}\n\n"
            "We don't want to lose you — please take a moment to resolve this."
        ),
    },
    {
        "step": 3,
        "days": 7,
        "action": "restrict_access",
        # No email for restrict — the system handles it silently
    },
    {
        "step": 4,
        "days": 14,
        "action": "cancel_subscription",
        "subject": "Subscription Cancelled: Payment Not Received",
        "body_template": (
            "Hi {first_name},\n\n"
            "We were unable to process your payment for {plan_name} "
            "({product_name}) after multiple attempts over 14 days.\n\n"
            "Your subscription has been cancelled. If you'd like to "
            "resubscribe, you can do so from your billing page:\n\n"
            "{portal_link}\n\n"
            "We're sorry to see you go. If you have any questions, "
            "our support team is here to help."
        ),
    },
]

# Minimum interval (in hours) between dunning emails to prevent spam
DUNNING_EMAIL_MIN_INTERVAL_HOURS = 24

# =============================================================================
# Credit Expiry Notification Configuration (Enhancement 3)
# =============================================================================

# Days before expiry to send warning emails. Each threshold maps to a
# CreditNotificationLog.NotificationType to prevent duplicate sends.
CREDIT_EXPIRY_WARNING_DAYS = [14, 7, 1]

# Grace period before hard-expiring a pool after expires_at passes.
# During the grace period, the pool remains ACTIVE but an urgent banner
# is shown. After the grace period, the pool is marked EXPIRED.
CREDIT_EXPIRY_GRACE_HOURS = 24

# Data retention period after credit expiry. User data is preserved for
# this many days after a credit pool expires/exhausts. During this period,
# the user can renew their credit to regain full access. After this period,
# the access matrix of the free plan applies — integer values in the
# access matrix limit the number of data entries the user can maintain.
# For example, if the free plan has max_entries=5, only 5 rows of user
# data remain accessible; excess data is soft-locked (not deleted).
CREDIT_DATA_RETENTION_DAYS = 30


def _send_dunning_email(sub, step_config):
    """Send a dunning email to the subscriber.

    Returns True if email was sent, False if skipped (too recent).
    """
    from django.utils import timezone
    from django.core.mail import send_mail
    from django.conf import settings

    # Skip if no email body (restrict_access has no email)
    if not step_config.get("body_template"):
        return False

    # Prevent duplicate emails within the minimum interval
    min_interval = timezone.timedelta(hours=DUNNING_EMAIL_MIN_INTERVAL_HOURS)
    if sub.last_dunning_email_at and (
        timezone.now() - sub.last_dunning_email_at
    ) < min_interval:
        logger.info(
            f"DUNNING: Skipped email for sub={sub.id} — "
            f"last email sent {sub.last_dunning_email_at}"
        )
        return False

    portal_link = f"{getattr(settings, 'STRIPE_APP_DOMAIN', '')}/dashboard/billing"
    first_name = sub.user.first_name or sub.user.email

    body = step_config["body_template"].format(
        first_name=first_name,
        plan_name=sub.plan.name,
        product_name=sub.product.name,
        portal_link=portal_link,
    )

    sent = send_mail(
        subject=step_config["subject"],
        message=body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sattabase.com"),
        recipient_list=[sub.user.email],
        fail_silently=True,
    )

    if sent:
        sub.last_dunning_email_at = timezone.now()
        sub.save(update_fields=["last_dunning_email_at", "updated_at"])
        logger.info(
            f"DUNNING: Sent {step_config['action']} email to "
            f"{sub.user.email} for sub={sub.id}"
        )
        return True

    logger.error(
        f"DUNNING: Failed to send {step_config['action']} email to "
        f"{sub.user.email} for sub={sub.id}"
    )
    return False


def _execute_dunning_step(sub, step_config):
    """Execute a single dunning step for a subscription.

    Actions:
      - email_reminder: Send friendly payment reminder
      - email_urgent: Send urgent payment notice
      - restrict_access: Downgrade to free features (log warning)
      - cancel_subscription: Cancel the subscription on Stripe
    """
    action = step_config["action"]

    if action in ("email_reminder", "email_urgent"):
        return _send_dunning_email(sub, step_config)

    elif action == "restrict_access":
        logger.warning(
            f"DUNNING: Restricting access for sub={sub.id} "
            f"(user={sub.user.email}, past_due > 7 days). "
            f"Subscription remains active but flagged for review."
        )
        # NOTE: Actual access restriction should be implemented in the
        # auth/me access map check. The subscription stays past_due so
        # is_effectively_active() will return False after period_end.

    elif action == "cancel_subscription":
        logger.warning(
            f"DUNNING: Auto-cancelling sub={sub.id} "
            f"(user={sub.user.email}, past_due > 14 days)."
        )
        try:
            from django.utils import timezone
            from .stripe import cancel_subscription_on_stripe
            from .models import SubscriptionStatus

            if sub.stripe_subscription_id:
                cancel_subscription_on_stripe(sub)
            sub.status = SubscriptionStatus.CANCELED
            sub.canceled_at = timezone.now()
            sub.save(
                update_fields=[
                    "status",
                    "canceled_at",
                    "updated_at",
                ]
            )
            logger.info(f"DUNNING: Cancelled sub={sub.id} via dunning workflow")
        except Exception as e:
            logger.error(
                f"DUNNING: Failed to cancel sub={sub.id}: {e}", exc_info=True
            )
            # MED-04/HIGH-01 Fix: Return failure status so caller does NOT
            # advance dunning_step. Previously, this function always returned
            # None (implicit success), causing the caller to advance to step 4
            # even when the Stripe cancel failed.
            return False

    # MED-04 Fix: Return True to indicate success for all non-cancel actions
    return True


# =============================================================================
# Celery Tasks
# =============================================================================


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
    """Periodic task to process past_due subscriptions with staged dunning workflow.

    Called daily by Celery Beat. Finds subscriptions that are past_due
    and processes them through the DUNNING_STEPS workflow:

      Day 3  → email_reminder (friendly)
      Day 5  → email_urgent (stronger language)
      Day 7  → restrict_access (flag for access restriction)
      Day 14 → cancel_subscription (auto-cancel)

    Each subscription tracks its current ``dunning_step`` and
    ``last_dunning_email_at`` to prevent duplicate actions and emails.

    When a payment succeeds (invoice.payment_succeeded), the dunning
    step is reset to 0 automatically.
    """
    from django.utils import timezone
    from .models import Subscription, SubscriptionStatus

    try:
        past_due_subs = (
            Subscription.objects.filter(
                status=SubscriptionStatus.PAST_DUE,
            )
            .select_related("user", "plan", "product")
            .order_by("updated_at")
        )

        now = timezone.now()
        stats = {"processed": 0, "emails_sent": 0, "restricted": 0, "cancelled": 0}

        for sub in past_due_subs:
            # MED-04 Fix: Use past_due_at timestamp instead of updated_at.
            # updated_at advances on every save (including dunning task saves),
            # which artificially keeps days_past_due low and delays step escalation.
            # past_due_at is set once when status first transitions to PAST_DUE.
            past_due_at = sub.past_due_at or sub.updated_at
            days_past_due = (now - past_due_at).days

            for step_config in DUNNING_STEPS:
                step_num = step_config["step"]
                threshold_days = step_config["days"]

                # Only trigger if past threshold AND not already done
                if days_past_due >= threshold_days and sub.dunning_step < step_num:
                    try:
                        step_success = _execute_dunning_step(sub, step_config)
                        # MED-04/HIGH-02 Fix: Only advance dunning_step if the
                        # action succeeded. Previously, step was always advanced
                        # even if email failed to send or cancel failed.
                        if step_success:
                            sub.dunning_step = step_num
                            sub.save(update_fields=["dunning_step", "updated_at"])
                        stats["processed"] += 1

                        action = step_config["action"]
                        if "email" in action:
                            stats["emails_sent"] += 1
                        elif action == "restrict_access":
                            stats["restricted"] += 1
                        elif action == "cancel_subscription":
                            stats["cancelled"] += 1
                    except Exception as e:
                        logger.error(
                            f"DUNNING: Error processing step {step_num} "
                            f"for sub={sub.id}: {e}",
                            exc_info=True,
                        )

        logger.info(
            f"Dunning retry task completed: {stats['processed']} actions, "
            f"{stats['emails_sent']} emails, {stats['restricted']} restricted, "
            f"{stats['cancelled']} cancelled"
        )
        return stats

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
    API with fallback to frankfurter.app. Upserts rates into the ExchangeRate
    table. These rates are used by the currency conversion service to display
    plan prices in the user's preferred currency.
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


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 min between retries
)
def cleanup_stale_webhook_events(self, retention_days: int = 90):
    """Periodic task to clean up old processed webhook events.

    Called weekly by Celery Beat. Deletes webhook events that have been
    successfully processed and are older than the retention period (default
    90 days). This prevents the WebhookEventLog table from growing
    unboundedly as each event can be several KB of JSON.

    Args:
        retention_days: Only delete events older than this many days.

    Returns:
        {"deleted": int} — number of events deleted.
    """
    from django.utils import timezone
    from .models import WebhookEventLog

    try:
        cutoff = timezone.now() - timezone.timedelta(days=retention_days)
        deleted, _ = WebhookEventLog.objects.filter(
            processed=True,
            created_at__lte=cutoff,
        ).delete()
        logger.info(
            f"Cleaned up {deleted} stale webhook events (retention={retention_days}d)"
        )
        return {"deleted": deleted}
    except Exception as exc:
        logger.error(f"Webhook cleanup task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 min between retries
)
def recognize_revenue(self, target_date: str = None):
    """Periodic task to recognize daily revenue for active subscriptions.

    Called daily by Celery Beat. For each active subscription with a paid
    plan, this task creates (or updates) a RevenueRecognitionEntry for
    the target date. The daily amount is calculated as:

        amount_cents = plan.price_cents / days_in_billing_period

    The UniqueConstraint on (subscription, recognized_date) prevents
    duplicate entries if the task runs more than once for the same date.

    Args:
        target_date: ISO date string (YYYY-MM-DD). Defaults to yesterday
            so that the task always processes the most recent complete day.

    Returns:
        {"created": int, "skipped": int, "errors": int}
    """
    from django.utils import timezone
    from .models import (
        Subscription,
        SubscriptionStatus,
        RevenueRecognitionEntry,
        BillingCycle,
    )

    try:
        if target_date:
            recognized = timezone.datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            # Default to yesterday — the most recent complete day
            recognized = (timezone.now() - timezone.timedelta(days=1)).date()

        # MED-05 Fix: Exclude PAST_DUE from revenue recognition.
        # ASC 606 revenue recognition principles require that revenue
        # should only be recognized when it is probable that payment will
        # be collected. Including PAST_DUE subscriptions overstates revenue.
        # Revenue for these subscriptions is recognized retroactively when
        # payment succeeds via the invoice.payment_succeeded webhook handler.
        subs = Subscription.objects.filter(
            status__in=[
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.TRIALING,
                SubscriptionStatus.CANCELED,
            ],
            plan__price_cents__gt=0,  # Skip free plans
            current_period_start__lte=timezone.datetime.combine(
                recognized, timezone.datetime.max.time()
            ),
            current_period_end__gte=timezone.datetime.combine(
                recognized, timezone.datetime.min.time()
            ),
        ).select_related("plan")

        stats = {"created": 0, "skipped": 0, "errors": 0}
        batch = []

        for sub in subs:
            try:
                plan = sub.plan
                period_start = sub.current_period_start
                period_end = sub.current_period_end

                if not period_start or not period_end:
                    stats["skipped"] += 1
                    continue

                # Skip lifetime plans — recognize all revenue on payment day
                if plan.billing_cycle == BillingCycle.LIFETIME:
                    stats["skipped"] += 1
                    continue

                # Calculate total days in the billing period
                total_days = (period_end.date() - period_start.date()).days
                if total_days <= 0:
                    stats["skipped"] += 1
                    continue

                # Daily revenue = total plan price / days in period
                # Use integer division with rounding to avoid cent drift
                import math
                daily_cents = math.ceil(plan.price_cents / total_days)

                # For the last day of the period, adjust to capture any
                # remaining cents lost to ceiling rounding on prior days
                is_last_day = (period_end.date() - recognized).days == 0
                if is_last_day:
                    # CRIT-02 Fix: Guard against negative daily_cents.
                    # Edge case: if price_cents < total_days (e.g. a $0.01
                    # plan with a 30-day period), ceiling rounding on prior
                    # days may accumulate more than price_cents total.
                    # max(0, ...) ensures we never recognize negative revenue.
                    daily_cents = max(0, plan.price_cents - (daily_cents * (total_days - 1)))

                currency = sub.currency or plan.currency

                batch.append(RevenueRecognitionEntry(
                    subscription=sub,
                    plan=plan,
                    amount_cents=daily_cents,
                    currency=currency,
                    period_start=period_start,
                    period_end=period_end,
                    recognized_date=recognized,
                    stripe_invoice_id="",
                    source="scheduled",
                ))

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"REVENUE: Error calculating for sub={sub.id}: {e}",
                    exc_info=True,
                )

        # Bulk create with conflict handling (ignore duplicates)
        if batch:
            created = RevenueRecognitionEntry.objects.bulk_create(
                batch,
                ignore_conflicts=True,
            )
            stats["created"] = len(created)
            stats["skipped"] += len(batch) - len(created)

        logger.info(
            f"Revenue recognition for {recognized}: "
            f"{stats['created']} entries, {stats['skipped']} skipped, "
            f"{stats['errors']} errors"
        )
        return stats

    except Exception as exc:
        logger.error(f"Revenue recognition task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# =============================================================================
# Credit Request Email Notifications
# =============================================================================


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 min between retries
)
def send_credit_request_approved_email(
    self,
    user_email: str,
    user_name: str,
    product_name: str,
    plan_name: str,
    amount_cents: int,
    currency: str,
    credit_pool_id: int,
    invoice_number: str,
    periods: int,
    billing_cycle: str = "monthly",
    commitment_start: str = "",  # ISO date string
    commitment_end: str = "",    # ISO date string
):
    """Send email notification when a credit request is approved.

    Called after admin approves a CreditPurchaseRequest. Sends a professional
    HTML confirmation email to the user with their credit pool details,
    commitment terms, and invoice number.

    ENHANCEMENT-2: Added billing_cycle, commitment_start, commitment_end
    parameters for compliance & validity period messaging.

    Args:
        user_email: Recipient email address.
        user_name: User's first name or display name.
        product_name: Product name for the credit.
        plan_name: Plan name for the credit.
        amount_cents: Amount paid in cents.
        currency: ISO 4217 currency code.
        credit_pool_id: ID of the created CreditPool.
        invoice_number: Invoice number for reference.
        periods: Number of billing periods credited.
        billing_cycle: "monthly" or "yearly".
        commitment_start: ISO date string for commitment start date.
        commitment_end: ISO date string for commitment end date.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        # Format amount
        amount_display = f"{amount_cents / 100:.2f} {currency}"

        # Build email body
        subject = f"Credit Purchase Approved — {product_name}"
        app_domain = getattr(settings, 'STRIPE_APP_DOMAIN', '')

        display_name = user_name or user_email.split('@')[0]

        # ENHANCEMENT-2: Format commitment dates
        cycle_label = "month" if billing_cycle == "monthly" else "year"
        periods_label = f"{periods} {cycle_label}(s)" if periods != 1 else f"1 {cycle_label}"

        # Parse and format ISO date strings
        start_display = "—"
        end_display = "—"
        if commitment_start:
            try:
                from datetime import datetime
                start_display = datetime.fromisoformat(commitment_start).strftime("%B %d, %Y")
            except (ValueError, TypeError):
                start_display = commitment_start
        if commitment_end:
            try:
                from datetime import datetime
                end_display = datetime.fromisoformat(commitment_end).strftime("%B %d, %Y")
            except (ValueError, TypeError):
                end_display = commitment_end

        # ENHANCEMENT-2: Build commitment details section for HTML email
        commitment_section = f"""
<!-- Commitment Details -->
<tr><td style="padding:24px 40px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#FEF3C7;border-radius:8px;border:1px solid #FDE68A;">
<tr><td style="padding:16px 20px;">
<p style="margin:0 0 8px;color:#92400E;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:0.8px;">Commitment Details</p>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="padding:4px 0;color:#78350F;font-size:12px;width:140px;"><b>Commitment:</b></td>
<td style="padding:4px 0;color:#78350F;font-size:12px;">{periods_label}</td>
</tr>
<tr>
<td style="padding:4px 0;color:#78350F;font-size:12px;"><b>Start Date:</b></td>
<td style="padding:4px 0;color:#78350F;font-size:12px;">{start_display}</td>
</tr>
<tr>
<td style="padding:4px 0;color:#78350F;font-size:12px;"><b>End Date:</b></td>
<td style="padding:4px 0;color:#78350F;font-size:12px;">{end_display}</td>
</tr>
<tr>
<td style="padding:4px 0;color:#78350F;font-size:12px;"><b>Auto-Renewal:</b></td>
<td style="padding:4px 0;color:#78350F;font-size:12px;">No — credits do not auto-renew</td>
</tr>
</table>
<p style="margin:10px 0 0;color:#92400E;font-size:11px;line-height:1.5;">
<strong>Important:</strong> This is a non-refundable prepaid commitment for {periods} billing period(s). Credits are consumed at the start of each billing period and grant access to all features of your plan. Access will be revoked when all periods are consumed or the commitment expires. Unused periods are not refundable.
</p>
</td></tr></table>
</td></tr>
"""

        # Professional HTML email body
        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;padding:32px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="background-color:#2563EB;padding:32px 40px;">
<h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">SattaBase</h1>
<p style="margin:4px 0 0;color:#BFDBFE;font-size:13px;">Billing &amp; Subscription Platform</p>
</td></tr>

<!-- Success Badge -->
<tr><td style="padding:32px 40px 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="background-color:#ECFDF5;border-radius:6px;padding:6px 14px;">
<span style="color:#059669;font-size:13px;font-weight:600;">&#10003; Approved</span>
</td></tr></table>
</td></tr>

<!-- Greeting -->
<tr><td style="padding:20px 40px 0;">
<h2 style="margin:0;color:#111827;font-size:22px;font-weight:700;">Credit Purchase Confirmed</h2>
<p style="margin:8px 0 0;color:#6B7280;font-size:15px;line-height:1.5;">
Hi {display_name}, great news! Your credit purchase request has been approved and your credits are now active.
</p>
</td></tr>

<!-- Details Card -->
<tr><td style="padding:24px 40px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F9FAFB;border-radius:8px;border:1px solid #E5E7EB;">
<tr><td style="padding:20px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Product</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{product_name}</span>
</td>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Plan</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{plan_name}</span>
</td>
</tr>
<tr>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Amount</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{amount_display}</span>
</td>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Periods</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{periods_label}</span>
</td>
</tr>
<tr>
<td style="padding:8px 0;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Invoice</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{invoice_number}</span>
</td>
<td style="padding:8px 0;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Payment</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">Bank Transfer</span>
</td>
</tr>
</table>
</td></tr></table>
</td></tr>

{commitment_section}

<!-- Action Buttons -->
<tr><td style="padding:28px 40px 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="background-color:#2563EB;border-radius:6px;padding:0;">
<a href="{app_domain}/dashboard/billing/credits" style="display:inline-block;padding:12px 24px;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">View My Credits</a>
</td>
<td style="width:12px;"></td>
<td style="background-color:#F3F4F6;border-radius:6px;padding:0;">
<a href="{app_domain}/dashboard/billing/transactions" style="display:inline-block;padding:12px 24px;color:#374151;font-size:14px;font-weight:600;text-decoration:none;">Download Invoice</a>
</td>
</tr></table>
</td></tr>

<!-- Info -->
<tr><td style="padding:24px 40px 0;">
<p style="margin:0;color:#6B7280;font-size:13px;line-height:1.6;">
Credits are consumed at the start of each billing period and grant access to all features of your plan. You can download your invoice PDF from the Transactions page at any time. Credits do not auto-renew — please purchase new credits before your commitment ends to maintain uninterrupted access.
</p>
</td></tr>

<!-- Footer -->
<tr><td style="padding:32px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #E5E7EB;">
<tr><td style="padding-top:20px;">
<p style="margin:0;color:#9CA3AF;font-size:11px;line-height:1.5;">
This email was sent by SattaBase. If you have any questions, please contact our support team.
</p>
</td></tr></table>
</td></tr>

</table>
</td></tr></table>
</body>
</html>"""

        # Plain text fallback for email clients that don't support HTML
        # ENHANCEMENT-2: Added commitment details and non-refundable notice
        body = (
            f"Hi {display_name},\n\n"
            f"Great news! Your credit purchase request has been approved.\n\n"
            f"COMMITMENT DETAILS:\n"
            f"  Product:          {product_name}\n"
            f"  Plan:             {plan_name}\n"
            f"  Billing Cycle:    {billing_cycle.capitalize()}\n"
            f"  Commitment:       {periods_label}\n"
            f"  Start Date:       {start_display}\n"
            f"  End Date:         {end_display}\n"
            f"  Total Amount:     {amount_display}\n"
            f"  Invoice:          {invoice_number}\n\n"
            f"IMPORTANT:\n"
            f"  - This is a non-refundable prepaid commitment for {periods} billing period(s).\n"
            f"  - Credits are consumed at the start of each billing period.\n"
            f"  - Unused periods are not refundable.\n"
            f"  - Access will be revoked when the commitment ends unless renewed.\n"
            f"  - Credits do not auto-renew. Purchase new credits before expiry\n"
            f"    to maintain uninterrupted access.\n\n"
            f"View your credits: {app_domain}/dashboard/billing/credits\n"
            f"Download invoice: {app_domain}/dashboard/billing/transactions\n\n"
            f"Thank you for your payment!\n\n"
            f"— The SattaBase Team"
        )

        sent = send_mail(
            subject=subject,
            message=body,
            html_message=html_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sattabase.com"),
            recipient_list=[user_email],
            fail_silently=False,
        )

        if sent:
            logger.info(
                f"CREDIT_EMAIL: Sent approval notification to {user_email} "
                f"for credit_pool={credit_pool_id}"
            )
            return {"status": "sent", "user_email": user_email}
        else:
            logger.warning(
                f"CREDIT_EMAIL: Failed to send approval notification to {user_email}"
            )
            return {"status": "failed", "user_email": user_email}

    except Exception as exc:
        logger.error(
            f"CREDIT_EMAIL: Error sending approval email to {user_email}: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 min between retries
)
def send_credit_request_rejected_email(
    self,
    user_email: str,
    user_name: str,
    product_name: str,
    plan_name: str,
    amount_cents: int,
    currency: str,
    reason: str = "",
):
    """Send email notification when a credit request is rejected.

    Called after admin rejects a CreditPurchaseRequest. Sends a professional
    HTML notification email to the user explaining the rejection.

    Args:
        user_email: Recipient email address.
        user_name: User's first name or display name.
        product_name: Product name for the request.
        plan_name: Plan name for the request.
        amount_cents: Amount in cents that was requested.
        currency: ISO 4217 currency code.
        reason: Optional rejection reason from admin.
    """
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        # Format amount
        amount_display = f"{amount_cents / 100:.2f} {currency}"
        display_name = user_name or user_email.split('@')[0]
        app_domain = getattr(settings, 'STRIPE_APP_DOMAIN', '')

        # Build email body
        subject = f"Credit Request Update — {product_name}"

        # Professional HTML email body
        reason_section = ""
        if reason:
            reason_section = f"""
<!-- Reason Section -->
<tr><td style="padding:24px 40px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#FEF2F2;border-radius:8px;border:1px solid #FECACA;">
<tr><td style="padding:16px 20px;">
<span style="color:#991B1B;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Reason</span><br>
<span style="color:#7F1D1D;font-size:14px;line-height:1.5;">{reason}</span>
</td></tr></table>
</td></tr>"""

        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;padding:32px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="background-color:#2563EB;padding:32px 40px;">
<h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">SattaBase</h1>
<p style="margin:4px 0 0;color:#BFDBFE;font-size:13px;">Billing &amp; Subscription Platform</p>
</td></tr>

<!-- Status Badge -->
<tr><td style="padding:32px 40px 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="background-color:#FEF2F2;border-radius:6px;padding:6px 14px;">
<span style="color:#DC2626;font-size:13px;font-weight:600;">&#10007; Not Approved</span>
</td></tr></table>
</td></tr>

<!-- Greeting -->
<tr><td style="padding:20px 40px 0;">
<h2 style="margin:0;color:#111827;font-size:22px;font-weight:700;">Credit Request Update</h2>
<p style="margin:8px 0 0;color:#6B7280;font-size:15px;line-height:1.5;">
Hi {display_name}, we've reviewed your credit purchase request for {product_name} ({plan_name}), but unfortunately we were unable to process it at this time.
</p>
</td></tr>

<!-- Details Card -->
<tr><td style="padding:24px 40px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F9FAFB;border-radius:8px;border:1px solid #E5E7EB;">
<tr><td style="padding:20px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Product</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{product_name}</span>
</td>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Plan</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{plan_name}</span>
</td>
</tr>
<tr>
<td style="padding:8px 0;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Amount Requested</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{amount_display}</span>
</td>
<td style="padding:8px 0;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Payment</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">Bank Transfer</span>
</td>
</tr>
</table>
</td></tr></table>
</td></tr>

{reason_section}

<!-- Action Button -->
<tr><td style="padding:28px 40px 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="background-color:#2563EB;border-radius:6px;padding:0;">
<a href="{app_domain}/dashboard/billing/credits/request" style="display:inline-block;padding:12px 24px;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">Submit New Request</a>
</td>
</tr></table>
</td></tr>

<!-- Info -->
<tr><td style="padding:24px 40px 0;">
<p style="margin:0;color:#6B7280;font-size:13px;line-height:1.6;">
If you believe this is an error or would like to submit a new request, please visit the credit request page. For further assistance, please contact our support team.
</p>
</td></tr>

<!-- Footer -->
<tr><td style="padding:32px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #E5E7EB;">
<tr><td style="padding-top:20px;">
<p style="margin:0;color:#9CA3AF;font-size:11px;line-height:1.5;">
This email was sent by SattaBase. If you have any questions, please contact our support team.
</p>
</td></tr></table>
</td></tr>

</table>
</td></tr></table>
</body>
</html>"""

        # Plain text fallback
        body = (
            f"Hi {display_name},\n\n"
            f"We've reviewed your credit purchase request for {product_name} "
            f"({plan_name}), but unfortunately we were unable to process it at this time.\n\n"
            f"Product: {product_name}\n"
            f"Plan: {plan_name}\n"
            f"Amount: {amount_display}\n\n"
        )

        if reason:
            body += f"Reason: {reason}\n\n"

        body += (
            f"If you believe this is an error or would like to submit a new request, "
            f"please visit:\n"
            f"{app_domain}/dashboard/billing/credits/request\n\n"
            f"For assistance, please contact our support team.\n\n"
            f"— The SattaBase Team"
        )

        sent = send_mail(
            subject=subject,
            message=body,
            html_message=html_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sattabase.com"),
            recipient_list=[user_email],
            fail_silently=False,
        )

        if sent:
            logger.info(
                f"CREDIT_EMAIL: Sent rejection notification to {user_email}"
            )
            return {"status": "sent", "user_email": user_email}
        else:
            logger.warning(
                f"CREDIT_EMAIL: Failed to send rejection notification to {user_email}"
            )
            return {"status": "failed", "user_email": user_email}

    except Exception as exc:
        logger.error(
            f"CREDIT_EMAIL: Error sending rejection email to {user_email}: {exc}",
            exc_info=True,
        )
        raise self.retry(exc=exc)


# =============================================================================
# Credit Period Consumption
# =============================================================================


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,  # 10 min between retries
)
def consume_credit_periods(self):
    """Periodic task to consume billing periods from active credit pools.

    Called daily by Celery Beat. For each active credit pool:
      1. Check if current_period_end has passed
      2. If yes, consume one period and start a new billing period
      3. If no periods remaining, mark as exhausted

    This task ensures that credit pools behave like subscriptions — each
    billing period is "consumed" as time passes, and the pool becomes
    exhausted when all periods are used.

    Returns:
        {"consumed": int, "exhausted": int, "errors": int}
    """
    from django.utils import timezone
    from django.db import transaction
    from .models import CreditPool, CreditTransaction

    try:
        now = timezone.now()
        stats = {"consumed": 0, "exhausted": 0, "errors": 0}

        # BUG-FIX: select_for_update() must be within transaction.atomic().
        # Previously, the query was outside the per-pool transaction, causing
        # TransactionManagementError on PostgreSQL. Now the entire batch is
        # wrapped in a single transaction with select_for_update to lock rows
        # and prevent race conditions when multiple workers overlap.
        with transaction.atomic():
            active_pools = list(CreditPool.objects.filter(
                status=CreditPool.CreditPoolStatus.ACTIVE,
                current_period_end__lte=now,
            ).select_related("user", "product", "plan").select_for_update())

            # BUG-FIX: Import relativedelta once at the top of the loop scope,
            # avoiding duplicate imports in both the "first period" and "next period" branches.
            from dateutil.relativedelta import relativedelta

            for pool in active_pools:
                try:
                    # Check if this is the first period (not yet activated)
                    if not pool.current_period_start:
                        # Activate the pool - first period starts now
                        # ENHANCEMENT-4: relativedelta is imported at the top of the
                        # transaction scope to avoid duplicate imports.
                        if pool.plan.billing_cycle == "yearly":
                            next_end = now + relativedelta(years=1)
                        elif pool.plan.billing_cycle == "lifetime":
                            next_end = now + relativedelta(years=2)
                        else:
                            next_end = now + relativedelta(months=1)

                        pool.current_period_start = now
                        pool.current_period_end = next_end
                        pool.activated_at = now
                        pool.save(update_fields=[
                            "current_period_start", "current_period_end",
                            "activated_at", "updated_at"
                        ])
                        continue

                    # Consume one period
                    pool.periods_consumed += 1
                    periods_remaining = pool.credit_periods - pool.periods_consumed

                    # Create transaction record
                    CreditTransaction.objects.create(
                        credit_pool=pool,
                        action=CreditTransaction.TransactionType.PERIOD_CONSUME,
                        periods_delta=-1,
                        amount_cents_delta=0,
                        periods_balance=periods_remaining,
                        reason=f"Period {pool.periods_consumed} of {pool.credit_periods} consumed",
                    )

                    if periods_remaining <= 0:
                        # Pool is exhausted
                        pool.status = CreditPool.CreditPoolStatus.EXHAUSTED
                        pool.current_period_start = None
                        pool.current_period_end = None
                        pool.save(update_fields=[
                            "periods_consumed", "status",
                            "current_period_start", "current_period_end",
                            "updated_at"
                        ])
                        stats["exhausted"] += 1
                        logger.info(
                            f"CREDIT_CONSUME: Pool {pool.id} exhausted "
                            f"(user={pool.user.email}, product={pool.product.slug})"
                        )
                    else:
                        # Start next billing period
                        # BUG-FIX: Use pool.current_period_end (the exact end of the
                        # previous period) as the start of the next period, not `now`.
                        # Previously used `now` which caused drift: if the task runs at
                        # 05:00 UTC but the period ended at 00:00 UTC, the next period
                        # would start 5 hours late, and this drift accumulates.
                        period_start = pool.current_period_end
                        if pool.plan.billing_cycle == "yearly":
                            next_end = period_start + relativedelta(years=1)
                        elif pool.plan.billing_cycle == "lifetime":
                            next_end = period_start + relativedelta(years=2)
                        else:
                            next_end = period_start + relativedelta(months=1)

                        pool.current_period_start = period_start
                        pool.current_period_end = next_end
                        pool.save(update_fields=[
                            "periods_consumed", "current_period_start",
                            "current_period_end", "updated_at"
                        ])
                        stats["consumed"] += 1
                        logger.info(
                            f"CREDIT_CONSUME: Pool {pool.id} period consumed, "
                            f"{periods_remaining} remaining (user={pool.user.email})"
                        )

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        f"CREDIT_CONSUME: Error processing pool {pool.id}: {e}",
                        exc_info=True,
                    )

        logger.info(
            f"Credit period consumption complete: "
            f"{stats['consumed']} consumed, {stats['exhausted']} exhausted, "
            f"{stats['errors']} errors"
        )
        return stats

    except Exception as exc:
        logger.error(f"Credit period consumption task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,
)
def expire_credit_pools(self):
    """Periodic task to mark expired credit pools.

    Called daily by Celery Beat. Finds active pools that have reached their
    expiry and marks them as EXPIRED or EXHAUSTED.

    Two expiry mechanisms (Enhancement 5):
      1. **Hard expiry**: pools with an explicit expires_at set by an admin
         (e.g., promotional credits). A 24-hour grace period applies before
         the pool is hard-expired.
      2. **Soft expiry safety net**: pools where expires_at is None (soft
         expiry) but whose commitment_end has passed AND periods_remaining
         is still > 0. Normally, the consume_credit_periods task handles
         these by marking them EXHAUSTED, but if that task misses a day or
         has an error, this task catches the stragglers.

    BUG-FIX: Previously only handled hard-expiry pools (expires_at__lte=now).
    Now also catches soft-expiry pools that have slipped past their
    commitment_end without being properly exhausted.

    Returns:
        {"expired": int, "grace_period": int, "soft_expired": int, "errors": int}
    """
    from django.utils import timezone
    from django.db import transaction, models
    from dateutil.relativedelta import relativedelta
    from .models import CreditPool, CreditTransaction

    try:
        now = timezone.now()
        stats = {"expired": 0, "grace_period": 0, "soft_expired": 0, "errors": 0}

        # ── Part 1: Hard-expiry pools (expires_at is set) ──────────────────
        # ENHANCEMENT-3: Apply a 24-hour grace period before hard-expiring.
        # During the grace period, the pool remains ACTIVE and the frontend
        # displays an urgent expiry banner. After the grace period, the pool
        # is marked EXPIRED.
        hard_expiry_pools = CreditPool.objects.filter(
            status=CreditPool.CreditPoolStatus.ACTIVE,
            expires_at__lte=now,
        ).select_related("user", "product", "plan")

        for pool in hard_expiry_pools:
            try:
                # ENHANCEMENT-3: 24-hour grace period before hard expiry
                grace_period_end = pool.expires_at + timezone.timedelta(
                    hours=CREDIT_EXPIRY_GRACE_HOURS
                )

                if now < grace_period_end:
                    # Within grace period — pool remains ACTIVE
                    # Frontend banner handles urgency display
                    stats["grace_period"] += 1
                    logger.info(
                        f"CREDIT_EXPIRE: Pool {pool.id} in grace period "
                        f"(user={pool.user.email}, grace ends {grace_period_end})"
                    )
                    continue

                # Past grace period — hard expire
                with transaction.atomic():
                    periods_remaining = pool.credit_periods - pool.periods_consumed

                    # Create transaction record
                    CreditTransaction.objects.create(
                        credit_pool=pool,
                        action=CreditTransaction.TransactionType.EXPIRE,
                        periods_delta=-periods_remaining,
                        amount_cents_delta=0,
                        periods_balance=0,
                        reason="Credit pool expired (hard expiry date reached)",
                    )

                    # Mark as expired
                    pool.status = CreditPool.CreditPoolStatus.EXPIRED
                    pool.save(update_fields=["status", "updated_at"])

                    stats["expired"] += 1
                    logger.info(
                        f"CREDIT_EXPIRE: Pool {pool.id} expired "
                        f"(user={pool.user.email}, {periods_remaining} periods lost)"
                    )

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"CREDIT_EXPIRE: Error expiring pool {pool.id}: {e}",
                    exc_info=True,
                )

        # ── Part 2: Soft-expiry safety net ─────────────────────────────────
        # BUG-FIX: Catch soft-expiry pools (expires_at is None) that have
        # slipped past their commitment_end without being properly exhausted
        # by the consume_credit_periods task. This can happen if that task
        # misses a day or encounters an error.
        #
        # We cannot filter on commitment_end in the ORM (it's a @property),
        # so we compute the expected commitment_end from activated_at +
        # credit_periods and filter in Python.
        soft_expiry_pools = CreditPool.objects.filter(
            status=CreditPool.CreditPoolStatus.ACTIVE,
            expires_at__isnull=True,
            activated_at__isnull=False,
            periods_consumed__lt=models.F("credit_periods"),
        ).select_related("user", "product", "plan")

        for pool in soft_expiry_pools:
            try:
                c_end = pool.commitment_end
                if not c_end or c_end > now:
                    continue  # Not yet past commitment end

                # commitment_end has passed but pool still has remaining periods
                # This is a safety net — normally consume_credit_periods handles this
                with transaction.atomic():
                    periods_remaining = pool.credit_periods - pool.periods_consumed

                    CreditTransaction.objects.create(
                        credit_pool=pool,
                        action=CreditTransaction.TransactionType.EXPIRE,
                        periods_delta=-periods_remaining,
                        amount_cents_delta=0,
                        periods_balance=0,
                        reason=(
                            f"Credit pool soft-expired: commitment_end ({c_end.strftime('%Y-%m-%d')}) "
                            f"passed with {periods_remaining} period(s) remaining (safety net)"
                        ),
                    )

                    pool.status = CreditPool.CreditPoolStatus.EXHAUSTED
                    pool.current_period_start = None
                    pool.current_period_end = None
                    pool.save(update_fields=[
                        "status", "current_period_start",
                        "current_period_end", "updated_at",
                    ])

                    stats["soft_expired"] += 1
                    logger.warning(
                        f"CREDIT_EXPIRE_SAFETY: Pool {pool.id} soft-expired "
                        f"(commitment_end={c_end}, {periods_remaining} periods remaining, "
                        f"user={pool.user.email}) — consume task may have missed this pool"
                    )

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"CREDIT_EXPIRE: Error soft-expiring pool {pool.id}: {e}",
                    exc_info=True,
                )

        if stats["expired"] > 0 or stats["grace_period"] > 0 or stats["soft_expired"] > 0:
            logger.info(
                f"Credit expiry complete: {stats['expired']} hard-expired, "
                f"{stats['grace_period']} in grace period, "
                f"{stats['soft_expired']} soft-expired (safety net), "
                f"{stats['errors']} errors"
            )
        return stats

    except Exception as exc:
        logger.error(f"Credit expiry task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)


# =============================================================================
# Credit Expiry Warning Notifications (Enhancement 3)
# =============================================================================


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min between retries
)
def send_credit_expiry_warning(self):
    """Daily task to send pre-expiry warning emails for active credit pools.

    Called daily by Celery Beat at 05:15 UTC. Finds active credit pools
    approaching their expiry or period end and sends staged warning emails
    at 14-day, 7-day, and 1-day thresholds before expiry.

    Each warning is sent at most once per pool, tracked via
    CreditNotificationLog to prevent duplicate emails.
    """
    from django.utils import timezone
    from django.db import IntegrityError, models
    from django.core.mail import send_mail
    from django.conf import settings
    from .models import (
        CreditPool,
        CreditNotificationLog,
    )

    try:
        now = timezone.now()
        app_domain = getattr(settings, "STRIPE_APP_DOMAIN", "")
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@sattabase.com")

        # BUG-FIX: periods_remaining is a Python @property, not a DB field.
        # Django ORM cannot filter on @property — use F-expression instead.
        pools = (
            CreditPool.objects.filter(
                status=CreditPool.CreditPoolStatus.ACTIVE,
                periods_consumed__lt=models.F("credit_periods"),
            )
            .select_related("user", "plan", "product")
            .order_by("expires_at")
        )

        stats = {
            "checked": 0,
            "expiry_14d_sent": 0,
            "expiry_7d_sent": 0,
            "expiry_1d_sent": 0,
            "skipped": 0,
            "errors": 0,
        }

        for pool in pools:
            stats["checked"] += 1
            try:
                # Determine the effective end date for this pool
                # ENHANCEMENT-4/5: Use expires_at (hard deadline) when set, otherwise
                # fall back to commitment_end (natural end based on periods consumed).
                # When both are None, fall back to current_period_end.
                effective_end = pool.expires_at or pool.commitment_end or pool.current_period_end
                if not effective_end:
                    stats["skipped"] += 1
                    continue

                # ENHANCEMENT-5: Classify expiry type for messaging
                is_hard_expiry = pool.expires_at is not None

                days_until_expiry = (effective_end - now).days

                # Check each threshold
                for threshold_days in CREDIT_EXPIRY_WARNING_DAYS:
                    if days_until_expiry > threshold_days:
                        # Not yet within this threshold window
                        continue

                    # Determine the notification type
                    if threshold_days == 14:
                        notif_type = CreditNotificationLog.NotificationType.EXPIRY_14D
                    elif threshold_days == 7:
                        notif_type = CreditNotificationLog.NotificationType.EXPIRY_7D
                    elif threshold_days == 1:
                        notif_type = CreditNotificationLog.NotificationType.EXPIRY_1D
                    else:
                        continue

                    # Skip if this notification was already sent
                    if CreditNotificationLog.objects.filter(
                        credit_pool=pool,
                        notification_type=notif_type,
                    ).exists():
                        continue

                    # Build and send the warning email
                    display_name = pool.user.first_name or pool.user.email
                    end_date_str = effective_end.strftime("%B %d, %Y")
                    days_left = max(0, days_until_expiry)

                    # Email content varies by threshold
                    # ENHANCEMENT-5: Adjust messaging based on expiry type
                    if threshold_days == 14:
                        subject = f"Your credit commitment ends in 2 weeks — {pool.product.name}"
                        urgency = "reminder"
                        if is_hard_expiry:
                            intro = (
                                f"Hi {display_name},\n\n"
                                f"Your {pool.product.name} - {pool.plan.name} credit has a hard deadline "
                                f"of {end_date_str}. Access will end on this date even if you have "
                                f"remaining periods.\n"
                                f"You have {pool.periods_remaining} billing period(s) remaining."
                            )
                        else:
                            intro = (
                                f"Hi {display_name},\n\n"
                                f"Your {pool.product.name} - {pool.plan.name} credit commitment "
                                f"will end on {end_date_str}.\n"
                                f"You have {pool.periods_remaining} billing period(s) remaining."
                            )
                        badge_text = "2 Weeks Left"
                        badge_color = "#F59E0B"  # amber
                    elif threshold_days == 7:
                        subject = f"Your access will expire in {days_left} day(s) — {pool.product.name}"
                        urgency = "warning"
                        if is_hard_expiry:
                            intro = (
                                f"Hi {display_name},\n\n"
                                f"Your {pool.product.name} - {pool.plan.name} credit has a hard deadline "
                                f"of {end_date_str}. After this date, your access will end regardless "
                                f"of remaining periods."
                            )
                        else:
                            intro = (
                                f"Hi {display_name},\n\n"
                                f"Your {pool.product.name} - {pool.plan.name} credit commitment "
                                f"expires on {end_date_str}.\n"
                                f"After expiry, you will lose access to premium features."
                            )
                        badge_text = f"{days_left} Day(s) Left"
                        badge_color = "#F97316"  # orange
                    else:  # 1 day
                        subject = f"URGENT: Your credit expires tomorrow — {pool.product.name}"
                        urgency = "urgent"
                        if is_hard_expiry:
                            intro = (
                                f"Hi {display_name},\n\n"
                                f"Your {pool.product.name} - {pool.plan.name} credit has a hard deadline "
                                f"of {end_date_str}. This is your final notice — access will end on this "
                                f"date regardless of remaining periods."
                            )
                        else:
                            intro = (
                                f"Hi {display_name},\n\n"
                                f"Your {pool.product.name} - {pool.plan.name} credit commitment "
                                f"expires on {end_date_str}.\n"
                                f"This is your final notice — access will be revoked after expiry."
                            )
                        badge_text = "Final Notice"
                        badge_color = "#EF4444"  # red

                    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0;padding:0;background-color:#f4f5f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f5f7;padding:32px 0;">
<tr><td align="center">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

<!-- Header -->
<tr><td style="background-color:#2563EB;padding:32px 40px;">
<h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:700;letter-spacing:-0.3px;">SattaBase</h1>
<p style="margin:4px 0 0;color:#BFDBFE;font-size:13px;">Billing &amp; Subscription Platform</p>
</td></tr>

<!-- Urgency Badge -->
<tr><td style="padding:32px 40px 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="background-color:{badge_color}15;border:1px solid {badge_color};border-radius:6px;padding:6px 14px;">
<span style="color:{badge_color};font-size:13px;font-weight:600;">&#9888; {badge_text}</span>
</td></tr></table>
</td></tr>

<!-- Message -->
<tr><td style="padding:20px 40px 0;">
<h2 style="margin:0;color:#111827;font-size:22px;font-weight:700;">Credit Expiry {urgency.capitalize()}</h2>
<p style="margin:8px 0 0;color:#6B7280;font-size:15px;line-height:1.5;">
{intro}
</p>
</td></tr>

<!-- Details -->
<tr><td style="padding:24px 40px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F9FAFB;border-radius:8px;border:1px solid #E5E7EB;">
<tr><td style="padding:20px 24px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0">
<tr>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Product</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{pool.product.name}</span>
</td>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Plan</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{pool.plan.name}</span>
</td>
</tr>
<tr>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Periods Remaining</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{pool.periods_remaining} / {pool.credit_periods}</span>
</td>
<td style="padding:8px 0;border-bottom:1px solid #E5E7EB;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Expires</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{end_date_str}</span>
</td>
</tr>
<tr>
<td style="padding:8px 0;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Auto-Renewal</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">No</span>
</td>
<td style="padding:8px 0;text-align:right;">
<span style="color:#6B7280;font-size:12px;font-weight:500;text-transform:uppercase;letter-spacing:0.5px;">Amount</span><br>
<span style="color:#111827;font-size:14px;font-weight:600;">{pool.display_amount}</span>
</td>
</tr>
</table>
</td></tr></table>
</td></tr>

<!-- Action Buttons -->
<tr><td style="padding:28px 40px 0;">
<table role="presentation" cellpadding="0" cellspacing="0"><tr>
<td style="background-color:#2563EB;border-radius:6px;padding:0;">
<a href="{app_domain}/dashboard/billing/credits/request" style="display:inline-block;padding:12px 24px;color:#ffffff;font-size:14px;font-weight:600;text-decoration:none;">Purchase Credits</a>
</td>
<td style="width:12px;"></td>
<td style="background-color:#F3F4F6;border-radius:6px;padding:0;">
<a href="{app_domain}/dashboard/billing" style="display:inline-block;padding:12px 24px;color:#374151;font-size:14px;font-weight:600;text-decoration:none;">Subscribe with Stripe</a>
</td>
</tr></table>
</td></tr>

<!-- Info -->
<tr><td style="padding:24px 40px 0;">
<p style="margin:0;color:#6B7280;font-size:13px;line-height:1.6;">
Credits do not auto-renew. To maintain uninterrupted access, please purchase new credits before your commitment ends or subscribe via Stripe for automatic renewal.
</p>
</td></tr>

<!-- Footer -->
<tr><td style="padding:32px 40px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #E5E7EB;">
<tr><td style="padding-top:20px;">
<p style="margin:0;color:#9CA3AF;font-size:11px;line-height:1.5;">
This email was sent by SattaBase. If you have any questions, please contact our support team.
</p>
</td></tr></table>
</td></tr>

</table>
</td></tr></table>
</body>
</html>"""

                    # Plain text fallback
                    body = (
                        f"Hi {display_name},\n\n"
                        f"Your {pool.product.name} - {pool.plan.name} credit commitment "
                        f"expires on {end_date_str}.\n"
                        f"You have {pool.periods_remaining} billing period(s) remaining.\n\n"
                        f"To maintain uninterrupted access, please:\n"
                        f"  - Purchase new credits before your current commitment ends\n"
                        f"  - Or subscribe via Stripe for automatic renewal\n\n"
                        f"Purchase credits: {app_domain}/dashboard/billing/credits/request\n"
                        f"Subscribe: {app_domain}/dashboard/billing\n\n"
                        f"Thank you for being a valued customer.\n\n"
                        f"— The SattaBase Team"
                    )

                    sent = send_mail(
                        subject=subject,
                        message=body,
                        html_message=html_body,
                        from_email=from_email,
                        recipient_list=[pool.user.email],
                        fail_silently=True,
                    )

                    if sent:
                        # Log the notification to prevent duplicates
                        try:
                            CreditNotificationLog.objects.create(
                                credit_pool=pool,
                                notification_type=notif_type,
                            )
                        except IntegrityError:
                            # Race condition — another worker already logged it
                            pass

                        notif_key = f"expiry_{threshold_days}d_sent"
                        stats[notif_key] += 1
                        logger.info(
                            f"CREDIT_EXPIRY_WARNING: Sent {notif_type} to "
                            f"{pool.user.email} for pool={pool.id} "
                            f"(days_left={days_until_expiry})"
                        )
                    else:
                        stats["errors"] += 1
                        logger.error(
                            f"CREDIT_EXPIRY_WARNING: Failed to send {notif_type} to "
                            f"{pool.user.email} for pool={pool.id}"
                        )

            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"CREDIT_EXPIRY_WARNING: Error processing pool={pool.id}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"Credit expiry warning task completed: "
            f"checked={stats['checked']}, "
            f"14d={stats['expiry_14d_sent']}, "
            f"7d={stats['expiry_7d_sent']}, "
            f"1d={stats['expiry_1d_sent']}, "
            f"skipped={stats['skipped']}, "
            f"errors={stats['errors']}"
        )
        return stats

    except Exception as exc:
        logger.error(f"Credit expiry warning task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
