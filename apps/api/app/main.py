import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from uuid import UUID

from jose import JWTError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.businesses import Business
from app.models.drops import Drop, DropStatus
from app.models.groups import Group, GroupMember, GroupMemberStatus, GroupStatus
from app.models.users import User
from app.schemas.common import HealthResponse
from app.ws.manager import manager, redis_bridge_task


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    bridge_task = asyncio.create_task(redis_bridge_task())
    try:
        yield
    finally:
        bridge_task.cancel()
        with suppress(asyncio.CancelledError):
            await bridge_task


app = FastAPI(title="DropBy API", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


def _user_topics(db: Session, user_id: UUID) -> list[str] | None:
    if db.get(User, user_id) is None:
        return None
    group_ids = db.scalars(
        select(GroupMember.group_id)
        .join(Group, Group.id == GroupMember.group_id)
        .where(
            GroupMember.user_id == user_id,
            GroupMember.status == GroupMemberStatus.joined,
            Group.status.in_(
                [GroupStatus.forming, GroupStatus.ready, GroupStatus.checked_in]
            ),
        )
    ).all()
    return [f"ws:user:{user_id}", *(f"ws:group:{group_id}" for group_id in group_ids)]


def _business_topics(db: Session, business_id: UUID) -> list[str] | None:
    """Business dashboards get their own account channel plus a topic per
    currently live Drop, so drop.capacity_reached/expired/countdown_warning
    (already broadcast by the discovery engine and the cancel endpoint) reach
    the dashboard's live view the same way they reach consumer clients."""
    if db.get(Business, business_id) is None:
        return None
    drop_ids = db.scalars(
        select(Drop.id).where(
            Drop.business_id == business_id,
            Drop.status.in_(
                [DropStatus.scheduled, DropStatus.active, DropStatus.capacity_reached]
            ),
        )
    ).all()
    return [
        f"ws:business:{business_id}",
        *(f"ws:drop:{drop_id}" for drop_id in drop_ids),
    ]


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str) -> None:
    try:
        payload = decode_access_token(token)
        subject_id = UUID(payload["sub"])
        audience = payload.get("aud", "user")
    except (JWTError, KeyError, TypeError, ValueError):
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    with SessionLocal() as db:
        topics = (
            _business_topics(db, subject_id)
            if audience == "business"
            else _user_topics(db, subject_id)
        )
    if topics is None:
        await websocket.close(code=1008, reason="Unknown account")
        return
    await manager.connect(websocket, topics)
    try:
        while True:
            await (
                websocket.receive_text()
            )  # server does not act on client messages; REST is authoritative
    except WebSocketDisconnect:
        manager.disconnect(websocket, topics)
