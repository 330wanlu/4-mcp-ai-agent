"""Redis 会话 / Agent 图任务状态。"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as redis

from ka_common.config import Settings, get_settings

SESSION_TTL_SECONDS = 60 * 60 * 24  # 24h
SESSION_KEY_PREFIX = "session:"


class SessionStore:
    """活状态：session:{id} → JSON（current_node / status / trace …）。"""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: redis.Redis | None = None

    async def connect(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(
                self.settings.redis_url,
                decode_responses=True,
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _key(self, session_id: str) -> str:
        return f"{SESSION_KEY_PREFIX}{session_id}"

    async def save(self, session_id: str, state: dict[str, Any]) -> None:
        client = await self.connect()
        await client.set(
            self._key(session_id),
            json.dumps(state, ensure_ascii=False),
            ex=SESSION_TTL_SECONDS,
        )

    async def load(self, session_id: str) -> dict[str, Any] | None:
        client = await self.connect()
        raw = await client.get(self._key(session_id))
        if not raw:
            return None
        return json.loads(raw)

    async def update(self, session_id: str, **fields: Any) -> dict[str, Any]:
        state = await self.load(session_id) or {}
        state["session_id"] = session_id
        state.update(fields)
        await self.save(session_id, state)
        return state

    async def exists(self, session_id: str) -> bool:
        client = await self.connect()
        return bool(await client.exists(self._key(session_id)))
