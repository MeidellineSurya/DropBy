from app.workers.celery_app import celery_app


@celery_app.task
def notify_users_of_new_drop(drop_id: str) -> None:
    raise NotImplementedError


@celery_app.task
def send_push_task(user_id: str, notification_type: str, payload: dict) -> None:
    raise NotImplementedError
