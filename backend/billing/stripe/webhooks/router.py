"""Webhook router — signature verification, event logging, handler dispatch.

This is the entry-point called by the controller.  All webhook processing
funnels through here.
"""

import json
import logging
import signal
from contextlib import contextmanager
from typing import Optional

from django.db import transaction

from ...models import WebhookEventLog
from ..client import verify_webhook_signature
from .handlers.checkout import handle_checkout_completed
from .handlers.subscription import (
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
    handle_trial_will_end,
)
from .handlers.invoice import (
    handle_invoice_payment_succeeded,
    handle_invoice_payment_failed,
    handle_invoice_created,
)
from .handlers.charge import handle_charge_refunded, handle_customer_updated

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 25

HANDLED_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "customer.subscription.trial_will_end",
    "charge.refunded",
    "customer.updated",
    "invoice.created",
}

_EVENT_MAP = {
    "checkout.session.completed": handle_checkout_completed,
    "customer.subscription.created": handle_subscription_created,
    "customer.subscription.updated": handle_subscription_updated,
    "customer.subscription.deleted": handle_subscription_deleted,
    "invoice.payment_succeeded": handle_invoice_payment_succeeded,
    "invoice.payment_failed": handle_invoice_payment_failed,
    "customer.subscription.trial_will_end": handle_trial_will_end,
    "charge.refunded": handle_charge_refunded,
    "customer.updated": handle_customer_updated,
    "invoice.created": handle_invoice_created,
}


@contextmanager
def _timeout(seconds: int):
    """Raise TimeoutError after *seconds* (Unix SIGALRM)."""

    def _raise(signum, frame):
        raise TimeoutError(f"Webhook processing exceeded {seconds}s")

    try:
        signal.signal(signal.SIGALRM, _raise)
        signal.alarm(seconds)
        yield
    finally:
        signal.alarm(0)
        try:
            signal.signal(signal.SIGALRM, signal.SIG_DFL)
        except (ValueError, OSError):
            pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_and_parse(payload: bytes, sig_header: str) -> dict:
    """Verify Stripe signature and return event dict."""
    return verify_webhook_signature(payload, sig_header)


def record_event(event: dict) -> Optional[WebhookEventLog]:
    """Record event for audit.  Returns None on DB error."""
    event_id = event["id"]
    event_type = event["type"]
    try:
        log_entry, created = WebhookEventLog.objects.get_or_create(
            event_id=event_id,
            defaults={"event_type": event_type, "payload": event},
        )
        if created:
            logger.info(f"Recorded webhook: {event_type} ({event_id})")
        else:
            logger.info(f"Duplicate webhook: {event_type} ({event_id})")
        return log_entry
    except Exception as e:
        logger.error(f"Failed to record webhook {event_id}: {e}")
        return None


def process_event(event: dict) -> None:
    """Route event to the correct handler."""
    event_type = event["type"]
    event_id = event["id"]

    if event_type not in HANDLED_EVENTS:
        logger.info(f"Ignoring unhandled event: {event_type}")
        return

    handler = _EVENT_MAP.get(event_type)
    if not handler:
        logger.warning(f"No handler for: {event_type}")
        return

    try:
        with _timeout(TIMEOUT_SECONDS):
            with transaction.atomic():
                handler(event)
        WebhookEventLog.objects.filter(event_id=event_id).update(processed=True)
        logger.info(f"Processed webhook: {event_type} ({event_id})")
    except TimeoutError as e:
        msg = str(e)
        logger.error(f"Timeout: {event_type} ({event_id}): {msg}")
        WebhookEventLog.objects.filter(event_id=event_id).update(
            processed=False, error_message=msg[:500]
        )
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(f"Failed: {event_type} ({event_id}): {msg}", exc_info=True)
        WebhookEventLog.objects.filter(event_id=event_id).update(
            processed=False, error_message=msg[:500]
        )


def reconcile_unprocessed(max_age_hours: int = 24) -> dict:
    """Retry failed webhook events.  For Celery periodic task."""
    from django.utils import timezone

    cutoff = timezone.now() - timezone.timedelta(hours=max_age_hours)
    unprocessed = WebhookEventLog.objects.filter(
        processed=False,
        error_message__gt="",
        created_at__gte=cutoff,
    ).order_by("created_at")[:50]

    result = {"retried": 0, "succeeded": 0, "failed": 0}

    for log_entry in unprocessed:
        payload = log_entry.payload
        if not payload:
            continue
        result["retried"] += 1
        try:
            process_event(payload)
            result["succeeded"] += 1
        except Exception as e:
            result["failed"] += 1
            log_entry.error_message = f"Reconcile: {type(e).__name__}: {str(e)[:400]}"
            log_entry.save(update_fields=["error_message", "updated_at"])
            logger.error(f"Reconcile failed for {log_entry.event_id}: {e}")

    logger.info(
        f"Reconciliation: {result['retried']} retried, "
        f"{result['succeeded']} ok, {result['failed']} failed"
    )
    return result
