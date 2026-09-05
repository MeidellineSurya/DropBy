"""Detect -> Reveal proximity engine, driven by REST location pings."""

from datetime import datetime, timezone
from uuid import UUID

import redis.asyncio as aioredis
from geoalchemy2 import Geography, Geometry
from redis.exceptions import RedisError
from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.businesses import Business
from app.models.drops import Drop, DropStatus, DropViewEvent, DropViewStage
from app.models.gamification import PerkType, UserExploredCell, UserPerk
from app.models.users import User
from app.schemas.drops import DropSnapshot
from app.services.gamification import RADIUS_PERK_BONUS_PCT, award_territory_bonus, location_cell_for
from app.ws.manager import publish
from ws_contracts.events import DropStageUpdate, Stage, TerritoryBonusAwarded


def stage_for_distance(
    distance_m: float,
    drop: Drop,
    reveal_unlocked: bool = False,
    radius_multiplier: float = 1.0,
) -> DropViewStage:
    """Return the public two-stage state.

    ``discover_radius_m`` remains the close-range threshold in the database for
    migration compatibility. Public clients now receive Reveal at that point.

    radius_multiplier defaults to 1.0 (identical to prior behavior for every
    existing caller); app/services/gamification.py's "bigger_reveal" powerup
    passes a temporary >1.0 value via compute_stage_for_ping below.
    """
    if reveal_unlocked or distance_m <= drop.discover_radius_m * radius_multiplier:
        return DropViewStage.reveal
    return DropViewStage.detect


def snapshot_for(
    drop: Drop,
    business: Business,
    distance_m: float,
    stage: DropViewStage,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
) -> DropSnapshot:
    if stage == DropViewStage.detect:
        return DropSnapshot(
            id=str(drop.id),
            stage=stage.value,
            distance_m=max(50, round(distance_m / 50) * 50),
            rarity=drop.rarity,
            category=drop.category,
            interest_tag=drop.interest_tag,
            min_group_size=drop.min_group_size,
            max_group_size=drop.max_group_size,
        )
    return DropSnapshot(
        id=str(drop.id),
        stage=stage.value,
        distance_m=round(distance_m),
        rarity=drop.rarity,
        category=drop.category,
        interest_tag=drop.interest_tag,
        title=drop.title,
        description=drop.description,
        business_name=business.name,
        address=business.address,
        latitude=latitude,
        longitude=longitude,
        drop_type=drop.drop_type,
        min_group_size=drop.min_group_size,
        max_group_size=drop.max_group_size,
        ends_at=drop.ends_at,
        can_assemble=drop.min_group_size > 1,
    )


