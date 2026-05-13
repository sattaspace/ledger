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


app.conf.beat_schedule = {}