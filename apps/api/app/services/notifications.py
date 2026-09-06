"""Redemption/gamification module — push dispatch via Firebase Cloud Messaging.

Firebase is optional in dev/test: without fcm_credentials_json_path configured
(or if the SDK/credential fails to load), sends degrade to a logged-but-skipped
NotificationLog row instead of raising, so the rest of a flow (check-in,
confirm, XP award) never fails because push delivery isn't set up.
"""

import logging
from datetime import datetime, timezone
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


def find_users_to_notify_for_drop(db: Session, drop_id: UUID) -> list[tuple[UUID, float]]:
    """Every user with a known location, paired with their distance to the
    Drop — feeds the "new Drop" push alert sent to everyone, not just people
    already nearby (discovery is notification-driven now; see
    product design). No radius or freshness filter: a user doesn't have to be
    in range, or have pinged recently, to be told a Drop exists — they only
    need *some* last known location so a distance can be shown at all.
    Distance here is whatever their last ping says, however old; it's just
    for the notification's "X away" text, not a proximity gate."""
    distance = func.ST_Distance(Drop.location, User.last_location).label("distance_m")
    return list(
        db.execute(
            select(User.id, distance)
            .select_from(User, Drop)
            .where(Drop.id == drop_id, User.last_location.isnot(None))
        ).all()
    )
