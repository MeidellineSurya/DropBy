from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.connections import Connection, ConnectionStatus
from app.models.messages import Message
from app.models.users import User
from app.schemas.chat import ConversationResponse, MessageResponse
from app.schemas.connections import UserSummary


def _accepted_connection_for_participant(db: Session, user: User, connection_id: UUID) -> Connection:
    connection = db.get(Connection, connection_id)
    if connection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    if user.id not in (connection.requester_id, connection.addressee_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not a participant in this conversation")
    if connection.status != ConnectionStatus.accepted:
        raise HTTPException(status.HTTP_409_CONFLICT, "You are not connected with this user")
    return connection


def _message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        connection_id=str(message.connection_id),
        sender_id=str(message.sender_id),
        body=message.body,
        created_at=message.created_at,
    )


def list_conversations(db: Session, user: User) -> list[ConversationResponse]:
    connections = db.scalars(
        select(Connection).where(
            Connection.status == ConnectionStatus.accepted,
            or_(Connection.requester_id == user.id, Connection.addressee_id == user.id),
        )
    ).all()
    if not connections:
        return []

    other_ids = [c.addressee_id if c.requester_id == user.id else c.requester_id for c in connections]
    users_by_id = {u.id: u for u in db.scalars(select(User).where(User.id.in_(other_ids))).all()}

    results: list[ConversationResponse] = []
    for connection in connections:
        other_id = connection.addressee_id if connection.requester_id == user.id else connection.requester_id
        other = users_by_id.get(other_id)
        if other is None:
            continue
        last = db.scalar(
            select(Message)
            .where(Message.connection_id == connection.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        results.append(
            ConversationResponse(
                connection_id=str(connection.id),
                other_user=UserSummary(user_id=str(other.id), display_name=other.display_name, avatar_url=other.avatar_url),
                last_message=_message_response(last) if last else None,
            )
        )

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    results.sort(key=lambda item: item.last_message.created_at if item.last_message else epoch, reverse=True)
    return results


def list_messages(
    db: Session, user: User, connection_id: UUID, *, before: datetime | None = None, limit: int = 50
) -> list[MessageResponse]:
    _accepted_connection_for_participant(db, user, connection_id)
    stmt = select(Message).where(Message.connection_id == connection_id)
    if before is not None:
        stmt = stmt.where(Message.created_at < before)
    rows = db.scalars(stmt.order_by(Message.created_at.desc()).limit(limit)).all()
    rows.reverse()
    return [_message_response(message) for message in rows]


def send_message(db: Session, user: User, connection_id: UUID, body: str) -> MessageResponse:
    _accepted_connection_for_participant(db, user, connection_id)
    text = body.strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Message cannot be empty")

    message = Message(connection_id=connection_id, sender_id=user.id, body=text)
    db.add(message)
    db.commit()
    db.refresh(message)
    return _message_response(message)
