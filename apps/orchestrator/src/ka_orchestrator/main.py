"""Orchestrator 入口：阶段 0 健康检查 + Graph 元数据。"""

from __future__ import annotations

from fastapi import FastAPI

from ka_orchestrator.graph import AGENT_GRAPH_SUMMARY


def create_app() -> FastAPI:
    application = FastAPI(
        title="Knowledge Action Cluster Orchestrator",
        version="0.1.0",
        description="阶段 0 骨架：Agent Graph 草图已冻结，执行逻辑在阶段 2。",
    )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "orchestrator"}

    @application.get("/graph")
    async def graph() -> dict[str, object]:
        return AGENT_GRAPH_SUMMARY

    return application


app = create_app()
