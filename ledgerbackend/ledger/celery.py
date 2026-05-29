# backend/base/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# from celery.schedules import crontab, solar
# from datetime import timedelta
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ledger.settings")
app = Celery("ledger")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.task_track_started = True
app.conf.worker_send_task_events = True


app.conf.beat_schedule = {
    # ── Bill auto-generation ──────────────────────────────────────────
    # Scan for ACTIVE bills with next_due_date <= today and generate
    # EXPENSE transactions for them. Runs daily at 06:00 UTC.
    "generate-due-bills-daily": {
        "task": "api.tasks.generate_due_bills",
        "schedule": crontab(hour=6, minute=0),
    },
    # ── Exchange rate refresh ─────────────────────────────────────────
    # Pre-populate the exchange rate cache for common base currencies
    # so that the first user request doesn't incur a cache-miss latency
    # spike. Runs every 6 hours (aligned with EXCHANGE_RATE_CACHE_TTL).
    "refresh-exchange-rates-every-6h": {
        "task": "api.tasks.refresh_exchange_rates",
        "schedule": crontab(minute=0, hour="*/6"),
    },
}