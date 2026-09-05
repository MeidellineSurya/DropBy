"""WS is a read-only push channel — every mutation goes through REST.

ConnectionManager holds local (per-process) sockets keyed by topic. A single
background task PSUBSCRIBEs the Redis pattern "ws:*" and fans out any message
to whichever locally-held sockets are subscribed to that topic. Every API
process does this independently, so a message published from any process
reaches sockets connected to any other process.
"""

import asyncio
import json
from collections import defaultdict

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.core.config import settings


class ConnectionManager:
    def __init__(self) -> None:
        self._topic_sockets: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, topics: list[str]) -> None:
        await websocket.accept()
        for topic in topics:
            self._topic_sockets[topic].add(websocket)

    def disconnect(self, websocket: WebSocket, topics: list[str]) -> None:
        for topic in topics:
            self._topic_sockets[topic].discard(websocket)

    async def dispatch(self, topic: str, message: dict) -> None:
        for websocket in list(self._topic_sockets.get(topic, ())):
            await websocket.send_text(json.dumps(message))


manager = ConnectionManager()


async def redis_bridge_task() -> None:
    """Subscribes to ws:* on Redis and fans out to local sockets. Run once at app startup."""
    redis_client = aioredis.from_url(settings.redis_url)
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("ws:*")
    async for message in pubsub.listen():
        if message["type"] != "pmessage":
            continue
        topic = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
        data = message["data"].decode() if isinstance(message["data"], bytes) else message["data"]
        await manager.dispatch(topic, json.loads(data))


async def publish(topic: str, message: dict) -> None:
    """Called from REST handlers/services after a state-changing write to fan the
    event out to every API process's connected sockets for that topic."""
    redis_client = aioredis.from_url(settings.redis_url)
    await redis_client.publish(topic, json.dumps(message))
