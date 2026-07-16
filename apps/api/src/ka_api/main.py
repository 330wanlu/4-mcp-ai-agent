"""API 入口：阶段 0 仅健康检查 + 扩展点挂载说明。"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Request

from ka_auth import AuthProvider, UserContext, get_auth_provider
from ka_common.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Knowledge Action Cluster API",
        version="0.1.0",
        description="阶段 0 骨架：健康检查 + Auth 扩展点。业务路由在阶段 3 实现。",
    )
    auth = get_auth_provider(settings)

    async def get_current_user(request: Request) -> UserContext:
        """预留 Depends(get_current_user)；切换 AuthProvider 无需大改路由。"""
        return await auth.resolve_user(dict(request.headers))

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "api", "auth_provider": auth.name}

    @application.get("/me")
    async def me(user: UserContext = Depends(get_current_user)) -> dict[str, object]:
        return {
            "user_id": user.user_id,
            "display_name": user.display_name,
            "roles": user.roles,
        }

    # 供测试/调试暴露
    application.state.auth_provider = auth  # type: ignore[attr-defined]
    return application


app = create_app()
