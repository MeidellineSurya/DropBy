from uuid import UUID

from app.db.session import SessionLocal
from app.models.drops import Drop
from app.services.notifications import find_users_to_notify_for_drop, send_push
from app.workers.celery_app import celery_app

# Below this, "450m away" reads as noise rather than a useful distance —
# round down to whole km once we're this far out.
NOTIFICATION_DISTANCE_KM_THRESHOLD_M = 1000


def _format_distance(distance_m: float) -> str:
    """Same nearest-50m rounding Detect uses in-app (see
    proximity.snapshot_for) — avoids handing out a precise-enough distance
    to triangulate the venue from a notification alone."""
    if distance_m >= NOTIFICATION_DISTANCE_KM_THRESHOLD_M:
        return f"{distance_m / 1000:.1f}km"
    return f"{max(50, round(distance_m / 50) * 50)}m"


@celery_app.task
def notify_users_of_new_drop(drop_id: str) -> int:
    """Triggered when a Drop activates. Discovery is notification-driven —
    every user gets told a Drop exists, not just people already nearby (see
    product design); Detect itself only ever reveals category and distance, never
    the offer, title, or business name — that's still gated behind Reveal
    once someone actually gets close."""
    with SessionLocal() as db:
        drop = db.get(Drop, UUID(drop_id))
        if drop is None:
            return 0
        category_label = drop.category.value.replace("_", " ").title()
        recipients = find_users_to_notify_for_drop(db, drop.id)
        for user_id, distance_m in recipients:
            payload = {
                "title": "New Drop detected",
                "body": f"A {category_label} Drop appeared {_format_distance(distance_m)} away",
                "drop_id": str(drop.id),
                "category": drop.category.value,
                "distance_m": distance_m,
            }
            send_push(db, user_id, "drop_nearby", payload)
        return len(recipients)


@celery_app.task
def send_push_task(user_id: str, notification_type: str, payload: dict) -> None:
    with SessionLocal() as db:
        send_push(db, UUID(user_id), notification_type, payload)