async def compute_stage_for_ping(
    db: Session,
    user: User,
    latitude: float,
    longitude: float,
) -> list[DropSnapshot]:
    point = cast(
        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
        Geography(geometry_type="POINT", srid=4326),
    )
    user.last_location = point
    user.last_location_at = datetime.now(timezone.utc)

    # New-territory bonus: independent of any Drop, this rewards the ping
    # landing somewhere the user has never pinged from before. See
    # app/models/gamification.py::UserExploredCell and
    # app/services/gamification.py::award_territory_bonus (which does not
    # commit — the db.commit() below covers it).
    cell = location_cell_for(latitude, longitude)
    new_cell = db.execute(
        insert(UserExploredCell)
        .values(user_id=user.id, cell=cell)
        .on_conflict_do_nothing(index_elements=["user_id", "cell"])
        .returning(UserExploredCell.cell)
    ).scalar()
    territory_bonus_xp = award_territory_bonus(user) if new_cell is not None else 0

    distance = func.ST_Distance(Drop.location, point).label("distance_m")
    drop_geometry = cast(
        Drop.location, Geometry(geometry_type="POINT", srid=4326)
    )
    drop_latitude = func.ST_Y(drop_geometry).label("drop_latitude")
    drop_longitude = func.ST_X(drop_geometry).label("drop_longitude")
    rows = db.execute(
        select(Drop, Business, distance, drop_latitude, drop_longitude)
        .join(Business, Business.id == Drop.business_id)
        .where(
            Drop.status == DropStatus.active,
            Drop.starts_at <= func.now(),
            Drop.ends_at > func.now(),
        )
        .order_by(distance)
    ).all()

    drop_ids = [drop.id for drop, _, _, _, _ in rows]
    revealed_ids: set[UUID] = set()
    if drop_ids:
        revealed_ids = set(
            db.scalars(
                select(DropViewEvent.drop_id).where(
                    DropViewEvent.user_id == user.id,
                    DropViewEvent.drop_id.in_(drop_ids),
                    DropViewEvent.stage == DropViewStage.discover,
                )
            ).all()
        )

    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        await redis.ping()
    except (RedisError, OSError):
        await redis.aclose()
        redis = None
    # Permanent per-pick bonus from the "bigger_radius" level-milestone perk
    # (app/services/gamification.py::choose_perk) plus, on top of that, the
    # temporary "bigger_reveal" powerup's boost while active. Both default to
    # no bonus (multiplier 1.0) for a user with neither.
    radius_bonus_perks = db.scalar(
        select(func.count())
        .select_from(UserPerk)
        .where(UserPerk.user_id == user.id, UserPerk.type == PerkType.bigger_radius)
    )
    radius_multiplier = 1.0 + RADIUS_PERK_BONUS_PCT * int(radius_bonus_perks or 0)
    if redis:
        boost_raw = await redis.get(f"reveal_boost:{user.id}")
        if boost_raw:
            radius_multiplier += float(boost_raw) - 1.0
    snapshots: list[DropSnapshot] = []
    events: list[DropStageUpdate] = []
    try:
        for drop, business, distance_value, latitude_value, longitude_value in rows:
            ttl = max(
                1, int((drop.ends_at - datetime.now(timezone.utc)).total_seconds())
            )
            reveal_key = f"reveal_unlocked:{user.id}:{drop.id}"
            legacy_key = f"discover_unlocked:{user.id}:{drop.id}"
            unlocked = drop.id in revealed_ids or bool(
                redis
                and (await redis.exists(reveal_key) or await redis.exists(legacy_key))
            )
            stage = stage_for_distance(float(distance_value), drop, unlocked, radius_multiplier)
            snapshot = snapshot_for(
                drop,
                business,
                float(distance_value),
                stage,
                latitude=float(latitude_value),
                longitude=float(longitude_value),
            )
            snapshots.append(snapshot)

            # The original PostgreSQL enum called the full-unlock event
            # ``discover``. Keep writing that internal value so existing
            # databases and historical reveal records remain unambiguous.
            stored_stage = (
                DropViewStage.discover
                if stage == DropViewStage.reveal
                else DropViewStage.detect
            )
            db.execute(
                insert(DropViewEvent)
                .values(user_id=user.id, drop_id=drop.id, stage=stored_stage)
                .on_conflict_do_nothing(constraint="uq_drop_view_user_drop_stage")
            )
            if stage == DropViewStage.reveal and redis:
                await redis.setex(reveal_key, ttl, "1")

            if redis:
                stage_key = f"last_stage:{user.id}:{drop.id}"
                previous_stage = await redis.get(stage_key)
                if previous_stage != stage.value:
                    await redis.setex(stage_key, ttl, stage.value)
                    events.append(
                        DropStageUpdate(
                            drop_id=str(drop.id),
                            stage=Stage(stage.value),
                            distance_m=snapshot.distance_m,
                            data=snapshot.model_dump(mode="json", exclude_none=True),
                        )
                    )

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        if redis:
            await redis.aclose()

    for event in events:
        await publish(f"ws:user:{user.id}", event.model_dump(mode="json"))
    if territory_bonus_xp:
        await publish(
            f"ws:user:{user.id}",
            TerritoryBonusAwarded(cell=cell, xp_awarded=territory_bonus_xp).model_dump(mode="json"),
        )
    return snapshots


def get_revealed_drop(
    db: Session, user_id: UUID, drop_id: UUID
) -> DropSnapshot | None:
    unlocked = db.scalar(
        select(DropViewEvent.id).where(
            DropViewEvent.user_id == user_id,
            DropViewEvent.drop_id == drop_id,
            DropViewEvent.stage == DropViewStage.discover,
        )
    )
    if unlocked is None:
        return None
    row = db.execute(
        select(
            Drop,
            Business,
            func.ST_Y(
                cast(Drop.location, Geometry(geometry_type="POINT", srid=4326))
            ),
            func.ST_X(
                cast(Drop.location, Geometry(geometry_type="POINT", srid=4326))
            ),
        )
        .join(Business, Business.id == Drop.business_id)
        .where(Drop.id == drop_id)
    ).one_or_none()
    if row is None:
        return None
    drop, business, latitude, longitude = row
    return snapshot_for(
        drop,
        business,
        0,
        DropViewStage.reveal,
        latitude=float(latitude),
        longitude=float(longitude),
    )
