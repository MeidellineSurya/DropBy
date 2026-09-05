"""End-to-end verification for the discovery engine's stateful dependencies."""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import monotonic, sleep
from typing import cast
from uuid import UUID, uuid4

from geoalchemy2.elements import WKTElement
from redis import Redis
from sqlalchemy import delete, select, text
from websockets.sync.client import connect

from app.core.config import settings
from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.businesses import Business, BusinessStatus
from app.models.drops import (
    Drop,
    DropCategory,
    DropStatus,
    DropType,
    DropViewEvent,
    DropViewStage,
)
from app.models.groups import Group, GroupInvite, GroupMember, GroupStatus
from app.models.users import User
from app.services.drop_lifecycle import create_drop
from app.services.squad_state import create_group, join_group


@dataclass
class VerificationRecords:
    business_id: UUID = field(default_factory=uuid4)
    drop_id: UUID | None = None
    group_ids: list[UUID] = field(default_factory=list)
    user_ids: list[UUID] = field(default_factory=lambda: [uuid4() for _ in range(4)])


def _join_squad(group_id: UUID, user_id: UUID) -> GroupStatus:
    """Join using an independent transaction, just as separate requests do."""
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            raise AssertionError("verification user disappeared")
        snapshot, added, _ = join_group(db, group_id, user)
        if not added:
            raise AssertionError("verification member was not added")
        return GroupStatus(snapshot.status)


def _verify_postgres(records: VerificationRecords) -> None:
    """Create two competing squads and prove only one can reserve capacity."""
    suffix = uuid4().hex
    now = datetime.now(timezone.utc)
    user_ids = records.user_ids
    business_id = records.business_id

    with SessionLocal() as db:
        postgis_version = db.scalar(text("SELECT PostGIS_Version()"))
        if not postgis_version:
            raise AssertionError("PostGIS extension is unavailable")

        db.add(
            Business(
                id=business_id,
                name="Discovery Verification Venue",
                category="activity_entertainment",
                location=WKTElement("POINT(144.9674 -37.8119)", srid=4326),
                owner_email=f"verify-business-{suffix}@dropby.test",
                password_hash="verification-only",
                verified=True,
                status=BusinessStatus.active,
            )
        )
        for index, user_id in enumerate(user_ids, start=1):
            db.add(
                User(
                    id=user_id,
                    email=f"verify-user-{index}-{suffix}@dropby.test",
                    password_hash="verification-only",
                    display_name=f"Verifier {index}",
                    preferences=["activity_entertainment"],
                    location_permission="while_using",
                    onboarding_completed_at=now,
                    last_location=WKTElement("POINT(144.9674 -37.8119)", srid=4326),
                    last_location_at=now,
                )
            )
        db.flush()

        drop = create_drop(
            db,
            business_id=business_id,
            title="Atomic Capacity Verification",
            description="Temporary record created by dev.cmd verify",
            category=DropCategory.activity_entertainment,
            drop_type=DropType.squad,
            latitude=-37.8119,
            longitude=144.9674,
            min_group_size=2,
            max_group_size=4,
            max_capacity_participants=2,
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(minutes=10),
            publish=True,
        )
        records.drop_id = drop.id

        for user_id in user_ids:
            db.add(
                DropViewEvent(
                    user_id=user_id,
                    drop_id=drop.id,
                    stage=DropViewStage.discover,
                )
            )
        db.commit()

        leaders = [db.get(User, user_ids[0]), db.get(User, user_ids[2])]
        if any(leader is None for leader in leaders):
            raise AssertionError("verification leader could not be loaded")
        first = create_group(db, drop.id, cast(User, leaders[0]), open_to_nearby=True)
        second = create_group(db, drop.id, cast(User, leaders[1]), open_to_nearby=True)
        records.group_ids = [UUID(first.id), UUID(second.id)]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_join_squad, records.group_ids[0], user_ids[1]),
            pool.submit(_join_squad, records.group_ids[1], user_ids[3]),
        ]
        returned_statuses = [future.result(timeout=15) for future in futures]

    with SessionLocal() as db:
        persisted_statuses = list(
            db.scalars(
                select(Group.status)
                .where(Group.id.in_(records.group_ids))
                .order_by(Group.id)
            ).all()
        )
        drop = db.get(Drop, records.drop_id)
        if drop is None:
            raise AssertionError("verification Drop disappeared")
        expected = sorted([GroupStatus.ready.value, GroupStatus.cancelled.value])
        actual = sorted(status.value for status in persisted_statuses)
        if actual != expected:
            raise AssertionError(
                f"expected one ready and one cancelled squad, got {actual}"
            )
        if drop.reserved_count != 2 or drop.status != DropStatus.capacity_reached:
            raise AssertionError(
                "atomic capacity invariant failed: "
                f"reserved={drop.reserved_count}, status={drop.status.value}"
            )
        if sorted(status.value for status in returned_statuses) != expected:
            raise AssertionError("join responses did not match persisted squad states")

    print(f"[ok] PostgreSQL + PostGIS ({postgis_version})")
    print("[ok] Concurrent squad joins reserved exactly 2/2 participants")


