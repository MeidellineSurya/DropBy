"""Redemption/gamification module — push dispatch via Firebase Cloud Messaging.

Firebase is optional in dev/test: without fcm_credentials_json_path configured
(or if the SDK/credential fails to load), sends degrade to a logged-but-skipped
NotificationLog row instead of raising, so the rest of a flow (check-in,
confirm, XP award) never fails because push delivery isn't set up.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.drops import Drop
from app.models.notifications import NotificationLog, NotificationType, PushStatus
from app.models.users import User, UserDevice

logger = logging.getLogger(__name__)

_firebase_app = None
_firebase_unavailable = False


def _get_firebase_app():
    global _firebase_app, _firebase_unavailable
    if _firebase_app is not None or _firebase_unavailable:
        return _firebase_app
    if not settings.fcm_credentials_json_path:
        _firebase_unavailable = True
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(settings.fcm_credentials_json_path)
        _firebase_app = firebase_admin.initialize_app(cred)
    except Exception:
        logger.warning(
            "Firebase Cloud Messaging is not configured; pushes will be skipped",
            exc_info=True,
        )
        _firebase_unavailable = True
        return None
    return _firebase_app


def send_push(db: Session, user_id: UUID, notification_type: str, payload: dict) -> None:
    """Log the notification and best-effort deliver it to every active device."""
    type_enum = NotificationType(notification_type)
    devices = list(
        db.scalars(
            select(UserDevice).where(UserDevice.user_id == user_id, UserDevice.active.is_(True))
        ).all()
    )
    app = _get_firebase_app()
    push_status = PushStatus.skipped
    sent_at = None

    if devices and app is not None:
        from firebase_admin import messaging

        any_sent = False
        for device in devices:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=str(payload.get("title", "DropBy")),
                        body=str(payload.get("body", "")),
                    ),
                    data={key: str(value) for key, value in payload.items()},
                    token=device.fcm_token,
                )
                messaging.send(message, app=app)
                any_sent = True
            except Exception:
                logger.warning("FCM push failed for device %s", device.id, exc_info=True)
                device.active = False
        push_status = PushStatus.sent if any_sent else PushStatus.failed
        sent_at = datetime.now(timezone.utc) if any_sent else None

    db.add(
        NotificationLog(
            user_id=user_id,
            type=type_enum,
            payload=payload,
            sent_at=sent_at,
            push_status=push_status,
        )
    )
    db.commit()


def register_device(db: Session, user_id: UUID, fcm_token: str, platform: str) -> UserDevice:
    """Upsert by fcm_token: a device re-registering (app relaunch, token
    refresh handled client-side) updates the existing row rather than piling
    up duplicates, and reactivates a token previous send failures marked
    inactive."""
    device = db.scalar(select(UserDevice).where(UserDevice.fcm_token == fcm_token))
    now = datetime.now(timezone.utc)
    if device is None:
        device = UserDevice(user_id=user_id, fcm_token=fcm_token, platform=platform, active=True, last_seen_at=now)
        db.add(device)
    else:
        device.user_id = user_id
        device.platform = platform
        device.active = True
        device.last_seen_at = now
    db.commit()
    db.refresh(device)
    return device


# Higher-level users get a wider "something's nearby" awareness radius for
# the Rare+ Drop push alert, capped so it stays a bonus rather than global reach.
NOTIFICATION_RADIUS_BONUS_PER_LEVEL_M = 50
NOTIFICATION_RADIUS_BONUS_CAP_M = 1000


def find_nearby_users_for_drop(
    db: Session, drop_id: UUID, freshness: timedelta = timedelta(minutes=30)
) -> list[UUID]:
    """Users whose last known location is within a Drop's Detect radius
    (plus a level-scaled bonus) and recent enough to plausibly still be
    nearby — feeds the "Rare+ Drop activated near you" push alert."""
    cutoff = datetime.now(timezone.utc) - freshness
    level_bonus_m = func.least(
        (User.level - 1) * NOTIFICATION_RADIUS_BONUS_PER_LEVEL_M,
        NOTIFICATION_RADIUS_BONUS_CAP_M,
    )
    return list(
        db.scalars(
            select(User.id)
            .select_from(User, Drop)
            .where(
                Drop.id == drop_id,
                User.last_location.isnot(None),
                User.last_location_at >= cutoff,
                func.ST_DWithin(
                    Drop.location, User.last_location, Drop.discovery_radius_m + level_bonus_m
                ),
            )
        ).all()
    )
