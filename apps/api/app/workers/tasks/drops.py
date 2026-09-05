import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.drops import Drop, DropStatus, DropViewEvent
from app.models.groups import Group
from app.services.drop_lifecycle import activate_scheduled, expire_due
from app.services.squad_state import group_snapshot
from app.workers.celery_app import celery_app
from app.workers.tasks.notifications import notify_users_of_new_drop, send_push_task
from app.ws.manager import publish
from ws_contracts.events import DropCountdownWarning, DropExpired, GroupStateUpdate


def _publish(topic: str, message: dict) -> None:
    asyncio.run(publish(topic, message))


@celery_app.task
def activate_scheduled_drops() -> int:
    with SessionLocal() as db:
        drop_ids = activate_scheduled(db)
        for drop_id in drop_ids:
            drop = db.get(Drop, drop_id)
            if drop and drop.ends_at:
                warning_at = drop.ends_at.replace(
                    tzinfo=drop.ends_at.tzinfo or timezone.utc
                ) - timedelta(minutes=5)
                warning_at = warning_at.replace(microsecond=0)
                schedule_drop_countdown.apply_async(args=[str(drop_id)], eta=warning_at)
            notify_users_of_new_drop.delay(str(drop_id))
        return len(drop_ids)


@celery_app.task
def expire_drops_sweep() -> dict[str, int]:
    with SessionLocal() as db:
        drop_ids, group_ids = expire_due(db)
        for drop_id in drop_ids:
            user_ids = set(
                db.scalars(
                    select(DropViewEvent.user_id).where(
                        DropViewEvent.drop_id == drop_id
                    )
                ).all()
            )
            event = DropExpired(drop_id=str(drop_id), reason="time").model_dump(
                mode="json"
            )
            for topic in {
                f"ws:drop:{drop_id}",
                *(f"ws:user:{user_id}" for user_id in user_ids),
            }:
                _publish(topic, event)
        for group_id in group_ids:
            group = db.get(Group, group_id)
            if group is None:
                continue
            snapshot = group_snapshot(db, group)
            event = GroupStateUpdate(
                group_id=snapshot.id,
                drop_id=snapshot.drop_id,
                status=snapshot.status.value,
                current_count=snapshot.current_count,
                min_required=snapshot.min_required,
                max_allowed=snapshot.max_allowed,
                members=[member.model_dump(mode="json") for member in snapshot.members],
                expires_at=snapshot.expires_at,
            ).model_dump(mode="json")
            for topic in {
                f"ws:group:{group_id}",
                *(f"ws:user:{member.user_id}" for member in snapshot.members),
            }:
                _publish(topic, event)
        return {"drops": len(drop_ids), "groups": len(group_ids)}


@celery_app.task
def schedule_drop_countdown(drop_id: str) -> bool:
    with SessionLocal() as db:
        drop = db.get(Drop, UUID(drop_id))
        if drop is None or drop.status not in (
            DropStatus.active,
            DropStatus.capacity_reached,
        ):
            return False
        remaining = max(
            0, int((drop.ends_at - datetime.now(timezone.utc)).total_seconds() / 60)
        )
        if remaining > 5:
            return False
        user_ids = set(
            db.scalars(
                select(DropViewEvent.user_id).where(DropViewEvent.drop_id == drop.id)
            ).all()
        )
        event = DropCountdownWarning(
            drop_id=drop_id, minutes_remaining=remaining
        ).model_dump(mode="json")
        for user_id in user_ids:
            _publish(f"ws:user:{user_id}", event)
            send_push_task.delay(
                str(user_id),
                "countdown_warning",
                {
                    "title": "Drop ending soon!",
                    "body": f"{remaining} minutes left on {drop.title}",
                    "drop_id": drop_id,
                },
            )
        return True
