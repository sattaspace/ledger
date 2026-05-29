"""Celery tasks for the Ledger sister domain.

Scheduled tasks:
  - generate_due_bills: Auto-generate transactions for bills due today
  - refresh_exchange_rates: Refresh cached exchange rates from Sattabase

Both tasks are registered in ledger/celery.py beat_schedule and run
automatically by Celery Beat when the worker is running.
"""

import logging
from decimal import Decimal

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_due_bills(self):
    """Auto-generate EXPENSE transactions for all ACTIVE bills due today.

    Scans the Bill table for records where:
      - status = "ACTIVE"
      - next_due_date <= today

    For each matching bill, calls bill.generate_transaction() which:
      1. Creates an EXPENSE Transaction linked to the bill
      2. Advances next_due_date by one recurrence period

    This task is idempotent — generate_transaction() checks bill.status
    before creating anything, so duplicate runs are safe.

    Runs daily at 06:00 UTC via Celery Beat.
    """
    from django.utils import timezone

    today = timezone.now().date()

    try:
        from api.models import Bill

        due_bills = Bill.objects.filter(
            status="ACTIVE",
            next_due_date__lte=today,
            is_deleted=False,
        ).select_related("account", "category")

        generated = 0
        failed = 0

        for bill in due_bills:
            try:
                txn = bill.generate_transaction()
                if txn is not None:
                    generated += 1
                    logger.info(
                        "Auto-generated transaction %s for bill %s (user=%s, payee=%s)",
                        txn.id, bill.id, bill.user_id, bill.payee,
                    )
                else:
                    logger.debug(
                        "Bill %s skipped (not active after check)", bill.id,
                    )
            except Exception as exc:
                failed += 1
                logger.error(
                    "Failed to generate transaction for bill %s (user=%s): %s",
                    bill.id, bill.user_id, exc,
                )

        logger.info(
            "Bill auto-generation complete: %d generated, %d failed, %d total due",
            generated, failed, due_bills.count(),
        )
        return {
            "generated": generated,
            "failed": failed,
            "total_due": due_bills.count(),
        }

    except Exception as exc:
        logger.error("Bill auto-generation task failed: %s", exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical("Bill auto-generation failed after max retries: %s", exc)
            return {"error": str(exc)}


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def refresh_exchange_rates(self):
    """Refresh cached exchange rates from the Sattabase base backend.

    Fetches rates for USD, EUR, and BDT (the most commonly used base
    currencies) and caches them in Redis for use by api/currency.py.

    This ensures that even if no user has triggered a cache miss recently,
    the rates are still fresh for the next request.

    Runs every 6 hours via Celery Beat (aligned with EXCHANGE_RATE_CACHE_TTL).
    """
    try:
        from api.currency import fetch_and_cache_rates

        results = {}
        for base_currency in ("USD", "EUR", "BDT"):
            try:
                rates = fetch_and_cache_rates(base_currency)
                results[base_currency] = len(rates)
                logger.info(
                    "Refreshed %d exchange rates for base=%s",
                    len(rates), base_currency,
                )
            except Exception as exc:
                results[base_currency] = f"error: {exc}"
                logger.error(
                    "Failed to refresh exchange rates for base=%s: %s",
                    base_currency, exc,
                )

        logger.info("Exchange rate refresh complete: %s", results)
        return results

    except Exception as exc:
        logger.error("Exchange rate refresh task failed: %s", exc)
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.critical("Exchange rate refresh failed after max retries: %s", exc)
            return {"error": str(exc)}
