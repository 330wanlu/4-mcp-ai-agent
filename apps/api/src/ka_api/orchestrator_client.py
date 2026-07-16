"""调用 Orchestrator：http（:8001）或 local（进程内 pipeline）。"""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

import httpx

from ka_common.config import Settings, get_settings
from ka_api.errors import ApiError

Mode = Literal["http", "local"]


class OrchestratorClient:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        mode: Mode | None = None,
        timeout: float = 180.0,
    ) -> None:
        self.settings = settings or get_settings()
        raw = (mode or self.settings.orchestrator_mode or "local").lower()
        if raw not in ("http", "local"):
            raise ValueError(f"未知 ORCHESTRATOR_MODE={raw}")
        self.mode: Mode = raw  # type: ignore[assignment]
        self.timeout = timeout
        self.base_url = self.settings.orchestrator_url.rstrip("/")
        self._http: httpx.AsyncClient | None = None
        self._store = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=self.timeout)
        return self._http

    async def _get_store(self):
        if self._store is None:
            from ka_orchestrator.redis_state import SessionStore

            self._store = SessionStore(self.settings)
        return self._store

    async def close(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None
        if self._store is not None:
            await self._store.close()
            self._store = None

    async def create_session(
        self,
        *,
        user_id: str,
        title: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        session_id = session_id or str(uuid4())
        state = {
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "status": "created",
            "current_node": "idle",
            "messages": [],
            "citations": [],
            "agent_trace": [],
        }
        if self.mode == "local":
            store = await self._get_store()
            await store.save(session_id, state)
            return state

        # HTTP 模式：直接写 Redis（会话创建不必经过 orchestrator 进程）
        from ka_orchestrator.redis_state import SessionStore

        store = SessionStore(self.settings)
        try:
            await store.save(session_id, state)
        finally:
            await store.close()
        return state

    async def get_session(self, session_id: str) -> dict[str, Any]:
        if self.mode == "local":
            store = await self._get_store()
            state = await store.load(session_id)
            if state is None:
                return {"found": False, "session_id": session_id}
            return {"found": True, **state}

        http = await self._get_http()
        try:
            resp = await http.get(f"{self.base_url}/sessions/{session_id}")
        except httpx.HTTPError as exc:
            raise ApiError(
                "ORCHESTRATOR_UNAVAILABLE",
                f"无法连接 Orchestrator: {exc}",
                status_code=503,
            ) from exc
        if resp.status_code >= 400:
            raise ApiError(
                "ORCHESTRATOR_ERROR",
                f"Orchestrator HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=502,
            )
        return resp.json()

    async def ask(
        self,
        *,
        question: str,
        session_id: str,
        user_id: str,
        top_k: int = 5,
    ) -> dict[str, Any]:
        if self.mode == "local":
            from ka_orchestrator.pipeline import run_qa_pipeline

            store = await self._get_store()
            # 保留已有 messages / title
            prev = await store.load(session_id) or {}
            result = await run_qa_pipeline(
                question,
                session_id=session_id,
                user_id=user_id,
                top_k=top_k,
                store=store,
                persist=True,
            )
            messages = list(prev.get("messages") or [])
            message_id = str(uuid4())
            messages.append(
                {
                    "id": message_id,
                    "role": "user",
                    "content": question,
                }
            )
            messages.append(
                {
                    "id": str(uuid4()),
                    "role": "assistant",
                    "content": result.get("answer"),
                    "citations": result.get("citations") or [],
                    "agent_trace": result.get("agent_trace") or [],
                }
            )
            await store.update(
                session_id,
                messages=messages,
                title=prev.get("title"),
            )
            result["message_id"] = message_id
            result["messages"] = messages
            return result

        http = await self._get_http()
        try:
            resp = await http.post(
                f"{self.base_url}/qa",
                json={
                    "question": question,
                    "session_id": session_id,
                    "user_id": user_id,
                    "top_k": top_k,
                },
            )
        except httpx.HTTPError as exc:
            raise ApiError(
                "ORCHESTRATOR_UNAVAILABLE",
                f"无法连接 Orchestrator: {exc}",
                status_code=503,
            ) from exc
        if resp.status_code >= 400:
            raise ApiError(
                "ORCHESTRATOR_ERROR",
                f"Orchestrator HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=502,
            )
        data = resp.json()

        # 追加 messages 到 Redis（与 local 行为对齐）
        from ka_orchestrator.redis_state import SessionStore

        store = SessionStore(self.settings)
        try:
            prev = await store.load(session_id) or {}
            messages = list(prev.get("messages") or [])
            message_id = str(uuid4())
            messages.append({"id": message_id, "role": "user", "content": question})
            messages.append(
                {
                    "id": str(uuid4()),
                    "role": "assistant",
                    "content": data.get("answer"),
                    "citations": data.get("citations") or [],
                    "agent_trace": data.get("agent_trace") or [],
                }
            )
            await store.update(
                session_id,
                messages=messages,
                title=prev.get("title"),
                user_id=user_id,
            )
            data["message_id"] = message_id
            data["messages"] = messages
        finally:
            await store.close()
        return data
