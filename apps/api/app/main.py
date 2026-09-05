import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.api.v1.router import api_router
from app.core.deps import get_current_user_id
from app.schemas.common import HealthResponse
from app.ws.manager import manager, redis_bridge_task


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    bridge_task = asyncio.create_task(redis_bridge_task())
    try:
        yield
    finally:
        bridge_task.cancel()


app = FastAPI(title="DropBy API", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str) -> None:
    # TODO: validate `token` (JWT) before accepting; derive user_id and any
    # group/drop topics the user should currently be subscribed to.
    user_id = "TODO"
    topics = [f"ws:user:{user_id}"]
    await manager.connect(websocket, topics)
    try:
        while True:
            await websocket.receive_text()  # server does not act on client messages; REST is authoritative
    except WebSocketDisconnect:
        manager.disconnect(websocket, topics)
