from app.workers.celery_app import celery_app


@celery_app.task
def activate_scheduled_drops() -> None:
    """Beat, every 60s: flip scheduled Drops whose starts_at has passed to active."""
    raise NotImplementedError


@celery_app.task
def expire_drops_sweep() -> None:
    """Beat, every 60s: expire Drops past ends_at; grace-period sweep for
    in-flight (forming/ready) Groups on capacity_reached/expired Drops."""
    raise NotImplementedError


@celery_app.task
def schedule_drop_countdown(drop_id: str) -> None:
    """Scheduled via apply_async(eta=ends_at - 5min) at Drop activation time.
    Re-verifies the Drop is still active before pushing drop.countdown_warning."""
    raise NotImplementedError
