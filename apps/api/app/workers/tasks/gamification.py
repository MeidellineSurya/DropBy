import asyncio
from uuid import UUID

from app.db.session import SessionLocal
from app.models.groups import Group
from app.services.gamification import award_xp_for_redemption
from app.services.squad_state import group_snapshot
from app.workers.celery_app import celery_app
from app.workers.tasks.notifications import send_push_task
from app.ws.manager import publish
from ws_contracts.events import BadgeUnlocked, PowerupGranted, RedemptionConfirmed


def _publish(topic: str, message: dict) -> None:
    asyncio.run(publish(topic, message))


@celery_app.task
def award_xp_for_redemption_task(redemption_id: str) -> dict:
    with SessionLocal() as db:
        result = award_xp_for_redemption(db, UUID(redemption_id))

        member_ids: list[str] = []
        group = db.get(Group, UUID(result.group_id))
        if group is not None:
            member_ids = [member.user_id for member in group_snapshot(db, group).members]

        confirmed_event = RedemptionConfirmed(
            group_id=result.group_id,
            redemption_id=result.redemption_id,
            xp_awarded=result.xp_awarded,
        ).model_dump(mode="json")
        for topic in {f"ws:group:{result.group_id}", *(f"ws:user:{uid}" for uid in member_ids)}:
            _publish(topic, confirmed_event)
        for user_id in member_ids:
            send_push_task.delay(
                user_id,
                "redemption_confirmed",
                {
                    "title": "Drop redeemed!",
                    "body": f"You earned {result.xp_awarded.get(user_id, 0)} XP",
                    "redemption_id": result.redemption_id,
                },
            )

        for user_id, badges in result.badges_unlocked.items():
            for badge in badges:
                badge_event = BadgeUnlocked(
                    badge_code=badge.code, name=badge.name, icon_url=badge.icon_url
                ).model_dump(mode="json")
                _publish(f"ws:user:{user_id}", badge_event)
                send_push_task.delay(
                    user_id,
                    "badge_unlocked",
                    {"title": "New badge unlocked!", "body": badge.name, "badge_code": badge.code},
                )

        for user_id, powerups in result.powerups_granted.items():
            counts: dict[str, int] = {}
            for powerup_type in powerups:
                counts[powerup_type.value] = counts.get(powerup_type.value, 0) + 1
            for powerup_type_value, count in counts.items():
                powerup_event = PowerupGranted(
                    powerup_type=powerup_type_value, count=count
                ).model_dump(mode="json")
                _publish(f"ws:user:{user_id}", powerup_event)
                send_push_task.delay(
                    user_id,
                    "powerup_granted",
                    {
                        "title": "Powerup earned!",
                        "body": f"+{count} {powerup_type_value.replace('_', ' ')}",
                        "powerup_type": powerup_type_value,
                        "count": count,
                    },
                )

        return {
            "xp_awarded": result.xp_awarded,
            "badges_unlocked": {
                user_id: [badge.code for badge in badges]
                for user_id, badges in result.badges_unlocked.items()
            },
            "powerups_granted": {
                user_id: [powerup_type.value for powerup_type in powerups]
                for user_id, powerups in result.powerups_granted.items()
            },
        }
