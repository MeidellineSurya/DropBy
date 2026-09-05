from app.workers.celery_app import celery_app


@celery_app.task
def refresh_materialized_views() -> None:
    """Beat, every 5 min: refresh any business-analytics materialized views."""
    raise NotImplementedError