def _verify_redis() -> None:
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    channel = f"dropby:verify:{uuid4().hex}"
    payload = f'{{"type":"verification","id":"{uuid4()}"}}'
    pubsub = client.pubsub()
    try:
        client.ping()
        pubsub.subscribe(channel)
        acknowledgement = pubsub.get_message(timeout=2)
        if acknowledgement is None or acknowledgement.get("type") != "subscribe":
            raise AssertionError("Redis subscription was not acknowledged")
        client.publish(channel, payload)
        deadline = monotonic() + 5
        received = None
        while monotonic() < deadline and received is None:
            received = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
            if received is None:
                sleep(0.02)
        if received is None or received.get("data") != payload:
            raise AssertionError("Redis pub/sub message was not received")
    finally:
        pubsub.close()
        client.close()
    print("[ok] Redis publish/subscribe fan-out")


def _verify_websocket(user_id: UUID) -> None:
    token = create_access_token(str(user_id))
    event = {
        "type": "drop.stage_update",
        "drop_id": str(uuid4()),
        "stage": "discover",
        "distance_m": 42,
        "data": {"verification": True},
    }
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        with connect(
            f"ws://127.0.0.1:8000/ws/live?token={token}",
            open_timeout=5,
            close_timeout=2,
        ) as websocket:
            # The handshake is accepted immediately before the server registers
            # the topic; this tiny pause keeps the verification deterministic.
            sleep(0.1)
            redis_client.publish(f"ws:user:{user_id}", json.dumps(event))
            received = json.loads(websocket.recv(timeout=5))
    finally:
        redis_client.close()
    if received != event:
        raise AssertionError(f"WebSocket event mismatch: {received}")
    print("[ok] Authenticated WebSocket delivery through Redis")


def _cleanup(records: VerificationRecords) -> None:
    with SessionLocal() as db:
        if records.group_ids:
            db.execute(
                delete(GroupInvite).where(GroupInvite.group_id.in_(records.group_ids))
            )
            db.execute(
                delete(GroupMember).where(GroupMember.group_id.in_(records.group_ids))
            )
            db.execute(delete(Group).where(Group.id.in_(records.group_ids)))
        if records.drop_id is not None:
            db.execute(
                delete(DropViewEvent).where(DropViewEvent.drop_id == records.drop_id)
            )
            db.execute(delete(Drop).where(Drop.id == records.drop_id))
        db.execute(delete(User).where(User.id.in_(records.user_ids)))
        db.execute(delete(Business).where(Business.id == records.business_id))
        db.commit()


def verify() -> None:
    records = VerificationRecords()
    try:
        _verify_postgres(records)
        _verify_redis()
        _verify_websocket(records.user_ids[0])
        print("Discovery engine integration verification passed.")
    finally:
        _cleanup(records)


if __name__ == "__main__":
    verify()
