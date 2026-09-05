from uuid import UUID

from app.db.session import SessionLocal
from app.models.drops import Drop
from app.services.notifications import find_nearby_users_for_drop, send_push
from app.workers.celery_app import celery_app


@celery_app.task
def notify_users_of_new_drop(drop_id: str) -> int:
    """Triggered when a Drop activates. Alerts every nearby user with a fresh
    location ping if it's Rare or better — matches the brief's "Legendary
    Drop 300m away" curiosity hook; Common/Uncommon Drops stay silent so
    exploration, not notification spam, drives discovery."""
    with SessionLocal() as db:
        drop = db.get(Drop, UUID(drop_id))
        if drop is None or drop.rarity.value not in {"rare", "epic", "legendary"}:
            return 0
        user_ids = find_nearby_users_for_drop(db, drop.id)
        payload = {
            "title": f"{drop.rarity.value.title()} Drop nearby",
            "body": f"{drop.title} just appeared near you",
            "drop_id": str(drop.id),
        }
        for user_id in user_ids:
            send_push(db, user_id, "drop_nearby", payload)
        return len(user_ids)


@celery_app.task
def send_push_task(user_id: str, notification_type: str, payload: dict) -> None:
    with SessionLocal() as db:
        send_push(db, UUID(user_id), notification_type, payload)
