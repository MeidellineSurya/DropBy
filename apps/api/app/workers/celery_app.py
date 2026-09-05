from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "dropby",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.drops",
        "app.workers.tasks.notifications",
        "app.workers.tasks.gamification",
        "app.workers.tasks.analytics",
    ],
)

celery_app.conf.beat_schedule = {
    "activate-scheduled-drops": {
        "task": "app.workers.tasks.drops.activate_scheduled_drops",
        "schedule": 60.0,
    },
    "expire-drops-sweep": {
        "task": "app.workers.tasks.drops.expire_drops_sweep",
        "schedule": 60.0,
    },
    "refresh-analytics-views": {
        "task": "app.workers.tasks.analytics.refresh_materialized_views",
        "schedule": 300.0,
    },
}
