"""Celery application (broker/result backend: Redis).

Owner: Soughat
"""
from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery("lendwise", broker=settings.redis_url, backend=settings.redis_url, include=["app.workers.tasks"])
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="Asia/Kolkata",
    beat_schedule={},  # e.g. payout status polling, report cleanup
)
