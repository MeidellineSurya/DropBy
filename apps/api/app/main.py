import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from uuid import UUID

from jose import JWTError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.v1.router import api_router
from app.core.security import decode_access_token
from app.db.session import SessionLocal
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


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str) -> None:
    try:
        user_id = UUID(decode_access_token(token)["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        await websocket.close(code=1008, reason="Invalid or expired token")
        return
    with SessionLocal() as db:
        if db.get(User, user_id) is None:
            await websocket.close(code=1008, reason="Unknown user")
            return
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
    topics = [f"ws:user:{user_id}", *(f"ws:group:{group_id}" for group_id in group_ids)]
    await manager.connect(websocket, topics)
    try:
        while True:
            await (
                websocket.receive_text()
            )  # server does not act on client messages; REST is authoritative
    except WebSocketDisconnect:
        manager.disconnect(websocket, topics)
