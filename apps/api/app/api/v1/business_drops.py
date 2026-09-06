from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_business, get_db
from app.models.businesses import Business, BusinessStatus
from app.models.drops import Drop, DropStatus, DropViewEvent
from app.models.groups import Group
from app.schemas.business_drops import BusinessDropCreateRequest, BusinessDropResponse
from app.services.drop_lifecycle import (
    cancel_drop as cancel_drop_lifecycle,
    create_drop as create_drop_lifecycle,
    delete_drop as delete_drop_lifecycle,
    pause_drop as pause_drop_lifecycle,
    publish_drop as publish_drop_lifecycle,
    resume_drop as resume_drop_lifecycle,
)
from app.services.squad_state import group_snapshot
from app.workers.tasks.notifications import notify_users_of_new_drop
from app.ws.manager import publish
from ws_contracts.events import DropExpired, GroupStateUpdate

router = APIRouter()


def _drop_response(drop: Drop) -> BusinessDropResponse:
    return BusinessDropResponse(
        id=str(drop.id),
        title=drop.title,
        description=drop.description,
        category=drop.category,
        interest_tag=drop.interest_tag,
        rarity=drop.rarity,
        discount_percent=drop.discount_percent,
        drop_type=drop.drop_type,
        min_group_size=drop.min_group_size,
        max_group_size=drop.max_group_size,
        discovery_radius_m=drop.discovery_radius_m,
        discover_radius_m=drop.discover_radius_m,
        max_capacity_participants=drop.max_capacity_participants,
        reserved_count=drop.reserved_count,
        starts_at=drop.starts_at,
        ends_at=drop.ends_at,
        status=drop.status,
        xp_reward_base=drop.xp_reward_base,
    )


def _legacy_reveal_radius_m(discovery_radius_m: int, discover_radius_m: int) -> int:
    """The DB still enforces discovery_radius_m >= reveal_radius_m >=
    discover_radius_m from the retired three-stage model (see
    app/schemas/business_drops.py); pick the midpoint so callers never need
    to think about it."""
    return max(discover_radius_m, (discovery_radius_m + discover_radius_m) // 2)


def _owned_drop_or_404(db: Session, drop_id: UUID, business: Business) -> Drop:
    drop = db.scalar(
        select(Drop).where(Drop.id == drop_id, Drop.business_id == business.id)
    )
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drop not found")
    return drop


def _require_active_business(business: Business) -> None:
    """Registration alone used to be enough to publish a live, discoverable
    Drop — nothing checked BusinessStatus at all. A business can still
    prepare drafts before approval; going live requires status == active."""
    if business.status != BusinessStatus.active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Your business must be approved before publishing a Drop. "
            f"Current status: {business.status.value}.",
        )


@router.post("", response_model=BusinessDropResponse, status_code=status.HTTP_201_CREATED)
def create_drop(
    body: BusinessDropCreateRequest,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessDropResponse:
    if body.publish:
        _require_active_business(business)
    try:
        drop = create_drop_lifecycle(
            db,
            business_id=business.id,
            title=body.title,
            category=body.category,
            drop_type=body.drop_type,
            latitude=body.latitude,
            longitude=body.longitude,
            max_capacity_participants=body.max_capacity_participants,
            starts_at=body.starts_at,
            ends_at=body.ends_at,
            description=body.description,
            interest_tag=body.interest_tag,
            discount_percent=body.discount_percent,
            venue_capacity=business.venue_capacity,
            min_group_size=body.min_group_size,
            max_group_size=body.max_group_size,
            discovery_radius_m=body.discovery_radius_m,
            reveal_radius_m=body.reveal_radius_m
            or _legacy_reveal_radius_m(body.discovery_radius_m, body.discover_radius_m),
            discover_radius_m=body.discover_radius_m,
            publish=body.publish,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    db.commit()
    db.refresh(drop)
    if drop.status == DropStatus.active:
        # starts_at was already in the past, so this Drop skipped scheduled
        # entirely and went straight to active — the scheduled->active sweep
        # that normally fires this will never see it.
        notify_users_of_new_drop.delay(str(drop.id))
    return _drop_response(drop)


@router.get("", response_model=list[BusinessDropResponse])
def list_business_drops(
    drop_status: DropStatus | None = None,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> list[BusinessDropResponse]:
    query = select(Drop).where(Drop.business_id == business.id)
    if drop_status is not None:
        query = query.where(Drop.status == drop_status)
    drops = db.scalars(query.order_by(Drop.created_at.desc())).all()
    return [_drop_response(drop) for drop in drops]


@router.get("/{drop_id}", response_model=BusinessDropResponse)
def get_business_drop(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessDropResponse:
    return _drop_response(_owned_drop_or_404(db, drop_id, business))


@router.post("/{drop_id}/publish", response_model=BusinessDropResponse)
def publish_drop(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessDropResponse:
    _require_active_business(business)
    try:
        drop = publish_drop_lifecycle(db, drop_id, business.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Draft Drop not found")
    if drop.status == DropStatus.active:
        notify_users_of_new_drop.delay(str(drop.id))
    return _drop_response(drop)


@router.post("/{drop_id}/pause", response_model=BusinessDropResponse)
def pause_drop(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessDropResponse:
    drop = pause_drop_lifecycle(db, drop_id, business.id)
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Active Drop not found")
    return _drop_response(drop)


@router.post("/{drop_id}/resume", response_model=BusinessDropResponse)
def resume_drop(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessDropResponse:
    _require_active_business(business)
    drop = resume_drop_lifecycle(db, drop_id, business.id)
    if drop is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Paused Drop not found")
    return _drop_response(drop)


@router.post("/{drop_id}/cancel", response_model=BusinessDropResponse)
async def cancel_drop(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> BusinessDropResponse:
    cancelled_group_ids = cancel_drop_lifecycle(db, drop_id, business.id)
    if cancelled_group_ids is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cancellable Drop not found")

    # Mirror workers/tasks/drops.py's expiry-sweep broadcast so cancellation
    # notifies affected users/squads the same way a natural expiry does.
    viewer_ids = set(
        db.scalars(
            select(DropViewEvent.user_id).where(DropViewEvent.drop_id == drop_id)
        ).all()
    )
    drop_expired_event = DropExpired(
        drop_id=str(drop_id), reason="cancelled"
    ).model_dump(mode="json")
    for topic in {f"ws:drop:{drop_id}", *(f"ws:user:{uid}" for uid in viewer_ids)}:
        await publish(topic, drop_expired_event)

    for group_id in cancelled_group_ids:
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
            reason="This Drop was cancelled by the business.",
        ).model_dump(mode="json")
        for topic in {
            f"ws:group:{group_id}",
            *(f"ws:user:{member.user_id}" for member in snapshot.members),
        }:
            await publish(topic, event)

    return _drop_response(_owned_drop_or_404(db, drop_id, business))


@router.delete("/{drop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drop(
    drop_id: UUID,
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
) -> None:
    """Permanent — a real delete, not a status change (see cancel_drop
    above for that). Only allowed when no squad has ever formed against
    this Drop; see services/drop_lifecycle.delete_drop for why."""
    try:
        deleted = delete_drop_lifecycle(db, drop_id, business.id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Drop not found")
