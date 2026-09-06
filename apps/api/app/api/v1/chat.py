from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.connections import Connection
from app.models.users import User
from app.schemas.chat import ConversationResponse, MessageCreateRequest, MessageResponse
from app.services.chat import list_conversations, list_messages, send_message
from app.ws.manager import publish
from ws_contracts.events import MessageSent

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationResponse])
def conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationResponse]:
    return list_conversations(db, user)


@router.get("/conversations/{connection_id}/messages", response_model=list[MessageResponse])
def messages(
    connection_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    return list_messages(db, user, connection_id)


@router.post("/conversations/{connection_id}/messages", response_model=MessageResponse, status_code=201)
async def post_message(
    connection_id: UUID,
    body: MessageCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    message = send_message(db, user, connection_id, body.body)
    connection = db.get(Connection, connection_id)
    recipient_id = connection.addressee_id if connection.requester_id == user.id else connection.requester_id
    event = MessageSent(
        connection_id=message.connection_id,
        message_id=message.id,
        sender_id=message.sender_id,
        body=message.body,
        created_at=message.created_at,
    )
    await publish(f"ws:user:{recipient_id}", event.model_dump(mode="json"))
    return message
