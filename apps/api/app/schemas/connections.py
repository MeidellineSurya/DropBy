from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

ConnectionStatusView = Literal["none", "pending_outgoing", "pending_incoming", "connected", "blocked"]
RawConnectionStatus = Literal["pending", "accepted", "declined", "blocked"]


class UserSummary(BaseModel):
    user_id: str
    display_name: str
    avatar_url: str | None = None


class UserSearchResult(UserSummary):
    connection_status: ConnectionStatusView


class RecentSquadmate(UserSummary):
    connection_status: ConnectionStatusView
    met_via_drop_title: str | None = None
    met_at: datetime | None = None


class ConnectionRequestCreate(BaseModel):
    addressee_id: UUID


class ConnectionRespondRequest(BaseModel):
    accept: bool


class ConnectionResponse(BaseModel):
    id: str
    status: RawConnectionStatus
    other_user: UserSummary
    created_at: datetime
