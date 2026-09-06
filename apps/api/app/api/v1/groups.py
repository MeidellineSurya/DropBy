from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.drops import Drop, DropStatus, DropViewEvent
from app.models.groups import GroupStatus
from app.models.users import User
from app.schemas.groups import GroupCreateRequest, GroupResponse
from app.schemas.redemption import SquadQrResponse
from app.services.redemption import get_squad_qr
from app.services.squad_state import (
    create_group as create_group_state,
)
from app.services.squad_state import (
    get_group_for_member,
    join_group as join_group_state,
    leave_group as leave_group_state,
)
from app.workers.tasks.notifications import send_push_task
from app.ws.manager import publish
from ws_contracts.events import (
    DropCapacityReached,
    GroupMemberJoined,
    GroupReady,
    GroupStateUpdate,
)

router = APIRouter()


def _state_event(group: GroupResponse) -> GroupStateUpdate:
    return GroupStateUpdate(
        group_id=group.id,
        drop_id=group.drop_id,
        status=group.status.value,
        current_count=group.current_count,
        min_required=group.min_required,
        max_allowed=group.max_allowed,
        members=[member.model_dump(mode="json") for member in group.members],
        expires_at=group.expires_at,
        reason=group.cancelled_reason,
    )


async def _broadcast_group(
    group: GroupResponse,
    event: GroupStateUpdate | GroupMemberJoined | GroupReady,
) -> None:
    message = event.model_dump(mode="json")
    topics = {
        f"ws:group:{group.id}",
        *(f"ws:user:{member.user_id}" for member in group.members),
    }
    for topic in topics:
        await publish(topic, message)


def _notify_squad_ready(group: GroupResponse) -> None:
    for member in group.members:
        send_push_task.delay(
            member.user_id,
            "squad_ready",
            {
                "title": "Squad ready!",
                "body": "Everyone's in — head to the venue to check in.",
                "group_id": group.id,
            },
        )


async def _broadcast_capacity_reached(db: Session, group: GroupResponse) -> None:
    if (
        db.scalar(select(Drop.status).where(Drop.id == UUID(group.drop_id)))
        != DropStatus.capacity_reached
    ):
        return
    user_ids = set(
        db.scalars(
            select(DropViewEvent.user_id).where(
                DropViewEvent.drop_id == UUID(group.drop_id)
            )
        ).all()
    )
    event = DropCapacityReached(drop_id=group.drop_id).model_dump(mode="json")
    for topic in {
        f"ws:drop:{group.drop_id}",
        *(f"ws:user:{user_id}" for user_id in user_ids),
    }:
        await publish(topic, event)


@router.post("", response_model=GroupResponse, status_code=201)
async def create_group(
    body: GroupCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupResponse:
    group = create_group_state(db, body.drop_id, user, body.open_to_nearby)
    await _broadcast_group(group, _state_event(group))
    if group.status == GroupStatus.ready:
        await _broadcast_group(
            group,
            GroupReady(
                group_id=group.id,
                drop_id=group.drop_id,
                venue_directions_url="",
            ),
        )
        _notify_squad_ready(group)
    await _broadcast_capacity_reached(db, group)
    return group


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupResponse:
    return get_group_for_member(db, group_id, user.id)


@router.post("/{group_id}/join", response_model=GroupResponse)
async def join_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupResponse:
    group, member_added, became_ready = join_group_state(db, group_id, user)
    if not member_added:
        return group
    if group.status == GroupStatus.cancelled:
        await _broadcast_group(group, _state_event(group))
    else:
        await _broadcast_group(
            group,
            GroupMemberJoined(
                group_id=group.id,
                user_id=str(user.id),
                display_name=user.display_name,
                current_count=group.current_count,
            ),
        )
        await _broadcast_group(group, _state_event(group))
    if became_ready:
        await _broadcast_group(
            group,
            GroupReady(
                group_id=group.id,
                drop_id=group.drop_id,
                venue_directions_url="",
            ),
        )
        _notify_squad_ready(group)
    await _broadcast_capacity_reached(db, group)
    return group


@router.post("/{group_id}/leave", response_model=GroupResponse | None)
async def leave_group(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupResponse | None:
    previous = get_group_for_member(db, group_id, user.id)
    group = leave_group_state(db, group_id, user)
    if group is None:
        event = GroupStateUpdate(
            group_id=str(group_id),
            drop_id=previous.drop_id,
            status="cancelled",
            current_count=0,
            min_required=previous.min_required,
            max_allowed=previous.max_allowed,
            members=[],
            expires_at=previous.expires_at,
        )
        await publish(f"ws:user:{user.id}", event.model_dump(mode="json"))
        return None
    await _broadcast_group(group, _state_event(group))
    return group


@router.get("/{group_id}/qr", response_model=SquadQrResponse)
def get_group_qr(
    group_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SquadQrResponse:
    """Any squad member can pull up the squad's check-in code once ready —
    show it to staff at the venue. Business confirms by scanning it (see
    POST /redemptions/scan); there's nothing for the consumer to do beyond
    displaying this."""
    return SquadQrResponse(qr_token=get_squad_qr(db, group_id, user))
