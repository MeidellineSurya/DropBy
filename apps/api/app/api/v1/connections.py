from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.models.users import User
from app.schemas.connections import (
    ConnectionRequestCreate,
    ConnectionRespondRequest,
    ConnectionResponse,
    RecentSquadmate,
    UserSearchResult,
)
from app.services.connections import (
    list_connections,
    list_incoming_requests,
    recent_squadmates,
    respond_request,
    search_users,
    send_request,
)
from app.ws.manager import publish
from ws_contracts.events import ConnectionRequestAccepted, ConnectionRequestReceived

router = APIRouter()


@router.get("/search", response_model=list[UserSearchResult])
def search(
    q: str = Query(default="", min_length=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserSearchResult]:
    return search_users(db, user, q)


@router.get("/recent-squadmates", response_model=list[RecentSquadmate])
def recent_squadmates_route(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecentSquadmate]:
    return recent_squadmates(db, user)


@router.get("/requests", response_model=list[ConnectionResponse])
def incoming_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConnectionResponse]:
    return list_incoming_requests(db, user)


@router.post("/requests", response_model=ConnectionResponse, status_code=201)
async def create_request(
    body: ConnectionRequestCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectionResponse:
    connection = send_request(db, user, body.addressee_id)
    event = ConnectionRequestReceived(
        connection_id=connection.id,
        requester_id=str(user.id),
        requester_display_name=user.display_name,
    )
    await publish(f"ws:user:{connection.other_user.user_id}", event.model_dump(mode="json"))
    return connection


@router.post("/requests/{connection_id}/respond", response_model=ConnectionResponse)
async def respond(
    connection_id: UUID,
    body: ConnectionRespondRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectionResponse:
    connection = respond_request(db, user, connection_id, body.accept)
    if connection.status == "accepted":
        event = ConnectionRequestAccepted(
            connection_id=connection.id,
            addressee_id=str(user.id),
            addressee_display_name=user.display_name,
        )
        await publish(f"ws:user:{connection.other_user.user_id}", event.model_dump(mode="json"))
    return connection


@router.get("", response_model=list[ConnectionResponse])
def list_accepted_connections(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConnectionResponse]:
    return list_connections(db, user)
