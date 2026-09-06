from datetime import datetime

from pydantic import BaseModel

from app.schemas.connections import UserSummary


class MessageCreateRequest(BaseModel):
    body: str


class MessageResponse(BaseModel):
    id: str
    connection_id: str
    sender_id: str
    body: str
    created_at: datetime


class ConversationResponse(BaseModel):
    connection_id: str
    other_user: UserSummary
    last_message: MessageResponse | None = None
