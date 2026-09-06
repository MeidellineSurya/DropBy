"""Friend requests and the "recent squadmates" suggestion feed.

An accepted Connection row also identifies a conversation for
app/services/chat.py — there is no separate Conversation table.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.connections import Connection, ConnectionStatus
from app.models.drops import Drop
from app.models.groups import Group, GroupMember, GroupMemberStatus
from app.models.users import User
from app.schemas.connections import (
    ConnectionResponse,
    ConnectionStatusView,
    RecentSquadmate,
    UserSearchResult,
    UserSummary,
)


def _find_connection(db: Session, user_a_id: UUID, user_b_id: UUID) -> Connection | None:
    return db.scalar(
        select(Connection).where(
            or_(
                and_(Connection.requester_id == user_a_id, Connection.addressee_id == user_b_id),
                and_(Connection.requester_id == user_b_id, Connection.addressee_id == user_a_id),
            )
        )
    )


def _status_view(connection: Connection | None, viewer_id: UUID) -> ConnectionStatusView:
    if connection is None or connection.status == ConnectionStatus.declined:
        return "none"
    if connection.status == ConnectionStatus.blocked:
        return "blocked"
    if connection.status == ConnectionStatus.accepted:
        return "connected"
    return "pending_outgoing" if connection.requester_id == viewer_id else "pending_incoming"


def _connection_response(db: Session, connection: Connection, viewer_id: UUID) -> ConnectionResponse:
    other_id = connection.addressee_id if connection.requester_id == viewer_id else connection.requester_id
    other = db.get(User, other_id)
    return ConnectionResponse(
        id=str(connection.id),
        status=connection.status.value,
        other_user=UserSummary(user_id=str(other.id), display_name=other.display_name, avatar_url=other.avatar_url),
        created_at=connection.created_at,
    )


def search_users(db: Session, current_user: User, query: str) -> list[UserSearchResult]:
    term = query.strip()
    if not term:
        return []
    rows = db.scalars(
        select(User)
        .where(User.display_name.ilike(f"%{term}%"), User.id != current_user.id)
        .order_by(User.display_name)
        .limit(20)
    ).all()
    return [
        UserSearchResult(
            user_id=str(user.id),
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            connection_status=_status_view(_find_connection(db, current_user.id, user.id), current_user.id),
        )
        for user in rows
    ]


def recent_squadmates(db: Session, current_user: User) -> list[RecentSquadmate]:
    my_group_ids = db.scalars(
        select(GroupMember.group_id).where(
            GroupMember.user_id == current_user.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    ).all()
    if not my_group_ids:
        return []

    rows = db.execute(
        select(GroupMember, User, Group)
        .join(User, User.id == GroupMember.user_id)
        .join(Group, Group.id == GroupMember.group_id)
        .where(
            GroupMember.group_id.in_(my_group_ids),
            GroupMember.user_id != current_user.id,
            GroupMember.status == GroupMemberStatus.joined,
        )
    ).all()

    latest: dict[UUID, tuple[User, datetime, Group]] = {}
    for _member, user, group in rows:
        met_at = group.completed_at or group.checked_in_at or group.created_at
        current = latest.get(user.id)
        if current is None or met_at > current[1]:
            latest[user.id] = (user, met_at, group)

    drop_ids = {group.drop_id for _, _, group in latest.values()}
    titles: dict[UUID, str] = {}
    if drop_ids:
        titles = dict(db.execute(select(Drop.id, Drop.title).where(Drop.id.in_(drop_ids))).all())

    results = [
        RecentSquadmate(
            user_id=str(user.id),
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            connection_status=_status_view(_find_connection(db, current_user.id, user.id), current_user.id),
            met_via_drop_title=titles.get(group.drop_id),
            met_at=met_at,
        )
        for user, met_at, group in latest.values()
    ]
    results.sort(key=lambda item: item.met_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return results


def send_request(db: Session, requester: User, addressee_id: UUID) -> ConnectionResponse:
    if addressee_id == requester.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot send a connection request to yourself")
    if db.get(User, addressee_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    existing = _find_connection(db, requester.id, addressee_id)
    if existing is not None and existing.status in (
        ConnectionStatus.pending,
        ConnectionStatus.accepted,
        ConnectionStatus.blocked,
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "A connection already exists with this user")

    if existing is not None:
        # Re-sending after a decline reuses the row rather than inserting a
        # second one, since (requester_id, addressee_id) must stay unique.
        existing.requester_id = requester.id
        existing.addressee_id = addressee_id
        existing.status = ConnectionStatus.pending
        existing.responded_at = None
        connection = existing
    else:
        connection = Connection(requester_id=requester.id, addressee_id=addressee_id, status=ConnectionStatus.pending)
        db.add(connection)
    db.commit()
    db.refresh(connection)
    return _connection_response(db, connection, requester.id)


def respond_request(db: Session, user: User, connection_id: UUID, accept: bool) -> ConnectionResponse:
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Request not found")
    if connection.addressee_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your request to respond to")
    if connection.status != ConnectionStatus.pending:
        raise HTTPException(status.HTTP_409_CONFLICT, "Request already resolved")

    connection.status = ConnectionStatus.accepted if accept else ConnectionStatus.declined
    connection.responded_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(connection)
    return _connection_response(db, connection, user.id)


def list_incoming_requests(db: Session, user: User) -> list[ConnectionResponse]:
    rows = db.execute(
        select(Connection, User)
        .join(User, User.id == Connection.requester_id)
        .where(Connection.addressee_id == user.id, Connection.status == ConnectionStatus.pending)
        .order_by(Connection.created_at.desc())
    ).all()
    return [
        ConnectionResponse(
            id=str(connection.id),
            status=connection.status.value,
            other_user=UserSummary(user_id=str(requester.id), display_name=requester.display_name, avatar_url=requester.avatar_url),
            created_at=connection.created_at,
        )
        for connection, requester in rows
    ]


def list_connections(db: Session, user: User) -> list[ConnectionResponse]:
    rows = db.scalars(
        select(Connection).where(
            Connection.status == ConnectionStatus.accepted,
            or_(Connection.requester_id == user.id, Connection.addressee_id == user.id),
        )
    ).all()
    return [_connection_response(db, connection, user.id) for connection in rows]
