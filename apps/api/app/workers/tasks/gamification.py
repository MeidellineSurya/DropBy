from app.workers.celery_app import celery_app


@celery_app.task
def award_xp_for_redemption_task(redemption_id: str) -> None:
    raise NotImplementedError
