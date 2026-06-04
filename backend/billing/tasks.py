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
):
    """Send email notification when a credit request is approved.

    Called after admin approves a CreditPurchaseRequest. Sends a professional
    HTML confirmation email to the user with their credit pool details and
    invoice number.

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
<span style="color:#111827;font-size:14px;font-weight:600;">{periods}</span>
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
Your credits are now active and will be applied to your subscription automatically each billing cycle. You can download your invoice PDF from the Transactions page at any time.
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
        body = (
            f"Hi {display_name},\n\n"
            f"Great news! Your credit purchase request has been approved.\n\n"
            f"Product: {product_name}\n"
            f"Plan: {plan_name}\n"
            f"Amount: {amount_display}\n"
            f"Billing Periods: {periods}\n"
            f"Invoice: {invoice_number}\n\n"
            f"Your credits are now active and will be applied to your subscription "
            f"automatically each billing cycle.\n\n"
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

        # CRIT-04 FIX: Find active pools with select_for_update to prevent race conditions
        # when multiple workers or task overlap attempt to process the same pool
        active_pools = list(CreditPool.objects.filter(
            status=CreditPool.CreditPoolStatus.ACTIVE,
            current_period_end__lte=now,
        ).select_related("user", "product", "plan").select_for_update())

        for pool in active_pools:
            try:
                with transaction.atomic():
                    # Check if this is the first period (not yet activated)
                    if not pool.current_period_start:
                        # Activate the pool - first period starts now
                        pool.current_period_start = now
                        pool.current_period_end = now + timezone.timedelta(
                            days=30 if pool.plan.billing_cycle == "monthly" else 365
                        )
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
                        pool.current_period_start = now
                        pool.current_period_end = now + timezone.timedelta(
                            days=30 if pool.plan.billing_cycle == "monthly" else 365
                        )
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

    Called daily by Celery Beat. Finds active pools where expires_at
    has passed and marks them as expired, regardless of remaining periods.

    This handles the case where an admin sets a hard expiry date on a
    credit pool (e.g., promotional credits that expire after 6 months).

    Returns:
        {"expired": int, "errors": int}
    """
    from django.utils import timezone
    from django.db import transaction
    from .models import CreditPool, CreditTransaction

    try:
        now = timezone.now()
        stats = {"expired": 0, "errors": 0}

        # Find active pools that have expired
        expired_pools = CreditPool.objects.filter(
            status=CreditPool.CreditPoolStatus.ACTIVE,
            expires_at__lte=now,
        ).select_related("user", "product", "plan")

        for pool in expired_pools:
            try:
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

        if stats["expired"] > 0:
            logger.info(
                f"Credit expiry complete: {stats['expired']} expired, "
                f"{stats['errors']} errors"
            )
        return stats

    except Exception as exc:
        logger.error(f"Credit expiry task failed: {exc}", exc_info=True)
        raise self.retry(exc=exc)
